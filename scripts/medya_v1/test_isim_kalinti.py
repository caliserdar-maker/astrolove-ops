#!/usr/bin/env python3
"""Isim bandi kalintisi (GIFT_9518 bulgusu, 29 Eyl): SAHTE veri.

Kaynak = plate + eski burc yazisi (yeni isimlerden genis); render tabani (temiz_a) eski yazinin
ince uclarini tasir (asindirilmis silme maskesi), yeni isimler + sonsuzluk uzerine cizilir;
yeni oge maskesi = poster_kur yeni_genis (3 px):
- eski yol (temizliksiz): isim_kalinti_kapisi FAIL
- isim_bandi_temizle ile: PASS, yeni isimler ve sonsuzluk korunur, eski murekkep kalmaz.
Koyu (Deep Black / Midnight Blue) ve acik (Pure White) zemin.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import cv2
    import siparis_dosyasi as sd
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

W, H = 2400, 3000
ALTIN = (214, 170, 92)
OLCUM = {'sembol_bant': [2060, 2160], 'isim_bant': [2200, 2290], 'tag_bant': [2560, 2640]}


def zemin(koyu):
    rng = np.random.default_rng(5)
    a = np.zeros((H, W, 3), np.float32) + ((6, 9, 28) if koyu else (246, 244, 240))
    a += rng.normal(0, 1.0, (H, W, 1))
    return np.clip(a, 0, 255).astype(np.uint8)


def yaz(a, metinler, font):
    im = Image.fromarray(a.copy())
    d = ImageDraw.Draw(im)
    for x, t in metinler:
        d.text((x, 2245), t, anchor='mm', fill=ALTIN, font=font)
    return np.asarray(im)


@unittest.skipUnless(HAZIR, 'siparis_dosyasi ice aktarilamadi')
class IsimKalintiTesti(unittest.TestCase):
    font = str(Path(KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf') if KY else ''

    def kos(self, koyu):
        f = ImageFont.truetype(self.font, 88)
        pl = zemin(koyu)
        eski = [(620, 'ARIES'), (1200, '~'), (1780, 'SCORPIO')]
        yeni = [(820, 'LIZ'), (1200, '~'), (1580, 'ZACH')]
        A = yaz(pl, eski, f).astype(np.float32)
        Plf = pl.astype(np.float32)
        ek = np.abs(A - Plf).max(axis=2) > 12
        # render tabani (poster_kur temiz_a): eski oge maskesi 2 px asindirilmis silinmis -> ince
        # uclar tabanda kalir (GIFT_9518'de olculen durum); yeni isimler bunun uzerine cizilir
        sil = cv2.erode(ek.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        temiz = np.where(sil[..., None], Plf, A)
        yeni_im = yaz(np.zeros_like(pl), yeni, f)
        yk = yeni_im.max(axis=2) > 12
        P = np.where(yk[..., None], yaz(pl, yeni, f).astype(np.float32), temiz)
        Y = cv2.dilate(yk.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
        M = (sil | Y).astype(np.float32)
        Mf = cv2.GaussianBlur(M, (0, 0), 2.0)[..., None]
        eski_out = A * (1 - Mf) + P * Mf
        with tempfile.TemporaryDirectory() as t:
            yol = Path(t) / 'plate.png'
            Image.fromarray(pl).save(yol)
            b_eski = Image.fromarray(np.clip(eski_out, 0, 255).astype(np.uint8))
            k_eski = sd.isim_kalinti_kapisi(b_eski, yol, Y, OLCUM)
            yeni_out, bilgi = sd.isim_bandi_temizle(eski_out, A, Y, yol, OLCUM)
            b_yeni = Image.fromarray(np.clip(yeni_out, 0, 255).astype(np.uint8))
            k_yeni = sd.isim_kalinti_kapisi(b_yeni, yol, Y, OLCUM)
        self.assertFalse(k_eski['gecti'], k_eski)
        self.assertGreater(k_eski['kalinti_sayisi'], 0)
        self.assertTrue(bilgi['uygulandi'], bilgi)
        self.assertTrue(k_yeni['gecti'], k_yeni)
        Bn = np.asarray(b_yeni)
        Be = np.clip(eski_out, 0, 255).astype(np.uint8)
        # yeni isimler ve sonsuzluk: temizlik yeni oge maskesine DOKUNMAZ
        self.assertTrue((Bn[Y] == Be[Y]).all())
        # bant disi dokunulmadi
        dis = np.ones((H, W), bool); dis[2100:2400] = False
        self.assertTrue((Bn[dis] == Be[dis]).all())
        # eski murekkep (yeni murekkep disi) plate'e dondu
        kalan = np.abs(Bn.astype(np.int16) - pl.astype(np.int16)).max(axis=2)[ek & ~(
            cv2.dilate(Y.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)]
        self.assertLess(float(np.percentile(kalan, 99)), 4)
        return k_eski, k_yeni

    def test_koyu(self):
        self.kos(True)

    def test_acik(self):
        self.kos(False)


if __name__ == '__main__':
    unittest.main()
