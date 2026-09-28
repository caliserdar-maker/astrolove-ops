#!/usr/bin/env python3
"""cl_galeri_degistir yerel testi - sahte Etsy, 60 sn alti. Senaryolar:
temiz akis PASS; yedek-canli uyusmazligi DUR; active degil DUR; sira davranisi
(rank ekleme kaydirir, silme sikistirir, gorsel silinince bagi da silinir - GOREV 0024)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402

G.OKUMA_BEKLE = 0
LID = "4570143815"


class Fake:
    def __init__(self, n_eski=14):
        self.remaining = "3000"; self.calls = 0; self.nid = 9000
        self.imgs = [{"listing_image_id": 100 + n, "rank": n, "alt_text": f"eski {n}",
                      "url_fullxfull": f"fake://{100 + n}"} for n in range(1, n_eski + 1)]
        self.vimg = [{"property_id": 200, "value_id": 1000 + i, "value": r, "image_id": 100 + 10 + i}
                     for i, r in enumerate(["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"])]
        self.vids = [{"video_id": 777}]
        self.listing = {"listing_id": int(LID), "state": "active", "title": "CL", "tags": ["a"], "description": "d"}
        self.products = [{"sku": f"S{i}", "offerings": [{"price": 1, "quantity": 9, "is_enabled": True}],
                          "property_values": [{"property_id": 200, "value_ids": [1000 + i], "values": [r]}]}
                         for i, r in enumerate(["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"])]

    def _renum(self):
        for i, x in enumerate(sorted(self.imgs, key=lambda x: x["rank"]), 1):
            x["rank"] = i
        self.imgs.sort(key=lambda x: x["rank"])

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/images"):
            return {"results": [dict(x) for x in self.imgs]}
        if path.endswith("/variation-images"):
            return {"results": [dict(v) for v in self.vimg]}
        if path.endswith("/videos"):
            return {"results": list(self.vids)}
        if path.endswith("/inventory"):
            return {"products": json.loads(json.dumps(self.products))}
        return dict(self.listing)

    def delete(self, path):
        self.calls += 1
        iid = int(path.rsplit("/", 1)[1])
        assert any(x["listing_image_id"] == iid for x in self.imgs), f"silinecek {iid} yok"
        self.imgs = [x for x in self.imgs if x["listing_image_id"] != iid]
        self.vimg = [v for v in self.vimg if v["image_id"] != iid]   # GOREV 0024 davranisi
        self._renum()
        return {}

    def post_file(self, path, files, data=None):
        self.calls += 1
        assert len(self.imgs) < G.IMG_LIMIT, "20 siniri asildi"
        self.nid += 1
        r = int(data["rank"])
        for x in self.imgs:
            if x["rank"] >= r:
                x["rank"] += 1
        self.imgs.append({"listing_image_id": self.nid, "rank": r, "alt_text": data["alt_text"],
                          "url_fullxfull": f"fake://{self.nid}"})
        self._renum()
        return {"listing_image_id": self.nid}

    def post_json(self, path, body):
        self.calls += 1
        assert path.endswith("/variation-images")
        canli = {x["listing_image_id"] for x in self.imgs}
        assert all(v["image_id"] in canli for v in body["variation_images"]), "bag olmayan gorsele"
        ad = {1000 + i: r for i, r in enumerate(["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"])}
        self.vimg = [{"property_id": v["property_id"], "value_id": v["value_id"],
                      "value": ad[v["value_id"]], "image_id": v["image_id"]} for v in body["variation_images"]]
        return {"results": self.vimg}


def hazirla(td):
    kd = td / "kaynak"; kd.mkdir()
    adlar = ["kapak", "format", "konsept", "kisisellestirme", "renk_ve_dijital", "hediye", "cerceveler", "boylar",
             "yatak", "calisma", "yemek", "zoom", "kagit", "surec", "renk_mb", "renk_db", "renk_pw", "renk_ci", "renk_wp"]
    for n, ad in enumerate(adlar, 1):
        (kd / f"{n:02d}_{ad}.jpg").write_bytes(b"JPG" + bytes([n]))
    return kd


def main():
    csvyol = Path(__file__).resolve().parents[2] / "data/pod/cl_galeri_alt_metin.csv"
    kotu = []
    with tempfile.TemporaryDirectory() as t:
        td = Path(t); kd = hazirla(td); out = td / "out"; out.mkdir()
        api = Fake()
        G.indir = lambda url, hedef: Path(hedef).write_bytes(b"YEDEK")     # CDN yerine
        man = G.yedek_al(api, "39729443", LID, out)
        if len(man["galeri"]) != 14 or len(list((out / "yedek").glob("*.jpg"))) != 14:
            kotu.append("yedek")
        r = G.uygula(api, "39729443", LID, kd, csvyol, out, 400)
        alt = G.alt_metinler(csvyol)
        son = api.get(f"/listings/{LID}/images")["results"]
        vm = {v["value"]: v["image_id"] for v in api.vimg}
        rid = {x["rank"]: x["listing_image_id"] for x in son}
        if r["sonuc"] != "PASS":
            kotu.append("uygula sonuc")
        if len(son) != 19 or [x["rank"] for x in son] != list(range(1, 20)):
            kotu.append("son galeri")
        if any(x["alt_text"] != alt[x["rank"]] for x in son):
            kotu.append("alt metin")
        if not all(vm.get(rk) == rid[n] for rk, n in G.RENK_SIRA.items()):
            kotu.append("renk baglari")
        if any(x["listing_image_id"] <= 114 for x in son):
            kotu.append("eski gorsel kalmis")
        # senaryo: yedek sonrasi galeri degisti -> DUR
        api2 = Fake(); out2 = td / "out2"; out2.mkdir()
        G.yedek_al(api2, "39729443", LID, out2)
        api2.imgs.pop()
        api2._renum()
        try:
            G.uygula(api2, "39729443", LID, kd, csvyol, out2, 400); kotu.append("uyusmazlik yakalanmadi")
        except SystemExit as e:
            if "yedekten farkli" not in str(e): kotu.append(f"uyusmazlik mesaji: {e}")
        # senaryo: active degil -> DUR
        api3 = Fake(); api3.listing["state"] = "draft"; out3 = td / "out3"; out3.mkdir()
        G.yedek_al(api3, "39729443", LID, out3)
        try:
            G.uygula(api3, "39729443", LID, kd, csvyol, out3, 400); kotu.append("draft yakalanmadi")
        except SystemExit as e:
            if "active degil" not in str(e): kotu.append(f"draft mesaji: {e}")
        # senaryo: kapak-yukle sonrasi farkli eski sayilari (13 / 15) - akis canli sayiyla calismali
        for n_eski in (13, 15):
            api4 = Fake(n_eski); out4 = td / f"out_{n_eski}"; out4.mkdir()
            G.yedek_al(api4, "39729443", LID, out4)
            r4 = G.uygula(api4, "39729443", LID, kd, csvyol, out4, 400)
            son4 = api4.get(f"/listings/{LID}/images")["results"]
            if r4["sonuc"] != "PASS" or [x["rank"] for x in son4] != list(range(1, 20)) \
                    or len(r4["silinen_eski"]) != n_eski:
                kotu.append(f"{n_eski} eski senaryosu")
    print("SELFTEST:", "PASS" if not kotu else "FAIL " + "; ".join(kotu))
    if kotu:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
