#!/usr/bin/env python3
"""ornament_kargo testleri (ag yok). Bilinen PASS + bilinen FAIL (CLAUDE.md KALITE 3). Taklit YALNIZ ag katmani (_ag, _tek); izin
kontrolleri gercek FiyatIzin / ProfilIzin / SaltOkur siniflarindan gecer. Kullanim: python3 scripts/etsy/test_ornament_kargo.py"""
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


def kf(n=3):
    lids = {c: str(4600000000 + i) for i, c in enumerate(OT.CIFTLER[:n])}
    return K.KuruFiyat(lids), lids


def tmp():
    return tempfile.TemporaryDirectory()


# ---------------- fiyat ----------------
def t_fiyat_pass_tek():
    api, lids = kf(1)
    with tmp() as d:
        R = K.fiyat(api, "1", Path(d), lids, list(lids))
        assert (Path(d) / "fiyat_once" / f"{list(lids)[0]}.json").exists(), "once dosyasi yok"
    assert R["ozet"] == {"PASS": 1}, R["ozet"]
    assert all(u["fiyat"] == 19.90 for u in R["sonuc"][0]["sonra"])
    assert [x[0] for x in api.istek].count("PUT") == 1


def t_fiyat_coklu_pilotsuz_dur():
    api, lids = kf(3)
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "PILOT_CIFT gerekli")
    assert "PUT" not in [x[0] for x in api.istek]


def t_fiyat_coklu_pilot_yazilmamis_dur():
    api, lids = kf(3)
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids), pilot=list(lids)[1]), "pilot")


def t_fiyat_coklu_pilot_ok():
    api, lids = kf(3)
    p = list(lids)[1]
    with tmp() as d:
        K.fiyat(api, "1", Path(d), {p: lids[p]}, [p])
        api.istek.clear()
        R = K.fiyat(api, "1", Path(d), lids, list(lids), pilot=p)
    assert R["ozet"] == {"ZATEN": 1, "PASS": 2}, R["ozet"]
    assert R["sonuc"][0]["cift"] == p


def t_fiyat_active_dur():
    api, lids = kf(1)
    api.db[next(iter(lids.values()))]["state"] = "active"
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "draft degil")
    assert "PUT" not in [x[0] for x in api.istek]


def t_fiyat_put_sonrasi_state_dur():
    api, lids = kf(1)
    lid = next(iter(lids.values())); orj = api._ag

    def bozuk(method, path, **kw):
        r = orj(method, path, **kw)
        if method == "PUT":
            api.db[lid]["state"] = "active"
        return r
    api._ag = bozuk
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "inactive yapilmali")


def t_fiyat_stok_degisirse_dur():
    api, lids = kf(1)
    lid = next(iter(lids.values())); orj = api._ag

    def bozuk(method, path, **kw):
        r = orj(method, path, **kw)
        if method == "PUT":
            api.db[lid]["inv"]["products"][0]["offerings"][0]["quantity"] = 1
        return r
    api._ag = bozuk
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "envanter geri okuma farkli")


def t_fiyat_on_property_degisirse_dur():
    api, lids = kf(1)
    lid = next(iter(lids.values())); orj = api._ag

    def bozuk(method, path, **kw):
        r = orj(method, path, **kw)
        if method == "PUT":
            api.db[lid]["inv"]["sku_on_property"] = []
        return r
    api._ag = bozuk
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "on_property farkli")


def t_fiyat_sku_ve_sayi_dur():
    api, lids = kf(1)
    api.db[next(iter(lids.values()))]["inv"]["products"][0]["sku"] = "BASKA"
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "sku farkli")
    api, lids = kf(1)
    api.db[next(iter(lids.values()))]["inv"]["products"].pop()
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "urun sayisi")


def t_fiyat_kota_ilan_oncesi_dur():
    api, lids = kf(2)
    api.remaining = str(K.KOTA_MIN + K.ILAN_ISTEK + 1)     # magaza GET sonrasi 1 eksik -> ilk ilandan ONCE DUR
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), {list(lids)[0]: lids[list(lids)[0]]}, [list(lids)[0]]), "kota")
    assert "PUT" not in [x[0] for x in api.istek]


def t_fiyat_kuru_put_yok():
    api, lids = kf(2)
    with tmp() as d:
        R = K.fiyat(api, "1", Path(d), lids, list(lids), kuru=True)
        g = json.load(open(Path(d) / "fiyat_kuru" / f"{list(lids)[0]}.json"))
    assert R["ozet"] == {"KURU": 2} and "PUT" not in [x[0] for x in api.istek]
    assert all(p["offerings"][0]["price"] == 19.90 for p in g["put"]["products"]) and g["put"]["sku_on_property"] == [OT.P_STYLE]


def t_izin_gercek_fiyat():
    api, lids = kf(2)
    a, b = list(lids.values())
    api.izinli = frozenset([a])
    dur_bekle(lambda: api.put_json(f"/listings/{b}/inventory", {}), "YASAK (fiyat)")
    dur_bekle(lambda: api.patch(f"/shops/1/listings/{a}", {"state": "active"}), "YASAK (fiyat)")
    dur_bekle(lambda: api.post("/shops/1/listings", {}), "YASAK (fiyat)")
    dur_bekle(lambda: api.tek_post("/shops/1/shipping-profiles", {}), "YASAK (fiyat)")
    assert not [x for x in api.istek if x[0] != "GET"], api.istek


def t_izin_gercek_profil_ve_salt():
    p = K.KuruProfil()
    dur_bekle(lambda: p.put_json("/listings/1/inventory", {}), "YASAK (profil)")
    dur_bekle(lambda: p.patch("/shops/1/listings/1", {}), "YASAK (profil)")
    dur_bekle(lambda: p.tek_post("/shops/1/listings", {}), "YASAK (profil)")
    s = K.SaltOkur.__new__(K.SaltOkur)
    dur_bekle(lambda: s._call("POST", "/x"), "salt okuma")
    dur_bekle(lambda: s.tek_post("/shops/1/shipping-profiles", {}), "salt okuma")


# ---------------- profil ----------------
def t_profil_pass():
    p = K.KuruProfil()
    with tmp() as d:
        R = K.profil(p, "1", Path(d))
        assert (Path(d) / "KARGO_PROFIL.json").exists()
    assert R["kontrol"] == {"hedef_beklenen": 127, "profilde": 127, "reddedilen": 0}, R["kontrol"]
    posts = [x for x in p.istek if x[0] == "POST"]
    assert len(posts) == 127 and posts[0][1].endswith("/shipping-profiles")
    us = posts[0][2]
    assert (us["destination_country_iso"], us["primary_cost"], us["secondary_cost"], us["origin_country_iso"]) == ("US", 9.90, 0.90, "LV")
    assert all(x[2]["primary_cost"] == 13.90 and x[2]["secondary_cost"] == 2.90 for x in posts[1:])
    assert not {"IN", "ZA", "CY", "SA", "UA"} & {x[2].get("destination_country_iso") for x in posts}


def t_profil_tekrar_kosu_idempotent():
    p = K.KuruProfil()
    with tmp() as d:
        K.profil(p, "1", Path(d))
        p.istek.clear()
        R = K.profil(p, "1", Path(d))
    assert not [x for x in p.istek if x[0] == "POST"] and R["kontrol"]["profilde"] == 127


def t_profil_yarida_devam():
    p = K.KuruProfil()
    orj = p._tek
    say = {"n": 0}

    def kesik(path, body):
        say["n"] += 1
        if say["n"] == 40:
            return "BELIRSIZ", None, "Timeout"
        return orj(path, body)
    p._tek = kesik
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "BELIRSIZ")
        assert (Path(d) / "KARGO_PROFIL.json").exists(), "finally dokumu yok"
        p._tek = orj; p.istek.clear()
        R = K.profil(p, "1", Path(d))
    assert R["kontrol"]["profilde"] == 127
    assert len([x for x in p.istek if x[0] == "POST"]) == 127 - 39, len([x for x in p.istek if x[0] == "POST"])


def t_profil_hepsi_400_dur():
    p = K.KuruProfil()
    p.ret = {cc: 400 for cc, *_ in K.hedef_listesi()[0] if cc != "US"}
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "DUR: hedef")


def t_profil_izinli_ret_atlanir():
    p = K.KuruProfil()
    p.ret = {"XK": 400, "BV": 400}
    with tmp() as d:
        R = K.profil(p, "1", Path(d))
    assert R["kontrol"] == {"hedef_beklenen": 127, "profilde": 125, "reddedilen": 2}, R["kontrol"]


def t_profil_izinli_ama_500_dur():
    p = K.KuruProfil()
    p.ret = {"XK": 500}
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "XK -> 500")


def t_profil_kota_butce_dur():
    p = K.KuruProfil()
    p.remaining = "100"
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "profil butcesi")
    assert not [x for x in p.istek if x[0] == "POST"]


def t_profil_kopya_hedef_dur():
    p = K.KuruProfil()
    with tmp() as d:
        K.profil(p, "1", Path(d))
        prof = next(iter(p.profiller.values()))
        prof["shipping_profile_destinations"].append(dict(prof["shipping_profile_destinations"][1]))
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "kopya hedef")


def t_profil_var_ama_yanlis_cikis_dur():
    p = K.KuruProfil()
    with tmp() as d:
        K.profil(p, "1", Path(d))
        next(iter(p.profiller.values()))["origin_country_iso"] = "US"
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "cikis ulkesi")


def t_profil_yanlis_ucret_dur():
    p = K.KuruProfil()
    orj = p._tek

    def kotu(path, body):
        if body.get("destination_country_iso") == "JP":
            body = dict(body, primary_cost=12.90)
        return orj(path, body)
    p._tek = kotu
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "JP")


def t_profil_everywhere_dur():
    p = K.KuruProfil()
    with tmp() as d:
        K.profil(p, "1", Path(d))
        next(iter(p.profiller.values()))["shipping_profile_destinations"].append(dict(destination_country_iso=None, destination_region="none"))
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "ulke disi hedef")


def t_profil_abd_red_dur():
    p = K.KuruProfil()
    orj = p._tek
    p._tek = lambda path, body: (400, None, "US red") if path.endswith("/shipping-profiles") else orj(path, body)
    with tmp() as d:
        dur_bekle(lambda: K.profil(p, "1", Path(d)), "profil olusturma 400")


def t_profil_kuru_yazmaz():
    p = K.KuruProfil()
    with tmp() as d:
        R = K.profil(p, "1", Path(d), kuru=True)
        assert (Path(d) / "KARGO_PROFIL_PLAN.json").exists()
    assert len(R["plan"]) == 127 and not [x for x in p.istek if x[0] == "POST"]


# ---------------- veri ----------------
def t_hedef():
    h, d = K.hedef_listesi()
    assert [x for x in h if x[0] == "US"][0][1:3] == (9.90, 0.90)
    diger = [x for x in h if x[0] != "US"]
    assert len(diger) == 126 and all(x[1:3] == (13.90, 2.90) for x in diger)
    assert not {"IN", "ZA", "CY", "SA", "UA", "RU"} & {x[0] for x in h}
    assert not d


def _veri_degistir(fn):
    orj = K.KARGO_F
    with tmp() as dd:
        R = json.load(open(orj)); fn(R)
        f = Path(dd) / "k.json"; f.write_text(json.dumps(R))
        K.KARGO_F = f
        try:
            return K.hedef_listesi()
        finally:
            K.KARGO_F = orj


def t_hedef_abd_degisirse_dur():
    def f(R):
        [s for s in R["satir"] if s["ulke"] == "US"][0]["ucret_1"] = "6.49"
    dur_bekle(lambda: _veri_degistir(f), "ABD Printful kargo")


def t_hedef_farkli_ucret_disari():
    def f(R):
        [s for s in R["satir"] if s["ulke"] == "JP"][0]["ucret_1"] = "14.99"
    h, d = _veri_degistir(f)
    assert "JP" not in {x[0] for x in h} and d[0][0] == "JP"


def t_hedef_gun_gecersiz_dur():
    def f(R):
        [s for s in R["satir"] if s["ulke"] == "DE"][0]["gun_1"] = [10, 60]
    dur_bekle(lambda: _veri_degistir(f), "teslim gunu")


def t_durum():
    with tmp() as d:
        D = {"ciftler": {c: "4600000001" for c in OT.CIFTLER}, "tamam": OT.CIFTLER[:-1]}
        (Path(d) / "DURUM.json").write_text(json.dumps(D))
        dur_bekle(lambda: K.durum_oku(Path(d)), "tamam olmayan")
        D["tamam"] = list(OT.CIFTLER)
        (Path(d) / "DURUM.json").write_text(json.dumps(D))
        assert len(K.durum_oku(Path(d))) == 78


def t_para_birimi_dur():
    api, lids = kf(1)
    orj = api._ag
    api._ag = lambda m, p, **kw: {"currency_code": "EUR"} if p == "/shops/1" else orj(m, p, **kw)
    with tmp() as d:
        dur_bekle(lambda: K.fiyat(api, "1", Path(d), lids, list(lids)), "para birimi")


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
