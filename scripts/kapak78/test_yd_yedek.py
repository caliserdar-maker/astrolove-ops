#!/usr/bin/env python3
"""yd_yedek.py yerel testi (plan v3 adim 5): sahte HTTP sunucu (127.0.0.1), pilot HAM (test_veri/HAM_4595350971.json, gercek
yapi) url'leri sahte sunucuya cevrilir. Senaryolar: 13 dosya + boyut = JSON PASS; bir gorsel yanlis boyut FAIL; HAM dosyasi yok FAIL;
BAGLAR.csv 5 Style bagi (Botanical rank 12); paylasilan yedek_mb_kontrol.py'ye bagli degil."""
import contextlib
import csv
import http.server
import inspect
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yd_yedek as D  # noqa: E402

HAM = json.loads((HERE / "test_veri/HAM_4595350971.json").read_text())


class S(http.server.BaseHTTPRequestHandler):
    DOSYA = {}

    def do_GET(self):  # noqa: N802
        b = self.DOSYA.get(self.path.lstrip("/"))
        if b is None:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


def jpg(wh):
    b = io.BytesIO(); Image.new("RGB", wh, (10, 20, 30)).save(b, "JPEG", quality=60); return b.getvalue()


class YedekTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for k in ("NO_PROXY", "no_proxy"):
            os.environ[k] = "127.0.0.1"
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), S)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.ham, self.out = t / "HAM", t / "out"; self.ham.mkdir()
        self.ciftler = t / "yd.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def ilan(self, lid, cift, bozuk_rank=None):
        h = json.loads(json.dumps(HAM)); h["listing"]["listing_id"] = int(lid)
        for g in h["images"]:
            yol = f"{lid}/{g['listing_image_id']}.jpg"
            wh = (g["full_width"], g["full_height"])
            S.DOSYA[yol] = jpg((wh[0] - 8, wh[1]) if g["rank"] == bozuk_rank else wh)
            g["url_fullxfull"] = f"{self.url}/{yol}"
        (self.ham / f"{lid}.json").write_text(json.dumps(h))
        return f"{lid},{cift},A,B\n"

    def kos(self, satir):
        self.ciftler.write_text("listing_id,cift,a,b\n" + "".join(satir))
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = D.main(["--ham-dir", str(self.ham), "--ciftler", str(self.ciftler), "--out", str(self.out)])
        return rc, o.getvalue(), (self.out / "OZET.md").read_text()

    def test_01_pass_13_ve_baglar(self):
        rc, log, oz = self.kos([self.ilan("4595350971", "CANCER_LIBRA")])
        self.assertEqual(rc, 0, log + oz)
        self.assertIn("ilan PASS 1/1 | dosya 13 (beklenen 13)", oz)
        d = self.out / "4595350971_CANCER_LIBRA"
        self.assertEqual(len(list(d.glob("r*_*.jpg"))), 13); self.assertTrue((d / "r1_8760104081.jpg").exists())
        b = list(csv.DictReader(open(self.out / "BAGLAR.csv")))
        self.assertEqual(len(b), 5)
        self.assertEqual([(x["stil"], x["rank"]) for x in b if x["stil"] == "Botanical"], [("Botanical", "12")])
        self.assertEqual(len(json.loads((d / "GALERI.json").read_text())["gorseller"]), 13)

    def test_02_boyut_ve_ham_eksik_fail(self):
        rc, log, oz = self.kos([self.ilan("4595350971", "CANCER_LIBRA", bozuk_rank=5), "4595373190,AQUARIUS_AQUARIUS,A,B\n"])
        self.assertEqual(rc, 1)
        self.assertIn("r5 boyut 3192x2400 != 3200x2400", oz); self.assertIn("| 4595373190 | AQUARIUS_AQUARIUS | 0 | FAIL | HAM dosyasi yok |", oz)
        self.assertIn("HAM eksik 1", log)

    def test_03_paylasilan_dosyaya_bagli_degil(self):
        self.assertNotIn("yedek_mb_kontrol", (HERE / "yd_yedek.py").read_text().split('"""', 2)[2])
        self.assertEqual(inspect.signature(D.yedek).parameters["beklenen"].default, 13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
