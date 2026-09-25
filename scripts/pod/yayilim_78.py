#!/usr/bin/env python3
"""YAYILIM 78 (Serdar, 25 Eyl 2026): 78 kisisellestirilebilir POD ilanina onayli metin + kisisellestirme
+ nitelik + 80 varyantli envanter + 3-5 gun hazirlik suresi. Kaynak: Drive TEMP/METIN_78/METIN_78.csv
(kuru kosu PASS 78/78). GORSELLERE DOKUNULMAZ (yalniz renk->gorsel baglari korunur/onarilir).

Modlar:
  hazirlik : SALT OKUMA. 78 ilanin yedegi (listing, inventory, variation-images, images, properties,
             personalization, RU) + ilan basina yazma plani + kapilar (state, 5 renk, SKU cifti, boy
             etiketleri) + hazirlik suresi tanimi + OAS istek semalari (kanit) + kota.
  yaz      : --listing X (pilot) ya da --hepsi (kalan ilanlar). --confirm YAYILIM_78 sart.
             Her ilan: once yedek, sonra yazma, sonra TAM geri okuma ve PASS/FAIL.

KURAL (CLAUDE.md): updateListing bir TASLAGI yayina alir -> state 'active' olmayan ilana HICBIR sey
yazilmaz, raporda 'ATLANDI (state=...)' olarak sorulur.
"""
import argparse
import csv
import html
import json
import os
import pathlib
import sys
import time

import requests

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
import pod_pilot_15 as P  # noqa: E402
from fiyat_b import FIYAT, anahtar_of  # noqa: E402
from pod_sku import ED2, SIGN3, make_sku  # noqa: E402
import metin_78 as M  # noqa: E402

REF = "4570143815"                      # Cancer-Libra: boy etiketleri + sira kaynagi
PILOT = "4570110641"                    # Aquarius-Aries
ONAY = "YAYILIM_78"
NITELIK = [(148789511775, 2315, "Yes", "Can be personalized"), (46803063641, 12, "Anniversary", "Occasion")]
HAZIRLIK_GUN = (3, 5)
ADET = 999                              # tek adet: Etsy "quantity must be consistent" (25 Eyl, 3 ilan FAIL)
ONCELIK = "4570110641,4570113157,4570114301,4570224058,4570160260"   # pilot + satis yapmis 4 ilan
OAS_URL = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
OAS_OP = ["updateListing", "updateListingPersonalization", "getListingPersonalization",
          "createShopReadinessStateDefinition", "updateListingProperty", "updateListingTranslation",
          "updateListingInventory", "updateVariationImages"]
csv.field_size_limit(10 ** 8)


# ------------------------------------------------------------------ yardimcilar
def norm(s):
    """Etsy metni HTML-escape ile dondurur (' -> &#39;, pilot 4570110641 olcumu): once unescape."""
    return "\n".join(x.rstrip() for x in html.unescape(str(s or "")).replace("\r\n", "\n").strip().split("\n"))


def csv_oku(yol):
    with open(yol, encoding="utf-8") as fh:
        return {r["ilan_id"]: r for r in csv.DictReader(fh)}


def cift(row):
    a, b = [x.strip() for x in row["cift"].split("+")]
    return a, b


def sku_cifti(row):
    a, b = cift(row)
    return f"{a.upper()}_{b.upper()}"


def sorular(row):
    return [{"question_type": "text_input", "question_text": row[f"alan{i}_ad"],
             "instructions": row[f"alan{i}_aciklama"], "required": True,
             "max_allowed_characters": int(row[f"alan{i}_max"])} for i in (1, 2, 3)]


def renk_adi_pv(inv):
    for pr in inv.get("products") or []:
        if P.pv_of(pr, "primary color"):
            return "primary color"
        if P.pv_of(pr, "color"):
            return "color"
    return None


def ed_of(renk):
    k = (renk or "").strip().upper().replace(" ", "_")
    return k if k in ED2 else None


def anlik(api, shop, lid, nitelik=True):
    """Kota dostu anlik goruntu (ilan basina 5-6 GET): listing+kisisellestirme tek cagrida; video okunmaz."""
    L = api.get(f"/listings/{lid}", params={"includes": "Personalization"}) or {}
    sn = {"listing": L,
          "personalization": {k: v for k, v in L.items() if "personaliz" in k.lower()},
          "inventory": api.get(f"/listings/{lid}/inventory") or {},
          "images": sorted(((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or []),
                           key=lambda x: x.get("rank") or 0),
          "variation_images": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
          "ru": api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {},
          "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    sn["properties"] = ((api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []) if nitelik else []
    return sn


def soru_listesi(sn):
    p = sn.get("personalization") or {}
    q = p.get("personalization_questions") or p.get("personalization") or []
    if isinstance(q, dict):
        q = q.get("personalization_questions") or []
    return [x for x in q if isinstance(x, dict)]


def hazirlik_tanimi(api, shop):
    rs = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    bul = next((x for x in rs if x.get("readiness_state") == "made_to_order"
                and (x.get("min_processing_days"), x.get("max_processing_days")) == HAZIRLIK_GUN), None)
    return (bul or {}).get("readiness_state_id"), rs


# ------------------------------------------------------------------ hedef envanter
def ref_sablon(ref_inv):
    rpv = renk_adi_pv(ref_inv)
    sab = []
    for pr in ref_inv.get("products") or []:
        et = P.deger(pr, "size")
        o = (pr.get("offerings") or [{}])[0]
        sab.append({"etiket": et, "anahtar": anahtar_of(et), "renk": P.deger(pr, rpv),
                    "adet": o.get("quantity"), "acik": bool(o.get("is_enabled")),
                    "pv_sira": [(pv.get("property_name") or "").lower() for pv in pr.get("property_values") or []]})
    return sab


def hedef_envanter(inv, sab, ref_inv, pair, rs_id):
    """-> (govde, [hatalar]). Boy etiketi + sira + renk sirasi referanstan; renk pv (value_ids) ilanin kendisinden."""
    h = []
    rpv = renk_adi_pv(inv)
    if not rpv:
        return None, ["ilanda renk ozelligi yok"]
    renk_pv, boy_pv0, mevcut = {}, None, {}
    for pr in inv.get("products") or []:
        pv = P.pv_of(pr, rpv)
        ad = ((pv or {}).get("values") or [""])[0]
        renk_pv.setdefault(ad.lower(), pv)
        spv = P.pv_of(pr, "size")
        boy_pv0 = boy_pv0 or spv
        mevcut[(anahtar_of(P.deger(pr, "size")), ad.lower())] = pr
    if not boy_pv0:
        return None, ["ilanda boy ozelligi yok"]
    ref_renkler = sorted({(s["renk"] or "").lower() for s in sab})
    if sorted(renk_pv) != ref_renkler:
        h.append(f"renkler referansla ayni degil: {sorted(renk_pv)} != {ref_renkler}")
    urunler = []
    for s in sab:
        k, et, rn = s["anahtar"], s["etiket"], (s["renk"] or "").lower()
        if k not in FIYAT:
            h.append(f"fiyat tablosunda olmayan boy: {et}")
            continue
        cpv, ed = renk_pv.get(rn), ed_of(s["renk"])
        if not cpv or not ed:
            h.append(f"renk eslesmedi: {s['renk']}")
            continue
        eski = mevcut.get((k, rn))
        d_renk = {"property_id": cpv.get("property_id"), "property_name": cpv.get("property_name"),
                  "values": list(cpv.get("values") or [])}
        if cpv.get("value_ids"):
            d_renk["value_ids"] = list(cpv["value_ids"])          # renk->gorsel bagi korunur
        d_boy = {"property_id": boy_pv0.get("property_id"), "property_name": boy_pv0.get("property_name"),
                 "values": [et]}
        if boy_pv0.get("scale_id"):
            d_boy["scale_id"] = boy_pv0["scale_id"]
        eski_spv = P.pv_of(eski, "size") if eski else None
        if eski_spv and (eski_spv.get("values") or [None])[0] == et and eski_spv.get("value_ids"):
            d_boy["value_ids"] = list(eski_spv["value_ids"])     # ayni etiket: id korunur
        pvs = [d_renk, d_boy] if (s["pv_sira"] or ["x"])[0] in ("primary color", "color") else [d_boy, d_renk]
        adet = ADET                                               # mevcut adet KOPYALANMAZ (satista 998 kalir -> 400)
        urunler.append({"sku": make_sku(pair, ed, k), "property_values": pvs,
                        "offerings": [{"price": FIYAT[k], "quantity": adet, "is_enabled": s["acik"],
                                       "readiness_state_id": rs_id}]})
    if len(urunler) != 80:
        h.append(f"hedef urun {len(urunler)} != 80")
    cpid, spid = (next(iter(renk_pv.values())) or {}).get("property_id"), boy_pv0.get("property_id")
    rolu = {}
    for pr in ref_inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            rolu[pv.get("property_id")] = "renk" if (pv.get("property_name") or "").lower() in ("primary color", "color") else "boy"
        break

    def esle(ids):
        return [cpid if rolu.get(i) == "renk" else spid for i in (ids or [])]

    govde = {"products": urunler,
             "price_on_property": esle(ref_inv.get("price_on_property")),
             "quantity_on_property": esle(ref_inv.get("quantity_on_property")),
             "sku_on_property": esle(ref_inv.get("sku_on_property"))}
    return govde, h


# ------------------------------------------------------------------ dogrulama
def dogrula(sn0, sn1, row, sab, rs_id, pair):
    h = []
    L1 = sn1["listing"]
    if L1.get("state") != sn0["listing"].get("state"):
        h.append(f"state degisti {sn0['listing'].get('state')} -> {L1.get('state')}")
    if html.unescape(L1.get("title") or "") != row["yeni_baslik"]:
        h.append("baslik farkli")
    et = row["yeni_etiketler"].split("|")
    gelen_et = [html.unescape(t).lower() for t in (L1.get("tags") or [])]
    if gelen_et != [t.lower() for t in et]:
        if sorted(gelen_et) == sorted(et):
            pass                                                  # Etsy sirayi degistirebilir: kume esit yeter
        else:
            h.append(f"etiketler farkli ({len(L1.get('tags') or [])})")
    if norm(L1.get("description")) != norm(row["yeni_aciklama_en"]):
        h.append("EN aciklama farkli")
    ru = sn1.get("ru") or {}
    if html.unescape(ru.get("title") or "") != row["yeni_ru_baslik"]:
        h.append("RU baslik farkli")
    if norm(ru.get("description")) != norm(row["yeni_ru_aciklama"]):
        h.append("RU aciklama farkli")
    q = soru_listesi(sn1)
    bek = sorular(row)
    if len(q) != 3:
        h.append(f"kisisellestirme soru sayisi {len(q)} != 3")
    for a, b in zip(q, bek):
        if ((a.get("question_text") or "") != b["question_text"] or not a.get("required")
                or int(a.get("max_allowed_characters") or 0) != b["max_allowed_characters"]
                or (a.get("question_type") or "") != "text_input"):
            h.append(f"soru farkli: {a.get('question_text')}")
    if any("sign order" in (x.get("question_text") or "").lower() for x in q):
        h.append("Sign order sorusu duruyor")
    pmap = {p.get("property_id"): set(p.get("value_ids") or []) for p in sn1.get("properties") or []}
    for pid, vid, _, ad in NITELIK:
        if vid not in pmap.get(pid, set()):
            h.append(f"nitelik yok: {ad}")
    inv1 = sn1["inventory"]
    prs = inv1.get("products") or []
    if len(prs) != 80:
        h.append(f"varyant {len(prs)} != 80")
    ref_sira = []
    for s in sab:
        if s["etiket"] not in ref_sira:
            ref_sira.append(s["etiket"])
    if P.boy_sirasi(inv1) != ref_sira:
        h.append("boy etiketi/sirasi referansla ayni degil")
    rpv = renk_adi_pv(inv1)
    for pr in prs:
        k = anahtar_of(P.deger(pr, "size"))
        o = (pr.get("offerings") or [{}])[0]
        bek_sku = make_sku(pair, ed_of(P.deger(pr, rpv)) or "MIDNIGHT_BLUE", k) if k else "?"
        if (pr.get("sku") or "") != bek_sku:
            h.append(f"SKU {pr.get('sku')} != {bek_sku}")
            break
        if abs(P.para(o.get("price")) - FIYAT.get(k, -1)) > 1e-9:
            h.append(f"fiyat {pr.get('sku')} {P.para(o.get('price'))}")
            break
        if o.get("readiness_state_id") != rs_id:
            h.append(f"hazirlik suresi {pr.get('sku')}: {o.get('readiness_state_id')} != {rs_id}")
            break
    v0 = P.v_renk_haritasi(sn0["inventory"], sn0["variation_images"])
    v1 = P.v_renk_haritasi(inv1, sn1["variation_images"])
    if v1 != v0:
        h.append(f"renk-gorsel bagi farkli: {len(v1)}/{len(v0)}")
    if [i.get("listing_image_id") for i in sn0["images"]] != [i.get("listing_image_id") for i in sn1["images"]]:
        h.append("GORSELLER DEGISTI")
    return h


# ------------------------------------------------------------------ yazma
def mevcut_adetler(inv):
    say = {}
    for pr in inv.get("products") or []:
        q = ((pr.get("offerings") or [{}])[0]).get("quantity")
        say[q] = say.get(q, 0) + 1
    return ", ".join(f"{k} x{v}" for k, v in sorted(say.items(), key=lambda kv: str(kv[0])))


def yaz_ilan(api, shop, lid, row, sab, ref_inv, rs_id, yedek, yalniz_envanter=False):
    sn0 = anlik(api, shop, lid, nitelik=False)
    adetler = mevcut_adetler(sn0["inventory"])
    (yedek / f"{lid}_ONCE.json").write_text(json.dumps(sn0, ensure_ascii=False, indent=1), encoding="utf-8")
    st = sn0["listing"].get("state")
    if st != "active":
        return "ATLANDI", f"state={st} (taslak/pasif: updateListing yayina alir; Serdar'a soruldu)"
    pair = sku_cifti(row)
    govde, h = hedef_envanter(sn0["inventory"], sab, ref_inv, pair, rs_id)
    if h:
        return "FAIL", "kapi: " + "; ".join(h)[:300]
    adim = "baslik/etiket/aciklama"
    try:
        if not yalniz_envanter:
            api.patch(f"/shops/{shop}/listings/{lid}", {"title": row["yeni_baslik"], "tags": row["yeni_etiketler"].replace("|", ","),
                                                        "description": row["yeni_aciklama_en"]})
            adim = "RU"
            api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                    {"title": row["yeni_ru_baslik"], "description": row["yeni_ru_aciklama"],
                     "tags": ",".join((sn0.get("ru") or {}).get("tags") or [])})
            adim = "kisisellestirme"
            # OAS: supports_multiple_personalization_questions bir SORGU parametresi (govde degil); tam degistirir.
            api._call("POST", f"/shops/{shop}/listings/{lid}/personalization",
                      params={"supports_multiple_personalization_questions": "true"},
                      json_body={"personalization_questions": sorular(row)})
            adim = "nitelik"
            for pid, vid, deg, _ in NITELIK:
                api.put(f"/shops/{shop}/listings/{lid}/properties/{pid}", {"value_ids": str(vid), "values": deg})
        adim = "envanter"
        api.put_json(f"/listings/{lid}/inventory", govde)
        adim = "renk-gorsel"
        sn_ara = {"inventory": api.get(f"/listings/{lid}/inventory") or {},
                  "variation_images": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []}
        v0 = P.v_renk_haritasi(sn0["inventory"], sn0["variation_images"])
        v1 = P.v_renk_haritasi(sn_ara["inventory"], sn_ara["variation_images"])
        if v0 and v1 != v0:
            pid = (sn0["variation_images"][0] or {}).get("property_id")
            ad_vid = {}
            rpv = renk_adi_pv(sn_ara["inventory"])
            for pr in sn_ara["inventory"].get("products") or []:
                pv = P.pv_of(pr, rpv)
                if pv and pv.get("value_ids"):
                    ad_vid[(pv.get("values") or [""])[0]] = pv["value_ids"][0]
            vi = [{"property_id": pid, "value_id": ad_vid[ad], "image_id": int(img)}
                  for ad, img in v0.items() if ad in ad_vid]
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
            log(f"  {lid}: renk-gorsel baglari geri yazildi ({len(vi)})")
    except SystemExit as e:
        return "FAIL", f"{adim} adiminda hata: {str(e)[:240]} | onceki adet: {adetler}"
    sn1 = anlik(api, shop, lid)
    (yedek / f"{lid}_SONRA.json").write_text(json.dumps(sn1, ensure_ascii=False, indent=1), encoding="utf-8")
    h = dogrula(sn0, sn1, row, sab, rs_id, pair)
    ek = f" | onceki adet: {adetler} -> {ADET}"
    return ("PASS", "tam geri okuma temiz" + ek) if not h else ("FAIL", "; ".join(h)[:300] + ek)


# ------------------------------------------------------------------ metin2: yalniz metin + kisisellestirme (25 Eyl)
def csv_yenile(satirlar):
    """CSV'yi Etsy'yi okumadan sablondan yeniler: EN/RU aciklama, RU baslik, 3 alan. Baslik/etiket DEGISMEZ (kapi)."""
    h_top, yeni = [], {}
    for lid, r in satirlar.items():
        a, b = cift(r)
        m, al = M.metinler(a, b), M.kisisel_alanlar(a, b)
        h = M.kontrol(m)
        if m["baslik"] != r["yeni_baslik"] or "|".join(m["etiketler"]) != r["yeni_etiketler"]:
            h.append("baslik/etiket sablondan farkli cikti (degismemeliydi)")
        r2 = dict(r)
        r2.update({"yeni_aciklama_en": m["aciklama"], "yeni_ru_baslik": m["ru_baslik"], "yeni_ru_aciklama": m["ru_aciklama"],
                   "kontrol": "PASS" if not h else "FAIL: " + "; ".join(h)})
        for i, x in enumerate(al, 1):
            r2.update({f"alan{i}_ad": x["ad"], f"alan{i}_aciklama": x["aciklama"], f"alan{i}_max": x["max"]})
        yeni[lid] = r2
        if h:
            h_top.append((lid, h))
    return yeni, h_top


def ru_of(api, shop, lid, L):
    for t in L.get("translations") or []:
        if (t.get("language") or "").lower().startswith("ru"):
            return t
    return api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}


def metin2_ilan(api, shop, lid, row, yedek):
    inc = {"includes": "Personalization,Translations"}
    L0 = api.get(f"/listings/{lid}", params=inc) or {}
    ru0 = ru_of(api, shop, lid, L0)
    (yedek / f"{lid}_METIN2_ONCE.json").write_text(json.dumps({"listing": L0, "ru": ru0}, ensure_ascii=False, indent=1), encoding="utf-8")
    if L0.get("state") != "active":
        return "ATLANDI", f"state={L0.get('state')}"
    adim = "EN aciklama"
    try:
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": row["yeni_aciklama_en"]})
        adim = "RU"
        api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                {"title": row["yeni_ru_baslik"], "description": row["yeni_ru_aciklama"], "tags": ",".join(ru0.get("tags") or [])})
        adim = "kisisellestirme"
        api._call("POST", f"/shops/{shop}/listings/{lid}/personalization",
                  params={"supports_multiple_personalization_questions": "true"},
                  json_body={"personalization_questions": sorular(row)})
    except SystemExit as e:
        return "FAIL", f"{adim} adiminda hata: {str(e)[:240]}"
    L1 = api.get(f"/listings/{lid}", params=inc) or {}
    ru1 = ru_of(api, shop, lid, L1)
    (yedek / f"{lid}_METIN2_SONRA.json").write_text(json.dumps({"listing": L1, "ru": ru1}, ensure_ascii=False, indent=1), encoding="utf-8")
    h = []
    if L1.get("state") != L0.get("state"):
        h.append(f"state degisti {L0.get('state')} -> {L1.get('state')}")
    if norm(L1.get("description")) != norm(row["yeni_aciklama_en"]):
        h.append("EN aciklama farkli")
    if html.unescape(ru1.get("title") or "") != row["yeni_ru_baslik"]:
        h.append("RU baslik farkli")
    if norm(ru1.get("description")) != norm(row["yeni_ru_aciklama"]):
        h.append("RU aciklama farkli")
    if [html.unescape(t).lower() for t in (L1.get("tags") or [])] != [html.unescape(t).lower() for t in (L0.get("tags") or [])]:
        h.append("EN etiketler degisti")
    q = soru_listesi({"personalization": {k: v for k, v in L1.items() if "personaliz" in k.lower()}})
    bek = sorular(row)
    if len(q) != 3:
        h.append(f"soru sayisi {len(q)} != 3")
    for a_, b_ in zip(q, bek):
        if ((a_.get("question_text") or "") != b_["question_text"] or (a_.get("instructions") or "") != b_["instructions"]
                or not a_.get("required") or int(a_.get("max_allowed_characters") or 0) != b_["max_allowed_characters"]):
            h.append(f"soru farkli: {a_.get('question_text')}")
    return ("PASS", "geri okuma temiz") if not h else ("FAIL", "; ".join(h)[:300])


# ------------------------------------------------------------------ OAS kaniti
def oas_ozet():
    try:
        d = requests.get(OAS_URL, timeout=120).json()
    except Exception as e:
        return {"hata": f"{type(e).__name__}"}
    out = {}
    for yol, ops in (d.get("paths") or {}).items():
        for yontem, op in (ops or {}).items():
            if isinstance(op, dict) and op.get("operationId") in OAS_OP:
                icerik = ((op.get("requestBody") or {}).get("content") or {})
                out[op["operationId"]] = {
                    "uc": f"{yontem.upper()} {yol}",
                    "parametre": [p.get("name") for p in op.get("parameters") or [] if isinstance(p, dict)],
                    "govde": {ct: json.dumps(v.get("schema") or {}, ensure_ascii=False)[:1500] for ct, v in icerik.items()},
                }
    return out


# ------------------------------------------------------------------ ana
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=["hazirlik", "yaz", "metin2"])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="_out/yayilim78")
    ap.add_argument("--listing", default="")
    ap.add_argument("--hepsi", action="store_true", help="yaz: kalan tum ilanlar (pilot haric)")
    ap.add_argument("--atla", default=PILOT)
    ap.add_argument("--confirm", default="")
    ap.add_argument("--kota-alt", type=int, default=400)
    ap.add_argument("--yalniz-envanter", action="store_true", help="yaz: metin/kisisellestirme/nitelik atlanir")
    ap.add_argument("--oncelik", default=ONCELIK, help="metin2 --hepsi: once bu sira (ilki pilot: FAIL ise durur)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    yedek = out / "YEDEK"
    yedek.mkdir(parents=True, exist_ok=True)
    satirlar = csv_oku(a.csv)
    if len(satirlar) != 78:
        sys.exit(f"HATA: CSV {len(satirlar)} satir (78 bekleniyordu)")
    kotu = [k for k, r in satirlar.items() if r.get("kontrol") != "PASS"]
    if kotu:
        sys.exit(f"HATA: CSV'de kontrolu PASS olmayan ilan: {kotu[:5]}")

    if a.mod == "metin2":
        satirlar, h_csv = csv_yenile(satirlar)
        if h_csv:
            sys.exit(f"HATA: CSV kapisi FAIL: {h_csv[:3]} (CSV ve Etsy'ye yazilmadi)")
        with (out / "METIN_78.csv").open("w", encoding="utf-8", newline="") as fh:
            ilk = next(iter(satirlar.values()))
            w = csv.DictWriter(fh, fieldnames=list(ilk.keys()))
            w.writeheader()
            w.writerows(satirlar.values())
        log(f"CSV yenilendi: kontrol PASS {78 - len(h_csv)}/78")
        if h_csv:
            sys.exit(f"HATA: CSV kapisi FAIL: {h_csv[:3]} (Etsy'ye yazilmadi)")
    basliklar = {}
    _ham = requests.request

    def _kaydet(*x, **k):                                         # Etsy limit/remaining/reset basliklarini olc
        r = _ham(*x, **k)
        basliklar.update({h: v for h, v in r.headers.items()
                          if any(t in h.lower() for t in ("limit", "remaining", "reset", "retry"))})
        return r
    requests.request = _kaydet
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    ref_inv = api.get(f"/listings/{REF}/inventory") or {}
    (out / "REFERANS_ENVANTER.json").write_text(json.dumps(ref_inv, ensure_ascii=False, indent=1), encoding="utf-8")
    sab = ref_sablon(ref_inv)
    rs_id, rs_liste = hazirlik_tanimi(api, shop)
    rapor = [f"# YAYILIM 78 — {a.mod} — {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", "",
             f"- referans {REF}: {len(sab)} varyant, boylar {P.boy_sirasi(ref_inv)}",
             f"- hazirlik suresi tanimi {HAZIRLIK_GUN[0]}-{HAZIRLIK_GUN[1]} gun: "
             + (str(rs_id) if rs_id else "YOK (yaz modunda olusturulur)"),
             f"- tum tanimlar: {[(x.get('readiness_state_id'), x.get('readiness_state'), x.get('min_processing_days'), x.get('max_processing_days')) for x in rs_liste]}",
             f"- kota basta: {api.remaining}", ""]

    if a.mod == "metin2":
        if a.confirm != ONAY:
            sys.exit(f"HATA: metin2 --confirm {ONAY} ister")
        sonuc, t0 = [], time.time()
        if a.listing:
            hedef = [x.strip() for x in a.listing.split(",") if x.strip()]
        elif a.hepsi:
            onc = [x.strip() for x in a.oncelik.split(",") if x.strip() in satirlar]
            hedef = onc + [k for k in satirlar if k not in onc]
        else:
            sys.exit("HATA: --listing ya da --hepsi")
        for i, lid in enumerate(hedef, 1):
            try:
                kalan_kota = int(api.remaining or 99999)
            except ValueError:
                kalan_kota = 99999
            if kalan_kota < a.kota_alt:
                sonuc.append((lid, "DURDU", f"kota {api.remaining} < {a.kota_alt}"))
                break
            d, n = metin2_ilan(api, shop, lid, satirlar[lid], yedek)
            sonuc.append((lid, d, n))
            if i == 1 and d != "PASS":
                break                                             # ilk ilan pilottur: FAIL ise kalanlar yazilmaz
            g = time.time() - t0
            log(f"  [{i}/{len(hedef)}] {lid} {d} | gecen {g / 60:.1f} dk | kalan {g / i * (len(hedef) - i) / 60:.1f} dk "
                f"| %{i * 100 // len(hedef)} | kota {api.remaining} | {n[:100]}")
        ok = sum(1 for x in sonuc if x[1] == "PASS")
        rapor += [f"- METIN2 PASS {ok}/{len(hedef)} | FAIL {sum(1 for x in sonuc if x[1] == 'FAIL')} | "
                  f"islenmeyen {len(hedef) - len(sonuc)} | kota sonda {api.remaining}", "",
                  "| ilan | cift | sonuc | not |", "|---|---|---|---|"]
        rapor += [f"| {lid} | {satirlar[lid]['cift']} | {d} | {n} |" for lid, d, n in sonuc]
        with (out / "SONUC_METIN2.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ilan", "cift", "sonuc", "not"])
            w.writerows([(lid, satirlar[lid]["cift"], d, n) for lid, d, n in sonuc])
    elif a.mod == "hazirlik":
        (out / "OAS_ISTEK.json").write_text(json.dumps(oas_ozet(), ensure_ascii=False, indent=1), encoding="utf-8")
        tablo = ["| ilan | cift | state | renk | varyant | boylar (mevcut) | SKU cifti mevcut -> yeni | kisisel soru | kapi |",
                 "|---|---|---|---|---|---|---|---|---|"]
        say = {"hazir": 0, "sorun": 0}
        t0 = time.time()
        for i, (lid, row) in enumerate(satirlar.items(), 1):
            sn = anlik(api, shop, lid)
            (yedek / f"{lid}_ONCE.json").write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
            inv = sn["inventory"]
            rpv = renk_adi_pv(inv)
            renkler = sorted({P.deger(pr, rpv) for pr in inv.get("products") or []}) if rpv else []
            mevcut_cift = sorted({(pr.get("sku") or "").split("-")[1] for pr in inv.get("products") or []
                                  if (pr.get("sku") or "").startswith("POD-") and len((pr.get("sku") or "").split("-")) > 2})
            yeni = sku_cifti(row)
            yeni_kod = "_".join(SIGN3.get(x, "?") for x in yeni.split("_"))
            _, h = hedef_envanter(inv, sab, ref_inv, yeni, rs_id or 0)
            st = sn["listing"].get("state")
            if st != "active":
                h.append(f"state={st}")
            if mevcut_cift and mevcut_cift != [yeni_kod]:
                h.append(f"SKU cifti degisir {mevcut_cift} -> {yeni_kod}")
            say["hazir" if not h else "sorun"] += 1
            boylar = [anahtar_of(b) for b in P.boy_sirasi(inv)]
            tablo.append(f"| {lid} | {row['cift']} | {st} | {len(renkler)} | {len(inv.get('products') or [])} | "
                         f"{','.join(str(b) for b in boylar)} | {','.join(mevcut_cift) or '-'} -> {yeni_kod} | "
                         f"{len(soru_listesi(sn))} | {'HAZIR' if not h else '; '.join(h)[:160]} |")
            if i % 10 == 0 or i == len(satirlar):
                g = time.time() - t0
                log(f"  {i}/{len(satirlar)} (%{i * 100 // len(satirlar)}) | gecen {g / 60:.1f} dk | "
                    f"kalan {g / i * (len(satirlar) - i) / 60:.1f} dk | kota {api.remaining}")
        rapor += [f"- yazmaya hazir: {say['hazir']}/78 | sorunlu: {say['sorun']}/78", f"- kota sonda: {api.remaining}", ""] + tablo
    else:
        if a.confirm != ONAY:
            sys.exit(f"HATA: yaz modu --confirm {ONAY} ister")
        if not rs_id:
            r = api.post(f"/shops/{shop}/readiness-state-definitions",
                         {"readiness_state": "made_to_order", "min_processing_time": HAZIRLIK_GUN[0],
                          "max_processing_time": HAZIRLIK_GUN[1], "processing_time_unit": "days"})
            rs_id = r.get("readiness_state_id")
            rapor.append(f"- hazirlik suresi tanimi OLUSTURULDU: {rs_id}")
            if not rs_id:
                sys.exit("HATA: hazirlik suresi tanimi olusturulamadi")
        if a.listing:
            hedef = [x.strip() for x in a.listing.split(",") if x.strip()]
        elif a.hepsi:
            atla = {x.strip() for x in a.atla.split(",") if x.strip()}
            hedef = [k for k in satirlar if k not in atla]
        else:
            sys.exit("HATA: --listing ya da --hepsi")
        sonuc = []
        t0 = time.time()
        for i, lid in enumerate(hedef, 1):
            try:
                kalan_kota = int(api.remaining or 99999)
            except ValueError:
                kalan_kota = 99999
            if kalan_kota < a.kota_alt:
                sonuc.append((lid, "DURDU", f"kota {api.remaining} < {a.kota_alt}"))
                break
            d, n = yaz_ilan(api, shop, lid, satirlar[lid], sab, ref_inv, rs_id, yedek, a.yalniz_envanter)
            sonuc.append((lid, d, n))
            g = time.time() - t0
            log(f"  [{i}/{len(hedef)}] {lid} {d} | gecen {g / 60:.1f} dk | kalan {g / i * (len(hedef) - i) / 60:.1f} dk "
                f"| %{i * 100 // len(hedef)} | kota {api.remaining} | {n[:120]}")
            if a.listing and len(hedef) == 1 and d != "PASS":
                break
        ok = sum(1 for s in sonuc if s[1] == "PASS")
        rapor += [f"- PASS {ok}/{len(hedef)} | FAIL {sum(1 for s in sonuc if s[1] == 'FAIL')} | "
                  f"ATLANDI {sum(1 for s in sonuc if s[1] == 'ATLANDI')} | kota sonda {api.remaining}", "",
                  "| ilan | cift | sonuc | not |", "|---|---|---|---|"]
        rapor += [f"| {lid} | {satirlar[lid]['cift']} | {d} | {n} |" for lid, d, n in sonuc]
        with (out / "SONUC.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ilan", "cift", "sonuc", "not"])
            w.writerows([(lid, satirlar[lid]["cift"], d, n) for lid, d, n in sonuc])
    rapor += ["", f"- Etsy kota basliklari (son cevap, {time.strftime('%H:%M:%S', time.gmtime())} UTC): {basliklar}"]
    metin = "\n".join(rapor)
    (out / f"RAPOR_{a.mod}.md").write_text(metin + "\n", encoding="utf-8")
    log(metin[:6000])
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(metin[:60000] + "\n")
    if a.mod in ("yaz", "metin2") and (any(x[1] != "PASS" for x in sonuc) or (a.mod == "metin2" and len(sonuc) < len(hedef))):
        sys.exit("DUR: PASS olmayan ilan var (rapora bak)")


if __name__ == "__main__":
    main()
