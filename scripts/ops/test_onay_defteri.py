#!/usr/bin/env python3
"""onay_defteri.py yerel testi: sahte rclone (gdrive: -> gecici dizin), gercek Drive / gercek ONAYLAR.json YOK.
Senaryolar: dosya var + normal ekleme, okuma hatasi (lsjson / copyto), dosya yok (ilk kayit), bozuk JSON (metin / liste),
kayit azalmasi, baska kaydin degismesi, yedek yazilamiyor, ayni kimlik ikinci onay, okumadan sonra uzak degisti,
geri okuma tutmuyor. Her FAIL'de uzak ONAYLAR.json'un degismedigi de kontrol edilir."""
import contextlib
import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import onay_defteri as D  # noqa: E402
import siparis_onay as S  # noqa: E402

SAHTE = (Path(__file__).resolve().parent / "sahte_rclone.py").read_text()   # ortak sahte rclone (durum_dosyasi ile)
UZAK = "gdrive:ASTROLOVE/TEMP/SIPARIS_ONAY"


class DefterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        (t / "sahte_rclone.py").write_text(SAHTE)
        self.kok = t / "drive"; self.uzak_dir = self.kok / "ASTROLOVE/TEMP/SIPARIS_ONAY"; self.uzak_dir.mkdir(parents=True)
        self.dizin, self.durum = t / "_work/SIPARIS_ONAY", t / "_work/DEFTER"
        os.environ.update(RCLONE=f"{sys.executable} {t / 'sahte_rclone.py'}", FAKE_ROOT=str(self.kok), FAKE_HATA="")
        self.paket = {}
        for k in ("sahte-001", "sahte-002", "sahte-003"):             # gercek siparis_onay paket akisi
            f = t / f"{k}.png"; f.write_bytes(k.encode() * 10)
            S.onay_paketi_hazirla(k, [f], t / "paket")
            self.paket[k] = t / "paket" / k

    def tearDown(self):
        self.tmp.cleanup()

    def uzak(self, v=None, ham=None):
        p = self.uzak_dir / "ONAYLAR.json"
        if ham is not None:
            p.write_bytes(ham)
        elif v is not None:
            p.write_text(json.dumps(v, indent=2) + "\n")
        return p.read_bytes() if p.exists() else None

    def kos(self, *arg):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = D.main([*arg, "--uzak", UZAK, "--dizin", str(self.dizin), "--durum", str(self.durum)])
        return rc, o.getvalue()

    def akis(self, kimlik, hata_oku="", hata_yaz="", bozma=None):
        os.environ["FAKE_HATA"] = hata_oku
        rc, log = self.kos("oku")
        if rc:
            return rc, log
        S.onay_yaz(kimlik, self.paket[kimlik], self.dizin / "ONAYLAR.json")
        if bozma:
            bozma(self.dizin / "ONAYLAR.json")
        os.environ["FAKE_HATA"] = hata_yaz
        rc2, log2 = self.kos("yaz", "--kimlik", kimlik)
        return rc2, log + log2

    def yedekler(self):
        return sorted((self.uzak_dir / "YEDEK").glob("ONAYLAR_*.json"))       # 26 Eki: yedekler YEDEK/ alt klasorunde

    def test_1_dosya_var_normal_ekleme(self):
        once = {"eski-1": {"sha256": "a" * 64, "onay_zamani": "2026-10-01T00:00:00Z"},
                "eski-2": {"sha256": "b" * 64, "onay_zamani": "2026-10-02T00:00:00Z"}}
        self.uzak(once)
        rc, log = self.akis("sahte-001")
        self.assertEqual(rc, 0, log)
        sonra = json.loads(self.uzak())
        self.assertEqual(set(sonra), {"eski-1", "eski-2", "sahte-001"})
        self.assertEqual({k: sonra[k] for k in once}, once)
        self.assertEqual(len(self.yedekler()), 1)
        self.assertEqual(json.loads(self.yedekler()[0].read_text()), once)

    def test_2a_listeleme_hatasi(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_oku="lsjson")
        self.assertEqual(rc, 1); self.assertIn("listeleme hatasi", log)
        self.assertEqual(self.uzak(), b); self.assertFalse(self.yedekler())

    def test_2b_listede_var_indirme_hatasi(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_oku="copyto_indir")
        self.assertEqual(rc, 1); self.assertIn("indirilemedi", log)
        self.assertEqual(self.uzak(), b)

    def test_3_dosya_yok_ilk_kayit(self):
        rc, log = self.akis("sahte-001")
        self.assertEqual(rc, 0, log); self.assertIn("ilk kayit", log)
        self.assertEqual(set(json.loads(self.uzak())), {"sahte-001"})
        self.assertFalse(self.yedekler())

    def test_4a_bozuk_json(self):
        b = self.uzak(ham=b'{"eski-1": {"sha256": ')
        rc, log = self.akis("sahte-001")
        self.assertEqual(rc, 1); self.assertIn("gecerli JSON degil", log); self.assertEqual(self.uzak(), b)

    def test_4b_json_nesne_degil(self):
        b = self.uzak(ham=b'[1, 2]\n')
        rc, log = self.akis("sahte-001")
        self.assertEqual(rc, 1); self.assertIn("nesnesi degil", log); self.assertEqual(self.uzak(), b)

    def test_5a_kayit_azalmasi(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}, "eski-2": {"sha256": "b" * 64, "onay_zamani": "y"}})

        def sil(p):
            v = json.loads(p.read_text()); v.pop("eski-1"); p.write_text(json.dumps(v))
        rc, log = self.akis("sahte-001", bozma=sil)
        self.assertEqual(rc, 1); self.assertIn("kayit sayisi", log)
        self.assertEqual(self.uzak(), b); self.assertFalse(self.yedekler())

    def test_5b_baska_kayit_degisti(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})

        def degistir(p):
            v = json.loads(p.read_text()); v["eski-1"]["sha256"] = "c" * 64; p.write_text(json.dumps(v))
        rc, log = self.akis("sahte-001", bozma=degistir)
        self.assertEqual(rc, 1); self.assertIn("korunmadi", log); self.assertEqual(self.uzak(), b)

    def test_6_yedek_yazilamiyor(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_yaz="copyto_yedek")
        self.assertEqual(rc, 1); self.assertIn("yedek yazilamadi", log)
        self.assertEqual(self.uzak(), b)

    def test_7_ayni_kimlik_ikinci_onay(self):
        self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-002"); self.assertEqual(rc, 0, log)
        ilk = json.loads(self.uzak())
        rc, log = self.akis("sahte-002"); self.assertEqual(rc, 0, log)
        iki = json.loads(self.uzak())
        self.assertEqual(len(iki), len(ilk)); self.assertEqual(iki["eski-1"], ilk["eski-1"])
        self.assertEqual(iki["sahte-002"]["sha256"], ilk["sahte-002"]["sha256"])
        self.assertEqual(len(self.yedekler()), 2)

    def test_8_okumadan_sonra_uzak_degisti(self):
        self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        os.environ["FAKE_HATA"] = ""
        self.assertEqual(self.kos("oku")[0], 0)
        S.onay_yaz("sahte-001", self.paket["sahte-001"], self.dizin / "ONAYLAR.json")
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}, "baska": {"sha256": "d" * 64, "onay_zamani": "z"}})
        rc, log = self.kos("yaz", "--kimlik", "sahte-001")
        self.assertEqual(rc, 1); self.assertIn("degismis", log); self.assertEqual(self.uzak(), b)

    def test_9_geri_okuma_tutmuyor(self):
        self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        os.environ["FAKE_HATA"] = ""
        self.assertEqual(self.kos("oku")[0], 0)
        S.onay_yaz("sahte-001", self.paket["sahte-001"], self.dizin / "ONAYLAR.json")
        os.environ["FAKE_HATA"] = "cat_bozuk_sonra"            # yazimdan SONRAKI geri okuma farkli icerik dondurur
        rc, log = self.kos("yaz", "--kimlik", "sahte-001")
        self.assertEqual(rc, 1); self.assertIn("geri okuma sha256", log)

    def test_11_liste_bos_ama_dosya_var(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_oku="lsjson_bos")
        self.assertEqual(rc, 1); self.assertIn("dogrudan okunabiliyor", log); self.assertEqual(self.uzak(), b)

    def test_12_defter_kayip_yedek_var(self):
        self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001"); self.assertEqual(rc, 0, log)         # yedek olustu
        b = self.uzak()
        rc, log = self.akis("sahte-002", hata_oku="lsjson_bos_ana,cat")      # defter listede yok, okunamiyor, yedek var
        self.assertEqual(rc, 1); self.assertIn("yedek var", log); self.assertEqual(self.uzak(), b)

    def test_13_ayni_adli_iki_defter(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_oku="lsjson_cift")
        self.assertEqual(rc, 1); self.assertIn("belirsiz", log); self.assertEqual(self.uzak(), b)

    def test_14_logda_kimlik_yok(self):
        self.uzak({"gizli-receipt-123": {"sha256": "a" * 64, "onay_zamani": "x"}})

        def sil(p):
            v = json.loads(p.read_text()); v.pop("gizli-receipt-123"); p.write_text(json.dumps(v))
        rc, log = self.akis("sahte-001", bozma=sil)
        self.assertEqual(rc, 1); self.assertNotIn("gizli-receipt-123", log)

    def test_15_yedek_30_siniri_ve_eski_kok_yedekleri(self):
        self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        kok_eski = [self.uzak_dir / f"ONAYLAR_YEDEK_2026102{i}T000000000000Z.json" for i in range(3)]
        for p in kok_eski:
            p.write_text("{}")                                     # kokteki eski yedekler: tasinmaz, silinmez
        yd = self.uzak_dir / "YEDEK"; yd.mkdir()
        eski = [yd / f"ONAYLAR_202610{g:02d}T000000000000Z_{g}.json" for g in range(1, 31)]
        for p in eski:
            p.write_text("{}")
        rc, log = self.akis("sahte-001")
        self.assertEqual(rc, 0, log)
        self.assertEqual(len(self.yedekler()), 30); self.assertFalse(eski[0].exists())
        self.assertTrue(all(p.exists() for p in kok_eski))

    def test_16_kimlik_kaydi_yokken_basari_yok(self):         # defter degismedi ama kimlik kaydi yok -> FAIL (eski davranis)
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        os.environ["FAKE_HATA"] = ""
        self.assertEqual(self.kos("oku")[0], 0)
        rc, log = self.kos("yaz", "--kimlik", "sahte-001")
        self.assertEqual(rc, 1); self.assertIn("kaydi yok", log); self.assertEqual(self.uzak(), b)

    def test_10_defter_yazilamiyor(self):
        b = self.uzak({"eski-1": {"sha256": "a" * 64, "onay_zamani": "x"}})
        rc, log = self.akis("sahte-001", hata_yaz="copyto_ana")
        self.assertEqual(rc, 1); self.assertIn("uzaktaki defter simdi: onceki defter", log)
        self.assertEqual(self.uzak(), b); self.assertEqual(len(self.yedekler()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
