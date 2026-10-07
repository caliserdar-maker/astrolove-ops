#!/usr/bin/env python3
"""HEDEF GORUNUM KAPISI (Serdar 7 Eki, ChatGPT referansi): REF / T5 / YENI ayni olcekte (2000x3000), YENI posterin
maskesiyle (yerlesim ayni) olculur. Kapilar (hatta FAIL):
  REF uzakligi : her ogede medyan dE00 (YENI oge - REF ayni oge, 2000 olcek) <= REF_DE_ESIK (1.5)
  sekil        : ana sembol + kucuk semboller altin maske (7200 olcek, oge kutusunda b* > 20 ve L > 20) T5 ile
                 ortusme (IoU) >= SEKIL_ESIK (%99)
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
        out['ogeler'][ad]['ref_gecti'] = out['ogeler'][ad]['dE00_ref']['YENI'] <= REF_DE_ESIK
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
    PY = np.asarray(Image.open(Y / 'GOLGE_1.png').convert('RGB')); PT = np.asarray(Image.open(T5 / 'GOLGE_1.png').convert('RGB'))
    ku = json.loads((Y / 'POSTER.json').read_text())['kutu']
    for ad in SEKIL_OGE:
        x0, y0, x1, y1 = ku[ad]; k = (max(x0 - 20, 0), max(y0 - 20, 0), x1 + 20, y1 + 20)
        gy, gt = altin(PY, k), altin(PT, k)
        iou = 100 * (gy & gt).sum() / max((gy | gt).sum(), 1)
        out['sekil'][ad] = {'iou_yuzde': round(float(iou), 3), 'gecti': bool(iou >= SEKIL_ESIK)}
    out['sonuc'] = 'PASS' if (all(v['ref_gecti'] for v in out['ogeler'].values())
                              and all(v['gecti'] for v in out['sekil'].values())) else 'FAIL'
    Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for ad, v in out['ogeler'].items():
        print(f"{ad:11s} dE_ref T5 {v['dE00_ref']['T5']:.2f} YENI {v['dE00_ref']['YENI']:.2f} | ic doku REF/T5/YENI "
              f"{v['doku_ic3']['REF']:.2f}/{v['doku_ic3']['T5']:.2f}/{v['doku_ic3']['YENI']:.2f} | Lab YENI {v['Lab']['YENI']} REF {v['Lab']['REF']}")
    print('zemin', out['zemin']); print('cember', out['cember']); print('sekil', out['sekil']); print(out['sonuc'])
    sys.exit(0 if out['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
