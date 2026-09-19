#!/usr/bin/env python3
"""V01 kesif 3: canli POD videosunun sahnesi hangi kaynaktan? (salt okur)

01_EXPORTS edisyon dokumu, DEEP_BLACK V01 videosu (varsa), POD V2 mockup'i ve
POD_HERO_CROP/AQUARIUS_GEMINI/ETSY_SWAP dokumu + icindeki video.
"""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v01c")
EXP = "gdrive:ASTROLOVE/WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/01_EXPORTS"
SWAP = "gdrive:ASTROLOVE/TEMP/POD_HERO_CROP/AQUARIUS_GEMINI/ETSY_SWAP"
MOCKUP_V2 = "gdrive:ASTROLOVE/WALLPAPER"


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    ed = lsf(EXP, "--dirs-only")
    (HEDEF / "edisyonlar.txt").write_text("\n".join(ed), encoding="utf-8")
    log(f"01_EXPORTS edisyonlari: {ed}")
    for e in ed:
        e = e.strip("/")
        if e == "MIDNIGHT_BLUE":
            continue
        ad = f"WA_VIDEO_V01_AQUARIUS_GEMINI_{e}.mp4"
        if ad in lsf(f"{EXP}/{e}"):
            subprocess.run(["rclone", "copyto", f"{EXP}/{e}/{ad}",
                            str(HEDEF / f"v01_{e}.mp4")], check=True)
            log(f"indi: {e}")
    sw = lsf(SWAP, "-R")
    (HEDEF / "etsy_swap.txt").write_text("\n".join(sw), encoding="utf-8")
    log(f"ETSY_SWAP: {sw}")
    for ad in sw:
        if ad.lower().endswith(".mp4"):
            subprocess.run(["rclone", "copyto", f"{SWAP}/{ad}",
                            str(HEDEF / ("swap_" + ad.replace("/", "_")))], check=True)
            log(f"indi: swap/{ad}")
    v2 = subprocess.run(["rclone", "lsf", MOCKUP_V2, "-R", "--include",
                         "**Aquarius_Gemini_FINAL.jpg"], text=True,
                        capture_output=True).stdout.splitlines()
    (HEDEF / "v2_mockup_dokum.txt").write_text("\n".join(v2), encoding="utf-8")
    log(f"V2 mockup: {v2[:5]}")
    for yol in v2:
        if "SET07" in yol or (v2 and yol == v2[0]):
            subprocess.run(["rclone", "copyto", f"{MOCKUP_V2}/{yol}",
                            str(HEDEF / ("v2_" + pathlib.Path(yol).name))], check=True)
            log(f"indi: {yol}")
            break
    for p in sorted(HEDEF.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
