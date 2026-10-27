#!/usr/bin/env python3
"""yd_kapak_qc.py yerel testi (plan v3 adim 4), SAHTE gorsellerle (gercek kapak / Canva yok):
sahne sablonu 2400x2400 + cift basina kaynak 2400x3000 (farkli doku) -> kapak = sahne + kutuya olceklenmis kaynak kirpimi +
cift satiri. Senaryolar: olc kutuyu ve kirpimi bulur (+-3 px); dogru kapak yuksek NCC + en_yakin kendi cifti; yanlis kaynak
(ters cift) en_yakin ile FAIL; 3000x2250 FAIL; esik yoksa OLCUM (PASS yok); esikle PASS / FAIL; METIN_KAPI FAIL; kontak sayfasi."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yd_kapak_qc as Q  # noqa: E402

KUTU = [520, 300, 1720, 1800]          # 1200 x 1500
KIRP = [200, 250, 2200, 2750]          # olcek 0.6
SATIR = [700, 1900, 1700, 2010]
CIFTLER = ["AQUARIUS_AQUARIUS", "AQUARIUS_ARIES", "CANCER_LIBRA", "LEO_VIRGO"]
KID = {c: str(8000000000 + i) for i, c in enumerate(CIFTLER)}


def doku(seed, wh):
    r = np.random.default_rng(seed)
    w, h = wh
    out = np.zeros((h, w, 3), np.float32)
    for s, a in ((8, 60), (32, 50), (128, 40)):
        n = r.standard_normal((h // s + 2, w // s + 2, 3)).astype(np.float32)
        out += a * cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(out + 128, 0, 255).astype(np.uint8)


def kapak_yap(sahne, kaynak, metin, boyut=(2400, 2400)):
    im = sahne.copy()
    k = cv2.resize(kaynak[KIRP[1]:KIRP[3], KIRP[0]:KIRP[2]], (KUTU[2] - KUTU[0], KUTU[3] - KUTU[1]), interpolation=cv2.INTER_AREA)
    im[KUTU[1]:KUTU[3], KUTU[0]:KUTU[2]] = k
    p = Image.fromarray(im); ImageDraw.Draw(p).text((SATIR[0] + 20, SATIR[1] + 20), metin, fill=(255, 255, 255))
    return p.resize(boyut) if boyut != (2400, 2400) else p


class QcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); t = Path(cls.tmp.name)
        cls.kapak, cls.kaynak, cls.out = t / "kapak", t / "kaynak", t / "out"
        for d in (cls.kapak, cls.kaynak):
            d.mkdir()
        cls.sahne = doku(1, (2400, 2400))
        cls.src = {c: doku(10 + i, (2400, 3000)) for i, c in enumerate(CIFTLER)}
        for c in CIFTLER:
            Image.fromarray(cls.src[c]).save(cls.kaynak / f"{KID[c]}.jpg", quality=95)
        Image.fromarray(cls.sahne).save(t / "sahne_ref.jpg", quality=95)
        for c in CIFTLER[:2]:
            kapak_yap(cls.sahne, cls.src[c], c).save(cls.kapak / f"KAPAK_{c}.jpg", quality=95)
        kapak_yap(cls.sahne, cls.src["AQUARIUS_AQUARIUS"], "CANCER_LIBRA").save(cls.kapak / "KAPAK_CANCER_LIBRA.jpg", quality=95)  # yanlis kaynak
        kapak_yap(cls.sahne, cls.src["LEO_VIRGO"], "LEO_VIRGO", (3000, 2250)).save(cls.kapak / "KAPAK_LEO_VIRGO.jpg", quality=95)
        (t / "ciftler.csv").write_text("listing_id,cift,a,b\n" + "".join(f"{i},{c},x,y\n" for i, c in enumerate(CIFTLER)))
        (t / "kaynak.csv").write_text("listing_id,cift,tur,kaynak_image_id,kaynak_url,kaynak_boyut\n"
                                      + "".join(f"{i},{c},yd,{KID[c]},u,2400x3000\n" for i, c in enumerate(CIFTLER)))
        (t / "mk.tsv").write_text("cift\tdesign_id\tbaslik\tsatir_metni\tdurum\n" + "".join(
            f"{c}\tD{i}\tYD_KAPAK_V1 {c}\t{c}\t{'FAIL' if c == 'AQUARIUS_ARIES' else 'PASS'}\n" for i, c in enumerate(CIFTLER)))
        cls.t = t

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def kos(self, *ek):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = Q.main(["kontrol", "--kapak-dir", str(self.kapak), "--kaynak-dir", str(self.kaynak), "--kaynak-csv", str(self.t / "kaynak.csv"),
                         "--ciftler", str(self.t / "ciftler.csv"), "--sablon", str(self.sablon()), "--sahne-ref", str(self.t / "sahne_ref.jpg"),
                         "--out", str(self.out), *ek])
        J = json.loads((self.out / "QC_RAPOR.json").read_text())
        return rc, o.getvalue(), {s["cift"]: s for s in J["dosyalar"]}, J

    def sablon(self):
        p = self.t / "SABLON.json"
        if not p.exists():
            p.write_text(json.dumps(dict(kutu=KUTU, kaynak_kirp=KIRP, maske=[SATIR])))
        return p

    def test_01_olc_kutu_ve_kirp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = Q.main(["olc", "--kapak", str(self.kapak / "KAPAK_AQUARIUS_AQUARIUS.jpg"), "--kaynak", str(self.kaynak / f"{KID['AQUARIUS_AQUARIUS']}.jpg"),
                         "--kapak", str(self.kapak / "KAPAK_AQUARIUS_ARIES.jpg"), "--kaynak", str(self.kaynak / f"{KID['AQUARIUS_ARIES']}.jpg"),
                         "--out", str(self.t / "OLCUM.json")])
        self.assertEqual(rc, 0)
        R = json.loads((self.t / "OLCUM.json").read_text())["olcumler"]
        for r in R:
            self.assertLessEqual(max(abs(a - b) for a, b in zip(r["kutu"], KUTU)), 3, (r, KUTU))
            self.assertLessEqual(max(abs(a - b) for a, b in zip(r["kaynak_kirp"], KIRP)), 6, r)
            self.assertAlmostEqual(r["olcek"], 0.6, delta=0.005)
            self.assertGreater(r["ncc_poster"], 0.95, r)
        self.assertLessEqual(R[1]["kutu_sapma"], 6)                   # iki olcum arasi (her biri +-3 px)

    def test_02_olcum_esiksiz_pass_yok(self):
        rc, log, s, J = self.kos("--metin-kapi", str(self.t / "mk.tsv"))
        self.assertEqual(rc, 1, log)                                   # yanlis kaynak + boyut + metin kapisi FAIL
        a = s["AQUARIUS_AQUARIUS"]
        self.assertEqual(a["durum"], "OLCUM"); self.assertEqual(J["sayilar"]["PASS"], 0)
        self.assertGreater(a["ncc_poster"], 0.95); self.assertGreater(a["ncc_sahne"], 0.95); self.assertEqual(a["en_yakin"], "AQUARIUS_AQUARIUS")
        self.assertEqual(s["CANCER_LIBRA"]["durum"], "FAIL"); self.assertIn("kendi cifti degil", s["CANCER_LIBRA"]["neden"][0])
        self.assertIn("2400x2400", s["LEO_VIRGO"]["neden"][0])
        self.assertEqual(s["AQUARIUS_ARIES"]["durum"], "FAIL"); self.assertIn("METIN_KAPI", s["AQUARIUS_ARIES"]["neden"][0])
        self.assertTrue((self.out / "KONTAK.jpg").exists())
        self.assertEqual(Image.open(self.out / "KONTAK.jpg").size, (13 * 180, 214))

    def test_03_esikle_pass_ve_fail(self):
        (self.t / "esik.json").write_text(json.dumps(dict(poster_min=0.9, sahne_min=0.9)))
        rc, log, s, J = self.kos("--esik", str(self.t / "esik.json"))
        self.assertEqual(s["AQUARIUS_AQUARIUS"]["durum"], "PASS"); self.assertEqual(s["AQUARIUS_ARIES"]["durum"], "PASS")
        self.assertIn("ncc_poster", " ".join(s["CANCER_LIBRA"]["neden"]))   # kendi kaynagina gore dusuk NCC
        (self.t / "esik2.json").write_text(json.dumps(dict(poster_min=0.9, sahne_min=1.0001)))
        rc, log, s, J = self.kos("--esik", str(self.t / "esik2.json"))
        self.assertEqual(s["AQUARIUS_AQUARIUS"]["durum"], "FAIL"); self.assertIn("ncc_sahne", s["AQUARIUS_AQUARIUS"]["neden"][0])

    def test_04_sahne_maskesi_cift_satirini_disarida_birakir(self):
        rc, log, s, J = self.kos()
        self.assertGreater(s["AQUARIUS_ARIES"]["ncc_sahne"], 0.97)           # satir metni farkli, maske disinda ayni
        m = Q.sahne_maske(dict(kutu=KUTU, maske=[SATIR]), (1200, 1200), 2)
        self.assertFalse(m[SATIR[1] // 2 + 5, SATIR[0] // 2 + 5]); self.assertFalse(m[KUTU[1] // 2 + 5, KUTU[0] // 2 - 3])
        self.assertTrue(m[50, 50])


if __name__ == "__main__":
    unittest.main(verbosity=2)
