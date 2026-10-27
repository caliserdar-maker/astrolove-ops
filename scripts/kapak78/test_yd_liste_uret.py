#!/usr/bin/env python3
"""yd_liste_uret.py yerel testi (plan v3 adim 6). Gercek veri: pilot HAM (test_veri/HAM_4595350971.json), docs/yd_kapak/KAPAK_KAYNAK.csv,
docs/yd_kapak/YD_OZET.csv. Sahte: kapak dosyasi, tasima MANIFEST, QC_RAPOR, yedek OZET / liste.
Senaryolar: kimlik 78/78 (depodaki data/pod/yd78_ids.csv ile ayni) ve uyusmazlik cikis 2; pilot LISTE (sira 1 DEGISTIR yeni alt metin,
2-13 KORU HAM alt metni aynen (bos), eski kapak CIKAR), manifest 5 Style bagi aynen (Botanical -> rank 12 = KAPAK_KAYNAK kaynagi),
kapak bagsiz, eski78 liste_oku (bos alt izinli) + renk_sira 5 bag; ESLEME sha = tasima MANIFEST; BLOK: QC PASS degil, sha farkli,
3000x2250, yedekte eski kapak yok, kapak bagli, Botanical farkli."""
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


def jpg(p, wh=(2400, 2400), renk=(30, 90, 40)):
    Image.new("RGB", wh, renk).save(p, "JPEG", quality=90)


class ListeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = self.t = Path(self.tmp.name)
        for d in ("HAM", "kapak", "out"):
            (t / d).mkdir()
        (t / "yd.csv").write_text(f"listing_id,cift,a,b\n{LID},{CIFT},Cancer,Libra\n")
        self.ham(HAM)
        jpg(t / "kapak" / f"KAPAK_{CIFT}.jpg")
        self.manifest()
        self.qc("PASS")
        (t / "OZET.md").write_text(f"| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n| {LID} | {CIFT} | 13 | PASS |  |\n")
        self.yliste([g for g in HAM["images"]])

    def tearDown(self):
        self.tmp.cleanup()

    def ham(self, h):
        (self.t / "HAM" / f"{LID}.json").write_text(json.dumps(h))

    def manifest(self, sha=None):
        s = sha or L.sha(self.t / "kapak" / f"KAPAK_{CIFT}.jpg")
        (self.t / "kapak" / "MANIFEST.csv").write_text(
            f"ad,cift,kart_no,design_id,boyut,sha256,durum\nKAPAK_{CIFT}.jpg,{CIFT},1,DAHZIAyOYA8,2400x2400,{s},YENI\n")

    def qc(self, durum, sha=None):
        (self.t / "QC_RAPOR.json").write_text(json.dumps(dict(esik=dict(poster_min=0.9, sahne_min=0.9), dosyalar=[
            dict(dosya=f"KAPAK_{CIFT}.jpg", cift=CIFT, ncc_poster=0.99, ncc_sahne=0.99, durum=durum,
                 sha256=sha or L.sha(self.t / "kapak" / f"KAPAK_{CIFT}.jpg"))])))

    def yliste(self, gorseller):
        (self.t / "yliste.json").write_text(json.dumps([dict(Path=f"{LID}_{CIFT}/r{g['rank']}_{g['listing_image_id']}.jpg", Size=1000)
                                                        for g in gorseller]))

    def kos(self):
        t = self.t
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = L.main(["liste", "--ciftler", str(t / "yd.csv"), "--kaynak", str(KAYNAK), "--ham-dir", str(t / "HAM"),
                         "--kapak-dir", str(t / "kapak"), "--qc", str(t / "QC_RAPOR.json"), "--yedek-ozet", str(t / "OZET.md"),
                         "--yedek-liste", str(t / "yliste.json"), "--out", str(t / "out")])
        oz = json.loads((t / "out/LISTE_OZET.json").read_text())
        return rc, o.getvalue(), oz["ilanlar"][LID]

    def test_01_kimlik(self):
        out = self.t / "yd78.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = L.main(["kimlik", "--kaynak", str(KAYNAK), "--ozet", str(KOK / "docs/yd_kapak/YD_OZET.csv"), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertEqual(out.read_text(), (KOK / "data/pod/yd78_ids.csv").read_text())
        oz = (KOK / "docs/yd_kapak/YD_OZET.csv").read_text().splitlines()
        (self.t / "oz.csv").write_text("\n".join(oz[:-1]) + "\n")                       # 77 satir
        with contextlib.redirect_stdout(io.StringIO()):
            rc = L.main(["kimlik", "--kaynak", str(KAYNAK), "--ozet", str(self.t / "oz.csv"), "--out", str(self.t / "x.csv")])
        self.assertEqual(rc, 2); self.assertFalse((self.t / "x.csv").exists())

    def test_02_pilot_liste_manifest_esleme(self):
        rc, log, s = self.kos()
        self.assertEqual((rc, s["durum"]), (0, "HAZIR"), s)
        od = self.t / "out" / LID
        rows = list(csv.DictReader(open(od / f"LISTE_{LID}.csv")))
        self.assertEqual(rows[0], dict(hedef_sira="1", hedef_gorsel="01_1.jpg", hedef_alt="Cancer and Libra 1st anniversary zodiac print, paper anniversary gift",
                                       islem="DEGISTIR", simdi_sira="", simdi_id=""))
        koru = [r for r in rows if r["islem"] == "KORU"]
        self.assertEqual([int(r["hedef_sira"]) for r in koru], list(range(2, 14)))
        self.assertEqual([r["simdi_id"] for r in koru], [str(g["listing_image_id"]) for g in HAM["images"][1:]])
        self.assertTrue(all(r["hedef_alt"] == "" for r in koru))                                    # HAM'da bos -> bos
        self.assertEqual([(r["islem"], r["simdi_id"]) for r in rows if r["islem"] == "CIKAR"], [("CIKAR", "8760104081")])
        man = json.loads((od / "manifest.json").read_text())
        self.assertEqual(sorted((v["value"], v["image_id"]) for v in man["variation_images"]),
                         sorted((v["value"], v["image_id"]) for v in HAM["variation_images"]))
        self.assertEqual(man["botanical_id"], 8678064852); self.assertEqual(man["eski_kapak"], 8760104081)
        self.assertNotIn(8760104081, [v["image_id"] for v in man["variation_images"]])
        self.assertEqual(man["yedek_kapak"]["yol"], f"{LID}_{CIFT}/r1_8760104081.jpg")
        # eski78 okuyuculari: bos alt KORU izinli (YD), 5 Style bagi siralari 9..13
        hedef, cikar = Y.liste_oku(od / f"LISTE_{LID}.csv", 13, bos_alt_koru=True)
        self.assertEqual(cikar, [8760104081])
        rv = {v["value"]: (513, v["value_id"]) for v in HAM["variation_images"]}
        self.assertEqual(Y.renk_sira(man, hedef, rv), {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 13})
        with self.assertRaises(Y.Dur):
            Y.liste_oku(od / f"LISTE_{LID}.csv", 13)                                             # poster kurali aynen: bos alt red
        e = list(csv.DictReader(open(self.t / "out/ESLEME.csv")))
        self.assertEqual(len(e), 1); self.assertEqual(e[0]["durum"], "PASS"); self.assertEqual(e[0]["sha256"], e[0]["tasima_sha256"])
        self.assertEqual(Y.sha256(od / "hedef/01_1.jpg"), e[0]["sha256"])

    def test_03_blok_qc_sha_boyut(self):
        self.qc("OLCUM")
        self.assertIn("QC_RAPOR", self.kos()[2]["neden"][0])
        self.qc("PASS", sha="0" * 64)
        self.assertIn("PASS baska dosyaya ait", " ".join(self.kos()[2]["neden"]))           # QC baska baytlara ait
        self.qc("PASS"); self.manifest(sha="0" * 64)
        self.assertIn("sha256 tasima MANIFEST ile ayni degil", " ".join(self.kos()[2]["neden"]))
        jpg(self.t / "kapak" / f"KAPAK_{CIFT}.jpg", (3000, 2250)); self.manifest()
        self.assertIn("2400x2400", " ".join(self.kos()[2]["neden"]))

    def test_04_blok_yedek_ve_ham(self):
        self.yliste(HAM["images"][1:])                                                            # eski kapak yedekte yok
        n = " ".join(self.kos()[2]["neden"]); self.assertIn("yedekte eski kapak yok", n)
        self.yliste(HAM["images"])
        h = json.loads(json.dumps(HAM))
        h["variation_images"][1]["image_id"] = 8760104081                                         # Botanical kapaga bagli
        self.ham(h)
        n = " ".join(self.kos()[2]["neden"])
        self.assertIn("kapak (rank 1) bagli", n); self.assertIn("Botanical bagli gorsel 8760104081", n)
        h = json.loads(json.dumps(HAM))
        h["images"][11]["rank"], h["images"][12]["rank"] = 13, 12                                  # Botanical rank 13'e kaymis
        self.ham(h)
        self.assertIn("rank 13 (12 beklenir", " ".join(self.kos()[2]["neden"]))
        h = json.loads(json.dumps(HAM)); h["images"] = h["images"][:12]; h["listing"]["state"] = "draft"
        self.ham(h)
        n = " ".join(self.kos()[2]["neden"]); self.assertIn("13 beklenir", n); self.assertIn("state draft", n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
