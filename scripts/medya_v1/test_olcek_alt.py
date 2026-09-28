#!/usr/bin/env python3
"""Olcek kapisi alt piksel olcumu (28 Eyl hata kontrolu, baski-duzelt).

Sentetik isim satiri AYNI fiziksel geometride 2400 ve 3307 px genislikte cizilir
(yazi boyu ve konum hedef cozunurlukte tam sayiya yuvarlanir, uretimdeki gibi).
Pencere sinirina yakin bir yildiz ve bandin altina inen bir kuyruk vardir.
- Eski olcum (satir_olc, hi-res'te pay=10 olceklenmez) dogru ciktiyi REDDEDER.
- Yeni olcum (satir_olc_alt) dogru ciktiyi GECIRIR, 2 px kaymis ciktiyi REDDEDER.
kisisel-v1 modulleri gerekir: KISISEL_YOL=<kisisel-v1>/scripts/kisisel (yoksa atlanir).
"""
import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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

BANT = (2244, 2331)             # CANCER_LIBRA 11x14 isim_bant (eski isimde kuyruk yok)
Y_MERKEZ = 2288.0
YILDIZ = (1480.0, 2235.5, 2.2)  # J'nin solunda, 2400 penceresinde, hi-res penceresinin disinda


def poster(k, kayma=0.0, font_yol=None, S=4):
    """4x super ornekleme + alan ortalamasi: iki olcekte FIZIKSEL olarak ayni cizim."""
    W, H = int(round(2400 * k)), int(round(2500 * k))
    q = k * S
    im = Image.new('RGB', (W * S, H * S), (8, 10, 30))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font_yol, int(round(117 * q)))
    for metin, x in (('EMILY', 560.0), ('JAMES', 1500.0 + kayma)):
        kutu = d.textbbox((0, 0), metin, font=f)
        px = int(round(x * q)) - kutu[0]
        py = int(round(Y_MERKEZ * q - (kutu[3] + kutu[1]) / 2))
        d.text((px, py), metin, font=f, fill=(231, 167, 48))
    for cx in (1215, 1290):                                   # sonsuz: iki halka
        d.ellipse([(cx - 38) * q, (Y_MERKEZ - 22) * q, (cx + 38) * q, (Y_MERKEZ + 22) * q],
                  outline=(231, 167, 48), width=int(round(7 * q)))
    # J kuyrugu: bandin altina iner (yeni isimde inen harf)
    d.rectangle([1506 * q, 2320 * q, 1514 * q - 1, 2338 * q - 1], fill=(231, 167, 48))
    x, y, r = YILDIZ
    d.ellipse([(x - r) * q, (y - r) * q, (x + r) * q - 1, (y + r) * q - 1], fill=(255, 250, 235))
    return im.resize((W, H), Image.BOX)


@unittest.skipUnless(HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class OlcekAltTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = str(Path(KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf')
        cls.k = 3307 / 2400.0
        cls.p0 = poster(1.0, font_yol=cls.font)
        cls.p1 = poster(cls.k, font_yol=cls.font)

    def eski(self, p1):
        eu = sd._mod('edisyon_uret')
        bant1 = [int(round(v * self.k)) for v in BANT]
        sd.olcek_kur(p1.width)
        g1 = eu.satir_olc(np.asarray(p1).astype(np.float32), bant1)
        sd.olcek_kur(2400)
        g0 = eu.satir_olc(np.asarray(self.p0).astype(np.float32), list(BANT))
        return sd.olcek_kapisi(g1, g0, self.k)

    def test_eski_olcum_dogru_ciktiyi_reddeder(self):
        r = self.eski(self.p1)
        self.assertFalse(r['gecti'], r)

    def test_yeni_olcum_dogru_ciktiyi_gecirir(self):
        r = sd.olcek_kapisi_baski(self.p1, self.p0, BANT)
        self.assertTrue(r['gecti'], r)
        self.assertLess(r['konum_fark_px'], 0.6, r)

    def test_yeni_olcum_kaymis_ciktiyi_reddeder(self):
        kaymis = poster(self.k, kayma=2.0, font_yol=self.font)
        r = sd.olcek_kapisi_baski(kaymis, self.p0, BANT)
        self.assertFalse(r['gecti'], r)

    def test_blue_buyutulmus_2400_gecer(self):
        # Blue: 2400 render baski boyuna buyutulur; kapi artik None degil, olcer.
        buyuk = self.p0.resize(self.p1.size, Image.LANCZOS)
        r = sd.olcek_kapisi_baski(buyuk, self.p0, BANT)
        self.assertTrue(r['gecti'], r)


if __name__ == '__main__':
    unittest.main()
