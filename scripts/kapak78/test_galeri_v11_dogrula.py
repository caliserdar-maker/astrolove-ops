#!/usr/bin/env python3
"""galeri_v11_dogrula.py sahte veriyle: PASS, yer degisen gorsel, alt metin, bag, state, sha. Pillow 11.0.0."""
import csv
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_v11_dogrula as D  # noqa: E402
import galeri_v10_liste as L  # noqa: E402

KOK = HERE.parent.parent
SONUC = []


def kontrol(ad, ok):
    SONUC.append((ad, ok)); print(("PASS " if ok else "FAIL ") + ad)


def kur(t):
    r = next(csv.DictReader(open(KOK / "data/pod/pod78_ids.csv", encoding="utf-8-sig")))
    lid, cift = r["listing_id"], r["cift"]
    g, k, c, so = t / "g", t / "k", t / "c" / f"{lid}_{cift}", t / "s"
    for x in (g, k, c, so):
        x.mkdir(parents=True)
    rng = np.random.default_rng(1)
    ids = [9000 + s for s in range(1, 11)]
    alt = L.alt_metin({int(x["sira"]): x for x in csv.DictReader(open(KOK / "data/pod/galeri_v11_alt.csv", encoding="utf-8-sig"))},
                      r["a"], r["b"])
    kay = []
    for s in range(1, 11):
        a = (rng.random((45, 60, 3)) * 255).astype(np.uint8)
        im = Image.fromarray(a).resize((3000, 2250), Image.BILINEAR)
        p = D.kaynak_yol(cift, s, g, k); im.save(p, quality=95)
        im.save(c / f"r{s}_{ids[s - 1]}.jpg", quality=70)
        kay.append(dict(hedef_sira=s, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), listing_image_id=ids[s - 1]))
    bag = [dict(property_id=200, value=v, image_id=ids[s - 1]) for v, s in D.RENK_SIRA.items()]
    j = dict(ilan=dict(state="active"), gorseller=[dict(rank=s, listing_image_id=ids[s - 1], alt_text=alt[s]) for s in range(1, 11)],
             baglar=bag, videolar=[dict(video_id=1)])
    (c / "GALERI.json").write_text(json.dumps(j))
    (so / f"SONRA_{lid}.json").write_text(json.dumps(dict(son_ids=ids, yukleme_kaydi=kay)))
    return lid, c, j


def kos(t, lid, profil="v11"):
    ek = ["--profil", "v11b", "--b1", str(t / "b1")] if profil == "v11b" else []
    return D.main(ek + ["--canli", str(t / "c"), "--sonra", str(t / "s"), "--galeri", str(t / "g"), "--kart", str(t / "k"),
                   "--alt", str(KOK / "data/pod/galeri_v11_alt.csv"), "--ciftler", str(KOK / "data/pod/pod78_ids.csv"),
                   "--sadece", lid, "--out", str(t / "o")])


def main():
    t = Path(tempfile.mkdtemp())
    try:
        lid, c, j = kur(t)
        kontrol("dogru galeri PASS", kos(t, lid) == 0)
        a, b = c / "r3_9003.jpg", c / "r4_9004.jpg"
        shutil.copyfile(a, t / "x"); shutil.copyfile(b, a); shutil.copyfile(t / "x", b)
        kontrol("canli W03 / W04 yer degistirmis -> FAIL (NCC kimlik)", kos(t, lid) == 1)
        shutil.copyfile(b, t / "x"); shutil.copyfile(a, b); shutil.copyfile(t / "x", a)
        for alan, bozan in (("alt", lambda y: y["gorseller"][4].update(alt_text="x")),
                            ("bag", lambda y: y["baglar"][0].update(image_id=9002)),
                            ("state", lambda y: y["ilan"].update(state="draft"))):
            y = json.loads(json.dumps(j)); bozan(y); (c / "GALERI.json").write_text(json.dumps(y))
            kontrol(f"{alan} bozuk -> FAIL", kos(t, lid) == 1)
        (c / "GALERI.json").write_text(json.dumps(j))
        p = next((t / "g").glob("*_W01_KAPAK.jpg")); Image.new("RGB", (3000, 2250)).save(p)
        kontrol("kaynak sha256 yukleme kaydindan farkli -> FAIL", kos(t, lid) == 1)
        # v11b (Serdar 29 Eki): rank 1 = B1 yedegindeki MB kapak (dokunulmaz), 2-10 yuklenen, baglar MB 7 DB 8 PW 9 WP 10
        (t / "g" / p.name).unlink()
        so = t / "s" / f"SONRA_{lid}.json"; sj = json.loads(so.read_text())
        sj["yukleme_kaydi"] = [k for k in sj["yukleme_kaydi"] if k["hedef_sira"] != 1]; so.write_text(json.dumps(sj))
        jb = json.loads(json.dumps(j)); jb["baglar"] = [x for x in jb["baglar"] if x["value"] != "Champagne Ivory"]
        for x in jb["baglar"]:
            x["image_id"] = 9000 + D.RENK_SIRA_B[x["value"]]
        jb["gorseller"][0]["alt_text"] = "eski MB kapak metni"; (c / "GALERI.json").write_text(json.dumps(jb))
        b1 = t / "b1" / c.name; b1.mkdir(parents=True)
        (b1 / "GALERI.json").write_text(json.dumps(dict(gorseller=[dict(rank=1, listing_image_id=9001)])))
        kontrol("v11b: rank 1 B1 MB kapak, alt metni serbest, 4 bag -> PASS", kos(t, lid, "v11b") == 0)
        (b1 / "GALERI.json").write_text(json.dumps(dict(gorseller=[dict(rank=1, listing_image_id=1234)])))
        kontrol("v11b: rank 1 B1 MB kapak degil -> FAIL", kos(t, lid, "v11b") == 1)
        (b1 / "GALERI.json").write_text(json.dumps(dict(gorseller=[dict(rank=1, listing_image_id=9001)])))
        (c / "GALERI.json").write_text(json.dumps(j))
        kontrol("v11b: CI bagi var (5 bag) -> FAIL", kos(t, lid, "v11b") == 1)
    finally:
        shutil.rmtree(t)
    bad = [a for a, ok in SONUC if not ok]
    print(f"galeri_v11_dogrula testleri: {len(SONUC) - len(bad)}/{len(SONUC)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
