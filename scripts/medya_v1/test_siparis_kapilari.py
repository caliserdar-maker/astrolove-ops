#!/usr/bin/env python3
import unittest

import numpy as np
from PIL import Image

from siparis_dosyasi import leke_kapisi, olcek_kapisi


def olcum(k=1.0, kayma=0.0):
    sc = lambda v: (v + kayma) * k
    return {
        'cap_sol': sc(100), 'cap_sag': sc(101),
        'taban_sol': sc(140), 'taban_sag': sc(140),
        'satir_merkez': sc(120), 'bosluk': [sc(20), sc(21)],
        'sol_isim': [sc(300), sc(700)], 'sonsuz': [sc(710), sc(760)],
        'sag_isim': [sc(770), sc(1200)],
    }


class KapiTesti(unittest.TestCase):
    def test_olcek_dogru_gecer_kaymis_kalir(self):
        self.assertTrue(olcek_kapisi(olcum(3.75), olcum(), 3.75)['gecti'])
        self.assertFalse(olcek_kapisi(olcum(3.75, 3), olcum(), 3.75)['gecti'])

    def test_leke_dogru_gecer_lekeli_kalir(self):
        kaynak = np.full((300, 400, 3), 80, np.uint8)
        maske = np.zeros((80, 100), bool)
        dogru = Image.fromarray(kaynak.copy())
        self.assertTrue(leke_kapisi(dogru, Image.fromarray(kaynak), maske)['gecti'])
        lekeli = kaynak.copy()
        lekeli[:256, :256] = 180
        self.assertFalse(leke_kapisi(Image.fromarray(lekeli), Image.fromarray(kaynak), maske)['gecti'])


if __name__ == '__main__':
    unittest.main()
