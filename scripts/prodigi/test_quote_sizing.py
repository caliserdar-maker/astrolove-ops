"""Prodigi /quotes govdesinde 'sizing' YOK, siparis govdesinde (order_body) VAR (29 Eyl: quotes UnknownField).
Calistir: python3 scripts/prodigi/test_quote_sizing.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import order_router as R

gov = []
class P(R.Prodigi):
    def __init__(s): s.base = "sahte"; s.shipping_method = "Standard"
    def call(s, m, p, b=None):
        gov.append((m, p, b))
        return 200, {"quotes": [{"shipmentMethod": "Standard", "costSummary": {"items": {"amount": "10"}, "shipping": {"amount": "5"}}}]}

it = {"prodigi_sku": "GLOBAL-CFP-8X10", "qty": 1, "attributes": {"color": "black"}}
maliyet, hata, _ = P().quote([it], "US")
q = gov[-1][2]["items"][0]
rc = {"receipt_id": 1, "name": "x", "first_line": "a", "city": "c", "zip": "1", "country_iso": "US", "state": "NY", "transactions": []}
o = R.order_body(rc, [dict(it, transaction_id=5, sku="POD-ARI_LEO-8x10-FBK", size="8x10")], {"POD-ARI_LEO-8x10-FBK": "https://x"})
k = [("quote HTTP 200 -> maliyet", maliyet == round(15 + R.EKLER_USD, 2)),
     ("quote govdesinde sizing yok", "sizing" not in q and q["sku"] == "GLOBAL-CFP-8X10" and q["attributes"] == {"color": "black"}),
     ("siparis govdesinde sizing var", o["items"][0].get("sizing") == "fillPrintArea"),
     ("prodigi_item degismedi (sizing var)", R.prodigi_item(it).get("sizing") == "fillPrintArea")]
for ad, ok in k:
    print(("PASS " if ok else "FAIL ") + ad)
print(f"{sum(ok for _, ok in k)}/{len(k)} PASS"); sys.exit(0 if all(ok for _, ok in k) else 1)
