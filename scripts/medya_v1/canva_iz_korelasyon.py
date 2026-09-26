#!/usr/bin/env python3
"""Slogan izi icin BAGIMSIZ ucuncu olcut: glif sablonu korelasyonu.

canva_denetim'in iki olcutu maskeyi |HAM - Canva| farkindan kurar. HAM ile Canva
plate'in zemin dokusu hizali degilse (Vintage 11x14/A4: bant disi p99 63-72)
maske dokuyu da kapsar ve 'IZ VAR' dokudan gelebilir. Bu script maskeye
dayanmaz: sloganin SEKLINI arar.

  sablon : ayni yerlesimli, duz zeminli edisyonun HAM bandindan glifler
           (Vintage icin MODERN - ayni sayfa yerlesimi, acik duz zemin)
  hedef  : bandin yuksek geciren hali (zemin = medyan 41)
  olcu   : cv2.matchTemplate TM_CCOEFF_NORMED en buyuk degeri
  ONCE   : HAM hedefte (slogan VAR)   -> yuksek beklenir
  SONRA  : Canva hedefte               -> taban duzeyinde beklenir
  TABAN  : Canva'da bandin 400 sayfa-px USTU (yalniz doku)
Karar: SONRA <= TABAN + 0.05 ise slogan YOK. Salt okur.
"""
import argparse, json, subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from canva_denetim import ORAN, KUTU, KUTU_ISTISNA, PAY_3000

Image.MAX_IMAGE_PIXELS = None
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_ckor').resolve(); W.mkdir(exist_ok=True)
FARK_ESIK = 0.05


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')


def bant(yol, kutu, sayfa_en, kaydir=0.0):
    """Payli slogan bandi (gri, float). kaydir: sayfa-px cinsinden dikey kayma."""
    with Image.open(yol) as im:
        k = im.width / float(sayfa_en)
        x0, y0, x1, y1 = kutu
        p = PAY_3000 * sayfa_en / 3000.0
        b = (int((x0 - p) * k), int((y0 - p + kaydir) * k),
             int((x1 + p) * k), int((y1 + p + kaydir) * k))
        return np.asarray(im.crop(b).convert('L')).astype(np.float32)


def yuksek_gecir(a):
    z = cv2.medianBlur(np.clip(a, 0, 255).astype(np.uint8), 41).astype(np.float32)
    return z - a                       # koyu glif -> pozitif


def sablon(a):
    """Duz zeminli bantta glifleri kesip siki kutuya alir."""
    g = yuksek_gecir(a)
    m = g > 25
    if m.sum() < 100:
        raise RuntimeError('sablonda glif bulunamadi')
    ys, xs = np.where(m)
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def ncc(hedef, s):
    h = yuksek_gecir(hedef)
    if h.shape[0] < s.shape[0] or h.shape[1] < s.shape[1]:
        raise RuntimeError(f'hedef {h.shape} sablondan {s.shape} kucuk')
    return float(cv2.matchTemplate(h, s, cv2.TM_CCOEFF_NORMED).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edisyon', default='VINTAGE')
    ap.add_argument('--sablon', default='MODERN', help='ayni yerlesimli duz zeminli edisyon')
    ap.add_argument('--boy', default='30x40,16x20,11x14,A2,A3,A4')
    a = ap.parse_args()
    rapor = {}
    for boy in a.boy.split(','):
        try:
            oran = ORAN[boy]
            kutu, en = KUTU_ISTISNA.get((a.edisyon, oran), KUTU[oran])
            ks, ens = KUTU_ISTISNA.get((a.sablon, oran), KUTU[oran])
            yol = {}
            for ad, uzak in (('sab', f'HAM/{a.sablon}_{boy}.png'),
                             ('ham', f'HAM/{a.edisyon}_{boy}.png'),
                             ('can', f'{a.edisyon}_CANVA_{boy}.png')):
                yol[ad] = W / f'{ad}_{boy}.png'
                rc('copyto', f'{PLATES}/{uzak}', str(yol[ad]))
            s = sablon(bant(yol['sab'], ks, ens))
            d = {'ONCE_HAM': round(ncc(bant(yol['ham'], kutu, en), s), 3),
                 'SONRA_CANVA': round(ncc(bant(yol['can'], kutu, en), s), 3),
                 'TABAN_doku': round(ncc(bant(yol['can'], kutu, en, kaydir=-400), s), 3),
                 'sablon_px': list(s.shape)}
            d['SONUC'] = ('SLOGAN YOK' if d['SONRA_CANVA'] <= d['TABAN_doku'] + FARK_ESIK
                          else 'SLOGAN IZI VAR')
            rapor[boy] = d
            for f in yol.values():
                f.unlink(missing_ok=True)
        except BaseException as e:                                    # noqa: BLE001
            rapor[boy] = {'hata': f'{type(e).__name__}: {e}'}
    for boy, d in rapor.items():
        print(f'{a.edisyon}_{boy:6s}', json.dumps(d, ensure_ascii=False))


if __name__ == '__main__':
    main()
