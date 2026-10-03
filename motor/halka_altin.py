#!/usr/bin/env python3
"""Altin edisyon plate'inde halka (cember) katmani + halkasiz zemin (Serdar 3 Eki: TEK DOKU BUTUNLUGU, cember ana
sembolle ayni renk / doku / parlaklikta). BIR KEZ uretilir, sha + kayitla saklanir; render sirasinda zemine dokunulmaz
(yazi cevresi yildiz temizligi haric, Serdar 3 Eki B maddesi).

1) Halka geometrisi: yerel kagittan (medyan pencere 62 x W / 3307) parlak fark > 10 luma, genisligi sayfanin
   >= %35'i olan bilesenler (olc.halka_maskesi ile ayni olcut, genisletmesiz).
2) Halka alfasi: GEOMETRIK kaplama (3 Eki goz kontrolu: fark / sabit cekirdek ortancasi alfasi plate halkasinin
   kendi parlaklik dalgalanmasini saydamliga ceviriyordu; kopruk / lekeli cember). Her noktada yerel kesit tepesi
   (25 x W / 4800 px pencerede en buyuk fark) ile normalize: alfa = fark / (0.5 x tepe), 0-1; yari yukseklik
   genisligi dolu, kenarlar yumusak. 7 px bolge icinde, gurultu tabani (wb.T0) alti 0.
2b) Geometri (3 Eki 2. bulgu: plate halkasinin kenari piksel basamakli, merkez cizgisi dalgali; boru profili ic
   cizgisi kayiyordu): agirlikli daire uydurmasi (merkez, R); 0.25 derecelik dilimlerde merkez cizgisi sapmasi rc(aci) ve
   yari genislik hw(aci) = alfa toplami / yay / 2; aci boyunca Gauss yumusatma (2 derece). Son alfa = clip(hw - |rho -
   rc| + 0.5), kesit konumu u = (rho - rc) / hw. Uclarin incelmesi korunur. Geometri json'a yazilir (motor t'yi buradan
   hesaplar).
3) Halkasiz zemin: kilitli wp_bakir.kagit_tabani (yalniz halka altinda inpaint, plate'in geri kalani birebir).
QC (PASS/FAIL): halkasiz zeminde halka bolgesinde kalan parlak fark ortancasi <= 2 luma, p99 <= 8; halka disi birebir.

Kullanim: halka_altin.py --plate PLATES/BLUE_16x20.png --cikti motor/varlik
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
import wp_katman as wk                                                # noqa: E402
import wp_bakir as wb                                                 # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def yerel(L):
    W = L.shape[1]
    kw = 31 if W == 3307 else int(round(62 * W / 3307)) | 1
    return cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), kw).astype(np.float32)


DILIM = 0.25      # derece
YUMUSAT = 2.0     # derece (Gauss sigma, aci boyunca)


def geometri(alfa):
    ys, xs = np.nonzero(alfa > 0.02)
    w = alfa[ys, xs].astype(np.float64)
    M = np.stack([xs, ys, np.ones_like(xs)], 1).astype(np.float64) * np.sqrt(w)[:, None]
    c = np.linalg.lstsq(M, (xs ** 2. + ys ** 2.) * np.sqrt(w), rcond=None)[0]
    cx, cy = c[0] / 2, c[1] / 2
    R = float(np.sqrt(c[2] + cx ** 2 + cy ** 2))
    rho = np.hypot(xs - cx, ys - cy) - R
    nb = int(round(360 / DILIM))
    k = (np.floor((np.degrees(np.arctan2(ys - cy, xs - cx)) + 180) / DILIM).astype(int)) % nb
    sw = np.bincount(k, w, nb)
    rc = np.bincount(k, w * rho, nb) / np.maximum(sw, 1e-9)
    hw = sw / (np.radians(DILIM) * R) / 2
    var = sw > 0
    # bos dilimlerde rc: komsu doldurma (dairesel), hw 0
    idx = np.arange(nb)
    rc = np.interp(idx, idx[var], rc[var], period=nb)
    g = YUMUSAT / DILIM
    yum = lambda v: cv2.GaussianBlur(np.tile(v, 3).astype(np.float32)[None], (0, 0), g)[0][nb:2 * nb]
    return {'merkez': [round(cx, 3), round(cy, 3)], 'R': round(R, 3), 'dilim_derece': DILIM,
            'rc': [round(float(v), 3) for v in yum(rc)], 'hw': [round(float(v), 3) for v in yum(hw)]}


def geo_uv(shape, geo):
    """her piksel icin (u, hw): u = (rho - rc(aci)) / hw(aci) (kesit konumu, 0 merkez cizgisi), hw yari genislik."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = geo['merkez']
    rho = np.hypot(xx - cx, yy - cy) - geo['R']
    a = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 180) / geo['dilim_derece']
    nb = len(geo['rc'])
    rc = np.interp(a, np.arange(nb + 1), np.r_[geo['rc'], geo['rc'][0]]).astype(np.float32)
    hw = np.interp(a, np.arange(nb + 1), np.r_[geo['hw'], geo['hw'][0]]).astype(np.float32)
    return (rho - rc), hw


def geo_alfa(shape, geo):
    d, hw = geo_uv(shape, geo)
    return np.clip(hw - np.abs(d) + 0.5, 0, 1).astype(np.float32) * (hw > 0.05)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plate', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    pf = Path(a.plate)
    C = Path(a.cikti)
    P = np.asarray(Image.open(pf).convert('RGB'), np.float32)
    L = P @ wk.LUMA
    H, W = L.shape
    d = L - yerel(L)
    n, lab, st, _ = cv2.connectedComponentsWithStats((np.abs(d) > 10).astype(np.uint8), 8)
    tut = [i for i in range(1, n) if st[i, cv2.CC_STAT_WIDTH] > 0.35 * W and st[i, cv2.CC_STAT_AREA] > 500 * (W / 3307) ** 2]
    daire = np.isin(lab, tut)
    mc = np.clip(d, 0, None)
    bolge = cv2.dilate(daire.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    ce = cv2.erode(daire.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    Lk = float(np.median(mc[ce if ce.sum() > 500 else daire]))
    kw = int(round(25 * W / 4800)) | 1
    tepe = cv2.dilate(mc * bolge, np.ones((kw, kw), np.uint8))
    alfa = np.clip(mc / np.maximum(0.5 * tepe, 1.0), 0, 1) * bolge
    alfa[mc < wb.T0] = 0
    geo = geometri(alfa)
    alfa_g = geo_alfa(alfa.shape, geo)
    alfa_sil = np.maximum(alfa, alfa_g)                               # zeminden silinecek: eski + yeni kaplama
    alfa = alfa_g
    ad = pf.stem
    (C / 'halka').mkdir(parents=True, exist_ok=True); (C / 'plates').mkdir(parents=True, exist_ok=True)
    hf = C / 'halka' / f'HALKA_{ad}.png'
    Image.fromarray(np.round(alfa * 255).astype(np.uint8), 'L').save(hf)
    P1, dd = wb.kagit_tabani(P, alfa_sil > 0.02)
    zf = C / 'plates' / f'{ad}_halkasiz.png'
    Image.fromarray(np.clip(np.round(P1), 0, 255).astype(np.uint8)).save(zf)
    P1 = np.asarray(Image.open(zf).convert('RGB'), np.float32)
    L1 = P1 @ wk.LUMA
    kal = np.clip(L1 - yerel(L1), 0, None)[alfa_sil > 0.5]
    disari = np.abs(P1 - P).max(2)[~cv2.dilate(dd.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)]
    qc = {'halka_kalan_ortanca': round(float(np.median(kal)), 2), 'halka_kalan_p99': round(float(np.percentile(kal, 99)), 2),
          'halka_disi_degisen_px': int((disari > 0).sum())}
    qc['gecti'] = qc['halka_kalan_ortanca'] <= 2 and qc['halka_kalan_p99'] <= 8 and qc['halka_disi_degisen_px'] == 0
    R = {'kaynak_plate': {'dosya': f'TEMP/SIPARIS_ISIM/PLATES/{pf.name}', 'sha256': sha(pf)},
         'halka': {'dosya': str(hf.relative_to(KOK.parent)) if hf.is_absolute() else str(hf), 'sha256': sha(hf),
                   'Lk': round(Lk, 2), 'px': int((alfa > 0.02).sum()), 'geometri': geo},
         'halkasiz_zemin': {'dosya': str(zf), 'sha256': sha(zf)}, 'qc': qc}
    (C / 'plates' / f'{ad}_halkasiz.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, indent=1, ensure_ascii=False))
    sys.exit(0 if qc['gecti'] else 1)


if __name__ == '__main__':
    main()
