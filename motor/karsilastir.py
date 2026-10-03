#!/usr/bin/env python3
"""Yan yana TAM SAYFA karsilastirma (kesit yok): [orijinal satis posteri | Test 5 eski sistem | yeni motor].
Her sayfa 1:1 (300 dpi, olcekleme yok), ustte etiket seridi. Cikti PNG.

Kullanim: karsilastir.py --orijinal A.jpg --eski B.jpeg --motor C.png --cikti YANYANA.png
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
FONT = Path(__file__).resolve().parent / 'font' / 'EBGaramond-Italic.ttf'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orijinal', required=True)
    ap.add_argument('--eski', required=True)
    ap.add_argument('--motor', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--jpg', help='ayrica JPG (tam sayfa, < 10 MB: kalite 92..60, gerekirse olcek kuculur)')
    a = ap.parse_args()
    sayfa = [('ORIJINAL SATIS POSTERI (SCORPIO_VIRGO WARM_PARCHMENT 11x14)', a.orijinal),
             ('TEST 5 ESKI SISTEM (siparis-dijital, 9000000005 sayfa 4)', a.eski),
             ('YENI MOTOR (katmanlardan, temiz zemin)', a.motor)]
    ims = [Image.open(f).convert('RGB') for _, f in sayfa]
    W, H = ims[0].size
    if any(im.size != (W, H) for im in ims):
        raise SystemExit(f'FAIL: sayfa olculeri farkli {[im.size for im in ims]}')
    ara, ust = 60, 160
    c = Image.new('RGB', (3 * W + 2 * ara, H + ust), 'white')
    d = ImageDraw.Draw(c)
    f = ImageFont.truetype(str(FONT), 72)
    for i, ((ad, _), im) in enumerate(zip(sayfa, ims)):
        x = i * (W + ara)
        c.paste(im, (x, ust))
        d.text((x + 20, 40), ad, font=f, fill=(40, 30, 20))
    c.save(a.cikti, dpi=(300, 300))
    print(a.cikti, c.size)
    if a.jpg:
        sinir = 10 * 1024 * 1024
        olcek = 1.0
        while True:
            im = c if olcek == 1.0 else c.resize((int(c.width * olcek), int(c.height * olcek)), Image.LANCZOS)
            for q in (92, 88, 85, 80, 75, 70, 65, 60):
                im.save(a.jpg, 'JPEG', quality=q, subsampling=0 if q >= 85 else 2, dpi=(300 * olcek,) * 2)
                if Path(a.jpg).stat().st_size < sinir:
                    print(a.jpg, im.size, 'kalite', q, 'olcek', olcek, Path(a.jpg).stat().st_size)
                    return
            olcek *= 0.8


if __name__ == '__main__':
    main()
