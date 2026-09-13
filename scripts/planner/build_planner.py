#!/usr/bin/env python3
"""
AstroLove Couple Digital Planner - tek dosya uretici (Mo, 13 Eyl 2026).

Ne yapar
  1. Poster'dan altin birlesik sembolu kirpar (RGBA seffaf PNG) veya hazir
     sembol PNG'sini kullanir. Sembol YENIDEN CIZILMEZ: RGB posterden birebir
     alinir, yalniz alfa maskesi uretilir. Aynalama/deformasyon yok.
  2. 1024 x 768 pt (4:3 yatay) planner PDF'ini kurar. Govde tamamen vektor;
     tek raster oge sembol (kapak 150 ppi, sekme ikonu 100 ppi).
  3. Iki surum yazar: hafta Pazartesi baslangicli (MON) ve Pazar (SUN).
  4. Tum ic linkleri (kind=LINK_GOTO) sayar ve hedeflerini dogrular.
  5. PNG onizlemeleri 2732x2048 (gercek 4:3 oran) uretir.

Bagimlilik: pymupdf (fitz), pillow, numpy, scipy. Baska PDF kutuphanesi YOK.

Kullanim
  # sembolu posterden cikar + planner kur
  build_planner.py --poster ARIES_LEO.jpg --out OUT
  # sembol hazirsa
  build_planner.py --symbol ARIES_LEO_MB.png --out OUT
  # yalniz sembol kirpma (dogrulama turu)
  build_planner.py --poster ARIES_LEO.jpg --out OUT --symbol-only

Cikti (--out altinda)
  SYMBOLS/ARIES_LEO_MB.png, SYMBOLS/_preview_ARIES_LEO.png
  SAMPLE/ASTROLOVE_PLANNER_ARIES_LEO_MB_MON_SAMPLE.pdf
  SAMPLE/ASTROLOVE_PLANNER_ARIES_LEO_MB_SUN_SAMPLE.pdf
  SAMPLE/01_cover.png .. 06_notes.png
  SAMPLE/build_report.json
"""
import argparse
import json
import math
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

RULE_OP = 0.25          # cizgi/grid opakligi (navy uzerinden)
FOOT_OP = 0.40
FOOTER = "The Shape of Your Connection. (c) 2026 AstroLove"

TAB_W = 74.0            # sag dikey sekme seridi genisligi
ICON_H = 66.0           # serit basindaki sembol ikonu blogu
M_L = 56.0              # sol kenar
M_T = 52.0              # ust kenar
M_R = PAGE_W - TAB_W - 34.0     # 916.0 -> govde sag siniri
BODY_T = 132.0          # baslik altindan sonra govde basi
BODY_B = 706.0          # govde alt siniri (altbilgi ustu)
FOOT_Y = PAGE_H - 22.0

TABS = ["Home", "Story", "Year", "Months", "Weeks", "Dates",
        "Goals", "Budget", "Memories", "Us", "Notes"]

# 12 aya 52 hafta: 3-6-9-12. aylar 5 hafta, digerleri 4.
WEEKS_PER_MONTH = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
DAYS_MON = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
        out[key] = dst
    return out


# ------------------------------------------------------------ sembol kirpma
def extract_symbol(poster: Path, out_png: Path, preview_png: Path, pad=0.06):
    """
    Lacivert zeminli posterden ortadaki altin birlesik sembolu kirpar.

    Yontem: altin tonu maskele (kirmizi>yesil>mavi ve zeminden belirgin parlak)
    -> en buyuk baglantili bolgeyi al (halka + fusion tek parcadir; baslik,
    isim satiri ve tagline ayri ve daha kucuk parcalardir) -> bbox + %6 pay ->
    alfa = altinlik rampasi, RGB posterden BIREBIR. Yeniden cizim yok.
    """
    im = Image.open(poster).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]

    # Altin (#C9A227) lacivert (#1A1A2E) zeminde: r>g>b, r-b genis, r yeterince parlak.
    warm = (r - b).astype(np.float32)
    gold = (r > g) & (g > b) & (warm >= 40) & (r >= 80)
    if gold.sum() < 500:
        raise RuntimeError(f"altin maske bos ({int(gold.sum())} px) - poster beklenen "
                           f"lacivert/altin edisyon degil: {poster}")

    # Yildiz/toz temizligi: 1 px'lik tekil noktalari ele, sonra parcala.
    clean = ndimage.binary_opening(gold, structure=np.ones((3, 3), bool))
    if clean.sum() < 500:
        clean = gold
    # Halka ile fusion arasinda kucuk boslik olabilir: hafif kapama ile birlestir.
    k = max(3, int(round(min(a.shape[:2]) * 0.004)) | 1)
    joined = ndimage.binary_closing(clean, structure=np.ones((k, k), bool))

    lab, n = ndimage.label(joined)
    if n == 0:
        raise RuntimeError("baglantili altin bolge yok")
    sizes = ndimage.sum(joined, lab, range(1, n + 1))
    big = int(np.argmax(sizes)) + 1
    comp = lab == big

    ys, xs = np.where(comp)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = comp.shape
    py = int(round((y1 - y0 + 1) * pad))
    px = int(round((x1 - x0 + 1) * pad))
    y0, y1 = max(0, y0 - py), min(H - 1, y1 + py)
    x0, x1 = max(0, x0 - px), min(W - 1, x1 + px)

    sub = a[y0:y1 + 1, x0:x1 + 1]
    subm = comp[y0:y1 + 1, x0:x1 + 1]

    # Alfa: zemin (lacivert) ile altin arasinda yumusak rampa; maske disi 0.
    lum = sub.mean(axis=2).astype(np.float32)
    bg = float(np.percentile(lum[~subm], 60)) if (~subm).any() else 0.0
    fg = float(np.percentile(lum[subm], 85))
    if fg - bg < 8:
        fg = bg + 8.0
    alpha = np.clip((lum - bg) / (fg - bg), 0.0, 1.0)
    grown = ndimage.binary_dilation(subm, structure=np.ones((3, 3), bool), iterations=2)
    alpha = np.where(grown, alpha, 0.0)

    rgba = np.dstack([sub.astype(np.uint8),
                      (alpha * 255).round().astype(np.uint8)])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out_png, "PNG", optimize=True)

    sym = Image.open(out_png)
    pw = 800
    sym.resize((pw, max(1, round(sym.height * pw / sym.width))),
               Image.LANCZOS).save(preview_png, "PNG", optimize=True)

    frac = float(comp.sum()) / (H * W)
    return {"poster": str(poster), "poster_px": [W, H],
            "bbox": [int(x0), int(y0), int(x1), int(y1)],
            "symbol_px": [int(x1 - x0 + 1), int(y1 - y0 + 1)],
            "component_area_frac": round(frac, 5),
            "components": int(n),
            "alpha_mean": round(float(alpha.mean()), 4)}


def check_symbol(info):
    """Kirpma makul mu? Sembol posterin ortasinda, tuvalin %1-%60'i olmali."""
    W, H = info["poster_px"]
    x0, y0, x1, y1 = info["bbox"]
    w, h = x1 - x0 + 1, y1 - y0 + 1
    problems = []
    if not (0.01 <= info["component_area_frac"] <= 0.60):
        problems.append(f"bolge alani tuvalin %{info['component_area_frac']*100:.1f}'i")
    if w / W > 0.95 or h / H > 0.95:
        problems.append("bbox neredeyse tum poster (maske zemini de yakalamis)")
    if not (0.15 < ((x0 + x1) / 2) / W < 0.85):
        problems.append("bbox yatayda ortali degil")
    if info["alpha_mean"] < 0.01:
        problems.append("alfa bos")
    return problems


# ------------------------------------------------------------- sayfa duzeni
class Plan:
    """Sayfa sirasi ve index'ler. Once kurulur, sonra cizilir."""

    def __init__(self):
        self.pages = []
        def add(kind, tab, **kw):
            self.pages.append(dict(kind=kind, tab=tab, **kw))
            return len(self.pages) - 1

        self.cover = add("cover", None)
        self.home = add("home", "Home")
        self.story = add("story", "Story")
        self.important = add("important", "Story")
        self.year = add("year", "Year")
        self.monthly = [add("monthly", "Months", month=m) for m in range(12)]
        self.weekly = [add("weekly", "Weeks", week=w) for w in range(52)]
        self.dn_ideas = add("dn_ideas", "Dates")
        self.dn_plan = add("dn_plan", "Dates")
        self.dn_bucket = add("dn_bucket", "Dates")
        self.bucket = add("bucket", "Goals")
        self.goals = add("goals", "Goals")
        self.budget = [add("budget", "Budget", part=i) for i in range(2)]
        self.memories = [add("memories", "Memories", part=i) for i in range(2)]
        self.love = add("love", "Us")
        self.checkin = add("checkin", "Us")
        self.starters = add("starters", "Us")
        self.movies = [add("movies", "Us", part=i) for i in range(2)]
        self.travel = [add("travel", "Goals", part=i) for i in range(2)]
        self.lined = [add("lined", "Notes", part=i) for i in range(3)]
        self.dotted = [add("dotted", "Notes", part=i) for i in range(3)]

        # hafta <-> ay eslemesi
        self.month_weeks = []
        w = 0
        for n in WEEKS_PER_MONTH:
            self.month_weeks.append(list(range(w, w + n)))
            w += n
        assert w == 52, w
        self.week_month = {wk: m for m, wks in enumerate(self.month_weeks) for wk in wks}

        self.tab_target = {
            "Home": self.home, "Story": self.story, "Year": self.year,
            "Months": self.monthly[0], "Weeks": self.weekly[0],
            "Dates": self.dn_ideas, "Goals": self.bucket,
            "Budget": self.budget[0], "Memories": self.memories[0],
            "Us": self.love, "Notes": self.lined[0],
        }

    def __len__(self):
        return len(self.pages)


class Painter:
    """Tek sayfa icin metin/vektor yardimcilari. Metinler renge gore gruplanir."""

    def __init__(self, page, fonts):
        self.page = page
        self.fonts = fonts
        self._tw = {}
        self.links = []

    def _font(self, name, bold):
        return self.fonts[(name, bold)]

    def width(self, s, name="mont", size=9, bold=False):
        return self._font(name, bold).text_length(s, size)

    def text(self, x, y, s, name="mont", size=9, color=NAVY, bold=False,
             align="l", opacity=1.0):
        f = self._font(name, bold)
        w = f.text_length(s, size)
        if align == "c":
            x -= w / 2
        elif align == "r":
            x -= w
        key = (color, round(opacity, 3))
        tw = self._tw.get(key)
        if tw is None:
            tw = fitz.TextWriter(self.page.rect)
            self._tw[key] = tw
        tw.append((x, y), s, font=f, fontsize=size)
        return w

    def line(self, x0, y0, x1, y1, color=NAVY, width=0.6, opacity=RULE_OP):
        self.page.draw_line((x0, y0), (x1, y1), color=color, width=width,
                            stroke_opacity=opacity)

    def rect(self, x0, y0, x1, y1, color=NAVY, fill=None, width=0.6,
             opacity=RULE_OP, fill_opacity=1.0, radius=None):
        self.page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=color, fill=fill,
                            width=width, stroke_opacity=opacity,
                            fill_opacity=fill_opacity, radius=radius)

    def rows(self, x0, x1, y0, n, gap=None, color=NAVY, opacity=RULE_OP, end=None):
        if gap is None:
            gap = (end - y0) / max(1, n - 1)
        for i in range(n):
            y = y0 + i * gap
            self.line(x0, y, x1, y, color=color, opacity=opacity)
        return y0 + (n - 1) * gap

    def dots(self, x0, y0, x1, y1, step=16.0):
        y = y0
        while y <= y1:
            x = x0
            while x <= x1:
                self.page.draw_circle((x, y), 0.7, color=None, fill=NAVY,
                                      fill_opacity=RULE_OP)
                x += step
            y += step

    def checkboxes(self, x0, y0, n, gap, size=9.0, x1=None, label_gap=8.0,
                   labels=None):
        for i in range(n):
            y = y0 + i * gap
            self.rect(x0, y - size, x0 + size, y)
            if x1:
                self.line(x0 + size + label_gap, y, x1, y)
            if labels and i < len(labels):
                self.text(x0 + size + label_gap, y - 3, labels[i], size=8.5)
        return y0 + (n - 1) * gap

    def goto(self, x0, y0, x1, y1, target):
        self.links.append({"kind": fitz.LINK_GOTO, "page": target,
                           "from": fitz.Rect(x0, y0, x1, y1),
                           "to": fitz.Point(0, 0)})

    def flush(self):
        for (color, op), tw in self._tw.items():
            tw.write_text(self.page, color=color, opacity=op)
        for lk in self.links:
            self.page.insert_link(lk)


# ---------------------------------------------------------------- cerceveler
def draw_footer(p, on_navy=False):
    p.text(M_L, FOOT_Y, FOOTER, size=8,
           color=GOLD if on_navy else NAVY, opacity=FOOT_OP)


def draw_tabs(p, plan, active, icon_png, icon_rect_xref):
    x0 = PAGE_W - TAB_W
    p.rect(x0, 0, PAGE_W, PAGE_H, color=None, fill=NAVY, width=0)

    # ust: sembol ikonu -> Home
    iw, ih = icon_rect_xref["size_pt"]
    ix = x0 + (TAB_W - iw) / 2
    iy = (ICON_H - ih) / 2
    xref = p.page.insert_image(fitz.Rect(ix, iy, ix + iw, iy + ih),
                               filename=icon_png,
                               xref=icon_rect_xref.get("xref", 0))
    icon_rect_xref["xref"] = xref
    p.goto(x0, 0, PAGE_W, ICON_H, plan.home)
    p.line(x0 + 14, ICON_H, PAGE_W - 14, ICON_H, color=GOLD, opacity=0.35)

    h = (PAGE_H - ICON_H) / len(TABS)
    for i, name in enumerate(TABS):
        ty = ICON_H + i * h
        on = (name == active)
        if on:
            p.rect(x0 + 4, ty + 3, PAGE_W - 4, ty + h - 3, color=None,
                   fill=GOLD, width=0)
        p.text(x0 + TAB_W / 2, ty + h / 2 + 3, name, size=8.2, bold=True,
               color=NAVY if on else GOLD, align="c")
        p.goto(x0, ty, PAGE_W, ty + h, plan.tab_target[name])


def page_title(p, title, sub=None):
    p.text(M_L, M_T + 26, title, name="pf", size=27, bold=True, color=NAVY)
    p.line(M_L, M_T + 42, M_L + 92, M_T + 42, color=GOLD, width=1.6, opacity=1.0)
    if sub:
        p.text(M_L, M_T + 62, sub, size=8.6, color=NAVY, opacity=0.62)


# -------------------------------------------------------------- sayfa cizimi
def draw_cover(p, plan, cover_png, cover_size_pt):
    p.rect(0, 0, PAGE_W, PAGE_H, color=None, fill=NAVY, width=0)
    p.rect(30, 30, PAGE_W - 30, PAGE_H - 30, color=GOLD, width=0.8, opacity=0.45)

    sw, sh = cover_size_pt
    sx = (PAGE_W - sw) / 2
    sy = 148.0
    p.page.insert_image(fitz.Rect(sx, sy, sx + sw, sy + sh), filename=cover_png)

    p.text(PAGE_W / 2, sy + sh + 92, "Aries and Leo", name="pf", size=44,
           bold=True, color=GOLD, align="c")
    p.text(PAGE_W / 2, sy + sh + 124, "C O U P L E   D I G I T A L   P L A N N E R",
           size=9.4, bold=True, color=GOLD, align="c", opacity=0.75)

    # ince infinity: Bernoulli lemniskati (vektor polyline, tek surekli egri)
    cx, cy, aa = PAGE_W / 2, 600.0, 27.0
    pts = []
    for i in range(121):
        t = 2 * math.pi * i / 120
        den = 1.0 + math.sin(t) ** 2
        pts.append((cx + aa * math.cos(t) / den,
                    cy + aa * math.sin(t) * math.cos(t) / den))
    sh_ = p.page.new_shape()
    sh_.draw_polyline(pts)
    sh_.finish(color=GOLD, width=0.9, closePath=True, stroke_opacity=0.9)
    sh_.commit()

    p.text(PAGE_W / 2, 654, "Two Souls. One Bond.", name="pf", size=15,
           color=GOLD, align="c")
    draw_footer(p, on_navy=True)


def draw_home(p, plan):
    page_title(p, "Home", "Every section of your planner. Tap any line to jump.")
    entries = [
        ("Our Story", plan.story), ("Important Dates", plan.important),
        ("Year at a Glance", plan.year), ("Weeks 1 to 52", plan.weekly[0]),
        ("Date Night Ideas", plan.dn_ideas), ("Date Night Planner", plan.dn_plan),
        ("Date Night Bucket", plan.dn_bucket), ("Bucket List", plan.bucket),
        ("Shared Goals", plan.goals), ("Budget", plan.budget[0]),
        ("Memories", plan.memories[0]), ("Love Languages", plan.love),
        ("Monthly Check-in", plan.checkin), ("Conversation Starters", plan.starters),
        ("Movies and Books", plan.movies[0]), ("Travel", plan.travel[0]),
        ("Lined Notes", plan.lined[0]), ("Dotted Notes", plan.dotted[0]),
    ]
    colw = (M_R - M_L) / 3
    y0 = BODY_T + 22
    p.text(M_L, y0 - 14, "S E C T I O N S", size=8, bold=True, color=GOLD)
    for i, (label, target) in enumerate(entries):
        col, row = divmod(i, 6)
        x = M_L + col * colw
        y = y0 + 18 + row * 27
        p.text(x, y, label, size=10.5)
        p.line(x, y + 5, x + colw - 26, y + 5)
        p.goto(x - 4, y - 12, x + colw - 26, y + 8, target)

    y1 = y0 + 18 + 6 * 27 + 40
    p.text(M_L, y1, "M O N T H S", size=8, bold=True, color=GOLD)
    bw = (M_R - M_L) / 6
    for m in range(12):
        row, col = divmod(m, 6)
        x = M_L + col * bw
        y = y1 + 20 + row * 40
        p.rect(x, y, x + bw - 12, y + 26)
        p.text(x + (bw - 12) / 2, y + 17, f"{m + 1:02d}", size=9,
               bold=True, align="c")
        p.goto(x, y, x + bw - 12, y + 26, plan.monthly[m])


def draw_story(p, plan):
    page_title(p, "Our Story")
    prompts = ["How we met", "Our first date", "The moment I knew",
               "What I love about you", "Our song, our place, our thing"]
    y = BODY_T
    for i, q in enumerate(prompts):
        p.text(M_L, y, q, size=9.5, bold=True, color=GOLD)
        rows = 3 if i < 4 else 4
        p.rows(M_L, M_R, y + 22, rows, 22)
        y += 22 + rows * 22 + 14


def draw_important(p, plan):
    page_title(p, "Important Dates", "Birthdays, anniversaries and the days that matter.")
    colw = (M_R - M_L) / 2 - 16
    for col in range(2):
        x = M_L + col * (colw + 32)
        p.text(x, BODY_T, "DATE", size=8, bold=True, color=GOLD)
        p.text(x + 86, BODY_T, "OCCASION", size=8, bold=True, color=GOLD)
        p.line(x, BODY_T + 6, x + colw, BODY_T + 6, opacity=0.45)
        for i in range(15):
            y = BODY_T + 32 + i * 30
            p.line(x, y, x + colw, y)
            p.line(x + 78, y - 18, x + 78, y, opacity=0.18)


def draw_year(p, plan):
    page_title(p, "Year at a Glance", "Tap a month to open its spread.")
    cols, rows = 4, 3
    gx, gy = 18.0, 16.0
    bw = (M_R - M_L - gx * (cols - 1)) / cols
    bh = (BODY_B - BODY_T - gy * (rows - 1)) / rows
    for m in range(12):
        c, r = m % cols, m // cols
        x = M_L + c * (bw + gx)
        y = BODY_T + r * (bh + gy)
        p.rect(x, y, x + bw, y + bh)
        p.rect(x, y, x + bw, y + 22, color=None, fill=NAVY, width=0,
               fill_opacity=0.06)
        p.text(x + 10, y + 15, f"MONTH {m + 1:02d}", size=8.6, bold=True, color=GOLD)
        p.rows(x + 10, x + bw - 10, y + 42, 5, 17)
        p.goto(x, y, x + bw, y + bh, plan.monthly[m])


def draw_monthly(p, plan, month, days):
    # Tarihsiz planner: ay ADI basilmaz, sol ustte bos alan birakilir.
    page_title(p, f"Month {month + 1:02d}")
    p.text(M_L + 190, M_T + 26, "M O N T H", size=7.5, bold=True, color=GOLD)
    p.line(M_L + 190, M_T + 30, M_L + 430, M_T + 30, opacity=0.45)
    p.text(M_L + 470, M_T + 26, "Y E A R", size=7.5, bold=True, color=GOLD)
    p.line(M_L + 470, M_T + 30, M_L + 620, M_T + 30, opacity=0.45)

    grid_r = M_L + 620.0
    hy = BODY_T
    cw = (grid_r - M_L) / 7
    for i, d in enumerate(days):
        p.text(M_L + cw * (i + 0.5), hy, d[:3].upper(), size=7.6, bold=True,
               color=GOLD, align="c")
    p.line(M_L, hy + 7, grid_r, hy + 7, opacity=0.45)

    top = hy + 14
    rh = (BODY_B - top) / 6
    wks = plan.month_weeks[month]
    for r in range(6):
        y = top + r * rh
        p.rect(M_L, y, grid_r, y + rh)
        for c in range(1, 7):
            p.line(M_L + c * cw, y, M_L + c * cw, y + rh, opacity=0.18)
        if r < len(wks):
            p.text(M_L + 4, y + 10, f"W{wks[r] + 1}", size=6.4, bold=True,
                   color=GOLD, opacity=0.85)
            p.goto(M_L, y, grid_r, y + rh, plan.weekly[wks[r]])

    lx = grid_r + 24
    p.text(lx, hy, "Our Dates This Month", size=9.6, bold=True, color=NAVY)
    p.line(lx, hy + 7, M_R, hy + 7, color=GOLD, width=1.0, opacity=0.9)
    p.checkboxes(lx, top + 22, 16, 26, x1=M_R)


def draw_weekly(p, plan, week, days):
    month = plan.week_month[week]
    page_title(p, f"Week {week + 1}", f"Month {month + 1:02d}")

    bx0, bx1 = M_L, M_R
    btn_w, btn_h = 96.0, 22.0
    by = M_T + 4
    for i, (label, target) in enumerate([("Back to Month", plan.monthly[month]),
                                         ("Home", plan.home)]):
        x = bx1 - (2 - i) * (btn_w + 10) + 10
        p.rect(x, by, x + btn_w, by + btn_h, color=NAVY, width=0.7, opacity=0.55)
        p.text(x + btn_w / 2, by + 15, label, size=7.8, bold=True, align="c")
        p.goto(x, by, x + btn_w, by + btn_h, target)

    top = BODY_T
    bottom = 566.0
    cw = (bx1 - bx0) / 7
    for i, d in enumerate(days):
        x = bx0 + i * cw
        p.rect(x, top, x + cw, bottom)
        p.rect(x, top, x + cw, top + 20, color=None, fill=NAVY, width=0,
               fill_opacity=0.06)
        p.text(x + cw / 2, top + 14, d[:3].upper(), size=7.6, bold=True,
               color=GOLD, align="c")
        # gun icin tarih alani (tarihsiz: elle yazilir), sonra cizgiler
        p.line(x + cw - 40, top + 36, x + cw - 6, top + 36, opacity=0.30)
        p.rows(x + 6, x + cw - 6, top + 58, 12, end=bottom - 10)

    y = bottom + 22
    lab_r = bx0 + 560.0
    for i, label in enumerate(["Me", "You", "Us"]):
        ly = y + i * 30
        p.text(bx0, ly, label, size=9, bold=True, color=GOLD)
        p.line(bx0 + 34, ly, lab_r, ly)

    p.rect(lab_r + 26, y - 16, bx1, y + 74)
    p.text(lab_r + 36, y, "Date Night", size=9.4, bold=True, color=NAVY)
    p.rows(lab_r + 36, bx1 - 12, y + 24, 3, 22)


def draw_dn_ideas(p, plan):
    page_title(p, "Date Night Ideas", "Fifty starting points. Add your own at the end.")
    ideas = [
        "Cook a recipe neither of you has tried", "Sunrise walk with coffee",
        "Build a playlist of songs from the year you met", "Museum day, one room each picks",
        "Picnic on the living room floor", "Learn a dance from a video",
        "Farmers market, then cook what you find", "Stargazing with a blanket",
        "Write letters to open in one year", "Board game tournament",
        "Try a new coffee shop every week for a month", "Paint the same subject side by side",
        "Long drive with no destination", "Home spa night",
        "Cook a dish from a country you want to visit", "Bookstore date, buy each other a book",
        "Bike ride and ice cream", "Pottery or craft class",
        "Backyard camping", "Karaoke at home",
        "Volunteer together for a morning", "Sunset picnic at a lookout",
        "Photo walk, twenty shots each", "Breakfast for dinner",
        "Plan next year's trip on paper", "Thrift store challenge with a budget",
        "Watch the film that made you cry", "Take a pasta making class",
        "Puzzle night with jazz", "Visit a place from your first date",
        "Write each other a short poem", "Try a new hiking trail",
        "Blind taste test with snacks", "Late night diner run",
        "Plant something and name it", "Reread old messages together",
        "Do a home workout together", "Cook only with what is in the pantry",
        "Visit a rooftop bar", "Make a photo album of the last year",
        "Learn ten words in a new language", "Board a train, get off anywhere",
        "Candlelit dinner, phones in a drawer", "Draw each other in five minutes",
        "Watch a documentary about space", "Bake bread from scratch",
        "Make a vision board for the two of you", "Go to a local show or gig",
        "Swap favorite childhood movies", "Do nothing together, on purpose",
    ]
    colw = (M_R - M_L) / 2 - 14
    for i, idea in enumerate(ideas):
        col, row = divmod(i, 25)
        x = M_L + col * (colw + 28)
        y = BODY_T + 4 + row * 22.4
        p.rect(x, y - 7.5, x + 7.5, y)
        p.text(x + 14, y - 1, f"{i + 1}.", size=7.4, color=GOLD, bold=True)
        p.text(x + 30, y - 1, idea, size=8.2)


def draw_dn_plan(p, plan):
    page_title(p, "Date Night Planner", "One page per plan. Print or duplicate as needed.")
    fields = ["Date", "Time", "Where", "Dress code", "Booking made by",
              "Budget", "Who is planning", "Backup plan"]
    colw = (M_R - M_L) / 2 - 18
    for i, f in enumerate(fields):
        col, row = divmod(i, 4)
        x = M_L + col * (colw + 36)
        y = BODY_T + row * 34
        p.text(x, y, f, size=8.4, bold=True, color=GOLD)
        p.line(x + 96, y, x + colw, y)
    y = BODY_T + 4 * 34 + 16
    for label, rows in [("The plan", 5), ("What we loved", 4), ("Next time", 3)]:
        p.text(M_L, y, label, size=9.4, bold=True, color=NAVY)
        p.rows(M_L, M_R, y + 20, rows, 22)
        y += 20 + rows * 22 + 14


def draw_dn_bucket(p, plan):
    page_title(p, "Date Night Bucket", "The ones you promised each other.")
    colw = (M_R - M_L) / 2 - 16
    for col in range(2):
        x = M_L + col * (colw + 32)
        p.text(x, BODY_T - 14, "IDEA", size=7.6, bold=True, color=GOLD)
        p.text(x + colw - 52, BODY_T - 14, "DONE", size=7.6, bold=True, color=GOLD)
        for i in range(18):
            y = BODY_T + 12 + i * 30
            p.line(x, y, x + colw - 60, y)
            p.rect(x + colw - 44, y - 10, x + colw - 34, y)


def draw_bucket(p, plan):
    page_title(p, "Bucket List", "Big and small. No deadlines.")
    colw = (M_R - M_L) / 2 - 16
    for col in range(2):
        x = M_L + col * (colw + 32)
        for i in range(19):
            y = BODY_T + i * 29
            p.rect(x, y - 9, x + 9, y)
            p.line(x + 18, y, x + colw, y)


def draw_goals(p, plan):
    page_title(p, "Shared Goals", "What we are building together this year.")
    heads = ["GOAL", "WHY IT MATTERS", "BY WHEN", "DONE"]
    xs = [M_L, M_L + 250, M_L + 560, M_R - 46]
    for h, x in zip(heads, xs):
        p.text(x, BODY_T, h, size=7.6, bold=True, color=GOLD)
    p.line(M_L, BODY_T + 7, M_R, BODY_T + 7, color=GOLD, width=1.0, opacity=0.8)
    for i in range(15):
        y = BODY_T + 36 + i * 34
        p.line(M_L, y, M_R, y)
        for x in xs[1:3]:
            p.line(x - 14, y - 24, x - 14, y, opacity=0.16)
        p.line(xs[3] - 14, y - 24, xs[3] - 14, y, opacity=0.16)
        p.rect(xs[3] + 4, y - 20, xs[3] + 14, y - 10)


def draw_budget(p, plan, part):
    if part == 0:
        page_title(p, "Budget", "Monthly plan. Fill the month by hand.")
        heads = ["CATEGORY", "PLANNED", "ACTUAL", "DIFFERENCE"]
        xs = [M_L, M_L + 420, M_L + 570, M_L + 720]
        for h, x in zip(heads, xs):
            p.text(x, BODY_T, h, size=7.6, bold=True, color=GOLD)
        p.line(M_L, BODY_T + 7, M_R, BODY_T + 7, color=GOLD, width=1.0, opacity=0.8)
        for i in range(16):
            y = BODY_T + 34 + i * 32
            p.line(M_L, y, M_R, y)
            for x in xs[1:]:
                p.line(x - 16, y - 22, x - 16, y, opacity=0.16)
        p.text(M_L, BODY_B - 4, "TOTAL", size=8.6, bold=True, color=NAVY)
        p.line(M_L + 60, BODY_B - 2, M_R, BODY_B - 2, color=GOLD, width=1.0,
               opacity=0.8)
    else:
        page_title(p, "Savings and Big Purchases")
        p.text(M_L, BODY_T, "WHAT WE ARE SAVING FOR", size=7.6, bold=True, color=GOLD)
        p.line(M_L, BODY_T + 7, M_L + 460, BODY_T + 7, color=GOLD, width=1.0,
               opacity=0.8)
        for i in range(12):
            y = BODY_T + 34 + i * 38
            p.line(M_L, y, M_L + 300, y)
            for s in range(10):
                p.rect(M_L + 316 + s * 15, y - 11, M_L + 328 + s * 15, y - 1)
        p.text(M_L + 500, BODY_T, "NOTES", size=7.6, bold=True, color=GOLD)
        p.line(M_L + 500, BODY_T + 7, M_R, BODY_T + 7, color=GOLD, width=1.0,
               opacity=0.8)
        p.rows(M_L + 500, M_R, BODY_T + 34, 17, 27)


def draw_memories(p, plan, part):
    if part == 0:
        page_title(p, "Memories", "Paste a photo, write the date, keep the feeling.")
        cols, rows = 3, 2
        gx, gy = 22.0, 22.0
        bw = (M_R - M_L - gx * (cols - 1)) / cols
        bh = (BODY_B - BODY_T - gy * (rows - 1)) / rows
        for i in range(6):
            c, r = i % cols, i // cols
            x = M_L + c * (bw + gx)
            y = BODY_T + r * (bh + gy)
            p.rect(x, y, x + bw, y + bh - 40, opacity=0.35)
            p.text(x + bw / 2, y + (bh - 40) / 2, "photo", size=8, align="c",
                   opacity=0.28)
            p.rows(x, x + bw, y + bh - 24, 2, 18)
    else:
        page_title(p, "Best Moments of the Year")
        colw = (M_R - M_L) / 2 - 18
        for col in range(2):
            x = M_L + col * (colw + 36)
            for i in range(6):
                y = BODY_T + i * 92
                p.text(x, y, f"{col * 6 + i + 1}", size=9, bold=True, color=GOLD)
                p.rows(x + 20, x + colw, y, 4, 20)


def draw_love(p, plan):
    page_title(p, "Love Languages", "Rank yours, then compare.")
    langs = ["Words of affirmation", "Quality time", "Acts of service",
             "Physical touch", "Receiving gifts"]
    for ci, who in enumerate(["ME", "YOU"]):
        x = M_L + ci * ((M_R - M_L) / 2 + 8)
        w = (M_R - M_L) / 2 - 24
        p.text(x, BODY_T, who, size=8.4, bold=True, color=GOLD)
        p.line(x, BODY_T + 7, x + w, BODY_T + 7, color=GOLD, width=1.0, opacity=0.8)
        for i, lg in enumerate(langs):
            y = BODY_T + 38 + i * 36
            p.rect(x, y - 15, x + 22, y + 3)
            p.text(x + 32, y, lg, size=9.4)
            p.line(x + 32, y + 5, x + w, y + 5, opacity=0.18)
    y = BODY_T + 38 + 5 * 36 + 24
    p.text(M_L, y, "What this tells us", size=9.4, bold=True, color=NAVY)
    p.rows(M_L, M_R, y + 22, 7, 24)


def draw_checkin(p, plan):
    page_title(p, "Monthly Check-in", "Twenty minutes, once a month.")
    qs = ["What went well between us this month",
          "What felt hard",
          "One thing I need more of",
          "One thing I want to give you",
          "Something I appreciated but did not say",
          "What we want next month to look like"]
    y = BODY_T
    for q in qs:
        p.text(M_L, y, q, size=9.2, bold=True, color=GOLD)
        p.rows(M_L, M_R, y + 20, 3, 21)
        y += 20 + 3 * 21 + 12


def draw_starters(p, plan):
    page_title(p, "Conversation Starters", "Pick one. No wrong answers.")
    qs = [
        "What is a small thing I do that you love",
        "When did you feel closest to me this year",
        "What is something you want to try together",
        "What does a perfect ordinary day look like",
        "What do you need when you are stressed",
        "What is a fear you have not said out loud",
        "Which memory of us would you relive",
        "What did you believe at twenty that you do not now",
        "What are you proud of right now",
        "How do you want to be comforted",
        "What is a habit you want to build together",
        "Where do you want to be in five years",
        "What is your favorite thing about our home",
        "What song reminds you of us",
        "What is one thing you want to unlearn",
        "What makes you feel appreciated",
        "What do you wish we did more often",
        "What is the kindest thing anyone has done for you",
        "What is something you want me to ask you about",
        "What would you do with a free year",
    ]
    colw = (M_R - M_L) / 2 - 16
    for i, q in enumerate(qs):
        col, row = divmod(i, 10)
        x = M_L + col * (colw + 32)
        y = BODY_T + 8 + row * 52
        p.text(x, y, f"{i + 1:02d}", size=8.6, bold=True, color=GOLD)
        p.text(x + 26, y, q, size=9.2)
        p.line(x + 26, y + 6, x + colw, y + 6, opacity=0.16)


def draw_movies(p, plan, part):
    title = "Movies to Watch" if part == 0 else "Books to Read"
    page_title(p, title, "Who picked it, and was it any good.")
    heads = ["TITLE", "PICKED BY", "DATE", "RATING", "NOTES"]
    xs = [M_L, M_L + 300, M_L + 400, M_L + 470, M_L + 570]
    for h, x in zip(heads, xs):
        p.text(x, BODY_T, h, size=7.6, bold=True, color=GOLD)
    p.line(M_L, BODY_T + 7, M_R, BODY_T + 7, color=GOLD, width=1.0, opacity=0.8)
    for i in range(17):
        y = BODY_T + 34 + i * 30
        p.line(M_L, y, M_R, y)
        for x in xs[1:]:
            p.line(x - 14, y - 21, x - 14, y, opacity=0.16)
        for s in range(5):
            p.page.draw_circle((xs[3] + 6 + s * 13, y - 8), 3.6, color=NAVY,
                               width=0.5, stroke_opacity=RULE_OP)


def draw_travel(p, plan, part):
    if part == 0:
        page_title(p, "Travel Wishlist", "Everywhere we said we would go.")
        heads = ["DESTINATION", "WHY", "BEST SEASON", "BUDGET", "DONE"]
        xs = [M_L, M_L + 220, M_L + 500, M_L + 640, M_R - 40]
        for h, x in zip(heads, xs):
            p.text(x, BODY_T, h, size=7.6, bold=True, color=GOLD)
        p.line(M_L, BODY_T + 7, M_R, BODY_T + 7, color=GOLD, width=1.0, opacity=0.8)
        for i in range(17):
            y = BODY_T + 34 + i * 30
            p.line(M_L, y, M_R, y)
            for x in xs[1:4]:
                p.line(x - 14, y - 21, x - 14, y, opacity=0.16)
            p.rect(xs[4] + 2, y - 17, xs[4] + 12, y - 7)
    else:
        page_title(p, "Trip Planner")
        fields = ["Destination", "Dates", "Flights", "Stay", "Budget", "Booked by"]
        colw = (M_R - M_L) / 2 - 18
        for i, f in enumerate(fields):
            col, row = divmod(i, 3)
            x = M_L + col * (colw + 36)
            y = BODY_T + row * 34
            p.text(x, y, f, size=8.4, bold=True, color=GOLD)
            p.line(x + 92, y, x + colw, y)
        y = BODY_T + 3 * 34 + 14
        for label, rows in [("Itinerary", 8), ("Packing list", 5)]:
            p.text(M_L, y, label, size=9.4, bold=True, color=NAVY)
            p.rows(M_L, M_R, y + 20, rows, 22)
            y += 20 + rows * 22 + 12


def draw_lined(p, plan, part):
    page_title(p, "Notes")
    p.rows(M_L, M_R, BODY_T, 22, 26)


def draw_dotted(p, plan, part):
    page_title(p, "Notes")
    p.dots(M_L, BODY_T, M_R, BODY_B)


DRAW = {
    "home": draw_home, "story": draw_story, "important": draw_important,
    "year": draw_year, "dn_ideas": draw_dn_ideas, "dn_plan": draw_dn_plan,
    "dn_bucket": draw_dn_bucket, "bucket": draw_bucket, "goals": draw_goals,
    "love": draw_love, "checkin": draw_checkin, "starters": draw_starters,
}
DRAW_PART = {"budget": draw_budget, "memories": draw_memories,
             "movies": draw_movies, "travel": draw_travel,
             "lined": draw_lined, "dotted": draw_dotted}


# ------------------------------------------------------------------- kurulum
def render_symbol_rasters(symbol_png: Path, tmp: Path, cover_w_pt, icon_w_pt):
    """Kapak (150 ppi) ve sekme ikonu (100 ppi) icin tam olculu PNG uret."""
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
    icon_state = {"size_pt": rasters["icon"]["size_pt"]}

    # Once TUM sayfalar acilir: LINK_GOTO hedefi var olmayan sayfaya bakamaz.
    # (Page nesneleri yeni sayfa eklenince gecersizlesir; sonra doc[i] ile alinir.)
    for _ in plan.pages:
        doc.new_page(width=PAGE_W, height=PAGE_H)

    for i, spec in enumerate(plan.pages):
        page = doc[i]
        p = Painter(page, fonts)
        kind = spec["kind"]

        if kind == "cover":
            draw_cover(p, plan, rasters["cover"]["path"], rasters["cover"]["size_pt"])
            p.flush()
            continue

        p.rect(0, 0, PAGE_W, PAGE_H, color=None, fill=CREAM, width=0)
        if kind == "monthly":
            draw_monthly(p, plan, spec["month"], days)
        elif kind == "weekly":
            draw_weekly(p, plan, spec["week"], days)
        elif kind in DRAW:
            DRAW[kind](p, plan)
        elif kind in DRAW_PART:
            DRAW_PART[kind](p, plan, spec["part"])
        else:
            raise RuntimeError(f"bilinmeyen sayfa tipi: {kind}")

        draw_tabs(p, plan, spec["tab"], rasters["icon"]["path"], icon_state)
        draw_footer(p)
        p.flush()

    doc.subset_fonts()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_pdf, garbage=4, deflate=True, clean=True)
    doc.close()
    return out_pdf


def verify_pdf(pdf: Path):
    doc = fitz.open(pdf)
    n = doc.page_count
    total = goto = broken = 0
    for pno in range(n):
        for lk in doc[pno].get_links():
            total += 1
            if lk["kind"] != fitz.LINK_GOTO:
                broken += 1
                continue
            goto += 1
            tgt = lk.get("page", -1)
            if not isinstance(tgt, int) or not (0 <= tgt < n):
                broken += 1
    doc.close()
    return {"pages": n, "links_total": total, "links_goto": goto,
            "links_broken": broken, "bytes": pdf.stat().st_size,
            "mb": round(pdf.stat().st_size / 1024 / 1024, 2)}


PREVIEWS = [("01_cover", "cover"), ("02_home", "home"), ("03_monthly", "monthly"),
            ("04_weekly", "weekly"), ("05_datenight", "dn_ideas"),
            ("06_notes", "lined")]


def render_previews(plan, pdf: Path, out_dir: Path):
    doc = fitz.open(pdf)
    zoom = 2732.0 / PAGE_W          # -> 2732 x 2048, gercek 4:3
    mat = fitz.Matrix(zoom, zoom)
    made = []
    first = {}
    for i, spec in enumerate(plan.pages):
        first.setdefault(spec["kind"], i)
    for name, kind in PREVIEWS:
        pix = doc[first[kind]].get_pixmap(matrix=mat, alpha=False)
        dst = out_dir / f"{name}.png"
        pix.save(dst)
        made.append({"file": dst.name, "page": first[kind] + 1,
                     "px": [pix.width, pix.height]})
    doc.close()
    return made


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster", help="lacivert/altin poster (JPG/PNG); sembol buradan kirpilir")
    ap.add_argument("--symbol", help="hazir RGBA sembol PNG (poster yerine)")
    ap.add_argument("--out", required=True, help="cikti klasoru")
    ap.add_argument("--symbol-only", action="store_true")
    ap.add_argument("--pair", default="ARIES_LEO_MB")
    ap.add_argument("--cover-frac", type=float, default=0.12, help="kapakta sembol genisligi / sayfa")
    ap.add_argument("--icon-pt", type=float, default=34.0)
    ap.add_argument("--max-mb", type=float, default=8.0)
    ap.add_argument("--font-cache", default="")
    ap.add_argument("--rclone-symbols", default="", help="or. gdrive:ASTROLOVE/PLANNER/SYMBOLS")
    ap.add_argument("--rclone-sample", default="", help="or. gdrive:ASTROLOVE/PLANNER/SAMPLE")
    a = ap.parse_args()

    if not a.poster and not a.symbol:
        ap.error("--poster veya --symbol gerekli")

    out = Path(a.out)
    sym_dir = out / "SYMBOLS"
    smp_dir = out / "SAMPLE"
    tmp = out / "_tmp"
    for d in (sym_dir, smp_dir, tmp):
        d.mkdir(parents=True, exist_ok=True)

    report = {}

    # 1) sembol
    if a.poster:
        sym_png = sym_dir / f"{a.pair}.png"
        prev_png = sym_dir / f"_preview_{a.pair.rsplit('_', 1)[0]}.png"
        info = extract_symbol(Path(a.poster), sym_png, prev_png)
        problems = check_symbol(info)
        info["problems"] = problems
        report["symbol"] = info
        print(f"[symbol] poster {info['poster_px']} -> bbox {info['bbox']} "
              f"= {info['symbol_px']} px, alan %{info['component_area_frac']*100:.2f}")
        if problems:
            print("[symbol] DUR: kirpma dogrulanamadi -> " + "; ".join(problems),
                  file=sys.stderr)
            (out / "build_report.json").write_text(json.dumps(report, indent=2))
            return 2
    else:
        sym_png = Path(a.symbol)
        report["symbol"] = {"supplied": str(sym_png)}

    if a.symbol_only:
        print(json.dumps(report, indent=2))
        return 0

    # 2) fontlar + raster olculer
    fc = Path(a.font_cache) if a.font_cache else (out / "_fonts")
    ff = fetch_fonts(fc)
    fonts = {("mont", False): fitz.Font(fontfile=str(ff[("Montserrat", "400")])),
             ("mont", True): fitz.Font(fontfile=str(ff[("Montserrat", "600")])),
             ("pf", False): fitz.Font(fontfile=str(ff[("Playfair Display", "400")])),
             ("pf", True): fitz.Font(fontfile=str(ff[("Playfair Display", "700")]))}
    rasters = render_symbol_rasters(sym_png, tmp, PAGE_W * a.cover_frac, a.icon_pt)
    report["rasters"] = {k: {"px": v["px"],
                             "pt": [round(x, 2) for x in v["size_pt"]]}
                         for k, v in rasters.items()}

    # 3) iki PDF
    plan = Plan()
    report["page_count_planned"] = len(plan)
    outs = {}
    for ws in ("MON", "SUN"):
        pdf = smp_dir / f"ASTROLOVE_PLANNER_{a.pair}_{ws}_SAMPLE.pdf"
        build_pdf(plan, fonts, rasters, ws, pdf)
        v = verify_pdf(pdf)
        outs[ws] = v
        print(f"[pdf] {pdf.name}: {v['pages']} sayfa, {v['mb']} MB, "
              f"{v['links_goto']} link, kirik {v['links_broken']}")
    report["pdf"] = outs

    fails = []
    for ws, v in outs.items():
        if v["links_broken"]:
            fails.append(f"{ws}: {v['links_broken']} kirik link")
        if v["mb"] > a.max_mb:
            fails.append(f"{ws}: {v['mb']} MB > {a.max_mb} MB")
    report["qc"] = "PASS" if not fails else "FAIL: " + "; ".join(fails)

    # 4) onizlemeler (MON surumunden)
    report["previews"] = render_previews(
        plan, smp_dir / f"ASTROLOVE_PLANNER_{a.pair}_MON_SAMPLE.pdf", smp_dir)

    (smp_dir / "build_report.json").write_text(json.dumps(report, indent=2))
    print(f"[qc] {report['qc']}")

    # 5) Drive'a yukle
    if a.rclone_symbols:
        rclone("copy", str(sym_dir), a.rclone_symbols, "-q")
        print(f"[drive] {sym_dir} -> {a.rclone_symbols}")
    if a.rclone_sample:
        rclone("copy", str(smp_dir), a.rclone_sample, "-q")
        print(f"[drive] {smp_dir} -> {a.rclone_sample}")

    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
