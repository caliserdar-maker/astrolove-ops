#!/usr/bin/env python3
"""
SAAT %80 URETIM - B asamasi (5 Eyl 2026, Mo). Parca (shard) basina:
  her cift icin
    1) FINAL_V2/<UP>/ 16 wallpaper indirilir (saat dosyalari %80 SAAT ile
       degistirilmis olmali; hazirlik isi yapar, burada dogrulanir: Watch jpg'nin
       md5'i TEMP/WATCH_CANVA/<UP>/ ile ayni),
    2) 4 teslim ZIP (Phone/Tablet/Desktop/Watch + LICENSE.txt; PDF YOK) ->
       WALLPAPER/DELIVERY_SAAT80/<UP>/ (wp_zip.build_pair, qc_zip),
    3) eski SET07 -> WALLPAPER/MOCKUP_V2_YEDEK_SAAT100/<UP>/, yeni SET07 render
       (yalniz SET07) -> WALLPAPER/MOCKUP_V2/<UP>/ (diger 5 sahne dokunulmaz).
  ETA sayaci, cift basina CSV satiri. Herhangi bir cift FAIL ise cikis kodu 2.
"""
import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import EDITIONS, log  # noqa: E402
from wp_zip import MAX_BYTES, build_pair  # noqa: E402

ZIP_DIR = "WALLPAPER/DELIVERY_SAAT80"
MOCK_DIR = "WALLPAPER/MOCKUP_V2"
MOCK_YEDEK = "WALLPAPER/MOCKUP_V2_YEDEK_SAAT100"
WATCH_DIR = "TEMP/WATCH_CANVA"


def rclone(*args, check=True):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"rclone {' '.join(args[:2])}: rc {r.returncode} {r.stderr.strip()[-400:]}")
    return r


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def eta(i, n, t0):
    g = time.time() - t0
    k = g / i * (n - i) if i else 0
    return f"[{i}/{n} {100 * i / n:.0f}% gecen {g / 60:.1f} dk kalan {k / 60:.1f} dk]"


def bir_cift(pair, a, work, lic):
    up = pair.upper()
    wp = work / "wp" / up
    shutil.rmtree(wp, ignore_errors=True); wp.mkdir(parents=True)
    rclone("copy", f"{a.drive}/{a.wp_dir}/{up}", str(wp), "--include", "AstroLove_*.jpg")
    n_wp = len(list(wp.glob("AstroLove_*.jpg")))
    if n_wp != 16:
        return dict(pair=pair, durum=f"FAIL wp {n_wp}/16")
    # saat dogrulama: FINAL_V2 saati == TEMP/WATCH_CANVA (%80) saati
    ref = work / "watchref" / up
    shutil.rmtree(ref, ignore_errors=True); ref.mkdir(parents=True)
    rclone("copy", f"{a.drive}/{WATCH_DIR}/{up}", str(ref), "--include", "AstroLove_*_Watch.jpg")
    for ed in EDITIONS:
        n = f"AstroLove_{pair}_{ed}_Watch.jpg"
        if not (ref / n).exists() or md5(ref / n) != md5(wp / n):
            return dict(pair=pair, durum=f"FAIL saat {ed} (FINAL_V2 != WATCH_CANVA)")
    # ZIP (PDF yok)
    zout = work / "zip" / up
    shutil.rmtree(zout, ignore_errors=True)
    rows = build_pair(pair, wp, lic, zout)
    zip_ok = all(r["ok"] for r in rows.values())
    sizes = {ed: rows[ed]["size_bytes"] for ed in EDITIONS}
    if not zip_ok:
        return dict(pair=pair, durum="FAIL zip " + "; ".join(f"{e}:{r['issues']}" for e, r in rows.items() if not r["ok"]), **{f"zip_{e}": sizes[e] for e in EDITIONS})
    rclone("copy", str(zout), f"{a.drive}/{ZIP_DIR}/{up}", "--include", "*.zip")
    chk = rclone("check", str(zout), f"{a.drive}/{ZIP_DIR}/{up}", "--one-way", "--include", "*.zip", check=False)
    if chk.returncode != 0:
        return dict(pair=pair, durum="FAIL zip yukleme", **{f"zip_{e}": sizes[e] for e in EDITIONS})
    # SET07: eski yedek, yeni render
    s7 = f"WA_MOCKUP_V2_SET07_{pair}_FINAL.jpg"
    rclone("copyto", f"{a.drive}/{MOCK_DIR}/{up}/{s7}", f"{a.drive}/{MOCK_YEDEK}/{up}/{s7}", check=False)
    mout = work / "mock" / up
    shutil.rmtree(mout, ignore_errors=True); mout.mkdir(parents=True)
    cmd = [sys.executable, str(Path(__file__).parent / "wp_mockup_render.py"), "--calib", a.calib, "--masters", a.masters,
           "--pilot", a.pilot, "--wallpapers", str(wp), "--pair", pair, "--scenes", "SET07", "--out", str(mout)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not (mout / s7).exists():
        log(r.stdout[-800:]); log(r.stderr[-800:])
        return dict(pair=pair, durum="FAIL set07 render", **{f"zip_{e}": sizes[e] for e in EDITIONS})
    rclone("copyto", str(mout / s7), f"{a.drive}/{MOCK_DIR}/{up}/{s7}")
    for d in (wp, ref, zout, mout):
        shutil.rmtree(d, ignore_errors=True)
    return dict(pair=pair, durum="PASS", set07=s7, **{f"zip_{e}": sizes[e] for e in EDITIONS})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--drive", default="gdrive:ASTROLOVE")
    ap.add_argument("--wp-dir", default="WALLPAPER/FINAL_V2")
    ap.add_argument("--license", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--work", default="_work")
    ap.add_argument("--report", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    work = Path(a.work)
    pairs = [r[0].strip() for r in csv.reader(open(a.pairs_file, encoding="utf-8")) if r and r[0].strip() and r[0] != "pair"]
    mine = [p for i, p in enumerate(pairs) if i % a.shards == a.shard]
    if a.limit:
        mine = mine[:a.limit]
    log(f"parca {a.shard}/{a.shards}: {len(mine)} cift")
    t0 = time.time(); out = []
    for i, pair in enumerate(mine):
        try:
            row = bir_cift(pair, a, work, a.license)
        except Exception as e:  # noqa: BLE001
            row = dict(pair=pair, durum=f"FAIL hata {str(e)[:200]}")
        out.append(row)
        mx = max((row.get(f"zip_{e}", 0) for e in EDITIONS), default=0)
        log(f"{eta(i + 1, len(mine), t0)} {pair:<24} {row['durum']}  en buyuk ZIP {mx / 1e6:.2f} MB")
    cols = ["pair", "durum", "set07"] + [f"zip_{e}" for e in EDITIONS]
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    with open(a.report, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    npass = sum(r["durum"] == "PASS" for r in out)
    mx = max((r.get(f"zip_{e}", 0) for r in out for e in EDITIONS), default=0)
    log(f"SONUC parca {a.shard}: {npass}/{len(out)} PASS, en buyuk ZIP {mx / 1e6:.2f} MB ({'<20MB' if mx < MAX_BYTES else 'ASIYOR'})")
    if npass != len(out):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
