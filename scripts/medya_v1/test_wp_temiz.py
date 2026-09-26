#!/usr/bin/env python3
"""IS 0015: dokulu slogan maskesi icin ag/Drive gerektirmeyen sentetik testler."""
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tam_set as T


FONT = next((p for p in (
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
) if p.exists()), None)


@unittest.skipUnless(FONT, 'sentetik test fontu bulunamadi')
class WarmParchmentTemizTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(15)
        self.h, self.w = 420, 600
        noise = rng.normal(0, 3, (self.h, self.w, 1))
        self.zemin = np.clip(np.array([222, 207, 177]) + noise, 0, 255).astype(np.uint8)
        self.bant = [280, 310]

    def sloganli(self, dy=31):
        im = Image.fromarray(self.zemin.copy()); d = ImageDraw.Draw(im)
        f = ImageFont.truetype(str(FONT), 31); text = T.TAG
        bb = f.getbbox(text, anchor='ls'); x = round((self.w - (bb[2] - bb[0])) / 2 - bb[0])
        ust = round((sum(self.bant) - (bb[3] - bb[1])) / 2) + dy
        d.text((x, ust - bb[1]), text, font=f, fill=(80, 62, 35), anchor='ls')
        return np.asarray(im)

    @staticmethod
    def kapi(im, zemin):
        fark = np.abs(im.astype(np.int16) - zemin.astype(np.int16)).max(2)
        return int((fark > 20).sum()) == 0

    def test_dokulu_slogan_31_px_kaymayla_temizlenir(self):
        kirli = self.sloganli(31)
        # Eski ton-esikli yol glifin ancak bir bolumunu goruyor.
        gri = kirli.mean(2); mevcut = (gri < 150) & (np.indices(gri.shape)[1] % 3 == 0)
        maske, bilgi = T.slogan_maske(kirli, mevcut, self.bant, T.TAG, str(FONT), 40)
        temiz = kirli.copy(); temiz[maske] = self.zemin[maske]
        self.assertEqual(bilgi['dy'], 31)
        self.assertTrue(self.kapi(temiz, self.zemin))

    def test_dokusuz_edisyon_yolu_degismez(self):
        self.assertNotIn('blue', T.DOKULU)
        self.assertNotIn('modern', T.DOKULU)
        self.assertNotIn('pure_white', T.DOKULU)

    def test_bilincli_birakilan_leke_fail(self):
        temiz = self.zemin.copy(); temiz[80:92, 90:104] = (40, 20, 10)
        self.assertFalse(self.kapi(temiz, self.zemin))


if __name__ == '__main__':
    unittest.main()
