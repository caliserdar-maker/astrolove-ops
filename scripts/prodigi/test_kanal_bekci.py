"""Kanal bekcisi testi (ag yok; Prodigi HTTP katmani + Etsy sahte). Router'in GERCEK Prodigi.iptal /
iptal_edilebilir kodu kosar; yalniz Prodigi.call sahtedir.
K1 kisisel + kanal siparisi iptal edilebilir -> iptal + STATE kanal_iptal
K2 kisisel + kanal siparisi iptal edilemez -> ACIL (DIKKAT + hata + ::error)
K3 kisisel + iptal edilebilir ama iptal basarisiz -> ACIL
K4 kisisellestirmesiz + kanal siparisi -> dokunulmaz (iptal cagrisi yok)
K5 kisisel + kendi etsy-* siparisimiz -> dokunulmaz
Ikinci kosu: tekrar iptal / tekrar ACIL bildirimi yok. Kuru kosu: iptal yok.
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
REC = [rec(9101, "POD-ARI_LEO-MB-8x10", K3), rec(9102, "POD-ARI_LEO-DB-A4", K3), rec(9103, "POD-ARI_LEO-PW-8x10", K3),
       rec(9104, "POD-ARI_LEO-MB-12x16", []), rec(9105, "POD-ARI_LEO-WP-8x10", K3)]


def kanal_siparis(oid, rid, stage="InProgress"):
    return {"id": oid, "created": "2026-09-25T10:00:00Z", "merchantReference": str(rid),
            "status": {"stage": stage, "issues": [], "details": {"downloadAssets": "NotStarted"}},
            "items": [{"merchantReference": str(rid * 10), "sku": "GLOBAL-HPR-8X10"}],
            "metadata": {"SalesChannelId": "x", "RutterOrderId": "y", "MerchantId": "z"}}


class Sahte:
    def __init__(s):
        s.orders = {o["id"]: o for o in (kanal_siparis("ord_K1", 9101), kanal_siparis("ord_K2", 9102),
                                           kanal_siparis("ord_K3", 9103), kanal_siparis("ord_K4", 9104))}
        own = kanal_siparis("ord_K5", 9105); own["merchantReference"] = "etsy-9105-8x10"; own.pop("metadata")
        s.orders["ord_K5"] = own
        s.cancel_ok = {"ord_K1": "Yes", "ord_K2": "No", "ord_K3": "Yes", "ord_K4": "Yes", "ord_K5": "Yes"}
        s.iptal_tutmaz = {"ord_K3"}
        s.cagri = []

    def call(s, method, path, body=None):
        s.cagri.append((method, path))
        if method == "GET" and path.startswith("/orders?"):
            return 200, {"outcome": "Ok", "orders": [o for o in s.orders.values() if o["status"]["stage"] != "Cancelled"],
                         "hasMore": False}
        if method == "GET" and path.startswith("/orders/") and path.endswith("/actions"):
            oid = path.split("/")[2]
            return 200, {"outcome": "Ok", "cancel": {"isAvailable": s.cancel_ok[oid]},
                         "changeRecipientDetails": {"isAvailable": "No"}, "changeShippingMethod": {"isAvailable": "No"},
                         "changeMetaData": {"isAvailable": "Yes"}}
        if method == "GET" and path.startswith("/orders/"):
            oid = path.split("/")[2]
            return 200, {"outcome": "Ok", "order": s.orders[oid]}
        if method == "POST" and path.endswith("/actions/cancel"):
            oid = path.split("/")[2]
            if s.cancel_ok[oid] != "Yes":
                return 400, {"outcome": "FailedToCancel"}
            if oid in s.iptal_tutmaz:
                return 200, {"outcome": "FailedToCancel"}
            s.orders[oid]["status"]["stage"] = "Cancelled"
            return 200, {"outcome": "Cancelled", "order": s.orders[oid]}
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

# --- 0) kuru kosu: iptal yok
S.cagri.clear()
rc0, log0 = run(kuru=True, ad="kuru")
k("kuru: hic iptal POST'u yok", not [c for c in S.cagri if c[0] == "POST" and "cancel" in c[1]], S.cagri)
k("kuru: K1 'iptal edilebilir' raporlandi", "(kuru) KANAL BEKCISI ord_K1 iptal edilebilir" in log0)
os.remove(W / "state.csv")

# --- 1) canli (sahte) kosu
S.cagri.clear()
rc, log1 = run(ad="k1")
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
iptal = [c[1] for c in S.cagri if c[0] == "POST" and "cancel" in c[1]]
k("iptal edilebilirlik GET /orders/{id}/actions ile okundu", ("GET", "/orders/ord_K1/actions") in S.cagri)
k("K1 iptal edildi + STATE kanal_iptal", "/orders/ord_K1/actions/cancel" in iptal and st["9101"]["kanal_iptal"] == "ord_K1"
  and S.orders["ord_K1"]["status"]["stage"] == "Cancelled", st["9101"].get("kanal_iptal"))
k("K2 iptal denenmedi (isAvailable=No) + ACIL", "/orders/ord_K2/actions/cancel" not in iptal and st["9102"]["warn"] == R.ACIL_KOD)
k("K3 iptal tutmadi -> ACIL", st["9103"]["warn"] == R.ACIL_KOD and "iptal BASARISIZ" in st["9103"]["note"], st["9103"]["note"][:120])
k("K4 kisisellestirmesiz: kanal siparisine dokunulmadi", "/orders/ord_K4/actions/cancel" not in iptal
  and ("GET", "/orders/ord_K4/actions") not in S.cagri)
k("K5 kendi siparisimize dokunulmadi", "/orders/ord_K5/actions/cancel" not in iptal and ("GET", "/orders/ord_K5/actions") not in S.cagri)
dk = (W / "k1/DIKKAT.md").read_text(encoding="utf-8")
k("DIKKAT: ACIL metni K2 + K3 (siparis no + Prodigi id)",
  "ACIL: kisisellestirilmis siparis Prodigi'de uretime girdi - siparis 9102, Prodigi ord_K2" in dk
  and "siparis 9103, Prodigi ord_K3" in dk)
k("DIKKAT: K1 iptal satiri", "KANAL IPTAL 9101" in dk)
k("bildirim: ::error ACIL satirlari", "::error title=ACIL 9102::" in log1 and "::error title=ACIL 9103::" in log1)
k("kosu bildirim icin basarisiz", rc not in (0, None), rc)
k("Prodigi'ye yeni siparis acilmadi", ("POST", "/orders") not in S.cagri)
k("K1/K2/K3 kartlarinda bekci notu", "IPTAL EDILDI" in (W / "k1/SIPARIS_ISIM/9101.md").read_text(encoding="utf-8")
  and "ACIL" in (W / "k1/SIPARIS_ISIM/9102.md").read_text(encoding="utf-8"))
k("K1-K3,K5 ISIM_BEKLIYOR", all(st[x]["stage"] == "ISIM_BEKLIYOR" for x in ("9101", "9102", "9103", "9105")),
  {x: st[x]["stage"] for x in st})

# --- 2) ikinci kosu: tekrar yok
S.cagri.clear()
rc2, log2 = run(ad="k2")
iptal2 = [c[1] for c in S.cagri if c[0] == "POST" and "cancel" in c[1]]
k("ikinci kosu: tekrar iptal yok", not iptal2, iptal2)
k("ikinci kosu: tekrar ACIL bildirimi yok", "::error title=ACIL" not in log2 and "zaten ACIL bildirildi" in log2)
k("ikinci kosu: hata yok (rc 0)", rc2 in (0, None), rc2)
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
