#!/usr/bin/env python3
"""SALT OKUMA (Serdar 21 Eki not 1a): Drive'da herkese acik ve adinda SIPARIS/ISIM/TESLIM gecen ogelerin ICERIGINI cikarir.
Girdi: PAYLASIM_ONCE.json (drive-paylasim-kapat kaydi). Ogeler rclone backend copyid ile indirilir; gorselde OCR (tesseract),
pdf'te pdftotext, metin dosyalarinda ilk 20.000 karakter. Cikti yalniz --cikti/ICERIK.json (Drive'a sahip-yalniz yuklenir).
Loga yalniz sayi yazilir; ad/icerik loga yazilmaz. Hicbir izin/dosya degistirilmez."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

DESEN = re.compile(r"SIPARIS|ISIM|TESLIM", re.I)


def calistir(k, **kw):
    return subprocess.run(k, capture_output=True, text=True, timeout=180, **kw)


def alt_hedef(L, eslesen):
    """eslesen klasorlerin (listede acik olan) alt ogeleri; yalniz JSON ve adinda BANDI gecen gorseller."""
    cocuk = {}
    for x in L:
        for u in x.get("ust") or []:
            cocuk.setdefault(u, []).append(x)
    goruldu = {x["id"] for x in eslesen}
    kuyruk = [x["id"] for x in eslesen if x["tur"].endswith("folder")]
    secilen = []
    while kuyruk:
        for y in cocuk.get(kuyruk.pop(), []):
            if y["tur"].endswith("folder"):
                kuyruk.append(y["id"])
            elif y["id"] not in goruldu and (y["ad"].lower().endswith(".json") or "BANDI" in y["ad"]):
                goruldu.add(y["id"])
                secilen.append(y)
    return secilen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--alt", action="store_true", help="adi eslesen klasorlerin acik alt agaci: JSON + *BANDI* gorsel (adi zaten eslesenler haric)")
    a = ap.parse_args()
    L = json.load(open(a.liste))["tarama"]["drive_geneli_acik"]
    hedef = [x for x in L if DESEN.search(x["ad"])]
    if a.alt:
        hedef = alt_hedef(L, hedef)
    os.makedirs(a.cikti, exist_ok=True)
    sonuc, say = [], {"oge": len(hedef), "klasor": 0, "ocr": 0, "pdf": 0, "metin": 0, "atla": 0, "hata": 0}
    for i, x in enumerate(hedef, 1):
        k = {"id": x["id"], "ad": x["ad"], "tur": x["tur"], "ust": x.get("ust"), "metin": ""}
        if x["tur"].endswith("folder"):
            say["klasor"] += 1
            k["not"] = "klasor"
            sonuc.append(k)
            continue
        with tempfile.TemporaryDirectory() as d:
            r = calistir(["rclone", "backend", "copyid", "gdrive:", x["id"], d + "/"])
            f = [os.path.join(d, n) for n in os.listdir(d)] if r.returncode == 0 else []
            if not f:
                say["hata"] += 1
                k["not"] = "indirilemedi"
                sonuc.append(k)
                continue
            yol, ad = f[0], x["ad"].lower()
            if re.search(r"\.(jpe?g|png|webp)$", ad):
                o = calistir(["tesseract", yol, "-", "--psm", "11"])
                k["metin"], k["yontem"] = o.stdout[:4000], "ocr"
                say["ocr"] += 1
            elif ad.endswith(".pdf"):
                o = calistir(["pdftotext", "-l", "3", yol, "-"])
                k["metin"], k["yontem"] = o.stdout[:8000], "pdf"
                say["pdf"] += 1
            elif re.search(r"\.(json|txt|csv|md|html?)$", ad):
                k["metin"], k["yontem"] = open(yol, errors="replace").read()[:20000], "metin"
                say["metin"] += 1
            else:
                k["not"] = "desteklenmeyen tur"
                say["atla"] += 1
        sonuc.append(k)
        if i % 25 == 0:
            print(f"[{i}/{len(hedef)}] %{100 * i // len(hedef)}", flush=True)
    json.dump({"sayim": say, "ogeler": sonuc}, open(os.path.join(a.cikti, "ICERIK.json"), "w"), ensure_ascii=False, indent=1)
    print("SAYIM", json.dumps(say))
    return 0


if __name__ == "__main__":
    sys.exit(main())
