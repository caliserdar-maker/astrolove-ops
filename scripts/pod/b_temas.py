#!/usr/bin/env python3
"""B goz kontrolu temas sayfasi (Serdar 24 Eki madde 3): galeri23-duzelt kosusunun KART/ONCE_SONRA/NN.jpg gorselleri (sol once,
sag sonra) tek sayfada, her satir ilan / cift / kart etiketli, kart yazisi okunur boyutta (ONCE_SONRA ozgun cozunurlugu).
Etsy YOK. Girdi: --dir altinda <ilan>_<CIFT>_<NN>.jpg dosyalari, --sira (virgullu <ilan>_<CIFT>_<NN>)."""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--sira", required=True)
    ap.add_argument("--baslik", default="")
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sira = [s for s in a.sira.split(",") if s]
    imgs = [Image.open(os.path.join(a.dir, f"{s}.jpg")).convert("RGB") for s in sira]
    f, f2 = ImageFont.truetype(a.font, 46), ImageFont.truetype(a.font, 30)
    W, BAS, ETK = max(i.width for i in imgs), 150, 90
    S = Image.new("RGB", (W, BAS + sum(i.height + ETK for i in imgs)), "white")
    d = ImageDraw.Draw(S)
    for n, sat in enumerate(a.baslik.split("|")[:2]):
        d.text((30, 25 + 50 * n), sat, font=f2, fill="black")
    y = BAS
    for s, im in zip(sira, imgs):
        lid, rest = s.split("_", 1)
        cift, k = rest.rsplit("_", 1)
        d.rectangle([0, y, W, y + ETK - 8], fill=(235, 235, 235))
        d.text((30, y + 18), f"{lid}  {cift}  kart {int(k)}", font=f, fill="black")
        S.paste(im, (0, y + ETK)); y += ETK + im.height
    S.save(a.out, quality=88)
    print("TEMAS", S.size, len(sira), "satir")


if __name__ == "__main__":
    main()
