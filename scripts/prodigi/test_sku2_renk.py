"""Yapi v2 (27 Eyl): renksiz SKU + 'Primary color' varyasyonu. Ag ve gercek servis yok."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/prodigi"), str(ROOT / "scripts/etsy")]

import kisisel_siparis as K
import order_router as R
from pod_sku import parse_sku, parse_tx

R.CERCEVE_ESLEME = ROOT / "data/pod/prodigi_cerceve_esleme.csv"


def tx(tid, sku, renk=None, fmt=None, kisisel=None):
    v = []
    if fmt:
        v.append({"formatted_name": "Digital File, Print or Framed?", "formatted_value": fmt})
    if renk:
        v.append({"formatted_name": "Primary color", "formatted_value": renk})
    v.append({"formatted_name": "Size", "formatted_value": "8×10″ (20×25cm)"})
    if kisisel:
        v.append({"formatted_name": "Personalization", "formatted_value": kisisel})
    return {"transaction_id": tid, "sku": sku, "quantity": 1, "price": {"amount": 4799, "divisor": 100},
            "variations": v}


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise AssertionError(name)


# 1 eski renkli SKU aynen
check("eski SKU", parse_tx(tx(1, "POD-CAN_LIB-MB-8x10")) == ("CANCER_LIBRA", "MIDNIGHT_BLUE", "8x10", None, "POD-CAN_LIB-MB-8x10"))
# 2 yeni baski SKU + renk varyasyonu
p = parse_tx(tx(2, "POD-CAN_LIB-8x10", "Deep Black", "Print"))
check("yeni baski SKU renk varyasyondan", p == ("CANCER_LIBRA", "DEEP_BLACK", "8x10", None, "POD-CAN_LIB-DB-8x10"))
check("yeni SKU parse_sku ile cozulmez (eski kod yanlis renge gitmez)", parse_sku("POD-CAN_LIB-8x10") is None)
# 3 renk yok / bilinmeyen renk -> None (fail-closed)
check("renk yok -> None", parse_tx(tx(3, "POD-CAN_LIB-8x10", None, "Print")) is None)
check("dijital renk degeri -> None", parse_tx(tx(4, "POD-CAN_LIB-8x10", "All 5 colors, Digital", "Print")) is None)

rec = {"receipt_id": "sahte-9", "transactions": [
    tx("a", "POD-CAN_LIB-8x10", "Deep Black", "Print"),
    tx("b", "POD-CAN_LIB-8x10", "Pure White", "Print"),
    tx("c", "POD-CAN_LIB-16x20-FNA", "Champagne Ivory", "Natural Frame"),
    tx("d", "POD-CAN_LIB-8x10-DIGITAL", "All 5 colors, Digital", "Digital File"),
    tx("g", "POD-CAN_LIB-24x36-FGO", "Midnight Blue", "Antique Gold Frame"),
    tx("e", "POD-CAN_LIB-12x16", None, "Print"),
]}
items, other, atl = R.parse_items(rec)
by = {i["transaction_id"]: i for i in items}
check("iki renk ayni SKU: iki kalem, ayri anahtar", by["a"]["sku"] != by["b"]["sku"] and len(items) == 4)
check("antique gold -> CFP + gold", by["g"]["prodigi_sku"] == "GLOBAL-CFP-24x36"
      and by["g"]["attributes"].get("color") == "gold" and not by["g"]["mapping_error"])
check("renk dosyasi dogru (DB)", by["a"]["asset_remote"].endswith("/CANCER_LIBRA/DEEP_BLACK/8x10.jpg"))
check("renk dosyasi dogru (PW)", by["b"]["asset_remote"].endswith("/CANCER_LIBRA/PURE_WHITE/8x10.jpg"))
check("baski -> HPR", by["a"]["prodigi_sku"] == "GLOBAL-HPR-8x10" and not by["a"]["cerceve"])
check("cerceveli -> CFP + natural", by["c"]["prodigi_sku"] == "GLOBAL-CFP-16x20"
      and by["c"]["attributes"].get("color") == "natural" and by["c"]["ed"] == "CHAMPAGNE_IVORY"
      and not by["c"]["mapping_error"])
check("dijital Prodigi'ye gitmez", "d" not in by and any(o.startswith("DIJITAL:") for o in other))
check("renksiz fiziksel kalem gonderilmez", "e" not in by and "POD-CAN_LIB-12x16" in other)
body = R.order_body(rec, items, {i["sku"]: "u" for i in items})
check("siparis govdesi 4 kalem, Standard", len(body["items"]) == 4 and body["shippingMethod"] == "Standard")

# kisisellestirme karti yeni SKU'yu da gorur
rk = {"receipt_id": "sahte-10", "transactions": [
    {**tx("k", "POD-CAN_LIB-8x10", "Warm Parchment", "Print"),
     "variations": tx("k", "POD-CAN_LIB-8x10", "Warm Parchment", "Print")["variations"]
     + [{"formatted_name": "Personalization", "formatted_value": "Cancer name: Emma, Libra name: Noah"}]}]}
kal = K.cevaplar(rk, parse_sku)
check("kisisel: yeni SKU cozuldu (kalem varsa renk WP)", all(k["ed"] == "WARM_PARCHMENT" and k["sku"] == "POD-CAN_LIB-WP-8x10" for k in kal))
print("TUMU PASS")
