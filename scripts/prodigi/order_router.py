#!/usr/bin/env python3
"""
PRODIGI SIPARIS YONLENDIRICI (6 Eyl 2026): Etsy POD siparisi -> Prodigi siparisi -> takip -> Etsy.

Akis (her kosu):
  1. Etsy getShopReceipts (was_paid, unshipped); SKU POD-<burc3>_<burc3>-<ed2>-<SIZE> (pod_sku.py) olan islemler.
  2. Yeni receipt: ulke US/CA/AU/GB degilse MANUAL; Prodigi teklif (Budget) ile maliyet kontrolu,
     marj < --margin-min ise MARJ_DUSUK uyarisi (durdurmaz); apply'da baski dosyasina gecici Drive
     linki (anyone:reader) verilir, POST /orders (idempotencyKey = etsy-<receipt_id>) -> ordered.
  3. ordered: GET /orders/{id}; assetler indirildiyse gecici izin kaldirilir; kargo takip numarasi
     geldiyse shipped.
  4. shipped: Etsy createReceiptShipment (tracking, carrier) -> tracked. (--etsy-writes yoksa atlanir.)
  Idempotent: STATE (receipt_id) + Prodigi idempotencyKey. Prodigi/Etsy hatasi -> STATE yazilir, DUR (exit 1).

ONAYLI MOD (Mo 7 Eyl 2026, varsayilan --approve-mode on; 78 ilan yayinda):
  Kosu yalniz PAKET HAZIRLAR: her yeni POD receipt'i icin Prodigi siparis govdesi (GLOBAL-HPR SKU,
  asset TEMP/POD_PRINT/<PAIR>/<ED>/<SIZE>.jpg, Budget kargo, alici adresi) + teklif/marj hesaplanir,
  <out>/<receipt_id>.json olarak yazilir (Drive TEMP/POD_ORDERS/), STATE stage="bekliyor".
  PRODIGI'YE SIPARIS GONDERILMEZ. Gonderim yalniz --submit <receipt_id> ile, tek receipt icin olur:
  paket dosyasi okunur, asset linkleri acilir, POST /orders yapilir, sonuc <receipt_id>.result.json
  ve STATE (ordered + prodigi_order_id) olarak yazilir. Ayni receipt IKINCI KEZ GONDERILEMEZ
  (STATE stage ordered/shipped/tracked ya da .result.json varsa atlanir; Prodigi idempotencyKey ikinci kat).
  Kargo takibi Etsy'ye YAZILMAZ, yalnizca loglanir (ayri adim, sonra acilacak).

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE; PRODIGI_API_KEY (yerel) ya da
Drive TEMP/PRODIGI_TOKEN.json (live) / TEMP/PRODIGI_SANDBOX_TOKEN.json (sandbox) rclone ile.
Kullanim:
  order_router.py --env sandbox --state ST.csv --out OUT --dry-run
  order_router.py --env sandbox --state ST.csv --out OUT --apply --test-receipt test.json   # sandbox uctan uca
  order_router.py --env live    --state ST.csv --out OUT --apply --etsy-writes              # canli (onay)
  order_router.py --env live    --state ST.csv --out OUT --approve-mode on                  # paket hazirla (gonderim yok)
  order_router.py --env live    --state ST.csv --out OUT --submit 3412345678                # tek paketi GONDER (onay)
"""
import argparse
import calendar
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "etsy"))
sys.path.insert(0, str(HERE.parent / "pinterest"))
from etsy_common import Etsy, TokenStore, log as elog, mask  # noqa: E402
from pod_sku import parse_sku  # noqa: E402
import takip  # noqa: E402

PRODIGI = {"live": "https://api.prodigi.com/v4.0", "sandbox": "https://api.sandbox.prodigi.com/v4.0"}
KEY_REMOTE = {"live": "gdrive:ASTROLOVE/TEMP/PRODIGI_TOKEN.json", "sandbox": "gdrive:ASTROLOVE/TEMP/PRODIGI_SANDBOX_TOKEN.json"}
PRINT_REMOTE = "gdrive:ASTROLOVE/TEMP/POD_PRINT"
ALLOWED = {"US", "CA", "AU", "GB"}
KARGO_SECENEK = ["Budget", "Standard", "Express", "Overnight"]   # teklifte hepsi sorulur, EN UCUZ secilir
EKLER_USD = 5.00        # hesap ayarindaki ekler (postcard 2.50 + 2 sticker 1.25x2); ord_14538276 olcumu
# SKU semasi pod_sku.py: POD-<burc3>_<burc3>-<edisyon2>-<boyut>
STAGES = ["dryrun", "bekliyor", "manual", "atlandi", "ordered", "shipped", "tracked", "error"]
TUM_BOYLAR = ["5x7", "8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30",
              "24x36", "30x40", "A4", "A3", "A2", "A1"]      # 13 mevcut + 5x7 + A1
COLS = ["receipt_id", "stage", "country", "items", "etsy_total", "prodigi_cost", "margin", "warn", "prodigi_order_id",
        "prodigi_status", "asset_perms", "tracking", "carrier", "carrier_service", "tracking_url", "tracking_son_ayak",
        "carrier_etsy", "sent_tx", "kanal_iptal", "kanal_oid", "alarm_kosu", "ts_utc", "note"]
_secret = None


def log(m):
    if _secret:
        m = str(m).replace(_secret, "***")
    print(m, flush=True)


def load_prodigi_key(env):
    global _secret
    key = os.environ.get("PRODIGI_API_KEY")
    if not key:
        r = subprocess.run(["rclone", "cat", KEY_REMOTE[env]], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"HATA: {KEY_REMOTE[env]} okunamadi (rclone).")
        key = json.loads(r.stdout).get("api_key")
    if not key:
        sys.exit("HATA: Prodigi api_key bos.")
    _secret = key.strip()
    print(f"::add-mask::{_secret}", flush=True)
    return _secret


class Prodigi:
    def __init__(self, key, env):
        self.base = PRODIGI[env]
        self.s = requests.Session()
        self.s.headers.update({"X-API-Key": key, "Content-Type": "application/json"})

    def call(self, method, path, body=None):
        for attempt in range(3):
            r = self.s.request(method, self.base + path, json=body, timeout=60)
            if (r.status_code == 429 or r.status_code >= 500) and attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            break
        try:
            d = r.json()
        except ValueError:
            d = {"raw": r.text[:300]}
        return r.status_code, d

    def quote(self, items, country):
        """Tum kargo secenekleri sorulur, EN UCUZ olan secilir. -> (maliyet, hata, ayrinti)."""
        govde = [{"sku": i["prodigi_sku"], "copies": i["qty"], "assets": [{"printArea": "default"}]} for i in items]
        secenekler, hatalar = [], []
        for yontem in KARGO_SECENEK:
            st, d = self.call("POST", "/quotes", {"shippingMethod": yontem, "destinationCountryCode": country,
                                                  "currencyCode": "USD", "items": govde})
            if st != 200 or not d.get("quotes"):
                hatalar.append(f"{yontem}: HTTP {st}")
                continue
            for q in d["quotes"]:
                cs = q.get("costSummary") or {}
                kalem = float((cs.get("items") or {}).get("amount") or 0)
                kargo = float((cs.get("shipping") or {}).get("amount") or 0)
                secenekler.append({"yontem": q.get("shipmentMethod") or yontem, "kalem": round(kalem, 2),
                                   "kargo": round(kargo, 2), "toplam": round(kalem + kargo, 2)})
        if not secenekler:
            return None, f"quote basarisiz: {'; '.join(hatalar)[:200]}", {}
        en_ucuz = min(secenekler, key=lambda x: x["toplam"])
        ayrinti = {"secenekler": sorted(secenekler, key=lambda x: x["toplam"]), "secilen": en_ucuz,
                   "ekler_tahmini": EKLER_USD}
        return round(en_ucuz["toplam"] + EKLER_USD, 2), "", ayrinti

    def urun(self, sku):
        return self.call("GET", f"/products/{sku}")

    def iptal(self, oid):
        """Taslak/submit edilmemis siparisi iptal eder; geri okuyarak dogrular. -> (ok, aciklama)."""
        st, d = self.call("POST", f"/orders/{oid}/actions/cancel", {})
        st2, d2 = self.get_order(oid)
        stage = str((((d2.get("order") or {}).get("status") or {}).get("stage")) or "")
        return stage.lower() == "cancelled", f"iptal HTTP {st} outcome={d.get('outcome')} -> stage {stage or '?'}"

    def iptal_edilebilir(self, oid):
        """GET /orders/{id} -> actions.cancel.isAvailable. -> (evet_mi, ham_deger)."""
        st, d = self.get_order(oid)
        v = ((((d.get("order") or {}).get("actions") or {}).get("cancel") or {}).get("isAvailable"))
        return str(v).lower() == "yes", str(v)

    def siparisler(self, top=50):
        st, d = self.call("GET", f"/orders?top={top}")
        return (d.get("orders") or []) if st == 200 else []

    def create_order(self, body):
        return self.call("POST", "/orders", body)

    def get_order(self, oid):
        return self.call("GET", f"/orders/{oid}")


# ------------------------------------------------------------------ Drive gecici link
def drive_file_id(remote_path):
    r = subprocess.run(["rclone", "lsjson", remote_path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone lsjson {remote_path}: {r.stderr.strip()[-160:]}")
    items = json.loads(r.stdout)
    if len(items) != 1:
        raise RuntimeError(f"{remote_path}: {len(items)} kayit")
    return items[0]["ID"]


class DriveLinks:
    """Baski dosyasina gecici 'anyone:reader' izni; Prodigi assetleri indirince kaldirilir."""

    def __init__(self):
        from pin_media_perms import Drive, access_token
        self.d = Drive(access_token())

    def open(self, remote_path):
        fid = drive_file_id(remote_path)
        p = self.d.create_anyone(fid, "reader")
        return fid, p["id"], f"https://drive.google.com/uc?export=download&id={fid}&confirm=t"

    def close(self, fid, pid):
        try:
            self.d.delete_perm(fid, pid)
        except RuntimeError as e:
            if "404" not in str(e):
                raise


def sku_haritasi(prod, boylar):
    """Her boy icin GLOBAL-HPR-<boy> canli katalogda var mi? -> ({boy: katalogdaki_sku}, eksikler)."""
    harita, eksik = {}, []
    for b in sorted(set(boylar)):
        bulundu = ""
        for aday in (f"GLOBAL-HPR-{b}", f"GLOBAL-HPR-{b.upper()}", f"GLOBAL-HPR-{b.lower()}"):
            st, d = prod.urun(aday)
            if st == 200:
                bulundu = ((d.get("product") or {}).get("sku")) or aday
                break
        if bulundu:
            harita[b] = bulundu
        else:
            eksik.append(b)
    return harita, eksik


def prodigi_indeks(prod, top=50):
    """Prodigi'deki (iptal edilmemis) siparislerin referanslari: receipt id'leri ve kalem referanslari."""
    ref, kalem_ref, kayit = set(), set(), {}
    for o in prod.siparisler(top):
        durum = o.get("status") or {}
        stage = str(durum.get("stage") or "")
        if stage.lower() == "cancelled":
            continue
        _mr = str(o.get("merchantReference") or "")
        bilgi = {"id": o.get("id"), "stage": stage, "issues": bool(durum.get("issues")), "mr": _mr,
                 "created": o.get("created") or "", "kanal": not _mr.startswith("etsy-")}
        mr = str(o.get("merchantReference") or "")
        if mr:
            ref.add(mr)
            kayit.setdefault(mr, bilgi)
            if "-" in mr:                      # etsy-<receipt>-<boy>
                parca = mr.split("-")
                if len(parca) > 1 and parca[1].isdigit():
                    ref.add(parca[1])
                    kayit.setdefault(parca[1], bilgi)
        for k in o.get("items") or []:
            kr = str(k.get("merchantReference") or "")
            if kr:
                kalem_ref.add(kr)
                kayit.setdefault(kr, bilgi)
    return {"ref": ref, "kalem_ref": kalem_ref, "kayit": kayit}


URETIMDE = {"inprogress", "complete", "shipped"}
META_ID = "_META"            # STATE icinde tek satirlik kosu hafizasi (note alaninda JSON)
SINIR_SAAT = 24              # ilk canli kosudan sonra hatasiz gecmesi gereken sure
SINIRSIZ = 25                # sinir kalkinca kosu basina ust sinir
KANAL_SESSIZ_GUN = 7         # bu kadar gun yeni kanal siparisi yoksa kanal kopuk sayilir
DIKKAT_EK = []               # DIKKAT.md'ye eklenecek serbest satirlar


def _neden(idx, anahtar, aciklama):
    b = idx["kayit"].get(anahtar) or {}
    return f"{aciklama} ({anahtar} -> {b.get('id')}, {b.get('stage')})"


def kanal_durumu(idx, rid, items):
    """Bu receipt icin Prodigi'de ne var? -> (tur, bilgi, aciklama).
    tur: '' yok | 'bizim' | 'uretimde' | 'taslak'."""
    rid = str(rid)
    anahtarlar = [rid] + [f"etsy-{rid}"] + [f"etsy-{rid}-{i.get('size')}" for i in items] \
        + [str(i.get("transaction_id") or "") for i in items]
    for k in anahtarlar:
        if not k:
            continue
        if k in idx["ref"] or k in idx["kalem_ref"]:
            b = idx["kayit"].get(k) or {}
            stage = str(b.get("stage", "")).lower()
            if k.startswith(f"etsy-{rid}") or str(b.get("mr", "")).startswith(f"etsy-{rid}"):
                return "bizim", b, _neden(idx, k, "kendi yonlendirici siparisimiz var")
            if stage in URETIMDE and not b.get("issues"):
                return "uretimde", b, _neden(idx, k, "kanal siparisi uretimde")
            return "taslak", b, _neden(idx, k, "kanal kaydi taslak/sorunlu")
    return "", {}, ""


def meta_oku(st):
    try:
        return json.loads((st.get(META_ID) or {}).get("note") or "{}")
    except ValueError:
        return {}


def meta_yaz(st, path, m):
    upd(st, path, META_ID, stage="meta", note=json.dumps(m, ensure_ascii=False))


def _utc_ts(metin, bicim="%Y-%m-%d %H:%M:%S"):
    try:
        return calendar.timegm(time.strptime(str(metin)[:19], bicim))
    except (ValueError, TypeError):
        return 0


def otomasyonlar(a, prod, st, idx, report, errors, hata_var):
    """1) 24 saat hatasizsa --max-orders sinirini kaldirir. 2) kanal siparisi sevk edilince
    TEK SEFER 'kanali kopar' hatirlatmasi (DIKKAT + kosu basarisiz). Kanal kopuksa kanali aramaz."""
    m = meta_oku(st)
    simdi = time.time()
    m.setdefault("ilk_canli_utc", now())
    if hata_var:
        m["hata_sayaci"] = int(m.get("hata_sayaci") or 0) + 1
        m["son_hata_utc"] = now()

    # --- 2) kanal siparisi sevk edildi mi (tek seferlik hatirlatma)
    if not m.get("kanal_kopuk") and not m.get("kanal_hatirlatma_utc"):
        for rid, row in list(st.items()):
            oid = row.get("kanal_oid")
            if not oid:
                continue
            _stc, d = prod.get_order(oid)
            o = d.get("order") or {}
            asama = str(((o.get("status") or {}).get("stage") or "")).lower()
            sevk = any((sp.get("tracking") or {}).get("number") for sp in (o.get("shipments") or [])) \
                or asama in ("complete", "shipped")
            if not sevk:
                continue
            mesaj = (f"Kanal siparisi {oid} (Etsy {rid}) sevk edildi. TEK ADIM: "
                     "Prodigi paneli -> Sales channels -> Etsy -> baglantiyi kaldir (Disconnect).")
            m["kanal_hatirlatma_utc"] = now()
            upd(st, a.state, rid, warn="KANAL_KOPAR", note=mesaj)
            DIKKAT_EK.append(f"- KANAL: {mesaj}")
            report.append(f"- {rid}: HATIRLATMA - {mesaj}")
            errors.append(f"{rid}: KANAL_KOPAR hatirlatmasi (kosu bilincli basarisiz)")
            break

    # --- kanal sessizligi: hatirlatmadan sonra 7 gun yeni kanal siparisi yoksa bayrak
    if m.get("kanal_hatirlatma_utc") and not m.get("kanal_kopuk"):
        zamanlar = [b.get("created") or "" for b in idx["kayit"].values() if b.get("kanal")]
        en_yeni = max(zamanlar) if zamanlar else ""
        t = _utc_ts(en_yeni, "%Y-%m-%dT%H:%M:%S")
        if not en_yeni or (t and (simdi - t) / 86400 >= KANAL_SESSIZ_GUN):
            m["kanal_kopuk"] = True
            m["kanal_kopuk_utc"] = now()
            report.append(f"- KANAL KOPUK: {KANAL_SESSIZ_GUN} gundur yeni kanal siparisi yok "
                          f"(son {en_yeni or 'yok'}); kanal artik aranmaz")

    # --- 1) sinir kaldirma
    if not m.get("sinir_kalkti_utc"):
        gecen = (simdi - _utc_ts(m.get("ilk_canli_utc"))) / 3600
        if gecen >= SINIR_SAAT:
            if int(m.get("hata_sayaci") or 0) == 0:
                m["sinir_kalkti_utc"] = now()
                report.append(f"- SINIR KALKTI: ilk canli kosudan bu yana {gecen:.0f} saat hatasiz; "
                              f"bundan sonra kosu basina en fazla {SINIRSIZ} siparis")
            else:
                mesaj = (f"SINIR KALKMADI: {gecen:.0f} saatte {m.get('hata_sayaci')} hata/DIKKAT "
                         f"(son {m.get('son_hata_utc')}); --max-orders 1 suruyor")
                report.append(f"- {mesaj}")
                DIKKAT_EK.append(f"- SINIR: {mesaj}")
    meta_yaz(st, a.state, m)
    return m


def zaten_siparis(idx, rid, items):
    """Bu receipt icin Prodigi'de siparis var mi? -> '' ya da neden."""
    rid = str(rid)
    if rid in idx["ref"]:
        return _neden(idx, rid, "Prodigi siparisi var")
    for i in items:
        tx = str(i.get("transaction_id") or "")
        if tx and tx in idx["kalem_ref"]:
            return _neden(idx, tx, "Prodigi kanal siparisi var")
        for ek in (f"etsy-{rid}", f"etsy-{rid}-{i.get('size')}"):
            if ek in idx["ref"]:
                return _neden(idx, ek, "Prodigi siparisi var")
    return ""


# ------------------------------------------------------------------ Etsy
def etsy_receipts(api, shop, since_days=0, max_pages=10, quota_min=0):
    """Odenmis/gonderilmemis receipt'ler. since_days>0 ise yalniz son N gun; en fazla max_pages cagri;
    kota quota_min altina inerse okuma durur (eldekiler islenir)."""
    out, offset = [], 0
    params = {"was_paid": "true", "was_shipped": "false", "limit": 100}
    if since_days:
        params["min_created"] = int(time.time()) - since_days * 86400
    for _ in range(max_pages):
        r = api.get(f"/shops/{shop}/receipts", params={**params, "offset": offset}) or {}
        res = r.get("results") or []
        out += res
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if len(res) < 100 or (rem is not None and quota_min and rem < quota_min):
            break
        offset += 100
    return out


def parse_items(receipt, only_size=""):
    """(gonderilecek kalemler, POD disi SKU'lar, atlanan POD kalemleri).
    only_size virgulle birden cok boy alir (or. '5x7,A1'): YALNIZ bu boylarin kalemleri
    gonderilir, ayni sepetteki diger boylar atlanir (onlari Prodigi entegrasyonu ceker).
    Secilen boylar TEK Prodigi siparisinde birlesir (kargo tek sefer)."""
    boylar = {b.strip() for b in (only_size or "").split(",") if b.strip()}
    items, other, atlanan = [], [], []
    for t in receipt.get("transactions") or []:
        sku = (t.get("sku") or "").strip()
        parsed = parse_sku(sku)
        if not parsed:
            other.append(sku or f"tx{t.get('transaction_id')}"); continue
        pair, ed, size = parsed
        if boylar and size not in boylar:
            atlanan.append(f"{sku}x{int(t.get('quantity') or 1)}"); continue
        pr = t.get("price") or {}
        price = float(pr.get("amount") or 0) / float(pr.get("divisor") or 100)
        items.append(dict(transaction_id=t.get("transaction_id"), sku=sku, pair=pair, ed=ed, size=size,
                          prodigi_sku=f"GLOBAL-HPR-{size}", qty=int(t.get("quantity") or 1), price=price,
                          asset_remote=f"{PRINT_REMOTE}/{pair}/{ed}/{size}.jpg"))
    return items, other, atlanan


def order_body(receipt, items, urls, only_size="", shipping_method="Budget"):
    rid = receipt["receipt_id"]
    # Anahtar SIPARISTEKI boylardan turetilir (or. etsy-123-5x7, etsy-123-5x7+A1): tam sepet
    # siparisiyle de, tek boyluk bir siparisle de carpismaz. Kalemler TEK siparistedir.
    ek = "+".join(sorted({i["size"] for i in items})) if only_size else ""
    ref = f"etsy-{rid}" + (f"-{ek}" if ek else "")
    # Kargo yontemi TEK KAYNAK: teklifte secilen (kargo_ayrinti["secilen"]["yontem"]) buraya gelir;
    # maliyet hesabi ile siparis govdesi ayni yontemi kullanir (23 Eyl bulgusu 1).
    return {"merchantReference": ref, "shippingMethod": shipping_method or "Budget", "idempotencyKey": ref,
            "recipient": {"name": receipt.get("name") or "", "email": receipt.get("buyer_email") or None,
                          "address": {"line1": receipt.get("first_line") or "", "line2": receipt.get("second_line") or None,
                                      "postalOrZipCode": receipt.get("zip") or "", "countryCode": receipt.get("country_iso") or "",
                                      "townOrCity": receipt.get("city") or "", "stateOrCounty": receipt.get("state") or None}},
            "items": [{"merchantReference": f"etsy-{rid}-{i['transaction_id']}", "sku": i["prodigi_sku"], "copies": i["qty"],
                       "sizing": "fillPrintArea", "assets": [{"printArea": "default", "url": urls[i["sku"]]}]} for i in items]}


# ------------------------------------------------------------------ onayli mod: paket + gonderim
def package_of(receipt, items, country, etsy_total, cost, margin, warn, env, only_size="", shipping_method="Budget"):
    """Prodigi'ye gonderilmeye HAZIR paket (asset url'leri gonderim aninda doldurulur)."""
    rid = str(receipt["receipt_id"])
    return {"receipt_id": rid, "env": env, "created_utc": now(), "country": country, "only_size": only_size,
            "etsy_total": etsy_total, "prodigi_cost": cost, "margin": margin, "warn": warn,
            "recipient_name": receipt.get("name") or "",
            "items": [{k: i[k] for k in ("transaction_id", "sku", "prodigi_sku", "pair", "ed", "size", "qty", "price", "asset_remote")}
                      for i in items],
            "order": order_body(receipt, items, {i["sku"]: "" for i in items}, only_size, shipping_method)}


def submit_package(a, prod, st, rid, report):
    """Tek paketi canli Prodigi API'ye gonderir. Ikinci gonderim ENGELLI. -> (gonderildi_mi, hata)"""
    rid = str(rid)
    pkg_path = Path(a.packages or a.out) / f"{rid}.json"
    res_paths = [Path(d) / f"{rid}.result.json" for d in {a.packages or a.out, a.out}]
    row = st.get(rid) or {}
    gonderilen = {x for x in (row.get("sent_tx") or "").split(";") if x}
    if not pkg_path.exists() and gonderilen:
        report.append(f"- {rid}: IDEMPOTENS - kalemler zaten gonderildi ({len(gonderilen)} tx)")
        return False, ""
    if pkg_path.exists() and gonderilen:
        istenen = {str(i["transaction_id"]) for i in json.loads(pkg_path.read_text(encoding="utf-8")).get("items") or []}
        if istenen & gonderilen:
            report.append(f"- {rid}: IDEMPOTENS - ayni kalem(ler) zaten gonderildi: "
                          f"{sorted(istenen & gonderilen)}; YENIDEN GONDERILMEDI")
            return False, ""
    if row.get("stage") in ("ordered", "shipped", "tracked") or any(r.exists() for r in res_paths):
        report.append(f"- {rid}: IDEMPOTENS - zaten gonderildi (stage {row.get('stage') or '-'}, "
                      f"prodigi {row.get('prodigi_order_id') or '-'}); YENIDEN GONDERILMEDI")
        return False, ""
    if not pkg_path.exists():
        return False, f"{rid}: paket dosyasi yok: {pkg_path}"
    if row and row.get("stage") not in ("bekliyor", "dryrun"):
        return False, f"{rid}: STATE stage '{row.get('stage')}' - yalniz 'bekliyor' gonderilir"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    body = pkg["order"]
    if len(body.get("items") or []) != len(pkg.get("items") or []):
        return False, f"{rid}: paket bozuk (kalem sayisi uyusmuyor)"
    links, perms = DriveLinks(), []
    try:
        for n, it in enumerate(pkg["items"]):
            fid, pid, url = links.open(it["asset_remote"])
            perms.append([fid, pid])
            body["items"][n]["assets"][0]["url"] = url
        stc, d = prod.create_order(body)
        outcome = (d.get("outcome") or "")
        oid = (d.get("order") or {}).get("id")
        if stc != 200 or not oid or outcome.lower() not in ("created", "createdwithissues", "onhold"):
            raise RuntimeError(f"order HTTP {stc} outcome={outcome}: {json.dumps(d)[:300]}")
    except Exception as e:                       # noqa: BLE001 - hata da STATE'e yazilir
        upd(st, a.state, rid, stage="error", asset_perms=perms, note=f"submit: {str(e)[:280]}")
        return False, f"{rid}: {type(e).__name__} {str(e)[:300]}"
    res = {"receipt_id": rid, "env": a.env, "submitted_utc": now(), "http": stc, "outcome": outcome,
           "prodigi_order_id": oid, "order": d.get("order") or {}}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / f"{rid}.result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    upd(st, a.state, rid, stage="ordered", country=pkg.get("country", ""),
        sent_tx=";".join(str(i["transaction_id"]) for i in pkg["items"]),
        items=", ".join(f"{i['sku']}x{i['qty']}" for i in pkg["items"]),
        etsy_total=pkg.get("etsy_total", ""), prodigi_cost=pkg.get("prodigi_cost", ""), margin=pkg.get("margin", ""),
        warn=pkg.get("warn", ""), prodigi_order_id=oid, prodigi_status=outcome, asset_perms=perms,
        note=f"onayli gonderim ({a.env})")
    report.append(f"- {rid}: GONDERILDI {oid} ({outcome}) | Etsy {pkg.get('etsy_total')} USD, "
                  f"Prodigi {pkg.get('prodigi_cost')} USD, marj {pkg.get('margin')}")
    return True, ""


# ------------------------------------------------------------------ durum
def read_state(p):
    st = {}
    if Path(p).exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st[r["receipt_id"]] = r
    return st


def write_state(p, st):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
        for k in sorted(st, key=lambda x: str(x)):
            w.writerow({c: st[k].get(c, "") for c in COLS})


def takip_url_durumu(url, zaman_asimi=20):
    """Takip linki calisiyor mu: 2xx/3xx -> 'ok'. Ag yoksa/hata varsa nedeni dondurur."""
    if not url:
        return "url yok"
    try:
        r = requests.get(url, timeout=zaman_asimi, allow_redirects=True,
                         headers={"User-Agent": "astrolove-ops/1.0"})
        return "ok" if r.status_code < 400 else f"HTTP {r.status_code}"
    except Exception as e:
        return f"{type(e).__name__}"


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def upd(st, path, rid, **kw):
    row = st.setdefault(str(rid), {"receipt_id": str(rid)})
    row.update({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in kw.items()})
    row["ts_utc"] = now()
    write_state(path, st)
    return row


# ------------------------------------------------------------------ ana
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", choices=["sandbox", "live"], default="sandbox")
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-receipt", default="", help="Etsy receipt JSON (sandbox uctan uca test; Etsy okunmaz/yazilmaz)")
    ap.add_argument("--etsy-writes", action="store_true", help="tracking'i Etsy'ye yaz (yalniz live + onay)")
    ap.add_argument("--margin-min", type=float, default=0.20)
    ap.add_argument("--max-orders", type=int, default=5, help="kosu basina en fazla yeni siparis")
    ap.add_argument("--asset-wait", type=int, default=6, help="asset indirme icin bekleme turu (x20 sn)")
    ap.add_argument("--approve-mode", choices=["on", "off"], default="on",
                    help="on (varsayilan): yalniz paket hazirla, Prodigi'ye siparis GONDERME")
    ap.add_argument("--submit", default="", help="yalniz bu receipt'in hazir paketini Prodigi'ye gonder (--apply ile)")
    ap.add_argument("--packages", default="", help="hazir paket dizini (varsayilan --out)")
    ap.add_argument("--since-days", type=int, default=0, help="yalniz son N gunun receipt'leri (0 = hepsi)")
    ap.add_argument("--quota-min", type=int, default=400, help="Etsy kota tabani; altinda receipt okumasi durur")
    ap.add_argument("--max-pages", type=int, default=10, help="receipt okumasinda en fazla N cagri")
    ap.add_argument("--min-yas-dk", type=int, default=60,
                    help="receipt bu kadar dakika eskimeden islenmez (kanal ice aktarmasi bitsin)")
    ap.add_argument("--kanal-kopuk", action="store_true",
                    help="Serdar onayi: Etsy kanali Prodigi'den koparildi; kanal artik aranmaz")
    ap.add_argument("--devral", default="", help="disarida acilan siparisleri STATE'e al: receipt=order_id[,...]")
    ap.add_argument("--takip-baslangic", default="",
                    help="Etsy takip yazimi icin yeni siparis siniri (UTC 'YYYY-MM-DD HH:MM:SS'); "
                         "takip.YENI_SIPARIS_BASLANGIC_UTC'den yalniz ILERI tasinabilir")
    ap.add_argument("--only-size", default="", help="yalniz bu boyun kalemlerini isle (or. 5x7); "
                                                   "ayni sepetteki diger boylar atlanir")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not (a.dry_run or a.apply):
        a.dry_run = True                       # onayli modda varsayilan: Prodigi'ye yazma yok
    try:
        takip_sinir = takip.sinir_ts(a.takip_baslangic)   # hatali bicim: kosu basinda dur, yazma yok
    except ValueError:
        sys.exit(f"HATA: --takip-baslangic bicimi 'YYYY-MM-DD HH:MM:SS' olmali: {a.takip_baslangic!r}")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = read_state(a.state)
    approve = (a.approve_mode == "on") and not a.submit
    mod = "ONAYLI MOD (paket hazirlama)" if approve else ("GONDERIM" if a.submit else ("DRY-RUN" if a.dry_run else "APPLY"))
    report = [f"# POD siparis yonlendirici — {a.env.upper()} — {mod} — {now()} UTC", ""]
    errors = []

    meta0 = meta_oku(st)
    kanal_kopuk = bool(meta0.get("kanal_kopuk")) or a.kanal_kopuk
    if meta0.get("sinir_kalkti_utc"):
        a.max_orders = max(a.max_orders, SINIRSIZ)
        report.append(f"- SINIR KALKMIS ({meta0['sinir_kalkti_utc']}): kosu basina en fazla {a.max_orders}")
    if kanal_kopuk:
        report.append("- KANAL KOPUK: kanal siparisi aranmaz, 60 dk bekleme uygulanmaz")

    prod = Prodigi(load_prodigi_key(a.env), a.env)
    api = shop = None
    # --- tum POD boylari canli katalogla dogrulanir (buyuk/kucuk harf dahil)
    harita, eksik = sku_haritasi(prod, TUM_BOYLAR)
    (out / "PRODIGI_SKU_HARITA.json").write_text(json.dumps(
        {"harita": harita, "eksik": eksik, "utc": now()}, indent=1, ensure_ascii=False), encoding="utf-8")
    report.append(f"- Prodigi katalog: {len(harita)}/{len(TUM_BOYLAR)} boy dogrulandi"
                  + (f" | EKSIK: {eksik}" if eksik else ""))
    if eksik:
        errors.append(f"katalogda olmayan boy(lar): {eksik}")
    # --- devralma: disarida acilan siparisi STATE'e al (takip Etsy'ye yazilabilsin)
    for es in [x for x in (a.devral or "").split(",") if x.strip()]:
        rid_d, _, oid_d = es.partition("=")
        rid_d, oid_d = rid_d.strip(), oid_d.strip()
        if rid_d and oid_d and (st.get(rid_d) or {}).get("prodigi_order_id") != oid_d:
            upd(st, a.state, rid_d, stage="ordered", prodigi_order_id=oid_d, asset_perms=[],
                note="devralindi (disarida acilan siparis; takip bu kosudan yazilir)")
            report.append(f"- {rid_d}: DEVRALINDI -> {oid_d}")
    if approve:
        a.etsy_writes = False                  # onayli modda kargo bildirimi yalniz loglanir
        report.append("- ONAYLI MOD: paketler hazirlanir, Prodigi'ye siparis GONDERILMEZ (--submit ile gonderilir)")
    if a.submit:
        if not a.apply:
            sys.exit("HATA: --submit icin --apply gerekir (canli gonderim).")
        report.append(f"- GONDERIM: receipt {a.submit} (yalniz bu paket)")
        ok_sub, err_sub = submit_package(a, prod, st, a.submit, report)
        if err_sub:
            errors.append(err_sub)
        receipts = []
    elif a.test_receipt:
        receipts = [json.loads(Path(a.test_receipt).read_text(encoding="utf-8"))]
        report.append(f"- test receipt: {a.test_receipt} (Etsy okunmadi)")
    else:
        keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
        shop = os.environ.get("ETSY_SHOP_ID", "")
        mask(keystring); mask(shared)
        store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
        if store.needs_refresh():
            store.refresh()
        api = Etsy(store)
        q0 = api.remaining
        receipts = etsy_receipts(api, shop, a.since_days, a.max_pages, a.quota_min)
        report.append(f"- Etsy odenmis/gonderilmemis receipt: {len(receipts)}"
                      + (f" (son {a.since_days} gun)" if a.since_days else "") + f" | kota {q0} -> {api.remaining}")
    idx = prodigi_indeks(prod) if not a.test_receipt else {"ref": set(), "kalem_ref": set(), "kayit": {}}
    if not a.test_receipt:
        report.append(f"- Prodigi'de mevcut referans: {len(idx['ref'])} siparis, {len(idx['kalem_ref'])} kalem")
    pod = [(r, *parse_items(r, a.only_size)) for r in receipts]
    pod = [(r, items, other, atlanan) for r, items, other, atlanan in pod if items]
    report.append(f"- POD urunlu receipt: {len(pod)}"
                  + (f" (yalniz {a.only_size} kalemleri)" if a.only_size else ""))
    links = None
    new_orders = 0

    # ---- 1) yeni receipt'ler
    t0 = time.time()
    for n, (r, items, other, atlanan) in enumerate(pod, 1):
        rid = str(r.get("receipt_id"))
        row = st.get(rid) or {}
        if row.get("stage") in ("bekliyor", "ordered", "shipped", "tracked", "manual", "error", "atlandi"):
            report.append(f"- {rid}: ATLA (STATE {row.get('stage')}"
                          + (f", prodigi {row.get('prodigi_order_id')}" if row.get("prodigi_order_id") else "") + ")")
            continue
        el = time.time() - t0
        log(f"[{n}/{len(pod)}] receipt {rid} | gecen {el:.0f}s kalan~{el / n * (len(pod) - n):.0f}s %{100 * n // len(pod)}")
        for i in items:                       # katalogdaki tam SKU yazimi
            i["prodigi_sku"] = harita.get(i["size"], i["prodigi_sku"])
        if r.get("is_shipped"):
            report.append(f"- {rid}: ATLA (Etsy'de gonderilmis)")
            continue
        desc0 = ", ".join(f"{i['sku']}x{i['qty']}" for i in items)
        yas_dk = (time.time() - float(r.get("created_timestamp") or r.get("create_timestamp") or 0)) / 60 \
            if (r.get("created_timestamp") or r.get("create_timestamp")) else 1e9
        if yas_dk < (0 if kanal_kopuk else a.min_yas_dk):
            report.append(f"- {rid}: BEKLE ({yas_dk:.0f} dk < {a.min_yas_dk} dk; kanal ice aktarmasi bitsin)")
            continue
        tur, bilgi, neden = kanal_durumu(idx, rid, items)
        if tur in ("bizim", "uretimde"):
            if a.dry_run and bilgi.get("id"):       # salt okuma: iptal alaninin varligi kanitlanir
                olur_p, ham_p = prod.iptal_edilebilir(bilgi["id"])
                neden += f" | iptal API alani: cancel.isAvailable={ham_p}"
            upd(st, a.state, rid, stage="atlandi", items=desc0, note=neden,
                **({"kanal_oid": bilgi.get("id")} if tur == "uretimde" and bilgi.get("kanal") else {}))
            report.append(f"- {rid}: ATLA ({neden})")
            continue
        if tur == "taslak":
            oid_t = bilgi.get("id")
            olur, ham = prod.iptal_edilebilir(oid_t)
            if not olur:
                mesaj = f"{neden}; Prodigi iptal API'si bu siparis icin kapali (cancel.isAvailable={ham}) - SERDAR IPTAL ETMELI"
                upd(st, a.state, rid, stage="manual", items=desc0, warn="KANAL_TASLAK", note=mesaj)
                report.append(f"- {rid}: DIKKAT ({mesaj}); siparis ACILMADI")
                continue
            if a.dry_run:
                report.append(f"- {rid}: (kuru) kanal taslagi {oid_t} IPTAL EDILEBILIR -> iptal + kendi siparisimiz")
                continue
            ok_i, aciklama = prod.iptal(oid_t)
            if not ok_i:
                mesaj = f"{neden}; iptal BASARISIZ: {aciklama}"
                upd(st, a.state, rid, stage="manual", items=desc0, warn="KANAL_TASLAK_IPTAL_HATA", note=mesaj)
                report.append(f"- {rid}: DUR ({mesaj}); siparis ACILMADI")
                errors.append(f"{rid}: {mesaj}")
                continue
            report.append(f"- {rid}: kanal taslagi {oid_t} IPTAL EDILDI ({aciklama}); kendi siparisimiz aciliyor")
            upd(st, a.state, rid, kanal_iptal=oid_t)
        country = (r.get("country_iso") or "").upper()
        etsy_total = round(sum(i["price"] * i["qty"] for i in items), 2)
        desc = ", ".join(f"{i['sku']}x{i['qty']}" for i in items)
        warn = []
        if other:
            warn.append(f"POD disi urun: {other}")
        if atlanan:
            warn.append(f"Prodigi entegrasyonunda kalan boylar: {atlanan}")
        if country not in ALLOWED:
            upd(st, a.state, rid, stage="manual", country=country, items=desc, etsy_total=etsy_total, warn="; ".join(warn),
                note=f"ulke {country} otomatik listede degil (US/CA/AU/GB); elle islenecek")
            report.append(f"- {rid}: MANUAL ({country}) {desc}")
            continue
        cost, err, kargo_ayrinti = prod.quote(items, country)
        if cost is None:
            errors.append(f"{rid}: {err}")
            upd(st, a.state, rid, stage="error", country=country, items=desc, etsy_total=etsy_total, note=err)
            break
        margin = round((etsy_total - cost) / etsy_total, 3) if etsy_total else 0
        sec = kargo_ayrinti.get("secilen") or {}
        kargo_metin = (f"kargo {sec.get('yontem')} {sec.get('kargo')} + ekler {EKLER_USD:.2f} "
                       f"(secenekler: " + ", ".join(f"{x['yontem']} {x['toplam']:.2f}"
                                                    for x in kargo_ayrinti.get("secenekler", [])) + ")"
                       ) if sec else ""
        if margin < a.margin_min:
            warn.append(f"MARJ_DUSUK {margin:.0%} (< {a.margin_min:.0%}): Etsy {etsy_total} / Prodigi {cost}")
        if approve:
            secilen_yontem = (kargo_ayrinti.get("secilen") or {}).get("yontem") or "Budget"
            pkg = package_of(r, items, country, etsy_total, cost, margin, "; ".join(warn), a.env, a.only_size,
                             secilen_yontem)
            pkg["kargo"] = kargo_ayrinti
            (out / f"{rid}.json").write_text(json.dumps(pkg, indent=1, ensure_ascii=False), encoding="utf-8")
            upd(st, a.state, rid, stage="bekliyor", country=country, items=desc, etsy_total=etsy_total, prodigi_cost=cost,
                margin=margin, warn="; ".join(warn), note=f"paket hazir ({rid}.json); onay bekliyor (--submit {rid})")
            report.append(f"- {rid}: BEKLIYOR (paket {rid}.json) {country} {desc} | Etsy {etsy_total} USD, "
                          f"Prodigi {cost} USD, marj {margin:.0%} | {kargo_metin}"
                          + (f" | {'; '.join(warn)}" if warn else ""))
            continue
        if a.dry_run:
            upd(st, a.state, rid, stage="dryrun", country=country, items=desc, etsy_total=etsy_total, prodigi_cost=cost,
                margin=margin, warn="; ".join(warn), note="dry-run: siparis verilmedi")
            report.append(f"- {rid}: DRY-RUN {country} {desc} | Etsy {etsy_total} USD, Prodigi {cost} USD, "
                          f"marj {margin:.0%} | {kargo_metin}" + (f" | {'; '.join(warn)}" if warn else ""))
            continue
        if new_orders >= a.max_orders:
            report.append(f"- {rid}: kosu siniri ({a.max_orders}); sonraki kosuda")
            continue
        try:
            links = links or DriveLinks()
            perms, urls = [], {}
            for i in items:
                fid, pid, url = links.open(i["asset_remote"])
                perms.append([fid, pid]); urls[i["sku"]] = url
            secilen_yontem = (kargo_ayrinti.get("secilen") or {}).get("yontem") or "Budget"
            stc, d = prod.create_order(order_body(r, items, urls, a.only_size, secilen_yontem))
            outcome = (d.get("outcome") or "")
            oid = (d.get("order") or {}).get("id")
            if stc != 200 or not oid or outcome.lower() not in ("created", "createdwithissues", "onhold"):
                raise RuntimeError(f"order HTTP {stc} outcome={outcome}: {json.dumps(d)[:300]}")
            new_orders += 1
            upd(st, a.state, rid, stage="ordered", country=country, items=desc, etsy_total=etsy_total, prodigi_cost=cost,
                margin=margin, warn="; ".join(warn), prodigi_order_id=oid, prodigi_status=outcome, asset_perms=perms,
                note=f"siparis verildi ({a.env})")
            report.append(f"- {rid}: ORDERED {oid} ({outcome}) {country} {desc} | Etsy {etsy_total}, Prodigi {cost}, marj {margin:.0%}" + (f" | {'; '.join(warn)}" if warn else ""))
        except Exception as e:
            errors.append(f"{rid}: {type(e).__name__} {str(e)[:300]}")
            upd(st, a.state, rid, stage="error", country=country, items=desc, etsy_total=etsy_total, prodigi_cost=cost,
                margin=margin, warn="; ".join(warn), asset_perms=locals().get("perms", []), note=str(e)[:300])
            break

    # ---- 1b) ALARM: kendi siparisimizden sonra kanalda yeni submit edilmis siparis belirdi mi (3 kosu)
    if not a.test_receipt:
        for rid, row in list(st.items()):
            if row.get("stage") not in ("ordered", "shipped", "tracked"):
                continue
            try:
                sayac = int(row.get("alarm_kosu") or 0)
            except ValueError:
                sayac = 0
            if sayac >= 3:
                continue
            bizim = str(row.get("prodigi_order_id") or "")
            adaylar = [str(rid)] + [x for x in (row.get("sent_tx") or "").split(";") if x]
            carpisan = []
            for k in adaylar:
                b = idx["kayit"].get(k) or {}
                if b.get("id") and b["id"] != bizim and str(b.get("stage", "")).lower() in URETIMDE:
                    carpisan.append(f"{k} -> {b['id']} ({b['stage']})")
            upd(st, a.state, rid, alarm_kosu=sayac + 1)
            if carpisan:
                mesaj = ("ALARM: ayni receipt icin kanalda YENI siparis var: " + "; ".join(carpisan)
                         + f" | bizim {bizim}. Otomatik iptal YAPILMADI - Serdar bakmali.")
                upd(st, a.state, rid, warn="CIFT_SIPARIS_ALARM", note=mesaj)
                report.append(f"- {rid}: {mesaj}")
                errors.append(f"{rid}: CIFT_SIPARIS_ALARM")

    # ---- 2) ordered: asset izinleri + kargo (onayli modda da: acik izinler kapanir, kargo yakalanir)
    if a.apply or approve or a.submit:
        for rid, row in list(st.items()):
            if row.get("stage") != "ordered" or not row.get("prodigi_order_id"):
                continue
            stc, d = prod.get_order(row["prodigi_order_id"])
            o = d.get("order") or {}
            if stc != 200 or not o:
                errors.append(f"{rid}: get_order HTTP {stc}"); continue
            status = o.get("status") or {}
            details = status.get("details") or {}
            perms = json.loads(row.get("asset_perms") or "[]")
            if perms and str(details.get("downloadAssets", "")).lower() == "complete":
                links = links or DriveLinks()
                for fid, pid in perms:
                    links.close(fid, pid)
                perms = []
                report.append(f"- {rid}: assetler indirildi, gecici izinler kaldirildi")
            elif perms:
                for _ in range(a.asset_wait):           # yeni siparis: kisa bekleme, indirilirse hemen kapat
                    time.sleep(20)
                    stc, d = prod.get_order(row["prodigi_order_id"]); o = d.get("order") or {}
                    details = (o.get("status") or {}).get("details") or {}
                    if str(details.get("downloadAssets", "")).lower() == "complete":
                        links = links or DriveLinks()
                        for fid, pid in perms:
                            links.close(fid, pid)
                        perms = []; report.append(f"- {rid}: assetler indirildi, gecici izinler kaldirildi"); break
            ship = next((s for s in o.get("shipments") or [] if (s.get("tracking") or {}).get("number")), None)
            kw = dict(prodigi_status=f"{status.get('stage')}/{details.get('downloadAssets')}/{details.get('inProduction', details.get('printReadyAssetsPrepared'))}", asset_perms=perms)
            if ship:
                bilgi = takip.takip_bilgi(ship)
                plan = takip.etsy_plani(bilgi)
                kw.update(stage="shipped", tracking=bilgi["numara"], carrier=bilgi["tasiyici_ad"],
                          carrier_service=bilgi["tasiyici_hizmet"], tracking_url=plan["takip_url"],
                          tracking_son_ayak=bilgi["son_ayak_numara"], carrier_etsy=plan["carrier_name"])
                report.append(f"- {rid}: SHIPPED {bilgi['tasiyici_ad']} / {bilgi['tasiyici_hizmet']} "
                              f"{bilgi['numara']} -> Etsy {plan['carrier_name']} {plan['tracking_code']}"
                              + (f" | {plan['uyari']}" if plan["uyari"] else ""))
            upd(st, a.state, rid, **kw)

    # ---- 2b) TAKIP KORUMASI raporu (salt okuma): hangi siparise neden Etsy takibi yazilmaz
    report.append(f"- TAKIP KORUMASI: sinir {takip.utc_metin(takip_sinir)} UTC; Etsy'ye yalniz STATE 'shipped' "
                  "+ yazma_karari 'yaz' olan receipt yazilir")
    bilinen = set()
    for rid, row in st.items():
        if rid == META_ID:
            continue
        bilinen.update(x for x in (rid, row.get("prodigi_order_id"), row.get("kanal_oid")) if x)
        if row.get("stage") != "shipped":
            report.append(f"- TAKIP KORUMASI {rid}: YAZMAZ (STATE '{row.get('stage')}', adim 3 disi)"
                          + (f"; kayitli takip {row.get('carrier') or '-'} {row.get('tracking')}" if row.get("tracking") else ""))
        else:
            report.append(f"- TAKIP KORUMASI {rid}: STATE 'shipped' -> karar adim 3'te receipt okunarak verilir")
    for ref, b in sorted((idx.get("kayit") or {}).items(), key=lambda kv: str(kv[1].get("id"))):
        if b.get("id") in bilinen or ref in bilinen:
            continue
        bilinen.add(b.get("id"))
        report.append(f"- TAKIP KORUMASI {b.get('id')} (ref {b.get('mr') or '-'}): YAZMAZ (STATE'te yok; "
                      "router bu siparise takip yazmaz)")

    # ---- 3) shipped -> Etsy tracking
    for rid, row in list(st.items()):
        if row.get("stage") != "shipped":
            continue
        if approve or a.dry_run or not a.etsy_writes or api is None:
            nedeni = "onayli mod (yalniz log)" if approve else ("dry-run" if a.dry_run else "etsy-writes kapali / test")
            report.append(f"- {rid}: Etsy tracking YAZILMADI ({nedeni}); tracking {row.get('tracking')} {row.get('carrier') or ''}")
            continue
        try:
            bilgi = {"numara": row.get("tracking") or "", "url": row.get("tracking_url") or "",
                     "tasiyici_ad": row.get("carrier") or "", "tasiyici_hizmet": row.get("carrier_service") or "",
                     "son_ayak_numara": row.get("tracking_son_ayak") or ""}
            plan = takip.etsy_plani(bilgi)
            # Tekrar POST yok + GECMIS SIPARISE HIC yazma yok (24 Eyl, Serdar): Etsy her POST'ta
            # aliciya e-posta atar. Once receipt okunur; yalniz karar "yaz" ise tek POST yapilir.
            onceki = api.get(f"/shops/{shop}/receipts/{rid}") or {}
            karar, neden = takip.yazma_karari(onceki, rid, plan, takip_sinir)
            if karar == "gecmis":
                upd(st, a.state, rid, stage="atlandi", note=f"Etsy takip YAZILMADI: {neden}"[:300])
                report.append(f"- {rid}: Etsy tracking YAZILMADI (kalici) - {neden}")
                continue
            if karar == "hata":
                report.append(f"- {rid}: Etsy tracking YAZILMADI - {neden}")
                errors.append(f"{rid}: takip yazilmadi: {neden}")
                continue
            if karar == "dogrula":
                report.append(f"- {rid}: {neden}; POST YAPILMADI")
            else:
                api.post(f"/shops/{shop}/receipts/{rid}/tracking",
                         {"tracking_code": plan["tracking_code"], "carrier_name": plan["carrier_name"],
                          "send_bcc": "true"})
            back = api.get(f"/shops/{shop}/receipts/{rid}") or {}
            url_durumu = takip_url_durumu(plan.get("takip_url"))
            ok, eksik = takip.dogrula(back, rid, plan, url_durumu)   # is_shipped TEK BASINA PASS DEGIL
            upd(st, a.state, rid, stage="tracked" if ok else "shipped", carrier_etsy=plan["carrier_name"],
                tracking_url=plan["takip_url"],
                note=("Etsy tracking dogrulandi" if ok else "Etsy tracking DOGRULANAMADI: " + "; ".join(eksik))[:300])
            report.append(f"- {rid}: {'TRACKED PASS' if ok else 'FAIL'} -> Etsy {plan['carrier_name']} "
                          f"{plan['tracking_code']} | link {url_durumu} {plan.get('takip_url') or 'YOK'}"
                          + ("" if ok else " | eksik: " + "; ".join(eksik))
                          + (f" | {plan['uyari']}" if plan.get("uyari") else ""))
            if not ok:
                errors.append(f"{rid}: takip dogrulanamadi: {'; '.join(eksik)}")
        except SystemExit as e:
            errors.append(f"{rid}: Etsy tracking {e}")
            upd(st, a.state, rid, stage="error", note=f"Etsy tracking: {e}")
            break

    if (a.apply or a.submit) and not a.test_receipt:
        hata_var = bool(errors) or any(
            (v.get("stage") in ("manual", "error") or v.get("warn")) for k, v in st.items() if k != META_ID)
        otomasyonlar(a, prod, st, idx, report, errors, hata_var)

    counts = {}
    for row in st.values():
        counts[row.get("stage", "")] = counts.get(row.get("stage", ""), 0) + 1
    report += ["", f"STATE: {counts}", ""] + ([f"HATA: {e}" for e in errors] or ["hata yok"])
    text = "\n".join(report)
    log(text)
    (out / "REPORT.md").write_text(text + "\n", encoding="utf-8")
    dikkat = [r for r in st.values() if r.get("stage") in ("manual", "error") or r.get("warn")]
    if dikkat or DIKKAT_EK:
        satir = ["# DIKKAT: elle islem gereken siparisler", f"(kosu {now()} UTC)", ""]
        satir += [f"- {r['receipt_id']}: {r.get('stage')} | {r.get('country', '')} {r.get('items', '')} "
                  f"| {r.get('warn') or ''} {r.get('note') or ''}".strip() for r in dikkat]
        satir += DIKKAT_EK
        (out / "DIKKAT.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if errors:
        sys.exit("DUR: hata var, STATE yazildi")


if __name__ == "__main__":
    main()
