#!/usr/bin/env python3
"""Kaynak olcum guvenligi (Test 3 ARIES_VIRGO MB 2:3, KeyError 'tag_bant').

Sentetik 2400x3600 Blue sayfa, kaynak_olcum ayrintisindaki (run 36918874524) bant duzeniyle: isim satirinda ilk isim
25 px harf boslugu ile iki kumeye bolunur, 3 kumeli tagline. Dogrudan sayfa_olc tagline'i isim satiri secer
(tag_bant yok); sayfa_olc_guvenli dogru bantlari bulur. Sablona uymayan sayfa FAIL-CLOSED hata verir.
KISISEL_YOL=<kisisel-v1>/scripts/kisisel gerekir (yoksa atlanir).
"""
import os, sys, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import pilot11
    import a1_poster
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

ALTIN = (231, 167, 48)


def sayfa(yol, isim_bolunmus=True, tagline=True, isim_y=(2600, 2696)):
    im = Image.new('RGB', (2400, 3600), (4, 10, 40)); d = ImageDraw.Draw(im)
    d.ellipse([254, 511, 2146, 1964], outline=ALTIN, width=8)                       # buyuk daire + sembol
    d.rectangle([900, 800, 1500, 1500], fill=ALTIN)
    for x0, x1 in ((602, 823), (1539, 1766)):                                       # kucuk semboller
        d.rectangle([x0, 2255, x1, 2478], fill=ALTIN)
    y0, y1 = isim_y
    isim = [(519, 735), (761, 906)] if isim_bolunmus else [(519, 906)]
    for x0, x1 in isim + [(1059, 1270), (1423, 1881)]:                              # ARIE S | sonsuz | VIRGO
        d.rectangle([x0, y0, x1, y1], fill=ALTIN)
    if tagline:
        for x0, x1 in ((807, 957), (982, 1175), (1267, 1594)):                      # Two | Souls | One Bond
            d.rectangle([x0, 3009, x1, 3090], fill=ALTIN)
    im.save(yol)
    return yol


@unittest.skipUnless(HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class KaynakOlcumGuvenliTesti(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.k = Path(self.d.name)

    def tearDown(self):
        self.d.cleanup()

    def test_dogrudan_olcum_tagline_i_isim_sanar(self):
        o = pilot11.sayfa_olc(sayfa(self.k / 'a.png'))
        self.assertEqual(o['isim_bant'][0], 3009)
        self.assertNotIn('tag_bant', o)
        self.assertIsNotNone(a1_poster.olcum_sorunu(o))

    def test_guvenli_olcum_dogru_bantlar(self):
        o, yedek = a1_poster.sayfa_olc_guvenli(pilot11, sayfa(self.k / 'a.png'))
        self.assertEqual(o['isim_bant'], [2600, 2697])
        self.assertEqual(o['tag_bant'][0], 3009)
        self.assertEqual(o['sol_isim'], [519, 907])
        self.assertIsNotNone(yedek)
        self.assertIsNone(a1_poster.olcum_sorunu(o))
        self.assertIs(pilot11.kumeler, pilot11.kumeler)        # yama geri alindi (asagida ayrica)

    def test_yama_geri_alinir(self):
        asil = pilot11.kumeler
        a1_poster.sayfa_olc_guvenli(pilot11, sayfa(self.k / 'a.png'))
        self.assertIs(pilot11.kumeler, asil)

    def test_gecerli_sayfa_yeniden_olculmez(self):
        y = sayfa(self.k / 'b.png', isim_bolunmus=False)
        o0 = pilot11.sayfa_olc(y)
        o, yedek = a1_poster.sayfa_olc_guvenli(pilot11, y)
        self.assertIsNone(yedek); self.assertEqual(o, o0)

    def test_tagline_yok_fail_closed(self):
        with self.assertRaises(a1_poster.KaynakOlcumHatasi) as h:
            a1_poster.sayfa_olc_guvenli(pilot11, sayfa(self.k / 'c.png', isim_bolunmus=False, tagline=False))
        self.assertIn('KAYNAK OLCUM HATASI', str(h.exception))


if __name__ == '__main__':
    unittest.main()
