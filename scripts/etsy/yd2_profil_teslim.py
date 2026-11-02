#!/usr/bin/env python3
"""YD 2. asama kargo profili (Serdar 2 Kas karar 4): profil 318080539024'te YALNIZ AU hedefi teslim 5-10 -> 7-22 gun ve profil adi
"BY Print Worldwide". Diger hedefler, ucretler, tasiyici ve isleme suresi DEGISMEZ. Ilanlardan (metin "checkout'ta gorun") ONCE yazilir.
Modlar: kontrol (SALT OKUMA) | yaz (--onay SERDAR_YD2_PROFIL) | geri-al (--onay SERDAR_YD2_PROFIL_GERI_AL; AU 5-10 + eski ad).
Kapilar: profil tam 1 AU hedefi (destination_country_iso AU); AU tasiyicisiz (shipping_carrier_id bos / 0: teslim gunleri ancak
tasiyicisiz hedefte yazilabilir); AU simdi (5, 10) [yaz] ya da (7, 22) [ZATEN]; profili kullanan ilanlarin hepsi YD 78 listesinde
(5 durum taranir; disarida kullanan varsa DUR). Yazim: updateShopShippingProfileDestination (AU; govde canli hedeften, yalniz gunler
degisir) + updateShopShippingProfile (yalniz title). Geri okuma: AU (7, 22), ad yeni, diger tum hedefler ve profil alanlari once ile
ayni (ad haric); tutmazsa otomatik geri alma (AU 5-10 + eski ad) ve FAIL. Istek (kod sayimi): kontrol 1 + tarama ~5-10; yaz +2 PUT +1 GET.
Cikti <out>/SONUC.json (once / sonra profil)."""
import argparse
import csv
import json
import os
import pathlib
import sys
import traceback

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import yd_yapi_kuru as K  # noqa: E402
import yd_yapi_yaz as W  # noqa: E402  (hedef_govde: canli hedeften govde)

PROFIL = "318080539024"
ONAY = {"yaz": "SERDAR_YD2_PROFIL", "geri-al": "SERDAR_YD2_PROFIL_GERI_AL"}
ESKI_AU, YENI_AU = (5, 10), (7, 22)
YENI_AD = "BY Print Worldwide"


def au_bul(p):
    au = [d for d in p.get("shipping_profile_destinations") or [] if d.get("destination_country_iso") == "AU"]
    return au


def gun(d):
    return (d.get("min_delivery_days"), d.get("max_delivery_days"))


def calis(api, shop, a):
    once = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
    R = dict(mod=a.mod, profil=PROFIL, ad_once=once.get("title"), once=once)
    au = au_bul(once)
    if len(au) != 1:
        return dict(R, sonuc="DUR", neden=f"AU hedefi {len(au)} (1 beklenir)")
    d = au[0]
    if d.get("shipping_carrier_id"):
        return dict(R, sonuc="DUR", neden=f"AU tasiyicili ({d.get('shipping_carrier_id')}); teslim gunleri yazilamaz")
    hedef_gun, hedef_ad = (YENI_AU, YENI_AD) if a.mod != "geri-al" else (ESKI_AU, a.eski_ad)
    R.update(au_once=gun(d))
    if gun(d) == hedef_gun and once.get("title") == hedef_ad:
        return dict(R, sonuc="ZATEN")
    if gun(d) not in (ESKI_AU, YENI_AU):
        return dict(R, sonuc="KAYMA", neden=f"AU {gun(d)} beklenen degil")
    kim = K.kullananlar(api, shop, PROFIL)
    yd = {r["listing_id"] for r in csv.DictReader(open(a.liste, encoding="utf-8-sig"))}
    disari = sorted({x for x, _ in kim} - yd)
    R.update(kullanan=len(kim), yd_disi=disari)
    if disari:
        return dict(R, sonuc="DUR", neden=f"profili YD disinda {len(disari)} ilan kullaniyor")
    if a.mod == "kontrol":
        return dict(R, sonuc="PLAN", plan=dict(au=f"{gun(d)} -> {hedef_gun}", ad=f"{once.get('title')} -> {hedef_ad}"))
    if api.remaining is not None and api.remaining < 6 + E.KOTA_SINIRI:
        return dict(R, sonuc="KOTA", neden=f"kalan {api.remaining}")
    yazildi = []
    try:
        if gun(d) != hedef_gun:
            g = W.hedef_govde(d, K.para(d.get("primary_cost")), K.para(d.get("secondary_cost")))
            g["min_delivery_days"], g["max_delivery_days"] = hedef_gun
            api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/{d['shipping_profile_destination_id']}", g)
            yazildi.append("AU")
        if once.get("title") != hedef_ad:
            api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}", {"title": hedef_ad})
            yazildi.append("ad")
        sonra = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
        R.update(sonra=sonra, yazildi=yazildi)
        neden = dogrula(once, sonra, hedef_gun, hedef_ad)
        if neden:
            raise RuntimeError("; ".join(neden))
        return dict(R, sonuc="TAMAM")
    except (Exception, SystemExit) as e:   # noqa: BLE001
        R.update(sonuc="FAIL", neden=f"{type(e).__name__}: {str(e)[:300]}", iz=traceback.format_exc()[-600:])
        if yazildi:
            try:
                g = W.hedef_govde(d, K.para(d.get("primary_cost")), K.para(d.get("secondary_cost")))
                g["min_delivery_days"], g["max_delivery_days"] = gun(d)
                api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/{d['shipping_profile_destination_id']}", g)
                api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}", {"title": once.get("title")})
                g2 = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
                R["geri_alma"] = "TAMAM" if not dogrula(once, g2, gun(d), once.get("title")) else "OKUMA TUTMADI"
            except (Exception, SystemExit) as e2:   # noqa: BLE001
                R["geri_alma"] = f"FAIL {type(e2).__name__}: {str(e2)[:200]}"
        return R


def dogrula(once, sonra, hedef_gun, hedef_ad):
    """AU hedef gunlerde, ad hedefte; diger her sey once ile ayni."""
    neden = []
    if sonra.get("title") != hedef_ad:
        neden.append(f"ad {sonra.get('title')}")
    h0 = {x["shipping_profile_destination_id"]: x for x in once.get("shipping_profile_destinations") or []}
    h1 = {x["shipping_profile_destination_id"]: x for x in sonra.get("shipping_profile_destinations") or []}
    if set(h0) != set(h1):
        neden.append("hedef kumesi degisti")
    for i, x in h0.items():
        y = h1.get(i) or {}
        if x.get("destination_country_iso") == "AU":
            if gun(y) != hedef_gun:
                neden.append(f"AU {gun(y)}")
            x = {k: v for k, v in x.items() if k not in ("min_delivery_days", "max_delivery_days")}
            y = {k: v for k, v in y.items() if k not in ("min_delivery_days", "max_delivery_days")}
        if x != y:
            neden.append(f"hedef {i} degisti")
    yan = lambda p: {k: v for k, v in p.items() if k not in ("title", "shipping_profile_destinations", "shipping_profile_upgrades")}  # noqa: E731
    if yan(once) != yan(sonra):
        neden.append("profil alanlari degisti")
    return neden


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["kontrol", "yaz", "geri-al"])
    ap.add_argument("--onay", default=""); ap.add_argument("--eski-ad", default="BY Print 8x10 Worldwide")
    ap.add_argument("--liste", default=str(KOK.parents[1] / "data/pod/yd78_ids.csv")); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.mod in ONAY and a.onay != ONAY[a.mod]:
        raise SystemExit(f"DUR: {a.mod} icin --onay {ONAY[a.mod]}")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = E.Etsy(store)
    if a.mod == "kontrol":
        K.K.salt_okur(api)
    try:
        r = calis(api, os.environ["ETSY_SHOP_ID"], a)
    except (Exception, SystemExit) as e:   # noqa: BLE001
        r = dict(sonuc="HATA", neden=f"{type(e).__name__}: {str(e)[:300]}", iz=traceback.format_exc()[-600:])
    r.update(istek=api.calls, kota=api.remaining)
    (out / "SONUC.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"::notice::YD2 PROFIL {a.mod}: {r['sonuc']} {r.get('neden', '')} | istek {api.calls} | kota {api.remaining}", flush=True)
    return 0 if r["sonuc"] in ({"PLAN", "ZATEN"} if a.mod == "kontrol" else {"TAMAM", "ZATEN"}) else 1


if __name__ == "__main__":
    sys.exit(main())
