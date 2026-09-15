#!/usr/bin/env python3
"""GECE BATCH 2 - ONCELIK 5 + 6 + 7 (uretim, Etsy/Drive'a yazma YOK).

  ONCELIK 5  78 cift x 7 platform = 546 satirlik icerik veri seti (CSV + JSON).
             Icerik YAYINLANMAZ, PLANLANMAZ; yalniz veri uretilir.
  ONCELIK 6  Etsy Ads veri altyapisi: bos import sablonu, kolon sozlugu,
             KPI hesaplama betigi ve karar siniflari (veri UYDURULMAZ).
  ONCELIK 7  78 POD ilani icin panel-ready GPSR tablosu (panele giris YAPILMAZ).

Kullanim: assets_kit.py --catalog full_etsy_catalog.json --pod-state P.csv --out OUT
"""
import argparse
import csv
import json
import pathlib
import re
from collections import defaultdict
from datetime import datetime, timezone

PLATFORMLAR = [
    # ad, amac, format, oran, sure, yayin zamani, medya turu, metricool
    ("Etsy", "arama gorunurlugu ve donusum", "ilan galerisi + video", "4:5 / 1080x1350",
     "video 10-20 sn", "surekli yayinda", "hero + oda sahnesi + sembol karti", "hayir"),
    ("Pinterest", "uzun omurlu kesif trafigi", "statik Pin + video Pin", "2:3 / 1000x1500",
     "video 6-15 sn", "hafta ici 20:00-23:00 yerel", "hero, sembol karti, oda sahnesi", "evet"),
    ("Instagram", "marka estetigi ve topluluk", "Reels + karusel", "9:16 Reels / 4:5 karusel",
     "Reels 7-15 sn", "sali-persembe 19:00-21:00", "surec videosu + 5 edisyon karusel", "evet"),
    ("Facebook", "hediye odakli kitle", "tek gorsel + karusel", "1:1 / 4:5",
     "video 15-30 sn", "cuma-pazar 18:00-21:00", "oda sahnesi + edisyon karuseli", "evet"),
    ("TikTok", "kesif ve surec merakti", "dikey video", "9:16 / 1080x1920",
     "7-20 sn", "her gun 20:00-23:00", "sembol birlesim animasyonu", "evet"),
    ("YouTube", "arama arsivi", "Shorts", "9:16 / 1080x1920",
     "15-45 sn", "haftada 2, aksam", "surec videosu + cerceveleme ipucu", "evet"),
    ("Google Business", "marka guveni", "isletme gonderisi", "4:3 / 1200x900",
     "gorsel", "ayda 2-4", "hero gorsel", "hayir"),
]
ORTAK_TAG = ["zodiaccouple", "zodiacart", "astrologygift", "minimalwallart", "couplegift",
             "celestialdecor", "giclee"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def hook(a, b, platform):
    if a == b:
        return {
            "Etsy": f"Two {a} hearts, one symbol.",
            "Pinterest": f"{a} and {a}: one emblem for two of the same sign.",
            "Instagram": f"What happens when both of you are {a}?",
            "Facebook": f"For the couple who share the same sign.",
            "TikTok": f"Both {a}? This one is yours.",
            "YouTube": f"{a} and {a}: one symbol, two people.",
            "Google Business": f"{a} and {a} zodiac couple print.",
        }[platform]
    return {
        "Etsy": f"{a} and {b}, merged into one symbol.",
        "Pinterest": f"{a} and {b} as a single line-drawn emblem.",
        "Instagram": f"{a} plus {b}. One symbol, not two.",
        "Facebook": f"The {a} and {b} print for couples who share astrology.",
        "TikTok": f"{a} + {b} = one symbol. Watch it form.",
        "YouTube": f"How the {a} and {b} emblem is drawn.",
        "Google Business": f"{a} and {b} zodiac couple print.",
    }[platform]


def aciklama(a, b, platform, pod_url):
    ortak = (f"One original emblem that merges the {a} and {b} glyphs, drawn in-house. "
             "Five color editions, museum-quality cotton paper, made to order and shipped unframed.")
    if platform == "Etsy":
        return "Ilan aciklamasi SEO v2 sablonundan gelir (bu satir referanstir): " + ortak
    if platform == "Pinterest":
        return ortak + " Available as a giclee print or an instant download."
    if platform == "Instagram":
        return ortak + " Link in bio."
    if platform == "Facebook":
        return ortak + f" {pod_url}"
    if platform == "TikTok":
        return f"{a} + {b}, one symbol. Five editions. Link in bio."
    if platform == "YouTube":
        return (ortak + " Chapters: the glyphs, the merge, the paper, framing. "
                f"Print: {pod_url}")
    return ortak


def cta(platform):
    return {"Etsy": "Add to cart", "Pinterest": "Save this Pin",
            "Instagram": "Link in bio", "Facebook": "Shop on Etsy",
            "TikTok": "Link in bio", "YouTube": "Link in description",
            "Google Business": "Visit our Etsy shop"}[platform]


def etiketler(a, b, platform):
    ozel = [f"{a.lower()}{b.lower()}", f"{a.lower()}zodiac", f"{b.lower()}zodiac"]
    if platform == "Etsy":
        return " | ".join([f"{a.lower()} {b.lower()}", f"{a.lower()} zodiac art",
                           f"{b.lower()} zodiac art", "zodiac couple print"])
    if platform == "Google Business":
        return "(hashtag kullanilmaz)"
    n = {"Pinterest": 3, "Instagram": 10, "Facebook": 3, "TikTok": 5, "YouTube": 3}[platform]
    return " ".join("#" + t for t in (ozel + ORTAK_TAG)[:n])


def seo_kelime(a, b, platform):
    temel = [f"{a} {b} zodiac print", "zodiac couple art", "minimalist gold line art",
             "astrology wall art", "couple gift"]
    if platform in ("YouTube", "Pinterest"):
        temel += ["how to frame a giclee print", "zodiac couple gift idea"]
    return ", ".join(temel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="")
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    ciftler = []
    with open(a.pod_state, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("pair") or "") and (r.get("listing_id") or "").isdigit() \
                    and (r.get("stage") or "") == "verified":
                ciftler.append((r["pair"], r["listing_id"]))
    ciftler.sort()

    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8")) \
        if a.catalog and pathlib.Path(a.catalog).exists() else []
    pod_url = {}
    for L in katalog:
        if L.get("urun_ailesi") == "POD baski" and L.get("burc_cifti"):
            pod_url[L["burc_cifti"]] = L.get("url") or f"https://www.etsy.com/listing/{L['listing_id']}"

    # ------------------------------------------------ ONCELIK 5
    satirlar = []
    for pair, lid in ciftler:
        A, B = [x.capitalize() for x in pair.split("_")]
        url = pod_url.get(pair, f"https://www.etsy.com/listing/{lid}")
        for (plat, amac, fmt, oran, sure, zaman, medya, metricool) in PLATFORMLAR:
            satirlar.append({
                "cift": pair, "platform": plat, "icerik_amaci": amac, "icerik_formati": fmt,
                "baslik": (f"{A} and {B} Zodiac Couple Print" if plat != "TikTok"
                           else f"{A} + {B}, one symbol"),
                "aciklama": aciklama(A, B, plat, url),
                "hook": hook(A, B, plat), "cta": cta(plat),
                "hashtag_tag": etiketler(A, B, plat),
                "seo_anahtar_kelimeler": seo_kelime(A, B, plat),
                "onerilen_oran": oran, "onerilen_sure": sure, "onerilen_yayin_zamani": zaman,
                "kullanilacak_medya": medya, "metricool_aktarilabilir": metricool,
                "pod_listing_id": lid, "pod_url": url,
            })
    sut = list(satirlar[0])
    with open(out / "platform_content_dataset.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sut)
        w.writeheader()
        for x in satirlar:
            w.writerow(x)
    (out / "platform_content_dataset.json").write_text(
        json.dumps(satirlar, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------ ONCELIK 6
    ADS_KOLON = [
        ("date", "YYYY-MM-DD", "Etsy Ads gun bazli satir"),
        ("listing_id", "sayi", "ilan no"),
        ("listing_title", "metin", "ilan basligi"),
        ("impressions", "sayi", "gosterim"),
        ("clicks", "sayi", "tiklama"),
        ("spend", "ondalik", "harcama (magaza para birimi)"),
        ("orders", "sayi", "reklamdan gelen siparis"),
        ("revenue", "ondalik", "reklamdan gelen gelir"),
        ("currency", "metin", "USD vb."),
    ]
    with open(out / "etsy_ads_import_template.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([k for k, _, _ in ADS_KOLON])
    with open(out / "etsy_ads_column_dictionary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kolon", "tip", "aciklama"])
        for k, t, d in ADS_KOLON:
            w.writerow([k, t, d])

    # ------------------------------------------------ ONCELIK 7
    GPSR = {
        "uretici": "Prodigi Group plc (baski ve uretim ortagi)",
        "uretici_adres": "Prodigi Group plc, Vauxhall Industrial Estate, Ruabon, Wrexham, LL14 6HA, United Kingdom",
        "responsible_person": "Prodigi B.V., Jan van Riebeeckweg 15, 5928 LG Venlo, Netherlands",
        "malzeme": "Hahnemuhle Photo Rag 308 gsm, %100 pamuk, asitsiz ve ligninsiz (ISO 9706), arsiv pigment giclee baski",
        "guvenlik_notu": ("Dekoratif duvar baskisi. Oyuncak degildir; 3 yas alti cocuklar icin uygun "
                          "degildir. Cerceve ve cam iceriginde degildir. Nemden, dogrudan gunes "
                          "isigindan ve atesten uzak tutunuz. Kenarlarindan tutunuz."),
        "kaynak": "B97 START_HERE (Prodigi 6 Eyl 2026 maili) + POD aciklama metni",
    }
    with open(out / "gpsr_panel_ready.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "urun", "uretici", "uretici_adresi", "responsible_person",
                    "malzeme", "guvenlik_notu", "kaynak_dosya", "panelde_girilecek_alan"])
        for pair, lid in ciftler:
            A, B = [x.capitalize() for x in pair.split("_")]
            w.writerow([lid, f"{A} and {B} Zodiac Couple Print (unframed giclee)",
                        GPSR["uretici"], GPSR["uretici_adres"], GPSR["responsible_person"],
                        GPSR["malzeme"], GPSR["guvenlik_notu"], GPSR["kaynak"],
                        "Listing > Product safety: Manufacturer / EU responsible person / "
                        "Safety information"])

    ozet = {"icerik_satiri": len(satirlar), "cift": len(ciftler),
            "platform": len(PLATFORMLAR), "gpsr_satiri": len(ciftler),
            "ads_kolon": len(ADS_KOLON)}
    (out / "_oncelik_5_6_7_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    print("ONCELIK 5/6/7 ozet:", json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
