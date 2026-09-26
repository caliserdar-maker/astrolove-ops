#!/usr/bin/env python3
"""IS_0003 onayli POD sablon kilitlari."""

import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import pod_listing_create as create  # noqa: E402
import pod_referans_kiyas as compare  # noqa: E402


class PodSablonTest(unittest.TestCase):
    def test_approved_title(self):
        title, _, _, _ = create.build_listing("ARIES_LEO", create.load_template())
        self.assertEqual(
            title,
            "Aries and Leo Zodiac Wall Art, Personalized Couple Print with Names and Message, Unframed",
        )

    def test_three_required_personalization_fields(self):
        questions = create.personalization_questions("ARIES_LEO")
        self.assertEqual([q["question_text"] for q in questions], ["Name under Aries", "Name under Leo", "Your message"])
        self.assertEqual([q["instruction"] for q in questions], [create.NAME_INSTRUCTION, create.NAME_INSTRUCTION, create.MESSAGE_INSTRUCTION])
        self.assertEqual([q["max_allowed_characters"] for q in questions], [11, 11, 35])
        self.assertTrue(all(q["required"] and q["question_type"] == "text" for q in questions))
        self.assertFalse(any("order" in q["question_text"].lower() for q in questions))

    def test_same_sign_uses_left_and_right(self):
        questions = create.personalization_questions("LEO_LEO")
        self.assertEqual([q["question_text"] for q in questions[:2]], ["Left name", "Right name"])

    def test_missing_personalization_fails_closed(self):
        with self.assertRaisesRegex(SystemExit, "ilan olusturulmadi"):
            create.validate_personalization(create.personalization_questions("ARIES_LEO")[:2])
        malformed = create.personalization_questions("ARIES_LEO")
        malformed[2]["instruction"] = ""
        with self.assertRaisesRegex(SystemExit, "ilan olusturulmadi"):
            create.validate_personalization(malformed)

    def test_russian_payload_keeps_english_tags(self):
        _, english, _, _ = create.build_listing("ARIES_LEO", create.load_template())
        _, russian_payload_tags, _, _ = create.build_ru("ARIES_LEO", create.load_ru_template())
        self.assertEqual(russian_payload_tags, english)
        self.assertTrue(all(tag.isascii() for tag in russian_payload_tags))

    def test_legacy_seo_builder_is_locked(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "seo" / "pod_seo_v2_build.py"), "--out", "/tmp/should-not-exist.json"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ESKI - kullanma", result.stderr + result.stdout)

    def test_compare_canon_is_fixed_schema(self):
        canon = compare.canonical_schema("Aries", "Leo")
        self.assertEqual(canon["title"], create.TITLE.format(S1="Aries", S2="Leo"))
        self.assertEqual(canon["questions"], create.personalization_questions("ARIES_LEO"))

    def test_document_has_no_long_dashes_and_marks_unapproved_claims(self):
        text = (ROOT / "docs" / "POD_LISTING_TEMPLATE.md").read_text(encoding="utf-8")
        self.assertNotIn("—", text)
        self.assertNotIn("–", text)
        self.assertGreaterEqual(text.count("<!-- IZINLI LISTE DISI:"), 8)


if __name__ == "__main__":
    unittest.main()
