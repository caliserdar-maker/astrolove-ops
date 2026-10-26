#!/usr/bin/env python3
"""galeri_tasi.py yerel testi: sahte HTTP sunucu (127.0.0.1), gercek Canva / Drive yok.
Senaryolar: normal, 403, yanlis boyut, PNG, gecersiz cift, ORTAK yanlis kart_no, ayni ad ayni sha (ATLA),
ayni ad farkli sha (FAIL), iki farkli adda ayni sha (FAIL), hedef_damga ile ekleme (mevcut klasor) ve tamlik sayimi,
imzali URL'nin ciktilara yazilmamasi."""
import contextlib
import csv
import http.server
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_tasi as G  # noqa: E402

CIFTLER = HERE.parents[1] / "data/pod/pod78_ids.csv"
GIZLI = "X-Amz-Signature=GIZLI123"


def jpg(renk, boyut=(3000, 2250), fmt="JPEG"):
    b = io.BytesIO(); Image.new("RGB", boyut, renk).save(b, fmt, quality=90); return b.getvalue()


class Sunucu(http.server.BaseHTTPRequestHandler):
    DOSYA = {}

    def do_GET(self):  # noqa: N802
        yol = self.path.split("?")[0].lstrip("/")
        if yol == "yasak":
            self.send_response(403); self.end_headers(); return
        b = self.DOSYA.get(yol)
        if b is None:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


class GaleriTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for k in ("NO_PROXY", "no_proxy"):
            os.environ[k] = "127.0.0.1"
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sunucu)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        Sunucu.DOSYA.update({f"r{i}": jpg((i * 3 % 256, i * 7 % 256, i * 11 % 256)) for i in range(1, 40)})
        Sunucu.DOSYA.update(kucuk=jpg((1, 2, 3), (3000, 2000)), png=jpg((4, 5, 6), fmt="PNG"))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.klasor, self.yeni, self.tsv = t / "drive", t / "yeni", t / "g.tsv"

    def tearDown(self):
        self.tmp.cleanup()

    def kos(self, satirlar, baslik=True):
        txt = ("cift\tkart_no\tdesign_id\turl\n" if baslik else "") + "".join(
            f"{c}\t{k}\tDAX{i}\t{self.url}/{y}?{GIZLI}\n" for i, (c, k, y) in enumerate(satirlar))
        self.tsv.write_text(txt)
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = G.main(["--tsv", str(self.tsv), "--klasor", str(self.klasor), "--yeni", str(self.yeni), "--ciftler", str(CIFTLER)])
        log = o.getvalue()
        m = {r["ad"]: r for r in csv.DictReader(open(self.yeni / "MANIFEST.csv"))}
        return rc, log, m

    def yayinla(self):                       # sahte rclone yerine: yeni dosyalari Drive yansisina tasi (bir sonraki kosu icin)
        for p in self.yeni.glob("*"):
            (self.klasor / p.name).write_bytes(p.read_bytes()); p.unlink()

    def test_01_normal_ve_tamlik(self):
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "r1"), ("AQUARIUS_AQUARIUS", 3, "r2"), ("ORTAK", 4, "r3"), ("ORTAK", 5, "r4")])
        self.assertEqual(rc, 0, log)
        self.assertEqual({k for k, v in m.items() if v["durum"] == "YENI"}, {"AQUARIUS_AQUARIUS_G2.jpg", "AQUARIUS_AQUARIUS_G3.jpg", "ORTAK_G4.jpg", "ORTAK_G5.jpg"})
        self.assertTrue((self.yeni / "ORTAK_G4.jpg").exists())
        oz = (self.yeni / "OZET.md").read_text()
        self.assertIn("4 / 470", oz); self.assertIn("AQUARIUS_AQUARIUS: G6, G7, G8, G9", oz)

    def test_02_403(self):
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "yasak"), ("AQUARIUS_AQUARIUS", 3, "r1")])
        self.assertEqual(rc, 1); self.assertIn("HTTP 403", m["AQUARIUS_AQUARIUS_G2.jpg"]["durum"])
        self.assertEqual(m["AQUARIUS_AQUARIUS_G3.jpg"]["durum"], "YENI")
        self.assertFalse((self.yeni / "AQUARIUS_AQUARIUS_G2.jpg").exists())

    def test_03_boyut_ve_png(self):
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "kucuk"), ("AQUARIUS_AQUARIUS", 3, "png")])
        self.assertEqual(rc, 1)
        self.assertIn("boyut 3000x2000", m["AQUARIUS_AQUARIUS_G2.jpg"]["durum"]); self.assertIn("JPEG degil", m["AQUARIUS_AQUARIUS_G3.jpg"]["durum"])
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_04_gecersiz_cift_ve_ortak_kart(self):
        rc, log, m = self.kos([("SUN_MOON", 2, "r1"), ("ORTAK", 2, "r2"), ("AQUARIUS_AQUARIUS", 4, "r3"), ("AQUARIUS_AQUARIUS", 1, "r4")])
        self.assertEqual(rc, 1)
        d = [v["durum"] for v in m.values()]
        self.assertEqual(sum(x.startswith("FAIL") for x in d), 4, d)
        self.assertFalse(list(self.yeni.glob("*.jpg")))

    def test_05_ayni_ad_ayni_sha_atla_ve_hedef_damga(self):
        self.assertEqual(self.kos([("AQUARIUS_AQUARIUS", 2, "r1"), ("ORTAK", 4, "r2")])[0], 0)
        self.yayinla()
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "r1"), ("AQUARIUS_ARIES", 2, "r5")])
        self.assertEqual(rc, 0, log)
        self.assertTrue(m["AQUARIUS_AQUARIUS_G2.jpg"]["durum"].startswith("ATLA"))
        self.assertEqual(m["ORTAK_G4.jpg"]["durum"], "MEVCUT"); self.assertEqual(m["AQUARIUS_ARIES_G2.jpg"]["durum"], "YENI")
        self.assertFalse((self.yeni / "AQUARIUS_AQUARIUS_G2.jpg").exists())       # tekrar yuklenmez
        self.assertIn("3 / 470", (self.yeni / "OZET.md").read_text())
        self.assertEqual(m["ORTAK_G4.jpg"]["design_id"], "DAX1")                   # eski MANIFEST'ten

    def test_06_ayni_ad_farkli_sha(self):
        self.kos([("AQUARIUS_AQUARIUS", 2, "r1")]); self.yayinla()
        onceki = (self.klasor / "AQUARIUS_AQUARIUS_G2.jpg").read_bytes()
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "r6")])
        self.assertEqual(rc, 1); self.assertIn("farkli sha256", [v for v in m.values() if v["durum"].startswith("FAIL")][0]["durum"])
        self.assertFalse((self.yeni / "AQUARIUS_AQUARIUS_G2.jpg").exists())
        self.assertEqual((self.klasor / "AQUARIUS_AQUARIUS_G2.jpg").read_bytes(), onceki)

    def test_07_iki_adda_ayni_sha(self):
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "r1"), ("AQUARIUS_AQUARIUS", 3, "r1"), ("ORTAK", 5, "r1")])
        self.assertEqual(rc, 1)
        self.assertEqual(m["AQUARIUS_AQUARIUS_G2.jpg"]["durum"], "YENI")
        self.assertFalse((self.yeni / "AQUARIUS_AQUARIUS_G3.jpg").exists()); self.assertFalse((self.yeni / "ORTAK_G5.jpg").exists())
        self.kos([("AQUARIUS_ARIES", 2, "r7")]); self.yayinla()                  # klasorde onceden var olan cift kopya
        (self.klasor / "AQUARIUS_CANCER_G2.jpg").write_bytes((self.klasor / "AQUARIUS_ARIES_G2.jpg").read_bytes())
        rc, log, m = self.kos([("AQUARIUS_GEMINI", 2, "r8")])
        self.assertEqual(rc, 1); self.assertIn("2 adda ayni", m["AQUARIUS_CANCER_G2.jpg"]["durum"])

    def test_08_url_sizmaz(self):
        rc, log, m = self.kos([("AQUARIUS_AQUARIUS", 2, "r1"), ("AQUARIUS_AQUARIUS", 3, "yasak")])
        cikti = (self.yeni / "OZET.md").read_text() + (self.yeni / "MANIFEST.csv").read_text()
        self.assertNotIn("GIZLI123", cikti); self.assertNotIn("GIZLI123", log.replace(f"::add-mask::", "").split("[1/")[1])
        self.assertEqual(sum(1 for l in log.splitlines() if "GIZLI123" in l and not l.startswith("::add-mask::")), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
