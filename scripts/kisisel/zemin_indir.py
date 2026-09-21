"""Canva'da hazirlanan temiz zemin PNG'lerini Drive HAZIR/ altina tasir.

Neden Actions: bu depo kabugundan Canva'nin indirme sunucusuna cikis yok
(ag politikasi yalniz GitHub'a izin veriyor), Drive'a da yalniz rclone
yetkili runner erisiyor. Bu yuzden indirme + yukleme adimi buraya alindi.

Girdi: Drive TEMP/KISISEL_PILOT/zemin_urls.json  -> {"dosya_adi": "imzali_url"}
Cikti: Drive TEMP/KISISEL_PILOT/HAZIR/<dosya_adi>

URL'ler imzali ve kisa omurlu; loga hicbiri yazilmaz, ::add-mask:: ile
maskelenir. Rapor yalniz dosya adi, bayt ve olcu icerir.
"""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "zemin"
DEST = "gdrive:ASTROLOVE/TEMP/KISISEL_PILOT"
RC_SINIR = ["--timeout", "60s", "--contimeout", "20s", "--retries", "2"]
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def rc(*args, capture=True, timeout=300):
    cmd = ["rclone", *RC_SINIR, *args]
    r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): {' '.join(args[:3])}\n"
                           f"{(r.stderr or '')[-800:]}")
    return r.stdout if capture else ""


def maskele(url):
    """URL'yi ve imzasini Actions log maskesine ekle."""
    print(f"::add-mask::{url}", flush=True)
    for parca in url.split("&"):
        if parca.startswith("X-Amz-Signature=") and len(parca) > 30:
            print(f"::add-mask::{parca.split('=', 1)[1]}", flush=True)


def indir(url, hedef, deneme=3):
    son = None
    for i in range(deneme):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                veri = r.read()
            hedef.write_bytes(veri)
            return len(veri)
        except Exception as e:                                   # noqa: BLE001
            son = e
            time.sleep(2 ** i)
    raise RuntimeError(f"indirilemedi ({hedef.name}): {type(son).__name__}")


def kos():
    OUT.mkdir(parents=True, exist_ok=True)
    liste_yolu = OUT / "zemin_urls.json"
    rc("copy", f"{DEST}/zemin_urls.json", str(OUT))
    liste = json.loads(liste_yolu.read_text(encoding="utf-8"))
    liste_yolu.unlink()
    for url in liste.values():
        maskele(url)
    log(f"{len(liste)} zemin indirilecek")

    satirlar, hata = [], []
    for i, (ad, url) in enumerate(liste.items(), 1):
        hedef = OUT / ad
        try:
            n = indir(url, hedef)
            with Image.open(hedef) as im:
                if im.format != "PNG":
                    raise RuntimeError(f"PNG degil: {im.format}")
                w, h = im.size
                mod = im.mode
            satirlar.append((ad, n, w, h, mod))
            log(f"{i}/{len(liste)} {ad}: {n} bayt, {w}x{h} {mod}")
        except Exception as e:                                   # noqa: BLE001
            hata.append((ad, str(e)))
            log(f"{i}/{len(liste)} {ad}: HATA {e}")
            hedef.unlink(missing_ok=True)

    if satirlar:
        rc("copy", str(OUT), f"{DEST}/HAZIR", "--include", "zemin_*.png",
           capture=False, timeout=600)
        log(f"{len(satirlar)} dosya {DEST}/HAZIR altina yazildi")

    print("\n## ZEMIN INDIRME", flush=True)
    for ad, n, w, h, mod in satirlar:
        print(f"- {ad}: {w}x{h} {mod}, {n/1e6:.2f} MB", flush=True)
    for ad, e in hata:
        print(f"- {ad}: HATA {e}", flush=True)
    if hata:
        sys.exit(1)


if __name__ == "__main__":
    kos()
