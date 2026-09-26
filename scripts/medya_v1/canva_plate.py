#!/usr/bin/env python3
"""Canva kaynagindan plate (GOREV_0015).

Canva'da posterin orijinal katmanlari duruyor; slogan ve cifte ozel ogeler
AYRI KATMAN. Kopyada bunlar silinip disa aktarilinca temiz zemin dogrudan
cikiyor - 6 iterasyondur piksel duzeyinde silmeye calistigimiz sey kaynakta
cozuluyor.

Bu script yalnizca disa aktarilmis PNG'yi alir, MEVCUT plate ile karsilastirir
(slogan bandi disinda fark ~0 olmali - ayni kaynak) ve PLATES'e YENI adla
yukler. Eski plate'lere DOKUNMAZ.

Export URL'leri imzali ve gecici oldugu icin Drive'daki bir JSON'dan okunur:
  TEMP/SIPARIS_ISIM/CANVA_EXPORT.json = {"<ad>": {"url": ..., "kiyas": ...}}
"""
import argparse, json, subprocess, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
KOK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM'
PLATES = f'{KOK}/PLATES'
W = Path('_canva').resolve(); W.mkdir(exist_ok=True)
# Canva sayfasi 3000x4000; slogan katmani top 3427, left 1035, 930x95.7.
# Orana gore olceklenir (plate genisligi / 3000).
SLOGAN_KUTU_3000 = (1035, 3427, 1035 + 930, 3427 + 96)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def indir(url, hedef):
    with urllib.request.urlopen(url, timeout=600) as r, open(hedef, 'wb') as f:
        while True:
            p = r.read(1 << 20)
            if not p:
                break
            f.write(p)
    return hedef


def kiyas(yeni, eski):
    """Slogan bandi DISINDA fark ~0 mi? (ayni kaynak, ayni olcek beklenir)"""
    a = np.asarray(Image.open(yeni).convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(eski).convert('RGB')).astype(np.float32)
    if a.shape != b.shape:
        return {'hata': f'boyut farkli: yeni {a.shape[:2]} eski {b.shape[:2]}'}
    k = a.shape[1] / 3000.0
    x0, y0, x1, y1 = (int(round(v * k)) for v in SLOGAN_KUTU_3000)
    pay = int(round(60 * k))
    m = np.ones(a.shape[:2], bool)
    m[max(y0 - pay, 0):y1 + pay, max(x0 - pay, 0):x1 + pay] = False   # bant DISI
    d = np.abs(a - b).max(axis=2)
    dis, ic = d[m], d[~m]
    return {'bant_DISI': {'ort': round(float(dis.mean()), 3),
                          'p99': round(float(np.percentile(dis, 99)), 1),
                          'tepe': round(float(dis.max()), 1)},
            'bant_ICI': {'ort': round(float(ic.mean()), 2),
                         'p99': round(float(np.percentile(ic, 99)), 1)},
            'px': list(a.shape[:2])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--liste', default='CANVA_EXPORT.json')
    ap.add_argument('--yukle', action='store_true', help='PLATES\'e yeni adla yukle')
    a = ap.parse_args()
    rc('copy', f'{KOK}/{a.liste}', str(W))
    isler = json.loads((W / a.liste).read_text())
    rapor = {}
    for ad, d in isler.items():
        try:
            f = indir(d['url'], W / f'{ad}.png')
            r = {'MB': round(f.stat().st_size / 1e6, 1)}
            if d.get('kiyas'):
                rc('copy', f'{PLATES}/{d["kiyas"]}', str(W))
                r['kiyas'] = kiyas(f, W / d['kiyas'])
                (W / d['kiyas']).unlink(missing_ok=True)
            if a.yukle:
                rc('copyto', str(f), f'{PLATES}/{ad}.png')
                r['yuklendi'] = f'{ad}.png'
            f.unlink(missing_ok=True)
            rapor[ad] = r
        except BaseException as e:                                # noqa: BLE001
            rapor[ad] = {'hata': f'{type(e).__name__}: {e}'}
    print(json.dumps(rapor, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
