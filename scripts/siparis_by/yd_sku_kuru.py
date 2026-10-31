#!/usr/bin/env python3
"""1st Anniversary yeni SKU bicimi siparis hattinda KURU sinama (Serdar 31 Eki karar 5b). AG YOK: Etsy / Printful / Prodigi istegi yok,
gercek siparis yok. Sahte makbuz kalemleri (SKU + varyasyonlar) siparis hattinin SKU okuyan noktalarindan gecirilir:
  R  scripts/prodigi/order_router.py parse_items + dijital_mi  (Prodigi'ye gidecek kalem / DIJITAL / PRINTFUL_ELLE / POD disi)
  P  scripts/etsy/pod_sku.py parse_sku + is_digital_sku       (poster SKU cozucusu)
  G  scripts/etsy/burc_gift_yaz.py siparis_say kosulu          (gonderilmemis baski sayimi: SKU PRINT8X10 ya da 'shipped print')
  K  scripts/kupa_siparis/kupa_siparis.py sku_coz             (kupa SKU cozucusu; YD SKU'sunu kupa sanmamali)
Yeni SKU: <BY-AAA_BBB-STIL>-<boy> (Print), ...-<boy>-DIGITAL (Digital File) (scripts/etsy/yd_yapi_kuru.py envanter_plani).
Eski SKU: ...-CARD5X7 / -FILE8X10 / -PRINT8X10 (canli).
Cikti --out: SKU_KURU.csv (her SKU satiri) + OZET.md (format x boy grubu tablosu). Cikis 0 her zaman (rapor)."""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
for p in ("scripts/prodigi", "scripts/etsy", "scripts/kupa_siparis"):
    sys.path.insert(0, str(KOK / p))
import order_router as R  # noqa: E402
import pod_sku as P  # noqa: E402
import yd_yapi_kuru as Y  # noqa: E402

STIL_KOD = {s: s.upper().replace(" ", "") for s in Y.STILLER}
ORNEK = [("CANCER_LIBRA", "CAN_LIB"), ("LEO_LEO", "LEO_LEO")]


def kalem(sku, stil, fmt, boy_etiket):
    var = [dict(property_name="Style", formatted_value=stil), dict(property_name="Format", formatted_value=fmt)]
    if boy_etiket:
        var.append(dict(property_name="Size", formatted_value=boy_etiket))
    return dict(transaction_id=1, listing_id=4595350971, sku=sku, quantity=1, price=dict(amount=1990, divisor=100), variations=var)


def kupa_coz(sku):
    try:
        import kupa_siparis as KS
        r, _ = KS.sku_coz(sku)                          # (sonuc, hata) cifti doner
        return "TANIR" if r else "TANIMAZ"
    except SystemExit as e:
        return f"DUR ({str(e)[:40]})"
    except Exception as e:  # noqa: BLE001
        return f"HATA {type(e).__name__}"


def sinifla(t):
    items, other, atl = R.parse_items({"transactions": [t]})
    if items:
        return f"PRODIGI ({items[0]['prodigi_sku']})"
    o = other[0] if other else ""
    return "DIJITAL" if o.startswith("DIJITAL:") else "PRINTFUL_ELLE" if o.startswith("PRINTFUL_ELLE:") else "POD_DISI (elle)"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir = []
    for cift, kod in ORNEK:
        for stil in Y.STILLER:
            pre = f"BY-{kod}-{STIL_KOD[stil]}"
            for fmt in Y.FORMATLAR:
                for etiket, boy in Y.BOYLAR:
                    sku = f"{pre}-{boy}" + ("-DIGITAL" if fmt == Y.DIJITAL else "")
                    satir.append(("yeni", cift, stil, fmt, boy, sku, kalem(sku, stil, fmt, etiket)))
            for eski_fmt, ek in Y.ESKI_SKU_EK.items():
                sku = f"{pre}-{ek}"
                satir.append(("eski", cift, stil, eski_fmt, ek, sku, kalem(sku, stil, eski_fmt, None)))
    rows = []
    for tur, cift, stil, fmt, boy, sku, t in satir:
        g = "PRINT8X10" in sku.upper() or "shipped print" in " ".join(v["formatted_value"] for v in t["variations"]).lower()
        rows.append(dict(tur=tur, cift=cift, stil=stil, format=fmt, boy=boy, sku=sku, router=sinifla(t), router_dijital=R.dijital_mi(t),
                         pod_sku=bool(P.parse_sku(sku)), pod_dijital=P.is_digital_sku(sku), gift_baski_sayimi=g, kupa=kupa_coz(sku)))
    with open(out / "SKU_KURU.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    grup = defaultdict(lambda: defaultdict(set))
    for r in rows:
        k = (r["tur"], r["format"], "5x7" if r["boy"] == "5x7" else ("diger 13 boy" if r["tur"] == "yeni" else r["boy"]))
        for alan in ("router", "router_dijital", "pod_sku", "gift_baski_sayimi", "kupa"):
            grup[k][alan].add(str(r[alan]).split(" (")[0] if alan == "router" else str(r[alan]))
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# 1st Anniversary SKU kuru sinama (ag yok)\n\nSKU {len(rows)} (ornek ciftler {', '.join(c for c, _ in ORNEK)}; 5 stil)\n\n"
                "| SKU | format | boy | order_router | dijital_mi | pod_sku.parse_sku | gift baski sayimi | kupa sku_coz |\n"
                "|---|---|---|---|---|---|---|---|\n")
        for (tur, fmt, boy), v in sorted(grup.items()):
            f.write(f"| {tur} | {fmt} | {boy} | {'/'.join(sorted(v['router']))} | {'/'.join(sorted(v['router_dijital']))} | "
                    f"{'/'.join(sorted(v['pod_sku']))} | {'/'.join(sorted(v['gift_baski_sayimi']))} | {'/'.join(sorted(v['kupa']))} |\n")
    print(open(out / "OZET.md", encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
