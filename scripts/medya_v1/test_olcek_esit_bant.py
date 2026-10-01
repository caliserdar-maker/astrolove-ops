#!/usr/bin/env python3
"""Olcek kapisi ESIT BANT olcumu (1 Eki, isim on testi: isim bagimli olcek FAIL kok nedeni).

Isim plakalari uretimdeki plaka_ss ile (gercek font, SS=4) 2400 ve 3x cizilir; hi-res yerlesim 2400 kutle
merkezi x k (olcekli kutle yerlesimi). Dogal olcumde MAXIMILIAN capi 2400'de ~1 px buyuk cikar (2400 plakasi
1 px kutu bulanik, %0.2 kutle kenari disari kayar) -> dogru cikti FAIL. Esit bantta:
- dogru cikti PASS,
- sol isim 1.2 px (2400 birimi) yatay ya da dikey kaydirilirsa FAIL (gercek kayma korunur).
kisisel-v1 modulleri gerekir: KISISEL_YOL=<kisisel-v1>/scripts/kisisel (yoksa atlanir).
"""
import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import pilot12  # noqa: F401
    import edisyon_uret  # noqa: F401
    import siparis_dosyasi as sd
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

BANT = (2244, 2356)
IY = 2290.0
PROF = np.linspace(np.array((231, 167, 48), np.float32), np.array((150, 100, 30), np.float32), 50)


def kutle(pl):
    a = np.asarray(pl, np.float32)[..., 3]
    x0, x1 = sd._uc(a.sum(axis=0)); t, b = sd._uc(a.sum(axis=1))
    return (x0 + x1) / 2, (t + b) / 2


def sahne(k, isimler, yer0=None, kay=(0.0, 0.0)):
    """Sol isim, sonsuz yerine tek kume ('O'), sag isim; hi-res'te her oge 2400 kutle merkezi x k'ya konur."""
    W, H = int(round(2400 * k)), int(round(2700 * k))
    t = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    pl = [sd.plaka_ss(isimler[0], PROF, 0, 1.0, tam=115 * k)[0], sd.plaka_ss('O', PROF, 0, 1.0, tam=90 * k)[0],
          sd.plaka_ss(isimler[1], PROF, 0, 1.0, tam=115 * k)[0]]
    yer = []
    for i, p in enumerate(pl):
        cx, cy = kutle(p)
        if yer0 is None:
            px, py = int(round((300.0, 1120.0, 1400.0)[i])), int(round(IY - p.height / 2))
            yer.append((px + cx, py + cy))
        else:
            dx, dy = kay if i == 0 else (0.0, 0.0)
            px, py = int(round((yer0[i][0] + dx) * k - cx)), int(round((yer0[i][1] + dy) * k - cy))
        t.alpha_composite(p, (px, py))
    return t.convert('RGB'), yer


@unittest.skipUnless(HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class EsitBantTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sd._mod = lambda ad, _m=sd._mod: sys.modules.get(ad) or _m(ad)
        cls.isim = ('MAXIMILIAN', 'JO')
        sd.olcek_kur(2400)
        cls.p0, cls.yer0 = sahne(1.0, cls.isim)
        cls.k = 3.0
        cls.p1, _ = sahne(cls.k, cls.isim, cls.yer0)

    def test_dogal_olcum_cap_farkini_yer_sanar(self):
        r = sd.olcek_kapisi_baski(self.p1, self.p0, BANT)
        self.assertGreater(abs(r['fark']['cap_sol']), 0.7, r['fark'])

    def test_esit_bant_dogru_ciktiyi_gecirir(self):
        r = sd.olcek_kapisi_baski(self.p1, self.p0, BANT, esit=True)
        self.assertTrue(r['gecti'], r['fark'])
        self.assertLess(abs(r['fark']['cap_sol']), 0.5, r['fark'])
        self.assertTrue(r.get('esit_bant'))

    def test_esit_bant_yatay_kaymayi_yakalar(self):
        p, _ = sahne(self.k, self.isim, self.yer0, kay=(1.2, 0.0))
        r = sd.olcek_kapisi_baski(p, self.p0, BANT, esit=True)
        self.assertFalse(r['gecti'], r['fark'])

    def test_esit_bant_dikey_kaymayi_yakalar(self):
        p, _ = sahne(self.k, self.isim, self.yer0, kay=(0.0, 1.2))
        r = sd.olcek_kapisi_baski(p, self.p0, BANT, esit=True)
        self.assertFalse(r['gecti'], r['fark'])


if __name__ == '__main__':
    unittest.main()
