#!/usr/bin/env python3
"""V02 girdi kesfi (salt okur): MOCKUP_V2 SET dosyalari + uretim betigi izi.

Drive'dan: WALLPAPER/MOCKUP_V2/AQUARIUS_GEMINI/*.jpg, SCRIPTS dokumu,
WALLPAPER dokumu (isim listesi), sahne sablonu adaylari.
"""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v02")
MOCK = "gdrive:ASTROLOVE/WALLPAPER/MOCKUP_V2/AQUARIUS_GEMINI"
SCRIPTS = "gdrive:ASTROLOVE/SCRIPTS"
WALLPAPER = "gdrive:ASTROLOVE/WALLPAPER"
TEMP = "gdrive:ASTROLOVE/TEMP"


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    if p.returncode:
        log(f"lsf HATA {yol}: {p.stderr.strip()[:120]}")
        return []
    return p.stdout.splitlines()


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    setler = lsf(MOCK)
    (HEDEF / "mockup_v2_setler.txt").write_text("\n".join(setler), encoding="utf-8")
    log(f"MOCKUP_V2/AQUARIUS_GEMINI: {setler}")
    for ad in setler:
        if ad.lower().endswith((".jpg", ".png")):
            subprocess.run(["rclone", "copyto", f"{MOCK}/{ad}", str(HEDEF / ad)],
                           check=True)
    betikler = lsf(SCRIPTS)
    (HEDEF / "scripts_dokum.txt").write_text("\n".join(betikler), encoding="utf-8")
    log(f"SCRIPTS: {len(betikler)} dosya")
    for ad in betikler:
        u = ad.upper()
        if ad.endswith(".py") and any(k in u for k in
                                      ("MOCKUP", "SAHNE", "SET", "V2", "POD")):
            subprocess.run(["rclone", "copyto", f"{SCRIPTS}/{ad}",
                            str(HEDEF / "betik" / ad)], check=True)
    (HEDEF / "wallpaper_dokum.txt").write_text(
        "\n".join(lsf(WALLPAPER, "-R", "--max-depth", "3", "--files-only")),
        encoding="utf-8")
    (HEDEF / "temp_dokum.txt").write_text("\n".join(lsf(TEMP, "--dirs-only")),
                                          encoding="utf-8")
    for p in sorted(HEDEF.rglob("*")):
        if p.is_file():
            log(f"{p.relative_to(HEDEF)}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
