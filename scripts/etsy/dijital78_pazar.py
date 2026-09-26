#!/usr/bin/env python3
"""
DIJITAL 78 - PAZAR FIYAT VERISI (Etsy SALT OKUR, yazma yok).

Etsy v3 `GET /listings/active` (keywords, limit=100, sayfali) ile aramalar
kosulur, YALNIZ dijital ilanlar (listing_type download/both) alinir, kendi
magazamiz haric tutulur, tekrarlar ayiklanir. Tahmin yok: yalnizca API'den
OLCULEN alanlar kullanilir.

Fiyatlar USD'ye cevrilir; kur canli alinamazsa analiz YALNIZ USD ilanlarla
yapilir ve bu durum raporda acikca yazilir.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

ARAMALAR = [
    "zodiac couple print", "zodiac compatibility print", "zodiac couple wall art printable",
    "astrology couple print digital", "zodiac sign printable wall art",
    "aries and leo zodiac print", "cancer and scorpio zodiac print",
    "gemini and libra zodiac print", "taurus and virgo zodiac print",
    "pisces and sagittarius zodiac print",
]
SET_RE = re.compile(r"\bset\b|\bbundle\b|\bcolors?\b|\bcolours?\b|variation|\b\d\s*in\s*1\b", re.I)
BIZIM = "39729443"
SUTUN = ["listing_id", "shop_id", "shop_name", "baslik", "fiyat", "para_birimi", "fiyat_usd",
         "kur", "num_favorers", "is_personalizable", "listing_type", "set_bundle_colors",
         "arama", "url"]
# Etsy ucretleri (Mo, 20 Eyl 2026): islem %6.5, odeme %6.5 + 14 TRY, duzenleyici %1.67,
# doviz %2.5, ilan 0.20 USD
ORAN_TOPLAM = 0.065 + 0.065 + 0.0167 + 0.025
ILAN_UCRETI = 0.20
SABIT_TRY = 14.0


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def kurlar():
    """Canli kur; alinamazsa None (o zaman yalniz USD ilanlar analiz edilir)."""
    for url in ("https://open.er-api.com/v6/latest/USD",
                "https://api.frankfurter.app/latest?from=USD"):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            k = d.get("rates") or d.get("conversion_rates")
            if k:
                return {"kaynak": url, "tarih": d.get("time_last_update_utc") or d.get("date"),
                        "rates": k}
        except Exception as ex:                              # noqa: BLE001
            print(f"   kur alinamadi ({url}): {str(ex)[:70]}", flush=True)
    return None


def yuzdelik(veri, p):
    if not veri:
        return None
    s = sorted(veri)
    k = (len(s) - 1) * p
    alt, ust = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[alt] + (s[ust] - s[alt]) * (k - alt), 2)


def dagilim(veri):
    return {"n": len(veri), "min": round(min(veri), 2) if veri else None,
            "p25": yuzdelik(veri, 0.25), "medyan": yuzdelik(veri, 0.5),
            "p75": yuzdelik(veri, 0.75), "max": round(max(veri), 2) if veri else None,
            "ortalama": round(statistics.mean(veri), 2) if veri else None}


def yuzdelik_konum(veri, deger):
    if not veri:
        return None
    return round(100.0 * sum(1 for x in veri if x <= deger) / len(veri), 1)


def net(fiyat, try_usd):
    kesinti = fiyat * ORAN_TOPLAM + ILAN_UCRETI + (SABIT_TRY * try_usd if try_usd else 0)
    return round(fiyat - kesinti, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--sayfa", type=int, default=2, help="arama basina sayfa (limit=100)")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    kur = kurlar()
    if kur:
        print(f"kur kaynagi: {kur['kaynak']} ({kur['tarih']})", flush=True)
    else:
        print("::warning::kur alinamadi - analiz YALNIZ USD ilanlarla yapilacak", flush=True)

    ilanlar, son = {}, time.time()
    for i, arama in enumerate(ARAMALAR, 1):
        for sayfa in range(a.sayfa):
            if api.calls >= a.max_calls:
                print(f"BUTCE: {api.calls} cagri, arama {i}/{len(ARAMALAR)} sonrasi durduruldu",
                      flush=True)
                break
            r = api.get("/listings/active", params={"keywords": arama, "limit": 100,
                                                    "offset": sayfa * 100}) or {}
            sonuc = r.get("results") or []
            for x in sonuc:
                lid = str(x.get("listing_id"))
                tip = (x.get("listing_type") or "").lower()
                if tip not in ("download", "both"):
                    continue
                if str(x.get("shop_id")) == BIZIM:
                    continue
                if lid in ilanlar:
                    continue
                p = x.get("price") or {}
                tutar = (p.get("amount") or 0) / (p.get("divisor") or 100)
                birim = p.get("currency_code") or ""
                oran = None
                if birim == "USD":
                    oran = 1.0
                elif kur and birim in kur["rates"] and kur["rates"][birim]:
                    oran = 1.0 / float(kur["rates"][birim])
                ilanlar[lid] = {
                    "listing_id": lid, "shop_id": x.get("shop_id"),
                    "shop_name": (x.get("shop") or {}).get("shop_name", ""),
                    "baslik": (x.get("title") or "").replace("\n", " ")[:160],
                    "fiyat": round(tutar, 2), "para_birimi": birim,
                    "fiyat_usd": round(tutar * oran, 2) if oran else "",
                    "kur": round(oran, 6) if oran else "",
                    "num_favorers": x.get("num_favorers"),
                    "is_personalizable": x.get("is_personalizable"),
                    "listing_type": tip,
                    "set_bundle_colors": bool(SET_RE.search(x.get("title") or "")),
                    "arama": arama, "url": x.get("url", ""),
                }
            if len(sonuc) < 100:
                break
        if time.time() - son >= 60 or i == len(ARAMALAR):
            print(f"   ETA arama {i}/{len(ARAMALAR)} | benzersiz dijital ilan {len(ilanlar)} | "
                  f"Etsy cagrisi {api.calls}/{a.max_calls} | gecen {time.time()-t0:.0f}s",
                  flush=True)
            son = time.time()
        if api.calls >= a.max_calls:
            break

    satirlar = sorted(ilanlar.values(), key=lambda x: -(x["num_favorers"] or 0))
    with open(out / "PAZAR_FIYAT.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)

    fiyatli = [x for x in satirlar if x["fiyat_usd"] != ""]
    hepsi = [x["fiyat_usd"] for x in fiyatli]
    kisiselsiz = [x["fiyat_usd"] for x in fiyatli if not x["is_personalizable"]]
    setli = [x["fiyat_usd"] for x in fiyatli if x["set_bundle_colors"]]
    en_sevilen = sorted(fiyatli, key=lambda x: -(x["num_favorers"] or 0))[:20]
    para = {}
    for x in satirlar:
        para[x["para_birimi"]] = para.get(x["para_birimi"], 0) + 1
    try_usd = (1.0 / float(kur["rates"]["TRY"])) if kur and kur["rates"].get("TRY") else None

    def yuvarla99(v):
        return float(f"{int(v)}.99") if v and v >= 1 else v

    secenekler = []
    for etiket, taban in (("MEDYAN", yuzdelik(hepsi, 0.5)), ("P75", yuzdelik(hepsi, 0.75)),
                          ("P90", yuzdelik(hepsi, 0.90))):
        if taban is None:
            continue
        liste = yuvarla99(taban)
        indirimli = round(liste * 0.6, 2)                    # mevcut 9.99 -> 5.99 orani
        secenekler.append({
            "etiket": etiket, "liste_fiyati": liste, "indirimli": indirimli,
            "liste_yuzdelik": yuzdelik_konum(hepsi, liste),
            "indirimli_yuzdelik": yuzdelik_konum(hepsi, indirimli),
            "net_liste": net(liste, try_usd), "net_indirimli": net(indirimli, try_usd),
        })

    md = [f"# PAZAR FIYAT ANALIZI ({simdi()} UTC)", "",
          f"Kaynak: Etsy v3 `GET /listings/active`, {len(ARAMALAR)} arama, "
          f"{api.calls} cagri (salt okuma). Yalniz dijital ilanlar "
          f"(listing_type download/both), kendi magazamiz ({BIZIM}) haric, tekrarlar ayiklandi.",
          f"Benzersiz dijital ilan: **{len(satirlar)}**. Para birimi dagilimi: {para}.", ""]
    if kur:
        md.append(f"Kur: {kur['kaynak']} ({kur['tarih']}); USD disi fiyatlar bu kurla cevrildi.")
    else:
        md.append("**Kur alinamadi**: analiz yalniz USD fiyatli ilanlarla yapildi; "
                  "USD disi ilanlar CSV'de duruyor ama dagilima girmedi.")
    md += ["", "> Etsy `listings/active` tek bir `price` alani doner; **liste fiyati ile "
           "indirimli (satis) fiyati ayirt edilemiyor**. Asagidaki dagilim ilanda gorunen "
           "fiyattir.", "",
           "## Fiyat dagilimi (USD)", "",
           "| kume | n | min | %25 | medyan | %75 | max | ortalama |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for ad, veri in (("Tum dijital ilanlar", hepsi), ("Kisisellestirmesiz", kisiselsiz),
                     ("Basligi set/bundle/colors iceren", setli),
                     ("En cok favorilenen 20", [x["fiyat_usd"] for x in en_sevilen])):
        dg = dagilim(veri)
        md.append(f"| {ad} | {dg['n']} | {dg['min']} | {dg['p25']} | {dg['medyan']} | "
                  f"{dg['p75']} | {dg['max']} | {dg['ortalama']} |")
    md += ["", "## En cok favorilenen 20 ilan", "",
           "| favori | fiyat USD | kisisellestirme | set/renk | baslik |",
           "|---:|---:|---|---|---|"]
    for x in en_sevilen:
        md.append(f"| {x['num_favorers']} | {x['fiyat_usd']} | "
                  f"{'evet' if x['is_personalizable'] else 'hayir'} | "
                  f"{'evet' if x['set_bundle_colors'] else 'hayir'} | {x['baslik'][:70]} |")
    md += ["", "## Bizim durum ve 5 renk paketi secenekleri", "",
           "- Mevcut: tek renk liste 9.99 (indirimli 5.99); wallpaper 5'li 6.65 (3.99).",
           f"- Ucretler: islem %6.5 + odeme %6.5 ve 14 TRY + duzenleyici %1.67 + doviz %2.5 "
           f"+ ilan 0.20 USD (toplam oran %{ORAN_TOPLAM*100:.2f}).",
           (f"- 14 TRY = {14*try_usd:.2f} USD (kur {try_usd:.6f})." if try_usd else
            "- 14 TRY'nin USD karsiligi kur alinamadigi icin hesaba KATILMADI (net degerler "
            "bu kadar yuksek gorunuyor)."), "",
           "| secenek | liste | dagilimdaki yuzdelik | indirimli (x0.6) | yuzdelik | "
           "net (liste) | net (indirimli) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for s2 in secenekler:
        md.append(f"| {s2['etiket']} | {s2['liste_fiyati']} | %{s2['liste_yuzdelik']} | "
                  f"{s2['indirimli']} | %{s2['indirimli_yuzdelik']} | {s2['net_liste']} | "
                  f"{s2['net_indirimli']} |")
    mevcut = [("tek renk liste 9.99", 9.99), ("tek renk indirimli 5.99", 5.99)]
    md += ["", "### Mevcut fiyatlarimizin dagilimdaki yeri", ""]
    for ad, v in mevcut:
        md.append(f"- {ad}: %{yuzdelik_konum(hepsi, v)} yuzdelik, net {net(v, try_usd)} USD")
    md += ["", f"- Sure: {time.time()-t0:.0f}s | CSV: `PAZAR_FIYAT.csv` ({len(satirlar)} satir)"]
    (out / "PAZAR_FIYAT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BITTI | {len(satirlar)} ilan | {api.calls} Etsy cagrisi | "
          f"medyan {yuzdelik(hepsi, 0.5)} USD | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
