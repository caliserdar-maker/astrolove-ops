#!/usr/bin/env python3
"""yayina_hazir.py testleri (ag yok). Her kontrol bilinen PASS + bilinen FAIL ile (CLAUDE.md kalite kurali 3).
Birim: kontrol_et / siniflandir / gorsel_kontrol / ru_bul / md / ilan_listesi / alan_turleri.
Uctan uca: main() GERCEK Etsy istemcisi (etsy_common.Etsy._call + SaltOkur kota tabani) uzerinden kosar; yalniz ag katmani
(etsy_common.requests.request) ve token dosyasi sahte. Sahte yanit yapisi: batch translations dict {dil: ceviri}
(emsal beyan_marka_yaz.ru_ceviri, marka_tara.py), properties results listesi (ornament_ru_olcu olcumu 42468292187).
NOT: mod=olc gercek Etsy kosusundan sonra sabit ornek (OLCUM.json) bu teste eklenecek; o zamana kadar yanit yapisi varsayimdir."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common  # noqa: E402
import yayina_hazir as y  # noqa: E402

SPEC = y.spec_yukle(str(y.KOK / "docs/ornament/ORN_YAYIN_SPEC.json"))
RU = y.ru_csv(SPEC)
ALT_F = y.alt_kaynak(SPEC)
B = SPEC["beklenen"]
KOD = "CANCER_LIBRA"
ALT = ALT_F(KOD)[0]


def ilan(kod=KOD, lid=4611501158, state="draft"):
    alt = ALT_F(kod)[0]
    return {"listing_id": lid, "state": state, "shipping_profile_id": B["shipping_profile_id"],
            "production_partners": [{"production_partner_id": 77, "partner_name": "Printful Latvia"}],
            "price": {"amount": 1990, "divisor": 100}, "description": "intro\n" + B["aciklama_zorunlu"][0] + "\nend",
            "images": [{"rank": i + 1, "alt_text": alt[i]} for i in range(14)], "videos": [{"video_id": 1}],
            "translations": {"ru": {"language": "ru", "title": RU[kod]["baslik_ru"], "description": RU[kod]["aciklama_ru"]}}}


PROPS = [{"property_id": o["property_id"], "values": o["values"], "scale_id": o["scale_id"]} for o in B["nitelikler"]]


def sinif(L, props=PROPS, spec=SPEC, ru=RU, kod=KOD):
    S = y.kontrol_et(spec, kod, L, ru, props, ALT_F)
    return y.siniflandir(L, S)


def birim():
    n = 0
    s, k = sinif(ilan()); assert s == "YAYINA HAZIR" and not k, (s, k); n += 1
    L = ilan(); L["state"] = "active"; assert sinif(L) == ("YAYINDA", {}); n += 1
    L = ilan(); L["state"] = "inactive"; assert sinif(L)[0] == "DURUM inactive"; n += 1
    for alan, deger, ad in (("shipping_profile_id", 319194887351, "kargo profili"),
                            ("production_partners", [{"production_partner_id": 5817638, "partner_name": "Prodigi"}], "uretim ortagi"),
                            ("production_partners", [], "uretim ortagi"),
                            ("price", {"amount": 2990, "divisor": 100}, "fiyat"),
                            ("videos", [], "video")):
        L = ilan(); L[alan] = deger
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and ad in k and k[ad].startswith("FAIL"), (alan, s, k); n += 1
    sp = copy.deepcopy(SPEC); sp["beklenen"]["uretim_ortagi_id"] = 99           # ad dogru, id farkli -> FAIL
    assert "uretim ortagi" in sinif(ilan(), spec=sp)[1]; n += 1
    sp["beklenen"]["uretim_ortagi_id"] = 77; assert sinif(ilan(), spec=sp)[0] == "YAYINA HAZIR"; n += 1
    # aciklama
    L = ilan(); L["description"] = "with Free Shipping " + L["description"]
    assert sinif(L)[1].get("aciklama yasak: free shipping") == "FAIL: var"; n += 1
    L = ilan(); L["description"] = "Made and shipped by our production partner, with free shipping."
    assert any(x.startswith("aciklama zorunlu") for x in sinif(L)[1]); n += 1
    L = ilan(); L["description"] = L["description"].replace(". You", ".  You")          # bosluk farki norm ile PASS
    assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    L = ilan(); del L["description"]; assert sinif(L)[1].get("aciklama", "").startswith("olculemedi"); n += 1   # eskiden PASS'ti
    # gorsel: sayi, rank, sira (alt metin tam)
    L = ilan(); L["images"] = L["images"][:13]; assert sinif(L)[1]["gorsel"].startswith("FAIL"); n += 1
    L = ilan(); L["images"][3]["rank"] = 3; assert "tekrarli" in sinif(L)[1]["gorsel"]; n += 1
    L = ilan(); L["images"][3]["rank"] = None; assert "eksik" in sinif(L)[1]["gorsel"]; n += 1
    L = ilan(); L["images"][1]["alt_text"] = "tree"; assert "sira [2]" in sinif(L)[1]["gorsel"]; n += 1
    L = ilan(); L["images"][11]["alt_text"], L["images"][13]["alt_text"] = ALT[13], ALT[11]      # Ivory 12. sirada (8 Kas olgusu)
    assert "sira [12, 14]" in sinif(L)[1]["gorsel"]; n += 1
    L = ilan(); L["images"][3]["alt_text"], L["images"][4]["alt_text"] = ALT[4], ALT[3]          # 4 stiller / 5 eller (8 Kas olgusu)
    assert sinif(L)[1]["gorsel"].startswith("FAIL"); n += 1
    L = ilan(); L["images"].reverse(); assert sinif(L)[0] == "YAYINA HAZIR"; n += 1               # yanit sirasi degil rank esas
    L = ilan(); [x.update(rank=x["rank"] + 1) for x in L["images"]]                              # rank 2-15, icerik sirasi dogru:
    assert sinif(L)[0] == "YAYINA HAZIR"; n += 1   # Serdar 8 Kas gevsetme: "tekrarsiz ve kesin artan" kabul (ARIES_ARIES 2-6)
    L = ilan(); L["images"][0]["alt_text"] = ALT[0] + "  "; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    L = ilan(kod="ARIES_ARIES"); assert sinif(L, kod="ARIES_ARIES")[0] == "YAYINA HAZIR"; n += 1
    assert sinif(ilan(), kod="ARIES_ARIES")[1]["gorsel"].startswith("FAIL"); n += 1           # baska ciftin alt metni
    S = y.kontrol_et(SPEC, "YOK_YOK", ilan(), RU, PROPS, ALT_F)                                # kaynak yok -> olculemedi, PASS degil
    assert S["gorsel"].startswith("olculemedi") and S["RU"] == "FAIL: RU CSV'de kod yok"; n += 1
    sp = copy.deepcopy(SPEC); del sp["alt_metin_kaynagi"]                                      # yedek yol: yalniz 2. gorsel
    assert y.kontrol_et(sp, KOD, ilan(), RU, PROPS, None)["gorsel"] == "PASS"; n += 1
    L = ilan(); L["images"][1]["alt_text"] = "tree"
    assert y.kontrol_et(sp, KOD, L, RU, PROPS, None)["gorsel"].startswith("FAIL"); n += 1
    # RU
    L = ilan(); L["translations"] = {}; assert sinif(L)[1].get("RU") == "FAIL: RU yok"; n += 1
    L = ilan(); L["translations"]["ru"]["description"] += " x"; assert sinif(L)[1].get("RU") == "FAIL: RU farkli"; n += 1
    L = ilan(); L["translations"] = [L["translations"]["ru"]]; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1     # liste bicimi
    L = ilan(); L["translations"] = {"x": L["translations"]["ru"]}; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1  # dil anahtarsiz dict
    L = ilan(); L["translations"] = {"de": {"language": "de", "title": "t", "description": "d"}}
    assert sinif(L)[1].get("RU") == "FAIL: RU yok"; n += 1
    # nitelik
    p = copy.deepcopy(PROPS); p[2]["values"] = ["0.2"]; assert "nitelik Depth" in sinif(ilan(), p)[1]; n += 1
    p = copy.deepcopy(PROPS); p[0]["values"] = [2.99]; assert sinif(ilan(), p)[0] == "YAYINA HAZIR"; n += 1
    p = copy.deepcopy(PROPS); p[1]["scale_id"] = 7; assert "nitelik Height" in sinif(ilan(), p)[1]; n += 1
    assert sinif(ilan(), PROPS[:2])[1].get("nitelik Depth") == "FAIL: yok"; n += 1
    s, k = sinif(ilan(), None); assert s == "HENUZ YAYINLAMAYIN" and k["nitelik"].startswith("olculemedi"), (s, k); n += 1  # YUKSEK bulgu
    # alan yok -> olculemedi
    for alan, ad in (("shipping_profile_id", "kargo profili"), ("production_partners", "uretim ortagi"), ("images", "gorsel"),
                     ("videos", "video"), ("translations", "RU"), ("price", "fiyat")):
        L = ilan(); del L[alan]
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and k[ad].startswith("olculemedi"), (alan, s, k); n += 1
    L = ilan(); L["state"] = "active"; L["shipping_profile_id"] = 1; assert sinif(L)[0] == "YAYINDA (EKSIK VAR)"; n += 1
    # rapor ve liste
    R = {"ilanlar": {KOD: {"listing_id": 1, "sinif": "YAYINA HAZIR", "eksik": {}},
                     "X_Y": {"listing_id": None, "sinif": "DURUM okunamadi", "eksik": {"okuma": "listing id yok"}}},
         "zaman": "t", "kota_bas": 1, "kota_son": 1, "cagri": 2, "yarim": "DUR: kota 9 < 10"}
    m = y.md(R, SPEC)
    assert "listing-editor/edit/1" in m and "Toplam 2" in m and "Kontrol EDİLMEYEN: stil" in m and "YARIM" in m and "X_Y" in m; n += 1
    ids, kotu = y.ilan_listesi({"A": {"listing_id": 5}, "B": {"hata": "listing id yok (None)"}, "C": "x"})
    assert ids == {"A": 5} and sorted(kotu) == ["B", "C"]; n += 1
    T = y.alan_turleri({"images": [{"rank": 1, "alt_text": "a"}], "translations": {"ru": {"title": "t"}}, "price": {"amount": 1}})
    assert T["images[0].rank"] == "int" and T["translations.ru.title"] == "str" and T["price.amount"] == "int", T; n += 1
    so = y.SaltOkur.__new__(y.SaltOkur)
    for met in ("PUT", "PATCH", "POST", "DELETE"):
        try:
            so._call(met, "/x"); raise AssertionError("yazma gecti")
        except SystemExit as e:
            assert "salt okuma" in str(e.code); n += 1
    return n


# ------------------------------------------------------------------ uctan uca (gercek istemci, sahte ag)
class Yanit:
    def __init__(self, kod, j, kalan):
        self.status_code, self._j, self.headers, self.text = kod, j, {"x-remaining-today": str(kalan)}, json.dumps(j)[:300]

    def json(self):
        return self._j


class SahteAg:
    def __init__(self, ilanlar, kalan, adim=1):
        self.ilanlar, self.kalan, self.istek, self.adim = ilanlar, kalan, [], adim   # adim 2: paralel baska kosu kota yiyor

    def __call__(self, method, url, params=None, **kw):
        assert method == "GET", method
        self.istek.append((url.split("/v3/application")[-1], dict(params or {})))
        self.kalan -= self.adim
        path = url.split("/v3/application")[-1]
        if path.startswith("/shops/") and path.endswith("/properties"):
            return Yanit(200, {"count": 3, "results": copy.deepcopy(PROPS)}, self.kalan)
        if path == "/listings/batch":
            ids = [int(x) for x in params["listing_ids"].split(",")]
            assert params["includes"] == "Images,Videos,Translations"
            return Yanit(200, {"count": len(ids), "results": [copy.deepcopy(self.ilanlar[i]) for i in ids if i in self.ilanlar]}, self.kalan)
        if path.startswith("/shops/"):
            return Yanit(200, {"shop_id": 1}, self.kalan)
        return Yanit(404, {"error": path}, self.kalan)


class SahteStore:
    api_key_header = "k:s"
    access_token = "t"

    def __init__(self, *a):
        pass

    def needs_refresh(self):
        return False


def kos(ilanlar_json, ag, *ek):
    d = Path(tempfile.mkdtemp())
    (d / "I.json").write_text(json.dumps(ilanlar_json))
    eski = (etsy_common.requests.request, y.TokenStore, sys.argv, dict(os.environ))
    etsy_common.requests.request, y.TokenStore = ag, SahteStore
    os.environ.update(TOKEN_FILE="x", ETSY_API_KEY="k", ETSY_SHARED_SECRET="s", ETSY_SHOP_ID="39729443")
    sys.argv = ["yayina_hazir.py", "--spec", str(y.KOK / "docs/ornament/ORN_YAYIN_SPEC.json"), "--ilanlar", str(d / "I.json"),
                "--out", str(d / "o"), *ek]
    hata = None
    try:
        y.main()
    except SystemExit as e:
        hata = str(e.code)
    finally:
        etsy_common.requests.request, y.TokenStore, sys.argv = eski[0], eski[1], eski[2]
        os.environ.clear(); os.environ.update(eski[3])
    R = json.loads((d / "o/YAYINA_HAZIR.json").read_text()) if (d / "o/YAYINA_HAZIR.json").exists() else None
    return hata, R, d


def uctan_uca():
    n = 0
    a, b = ilan(), ilan(kod="ARIES_ARIES", lid=4611500001, state="active")
    b["shipping_profile_id"] = 319194887351
    I = {KOD: {"listing_id": a["listing_id"]}, "ARIES_ARIES": {"listing_id": b["listing_id"]}, "LEO_LEO": {"hata": "listing id yok (None)"}}
    ag = SahteAg({a["listing_id"]: a, b["listing_id"]: b}, 500)
    hata, R, _ = kos(I, ag, "--mod", "kontrol")
    assert hata is None, hata
    s = {k: v["sinif"] for k, v in R["ilanlar"].items()}
    assert s == {KOD: "YAYINA HAZIR", "ARIES_ARIES": "YAYINDA (EKSIK VAR)", "LEO_LEO": "DURUM okunamadi"}, s; n += 1
    assert R["cagri"] == 4 and len(ag.istek) == 4, (R["cagri"], ag.istek); n += 1       # shop + batch + 2 nitelik
    ag = SahteAg({a["listing_id"]: a}, 500)
    hata, R, _ = kos({KOD: {"listing_id": a["listing_id"]}}, ag, "--mod", "kontrol", "--nitelik-yok")
    assert R["ilanlar"][KOD]["sinif"] == "HENUZ YAYINLAMAYIN" and len(ag.istek) == 2; n += 1   # nitelik kapali PASS uretmez
    ag = SahteAg({a["listing_id"]: a, b["listing_id"]: b}, 13)                                     # 12 kalir; tahmin 3 + 10 > 12
    hata, R, _ = kos(I, ag, "--mod", "kontrol")
    assert hata and "okuma baslamadi" in hata and len(ag.istek) == 1 and R is None, (hata, ag.istek); n += 1
    many = {}
    I2 = {}
    for i in range(30):
        x = ilan(); x["listing_id"] = 4611600000 + i; many[x["listing_id"]] = x; I2[f"{KOD}_{i:02d}"] = {"listing_id": x["listing_id"]}
    ag = SahteAg(many, 52, adim=2)    # baslangic kapisi gecer (50 >= 31 + 10); baska kosu da yedigi icin istek ortasinda taban 10'a iner
    hata, R, d = kos(I2, ag, "--mod", "kontrol")
    assert hata and "kota" in hata and R and R.get("yarim") and 0 < len(R["ilanlar"]) < 30, (hata, R and len(R["ilanlar"])); n += 1
    assert "YARIM" in (d / "o/YAYINA_HAZIR.md").read_text(); n += 1
    ag = SahteAg({a["listing_id"]: a, b["listing_id"]: b}, 500)
    hata, _, d = kos(I, ag, "--mod", "olc")
    O = json.loads((d / "o/OLCUM.json").read_text())
    assert hata is None and len(ag.istek) == 4 and O["ARIES_ARIES"]["_ornek"]["translations_anahtar"] == ["ru"], (hata, ag.istek); n += 1
    assert "images[0].alt_text" in O[KOD]["batch_alanlar"] and "[0].scale_id" in O[KOD]["properties_alanlar"]; n += 1
    return n


if __name__ == "__main__":
    n1 = birim()
    n2 = uctan_uca()
    print(f"test_yayina_hazir: {n1 + n2}/{n1 + n2} PASS (birim {n1}, uctan uca {n2})")
