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
    """Serdar 27 Eyl secenek A: 5 renk + 'All 5 colors, Digital'; SKU renksiz; dijital yalniz dijital renkte acik."""
    live = inventory()
    plan = y2.build_plan(live, y2.load_config("data/pod/yapi_v2.csv"))
    p = plan["products"]
    cfg = y2.load_config("data/pod/yapi_v2.csv")
    n_dij = sum(1 for r in cfg if r["tur"] == "digital"); n_fiz = len(cfg) - n_dij
    assert len(p) == len(cfg) * 6
    assert plan["sku_on_property"] == plan["price_on_property"]
    assert plan["price_on_property"] == [100, 200, 300]  # Etsy: 3 varyasyonda 0, 1 ya da 3 id
    acik = [x for x in p if x["offerings"][0]["is_enabled"]]
    for x in acik:
        fmt, renk = x["property_values"][0]["values"][0], x["property_values"][1]["values"][0]
        assert (fmt == "Digital File") == (renk == y2.DIJITAL_RENK)
        assert "-MB-" not in x["sku"] and "-DB-" not in x["sku"]
    assert len(acik) == n_dij + n_fiz * 5
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


def test_plan_referans_ile_birebir():
    """REFERANS_ILAN_CL fiyat tablosu + SKU v3: repo CSV'sinden kurulan plan hatasiz."""
    tablo = y2.referans_tablosu()
    assert len(tablo) == 16 and tablo["8x10"] == (47.99, 95.99) and tablo["24x36"] == (109.99, 164.99)
    plan = y2.build_plan(inventory(), y2.load_config("data/pod/yapi_v2.csv"))
    assert y2.referans_kontrol(plan, tablo) == []
    plan["products"][0]["offerings"][0]["price"] = 1.0
    assert y2.referans_kontrol(plan, tablo)


def test_ozet_menu_ve_ornek():
    live = inventory()
    plan = y2.build_plan(live, y2.load_config("data/pod/yapi_v2.csv"))
    oz = y2.ozet(live, plan, "active")
    assert oz["urun"] == [len(live["products"]), 576] and oz["acik"][1] == 16 + 80 * 5
    assert oz["menu"][1] == ["Digital File", "Print", "Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"]
    assert oz["menu"][2][-1] == y2.DIJITAL_RENK and len(oz["menu"][2]) == 6
    assert oz["ornek"]["8x10 | Digital File"] == "9.99 POD-ARI_LEO-8x10-DIGITAL"


class FakeApi:
    remaining = 5000

    def __init__(self):
        self.listing = {"state": "active", "title": "T", "tags": ["a"], "description": "eski aciklama",
                        "is_personalizable": True}
        self.inv = inventory(); self.calls = []

    def get(self, path, ok404=False):
        if path.endswith("/inventory"): return self.inv
        if path.endswith("/variation-images"): return {"results": []}
        if path.endswith("/images"): return {"results": [{"listing_image_id": 1, "rank": 1}]}
        if path.endswith("/videos"): return {"results": [{"video_id": 9}]}
        return dict(self.listing)

    def put_json(self, path, body):
        self.calls.append(("put", path)); self.inv = body

    def post_json(self, path, body):
        self.calls.append(("post", path))

    def patch(self, path, body):
        self.calls.append(("patch", path)); self.listing.update(body)


def test_yaz_aciklama_varsayilan_kapali(tmp_path, monkeypatch):
    monkeypatch.setenv("ETSY_SHOP_ID", "1"); monkeypatch.chdir(Path(__file__).resolve().parents[2])
    monkeypatch.setattr(y2, "OUT", tmp_path)
    api = FakeApi()
    assert y2.main(["yaz", "4570143815", "--confirm", "YAPI_V2", "--yapi", "v3"], api=api) == 0
    assert ("put", "/listings/4570143815/inventory?max_variations_supported=3") in api.calls
    assert not [c for c in api.calls if c[0] == "patch"]
    assert api.listing["description"] == "eski aciklama"
    assert y2.parser().parse_args(["kuru", "1"]).aciklama is False


def test_dijital_renk_parantezsiz_ve_oneri():
    assert "(" not in y2.DIJITAL_RENK
    plan = y2.build_plan(inventory(), y2.load_config("data/pod/yapi_v2.csv"))
    assert y2.varyasyon_sayisi(plan) == 3
    oneri = y2.parantezsiz_oneri(plan)
    assert oneri.get("8×10″ (20×25cm)") == "8×10″ / 20×25cm"
    assert all("(" not in v for v in oneri.values())


def inventory_d():
    """Canli CL gibi: Primary color (200, her renge ayri value_id) x Size (513)."""
    products = []
    for i, color in enumerate(COLORS):
        for size in ["8x10", "11x14"]:
            products.append({"sku": f"POD-CAN_LIB-{ED[i]}-{size}",
                             "property_values": [{"property_id": 200, "property_name": "Primary color",
                                                  "values": [color], "value_ids": [9000 + i]},
                                                 {"property_id": 513, "property_name": "Size", "values": [size],
                                                  "value_ids": [7000]}],
                             "offerings": [{"price": {"amount": 4799, "divisor": 100}, "quantity": 7,
                                            "is_enabled": True, "readiness_state_id": 4}]})
    return {"products": products, "price_on_property": [513], "quantity_on_property": [],
            "sku_on_property": [513], "readiness_state_on_property": []}


BEKLENEN_MENU1 = ["Digital File, All 5 Colors"] + [f"{f}, {c}" for f in
                  ["Print", "Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"]
                  for c in ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]]


def test_menu_d_416_urun_sira_ve_referans():
    plan = y2.build_plan_d(inventory_d(), y2.load_config("data/pod/yapi_v2.csv"))
    p = plan["products"]
    assert len(p) == 416 and all(x["offerings"][0]["is_enabled"] for x in p)
    assert plan["price_on_property"] == plan["sku_on_property"] == [514, 513]
    assert y2.varyasyon_sayisi(plan) == 2
    oz = y2.ozet(inventory_d(), plan, "active")
    assert oz["menu"][1] == BEKLENEN_MENU1 and len(oz["menu"][2]) == 16
    assert all("(" not in v for v in BEKLENEN_MENU1)
    assert y2.referans_kontrol(plan, y2.referans_tablosu()) == []
    assert oz["ornek"]["8x10 | Digital File"] == "9.99 POD-CAN_LIB-8x10-DIGITAL"
    assert oz["ornek"]["8x10 | Antique Gold Frame"] == "95.99 POD-CAN_LIB-8x10-FGO"


class FakeApiD(FakeApi):
    def __init__(self):
        super().__init__(); self.inv = inventory_d(); self.vimg = [
            {"property_id": 200, "value_id": 9000 + i, "value": c, "image_id": 100 + i} for i, c in enumerate(COLORS)]
        self.posted = None

    def get(self, path, ok404=False):
        if path.endswith("/variation-images"): return {"results": self.vimg}
        return super().get(path, ok404)

    def put_json(self, path, body):
        self.calls.append(("put", path))
        vid = {}
        for pr in body["products"]:
            for pv in pr["property_values"]:
                if pv["property_id"] == 514:
                    pv["value_ids"] = [vid.setdefault(pv["values"][0], 50000 + len(vid))]
        self.inv = body

    def post_json(self, path, body):
        self.calls.append(("post", path)); self.posted = body["variation_images"]
        self.vimg = [dict(x, value="") for x in self.posted]


def test_yaz_menu_d_renk_gorselleri(tmp_path, monkeypatch):
    monkeypatch.setenv("ETSY_SHOP_ID", "1"); monkeypatch.chdir(Path(__file__).resolve().parents[2])
    monkeypatch.setattr(y2, "OUT", tmp_path)
    api = FakeApiD()
    assert y2.main(["yaz", "4570143815", "--confirm", "YAPI_V2"], api=api) == 0
    assert ("put", "/listings/4570143815/inventory") in api.calls          # 2 menu: parametre yok
    assert not [c for c in api.calls if c[0] == "patch"]                    # aciklama yazilmaz
    assert len(api.posted) == 25
    renk_gorsel = {c: 100 + i for i, c in enumerate(COLORS)}
    ad = {pv["value_ids"][0]: pv["values"][0] for pr in api.inv["products"] for pv in pr["property_values"]
          if pv["property_id"] == 514}
    for x in api.posted:
        assert x["image_id"] == renk_gorsel[ad[x["value_id"]].rpartition(", ")[2]]
