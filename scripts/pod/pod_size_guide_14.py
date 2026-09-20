#!/usr/bin/env python3
"""Size Guide karti 14 boy (5x7 eklenmis) - onayli pod_gallery_sample.py'yi import eder,
tasarimi/fontu/duzeni degistirmez; yalniz SIZES listesine 5x7 (13x18 cm) ve "5:7" grubu eklenir.

Cift x edisyon basina 08_SIZES karti yeniden cizilir; QC: 3000x2250, palet sapmasi <= 16,
grup bosluklari esit (|bosluk - hedef| <= 2.5 px, grup sayisi kadar + 2 bosluk).
Cikti: <out>/<PAIR>/<ED>/08_SIZES_<PAIR>_<ED>.jpg -> Drive TEMP/POD_SIZE_GUIDE_14/...
ETSY'YE YUKLEME YOK.
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import pod_gallery_sample as G  # noqa: E402

YENI = ("5x7", 5, 7, 13, 18, "5:7")
DURUM_SUT = ["pair", "status", "cards", "fail", "secs", "ts_utc"]
CSV_SUT = ["pair", "edition", "dosya", "boyut", "palet_sapma", "bosluk_sapma", "durum", "neden"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def yamali():
    """14 boy: 5x7 SIZES'a, '5:7' grubu GROUP_ORDER sonuna (en kucuk grup)."""
    if YENI not in G.SIZES:
        G.SIZES.append(YENI)
    if "5:7" not in G.GROUP_ORDER:
        G.GROUP_ORDER.append("5:7")
    G.GROUP_TITLE["5:7"] = "5:7"


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def bosluklar(kart):
    """sizes_gaps'in grup sayisindan bagimsiz surumu -> (bosluk listesi, hedef)."""
    rgb = np.array(Image.open(kart).convert("RGB")).astype(int)
    y = G.SG_BASE_Y - 30
    bar, rule = rgb[2120, 1500], rgb[418, 1500]
    _, kutular, hedef = G.sg_layout()
    rrow = np.abs(rgb[y] - rule).sum(1) < 60
    lim = int(kutular[0][0]) - 20
    rx = int(np.where(rrow[:lim])[0].min()) if rrow[:lim].any() else None
    kenarlar = []
    for bx0, bx1 in kutular:
        a0, a1 = max(0, int(bx0) - 30), min(G.W, int(bx1) + 30)
        seg = np.abs(rgb[y, a0:a1] - bar).sum(1) < 60
        xs = np.where(seg)[0]
        if len(xs):
            kenarlar.append((int(xs.min() + a0), int(xs.max() + a0)))
    if rx is None or len(kenarlar) != len(kutular):
        return [], hedef
    g = [rx, kenarlar[0][0] - rx]
    g += [kenarlar[i + 1][0] - kenarlar[i][1] for i in range(len(kenarlar) - 1)]
    g.append(G.W - kenarlar[-1][1])
    return g, hedef


def qc(kart, pal):
    errs = []
    im = Image.open(kart)
    if im.size != (G.W, G.H):
        errs.append(f"boyut {im.size}")
    mp = G.measure(kart)
    sapma = max(abs(mp[k][i] - pal[k][i]) for k in ("bg", "bar", "ink") for i in range(3))
    if sapma > 16:
        errs.append(f"palet sapmasi {sapma}")
    g, hedef = bosluklar(kart)
    b_sapma = max(abs(x - hedef) for x in g) if g else None
    if not g:
        errs.append("bosluk olculemedi")
    elif b_sapma > 2.5:
        errs.append(f"bosluk sapmasi {b_sapma:.1f} (hedef {hedef:.1f})")
    return errs, sapma, (round(b_sapma, 1) if b_sapma is not None else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--src", default="src")
    ap.add_argument("--out", default="out")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="")
    ap.add_argument("--rclone-out", default="")
    ap.add_argument("--ornek-cift", default="")
    ap.add_argument("--ornek-drv", default="gdrive:ASTROLOVE/TEMP/POD_5X7")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    yamali()
    log(f"boy sayisi {len(G.SIZES)} | gruplar {G.GROUP_ORDER}")
    F = G.Fonts(a.fonts)
    ciftler = [l.strip().upper() for l in pathlib.Path(a.pairs_file).read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.startswith("#")]
    ciftler = sorted(dict.fromkeys(ciftler))
    benim = [p for i, p in enumerate(ciftler) if i % a.shards == a.shard]
    durum_yol = pathlib.Path(a.state)
    durum = {}
    if durum_yol.exists():
        for r in csv.DictReader(durum_yol.open(encoding="utf-8")):
            durum[r["pair"]] = r
    todo = [p for p in benim if a.force or durum.get(p, {}).get("status") != "PASS"]
    log(f"shard {a.shard}/{a.shards}: {len(benim)} cift, {len(todo)} islenecek")
    csv_yol = pathlib.Path(a.csv or (durum_yol.parent / f"SIZE_GUIDE_14_shard{a.shard}.csv"))
    if not csv_yol.exists():
        with csv_yol.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_SUT)

    t0 = time.time()
    for i, cift in enumerate(todo, start=1):
        tp = time.time()
        hatalar, satirlar, n = [], [], 0
        pair_txt = " • ".join(cift.split("_"))
        for ed in G.EDITIONS:
            kaynak = pathlib.Path(a.src) / ed / cift
            if a.rclone_src:
                kaynak.mkdir(parents=True, exist_ok=True)
                rclone("copy", f"{a.rclone_src}/{ed}/{cift}", str(kaynak),
                       "--include", "{05,10}_WA_*", "--transfers", "4", "-q", sert=False)
            try:
                pal = G.palette(G.find_src(kaynak, "10"))
                c05 = Image.open(G.find_src(kaynak, "05")).convert("RGB")
            except (FileNotFoundError, OSError) as e:
                hatalar.append(f"{ed}: kaynak {type(e).__name__}")
                continue
            x, y, w, h = G.POSTER_BOX
            poster = c05.crop((x, y, x + w, y + h))
            cikti = pathlib.Path(a.out) / cift / ed / f"08_SIZES_{cift}_{ed}.jpg"
            cikti.parent.mkdir(parents=True, exist_ok=True)
            G.save_jpg(G.card_sizes(pal, F, poster, pair_txt), cikti, 95)
            errs, p_sapma, b_sapma = qc(cikti, pal)
            satirlar.append({"pair": cift, "edition": ed, "dosya": str(cikti.relative_to(a.out)),
                             "boyut": "x".join(map(str, Image.open(cikti).size)),
                             "palet_sapma": p_sapma, "bosluk_sapma": b_sapma,
                             "durum": "PASS" if not errs else "FAIL", "neden": "; ".join(errs)[:160]})
            if errs:
                hatalar.append(f"{ed}: " + "; ".join(errs))
            if a.ornek_cift and cift == a.ornek_cift.upper() and ed == "MIDNIGHT_BLUE":
                ornek = pathlib.Path(a.out) / "SIZE_GUIDE_14_ORNEK.jpg"
                im = Image.open(cikti).convert("RGB")
                for genislik, kal in ((2000, 88), (1600, 84), (1400, 80), (1200, 76)):
                    im.resize((genislik, round(genislik * im.size[1] / im.size[0])),
                              Image.LANCZOS).save(ornek, "JPEG", quality=kal, optimize=True)
                    if ornek.stat().st_size <= 500_000:
                        break
                rclone("copyto", str(ornek), f"{a.ornek_drv}/SIZE_GUIDE_14_ORNEK.jpg")
                log(f"SIZE_GUIDE_14_ORNEK.jpg {ornek.stat().st_size / 1024:.0f} KB")
            if a.rclone_out:
                rclone("copyto", str(cikti), f"{a.rclone_out}/{cift}/{ed}/{cikti.name}")
                cikti.unlink(missing_ok=True)
            if a.rclone_src:
                subprocess.run(["rm", "-rf", str(kaynak)], check=False)
            n += 1
        with csv_yol.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_SUT, extrasaction="ignore")
            for s in satirlar:
                w.writerow(s)
        ok = n == len(G.EDITIONS) and not hatalar
        durum[cift] = {"pair": cift, "status": "PASS" if ok else "FAIL", "cards": n,
                       "fail": "; ".join(hatalar)[:300], "secs": round(time.time() - tp, 1),
                       "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with durum_yol.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=DURUM_SUT)
            w.writeheader()
            for k in sorted(durum):
                w.writerow({c: durum[k].get(c, "") for c in DURUM_SUT})
        gec = time.time() - t0
        log(f"{i}/{len(todo)} (%{100 * i / len(todo):.1f}) {cift} {'PASS' if ok else 'FAIL'} "
            f"{n}/5 kart {('; '.join(hatalar))[:60]} | gecen {sure(gec)} "
            f"| kalan ~{sure(gec / i * (len(todo) - i))}")
    if a.rclone_out:
        rclone("copyto", str(csv_yol), f"gdrive:ASTROLOVE/TEMP/POD_SIZE_GUIDE_14/parca/{csv_yol.name}")
    print(json.dumps({"shard": a.shard,
                      "pass": sum(1 for p in todo if durum.get(p, {}).get("status") == "PASS"),
                      "fail": sum(1 for p in todo if durum.get(p, {}).get("status") == "FAIL")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
