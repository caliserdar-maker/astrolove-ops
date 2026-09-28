#!/usr/bin/env python3
"""SALT OKUMA: bir Prodigi siparisini okur, kaynagini/urununu/maliyetini raporlar ve son N siparisle
(ozellikle verilen bir karsilastirma siparisiyle) ayni urun/ulke/tarih cakismasini arar.

Yalniz GET: Prodigi /orders/{id}, /orders?top=N; Etsy /shops/{shop}/receipts/{id} (varsa).
Hicbir yere yazmaz; rapor yalniz loga/step summary'ye basilir. Tam adres, isim, e-posta, telefon basilmaz.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "etsy"))
import order_router as R  # noqa: E402


def ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def dosya_adi(url):
    """Asset URL'sinden dosya adi (Drive linkinde ad yoksa 'drive id ...' kisaltmasi); tam URL basilmaz."""
    if not url:
        return "-"
    u = urlparse(url)
    q = parse_qs(u.query)
    if "id" in q:
        return f"{u.netloc} id={q['id'][0][:10]}…"
    ad = u.path.rstrip("/").split("/")[-1]
    return f"{u.netloc}/…/{ad}" if ad else u.netloc


def ozet(o):
    rc = o.get("recipient") or {}
    ad = rc.get("address") or {}
    st = o.get("status") or {}
    items = []
    for k in o.get("items") or []:
        items.append({"sku": k.get("sku"), "adet": k.get("copies"), "sizing": k.get("sizing"),
                      "attributes": k.get("attributes") or {}, "kalem_ref": k.get("merchantReference"),
                      "assets": [{"alan": a.get("printArea"), "dosya": dosya_adi(a.get("url")),
                                  "md5": a.get("md5Hash") or "-"} for a in k.get("assets") or []]})
    charges = []
    for c in o.get("charges") or []:
        tc = c.get("totalCost") or {}
        charges.append({"toplam": f"{tc.get('amount')} {tc.get('currency')}",
                        "kalemler": [f"{(i.get('description') or i.get('itemSku') or '-')}: "
                                     f"{(i.get('cost') or {}).get('amount')} {(i.get('cost') or {}).get('currency')}"
                                     for i in c.get("items") or []]})
    return {"id": o.get("id"), "olusturma": o.get("created"), "son_guncelleme": o.get("lastUpdated"),
            "durum": st.get("stage"), "sorun": st.get("issues") or [], "detay": st.get("details") or {},
            "merchantReference": o.get("merchantReference") or "", "idempotencyKey": o.get("idempotencyKey") or "",
            "callbackUrl_var": bool(o.get("callbackUrl")), "metadata": o.get("metadata") or {},
            "packingSlip_var": bool(o.get("packingSlip")), "branding_var": bool(o.get("branding")),
            "kargo_yontemi": o.get("shippingMethod"), "ulke": ad.get("countryCode"),
            "sehir": ad.get("townOrCity"), "eyalet": ad.get("stateOrCounty"),
            "kalemler": items, "ucretler": charges,
            "gonderiler": [{"tasiyici": (s.get("carrier") or {}).get("name"),
                            "hizmet": (s.get("carrier") or {}).get("service"),
                            "numara": (s.get("tracking") or {}).get("number"),
                            "sevk": s.get("dispatchDate"), "durum": s.get("status")}
                           for s in o.get("shipments") or []]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="live")
    ap.add_argument("--siparis", required=True)
    ap.add_argument("--kiyas", default="", help="karsilastirilacak Prodigi siparisi")
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--gun", type=int, default=7, help="tarih yakinligi penceresi (gun)")
    a = ap.parse_args()

    prod = R.Prodigi(R.load_prodigi_key(a.env), a.env)
    rapor = {}
    for oid in [a.siparis] + ([a.kiyas] if a.kiyas else []):
        stc, d = prod.call("GET", f"/orders/{oid}")
        if stc != 200 or not d.get("order"):
            sys.exit(f"HATA: GET /orders/{oid} -> HTTP {stc}: {str(d)[:200]} (salt okuma, yazma yok)")
        rapor[oid] = ozet(d["order"])

    stc, d = prod.call("GET", f"/orders?top={a.top}")
    liste = (d.get("orders") or []) if stc == 200 else []
    hedef = rapor[a.siparis]
    h_sku = {k["sku"] for k in hedef["kalemler"]}
    h_md5 = {x["md5"] for k in hedef["kalemler"] for x in k["assets"] if x["md5"] != "-"}
    h_t = ts(hedef["olusturma"])
    cakisma = []
    for o in liste:
        if o.get("id") == a.siparis:
            continue
        z = ozet(o)
        ayni_sku = h_sku & {k["sku"] for k in z["kalemler"]}
        ayni_md5 = h_md5 & {x["md5"] for k in z["kalemler"] for x in k["assets"] if x["md5"] != "-"}
        ayni_ulke = z["ulke"] == hedef["ulke"]
        t = ts(z["olusturma"])
        fark = abs((t - h_t).total_seconds()) / 86400 if (t and h_t) else None
        yakin = fark is not None and fark <= a.gun
        if ayni_md5 or (ayni_sku and ayni_ulke) or (ayni_sku and yakin):
            cakisma.append({"id": z["id"], "ref": z["merchantReference"], "olusturma": z["olusturma"],
                            "durum": z["durum"], "ulke": z["ulke"], "sehir": z["sehir"],
                            "ayni_sku": sorted(ayni_sku), "ayni_gorsel_md5": sorted(ayni_md5),
                            "ayni_ulke": ayni_ulke, "gun_farki": round(fark, 2) if fark is not None else None,
                            "ayni_sehir": z["sehir"] == hedef["sehir"]})

    etsy = {}
    if a.kiyas:
        ref = rapor[a.kiyas]["merchantReference"]
        rid = ref.split("-")[1] if ref.startswith("etsy-") else (ref if ref.isdigit() else "")
        if rid:
            try:
                store = R.TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""),
                                     os.environ.get("ETSY_SHARED_SECRET", ""))
                if store.needs_refresh():
                    store.refresh()
                api = R.Etsy(store)
                r = api.get(f"/shops/{os.environ['ETSY_SHOP_ID']}/receipts/{rid}", ok404=True) or {}
                etsy = {"receipt": rid, "ulke": r.get("country_iso"), "sehir": r.get("city"),
                        "acilis_ts": r.get("create_timestamp"),
                        "kalemler": [{"sku": t.get("sku"), "adet": t.get("quantity"), "baslik": (t.get("title") or "")[:70],
                                      "varyasyon": [f"{v.get('formatted_name')}={v.get('formatted_value')}"
                                                    for v in t.get("variations") or []]}
                                     for t in r.get("transactions") or []]}
            except (SystemExit, KeyError) as e:
                etsy = {"receipt": rid, "hata": str(e)[:120]}

    cikti = {"siparis": hedef, "kiyas": rapor.get(a.kiyas), "kiyas_etsy": etsy,
             "liste": {"okunan": len(liste), "hasMore": d.get("hasMore") if stc == 200 else f"HTTP {stc}",
                       "gun_penceresi": a.gun},
             "cakisma": cakisma}
    metin = json.dumps(cikti, ensure_ascii=False, indent=1, default=str)
    print("=== SIPARIS_KIYAS_BASLA ===")
    print(metin)
    print("=== SIPARIS_KIYAS_BITTI ===")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("```json\n" + metin + "\n```\n")


if __name__ == "__main__":
    main()
