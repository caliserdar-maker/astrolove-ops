#!/usr/bin/env python3
"""Slogan temizligi ONAY SAYFASI (Serdar 2. madde, 25 Eyl 2026).

PLATES/SLOGAN_KIRPIM altindaki once/sonra x3 kirpimlarini TEK SAYFADA toplar:
5 edisyon x istenen boylar. Serdar onaylamadan plate'ler uretimde kullanilmaz.
SALT OKUR: yalniz kirpimlari indirir, birlestirir, Drive'a tek dosya yazar.
"""
import argparse, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KIRPIM = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES/SLOGAN_KIRPIM'
CIK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_sayfa').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
GENISLIK = 2200


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boylar', default='30x40,A3')
    a = ap.parse_args()
    boylar = [x.strip() for x in a.boylar.split(',') if x.strip()]
    rc('copy', KIRPIM, str(W), '--include', '*.jpg')
    satirlar, eksik = [], []
    for boy in boylar:
        for ed in EDISYONLAR:
            f = W / f'SLOGAN_{ed}_{boy}_x3.jpg'
            if f.exists():
                satirlar.append((f'{ed}  {boy}', Image.open(f).convert('RGB')))
            else:
                eksik.append(f'{ed}_{boy}')
    if not satirlar:
        raise SystemExit(f'hic kirpim yok (eksik: {eksik})')
    parcalar = []
    for ad, im in satirlar:
        if im.width != GENISLIK:
            im = im.resize((GENISLIK, round(im.height * GENISLIK / im.width)), Image.LANCZOS)
        parcalar.append((ad, im))
    bas = 64
    yuk = bas + sum(i.height + 38 for _, i in parcalar) + 20
    t = Image.new('RGB', (GENISLIK + 40, yuk), 'white')
    d = ImageDraw.Draw(t)
    d.text((20, 16), 'SLOGAN TEMIZLIGI - ONAY SAYFASI  (her blokta ustte ONCE, altta SONRA, x3)',
           fill='black')
    d.text((20, 36), f'{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")} UTC'
                     + (f'   EKSIK: {", ".join(eksik)}' if eksik else ''), fill='black')
    y = bas
    for ad, im in parcalar:
        d.text((20, y), ad, fill='black')
        t.paste(im, (20, y + 16)); y += im.height + 38
    ad = 'SLOGAN_ONAY_SAYFASI.jpg'
    t.save(W / ad, quality=94)
    rc('copy', str(W / ad), CIK, timeout=900)
    print(f'{ad} {t.size} | blok {len(parcalar)} | eksik {eksik}')


if __name__ == '__main__':
    main()
