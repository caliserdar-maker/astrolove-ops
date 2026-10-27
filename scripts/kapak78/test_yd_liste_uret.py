#!/usr/bin/env python3
"""yd_liste_uret.py yerel testi (plan v3 adim 6; 10'lu galeri, Serdar 27 Eki). Gercek veri: pilot HAM (test_veri/HAM_4595350971.json),
docs/yd_kapak/KAPAK_KAYNAK.csv, docs/yd_kapak/YD_OZET.csv. Sahte: 10 kart dosyasi, tasima MANIFEST, QC_RAPOR, ALT.csv, yedek OZET / liste.
Senaryolar: kimlik 78/78 (depodaki data/pod/yd78_ids.csv ile ayni) ve uyusmazlik cikis 2; pilot LISTE (sira 1-10 DEGISTIR, kapak
kararlastirilan alt metin, 2-10 Canva alt metni, ORTAK satiri 4 / 5; eski 13 gorsel CIKAR), manifest Style bagi sira 6-10 (value_id HAM),
eski78 liste_oku + renk_sira; ESLEME 10 satir sha = tasima MANIFEST; BLOK: QC PASS degil / baska sha, sha farkli, karta gore boyut,
yedekte dosya eksik, kapak bagli, Botanical farkli / rank 12 degil, alt metin eksik / uzun tire."""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
KOK = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(KOK / "scripts/etsy"))
import yd_liste_uret as L  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402

HAM = json.loads((HERE / "test_veri/HAM_4595350971.json").read_text())
LID, CIFT = "4595350971", "CANCER_LIBRA"
KAYNAK = KOK / "docs/yd_kapak/KAPAK_KAYNAK.csv"


def kart(p, k, renk=None):
    Image.new("RGB", L.KART_BOYUT[k], renk or (10 + k * 20, 90, 200 - k * 10)).save(p, "JPEG", quality=90)


def galeri_kur(d, cift=CIFT, alt_ek=None, ham=HAM):
    """d altinda HAM, kapak (10 kart + MANIFEST), QC, ALT, yedek OZET / liste"""
    for x in ("HAM", "kapak", "out"):
        (d / x).mkdir(parents=True, exist_ok=True)
    (d / "yd.csv").write_text(f"listing_id,cift,a,b\n{LID},{cift},Cancer,Libra\n")
    (d / "HAM" / f"{LID}.json").write_text(json.dumps(ham))
    for k in range(1, 11):
        kart(d / "kapak" / L.kaynak_ad(cift, k), k)
    manifest(d, cift)
    qc(d, cift)
    alt = {k: f"Cancer and Libra card {k} alt text" for k in (2, 3, 6, 7, 8, 9, 10)}
    alt.update(alt_ek or {})
    (d / "ALT.csv").write_text("cift,kart_no,alt\n" + "".join(f"{cift},{k},{v}\n" for k, v in alt.items())
                               + "ORTAK,4,Format and size options card\nORTAK,5,How your print is made\n")
    (d / "OZET.md").write_text(f"| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n| {LID} | {cift} | 13 | PASS |  |\n")
    yliste(d, ham["images"])


def manifest(d, cift=CIFT, bozuk=None):
    rows = "".join(f"{L.kaynak_ad(cift, k)},{cift},{k},D,-,{'0' * 64 if k == bozuk else L.sha(d / 'kapak' / L.kaynak_ad(cift, k))},YENI\n"
                   for k in range(1, 11))
    (d / "kapak" / "MANIFEST.csv").write_text("ad,cift,kart_no,design_id,boyut,sha256,durum\n" + rows)


def qc(d, cift=CIFT, durum="PASS", sha_bozuk=None):
    (d / "QC.json").write_text(json.dumps(dict(esik=dict(kartlar={}), dosyalar=[
        dict(dosya=L.kaynak_ad(cift, k), cift=cift, kart_no=k, durum=durum,
             sha256="0" * 64 if k == sha_bozuk else L.sha(d / "kapak" / L.kaynak_ad(cift, k))) for k in range(1, 11)])))


def yliste(d, gorseller, cift=CIFT):
    (d / "yl.json").write_text(json.dumps([dict(Path=f"{LID}_{cift}/r{g['rank']}_{g['listing_image_id']}.jpg", Size=1000) for g in gorseller]))


def kos(d):
    with contextlib.redirect_stdout(io.StringIO()) as o:
        rc = L.main(["liste", "--ciftler", str(d / "yd.csv"), "--kaynak", str(KAYNAK), "--ham-dir", str(d / "HAM"),
                     "--kapak-dir", str(d / "kapak"), "--qc", str(d / "QC.json"), "--alt", str(d / "ALT.csv"),
                     "--yedek-ozet", str(d / "OZET.md"), "--yedek-liste", str(d / "yl.json"), "--out", str(d / "out")])
    if rc:
        return rc, o.getvalue(), None
    return rc, o.getvalue(), json.loads((d / "out/LISTE_OZET.json").read_text())["ilanlar"][LID]


class ListeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        galeri_kur(self.t)

    def tearDown(self):
        self.tmp.cleanup()

    def neden(self):
        return " ".join(kos(self.t)[2]["neden"])

    def test_01_kimlik(self):
        out = self.t / "yd78.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = L.main(["kimlik", "--kaynak", str(KAYNAK), "--ozet", str(KOK / "docs/yd_kapak/YD_OZET.csv"), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertEqual(out.read_text(), (KOK / "data/pod/yd78_ids.csv").read_text())
        oz = (KOK / "docs/yd_kapak/YD_OZET.csv").read_text().splitlines()
        (self.t / "oz.csv").write_text("\n".join(oz[:-1]) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = L.main(["kimlik", "--kaynak", str(KAYNAK), "--ozet", str(self.t / "oz.csv"), "--out", str(self.t / "x.csv")])
        self.assertEqual(rc, 2); self.assertFalse((self.t / "x.csv").exists())

    def test_02_pilot_liste_manifest_esleme(self):
        rc, log, s = kos(self.t)
        self.assertEqual((rc, s["durum"]), (0, "HAZIR"), s)
        od = self.t / "out" / LID
        rows = list(csv.DictReader(open(od / f"LISTE_{LID}.csv")))
        hedef = [r for r in rows if r["hedef_sira"]]
        self.assertEqual([(r["hedef_sira"], r["hedef_gorsel"], r["islem"]) for r in hedef],
                         [(str(k), f"{k:02d}_{k}.jpg", "DEGISTIR") for k in range(1, 11)])
        self.assertEqual(hedef[0]["hedef_alt"], "Cancer and Libra 1st anniversary zodiac print, paper anniversary gift")
        self.assertEqual(hedef[3]["hedef_alt"], "Format and size options card"); self.assertEqual(hedef[6]["hedef_alt"], "Cancer and Libra card 7 alt text")
        cikar = [int(r["simdi_id"]) for r in rows if r["islem"] == "CIKAR"]
        self.assertEqual(cikar, [g["listing_image_id"] for g in HAM["images"]])
        man = json.loads((od / "manifest.json").read_text())
        self.assertEqual({v["value"]: v["image_id"] for v in man["variation_images"]}, L.STIL_SIRA)
        self.assertEqual({v["value"]: v["value_id"] for v in man["variation_images"]}, {v["value"]: v["value_id"] for v in HAM["variation_images"]})
        self.assertEqual(man["botanical_id"], 8678064852); self.assertEqual(len(man["hedef"]), 10)
        h, c = Y.liste_oku(od / f"LISTE_{LID}.csv", 10)
        self.assertEqual(len(c), 13)
        rv = {v["value"]: (513, v["value_id"]) for v in HAM["variation_images"]}
        self.assertEqual(Y.renk_sira(man, h, rv), L.STIL_SIRA)
        e = list(csv.DictReader(open(self.t / "out/ESLEME.csv")))
        self.assertEqual(len(e), 10); self.assertTrue(all(x["durum"] == "PASS" and x["sha256"] == x["tasima_sha256"] for x in e))
        self.assertEqual([x["kaynak"] for x in e][3:5], ["ORTAK_Y04.jpg", "ORTAK_Y05.jpg"])
        self.assertEqual(Y.sha256(od / "hedef/04_4.jpg"), e[3]["sha256"])

    def test_03_blok_qc_sha_boyut(self):
        qc(self.t, durum="OLCUM"); self.assertIn("QC_RAPOR", self.neden())
        qc(self.t, sha_bozuk=8); self.assertIn("CANCER_LIBRA_Y08.jpg PASS baska dosyaya ait", self.neden())
        qc(self.t); manifest(self.t, bozuk=3); self.assertIn("CANCER_LIBRA_Y03.jpg sha256 tasima MANIFEST ile ayni degil", self.neden())
        kart(self.t / "kapak" / "CANCER_LIBRA_Y02.jpg", 1); manifest(self.t); qc(self.t)                   # kare -> sembol karti
        self.assertIn("CANCER_LIBRA_Y02.jpg: boyut 2400x2400 != 3000x2250", self.neden())

    def test_04_blok_yedek_ham_alt(self):
        yliste(self.t, HAM["images"][1:]); self.assertIn("yedekte 1 gorsel dosyasi yok", self.neden())
        yliste(self.t, HAM["images"])
        h = json.loads(json.dumps(HAM)); h["variation_images"][1]["image_id"] = 8760104081
        (self.t / "HAM" / f"{LID}.json").write_text(json.dumps(h))
        n = self.neden(); self.assertIn("kapak (rank 1) bagli", n); self.assertIn("Botanical bagli gorsel 8760104081", n)
        h = json.loads(json.dumps(HAM)); h["images"][11]["rank"], h["images"][12]["rank"] = 13, 12
        (self.t / "HAM" / f"{LID}.json").write_text(json.dumps(h)); self.assertIn("rank 13 (12 beklenir", self.neden())
        (self.t / "HAM" / f"{LID}.json").write_text(json.dumps(HAM))
        galeri_kur(self.t, alt_ek={7: "Cancer and Libra — Timeless"}); self.assertIn("sira 7 alt metni gecersiz", self.neden())
        (self.t / "ALT.csv").write_text("cift,kart_no,alt\nCANCER_LIBRA,2,x\n"); self.assertIn("sira 3 alt metni gecersiz", self.neden())
        galeri_kur(self.t, alt_ek={6: "Cancer and Libra bright white OBA-free print"}); self.assertIn("sira 6 alt metni gecersiz", self.neden())
        galeri_kur(self.t, alt_ek={8: "Cancer & Libra First Page print"}); self.assertIn("sira 8 alt metni gecersiz", self.neden())
        galeri_kur(self.t)
        (self.t / "ALT.csv").write_text((self.t / "ALT.csv").read_text() + "CANCER_LIBRA,9,Layers print, shown on a wall\n")
        self.assertEqual(kos(self.t)[0], 2)                                           # tirnaksiz virgul: girdi hatasi


if __name__ == "__main__":
    unittest.main(verbosity=2)
