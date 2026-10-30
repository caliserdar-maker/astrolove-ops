#!/usr/bin/env python3
"""yd_set_kontrol.py sentetik testi (Etsy yok, Drive yok). Kucuk boyutlu sahte JPEG'ler; boyut kapisi BOYUT yamasiyla."""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

import random

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_set_kontrol as Y  # noqa: E402

Y.BOYUT = (60, 45)
SAY = [0, 0]


def ok(ad, kosul):
    SAY[0 if kosul else 1] += 1
    print(("PASS " if kosul else "FAIL ") + ad)


def gorsel(tohum):
    r = random.Random(tohum)
    return Image.frombytes("RGB", (60, 45), bytes(r.randrange(256) for _ in range(60 * 45 * 3)))


def kur(d, ciftler):
    for i, c in enumerate(ciftler):
        for k in Y.KARTLAR:
            gorsel(i * 100 + k).save(d / f"{c}_Y{k:02d}.jpg", quality=95)
    gorsel(999999).save(d / Y.ORTAK, quality=95)


def kos(t, ids, mut=None):
    d = t / "k"; o = t / "o"
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(o, ignore_errors=True); d.mkdir()
    kur(d, [r["cift"] for r in csv.DictReader(open(ids))])
    if mut:
        mut(d)
    rc = Y.main(["--dir", str(d), "--ciftler", str(ids), "--out", str(o)])
    return rc, (o / "OZET.md").read_text(), list(csv.DictReader(open(o / "SET_KONTROL.csv")))


def main():
    t = Path(tempfile.mkdtemp())
    ids = t / "ids.csv"
    with open(ids, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift"])
        for i in range(78):
            w.writerow([1000 + i, f"AA{chr(65 + i // 26)}{chr(65 + i % 26)}_BB"])
    rc, oz, r = kos(t, ids)
    ok("temiz set PASS 703", rc == 0 and len(r) == 703 and oz.startswith("# YD set kontrolu\n\nPASS"))
    c0 = r[0]["cift"] if r[0]["cift"] != "ORTAK" else r[1]["cift"]
    rc, oz, r = kos(t, ids, lambda d: (d / f"{c0}_Y03.jpg").unlink())
    ok("eksik dosya FAIL", rc == 1 and any(x["neden"] == "dosya yok (eksik)" for x in r))
    rc, oz, r = kos(t, ids, lambda d: Image.new("RGB", (61, 45)).save(d / f"{c0}_Y02.jpg"))
    ok("boyut disi FAIL + listede", rc == 1 and f"- {c0}_Y02.jpg" in oz.split("## Boyut disi")[1])
    rc, oz, r = kos(t, ids, lambda d: (d / f"{c0}_Y05.jpg").write_bytes(b""))
    ok("bos dosya FAIL", rc == 1 and any("bos dosya" in x["neden"] for x in r))
    rc, oz, r = kos(t, ids, lambda d: (d / f"{c0}_Y06.jpg").write_bytes((d / f"{c0}_Y06.jpg").read_bytes()[:300]))
    ok("bozuk JPEG FAIL", rc == 1 and any("bozuk" in x["neden"] for x in r))
    rc, oz, r = kos(t, ids, lambda d: shutil.copyfile(d / f"{c0}_Y07.jpg", d / f"{c0}_Y08.jpg"))
    ok("sha tekrari FAIL", rc == 1 and "ayni sha256" in oz)
    rc, oz, r = kos(t, ids, lambda d: shutil.copyfile(d / Y.ORTAK, d / f"{c0}_Y09.jpg"))
    ok("ORTAK_Y04 ile ayni sha FAIL", rc == 1 and "ORTAK_Y04.jpg" in oz.split("## sha256 tekrari")[1])
    rc, oz, r = kos(t, ids, lambda d: shutil.copyfile(d / f"{c0}_Y01.jpg", d / "ZZZ_YYY_Y01.jpg"))
    ok("listede olmayan cift FAIL", rc == 1 and any(x["dosya"] == "ZZZ_YYY_Y01.jpg" and "yok" in x["neden"] for x in r))
    rc, oz, r = kos(t, ids, lambda d: shutil.copyfile(d / f"{c0}_Y01.jpg", d / f"{c0}_Y04.jpg"))
    ok("cifte ozel Y04 FAIL", rc == 1 and any(x["dosya"] == f"{c0}_Y04.jpg" and "Y04" in x["neden"] for x in r))
    rc, oz, r = kos(t, ids, lambda d: (d / f"{c0}_Y10.jpg").rename(d / f"{c0.lower()}_Y10.jpg"))
    ok("ad kalibi / eslesme FAIL", rc == 1 and any("ad kalibi" in x["neden"] for x in r))
    shutil.rmtree(t)
    print(f"SONUC {SAY[0]} PASS {SAY[1]} FAIL")
    return 1 if SAY[1] else 0


if __name__ == "__main__":
    sys.exit(main())
