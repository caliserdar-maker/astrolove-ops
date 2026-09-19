#!/usr/bin/env python3
"""V11 PILOT YAYIN - yalniz ilan 4570110641 (Aquarius+Aries).

Serdar onayi: bu TEK ilan icin Etsy yazma. Baska ilan id'si kabul edilmez.

ADIM 1 onkontrol (salt okur): kota, galeri (13 gorsel), video, varyasyon
baglantilari, baslik, durum; rank-1 kapak id'si Gold B state.json'daki yeni
kapak id'siyle ayni mi; rank-1 varyasyona bagli mi; yedek + snapshot.json.
ADIM 2 yazma: yeni kapak (rank 1) -> geri okuma -> eski Gold B kapagi sil;
yeni video yukle -> eski videoyu sil.
ADIM 3 dogrulama: 90 sn'ye kadar bekleyip canliyi okur, PILOT.json yazar.

Ilk uyusmazlikta durur; korlemesine devam yok.
"""
import argparse
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

ILAN = "4570110641"
CIFT = "AQUARIUS_ARIES"
KAYNAK = "gdrive:ASTROLOVE/TEMP/POD_V11_URETIM"
YAYIN = "gdrive:ASTROLOVE/TEMP/POD_V11_YAYIN"
GOLD_STATE = "gdrive:ASTROLOVE/TEMP/POD_COVER_GOLD_B_77/state.json"
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:6.1f}s] {m}")


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def dur(sebep, ek=None):
    ilerle(f"DUR: {sebep}")
    if ek is not None:
        ilerle(json.dumps(ek, ensure_ascii=False)[:1200])
    raise SystemExit(f"DUR: {sebep}")


def anlik(api, shop):
    return {"listing": api.get(f"/listings/{ILAN}") or {},
            "images": gallery(api, ILAN),
            "videos": videos(api, ILAN),
            "variations": variation_images(api, shop, ILAN)}


def ozet(s):
    return {"gorsel": [{"id": str(r.get("listing_image_id")), "rank": r.get("rank"),
                        "boyut": [r.get("full_width"), r.get("full_height")]}
                       for r in s["images"]],
            "video": [str(v) for v in video_ids(s["videos"])],
            "varyasyon": [list(x) for x in variation_map(s["variations"])],
            "baslik": s["listing"].get("title"),
            "durum": s["listing"].get("state")}


def gold_b_kapak_id(isd):
    """POD_COVER_GOLD_B_77/state.json icinde bu ilanin yeni kapak id'si."""
    y = isd / "gold_state.json"
    r = rclone("copyto", GOLD_STATE, str(y))
    if r.returncode != 0 or not y.is_file():
        return None, "gold_b state.json inmedi"
    veri = json.loads(y.read_text(encoding="utf-8"))
    yigin = [veri] if isinstance(veri, dict) else list(veri)
    bulunan = []

    def gez(d):
        if isinstance(d, dict):
            metin = json.dumps(d, ensure_ascii=False)
            if ILAN in metin:
                for anahtar in ("new_cover_id", "yeni_kapak_id", "cover_id",
                                "new_cover", "kapak_id"):
                    if d.get(anahtar):
                        bulunan.append(str(d[anahtar]))
            for v in d.values():
                gez(v)
        elif isinstance(d, list):
            for v in d:
                gez(v)

    for d in yigin:
        gez(d)
    if not bulunan:
        # ilan anahtarli sozluk duzeni
        d = veri if isinstance(veri, dict) else {}
        kayit = d.get(ILAN) or (d.get("listings") or {}).get(ILAN) or {}
        for anahtar in ("new_cover_id", "yeni_kapak_id", "cover_id"):
            if kayit.get(anahtar):
                bulunan.append(str(kayit[anahtar]))
    return (bulunan[0] if bulunan else None), (None if bulunan else "kayit bulunamadi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is-dizin", default="_work/yayin")
    a = ap.parse_args()
    if a.listing != ILAN:
        dur(f"yalniz {ILAN} onaylandi, gelen {a.listing}")
    if a.apply and a.confirm != "PILOT_4570110641":
        dur("apply icin confirm 'PILOT_4570110641' olmali")
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

    # ---------------- ADIM 1
    once = anlik(api, shop)
    o = ozet(once)
    ilerle(f"galeri {len(o['gorsel'])} gorsel | video {o['video']} | "
           f"durum {o['durum']} | baslik {str(o['baslik'])[:50]}")
    if len(once["images"]) != 13:
        dur(f"galeri 13 degil: {len(once['images'])}", o)
    if len(once["videos"]) != 1:
        dur(f"video sayisi 1 degil: {len(once['videos'])}", o)
    rank1 = once["images"][0]
    rank1_id = str(rank1.get("listing_image_id"))
    if int(rank1.get("rank") or 0) != 1:
        dur("ilk gorselin rank'i 1 degil", o)
    bagli = {str(r.get("image_id")) for r in once["variations"]}
    if rank1_id in bagli:
        dur(f"rank-1 kapak varyasyona bagli: {rank1_id}", o)
    gold_id, hata = gold_b_kapak_id(isd)
    ilerle(f"rank-1 {rank1_id} | Gold B state yeni kapak {gold_id} ({hata or 'ok'})")
    if gold_id is None:
        dur(f"Gold B kapak id okunamadi: {hata}", o)
    if gold_id != rank1_id:
        dur(f"rank-1 ({rank1_id}) Gold B kapagi ({gold_id}) degil", o)

    yedek = isd / "yedek"
    yedek.mkdir(exist_ok=True)
    download(rank1.get("url_fullxfull") or rank1.get("url_570xN"),
             yedek / f"kapak_{rank1_id}.png")
    eski_video = once["videos"][0]
    vurl = (eski_video.get("video_url") or
            (eski_video.get("video_urls") or [{}])[0].get("video_url"))
    if vurl:
        download(vurl, yedek / f"video_{eski_video.get('video_id')}.mp4")
    (yedek / "snapshot.json").write_text(json.dumps(
        {"ilan": ILAN, "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "ozet": o, "gold_b_kapak_id": gold_id,
         "galeri_ham": image_map(once["images"])}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    r = rclone("copy", str(yedek), f"{YAYIN}/YEDEK/{ILAN}", "-q")
    ilerle(f"yedek yuklendi ({'ok' if r.returncode == 0 else r.stderr[-80:]})")

    kapak = isd / f"{CIFT}_V11_kapak.png"
    video = isd / f"{CIFT}_V11.mp4"
    for uzak, yerel in ((f"{KAYNAK}/KAPAK/{CIFT}_V11_kapak.png", kapak),
                        (f"{KAYNAK}/VIDEO/{CIFT}_V11.mp4", video)):
        if rclone("copyto", uzak, str(yerel)).returncode != 0:
            dur(f"kaynak inmedi: {uzak}")
    with Image.open(kapak) as im:
        if im.size != (2400, 3000):
            dur(f"yeni kapak boyutu {im.size}")
    ilerle(f"kaynak hazir: kapak {kapak.stat().st_size} B, video {video.stat().st_size} B")

    if not a.apply:
        ilerle("KURU DENEME: Etsy yazma yok. ADIM 1 tamam.")
        print(json.dumps({"adim1": "TAMAM", "rank1": rank1_id, "gold_b": gold_id,
                          "kota_once": kota_once}, ensure_ascii=False))
        return 0

    # ---------------- ADIM 2
    ilerle("ADIM 2: yeni kapak yukleniyor (rank 1)")
    with open(kapak, "rb") as fh:
        yuklenen = api.post_file(
            f"/shops/{shop}/listings/{ILAN}/images",
            files={"image": (kapak.name, fh, "image/png")},
            data={"rank": "1", "alt_text":
                  "Aquarius Aries gold zodiac couple art in a midnight blue interior"})
    yeni_kapak = str(yuklenen.get("listing_image_id") or "")
    if not yeni_kapak:
        dur("yeni kapak id donmedi; eski kapak korunuyor")
    api.post_file(f"/shops/{shop}/listings/{ILAN}/images",
                  files={"listing_image_id": (None, yeni_kapak), "rank": (None, "1")})
    ilerle(f"yeni kapak id {yeni_kapak}")

    ara = anlik(api, shop)
    ara_idler = {str(x.get("listing_image_id")) for x in ara["images"]}
    kontrol = {
        "gorsel_14": len(ara["images"]) == 14,
        "yeni_kapak_galeride": yeni_kapak in ara_idler,
        "eski_gorseller_duruyor": all(str(x.get("listing_image_id")) in ara_idler
                                      for x in once["images"]),
        "video_degismedi": video_ids(once["videos"]) == video_ids(ara["videos"]),
        "varyasyon_degismedi": variation_map(once["variations"]) ==
                               variation_map(ara["variations"])}
    if not all(kontrol.values()):
        dur(f"yukleme geri-okumasi: {kontrol}", ozet(ara))
    ilerle(f"ara kontrol tamam: {kontrol}")

    if rank1_id in bagli:
        dur("eski kapak varyasyona bagli (silme yok)")
    api.delete(f"/shops/{shop}/listings/{ILAN}/images/{rank1_id}")
    ilerle(f"eski Gold B kapagi silindi: {rank1_id}")

    ilerle("yeni video yukleniyor")
    with open(video, "rb") as fh:
        yv = api.post_file(f"/shops/{shop}/listings/{ILAN}/videos",
                           files={"video": (video.name, fh, "video/mp4")},
                           data={"name": video.name})
    yeni_video = str(yv.get("video_id") or "")
    if not yeni_video:
        dur("yeni video id donmedi")
    ilerle(f"yeni video id {yeni_video} durum {yv.get('video_state')}")
    eski_video_id = str(eski_video.get("video_id"))
    if yeni_video != eski_video_id:
        api.delete(f"/shops/{shop}/listings/{ILAN}/videos/{eski_video_id}")
        ilerle(f"eski video silindi: {eski_video_id}")

    # ---------------- ADIM 3
    ilerle("ADIM 3: canli geri-okuma (90 sn'ye kadar)")
    son = None
    bitis = time.time() + 90
    while time.time() < bitis:
        son = anlik(api, shop)
        idler = [str(x.get("listing_image_id")) for x in son["images"]]
        if (len(idler) == 13 and idler[0] == yeni_kapak
                and len(son["videos"]) == 1
                and str(video_ids(son["videos"])[0]) == yeni_video):
            break
        ilerle(f"  bekleniyor: {len(idler)} gorsel, rank1 {idler[0] if idler else '-'}, "
               f"video {video_ids(son['videos'])}")
        time.sleep(10)
    s = ozet(son)
    eski_sira = [str(x.get("listing_image_id")) for x in once["images"]
                 if str(x.get("listing_image_id")) != rank1_id]
    yeni_sira = [str(x.get("listing_image_id")) for x in son["images"]
                 if str(x.get("listing_image_id")) != yeni_kapak]
    yeni_meta = next((x for x in son["images"]
                      if str(x.get("listing_image_id")) == yeni_kapak), {})
    kapilar = {
        "rank1_yeni_kapak": bool(son["images"]) and
                            str(son["images"][0].get("listing_image_id")) == yeni_kapak,
        "kapak_2400x3000": [yeni_meta.get("full_width"),
                            yeni_meta.get("full_height")] == [2400, 3000],
        "gorsel_13": len(son["images"]) == 13,
        "diger_12_ayni": yeni_sira == eski_sira,
        "tek_video": len(son["videos"]) == 1,
        "video_yeni": bool(son["videos"]) and
                      str(video_ids(son["videos"])[0]) == yeni_video,
        "varyasyon_ayni": variation_map(once["variations"]) ==
                          variation_map(son["variations"]),
        "baslik_ayni": o["baslik"] == s["baslik"],
        "durum_ayni": o["durum"] == s["durum"]}
    sonuc = {"ilan": ILAN, "cift": CIFT, "yeni_kapak_id": yeni_kapak,
             "silinen_kapak_id": rank1_id, "yeni_video_id": yeni_video,
             "silinen_video_id": eski_video_id, "kapilar": kapilar,
             "hepsi_gecti": all(kapilar.values()),
             "kota_once": kota_once, "kota_sonra": api.remaining,
             "once": o, "sonra": s,
             "link": f"https://www.etsy.com/listing/{ILAN}"}
    p = pathlib.Path(a.is_dizin) / "PILOT.json"
    p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(p), f"{YAYIN}/PILOT.json")
    ilerle(f"SONUC: {kapilar} | kota {kota_once} -> {api.remaining}")
    print(json.dumps({"hepsi_gecti": sonuc["hepsi_gecti"], "kapilar": kapilar,
                      "yeni_kapak": yeni_kapak, "yeni_video": yeni_video},
                     ensure_ascii=False))
    return 0 if all(kapilar.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
