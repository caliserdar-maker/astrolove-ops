#!/usr/bin/env python3
"""SADE_8 KONTAK_8.jpg: 2 x 4 numarali Printful mockuplari, altinda aday adi + acik zemin KATI kontrast (OLCUM.json), OKUNMAZ etiketi.
Kullanim: ornament_kontak.py --dir DIR --font TTF"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dir', required=True); ap.add_argument('--font', required=True)
    a = ap.parse_args(); O = Path(a.dir)
    R = json.loads((O / 'OLCUM.json').read_text())
    W, H_ET = 600, 96
    f1, f2 = ImageFont.truetype(a.font, 30), ImageFont.truetype(a.font, 24)
    u = Image.new('RGB', (4 * W + 5 * 16, 2 * (W + H_ET) + 3 * 16), 'white')
    for i in range(8):
        n = str(i + 1); r = R['aday'][n]
        im = Image.open(O / f'MOCKUP_{n}.jpg').convert('RGB')
        s = W / max(im.size); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x, y = 16 + (i % 4) * (W + 16), 16 + (i // 4) * (W + H_ET + 16)
        u.paste(im, (x + (W - im.width) // 2, y + (W - im.height) // 2))
        d = ImageDraw.Draw(u)
        ad = r['dosya'].replace('_954.png', '').replace('SADE_', '').replace('_', ' ')
        d.text((x + 4, y + W + 6), ad, fill=(20, 20, 20), font=f1)
        okun = r['okunur']
        d.text((x + 4, y + W + 46), f'kati kontrast {r["kati_kontrast_en_kotu"]}' + ('' if okun else '  OKUNMAZ'),
               fill=(20, 20, 20) if okun else (170, 20, 20), font=f2)
    u.save(O / 'KONTAK_8.jpg', quality=92)
    print('KONTAK_8.jpg', u.size)


if __name__ == '__main__':
    main()
