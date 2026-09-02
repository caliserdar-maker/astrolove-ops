#!/usr/bin/env python3
"""
Pinterest pin gorseli YENIDEN TASARIM ornegi (V2): 1 ilan, 4 varyant.
Toplu uretim degildir.

Kaynak: WALL_ART/LISTING_MEDIA/MOCKUPS/<sahne>/<edisyon>/WA_xx_MOCKUP_<PAIR>_<ED>.jpg
(3000x2250). Poster, IG carousel'deki FARK yontemiyle bulunur
(scripts/instagram/build_carousel.py: ayni sahnenin baska bir cifti referans).

Ortak: cikti 1000x1500 (2:3), JPG kalite 85. Filigran sag alt kose, genislik
gorselin %9'u, opaklik %50, ince serif "AstroLove", kenardan 30 px iceride.
Capraz buyuk filigran YOK.

Varyantlar:
  V1   ANA     WA_11 (yere yasli). Ust %15 bant: "CAPRICORN & VIRGO" buyuk,
               altinda "Zodiac Wall Art" kucuk; zemin sahne rengine uyumlu.
  V1b  ANA     ayni sahne, overlay yok (A/B kontrol).
  V2   HEDIYE  WA_03 (masa, kadehler). Bant: "Gift for Couples".
  V3   DEKOR   WA_12 (konsol), genis kadraj (tam yukseklik), overlay yok.

Ciktilar: 4 tam boy + KONTAK (yan yana) + FILIGRAN_YAKIN_300 (300x300).
Drive: TEMP/PIN_SAMPLE_V2/<PAIR>_<ED>/
"""

import argparse
import glob
import os
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "instagram"))
import build_carousel as bc  # noqa: E402  (rclone, lsf, fetch, match_pair, pick_reference)

Image.MAX_IMAGE_PIXELS = None

OUT_W, OUT_H = 1000, 1500
JPEG_OPTS = dict(quality=85, optimize=True, dpi=(72, 72))
OUT_DIR = f"{bc.ROOT}/TEMP/PIN_SAMPLE_V2"
BAND_RATIO = 0.15
WM_WIDTH_RATIO = 0.09
WM_ALPHA = 128            # %50
WM_INSET = 30

SCENES = {
    "WA_11": "11_FLOOR_LEANING__POSTER_2X3",
    "WA_03": "03_LIVED_IN_LOVE__POSTER_2X3",
    "WA_12": "12_DESK_SIDE__POSTER_2X3",
}
# (dosya adi, sahne, pencere yuksekligi/kaynak yuksekligi, overlay satirlari)
VARIANTS = [
    ("V1_ANA",             "WA_11", 0.92, ("{S1} & {S2}", "Zodiac Wall Art")),
    ("V1b_ANA_OVERLAYSIZ", "WA_11", 0.92, None),
    ("V2_HEDIYE",          "WA_03", 0.92, ("Gift for Couples", None)),
    ("V3_DEKOR",           "WA_12", 1.00, None),
]

# Edisyon zemin/murekkep (build_carousel CTA_COLORS ile ayni olcumler)
PALETTE = bc.CTA_COLORS

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


def fonts():
    reg = find_font(["EBGaramond12-Regular.*", "EBGaramond-Regular.*", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"])
    ita = find_font(["EBGaramond12-Italic.*", "EBGaramond-Italic.*", "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf",
                     "DejaVuSerif.ttf"])
    log(f"font: {os.path.basename(reg)} / {os.path.basename(ita)}")
    return reg, ita


# ------------------------------------------------------------ poster tespiti
def detect_bbox(target, reference):
    """Fark yontemi: posterin kaynak koordinatlarinda sinir kutusu (veya None)."""
    A = np.asarray(Image.open(target).convert("L").resize((750, 562), Image.LANCZOS), np.float32)
    B = np.asarray(Image.open(reference).convert("L").resize((750, 562), Image.LANCZOS), np.float32)
    W, H = Image.open(target).size
    d = ndimage.binary_closing(np.abs(A - B) > 18, np.ones((15, 15)))
    frac = d.mean()
    lab, n = ndimage.label(d)
    if n == 0 or not (0.002 <= frac <= 0.25):
        return None, f"fark alani %{frac*100:.1f} sinir disi"
    big = int(np.argmax(ndimage.sum(d, lab, range(1, n + 1)))) + 1
    ys, xs = np.where(lab == big)
    sx, sy = W / 750, H / 562
    return (xs.min() * sx, ys.min() * sy, (xs.max() + 1) * sx, (ys.max() + 1) * sy), f"fark %{frac*100:.1f}"


def crop_2x3(img, bbox, h_ratio, band):
    """Poster merkezli 2:3 pencere. band=True ise posteri ust bandin altina yerlestirir."""
    W, H = img.size
    ch = H * h_ratio
    cw = ch * 2 / 3
    if bbox:
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
    else:
        cx, cy = W / 2, H / 2
    left = min(max(cx - cw / 2, 0), W - cw)
    top = min(max(cy - ch / 2, 0), H - ch)
    note = None
    if band and bbox:
        # Poster ustu bandin altinda kalsin: once pencereyi yukari kaydir; kaynak
        # yetmezse pencereyi kucult (yakinlas), poster cikti icinde asagi iner.
        pw = bbox[2] - bbox[0]
        placed = False
        h = h_ratio
        while h >= 0.55:
            ch = H * h
            cw = ch * 2 / 3
            band_src = ch * BAND_RATIO
            margin = ch * 0.03
            top2 = min(max(bbox[1] - band_src - margin, 0), H - ch)
            if (bbox[1] - top2 >= band_src + margin and top2 + ch >= bbox[3] + margin
                    and cw >= pw + 2 * margin):
                top = top2
                left = min(max(cx - cw / 2, 0), W - cw)
                placed = True
                break
            h -= 0.02
        if not placed:
            ch = H * h_ratio
            cw = ch * 2 / 3
            left = min(max(cx - cw / 2, 0), W - cw)
            top = min(max(cy - ch / 2, 0), H - ch)
            note = "poster bant altina sigmiyor, merkez kirpma"
        elif h < h_ratio:
            note = f"bant icin pencere {h:.2f}H'ye kucultuldu"
    box = tuple(int(round(v)) for v in (left, top, left + cw, top + ch))
    out = img.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS)
    sc = OUT_W / cw
    pb = None
    if bbox:
        pb = ((bbox[0] - box[0]) * sc, (bbox[1] - box[1]) * sc, (bbox[2] - box[0]) * sc, (bbox[3] - box[1]) * sc)
    return out, pb, note


# ------------------------------------------------------------------ overlay
def blend(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def tracked_width(font, text, track):
    return sum(font.getlength(c) for c in text) + track * (len(text) - 1)


def draw_tracked(d, xy_center, text, font, track, fill):
    x = xy_center[0] - tracked_width(font, text, track) / 2
    asc, desc = font.getmetrics()
    y = xy_center[1] - (asc - desc) / 2
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + track


def add_band(img, lines, edition, font_reg, font_ita):
    """Ust %15 bant: zemin = sahnenin o bolgesinin ortalama rengi ile edisyon zemininin karisimi."""
    bg_ed, ink = PALETTE[edition]
    band_h = int(round(OUT_H * BAND_RATIO))
    region = np.asarray(img.crop((0, 0, OUT_W, band_h)).resize((50, 8))).reshape(-1, 3).mean(0)
    scene = tuple(int(v) for v in region)
    zemin = blend(scene, bg_ed, 0.55)
    # Cok koyu/acik uclari edisyon zeminine yaklastir (metin kontrasti icin).
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, OUT_W, band_h), fill=zemin)
    d.line((0, band_h - 1, OUT_W, band_h - 1), fill=blend(zemin, ink, 0.35), width=1)

    big, small = lines
    big = big.upper()
    # Buyuk satir: poster tipografisi gibi bosluklu buyuk harf serif; genislik bandin %78'ini gecmesin.
    size = 96
    while size > 24:
        f = ImageFont.truetype(font_reg, size)
        track = size * 0.12
        if tracked_width(f, big, track) <= OUT_W * 0.78:
            break
        size -= 2
    fb = ImageFont.truetype(font_reg, size)
    if small:
        fs = ImageFont.truetype(font_ita, max(26, int(size * 0.42)))
        gap = size * 0.18
        total = size + gap + fs.size
        y0 = band_h / 2 - total / 2
        draw_tracked(d, (OUT_W / 2, y0 + size / 2), big, fb, size * 0.12, ink)
        draw_tracked(d, (OUT_W / 2, y0 + size + gap + fs.size / 2), small, fs, 1.5, ink)
    else:
        draw_tracked(d, (OUT_W / 2, band_h / 2), big, fb, size * 0.12, ink)
    return img, zemin, size


def add_watermark(img, font_reg, edition):
    """Sag alt kose, genislik %9, opaklik %50, ince serif 'AstroLove', 30 px iceride."""
    target_w = OUT_W * WM_WIDTH_RATIO
    size = 10
    while True:
        f = ImageFont.truetype(font_reg, size + 1)
        if f.getlength("AstroLove") > target_w:
            break
        size += 1
    f = ImageFont.truetype(font_reg, size)
    tw = f.getlength("AstroLove")
    asc, desc = f.getmetrics()
    th = asc + desc
    x = OUT_W - WM_INSET - tw
    y = OUT_H - WM_INSET - th
    # Renk: bolge acik ise edisyon murekkebi, koyu ise beyaz.
    reg = np.asarray(img.crop((int(x), int(y), OUT_W - WM_INSET, OUT_H - WM_INSET)).convert("L"))
    lum = float(reg.mean()) if reg.size else 128.0
    ink = PALETTE[edition][1]
    color = (255, 255, 255) if lum < 140 else ink
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((x, y), "AstroLove", font=f, fill=color + (WM_ALPHA,))
    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return out, (int(x), int(y), int(x + tw), int(y + th)), size, color, lum


# ------------------------------------------------------------------- kontak
def contact_sheet(paths, labels, font_reg):
    cw, ch, band = 300, 450, 34
    sheet = Image.new("RGB", (cw * len(paths) + 10 * (len(paths) - 1), ch + band), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(font_reg, 18)
    x = 0
    for p, lab in zip(paths, labels):
        sheet.paste(Image.open(p).resize((cw, ch), Image.LANCZOS), (x, band))
        d.text((x + 6, 8), lab, font=f, fill=(20, 20, 20))
        x += cw + 10
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="CAPRICORN_VIRGO")
    ap.add_argument("--edition", default="WARM_PARCHMENT")
    ap.add_argument("--src", help="yerel mockup klasoru (verilirse Drive'dan indirilmez; WA_xx_MOCKUP_*.jpg)")
    ap.add_argument("--work", default="_work")
    ap.add_argument("--out", default="_out")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()

    s1, s2 = a.pair.split("_")
    font_reg, font_ita = fonts()
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    tag = f"{a.pair}_{a.edition}"
    out = Path(a.out) / tag; out.mkdir(parents=True, exist_ok=True)
    rows, produced = [], {}

    for name, scene, h_ratio, overlay in VARIANTS:
        if scene in produced and produced[scene][0] is not None:
            tgt, ref = produced[scene]
        else:
            if a.src:
                names = sorted(os.listdir(a.src))
                names = [n for n in names if n.startswith(f"{scene}_")]
                tgt = Path(a.src) / bc.match_pair(names, a.pair)
                ref = Path(a.src) / bc.pick_reference(names, a.pair)
            else:
                sdir = f"{bc.SCENE_ROOT}/{SCENES[scene]}/{a.edition}"
                names = bc.lsf(sdir)
                tgt = bc.fetch(f"{sdir}/{bc.match_pair(names, a.pair)}", work)
                ref = bc.fetch(f"{sdir}/{bc.pick_reference(names, a.pair)}", work)
            produced[scene] = (tgt, ref)
        img = Image.open(tgt).convert("RGB")
        bbox, info = detect_bbox(tgt, ref)
        pin, pb, note = crop_2x3(img, bbox, h_ratio, band=overlay is not None)
        band_info = ""
        if overlay:
            lines = (overlay[0].format(S1=s1.title(), S2=s2.title()), overlay[1])
            pin, zemin, size = add_band(pin, lines, a.edition, font_reg, font_ita)
            band_info = f"bant zemin {zemin}, punto {size}"
            if pb and pb[1] < OUT_H * BAND_RATIO:
                note = (note + "; " if note else "") + f"poster ustu bant altinda kaliyor ({pb[1]:.0f}px)"
        pin, wm_box, wm_size, wm_color, lum = add_watermark(pin, font_reg, a.edition)
        path = out / f"{tag}_{name}.jpg"
        pin.save(path, "JPEG", **JPEG_OPTS)
        rows.append((name, scene, info, f"{wm_size}pt {wm_color} lum {lum:.0f}", band_info, note or ""))
        log(f"{name}: {scene} | {info} | filigran {wm_size}pt {wm_color} | {band_info} | {note or ''}")
        if name == "V1_ANA":
            x0, y0 = wm_box[0] - 30, wm_box[1] - 60
            close = pin.crop((max(0, x0), max(0, y0), OUT_W, OUT_H))   # ~150x120 kose
            side = max(close.size)
            sq = Image.new("RGB", (side, side), (0, 0, 0))
            sq.paste(close, (side - close.width, side - close.height))
            sq.resize((300, 300), Image.LANCZOS).save(out / f"{tag}_FILIGRAN_YAKIN_300.jpg", "JPEG", quality=95)

    paths = [out / f"{tag}_{v[0]}.jpg" for v in VARIANTS]
    contact_sheet(paths, [v[0] for v in VARIANTS], font_reg).save(out / f"{tag}_KONTAK.jpg", "JPEG", quality=90)

    files = sorted(p.name for p in out.iterdir())
    if not a.no_upload:
        bc.push_dir(out, f"{OUT_DIR}/{tag}")
        log(f"yuklendi: {OUT_DIR}/{tag}/ ({len(files)} dosya)")

    step = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [f"## PIN_SAMPLE_V2 {tag}", "", f"Drive: `{OUT_DIR}/{tag}/`", "",
             "| Varyant | Sahne | Tespit | Filigran | Bant | Not |", "|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines += ["", "Dosyalar: " + ", ".join(files)]
    text = "\n".join(lines)
    log(text)
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
