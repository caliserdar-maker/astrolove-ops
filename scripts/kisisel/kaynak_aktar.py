#!/usr/bin/env python3
"""Canva kaynak sayfalarini bir kez Drive'a aktarir (Serdar karari 22 Eyl 2026).

Karar: Canva token'i Actions'a EKLENMEZ. Bunun yerine 78 cift x 5 oran x
5 edisyon = 1950 sayfa tam cozunurlukte KAYIPSIZ PNG olarak bir kez Drive'a
aktarilir; uretim bundan sonra yalniz Drive'dan okur.

Hedef yol: TEMP/KISISEL_PILOT/KAYNAK/<edisyon>/<oran>/p<NN>.png

Is bolusumu: imzali disa aktarma URL'lerini Canva MCP'si olan oturum uretir
ve Drive'a bir liste dosyasi olarak yazar; bu script Actions runner'inda
o listeyi indirir, dogrular ve Drive'a yazar (konteynerin Canva'ya cikisi,
runner'in Canva kimligi yok).

Kaldigi yerden devam: KAYNAK_DURUM.json Drive'da tutulur; listede olup
durumda "bitti" gorunen sayfalar yeniden indirilmez. Ilerleme 60 sn'de bir
yazilir (islenen/toplam, gecen, kalan, yuzde).

Dogrulama: her dosya PNG olmali, en az MIN_BAYT, PIL ile acilabilmeli ve
olcusu listede bildirilen olcuyle (varsa) birebir tutmali.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "kaynak"
DEST = "gdrive:ASTROLOVE/TEMP/KISISEL_PILOT"
DEST_K = DEST + "/KAYNAK"
DURUM_ADI = "KAYNAK_DURUM.json"
RC_SINIR = ["--timeout", "120s", "--contimeout", "20s", "--retries", "3"]

EDISYONLAR = ("blue", "black", "pure_white", "modern", "vintage")
ORANLAR = ("2x3", "3x4", "4x5", "11x14", "A")
SAYFA_N = 78
TOPLAM_HEDEF = len(EDISYONLAR) * len(ORANLAR) * SAYFA_N     # 1950
MIN_BAYT = 300_000          # olculdu: tek sayfa kayipsiz PNG 2.45-4.22 MB
YIGIN = 25                  # kac dosyada bir Drive'a yazilip durum guncellenir
ILERLEME_SN = 60
T0 = time.time()
_son_ilerleme = 0.0


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def rc(*args, capture=True, timeout=600):
    r = subprocess.run(["rclone", *RC_SINIR, *args], capture_output=capture,
                       text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): {' '.join(args[:3])}\n"
                           f"{(r.stderr or '')[-800:]}")
    return r.stdout if capture else ""


def maskele(url):
    print(f"::add-mask::{url}", flush=True)
    for parca in url.split("&"):
        if parca.startswith("X-Amz-Signature=") and len(parca) > 30:
            print(f"::add-mask::{parca.split('=', 1)[1]}", flush=True)


def yol_gecerli(yol):
    """KAYNAK/<edisyon>/<oran>/p<NN>.png bicimi disina cikilmaz."""
    p = yol.split("/")
    return (len(p) == 3 and p[0] in EDISYONLAR and p[1] in ORANLAR
            and p[2].startswith("p") and p[2].endswith(".png")
            and p[2][1:-4].isdigit() and 1 <= int(p[2][1:-4]) <= SAYFA_N)


def indir(url, hedef, deneme=4):
    son = None
    for i in range(deneme):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                veri = r.read()
            hedef.write_bytes(veri)
            return len(veri)
        except Exception as e:                                   # noqa: BLE001
            son = e
            time.sleep(2 ** i)
    raise RuntimeError(f"indirilemedi: {type(son).__name__}: {son}")


def dogrula(hedef, bayt, bekl_olcu=None):
    if bayt < MIN_BAYT:
        raise RuntimeError(f"dosya kucuk: {bayt} bayt < {MIN_BAYT}")
    with Image.open(hedef) as im:
        if im.format != "PNG":
            raise RuntimeError(f"PNG degil: {im.format}")
        im.load()                       # bozuk/yarim dosya burada patlar
        w, h, mod = im.width, im.height, im.mode
    if bekl_olcu and [w, h] != list(bekl_olcu):
        raise RuntimeError(f"olcu {w}x{h}, beklenen {bekl_olcu[0]}x{bekl_olcu[1]}")
    return w, h, mod


def durum_oku():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        rc("copy", f"{DEST}/{DURUM_ADI}", str(OUT))
    except RuntimeError:
        pass
    p = OUT / DURUM_ADI
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        d.setdefault("bitti", {})
        d.setdefault("hata", {})
        return d
    return {"bitti": {}, "hata": {}, "toplam_hedef": TOPLAM_HEDEF}


def durum_yaz(durum):
    durum["toplam_hedef"] = TOPLAM_HEDEF
    durum["bitti_n"] = len(durum["bitti"])
    durum["kalan_n"] = TOPLAM_HEDEF - len(durum["bitti"])
    durum["guncelleme"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p = OUT / DURUM_ADI
    p.write_text(json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    rc("copy", str(p), DEST, timeout=300)


def ilerleme(i, n, zorla=False):
    global _son_ilerleme
    simdi = time.time()
    if not zorla and simdi - _son_ilerleme < ILERLEME_SN:
        return
    _son_ilerleme = simdi
    gecen = simdi - T0
    hiz = i / gecen if gecen > 0 else 0
    kalan = (n - i) / hiz if hiz > 0 else float("nan")
    log(f"ILERLEME {i}/{n} (%{100 * i / n:.1f}) gecen {gecen / 60:.1f} dk, "
        f"kalan ~{kalan / 60:.1f} dk, {hiz * 60:.1f} sayfa/dk")


def yukle(yeni):
    """Indirilen dosyalari Drive'a yazar (klasor yapisi korunur)."""
    if not yeni:
        return
    rc("copy", str(OUT / "KAYNAK"), DEST_K, capture=False, timeout=1800)


def kos(a):
    OUT.mkdir(parents=True, exist_ok=True)
    liste_yolu = OUT / a.liste
    rc("copy", f"{DEST}/{a.liste}", str(OUT), timeout=300)
    liste = json.loads(liste_yolu.read_text(encoding="utf-8"))
    liste_yolu.unlink()
    # Liste iki bicimi kabul eder: {yol: url} ya da {yol: {"url":..., "olcu":[w,h]}}
    kayitlar = {}
    for yol, v in liste.items():
        if not yol_gecerli(yol):
            raise ValueError(f"gecersiz hedef yol: {yol}")
        if isinstance(v, str):
            kayitlar[yol] = {"url": v, "olcu": None}
        else:
            kayitlar[yol] = {"url": v["url"], "olcu": v.get("olcu")}
    for k in kayitlar.values():
        maskele(k["url"])

    durum = durum_oku()
    bekleyen = [y for y in kayitlar if y not in durum["bitti"]]
    log(f"liste {len(kayitlar)} sayfa; {len(kayitlar) - len(bekleyen)} zaten bitti, "
        f"{len(bekleyen)} indirilecek. Drive'da toplam "
        f"{len(durum['bitti'])}/{TOPLAM_HEDEF} sayfa var.")
    if not bekleyen:
        durum_yaz(durum)
        log("yapilacak is yok")
        return

    yeni, hata_n = [], 0
    for i, yol in enumerate(bekleyen, 1):
        hedef = OUT / "KAYNAK" / yol
        hedef.parent.mkdir(parents=True, exist_ok=True)
        try:
            bayt = indir(kayitlar[yol]["url"], hedef)
            w, h, mod = dogrula(hedef, bayt, kayitlar[yol]["olcu"])
            durum["bitti"][yol] = {"bayt": bayt, "olcu": [w, h], "mod": mod}
            durum["hata"].pop(yol, None)
            yeni.append(yol)
        except Exception as e:                                   # noqa: BLE001
            hata_n += 1
            durum["hata"][yol] = str(e)
            log(f"HATA {yol}: {e}")
            hedef.unlink(missing_ok=True)
        ilerleme(i, len(bekleyen))
        if len(yeni) >= YIGIN:
            yukle(yeni)
            durum_yaz(durum)
            log(f"{len(yeni)} sayfa Drive'a yazildi, durum guncellendi "
                f"({len(durum['bitti'])}/{TOPLAM_HEDEF})")
            yeni = []
    yukle(yeni)
    durum_yaz(durum)
    ilerleme(len(bekleyen), len(bekleyen), zorla=True)

    bitti = len(durum["bitti"])
    print("\n## KAYNAK AKTARIMI", flush=True)
    print(f"- Bu kosuda indirilen: {len(bekleyen) - hata_n}/{len(bekleyen)}", flush=True)
    print(f"- Drive'daki toplam: **{bitti}/{TOPLAM_HEDEF}** "
          f"(%{100 * bitti / TOPLAM_HEDEF:.1f})", flush=True)
    print(f"- Hata: {len(durum['hata'])}", flush=True)
    for yol, e in list(durum["hata"].items())[:10]:
        print(f"  - {yol}: {e}", flush=True)
    print(f"- Durum dosyasi: {DEST}/{DURUM_ADI}", flush=True)
    if hata_n:
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", required=True,
                    help="Drive TEMP/KISISEL_PILOT altindaki url listesi")
    kos(ap.parse_args())
