#!/usr/bin/env python3
"""
POD galeri ornegi: 1 cift x 5 edisyon, 10 kare (Etsy 3000x2250).

Kaynak: ETSY_UPLOAD_SETS/<ED>/<PAIR>/NN_WA_XX_*.jpg|png (dijital galeri seti).
Mevcut kareler dokunulmadan alinir (04 PNG -> JPG q98). Uc yeni kart (Paper &
Quality, Size Guide, Shipping & Care) mevcut teknik kart sablonunun olculmus
geometrisi ve edisyon paletiyle (10_ karttan olculur) cizilir.

Cikti: <out>/<ED>/01..10.jpg (+ 11_EXTRA_*.jpg: 10 kare sinirina sigmayan
mockup) ve <out>/CONTACT_<ED>.jpg.

Kullanim:
  python pod_gallery_sample.py --src SRC --out OUT [--editions MB,DB] [--pair ARIES_LEO]
  --fonts DIR  (CormorantGaramond[wght].ttf, CormorantGaramond-Italic[wght].ttf, Montserrat[wght].ttf)
  --spellcheck (pyspellchecker ile Ingilizce metin denetimi; bilinmeyen kelime -> HATA)
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 3000, 2250
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
POSTER_BOX = (732, 101, 1536, 2048)          # 05_PRODUCT_TRUTH kartindaki 3:4 poster (x, y, w, h)

# yeni galeri sirasi: (cikti no, kaynak rank | yeni kart adi)
PLAN = [("01", "01"), ("02", "02"), ("03", "03"), ("04", "04"), ("05", "PAPER"),
        ("06", "06"), ("07", "07"), ("08", "SIZES"), ("09", "10"), ("10", "CARE")]
EXTRA = ("11_EXTRA", "08")                    # 6. mockup (WA_12), Etsy 10 kare siniri

SIZES = [  # (etiket, en_in, boy_in, en_cm, boy_cm, oran grubu)
    ("8x10", 8, 10, 20.3, 25.4, "4:5"), ("16x20", 16, 20, 40.6, 50.8, "4:5"),
    ("12x16", 12, 16, 30.5, 40.6, "3:4"), ("18x24", 18, 24, 45.7, 61.0, "3:4"), ("30x40", 30, 40, 76.2, 101.6, "3:4"),
    ("12x18", 12, 18, 30.5, 45.7, "2:3"), ("16x24", 16, 24, 40.6, 61.0, "2:3"),
    ("20x30", 20, 30, 50.8, 76.2, "2:3"), ("24x36", 24, 36, 61.0, 91.4, "2:3"),
    ("11x14", 11, 14, 27.9, 35.6, "11:14"),
    ("A4", 8.3, 11.7, 21.0, 29.7, "A"), ("A3", 11.7, 16.5, 29.7, 42.0, "A"), ("A2", 16.5, 23.4, 42.0, 59.4, "A"),
]
GROUP_ORDER = ["3:4", "2:3", "A", "4:5", "11:14"]
GROUP_TITLE = {"3:4": "3:4", "2:3": "2:3", "A": "A SERIES", "4:5": "4:5", "11:14": "11:14"}

TEXT = {
    "PAPER": {
        "kicker": "MUSEUM-GRADE FINE ART PAPER", "title": "Paper & Quality",
        "rows": [("HAHNEMÜHLE PHOTO RAG", "308 gsm fine art paper with a soft matte surface"),
                 ("100% COTTON", "Pure cotton rag base, no wood pulp"),
                 ("ACID-FREE", "Archival paper that will not yellow over time"),
                 ("ARCHIVAL PIGMENT GICLÉE", "Fade-resistant pigment inks, printed at 300 DPI"),
                 ("MUSEUM QUALITY", "The paper galleries and collectors choose")],
        "footer": "Printed on Hahnemühle Photo Rag",
    },
    "SIZES": {"kicker": "CHOOSE YOUR SIZE", "title": "Size Guide", "footer": "Pick the Size That Fits Your Wall"},
    "CARE": {
        "kicker": "SHIPPING & CARE", "title": "Shipping & Care",
        "rows": [("ROLLED IN A TUBE", "Shipped rolled in a sturdy tube; 8x10 and A4 ship flat"),
                 ("FRAME NOT INCLUDED", "Print only, ready for the frame of your choice"),
                 ("FLAT GOLDEN INK", "Gold tones are printed as flat golden ink, not metallic foil"),
                 ("HANDLE BY THE EDGES", "Keep out of direct sunlight and frame under glass"),
                 ("SHIPS FROM THE US", "EU and UK orders are printed at our UK/EU lab")],
        "footer": "Made to Order, Just for You",
    },
    "common": {"bond": "TWO SOULS · ONE BOND", "copy": "© 2026 ASTROLOVE"},
}
SPELL_OK = {"hahnemühle", "giclée", "gsm", "astrolove", "dpi", "a4", "a3", "a2", "8x10", "uk", "eu", "us",
            "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x36", "30x40", "in", "cm"}


def log(m):
    print(m, flush=True)


# ------------------------------------------------------------------ palet / font
def palette(card10):
    """10_CRAFTED_DETAIL kartindan olculur (MB: bg 243,246,251 / bar 37,48,78 / ink 15,32,58)."""
    a = np.array(Image.open(card10).convert("RGB"))
    bg = tuple(int(v) for v in np.median(a[400:1800, 4:16].reshape(-1, 3), axis=0))
    bar = tuple(int(v) for v in a[2120, 1500])
    t = a[200:360, 900:2100].reshape(-1, 3)
    ink = tuple(int(v) for v in t[t.sum(1).argmin()])
    rule = tuple(int(v) for v in a[418, 1500])
    reg = a[2050:2180, 900:2100].reshape(-1, 3)
    d = np.abs(reg.astype(int) - np.array(bar)).sum(1)
    bt = reg[d > 150]
    bartext = tuple(int(v) for v in np.median(bt, axis=0)) if len(bt) else bg
    return {"bg": bg, "bar": bar, "ink": ink, "rule": rule, "bartext": bartext}


class Fonts:
    def __init__(self, d):
        d = Path(d)
        self.serif = d / "CormorantGaramond[wght].ttf"
        self.serif_i = d / "CormorantGaramond-Italic[wght].ttf"
        self.sans = d / "Montserrat[wght].ttf"
        for p in (self.serif, self.sans):
            if not p.exists():
                sys.exit(f"HATA: font yok: {p}")

    def f(self, kind, size, weight):
        p = {"serif": self.serif, "serif_i": self.serif_i, "sans": self.sans}[kind]
        ft = ImageFont.truetype(str(p), size)
        try:
            ft.set_variation_by_axes([weight])
        except Exception:
            pass
        return ft


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def text_w(draw, s, font, tracking=0):
    return sum(draw.textlength(ch, font=font) for ch in s) + tracking * (len(s) - 1)


def draw_tracked(draw, xy, s, font, fill, tracking=0, anchor="l"):
    x, y = xy
    w = text_w(draw, s, font, tracking)
    if anchor == "c":
        x -= w / 2
    elif anchor == "r":
        x -= w
    for ch in s:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return w


# ------------------------------------------------------------------ sablon
def card_base(pal, F, kicker, title, pair_txt, footer):
    """Olculmus sablon: kicker y142-171, baslik y233-374, cizgi y417 (x972-2027),
    cift satiri ~y495, bar y1990-2181 x104-2894 r30, bar serif y2031-2094, caps y2121-2141."""
    im = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(im)
    draw_tracked(d, (W / 2, 138), kicker, F.f("sans", 40, 500), pal["ink"], tracking=14, anchor="c")
    d.text((W / 2, 352), title, font=F.f("serif", 190, 500), fill=pal["ink"], anchor="ms")
    d.rectangle([972, 417, 2027, 419], fill=pal["rule"])
    draw_tracked(d, (W / 2, 482), pair_txt, F.f("sans", 44, 500), pal["ink"], tracking=16, anchor="c")
    d.rounded_rectangle([104, 1990, 2894, 2181], radius=30, fill=pal["bar"])
    d.text((W / 2, 2062), footer, font=F.f("serif", 78, 500), fill=pal["bartext"], anchor="mm")
    draw_tracked(d, (W / 2, 2118), TEXT["common"]["bond"], F.f("sans", 28, 500), pal["bartext"], tracking=9, anchor="c")
    draw_tracked(d, (2795, 2118), TEXT["common"]["copy"], F.f("sans", 28, 500), pal["bartext"], tracking=7, anchor="r")
    return im, d


def paste_shadowed(im, thumb, xy, blur=28, alpha=90):
    x, y = xy
    sh = Image.new("RGBA", (thumb.width + 160, thumb.height + 160), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([80, 90, 80 + thumb.width, 90 + thumb.height], fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(sh, (x - 80, y - 80), sh)
    im.paste(thumb, (x, y))


def numbered_rows(d, F, pal, rows, x0, y0, step, r=52):
    for i, (head, body) in enumerate(rows):
        cy = y0 + i * step
        d.ellipse([x0, cy - r, x0 + 2 * r, cy + r], fill=pal["bar"])
        d.text((x0 + r, cy), f"{i + 1:02d}", font=F.f("serif", 46, 700), fill=pal["bartext"], anchor="mm")
        draw_tracked(d, (x0 + 2 * r + 60, cy - 58), head, F.f("sans", 46, 600), pal["ink"], tracking=5)
        d.text((x0 + 2 * r + 60, cy + 6), body, font=F.f("sans", 38, 400), fill=mix(pal["ink"], pal["bg"], 0.25))


def card_paper(pal, F, poster, pair_txt):
    t = TEXT["PAPER"]
    im, d = card_base(pal, F, t["kicker"], t["title"], pair_txt, t["footer"])
    th = poster.resize((840, 1120), Image.LANCZOS)
    paste_shadowed(im, th, (330, 640))
    numbered_rows(d, F, pal, t["rows"], 1400, 760, 212)
    return im


def tube_icon(pal, poster):
    """Egik kargo tupu: gradyanli silindir, sol kapak, sag agizdan eksen boyunca cikan rulo poster."""
    c_dark, c_mid, c_light = mix(pal["bar"], (0, 0, 0), 0.3), pal["bar"], mix(pal["bar"], pal["bg"], 0.4)
    tw, th = 1150, 300
    cw = tw + 420
    body = Image.new("RGBA", (cw, th), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    for i in range(th):                       # dikey gradyan: ust acik -> orta koyu -> alt orta
        tt = i / (th - 1)
        c = mix(c_light, c_dark, min(1, tt * 1.7)) if tt < 0.6 else mix(c_dark, c_mid, (tt - 0.6) / 0.4)
        bd.line([80, i, tw - 180, i], fill=c + (255,))
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([80, 0, tw - 180, th - 1], radius=48, fill=255)
    body.putalpha(mask)
    bd = ImageDraw.Draw(body)
    bd.ellipse([40, 0, 120, th - 1], fill=c_dark + (255,))                       # sol kapak (yandan)
    bd.ellipse([tw - 330, 0, tw - 30, th - 1], fill=c_mid + (255,))              # sag agiz zemin
    bd.ellipse([tw - 285, 45, tw - 75, th - 45], fill=mix(pal["ink"], (0, 0, 0), 0.45) + (255,))  # ic bosluk
    # rulo: poster 90 derece, eksen boyunca disari; silindirik golge (dikey gradyan)
    rw, rh = 520, 170
    roll = poster.resize((rh, rw), Image.LANCZOS).rotate(90, expand=True).convert("RGB")
    shade = Image.new("L", (rw, rh), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(rh):
        tt = abs(y - rh * 0.4) / (rh * 0.6)
        sd.line([0, y, rw, y], fill=int(255 * min(1, 0.1 + 0.9 * tt ** 1.5)))
    roll = Image.composite(Image.new("RGB", (rw, rh), (0, 0, 0)), roll, shade.point(lambda v: int(v * 0.8))).convert("RGBA")
    rm = Image.new("L", (rw, rh), 0)
    ImageDraw.Draw(rm).rounded_rectangle([0, 0, rw - 1, rh - 1], radius=80, fill=255)
    roll.putalpha(rm)
    body.paste(roll, (tw - 200, (th - rh) // 2), roll)
    bd.ellipse([tw - 330, 0, tw - 30, th - 1], outline=c_light + (255,), width=8)  # agiz halkasi (rulo ustune)
    return body.rotate(30, expand=True, resample=Image.BICUBIC)


def card_care(pal, F, poster, pair_txt):
    t = TEXT["CARE"]
    im, d = card_base(pal, F, t["kicker"], t["title"], pair_txt, t["footer"])
    icon = tube_icon(pal, poster)
    sh = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 70), (0, 0, icon.width, icon.height), icon.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    x, y = 200 + (1000 - icon.width) // 2, 700 + (1000 - icon.height) // 2
    im.paste(sh, (x + 10, y + 40), sh)
    im.paste(icon, (x, y), icon)
    numbered_rows(d, F, pal, t["rows"], 1400, 760, 212)
    return im


def card_sizes(pal, F, poster, pair_txt):
    t = TEXT["SIZES"]
    im, d = card_base(pal, F, t["kicker"], t["title"], pair_txt, t["footer"])
    s = 6.8                                   # px / cm
    floor_y = 1905
    hang = 52                                 # poster alt kenari yerden (cm)
    gold = (200, 150, 48)
    colors = {"3:4": pal["ink"], "2:3": gold, "A": pal["bar"] if pal["bar"] != pal["ink"] else mix(pal["ink"], gold, 0.5),
              "4:5": mix(pal["ink"], gold, 0.55), "11:14": mix(pal["ink"], pal["bg"], 0.5)}
    if abs(sum(colors["A"]) - sum(colors["3:4"])) < 60:      # bar ~ ink ise ayirt edilsin
        colors["A"] = mix(pal["ink"], pal["bg"], 0.3)
    d.line([250, floor_y, 2760, floor_y], fill=mix(pal["ink"], pal["bg"], 0.6), width=3)
    # insan silueti 175 cm
    px, ph = 430, 175 * s
    top = floor_y - ph
    sil = mix(pal["ink"], pal["bg"], 0.55)
    d.ellipse([px - 66, top, px + 66, top + 132], fill=sil)
    d.rounded_rectangle([px - 125, top + 152, px + 125, top + 680], radius=100, fill=sil)
    d.rounded_rectangle([px - 108, top + 660, px - 14, floor_y], radius=32, fill=sil)
    d.rounded_rectangle([px + 14, top + 660, px + 108, floor_y], radius=32, fill=sil)
    draw_tracked(d, (px, floor_y + 24), "175 CM \u00b7 5'9\"", F.f("sans", 26, 500), mix(pal["ink"], pal["bg"], 0.3), tracking=4, anchor="c")
    # gruplar: sabit 430 px sutun, ic ice dikdortgenler sol-alt koseden hizali
    pitch, x0 = 430, 660
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    base_y = floor_y - hang * s
    for gi, g in enumerate(GROUP_ORDER):
        x = x0 + gi * pitch
        items = sorted([z for z in SIZES if z[5] == g], key=lambda z: -z[4])
        col = colors[g]
        for lab, win, hin, wcm, hcm, _ in items:
            w, h = wcm * s, hcm * s
            od.rectangle([x, base_y - h, x + w, base_y], fill=col + (40,), outline=col + (255,), width=4)
            d.text((x + w - 14, base_y - h + 12), lab, font=F.f("sans", 28, 600), fill=col, anchor="ra")
        ly = base_y + 30
        draw_tracked(d, (x, ly), GROUP_TITLE[g], F.f("sans", 30, 700), col, tracking=4)
        ly += 46
        for lab, win, hin, wcm, hcm, _ in items:
            line = f"{lab} in \u00b7 {wcm:g}\u00d7{hcm:g} cm" if not lab.startswith("A") else f"{lab} \u00b7 {win:g}\u00d7{hin:g} in \u00b7 {wcm:g}\u00d7{hcm:g} cm"
            d.text((x, ly), line, font=F.f("sans", 26, 400), fill=mix(pal["ink"], pal["bg"], 0.2))
            ly += 36
    im.paste(overlay, (0, 0), overlay)
    return im


# ------------------------------------------------------------------ spellcheck
def spellcheck():
    try:
        from spellchecker import SpellChecker
    except ImportError:
        sys.exit("HATA: pyspellchecker yok (pip install pyspellchecker)")
    sp = SpellChecker()
    words = set()
    for k in ("PAPER", "SIZES", "CARE"):
        blob = " ".join([TEXT[k]["kicker"], TEXT[k]["title"], TEXT[k]["footer"]] +
                        [a + " " + b for a, b in TEXT[k].get("rows", [])])
        words |= {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ']+", blob)}
    words |= {w.lower() for w in re.findall(r"[A-Za-z']+", " ".join(TEXT["common"].values()))}
    bad = sorted(w for w in sp.unknown(words) if w not in SPELL_OK)
    if bad:
        sys.exit(f"HATA: yazim denetimi bilinmeyen kelime: {bad}")
    log(f"yazim denetimi: {len(words)} kelime, PASS")


# ------------------------------------------------------------------ ana
def save_jpg(im, p, q=95):
    im.save(p, "JPEG", quality=q, subsampling=0, progressive=False, dpi=(300, 300))


def find_src(src_ed, rank):
    c = sorted(src_ed.glob(f"{rank}_WA_*"))
    if not c:
        raise FileNotFoundError(f"{src_ed}/{rank}_WA_*")
    return c[0]


def contact(out_ed, name, out_p, F):
    files = sorted(out_ed.glob("*.jpg"))
    cols, tw, th = 5, 600, 450
    rows = -(-len(files) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 40) + 60), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((20, 15), name, font=F.f("sans", 30, 600), fill=(0, 0, 0))
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize((tw - 10, th - 10), Image.LANCZOS)
        x, y = (i % cols) * tw, 60 + (i // cols) * (th + 40)
        sheet.paste(im, (x + 5, y))
        d.text((x + 8, y + th - 4), f.stem, font=F.f("sans", 22, 500), fill=(0, 0, 0))
    sheet.save(out_p, "JPEG", quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="SRC/<ED>/ altinda 12 kaynak dosya")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--pair", default="ARIES_LEO")
    ap.add_argument("--editions", default=",".join(EDITIONS))
    ap.add_argument("--spellcheck", action="store_true")
    ap.add_argument("--only-new", action="store_true", help="yalniz 3 yeni kart (yerel prototip)")
    a = ap.parse_args()
    if a.spellcheck:
        spellcheck()
    F = Fonts(a.fonts)
    eds = [e for e in a.editions.split(",") if e]
    pair_txt = " • ".join(a.pair.split("_"))
    t0 = time.time()
    report = {}
    for n, ed in enumerate(eds, 1):
        src, out = Path(a.src) / ed, Path(a.out) / ed
        out.mkdir(parents=True, exist_ok=True)
        pal = palette(find_src(src, "10"))
        c05 = Image.open(find_src(src, "05")).convert("RGB")
        x, y, w, h = POSTER_BOX
        poster = c05.crop((x, y, x + w, y + h))
        made = []
        for outno, what in (PLAN + [EXTRA] if not a.only_new else [p for p in PLAN if p[1] in ("PAPER", "SIZES", "CARE")]):
            if what in ("PAPER", "SIZES", "CARE"):
                im = {"PAPER": card_paper, "SIZES": card_sizes, "CARE": card_care}[what](pal, F, poster, pair_txt)
                p = out / f"{outno}_{what}_{a.pair}_{ed}.jpg"
                save_jpg(im, p, 95)
                made.append((outno, what, "yeni"))
            else:
                s = find_src(src, what)
                p = out / f"{outno}_{s.stem.split('_', 1)[1]}.jpg"
                if s.suffix.lower() == ".png":
                    save_jpg(Image.open(s).convert("RGB"), p, 98)
                else:
                    shutil.copyfile(s, p)
                made.append((outno, s.name, "mevcut"))
        contact(out, f"{a.pair} / {ed}", Path(a.out) / f"CONTACT_{ed}.jpg", F)
        report[ed] = {"palette": pal, "frames": made}
        el = time.time() - t0
        log(f"[{n}/{len(eds)}] {ed:<16} {len(made)} kare  gecen={el:.0f}s kalan~{el / n * (len(eds) - n):.0f}s")
    (Path(a.out) / "build_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    log(f"bitti: {len(eds)} edisyon, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
