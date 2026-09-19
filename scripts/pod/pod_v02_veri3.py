#!/usr/bin/env python3
"""V02 kesif 3 (salt okur): eski ZOOM60/mockup yedekleri (GEMINI_YEDEK*) ve
WA_HERO_ZOOM eski surumleri - canli odanin kaynagi icin."""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v02c")
TEMP = "gdrive:ASTROLOVE/TEMP"
ARA = ("GEMINI_YEDEK5_ZOOM60", "GEMINI_YEDEK3_MOCKUP", "GEMINI_YEDEK6_VIDEO",
       "WA_HERO_ZOOM_V4")


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    if p.returncode:
        log(f"lsf HATA {yol}: {p.stderr.strip()[:150]}")
        return []
    return p.stdout.splitlines()


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    tum = lsf(TEMP, "--dirs-only")
    (HEDEF / "temp_klasorler.txt").write_text("\n".join(tum), encoding="utf-8")
    for kl in ARA:
        icerik = lsf(f"{TEMP}/{kl}", "-R", "--files-only", "--max-depth", "3")
        (HEDEF / f"{kl}_dokum.txt").write_text("\n".join(icerik), encoding="utf-8")
        log(f"{kl}: {len(icerik)} dosya | ornek {icerik[:4]}")
        for d in icerik:
            u = d.upper()
            if "AQUARIUS_GEMINI" in u and (u.endswith(".PNG") or u.endswith(".JPG")
                                           or u.endswith(".MP4")):
                yerel = HEDEF / f"{kl}__{d.replace('/', '_')}"
                subprocess.run(["rclone", "copyto", f"{TEMP}/{kl}/{d}", str(yerel)],
                               check=True)
                log(f"indi: {kl}/{d}")
    for p in sorted(HEDEF.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
