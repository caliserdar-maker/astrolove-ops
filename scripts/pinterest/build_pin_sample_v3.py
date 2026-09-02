#!/usr/bin/env python3
"""
Pinterest pin gorseli V3 ornegi: POSTERIN KENDISI (mockup yok), 4 filigran turu.
Toplu uretim degildir.

Kaynak: WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/<EDISYON>/2X3/
        WA_POSTER_<PAIR>_<EDISYON>_2X3.jpg (tam 2:3, kirpma yok)
Cikti:  1000x1500 JPG kalite 85, LANCZOS, 4:4:4 (subsampling 0)

Filigran turleri:
  F1  KOSE METIN  sag alt, "AstroLove" ince serif, genislik %9, opaklik %50
  F2  KOSE LOGO   sag alt, sonsuzluk isareti (BRAND/ASTROLOVE_LOGO_3000.png'den
                  arka plan ayiklanarak), yukseklik %5, opaklik %50
  F3  DOKU        tum yuzeye capraz tekrarlayan "AstroLove", genislik %4,
                  opaklik %12, 45 derece
  F4  ALT BANT    en altta %6 yukseklikte bant, posterin alt kenar renginde,
                  ortada "ASTROLOVE · astrolove.art" harf aralikli

Filigran rengi: koyu posterde altin/acik, acik posterde edisyon murekkebi
(build_carousel.CTA_COLORS olcumleri). Ciktilar: 8 tam boy + edisyon basina
kontak sayfasi + her filigranin 300x300 yakin cekimi. Drive: TEMP/PIN_SAMPLE_V3/<PAIR>/
"""

import argparse
import glob
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "instagram"))
import build_carousel as bc  # noqa: E402  (rclone, lsf, fetch, match_pair, push_dir)

Image.MAX_IMAGE_PIXELS = None

OUT_W, OUT_H = 1000, 1500
JPEG_OPTS = dict(quality=85, subsampling=0, optimize=True, dpi=(72, 72))
POSTER_DIR = f"{bc.ROOT}/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION"
LOGO_PATH = f"{bc.ROOT}/BRAND/ASTROLOVE_LOGO_3000.png"
OUT_DIR = f"{bc.ROOT}/TEMP/PIN_SAMPLE_V3"
INSET = 30
GOLD = (208, 164, 67)          # koyu edisyon altin (MIDNIGHT_BLUE CTA olcumu)
PALETTE = bc.CTA_COLORS         # edisyon -> (zemin, murekkep)

FONT_DIRS = ["/usr/share/fonts/truetype/ebgaramond", "/usr/share/fonts/opentype/ebgaramond",
             "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation"]


def log(msg):
    print(msg, flush=True)


def find_font(patterns):
    for d in FONT_DIRS:
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(d, pat)))
            if hits:
                return hits[0]
    raise SystemExit(f"HATA: font yok: {patterns}")


def font_size_for_width(path, text, width, track=0.0):
    size = 8
    while True:
        f = ImageFont.truetype(path, size + 1)
        if tracked_width(f, text, track * (size + 1)) > width:
            return ImageFont.truetype(path, size)
        size += 1


def tracked_width(font, text, track):
    return sum(font.getlength(c) for c in text) + track * (len(text) - 1)


def draw_tracked(d, x, y, text, font, track, fill):
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + track


# ------------------------------------------------------------- renk kurali
def is_dark(img):
    return float(np.asarray(img.convert("L").resize((50, 75))).mean()) < 110


def wm_color(img, edition):
    """Koyu posterde altin, acik posterde edisyon murekkebi."""
    if is_dark(img):
        return GOLD, "altin (koyu poster)"
    return PALETTE[edition][1], "edisyon murekkebi (acik poster)"


def composite(img, layer):
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# ----------------------------------------------------------------- filigran
def f1_corner_text(img, color, font_reg):
    f = font_size_for_width(font_reg, "AstroLove", OUT_W * 0.09)
    tw = f.getlength("AstroLove")
    asc, desc = f.getmetrics()
    x, y = OUT_W - INSET - tw, OUT_H - INSET - (asc + desc)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((x, y), "AstroLove", font=f, fill=color + (128,))
    return composite(img, layer), (int(x), int(y), OUT_W - INSET, OUT_H - INSET), f"{f.size}pt"


def logo_mask(logo_png):
    """Altin sonsuzluk isaretini gece mavisi zeminden ayirir: alfa = zeminden uzaklik."""
    a = np.asarray(Image.open(logo_png).convert("RGB")).astype(np.int16)
    bg = np.median(np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3)]), axis=0)
    d = np.abs(a - bg).sum(2)
    alpha = np.clip((d - 30) / 90.0, 0, 1)                 # 30..120 arasi yumusak gecis
    ys, xs = np.where(alpha > 0.5)
    m = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    return m.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def f2_corner_logo(img, color, mask):
    h = int(round(OUT_H * 0.05))
    w = int(round(mask.width * h / mask.height))
    m = mask.resize((w, h), Image.LANCZOS)
    m = m.point(lambda v: v * 128 // 255)                   # opaklik %50
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = OUT_W - INSET - w, OUT_H - INSET - h
    layer.paste(Image.new("RGBA", (w, h), color + (255,)), (x, y), m)
    return composite(img, layer), (x, y, x + w, y + h), f"{w}x{h}px"


def f3_texture(img, color, font_reg):
    f = font_size_for_width(font_reg, "AstroLove", OUT_W * 0.04)
    tw = f.getlength("AstroLove")
    th = sum(f.getmetrics())
    # Buyuk tuvale dizip 45 derece dondur, merkezden kirp.
    side = int((OUT_W ** 2 + OUT_H ** 2) ** 0.5) + 200
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    sx, sy = tw * 1.9, th * 3.2
    row = 0
    y = 0
    while y < side:
        x = (sx / 2) if row % 2 else 0
        while x < side:
            d.text((x, y), "AstroLove", font=f, fill=color + (int(255 * 0.12),))
            x += sx
        y += sy
        row += 1
    tile = tile.rotate(45, resample=Image.BICUBIC, expand=False)
    ox, oy = (side - OUT_W) // 2, (side - OUT_H) // 2
    layer = tile.crop((ox, oy, ox + OUT_W, oy + OUT_H))
    return composite(img, layer), (OUT_W // 2 - 75, OUT_H // 2 - 75, OUT_W // 2 + 75, OUT_H // 2 + 75), f"{f.size}pt adim {sx:.0f}x{sy:.0f}"


def f4_bottom_band(img, color, font_reg):
    band_h = int(round(OUT_H * 0.06))
    edge = np.asarray(img.crop((0, OUT_H - 12, OUT_W, OUT_H)).resize((50, 2))).reshape(-1, 3).mean(0)
    zemin = tuple(int(v) for v in edge)
    out = img.copy()
    d = ImageDraw.Draw(out)
    d.rectangle((0, OUT_H - band_h, OUT_W, OUT_H), fill=zemin)
    text = "ASTROLOVE · astrolove.art"
    f = ImageFont.truetype(font_reg, max(18, int(band_h * 0.40)))
    track = f.size * 0.22
    tw = tracked_width(f, text, track)
    asc, desc = f.getmetrics()
    x = (OUT_W - tw) / 2
    y = OUT_H - band_h / 2 - (asc - desc) / 2
    draw_tracked(d, x, y, text, f, track, color)
    return out, (OUT_W // 2 - 150, OUT_H - band_h - 60, OUT_W // 2 + 150, OUT_H), f"bant {band_h}px zemin {zemin}, {f.size}pt"


def close_up(img, box, name, out):
    """Kutunun etrafindan 150x150 (veya bant icin 300x150) alip 300x300'e buyutur."""
    cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    x0 = min(max(cx - 75, 0), OUT_W - 150)
    y0 = min(max(cy - 75, 0), OUT_H - 150)
    img.crop((x0, y0, x0 + 150, y0 + 150)).resize((300, 300), Image.LANCZOS).save(out / name, "JPEG", quality=95)


def contact_sheet(paths, labels, font_reg, title):
    cw, ch, band = 250, 375, 34
    sheet = Image.new("RGB", (cw * len(paths) + 10 * (len(paths) - 1), ch + band * 2), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(font_reg, 18)
    d.text((6, 6), title, font=f, fill=(20, 20, 20))
    x = 0
    for p, lab in zip(paths, labels):
        sheet.paste(Image.open(p).resize((cw, ch), Image.LANCZOS), (x, band * 2))
        d.text((x + 6, band + 8), lab, font=f, fill=(20, 20, 20))
        x += cw + 10
    return sheet


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="CAPRICORN_VIRGO")
    ap.add_argument("--editions", default="WARM_PARCHMENT,MIDNIGHT_BLUE")
    ap.add_argument("--src", help="yerel klasor: WA_POSTER_<PAIR>_<ED>_2X3.jpg + ASTROLOVE_LOGO_3000.png (Drive yerine)")
    ap.add_argument("--work", default="_work")
    ap.add_argument("--out", default="_out")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()

    font_reg = find_font(["EBGaramond12-Regular.*", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"])
    log(f"font: {os.path.basename(font_reg)}")
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) / a.pair; out.mkdir(parents=True, exist_ok=True)

    logo = Path(a.src) / "ASTROLOVE_LOGO_3000.png" if a.src else bc.fetch(LOGO_PATH, work)
    mask = logo_mask(logo)
    log(f"logo maskesi: {mask.size} (en/boy {mask.width/mask.height:.2f})")

    rows = []
    for ed in [e.strip() for e in a.editions.split(",") if e.strip()]:
        if a.src:
            src = Path(a.src) / f"WA_POSTER_{a.pair}_{ed}_2X3.jpg"
        else:
            pdir = f"{POSTER_DIR}/{ed}/2X3"
            src = bc.fetch(f"{pdir}/{bc.match_pair(bc.lsf(pdir), a.pair)}", work)
        poster = Image.open(src).convert("RGB")
        ratio = poster.width / poster.height
        note = "" if abs(ratio - 2 / 3) < 0.003 else f"kaynak orani {ratio:.4f} != 2:3"
        base = poster.resize((OUT_W, OUT_H), Image.LANCZOS)
        color, why = wm_color(base, ed)
        log(f"{ed}: kaynak {poster.size}, filigran rengi {color} {why} {note}")

        variants = [
            ("F1_KOSE_METIN", lambda: f1_corner_text(base, color, font_reg)),
            ("F2_KOSE_LOGO",  lambda: f2_corner_logo(base, color, mask)),
            ("F3_DOKU",       lambda: f3_texture(base, color, font_reg)),
            ("F4_ALT_BANT",   lambda: f4_bottom_band(base, color, font_reg)),
        ]
        paths = []
        for name, fn in variants:
            img, box, info = fn()
            p = out / f"{a.pair}_{ed}_{name}.jpg"
            img.save(p, "JPEG", **JPEG_OPTS)
            close_up(img, box, f"{a.pair}_{ed}_{name}_YAKIN_300.jpg", out)
            paths.append(p)
            rows.append((ed, name, f"{color}", info, note))
            log(f"  {name}: {info}")
        contact_sheet(paths, [v[0] for v in variants], font_reg, f"{a.pair} · {ed}").save(
            out / f"{a.pair}_{ed}_KONTAK.jpg", "JPEG", quality=90)

    files = sorted(p.name for p in out.iterdir())
    if not a.no_upload:
        bc.push_dir(out, f"{OUT_DIR}/{a.pair}")
        log(f"yuklendi: {OUT_DIR}/{a.pair}/ ({len(files)} dosya)")

    lines = [f"## PIN_SAMPLE_V3 {a.pair}", "", f"Drive: `{OUT_DIR}/{a.pair}/`", "",
             "| Edisyon | Filigran | Renk | Detay | Not |", "|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines += ["", "Dosyalar: " + ", ".join(files)]
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
