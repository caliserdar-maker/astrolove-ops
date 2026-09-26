#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import dijital_teslim_paketi as D
import siparis_onay as S


class DijitalTeslimPaketiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.kok = Path(self.temp.name)
        self.onaylar = self.kok / "ONAYLAR.json"
        self.cikti = self.kok / "DIJITAL_TESLIM"

    def tearDown(self):
        self.temp.cleanup()

    def zip_yaz(self, renk, tur="wallart"):
        yol = self.kok / f"{renk}.zip"
        parcalar = D.ORANLAR if tur == "wallart" else D.CIHAZLAR
        with zipfile.ZipFile(yol, "w") as arsiv:
            for parca in parcalar:
                arsiv.writestr(f"{renk}_{parca}.jpg", b"sahte-gorsel")
            if tur == "wallart":
                arsiv.writestr("PRINT_GUIDE.pdf", b"%PDF-1.4\n")
        return yol

    def wallart(self):
        return [(renk.replace("_", " ").title(), self.zip_yaz(renk))
                for renk in sorted(D.RENKLER)]

    def wallpaper(self):
        girdiler = [(renk.replace("_", " ").title(), self.zip_yaz(renk, "wallpaper"))
                    for renk in sorted(D.WALLPAPER_RENKLER)]
        rehber = self.kok / "wallpaper-guide.pdf"
        rehber.write_bytes(b"%PDF-1.7\n")
        return girdiler + [("Wallpaper Guide", rehber)]

    def onayla(self, girdiler):
        ozet = S.paket_sha256([yol for _, yol in girdiler])
        self.onaylar.write_text(json.dumps({"sahte-001": {
            "sha256": ozet, "onay_zamani": "2026-09-26T12:00:00Z"}}))

    def hazirla(self, girdiler, urun="Digital Wall Art"):
        return D.paket_hazirla("sahte-001", girdiler, self.onaylar, self.cikti,
                               cift="Aries Leo", urun=urun)

    def test_dijital_bes_renk_zip_hazirlanir(self):
        girdiler = self.wallart()
        self.onayla(girdiler)
        hedef = self.hazirla(girdiler)
        self.assertTrue((hedef / "AstroLove_Digital_Wall_Art_ARIES_LEO_Deep_Black.zip").is_file())
        self.assertIn("ZIP/PDF", (hedef / "TALIMAT.txt").read_text())

    def test_wallpaper_dort_zip_bir_pdf_hazirlanir(self):
        girdiler = self.wallpaper()
        self.onayla(girdiler)
        hedef = self.hazirla(girdiler, "Wallpaper")
        self.assertEqual(len(list(hedef.glob("*.zip"))), 4)
        self.assertEqual(len(list(hedef.glob("*.pdf"))), 1)

    def test_bozuk_zip_reddedilir(self):
        girdiler = self.wallart()
        girdiler[0][1].write_bytes(b"zip-degil")
        self.onayla(girdiler)
        with self.assertRaisesRegex(S.OnayHatasi, "bozuk ZIP"):
            self.hazirla(girdiler)

    def test_eksik_oran_reddedilir(self):
        girdiler = self.wallart()
        renk, yol = girdiler[0]
        with zipfile.ZipFile(yol, "w") as arsiv:
            arsiv.writestr(f"{renk}_4x5.jpg", b"sahte")
        self.onayla(girdiler)
        with self.assertRaisesRegex(S.OnayHatasi, "eksik"):
            self.hazirla(girdiler)

    def test_alti_dosya_reddedilir(self):
        girdiler = self.wallart()
        with self.assertRaisesRegex(S.OnayHatasi, "en fazla 5"):
            self.hazirla(girdiler + [girdiler[0]])

    def test_onaysizken_paket_olusturmaz(self):
        girdiler = self.wallart()
        self.onaylar.write_text("{}")
        with self.assertRaisesRegex(S.OnayHatasi, "Serdar onayi yok"):
            self.hazirla(girdiler)

    def test_gecersiz_pdf_reddedilir(self):
        girdiler = self.wallpaper()
        girdiler[-1][1].write_bytes(b"sahte-pdf")
        self.onayla(girdiler)
        with self.assertRaisesRegex(S.OnayHatasi, "PDF basligi"):
            self.hazirla(girdiler, "Wallpaper")

    def test_yirmi_mb_siniri_reddedilir(self):
        girdiler = self.wallart()
        self.onayla(girdiler)
        with mock.patch.object(D, "AZAMI_BAYT", 3):
            with self.assertRaisesRegex(S.OnayHatasi, "20 MB"):
                self.hazirla(girdiler)


if __name__ == "__main__":
    unittest.main()
