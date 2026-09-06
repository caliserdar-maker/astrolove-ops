#!/usr/bin/env python3
"""
"Everywhere else" kargo ucreti icin Prodigi teklifi (salt okur) - Mo, 6 Eyl 2026.

8 ornek ulke (TR, JP, BR, IN, ZA, MX, AE, KR) x GLOBAL-HPR-18x24, Standard kargo, USD.
ucret = ortalama(Standard kargo) - Budget US (fiyata gomulu) -> bir ust .99 (ceil - 0.01).
Ulke sapmasi |kargo - ortalama| / ortalama > %50 ise DUR (exit 2), rapor yazilir.
Cikti: PRODIGI_SHIP_EVERYWHERE.csv/.md (+ .json: fee) -> gdrive:ASTROLOVE/TEMP/PRODIGI/
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_hpr_sizes import parse_quote  # noqa: E402
from prodigi_pilot_quote import Api, leak_check, load_key, log  # noqa: E402

COUNTRIES = ["TR", "JP", "BR", "IN", "ZA", "MX", "AE", "KR"]
SKU = "GLOBAL-HPR-18x24"
DEV_MAX = 0.50


def to_99(x):
    return round(math.ceil(x) - 0.01, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--budget-us", type=float, default=None, help="Budget US kargo (bos = API'den okunur)")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    rows = []
    for cc in ["US"] + COUNTRIES:
        q, err = api.quote(SKU, {}, dest=cc)
        m = parse_quote(q) if q else {}
        std = m.get("standard"); bud = m.get("budget")
        rows.append(dict(ulke=cc, standard_kargo=std[0] if std else "", budget_kargo=bud[0] if bud else "",
                         birim=next((v[1] for v in m.values() if v[1]), ""), lab=next((v[2] for v in m.values() if v[2]), ""),
                         yontemler=",".join(m.keys()), hata=err))
        log(f"{cc}: standard {std[0] if std else '-'} budget {bud[0] if bud else '-'} lab {rows[-1]['lab']} {err}")
    us = rows[0]
    budget_us = a.budget_us if a.budget_us is not None else (float(us["budget_kargo"]) if us["budget_kargo"] != "" else None)
    vals = {r["ulke"]: float(r["standard_kargo"]) for r in rows[1:] if r["standard_kargo"] != ""}
    missing = [r["ulke"] for r in rows[1:] if r["standard_kargo"] == ""]
    mean = sum(vals.values()) / len(vals) if vals else 0
    devs = {cc: (v - mean) / mean if mean else 0 for cc, v in vals.items()}
    big = {cc: d for cc, d in devs.items() if abs(d) > DEV_MAX}
    fee = to_99(mean - budget_us) if (vals and budget_us is not None) else None
    with open(out / "PRODIGI_SHIP_EVERYWHERE.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["sapma"]); w.writeheader()
        for r in rows:
            w.writerow({**r, "sapma": f"{devs[r['ulke']]:+.0%}" if r["ulke"] in devs else ""})
    md = [f"# Everywhere else kargo ({SKU}, Standard, USD) — {len(vals)}/{len(COUNTRIES)} ulke", "",
          "| ulke | Standard | Budget | lab | sapma |", "|---|---|---|---|---|"]
    md += [f"| {r['ulke']} | {r['standard_kargo']} | {r['budget_kargo']} | {r['lab']} | {('%+.0f%%' % (devs[r['ulke']] * 100)) if r['ulke'] in devs else r['hata']} |" for r in rows]
    md += ["", f"- ortalama Standard: {mean:.2f} USD; Budget US (gomulu): {budget_us}",
           f"- ucret = {mean:.2f} - {budget_us} = {(mean - budget_us) if budget_us is not None else '-'} -> **{fee} USD**; teslim 7-21 is gunu",
           f"- sapma > %{DEV_MAX:.0%}: {big or 'yok'}; eksik: {missing or 'yok'}"]
    (out / "PRODIGI_SHIP_EVERYWHERE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "PRODIGI_SHIP_EVERYWHERE.json").write_text(json.dumps({"fee": fee, "mean": round(mean, 2), "budget_us": budget_us, "big_dev": big, "missing": missing, "values": vals}, indent=1))
    leak_check(out)
    log("\n".join(md))
    if missing or big or fee is None:
        sys.exit(2)


if __name__ == "__main__":
    main()
