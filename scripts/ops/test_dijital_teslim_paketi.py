#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import dijital_teslim_paketi as D
import siparis_onay as S


class DijitalTeslimPaketiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.kok = Path(self.temp.name)
        self.a = self.kok / "masaustu.jpg"
        self.a.write_bytes(b"sahte-jpg")
        self.onaylar = self.kok / "ONAYLAR.json"
        self.cikti = self.kok / "DIJITAL_TESLIM"

    def tearDown(self):
        self.temp.cleanup()

    def onayla(self, dosyalar=None):
        ozet = S.paket_sha256(dosyalar or [self.a])
        self.onaylar.write_text(json.dumps({"sahte-001": {
            "sha256": ozet, "onay_zamani": "2026-09-26T12:00:00Z"}}))

    def hazirla(self, girdiler=None):
        return D.paket_hazirla("sahte-001", girdiler or [("Desktop", self.a)],
                               self.onaylar, self.cikti,
                               cift="Aries Leo", urun="Wallpaper")

    def test_onaysizken_paket_olusturmaz(self):
        self.onaylar.write_text("{}")
        with self.assertRaisesRegex(S.OnayHatasi, "Serdar onayi yok"):
            self.hazirla()
        self.assertFalse((self.cikti / "sahte-001").exists())

    def test_sha_farki_paket_olusturmaz(self):
        self.onayla()
        self.a.write_bytes(b"degisti")
        with self.assertRaisesRegex(S.OnayHatasi, "SHA256"):
            self.hazirla()

    def test_onayli_dosya_son_adla_ve_talimatla_hazirlanir(self):
        self.onayla()
        hedef = self.hazirla()
        self.assertTrue((hedef / "AstroLove_ARIES_LEO_Wallpaper_Desktop.jpg").is_file())
        talimat = (hedef / "TALIMAT.txt").read_text()
        self.assertEqual(len(talimat.splitlines()), 3)
        self.assertIn("Chrome", talimat)
        self.assertIn("Orders & Shipping", talimat)

    def test_bes_dosyadan_fazlasi_reddedilir(self):
        self.onaylar.write_text("{}")
        with self.assertRaisesRegex(S.OnayHatasi, "en fazla 5"):
            self.hazirla([("x", self.a)] * 6)

    def test_yirmi_mb_siniri_reddedilir(self):
        self.onayla()
        with mock.patch.object(D, "AZAMI_BAYT", 3):  # dosyalar 3 bayttan buyuk -> sinir asilir
            with self.assertRaisesRegex(S.OnayHatasi, "20 MB"):
                self.hazirla()

    def test_desteklenmeyen_uzanti_reddedilir(self):
        pdf = self.kok / "teslim.pdf"
        pdf.write_bytes(b"sahte-pdf")
        self.onayla([pdf])
        with self.assertRaisesRegex(S.OnayHatasi, "JPG ve PNG"):
            self.hazirla([("A4", pdf)])

    def test_ayni_son_ad_cakismasi_reddedilir(self):
        b = self.kok / "telefon.jpg"
        b.write_bytes(b"sahte-jpg-iki")
        self.onayla([self.a, b])
        with self.assertRaisesRegex(S.OnayHatasi, "cakismali"):
            self.hazirla([("Mobile", self.a), ("Mobile", b)])


if __name__ == "__main__":
    unittest.main()
