#!/usr/bin/env python3
"""TAKIP DUZELTMESI KURU TESTI (23 Eyl bulgulari). SALT OKUMA.

Prodigi'deki son siparisleri okur, her gonderi icin YENI kodun Etsy'ye ne yazacagini tablo yapar.
Etsy'ye POST YOK; Etsy'den yalniz ilgili receipt okunur (varsa mevcut gonderi karsilastirmasi icin).
Gecmis siparisler icin duzeltme/POST HAZIRLANMAZ (24 Eyl, Serdar musterilere kendisi yazdi); her
siparis icin router'in gecmis-siparis korumasinin (takip.yazma_karari) verecegi karar gosterilir.
Takip linkleri yalniz GET ile erisilebilirlik acisindan denenir (musteri linki calisiyor mu).
Ayrica Etsy OAS'tan createReceiptShipment'in carrier_name/tracking_code aciklamasi kanit olarak alinir.

Cikti: <out>/TAKIP_PLAN.csv + TAKIP_PLAN.md (+ ORNEK_GONDERI.json)
"""
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "etsy"))
import takip  # noqa: E402
import order_router as R  # noqa: E402

OAS_URL = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
SUT = ["prodigi_order", "merchant_ref", "receipt_id", "shipment", "kargo_yontemi", "tasiyici_ad",
       "tasiyici_hizmet", "prodigi_numara", "prodigi_url", "son_ayak_numara", "etsy_carrier_name",
       "etsy_tracking_code", "takip_url", "url_kaynagi", "url_durumu", "eski_davranis_carrier",
       "eski_davranis_url", "degisti_mi", "gerekce", "uyari", "etsy_receipt_utc", "etsy_mevcut_gonderi",
       "router_karari", "router_neden"]
RID_CIPLAK = re.compile(r"^\d{9,12}$")       # elle acilan siparislerde merchantReference = receipt no


def receipt_no(ref):
    """merchantReference -> Etsy receipt no. 'etsy-<rid>-<boy>' (router) ya da ciplak numara (elle)."""
    ref = str(ref or "").strip()
    if ref.startswith("etsy-") and len(ref.split("-")) > 1 and ref.split("-")[1].isdigit():
        return ref.split("-")[1]
    return ref if RID_CIPLAK.match(ref) else ""


def oas_shipment_alanlari(url=OAS_URL):
    try:
        d = requests.get(url, timeout=120).json()
    except Exception as e:
        return {"hata": f"{type(e).__name__}: {e}"[:200]}
    for yol, islemler in (d.get("paths") or {}).items():
        if not yol.endswith("/receipts/{receipt_id}/tracking"):
            continue
        for yontem, op in (islemler or {}).items():
            if yontem != "post":
                continue
            out = {"uc": f"POST {yol}", "operationId": op.get("operationId"), "alanlar": {}}
            for ictyp in ((op.get("requestBody") or {}).get("content") or {}).values():
                for k, v in ((ictyp.get("schema") or {}).get("properties") or {}).items():
                    out["alanlar"][k] = (v or {}).get("description") or (v or {}).get("type") or ""
            return out
    return {"hata": "createReceiptShipment ucu OAS'ta bulunamadi"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default="live", choices=["live", "sandbox"])
    ap.add_argument("--out", default="_out/takip")
    ap.add_argument("--top", type=int, default=50, help="son N Prodigi siparisi")
    ap.add_argument("--url-kontrol", default="acik", choices=["acik", "kapali"])
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

    prod = R.Prodigi(R.load_prodigi_key(a.env), a.env)
    stc, d = prod.call("GET", f"/orders?top={a.top}")      # hasMore/nextUrl kanit icin dogrudan okunur
    orders = (d.get("orders") or []) if stc == 200 else []
    if not orders:
        sys.exit(f"HATA: GET /orders?top={a.top} -> HTTP {stc}, bos (yetki/kota?) - salt okuma, hicbir sey yazilmadi.")
    daha_var = d.get("hasMore")
    R.log(f"Prodigi siparis: {len(orders)} (top={a.top}, hasMore={daha_var})")
    sinir = takip.sinir_ts()

    api = shop = None
    try:
        store = R.TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""),
                             os.environ.get("ETSY_SHARED_SECRET", ""))
        if store.needs_refresh():
            store.refresh()
        api = R.Etsy(store)
        shop = os.environ["ETSY_SHOP_ID"]
    except Exception as e:
        R.log(f"UYARI: Etsy okunamiyor ({type(e).__name__}); mevcut gonderi karsilastirmasi atlanir")

    satirlar, ornek = [], None
    for o in orders:
        ref = str(o.get("merchantReference") or "")
        rid = receipt_no(ref)
        yontem = o.get("shippingMethod") or ""
        for n, sp in enumerate(o.get("shipments") or [], 1):
            bilgi = takip.takip_bilgi(sp)
            if not bilgi["numara"]:
                continue
            ornek = ornek or sp
            plan = takip.etsy_plani(bilgi)
            durum = "kontrol yok"
            if a.url_kontrol == "acik" and plan["takip_url"]:
                try:
                    r = requests.get(plan["takip_url"], timeout=20, allow_redirects=True,
                                     headers={"User-Agent": "astrolove-ops/1.0"})
                    durum = "ok" if r.status_code < 400 else f"HTTP {r.status_code}"
                except Exception as e:
                    durum = type(e).__name__
                time.sleep(0.5)
            mevcut, rec_utc = ("receipt no yok (merchantReference bos/tanimsiz)", "")
            karar, neden = ("yok", "receipt no yok: router bu siparisi STATE'te tutmaz, Etsy'ye yazmaz")
            if rid and not api:
                mevcut, karar, neden = "Etsy okunamadi", "hata", "Etsy okunamadi"
            if api and rid:
                try:
                    rec = api.get(f"/shops/{shop}/receipts/{rid}", ok404=True)
                    if rec is None:
                        mevcut, karar, neden = "receipt 404", "hata", "receipt 404"
                    else:
                        gl = rec.get("shipments") or []
                        mevcut = ("; ".join(f"{g.get('carrier_name')}:{g.get('tracking_code')}" for g in gl)
                                  or "gonderi yok") + f" (is_shipped={bool(rec.get('is_shipped'))})"
                        ts = rec.get("create_timestamp") or rec.get("created_timestamp")
                        rec_utc = takip.utc_metin(ts) if ts else ""
                        karar, neden = takip.yazma_karari(rec, rid, plan, sinir)
                except SystemExit as e:
                    mevcut, karar, neden = f"okunamadi ({str(e)[:60]})", "hata", "receipt okunamadi"
            eski_carrier = bilgi["tasiyici_ad"] or "other"      # ESKI kod: carrier.name dogrudan
            satirlar.append({
                "prodigi_order": o.get("id"), "merchant_ref": ref, "receipt_id": rid, "shipment": n,
                "kargo_yontemi": yontem, "tasiyici_ad": bilgi["tasiyici_ad"],
                "tasiyici_hizmet": bilgi["tasiyici_hizmet"], "prodigi_numara": bilgi["numara"],
                "prodigi_url": bilgi["url"] or "YOK", "son_ayak_numara": bilgi["son_ayak_numara"] or "YOK",
                "etsy_carrier_name": plan["carrier_name"], "etsy_tracking_code": plan["tracking_code"],
                "takip_url": plan["takip_url"] or "YOK", "url_kaynagi": plan["url_kaynagi"],
                "url_durumu": durum, "eski_davranis_carrier": eski_carrier, "eski_davranis_url": "YOK (saklanmiyordu)",
                "degisti_mi": "EVET" if eski_carrier.lower() != plan["carrier_name"] else "hayir",
                "gerekce": plan["gerekce"], "uyari": plan["uyari"], "etsy_receipt_utc": rec_utc,
                "etsy_mevcut_gonderi": mevcut, "router_karari": karar, "router_neden": neden})

    with (out / "TAKIP_PLAN.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT); w.writeheader(); w.writerows(satirlar)
    if ornek:
        (out / "ORNEK_GONDERI.json").write_text(json.dumps(ornek, ensure_ascii=False, indent=1), encoding="utf-8")
    oas = oas_shipment_alanlari()
    (out / "OAS_TRACKING.json").write_text(json.dumps(oas, ensure_ascii=False, indent=1), encoding="utf-8")

    yazar = [x for x in satirlar if x["router_karari"] == "yaz"]
    md = [f"# Takip duzeltmesi kuru testi — {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", "",
          "**SALT OKUMA.** Etsy'ye POST yok, Prodigi'ye yazma yok; yalniz okuma + dosya uretimi.",
          "**Gecmis siparisler icin duzeltme/POST HAZIRLANMADI** (MUSTERI dahil; Serdar musterilere yazdi).", "",
          f"- Prodigi siparis okundu: {len(orders)} (top={a.top}, hasMore={daha_var}) | takip numarali gonderi: {len(satirlar)}",
          f"- Etsy receipt'i okunan: {sum(1 for x in satirlar if x['etsy_receipt_utc'])}/{len(satirlar)}",
          f"- Yeni kodun carrier_name'i eski koddan farkli: {sum(1 for x in satirlar if x['degisti_mi'] == 'EVET')}",
          f"- Prodigi takip linki calisan: {sum(1 for x in satirlar if x['url_durumu'] == 'ok')}/{len(satirlar)}",
          f"- **Router bugun canliya alinsa Etsy'ye yazacagi gonderi: {len(yazar)}/{len(satirlar)}**", "",
          "## Siparis basina: Etsy'de su an / yeni kod ne yazardi / link", "",
          "| prodigi | receipt (acilis UTC) | Etsy'de su an | tasiyici / hizmet | numara | yeni kod carrier_name | eski kod carrier | Prodigi linki | link | router karari |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for x in ({k: str(v).replace("|", "/") for k, v in y.items()} for y in satirlar):   # tablo bozulmasin
        md.append(f"| {x['prodigi_order']} | {x['receipt_id'] or '-'} ({x['etsy_receipt_utc'] or '-'}) | "
                  f"{x['etsy_mevcut_gonderi']} | {x['tasiyici_ad']} / {x['tasiyici_hizmet'] or '-'} | "
                  f"{x['prodigi_numara']} | **{x['etsy_carrier_name']}** | {x['eski_davranis_carrier']} | "
                  f"{x['takip_url']} | {x['url_durumu']} | **{x['router_karari']}**: {x['router_neden']} |")
    md += ["", "Not: Etsy alicinin linkini kendi uretir (carrier_name + tracking_code); createReceiptShipment'ta "
           "URL alani yoktur. 'Prodigi linki' Prodigi'nin verdigi takip sayfasidir.", "",
           "## Gecmis siparis korumasi (kodda)", "",
           f"- Sinir: `takip.YENI_SIPARIS_BASLANGIC_UTC = {takip.YENI_SIPARIS_BASLANGIC_UTC}` UTC; "
           "`--takip-baslangic` yalniz ileri tasir (`takip.sinir_ts`).",
           "- `order_router.py` adim 3 (Etsy'ye yazan TEK yer): POST'tan once receipt okunur, "
           "`takip.yazma_karari` yalniz `yaz` derse tek POST yapilir.",
           "- `gecmis`: receipt sinirdan once acilmis YA DA Etsy'de baska gonderi / is_shipped var -> POST yok, "
           "STATE `atlandi` (kalici, bir daha denenmez).",
           "- `dogrula`: ayni numara zaten kayitli -> POST yok, yalniz dogrulama. `hata`: receipt/zaman okunamadi -> POST yok.",
           "- Bu kosuda karar dagilimi: " + ", ".join(f"{k}={sum(1 for x in satirlar if x['router_karari'] == k)}"
                                                    for k in sorted({x['router_karari'] for x in satirlar})), "",
           "## Etsy OAS: createReceiptShipment alanlari (kanit)", "", "```json",
           json.dumps(oas, ensure_ascii=False, indent=1)[:1500], "```", ""]
    metin = "\n".join(md)
    (out / "TAKIP_PLAN.md").write_text(metin + "\n", encoding="utf-8")
    R.log(metin[:4000])
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n".join(md[:30]) + "\n")


if __name__ == "__main__":
    main()
