"""kupa_taslak --mod kuru: sahte galeri + metinle CANCER_LIBRA istek plani. Ag erisimi yok."""
import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kupa_taslak as k  # noqa: E402

GALERI = ["01_Orange_Blossom_kapak", "02_Yakin_plan", "03_How_to_personalize", "04_Choose_your_style", "05_Two_sizes",
          "06_Names_and_message", "07_Care_and_making", "08_Purple_Fig", "09_Olive_Breeze", "10_Pomegranate_Bloom",
          "11_Almond_Blossom", "12_Lemon_Grove", "13_Blue_Grape", "14_Golden_Loquat"]
ACIKLAMA = "Eight styles: " + ", ".join(a for a, *_ in k.STILLER) + ". Made by AstroLoveArt."
ETIKET = ", ".join(f"cancer libra tag {i}" for i in range(13))


class KuruTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        g = self.d / "img/CANCER_LIBRA/galeri"; g.mkdir(parents=True)
        (self.d / "img/CANCER_LIBRA/video").mkdir()
        for n in GALERI:
            (g / f"{n}.jpg").write_bytes(b"x" * 10)
        (g / "GALERI_1_14.jpg").write_bytes(b"x")
        (self.d / "img/CANCER_LIBRA/video/ORCHARD_Cancer_Libra_video_6sn.mp4").write_bytes(b"v" * 20)
        with open(self.d / "metin.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(k.METIN_SUTUN)
            w.writerow(["CANCER_LIBRA", "Cancer and Libra Personalized Mug", ETIKET, "Please write 3 lines", ACIKLAMA])
        os.environ.update(METIN_CSV=str(self.d / "metin.csv"), IMG_ROOT=str(self.d / "img"))

    def test_kuru_plan(self):
        oz = k.kuru("39729443", self.d / "out", "CANCER_LIBRA")
        self.assertTrue(all(oz["kontrol"].values()), oz["kontrol"])
        self.assertEqual(oz["metin"]["hata"], [])
        self.assertEqual(oz["eski_taslak_yok_sayildi"], [4597843405])
        d = json.load(open(self.d / "out/kuru/KURU_CANCER_LIBRA.json"))
        yaz = [x for x in d["istekler"] if x["yazma"]]
        self.assertEqual(sum(x["url"].endswith("/images") for x in yaz), 14)
        self.assertFalse(any(x["method"] in ("PATCH", "DELETE") for x in yaz))
        self.assertFalse(any("4597843405" in x["url"] for x in yaz))
        inv = next(x["json"] for x in yaz if x["url"].endswith("/inventory"))
        self.assertEqual(len(inv["products"]), 16)
        self.assertEqual({p["sku"] for p in inv["products"]},
                         {f"KUPA-CANCER_LIBRA-{i:02d}-{b}" for i in range(1, 9) for b in (11, 15)})
        self.assertEqual({p["property_values"][1]["values"][0]: p["offerings"][0]["price"] for p in inv["products"]},
                         {"11 oz": 24.0, "15 oz": 29.0})
        vi = next(x["json"] for x in yaz if x["url"].endswith("/variation-images"))["variation_images"]
        self.assertEqual([v["image_id"] - 800000 for v in vi], [1, 8, 9, 10, 11, 12, 13, 14])

    def test_eski_stil_metni_durdurur(self):
        satir = dict(kod="CANCER_LIBRA", baslik="x", etiketler=ETIKET, kisisellestirme_talimati="y",
                     aciklama="Rose Ribbon or Nazar Bond")
        self.assertTrue(k.metin_kontrol(satir)[4])

    def test_talimat_120(self):
        satir = dict(kod="CANCER_LIBRA", baslik="x", etiketler=ETIKET, kisisellestirme_talimati="a" * 120, aciklama=ACIKLAMA)
        self.assertEqual(k.metin_kontrol(satir)[4], [])
        satir["kisisellestirme_talimati"] = "a" * 121
        self.assertEqual(k.metin_kontrol(satir)[4], ["talimat 121 > 120"])

    def test_izin(self):
        api = k.Kuru("1"); api.lid = 9000000001
        for m, p in [("PUT", "/listings/4597843405/inventory"), ("POST", "/shops/1/listings/4598525642/personalization"),
                     ("POST", "/shops/1/sections"),
                     ("POST", "/shops/1/shipping-profiles"), ("DELETE", "/shops/1/listings/9000000001")]:
            with self.assertRaises(SystemExit):
                api._izin(m, p)
        with self.assertRaises(SystemExit):
            api.patch("/shops/1/listings/9000000001", {"title": "x"})

    def test_78_cift(self):
        self.assertEqual(len(k.CIFTLER), 78)
        self.assertEqual(k.cift_listesi("cancer_libra, LEO_LEO"), ["CANCER_LIBRA", "LEO_LEO"])
        with self.assertRaises(SystemExit):
            k.cift_listesi("LIBRA_CANCER")


if __name__ == "__main__":
    unittest.main()
