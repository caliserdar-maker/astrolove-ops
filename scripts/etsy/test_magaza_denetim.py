import copy
import unittest

import magaza_denetim as audit


def valid():
    return {
        "listing_id": 1,
        "title": "Aries Leo Zodiac Couple Portrait",
        "description": "Aries Leo zodiac portrait on natural white paper.",
        "tags": [f"tag {index}" for index in range(13)],
        "materials": ["Hahnemühle Photo Rag"],
        "who_made": "i_did",
        "when_made": "made_to_order",
        "is_supply": False,
        "is_personalizable": True,
        "shop_section_id": 2,
        "taxonomy_id": 10,
        "images": [{"rank": index, "alt_text": "Aries and Leo portrait"} for index in range(1, 14)],
        "videos": [{"video_id": 1}],
        "price": {"amount": 1000, "divisor": 100},
        "shipping_profile_id": 3,
        "processing_min": 3,
        "processing_max": 5,
        "type": "physical",
    }


def failed_rules(item):
    return {row["kural"] for row in audit.denetle_ilan(item) if row["durum"] == "FAIL"}


class Tests(unittest.TestCase):
    def test_correct_listing_passes(self):
        self.assertFalse(failed_rules(valid()))

    def test_title_rules_fail(self):
        item = valid()
        item["title"] = "ART ART " + "%" * 2 + "x" * 141
        expected = {"baslik_uzunluk", "baslik_tekrar", "baslik_ozel_karakter", "baslik_all_caps"}
        self.assertTrue(expected <= failed_rules(item))

    def test_tag_rules_fail(self):
        item = valid()
        item["tags"] = ["same", "same", "x" * 21]
        self.assertTrue({"etiket_sayisi", "etiket_uzunluk", "etiket_tekrar"} <= failed_rules(item))

    def test_description_rules_fail(self):
        item = valid()
        item["description"] = "unrelated — OBA-free Hahnemuhle 100-200 years bright white 12-colour"
        expected = {"aciklama_ilk160_anahtar", "aciklama_yasak_ifade", "aciklama_tire", "hahnemuhle_yazimi"}
        self.assertTrue(expected <= failed_rules(item))

    def test_metadata_rules_fail(self):
        item = valid()
        item.update(materials=[], who_made="someone_else", when_made="2020_2026", is_supply=True, shop_section_id=None)
        expected = {"materials", "who_made", "when_made", "is_supply", "section"}
        self.assertTrue(expected <= failed_rules(item))

    def test_media_price_shipping_rules_fail(self):
        item = valid()
        item.update(images=[], videos=[], price=0, shipping_profile_id=None, processing_min=1, processing_max=3)
        expected = {"gorsel_sayisi", "video", "alt_metin", "fiyat", "shipping_profile", "processing_3_5"}
        self.assertTrue(expected <= failed_rules(item))

    def test_digital_type_and_taxonomy(self):
        item = valid()
        item.update(type="download", materials=[], files=[])
        item2 = copy.deepcopy(item)
        item2.update(listing_id=2, taxonomy_id=99)
        rows = audit.denetle([item, item2])
        self.assertTrue(all(row["durum"] == "FAIL" for row in rows if row["kural"] == "taxonomy_tutarlilik"))
        self.assertNotIn("dijital_type", failed_rules(item))

    def test_personalization_and_instant_delivery_fail(self):
        item = valid()
        item.update(is_personalizable=False, description="Aries Leo portrait instant download")
        self.assertTrue({"is_personalizable", "anlik_teslim_ifadesi"} <= failed_rules(item))

    def test_attached_digital_file_fails(self):
        item = valid()
        item.update(type="download", materials=[], files=[{"listing_file_id": 42}])
        self.assertIn("dijital_dosya_yok", failed_rules(item))


if __name__ == "__main__":
    unittest.main()
