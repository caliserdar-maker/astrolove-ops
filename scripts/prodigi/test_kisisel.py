"""Kisisellestirme korumasi testi (ag yok; Etsy/Prodigi sahte): Kiril isim, emoji/♥, uzun mesaj, ayni burc,
coklu sorun, bos cevap + kontrol. Sablonlar: test_musteri_mesajlari.md (Drive TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md kopyasi).
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
 rec(9006, "POD-PIS_VIR-CI-8x10", [("Name under Pisces", "Александрина"), ("Name under Virgo", "Oleg"), ("Your message", "Люблю ♥")], "KZ"),
 rec(9007, "POD-GEM_SAG-WP-A4", [("Name under Gemini", ""), ("Name under Sagittarius", "Tom"), ("Your message", "Us")], "US"),
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
SABLON = str(ROOT / "scripts/prodigi/test_musteri_mesajlari.md")
def run():
    sys.argv = ["r", "--env", "live", "--state", str(W / "state.csv"), "--out", str(W / "out"), "--packages", str(W / "pk"),
                "--dry-run", "--approve-mode", "off", "--min-yas-dk", "60", "--sablonlar", SABLON]
    try: R.main(); return 0
    except SystemExit as e: return e.code
rc = run()
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
sonuc = []
def k(ad, kosul, d=""): sonuc.append(kosul); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))
KIS = ("9001", "9002", "9003", "9004", "9006", "9007")
for rid in KIS:
    k(f"{rid} ISIM_BEKLIYOR", st[rid]["stage"] == "ISIM_BEKLIYOR", st[rid]["note"][:120])
k("Prodigi'ye siparis yok", not any(c[0] == "create" for c in CAGRI))
k("kisisel siparislerde teklif bile yok (yalniz kontrol 9005)", [c[1] for c in CAGRI if c[0] == "quote"] == ["US"], CAGRI)
k("kontrol 9005 eski akista (dryrun)", st["9005"]["stage"] == "dryrun", st["9005"]["stage"])
k("kosu bildirim icin basarisiz", rc not in (0, None), rc)
yeni = (W / "out/ISIM_YENI.txt").read_text().split()
k("ISIM_YENI 6 siparis", sorted(yeni) == list(KIS), yeni)
kart = {r: (W / f"out/SIPARIS_ISIM/{r}.md").read_text(encoding="utf-8") for r in yeni}
def liste(r):
    return [int(x.split(" (")[0]) for x in kart[r].split("- Sablonlar: ")[1].split("\n")[0].split(" — ")[0].split(", ")]
for ham, ulke, bek in (("Ali", "US", "ALI"), ("Ali", "", "ALI"), ("Ali", "TR", "ALİ"), ("Işıl", "US", "IŞIL"),
                       ("Şirin", "GB", "ŞİRİN"), ("Müller", "DE", "MÜLLER"), ("Çiçek", "US", "ÇIÇEK")):
    k(f"buyuk harf {ham}/{ulke or '-'} -> {bek}", K.buyut(ham, ulke) == bek, K.buyut(ham, ulke))
k("sablon dosyasi 6x2 okundu", sorted(K.sablon_oku(SABLON)) == [(n, d) for n in range(1, 7) for d in ("EN", "RU")])
k("9001 Kiril isim -> sablon 2 RU + oneri ANNA", liste("9001") == [2, 1] and "Мы получили имя Анна" in kart["9001"]
  and "ANNA." in kart["9001"] and "KIRIL_ISIM" in st["9001"]["note"], liste("9001"))
k("9001 RU sablon 1: burc ilgi hali + basilacak isim", "Под знаком Водолея: АННА" in kart["9001"] and "Под знаком Овна: IVAN" in kart["9001"])
k("9001 RU mesaj (Kiril) mesajda serbest", "mesaj | `Навсегда вместе` (15 kar.) — TAMAM" in kart["9001"])
k("9002 emoji/♥ (liste bicimi) -> sablon 3 + temiz oneri", liste("9002") == [3, 1] and "\nForever\n" in kart["9002"]
  and "EMOJI" in st["9002"]["note"], liste("9002"))
k("9003 uzun mesaj -> sablon 4; 11 harf sinirda serbest", liste("9003") == [4, 1] and "UZUN_MESAJ" in st["9003"]["note"]
  and "CHRISTOPHER" in kart["9003"] and "Doldurulmadi (Serdar yazar): [Suggested shorter version]" in kart["9003"], liste("9003"))
k("9004 ayni burc sol/sag + TR buyuk harf", "sol (Leo)" in kart["9004"] and "ZEYNEP" in kart["9004"] and "dogrulama TAMAM" in st["9004"]["note"])
k("9004 temiz -> yalniz sablon 1", liste("9004") == [1] and "Under Leo: ALİ\nUnder Leo: ZEYNEP" in kart["9004"], liste("9004"))
k("9006 coklu sorun (Kiril+uzun isim, ♥) -> 2,3,4 + 1, KZ -> RU", liste("9006") == [2, 3, 4, 1] and "(RU)" in kart["9006"]
  and "ALEKSANDRINA" in kart["9006"], liste("9006"))
k("9007 bos isim -> sablon 5", liste("9007") == [5, 1] and "Name under Gemini:" in kart["9007"], liste("9007"))
k("her kartta sablon 6 tarih notu (+2 gun)", all("Sablon 6 (hatirlatma):" in kart[r] and "UTC tarihine kadar" in kart[r] for r in KIS))
k("mesaj GONDERILMEDI ibaresi", all("GONDERILMEDI" in kart[r] for r in KIS))
dk = (W / "out/DIKKAT.md").read_text(encoding="utf-8")
k("DIKKAT.md 6 kart satiri", dk.count("ISIM_BEKLIYOR") >= 6)
CAGRI.clear(); (W / "out/ISIM_YENI.txt").unlink()
rc2 = run()
k("ikinci kosu: tekrar kart/bildirim yok, ATLA", not (W / "out/ISIM_YENI.txt").exists() and not any(c[0] == "create" for c in CAGRI))
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
