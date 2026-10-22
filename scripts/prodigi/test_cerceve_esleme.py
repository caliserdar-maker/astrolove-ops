"""IS_0044: cerceveli/dijital yonlendirme testleri; ag ve gercek servis yok."""
import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/prodigi"), str(ROOT / "scripts/etsy")]

import order_router as R
from pod_sku import frame_code, parse_sku


def tx(tid, sku):
    return {"transaction_id": tid, "sku": sku, "quantity": 1,
            "price": {"amount": 2000, "divisor": 100}}


def check(name, condition):
    print(("PASS " if condition else "FAIL ") + name)
    if not condition:
        raise AssertionError(name)


work = Path(tempfile.mkdtemp(prefix="cerceve_"))
mapping = work / "map.csv"
with mapping.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["boy", "cerceve", "prodigi_sku", "attr_color", "attr_ek_json"])
    writer.writeheader()
    writer.writerow({"boy": "8x10", "cerceve": "BK", "prodigi_sku": "FAKE-FRAME-8X10",
                     "attr_color": "Black", "attr_ek_json": json.dumps({"finish": "matte"})})
R.CERCEVE_ESLEME = mapping

framed = "POD-ARI_LEO-MB-8x10-FBK"
digital = "POD-ARI_LEO-MB-DIGITAL"
check("cerceveli SKU ayristirma", parse_sku(framed) == ("ARIES_LEO", "MIDNIGHT_BLUE", "8x10")
      and frame_code(framed) == "BK")

receipt = {"receipt_id": "fake-1", "transactions": [tx("p", framed), tx("d", digital)]}
items, other, _ = R.parse_items(receipt)
check("karma sipariste yalniz fiziksel kalem", len(items) == 1 and other == [f"DIJITAL:{digital}"])
check("cerceve esleme ve attributes", items[0]["prodigi_sku"] == "FAKE-FRAME-8X10"
      and items[0]["attributes"] == {"color": "Black", "finish": "matte"})

missing = {"receipt_id": "fake-2", "transactions": [tx("x", "POD-ARI_LEO-MB-8x10-FWH")]}
missing_item = R.parse_items(missing)[0][0]
check("esleme yok fail-closed isareti", missing_item["mapping_error"] is True)

body = R.order_body({"receipt_id": "fake-1", "country_iso": "US"}, items, {framed: "https://invalid.test/a.jpg"})
check("Standard varsayilan", body["shippingMethod"] == "Standard")
check("cerceve govdesi sizing, asset ve attributes", body["items"][0]["sizing"] == "fillPrintArea"
      and body["items"][0]["attributes"]["color"] == "Black"
      and body["items"][0]["assets"][0]["url"].endswith("a.jpg"))


class FakeProdigi(R.Prodigi):
    def __init__(self):
        self.calls = []

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        return 200, {"quotes": [{"shipmentMethod": body["shippingMethod"],
                                  "costSummary": {"items": {"amount": "10"},
                                                  "shipping": {"amount": "5"}}}]}


prod = FakeProdigi()
prod.quote(items, "US")
check("teklif Standard ve ayni cerceve attributes", prod.calls[0][2]["shippingMethod"] == "Standard"
      and prod.calls[0][2]["items"][0]["attributes"]["color"] == "Black")

digital_only = {"receipt_id": "fake-3", "transactions": [tx("d", digital)]}
check("yalniz dijital 0 Prodigi kalemi", R.parse_items(digital_only)[0] == [])
print("SONUC: 8/8 PASS")
