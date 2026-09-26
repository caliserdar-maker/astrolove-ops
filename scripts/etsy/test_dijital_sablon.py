import unittest

import dijital_sablon
import kisisel_uyum
import magaza_denetim


class DijitalSablonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = dijital_sablon.catalog()

    @staticmethod
    def listing(record, index):
        item = dict(record)
        first, second = (part.capitalize() for part in record["pair"].split("_", 1))
        alt_text = f"{first} and {second} personalized zodiac couple digital artwork"
        item.update({"listing_id": index, "type": "download", "files": [], "processing_min": 2,
                     "processing_max": 3, "materials": [], "who_made": "i_did", "when_made": "made_to_order",
                     "is_supply": False, "shop_section_id": 1, "taxonomy_id": 1, "price": 1,
                     "images": [{"rank": rank, "alt_text": alt_text}
                                for rank in range(1, 11)], "videos": [{"video_id": 1}]})
        return item

    def test_78_pairs_times_two_products(self):
        self.assertEqual(78, len(dijital_sablon.zodiac_pairs()))
        self.assertEqual(156, len(self.records))
        self.assertEqual(156, len({(row["pair"], row["product"]) for row in self.records}))

    def test_approved_copy_is_used_verbatim(self):
        row = dijital_sablon.build("Aries", "Leo", "wall_art")
        self.assertEqual(dijital_sablon.TITLE["wall_art"].format(A="Aries", B="Leo"), row["title"])
        self.assertEqual(dijital_sablon.DESCRIPTION["wall_art"].format(
            A="Aries", B="Leo", a="aries", b="leo", personalize=dijital_sablon.PERSONALIZE,
            how=dijital_sablon.HOW), row["description"])
        self.assertNotRegex(row["description"].casefold(), r"instant download")
        self.assertIn("check every order by hand", row["description"])

    def test_approved_tag_rules(self):
        cancer = dijital_sablon.build("Cancer", "Leo", "wall_art")["tags"]
        self.assertIn("cancer zodiac gift", cancer)
        self.assertNotIn("cancer gift", cancer)
        fallback = dijital_sablon.build("Sagittarius", "Aquarius", "wall_art")["tags"]
        self.assertEqual("sagittarius aquarius", fallback[0])
        skipped = dijital_sablon.build("Sagittarius", "Capricorn", "wall_art")["tags"]
        self.assertEqual(12, len(skipped))
        overlong = {tag for row in self.records for tag in row["tags"] if len(tag) > 20}
        self.assertEqual({"sagittarius wallpaper"}, overlong)

    def test_personalization_uses_pod_schema(self):
        for row in self.records:
            self.assertEqual(dijital_sablon.personalization_questions(row["pair"]),
                             row["personalization_questions"])

    def test_current_auditor_incompatibilities_are_stable_and_reported(self):
        personal_failures = set()
        shop_failures = set()
        for index, record in enumerate(self.records, 1):
            listing = self.listing(record, index)
            result = kisisel_uyum.audit_one(listing)
            if result["durum"] == "FAIL":
                personal_failures.update(result["neden"].split(";"))
            shop_failures.update(row["kural"] for row in magaza_denetim.denetle_ilan(listing)
                                 if row["durum"] == "FAIL")
        self.assertEqual({"kisisellestirme_soru_sayisi"}, personal_failures)
        self.assertEqual({"baslik_tekrar", "etiket_sayisi", "etiket_uzunluk", "etiket_tekrar"},
                         shop_failures)


if __name__ == "__main__":
    unittest.main()
