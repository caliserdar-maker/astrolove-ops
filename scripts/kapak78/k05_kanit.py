#!/usr/bin/env python3
"""K05 15 oz kenar kusuru ONCE / SONRA kaniti (Serdar 31 Eki, gorev F-A). ETSY YOK.
Girdi: (etiket, eski K05, yeni K05) uclusu; 15 oz kupanin sag kenari (kart koordinati x 2370-2650, y 470-1570) yan yana kirpilir.
Kullanim: k05_kanit.py --cikti ONCE_SONRA_K05_KENAR.jpg "ETIKET|eski.jpg|yeni.jpg" ..."""
import argparse
import sys

from PIL import Image, ImageDraw

KUTU = (2370, 470, 2650, 1570)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", required=True)
    ap.add_argument("ucluler", nargs="+")
    a = ap.parse_args(argv)
    U = [x.rsplit("|", 2) for x in a.ucluler]   # etiket "|" icerebilir: dosya yollari sondan iki alan
    w, h = KUTU[2] - KUTU[0], KUTU[3] - KUTU[1]
    c = Image.new("RGB", (len(U) * (2 * w + 40) + 20, h + 70), (255, 255, 255))
    d = ImageDraw.Draw(c)
    for i, (et, e, y) in enumerate(U):
        x0 = 10 + i * (2 * w + 40)
        for j, (yol, ad) in enumerate(((e, "ONCE"), (y, "SONRA"))):
            c.paste(Image.open(yol).convert("RGB").crop(KUTU), (x0 + j * (w + 10), 60))
            d.text((x0 + j * (w + 10), 30), f"{ad}", fill=(0, 0, 0))
        d.text((x0, 8), et, fill=(0, 0, 0))
    c.save(a.cikti, quality=90)
    print(a.cikti, c.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
