#!/usr/bin/env python3
"""kupa_zam_1114 yerel testi (sahte Etsy; gercek aga cikmaz). Kosu: python3 scripts/etsy/test_kupa_zam_1114.py

Envanter yapisi: 8 stil (513) x 2 boy (514), kupa_taslak.py:505-511 yapisi (price/sku_on_property [513, 514]).
Canli yapi yaz oncesi 'oku' kosusuyla olculur; gercek ONCE.json'dan fixture yaz onayindan once eklenir.
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


socket.socket.connect = _ag_yok          # TEST AGI: baglanti duzeyinde kapali
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import kupa_zam_1114 as M  # noqa: E402

STIL = ["Orange Blossom", "Purple Fig", "Olive Breeze", "Pomegranate Bloom", "Almond Blossom", "Lemon Grove", "Blue Grape", "Golden Loquat"]
SONUC = []


def ok(ad):
    SONUC.append(ad)


def inv(f11=1290, f15=1690):
    pr = []
    for i, st in enumerate(STIL):
        for j, (b, f) in enumerate((("11 oz", f11), ("15 oz", f15))):
            pr.append({"sku": f"KUPA-ARI_LEO-0{i + 1}-{b[:2]}", "is_deleted": False,
                       "property_values": [{"property_id": 513, "property_name": "Style", "values": [st], "value_ids": [100 + i]},
                                           {"property_id": 514, "property_name": "Size", "values": [b], "value_ids": [200 + j]}],
                       "offerings": [{"price": {"amount": f, "divisor": 100}, "quantity": 999, "is_enabled": True, "is_deleted": False,
                                      "readiness_state_id": 77}]})
    pr[5]["offerings"][0]["is_enabled"] = False   # kapali urun fiyat disinda aynen korunmali
    return {"products": pr, "price_on_property": [513, 514], "quantity_on_property": [], "sku_on_property": [513, 514],
            "readiness_state_on_property": []}


VIMG = [{"property_id": 513, "value_id": 100 + i, "image_id": 900 + i} for i in range(8)]


def fiyat_kumesi(body):
    return sorted({(p["property_values"][1]["values"][0], o["price"]) for p in body["products"] for o in p["offerings"]})


def test_plan_govde():
    prs, h, z = M.plan(inv())
    assert not h and len(prs) == 16 and not z, h
    ok("plan eski fiyat PLAN")
    assert fiyat_kumesi(M.govde(inv())) == [("11 oz", 24.9), ("15 oz", 29.9)]
    ok("govde hedef fiyat")
    b = M.govde(inv())
    assert b["price_on_property"] == [513, 514] and b["sku_on_property"] == [513, 514]
    assert all(p["property_values"][0]["value_ids"] and p["offerings"][0]["quantity"] == 999
               and p["offerings"][0]["readiness_state_id"] == 77 and p["sku"] for p in b["products"])
    assert [o["is_enabled"] for p in b["products"] for o in p["offerings"]].count(False) == 1
    assert all(pv.get("property_name") for p in b["products"] for pv in p["property_values"])
    ok("govde fiyat disi alanlar")
    assert M.plan(inv(2490, 2990))[2] and not M.plan(inv(2490, 2990))[1]
    ok("hedefte ZATEN")
    assert M.plan(inv(2490, 1690))[1] == [] and not M.plan(inv(2490, 1690))[2]
    ok("yarim yazilmis ilan: kapi gecer, ZATEN degil")
    for f11, f15 in ((2400, 2900), (1290, 2990 + 500), (1990, 1690)):
        assert M.plan(inv(f11, f15))[1], (f11, f15)
    ok("beklenmeyen fiyat FAIL")
    x = inv(); x["products"].pop()
    assert M.plan(x)[1]
    ok("eksik urun FAIL")
    x = inv(); x["products"][0]["property_values"][1]["values"] = ["20 oz"]
    assert any("bilinmeyen boy" in s for s in M.plan(x)[1])
    ok("bilinmeyen boy FAIL")
    x = inv(); x["products"][0]["offerings"].append(copy.deepcopy(x["products"][0]["offerings"][0]))
    assert M.plan(x)[1]
    ok("cift teklif FAIL")
    x = inv(); x["products"][0]["property_values"] = x["products"][0]["property_values"][1:]
    assert M.plan(x)[1]
    ok("stilsiz urun FAIL")
    assert M.bag_gecerli(inv(), VIMG) and not M.bag_gecerli(inv(), VIMG[:7])
    assert not M.bag_gecerli(inv(), [dict(v, value_id=v["value_id"] + 50) for v in VIMG])
    ok("stil bagi kontrolu")
    assert not M.kota_yeter(None, 10) and not M.kota_yeter(29, 10) and M.kota_yeter(30, 10)
    ok("kota (None KOTA_BEKLE, 20+10)")


class SahteApi:
    def __init__(self, inv_, kalan=4000, bolum="Zodiac Couple Mugs", bolum_id=60980873, ilanlar=None, bag_kaybet=False, bozan=None):
        self.inv, self.remaining, self.puts, self.posts, self.bag_kaybet, self.bozan = inv_, kalan, [], [], bag_kaybet, bozan
        self.per = [{"question_id": 5, "question_text": "Personalization", "question_type": "text_input", "required": True,
                     "max_allowed_characters": 256, "instructions": "Name"}]
        self.vimg = copy.deepcopy(VIMG)
        self.L = {"state": "active", "description": "A mug for two", "is_personalizable": True}
        self.secs = [{"shop_section_id": 60895624, "title": "1st Anniversary Gifts"},
                     {"shop_section_id": bolum_id, "title": bolum}]
        self.ilanlar = ilanlar if ilanlar is not None else [str(4600000000 + i) for i in range(78)]

    def _say(self):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"kota kalan {self.remaining} < 10")
        self.remaining -= 1

    def get(self, path, params=None, ok404=False):
        self._say()
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(self.vimg)}
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(self.per)}
        if path.endswith("/sections"):
            return {"results": copy.deepcopy(self.secs)}
        if "/shop-sections/listings" in path:
            assert params["shop_section_ids"] == self.secs[1]["shop_section_id"], params
            o = params.get("offset", 0)
            return {"results": [{"listing_id": x} for x in self.ilanlar[o:o + 100]]}
        return copy.deepcopy(self.L)

    def put_json(self, path, body):
        self._say()
        assert path.endswith("/inventory"), path
        self.puts.append((path, copy.deepcopy(body)))
        yeni = {k: v for k, v in copy.deepcopy(body).items() if k != "products"}   # gövdenin TAMAMI uygulanir
        yeni["products"] = []
        for q in copy.deepcopy(body["products"]):
            q["is_deleted"] = False
            for o in q["offerings"]:
                o["price"] = {"amount": int(round(o["price"] * 100)), "divisor": 100}
                o["is_deleted"] = False
            if self.bag_kaybet:
                for pv in q["property_values"]:
                    pv["value_ids"] = [i + 1000 for i in pv["value_ids"]]
            yeni["products"].append(q)
        self.inv = yeni
        if self.bozan:
            self.bozan(self)
        if self.bag_kaybet:
            self.vimg = []

    def post_json(self, path, body):
        self._say()
        self.posts.append(body)
        self.vimg = [{"property_id": v["property_id"], "value_id": v["value_id"], "image_id": v["image_id"]}
                     for v in body["variation_images"]]

    def kota_kapisi(self, ne=""):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit("DUR: kota esigi")


def kos(api, *arg, atla=""):
    class FakeStore:
        def __init__(self, *a):
            pass

        def needs_refresh(self):
            return False

    sys.modules["etsy_common"] = types.SimpleNamespace(Etsy=lambda store: api, TokenStore=FakeStore, mask=lambda x: None,
                                                       KOTA_SINIRI=10)
    os.environ.update({"TOKEN_FILE": "x", "ETSY_SHOP_ID": "1", "ETSY_API_KEY": "k", "ETSY_SHARED_SECRET": "s", "ATLA": atla})
    sys.argv = ["kupa_zam_1114.py", *arg]
    M.OUT = Path(tempfile.mkdtemp())
    rc = 0
    try:
        M.main()
    except SystemExit as e:
        rc = e.code
    js = list(M.OUT.glob("KUPA_ZAM_1114_*.json"))
    return rc, (json.loads(js[0].read_text()) if js else None), M.OUT


def test_main():
    # onaysiz yaz: DUR, PUT yok
    a = SahteApi(inv())
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0])
    assert rc == 1 and "KUPA_ZAM_1114" in oz["genel_hata"] and not a.puts, oz
    ok("yaz onaysiz DUR")
    # sade onayiyla cift yazimi: DUR
    a = SahteApi(inv())
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114_SADE")
    assert rc == 1 and not a.puts
    ok("aile onay sozcugu ayri")
    # hepsi tek-ilan onayiyla: DUR
    a = SahteApi(inv())
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114")
    assert rc == 1 and "KUPA_ZAM_1114_HEPSI" in oz["genel_hata"] and not a.puts
    ok("hepsi icin _HEPSI onayi")
    # oku --hepsi: ATLA uygulanmaz, 78 PLAN_OK, PUT yok
    a = SahteApi(inv())
    rc, oz, _ = kos(a, "oku", "--aile", "cift", "--hepsi", atla=",".join(a.ilanlar[:5]))
    assert rc == 0 and oz["sayim"] == {"PLAN_OK": 78} and oz["bolum_ilan"] == 78 and not a.puts, oz["sayim"]
    ok("oku hepsi 78 PLAN_OK, ATLA yok")
    # DOKUNMA ilani listeden duser
    a = SahteApi(inv(), ilanlar=[str(4600000000 + i) for i in range(78)] + ["4597843405"])
    rc, oz, _ = kos(a, "oku", "--aile", "cift", "--hepsi")
    assert oz["bolum_ilan"] == 78 and all(r["ilan"] != "4597843405" for r in oz["ilanlar"])
    rc, oz, _ = kos(SahteApi(inv(), ilanlar=a.ilanlar), "yaz", "--aile", "cift", "--ilanlar", "4597843405", "--confirm", "KUPA_ZAM_1114")
    assert rc == 1 and "DOKUNMA" in oz["genel_hata"]
    ok("DOKUNMA yazilmaz")
    # sade yazimi kapali (onay sozcugu dogru olsa da), PUT yok
    a = SahteApi(inv(), bolum="Zodiac Sign Mugs", bolum_id=61234567, ilanlar=[str(4700000000 + i) for i in range(12)])
    rc, oz, _ = kos(a, "yaz", "--aile", "sade", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114_SADE")
    assert rc == 1 and "sade yazimi kapali" in oz["genel_hata"] and not a.puts, oz
    ok("sade yazimi kapali")
    # sade: bolum adindan bulunur, 12 ilan
    a = SahteApi(inv(), bolum="Zodiac Sign Mugs", bolum_id=61234567, ilanlar=[str(4700000000 + i) for i in range(12)])
    rc, oz, _ = kos(a, "oku", "--aile", "sade", "--hepsi")
    assert rc == 0 and oz["bolum"] == 61234567 and oz["sayim"] == {"PLAN_OK": 12}, oz
    ok("sade bolum adindan")
    # sade bolumu yoksa DUR
    a = SahteApi(inv(), bolum="Zodiac Sign Mug", ilanlar=[])
    rc, oz, _ = kos(a, "oku", "--aile", "sade", "--hepsi")
    assert rc == 1 and "bulundu" in oz["genel_hata"]
    ok("sade bolum yok DUR")
    # cift bolum id farkliysa DUR
    a = SahteApi(inv(), bolum_id=1)
    rc, oz, _ = kos(a, "oku", "--aile", "cift", "--hepsi")
    assert rc == 1 and "60980873" in oz["genel_hata"]
    ok("cift bolum id kontrolu")
    # yaz hepsi: bolumde 77 ilan varsa DUR, PUT yok
    a = SahteApi(inv(), ilanlar=[str(4600000000 + i) for i in range(77)])
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114_HEPSI")
    assert rc == 1 and "beklenen 78" in oz["genel_hata"] and not a.puts
    ok("yaz hepsi ilan sayisi kapisi")
    # yaz tek ilan: PUT, geri okuma, PASS, TAMAM_EK
    a = SahteApi(inv())
    rc, oz, out = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    r = oz["ilanlar"][0]
    assert rc == 0 and r["durum"] == "PASS" and len(a.puts) == 1 and r["renk_onarim"] == "gerekmedi", r
    assert fiyat_kumesi(a.puts[0][1]) == [("11 oz", 24.9), ("15 oz", 29.9)]
    assert (out / "TAMAM_EK.txt").read_text() == a.ilanlar[0] + "\n"
    ok("yaz tek ilan PASS")
    # yaz hepsi ATLA: atlananlar yazilmaz
    a = SahteApi(inv(), ilanlar=[str(4600000000 + i) for i in range(78)])
    a.inv_kopya = inv()
    os.environ["TAMAM_LISTE"] = ",".join(a.ilanlar[:77])
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114_HEPSI", atla=",".join(a.ilanlar[:77]))
    assert rc == 0 and oz["istenen"] == 1 and oz["ilanlar"][0]["ilan"] == a.ilanlar[77] and len(a.puts) == 1
    assert oz["kapsam_eksik"] == []
    ok("yaz hepsi ATLA (onceki TAMAM)")
    # elle atlanan (TAMAM'da olmayan) ilan: kapsam_eksik, sonuc HATA
    a = SahteApi(inv(), ilanlar=[str(4600000000 + i) for i in range(78)])
    os.environ["TAMAM_LISTE"] = ",".join(a.ilanlar[:70])
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114_HEPSI", atla=",".join(a.ilanlar[:77]))
    assert rc == 1 and oz["sonuc"] == "HATA" and oz["kapsam_eksik"] == a.ilanlar[70:77] and len(a.puts) == 1, oz["kapsam_eksik"]
    os.environ["TAMAM_LISTE"] = ""
    ok("elle atla kapsam_eksik HATA")
    # hepsi + yaz, kota yetmez: ilk KOTA_BEKLE'de durur
    a = SahteApi(inv(), kalan=31)
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114_HEPSI")
    assert rc == 0 and oz["islenen"] == 1 and oz["sonuc"] == "KOTA" and not a.puts, oz["sayim"]
    ok("hepsi KOTA_BEKLE'de durur")
    # zaten hedefte: PUT yok
    a = SahteApi(inv(2490, 2990))
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    assert rc == 0 and oz["ilanlar"][0]["durum"] == "ZATEN" and not a.puts
    ok("ZATEN PUT yok")
    # kapi FAIL: PUT yok
    a = SahteApi(inv(2200, 1690))
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    assert rc == 1 and oz["ilanlar"][0]["durum"] == "FAIL_KAPI" and not a.puts
    ok("FAIL_KAPI PUT yok")
    # aktif degil: yazilmaz
    a = SahteApi(inv()); a.L["state"] = "draft"
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    assert rc == 1 and oz["ilanlar"][0]["durum"] == "ATLANDI_STATE" and not a.puts and oz["sonuc"] == "HATA"
    ok("draft yazilmaz")
    # kota yetmez (ilan basinda): okuma ve yazma yok, etiket KOTA, cikis 0
    a = SahteApi(inv(), kalan=31)
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    assert rc == 0 and oz["sonuc"] == "KOTA" and oz["ilanlar"][0]["durum"].startswith("KOTA_BEKLE") and not a.puts, oz
    ok("kota ilan basinda KOTA_BEKLE")
    # kota okumalardan sonra yetmez (PUT oncesi): yazma yok
    a = SahteApi(inv(), kalan=34)   # 2 bolum okumasi -> 32 >= 30 baslar, 4 okuma -> 28 < 30
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    assert oz["ilanlar"][0]["durum"].startswith("KOTA_BEKLE") and "yazma yok" in oz["ilanlar"][0]["durum"] and not a.puts, oz
    ok("kota PUT oncesi KOTA_BEKLE")
    # Etsy fiyat disi alani degistirirse FAIL (sku, state, kisisellestirme sorusu, is_enabled)
    bozanlar = {"sku": lambda s: s.inv["products"][0].update(sku="X"),
                "state": lambda s: s.L.update(state="inactive"),
                "soru": lambda s: s.per[0].update(max_allowed_characters=100),
                "is_enabled": lambda s: s.inv["products"][5]["offerings"][0].update(is_enabled=True),
                "kisisel": lambda s: s.L.update(is_personalizable=False)}
    import time as _t
    uyku, _t.sleep = _t.sleep, lambda s: None
    try:
        for ad, bz in bozanlar.items():
            a = SahteApi(inv(), bozan=bz)
            rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
            assert rc == 1 and oz["ilanlar"][0]["durum"] == "FAIL", (ad, oz["ilanlar"][0])
            ok(f"fiyat disi degisim FAIL: {ad}")
        # geri okuma tutmaz VE stil bagi koparsa onarim yazilmaz
        a = SahteApi(inv(), bag_kaybet=True, bozan=bozanlar["sku"])
        rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
        assert oz["ilanlar"][0]["renk_onarim"].startswith("yapilmadi") and not a.posts, oz["ilanlar"][0]
        ok("tutarsiz ilanda onarim yok")
    finally:
        _t.sleep = uyku
    # PUT hata verirse yazmadan tek geri okuma kaydedilir
    a = SahteApi(inv())
    def patla(path, body):
        a.puts.append((path, body))
        raise RuntimeError("503")
    a.put_json = patla
    rc, oz, out = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    r = oz["ilanlar"][0]
    assert rc == 1 and r["durum"].startswith("FAIL_YAZILDI_DOGRULANMADI") and isinstance(r["hata_sonrasi"], dict), r
    assert r["hata_sonrasi"]["stil_bag_gecerli"] and (out / a.ilanlar[0] / "SONRA_HATA.json").is_file() and not a.posts
    ok("PUT hatasi sonrasi geri okuma")
    # stil bagi kaybolursa ada gore geri yazilir
    a = SahteApi(inv(), bag_kaybet=True)
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", a.ilanlar[0], "--confirm", "KUPA_ZAM_1114")
    r = oz["ilanlar"][0]
    assert r["durum"] == "PASS" and r["renk_onarim"] == "ada gore geri yazildi" and len(a.posts) == 1, r
    assert {v["value_id"] for v in a.vimg} == {1100 + i for i in range(8)}
    ok("stil bagi onarimi")
    # yazim sonrasi fiyat tutmazsa FAIL, ilk FAIL'de durur
    a = SahteApi(inv(), ilanlar=[str(4600000000 + i) for i in range(78)])
    a.put_json = lambda path, body: a.puts.append((path, body))   # fiyat degismiyor
    import time as _t
    uyku, _t.sleep = _t.sleep, lambda s: None
    try:
        rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--hepsi", "--confirm", "KUPA_ZAM_1114_HEPSI")
    finally:
        _t.sleep = uyku
    assert rc == 1 and oz["islenen"] == 1 and oz["ilanlar"][0]["durum"] == "FAIL" and len(a.puts) == 1, oz["sayim"]
    ok("geri okuma FAIL ilk ilanda durur")


def test_gercek_veri():
    """Canli olcum: kosu 43518175873 (oku, cift), ilan 4598537101 ONCE.json (testdata_kupa_4598537101.json)."""
    G = json.loads((KOK / "testdata_kupa_4598537101.json").read_text(encoding="utf-8"))
    prs, h, z = M.plan(G["inventory"])
    assert not h and len(prs) == 16 and not z and M.bag_gecerli(G["inventory"], G["vimg"]), h
    ok("gercek envanter PLAN_OK, stil bagi gecerli")
    b = M.govde(G["inventory"])
    assert fiyat_kumesi(b) == [("11 oz", 24.9), ("15 oz", 29.9)]
    once = {p["sku"]: p for p in G["inventory"]["products"]}
    for p in b["products"]:
        o = once[p["sku"]]
        assert [(pv["property_id"], pv["values"], pv["value_ids"]) for pv in p["property_values"]] == \
               [(pv["property_id"], pv["values"], pv["value_ids"]) for pv in o["property_values"]]
        assert (p["offerings"][0]["quantity"], p["offerings"][0]["is_enabled"], p["offerings"][0]["readiness_state_id"]) == \
               (o["offerings"][0]["quantity"], o["offerings"][0]["is_enabled"], o["offerings"][0]["readiness_state_id"])
    assert b["price_on_property"] == [513, 514] and b["sku_on_property"] == [513, 514] and "listing" not in b
    ok("gercek envanter govdesi: fiyat disi birebir")
    a = SahteApi(copy.deepcopy(G["inventory"]), ilanlar=["4598537101"] + [str(4600000000 + i) for i in range(77)])
    a.vimg, a.per, a.L = copy.deepcopy(G["vimg"]), copy.deepcopy(G["per"]), copy.deepcopy(G["listing"])
    rc, oz, _ = kos(a, "yaz", "--aile", "cift", "--ilanlar", "4598537101", "--confirm", "KUPA_ZAM_1114")
    r = oz["ilanlar"][0]
    assert rc == 0 and r["durum"] == "PASS" and r["renk_onarim"] == "gerekmedi" and len(a.puts) == 1, r
    ok("gercek veriyle yaz PASS")
    assert M.soru_imza(G["per"]) == M.soru_imza(copy.deepcopy(G["per"]))
    ok("gercek kisisellestirme sorusu imzasi")


def test_eski_arac_kapali():
    import kupa_fiyat as K
    for arg in (["yaz", "--ilanlar", "1", "--confirm", "KUPA_FIYAT"], ["oku", "--hepsi"]):
        sys.argv = ["kupa_fiyat.py", *arg]
        try:
            K.main()
            raise AssertionError("kupa_fiyat acik")
        except SystemExit as e:
            assert "kapali" in str(e.code), e.code
    ok("eski kupa_fiyat oku ve yaz kapali")


if __name__ == "__main__":
    test_plan_govde()
    test_main()
    test_gercek_veri()
    test_eski_arac_kapali()
    print(f"TOPLAM test_kupa_zam_1114: {len(SONUC)}/{len(SONUC)} PASS")
