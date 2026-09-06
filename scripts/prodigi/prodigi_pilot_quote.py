#!/usr/bin/env python3
"""
Prodigi pilot katalog + ABD fiyat/kargo okuma (salt okur; siparis vermez).

- API anahtari: rclone ile gdrive:ASTROLOVE/TEMP/PRODIGI_TOKEN.json ({"api_key": ...}).
  Yerel deneme icin PRODIGI_API_KEY ortam degiskeni de kabul edilir. Anahtar hicbir
  loga/dosyaya yazilmaz (::add-mask:: + cikti dosyalarinda sizinti kontrolu).
- Aday SKU'lar: scripts/prodigi/pilot_skus.csv (sinif,sku,not). Katalog ucu yok;
  her aday GET /products/{sku} ile dogrulanir (404 -> "gecersiz", devam).
- --discover: pilot_pages.txt'teki prodigi.com sayfalarindan GLOBAL-... kodlari
  toplanir, sinifi taninanlar aday listesine eklenir (DISCOVERED_SKUS.csv).
- Gecerli her SKU icin POST /quotes (US, USD, tum kargo yontemleri).
- Cikti: PRODIGI_PILOT_QUOTES.csv + .md -> gdrive:ASTROLOVE/TEMP/PRODIGI/
  (--no-drive ile yalniz yerel out-dir).

Kullanim:
  python prodigi_pilot_quote.py [--limit 3] [--discover] [--skus A,B] [--out-dir DIR] [--no-drive]
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://api.prodigi.com/v4.0"
TOKEN_REMOTE = "gdrive:ASTROLOVE/TEMP/PRODIGI_TOKEN.json"
OUT_REMOTE = "gdrive:ASTROLOVE/TEMP/PRODIGI"
HERE = Path(__file__).resolve().parent
DEST_COUNTRY = "US"
CURRENCY = "USD"
CLASSES = ["poster", "kupa", "kilif"]

POSTER_SIZES = {"8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "24x36", "a4", "a3", "a2"}
SKU_RE = re.compile(r"GLOBAL-[A-Z0-9]{2,6}(?:-[A-Za-z0-9.]{1,12}){1,4}")

FIELDS = ["sinif", "sku", "urun_adi", "boyut", "gerekli_px_uzun_kenar", "dpi", "attribute_secenekleri",
          "kullanilan_attribute", "birim_fiyat", "para_birimi",
          "kargo_budget", "kargo_standard", "kargo_standardplus", "kargo_express", "kargo_overnight",
          "uretim_ulkesi_lab", "kargo_firmasi", "abd_gonderim", "notlar"]

_secret = None


def log(msg):
    if _secret:
        msg = str(msg).replace(_secret, "***")
    print(msg, flush=True)


# ------------------------------------------------------------------ anahtar
def load_key():
    global _secret
    key = os.environ.get("PRODIGI_API_KEY")
    if not key:
        raw = subprocess.run(["rclone", "cat", TOKEN_REMOTE], capture_output=True, text=True)
        if raw.returncode != 0:
            sys.exit("HATA: PRODIGI_TOKEN.json okunamadi (rclone).")
        key = json.loads(raw.stdout).get("api_key")
    if not key:
        sys.exit("HATA: api_key bos.")
    key = key.strip()
    _secret = key
    print(f"::add-mask::{key}", flush=True)
    return key


# ------------------------------------------------------------------ http
class Api:
    def __init__(self, key):
        self.s = requests.Session()
        self.s.headers.update({"X-API-Key": key, "Content-Type": "application/json"})

    def _call(self, method, path, body=None):
        for attempt in range(3):
            r = self.s.request(method, API + path, json=body, timeout=40)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            return r
        return r

    def product(self, sku):
        r = self._call("GET", f"/products/{sku}")
        if r.status_code == 404:
            return None, "gecersiz (404)"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:120]}"
        d = r.json()
        if d.get("outcome", "").lower() != "ok" or "product" not in d:
            return None, f"outcome={d.get('outcome')}"
        return d["product"], ""

    def quote(self, sku, attributes):
        item = {"sku": sku, "copies": 1, "assets": [{"printArea": "default"}]}
        if attributes:
            item["attributes"] = attributes
        body = {"destinationCountryCode": DEST_COUNTRY, "currencyCode": CURRENCY, "items": [item]}
        r = self._call("POST", "/quotes", body)
        if r.status_code != 200:
            return None, f"quote HTTP {r.status_code}: {r.text[:160]}"
        d = r.json()
        if not d.get("quotes"):
            iss = "; ".join(f"{i.get('errorCode')}: {i.get('description')}" for i in d.get("issues", []) or [])
            return None, f"quote outcome={d.get('outcome')} {iss}".strip()
        return d, ""


# ------------------------------------------------------------------ adaylar
def classify(sku):
    u = sku.upper()
    parts = u.split("-")
    if "MUG" in u:
        return "kupa"
    if "TECH" in u or "CASE" in u or "PHONE" in u:
        return "kilif"
    if len(parts) >= 3 and parts[1] in {"FAP", "BLP", "HGE", "HPR", "EMA", "CFP", "PAP", "SAP", "MFA", "BAP"}:
        if parts[-1].lower() in POSTER_SIZES:
            return "poster"
    return None


def read_candidates(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("sku"):
                rows.append({"sinif": r["sinif"].strip(), "sku": r["sku"].strip(), "not": r.get("not", "").strip()})
    return rows


def discover(pages_file, out_dir):
    """prodigi.com sayfalarini ceker, GLOBAL-... kodlarini toplar."""
    found = {}
    urls = [l.strip() for l in Path(pages_file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    for u in urls:
        try:
            r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0 astrolove-ops"})
            hits = set(SKU_RE.findall(r.text)) if r.status_code == 200 else set()
            log(f"  kesif {u} -> HTTP {r.status_code}, {len(hits)} kod")
        except requests.RequestException as e:
            log(f"  kesif {u} -> HATA {type(e).__name__}")
            continue
        for h in hits:
            found.setdefault(h, u)
    p = Path(out_dir) / "DISCOVERED_SKUS.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sku", "sinif", "kaynak"])
        for sku in sorted(found):
            w.writerow([sku, classify(sku) or "", found[sku]])
    log(f"kesif: {len(found)} benzersiz kod -> {p.name}")
    return found


# ------------------------------------------------------------------ islem
def money(c):
    return (c or {}).get("amount", "")


def process(api, cand, raw_dir):
    sku = cand["sku"]
    row = {k: "" for k in FIELDS}
    row.update(sinif=cand["sinif"], sku=sku, notlar=cand.get("not", ""))
    prod, err = api.product(sku)
    if prod is None:
        row["notlar"] = f"{err}; {row['notlar']}".strip("; ")
        return row, "gecersiz" if "404" in err else "hata"
    if raw_dir:
        (raw_dir / f"{sku}.product.json").write_text(json.dumps(prod, indent=1))
    dims = prod.get("productDimensions") or {}
    w, h, units = dims.get("width"), dims.get("height"), dims.get("units", "")
    row["urun_adi"] = prod.get("description", "")
    row["boyut"] = f"{w}x{h} {units}".strip() if w else ""
    attrs = prod.get("attributes") or {}
    row["attribute_secenekleri"] = "; ".join(f"{k}={'|'.join(map(str, v))}" for k, v in attrs.items())
    variants = prod.get("variants") or []
    # US'e giden ilk varyant; yoksa ilk varyant
    var = next((v for v in variants if "US" in (v.get("shipsTo") or [])), variants[0] if variants else {})
    row["abd_gonderim"] = "evet" if "US" in (var.get("shipsTo") or []) else ("hayir" if variants else "")
    used = dict(var.get("attributes") or {})
    for k, vals in attrs.items():                      # varyantta yoksa ilk secenek
        used.setdefault(k, vals[0] if vals else None)
    used = {k: v for k, v in used.items() if v is not None}
    row["kullanilan_attribute"] = "; ".join(f"{k}={v}" for k, v in used.items())
    pas = (var.get("printAreaSizes") or {}).get("default") or {}
    px = max(pas.get("horizontalResolution") or 0, pas.get("verticalResolution") or 0)
    if px:
        row["gerekli_px_uzun_kenar"] = px
        if w and h:
            long_in = max(float(w), float(h)) / (2.54 if units.lower().startswith("cm") else 1.0)
            row["dpi"] = round(px / long_in) if long_in else ""

    q, err = api.quote(sku, used)
    if q is None:
        row["notlar"] = f"{err}; {row['notlar']}".strip("; ")
        return row, "hata"
    if raw_dir:
        (raw_dir / f"{sku}.quote.json").write_text(json.dumps(q, indent=1))
    labs, carriers = [], []
    for qu in q["quotes"]:
        m = (qu.get("shipmentMethod") or "").replace(" ", "").lower()
        col = f"kargo_{m}"
        if col in row:
            row[col] = money((qu.get("costSummary") or {}).get("shipping"))
        if not row["birim_fiyat"] and qu.get("items"):
            uc = qu["items"][0].get("unitCost") or {}
            row["birim_fiyat"], row["para_birimi"] = money(uc), uc.get("currency", "")
        for sh in qu.get("shipments") or []:
            fl = sh.get("fulfillmentLocation") or {}
            lab = f"{fl.get('countryCode', '')}/{fl.get('labCode', '')}"
            if lab not in labs:
                labs.append(lab)
            ca = sh.get("carrier") or {}
            c = f"{m}:{ca.get('name', '')} {ca.get('service', '')}".strip()
            if c not in carriers:
                carriers.append(c)
    issues = q.get("issues") or []
    if issues:
        row["notlar"] = ("; ".join(f"{i.get('errorCode')}: {i.get('description')}" for i in issues)
                         + "; " + row["notlar"]).strip("; ")
    row["uretim_ulkesi_lab"] = ", ".join(labs)
    row["kargo_firmasi"] = ", ".join(carriers)
    return row, "ok"


def write_outputs(rows, errors, out_dir, started):
    out_dir = Path(out_dir)
    csv_p = out_dir / "PRODIGI_PILOT_QUOTES.csv"
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r["birim_fiyat"]]
    md = [f"# Prodigi pilot teklifleri ({DEST_COUNTRY}, {CURRENCY}) — {started:%Y-%m-%d %H:%M} UTC", "",
          f"Aday: {len(rows)} · fiyat alinan: {len(ok)} · gecersiz/hatali: {len(rows) - len(ok)}", ""]
    for cls in CLASSES:
        sub = sorted((r for r in ok if r["sinif"] == cls), key=lambda r: (r["boyut"], float(r["birim_fiyat"])))
        if not sub:
            continue
        md += [f"## {cls} ({len(sub)})", "",
               "| sku | urun | boyut | px uzun kenar | dpi | birim | budget | standard | express | lab | attr |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sub:
            md.append(f"| {r['sku']} | {r['urun_adi'][:40]} | {r['boyut']} | {r['gerekli_px_uzun_kenar']} | {r['dpi']} "
                      f"| {r['birim_fiyat']} | {r['kargo_budget']} | {r['kargo_standard']} | {r['kargo_express']} "
                      f"| {r['uretim_ulkesi_lab']} | {r['kullanilan_attribute']} |")
        md.append("")
    bad = [r for r in rows if not r["birim_fiyat"]]
    if bad:
        md += ["## Gecersiz / hatali SKU", ""] + [f"- {r['sku']}: {r['notlar']}" for r in bad] + [""]
    if errors:
        md += ["## Kosu hatalari", ""] + [f"- {e}" for e in errors] + [""]
    (out_dir / "PRODIGI_PILOT_QUOTES.md").write_text("\n".join(md), encoding="utf-8")
    return csv_p, out_dir / "PRODIGI_PILOT_QUOTES.md"


def leak_check(out_dir):
    for p in Path(out_dir).rglob("*"):
        if p.is_file() and _secret and _secret in p.read_text(errors="ignore"):
            p.unlink()
            sys.exit(f"HATA: anahtar cikti dosyasina sizdi, dosya silindi: {p.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="siniflar arasi donusumlu, gecerli N SKU (0 = hepsi)")
    ap.add_argument("--discover", action="store_true", help="pilot_pages.txt sayfalarindan SKU topla")
    ap.add_argument("--skus", default="", help="aday listesini ez: virgullu SKU listesi")
    ap.add_argument("--out-dir", default=str(HERE / "_out"))
    ap.add_argument("--no-drive", action="store_true", help="Drive'a yukleme")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    started = datetime.now(timezone.utc)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw"
    raw_dir.mkdir(exist_ok=True)
    key = load_key()
    api = Api(key)

    if a.skus:
        cands = [{"sinif": classify(s.strip()) or "?", "sku": s.strip(), "not": "elle"} for s in a.skus.split(",") if s.strip()]
    else:
        cands = read_candidates(HERE / "pilot_skus.csv")
    if a.discover:
        known = {c["sku"].upper() for c in cands}
        for sku, src in discover(HERE / "pilot_pages.txt", out_dir).items():
            cls = classify(sku)
            if cls and sku.upper() not in known:
                cands.append({"sinif": cls, "sku": sku, "not": f"kesif: {src}"})
                known.add(sku.upper())

    # siniflar arasi donusumlu sira (limit=3 -> 1 poster, 1 kupa, 1 kilif hedefi)
    by_cls = {c: [x for x in cands if x["sinif"] == c] for c in CLASSES}
    other = [x for x in cands if x["sinif"] not in CLASSES]
    ordered = []
    while any(by_cls.values()):
        for c in CLASSES:
            if by_cls[c]:
                ordered.append(by_cls[c].pop(0))
    ordered += other
    log(f"aday: {len(ordered)} (poster {sum(1 for x in ordered if x['sinif']=='poster')}, "
        f"kupa {sum(1 for x in ordered if x['sinif']=='kupa')}, kilif {sum(1 for x in ordered if x['sinif']=='kilif')})"
        + (f", limit={a.limit} gecerli SKU" if a.limit else ""))

    rows, errors = [], []
    t0 = time.time()
    valid = 0
    if a.limit:
        # sirayla dene; sinif basina en fazla ceil(limit/3) gecerli
        per_cls = -(-a.limit // len(CLASSES))
        got = {c: 0 for c in CLASSES}
        for i, c in enumerate(ordered, 1):
            if valid >= a.limit:
                break
            if got.get(c["sinif"], 0) >= per_cls:
                continue
            try:
                row, st = process(api, c, raw_dir)
            except Exception as e:                    # satiri atla, kosu durmasin
                errors.append(f"{c['sku']}: {type(e).__name__}: {e}")
                continue
            rows.append(row)
            if st == "ok":
                valid += 1
                got[c["sinif"]] = got.get(c["sinif"], 0) + 1
            log(f"[{i}/{len(ordered)}] {c['sku']:<28} {st:<9} gecerli={valid}")
    else:
        def work(c):
            try:
                return c, process(api, c, raw_dir), None
            except Exception as e:
                return c, None, f"{c['sku']}: {type(e).__name__}: {e}"
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for i, (c, res, err) in enumerate(ex.map(work, ordered), 1):
                if err:
                    errors.append(err)
                    st = "HATA"
                else:
                    row, st = res
                    rows.append(row)
                    valid += st == "ok"
                el = time.time() - t0
                eta = el / i * (len(ordered) - i)
                log(f"[{i}/{len(ordered)}] {c['sku']:<28} {st:<9} gecerli={valid} gecen={el:.0f}s kalan~{eta:.0f}s")

    csv_p, md_p = write_outputs(rows, errors, out_dir, started)
    leak_check(out_dir)
    log(f"\nbitti: {len(rows)} satir, {valid} fiyatli, {len(errors)} kosu hatasi, {time.time()-t0:.0f}s")
    for e in errors:
        log(f"  HATA {e}")
    if not a.no_drive:
        for p in (csv_p, md_p, out_dir / "DISCOVERED_SKUS.csv"):
            if p.exists():
                subprocess.run(["rclone", "copyto", str(p), f"{OUT_REMOTE}/{p.name}"], check=True)
        log(f"Drive: {OUT_REMOTE}/ guncellendi")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md_p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
