import unittest

from scripts.etsy.kisisel_uyum import audit_one
from scripts.etsy.pod_listing_create import personalization_questions


class KisiselUyumTest(unittest.TestCase):
    def listing(self, **changes):
        item = {"listing_id": 123, "title": "Synthetic product", "type": "physical",
                "is_personalizable": True, "personalization_questions": personalization_questions("ARIES_LEO"),
                "description": "Made to order and delivered within 2-3 business days.",
                "processing_min": 2, "processing_max": 3}
        item.update(changes)
        return item

    def test_valid_listing_passes(self):
        self.assertEqual("PASS", audit_one(self.listing())["durum"])

    def test_not_personalizable_fails(self):
        self.assertIn("kisisellestirme_kapali", audit_one(self.listing(is_personalizable=False))["neden"])

    def test_questions_must_be_required(self):
        questions = personalization_questions("ARIES_LEO")
        questions[0]["required"] = False
        self.assertIn("kisisellestirme_zorunlu", audit_one(self.listing(personalization_questions=questions))["neden"])

    def test_character_limits_must_match_schema(self):
        questions = personalization_questions("ARIES_LEO")
        questions[2]["max_allowed_characters"] = 40
        self.assertIn("kisisellestirme_karakter_siniri", audit_one(self.listing(personalization_questions=questions))["neden"])

    def test_question_text_must_contain_names_and_message(self):
        questions = personalization_questions("ARIES_LEO")
        questions[0]["question_text"] = "First value"
        self.assertIn("kisisellestirme_soru_metni", audit_one(self.listing(personalization_questions=questions))["neden"])

    def test_download_with_file_reports_filename(self):
        row = audit_one(self.listing(type="download"), [{"filename": "old.zip"}])
        self.assertIn("anlik_indirme_dosyasi", row["neden"])
        self.assertEqual("old.zip", row["dosya_adlari"])

    def test_instant_delivery_phrase_fails(self):
        row = audit_one(self.listing(description="Your instant download is ready within 2 hours."))
        self.assertIn("anlik_teslim_ifadesi", row["neden"])

    def test_missing_processing_time_fails(self):
        row = audit_one(self.listing(processing_min=None, processing_max=None))
        self.assertIn("islem_suresi_yok", row["neden"])


if __name__ == "__main__":
    unittest.main()
