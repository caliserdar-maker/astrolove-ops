#!/usr/bin/env python3
"""A1 (GLOBAL-HPR-A1, 59.4x84.1 cm) baski dosyalari: 78 cift x 5 edisyon = 390 JPEG.

A1 orani ISO ustasiyla ayni -> KIRPMA YOK, YENIDEN BOYUTLANDIRMA YOK: usta dosyasi
oldugu gibi <PAIR>/<ED>/A1.jpg olarak kopyalanir (Drive ici sunucu tarafli kopya).
Dogrulama: JPEG basligindan piksel olcusu okunur (indirme yok), Prodigi A1 baski
alani (7020x9930) ile kiyaslanir; oran farki ve DPI hesaplanir; kopya bayt bayt ayni mi
bakilir. Cikti: TEMP/POD_PRINT/<PAIR>/<ED>/A1.jpg + URETIM_A1.csv (TEMP/POD_5X7).
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys
import time

EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
BOY = "A1"
A1_IN = (23.3858, 33.1102)      # Prodigi urun olcusu (inc)
ORAN_TOL = 0.005                # ISO ustasi ile A1 baski alani orani farki esigi (%0.5)
CSV_SUT = ["pair", "edition", "dosya", "usta_px", "baski_alani_px", "oran_farki_yuzde",
           "dpi_kisa", "dpi_uzun", "dpi_yeterli", "bayt", "kopya_bayt", "sn", "durum", "neden"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a, sert=True, ikili=False):
    r = subprocess.run(["rclone", *a], capture_output=not ikili, text=not ikili,
                       stdout=subprocess.PIPE if ikili else None)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]}: {(r.stderr or '')[-200:]}")
    return r


def jpeg_olcu(uzak, bayt=262144):
    """JPEG basligindan (w, h) — dosyanin ilk N baytini okur, indirme yok."""
    r = subprocess.run(["rclone", "cat", "--count", str(bayt), uzak],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0 or len(r.stdout) < 4:
        return None
    d, i = r.stdout, 2
    while i + 9 < len(d):
        if d[i] != 0xFF:
            i += 1
            continue
        m = d[i + 1]
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7 or m == 0x01:
            i += 2
            continue
        uz = int.from_bytes(d[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = int.from_bytes(d[i + 5:i + 7], "big")
            w = int.from_bytes(d[i + 7:i + 9], "big")
            return w, h
        i += 2 + uz
    return None


def bayt_olcu(uzak):
    r = rclone("lsjson", uzak, sert=False)
    if r.returncode != 0:
        return None
    try:
        return int(json.loads(r.stdout)[0]["Size"])
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--sizes-json", required=True, help="PRODIGI_HPR_PRINT_AREAS.json (A1 gerekli)")
    ap.add_argument("--state", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", required=True)
    ap.add_argument("--rclone-out", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    alan = json.loads(pathlib.Path(a.sizes_json).read_text(encoding="utf-8")).get(BOY)
    if not alan:
        raise SystemExit(f"HATA: {a.sizes_json} icinde {BOY} yok")
    aw, ah = int(alan["w"]), int(alan["h"])
    hedef_oran = aw / ah
    ciftler = sorted({l.strip().upper() for l in pathlib.Path(a.pairs_file).read_text(encoding="utf-8").splitlines()
                      if l.strip() and not l.startswith("#")})
    benim = [p for i, p in enumerate(ciftler) if i % a.shards == a.shard]
    durum_yol = pathlib.Path(a.state)
    durum = {}
    if durum_yol.exists():
        for r in csv.DictReader(durum_yol.open(encoding="utf-8")):
            durum[r["pair"]] = r
    todo = [p for p in benim if a.force or durum.get(p, {}).get("status") != "PASS"]
    log(f"shard {a.shard}/{a.shards}: {len(benim)} cift, {len(todo)} islenecek | A1 baski alani "
        f"{aw}x{ah} (oran {hedef_oran:.5f}) | kopya: Drive ici, kirpma/olcekleme yok")

    csv_yol = pathlib.Path(a.csv or (durum_yol.parent / f"URETIM_A1_shard{a.shard}.csv"))
    if not csv_yol.exists():
        with csv_yol.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_SUT)
    t0 = time.time()
    n_ok = n_fail = 0
    for i, cift in enumerate(todo, start=1):
        tp = time.time()
        hatalar, satirlar, n = [], [], 0
        for ed in EDITIONS:
            ts = time.time()
            src = f"{a.rclone_src}/{ed}/A_SERIES/{cift}.jpg"
            dst = f"{a.rclone_out}/{cift}/{ed}/{BOY}.jpg"
            s = {"pair": cift, "edition": ed, "dosya": f"{cift}/{ed}/{BOY}.jpg",
                 "baski_alani_px": f"{aw}x{ah}", "durum": "HATA", "neden": ""}
            olcu = jpeg_olcu(src)
            if not olcu:
                s["neden"] = "usta okunamadi/JPEG basligi yok"
                hatalar.append(f"{ed}: {s['neden']}")
                satirlar.append(s)
                continue
            w, h = olcu
            fark = abs((w / h) / hedef_oran - 1)
            dpi_kisa, dpi_uzun = round(w / A1_IN[0]), round(h / A1_IN[1])
            s.update({"usta_px": f"{w}x{h}", "oran_farki_yuzde": round(fark * 100, 3),
                      "dpi_kisa": dpi_kisa, "dpi_uzun": dpi_uzun,
                      "dpi_yeterli": "EVET" if min(dpi_kisa, dpi_uzun) >= 300 else "HAYIR",
                      "bayt": bayt_olcu(src)})
            if fark > ORAN_TOL:
                s["neden"] = f"oran farki %{fark * 100:.2f} > %{ORAN_TOL * 100:.1f}"
                hatalar.append(f"{ed}: {s['neden']}")
                satirlar.append(s)
                continue
            if w < aw or h < ah:
                s["neden"] = f"usta {w}x{h} < baski alani {aw}x{ah}"
                hatalar.append(f"{ed}: {s['neden']}")
                satirlar.append(s)
                continue
            r = rclone("copyto", src, dst, sert=False)
            if r.returncode != 0:
                s["neden"] = f"kopya hatasi: {(r.stderr or '')[-80:]}"
                hatalar.append(f"{ed}: kopya hatasi")
                satirlar.append(s)
                continue
            s["kopya_bayt"] = bayt_olcu(dst)
            s["durum"] = "GECTI" if s["kopya_bayt"] == s["bayt"] else "HATA"
            if s["durum"] != "GECTI":
                s["neden"] = f"kopya bayt {s['kopya_bayt']} != usta {s['bayt']}"
                hatalar.append(f"{ed}: {s['neden']}")
            else:
                n += 1
            s["sn"] = round(time.time() - ts, 1)
            satirlar.append(s)
        with csv_yol.open("a", newline="", encoding="utf-8") as fh:
            w_csv = csv.DictWriter(fh, fieldnames=CSV_SUT, extrasaction="ignore")
            for s in satirlar:
                w_csv.writerow(s)
        ok = n == len(EDITIONS) and not hatalar
        durum[cift] = {"pair": cift, "status": "PASS" if ok else "FAIL", "files": n,
                       "fail": "; ".join(hatalar)[:300], "secs": round(time.time() - tp, 1),
                       "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with durum_yol.open("w", newline="", encoding="utf-8") as fh:
            w_csv = csv.DictWriter(fh, fieldnames=["pair", "status", "files", "fail", "secs", "ts_utc"])
            w_csv.writeheader()
            for k in sorted(durum):
                w_csv.writerow({c: durum[k].get(c, "") for c in
                                ["pair", "status", "files", "fail", "secs", "ts_utc"]})
        n_ok += ok
        n_fail += (not ok)
        gec = time.time() - t0
        log(f"{i}/{len(todo)} (%{100 * i / len(todo):.1f}) {cift} {'PASS' if ok else 'FAIL'} {n}/5 "
            f"{('; '.join(hatalar))[:60]} | gecen {sure(gec)} | kalan ~{sure(gec / i * (len(todo) - i))}")
    rclone("copyto", str(csv_yol), f"gdrive:ASTROLOVE/TEMP/POD_5X7/parca/{csv_yol.name}", sert=False)
    print(json.dumps({"shard": a.shard, "pass": n_ok, "fail": n_fail}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
