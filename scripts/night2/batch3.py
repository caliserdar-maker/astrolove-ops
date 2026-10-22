#!/usr/bin/env python3
"""BATCH 3 - bulgulari ise cevirme (GOREV 2,3,4,5,7,8,9,10). SALT OKUR + TASLAK.

Etsy'ye yazma YOK. Girdiler Batch 2 ciktilaridir (yeniden tarama yapilmaz).
Her gorev kendi hata blogunda; biri patlarsa digerleri surer.
"""
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "etsy"))
UZUN_TIRE = {"—": "EM DASH", "–": "EN DASH", "‒": "FIGURE DASH",
             "―": "HORIZONTAL BAR", "−": "MINUS SIGN"}
ONCELIK = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "FALSE_POSITIVE"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def gorev(ad, fn, sonuclar):
    bas = simdi()
    try:
        kayit, hata, notu = fn()
        durum = "PASS" if not hata else ("FAIL" if kayit == 0 else "PASS")
    except Exception as ex:                                       # noqa: BLE001
        kayit, hata, notu, durum = 0, 1, f"{type(ex).__name__}: {ex}", "FAIL"
        print(f"  {ad} HATA: {traceback.format_exc(limit=2)[:400]}")
    sonuclar.append({"gorev": ad, "baslangic": bas, "bitis": simdi(), "durum": durum,
                     "kayit": kayit, "hata": hata, "aciklama": notu})
    print(f"  {ad}: {durum} | kayit {kayit} | hata {hata} | {notu}")


def tire_temizle(metin):
    """Uzun tireleri baglama gore duz karsiliklariyla degistirir."""
    t = metin
    # " - " gibi ayirac kullanimlari: bosluklu uzun tire -> virgul yerine duz tire
    t = re.sub(r"\s*[—―]\s*", " - ", t)          # em dash / horizontal bar
    t = re.sub(r"(\d)\s*[–‒]\s*(\d)", r"\1-\2", t)   # sayi araligi: 5-7
    t = re.sub(r"\s*[–‒]\s*", " - ", t)          # kalan en dash
    t = t.replace("−", "-")                            # minus
    t = re.sub(r" {2,}", " ", t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b2-dir", required=True, help="Batch 2 cikti klasoru (yerel kopya)")
    ap.add_argument("--prices", default="scripts/etsy/pod_prices.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shop-json", default="", help="GET /shops/{id} ciktisi (salt okur)")
    ap.add_argument("--web-notes", default="", help="rakip arastirmasi ham notlari")
    a = ap.parse_args()
    b2 = pathlib.Path(a.b2_dir)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sonuclar = []

    katalog = json.loads((b2 / "full_etsy_catalog.json").read_text(encoding="utf-8")) \
        if (b2 / "full_etsy_catalog.json").exists() else []

    # ---------------------------------------------------------------- GOREV 2
    def g2():
        wp = [L for L in katalog if L.get("urun_ailesi") == "Digital wallpaper"]
        if not wp:
            return 0, 1, "katalogda wallpaper ilani yok"
        yeni, fark = [], []
        for L in wp:
            eski = L.get("_desc") or ""
            tireler = {UZUN_TIRE[c]: eski.count(c) for c in UZUN_TIRE if c in eski}
            temiz = tire_temizle(eski)
            kalan = {UZUN_TIRE[c]: temiz.count(c) for c in UZUN_TIRE if c in temiz}
            degisti = temiz != eski
            yeni.append({"listing_id": L["listing_id"], "burc_cifti": L.get("burc_cifti", ""),
                         "baslik": L.get("baslik", ""), "description": temiz,
                         "eski_uzunluk": len(eski), "yeni_uzunluk": len(temiz),
                         "temizlenen_tire": tireler})
            # satir bazli fark
            e_satir, y_satir = eski.split("\n"), temiz.split("\n")
            for i, (es, ys) in enumerate(zip(e_satir, y_satir), 1):
                if es != ys:
                    fark.append({"listing_id": L["listing_id"], "satir": i,
                                 "once": es.strip()[:160], "sonra": ys.strip()[:160],
                                 "tur": "uzun tire temizligi"})
            if kalan:
                fark.append({"listing_id": L["listing_id"], "satir": 0, "once": "",
                             "sonra": "", "tur": f"UYARI: temizlenemeyen tire {kalan}"})
        (out / "wallpaper_description_v2.json").write_text(
            json.dumps(yeni, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(out / "wallpaper_description_diff.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["listing_id", "satir", "once", "sonra", "tur"])
            w.writeheader()
            for x in fark:
                w.writerow(x)
        degisen = sum(1 for x in yeni if x["temizlenen_tire"])
        kalanlar = sum(1 for x in fark if x["tur"].startswith("UYARI"))
        return len(yeni), kalanlar, (f"{degisen}/{len(yeni)} ilanda tire temizlendi, "
                                     f"{len(fark)} satir degisti, temizlenemeyen {kalanlar}")

    # ---------------------------------------------------------------- GOREV 3
    def g3():
        p = b2 / "seo_audit.csv"
        if not p.exists():
            return 0, 1, "seo_audit.csv yok"
        with open(p, newline="", encoding="utf-8") as fh:
            bulgular = list(csv.DictReader(fh))
        kat = {L["listing_id"]: L for L in katalog}
        # yeniden siniflandirma kurallari
        YENI = {
            "DIJITAL_ICINDE_KARGO_IFADESI": ("FALSE_POSITIVE",
                "wallpaper capraz satis blogu 'PREFER IT ON YOUR WALL?' basligini kullaniyor; "
                "kural yalniz 'PREFER IT READY TO HANG' blogunu cikariyor"),
            "DOSYA_TESLIM_BILINMIYOR": ("FALSE_POSITIVE",
                "dosya envanteri cache'i yalniz 390 poster dijitalini kapsiyor"),
            "UZUN_TIRE": ("HIGH", "marka kurali: uzun tire AI isareti sayiliyor"),
            "ILK40_URUN": ("FALSE_POSITIVE",
                "Etsy 26 Agustos 2025: ifadenin basliktaki yeri siralamayi etkilemez; "
                "kisa, acik ve alici odakli baslik esastir"),
        }
        triaj = []
        for b in bulgular:
            kod = b["kod"]
            yeni_onc, gerekce = YENI.get(kod, (b["oncelik"], "kural degismedi"))
            L = kat.get(b["id"], {})
            triaj.append({"id": b["id"], "urun_ailesi": b["urun_ailesi"],
                          "eski_oncelik": b["oncelik"], "yeni_oncelik": yeni_onc,
                          "kod": kod, "aciklama": b["aciklama"], "gerekce": gerekce,
                          "baslik": (L.get("baslik") or "")[:80]})
        triaj.sort(key=lambda x: (ONCELIK.index(x["yeni_oncelik"]), x["kod"], x["id"]))
        with open(out / "seo_findings_triaged.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "urun_ailesi", "eski_oncelik",
                                               "yeni_oncelik", "kod", "aciklama", "gerekce",
                                               "baslik"])
            w.writeheader()
            for x in triaj:
                w.writerow(x)
        gercek = [x for x in triaj if x["yeni_oncelik"] != "FALSE_POSITIVE"]
        top = gercek[:50]
        md = [f"# GOREV 3 - En onemli 50 gercek SEO duzeltmesi ({simdi()} UTC)", "",
              f"Toplam bulgu {len(triaj)} | gercek {len(gercek)} | "
              f"yanlis pozitif {len(triaj) - len(gercek)}. Canli degisiklik YOK.", "",
              "| # | listing | aile | oncelik | kod | mevcut | onerilen | gerekce |",
              "|---:|---|---|---|---|---|---|---|"]
        for i, x in enumerate(top, 1):
            L = kat.get(x["id"], {})
            if x["kod"] == "UZUN_TIRE":
                mevcut = "aciklamada em/en dash"
                onerilen = "duz tire ( - ) ile degistir (wallpaper_description_v2.json hazir)"
            else:
                mevcut, onerilen = x["aciklama"][:40], "kural bazli duzeltme"
            md.append(f"| {i} | {x['id']} | {x['urun_ailesi']} | {x['yeni_oncelik']} | "
                      f"{x['kod']} | {mevcut} | {onerilen} | {x['gerekce'][:50]} |")
        md += ["", "## Not", "",
               "ILK40_URUN bulgusu yanlis pozitiftir; baslik degisikligi uretilmez.",
               "Dogrulanmis metin duzeltmesi UZUN_TIRE (78 wallpaper) grubudur.", ""]
        (out / "top_50_seo_actions.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        say = Counter(x["yeni_oncelik"] for x in triaj)
        return len(triaj), 0, f"{dict(say)}; gercek {len(gercek)}, top 50 secildi"

    # ---------------------------------------------------------------- GOREV 4
    def g4():
        fiyatlar = {}
        p = pathlib.Path(a.prices)
        if p.exists():
            with open(p, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    fiyatlar[r["size"]] = float(r["price"])
        VARSAYIM = [
            ("Etsy islem ucreti", "6.5%", "Etsy 2026 standart oran (urun + kargo uzerinden)"),
            ("Etsy odeme islem ucreti", "3.0% + 0.25 USD", "ABD hesabi varsayimi; ulkeye gore degisir"),
            ("Etsy listeleme ucreti", "0.20 USD / 4 ay", "ilan basina, yenilemede tekrar"),
            ("Prodigi POD maliyeti", "VARSAYIM 12.00 USD (8x10) - 28.00 USD (30x40)",
             "GERCEK VERI YOK: Prodigi fiyat listesi repoda yok, panelden alinmali"),
            ("Kargo maliyeti", "VARSAYIM 5.00 USD ortalama", "Prodigi fiyata dahil degil; "
             "gercek deger sipariste netlesir"),
            ("Dijital urun maliyeti", "0.00 USD", "dosya teslimi, marjinal maliyet yok"),
            ("Etsy Ads butcesi", "25.00 USD / gun", "kullanicidan verildi"),
        ]
        satir = []
        for aile, fiyat, maliyet, kargo in [
                ("POD baski (8x10)", fiyatlar.get("8x10", 30.99), 12.00, 5.00),
                ("POD baski (30x40)", fiyatlar.get("30x40", 0) or 89.99, 28.00, 5.00),
                ("Digital wall art", 9.99, 0.0, 0.0),
                ("Digital wallpaper", 6.65, 0.0, 0.0)]:
            islem = fiyat * 0.065
            odeme = fiyat * 0.03 + 0.25
            listeleme = 0.20
            toplam_maliyet = maliyet + kargo + islem + odeme + listeleme
            kar = fiyat - toplam_maliyet
            marj = kar / fiyat * 100 if fiyat else 0
            bb = 25.00 / kar if kar > 0 else None
            min_fiyat = (maliyet + kargo + listeleme + 0.25) / (1 - 0.065 - 0.03) if kar else 0
            satir.append({
                "urun_ailesi": aile, "fiyat": round(fiyat, 2),
                "urun_maliyeti": maliyet, "kargo": kargo,
                "etsy_islem_6.5": round(islem, 2), "etsy_odeme_3+0.25": round(odeme, 2),
                "listeleme_0.20": listeleme, "toplam_maliyet": round(toplam_maliyet, 2),
                "birim_kar": round(kar, 2), "brut_marj_yuzde": round(marj, 1),
                "gunluk_25usd_basabas_satis": round(bb, 2) if bb else "kar yok",
                "min_karli_fiyat": round(min_fiyat, 2),
                "roas_esigi_basabas": round(fiyat / kar, 2) if kar > 0 else "-",
                "roas_hedef_2x_kar": round(2 * fiyat / kar, 2) if kar > 0 else "-",
            })
        with open(out / "astrolove_unit_economics.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(satir[0]))
            w.writeheader()
            for x in satir:
                w.writerow(x)
        md = [f"# GOREV 4 - AstroLove birim ekonomisi ({simdi()} UTC)", "",
              "**UYARI: Prodigi gercek maliyet listesi repoda YOK.** Asagidaki POD maliyetleri",
              "VARSAYIMDIR ve panelden dogrulanmadan karar alinmamalidir. Veri uydurulmadi;",
              "varsayim oldugu her yerde isaretlendi.", "",
              "## Varsayimlar ve kaynaklar", "", "| kalem | deger | kaynak / not |", "|---|---|---|"]
        for k, v, n in VARSAYIM:
            md.append(f"| {k} | {v} | {n} |")
        md += ["", "## Birim ekonomi", "", "| aile | fiyat | toplam maliyet | birim kar | marj | "
               "25 USD/gun basabas satis | min karli fiyat | basabas ROAS |",
               "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for x in satir:
            md.append(f"| {x['urun_ailesi']} | {x['fiyat']} | {x['toplam_maliyet']} | "
                      f"{x['birim_kar']} | %{x['brut_marj_yuzde']} | "
                      f"{x['gunluk_25usd_basabas_satis']} | {x['min_karli_fiyat']} | "
                      f"{x['roas_esigi_basabas']} |")
        md += ["", "## Okuma", "",
               "- **Basabas satis**: gunluk 25 USD reklam butcesini karsilamak icin gereken",
               "  gunluk satis adedi (yalniz o urun ailesinden satildigi varsayimiyla).",
               "- **Basabas ROAS**: reklamin zarar etmemesi icin gereken en dusuk ROAS.",
               "  Bunun altinda her satis reklam maliyetini kurtarmaz.",
               "- Dijital urunlerde marjinal maliyet 0 oldugu icin basabas ROAS en dusuk,",
               "  yani reklam butcesi once dijital ailede denenmeli.",
               "- POD'da gercek Prodigi maliyeti alinmadan reklam olceklenmemeli: 12 USD",
               "  varsayimi 2 USD sasarsa marj yaklasik %7 kayar.", ""]
        (out / "unit_economics_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(satir), 0, "4 urun ailesi; POD maliyeti VARSAYIM olarak isaretlendi"

    # ---------------------------------------------------------------- GOREV 5
    def g5():
        shop = {}
        if a.shop_json and pathlib.Path(a.shop_json).exists():
            shop = json.loads(pathlib.Path(a.shop_json).read_text(encoding="utf-8"))
        aile = Counter(L.get("urun_ailesi") for L in katalog)
        gorsel = [L.get("gorsel_sayisi", 0) for L in katalog]
        videolu = sum(1 for L in katalog if L.get("video_durumu") == "var")
        kontrol = []

        def K(alan, deger, puan, onem, oneri):
            kontrol.append({"alan": alan, "gozlem": str(deger)[:150], "puan_10": puan,
                            "onem": onem, "onerilen_duzeltme": oneri})
        ad = shop.get("shop_name") or "(okunamadi)"
        K("shop name", ad, 8 if ad and ad != "(okunamadi)" else 0, "MEDIUM",
          "Marka adi net; arama icin 'Zodiac' gibi bir kelime eklenmesi degerlendirilsin")
        duyuru = (shop.get("announcement") or "").strip()
        K("announcement", duyuru[:120] or "BOS", 9 if len(duyuru) > 80 else (5 if duyuru else 0),
          "HIGH" if not duyuru else "LOW",
          "Bos ise: 78 cift, 5 edisyon, dijital+fiziksel ayrimi ve teslim suresi tek paragrafta")
        K("icon / header", f"icon_url={bool(shop.get('icon_url_fullxfull'))}",
          5 if shop.get("icon_url_fullxfull") else 0, "MEDIUM",
          "API'den dogrulanamiyorsa panelden gorsel kontrol; header'da 'INSTANT DOWNLOAD' "
          "ifadesi artik yaniltici (fiziksel urun de var, B97 acik is 4)")
        K("About / FAQ / policies", "API'de bu alanlar YOK", 0, "HIGH",
          "Panelden kontrol: About hikayesi, FAQ'de teslim/iade/cerceve sorulari, "
          "dijital urunlerde iade politikasi acik yazilmali")
        K("urun galeri sirasi", f"ortalama {sum(gorsel)/len(gorsel):.1f} gorsel, "
          f"{videolu} ilanda video", 8, "LOW",
          "POD'da 12 gorsel + video var; dijitalde ilk kare edisyon rengini net gostermeli")
        K("mobil gorunum", "API'den olculemez", 0, "MEDIUM",
          "Baslik ilk 40 karakteri mobilde gorunur: 54 ilanda urun kelimesi ilk 40'ta yok")
        K("guven unsurlari", f"{len(katalog)} aktif ilan, magaza satis sayisi "
          f"{shop.get('transaction_sold_count', '?')}", 4, "HIGH",
          "Yorum sayisi dusukken: teslim suresi, uretim ortagi ve iade kosulu ilan icinde "
          "one cikarilmali; insert karti yorum davetine donusturulebilir (politika kontrolu sart)")
        K("dijital/fiziksel ayrimi", f"{aile.get('POD baski', 0)} fiziksel / "
          f"{aile.get('Digital wall art', 0) + aile.get('Digital wallpaper', 0)} dijital", 7,
          "HIGH", "Bolum adlari ayrimi tasiyor; magaza duyurusu ve header'da da ayrim netlesmeli")
        K("CTA netligi", "ilan aciklamalarinda capraz satis linki var", 7, "MEDIUM",
          "Dijitalde 'PREFER IT ON YOUR WALL?', posterde 'PREFER AN INSTANT DOWNLOAD?' "
          "bloklari calisiyor; magaza duzeyinde tek bir CTA yok")
        ort = sum(x["puan_10"] for x in kontrol) / len(kontrol)
        with open(out / "shop_conversion_audit.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["alan", "gozlem", "puan_10", "onem",
                                               "onerilen_duzeltme"])
            w.writeheader()
            for x in kontrol:
                w.writerow(x)
        md = [f"# GOREV 5 - Etsy magaza donusum denetimi ({simdi()} UTC)", "",
              f"Ortalama puan: **{ort:.1f}/10**. Canli magaza degisikligi YAPILMADI.", "",
              "**Kapsam siniri:** Etsy Open API v3'te About, FAQ, policies, header gorseli ve",
              "mobil gorunum alanlari YOK. Bu basliklar panelden elle kontrol edilmeli;",
              "asagida 0 puan verilenler 'olculemedi' anlamindadir, 'kotu' degil.", "",
              "| alan | gozlem | puan | onem | onerilen duzeltme |", "|---|---|---:|---|---|"]
        for x in kontrol:
            md.append(f"| {x['alan']} | {x['gozlem'][:60]} | {x['puan_10']} | {x['onem']} | "
                      f"{x['onerilen_duzeltme'][:90]} |")
        md += ["", "## Oncelikli uc is", "",
               "1. **Magaza duyurusu (announcement)**: dijital/fiziksel ayrimi + teslim suresi.",
               "2. **Header'daki 'INSTANT DOWNLOAD' ifadesi**: artik fiziksel urun de var (B97).",
               "3. **Baslik ilk 40 karakteri**: 54 ilanda urun kelimesi mobil kesimde disarida.", ""]
        (out / "shop_conversion_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(kontrol), 0, f"ortalama {ort:.1f}/10; About/FAQ/policies API'de yok"

    # ---------------------------------------------------------------- GOREV 7
    def g7():
        p = b2 / "gpsr_panel_ready.csv"
        if not p.exists():
            return 0, 1, "gpsr_panel_ready.csv yok"
        with open(p, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        pod = {L["listing_id"] for L in katalog if L.get("urun_ailesi") == "POD baski"}
        hata = []
        for r in rows:
            for alan in ("listing_id", "urun", "uretici", "uretici_adresi", "responsible_person",
                         "malzeme", "guvenlik_notu", "kaynak_dosya", "panelde_girilecek_alan"):
                if not (r.get(alan) or "").strip():
                    hata.append((r.get("listing_id"), f"bos alan: {alan}"))
            if pod and r["listing_id"] not in pod:
                hata.append((r["listing_id"], "katalogda POD ilani degil"))
        eksik = sorted(pod - {r["listing_id"] for r in rows}) if pod else []
        for lid in eksik:
            hata.append((lid, "GPSR tablosunda yok"))
        with open(out / "gpsr_panel_ready.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        with open(out / "gpsr_validation.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["listing_id", "bulgu"])
            for lid, b in hata:
                w.writerow([lid, b])
        return len(rows), len(hata), (f"{len(rows)} satir, {len(hata)} bulgu, "
                                      f"POD eslesmesi {len(rows) - len(eksik)}/{len(pod) or '?'}")

    # ---------------------------------------------------------------- GOREV 8
    def g8():
        p = b2 / "duplicate_candidates.csv"
        if not p.exists():
            return 0, 1, "duplicate_candidates.csv yok"
        with open(p, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        # matristeki kullanilan dosyalar korunur
        kullanilan = set()
        mp = b2 / "product_listing_media_matrix.json"
        if mp.exists():
            for m in json.loads(mp.read_text(encoding="utf-8")):
                for k in ("ana_zip", "pdf_guide", "video"):
                    if m.get(k):
                        kullanilan.add(m[k])
        KORU_RX = re.compile(r"MASTER|FINAL|APPROVED|ONAYLI|/PRINT|ETSY_ZIPS", re.I)
        ARSIV_RX = re.compile(r"YEDEK|BACKUP|ARCHIVE|ARSIV|/OLD|ESKI|COPY|KOPYA|_v\d|TEMP/", re.I)
        plan, bosalacak = [], 0
        for r in rows:
            yollar = [y.strip() for y in (r.get("yollar") or "").split("|") if y.strip()]
            if r.get("tur") == "AYNI_AD_FARKLI_ICERIK":
                plan.append({"sinif": "BELIRSIZ", "tur": r["tur"], "anahtar": r.get("anahtar", ""),
                             "kopya_sayisi": r.get("kopya_sayisi", ""),
                             "bosalacak_bayt": 0, "master_adayi": "",
                             "arsiv_adaylari": " | ".join(yollar[:4]),
                             "gerekce": "ayni ad farkli icerik: elle incelenmeli, otomatik islem YOK"})
                continue
            master = next((y for y in yollar if y in kullanilan), None)
            gerekce = "ilan tarafindan kullaniliyor" if master else ""
            if not master:
                master = next((y for y in yollar if KORU_RX.search(y)), None)
                gerekce = "MASTER/FINAL/PRINT yolunda" if master else ""
            if not master:
                master = yollar[0] if yollar else ""
                gerekce = "ilk yol birincil secildi (belirsiz)"
            adaylar = [y for y in yollar if y != master]
            guvenli = [y for y in adaylar if ARSIV_RX.search(y)]
            sinif = ("GUVENLI_ARSIV_ADAYI" if guvenli and len(guvenli) == len(adaylar)
                     else "BELIRSIZ" if adaylar else "KORUNACAK_MASTER")
            try:
                tb = int(r.get("bosalacak_bayt") or 0)
            except ValueError:
                tb = 0
            if sinif == "GUVENLI_ARSIV_ADAYI":
                bosalacak += tb
            plan.append({"sinif": sinif, "tur": r.get("tur", ""), "anahtar": r.get("anahtar", ""),
                         "kopya_sayisi": r.get("kopya_sayisi", ""), "bosalacak_bayt": tb,
                         "master_adayi": master, "arsiv_adaylari": " | ".join(adaylar[:4]),
                         "gerekce": gerekce})
        # oksuzler
        op = b2 / "orphan_assets.csv"
        if op.exists():
            with open(op, newline="", encoding="utf-8") as fh:
                for i, r in enumerate(csv.DictReader(fh)):
                    if i >= 500:
                        break
                    plan.append({"sinif": "HICBIR_CIFTE_BAGLANAMAYAN", "tur": "orphan",
                                 "anahtar": r.get("yol", ""), "kopya_sayisi": 1,
                                 "bosalacak_bayt": 0, "master_adayi": "", "arsiv_adaylari": "",
                                 "gerekce": r.get("neden", "")})
        with open(out / "duplicate_archive_plan.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["sinif", "tur", "anahtar", "kopya_sayisi",
                                               "bosalacak_bayt", "master_adayi",
                                               "arsiv_adaylari", "gerekce"])
            w.writeheader()
            for x in plan:
                w.writerow(x)
        say = Counter(x["sinif"] for x in plan)
        return len(plan), 0, (f"{dict(say)}; guvenli arsivden bosalacak "
                              f"{bosalacak/1e9:.2f} GB (tasima YAPILMADI)")

    # ---------------------------------------------------------------- GOREV 9
    def g9():
        KOLON = [("date", "YYYY-MM-DD", "zorunlu", "gun bazli satir"),
                 ("listing_id", "sayi", "zorunlu", "ilan no; katalogla eslesmeli"),
                 ("listing_title", "metin", "opsiyonel", "raporda okunurluk icin"),
                 ("impressions", "sayi", "zorunlu", "gosterim"),
                 ("clicks", "sayi", "zorunlu", "tiklama"),
                 ("spend", "ondalik", "zorunlu", "harcama"),
                 ("orders", "sayi", "zorunlu", "reklamdan siparis"),
                 ("revenue", "ondalik", "zorunlu", "reklamdan gelir"),
                 ("currency", "metin", "opsiyonel", "varsayilan USD")]
        with open(out / "ads_import_template.csv", "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow([k for k, _, _, _ in KOLON])
        with open(out / "ads_column_spec.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["kolon", "tip", "zorunluluk", "aciklama"])
            for row in KOLON:
                w.writerow(row)
        md = [f"# GOREV 9 - Etsy Ads import sistemi ({simdi()} UTC)", "",
              "**Gercek veri YOK.** Etsy Open API v3'te reklam ucu bulunmuyor; CSV panelden",
              "indirilmeli. Bu dosyalar bos sablon ve hesap kurallaridir, sonuc uretilmedi.", "",
              "## Zorunlu kolonlar", "", "| kolon | tip | zorunluluk | aciklama |", "|---|---|---|---|"]
        for k, t, z, d in KOLON:
            md.append(f"| {k} | {t} | {z} | {d} |")
        md += ["", "## Eksik veri alanlari", "",
               "- `revenue` Etsy disa aktariminda bazen yok: yoksa ROAS hesaplanamaz,",
               "  betik o ilani WATCH sinifina alir.",
               "- `orders` yoksa donusum ve wasted spend hesaplanamaz.",
               "- Attribution penceresi (30 gun) Etsy tarafinda sabittir, CSV'de belirtilmez.", "",
               "## Formuller", "",
               "```", "CTR             = clicks / impressions * 100",
               "CPC             = spend / clicks", "conversion rate = orders / clicks * 100",
               "ROAS            = revenue / spend",
               "wasted spend    = orders = 0 olan ilanlarin spend toplami", "```", "",
               "## Karar kurallari", "", "| sinif | kural | eylem |", "|---|---|---|",
               "| PAUSE | clicks >= 30 ve orders = 0 ve spend >= 10 | reklami durdur (panelden) |",
               "| REVIEW | clicks >= 15 ve orders = 0 | ilan sayfasini incele (gorsel/fiyat/baslik) |",
               "| REDUCE | spend >= 3 ve ROAS < 1.0 | butce dusur |",
               "| KEEP | ROAS >= 2.0 | devam |",
               "| WATCH | digerleri / yetersiz veri | veri biriktir |", "",
               "Esikler `ads_kpi.py` parametreleriyle degistirilebilir. Butce ve teklif",
               "degisikligi bu sistemin isi DEGILDIR; panelden Serdar yapar.", ""]
        (out / "ads_import_system.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(KOLON), 0, "sablon + kolon spesifikasyonu + 5 karar sinifi (PAUSE eklendi)"

    # ---------------------------------------------------------------- GOREV 10
    def g10():
        p = b2 / "platform_content_dataset.csv"
        if not p.exists():
            return 0, 1, "platform_content_dataset.csv yok"
        with open(p, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        SINIR = {"Instagram": 2200, "Facebook": 63206, "TikTok": 2200, "YouTube": 5000,
                 "Pinterest": 500, "Etsy": 13000, "Google Business": 1500}
        BASLIK_SINIR = {"Pinterest": 100, "YouTube": 100, "Instagram": 125, "TikTok": 150,
                        "Etsy": 140, "Facebook": 255, "Google Business": 300}
        qa, hata = [], 0
        ciftler = {r["cift"] for r in rows}
        platformlar = {r["platform"] for r in rows}
        for r in rows:
            b = []
            plat = r["platform"]
            if len(r["aciklama"]) > SINIR.get(plat, 99999):
                b.append(f"aciklama {len(r['aciklama'])}>{SINIR[plat]}")
            if len(r["baslik"]) > BASLIK_SINIR.get(plat, 999):
                b.append(f"baslik {len(r['baslik'])}>{BASLIK_SINIR[plat]}")
            for alan in ("icerik_amaci", "icerik_formati", "hook", "cta", "hashtag_tag",
                         "seo_anahtar_kelimeler", "onerilen_oran", "onerilen_sure",
                         "onerilen_yayin_zamani", "kullanilacak_medya"):
                if not (r.get(alan) or "").strip():
                    b.append(f"bos alan: {alan}")
            if any(c in r["baslik"] + r["aciklama"] + r["hook"] for c in UZUN_TIRE):
                b.append("uzun tire")
            if plat == "Google Business" and r["hashtag_tag"] != "(hashtag kullanilmaz)":
                b.append("Google Business'ta hashtag olmamali")
            if plat in ("Instagram", "TikTok") and not r["hashtag_tag"].startswith("#"):
                b.append("hashtag '#' ile baslamiyor")
            if plat == "Pinterest" and "2:3" not in r["onerilen_oran"]:
                b.append("Pinterest orani 2:3 olmali")
            A, B = [x.capitalize() for x in r["cift"].split("_")]
            if A not in r["hook"] and A.lower() not in r["hook"].lower():
                b.append("hook'ta birinci burc yok")
            hata += len(b)
            qa.append({"cift": r["cift"], "platform": plat,
                       "baslik_uzunluk": len(r["baslik"]),
                       "aciklama_uzunluk": len(r["aciklama"]),
                       "sonuc": "TEMIZ" if not b else "BULGU",
                       "bulgular": " | ".join(b)})
        with open(out / "platform_content_qa.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["cift", "platform", "baslik_uzunluk",
                                               "aciklama_uzunluk", "sonuc", "bulgular"])
            w.writeheader()
            for x in qa:
                w.writerow(x)
        bulgulu = sum(1 for x in qa if x["sonuc"] == "BULGU")
        tam = len(ciftler) == 78 and len(platformlar) == 7 and len(rows) == 546
        return len(qa), hata, (f"{len(rows)} satir, {len(ciftler)} cift x {len(platformlar)} "
                               f"platform, matris {'TAM' if tam else 'EKSIK'}, "
                               f"bulgulu satir {bulgulu}")

    print("BATCH 3 gorevleri")
    gorev("GOREV 2 wallpaper taslagi", g2, sonuclar)
    gorev("GOREV 3 SEO triage", g3, sonuclar)
    gorev("GOREV 4 birim ekonomi", g4, sonuclar)
    gorev("GOREV 5 magaza denetimi", g5, sonuclar)
    gorev("GOREV 7 GPSR dogrulama", g7, sonuclar)
    gorev("GOREV 8 duplicate plan", g8, sonuclar)
    gorev("GOREV 9 ads import", g9, sonuclar)
    gorev("GOREV 10 icerik QA", g10, sonuclar)
    (out / "_batch3_gorev_durum.json").write_text(
        json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OZET:", json.dumps({x["gorev"]: x["durum"] for x in sonuclar}, ensure_ascii=False))


if __name__ == "__main__":
    main()
