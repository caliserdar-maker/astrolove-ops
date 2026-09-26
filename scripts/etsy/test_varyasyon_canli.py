#!/usr/bin/env python3
"""varyasyon_canli ilan dongusu icin agsiz sentetik testler."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.etsy.varyasyon_canli import ilanlari_denetle, state_hedefleri


class VaryasyonCanliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.renkler = [("Black", 11), ("White", 12), ("Blue", 13), ("Red", 14), ("Green", 15)]
        self.inventory = {"products": [{"property_values": [{"property_id": 200, "property_name": "Primary color",
                            "values": [ad], "value_ids": [vid]}]} for ad, vid in self.renkler]}
        self.images = {"results": [{"rank": n, "listing_image_id": 100 + n} for n in range(1, 6)]}
        self.variation = {"results": [{"property_id": 200, "value_id": vid, "image_id": 100 + n}
                            for n, (_, vid) in enumerate(self.renkler, 1)]}
        d = self.root / "ARIES_LEO" / "TAM_SET"; d.mkdir(parents=True)
        (d / "SET.json").write_text(json.dumps({
            "renk_gorselleri": {ad: f"{ad}.jpg" for ad, _ in self.renkler},
            "galeri": [{"dosya": f"{ad}.jpg", "sira": n} for n, (ad, _) in enumerate(self.renkler, 1)],
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass_ve_tam_uc_cagri(self):
        veri = {"inventory": self.inventory, "variation-images": self.variation, "images": self.images}
        satirlar, cagri = ilanlari_denetle([("ARIES_LEO", "1001")], self.root, lambda _, tur: veri[tur])
        self.assertEqual((satirlar[0]["durum"], cagri), ("PASS", 3))

    def test_yanlis_baglanti_fail(self):
        bozuk = json.loads(json.dumps(self.variation)); bozuk["results"][0]["image_id"] = 105
        veri = {"inventory": self.inventory, "variation-images": bozuk, "images": self.images}
        satirlar, _ = ilanlari_denetle([("ARIES_LEO", "1002")], self.root, lambda _, tur: veri[tur])
        self.assertEqual(satirlar[0]["durum"], "FAIL")
        self.assertIn("Black", satirlar[0]["neden"])

    def test_eksik_set_fail_ve_sonraki_ilan_devam(self):
        veri = {"inventory": self.inventory, "variation-images": self.variation, "images": self.images}
        satirlar, cagri = ilanlari_denetle(
            [("YOK_SET", "1003"), ("ARIES_LEO", "1004")], self.root, lambda _, tur: veri[tur])
        self.assertEqual([x["durum"] for x in satirlar], ["FAIL", "PASS"])
        self.assertEqual(cagri, 6)

    def test_state_yalniz_pass_ve_referans(self):
        hedef = state_hedefleri({"ilan": {"ARIES_LEO": {"sonuc": "PASS", "ilan_id": 1001},
                                                "TAURUS_VIRGO": {"sonuc": "FAIL", "ilan_id": 1002}}})
        self.assertEqual(hedef, [("ARIES_LEO", "1001"), ("CANCER_LIBRA", "4570143815")])


if __name__ == "__main__":
    unittest.main()
