#!/usr/bin/env python3
"""LEKE TEMIZLIGI (Serdar 4 Eki): onayli Canva dokusunda (cila sonrasi sayfa npz) yalniz leke_kapi lekelerinde renk
duzeltmesi. Yeni Canva uretimi YOK; sekil / kontur / ince uc / desen degismez, leke disi piksel DEGISMEZ.

1 leke maskesi : leke_kapi.olc (doygunluk < 0.42, parlaklik > 0.55, bilesen >= 800 px, cekirdekte).
2 kontur bandi : d = oge icinde kenara uzaklik (px); BANT sinirlarina gore bant no. Kabartma kesiti banda gore degisir.
3 hedef ton    : her bantta lekesiz cekirdek altininin (leke 5 px genisletilip disarida) yerel Lab ortalamasi,
                 normalize Gauss evrisim (SIGMA_REF; bos yerde SIGMA_GENIS).
   (2. deneme: bant = kenara uzaklik x en yakin kenarin yonu (8 yon), hedef cizginin ayni tarafindan; 1. denemede
    yalniz uzaklik bandi koyu taraftan ton aliyordu, duzeltilen yerler kahverengi lekeye donuyordu)
4 leke bolgesi : kapi lekesine bagli solgun bolge, histerezis doygunluk < S_UST (kapi maskesi lekenin cekirdegi; tamami
                 degil). Bolge disi piksel DEGISMEZ.
5 duzeltme     : lekenin kendi dusuk frekans tonu (ayni grupta, SIGMA_LEKE) -> Delta = hedef - kendi; yeni Lab = Lab +
                 w x Delta; w = solgunlukla orantili (doygunluk S_UST'te 0, 0.42 ve alti 1), 1.5 px yumusak: sinirda 0,
                 sert kenar yok. Delta yavas degistigi icin dokunun ince deseni (yuksek frekans) aynen kalir.

Kullanim: leke_temizle.py --set S17 --sayfa-json DIR --sayfa ANA_DENEME --oge CANCER_LIBRA --cikti-npz OUT.npz
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import leke_kapi as lk                                               # noqa: E402

BANT = [0, 4, 8, 13, 19, 26, 35, 1e9]
SIGMA_REF, SIGMA_GENIS, SIGMA_LEKE = 40.0, 160.0, 6.0
S_UST = 0.55          # leke bolgesi histerezis ust doygunlugu; agirlik S_UST'te 0, kapi esiginde (0.42) 1


def lab(t):
    return cv2.cvtColor(t.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def rgb(L):
    return np.clip(cv2.cvtColor(L.astype(np.float32), cv2.COLOR_LAB2RGB) * 255, 0, 255)


def nconv(X, m, s):
    w = cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)
    return cv2.GaussianBlur(X * m[..., None], (0, 0), s) / np.maximum(w, 1e-6)[..., None], w


def temizle(t, O):
    v0, cey0, bm = lk.olc(t, O)
    ce = cv2.erode((O > 0.95).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    hsv = cv2.cvtColor(np.ascontiguousarray(t), cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    sb = cv2.GaussianBlur(hsv[..., 1], (0, 0), 2)
    # leke bolgesi R: kapi lekesine bagli solgun bolge (histerezis, doygunluk < S_UST)
    n, lab_, _, _ = cv2.connectedComponentsWithStats(((sb < S_UST) & (hsv[..., 2] > 0.5) & ce).astype(np.uint8), 8)
    tut = np.zeros(n, bool); tut[np.unique(lab_[bm])] = True; tut[0] = False
    R = tut[lab_]
    # kontur bandi: kenara uzaklik x en yakin kenarin yonu (cizginin ayni tarafi)
    ic = (O > 0.5).astype(np.uint8)
    d, lbl = cv2.distanceTransformWithLabels(ic, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ey, ex = np.nonzero(ic == 0)
    ez = np.zeros((lbl.max() + 1, 2), np.float32)
    ez[lbl[ey, ex]] = np.c_[ex, ey]
    yy, xx = np.mgrid[0:O.shape[0], 0:O.shape[1]]
    v = ez[lbl] - np.dstack([xx, yy]).astype(np.float32)
    yon = ((np.degrees(np.arctan2(v[..., 1], v[..., 0])) + 360 + 22.5) // 45).astype(int) % 8
    del v, yy, xx, lbl
    grup = (np.digitize(d, BANT) - 1) * 8 + yon
    Lb = lab(t)
    temiz = ce & ~cv2.dilate(R.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
    D = np.zeros_like(Lb)
    for g in np.unique(grup[R]):
        gg = grup == g; hl = R & gg
        ref, w = nconv(Lb, temiz & gg, SIGMA_REF)
        refg, wg = nconv(Lb, temiz & gg, SIGMA_GENIS)
        ref = np.where((w > 1e-3)[..., None], ref, refg)
        own, _ = nconv(Lb, hl, SIGMA_LEKE)
        ok = hl & (np.maximum(w, wg) > 1e-4)
        D[ok] = (ref - own)[ok]
    w = np.clip((S_UST - sb) / (S_UST - lk.DOY_MAX), 0, 1) * R
    w = cv2.GaussianBlur(w, (0, 0), 1.5) * R
    yeni = rgb(Lb + D * w[..., None])
    t2 = t.copy()
    t2[R] = np.round(yeni[R]).astype(np.uint8)
    v1, cey1, _ = lk.olc(t2, O)
    deg = (t2 != t).any(-1)
    return t2, R, {'leke_once': v0, 'leke_sonra': v1, 'ceyrek_once': cey0, 'ceyrek_sonra': cey1, 'esik': lk.ESIK,
                   'kapi_leke_px': int(bm.sum()), 'leke_bolgesi_px': int(R.sum()), 'degisen_px': int(deg.sum()),
                   'leke_bolgesi_disi_degisen_oran': float((deg & ~R).mean()),
                   'kapi_maskesi_disi_degisen_px': int((deg & ~bm).sum())}


def main():
    ap = argparse.ArgumentParser()
    for k in ('set', 'sayfa-json', 'sayfa', 'oge', 'cikti-npz'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    z = np.load(Path(a.set) / f'{a.sayfa}.npz'); t1, Oall = z['t1'].copy(), z['O']
    j = json.loads((Path(a.sayfa_json) / f'DOKU_AI_{a.sayfa}.json').read_text())
    x0, y0, x1, y1 = [o['kutu'] for o in j['ogeler'] if o['oge'] == a.oge][0]
    t2, bm, rap = temizle(t1[y0:y1, x0:x1], Oall[y0:y1, x0:x1].astype(np.float32) / 255)
    t1[y0:y1, x0:x1] = t2
    np.savez_compressed(a.cikti_npz, t1=t1, O=Oall)
    np.save(Path(a.cikti_npz).with_suffix('.leke.npy'), bm)
    rap |= {'oge': a.oge, 'kutu': [x0, y0, x1, y1], 'kaynak': f'{a.sayfa}.npz'}
    print(json.dumps(rap, ensure_ascii=False))
    Path(a.cikti_npz).with_suffix('.json').write_text(json.dumps(rap, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
