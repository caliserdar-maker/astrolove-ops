#!/usr/bin/env python3
"""yayina_hazir.py testleri (ag yok). Her kontrol bilinen PASS + bilinen FAIL ile (CLAUDE.md kalite kurali 3).
Birim: spec_yukle / kontrol_et / siniflandir / gorsel_kontrol / video_kontrol / ru_bul / eski_idler / md / ilan_listesi / alan_turleri.
Uctan uca: main() GERCEK Etsy istemcisi (etsy_common.Etsy._call + SaltOkur kota tabani) uzerinden kosar; yalniz ag katmani
(etsy_common.requests.request) ve token dosyasi sahte. Sahte yanit yapisi: batch translations dict {dil: ceviri}
(emsal beyan_marka_yaz.ru_ceviri, marka_tara.py), properties results listesi (ornament_ru_olcu olcumu 42468292187),
production-partners (id, partner_name, location; emsal kupa_taslak.py:204).
NOT: mod=olc gercek Etsy kosusundan sonra sabit ornek (OLCUM.json) bu teste eklenecek; o zamana kadar yanit yapisi varsayimdir."""
import contextlib
import copy
import io
import json
import os
import signal
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common  # noqa: E402
import yayina_hazir as y  # noqa: E402

SPEC_YOL = y.KOK / "docs/ornament/ORN_YAYIN_SPEC.json"
SPEC = y.spec_yukle(str(SPEC_YOL))
RU = y.ru_csv(SPEC)
ALT_F = y.alt_kaynak(SPEC)
B = SPEC["beklenen"]
KOD = "CANCER_LIBRA"
ALT = ALT_F(KOD)[0]
ORTAK = 77
ESKI = ({str(101 + i) for i in range(11)}, {"900"})   # eski 11 gorsel id'si, eski video id'si (YEDEK9 yapisi: 11 gorsel, 1 video)


def ilan(kod=KOD, lid=4611501158, state="draft"):
    alt = ALT_F(kod)[0]
    return {"listing_id": lid, "state": state, "shipping_profile_id": B["shipping_profile_id"], "is_personalizable": True,
            "production_partners": [{"production_partner_id": ORTAK, "partner_name": "Printful Latvia", "location": "Latvia"}],
            "price": {"amount": 1990, "divisor": 100, "currency_code": "USD"}, "title": "Zodiac Couple Ornament", "tags": ["ornament"],
            "description": "intro\n\n[ SHIPPING ]\nMade and shipped by our production partner. You can see the shipping cost and "
                           "estimated delivery time for your country on this page and at checkout.\n\n[ RETURNS ]\nend",
            "images": [{"listing_image_id": 5000 + i, "rank": i + 1, "alt_text": alt[i]} for i in range(14)],
            "videos": [{"video_id": 7000, "video_state": "active"}],
            "translations": {"ru": {"language": "ru", "title": RU[kod]["baslik_ru"], "description": RU[kod]["aciklama_ru"]}}}


PROPS = [{"property_id": o["property_id"], "values": o["values"], "scale_id": o["scale_id"]} for o in B["nitelikler"]]


def sinif(L, props=PROPS, spec=SPEC, ru=RU, kod=KOD, eski=ESKI, ortak=ORTAK):
    S = y.kontrol_et(spec, kod, L, ru, props, ALT_F if spec.get("alt_metin_kaynagi") else None, eski, ortak)
    return y.siniflandir(L, S)


def spec_dene(degistir):
    s = json.loads(SPEC_YOL.read_text())
    degistir(s)
    p = Path(tempfile.mkdtemp()) / "S.json"; p.write_text(json.dumps(s))
    try:
        y.spec_yukle(str(p)); return None
    except SystemExit as e:
        return str(e.code)


def birim():
    n = 0
    s, k = sinif(ilan()); assert s == "YAYINA HAZIR" and not k, (s, k); n += 1
    L = ilan(); L["state"] = "active"; assert sinif(L) == ("YAYINDA", {}); n += 1
    L = ilan(); L["state"] = "inactive"; assert sinif(L)[0] == "DURUM inactive"; n += 1
    for alan, deger, ad in (("shipping_profile_id", 319194887351, "kargo profili"),
                            ("shipping_profile_id", "abc", "kargo profili"),
                            ("production_partners", [{"production_partner_id": 5817638, "partner_name": "Prodigi"}], "uretim ortagi"),
                            ("production_partners", [], "uretim ortagi"),
                            ("price", {"amount": 2990, "divisor": 100}, "fiyat"),
                            ("is_personalizable", False, "kisisellestirme"),
                            ("videos", [], "video")):
        L = ilan(); L[alan] = deger
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and ad in k and k[ad].startswith("FAIL"), (alan, s, k); n += 1
    L = ilan(); L["production_partners"][0]["production_partner_id"] = 99                     # ad dogru, magazadaki id degil
    assert sinif(L)[1]["uretim ortagi"].startswith("FAIL"); n += 1
    assert sinif(ilan(), ortak=None)[1]["uretim ortagi"].startswith("FAIL"); n += 1           # magaza id'si yok -> PASS olmaz
    sp = copy.deepcopy(SPEC); sp["beklenen"]["uretim_ortagi_id"] = 99
    assert "uretim ortagi" in sinif(ilan(), spec=sp)[1]; n += 1
    sp["beklenen"]["uretim_ortagi_id"] = ORTAK; assert sinif(ilan(), spec=sp)[0] == "YAYINA HAZIR"; n += 1
    # metin: yasak desen baslik / aciklama / etiket, zorunlu cumle ve [ SHIPPING ] basligi
    for alan, deger in (("description", "with Free  Shipping "), ("title", "Ornament ships free "), ("tags", ["free delivery"])):
        L = ilan(); L[alan] = (deger + L[alan]) if isinstance(deger, str) else deger
        k = sinif(L)[1]; assert any(x.startswith("yasak") and v.startswith("FAIL") for x, v in k.items()), (alan, k); n += 1
    L = ilan(); L["tags"] = ["gift ornament free", "shipping ornament"]; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1   # etiket ucu
    L = ilan(); L["is_personalizable"] = "false"; assert sinif(L)[1]["kisisellestirme"].startswith("olculemedi"); n += 1
    L = ilan(); L["description"] = L["description"].replace("[ SHIPPING ]\n", "")
    assert any(x.startswith("aciklama zorunlu") for x in sinif(L)[1]); n += 1
    L = ilan(); L["description"] = "Made and shipped by our production partner, with free shipping."
    k = sinif(L)[1]; assert any(x.startswith("aciklama zorunlu") for x in k) and any(x.startswith("yasak") for x in k); n += 1
    L = ilan(); L["description"] = L["description"].replace(". You", ".  You")
    assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    for alan in ("description", "title", "tags"):
        L = ilan(); del L[alan]; assert sinif(L)[1].get("metin", "").startswith("olculemedi"), alan; n += 1
    # gorsel: sayi, rank, sira (alt metin tam), eski gorsel
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
    L = ilan(); L["images"][0]["listing_image_id"] = 101                                        # eski kapak (alt metni ayni)
    assert "eski gorsel" in sinif(L)[1]["gorsel"]; n += 1
    L = ilan(); del L["images"][0]["listing_image_id"]; assert sinif(L)[1]["gorsel"].startswith("olculemedi"); n += 1
    assert sinif(ilan(), eski=None)[1]["eski medya"].startswith("olculemedi"); n += 1          # SPEC eski_medya, kayit yok
    Y_ = SPEC["eski_medya"]
    assert y.eski_idler({"gorsel": [], "video": []}, Y_) is None; n += 1                       # bos liste yanlis PASS vermez
    assert y.eski_idler({"gorsel": [{"id": i} for i in range(10)], "video": [{"id": 1}]}, Y_) is None; n += 1
    assert y.eski_idler({"gorsel": [{"id": i} for i in range(11)], "video": [{"id": 1}]}, Y_) is not None; n += 1
    L = ilan(kod="ARIES_ARIES"); assert sinif(L, kod="ARIES_ARIES")[0] == "YAYINA HAZIR"; n += 1
    assert sinif(ilan(), kod="ARIES_ARIES")[1]["gorsel"].startswith("FAIL"); n += 1           # baska ciftin alt metni
    S = y.kontrol_et(SPEC, "YOK_YOK", ilan(), RU, PROPS, ALT_F, ESKI, ORTAK)                     # kaynak yok -> olculemedi
    assert S["gorsel"].startswith("olculemedi") and S["RU"] == "FAIL: RU CSV'de kod yok"; n += 1
    # video: sayi, durum, eski video
    L = ilan(); L["videos"][0]["video_id"] = 900; assert sinif(L)[1]["video"] == "FAIL: eski video"; n += 1
    L = ilan(); L["videos"][0]["video_state"] = "inactive"; assert "video_state" in sinif(L)[1]["video"]; n += 1
    L = ilan(); del L["videos"][0]["video_state"]; assert sinif(L)[1]["video"].startswith("olculemedi"); n += 1
    # RU
    L = ilan(); L["translations"] = {}; assert sinif(L)[1].get("RU") == "FAIL: RU yok"; n += 1
    L = ilan(); L["translations"]["ru"]["description"] += " x"; assert sinif(L)[1].get("RU") == "FAIL: RU farkli"; n += 1
    L = ilan(); L["translations"] = [L["translations"]["ru"]]; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    L = ilan(); L["translations"] = {"x": L["translations"]["ru"]}; assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    L = ilan(); L["translations"] = {"de": {"language": "de", "title": "t", "description": "d"}}
    assert sinif(L)[1].get("RU") == "FAIL: RU yok"; n += 1
    # nitelik
    p = copy.deepcopy(PROPS); p[2]["values"] = ["0.2"]; assert "nitelik Depth" in sinif(ilan(), p)[1]; n += 1
    p = copy.deepcopy(PROPS); p[0]["values"] = [2.99]; assert sinif(ilan(), p)[0] == "YAYINA HAZIR"; n += 1
    p = copy.deepcopy(PROPS); p[1]["scale_id"] = 7; assert "nitelik Height" in sinif(ilan(), p)[1]; n += 1
    assert sinif(ilan(), PROPS[:2])[1].get("nitelik Depth") == "FAIL: yok"; n += 1
    s, k = sinif(ilan(), None); assert s == "HENUZ YAYINLAMAYIN" and k["nitelik"].startswith("olculemedi"), (s, k); n += 1
    # alan yok -> olculemedi
    for alan, ad in (("shipping_profile_id", "kargo profili"), ("production_partners", "uretim ortagi"), ("images", "gorsel"),
                     ("videos", "video"), ("translations", "RU"), ("price", "fiyat"), ("is_personalizable", "kisisellestirme")):
        L = ilan(); del L[alan]
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and k[ad].startswith("olculemedi"), (alan, s, k); n += 1
    L = ilan(); L["state"] = "active"; L["shipping_profile_id"] = 1; assert sinif(L)[0] == "YAYINDA (EKSIK VAR)"; n += 1
    # SPEC anahtar kapisi (yanlis adli anahtar kontrolu sessizce kaldirmasin)
    assert spec_dene(lambda s: None) is None; n += 1
    for anahtar in ("ru", "alt_metin_kaynagi"):
        assert "eksik" in spec_dene(lambda s, a=anahtar: s.pop(a)); n += 1
    for anahtar in ("nitelikler", "aciklama_zorunlu"):
        assert "beklenen." + anahtar in spec_dene(lambda s, a=anahtar: s["beklenen"].pop(a)); n += 1
    assert "eksik" in spec_dene(lambda s: s.pop("eski_medya")); n += 1
    assert "beklenen.kisisellestirme" in spec_dene(lambda s: s["beklenen"].pop("kisisellestirme")); n += 1
    assert "beklenen.nitelik" in spec_dene(lambda s: s["beklenen"].update(nitelik=s["beklenen"].pop("nitelikler"))); n += 1
    assert "bilinmeyen ['rus']" in spec_dene(lambda s: s.update(rus=s.pop("ru"))); n += 1
    sp = copy.deepcopy(SPEC); sp["alt_metin_kaynagi"] = None                                   # acikca kapali: ZAYIF sinif
    assert y.zayif_mi(sp) and not y.zayif_mi(SPEC); n += 1
    S = y.kontrol_et(sp, KOD, ilan(), RU, PROPS, None, ESKI, ORTAK)
    assert y.siniflandir(ilan(), S, y.zayif_mi(sp))[0] == "YAYINA HAZIR (ZAYIF KONTROL)"; n += 1
    sp2 = copy.deepcopy(SPEC); sp2["beklenen"]["nitelikler"] = []; assert y.zayif_mi(sp2); n += 1
    L = ilan(); L["images"][1]["alt_text"] = "tree"; assert sinif(L, spec=sp)[1]["gorsel"].startswith("FAIL"); n += 1
    # rapor ve liste
    R = {"ilanlar": {KOD: {"listing_id": 1, "sinif": "YAYINA HAZIR", "eksik": {}},
                     "X_Y": {"listing_id": None, "sinif": "DURUM okunamadi", "eksik": {"okuma": "listing id yok"}}},
         "zaman": "t", "kota_bas": 1, "kota_son": 1, "cagri": 2, "yarim": "SystemExit: DUR: kota 9 < 10", "beklenen_sayi": 78}
    m = y.md(R, SPEC)
    assert ("listing-editor/edit/1" in m and "Toplam 2 / beklenen 78" in m and "Kontrol EDİLMEYEN: stil" in m
            and m.splitlines()[2].startswith("YARIM") and "X_Y" in m and "Uygulanan kontroller" in m), m; n += 1
    ids, kotu = y.ilan_listesi({"A": {"listing_id": 5}, "B": {"hata": "listing id yok (None)"}, "C": "x"})
    assert ids == {"A": 5} and sorted(kotu) == ["B", "C"]; n += 1
    assert y.eski_idler({"gorsel": [{"id": 1}], "video": [{"id": 2}]}) == ({"1"}, {"2"}) and y.eski_idler({"listing_id": 1}) is None; n += 1
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
    def __init__(self, ilanlar, kalan, adim=1, ortaklar=None):
        self.ilanlar, self.kalan, self.istek, self.adim = ilanlar, kalan, [], adim   # adim 2: paralel baska kosu kota yiyor
        self.ortaklar = ortaklar if ortaklar is not None else [
            {"production_partner_id": ORTAK, "partner_name": "Printful Latvia", "location": "Latvia"},
            {"production_partner_id": 5817638, "partner_name": "Printing and Fulfillment Partner", "location": "United States"}]

    def __call__(self, method, url, params=None, **kw):
        assert method == "GET", method
        path = url.split("/v3/application")[-1]
        self.istek.append((path, dict(params or {})))
        self.kalan -= self.adim
        if path.endswith("/production-partners") and self.ortaklar == "403":
            return Yanit(403, {"error": "forbidden"}, self.kalan)
        if path.endswith("/production-partners"):
            return Yanit(200, {"count": len(self.ortaklar), "results": copy.deepcopy(self.ortaklar)}, self.kalan)
        if path.startswith("/shops/") and path.endswith("/properties"):
            return Yanit(200, {"count": 3, "results": copy.deepcopy(PROPS)}, self.kalan)
        if path == "/listings/batch":
            ids = [int(x) for x in params["listing_ids"].split(",")]
            assert params["includes"] == y.INCLUDES
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


def kos(ilanlar_json, ag, *ek, spec=SPEC_YOL):
    d = Path(tempfile.mkdtemp())
    (d / "I.json").write_text(json.dumps(ilanlar_json))
    eski = (etsy_common.requests.request, y.TokenStore, sys.argv, dict(os.environ))
    etsy_common.requests.request, y.TokenStore = ag, SahteStore
    os.environ.update(TOKEN_FILE="x", ETSY_API_KEY="k", ETSY_SHARED_SECRET="s", ETSY_SHOP_ID="39729443")
    sys.argv = ["yayina_hazir.py", "--spec", str(spec), "--ilanlar", str(d / "I.json"), "--out", str(d / "o"), *ek]
    hata = None
    try:
        y.main()
    except SystemExit as e:
        hata = str(e.code)
    except KeyboardInterrupt:
        hata = "KeyboardInterrupt"
    finally:
        etsy_common.requests.request, y.TokenStore, sys.argv = eski[0], eski[1], eski[2]
        os.environ.clear(); os.environ.update(eski[3])
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
    R = json.loads((d / "o/YAYINA_HAZIR.json").read_text()) if (d / "o/YAYINA_HAZIR.json").exists() else None
    return hata, R, d


def kayit(lid):
    return {"listing_id": lid, "gorsel": [{"id": 101 + i} for i in range(11)], "video": [{"id": 900}]}


def tum78(n_ilan=78, bozuk=None):
    """RU CSV'deki kodlar icin ilan (cift sira draft, tek sira active); bozuk(kod, L) ile degisiklik."""
    I, ilanlar = {}, {}
    for i, kod in enumerate(sorted(RU)[:n_ilan]):
        L = ilan(kod=kod, lid=4611600000 + i, state="active" if i % 2 else "draft")
        if bozuk:
            bozuk(kod, L)
        ilanlar[L["listing_id"]] = L; I[kod] = kayit(L["listing_id"])
    return I, ilanlar


def istisna(kod_hedef, exc):
    eski_k = y.kontrol_et

    def f(spec, kod, *a, **k):
        if kod == kod_hedef:
            raise exc
        return eski_k(spec, kod, *a, **k)
    return eski_k, f


def uctan_uca():
    n = 0
    I, il = tum78()
    ag = SahteAg(il, 1000)
    hata, R, _ = kos(I, ag, "--mod", "kontrol")
    assert hata is None and "yarim" not in R, hata
    s = {}
    for v in R["ilanlar"].values():
        s[v["sinif"]] = s.get(v["sinif"], 0) + 1
    assert s == {"YAYINA HAZIR": 39, "YAYINDA": 39}, s; n += 1
    assert R["cagri"] == 1 + 1 + 1 + 78 and len(ag.istek) == 81, (R["cagri"], len(ag.istek)); n += 1   # shop + ortak + batch + 78 nitelik
    # 77 kodlu dosya: eksik kod listelenir; eski video olan, bozuk veri olan ilan

    def boz(kod, L):
        if kod == "ARIES_ARIES":
            L["videos"][0]["video_id"] = 900
        if kod == "ARIES_CANCER":
            L["images"].append("x")                      # dict olmayan oge: gercek istisna, yalniz bu ilanda kalir
    I, il = tum78(bozuk=boz); eksik = sorted(I)[-1]; del I[eksik]
    I["LEO_LEO"] = {"hata": "listing id yok (None)"}
    hata, R, d = kos(I, SahteAg(il, 1000), "--mod", "kontrol")
    assert hata is None, hata
    assert R["ilanlar"][eksik]["sinif"] == "DURUM ilan dosyasinda yok"; n += 1
    assert R["ilanlar"]["ARIES_ARIES"]["eksik"]["video"] == "FAIL: eski video"; n += 1
    assert R["ilanlar"]["ARIES_CANCER"]["sinif"] == "DURUM olculemedi", R["ilanlar"]["ARIES_CANCER"]; n += 1
    assert R["ilanlar"]["LEO_LEO"]["sinif"] == "DURUM okunamadi" and "Toplam 78 / beklenen 78" in (d / "o/YAYINA_HAZIR.md").read_text(); n += 1
    # batch'te donmeyen ilan
    I, il = tum78(); del il[4611600005]
    hata, R, _ = kos(I, SahteAg(il, 1000), "--mod", "kontrol")
    assert R["ilanlar"][sorted(RU)[5]]["eksik"]["okuma"] == "batch yanitinda yok"; n += 1
    # nitelik kapali PASS uretmez
    I, il = tum78()
    hata, R, _ = kos(I, SahteAg(il, 1000), "--mod", "kontrol", "--nitelik-yok")
    x = R["ilanlar"][sorted(RU)[0]]
    assert x["sinif"] == "HENUZ YAYINLAMAYIN" and x["eksik"]["nitelik"].startswith("olculemedi"); n += 1
    # magazada ortak adi tek degil -> DUR, yarim cikti isaretli
    hata, R, _ = kos(I, SahteAg(il, 1000, ortaklar=[]), "--mod", "kontrol")
    assert hata and "uretim ortagi 0 kayit" in hata and R and R["yarim"].startswith("SystemExit"), hata; n += 1
    # kota baslangicta yetmiyor -> okuma yok
    ag = SahteAg(il, 90)                                   # 89 < 81 + 10
    hata, R, _ = kos(I, ag, "--mod", "kontrol")
    assert hata and "okuma baslamadi" in hata and len(ag.istek) == 1 and R is None, (hata, len(ag.istek)); n += 1
    # kota istek ortasinda tabana iner -> yarim cikti, isaretli
    ag = SahteAg(il, 120, adim=2)                          # baslangic gecer (118 >= 91), baska kosu da yedigi icin ortada DUR
    hata, R, d = kos(I, ag, "--mod", "kontrol")
    assert hata and "kota" in hata and R and R["yarim"].startswith("SystemExit") and len(R["ilanlar"]) < 78, hata; n += 1
    assert (d / "o/YAYINA_HAZIR.md").read_text().splitlines()[2].startswith("YARIM"); n += 1
    # ilan basina beklenmeyen istisna: o ilan DURUM olculemedi, kosu surer
    eski_k, f = istisna(sorted(RU)[3], ValueError("x")); y.kontrol_et = f
    try:
        hata, R, _ = kos(I, SahteAg(il, 1000), "--mod", "kontrol")
    finally:
        y.kontrol_et = eski_k
    assert hata is None and R["ilanlar"][sorted(RU)[3]]["sinif"] == "DURUM olculemedi" and "yarim" not in R; n += 1
    # iptal (KeyboardInterrupt) ara noktada: yarim cikti isaretli kalir, istisna yutulmaz
    eski_k, f = istisna(sorted(RU)[12], KeyboardInterrupt()); y.kontrol_et = f
    try:
        hata, R, d = kos(I, SahteAg(il, 1000), "--mod", "kontrol")
    finally:
        y.kontrol_et = eski_k
    assert hata == "KeyboardInterrupt" and R["yarim"].startswith("KeyboardInterrupt") and 10 <= len(R["ilanlar"]) < 78, (hata, R.get("yarim")); n += 1
    assert (d / "o/YAYINA_HAZIR.md").read_text().splitlines()[2].startswith("YARIM"); n += 1
    eski_k = y.kontrol_et

    def sinyal(spec, kod, *a, **k):                       # SIGTERM (Actions iptali / zaman asimi) gercek sinyalle
        if kod == sorted(RU)[20]:
            os.kill(os.getpid(), signal.SIGTERM)
        return eski_k(spec, kod, *a, **k)
    y.kontrol_et = sinyal
    try:
        hata, R, _ = kos(I, SahteAg(il, 1000), "--mod", "kontrol")
    finally:
        y.kontrol_et = eski_k
    assert hata and "sinyal 15" in hata and R["yarim"].startswith("SystemExit: DUR: sinyal 15"), (hata, R.get("yarim")); n += 1
    # olc: tum ilanlar tek batch, ornek draft + active, ortaklar
    ag = SahteAg(il, 1000)
    hata, _, d = kos(I, ag, "--mod", "olc")
    O = json.loads((d / "o/OLCUM.json").read_text())
    assert hata is None and len(ag.istek) == 5 and O["donen"] == 78 and sorted(O["ornek"]) == ["active", "draft"], (hata, len(ag.istek)); n += 1
    assert O["ornek"]["draft"]["translations_anahtar"] == ["ru"] and "images[0].listing_image_id" in O["ornek"]["draft"]["batch_alanlar"]; n += 1
    assert [x[1] for x in O["uretim_ortaklari"]] == ["Printful Latvia", "Printing and Fulfillment Partner"]; n += 1
    il2 = {k: v for k, v in il.items() if v["state"] == "active"}                               # batch taslaklari dondurmuyor
    hata, _, d = kos(I, SahteAg(il2, 1000), "--mod", "olc")
    O = json.loads((d / "o/OLCUM.json").read_text())
    assert hata and "olc eksik" in hata and O["donen"] == 39 and len(O["donmeyen"]) == 39; n += 1
    hata, _, d = kos(I, SahteAg({}, 1000), "--mod", "olc")
    assert hata and "olc eksik" in hata; n += 1
    ag = SahteAg(il, 1000, ortaklar="403")
    hata, _, d = kos(I, ag, "--mod", "olc")
    O = json.loads((d / "o/OLCUM.json").read_text())
    assert hata is None and O["donen"] == 78 and str(O["uretim_ortaklari"]).startswith("okunamadi"), (hata, O["uretim_ortaklari"]); n += 1
    return n


if __name__ == "__main__":
    n1 = birim()
    with contextlib.redirect_stdout(io.StringIO()):
        n2 = uctan_uca()
    print(f"test_yayina_hazir: {n1 + n2}/{n1 + n2} PASS (birim {n1}, uctan uca {n2})")
