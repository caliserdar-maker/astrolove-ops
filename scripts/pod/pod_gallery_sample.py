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
    ("A4", 8.3, 11.7, 21.0, 29.7, "A"), ("A3", 11.7, 16.5, 29.7, 42.0, "A"), ("A2", 16.5, 23.4, 41.9, 59.4, "A"),
]
GROUP_ORDER = ["3:4", "2:3", "A", "4:5", "11:14"]
GROUP_TITLE = {"3:4": "3:4", "2:3": "2:3", "A": "A SERIES", "4:5": "4:5", "11:14": "11:14"}

TEXT = {
    "PAPER": {
        "kicker": ("P_kicker", "MUSEUM-GRADE FINE ART PAPER"), "title": "Paper & Quality",
        "rows": [("P1", "HAHNEMÜHLE PHOTO RAG", "308 gsm fine art paper with a soft matte surface"),
                 ("P2", "100% COTTON", "Made from 100% cotton rag"),
                 ("P3", "ACID-FREE", "Acid- and lignin-free, ISO 9706 conform"),
                 ("P4", "ARCHIVAL PIGMENT GICLÉE", "Giclée print with pigment inks at 300 DPI"),
                 ("P5", "MUSEUM QUALITY", "Highest age resistance, ISO 9706 conform")],
        "footer": ("P_footer", "Printed on Hahnemühle Photo Rag"),
    },
    "SIZES": {"kicker": ("S_kicker", "CHOOSE YOUR SIZE"), "title": "Size Guide",
              "footer": ("S_footer", "Pick the Size That Fits Your Wall")},
    "CARE": {
        "kicker": ("C_kicker", "SHIPPING & CARE"), "title": "Shipping & Care",
        "rows": [("C1", "ROLLED IN A TUBE", "8x10 and A4 ship flat (US & EU); all other sizes ship rolled in a sturdy tube."),
                 ("C2", "FRAME NOT INCLUDED", "Print only, ready for the frame of your choice"),
                 ("C3", "FLAT GOLDEN INK", "Gold tones are printed as flat golden ink, not metallic foil"),
                 ("C4", "HANDLE BY THE EDGES", "Touch only the margins to avoid fingerprints"),
                 ("C5", "SHIPS FROM THE US", "EU and UK orders are printed at our UK/EU lab")],
        "footer": ("C_footer", "Made to Order, Just for You"),
    },
    "common": {"bond": "TWO SOULS · ONE BOND", "copy": "© 2026 ASTROLOVE"},
}
SPELL_OK = {"hahnemühle", "giclée", "gsm", "astrolove", "dpi", "iso", "a4", "a3", "a2", "8x10", "uk", "eu", "us",
            "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x36", "30x40", "in", "cm"}


def log(m):
    print(m, flush=True)


VERIFIED = None                               # None = filtre yok; dict = kaynaksiz satir dusur


def ok(fid):
    """factcheck listesinde olmayan kimlikler (kicker/footer gibi iddia icermeyen metin) her zaman gecer."""
    return VERIFIED is None or VERIFIED.get(fid, True)


def vtext(item):
    """(fid, metin) -> metin | '' (kaynaksizsa)."""
    return item[1] if ok(item[0]) else ""


def rows_of(card):
    return [(h, b) for fid, h, b in TEXT[card]["rows"] if ok(fid)]


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


# ------------------------------------------------------------------ sablon (04/09 referansindan olculdu, MB 3000x2250)
# kicker cap y141-172 | baslik "Symbol Story" bandi y233-373 | cizgi y417-420 x972-2027 | cift satiri cap y489-522
# rozet o130 x271-401, rakam bandi 34 px | satir basligi cap y736-777 x460 | 09 madde caps 27 px
# bar y1990-2180 x105-2893 r30 | bar serif bandi 2031-2094 | bar caps 2121-2141 (x1255-1745) | (c) sagda ~x2795
REF = {"kicker_cap": 31, "kicker_w": ("ASTROLOVE ORIGINAL COMPOSITION", 1147), "title_band": ("Symbol Story", 140),
       "pair_cap": 33, "pair_w": ("ARIES \u2022 LEO", 357), "badge_d": 130, "digit_h": 34,
       "head_cap": 41, "head_w": ("TWO SIGNS", 338), "body_cap": 27,
       "foot_serif_band": ("The Shape of Your Connection", 63), "foot_cap": 20, "foot_w": ("TWO SOULS \u00b7 ONE BOND", 490)}
_cal = {}


def cap_h(font, txt="H"):
    b = font.getbbox(txt)
    return b[3] - b[1]


def solve_size(F, kind, weight, target, txt="H"):
    """bbox yuksekligi hedefe esit olacak font boyutunu bul (tam sayi, en yakin)."""
    key = (kind, weight, target, txt)
    if key not in _cal:
        best = min(range(10, 400), key=lambda sz: abs(cap_h(F.f(kind, sz, weight), txt) - target))
        _cal[key] = best
    return _cal[key]


def solve_tracking(d, font, txt, target_w):
    base = sum(d.textlength(ch, font=font) for ch in txt)
    return (target_w - base) / max(1, len(txt) - 1)


def card_base(pal, F, kicker, title, pair_txt, footer):
    im = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(im)
    f_k = F.f("sans", solve_size(F, "sans", 500, REF["kicker_cap"]), 500)
    tr_k = solve_tracking(d, f_k, *REF["kicker_w"])
    if kicker:
        draw_tracked(d, (W / 2, 141 - f_k.getbbox("H")[1]), kicker, f_k, pal["ink"], tracking=tr_k, anchor="c")
    f_t = F.f("serif", solve_size(F, "serif", 500, REF["title_band"][1], REF["title_band"][0]), 500)
    d.text((W / 2, 233 - f_t.getbbox("Symbol Story")[1]), title, font=f_t, fill=pal["ink"], anchor="ma")
    d.rectangle([972, 417, 2027, 419], fill=pal["rule"])
    f_p = F.f("sans", solve_size(F, "sans", 500, REF["pair_cap"]), 500)
    draw_tracked(d, (W / 2, 489 - f_p.getbbox("H")[1]), pair_txt, f_p, pal["ink"], tracking=solve_tracking(d, f_p, *REF["pair_w"]), anchor="c")
    d.rounded_rectangle([105, 1990, 2893, 2180], radius=30, fill=pal["bar"])
    f_fs = F.f("serif", solve_size(F, "serif", 500, REF["foot_serif_band"][1], REF["foot_serif_band"][0]), 500)
    if footer:
        d.text((W / 2, 2031 - f_fs.getbbox(REF["foot_serif_band"][0])[1]), footer, font=f_fs, fill=pal["bartext"], anchor="ma")
    f_fc = F.f("sans", solve_size(F, "sans", 500, REF["foot_cap"]), 500)
    tr_fc = solve_tracking(d, f_fc, *REF["foot_w"])
    y_fc = 2121 - f_fc.getbbox("H")[1]
    draw_tracked(d, (W / 2, y_fc), TEXT["common"]["bond"], f_fc, pal["bartext"], tracking=tr_fc, anchor="c")
    draw_tracked(d, (2795, y_fc), TEXT["common"]["copy"], f_fc, pal["bartext"], tracking=tr_fc, anchor="r")
    return im, d


def numbered_rows(d, F, pal, rows, y0=640, y1=1900):
    """04 rozeti: o130 merkez x336; rakam serif 34 px; baslik caps cap 41 @x460; aciklama caps-olcek 27."""
    r = REF["badge_d"] // 2
    cx, tx = 336, 460
    f_d = F.f("serif", solve_size(F, "serif", 700, REF["digit_h"], "01"), 700)
    f_h = F.f("sans", solve_size(F, "sans", 600, REF["head_cap"]), 600)
    tr_h = solve_tracking(d, f_h, *REF["head_w"])
    f_b = F.f("sans", solve_size(F, "sans", 400, REF["body_cap"]), 400)
    n = len(rows)
    step = (y1 - y0) / n
    for i, (head, body) in enumerate(rows):
        cy = y0 + step * (i + 0.5)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["bar"])
        d.text((cx, cy), f"{i + 1:02d}", font=f_d, fill=pal["bartext"], anchor="mm")
        hb = f_h.getbbox("H")
        draw_tracked(d, (tx, cy - 6 - hb[3]), head, f_h, pal["ink"], tracking=tr_h)          # baslik: rozet merkezinin ustu
        d.text((tx, cy + 18 - f_b.getbbox("H")[1]), body, font=f_b, fill=mix(pal["ink"], pal["bg"], 0.25))


def paste_shadowed(im, thumb, xy, blur=28, alpha=90):
    x, y = xy
    sh = Image.new("RGBA", (thumb.width + 160, thumb.height + 160), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([80, 90, 80 + thumb.width, 90 + thumb.height], fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(sh, (x - 80, y - 80), sh)
    im.paste(thumb, (x, y))


def card_paper(pal, F, poster, pair_txt):
    t = TEXT["PAPER"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    th = poster.resize((780, 1040), Image.LANCZOS)
    paste_shadowed(im, th, (1980, 660))
    numbered_rows(d, F, pal, rows_of("PAPER"), 640, 1900)
    return im


TABLER_PACKAGE = [  # tabler-icons "package" (MIT), 24x24 izgara, stroke 2
    [(12, 3), (20, 7.5), (20, 16.5), (12, 21), (4, 16.5), (4, 7.5), (12, 3)],
    [(12, 12), (20, 7.5)], [(12, 12), (12, 21)], [(12, 12), (4, 7.5)], [(16, 5.25), (8, 9.75)],
]


def package_icon(pal, size=760, stroke=4):
    """Cizgisel paket ikonu; cizgi kalinligi 09 kartindaki panel/baglanti cizgisiyle ayni (4 px)."""
    S = 4
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = size * S / 24
    col = pal["rule"] + (255,)
    w = stroke * S
    for path in TABLER_PACKAGE:
        pts = [(x * k, y * k) for x, y in path]
        d.line(pts, fill=col, width=w, joint="curve")
        for x, y in pts:
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col)
    return img.resize((size, size), Image.LANCZOS)


def card_care(pal, F, poster, pair_txt):
    t = TEXT["CARE"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    icon = package_icon(pal)
    im.paste(icon, (2370 - icon.width // 2, 1270 - icon.height // 2), icon)
    numbered_rows(d, F, pal, rows_of("CARE"), 640, 1900)
    return im


def silhouette(height_px, color):
    """Sade, anatomik oranli duz vektor siluet (on gorunus, ayakta). Yukseklik = 175 cm referansi."""
    S = 4
    Hh = height_px * S
    u = lambda x, y: (x * Hh, y * Hh)          # birim: boy = 1
    img = Image.new("RGBA", (int(0.34 * Hh), int(Hh)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = 0.17
    # bas
    d.ellipse([u(cx - 0.045, 0.0)[0], 0, u(cx + 0.045, 0.13)[0], 0.13 * Hh], fill=color)
    # boyun
    d.rectangle([u(cx - 0.02, 0.12), u(cx + 0.02, 0.165)], fill=color)
    # govde (omuz -> bel -> kalca), sag yarim + ayna
    torso = [(cx, 0.16), (cx + 0.09, 0.17), (cx + 0.115, 0.20), (cx + 0.10, 0.30), (cx + 0.082, 0.40),
             (cx + 0.086, 0.47), (cx + 0.092, 0.53), (cx, 0.56)]
    poly = torso + [(2 * cx - x, y) for x, y in reversed(torso)]
    d.polygon([u(*p) for p in poly], fill=color)
    # kollar (govdeden hafif ayrik)
    for sgn in (1, -1):
        arm = [(cx + sgn * 0.095, 0.185), (cx + sgn * 0.135, 0.20), (cx + sgn * 0.15, 0.42), (cx + sgn * 0.152, 0.60),
               (cx + sgn * 0.125, 0.61), (cx + sgn * 0.118, 0.43), (cx + sgn * 0.10, 0.30)]
        d.polygon([u(*p) for p in arm], fill=color)
        d.ellipse([u(cx + sgn * 0.14 - 0.022, 0.59), u(cx + sgn * 0.14 + 0.022, 0.635)], fill=color)
    # bacaklar (kalcadan ayaga incelen) ve ayaklar
    for sgn in (1, -1):
        leg = [(cx + sgn * 0.010, 0.545), (cx + sgn * 0.092, 0.53), (cx + sgn * 0.078, 0.75),
               (cx + sgn * 0.066, 0.955), (cx + sgn * 0.026, 0.955), (cx + sgn * 0.028, 0.75)]
        d.polygon([u(*p) for p in leg], fill=color)
        foot = [(cx + sgn * 0.02, 0.955), (cx + sgn * 0.07, 0.955), (cx + sgn * 0.10, 0.99), (cx + sgn * 0.02, 1.0)]
        d.polygon([u(*p) for p in foot], fill=color)
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


SG_SCALE = 6.2      # px/cm  (6.8 istendi; 30x40 = 518 px, 5 esit sutun + cetvel 3000 px'e sigmiyor -> 6.2: 472 px)
SG_COLS = 5
SG_COL_W, SG_GAP = 480, 40
SG_X0 = 300         # ilk sutun sol kenari; cetvel x=180; sag bosluk 3000-2860=140 ~ cetvel-sutun araligi


def card_sizes(pal, F, poster, pair_txt):
    t = TEXT["SIZES"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    s = SG_SCALE
    floor_y = 1905
    hang = 45
    accent, rule = pal["bar"], pal["rule"]
    neutral_fill = mix(pal["ink"], pal["bg"], 0.90)
    neutral_line = mix(pal["ink"], pal["bg"], 0.45)
    f_lab = F.f("sans", solve_size(F, "sans", 600, 20), 600)
    f_ttl = F.f("sans", solve_size(F, "sans", 700, REF["body_cap"]), 700)
    f_txt = F.f("sans", solve_size(F, "sans", 400, 19), 400)
    f_ruler = F.f("sans", solve_size(F, "sans", 500, 18), 500)
    # ortak taban cizgisi
    d.line([SG_X0 - 20, floor_y, SG_X0 + SG_COLS * SG_COL_W + (SG_COLS - 1) * SG_GAP + 20, floor_y], fill=neutral_line, width=3)
    # dikey cetvel (metre): 04/09 ayraci ile ayni kalinlik (3 px) ve renk
    rx = 180
    top = floor_y - 175 * s
    d.line([rx, floor_y, rx, top], fill=rule, width=3)
    for cm in range(0, 176, 25):
        y = floor_y - cm * s
        long = cm % 50 == 0
        d.line([rx - (40 if long else 20), y, rx, y], fill=rule, width=3)
        if long and cm:
            d.text((rx - 50, y), f"{cm} CM", font=f_ruler, fill=mix(pal["ink"], pal["bg"], 0.2), anchor="rm")
    d.line([rx - 40, top, rx + 40, top], fill=rule, width=3)
    draw_tracked(d, (rx, top - 48), "175 CM \u00b7 5'9\"", f_ruler, pal["ink"], tracking=3, anchor="c")
    # 5 esit sutun, alt-orta hizali ic ice dikdortgenler
    base_y = floor_y - hang * s
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    labels = []
    for gi, g in enumerate(GROUP_ORDER):
        cxg = SG_X0 + gi * (SG_COL_W + SG_GAP) + SG_COL_W // 2
        items = sorted([z for z in SIZES if z[5] == g], key=lambda z: -z[4])
        for k, (lab, win, hin, wcm, hcm, _) in enumerate(items):
            w, h = wcm * s, hcm * s
            x1, y1 = cxg - w / 2, base_y - h
            od.rectangle([x1, y1, x1 + w, base_y], fill=(neutral_fill if k == 0 else pal["bg"]) + (255,),
                         outline=(accent if k == 0 else neutral_line) + (255,), width=4 if k == 0 else 3)
            labels.append(((cxg, y1 + 10), lab))
    im.paste(overlay, (0, 0), overlay)
    d = ImageDraw.Draw(im)
    for xy, lab in labels:
        d.text(xy, lab, font=f_lab, fill=mix(pal["ink"], pal["bg"], 0.15), anchor="ma")
    for gi, g in enumerate(GROUP_ORDER):
        cxg = SG_X0 + gi * (SG_COL_W + SG_GAP) + SG_COL_W // 2
        items = sorted([z for z in SIZES if z[5] == g], key=lambda z: -z[4])
        ly = base_y + 26
        draw_tracked(d, (cxg, ly), GROUP_TITLE[g], f_ttl, accent, tracking=4, anchor="c")
        d.line([cxg - 60, ly + 40, cxg + 60, ly + 40], fill=accent, width=2)
        ly += 56
        for lab, win, hin, wcm, hcm, _ in items:
            line = f"{lab} in \u00b7 {wcm:g}\u00d7{hcm:g} cm" if not lab.startswith("A") else f"{lab} \u00b7 {win:g}\u00d7{hin:g} in \u00b7 {wcm:g}\u00d7{hcm:g} cm"
            d.text((cxg, ly), line, font=f_txt, fill=mix(pal["ink"], pal["bg"], 0.2), anchor="ma")
            ly += 32
    return im


# ------------------------------------------------------------------ geometri olcumu (04/09 ile kiyas)
def _bands(a, y0, y1, x0, x1, dark=True, th=150):
    m = (a[y0:y1, x0:x1] < th) if dark else (a[y0:y1, x0:x1] > th)
    rows = m.sum(1) > 0
    out, st = [], None
    for i, r in enumerate(rows):
        if r and st is None:
            st = i
        if not r and st is not None:
            out.append((y0 + st, y0 + i))
            st = None
    if st is not None:
        out.append((y0 + st, y1))
    return out


def _xext(a, y0, y1, x0, x1, dark=True, th=150):
    m = (a[y0:y1, x0:x1] < th) if dark else (a[y0:y1, x0:x1] > th)
    xs = np.where(m.sum(0) > 0)[0]
    return (int(x0 + xs.min()), int(x0 + xs.max())) if len(xs) else None


def geometry(card_p, rows=True):
    """kicker/baslik/cizgi/cift/bar bantlari (px). Acik zeminli kartlar icin koyu metin."""
    im = Image.open(card_p).convert("RGB")
    a = np.array(im.convert("L"))
    rgb = np.array(im)
    # zemin acik mi? (PURE_WHITE/WP gibi) -> esik zemin parlakligina gore
    bg = float(np.median(a[400:1800, 4:16]))
    th = bg - 60
    hb = _bands(a, 80, 560, 600, 2400, th=th)
    g = {"kicker": hb[0] if hb else None, "title": hb[1] if len(hb) > 1 else None,
         "rule": hb[2] if len(hb) > 2 else None, "pair": hb[3] if len(hb) > 3 else None,
         "rule_x": _xext(a, 414, 424, 0, 3000, th=th)}
    colm = rgb[:, 1500]
    bar = tuple(int(v) for v in rgb[2120, 1500])
    ys = np.where(np.abs(colm.astype(int) - np.array(bar)).sum(1) < 20)[0]
    ys = ys[ys > 1900]
    row = rgb[2100]
    xs = np.where(np.abs(row.astype(int) - np.array(bar)).sum(1) < 20)[0]
    g["bar"] = (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())) if len(ys) and len(xs) else None
    # bar ici acik metin bantlari
    bl = float(np.mean(a[2100, 1400:1600]))
    g["bar_text"] = _bands(a, 2000, 2180, 900, 2100, dark=False, th=bl + 60)
    # rozet (ilk bar-rengi daire, x200-500) ve satir basligi cap yuksekligi — saf numpy
    if not rows:
        g["badge"] = g["head_cap"] = g["head_x0"] = None
        return g
    m = np.abs(rgb[600:1950, 200:500].astype(int) - np.array(bar)).sum(2) < 40
    wide = m.sum(1) >= 80
    ys = np.where(wide)[0]
    if len(ys):
        y0 = 600 + ys[0]
        y1 = y0
        while y1 - 600 < len(wide) and wide[y1 - 600]:
            y1 += 1
        xs = np.where(m[ys[0]:y1 - 600].sum(0) > 0)[0]
        g["badge"] = (200 + int(xs.min()), 200 + int(xs.max()) + 1, y1 - y0)
        hb = [b for b in _bands(a, y0 - 40, y1 + 60, 450, 1500, th=th) if b[1] - b[0] >= 20]   # umlaut/nokta bantlarini atla
        g["head_cap"] = (hb[0][1] - hb[0][0]) if hb else None
        g["head_x0"] = _xext(a, hb[0][0], hb[0][1], 450, 1500, th=th)[0] if hb else None
    else:
        g["badge"] = g["head_cap"] = g["head_x0"] = None
    return g
    lab, _ = ndimage.label(np.abs(rgb[600:1950, 200:500].astype(int) - np.array(bar)).sum(2) < 40)
    objs = [sl for sl in ndimage.find_objects(lab) if (sl[1].stop - sl[1].start) > 80 and (sl[0].stop - sl[0].start) > 80]
    if objs:
        sl = objs[0]
        y0, y1 = 600 + sl[0].start, 600 + sl[0].stop
        g["badge"] = (200 + sl[1].start, 200 + sl[1].stop, y1 - y0)
        hb = [b for b in _bands(a, y0 - 40, y1 + 60, 450, 1500, th=th) if b[1] - b[0] >= 20]   # umlaut/nokta bantlarini atla
        g["head_cap"] = (hb[0][1] - hb[0][0]) if hb else None
        g["head_x0"] = _xext(a, hb[0][0], hb[0][1], 450, 1500, th=th)[0] if hb else None
    else:
        g["badge"] = g["head_cap"] = g["head_x0"] = None
    return g


GEOM_REF = {"kicker": (141, 172), "title": (233, 373), "rule": (417, 420), "pair": (489, 522), "rule_x": (972, 2027),
            "bar": (1990, 2180, 105, 2893), "bar_text": [(2031, 2094), (2121, 2141)],
            "badge": (271, 401, 130), "head_cap": (41,), "head_x0": (460,)}


# ------------------------------------------------------------------ spellcheck
def spellcheck():
    try:
        from spellchecker import SpellChecker
    except ImportError:
        sys.exit("HATA: pyspellchecker yok (pip install pyspellchecker)")
    sp = SpellChecker()
    words = set()
    for k in ("PAPER", "SIZES", "CARE"):
        blob = " ".join([TEXT[k]["kicker"][1], TEXT[k]["title"], TEXT[k]["footer"][1]] +
                        [h + " " + b for _, h, b in TEXT[k].get("rows", [])])
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


def measure(card_p):
    """Uretilen kartta zemin / bar / baslik murekkebi / aksan (numara dairesi) olcumu."""
    a = np.array(Image.open(card_p).convert("RGB"))
    t = a[200:360, 900:2100].reshape(-1, 3)
    return {"bg": tuple(int(v) for v in np.median(a[400:1800, 4:16].reshape(-1, 3), axis=0)),
            "bar": tuple(int(v) for v in a[2120, 1500]),
            "ink": tuple(int(v) for v in t[t.sum(1).argmin()]),
            "accent": tuple(int(v) for v in a[2120, 1500])}


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
    ap.add_argument("--verified", help="factcheck verified.json; kaynaksiz satirlar karttan dusurulur")
    a = ap.parse_args()
    global VERIFIED
    if a.verified:
        VERIFIED = json.loads(Path(a.verified).read_text())
        log(f"kaynak filtresi: {sum(VERIFIED.values())}/{len(VERIFIED)} satir kaynakli; dusenler: {[k for k, v in VERIFIED.items() if not v]}")
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
                mp = measure(p)
                dev = max(abs(mp[k][i] - pal[k][i]) for k in ("bg", "bar", "ink") for i in range(3))
                made.append((outno, what, "yeni", {"olcum": mp, "referans_sapma_max": dev, "geom": geometry(p, rows=(what != "SIZES"))}))
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
    md = ["# Palet uyumu raporu (yeni kartlar vs edisyonun mevcut 10_ karti)", "",
          "| edisyon | kart | zemin | bar | baslik | referans zemin/bar/baslik | max sapma |", "|---|---|---|---|---|---|---|"]
    for ed, r in report.items():
        pal = r["palette"]
        for m in r["frames"]:
            if len(m) == 4:
                o = m[3]["olcum"]
                md.append(f"| {ed} | {m[1]} | {o['bg']} | {o['bar']} | {o['ink']} | {pal['bg']} / {pal['bar']} / {pal['ink']} | {m[3]['referans_sapma_max']} |")
    (Path(a.out) / "PALETTE_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    gm = ["# Geometri / tipografi kiyasi (yeni kartlar vs 04 Symbol Story / 09 Crafted Detail, MB olcumu)", "",
          "Referans (px): kicker cap y141-172 · baslik bandi y233-373 · cizgi y417-420 x972-2027 · cift satiri y489-522 · "
          "bar y1990-2180 x105-2893 · bar serif y2031-2094 · bar caps y2121-2141", "",
          "Referans rozet x271-401 o130 · satir basligi cap 41 px @x460 · 09 cizgi kalinligi 4 px (paket ikonu 4 px)", "",
          "| edisyon | kart | kicker | baslik | cizgi | cift | cizgi x | bar (y0,y1,x0,x1) | bar metin | rozet (x0,x1,o) | baslik cap | baslik x0 | max sapma px |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for ed, r in report.items():
        for m in r["frames"]:
            if len(m) == 4:
                g = m[3]["geom"]
                devs = []
                for k, ref in GEOM_REF.items():
                    v = g.get(k)
                    if v is None:
                        continue
                    if k == "bar_text":
                        devs += [abs(x - y) for a_, b_ in zip(v, ref) for x, y in zip(a_, b_)]
                    elif k == "title":
                        devs.append(abs(v[0] - ref[0]))          # baslik alt siniri metne bagli (alt uzanti yoksa kisa)
                    elif isinstance(v, tuple):
                        devs += [abs(x - y) for x, y in zip(v, ref)]
                    else:
                        devs.append(abs(v - ref[0]))
                gm.append(f"| {ed} | {m[1]} | {g['kicker']} | {g['title']} | {g['rule']} | {g['pair']} | {g['rule_x']} | {g['bar']} | {g['bar_text']} | {g['badge']} | {g['head_cap']} | {g['head_x0']} | {max(devs) if devs else '-'} |")
    (Path(a.out) / "GEOMETRY_REPORT.md").write_text("\n".join(gm) + "\n", encoding="utf-8")
    log(f"bitti: {len(eds)} edisyon, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
