#!/usr/bin/env python3
"""Galeri CI rank 11 dosya kapisi (Etsy YOK, kilitsiz ayri is akisi; Serdar 30 Eki karari). Girdi: TEMP/POSTER_GALERI_V11/<damga>
klasorundeki <CIFT>_W01_KAPAK.jpg dosyalari (29 Eki iptal edilen CI kapaklari) + ayni klasorun MANIFEST.csv'si + istege bagli B3
KAPI/<kosu>/KAPI.csv. Ilan basina (data/pod/pod78_ids.csv; --sadece / --haric):
  BLOK (durum FAIL): dosya <CIFT>_W01_KAPAK.jpg yok; JPEG degil (FFD8FF + Pillow bicimi); boyut 3000x2250 degil; dosya adindaki cift
    ilan cifti degil; MANIFEST satiri yok / cift ya da kart_no farkli / sha256 farkli (--manifest verildiyse); KAPI.csv W01_KAPAK satiri
    PASS degil ya da sha256 farkli (--kapi-csv verildiyse).
  RAPOR (engellemez): tesseract OCR "Frame not included" VAR / YOK (tam gorsel + sag alt etiket kutusu 2x), cift satiri "<A> & <B>"
    VAR / YOK; tesseract yoksa ATLANDI.
Klasorde ilan cifti olmayan W01 dosyasi FAZLA olarak raporlanir (BLOK degil).
Cikti --out: CI_KAPI.csv (listing_id, cift, dosya, sha256, genislik, yukseklik, bicim, durum, neden, ocr_frame, ocr_cift, ocr_metin),
CI_KAPI.md. Cikis 0 = tum ilanlar PASS, 1 = en az bir FAIL."""
import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

BOYUT = (3000, 2250)
AD_RX = re.compile(r"^(?P<c>[A-Z]+_[A-Z]+)_W01_KAPAK\.jpg$")
FRAME_RX = re.compile(r"FRAME\s*N[O0]T\s*[I1L]NCLU")   # OCR kenar kirpmasina dayanikli (INCLUDE / INCLUDED)
ETIKET_KUTU = (2050, 1900, 2600, 2180)   # renk kartlarindaki "Frame not included" etiket bolgesi (galeri_v11_kapi: x 2150-2410, y 1960-2110)
KAPAK_KART = "W01_KAPAK"


def log(m):
    print(m, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ocr(p):
    """-> (frame VAR/YOK/ATLANDI, cift metni (buyuk harf), ham metin kisaltmasi)"""
    if not shutil.which("tesseract"):
        return "ATLANDI", "", "tesseract yok"
    metin = []
    with tempfile.TemporaryDirectory() as td:
        k = Path(td) / "kutu.png"
        with Image.open(p) as im:
            im.convert("L").crop(ETIKET_KUTU).resize(((ETIKET_KUTU[2] - ETIKET_KUTU[0]) * 2, (ETIKET_KUTU[3] - ETIKET_KUTU[1]) * 2)).save(k)
        for x in (str(p), str(k)):
            r = subprocess.run(["tesseract", x, "-", "--psm", "3"], capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, OMP_THREAD_LIMIT="1"))
            metin.append(r.stdout or "")
    t = " ".join(" ".join(metin).upper().split())
    return ("VAR" if FRAME_RX.search(t) else "YOK"), t, t[:160]


def kontrol(r, d, man, kapi, ocr_ac):
    cift, lid = r["cift"], r["listing_id"]
    ad = f"{cift}_{KAPAK_KART}.jpg"
    p = Path(d) / ad
    s = dict(listing_id=lid, cift=cift, dosya=ad, sha256="", genislik="", yukseklik="", bicim="", durum="FAIL", neden="",
             ocr_frame="", ocr_cift="", ocr_metin="")
    neden = []
    if not p.exists():
        s["neden"] = "dosya yok"
        return s
    m = AD_RX.match(p.name)
    if not m or m.group("c") != cift:
        neden.append(f"dosya adindaki cift {m.group('c') if m else '?'} != ilan {cift}")
    with open(p, "rb") as f:
        bas = f.read(3)
    try:
        with Image.open(p) as im:
            s.update(bicim=im.format or "", genislik=im.size[0], yukseklik=im.size[1])
    except Exception as e:   # noqa: BLE001
        neden.append(f"gorsel acilamadi ({str(e)[:60]})")
    if bas != b"\xff\xd8\xff" or s["bicim"] != "JPEG":
        neden.append(f"JPEG degil (bicim {s['bicim'] or '?'})")
    if (s["genislik"], s["yukseklik"]) != BOYUT:
        neden.append(f"boyut {s['genislik']}x{s['yukseklik']} (3000x2250 beklenir)")
    s["sha256"] = sha256(p)
    if man is not None:
        mr = man.get(ad)
        if not mr:
            neden.append("MANIFEST satiri yok")
        elif mr.get("cift") != cift or mr.get("kart_no") != KAPAK_KART or mr.get("sha256") != s["sha256"]:
            neden.append("MANIFEST cift / kart_no / sha256 farkli")
    if kapi is not None:
        kr = kapi.get((cift, KAPAK_KART))
        if not kr:
            neden.append("KAPI.csv W01_KAPAK satiri yok")
        elif kr.get("durum") != "PASS" or kr.get("sha256") != s["sha256"] or kr.get("dosya") != ad:
            neden.append(f"KAPI.csv {kr.get('durum')} / sha256 ya da dosya adi farkli")
    if ocr_ac:
        fr, t, kisa = ocr(p)
        s.update(ocr_frame=fr, ocr_metin=kisa)
        s["ocr_cift"] = "ATLANDI" if fr == "ATLANDI" else ("VAR" if f"{r['a'].upper()} & {r['b'].upper()}" in t else "YOK")
    else:
        s.update(ocr_frame="ATLANDI", ocr_cift="ATLANDI")
    s["durum"] = "FAIL" if neden else "PASS"
    s["neden"] = "; ".join(neden)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True); ap.add_argument("--ciftler", required=True)
    ap.add_argument("--manifest", default=""); ap.add_argument("--kapi-csv", default="")
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--ocr-yok", action="store_true", help="OCR raporu atlanir")
    ap.add_argument("--is", type=int, default=4, dest="isci")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sa = {x for x in a.sadece.split(",") if x}; ha = {x for x in a.haric.split(",") if x}
    R = [r for r in csv.DictReader(open(a.ciftler, encoding="utf-8")) if (not sa or r["listing_id"] in sa) and r["listing_id"] not in ha]
    man = {r["ad"]: r for r in csv.DictReader(open(a.manifest, encoding="utf-8-sig"))} if a.manifest else None
    kapi = {(r["cift"], r["ad"]): r for r in csv.DictReader(open(a.kapi_csv, encoding="utf-8-sig"))} if a.kapi_csv else None
    t0, sonuc = time.time(), []
    with ThreadPoolExecutor(max_workers=max(1, a.isci)) as ex:
        for n, s in enumerate(ex.map(lambda r: kontrol(r, a.dir, man, kapi, not a.ocr_yok), R), 1):
            sonuc.append(s)
            e = time.time() - t0
            log(f"{s['listing_id']} {s['cift']} {s['durum']} frame {s['ocr_frame']} cift {s['ocr_cift']}"
                + (f" | {s['neden']}" if s["neden"] else ""))
            log(f"ETA: {n}/{len(R)} | gecen {e:.0f} sn | kalan {e / n * (len(R) - n):.0f} sn | %{100 * n // max(1, len(R))}")
    ciftler = {r["cift"] for r in csv.DictReader(open(a.ciftler, encoding="utf-8"))}
    fazla = sorted(p.name for p in Path(a.dir).glob(f"*_{KAPAK_KART}.jpg")
                   if not AD_RX.match(p.name) or AD_RX.match(p.name).group("c") not in ciftler)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    alan = ["listing_id", "cift", "dosya", "sha256", "genislik", "yukseklik", "bicim", "durum", "neden", "ocr_frame", "ocr_cift", "ocr_metin"]
    with open(out / "CI_KAPI.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(sonuc)
    say = {}
    for s in sonuc:
        for k in (f"durum {s['durum']}", f"frame {s['ocr_frame']}", f"cift {s['ocr_cift']}"):
            say[k] = say.get(k, 0) + 1
    with open(out / "CI_KAPI.md", "w", encoding="utf-8") as f:
        f.write("# Galeri CI rank 11 dosya kapisi\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                + f" | ilan {len(sonuc)} | FAZLA dosya {len(fazla)}\n\nOCR (rapor, engellemez): frame = \"Frame not included\" metni, "
                  "cift = \"<A> & <B>\" satiri.\n\n## FAIL\n" + "".join(f"- {s['listing_id']} {s['cift']}: {s['neden']}\n"
                                                                      for s in sonuc if s["durum"] != "PASS")
                + "\n## Frame not included VAR\n" + "".join(f"- {s['listing_id']} {s['cift']}\n" for s in sonuc if s["ocr_frame"] == "VAR")
                + "\n## FAZLA\n" + "".join(f"- {x}\n" for x in fazla))
    log(f"CI DOSYA KAPISI: " + " ".join(f"{k}={v}" for k, v in sorted(say.items())) + f" | FAZLA {len(fazla)}")
    return 0 if sonuc and all(s["durum"] == "PASS" for s in sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
