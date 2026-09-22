#!/usr/bin/env python3
"""Kisisellestirme cap ve Turkce buyuk-harf sozlesmesi regresyon testleri."""
import unittest

import numpy as np

from edisyon_uret import profil_farki
from giris_dogrula import buyut
from kisisel_pilot import FONT_DIR, cap_icin_boyut
from pilot6 import ISIM_FONT, ISIM_W
from pilot12 import plaka


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

    def test_renderer_plate_preserves_source_profile(self):
        profil = np.asarray([
            [112, 74, 30], [164, 116, 48], [224, 188, 102], [138, 92, 36]
        ], dtype=np.float32)
        p = plaka("SERDAR", profil, 89)[0]
        a = np.asarray(p).astype(np.float32)
        m = a[..., 3] > 160
        uretilen = np.asarray([
            np.median(a[y, m[y], :3], axis=0)
            for y in range(a.shape[0]) if m[y].sum() >= 3
        ], dtype=np.float32)
        self.assertLessEqual(profil_farki(uretilen, profil), 5.0)


if __name__ == "__main__":
    unittest.main()
