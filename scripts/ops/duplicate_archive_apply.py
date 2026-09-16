#!/usr/bin/env python3
"""Batch 4 duplicate planını güvenli, doğrulanmış ve devam edebilir biçimde uygula."""

import argparse
import csv
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict


ORIGINAL_PLAN_SHA256 = "ed00ee541d8be25aeab540a996bb70b5c9c70abbb9fa215f70e7ba5d12c58023"
ORIGINAL_ROWS = 722
MASTER_ROWS = 200
SAFE_ROWS = 522
GROUPS = 200
SAFE_BYTES = 541_913_817
ARCHIVE_ROOT = "ASTROLOVE/ARCHIVE/DUPLICATES/20260915_2059"
PROTECTED_RX = re.compile(r"MASTER|FINAL|APPROVED|ONAYLI|/PRINT|ETSY_ZIPS", re.I)


def fail(message):
    raise RuntimeError(message)


def drive_path(path):
    path = (path or "").lstrip("/")
    return path if path.startswith("ASTROLOVE/") else f"ASTROLOVE/{path}"


def command(*args):
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode:
        detail = (proc.stderr or proc.stdout or "").strip()[-1500:]
        fail(f"komut basarisiz ({proc.returncode}): {' '.join(args[:3])}: {detail}")
    return proc.stdout


def load_plan(path):
    raw = pathlib.Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != ORIGINAL_PLAN_SHA256:
        fail(f"plan SHA-256 uyusmuyor: {digest}")
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    if len(rows) != ORIGINAL_ROWS:
        fail(f"orijinal plan {len(rows)} satir; beklenen {ORIGINAL_ROWS}")

    master_rows, safe = [], []
    for number, row in enumerate(rows, 2):
        src = drive_path(row.get("kaynak_yol"))
        master = drive_path(row.get("korunan_master"))
        dst = drive_path(row.get("hedef_arsiv_yolu"))
        md5 = (row.get("dosya_hash_md5") or "").lower()
        if row.get("durum") != "PLANLANDI - TASINMADI":
            fail(f"satir {number}: durum guvenli degil")
        if not re.fullmatch(r"[0-9a-f]{32}", md5) or md5 != (row.get("grup_md5") or "").lower():
            fail(f"satir {number}: MD5 gecersiz")
        if src == master:
            master_rows.append(row)
            continue
        if not src.startswith("ASTROLOVE/TEMP/"):
            fail(f"satir {number}: kaynak TEMP disinda: {src}")
        if PROTECTED_RX.search(src):
            fail(f"satir {number}: korunan yol tasima kapsaminda: {src}")
        rel = src.split("ASTROLOVE/", 1)[1]
        if dst != f"{ARCHIVE_ROOT}/{rel}":
            fail(f"satir {number}: hedef kaynakla birebir eslesmiyor")
        row["kaynak_yol"] = src
        row["hedef_arsiv_yolu"] = dst
        row["korunan_master"] = master
        row["dosya_hash_md5"] = md5
        safe.append(row)

    if len(master_rows) != MASTER_ROWS:
        fail(f"yanlis dahil edilen master satiri {len(master_rows)}; beklenen {MASTER_ROWS}")
    if len(safe) != SAFE_ROWS or sum(int(r["bayt"]) for r in safe) != SAFE_BYTES:
        fail("duzeltilmis kapsam 522 dosya / 541913817 bayt degil")
    if len({r["grup_md5"] for r in safe}) != GROUPS:
        fail("duzeltilmis kapsam 200 grup degil")
    sources = [r["kaynak_yol"] for r in safe]
    targets = [r["hedef_arsiv_yolu"] for r in safe]
    masters = [r["korunan_master"] for r in safe]
    if len(set(sources)) != SAFE_ROWS or len(set(targets)) != SAFE_ROWS:
        fail("kaynak veya hedef listesinde tekrar var")
    if set(sources) & set(masters):
        fail("korunan master tasima listesinde")
    if set(sources) & set(targets):
        fail("kaynak ve hedef listeleri cakismis")
    return safe, digest


def load_excluded(path, safe_sources):
    rows = list(csv.DictReader(pathlib.Path(path).read_text(encoding="utf-8-sig").splitlines()))
    if len(rows) != 29:
        fail(f"dislanan yol sayisi {len(rows)}; beklenen 29")
    paths = {drive_path(r["yol"]) for r in rows}
    if paths & set(safe_sources):
        fail("dislanan yol guvenli tasima listesine girmis")
    return paths


def write_lines(path, values):
    pathlib.Path(path).write_text("\n".join(sorted(set(values))) + "\n", encoding="utf-8")


def remote_index(remote, values, work, label):
    list_file = work / f"{label}.txt"
    json_file = work / f"{label}.json"
    write_lines(list_file, values)
    output = command(
        "rclone", "lsjson", f"{remote}:", "--files-from", str(list_file),
        "--recursive", "--files-only", "--hash", "--no-modtime", "--no-mimetype",
    )
    json_file.write_text(output, encoding="utf-8")
    index = {}
    for item in json.loads(output or "[]"):
        path = drive_path(item.get("Path") or item.get("Name"))
        hashes = item.get("Hashes") or {}
        index[path] = {
            "md5": (hashes.get("MD5") or hashes.get("md5") or "").lower(),
            "size": int(item.get("Size") or 0),
        }
    return index


def verify_masters(rows, index):
    expected = defaultdict(set)
    for row in rows:
        expected[row["korunan_master"]].add(row["dosya_hash_md5"])
    if len(expected) != GROUPS:
        fail(f"benzersiz master sayisi {len(expected)}; beklenen {GROUPS}")
    for path, hashes in expected.items():
        if len(hashes) != 1:
            fail(f"master birden fazla hash ile eslesiyor: {path}")
        if path not in index:
            fail(f"korunan master Drive'da yok: {path}")
        if index[path]["md5"] != next(iter(hashes)):
            fail(f"korunan master MD5 uyusmuyor: {path}")


def classify(rows, sources, targets):
    pending, archived = [], []
    for row in rows:
        src, dst, md5 = row["kaynak_yol"], row["hedef_arsiv_yolu"], row["dosya_hash_md5"]
        source, target = sources.get(src), targets.get(dst)
        if source and target:
            fail(f"kaynak ve hedef birlikte mevcut: {src}")
        if source:
            if source["md5"] != md5 or source["size"] != int(row["bayt"]):
                fail(f"kaynak hash/boyut uyusmuyor: {src}")
            pending.append(row)
        elif target:
            if target["md5"] != md5 or target["size"] != int(row["bayt"]):
                fail(f"hedef hash/boyut uyusmuyor: {dst}")
            archived.append(row)
        else:
            fail(f"kaynak ve hedef birlikte kayip: {src}")
    return pending, archived


def write_rollback(path, rows, remote):
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for row in rows:
        lines.append(
            f'rclone moveto "{remote}:{row["hedef_arsiv_yolu"]}" '
            f'"{remote}:{row["kaynak_yol"]}"'
        )
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_result(path, rows, statuses):
    fields = ["grup_md5", "kaynak_yol", "hedef_arsiv_yolu", "dosya_hash_md5", "bayt", "sonuc"]
    with pathlib.Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row[k] for k in fields[:-1]}, "sonuc": statuses[row["kaynak_yol"]]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--excluded", required=True)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    work = args.out / "preflight"
    work.mkdir(exist_ok=True)

    rows, plan_sha = load_plan(args.plan)
    sources = [r["kaynak_yol"] for r in rows]
    targets = [r["hedef_arsiv_yolu"] for r in rows]
    masters = [r["korunan_master"] for r in rows]
    excluded = load_excluded(args.excluded, sources)
    write_rollback(args.out / "rollback_522.sh", rows, args.remote)

    source_before = remote_index(args.remote, sources, work, "sources_before")
    target_before = remote_index(args.remote, targets, work, "targets_before")
    master_before = remote_index(args.remote, masters, work, "masters_before")
    excluded_before = remote_index(args.remote, excluded, work, "excluded_before")
    verify_masters(rows, master_before)
    pending, archived = classify(rows, source_before, target_before)
    print(f"ON KONTROL PASS: 522/522 | bekleyen {len(pending)} | zaten arsivde {len(archived)}")

    if not args.apply:
        print("DRY-RUN: tasima yapilmadi")
        return 0
    if args.confirm != "CANLI":
        fail("canli tasima icin --confirm CANLI gerekli")

    progress = args.out / "progress.csv"
    with progress.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["kaynak_yol", "hedef_arsiv_yolu", "sonuc"])
        for row in archived:
            writer.writerow([row["kaynak_yol"], row["hedef_arsiv_yolu"], "ALREADY_ARCHIVED"])
        fh.flush()
        os.fsync(fh.fileno())
        for number, row in enumerate(pending, 1):
            command(
                "rclone", "moveto", f"{args.remote}:{row['kaynak_yol']}",
                f"{args.remote}:{row['hedef_arsiv_yolu']}",
                "--retries", "5", "--low-level-retries", "10",
            )
            writer.writerow([row["kaynak_yol"], row["hedef_arsiv_yolu"], "MOVED"])
            fh.flush()
            os.fsync(fh.fileno())
            if number % 25 == 0 or number == len(pending):
                print(f"TASINDI: {number}/{len(pending)}")

    source_after = remote_index(args.remote, sources, work, "sources_after")
    target_after = remote_index(args.remote, targets, work, "targets_after")
    master_after = remote_index(args.remote, masters, work, "masters_after")
    excluded_after = remote_index(args.remote, excluded, work, "excluded_after")
    if source_after:
        fail(f"tasima sonrasi kaynakta {len(source_after)} dosya kaldi")
    verify_masters(rows, master_after)
    if excluded_before != excluded_after:
        fail("dislanan yollarin Drive durumu degisti")
    pending_after, archived_after = classify(rows, source_after, target_after)
    if pending_after or len(archived_after) != SAFE_ROWS:
        fail("son dogrulama 522/522 degil")

    statuses = {r["kaynak_yol"]: "ARCHIVED_VERIFIED" for r in rows}
    write_result(args.out / "result.csv", rows, statuses)
    summary = {
        "target": SAFE_ROWS,
        "moved_this_run": len(pending),
        "already_archived": len(archived),
        "verified_in_archive": len(archived_after),
        "groups": GROUPS,
        "bytes": SAFE_BYTES,
        "original_plan_rows_rejected_as_masters": MASTER_ROWS,
        "masters_verified_before_after": len(set(masters)),
        "excluded_paths_changed": 0,
        "operation": "move_only_no_delete",
        "archive_root": ARCHIVE_ROOT,
        "original_plan_sha256": plan_sha,
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("TAMAMLANDI: 522/522 arsivde; 200 master yerinde; silme yapilmadi")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
