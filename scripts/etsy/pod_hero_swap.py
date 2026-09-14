#!/usr/bin/env python3
"""POD ilaninda 5 edisyon hero'sunu ve videoyu KIRPILMIS surumleriyle degistirir.

Mo 14 Eyl 2026, tek ilan (Aquarius-Aquarius 4570110121).
- Her yeni gorsel, yerini aldigi eski gorselin RANK'ine gelir ve o edisyonun
  varyasyon gorseli olarak yeniden baglanir (variation-images yeni id ile yazilir).
- Galerinin geri kalanina (kartlar, diger sahneler) DOKUNULMAZ.
- Baslik/etiket/fiyat/aciklama/bolum DEGISMEZ (updateListing cagrilmaz).
- Yazmadan once mevcut gorsel listesi + varyasyon baglantilari + video JSON olarak
  yedeklenir (--out/backup_<lid>_<ts>.json).

Kullanim:
  pod_hero_swap.py --listing-id 4570110121 --heroes MB=...,DB=... --video v.mp4
                   --out OUT [--apply] [--quota-min 300]
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

ED_NAME = {"MB": "Midnight Blue", "DB": "Deep Black", "WP": "Warm Parchment",
           "CI": "Champagne Ivory", "PW": "Pure White"}
ETSY_MAX_IMG = 10          # Etsy ilan basina gorsel siniri
OKUMA_TEKRAR, OKUMA_BEKLE = 6, 3


def galeri(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return sorted((r.get("results") or []), key=lambda x: x.get("rank") or 0)


def var_img(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}
    return r.get("results") or []


def videolar(api, lid):
    r = api.get(f"/listings/{lid}/videos", ok404=True) or {}
    return r.get("results") or []


def kararli(fn, bekle=None):
    """Etsy okumasi gecikmeli olabilir: ayni sonucu iki kez gorene kadar tekrar."""
    onceki = None
    for _ in range(OKUMA_TEKRAR):
        simdi = fn()
        if onceki is not None and simdi == onceki and (bekle is None or bekle(simdi)):
            return simdi
        onceki = simdi
        time.sleep(OKUMA_BEKLE)
    return onceki


def kota_yeter(api, qmin):
    if api.remaining is None:
        return True
    try:
        return int(api.remaining) >= qmin
    except ValueError:
        return True


def hero_degistir(api, shop, lid, eski_id, rank, dosya, alt_text, sinirda):
    """Eski hero'yu yenisiyle degistir; donus: yeni listing_image_id."""
    veri = {"rank": str(rank)}
    if alt_text:
        veri["alt_text"] = alt_text
    if sinirda:                      # 10 gorsel siniri: once sil, sonra yukle
        api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
        log(f"      eski {eski_id} silindi (sinir dolu)")
    with open(dosya, "rb") as fh:
        r = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"image": (dosya.name, fh, "image/jpeg")}, data=veri)
    yeni = r.get("listing_image_id")
    log(f"      yuklendi: id {yeni} rank {r.get('rank')}")
    if not sinirda:
        api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
        log(f"      eski {eski_id} silindi")
    return yeni


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--heroes", default="", help="MB=yol,DB=yol,... (--video-only ile gerekmez)")
    ap.add_argument("--video-only", action="store_true", help="yalniz videoyu degistir")
    ap.add_argument("--video", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=300)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lid = a.listing_id
    heroes = {s.split("=", 1)[0]: pathlib.Path(s.split("=", 1)[1]) for s in a.heroes.split(",") if s}
    if a.video_only:
        if not a.video or not pathlib.Path(a.video).exists():
            raise SystemExit("HATA: --video-only icin video dosyasi gerekli")
        heroes = {}
    else:
        eksik = [k for k, v in heroes.items() if not v.exists()]
        if eksik or set(heroes) != set(ED_NAME):
            raise SystemExit(f"HATA: hero dosyalari eksik/hatali: eksik={eksik} verilen={sorted(heroes)}")

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]

    # ---------------- 1) YEDEK (salt okur)
    L = api.get(f"/listings/{lid}") or {}
    imgs = galeri(api, lid)
    vimg = var_img(api, shop, lid)
    vids = videolar(api, lid)
    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    yedek = {"alindi_utc": zaman, "listing_id": lid, "state": L.get("state"), "title": L.get("title"),
             "images": imgs, "variation_images": vimg, "videos": vids,
             "not": "Geri donus: bu dosyadaki rank/varyasyon duzeni + Drive'daki kaynak gorseller "
                    "(TEMP/POD_GALLERY/<PAIR>/<ED>/01.jpg) ile yeniden yuklenir."}
    ypath = out / f"backup_{lid}_{zaman}.json"
    ypath.write_text(json.dumps(yedek, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"YEDEK: {ypath} ({len(imgs)} gorsel, {len(vimg)} varyasyon baglantisi, {len(vids)} video)")

    # ---------------- 2) PLAN
    id_rank = {i.get("listing_image_id"): i.get("rank") for i in imgs}
    alt_of = {i.get("listing_image_id"): i.get("alt_text") for i in imgs}
    ad_id = {v.get("value"): v.get("image_id") for v in vimg}
    pid_of = {v.get("value"): v.get("property_id") for v in vimg}
    vid_of = {v.get("value"): v.get("value_id") for v in vimg}
    plan, sorun = [], []
    for ed, dosya in ({} if a.video_only else heroes).items():
        ad = ED_NAME[ed]
        iid = ad_id.get(ad)
        if iid is None:
            sorun.append(f"{ed}: '{ad}' icin varyasyon gorseli yok")
            continue
        if iid not in id_rank:
            sorun.append(f"{ed}: varyasyon gorseli {iid} galeride yok")
            continue
        plan.append({"edisyon": ed, "renk": ad, "eski_image_id": iid, "rank": id_rank[iid],
                     "property_id": pid_of[ad], "value_id": vid_of[ad],
                     "alt_text": alt_of.get(iid), "dosya": dosya.name})
    plan.sort(key=lambda p: p["rank"])
    rapor = {"listing_id": lid, "state_once": L.get("state"), "yedek": ypath.name,
             "gorsel_sayisi_once": len(imgs), "plan": plan, "sorunlar": sorun,
             "video_once": [{"video_id": v.get("video_id"), "video_state": v.get("video_state")} for v in vids],
             "kota_once": api.remaining}
    log(json.dumps({"plan": plan, "sorunlar": sorun}, ensure_ascii=False, indent=1))
    if a.video_only:
        log("VIDEO-ONLY: galeri ve varyasyon baglantilarina dokunulmayacak.")
    if sorun:
        (out / "swap_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
        raise SystemExit(f"HATA: plan eksik: {sorun}")
    if not a.video_only and len(plan) != len(ED_NAME):
        raise SystemExit(f"HATA: plan {len(plan)}/{len(ED_NAME)} - DUR")
    if not a.apply:
        rapor["sonuc"] = "DRY-RUN (yazma yok)"
        (out / "swap_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
        log("DRY-RUN: yazma yok.")
        return
    if not kota_yeter(api, a.quota_min):
        raise SystemExit(f"HATA: kota {api.remaining} < {a.quota_min}: yazma yok")

    # ---------------- 3) HERO DEGISIMI (video-only'de atlanir)
    son_imgs, son_vimg = imgs, vimg
    sinirda = len(imgs) >= ETSY_MAX_IMG
    if a.video_only:
        log("hero degisimi ve variation-images ATLANDI (--video-only)")
    if not a.video_only:
        log(f"UYGULA: {len(plan)} hero degisecek (galeri {len(imgs)}/{ETSY_MAX_IMG}, "
            f"{'sinir dolu: once sil-sonra yukle' if sinirda else 'once yukle-sonra sil'})")
    for n, p in enumerate(plan, 1):
        log(f"  [{n}/{len(plan)}] {p['edisyon']} rank {p['rank']} eski {p['eski_image_id']}")
        p["yeni_image_id"] = hero_degistir(api, shop, lid, p["eski_image_id"], p["rank"],
                                           heroes[p["edisyon"]], p["alt_text"], sinirda)

    if plan:
        son_imgs = kararli(lambda: galeri(api, lid), bekle=lambda g: len(g) == len(imgs))
    id_rank2 = {i.get("listing_image_id"): i.get("rank") for i in son_imgs}
    # rank duzeltmesi (gerekiyorsa)
    for p in plan:
        if id_rank2.get(p["yeni_image_id"]) != p["rank"]:
            log(f"    rank duzeltme: {p['yeni_image_id']} -> {p['rank']}")
            api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"listing_image_id": (None, str(p["yeni_image_id"])),
                                 "rank": (None, str(p["rank"]))})
    if plan:
        son_imgs = kararli(lambda: galeri(api, lid), bekle=lambda g: len(g) == len(imgs))

        # ---------------- 4) VARYASYON BAGLANTISI
        vi = [{"property_id": p["property_id"], "value_id": p["value_id"], "image_id": p["yeni_image_id"]}
              for p in plan]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        log(f"variation-images yazildi: {len(vi)} baglanti")

    # ---------------- 5) VIDEO
    if a.video:
        vp = pathlib.Path(a.video)
        for v in vids:
            api.delete(f"/shops/{shop}/listings/{lid}/videos/{v.get('video_id')}")
            log(f"  eski video silindi: {v.get('video_id')}")
        with open(vp, "rb") as fh:
            rv = api.post_file(f"/shops/{shop}/listings/{lid}/videos",
                               files={"video": (vp.name, fh, "video/mp4")}, data={"name": vp.name})
        log(f"  yeni video: {rv.get('video_id')} {rv.get('video_state')}")

    # ---------------- 6) GERI OKUMA
    son_imgs = kararli(lambda: galeri(api, lid), bekle=lambda g: len(g) == len(imgs))
    son_vimg = kararli(lambda: var_img(api, shop, lid), bekle=lambda v: len(v) == len(vimg))
    son_vids = kararli(lambda: videolar(api, lid), bekle=lambda v: len(v) == 1) if a.video else vids
    L2 = api.get(f"/listings/{lid}") or {}
    yeni_ad_id = {v.get("value"): v.get("image_id") for v in son_vimg}
    dokunulmayan_once = {i.get("listing_image_id"): i.get("rank") for i in imgs
                         if i.get("listing_image_id") not in {p["eski_image_id"] for p in plan}}
    dokunulmayan_sonra = {i.get("listing_image_id"): i.get("rank") for i in son_imgs
                          if i.get("listing_image_id") in dokunulmayan_once}
    kontrol = {
        "gorsel_sayisi": len(son_imgs) == len(imgs),
        "galeri_hic_degismedi": ([(i.get("listing_image_id"), i.get("rank")) for i in son_imgs] ==
                                 [(i.get("listing_image_id"), i.get("rank")) for i in imgs]) if a.video_only else None,
        "varyasyon_degismedi": ({v.get("value"): v.get("image_id") for v in son_vimg} ==
                                {v.get("value"): v.get("image_id") for v in vimg}) if a.video_only else None,
        "hero_ranklari": all(
            next((i.get("rank") for i in son_imgs if i.get("listing_image_id") == p["yeni_image_id"]), None) == p["rank"]
            for p in plan),
        "varyasyon_baglantilari": all(yeni_ad_id.get(p["renk"]) == p["yeni_image_id"] for p in plan),
        "diger_gorseller_ayni": dokunulmayan_once == dokunulmayan_sonra,
        "state_degismedi": L2.get("state") == L.get("state"),
        "baslik_degismedi": L2.get("title") == L.get("title"),
        "video_tek": (len(son_vids) == 1) if a.video else None,
    }
    rapor.update({
        "sonuc": "PASS" if all(v for v in kontrol.values() if v is not None) else "FAIL",
        "kontrol": kontrol, "state_sonra": L2.get("state"),
        "galeri_sonra": [{"rank": i.get("rank"), "image_id": i.get("listing_image_id"),
                          "hero": next((p["edisyon"] for p in plan if p["yeni_image_id"] == i.get("listing_image_id")), "")}
                         for i in son_imgs],
        "varyasyon_sonra": [{"renk": v.get("value"), "image_id": v.get("image_id")} for v in son_vimg],
        "video_sonra": [{"video_id": v.get("video_id"), "video_state": v.get("video_state")} for v in son_vids],
        "plan": plan, "kota_sonra": api.remaining, "api_cagrisi": api.calls,
    })
    (out / "swap_result.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    log(json.dumps({k: rapor[k] for k in ("sonuc", "kontrol", "galeri_sonra", "varyasyon_sonra",
                                          "video_sonra", "state_sonra", "kota_sonra")},
                   ensure_ascii=False, indent=1))
    if rapor["sonuc"] != "PASS":
        raise SystemExit("HATA: geri okuma kontrolleri gecmedi")


if __name__ == "__main__":
    main()
