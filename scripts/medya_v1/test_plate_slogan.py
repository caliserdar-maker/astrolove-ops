#!/usr/bin/env python3
"""Plate slogan kapisi (28 Eyl, baski-duzelt): SAHTE veriyle.

Sentetik sayfa: sembol, isim satiri (3 kume) ve slogan. Temiz plate = zemin; kirli plate =
zemin + AYNI slogan (25 Eyl medyan plate'lerinde oldugu gibi). Koyu duz zemin (Blue/Black)
ve dokulu acik zemin (Warm Parchment benzeri) icin: temiz -> PASS, kirli -> FAIL.
kisisel-v1 modulleri gerekir: KISISEL_YOL=<kisisel-v1>/scripts/kisisel (yoksa atlanir).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import edisyon_uret  # noqa: F401
    import siparis_dosyasi as sd
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

W, H = 2400, 3048


def zemin(koyu, doku):
    rng = np.random.default_rng(7)
    if koyu:
        a = np.zeros((H, W, 3), np.float32) + (4, 8, 30)
    else:
        a = np.zeros((H, W, 3), np.float32) + (222, 193, 138)
    if doku:                                     # parsomen: dusuk frekans + ince lif
        dus = rng.normal(0, 1, (H // 40, W // 40)).astype(np.float32)
        dus = np.asarray(Image.fromarray(dus).resize((W, H), Image.BICUBIC))
        a += (dus * 9)[..., None] + rng.normal(0, 3, (H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def slogan(im, renk, font):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, 62)
    d.text((1200, 2650), 'Two Souls  One Bond', font=f, fill=renk, anchor='mm')


def sayfa(koyu, doku, font):
    renk = (231, 167, 48) if koyu else (120, 70, 25)
    im = zemin(koyu, doku)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, 117)
    d.ellipse([700, 1960, 890, 2120], outline=renk, width=12)          # semboller
    d.ellipse([1510, 1960, 1700, 2120], outline=renk, width=12)
    d.text((780, 2290), 'EMILY', font=f, fill=renk, anchor='mm')        # isim satiri
    d.text((1200, 2290), 'oo', font=f, fill=renk, anchor='mm')
    d.text((1620, 2290), 'JAMES', font=f, fill=renk, anchor='mm')
    slogan(im, renk, font)
    return im.filter(ImageFilter.GaussianBlur(0.6)), renk


@unittest.skipUnless(HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class PlateSloganTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = str(Path(KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf')
        cls.tmp = Path(tempfile.mkdtemp())

    def durum(self, koyu, doku, ed):
        im, renk = sayfa(koyu, doku, self.font)
        yol = self.tmp / f'sayfa_{koyu}_{doku}.png'
        im.save(yol)
        temiz = zemin(koyu, doku)
        kirli = zemin(koyu, doku)
        slogan(kirli, renk, self.font)
        kirli = kirli.filter(ImageFilter.GaussianBlur(0.6))
        sonuc = {}
        for ad, pl in (('temiz', temiz), ('kirli', kirli)):
            p = self.tmp / f'plate_{ad}_{koyu}_{doku}.png'
            pl.save(p)
            sonuc[ad] = sd.plate_slogan_kapisi(yol.read_bytes(), p, ed)
        return sonuc

    def test_koyu_duz_zemin(self):
        r = self.durum(True, False, 'black')
        self.assertTrue(r['temiz']['gecti'], r['temiz'])
        self.assertFalse(r['kirli']['gecti'], r['kirli'])

    def test_blue_esigi(self):
        r = self.durum(True, False, 'blue')
        self.assertTrue(r['temiz']['gecti'], r['temiz'])
        self.assertFalse(r['kirli']['gecti'], r['kirli'])

    def test_dokulu_acik_zemin(self):
        r = self.durum(False, True, 'vintage')
        self.assertTrue(r['temiz']['gecti'], r['temiz'])
        self.assertFalse(r['kirli']['gecti'], r['kirli'])

    def test_paralel_cagrilar_karismaz(self):
        # 1 Eki: paralel iscilerin ortak gecici dosyasi birbirinin sayfasini olcturuyordu. Ayni anda
        # temiz (slogan var) ve slogansiz sayfa: her cagri kendi sonucunu vermeli, gecici dosya kalmamali.
        from concurrent.futures import ThreadPoolExecutor
        im, renk = sayfa(True, False, self.font)
        bos = zemin(True, False)
        temiz = self.tmp / 'plate_paralel.png'; zemin(True, False).save(temiz)
        import io as _io
        def bayt(i):
            b = _io.BytesIO(); i.save(b, 'PNG'); return b.getvalue()
        isler = [bayt(im), bayt(bos)] * 4
        with ThreadPoolExecutor(8) as h:
            r = list(h.map(lambda b: sd.plate_slogan_kapisi(b, temiz, 'black')['gecti'], isler))
        self.assertEqual(r, [True, False] * 4)
        self.assertEqual(list(sd.W.glob('_plate_kapisi_kaynak*')), [])


if __name__ == '__main__':
    unittest.main()
