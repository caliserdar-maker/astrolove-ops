#!/usr/bin/env python3
"""GECE BATCH 2 - ONCELIK 1 + 2: tam Etsy katalog envanteri ve SEO denetimi.

SALT OKUR. Kota korumasi: tum aktif ilanlar tek gecisde
GET /shops/{shop}/listings?includes=Images,Videos ile (100'luk sayfalar, ~6 cagri)
okunur. Dijital dosya teslim durumu ONCEKI kosunun Drive ciktisindan (cache)
gelir; ilan basina yeni cagri YAPILMAZ.

Cikti: full_etsy_catalog.csv/json, catalog_summary.md, seo_audit.csv, seo_summary.md
"""
import argparse
import csv
import html
import json
import os
import pathlib
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "etsy"))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
BURC_RX = re.compile(r"(?<![A-Za-z])(" + "|".join(BURCLAR) + r")(?![A-Za-z])", re.I)
EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
WP_EDISYON = ["Champagne Ivory", "Warm Parchment", "Midnight Blue", "Deep Black"]  # WP'de 4 renk
TAG_MAX, BASLIK_MAX = 20, 140
ONCELIK = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def burclar(metin):
    out = []
    for m in BURC_RX.finditer(metin or ""):
        out.append(m.group(1).capitalize())
        if len(out) == 2:
            break
    return out


def aile(L):
    t = L.get("title") or ""
    if L.get("listing_type") == "physical":
        return "POD baski"
    if re.search(r"wallpaper", t, re.I):
        return "Digital wallpaper"
    if L.get("listing_type") == "download":
        return "Digital wall art"
    return f"Diger ({L.get('listing_type')})"


def edisyon(baslik, ailesi):
    for e in EDISYONLAR:
        if re.search(re.escape(e), baslik, re.I):
            return e
    if ailesi == "Digital wallpaper":
        return "4 renk (tek ilan)"
    if ailesi == "POD baski":
        return "5 renk (varyasyon)"
    return ""


def fiyat(L):
    p = L.get("price") or {}
    try:
        return round(p["amount"] / p["divisor"], 2), p.get("currency_code", "")
    except (KeyError, TypeError, ZeroDivisionError):
        return "", ""


def sayfalar(api, shop, durum="active", max_sayfa=12):
    out, offset = [], 0
    for _ in range(max_sayfa):
        r = api.get(f"/shops/{shop}/listings",
                    params={"state": durum, "limit": 100, "offset": offset,
                            "includes": "Images,Videos"}) or {}
        res = r.get("results") or []
        out += res
        if len(res) < 100:
            break
        offset += 100
    return out


def dosya_cache(yol):
    """Onceki kosunun DIGITAL_FILES_ALL.csv ciktisi -> {listing_id: (sayi, turler, adlar)}."""
    out = {}
    p = pathlib.Path(yol)
    if not p.exists():
        return out
    with open(p, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[str(r.get("listing_id"))] = (r.get("dosya_sayisi") or "", r.get("turler") or "",
                                             r.get("adlar") or "")
    return out


def bulgu_ekle(liste, lid, aile_, oncelik, kod, aciklama):
    liste.append({"id": lid, "urun_ailesi": aile_, "oncelik": oncelik, "kod": kod,
                  "aciklama": aciklama})


def seo_denetle(satirlar, bulgular):
    tag_kullanim = Counter()
    for s in satirlar:
        lid, ail = s["listing_id"], s["urun_ailesi"]
        baslik = s["baslik"]
        desc = s["_desc"]
        tags = s["_tags"]
        for t in tags:
            tag_kullanim[t] += 1
        # baslik
        if len(baslik) > BASLIK_MAX:
            bulgu_ekle(bulgular, lid, ail, "CRITICAL", "BASLIK_UZUN", f"{len(baslik)}>140")
        elif len(baslik) < 40:
            bulgu_ekle(bulgular, lid, ail, "HIGH", "BASLIK_KISA", f"{len(baslik)} karakter")
        ilk40 = baslik[:40]
        b40 = burclar(ilk40)
        if len(b40) < 2:
            bulgu_ekle(bulgular, lid, ail, "HIGH", "ILK40_BURC",
                       f"ilk 40 karakterde iki burc yok: {ilk40!r}")
        if not re.search(r"print|art|poster|wallpaper|download", ilk40, re.I):
            bulgu_ekle(bulgular, lid, ail, "MEDIUM", "ILK40_URUN",
                       f"ilk 40 karakterde urun kelimesi yok: {ilk40!r}")
        # burc cifti
        bb = burclar(baslik)
        if len(bb) < 2:
            bulgu_ekle(bulgular, lid, ail, "CRITICAL", "CIFT_YOK", f"baslikta iki burc yok")
        else:
            for burc in bb:
                if burc.lower() not in desc.lower():
                    bulgu_ekle(bulgular, lid, ail, "HIGH", "ACIKLAMADA_BURC_YOK",
                               f"{burc} aciklamada gecmiyor")
        # etiketler
        if len(tags) != 13:
            bulgu_ekle(bulgular, lid, ail, "HIGH", "TAG_SAYISI", f"{len(tags)}/13")
        if len(set(tags)) != len(tags):
            yin = [t for t, n in Counter(tags).items() if n > 1]
            bulgu_ekle(bulgular, lid, ail, "HIGH", "TAG_YINELENEN", str(yin))
        uzun = [t for t in tags if len(t) > TAG_MAX]
        if uzun:
            bulgu_ekle(bulgular, lid, ail, "CRITICAL", "TAG_UZUN", str(uzun))
        gecersiz = [t for t in tags if not all(c.isalnum() or c in " -'" for c in t)]
        if gecersiz:
            bulgu_ekle(bulgular, lid, ail, "HIGH", "TAG_GECERSIZ_KARAKTER", str(gecersiz))
        bos = [t for t in tags if not t.strip()]
        if bos:
            bulgu_ekle(bulgular, lid, ail, "HIGH", "TAG_BOS", f"{len(bos)} bos tag")
        # urun ailesi - aciklama uyumu
        # Capraz satis blogu (POD ilanini tanitir) fiziksel ifade icerir; cikarilir.
        desc_xsell_yok = re.sub(
            r"(?is)(PREFER IT READY TO HANG.*?)(?=\n\s*(?:✦|GOOD TO KNOW|HOW TO DOWNLOAD|LICENSE|$))",
            "", desc)
        dijital_ifade = bool(re.search(r"instant download|digital download|\bZIP\b|printable file|"
                                       r"no physical item|nothing is shipped", desc, re.I))
        fiziksel_ifade = bool(re.search(r"shipped unframed|made to order|giclee|giclée|"
                                        r"Hahnem|protective tube", desc, re.I))
        if ail == "POD baski":
            if dijital_ifade:
                bulgu_ekle(bulgular, lid, ail, "CRITICAL", "POD_ICINDE_DIJITAL_IFADE",
                           "fiziksel ilanda dijital teslimat ifadesi")
            if not fiziksel_ifade:
                bulgu_ekle(bulgular, lid, ail, "HIGH", "POD_FIZIKSEL_IFADE_YOK",
                           "fiziksel urun ifadesi (unframed/made to order/giclee) yok")
            if s["dijital_fiziksel"] != "physical":
                bulgu_ekle(bulgular, lid, ail, "CRITICAL", "TIP_KARISIKLIGI",
                           f"listing_type={s['dijital_fiziksel']}")
        else:
            if not dijital_ifade:
                bulgu_ekle(bulgular, lid, ail, "HIGH", "DIJITAL_IFADE_YOK",
                           "dijital ilanda teslimat ifadesi yok")
            if re.search(r"shipped unframed|protective tube", desc_xsell_yok, re.I):
                bulgu_ekle(bulgular, lid, ail, "CRITICAL", "DIJITAL_ICINDE_KARGO_IFADESI",
                           "dijital ilanda (capraz satis blogu disinda) fiziksel kargo ifadesi")
            if s["dijital_fiziksel"] != "download":
                bulgu_ekle(bulgular, lid, ail, "CRITICAL", "TIP_KARISIKLIGI",
                           f"listing_type={s['dijital_fiziksel']}")
        # edisyon kurallari
        ed = s["edisyon"]
        if ail == "Digital wall art":
            if ed not in EDISYONLAR:
                bulgu_ekle(bulgular, lid, ail, "HIGH", "EDISYON_OKUNAMADI", f"{ed!r}")
            elif ed.lower() not in desc.lower():
                bulgu_ekle(bulgular, lid, ail, "MEDIUM", "EDISYON_ACIKLAMADA_YOK", ed)
        if ail == "Digital wallpaper":
            if re.search(r"Pure White", baslik + desc, re.I):
                bulgu_ekle(bulgular, lid, ail, "HIGH", "WP_PURE_WHITE",
                           "wallpaper 4 edisyon kurali: Pure White olmamali")
            if not re.search(r"4 Colors|four colors|4 renk", baslik + desc, re.I):
                bulgu_ekle(bulgular, lid, ail, "MEDIUM", "WP_4_RENK_IFADESI",
                           "wallpaper'da 4 renk ifadesi yok")
        if ail == "POD baski" and re.search(r"Pure White", baslik, re.I):
            bulgu_ekle(bulgular, lid, ail, "MEDIUM", "POD_BASLIKTA_EDISYON",
                       "POD basliginda tek edisyon adi (5 varyasyon var)")
        # medya
        if ail == "POD baski":
            if (s["gorsel_sayisi"] or 0) < 10:
                bulgu_ekle(bulgular, lid, ail, "MEDIUM", "GORSEL_AZ", f"{s['gorsel_sayisi']} gorsel")
            if s["video_durumu"] == "yok":
                bulgu_ekle(bulgular, lid, ail, "MEDIUM", "VIDEO_YOK", "POD ilaninda video yok")
        if s["durum"] != "active":
            bulgu_ekle(bulgular, lid, ail, "HIGH", "PASIF", s["durum"])
        if s["dosya_teslim"].startswith("0 dosya") and ail != "POD baski":
            bulgu_ekle(bulgular, lid, ail, "CRITICAL", "DIJITAL_DOSYA_YOK",
                       "dijital ilanda teslim dosyasi kaydi yok")
        elif s["dosya_teslim"].startswith("bilinmiyor") and ail != "POD baski":
            bulgu_ekle(bulgular, lid, ail, "LOW", "DOSYA_TESLIM_BILINMIYOR",
                       "dosya envanteri cache'inde yok; ayri salt okur kosuyla dogrulanmali")
        tire = [c for c in "—–‒―−" if c in baslik + desc]
        if tire:
            nerede = "baslik" if any(c in baslik for c in tire) else "aciklama"
            bulgu_ekle(bulgular, lid, ail, "MEDIUM", "UZUN_TIRE", f"{nerede}: {tire}")
    return tag_kullanim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--files-cache", default="")
    ap.add_argument("--pod-state", default="")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    kota_bas = api.remaining

    log("ONCELIK 1 - tam katalog (includes=Images,Videos)")
    ilanlar = sayfalar(api, shop)
    log(f"   {len(ilanlar)} aktif ilan, {api.calls} cagri, kota {api.remaining}")
    cache = dosya_cache(a.files_cache)
    log(f"   dosya teslim cache: {len(cache)} ilan (yeni cagri yapilmadi)")
    bolumler = {}
    r = api.get(f"/shops/{shop}/sections", ok404=True) or {}
    for sec in r.get("results") or []:
        bolumler[sec.get("shop_section_id")] = sec.get("title")

    satirlar = []
    for L in ilanlar:
        lid = str(L.get("listing_id"))
        ail = aile(L)
        baslik = L.get("title") or ""
        desc = html.unescape(L.get("description") or "")
        tags = [html.unescape(t) for t in (L.get("tags") or [])]
        bb = burclar(baslik)
        f, para = fiyat(L)
        gorseller = L.get("images") or L.get("Images") or []
        videolar = L.get("videos") or L.get("Videos") or []
        dosya = cache.get(lid)
        satirlar.append({
            "listing_id": lid,
            "urun_ailesi": ail,
            "burc_cifti": "_".join(sorted(x.upper() for x in bb)) if len(bb) == 2 else "",
            "edisyon": edisyon(baslik, ail),
            "baslik": baslik,
            "baslik_uzunluk": len(baslik),
            "aciklama_uzunluk": len(desc),
            "etiket_sayisi": len(tags),
            "etiketler": " | ".join(tags),
            "kategori_taxonomy_id": L.get("taxonomy_id"),
            "bolum": bolumler.get(L.get("shop_section_id")) or L.get("shop_section_id") or "",
            "fiyat": f, "para": para,
            "gorsel_sayisi": len(gorseller),
            "video_durumu": "var" if videolar else "yok",
            "dijital_fiziksel": L.get("listing_type") or "",
            "dosya_teslim": (f"{dosya[0]} dosya ({dosya[1]})" if dosya else
                             ("fiziksel urun" if ail == "POD baski"
                              else "bilinmiyor (cache kapsami disi)")),
            "durum": L.get("state") or "",
            "quantity": L.get("quantity"),
            "url": L.get("url") or "",
            "_desc": desc, "_tags": tags,
        })
    satirlar.sort(key=lambda x: (x["urun_ailesi"], x["burc_cifti"], x["edisyon"]))

    sutun = [c for c in satirlar[0] if not c.startswith("_")] if satirlar else []
    with open(out / "full_etsy_catalog.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sutun, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)
    (out / "full_etsy_catalog.json").write_text(
        json.dumps([{k2: v for k2, v in x.items() if not k2.startswith("_") or k2 == "_desc"}
                    for x in satirlar], ensure_ascii=False, indent=1), encoding="utf-8")

    log("ONCELIK 2 - SEO denetimi")
    bulgular = []
    tag_kullanim = seo_denetle(satirlar, bulgular)
    bulgular.sort(key=lambda b: (ONCELIK.index(b["oncelik"]), b["kod"], b["id"]))
    with open(out / "seo_audit.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "urun_ailesi", "oncelik", "kod", "aciklama"])
        w.writeheader()
        for b in bulgular:
            w.writerow(b)

    aile_say = Counter(x["urun_ailesi"] for x in satirlar)
    cift_say = Counter(x["burc_cifti"] for x in satirlar if x["burc_cifti"])
    ed_say = Counter(f"{x['urun_ailesi']} / {x['edisyon']}" for x in satirlar)
    onc_say = Counter(b["oncelik"] for b in bulgular)
    kod_say = Counter(b["kod"] for b in bulgular)
    etkilenen = len({b["id"] for b in bulgular})

    md = [f"# ONCELIK 1 - Tam Etsy katalog envanteri ({simdi()} UTC)", "",
          f"Salt okur. Toplam **{len(satirlar)} aktif ilan**. Etsy cagrisi: {api.calls} "
          f"(kota {kota_bas} -> {api.remaining}). Dosya teslim verisi onceki kosunun "
          f"Drive ciktisindan alindi, ilan basina yeni cagri yapilmadi.", "",
          "## Urun ailesi", "", "| aile | ilan | ort. fiyat | gorsel ort. | video var |",
          "|---|---:|---:|---:|---:|"]
    for ail, n in aile_say.most_common():
        g = [x for x in satirlar if x["urun_ailesi"] == ail]
        fiyatlar = [x["fiyat"] for x in g if isinstance(x["fiyat"], float)]
        md.append(f"| {ail} | {n} | {sum(fiyatlar)/len(fiyatlar):.2f} | "
                  f"{sum(x['gorsel_sayisi'] for x in g)/len(g):.1f} | "
                  f"{sum(1 for x in g if x['video_durumu'] == 'var')} |")
    md += ["", "## Burc cifti kapsami", "",
           f"- Benzersiz cift: **{len(cift_say)}**",
           f"- Cift basina ilan: {Counter(cift_say.values())}",
           f"- Cifti cozulemeyen ilan: {sum(1 for x in satirlar if not x['burc_cifti'])}", "",
           "## Aile / edisyon dagilimi", ""]
    for key, n in sorted(ed_say.items()):
        md.append(f"- {key}: {n}")
    md += ["", "## Dosya teslim durumu (cache)", ""]
    for d, n in Counter(x["dosya_teslim"].split(" (")[0] for x in satirlar).most_common():
        md.append(f"- {d}: {n}")
    (out / "catalog_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    md2 = [f"# ONCELIK 2 - 390+ listing SEO denetimi ({simdi()} UTC)", "",
           f"Denetlenen ilan: **{len(satirlar)}**. Bulgu: **{len(bulgular)}**, "
           f"etkilenen ilan: **{etkilenen}**. Hicbir ilan degistirilmedi.", "",
           "## Oncelik dagilimi", "", "| oncelik | bulgu |", "|---|---:|"]
    for o in ONCELIK:
        md2.append(f"| {o} | {onc_say.get(o, 0)} |")
    md2 += ["", "## Bulgu kodlari", "", "| kod | adet | oncelik |", "|---|---:|---|"]
    for kod, n in kod_say.most_common():
        o = next(b["oncelik"] for b in bulgular if b["kod"] == kod)
        md2.append(f"| {kod} | {n} | {o} |")
    md2 += ["", "## En cok kullanilan 15 etiket", "", "| etiket | ilan |", "|---|---:|"]
    for t, n in tag_kullanim.most_common(15):
        md2.append(f"| {t} | {n} |")
    md2 += ["", "Duzeltme tablosu: `seo_audit.csv` (id, urun_ailesi, oncelik, kod, aciklama).", ""]
    (out / "seo_summary.md").write_text("\n".join(md2) + "\n", encoding="utf-8")

    ozet = {"ilan": len(satirlar), "aile": dict(aile_say), "cift": len(cift_say),
            "bulgu": len(bulgular), "etkilenen_ilan": etkilenen, "oncelik": dict(onc_say),
            "kota_bas": kota_bas, "kota_son": api.remaining, "cagri": api.calls}
    (out / "_oncelik_1_2_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    log(f"OZET: {json.dumps(ozet, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
