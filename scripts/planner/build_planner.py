#!/usr/bin/env python3
"""
AstroLove Couple Planner - tek dosya uretici (Mo spesifikasyonu, 13 Eyl 2026).

Ne yapar
  1. Poster'dan altin birlesik sembolu kirpar (RGBA seffaf PNG) veya hazir
     sembol PNG'sini kullanir. Sembol YENIDEN CIZILMEZ: RGB posterden birebir
     alinir, yalniz alfa maskesi uretilir. Aynalama/deformasyon yok.
  2. 126 sayfalik 1024 x 768 pt (4:3 yatay) planner kurar. Govde tamamen
     vektor; tek raster oge sembol (kapak 150 ppi, sekme ikonu 100 ppi).
  3. Iki surum yazar: hafta Pazartesi (MON) ve Pazar (SUN) baslangicli.
  4. Kod icinde dogrular: sayfa sayisi, kirik link, sayfa basina sekme+ikon
     linki, gomulu olmayan font, tipografi taramasi (em/en dash, bosluklu
     tire, Ingiliz yazimi, burca ozel kelimeler).
  5. PNG onizlemeleri 2732x2048 (gercek 4:3 oran) uretir.

78 ciftte degisen: kapak (sembol + burc adlari), ust baslikteki cift adi,
sekme ikonu, s.2'deki sablon paragraf. Baska sayfada burca ozel sozcuk yok.

Bagimlilik: pymupdf (fitz), pillow, numpy, scipy. Baska PDF kutuphanesi YOK.

Kullanim
  build_planner.py --poster ARIES_LEO.jpg --out OUT
  build_planner.py --symbol ARIES_LEO_MB.png --out OUT
  build_planner.py --poster ARIES_LEO.jpg --out OUT --symbol-only
"""
import argparse
import json
import math
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import fitz
import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None

# ----------------------------------------------------------------- sabitler
PAGE_W, PAGE_H = 1024.0, 768.0

NAVY = (0x1A / 255, 0x1A / 255, 0x2E / 255)
GOLD = (0xC9 / 255, 0xA2 / 255, 0x27 / 255)
CREAM = (0xF9 / 255, 0xF0 / 255, 0xDF / 255)

RULE_OP = 0.25          # grid ve yazma cizgileri: NAVY %25
FOOT_OP = 0.40

TAB_X0 = 930.0          # sag sekme seridi
ICON_PT = 40.0          # serit basindaki sembol ikonu genisligi
M_L = 56.0
M_R = TAB_X0 - 34.0     # 896.0
HDR_Y = 40.0
TITLE_Y = 88.0
SUB_Y = 110.0
BODY_T = 142.0
BODY_B = 716.0
FOOT_Y = 744.0

FOOT_L = "The Shape of Your Connection."
FOOT_C = "© 2026 AstroLove. Personal use only."

TABS = ["Home", "Plan", "Connect", "Reflect", "Remember", "Grow"]

WEEKS_PER_MONTH = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]      # 3-6-9-12 -> 5
DAYS_MON = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAYS_SUN = DAYS_MON[-1:] + DAYS_MON[:-1]

GF_CSS = ("https://fonts.googleapis.com/css2?"
          "family=Montserrat:wght@400;600&family=Playfair+Display:wght@400;700")


# --------------------------------------------------------------- yardimcilar
def rclone(*args):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {' '.join(args[:2])}: rc={r.returncode} "
                           f"{r.stderr.strip()[-200:]}")
    return r.stdout


def fetch_fonts(cache: Path):
    """Google Fonts'tan TTF indir (CSS -> gstatic). Dosyalar cache'te tutulur."""
    cache.mkdir(parents=True, exist_ok=True)
    want = {("Montserrat", "400"): "montserrat_400.ttf",
            ("Montserrat", "600"): "montserrat_600.ttf",
            ("Playfair Display", "400"): "playfair_400.ttf",
            ("Playfair Display", "700"): "playfair_700.ttf"}
    if all((cache / v).exists() for v in want.values()):
        return {k: cache / v for k, v in want.items()}

    req = urllib.request.Request(GF_CSS, headers={"User-Agent": "Mozilla/5.0"})
    css = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")

    fam = wgt = None
    found = {}
    for line in css.splitlines():
        s = line.strip()
        if s.startswith("font-family:"):
            fam = s.split("'")[1]
        elif s.startswith("font-weight:"):
            wgt = s.split(":")[1].strip().rstrip(";")
        elif s.startswith("src:") and fam and wgt:
            url = s.split("url(")[1].split(")")[0]
            found.setdefault((fam, wgt), url)

    out = {}
    for key, name in want.items():
        dst = cache / name
        if not dst.exists():
            if key not in found:
                raise RuntimeError(f"Google Fonts CSS'inde bulunamadi: {key}")
            dst.write_bytes(urllib.request.urlopen(found[key], timeout=60).read())
        # fitz.Font woff/woff2 okumaz; Google Fonts UA'ya gore format degistirir.
        if dst.read_bytes()[:4] in (b"wOFF", b"wOF2"):
            raise RuntimeError(f"{dst.name}: woff geldi, TTF bekleniyordu "
                               f"(Google Fonts UA pazarligi degismis)")
        out[key] = dst
    return out


# ------------------------------------------------------------ sembol kirpma
def extract_symbol(poster: Path, out_png: Path, preview_png: Path, pad=0.06):
    """
    Lacivert zeminli posterden ortadaki altin birlesik sembolu kirpar.

    Altin tonu maskelenir -> en buyuk baglantili bolge alinir (halka + fusion
    tek parcadir; baslik, isim satiri ve tagline ayri ve daha kucuktur) ->
    bbox + %6 pay -> alfa altinlik rampasi, RGB posterden BIREBIR.
    """
    im = Image.open(poster).convert("RGB")
    a8 = np.asarray(im)                     # uint8; tam boy int16 kopyasi ALINMAZ
    r, g, b = a8[..., 0], a8[..., 1], a8[..., 2]

    gold = (r > g) & (g > b) & ((r.astype(np.int16) - b) >= 40) & (r >= 80)
    if gold.sum() < 500:
        raise RuntimeError(f"altin maske bos ({int(gold.sum())} px) - poster beklenen "
                           f"lacivert/altin edisyon degil: {poster}")

    box3 = np.ones((3, 3), bool)
    clean = ndimage.binary_opening(gold, structure=box3)
    if clean.sum() < 500:
        clean = gold
    # 3x3 + iterations: kxk tek adim 20+ MP posterde O(k^2)/px olur.
    it = max(1, int(round(min(a8.shape[:2]) * 0.002)))
    joined = ndimage.binary_closing(clean, structure=box3, iterations=it)

    lab, n = ndimage.label(joined)
    if n == 0:
        raise RuntimeError("baglantili altin bolge yok")
    sizes = ndimage.sum(joined, lab, range(1, n + 1))
    comp = lab == int(np.argmax(sizes)) + 1

    ys, xs = np.where(comp)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = comp.shape
    py = int(round((y1 - y0 + 1) * pad))
    px = int(round((x1 - x0 + 1) * pad))
    y0, y1 = max(0, y0 - py), min(H - 1, y1 + py)
    x0, x1 = max(0, x0 - px), min(W - 1, x1 + px)

    sub = a8[y0:y1 + 1, x0:x1 + 1].astype(np.int16)
    subm = comp[y0:y1 + 1, x0:x1 + 1]

    lum = sub.mean(axis=2).astype(np.float32)
    bg = float(np.percentile(lum[~subm], 60)) if (~subm).any() else 0.0
    fg = float(np.percentile(lum[subm], 85))
    if fg - bg < 8:
        fg = bg + 8.0
    alpha = np.clip((lum - bg) / (fg - bg), 0.0, 1.0)
    grown = ndimage.binary_dilation(subm, structure=box3, iterations=2)
    alpha = np.where(grown, alpha, 0.0)

    rgba = np.dstack([sub.astype(np.uint8), (alpha * 255).round().astype(np.uint8)])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out_png, "PNG", optimize=True)

    sym = Image.open(out_png)
    sym.resize((800, max(1, round(sym.height * 800 / sym.width))),
               Image.LANCZOS).save(preview_png, "PNG", optimize=True)

    return {"poster": str(poster), "poster_px": [W, H],
            "bbox": [int(x0), int(y0), int(x1), int(y1)],
            "symbol_px": [int(x1 - x0 + 1), int(y1 - y0 + 1)],
            "component_area_frac": round(float(comp.sum()) / (H * W), 5),
            "components": int(n),
            "alpha_mean": round(float(alpha.mean()), 4)}


def check_symbol(info):
    W, H = info["poster_px"]
    x0, y0, x1, y1 = info["bbox"]
    w, h = x1 - x0 + 1, y1 - y0 + 1
    bad = []
    if not (0.01 <= info["component_area_frac"] <= 0.60):
        bad.append(f"bolge alani tuvalin %{info['component_area_frac'] * 100:.1f}'i")
    if w / W > 0.95 or h / H > 0.95:
        bad.append("bbox neredeyse tum poster")
    if not (0.15 < ((x0 + x1) / 2) / W < 0.85):
        bad.append("bbox yatayda ortali degil")
    if info["alpha_mean"] < 0.01:
        bad.append("alfa bos")
    return bad


# -------------------------------------------------------------------- metin
BEGIN_PARA = ("This planner was made for an Aries and a Leo. The signs are a "
              "starting point for curiosity, never a verdict. Make room for two "
              "individual lives and for the connection between them.")

HOW_TO = [
    ("01 SET UP ONCE",
     "Import the Monday or Sunday file into GoodNotes, Notability or your PDF "
     "app. Fill in Begin Together and Our Story."),
    ("02 PLAN IN TEN MINUTES",
     "Open a month, then choose a week. Each person fills Mine or Yours, then "
     "choose one Ours commitment."),
    ("03 CONNECT IN FIVE MINUTES",
     "Offer one specific appreciation. Pick a ritual, a question or a date idea."),
    ("04 REFLECT EACH MONTH",
     "Use the Monthly Check-in. Moon and planet pages are optional and undated."),
    ("05 DUPLICATE FREELY",
     "Date Night Plan, Memory Capsule and Notes are templates. Duplicate any "
     "page in your app as often as you like."),
]
HOW_TO_NOTE = ("Tap links in read mode. This PDF does not calculate or sync "
               "between two devices; agree on one keeper or share an updated "
               "copy. Astrology pages are reflection prompts, not predictions "
               "or advice.")

DATE_IDEAS = [
    "Cook something neither of us has made", "Sunset walk without phones",
    "Beginner class together", "Living room movie premiere",
    "Bookstore, one book each", "Picnic for a small win",
    "Board game night",
    "Visit somewhere we have never been in our own city",
    "Breakfast date", "Museum and one question each",
    "Rewatch our first film", "Volunteer together",
    "Stargazing with blankets", "Plan a fantasy trip",
    "Cook for friends", "Long drive, shared playlist",
    "Photo walk", "Farmers market and cook the haul",
    "Karaoke at home", "Take turns planning a surprise hour",
    "Write letters to future us", "Try a new cafe",
    "Dance in the kitchen", "Do nothing together, on purpose",
]

DATE_MATRIX = [
    ("BOLD DATE", "Try something new together.", "Active / out"),
    ("WARM DATE", "Cook a favorite meal and trade appreciations.", "Low energy / home"),
    ("PLAYFUL DATE", "Invent a silly game with no real stakes.", "Flexible / home"),
    ("SLOW DATE", "A long walk and one honest question.", "Low energy / out"),
    ("COZY DATE", "Dress up for a living room premiere.", "Medium / home"),
    ("CELEBRATION NIGHT", "Toast a small win with dessert.", "Flexible / either"),
]

DECK_Q = [
    "When do you feel most appreciated by me?",
    "What would brave love look like this week?",
    "Where do we compete when we could cooperate?",
    "What ordinary moment with us feels precious?",
    "When does my enthusiasm feel supportive?",
    "How do you like to share the spotlight?",
    "What kind of play brings us closer?",
    "Which boundary helps you stay open?",
    "What would make our home feel more like us?",
    "What small win deserves a celebration?",
    "What do you want future us to remember?",
    "What would help us choose kindness over being right?",
]

WEEK_PROMPTS = [
    "This week we choose...",
    "One brave gesture we choose...",
    "One moment of appreciation...",
    "One thing we will not turn into a competition...",
    "Where we choose kindness over being right...",
    "One small act of loyalty...",
    "One invitation to play...",
    "One boundary that protects our closeness...",
    "One way we share the spotlight...",
    "One wish we can voice honestly...",
    "One everyday moment worth celebrating...",
    "One quiet way to reconnect...",
    "One promise we can actually keep...",
]

REPAIR = [
    ("01 PAUSE", "Step back before the conversation hardens. Agree on a short "
                 "break and a time to return."),
    ("02 NAME IT", "Say what happened in plain words, without a verdict about "
                   "who someone is."),
    ("03 HEAR THE NEED", "Listen for the need under the complaint. Repeat it back "
                         "before answering."),
    ("04 RETURN TO RESPECT", "Drop the score. Neither of us has to lose for the "
                             "other one to be heard."),
    ("05 REPAIR IN ACTION", "Choose one specific action, small enough to actually "
                            "happen this week."),
]

MOON_FIELDS = {
    "New Moon Intention": ("A quiet start, written in your own words.",
                           ["Date / Moon sign / source",
                            "What we are beginning",
                            "What each of us needs to start it",
                            "One first step this week"]),
    "Full Moon Reflection": ("A pause to notice what has grown.",
                             ["Date / Moon sign / source",
                              "What became clear",
                              "What we are ready to release",
                              "What we want to keep"]),
    "Venus Notes": ("Warmth, taste and the way we show care.",
                    ["Date / Venus sign / source",
                     "How affection felt this cycle",
                     "What we want more of",
                     "One gesture to offer"]),
    "Mars Notes": ("Drive, initiative and how we handle friction.",
                   ["Date / Mars sign / source",
                    "Where our energy went",
                    "What we want to move on",
                    "One action we take together"]),
}


# ----------------------------------------------------------------- painter
class Painter:
    """Tek sayfa: metin renge gore gruplanir, linkler ve metinler kaydedilir."""

    def __init__(self, page, fonts):
        self.page = page
        self.fonts = fonts
        self._tw = {}
        self.links = []
        self.strings = []      # (metin, chrome?) - dogrulama icin

    def _f(self, name, bold):
        return self.fonts[(name, bold)]

    def width(self, s, name="mont", size=9, bold=False, track=0.0):
        w = self._f(name, bold).text_length(s, size)
        return w + track * max(0, len(s) - 1)

    def text(self, x, y, s, name="mont", size=9, color=NAVY, bold=False,
             align="l", opacity=1.0, track=0.0, chrome=False):
        f = self._f(name, bold)
        w = self.width(s, name, size, bold, track)
        if align == "c":
            x -= w / 2
        elif align == "r":
            x -= w
        key = (color, round(opacity, 3))
        tw = self._tw.get(key)
        if tw is None:
            tw = fitz.TextWriter(self.page.rect)
            self._tw[key] = tw
        if track:
            for ch in s:
                tw.append((x, y), ch, font=f, fontsize=size)
                x += f.text_length(ch, size) + track
        else:
            tw.append((x, y), s, font=f, fontsize=size)
        self.strings.append((s, chrome))
        return w

    def wrap(self, x0, x1, y, s, name="mont", size=8.6, color=NAVY,
             leading=12.0, opacity=1.0, chrome=False):
        f = self._f(name, False)
        words, line, out = s.split(" "), "", []
        for wd in words:
            t = (line + " " + wd).strip()
            if f.text_length(t, size) > (x1 - x0) and line:
                out.append(line)
                line = wd
            else:
                line = t
        if line:
            out.append(line)
        for i, ln in enumerate(out):
            self.text(x0, y + i * leading, ln, name=name, size=size,
                      color=color, opacity=opacity, chrome=chrome)
        self.strings.append((s, chrome))
        return y + (len(out) - 1) * leading

    def line(self, x0, y0, x1, y1, color=NAVY, width=0.6, opacity=RULE_OP):
        self.page.draw_line((x0, y0), (x1, y1), color=color, width=width,
                            stroke_opacity=opacity)

    def rect(self, x0, y0, x1, y1, color=NAVY, fill=None, width=0.6,
             opacity=RULE_OP, fill_opacity=1.0):
        self.page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=color, fill=fill,
                            width=width, stroke_opacity=opacity,
                            fill_opacity=fill_opacity)

    def goto(self, x0, y0, x1, y1, target):
        self.links.append({"kind": fitz.LINK_GOTO, "page": target,
                           "from": fitz.Rect(x0, y0, x1, y1),
                           "to": fitz.Point(0, 0)})

    def flush(self):
        for (color, op), tw in self._tw.items():
            tw.write_text(self.page, color=color, opacity=op)
        for lk in self.links:
            self.page.insert_link(lk)


# ------------------------------------------------------------- yapi taslari
def rules(p, x0, x1, y0, n, gap):
    for i in range(n):
        p.line(x0, y0 + i * gap, x1, y0 + i * gap)


def field(p, x0, x1, y, h, label, sub=None, min_lines=3):
    """Etiketli yazma alani: verilen yuksekligi cizgilerle doldurur."""
    p.text(x0, y + 8, label.upper(), size=7.4, bold=True, color=GOLD, track=0.5)
    top = y + 12
    if sub:
        p.text(x0, top + 10, sub, size=7.4, color=NAVY, opacity=0.55)
        top += 13
    avail = h - (top - y) - 4
    n = max(min_lines, int(avail // 21))
    gap = avail / n
    for i in range(1, n + 1):
        p.line(x0, top + i * gap, x1, top + i * gap)
    return n


def field_grid(p, specs, cols, top, bottom, gx=28.0, gy=14.0, min_lines=3):
    """specs: (label, sub) listesi. Izgarayi top..bottom arasina yayar."""
    rows = math.ceil(len(specs) / cols)
    cw = (M_R - M_L - gx * (cols - 1)) / cols
    ch = (bottom - top + gy) / rows
    for i, spec in enumerate(specs):
        label, sub = spec if isinstance(spec, tuple) else (spec, None)
        r, c = divmod(i, cols)
        field(p, M_L + c * (cw + gx), M_L + c * (cw + gx) + cw,
              top + r * ch, ch - gy, label, sub, min_lines)


def table(p, headers, fracs, nrows, top, bottom, boxes_last=False):
    """Basliklari altin, satirlari %25 navy cizgi olan tablo."""
    total = M_R - M_L
    xs, acc = [], M_L
    for fr in fracs:
        xs.append(acc)
        acc += total * fr
    for h, x in zip(headers, xs):
        p.text(x, top, h, size=7.4, bold=True, color=GOLD, track=0.5)
    p.line(M_L, top + 7, M_R, top + 7, color=GOLD, width=1.0, opacity=0.9)
    gap = (bottom - (top + 30)) / max(1, nrows - 1)
    for i in range(nrows):
        y = top + 30 + i * gap
        p.line(M_L, y, M_R, y)
        for x in xs[1:]:
            p.line(x - 12, y - gap + 4, x - 12, y, opacity=0.16)
        if boxes_last:
            p.rect(xs[-1], y - 11, xs[-1] + 10, y - 1)
    return xs


def buttons(p, items, y, h=22.0, w=None, right=True):
    """items: (etiket, hedef). Sagdan sola dizer, her biri LINK_GOTO."""
    ws = [max(w or 0, p.width(t, size=7.4, bold=True, track=0.6) + 26)
          for t, _ in items]
    x = M_R - sum(ws) - 10 * (len(items) - 1) if right else M_L
    for (label, target), bw in zip(items, ws):
        p.rect(x, y, x + bw, y + h, color=NAVY, width=0.7, opacity=0.5)
        p.text(x + bw / 2, y + 15, label, size=7.4, bold=True, align="c",
               track=0.6, chrome=True)
        p.goto(x, y, x + bw, y + h, target)
        x += bw + 10


# ------------------------------------------------------------------ cerceve
def draw_chrome(p, plan, spec, pno, icon_png, icon_state):
    """Ust baslik, sekme seridi ve alt bilgi. Kapak disi HER sayfada."""
    p.text(M_L, HDR_Y, f"ASTROLOVE  /  {plan.pair_label}", size=7.0,
           color=GOLD, bold=True, track=1.6, chrome=True)

    p.rect(TAB_X0, 0, PAGE_W, PAGE_H, color=None, fill=NAVY, width=0)
    iw, ih = icon_state["size_pt"]
    ix = TAB_X0 + (PAGE_W - TAB_X0 - iw) / 2
    icon_state["xref"] = p.page.insert_image(
        fitz.Rect(ix, 16, ix + iw, 16 + ih), filename=icon_png,
        xref=icon_state.get("xref", 0))
    p.goto(TAB_X0, 0, PAGE_W, 16 + ih + 10, plan.home)
    p.line(TAB_X0 + 16, 16 + ih + 14, PAGE_W - 16, 16 + ih + 14,
           color=GOLD, opacity=0.35)

    top = 16 + ih + 22
    th = (PAGE_H - top) / len(TABS)
    for i, name in enumerate(TABS):
        ty = top + i * th
        on = (name == spec["tab"])
        if on:
            p.rect(TAB_X0 + 5, ty + 4, PAGE_W - 5, ty + th - 4, color=None,
                   fill=GOLD, width=0)
        p.text((TAB_X0 + PAGE_W) / 2, ty + th / 2 + 3, name, size=8.0,
               bold=True, color=NAVY if on else GOLD, align="c", track=0.5,
               chrome=True)
        p.goto(TAB_X0, ty, PAGE_W, ty + th, plan.tab_target[name])

    p.text(M_L, FOOT_Y, FOOT_L, size=7.6, color=NAVY, opacity=FOOT_OP,
           chrome=True)
    p.text((M_L + M_R) / 2, FOOT_Y, FOOT_C, size=7.0, color=NAVY,
           opacity=FOOT_OP, align="c", chrome=True)
    p.text(M_R, FOOT_Y, str(pno + 1), size=7.6, color=NAVY, opacity=FOOT_OP,
           align="r", chrome=True)


def head(p, title, sub=None):
    p.text(M_L, TITLE_Y, title, name="pf", size=30, bold=True, color=NAVY)
    p.line(M_L, TITLE_Y + 12, M_L + 86, TITLE_Y + 12, color=GOLD, width=1.6,
           opacity=1.0)
    if sub:
        p.text(M_L, SUB_Y + 14, sub, size=10, color=NAVY, opacity=0.72)


# ------------------------------------------------------------ sayfa cizimi
def pg_cover(p, plan, sym_png, sym_pt, week_start):
    p.rect(0, 0, PAGE_W, PAGE_H, color=None, fill=NAVY, width=0)
    p.rect(30, 30, PAGE_W - 30, PAGE_H - 30, color=GOLD, width=0.8, opacity=0.4)
    p.text(PAGE_W / 2, 84, "ASTROLOVE", size=9, bold=True, color=GOLD,
           align="c", track=5.0)

    sw, sh = sym_pt
    sx, sy = (PAGE_W - sw) / 2, 178.0
    p.page.insert_image(fitz.Rect(sx, sy, sx + sw, sy + sh), filename=sym_png)

    y = sy + sh + 74
    p.text(PAGE_W / 2, y, plan.cover_title, name="pf", size=44, bold=True,
           color=GOLD, align="c")
    p.text(PAGE_W / 2, y + 30, "THE COUPLE PLANNER", size=9, bold=True,
           color=GOLD, align="c", track=3.0)
    p.text(PAGE_W / 2, y + 68, "Two individuals. One connection.", name="pf",
           size=14, color=CREAM, align="c")

    p.text(PAGE_W / 2, PAGE_H - 96, FOOT_L, name="pf", size=12, color=CREAM,
           align="c", opacity=0.8)
    start = "MONDAY START" if week_start == "MON" else "SUNDAY START"
    p.text(PAGE_W / 2, PAGE_H - 66, f"MIDNIGHT BLUE  /  {start}  /  UNDATED",
           size=7.6, bold=True, color=GOLD, align="c", track=1.8)
    p.goto(0, 0, PAGE_W, PAGE_H, plan.home)


def pg_begin(p, plan):
    head(p, "Begin Together", "Two people, one shared practice.")
    field_grid(p, [("Me / name and sign", None), ("You / name and sign", None),
                   ("Our year begins", None), ("Our shared word", None)],
               2, BODY_T, 544)
    p.rect(M_L, 566, M_R, 694, color=None, fill=NAVY, width=0)
    p.text(M_L + 26, 598, "MINE. YOURS. OURS.", size=9, bold=True, color=GOLD,
           track=2.0)
    p.wrap(M_L + 26, M_R - 26, 626, BEGIN_PARA, size=10.5, color=CREAM,
           leading=19)


def pg_howto(p, plan):
    head(p, "How to Use This Planner", "A light routine, not another obligation.")
    top, bot = BODY_T, BODY_B - 46
    rh = (bot - top) / len(HOW_TO)
    for i, (label, body) in enumerate(HOW_TO):
        y = top + i * rh + 26
        p.text(M_L, y, label, size=8.4, bold=True, color=GOLD, track=1.0)
        p.wrap(M_L + 226, M_R, y, body, size=9.6, leading=15)
        p.line(M_L, top + (i + 1) * rh, M_R, top + (i + 1) * rh, opacity=0.16)
    p.wrap(M_L, M_R, BODY_B - 8, HOW_TO_NOTE, size=8, opacity=0.62, leading=12)


def pg_home(p, plan):
    head(p, "Your Shared Orbit", "Choose what you need today.")
    cards = [("01", "Begin", "Setup and story", plan.begin),
             ("02", "Plan", "Year, months and weeks", plan.plan_div),
             ("03", "Connect", "Dates, play and appreciation", plan.connect_div),
             ("04", "Reflect", "Check-ins and moon pages", plan.reflect_div),
             ("05", "Remember", "Photos, trips and milestones", plan.remember_div),
             ("06", "Grow", "Goals, money and notes", plan.grow_div)]
    gx, gy = 26.0, 22.0
    cw = (M_R - M_L - gx * 2) / 3
    ch = (BODY_B - 54 - BODY_T - gy) / 2
    for i, (num, name, desc, tgt) in enumerate(cards):
        r, c = divmod(i, 3)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.rect(x, y, x + cw, y + ch)
        p.text(x + 20, y + 34, num, size=8.4, bold=True, color=GOLD, track=1.2)
        p.line(x + 20, y + 44, x + 44, y + 44, color=GOLD, width=1.2, opacity=1.0)
        p.text(x + 20, y + ch - 62, name, name="pf", size=22, bold=True, color=NAVY)
        p.text(x + 20, y + ch - 38, desc, size=9, color=NAVY, opacity=0.66)
        p.goto(x, y, x + cw, y + ch, tgt)
    buttons(p, [("OUR STORY", plan.story), ("DATES THAT MATTER", plan.dates),
                ("HOW TO USE", plan.howto), ("ALL WEEKS", plan.weeks_idx)],
            BODY_B - 24)


def pg_story(p, plan):
    head(p, "Our Story", "How we met, and how we keep meeting.")
    field_grid(p, ["How we met", "The first moment I knew",
                   "What we have built so far",
                   "The story we want to write next"],
               1, BODY_T, BODY_B, min_lines=4)


def pg_who(p, plan):
    head(p, "Who We Are",
         "Meet the person, not the sign. Complete separately, then compare.")
    field_grid(p, ["What energizes me", "What energizes you",
                   "What support looks like for me",
                   "What support looks like for you",
                   "What we protect together",
                   "One question we have never asked each other"],
               2, BODY_T, BODY_B)


def pg_dates(p, plan):
    head(p, "Dates That Matter",
         "Birthdays, anniversaries and the ordinary milestones.")
    table(p, ["DATE", "OCCASION", "HOW WE WILL MARK IT"],
          [0.0, 0.18, 0.52], 12, BODY_T, BODY_B)


def pg_divider(p, plan, spec):
    head(p, spec["title"], spec["sub"])
    items = spec["items"]
    top = BODY_T
    rh = (BODY_B - top) / len(items)
    size = 20 if len(items) <= 5 else 17
    for i, (label, tgt) in enumerate(items):
        y0 = top + i * rh
        yb = y0 + rh / 2 + size * 0.34
        p.text(M_L, yb, f"{i + 1:02d}", size=7.6, bold=True, color=GOLD, track=0.8)
        p.text(M_L + 46, yb, label, name="pf", size=size, color=NAVY)
        p.text(M_R, yb, str(tgt + 1), size=8.4, color=GOLD, align="r")
        p.line(M_L, y0 + rh, M_R, y0 + rh, opacity=0.16)
        p.goto(M_L, y0, M_R, y0 + rh, tgt)


def pg_year(p, plan):
    head(p, "Year at a Glance", "Write the month and year. Tap a card to open it.")
    gx, gy = 20.0, 18.0
    cw = (M_R - M_L - gx * 3) / 4
    ch = (BODY_B - 40 - BODY_T - gy * 2) / 3
    for m in range(12):
        r, c = divmod(m, 4)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.rect(x, y, x + cw, y + ch)
        p.text(x + 12, y + 20, f"MONTH {m + 1:02d}", size=7.4, bold=True,
               color=GOLD, track=0.8)
        rules(p, x + 12, x + cw - 12, y + 44, 2, 26)
        p.goto(x, y, x + cw, y + ch, plan.month_plan[m])
    buttons(p, [("ALL WEEKS", plan.weeks_idx)], BODY_B - 22)


def pg_weeks_index(p, plan):
    head(p, "Your 52 Weeks",
         "Choose a week, write the dates, return here any time.")
    cols, rowsn = 8, 7
    gx, gy = 12.0, 12.0
    cw = (M_R - M_L - gx * (cols - 1)) / cols
    ch = (BODY_B - BODY_T - gy * (rowsn - 1)) / rowsn
    for w in range(52):
        r, c = divmod(w, cols)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.rect(x, y, x + cw, y + ch)
        p.text(x + cw / 2, y + 22, f"{w + 1:02d}", name="pf", size=17,
               color=NAVY, align="c")
        p.line(x + 10, y + ch - 14, x + cw - 10, y + ch - 14, opacity=0.16)
        p.goto(x, y, x + cw, y + ch, plan.week[w])


def pg_month_plan(p, plan, m, days):
    head(p, f"Month {m + 1:02d} Plan",
         "Name the month. Choose the feeling. Protect the time.")
    top = BODY_T + 6
    tw = (M_R - M_L) / 3 - 16
    for i, lab in enumerate(["Month and year", "Our intention",
                             "One date we protect"]):
        x = M_L + i * (tw + 24)
        p.text(x, top, lab.upper(), size=7.2, bold=True, color=GOLD, track=0.5)
        p.line(x, top + 18, x + tw, top + 18)

    gtop, gright = top + 40, M_L + 596
    cw = (gright - M_L) / 7
    for i, d in enumerate(days):
        p.text(M_L + cw * (i + 0.5), gtop, d, size=7.2, bold=True, color=GOLD,
               align="c", track=0.5)
    p.line(M_L, gtop + 7, gright, gtop + 7, opacity=0.45)
    g0 = gtop + 14
    rh = (BODY_B - 34 - g0) / 6
    wks = plan.month_weeks[m]
    for r in range(6):
        y = g0 + r * rh
        p.rect(M_L, y, gright, y + rh)
        for c in range(1, 7):
            p.line(M_L + c * cw, y, M_L + c * cw, y + rh, opacity=0.16)
        if r < len(wks):
            p.text(M_L + 5, y + 11, f"W{wks[r] + 1:02d}", size=6.2, bold=True,
                   color=GOLD, opacity=0.85)
            p.goto(M_L, y, gright, y + rh, plan.week[wks[r]])

    sx = gright + 26
    side = [("More closeness", "One action, not a promise."),
            ("One brave shared step", "Keep it small and mutual."),
            ("One thing to celebrate", "Big or ordinary.")]
    sh = (BODY_B - 34 - gtop) / 3
    for i, (lab, sub) in enumerate(side):
        field(p, sx, M_R, gtop + i * sh, sh - 12, lab, sub)

    buttons(p, [("MONTHLY INTENTIONS", plan.month_int[m]),
                ("ALL MONTHS", plan.year), ("ALL WEEKS", plan.weeks_idx),
                ("PREV", plan.month_plan[(m - 1) % 12]),
                ("NEXT", plan.month_plan[(m + 1) % 12])], BODY_B - 22)


def pg_month_int(p, plan, m):
    head(p, f"Month {m + 1:02d} Intentions", "Intentions, not predictions.")
    field_grid(p, ["Our theme this month",
                   "What would help both of us thrive",
                   "One pattern we want to soften",
                   "New Moon intention", "Full Moon reflection",
                   "What feels loving this month",
                   "How we take action this month"],
               2, BODY_T, BODY_B - 34)
    buttons(p, [("BACK TO MONTH", plan.month_plan[m]),
                ("MONTHLY CHECK-IN", plan.checkin)], BODY_B - 22)


def pg_week(p, plan, w, days):
    m = plan.week_month[w]
    head(p, f"Week {w + 1:02d}",
         "Plan two lives without losing the life you share.")
    top = BODY_T + 6
    tw = (M_R - M_L) / 2 - 20
    for i, lab in enumerate(["Dates", "This week we want to feel"]):
        x = M_L + i * (tw + 40)
        p.text(x, top, lab.upper(), size=7.2, bold=True, color=GOLD, track=0.5)
        p.line(x, top + 18, x + tw, top + 18)

    gtop = top + 38
    gbot = gtop + 226
    cw = (M_R - M_L) / 7
    for i, d in enumerate(days):
        x = M_L + i * cw
        p.rect(x, gtop, x + cw, gbot)
        p.rect(x, gtop, x + cw, gtop + 18, color=None, fill=NAVY, width=0,
               fill_opacity=0.06)
        p.text(x + cw / 2, gtop + 13, d, size=7.2, bold=True, color=GOLD,
               align="c", track=0.5)
        rules(p, x + 6, x + cw - 6, gtop + 40, 6, (gbot - 12 - gtop - 40) / 5)

    btop = gbot + 20
    bbot = BODY_B - 60
    bw = (M_R - M_L) / 3 - 18
    trio = [("MINE", "My priority / support I need"),
            ("YOURS", "Your priority / support you need"),
            ("OURS", "Our protected time / shared action")]
    for i, (lab, sub) in enumerate(trio):
        x = M_L + i * (bw + 27)
        p.rect(x, btop, x + bw, bbot)
        p.text(x + 12, btop + 18, lab, size=8, bold=True, color=GOLD, track=1.4)
        p.text(x + 12, btop + 33, sub, size=7.4, opacity=0.6)
        rules(p, x + 12, x + bw - 12, btop + 52, 4, (bbot - 12 - btop - 52) / 3)

    p.text(M_L, bbot + 22, WEEK_PROMPTS[w % len(WEEK_PROMPTS)], name="pf",
           size=12, color=NAVY)
    p.line(M_L + p.width(WEEK_PROMPTS[w % len(WEEK_PROMPTS)], "pf", 12) + 14,
           bbot + 22, M_R, bbot + 22)

    prev = plan.weeks_idx if w == 0 else plan.week[w - 1]
    nxt = plan.weeks_idx if w == 51 else plan.week[w + 1]
    buttons(p, [("BACK TO MONTH", plan.month_plan[m]),
                ("WEEK INDEX", plan.weeks_idx),
                ("CONNECTION RITUALS", plan.rituals),
                ("PREV", prev), ("NEXT", nxt)], BODY_B - 22)


def pg_date_ideas(p, plan):
    head(p, "Date Night Ideas",
         "Twenty-four starting points. Circle what you both want.")
    cols = 3
    colw = (M_R - M_L - 40) / cols
    per = 8
    gap = (BODY_B - BODY_T) / per
    for i, idea in enumerate(DATE_IDEAS):
        c, r = divmod(i, per)
        x, y = M_L + c * (colw + 20), BODY_T + 12 + r * gap
        p.rect(x, y - 8, x + 9, y + 1)
        p.wrap(x + 18, x + colw - 8, y, idea, size=8.8, leading=12)


def pg_date_matrix(p, plan):
    head(p, "Date Night Matrix",
         "Choose the mood, then agree on time, energy and budget.")
    gx, gy = 24.0, 20.0
    cw = (M_R - M_L - gx * 2) / 3
    ch = (BODY_B - 40 - BODY_T - gy) / 2
    for i, (name, desc, tag) in enumerate(DATE_MATRIX):
        r, c = divmod(i, 3)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.rect(x, y, x + cw, y + ch)
        p.text(x + 18, y + 30, name, size=8.4, bold=True, color=GOLD, track=1.0)
        p.wrap(x + 18, x + cw - 18, y + 54, desc, size=9.6, leading=14)
        p.text(x + 18, y + ch - 18, tag, size=7.6, opacity=0.6)
        rules(p, x + 18, x + cw - 18, y + 96, 3, (ch - 34 - 96) / 2)
    buttons(p, [("PLAN OUR DATE", plan.date_plan)], BODY_B - 22)


def pg_date_plan(p, plan):
    head(p, "Date Night Plan", "A plan with room for spontaneity.")
    field_grid(p, [("The invitation / what, when, where, budget", None),
                   ("A detail just for you", None),
                   ("Comfort and preferences", None),
                   ("Afterwards / what we keep", None)],
               2, BODY_T, BODY_B, min_lines=4)


def pg_bucket(p, plan):
    head(p, "Our Bucket List", "Big dreams and small firsts.")
    table(p, ["WHAT", "WHY US", "WHEN", "DONE"], [0.0, 0.36, 0.68, 0.88],
          12, BODY_T, BODY_B, boxes_last=True)


def pg_decide(p, plan):
    head(p, "How We Decide Together",
         "Share initiative, decisions and the spotlight.")
    field_grid(p, ["Where I want to lead", "Where you want to lead",
                   "Where we decide together", "How we hand over"],
               2, BODY_T, BODY_B, min_lines=4)


def pg_seen(p, plan):
    head(p, "What Makes Us Feel Seen",
         "Specific appreciation is more personal than general praise.")
    field_grid(p, ["I feel seen when...", "You feel seen when...",
                   "Private or public?",
                   "One appreciation to give this week"],
               2, BODY_T, BODY_B, min_lines=4)


def pg_disagree(p, plan):
    head(p, "When We Disagree", "Understanding does not require agreement.")
    field_grid(p, ["What I am defending", "What you want understood",
                   "What we can both acknowledge", "Our next conversation"],
               2, BODY_T, BODY_B, min_lines=4)


def pg_invitations(p, plan):
    head(p, "Small Invitations",
         "Choose one. A no, a pause or a smaller version is welcome.")
    field_grid(p, ["Tell the small truth", "Ask without testing",
                   "Try something new", "Return to kindness"],
               2, BODY_T, BODY_B, min_lines=4)


def pg_rituals(p, plan):
    head(p, "Connection Rituals", "One sustainable ritual at each rhythm.")
    field_grid(p, [("Daily / a moment of attention", None),
                   ("Weekly / protected time", None),
                   ("Monthly / a pause to celebrate", None),
                   ("Seasonally / our shared future", None)],
               2, BODY_T, BODY_B, min_lines=4)


def pg_loved(p, plan):
    head(p, "How We Feel Loved",
         "Preferences are personal and can change. Ask rather than assume.")
    specs = ["Words and attention", "Time and practical care",
             "Touch and closeness", "Gifts and gestures"]
    gx, gy = 28.0, 18.0
    cw = (M_R - M_L - gx) / 2
    ch = (BODY_B - BODY_T - gy) / 2
    for i, lab in enumerate(specs):
        r, c = divmod(i, 2)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.text(x, y + 8, lab.upper(), size=7.4, bold=True, color=GOLD, track=0.5)
        for j, who in enumerate(["Mine", "Yours"]):
            yy = y + 34 + j * ((ch - 44) / 2)
            p.text(x, yy, who, size=7.6, color=NAVY, opacity=0.6)
            rules(p, x + 44, x + cw, yy + 14, 2, (ch - 60) / 4)


def pg_deck(p, plan):
    head(p, "Conversation Deck",
         "Pick one question. Take turns. Listen before solving.")
    gx, gy = 24.0, 16.0
    cw = (M_R - M_L - gx) / 2
    ch = (BODY_B - BODY_T - gy * 5) / 6
    for i, q in enumerate(DECK_Q):
        c, r = divmod(i, 6)
        x, y = M_L + c * (cw + gx), BODY_T + r * (ch + gy)
        p.rect(x, y, x + cw, y + ch)
        p.text(x + 14, y + ch / 2 + 4, f"{i + 1:02d}", size=7.6, bold=True,
               color=GOLD)
        p.wrap(x + 42, x + cw - 14, y + ch / 2 + 4, q, size=9.4, leading=13)


def pg_checkin(p, plan):
    head(p, "Monthly Check-in",
         "Twenty minutes. Each person speaks for themselves.")
    field_grid(p, ["What felt warm between us",
                   "Where did we get in our own way",
                   "What do I need more of", "What do you need more of",
                   "What are we proud of", "What do we protect next month"],
               2, BODY_T, BODY_B)


def pg_compass(p, plan):
    head(p, "Connection Compass",
         "No score, no ideal shape. Mark where you want more attention.")
    cx, cy, R = 300.0, 430.0, 150.0
    for k in (1, 2, 3):
        r = R * k / 3
        p.page.draw_circle((cx, cy), r, color=NAVY, width=0.6,
                           stroke_opacity=RULE_OP)
    axes = [("CLOSENESS", 0, -1), ("PLAY", 1, 0),
            ("STABILITY", 0, 1), ("SPACE", -1, 0)]
    for label, dx, dy in axes:
        p.line(cx, cy, cx + dx * R, cy + dy * R, opacity=RULE_OP)
        lx, ly = cx + dx * (R + 26), cy + dy * (R + 26)
        p.text(lx, ly + (4 if dy == 0 else (0 if dy < 0 else 8)), label,
               size=7.4, bold=True, color=GOLD, align="c", track=0.6)
    p.text(M_L, BODY_B - 4, "Use initials or two different marks.", size=8,
           opacity=0.62)

    sx = 520.0
    sh = (BODY_B - 30 - BODY_T) / 3
    for i, lab in enumerate(["What I notice", "What you notice",
                             "One gentle adjustment"]):
        field(p, sx, M_R, BODY_T + i * sh, sh - 14, lab)


def pg_repair(p, plan):
    head(p, "Repair and Reconnect", "Name what happened without throwing it.")
    top, bot = BODY_T, BODY_B - 92
    rh = (bot - top) / len(REPAIR)
    for i, (label, body) in enumerate(REPAIR):
        y = top + i * rh + 24
        p.text(M_L, y, label, size=8.4, bold=True, color=GOLD, track=1.0)
        p.wrap(M_L + 210, M_R, y, body, size=9.6, leading=15)
        p.line(M_L, top + (i + 1) * rh, M_R, top + (i + 1) * rh, opacity=0.16)
    field(p, M_L, M_R, bot + 6, BODY_B - bot - 6, "What we agreed")


def pg_moon(p, plan, title):
    sub, fields = MOON_FIELDS[title]
    head(p, title, sub)
    field_grid(p, fields, 2, BODY_T, BODY_B, min_lines=4)


def pg_memory(p, plan):
    head(p, "Memory Capsule", "Keep the detail, not only the date.")
    gx = 30.0
    cw = (M_R - M_L - gx) / 2
    for c in range(2):
        x = M_L + c * (cw + gx)
        p.rect(x, BODY_T, x + cw, BODY_T + 250, opacity=0.35)
        p.text(x + cw / 2, BODY_T + 128, "photo", size=8.4, align="c",
               opacity=0.3)
        field(p, x, x + cw, BODY_T + 262, 60, "Date / place")
        field(p, x, x + cw, BODY_T + 330, BODY_B - (BODY_T + 330),
              "The detail and the feeling", min_lines=4)


def pg_travel(p, plan):
    head(p, "Travel Wish List", "Places we keep talking about.")
    table(p, ["DESTINATION", "WHY US", "SEASON", "BUDGET", "DONE"],
          [0.0, 0.26, 0.56, 0.72, 0.9], 10, BODY_T, BODY_B, boxes_last=True)


def pg_celebration(p, plan):
    head(p, "Celebration Notes", "Small wins counted out loud.")
    field_grid(p, ["What we are celebrating", "Who noticed it first",
                   "How we marked it", "What it told us about us"],
               2, BODY_T, BODY_B, min_lines=4)


def pg_movies(p, plan):
    head(p, "Movies and Books",
         "What we watched, what we read, what we talked about.")
    mid = BODY_T + (BODY_B - BODY_T) / 2
    for label, top, bot in [("WATCHED", BODY_T, mid - 26),
                            ("READ", mid + 6, BODY_B)]:
        p.text(M_L, top, label, size=7.6, bold=True, color=GOLD, track=1.2)
        xs = []
        total = M_R - M_L
        acc = M_L
        for fr in [0.0, 0.42, 0.56, 0.76]:
            xs.append(M_L + total * fr)
        for h, x in zip(["TITLE", "DATE", "OUR RATING", "ONE LINE"], xs):
            p.text(x, top + 20, h, size=7.2, bold=True, color=GOLD, track=0.5)
        p.line(M_L, top + 27, M_R, top + 27, color=GOLD, width=1.0, opacity=0.9)
        gap = (bot - (top + 48)) / 5
        for i in range(6):
            y = top + 48 + i * gap
            p.line(M_L, y, M_R, y)
            for x in xs[1:]:
                p.line(x - 12, y - gap + 4, x - 12, y, opacity=0.16)
            for s in range(5):
                p.rect(xs[2] + s * 15, y - 12, xs[2] + 10 + s * 15, y - 2)


def pg_goals(p, plan):
    head(p, "Shared Goals", "A vision, not a scorecard.")
    field_grid(p, ["What we are building this year",
                   "Why it matters to both of us",
                   "The first step we can take", "How we will know it is working",
                   "What we will stop doing", "Who we ask for help"],
               2, BODY_T, BODY_B)


def pg_money(p, plan):
    head(p, "Shared Money", "Plain numbers, shared decisions.")
    table(p, ["CATEGORY", "PLANNED", "ACTUAL", "DIFFERENCE", "NOTES"],
          [0.0, 0.3, 0.44, 0.58, 0.74], 10, BODY_T, BODY_B - 84)
    field_grid(p, [("Shared fund / purpose", None),
                   ("Target / each contribution", None)],
               2, BODY_B - 74, BODY_B)


def pg_notes(p, plan, dotted):
    head(p, "Notes")
    if dotted:
        y = BODY_T
        while y <= BODY_B:
            x = M_L
            while x <= M_R:
                p.page.draw_circle((x, y), 0.7, color=None, fill=NAVY,
                                   fill_opacity=RULE_OP)
                x += 17
            y += 17
    else:
        n = int((BODY_B - BODY_T) // 26) + 1
        rules(p, M_L, M_R, BODY_T, n, (BODY_B - BODY_T) / (n - 1))


def pg_closing(p, plan):
    head(p, "Keep Choosing Each Other",
         "The value is in the practice, not in filling every page.")
    cx = (M_L + M_R) / 2
    p.text(cx, 258, "Two Souls. One Bond.", name="pf", size=28, color=NAVY,
           align="c")
    p.line(cx - 62, 280, cx + 62, 280, color=GOLD, width=1.2, opacity=0.9)
    field(p, M_L + 110, M_R - 110, 320, 340,
          "What we want to carry forward", min_lines=3)
    buttons(p, [("RETURN TO HOME", plan.home)], BODY_B - 22)


# --------------------------------------------------------------------- plan
class Plan:
    """Sayfa sirasi, index'ler ve sekme hedefleri."""

    def __init__(self, pair_label="ARIES & LEO", cover_title="Aries & Leo"):
        self.pair_label = pair_label
        self.cover_title = cover_title
        self.pages = []

        def add(kind, tab, **kw):
            self.pages.append(dict(kind=kind, tab=tab, **kw))
            return len(self.pages) - 1

        self.cover = add("cover", None)
        self.begin = add("begin", "Home")
        self.howto = add("howto", "Home")
        self.home = add("home", "Home")
        self.story = add("story", "Home")
        self.who = add("who", "Home")
        self.dates = add("dates", "Home")

        self.plan_div = add("divider", "Plan")
        self.year = add("year", "Plan")
        self.weeks_idx = add("weeks_index", "Plan")
        self.month_plan, self.month_int = [], []
        for m in range(12):
            self.month_plan.append(add("month_plan", "Plan", month=m))
            self.month_int.append(add("month_int", "Plan", month=m))
        self.week = [add("week", "Plan", week=w) for w in range(52)]

        self.connect_div = add("divider", "Connect")
        self.date_ideas = add("date_ideas", "Connect")
        self.date_matrix = add("date_matrix", "Connect")
        self.date_plan = add("date_plan", "Connect")
        add("date_plan", "Connect")
        self.bucket = add("bucket", "Connect")
        add("bucket", "Connect")
        self.decide = add("decide", "Connect")
        self.seen = add("seen", "Connect")
        self.disagree = add("disagree", "Connect")
        self.invitations = add("invitations", "Connect")
        self.rituals = add("rituals", "Connect")
        self.loved = add("loved", "Connect")
        self.deck = add("deck", "Connect")

        self.reflect_div = add("divider", "Reflect")
        self.checkin = add("checkin", "Reflect")
        add("checkin", "Reflect")
        self.compass = add("compass", "Reflect")
        self.repair = add("repair", "Reflect")
        self.new_moon = add("moon", "Reflect", title="New Moon Intention")
        self.full_moon = add("moon", "Reflect", title="Full Moon Reflection")
        self.venus = add("moon", "Reflect", title="Venus Notes")
        self.mars = add("moon", "Reflect", title="Mars Notes")

        self.remember_div = add("divider", "Remember")
        self.memory = add("memory", "Remember")
        add("memory", "Remember")
        self.travel = add("travel", "Remember")
        self.celebration = add("celebration", "Remember")
        self.movies = add("movies", "Remember")

        self.grow_div = add("divider", "Grow")
        self.goals = add("goals", "Grow")
        self.money = add("money", "Grow")
        add("money", "Grow")
        self.notes_lined = add("notes", "Grow", dotted=False)
        for _ in range(2):
            add("notes", "Grow", dotted=False)
        self.notes_dotted = add("notes", "Grow", dotted=True)
        for _ in range(2):
            add("notes", "Grow", dotted=True)

        self.closing = add("closing", "Home")

        # hafta <-> ay eslemesi
        self.month_weeks, w = [], 0
        for n in WEEKS_PER_MONTH:
            self.month_weeks.append(list(range(w, w + n)))
            w += n
        self.week_month = {wk: m for m, wks in enumerate(self.month_weeks)
                           for wk in wks}

        self.tab_target = {"Home": self.home, "Plan": self.plan_div,
                           "Connect": self.connect_div,
                           "Reflect": self.reflect_div,
                           "Remember": self.remember_div, "Grow": self.grow_div}

        # bolum ayirici icerikleri (etiketler = sayfa basliklari birebir)
        self.divider = {
            self.plan_div: {"title": "Plan",
                            "sub": "Give your connection a place in the calendar.",
                            "items": [("Year at a Glance", self.year),
                                      ("Your 52 Weeks", self.weeks_idx),
                                      ("Month 01 Plan", self.month_plan[0])]},
            self.connect_div: {"title": "Connect",
                               "sub": "Turn attention into warmth.",
                               "items": [("Date Night Ideas", self.date_ideas),
                                         ("Date Night Matrix", self.date_matrix),
                                         ("Date Night Plan", self.date_plan),
                                         ("Our Bucket List", self.bucket),
                                         ("How We Decide Together", self.decide),
                                         ("What Makes Us Feel Seen", self.seen),
                                         ("When We Disagree", self.disagree),
                                         ("Small Invitations", self.invitations),
                                         ("Connection Rituals", self.rituals),
                                         ("How We Feel Loved", self.loved),
                                         ("Conversation Deck", self.deck)]},
            self.reflect_div: {"title": "Reflect",
                               "sub": "Notice. Name. Choose again.",
                               "items": [("Monthly Check-in", self.checkin),
                                         ("Connection Compass", self.compass),
                                         ("Repair and Reconnect", self.repair),
                                         ("New Moon Intention", self.new_moon),
                                         ("Full Moon Reflection", self.full_moon),
                                         ("Venus Notes", self.venus),
                                         ("Mars Notes", self.mars)]},
            self.remember_div: {"title": "Remember",
                                "sub": "Keep the feeling, not just the date.",
                                "items": [("Memory Capsule", self.memory),
                                          ("Travel Wish List", self.travel),
                                          ("Celebration Notes", self.celebration),
                                          ("Movies and Books", self.movies)]},
            self.grow_div: {"title": "Grow",
                            "sub": "Make room for who you are becoming.",
                            "items": [("Shared Goals", self.goals),
                                      ("Shared Money", self.money),
                                      ("Notes", self.notes_lined)]},
        }

        # spesifikasyondaki 1-tabanli sayfa numaralari
        expect = {self.begin: 2, self.howto: 3, self.home: 4, self.story: 5,
                  self.who: 6, self.dates: 7, self.plan_div: 8, self.year: 9,
                  self.weeks_idx: 10, self.month_plan[0]: 11,
                  self.month_int[11]: 34, self.week[0]: 35, self.week[51]: 86,
                  self.connect_div: 87, self.date_ideas: 88,
                  self.deck: 100, self.reflect_div: 101, self.checkin: 102,
                  self.compass: 104, self.repair: 105, self.mars: 109,
                  self.remember_div: 110, self.memory: 111, self.movies: 115,
                  self.grow_div: 116, self.goals: 117, self.money: 118,
                  self.notes_lined: 120, self.notes_dotted: 123,
                  self.closing: 126}
        for idx, want in expect.items():
            if idx + 1 != want:
                raise AssertionError(f"sayfa sirasi: {idx + 1} != beklenen {want}")
        if len(self.pages) != 126:
            raise AssertionError(f"sayfa sayisi {len(self.pages)}, 126 bekleniyor")

    def __len__(self):
        return len(self.pages)


SIMPLE = {"begin": pg_begin, "howto": pg_howto, "home": pg_home,
          "story": pg_story, "who": pg_who, "dates": pg_dates,
          "year": pg_year, "weeks_index": pg_weeks_index,
          "date_ideas": pg_date_ideas, "date_matrix": pg_date_matrix,
          "date_plan": pg_date_plan, "bucket": pg_bucket, "decide": pg_decide,
          "seen": pg_seen, "disagree": pg_disagree,
          "invitations": pg_invitations, "rituals": pg_rituals,
          "loved": pg_loved, "deck": pg_deck, "checkin": pg_checkin,
          "compass": pg_compass, "repair": pg_repair, "memory": pg_memory,
          "travel": pg_travel, "celebration": pg_celebration,
          "movies": pg_movies, "goals": pg_goals, "money": pg_money,
          "closing": pg_closing}


# ------------------------------------------------------------------ uretim
def render_symbol_rasters(symbol_png: Path, tmp: Path, cover_w_pt, icon_w_pt):
    im = Image.open(symbol_png).convert("RGBA")
    ar = im.height / im.width
    out = {}
    for name, w_pt, ppi in (("cover", cover_w_pt, 150), ("icon", icon_w_pt, 100)):
        px = max(1, int(round(w_pt / 72.0 * ppi)))
        r = im.resize((px, max(1, int(round(px * ar)))), Image.LANCZOS)
        path = tmp / f"sym_{name}.png"
        r.save(path, "PNG", optimize=True)
        out[name] = {"path": str(path), "size_pt": (w_pt, w_pt * ar), "px": r.size}
    return out


def build_pdf(plan, fonts, rasters, week_start, out_pdf: Path):
    days = DAYS_MON if week_start == "MON" else DAYS_SUN
    doc = fitz.open()
    for _ in plan.pages:
        doc.new_page(width=PAGE_W, height=PAGE_H)

    icon_state = {"size_pt": rasters["icon"]["size_pt"]}
    all_strings = []

    for i, spec in enumerate(plan.pages):
        p = Painter(doc[i], fonts)
        kind = spec["kind"]

        if kind == "cover":
            pg_cover(p, plan, rasters["cover"]["path"],
                     rasters["cover"]["size_pt"], week_start)
            p.flush()
            all_strings.append(p.strings)
            continue

        p.rect(0, 0, PAGE_W, PAGE_H, color=None, fill=CREAM, width=0)
        if kind == "divider":
            pg_divider(p, plan, plan.divider[i])
        elif kind == "month_plan":
            pg_month_plan(p, plan, spec["month"], days)
        elif kind == "month_int":
            pg_month_int(p, plan, spec["month"])
        elif kind == "week":
            pg_week(p, plan, spec["week"], days)
        elif kind == "moon":
            pg_moon(p, plan, spec["title"])
        elif kind == "notes":
            pg_notes(p, plan, spec["dotted"])
        elif kind in SIMPLE:
            SIMPLE[kind](p, plan)
        else:
            raise RuntimeError(f"bilinmeyen sayfa tipi: {kind}")

        draw_chrome(p, plan, spec, i, rasters["icon"]["path"], icon_state)
        p.flush()
        all_strings.append(p.strings)

    doc.subset_fonts()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_pdf, garbage=4, deflate=True, clean=True)
    doc.close()
    return all_strings


# --------------------------------------------------------------- dogrulama
BANNED_CHARS = {"em dash": "—", "en dash": "–",
                "bosluklu tire": " - "}
BANNED_WORDS = ["colour", "favourite", "fire"]
SIGN_WORDS = ["aries", "leo"]


def verify(plan, pdf: Path, all_strings):
    doc = fitz.open(pdf)
    n = doc.page_count
    res = {"pages": n, "bytes": pdf.stat().st_size,
           "mb": round(pdf.stat().st_size / 1024 / 1024, 2)}
    fails = []

    if n != 126:
        fails.append(f"sayfa sayisi {n}")

    # linkler
    total = broken = 0
    min_links = 999
    for pno in range(n):
        links = doc[pno].get_links()
        total += len(links)
        for lk in links:
            tgt = lk.get("page", -1)
            if lk["kind"] != fitz.LINK_GOTO or not (0 <= tgt < n):
                broken += 1
        if pno != plan.cover:
            min_links = min(min_links, len(links))
    res.update(links_total=total, links_broken=broken,
               min_links_per_page=min_links)
    if broken:
        fails.append(f"{broken} kirik link")
    if min_links < len(TABS) + 1:
        fails.append(f"bir sayfada {min_links} link (sekme+ikon = "
                     f"{len(TABS) + 1} olmali)")
    if len(doc[plan.cover].get_links()) != 1:
        fails.append("kapakta tam 1 link olmali")
    for div in plan.divider:
        if len(doc[div].get_links()) < len(TABS) + 1:
            fails.append(f"ayirici s.{div + 1} seritsiz")

    # gomulu font
    not_embedded = set()
    for pno in range(n):
        for f in doc[pno].get_fonts(full=True):
            if f[1] == "n/a":
                not_embedded.add(f[3])
    res["fonts_not_embedded"] = sorted(not_embedded)
    res["fonts"] = sorted({f[3] for pno in range(n)
                           for f in doc[pno].get_fonts(full=True)})
    if not_embedded:
        fails.append(f"gomulu olmayan font: {sorted(not_embedded)}")

    # tipografi ve burca ozel sozcukler
    header = f"ASTROLOVE  /  {plan.pair_label}"
    typo = []
    for pno, strings in enumerate(all_strings):
        body = " ".join(s for s, chrome in strings
                        if not chrome and s != header)
        low = body.lower()
        for name, ch in BANNED_CHARS.items():
            if ch in body:
                typo.append(f"s.{pno + 1}: {name}")
        # kelime siniri sart: "anniversaries" icinde "aries" gecer.
        for w in BANNED_WORDS:
            if re.search(rf"\b{w}\b", low):
                typo.append(f"s.{pno + 1}: '{w}'")
        if pno not in (plan.cover, plan.begin):
            for w in SIGN_WORDS:
                if re.search(rf"\b{w}\b", low):
                    typo.append(f"s.{pno + 1}: burc adi '{w}'")
    res["typography_issues"] = typo
    if typo:
        fails.append(f"tipografi: {typo[:6]}")

    doc.close()
    res["qc"] = "PASS" if not fails else "FAIL: " + "; ".join(fails)
    return res, fails


PREVIEWS = [("01_cover", "cover"), ("02_home", "home"),
            ("03_month", "month_plan"), ("04_week", "week"),
            ("05_datenight_matrix", "date_matrix"), ("06_compass", "compass"),
            ("07_notes", "notes"), ("08_closing", "closing")]


def render_previews(plan, pdf: Path, out_dir: Path):
    doc = fitz.open(pdf)
    mat = fitz.Matrix(2732.0 / PAGE_W, 2732.0 / PAGE_W)
    first = {}
    for i, spec in enumerate(plan.pages):
        first.setdefault(spec["kind"], i)
    made = []
    for name, kind in PREVIEWS:
        pix = doc[first[kind]].get_pixmap(matrix=mat, alpha=False)
        pix.save(out_dir / f"{name}.png")
        made.append({"file": f"{name}.png", "page": first[kind] + 1,
                     "px": [pix.width, pix.height]})
    doc.close()
    return made


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster")
    ap.add_argument("--symbol")
    ap.add_argument("--out", required=True)
    ap.add_argument("--symbol-only", action="store_true")
    ap.add_argument("--pair", default="ARIES_LEO_MB")
    ap.add_argument("--pair-label", default="ARIES & LEO")
    ap.add_argument("--cover-title", default="Aries & Leo")
    ap.add_argument("--cover-frac", type=float, default=0.12)
    ap.add_argument("--max-mb", type=float, default=8.0)
    ap.add_argument("--font-cache", default="")
    ap.add_argument("--rclone-symbols", default="")
    ap.add_argument("--rclone-sample", default="")
    a = ap.parse_args()

    if not a.poster and not a.symbol:
        ap.error("--poster veya --symbol gerekli")

    out = Path(a.out)
    sym_dir, smp_dir, tmp = out / "SYMBOLS", out / "SAMPLE", out / "_tmp"
    for d in (sym_dir, smp_dir, tmp):
        d.mkdir(parents=True, exist_ok=True)
    report = {}

    if a.poster:
        sym_png = sym_dir / f"{a.pair}.png"
        prev = sym_dir / f"_preview_{a.pair.rsplit('_', 1)[0]}.png"
        info = extract_symbol(Path(a.poster), sym_png, prev)
        info["problems"] = check_symbol(info)
        report["symbol"] = info
        print(f"[symbol] poster {info['poster_px']} -> bbox {info['bbox']} "
              f"= {info['symbol_px']} px, alan %{info['component_area_frac']*100:.2f}")
        if info["problems"]:
            print("[symbol] DUR: " + "; ".join(info["problems"]), file=sys.stderr)
            (smp_dir / "build_report.json").write_text(json.dumps(report, indent=2))
            return 2
    else:
        sym_png = Path(a.symbol)
        report["symbol"] = {"supplied": str(sym_png)}

    if a.symbol_only:
        print(json.dumps(report, indent=2))
        return 0

    ff = fetch_fonts(Path(a.font_cache) if a.font_cache else out / "_fonts")
    fonts = {("mont", False): fitz.Font(fontfile=str(ff[("Montserrat", "400")])),
             ("mont", True): fitz.Font(fontfile=str(ff[("Montserrat", "600")])),
             ("pf", False): fitz.Font(fontfile=str(ff[("Playfair Display", "400")])),
             ("pf", True): fitz.Font(fontfile=str(ff[("Playfair Display", "700")]))}
    rasters = render_symbol_rasters(sym_png, tmp, PAGE_W * a.cover_frac, ICON_PT)
    report["rasters"] = {k: {"px": v["px"], "pt": [round(x, 2) for x in v["size_pt"]]}
                         for k, v in rasters.items()}

    plan = Plan(a.pair_label, a.cover_title)
    outs, fails = {}, []
    for ws in ("MON", "SUN"):
        pdf = smp_dir / f"ASTROLOVE_PLANNER_{a.pair}_{ws}_SAMPLE.pdf"
        strings = build_pdf(plan, fonts, rasters, ws, pdf)
        res, f = verify(plan, pdf, strings)
        if res["mb"] > a.max_mb:
            f.append(f"{res['mb']} MB > {a.max_mb} MB")
            res["qc"] = "FAIL: " + f[-1]
        outs[ws] = res
        fails += [f"{ws}: {x}" for x in f]
        print(f"[pdf] {pdf.name}: {res['pages']} sayfa, {res['mb']} MB, "
              f"{res['links_total']} link, kirik {res['links_broken']}, "
              f"sayfa basina en az {res['min_links_per_page']} link, "
              f"gomusuz font {len(res['fonts_not_embedded'])}, "
              f"tipografi {len(res['typography_issues'])}")
    report["pdf"] = outs
    report["qc"] = "PASS" if not fails else "FAIL: " + "; ".join(fails)

    report["previews"] = render_previews(
        plan, smp_dir / f"ASTROLOVE_PLANNER_{a.pair}_MON_SAMPLE.pdf", smp_dir)
    (smp_dir / "build_report.json").write_text(json.dumps(report, indent=2))
    print(f"[qc] {report['qc']}")

    if a.rclone_symbols:
        rclone("copy", str(sym_dir), a.rclone_symbols, "-q")
    if a.rclone_sample:
        rclone("copy", str(smp_dir), a.rclone_sample, "-q")

    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
