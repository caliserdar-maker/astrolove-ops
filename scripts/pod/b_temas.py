#!/usr/bin/env python3
"""B goz kontrolu temas sayfasi (Serdar 24 Eki madde 3): galeri23-duzelt kosusunun KART/ONCE_SONRA/NN.jpg gorselleri (sol once,
sag sonra) tek sayfada, her satir ilan / cift / kart etiketli, kart yazisi okunur boyutta (ONCE_SONRA ozgun cozunurlugu).
Etsy YOK. Girdi: --dir altinda <ilan>_<CIFT>_<NN>.jpg dosyalari, --sira (virgullu <ilan>_<CIFT>_<NN>).
--sutun (Serdar 24 Eki, 22 ilan hazirlik 4b): --sira virgullu <ilan>_<CIFT>; her satir bir ilan, sutunlar --sutun kartlari (orn. 04,09)
yan yana, her kart --kart-gen genislige olceklenir (3000x2250 -> 1500x1125, ONCE_SONRA yarisi ile ayni olcek); QC cercevesi yok
(KART/NN_*.jpg son gorseller). Ayni burclu cift (A_A) etikette "AYNI BURC" ile isaretlenir."""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont


def temas_once_sonra(a, f, f2):
    sira = [s for s in a.sira.split(",") if s]
    imgs = [Image.open(os.path.join(a.dir, f"{s}.jpg")).convert("RGB") for s in sira]
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
    return S, len(sira)


def temas_sutun(a, f, f2):
    sira = [s for s in a.sira.split(",") if s]
    sut = [k for k in a.sutun.split(",") if k]
    GW, ARA, BAS, ETK = a.kart_gen, 20, 150, 90
    satir = []
    for s in sira:
        ims = []
        for k in sut:
            im = Image.open(os.path.join(a.dir, f"{s}_{k}.jpg")).convert("RGB")
            ims.append(im.resize((GW, round(im.height * GW / im.width)), Image.LANCZOS))
        satir.append((s, ims))
    W = len(sut) * GW + (len(sut) - 1) * ARA
    S = Image.new("RGB", (W, BAS + sum(ETK + max(i.height for i in ims) for _, ims in satir)), "white")
    d = ImageDraw.Draw(S)
    for n, sat in enumerate(a.baslik.split("|")[:2]):
        d.text((30, 25 + 50 * n), sat, font=f2, fill="black")
    y = BAS
    for s, ims in satir:
        lid, cift = s.split("_", 1)
        b1, b2 = cift.split("_")
        d.rectangle([0, y, W, y + ETK - 8], fill=(255, 226, 160) if b1 == b2 else (235, 235, 235))
        d.text((30, y + 18), f"{lid}  {cift}" + ("   AYNI BURC" if b1 == b2 else ""), font=f, fill="black")
        for j, (k, im) in enumerate(zip(sut, ims)):
            x = j * (GW + ARA)
            d.text((x + GW - 220, y + 24), f"kart {int(k)}", font=f2, fill="black")
            S.paste(im, (x, y + ETK))
        y += ETK + max(i.height for i in ims)
    return S, len(satir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--sira", required=True)
    ap.add_argument("--baslik", default="SOL = 17 Eki hedef galeri yedegi (once), SAG = duzeltilmis (sonra). Kirmizi cerceve = degisen "
                    "satir kutusu (QC isareti, asil gorselde yok)")
    ap.add_argument("--sutun", default="", help="bos: once/sonra satirlari; orn. 04,09: ilan basina bir satir, kartlar yan yana")
    ap.add_argument("--kart-gen", type=int, default=1500)
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    f, f2 = ImageFont.truetype(a.font, 46), ImageFont.truetype(a.font, 30)
    S, n = temas_sutun(a, f, f2) if a.sutun else temas_once_sonra(a, f, f2)
    S.save(a.out, quality=88)
    print("TEMAS", S.size, n, "satir")


if __name__ == "__main__":
    main()
