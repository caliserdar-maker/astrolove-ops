"""Bizim Yilimiz vitrin gorselleri (Serdar 14 Eki): poster kirik beyaz zeminde, 4 kenarda ince bosluk + hafif golge.
01_Cover.jpg = 4_Layers posteri; Starlit / Timeless / First Page / Botanical icin ayni duzende stil gorselleri.
Env: BY_ROOT, PAIR. Girdi: <ROOT>/cikti/<PAIR>/poster/<stil>_8x10.jpg. Cikti: <ROOT>/cikti/<PAIR>/vitrin/*.jpg (2400x3000, 300 dpi).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.environ.get("BY_ROOT", "/home/claude/by78")
PAIR = os.environ["PAIR"]
SRC = f"{ROOT}/cikti/{PAIR}/poster"
OUT = os.environ.get("OUT", f"{ROOT}/cikti/{PAIR}/vitrin")
W, H = 2400, 3000
ZEMIN = (246, 244, 240)          # kirik beyaz #F6F4F0
KENAR = 140                      # yatay bosluk; poster 2120x2650, dikey bosluk 175
GOLGE = (((14, 22), 36, 0.30), ((0, 3), 5, 0.22))
GOLGE_RENK = (70, 50, 35)
DOSYALAR = {"01_Cover.jpg": "4_Layers", "Style_Starlit.jpg": "1_Starlit", "Style_Timeless.jpg": "2_Timeless",
            "Style_FirstPage.jpg": "3_FirstPage", "Style_Botanical.jpg": "5_Botanical"}


def zemin():
    rng = np.random.default_rng(5)
    n = Image.fromarray(np.clip(rng.normal(0, 1, (H, W)) * 255, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))
    a = np.array(Image.new("RGB", (W, H), ZEMIN)).astype(float) + (np.array(n).astype(float)[..., None] - 128) * 0.03
    a *= (1 - 0.04 * np.linspace(0, 1, H)[:, None, None])
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def vitrin(poster):
    pw = W - 2 * KENAR
    ph = round(pw * 1.25)
    x0, y0 = KENAR, (H - ph) // 2
    bg = zemin()
    for off, blur, op in GOLGE:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((x0 + off[0], y0 + off[1], x0 + pw + off[0], y0 + ph + off[1]), fill=round(255 * op))
        bg = Image.composite(Image.new("RGB", (W, H), GOLGE_RENK), bg, m.filter(ImageFilter.GaussianBlur(blur)))
    bg.paste(poster.resize((pw, ph), Image.LANCZOS), (x0, y0))
    return bg


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for ad, stil in DOSYALAR.items():
        p = Image.open(f"{SRC}/{stil}_8x10.jpg").convert("RGB")
        assert p.size == (2400, 3000), (stil, p.size)
        vitrin(p).save(f"{OUT}/{ad}", quality=95, subsampling=0, dpi=(300, 300))
        print(ad)
