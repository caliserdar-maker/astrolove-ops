#!/usr/bin/env python3
"""Plate onay CLI birim ve alt surec testleri."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import plate_onay as P


class PlateOnayTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.dosya = Path(self.gecici.name) / "plate_onay.json"
        self.dosya.write_text('{"onayli": []}\n', encoding="utf-8")

    def tearDown(self):
        self.gecici.cleanup()

    def calistir(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(P.__file__)), "--dosya", str(self.dosya), *args],
            text=True, capture_output=True, check=False,
        )

    def test_ekle_alias_coklu_boy_ve_idempotent(self):
        args = ("ekle", "--edisyon", "BLUE", "--boylar", "8x10,A4",
                "--kanit", "sahte-kanit-id", "--onaylayan", "Test Kullanici")
        self.assertEqual(self.calistir(*args).returncode, 0)
        ikinci = self.calistir(*args)
        self.assertEqual(ikinci.returncode, 0)
        self.assertIn("0 kayit eklendi", ikinci.stdout)
        kayitlar = json.loads(self.dosya.read_text(encoding="utf-8"))["onayli"]
        self.assertEqual([(k["edisyon"], k["boy"]) for k in kayitlar],
                         [("MIDNIGHT_BLUE", "8x10"), ("MIDNIGHT_BLUE", "A4")])
        self.assertTrue(all(k["tarih_utc"].endswith("Z") for k in kayitlar))

    def test_kaldir_ve_listele(self):
        self.calistir("ekle", "--edisyon", "PURE_WHITE", "--boylar", "A1,A2",
                      "--kanit", "sahte", "--onaylayan", "Test")
        sonuc = self.calistir("kaldir", "--edisyon", "PURE_WHITE", "--boylar", "A1")
        self.assertEqual(sonuc.returncode, 0)
        liste = self.calistir("listele")
        self.assertEqual([k["boy"] for k in json.loads(liste.stdout)["onayli"]], ["A2"])

    def test_bilinmeyen_boy_ve_edisyon_reddedilir(self):
        ortak = ("--boylar", "5x7", "--kanit", "x", "--onaylayan", "y")
        self.assertNotEqual(self.calistir("ekle", "--edisyon", "BLUE", *ortak).returncode, 0)
        self.assertNotEqual(self.calistir("ekle", "--edisyon", "GREEN", "--boylar", "A4",
                                         "--kanit", "x", "--onaylayan", "y").returncode, 0)

    def test_dogrula_yinelenen_ve_eksik_alan_reddeder(self):
        kayit = {"edisyon": "DEEP_BLACK", "boy": "A4", "kanit": "x",
                 "onaylayan": "y", "tarih_utc": "2026-09-26T12:00:00Z"}
        with self.assertRaises(P.DefterHatasi):
            P.dogrula({"onayli": [kayit, dict(kayit)]})
        bozuk = dict(kayit)
        bozuk.pop("kanit")
        with self.assertRaises(P.DefterHatasi):
            P.dogrula({"onayli": [bozuk]})

    def test_tum_16_boy_gecerli(self):
        self.assertEqual(len(P.BOYLAR), 16)
        P.dogrula({"onayli": []})


if __name__ == "__main__":
    unittest.main()
