#!/usr/bin/env python3
"""dijital_fiyat_390 yerel testi (sahte Etsy). Kosu: python3 scripts/pod/test_dijital_fiyat_390.py"""
import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dijital_fiyat_390 as M  # noqa: E402

RENK = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
BOY = ["8x10", "A4", "11x14"]


def ornek_inv(dijital_fiyat=9.00):
    pr = []
    for b in BOY:
        for i, r in enumerate(RENK):
            pr.append({"sku": f"POD-ARI_LEO-{b}-DIGITAL", "property_values": [
                {"property_id": 513, "property_name": "Format", "values": ["Digital File"], "value_ids": [1]},
                {"property_id": 200, "property_name": "Primary color", "values": [r], "value_ids": [50 + i]},
                {"property_id": 100, "property_name": "Size", "values": [b], "value_ids": [10 + BOY.index(b)]}],
                "offerings": [{"price": {"amount": int(dijital_fiyat * 100), "divisor": 100}, "quantity": 999, "is_enabled": True}]})
            pr.append({"sku": f"POD-ARI_LEO-{b}", "property_values": [
                {"property_id": 513, "property_name": "Format", "values": ["Print"], "value_ids": [2]},
                {"property_id": 200, "property_name": "Primary color", "values": [r], "value_ids": [50 + i]},
                {"property_id": 100, "property_name": "Size", "values": [b], "value_ids": [10 + BOY.index(b)]}],
                "offerings": [{"price": {"amount": 4700 + 100 * BOY.index(b), "divisor": 100}, "quantity": 999, "is_enabled": True}]})
    return {"products": pr, "price_on_property": [513, 200, 100], "quantity_on_property": [], "sku_on_property": [513, 200, 100]}


class SahteApi:
    def __init__(self, inv, bag_kaybet=False):
        self.inv, self.remaining, self.calls, self.bag_kaybet = inv, 1000, 0, bag_kaybet
        self.vimg = [{"property_id": 200, "value_id": 50 + i, "image_id": 1000 + i} for i in range(5)]
        self.L = {"state": "active", "description": "Digital file $9 or print", "is_personalizable": True}
        self.puts = []

    def _say(self):
        self.calls += 1
        self.remaining -= 1

    def get(self, path, params=None, ok404=False):
        self._say()
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(self.vimg)}
        return copy.deepcopy(self.L)

    def put_json(self, path, body):
        self._say()
        self.puts.append(body)
        yeni = copy.deepcopy(self.inv)
        for p, b in zip(yeni["products"], body["products"]):
            assert p["sku"] == b["sku"]
            p["offerings"][0]["price"] = {"amount": int(round(b["offerings"][0]["price"] * 100)), "divisor": 100}
        self.inv = yeni
        if self.bag_kaybet:
            self.vimg = []

    def post_json(self, path, body):
        self._say()
        self.vimg = [{"property_id": x["property_id"], "value_id": x["value_id"], "image_id": x["image_id"]}
                     for x in body["variation_images"]]


def test():
    ok = 0
    tmp = tempfile.mkdtemp()
    M.OUT = Path(tmp)
    # 1 plan: 3 dijital, 15 baski, kapi temiz
    dig, diger, h, zaten = M.plan(ornek_inv())
    assert (len(dig), len(diger), h, zaten) == (15, 15, [], False), (len(dig), len(diger), h, zaten); ok += 1
    # 2 govde: yalniz dijital 3.90, baski fiyatlari ayni
    b = M.govde(ornek_inv())
    fy = {p["sku"]: p["offerings"][0]["price"] for p in b["products"]}
    assert all(v == 3.90 for k, v in fy.items() if k.endswith("-DIGITAL"))
    assert all(v >= 47 for k, v in fy.items() if not k.endswith("-DIGITAL")); ok += 1
    # 3 oku modu yazmaz
    api = SahteApi(ornek_inv())
    s = M.ilan_isle(api, "1", "111", yaz=False)
    assert s["durum"] == "PLAN_OK" and not api.puts and s["aciklamada_fiyat"] == ["$9"], s; ok += 1
    # 4 yaz PASS
    api = SahteApi(ornek_inv())
    s = M.ilan_isle(api, "1", "112", yaz=True)
    assert s["durum"] == "PASS" and len(api.puts) == 1, s; ok += 1
    # 5 renk bagi kaybolursa geri yazilir, PASS
    api = SahteApi(ornek_inv(), bag_kaybet=True)
    s = M.ilan_isle(api, "1", "113", yaz=True)
    assert s["durum"] == "PASS" and s["renk_onarim"] == "geri yazildi", s; ok += 1
    # 6 zaten hedefte: yazma yok
    api = SahteApi(ornek_inv(3.90))
    s = M.ilan_isle(api, "1", "114", yaz=True)
    assert s["durum"] == "ZATEN" and not api.puts, s; ok += 1
    # 7 beklenmeyen dijital fiyat (12.00): FAIL_KAPI, yazma yok
    api = SahteApi(ornek_inv(12.00))
    s = M.ilan_isle(api, "1", "115", yaz=True)
    assert s["durum"] == "FAIL_KAPI" and not api.puts, s; ok += 1
    # 8 tanim uyusmazligi: SKU -DIGITAL ama ozellik 'Print'
    inv = ornek_inv(); inv["products"][0]["property_values"][0]["values"] = ["Print"]
    inv["products"][0]["property_values"][1]["values"] = ["Midnight Blue"]
    _, _, h, _ = M.plan(inv)
    assert any("uyusmuyor" in x for x in h), h; ok += 1
    # 9 aktif degil: dokunma
    api = SahteApi(ornek_inv()); api.L["state"] = "draft"
    s = M.ilan_isle(api, "1", "116", yaz=True)
    assert s["durum"] == "ATLANDI_STATE" and not api.puts, s; ok += 1
    # 10 kota az: yazma yok
    api = SahteApi(ornek_inv()); api.remaining = 20
    s = M.ilan_isle(api, "1", "117", yaz=True)
    assert s["durum"].startswith("DUR_KOTA") and not api.puts, s; ok += 1
    print(f"TEST {ok}/10 PASS")


if __name__ == "__main__":
    test()
