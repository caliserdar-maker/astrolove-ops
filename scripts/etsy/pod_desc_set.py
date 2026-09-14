#!/usr/bin/env python3
"""Tek ilanin aciklamasini dosyadaki metinle BIREBIR degistirir (Mo 14 Eyl 2026).

Yalniz `description` yazilir. Baslik, etiket, fiyat, bolum, materials, gorseller,
varyasyonlar ve video degismez. Yazmadan once tum alanlar JSON olarak yedeklenir.
Geri okuma: aciklama birebir mi, diger alanlar ayni mi, state active mi,
metinde uzun tire (em/en dash) var mi.

UYARI (7 Eyl 2026 olcumu): updateListing bir TASLAGI otomatik yayina alir.
Bu betik state'i once okur; taslak ise --allow-draft verilmedikce YAZMAZ.

Kullanim:
  pod_desc_set.py --listing-id 4570110121 --desc-file D.txt --out OUT [--apply]
"""
import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402

UZUN_TIRE = {"—": "EM DASH", "–": "EN DASH", "‒": "FIGURE DASH",
             "―": "HORIZONTAL BAR", "−": "MINUS SIGN"}
ALANLAR = ["title", "tags", "materials", "price", "shop_section_id", "taxonomy_id",
           "who_made", "when_made", "is_supply", "state", "quantity", "url"]


def ozet(L):
    return {k: L.get(k) for k in ALANLAR}


def galeri(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return [(i.get("rank"), i.get("listing_image_id"))
            for i in sorted(r.get("results") or [], key=lambda x: x.get("rank") or 0)]


def var_img(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}
    return sorted((v.get("value"), v.get("image_id")) for v in (r.get("results") or []))


def videolar(api, lid):
    r = api.get(f"/listings/{lid}/videos", ok404=True) or {}
    return sorted((v.get("video_id"), v.get("video_state")) for v in (r.get("results") or []))


def envanter(api, lid):
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    fiyat = []
    for p in inv.get("products") or []:
        for o in p.get("offerings") or []:
            f = o.get("price") or {}
            fiyat.append((p.get("sku"), f.get("amount"), f.get("divisor"), f.get("currency_code"),
                          o.get("quantity"), o.get("is_enabled")))
    return sorted(fiyat)


def esit(a, b):
    """('tam' | 'sondaki_newline' | 'farkli')"""
    if a == b:
        return "tam"
    if a.replace("\r\n", "\n").rstrip("\n") == b.replace("\r\n", "\n").rstrip("\n"):
        return "sondaki_newline"
    return "farkli"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--desc-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-draft", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lid = a.listing_id
    yeni = pathlib.Path(a.desc_file).read_text(encoding="utf-8")
    tire = {UZUN_TIRE[c]: yeni.count(c) for c in UZUN_TIRE if c in yeni}
    if tire:
        raise SystemExit(f"HATA: kaynak metinde uzun tire var: {tire} - DUR")

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]

    # ---------------- yedek (salt okur)
    L = api.get(f"/listings/{lid}") or {}
    once = {"ozet": ozet(L), "description": L.get("description"), "galeri": galeri(api, lid),
            "varyasyon_gorselleri": var_img(api, shop, lid), "videolar": videolar(api, lid),
            "envanter_fiyat": envanter(api, lid)}
    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ypath = out / f"backup_desc_{lid}_{zaman}.json"
    ypath.write_text(json.dumps({"alindi_utc": zaman, "listing_id": lid, "tam_listing": L,
                                 **once}, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"YEDEK: {ypath.name} | state={L.get('state')} baslik={L.get('title')[:60]!r} "
        f"etiket={len(L.get('tags') or [])} fiyat={(L.get('price') or {}).get('amount')} "
        f"bolum={L.get('shop_section_id')} gorsel={len(once['galeri'])}")

    rapor = {"listing_id": lid, "yedek": ypath.name, "state_once": L.get("state"),
             "eski_uzunluk": len(L.get("description") or ""), "yeni_uzunluk": len(yeni),
             "kaynak_dosya": pathlib.Path(a.desc_file).name, "kota_once": api.remaining}
    if esit(L.get("description") or "", yeni) != "farkli":
        rapor["sonuc"] = "DEGISIM YOK (aciklama zaten ayni)"
        (out / "desc_set_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        log(rapor["sonuc"])
        return
    if L.get("state") != "active" and not a.allow_draft:
        raise SystemExit(f"HATA: ilan state={L.get('state')} (active degil) - DUR "
                         f"(updateListing taslagi yayina alir)")
    if not a.apply:
        rapor["sonuc"] = "DRY-RUN (yazma yok)"
        (out / "desc_set_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        log("DRY-RUN: yazma yok.")
        return

    # ---------------- yazma (yalniz description)
    try:
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": yeni})
        rapor["yazim"] = "description tek basina"
    except SystemExit as ex:                       # 6 Eyl notu: bazi uclarda uclu alan gerekir
        if "400" not in str(ex):
            raise
        log(f"400 alindi, who_made/when_made/is_supply ile tekrar deneniyor: {str(ex)[:120]}")
        api.patch(f"/shops/{shop}/listings/{lid}",
                  {"description": yeni, "who_made": L.get("who_made"),
                   "when_made": L.get("when_made"),
                   "is_supply": "true" if L.get("is_supply") else "false"})
        rapor["yazim"] = "description + who_made/when_made/is_supply (degismeyen degerler)"
    time.sleep(3)

    # ---------------- geri okuma
    L2 = api.get(f"/listings/{lid}") or {}
    yazilan = L2.get("description") or ""
    sonra = {"ozet": ozet(L2), "galeri": galeri(api, lid),
             "varyasyon_gorselleri": var_img(api, shop, lid), "videolar": videolar(api, lid),
             "envanter_fiyat": envanter(api, lid)}
    metin = esit(yazilan, yeni)
    yazilan_tire = {UZUN_TIRE[c]: yazilan.count(c) for c in UZUN_TIRE if c in yazilan}
    degisen = {k: (once["ozet"].get(k), sonra["ozet"].get(k))
               for k in ALANLAR if once["ozet"].get(k) != sonra["ozet"].get(k)}
    kontrol = {
        "aciklama_birebir": metin in ("tam", "sondaki_newline"),
        "uzun_tire_yok": not yazilan_tire,
        "baslik_ayni": L2.get("title") == L.get("title"),
        "etiketler_ayni": (L2.get("tags") or []) == (L.get("tags") or []),
        "materials_ayni": (L2.get("materials") or []) == (L.get("materials") or []),
        "fiyat_ayni": (L2.get("price") or {}) == (L.get("price") or {}),
        "envanter_fiyat_ayni": sonra["envanter_fiyat"] == once["envanter_fiyat"],
        "bolum_ayni": L2.get("shop_section_id") == L.get("shop_section_id"),
        "gorseller_ayni": sonra["galeri"] == once["galeri"],
        "varyasyon_gorselleri_ayni": sonra["varyasyon_gorselleri"] == once["varyasyon_gorselleri"],
        "video_ayni": sonra["videolar"] == once["videolar"],
        "state_active": L2.get("state") == "active",
        "state_degismedi": L2.get("state") == L.get("state"),
    }
    rapor.update({"sonuc": "PASS" if all(kontrol.values()) else "FAIL", "kontrol": kontrol,
                  "metin_eslesmesi": metin, "yazilan_uzunluk": len(yazilan),
                  "yazilan_uzun_tire": yazilan_tire, "degisen_alanlar": degisen,
                  "state_sonra": L2.get("state"), "kota_sonra": api.remaining,
                  "api_cagrisi": api.calls})
    (out / "desc_set_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    (out / "description_after.txt").write_text(yazilan, encoding="utf-8")
    log(json.dumps({k: rapor[k] for k in ("sonuc", "kontrol", "metin_eslesmesi", "degisen_alanlar",
                                          "state_sonra", "kota_sonra")}, ensure_ascii=False, indent=1))
    if rapor["sonuc"] != "PASS":
        raise SystemExit("HATA: geri okuma kontrolleri gecmedi")


if __name__ == "__main__":
    main()
