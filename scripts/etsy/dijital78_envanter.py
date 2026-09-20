#!/usr/bin/env python3
"""
DIJITAL 390 -> 78 BIRLESTIRME PLANI, ADIM 1/2/4/6 - SALT OKUR (Serdar 20 Eyl 2026).
Etsy'ye HICBIR yazma yok; yalniz toplu GET uclari kullanilir.

Cagri butcesi (varsayilan 60):
  - GET /shops/{id}/sections                         1
  - GET /shops/{id}/listings?state=...&limit=100     durum basina sayfa
  - GET /shops/{id}/receipts?limit=100               sayfa basina 1
  - GET /shops/{id}/listings/{lid}/files             yalniz ORNEKLEM (--ornek-dosya)
Ilan bazinda tek tek listing okuma YOK.

Ciktilar (--out):
  ENVANTER.csv      390 dijital poster ilani, tam alan seti
  KALACAK.csv       78 cift icin kalacak ilan + gerekce + kapanacak 4 id
  LINK_ESLEME.csv   POD/wallpaper aciklamalarindaki dijital linkler -> kalacak id
  FIYAT_VERI.md     fiyat/indirim verisi (oneri yok)
  AYRIM.md          urun tipi ayrim kurali ve sayimlar
  ETSY_HAM.json     sonraki adimlar icin ham ozet (sir icermez)
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
EDISYON_KISA = {"Champagne Ivory": "CI", "Pure White": "PW", "Warm Parchment": "WP",
                "Midnight Blue": "MB", "Deep Black": "DB"}
DURUMLAR = ["active", "draft", "inactive", "expired", "sold_out"]
LINK_RX = re.compile(r"etsy\.com/listing/(\d+)")

# Serdar 20 Eyl 2026: koruma altindaki 3 ilan kosulsuz kalir.
KORUMALI = {
    "4552582170": ("LEO_PISCES", "Champagne Ivory"),
    "4555411521": ("ARIES_SCORPIO", "Deep Black"),
    "4553832904": ("CAPRICORN_LIBRA", "Midnight Blue"),
}

ENV_SUTUN = ["listing_id", "cift", "edisyon", "edisyon_kisa", "baslik", "state", "bolum_id",
             "bolum", "fiyat", "para", "views", "num_favorers", "satis_adedi", "etiket_sayisi",
             "olusturma", "url"] + [f"tag{i}" for i in range(1, 14)]
KAL_SUTUN = ["cift", "kalan_listing_id", "kalan_edisyon", "gerekce", "kalan_satis",
             "kalan_favori", "kalan_views", "kapanacak_1", "kapanacak_2", "kapanacak_3",
             "kapanacak_4", "cift_ilan_sayisi", "not"]
LINK_SUTUN = ["kaynak_tip", "kaynak_listing_id", "kaynak_baslik", "eski_listing_id",
              "eski_cift", "eski_edisyon", "durum", "kalacak_listing_id", "kalacak_edisyon"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def tarih(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def fiyat(L):
    p = L.get("price") or {}
    try:
        return round(p["amount"] / p["divisor"], 2), p.get("currency_code", "")
    except (KeyError, TypeError, ZeroDivisionError):
        return None, ""


def burclar(baslik):
    """Basliktaki ilk iki burc adi (sirayla, tekrar dahil)."""
    bulunan = []
    for m in re.finditer(r"\b(" + "|".join(BURCLAR) + r")\b", baslik, re.I):
        bulunan.append(m.group(1).capitalize())
        if len(bulunan) == 2:
            break
    return bulunan


def cift_anahtar(bs):
    return "_".join(sorted(x.upper() for x in bs)) if len(bs) == 2 else ""


def edisyon(baslik):
    for e in EDISYONLAR:
        if re.search(re.escape(e), baslik, re.I):
            return e
    return ""


def siniflandir(L):
    """AYRIM KURALI (olculebilir, tahmin yok):
    1) listing_type == 'physical'            -> POD baski        (78)
    2) baslikta 'wallpaper' gecer            -> Duvar kagidi     (78)
    3) listing_type == 'download' ve 1-2 yok -> Dijital poster   (390)
    4) digeri                                -> Siniflanamadi
    """
    t = L.get("title") or ""
    tip = L.get("listing_type") or ""
    if tip == "physical":
        return "POD baski"
    if re.search(r"wallpaper", t, re.I):
        return "Duvar kagidi"
    if tip == "download":
        return "Dijital poster"
    return f"Siniflanamadi ({tip or 'tip yok'})"


# --------------------------------------------------------------- Etsy okuma
def ilanlar_durum(api, shop, durum, butce, max_sayfa=12):
    out, offset = [], 0
    for _ in range(max_sayfa):
        if api.calls >= butce:
            log(f"   BUTCE: {durum} yarim kaldi ({len(out)} ilan)")
            return out, False
        r = api.get(f"/shops/{shop}/listings", params={"state": durum, "limit": 100,
                                                       "offset": offset}, ok404=True) or {}
        res = r.get("results") or []
        for L in res:
            L["_state"] = durum
        out += res
        if len(res) < 100:
            return out, True
        offset += 100
    return out, False


def satislar(api, shop, sayfa_siniri, butce):
    say, makbuz, sayfa = defaultdict(int), 0, 0
    offset = 0
    for _ in range(sayfa_siniri):
        if api.calls >= butce:
            return say, makbuz, f"butce siniri - {sayfa} sayfa okundu (EKSIK)"
        r = api.get(f"/shops/{shop}/receipts", params={"limit": 100, "offset": offset},
                    ok404=True) or {}
        res = r.get("results") or []
        sayfa += 1
        for rc in res:
            makbuz += 1
            for tr in rc.get("transactions") or []:
                lid = str(tr.get("listing_id") or "")
                if lid:
                    say[lid] += int(tr.get("quantity") or 1)
        if len(res) < 100:
            return say, makbuz, f"tam ({sayfa} sayfa)"
        offset += 100
    return say, makbuz, f"{sayfa_siniri} sayfa siniri (EKSIK olabilir)"


# --------------------------------------------------------------- 2) secim
def kalan_sec(grup, satis):
    """Serdar onceligi: (a) korumali, (b) satisi olan, (c) en cok favori,
    (d) en cok views, (e) esitlikte Midnight Blue. Hepsi esitse en kucuk id."""
    for s in grup:
        if s["listing_id"] in KORUMALI:
            return s, "a) koruma altinda"
    satisli = [s for s in grup if (satis.get(s["listing_id"], 0) or 0) > 0]
    if satisli:
        en = max(satisli, key=lambda s: (satis.get(s["listing_id"], 0),
                                         s["num_favorers"] or 0, s["views"] or 0,
                                         s["edisyon"] == "Midnight Blue",
                                         -int(s["listing_id"])))
        return en, f"b) satis gecmisi ({satis.get(en['listing_id'], 0)} adet)"
    en_fav = max((s["num_favorers"] or 0) for s in grup)
    if en_fav > 0:
        adaylar = [s for s in grup if (s["num_favorers"] or 0) == en_fav]
        if len(adaylar) == 1:
            return adaylar[0], f"c) en cok favori ({en_fav})"
    else:
        adaylar = list(grup)
    en_view = max((s["views"] or 0) for s in adaylar)
    adaylar2 = [s for s in adaylar if (s["views"] or 0) == en_view]
    if len(adaylar2) == 1:
        gerekce = (f"c) favori esit ({en_fav}), d) en cok views ({en_view})"
                   if en_fav > 0 else f"d) en cok views ({en_view})")
        return adaylar2[0], gerekce
    mb = [s for s in adaylar2 if s["edisyon"] == "Midnight Blue"]
    if mb:
        return mb[0], f"e) esitlik (favori {en_fav}, views {en_view}) -> Midnight Blue"
    son = min(adaylar2, key=lambda s: int(s["listing_id"]))
    return son, (f"e) esitlik (favori {en_fav}, views {en_view}), MB yok -> "
                 f"en kucuk listing_id")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--receipt-pages", type=int, default=10)
    ap.add_argument("--ornek-dosya", type=int, default=0,
                    help="Kac ilanin dijital dosyalari canli dogrulansin (cagri harcar)")
    ap.add_argument("--dfiles", default="", help="DIGITAL_FILES_ALL.csv (Drive anlik goruntusu)")
    ap.add_argument("--pin-map", default="", help="PIN_LISTING_MAP.csv (pair,edition,listing_id)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    mask(shop)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    t0 = time.time()
    butce = a.max_calls

    log(f"1) Bolumler (butce {butce})")
    br = api.get(f"/shops/{shop}/sections", ok404=True) or {}
    bolum = {str(x.get("shop_section_id")): x.get("title") for x in (br.get("results") or [])}
    log(f"   {len(bolum)} bolum | cagri {api.calls}")

    # Kalan butce rezervi: makbuz sayfalari + canli dosya ornegi icin yer birak.
    rezerv = a.receipt_pages + a.ornek_dosya
    log(f"2) Ilanlar (durum durum, limit=100) | ilan butcesi {butce - rezerv}")
    hepsi, tam_durum = [], {}
    for d in DURUMLAR:
        ilan, tam = ilanlar_durum(api, shop, d, butce - rezerv)
        tam_durum[d] = tam
        hepsi += ilan
        log(f"   {d:9s} {len(ilan):4d} ilan | cagri {api.calls} | gecen {time.time()-t0:.0f}s")

    log("3) Makbuzlar (satis gecmisi)")
    sat_ham, makbuz, sat_not = satislar(api, shop, a.receipt_pages,
                                        butce - a.ornek_dosya)
    log(f"   makbuz {makbuz} | {sat_not} | cagri {api.calls}")

    # ------------------------------------------------------------- siniflama
    satirlar, tip_say = [], Counter()
    pod_ilan, wp_ilan, siniflanamayan = [], [], []
    for L in hepsi:
        tipi = siniflandir(L)
        tip_say[f"{tipi} / {L.get('_state')}"] += 1
        if tipi == "POD baski":
            pod_ilan.append(L)
            continue
        if tipi == "Duvar kagidi":
            wp_ilan.append(L)
            continue
        if tipi != "Dijital poster":
            siniflanamayan.append(L)
            continue
        bas = L.get("title") or ""
        bs = burclar(bas)
        f, para = fiyat(L)
        tags = list(L.get("tags") or [])
        lid = str(L.get("listing_id"))
        ed = edisyon(bas)
        row = {
            "listing_id": lid, "cift": cift_anahtar(bs), "edisyon": ed,
            "edisyon_kisa": EDISYON_KISA.get(ed, ""), "baslik": bas,
            "state": L.get("_state"), "bolum_id": L.get("shop_section_id") or "",
            "bolum": bolum.get(str(L.get("shop_section_id")), ""),
            "fiyat": f, "para": para, "views": L.get("views") or 0,
            "num_favorers": L.get("num_favorers") or 0,
            "satis_adedi": sat_ham.get(lid, 0), "etiket_sayisi": len(tags),
            "olusturma": tarih(L.get("original_creation_timestamp")),
            "url": L.get("url") or "",
        }
        for i in range(13):
            row[f"tag{i+1}"] = tags[i] if i < len(tags) else ""
        satirlar.append(row)

    satirlar.sort(key=lambda x: (x["cift"], x["edisyon"]))
    with open(out / "ENVANTER.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ENV_SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"   ENVANTER.csv: {len(satirlar)} dijital poster ilani")

    # ------------------------------------------------------------- 2) kalacak
    gruplar = defaultdict(list)
    for r in satirlar:
        gruplar[r["cift"] or "(CIFT_YOK)"].append(r)

    kal_satir, kapanacak, kalan_idler = [], [], {}
    for cift in sorted(gruplar):
        grup = sorted(gruplar[cift], key=lambda x: x["edisyon"])
        if cift == "(CIFT_YOK)":
            for r in grup:
                kal_satir.append({"cift": "(CIFT_YOK)", "kalan_listing_id": r["listing_id"],
                                  "kalan_edisyon": r["edisyon"], "gerekce": "ELDE INCELE",
                                  "kalan_satis": r["satis_adedi"], "kalan_favori": r["num_favorers"],
                                  "kalan_views": r["views"], "cift_ilan_sayisi": len(grup),
                                  "not": "basliktan iki burc cikarilamadi"})
            continue
        secilen, gerekce = kalan_sec(grup, {r["listing_id"]: r["satis_adedi"] for r in grup})
        kapali = [r for r in grup if r["listing_id"] != secilen["listing_id"]]
        kapanacak += kapali
        kalan_idler[cift] = secilen
        row = {"cift": cift, "kalan_listing_id": secilen["listing_id"],
               "kalan_edisyon": secilen["edisyon"], "gerekce": gerekce,
               "kalan_satis": secilen["satis_adedi"], "kalan_favori": secilen["num_favorers"],
               "kalan_views": secilen["views"], "cift_ilan_sayisi": len(grup),
               "not": "" if len(grup) == 5 else f"UYARI: ciftte {len(grup)} ilan (5 bekleniyor)"}
        for i in range(4):
            row[f"kapanacak_{i+1}"] = kapali[i]["listing_id"] if i < len(kapali) else ""
        kal_satir.append(row)

    with open(out / "KALACAK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=KAL_SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in kal_satir:
            w.writerow(r)
    log(f"   KALACAK.csv: {len([r for r in kal_satir if r['cift'] != '(CIFT_YOK)'])} cift, "
        f"{len(kapanacak)} ilan devre disi birakilacak")

    # ------------------------------------------------------------- 4) linkler
    id_index = {r["listing_id"]: r for r in satirlar}
    link_satir = []
    for tip, kume in (("POD", pod_ilan), ("Wallpaper", wp_ilan)):
        for L in kume:
            desc = html.unescape(L.get("description") or "")
            for m in LINK_RX.finditer(desc):
                eski = m.group(1)
                d = id_index.get(eski)
                if not d:
                    continue  # dijital poster olmayan link (POD/wallpaper capraz)
                kalan = kalan_idler.get(d["cift"])
                bozuk = bool(kalan) and kalan["listing_id"] != eski
                link_satir.append({
                    "kaynak_tip": tip, "kaynak_listing_id": str(L.get("listing_id")),
                    "kaynak_baslik": (L.get("title") or "")[:90],
                    "eski_listing_id": eski, "eski_cift": d["cift"],
                    "eski_edisyon": d["edisyon"],
                    "durum": "KIRILACAK" if bozuk else "KALIYOR",
                    "kalacak_listing_id": kalan["listing_id"] if kalan else "",
                    "kalacak_edisyon": kalan["edisyon"] if kalan else "",
                })
    with open(out / "LINK_ESLEME.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LINK_SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in link_satir:
            w.writerow(r)
    kirilacak = sum(1 for r in link_satir if r["durum"] == "KIRILACAK")
    log(f"   LINK_ESLEME.csv: {len(link_satir)} dijital link, {kirilacak} kirilacak")

    # ------------------------------------------------------------- 6) fiyat
    dij_f = Counter(f"{r['fiyat']} {r['para']}" for r in satirlar)
    wp_f = Counter()
    for L in wp_ilan:
        f, p = fiyat(L)
        wp_f[f"{f} {p}"] += 1
    pod_f = Counter()
    for L in pod_ilan:
        f, p = fiyat(L)
        pod_f[f"{f} {p}"] += 1
    fmd = [f"# FIYAT VERISI (salt okur, {simdi()} UTC)", "",
           "Yalniz olculen veri. Oneri yok.", "",
           "## Dijital poster (tek renk edisyonu, liste fiyati)", ""]
    for k2, v in dij_f.most_common():
        fmd.append(f"- {k2} : {v} ilan")
    fmd += ["", "## Duvar kagidi (wallpaper) 5'li paket", ""]
    for k2, v in wp_f.most_common():
        fmd.append(f"- {k2} : {v} ilan")
    fmd += ["", "## POD baski (karsilastirma icin)", ""]
    for k2, v in pod_f.most_common():
        fmd.append(f"- {k2} : {v} ilan")
    fmd += ["", "## Aktif indirim", "",
            "- Kod: ASTROLOVE40B, %40, yalniz 6 dijital bolum (468 ilan: 390 poster + 78 wallpaper).",
            "- POD ilanlari indirime DAHIL DEGIL (B97/B98, 7 Eyl 2026 karari).",
            "- Yenileme: ~6 Ekim 2026.",
            "- Kaynak: docs/start_here/B97.txt, B98.txt. Indirim orani Etsy API'de okunmuyor;",
            "  bu satirlar magaza panelinde dogrulanmis karar kaydindan gelir.",
            "", "## Not", "",
            "- Etsy API indirim/kupon ucu vermez; yukaridaki fiyatlar LISTE fiyatlaridir.",
            "- Indirimli gorunen fiyat = liste x 0.60 (dijital bolumler icin)."]
    (out / "FIYAT_VERI.md").write_text("\n".join(fmd) + "\n", encoding="utf-8")

    # ------------------------------------------------------------- ayrim raporu
    amd = [f"# URUN TIPI AYRIM KURALI ve SAYIMLAR ({simdi()} UTC)", "",
           "Kural (sirayla uygulanir, tahmin yok):", "",
           "1. `listing_type == 'physical'` -> POD baski",
           "2. baslikta `wallpaper` gecer -> Duvar kagidi",
           "3. `listing_type == 'download'` ve 1-2 uymuyor -> Dijital poster",
           "4. hicbiri -> Siniflanamadi (elle incelenir)", "",
           "## Tip / durum dagilimi", "", "| tip / state | ilan |", "|---|---:|"]
    for k2, v in sorted(tip_say.items()):
        amd.append(f"| {k2} | {v} |")
    amd += ["", f"- Toplam okunan ilan: {len(hepsi)}",
            f"- Dijital poster: {len(satirlar)}",
            f"- POD: {len(pod_ilan)} | Wallpaper: {len(wp_ilan)} | Siniflanamadi: {len(siniflanamayan)}",
            f"- Durum sayfalari tam mi: {json.dumps(tam_durum)}",
            f"- Satis okuma: {sat_not}, makbuz {makbuz}",
            f"- Etsy cagrisi: {api.calls}, kalan gunluk kota: {api.remaining}"]
    if siniflanamayan:
        amd += ["", "## Siniflanamayan ilanlar", ""]
        for L in siniflanamayan[:40]:
            amd.append(f"- {L.get('listing_id')} | {L.get('listing_type')} | {(L.get('title') or '')[:80]}")
    (out / "AYRIM.md").write_text("\n".join(amd) + "\n", encoding="utf-8")

    # ------------------------------------------------------------- ornek dosya dogrulamasi
    dogrulama = []
    if a.ornek_dosya > 0:
        anlik = {}
        if a.dfiles and Path(a.dfiles).exists():
            with open(a.dfiles, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    anlik[str(r.get("listing_id"))] = r
        # her edisyondan esit sayida ornek
        per = max(1, a.ornek_dosya // 5)
        ornekler = []
        for ed in EDISYONLAR:
            ornekler += [r for r in satirlar if r["edisyon"] == ed][:per]
        for r in ornekler[:a.ornek_dosya]:
            if api.calls >= butce:
                log("   BUTCE: ornek dosya dogrulamasi yarim kaldi")
                break
            fr = api.get(f"/shops/{shop}/listings/{r['listing_id']}/files", ok404=True) or {}
            adlar = [f.get("filename") or "" for f in (fr.get("results") or [])]
            boy = [f.get("size_bytes") for f in (fr.get("results") or [])]
            ref = anlik.get(r["listing_id"])
            uyum = ""
            if ref:
                uyum = ("AYNI" if "|".join(adlar) == (ref.get("adlar") or "") and
                        "|".join(str(b) for b in boy) == (ref.get("boyutlar") or "")
                        else "FARKLI")
            dogrulama.append({"listing_id": r["listing_id"], "cift": r["cift"],
                              "edisyon": r["edisyon"], "dosya_sayisi": len(adlar),
                              "adlar": "|".join(adlar),
                              "boyutlar": "|".join(str(b) for b in boy),
                              "anlik_goruntu_uyumu": uyum})
        if dogrulama:
            with open(out / "DOSYA_ORNEK_DOGRULAMA.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dogrulama[0].keys()))
                w.writeheader()
                for r in dogrulama:
                    w.writerow(r)
            log(f"   DOSYA_ORNEK_DOGRULAMA.csv: {len(dogrulama)} ilan, "
                f"FARKLI={sum(1 for x in dogrulama if x['anlik_goruntu_uyumu']=='FARKLI')}")

    # --------------------------------------------------------- 4b) Pinterest
    pin_kirilacak = 0
    if a.pin_map and Path(a.pin_map).exists():
        pin_satir = []
        with open(a.pin_map, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                eski = str(r.get("listing_id") or "").strip()
                d = id_index.get(eski)
                cift = d["cift"] if d else ""
                kalan = kalan_idler.get(cift)
                bozuk = bool(kalan) and kalan["listing_id"] != eski
                pin_kirilacak += 1 if bozuk else 0
                pin_satir.append({
                    "pin_pair": r.get("pair", ""), "pin_edition": r.get("edition", ""),
                    "eski_listing_id": eski, "eski_cift": cift,
                    "eski_edisyon": d["edisyon"] if d else "(envanterde yok)",
                    "durum": "KIRILACAK" if bozuk else ("KALIYOR" if kalan else "BILINMIYOR"),
                    "kalacak_listing_id": kalan["listing_id"] if kalan else "",
                    "kalacak_edisyon": kalan["edisyon"] if kalan else "",
                    "yeni_url": (f"https://www.etsy.com/listing/{kalan['listing_id']}"
                                 if kalan else ""),
                })
        with open(out / "PIN_ESLEME.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(pin_satir[0].keys()) if pin_satir else
                               ["pin_pair"], extrasaction="ignore")
            w.writeheader()
            for r in pin_satir:
                w.writerow(r)
        log(f"   PIN_ESLEME.csv: {len(pin_satir)} pin kaydi, {pin_kirilacak} kirilacak")
    else:
        log("   PIN_ESLEME.csv: PIN_LISTING_MAP.csv yok, atlandi")

    ham = {
        "uretim": simdi(), "etsy_cagri": api.calls, "kalan_kota": api.remaining,
        "dijital_poster": len(satirlar), "pod": len(pod_ilan), "wallpaper": len(wp_ilan),
        "siniflanamadi": len(siniflanamayan), "cift_sayisi": len(kalan_idler),
        "kapanacak": len(kapanacak), "link_toplam": len(link_satir), "link_kirilacak": kirilacak,
        "pin_kirilacak": pin_kirilacak,
        "durum_tam": tam_durum, "satis_notu": sat_not, "makbuz": makbuz,
        "kalan": {c: {"listing_id": r["listing_id"], "edisyon": r["edisyon"],
                      "baslik": r["baslik"]} for c, r in kalan_idler.items()},
    }
    (out / "ETSY_HAM.json").write_text(json.dumps(ham, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    log(f"BITTI | cagri {api.calls} | kota {api.remaining} | sure {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
