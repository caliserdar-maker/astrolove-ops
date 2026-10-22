import unittest

import dijital_donusum_plan as plan


def ilan(no, title, state="active", **extra):
    sonuc = {"listing_id": no, "title": title, "type": "download", "state": state}
    sonuc.update(extra)
    return sonuc


class Tests(unittest.TestCase):
    def test_title_tag_and_nested_sku_matching(self):
        self.assertEqual(plan.cifti_bul(ilan(1, "Aries + Leo"))[0], "ARIES_LEO")
        self.assertEqual(plan.cifti_bul(ilan(2, "Portrait", tags=["Taurus", "Cancer"]))[0], "TAURUS_CANCER")
        item = ilan(3, "Portrait", inventory={"products": [{"sku": "Gemini_Virgo"}]})
        self.assertEqual(plan.cifti_bul(item)[0], "GEMINI_VIRGO")

    def test_same_sign_requires_two_mentions(self):
        self.assertEqual(plan.cifti_bul(ilan(1, "Aries Aries Couple"))[0], "ARIES_ARIES")
        self.assertEqual(plan.cifti_bul(ilan(2, "Aries Portrait"))[1], "ESLESMEDI")

    def test_conflict_and_unmatched_are_listed(self):
        rows, summary = plan.planla([
            ilan(1, "Aries Leo", tags=["Taurus Cancer"]), ilan(2, "No zodiac names")
        ])
        self.assertEqual(summary["cakismalar"], ["1"])
        self.assertEqual(summary["eslesmeyenler"], ["2"])
        self.assertTrue(all(row["eylem"] == "TASLAGA_AL" for row in rows))

    def test_engagement_selects_keeper_and_draft_is_archived(self):
        rows, _ = plan.planla([
            ilan(1, "Aries Leo", views=10),
            ilan(2, "Aries Leo", state="draft", views=9),
        ])
        actions = {row["ilan_id"]: row["eylem"] for row in rows}
        self.assertEqual(actions, {"1": "TUT_VE_DONUSTUR", "2": "ARSIV"})

    def test_oldest_wins_without_metrics_and_draft_warning_is_explicit(self):
        rows, _ = plan.planla([
            ilan(1, "Libra Pisces", creation_timestamp=200),
            ilan(2, "Libra Pisces", state="draft", creation_timestamp=100),
        ])
        keeper = next(row for row in rows if row["eylem"] == "TUT_VE_DONUSTUR")
        self.assertEqual(keeper["ilan_id"], "2")
        self.assertEqual(keeper["taslak_uyarisi"], "UPDATE_LISTING_YAYINA_ALABILIR")

    def test_non_digital_is_ignored(self):
        rows, summary = plan.planla([{"listing_id": 1, "title": "Aries Leo", "type": "physical"}])
        self.assertEqual(rows, [])
        self.assertEqual(summary["dijital_ilan"], 0)


if __name__ == "__main__":
    unittest.main()
