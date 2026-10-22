#!/usr/bin/env python3
"""V01 kesif ek verisi (salt okur): canli POD videosunun kaynagini bulmak icin.

Drive'dan: WALLPAPER/VIDEO_V2 videosu, POD_HERO_CROP klasor dokumu ve
Aquarius+Gemini icin hero_MB.jpg + video_MB_cropped.mp4, POD V2 mockup'i.
"""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v01b")
WP = ("gdrive:ASTROLOVE/WALLPAPER/VIDEO_V2/AQUARIUS_GEMINI/"
      "WA_WP_VIDEO_AQUARIUS_GEMINI.mp4")
HERO_KOK = "gdrive:ASTROLOVE/TEMP/POD_HERO_CROP"


def lsf(yol, *ek):
    return subprocess.run(["rclone", "lsf", yol, *ek], check=True, text=True,
                          capture_output=True).stdout.splitlines()


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rclone", "copyto", WP, str(HEDEF / "wp_video_AQUARIUS_GEMINI.mp4")],
                   check=True)
    klasorler = lsf(HERO_KOK, "--dirs-only")
    (HEDEF / "pod_hero_crop_klasorler.txt").write_text("\n".join(klasorler),
                                                       encoding="utf-8")
    log(f"POD_HERO_CROP klasor: {len(klasorler)} -> {klasorler[:6]}")
    aday = [k.strip("/") for k in klasorler
            if k.upper().startswith("AQU") and "GEM" in k.upper()]
    if not aday:
        raise SystemExit(f"HATA: AQU_GEM klasoru yok: {klasorler[:20]}")
    kl = aday[0]
    icerik = lsf(f"{HERO_KOK}/{kl}")
    (HEDEF / "pod_hero_crop_icerik.txt").write_text(f"{kl}\n" + "\n".join(icerik),
                                                    encoding="utf-8")
    log(f"{kl}: {icerik}")
    for ad, yerel in (("video_MB_cropped.mp4", "pod_video_MB_cropped.mp4"),
                      ("hero_MB.jpg", "pod_hero_MB.jpg")):
        if ad in icerik:
            subprocess.run(["rclone", "copyto", f"{HERO_KOK}/{kl}/{ad}",
                            str(HEDEF / yerel)], check=True)
            log(f"indi: {ad}")
    for p in sorted(HEDEF.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
