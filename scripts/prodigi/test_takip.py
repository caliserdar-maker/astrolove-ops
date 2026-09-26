#!/usr/bin/env python3
"""Takip duzeltmesi testleri (ag yok, Etsy/Prodigi sahte): eski eslestirme testleri + gecmis siparis
korumasi (takip.yazma_karari) + order_router adim 3 entegrasyonu. Calistir: python3 scripts/prodigi/test_takip.py"""
import copy, csv, os, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import takip as T
import order_router as R

# 1) UPS Mail Innovations + USPS bicimli numara -> usps
sp = {"carrier":{"name":"UPS Mail Innovations","service":"UPS Mail Innovations Domestic"},
      "tracking":{"number":"9261290312345678901234","url":"https://www.ups.com/track?tracknum=9261290312345678901234"}}
b = T.takip_bilgi(sp); p = T.etsy_plani(b)
assert p["carrier_name"]=="usps", p
assert p["tracking_code"]=="9261290312345678901234"
assert p["takip_url"].startswith("https://www.ups.com/track"), p   # Prodigi URL'si korunur
assert p["url_kaynagi"]=="prodigi"
print("1 UPS MI + USPS numara ->", p["carrier_name"], "|", p["gerekce"][:60])

# 2) Mail Innovations AMA numara USPS bicimi degil -> eslestirme YOK (other), uyari var
sp2 = {"carrier":{"name":"UPS Mail Innovations","service":"MI"},"tracking":{"number":"1Z999AA10123456784"}}
p2 = T.etsy_plani(T.takip_bilgi(sp2))
assert p2["carrier_name"]=="other" and "uymuyor" in p2["uyari"], p2
print("2 MI + UPS numara ->", p2["carrier_name"], "|", p2["uyari"][:70])

# 3) Duz UPS -> ups, link tablodan
sp3 = {"carrier":{"name":"UPS","service":"UPS Ground"},"tracking":{"number":"1Z999AA10123456784"}}
p3 = T.etsy_plani(T.takip_bilgi(sp3))
assert p3["carrier_name"]=="ups" and p3["takip_url"].endswith("1Z999AA10123456784") and p3["url_kaynagi"]=="tablo"
print("3 UPS ->", p3["carrier_name"], p3["takip_url"])

# 4) USPS 420 onekli numara -> onek ayrilir
USPS22 = "9261290312345678901234"
assert len(USPS22) == 22
sp4 = {"carrier":{"name":"USPS","service":"USPS Ground Advantage"},"tracking":{"number":"42003237" + USPS22}}
b4=T.takip_bilgi(sp4); p4 = T.etsy_plani(b4)
assert p4["carrier_name"]=="usps" and p4["tracking_code"]=="9261290312345678901234", p4
assert b4["son_ayak_numara"]=="9261290312345678901234"
print("4 420 onek ->", p4["tracking_code"], "|", p4["gerekce"][-30:])

# 4b) GOREV 0033: Prodigi yalniz "UPS" (hizmet bos) + 26 haneli USPS IMpb -> usps (UPS'te bulunamiyordu)
p4b = T.etsy_plani(T.takip_bilgi({"carrier": {"name": "UPS", "service": ""},
                                  "tracking": {"number": "92419903104126543475578595"}}))
assert p4b["carrier_name"] == "usps" and p4b["tracking_code"] == "92419903104126543475578595", p4b
assert "tools.usps.com" in p4b["takip_url"], p4b
# 1Z numarali duz UPS degismez
assert T.etsy_plani(T.takip_bilgi({"carrier": {"name": "UPS"}, "tracking": {"number": "1Z999AA10123456784"}}))["carrier_name"] == "ups"
print("4b UPS + IMpb ->", p4b["carrier_name"], p4b["takip_url"][:50])

# 5) Bilinmeyen tasiyici -> other + uyari
p5 = T.etsy_plani(T.takip_bilgi({"carrier":{"name":"Evri"},"tracking":{"number":"H00123456789"}}))
assert p5["carrier_name"]=="other" and "tabloda yok" in p5["uyari"]
print("5 bilinmeyen ->", p5["carrier_name"], "|", p5["uyari"])

# 6) Royal Mail (GB)
p6 = T.etsy_plani(T.takip_bilgi({"carrier":{"name":"Royal Mail","service":"Tracked 48"},"tracking":{"number":"AB123456789GB"}}))
assert p6["carrier_name"]=="royal-mail"
print("6 Royal Mail ->", p6["carrier_name"], p6["takip_url"][:60])

# 7) zaten_var: ayni numara varsa tekrar POST yok
rec = {"receipt_id": 1000000001, "shipments":[{"carrier_name":"ups","tracking_code":"9261290312345678901234"}]}
var, kayitli = T.zaten_var(rec, p); assert var and kayitli=="ups"
print("7 zaten_var ->", var, kayitli)

# 8) dogrula: is_shipped TEK BASINA PASS DEGIL
rec_is = {"receipt_id": 1000000001, "is_shipped": True, "shipments": []}
ok, eksik = T.dogrula(rec_is, 1000000001, p, "ok")
assert not ok and any("numara Etsy gonderilerinde yok" in e for e in eksik), (ok,eksik)
print("8 is_shipped tek basina ->", ok, eksik)

# 9) yanlis carrier yakalanir
rec_y = {"receipt_id": 1000000001, "shipments":[{"carrier_name":"ups","tracking_code":"9261290312345678901234"}]}
ok2, eksik2 = T.dogrula(rec_y, 1000000001, p, "ok")
assert not ok2 and any("carrier_name farkli" in e for e in eksik2), eksik2
print("9 yanlis carrier ->", eksik2)

# 10) tam dogru + calisan link -> PASS
rec_ok = {"receipt_id": 1000000001, "shipments":[{"carrier_name":"usps","tracking_code":"9261290312345678901234"}]}
ok3, eksik3 = T.dogrula(rec_ok, 1000000001, p, "ok"); assert ok3 and not eksik3
ok4, eksik4 = T.dogrula(rec_ok, 1000000001, p, "HTTP 404"); assert not ok4 and "calismiyor" in eksik4[0]
print("10 tam dogru ->", ok3, "| link bozuk ->", eksik4)

# 11) router: kargo yontemi govdeye gecer
receipt = {"receipt_id": 123, "name":"X", "first_line":"a", "zip":"1", "country_iso":"US", "city":"c"}
items = [{"transaction_id": 9, "sku":"POD-CAN_LIB-MB-8x10", "prodigi_sku":"GLOBAL-HPR-8X10", "qty":1,
          "size":"8x10", "pair":"CAN_LIB", "ed":"MB", "price":34.99, "asset_remote":"gdrive:x/8x10.jpg"}]
b_std = R.order_body(receipt, items, {"POD-CAN_LIB-MB-8x10":"u"}, "", "Standard")
b_var = R.order_body(receipt, items, {"POD-CAN_LIB-MB-8x10":"u"}, "")
assert b_std["shippingMethod"]=="Standard" and b_var["shippingMethod"]=="Budget"
pkg = R.package_of(receipt, items, "US", 34.99, 20.0, 0.4, "", "live", "", "Express")
assert pkg["order"]["shippingMethod"]=="Express", pkg["order"]["shippingMethod"]
print("11 order_body/package_of shippingMethod ->", b_std["shippingMethod"], pkg["order"]["shippingMethod"])
print("eski testler: 11/11 PASS")

# ================= gecmis siparis korumasi

S = T.sinir_ts(); YENI = S + 3600; ESKI = S - 86400
N = "92419903104126543475578595"
plan = T.etsy_plani(T.takip_bilgi({"carrier": {"name": "UPS", "service": "UPS Mail Innovations"},
                                    "tracking": {"number": N, "url": "https://tracking.ups-mi.net/packageID/" + N}}))
assert plan["carrier_name"] == "usps"
sonuc = []
def kontrol(ad, kosul, detay=""):
    sonuc.append((ad, bool(kosul))); print(("PASS " if kosul else "FAIL ") + ad + (f" | {detay}" if detay else ""))

# --- birim
k = lambda rec: T.yazma_karari(rec, 1, plan, S)
kontrol("U1 gecmis receipt, gonderi yok -> gecmis", k({"receipt_id": 1, "create_timestamp": ESKI, "shipments": []})[0] == "gecmis")
kontrol("U2 gecmis receipt, ayni numara UPS (MUSTERI tipi) -> gecmis",
        k({"receipt_id": 1, "create_timestamp": ESKI, "shipments": [{"carrier_name": "UPS", "tracking_code": N}]})[0] == "gecmis")
kontrol("U3 yeni receipt, gonderi yok -> yaz", k({"receipt_id": 1, "create_timestamp": YENI, "shipments": []})[0] == "yaz")
kontrol("U4 yeni receipt, ayni numara -> dogrula (POST yok)",
        k({"receipt_id": 1, "create_timestamp": YENI, "shipments": [{"carrier_name": "usps", "tracking_code": N}]})[0] == "dogrula")
kontrol("U5 yeni receipt, baska gonderi (elle) -> gecmis",
        k({"receipt_id": 1, "create_timestamp": YENI, "shipments": [{"carrier_name": "ups", "tracking_code": "1Z1"}]})[0] == "gecmis")
kontrol("U6 yeni receipt, is_shipped=True gonderisiz -> gecmis",
        k({"receipt_id": 1, "create_timestamp": YENI, "is_shipped": True, "shipments": []})[0] == "gecmis")
kontrol("U7 zaman yok -> hata", k({"receipt_id": 1, "shipments": []})[0] == "hata")
kontrol("U8 receipt eslesmedi -> hata", k({"receipt_id": 2, "create_timestamp": YENI})[0] == "hata")
kontrol("U9 created_timestamp alani da okunur", k({"receipt_id": 1, "created_timestamp": YENI, "shipments": []})[0] == "yaz")
kontrol("U10 sinir geri alinamaz", T.sinir_ts("2020-01-01 00:00:00") == S)
kontrol("U11 sinir ileri tasinir", T.sinir_ts("2027-01-01 00:00:00") > S)
ok_, e_ = T.dogrula({"receipt_id": 1, "shipments": [{"carrier_name": "UPS", "tracking_code": N},
                                                   {"carrier_name": "usps", "tracking_code": N}]}, 1, plan, "ok")
kontrol("U12 dogrula: ayni numarali 2 kayit [UPS, usps] -> PASS", ok_, e_)

# --- entegrasyon: order_router main(), adim 3
WORK = Path(tempfile.mkdtemp(prefix="takip_test_"))
STATE = WORK / "state.csv"; OUT = WORK / "out"; OUT.mkdir(exist_ok=True)
(WORK / "tok.json").write_text("{}")
RECEIPTS = {
    "101": {"receipt_id": 101, "create_timestamp": ESKI, "shipments": [], "is_shipped": False},                       # gecmis, takipsiz
    "102": {"receipt_id": 102, "create_timestamp": ESKI, "shipments": [{"carrier_name": "UPS", "tracking_code": N}], "is_shipped": True},  # MUSTERI tipi
    "103": {"receipt_id": 103, "create_timestamp": YENI, "shipments": [], "is_shipped": False},                      # YENI
    "104": {"receipt_id": 104, "create_timestamp": YENI, "shipments": [{"carrier_name": "ups", "tracking_code": "1ZELLE"}], "is_shipped": True},  # Serdar elle
    "105": {"receipt_id": 105, "shipments": [], "is_shipped": False},                                                # zaman yok
}
POSTS = []
class FakeEtsy:
    remaining = 5000
    def __init__(self, store): pass
    def get(self, path, params=None, ok404=False):
        rid = path.rstrip("/").split("/")[-1]
        return copy.deepcopy(RECEIPTS[rid])
    def post(self, path, data):
        rid = path.split("/receipts/")[1].split("/")[0]
        POSTS.append((rid, dict(data)))
        RECEIPTS[rid]["shipments"].append({"carrier_name": data["carrier_name"], "tracking_code": data["tracking_code"]})
        RECEIPTS[rid]["is_shipped"] = True
        return {}
class FakeStore:
    def __init__(self, *a, **k): pass
    def needs_refresh(self): return False
class FakeProdigi:
    def siparisler(self, top=50):      # STATE disi gecmis siparisler (Ivan kanal siparisi + numune paketi)
        return [{"id": "ord_IVAN", "merchantReference": "4175473435", "status": {"stage": "Complete"}, "items": []},
                {"id": "ord_NUMUNE", "merchantReference": "", "status": {"stage": "Complete"},
                 "items": [{"merchantReference": "0"}]}]
    def get_order(self, oid): return 200, {"order": {}}
R.Prodigi = lambda *a, **k: FakeProdigi()
R.load_prodigi_key = lambda env: "x"
R.TokenStore = FakeStore; R.Etsy = FakeEtsy
R.sku_haritasi = lambda prod, boylar: ({b: f"GLOBAL-HPR-{b}" for b in boylar}, [])
R.etsy_receipts = lambda *a, **k: []
R.otomasyonlar = lambda *a, **k: None
LINK = {}   # url -> sahte link durumu (varsayilan ok)
R.takip_url_durumu = lambda url, zaman_asimi=20: LINK.get(url, "ok")
os.environ.update(TOKEN_FILE=str(WORK / "tok.json"), ETSY_SHOP_ID="39729443", ETSY_API_KEY="k", ETSY_SHARED_SECRET="s")

def state_yaz():
    with STATE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=R.COLS); w.writeheader()
        for rid in RECEIPTS:
            w.writerow({"receipt_id": rid, "stage": "shipped", "prodigi_order_id": f"ord_{rid}", "tracking": N,
                        "carrier": "UPS", "carrier_service": "UPS Mail Innovations",
                        "tracking_url": "https://tracking.ups-mi.net/packageID/" + N})
def run(ek=()):
    sys.argv = ["order_router.py", "--env", "live", "--state", str(STATE), "--out", str(OUT), "--apply",
                "--approve-mode", "off", "--etsy-writes", *ek]
    try:
        R.main(); return 0
    except SystemExit as e:
        return e.code
def stage():
    return {r["receipt_id"]: r["stage"] for r in csv.DictReader(STATE.open(encoding="utf-8")) if r["receipt_id"] != R.META_ID}

state_yaz()
rc = run()
st1 = stage()
print("kosu1 POST:", POSTS, "| stage:", st1)
kontrol("I1 yalniz YENI ve gonderisiz receipt'e (103) tek POST", [p[0] for p in POSTS] == ["103"], POSTS)
kontrol("I2 POST govdesi usps + tam numara", POSTS and POSTS[0][1]["carrier_name"] == "usps" and POSTS[0][1]["tracking_code"] == N)
kontrol("I3 gecmis/elle olanlar atlandi (kalici)", st1["101"] == st1["102"] == st1["104"] == "atlandi", st1)
kontrol("I4 yeni siparis dogrulandi -> tracked", st1["103"] == "tracked", st1)
kontrol("I5 zamansiz receipt: POST yok, shipped kalir + hata", st1["105"] == "shipped" and rc not in (0, None), rc)
kontrol("I6 MUSTERI tipi (102) Etsy kaydi degismedi", RECEIPTS["102"]["shipments"] == [{"carrier_name": "UPS", "tracking_code": N}])
POSTS.clear(); rc2 = run()
kontrol("I7 ikinci kosu: sifir POST", POSTS == [], POSTS)
# sinir geriye cekilmeye calisilirsa gecmis siparis yine korunur
POSTS.clear(); RECEIPTS["101"]["shipments"] = []; state_yaz(); RECEIPTS["103"]["shipments"] = []
run(["--takip-baslangic", "2020-01-01 00:00:00"])
kontrol("I8 --takip-baslangic geriye: 101 yine POST almaz", "101" not in [p[0] for p in POSTS], POSTS)
POSTS.clear(); state_yaz()
rc3 = run(["--takip-baslangic", "dun"])
kontrol("I9 bozuk --takip-baslangic: kosu baslamadan durur, POST yok", POSTS == [] and "HATA" in str(rc3), rc3)
rapor = (OUT / "REPORT.md").read_text(encoding="utf-8")
kontrol("I10 koruma logu: STATE disi siparisler YAZMAZ olarak listelenir",
        "TAKIP KORUMASI ord_IVAN" in rapor and "TAKIP KORUMASI ord_NUMUNE" in rapor, "")
kontrol("I11 koruma logu: STATE satirlari listelenir", all(f"TAKIP KORUMASI {r}:" in rapor for r in ("101", "102")), "")

# ================= link erisim engeli (403/429) = uyari; 404/bozuk = gercek hata
rec_ok = {"receipt_id": 1, "shipments": [{"carrier_name": "usps", "tracking_code": N}]}
for durum, beklenen in (("HTTP 403", True), ("HTTP 429", True), ("HTTP 401", True),
                        ("HTTP 404", False), ("HTTP 500", False), ("ConnectionError", False), ("url yok", False)):
    ok_l, e_l = T.dogrula(rec_ok, 1, plan, durum)
    kontrol(f"L {durum}: {'PASS+uyari' if beklenen else 'FAIL'}",
            ok_l == beklenen and bool(T.link_uyarisi(durum)) == beklenen, e_l)
ok_c, e_c = T.dogrula({"receipt_id": 1, "shipments": [{"carrier_name": "ups", "tracking_code": N}]}, 1, plan, "HTTP 403")
kontrol("L 403 + yanlis carrier: yine FAIL (engel carrier hatasini ortmez)", not ok_c and any("carrier" in e for e in e_c), e_c)

SP = "LX104881201NL"
for rid, url, durum in (("106", "https://engel.example/" + SP, "HTTP 403"), ("107", "https://yok.example/" + SP, "HTTP 404")):
    RECEIPTS[rid] = {"receipt_id": int(rid), "create_timestamp": YENI, "shipments": [], "is_shipped": False}
    LINK[url] = durum
with STATE.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=R.COLS); w.writeheader()
    for rid, url in (("106", "https://engel.example/" + SP), ("107", "https://yok.example/" + SP)):
        w.writerow({"receipt_id": rid, "stage": "shipped", "prodigi_order_id": f"ord_{rid}", "tracking": SP,
                    "carrier": "Royal Mail", "carrier_service": "Tracked", "tracking_url": url})
POSTS.clear(); rc_l1 = run(); st_l = {r["receipt_id"]: r for r in csv.DictReader(STATE.open(encoding="utf-8"))}
rap1 = (OUT / "REPORT.md").read_text(encoding="utf-8")
kontrol("L-I1 403: tek POST, tracked + UYARI notu", ("106" in [x[0] for x in POSTS]) and st_l["106"]["stage"] == "tracked"
        and "UYARI" in st_l["106"]["note"] and "HATA: 106" not in rap1, st_l["106"]["note"])
kontrol("L-I2 404: POST yapildi ama shipped kalir + gercek hata", st_l["107"]["stage"] == "shipped"
        and "HATA: 107" in rap1 and rc_l1 not in (0, None), rc_l1)
POSTS.clear(); rc_l2 = run(); rap2 = (OUT / "REPORT.md").read_text(encoding="utf-8")
kontrol("L-I3 ikinci kosu: 106 icin hata/uyari tekrari yok, sifir POST", POSTS == [] and "106: TRACKED" not in rap2
        and "HATA: 106" not in rap2, POSTS)
kontrol("L-I4 ikinci kosu: 404 hatasi durur (gercek hata), POST yok", "HATA: 107" in rap2, "")

gecen = sum(o for _, o in sonuc)
print(f"koruma testleri: {gecen}/{len(sonuc)} PASS")
sys.exit(0 if gecen == len(sonuc) else 1)
