#!/usr/bin/env python3
"""yd_kapak_qc.py yerel testi (plan v3 adim 4; 10'lu galeri, Merkez 27 Eki), SAHTE gorsellerle (gercek kart / Canva yok):
NCC kartlari (Y01, Y06-Y10) icin kart basina sahne sablonu 2400x2400 + cift x kart kaynak 2400x3000 (farkli doku) -> kart = sahne +
kutuya olceklenmis kaynak kirpimi + cift satiri; Y02 / Y03 cift basina 3000x2250, Y04 / Y05 ORTAK.
Senaryolar: olc kutuyu ve kirpimi bulur (+-3 px, iki kart); dogru dosyalar yuksek NCC + en_yakin kendi cifti; yanlis kaynak (baska
ciftin stil karti) en_yakin ile FAIL; Y02 kare FAIL; esik yoksa OLCUM (PASS yok); esikle PASS / FAIL; METIN_KAPI yalniz Y01'de;
626 yerine kucuk liste beklenen sayisi; stil-kaynak uretimi (BAGLAR.csv + KAPAK_KAYNAK); kontak sayfasi."""
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
NCC = Q.NCC_KART


def doku(seed, wh):
    r = np.random.default_rng(seed)
    w, h = wh
    out = np.zeros((h, w, 3), np.float32)
    for s, a in ((8, 60), (32, 50), (128, 40)):
        n = r.standard_normal((h // s + 2, w // s + 2, 3)).astype(np.float32)
        out += a * cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(out + 128, 0, 255).astype(np.uint8)


def kart_yap(sahne, kaynak, metin, boyut=(2400, 2400)):
    im = sahne.copy()
    k = cv2.resize(kaynak[KIRP[1]:KIRP[3], KIRP[0]:KIRP[2]], (KUTU[2] - KUTU[0], KUTU[3] - KUTU[1]), interpolation=cv2.INTER_AREA)
    im[KUTU[1]:KUTU[3], KUTU[0]:KUTU[2]] = k
    p = Image.fromarray(im); ImageDraw.Draw(p).text((SATIR[0] + 20, SATIR[1] + 20), metin, fill=(255, 255, 255))
    return p.resize(boyut) if boyut != (2400, 2400) else p


def kid(c, k):
    return str(8000000000 + CIFTLER.index(c) * 100 + k)


class QcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); t = Path(cls.tmp.name)
        cls.kapak, cls.kaynak, cls.out = t / "kapak", t / "yedek", t / "out"
        cls.kapak.mkdir()
        cls.sahne = {k: doku(k, (2400, 2400)) for k in NCC}
        cls.src = {(c, k): doku(100 + i * 20 + k, (2400, 3000)) for i, c in enumerate(CIFTLER) for k in NCC}
        sk = []
        for i, c in enumerate(CIFTLER):
            d = cls.kaynak / f"{i}_{c}"; d.mkdir(parents=True)
            for k in NCC:
                Image.fromarray(cls.src[(c, k)]).save(d / f"r{k}_{kid(c, k)}.jpg", quality=95)
                sk.append(f"{i},{c},{k},{Q.STIL_KART[k]},{kid(c, k)},{k},{i}_{c}/r{k}_{kid(c, k)}.jpg\n")
            for k in (2, 3):
                Image.fromarray(doku(500 + i * 3 + k, (3000, 2250))).save(cls.kapak / f"{c}_Y{k:02d}.jpg", quality=90)
            for k in NCC:
                src = cls.src[(c, k)]
                if c == "LEO_VIRGO" and k == 7:
                    src = cls.src[("AQUARIUS_ARIES", 7)]                            # yanlis stil karti
                kart_yap(cls.sahne[k], src, c).save(cls.kapak / f"{c}_Y{k:02d}.jpg", quality=95)
        Image.fromarray(doku(900, (2400, 2400))).save(cls.kapak / "AQUARIUS_ARIES_Y02.jpg", quality=90)   # Y02 kare -> FAIL
        for k in (4, 5):
            Image.fromarray(doku(700 + k, (3000, 2250))).save(cls.kapak / f"ORTAK_Y{k:02d}.jpg", quality=90)
        (t / "STIL.csv").write_text("listing_id,cift,kart_no,stil,kaynak_image_id,rank,yedek_yol\n" + "".join(sk))
        (t / "ciftler.csv").write_text("listing_id,cift,a,b\n" + "".join(f"{i},{c},x,y\n" for i, c in enumerate(CIFTLER)))
        (t / "mk.tsv").write_text("cift\tdesign_id\tbaslik\tsatir_metni\tdurum\n" + "".join(
            f"{c}\tD{i}\tYD_KAPAK_V1 {c}\t{c}\t{'FAIL' if c == 'AQUARIUS_AQUARIUS' else 'PASS'}\n" for i, c in enumerate(CIFTLER)))
        (t / "SABLON.json").write_text(json.dumps(dict(kartlar={str(k): dict(kutu=KUTU, kaynak_kirp=KIRP, maske=[SATIR]) for k in NCC})))
        cls.t = t

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def kos(self, *ek):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = Q.main(["kontrol", "--kapak-dir", str(self.kapak), "--kaynak-dir", str(self.kaynak), "--stil-kaynak", str(self.t / "STIL.csv"),
                         "--ciftler", str(self.t / "ciftler.csv"), "--sablon", str(self.t / "SABLON.json"), "--out", str(self.out), *ek])
        J = json.loads((self.out / "QC_RAPOR.json").read_text())
        return rc, o.getvalue(), {s["dosya"]: s for s in J["dosyalar"]}, J

    def test_01_olc_kutu_ve_kirp(self):
        A = []
        for k, c in ((1, "AQUARIUS_AQUARIUS"), (1, "AQUARIUS_ARIES"), (8, "CANCER_LIBRA")):
            A += ["--kart", str(k), "--kapak", str(self.kapak / f"{c}_Y{k:02d}.jpg"), "--kaynak", str(self.kaynak / f"{CIFTLER.index(c)}_{c}/r{k}_{kid(c, k)}.jpg")]
        with contextlib.redirect_stdout(io.StringIO()):
            rc = Q.main(["olc", *A, "--out", str(self.t / "OLCUM.json")])
        self.assertEqual(rc, 0)
        R = json.loads((self.t / "OLCUM.json").read_text())["olcumler"]
        for r in R:
            self.assertLessEqual(max(abs(a - b) for a, b in zip(r["kutu"], KUTU)), 3, r)
            self.assertLessEqual(max(abs(a - b) for a, b in zip(r["kaynak_kirp"], KIRP)), 6, r)
            self.assertAlmostEqual(r["olcek"], 0.6, delta=0.005); self.assertGreater(r["ncc_poster"], 0.95, r)
        self.assertEqual([r["kart"] for r in R], [1, 1, 8]); self.assertEqual(R[2]["kutu_sapma"], 0)

    def test_02_olcum_esiksiz_pass_yok(self):
        rc, log, s, J = self.kos("--metin-kapi", str(self.t / "mk.tsv"))
        self.assertEqual(rc, 1, log)
        self.assertEqual(J["beklenen"], len(CIFTLER) * 8 + 2); self.assertEqual(len(s), J["beklenen"])
        a = s["AQUARIUS_ARIES_Y06.jpg"]
        self.assertEqual(a["durum"], "OLCUM"); self.assertEqual(J["sayilar"]["PASS"], 0)
        self.assertGreater(a["ncc_poster"], 0.95); self.assertGreater(a["ncc_sahne"], 0.95); self.assertEqual(a["en_yakin"], "AQUARIUS_ARIES")
        self.assertIn("kendi cifti degil", s["LEO_VIRGO_Y07.jpg"]["neden"][0])
        self.assertIn("3000x2250", s["AQUARIUS_ARIES_Y02.jpg"]["neden"][0])
        self.assertIn("METIN_KAPI", s["AQUARIUS_AQUARIUS_Y01.jpg"]["neden"][0])
        self.assertEqual(s["AQUARIUS_AQUARIUS_Y06.jpg"]["durum"], "OLCUM")                 # METIN_KAPI yalniz Y01
        self.assertIsNone(s["ORTAK_Y04.jpg"]["ncc_poster"]); self.assertEqual(s["ORTAK_Y04.jpg"]["durum"], "OLCUM")
        self.assertEqual(sorted(p.name for p in self.out.glob("KONTAK_*.jpg")), ["KONTAK_01.jpg"])
        self.assertEqual(Image.open(self.out / "KONTAK_01.jpg").size, (190 + 1500, 4 * 180))

    def test_03_esikle_pass_ve_fail(self):
        (self.t / "esik.json").write_text(json.dumps(dict(kartlar={str(k): dict(poster_min=0.9, sahne_min=0.9) for k in NCC})))
        rc, log, s, J = self.kos("--esik", str(self.t / "esik.json"))
        self.assertEqual(s["CANCER_LIBRA_Y10.jpg"]["durum"], "PASS"); self.assertEqual(s["CANCER_LIBRA_Y02.jpg"]["durum"], "PASS")
        self.assertEqual(s["ORTAK_Y05.jpg"]["durum"], "PASS")
        self.assertIn("ncc_poster", " ".join(s["LEO_VIRGO_Y07.jpg"]["neden"]))
        e2 = dict(kartlar={str(k): dict(poster_min=0.9, sahne_min=1.0001 if k == 9 else 0.9) for k in NCC})
        (self.t / "esik2.json").write_text(json.dumps(e2))
        rc, log, s, J = self.kos("--esik", str(self.t / "esik2.json"))
        self.assertEqual(s["AQUARIUS_AQUARIUS_Y09.jpg"]["durum"], "FAIL"); self.assertEqual(s["AQUARIUS_AQUARIUS_Y08.jpg"]["durum"], "PASS")
        (self.t / "esik3.json").write_text(json.dumps(dict(poster_min=0.9, sahne_min=0.9)))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(Q.main(["kontrol", "--kapak-dir", str(self.kapak), "--kaynak-dir", str(self.kaynak), "--stil-kaynak",
                                     str(self.t / "STIL.csv"), "--ciftler", str(self.t / "ciftler.csv"), "--sablon", str(self.t / "SABLON.json"),
                                     "--out", str(self.out), "--esik", str(self.t / "esik3.json")]), 2)   # kart basina esik zorunlu

    def test_04_sahne_maskesi_ve_ozet(self):
        rc, log, s, J = self.kos()
        self.assertGreater(s["AQUARIUS_ARIES_Y01.jpg"]["ncc_sahne"], 0.97)          # satir metni farkli, maske disinda ayni
        self.assertEqual(J["kart_ozet"]["1"]["n"], 3)                                 # sahne cifti (CANCER_LIBRA) ozet disi
        m = Q.sahne_maske(dict(kutu=KUTU, maske=[SATIR]), (1200, 1200), 2)
        self.assertFalse(m[SATIR[1] // 2 + 5, SATIR[0] // 2 + 5]); self.assertTrue(m[50, 50])

    def test_05_stil_kaynak_uret(self):
        (self.t / "BAGLAR.csv").write_text("listing_id,cift,stil,value_id,image_id,rank\n"
                                           "4595350971,CANCER_LIBRA,Layers,1,8725886577,13\n4595350971,CANCER_LIBRA,Botanical,2,8678064852,12\n"
                                           "4595350971,CANCER_LIBRA,First Page,3,8678064112,11\n4595350971,CANCER_LIBRA,Timeless,4,8725881453,10\n"
                                           "4595350971,CANCER_LIBRA,Starlit,5,8678059940,9\n")
        (self.t / "c1.csv").write_text("listing_id,cift,a,b\n4595350971,CANCER_LIBRA,Cancer,Libra\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = Q.main(["stil-kaynak", "--baglar", str(self.t / "BAGLAR.csv"), "--kaynak-csv", str(HERE.parents[1] / "docs/yd_kapak/KAPAK_KAYNAK.csv"),
                         "--ciftler", str(self.t / "c1.csv"), "--out", str(self.t / "SK.csv")])
        self.assertEqual(rc, 0)
        r = {int(x["kart_no"]): x for x in __import__("csv").DictReader(open(self.t / "SK.csv"))}
        self.assertEqual(sorted(r), [1, 6, 7, 8, 9, 10])
        self.assertEqual((r[1]["kaynak_image_id"], r[10]["kaynak_image_id"], r[6]["kaynak_image_id"]), ("8678064852", "8678064852", "8678059940"))
        self.assertEqual(r[9]["yedek_yol"], "4595350971_CANCER_LIBRA/r13_8725886577.jpg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
