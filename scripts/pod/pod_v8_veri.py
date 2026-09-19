#!/usr/bin/env python3
"""V8 icin GERCEK medya disa aktarimi (salt okur).

Etsy'den referans ilanin kapagi+videosu ve ornek ilanin kapagi, Drive'dan da
V5 kosusunun urettigi ornek video indirilir. Dosyalar `_veri/v8/` altina
yazilir; workflow bunlari dala commit'ler, boylece yerelde GERCEK dosyalarla
calisilabilir (Actions artifact indirme bu ortamda engelli).

Etsy'ye YAZMA YOK: yalniz GET.
"""
import os
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import download, gallery, videos, video_url  # noqa: E402

REFERANS = "4570112095"
ORNEK = "4570110641"
KONTROL_KAPAK_ID = "8590281557"
V5_VIDEO = ("gdrive:ASTROLOVE/TEMP/POD_REFERANS_ORNEK_V5/"
            "Aquarius_Aries_4570110641_video.mp4")


def main():
    hedef = pathlib.Path("_veri/v8")
    hedef.mkdir(parents=True, exist_ok=True)
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{os.environ['ETSY_SHOP_ID']}", ok404=True)
    log(f"kota once {api.remaining}")

    gor = gallery(api, REFERANS)
    kap = next((g for g in gor if str(g.get("listing_image_id")) == KONTROL_KAPAK_ID),
               gor[0] if gor else None)
    if kap is None:
        raise SystemExit("HATA: referans kapagi yok")
    download(kap.get("url_fullxfull") or kap.get("url_570xN"),
             hedef / "referans_kapak.png")
    vid = videos(api, REFERANS)
    if not vid:
        raise SystemExit("HATA: referans videosu yok")
    download(video_url(vid[0]), hedef / "referans_video.mp4")
    log(f"referans kapak id {kap.get('listing_image_id')} | "
        f"video id {vid[0].get('video_id')}")

    gor2 = gallery(api, ORNEK)
    if not gor2:
        raise SystemExit("HATA: ornek kapagi yok")
    download(gor2[0].get("url_fullxfull") or gor2[0].get("url_570xN"),
             hedef / "ornek_kapak.png")
    log(f"ornek kapak id {gor2[0].get('listing_image_id')}")

    subprocess.run(["rclone", "copyto", V5_VIDEO,
                    str(hedef / "v5_ornek_video.mp4")], check=True)
    log(f"kota sonra {api.remaining}")
    for p in sorted(hedef.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
