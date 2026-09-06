#!/usr/bin/env python3
"""
PRODIGI SIPARIS YONLENDIRICI (6 Eyl 2026): Etsy POD siparisi -> Prodigi siparisi -> takip -> Etsy.

Akis (her kosu):
  1. Etsy getShopReceipts (was_paid, unshipped); SKU POD-<PAIR>-<ED>-<SIZE> olan islemler.
  2. Yeni receipt: ulke US/CA/AU/GB degilse MANUAL; Prodigi teklif (Budget) ile maliyet kontrolu,
     marj < --margin-min ise MARJ_DUSUK uyarisi (durdurmaz); apply'da baski dosyasina gecici Drive
     linki (anyone:reader) verilir, POST /orders (idempotencyKey = etsy-<receipt_id>) -> ordered.
  3. ordered: GET /orders/{id}; assetler indirildiyse gecici izin kaldirilir; kargo takip numarasi
     geldiyse shipped.
  4. shipped: Etsy createReceiptShipment (tracking, carrier) -> tracked. (--etsy-writes yoksa atlanir.)
  Idempotent: STATE (receipt_id) + Prodigi idempotencyKey. Prodigi/Etsy hatasi -> STATE yazilir, DUR (exit 1).

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE; PRODIGI_API_KEY (yerel) ya da
Drive TEMP/PRODIGI_TOKEN.json (live) / TEMP/PRODIGI_SANDBOX_TOKEN.json (sandbox) rclone ile.
Kullanim:
  order_router.py --env sandbox --state ST.csv --out OUT --dry-run
  order_router.py --env sandbox --state ST.csv --out OUT --apply --test-receipt test.json   # sandbox uctan uca
  order_router.py --env live    --state ST.csv --out OUT --apply --etsy-writes              # canli (onay)
"""
import argparse
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

PRODIGI = {"live": "https://api.prodigi.com/v4.0", "sandbox": "https://api.sandbox.prodigi.com/v4.0"}
KEY_REMOTE = {"live": "gdrive:ASTROLOVE/TEMP/PRODIGI_TOKEN.json", "sandbox": "gdrive:ASTROLOVE/TEMP/PRODIGI_SANDBOX_TOKEN.json"}
PRINT_REMOTE = "gdrive:ASTROLOVE/TEMP/POD_PRINT"
ALLOWED = {"US", "CA", "AU", "GB"}
SKU_RE = re.compile(r"^POD-([A-Z]+_[A-Z]+)-([A-Z_]+)-([0-9x]+|A[234])$")
STAGES = ["dryrun", "manual", "ordered", "shipped", "tracked", "error"]
COLS = ["receipt_id", "stage", "country", "items", "etsy_total", "prodigi_cost", "margin", "warn", "prodigi_order_id",
        "prodigi_status", "asset_perms", "tracking", "carrier", "ts_utc", "note"]
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
        st, d = self.call("POST", "/quotes", {"shippingMethod": "Budget", "destinationCountryCode": country, "currencyCode": "USD",
                                             "items": [{"sku": i["prodigi_sku"], "copies": i["qty"], "assets": [{"printArea": "default"}]} for i in items]})
        if st != 200 or not d.get("quotes"):
            return None, f"quote HTTP {st}: {json.dumps(d)[:200]}"
        q = next((x for x in d["quotes"] if (x.get("shipmentMethod") or "").lower() == "budget"), d["quotes"][0])
        cs = q.get("costSummary") or {}
        tot = float((cs.get("items") or {}).get("amount") or 0) + float((cs.get("shipping") or {}).get("amount") or 0)
        return round(tot, 2), ""

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


# ------------------------------------------------------------------ Etsy
def etsy_receipts(api, shop):
    out, offset = [], 0
    while True:
        r = api.get(f"/shops/{shop}/receipts", params={"was_paid": "true", "was_shipped": "false", "limit": 100, "offset": offset}) or {}
        res = r.get("results") or []
        out += res
        if len(res) < 100:
            return out
        offset += 100


def parse_items(receipt):
    items, other = [], []
    for t in receipt.get("transactions") or []:
        sku = (t.get("sku") or "").strip()
        m = SKU_RE.match(sku)
        if not m:
            other.append(sku or f"tx{t.get('transaction_id')}"); continue
        pair, ed, size = m.groups()
        pr = t.get("price") or {}
        price = float(pr.get("amount") or 0) / float(pr.get("divisor") or 100)
        items.append(dict(transaction_id=t.get("transaction_id"), sku=sku, pair=pair, ed=ed, size=size,
                          prodigi_sku=f"GLOBAL-HPR-{size}", qty=int(t.get("quantity") or 1), price=price,
                          asset_remote=f"{PRINT_REMOTE}/{pair}/{ed}/{size}.jpg"))
    return items, other


def order_body(receipt, items, urls):
    rid = receipt["receipt_id"]
    return {"merchantReference": f"etsy-{rid}", "shippingMethod": "Budget", "idempotencyKey": f"etsy-{rid}",
            "recipient": {"name": receipt.get("name") or "", "email": receipt.get("buyer_email") or None,
                          "address": {"line1": receipt.get("first_line") or "", "line2": receipt.get("second_line") or None,
                                      "postalOrZipCode": receipt.get("zip") or "", "countryCode": receipt.get("country_iso") or "",
                                      "townOrCity": receipt.get("city") or "", "stateOrCounty": receipt.get("state") or None}},
            "items": [{"merchantReference": f"etsy-{rid}-{i['transaction_id']}", "sku": i["prodigi_sku"], "copies": i["qty"],
                       "sizing": "fillPrintArea", "assets": [{"printArea": "default", "url": urls[i["sku"]]}]} for i in items]}


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
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = read_state(a.state)
    report = [f"# POD siparis yonlendirici — {a.env.upper()} — {'DRY-RUN' if a.dry_run else 'APPLY'} — {now()} UTC", ""]
    errors = []

    prod = Prodigi(load_prodigi_key(a.env), a.env)
    api = shop = None
    if a.test_receipt:
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
        receipts = etsy_receipts(api, shop)
        report.append(f"- Etsy odenmis/gonderilmemis receipt: {len(receipts)} | kota {api.remaining}")
    pod = [(r, *parse_items(r)) for r in receipts]
    pod = [(r, items, other) for r, items, other in pod if items]
    report.append(f"- POD urunlu receipt: {len(pod)}")
    links = None
    new_orders = 0

    # ---- 1) yeni receipt'ler
    for r, items, other in pod:
        rid = str(r.get("receipt_id"))
        row = st.get(rid) or {}
        if row.get("stage") in ("ordered", "shipped", "tracked", "manual", "error"):
            continue
        country = (r.get("country_iso") or "").upper()
        etsy_total = round(sum(i["price"] * i["qty"] for i in items), 2)
        desc = ", ".join(f"{i['sku']}x{i['qty']}" for i in items)
        warn = []
        if other:
            warn.append(f"POD disi urun: {other}")
        if country not in ALLOWED:
            upd(st, a.state, rid, stage="manual", country=country, items=desc, etsy_total=etsy_total, warn="; ".join(warn),
                note=f"ulke {country} otomatik listede degil (US/CA/AU/GB); elle islenecek")
            report.append(f"- {rid}: MANUAL ({country}) {desc}")
            continue
        cost, err = prod.quote(items, country)
        if cost is None:
            errors.append(f"{rid}: {err}")
            upd(st, a.state, rid, stage="error", country=country, items=desc, etsy_total=etsy_total, note=err)
            break
        margin = round((etsy_total - cost) / etsy_total, 3) if etsy_total else 0
        if margin < a.margin_min:
            warn.append(f"MARJ_DUSUK {margin:.0%} (< {a.margin_min:.0%}): Etsy {etsy_total} / Prodigi {cost}")
        if a.dry_run:
            upd(st, a.state, rid, stage="dryrun", country=country, items=desc, etsy_total=etsy_total, prodigi_cost=cost,
                margin=margin, warn="; ".join(warn), note="dry-run: siparis verilmedi")
            report.append(f"- {rid}: DRY-RUN {country} {desc} | Etsy {etsy_total} USD, Prodigi {cost} USD, marj {margin:.0%}" + (f" | {'; '.join(warn)}" if warn else ""))
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
            stc, d = prod.create_order(order_body(r, items, urls))
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

    # ---- 2) ordered: asset izinleri + kargo
    if not a.dry_run:
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
                kw.update(stage="shipped", tracking=ship["tracking"]["number"], carrier=(ship.get("carrier") or {}).get("name") or "")
                report.append(f"- {rid}: SHIPPED {kw['carrier']} {kw['tracking']}")
            upd(st, a.state, rid, **kw)

    # ---- 3) shipped -> Etsy tracking
    for rid, row in list(st.items()):
        if row.get("stage") != "shipped":
            continue
        if a.dry_run or not a.etsy_writes or api is None:
            report.append(f"- {rid}: Etsy tracking yazilmadi ({'dry-run' if a.dry_run else 'etsy-writes kapali / test'}); tracking {row.get('tracking')}")
            continue
        try:
            api.post(f"/shops/{shop}/receipts/{rid}/tracking", {"tracking_code": row["tracking"], "carrier_name": row.get("carrier") or "other", "send_bcc": "true"})
            back = api.get(f"/shops/{shop}/receipts/{rid}") or {}
            ok = bool(back.get("is_shipped")) or any((s.get("tracking_code") == row["tracking"]) for s in back.get("shipments") or [])
            upd(st, a.state, rid, stage="tracked" if ok else "shipped", note="Etsy tracking yazildi" + ("" if ok else " (geri okuma dogrulanamadi)"))
            report.append(f"- {rid}: TRACKED -> Etsy {'PASS' if ok else 'FAIL geri okuma'}")
        except SystemExit as e:
            errors.append(f"{rid}: Etsy tracking {e}")
            upd(st, a.state, rid, stage="error", note=f"Etsy tracking: {e}")
            break

    counts = {}
    for row in st.values():
        counts[row.get("stage", "")] = counts.get(row.get("stage", ""), 0) + 1
    report += ["", f"STATE: {counts}", ""] + ([f"HATA: {e}" for e in errors] or ["hata yok"])
    text = "\n".join(report)
    log(text)
    (out / "REPORT.md").write_text(text + "\n", encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if errors:
        sys.exit("DUR: hata var, STATE yazildi")


if __name__ == "__main__":
    main()
