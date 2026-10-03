#!/usr/bin/env python3
"""1:1 kesit (olcekleme yok): [Test 5 | yeni motor], isim satiri ve tagline bantlari. Bant sinirlari sabitlerden
(+-pay), yatayda iki sayfanin murekkep kutularinin birlesimi. Cikti PNG (kayipsiz).

Kullanim: kesit.py --sabit motor/sabitler/X.json --eski test5.jpeg --motor MOTOR.png --cikti DIR
"""
import argparse, json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
FONT = Path(__file__).resolve().parent / 'font' / 'EBGaramond-Italic.ttf'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--eski', required=True)
    ap.add_argument('--motor', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    Z = json.loads(Path(a.sabit).read_text())
    t, m = Image.open(a.eski).convert('RGB'), Image.open(a.motor).convert('RGB')
    W = t.width
    f = ImageFont.truetype(str(FONT), 44)
    for ad, bant, pay in (('ISIM', Z['bantlar']['isim'], 90), ('TAGLINE', Z['bantlar']['mesaj'], 90)):
        y0, y1 = bant[0] - pay, bant[1] + pay
        x0, x1 = int(0.15 * W), int(0.85 * W)
        k = (x0, y0, x1, y1)
        ust = 70
        c = Image.new('RGB', (x1 - x0, 2 * (y1 - y0) + 2 * ust + 20), 'white')
        d = ImageDraw.Draw(c)
        d.text((10, 10), f'TEST 5 ESKI SISTEM (1:1)  x {x0}-{x1}, y {y0}-{y1}', font=f, fill=(40, 30, 20))
        c.paste(t.crop(k), (0, ust))
        y = ust + (y1 - y0) + 20
        d.text((10, y + 10), 'YENI MOTOR (1:1)', font=f, fill=(40, 30, 20))
        c.paste(m.crop(k), (0, y + ust))
        o = Path(a.cikti) / f'KESIT_1e1_{ad}_TEST5_MOTOR.png'
        c.save(o, dpi=(300, 300))
        print(o, c.size)


if __name__ == '__main__':
    main()
