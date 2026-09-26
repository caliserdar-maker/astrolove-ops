#!/usr/bin/env python3
"""mesaj_taslak icin sentetik birim ve CLI davranis testleri."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import mesaj_taslak as M


class MesajTaslakTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.state = self.kok / "state.json"
        self.cikti = self.kok / "cikti"

    def tearDown(self):
        self.gecici.cleanup()

    def calistir(self, kayitlar):
        self.state.write_text(json.dumps(kayitlar), encoding="utf-8")
        M.uret(self.state, self.cikti)
        with (self.cikti / "OZET.csv").open(encoding="utf-8", newline="") as dosya:
            return list(csv.DictReader(dosya))

    def test_alti_sablon_eslesir(self):
        ortak = {"buyer_first_name": "TestBuyer"}
        kayitlar = [
            {**ortak, "receipt_id": "FAKE-1", "stage": "ISIM_BEKLIYOR", "neden": "UZUN_ISIM",
             "submitted_name": "ABCDEFGHIJKL", "suggested_name": "ABCDEFGHIJK"},
            {**ortak, "receipt_id": "FAKE-2", "stage": "ISIM_BEKLIYOR", "neden": "UZUN_MESAJ",
             "suggested_message": "Synthetic short message"},
            {**ortak, "receipt_id": "FAKE-3", "stage": "ISIM_BEKLIYOR", "neden": "EKSIK_SORU",
             "sign_a": "Aries", "sign_b": "Leo", "name_a": "ALFA", "name_b": "BETA", "message": "Test"},
            {**ortak, "receipt_id": "FAKE-4", "stage": "ISIM_BEKLIYOR", "neden": "SAME_SIGN",
             "zodiac_sign": "Leo", "left_name": "LEFT", "right_name": "RIGHT"},
            {**ortak, "receipt_id": "FAKE-5", "stage": "atlandi", "neden": "MANUAL_FILE_CHECK",
             "date": "2099-01-01"},
            {**ortak, "receipt_id": "FAKE-6", "stage": "shipped", "neden": "tracking ready",
             "tracking": "TRACK-TEST", "carrier": "Test Carrier", "tracking_url": "https://example.test/track"},
        ]
        ozet = self.calistir(kayitlar)
        self.assertEqual([satir["sablon_no"] for satir in ozet], list("123456"))
        for no in range(1, 7):
            metin = (self.cikti / f"FAKE-{no}.txt").read_text(encoding="utf-8")
            self.assertNotRegex(metin, M.UZUN_TIRE)

    def test_eslesmeyen_sablon_yok_ve_dosya_yok(self):
        ozet = self.calistir([{"receipt_id": "FAKE-NONE", "stage": "error", "neden": "API_HATASI"}])
        self.assertEqual(ozet[0]["sablon_no"], "SABLON_YOK")
        self.assertFalse((self.cikti / "FAKE-NONE.txt").exists())

    def test_eksik_alan_doldur_isareti_olarak_kalir(self):
        self.calistir([{"receipt_id": "FAKE-MISSING", "stage": "ISIM_BEKLIYOR", "neden": "BOS"}])
        metin = (self.cikti / "FAKE-MISSING.txt").read_text(encoding="utf-8")
        self.assertIn("[DOLDUR: buyer_first_name]", metin)
        self.assertIn("[DOLDUR: sign_a]", metin)

    def test_stdout_musteri_alani_icermez(self):
        kayit = [{"receipt_id": "FAKE-CLI", "stage": "ISIM_BEKLIYOR", "neden": "UZUN_ISIM",
                  "buyer_first_name": "PRIVATE_TEST_NAME"}]
        self.state.write_text(json.dumps(kayit), encoding="utf-8")
        sonuc = subprocess.run(
            [sys.executable, str(Path(M.__file__)), "--state", str(self.state), "--cikti", str(self.cikti)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        self.assertNotIn("PRIVATE_TEST_NAME", sonuc.stdout + sonuc.stderr)

    def test_guvensiz_receipt_reddedilir(self):
        self.state.write_text(json.dumps([{"receipt_id": "../FAKE", "stage": "error"}]), encoding="utf-8")
        with self.assertRaises(M.TaslakHatasi):
            M.uret(self.state, self.cikti)


if __name__ == "__main__":
    unittest.main()
