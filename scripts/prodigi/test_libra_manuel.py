"""LIBRA = manuel kontrol testi (sahte veri, ag yok). Prodigi'ye siparis/iptal yok, Etsy'ye yazma yok.
L1 kisisel + LIBRA -> manual LIBRA_MANUEL, kart/onizleme yok, bildirim (DIKKAT + ::error + kosu basarisiz)
L2 kisisellestirmesiz + LIBRA (onayli mod) -> manual, paket YOK
L3 kisisellestirmesiz, LIBRA yok -> degismez: paket hazir (bekliyor)
L4 kisisel, LIBRA yok -> degismez: ISIM_BEKLIYOR + kart
L5 elle hazirlanmis LIBRA paketi --submit -> reddedilir, Prodigi POST yok
L6 ikinci kosu: tekrar bildirim yok. L7 kanal bekleyen satirinda LIBRA uyarisi.
Calistir: python3 scripts/prodigi/test_libra_manuel.py"""
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



KL = [("Name under Cancer", "Mia"), ("Name under Libra", "Tom"), ("Your message", "Always")]
KA = [("Name under Aries", "Mia"), ("Name under Leo", "Tom"), ("Your message", "Always")]
REC = [rec(9201, "POD-CAN_LIB-MB-8x10", KL), rec(9202, "POD-LIB_SCO-DB-12x16", []),
       rec(9203, "POD-ARI_LEO-MB-12x16", []), rec(9204, "POD-ARI_LEO-CI-8x10", KA)]


class Sahte:
    def __init__(s):
        s.orders = {}
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
W = Path(tempfile.mkdtemp(prefix="libra_"))


def run(kuru=False, ad="a", mod="on", ek=()):
    R.DIKKAT_EK.clear()
    sys.argv = ["r", "--env", "live", "--state", str(W / "state.csv"), "--out", str(W / ad), "--packages", str(W / "pk"),
                "--approve-mode", mod, "--min-yas-dk", "60", "--sablonlar", SABLON] + (["--dry-run"] if kuru else ["--apply"]) + list(ek)
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

yasak = lambda: [c for c in S.cagri if (c[0] == "POST" and c[1] != "/quotes") or c[1].endswith("/actions")]
k("libra_mi: CAN_LIB / LIBRA / LIB_SCO evet; ARI_LEO / CALIBRE hayir",
  R.libra_mi([{"pair": "CAN_LIB"}]) and R.libra_mi([{"pair": "CANCER_LIBRA"}]) and R.libra_mi([{"sku": "POD-LIB_SCO-8x10"}])
  and not R.libra_mi([{"pair": "ARI_LEO", "sku": "POD-ARI_LEO-8x10"}]) and not R.libra_mi([{"pair": "CALIBRE_X"}]))
S.cagri.clear()
rc, log1 = run(ad="l1")
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
k("Prodigi'ye yazma yok (siparis/iptal/actions yok)", not yasak(), yasak())
k("L1 kisisel LIBRA -> manual LIBRA_MANUEL", st["9201"]["stage"] == "manual" and st["9201"]["warn"] == R.LIBRA_KOD, st["9201"])
k("L1 kart/onizleme hazirlanmadi", not (W / "l1/SIPARIS_ISIM/9201.md").exists())
k("L2 LIBRA -> manual, paket yok", st["9202"]["stage"] == "manual" and st["9202"]["warn"] == R.LIBRA_KOD
  and not (W / "l1/9202.json").exists(), st["9202"])
k("L3 LIBRA yok -> degismedi (bekliyor + paket)", st["9203"]["stage"] == "bekliyor" and (W / "l1/9203.json").exists(), st["9203"])
k("L4 kisisel LIBRA yok -> degismedi (ISIM_BEKLIYOR + kart)", st["9204"]["stage"] == "ISIM_BEKLIYOR"
  and (W / "l1/SIPARIS_ISIM/9204.md").exists() and not st["9204"].get("warn"))
dk = (W / "l1/DIKKAT.md").read_text(encoding="utf-8")
k("DIKKAT: iki LIBRA satiri", dk.count("LIBRA_MANUEL: LIBRA iceren siparis 9201") >= 1 and "siparis 9202" in dk)
k("bildirim: ::error LIBRA_MANUEL x2, receipt no logda yok",
  log1.count("::error title=LIBRA_MANUEL S-") == 2 and "9201" not in "".join(l for l in log1.splitlines() if l.startswith("::error title=LIBRA")))
k("L7 kanal bekleyen satirinda LIBRA uyarisi (yalniz LIBRA)", "receipt 9202 (POD-LIB_SCO-DB-12x16) - ONAYLAR.json onayi olmadan panelden serbest birakma | LIBRA_MANUEL" in dk
  and "9203 (POD-ARI_LEO-MB-12x16) - ONAYLAR.json onayi olmadan panelden serbest birakma\n" in dk, [l for l in dk.splitlines() if "BEKLEYEN" in l])
k("kosu bildirim icin basarisiz", rc not in (0, None), rc)
S.cagri.clear()
rc2, log2 = run(ad="l2")
k("L6 ikinci kosu: tekrar bildirim yok, yazma yok", "::error title=LIBRA" not in log2 and not yasak())
sahte = json.loads((W / "l1/9203.json").read_text(encoding="utf-8"))
sahte["items"][0]["pair"] = "CAN_LIB"; sahte["items"][0]["sku"] = "POD-CAN_LIB-MB-12x16"
(W / "pk").mkdir(exist_ok=True); (W / "pk/9203.json").write_text(json.dumps(sahte), encoding="utf-8")
S.cagri.clear()
rep = []
ok5, err5 = R.submit_package(type("A", (), {"packages": str(W / "pk"), "out": str(W / "pk"), "state": str(W / "state.csv"),
                                               "onay_dizin": str(W), "onaylar": "", "env": "live"})(),
                             FP(), {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}, "9203", rep)
k("L5 LIBRA paketi --submit reddedildi", not ok5 and R.LIBRA_KOD in err5 and not yasak(), err5)
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
