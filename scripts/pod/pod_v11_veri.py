#!/usr/bin/env python3
"""V11 veri + envanter (salt okur, Drive).

1) 01_EXPORTS/MIDNIGHT_BLUE ile 78 ZOOM60 karsilastirilir -> eksik cift.
2) Her ZOOM60 mockup icin poster kutusu (WA_VIDEO_V01_BATCH_V5.kutu_olc) olculur;
   dosyalar tek tek inip olculdukten sonra silinir. Her ciftte ETA yazilir.
3) Ornek ciftlerin V01 MB videolari dala alinir.
"""
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ED = "MIDNIGHT_BLUE"
HEDEF = pathlib.Path("_veri/v11")
IS = pathlib.Path("_work/v11")
BETIK = "gdrive:ASTROLOVE/SCRIPTS/WA_VIDEO_V01_BATCH_V5.py"
ZOOM = f"gdrive:ASTROLOVE/TEMP/WA_HERO_ZOOM_V4/{ED}"
EXP = ("gdrive:ASTROLOVE/WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/"
       f"01_EXPORTS/{ED}")
POS = f"gdrive:ASTROLOVE/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/{ED}/3X4"
ORNEK = ("AQUARIUS_GEMINI", "AQUARIUS_ARIES", "ARIES_LEO", "SCORPIO_TAURUS")
KESME = "# ================== ADIM 1: KALITE KAPISI"


def lsf(yol, *ek):
    p = subprocess.run(["rclone", "lsf", yol, *ek], text=True, capture_output=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


def kopya(kaynak, hedef):
    return subprocess.run(["rclone", "copyto", kaynak, str(hedef)]).returncode == 0


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def betik_yukle():
    yol = IS / "batch.py"
    if not kopya(BETIK, yol):
        raise SystemExit("HATA: uretim betigi inmedi")
    kaynak = yol.read_text(encoding="utf-8")
    bas = kaynak[:kaynak.index(KESME)]
    bas = bas.replace("DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'",
                      f"DRIVE_ROOT = {str((IS / 'agac').resolve())!r}")
    bas = bas.replace("EDITION    = 'PURE_WHITE'", f"EDITION    = {ED!r}")
    agac = IS / "agac"
    for d in ("TEMP/WA_HERO_ZOOM_V4/" + ED,
              f"WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION/{ED}/3X4",
              "WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/01_EXPORTS"):
        (agac / d).mkdir(parents=True, exist_ok=True)
    ns = {"__name__": "wa_v01_batch"}
    exec(compile(bas, "batch.py", "exec"), ns)
    return ns


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    IS.mkdir(parents=True, exist_ok=True)
    zoom = [s for s in lsf(ZOOM) if s.endswith("ZOOM60.png")]
    ciftler = sorted(s.replace("WA_06_MOCKUP_", "").replace(f"_{ED}_ZOOM60.png", "")
                     for s in zoom)
    videolar = [s for s in lsf(EXP) if s.endswith(".mp4")]
    var = {s.replace("WA_VIDEO_V01_", "").replace(f"_{ED}.mp4", "") for s in videolar}
    eksik = [c for c in ciftler if c not in var]
    log(f"ZOOM60 {len(ciftler)} cift | video {len(videolar)} | EKSIK: {eksik}")

    ns = betik_yukle()
    satir = ["cift,x0,y0,x1,y1,genislik,yukseklik,skor"]
    t0 = time.time()
    for i, cift in enumerate(ciftler, start=1):
        m = IS / "m.png"
        p = IS / "p.jpg"
        ok = kopya(f"{ZOOM}/WA_06_MOCKUP_{cift}_{ED}_ZOOM60.png", m)
        ok2 = kopya(f"{POS}/WA_POSTER_{cift}_{ED}_3X4.jpg", p)
        if not (ok and ok2):
            satir.append(f"{cift},,,,,,,DOSYA_YOK")
        else:
            try:
                hero = np.array(Image.open(m).convert("RGB"))
                kutu, skor = ns["kutu_olc"](hero, str(p))
                satir.append(f"{cift},{kutu[0]},{kutu[1]},{kutu[2]},{kutu[3]},"
                             f"{kutu[2] - kutu[0]},{kutu[3] - kutu[1]},{skor:.4f}")
            except Exception as e:  # olcum hatasi raporlanir, kosu surer
                satir.append(f"{cift},,,,,,,HATA:{type(e).__name__}")
        for f in (m, p):
            f.unlink(missing_ok=True)
        gec = time.time() - t0
        if i % 5 == 0 or i == len(ciftler):
            log(f"kutu olcum {i}/{len(ciftler)} (%{100 * i / len(ciftler):.0f}) "
                f"gecen {sure(gec)} kalan ~{sure(gec / i * (len(ciftler) - i))}")
        (HEDEF / "KUTULAR.csv").write_text("\n".join(satir), encoding="utf-8")
    (HEDEF / "ENVANTER_HAM.txt").write_text(
        f"zoom60={len(ciftler)}\nvideo={len(videolar)}\neksik={','.join(eksik)}\n",
        encoding="utf-8")
    for cift in ORNEK:
        ad = f"WA_VIDEO_V01_{cift}_{ED}.mp4"
        if ad in videolar:
            kopya(f"{EXP}/{ad}", HEDEF / f"v01_{cift}.mp4")
            log(f"video indi: {cift}")
    for f in sorted(HEDEF.iterdir()):
        log(f"{f.name}: {f.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
