#!/usr/bin/env python3
"""GOREV 0011/1: 3 TAM BOY (1240x1748) kartpostal ornegi, mevcut kartpostal.py ile (degistirmeden).
 a) CANCER_LIBRA, EMILY & JAMES   b) SAGITTARIUS_SAGITTARIUS, EMILY & JAMES (genis sembol)
 c) uzun isim testinin en uzunu (karakter): GUINEVERE ELIZABETH & BARTHOLOMEW JONATHAN (CANCER_CANCER, test78 ile ayni cift)
Isimler sahte (musteri verisi yok). Cikti: gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK/POD_TEST/TAM_BOY/."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy")); sys.path.insert(0, str(HERE.parent / "pinterest"))
try:
    import scipy  # noqa: F401
except ImportError:                                      # kisisel-pilot bagimliliklarinda scipy yok
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "scipy"], check=True)
import kartpostal as KP  # noqa: E402
import siparis_onay as O  # noqa: E402

HEDEF = "gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK/POD_TEST/TAM_BOY"
ORNEK = [("a_CANCER_LIBRA_EMILY_JAMES", "CANCER_LIBRA", "EMILY", "JAMES"),
         ("b_SAGITTARIUS_SAGITTARIUS_EMILY_JAMES", "SAGITTARIUS_SAGITTARIUS", "EMILY", "JAMES"),
         ("c_CANCER_CANCER_UZUN_ISIM", "CANCER_CANCER", "GUINEVERE ELIZABETH", "BARTHOLOMEW JONATHAN")]


def main():
    w = Path(tempfile.mkdtemp(prefix="tamboy_"))
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "kisisel-v1"], check=True)
    font = w / "Cinzel.ttf"
    font.write_bytes(subprocess.run(["git", "show", "FETCH_HEAD:assets/fonts/Cinzel.ttf"], capture_output=True, check=True).stdout)
    kaynak = w / "KAYNAK.jpg"
    assert O._rclone_indir(O.KART_KAYNAK, kaynak), "kaynak kart yok"
    sonuc, hata = [], 0
    for ad, cift, i1, i2 in ORNEK:
        poster = w / f"{cift}_poster.png"
        pk = next((u for u in O.poster_adaylari(cift) if O._rclone_indir(u, poster)), None)
        cikti = w / f"KARTPOSTAL_{ad}.jpg"
        qc = KP.kartpostal_uret(kaynak, poster, font, KP.kart_metni(i1, i2), cikti) if pk else {"PASS": False}
        from PIL import Image
        with Image.open(cikti) as im:
            olcu, dpi, fmt = im.size, im.info.get("dpi"), im.format
        up = subprocess.run(["rclone", "copyto", str(cikti), f"{HEDEF}/{cikti.name}"], capture_output=True, text=True)
        ls = subprocess.run(["rclone", "lsjson", f"{HEDEF}/{cikti.name}"], capture_output=True, text=True)
        fid = (json.loads(ls.stdout or "[]") or [{}])[0].get("ID", "") if ls.returncode == 0 else ""
        ok = bool(qc.get("PASS")) and olcu == (1240, 1748) and fmt == "JPEG" and up.returncode == 0 and fid
        hata += not ok
        satir = {"ornek": ad, "cift": cift, "poster": (pk or "YOK").split("TEMP/", 1)[-1], "PASS": ok, "qc_PASS": qc.get("PASS"),
                 "fail": [k for k, v in (qc.get("kapilar") or {}).items() if not v], "olcu": olcu, "dpi": dpi, "format": fmt,
                 "isim_cap": (lambda t: t[1] - t[0] if t else None)(qc.get("isim_cap_ust_taban")), "drive_id": fid}
        sonuc.append(satir)
        print("SATIR " + json.dumps(satir, ensure_ascii=False, default=str), flush=True)
    print(f"SONUC {len(ORNEK) - hata}/{len(ORNEK)} PASS", flush=True)
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
