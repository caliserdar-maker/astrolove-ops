#!/usr/bin/env python3
"""
DIJITAL 78 v2 - ADIM 1/2: KALACAK.csv v2 + LINK_ESLEME.csv (Etsy cagrisi YOK).

Serdar kararlari (20 Eyl 2026, v1 sonrasi):
  - Satis verisi beklenmiyor: token'da transactions_r kapsami yok, oncelik (b)
    DUSURULDU. v1'deki "GECICI" isaretleri kaldirilir; satis durumu ayri sutunda
    tek satirda belirtilir.
  - 4556456919 ZORLA KALACAK.
  - Linkler Drive'daki crosslink_result.json'dan turetilir (0 Etsy cagrisi).

CAKISMA: 4556456919 ARIES_SCORPIO / Pure White'tir; ayni ciftte koruma altindaki
4555411521 (Deep Black) vardir. Bir ciftte tek ilan kalir, ikisi birden kalamaz.
Bu yuzden IKI dosya uretilir ve karar kullaniciya birakilir:
  KALACAK.csv            koruma kurali (a) kazanir  [birincil]
  KALACAK_ALT_ZORLA.csv  zorlama kazanir            [alternatif]
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
# pod_listing_create.DIGITAL_ORDER ile ayni sira; crosslink_result.json bu sirada yazar.
DIGITAL_ORDER = list(EDISYONLAR)

KORUMALI = {
    "4552582170": ("LEO_PISCES", "Champagne Ivory"),
    "4555411521": ("ARIES_SCORPIO", "Deep Black"),
    "4553832904": ("CAPRICORN_LIBRA", "Midnight Blue"),
}
ZORLA = {"4556456919"}

SATIS_NOTU = ("yok - token'da transactions_r kapsami yok; Serdar 20 Eyl: beklenmiyor, "
              "oncelik (b) dusuruldu")

KAL_SUTUN = ["cift", "kalan_listing_id", "kalan_edisyon", "gerekce", "satis_verisi",
             "kalan_favori", "kalan_views", "kapanacak_1", "kapanacak_2", "kapanacak_3",
             "kapanacak_4", "cift_ilan_sayisi", "not"]
LINK_SUTUN = ["kaynak_tip", "kaynak_listing_id", "kaynak_cift", "eski_listing_id",
              "eski_edisyon", "durum", "kalacak_listing_id", "kalacak_edisyon", "yeni_url"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sec(grup, zorla_kazanir):
    """Oncelik: (a) koruma / zorlama, (c) en cok favori, (d) en cok views,
    (e) esitlikte Midnight Blue, yoksa en kucuk listing_id. (b) satis dusuruldu."""
    korumali = [r for r in grup if r["listing_id"] in KORUMALI]
    zorlanan = [r for r in grup if r["listing_id"] in ZORLA]
    if korumali and zorlanan and korumali[0]["listing_id"] != zorlanan[0]["listing_id"]:
        kazanan = zorlanan[0] if zorla_kazanir else korumali[0]
        kaybeden = korumali[0] if zorla_kazanir else zorlanan[0]
        etiket = "zorlama" if zorla_kazanir else "koruma"
        return kazanan, (f"a) CAKISMA: {etiket} kazandi "
                         f"({kazanan['listing_id']} secildi, {kaybeden['listing_id']} dusuruldu)")
    if zorlanan:
        return zorlanan[0], "a) ZORLA KALACAK (Serdar 20 Eyl)"
    if korumali:
        return korumali[0], "a) koruma altinda"
    en_fav = max((r["num_favorers"] for r in grup), default=0)
    adaylar = [r for r in grup if r["num_favorers"] == en_fav] if en_fav > 0 else list(grup)
    if en_fav > 0 and len(adaylar) == 1:
        return adaylar[0], f"c) en cok favori ({en_fav})"
    en_view = max(r["views"] for r in adaylar)
    adaylar2 = [r for r in adaylar if r["views"] == en_view]
    if len(adaylar2) == 1:
        onek = f"c) favori esit ({en_fav}), " if en_fav > 0 else ""
        return adaylar2[0], f"{onek}d) en cok views ({en_view})"
    mb = [r for r in adaylar2 if r["edisyon"] == "Midnight Blue"]
    if mb:
        return mb[0], f"e) esitlik (favori {en_fav}, views {en_view}) -> Midnight Blue"
    son = min(adaylar2, key=lambda r: int(r["listing_id"]))
    return son, f"e) esitlik (favori {en_fav}, views {en_view}), MB yok -> en kucuk listing_id"


def kalacak_uret(gruplar, zorla_kazanir):
    satirlar, kalan = [], {}
    for cift in sorted(gruplar):
        grup = sorted(gruplar[cift], key=lambda r: EDISYONLAR.index(r["edisyon"])
                      if r["edisyon"] in EDISYONLAR else 9)
        secilen, gerekce = sec(grup, zorla_kazanir)
        kapali = [r for r in grup if r["listing_id"] != secilen["listing_id"]]
        kalan[cift] = secilen
        row = {"cift": cift, "kalan_listing_id": secilen["listing_id"],
               "kalan_edisyon": secilen["edisyon"], "gerekce": gerekce,
               "satis_verisi": SATIS_NOTU, "kalan_favori": secilen["num_favorers"],
               "kalan_views": secilen["views"], "cift_ilan_sayisi": len(grup),
               "not": "" if len(grup) == 5 else f"UYARI: ciftte {len(grup)} ilan (5 bekleniyor)"}
        if "CAKISMA" in gerekce:
            row["not"] = (row["not"] + " | KARAR GEREKIYOR: koruma altindaki 4555411521 ile "
                          "zorlanan 4556456919 ayni cifte dusuyor").strip(" |")
        for i in range(4):
            row[f"kapanacak_{i+1}"] = kapali[i]["listing_id"] if i < len(kapali) else ""
        satirlar.append(row)
    return satirlar, kalan


def yaz(path, satirlar):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=KAL_SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envanter", required=True)
    ap.add_argument("--crosslink", required=True, help="crosslink_result.json (POD -> 5 dijital id)")
    ap.add_argument("--xsell", default="", help="XSELL_STATE.csv (wallpaper capraz link durumu)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- envanter
    gruplar, index = defaultdict(list), {}
    with open(a.envanter, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row = {"listing_id": r["listing_id"], "cift": r["cift"], "edisyon": r["edisyon"],
                   "baslik": r["baslik"], "num_favorers": int(r["num_favorers"] or 0),
                   "views": int(r["views"] or 0)}
            if not row["cift"]:
                continue
            gruplar[row["cift"]].append(row)
            index[row["listing_id"]] = row
    print(f"envanter: {len(index)} dijital ilan, {len(gruplar)} cift", flush=True)

    zorla_bilgi = []
    for lid in sorted(ZORLA):
        r = index.get(lid)
        zorla_bilgi.append(f"{lid} -> {r['cift']} / {r['edisyon']}" if r else f"{lid} -> ENVANTERDE YOK")
        print(f"ZORLA KALACAK: {zorla_bilgi[-1]}", flush=True)

    # ---------------------------------------------------------------- KALACAK
    birincil, kalan = kalacak_uret(gruplar, zorla_kazanir=False)
    alt, kalan_alt = kalacak_uret(gruplar, zorla_kazanir=True)
    yaz(out / "KALACAK.csv", birincil)
    yaz(out / "KALACAK_ALT_ZORLA.csv", alt)
    fark = [(b["cift"], b["kalan_listing_id"], x["kalan_listing_id"])
            for b, x in zip(birincil, alt) if b["kalan_listing_id"] != x["kalan_listing_id"]]
    print(f"KALACAK.csv: {len(birincil)} cift | ALT ile farkli cift: {len(fark)} {fark}", flush=True)

    # ---------------------------------------------------------------- LINK
    cl = json.loads(Path(a.crosslink).read_text(encoding="utf-8"))
    link_satir, pod_cift, eksik = [], {}, []
    for row in cl.get("rows") or []:
        cift, pod_id, durum, notu = row[0], str(row[1]), row[2], row[3]
        pod_cift[cift] = pod_id
        ids = [x.strip() for x in notu.split("|")[-1].split(",") if x.strip().isdigit()]
        if len(ids) != 5:
            eksik.append(f"{cift}: {len(ids)} link")
            continue
        kal = kalan.get(cift)
        for sira, eski in enumerate(ids):
            d = index.get(eski)
            ed = d["edisyon"] if d else DIGITAL_ORDER[sira]
            bozuk = bool(kal) and kal["listing_id"] != eski
            link_satir.append({
                "kaynak_tip": "POD", "kaynak_listing_id": pod_id, "kaynak_cift": cift,
                "eski_listing_id": eski, "eski_edisyon": ed,
                "durum": "KIRILACAK" if bozuk else "KALIYOR",
                "kalacak_listing_id": kal["listing_id"] if kal else "",
                "kalacak_edisyon": kal["edisyon"] if kal else "",
                "yeni_url": f"https://www.etsy.com/listing/{kal['listing_id']}" if kal else "",
            })
    with open(out / "LINK_ESLEME.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LINK_SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in link_satir:
            w.writerow(r)
    kir = sum(1 for r in link_satir if r["durum"] == "KIRILACAK")
    print(f"LINK_ESLEME.csv: {len(link_satir)} POD linki, {kir} kirilacak", flush=True)

    # ---------------------------------------------------------------- wallpaper
    wp_say, wp_durum = 0, Counter()
    if a.xsell and Path(a.xsell).exists():
        with open(a.xsell, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("mode") or "") == "wallpaper":
                    wp_say += 1
                    wp_durum[r.get("durum") or "(bos)"] += 1

    md = [f"# LINK ESLEME OZETI ({simdi()} UTC)", "",
          "Etsy cagrisi: 0. Kaynak: Drive `TEMP/POD_LISTING/CROSSLINK_20260907_1219/apply/"
          "crosslink_result.json` (78 POD ilani x 5 dijital link).", "",
          "## POD -> dijital linkler", "",
          f"- Toplam link: {len(link_satir)} (78 POD ilani x 5 renk)",
          f"- **KIRILACAK: {kir}**  |  KALIYOR: {len(link_satir) - kir}",
          f"- Eksik/kusurlu cift: {len(eksik)} {eksik if eksik else ''}",
          "- Her POD ilaninda 5 linkten 1'i kalan ilana gider, 4'u kapanacak ilana gider.", "",
          "## Wallpaper capraz linkleri", ""]
    if wp_say:
        md += [f"- XSELL_STATE.csv'de `mode=wallpaper` satiri: {wp_say}",
               f"- Durum dagilimi: {dict(wp_durum)}"]
    else:
        md.append("- XSELL_STATE.csv okunamadi veya `mode=wallpaper` satiri yok.")
    md += ["",
           "**BULGU: wallpaper aciklamalarinda DIJITAL POSTER linki YOK.**",
           "Kanit: `scripts/etsy/xsell_links.py` SPEC tablosunda `wallpaper` modunun eklediği",
           "tek blok `PREFER IT ON YOUR WALL?` ve hedefi POD (fiziksel baski) ilanidir;",
           "dijital poster linki eklenmez. `docs/WP_LISTING_TEMPLATE.md` govdesinde de",
           "`etsy.com/listing/` gecen tek satir yoktur. Bu nedenle wallpaper tarafinda",
           "birlestirme sonrasi KIRILACAK link yoktur; ayri bir durum dosyasina gerek kalmadi.",
           "Wallpaper -> POD linkleri bu isten etkilenmez (POD ilanlari kapanmiyor).", "",
           "## Zorla kalacak", ""] + [f"- {x}" for x in zorla_bilgi]
    if fark:
        md += ["", "## CAKISMA", "",
               "Zorlanan ilan koruma altindaki bir ilanla AYNI cifte dusuyor. Iki dosya uretildi:", "",
               "| dosya | cift | kalan |", "|---|---|---|"]
        for c, b, x in fark:
            md.append(f"| KALACAK.csv (birincil, koruma kazanir) | {c} | {b} |")
            md.append(f"| KALACAK_ALT_ZORLA.csv (zorlama kazanir) | {c} | {x} |")
        md.append("")
        md.append("Karar Serdar'a birakildi; baska hicbir cift etkilenmiyor.")
    (out / "LINK_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ozet = {"cift": len(birincil), "link": len(link_satir), "kirilacak": kir,
            "wallpaper_xsell_satiri": wp_say, "wallpaper_dijital_link": 0,
            "zorla": zorla_bilgi, "cakisma": fark,
            "edisyon_dagilimi": dict(Counter(r["kalan_edisyon"] for r in birincil)),
            "edisyon_dagilimi_alt": dict(Counter(r["kalan_edisyon"] for r in alt)),
            "pod_cift": pod_cift}
    (out / "KALACAK_V2_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    print("BITTI | " + json.dumps({k: v for k, v in ozet.items() if k != "pod_cift"},
                                  ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
