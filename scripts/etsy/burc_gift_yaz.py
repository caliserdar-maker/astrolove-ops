#!/usr/bin/env python3
"""Burc hediye ifadesi + yil donumu 77 ilan plani TEK KOSU (Serdar kararlari 22 Eki; PLAN_BURC_GIFT v3).
Her ilan bir kez yazilir. Hedef metinler: SONRA_234.json (Serdar onayi 22 Eki); eski metinler: ONCE (AKTIF_METIN.json, 22 Eki canli okuma).

Modlar:
  yedek   : SALT OKUMA. Kumedeki ilanlar GET (+ yil donumu envanter) -> <out>/YEDEK/<id>.json; ONCE ile fark (kayma) raporu.
  siparis : SALT OKUMA. Gonderilmemis makbuzlarda SKU'su PRINT8X10 iceren satir sayisi (yalniz sayi; musteri verisi yazilmaz).
  yaz     : ETSY'YE YAZAR (--onay SERDAR_BURC_GIFT). Ilan basina:
            GET -> state active degilse ATLA -> alan bazli plan (eski -> yaz, yeni -> atla, ikisi de degil -> DUR)
            -> yedek (yazmadan once) -> yil donumu: envanter PUT (Shipped print 8x10 cikar, hazirlik = yeni 1-3 gun tanimi)
            -> tek PATCH (title, tags, description [+ yil donumu: materials, production_partner_ids, shipping_profile_id])
            -> geri okuma (10 sn arayla en fazla 3 deneme) -> dogrulama. Ilk FAIL'de DUR.
            Uretim ortagi API ile kalkmazsa FAIL degil: PANEL listesine yazilir (Serdar elle kaldirir).
Kume: cl (CANCER_LIBRA 3 aile) | pilot (5 ilan) | kalan (geri kalan 226) | id1,id2,...
Kota tabani 10 (CLAUDE.md); ilan basina baslamadan once kalan >= 15 aranir.
Kullanim: burc_gift_yaz.py --mod yedek|siparis|yaz --once ONCE.json --sonra SONRA.json --kume cl --out OUT [--onay KOD]"""
import argparse
import html
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ONAY = "SERDAR_BURC_GIFT"
KOTA_TABAN = 10
KOTA_ILAN = 15
P_FORMAT = 514
BASKI = "Shipped print 8x10"
ESKI_PROFIL, YENI_PROFIL = 318080539024, 318577242658   # BY Print 8x10 Worldwide -> BY Digital Free Worldwide (21 Eki, PASS)
ORTAK_HAZIRLIK = 1517641240112                          # poster + kupa + BY ortak 4-7 gun tanimi: DEGISTIRILMEZ
MATERIALS = "digital file"
PILOT = [("poster", "ARIES_LIBRA"), ("kupa", "LEO_LEO"), ("yildonumu", "AQUARIUS_ARIES"),
         ("yildonumu", "SAGITTARIUS_TAURUS"), ("poster", "CAPRICORN_SAGITTARIUS")]
KORUNAN = ("taxonomy_id", "shop_section_id", "who_made", "when_made", "is_supply", "return_policy_id", "quantity",
           "is_personalizable", "personalization_is_required", "personalization_char_count_max", "personalization_instructions",
           "listing_type", "should_auto_renew", "is_taxable", "price")
BEKLE_SN = 10


class Dur(Exception):
    pass


def norm(s):
    return html.unescape(s or "").replace("\r\n", "\n")


def kota(api, gerek=KOTA_TABAN):
    try:
        r = int(api.remaining)
    except (TypeError, ValueError):
        return
    if r < max(gerek, KOTA_TABAN):
        raise Dur(f"KOTA {r} < {max(gerek, KOTA_TABAN)}")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else float(p)


def imza(inv, hazirlik_dahil=True):
    """{(deger_metni,...): (sku, fiyat, adet, acik, [hazirlik])} ; urun anahtari tum ozellik degerleri."""
    s = {}
    for p in inv.get("products") or []:
        anahtar = tuple((v.get("property_id"), tuple(v.get("values") or [])) for v in p.get("property_values") or [])
        o = (p.get("offerings") or [{}])[0]
        d = (p.get("sku"), para(o.get("price") or 0), o.get("quantity"), o.get("is_enabled"))
        s[anahtar] = d + ((o.get("readiness_state_id"),) if hazirlik_dahil else ())
    return s


def baski_mi(anahtar):
    return any(pid == P_FORMAT and BASKI in vals for pid, vals in anahtar)


def partner_ids(x):
    """None = API yanitinda alan yok (okunamadi)."""
    if "production_partners" not in x and "production_partner_ids" not in x:
        return None
    if x.get("production_partners") is not None:
        return sorted(p.get("production_partner_id") for p in x["production_partners"])
    return sorted(x.get("production_partner_ids") or [])


def korunan(x):
    return {k: (para(x[k]) if k == "price" and x.get(k) is not None else x.get(k)) for k in KORUNAN}


def ozet(x):
    return {"title": norm(x.get("title")), "tags": list(x.get("tags") or []), "description": norm(x.get("description"))}


def alan_plani(cur, once, sonra):
    """her alan: 'yaz' | 'atla'; kayma -> Dur."""
    p = {}
    for k in ("title", "tags", "description"):
        if cur[k] == sonra[k]:
            p[k] = "atla"
        elif cur[k] == once[k]:
            p[k] = "yaz"
        else:
            raise Dur(f"{k}: canli metin ne eski ne yeni (kayma); ilan listeden cikar")
    return p


def hazirlik_bul(api, shop, olustur):
    lst = (api.get(f"/shops/{shop}/readiness-state-definitions", params={"limit": 100}) or {}).get("results") or []
    uygun = [d for d in lst if d.get("readiness_state") == "made_to_order" and d.get("min_processing_days") == 1
             and d.get("max_processing_days") == 3 and d.get("readiness_state_id") != ORTAK_HAZIRLIK]
    if uygun:
        return uygun[0]["readiness_state_id"], "var"
    if not olustur:
        return None, "yok"
    y = api.post(f"/shops/{shop}/readiness-state-definitions",
                 {"readiness_state": "made_to_order", "min_processing_time": 1, "max_processing_time": 3, "processing_time_unit": "days"}) or {}
    rid = y.get("readiness_state_id")
    z = api.get(f"/shops/{shop}/readiness-state-definitions/{rid}") or {}
    if not (z.get("readiness_state") == "made_to_order" and z.get("min_processing_days") == 1 and z.get("max_processing_days") == 3):
        raise Dur(f"hazirlik tanimi geri okuma FAIL: {z}")
    return rid, "olusturuldu"


def envanter_govdesi(inv, hazirlik):
    prods = []
    for p in inv.get("products") or []:
        anahtar = tuple((v.get("property_id"), tuple(v.get("values") or [])) for v in p.get("property_values") or [])
        if baski_mi(anahtar):
            continue
        o = (p.get("offerings") or [{}])[0]
        prods.append(dict(sku=p.get("sku") or "",
                          property_values=[dict(property_id=v["property_id"], property_name=v.get("property_name"),
                                                value_ids=v.get("value_ids"), values=v.get("values")) for v in p.get("property_values") or []],
                          offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                          readiness_state_id=hazirlik)]))
    return dict(products=prods, price_on_property=inv.get("price_on_property") or [],
                quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                readiness_state_on_property=inv.get("readiness_state_on_property") or [])


def bir_ilan(api, shop, lid, hedef, once, out, hazirlik, R):
    kota(api, KOTA_ILAN)
    x = api.get(f"/listings/{lid}") or {}
    if str(x.get("shop_id")) != str(shop):
        raise Dur("shop uyusmuyor")
    if x.get("state") != "active":
        R["sonuc"] = f"ATLANDI_STATE {x.get('state')}"   # updateListing taslagi yayina alir (CLAUDE.md 7 Eyl)
        return
    aile = hedef["aile"]
    sonra = {"title": hedef["baslik"], "tags": hedef["etiketler"], "description": hedef["aciklama"]}
    cur = ozet(x)
    plan = alan_plani(cur, once, sonra)
    data = {"title": sonra["title"]} if plan["title"] == "yaz" else {}
    if plan["tags"] == "yaz":
        data["tags"] = ",".join(sonra["tags"])
    if plan["description"] == "yaz":
        data["description"] = sonra["description"]
    inv0, govde = None, None
    if aile == "yildonumu":
        if (x.get("materials") or []) != [MATERIALS]:
            data["materials"] = MATERIALS
        if partner_ids(x) is None or partner_ids(x):
            data["production_partner_ids"] = ""
        prof = int(x.get("shipping_profile_id") or 0)
        if prof == ESKI_PROFIL:
            data["shipping_profile_id"] = YENI_PROFIL
        elif prof != YENI_PROFIL:
            raise Dur(f"kargo profili {prof}: ne eski ne yeni")
        inv0 = api.get(f"/listings/{lid}/inventory") or {}
        i0 = imza(inv0)
        nb = sum(1 for k in i0 if baski_mi(k))
        if not ((len(i0) == 15 and nb == 5) or (len(i0) == 10 and nb == 0)):
            raise Dur(f"envanter {len(i0)} urun, baski {nb} (15/5 ya da 10/0 beklenir)")
        if nb or any(v[4] != hazirlik for v in i0.values()):
            govde = envanter_govdesi(inv0, hazirlik)
    R["plan"] = dict(alanlar=plan, ek=sorted(k for k in data if k not in ("title", "tags", "description")), envanter=bool(govde))
    yedek = out / "YEDEK"; yedek.mkdir(exist_ok=True)
    (yedek / f"{lid}.json").write_text(json.dumps({"ilan": x, "envanter": inv0}, ensure_ascii=False, indent=1), encoding="utf-8")
    if not data and not govde:
        R["sonuc"] = "ZATEN"
        return
    if govde:
        api.put_json(f"/listings/{lid}/inventory", govde)
        kota(api)
    if data:
        api.patch(f"/shops/{shop}/listings/{lid}", data)
        kota(api)
    # geri okuma (bayat okumaya karsi 3 deneme)
    for deneme in range(3):
        y = api.get(f"/listings/{lid}") or {}
        if ozet(y) == sonra:
            break
        time.sleep(BEKLE_SN)
    s = ozet(y)
    hata = [k for k in sonra if s[k] != sonra[k]]
    if y.get("state") != "active":
        hata.append(f"state {y.get('state')}")
    kx, ky = korunan(x), korunan(y)
    if aile == "yildonumu":
        for z in ("price", "quantity"):                 # envanterle degisebilir (baski urunleri cikar)
            kx.pop(z, None); ky.pop(z, None)
    hata += [f"korunan alan {k}" for k in kx if kx[k] != ky[k]]
    if aile == "yildonumu":
        if (y.get("materials") or []) != [MATERIALS]:
            hata.append(f"materials {y.get('materials')}")
        if int(y.get("shipping_profile_id") or 0) != YENI_PROFIL:
            hata.append(f"profil {y.get('shipping_profile_id')}")
        if partner_ids(y) is None:
            R["panel"] = "uretim ortagi API yanitinda okunamadi: panelde kontrol"   # Serdar panel adimi
        elif partner_ids(y):
            R["panel"] = f"uretim ortagi API ile kalkmadi: {partner_ids(y)}"
        inv1 = api.get(f"/listings/{lid}/inventory") or {}
        i0, i1 = imza(inv0), imza(inv1)
        bek = {k: v[:4] + (hazirlik,) for k, v in i0.items() if not baski_mi(k)}
        if i1 != bek:
            hata.append(f"envanter {len(i1)} urun, beklenen {len(bek)}; fark var")
    R["sonra"] = dict(alan_hata=hata, istek=api.calls, kota=api.remaining)
    if hata:
        R["sonuc"] = "FAIL"
        raise Dur(f"geri okuma FAIL: {hata}")
    R["sonuc"] = "PASS"


def siparis_say(api, shop):
    n_satir, n_makbuz, ofs = 0, 0, 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"was_shipped": "false", "was_canceled": "false", "limit": 100, "offset": ofs}) or {}
        r = d.get("results") or []
        for rc in r:
            k = sum(1 for t in rc.get("transactions") or [] if "PRINT8X10" in (t.get("sku") or "").upper())
            n_satir += k
            n_makbuz += 1 if k else 0
        ofs += len(r)
        if not r or ofs >= (d.get("count") or 0):
            break
    return {"gonderilmemis_makbuz_tarandi": ofs, "print8x10_satir": n_satir, "print8x10_makbuz": n_makbuz}


def kume_sec(kume, sonra):
    cift = {(v["aile"], v["cift"]): k for k, v in sonra.items()}
    cl = [k for k, v in sonra.items() if v["cift"] == "CANCER_LIBRA"]
    pilot = [cift[p] for p in PILOT]
    if kume == "cl":
        return sorted(cl)
    if kume == "pilot":
        return pilot
    if kume == "kalan":
        return sorted(k for k in sonra if k not in cl and k not in pilot)
    ids = [s.strip() for s in kume.split(",") if s.strip()]
    yok = [i for i in ids if i not in sonra]
    if yok or not ids:
        raise SystemExit(f"HATA: kume listede yok: {yok}")
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["yedek", "siparis", "yaz"])
    ap.add_argument("--once", required=True)
    ap.add_argument("--sonra", required=True)
    ap.add_argument("--kume", default="cl")
    ap.add_argument("--onay", default="")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    if a.mod == "yaz" and a.onay != ONAY:
        raise SystemExit(f"DUR: yaz modu --onay {ONAY} ister")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sonra = json.load(open(a.sonra))
    once = {str(x["listing_id"]): {"title": norm(x["title"]), "tags": list(x["tags"]), "description": norm(x["description"])}
            for x in json.load(open(a.once))}
    if set(once) != set(sonra) or len(sonra) != 234:
        raise SystemExit(f"HATA: ONCE {len(once)} / SONRA {len(sonra)} ilan kumesi ayni degil")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    RAPOR = {"mod": a.mod, "kume": a.kume, "ilanlar": []}
    kod = 0
    try:
        if a.mod == "siparis":
            RAPOR["siparis"] = siparis_say(api, shop)
            print("SIPARIS", json.dumps(RAPOR["siparis"]))
            return
        if a.kume == "hepsi" and a.mod != "yedek":
            raise SystemExit("HATA: 'hepsi' yalniz yedek modunda; yazma cl -> pilot -> kalan sirasiyla")
        ids = sorted(sonra) if a.kume == "hepsi" else kume_sec(a.kume, sonra)
        if a.mod == "yedek":
            yd = out / "YEDEK"; yd.mkdir(exist_ok=True)
            kayma = []
            for i, lid in enumerate(ids, 1):
                kota(api)
                x = api.get(f"/listings/{lid}") or {}
                inv = (api.get(f"/listings/{lid}/inventory") or {}) if sonra[lid]["aile"] == "yildonumu" else None
                (yd / f"{lid}.json").write_text(json.dumps({"ilan": x, "envanter": inv}, ensure_ascii=False, indent=1), encoding="utf-8")
                cur = ozet(x)
                durum = ("YENI" if cur == {"title": sonra[lid]["baslik"], "tags": sonra[lid]["etiketler"], "description": sonra[lid]["aciklama"]}
                         else "ESKI" if cur == once[lid] else "KAYMA")
                if durum == "KAYMA" or x.get("state") != "active":
                    kayma.append({"listing_id": lid, "durum": durum, "state": x.get("state")})
                if i % 25 == 0:
                    print(f"[{i}/{len(ids)}] istek {api.calls} kota {api.remaining}", flush=True)
            RAPOR["yedek"] = {"ilan": len(ids), "kayma_ya_da_aktif_degil": kayma}
            print("YEDEK", len(ids), "kayma/aktif degil", len(kayma))
            return
        hazirlik = None
        if any(sonra[i]["aile"] == "yildonumu" for i in ids):
            hazirlik, nasil = hazirlik_bul(api, shop, olustur=True)
            RAPOR["hazirlik"] = {"id": hazirlik, "nasil": nasil}
        t0 = time.time()
        for n, lid in enumerate(ids, 1):
            R = {"listing_id": lid, "aile": sonra[lid]["aile"], "cift": sonra[lid]["cift"]}
            RAPOR["ilanlar"].append(R)
            bir_ilan(api, shop, lid, sonra[lid], once[lid], out, hazirlik, R)
            g = time.time() - t0
            print(f"[{n}/{len(ids)}] {R['aile']} {R['cift']} {R['sonuc']} | gecen {g:.0f} sn, kalan ~{g / n * (len(ids) - n):.0f} sn, "
                  f"%{100 * n // len(ids)} | kota {api.remaining}", flush=True)
    except Dur as e:
        RAPOR["dur"] = str(e)
        print(f"::error::DURDU: {e}")
        kod = 4
    finally:
        RAPOR["istek"], RAPOR["kota_son"] = api.calls, api.remaining
        RAPOR["panel"] = [r for r in RAPOR["ilanlar"] if r.get("panel")]
        (out / "RAPOR.json").write_text(json.dumps(RAPOR, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if kod:
        raise SystemExit(kod)
    say = {}
    for r in RAPOR["ilanlar"]:
        say[r["sonuc"]] = say.get(r["sonuc"], 0) + 1
    print(f"SONUC {say} | panel {len(RAPOR['panel'])} | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    main()
