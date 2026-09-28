#!/usr/bin/env python3
"""RANK3 -> RANK11 uygulama (Etsy YAZMA - Serdar onayi, 78 POD ilani).

Yontem: uploadListingImage, DOSYA YOK, yalniz listing_image_id + rank=11.
overwrite KULLANILMAZ. Baska hicbir cagri yapilmaz.

Ilan basina: canli sira PLAN "once" ile ayni mi -> degilse ATLANDI (yazma yok);
ayniysa tek yazma cagrisi -> 90 sn'ye kadar geri-okuma -> PLAN "sonra" sirasi,
video, varyasyon baglantilari, baslik, durum ayni mi. Tutmazsa TUM KOSU DURUR.

Once pilot 4570031205; gecmeden digerlerine gecilmez.
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
PILOT = "4570031205"
HEDEF_RANK = 11
KOTA_ALT = 400
SUTUN = ["listing_id", "cift", "durum", "tasinan_image_id", "neden", "kota", "sn"]
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def plan_oku(isd):
    y = isd / "PLAN.csv"
    if rclone("copyto", f"{DRV}/PLAN.csv", str(y)).returncode != 0:
        raise SystemExit("DUR: PLAN.csv inmedi")
    satir = []
    with y.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("durum") != "OK":
                continue
            once = [r[f"once_{i}"] for i in range(1, 14) if r.get(f"once_{i}")]
            sonra = [r[f"sonra_{i}"] for i in range(1, 14) if r.get(f"sonra_{i}")]
            satir.append({"listing_id": r["listing_id"], "cift": r["cift"],
                          "rank3": r["rank3_image_id"], "once": once, "sonra": sonra})
    return satir


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "images": gallery(api, lid),
            "videos": videos(api, lid),
            "variations": variation_images(api, shop, lid)}


def idler(s):
    return [str(x.get("listing_image_id")) for x in s["images"]]


def tasi(api, shop, kayit, isd):
    """Tek ilan: kontrol -> yazma -> dogrulama. Donus: (durum, neden)."""
    lid = kayit["listing_id"]
    once = anlik(api, shop, lid)
    canli = idler(once)
    if canli != kayit["once"]:
        return "ATLANDI", f"canli sira PLAN 'once' ile ayni degil ({len(canli)} gorsel)"
    if kayit["rank3"] != canli[2]:
        return "ATLANDI", f"rank-3 {canli[2]} != PLAN {kayit['rank3']}"
    api.post_file(f"/shops/{shop}/listings/{lid}/images",
                  files={"listing_image_id": (None, kayit["rank3"]),
                         "rank": (None, str(HEDEF_RANK))})
    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        if idler(son) == kayit["sonra"]:
            break
        if time.time() >= bitis:
            break
        time.sleep(10)
    kapilar = {
        "sira_plan_sonra": idler(son) == kayit["sonra"],
        "gorsel_sayisi": len(son["images"]) == len(once["images"]),
        "video_ayni": video_ids(once["videos"]) == video_ids(son["videos"]),
        "varyasyon_ayni": variation_map(once["variations"]) ==
                          variation_map(son["variations"]),
        "baslik_ayni": once["listing"].get("title") == son["listing"].get("title"),
        "durum_ayni": once["listing"].get("state") == son["listing"].get("state")}
    if not all(kapilar.values()):
        raise RuntimeError(f"YAZMA SONRASI KAPI {kapilar} | canli sira {idler(son)} "
                           f"| beklenen {kayit['sonra']}")
    return "TAMAM", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--is-dizin", default="_work/rank3u")
    a = ap.parse_args()
    if a.apply and a.confirm != "RANK3_TO_11":
        raise SystemExit("DUR: apply icin confirm 'RANK3_TO_11' olmali")
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
    ilerle(f"kota once: {kota_once} | mod {'YAZMA' if a.apply else 'KURU DENEME'}")

    plan = plan_oku(isd)
    sirali = ([k for k in plan if k["listing_id"] == PILOT]
              + [k for k in plan if k["listing_id"] != PILOT])
    if a.limit:
        sirali = sirali[:a.limit]
    durum_yerel = isd / "state.json"
    durum = {"tamam": {}, "atlandi": {}, "hata": {}}
    if rclone("copyto", f"{DRV}/state.json", str(durum_yerel)).returncode == 0:
        try:
            durum = json.loads(durum_yerel.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    for k in ("tamam", "atlandi", "hata"):
        durum.setdefault(k, {})
    kalan = [k for k in sirali if k["listing_id"] not in durum["tamam"]]
    ilerle(f"plan {len(plan)} ilan | tamam {len(durum['tamam'])} | kosulacak {len(kalan)}")

    sonuc = isd / "SONUC.csv"
    if rclone("copyto", f"{DRV}/SONUC.csv", str(sonuc)).returncode != 0:
        with sonuc.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(SUTUN)

    def yaz(satir):
        with sonuc.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore").writerow(satir)
        rclone("copyto", str(sonuc), f"{DRV}/SONUC.csv")
        durum_yerel.write_text(json.dumps(durum, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        rclone("copyto", str(durum_yerel), f"{DRV}/state.json")

    t0 = time.time()
    for j, kayit in enumerate(kalan, start=1):
        ts = time.time()
        lid, cift = kayit["listing_id"], kayit["cift"]
        kota = int(api.remaining or 0)
        if kota and kota < KOTA_ALT:
            ilerle(f"DUR: kota {kota} < {KOTA_ALT}")
            break
        satir = {"listing_id": lid, "cift": cift, "durum": "ATLANDI",
                 "tasinan_image_id": kayit["rank3"], "neden": "", "kota": kota}
        try:
            if not a.apply:
                once = anlik(api, shop, lid)
                ayni = idler(once) == kayit["once"]
                satir["durum"] = "KURU_UYGUN" if ayni else "ATLANDI"
                satir["neden"] = "" if ayni else "canli sira PLAN 'once' degil"
            else:
                d, neden = tasi(api, shop, kayit, isd)
                satir.update({"durum": d, "neden": neden})
                if d == "TAMAM":
                    durum["tamam"][lid] = {"cift": cift, "image": kayit["rank3"]}
                    durum["atlandi"].pop(lid, None)
                else:
                    durum["atlandi"][lid] = neden
        except RuntimeError as e:
            satir.update({"durum": "HATA", "neden": str(e)[:220]})
            durum["hata"][lid] = str(e)[:300]
            satir["sn"] = round(time.time() - ts, 1)
            yaz(satir)
            ilerle(f"DUR (yazma sonrasi kapi): {lid} {cift}: {e}")
            print(json.dumps({"durdu": lid, "neden": str(e)[:300],
                              "tamam": len(durum["tamam"])}, ensure_ascii=False))
            return 3
        except Exception as e:
            satir.update({"durum": "HATA", "neden": f"{type(e).__name__}: {e}"[:220]})
            durum["hata"][lid] = satir["neden"]
            satir["sn"] = round(time.time() - ts, 1)
            yaz(satir)
            ilerle(f"DUR (beklenmeyen): {lid}: {satir['neden']}")
            return 3
        satir["sn"] = round(time.time() - ts, 1)
        yaz(satir)
        gec = time.time() - t0
        ilerle(f"{j}/{len(kalan)} (%{100 * j / len(kalan):.1f}) {lid} {cift} "
               f"{satir['durum']} {satir['neden'][:40]} | gecen {sure_yaz(gec)} "
               f"kalan ~{sure_yaz(gec / j * (len(kalan) - j))} | kota {api.remaining}")
        if a.apply and j == 1 and lid == PILOT and satir["durum"] != "TAMAM":
            ilerle("DUR: pilot gecmedi, toplu kosu baslatilmadi")
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
