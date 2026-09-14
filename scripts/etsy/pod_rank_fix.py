#!/usr/bin/env python3
"""Galeri rank cakismasini duzeltir (Mo 14 Eyl 2026).

Toplu hero degisiminde 5 ilanda rank 2 bosalmis, rank 1'de iki gorsel kalmisti
(yeni MB hero + eskiden rank 2'de olan kart). Bu script, cakisan rank'teki
HERO OLMAYAN gorseli bos rank'e geri alir; hero'lara ve varyasyon baglantilarina
dokunmaz, hicbir metin alani degismez (updateListing cagrilmaz).

Akis (ilan basina): yedek JSON -> gerekliyse tek rank yazimi -> geri okuma
(12 gorselin rank'i 1..N tekil, hero rank'leri ayni, 5/5 varyasyon baglantisi,
state/baslik/video ayni).

Kullanim:
  pod_rank_fix.py --listings 111,222 --out OUT [--apply] [--quota-min 300]
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

OKUMA_TEKRAR, OKUMA_BEKLE = 6, 3


def galeri(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return sorted((r.get("results") or []), key=lambda x: (x.get("rank") or 0, x.get("listing_image_id")))


def var_img(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}
    return r.get("results") or []


def videolar(api, lid):
    r = api.get(f"/listings/{lid}/videos", ok404=True) or {}
    return r.get("results") or []


def kararli(fn, bekle=None):
    onceki = None
    for _ in range(OKUMA_TEKRAR):
        simdi = fn()
        if onceki is not None and simdi == onceki and (bekle is None or bekle(simdi)):
            return simdi
        onceki = simdi
        time.sleep(OKUMA_BEKLE)
    return onceki


def plan_cikar(imgs, hero_ids):
    """Cakisan rank'lerdeki hero olmayan gorselleri bos rank'lere esle."""
    rank_ids = {}
    for i in imgs:
        rank_ids.setdefault(i.get("rank"), []).append(i.get("listing_image_id"))
    n = len(imgs)
    bos = [r for r in range(1, n + 1) if r not in rank_ids]
    tasinacak = []
    for r, ids in sorted(rank_ids.items()):
        if len(ids) < 2:
            continue
        for iid in ids:                      # hero'lar yerinde kalir
            if iid not in hero_ids and len(ids) > 1:
                tasinacak.append(iid)
                ids = [x for x in ids if x != iid]
    return list(zip(tasinacak, bos)), sorted(rank_ids), bos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=300)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lids = [x.strip() for x in a.listings.split(",") if x.strip()]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    t0, sonuc = time.time(), []

    for n, lid in enumerate(lids, 1):
        gecen = time.time() - t0
        kalan = gecen / (n - 1) * (len(lids) - n + 1) if n > 1 else 0
        log(f"[{n}/{len(lids)} %{(n-1)/len(lids)*100:.0f}] ilan {lid} | gecen {gecen/60:.1f} dk, "
            f"kalan ~{kalan/60:.1f} dk")
        L = api.get(f"/listings/{lid}") or {}
        imgs = galeri(api, lid)
        vimg = var_img(api, shop, lid)
        vids = videolar(api, lid)
        zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        (out / f"backup_{lid}_{zaman}.json").write_text(json.dumps(
            {"alindi_utc": zaman, "listing_id": lid, "state": L.get("state"), "title": L.get("title"),
             "images": imgs, "variation_images": vimg, "videos": vids}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        hero_ids = {v.get("image_id") for v in vimg}
        tasi, ranklar, bos = plan_cikar(imgs, hero_ids)
        kayit = {"listing_id": lid, "state_once": L.get("state"), "gorsel": len(imgs),
                 "ranklar_once": ranklar, "bos_rank": bos, "tasinacak": tasi,
                 "yedek": f"backup_{lid}_{zaman}.json"}
        log(f"    ranklar {ranklar} | bos {bos} | tasinacak {tasi}")
        if not tasi:
            kayit["sonuc"] = "DEGISIM YOK (rank duzeni zaten temiz)"
            sonuc.append(kayit)
            continue
        if not a.apply:
            kayit["sonuc"] = "DRY-RUN"
            sonuc.append(kayit)
            continue
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < a.quota_min:
            kayit["sonuc"] = f"DUR: kota {api.remaining} < {a.quota_min}"
            sonuc.append(kayit)
            log(kayit["sonuc"])
            break
        for iid, rank in tasi:
            api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"listing_image_id": (None, str(iid)), "rank": (None, str(rank))})
            log(f"    {iid} -> rank {rank}")
        son_imgs = kararli(lambda: galeri(api, lid), bekle=lambda g: len(g) == len(imgs))
        son_vimg = kararli(lambda: var_img(api, shop, lid), bekle=lambda v: len(v) == len(vimg))
        son_vids = videolar(api, lid)
        L2 = api.get(f"/listings/{lid}") or {}
        son_rank = sorted(i.get("rank") for i in son_imgs)
        eski_hero_rank = {i.get("listing_image_id"): i.get("rank") for i in imgs
                          if i.get("listing_image_id") in hero_ids}
        yeni_hero_rank = {i.get("listing_image_id"): i.get("rank") for i in son_imgs
                          if i.get("listing_image_id") in hero_ids}
        kontrol = {
            "gorsel_sayisi": len(son_imgs) == len(imgs),
            "rank_tekil_ve_sirali": son_rank == list(range(1, len(son_imgs) + 1)),
            "hero_ranklari_ayni": eski_hero_rank == yeni_hero_rank,
            "varyasyon_baglantilari": ({v.get("value"): v.get("image_id") for v in son_vimg} ==
                                       {v.get("value"): v.get("image_id") for v in vimg}),
            "varyasyon_sayisi_5": len(son_vimg) == 5,
            "state_degismedi": L2.get("state") == L.get("state"),
            "baslik_degismedi": L2.get("title") == L.get("title"),
            "video_degismedi": ([v.get("video_id") for v in son_vids] ==
                                [v.get("video_id") for v in vids]),
        }
        kayit.update({"sonuc": "PASS" if all(kontrol.values()) else "FAIL", "kontrol": kontrol,
                      "galeri_sonra": [{"rank": i.get("rank"), "image_id": i.get("listing_image_id"),
                                        "hero": i.get("listing_image_id") in hero_ids} for i in son_imgs],
                      "kota": api.remaining})
        log(f"    {kayit['sonuc']} | ranklar {son_rank} | kota {api.remaining}")
        sonuc.append(kayit)

    ozet = {"ilan": len(lids), "pass": sum(1 for s in sonuc if s.get("sonuc") == "PASS"),
            "degisim_yok": sum(1 for s in sonuc if str(s.get("sonuc", "")).startswith("DEGISIM")),
            "fail": [s["listing_id"] for s in sonuc if s.get("sonuc") == "FAIL"],
            "sure_dk": round((time.time() - t0) / 60, 1), "kota": api.remaining, "kayitlar": sonuc}
    (out / "rank_fix_result.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    log(json.dumps({k: v for k, v in ozet.items() if k != "kayitlar"}, ensure_ascii=False, indent=1))
    if ozet["fail"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
