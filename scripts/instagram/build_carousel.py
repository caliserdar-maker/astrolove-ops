#!/usr/bin/env python3
"""
Instagram carousel uretici (IG_CAROUSEL_V2).

Her plan gunu icin bes slayt uretir ve Drive'a yazar:

  slide_1  4:5 poster, 1080x1350'e kucultme
  slide_2  WA_11 (yere yasli)   poster merkezli 4:5 kirpma, pencere 1800x2250
  slide_3  WA_03 (yemek masasi) poster merkezli 4:5 kirpma, pencere 1800x2250
  slide_4  WA_12 (konsol)       poster merkezli 4:5 kirpma, pencere 1200x1500
  slide_5  cagri karesi, edisyona gore sabit renkler

Poster tespiti FARK yontemiyle yapilir: ayni sahnenin ayni edisyondaki
baska bir cifti referans alinir; oda, cerceve ve isik ayni oldugu icin
piksel farki dogrudan posterin icine oturur. Edisyon renginden bagimsizdir
(koyu-blok yontemi acik posterlerde calismadigi icin secildi).

Drive erisimi rclone uzerinden (remote: gdrive, kok: ASTROLOVE). Plan
WA_IG_PLAN sheet'inden CSV export ile okunur; carousel icin
CAROUSEL_EDITION sutunu gecerlidir.

Kullanim:
  build_carousel.py                          # plandaki tum gunler
  build_carousel.py --edition WARM_PARCHMENT --days 4
  build_carousel.py --days 1-10,15 --contact
  build_carousel.py --plan plan.csv --dry-run
"""
import argparse
import csv
import io
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None

# ----------------------------------------------------------------- ayarlar
REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
ROOT = os.environ.get("DRIVE_ROOT", "ASTROLOVE")
PLAN_SHEET = f"{ROOT}/TEMP/WA_IG_PLAN"
POSTER_DIR = f"{ROOT}/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION"
SCENE_ROOT = f"{ROOT}/WALL_ART/LISTING_MEDIA"
OUT_DIR = f"{ROOT}/TEMP/IG_CAROUSEL_V2"

OUT_W, OUT_H = 1080, 1350
JPEG_OPTS = dict(quality=92, subsampling=0, optimize=True, dpi=(72, 72))

# Sahne sirasi: poster -> WA_11 -> WA_03 -> WA_12 -> cagri.
# Pencere oranlari 3000x2250 kaynakta 1800x2250 ve 1200x1500'e karsilik gelir;
# farkli boyutta bir render gelirse ayni oranla olceklenir.
SCENES = [
    # (slayt no, sahne kodu, Drive klasoru, pencere yuksekligi / kaynak yuksekligi)
    (2, "WA_11", "11_FLOOR_LEANING__POSTER_2X3", 1.0),
    (3, "WA_03", "03_LIVED_IN_LOVE__POSTER_2X3", 1.0),
    (4, "WA_12", "12_DESK_SIDE__POSTER_2X3", 1500 / 2250),
]

# Cagri karesi renkleri: 2026-09-01 orneklerinde posterlerden olculup onaylandi.
# Acik edisyonlarda metin, 4.5:1 kontrast icin olculen aksanin koyulastirilmis hali.
CTA_COLORS = {
    "MIDNIGHT_BLUE":   ((2, 6, 27),        (208, 164, 67)),
    "DEEP_BLACK":      ((0, 0, 0),         (237, 188, 77)),
    "WARM_PARCHMENT":  ((217, 180, 116),   (57, 24, 3)),
    "CHAMPAGNE_IVORY": ((235, 212, 185),   (56, 33, 14)),
    "PURE_WHITE":      ((255, 255, 255),   (60, 43, 12)),
}
CTA_LINES = [("DIGITAL DOWNLOAD · INSTANT", 32, 9),
             ("LINK IN BIO", 19, 8),
             ("ASTROLOVE", 32, 9)]
CTA_GAP = 95

FONT_CANDIDATES = [
    os.environ.get("IG_FONT", ""),
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
]


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ rclone
def rclone(*args, check=True):
    cmd = ["rclone", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def lsf(remote_dir, cache={}):
    """Klasordeki dosya adlari (onbellekli)."""
    if remote_dir not in cache:
        r = rclone("lsf", f"{REMOTE}:{remote_dir}", "--files-only")
        cache[remote_dir] = [l for l in r.stdout.splitlines() if l]
    return cache[remote_dir]


def fetch(remote_path, local_dir):
    """Tek dosyayi indirir, yerel yolu dondurur (varsa indirmez)."""
    local = Path(local_dir) / Path(remote_path).name
    if not local.exists():
        rclone("copyto", f"{REMOTE}:{remote_path}", str(local))
    return local


def push_dir(local_dir, remote_dir):
    rclone("copy", str(local_dir), f"{REMOTE}:{remote_dir}")


# -------------------------------------------------------------------- plan
def load_plan(plan_csv, work):
    if plan_csv:
        text = Path(plan_csv).read_text(encoding="utf-8-sig")
    else:
        # Google Sheet -> CSV export; rclone dosyayi "WA_IG_PLAN.csv" olarak gorur.
        local = Path(work) / "WA_IG_PLAN.csv"
        rclone("copyto", f"{REMOTE}:{PLAN_SHEET}.csv", str(local), "--drive-export-formats", "csv")
        text = local.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    # Baslik satirini sabit varsayma: GUN ve PAIR'i iceren ilk satir.
    for i, r in enumerate(rows):
        cells = [c.strip() for c in r]
        if "GUN" in cells and "PAIR" in cells:
            hdr = cells
            body = rows[i + 1:]
            break
    else:
        raise SystemExit("HATA: planda GUN/PAIR basligi bulunamadi.")
    idx = {h: n for n, h in enumerate(hdr)}
    need = ["GUN", "PAIR", "CAROUSEL_EDITION"]
    missing = [c for c in need if c not in idx]
    if missing:
        raise SystemExit(f"HATA: planda eksik sutun: {missing}")
    plan = []
    for r in body:
        if len(r) <= idx["PAIR"] or not r[idx["GUN"]].strip():
            continue
        try:
            gun = int(r[idx["GUN"]])
        except ValueError:
            continue
        plan.append({
            "gun": gun,
            "pair": r[idx["PAIR"]].strip(),
            "edition": r[idx["CAROUSEL_EDITION"]].strip(),
        })
    return plan


def parse_days(spec):
    """'4' | '4,7' | '1-10,15' -> kume; bos -> None (hepsi)."""
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


# ---------------------------------------------------------- dosya eslestirme
def match_pair(names, pair):
    """Listede cift adini tasiyan dosya: '..._PAIR_...' veya 'PAIR.jpg'."""
    pat = re.compile(rf"(^|_){re.escape(pair)}(_|\.)")
    hits = [n for n in names if pat.search(n)]
    if not hits:
        raise FileNotFoundError(f"{pair} icin dosya yok")
    return sorted(hits)[0]


def pick_reference(names, pair):
    """Fark yontemi icin referans cift: tercihen iki burcu da farkli olan."""
    signs = set(pair.split("_"))
    pat = re.compile(r"([A-Z]+_[A-Z]+)")
    cands = []
    for n in names:
        m = re.search(r"(?:MOCKUP_|^)([A-Z]+_[A-Z]+)", n)
        if not m:
            continue
        p = m.group(1)
        if p == pair or not p.replace("_", "").isalpha():
            continue
        cands.append((len(signs & set(p.split("_"))), p, n))
    if not cands:
        raise FileNotFoundError(f"{pair} icin referans cift yok")
    cands.sort()                       # ortak burc sayisi en az olan once
    return cands[0][2]


# ------------------------------------------------------------ goruntu isleme
def detect_center(target, reference):
    """
    Iki render'in farkindan posterin merkezini bulur.
    Dondurur: (cx, cy, guvenilir_mi, aciklama)
    """
    A = np.asarray(Image.open(target).convert("L").resize((750, 562), Image.LANCZOS), np.float32)
    B = np.asarray(Image.open(reference).convert("L").resize((750, 562), Image.LANCZOS), np.float32)
    W, H = Image.open(target).size
    d = ndimage.binary_closing(np.abs(A - B) > 18, np.ones((15, 15)))
    frac = d.mean()
    lab, n = ndimage.label(d)
    if n == 0 or not (0.002 <= frac <= 0.25):
        return W / 2, H / 2, False, f"fark alani %{frac*100:.1f} sinir disi"
    big = int(np.argmax(ndimage.sum(d, lab, range(1, n + 1)))) + 1
    ys, xs = np.where(lab == big)
    sx, sy = W / 750, H / 562
    cx, cy = (xs.min() + xs.max()) / 2 * sx, (ys.min() + ys.max()) / 2 * sy
    return cx, cy, True, f"fark %{frac*100:.1f}"


def crop_window(img, cx, cy, h_ratio):
    """Poster merkezli 4:5 pencere; kenarlara kelepceli."""
    W, H = img.size
    ch = H * h_ratio
    cw = ch * 0.8
    left = min(max(cx - cw / 2, 0), W - cw)
    top = min(max(cy - ch / 2, 0), H - ch)
    box = tuple(int(round(v)) for v in (left, top, left + cw, top + ch))
    return img.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS), box


def font_path():
    for p in FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    raise SystemExit("HATA: Liberation Serif bulunamadi (fonts-liberation kur veya IG_FONT ver).")


def draw_tracked(d, text, size, track, cy, fill, font):
    f = ImageFont.truetype(font, size)
    ws = [d.textlength(c, font=f) for c in text]
    x = (OUT_W - (sum(ws) + track * (len(text) - 1))) / 2
    asc, desc = f.getmetrics()
    y = cy - (asc - desc) / 2 - desc / 2
    for c, w in zip(text, ws):
        d.text((x, y), c, font=f, fill=fill)
        x += w + track


def build_cta(edition, font):
    bg, ink = CTA_COLORS[edition]

    def render(shift, img, fill):
        d = ImageDraw.Draw(img)
        for i, (t, s, tr) in enumerate(CTA_LINES):
            draw_tracked(d, t, s, tr, 600 + i * CTA_GAP + shift, fill, font)

    # Once maskeye ciz, murekkep sinirlarini olc, blogu tuval merkezine tasi.
    m = Image.new("L", (OUT_W, OUT_H), 0)
    render(0, m, 255)
    ys = np.where(np.asarray(m).max(1) > 0)[0]
    shift = (OUT_H - 1) / 2 - (ys.min() + ys.max()) / 2
    img = Image.new("RGB", (OUT_W, OUT_H), bg)
    render(shift, img, ink)
    return img


def contact_sheet(slides, title, font):
    cw, ch, band = 216, 270, 28
    sheet = Image.new("RGB", (cw * 5, ch + band), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.text((8, 7), title, font=ImageFont.truetype(font, 14), fill=(20, 20, 20))
    for i, p in enumerate(slides):
        sheet.paste(Image.open(p).resize((cw, ch), Image.LANCZOS), (i * cw, band))
    return sheet


# --------------------------------------------------------------------- ETA
def fmt(sec):
    sec = int(max(0, sec))
    return f"{sec//3600}s {sec%3600//60:02d}d {sec%60:02d}sn" if sec >= 3600 else f"{sec//60}d {sec%60:02d}sn"


# -------------------------------------------------------------------- main
def process_day(row, work, out_root, font, contact, dry):
    gun, pair, ed = row["gun"], row["pair"], row["edition"]
    tag = f"D{gun:02d}"
    day_out = Path(out_root) / tag
    day_out.mkdir(parents=True, exist_ok=True)
    notes = []

    if ed not in CTA_COLORS:
        raise ValueError(f"bilinmeyen edisyon: {ed}")

    # slide_1: poster
    pdir = f"{POSTER_DIR}/{ed}/4X5"
    pname = match_pair(lsf(pdir), pair)
    if not dry:
        poster = Image.open(fetch(f"{pdir}/{pname}", work)).convert("RGB")
        if abs(poster.width / poster.height - 0.8) > 0.002:
            notes.append(f"poster orani {poster.width/poster.height:.3f} != 4:5")
        poster.resize((OUT_W, OUT_H), Image.LANCZOS).save(day_out / "slide_1.jpg", "JPEG", **JPEG_OPTS)

    # slide_2..4: sahneler
    for slot, code, folder, h_ratio in SCENES:
        sdir = f"{SCENE_ROOT}/{folder}/{ed}"
        names = lsf(sdir)
        tname = match_pair(names, pair)
        rname = pick_reference(names, pair)
        if dry:
            continue
        tgt = fetch(f"{sdir}/{tname}", work)
        ref = fetch(f"{sdir}/{rname}", work)     # edisyon basina bir kez iner
        img = Image.open(tgt).convert("RGB")
        cx, cy, ok, info = detect_center(tgt, ref)
        out, box = crop_window(img, cx, cy, h_ratio)
        out.save(day_out / f"slide_{slot}.jpg", "JPEG", **JPEG_OPTS)
        if not ok:
            notes.append(f"{code}: tespit basarisiz ({info}), MERKEZ kirpma")
        tgt.unlink(missing_ok=True)              # hedef sahne bir daha lazim degil

    # slide_5: cagri
    if not dry:
        build_cta(ed, font).save(day_out / "slide_5.jpg", "JPEG", **JPEG_OPTS)

    if contact and not dry:
        cdir = Path(out_root) / "_contact"
        cdir.mkdir(exist_ok=True)
        contact_sheet([day_out / f"slide_{i}.jpg" for i in range(1, 6)],
                      f"{tag} · {pair} · {ed}", font).save(cdir / f"{tag}.jpg", "JPEG", quality=85)
    return tag, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edition", help="yalnizca bu CAROUSEL_EDITION")
    ap.add_argument("--days", help="gun secimi: 4 | 4,7 | 1-10,15")
    ap.add_argument("--contact", action="store_true", help="gun basina kontak sayfasi uret")
    ap.add_argument("--plan", help="yerel plan CSV (Drive yerine)")
    ap.add_argument("--work", default="_work", help="indirme/onbellek dizini")
    ap.add_argument("--out", default="_out", help="yerel cikti dizini")
    ap.add_argument("--no-upload", action="store_true", help="Drive'a yazma")
    ap.add_argument("--force", action="store_true", help="Drive'da var olsa da yeniden uret")
    ap.add_argument("--dry-run", action="store_true", help="dosyalari esle, uretme")
    a = ap.parse_args()

    Path(a.work).mkdir(parents=True, exist_ok=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    font = font_path()

    plan = load_plan(a.plan, a.work)
    days = parse_days(a.days)
    todo = [r for r in plan
            if (days is None or r["gun"] in days)
            and (not a.edition or r["edition"] == a.edition)]
    if not todo:
        raise SystemExit("Secime uyan gun yok.")

    if not a.force and not a.dry_run and not a.no_upload:
        done = set()
        try:
            r = rclone("lsf", f"{REMOTE}:{OUT_DIR}", "--dirs-only", check=False)
            done = {l.strip("/") for l in r.stdout.splitlines()}
        except RuntimeError:
            pass
        skipped = [r for r in todo if f"D{r['gun']:02d}" in done]
        todo = [r for r in todo if f"D{r['gun']:02d}" not in done]
        if skipped:
            names = ", ".join("D%02d" % r["gun"] for r in skipped)
            log(f"Drive'da zaten var, atlaniyor: {names}")
        if not todo:
            log("Uretilecek gun kalmadi."); return

    total, t0 = len(todo), time.time()
    log(f"{total} gun uretilecek | edisyon: {a.edition or 'hepsi'} | kontak: {'evet' if a.contact else 'hayir'}")
    log("-" * 72)
    summary = []
    for i, row in enumerate(todo, 1):
        ts = time.time()
        try:
            tag, notes = process_day(row, a.work, a.out, font, a.contact, a.dry_run)
            if not a.dry_run and not a.no_upload:
                push_dir(Path(a.out) / tag, f"{OUT_DIR}/{tag}")
                if a.contact:
                    push_dir(Path(a.out) / "_contact", f"{OUT_DIR}/_contact")
            status = "OK" if not notes else "BAK"
        except Exception as e:
            tag, notes, status = f"D{row['gun']:02d}", [f"{type(e).__name__}: {e}"], "HATA"
        elapsed = time.time() - t0
        eta = elapsed / i * (total - i)
        log(f"{i}/{total} (%{100*i/total:5.1f}) | {tag} {row['pair']:<22} {row['edition']:<16} "
            f"| {status:<4} | {time.time()-ts:4.0f}sn | gecen {fmt(elapsed)} | kalan ~{fmt(eta)}")
        for n in notes:
            log(f"        - {n}")
        summary.append((tag, row["pair"], row["edition"], status, "; ".join(notes)))

    log("-" * 72)
    bad = [s for s in summary if s[3] != "OK"]
    log(f"BITTI: {total} gun | OK {total-len(bad)} | BAK/HATA {len(bad)} | sure {fmt(time.time()-t0)}")

    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"## IG carousel: {total} gun, {len(bad)} sorunlu\n\n| Gun | Cift | Edisyon | Durum | Not |\n|---|---|---|---|---|\n")
            for s in summary:
                f.write("| " + " | ".join(s) + " |\n")
    if any(s[3] == "HATA" for s in summary):
        sys.exit(1)


if __name__ == "__main__":
    main()
