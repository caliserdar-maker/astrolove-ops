#!/usr/bin/env python3
"""Tek pasif dijital ilanda tur degisikligi denemesi: download -> physical (Serdar 22 Eki, BAG EDISYONLARI madde 1; YALNIZ 1 ILAN).

kuru (varsayilan, yazma yok): tam yedek (ilan + envanter + gorseller + dosyalar + ceviriler), referans fiziksel ilanin kargo /
  iade / hazirlik alanlari, planlanan PATCH kademeleri. Ilana ekli dijital dosyalarin adlari YEDEK'e yazilir (Drive varligi
  is akisinda kontrol edilir; kopyasi olmayan ilanda yaz modu calismaz).
yaz (--onay SERDAR_TUR1): updateListing (PATCH) kademeli, ilk basarida durur:
  K1 {type: physical}  K2 + shipping_profile_id (referans)  K3 + return_policy_id (referans)
  Her kademeden sonra GET: state, type, shipping_profile_id. state 'inactive' degilse ANINDA PATCH state=inactive (yayina alma
  yok; CLAUDE.md 7 Eyl olcumu: updateListing taslagi yayina alabiliyor). Sonra dosyalar ve envanter yeniden okunur.
  Geri donus (type=download) YAPILMAZ; raporlanir. Kota tabani 10. Yanit govdeleri yalniz hata mesaji (sir yok).
Cikti: <out>/TUR_YEDEK_<id>.json, TUR_SONUC_<id>.json; log'a ozet."""
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ONAY = "SERDAR_TUR1"
KOTA_TABAN = 10


def kota(api):
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")


def oku(api, shop, lid):
    L = api.get(f"/listings/{lid}", {"includes": "Images,Videos,Translations"}) or {}
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    files = (api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}).get("results") or []
    kota(api)
    return L, inv, files


def ozet(L, inv, files):
    return dict(state=L.get("state"), type=L.get("listing_type"), shipping_profile_id=L.get("shipping_profile_id"),
                return_policy_id=L.get("return_policy_id"), quantity=L.get("quantity"),
                offering_sayisi=sum(len(p.get("offerings") or []) for p in inv.get("products") or []),
                readiness=sorted({o.get("readiness_state_id") for p in inv.get("products") or [] for o in p.get("offerings") or []} - {None}),
                dosya=[f.get("filename") for f in files], gorsel=len(L.get("images") or []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ilan", required=True)
    ap.add_argument("--referans", default="4570143815")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mod", choices=["kuru", "yaz"], default="kuru")
    ap.add_argument("--onay", default="")
    a = ap.parse_args()
    if a.mod == "yaz" and a.onay != ONAY:
        raise SystemExit(f"DUR: yaz icin --onay {ONAY}")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    L, inv, files = oku(api, shop, a.ilan)
    R = api.get(f"/listings/{a.referans}") or {}
    kota(api)
    once = ozet(L, inv, files)
    if once["state"] != "inactive" or once["type"] != "download":
        raise SystemExit(f"DUR: ilan inactive + download degil ({once['state']}, {once['type']})")
    ref = dict(listing_id=a.referans, type=R.get("listing_type"), shipping_profile_id=R.get("shipping_profile_id"),
               return_policy_id=R.get("return_policy_id"))
    (out / f"TUR_YEDEK_{a.ilan}.json").write_text(json.dumps(dict(ilan=L, envanter=inv, dosyalar=files, referans=ref),
                                                             ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"TUR_DOSYA_ADLARI_{a.ilan}.txt").write_text("\n".join(once["dosya"]) + "\n", encoding="utf-8")
    kademe = [("K1", {"type": "physical"}),
              ("K2", {"type": "physical", "shipping_profile_id": ref["shipping_profile_id"]}),
              ("K3", {"type": "physical", "shipping_profile_id": ref["shipping_profile_id"], "return_policy_id": ref["return_policy_id"]})]
    print(f"ONCE {json.dumps(once, ensure_ascii=False)}\nREFERANS {json.dumps(ref)}\nPLAN {[(k_, v) for k_, v in kademe]}", flush=True)
    if a.mod == "kuru":
        print("KURU: yazma yok", flush=True)
        return
    sonuc = dict(once=once, referans=ref, kademeler=[])
    for ad, veri in kademe:
        if None in veri.values():
            sonuc["kademeler"].append(dict(kademe=ad, atlandi="referansta alan bos")); continue
        try:
            api.patch(f"/shops/{shop}/listings/{a.ilan}", {k_: str(v) for k_, v in veri.items()})
            durum, hata = "OK", ""
        except SystemExit as e:   # etsy_common hata durumunu SystemExit("HATA: ...") ile bildirir
            if "429" in str(e):
                raise
            durum, hata = "HATA", str(e)[:400]
        kota(api)
        L2, inv2, files2 = oku(api, shop, a.ilan)
        sonra = ozet(L2, inv2, files2)
        geri = None
        if sonra["state"] != "inactive":
            try:
                api.patch(f"/shops/{shop}/listings/{a.ilan}", {"state": "inactive"}); geri = "state inactive'e geri alindi"
            except SystemExit as e:
                geri = f"GERI ALINAMADI: {str(e)[:200]}"
            sonra["state_geri_sonrasi"] = (api.get(f"/listings/{a.ilan}") or {}).get("state")
        sonuc["kademeler"].append(dict(kademe=ad, gonderilen=veri, durum=durum, hata=hata, sonra=sonra, state_geri=geri))
        print(f"{ad} {durum} {hata} | SONRA {json.dumps(sonra, ensure_ascii=False)}" + (f" | {geri}" if geri else ""), flush=True)
        if durum == "OK":
            break
    son = sonuc["kademeler"][-1].get("sonra", {})
    sonuc["sonuc"] = dict(tur_degisti=son.get("type") == "physical", state_inactive_kaldi=all(
        (x.get("sonra") or {}).get("state") == "inactive" for x in sonuc["kademeler"] if x.get("sonra")),
        dosya_kaybi=sorted(set(once["dosya"]) - set(son.get("dosya") or [])))
    (out / f"TUR_SONUC_{a.ilan}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SONUC", json.dumps(sonuc["sonuc"], ensure_ascii=False), f"| istek {api.calls} | kota {api.remaining}", flush=True)


if __name__ == "__main__":
    main()
