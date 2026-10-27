#!/usr/bin/env python3
"""galeri_tasi.py --urun yd yerel testi (plan v3 adim 2; 10'lu galeri, Serdar 27 Eki): sahte HTTP sunucu (127.0.0.1), gercek Canva / Drive yok.
Senaryolar: 3000x2250 kabul / 2400x2400 red (Merkez 27 Eki karar e: tum kartlar 4:3), ORTAK yalniz Y04 (karar d), KAPAK_<CIFT>.jpg adi, beklenen 78 listesi, 3 sutun satir FAIL (sessiz atlama yok),
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
        T.Sunucu.DOSYA.update({f"k{i}": T.jpg((i * 5 % 256, i * 13 % 256, 200), (3000, 2250)) for i in range(1, 20)})
        T.Sunucu.DOSYA.update(kare=T.jpg((9, 9, 9), (2400, 2400)))
        T.Sunucu.DOSYA.update({f"y{i}": T.jpg((i * 7 % 256, 90, i * 3 % 256), (3000, 2250)) for i in range(1, 12)})

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
        return rc, o.getvalue(), {r["ad"].split(":", 1)[-1]: r for r in m}, m     # satir<n>:<ad> -> <ad> (son satir)

    def yayinla(self):
        T.GaleriTest.yayinla(self)

    def test_01_kabul_ad_ve_78(self):
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1"))])
        self.assertEqual(rc, 0, log)
        self.assertEqual(m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"], "YENI")
        self.assertTrue((self.yeni / "AQUARIUS_AQUARIUS_Y01.jpg").exists())
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("1 / 703", oz); self.assertIn("## Eksik (702)", oz)
        self.assertIn("- CANCER_LIBRA: Y01, Y02, Y03, Y05, Y06, Y07, Y08, Y09, Y10\n", oz)

    def test_02_boyut_red(self):
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "kare"))])
        self.assertEqual(rc, 1)
        self.assertIn("boyut 2400x2400 != 3000x2250", m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_03_uc_sutun_ve_gecersiz_satir_fail(self):
        u = url(self.url, "k2")
        ham = ("cift\tkart_no\tdesign_id\turl\n\nAQUARIUS_AQUARIUS\tDAA\t" + url(self.url, "k1") + "\n"
               "AQUARIUS_ARIES\t1\tDAB\t" + u + "\n" "AQUARIUS_ARIES\t1\n")
        rc, log, m, rows = self.kos(None, ham=ham)
        self.assertEqual(rc, 1)
        f = [r for r in rows if r["durum"].startswith("FAIL TSV satiri")]
        self.assertEqual(len(f), 2, rows)                              # 3 sutun + 2 sutun; bos satir ve baslik sayilmaz
        self.assertEqual(m["AQUARIUS_ARIES_Y01.jpg"]["durum"], "YENI")
        self.assertNotIn("AQUARIUS_AQUARIUS_Y01.jpg", m)

    def test_04_metin_kapi_ve_kart_no(self):
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAX", url(self.url, "k1")),      # design farkli
                                     ("ARIES_LEO", 1, "DAC", url(self.url, "k2")),              # METIN_KAPI FAIL
                                     ("AQUARIUS_ARIES", 2, "DAB", url(self.url, "kare")),       # kart_no 2, kare boyut
                                     ("SUN_MOON", 1, "DAZ", url(self.url, "k4"))])              # cift yok
        self.assertEqual(rc, 1)
        d = [r["durum"] for r in rows]
        self.assertEqual(sum(x.startswith("FAIL") for x in d), 4, d)
        self.assertIn("METIN_KAPI", m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"])
        self.assertIn("cift PASS degil", m["ARIES_LEO_Y01.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_05_sure_az_ve_parametresiz(self):
        az = url(self.url, "k1", sure=600 + 299)                      # kalan 299 sn
        yeter = url(self.url, "k2", sure=600 + 301)                   # kalan 301 sn
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", az), ("AQUARIUS_ARIES", 1, "DAB", yeter),
                                     ("CANCER_LIBRA", 1, "DAHZIAyOYA8", f"{self.url}/k3?X-Amz-Signature=GIZLI123")])
        self.assertEqual(rc, 1)
        self.assertTrue(m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"].startswith("SURE_AZ"))
        self.assertFalse((self.yeni / "AQUARIUS_AQUARIUS_Y01.jpg").exists())
        self.assertEqual(m["AQUARIUS_ARIES_Y01.jpg"]["durum"], "YENI")
        self.assertIn("link suresi okunamadi", m["CANCER_LIBRA_Y01.jpg"]["durum"])
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
        self.assertTrue(m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"].startswith("DUR ayni imza"))
        self.assertEqual(m["AQUARIUS_ARIES_Y01.jpg"]["durum"], "YENI")
        self.yayinla()
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1", imza="YENI2")),             # yeniden aktarim
                                  ("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k2", imza="YENI3"))])              # ayni dosya
        self.assertEqual(rc, 0, log)
        self.assertEqual(m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"], "YENI")
        self.assertTrue(m["AQUARIUS_ARIES_Y01.jpg"]["durum"].startswith("ATLA"))
        self.assertIn("2 / 703", (self.yeni / "OZET.md").read_text())
        self.assertEqual(len(list(csv.DictReader(open(self.yeni / "IMZA.csv")))), 4)   # DAA/GIZLI, DAB/YENI1, DAA/YENI2, DAB/YENI3

    def test_07_ayni_ad_farkli_sha_ve_iki_adda_ayni_sha(self):
        self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k1"))]); self.yayinla()
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k5", imza="B")),
                                     ("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k1", imza="C"))])
        self.assertEqual(rc, 1)
        d = [r["durum"] for r in rows if r["durum"].startswith("FAIL")]
        self.assertTrue(any("farkli sha256" in x for x in d) and any("baska adla ayni" in x for x in d), d)
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_08_klasordeki_kare_boyut_fail_ve_url_sizmaz(self):
        self.klasor.mkdir(parents=True)
        (self.klasor / "CANCER_LIBRA_Y01.jpg").write_bytes(T.Sunucu.DOSYA["kare"])
        rc, log, m, _ = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "yasak"))])
        self.assertEqual(rc, 1)
        self.assertIn("FAIL klasordeki dosya (boyut 2400x2400)", m["CANCER_LIBRA_Y01.jpg"]["durum"])
        self.assertIn("HTTP 403", m["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"])
        cikti = "".join((self.yeni / f).read_text() for f in ("OZET.md", "MANIFEST.csv", "IMZA.csv"))
        self.assertNotIn("GIZLI123", cikti)
        self.assertEqual(sum(1 for ln in log.splitlines() if "GIZLI123" in ln and not ln.startswith("::add-mask::")), 0)
        self.assertIn("0 / 703", (self.yeni / "OZET.md").read_text())

    def test_09_metin_kapi_zorunlu(self):
        self.tsv.write_text("cift\tkart_no\tdesign_id\turl\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER),
                         "--urun", "yd"])
        self.assertEqual(rc, 1)

    def test_10_tekrar_gonderilen_satir_dosya_satirini_bozmaz(self):
        u = url(self.url, "k1")
        self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", u)]); self.yayinla()
        self.kapi.write_text(self.kapi.read_text().replace("AQUARIUS_AQUARIUS\tDAA", "AQUARIUS_AQUARIUS\tDAA"))
        rc, log, m, rows = self.kos([("AQUARIUS_AQUARIUS", 1, "DAA", u),                                  # ayni link (ayni imza)
                                     ("AQUARIUS_AQUARIUS", 1, "DAA", url(self.url, "k6", imza="B")),      # farkli bayt
                                     ("AQUARIUS_AQUARIUS", 1, "DAX", url(self.url, "k1", imza="C"))])     # METIN_KAPI uyusmaz
        ad = {r["ad"]: r for r in rows}
        self.assertTrue(ad["AQUARIUS_AQUARIUS_Y01.jpg"]["durum"].startswith("ATLA (dosya mevcut, ayni imza"), rows)
        self.assertEqual(ad["AQUARIUS_AQUARIUS_Y01.jpg"]["design_id"], "DAA")
        self.assertEqual(sum(1 for r in rows if r["ad"] == "AQUARIUS_AQUARIUS_Y01.jpg"), 1)
        self.assertEqual(sorted(r["ad"].split(":")[0] for r in rows if r["durum"].startswith("FAIL")), ["satir3", "satir4"])
        self.assertIn("1 / 703", (self.yeni / "OZET.md").read_text())
        self.yayinla()                                                                             # sonraki kosu: design_id korunur
        rc, log, m, rows = self.kos([("AQUARIUS_ARIES", 1, "DAB", url(self.url, "k2", imza="D"))])
        self.assertEqual({r["ad"]: r for r in rows}["AQUARIUS_AQUARIUS_Y01.jpg"]["design_id"], "DAA")

    def test_11_on_kart_ve_ortak(self):
        self.kapi.write_text(self.kapi.read_text() + "ORTAK\tDORT\tYD ortak\t-\tPASS\n")
        satir = [("CANCER_LIBRA", k, "DAHZIAyOYA8", url(self.url, f"k{k}" if k in (1, 6, 7, 8, 9, 10) else f"y{k}", imza=f"S{k}"))
                 for k in (1, 2, 3, 5, 6, 7, 8, 9, 10)]
        satir += [("ORTAK", 4, "DORT", url(self.url, "y4", imza="O4"))]
        rc, log, m, rows = self.kos(satir + [("CANCER_LIBRA", 2, "DAHZIAyOYA8", url(self.url, "kare", imza="X")),  # kare -> kart 2 red
                                             ("ORTAK", 5, "DORT", url(self.url, "y7", imza="O5")),                 # Y05 artik cifte ozel
                                             ("CANCER_LIBRA", 4, "DAHZIAyOYA8", url(self.url, "y6", imza="Y")),     # cift kart 4
                                             ("ORTAK", 6, "DORT", url(self.url, "k12", imza="Z")),                 # ORTAK kart 6
                                             ("CANCER_LIBRA", 11, "DAHZIAyOYA8", url(self.url, "k13", imza="W"))])
        yeni = sorted(r["ad"] for r in rows if r["durum"] == "YENI")
        self.assertEqual(yeni, sorted([f"CANCER_LIBRA_Y{k:02d}.jpg" for k in (1, 2, 3, 5, 6, 7, 8, 9, 10)] + ["ORTAK_Y04.jpg"]), rows)
        f = [r["durum"] for r in rows if r["durum"].startswith("FAIL")]
        self.assertEqual(len(f), 5, f)
        self.assertTrue(any("boyut 2400x2400 != 3000x2250" in x for x in f) and any("yalniz ORTAK" in x for x in f)
                        and any("ORTAK yalniz kart 4 olabilir (kart 5)" in x for x in f)
                        and any("ORTAK yalniz kart 4 olabilir (kart 6)" in x for x in f) and any("1..10" in x for x in f), f)
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("10 / 703", oz); self.assertNotIn("- CANCER_LIBRA:", oz)

    def test_12_metin_kapi_kart_no_sutunu(self):
        self.kapi.write_text("cift\tkart_no\tdesign_id\tbaslik\tsatir_metni\tdurum\n"
                             "CANCER_LIBRA\t1\tDK1\tb\tCancer & Libra\tPASS\nCANCER_LIBRA\t6\tDK6\tb\t-\tPASS\n")
        rc, log, m, rows = self.kos([("CANCER_LIBRA", 1, "DK1", url(self.url, "k1")), ("CANCER_LIBRA", 6, "DK1", url(self.url, "k2", imza="B"))])
        d = {r["ad"]: r["durum"] for r in rows}
        self.assertEqual(d["CANCER_LIBRA_Y01.jpg"], "YENI"); self.assertIn("kart_no, design_id) ayni degil", d["satir3:CANCER_LIBRA_Y06.jpg"])
        self.kapi.write_text("cift\tkart_no\tdesign_id\tbaslik\tsatir_metni\tdurum\nCANCER_LIBRA\t\tDK1\tb\t-\tPASS\n")
        with self.assertRaises(SystemExit):
            self.kos([("CANCER_LIBRA", 1, "DK1", url(self.url, "k1"))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
