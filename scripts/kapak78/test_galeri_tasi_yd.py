#!/usr/bin/env python3
"""galeri_tasi.py --urun yd yerel testi (plan v3 adim 2): sahte HTTP sunucu (127.0.0.1), gercek Canva / Drive yok.
Senaryolar: 2400x2400 kabul / 3000x2250 red, KAPAK_<CIFT>.jpg adi, beklenen 78 listesi, 3 sutun satir FAIL (sessiz atlama yok),
METIN_KAPI uyusmazligi FAIL, SURE_AZ (5 dk alti indirilmez), ayni imza DUR, ikinci grup ayni klasore ekleme, imzanin ciktiya
yazilmamasi. Poster profili testleri ayri dosyada aynen (test_galeri_tasi.py)."""
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

CIFTLER = HERE.parents[1] / "data/pod/yd78_ids.csv"
SIMDI = 1793000000.0                                   # sabit saat (test)
TARIH = G.time.strftime("%Y%m%dT%H%M%SZ", G.time.gmtime(SIMDI - 600))   # 10 dk once imzalandi


def url(base, yol, imza="GIZLI123", sure=3600, tarih=TARIH):
    return (f"{base}/{yol}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date={tarih}&X-Amz-Expires={sure}"
            f"&X-Amz-SignedHeaders=host&X-Amz-Signature={imza}")


class YdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        T.GaleriTest.setUpClass.__func__(cls)
        T.Sunucu.DOSYA.update({f"k{i}": T.jpg((i * 5 % 256, i * 13 % 256, 200), (2400, 2400)) for i in range(1, 20)})
        T.Sunucu.DOSYA.update(poster=T.jpg((9, 9, 9), (3000, 2250)))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.klasor, self.yeni, self.tsv, self.kapi = t / "drive", t / "yeni", t / "g.tsv", t / "METIN_KAPI.tsv"
        self.kapi.write_text("cift\tdesign_id\tbaslik\tsatir_metni\tdurum\n"
                             "AQUARIUS_AQUARIUS\tDAA\tYD_KAPAK_V1 AQUARIUS_AQUARIUS\tAquarius & Aquarius\tPASS\n"
                             "AQUARIUS_ARIES\tDAB\tYD_KAPAK_V1 AQUARIUS_ARIES\tAquarius & Aries\tPASS\n"
                             "CANCER_LIBRA\tDAHZIAyOYA8\tYD_KAPAK_V1 CANCER_LIBRA\tCancer & Libra\tPASS\n"
                             "ARIES_LEO\tDAC\tYD Kapak Ornek ARIES_LEO\tAries & Lion\tFAIL\n")

    def tearDown(self):
        self.tmp.cleanup()

    def kos(self, satirlar, ham=""):
        """satirlar: (cift, kart_no, design_id, url) ya da ham TSV metni"""
        txt = ham or "cift\tkart_no\tdesign_id\turl\n" + "".join("\t".join(map(str, r)) + "\n" for r in satirlar)
        self.tsv.write_text(txt)
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER),
                         "--urun", "yd", "--metin-kapi", str(self.kapi), "--simdi", str(SIMDI)])
        m = list(csv.DictReader(open(self.yeni / "MANIFEST.csv")))
        return rc, o.getvalue(), {r["ad"]: r for r in m}, m

    def yayinla(self):
        T.GaleriTest.yayinla(self)

    def test_01_kabul_ad_ve_78(self):
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1"))])
        self.assertEqual(rc, 0, log)
        self.assertEqual(m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"], "YENI")
        self.assertTrue((self.yeni / "KAPAK_AQUARIUS_AQUARIUS.jpg").exists())
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("1 / 78", oz); self.assertIn("## Eksik (77)", oz); self.assertIn("- CANCER_LIBRA\n", oz)

    def test_02_boyut_red(self):
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "poster"))])
        self.assertEqual(rc, 1)
        self.assertIn("boyut 3000x2250 != 2400x2400", m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_03_uc_sutun_ve_gecersiz_satir_fail(self):
        u = url(self.url, "k2")
        ham = ("cift\tkart_no\tdesign_id\turl\n\nAQUARIUS_AQUARIUS\tDAA\t" + url(self.url, "k1") + "\n"
               "AQUARIUS_ARIES\t1\tDAB\t" + u + "\n" "AQUARIUS_ARIES\t1\n")
        rc, log, m, rows = self.kos(None, ham=ham)
        self.assertEqual(rc, 1)
        f = [r for r in rows if r["durum"].startswith("FAIL TSV satiri")]
        self.assertEqual(len(f), 2, rows)                              # 3 sutun + 2 sutun; bos satir ve baslik sayilmaz
        self.assertEqual(m["KAPAK_AQUARIUS_ARIES.jpg"]["durum"], "YENI")
        self.assertNotIn("KAPAK_AQUARIUS_AQUARIUS.jpg", m)

    def test_04_metin_kapi_ve_kart_no(self):
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAX", url(self.url, "k1")),      # design farkli
                                     ("ARIES_LEO", 1, "DAC", url(self.url, "k2")),              # METIN_KAPI FAIL
                                     ("AQUARIUS_ARIES", 2, "DAB", url(self.url, "k3")),         # kart_no 2
                                     ("SUN_MOON", 1, "DAZ", url(self.url, "k4"))])              # cift yok
        self.assertEqual(rc, 1)
        d = [r["durum"] for r in rows]
        self.assertEqual(sum(x.startswith("FAIL") for x in d), 4, d)
        self.assertIn("METIN_KAPI", m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"])
        self.assertIn("cift PASS degil", m["KAPAK_ARIES_LEO.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_05_sure_az_ve_parametresiz(self):
        az = url(self.url, "k1", sure=600 + 299)                      # kalan 299 sn
        yeter = url(self.url, "k2", sure=600 + 301)                   # kalan 301 sn
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", az), ("AQUARIUS_ARIES", 1, "DAB", yeter),
                                     ("CANCER_LIBRA", 1, "DAHZIAyOYA8", f"{self.url}/k3?X-Amz-Signature=GIZLI123")])
        self.assertEqual(rc, 1)
        self.assertTrue(m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"].startswith("SURE_AZ"))
        self.assertFalse((self.yeni / "KAPAK_AQUARIUS_AQUARIUS.jpg").exists())
        self.assertEqual(m["KAPAK_AQUARIUS_ARIES.jpg"]["durum"], "YENI")
        self.assertIn("link suresi okunamadi", m["KAPAK_CANCER_LIBRA.jpg"]["durum"])
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("## Yeniden disa aktar", oz); self.assertIn("AQUARIUS_AQUARIUS DAA: SURE_AZ", oz)

    def test_06_ayni_imza_dur_ve_ikinci_grup(self):
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1", sure=600 + 200))])   # SURE_AZ
        self.assertEqual(rc, 1); self.yayinla()
        self.assertIn("DAA", (self.klasor / "IMZA.csv").read_text())
        self.assertNotIn("GIZLI123", (self.klasor / "IMZA.csv").read_text())
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1", sure=600 + 200)),           # ayni imza
                                  ("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k2", imza="YENI1"))])
        self.assertEqual(rc, 1)
        self.assertTrue(m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"].startswith("DUR ayni imza"))
        self.assertEqual(m["KAPAK_AQUARIUS_ARIES.jpg"]["durum"], "YENI")
        self.yayinla()
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1", imza="YENI2")),             # yeniden aktarim
                                  ("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k2", imza="YENI3"))])              # ayni dosya
        self.assertEqual(rc, 0, log)
        self.assertEqual(m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"], "YENI")
        self.assertTrue(m["KAPAK_AQUARIUS_ARIES.jpg"]["durum"].startswith("ATLA"))
        self.assertIn("2 / 78", (self.yeni / "OZET.md").read_text())
        self.assertEqual(len(list(csv.DictReader(open(self.yeni / "IMZA.csv")))), 4)   # DAA/GIZLI, DAB/YENI1, DAA/YENI2, DAB/YENI3

    def test_07_ayni_ad_farkli_sha_ve_iki_adda_ayni_sha(self):
        self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1"))]); self.yayinla()
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k5", imza="B")),
                                     ("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k1", imza="C"))])
        self.assertEqual(rc, 1)
        d = [r["durum"] for r in rows if r["durum"].startswith("FAIL")]
        self.assertTrue(any("farkli sha256" in x for x in d) and any("baska adla ayni" in x for x in d), d)
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_08_klasordeki_poster_boyutu_fail_ve_url_sizmaz(self):
        self.klasor.mkdir(parents=True)
        (self.klasor / "KAPAK_CANCER_LIBRA.jpg").write_bytes(T.Sunucu.DOSYA["poster"])
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "yasak"))])
        self.assertEqual(rc, 1)
        self.assertIn("FAIL klasordeki dosya (boyut 3000x2250)", m["KAPAK_CANCER_LIBRA.jpg"]["durum"])
        self.assertIn("HTTP 403", m["KAPAK_AQUARIUS_AQUARIUS.jpg"]["durum"])
        cikti = "".join((self.yeni / f).read_text() for f in ("OZET.md", "MANIFEST.csv", "IMZA.csv"))
        self.assertNotIn("GIZLI123", cikti)
        self.assertEqual(sum(1 for ln in log.splitlines() if "GIZLI123" in ln and not ln.startswith("::add-mask::")), 0)
        self.assertIn("0 / 78", (self.yeni / "OZET.md").read_text())

    def test_09_metin_kapi_zorunlu(self):
        self.tsv.write_text("cift\tkart_no\tdesign_id\turl\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER),
                         "--urun", "yd"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
