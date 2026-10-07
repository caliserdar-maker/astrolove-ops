#!/usr/bin/env python3
"""HEDEF GORUNUM KAPISI (Serdar 7 Eki, ChatGPT referansi): REF / T5 / YENI ayni olcekte (2000x3000), YENI posterin
maskesiyle (yerlesim ayni) olculur. Kapilar (hatta FAIL):
  REF uzakligi : her ogede medyan dE00 (YENI oge - REF ayni oge, 2000 olcek) <= REF_DE_ESIK (1.5); cember ve sonsuzda
                 YALNIZ RAPOR (Serdar 7 Eki, secenek b: ogeler arasi esitlik esas, ince ogeler 2000'de kararir)
  sekil        : ana sembol + kucuk semboller altin maske T5 ile ortusme (IoU) >= SEKIL_ESIK (%99); maske RENKTEN
                 BAGIMSIZ: ALFA.png > 0.5, oge kutusunda (D1'de renk esikli maske renk degisiminde kenar topluyordu)
  cember dilim : cember boyunca 36 dilim (10 derece), aci basina tepe L* (yaricap boyunca, yerel zemine gore fazla);
                 REF'in sonmedigi acilar; dilim medyanlari farki (maks - min) <= REF'in kendi degeri (D2, 7 Eki)
Rapor (kapi degil): zemin radyal profil farki (kanal, RMS / maks), ic doku (3x3, cekirdek ici), cember genislik / tepe.
Ogeler arasi dE00, kirmizimsi, leke, parca: renk_kapi (RENK_KAPI.json); halka: arka_kapi.

Kullanim: hedef_kapi.py --ref REF.png --yeni DIR_YENI --t5 DIR_T5 --json OUT
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import ref_olc as ro                                                 # noqa: E402

Image.MAX_IMAGE_PIXELS = None
REF_DE_ESIK = 1.5
SEKIL_ESIK = 99.0
SEKIL_OGE = ('ana_sembol', 'kucuk_sol', 'kucuk_sag')
REF_RAPOR = ('cember', 'sonsuz')


def tepe_L(f):
    """aci basina cember tepe L* fazlasi (2000 olcek)."""
    from skimage.color import rgb2lab
    cx, cy, R = (v * ro.W2 / 7200 for v in ro.dp.halka_geo(ro.dp.HALKA24))
    I = ro.kucult(np.asarray(Image.open(f).convert('RGB'))); L = rgb2lab(I / 255.)[..., 0].astype(np.float32)
    d = np.arange(-12, 12.01, 0.1); out = []
    for t in range(360):
        th = np.radians(t); xs = cx + (R + d) * np.cos(th); ys = cy + (R + d) * np.sin(th)
        if xs.min() < 1 or ys.min() < 1 or xs.max() > ro.W2 - 2 or ys.max() > ro.H2 - 2:
            out.append(np.nan); continue
        v = cv2.remap(L, xs[None].astype(np.float32), ys[None].astype(np.float32), cv2.INTER_LINEAR)[0]
        out.append(v.max() - np.median(np.r_[v[:20], v[-20:]]))
    return np.array(out)


def dilim(p, ok):
    med = [float(np.median(p[i * 10:i * 10 + 10][ok[i * 10:i * 10 + 10]])) for i in range(36) if ok[i * 10:i * 10 + 10].sum() >= 5]
    return {'n': len(med), 'fark': round(float(np.ptp(med)), 2), 'medyanlar': [round(v, 1) for v in med]}


def altin(P, k):
    x0, y0, x1, y1 = k
    lab = cv2.cvtColor(np.ascontiguousarray(P[y0:y1, x0:x1]).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    return (lab[..., 2] > 20) & (lab[..., 0] > 20)


def main():
    ap = argparse.ArgumentParser()
    for k in ('ref', 'yeni', 't5', 'json'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    Y, T5 = Path(a.yeni), Path(a.t5)
    M, A = ro.maskeler(Y)
    R = {'REF': ro.olc(a.ref, M, A), 'T5': ro.olc(T5 / 'GOLGE_1.png', M, A), 'YENI': ro.olc(Y / 'GOLGE_1.png', M, A)}
    out = {'ogeler': {}, 'zemin': {}, 'cember': {}, 'sekil': {}}
    for ad in R['REF']['ogeler']:
        r = {k: R[k]['ogeler'][ad] for k in R}
        out['ogeler'][ad] = {
            'Lab': {k: v['Lab'] for k, v in r.items()},
            'L_p5_50_95_99': {k: [v['L_q'][i] for i in (1, 12, 23, 24)] for k, v in r.items()},
            'dE00_ref': {k: ro.de(v['Lab'], r['REF']['Lab']) for k, v in r.items()},
            'doku_ic3': {k: v['doku_ic3'] for k, v in r.items()},
            'kirmizi_2000': {k: v['kirmizi_yuzde'] for k, v in r.items()}}
        out['ogeler'][ad]['ref_gecti'] = ad in REF_RAPOR or out['ogeler'][ad]['dE00_ref']['YENI'] <= REF_DE_ESIK
        out['ogeler'][ad]['ref_kapi'] = 'rapor' if ad in REF_RAPOR else f'<= {REF_DE_ESIK}'
    n = np.array(R['REF']['zemin']['profil_n']) >= 200
    for k in ('T5', 'YENI'):
        d = [np.array(R[k]['zemin']['profil'][c])[n] - np.array(R['REF']['zemin']['profil'][c])[n] for c in range(3)]
        out['zemin'][k] = {'ort_rgb': R[k]['zemin']['ort_rgb'],
                           'fark_rms': [round(float(np.sqrt((x ** 2).mean())), 2) for x in d],
                           'fark_maks': [round(float(np.abs(x).max()), 2) for x in d]}
    out['zemin']['REF'] = {'ort_rgb': R['REF']['zemin']['ort_rgb']}
    for k in R:
        c = [v for i, v in enumerate(R[k]['cember']) if v and not 100 <= i < 135 and v['tepe'] > 60]
        out['cember'][k] = {'genislik_med': round(float(np.median([v['genislik'] for v in c])), 3),
                            'tepe_med': round(float(np.median([v['tepe'] for v in c])), 1),
                            'tepe_aci_45_135': [R[k]['cember'][i]['tepe'] if R[k]['cember'][i] else 0
                                                for i in (24, 30, 36, 42, 138, 144, 150, 156)]}
    AY = np.asarray(Image.open(Y / 'ALFA.png')); AT = np.asarray(Image.open(T5 / 'ALFA.png'))
    ku = json.loads((Y / 'POSTER.json').read_text())['kutu']
    for ad in SEKIL_OGE:
        x0, y0, x1, y1 = ku[ad]
        gy, gt = AY[y0:y1, x0:x1] > 127, AT[y0:y1, x0:x1] > 127
        iou = 100 * (gy & gt).sum() / max((gy | gt).sum(), 1)
        out['sekil'][ad] = {'iou_yuzde': round(float(iou), 3), 'gecti': bool(iou >= SEKIL_ESIK)}
    tp = {'REF': tepe_L(a.ref), 'T5': tepe_L(T5 / 'GOLGE_1.png'), 'YENI': tepe_L(Y / 'GOLGE_1.png')}
    ok = np.isfinite(tp['REF']) & (tp['REF'] > 0.9 * np.nanmedian(tp['REF'])); ok[100:135] = False
    out['cember_dilim'] = {k: dilim(v, ok) for k, v in tp.items()}
    out['cember_dilim']['esik'] = out['cember_dilim']['REF']['fark']
    out['cember_dilim']['gecti'] = out['cember_dilim']['YENI']['fark'] <= out['cember_dilim']['esik']
    out['sonuc'] = 'PASS' if (all(v['ref_gecti'] for v in out['ogeler'].values())
                              and all(v['gecti'] for v in out['sekil'].values())
                              and out['cember_dilim']['gecti']) else 'FAIL'
    Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for ad, v in out['ogeler'].items():
        print(f"{ad:11s} dE_ref T5 {v['dE00_ref']['T5']:.2f} YENI {v['dE00_ref']['YENI']:.2f} | ic doku REF/T5/YENI "
              f"{v['doku_ic3']['REF']:.2f}/{v['doku_ic3']['T5']:.2f}/{v['doku_ic3']['YENI']:.2f} | Lab YENI {v['Lab']['YENI']} REF {v['Lab']['REF']}")
    print('zemin', out['zemin']); print('cember', out['cember']); print('sekil', out['sekil'])
    print('cember dilim', {k: (v['fark'] if isinstance(v, dict) else v) for k, v in out['cember_dilim'].items()}); print(out['sonuc'])
    sys.exit(0 if out['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
