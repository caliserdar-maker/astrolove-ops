#!/usr/bin/env python3
"""Burc hediye ifadesi + yil donumu 77 ilan plani TEK KOSU (Serdar kararlari 22 Eki; PLAN_BURC_GIFT v3).
Her ilan bir kez yazilir. Hedef metinler: SONRA_234.json (Serdar onayi 22 Eki); eski metinler: ONCE (AKTIF_METIN.json, 22 Eki canli okuma).

Modlar:
  yedek   : SALT OKUMA. Kumedeki ilanlar GET (+ yil donumu envanter, stil-gorsel baglari) -> <out>/YEDEK/<id>.json; kayma raporu.
  siparis : SALT OKUMA. Gonderilmemis, iptal edilmemis makbuzlarda baski satiri sayisi (SKU PRINT8X10 YA DA yil donumu ilaninda
            "Shipped print" varyasyonu). Yalniz sayi; musteri verisi yazilmaz.
  yaz     : ETSY'YE YAZAR (--onay SERDAR_BURC_GIFT). Sira:
            1) kume yil donumu iceriyorsa siparis kapisi (baski satiri > 0 -> DUR)
            2) kumenin TAMAMI icin yedek (yazmadan once) -> Drive'a yukle ve sayisini dogrula (YEDEK_DRIVE ortami)
            3) ilan basina: GET -> state active degilse ATLA -> alan bazli plan (eski -> yaz, yeni -> atla, ikisi de degil -> DUR)
               -> yil donumu envanter PUT (Shipped print 8x10 cikar; hazirlik = BY'ye ozel 1-3 gun tanimi)
               -> PATCH (title, tags, description [+ yil donumu: materials, shipping_profile_id])
               -> yil donumu: uretim ortagi AYRI PATCH (production_partner_ids=""); 4xx ise FAIL degil, PANEL listesi
               -> geri okuma (10 sn arayla en fazla 3 deneme: metin + envanter) -> dogrulama. Ilk FAIL'de DUR.
            Envanter PUT ile PATCH arasinda kota DUR'u yok (yarim ilan birakmamak icin); ilan basina baslarken kalan >= 30 aranir.
  geri_al : ETSY'YE YAZAR (--onay SERDAR_GERI_AL). --yedek-dizin'deki <id>.json'dan baslik/etiket/aciklama/materials/profil ve
            envanteri (baski urunleri dahil, eski hazirlik) geri yazar; geri okuma.
Kume: cl (CANCER_LIBRA 3 aile) | pilot (5 ilan) | kalan (geri kalan 226) | id1,id2,...
Kullanim: burc_gift_yaz.py --mod yedek|siparis|yaz|geri_al --once ONCE.json --sonra SONRA.json --kume cl --out OUT [--onay KOD]"""
import argparse
import html
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ONAY, ONAY_GERI = "SERDAR_BURC_GIFT", "SERDAR_GERI_AL"
KOTA_TABAN = 10
KOTA_ILAN = 30
P_FORMAT = 514
BASKI = "Shipped print 8x10"
ESKI_PROFIL, YENI_PROFIL = 318080539024, 318577242658   # BY Print 8x10 Worldwide -> BY Digital Free Worldwide (21 Eki, PASS)
ORTAK_HAZIRLIK = 1517641240112                          # poster + kupa + BY ortak 4-7 gun tanimi: DEGISTIRILMEZ
MATERIALS = "digital file"
PILOT = [("poster", "ARIES_LIBRA"), ("kupa", "LEO_LEO"), ("yildonumu", "AQUARIUS_ARIES"),
         ("yildonumu", "SAGITTARIUS_TAURUS"), ("poster", "CAPRICORN_SAGITTARIUS")]
KORUNAN = ("taxonomy_id", "shop_section_id", "who_made", "when_made", "is_supply", "return_policy_id", "quantity",
           "is_personalizable", "personalization_is_required", "personalization_char_count_max", "personalization_instructions",
           "listing_type", "should_auto_renew", "is_taxable", "price", "materials", "shipping_profile_id", "production_partners")
BY_DEGISEN = ("price", "quantity", "materials", "shipping_profile_id", "production_partners")  # yil donumunde bilerek degisir
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


def urun_anahtari(p):
    return tuple((v.get("property_id"), tuple(v.get("values") or []), tuple(v.get("value_ids") or [])) for v in p.get("property_values") or [])


def imza(inv):
    """{urun anahtari (ozellik, degerler, value_ids): (sku, fiyat, adet, acik, hazirlik)}"""
    s = {}
    for p in (inv or {}).get("products") or []:
        o = (p.get("offerings") or [{}])[0]
        s[urun_anahtari(p)] = (p.get("sku"), para(o.get("price") or 0), o.get("quantity"), o.get("is_enabled"), o.get("readiness_state_id"))
    return s


def inv_ozellik(inv):
    return {k: sorted((inv or {}).get(k) or []) for k in ("price_on_property", "quantity_on_property", "sku_on_property")}


def baski_mi(anahtar):
    return any(pid == P_FORMAT and BASKI in vals for pid, vals, _ in anahtar)


def partner_ids(x):
    """None = API yanitinda alan yok (okunamadi)."""
    if "production_partners" not in x and "production_partner_ids" not in x:
        return None
    if x.get("production_partners") is not None:
        return sorted(p.get("production_partner_id") for p in x["production_partners"])
    return sorted(x.get("production_partner_ids") or [])


def korunan(x):
    out = {}
    for k in KORUNAN:
        v = x.get(k)
        out[k] = para(v) if k == "price" and v is not None else (partner_ids(x) if k == "production_partners" else v)
    return out


def ozet(x):
    return {"title": norm(x.get("title")), "tags": list(x.get("tags") or []), "description": norm(x.get("description"))}


def esdeger(a, b, alan):
    """Etsy'nin olasi bicim normalizasyonuna dayanikli karsilastirma (bosluk, satir sonu, etiket sirasi/harf)."""
    if alan == "tags":
        return sorted(t.strip().lower() for t in a) == sorted(t.strip().lower() for t in b)
    if alan == "title":
        return " ".join(a.split()) == " ".join(b.split())
    return [ln.rstrip() for ln in a.strip().split("\n")] == [ln.rstrip() for ln in b.strip().split("\n")]


def alan_plani(cur, once, sonra):
    p = {}
    for k in ("title", "tags", "description"):
        if esdeger(cur[k], sonra[k], k):
            p[k] = "atla"
        elif esdeger(cur[k], once[k], k):
            p[k] = "yaz"
        else:
            raise Dur(f"{k}: canli metin ne eski ne yeni (kayma); ilan listeden cikar")
    return p


def stil_gorsel(api, shop, lid):
    return sorted((v.get("property_id"), v.get("value_id"), v.get("image_id"))
                  for v in (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or [])


def hazirlik_listesi(api, shop):
    lst, ofs = [], 0
    while True:
        d = api.get(f"/shops/{shop}/readiness-state-definitions", params={"limit": 100, "offset": ofs}) or {}
        r = d.get("results") or []
        lst += r
        ofs += len(r)
        if not r or ofs >= (d.get("count") or 0):
            return lst


def _uygun(lst):
    return [d for d in lst if d.get("readiness_state") == "made_to_order" and d.get("min_processing_days") == 1
            and d.get("max_processing_days") == 3 and d.get("readiness_state_id") != ORTAK_HAZIRLIK]


def hazirlik_bul(api, shop, olustur):
    uygun = _uygun(hazirlik_listesi(api, shop))
    if len(uygun) > 1:
        raise Dur(f"1-3 gunluk {len(uygun)} tanim var; hangisinin BY'ye ait oldugu belirsiz (Serdar)")
    if uygun:
        return uygun[0]["readiness_state_id"], "var"
    if not olustur:
        return None, "yok"
    try:
        api.post(f"/shops/{shop}/readiness-state-definitions",
                 {"readiness_state": "made_to_order", "min_processing_time": 1, "max_processing_time": 3, "processing_time_unit": "days"})
    except SystemExit as e:
        print(f"hazirlik POST hatasi, liste yeniden okunuyor: {str(e)[:120]}")
    uygun = _uygun(hazirlik_listesi(api, shop))
    if len(uygun) != 1:
        raise Dur(f"hazirlik tanimi olusturma sonrasi {len(uygun)} uygun tanim (1 beklenir)")
    return uygun[0]["readiness_state_id"], "olusturuldu"


def envanter_govdesi(inv, hazirlik, baski_cikar=True):
    prods = []
    for p in inv.get("products") or []:
        if baski_cikar and baski_mi(urun_anahtari(p)):
            continue
        o = (p.get("offerings") or [{}])[0]
        prods.append(dict(sku=p.get("sku") or "",
                          property_values=[dict(property_id=v["property_id"], property_name=v.get("property_name"),
                                                value_ids=v.get("value_ids"), values=v.get("values")) for v in p.get("property_values") or []],
                          offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                          readiness_state_id=hazirlik if hazirlik else o.get("readiness_state_id"))]))
    return dict(products=prods, price_on_property=inv.get("price_on_property") or [],
                quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                readiness_state_on_property=inv.get("readiness_state_on_property") or [])


def yedek_al(api, shop, lid, aile):
    x = api.get(f"/listings/{lid}") or {}
    inv = (api.get(f"/listings/{lid}/inventory") or {}) if aile == "yildonumu" else None
    sg = stil_gorsel(api, shop, lid) if aile == "yildonumu" else None
    return {"ilan": x, "envanter": inv, "stil_gorsel": sg}


def drive_yukle(yerel, hedef_alt):
    """YEDEK_DRIVE ortami varsa klasoru Drive'a kopyalar ve dosya sayisini dogrular."""
    kok = os.environ.get("YEDEK_DRIVE")
    if not kok:
        return "drive yok (yerel)"
    hedef = f"{kok}/{hedef_alt}"
    subprocess.run(["rclone", "copy", str(yerel), hedef, "-q"], check=True)
    n = len([s for s in subprocess.run(["rclone", "lsf", hedef], check=True, capture_output=True, text=True).stdout.split("\n") if s])
    yer = len(list(pathlib.Path(yerel).glob("*.json")))
    if n < yer:
        raise Dur(f"yedek Drive'a eksik yuklendi {n}/{yer}")
    return f"{n} dosya {hedef}"


def bir_ilan(api, shop, lid, hedef, once, out, hazirlik_al, R):
    kota(api, KOTA_ILAN)
    x = api.get(f"/listings/{lid}") or {}
    if str(x.get("shop_id")) != str(shop):
        raise Dur("shop uyusmuyor")
    if x.get("state") != "active":
        R["sonuc"] = f"ATLANDI_STATE {x.get('state')}"   # updateListing taslagi yayina alir (CLAUDE.md 7 Eyl)
        return
    aile = hedef["aile"]
    sonra = {"title": hedef["baslik"], "tags": hedef["etiketler"], "description": hedef["aciklama"]}
    plan = alan_plani(ozet(x), once, sonra)
    data = {}
    if plan["title"] == "yaz":
        data["title"] = sonra["title"]
    if plan["tags"] == "yaz":
        data["tags"] = ",".join(sonra["tags"])
    if plan["description"] == "yaz":
        data["description"] = sonra["description"]
    inv0, govde, sg0, partner_yaz, hazirlik = None, None, None, False, None
    if aile == "yildonumu":
        if (x.get("materials") or []) != [MATERIALS]:
            data["materials"] = MATERIALS
        prof = int(x.get("shipping_profile_id") or 0)
        if prof == ESKI_PROFIL:
            data["shipping_profile_id"] = YENI_PROFIL
        elif prof != YENI_PROFIL:
            raise Dur(f"kargo profili {prof}: ne eski ne yeni")
        partner_yaz = partner_ids(x) is None or bool(partner_ids(x))
        inv0 = api.get(f"/listings/{lid}/inventory") or {}
        sg0 = stil_gorsel(api, shop, lid)
        i0 = imza(inv0)
        nb = sum(1 for k in i0 if baski_mi(k))
        if not ((len(i0) == 15 and nb == 5) or (len(i0) == 10 and nb == 0)):
            raise Dur(f"envanter {len(i0)} urun, baski {nb} (15/5 ya da 10/0 beklenir)")
        hazirlik = hazirlik_al()
        if nb or any(v[4] != hazirlik for v in i0.values()):
            govde = envanter_govdesi(inv0, hazirlik)
    R["plan"] = dict(alanlar=plan, ek=sorted(k for k in data if k not in ("title", "tags", "description")), envanter=bool(govde),
                     partner=partner_yaz)
    if not data and not govde and not partner_yaz:
        R["sonuc"] = "ZATEN"
        return
    # yaz: envanter -> PATCH -> partner (aralarda kota DUR'u yok; yarim ilan birakilmaz)
    if govde:
        api.put_json(f"/listings/{lid}/inventory", govde)
    if data:
        api.patch(f"/shops/{shop}/listings/{lid}", data)
    if partner_yaz:
        try:
            api.patch(f"/shops/{shop}/listings/{lid}", {"production_partner_ids": ""})
        except SystemExit as e:
            R["panel"] = f"uretim ortagi API ile kaldirilamadi ({str(e)[:120]}): panelde kaldir"
    # geri okuma (bayat okumaya karsi 3 deneme: metin + envanter)
    bek_inv = {k: v[:4] + (hazirlik,) for k, v in imza(inv0).items() if not baski_mi(k)} if aile == "yildonumu" else None
    for deneme in range(3):
        y = api.get(f"/listings/{lid}") or {}
        inv1 = (api.get(f"/listings/{lid}/inventory") or {}) if aile == "yildonumu" else None
        if all(esdeger(ozet(y)[k], sonra[k], k) for k in sonra) and (aile != "yildonumu" or imza(inv1) == bek_inv):
            break
        time.sleep(BEKLE_SN)
    (out / "HAM").mkdir(exist_ok=True)
    (out / "HAM" / f"{lid}.json").write_text(json.dumps({"ilan": y, "envanter": inv1}, ensure_ascii=False, indent=1), encoding="utf-8")
    s = ozet(y)
    hata = [k for k in sonra if not esdeger(s[k], sonra[k], k)]
    if y.get("state") != "active":
        hata.append(f"state {y.get('state')}")
    kx, ky = korunan(x), korunan(y)
    for z in (BY_DEGISEN if aile == "yildonumu" else ()):
        kx.pop(z, None); ky.pop(z, None)
    hata += [f"korunan alan {k}: {kx[k]} -> {ky[k]}" for k in kx if kx[k] != ky[k]]
    if aile == "yildonumu":
        if (y.get("materials") or []) != [MATERIALS]:
            hata.append(f"materials {y.get('materials')}")
        if int(y.get("shipping_profile_id") or 0) != YENI_PROFIL:
            hata.append(f"profil {y.get('shipping_profile_id')}")
        if partner_ids(y) is None:
            R.setdefault("panel", "uretim ortagi API yanitinda okunamadi: panelde kontrol")
        elif partner_ids(y):
            R.setdefault("panel", f"uretim ortagi API ile kalkmadi: {partner_ids(y)}")
        if imza(inv1) != bek_inv:
            hata.append(f"envanter {len(imza(inv1))} urun, beklenen {len(bek_inv)}; fark var")
        if inv_ozellik(inv1) != inv_ozellik(inv0):
            hata.append("price/quantity/sku_on_property degisti")
        if stil_gorsel(api, shop, lid) != sg0:
            hata.append("stil-gorsel baglari degisti")
    R["sonra"] = dict(alan_hata=hata, istek=api.calls, kota=api.remaining)
    if hata:
        R["sonuc"] = "FAIL"
        raise Dur(f"geri okuma FAIL {lid}: {hata}")
    R["sonuc"] = "PASS"


def siparis_say(api, shop, by_ids):
    n_satir, n_makbuz, ofs = 0, 0, 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"was_shipped": "false", "was_canceled": "false", "limit": 100, "offset": ofs}) or {}
        r = d.get("results") or []
        for rc in r:
            k = 0
            for t in rc.get("transactions") or []:
                var = " ".join(str(v.get("formatted_value") or v.get("value") or "") for v in t.get("variations") or [])
                if "PRINT8X10" in (t.get("sku") or "").upper() or (str(t.get("listing_id")) in by_ids and "shipped print" in var.lower()):
                    k += 1
            n_satir += k
            n_makbuz += 1 if k else 0
        ofs += len(r)
        if not r or ofs >= (d.get("count") or 0):
            break
    toplam = (api.get(f"/shops/{shop}/receipts", params={"limit": 1}) or {}).get("count")
    return {"gonderilmemis_makbuz_tarandi": ofs, "baski_satiri": n_satir, "baski_makbuz": n_makbuz, "magaza_toplam_makbuz": toplam}


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


def geri_al(api, shop, lid, yedek, R):
    x0, inv0 = yedek["ilan"], yedek.get("envanter")
    data = {"title": norm(x0.get("title")), "tags": ",".join(x0.get("tags") or []), "description": norm(x0.get("description"))}
    if inv0 is not None:
        data["materials"] = ",".join(x0.get("materials") or [])
        data["shipping_profile_id"] = x0.get("shipping_profile_id")
        api.put_json(f"/listings/{lid}/inventory", envanter_govdesi(inv0, None, baski_cikar=False))
    api.patch(f"/shops/{shop}/listings/{lid}", data)
    y = api.get(f"/listings/{lid}") or {}
    hata = [k for k in ("title", "tags", "description") if not esdeger(ozet(y)[k], ozet(x0)[k], k)]
    if inv0 is not None and imza(api.get(f"/listings/{lid}/inventory") or {}) != imza(inv0):
        hata.append("envanter")
    if inv0 is not None and partner_ids(x0):
        R["panel"] = f"uretim ortagi {partner_ids(x0)} API ile geri yazilmaz: gerekirse panelde ekle"
    R["sonuc"] = "GERI_ALINDI" if not hata else f"FAIL {hata}"
    if hata:
        raise Dur(f"geri alma FAIL {lid}: {hata}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["yedek", "siparis", "yaz", "geri_al"])
    ap.add_argument("--once", required=True)
    ap.add_argument("--sonra", required=True)
    ap.add_argument("--kume", default="cl")
    ap.add_argument("--onay", default="")
    ap.add_argument("--yedek-dizin", default="")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    if a.mod == "yaz" and a.onay != ONAY:
        raise SystemExit(f"DUR: yaz modu --onay {ONAY} ister")
    if a.mod == "geri_al" and (a.onay != ONAY_GERI or not a.yedek_dizin):
        raise SystemExit(f"DUR: geri_al modu --onay {ONAY_GERI} ve --yedek-dizin ister")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sonra = json.load(open(a.sonra))
    once = {str(x["listing_id"]): {"title": norm(x["title"]), "tags": list(x["tags"]), "description": norm(x["description"])}
            for x in json.load(open(a.once))}
    if set(once) != set(sonra) or len(sonra) != 234:
        raise SystemExit(f"HATA: ONCE {len(once)} / SONRA {len(sonra)} ilan kumesi ayni degil")
    by_ids = {k for k, v in sonra.items() if v["aile"] == "yildonumu"}
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
            RAPOR["siparis"] = siparis_say(api, shop, by_ids)
            print("SIPARIS", json.dumps(RAPOR["siparis"]))
            return
        if a.kume == "hepsi" and a.mod != "yedek":
            raise SystemExit("HATA: 'hepsi' yalniz yedek modunda; yazma cl -> pilot -> kalan sirasiyla")
        ids = sorted(sonra) if a.kume == "hepsi" else kume_sec(a.kume, sonra)
        yd = out / "YEDEK"; yd.mkdir(exist_ok=True)
        if a.mod == "geri_al":
            for lid in ids:
                R = {"listing_id": lid}; RAPOR["ilanlar"].append(R)
                geri_al(api, shop, lid, json.load(open(pathlib.Path(a.yedek_dizin) / f"{lid}.json")), R)
            return
        if a.mod == "yaz" and any(i in by_ids for i in ids):
            sp = siparis_say(api, shop, by_ids)
            RAPOR["siparis"] = sp
            if sp["baski_satiri"]:
                raise Dur(f"gonderilmemis baski siparisi var ({sp['baski_satiri']} satir): yazma yok")
        kayma = []
        for i, lid in enumerate(ids, 1):
            kota(api)
            Y = yedek_al(api, shop, lid, sonra[lid]["aile"])
            (yd / f"{lid}.json").write_text(json.dumps(Y, ensure_ascii=False, indent=1), encoding="utf-8")
            cur, hed = ozet(Y["ilan"]), {"title": sonra[lid]["baslik"], "tags": sonra[lid]["etiketler"], "description": sonra[lid]["aciklama"]}
            durum = ("YENI" if all(esdeger(cur[f], hed[f], f) for f in cur)
                     else "ESKI" if all(esdeger(cur[f], once[lid][f], f) for f in cur) else "KAYMA")
            if durum == "KAYMA" or Y["ilan"].get("state") != "active":
                kayma.append({"listing_id": lid, "durum": durum, "state": Y["ilan"].get("state")})
            if i % 25 == 0:
                print(f"[{i}/{len(ids)}] istek {api.calls} kota {api.remaining}", flush=True)
        RAPOR["yedek"] = {"ilan": len(ids), "kayma_ya_da_aktif_degil": kayma, "drive": drive_yukle(yd, f"YEDEK_{a.mod}_{a.kume[:20]}")}
        print("YEDEK", len(ids), "kayma/aktif degil", len(kayma), "|", RAPOR["yedek"]["drive"])
        if a.mod == "yedek":
            return
        H = {}

        def hazirlik_al():
            if "id" not in H:
                H["id"], H["nasil"] = hazirlik_bul(api, shop, olustur=True)
                RAPOR["hazirlik"] = dict(H)
            return H["id"]
        t0 = time.time()
        for n, lid in enumerate(ids, 1):
            R = {"listing_id": lid, "aile": sonra[lid]["aile"], "cift": sonra[lid]["cift"]}
            RAPOR["ilanlar"].append(R)
            bir_ilan(api, shop, lid, sonra[lid], once[lid], out, hazirlik_al, R)
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
