#!/usr/bin/env python3
"""5x7 (GLOBAL-HPR-5x7, 13x18 cm) baski dosyalari: 78 cift x 5 edisyon = 390 JPEG.

Kaynak: ORIGINAL_HIGH_RES/<ED>/A_SERIES/<PAIR>.jpg (ISO ustasi, 10962x15503).
Yontem: YALNIZ dikey merkez kirpma (usta cozunurlugu korunur, yeniden boyutlandirma yok);
hedef oran Prodigi 5x7 baski alanindan (1535x2125 -> 0.72235). Oran farki toleransi bu
boy icin 0.025 (diger boylar pod_print_build.py'de 0.01 kalir).
Kontrol: kirpilan ust/alt bantlarda zemin disi piksel yoksa GECTI (bant medyani + sapma).
Cikti: <out>/<PAIR>/<ED>/5x7.jpg -> Drive TEMP/POD_PRINT/<PAIR>/<ED>/5x7.jpg, satir satir CSV.
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

Image.MAX_IMAGE_PIXELS = None
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
RATIO_TOL_5X7 = 0.025
BOY = "5x7"
SAPMA = 12          # bant medyanindan kanal sapmasi; ustu "zemin disi" sayilir
CSV_SUT = ["pair", "edition", "dosya", "usta_px", "kirp_px", "kirpma_px", "ust_sapma",
           "alt_sapma", "ust_ink_px", "alt_ink_px", "bayt", "sn", "durum", "neden"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]} {a[1] if len(a) > 1 else ''}: {r.stderr.strip()[-200:]}")
    return r


def hedef_oran(sizes_json):
    """Prodigi 5x7 baski alani -> (w_px, h_px, oran)."""
    d = json.loads(pathlib.Path(sizes_json).read_text(encoding="utf-8"))
    v = d.get(BOY) or d.get("5X7")
    if not v:
        raise SystemExit(f"HATA: {sizes_json} icinde {BOY} yok")
    w, h = int(v["w"]), int(v["h"])
    return w, h, w / h


def bant_kontrol(arr):
    """(max kanal sapmasi, SAPMA ustu piksel sayisi) — bant medyanina gore."""
    if arr.size == 0:
        return 0, 0
    med = np.median(arr.reshape(-1, arr.shape[-1]), axis=0)
    fark = np.abs(arr.astype(np.int16) - med.astype(np.int16)).max(axis=2)
    return int(fark.max()), int((fark > SAPMA).sum())


def uret(usta_yol, cikti_yol, oran):
    """Kirp + kaydet. Donus: satir sozlugu."""
    t0 = time.time()
    im = Image.open(usta_yol)
    im.draft(None, None)
    im = im.convert("RGB")
    sw, sh = im.size
    fark = abs((sw / sh) / oran - 1)
    if fark > RATIO_TOL_5X7:
        raise ValueError(f"oran {sw}x{sh} ({sw / sh:.4f}) hedef {oran:.4f} fark %{fark * 100:.2f}")
    nh = round(sw / oran)
    if nh > sh:
        raise ValueError(f"hedef yukseklik {nh} > usta {sh}")
    y0 = (sh - nh) // 2
    a = np.asarray(im)
    ust_s, ust_i = bant_kontrol(a[:y0])
    alt_s, alt_i = bant_kontrol(a[y0 + nh:])
    kirp = im.crop((0, y0, sw, y0 + nh))
    dpi = round(kirp.size[0] / (1535 / 300.0))
    cikti_yol.parent.mkdir(parents=True, exist_ok=True)
    kirp.save(cikti_yol, "JPEG", quality=95, subsampling=0, dpi=(dpi, dpi), optimize=True)
    return {"usta_px": f"{sw}x{sh}", "kirp_px": f"{kirp.size[0]}x{kirp.size[1]}",
            "kirpma_px": sh - nh, "ust_sapma": ust_s, "alt_sapma": alt_s,
            "ust_ink_px": ust_i, "alt_ink_px": alt_i,
            "bayt": cikti_yol.stat().st_size, "sn": round(time.time() - t0, 1),
            "durum": "GECTI" if (ust_i == 0 and alt_i == 0) else "KONTROL", "neden": ""}


def onizleme(dosyalar, yol):
    """5 edisyon yan yana, gercek 5x7 orani, telefonda okunur, <= 1 MB."""
    from PIL import ImageDraw
    pw = 560
    paneller = []
    for ed, p in dosyalar:
        im = Image.open(p)
        im.draft("RGB", (pw * 2, pw * 2))
        im = im.convert("RGB")
        ph = round(pw * im.size[1] / im.size[0])
        paneller.append((ed, im.resize((pw, ph), Image.LANCZOS)))
    bosluk, kenar, alt = 36, 40, 60
    gen = kenar * 2 + len(paneller) * pw + bosluk * (len(paneller) - 1)
    yuk = kenar * 2 + max(p.size[1] for _, p in paneller) + alt
    tuval = Image.new("RGB", (gen, yuk), (247, 246, 243))
    d = ImageDraw.Draw(tuval)
    x = kenar
    for ed, p in paneller:
        tuval.paste(p, (x, kenar))
        d.rectangle([x, kenar, x + p.size[0] - 1, kenar + p.size[1] - 1], outline=(140, 140, 140))
        d.text((x + p.size[0] // 2, kenar + p.size[1] + 18), ed.replace("_", " "),
               fill=(25, 25, 25), anchor="ma")
        x += pw + bosluk
    d.text((kenar, yuk - 26), "5x7 in / 13x18 cm - ISO ustasindan dikey kirpma (164/164 px)",
           fill=(70, 70, 70), anchor="lm")
    for q in (88, 82, 74, 66):
        tuval.save(yol, "JPEG", quality=q, optimize=True)
        if yol.stat().st_size <= 1_000_000:
            break
    log(f"ONIZLEME_5X7.jpg {tuval.size[0]}x{tuval.size[1]} {yol.stat().st_size / 1024:.0f} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--sizes-json", required=True)
    ap.add_argument("--src", default="src")
    ap.add_argument("--out", default="out")
    ap.add_argument("--state", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="")
    ap.add_argument("--rclone-out", default="")
    ap.add_argument("--onizleme-cift", default="")
    ap.add_argument("--onizleme-drv", default="gdrive:ASTROLOVE/TEMP/POD_5X7")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    w, h, oran = hedef_oran(a.sizes_json)
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
    log(f"shard {a.shard}/{a.shards}: {len(benim)} cift, {len(todo)} islenecek | hedef oran "
        f"{oran:.5f} ({w}x{h}) | tolerans {RATIO_TOL_5X7}")

    csv_yol = pathlib.Path(a.csv or (durum_yol.parent / f"URETIM_5X7_shard{a.shard}.csv"))
    if not csv_yol.exists():
        with csv_yol.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_SUT)
    onizleme_dosyalari = []
    t0, n_ok, n_fail = time.time(), 0, 0
    for i, cift in enumerate(todo, start=1):
        tp = time.time()
        hatalar, satirlar, uretilen = [], [], 0
        for ed in EDITIONS:
            usta = pathlib.Path(a.src) / ed / "A_SERIES" / f"{cift}.jpg"
            if a.rclone_src:
                usta.parent.mkdir(parents=True, exist_ok=True)
                r = rclone("copyto", f"{a.rclone_src}/{ed}/A_SERIES/{cift}.jpg", str(usta), sert=False)
                if r.returncode != 0 or not usta.exists():
                    hatalar.append(f"{ed}: usta inmedi")
                    continue
            if not usta.exists():
                hatalar.append(f"{ed}: usta yok")
                continue
            cikti = pathlib.Path(a.out) / cift / ed / f"{BOY}.jpg"
            try:
                s = uret(usta, cikti, oran)
            except Exception as e:  # noqa: BLE001
                hatalar.append(f"{ed}: {type(e).__name__}: {e}")
                usta.unlink(missing_ok=True)
                continue
            s.update({"pair": cift, "edition": ed, "dosya": f"{cift}/{ed}/{BOY}.jpg"})
            if s["durum"] != "GECTI":
                hatalar.append(f"{ed}: bant kontrolu ust {s['ust_ink_px']} alt {s['alt_ink_px']} px")
            satirlar.append(s)
            if a.onizleme_cift and cift == a.onizleme_cift.upper():
                onizleme_dosyalari.append((ed, cikti))
            if a.rclone_out and not (a.onizleme_cift and cift == a.onizleme_cift.upper()):
                rclone("copyto", str(cikti), f"{a.rclone_out}/{cift}/{ed}/{BOY}.jpg")
                cikti.unlink(missing_ok=True)
            usta.unlink(missing_ok=True)
            uretilen += 1
        with csv_yol.open("a", newline="", encoding="utf-8") as fh:
            wcsv = csv.DictWriter(fh, fieldnames=CSV_SUT, extrasaction="ignore")
            for s in satirlar:
                wcsv.writerow(s)
        ok = uretilen == len(EDITIONS) and not hatalar
        durum[cift] = {"pair": cift, "status": "PASS" if ok else "FAIL", "files": uretilen,
                       "fail": "; ".join(hatalar)[:300], "secs": round(time.time() - tp, 1),
                       "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with durum_yol.open("w", newline="", encoding="utf-8") as fh:
            wcsv = csv.DictWriter(fh, fieldnames=["pair", "status", "files", "fail", "secs", "ts_utc"])
            wcsv.writeheader()
            for k in sorted(durum):
                wcsv.writerow({c: durum[k].get(c, "") for c in
                               ["pair", "status", "files", "fail", "secs", "ts_utc"]})
        n_ok += ok
        n_fail += (not ok)
        gec = time.time() - t0
        log(f"{i}/{len(todo)} (%{100 * i / len(todo):.1f}) {cift} {'PASS' if ok else 'FAIL'} "
            f"{uretilen}/5 dosya {('; '.join(hatalar))[:60]} | gecen {sure(gec)} "
            f"| kalan ~{sure(gec / i * (len(todo) - i))}")

    if a.onizleme_cift and onizleme_dosyalari:
        yol = pathlib.Path(a.out) / "ONIZLEME_5X7.jpg"
        onizleme(sorted(onizleme_dosyalari, key=lambda t: EDITIONS.index(t[0])), yol)
        rclone("copyto", str(yol), f"{a.onizleme_drv}/ONIZLEME_5X7.jpg")
        for ed, p in onizleme_dosyalari:
            if a.rclone_out:
                rclone("copyto", str(p), f"{a.rclone_out}/{a.onizleme_cift.upper()}/{ed}/{BOY}.jpg")
                p.unlink(missing_ok=True)
    if a.rclone_out:
        rclone("copyto", str(csv_yol), f"gdrive:ASTROLOVE/TEMP/POD_5X7/parca/{csv_yol.name}")
    print(json.dumps({"shard": a.shard, "pass": n_ok, "fail": n_fail,
                      "dosya_csv": str(csv_yol)}, ensure_ascii=False))
    return 0 if n_fail == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
