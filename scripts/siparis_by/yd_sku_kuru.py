#!/usr/bin/env python3
"""1st Anniversary yeni SKU bicimi siparis hattinda KURU sinama (Serdar 31 Eki karar 5b). AG YOK: Etsy / Printful / Prodigi istegi yok,
gercek siparis yok. Sahte makbuz kalemleri (SKU + varyasyonlar) siparis hattinin SKU okuyan noktalarindan gecirilir:
  R  scripts/prodigi/order_router.py parse_items + dijital_mi  (Prodigi'ye gidecek kalem / DIJITAL / PRINTFUL_ELLE / POD disi)
  P  scripts/etsy/pod_sku.py parse_sku + is_digital_sku       (poster SKU cozucusu)
  G  scripts/etsy/burc_gift_yaz.py siparis_say kosulu          (gonderilmemis baski sayimi: SKU PRINT8X10 ya da 'shipped print')
  K  scripts/kupa_siparis/kupa_siparis.py sku_coz             (kupa SKU cozucusu; YD SKU'sunu kupa sanmamali)
  U  scripts/siparis_by/by_siparis.py OLCU                     (uretim boylari) + SKU uzunlugu (Etsy siniri 32)
  Makbuz bicimi gercek: formatted_name + Personalization variations icinde; mesajda "digital" gecen Print ayrica sinanir.
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
sys.path.insert(0, str(KOK / "scripts/siparis_by"))
import by_siparis as BS  # noqa: E402  uretim boylari (OLCU)
import by_sku as SK  # noqa: E402  YD SKU cozucusu (kisa + eski uzun kod)
import burc_gift_yaz as G  # noqa: E402  baski_mi (yazim kapisi baski sayimi)

ORNEK = [("CANCER_LIBRA", "CAN_LIB"), ("LEO_LEO", "LEO_LEO")]


def kalem(sku, stil, fmt, boy_etiket, mesaj="Anna & Max, forever"):
    """Gercek makbuz bicimi (kupa_siparis/ornek/sahte_receipt_9000000001.json): variations formatted_name + formatted_value,
    Personalization da variations icinde (inceleme 31 Eki)."""
    var = [dict(formatted_name="Style", formatted_value=stil), dict(formatted_name="Format", formatted_value=fmt)]
    if boy_etiket:
        var.append(dict(formatted_name="Size", formatted_value=boy_etiket))
    var.append(dict(formatted_name="Personalization", formatted_value=mesaj))
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
            for fmt in Y.FORMATLAR:
                for etiket, boy in Y.BOYLAR:
                    dig = fmt == Y.DIJITAL
                    satir.append(("yeni (kisa kod)", cift, stil, fmt, boy, SK.sku(kod, stil, boy, dig), etiket))
                    satir.append(("eski uzun kod + yeni boy", cift, stil, fmt, boy,
                                  f"BY-{kod}-{SK.UZUN[stil]}-{boy}" + ("-DIGITAL" if dig else ""), etiket))
            for eski_fmt, ek in Y.ESKI_SKU_EK.items():
                satir.append(("eski (canli)", cift, stil, eski_fmt, ek, f"BY-{kod}-{SK.UZUN[stil]}-{ek}", None))
    rows = []
    for tur, cift, stil, fmt, boy, sku, etiket in satir:
        dig_bek = "digital" in fmt.lower()
        t = kalem(sku, stil, fmt, etiket)
        t_msj = kalem(sku, stil, fmt, etiket, mesaj="our digital love story" if not dig_bek else "print it big for us")
        c = SK.coz(sku)
        bk = {"CARD5X7": "5x7", "FILE8X10": "8x10", "PRINT8X10": "8x10"}.get(boy, boy)
        rows.append(dict(tur=tur, cift=cift, stil=stil, format=fmt, boy=boy, sku=sku, sku_uzunluk=len(sku), sku_32_asar=len(sku) > 32,
                         cozucu=("TANIR" if c and c["stil"] == stil and c["boy"] == bk and c["dijital"] == dig_bek else
                                 "YANLIS" if c else "TANIMAZ"),
                         router=sinifla(t), router_dijital=R.dijital_mi(t), router_mesajli=sinifla(t_msj),
                         tur_dogru=R.dijital_mi(t) == dig_bek and R.dijital_mi(t_msj) == dig_bek,
                         gift_baski_sayimi=G.baski_mi(t, {"4595350971"}), gift_dogru=G.baski_mi(t_msj, {"4595350971"}) == (not dig_bek),
                         pod_sku=bool(P.parse_sku(sku)), kupa=kupa_coz(sku), uretim_boyu_var=bk in BS.OLCU))
    with open(out / "SKU_KURU.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    alanlar = ("cozucu", "router", "router_mesajli", "tur_dogru", "gift_baski_sayimi", "gift_dogru", "pod_sku", "kupa", "sku_32_asar",
               "uretim_boyu_var")
    grup = defaultdict(lambda: defaultdict(set))
    for r in rows:
        k = (r["tur"], r["format"], "5x7" if r["boy"] == "5x7" else ("diger 13 boy" if not r["tur"].startswith("eski (") else r["boy"]))
        for alan in alanlar:
            grup[k][alan].add(str(r[alan]).split(" (")[0] if alan.startswith("router") else str(r[alan]))
    hata = [r for r in rows if r["cozucu"] != "TANIR" or not r["tur_dogru"] or not r["gift_dogru"] or r["kupa"] != "TANIMAZ"
            or (r["tur"] == "yeni (kisa kod)" and r["sku_32_asar"])]
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# 1st Anniversary SKU kuru sinama (ag yok)\n\nSKU {len(rows)} (ornek ciftler {', '.join(c for c, _ in ORNEK)}; 5 stil). "
                f"Makbuz bicimi gercek (formatted_name + Personalization); mesajli satir: Print'te 'digital', Digital'de 'print' gecen mesaj.\n\n"
                "| SKU | format | boy | by_sku.coz | order_router | mesajli order_router | tur dogru (mesaj dahil) | gift baski sayimi "
                "| gift dogru (mesaj dahil) | pod_sku | kupa sku_coz | SKU > 32 | uretim boyu (by_siparis.OLCU) |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for (tur, fmt, boy), v in sorted(grup.items()):
            f.write(f"| {tur} | {fmt} | {boy} | " + " | ".join("/".join(sorted(v[x])) for x in alanlar) + " |\n")
        f.write(f"\nYeni kisa kod SKU > 32: {sum(r['sku_32_asar'] for r in rows if r['tur'] == 'yeni (kisa kod)')} "
                f"(en uzun {max(r['sku_uzunluk'] for r in rows if r['tur'] == 'yeni (kisa kod)')}). Uretim boyu (by_siparis.OLCU): "
                f"{sorted(BS.OLCU)}.\nKAPI: {'PASS' if not hata else 'FAIL ' + str(len(hata))} (cozucu TANIR, tur ve gift mesajdan bagimsiz, "
                f"kupa TANIMAZ, yeni SKU <= 32).\n")
    print(open(out / "OZET.md", encoding="utf-8").read())
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main())
