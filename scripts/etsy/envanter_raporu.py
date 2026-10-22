#!/usr/bin/env python3
"""
SALT OKUR ENVANTER RAPORU (Mo 15 Eyl 2026). Etsy'ye yazma yok, reklam ayarina dokunma yok.

1) Etsy Open API v3 semasinda (oas.json) reklam/istatistik ucu var mi: yol adlari ve
   sema metni taranir, sonuc MD'ye yazilir.
2) Tum aktif ilanlar: listing_id, baslik, 13 etiket, fiyat, edisyon, cift, urun tipi
   (dijital poster / duvar kagidi / POD), bolum, olusturulma, views, num_favorers ve
   (transactions_r kapsami varsa) makbuzlardan satis adedi.
3) Tip ve bolum bazinda ozet: ilan sayisi, ortalama fiyat, toplam views, toplam favori.
Raporda anahtar/token/kimlik yok; magaza no yalniz API yolunda kullanilir.

Kullanim: envanter_raporu.py --oas oas.json --out OUT [--max-calls 400] [--receipt-pages 8]
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
SUTUN = (["listing_id", "baslik", "urun_tipi", "cift", "edisyon", "bolum", "fiyat", "para",
          "olusturma", "views", "num_favorers", "satis_adedi", "quantity", "listing_type",
          "etiket_sayisi"] + [f"tag{i}" for i in range(1, 14)] + ["url"])


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------ 1) OAS taramasi
def oas_tara(path):
    if not Path(path).exists():
        return {"hata": "oas.json yok"}
    d = json.load(open(path, encoding="utf-8"))
    yollar = list(d.get("paths") or {})
    rx = re.compile(r"/ads?\b|advert|promot|campaign|search[_-]?terms?|keyword|/stats?\b|analytic|impression",
                    re.I)
    yol_hit = [p for p in yollar if rx.search(p)]
    metin = json.dumps(d)
    kelimeler = {}
    for kw in ("advertis", "Etsy Ads", "offsite", "promoted", "search term", "impression",
               "click", "spend", "budget"):
        kelimeler[kw] = len(re.findall(re.escape(kw), metin, re.I))
    # sema alanlarinda reklam gecen yerler (hangi semada)
    sema_hit = []
    for ad, sc in (d.get("components", {}).get("schemas") or {}).items():
        for alan, tanim in (sc.get("properties") or {}).items():
            s = f"{alan} {tanim.get('description', '')}"
            if re.search(r"advertis|Etsy Ads|offsite|promot", s, re.I):
                sema_hit.append(f"{ad}.{alan}")
    sl = sorted((d["components"]["schemas"].get("ShopListing") or {}).get("properties") or {})
    shop = sorted((d["components"]["schemas"].get("Shop") or {}).get("properties") or {})
    return {"yol_sayisi": len(yollar), "reklam_yollari": yol_hit, "kelime_sayilari": kelimeler,
            "sema_alanlari": sema_hit, "ShopListing_alanlari": sl,
            "Shop_satis_alanlari": [k for k in shop if re.search(r"sale|sold|transaction", k)],
            "oas_surumu": (d.get("info") or {}).get("version")}


# ------------------------------------------------------------ 2) ilanlar
def burclar(baslik):
    bulunan = []
    for m in re.finditer(r"\b(" + "|".join(BURCLAR) + r")\b", baslik, re.I):
        bulunan.append(m.group(1).capitalize())
        if len(bulunan) == 2:
            break
    return bulunan


def siniflandir(L):
    t = (L.get("title") or "")
    tip = L.get("listing_type") or ""
    if tip == "physical":
        return "POD baski"
    if re.search(r"wallpaper", t, re.I):
        return "Duvar kagidi"
    if tip == "download":
        return "Dijital poster"
    return f"Diger ({tip})"


def edisyon(baslik, tipi):
    for e in EDISYONLAR:
        if re.search(re.escape(e), baslik, re.I):
            return e
    if tipi == "Duvar kagidi":
        return "4 renk (tek ilan)"
    if tipi == "POD baski":
        return "5 renk (varyasyon)"
    return ""


def fiyat(L):
    p = L.get("price") or {}
    try:
        return round(p["amount"] / p["divisor"], 2), p.get("currency_code", "")
    except (KeyError, TypeError, ZeroDivisionError):
        return None, ""


def tarih(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def aktif_ilanlar(api, shop, max_pages=12):
    out, offset = [], 0
    for _ in range(max_pages):
        r = api.get(f"/shops/{shop}/listings", params={"state": "active", "limit": 100,
                                                        "offset": offset}) or {}
        res = r.get("results") or []
        out += res
        if len(res) < 100:
            break
        offset += 100
    return out


def bolumler(api, shop):
    r = api.get(f"/shops/{shop}/sections", ok404=True) or {}
    return {s.get("shop_section_id"): s.get("title") for s in (r.get("results") or [])}


def satislar(api, shop, max_pages, cagri_siniri):
    """Makbuzlardaki islemlerden ilan basina satilan adet. Kapsam yoksa None."""
    say, makbuz, sayfa_ok = defaultdict(int), 0, 0
    offset = 0
    for _ in range(max_pages):
        if api.calls >= cagri_siniri:
            return say, makbuz, f"cagri siniri ({cagri_siniri}) - {sayfa_ok} sayfa okundu"
        try:
            r = api.get(f"/shops/{shop}/receipts", params={"limit": 100, "offset": offset}) or {}
        except SystemExit as ex:
            return None, 0, f"makbuz okunamadi: {str(ex)[:120]}"
        res = r.get("results") or []
        sayfa_ok += 1
        for rc in res:
            makbuz += 1
            for tr in rc.get("transactions") or []:
                lid = str(tr.get("listing_id") or "")
                if lid:
                    say[lid] += int(tr.get("quantity") or 1)
        if len(res) < 100:
            return say, makbuz, "tam"
        offset += 100
    return say, makbuz, f"{max_pages} sayfa siniri"


# ------------------------------------------------------------ 3) ozet
def ozet_tablo(satirlar, anahtar):
    grup = defaultdict(list)
    for s in satirlar:
        grup[s[anahtar] or "(bos)"].append(s)
    lines = [f"| {anahtar} | ilan | ort. fiyat | toplam views | toplam favori | satis |",
             "|---|---:|---:|---:|---:|---:|"]
    for k in sorted(grup, key=lambda x: -len(grup[x])):
        g = grup[k]
        fiy = [s["fiyat"] for s in g if isinstance(s["fiyat"], (int, float))]
        sat = [s["satis_adedi"] for s in g if isinstance(s["satis_adedi"], int)]
        lines.append(f"| {k} | {len(g)} | {statistics.mean(fiy):.2f} | "
                     f"{sum(s['views'] or 0 for s in g)} | {sum(s['num_favorers'] or 0 for s in g)} | "
                     f"{sum(sat) if sat else '-'} |" if fiy else
                     f"| {k} | {len(g)} | - | {sum(s['views'] or 0 for s in g)} | "
                     f"{sum(s['num_favorers'] or 0 for s in g)} | {sum(sat) if sat else '-'} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oas", default="_work/oas.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-calls", type=int, default=400)
    ap.add_argument("--receipt-pages", type=int, default=8)
    ap.add_argument("--ads-drive", default="", help="Drive'da bulunan reklam CSV listesi (metin dosyasi)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    log("1) OAS taramasi")
    oas = oas_tara(a.oas)
    log(f"   yol {oas.get('yol_sayisi')} | reklam benzeri yol: {oas.get('reklam_yollari') or 'YOK'}")

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    mask(shop)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    t0 = time.time()

    log("2) Aktif ilanlar")
    ilanlar = aktif_ilanlar(api, shop)
    log(f"   {len(ilanlar)} aktif ilan, {api.calls} cagri, kota {api.remaining}")
    bol = bolumler(api, shop)
    log(f"   {len(bol)} bolum")
    shop_bilgi = api.get(f"/shops/{shop}", ok404=True) or {}
    magaza_satis = shop_bilgi.get("transaction_sold_count")
    sat, makbuz, sat_not = satislar(api, shop, a.receipt_pages, a.max_calls - 5)
    log(f"   makbuz {makbuz} | satis notu: {sat_not} | cagri {api.calls}")

    satirlar = []
    for L in ilanlar:
        tipi = siniflandir(L)
        b = burclar(L.get("title") or "")
        f, para = fiyat(L)
        tags = list(L.get("tags") or [])
        lid = str(L.get("listing_id"))
        s = {
            "listing_id": lid, "baslik": L.get("title") or "", "urun_tipi": tipi,
            "cift": "_".join(sorted(x.upper() for x in b)) if len(b) == 2 else "",
            "edisyon": edisyon(L.get("title") or "", tipi),
            "bolum": bol.get(L.get("shop_section_id")) or (str(L.get("shop_section_id")) if L.get("shop_section_id") else ""),
            "fiyat": f, "para": para, "olusturma": tarih(L.get("original_creation_timestamp")),
            "views": L.get("views"), "num_favorers": L.get("num_favorers"),
            "satis_adedi": (sat.get(lid, 0) if sat is not None else ""),
            "quantity": L.get("quantity"), "listing_type": L.get("listing_type"),
            "etiket_sayisi": len(tags), "url": L.get("url") or "",
        }
        for i in range(13):
            s[f"tag{i+1}"] = tags[i] if i < len(tags) else ""
        satirlar.append(s)
    satirlar.sort(key=lambda x: (x["urun_tipi"], x["cift"], x["edisyon"]))

    csv_ad = f"ETSY_INVENTORY_{stamp}.csv"
    with open(out / csv_ad, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN)
        w.writeheader()
        for s in satirlar:
            w.writerow(s)

    log("3) Ozet")
    top_v = sorted(satirlar, key=lambda x: -(x["views"] or 0))[:10]
    top_f = sorted(satirlar, key=lambda x: -(x["num_favorers"] or 0))[:10]
    az13 = [s for s in satirlar if s["etiket_sayisi"] != 13]
    ciftsiz = [s for s in satirlar if not s["cift"]]
    ads_drive = Path(a.ads_drive).read_text(encoding="utf-8").strip() if a.ads_drive and Path(a.ads_drive).exists() else ""

    md = [f"# Etsy envanter raporu ({simdi()} UTC)", "",
          "Salt okur koşu. Etsy'ye yazma yok, reklam ayarlarına dokunulmadı. Raporda anahtar/token/kimlik yok.", "",
          "## 1. Etsy Ads verisi API'de var mı?", ""]
    if oas.get("hata"):
        md.append(f"OAS taranamadı: {oas['hata']}")
    else:
        md += [f"- OAS sürümü: {oas['oas_surumu']}, toplam yol: {oas['yol_sayisi']}",
               f"- Reklam/istatistik benzeri yol (regex `ads|advert|promot|campaign|search_term|keyword|stats|analytic|impression`): "
               f"**{', '.join(oas['reklam_yollari']) if oas['reklam_yollari'] else 'YOK'}**",
               f"- Şemada anahtar kelime sayıları: {oas['kelime_sayilari']}",
               f"- Reklamla ilgili şema alanları: {', '.join(oas['sema_alanlari']) if oas['sema_alanlari'] else 'yok'}",
               f"- Shop şemasında satış alanları: {oas['Shop_satis_alanlari']}",
               f"- ShopListing alanları: {', '.join(oas['ShopListing_alanlari'])}", ""]
        if not oas["reklam_yollari"]:
            md.append("**SONUÇ: API'de yok, yalnız Shop Manager arayüzünde.** Etsy Open API v3'te reklam harcaması, "
                      "gösterim, tıklama veya arama terimi döndüren bir uç nokta bulunmuyor; Etsy Ads verisi "
                      "Shop Manager > Marketing > Etsy Ads ekranından (ve oradaki CSV dışa aktarımından) alınabilir.")
        else:
            md.append("Bulunan yollar yukarıda; her biri elle doğrulanmalı.")
    md += ["", "## 2. Drive'da Etsy Ads CSV'si", "",
           ads_drive or "Drive'da `etsy_ads_stats_*` / `*ads*` kalıbına uyan CSV bulunamadı (MCP başlık araması + rclone ad taraması).", "",
           "## 3. Aktif ilan dışa aktarımı", "",
           f"- Aktif ilan: **{len(satirlar)}** → `{csv_ad}` (satır başına: id, başlık, tip, çift, edisyon, bölüm, fiyat, oluşturma, views, favori, satış, 13 etiket, url)",
           f"- Mağaza toplam satış (Shop.transaction_sold_count): **{magaza_satis if magaza_satis is not None else 'okunamadı'}**",
           f"- İlan başına satış: {'makbuzlardan sayıldı (' + str(makbuz) + ' makbuz, ' + sat_not + ')' if sat is not None else 'API kapsamı yok / okunamadı (' + sat_not + ')'}",
           f"- 13 etiketi olmayan ilan: {len(az13)}" + (f" → {', '.join(s['listing_id'] + ' (' + str(s['etiket_sayisi']) + ')' for s in az13[:20])}" if az13 else ""),
           f"- Başlıktan çift çıkarılamayan ilan: {len(ciftsiz)}" + (f" → {', '.join(s['listing_id'] for s in ciftsiz[:20])}" if ciftsiz else ""),
           "", "## 4. Ürün tipi bazında özet", "", ozet_tablo(satirlar, "urun_tipi"),
           "", "## 5. Bölüm bazında özet", "", ozet_tablo(satirlar, "bolum"),
           "", "## 6. Edisyon bazında özet (dijital poster)", "",
           ozet_tablo([s for s in satirlar if s["urun_tipi"] == "Dijital poster"], "edisyon"),
           "", "## 7. En çok görüntülenen 10", "", "| listing | tip | çift | edisyon | views | favori |", "|---|---|---|---|---:|---:|"]
    md += [f"| {s['listing_id']} | {s['urun_tipi']} | {s['cift']} | {s['edisyon']} | {s['views']} | {s['num_favorers']} |" for s in top_v]
    md += ["", "## 8. En çok favorilenen 10", "", "| listing | tip | çift | edisyon | views | favori |", "|---|---|---|---|---:|---:|"]
    md += [f"| {s['listing_id']} | {s['urun_tipi']} | {s['cift']} | {s['edisyon']} | {s['views']} | {s['num_favorers']} |" for s in top_f]
    md += ["", f"API çağrısı: {api.calls} (sınır {a.max_calls}) | kota kalan: {api.remaining} | süre {round((time.time()-t0)/60,1)} dk"]
    md_ad = f"ETSY_INVENTORY_SUMMARY_{stamp}.md"
    (out / md_ad).write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"OZET: {json.dumps({'ilan': len(satirlar), 'tip': {t: sum(1 for s in satirlar if s['urun_tipi']==t) for t in sorted({s['urun_tipi'] for s in satirlar})}, 'cagri': api.calls, 'kota': api.remaining, 'reklam_yolu': oas.get('reklam_yollari')}, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
