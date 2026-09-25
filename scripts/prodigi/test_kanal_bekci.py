"""Kanal bekcisi testi (ag yok; Prodigi HTTP katmani + Etsy sahte). YALNIZ UYARI, Prodigi'ye yazma yok.
K1 kisisel + kanal siparisi (pause, InProgress/NotStarted) -> ACIL (DIKKAT + hata + ::error)
K2 kisisel + kanal siparisi Complete -> ACIL
K4 kisisellestirmesiz + kanal siparisi -> uyari yok
K5 kisisel + kendi etsy-* siparisimiz -> uyari yok
K6 kisisel + Prodigi'de kayit yok -> yalniz ISIM_BEKLIYOR
Hicbir kosuda Prodigi POST (iptal/siparis) ve /actions cagrisi yok. Ikinci kosu: tekrar bildirim yok.
Calistir: python3 scripts/prodigi/test_kanal_bekci.py"""
import sys, os, json, copy, csv, time, tempfile, io, contextlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R
taban = json.load(open(ROOT / "scripts/prodigi/test_receipt_kisisel_taban.json"))
SABLON = str(ROOT / "scripts/prodigi/test_musteri_mesajlari.md")


def rec(rid, sku, alanlar, ulke="US"):
    r = copy.deepcopy(taban); r["receipt_id"] = rid; r["country_iso"] = ulke; r["is_shipped"] = False
    r["created_timestamp"] = int(time.time()) - 7200
    r["transactions"] = [{"transaction_id": rid * 10, "sku": sku, "quantity": 1, "price": {"amount": 3499, "divisor": 100},
                          "variations": [{"property_id": None, "value_id": None, "formatted_name": q, "formatted_value": v}
                                         for q, v in alanlar]}]
    return r


K3 = [("Name under Aries", "Mia"), ("Name under Leo", "Tom"), ("Your message", "Always")]
REC = [rec(9101, "POD-ARI_LEO-MB-8x10", K3), rec(9102, "POD-ARI_LEO-DB-A4", K3),
       rec(9104, "POD-ARI_LEO-MB-12x16", []), rec(9105, "POD-ARI_LEO-WP-8x10", K3), rec(9106, "POD-ARI_LEO-CI-8x10", K3)]


def kanal_siparis(oid, rid, stage="InProgress"):
    return {"id": oid, "created": "2026-09-25T10:00:00Z", "merchantReference": str(rid),
            "status": {"stage": stage, "issues": [], "details": {"downloadAssets": "NotStarted"}},
            "items": [{"merchantReference": str(rid * 10), "sku": "GLOBAL-HPR-8X10"}],
            "metadata": {"SalesChannelId": "x", "RutterOrderId": "y", "MerchantId": "z"}}


class Sahte:
    def __init__(s):
        s.orders = {o["id"]: o for o in (kanal_siparis("ord_K1", 9101), kanal_siparis("ord_K2", 9102, "Complete"),
                                           kanal_siparis("ord_K4", 9104))}
        own = kanal_siparis("ord_K5", 9105); own["merchantReference"] = "etsy-9105-8x10"; own.pop("metadata")
        s.orders["ord_K5"] = own
        s.cagri = []

    def call(s, method, path, body=None):
        s.cagri.append((method, path))
        if method == "GET" and path.startswith("/orders?"):
            return 200, {"outcome": "Ok", "orders": [o for o in s.orders.values() if o["status"]["stage"] != "Cancelled"],
                         "hasMore": False}
        if method == "GET" and path.startswith("/orders/"):
            oid = path.split("/")[2]
            return 200, {"outcome": "Ok", "order": s.orders[oid]}
        if method == "GET" and path.startswith("/products/"):
            return 200, {"product": {"sku": path.split("/")[2]}}
        if method == "POST" and path == "/quotes":
            return 200, {"quotes": [{"shipmentMethod": "Budget", "costSummary": {"items": {"amount": "10"}, "shipping": {"amount": "5"}}}]}
        if method == "POST" and path == "/orders":
            raise AssertionError("PRODIGI SIPARISI ACILDI")
        raise AssertionError(f"beklenmeyen cagri {method} {path}")


S = Sahte()
Gercek = R.Prodigi


class FP(Gercek):
    def __init__(self, *a):
        self.base = "sahte"

    def call(self, method, path, body=None):
        return S.call(method, path, body)


class FE:
    remaining = 5000
    def __init__(s, st): pass
    def get(s, *a, **k): return {}
    def post(s, *a): raise AssertionError("ETSY POST")
class FS:
    def __init__(s, *a): pass
    def needs_refresh(s): return False
R.Prodigi = FP; R.load_prodigi_key = lambda e: "x"; R.TokenStore = FS; R.Etsy = FE
R.etsy_receipts = lambda *a, **k: REC
R.otomasyonlar = lambda *a, **k: None
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
W = Path(tempfile.mkdtemp(prefix="kanal_bekci_"))


def run(kuru=False, ad="a"):
    R.DIKKAT_EK.clear()
    sys.argv = ["r", "--env", "live", "--state", str(W / "state.csv"), "--out", str(W / ad), "--packages", str(W / "pk"),
                "--approve-mode", "off", "--min-yas-dk", "60", "--sablonlar", SABLON] + (["--dry-run"] if kuru else ["--apply"])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            R.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    return rc, buf.getvalue()


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))

yasak = lambda: [c for c in S.cagri if c[0] != "GET" or c[1].endswith("/actions")]
S.cagri.clear()
rc, log1 = run(ad="k1")
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
k("Prodigi'ye hic yazma yok (POST/iptal/actions yok)", not yasak(), yasak())
k("K1 pause'daki kanal siparisi -> ACIL", st["9101"].get("warn") == R.ACIL_KOD and st["9101"].get("kanal_oid") == "ord_K1")
k("K2 Complete kanal siparisi -> ACIL", st["9102"].get("warn") == R.ACIL_KOD and st["9102"].get("kanal_oid") == "ord_K2")
k("K4 kisisellestirmesiz: uyari yok", not st["9104"].get("warn"), st["9104"])
k("K5 kendi siparisimiz: uyari yok", not st["9105"].get("warn"), st["9105"].get("warn"))
k("K6 Prodigi kaydi yok: uyari yok, ISIM_BEKLIYOR", not st["9106"].get("warn") and st["9106"]["stage"] == "ISIM_BEKLIYOR")
dk = (W / "k1/DIKKAT.md").read_text(encoding="utf-8")
k("DIKKAT: ACIL metni (siparis no + Prodigi id)",
  "ACIL: kisisellestirilmis Etsy siparisi Prodigi'de gorundu - siparis 9101, Prodigi ord_K1" in dk
  and "siparis 9102, Prodigi ord_K2" in dk and "9104" not in "".join(l for l in dk.splitlines() if "ACIL" in l))
K1, K2 = R.siparis_onay.kod("9101"), R.siparis_onay.kod("9102")
k("bildirim: ::error ACIL satirlari (yalniz K1, K2; receipt yerine opak kod)", f"::error title=ACIL {K1}::" in log1
  and f"::error title=ACIL {K2}::" in log1 and log1.count("::error title=ACIL") == 2
  and not [l for l in log1.splitlines() if l.startswith("::error") and ("9101" in l or "9102" in l)])
k("kosu bildirim icin basarisiz", rc not in (0, None), rc)
k("kartta ACIL notu", "ACIL" in (W / "k1/SIPARIS_ISIM/9101.md").read_text(encoding="utf-8")
  and "ACIL" not in (W / "k1/SIPARIS_ISIM/9106.md").read_text(encoding="utf-8"))
S.cagri.clear()
rc2, log2 = run(ad="k2")
k("ikinci kosu: Prodigi'ye yazma yok", not yasak(), yasak())
k("ikinci kosu: tekrar bildirim yok", "::error title=ACIL" not in log2 and log2.count("zaten bildirildi") == 2)
k("ikinci kosu: hata yok (rc 0)", rc2 in (0, None), rc2)
os.remove(W / "state.csv"); S.cagri.clear()
rc3, log3 = run(kuru=True, ad="kuru")
k("kuru kosu: uyari calisir, yazma yok", f"::error title=ACIL {K1}::" in log3 and not yasak())
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
