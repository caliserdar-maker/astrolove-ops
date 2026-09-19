#!/usr/bin/env python3
"""Galeri duzeni TOPLU (77 ilan; pilot 4570031205 haric, referans dahil).

Ilan basina (pilotla birebir): canli oku + snapshot yedegi -> canli sira
HEDEF_PLAN 'once' ile eslesmiyorsa ATLANDI (yazma yok) -> rank atamalari ->
EN SONDA variation-images PUT (snapshot'taki 5 baglanti) -> 90 sn'ye kadar
dogrulama. Rank cifti kalirsa ilgili gorsele 1 kez tekrar rank + PUT tekrar.
Yazmadan sonra bir kapi duserse TUM KOSU DURUR.

Ilk ilan otomatik pilottur: TAMAM degilse ikinciye gecilmez.
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
PILOT_BITEN = "4570031205"
KOTA_ALT = 400
SUTUN = ["listing_id", "cift", "durum", "rank_cagrisi", "neden", "kota", "sn"]
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def plan_oku(isd):
    y = isd / "HEDEF_PLAN.csv"
    if rclone("copyto", f"{DRV}/HEDEF_PLAN.csv", str(y)).returncode != 0:
        raise SystemExit("DUR: HEDEF_PLAN.csv inmedi")
    cikti = []
    with y.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("durum") != "OK" or r["listing_id"] == PILOT_BITEN:
                continue
            cikti.append({"listing_id": r["listing_id"], "cift": r["cift"],
                          "once": [r[f"once_{i}"] for i in range(1, 14)],
                          "hedef": [r[f"hedef_{i}"] for i in range(1, 14)]})
    return cikti


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "images": gallery(api, lid),
            "videos": videos(api, lid),
            "variations": variation_images(api, shop, lid)}


def sira(s):
    return [(str(x.get("listing_image_id")), int(x.get("rank") or 0))
            for x in s["images"]]


def vgovde(s):
    return [{"property_id": r.get("property_id"), "value_id": r.get("value_id"),
             "image_id": int(r.get("image_id"))} for r in s["variations"]]


def yedekle(isd, lid, s, hedef):
    y = isd / f"{lid}.json"
    y.write_text(json.dumps(
        {"listing": lid, "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "sira": sira(s), "varyasyon": [list(x) for x in variation_map(s["variations"])],
         "video": [str(v) for v in video_ids(s["videos"])],
         "baslik": s["listing"].get("title"), "durum": s["listing"].get("state"),
         "hedef": hedef}, ensure_ascii=False, indent=1), encoding="utf-8")
    if rclone("copyto", str(y), f"{DRV}/YEDEK/{lid}.json").returncode != 0:
        raise RuntimeError("yedek yuklenemedi")


def duzenle(api, shop, kayit, isd):
    """Tek ilan. Donus: (durum, neden, rank_cagrisi)."""
    lid = kayit["listing_id"]
    once = anlik(api, shop, lid)
    canli = sira(once)
    idler = [i for i, _ in canli]
    if len(once["images"]) != 13:
        return "ATLANDI", f"galeri {len(once['images'])} gorsel", 0
    if len(once["variations"]) != 5:
        return "ATLANDI", f"varyasyon baglantisi {len(once['variations'])}", 0
    if idler != kayit["once"]:
        return "ATLANDI", "canli sira HEDEF_PLAN 'once' ile ayni degil", 0
    if sorted(kayit["hedef"]) != sorted(idler):
        return "ATLANDI", "hedef id kumesi galeriyle ayni degil", 0
    yedekle(isd, lid, once, kayit["hedef"])
    govde = vgovde(once)
    hedef_vmap = sorted(variation_map(once["variations"]))

    simdiki = dict(canli)
    yapilacak = [(iid, i + 1) for i, iid in enumerate(kayit["hedef"])
                 if simdiki.get(iid) != i + 1]
    for iid, r in yapilacak:
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, iid), "rank": (None, str(r))})
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": govde})
    cagri = len(yapilacak) + 1

    def tamam(s):
        ss = sira(s)
        return ([i for i, _ in ss] == kayit["hedef"]
                and [r for _, r in ss] == list(range(1, 14))
                and sorted(variation_map(s["variations"])) == hedef_vmap)

    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        if tamam(son):
            break
        if time.time() >= bitis:
            break
        time.sleep(10)
    if not tamam(son):
        # rank cifti icin tek tekrar + PUT tekrari
        ss = sira(son)
        simdiki = dict(ss)
        tekrar = [(iid, i + 1) for i, iid in enumerate(kayit["hedef"])
                  if simdiki.get(iid) != i + 1]
        if tekrar:
            ilerle(f"  {lid}: rank tekrari {tekrar}")
            for iid, r in tekrar:
                api.post_file(f"/shops/{shop}/listings/{lid}/images",
                              files={"listing_image_id": (None, iid),
                                     "rank": (None, str(r))})
                cagri += 1
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                      {"variation_images": govde})
        cagri += 1
        bitis = time.time() + 60
        while True:
            son = anlik(api, shop, lid)
            if tamam(son) or time.time() >= bitis:
                break
            time.sleep(10)

    s_sira = sira(son)
    kapilar = {
        "rank_1_13_temiz": [r for _, r in s_sira] == list(range(1, 14)),
        "sira_hedef": [i for i, _ in s_sira] == kayit["hedef"],
        "varyasyon_5_birebir": sorted(variation_map(son["variations"])) == hedef_vmap,
        "gorsel_13": len(son["images"]) == 13,
        "video_ayni": video_ids(once["videos"]) == video_ids(son["videos"]),
        "baslik_ayni": once["listing"].get("title") == son["listing"].get("title"),
        "durum_ayni": once["listing"].get("state") == son["listing"].get("state")}
    if not all(kapilar.values()):
        raise RuntimeError(f"YAZMA SONRASI KAPI {kapilar} | canli {s_sira} | "
                           f"varyasyon {variation_map(son['variations'])}")
    return "TAMAM", "", cagri


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--is-dizin", default="_work/toplu")
    a = ap.parse_args()
    if a.apply and a.confirm != "GALERI_TOPLU":
        raise SystemExit("DUR: apply icin confirm 'GALERI_TOPLU' olmali")
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
    plan = plan_oku(isd)
    if a.limit:
        plan = plan[:a.limit]
    durum_yerel = isd / "state.json"
    durum = {"tamam": {}, "atlandi": {}, "hata": {}}
    if rclone("copyto", f"{DRV}/state_duzen.json", str(durum_yerel)).returncode == 0:
        try:
            durum = json.loads(durum_yerel.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    for k in ("tamam", "atlandi", "hata"):
        durum.setdefault(k, {})
    kalan = [k for k in plan if k["listing_id"] not in durum["tamam"]]
    ilerle(f"kota {kota_once} | plan {len(plan)} ilan | tamam {len(durum['tamam'])} "
           f"| kosulacak {len(kalan)} | mod {'YAZMA' if a.apply else 'KURU'}")

    sonuc = isd / "SONUC_DUZEN.csv"
    if rclone("copyto", f"{DRV}/SONUC_DUZEN.csv", str(sonuc)).returncode != 0:
        with sonuc.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(SUTUN)

    def yaz(satir):
        with sonuc.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore").writerow(satir)
        rclone("copyto", str(sonuc), f"{DRV}/SONUC_DUZEN.csv")
        durum_yerel.write_text(json.dumps(durum, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        rclone("copyto", str(durum_yerel), f"{DRV}/state_duzen.json")

    t0 = time.time()
    for j, kayit in enumerate(kalan, start=1):
        ts = time.time()
        lid, cift = kayit["listing_id"], kayit["cift"]
        kota = int(api.remaining or 0)
        if kota and kota < KOTA_ALT:
            ilerle(f"DUR: kota {kota} < {KOTA_ALT}")
            break
        satir = {"listing_id": lid, "cift": cift, "durum": "ATLANDI",
                 "rank_cagrisi": 0, "neden": "", "kota": kota}
        try:
            if not a.apply:
                once = anlik(api, shop, lid)
                ayni = [i for i, _ in sira(once)] == kayit["once"]
                satir["durum"] = "KURU_UYGUN" if ayni else "ATLANDI"
                satir["neden"] = "" if ayni else "canli sira 'once' degil"
            else:
                d, neden, cagri = duzenle(api, shop, kayit, isd)
                satir.update({"durum": d, "neden": neden, "rank_cagrisi": cagri})
                if d == "TAMAM":
                    durum["tamam"][lid] = {"cift": cift, "cagri": cagri}
                    durum["atlandi"].pop(lid, None)
                else:
                    durum["atlandi"][lid] = neden
        except Exception as e:
            satir.update({"durum": "HATA", "neden": f"{type(e).__name__}: {e}"[:220]})
            durum["hata"][lid] = satir["neden"]
            satir["sn"] = round(time.time() - ts, 1)
            yaz(satir)
            ilerle(f"DUR: {lid} {cift}: {satir['neden']}")
            print(json.dumps({"durdu": lid, "neden": satir["neden"],
                              "tamam": len(durum["tamam"])}, ensure_ascii=False))
            return 3
        satir["sn"] = round(time.time() - ts, 1)
        yaz(satir)
        gec = time.time() - t0
        ilerle(f"{j}/{len(kalan)} (%{100 * j / len(kalan):.1f}) {lid} {cift} "
               f"{satir['durum']} {satir['neden'][:40]} cagri {satir['rank_cagrisi']} "
               f"| gecen {sure_yaz(gec)} kalan ~{sure_yaz(gec / j * (len(kalan) - j))} "
               f"| kota {api.remaining}")
        if a.apply and j == 1 and satir["durum"] != "TAMAM":
            ilerle("DUR: ilk ilan (pilot) TAMAM degil, digerlerine gecilmedi")
            print(json.dumps({"pilot": satir["durum"], "neden": satir["neden"]},
                             ensure_ascii=False))
            return 3

    ilerle(f"BITTI | tamam {len(durum['tamam'])} | atlandi {len(durum['atlandi'])} "
           f"| hata {len(durum['hata'])} | kota {kota_once} -> {api.remaining}")
    print(json.dumps({"tamam": len(durum["tamam"]), "atlandi": durum["atlandi"],
                      "hata": durum["hata"], "kota_once": kota_once,
                      "kota_sonra": api.remaining}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
