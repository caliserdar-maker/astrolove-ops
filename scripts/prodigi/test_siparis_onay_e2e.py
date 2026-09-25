#!/usr/bin/env python3
"""Siparis ONAY akisi UCTAN UCA testi (kisisel-pilot workflow'u ile, dal siparis-onay). CANLI SIPARIS YOK.

Etsy: SAHTE (receipt'ler bu dosyada; Etsy'ye hic cagri yok). Prodigi: SANDBOX (anahtar Drive'dan).
Drive + onay tablosu: GERCEK, test klasoru TEMP/SIPARIS_TEST (canli TEMP/SIPARIS'e dokunulmaz).
Baski dosyasi: GERCEK uretec (siparis-baski-v1 siparis_dosyasi.py), logu yalniz Drive'a.
Siparisler (sahte): 1 POD (EMILY/JAMES, Aries-Leo Deep Black 8x10), 1 dijital (EMILY/JAMES), 1 hatali (Kiril isim).
Adimlar: router (kayit) -> uretec -> uretildi -> ONAY isaretle (Serdar yerine) -> router (izle: POD sandbox siparisi,
dijital CHATGPT) -> router tekrar (idempotens) -> izin kapat + temizlik. Actions loguna yalniz PASS/FAIL + opak kod.
"""
import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "requests==2.34.2"], check=True)
ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts/prodigi")); sys.path.insert(0, str(ROOT / "scripts/etsy"))
import order_router as R          # noqa: E402
import siparis_onay as O          # noqa: E402

T0 = time.time()
DAMGA = time.strftime("%m%d%H%M", time.gmtime())
KOK = "gdrive:ASTROLOVE/TEMP/SIPARIS_TEST"
O.DRIVE_KOK = KOK                 # paket asset yolu + tablo klasoru test kokune
W = ROOT / "_e2e"; W.mkdir(exist_ok=True)
POD, DIJ, KIR = int(f"98{DAMGA}"), int(f"97{DAMGA}"), int(f"96{DAMGA}")
MESAJ = "It Began With a Kiss in the Rain"
ADRES = {"name": "Test Buyer", "first_line": "123 Test Street", "second_line": "", "city": "Springfield", "state": "IL",
         "zip": "62701", "country_iso": "US", "buyer_email": "test@example.com"}
GIZLI = ["Emily", "EMILY", "James", "JAMES", "Анна", "АННА", MESAJ, "Test Street", "Springfield", "test@example.com",
         str(POD), str(DIJ), str(KIR)]


def rec(rid, sku, a, b, dijital=False, baslik=""):
    r = dict(ADRES, receipt_id=rid, is_shipped=False, created_timestamp=int(time.time()) - 7200)
    r["transactions"] = [{"transaction_id": rid + 1, "sku": sku, "quantity": 1, "price": {"amount": 4999, "divisor": 100},
                          "is_digital": dijital, "title": baslik,
                          "variations": [{"formatted_name": "Name under Aries", "formatted_value": a},
                                         {"formatted_name": "Name under Leo", "formatted_value": b},
                                         {"formatted_name": "Your message", "formatted_value": MESAJ}]}]
    return r


REC = [rec(POD, "POD-ARI_LEO-DB-8x10", "Emily", "James"),
       rec(DIJ, "", "Emily", "James", dijital=True, baslik="Aries Leo Couple Zodiac Digital Art, Personalized Names"),
       rec(KIR, "POD-ARI_LEO-MB-8x10", "Анна", "James")]


class FE:                                              # Etsy SAHTE: okuma bos, yazma yasak
    remaining = 5000
    def __init__(s, st): pass
    def get(s, *a, **k): return {}
    def post(s, *a, **k): raise AssertionError("ETSY YAZMA")
    put = patch = delete = post


class FS:
    def __init__(s, *a): pass
    def needs_refresh(s): return False


R.TokenStore = FS; R.Etsy = FE
R.etsy_receipts = lambda *a, **k: copy.deepcopy(REC)
R.otomasyonlar = lambda *a, **k: None
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="0")
subprocess.run(["rclone", "copyto", "gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/MUSTERI_MESAJLARI.md", str(W / "MUSTERI_MESAJLARI.md")], check=True)
TABLO = f"csv:SIPARIS_ONAY_TEST_{DAMGA}"
LOGLAR, BILDIRIM, sonuc = [], [], []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul))
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""), flush=True)


def router(ad, ek=()):
    R.DIKKAT_EK.clear(); O.BILDIRIMLER.clear()
    sys.argv = ["r", "--env", "sandbox", "--state", str(W / "state.csv"), "--out", str(W / ad), "--packages", str(W / "pk"),
                "--approve-mode", "off", "--min-yas-dk", "60", "--sablonlar", str(W / "MUSTERI_MESAJLARI.md"),
                "--onay-tablo", TABLO, "--asset-wait", "9", "--apply", *ek]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            R.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    except Exception as e:                            # noqa: BLE001
        rc = f"{type(e).__name__}: {str(e)[:200]}"
    log = buf.getvalue(); LOGLAR.append(log)
    BILDIRIM.extend(l for l in log.splitlines() if l.startswith("::error"))
    (W / f"{ad}.log").write_text(log, encoding="utf-8")   # yalniz Drive'a gider
    return rc, log


def tablo():
    return {r["KOD"]: r for r in O.tablo_ac(TABLO).satirlar()}


KP, KD, KK = O.kod(POD), O.kod(DIJ), O.kod(KIR)
print(f"test kodlari: POD {KP} | dijital {KD} | Kiril {KK}", flush=True)

# 1) router: kayit + on kontrol + tablo + uretim listesi + paket
rc1, log1 = router("r1")
T = tablo()
tur = O.tablo_ac(TABLO).tur
k(f"tablo acildi ({tur}), 3 satir", {KP, KD, KK} <= set(T), f"rc={rc1}")
k("POD + dijital DOSYA_URETILIYOR, Kiril MUSTERIYE_MESAJ + sablon 2",
  T.get(KP, {}).get("DURUM") == O.D_DOSYA and T.get(KD, {}).get("DURUM") == O.D_DOSYA
  and T.get(KK, {}).get("DURUM") == O.D_MESAJ and "2" in T.get(KK, {}).get("SABLON", "").split(","))
uretim = (W / "r1/URETIM.txt").read_text().split() if (W / "r1/URETIM.txt").exists() else []
k("uretim listesi POD + dijital (Kiril yok)", sorted(uretim) == sorted([str(POD), str(DIJ)]))
(W / "pk").mkdir(exist_ok=True)
for f in (W / "r1").glob("*.json"):
    if f.stem.isdigit():
        (W / "pk" / f.name).write_text(f.read_text())
subprocess.run(["rclone", "copy", str(W / "r1/SIPARIS_ISIM"), "gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM", "--include", "*.md", "-q"], check=True)

# 2) uretec (gercek) -> Drive SIPARIS_TEST/<rid>, logu yalniz Drive'a
sb = W / "sb"; sb.mkdir(exist_ok=True)
subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "siparis-baski-v1"], check=True)
arc = subprocess.run(["git", "archive", "FETCH_HEAD", "scripts/medya_v1"], capture_output=True, check=True).stdout
subprocess.run(["tar", "-x", "-C", str(sb)], input=arc, check=True)
sure = {}
for rid, lim in ((POD, 1800), (DIJ, 2700)):
    t = time.time()
    lp = W / f"uretim_{O.kod(rid)}.log"
    try:
        with lp.open("w") as fh:
            p = subprocess.run([sys.executable, str(sb / "scripts/medya_v1/siparis_dosyasi.py"), "--kart", f"{rid}.md"],
                               stdout=fh, stderr=subprocess.STDOUT, timeout=lim)
        rcu = p.returncode
    except subprocess.TimeoutExpired:
        rcu = "zaman asimi"
    sure[O.kod(rid)] = round((time.time() - t) / 60, 1)
    subprocess.run(["rclone", "move", f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{rid}", f"{KOK}/{rid}", "-q"])
    subprocess.run(["rclone", "copyto", str(lp), f"{KOK}/{rid}/URETIM.log", "-q"])
    rp = ROOT / "_siparis" / str(rid) / "KAPI_RAPORU.json"
    rapor = json.loads(rp.read_text()) if rp.exists() else {"durum": "HATA", "hata": f"uretec {rcu}"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        O.BILDIRIMLER.clear()
        d = O.uretildi(O.tablo_ac(TABLO), str(rid), rapor, kok=KOK)
    LOGLAR.append(buf.getvalue()); BILDIRIM.extend(l for l in buf.getvalue().splitlines() if l.startswith("::error"))
    k(f"uretec {O.kod(rid)}: {rapor.get('durum')} kapi={rapor.get('kapilar_gecti')} -> {d} ({sure[O.kod(rid)]} dk)",
      d == O.D_ONAY, f"cikis {rcu}")
T = tablo()
k("tabloda KONTROL/BASKI/x3 linkleri (POD)", all(str(T[KP].get(c, "")).startswith("https://") for c in ("KONTROL_KLASOR", "BASKI", "ISIM_x3", "MESAJ_x3")))

# 3) Serdar yerine ONAY (POD + dijital)
tb = O.tablo_ac(TABLO)
for kk_ in (KP, KD):
    tb.guncelle(tablo()[kk_]["_no"], {"ONAY": True if tb.tur == "sheets" else "EVET"})
rc2, log2 = router("r2")
T = tablo()
k("POD onaylandi -> Prodigi SANDBOX siparisi", T[KP].get("DURUM") == O.D_PRODIGI and str(T[KP].get("PRODIGI", "")).startswith("ord_"),
  f"{T[KP].get('DURUM')} {T[KP].get('NOT', '')[:80]}")
k("dijital onaylandi -> CHATGPT_YUKLEME_BEKLIYOR", T[KD].get("DURUM") == O.D_CHATGPT)
k("Kiril: onay yok, Prodigi yok", T[KK].get("DURUM") == O.D_MESAJ)

# 4) idempotens: tekrar kosu -> ikinci siparis yok
rc3, log3 = router("r3")
prod = R.Prodigi(R.load_prodigi_key("sandbox"), "sandbox")
ayni = [o for o in prod.siparisler(100) if str(o.get("merchantReference")) == f"etsy-{POD}"]
k("sandbox'ta etsy-<receipt> siparisi TEK", len(ayni) == 1, f"{len(ayni)} adet")
k("tekrar kosuda yeni bildirim yok", not [l for l in log3.splitlines() if l.startswith("::error")])

# 5) gecici Drive izinleri: indirilince kapanir; acik kalan varsa test sonunda kapatilir
st = R.read_state(W / "state.csv")
acik = json.loads((st.get(str(POD)) or {}).get("asset_perms") or "[]")
k("gecici Drive izni kapandi (Prodigi indirdi)", not acik, f"{len(acik)} acik")
if acik:
    dl = R.DriveLinks()
    for fid, pid in acik:
        dl.close(fid, pid)

# 6) guvenlik: Actions'a gidecek her ciktida musteri verisi yok
sz = sorted({g for lg in LOGLAR for g in GIZLI if g in lg})
k("loglarda isim/mesaj/adres/receipt YOK", not sz, f"{len(sz)} eslesme")
for l in BILDIRIM:                                     # bildirimler Actions'ta gorunsun (e-posta icerigi): yalniz kod + link
    print(l.replace("::error", "::notice"), flush=True)

# temizlik + rapor (Drive)
for rid in (POD, DIJ, KIR):
    subprocess.run(["rclone", "deletefile", f"gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/{rid}.md"], capture_output=True)
ozet = {"tablo": O.tablo_ac(TABLO).link, "tablo_tur": tur, "sure_dk": sure, "toplam_dk": round((time.time() - T0) / 60, 1),
        "sonuc": f"{sum(sonuc)}/{len(sonuc)}", "kod": {"POD": KP, "DIJITAL": KD, "KIRIL": KK}}
(W / "E2E_RAPOR.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False))
subprocess.run(["rclone", "copy", str(W), f"{KOK}/_E2E_{DAMGA}", "--include", "*.log", "--include", "*.json", "--include", "*.md",
                "--max-depth", "2", "-q"])
print(f"{sum(sonuc)}/{len(sonuc)} PASS | tablo {ozet['tablo']} | toplam {ozet['toplam_dk']} dk | Drive {KOK}/_E2E_{DAMGA}", flush=True)
sys.exit(0 if all(sonuc) else 1)
