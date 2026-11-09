#!/usr/bin/env python3
"""canli_yapi_olc testleri (ag yok). Bilinen PASS + bilinen FAIL (CLAUDE.md KALITE 3). Taklit YALNIZ ag katmani:
etsy_common.requests.request / requests.post; istekler gercek Etsy._call yolundan (kota tabani, tempo, hata) gecer.
ZAYIF TEST: batch ve tek ilan envanter yanit semalari OLCULMEDI (sahte yanit bicimi Etsy belgesinden degil, depo emsalinden:
kupa_galeri78 / ornament_taslak envanter okumalari); bu semaya dayanan testler "(ZAYIF: sema olculmedi, prob ile olculecek)".
Sahte ilan kimlikleri 900000000N bicimi (emsal test_ornament_taslak.py:146). Kullanim: python3 scripts/etsy/test_canli_yapi_olc.py"""
import contextlib
import csv
import io
import itertools
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as EC  # noqa: E402
import canli_yapi_olc as C  # noqa: E402

os.environ.pop("GITHUB_STEP_SUMMARY", None)
SONUC = []
ZAYIF = " (ZAYIF: sema olculmedi, prob ile olculecek)"


def t(ad, f):
    try:
        f(); SONUC.append((ad, "PASS", ""))
    except AssertionError as e:
        SONUC.append((ad, "FAIL", str(e)[:200]))
    except SystemExit as e:
        SONUC.append((ad, "FAIL", f"beklenmeyen DUR: {str(e.code)[:200]}"))
    except Exception as e:  # noqa: BLE001
        SONUC.append((ad, "FAIL", f"{type(e).__name__}: {str(e)[:200]}"))


def dur(f, metin):
    try:
        f()
    except SystemExit as e:
        assert metin in str(e.code), f"DUR metni farkli: {e.code}"
        return str(e.code)
    raise AssertionError("DUR bekleniyordu, gecti")


class Store:
    api_key_header = "k"
    access_token = "t"
    bozuk = False

    def needs_refresh(self, margin=300):
        return False

    def refresh(self):
        if self.bozuk:
            raise SystemExit("HATA: token yenileme 400: invalid_grant")


def inv(menuler, acik=True, rsd=111, eksik=0):
    """menuler: [(property_id, ad, [degerler])] -> tam carpim urunler (eksik: sondan cikarilan urun)."""
    prods = []
    for kombi in itertools.product(*[[(pid, ad, v) for v in vals] for pid, ad, vals in menuler]):
        prods.append({"sku": "S", "property_values": [{"property_id": pid, "property_name": ad, "value_ids": [1], "values": [v]}
                                                        for pid, ad, v in kombi],
                      "offerings": [{"price": {"amount": 100, "divisor": 100}, "quantity": 1, "is_enabled": acik, "readiness_state_id": rsd}]})
    if eksik:
        prods = prods[:-eksik]
    return {"products": prods, "price_on_property": [m[0] for m in menuler], "quantity_on_property": [],
            "sku_on_property": [m[0] for m in menuler], "readiness_state_on_property": []}


def menu(*sayilar, pids=(514, 200, 513)):
    return [(pids[i], f"M{i}", [f"v{j}" for j in range(n)]) for i, n in enumerate(sayilar)]


class Sahte:
    """Sahte Etsy (ag katmani). remaining: x-remaining-today. INV: lid -> envanter. batch_env: batch'te 'inventory' doner mi."""
    def __init__(self, remaining=1000, batch_env=True):
        self.remaining, self.batch_env = remaining, batch_env
        self.INV, self.istek, self.post, self.hata, self.tanim_count = {}, [], 0, {}, 1

    def ilan(self, lid, env):
        L = {"listing_id": int(lid), "state": "active", "shipping_profile_id": 5, "return_policy_id": 6, "shop_section_id": 7,
             "taxonomy_id": 8, "title": "x"}
        if env and lid in self.INV:
            L["inventory"] = self.INV[lid]
        return L

    def request(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):
        yol = url[len(EC.API):]
        self.istek.append((method, yol))
        for rx, h in self.hata.items():
            if re.search(rx, yol):
                if isinstance(h, BaseException):
                    raise h
                if isinstance(h, tuple):                 # (kod, ek basliklar), or. (429, {"retry-after": "3600"})
                    y = Y(h[0], {"error": "x"}, self.remaining); y.headers.update(h[1]); return y
                return Y(h, {"error": f"yok {yol}"}, self.remaining)
        if method != "GET":
            return Y(500, {}, self.remaining)
        if re.fullmatch(r"/shops/1", yol):
            j = {"shop_id": 1}
        elif yol == "/listings/batch":
            ids = params["listing_ids"].split(",")
            env = self.batch_env and "Inventory" in (params.get("includes") or "")
            j = {"count": len(ids), "results": [self.ilan(i, env) for i in ids if i in self.INV or not self.INV]}
        elif re.fullmatch(r"/listings/\d+/inventory", yol):
            j = self.INV.get(yol.split("/")[2], {})
        elif re.fullmatch(r"/shops/1/(readiness-state-definitions|policies/return|sections)", yol):
            j = {"count": self.tanim_count, "results": [{"x": 1}]}
        else:
            return Y(404, {"error": "yok"}, self.remaining)
        self.remaining -= 1                      # x-remaining-today: bu istek sayildiktan sonra kalan
        return Y(200, j, self.remaining)

    def post_(self, *a, **k):
        self.post += 1
        return Y(201, {}, self.remaining)


class Y:
    def __init__(self, kod, j, rem):
        self.status_code, self._j, self.headers, self.text = kod, j, {"x-remaining-today": str(rem)}, json.dumps(j)

    def json(self):
        return self._j


@contextlib.contextmanager
def ag(F):
    o1, o2 = EC.requests.request, EC.requests.post
    EC.requests.request, EC.requests.post = F.request, F.post_
    try:
        yield
    finally:
        EC.requests.request, EC.requests.post = o1, o2


def api_(bozuk=False):
    s = Store(); s.bozuk = bozuk
    a = C.CanliOkur(s); a.pace = 0
    return a


def gruplar(n=1, sade=True):
    G = {g: [(f"{g.upper()}_{i}", str(9000000000 + 10 * k + i)) for i in range(1, n + 1)] for k, g in enumerate(C.GRUPLAR)
         if sade or g != "sade"}
    G["_kimliksiz"] = {}
    return G


def kur(F, G, yapilar=None):
    yapilar = yapilar or {"ornament": menu(5, pids=(513,)), "kupa": menu(8, 2, pids=(513, 516)), "sade": menu(8, 2, pids=(513, 516)),
                          "poster": menu(6, 5, 13), "yd": menu(5, 2, 14, pids=(513, 514, 516))}
    for g, L in G.items():
        if g.startswith("_"):
            continue
        for _, lid in L:
            F.INV[lid] = inv(yapilar[g])


def prob_kos(F, G, td):
    with ag(F), contextlib.redirect_stdout(io.StringIO()) as o:
        P = C.prob(api_(), "1", G, Path(td))
    return P, o.getvalue()


# ---------------------------------------------------------------- yazma yasagi (bilinen FAIL her yontemde)
def t_yazma_yasak():
    F = Sahte()
    with ag(F):
        a = api_()
        for m in ("POST", "PUT", "PATCH", "DELETE", "post"):
            dur(lambda: a._call(m, "/shops/1/listings/9000000001"), "YASAK")
        for ad, f in (("post_file", lambda: a.post_file("/shops/1/listings/9000000001/images", {"image": ("x", io.BytesIO(b"x"), "i")})),
                      ("put_json", lambda: a.put_json("/listings/9000000001/inventory", {})),
                      ("post_json", lambda: a.post_json("/shops/1/listings/9000000001/variation-images", {})),
                      ("delete", lambda: a.delete("/shops/1/listings/9000000001/images/1")),
                      ("patch", lambda: a.patch("/shops/1/listings/9000000001", {"state": "inactive"})),
                      ("put", lambda: a.put("/shops/1/listings/9000000001/properties/1", {})),
                      ("post", lambda: a.post("/shops/1/sections", {}))):
            m_ = dur(f, f"YASAK (salt okuma): {ad}")   # her katman kendi adiyla (ust katman sokulse alttaki yakalamasin)
            assert "9000000001" not in m_, f"{ad}: mesajda yol {m_}"
    assert F.istek == [] and F.post == 0, f"yazma istegi gitti {F.istek} {F.post}"
    with ag(F):
        assert api_().get("/shops/1") == {"shop_id": 1}, "bilinen PASS: GET gecer"


# ---------------------------------------------------------------- kota kapisi
def t_kota_prob():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar()
        F = Sahte(remaining=13); kur(F, G)       # magaza GET sonrasi kalan 12 < 3 + 10
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            dur(lambda: C.prob(api_(), "1", G, Path(td)), "DUR: kota")
        assert len(F.istek) == 1, f"kota DUR'unda okuma basladi {len(F.istek)}"
        F = Sahte(remaining=14); kur(F, G)       # kalan 13 = 3 + 10 -> PASS
        P, _ = prob_kos(F, G, td)
        assert P["istek"] == 3 and len(F.istek) == 3, f"prob tam 3 istek degil {P['istek']}"


def t_kota_olc():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar(2)
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        tah = C.tahmin(10, True, 2)
        F = Sahte(remaining=tah + 10); kur(F, G)  # magaza sonrasi kalan tah + 9
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            dur(lambda: C.olc(api_(), "1", G, Path(td), 2, P), "DUR: kota")
        assert len(F.istek) == 1
        F = Sahte(remaining=tah + 11); kur(F, G)
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            O = C.olc(api_(), "1", G, Path(td), 2, P)
        assert O["istek"] == tah == len(F.istek), f"senaryo 2 istek {O['istek']} tahmin {tah} gercek {len(F.istek)}"


def t_tahmin():
    assert C.tahmin(324, True, 1) == 8 and C.tahmin(324, True, 2) == 332 and C.tahmin(90, False, 1) == 2 and C.tahmin(100, False, 1) == 2
    assert C.tahmin(101, False, 1) == 3


# ---------------------------------------------------------------- menu ve urun sayimi
def t_menu_sayim():
    oz, n = C.env_ozet(inv(menu(6, 5, 13)))
    assert n is None and oz["menu_sayisi"] == 3 and oz["urun"] == 390 == oz["carpim"] and oz["tam_carpim"], oz
    assert C.yapi_etiketi(oz) == "3 menu 6x5x13"
    oz, _ = C.env_ozet(inv(menu(5, 2, 14, pids=(513, 514, 516))))
    assert oz["urun"] == 140 and C.yapi_etiketi(oz) == "3 menu 5x2x14", oz
    oz, _ = C.env_ozet(inv(menu(5, pids=(513,))))
    assert oz["menu_sayisi"] == 1 and oz["urun"] == 5
    oz, _ = C.env_ozet(inv(menu(6, 5, 13), eksik=10))        # bilinen FAIL: tam carpim degil
    assert oz["urun"] == 380 and oz["carpim"] == 390 and not oz["tam_carpim"], oz
    oz, _ = C.env_ozet(inv(menu(2, 3), acik=False))
    assert oz["acik"] == 0 and oz["kapali"] == 6 and oz["readiness_state_id"] == {"111": 6}


def t_beklenmeyen_sema():
    for bozuk, neden in (({}, "products yok"), ([], "envanter sozluk degil"), ({"products": [{"x": 1}]}, "urun bicimi"),
                         ({"products": [{"property_values": [{"a": 1}], "offerings": []}]}, "property_values"),
                         ({"products": [{"property_values": [{"property_id": [1], "values": ["a"]}], "offerings": [{"readiness_state_id": 1}]}]},
                          "beklenmeyen tur"),
                         ({"products": [{"property_values": [], "offerings": []}]}, "offering yok")):
        oz, n = C.env_ozet(bozuk)
        assert oz is None and neden in n, (bozuk, n)
    with tempfile.TemporaryDirectory() as td:
        G = gruplar(2)
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        F = Sahte(); kur(F, G); F.INV[G["kupa"][0][1]] = {}      # tek ilan bozuk -> olculemedi, kosu surer
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            O = C.olc(api_(), "1", G, Path(td), 1, P)
        assert O["ozet"]["kupa"]["olculemedi"] == 1 and O["ozet"]["poster"]["olculemedi"] == 0, O["ozet"]["kupa"]
        F = Sahte(); kur(F, G)
        for k in list(F.INV):
            F.INV[k] = {"urunler": []}                       # tum ilanlar beklenmeyen -> DUR, cikti yine yazilir
        (Path(td) / "OLCUM.json").unlink()
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            dur(lambda: C.olc(api_(), "1", G, Path(td), 1, P), "DUR: hicbir ilanin")
        assert (Path(td) / "OLCUM.json").exists()


def t_varyasyonsuz_ve_readiness():
    oz, n = C.env_ozet({"products": [{"property_values": [], "offerings": [{"is_enabled": True, "readiness_state_id": 5}]}]})
    assert n is None and oz["menu_sayisi"] == 0 and oz["carpim"] == 1 and oz["tam_carpim"], oz      # varyasyonsuz: 1 urun = carpim 1
    i = inv(menu(2, 3)); del i["products"][0]["offerings"][0]["readiness_state_id"]
    oz, n = C.env_ozet(i)
    assert n is None and oz["urun"] == 6 and oz["readiness_eksik_offering"] == 1 and oz["readiness_state_id"] == {"111": 5}, (n, oz)


def t_sema_derin():
    d = {"results": [{"a": 1}, {"b": {"c": [{"d": {"e": {"f": {"g": 1}}}}]}}]}
    S = C.sema(d)
    assert "results[].a" in S and "results[].b.c[].d.e.f.g" in S, sorted(S)          # 7 seviye + liste ogeleri birlesir
    assert S["results[].b.c[].d.e.f.g"] == {"int"}
    assert all("1" not in str(v) or v == {"int"} for v in S.values())


# ---------------------------------------------------------------- prob
def t_prob_envanter():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar()
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        assert P["batch_envanter"] == "EVET" and P["products_sema_ayni"] is True and all(P["gerekli_yol"].values()), P
        assert P["istenen"] == 5, P["istenen"]
        F = Sahte(batch_env=False); kur(F, G); P, _ = prob_kos(F, G, td)
        assert P["batch_envanter"] == "HAYIR" and P["products_sema_ayni"] is None, P
        G2 = gruplar(sade=False)
        F = Sahte(); kur(F, G2); P, _ = prob_kos(F, G2, td)
        assert P["istenen"] == 4
        F = Sahte(); kur(F, G)
        F.INV[G["poster"][0][1]] = {"products": [{"property_values": [{"x": 1}], "offerings": [{"y": 2}]}]}   # bilinen FAIL
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            dur(lambda: C.prob(api_(), "1", G, Path(td)), "FAIL: tek ilan envanterinde gerekli yol yok")




def t_prob_batch_hata_ve_kismi():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar()
        F = Sahte(); kur(F, G); F.hata = {r"^/listings/batch$": 400}                 # batch Inventory 400: olcum kaybolmaz
        P, o = prob_kos(F, G, td)
        assert P["batch_envanter"] == "HAYIR (batch hatasi)" and P["istek"] == 3 and P["sema_envanter"] and all(P["gerekli_yol"].values()), P
        assert json.loads((Path(td) / "OLCUM.json").read_text())["batch_hata"] and not re.search(r"900000\d{4}", o)
        F = Sahte(); kur(F, G)
        F.INV_YOK = {G["kupa"][0][1]}
        orj = F.ilan
        F.ilan = lambda lid, env: (lambda L: (L.pop("inventory", None), L)[1])(orj(lid, env)) if lid in F.INV_YOK else orj(lid, env)
        P, _ = prob_kos(F, G, td)
        assert P["batch_envanter"] == "KISMI" and P["grup_envanter"]["kupa"] is False and P["grup_envanter"]["poster"] is True, P
        F = Sahte(); kur(F, G)
        for _, lid in G["kupa"]:
            F.INV[lid]["products"][0]["property_values"][0]["scale_id"] = None     # baska grupta tur farki: poster kiyasini bozmaz
        P, _ = prob_kos(F, G, td)
        assert P["products_sema_ayni"] is True, P["yalniz_batch"]


def t_olc_yinelenen_ve_tanim():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar(2)
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        G["sade"] = [G["sade"][0], ("TEKRAR", G["kupa"][0][1])]                     # yinelenen kimlik: tek GET
        F = Sahte(); kur(F, G); F.tanim_count = 5
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            O = C.olc(api_(), "1", G, Path(td), 2, P)
        assert O["yinelenen_kimlik"] == 1 and O["istek"] == O["tahmin"] == len(F.istek), (O["istek"], O["tahmin"])
        assert len(O["uyarilar"]) == 3 and "sayfalama" in O["uyarilar"][0], O["uyarilar"]
        F = Sahte(); kur(F, G); F.hata = {rf"/listings/{G['kupa'][0][1]}/inventory": 404}      # ilk GET hatasi ikinci kayda da
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            O = C.olc(api_(), "1", G, Path(td), 2, P)
        n = [s.get("olculemedi", "") for s in O["ilanlar"] if s["listing_id"] == G["kupa"][0][1]]
        assert len(n) == 2 and all(x.startswith("GET hatasi") for x in n), n


def t_kosu_geneli_hata_yukari_ve_cikti():
    """Kota / 429 / token / iptal ilan hatasi sayilmaz, yukari gider; OLCUM.json her durumda (yeni klasorde) yazilir."""
    with tempfile.TemporaryDirectory() as t0:
        G = gruplar(3)
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, t0)
        lid = G["kupa"][1][1]
        for ad, h, tur, metin, bozuk in (("429 gunluk kota", (429, {"retry-after": "3600"}), SystemExit, "HATA: 429", False),
                                          ("token yenileme", 401, SystemExit, "token yenileme", True),
                                          ("iptal", KeyboardInterrupt(), KeyboardInterrupt, "kupa #2", False)):
            with tempfile.TemporaryDirectory() as td:
                F = Sahte(); kur(F, G); F.hata = {rf"/listings/{lid}/inventory": h}
                with ag(F), contextlib.redirect_stdout(io.StringIO()):
                    try:
                        C.olc(api_(bozuk), "1", G, Path(td), 2, P)
                        raise AssertionError(f"{ad}: kosu durmali")
                    except tur as e:
                        m_ = str(e.code if isinstance(e, SystemExit) else e)
                assert metin in m_ and lid not in m_, f"{ad}: {m_}"
                O = json.loads((Path(td) / "OLCUM.json").read_text())
                assert O["istek"] < C.tahmin(15, True, 2) and len(O["ilanlar"]) < 15, f"{ad}: kosu durmadi {O['istek']}"
        with tempfile.TemporaryDirectory() as td:                    # prob: batch 429 yukari, cikti yazilir
            F = Sahte(); kur(F, G); F.hata = {r"^/listings/batch$": (429, {"retry-after": "3600"})}
            with ag(F), contextlib.redirect_stdout(io.StringIO()):
                dur(lambda: C.prob(api_(), "1", G, Path(td)), "HATA: 429")
            assert json.loads((Path(td) / "OLCUM.json").read_text())["mod"] == "prob"
        with tempfile.TemporaryDirectory() as td:                    # prob: poster GET hatasi; batch karari kayitli
            F = Sahte(); kur(F, G); F.hata = {rf"^/listings/{G['poster'][0][1]}/inventory$": 404}
            with ag(F), contextlib.redirect_stdout(io.StringIO()):
                dur(lambda: C.prob(api_(), "1", G, Path(td)), "HATA")
            assert json.loads((Path(td) / "OLCUM.json").read_text())["batch_envanter"] == "EVET"


def t_olc_fail_prob_red():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar()
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        for bozuk in (dict(P, gerekli_yol={k: False for k in C.GEREKLI_YOL}), {k: v for k, v in P.items() if k != "gerekli_yol"}):
            with ag(F), contextlib.redirect_stdout(io.StringIO()):
                dur(lambda: C.olc(api_(), "1", G, Path(td), 1, bozuk), "--prob basarili degil")
        assert len(F.istek) == 3, "FAIL prob ile olc istek gondermemeli"


def t_olc_senaryo1():
    with tempfile.TemporaryDirectory() as td:
        G = gruplar(3)
        F = Sahte(); kur(F, G); P, _ = prob_kos(F, G, td)
        F = Sahte(); kur(F, G)
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            O = C.olc(api_(), "1", G, Path(td), 1, P)
        tah = C.tahmin(15, True, 1)
        assert O["istek"] == tah == len(F.istek) and not any("/inventory" in y for _, y in F.istek), (O["istek"], tah)
        assert O["ozet"]["poster"]["yapi"] == {"3 menu 6x5x13": 3} and O["ozet"]["yd"]["urun_max"] == 140, O["ozet"]["poster"]
        assert O["ozet"]["ornament"]["yapi"] == {"1 menu 5": 3} and O["magaza"], O["ozet"]["ornament"]


def t_senaryo_zorunlu():
    with tempfile.TemporaryDirectory() as td:
        dur(lambda: C.main(["--mod", "olc", "--gruplar", "poster", "--poster", "x.csv", "--out", td]), "--senaryo 1|2 ve --prob zorunlu")
        dur(lambda: C.main(["--mod", "olc", "--senaryo", "1", "--gruplar", "poster", "--poster", "x.csv", "--out", td]), "--prob zorunlu")
        dur(lambda: C.main(["--mod", "prob", "--gruplar", "poster,bilinmeyen", "--out", td]), "--gruplar yalniz")
        G = gruplar()
        F = Sahte(batch_env=False); kur(F, G); P, _ = prob_kos(F, G, td)
        with ag(F), contextlib.redirect_stdout(io.StringIO()):
            dur(lambda: C.olc(api_(), "1", G, Path(td), 1, P), "senaryo 1 icin prob batch envanter EVET")
            dur(lambda: C.olc(api_(), "1", G, Path(td), 2, {"mod": "olc"}), "gecerli bir prob")


# ---------------------------------------------------------------- gizlilik: kimlik log / mesaj / SAYIM / OZET'e cikmaz
def t_gizlilik():
    rx = re.compile(r"900000\d{4}")
    with tempfile.TemporaryDirectory() as td:
        G = gruplar(3)
        F = Sahte(); kur(F, G); P, o1 = prob_kos(F, G, td)
        F = Sahte(); kur(F, G)
        with ag(F), contextlib.redirect_stdout(io.StringIO()) as o:
            C.olc(api_(), "1", G, Path(td), 2, P)
        for ad, metin in (("prob log", o1), ("olc log", o.getvalue()), ("SAYIM", (Path(td) / "SAYIM.txt").read_text()),
                          ("OZET", (Path(td) / "OZET.md").read_text())):
            assert not rx.search(metin), f"{ad}: kimlik sizdi {rx.search(metin).group(0)}"
        assert rx.search((Path(td) / "OLCUM.json").read_text()), "bilinen PASS: kimlik yalniz OLCUM.json'da"
        lid = G["poster"][1][1]
        for h in (EC.requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: /v3/application/listings/{lid}/inventory"),
                  404, 500):                                       # ilan GET hatasi: kosu surer, ilan olculemedi (maskeli neden)
            F = Sahte(); kur(F, G); F.hata = {rf"/listings/{lid}/inventory": h}
            with ag(F), contextlib.redirect_stdout(io.StringIO()) as o:
                O = C.olc(api_(), "1", G, Path(td), 2, P)
            s = [x for x in O["ilanlar"] if x["listing_id"] == lid][0]
            assert s["olculemedi"].startswith("GET hatasi: poster #2") and lid not in s["olculemedi"] and "<id>" in s["olculemedi"], s
            assert not rx.search(o.getvalue()) and not rx.search((Path(td) / "OZET.md").read_text()), f"{h}: logda / OZET'te kimlik"
        F = Sahte(); kur(F, G)
        F.hata = {r"^/listings/batch$": EC.requests.ConnectionError(f"Max retries exceeded with url: /v3/application/listings/batch?listing_ids={lid}")}
        with ag(F), contextlib.redirect_stdout(io.StringIO()) as o:
            try:
                C.olc(api_(), "1", G, Path(td), 2, P)
                raise AssertionError("batch hatasi bekleniyordu")
            except RuntimeError as e:
                m_ = str(e)
        assert m_.startswith("batch 1: ConnectionError") and lid not in m_ and "<id>" in m_, m_
        assert not rx.search(o.getvalue()) and (Path(td) / "OLCUM.json").exists(), "batch hatasinda cikti yazilmali, logda kimlik yok"


def t_liste():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        C78 = {f"C{i}": str(9000000100 + i) for i in range(78)}
        (d / "o.json").write_text(json.dumps({"ciftler": dict(C78, X_Y="BELIRSIZ"), "tamam": []}))
        r = C.liste_oku("ornament", d / "o.json"); assert len(r[0]) == 78 and r[1] == 1, r[1]
        (d / "o2.json").write_text(json.dumps({"ciftler": dict(list(C78.items())[:77], X_Y="BELIRSIZ")}))
        dur(lambda: C.liste_oku("ornament", d / "o2.json"), "77 gecerli kimlik (beklenen en az 78)")     # bilinen FAIL: eksik liste
        B11 = {f"B{i}": 9000000200 + i for i in range(11)}
        (d / "s.json").write_text(json.dumps({"burclar": B11, "tamam": [], "yayin": {}}))          # gorev-g sade_taslak.py:414, :451
        r = C.liste_oku("sade", d / "s.json"); assert len(r[0]) == 11 and r[1] == 0
        (d / "s10.json").write_text(json.dumps({"burclar": dict(list(B11.items())[:10])}))
        dur(lambda: C.liste_oku("sade", d / "s10.json"), "10 gecerli kimlik (beklenen en az 11)")
        (d / "s2.json").write_text(json.dumps(B11))                                                  # bilinen FAIL: anahtarsiz bicim
        dur(lambda: C.liste_oku("sade", d / "s2.json"), "burclar sozlugu yok")
        (d / "s3.json").write_text(json.dumps({"ciftler": B11}))
        dur(lambda: C.liste_oku("sade", d / "s3.json"), "burclar sozlugu yok")
        with open(d / "k.csv", "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["cift", "listing_id"])
            for k, v in C78.items():
                w.writerow([k, v])
            w.writerow(["C_D", ""])
        r = C.liste_oku("kupa", d / "k.csv"); assert len(r[0]) == 78 and r[1] == 1
        (d / "b.csv").write_text("x,y\n1,2\n")
        dur(lambda: C.liste_oku("kupa", d / "b.csv"), "sutunlari")
        m_ = dur(lambda: C.liste_oku("kupa", d / "yok.csv"), "listesi yok")
        assert td not in m_
        dur(lambda: C.liste_oku("kupa", d / "o.json"), "json beklenmiyor")
        for g, f in (("poster", "pod78_ids.csv"), ("yd", "yd78_ids.csv")):
            r = C.liste_oku(g, Path(__file__).resolve().parents[2] / "data" / "pod" / f)
            assert len(r[0]) == 78 and r[1] == 0


for _f in (t_prob_envanter, t_menu_sayim, t_beklenmeyen_sema, t_olc_senaryo1):   # sahte envanter semasina dayanir
    _f.__name__ += ZAYIF
for ad, f in list(globals().items()):
    if ad.startswith("t_") and callable(f):
        t(f.__name__, f)
for ad, s, m in SONUC:
    print(f"{s} {ad} {m}")
fail = sum(1 for x in SONUC if x[1] == "FAIL")
print(f"TOPLAM {len(SONUC)} | PASS {len(SONUC) - fail} | FAIL {fail}")
sys.exit(1 if fail else 0)
