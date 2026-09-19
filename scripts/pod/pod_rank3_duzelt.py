#!/usr/bin/env python3
"""RANK duzeltme: hedef siradaki her gorsele rank'i ACIKCA atar.

Teshis: uploadListingImage(listing_image_id, rank) yalniz o gorselin rank'ini
yazar, digerlerini kaydirmaz. Bu yuzden 3.-11. konumdaki 9 gorsele sirayla
rank=3..11 atanir (1, 2, 12, 13 sabit). Rank'i zaten hedefte olan gorsele
cagri gonderilmez.

Varsayilan tek ilan (pilot). Etsy'ye yazma: --apply --confirm gerekir.
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (gallery, variation_images,  # noqa: E402
                                  variation_map, video_ids, videos)

DRV = "gdrive:ASTROLOVE/TEMP/POD_RANK3_TO_11"
ILK, SON = 3, 11          # sabit: 1, 2, 12, 13
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def plan_kayit(isd, lid):
    y = isd / "PLAN.csv"
    if not y.is_file() and rclone("copyto", f"{DRV}/PLAN.csv", str(y)).returncode != 0:
        raise SystemExit("DUR: PLAN.csv inmedi")
    with y.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["listing_id"] == lid:
                return {"cift": r["cift"], "rank3": r["rank3_image_id"],
                        "once": [r[f"once_{i}"] for i in range(1, 14)],
                        "sonra": [r[f"sonra_{i}"] for i in range(1, 14)]}
    raise SystemExit(f"DUR: PLAN'da {lid} yok")


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "images": gallery(api, lid),
            "videos": videos(api, lid),
            "variations": variation_images(api, shop, lid)}


def sira(s):
    return [(str(x.get("listing_image_id")), int(x.get("rank") or 0))
            for x in s["images"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is-dizin", default="_work/rank3d")
    a = ap.parse_args()
    if a.apply and a.confirm != "RANK_DUZELT":
        raise SystemExit("DUR: apply icin confirm 'RANK_DUZELT' olmali")
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    lid = a.listing

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    kayit = plan_kayit(isd, lid)
    once = anlik(api, shop, lid)
    canli = sira(once)
    ilerle(f"{lid} {kayit['cift']} | kota {kota_once} | canli {canli}")

    hedef = {iid: i + 1 for i, iid in enumerate(kayit["sonra"])}
    simdiki = dict(canli)
    if set(simdiki) != set(hedef):
        raise SystemExit(f"DUR: galeri id kumesi PLAN ile ayni degil "
                         f"({len(simdiki)} vs {len(hedef)})")
    yapilacak = [(kayit["sonra"][i - 1], i) for i in range(ILK, SON + 1)
                 if simdiki.get(kayit["sonra"][i - 1]) != i]
    atlanan = [(kayit["sonra"][i - 1], i) for i in range(ILK, SON + 1)
               if simdiki.get(kayit["sonra"][i - 1]) == i]
    ilerle(f"gonderilecek cagri: {len(yapilacak)} {yapilacak} | atlanan "
           f"{len(atlanan)} {atlanan}")
    if not a.apply:
        print(json.dumps({"cagri": len(yapilacak), "plan": yapilacak,
                          "atlanan": atlanan}, ensure_ascii=False))
        return 0

    for n, (iid, r) in enumerate(yapilacak, start=1):
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, iid), "rank": (None, str(r))})
        ilerle(f"  {n}/{len(yapilacak)} {iid} -> rank {r} | kota {api.remaining}")

    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        idler = [i for i, _ in sira(son)]
        ranklar = [r for _, r in sira(son)]
        if idler == kayit["sonra"] and ranklar == list(range(1, 14)):
            break
        if time.time() >= bitis:
            break
        ilerle(f"  bekleniyor: rank {ranklar}")
        time.sleep(10)
    s_sira = sira(son)
    idler = [i for i, _ in s_sira]
    ranklar = [r for _, r in s_sira]
    kapilar = {
        "rank_1_13_boslukSuz": ranklar == list(range(1, 14)),
        "sira_plan_sonra": idler == kayit["sonra"],
        "gorsel_sayisi": len(son["images"]) == 13,
        "video_ayni": video_ids(once["videos"]) == video_ids(son["videos"]),
        "varyasyon_ayni": variation_map(once["variations"]) ==
                          variation_map(son["variations"]),
        "baslik_ayni": once["listing"].get("title") == son["listing"].get("title"),
        "durum_ayni": once["listing"].get("state") == son["listing"].get("state")}
    sonuc = {"listing": lid, "cift": kayit["cift"], "cagri": len(yapilacak),
             "atlanan_cagri": len(atlanan), "gonderilen": yapilacak,
             "canli_once": canli, "canli_sonra": s_sira, "kapilar": kapilar,
             "hepsi_gecti": all(kapilar.values()),
             "kota_once": kota_once, "kota_sonra": api.remaining,
             "link": f"https://www.etsy.com/listing/{lid}"}
    (isd / "DUZELT.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    rclone("copyto", str(isd / "DUZELT.json"), f"{DRV}/DUZELT_{lid}.json")
    ilerle(f"SONUC {kapilar} | kota {kota_once} -> {api.remaining}")
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0 if all(kapilar.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
