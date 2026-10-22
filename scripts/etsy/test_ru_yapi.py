#!/usr/bin/env python3
"""POD RU metninin onayli EN metniyle yapisal esligini denetler."""
import re
import unittest

from pod_listing_create import build_ru, fill_digital, load_ru_template
from pod_listing_update import build, load_template


LONG_DASHES = "\u2013\u2014"
BRANDS = ("Hahnemühle Photo Rag", "AstroLove")


def paragraphs(text):
    return [part for part in text.split("\n\n") if part.strip()]


def numeric_tokens(text):
    """Metindeki sayilari siralariyla dondurur (olcu carpani ayri sayilardir)."""
    return re.findall(r"\d+", text)


class RuStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        en_template = fill_digital(load_template(), None, "en")
        cls.en_tags, cls.en, _ = build("ARIES_LEO", en_template)
        _, cls.ru_tags, cls.ru, _ = build_ru("ARIES_LEO", load_ru_template())

    def test_paragraph_and_bullet_structure_matches_english(self):
        en_paragraphs = paragraphs(self.en)
        ru_paragraphs = paragraphs(self.ru)
        self.assertEqual(len(ru_paragraphs), len(en_paragraphs))
        self.assertEqual(
            [sum(line.startswith("- ") for line in p.splitlines()) for p in ru_paragraphs],
            [sum(line.startswith("- ") for line in p.splitlines()) for p in en_paragraphs],
        )

    def test_numbers_and_required_names_match_english(self):
        self.assertEqual(numeric_tokens(self.ru), numeric_tokens(self.en))
        self.assertIn("308 gsm", self.ru)
        self.assertIn("16 РАЗМЕРОВ", self.ru)
        for brand in BRANDS:
            self.assertEqual(self.ru.count(brand), self.en.count(brand))

    def test_no_long_or_medium_dash(self):
        for dash in LONG_DASHES:
            self.assertNotIn(dash, self.ru)

    def test_russian_translation_keeps_english_tags(self):
        self.assertEqual(self.ru_tags, self.en_tags)
        self.assertTrue(all(tag.isascii() for tag in self.ru_tags))


if __name__ == "__main__":
    unittest.main()
