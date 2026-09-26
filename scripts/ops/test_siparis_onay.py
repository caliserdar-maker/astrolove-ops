#!/usr/bin/env python3
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import siparis_onay as S


class SiparisOnayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.a = self.kok / "baski.png"
        self.a.write_bytes(b"sahte tam cozunurluk")
        self.onaylar = self.kok / "ONAYLAR.json"

    def tearDown(self):
        self.tmp.cleanup()

    def onayla(self, kimlik="sahte-001", dosyalar=None):
        ozet = S.paket_sha256(dosyalar or [self.a])
        self.onaylar.write_text(json.dumps({kimlik: {"sha256": ozet, "onay_zamani": "2026-09-26T12:00:00Z"}}))
        return ozet

    def test_onaysiz_gonderim_reddedilir(self):
        self.onaylar.write_text("{}")
        with self.assertRaisesRegex(S.OnayHatasi, "Serdar onayi yok"):
            S.onay_kapisi("sahte-001", [self.a], self.onaylar)

    def test_sha_farki_reddedilir(self):
        self.onayla()
        self.a.write_bytes(b"onaydan sonra degisti")
        with self.assertRaisesRegex(S.OnayHatasi, "SHA256"):
            S.onay_kapisi("sahte-001", [self.a], self.onaylar)

    def test_onayli_fiziksel_paket_gecer(self):
        beklenen = self.onayla()
        self.assertEqual(S.onay_kapisi("sahte-001", [self.a], self.onaylar), beklenen)

    def test_dijital_teslim_ayni_kapiyi_kullanir(self):
        beklenen = self.onayla()
        self.assertEqual(S.dijital_teslim_kapisi("sahte-001", [self.a], self.onaylar), beklenen)

    def test_eksik_dosya_reddedilir(self):
        self.onaylar.write_text("{}")
        with self.assertRaisesRegex(S.OnayHatasi, "dosyasi eksik"):
            S.onay_kapisi("sahte-001", [self.kok / "yok.png"], self.onaylar)

    def test_musteri_verisi_loga_sizmaz(self):
        gizli = "Sahte Musteri sahte@example.invalid"
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            S.onay_paketi_hazirla("sahte-001", [self.a], self.kok / "SIPARIS_ONAY", isim_mesaj=gizli)
        self.assertNotIn(gizli, cikti.getvalue())
        self.assertIn(gizli, (self.kok / "SIPARIS_ONAY/sahte-001/onay.html").read_text())

    def test_coklu_dosya_siradan_bagimsizdir(self):
        b = self.kok / "teslim.pdf"
        b.write_bytes(b"sahte pdf")
        self.assertEqual(S.paket_sha256([self.a, b]), S.paket_sha256([b, self.a]))

    def test_hazirla_onaysiz_red_onayla_gecer_degisince_red(self):
        """IS_0026 sentetik uctan uca: hazirla -> red -> onay -> gec -> degistir -> red."""
        kok = self.kok / "SIPARIS_ONAY"
        S.onay_paketi_hazirla("sahte-002", [self.a], kok)
        self.onaylar.write_text("{}")
        kopya = kok / "sahte-002" / self.a.name
        with self.assertRaisesRegex(S.OnayHatasi, "Serdar onayi yok"):
            S.onay_kapisi("sahte-002", [kopya], self.onaylar)
        S.onay_yaz("sahte-002", kok / "sahte-002", self.onaylar,
                    zaman="2026-09-26T12:00:00Z")
        S.onay_kapisi("sahte-002", [kopya], self.onaylar)
        kopya.write_bytes(b"onaydan sonra degisti")
        with self.assertRaisesRegex(S.OnayHatasi, "SHA256"):
            S.onay_kapisi("sahte-002", [kopya], self.onaylar)

    def test_dijital_paket_ortak_dizin_semasini_kullanir(self):
        kayit = S.dijital_teslim_paketi_hazirla("dijital-sahte", [self.a], self.kok / "SIPARIS_ONAY")
        self.assertEqual(kayit["dosyalar"], ["baski.png"])
        self.assertTrue((self.kok / "SIPARIS_ONAY/dijital-sahte/onay.html").is_file())

    def test_guvensiz_kimlik_reddedilir(self):
        with self.assertRaisesRegex(S.OnayHatasi, "kimlik gecersiz"):
            S.onay_paketi_hazirla("../disari", [self.a], self.kok)


if __name__ == "__main__":
    unittest.main()
