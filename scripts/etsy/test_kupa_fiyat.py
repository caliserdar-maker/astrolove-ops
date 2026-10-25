#!/usr/bin/env python3
"""kupa_fiyat yerel testi: 8 stil x 2 boy sahte envanter (kupa_taslak.py yapisi)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kupa_fiyat as K  # noqa: E402

STIL = ["Orange Blossom", "Purple Fig", "Olive Breeze", "Pomegranate Bloom", "Almond Blossom", "Lemon Grove", "Blue Grape", "Golden Loquat"]


def inv(f11=2400, f15=2900):
    pr = []
    for i, st in enumerate(STIL):
        for j, (b, f) in enumerate((("11 oz", f11), ("15 oz", f15))):
            pr.append({"sku": f"KUPA-ARI_LEO-0{i + 1}-{b[:2]}", "is_deleted": False,
                       "property_values": [{"property_id": 513, "property_name": "Style", "values": [st], "value_ids": [100 + i]},
                                           {"property_id": 514, "property_name": "Size", "values": [b], "value_ids": [200 + j]}],
                       "offerings": [{"price": {"amount": f, "divisor": 100}, "quantity": 999, "is_enabled": True, "is_deleted": False,
                                      "readiness_state_id": 77}]})
    return {"products": pr, "price_on_property": [513, 514], "quantity_on_property": [], "sku_on_property": [513, 514],
            "readiness_state_on_property": []}


def test():
    ok = 0
    prs, h, z = K.plan(inv())
    assert not h and len(prs) == 16 and not z, h; ok += 1
    b = K.govde(inv())
    assert sorted({o["price"] for p in b["products"] for o in p["offerings"]}) == [24.9, 29.9]
    assert b["price_on_property"] == [513, 514] and all(p["property_values"][0]["value_ids"] for p in b["products"]); ok += 1
    assert K.plan(inv(2490, 2990))[2]; ok += 1
    assert K.plan(inv(2200, 2900))[1]; ok += 1
    x = inv(); x["products"].pop()
    assert K.plan(x)[1]; ok += 1
    vimg = [{"property_id": 513, "value_id": 100 + i, "image_id": 900 + i} for i in range(8)]
    assert K.bag_gecerli(inv(), vimg); ok += 1
    assert not K.bag_gecerli(inv(), vimg[:7]); ok += 1
    eski = [dict(v, value_id=v["value_id"] + 50) for v in vimg]   # 8 kayit ama value_id degismis
    assert not K.bag_gecerli(inv(), eski); ok += 1
    print(f"test_kupa_fiyat: {ok}/8 PASS")


if __name__ == "__main__":
    test()
