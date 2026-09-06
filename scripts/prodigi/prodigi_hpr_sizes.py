#!/usr/bin/env python3
"""
Prodigi HPR (Hahnemuhle Photo Rag 308gsm) boyut + ABD/AB teklif okuma (salt okur).

Aday SKU'lar hpr_sizes.txt'ten (satir basina bir SKU; tahmin eklenmez). Her aday
GET /products ile dogrulanir (404 -> "yok"); gecerli her SKU icin iki teklif:
US (Budget/Standard/Express) ve DE (AB lab'i, kargo). Ikisi de USD ile istenir
(karsilastirma icin tek para birimi). Cikti: PRODIGI_HPR_SIZES.csv + .md ->
gdrive:ASTROLOVE/TEMP/PRODIGI/. Anahtar: prodigi_pilot_quote.load_key (maskeli).
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_pilot_quote import Api, CURRENCY, OUT_REMOTE, leak_check, load_key, log, money  # noqa: E402

HERE = Path(__file__).resolve().parent
FIELDS = ["sku", "durum", "boyut_inch", "boyut_cm", "gerekli_px", "dpi",
          "birim_fiyat_US", "kargo_B_US", "kargo_S_US", "kargo_E_US", "lab_US",
          "birim_fiyat_DE", "kargo_S_DE", "lab_DE", "para_birimi", "notlar"]


def dims(prod):
    d = prod.get("productDimensions") or {}
    w, h, u = d.get("width"), d.get("height"), (d.get("units") or "").lower()
    if not w:
        return "", "", 0
    if u.startswith("cm"):
        return f"{w/2.54:.1f}x{h/2.54:.1f}", f"{w}x{h}", max(w, h) / 2.54
    return f"{w}x{h}", f"{w*2.54:.1f}x{h*2.54:.1f}", max(w, h)


def parse_quote(q):
    """{method: (shipping, unit, lab, carrier)}"""
    out = {}
    for qu in q.get("quotes") or []:
        m = (qu.get("shipmentMethod") or "").replace(" ", "").lower()
        unit = money((qu.get("items") or [{}])[0].get("unitCost"))
        ship = money((qu.get("costSummary") or {}).get("shipping"))
        labs, cars = [], []
        for sh in qu.get("shipments") or []:
            fl = sh.get("fulfillmentLocation") or {}
            labs.append(f"{fl.get('countryCode', '')}/{fl.get('labCode', '')}")
            ca = sh.get("carrier") or {}
            cars.append(f"{ca.get('name', '')} {ca.get('service', '')}".strip())
        out[m] = (ship, unit, ", ".join(dict.fromkeys(labs)), ", ".join(dict.fromkeys(cars)))
    return out


def process(api, sku):
    row = {k: "" for k in FIELDS}
    row["sku"] = sku
    prod, err = api.product(sku)
    if prod is None:
        row["durum"] = "yok" if "404" in err else "hata"
        row["notlar"] = err
        return row
    row["durum"] = "gecerli"
    row["boyut_inch"], row["boyut_cm"], long_in = dims(prod)
    variants = prod.get("variants") or []
    var = variants[0] if variants else {}
    pas = (var.get("printAreaSizes") or {}).get("default") or {}
    px = max(pas.get("horizontalResolution") or 0, pas.get("verticalResolution") or 0)
    row["gerekli_px"] = px or ""
    row["dpi"] = round(px / long_in) if px and long_in else ""
    attrs = {k: v[0] for k, v in (prod.get("attributes") or {}).items() if v}
    attrs.update({k: v for k, v in (var.get("attributes") or {}).items() if v is not None})
    ships = var.get("shipsTo") or []
    notes = []
    for cc in ("US", "DE"):
        if ships and cc not in ships:
            notes.append(f"{cc}: shipsTo listesinde yok")
    row["para_birimi"] = CURRENCY

    q, err = api.quote(sku, attrs, dest="US")
    if q:
        m = parse_quote(q)
        row["birim_fiyat_US"] = next((v[1] for v in m.values() if v[1]), "")
        row["kargo_B_US"] = m.get("budget", ("",))[0]
        row["kargo_S_US"] = m.get("standard", ("",))[0]
        row["kargo_E_US"] = m.get("express", ("",))[0]
        row["lab_US"] = next((v[2] for v in m.values() if v[2]), "")
        for i in q.get("issues") or []:
            if "SalesTax" not in (i.get("errorCode") or ""):
                notes.append(f"US {i.get('errorCode')}: {i.get('description')}")
    else:
        notes.append(f"US teklif yok: {err}")

    q, err = api.quote(sku, attrs, dest="DE")
    if q:
        m = parse_quote(q)
        row["birim_fiyat_DE"] = next((v[1] for v in m.values() if v[1]), "")
        std = m.get("standard") or next(iter(m.values()), ("", "", "", ""))
        row["kargo_S_DE"] = std[0]
        row["lab_DE"] = next((v[2] for v in m.values() if v[2]), "")
        others = "; ".join(f"DE {k}={v[0]}" for k, v in m.items() if k != "standard")
        if others:
            notes.append(others)
        if "standard" not in m:
            notes.append("DE: Standard yok, ilk yontem yazildi")
        for i in q.get("issues") or []:
            notes.append(f"DE {i.get('errorCode')}: {i.get('description')}")
    else:
        notes.append(f"DE teklif yok: {err}")
    row["notlar"] = "; ".join(notes)
    return row


def write_outputs(rows, out_dir, started, elapsed):
    out_dir = Path(out_dir)
    csv_p = out_dir / "PRODIGI_HPR_SIZES.csv"
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r["durum"] == "gecerli"]
    md = [f"# Prodigi HPR boyutlar — US + DE teklifleri ({CURRENCY}) — {started:%Y-%m-%d %H:%M} UTC", "",
          f"Aday: {len(rows)} · gecerli: {len(ok)} · yok: {sum(r['durum']=='yok' for r in rows)} · sure: {elapsed:.0f}s", "",
          "| sku | inch | cm | px | dpi | birim US | B/S/E US | lab US | birim DE | S DE | lab DE |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ok:
        md.append(f"| {r['sku']} | {r['boyut_inch']} | {r['boyut_cm']} | {r['gerekli_px']} | {r['dpi']} | {r['birim_fiyat_US']} "
                  f"| {r['kargo_B_US']}/{r['kargo_S_US']}/{r['kargo_E_US']} | {r['lab_US']} | {r['birim_fiyat_DE']} | {r['kargo_S_DE']} | {r['lab_DE']} |")
    no_eu = [r["sku"] for r in ok if r["lab_DE"] and not any(r["lab_DE"].startswith(c) for c in ("DE", "NL", "FR", "ES", "IT", "PL", "AT", "BE", "CZ", "SE", "DK", "IE", "PT", "FI", "HU", "RO", "SK", "SI", "LT", "LV", "EE", "HR", "BG", "GR", "LU", "MT", "CY"))]
    md += ["", "## AB disi lab'dan gonderilen boyutlar (DE teklifi)", ""] + ([f"- {s}" for s in no_eu] or ["- yok"])
    md += ["", "## Yok (404)", ""] + ([f"- {r['sku']}" for r in rows if r["durum"] == "yok"] or ["- yok"])
    bad = [r for r in rows if r["durum"] == "hata" or "teklif yok" in r["notlar"]]
    if bad:
        md += ["", "## Hatali", ""] + [f"- {r['sku']}: {r['notlar']}" for r in bad]
    (out_dir / "PRODIGI_HPR_SIZES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return csv_p, out_dir / "PRODIGI_HPR_SIZES.md"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skus-file", default=str(HERE / "hpr_sizes.txt"))
    ap.add_argument("--out-dir", default=str(HERE / "_out"))
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    started = datetime.now(timezone.utc)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    skus = [l.strip() for l in Path(a.skus_file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    log(f"aday: {len(skus)} HPR SKU, hedefler US + DE")
    rows, t0 = [], time.time()
    for i, sku in enumerate(skus, 1):
        try:
            row = process(api, sku)
        except Exception as e:                        # satiri atla, kosu durmasin
            row = {k: "" for k in FIELDS}
            row.update(sku=sku, durum="hata", notlar=f"{type(e).__name__}: {e}")
        rows.append(row)
        el = time.time() - t0
        log(f"[{i}/{len(skus)}] {sku:<18} {row['durum']:<8} US={row['birim_fiyat_US'] or '-':<6} DE={row['birim_fiyat_DE'] or '-':<6} "
            f"lab_DE={row['lab_DE'] or '-':<14} gecen={el:.0f}s kalan~{el/i*(len(skus)-i):.0f}s")
    csv_p, md_p = write_outputs(rows, out_dir, started, time.time() - t0)
    leak_check(out_dir)
    log(f"\nbitti: {len(rows)} satir, {sum(r['durum']=='gecerli' for r in rows)} gecerli, {time.time()-t0:.0f}s")
    if not a.no_drive:
        for p in (csv_p, md_p):
            subprocess.run(["rclone", "copyto", str(p), f"{OUT_REMOTE}/{p.name}"], check=True)
        log(f"Drive: {OUT_REMOTE}/ guncellendi")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md_p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
