import csv
from pathlib import Path

import pytest

import ilan_yapi_v2 as y2


COLORS = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
ED = ["MB", "DB", "PW", "CI", "WP"]


def prop(pid, name, value):
    return {"property_id": pid, "property_name": name, "values": [value], "value_ids": [pid * 10]}


def inventory(with_format=True):
    products = []
    for color, edition in zip(COLORS, ED):
        for size in ["8x10", "11x14"] + [f"{n}x{n+2}" for n in range(12, 27)]:
            props = [prop(200, "Primary color", color), prop(300, "Size", size)]
            if with_format:
                props.insert(0, prop(100, "Format", "Print"))
            products.append({"sku": f"POD-ARI_LEO-{edition}-{size}", "property_values": props,
                             "offerings": [{"price": {"amount": 1200, "divisor": 100}, "quantity": 7,
                                            "is_enabled": True, "readiness_state_id": 4}]})
    return {"products": products, "price_on_property": [300], "quantity_on_property": [300],
            "sku_on_property": [300], "readiness_state_on_property": [300]}


def rows(mode):
    common = {"mod": str(mode), "sira": "1", "tur": "print", "cerceve": "", "fiyat": 19.99,
              "sku_ek": "8x10", "aktif": True}
    if mode == 2:
        return [dict(common, etiket="8x10 Print", format="Print", boy="8x10")]
    return [dict(common, etiket="", format="Print", boy="8x10"),
            dict(common, sira="2", etiket="", format="Black Frame", boy="8x10",
                 tur="framed", cerceve="BK", sku_ek="8x10-FBK", aktif=False)]


def test_v3_repo_csv_six_colors_colorless_sku():
    """Serdar 27 Eyl secenek A: 5 renk + 'All 5 colors (Digital)'; SKU renksiz; dijital yalniz dijital renkte acik."""
    live = inventory()
    plan = y2.build_plan(live, y2.load_config("data/pod/yapi_v2.csv"))
    p = plan["products"]
    assert len(p) == 80 * 6
    assert plan["sku_on_property"] == plan["price_on_property"]
    acik = [x for x in p if x["offerings"][0]["is_enabled"]]
    for x in acik:
        fmt, renk = x["property_values"][0]["values"][0], x["property_values"][1]["values"][0]
        assert (fmt == "Digital File") == (renk == y2.DIJITAL_RENK)
        assert "-MB-" not in x["sku"] and "-DB-" not in x["sku"]
    assert len(acik) == 16 + 64 * 5
    fiyat = {}
    for x in p:
        k = (x["property_values"][0]["values"][0], x["property_values"][2]["values"][0])
        assert fiyat.setdefault(k, x["offerings"][0]["price"]) == x["offerings"][0]["price"]


def test_two_variations_combines_format_and_size():
    live = inventory(with_format=False)
    plan = y2.build_plan(live, rows(2))
    assert len(plan["products"]) == 5
    assert y2.value(plan["products"][0], "size") == "8x10 Print"
    assert y2.property_value(plan["products"][0], "format") is None
    assert plan["price_on_property"] == [300]


def test_description_normalization_replacement_and_idempotence():
    old = "Intro &amp; details\r\n✦ 16 SIZES\r\nold\r\n✦ SHIPPING\r\nfast"
    result = y2.replace_description(old, "✦ SIZE & FORMAT OPTIONS\nnew", "✦ DIGITAL FILE OPTION\ndigital")
    assert "old" not in result and "✦ SHIPPING" in result
    assert y2.replace_description(result, "✦ SIZE & FORMAT OPTIONS\nnew",
                                  "✦ DIGITAL FILE OPTION\ndigital") == result
    assert y2.normalize("A &amp; B\r\n") == y2.normalize("A & B\n")


def test_csv_header_and_mode_validation(tmp_path):
    path = tmp_path / "bad.csv"; path.write_text("mod,format\n3,Print\n")
    with pytest.raises(ValueError): y2.load_config(path)
    assert {r["mod"] for r in y2.load_config("data/pod/yapi_v2.csv")} == {"3"}  # Serdar 27 Eyl: rakip yapi, 3 menu
