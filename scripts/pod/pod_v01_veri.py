#!/usr/bin/env python3
"""V01 yeniden uretim icin GERCEK veri disa aktarimi (salt okur).

Drive'dan: uretim betigi (WA_VIDEO_V01_BATCH_V5.py), 3 ciftin ZOOM60 mockup'i,
3 ciftin orijinal V01 MIDNIGHT_BLUE videosu, 3 ciftin OPTIMIZED 3X4 posteri,
ZOOM60 klasor envanteri (78 kontrolu).
Etsy'den (GET): 3 ilanin canli videosu ve kapagi.

Etsy'ye YAZMA YOK.
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

ED = "MIDNIGHT_BLUE"
CIFTLER = {"AQUARIUS_GEMINI": "4570112095",
           "AQUARIUS_ARIES": "4570110641",
           "SCORPIO_TAURUS": "4570224058"}
BETIK = "gdrive:ASTROLOVE/SCRIPTS/WA_VIDEO_V01_BATCH_V5.py"
ZOOM_KOK = f"gdrive:ASTROLOVE/TEMP/WA_HERO_ZOOM_V4/{ED}"
EXP_KOK = ("gdrive:ASTROLOVE/WALL_ART/LISTING_MEDIA/VIDEOS/"
           f"V01_FIREFLY_STORY/01_EXPORTS/{ED}")
POS_KOK = f"gdrive:ASTROLOVE/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/{ED}/3X4"


def kos(*arg, **kw):
    return subprocess.run(list(arg), check=True, text=True, **kw)


def main():
    hedef = pathlib.Path("_veri/v01")
    hedef.mkdir(parents=True, exist_ok=True)
    kos("rclone", "copyto", BETIK, str(hedef / "WA_VIDEO_V01_BATCH_V5.py"))

    env = subprocess.run(["rclone", "lsf", ZOOM_KOK], check=True, text=True,
                         capture_output=True).stdout
    zoom = [s for s in env.splitlines() if s.endswith("ZOOM60.png")]
    (hedef / "zoom60_envanter.txt").write_text(
        f"{len(zoom)} dosya\n" + "\n".join(sorted(zoom)), encoding="utf-8")
    log(f"ZOOM60 {ED}: {len(zoom)} dosya")

    pos_env = subprocess.run(["rclone", "lsf", POS_KOK], check=True, text=True,
                             capture_output=True).stdout.splitlines()
    (hedef / "poster_envanter.txt").write_text("\n".join(sorted(pos_env)),
                                               encoding="utf-8")
    exp_env = subprocess.run(["rclone", "lsf", EXP_KOK], check=True, text=True,
                             capture_output=True).stdout.splitlines()
    (hedef / "v01_export_envanter.txt").write_text("\n".join(sorted(exp_env)),
                                                   encoding="utf-8")
    log(f"OPTIMIZED 3X4: {len(pos_env)} | 01_EXPORTS/{ED}: {len(exp_env)}")

    for cift in CIFTLER:
        kos("rclone", "copyto", f"{ZOOM_KOK}/WA_06_MOCKUP_{cift}_{ED}_ZOOM60.png",
            str(hedef / f"mockup_{cift}.png"))
        kos("rclone", "copyto", f"{EXP_KOK}/WA_VIDEO_V01_{cift}_{ED}.mp4",
            str(hedef / f"v01_{cift}.mp4"))
        ad = next((s for s in pos_env if cift in s), None)
        if ad is None:
            raise SystemExit(f"HATA: poster yok {cift}")
        kos("rclone", "copyto", f"{POS_KOK}/{ad}", str(hedef / f"poster_{cift}.jpg"))
        log(f"{cift}: mockup+video+poster indi ({ad})")

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{os.environ['ETSY_SHOP_ID']}", ok404=True)
    log(f"kota once {api.remaining}")
    for cift, lid in CIFTLER.items():
        vid = videos(api, lid)
        if not vid:
            raise SystemExit(f"HATA: video yok {cift}")
        download(video_url(vid[0]), hedef / f"canli_{cift}.mp4")
        gor = gallery(api, lid)
        if gor:
            download(gor[0].get("url_fullxfull") or gor[0].get("url_570xN"),
                     hedef / f"canli_kapak_{cift}.png")
        log(f"{cift}: canli video id {vid[0].get('video_id')}")
    log(f"kota sonra {api.remaining}")
    for p in sorted(hedef.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
