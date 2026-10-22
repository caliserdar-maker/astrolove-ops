#!/usr/bin/env python3
"""BY78 dikey pin V1 (14 Eki 2026, Serdar onayi). YAYIN YOK. 2000x3000 JPG 90.
Zemin assets/pin/PIN_ZEMIN_BOTANIK_MESE.png (1024x1536, Lanczos -> 2000x3000).
8x10 poster (First Page, EMMA / JAMES) kutu x 600-1780 y 765-2240; 5x7 kart kutu x 150-770 y 1665-2533 (posterin ustunde).
Golge: (18,26) blur 40 opaklik 0.35 #3C2819 + temas (0,4) blur 6 opaklik 0.25.
Baslik Cormorant Garamond 600 150 px #352219 ortali: "A little note." ust y=170, "A lasting keepsake." ust y=330.
Alt satir Manrope 500 62 px ortali, ust y = kart alti + 70: "Personalized 1st anniversary gift".
(y degerleri yazinin gorunen ust kenari.) Kullanim:
by78_pin_v1.py --zemin Z.png --fontlar galeri/fonts --girdi DIR (DIR/<CIFT>/{3_FirstPage_8x10,3_FirstPage_5x7}.jpg) --cikti OUT CIFT..."""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2000, 3000
POSTER = (600, 765, 1780, 2240)
KART = (150, 1665, 770, 2533)
RENK = (0x35, 0x22, 0x19)
GOLGE = (0x3C, 0x28, 0x19)


def font(yol, boy, agirlik):
    f = ImageFont.truetype(yol, boy)
    f.set_variation_by_axes([agirlik])
    return f


def golge(zemin, kutu, kayma, blur, opak):
    x0, y0, x1, y1 = kutu
    m = Image.new("L", zemin.size, 0)
    ImageDraw.Draw(m).rectangle((x0 + kayma[0], y0 + kayma[1], x1 - 1 + kayma[0], y1 - 1 + kayma[1]), fill=round(255 * opak))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    zemin.paste(Image.new("RGB", zemin.size, GOLGE), (0, 0), m)


def yerlestir(zemin, yol, kutu):
    x0, y0, x1, y1 = kutu
    im = Image.open(yol).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS)
    golge(zemin, kutu, (18, 26), 40, 0.35)
    golge(zemin, kutu, (0, 4), 6, 0.25)
    zemin.paste(im, (x0, y0))


def yazi(d, metin, f, ust):
    b = d.textbbox((0, 0), metin, font=f)
    d.text(((W - (b[2] - b[0])) / 2 - b[0], ust - b[1]), metin, font=f, fill=RENK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zemin", required=True)
    ap.add_argument("--fontlar", required=True)
    ap.add_argument("--girdi", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("ciftler", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    z = Image.open(a.zemin).convert("RGB")
    if z.size != (W, H):
        z = z.resize((W, H), Image.LANCZOS)
    fb = font(f"{a.fontlar}/CormorantGaramond.ttf", 150, 600)
    fa = font(f"{a.fontlar}/Manrope.ttf", 62, 500)
    hata = 0
    for c in a.ciftler:
        p, k = f"{a.girdi}/{c}/3_FirstPage_8x10.jpg", f"{a.girdi}/{c}/3_FirstPage_5x7.jpg"
        if not (os.path.exists(p) and os.path.exists(k)):
            print("EKSIK", c); hata += 1; continue
        im = z.copy()
        yerlestir(im, p, POSTER)
        yerlestir(im, k, KART)
        d = ImageDraw.Draw(im)
        yazi(d, "A little note.", fb, 170)
        yazi(d, "A lasting keepsake.", fb, 330)
        yazi(d, "Personalized 1st anniversary gift", fa, KART[3] + 70)
        out = f"{a.cikti}/{c}.jpg"
        im.save(out, quality=90)
        r = Image.open(out)
        ok = r.size == (W, H)
        hata += not ok
        print(f"PIN {'PASS' if ok else 'FAIL'} {c} {r.size[0]}x{r.size[1]} {os.path.getsize(out) / 1e6:.2f} MB")
    print(f"PIN SONUC {len(a.ciftler) - hata}/{len(a.ciftler)}")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
