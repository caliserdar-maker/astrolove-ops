#!/usr/bin/env python3
"""yayina_hazir.py testleri (ag yok). Bilinen PASS: tam ilan YAYINA HAZIR, yayinda ilan YAYINDA. Bilinen FAIL: eski kargo profili,
eksik ortak, free shipping, eski cumle, 13 gorsel, rank tekrari, 2. gorsel alt metni, video yok, RU yok / farkli, nitelik farki,
alan yok -> olculemedi (PASS sayilmaz), salt okuma yazma yasagi."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yayina_hazir as y  # noqa: E402

SPEC = y.spec_yukle(str(y.KOK / "docs/ornament/ORN_YAYIN_SPEC.json"))
RU = y.ru_csv(SPEC)
B = SPEC["beklenen"]
KOD = "CANCER_LIBRA"


def ilan():
    alts = ["cover"] + ["two signs, one shared symbol x"] + ["a"] * 12
    return {"listing_id": 4611501158, "state": "draft", "shipping_profile_id": B["shipping_profile_id"],
            "production_partners": [{"production_partner_id": 1, "partner_name": "Printful Latvia"}],
            "price": {"amount": 1990, "divisor": 100}, "description": "intro\n" + B["aciklama_zorunlu"][0] + "\nend",
            "images": [{"rank": i + 1, "alt_text": alts[i]} for i in range(14)], "videos": [{"video_id": 1}],
            "translations": [{"language": "ru", "title": RU[KOD]["baslik_ru"], "description": RU[KOD]["aciklama_ru"]}]}


PROPS = [{"property_id": o["property_id"], "values": o["values"], "scale_id": o["scale_id"]} for o in B["nitelikler"]]


def sinif(L, props=PROPS):
    S = y.kontrol_et(SPEC, KOD, L, RU[KOD], props)
    return y.siniflandir(L, S)


def main():
    n = 0
    s, k = sinif(ilan()); assert s == "YAYINA HAZIR" and not k, (s, k); n += 1
    L = ilan(); L["state"] = "active"; assert sinif(L)[0] == "YAYINDA"; n += 1
    bozuklar = [
        ("shipping_profile_id", 319194887351, "kargo profili"),
        ("production_partners", [{"partner_name": "Prodigi"}], "uretim ortagi"),
        ("price", {"amount": 2990, "divisor": 100}, "fiyat"),
        ("videos", [], "video"),
    ]
    for alan, deger, ad in bozuklar:
        L = ilan(); L[alan] = deger
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and ad in k, (alan, s, k); n += 1
    L = ilan(); L["description"] = "with free shipping " + L["description"]
    assert "aciklama yasak: free shipping" in sinif(L)[1]; n += 1
    L = ilan(); L["description"] = "Made and shipped by our production partner, with free shipping."
    k = sinif(L)[1]; assert any(x.startswith("aciklama zorunlu") for x in k); n += 1
    L = ilan(); L["images"] = L["images"][:13]; assert "gorsel" in sinif(L)[1]; n += 1
    L = ilan(); L["images"][3]["rank"] = 3; assert "gorsel" in sinif(L)[1]; n += 1
    L = ilan(); L["images"][1]["alt_text"] = "tree"; assert "gorsel" in sinif(L)[1]; n += 1
    L = ilan(); L["translations"] = []; assert sinif(L)[1].get("RU") == "FAIL: RU yok"; n += 1
    L = ilan(); L["translations"][0]["description"] += " x"; assert sinif(L)[1].get("RU") == "FAIL: RU farkli"; n += 1
    L = ilan(); L["translations"] = {"ru": {"title": RU[KOD]["baslik_ru"], "description": RU[KOD]["aciklama_ru"]}}
    assert sinif(L)[0] == "YAYINA HAZIR"; n += 1
    p = copy.deepcopy(PROPS); p[2]["values"] = ["0.2"]; assert "nitelik Depth" in sinif(ilan(), p)[1]; n += 1
    p = copy.deepcopy(PROPS); p[0]["values"] = [2.99]; assert sinif(ilan(), p)[0] == "YAYINA HAZIR"; n += 1
    for alan, ad in (("shipping_profile_id", "kargo profili"), ("production_partners", "uretim ortagi"), ("images", "gorsel"),
                     ("videos", "video"), ("translations", "RU")):
        L = ilan(); del L[alan]
        s, k = sinif(L); assert s == "HENUZ YAYINLAMAYIN" and k[ad].startswith("olculemedi"), (alan, s, k); n += 1
    L = ilan(); L["state"] = "active"; L["shipping_profile_id"] = 1; assert sinif(L)[0] == "YAYINDA (EKSIK VAR)"; n += 1
    R = {"ilanlar": {KOD: {"listing_id": 1, "sinif": "YAYINA HAZIR", "eksik": {}}}, "zaman": "t", "kota_bas": 1, "kota_son": 1, "cagri": 2}
    assert "listing-editor/edit/1" in y.md(R, SPEC); n += 1
    so = y.SaltOkur.__new__(y.SaltOkur)
    try:
        so._call("PUT", "/x"); raise AssertionError("yazma gecti")
    except SystemExit as e:
        assert "salt okuma" in str(e.code); n += 1
    print(f"test_yayina_hazir: {n}/{n} PASS (TOPLAM {n})")


if __name__ == "__main__":
    main()
