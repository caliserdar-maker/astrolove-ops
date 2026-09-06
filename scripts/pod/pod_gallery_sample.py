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
        "rows": [("C1", "ROLLED IN A TUBE", "Rolled in a thick cardboard tube; EU orders A4 and smaller ship flat"),
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
    return VERIFIED is None or VERIFIED.get(fid, False)


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


# ------------------------------------------------------------------ sablon
def card_base(pal, F, kicker, title, pair_txt, footer):
    """Olculmus sablon: kicker y142-171, baslik y233-374, cizgi y417 (x972-2027),
    cift satiri ~y495, bar y1990-2181 x104-2894 r30, bar serif y2031-2094, caps y2121-2141."""
    im = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(im)
    if kicker:
        draw_tracked(d, (W / 2, 138), kicker, F.f("sans", 40, 500), pal["ink"], tracking=14, anchor="c")
    d.text((W / 2, 352), title, font=F.f("serif", 190, 500), fill=pal["ink"], anchor="ms")
    d.rectangle([972, 417, 2027, 419], fill=pal["rule"])
    draw_tracked(d, (W / 2, 482), pair_txt, F.f("sans", 44, 500), pal["ink"], tracking=16, anchor="c")
    d.rounded_rectangle([104, 1990, 2894, 2181], radius=30, fill=pal["bar"])
    if footer:
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
    y0 = y0 + (5 - len(rows)) * step / 2       # 5 satirlik alan icinde dikey ortala
    for i, (head, body) in enumerate(rows):
        cy = y0 + i * step
        d.ellipse([x0, cy - r, x0 + 2 * r, cy + r], fill=pal["bar"])
        d.text((x0 + r, cy), f"{i + 1:02d}", font=F.f("serif", 46, 700), fill=pal["bartext"], anchor="mm")
        draw_tracked(d, (x0 + 2 * r + 60, cy - 58), head, F.f("sans", 46, 600), pal["ink"], tracking=5)
        d.text((x0 + 2 * r + 60, cy + 6), body, font=F.f("sans", 38, 400), fill=mix(pal["ink"], pal["bg"], 0.25))


def card_paper(pal, F, poster, pair_txt):
    t = TEXT["PAPER"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    th = poster.resize((840, 1120), Image.LANCZOS)
    paste_shadowed(im, th, (330, 640))
    numbered_rows(d, F, pal, rows_of("PAPER"), 1400, 760, 212)
    return im


def tube_icon(pal):
    """Sade, cizgisel kargo tupu: kontur silindir + sag agiz halkasi + sol kapak; poster yok."""
    S = 3
    tw, th = 1150 * S, 300 * S
    ink, fill = pal["bar"], mix(pal["bar"], pal["bg"], 0.86)
    body = Image.new("RGBA", (tw + 60 * S, th + 20 * S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    lw = 7 * S
    bd.rounded_rectangle([30 * S, 10 * S, tw - 150 * S, th + 10 * S], radius=52 * S, fill=fill + (255,), outline=ink + (255,), width=lw)
    bd.ellipse([tw - 300 * S, 10 * S, tw, th + 10 * S], fill=fill + (255,), outline=ink + (255,), width=lw)        # sag agiz
    bd.ellipse([tw - 258 * S, 52 * S, tw - 42 * S, th - 32 * S], fill=mix(pal["bar"], pal["bg"], 0.6) + (255,), outline=ink + (255,), width=lw)  # ic bosluk
    bd.line([tw - 150 * S, 10 * S + lw, tw - 150 * S, th + 10 * S - lw], fill=fill + (255,), width=lw + 2)           # kavsak kapat
    bd.line([tw - 150 * S, 10 * S, tw - 150 * S, th + 10 * S], fill=ink + (255,), width=2 * S)
    bd.arc([30 * S - 40 * S, 10 * S, 30 * S + 60 * S, th + 10 * S], 270, 90, fill=ink + (255,), width=lw)            # sol kapak kavisi
    bd.line([120 * S, 10 * S + 30 * S, tw - 320 * S, 10 * S + 30 * S], fill=mix(ink, fill, 0.55) + (255,), width=2 * S)  # ince isik cizgisi
    body = body.resize((body.width // S, body.height // S), Image.LANCZOS)
    return body.rotate(30, expand=True, resample=Image.BICUBIC)


def card_care(pal, F, poster, pair_txt):
    t = TEXT["CARE"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    icon = tube_icon(pal)
    x, y = 200 + (1000 - icon.width) // 2, 700 + (1000 - icon.height) // 2
    im.paste(icon, (x, y), icon)
    numbered_rows(d, F, pal, rows_of("CARE"), 1400, 760, 212)
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


def card_sizes(pal, F, poster, pair_txt):
    t = TEXT["SIZES"]
    im, d = card_base(pal, F, vtext(t["kicker"]), t["title"], pair_txt, vtext(t["footer"]))
    s = 6.8                                   # px / cm
    floor_y = 1905
    hang = 52                                 # poster alt kenari yerden (cm)
    accent = pal["bar"]
    neutral_fill = mix(pal["ink"], pal["bg"], 0.90)
    neutral_line = mix(pal["ink"], pal["bg"], 0.45)
    label_col = mix(pal["ink"], pal["bg"], 0.15)
    d.line([250, floor_y, 2760, floor_y], fill=neutral_line, width=3)
    # siluet 175 cm
    sil = silhouette(175 * s, mix(pal["ink"], pal["bg"], 0.5))
    px = 400
    im.paste(sil, (px - sil.width // 2, floor_y - sil.height), sil)
    d = ImageDraw.Draw(im)
    if ok("S_human"):
        draw_tracked(d, (px, floor_y + 24), "175 CM \u00b7 5'9\"", F.f("sans", 26, 500), mix(pal["ink"], pal["bg"], 0.3), tracking=4, anchor="c")
    # 5 grup: esit aralikli sutunlar, ortak taban, alt-orta hizali ic ice dikdortgenler
    pitch, x0 = 430, 640
    base_y = floor_y - hang * s
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    labels = []
    for gi, g in enumerate(GROUP_ORDER):
        cxg = x0 + gi * pitch + pitch // 2
        items = sorted([z for z in SIZES if z[5] == g], key=lambda z: -z[4])
        for k, (lab, win, hin, wcm, hcm, _) in enumerate(items):
            w, h = wcm * s, hcm * s
            x1, y1 = cxg - w / 2, base_y - h
            od.rectangle([x1, y1, x1 + w, base_y], fill=(neutral_fill if k == 0 else pal["bg"]) + (255,),
                         outline=(accent if k == 0 else neutral_line) + (255,), width=4 if k == 0 else 3)
            labels.append(((cxg, y1 + 12), lab))
    im.paste(overlay, (0, 0), overlay)
    d = ImageDraw.Draw(im)
    for xy, lab in labels:
        d.text(xy, lab, font=F.f("sans", 27, 600), fill=label_col, anchor="ma")
    for gi, g in enumerate(GROUP_ORDER):
        cxg = x0 + gi * pitch + pitch // 2
        items = sorted([z for z in SIZES if z[5] == g], key=lambda z: -z[4])
        ly = base_y + 30
        draw_tracked(d, (cxg, ly), GROUP_TITLE[g], F.f("sans", 30, 700), accent, tracking=4, anchor="c")
        d.line([cxg - 60, ly + 44, cxg + 60, ly + 44], fill=accent, width=2)
        ly += 62
        for lab, win, hin, wcm, hcm, _ in items:
            line = f"{lab} in \u00b7 {wcm:g}\u00d7{hcm:g} cm" if not lab.startswith("A") else f"{lab} \u00b7 {win:g}\u00d7{hin:g} in \u00b7 {wcm:g}\u00d7{hcm:g} cm"
            d.text((cxg, ly), line, font=F.f("sans", 26, 400), fill=mix(pal["ink"], pal["bg"], 0.2), anchor="ma")
            ly += 36
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
                made.append((outno, what, "yeni", {"olcum": mp, "referans_sapma_max": dev}))
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
    log(f"bitti: {len(eds)} edisyon, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
