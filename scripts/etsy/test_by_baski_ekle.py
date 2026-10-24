#!/usr/bin/env python3
"""by_baski_ekle yerel testi (sahte Etsy). Aciklama ornegi: by_baski_kaldir ile uretilen 'kaldirilmis' metin."""
import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_baski_ekle as E  # noqa: E402
import by_baski_kaldir as K  # noqa: E402

ORJ = Path(__file__).resolve().parent / "testdata_by_aciklama_cl.txt"
STIL = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]


def inv10():
    pr = []
    for i, st in enumerate(STIL):
        for j, (fm, f) in enumerate([("Digital card 5x7", 3.9), ("Digital file 8x10", 4.9)]):
            pr.append({"sku": "", "property_values": [
                {"property_id": 513, "property_name": "Style", "values": [st], "value_ids": [70 + i]},
                {"property_id": 514, "property_name": "Format", "values": [fm], "value_ids": [80 + j]}],
                "offerings": [{"price": {"amount": int(round(f * 100)), "divisor": 100}, "quantity": 999, "is_enabled": True,
                               "readiness_state_id": 555}]})
    return {"products": pr, "price_on_property": [514], "quantity_on_property": [], "sku_on_property": []}


class Api:
    def __init__(self, desc, bag_kaybet=False):
        self.inv, self.remaining, self.calls = inv10(), 900, 0
        self.L = {"state": "active", "shop_id": "1", "shipping_profile_id": 9, "listing_type": "physical",
                  "title": "t", "tags": ["a"], "description": desc}
        self.v = [(513, 70 + i, 900 + i) for i in range(5)]
        self.bag_kaybet, self.puts, self.patches = bag_kaybet, [], []

    def get(self, path, params=None, ok404=False):
        self.calls += 1; self.remaining -= 1
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        if path.endswith("/variation-images"):
            return {"results": [{"property_id": p, "value_id": v, "image_id": i} for p, v, i in self.v]}
        return copy.deepcopy(self.L)

    def put_json(self, path, body):
        self.calls += 1; self.remaining -= 1; self.puts.append(body)
        yeni = []
        for p in body["products"]:
            q = copy.deepcopy(p)
            for v in q["property_values"]:
                if not v.get("value_ids"):
                    v["value_ids"] = [99]
            o = q["offerings"][0]
            o["price"] = {"amount": int(round(o["price"] * 100)), "divisor": 100}
            yeni.append(q)
        self.inv = {**self.inv, "products": yeni}
        if self.bag_kaybet:
            self.v = []

    def patch(self, path, data):
        self.calls += 1; self.remaining -= 1; self.patches.append(data)
        self.L["description"] = data["description"]

    def post_json(self, path, body):
        self.calls += 1; self.remaining -= 1
        self.v = [(x["property_id"], x["value_id"], x["image_id"]) for x in body["variation_images"]]


def test():
    orj = ORJ.read_text(encoding="utf-8")
    kaldirilmis = K.yeni_aciklama(orj)
    ok = 0
    # 1 ters islem orijinali birebir geri verir
    assert E.yeni_aciklama(kaldirilmis) == orj.replace("\r\n", "\n"), "geri ekleme orijinalle ayni degil"; ok += 1
    # 2 zaten baski metni varsa None
    assert E.yeni_aciklama(orj) is None; ok += 1
    out = Path(tempfile.mkdtemp())
    # 3 yaz PASS, 15 urun, sira: her stil kart, dosya, baski
    api = Api(kaldirilmis)
    r = E.ilan(api, "1", "111", True, out)
    assert r["durum"] == "PASS", r
    fm = [[v["values"][0] for v in p["property_values"] if v["property_id"] == 514][0] for p in api.puts[0]["products"]]
    assert fm == ["Digital card 5x7", "Digital file 8x10", E.BASKI] * 5, fm; ok += 1
    assert api.L["description"] == orj.replace("\r\n", "\n"); ok += 1
    # 4 ikinci kez: ZATEN, yazma yok
    r2 = E.ilan(api, "1", "111", True, out)
    assert r2["durum"] == "ZATEN" and len(api.puts) == 1; ok += 1
    # 5 bag kaybolursa geri yazilir
    api = Api(kaldirilmis, bag_kaybet=True)
    r = E.ilan(api, "1", "112", True, out)
    assert r["durum"] == "PASS" and r["onarim"] == "geri yazildi", r; ok += 1
    # 6 oku modu yazmaz
    api = Api(kaldirilmis)
    r = E.ilan(api, "1", "113", False, out)
    assert r["durum"] == "PLAN_OK" and not api.puts and not api.patches; ok += 1
    # 7 beklenmeyen dijital fiyat -> DUR
    api = Api(kaldirilmis); api.inv["products"][0]["offerings"][0]["price"] = {"amount": 500, "divisor": 100}
    try:
        E.ilan(api, "1", "114", True, out); raise AssertionError("DUR beklenirdi")
    except E.Dur:
        ok += 1
    # 8 aktif degil -> dokunma
    api = Api(kaldirilmis); api.L["state"] = "draft"
    r = E.ilan(api, "1", "115", True, out)
    assert r["durum"] == "ATLANDI_STATE" and not api.puts; ok += 1
    print(f"TEST {ok}/9 PASS")


if __name__ == "__main__":
    test()
