"""GOREV 0036 dijital secenek korumasi (ag yok; sahte fis). Dijital kalem ASLA Prodigi'ye gitmez.
D1 --test-receipt, yalniz dijital fis -> siparise ait 0 Prodigi cagrisi (kosu basindaki sabit katalog
   denetimi GET /products/GLOBAL-HPR-* disinda HIC cagri yok) + rapor "DIJITAL - teslim paketi"
D2 canli (sahte), onayli mod: A yalniz dijital (SKU -DIGITAL), B SKU POD ama varyasyon "Digital File" (yanlis SKU),
   C karisik (8x10 + dijital) -> A/B paket yok, C paketinde yalniz 8x10; POST /orders yok; dijital icin quote yok.
Calistir: python3 scripts/prodigi/test_dijital.py"""
import sys, os, json, copy, time, tempfile, io, contextlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R
from pod_sku import make_digital_sku, parse_sku, is_digital_sku
taban = json.load(open(ROOT / "scripts/prodigi/test_receipt_kisisel_taban.json"))
DV = [{"property_id": None, "value_id": None, "formatted_name": "Size", "formatted_value": "Digital File, 5 colors + 5 ratios"}]


def tx(tid, sku, var=()):
    return {"transaction_id": tid, "sku": sku, "quantity": 1, "price": {"amount": 1499, "divisor": 100}, "variations": list(var)}


def rec(rid, txs):
    r = copy.deepcopy(taban); r.update(receipt_id=rid, country_iso="US", is_shipped=False,
                                       created_timestamp=int(time.time()) - 7200, transactions=txs)
    return r


DSKU = make_digital_sku("CANCER_LIBRA", "MIDNIGHT_BLUE")
A = rec(9201, [tx(1, DSKU, DV)])
B = rec(9202, [tx(2, "POD-CAN_LIB-MB-8x10", DV)])
C = rec(9203, [tx(3, "POD-CAN_LIB-DB-8x10"), tx(4, make_digital_sku("CANCER_LIBRA", "DEEP_BLACK"), DV)])
cagri = []


class FP(R.Prodigi):
    def __init__(self, *a):
        self.base = "sahte"

    def call(self, method, path, body=None):
        cagri.append((method, path, json.dumps(body or {})))
        if method == "POST" and path == "/orders":
            raise AssertionError("PRODIGI SIPARISI ACILDI")
        if method == "GET" and path.startswith("/orders?"):
            return 200, {"outcome": "Ok", "orders": [], "hasMore": False}
        if method == "GET" and path.startswith("/products/"):
            return 200, {"product": {"sku": path.split("/")[2]}}
        if method == "POST" and path == "/quotes":
            return 200, {"quotes": [{"shipmentMethod": "Budget", "costSummary": {"items": {"amount": "10"}, "shipping": {"amount": "5"}}}]}
        return 404, {}


class FE:
    remaining = 5000
    def __init__(s, st): pass
    def get(s, *a, **k): return {}
    def post(s, *a): raise AssertionError("ETSY POST")
class FS:
    def __init__(s, *a): pass
    def needs_refresh(s): return False


R.Prodigi = FP; R.load_prodigi_key = lambda e: "x"; R.TokenStore = FS; R.Etsy = FE
R.otomasyonlar = lambda *a, **k: None
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
W = Path(tempfile.mkdtemp(prefix="dijital_"))


def run(ek, ad):
    R.DIKKAT_EK.clear()
    sys.argv = ["r", "--state", str(W / f"{ad}.csv"), "--out", str(W / ad), "--sablonlar",
                str(ROOT / "scripts/prodigi/test_musteri_mesajlari.md")] + ek
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            R.main()
    except SystemExit:
        pass
    return "".join(p.read_text(encoding="utf-8") for p in (W / ad).glob("*.md")) if (W / ad).exists() else buf.getvalue()


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


k("SKU semasi: -DIGITAL parse_sku disi, <=32", parse_sku(DSKU) is None and is_digital_sku(DSKU) and len(DSKU) <= 32, DSKU)
k("parse_items: B (yanlis SKU + Digital varyasyon) gonderilmez", R.parse_items(B)[0] == [], R.parse_items(B))
k("parse_items: C yalniz 8x10", [i["size"] for i in R.parse_items(C)[0]] == ["8x10"])

p = W / "a.json"; p.write_text(json.dumps(A))
cagri.clear()
out1 = run(["--env", "sandbox", "--test-receipt", str(p), "--approve-mode", "off", "--apply"], "d1")
katalog = lambda c: c[0] == "GET" and c[1].startswith("/products/GLOBAL-HPR-")
k("D1 yalniz dijital fis: siparise ait 0 Prodigi cagrisi", not [c for c in cagri if not katalog(c)],
  [c for c in cagri if not katalog(c)][:3])
k("D1 rapor: DIJITAL - teslim paketi", "DIJITAL - teslim paketi" in out1)

R.etsy_receipts = lambda *a, **k: [A, B, C]
cagri.clear()
out2 = run(["--env", "live"], "d2")
pk = sorted(x.name for x in (W / "d2").glob("*.json"))
k("D2 POST /orders yok", not [c for c in cagri if c[0] == "POST" and c[1] == "/orders"])
k("D2 A/B icin paket yok", not [x for x in pk if x.startswith(("9201", "9202"))], pk)
cp = json.loads((W / "d2" / "9203.json").read_text()) if (W / "d2" / "9203.json").exists() else {}
k("D2 C paketi yalniz 8x10", [i["sku"] for i in cp.get("items", [])] == ["POD-CAN_LIB-DB-8x10"], cp.get("items"))
k("D2 dijital SKU hicbir Prodigi govdesinde yok", not [c for c in cagri if "DIGITAL" in c[2] or "DIGITAL" in c[1]])
k("D2 rapor: 3 dijital satiri", out2.count("DIJITAL - teslim paketi") == 3, out2.count("DIJITAL - teslim paketi"))
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
