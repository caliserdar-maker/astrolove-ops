#!/usr/bin/env python3
"""V11 TOPLU YAYIN - 76 ilan (Aquarius+Gemini referansi ve pilot haric).

Yontem pilotla (pod_v11_yayin.py) birebir ayni; yalniz ilan listesi genis.

Ilan basina: onkontrol (kapi tutmazsa ATLANDI, sonraki ilana gecilir) ->
yedek -> yazma (kapak rank 1, eski Gold B kapagi sil, yeni video, eski videoyu
sil) -> 90 sn'ye kadar dogrulama. YAZMADAN SONRA bir kapi tutmazsa TUM KOSU
DURUR.

Guvenlik: Drive state.json ile devam edilebilir; kota 400'un altina inerse
durur; gizli deger loglanmaz.
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time

from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (download, gallery, image_map,  # noqa: E402
                                  variation_images, variation_map, video_ids,
                                  videos)

REFERANS_ILAN = "4570112095"      # Aquarius+Gemini, canlida kalir
PILOT_ILAN = "4570110641"         # pilotta yayinlandi
KAYNAK = "gdrive:ASTROLOVE/TEMP/POD_V11_URETIM"
YAYIN = "gdrive:ASTROLOVE/TEMP/POD_V11_YAYIN"
GOLD_STATE = "gdrive:ASTROLOVE/TEMP/POD_COVER_GOLD_B_77/state.json"
CIFT_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
KOTA_ALT = 400
SUTUN = ["listing_id", "cift", "durum", "yeni_kapak_id", "yeni_video_id",
         "silinen_kapak_id", "silinen_video_id", "neden", "kota", "sn"]
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def ciftler():
    veri = json.loads(CIFT_JSON.read_text(encoding="utf-8"))
    cikti = []
    for r in veri:
        lid, ad = str(r.get("id", "")), r.get("pair", "")
        if not lid or not ad or lid in (REFERANS_ILAN, PILOT_ILAN):
            continue
        cikti.append((lid, ad.replace(" + ", "_").replace(" ", "_").upper()))
    return sorted(set(cikti))


def gold_haritasi(isd):
    y = isd / "gold_state.json"
    if rclone("copyto", GOLD_STATE, str(y)).returncode != 0:
        raise SystemExit("DUR: Gold B state.json inmedi")
    veri = json.loads(y.read_text(encoding="utf-8"))
    harita = {}
    for lid, kayit in (veri.get("rows") or {}).items():
        kimlik = ((kayit.get("apply") or {}).get("new_cover_id")
                  or (kayit.get("repair") or {}).get("new_cover_id"))
        if kimlik:
            harita[str(lid)] = str(kimlik)
    return harita


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "images": gallery(api, lid),
            "videos": videos(api, lid),
            "variations": variation_images(api, shop, lid)}


def ozet(s):
    return {"gorsel": [{"id": str(r.get("listing_image_id")), "rank": r.get("rank"),
                        "boyut": [r.get("full_width"), r.get("full_height")]}
                       for r in s["images"]],
            "video": [str(v) for v in video_ids(s["videos"])],
            "varyasyon": [list(x) for x in variation_map(s["variations"])],
            "baslik": s["listing"].get("title"),
            "durum": s["listing"].get("state")}


def onkontrol(s, gold_id):
    """Yazmadan onceki kapilar. Donus: (uygun_mu, neden)."""
    if len(s["images"]) != 13:
        return False, f"galeri {len(s['images'])} gorsel"
    if len(s["videos"]) != 1:
        return False, f"video sayisi {len(s['videos'])}"
    if s["listing"].get("state") != "active":
        return False, f"durum {s['listing'].get('state')}"
    rank1 = s["images"][0]
    if int(rank1.get("rank") or 0) != 1:
        return False, "ilk gorselin rank'i 1 degil"
    rank1_id = str(rank1.get("listing_image_id"))
    if gold_id is None:
        return False, "Gold B state kaydi yok"
    if rank1_id != gold_id:
        return False, f"rank-1 {rank1_id} != Gold B {gold_id}"
    if rank1_id in {str(r.get("image_id")) for r in s["variations"]}:
        return False, f"rank-1 varyasyona bagli ({rank1_id})"
    return True, ""


def yayinla(api, shop, lid, cift, once, isd):
    """Yazma + dogrulama. Kapi tutmazsa RuntimeError (tum kosu durur)."""
    rank1_id = str(once["images"][0].get("listing_image_id"))
    eski_video_id = str(once["videos"][0].get("video_id"))
    bagli = {str(r.get("image_id")) for r in once["variations"]}

    kapak = isd / f"{cift}_kapak.png"
    video = isd / f"{cift}.mp4"
    for uzak, yerel in ((f"{KAYNAK}/KAPAK/{cift}_V11_kapak.png", kapak),
                        (f"{KAYNAK}/VIDEO/{cift}_V11.mp4", video)):
        if rclone("copyto", uzak, str(yerel)).returncode != 0:
            raise RuntimeError(f"kaynak inmedi: {uzak}")
    with Image.open(kapak) as im:
        if im.size != (2400, 3000):
            raise RuntimeError(f"yeni kapak boyutu {im.size}")

    # yedek
    yedek = isd / "yedek"
    yedek.mkdir(exist_ok=True)
    for f in yedek.iterdir():
        f.unlink()
    r1 = once["images"][0]
    download(r1.get("url_fullxfull") or r1.get("url_570xN"),
             yedek / f"kapak_{rank1_id}.png")
    ev = once["videos"][0]
    vurl = ev.get("video_url") or (ev.get("video_urls") or [{}])[0].get("video_url")
    if vurl:
        download(vurl, yedek / f"video_{eski_video_id}.mp4")
    (yedek / "snapshot.json").write_text(json.dumps(
        {"ilan": lid, "cift": cift,
         "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "ozet": ozet(once), "galeri_ham": image_map(once["images"])},
        ensure_ascii=False, indent=1), encoding="utf-8")
    if rclone("copy", str(yedek), f"{YAYIN}/YEDEK/{lid}", "-q").returncode != 0:
        raise RuntimeError("yedek yuklenemedi")

    # yazma
    with open(kapak, "rb") as fh:
        yuklenen = api.post_file(
            f"/shops/{shop}/listings/{lid}/images",
            files={"image": (kapak.name, fh, "image/png")},
            data={"rank": "1", "alt_text":
                  f"{cift.replace('_', ' ').title()} gold zodiac couple art "
                  "in a midnight blue interior"})
    yeni_kapak = str(yuklenen.get("listing_image_id") or "")
    if not yeni_kapak:
        raise RuntimeError("yeni kapak id donmedi; eski kapak korunuyor")
    api.post_file(f"/shops/{shop}/listings/{lid}/images",
                  files={"listing_image_id": (None, yeni_kapak), "rank": (None, "1")})
    ara = anlik(api, shop, lid)
    ara_idler = {str(x.get("listing_image_id")) for x in ara["images"]}
    ara_kontrol = {
        "gorsel_14": len(ara["images"]) == 14,
        "yeni_kapak_galeride": yeni_kapak in ara_idler,
        "eski_gorseller_duruyor": all(str(x.get("listing_image_id")) in ara_idler
                                      for x in once["images"]),
        "video_degismedi": video_ids(once["videos"]) == video_ids(ara["videos"]),
        "varyasyon_degismedi": variation_map(once["variations"]) ==
                               variation_map(ara["variations"])}
    if not all(ara_kontrol.values()):
        raise RuntimeError(f"yukleme geri-okumasi: {ara_kontrol}")
    if rank1_id in bagli:
        raise RuntimeError("eski kapak varyasyona bagli (silme yok)")
    api.delete(f"/shops/{shop}/listings/{lid}/images/{rank1_id}")
    with open(video, "rb") as fh:
        yv = api.post_file(f"/shops/{shop}/listings/{lid}/videos",
                           files={"video": (video.name, fh, "video/mp4")},
                           data={"name": video.name})
    yeni_video = str(yv.get("video_id") or "")
    if not yeni_video:
        raise RuntimeError("yeni video id donmedi")
    if yeni_video != eski_video_id:
        api.delete(f"/shops/{shop}/listings/{lid}/videos/{eski_video_id}")

    # dogrulama
    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        idler = [str(x.get("listing_image_id")) for x in son["images"]]
        if (len(idler) == 13 and idler[0] == yeni_kapak and len(son["videos"]) == 1
                and str(video_ids(son["videos"])[0]) == yeni_video):
            break
        if time.time() >= bitis:
            break
        time.sleep(10)
    eski_sira = [str(x.get("listing_image_id")) for x in once["images"]
                 if str(x.get("listing_image_id")) != rank1_id]
    yeni_sira = [str(x.get("listing_image_id")) for x in son["images"]
                 if str(x.get("listing_image_id")) != yeni_kapak]
    meta = next((x for x in son["images"]
                 if str(x.get("listing_image_id")) == yeni_kapak), {})
    o, s = ozet(once), ozet(son)
    kapilar = {
        "rank1_yeni_kapak": bool(son["images"]) and
                            str(son["images"][0].get("listing_image_id")) == yeni_kapak,
        "kapak_2400x3000": [meta.get("full_width"), meta.get("full_height")] ==
                           [2400, 3000],
        "gorsel_13": len(son["images"]) == 13,
        "diger_12_ayni": yeni_sira == eski_sira,
        "tek_video": len(son["videos"]) == 1,
        "video_yeni": bool(son["videos"]) and
                      str(video_ids(son["videos"])[0]) == yeni_video,
        "varyasyon_ayni": o["varyasyon"] == s["varyasyon"],
        "baslik_ayni": o["baslik"] == s["baslik"],
        "durum_ayni": o["durum"] == s["durum"]}
    if not all(kapilar.values()):
        raise RuntimeError(f"YAZMA SONRASI KAPI: {kapilar} | canli: "
                           f"{json.dumps(s, ensure_ascii=False)[:600]}")
    return {"yeni_kapak_id": yeni_kapak, "yeni_video_id": yeni_video,
            "silinen_kapak_id": rank1_id, "silinen_video_id": eski_video_id,
            "kapilar": kapilar}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--is-dizin", default="_work/yayin76")
    a = ap.parse_args()
    if a.apply and a.confirm != "YAYIN_76":
        raise SystemExit("DUR: apply icin confirm 'YAYIN_76' olmali")
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
    ilerle(f"kota once: {kota_once}")

    harita = gold_haritasi(isd)
    hepsi = ciftler()
    if a.limit:
        hepsi = hepsi[:a.limit]
    durum_yerel = isd / "state.json"
    durum = {"tamam": {}, "atlandi": {}, "hata": {}}
    if rclone("copyto", f"{YAYIN}/state.json", str(durum_yerel)).returncode == 0:
        try:
            durum = json.loads(durum_yerel.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    for k in ("tamam", "atlandi", "hata"):
        durum.setdefault(k, {})
    kalan = [(l, c) for l, c in hepsi if l not in durum["tamam"]]
    ilerle(f"ilan {len(hepsi)} | tamam {len(durum['tamam'])} | kosulacak {len(kalan)} "
           f"| Gold B haritasi {len(harita)} kayit | mod "
           f"{'YAZMA' if a.apply else 'KURU DENEME'}")

    rapor = isd / "YAYIN_RAPORU.csv"
    if rclone("copyto", f"{YAYIN}/YAYIN_RAPORU.csv", str(rapor)).returncode != 0:
        with rapor.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(SUTUN)

    def yaz_satir(satir):
        with rapor.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore").writerow(satir)
        rclone("copyto", str(rapor), f"{YAYIN}/YAYIN_RAPORU.csv")
        durum_yerel.write_text(json.dumps(durum, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        rclone("copyto", str(durum_yerel), f"{YAYIN}/state.json")

    t0 = time.time()
    for j, (lid, cift) in enumerate(kalan, start=1):
        ts = time.time()
        kota = int(api.remaining or 0)
        if kota and kota < KOTA_ALT:
            ilerle(f"DUR: kota {kota} < {KOTA_ALT}")
            break
        satir = {"listing_id": lid, "cift": cift, "durum": "ATLANDI", "neden": "",
                 "kota": kota}
        try:
            once = anlik(api, shop, lid)
            uygun, neden = onkontrol(once, harita.get(lid))
            if not uygun:
                satir["neden"] = neden
                durum["atlandi"][lid] = neden
                ilerle(f"{j}/{len(kalan)} {lid} {cift} ATLANDI: {neden}")
            elif not a.apply:
                satir["durum"] = "KURU_DENEME_UYGUN"
                ilerle(f"{j}/{len(kalan)} {lid} {cift} uygun (yazma yok)")
            else:
                sonuc = yayinla(api, shop, lid, cift, once, isd)
                satir.update({"durum": "TAMAM", **{k: v for k, v in sonuc.items()
                                                   if k != "kapilar"}})
                durum["tamam"][lid] = {"cift": cift,
                                       "kapak": sonuc["yeni_kapak_id"],
                                       "video": sonuc["yeni_video_id"]}
                durum["atlandi"].pop(lid, None)
                ilerle(f"{j}/{len(kalan)} {lid} {cift} TAMAM kapak "
                       f"{sonuc['yeni_kapak_id']} video {sonuc['yeni_video_id']}")
        except RuntimeError as e:
            satir.update({"durum": "HATA", "neden": str(e)[:200]})
            durum["hata"][lid] = str(e)[:300]
            satir["sn"] = round(time.time() - ts, 1)
            yaz_satir(satir)
            ilerle(f"DUR (yazma sonrasi kapi): {lid} {cift}: {e}")
            print(json.dumps({"durdu": lid, "neden": str(e)[:300],
                              "tamam": len(durum["tamam"])}, ensure_ascii=False))
            return 3
        except Exception as e:  # beklenmeyen: o ilan HATA, kosu durur
            satir.update({"durum": "HATA", "neden": f"{type(e).__name__}: {e}"[:200]})
            durum["hata"][lid] = satir["neden"]
            satir["sn"] = round(time.time() - ts, 1)
            yaz_satir(satir)
            ilerle(f"DUR (beklenmeyen): {lid}: {satir['neden']}")
            return 3
        satir["sn"] = round(time.time() - ts, 1)
        yaz_satir(satir)
        gec = time.time() - t0
        if j % 1 == 0:
            ilerle(f"  ilerleme {j}/{len(kalan)} (%{100 * j / len(kalan):.1f}) "
                   f"gecen {sure_yaz(gec)} kalan ~{sure_yaz(gec / j * (len(kalan) - j))}"
                   f" | kota {api.remaining}")

    ilerle(f"BITTI | tamam {len(durum['tamam'])} | atlandi {len(durum['atlandi'])} "
           f"| hata {len(durum['hata'])} | kota {kota_once} -> {api.remaining}")
    print(json.dumps({"tamam": len(durum["tamam"]), "atlandi": durum["atlandi"],
                      "hata": durum["hata"], "kota_once": kota_once,
                      "kota_sonra": api.remaining}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
