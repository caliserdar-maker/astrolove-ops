"""Kisisellestirme korumasi testi (ag yok; Etsy/Prodigi sahte): Kiril isim, emoji/♥, uzun mesaj, ayni burc + kontrol.
Calistir: python3 scripts/prodigi/test_kisisel.py"""
import sys, os, json, copy, csv, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R, kisisel_siparis as K
import tempfile
W = Path(tempfile.mkdtemp(prefix="kisisel_test_"))
taban = json.load(open(ROOT / "scripts/prodigi/test_receipt_kisisel_taban.json"))
def rec(rid, sku, alanlar, ulke="US", yol="var"):
    r = copy.deepcopy(taban); r["receipt_id"] = rid; r["country_iso"] = ulke; r["is_shipped"] = False
    r["created_timestamp"] = int(time.time()) - 7200
    t = {"transaction_id": rid * 10, "sku": sku, "quantity": 1, "price": {"amount": 3499, "divisor": 100},
         "variations": [{"property_id": 200, "value_id": 1, "formatted_name": "Primary color", "formatted_value": "Midnight Blue"},
                        {"property_id": 513, "value_id": 2, "formatted_name": "Size", "formatted_value": "8×10″ (20×25cm)"}]}
    if yol == "var":
        t["variations"] += [{"property_id": None, "value_id": None, "formatted_name": q, "formatted_value": a} for q, a in alanlar]
    else:
        t["personalization"] = [{"question_text": q, "answer": a} for q, a in alanlar]
    r["transactions"] = [t]; return r
REC = [
 rec(9001, "POD-AQU_ARI-MB-8x10", [("Name under Aquarius", "Анна"), ("Name under Aries", "Ivan"), ("Your message", "Навсегда вместе")], "RU"),
 rec(9002, "POD-CAN_LIB-DB-A4", [("Name under Cancer", "Mia"), ("Name under Libra", "Leo"), ("Your message", "Forever ♥ 😍")], "US", yol="liste"),
 rec(9003, "POD-SCO_TAU-PW-12x16", [("Name under Scorpio", "Christopher"), ("Name under Taurus", "Emma"), ("Your message", "Two souls, one bond, today and every day after")], "GB"),
 rec(9004, "POD-LEO_LEO-WP-16x20", [("Left name", "Ali"), ("Right name", "Zeynep"), ("Your message", "Seninle her gün")], "TR"),
 rec(9005, "POD-ARI_LEO-MB-8x10", [], "US"),        # kontrol: kisisellestirmesiz
]
CAGRI = []
class FP:
    def siparisler(self, top=50): return []
    def quote(self, items, country): CAGRI.append(("quote", country)); return 20.0, "", {}
    def create_order(self, b): CAGRI.append(("create", b)); raise AssertionError("ORDER")
    def get_order(self, oid): return 200, {"order": {}}
    def urun(self, sku): return 200, {}
class FE:
    remaining = 5000
    def __init__(s, st): pass
    def get(s, *a, **k): return {}
    def post(s, *a): raise AssertionError("ETSY POST")
class FS:
    def __init__(s, *a): pass
    def needs_refresh(s): return False
R.Prodigi = lambda *a: FP(); R.load_prodigi_key = lambda e: "x"; R.TokenStore = FS; R.Etsy = FE
R.sku_haritasi = lambda p, b: ({x: "GLOBAL-HPR-" + x for x in b}, []); R.etsy_receipts = lambda *a, **k: REC
R.otomasyonlar = lambda *a, **k: None
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
(W / "sablon.md").write_text("## Sablon 1 EN\nHi {ad}, please check: {isim1} / {isim2} / {mesaj}\n## Sablon 1 RU\nЗдравствуйте, {ad}: {isim1} / {isim2} / {mesaj}\n## Sablon 3 RU\n{ad}, имя {isim1} нужно латиницей.\n## Sablon 4 EN\nHi {ad}, emoji can't print.\n## Sablon 5 EN\nHi {ad}, message too long.\n", encoding="utf-8")
def run():
    sys.argv = ["r", "--env", "live", "--state", str(W / "state.csv"), "--out", str(W / "out"), "--packages", str(W / "pk"),
                "--dry-run", "--approve-mode", "off", "--min-yas-dk", "60", "--sablonlar", str(W / "sablon.md")]
    try: R.main(); return 0
    except SystemExit as e: return e.code
rc = run()
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
sonuc = []
def k(ad, kosul, d=""): sonuc.append(kosul); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))
for rid in ("9001", "9002", "9003", "9004"):
    k(f"{rid} ISIM_BEKLIYOR", st[rid]["stage"] == "ISIM_BEKLIYOR", st[rid]["note"][:120])
k("Prodigi'ye siparis yok", not any(c[0] == "create" for c in CAGRI))
k("kisisel siparislerde teklif bile yok (yalniz kontrol 9005)", [c[1] for c in CAGRI if c[0] == "quote"] == ["US"], CAGRI)
k("kontrol 9005 eski akista (dryrun)", st["9005"]["stage"] == "dryrun", st["9005"]["stage"])
k("kosu bildirim icin basarisiz", rc not in (0, None), rc)
yeni = (W / "out/ISIM_YENI.txt").read_text().split()
k("ISIM_YENI 4 siparis", sorted(yeni) == ["9001", "9002", "9003", "9004"], yeni)
kart = {r: (W / f"out/SIPARIS_ISIM/{r}.md").read_text(encoding="utf-8") for r in yeni}
k("9001 Kiril isim yakalandi + RU sablon", "KIRIL_ISIM" in st["9001"]["note"] and "Здравствуйте" not in kart["9001"] and "латиницей" in kart["9001"], "")
k("9001 RU mesaj (Kiril) mesajda serbest", "mesaj | `Навсегда вместе` (15 kar.) — TAMAM" in kart["9001"])
k("9002 emoji/♥ yakalandi (liste bicimi) + sablon 4", "EMOJI" in st["9002"]["note"] and "emoji can't print" in kart["9002"])
k("9003 uzun mesaj + 11 harf siniri", "UZUN_MESAJ" in st["9003"]["note"] and "11 harf" not in kart["9003"] and "CHRISTOPHER" in kart["9003"], st["9003"]["note"][:160])
k("9004 ayni burc sol/sag + TR buyuk harf", "sol (Leo)" in kart["9004"] and "ZEYNEP" in kart["9004"] and "dogrulama TAMAM" in st["9004"]["note"])
k("9004 temiz -> sablon 1", "please check: Ali / Zeynep" in kart["9004"])
dk = (W / "out/DIKKAT.md").read_text(encoding="utf-8")
k("DIKKAT.md 4 kart satiri", dk.count("ISIM_BEKLIYOR") >= 4)
CAGRI.clear(); (W / "out/ISIM_YENI.txt").unlink()
rc2 = run()
k("ikinci kosu: tekrar kart/bildirim yok, ATLA", not (W / "out/ISIM_YENI.txt").exists() and not any(c[0] == "create" for c in CAGRI))
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
