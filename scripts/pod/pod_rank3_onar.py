#!/usr/bin/env python3
"""PILOT ONARIM (4570031205): rank 10 duzeltme + varyasyon baglantilarini geri yaz.

Sira onemli: once rank, EN SONDA variation-images PUT (rank yazmak varyasyon
baglantisini siliyor - 19 Eyl olcumu).

1. 8521483764 -> rank=10 (tek cagri, dosya yok, overwrite yok); rank dizisi
   1..13 temiz degilse bir kez daha dener, yine olmazsa raporlar ve devam eder.
2. variation-images: 5 baglantinin TAMAMI V11 yedegindeki snapshot'tan yazilir.
3. 90 sn'ye kadar canli geri-okuma + dogrulama.
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
YEDEK = "gdrive:ASTROLOVE/TEMP/POD_V11_YAYIN/YEDEK"
RANK_HEDEF = ("8521483764", 10)
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
                return {"cift": r["cift"],
                        "sonra": [r[f"sonra_{i}"] for i in range(1, 14)]}
    raise SystemExit(f"DUR: PLAN'da {lid} yok")


def yedek_varyasyon(isd, lid):
    """V11 yedegindeki snapshot'tan (property_id, value_id, value, image_id)."""
    y = isd / "snapshot.json"
    if rclone("copyto", f"{YEDEK}/{lid}/snapshot.json", str(y)).returncode != 0:
        raise SystemExit("DUR: V11 yedek snapshot.json inmedi")
    veri = json.loads(y.read_text(encoding="utf-8"))
    vy = (veri.get("ozet") or {}).get("varyasyon") or []
    if len(vy) != 5:
        raise SystemExit(f"DUR: snapshot'ta 5 baglanti yok ({len(vy)})")
    return [{"property_id": int(p), "value_id": int(v), "deger": d,
             "image_id": int(i)} for p, v, d, i in vy]


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
    ap.add_argument("--listing", default="4570031205")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is-dizin", default="_work/onar")
    a = ap.parse_args()
    if a.apply and a.confirm != "PILOT_ONARIM":
        raise SystemExit("DUR: apply icin confirm 'PILOT_ONARIM' olmali")
    lid = a.listing
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    kayit = plan_kayit(isd, lid)
    hedef_vy = yedek_varyasyon(isd, lid)
    once = anlik(api, shop, lid)
    ilerle(f"{lid} {kayit['cift']} | kota {kota_once} | canli {sira(once)} | "
           f"varyasyon {len(once['variations'])} | hedef varyasyon "
           f"{[(v['deger'], v['image_id']) for v in hedef_vy]}")
    if not a.apply:
        print(json.dumps({"kuru": True, "rank_cagri": list(RANK_HEDEF),
                          "varyasyon_yazilacak": len(hedef_vy)}, ensure_ascii=False))
        return 0

    # 1) rank 10
    cagri = 0
    temiz = False
    for deneme in (1, 2):
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, RANK_HEDEF[0]),
                             "rank": (None, str(RANK_HEDEF[1]))})
        cagri += 1
        time.sleep(5)
        ara = sira(anlik(api, shop, lid))
        ranklar = [r for _, r in ara]
        ilerle(f"  rank denemesi {deneme}: {ranklar}")
        if ranklar == list(range(1, 14)):
            temiz = True
            break
    if not temiz:
        ilerle(f"  rank dizisi temizlenemedi: {ranklar} (sira gorsel olarak dogru, "
               f"2. adima geciliyor)")

    # 2) variation-images (EN SONDA)
    govde = [{"property_id": v["property_id"], "value_id": v["value_id"],
              "image_id": v["image_id"]} for v in hedef_vy]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": govde})
    cagri += 1
    ilerle(f"  variation-images yazildi: {len(govde)} baglanti")

    # 3) dogrulama
    hedef_harita = sorted((v["property_id"], v["value_id"], v["deger"], v["image_id"])
                          for v in hedef_vy)
    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        if (sorted(variation_map(son["variations"])) == hedef_harita
                and [i for i, _ in sira(son)] == kayit["sonra"]):
            break
        if time.time() >= bitis:
            break
        ilerle(f"  bekleniyor: varyasyon {len(son['variations'])} | sira "
               f"{[i for i, _ in sira(son)][:4]}...")
        time.sleep(10)
    s_sira = sira(son)
    ranklar = [r for _, r in s_sira]
    kapilar = {
        "varyasyon_5_birebir": sorted(variation_map(son["variations"])) == hedef_harita,
        "sira_plan_sonra": [i for i, _ in s_sira] == kayit["sonra"],
        "gorsel_13": len(son["images"]) == 13,
        "video_ayni": video_ids(once["videos"]) == video_ids(son["videos"]),
        "baslik_ayni": once["listing"].get("title") == son["listing"].get("title"),
        "durum_ayni": once["listing"].get("state") == son["listing"].get("state")}
    sonuc = {"listing": lid, "cift": kayit["cift"], "cagri": cagri,
             "rank_temiz": ranklar == list(range(1, 14)), "rank_dizisi": ranklar,
             "canli_sonra": s_sira,
             "varyasyon": [list(x) for x in variation_map(son["variations"])],
             "kapilar": kapilar, "hepsi_gecti": all(kapilar.values()),
             "kota_once": kota_once, "kota_sonra": api.remaining,
             "link": f"https://www.etsy.com/listing/{lid}"}
    (isd / "ONARIM.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    rclone("copyto", str(isd / "ONARIM.json"), f"{DRV}/ONARIM_{lid}.json")
    ilerle(f"SONUC {kapilar} | rank {ranklar} | kota {kota_once} -> {api.remaining}")
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0 if all(kapilar.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
