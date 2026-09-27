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


def test_three_variations_matrix_preserves_live_fields_and_disables_missing():
    live = inventory()
    plan = y2.build_plan(live, rows(3))
    assert len(plan["products"]) == 10
    assert plan["price_on_property"] == [100, 300]
    existing = plan["products"][0]
    assert existing["sku"] == "POD-ARI_LEO-MB-8x10"
    assert existing["offerings"][0] == {"price": 19.99, "quantity": 7, "is_enabled": True,
                                        "readiness_state_id": 4}
    assert plan["products"][1]["offerings"][0]["is_enabled"] is False
    assert len({p["sku"] for p in plan["products"]}) == 10


def test_three_variations_creates_disabled_cartesian_gaps():
    config = rows(3) + [dict(rows(3)[0], sira="3", boy="11x14", sku_ek="11x14")]
    plan = y2.build_plan(inventory(), config)
    assert len(plan["products"]) == 5 * 2 * 2
    gaps = [p for p in plan["products"] if y2.value(p, "format") == "Black Frame"
            and y2.value(p, "size") == "11x14"]
    assert len(gaps) == 5
    assert all(not p["offerings"][0]["is_enabled"] for p in gaps)


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
    assert {r["mod"] for r in y2.load_config("data/pod/yapi_v2.csv")} == {"2"}  # Serdar 27 Eyl: yapi B
