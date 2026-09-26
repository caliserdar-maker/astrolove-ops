#!/usr/bin/env python3
"""Canva kaynakli plate'lerde slogan izi denetimi (GOREV_0015 + GOREV_0014).

ONCE/SONRA cifti burada silme adimindan degil, iki AYRI plate'ten gelir:
  ONCE  = PLATES/HAM/<ED>_<BOY>.png   (ortanca plate; slogan DURUYOR)
  SONRA = PLATES/<ED>_CANVA_<BOY>.png (Canva kopyasi; slogan katmani SILINDI)
Maske ikisinin farkidir, yani tam olarak sloganin kapladigi alan.

Olcut GOREV_0014 kurali: sapma (maske ici/disi p99) VE Sobel kenar enerjisi.
Ikisi de temiz demeden TEMIZ yazilmaz. Salt okur: Drive'a hicbir sey yazmaz.
"""
import argparse, json, subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from slogan_sayfa import KENAR_ESIK, KENAR_MUTLAK

Image.MAX_IMAGE_PIXELS = None
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_cdenetim').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
# Canva sayfasi 3000x4000; slogan katmani top 3427, left 1035, 930x96.
SLOGAN_KUTU_3000 = (1035, 3427, 1035 + 930, 3427 + 96)
PAY_3000 = 60          # bandin disindan referans doku icin pay
SAPMA_ESIK = 4.0       # ic_p99 - dis_p99 (kalinti_olc2 ile ayni esik)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def serit(yol):
    """Plate'ten slogan bandini (paylı) gri olarak keser."""
    with Image.open(yol) as im:
        k = im.width / 3000.0
        x0, y0, x1, y1 = SLOGAN_KUTU_3000
        p = PAY_3000 * k
        kutu = (max(int(x0 * k - p), 0), max(int(y0 * k - p), 0),
                min(int(x1 * k + p), im.width), min(int(y1 * k + p), im.height))
        return np.asarray(im.crop(kutu).convert('L')).astype(np.float32)


def maske(once, sonra):
    m = cv2.dilate((np.abs(once - sonra) > 10).astype(np.uint8),
                   np.ones((5, 5), np.uint8)) > 0
    return m


def sapma_olc(once, sonra, m):
    """Maske ICI p99 - DISI p99; zemin dokuyu izleyen medyan (yaricap 41)."""
    z = cv2.medianBlur(np.clip(sonra, 0, 255).astype(np.uint8), 41).astype(np.float32)
    ic, dis = np.abs(sonra - z)[m], np.abs(sonra - z)[~m]
    o_ic = np.abs(once - z)[m]
    ic99, dis99 = float(np.percentile(ic, 99)), float(np.percentile(dis, 99))
    d = {'ONCE_ic_ort': round(float(o_ic.mean()), 2),
         'SONRA_ic_ort': round(float(ic.mean()), 2),
         'ic_p99': round(ic99, 1), 'dis_p99': round(dis99, 1),
         'FARK': round(ic99 - dis99, 1)}
    d['sonuc'] = ('olculemedi (zemin dokusu cok guclu)' if dis99 > 40
                  else 'TEMIZ' if d['FARK'] <= SAPMA_ESIK else 'IZ VAR')
    return d


def kenar_olc(once, sonra, m):
    def enerji(a):
        gx = cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3)
        return np.abs(gx) + np.abs(gy)
    e_s, e_o = enerji(sonra), enerji(once)
    ic, dis = float(e_s[m].mean()), float(e_s[~m].mean())
    o_ic = float(e_o[m].mean())
    duz = dis < 1.0
    oran = ic / max(dis, 1e-6)
    d = {'SONRA_ic_kenar': round(ic, 2), 'SONRA_dis_kenar': round(dis, 2),
         'ONCE_ic_kenar': round(o_ic, 2), 'oran': round(oran, 3),
         'SONRA/ONCE': round(ic / max(o_ic, 1e-6), 3),
         'zemin': 'duz' if duz else 'dokulu'}
    d['sonuc'] = ('TEMIZ' if ic <= dis + KENAR_MUTLAK else 'IZ VAR') if duz else \
                 ('TEMIZ' if oran <= KENAR_ESIK else 'IZ VAR')
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boy', default='30x40')
    ap.add_argument('--edisyon', default='')
    a = ap.parse_args()
    eds = [e for e in EDISYONLAR if not a.edisyon or e in a.edisyon.split(',')]
    rapor = {}
    for ed in eds:
        try:
            ham, yeni = W / f'HAM_{ed}.png', W / f'CANVA_{ed}.png'
            rc('copyto', f'{PLATES}/HAM/{ed}_{a.boy}.png', str(ham))
            rc('copyto', f'{PLATES}/{ed}_CANVA_{a.boy}.png', str(yeni))
            once, sonra = serit(ham), serit(yeni)
            ham.unlink(missing_ok=True); yeni.unlink(missing_ok=True)
            if once.shape != sonra.shape:
                rapor[ed] = {'hata': f'serit olcusu farkli {once.shape} {sonra.shape}'}
                continue
            m = maske(once, sonra)
            if m.sum() < 200 or (~m).sum() < 200:
                rapor[ed] = {'hata': f'maske kucuk ({int(m.sum())} px)'}
                continue
            s, k = sapma_olc(once, sonra, m), kenar_olc(once, sonra, m)
            rapor[ed] = {'maske_px': int(m.sum()), 'sapma': s, 'kenar': k,
                         'SONUC': ('TEMIZ' if s['sonuc'] == 'TEMIZ' and k['sonuc'] == 'TEMIZ'
                                   else f"{s['sonuc']} / {k['sonuc']}")}
        except BaseException as e:                                    # noqa: BLE001
            rapor[ed] = {'hata': f'{type(e).__name__}: {e}'}
    print(json.dumps(rapor, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
