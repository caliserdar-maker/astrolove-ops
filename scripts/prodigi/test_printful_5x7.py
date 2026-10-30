"""Serdar 30 Eki: 5x7 tedarikcisi Printful, siparis elle. Router 5x7 kalemini Prodigi'ye GONDERMEZ, "5x7 PRINTFUL, ELLE" isaretler;
diger boylar degismez (ag yok; sahte fis, sahte Prodigi/Etsy).
P1 parse_items: yalniz 5x7 -> gonderilecek kalem 0, other PRINTFUL_ELLE
P2 karisik 5x7 + 8x10 -> yalniz 8x10 (GLOBAL-HPR-8x10, POD_PRINT/<pair>/<ed>/8x10.jpg)
P3 --only-size 5x7 -> kalem 0, atlanan'a da girmez
P4 diger boylar (TUM_BOYLAR, cerceveli dahil) eski kodla (git HEAD~ surumu) birebir ayni parse_items ciktisi
P5 canli (sahte) onayli mod: POST /orders yok, 5x7 icin teklif/katalog yok, karisik pakette yalniz 8x10, rapor + DIKKAT isareti
P6 --submit: eski pakette 5x7 kalemi (meta ya da yalniz order govdesi SKU'su) -> gonderilmez, POST yok
P7 SKU2 + "Primary color" 5x7 -> PRINTFUL_ELLE
P8 kisisellestirmeli yalniz 5x7 fis -> ISIM_BEKLIYOR karti + ISIM_YENI + kosu bilincli kirmizi (eski davranis)
P9 kisisel olmayan yalniz 5x7 fis -> STATE manual/PRINTFUL_ELLE bir kez; ikinci kosu ATLA, DIKKAT tekrari yok
P10 manuel_siparis.py hazirla/gonder 5x7 SKU -> DUR
Calistir: python3 scripts/prodigi/test_printful_5x7.py [--eski <order_router.py eski surum yolu>]"""
import sys, os, json, copy, time, tempfile, io, contextlib, importlib.util, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R
taban = json.load(open(ROOT / "scripts/prodigi/test_receipt_kisisel_taban.json"))


def tx(tid, sku, var=()):
    return {"transaction_id": tid, "sku": sku, "quantity": 1, "price": {"amount": 2999, "divisor": 100}, "variations": list(var)}


def rec(rid, txs):
    r = copy.deepcopy(taban); r.update(receipt_id=rid, country_iso="US", is_shipped=False,
                                       created_timestamp=int(time.time()) - 7200, transactions=txs)
    return r


Y = rec(9301, [tx(1, "POD-CAN_LIB-MB-5x7")])
K = rec(9302, [tx(2, "POD-CAN_LIB-DB-5x7"), tx(3, "POD-CAN_LIB-DB-8x10")])
S = rec(9303, [tx(4, "POD-CAN_LIB-PW-8x10")])
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


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def eski_modul(yol):
    if not yol:
        kaynak = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:scripts/prodigi/order_router.py"],
                                capture_output=True, text=True, check=True).stdout
        if "PRINTFUL_ELLE" in kaynak:      # degisiklik commit edildiyse bir onceki surum
            kaynak = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H", "-S", "PRINTFUL_ELLE =", "--",
                                     "scripts/prodigi/order_router.py"], capture_output=True, text=True, check=True).stdout.strip()
            kaynak = subprocess.run(["git", "-C", str(ROOT), "show", f"{kaynak}~1:scripts/prodigi/order_router.py"],
                                    capture_output=True, text=True, check=True).stdout
        yol = Path(tempfile.mkdtemp(prefix="eski_router_")) / "order_router_eski.py"
        yol.write_text(kaynak, encoding="utf-8")
    sp = importlib.util.spec_from_file_location("order_router_eski", yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    m.CERCEVE_ESLEME = R.CERCEVE_ESLEME; m.PRINT_REMOTE = R.PRINT_REMOTE    # gecici dizin yolu yerine depodaki esleme
    return m


eski = eski_modul(sys.argv[sys.argv.index("--eski") + 1] if "--eski" in sys.argv else "")

# P1-P3
i, o, a = R.parse_items(Y)
k("P1 yalniz 5x7: kalem 0, other PRINTFUL_ELLE", i == [] and o == ["PRINTFUL_ELLE:POD-CAN_LIB-MB-5x7x1"] and a == [], (i, o, a))
i, o, a = R.parse_items(K)
k("P2 karisik: yalniz 8x10", [(x["size"], x["prodigi_sku"], x["asset_remote"]) for x in i]
  == [("8x10", "GLOBAL-HPR-8x10", f"{R.PRINT_REMOTE}/CANCER_LIBRA/DEEP_BLACK/8x10.jpg")] and o == ["PRINTFUL_ELLE:POD-CAN_LIB-DB-5x7x1"], (i, o))
i, o, a = R.parse_items(K, "5x7")
k("P3 --only-size 5x7: kalem 0, atlanan'da 5x7 yok", i == [] and a == ["POD-CAN_LIB-DB-8x10x1"] and o == ["PRINTFUL_ELLE:POD-CAN_LIB-DB-5x7x1"], (i, o, a))
k("P3b TUM_BOYLAR'da 5x7 yok, diger boylar eskiyle ayni", "5x7" not in R.TUM_BOYLAR and R.TUM_BOYLAR == [b for b in eski.TUM_BOYLAR if b != "5x7"],
  R.TUM_BOYLAR)

# P4 diger boylar: eski kodla birebir (cerceveli eslemeler dahil)
boylar = [b for b in eski.TUM_BOYLAR if b != "5x7"]
txs, n = [], 100
for b in boylar:
    for renk in ("MB", "DB", "PW", "CI", "WP"):
        n += 1; txs.append(tx(n, f"POD-CAN_LIB-{renk}-{b}"))
for (b, c) in sorted(R.cerceve_haritasi()):
    n += 1; txs.append(tx(n, f"POD-CAN_LIB-MB-{b}-F{c}"))
H = rec(9310, txs)
yeni_i, yeni_o, yeni_a = R.parse_items(H)
eski_i, eski_o, eski_a = eski.parse_items(H)
k(f"P4 {len(boylar)} boy x 5 renk + cerceveli {len(R.cerceve_haritasi())}: parse_items eskiyle birebir",
  yeni_i == eski_i and yeni_o == eski_o and yeni_a == eski_a and len(yeni_i) >= len(boylar) * 5, f"kalem {len(yeni_i)}")
for b in ("8x10", "A1"):
    k(f"P4b only_size {b} eskiyle ayni", R.parse_items(H, b) == eski.parse_items(H, b))

# P5 canli (sahte), onayli mod
R.Prodigi = FP; R.load_prodigi_key = lambda e: "x"; R.TokenStore = FS; R.Etsy = FE
R.otomasyonlar = lambda *a, **k: None
R.etsy_receipts = lambda *a, **k: [Y, K, S]
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
W = Path(tempfile.mkdtemp(prefix="pf5x7_"))


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
    md = "".join(p.read_text(encoding="utf-8") for p in (W / ad).glob("*.md")) if (W / ad).exists() else ""
    return md + buf.getvalue()


cagri.clear()
out = run(["--env", "live"], "p5")
pk = sorted(x.name for x in (W / "p5").glob("93*.json"))
k("P5 POST /orders yok", not [c for c in cagri if c[0] == "POST" and c[1] == "/orders"])
k("P5 5x7 hicbir Prodigi cagrisinda yok (katalog/teklif)", not [c for c in cagri if "5x7" in c[1] or "5x7" in c[2]],
  [c[:2] for c in cagri if "5x7" in c[1] or "5x7" in c[2]][:3])
k("P5 yalniz 5x7 fis icin paket yok", "9301.json" not in pk, pk)
kp = json.loads((W / "p5" / "9302.json").read_text()) if (W / "p5" / "9302.json").exists() else {}
k("P5 karisik paket yalniz 8x10", [x["sku"] for x in kp.get("items", [])] == ["POD-CAN_LIB-DB-8x10"]
  and [x["sku"] for x in kp.get("order", {}).get("items", [])] == ["GLOBAL-HPR-8x10"], kp.get("items"))
k("P5 karisik paket uyarisi '5x7 PRINTFUL, ELLE'", "5x7 PRINTFUL, ELLE" in (kp.get("warn") or ""), kp.get("warn"))
sp = json.loads((W / "p5" / "9303.json").read_text()) if (W / "p5" / "9303.json").exists() else {}
k("P5 yalniz 8x10 fis paketi eskisi gibi", [x["sku"] for x in sp.get("order", {}).get("items", [])] == ["GLOBAL-HPR-8x10"]
  and "PRINTFUL" not in (sp.get("warn") or ""), sp.get("warn"))
rap_md = "".join(x.read_text(encoding="utf-8") for x in (W / "p5").glob("*.md"))
k("P5 rapor: fis basina 1 '5x7 PRINTFUL, ELLE' satiri (9301, 9302; 9303 yok)",
  all(sum(1 for sat in rap_md.splitlines() if sat.startswith("- 5x7 PRINTFUL, ELLE: receipt") and R.receipt_kod(r) in sat) == 1
      for r in ("9301", "9302"))
  and not any(sat.startswith("- 5x7 PRINTFUL, ELLE: receipt") and R.receipt_kod("9303") in sat for sat in rap_md.splitlines()),
  [sat[:60] for sat in rap_md.splitlines() if "PRINTFUL, ELLE" in sat][:6])
k("P5 katalog denetimi 14 boy (5x7 yok)", f"{len(R.TUM_BOYLAR)}/{len(R.TUM_BOYLAR)} boy dogrulandi" in out and len(R.TUM_BOYLAR) == 14)

# P6 --submit: eski pakette 5x7 kalemi
pkg = W / "p6"; pkg.mkdir()
eski_pk = {"receipt_id": "9304", "items": [{"transaction_id": 9, "sku": "POD-CAN_LIB-MB-5x7", "prodigi_sku": "GLOBAL-HPR-5x7", "size": "5x7",
                                             "asset_remote": f"{R.PRINT_REMOTE}/CANCER_LIBRA/MIDNIGHT_BLUE/5x7.jpg"}],
           "order": {"merchantReference": "etsy-9304", "items": [{"sku": "GLOBAL-HPR-5x7", "copies": 1}]}}
(pkg / "9304.json").write_text(json.dumps(eski_pk))
cagri.clear()
out6 = run(["--env", "live", "--submit", "9304", "--apply", "--packages", str(pkg)], "p6")
k("P6 --submit 5x7 paket: POST /orders yok", not [c for c in cagri if c[0] == "POST" and c[1] == "/orders"])
k("P6 rapor/hata: GONDERILMEDI", "5x7 PRINTFUL, ELLE kalemi pakette" in out6, out6[-300:])
(pkg / "9305.json").write_text(json.dumps({"receipt_id": "9305", "items": [{"transaction_id": 10, "sku": "POD-CAN_LIB-MB-8x10",
    "prodigi_sku": "GLOBAL-HPR-8x10", "size": "8x10", "asset_remote": "x/8x10.jpg"}],
    "order": {"merchantReference": "etsy-9305", "items": [{"sku": "GLOBAL-HPR-5X7", "copies": 1}]}}))
cagri.clear()
out6b = run(["--env", "live", "--submit", "9305", "--apply", "--packages", str(pkg)], "p6b")
k("P6b yalniz order govdesinde 5x7 SKU: GONDERILMEDI", "5x7 PRINTFUL, ELLE kalemi pakette" in out6b
  and not [c for c in cagri if c[0] == "POST" and c[1] == "/orders"])

# P7 SKU2 (yeni SKU + Primary color)
RENK = {"property_id": 200, "value_id": 1, "formatted_name": "Primary color", "formatted_value": "Midnight Blue"}
i7, o7, _ = R.parse_items(rec(9307, [tx(7, "POD-CAN_LIB-5x7", [RENK]), tx(8, "POD-CAN_LIB-8x10", [RENK])]))
k("P7 SKU2 5x7 -> PRINTFUL_ELLE, 8x10 kalem", [x["size"] for x in i7] == ["8x10"] and o7 == ["PRINTFUL_ELLE:POD-CAN_LIB-MB-5x7x1"], (i7 and i7[0]["sku"], o7))

# P8 kisisel yalniz 5x7 / P9 kisisel olmayan yalniz 5x7 (ayni STATE ile iki kosu)
KIS = [RENK, {"property_id": None, "value_id": None, "formatted_name": "Name under Cancer", "formatted_value": "Mia"},
       {"property_id": None, "value_id": None, "formatted_name": "Name under Libra", "formatted_value": "Leo"}]
K8, Y9 = rec(9308, [tx(11, "POD-CAN_LIB-5x7", KIS)]), rec(9309, [tx(12, "POD-CAN_LIB-MB-5x7")])
R.etsy_receipts = lambda *a, **k: [K8, Y9]
cagri.clear()
st_yol = W / "p8.csv"


def run_st(ad):
    R.DIKKAT_EK.clear()
    sys.argv = ["r", "--state", str(st_yol), "--out", str(W / ad), "--sablonlar", str(ROOT / "scripts/prodigi/test_musteri_mesajlari.md"),
                "--env", "live"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            R.main()
    except SystemExit:
        pass
    return "".join(x.read_text(encoding="utf-8") for x in (W / ad).glob("*.md")), buf.getvalue(), list(R.DIKKAT_EK)


md8, so8, dk8 = run_st("p8")
st8 = R.read_state(st_yol)
k("P8 kisisel 5x7: STATE ISIM_BEKLIYOR + kart + ISIM_YENI", (st8.get("9308") or {}).get("stage") == "ISIM_BEKLIYOR"
  and (W / "p8" / "SIPARIS_ISIM" / "9308.md").exists() and "9308" in (W / "p8" / "ISIM_YENI.txt").read_text()
  if (W / "p8" / "ISIM_YENI.txt").exists() else False, (st8.get("9308") or {}).get("stage"))
k("P9 yalniz 5x7: STATE manual / PRINTFUL_ELLE, DIKKAT 1 kez", (st8.get("9309") or {}).get("stage") == "manual"
  and (st8.get("9309") or {}).get("warn") == "PRINTFUL_ELLE" and sum("9309" in d for d in dk8) == 1, (st8.get("9309"), dk8))
md9, so9, dk9 = run_st("p9")
k("P9 ikinci kosu: 9308/9309 ATLA, DIKKAT'te 9309 yok", "9309: ATLA (STATE manual" in md9 and "9308: ATLA (STATE ISIM_BEKLIYOR" in md9
  and not any("9309" in d for d in dk9), dk9)
k("P8-P9 POST /orders yok, 5x7 Prodigi cagrisinda yok", not [c for c in cagri if c[0] == "POST" and c[1] == "/orders"]
  and not [c for c in cagri if "5x7" in c[1].lower() or "5x7" in c[2].lower()])

# P10 manuel_siparis
for mod in ("hazirla", "gonder"):
    r10 = subprocess.run([sys.executable, str(ROOT / "scripts/prodigi/manuel_siparis.py"), mod, "--file-id", "x", "--remote", "y",
                          "--sku", "GLOBAL-HPR-5x7", "--ref", "r", "--alici", "a", "--adres1", "b", "--sehir", "c", "--posta", "d",
                          "--confirm", "r", "--env", "sandbox"], capture_output=True, text=True, cwd=str(W))
    k(f"P10 manuel_siparis {mod} 5x7 -> DUR", r10.returncode != 0 and "5x7 PRINTFUL, ELLE" in r10.stderr, r10.stderr[-120:])
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
