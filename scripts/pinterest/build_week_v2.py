#!/usr/bin/env python3
"""
Pinterest haftalik toplu-pin CSV'si V2 (KARAR 2 Eyl 2026).

Takvim : gunde 12 pin, UTC 08:00-19:00 arasi 60 dk arayla; 390 pin = 33 gun
         (32 tam gun + 6). Haftalik dosya 7 gun x 12 = 84 pin.
Metin  : mevcut TEMP/PIN_CSVS/WA_PIN_GUN_01..30.csv satirlari (tek pano,
         edisyon donusumlu sira, EN baslik/aciklama/keyword sablonu, canli Etsy
         linki) AYNEN; yalniz Media URL, PIN_MEDIA_V2'nin webContentLink'i ile
         degistirilir (TEMP/PIN_UPLOAD_STATE_V2.csv, pair+edition eslesmesi).
Sira   : GUN_01..30 satir sirasi korunur, 12'lik gunlere yeniden bolunur.
Cikti  : TEMP/PIN_CSVS_V2/WA_PIN_V2_HAFTAn_GUNxx_yy.csv (8 kolon, UTF-8 BOM, LF,
         Publish date "YYYY-MM-DD HH:MM" UTC) + TEMP/PIN_CSVS_V2/WA_PIN_V2_PLAN_390.csv
         (tum plan: gun, slot, publish, pair, edition, media_id).
Dogrulama (dusen varsa dosya yazilmaz): satir sayisi, 8 kolon, benzersiz Media
URL / Link / Publish date, tarih araligi, 200 pin siniri, tum medya linkleri
STATE_V2'den, baslik <= 100, aciklama <= 500.
Pinterest'e dokunmaz; CSV elle yuklenir.
"""

import argparse
import csv
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
ROOT = os.environ.get("DRIVE_ROOT", "ASTROLOVE")
SRC_DIR = f"{ROOT}/TEMP/PIN_CSVS"
STATE_PATH = f"{ROOT}/TEMP/PIN_UPLOAD_STATE_V2.csv"
OUT_DIR = f"{ROOT}/TEMP/PIN_CSVS_V2"

COLUMNS = ["Title", "Media URL", "Pinterest board", "Thumbnail",
           "Description", "Link", "Publish date", "Keywords"]
PINS_PER_DAY = 12
START_HOUR_UTC = 8
STEP_MINUTES = 60
DAYS_PER_WEEK = 7
MAX_PINS_PER_FILE = 200
DATE_FMT = "%Y-%m-%d %H:%M"
TITLE_RE = re.compile(r"^(\w+) and (\w+) Zodiac Wall Art, (.+?) Edition")


def log(msg):
    print(msg, flush=True)


def rclone(*args, check=True):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): rclone {' '.join(args)}\n{r.stderr.strip()}")
    return r


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, [dict(x) for x in r]


def key_of(row):
    m = TITLE_RE.match(row["Title"])
    if not m:
        return None
    return f"{m.group(1)}_{m.group(2)}".upper(), m.group(3).upper().replace(" ", "_")


def load_sources(src):
    """GUN_01..30 satirlari, dosya ve satir sirasiyla."""
    rows = []
    for day in range(1, 31):
        p = Path(src) / f"WA_PIN_GUN_{day:02d}.csv"
        if not p.exists():
            raise FileNotFoundError(f"kaynak yok: {p.name}")
        cols, day_rows = read_csv(p)
        if cols != COLUMNS:
            raise ValueError(f"{p.name}: kolonlar beklenen degil")
        rows += day_rows
    return rows


def build_plan(rows, state):
    """Tum 390 satir: Media URL -> V2 linki; gun/slot/publish henuz bos."""
    link = {(r["pair"], r["edition"]): (r["file_id"], r["webContentLink"]) for r in state}
    plan, missing = [], []
    for r in rows:
        k = key_of(r)
        if not k or k not in link:
            missing.append(r["Title"][:60])
            continue
        fid, url = link[k]
        n = dict(r)
        n["Media URL"] = url
        n["Thumbnail"] = ""
        plan.append((k, fid, n))
    return plan, missing


def schedule(plan, start_date, day_from, day_to):
    out = []
    for i, (k, fid, r) in enumerate(plan):
        day = i // PINS_PER_DAY + 1
        slot = i % PINS_PER_DAY
        if not (day_from <= day <= day_to):
            continue
        t = dt.datetime.combine(start_date + dt.timedelta(days=day - day_from), dt.time(START_HOUR_UTC, 0)) \
            + dt.timedelta(minutes=STEP_MINUTES * slot)
        r = dict(r)
        r["Publish date"] = t.strftime(DATE_FMT)
        out.append((day, slot, k, fid, r))
    return out


def validate(rows, day_from, day_to, start_date, state_urls):
    errors = []
    ndays = day_to - day_from + 1
    full_days = min(day_to, 32) - day_from + 1
    expected = full_days * PINS_PER_DAY + (6 if day_to >= 33 else 0)
    if len(rows) != expected:
        errors.append(f"satir sayisi {len(rows)}, beklenen {expected}")
    if len(rows) > MAX_PINS_PER_FILE:
        errors.append(f"{len(rows)} > dosya siniri {MAX_PINS_PER_FILE}")
    for col in ("Media URL", "Link", "Publish date"):
        vals = [r[col] for r in rows]
        if len(set(vals)) != len(vals):
            errors.append(f"{col} tekrarli")
    for n, r in enumerate(rows, 2):
        if r["Media URL"] not in state_urls:
            errors.append(f"satir {n}: Media URL STATE_V2'de yok")
        if len(r["Title"]) > 100:
            errors.append(f"satir {n}: Title > 100")
        if len(r["Description"]) > 500:
            errors.append(f"satir {n}: Description > 500")
        if not re.fullmatch(r"https://www\.etsy\.com/listing/\d+", r["Link"]):
            errors.append(f"satir {n}: Link Etsy degil")
        for col in ("Title", "Pinterest board", "Description", "Keywords"):
            if not r[col].strip():
                errors.append(f"satir {n}: {col} bos")
    if rows:
        stamps = [dt.datetime.strptime(r["Publish date"], DATE_FMT) for r in rows]
        want_first = dt.datetime.combine(start_date, dt.time(START_HOUR_UTC, 0))
        last_day_slots = PINS_PER_DAY if day_to <= 32 else 6
        want_last = dt.datetime.combine(start_date + dt.timedelta(days=ndays - 1), dt.time(START_HOUR_UTC, 0)) \
            + dt.timedelta(minutes=STEP_MINUTES * (last_day_slots - 1))
        if min(stamps) != want_first or max(stamps) != want_last:
            errors.append(f"tarih araligi {min(stamps)}..{max(stamps)}, beklenen {want_first}..{want_last}")
        if stamps != sorted(stamps):
            errors.append("Publish date sirali degil")
        if len({r["Pinterest board"] for r in rows}) != 1:
            errors.append("birden fazla pano")
    return errors


def write_csv(rows, path, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--start-date", required=True, help="haftanin ilk gununun tarihi, YYYY-MM-DD (UTC)")
    ap.add_argument("--src", help="yerel klasor: WA_PIN_GUN_xx.csv + PIN_UPLOAD_STATE_V2.csv (Drive yerine)")
    ap.add_argument("--work", default="_work")
    ap.add_argument("--out", default="_out")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--force", action="store_true", help="Drive'da ayni adli dosya varsa uzerine yaz")
    a = ap.parse_args()

    start_date = dt.date.fromisoformat(a.start_date)
    day_from = (a.week - 1) * DAYS_PER_WEEK + 1
    day_to = min(a.week * DAYS_PER_WEEK, 33)
    if day_from > 33:
        sys.exit("HATA: hafta 33 gunu asiyor")
    name = f"WA_PIN_V2_HAFTA{a.week}_GUN{day_from:02d}_{day_to:02d}.csv"

    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    if a.src:
        src = Path(a.src)
    else:
        src = work / "src"; src.mkdir(exist_ok=True)
        rclone("copy", f"{REMOTE}:{SRC_DIR}", str(src), "--include", "WA_PIN_GUN_*.csv")
        rclone("copyto", f"{REMOTE}:{STATE_PATH}", str(src / "PIN_UPLOAD_STATE_V2.csv"))
        if not a.force and not a.no_upload:
            r = rclone("lsf", f"{REMOTE}:{OUT_DIR}/{name}", check=False)
            if r.returncode == 0 and r.stdout.strip():
                sys.exit(f"HATA: {OUT_DIR}/{name} zaten var; --force gerekir")

    rows = load_sources(src)
    _, state = read_csv(src / "PIN_UPLOAD_STATE_V2.csv")
    log(f"kaynak: {len(rows)} satir (GUN_01..30), STATE_V2: {len(state)} satir")
    plan, missing = build_plan(rows, state)
    errors = [f"STATE_V2'de karsiligi olmayan {len(missing)} satir: {missing[:3]}"] if missing else []
    if len(plan) != 390:
        errors.append(f"plan {len(plan)} satir, beklenen 390")

    sched = schedule(plan, start_date, day_from, day_to)
    week_rows = [r for _, _, _, _, r in sched]
    errors += validate(week_rows, day_from, day_to, start_date, {s["webContentLink"] for s in state})

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    uploaded = False
    if not errors:
        write_csv(week_rows, out / name, COLUMNS)
        # Tum plan (33 gun), izlenebilirlik icin; tarih gun 1 = start_date - (day_from-1).
        base = start_date - dt.timedelta(days=day_from - 1)
        full = schedule(plan, base, 1, 33)
        plan_rows = [{"gun": d, "slot": s + 1, "publish_utc": r["Publish date"], "pair": k[0], "edition": k[1],
                      "media_id": fid, "listing": r["Link"].rsplit("/", 1)[1], "hafta": (d - 1) // DAYS_PER_WEEK + 1}
                     for d, s, k, fid, r in full]
        write_csv(plan_rows, out / "WA_PIN_V2_PLAN_390.csv",
                  ["hafta", "gun", "slot", "publish_utc", "pair", "edition", "media_id", "listing"])
        if not a.no_upload:
            rclone("copyto", str(out / name), f"{REMOTE}:{OUT_DIR}/{name}")
            rclone("copyto", str(out / "WA_PIN_V2_PLAN_390.csv"), f"{REMOTE}:{OUT_DIR}/WA_PIN_V2_PLAN_390.csv")
            uploaded = True
            log(f"yuklendi: {OUT_DIR}/{name} + WA_PIN_V2_PLAN_390.csv")

    first = week_rows[0]["Publish date"] if week_rows else "-"
    last = week_rows[-1]["Publish date"] if week_rows else "-"
    lines = [f"## {name}", "", "| Alan | Deger |", "| --- | --- |",
             f"| Satir | {len(week_rows)} (gun {day_from}-{day_to}, gunde {PINS_PER_DAY}) |",
             f"| Ilk / son Publish date (UTC) | {first} / {last} |",
             f"| Dogrulama | {'GECTI' if not errors else 'DUSTU'} |",
             f"| Drive | {OUT_DIR}/{name if uploaded else '(yuklenmedi)'} |", "",
             "Ilk 6 satir:", "", "| # | Publish (UTC) | Title | Media ID | Link |", "|---|---|---|---|---|"]
    for i, (d, s, k, fid, r) in enumerate(sched[:6], 1):
        lines.append(f"| {i} | {r['Publish date']} | {r['Title'][:60]} | {fid} | {r['Link'].rsplit('/', 1)[1]} |")
    if errors:
        lines += ["", "Hatalar:"] + [f"- {e}" for e in errors[:20]]
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
