#!/usr/bin/env python3
"""TAKIP DUZELTMESI KURU TESTI (23 Eyl bulgulari). SALT OKUMA.

Prodigi'deki son siparisleri okur, her gonderi icin YENI kodun Etsy'ye ne yazacagini tablo yapar.
Etsy'ye POST YOK; Etsy'den yalniz ilgili receipt okunur (varsa mevcut gonderi karsilastirmasi icin).
Takip linkleri yalniz GET ile erisilebilirlik acisindan denenir (musteri linki calisiyor mu).
Ayrica Etsy OAS'tan createReceiptShipment'in carrier_name/tracking_code aciklamasi kanit olarak alinir.

Cikti: <out>/TAKIP_PLAN.csv + TAKIP_PLAN.md (+ ORNEK_GONDERI.json)
"""
import argparse
import csv
import json
import os
import pathlib
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
       "etsy_tracking_code", "etsy_takip_url", "url_kaynagi", "url_durumu", "eski_davranis_carrier",
       "eski_davranis_url", "degisti_mi", "gerekce", "uyari", "etsy_mevcut_gonderi"]


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
    ap.add_argument("--receipt", default="1000000001", help="oneri hazirlanacak receipt (GONDERILMEZ)")
    ap.add_argument("--url-kontrol", default="acik", choices=["acik", "kapali"])
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

    prod = R.Prodigi(R.load_prodigi_key(a.env), a.env)
    # order_router.Prodigi.siparisler() dogrudan LISTE dondurur (status/dict degil).
    orders = prod.siparisler(top=a.top)
    if not orders:
        sys.exit(f"HATA: GET /orders?top={a.top} bos dondu (yetki/kota?) - salt okuma, hicbir sey yazilmadi.")
    R.log(f"Prodigi siparis: {len(orders)} (top={a.top})")

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
        rid = ref.split("-")[1] if ref.startswith("etsy-") and len(ref.split("-")) > 1 else ""
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
            mevcut = ""
            if api and rid:
                try:
                    rec = api.get(f"/shops/{shop}/receipts/{rid}", ok404=True) or {}
                    mevcut = "; ".join(f"{s.get('carrier_name')}:{s.get('tracking_code')}"
                                       for s in (rec.get("shipments") or [])) or "gonderi yok"
                except SystemExit as e:
                    mevcut = f"okunamadi ({str(e)[:60]})"
            eski_carrier = bilgi["tasiyici_ad"] or "other"      # ESKI kod: carrier.name dogrudan
            satirlar.append({
                "prodigi_order": o.get("id"), "merchant_ref": ref, "receipt_id": rid, "shipment": n,
                "kargo_yontemi": yontem, "tasiyici_ad": bilgi["tasiyici_ad"],
                "tasiyici_hizmet": bilgi["tasiyici_hizmet"], "prodigi_numara": bilgi["numara"],
                "prodigi_url": bilgi["url"] or "YOK", "son_ayak_numara": bilgi["son_ayak_numara"] or "YOK",
                "etsy_carrier_name": plan["carrier_name"], "etsy_tracking_code": plan["tracking_code"],
                "etsy_takip_url": plan["takip_url"] or "YOK", "url_kaynagi": plan["url_kaynagi"],
                "url_durumu": durum, "eski_davranis_carrier": eski_carrier, "eski_davranis_url": "YOK (saklanmiyordu)",
                "degisti_mi": "EVET" if eski_carrier.lower() != plan["carrier_name"] else "hayir",
                "gerekce": plan["gerekce"], "uyari": plan["uyari"], "etsy_mevcut_gonderi": mevcut})

    with (out / "TAKIP_PLAN.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT); w.writeheader(); w.writerows(satirlar)
    if ornek:
        (out / "ORNEK_GONDERI.json").write_text(json.dumps(ornek, ensure_ascii=False, indent=1), encoding="utf-8")
    oas = oas_shipment_alanlari()
    (out / "OAS_TRACKING.json").write_text(json.dumps(oas, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# Takip duzeltmesi kuru testi — {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", "",
          "**SALT OKUMA.** Etsy'ye POST yok, Prodigi'ye yazma yok; yalniz okuma + dosya uretimi.", "",
          f"- Prodigi siparis okundu: {len(orders)} | takip numarali gonderi: {len(satirlar)}",
          f"- Etsy carrier_name degisen gonderi: {sum(1 for s in satirlar if s['degisti_mi'] == 'EVET')}",
          f"- takip linki calisan: {sum(1 for s in satirlar if s['url_durumu'] == 'ok')}/{len(satirlar)}", "",
          "## Yeni kodun Etsy'ye yazacagi (gonderi basina)", "",
          "| prodigi | receipt | kargo | tasiyici / hizmet | numara | -> carrier_name | -> numara | link | link durumu | eski carrier | degisti | uyari |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in satirlar:
        md.append(f"| {s['prodigi_order']} | {s['receipt_id']} | {s['kargo_yontemi']} | "
                  f"{s['tasiyici_ad']} / {s['tasiyici_hizmet'] or '-'} | {s['prodigi_numara']} | "
                  f"**{s['etsy_carrier_name']}** | {s['etsy_tracking_code']} | {s['etsy_takip_url']} | "
                  f"{s['url_durumu']} | {s['eski_davranis_carrier']} | {s['degisti_mi']} | {s['uyari'] or '-'} |")
    md += ["", "## Etsy OAS: createReceiptShipment alanlari (kanit)", "", "```json",
           json.dumps(oas, ensure_ascii=False, indent=1)[:1500], "```", ""]

    hedef = [s for s in satirlar if s["receipt_id"] == str(a.receipt)]
    md += [f"## Receipt {a.receipt} icin duzeltme onerisi (GONDERILMEDI)", ""]
    if not hedef:
        md += [f"- Son {a.top} Prodigi siparisinde bu receipt icin takip numarali gonderi bulunamadi; "
               "oneri uretilemedi.", ""]
    for s in hedef:
        md += [f"- Prodigi siparis {s['prodigi_order']} / gonderi {s['shipment']}",
               f"- Etsy'de su an: {s['etsy_mevcut_gonderi']}", "",
               "Onerilen cagri (ONAY BEKLIYOR, calistirilmadi):", "", "```http",
               f"POST /v3/application/shops/<shop_id>/receipts/{a.receipt}/tracking",
               f"tracking_code={s['etsy_tracking_code']}",
               f"carrier_name={s['etsy_carrier_name']}", "send_bcc=true", "```", "",
               f"- Musteri linki: {s['etsy_takip_url']} (durum: {s['url_durumu']}, kaynak: {s['url_kaynagi']})",
               f"- Gerekce: {s['gerekce'] or '-'} | Uyari: {s['uyari'] or '-'}", ""]
    metin = "\n".join(md)
    (out / "TAKIP_PLAN.md").write_text(metin + "\n", encoding="utf-8")
    R.log(metin[:4000])
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n".join(md[:30]) + "\n")


if __name__ == "__main__":
    main()
