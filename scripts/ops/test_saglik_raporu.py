import csv
import tempfile
import unittest
from pathlib import Path

import saglik_raporu


class SaglikRaporuTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dizin = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def yaz(self, ad, alanlar, satirlar):
        with (self.dizin / ad).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=alanlar)
            writer.writeheader(); writer.writerows(satirlar)

    def test_ozet_bes_satir_eksik_kaynak_ve_link(self):
        self.yaz("MAGAZA_DENETIM.csv", ["ilan", "kural", "durum"], [
            {"ilan": "111", "kural": "baslik", "durum": "PASS"},
            {"ilan": "222", "kural": "etiket", "durum": "FAIL"},
        ])
        metin = saglik_raporu.rapor_uret(self.dizin, tarih="2026-09-26")
        self.assertEqual(5, len(metin.split("\n\n", 1)[0].splitlines()))
        self.assertIn("Hatasiz ilan: 1/2 (%50.0)", metin)
        self.assertIn("| FIYAT_SKU.csv | ? | ? | ? |", metin)
        self.assertIn("[222](https://www.etsy.com/listing/222)", metin)

    def test_onceki_rapora_gore_duzelen_ve_yeni(self):
        self.yaz("CANLI_METIN.csv", ["ilan_id", "durum", "neden"], [
            {"ilan_id": "111", "durum": "FAIL", "neden": "tag_count"}
        ])
        onceki = self.dizin / "onceki.md"
        onceki.write_text(saglik_raporu.rapor_uret(self.dizin), encoding="utf-8")
        self.yaz("CANLI_METIN.csv", ["ilan_id", "durum", "neden"], [
            {"ilan_id": "222", "durum": "FAIL", "neden": "title_schema"}
        ])
        metin = saglik_raporu.rapor_uret(self.dizin, onceki)
        self.assertIn("1 duzelen, 1 yeni sorun", metin)
        self.assertIn("CANLI_METIN.csv|111|tag_count", metin)
        self.assertIn("CANLI_METIN.csv|222|title_schema", metin)

    def test_belirsiz_sorun_sayilir(self):
        self.yaz("GORSEL_DENETIM.csv", ["ilan_id", "durum", "neden"], [
            {"ilan_id": "333", "durum": "BELIRSIZ", "neden": "ocr_okunamadi"}
        ])
        metin = saglik_raporu.rapor_uret(self.dizin)
        self.assertIn("ocr_okunamadi (1)", metin)
        self.assertIn("Hatasiz ilan: 0/1 (%0.0)", metin)


if __name__ == "__main__":
    unittest.main()
