#!/usr/bin/env python3
"""
Pinterest haftalik CSV birlestirme (WA_PIN_HAFTA1_V1 mantiginin kalici hali).

TEMP/PIN_CSVS/WA_PIN_GUN_xx.csv .. WA_PIN_GUN_yy.csv dosyalarini sirayla
birlestirir, her gunun 13 satirina UTC 13:00'dan baslayip 30 dakika artan
"Publish date" yazar (TR 16:00-22:00), gunler ardisik ilerler. Cikti
TEMP/PIN_CSVS/WA_PIN_HAFTAn_GUNxx_yy.csv; format HAFTA1 ile birebir
(8 kolon, UTF-8 BOM, LF, minimum tirnak, Publish date "YYYY-MM-DD HH:MM").

Dogrulama (herhangi biri duserse dosya YAZILMAZ, cikis kodu 1):
  - her gun dosyasinda tam PINS_PER_DAY satir, toplam = gun x 13
  - kolonlar birebir COLUMNS
  - Media URL, Link ve Publish date benzersiz
  - tarih araligi start_date .. start_date + gun - 1, saatler 13:00..19:00 UTC
  - Pinterest toplu olusturma siniri: en fazla 200 pin / dosya
  - zorunlu alanlar bos degil, Thumbnail bos, Media URL Drive direkt-link

Drive erisimi rclone uzerinden (remote: gdrive, kok: ASTROLOVE). --src ile
yerel klasor verilirse Drive'dan indirilmez; --no-upload ile Drive'a yazilmaz.
Pinterest'e dokunmaz; CSV Pinterest'e elle yuklenir.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
CSV_DIR = "ASTROLOVE/TEMP/PIN_CSVS"

COLUMNS = ["Title", "Media URL", "Pinterest board", "Thumbnail",
           "Description", "Link", "Publish date", "Keywords"]
PINS_PER_DAY = 13
MAX_PINS_PER_FILE = 200          # Pinterest toplu pin olusturma siniri (B87)
START_HOUR_UTC = 13              # TR 16:00
STEP_MINUTES = 30
DATE_FMT = "%Y-%m-%d %H:%M"
MEDIA_RE = re.compile(r"^https://drive\.google\.com/uc\?export=download&id=[\w-]{20,}$")
LINK_RE = re.compile(r"^https://www\.etsy\.com/listing/\d+$")


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ rclone
def rclone(*args, check=True):
    cmd = ["rclone", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def day_name(day):
    return f"WA_PIN_GUN_{day:02d}.csv"


def fetch_days(days, work):
    work.mkdir(parents=True, exist_ok=True)
    for d in days:
        name = day_name(d)
        rclone("copyto", f"{REMOTE}:{CSV_DIR}/{name}", str(work / name))
        log(f"indirildi: {name}")
    return work


def remote_exists(name):
    r = rclone("lsf", f"{REMOTE}:{CSV_DIR}/{name}", check=False)
    return r.returncode == 0 and r.stdout.strip() != ""


# ------------------------------------------------------------------ merge
def read_day(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{path.name}: kolonlar beklenen degil: {reader.fieldnames}")
        return [dict(r) for r in reader]


def merge(src, days, start_date):
    rows = []
    errors = []
    for i, d in enumerate(days):
        path = src / day_name(d)
        if not path.exists():
            errors.append(f"{path.name} yok")
            continue
        day_rows = read_day(path)
        if len(day_rows) != PINS_PER_DAY:
            errors.append(f"{path.name}: {len(day_rows)} satir, beklenen {PINS_PER_DAY}")
        date = start_date + dt.timedelta(days=i)
        for j, r in enumerate(day_rows):
            t = dt.datetime.combine(date, dt.time(START_HOUR_UTC, 0)) + dt.timedelta(minutes=STEP_MINUTES * j)
            r = {c: r.get(c, "") for c in COLUMNS}
            r["Publish date"] = t.strftime(DATE_FMT)
            rows.append(r)
    return rows, errors


def validate(rows, days, start_date):
    errors = []
    expected = PINS_PER_DAY * len(days)
    if len(rows) != expected:
        errors.append(f"satir sayisi {len(rows)}, beklenen {expected}")
    if len(rows) > MAX_PINS_PER_FILE:
        errors.append(f"{len(rows)} pin > dosya siniri {MAX_PINS_PER_FILE}")

    for col in ("Media URL", "Link", "Publish date"):
        vals = [r[col] for r in rows]
        dup = sorted({v for v in vals if vals.count(v) > 1})
        if dup:
            errors.append(f"{col} tekrarli ({len(dup)}): {dup[:3]}")

    for n, r in enumerate(rows, 2):
        for col in ("Title", "Media URL", "Pinterest board", "Description", "Link", "Keywords"):
            if not r[col].strip():
                errors.append(f"satir {n}: {col} bos")
        if r["Thumbnail"].strip():
            errors.append(f"satir {n}: Thumbnail dolu (bos olmali)")
        if not MEDIA_RE.match(r["Media URL"]):
            errors.append(f"satir {n}: Media URL Drive direkt-link degil")
        if not LINK_RE.match(r["Link"]):
            errors.append(f"satir {n}: Link Etsy listing degil")
        if len(r["Title"]) > 100:
            errors.append(f"satir {n}: Title > 100 karakter")
        if len(r["Description"]) > 500:
            errors.append(f"satir {n}: Description > 500 karakter")

    if rows:
        stamps = [dt.datetime.strptime(r["Publish date"], DATE_FMT) for r in rows]
        first, last = min(stamps), max(stamps)
        want_first = dt.datetime.combine(start_date, dt.time(START_HOUR_UTC, 0))
        want_last = (dt.datetime.combine(start_date + dt.timedelta(days=len(days) - 1), dt.time(START_HOUR_UTC, 0))
                     + dt.timedelta(minutes=STEP_MINUTES * (PINS_PER_DAY - 1)))
        if first != want_first or last != want_last:
            errors.append(f"tarih araligi {first:%Y-%m-%d %H:%M}..{last:%Y-%m-%d %H:%M}, "
                          f"beklenen {want_first:%Y-%m-%d %H:%M}..{want_last:%Y-%m-%d %H:%M}")
        if stamps != sorted(stamps):
            errors.append("Publish date sirali degil")
        per_day = {}
        for s in stamps:
            per_day[s.date()] = per_day.get(s.date(), 0) + 1
        bad = {str(k): v for k, v in per_day.items() if v != PINS_PER_DAY}
        if bad:
            errors.append(f"gun basina pin sayisi bozuk: {bad}")
    return errors


def write_csv(rows, path):
    # HAFTA1 ile birebir: UTF-8 BOM, LF, yalniz gerekli alanlar tirnakli.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def summary(name, rows, errors, uploaded, remote_path):
    first = rows[0]["Publish date"] if rows else "-"
    last = rows[-1]["Publish date"] if rows else "-"
    state = "GECTI" if not errors else "DUSTU"
    lines = [
        f"## {name}",
        "",
        "| Alan | Deger |",
        "| --- | --- |",
        f"| Satir sayisi | {len(rows)} |",
        f"| Ilk Publish date (UTC) | {first} |",
        f"| Son Publish date (UTC) | {last} |",
        f"| Dogrulama | {state} |",
        f"| Drive | {remote_path if uploaded else '(yuklenmedi)'} |",
    ]
    if errors:
        lines += ["", "Hatalar:"] + [f"- {e}" for e in errors]
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"rows={len(rows)}\nfirst={first}\nlast={last}\nvalidation={state}\n")
            f.write(f"drive={remote_path if uploaded else ''}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", type=int, required=True, help="hafta numarasi (dosya adi: HAFTAn)")
    ap.add_argument("--day-from", type=int, required=True, help="ilk gun dosyasi, or. 9")
    ap.add_argument("--day-to", type=int, required=True, help="son gun dosyasi (dahil), or. 15")
    ap.add_argument("--start-date", required=True, help="ilk gunun yayin tarihi, YYYY-MM-DD (UTC)")
    ap.add_argument("--src", help="yerel GUN CSV klasoru (verilirse Drive'dan indirilmez)")
    ap.add_argument("--work", default="_work", help="indirme dizini")
    ap.add_argument("--out", default="_out", help="yerel cikti dizini")
    ap.add_argument("--no-upload", action="store_true", help="Drive'a yazma")
    ap.add_argument("--force", action="store_true", help="Drive'da ayni adli dosya varsa uzerine yaz")
    a = ap.parse_args()

    if a.day_from < 1 or a.day_to < a.day_from:
        sys.exit("HATA: day_from/day_to araligi gecersiz")
    try:
        start_date = dt.date.fromisoformat(a.start_date)
    except ValueError:
        sys.exit("HATA: start_date YYYY-MM-DD olmali")

    days = list(range(a.day_from, a.day_to + 1))
    name = f"WA_PIN_HAFTA{a.week}_GUN{a.day_from:02d}_{a.day_to:02d}.csv"
    remote_path = f"{REMOTE}:{CSV_DIR}/{name}"

    if not a.no_upload and not a.force and remote_exists(name):
        sys.exit(f"HATA: {CSV_DIR}/{name} Drive'da zaten var; --force olmadan uzerine yazilmaz")

    src = Path(a.src) if a.src else fetch_days(days, Path(a.work))
    rows, errors = merge(src, days, start_date)
    errors += validate(rows, days, start_date)

    uploaded = False
    if not errors:
        out_dir = Path(a.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        local = out_dir / name
        write_csv(rows, local)
        log(f"yazildi: {local} ({local.stat().st_size} bayt)")
        if not a.no_upload:
            rclone("copyto", str(local), remote_path)
            back = rclone("lsjson", remote_path).stdout
            size = json.loads(back)[0]["Size"] if back.strip() else -1
            if size != local.stat().st_size:
                errors.append(f"Drive boyutu {size} != yerel {local.stat().st_size}")
            else:
                uploaded = True
                log(f"yuklendi: {remote_path} ({size} bayt)")

    summary(name, rows, errors, uploaded, f"{CSV_DIR}/{name}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
