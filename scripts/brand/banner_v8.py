#!/usr/bin/env python3
"""AstroLove Etsy magaza banner'i (3360x840) alt satir metni uretimi.

START_HERE B81-EK (22 Agu 2026) V7 spesi kilitlidir: sol blokta dort oge
(logo, ASTROLOVE, satir1, satir2) poster cerceve araligina hizalidir
(ust=ust, alt=alt, 3 esit bosluk ~77.7 px; olculen 139-628 / cerceve 139-629).
Bu script kilitli kompozisyonu ONAYLI V7 PNG'sinden alir ve YALNIZ alt satiri
(satir2) yeniden cizer; logo, posterler, ASTROLOVE, satir1 ve slogan bolgeleri
piksel piksel korunur.

Tipografi V7'den OLCULEREK turetildi (tahmin yok): Montserrat variable,
wght 540, boyut 27 px, harf araligi 2.60 px, renk = V7 metin rengi, satir
merkezi ve cap-ust y'si V7 ile ayni. Ayni parametrelerle V7 metni verilirse
V7 birebir geri uretilir (--verify bunu olcer).

Kullanim:
  python3 scripts/brand/banner_v8.py --base ASTROLOVE_BANNER_ETSY_3360x840_V7.png \\
      --out ASTROLOVE_BANNER_ETSY_3360x840_V8.png \\
      --line2 "78 PAIRS · 5 COLOR EDITIONS · DOWNLOADS & PRINTS" --verify
  # V7'yi geri uretmek (kalibrasyon kaniti):
  python3 scripts/brand/banner_v8.py --base V7.png --out V7_repro.png \\
      --line2 "78 PAIRS · 5 COLOR EDITIONS · INSTANT DOWNLOAD"
"""
import argparse
import os
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 3360, 840
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
            "montserrat/Montserrat%5Bwght%5D.ttf")
FONT_FILE = "Montserrat[wght].ttf"

# V7'den olculen tipografi (bkz. modul basligi)
L2_SIZE, L2_WGHT, L2_TRACK = 27, 540, 2.60
# sol blok temizlik penceresi: posterlerin sol kenari 1076 px
CLEAR_X0, CLEAR_X1 = 0, 1050
CLEAR_PAD = 14

# bolge kutulari (x0, y0, x1, y1) - dogrulama icin
REGIONS = {
    "logo": (300, 130, 780, 285),
    "ASTROLOVE": (170, 345, 910, 435),
    "satir1": (100, 500, 980, 537),
    "satir2": (60, 596, 1020, 642),
    "slogan": (1800, 700, 2560, 765),
    "posterler": (1050, 60, 3360, 700),
}


def log(msg):
    print(msg, flush=True)


def font_path(fonts_dir, fetch):
    p = os.path.join(fonts_dir, FONT_FILE)
    if not os.path.exists(p):
        if not fetch:
            sys.exit(f"HATA: font yok: {p} (--fetch-fonts ile indirilebilir)")
        os.makedirs(fonts_dir, exist_ok=True)
        log(f"font indiriliyor: {FONT_FILE}")
        with urllib.request.urlopen(FONT_URL, timeout=60) as r, open(p, "wb") as f:
            f.write(r.read())
    return p


def bands(arr, bg, x0=0, x1=1050, thr=40):
    """Sol bloktaki yatay metin/oge bantlarini (y0, y1, x0, x1) olarak dondurur."""
    d = np.abs(arr[:, x0:x1] - bg).sum(axis=2)
    m = d > thr
    rows = np.where(m.any(axis=1))[0]
    out, s, prev = [], None, None
    for y in rows:
        if s is None:
            s = y
        elif y - prev > 4:
            out.append((s, prev))
            s = y
        prev = y
    if s is not None:
        out.append((s, prev))
    res = []
    for y0, y1 in out:
        xs = np.where(m[y0:y1 + 1].any(axis=0))[0]
        res.append((int(y0), int(y1), int(xs.min() + x0), int(xs.max() + x0)))
    return res


def measure(base):
    """Kilitli kompozisyonu olcer: zemin/metin rengi ve dort oge kutusu."""
    a = np.asarray(base.convert("RGB")).astype(int)
    bg = a[5, 5]
    bb = bands(a, bg)
    if len(bb) != 4:
        sys.exit(f"HATA: sol blokta 4 oge beklenirken {len(bb)} bulundu: {bb}")
    logo, title, l1, l2 = bb
    seg = a[l2[0]:l2[1] + 1, l2[2]:l2[3] + 1]
    dark = seg[np.abs(seg - bg).sum(axis=2) > 150]
    ink = tuple(int(v) for v in np.median(dark, axis=0))
    m = {
        "bg": tuple(int(v) for v in bg), "ink": ink,
        "logo": logo, "ASTROLOVE": title, "satir1": l1, "satir2": l2,
        "merkez": [(o[2] + o[3]) / 2 for o in (logo, title, l1, l2)],
        "bosluklar": [title[0] - logo[1] - 1, l1[0] - title[1] - 1, l2[0] - l1[1] - 1],
    }
    return m


def line_image(txt, fpath, size, wght, track, ink, bg):
    """Metni harf harf, sabit harf araligi ile cizer; sikica kirpar."""
    f = ImageFont.truetype(fpath, size)
    f.set_variation_by_axes([wght])
    pad = 80
    im = Image.new("RGB", (4 * W, 4 * size + 2 * pad), tuple(bg))
    d = ImageDraw.Draw(im)
    x = float(pad)
    for ch in txt:
        d.text((x, pad), ch, font=f, fill=tuple(ink))
        x += d.textlength(ch, font=f) + track
    a = np.asarray(im).astype(int)
    m = np.abs(a - np.array(bg)).sum(axis=2) > 40
    ys, xs = np.where(m.any(axis=1))[0], np.where(m.any(axis=0))[0]
    return im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def build(base, m, txt, fpath):
    """Alt satir bandini temizler ve yeni metni V7 konumuna cizer."""
    out = base.copy().convert("RGB")
    y0, y1, x0, x1 = m["satir2"]
    ImageDraw.Draw(out).rectangle(
        [CLEAR_X0, y0 - CLEAR_PAD, CLEAR_X1, y1 + CLEAR_PAD], fill=m["bg"])
    line = line_image(txt, fpath, L2_SIZE, L2_WGHT, L2_TRACK, m["ink"], m["bg"])
    cx = (x0 + x1 + 1) / 2.0                      # V7 satir merkezi korunur
    px = int(round(cx - line.width / 2.0))
    if px < CLEAR_X0 or px + line.width > CLEAR_X1:
        sys.exit(f"HATA: metin sol bloga sigmiyor (genislik {line.width}, x {px}).")
    out.paste(line, (px, y0))                     # cap-ust y'si V7 ile ayni
    return out, {"genislik": line.width, "yukseklik": line.height,
                 "x0": px, "x1": px + line.width - 1, "y0": y0,
                 "y1": y0 + line.height - 1, "merkez": px + line.width / 2.0}


def compare(base, out):
    """Bolge bazli piksel farki (ortalama mutlak fark + degisen piksel sayisi)."""
    a = np.asarray(base.convert("RGB")).astype(int)
    b = np.asarray(out.convert("RGB")).astype(int)
    d = np.abs(a - b).sum(axis=2)
    rows = []
    for name, (x0, y0, x1, y1) in REGIONS.items():
        s = d[y0:y1, x0:x1]
        rows.append((name, round(float(s.mean()), 4), int((s > 0).sum()), int(s.max())))
    rows.append(("TUM KARE", round(float(d.mean()), 4), int((d > 0).sum()), int(d.max())))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="onayli V7 PNG (3360x840)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--line2", required=True, help="alt satir metni")
    ap.add_argument("--fonts", default="fonts")
    ap.add_argument("--fetch-fonts", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="V7 metniyle yeniden uretip kalibrasyonu olcer")
    ap.add_argument("--v7-line2", default="78 PAIRS · 5 COLOR EDITIONS · INSTANT DOWNLOAD")
    a = ap.parse_args()

    base = Image.open(a.base).convert("RGB")
    if base.size != (W, H):
        sys.exit(f"HATA: taban {base.size}, beklenen {(W, H)}")
    fpath = font_path(a.fonts, a.fetch_fonts)
    m = measure(base)
    log(f"olcum: zemin {m['bg']} metin {m['ink']}")
    for k in ("logo", "ASTROLOVE", "satir1", "satir2"):
        y0, y1, x0, x1 = m[k]
        log(f"  {k:<10} y {y0}-{y1} (h {y1 - y0 + 1})  x {x0}-{x1} (w {x1 - x0 + 1})  "
            f"merkez {(x0 + x1) / 2:.1f}")
    log(f"  bosluklar (3 esit olmali): {m['bosluklar']}")

    if a.verify:
        rep, info = build(base, m, a.v7_line2, fpath)
        rows = compare(base, rep)
        log("kalibrasyon (V7 metni yeniden uretildi):")
        for n, mean, cnt, mx in rows:
            log(f"  {n:<10} ort fark {mean:<8} degisen px {cnt:<8} max {mx}")
        log(f"  yeniden uretilen satir2: {info}")

    out, info = build(base, m, a.line2, fpath)
    out.save(a.out, "PNG", optimize=True)
    log(f"yazildi: {a.out} ({os.path.getsize(a.out)} B)")
    log(f"yeni satir2: y {info['y0']}-{info['y1']} x {info['x0']}-{info['x1']} "
        f"w {info['genislik']} merkez {info['merkez']:.1f}")
    log("bolge farklari (taban vs cikti):")
    for n, mean, cnt, mx in compare(base, out):
        log(f"  {n:<10} ort fark {mean:<8} degisen px {cnt:<8} max {mx}")


if __name__ == "__main__":
    main()
