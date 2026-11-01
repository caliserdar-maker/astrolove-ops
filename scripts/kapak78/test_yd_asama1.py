#!/usr/bin/env python3
"""yd_asama1 sahte Etsy testleri (ag yok). Plan: AYNI yalniz elle degisen ilk 5'te (blok olcutu), galeri sayisi / taslak / MANIFEST /
esleme sha / video ozelligi kapilari. Uygula: overwrite yer degistirir ya da ekleyip kaydirir (eski kapak silinir), Style bagi tasinir,
yukleme hata yaniti uzlastirilir (cift yukleme yok), video active olmazsa eski SILINMEZ, canli degistiyse ATLA = DUR (cikis 1),
kota payi (cikis 4), sure (cikis 5), plan damgasi / onay, plan disi silme YASAK, SONUC ile kaldigi yerden."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_asama1 as A  # noqa: E402

A.VIDEO_BEKLE = A.GORSEL_BEKLE = 0
GERCEK_ESLEME = A.ESLEME_SHA


def jpg(p, renk, boyut=(3000, 2250), rozet=False):
    a = np.full((boyut[1], boyut[0], 3), renk, np.uint8)
    a[::50] = (np.array(renk) * 0.8).astype(np.uint8)
    if rozet:
        a[100:400, 100:500] = 255 - np.array(renk, np.uint8)
    Image.fromarray(a).save(p, quality=92)


def mp4(p, sure=6, ses=False):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=1440x1080:r=30:d={sure}"]
    if ses:
        cmd += ["-f", "lavfi", "-i", f"sine=d={sure}", "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(p)], check=True)


class Sahte:
    def __init__(self, ilanlar, video_aktif=True, ekle=False, gorsel_hata=False, video_hata=False):
        self.L, self.calls, self.remaining, self.yaz = ilanlar, 0, "4000", []
        self.video_aktif, self.ekle, self.gorsel_hata, self.video_hata, self.n = video_aktif, ekle, gorsel_hata, video_hata, 100

    def kota_kapisi(self, ne=""):
        pass

    def _g(self, lid):
        return [dict(listing_image_id=int(g), rank=i + 1, url_fullxfull="u", alt_text="alt", full_width=w, full_height=h)
                for i, (g, w, h) in enumerate(self.L[lid]["g"])]

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path == "/listings/batch":
            return dict(results=[dict(listing_id=int(l), state=self.L[l]["state"], images=self._g(l),
                                      videos=[dict(video_id=int(v), video_state=s, video_url="v" if s == "active" else None)
                                              for v, s in self.L[l]["v"]]) for l in params["listing_ids"].split(",")])
        p = path.split("/")
        if path.endswith("/images"):
            return dict(results=self._g(p[2]))
        if path.endswith("/videos"):
            return dict(results=[dict(video_id=int(v), video_state=s, video_url="v" if s == "active" else None) for v, s in self.L[p[2]]["v"]])
        return dict(results=self.L[p[4]]["bag"])

    def post_file(self, path, files, data=None, tekrar=3):
        self.calls += 1; self.n += 1; lid = path.split("/")[4]
        self.yaz.append(("POST", path, dict(data or {})))
        if path.endswith("/images"):
            assert data["rank"] == "1" and data["overwrite"] == "true" and data["alt_text"]
            if self.ekle:
                self.L[lid]["g"].insert(0, (str(self.n), 3000, 2250))
            else:
                self.L[lid]["g"][0] = (str(self.n), 3000, 2250)
            if self.gorsel_hata:
                raise SystemExit("HATA: POST(file) 503")
            return dict(listing_image_id=self.n)
        self.L[lid]["v"].append((str(self.n), "active" if self.video_aktif else "processing"))
        if self.video_hata:
            raise SystemExit("HATA: POST(file) 503")
        return dict(video_id=self.n)

    def post_json(self, path, body):
        self.calls += 1; lid = path.split("/")[4]; self.yaz.append(("POST", path, body))
        self.L[lid]["bag"] = [dict(v) for v in body["variation_images"]]
        return {}

    def delete(self, path, ok404=False):
        self.calls += 1; p = path.split("/"); lid = p[4]; self.yaz.append(("DELETE", path, None))
        if p[5] == "videos":
            self.L[lid]["v"] = [x for x in self.L[lid]["v"] if x[0] != p[6]]
        else:
            self.L[lid]["g"] = [x for x in self.L[lid]["g"] if x[0] != p[6]]
        return {}


def galeri(ilk, n=13):
    return [(ilk, 3000, 2250)] + [(str(800 + i), 2400, 2400) for i in range(1, n)]


class T(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        for d in ("y01", "y01b", "yedek", "v/D", "out"):
            (self.t / d).mkdir(parents=True)
        cif = [("11", "AQUARIUS_AQUARIUS"), ("12", "AQUARIUS_ARIES"), ("13", "AQUARIUS_CANCER"), ("14", "AQUARIUS_CAPRICORN"),
               ("15", "AQUARIUS_GEMINI"), ("22", "ARIES_LEO"), ("33", "CANCER_LEO"), ("44", "LEO_LEO")]
        self.ids = self.t / "ids.csv"
        self.ids.write_text("listing_id,cift,a,b\n" + "".join(f"{l},{c},{c.split('_')[0].title()},{c.split('_')[1].title()}\n" for l, c in cif))
        renk = {c: ((37 * i) % 200 + 20, (71 * i) % 200 + 20, (13 * i) % 200 + 20) for i, (_, c) in enumerate(cif)}
        man = []
        for l, c in cif:
            d = "y01b" if c == "ARIES_LEO" else "y01"
            jpg(self.t / d / f"{c}_Y01.jpg", renk[c]); man.append((d, c))
        jpg(self.t / "y01/ARIES_LEO_Y01.jpg", (1, 1, 1))
        for d in ("y01", "y01b"):
            with open(self.t / d / "MANIFEST.csv", "w") as fh:
                fh.write("ad,cift,kart_no,sha256\n" + "".join(f"{c}_Y01.jpg,{c},1,{A.sha(self.t / d / (c + '_Y01.jpg'))}\n" for dd, c in man if dd == d))
        # canli rank 1 yedekleri: 11 elle degisen = Y01 (yeniden kodlama), 12 elle degisen ama rozetli (yanlis AYNI olmamali), digerleri eski
        jpg(self.t / "yedek/11_901.jpg", renk["AQUARIUS_AQUARIUS"], (2000, 1500))
        jpg(self.t / "yedek/12_902.jpg", renk["AQUARIUS_ARIES"], (2000, 1500), rozet=True)
        for l in ("13", "14", "15", "22", "33", "44"):
            jpg(self.t / f"yedek/{l}_9{l[-1]}{l[0]}.jpg", (90, 90, 90), (2000, 1500))
        es = []
        for l, c in cif:
            p = self.t / "v/D" / f"{c}_yd_video_43.mp4"
            mp4(p, ses=(c == "LEO_LEO"))
            (self.t / f"yedek/{l}_7{l}.mp4").write_bytes(b"x" * 20000)
            es.append(dict(cift=c, listing_id=l, damga="D", kosu="k", dosya=f"D/{c}_yd_video_43.mp4", sha256=A.sha(p), durum="OK"))
        with open(self.t / "es.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(es[0])); w.writeheader(); w.writerows(es)
        A.ESLEME_SHA = A.sha(self.t / "es.csv")
        self.eski = self.t / "eski.csv"
        self.eski.write_text("cift,durum,yeni_sha256,not\nARIES_LEO,YENILENDI," + A.sha(self.t / "y01b/ARIES_LEO_Y01.jpg") + ",x\n")
        self.canli = {l: dict(state="active", g=galeri(f"9{l[-1]}{l[0]}"), v=[(f"7{l}", "active")], bag=[]) for l, _ in cif}
        self.canli["11"]["g"] = galeri("901"); self.canli["12"]["g"] = galeri("902")
        self.canli["22"]["bag"] = [dict(property_id=513, value_id=5, image_id=922), dict(property_id=513, value_id=6, image_id=803)]
        self.canli["44"]["state"] = "draft"
        A.oku(Sahte(self.canli), A.ids_oku(self.ids), self.t)

    def tearDown(self):
        shutil.rmtree(self.t); A.ESLEME_SHA = GERCEK_ESLEME

    def plan(self):
        a = SimpleNamespace(ham=self.t / "HAM_ASAMA1.json", ids=self.ids, esleme=self.t / "es.csv", eski_kapak=str(self.eski),
                            y01=[self.t / "y01b", self.t / "y01"], video_kok=self.t / "v", yedek=self.t / "yedek", out=self.t / "out")
        rc = A.plan(a)
        with open(self.t / "out/PLAN.json") as fh:
            P = {x["listing_id"]: x for x in json.load(fh)["ilanlar"]}
        return rc, P, (self.t / "out/PLAN_DAMGA.txt").read_text().strip()

    def test_plan(self):
        rc, P, _ = self.plan()
        self.assertEqual(rc, 1)
        self.assertEqual((P["11"]["durum"], P["11"]["kapak"]["islem"]), ("PLAN", "AYNI"))
        self.assertEqual(P["12"]["kapak"]["islem"], "DEGISTIR", P["12"]["kapak"])          # rozetli elle kapak: AYNI degil
        self.assertEqual(P["22"]["kapak"]["islem"], "DEGISTIR")
        self.assertTrue(P["22"]["kapak"]["dosya"].endswith("y01b/ARIES_LEO_Y01.jpg"))
        self.assertEqual(P["22"]["kapak"]["alt"], "Aries and Leo 1st anniversary zodiac print, paper anniversary gift")
        self.assertEqual(P["44"]["durum"], "BLOK"); n44 = " ".join(P["44"]["neden"])
        self.assertIn("state draft", n44); self.assertIn("ses", n44.lower())

    def test_plan_kapilar(self):
        self.canli["33"]["g"] = galeri("933", 14)
        A.oku(Sahte(self.canli), A.ids_oku(self.ids), self.t)
        (self.t / "y01/CANCER_LEO_Y01.jpg").write_bytes((self.t / "y01/AQUARIUS_AQUARIUS_Y01.jpg").read_bytes())
        _, P, _ = self.plan()
        n = " ".join(P["33"]["neden"])
        self.assertIn("galeri 14", n); self.assertIn("MANIFEST", n)
        A.ESLEME_SHA = "0" * 64
        with self.assertRaises(SystemExit):
            self.plan()

    def ugy(self, api, damga, sadece="", confirm=A.ONAY, bitis=0.0):
        a = SimpleNamespace(plan=self.t / "out/PLAN.json", plan_damga=damga, confirm=confirm, sadece=sadece, out=self.t / "out", bitis=bitis)
        return A.uygula(a, api, "1")

    def S(self):
        with open(self.t / "out/SONUC.json") as fh:
            return json.load(fh)

    def test_uygula_yer_degistir_ve_bag(self):
        _, P, d = self.plan()
        api = Sahte(self.canli)
        with self.assertRaises(SystemExit):
            self.ugy(api, "yanlis")
        with self.assertRaises(SystemExit):
            self.ugy(api, d, confirm="X")
        self.assertEqual(self.ugy(api, d, sadece="22"), 0)
        self.assertEqual(self.S()["22"]["durum"], "PASS", self.S()["22"])
        g = self.canli["22"]["g"]
        self.assertEqual([x[0] for x in g[1:]], [str(800 + i) for i in range(1, 13)])
        self.assertIn(dict(property_id=513, value_id=5, image_id=int(g[0][0])), self.canli["22"]["bag"])
        self.assertEqual(len(self.canli["22"]["v"]), 1)
        n0 = len(api.yaz)
        self.assertEqual(self.ugy(api, d, sadece="11,22,33"), 0)            # 22 PASS atlanir; 11 AYNI: yalniz video
        y11 = [y for y in api.yaz[n0:] if "/listings/11/" in y[1]]
        self.assertEqual([y[0] for y in y11], ["POST", "DELETE"])
        self.assertFalse(any(y[1].endswith("/images") for y in y11))

    def test_ekleyip_kaydirma(self):
        _, P, d = self.plan()
        api = Sahte(self.canli, ekle=True)
        self.assertEqual(self.ugy(api, d, sadece="33"), 0, self.S())
        g = [x[0] for x in self.canli["33"]["g"]]
        self.assertEqual(len(g), 13); self.assertNotIn("933", g)
        self.assertIn(("DELETE", "/shops/1/listings/33/images/933", None), api.yaz)

    def test_hata_yanit_uzlasma(self):
        _, P, d = self.plan()
        api = Sahte(self.canli, gorsel_hata=True, video_hata=True)
        self.assertEqual(self.ugy(api, d, sadece="33"), 0, self.S())
        self.assertEqual(sum(1 for y in api.yaz if y[1].endswith("/videos")), 1)        # tekrar gonderilmedi
        self.assertEqual(len(self.canli["33"]["v"]), 1)

    def test_atla_ve_aktif_degil(self):
        _, P, d = self.plan()
        self.canli["33"]["v"] = [("99", "active")]
        self.assertEqual(self.ugy(Sahte(self.canli), d, sadece="33"), 1)
        self.assertEqual(self.S()["33"]["durum"], "ATLA")
        self.canli["33"]["v"] = [("733", "active")]
        (self.t / "out/SONUC.json").unlink()
        api = Sahte(self.canli, video_aktif=False)
        self.assertEqual(self.ugy(api, d, sadece="33"), 1)
        self.assertEqual(self.S()["33"]["durum"], "FAIL")
        self.assertIn(("733", "active"), self.canli["33"]["v"])
        self.assertFalse(any(y[0] == "DELETE" and "/videos/" in y[1] for y in api.yaz))

    def test_kota_ve_sure(self):
        _, P, d = self.plan()
        api = Sahte(self.canli); api.remaining = "40"
        self.assertEqual(self.ugy(api, d, sadece="33"), 4)
        self.assertFalse(api.yaz)
        self.assertEqual(self.ugy(Sahte(self.canli), d, sadece="33", bitis=1.0), 5)

    def test_plan_disi_silme(self):
        Y = A.Yazar(Sahte(self.canli), "1", ["11"], {"11": {"711"}}, {"11": "901"})
        for f in (lambda: Y.video_sil("11", "999"), lambda: Y.video_sil("22", "722"), lambda: Y.gorsel_sil("11", "802")):
            with self.assertRaises(SystemExit):
                f()


if __name__ == "__main__":
    unittest.main(verbosity=2)
