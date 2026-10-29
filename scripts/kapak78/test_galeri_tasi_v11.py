#!/usr/bin/env python3
"""galeri_tasi.py --urun v11 yerel testi (Merkez 29 Eki, WA_V11_TSV_BICIM.md): sahte HTTP sunucu (127.0.0.1), gercek Canva / Drive yok.
Senaryolar: kabul + ad <CIFT>_<ad>.jpg + 390 tamlik + W02-W06 UYGULANAMAZ, baslik zorunlu, sayfa kapisi, METIN_KAPI (yok / FAIL /
ust_satir / cift_satiri / etiket_yok yeniden denetimi), SURE_AZ (url_bitis_utc ve X-Amz'nin kucugu), url_bitis_utc bozuk FAIL,
ayni imza DUR (imzasiz url: sha256(url)), ayni ad farkli sha FAIL, iki adda ayni sha FAIL, boyut / PNG red, klasorde bilinmeyen jpg,
imzali URL'nin ciktilara yazilmamasi. yd / poster profili testleri ayri dosyalarda aynen."""
import contextlib
import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_tasi as G  # noqa: E402
import test_galeri_tasi as T  # noqa: E402  (ayni sahte sunucu)

CIFTLER = HERE.parents[1] / "data/pod/pod78_ids.csv"
SIMDI = 1793000000.0
TARIH = G.time.strftime("%Y%m%dT%H%M%SZ", G.time.gmtime(SIMDI - 600))


def bitis(sn):
    return G.time.strftime("%Y-%m-%dT%H:%M:%SZ", G.time.gmtime(SIMDI + sn))


def url(base, yol, imza="GIZLI123", sure=3600):
    return (f"{base}/{yol}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date={TARIH}&X-Amz-Expires={sure}"
            f"&X-Amz-SignedHeaders=host&X-Amz-Signature={imza}")


MK = {"W01_KAPAK": "Personalized Zodiac Couple Gift", "W07_MB": "Midnight Blue", "W08_DB": "Deep Black", "W09_PW": "Pure White",
      "W10_WP": "Warm Parchment"}
SAYFA = {"W01_KAPAK": 1, "W07_MB": 1, "W08_DB": 1, "W09_PW": 2, "W10_WP": 3}
DID = {"W01_KAPAK": "DK", "W07_MB": "DM", "W08_DB": "DR", "W09_PW": "DR", "W10_WP": "DR"}


class V11Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        T.GaleriTest.setUpClass.__func__(cls)
        T.Sunucu.DOSYA.update({f"v{i}": T.jpg((i * 9 % 256, i * 17 % 256, 120), (3000, 2250)) for i in range(1, 30)})
        T.Sunucu.DOSYA.update(kare=T.jpg((9, 9, 9), (2400, 2400)), png=T.jpg((4, 5, 6), fmt="PNG"))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.klasor, self.yeni, self.tsv, self.kapi = t / "drive", t / "yeni", t / "CANVA.tsv", t / "METIN_KAPI.tsv"
        self.mk([])

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, ek):
        """varsayilan: CANCER_LIBRA ve AQUARIUS_ARIES 5 kart PASS; ek: (cift, ad, design_id, ust, cift_satiri, etiket_yok, durum)"""
        rows = [(c, ad, f"{DID[ad]}{c[:2]}", MK[ad], cs, "1", "PASS") for c, cs in (("CANCER_LIBRA", "Cancer & Libra"),
                                                                                   ("AQUARIUS_ARIES", "Aquarius & Aries")) for ad in MK]
        self.kapi.write_text("cift\tad\tdesign_id\tust_satir\tcift_satiri\tetiket_yok\tdurum\n"
                             + "".join("\t".join(r) + "\n" for r in rows + list(ek)))

    def kos(self, satirlar, ham=""):
        """satirlar: (cift, ad, design_id, sayfa, url, url_bitis_utc)"""
        txt = ham or "cift\tad\tdesign_id\tsayfa\turl\turl_bitis_utc\n" + "".join("\t".join(map(str, r)) + "\n" for r in satirlar)
        self.tsv.write_text(txt)
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER),
                         "--urun", "v11", "--metin-kapi", str(self.kapi), "--simdi", str(SIMDI)])
        m = list(csv.DictReader(open(self.yeni / "MANIFEST.csv")))
        return rc, o.getvalue(), {r["ad"].split(":", 1)[-1]: r for r in m}, m

    def satir(self, c, ad, kaynak, imza="GIZLI123", sn=3600, did=None):
        return (c, ad, did or f"{DID[ad]}{c[:2]}", SAYFA[ad], url(self.url, kaynak, imza=imza), bitis(sn))

    def yayinla(self):
        T.GaleriTest.yayinla(self)

    def test_01_kabul_ad_tamlik(self):
        rc, log, m, _ = self.kos([self.satir("CANCER_LIBRA", ad, f"v{i}") for i, ad in enumerate(MK, 1)])
        self.assertEqual(rc, 0, log)
        self.assertEqual({k for k, v in m.items() if v["durum"] == "YENI"}, {f"CANCER_LIBRA_{ad}.jpg" for ad in MK})
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("5 / 390", oz); self.assertIn("UYGULANAMAZ", oz); self.assertIn("## Eksik (385)", oz)
        self.assertIn("- AQUARIUS_ARIES: W01, W07, W08, W09, W10\n", oz)
        for f in ("MANIFEST.csv", "OZET.md", "IMZA.csv"):
            self.assertNotIn("GIZLI123", (self.yeni / f).read_text())
        self.assertFalse([x for x in log.splitlines() if "GIZLI123" in x and not x.startswith("::add-mask::")])   # yalniz maske satiri

    def test_02_baslik_zorunlu_ve_sutun(self):
        u = url(self.url, "v1")
        rc, log, m, rows = self.kos(None, ham=f"CANCER_LIBRA\tW01_KAPAK\tDKCA\t1\t{u}\t{bitis(3600)}\n")
        self.assertEqual(rc, 1); self.assertIn("basligi", rows[0]["durum"])
        ham = ("cift\tad\tdesign_id\tsayfa\turl\turl_bitis_utc\n" f"CANCER_LIBRA\tW01_KAPAK\tDKCA\t1\t{u}\n"
               f"CANCER_LIBRA\tW07_MB\tDMCA\t1\t{url(self.url, 'v2')}\t{bitis(3600)}\n")
        rc, log, m, rows = self.kos(None, ham=ham)
        self.assertEqual(rc, 1)
        self.assertEqual(sum(r["durum"].startswith("FAIL TSV satiri") for r in rows), 1)
        self.assertEqual(m["CANCER_LIBRA_W07_MB.jpg"]["durum"], "YENI")

    def test_03_ad_sayfa_cift(self):
        rc, log, m, rows = self.kos([("CANCER_LIBRA", "W02_SEMBOL", "DX", 1, url(self.url, "v1"), bitis(3600)),
                                     ("CANCER_LIBRA", "W09_PW", "DRCA", 1, url(self.url, "v2"), bitis(3600)),
                                     ("SUN_MOON", "W01_KAPAK", "DKSU", 1, url(self.url, "v3"), bitis(3600)),
                                     ("ORTAK", "W07_MB", "DMOR", 1, url(self.url, "v4"), bitis(3600))])
        self.assertEqual(rc, 1)
        d = " | ".join(r["durum"] for r in rows)
        self.assertIn("ad W02_SEMBOL", d); self.assertIn("sayfa 1 != 2", d); self.assertEqual(d.count("pod78 listesinde yok"), 2)
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_04_metin_kapi_yeniden_denetim(self):
        self.mk([("ARIES_LEO", "W01_KAPAK", "DKAR", MK["W01_KAPAK"], "Aries & Leo", "1", "FAIL"),
                 ("ARIES_LIBRA", "W07_MB", "DMAR", "Midnight blue", "Aries & Libra", "1", "PASS"),
                 ("ARIES_PISCES", "W08_DB", "DRAR", "Deep Black", "Pisces & Aries", "1", "PASS"),
                 ("ARIES_SCORPIO", "W10_WP", "DRAR", "Warm Parchment", "Aries & Scorpio", "0", "PASS")])
        rc, log, m, rows = self.kos([self.satir("ARIES_LEO", "W01_KAPAK", "v1"), self.satir("ARIES_LIBRA", "W07_MB", "v2"),
                                     self.satir("ARIES_PISCES", "W08_DB", "v3"), self.satir("ARIES_SCORPIO", "W10_WP", "v4"),
                                     self.satir("CANCER_LIBRA", "W01_KAPAK", "v5", did="BASKA")])
        self.assertEqual(rc, 1)
        self.assertIn("durum FAIL", m["ARIES_LEO_W01_KAPAK.jpg"]["durum"])
        self.assertIn("ust_satir", m["ARIES_LIBRA_W07_MB.jpg"]["durum"])
        self.assertIn("cift_satiri", m["ARIES_PISCES_W08_DB.jpg"]["durum"])
        self.assertIn("etiket_yok 0", m["ARIES_SCORPIO_W10_WP.jpg"]["durum"])
        self.assertIn("satiri yok", m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_05_sure(self):
        rc, log, m, _ = self.kos([self.satir("CANCER_LIBRA", "W01_KAPAK", "v1", sn=299),               # url_bitis 299 sn
                                  ("CANCER_LIBRA", "W07_MB", "DMCA", 1, url(self.url, "v2", sure=600 + 200), bitis(3600)),  # X-Amz 200 sn
                                  self.satir("CANCER_LIBRA", "W08_DB", "v3", sn=301),
                                  ("CANCER_LIBRA", "W09_PW", "DRCA", 2, url(self.url, "v4"), "29 Eki 14:00"),
                                  ("CANCER_LIBRA", "W10_WP", "DRCA", 3, url(self.url, "v5"), "2026-10-29T14:00:00+03:00")])
        self.assertEqual(rc, 1)
        self.assertTrue(m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"].startswith("SURE_AZ"))
        self.assertTrue(m["CANCER_LIBRA_W07_MB.jpg"]["durum"].startswith("SURE_AZ"))
        self.assertEqual(m["CANCER_LIBRA_W08_DB.jpg"]["durum"], "YENI")
        self.assertIn("url_bitis_utc okunamadi", m["CANCER_LIBRA_W09_PW.jpg"]["durum"])
        self.assertIn("url_bitis_utc okunamadi", m["CANCER_LIBRA_W10_WP.jpg"]["durum"])
        self.assertFalse((self.yeni / "CANCER_LIBRA_W01_KAPAK.jpg").exists())

    def test_06_imza_dur_imzasiz_url(self):
        u = f"{self.url}/v1?token=ABC"                                     # X-Amz yok: imza ozeti sha256(url)
        rc, log, m, _ = self.kos([("CANCER_LIBRA", "W01_KAPAK", "DKCA", 1, u, bitis(200))])   # SURE_AZ, imza kaydedilir
        self.assertEqual(rc, 1); self.yayinla()
        self.assertNotIn("ABC", (self.klasor / "IMZA.csv").read_text())
        rc, log, m, _ = self.kos([("CANCER_LIBRA", "W01_KAPAK", "DKCA", 1, u, bitis(3600))])
        self.assertTrue(m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"].startswith("DUR ayni imza"))
        rc, log, m, _ = self.kos([("CANCER_LIBRA", "W01_KAPAK", "DKCA", 1, f"{self.url}/v1?token=YENI", bitis(3600))])
        self.assertEqual(m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"], "YENI", log)

    def test_07_sha_kurallari_ve_bicim(self):
        self.kos([self.satir("CANCER_LIBRA", "W01_KAPAK", "v1")]); self.yayinla()
        rc, log, m, rows = self.kos([self.satir("CANCER_LIBRA", "W01_KAPAK", "v6", imza="B"),        # ayni ad farkli sha
                                     self.satir("AQUARIUS_ARIES", "W01_KAPAK", "v1", imza="C"),      # baska adla ayni sha
                                     self.satir("AQUARIUS_ARIES", "W07_MB", "kare"), self.satir("AQUARIUS_ARIES", "W08_DB", "png")])
        self.assertEqual(rc, 1)
        d = " | ".join(r["durum"] for r in rows)
        self.assertIn("ayni ad, farkli sha256", d); self.assertIn("baska adla ayni: CANCER_LIBRA_W01_KAPAK.jpg", d)
        self.assertIn("boyut 2400x2400", d); self.assertIn("JPEG degil (PNG)", d)
        self.assertEqual(m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"], "FAIL ayni ad, farkli sha256 (uzerine yazilmaz)")
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_08_iki_adda_ayni_sha_klasorde_ve_bilinmeyen(self):
        self.klasor.mkdir(parents=True)
        b = T.Sunucu.DOSYA["v9"]
        (self.klasor / "CANCER_LIBRA_W07_MB.jpg").write_bytes(b); (self.klasor / "CANCER_LIBRA_W08_DB.jpg").write_bytes(b)
        (self.klasor / "CANCER_LIBRA_S1_SEMBOL.jpg").write_bytes(T.Sunucu.DOSYA["v10"])
        rc, log, m, _ = self.kos([self.satir("CANCER_LIBRA", "W01_KAPAK", "v1")])
        self.assertEqual(rc, 1)
        self.assertIn("2 adda ayni", m["CANCER_LIBRA_W07_MB.jpg"]["durum"])
        self.assertIn("jpg 1 (BILINMEYEN", (self.yeni / "OZET.md").read_text())
        self.assertNotIn("CANCER_LIBRA_S1_SEMBOL.jpg", m)

    def test_09_tsv_tekrar_ad(self):
        rc, log, m, rows = self.kos([self.satir("CANCER_LIBRA", "W01_KAPAK", "v1"), self.satir("CANCER_LIBRA", "W01_KAPAK", "v2", imza="Z")])
        self.assertEqual(rc, 1)
        self.assertIn("TSV'de ayni ad iki satir", " | ".join(r["durum"] for r in rows))

    def test_10_onayli_ornek(self):
        self.kapi.unlink()
        self.tsv.write_text("cift\tad\tdesign_id\tsayfa\turl\turl_bitis_utc\n" + "".join("\t".join(map(str, r)) + "\n" for r in [
            self.satir("CANCER_LIBRA", "W01_KAPAK", "v1"), self.satir("AQUARIUS_ARIES", "W07_MB", "v2")]))
        with contextlib.redirect_stdout(io.StringIO()):
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER),
                         "--urun", "v11", "--onayli-ornek", "--simdi", str(SIMDI)])
        m = {r["ad"].split(":", 1)[-1]: r for r in csv.DictReader(open(self.yeni / "MANIFEST.csv"))}
        self.assertEqual(rc, 1)
        self.assertEqual(m["CANCER_LIBRA_W01_KAPAK.jpg"]["durum"], "YENI")
        self.assertIn("yalniz CANCER_LIBRA", m["AQUARIUS_ARIES_W07_MB.jpg"]["durum"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
