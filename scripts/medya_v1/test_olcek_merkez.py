#!/usr/bin/env python3
"""Olcek kapisi KUTLE MERKEZI konumu (2 Eki, OLCEK_AL_TANI: CAGLA MB 24x36 bosluk_sag 1.28).

Sahne test_olcek_esit_bant ile ayni (plaka_ss, 2400 ve 3x). Sag ismin sol ucuna 1.2 px (2400 birimi) genisliginde
ince murekkep eklenir (tek glif kenari genisler, kelime yerinde): uc kuantil konumu bunu bosluk kaymasi sanar
(OLCEK_MERKEZ=0 FAIL), kutle merkezi konumu PASS verir, uc kenar kenar olcutunde (<= 2 px) kalir.
Gercek kayma korunur: sag isim 1.2 px yatay kaydirilirsa FAIL.
kisisel-v1 modulleri gerekir: KISISEL_YOL=<kisisel-v1>/scripts/kisisel (yoksa atlanir).
"""
import sys
import unittest
from pathlib import Path

from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_olcek_esit_bant as te  # noqa: E402
from test_olcek_esit_bant import BANT, HAZIR, IY, sahne  # noqa: E402

sd = te.sd if HAZIR else None
KAY = 1.2


@unittest.skipUnless(HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class OlcekMerkezTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        te.EsitBantTesti.setUpClass()
        cls.p0, cls.yer0, cls.k, cls.isim = te.EsitBantTesti.p0, te.EsitBantTesti.yer0, 3.0, te.EsitBantTesti.isim
        p1, _ = sahne(cls.k, cls.isim, cls.yer0)
        sd.olcek_kur(p1.width)
        x0 = sd.satir_olc_alt(p1, BANT, cls.k)['sag_isim'][0]
        sd.olcek_kur(2400)
        k = cls.k
        ImageDraw.Draw(p1).rectangle([int(round((x0 - KAY) * k)), int(round((IY + 40) * k)),
                                      int(round(x0 * k)) + 2, int(round((IY + 52) * k))], fill=(231, 167, 48))
        cls.p1 = p1

    def tearDown(self):
        sd.OLCEK_MERKEZ['etkin'] = True

    def test_uc_kuantil_glif_genislemesini_konum_sanar(self):
        sd.OLCEK_MERKEZ['etkin'] = False
        r = sd.olcek_kapisi_baski(self.p1, self.p0, BANT, esit=True)
        self.assertGreater(abs(r['fark']['bosluk_sag']), 1.0, r['fark'])
        self.assertFalse(r['gecti'], r['fark'])

    def test_kutle_merkezi_glif_genislemesini_gecirir(self):
        r = sd.olcek_kapisi_baski(self.p1, self.p0, BANT, esit=True)
        self.assertEqual(r['yatay_konum'], 'kutle merkezi')
        self.assertTrue(r['gecti'], r['fark'])
        self.assertLess(abs(r['fark']['bosluk_sag']), 0.5, r['fark'])
        self.assertGreater(abs(r['fark']['sag_isim_x0']), 1.0, r['fark'])     # uc kenar kenar olcutunde gorunur

    def test_kutle_merkezi_sag_isim_kaymasini_yakalar(self):
        yer = [list(v) for v in self.yer0]
        yer[2][0] += KAY
        p, _ = sahne(self.k, self.isim, yer)
        r = sd.olcek_kapisi_baski(p, self.p0, BANT, esit=True)
        self.assertFalse(r['gecti'], r['fark'])
        self.assertGreater(abs(r['fark']['bosluk_sag']), 1.0, r['fark'])


if __name__ == '__main__':
    unittest.main()
