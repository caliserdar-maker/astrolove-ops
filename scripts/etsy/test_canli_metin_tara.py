import copy
import json
import tempfile
import unittest
from pathlib import Path

import canli_metin_tara as scan


def valid(pair="ARIES_LEO"):
    a, b = pair.split("_")
    return {
        "title": scan.TITLE.format(S1=a.capitalize(), S2=b.capitalize()),
        "description": "Natural white acid-free paper with pigment-based archival inks.",
        "tags": ["zodiac art", "couple print", "personalized art", "wall decor", "gift for couple",
                 "star sign art", "custom names", "love wall art", "giclee print", "unframed poster",
                 "cotton paper", "anniversary gift", "bedroom decor"],
        "personalization_questions": scan.personalization_questions(pair),
    }


class AuditTests(unittest.TestCase):
    def check(self, listing, pair="ARIES_LEO"):
        return scan.audit_one("1001", pair, listing)

    def test_valid_listing_passes(self):
        self.assertEqual(self.check(valid())["durum"], "PASS")

    def test_title_schema_fails(self):
        item = valid(); item["title"] = "Aries and Leo print"
        self.assertIn("title_schema", self.check(item)["neden"])

    def test_forbidden_copy_dash_and_spelling_fail(self):
        item = valid(); item["description"] = "OBA-free, bright white — 100-200 years, 12-colour Hahnemuhle."
        reason = self.check(item)["neden"]
        for rule in ("oba_free", "bright_white", "lifetime_years", "12_colour", "long_dash", "hahnemuhle_spelling"):
            self.assertIn(rule, reason)

    def test_tag_rules_fail(self):
        item = valid(); item["tags"] = ["duvar süsü", "this tag is much too long"]
        reason = self.check(item)["neden"]
        self.assertIn("tag_count", reason); self.assertIn("tag_length", reason); self.assertIn("tag_english", reason)

    def test_personalization_instruction_fails(self):
        item = valid(); item["personalization_questions"][2]["instruction"] = "Write a message"
        self.assertIn("personalization_instruction", self.check(item)["neden"])

    def test_same_sign_requires_left_right(self):
        item = valid("LEO_LEO"); item["personalization_questions"][0]["question_text"] = "Name under Leo"
        self.assertIn("personalization_labels", self.check(item, "LEO_LEO")["neden"])

    def test_missing_api_listing_fails_closed(self):
        self.assertEqual(scan.audit_one("1001", "ARIES_LEO", None)["neden"], "api_missing")

    def test_outputs_csv_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "in.json"
            source.write_text(json.dumps([{"listing_id": "1001", "pair": "ARIES_LEO", "listing": valid()}]))
            _, summary = scan.audit(source, root / "CANLI_METIN.csv", root / "summary.json")
            self.assertEqual(summary["pass"], 1); self.assertTrue((root / "CANLI_METIN.csv").exists())


if __name__ == "__main__":
    unittest.main()
