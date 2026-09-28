#!/usr/bin/env python3
"""plate_yenile.melez_plate: SAHTE veri. Dokulu (parsomen) ve koyu yildizli zemin.

HAM = zemin + slogan (25 Eyl medyani gibi); Canva = ayni zemin (slogan katmani gizli), 2 px
kaymali ve hafif farkli tonlu (ayri disa aktarim). Beklenen: slogan gliflerinde yeni plate
zemine esit (|fark| p99 kucuk), glif disi HAM'la ayni, plate_uret temizlik kapilari PASS.
"""
import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import plate_yenile as py
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

W, H = 2400, 3048


def zemin(koyu, tohum=3, vinyet=0.0):
    rng = np.random.default_rng(tohum)
    a = np.zeros((H, W, 3), np.float32) + ((4, 8, 30) if koyu else (222, 193, 138))
    if vinyet:                                        # parsomen vinyeti: kenarlar koyu
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
        a -= (vinyet * r ** 2)[..., None]
    dus = rng.normal(0, 1, (H // 40, W // 40)).astype(np.float32)
    dus = np.asarray(Image.fromarray(dus).resize((W, H), Image.BICUBIC))
    a += (dus * (2 if koyu else 9))[..., None]
    if koyu:                                          # yildizlar
        for _ in range(2500):
            y, x = rng.integers(0, H), rng.integers(0, W)
            a[y:y + 2, x:x + 2] = 230
    else:
        a += rng.normal(0, 3, (H, W, 1)).astype(np.float32)
    return np.clip(a, 0, 255).astype(np.uint8)


def slogan_ekle(a, renk, font, punto=64):
    im = Image.fromarray(a)
    ImageDraw.Draw(im).text((1200, 2650), 'Two Souls  One Bond', anchor='mm', fill=renk,
                            font=ImageFont.truetype(font, punto))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.5)) if False else im)


@unittest.skipUnless(HAZIR, 'plate_yenile ice aktarilamadi (KISISEL_YOL)')
class PlateYenileTesti(unittest.TestCase):
    font = str(Path(KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf') if KY else ''

    def kos(self, koyu, renk, vinyet=0.0, punto=64):
        z = zemin(koyu, vinyet=vinyet)
        ham = slogan_ekle(z, renk, self.font, punto)
        canva = np.roll(z, (2, -2), axis=(0, 1)).astype(np.int16) + 3      # ayri disa aktarim
        canva = np.clip(canva, 0, 255).astype(np.uint8)
        yeni, rap = py.melez_plate(ham, canva)
        self.assertIsNotNone(yeni, rap)
        glif = np.abs(ham.astype(np.int16) - z.astype(np.int16)).max(axis=2) > 20
        kalan = np.abs(yeni.astype(np.int16) - z.astype(np.int16)).max(axis=2)[glif]
        self.assertLess(float(np.percentile(kalan, 99)), 12, rap)
        self.assertTrue(rap['temizlik_kapisi']['gecti'], rap['temizlik_kapisi'])
        disari = ~np.pad(glif, 0)
        disari[2500:2800] = False
        self.assertTrue((yeni[disari] == ham[disari]).all())
        return rap

    def test_parsomen(self):
        self.kos(False, (120, 70, 25))

    def test_parsomen_vinyetli(self):
        # 28 Eyl: tam en hayalet olcumu vinyeti hayalet sayiyordu (WP taban 26-28); yerel olcum
        # punto 96 = gercek slogan (8x10 glif yuksekligi 73 px @2400)
        rap = self.kos(False, (120, 70, 25), vinyet=60.0, punto=96)
        self.assertFalse(rap['temizlik_kapisi_tam_en']['gecti'], rap['temizlik_kapisi_tam_en'])

    def test_koyu_yildizli(self):
        self.kos(True, (231, 167, 48))


if __name__ == '__main__':
    unittest.main()
