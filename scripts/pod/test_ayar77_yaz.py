#!/usr/bin/env python3
"""ayar77_yaz yerel oz-testi (sahte Etsy, 60 sn alti). Senaryolar:
 1 normal ilan: yedek -> yaz -> 390 urun, aciklama, renk-gorsel yeniden baglanir (PUT baglari siler), sabitler ayni
 2 taslak ilan: ATLANDI, hic yazma yok
 3 yedekten sonra degismis ilan: DUR, yazma yok
 4 PUT reddi: DUR, aciklama PATCH yapilmaz
 5 --confirm yok: DUR"""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar77_yaz as Y  # noqa: E402
import test_ayar77_kuru as T  # noqa: E402
import metin_78_uret as M  # noqa: E402

Y.BEKLE = 0
CL = "4570143815"
IDS = Path(__file__).resolve().parents[2] / "data/pod/pod78_ids.csv"


class Fake:
    def __init__(self, ilanlar, put_red=False):
        self.I = ilanlar; self.remaining = "5000"; self.yaz = []; self.put_red = put_red; self.vid = 5000

    def _lid(self, path):
        return next(p.split("?")[0] for p in path.split("/") if p.split("?")[0].isdigit() and len(p.split("?")[0]) == 10)

    def get(self, path, params=None, ok404=False):
        I = self.I[self._lid(path)]
        if path.endswith("/inventory"):
            return copy.deepcopy(I["inv"])
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(I["vimg"])}
        if path.endswith("/images"):
            return {"results": copy.deepcopy(I["imgs"])}
        if path.endswith("/videos"):
            return {"results": [{"video_id": 1}]}
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(I["q"])}
        if path.endswith("/properties"):
            return {"results": copy.deepcopy(I["props"])}
        return copy.deepcopy(I["L"])

    def put_json(self, path, body):
        self.yaz.append(("PUT", path))
        if self.put_red:
            raise SystemExit("HATA: PUT -> 400: sahte red")
        I = self.I[self._lid(path)]
        assert "max_variations_supported=3" in path and len(body["products"]) == 390
        yeni = copy.deepcopy(body)
        for p in yeni["products"]:
            for v in p["property_values"]:
                if v["property_id"] == 200:
                    v["value_ids"] = [7000 + ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"].index(v["values"][0])]
            for o in p["offerings"]:
                o["price"] = {"amount": int(round(o["price"] * 100)), "divisor": 100}
        I["inv"] = yeni
        I["vimg"] = []                      # Etsy: deger id'leri degisince baglar duser
        return yeni

    def post_json(self, path, body):
        self.yaz.append(("POST", path))
        self.I[self._lid(path)]["vimg"] = [dict(value_id=v["value_id"], image_id=v["image_id"]) for v in body["variation_images"]]
        return {}

    def patch(self, path, data):
        self.yaz.append(("PATCH", path))
        assert set(data) == {"description"}
        self.I[self._lid(path)]["L"]["description"] = data["description"]
        return {}


def ilan(lid, a, b, cift, state="active"):
    x = T.ilan(lid, a, b, cift, T.eski_inv(f"POD-{a[:3].upper()}_{b[:3].upper()}-") if lid != CL else T.cl_inv(),
               M.uret(cift) if lid == CL else "eski metin", state=state)
    renkler = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
    if lid != CL:
        ps = []
        for i, r in enumerate(renkler):
            p = copy.deepcopy(x["inv"]["products"][0])
            p["sku"] = p["sku"].replace("MB", r[:1] + r.split()[1][:1])
            p["property_values"][0] = {"property_id": 200, "property_name": "Primary color", "values": [r], "value_ids": [100 + i]}
            ps.append(p)
        x["inv"] = {"products": ps, "price_on_property": [513], "sku_on_property": [200, 513]}
        x["vimg"] = [{"value_id": 100 + i, "image_id": 9000 + i} for i in range(5)]
    else:
        x["vimg"] = []
    x["imgs"] = [{"listing_image_id": 9000 + i, "rank": i + 1} for i in range(10)]
    return x


def main():
    kotu = []
    ids = {r.split(",")[0]: r.split(",") for r in IDS.read_text().splitlines()[1:]}
    ornek = "4570110641"                         # AQUARIUS_ARIES
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)

        def kur(state="active", put_red=False):
            il = {CL: ilan(CL, "Cancer", "Libra", "CANCER_LIBRA"),
                  ornek: ilan(ornek, "Aquarius", "Aries", "AQUARIUS_ARIES", state)}
            return Fake(il, put_red)
        # 1 normal
        api = kur(); out = td / "o1"
        Y.calis(api, "39729443", "yedek", out, IDS, ornek)
        s = Y.calis(api, "39729443", "yaz", out, IDS, ornek, "AYAR77")
        L = api.I[ornek]
        if s[0]["durum"] != "YAZILDI" or len(L["inv"]["products"]) != 390 or L["L"]["description"] != M.uret("AQUARIUS_ARIES").strip():
            kotu.append(f"normal: {s}")
        if Y.renk_gorsel(L["inv"], L["vimg"]) != {r: 9000 + i for i, r in enumerate(["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"])}:
            kotu.append("renk-gorsel geri gelmedi")
        if [w[0] for w in api.yaz] != ["PUT", "POST", "PATCH"]:
            kotu.append(f"yazma sirasi {api.yaz}")
        # 2 taslak
        api = kur(state="draft"); out = td / "o2"
        Y.calis(api, "39729443", "yedek", out, IDS, ornek)
        s = Y.calis(api, "39729443", "yaz", out, IDS, ornek, "AYAR77")
        if s[0]["durum"] != "ATLANDI" or api.yaz:
            kotu.append(f"taslak: {s} {api.yaz}")
        # 3 yedekten sonra degismis
        api = kur(); out = td / "o3"
        Y.calis(api, "39729443", "yedek", out, IDS, ornek)
        api.I[ornek]["L"]["description"] = "baska biri degistirdi"
        try:
            Y.calis(api, "39729443", "yaz", out, IDS, ornek, "AYAR77"); kotu.append("degisim yakalanmadi")
        except SystemExit as e:
            if "yedekten sonra" not in str(e) or api.yaz: kotu.append(f"degisim: {e} {api.yaz}")
        # 4 PUT reddi
        api = kur(put_red=True); out = td / "o4"
        Y.calis(api, "39729443", "yedek", out, IDS, ornek)
        try:
            Y.calis(api, "39729443", "yaz", out, IDS, ornek, "AYAR77"); kotu.append("PUT reddi yakalanmadi")
        except SystemExit as e:
            if "PUT reddedildi" not in str(e) or [w[0] for w in api.yaz] != ["PUT"]: kotu.append(f"PUT reddi: {e} {api.yaz}")
        # 5 confirm yok
        try:
            Y.calis(kur(), "39729443", "yaz", td / "o1", IDS, ornek, ""); kotu.append("confirm yok yakalanmadi")
        except SystemExit:
            pass
    print("SELFTEST:", "PASS" if not kotu else "FAIL " + "; ".join(kotu))
    raise SystemExit(0 if not kotu else 2)


if __name__ == "__main__":
    main()
