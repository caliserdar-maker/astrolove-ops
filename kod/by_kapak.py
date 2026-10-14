"""Bizim Yilimiz Etsy kapak gorseli (ilk gorsel), Serdar onayi 15 Eki 2026.
Kare 2400x2400, 300 dpi. Bordo radyal gradyan zemin (ortasi acik, ust bant koyu),
ustte "1st Anniversary Gift", altinda "BURC_A  logo  BURC_B" satiri, altta Layers 8x10 poster.
Env: BY_ROOT, PAIR. Girdi: <ROOT>/cikti/<PAIR>/poster/4_Layers_8x10.jpg, <ROOT>/galeri/logo_sonsuz_duz.png
Cikti: <ROOT>/cikti/<PAIR>/vitrin/00_Kapak.jpg (OUT env ile degistirilebilir).
"""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.environ.get("BY_ROOT", "/home/claude/by78")
PAIR = os.environ["PAIR"].upper()
OUT = os.environ.get("OUT", f"{ROOT}/cikti/{PAIR}/vitrin/00_Kapak.jpg")
POSTER = f"{ROOT}/cikti/{PAIR}/poster/4_Layers_8x10.jpg"
LOGO = f"{ROOT}/galeri/logo_sonsuz_duz.png"          # beyaz logo, siyah zemin (maske olarak kullanilir)
FONT = f"{ROOT}/galeri/fonts/CormorantGaramond.ttf"

S = 2400
BASLIK = "1st Anniversary Gift"
GRAD_ORTA, GRAD_KENAR = "8E2630", "34060F"          # radyal gradyan: orta / dis kenar
GRAD_Y = 0.60                                        # acik merkezin dikey konumu (posterin arkasi)
UST_KOYU = 0.22                                      # ust bant koyulastirma (yazilar daha iyi okunsun)
RENK_BASLIK, RENK_SATIR2 = "FFF4E6", "E6C298"        # baslik / burc adlari + logo
LOGO_W = 160                                         # logo genisligi px
POSTER_W = 1360                                      # poster 1360x1700, alt bosluk 90
ALT_BOSLUK = 90
GUVENLI = 0.76                                       # baslik genisligi siniri (Etsy dikey 4:5 kirpma)
SATIR2_GUVENLI = 0.74                                # satir 2 genisligi siniri
SATIR2_MAX = 150                                     # satir 2 en buyuk harf boyu
HARF_ARALIK = 0.05                                   # satir 2 harf araligi (em)
LOGO_BOSLUK = 50                                     # burc adi ile logo arasi


def hx(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def serif(size):
    f = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
    f.set_variation_by_axes([600])
    return f


def zemin():
    rng = np.random.default_rng(4)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.sqrt(((xx - S * 0.5) / (S * 0.72)) ** 2 + ((yy - S * GRAD_Y) / (S * 0.72)) ** 2)
    k = (np.clip(r, 0, 1) ** 1.6)[..., None]
    bg = np.array(hx(GRAD_ORTA), np.float32) * (1 - k) + np.array(hx(GRAD_KENAR), np.float32) * k
    bg *= (1 - UST_KOYU * np.clip(1 - yy / (S * 0.42), 0, 1) ** 1.4)[..., None]
    bg += cv2.GaussianBlur(rng.normal(0, 1, (S, S)).astype(np.float32), (0, 0), 1.3)[..., None] * 255 * 0.018
    return bg


def poster_yerlestir(bg, px, py, pw):
    ph = round(pw * 1.25)
    sh = np.zeros((S, S), np.float32)
    sh[py + 30:py + ph + 30, px + 16:px + pw + 16] = 1
    bg = bg * (1 - cv2.GaussianBlur(sh, (0, 0), 40)[..., None] * 0.5)
    p = np.asarray(Image.open(POSTER).convert("RGB").resize((pw, ph), Image.LANCZOS))
    bg[py:py + ph, px:px + pw] = p
    return bg


def logo_hazirla(renk):
    a = np.asarray(Image.open(LOGO).convert("L")).astype(np.float32) / 255
    al = np.clip((a - 0.25) / 0.5, 0, 1)
    ys, xs = np.where(al > 0.05)
    al = al[max(0, ys.min() - 6):ys.max() + 7, max(0, xs.min() - 6):xs.max() + 7]
    lg = Image.fromarray((al * 255).astype(np.uint8))
    lg = lg.resize((LOGO_W, round(LOGO_W * lg.height / lg.width)), Image.LANCZOS)
    al = np.asarray(lg)
    return Image.fromarray(np.dstack([np.full(al.shape + (3,), renk, np.uint8), al]), "RGBA")


def main():
    a_ad, b_ad = (x.upper() for x in PAIR.split("_"))
    c1, c2 = hx(RENK_BASLIK), hx(RENK_SATIR2)

    s1 = 230
    while serif(s1).getlength(BASLIK, features=["lnum"]) > S * GUVENLI:
        s1 -= 2

    py = S - round(POSTER_W * 1.25) - ALT_BOSLUK
    px = (S - POSTER_W) // 2
    bg = poster_yerlestir(zemin(), px, py, POSTER_W)
    gy = (95 + s1 + py) / 2 + 5

    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((S / 2, 95 + s1 / 2), BASLIK, font=serif(s1), fill=c1, anchor="mm", features=["lnum"])

    def tw(t, f):
        return sum(f.getlength(c) for c in t) + HARF_ARALIK * f.size * (len(t) - 1)

    def yaz(x, t, f):
        for c in t:
            d.text((x, gy), c, font=f, fill=c2, anchor="lm")
            x += f.getlength(c) + HARF_ARALIK * f.size

    ns = SATIR2_MAX
    while tw(a_ad, serif(ns)) + tw(b_ad, serif(ns)) + 2 * LOGO_BOSLUK + LOGO_W > S * SATIR2_GUVENLI:
        ns -= 2
    f2 = serif(ns)
    lg = logo_hazirla(c2)
    top = tw(a_ad, f2) + LOGO_BOSLUK + LOGO_W + LOGO_BOSLUK + tw(b_ad, f2)
    x0 = (S - top) / 2
    yaz(x0, a_ad, f2)
    lx = x0 + tw(a_ad, f2) + LOGO_BOSLUK
    im.paste(lg, (round(lx), round(gy - lg.height / 2)), lg)
    yaz(lx + LOGO_W + LOGO_BOSLUK, b_ad, f2)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    im.save(OUT, quality=95, subsampling=0, dpi=(300, 300))
    print(f"{PAIR}: baslik {s1}px, satir2 {ns}px, poster {POSTER_W}, -> {OUT}")


if __name__ == "__main__":
    main()
