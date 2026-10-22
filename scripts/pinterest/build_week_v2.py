#!/usr/bin/env python3
"""
Pinterest haftalik toplu-pin CSV'si V2 (KARAR 2 Eyl 2026).

Takvim : gunde 12 pin, UTC 08:00-19:00 arasi 60 dk arayla; 390 pin = 33 gun
         (32 tam gun + 6). Haftalik dosya 7 gun x 12 = 84 pin (son hafta 54).
Metin  : docs/PIN_TEXT_TEMPLATE_V2.md sablonundan KOD ICINDE uretilir (eski GUN
         CSV metinleri kullanilmaz). Tek pano, EN, hashtag yok.
Sira   : 5 edisyon donusumlu, cift ofsetli (slot i: edisyon i%5, cift
         (i//5 + 16*(i%5)) % 78, ciftler alfabetik); her (cift, edisyon) bir kez.
Girdi  : TEMP/PIN_UPLOAD_STATE_V2.csv (pair, edition, file_id, webContentLink)
         TEMP/PIN_LISTING_MAP.csv (pair, edition, listing_id). Harita yoksa
         --gun-dir'deki eski WA_PIN_GUN_xx.csv dosyalarindan YALNIZ Link kolonu
         okunarak uretilir ve Drive'a yazilir.
Cikti  : TEMP/PIN_CSVS_V2/WA_PIN_V2_HAFTAn_GUNxx_yy.csv (8 kolon, UTF-8 BOM, LF,
         Publish date "YYYY-MM-DD HH:MM" UTC) + TEMP/PIN_CSVS_V2/WA_PIN_V2_PLAN_390.csv
--archive-v1: eski TEMP/PIN_CSVS/WA_PIN_GUN_*.csv ve WA_PIN_HAFTA*.csv dosyalarini
         ARCHIVE/PIN_CSVS_V1/ altina TASIR (silmez).
Dogrulama (dusen varsa dosya yazilmaz): satir sayisi, 8 kolon, benzersiz Media
URL / Link / Publish date, tarih araligi, 200 pin siniri, tum medya STATE_V2'den,
tum linkler haritadan, baslik <= 100, aciklama <= 500, hashtag yok.
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
STATE_PATH = f"{ROOT}/TEMP/PIN_UPLOAD_STATE_V2.csv"
MAP_PATH = f"{ROOT}/TEMP/PIN_LISTING_MAP.csv"
OLD_DIR = f"{ROOT}/TEMP/PIN_CSVS"
ARCHIVE_DIR = f"{ROOT}/ARCHIVE/PIN_CSVS_V1"
OUT_DIR = f"{ROOT}/TEMP/PIN_CSVS_V2"

COLUMNS = ["Title", "Media URL", "Pinterest board", "Thumbnail",
           "Description", "Link", "Publish date", "Keywords"]
BOARD = "Zodiac Compatibility Wall Art"
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "PURE_WHITE", "CHAMPAGNE_IVORY", "WARM_PARCHMENT"]
PINS_PER_DAY = 12
START_HOUR_UTC = 8
STEP_MINUTES = 60
DAYS_PER_WEEK = 7
TOTAL = 390
MAX_PINS_PER_FILE = 200
DATE_FMT = "%Y-%m-%d %H:%M"
PAIR_OFFSET = 16

# ---- Sablon (docs/PIN_TEXT_TEMPLATE_V2.md ile birebir) ----
TITLE_TPL = "{S1} & {S2} Zodiac Wall Art — Couple Compatibility Print, {Edition}"
DESC_TPL = ("{S1} & {S2} united in one original zodiac pair symbol — AstroLove couple wall art in the "
            "{Edition} Edition. A meaningful anniversary or Valentine's gift for astrology lovers, and a quiet "
            "statement piece for a shared bedroom or living room. Instant digital download, printable in 5 sizes. "
            "Explore all 78 zodiac pairs in 5 editions in the AstroLove shop.")
KW_TPL = "zodiac wall art, couple gift, astrology decor, {s1} {s2}, compatibility art, celestial print"


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


def write_csv(rows, path, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def texts(pair, edition):
    s1, s2 = pair.split("_")
    ed = edition.replace("_", " ").title()
    v = dict(S1=s1.title(), S2=s2.title(), Edition=ed, s1=s1.lower(), s2=s2.lower())
    return TITLE_TPL.format(**v), DESC_TPL.format(**v), KW_TPL.format(**v)


# ------------------------------------------------------------ listing haritasi
TITLE_RE = re.compile(r"^(\w+) and (\w+) Zodiac Wall Art, (.+?) Edition")


def build_map_from_gun(gun_dir):
    """Eski GUN CSV'lerinden YALNIZ (pair, edition) -> listing_id."""
    out = {}
    for p in sorted(Path(gun_dir).glob("WA_PIN_GUN_*.csv")):
        _, rows = read_csv(p)
        for r in rows:
            m = TITLE_RE.match(r["Title"])
            lid = re.search(r"/listing/(\d+)", r["Link"])
            if m and lid:
                key = (f"{m.group(1)}_{m.group(2)}".upper(), m.group(3).upper().replace(" ", "_"))
                out[key] = lid.group(1)
    return [{"pair": k[0], "edition": k[1], "listing_id": v} for k, v in sorted(out.items())]


# ---------------------------------------------------------------------- plan
def build_plan(state, lmap):
    link = {(r["pair"], r["edition"]): r for r in state}
    lst = {(r["pair"], r["edition"]): r["listing_id"] for r in lmap}
    pairs = sorted({r["pair"] for r in state})
    plan, missing = [], []
    for i in range(TOTAL):
        e = i % len(EDITIONS)
        pair = pairs[(i // len(EDITIONS) + PAIR_OFFSET * e) % len(pairs)]
        ed = EDITIONS[e]
        if (pair, ed) not in link or (pair, ed) not in lst:
            missing.append(f"{pair}/{ed}")
            continue
        title, desc, kw = texts(pair, ed)
        plan.append((pair, ed, link[(pair, ed)]["file_id"], {
            "Title": title, "Media URL": link[(pair, ed)]["webContentLink"], "Pinterest board": BOARD,
            "Thumbnail": "", "Description": desc, "Link": f"https://www.etsy.com/listing/{lst[(pair, ed)]}",
            "Publish date": "", "Keywords": kw}))
    return plan, missing, len(pairs)


def schedule(plan, start_date, day_from, day_to):
    out = []
    for i, (pair, ed, fid, r) in enumerate(plan):
        day, slot = i // PINS_PER_DAY + 1, i % PINS_PER_DAY
        if not (day_from <= day <= day_to):
            continue
        t = dt.datetime.combine(start_date + dt.timedelta(days=day - day_from), dt.time(START_HOUR_UTC, 0)) \
            + dt.timedelta(minutes=STEP_MINUTES * slot)
        r = dict(r)
        r["Publish date"] = t.strftime(DATE_FMT)
        out.append((day, slot, pair, ed, fid, r))
    return out


def validate(rows, day_from, day_to, start_date, state_urls, listing_ids):
    errors = []
    ndays = day_to - day_from + 1
    expected = sum(PINS_PER_DAY if d <= 32 else TOTAL - 32 * PINS_PER_DAY for d in range(day_from, day_to + 1))
    if len(rows) != expected:
        errors.append(f"satir sayisi {len(rows)}, beklenen {expected}")
    if len(rows) > MAX_PINS_PER_FILE:
        errors.append(f"{len(rows)} > dosya siniri {MAX_PINS_PER_FILE}")
    for col in ("Media URL", "Link", "Publish date", "Title"):
        vals = [r[col] for r in rows]
        if len(set(vals)) != len(vals):
            errors.append(f"{col} tekrarli")
    for n, r in enumerate(rows, 2):
        if r["Media URL"] not in state_urls:
            errors.append(f"satir {n}: Media URL STATE_V2'de yok")
        if r["Link"].rsplit("/", 1)[1] not in listing_ids:
            errors.append(f"satir {n}: Link haritada yok")
        if len(r["Title"]) > 100:
            errors.append(f"satir {n}: Title > 100 ({len(r['Title'])})")
        if not 300 <= len(r["Description"]) <= 500:
            errors.append(f"satir {n}: Description {len(r['Description'])} karakter (300-500 disi)")
        if "#" in r["Description"] or "#" in r["Title"]:
            errors.append(f"satir {n}: hashtag var")
        if r["Pinterest board"] != BOARD or r["Thumbnail"]:
            errors.append(f"satir {n}: pano/thumbnail hatali")
        if not r["Keywords"].strip():
            errors.append(f"satir {n}: Keywords bos")
    if rows:
        stamps = [dt.datetime.strptime(r["Publish date"], DATE_FMT) for r in rows]
        want_first = dt.datetime.combine(start_date, dt.time(START_HOUR_UTC, 0))
        last_slots = PINS_PER_DAY if day_to <= 32 else TOTAL - 32 * PINS_PER_DAY
        want_last = dt.datetime.combine(start_date + dt.timedelta(days=ndays - 1), dt.time(START_HOUR_UTC, 0)) \
            + dt.timedelta(minutes=STEP_MINUTES * (last_slots - 1))
        if min(stamps) != want_first or max(stamps) != want_last:
            errors.append(f"tarih araligi {min(stamps)}..{max(stamps)}, beklenen {want_first}..{want_last}")
        if stamps != sorted(stamps):
            errors.append("Publish date sirali degil")
    return errors


def archive_v1():
    """Eski GUN/HAFTA CSV'lerini ARCHIVE/PIN_CSVS_V1/ altina tasir (silmez)."""
    r = rclone("lsf", f"{REMOTE}:{OLD_DIR}", "--files-only", check=False)
    names = [n for n in r.stdout.splitlines() if re.match(r"WA_PIN_(GUN_\d+|HAFTA\d+_GUN\d+_\d+)\.csv$", n)]
    for n in names:
        rclone("moveto", f"{REMOTE}:{OLD_DIR}/{n}", f"{REMOTE}:{ARCHIVE_DIR}/{n}")
    left = [n for n in rclone("lsf", f"{REMOTE}:{OLD_DIR}", "--files-only", check=False).stdout.splitlines() if n]
    arch = [n for n in rclone("lsf", f"{REMOTE}:{ARCHIVE_DIR}", "--files-only").stdout.splitlines() if n]
    log(f"arsiv: {len(names)} dosya tasindi -> {ARCHIVE_DIR}/ (arsivde {len(arch)}, PIN_CSVS'te kalan {len(left)}: {left[:5]})")
    return names, arch, left


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--start-date", required=True, help="haftanin ilk gununun tarihi, YYYY-MM-DD (UTC)")
    ap.add_argument("--src", help="yerel klasor: PIN_UPLOAD_STATE_V2.csv + PIN_LISTING_MAP.csv (Drive yerine)")
    ap.add_argument("--gun-dir", help="harita yoksa eski GUN CSV klasoru (yerel)")
    ap.add_argument("--archive-v1", action="store_true", help="eski GUN/HAFTA CSV'lerini ARCHIVE/PIN_CSVS_V1'e tasi")
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
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    # Girdiler
    if a.src:
        src = Path(a.src)
    else:
        src = work / "src"; src.mkdir(exist_ok=True)
        rclone("copyto", f"{REMOTE}:{STATE_PATH}", str(src / "PIN_UPLOAD_STATE_V2.csv"))
        r = rclone("copyto", f"{REMOTE}:{MAP_PATH}", str(src / "PIN_LISTING_MAP.csv"), check=False)
        if r.returncode != 0:
            gun = work / "gun"; gun.mkdir(exist_ok=True)
            rclone("copy", f"{REMOTE}:{OLD_DIR}", str(gun), "--include", "WA_PIN_GUN_*.csv")
            rclone("copy", f"{REMOTE}:{ARCHIVE_DIR}", str(gun), "--include", "WA_PIN_GUN_*.csv", check=False)
            a.gun_dir = str(gun)
        if not a.force and not a.no_upload:
            r = rclone("lsf", f"{REMOTE}:{OUT_DIR}/{name}", check=False)
            if r.returncode == 0 and r.stdout.strip():
                sys.exit(f"HATA: {OUT_DIR}/{name} zaten var; --force gerekir")
    _, state = read_csv(src / "PIN_UPLOAD_STATE_V2.csv")
    if (src / "PIN_LISTING_MAP.csv").exists():
        _, lmap = read_csv(src / "PIN_LISTING_MAP.csv")
        log(f"listing haritasi: {len(lmap)} satir (Drive)")
    else:
        if not a.gun_dir:
            sys.exit("HATA: PIN_LISTING_MAP.csv yok ve --gun-dir verilmedi")
        lmap = build_map_from_gun(a.gun_dir)
        write_csv(lmap, out / "PIN_LISTING_MAP.csv", ["pair", "edition", "listing_id"])
        log(f"listing haritasi eski GUN CSV'lerinden uretildi: {len(lmap)} satir")
        if not a.no_upload:
            rclone("copyto", str(out / "PIN_LISTING_MAP.csv"), f"{REMOTE}:{MAP_PATH}")
            log(f"yuklendi: {MAP_PATH}")
    if len(lmap) != TOTAL:
        sys.exit(f"HATA: listing haritasi {len(lmap)} satir, beklenen {TOTAL}")

    archived = None
    if a.archive_v1 and not a.no_upload:
        archived = archive_v1()

    # Plan + hafta
    plan, missing, npairs = build_plan(state, lmap)
    errors = [f"eksik (pair/edition): {len(missing)} {missing[:3]}"] if missing else []
    if npairs != 78 or len(plan) != TOTAL:
        errors.append(f"plan {len(plan)} satir / {npairs} cift, beklenen 390 / 78")
    sched = schedule(plan, start_date, day_from, day_to)
    week_rows = [r for *_, r in sched]
    errors += validate(week_rows, day_from, day_to, start_date,
                       {s["webContentLink"] for s in state}, {m["listing_id"] for m in lmap})

    uploaded = False
    if not errors:
        write_csv(week_rows, out / name, COLUMNS)
        base = start_date - dt.timedelta(days=day_from - 1)
        full = schedule(plan, base, 1, 33)
        plan_rows = [{"hafta": (d - 1) // DAYS_PER_WEEK + 1, "gun": d, "slot": s + 1, "publish_utc": r["Publish date"],
                      "pair": p, "edition": e, "media_id": fid, "listing": r["Link"].rsplit("/", 1)[1]}
                     for d, s, p, e, fid, r in full]
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
             f"| Drive | {OUT_DIR}/{name if uploaded else '(yuklenmedi)'} |"]
    if archived:
        lines.append(f"| Arsiv | {len(archived[0])} dosya -> {ARCHIVE_DIR}/ (arsivde {len(archived[1])}, kalan {len(archived[2])}) |")
    lines += ["", "Ilk 2 satir (tam metin):", ""]
    for i, (d, s, p, e, fid, r) in enumerate(sched[:2], 1):
        lines += [f"**{i}. {r['Publish date']} UTC · {p} · {e} · medya {fid} · listing {r['Link'].rsplit('/', 1)[1]}**",
                  f"- Title ({len(r['Title'])}): {r['Title']}",
                  f"- Description ({len(r['Description'])}): {r['Description']}",
                  f"- Keywords: {r['Keywords']}", ""]
    if errors:
        lines += ["Hatalar:"] + [f"- {e}" for e in errors[:20]]
    text = "\n".join(lines)
    log(text)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
