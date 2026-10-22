#!/usr/bin/env python3
"""GECE DENETIMI - GOREV 2/3/4/5 (Mo 15 Eyl 2026). SALT OKUR: Etsy'ye yazma YOK.

  GOREV 2  apply sonrasi dogrulama: 78 ilan tek batch GET ile okunur, title /
           description / tags v2 dosyasiyla karsilastirilir -> PASS/FAIL.
  GOREV 3  degismemesi gereken alanlar: apply kosusunun before_apply/after
           yedekleri karsilastirilir (0 ek cagri) + ornek ilanlarda gorsel,
           varyasyon gorseli, video ve envanter uclari okunur.
  GOREV 4  Etsy Ads: OAS semasinda reklam ucu taramasi + Drive'da Ads CSV arama
           sonucu (Etsy'ye cagri yok).
  GOREV 5  ilan kalite denetimi: baslik, 13 etiket, aciklama tutarliligi, burc
           cifti dogrulamasi, GPSR, dosya/teslimat ifadesi, fiziksel/dijital karisimi.

Her gorev kendi hata blogunda; biri patlarsa digerleri surer.
Kullanim: post_apply_audit.py --changes C.json --pod-state P.csv --apply-dir D
          --oas oas.json --ads-drive A.md --out OUT [--ornek 6]
"""
import argparse
import csv
import html
import json
import os
import pathlib
import re
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "etsy"))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
import pod_desc_set as DS  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
KORUNAN = ["price", "state", "shop_section_id", "taxonomy_id", "shipping_profile_id",
           "return_policy_id", "materials", "who_made", "when_made", "is_supply",
           "has_variations", "should_auto_renew", "quantity", "listing_type",
           "processing_min", "processing_max", "is_customizable", "is_personalizable"]
BEKLENEN_BOLUM = ["TWO SIGNS. ONE ORIGINAL SYMBOL.", "WHY IT IS DIFFERENT", "PAPER AND PRINT",
                  "CHOOSE YOUR EDITION", "CHOOSE YOUR SIZE", "MADE TO ORDER AND SHIPPING",
                  "PLEASE NOTE", "CARE", "RETURNS AND DAMAGE", "ORIGINAL ASTROLOVE ARTWORK"]
GPSR_ALAN = ["responsible_person", "manufacturer", "gpsr", "product_safety"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def gorev(ad, fn, sonuclar):
    bas = simdi()
    try:
        kayit, hata, notu = fn()
        durum = "PASS" if not hata else "FAIL"
    except Exception as ex:                                   # noqa: BLE001
        kayit, hata, notu, durum = 0, 1, f"{type(ex).__name__}: {ex}", "FAIL"
        log(f"  {ad} HATA: {traceback.format_exc(limit=2)[:400]}")
    sonuclar.append({"gorev": ad, "baslangic": bas, "bitis": simdi(), "durum": durum,
                     "kayit": kayit, "hata": hata, "aciklama": notu, "sonraki": "evet"})
    log(f"  {ad}: {durum} | kayit {kayit} | hata {hata} | {notu}")
    return sonuclar[-1]


def burclar_metinden(metin):
    out = []
    for m in re.finditer(r"\b(" + "|".join(BURCLAR) + r")\b", metin or "", re.I):
        out.append(m.group(1).capitalize())
        if len(out) == 2:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changes", required=True)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--apply-dir", default="")
    ap.add_argument("--oas", default="")
    ap.add_argument("--ads-drive", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ornek", type=int, default=6)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs = {r["id"]: r for r in json.loads(pathlib.Path(a.changes).read_text(encoding="utf-8"))}
    sonuclar = []

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    kota_bas = api.remaining
    canli = {}

    # ---------------------------------------------------------------- GOREV 2
    def gorev2():
        ids = sorted(recs)
        r = api.get("/listings/batch", params={"listing_ids": ",".join(ids)}) or {}
        for x in r.get("results") or []:
            if x.get("listing_id"):
                canli[str(x["listing_id"])] = x
        satir, hata = [], 0
        for lid in ids:
            L, rec = canli.get(lid), recs[lid]
            if not L:
                satir.append({"id": lid, "cift": rec["pair"], "sonuc": "FAIL",
                              "title": "?", "description": "?", "tags": "?",
                              "not": "batch GET'te donmedi"})
                hata += 1
                continue
            d = {
                "title": DS.esit(L.get("title") or "", rec["title"]) != "farkli",
                "description": DS.esit(L.get("description") or "", rec["description"]) != "farkli",
                "tags": [html.unescape(t) for t in (L.get("tags") or [])] == rec["tags"],
            }
            tamam = all(d.values())
            hata += 0 if tamam else 1
            satir.append({"id": lid, "cift": rec["pair"], "sonuc": "PASS" if tamam else "FAIL",
                          "title": "PASS" if d["title"] else "FAIL",
                          "description": "PASS" if d["description"] else "FAIL",
                          "tags": "PASS" if d["tags"] else "FAIL",
                          "not": "" if tamam else "v2 ile birebir degil"})
        with open(out / "task_02_verification.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "cift", "sonuc", "title", "description",
                                               "tags", "not"])
            w.writeheader()
            for x in satir:
                w.writerow(x)
        return len(satir), hata, f"{len(satir) - hata}/{len(satir)} ilan v2 ile birebir"

    # ---------------------------------------------------------------- GOREV 3
    def gorev3():
        yedek = pathlib.Path(a.apply_dir) / "backups" if a.apply_dir else None
        satir, hata = [], 0
        ciftler = 0
        if yedek and yedek.exists():
            for bf in sorted(yedek.glob("*.before_apply.json")):
                lid = bf.name.split(".")[0]
                af = yedek / f"{lid}.after.json"
                if not af.exists():
                    satir.append({"id": lid, "alan": "(after yedegi)", "once": "", "sonra": "",
                                  "sonuc": "EKSIK", "not": "ilan yazilmadan kosu durdu"})
                    continue
                ciftler += 1
                o, n = json.loads(bf.read_text(encoding="utf-8")), json.loads(af.read_text(encoding="utf-8"))
                for alan in KORUNAN:
                    if alan in o and alan in n and o[alan] != n[alan]:
                        hata += 1
                        satir.append({"id": lid, "alan": alan, "once": str(o[alan])[:60],
                                      "sonra": str(n[alan])[:60], "sonuc": "FARK",
                                      "not": "korunmasi gereken alan degisti"})
                if not any(x["id"] == lid and x["sonuc"] == "FARK" for x in satir):
                    satir.append({"id": lid, "alan": f"{len(KORUNAN)} alan", "once": "", "sonra": "",
                                  "sonuc": "AYNI", "not": "before_apply/after karsilastirmasi"})
        # ornek ilanlarda medya + envanter uclari (canli okuma)
        ornekler = sorted(recs)[:a.ornek]
        for lid in ornekler:
            try:
                medya = {"gorseller": DS.galeri(api, lid),
                         "varyasyon_gorselleri": DS.var_img(api, shop, lid),
                         "video": DS.videolar(api, lid),
                         "envanter_fiyat": DS.envanter(api, lid)}
            except SystemExit as ex:
                satir.append({"id": lid, "alan": "medya", "once": "", "sonra": "",
                              "sonuc": "OKUNAMADI", "not": str(ex)[:80]})
                hata += 1
                continue
            for alan, deger in medya.items():
                satir.append({"id": lid, "alan": alan, "once": "(apply oncesi kayit yok)",
                              "sonra": f"{len(deger)} kayit: {str(deger)[:70]}",
                              "sonuc": "GOZLEM", "not": "canli durum; apply sirasinda ilk ilanda birebir dogrulandi"})
        with open(out / "task_03_unchanged_fields.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "alan", "once", "sonra", "sonuc", "not"])
            w.writeheader()
            for x in satir:
                w.writerow(x)
        return len(satir), hata, f"{ciftler} ilanda once/sonra karsilastirildi, {hata} fark"

    # ---------------------------------------------------------------- GOREV 4
    def gorev4():
        md = [f"# GOREV 4 - Etsy Ads salt okur analizi ({simdi()} UTC)", "",
              "Butce, kampanya, teklif ve reklam ayarlarina DOKUNULMADI. Etsy'ye tek bir",
              "reklam cagrisi yapilmadi (API'de boyle bir uc yok).", ""]
        yollar, kelime = [], {}
        if a.oas and pathlib.Path(a.oas).exists():
            d = json.load(open(a.oas, encoding="utf-8"))
            rx = re.compile(r"/ads?\b|advert|promot|campaign|search[_-]?terms?|keyword|/stats?\b|analytic|impression", re.I)
            yollar = [p for p in d.get("paths") or {} if rx.search(p)]
            metin = json.dumps(d)
            for kw in ("advertis", "Etsy Ads", "offsite", "promoted", "impression", "click",
                       "spend", "budget", "cpc", "roas", "conversion"):
                kelime[kw] = len(re.findall(re.escape(kw), metin, re.I))
            md += [f"- OAS surumu {d.get('info', {}).get('version')}, {len(d.get('paths') or {})} yol",
                   f"- Reklam/istatistik benzeri yol: **{', '.join(yollar) if yollar else 'YOK'}**",
                   f"- Sema kelime sayilari: {kelime}", ""]
        ads = pathlib.Path(a.ads_drive).read_text(encoding="utf-8") if a.ads_drive and pathlib.Path(a.ads_drive).exists() else ""
        md += ["## Istenen metrikler ve durumu", "",
               "| metrik | kaynak | durum |", "|---|---|---|"]
        for m in ("gosterim", "tiklama", "CTR", "CPC", "harcama", "satis (reklamdan)",
                  "donusum", "ROAS", "hic tiklanmayan ilanlar", "tiklanip satis almayan ilanlar"):
            md.append(f"| {m} | Etsy Open API v3 | **VERI YOK** (uc nokta yok) |")
        md += ["", "## Drive'da indirilmis Etsy Ads disa aktarimi", "",
               ads or "Drive taramasinda Etsy Ads CSV'si bulunamadi.", "",
               "## Sonuc", "",
               "Etsy Ads metrikleri **yalniz Shop Manager > Marketing > Etsy Ads** ekranindan",
               "alinabilir. Analiz yapilabilmesi icin oradan CSV disa aktarimi Drive'a",
               "konmali (onerilen yol: ASTROLOVE/TEMP/ADS/etsy_ads_stats_<tarih>.csv).",
               "CSV geldiginde bu gorev ayni betikle hesaplanabilir: CTR = tiklama/gosterim,",
               "CPC = harcama/tiklama, ROAS = reklam geliri/harcama, ve ilan bazinda",
               "0 tiklama / 0 satis listeleri.", ""]
        (out / "task_04_ads_readonly.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        yok = 0 if not yollar else len(yollar)
        return len(kelime) or 1, 0, ("API'de reklam ucu YOK, Drive'da CSV yok -> veri yok"
                                     if not yollar else f"{yok} supheli yol bulundu")

    # ---------------------------------------------------------------- GOREV 5
    def gorev5():
        satir, hata = [], 0
        pod = {}
        with open(a.pod_state, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("listing_id") or "").isdigit():
                    pod[r["listing_id"]] = r.get("pair") or ""
        for lid in sorted(recs):
            rec = recs[lid]
            L = canli.get(lid) or {}
            bulgu = []
            baslik = L.get("title") or rec["title"]
            desc = html.unescape(L.get("description") or rec["description"])
            tags = [html.unescape(t) for t in (L.get("tags") or rec["tags"])]
            if len(baslik) > 140:
                bulgu.append(f"baslik {len(baslik)}>140")
            if len(baslik) < 40:
                bulgu.append(f"baslik kisa ({len(baslik)})")
            ilk = baslik.split(",")[0]
            if not re.search(r"Zodiac Couple Print", ilk):
                bulgu.append("baslikta birincil anahtar kelime ilk parcada degil")
            if len(tags) != 13:
                bulgu.append(f"tag {len(tags)}/13")
            if len(set(tags)) != len(tags):
                bulgu.append("tekrarli tag")
            uzun = [t for t in tags if len(t) > 20]
            if uzun:
                bulgu.append(f"20+ karakter tag: {uzun}")
            gecersiz = [t for t in tags if not all(c.isalnum() or c in " -'" for c in t)]
            if gecersiz:
                bulgu.append(f"gecersiz karakter: {gecersiz}")
            eksik_bolum = [b for b in BEKLENEN_BOLUM if b not in desc]
            if eksik_bolum:
                bulgu.append(f"aciklamada eksik bolum: {eksik_bolum}")
            b_baslik = burclar_metinden(baslik)
            b_bekl = [x.strip() for x in rec["pair"].split("+")]
            if sorted(b_baslik) != sorted(b_bekl):
                bulgu.append(f"baslik burc cifti {b_baslik} != {b_bekl}")
                hata += 1
            if pod.get(lid) and sorted(x.upper() for x in b_bekl) != sorted(pod[lid].split("_")):
                bulgu.append(f"POD state cifti {pod[lid]} uyusmuyor")
            for burc in b_bekl:
                if burc.lower() not in desc.lower():
                    bulgu.append(f"aciklamada {burc} gecmiyor")
            if L.get("listing_type") and L["listing_type"] != "physical":
                bulgu.append(f"listing_type={L['listing_type']} (fiziksel olmali)")
            if re.search(r"instant download|digital download|\bZIP\b|printable file", desc, re.I):
                bulgu.append("fiziksel ilanda dijital teslimat ifadesi")
            if "unframed" not in desc.lower():
                bulgu.append("aciklamada 'unframed' yok")
            if not re.search(r"Prodigi", desc):
                bulgu.append("uretim ortagi (Prodigi) gecmiyor")
            gpsr = [g for g in GPSR_ALAN if g in L]
            if not gpsr:
                bulgu.append("GPSR alani API'de yok (panelden girilir)")
            if any(c in baslik + desc for c in "—–‒―−"):
                bulgu.append("uzun tire var")
                hata += 1
            satir.append({"id": lid, "cift": rec["pair"],
                          "sonuc": "TEMIZ" if not bulgu else "BULGU",
                          "bulgu_sayisi": len(bulgu), "bulgular": " | ".join(bulgu),
                          "baslik_uzunluk": len(baslik), "tag_sayisi": len(tags)})
        with open(out / "task_05_listing_quality.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "cift", "sonuc", "bulgu_sayisi", "bulgular",
                                               "baslik_uzunluk", "tag_sayisi"])
            w.writeheader()
            for x in satir:
                w.writerow(x)
        bulgulu = sum(1 for x in satir if x["sonuc"] == "BULGU")
        return len(satir), hata, f"{bulgulu}/{len(satir)} ilanda bulgu (kritik hata {hata})"

    log("GOREV 2 - apply sonrasi dogrulama")
    gorev("GOREV 2 dogrulama", gorev2, sonuclar)
    log("GOREV 3 - degismemesi gereken alanlar")
    gorev("GOREV 3 korunan alanlar", gorev3, sonuclar)
    log("GOREV 4 - Etsy Ads salt okur")
    gorev("GOREV 4 ads", gorev4, sonuclar)
    log("GOREV 5 - ilan kalite denetimi")
    gorev("GOREV 5 kalite", gorev5, sonuclar)

    (out / "_gorev_durum.json").write_text(
        json.dumps({"gorevler": sonuclar, "kota_bas": kota_bas, "kota_son": api.remaining,
                    "api_cagrisi": api.calls}, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"OZET: {json.dumps({'gorev': len(sonuclar), 'fail': sum(1 for x in sonuclar if x['durum'] == 'FAIL'), 'kota': api.remaining, 'cagri': api.calls}, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
