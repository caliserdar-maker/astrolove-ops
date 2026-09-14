#!/usr/bin/env python3
"""Hero uzerine koordinat izgarasi + kenar cetveli (Mo 14 Eyl 2026).

Amac: Serdar'in her edisyon icin kirpma dikdortgenini (x, y, w, h) KAYNAK
piksel cinsinden okuyabilecegi tek PNG. Otomatik tespit yok.

Cizilenler:
  - %5 araliklarla izgara (hem piksel hem yuzde etiketli; her %25'te kalin cizgi)
  - ust ve sol kenarda piksel cetveli
  - merkez artisi
  - Etsy kart orani 4:5 referans dikdortgeni (tam yukseklik, ortali, kesikli)

Kullanim: hero_grid.py --hero ED=yol,... --out OUT
"""
import argparse
import pathlib

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
CETVEL = 96                      # ust/sol cetvel bandi (px)
ADIM = 0.05                      # izgara araligi (goruntu oraninin %5'i)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]


def font(px):
    for f in FONTS:
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


def cizgi(d, xy, ince=(20, 20, 30), dis=(255, 255, 255), kalin=False):
    """Acik/koyu her zeminde okunur cizgi: once beyaz kalin, ustune koyu ince."""
    d.line(xy, fill=dis, width=7 if kalin else 5)
    d.line(xy, fill=ince, width=3 if kalin else 1)


def kesikli(d, kutu, renk=(220, 40, 40), par=28, bos=20, w=5):
    x0, y0, x1, y1 = kutu
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)):
        uzun = max(abs(bx - ax), abs(by - ay))
        n = int(uzun // (par + bos)) + 1
        for i in range(n):
            t0, t1 = i * (par + bos), min(i * (par + bos) + par, uzun)
            if bx != ax:
                d.line([ax + t0, ay, ax + t1, by], fill=renk, width=w)
            else:
                d.line([ax, ay + t0, bx, ay + t1], fill=renk, width=w)


def grid(hero_yolu, ed):
    im = Image.open(hero_yolu).convert("RGB")
    W, H = im.size
    tuval = Image.new("RGB", (W + CETVEL, H + CETVEL), (248, 248, 250))
    tuval.paste(im, (CETVEL, CETVEL))
    d = ImageDraw.Draw(tuval)
    f_k, f_b = font(26), font(30)

    n = int(round(1 / ADIM))
    for i in range(n + 1):
        x = CETVEL + round(W * i * ADIM)
        y = CETVEL + round(H * i * ADIM)
        kalin = i % 5 == 0
        cizgi(d, [x, CETVEL, x, CETVEL + H], kalin=kalin)
        cizgi(d, [CETVEL, y, CETVEL + W, y], kalin=kalin)
        # ust cetvel: piksel + yuzde
        d.line([x, CETVEL - (34 if kalin else 20), x, CETVEL], fill=(40, 40, 50), width=3)
        d.text((x + 5, 6), f"{round(W * i * ADIM)}", font=f_b if kalin else f_k, fill=(20, 20, 30))
        d.text((x + 5, 42), f"%{int(i * ADIM * 100)}", font=f_k, fill=(120, 120, 135))
        # sol cetvel
        d.line([CETVEL - (34 if kalin else 20), y, CETVEL, y], fill=(40, 40, 50), width=3)
        d.text((6, y + 4), f"{round(H * i * ADIM)}", font=f_b if kalin else f_k, fill=(20, 20, 30))
        d.text((6, y + 34), f"%{int(i * ADIM * 100)}", font=f_k, fill=(120, 120, 135))

    # merkez artisi
    cx, cy = CETVEL + W // 2, CETVEL + H // 2
    d.line([cx - 70, cy, cx + 70, cy], fill=(220, 40, 40), width=4)
    d.line([cx, cy - 70, cx, cy + 70], fill=(220, 40, 40), width=4)

    # 4:5 referans (tam yukseklik, ortali)
    rw = round(H * 0.8)
    x0 = CETVEL + (W - rw) // 2
    kesikli(d, (x0, CETVEL, x0 + rw, CETVEL + H))
    d.text((x0 + 12, CETVEL + 12), f"4:5 referans {rw}x{H} (tam yukseklik, ortali)",
           font=f_b, fill=(220, 40, 40))
    d.text((CETVEL + 12, CETVEL + H - 46),
           f"{ed}  kaynak {W}x{H} px  |  izgara %5  |  kutu: x, y, w, h (kaynak px)",
           font=f_b, fill=(20, 20, 30))
    return tuval


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", required=True, help="ED=yol,ED=yol")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for s in a.hero.split(","):
        ed, yol = s.split("=", 1)
        p = out / f"grid_{ed}.png"
        grid(yol, ed).save(p, optimize=True)
        print(f"{p} {p.stat().st_size // 1024} KB {Image.open(p).size}", flush=True)


if __name__ == "__main__":
    main()
