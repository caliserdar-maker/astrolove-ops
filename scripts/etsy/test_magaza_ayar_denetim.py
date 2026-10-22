import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from magaza_ayar_denetim import POD_PROFILE_ID, audit


def fixture():
    return {
        "shop": {"title": "AstroLove", "announcement": "Fine art prints", "about": "Original zodiac art"},
        "sections": [{"shop_section_id": 10, "title": "Zodiac Prints"}],
        "shipping_profiles": [{"shipping_profile_id": POD_PROFILE_ID, "title": "POD",
            "min_processing_days": 2, "max_processing_days": 5,
            "shipping_profile_destinations": [{"destination_country_iso": "US", "primary_cost": {"amount": 0}, "shipping_upgrade_id": 3}]}],
        "return_policies": [{"return_policy_id": 20, "accepts_returns": False, "accepts_exchanges": False}],
        "production_partners": [{"production_partner_id": 30, "partner_name": "Prodigi"}],
        "listings": [{"listing_id": 40, "shop_section_id": 10, "shipping_profile_id": POD_PROFILE_ID,
                      "return_policy_id": 20, "production_partner_ids": [30]}],
    }


def failed(data, rule):
    return any(r["kural"] == rule and r["durum"] == "FAIL" for r in audit(data))


class AuditTests(unittest.TestCase):
    def test_valid_snapshot_passes(self):
        self.assertFalse([r for r in audit(fixture()) if r["durum"] == "FAIL"])

    def test_processing_null_fails(self):
        data = fixture(); data["shipping_profiles"][0]["min_processing_days"] = None
        self.assertTrue(failed(data, "processing_min_max"))

    def test_missing_and_empty_sections_fail(self):
        data = fixture(); data["listings"][0]["shop_section_id"] = None
        self.assertTrue(failed(data, "ilan_bolumu_var")); self.assertTrue(failed(data, "bolumde_ilan_var"))

    def test_bad_section_spelling_fails(self):
        data = fixture(); data["sections"][0]["title"] = " Zodiac  – Prints "
        self.assertTrue(failed(data, "bolum_adi"))

    def test_return_policy_fails(self):
        data = fixture(); data["return_policies"][0]["accepts_returns"] = True
        self.assertTrue(failed(data, "pod_iade_politikasi")); self.assertTrue(failed(data, "pod_ilan_iade"))

    def test_prodigi_assignment_fails(self):
        data = fixture(); data["listings"][0]["production_partner_ids"] = []
        self.assertTrue(failed(data, "pod_prodigi_atamasi"))

    def test_missing_prodigi_fails(self):
        data = fixture(); data["production_partners"] = []
        self.assertTrue(failed(data, "prodigi_var")); self.assertTrue(failed(data, "pod_prodigi_atamasi"))

    def test_shop_text_rules_fail(self):
        data = fixture(); data["shop"]["announcement"] = "Bright white — paper"
        self.assertTrue(failed(data, "metin_kurallari"))

    def test_missing_profile_and_destination_fail(self):
        data = fixture(); data["shipping_profiles"][0]["shipping_profile_destinations"] = []
        data["listings"].append({"listing_id": 41, "shipping_profile_id": 999, "shop_section_id": 10})
        self.assertTrue(failed(data, "ilan_profili_var")); self.assertTrue(failed(data, "hedefler_ve_ucretler"))

    def test_known_pod_profile_missing_fails(self):
        data = fixture(); data["shipping_profiles"] = []
        self.assertTrue(failed(data, "pod_profili_var")); self.assertTrue(failed(data, "ilan_profili_var"))


if __name__ == "__main__":
    unittest.main()
