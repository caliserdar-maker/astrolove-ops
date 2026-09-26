import json
import tempfile
import unittest
from pathlib import Path

import seo_puan as seo


def listing(**changes):
    data = {"listing_id": 1, "title": "Aries and Leo Zodiac Wall Art Couple Print",
            "description": "Aries and Leo Zodiac Wall Art for couples.\n\nMuseum quality natural white cotton paper.",
            "tags": ["aries leo", "zodiac wall art", "couple print", "astrology decor"]}
    data.update(changes)
    return ("1", "ARIES_LEO", data)


class SeoPuanTest(unittest.TestCase):
    def rule(self, name, **changes):
        return seo.score_rows([listing(**changes)])[0][0][name]

    def test_correct_listing_passes_every_rule(self):
        row = seo.score_rows([listing()])[0][0]
        self.assertEqual([row[key] for key in seo.WEIGHTS], ["PASS"] * 6)
        self.assertEqual(row["puan"], 100)

    def test_keyword_must_be_in_first_forty_characters(self):
        self.assertEqual(self.rule("ilk40", title="A thoughtful personalized gift for home Aries Leo Zodiac Art"), "FAIL")

    def test_long_tail_ratio(self):
        self.assertEqual(self.rule("long_tail", tags=["aries", "leo", "zodiac", "art"]), "FAIL")

    def test_title_tag_overlap(self):
        self.assertEqual(self.rule("ortusme", tags=["romantic gift", "celestial decor"]), "FAIL")

    def test_first_paragraph_keyword(self):
        description = "A meaningful gift.\n\nAries and Leo Zodiac Wall Art."
        self.assertEqual(self.rule("aciklama", description=description), "FAIL")

    def test_identical_titles_are_cannibalization(self):
        rows, _ = seo.score_rows([listing(), listing(listing_id=2)])
        self.assertTrue(all(row["kannibalizasyon"] == "FAIL" for row in rows))

    def test_storewide_repeated_tags_reduce_diversity(self):
        tags = ["zodiac wall art", "couple print", "astrology decor", "romantic gift"]
        records = [listing(tags=tags), ("2", "TAURUS_GEMINI", listing(listing_id=2, title="Taurus and Gemini Zodiac Wall Art Couple Print", description="Taurus and Gemini Zodiac Wall Art for couples.", tags=tags)[2])]
        rows, _ = seo.score_rows(records)
        self.assertTrue(all(row["cesitlilik"] == "FAIL" for row in rows))

    def test_writes_outputs_and_three_safe_suggestions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "raw.json"
            source.write_text(json.dumps({"results": [listing()[2]]}), encoding="utf-8")
            rows = seo.audit(source, root / "SEO_PUAN.csv", root / "OZET.md")
            self.assertTrue((root / "SEO_PUAN.csv").exists() and (root / "OZET.md").exists())
            advice = rows[0]["oneriler"].split(" | ")
            self.assertEqual(len(advice), 3)
            self.assertFalse(any("-" in item or "OBA" in item or "bright white" in item.lower() for item in advice))


if __name__ == "__main__":
    unittest.main()
