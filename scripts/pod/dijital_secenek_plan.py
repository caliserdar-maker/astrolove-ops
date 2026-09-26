#!/usr/bin/env python3
"""GOREV 0036 md.2 - POD ilanina "Digital File" secenegi: KURU KOSU (Etsy'ye YAZMA YOK).
etsy <ilan_id> <cikti.json> : getListingsByListingIds includes=Inventory,Images - YALNIZ API anahtari (OAuth yok, kilit yok).
plan <cikti.json>           : Size listesine ILK deger ETIKET, 5 rengin hepsinde FIYAT; SKU pod_sku.make_digital_sku
                              (POD-<S1>_<S2>-<ED2>-DIGITAL). Diger boy/fiyat/SKU/adet/gorunurluk AYNEN.
  Cikti: out/DIJITAL_SECENEK_DIFF_CL.csv (renk, boy, sku, eski_fiyat, yeni_fiyat, durum)
         out/DIJITAL_SECENEK_PUT_TASLAK.json (updateListingInventory govdesi TASLAGI - gonderilmez)
  PASS: 5 YENI + 80 AYNI, 0 DEGISTI/SILINDI, SKU <= 32, SKU tekil."""
import csv
import json
import os
import sys
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK.parent / "etsy"))
from pod_sku import MAX_LEN, make_digital_sku, parse_sku  # noqa: E402

ETIKET = "Digital File, 5 colors + 5 ratios"
FIYAT = 14.99
OUT = Path("out")


def para(p):
    return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2) if isinstance(p, dict) else round(float(p or 0), 2)


def pv(pr, ad):
    return next((x for x in pr.get("property_values") or [] if (x.get("property_name") or "").lower() in ad), None)


def anahtar(pr):
    r, b = pv(pr, ("primary color", "color")), pv(pr, ("size",))
    return ((r or {}).get("values") or [""])[0], ((b or {}).get("values") or [""])[0]


def kopya_pv(x, degerler=None):
    d = {"property_id": x.get("property_id"), "values": list(degerler or x.get("values") or [])}
    for k in ("property_name", "scale_id"):
        if x.get(k):
            d[k] = x[k]
    if not degerler and x.get("value_ids"):
        d["value_ids"] = list(x["value_ids"])
    return d


def kopya_off(o, fiyat=None):
    d = {"price": para(o.get("price")) if fiyat is None else fiyat, "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
    if o.get("readiness_state_id"):
        d["readiness_state_id"] = o["readiness_state_id"]
    return d


def plan(inv):
    eski = inv.get("products") or []
    renkler = list(dict.fromkeys(anahtar(p)[0] for p in eski))
    yeni = []
    for renk in renkler:
        ornek = next(p for p in eski if anahtar(p)[0] == renk)
        pair, ed, _ = parse_sku(ornek.get("sku")) or (None, None, None)
        if not pair:
            raise SystemExit(f"HATA: {renk} SKU cozulemedi: {ornek.get('sku')}. DUR.")
        pvs = [kopya_pv(x, [ETIKET] if (x.get("property_name") or "").lower() == "size" else None) for x in ornek["property_values"]]
        yeni.append({"sku": make_digital_sku(pair, ed), "property_values": pvs, "offerings": [kopya_off(ornek["offerings"][0], FIYAT)]})
    mevcut = [{"sku": p.get("sku") or "", "property_values": [kopya_pv(x) for x in p.get("property_values") or []],
               "offerings": [kopya_off(o) for o in p.get("offerings") or []]} for p in eski]
    body = {"products": yeni + mevcut}
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if inv.get(k):
            body[k] = list(inv[k])
    return body


def diff(inv, body):
    once = {anahtar(p): (p.get("sku"), para(p["offerings"][0].get("price")), p["offerings"][0].get("quantity"),
                         bool(p["offerings"][0].get("is_enabled"))) for p in inv.get("products") or []}
    sonra = {anahtar(p): (p["sku"], p["offerings"][0]["price"], p["offerings"][0]["quantity"], p["offerings"][0]["is_enabled"])
             for p in body["products"]}
    rows = []
    for k in list(sonra) + [k for k in once if k not in sonra]:
        a, b = once.get(k), sonra.get(k)
        durum = "YENI" if a is None else "SILINDI" if b is None else "AYNI" if a == b else "DEGISTI"
        rows.append({"renk": k[0], "boy": k[1], "sku": (b or a)[0], "eski_fiyat": a[1] if a else "",
                     "yeni_fiyat": b[1] if b else "", "durum": durum})
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    if sys.argv[1] == "etsy":
        k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        for v in (k_, s_):
            print(f"::add-mask::{v}")
        r = requests.get("https://openapi.etsy.com/v3/application/listings/batch", headers={"x-api-key": f"{k_}:{s_}"}, timeout=60,
                         params={"listing_ids": sys.argv[2], "includes": "Inventory,Images"})
        r.raise_for_status()
        Path(sys.argv[3]).write_text(json.dumps((r.json().get("results") or [{}])[0], ensure_ascii=False))
        print(f"etsy: 1 cagri, kota {r.headers.get('x-remaining-today')}")
        return
    L = json.loads(Path(sys.argv[2]).read_text())
    inv = L.get("inventory") or L
    body = plan(inv)
    rows = diff(inv, body)
    with open(OUT / "DIJITAL_SECENEK_DIFF_CL.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (OUT / "DIJITAL_SECENEK_PUT_TASLAK.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
    say = {d: sum(1 for r in rows if r["durum"] == d) for d in ("YENI", "AYNI", "DEGISTI", "SILINDI")}
    skus = [p["sku"] for p in body["products"]]
    etiket_max = max(len(anahtar(p)[1]) for p in inv.get("products") or [])
    ok = say == {"YENI": 5, "AYNI": 80, "DEGISTI": 0, "SILINDI": 0} and len(set(skus)) == len(skus) and max(map(len, skus)) <= MAX_LEN
    ozet = {"durum": "PASS" if ok else "FAIL", "sayim": say, "urun": len(skus), "ilk_deger": anahtar(body["products"][0])[1],
            "etiket_uzunluk": len(ETIKET), "mevcut_en_uzun_etiket": etiket_max, "state": L.get("state"),
            "on_property": {k: body.get(k) for k in ("price_on_property", "sku_on_property", "quantity_on_property")}}
    (OUT / "DIJITAL_SECENEK_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    print("OZET " + json.dumps(ozet, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
