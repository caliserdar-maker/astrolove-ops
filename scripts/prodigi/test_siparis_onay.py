"""Siparis ONAY akisi yerel testi (ag yok): Etsy sahte, Prodigi HTTP katmani sahte (router'in GERCEK submit_package /
order_body kodu kosar), Drive linki sahte, tablo yerel CSV. Sahte siparisler: EMILY/JAMES (POD + dijital) + Kiril isim.
Calistir: python3 scripts/prodigi/test_siparis_onay.py"""
import contextlib
import copy
import csv
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R
import siparis_onay as O

W = Path(tempfile.mkdtemp(prefix="siparis_onay_"))
SABLON = str(ROOT / "scripts/prodigi/test_musteri_mesajlari.md")
ADRES = {"name": "Test Buyer", "first_line": "1 Test Street", "second_line": "", "city": "Testville", "state": "NY",
         "zip": "10001", "country_iso": "US", "buyer_email": "test@example.com"}
MESAJ = "It Began With a Kiss in the Rain"


def rec(rid, sku, adlar, ulke="US", dijital=False, baslik=""):
    r = dict(ADRES, receipt_id=rid, country_iso=ulke, is_shipped=False, created_timestamp=int(time.time()) - 7200)
    a, b = adlar
    t = {"transaction_id": rid * 10, "sku": sku, "quantity": 1, "price": {"amount": 4999, "divisor": 100},
         "is_digital": dijital, "title": baslik,
         "variations": [{"formatted_name": "Name under Aries", "formatted_value": a},
                        {"formatted_name": "Name under Leo", "formatted_value": b},
                        {"formatted_name": "Your message", "formatted_value": MESAJ}]}
    r["transactions"] = [t]
    return r


POD, DIJ, KIR = 8800000001, 8800000002, 8800000003
REC = [rec(POD, "POD-ARI_LEO-DB-8x10", ("Emily", "James")),
       rec(DIJ, "", ("Emily", "James"), dijital=True, baslik="Aries Leo Couple Zodiac Digital Art, Personalized Names"),
       rec(KIR, "POD-ARI_LEO-MB-8x10", ("Анна", "James"))]
GIZLI = ["Emily", "EMILY", "James", "JAMES", "Анна", "АННА", MESAJ, "Test Street", "Testville", "test@example.com",
         str(POD), str(DIJ), str(KIR)]


class Sahte:
    def __init__(s, hata=False):
        s.cagri, s.orders, s.hata = [], {}, hata

    def call(s, method, path, body=None):
        s.cagri.append((method, path, body))
        if method == "GET" and path.startswith("/orders?"):
            return 200, {"orders": list(s.orders.values()), "hasMore": False}
        if method == "GET" and path.startswith("/products/"):
            return 200, {"product": {"sku": path.split("/")[2]}}
        if method == "POST" and path == "/quotes":
            return 200, {"quotes": [{"shipmentMethod": "Budget", "costSummary": {"items": {"amount": "12"}, "shipping": {"amount": "6"}}}]}
        if method == "POST" and path == "/orders":
            if s.hata:
                return 400, {"outcome": "ValidationFailed"}
            key = body["idempotencyKey"]
            o = next((o for o in s.orders.values() if o["merchantReference"] == key), None)
            if not o:
                o = {"id": f"ord_T{len(s.orders) + 1}", "merchantReference": key, "created": "2026-09-25T12:00:00Z",
                     "status": {"stage": "InProgress", "issues": [], "details": {"downloadAssets": "Complete"}},
                     "items": [{"merchantReference": i["merchantReference"]} for i in body["items"]], "_govde": body}
                s.orders[o["id"]] = o
            return 200, {"outcome": "Created", "order": o}
        if method == "GET" and path.startswith("/orders/"):
            return 200, {"order": s.orders[path.split("/")[2]]}
        raise AssertionError(f"beklenmeyen Prodigi cagrisi {method} {path}")


S = Sahte()
Gercek = R.Prodigi


class FP(Gercek):
    def __init__(self, *a):
        self.base = "sahte"

    def call(self, method, path, body=None):
        return S.call(method, path, body)


LINK = {"acik": {}, "kapali": []}


class FL:
    def open(self, remote):
        fid = f"FID{abs(hash(remote)) % 10 ** 8}"
        LINK["acik"][fid] = remote
        return fid, "PERM1", f"https://drive.google.com/uc?export=download&id={fid}&confirm=t"

    def close(self, fid, pid):
        LINK["acik"].pop(fid, None)
        LINK["kapali"].append(fid)


class FE:
    remaining = 5000
    def __init__(s, st): pass
    def get(s, *a, **k): return {}
    def post(s, *a): raise AssertionError("ETSY POST")
    def put(s, *a): raise AssertionError("ETSY PUT")
    def patch(s, *a): raise AssertionError("ETSY PATCH")


class FS:
    def __init__(s, *a): pass
    def needs_refresh(s): return False


R.Prodigi = FP; R.load_prodigi_key = lambda e: "x"; R.TokenStore = FS; R.Etsy = FE; R.DriveLinks = FL
R.etsy_receipts = lambda *a, **k: copy.deepcopy(REC)
R.otomasyonlar = lambda *a, **k: None
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1", ETSY_SHARED_SECRET="test-anahtar")
TABLO = W / "SIPARIS_ONAY.csv"


def run(ad, ek=()):
    R.DIKKAT_EK.clear(); O.BILDIRIMLER.clear()
    sys.argv = ["r", "--env", "sandbox", "--state", str(W / "state.csv"), "--out", str(W / ad), "--packages", str(W / "pk"),
                "--approve-mode", "off", "--min-yas-dk", "60", "--sablonlar", SABLON, "--onay-tablo", f"yerel:{TABLO}",
                "--asset-wait", "0", "--apply", *ek]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            R.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    return rc, buf.getvalue()


def tablo():
    return {r["KOD"]: r for r in O.YerelTablo(TABLO).satirlar()}


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def sizinti(log):
    return [g for g in GIZLI if g in log]


KP, KD, KK = O.kod(POD), O.kod(DIJ), O.kod(KIR)
LOGLAR = []
# ---- 1) yeni siparisler: on kontrol + tablo + uretim listesi
rc1, log1 = run("k1"); LOGLAR.append(log1)
T = tablo()
k("3 satir tabloda (POD, dijital, Kiril)", {KP, KD, KK} <= set(T), sorted(T))
k("POD temiz -> DOSYA_URETILIYOR, basilacak EMILY/JAMES", T[KP]["DURUM"] == O.D_DOSYA and T[KP]["ISIM1"] == "EMILY" and T[KP]["ISIM2"] == "JAMES"
  and T[KP]["CIFT"] == "ARIES_LEO" and T[KP]["RENK"] == "DEEP_BLACK" and T[KP]["BOY"] == "8x10")
k("dijital temiz -> DOSYA_URETILIYOR, urun DIJITAL, cift basliktan", T[KD]["DURUM"] == O.D_DOSYA and T[KD]["URUN"] == "DIJITAL" and T[KD]["CIFT"] == "ARIES_LEO")
k("Kiril -> MUSTERIYE MESAJ GEREKLI + sablon 2", T[KK]["DURUM"] == O.D_MESAJ and "KIRIL_ISIM" in T[KK]["ON_KONTROL"] and "2" in T[KK]["SABLON"].split(","), T[KK]["SABLON"])
uretim = (W / "k1/URETIM.txt").read_text().split()
k("uretim listesi: POD + dijital, Kiril YOK", sorted(uretim) == sorted([str(POD), str(DIJ)]), uretim)
kart = (W / f"k1/SIPARIS_ISIM/{POD}.md").read_text(encoding="utf-8")
k("POD kartinda uretim girdisi (cift/renk/boy/isimler/mesaj/urun)", "- cift: ARIES_LEO" in kart and "- boy: 8x10" in kart
  and "- isim1: EMILY" in kart and f"- mesaj: {MESAJ}" in kart and "- urun: pod" in kart)
k("Kiril kartinda uretim girdisi YOK", "## Uretim girdisi" not in (W / f"k1/SIPARIS_ISIM/{KIR}.md").read_text(encoding="utf-8"))
pkg = json.loads((W / f"k1/{POD}.json").read_text())
k("POD paketi: kisisel baski dosyasi yolu + SKU + adres", pkg["items"][0]["asset_remote"] == f"{O.DRIVE_KOK}/{POD}/BASKI_8x10.jpg"
  and pkg["order"]["items"][0]["sku"] == "GLOBAL-HPR-8x10" and pkg["order"]["recipient"]["address"]["postalOrZipCode"] == "10001")
k("Prodigi'ye siparis YOK (onay yok)", not [c for c in S.cagri if c[0] == "POST" and c[1] == "/orders"])
k("Kiril bildirimi (musteri mesaji gerekli)", f"::error title=MUSTERIYE MESAJ GEREKLI {KK}::" in log1 and rc1 not in (0, None))
# pakete Drive'dan gelecek sekilde packages dizinine koy (workflow: TEMP/POD_ORDERS -> _work/packages)
(W / "pk").mkdir(exist_ok=True)
(W / "pk" / f"{POD}.json").write_text((W / f"k1/{POD}.json").read_text())

# ---- 2) uretim sonucu (siparis_dosyasi.py KAPI_RAPORU) -> ONAY_BEKLIYOR + bildirim linkleri
link = lambda yol, klasor=False: f"https://drive.google.com/{'drive/folders' if klasor else 'file/d'}/X{abs(hash(yol)) % 10 ** 6}"
tb = O.YerelTablo(TABLO)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    O.BILDIRIMLER.clear()
    d1 = O.uretildi(tb, str(POD), {"urun": "POD", "boy": "8x10", "durum": "URETILDI", "kapilar_gecti": True}, link=link)
    d2 = O.uretildi(tb, str(DIJ), {"urun": "DIJITAL", "durum": "URETILDI", "kapilar_gecti": True}, link=link)
    d3 = O.uretildi(tb, str(POD), {"urun": "POD", "boy": "8x10", "durum": "URETILDI", "kapilar_gecti": True}, link=link)
log2 = buf.getvalue(); LOGLAR.append(log2)
T = tablo()
k("uretildi: POD + dijital ONAY_BEKLIYOR, tekrar cagri degistirmez", d1 == d2 == O.D_ONAY and d3 == O.D_ONAY and T[KP]["DURUM"] == O.D_ONAY)
k("tabloda KONTROL / BASKI / x3 linkleri", all(T[KP][c].startswith("https://drive.google.com/") for c in ("KONTROL_KLASOR", "BASKI", "ISIM_x3", "MESAJ_x3")))
k("bildirim: ozet + x3 linkleri + tam cozunurluk + tablo satiri", f"::error title=ONAY BEKLIYOR {KP}::POD DEEP_BLACK 8x10" in log2
  and "isim x3: https://" in log2 and "tam cozunurluk: https://" in log2 and "tablo satiri: file://" in log2 and log2.count("ONAY BEKLIYOR") == 2)

# ---- 3) onay yokken izleyici bir sey gondermez
rc3, log3 = run("k3"); LOGLAR.append(log3)
k("onay kutusu bos -> Prodigi'ye gonderim yok", not [c for c in S.cagri if c[0] == "POST" and c[1] == "/orders"])

# ---- 4) Serdar ONAY'i isaretler
for kk_ in (KP, KD):
    tb.guncelle(tablo()[kk_]["_no"], {"ONAY": "TRUE"})
rc4, log4 = run("k4"); LOGLAR.append(log4)
T = tablo()
post = [c for c in S.cagri if c[0] == "POST" and c[1] == "/orders"]
govde = post[0][2] if post else {}
k("POD: tek Prodigi siparisi, idempotencyKey etsy-<receipt>", len(post) == 1 and govde["idempotencyKey"] == f"etsy-{POD}")
k("POD: dosya linki gecici Drive linki (kisisel BASKI), dogru SKU", govde["items"][0]["assets"][0]["url"].startswith("https://drive.google.com/uc?")
  and govde["items"][0]["sku"] == "GLOBAL-HPR-8x10" and list(LINK["acik"].values()) in ([], [f"{O.DRIVE_KOK}/{POD}/BASKI_8x10.jpg"]))
k("POD: tablo PRODIGI_GONDERILDI + order id", T[KP]["DURUM"] == O.D_PRODIGI and T[KP]["PRODIGI"] == "ord_T1", T[KP]["DURUM"])
k("dijital: CHATGPT_YUKLEME_BEKLIYOR, Prodigi'ye gitmez", T[KD]["DURUM"] == O.D_CHATGPT and len(post) == 1)
k("bildirimler: PRODIGI GONDERILDI + CHATGPT", f"::error title=PRODIGI GONDERILDI {KP}::" in log4 and f"::error title=CHATGPT YUKLEME BEKLIYOR {KD}::" in log4)
st = {r["receipt_id"]: r for r in csv.DictReader(open(W / "state.csv", encoding="utf-8"))}
k("STATE: POD ordered, dijital dijital_bekliyor, Kiril ISIM_BEKLIYOR", st[str(POD)]["stage"] == "ordered"
  and st[str(DIJ)]["stage"] == "dijital_bekliyor" and st[str(KIR)]["stage"] == "ISIM_BEKLIYOR")
k("indirilince gecici izin kapandi", not LINK["acik"] and LINK["kapali"], LINK)

# ---- 5) tekrar kosu: idempotent
rc5, log5 = run("k5"); LOGLAR.append(log5)
k("tekrar: ikinci Prodigi siparisi YOK", len([c for c in S.cagri if c[0] == "POST" and c[1] == "/orders"]) == 1)
k("tekrar: yeni bildirim yok", "::error title=" not in log5, [l for l in log5.splitlines() if l.startswith("::error")][:2])
k("tekrar: tablo degismedi", tablo()[KP]["DURUM"] == O.D_PRODIGI and tablo()[KD]["DURUM"] == O.D_CHATGPT)

# ---- 6) Prodigi hatasi -> HATA + DUR + bildirim
S2 = Sahte(hata=True)
S.__dict__.update(S2.__dict__)
os.replace(W / "state.csv", W / "state_ok.csv"); os.replace(TABLO, W / "tablo_ok.csv")
run("h1")
tb2 = O.YerelTablo(TABLO)
with contextlib.redirect_stdout(io.StringIO()):
    O.uretildi(tb2, str(POD), {"urun": "POD", "boy": "8x10", "durum": "URETILDI", "kapilar_gecti": True}, link=link)
(W / "pk" / f"{POD}.json").write_text((W / f"h1/{POD}.json").read_text())
tb2.guncelle(tablo()[KP]["_no"], {"ONAY": "TRUE"})
rc6, log6 = run("h2"); LOGLAR.append(log6)
k("Prodigi hatasi: tablo HATA, kosu DUR, bildirim", tablo()[KP]["DURUM"] == O.D_HATA and rc6 not in (0, None)
  and f"::error title=SIPARIS HATA {KP}::" in log6)
k("Prodigi hatasi: gecici Drive izni hemen kapandi", not LINK["acik"], LINK["acik"])

# ---- 7) guvenlik: loglarda musteri verisi yok
sz = sorted({g for lg in LOGLAR for g in sizinti(lg)})
k("loglarda isim / mesaj / adres / receipt YOK", not sz, sz)
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
