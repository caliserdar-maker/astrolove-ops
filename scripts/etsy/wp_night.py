#!/usr/bin/env python3
"""
GECE ZINCIRI (ADIM 2) uretim surucusu: 78 cift icin asama asama uretim,
STATE CSV + resume + ETA sayaci. Etsy'ye DOKUNMAZ (yazma asamasi e ayri
scripttedir); bu script yalniz Drive'a yazar.

Asamalar:
  a  wallpaper : 16 dosya/cift (wp_build_pair) -> FINAL_V2/<PAIR>/
  b  galeri    : 6 mockup/cift (wp_mockup_render) -> MOCKUP_V2/<PAIR>/
  d  zip       : 4 ZIP/cift (wp_zip) -> DELIVERY/<PAIR>/
Her cift icin: girdiler rclone ile cekilir, uretilir, QC kosar, cikti
Drive'a yazilir, yerel kopya silinir. QC FAIL -> o cift STATE'e FAIL yazilir
ve script sonunda hata koduyla biter (digerleri islenmeye devam eder).

STATE CSV (Drive, --state): pair,stage,status,ts_utc,detail
Resume: STATE'te PASS olan (pair, stage) atlanir (--force ile yeniden).
ETA: islenen/toplam, gecen, kalan, yuzde -- her ciftten sonra.

Kullanim:
  wp_night.py --stage a --pairs-file pairs.txt --shard 0 --shards 6 \
      --state _work/STATE.csv --state-remote gdrive:ASTROLOVE/TEMP/WP_NIGHT_STATE.csv \
      --drive gdrive:ASTROLOVE --work _work
"""
import argparse
import csv
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import EDITIONS, SCENES, log  # noqa: E402

DEVICES4 = ["Phone", "Tablet", "Desktop", "Watch"]
STAGES = ("a", "b", "d")   # asama c (video) 4 Eyl 2026 kaldirildi: 78 ilan VIDEOSUZ yayinlanacak


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rclone(*args, check=True):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {' '.join(args[:3])} -> {r.returncode}: {r.stderr[:300]}")
    return r


def read_state(path):
    done = {}
    p = Path(path)
    if not p.exists():
        return done
    with open(p, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) >= 3 and row[0] != "pair":
                done[(row[0], row[1])] = row[2]
    return done


def append_state(path, remote, pair, stage, status, detail):
    p = Path(path)
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["pair", "stage", "status", "ts_utc", "detail"])
        w.writerow([pair, stage, status, utc(), detail])
    if remote:
        rclone("copyto", str(p), remote, check=False)


def run(cmd, cwd=None):
    """Alt script kosar; ciktisi loga akar. Donus: (returncode, son satirlar)."""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-12:])
    print(tail, flush=True)
    return r.returncode, tail


def stage_a(pair, drive, work, args):
    """16 wallpaper: plakalar + medyan + ciftin 4 posteri -> FINAL_V2/<PAIR>/."""
    up = pair.upper()
    wp_out = work / "out" / up
    posters = work / "posters"
    posters.mkdir(parents=True, exist_ok=True)
    for ed in EDITIONS:
        rclone("copyto", f"{drive}/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/{ed.upper()}/3X4/WA_POSTER_{up}_{ed.upper()}_3X4.jpg",
               str(posters / f"WA_POSTER_{up}_{ed.upper()}_3X4.jpg"))
    rc, tail = run([sys.executable, str(Path(__file__).parent / "wp_build_pair.py"), "build",
                    "--pair", pair, "--plates", str(work / "plates"), "--posters", str(posters),
                    "--medians", str(work / "plates"), "--out", str(wp_out),
                    "--crops", args.crops])
    ok = rc == 0
    n = len(list(wp_out.glob("AstroLove_*.jpg"))) if wp_out.exists() else 0
    if ok and n == 16:
        rclone("copy", str(wp_out), f"{drive}/{args.wp_dir}/{up}", "--include", "AstroLove_*.jpg",
               "--include", "CONTACT_*.jpg", "--include", "build_*.json")
        if (wp_out / "qc").exists():
            rclone("copy", str(wp_out / "qc"), f"{drive}/{args.wp_dir}/{up}/qc", "--include", "CROP_*.png")
    shutil.rmtree(posters, ignore_errors=True)
    return (ok and n == 16), f"{n}/16 dosya" + ("" if ok else " QC FAIL: " + tail.splitlines()[-1][:120] if tail else "")


def stage_b(pair, drive, work, args):
    """6 galeri mockup'i -> MOCKUP_V2/<PAIR>/ (wp_mockup_render QC'si kapidir)."""
    up = pair.upper()
    wp_in = work / "wp" / up
    wp_in.mkdir(parents=True, exist_ok=True)
    rclone("copy", f"{drive}/{args.wp_dir}/{up}", str(wp_in), "--include", "AstroLove_*.jpg")
    out = work / "mock" / up
    rc, tail = run([sys.executable, str(Path(__file__).parent / "wp_mockup_render.py"),
                    "--calib", str(work / "calib"), "--masters", str(work / "masters"),
                    "--pilot", str(work / "pilot"), "--wallpapers", str(wp_in),
                    "--pair", pair, "--out", str(out)])
    n = len(list(out.glob("WA_MOCKUP_V2_*.jpg"))) if out.exists() else 0
    ok = rc == 0 and n == 6
    if ok:
        rclone("copy", str(out), f"{drive}/{args.mock_dir}/{up}", "--include", "WA_MOCKUP_V2_*.jpg",
               "--include", "qc.json", "--include", "report.md")
    shutil.rmtree(wp_in, ignore_errors=True)
    return ok, f"{n}/6 gorsel"


def stage_d(pair, drive, work, args):
    """4 teslim ZIP -> DELIVERY/<PAIR>/."""
    up = pair.upper()
    wp_in = work / "wp" / up
    wp_in.mkdir(parents=True, exist_ok=True)
    rclone("copy", f"{drive}/{args.wp_dir}/{up}", str(wp_in), "--include", "AstroLove_*.jpg")
    out = work / "zip" / up
    rc, tail = run([sys.executable, str(Path(__file__).parent / "wp_zip.py"),
                    "--pair", pair, "--wallpapers", str(wp_in), "--license", str(work / "LICENSE.txt"),
                    "--out", str(out)])
    n = len(list(out.glob("*.zip"))) if out.exists() else 0
    ok = rc == 0 and n == 4
    if ok:
        rclone("copy", str(out), f"{drive}/{args.zip_dir}/{up}", "--include", "*.zip", "--include", "zip_*.json")
    shutil.rmtree(wp_in, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    return ok, f"{n}/4 ZIP"


HANDLERS = dict(a=stage_a, b=stage_b, d=stage_d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--state", required=True)
    ap.add_argument("--state-remote", default="")
    ap.add_argument("--drive", default="gdrive:ASTROLOVE")
    ap.add_argument("--work", default="_work")
    ap.add_argument("--wp-dir", default="WALLPAPER/FINAL_V2")
    ap.add_argument("--mock-dir", default="WALLPAPER/MOCKUP_V2")
    ap.add_argument("--zip-dir", default="WALLPAPER/DELIVERY")
    ap.add_argument("--crops", default="Deep_Black_Tablet,Champagne_Ivory_Phone")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    work = Path(a.work)
    pairs = [p.strip() for p in Path(a.pairs_file).read_text().split() if p.strip()]
    mine = [p for i, p in enumerate(pairs) if i % a.shards == a.shard]
    if a.limit:
        mine = mine[:a.limit]
    done = read_state(a.state)
    todo = [p for p in mine if a.force or done.get((p, a.stage)) != "PASS"]
    log(f"asama {a.stage} | parca {a.shard + 1}/{a.shards} | {len(mine)} cift, {len(todo)} islenecek "
        f"({len(mine) - len(todo)} STATE'te PASS)")
    t0 = time.time()
    fails = []
    for i, pair in enumerate(todo):
        log(f"[{i + 1}/{len(todo)}] {pair}")
        try:
            ok, detail = HANDLERS[a.stage](pair, a.drive, work, a)
        except SystemExit as e:
            ok, detail = False, str(e)[:160]
        append_state(a.state, a.state_remote, pair, a.stage, "PASS" if ok else "FAIL", detail)
        if not ok:
            fails.append(pair)
        el = time.time() - t0
        rem = el / (i + 1) * (len(todo) - i - 1)
        log(f"  {pair}: {'PASS' if ok else 'FAIL'} ({detail}) | {i + 1}/{len(todo)} gecen {el / 60:.1f} dk "
            f"kalan {rem / 60:.1f} dk %{100 * (i + 1) / len(todo):.0f}")
    log(f"SONUC asama {a.stage} parca {a.shard}: {len(todo) - len(fails)}/{len(todo)} PASS"
        + (f" | FAIL: {','.join(fails)}" if fails else ""))
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## gece asama {a.stage} parca {a.shard + 1}/{a.shards}: "
                     f"{len(todo) - len(fails)}/{len(todo)} PASS\n\n" + (f"FAIL: {', '.join(fails)}\n" if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
