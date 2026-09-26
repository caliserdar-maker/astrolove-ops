import csv
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import durum_ozet


class DurumOzetTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def csv_yaz(self, ad, alanlar, satirlar):
        yol = self.dizin / ad
        with yol.open("w", encoding="utf-8", newline="") as fh:
            y = csv.DictWriter(fh, fieldnames=alanlar)
            y.writeheader(); y.writerows(satirlar)
        return yol

    def test_kanonik_liste_ayni_burclarla_78_cift_uretir(self):
        ciftler = durum_ozet.kanonik_ciftler()
        self.assertEqual(78, len(ciftler))
        self.assertIn("ARIES_ARIES", ciftler)
        self.assertIn("PISCES_PISCES", ciftler)

    def test_eksik_kaynaklar_soru_isareti_olur(self):
        satir = durum_ozet.uret()[0]
        self.assertTrue(all(satir[a] == "?" for a in durum_ozet.ALANLAR[1:]))

    def test_qc_satirlari_birlestirilir_ve_liste_sirasi_korunur(self):
        liste = self.csv_yaz("liste.csv", ["cift"], [{"cift": "Leo + Aries"}, {"cift": "Taurus Taurus"}])
        qc = self.csv_yaz("qc.csv", ["cift", "sonuc"], [
            {"cift": "ARIES_LEO", "sonuc": "PASS"}, {"cift": "ARIES_LEO", "sonuc": "FAIL"}
        ])
        satirlar = durum_ozet.uret(tamset_qc=qc, liste=liste)
        self.assertEqual(["ARIES_LEO", "TAURUS_TAURUS"], [x["cift"] for x in satirlar])
        self.assertEqual("EVET", satirlar[0]["tamset_var"])
        self.assertEqual("FAIL", durum_ozet.csv_sonuclari(qc)[0]["ARIES_LEO"])
        self.assertEqual("?", satirlar[1]["tamset_var"])

    def test_galeri_video_varyasyon_ve_en_yeni_zaman(self):
        liste = self.csv_yaz("liste.csv", ["cift"], [{"cift": "ARIES_LEO"}])
        galeri = self.dizin / "galeri.json"
        galeri.write_text(json.dumps({"ilan": {"ARIES_LEO": {"sonuc": "PASS", "kontrol": {"varyasyon": True}}}}))
        video = self.csv_yaz("video.csv", ["cift", "sonuc"], [{"cift": "ARIES_LEO", "sonuc": "FAIL"}])
        os.utime(galeri, (100, 100)); os.utime(video, (200, 200))
        satir = durum_ozet.uret(galeri=galeri, video_qc=video, liste=liste)[0]
        self.assertEqual(("PASS", "FAIL", "PASS"), (satir["galeri_sonuc"], satir["video_sonuc"], satir["varyasyon_ok"]))
        self.assertEqual("1970-01-01T00:03:20Z", satir["son_guncelleme"])

    def test_cli_alti_satir_ozet_ve_csv_yazar(self):
        cikti = self.dizin / "DURUM_78.csv"
        ekran = StringIO()
        with redirect_stdout(ekran):
            durum_ozet.main(["--cikti", str(cikti)])
        self.assertEqual(6, len(ekran.getvalue().splitlines()))
        with cikti.open(encoding="utf-8") as fh:
            self.assertEqual(78, len(list(csv.DictReader(fh))))


if __name__ == "__main__":
    unittest.main()
