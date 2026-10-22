#!/usr/bin/env python3
"""alt_metin_kontrol birim testleri."""

import unittest

from scripts.etsy.alt_metin_kontrol import denetle


class AltMetinKontrolTest(unittest.TestCase):
    def test_gecerli_farkli_ve_ayni_burc(self):
        self.assertEqual(denetle({"1": "Aries and Leo art on Hahnemühle paper"}, "ARIES_LEO")[0][1], "PASS")
        self.assertEqual(denetle({"1": "Leo and Leo zodiac couple print"}, "LEO_LEO")[0][1], "PASS")

    def test_tum_kurallari_raporlar(self):
        metin = "Aries and Cancer on Hahnemuhle bright white 100-200 years — 12-colour OBA-free " + "x" * 180 + " "
        _, durum, hatalar = denetle({"5": metin}, "ARIES_LEO")[0]
        self.assertEqual(durum, "FAIL")
        birlesik = " | ".join(hatalar)
        for beklenen in ("250", "sonda bosluk", "tire", "Hahnemühle", "OBA-free", "bright white",
                         "omur yili", "12-colour", "Leo", "Cancer"):
            self.assertIn(beklenen, birlesik)

    def test_string_olmayan_deger_fail(self):
        self.assertEqual(denetle({"1": None}, "ARIES_LEO")[0][1], "FAIL")


if __name__ == "__main__":
    unittest.main()
