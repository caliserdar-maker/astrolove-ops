#!/usr/bin/env python3
"""Kisisellestirme cap ve Turkce buyuk-harf sozlesmesi regresyon testleri."""
import unittest

from giris_dogrula import buyut
from kisisel_pilot import FONT_DIR, cap_icin_boyut
from pilot6 import ISIM_FONT, ISIM_W


class GeometryContractTest(unittest.TestCase):
    def test_turkish_uppercase(self):
        self.assertEqual(buyut("Deniz", "TR"), "DENİZ")
        self.assertEqual(buyut("çiğdem", "TR"), "ÇİĞDEM")
        self.assertEqual(buyut("ışıl", "TR"), "IŞIL")
        self.assertEqual(buyut("Deniz", "US"), "DENIZ")

    def test_legacy_selector_stays_unchanged_for_blue_locks(self):
        fp = FONT_DIR / ISIM_FONT
        self.assertEqual(cap_icin_boyut(fp, "SERDAR", 89, ISIM_W), 119)
        self.assertEqual(cap_icin_boyut(fp, "LENA", 89, ISIM_W), 119)


if __name__ == "__main__":
    unittest.main()
