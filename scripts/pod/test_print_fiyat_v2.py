#!/usr/bin/env python3
"""print_fiyat_v2 yerel testi: canli envanter (4570143815, 25 Eki salt okuma 40176728255) ile plan + govde + sahte PUT."""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import print_fiyat_v2 as P  # noqa: E402

FIX = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "testdata_env_4570143815.json"


def test():
    d = json.load(open(FIX))
    inv = d["envanter"]
    ok = 0
    prs, h, zaten = P.plan(inv)
    assert not h and len(prs) == 65 and not zaten, (h, len(prs)); ok += 1
    b = P.govde(inv)
    assert len(b["products"]) == 130 and b["sku_on_property"] == inv["sku_on_property"]; ok += 1
    once = {P.anahtar(p): p for p in inv["products"]}
    for q in b["products"]:
        p = once[P.anahtar(q)]
        a, bb = P.print_mi(p)
        f = q["offerings"][0]["price"]
        if a and bb:
            assert f == P.HEDEF[P.boy_kodu(P.deger(p, P.P_BOY))][0]
        else:
            assert f == 3.90
        assert q["sku"] == (p.get("sku") or "")
        assert [pv["value_ids"] for pv in q["property_values"]] == [pv["value_ids"] for pv in p["property_values"]]
    ok += 1
    # yazilmis hal -> ZATEN
    inv2 = copy.deepcopy(inv)
    for p in inv2["products"]:
        yf = P.yeni_fiyat(p)
        if yf is not None:
            p["offerings"][0]["price"] = {"amount": int(round(yf * 100)), "divisor": 100}
    assert P.plan(inv2)[2] and not P.plan(inv2)[1]; ok += 1
    # beklenmedik eski fiyat -> kapi
    inv3 = copy.deepcopy(inv)
    for p in inv3["products"]:
        if P.yeni_fiyat(p) is not None:
            p["offerings"][0]["price"] = {"amount": 9999, "divisor": 100}
            break
    assert P.plan(inv3)[1]; ok += 1
    # dijital fiyat bozuksa kapi
    inv4 = copy.deepcopy(inv)
    for p in inv4["products"]:
        if P.yeni_fiyat(p) is None:
            p["offerings"][0]["price"] = {"amount": 900, "divisor": 100}
            break
    assert P.plan(inv4)[1]; ok += 1
    print("boylar", sorted({P.boy_kodu(P.deger(p, P.P_BOY)) for p in prs}))
    print(f"test_print_fiyat_v2: {ok}/6 PASS")


if __name__ == "__main__":
    test()
