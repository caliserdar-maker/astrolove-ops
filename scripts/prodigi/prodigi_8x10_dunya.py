#!/usr/bin/env python3
"""BY Shipped print 8x10 (GLOBAL-HPR-8x10) dunya kargo maliyeti (SALT OKUMA, 15 Eki 2026, Serdar A plani).
Yalniz POST /v4.0/quotes (siparis OLUSTURMAZ). Etsy cagrisi YOK.
Ulkeler: Etsy kargo bolgeleri (US, EU ornekleri, GB, AU) + "Everywhere else" ornekleri (CA, NO, CH, NZ, JP, KR, SG, HK, AE, IL,
MX, BR, IN, ZA, TR). Yontem: yanittaki tum yontemler (Budget/Standard/Express...), USD; tasiyici adi yanittan.
Net ($29, kargo ucretsiz): net = 29 - (0.698 + 0.2062 x 29) - (urun + kargo + vergi)  [Etsy kesintisi KDV dahil,
docs/REFERANS_ILAN_CL.md]; net_offsite = net - 0.15 x 29 (Offsite Ads ile gelen satis).
Ek ucret onerisi: kargo ucretli olursa ucret de Etsy kesintisine girer -> F = ceil((hedef_net - net) / (1 - 0.2062)).
Cikti: DUNYA_8x10.csv, DUNYA_8x10.md, raw/<ulke>.json -> gdrive:ASTROLOVE/TEMP/PRODIGI/DUNYA_8x10_20261015/
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_maliyet_api import ayikla  # noqa: E402
from prodigi_pilot_quote import Api, leak_check, load_key, log  # noqa: E402

SKU = "GLOBAL-HPR-8x10"
FIYAT = 29.0
SABIT, ORAN = 0.698, 0.2062
HEDEF_NET = 5.0
BOLGE = {"US": "US", "DE": "EU", "FR": "EU", "IT": "EU", "ES": "EU", "NL": "EU", "IE": "EU", "SE": "EU", "PL": "EU",
         "GB": "GB", "AU": "AU",
         "CA": "diger", "NO": "diger", "CH": "diger", "NZ": "diger", "JP": "diger", "KR": "diger", "SG": "diger",
         "HK": "diger", "AE": "diger", "IL": "diger", "MX": "diger", "BR": "diger", "IN": "diger", "ZA": "diger", "TR": "diger"}


def tasiyici(q, yontem):
    for qu in (q or {}).get("quotes") or []:
        if (qu.get("shipmentMethod") or "").replace(" ", "").lower() == yontem:
            c = [f"{(sh.get('carrier') or {}).get('name', '')} {(sh.get('carrier') or {}).get('service', '')}".strip()
                 for sh in qu.get("shipments") or []]
            return " / ".join(dict.fromkeys(x for x in c if x))
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    out = Path(a.out_dir); (out / "raw").mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    etsy = round(SABIT + ORAN * FIYAT, 2)
    rows = []
    for cc, bolge in BOLGE.items():
        q, err = api.quote(SKU, {}, dest=cc)
        (out / "raw" / f"{cc}.json").write_text(json.dumps(q or {"hata": err}, indent=1))
        m = ayikla(q) if q else {}
        if not m:
            rows.append(dict(ulke=cc, bolge=bolge, yontem="", hata=err)); log(f"{cc}: {err}"); continue
        for y, v in m.items():
            if None in (v["urun"], v["kargo"]):
                rows.append(dict(ulke=cc, bolge=bolge, yontem=y, hata="tutar eksik")); continue
            vergi = v["vergi"] or 0.0
            maliyet = round(v["urun"] + v["kargo"] + vergi, 2)
            net = round(FIYAT - etsy - maliyet, 2)
            ek = 0 if net >= HEDEF_NET else math.ceil((HEDEF_NET - net) / (1 - ORAN))
            rows.append(dict(ulke=cc, bolge=bolge, yontem=y, urun=v["urun"], kargo=v["kargo"], vergi=vergi, para=v["para"],
                             maliyet=maliyet, etsy_kesinti=etsy, net=net, net_offsite=round(net - 0.15 * FIYAT, 2),
                             ek_ucret_hedef5=ek, lab=v["lab"], tasiyici=tasiyici(q, y), vergi_faturada=v["faturada"], hata=""))
        log(f"{cc}: " + " | ".join(f"{y} {v['kargo']}" for y, v in m.items()))
    alan = ["ulke", "bolge", "yontem", "urun", "kargo", "vergi", "para", "maliyet", "etsy_kesinti", "net", "net_offsite",
            "ek_ucret_hedef5", "lab", "tasiyici", "vergi_faturada", "hata"]
    with open(out / "DUNYA_8x10.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, restval=""); w.writeheader(); w.writerows(rows)
    md = [f"# {SKU} dunya kargo (Prodigi quote, USD, salt okuma) | fiyat {FIYAT} | Etsy kesinti {etsy} | hedef net {HEDEF_NET}", "",
          "| ulke | bolge | yontem | urun | kargo | vergi | maliyet | net | net_offsite | ek ucret (net>=5) | lab | tasiyici |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['ulke']} | {r['bolge']} | {r.get('yontem', '')} | {r.get('urun', '')} | {r.get('kargo', '')} | {r.get('vergi', '')} | "
                  f"{r.get('maliyet', '')} | {r.get('net', '')} | {r.get('net_offsite', '')} | {r.get('ek_ucret_hedef5', '')} | "
                  f"{r.get('lab', '')} | {r.get('tasiyici', '') or r.get('hata', '')} |")
    (out / "DUNYA_8x10.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    leak_check(out)
    print("\n".join(md))
    eksik = [r["ulke"] for r in rows if r.get("hata")]
    print(f"::warning::DUNYA 8x10 | ulke {len(BOLGE)} | satir {len(rows)} | eksik {eksik or 'yok'}")


if __name__ == "__main__":
    main()
