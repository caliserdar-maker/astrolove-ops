#!/usr/bin/env python3
"""SALT OKUMA: son siparislerin ozeti (Serdar 28 Eyl talebi; Etsy'ye yazma YOK, mesaj YOK).
Ceker: son N receipt (tarih, kalemler, varyasyonlar, kargo bildirimleri), ilgili ilanlarin
processing_min/max ve kargo profili transit gunleri; taahhut penceresini hesaplar.
Loga MUSTERI BILGISI YAZILMAZ (isim/adres/e-posta yok; id ve takip no maskeli).
Tam JSON + ozet Drive'a cikar (_out/): SIPARIS_OZET.md, receipts_ham.json.
Kullanim: siparis_ozet.py N
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etsy_common import Etsy, TokenStore, log

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
SHOP = os.environ["ETSY_SHOP_ID"]
store = TokenStore(os.environ["TOKEN_FILE"], os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"])
c = Etsy(store)

os.makedirs("_out", exist_ok=True)


def m_id(v):
    s = str(v)
    return "***" + s[-4:]


def m_takip(v):
    s = str(v)
    return "..." + s[-6:] if len(s) > 6 else "***"


def ts(t):
    return dt.datetime.fromtimestamp(int(t), dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if t else "-"


r = c.get(f"/application/shops/{SHOP}/receipts", params={"limit": N, "sort_on": "created", "sort_order": "desc"})
receipts = r.get("results", [])
json.dump(receipts, open("_out/receipts_ham.json", "w"), indent=1)   # Drive'a gider; repoya/loga girmez

profiller = {}
ilanlar = {}
sat = ["# SIPARIS OZETI (salt okuma) " + dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), ""]
for rc in receipts:
    rid = m_id(rc.get("receipt_id"))
    olus = ts(rc.get("created_timestamp") or rc.get("create_timestamp"))
    ulke = rc.get("country_iso", "?")
    sat += [f"## Siparis {rid}", f"- Verilis: {olus} | Ulke: {ulke} | Odendi: {bool(rc.get('is_paid'))} | Kargolandi gorunumu: {bool(rc.get('is_shipped'))}"]
    for tr in rc.get("transactions", []):
        lid = tr.get("listing_id")
        var = "; ".join(f"{v.get('formatted_name')}: {v.get('formatted_value')}" for v in tr.get("variations", []))
        kis = "; ".join(f"{p.get('formatted_name')}: {p.get('formatted_value')}" for p in tr.get("product_data", []) if False)
        sat.append(f"- Kalem: ilan {lid} | {tr.get('title', '')[:60]} | {var}")
        esd = tr.get("expected_ship_date")
        if esd:
            sat.append(f"  Beklenen kargolama (Etsy): {ts(esd)}")
        if lid and lid not in ilanlar:
            il = c.get(f"/application/listings/{lid}")
            ilanlar[lid] = il
            pmin, pmax = il.get("processing_min"), il.get("processing_max")
            spid = il.get("shipping_profile_id")
            sat.append(f"  Ilan taahhudu: hazirlik {pmin}-{pmax} gun | kargo profili {spid}")
            if spid and spid not in profiller:
                try:
                    profiller[spid] = c.get(f"/application/shops/{SHOP}/shipping-profiles/{spid}")
                except Exception as e:
                    profiller[spid] = {"hata": str(e)[:80]}
    for sh in rc.get("shipments", []):
        sat.append(f"- Kargo bildirimi: {sh.get('carrier_name')} takip {m_takip(sh.get('tracking_code'))} | bildirim {ts(sh.get('shipment_notification_timestamp'))}")
    sat.append("")

sat.append("## Kargo profilleri (transit gunleri)")
for spid, p in profiller.items():
    sat.append(f"- Profil {spid}: {p.get('title', p.get('hata', ''))}")
    for d in p.get("shipping_profile_destinations", []):
        sat.append(f"  {d.get('destination_country_iso') or d.get('destination_region')}: min {d.get('min_delivery_days')} - max {d.get('max_delivery_days')} gun")

open("_out/SIPARIS_OZET.md", "w").write("\n".join(sat) + "\n")
store.write()
log(f"ozet hazir: {len(receipts)} siparis, {len(ilanlar)} ilan, {len(profiller)} profil")
print("PASS")
