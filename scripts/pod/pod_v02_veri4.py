#!/usr/bin/env python3
"""V02 kesif 4 (salt okur): POD ilan olusturma kayitlari + kalan aday klasorler.

Canli videonun hangi dosyadan yuklendigini kayitlardan bulmak icin
POD_LISTING / POD_MASTER_LOCKED_78 CSV'leri ve aday TEMP klasorlerinin dokumu.
"""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

HEDEF = pathlib.Path("_veri/v02d")
TEMP = "gdrive:ASTROLOVE/TEMP"
KAYIT = ("POD_LISTING", "POD_MASTER_LOCKED_78", "POD_COVER_FROM_VIDEO")
ADAY = ("V01_TESHIS", "V01_V9_PILOT", "V02_TANI", "VIDEO_PILOT_ARSIV",
        "WA_VIDEO_PROBE_V1", "KONTAK_VIDEO", "POD_REFERANS_FARK")


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    for kl in KAYIT:
        dosyalar = lsf(f"{TEMP}/{kl}", "-R", "--files-only", "--max-depth", "2")
        (HEDEF / f"{kl}_dokum.txt").write_text("\n".join(dosyalar), encoding="utf-8")
        log(f"{kl}: {dosyalar[:8]}")
        for d in dosyalar:
            if d.lower().endswith((".csv", ".json", ".md")):
                y = HEDEF / f"{kl}__{d.replace('/', '_')}"
                subprocess.run(["rclone", "copyto", f"{TEMP}/{kl}/{d}", str(y)],
                               check=False)
    for kl in ADAY:
        dosyalar = lsf(f"{TEMP}/{kl}", "-R", "--files-only", "--max-depth", "3")
        (HEDEF / f"{kl}_dokum.txt").write_text("\n".join(dosyalar), encoding="utf-8")
        log(f"{kl}: {len(dosyalar)} dosya | {dosyalar[:5]}")
        for d in dosyalar:
            if "AQUARIUS_GEMINI" in d.upper() and d.lower().endswith(".mp4"):
                subprocess.run(["rclone", "copyto", f"{TEMP}/{kl}/{d}",
                                str(HEDEF / f"{kl}__{d.replace('/', '_')}")], check=False)
                log(f"indi: {kl}/{d}")
    for p in sorted(HEDEF.iterdir()):
        log(f"{p.name}: {p.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
