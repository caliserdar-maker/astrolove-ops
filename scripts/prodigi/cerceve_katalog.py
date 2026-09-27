#!/usr/bin/env python3
"""Prodigi cerceveli + baski katalog/teklif taramasi (SALT OKUMA) - Serdar, 27 Eyl 2026.

Yalniz GET /products/{sku} ve POST /quotes (siparis OLUSTURMAZ). Etsy cagrisi yok.
Boy adaylari: 8x10 11x14 12x16 12x18 16x20 18x24 24x36 A4 A3 (boy arastirmasi icin genis).
Urunler: GLOBAL-HPR-<boy> (Hahnemuhle Photo Rag baski), GLOBAL-CFP-<boy> (classic frame),
GLOBAL-CFPM-<boy> (classic frame + mount). Cerceve renkleri black / white / natural.
Hedef ulke US, kargo Standard (Budget ve Express de yazilir). Para birimi USD.
Cikti (out/): CERCEVE_KATALOG.csv, CERCEVE_KATALOG.md, urun/<sku>.json (urun detayi: nitelikler, boyutlar, print area).
Kar hesabi: Etsy kesintisi KDV dahil 0.698 + 0.2062 x fiyat; paket eki 5.00 (kartpostal + sticker).
Onerilen fiyat: net hedefe (baski 10, cerceveli 20) ulasan en kucuk x.99.
"""
import csv
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_pilot_quote import Api, leak_check, load_key, log  # noqa: E402

BOYLAR = ["8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2", "18x24", "20x30", "A1", "24x30", "24x32", "24x36", "30x40"]
RENKLER = ["black"]  # renkler ayni fiyat (27 Eyl olcumu: black=white=natural)
EK = 5.00
HEDEF = {"HPR": 10.0, "CFP": 10.0, "CFPM": 10.0, "BOX": 10.0, "BOXM": 10.0}  # Serdar 27 Eyl: cerceveli net 10
import os  # noqa: E402
# Ortam ile daraltma/genisletme (salt okuma arastirmalari icin): CK_BOYLAR, CK_RENKLER, CK_URUNLER, CK_ETIKET
if os.environ.get("CK_BOYLAR"):
    BOYLAR = os.environ["CK_BOYLAR"].split(",")
if os.environ.get("CK_RENKLER"):
    RENKLER = [r.replace("_", " ") for r in os.environ["CK_RENKLER"].split(",")]
URUNLER = os.environ.get("CK_URUNLER", "HPR,CFP").split(",")
ETIKET = os.environ.get("CK_ETIKET", "")
ALANLAR = ["urun", "boy", "renk", "sku", "yontem", "urun_maliyet", "kargo", "vergi", "toplam", "lab",
           "teslim_gun", "maliyet_ekli", "onerilen_fiyat", "net", "not"]


def kesinti(f):
    return 0.698 + 0.2062 * f


def oneri(maliyet, hedef):
    # en kucuk N.99 ki  f - kesinti(f) - maliyet >= hedef
    f = (hedef + maliyet + 0.698) / (1 - 0.2062)
    x = math.ceil(f - 0.99) + 0.99
    return round(x, 2)


def para(c):
    try:
        return round(float((c or {}).get("amount")), 2)
    except (TypeError, ValueError):
        return None


def teklif_satirlari(api, urun, boy, sku, renk):
    attrs = {"color": renk} if renk else {}
    q, err = api.quote(sku, attrs)
    if not q:
        return [dict(urun=urun, boy=boy, renk=renk, sku=sku, not_=err)]
    rows = []
    for qu in q.get("quotes") or []:
        cs = qu.get("costSummary") or {}
        labs, gun = [], []
        for sh in qu.get("shipments") or []:
            fl = sh.get("fulfillmentLocation") or {}
            labs.append(f"{fl.get('countryCode', '')}/{fl.get('labCode', '')}")
        rows.append(dict(urun=urun, boy=boy, renk=renk, sku=sku, yontem=qu.get("shipmentMethod"),
                         urun_maliyet=para(cs.get("items")), kargo=para(cs.get("shipping")),
                         vergi=para(cs.get("totalTax")), toplam=para(cs.get("totalCost")),
                         lab=" ".join(dict.fromkeys(labs)), teslim_gun="", not_=""))
    return rows


def sku_bul(api, on, boy, cache):
    """Boy yazimi: 8x10 / 8X10 / A4 dener; ilk gecerli urun."""
    for aday in dict.fromkeys([f"GLOBAL-{on}-{boy}", f"GLOBAL-{on}-{boy.upper()}", f"GLOBAL-{on}-{boy.lower()}"]):
        if aday in cache:
            return aday, cache[aday]
        p, err = api.product(aday)
        if p:
            cache[aday] = p
            return aday, p
    return None, None


def main():
    out = Path(sys.argv[sys.argv.index("--out-dir") + 1] if "--out-dir" in sys.argv else "out")
    (out / "urun").mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    cache, isler, eksik = {}, [], []
    for on in URUNLER:
        for boy in BOYLAR:
            sku, p = sku_bul(api, on, boy, cache)
            if not sku:
                eksik.append(f"{on}-{boy}")
                continue
            (out / "urun" / f"{sku}.json").write_text(json.dumps(p, indent=1))
            for renk in (RENKLER if on != "HPR" else [""]):
                isler.append((on, boy, sku, renk))
    log(f"urun bulundu {len(cache)}, eksik {len(eksik)}: {' '.join(eksik)}; teklif {len(isler)}")
    with ThreadPoolExecutor(4) as ex:
        sonuc = list(ex.map(lambda a: teklif_satirlari(api, *a), isler))
    rows = []
    for grup in sonuc:
        for r in grup:
            r["not"] = r.pop("not_", "")
            if r.get("urun_maliyet") is not None and r.get("kargo") is not None:
                m = round(r["urun_maliyet"] + r["kargo"] + (r.get("vergi") or 0) + EK, 2)
                f = oneri(m, HEDEF.get(r["urun"], 10.0))
                r.update(maliyet_ekli=m, onerilen_fiyat=f, net=round(f - kesinti(f) - m, 2))
            rows.append({k: r.get(k, "") for k in ALANLAR})
    with open(out / f"CERCEVE_KATALOG{ETIKET}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALANLAR); w.writeheader(); w.writerows(rows)
    # Ozet: Standard, US
    md = ["# Prodigi katalog (salt okuma) - US, Standard", "",
          f"Eksik SKU: {', '.join(eksik) or 'yok'}", "",
          "Nitelikler (urun detayindan):"]
    for sku, p in sorted(cache.items()):
        at = p.get("attributes") or {}
        md.append(f"- {sku}: " + "; ".join(f"{k}={','.join(map(str, v))}" for k, v in at.items())
                  + f" | {p.get('description', '')[:90]}")
    md += ["", "| urun | boy | renk | urun $ | kargo $ | vergi $ | lab | maliyet+ek $ | oneri $ | net $ |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if (r["yontem"] or "").lower() == "standard":
            md.append(f"| {r['urun']} | {r['boy']} | {r['renk']} | {r['urun_maliyet']} | {r['kargo']} | {r['vergi']} | "
                      f"{r['lab']} | {r['maliyet_ekli']} | {r['onerilen_fiyat']} | {r['net']} |")
    hatali = [r for r in rows if r["not"]]
    if hatali:
        md += ["", "Hatalar:"] + [f"- {r['urun']} {r['boy']} {r['renk']}: {r['not']}" for r in hatali]
    (out / f"CERCEVE_KATALOG{ETIKET}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    leak_check(out)
    log(f"satir {len(rows)}, hata {len(hatali)}")


if __name__ == "__main__":
    main()
