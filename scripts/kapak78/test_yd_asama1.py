#!/usr/bin/env python3
"""yd_asama1 sahte Etsy testleri (ag yok): plan (AYNI / DEGISTIR / BLOK), uygula (kapak + bag + video, AYNI kapakta yalniz video,
canli degistiyse ATLA, video active olmazsa eski SILINMEZ, plan damgasi / onay kapisi, plan disi silme YASAK)."""
import csv
import hashlib
import json
import shutil
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


def jpg(p, renk, gurultu=0):
    a = np.full((450, 600, 3), renk, np.uint8)
    if gurultu:
        a = np.clip(a.astype(int) + np.random.default_rng(1).integers(-gurultu, gurultu + 1, a.shape), 0, 255).astype(np.uint8)
    Image.fromarray(a).save(p, quality=92)


class Sahte:
    def __init__(self, ilanlar, video_aktif=True):
        self.L, self.calls, self.remaining, self.yaz, self.video_aktif, self.n = ilanlar, 0, "4000", [], video_aktif, 100

    def kota_kapisi(self, ne=""):
        pass

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path == "/listings/batch":
            return dict(results=[dict(listing_id=int(l), state=self.L[l]["state"], images=[dict(listing_image_id=int(g), rank=i + 1,
                        url_fullxfull="u", alt_text="alt") for i, g in enumerate(self.L[l]["g"])],
                        videos=[dict(video_id=int(v), video_state=s, video_url="v" if s == "active" else None) for v, s in self.L[l]["v"]])
                        for l in params["listing_ids"].split(",")])
        lid = path.split("/")[4]
        return dict(results=self.L[lid]["bag"])

    def post_file(self, path, files, data=None, tekrar=3):
        self.calls += 1; self.n += 1; lid = path.split("/")[4]
        self.yaz.append(("POST", path, dict(data or {})))
        if path.endswith("/images"):
            assert data["rank"] == "1" and data["overwrite"] == "true"
            self.L[lid]["g"][0] = str(self.n)
            return dict(listing_image_id=self.n)
        self.L[lid]["v"].append((str(self.n), "active" if self.video_aktif else "processing"))
        return dict(video_id=self.n)

    def post_json(self, path, body):
        self.calls += 1; lid = path.split("/")[4]; self.yaz.append(("POST", path, body))
        self.L[lid]["bag"] = [dict(v) for v in body["variation_images"]]
        return {}

    def delete(self, path, ok404=False):
        self.calls += 1; lid = path.split("/")[4]; vid = path.rsplit("/", 1)[1]; self.yaz.append(("DELETE", path, None))
        self.L[lid]["v"] = [x for x in self.L[lid]["v"] if x[0] != vid]
        return {}


class T(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        for d in ("y01", "y01b", "yedek", "v", "out"):
            (self.t / d).mkdir()
        self.ids = self.t / "ids.csv"
        self.ids.write_text("listing_id,cift,a,b\n11,AQUARIUS_AQUARIUS,A,A\n22,ARIES_LEO,A,L\n33,CANCER_LEO,C,L\n44,LEO_LEO,L,L\n")
        jpg(self.t / "y01/AQUARIUS_AQUARIUS_Y01.jpg", (200, 30, 30))
        jpg(self.t / "y01b/ARIES_LEO_Y01.jpg", (30, 200, 30))
        jpg(self.t / "y01/ARIES_LEO_Y01.jpg", (1, 1, 1))         # ana setteki ESKI kapak: yeni klasor once gelir
        jpg(self.t / "y01/CANCER_LEO_Y01.jpg", (30, 30, 200))
        jpg(self.t / "yedek/11_901.jpg", (200, 30, 30), gurultu=2)   # elle degistirilmis = Y01 (Etsy yeniden kodlamasi)
        jpg(self.t / "yedek/22_902.jpg", (90, 90, 90))
        jpg(self.t / "yedek/33_903.jpg", (90, 90, 90))
        for l, v in (("11", "71"), ("22", "72"), ("33", "73")):
            (self.t / f"yedek/{l}_{v}.mp4").write_bytes(b"eski")
        es = []
        for l, c in (("11", "AQUARIUS_AQUARIUS"), ("22", "ARIES_LEO"), ("33", "CANCER_LEO"), ("44", "LEO_LEO")):
            p = self.t / "v" / "D" / f"{c}_yd_video_43.mp4"; p.parent.mkdir(exist_ok=True); p.write_bytes(c.encode())
            es.append(dict(cift=c, listing_id=l, damga="D", kosu="k", dosya=f"D/{c}_yd_video_43.mp4", sha256=hashlib.sha256(c.encode()).hexdigest(),
                           durum="OK"))
        with open(self.t / "es.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(es[0])); w.writeheader(); w.writerows(es)
        self.eski = self.t / "eski.csv"
        self.eski.write_text("cift,durum,yeni_sha256,not\nARIES_LEO,YENILENDI," + A.sha(self.t / "y01b/ARIES_LEO_Y01.jpg") + ",x\n")
        self.ham = self.t / "ham.json"
        self.canli = {"11": dict(state="active", g=["901", "801"], v=[("71", "active")], bag=[]),
                      "22": dict(state="active", g=["902", "802", "803"], v=[("72", "active")],
                                 bag=[dict(property_id=513, value_id=5, image_id=902), dict(property_id=513, value_id=6, image_id=803)]),
                      "33": dict(state="active", g=["903"], v=[("73", "active")], bag=[]),
                      "44": dict(state="draft", g=["904"], v=[], bag=[])}
        api = Sahte(self.canli)
        A.oku(api, A.ids_oku(self.ids), self.t)
        self.ham = self.t / "HAM_ASAMA1.json"

    def tearDown(self):
        shutil.rmtree(self.t)

    def plan(self):
        a = SimpleNamespace(ham=self.ham, ids=self.ids, esleme=self.t / "es.csv", eski_kapak=str(self.eski), y01=[self.t / "y01b", self.t / "y01"],
                            video_kok=self.t / "v", yedek=self.t / "yedek", out=self.t / "out")
        rc = A.plan(a)
        P = {x["listing_id"]: x for x in json.load(open(self.t / "out/PLAN.json"))["ilanlar"]}
        return rc, P, (self.t / "out/PLAN_DAMGA.txt").read_text().strip()

    def test_plan(self):
        rc, P, _ = self.plan()
        self.assertEqual(rc, 1)                                           # 44 taslak -> BLOK
        self.assertEqual((P["11"]["durum"], P["11"]["kapak"]["islem"]), ("PLAN", "AYNI"))
        self.assertEqual((P["22"]["kapak"]["islem"], P["22"]["kapak"]["dosya"].endswith("y01b/ARIES_LEO_Y01.jpg")), ("DEGISTIR", True))
        self.assertEqual(P["33"]["video"]["islem"], "DEGISTIR")
        self.assertEqual(P["44"]["durum"], "BLOK"); self.assertIn("state draft", " ".join(P["44"]["neden"]))

    def ugy(self, api, damga, sadece="", confirm=A.ONAY):
        a = SimpleNamespace(plan=self.t / "out/PLAN.json", plan_damga=damga, confirm=confirm, sadece=sadece, out=self.t / "out")
        return A.uygula(a, api, "1")

    def test_uygula(self):
        _, P, d = self.plan()
        api = Sahte(self.canli)
        with self.assertRaises(SystemExit):
            self.ugy(api, "yanlis")
        with self.assertRaises(SystemExit):
            self.ugy(api, d, confirm="X")
        self.assertEqual(self.ugy(api, d, sadece="22"), 0)              # pilot
        S = json.load(open(self.t / "out/SONUC.json"))
        self.assertEqual(S["22"]["durum"], "PASS", S["22"])
        self.assertEqual(self.canli["22"]["g"][1:], ["802", "803"])
        self.assertIn(dict(property_id=513, value_id=5, image_id=int(self.canli["22"]["g"][0])), self.canli["22"]["bag"])
        self.assertEqual(len(self.canli["22"]["v"]), 1)
        self.assertNotIn("11", S)
        n0 = len(api.yaz)
        self.assertEqual(self.ugy(api, d), 0)                            # kalanlar; 22 PASS atlanir
        S = json.load(open(self.t / "out/SONUC.json"))
        self.assertEqual((S["11"]["durum"], S["33"]["durum"]), ("PASS", "PASS"))
        yaz11 = [y for y in api.yaz[n0:] if "/listings/11/" in y[1]]
        self.assertFalse(any(y[1].endswith("/images") for y in yaz11))    # AYNI kapak: yalniz video
        self.assertEqual([y[0] for y in yaz11], ["POST", "DELETE"])

    def test_degisti_ve_video_aktif_degil(self):
        _, P, d = self.plan()
        self.canli["33"]["v"] = [("99", "active")]                         # plan sonrasi canli degisti
        api = Sahte(self.canli, video_aktif=False)
        rc = self.ugy(api, d, sadece="33")
        self.assertEqual(json.load(open(self.t / "out/SONUC.json"))["33"]["durum"], "ATLA")
        self.canli["33"]["v"] = [("73", "active")]
        (self.t / "out/SONUC.json").unlink()
        rc = self.ugy(api, d, sadece="33")
        S = json.load(open(self.t / "out/SONUC.json"))["33"]
        self.assertEqual((rc, S["durum"]), (1, "FAIL"))
        self.assertIn(("73", "active"), self.canli["33"]["v"])           # eski video silinmedi
        self.assertFalse(any(y[0] == "DELETE" for y in api.yaz))

    def test_plan_disi_silme(self):
        Y = A.Yazar(Sahte(self.canli), "1", ["11"], {"11": {"71"}})
        with self.assertRaises(SystemExit):
            Y.video_sil("11", "999")
        with self.assertRaises(SystemExit):
            Y.video_sil("22", "72")


if __name__ == "__main__":
    unittest.main(verbosity=2)
