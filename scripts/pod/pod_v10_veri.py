#!/usr/bin/env python3
"""V10 icin gercek medya disa aktarimi (salt okur).

pod_v8_veri ile ayni: referans kapak+video ve ornek kapak (Etsy GET), V5 ornek
videosu (Drive). Ek: ciftin Midnight Blue ORIGINAL_HIGH_RES posteri Drive'dan
alinir, panel oranina (1710/2220 = 0.770) en yakin oran secilir ve 2400 px
genislige kucultulup PNG olarak yazilir (234 MP dosya dala girmesin diye).
"""
import pathlib
import subprocess
import sys

from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import pod_v8_veri  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
POSTER_KOK = "gdrive:ASTROLOVE/WALL_ART/POSTERS/ORIGINAL_HIGH_RES/MIDNIGHT_BLUE"
CIFT = "AQUARIUS_ARIES"
PANEL_ORAN = 1710 / 2220


def main():
    pod_v8_veri.main()
    hedef = pathlib.Path("_veri/v8")
    ham = pathlib.Path("_work/poster")
    ham.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rclone", "copy", POSTER_KOK, str(ham),
                    "--include", f"**/{CIFT}.jpg", "-q"], check=True)
    adaylar = sorted(ham.rglob(f"{CIFT}.jpg"))
    if not adaylar:
        raise SystemExit("HATA: poster bulunamadi")
    en_iyi, en_fark = None, None
    for p in adaylar:
        with Image.open(p) as im:
            o = im.width / im.height
        f = abs(o - PANEL_ORAN)
        print(f"aday {p.relative_to(ham)}: {im.width}x{im.height} oran {o:.4f} "
              f"fark {f:.4f}")
        if en_fark is None or f < en_fark:
            en_iyi, en_fark = p, f
    with Image.open(en_iyi) as im:
        im.draft("RGB", (2400, 2400 * im.height // im.width))
        rgb = im.convert("RGB")
        rgb = rgb.resize((2400, round(2400 * rgb.height / rgb.width)),
                         Image.Resampling.LANCZOS)
        rgb.save(hedef / "poster_aquarius_aries.png")
    (hedef / "poster_kaynak.txt").write_text(
        f"{en_iyi.relative_to(ham)} oran farki {en_fark:.4f}\n", encoding="utf-8")
    print(f"secilen poster: {en_iyi.relative_to(ham)} -> "
          f"{rgb.width}x{rgb.height} PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
