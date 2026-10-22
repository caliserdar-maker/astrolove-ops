#!/usr/bin/env python3
"""ONCELIK 6 - Etsy Ads KPI hesaplayici (CSV geldiginde calisir; veri UYDURMAZ).

Girdi: Shop Manager > Marketing > Etsy Ads ekranindan indirilen CSV
(kolonlar: date, listing_id, listing_title, impressions, clicks, spend, orders,
revenue, currency - bkz. etsy_ads_column_dictionary.csv).

Hesaplar: CTR, CPC, donusum orani, ROAS, bosa giden harcama (wasted spend);
ilan basina karar sinifi: PAUSE / REVIEW / REDUCE / KEEP / WATCH.

Karar kurallari (esikler --ile degistirilebilir; sira onemlidir):
  PAUSE   : tiklama >= pause_click ve siparis = 0 ve harcama >= pause_spend
  REVIEW  : tiklama >= min_click ve siparis = 0            (para harciyor, satis yok)
  REDUCE  : ROAS < roas_dusuk ve harcama >= min_spend
  KEEP    : ROAS >= roas_iyi
  WATCH   : digerleri (yeterli veri yok ya da orta bant)
Hic tiklanmayan ilanlar ayrica listelenir (gosterim var, tiklama 0).

Kullanim: ads_kpi.py --csv etsy_ads_stats.csv --out OUT [--gun 7]
"""
import argparse
import csv
import json
import pathlib
from collections import defaultdict
from datetime import datetime, timezone

GEREKLI = ["listing_id", "impressions", "clicks", "spend"]


def sayi(x, ondalik=False):
    try:
        return float(str(x).replace(",", ".").replace("$", "").strip()) if ondalik \
            else int(float(str(x).replace(",", "").strip() or 0))
    except (ValueError, TypeError):
        return 0.0 if ondalik else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-click", type=int, default=15)
    ap.add_argument("--pause-click", type=int, default=30)
    ap.add_argument("--pause-spend", type=float, default=10.0)
    ap.add_argument("--min-spend", type=float, default=3.0)
    ap.add_argument("--roas-dusuk", type=float, default=1.0)
    ap.add_argument("--roas-iyi", type=float, default=2.0)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    p = pathlib.Path(a.csv)
    if not p.exists():
        raise SystemExit(f"HATA: {a.csv} yok. Once Shop Manager'dan CSV indirip Drive'a koyun. DUR.")
    with open(p, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("HATA: CSV bos. DUR.")
    eksik = [k for k in GEREKLI if k not in rows[0]]
    if eksik:
        raise SystemExit(f"HATA: CSV'de eksik kolon: {eksik}. Kolon sozlugune bakin. DUR.")

    ilan = defaultdict(lambda: {"impressions": 0, "clicks": 0, "spend": 0.0,
                                "orders": 0, "revenue": 0.0, "title": "", "gun": set()})
    for r in rows:
        lid = str(r.get("listing_id") or "").strip()
        if not lid:
            continue
        d = ilan[lid]
        d["impressions"] += sayi(r.get("impressions"))
        d["clicks"] += sayi(r.get("clicks"))
        d["spend"] += sayi(r.get("spend"), True)
        d["orders"] += sayi(r.get("orders"))
        d["revenue"] += sayi(r.get("revenue"), True)
        d["title"] = d["title"] or (r.get("listing_title") or "")
        if r.get("date"):
            d["gun"].add(r["date"])

    satir, toplam = [], defaultdict(float)
    for lid, d in ilan.items():
        ctr = d["clicks"] / d["impressions"] * 100 if d["impressions"] else 0.0
        cpc = d["spend"] / d["clicks"] if d["clicks"] else 0.0
        cr = d["orders"] / d["clicks"] * 100 if d["clicks"] else 0.0
        roas = d["revenue"] / d["spend"] if d["spend"] else 0.0
        bosa = d["spend"] if d["orders"] == 0 else 0.0
        if d["clicks"] >= a.pause_click and d["orders"] == 0 and d["spend"] >= a.pause_spend:
            karar, neden = "PAUSE", (f"{d['clicks']} tiklama, 0 siparis, "
                                     f"{d['spend']:.2f} harcama")
        elif d["clicks"] >= a.min_click and d["orders"] == 0:
            karar, neden = "REVIEW", f"{d['clicks']} tiklama, 0 siparis"
        elif d["spend"] >= a.min_spend and roas < a.roas_dusuk:
            karar, neden = "REDUCE", f"ROAS {roas:.2f} < {a.roas_dusuk}"
        elif roas >= a.roas_iyi:
            karar, neden = "KEEP", f"ROAS {roas:.2f} >= {a.roas_iyi}"
        else:
            karar, neden = "WATCH", "yeterli veri yok ya da orta bant"
        for k in ("impressions", "clicks", "spend", "orders", "revenue"):
            toplam[k] += d[k]
        toplam["bosa"] += bosa
        satir.append({"listing_id": lid, "baslik": d["title"][:70], "gun": len(d["gun"]),
                      "impressions": d["impressions"], "clicks": d["clicks"],
                      "ctr_yuzde": round(ctr, 3), "spend": round(d["spend"], 2),
                      "cpc": round(cpc, 3), "orders": d["orders"],
                      "conversion_yuzde": round(cr, 2), "revenue": round(d["revenue"], 2),
                      "roas": round(roas, 2), "wasted_spend": round(bosa, 2),
                      "karar": karar, "neden": neden})
    satir.sort(key=lambda x: (-x["wasted_spend"], -x["spend"]))
    with open(out / "ads_kpi_by_listing.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(satir[0]))
        w.writeheader()
        for x in satir:
            w.writerow(x)

    hic_tiklanmayan = [x for x in satir if x["impressions"] > 0 and x["clicks"] == 0]
    tiklanip_satmayan = [x for x in satir if x["clicks"] > 0 and x["orders"] == 0]
    g_ctr = toplam["clicks"] / toplam["impressions"] * 100 if toplam["impressions"] else 0
    g_cpc = toplam["spend"] / toplam["clicks"] if toplam["clicks"] else 0
    g_roas = toplam["revenue"] / toplam["spend"] if toplam["spend"] else 0
    md = [f"# Etsy Ads KPI ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
          f"- Ilan: {len(satir)} | gosterim {int(toplam['impressions'])} | "
          f"tiklama {int(toplam['clicks'])} | harcama {toplam['spend']:.2f}",
          f"- CTR **{g_ctr:.2f}%** | CPC **{g_cpc:.3f}** | ROAS **{g_roas:.2f}** | "
          f"bosa giden harcama **{toplam['bosa']:.2f}**",
          f"- Hic tiklanmayan ilan: **{len(hic_tiklanmayan)}**",
          f"- Tiklanip satis almayan ilan: **{len(tiklanip_satmayan)}**", "",
          "## Karar dagilimi", ""]
    from collections import Counter
    for k, n in Counter(x["karar"] for x in satir).most_common():
        md.append(f"- {k}: {n}")
    md += ["", "## En cok bosa harcama yapan 15 ilan", "",
           "| listing | tiklama | harcama | ROAS | karar |", "|---|---:|---:|---:|---|"]
    for x in satir[:15]:
        md.append(f"| {x['listing_id']} | {x['clicks']} | {x['spend']} | {x['roas']} | {x['karar']} |")
    (out / "ads_kpi_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"ilan": len(satir), "ctr": round(g_ctr, 2), "roas": round(g_roas, 2),
                      "bosa": round(toplam["bosa"], 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
