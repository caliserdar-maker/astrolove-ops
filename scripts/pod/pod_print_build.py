#!/usr/bin/env python3
"""
POD baski dosyalari: 78 cift x 5 edisyon x 13 boyut = 5.070 JPEG (6 Eyl 2026).

Kaynak: WALL_ART/POSTERS/ORIGINAL_HIGH_RES/<ED>/<RATIO>/<PAIR>.jpg
        RATIO: 4X5 (8x10,16x20) | 3X4 (12x16,18x24,30x40) | 2X3 (12x18,16x24,20x30,24x36) | 11X14 | A_SERIES (A4,A3,A2)
Hedef: boyut basina Prodigi print-area pikseli (PRODIGI_HPR_PRINT_AREAS.json; inc boyutlar = inc x 300,
       A serisi API degeri) -> merkez kirp (oran farki <= %1, aksi FAIL) -> LANCZOS -> JPEG q95, 300 dpi
       -> <out>/<PAIR>/<ED>/<SIZE>.jpg. QC: geri okuma, piksel TAM esit, dosya > 0.
STATE (cift basina, resume): pair,status,files,fail,secs,ts_utc. FAIL cift STATE'e yazilir, kosu surer.
rclone verilirse cift basina indir/yukle/sil (disk sinirli).

Kullanim: pod_print_build.py --pairs-file P --sizes-json S.json --src SRC --out OUT --state ST.csv
          [--shard i --shards n] [--rclone-src gdrive:.../ORIGINAL_HIGH_RES --rclone-out gdrive:.../TEMP/POD_PRINT] [--force]
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
RATIO_OF = {"8x10": "4X5", "16x20": "4X5", "12x16": "3X4", "18x24": "3X4", "30x40": "3X4",
            "12x18": "2X3", "16x24": "2X3", "20x30": "2X3", "24x36": "2X3", "11x14": "11X14",
            "A4": "A_SERIES", "A3": "A_SERIES", "A2": "A_SERIES"}
SIZES = list(RATIO_OF)
RATIO_TOL = 0.01
STATE_COLS = ["pair", "status", "files", "fail", "secs", "ts_utc"]


def log(m):
    print(m, flush=True)


def rclone(*args):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {args[0]} {args[1]}: rc={r.returncode} {r.stderr.strip()[-200:]}")


def fit(im, w, h):
    """Merkez kirp (hedef orana) + LANCZOS. Oran farki > %1 ise ValueError."""
    sw, sh = im.size
    if abs((sw / sh) / (w / h) - 1) > RATIO_TOL:
        raise ValueError(f"oran {sw}x{sh} ({sw / sh:.4f}) hedef {w}x{h} ({w / h:.4f})")
    if sw / sh > w / h:
        nw = round(sh * w / h); x0 = (sw - nw) // 2; im = im.crop((x0, 0, x0 + nw, sh))
    elif sw / sh < w / h:
        nh = round(sw * h / w); y0 = (sh - nh) // 2; im = im.crop((0, y0, sw, y0 + nh))
    if im.size == (w, h):
        return im
    return im.resize((w, h), Image.LANCZOS)


def build_pair(pair, sizes, src_root, out_root):
    errs, n = [], 0
    cache = {}
    for ed in EDITIONS:
        for sz in SIZES:
            ratio = RATIO_OF[sz]
            src = Path(src_root) / ed / ratio / f"{pair}.jpg"
            if not src.exists():
                errs.append(f"{ed}/{ratio}: kaynak yok"); continue
            w, h = sizes[sz]["w"], sizes[sz]["h"]
            out = Path(out_root) / pair / ed / f"{sz}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                key = (ed, ratio)
                if key not in cache:
                    im = Image.open(src); im.load()
                    cache = {key: im.convert("RGB")}          # edisyon+oran basina tek decode; bellek icin tek giris
                im = cache[key]
                fit(im, w, h).save(out, "JPEG", quality=95, subsampling=0, dpi=(300, 300), optimize=False)
                with Image.open(out) as chk:
                    if chk.size != (w, h) or out.stat().st_size == 0:
                        errs.append(f"{ed}/{sz}: QC {chk.size} != {w}x{h}"); continue
                n += 1
            except Exception as e:
                errs.append(f"{ed}/{sz}: {type(e).__name__} {str(e)[:120]}")
    cache.clear()
    return n, errs


def read_state(p):
    st = {}
    if Path(p).exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st[r["pair"]] = r
    return st


def write_state(p, st):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=STATE_COLS); w.writeheader()
        for k in sorted(st):
            w.writerow({c: st[k].get(c, "") for c in STATE_COLS})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--sizes-json", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="")
    ap.add_argument("--rclone-out", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    sizes = json.loads(Path(a.sizes_json).read_text())
    missing = [s for s in SIZES if s not in sizes]
    if missing:
        sys.exit(f"HATA: sizes json eksik: {missing}")
    pairs = sorted(dict.fromkeys(l.strip().upper() for l in Path(a.pairs_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")))
    mine = [p for i, p in enumerate(pairs) if i % a.shards == a.shard]
    st = read_state(a.state)
    todo = [p for p in mine if a.force or st.get(p, {}).get("status") != "PASS"]
    total = len(EDITIONS) * len(SIZES)
    log(f"shard {a.shard}/{a.shards}: {len(mine)} cift, {len(todo)} islenecek; hedefler: " + ", ".join(f"{s}={sizes[s]['w']}x{sizes[s]['h']}" for s in SIZES))
    t0 = time.time(); n_pass = n_fail = 0
    for i, pair in enumerate(todo, 1):
        tp = time.time()
        if a.rclone_src:
            for ed in EDITIONS:
                for ratio in sorted(set(RATIO_OF.values())):
                    d = Path(a.src) / ed / ratio; d.mkdir(parents=True, exist_ok=True)
                    try:
                        rclone("copyto", f"{a.rclone_src}/{ed}/{ratio}/{pair}.jpg", str(d / f"{pair}.jpg"), "-q")
                    except RuntimeError as e:
                        log(f"  {pair} {ed}/{ratio}: {e}")
        try:
            n, errs = build_pair(pair, sizes, a.src, a.out)
        except Exception as e:
            n, errs = 0, [f"istisna {type(e).__name__}: {str(e)[:200]}"]
        ok = not errs and n == total
        if n != total:
            errs.append(f"dosya {n}/{total}")
        if a.rclone_out and n:
            try:
                rclone("copy", str(Path(a.out) / pair), f"{a.rclone_out}/{pair}", "--transfers", "8", "-q")
                # geri sayim: uzak dosya sayisi = yerel
                r = subprocess.run(["rclone", "lsf", f"{a.rclone_out}/{pair}", "-R", "--files-only"], capture_output=True, text=True)
                remote_n = len([l for l in r.stdout.splitlines() if l.endswith(".jpg")])
                if remote_n < n:
                    ok = False; errs.append(f"uzak {remote_n}/{n}")
            except RuntimeError as e:
                ok = False; errs.append(str(e))
        secs = round(time.time() - tp, 1)
        st[pair] = dict(pair=pair, status="PASS" if ok else "FAIL", files=n, fail=" | ".join(errs)[:900], secs=secs,
                        ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        write_state(a.state, st)
        n_pass += ok; n_fail += (not ok)
        if a.rclone_src or a.rclone_out:
            for ed in EDITIONS:
                for ratio in set(RATIO_OF.values()):
                    (Path(a.src) / ed / ratio / f"{pair}.jpg").unlink(missing_ok=True)
            if a.rclone_out:
                shutil.rmtree(Path(a.out) / pair, ignore_errors=True)
        el = time.time() - t0
        log(f"[{i}/{len(todo)}] {pair:<24} {'PASS' if ok else 'FAIL'} {n}/{total} {secs}s | gecen {el:.0f}s kalan~{el / i * (len(todo) - i):.0f}s | {'; '.join(errs)[:160]}")
    log(f"shard {a.shard}: PASS {n_pass} FAIL {n_fail} sure {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
