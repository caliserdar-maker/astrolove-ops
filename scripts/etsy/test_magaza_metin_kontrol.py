import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from magaza_metin_kontrol import DEFAULT_FILE, audit, parse


class ShopCopyTests(unittest.TestCase):
    def setUp(self):
        self.drafts = parse(DEFAULT_FILE.read_text(encoding="utf-8"))

    def test_committed_drafts_pass(self):
        self.assertFalse([row for row in audit(self.drafts) if row[1] == "FAIL"])

    def test_long_title_fails(self):
        self.drafts["Shop title"] = "x" * 56
        self.assertEqual(audit(self.drafts)[0][1], "FAIL")

    def test_forbidden_claim_and_dash_fail(self):
        self.drafts["Announcement"] += " Bright white — paper."
        announcement = audit(self.drafts)[1]
        self.assertEqual(announcement[1], "FAIL")
        self.assertIn("long or medium dash", announcement[2])
        self.assertIn("forbidden phrase: bright white", announcement[2])

    def test_missing_digital_facts_fail_shared_requirements(self):
        self.drafts["Digital order message"] = "We care.\nLena & Serdar / AstroLoveArt"
        shared = audit(self.drafts)[-1]
        self.assertEqual(shared[1], "FAIL")
        self.assertIn("digital no instant download statement is missing", shared[2])


if __name__ == "__main__":
    unittest.main()
