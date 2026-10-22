#!/usr/bin/env python3
"""varyasyon_denetle birim testleri."""

import unittest

from scripts.etsy.varyasyon_denetle import denetle, hedef_liste


class VaryasyonDenetleTest(unittest.TestCase):
    def setUp(self):
        self.renkler = [("Black", 11), ("White", 12), ("Blue", 13), ("Red", 14), ("Green", 15)]
        self.inventory = {"products": [{"property_values": [{
            "property_id": 200, "property_name": "Primary color", "values": [renk], "value_ids": [value_id]
        }]} for renk, value_id in self.renkler]}
        self.set_data = {
            "renk_gorselleri": {renk: f"{renk}.jpg" for renk, _ in self.renkler},
            "galeri": [{"dosya": f"{renk}.jpg", "sira": sira} for sira, (renk, _) in enumerate(self.renkler, 1)],
        }
        self.images = {"results": [
            {"rank": sira, "listing_image_id": 100 + sira} for sira in range(1, 6)
        ]}
        self.variation_images = {"results": [
            {"property_id": 200, "value_id": value_id, "image_id": 100 + sira}
            for sira, (_, value_id) in enumerate(self.renkler, 1)
        ]}

    def test_dogru_bes_bes_pass_ve_hedef(self):
        self.assertEqual(denetle(self.inventory, self.variation_images, self.images, self.set_data)["durum"], "PASS")
        self.assertEqual(
            hedef_liste(self.inventory, self.images, self.set_data),
            {"variation_images": self.variation_images["results"]},
        )

    def test_bos_liste_fail(self):
        self.assertEqual(denetle(self.inventory, [], self.images, self.set_data)["durum"], "FAIL")

    def test_dort_bes_fail(self):
        rapor = denetle(self.inventory, self.variation_images["results"][:-1], self.images, self.set_data)
        self.assertEqual(rapor["durum"], "FAIL")
        self.assertIn("eksik", rapor["renkler"][-1]["nedenler"][0])

    def test_silinmis_image_id_fail(self):
        images = {"results": self.images["results"][:-1]}
        rapor = denetle(self.inventory, self.variation_images, images, self.set_data)
        self.assertEqual(rapor["durum"], "FAIL")
        self.assertIn("galeride yok", " ".join(rapor["renkler"][-1]["nedenler"]))

    def test_yanlis_siraya_bagli_fail(self):
        self.variation_images["results"][0]["image_id"] = 102
        rapor = denetle(self.inventory, self.variation_images, self.images, self.set_data)
        self.assertEqual(rapor["durum"], "FAIL")
        self.assertIn("yanlis siraya", " ".join(rapor["renkler"][0]["nedenler"]))

    def test_property_id_farkli_fail(self):
        self.variation_images["results"][0]["property_id"] = 999
        rapor = denetle(self.inventory, self.variation_images, self.images, self.set_data)
        self.assertEqual(rapor["durum"], "FAIL")
        self.assertIn("property_id", " ".join(rapor["renkler"][0]["nedenler"]))


if __name__ == "__main__":
    unittest.main()
