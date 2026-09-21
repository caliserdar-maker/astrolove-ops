#!/usr/bin/env python3
"""
Uretim dosyasi stratejisi olcumu (Serdar, gece modu 21 Eyl 2026).

1) Drive bos alani (rclone about).
2) Tek sayfanin TAM COZUNURLUK KAYIPSIZ PNG boyutu ve indirme suresi,
   Blue sayfa 28, bes oranda.
3) 78 sayfa x 5 oran x 5 edisyon icin toplam boyut ve sure tahmini.

Toplu disa aktarma YAPILMAZ; yalniz olcum. Imzali URL'ler loga yazilmaz.
"""
import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "URETIM_OLCUM"
DEST = "gdrive:ASTROLOVE/TEMP/KISISEL_PILOT"
RC = ["--timeout", "60s", "--contimeout", "20s", "--retries", "2"]
SAYFA, ORAN_N, EDISYON_N = 78, 5, 5
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def rc(*args, timeout=300):
    r = subprocess.run(["rclone", *RC, *args], capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {args[0]}: {(r.stderr or '')[-400:]}")
    return r.stdout


def bos_alan():
    try:
        d = json.loads(rc("about", "gdrive:", "--json", timeout=120))
    except Exception as e:                                       # noqa: BLE001
        return {"hata": str(e)[:200]}
    gb = lambda v: round(v / 1e9, 2) if isinstance(v, (int, float)) else None
    return {"toplam_GB": gb(d.get("total")), "kullanilan_GB": gb(d.get("used")),
            "bos_GB": gb(d.get("free")), "cop_GB": gb(d.get("trashed"))}


def olc(liste_adi):
    OUT.mkdir(parents=True, exist_ok=True)
    rc("copy", f"{DEST}/{liste_adi}", str(OUT))
    liste = json.loads((OUT / liste_adi).read_text(encoding="utf-8"))
    (OUT / liste_adi).unlink()
    for url in liste.values():
        print(f"::add-mask::{url}", flush=True)

    satir = []
    for ad, url in liste.items():
        p = OUT / ad
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=300) as r:
            veri = r.read()
        sn = time.time() - t0
        p.write_bytes(veri)
        with Image.open(p) as im:
            olcu = im.size
        satir.append({"oran": ad.replace(".png", ""), "olcu": list(olcu),
                      "bayt": len(veri), "MB": round(len(veri) / 1e6, 2),
                      "indirme_sn": round(sn, 2),
                      "MB_sn": round(len(veri) / 1e6 / max(sn, 0.01), 1)})
        log(f"{ad}: {olcu} {len(veri)/1e6:.2f} MB, indirme {sn:.2f} sn")
        p.unlink()                      # disk doldurmasin; olcum yeterli
    return satir


def rapor(bos, satir):
    ort_mb = sum(s["MB"] for s in satir) / len(satir)
    ort_sn = sum(s["indirme_sn"] for s in satir) / len(satir)
    toplam = SAYFA * ORAN_N * EDISYON_N
    m = ["# URETIM DOSYASI OLCUMU (tek sayfa, tam cozunurluk kayipsiz PNG)", "",
         f"Kosu: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", "",
         "## 1) Drive bos alani", "",
         f"- toplam {bos.get('toplam_GB')} GB, kullanilan {bos.get('kullanilan_GB')} GB, "
         f"**bos {bos.get('bos_GB')} GB**, cop {bos.get('cop_GB')} GB"
         if "hata" not in bos else f"- OLCULEMEDI: {bos['hata']}", "",
         "## 2) Tek sayfa (Blue, sayfa 28)", "",
         "| oran | olcu | boyut (MB) | indirme (sn) | MB/sn |",
         "| --- | --- | --- | --- | --- |"]
    for s in satir:
        m.append(f"| {s['oran']} | {s['olcu'][0]}x{s['olcu'][1]} | {s['MB']} | "
                 f"{s['indirme_sn']} | {s['MB_sn']} |")
    m += ["", f"Ortalama: **{ort_mb:.2f} MB/sayfa**, indirme {ort_sn:.2f} sn/sayfa.", "",
          "## 3) Toplu disa aktarma tahmini (YAPILMADI, yalniz tahmin)", "",
          f"- {SAYFA} sayfa x {ORAN_N} oran x {EDISYON_N} edisyon = **{toplam} dosya**",
          f"- Toplam boyut: {toplam} x {ort_mb:.2f} MB = **{toplam * ort_mb / 1000:.1f} GB**",
          f"- Yalniz indirme suresi: {toplam} x {ort_sn:.2f} sn = "
          f"**{toplam * ort_sn / 3600:.1f} saat** (Canva disa aktarma suresi haric)",
          f"- Drive bos alani {bos.get('bos_GB')} GB ise: "
          + ("**YETMEZ**" if (bos.get("bos_GB") or 0) < toplam * ort_mb / 1000
             else "yeterli"), "",
          "JPEG (kalite 90) ile ayni sayfalar ~1 MB civarindadir (olculdu: "
          "referans sayfalari 0.6-2.5 MB); kayipsiz PNG yaklasik 2-10 kat buyuk.", ""]
    (OUT / "URETIM_OLCUM.md").write_text("\n".join(m), encoding="utf-8")
    (OUT / "URETIM_OLCUM.json").write_text(
        json.dumps({"bos_alan": bos, "sayfalar": satir,
                    "ortalama_MB": round(ort_mb, 2), "ortalama_sn": round(ort_sn, 2),
                    "toplam_dosya": toplam,
                    "tahmini_GB": round(toplam * ort_mb / 1000, 1),
                    "tahmini_saat": round(toplam * ort_sn / 3600, 1)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(m), flush=True)
    rc("copy", str(OUT), DEST + "/URETIM_OLCUM", timeout=300)
    log("olcum Drive'a yazildi")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", default="uretim_urls.json")
    a = ap.parse_args()
    b = bos_alan()
    log(f"Drive: {b}")
    rapor(b, olc(a.liste))
