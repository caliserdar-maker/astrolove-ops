#!/usr/bin/env python3
"""POD Gold B kapak isi dogrulamasi (SALT OKUR - Etsy'ye YAZMA YOK).

ADIM 1  state.json kontrolleri (Etsy cagrisi yapilmaz).
ADIM 2  78 ilanin canli geri-okumasi (yalniz GET). ADIM 1 tamamen gecmezse
        hicbir Etsy cagrisi yapilmaz.

Kullanim:
  pod_cover_verify_78.py --state state.json --catalog pod_changes_v2.json \
      --out OUT [--skip-live]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import sys
import time
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    gallery, variation_images, variation_map, video_ids, videos,
)

PILOT_ID = "4570112095"
BEKLENEN_SHA = "51386f4ad727f446deecf55dac4f154ac58934a4ce74d6a61704f68aaf383917"
BEKLENEN_SATIR = 77
BEKLENEN_KURTARILAN = {"4570161266"}
BEKLENEN_MOD = {"standard_13_replace": 44,
                "missing_cover_12_add": 32,
                "missing_cover_12_add_recovered": 1}
GECER = {"PASS", "PASS_RECOVERED"}


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def satir_modu(apply_blok):
    """Kurtarilan satir apply.status'u PASS yazar; ayirt edici alanlar ayri."""
    mod = apply_blok.get("replacement_mode") or ""
    if apply_blok.get("recovered_partial_add") and not mod.endswith("_recovered"):
        mod = "missing_cover_12_add_recovered"
    return mod


def satir_durumu(apply_blok):
    d = apply_blok.get("status")
    if d == "PASS" and satir_modu(apply_blok).endswith("_recovered"):
        return "PASS_RECOVERED"
    return d


def adim1(state, katalog_yolu):
    """Donus: (kontroller, tamam_mi, ozet)."""
    k = []

    def ek(ad, gecti, beklenen, gercek):
        k.append({"kontrol": ad, "sonuc": "PASS" if gecti else "FAIL",
                  "beklenen": str(beklenen)[:180], "gercek": str(gercek)[:180]})

    ek("state.catalog_sha256", state.get("catalog_sha256") == BEKLENEN_SHA,
       BEKLENEN_SHA, state.get("catalog_sha256"))
    kat_sha = sha256(katalog_yolu)
    ek("katalog dosyasi sha256", kat_sha == BEKLENEN_SHA, BEKLENEN_SHA, kat_sha)
    ek("state.pilot_listing_id", str(state.get("pilot_listing_id")) == PILOT_ID,
       PILOT_ID, state.get("pilot_listing_id"))

    rows = state.get("rows") or {}
    ek("rows satir sayisi", len(rows) == BEKLENEN_SATIR, BEKLENEN_SATIR, len(rows))
    ek("pilot rows disinda", PILOT_ID not in {str(x) for x in rows},
       "pilot yok", "pilot VAR" if PILOT_ID in {str(x) for x in rows} else "pilot yok")

    applyler = {str(i): (r.get("apply") or {}) for i, r in rows.items()}
    durumlar = {i: satir_durumu(a) for i, a in applyler.items()}
    kotu = {i: d for i, d in durumlar.items() if d not in GECER}
    ek("her satir apply PASS/PASS_RECOVERED", not kotu, "hepsi PASS",
       kotu or "hepsi PASS")

    kurtarilan = {i for i, d in durumlar.items() if d == "PASS_RECOVERED"}
    ek("PASS_RECOVERED yalniz 4570161266", kurtarilan == BEKLENEN_KURTARILAN,
       sorted(BEKLENEN_KURTARILAN), sorted(kurtarilan))

    dagilim = Counter(satir_modu(a) for a in applyler.values())
    ek("mod dagilimi", dict(dagilim) == BEKLENEN_MOD, BEKLENEN_MOD, dict(dagilim))

    fc_kotu = {}
    for i, a in applyler.items():
        fc = a.get("final_checks") or {}
        if not fc or not all(bool(v) for v in fc.values()):
            fc_kotu[i] = {x: v for x, v in fc.items() if not v} or "final_checks YOK"
    ek("her satir final_checks tumu true", not fc_kotu, "hepsi true",
       fc_kotu or "hepsi true")

    ek("state.apply_complete", state.get("apply_complete") is True, True,
       state.get("apply_complete"))
    ek("state.dry_run_complete", state.get("dry_run_complete") is True, True,
       state.get("dry_run_complete"))
    ek("basarisiz satir sayisi", len(kotu) == 0, 0, len(kotu))

    tamam = all(x["sonuc"] == "PASS" for x in k)
    return k, tamam, {"dagilim": dict(dagilim), "kurtarilan": sorted(kurtarilan),
                      "satir": len(rows)}


def beklenen_degerler(row):
    """state.json satirindan beklenen canli degerler."""
    a = row.get("apply") or {}
    d = row.get("dry_run") or {}
    imza = (d.get("snapshot_signature") or {})
    galeri = a.get("gallery_after") or []
    return {
        "yeni_kapak_id": str(a.get("new_cover_id") or ""),
        "gorsel_sayisi": len(galeri),
        "video_ids": [str(x) for x in (a.get("video_ids_after") or [])],
        "varyasyon": sorted(tuple(str(y) for y in x)
                            for x in (imza.get("variation_images") or [])),
        "baslik": imza.get("title") or "",
    }


def eta(i, toplam, t0):
    gecen = time.time() - t0
    hiz = gecen / i if i else 0
    kalan = hiz * (toplam - i)
    return (f"[{i}/{toplam} %{i / toplam * 100:4.1f}] gecen {gecen / 60:5.1f} dk, "
            f"kalan ~{kalan / 60:5.1f} dk")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-live", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    state = json.loads(pathlib.Path(a.state).read_text(encoding="utf-8"))
    katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))

    log(f"ADIM 1 - state dogrulamasi ({simdi()} UTC)")
    kontroller, tamam1, ozet = adim1(state, a.catalog)
    for x in kontroller:
        log(f"  [{x['sonuc']}] {x['kontrol']}: beklenen={x['beklenen']} "
            f"gercek={x['gercek']}")
    with open(out / "ADIM1_state_kontrol.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["kontrol", "sonuc", "beklenen", "gercek"])
        w.writeheader()
        for x in kontroller:
            w.writerow(x)
    if not tamam1:
        log("ADIM 1 FAIL - Etsy'ye HICBIR cagri yapilmadi, ADIM 2 atlandi.")
        (out / "SONUC.json").write_text(json.dumps(
            {"adim1": "FAIL", "adim2": "ATLANDI",
             "basarisiz": [x for x in kontroller if x["sonuc"] == "FAIL"]},
            ensure_ascii=False, indent=2), encoding="utf-8")
        return 2
    log(f"ADIM 1 PASS - {ozet}")
    if a.skip_live:
        return 0

    # ---------------------------------------------------------------- ADIM 2
    rows = {str(i): r for i, r in (state.get("rows") or {}).items()}
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    log(f"ADIM 2 - canli geri-okuma (yalniz GET). Kota ONCE: {kota_once}")

    hedefler = [(str(r["id"]), str(r.get("title") or "")) for r in katalog]
    toplam = len(hedefler)
    t0 = time.time()
    satirlar, hatali = [], []
    for i, (lid, kat_baslik) in enumerate(hedefler, 1):
        row = rows.get(lid)
        bek = beklenen_degerler(row) if row else None
        listing = api.get(f"/listings/{lid}", ok404=True) or {}
        gorseller = gallery(api, lid)
        videolar = videos(api, lid)
        varyasyonlar = variation_images(api, shop, lid)
        rank1 = gorseller[0] if gorseller else {}
        canli = {
            "state": listing.get("state"),
            "baslik": listing.get("title") or "",
            "kapak_id": str(rank1.get("listing_image_id") or ""),
            "kapak_px": f"{rank1.get('full_width')}x{rank1.get('full_height')}",
            "gorsel_sayisi": len(gorseller),
            "video_ids": [str(x) for x in video_ids(videolar)],
            "varyasyon": sorted(tuple(str(y) for y in x)
                                for x in variation_map(varyasyonlar)),
        }
        k = {
            "listing_id": lid,
            "kaynak": "state.json" if row else "state.json YOK (pilot)",
            "state_active": canli["state"] == "active",
            "baslik_ayni": (canli["baslik"] == bek["baslik"]) if bek
                           else (canli["baslik"] == kat_baslik),
            "kapak_2400x3000": canli["kapak_px"] == "2400x3000",
            "kapak_id_ayni": (canli["kapak_id"] == bek["yeni_kapak_id"]) if bek
                             else "KAYNAK_YOK",
            "gorsel_sayisi_13": canli["gorsel_sayisi"] == 13,
            "video_1_adet": len(canli["video_ids"]) == 1,
            "video_id_ayni": (canli["video_ids"] == bek["video_ids"]) if bek
                             else "KAYNAK_YOK",
            "varyasyon_5_adet": len(canli["varyasyon"]) == 5,
            "varyasyon_ayni": (canli["varyasyon"] == bek["varyasyon"]) if bek
                              else "KAYNAK_YOK",
            "canli_state": canli["state"],
            "canli_kapak_id": canli["kapak_id"],
            "beklenen_kapak_id": bek["yeni_kapak_id"] if bek else "",
            "canli_kapak_px": canli["kapak_px"],
            "canli_gorsel_sayisi": canli["gorsel_sayisi"],
            "canli_video_id": ",".join(canli["video_ids"]),
            "beklenen_video_id": ",".join(bek["video_ids"]) if bek else "",
            "canli_varyasyon_sayisi": len(canli["varyasyon"]),
            "kota": api.remaining,
        }
        bayrak = [x for x in ("state_active", "baslik_ayni", "kapak_2400x3000",
                              "kapak_id_ayni", "gorsel_sayisi_13", "video_1_adet",
                              "video_id_ayni", "varyasyon_5_adet", "varyasyon_ayni")
                  if k[x] is False]
        k["sonuc"] = "PASS" if not bayrak else "FAIL"
        k["bulgular"] = ";".join(bayrak)
        if bayrak:
            hatali.append(k)
        satirlar.append(k)
        log(f"{eta(i, toplam, t0)} {lid}: {k['sonuc']}"
            f"{' -> ' + k['bulgular'] if bayrak else ''} | kota={api.remaining}")

    kota_sonra = api.remaining
    sut = ["listing_id", "sonuc", "bulgular", "kaynak", "state_active", "baslik_ayni",
           "kapak_2400x3000", "kapak_id_ayni", "gorsel_sayisi_13", "video_1_adet",
           "video_id_ayni", "varyasyon_5_adet", "varyasyon_ayni", "canli_state",
           "canli_kapak_id", "beklenen_kapak_id", "canli_kapak_px",
           "canli_gorsel_sayisi", "canli_video_id", "beklenen_video_id",
           "canli_varyasyon_sayisi", "kota"]
    ad = f"VERIFY_{datetime.now(timezone.utc):%Y-%m-%d}.csv"
    with open(out / ad, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sut, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)
    ozet2 = {"adim1": "PASS", "adim2": "PASS" if not hatali else "FAIL",
             "ilan": toplam, "gecen": toplam - len(hatali), "kalan": len(hatali),
             "kota_once": kota_once, "kota_sonra": kota_sonra,
             "kaynagi_olmayan": [x["listing_id"] for x in satirlar
                                 if x["kaynak"] != "state.json"],
             "basarisiz": [{"listing_id": x["listing_id"], "bulgular": x["bulgular"]}
                           for x in hatali]}
    (out / "SONUC.json").write_text(json.dumps(ozet2, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    log(json.dumps(ozet2, ensure_ascii=False))
    return 0 if not hatali else 3


if __name__ == "__main__":
    sys.exit(main())
