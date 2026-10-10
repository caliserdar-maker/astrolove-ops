#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arama_capraz as t


class CaprazTest(unittest.TestCase):
    def test_sayi(self):
        self.assertEqual(t.sayi("1.2k"), 1200)
        self.assertEqual(t.sayi("1,7M"), 1.7e6)
        self.assertEqual(t.sayi("2,4 bin"), 2400)
        self.assertEqual(t.sayi("77,500"), 77500)
        self.assertEqual(t.sayi("932.000"), 932000)
        self.assertEqual(t.sayi("651"), 651)
        self.assertIsNone(t.sayi(""))

    def test_isle(self):
        bos = {k: "" for k in t.SUT}
        r1 = dict(bos, terim="a", **{"MI arama/30g": "20", "MI rekabet": "2.6k", "eRank hacim": "50", "eRank rekabet": "2,700"})
        r2 = dict(bos, terim="b", **{"MI arama/30g": "651", "MI rekabet": "77.2k", "eRank hacim": "700", "eRank rekabet": "80k"})
        r3 = dict(bos, terim="c", **{"eRank hacim": "900"})
        self.assertEqual(t.isle([r1, r2, r3]), 1)
        self.assertIn("CELISKILI", r1["fark oranı"])
        self.assertNotIn("CELISKILI", r2["fark oranı"])
        self.assertEqual(r3["fark oranı"], "MI YOK: karar verilmez")


if __name__ == "__main__":
    unittest.main()
