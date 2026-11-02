#!/usr/bin/env python3
"""yd2_metin_yaz.py sahte Etsy testleri (Etsy istegi yok). python3 scripts/etsy/test_yd2_metin.py"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yd2_metin_yaz as M  # noqa: E402

ESKI = ("Intro Cancer and Libra.\n\nWe use AI tools to help create the artwork, and every design is reviewed and finished by us.\n\n"
        "HOW TO ORDER\n1. Choose your style and your format.\n2. Example: Cancer: Emma, Libra: James.\n3. Heading: x."
        ' The card always says "Happy First Anniversary".\n\nDELIVERY\n'
        "- Digital card and digital file: sent in Etsy Messages as soon as you approve your preview.\n"
        "- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping worldwide. Estimated delivery: "
        "US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days, other countries 7 to 21 days.\n\n"
        "FORMATS\n- Digital card 5x7: a single-sided flat card sent as a digital file, to print at home or at a print shop. Nothing is "
        "shipped.\n- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.\n- Shipped print 8x10: "
        "printed on premium matte art paper with long-lasting inks and shipped to you by our production partner.\n\n"
        "WHY PAPER\nPaper is traditional. Print your card at home or at a print shop and give a paper gift made only for the two of you.")
BASLIK = "Cancer Libra Paper Anniversary Card, Zodiac Print"


class Sahte:
    def __init__(self, state="active", desc=ESKI, title=BASLIK, bozuk_okuma=False, kalan=4000):
        self.L = dict(state=state, description=desc.replace('"', "&quot;"), title=title)
        self.calls, self.remaining, self.yaz, self.bozuk = 0, kalan, [], bozuk_okuma

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        L = dict(self.L)
        if self.bozuk and self.yaz:
            L["description"] = "bozuk"
        return L

    def patch(self, path, data):
        self.calls += 1; self.yaz.append(dict(data))
        if "description" in data:
            self.L["description"] = data["description"]
        if "title" in data:
            self.L["title"] = data["title"]
        if self.bozuk and len(self.yaz) > 1:
            self.bozuk = False
        return {}


class T(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        (self.d / "1.json").write_text(json.dumps({"listing": {"description": ESKI}}), encoding="utf-8")

    def test_donustur(self):
        y, yt, notlar, neden = M.donustur(ESKI, BASLIK)
        self.assertEqual(neden, [])
        self.assertEqual(yt, "Cancer Libra Paper Anniversary Gift, Zodiac Print")
        self.assertIn(M.SIZES_SATIR, y)
        self.assertNotIn("card", y.lower().replace("cards", "card").split("care")[0] if False else y.lower().replace("carefully", ""))
        self.assertTrue(any("Emma" in n for n in notlar))

    def test_cift_eslesme_blok(self):
        _, _, _, neden = M.donustur(ESKI + "\n1. Choose your style and your format.", BASLIK)
        self.assertTrue(any("D1 eslesme 2" in n for n in neden))

    def test_baslik_yok(self):
        _, yt, notlar, neden = M.donustur(ESKI, "Cancer Libra Zodiac Print")
        self.assertEqual((yt, neden), ("Cancer Libra Zodiac Print", []))
        self.assertTrue(any("baslikta" in n for n in notlar))

    def test_kontrol_yazmaz(self):
        api = Sahte(); r = M.ilan_isle(api, "S", "1", self.d, self.d, "kontrol")
        self.assertEqual((r["sonuc"], api.yaz, api.calls), ("PLAN", [], 1))

    def test_yaz(self):
        api = Sahte(); r = M.ilan_isle(api, "S", "1", self.d, self.d, "yaz")
        self.assertEqual(r["sonuc"], "TAMAM"); self.assertEqual(api.calls, 3)
        self.assertEqual(sorted(api.yaz[0]), ["description", "title"])
        self.assertTrue((self.d / "YEDEK_METIN_1.json").exists())

    def test_taslak_yazilmaz(self):
        api = Sahte(state="draft"); r = M.ilan_isle(api, "S", "1", self.d, self.d, "yaz")
        self.assertEqual((r["sonuc"], api.yaz), ("KAYMA", []))

    def test_kayma(self):
        api = Sahte(desc=ESKI + " ek"); r = M.ilan_isle(api, "S", "1", self.d, self.d, "yaz")
        self.assertEqual((r["sonuc"], api.yaz), ("KAYMA", []))

    def test_okuma_tutmazsa_geri_alma(self):
        api = Sahte(bozuk_okuma=True); r = M.ilan_isle(api, "S", "1", self.d, self.d, "yaz")
        self.assertEqual(r["sonuc"], "FAIL"); self.assertEqual(len(api.yaz), 2)
        self.assertEqual(api.yaz[1]["description"], ESKI); self.assertEqual(r["geri_alma"], "TAMAM")

    def test_kota(self):
        api = Sahte(kalan=12); r = M.ilan_isle(api, "S", "1", self.d, self.d, "yaz")
        self.assertEqual((r["sonuc"], api.calls), ("KOTA", 0))


if __name__ == "__main__":
    unittest.main(verbosity=1)
