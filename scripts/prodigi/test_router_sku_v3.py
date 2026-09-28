#!/usr/bin/env python3
"""Router x SKU v3 (390 urunluk CL yapisi) sahte siparis testi - ag YOK, Prodigi'ye gonderim YOK.

Girdi: CL envanteri (canli GET /listings/4570143815/inventory ciktisi ya da ayar77 ONCE/<id>.json).
Her urun icin sahte siparis kalemi kurulur (SKU + 3 varyasyon: format, Primary color, Size) ve
order_router.parse_items / order_body ile yonlendirilir. Beklenen:
  Digital File  -> Prodigi kalemi YOK, 'DIJITAL:<sku>' (dijital teslim akisi)
  Print         -> GLOBAL-HPR-<boy>, cerceve yok, attributes yok
  <X> Frame     -> GLOBAL-CFP-<boy>, attributes.color = gold/black/white/natural
  renk          -> varyasyondaki renk (edisyon) dogru cozulur; pair CANCER_LIBRA; mapping_error yok
Ek: karisik sepet (dijital + baski + cerceve), renk varyasyonu eksik (fail-closed), order_body kalemleri.
--katalog verilirse her Prodigi SKU'su Prodigi katalog CSV'sinde aranir.
Cikis: SONUC PASS/FAIL (+ ozet tablo). Kullanim: test_router_sku_v3.py --inv INV.json [--katalog CSV]
"""
import argparse
import copy
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/prodigi"), str(ROOT / "scripts/etsy")]
import order_router as R  # noqa: E402

FORMAT_ADI = "Digital File, Print or Framed?"
CERCEVE_RENK = {"Antique Gold Frame": ("GO", "gold"), "Black Frame": ("BK", "black"),
                "White Frame": ("WH", "white"), "Natural Frame": ("NA", "natural")}
ED = {"Midnight Blue": "MIDNIGHT_BLUE", "Deep Black": "DEEP_BLACK", "Pure White": "PURE_WHITE",
      "Champagne Ivory": "CHAMPAGNE_IVORY", "Warm Parchment": "WARM_PARCHMENT"}


def envanter_oku(yol):
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    inv = d.get("inventory", d)
    return inv.get("products") or []


def pv(p, ad):
    for v in p.get("property_values") or []:
        if (v.get("property_name") or "").lower() == ad.lower():
            return (v.get("values") or [""])[0]
    return ""


def tx(tid, p, renk_var=True):
    o = [x for x in p.get("offerings") or [] if not x.get("is_deleted")][0]
    pr = o.get("price") or {}
    fiyat = pr if isinstance(pr, dict) else {"amount": int(round(float(pr) * 100)), "divisor": 100}
    var = [{"formatted_name": FORMAT_ADI, "formatted_value": pv(p, FORMAT_ADI)},
           {"formatted_name": "Size", "formatted_value": pv(p, "Size")}]
    if renk_var:
        var.insert(1, {"formatted_name": "Primary color", "formatted_value": pv(p, "Primary color")})
    return {"transaction_id": tid, "sku": p.get("sku"), "quantity": 1, "price": fiyat, "variations": var}


def rec(rid, txs):
    return {"receipt_id": rid, "name": "TEST", "first_line": "x", "zip": "10001", "country_iso": "US",
            "city": "NY", "transactions": txs}


def katalog_skulari(yol):
    if not yol:
        return None
    s = set()
    with open(yol, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            s.update(c.strip() for c in row if c.strip().upper().startswith("GLOBAL-"))
    return {x.upper() for x in s}


def calis(inv_yol, katalog=None):
    urunler = envanter_oku(inv_yol)
    kat = katalog_skulari(katalog)
    kotu, say, ornek = [], Counter(), {}
    if len(urunler) != 390:
        kotu.append(f"urun sayisi {len(urunler)} != 390")
    for i, p in enumerate(urunler, 1):
        fmt, renk, sku = pv(p, FORMAT_ADI), pv(p, "Primary color"), p.get("sku") or ""
        boy = sku.split("-")[2] if sku.count("-") >= 2 else ""
        items, other, atl = R.parse_items(rec(900000 + i, [tx(i, p)]))
        anahtar = f"{fmt} | {renk} | {boy}"
        if fmt == "Digital File":
            if items or other != [f"DIJITAL:{sku}"]:
                kotu.append(f"dijital Prodigi'ye gidiyor/isaretlenmedi: {anahtar} {sku} -> {items} {other}")
            say["Digital File -> dijital teslim"] += 1
            ornek.setdefault("Digital File", f"{sku} -> dijital teslim (Prodigi yok)")
            continue
        if len(items) != 1 or other or atl:
            kotu.append(f"kalem cozulmedi: {anahtar} {sku} -> items {len(items)} other {other}")
            continue
        it = items[0]
        if it["pair"] != "CANCER_LIBRA" or it["ed"] != ED.get(renk) or it["size"] != boy or it["mapping_error"]:
            kotu.append(f"eslesme: {anahtar} {sku} -> pair {it['pair']} ed {it['ed']} size {it['size']} err {it['mapping_error']}")
        if fmt == "Print":
            bek_sku, bek_attr = f"GLOBAL-HPR-{boy}", {}
            if it["cerceve"]:
                kotu.append(f"baskida cerceve: {sku}")
        elif fmt in CERCEVE_RENK:
            kod, cr = CERCEVE_RENK[fmt]
            bek_sku, bek_attr = f"GLOBAL-CFP-{boy}", {"color": cr}
            if it["cerceve"] != kod:
                kotu.append(f"cerceve kodu {sku}: {it['cerceve']} != {kod}")
        else:
            kotu.append(f"bilinmeyen format: {fmt} {sku}"); continue
        if it["prodigi_sku"] != bek_sku or it["attributes"] != bek_attr:
            kotu.append(f"Prodigi urunu {anahtar}: {it['prodigi_sku']} {it['attributes']} != {bek_sku} {bek_attr}")
        if kat is not None and it["prodigi_sku"].upper() not in kat:
            kotu.append(f"katalogda yok: {it['prodigi_sku']}")
        body = R.order_body(rec(900000 + i, []), [it], {it["sku"]: "https://ornek/asset.jpg"})
        bi = body["items"][0]
        if bi["sku"] != bek_sku or bi.get("attributes", {}) != bek_attr or bi["copies"] != 1:
            kotu.append(f"order_body kalemi {sku}: {bi}")
        say[f"{fmt} -> {bek_sku.rsplit('-', 1)[0]}"] += 1
        ornek.setdefault(fmt, f"{sku} + {renk} -> {bek_sku} {bek_attr or ''} (ed {it['ed']})")
    # karisik sepet: dijital + baski + cerceve ayni fiste
    sec = {}
    for p in urunler:
        sec.setdefault(pv(p, FORMAT_ADI), p)
    if {"Digital File", "Print", "Black Frame"} <= set(sec):
        items, other, _ = R.parse_items(rec(990001, [tx(1, sec["Digital File"]), tx(2, sec["Print"]), tx(3, sec["Black Frame"])]))
        if sorted(i["prodigi_sku"].split("-")[1] for i in items) != ["CFP", "HPR"] or len(other) != 1 \
                or not other[0].startswith("DIJITAL:"):
            kotu.append(f"karisik sepet: {[i['prodigi_sku'] for i in items]} {other}")
        # fail-closed: renk varyasyonu yoksa baski kalemi gonderilmez
        items2, other2, _ = R.parse_items(rec(990002, [tx(1, sec["Print"], renk_var=False)]))
        if items2:
            kotu.append("renk varyasyonu yokken kalem gonderildi (fail-closed degil)")
    else:
        kotu.append(f"envanterde beklenen formatlar yok: {sorted(sec)}")
    print("| yonlendirme | adet |\n|---|---|")
    for k, v in sorted(say.items()):
        print(f"| {k} | {v} |")
    for k, v in ornek.items():
        print(f"ornek {k}: {v}")
    print(f"katalog kontrolu: {'yapildi (' + str(len(kat)) + ' SKU)' if kat is not None else 'yok'}")
    if kotu:
        print("HATALAR:\n  " + "\n  ".join(kotu[:30]))
    print("SONUC " + ("PASS" if not kotu else f"FAIL ({len(kotu)})"))
    return not kotu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inv", required=True)
    ap.add_argument("--katalog", default="")
    a = ap.parse_args()
    sys.exit(0 if calis(a.inv, a.katalog or None) else 1)


if __name__ == "__main__":
    main()
