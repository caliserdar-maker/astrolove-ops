#!/usr/bin/env python3
"""fiyat_zam_1114 yerel testi (sahte Etsy; gercek aga cikmaz). Kosu: python3 scripts/pod/test_fiyat_zam_1114.py

Gercek poster envanteri: scripts/etsy/testdata_pod_5x7_kuru_4570143815.json (130 urun, 13 boy x 5 renk x 2 format,
dijital 3.90, baski 25 Eki tablosu). 5x7 urunleri bu veriye ayni kalipla eklenir (30 Eki yazimi sonrasi canli 140 urun).
"""
import copy
import json
import os
import socket
import sys
import tempfile
import types
import urllib.request
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok          # TEST AGI (CLAUDE.md:124): baglanti duzeyinde kapali
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import fiyat_zam_1114 as M  # noqa: E402

GERCEK = json.loads((KOK.parent / "etsy" / "testdata_pod_5x7_kuru_4570143815.json").read_text(encoding="utf-8"))


def poster_inv(dijital=3.90, baski_ek=0.0, besyedi=True):
    inv = copy.deepcopy(GERCEK["inventory"])
    if besyedi:                                      # 5x7: 8x10 urunlerinin kopyasi, boy etiketi ve fiyati degisir
        ek = []
        for p in inv["products"]:
            if any(v == "8×10″ (20×25cm)" for pv in p["property_values"] for v in pv["values"]):
                q = copy.deepcopy(p)
                q["sku"] = q["sku"].replace("-8x10", "-5x7")
                for pv in q["property_values"]:
                    if pv["property_name"] == "Size":
                        pv["values"], pv["value_ids"] = ["5×7″ (13×18cm)"], [999]
                if not q["sku"].endswith("-DIGITAL"):
                    q["offerings"][0]["price"] = {"amount": 1990, "divisor": 100, "currency_code": "USD"}
                ek.append(q)
        inv["products"] = ek + inv["products"]
    for p in inv["products"]:
        f = M.deger(p, "format")
        if f == "Digital File":
            p["offerings"][0]["price"] = {"amount": int(round(dijital * 100)), "divisor": 100, "currency_code": "USD"}
        elif baski_ek:
            eski = M.para(p["offerings"][0]["price"])
            p["offerings"][0]["price"] = {"amount": int(round((eski + baski_ek) * 100)), "divisor": 100, "currency_code": "USD"}
    return inv


def yd_yeni(dijital=3.90):
    """1st Anniversary hedef yapisi (yd_yapi_kuru.py:5-9, :58-65): Style x Format x Size, SKU BY-...-<boy>[-DIGITAL].
    Canli yapi OLCULMEDI: yaz oncesi 'oku --aile yd' kosusu esastir."""
    pr = []
    for i, st in enumerate(["Starlit", "Timeless"]):
        for j, (b, bk) in enumerate([("5×7″ (13×18cm)", "5x7"), ("8×10″ (20×25cm)", "8x10"), ("24×36″ (61×91cm)", "24x36")]):
            for k, fm in enumerate(["Digital File", "Print"]):
                fy = dijital if fm == "Digital File" else M.BASKI_ESKI[bk]
                pr.append({"sku": f"BY-CAN_LIB-{st[:3].upper()}-{bk}" + ("-DIGITAL" if fm == "Digital File" else ""), "property_values": [
                    {"property_id": 513, "property_name": "Style", "values": [st], "value_ids": [70 + i]},
                    {"property_id": 514, "property_name": "Format", "values": [fm], "value_ids": [80 + k]},
                    {"property_id": 516, "property_name": "Size", "values": [b], "value_ids": [90 + j]}],
                    "offerings": [{"price": {"amount": int(round(fy * 100)), "divisor": 100}, "quantity": 999, "is_enabled": True}]})
    return {"products": pr, "price_on_property": [514, 516], "sku_on_property": [513, 514, 516],
            "readiness_state_on_property": [514]}                       # yd_yapi_kuru.py:64-65


def yd_eski():
    """1st Anniversary eski yapisi (by_baski_ekle.py:39-40; yd_yapi_kuru.py:59-60, :69): BY-...-CARD5X7 / FILE8X10 / PRINT8X10."""
    ek = {"Digital card 5x7": "CARD5X7", "Digital file 8x10": "FILE8X10", "Shipped print 8x10": "PRINT8X10"}
    return {"products": [{"sku": f"BY-CAN_LIB-{ek[fm]}", "property_values": [
        {"property_id": 513, "property_name": "Style", "values": [st], "value_ids": [70 + i]},
        {"property_id": 514, "property_name": "Format", "values": [fm], "value_ids": [80 + j]}],
        "offerings": [{"price": {"amount": int(pr * 100), "divisor": 100}, "quantity": 999, "is_enabled": True}]}
        for i, st in enumerate(["Starlit", "Timeless"])
        for j, (fm, pr) in enumerate([("Digital card 5x7", 3.9), ("Digital file 8x10", 3.9), ("Shipped print 8x10", 24.9)])],
        "price_on_property": [514]}


class SahteApi:
    def __init__(self, inv, bag_kaybet=False, kalan=1000):
        self.inv, self.remaining, self.calls, self.bag_kaybet = inv, kalan, 0, bag_kaybet
        self.vimg = copy.deepcopy(GERCEK["variation_images"])
        self.L = {"state": "active", "description": "Digital File $3.90 or a print", "is_personalizable": True}
        self.puts = []

    def _say(self):
        if self.remaining is not None and self.remaining < 10:      # etsy_common.py:734-735 sert taban
            raise SystemExit(f"kota kalan {self.remaining} < 10")
        self.calls += 1
        self.remaining -= 1

    def get(self, path, params=None, ok404=False):
        self._say()
        if "/inventory" in path:
            assert path.endswith("?max_variations_supported=3"), path
            return copy.deepcopy(self.inv)
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(self.vimg)}
        if "/shop-sections/listings" in path:
            return {"results": [{"listing_id": x} for x in M.ids_oku("yd")]}
        return copy.deepcopy(self.L)

    def put_json(self, path, body):
        assert path.endswith("/inventory?max_variations_supported=3"), path
        self._say()
        self.puts.append(body)
        yeni = copy.deepcopy(self.inv)
        canli = [p for p in yeni["products"] if not p.get("is_deleted")]
        assert len(canli) == len(body["products"])
        for p, b in zip(canli, body["products"]):
            assert p["sku"] == b["sku"]
            p["offerings"][0]["price"] = {"amount": int(round(b["offerings"][0]["price"] * 100)), "divisor": 100}
        self.inv = yeni
        if self.bag_kaybet:
            self.vimg = []

    def post_json(self, path, body):
        self._say()
        self.vimg = [{"property_id": x["property_id"], "value_id": x["value_id"], "image_id": x["image_id"]}
                     for x in body["variation_images"]]

    def kota_kapisi(self, ne):
        pass


def fiyat_tablosu(inv):
    return {(M.deger(p, "format"), M.boy_kodu(M.deger(p, "size")), M.deger(p, "primary color") or M.deger(p, "style")):
            M.fiyatlar(p)[0] for p in inv["products"] if not p.get("is_deleted")}


def test():
    ok = 0
    M.OUT = Path(tempfile.mkdtemp())
    inv = poster_inv()
    # 1 gercek poster envanteri (+5x7): 140 urun, kapi temiz
    u, h, z = M.plan(inv)
    assert (len(u), h, z) == (140, [], False), (len(u), h[:3], z); ok += 1
    # 2 govde: dijital 9.90, her baski +5, fiyat disi alanlar ve sira birebir
    b = M.govde(inv)
    once, sonra = inv["products"], b["products"]
    for p, q in zip(once, sonra):
        f = M.deger(p, "format")
        hedef = 9.90 if f == "Digital File" else round(M.fiyatlar(p)[0] + 5, 2)
        assert q["offerings"][0]["price"] == hedef, (p["sku"], q["offerings"][0]["price"], hedef)
        assert q["sku"] == p["sku"] and [x["values"] for x in q["property_values"]] == [x["values"] for x in p["property_values"]]
        assert q["offerings"][0]["quantity"] == p["offerings"][0]["quantity"]
    assert {q["offerings"][0]["price"] for p, q in zip(once, sonra) if M.boy_kodu(M.deger(p, "size")) == "5x7"
            and M.deger(p, "format") == "Print"} == {24.90}
    assert {q["offerings"][0]["price"] for p, q in zip(once, sonra) if M.boy_kodu(M.deger(p, "size")) == "24x36"
            and M.deger(p, "format") == "Print"} == {69.90}; ok += 1
    # 3 oku modu yazmaz; aciklamadaki fiyat raporlanir
    api = SahteApi(poster_inv())
    s = M.ilan_isle(api, "1", "111", yaz=False)
    assert s["durum"] == "PLAN_OK" and not api.puts and s["aciklamada_fiyat"] == ["$3.90"], s; ok += 1
    # 4 yaz PASS, tek PUT, sonra her fiyat hedefte
    api = SahteApi(poster_inv())
    s = M.ilan_isle(api, "1", "112", yaz=True)
    assert s["durum"] == "PASS" and len(api.puts) == 1, s
    assert fiyat_tablosu(api.inv) == fiyat_tablosu(poster_inv(9.90, 5.0)); ok += 1
    # 5 renk bagi kaybolursa geri yazilir, PASS
    api = SahteApi(poster_inv(), bag_kaybet=True)
    s = M.ilan_isle(api, "1", "113", yaz=True)
    assert s["durum"] == "PASS" and s["renk_onarim"] == "geri yazildi", s; ok += 1
    # 6 zaten hedefte: tek istek, yazma yok
    api = SahteApi(poster_inv(9.90, 5.0))
    s = M.ilan_isle(api, "1", "114", yaz=True)
    assert s["durum"] == "ZATEN" and not api.puts and api.calls == 1, (s, api.calls); ok += 1
    # 7 karisik (dijital yeni, baski eski): izinli, PASS
    api = SahteApi(poster_inv(9.90, 0.0))
    s = M.ilan_isle(api, "1", "115", yaz=True)
    assert s["durum"] == "PASS" and fiyat_tablosu(api.inv) == fiyat_tablosu(poster_inv(9.90, 5.0)), s; ok += 1
    # 8 baski beklenmeyen fiyat (Eylul 47.00): FAIL_KAPI
    inv = poster_inv(); [p["offerings"][0].update(price={"amount": 4700, "divisor": 100}) for p in inv["products"]
                         if M.deger(p, "format") == "Print" and M.boy_kodu(M.deger(p, "size")) == "8x10"]
    api = SahteApi(inv)
    s = M.ilan_isle(api, "1", "116", yaz=True)
    assert s["durum"] == "FAIL_KAPI" and not api.puts, s; ok += 1
    # 9 dijital eski 9.00: FAIL_KAPI
    api = SahteApi(poster_inv(9.00))
    s = M.ilan_isle(api, "1", "117", yaz=True)
    assert s["durum"] == "FAIL_KAPI" and not api.puts, s; ok += 1
    # 10 1st Anniversary eski yapi (SKU bos, Digital card 5x7 ...): FAIL_KAPI, yazma yok
    api = SahteApi(yd_eski()); api.vimg = []
    s = M.ilan_isle(api, "1", "118", yaz=True)
    assert s["durum"] == "FAIL_KAPI" and not api.puts, s; ok += 1
    # 11 1st Anniversary yeni yapi: PASS, dijital 9.90, baski +5
    api = SahteApi(yd_yeni()); api.vimg = []
    s = M.ilan_isle(api, "1", "119", yaz=True)
    assert s["durum"] == "PASS", s
    assert {(f, k): v for (f, k, _), v in fiyat_tablosu(api.inv).items()} == {
        ("Digital File", "5x7"): 9.9, ("Digital File", "8x10"): 9.9, ("Digital File", "24x36"): 9.9,
        ("Print", "5x7"): 24.9, ("Print", "8x10"): 29.9, ("Print", "24x36"): 69.9}; ok += 1
    # 12 aktif degil: dokunma
    api = SahteApi(poster_inv()); api.L["state"] = "draft"
    s = M.ilan_isle(api, "1", "120", yaz=True)
    assert s["durum"] == "ATLANDI_STATE" and not api.puts, s; ok += 1
    # 13 PUT oncesi kota: kalan 19 (4 okumadan sonra 15 < 16): DUR_KOTA, yazma yok
    api = SahteApi(poster_inv(), kalan=19)
    s = M.ilan_isle(api, "1", "121", yaz=True)
    assert s["durum"].startswith("DUR_KOTA") and not api.puts, s; ok += 1
    # 14 SKU / format uyusmazligi: FAIL_KAPI
    inv = poster_inv(); inv["products"][0]["sku"] = inv["products"][0]["sku"].replace("-DIGITAL", "")
    _, h, _ = M.plan(inv)
    assert any("uyusmuyor" in x for x in h), h; ok += 1
    # 15 bilinmeyen boy: FAIL_KAPI
    inv = poster_inv()
    for pv in inv["products"][1]["property_values"]:
        if pv["property_name"] == "Size":
            pv["values"] = ["30×40″ (76×102cm)"]
    _, h, _ = M.plan(inv)
    assert any("bilinmeyen" in x for x in h), h; ok += 1
    # 16 main: onay sozcugu, --hepsi/--ilanlar, ATLA yalniz yaz modunda, yd bolum kontrolu
    ok += test_main()
    print(f"TOPLAM {ok}/16 PASS")


def test_main():
    kayit = {}

    class FakeEtsy(SahteApi):
        def __init__(self, store):
            super().__init__(kayit["inv"])
            self.remaining = None
            kayit["api"] = self

        def get(self, path, params=None, ok404=False):
            if self.remaining is None:
                self.remaining = 4000
            return super().get(path, params, ok404)

    class FakeStore:
        def __init__(self, *a):
            pass

        def needs_refresh(self):
            return False

    sys.modules["etsy_common"] = types.SimpleNamespace(Etsy=FakeEtsy, TokenStore=FakeStore, mask=lambda x: None)
    os.environ.update({"TOKEN_FILE": "x", "ETSY_SHOP_ID": "1", "ETSY_API_KEY": "k", "ETSY_SHARED_SECRET": "s"})
    ids = M.ids_oku("poster")

    def kos(*arg, atla=""):
        os.environ["ATLA"] = atla
        sys.argv = ["fiyat_zam_1114.py", *arg]
        M.OUT = Path(tempfile.mkdtemp())
        try:
            M.main()
        except SystemExit as e:
            return e.code, M.OUT
        return 0, M.OUT

    kayit["inv"] = poster_inv()
    # yaz onaysiz: DUR
    rc, _ = kos("yaz", "--aile", "poster", "--ilanlar", ids[0])
    assert isinstance(rc, str) and "FIYAT_1114" in rc, rc
    # yaz --hepsi tek-ilan onayiyla: DUR
    rc, _ = kos("yaz", "--aile", "poster", "--hepsi", "--confirm", "FIYAT_1114")
    assert isinstance(rc, str) and "FIYAT_1114_HEPSI" in rc, rc
    # --hepsi ve --ilanlar birlikte: DUR
    rc, _ = kos("oku", "--aile", "poster", "--hepsi", "--ilanlar", ids[0])
    assert isinstance(rc, str) and "yalniz biri" in rc, rc
    # oku --hepsi: ATLA uygulanmaz, 78 ilan okunur, PUT yok
    rc, out = kos("oku", "--aile", "poster", "--hepsi", atla=",".join(ids[:10]))
    oz = json.loads((out / "FIYAT_1114_OKU.json").read_text(encoding="utf-8"))
    assert rc == 0 and oz["islenen"] == 78 and oz["sayim"] == {"PLAN_OK": 78} and not kayit["api"].puts, oz["sayim"]
    # yaz --hepsi: ATLA uygulanir (10 atlanir), 68 PASS
    rc, out = kos("yaz", "--aile", "poster", "--hepsi", "--confirm", "FIYAT_1114_HEPSI", atla=",".join(ids[:10]))
    oz = json.loads((out / "FIYAT_1114_YAZ.json").read_text(encoding="utf-8"))
    assert rc == 0 and oz["istenen"] == 68, oz["sayim"]
    # yd: poster onay sozcugu yd'de gecmez
    kayit["inv"] = yd_yeni()
    rc, _ = kos("yaz", "--aile", "yd", "--ilanlar", M.ids_oku("yd")[0], "--confirm", "FIYAT_1114")
    assert isinstance(rc, str) and "FIYAT_1114_YD" in rc, rc
    # yd oku: bolum listesi csv ile ayni, yd envanteri PLAN_OK
    rc, out = kos("oku", "--aile", "yd", "--ilanlar", M.ids_oku("yd")[0])
    oz = json.loads((out / "FIYAT_1114_OKU.json").read_text(encoding="utf-8"))
    assert rc == 0 and oz["sayim"] == {"PLAN_OK": 1} and oz["ilanlar"][0]["urun_n"] == 12, oz
    # yd yaz kendi sozcuguyle: PASS
    rc, out = kos("yaz", "--aile", "yd", "--ilanlar", M.ids_oku("yd")[0], "--confirm", "FIYAT_1114_YD")
    oz = json.loads((out / "FIYAT_1114_YAZ.json").read_text(encoding="utf-8"))
    assert rc == 0 and oz["sayim"] == {"PASS": 1}, oz["sayim"]
    eski = SahteApi.get

    def farkli(self, path, params=None, ok404=False):
        if "/shop-sections/listings" in path:
            self._say()
            return {"results": [{"listing_id": "1"}]}
        return eski(self, path, params, ok404)
    SahteApi.get = farkli
    rc, _ = kos("oku", "--aile", "yd", "--ilanlar", M.ids_oku("yd")[0])
    SahteApi.get = eski
    assert isinstance(rc, str) and "bolum" in rc, rc
    return 1


if __name__ == "__main__":
    test()
