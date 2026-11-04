#!/usr/bin/env python3
"""Gercek boy onizleme olcek kontrolu (Serdar 4 Kas O1, D maddesi; ORNAMENT_KARAR 6). PASS/FAIL, olculur esik:
  1) PNG dpi = 300 (+-0.5)  -> tuval 954 px = 80,8 mm, 1 px = 25,4/300 mm
  2) karolar 1:1: yukseklik 954, genislik n x 954 + (n-1) x 30 (yeniden orneklenmis onizleme FAIL)
  3) HER karoda kesim cizgisi merkez (476,477) r 449 px: dairenin 4 yonunde (sag, sol, alt, ust) cizgi rengi (150,150,150) +-6 bulunur
     (yaricap 449 +-1 px icinde); r 476,5'te (eski hatali dis cizgi) cizgi rengi BULUNMAZ.
Hesap satiri: tuval_mm = 954 x 25,4 / dpi, kesim_cap_mm = 898 x 25,4 / dpi.
Bilinen FAIL: deneme 3 GEMINI_VIRGO_SADE_GERCEK_BOY_76mm.png (318,85 dpi, cizgi r 476,5) ve %95 yeniden orneklenmis kopya (300 dpi).
Sinir: cizgiyi ciziciyle ayni sabitlerden kontrol eder (KARAR 6 sabitleri); 954 PNG'nin kendi icerik olcegini olcmez (kismen totolojik).
Cikis: 0 PASS, 1 FAIL, 2 cokus. Kullanim: gercek_boy_kontrol.py DOSYA [DOSYA ...] [--json CIKTI]"""
import argparse
import json
import sys

import numpy as np
from PIL import Image

N, KX, KY, KR, CIZGI = 954, 476.0, 477.0, 449.0, np.array([150, 150, 150])


def cizgi_var(a, r, ox=0):
    ok = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        bul = False
        for dr in (-1, 0, 1):
            x, y = int(round(ox + KX + dx * (r + dr))), int(round(KY + dy * (r + dr)))
            if 0 <= x < a.shape[1] and 0 <= y < a.shape[0] and np.abs(a[y, x].astype(int) - CIZGI).max() <= 6:
                bul = True
        ok.append(bul)
    return all(ok), ok


def kontrol(f):
    im = Image.open(f); dpi = im.info.get('dpi', (None, None))[0]
    a = np.asarray(im.convert('RGB'))
    dpi_ok = dpi is not None and abs(float(dpi) - 300) <= 0.5
    H, W = a.shape[:2]
    n = (W + 30) // (N + 30)
    boy_ok = bool(H == N and n >= 1 and W == n * N + (n - 1) * 30)          # karolar 1:1 (954 px, yeniden ornekleme yok)
    karo = []
    for i in range(max(n, 1)):
        k449, y449 = cizgi_var(a, KR, i * (N + 30)); k476, y476 = cizgi_var(a, 476.5, i * (N + 30))
        karo.append(dict(kesim_r449=bool(k449), kesim_yon=y449, eski_r476_5_yok=bool(not k476)))
    r = dict(dosya=str(f), boyut=[int(W), int(H)], karo_sayisi=int(n), karo_1e1_954=boy_ok, dpi=round(float(dpi), 3) if dpi else None,
             tuval_mm=round(N * 25.4 / float(dpi), 2) if dpi else None, kesim_cap_mm=round(2 * KR * 25.4 / float(dpi), 2) if dpi else None,
             dpi_300=bool(dpi_ok), karo=karo, kesim_r449=bool(all(k['kesim_r449'] for k in karo)),
             eski_r476_5_yok=bool(all(k['eski_r476_5_yok'] for k in karo)))
    r['gecti'] = bool(dpi_ok and boy_ok and r['kesim_r449'] and r['eski_r476_5_yok'])
    return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dosya', nargs='+'); ap.add_argument('--json')
    a = ap.parse_args()
    R = [kontrol(f) for f in a.dosya]
    for r in R:
        print('PASS' if r['gecti'] else 'FAIL', r['dosya'], '| dpi', r['dpi'], '| tuval', r['tuval_mm'], 'mm | kesim cap', r['kesim_cap_mm'], 'mm | r449',
              r['kesim_r449'], '| r476.5 yok', r['eski_r476_5_yok'], flush=True)
    if a.json:
        open(a.json, 'w').write(json.dumps(R, indent=1, ensure_ascii=False))
    return 0 if all(r['gecti'] for r in R) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
