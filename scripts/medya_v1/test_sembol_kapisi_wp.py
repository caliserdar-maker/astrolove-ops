#!/usr/bin/env python3
"""WP sembol olcutunun doku regresyonlari (harici veri/bagimlilik yok)."""
import unittest

import numpy as np

from a1_poster import SEMBOL_ESIK, _doku_karsitlik, _sembol_gecti


def ornek(tohum, zemin, murekkep=(72, 48, 25)):
    rng = np.random.default_rng(tohum)
    a = np.full((80, 100, 3), zemin, np.float32)
    # WP lifinin p99'u yaklasik 45; iki ayri taramada doku birebir ayni degil.
    a += rng.normal(0, 11, a.shape[:2])[:, :, None]
    m = np.zeros(a.shape[:2], bool)
    m[25:55, 42:47] = True
    m[25:30, 35:54] = True
    a[m] = np.asarray(murekkep) + rng.normal(0, 2, (m.sum(), 1))
    return a, m


class WPSembolKapisiTesti(unittest.TestCase):
    def test_bes_edisyon_iki_ornek_doku_degisince_gecer(self):
        """Olculen esik 6: 10 dogru ornekte azami karsitlik farki < 3."""
        zeminler = ((28, 35, 58), (20, 20, 20), (245, 245, 242),
                    (235, 224, 199), (218, 184, 126))
        farklar = []
        for i, zemin in enumerate(zeminler):
            for tekrar in range(2):
                kaynak, m = ornek(10 * i + tekrar, zemin)
                yeni, _ = ornek(100 + 10 * i + tekrar, zemin)
                fark = np.abs(_doku_karsitlik(kaynak, m) -
                              _doku_karsitlik(yeni, m)).mean()
                farklar.append(float(fark))
        self.assertEqual(len(farklar), 10)
        self.assertLessEqual(max(farklar), 6.0)

    def test_eksik_ve_lekeli_sembol_kalir(self):
        kaynak, m = ornek(1, (218, 184, 126))
        eksik, _ = ornek(2, (218, 184, 126))
        eksik[m] = (218, 184, 126)
        lekeli, _ = ornek(3, (218, 184, 126), murekkep=(125, 95, 65))
        for kotu in (eksik, lekeli):
            fark = np.abs(_doku_karsitlik(kaynak, m) -
                          _doku_karsitlik(kotu, m)).mean()
            self.assertGreater(fark, 6.0)
            self.assertFalse(_sembol_gecti(fark, 0, 0, 1.0, SEMBOL_ESIK))

    def test_kaymis_ve_eksik_maske_kalir(self):
        self.assertFalse(_sembol_gecti(0.0, 2, 0, 1.0, SEMBOL_ESIK))
        self.assertFalse(_sembol_gecti(0.0, 0, 0, 0.75, SEMBOL_ESIK))


if __name__ == '__main__':
    unittest.main()
