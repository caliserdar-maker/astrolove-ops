#!/usr/bin/env python3
"""ornament_kargo testleri (ag yok). Bilinen PASS + bilinen FAIL (CLAUDE.md KALITE 3). Kullanim: python3 scripts/etsy/test_ornament_kargo.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ornament_kargo as K  # noqa: E402
import ornament_taslak as OT  # noqa: E402

SONUC = []


def t(ad, f):
    try:
        f(); SONUC.append((ad, "PASS", ""))
    except AssertionError as e:
        SONUC.append((ad, "FAIL", str(e)[:200]))
    except Exception as e:  # noqa: BLE001
        SONUC.append((ad, "FAIL", f"{type(e).__name__}: {str(e)[:200]}"))


def dur_bekle(f, metin):
    try:
        f()
    except SystemExit as e:
        assert metin in str(e.code), f"DUR metni farkli: {e.code}"
        return
    raise AssertionError("DUR bekleniyordu, gecti")


def kuru_api(n=3):
    lids = {c: str(4600000000 + i) for i, c in enumerate(OT.CIFTLER[:n])}
    api = K.KuruEtsy(lids)
    return api, lids


def t_pass_fiyat():
    api, lids = kuru_api()
    with tempfile.TemporaryDirectory() as d:
        R = K.fiyat(api, Path(d), lids, list(lids))
    assert R["ozet"] == {"PASS": 3}, R["ozet"]
    for s in R["sonuc"]:
        assert all(u["fiyat"] == 19.90 for u in s["sonra"]), s
        assert {u["sku"] for u in s["sonra"]} == {u["sku"] for u in s["once"]}
    puts = [x for x in api.istek if x[0] == "PUT"]
    assert len(puts) == 3, len(puts)
    assert all(x[0] in ("GET", "PUT") for x in api.istek)


def t_zaten():
    api, lids = kuru_api(1)
    with tempfile.TemporaryDirectory() as d:
        K.fiyat(api, Path(d), lids, list(lids))
        api.istek.clear()
        R = K.fiyat(api, Path(d), lids, list(lids))
    assert R["ozet"] == {"ZATEN": 1}, R["ozet"]
    assert not [x for x in api.istek if x[0] == "PUT"], "ikinci kosuda PUT olmamali"


def t_fail_active():
    api, lids = kuru_api(1)
    api.db[next(iter(lids.values()))]["state"] = "active"
    with tempfile.TemporaryDirectory() as d:
        dur_bekle(lambda: K.fiyat(api, Path(d), lids, list(lids)), "draft degil")
    assert not [x for x in api.istek if x[0] == "PUT"]


def t_fail_put_sonrasi_state():
    api, lids = kuru_api(1)
    lid = next(iter(lids.values()))
    orj = api._call

    def bozuk(method, path, **kw):
        r = orj(method, path, **kw)
        if method == "PUT":
            api.db[lid]["state"] = "active"
        return r
    api._call = bozuk
    with tempfile.TemporaryDirectory() as d:
        dur_bekle(lambda: K.fiyat(api, Path(d), lids, list(lids)), "PUT sonrasi")


def t_fail_sku():
    api, lids = kuru_api(1)
    api.db[next(iter(lids.values()))]["inv"]["products"][0]["sku"] = "BASKA"
    with tempfile.TemporaryDirectory() as d:
        dur_bekle(lambda: K.fiyat(api, Path(d), lids, list(lids)), "sku farkli")


def t_fail_urun_sayisi():
    api, lids = kuru_api(1)
    api.db[next(iter(lids.values()))]["inv"]["products"].pop()
    with tempfile.TemporaryDirectory() as d:
        dur_bekle(lambda: K.fiyat(api, Path(d), lids, list(lids)), "urun sayisi")


def t_fail_stok_degisirse():
    api, lids = kuru_api(1)
    lid = next(iter(lids.values()))
    orj = api._call

    def bozuk(method, path, **kw):
        r = orj(method, path, **kw)
        if method == "PUT":
            api.db[lid]["inv"]["products"][0]["offerings"][0]["quantity"] = 1
        return r
    api._call = bozuk
    with tempfile.TemporaryDirectory() as d:
        dur_bekle(lambda: K.fiyat(api, Path(d), lids, list(lids)), "envanter geri okuma farkli")


def t_yasak_baska_ilan():
    api, lids = kuru_api(2)
    api.izinli = frozenset([next(iter(lids.values()))])
    dur_bekle(lambda: api.put_json(f"/listings/{list(lids.values())[1]}/inventory", {}), "YASAK")
    dur_bekle(lambda: api._call("PATCH", f"/shops/1/listings/{list(lids.values())[0]}", data={}), "YASAK")


def t_izin_siniflari():
    class Sahte:
        pass
    for cls, yol, metin in [(K.SaltOkur, ("POST", "/x"), "salt okuma"), (K.ProfilIzin, ("PATCH", "/shops/1/listings/2"), "YASAK (profil)"),
                            (K.ProfilIzin, ("PUT", "/listings/2/inventory"), "YASAK (profil)"), (K.FiyatIzin, ("POST", "/shops/1/listings"), "YASAK (fiyat)")]:
        o = cls.__new__(cls)
        dur_bekle(lambda: o._call(*yol), metin)


def t_hedef():
    h, d = K.hedef_listesi()
    us = [x for x in h if x[0] == "US"]
    assert us and us[0][1:3] == (9.90, 0.90), us
    diger = [x for x in h if x[0] != "US"]
    assert len(diger) == 126 and all(x[1:3] == (13.90, 2.90) for x in diger), (len(diger), diger[:3])
    yok = {"IN", "ZA", "CY", "SA", "UA", "RU"}
    assert not yok & {x[0] for x in h}, yok & {x[0] for x in h}
    assert not d, d
    assert all(x[3] and x[4] and x[3] <= x[4] for x in h)


def t_hedef_fail_abd_degisirse():
    orj = K.KARGO_F
    with tempfile.TemporaryDirectory() as dd:
        R = json.load(open(orj))
        for s in R["satir"]:
            if s["ulke"] == "US":
                s["ucret_1"] = "6.49"
        f = Path(dd) / "k.json"; f.write_text(json.dumps(R))
        K.KARGO_F = f
        try:
            dur_bekle(K.hedef_listesi, "ABD Printful kargo")
        finally:
            K.KARGO_F = orj


def t_hedef_farkli_ucret_disari():
    orj = K.KARGO_F
    with tempfile.TemporaryDirectory() as dd:
        R = json.load(open(orj))
        for s in R["satir"]:
            if s["ulke"] == "JP":
                s["ucret_1"] = "14.99"
        f = Path(dd) / "k.json"; f.write_text(json.dumps(R))
        K.KARGO_F = f
        try:
            h, d = K.hedef_listesi()
        finally:
            K.KARGO_F = orj
    assert "JP" not in {x[0] for x in h} and d and d[0][0] == "JP", (d, len(h))


def t_durum_eksik():
    with tempfile.TemporaryDirectory() as d:
        D = {"ciftler": {c: "4600000001" for c in OT.CIFTLER}, "tamam": OT.CIFTLER[:-1]}
        (Path(d) / "DURUM.json").write_text(json.dumps(D))
        dur_bekle(lambda: K.durum_oku(Path(d)), "tamam olmayan")
        D["tamam"] = list(OT.CIFTLER)
        (Path(d) / "DURUM.json").write_text(json.dumps(D))
        assert len(K.durum_oku(Path(d))) == 78


def t_free_regex():
    assert K.FREE.search("Made and shipped by our production partner, with free shipping.")
    assert not K.FREE.search("You can see the shipping cost and estimated delivery time for your country on this page and at checkout.")


for ad, f in list(globals().items()):
    if ad.startswith("t_") and callable(f):
        t(ad, f)
for ad, s, m in SONUC:
    print(f"{s} {ad} {m}")
fail = sum(1 for x in SONUC if x[1] == "FAIL")
print(f"TOPLAM {len(SONUC)} | PASS {len(SONUC) - fail} | FAIL {fail}")
sys.exit(1 if fail else 0)
