#!/usr/bin/env python3
"""V02 girdi kesfi 2 (salt okur): POD galeri / ETSY_UPLOAD_SETS oda sahneleri.

Canli POD videosunun odasi hangi mockup'tan geliyor? ETSY_UPLOAD_SETS ve
POD_GALLERY'deki Aquarius+Gemini MIDNIGHT_BLUE kareleri indirilir.
"""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v02b")
CIFT, ED = "AQUARIUS_GEMINI", "MIDNIGHT_BLUE"
SETS = f"gdrive:ASTROLOVE/WALL_ART/LISTING_MEDIA/ETSY_UPLOAD_SETS/{ED}/{CIFT}"
GAL = f"gdrive:ASTROLOVE/TEMP/POD_GALLERY/{CIFT}/{ED}"
ZOOM = "gdrive:ASTROLOVE/TEMP"


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    if p.returncode:
        log(f"lsf HATA {yol}: {p.stderr.strip()[:150]}")
        return []
    return p.stdout.splitlines()


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    for ad, kok in (("etsy_upload_sets", SETS), ("pod_gallery", GAL)):
        dosyalar = lsf(kok)
        (HEDEF / f"{ad}_dokum.txt").write_text("\n".join(dosyalar), encoding="utf-8")
        log(f"{ad}: {dosyalar}")
        for d in dosyalar:
            if d.lower().endswith((".jpg", ".png")) and (
                    d.startswith(("01", "02", "03")) or "MOCKUP" in d.upper()):
                subprocess.run(["rclone", "copyto", f"{kok}/{d}",
                                str(HEDEF / f"{ad}_{d}")], check=True)
    # ZOOM60 ureten klasorler (V1..V4) - hangi surumler var?
    (HEDEF / "temp_zoom_klasorler.txt").write_text(
        "\n".join(lsf(ZOOM, "--dirs-only")), encoding="utf-8")
    for p in sorted(HEDEF.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
