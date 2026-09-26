#!/usr/bin/env python3
"""IS_0001 fail-closed siparis kurallari icin yerel birim testleri."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import kisisel_siparis
import order_router


class _Image:
    def __init__(self, size, dpi):
        self.size = size
        self.info = {"dpi": dpi}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FailClosedTest(unittest.TestCase):
    def test_onayli_ve_onaysiz_boy(self):
        receipt = {"transactions": [
            {"transaction_id": 1, "sku": "POD-ARI_TAU-MB-8x10", "quantity": 1},
            {"transaction_id": 2, "sku": "POD-ARI_TAU-MB-5x7", "quantity": 1},
        ]}
        items, _, atlanan = order_router.parse_items(receipt)
        self.assertEqual(items[0]["prodigi_sku"], "GLOBAL-HPR-8x10")
        self.assertIn("GONDERME", atlanan[0])

    def test_plate_onayi(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "plate.json"
            p.write_text(json.dumps({"onayli": [{"edisyon": "MB", "boy": "8x10"}]}))
            self.assertTrue(order_router.plate_onayli_mi("MB", "8x10", p))
            self.assertFalse(order_router.plate_onayli_mi("MB", "A4", p))

    def test_piksel_ve_dpi(self):
        kopyala = Mock(return_value=SimpleNamespace(returncode=0))
        with patch.object(order_router.Image, "open", return_value=_Image((2400, 3000), (300, 300))):
            self.assertEqual(order_router.baski_dosyasi_dogrula("remote", "8x10", kopyala), (True, ""))
        with patch.object(order_router.Image, "open", return_value=_Image((2399, 3000), (72, 72))):
            self.assertFalse(order_router.baski_dosyasi_dogrula("remote", "8x10", kopyala)[0])

    def test_pause_govdesi_ve_geri_okuma(self):
        body = order_router.order_body({"receipt_id": "1234"}, [], {})
        self.assertEqual(body["status"], "Draft")
        self.assertTrue(order_router.siparis_beklemede_mi({"status": {"stage": "Draft"}}))
        self.assertFalse(order_router.siparis_beklemede_mi({"status": {"stage": "InProgress"}}))

    def test_turkce_buyuk_harf(self):
        self.assertEqual(kisisel_siparis.buyut("inci ışık", "TR"), "İNCİ IŞIK")

    def test_kisisellestirme_sinirlari_ve_karakter(self):
        self.assertEqual(kisisel_siparis.isim_dogrula("ABCDEFGHIJK")[0], "TAMAM")
        self.assertEqual(kisisel_siparis.isim_dogrula("ABCDEFGHIJKL")[0], "ELLE KONTROL")
        self.assertEqual(kisisel_siparis.mesaj_dogrula("x" * 35)[0], "TAMAM")
        self.assertEqual(kisisel_siparis.mesaj_dogrula("x" * 36)[0], "ELLE KONTROL")
        self.assertEqual(kisisel_siparis.mesaj_dogrula("hello_world")[0], "ELLE KONTROL")

    def test_ayni_burc_left_right(self):
        sonuc = kisisel_siparis.eslestir({"pair": "ARIES_ARIES", "alanlar": [
            ("Left name", "Ada"), ("Right name", "Ece"), ("Your message", "Forever")
        ]})
        self.assertEqual((sonuc["isim1"], sonuc["isim2"]), ("Ada", "Ece"))


if __name__ == "__main__":
    unittest.main()
