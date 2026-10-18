#!/usr/bin/env python3
"""Kupa 78 galeri kontrolu (Serdar 18 Eki), cift basina PASS/FAIL. Etsy yok.
1. baski/: tam 7 KUPA_*_baski_2700x1050.png (alt klasor 'tasarim' sayilmaz), hepsi 2700x1050.
2. galeri/: 01-13 jpg 2576x2576 + VIDEO_<KOD>.mp4 1080x1080, sure 6.3 +/- 0.3 sn (ffprobe).
3. CANCER_LIBRA: baski dosyalari referans (dalin tasarim/) ile piksel farki 0.
4. Ayni burclu cift: kart 10'da OCR ile "left" ve "right" (Name under left/right <Burc>).
Kullanim: kupa78_kontrol.py <KOD> <cift_klasoru> <ref_tasarim_klasoru> <cikti_json>"""
import glob, json, os, re, subprocess, sys
import numpy as np
from PIL import Image

KOD, D, REF, OUT = sys.argv[1:5]
ned = []
b = sorted(glob.glob(os.path.join(D, "baski", "KUPA_*_baski_2700x1050.png")))
diger = [p for p in glob.glob(os.path.join(D, "baski", "*")) if os.path.isfile(p) and p not in b]
if len(b) != 7 or diger:
    ned.append(f"baski {len(b)} dosya (+{len(diger)} baska)")
for p in b:
    if Image.open(p).size != (2700, 1050):
        ned.append(f"{os.path.basename(p)} boyut {Image.open(p).size}")
g = sorted(glob.glob(os.path.join(D, "galeri", "[01]*.jpg")))
nums = [os.path.basename(p)[:2] for p in g]
if nums != [f"{i:02d}" for i in range(1, 14)]:
    ned.append(f"galeri sira {nums}")
for p in g:
    if Image.open(p).size != (2576, 2576):
        ned.append(f"{os.path.basename(p)} boyut {Image.open(p).size}")
v = os.path.join(D, "galeri", f"VIDEO_{KOD}.mp4"); vid = {}
if not os.path.exists(v):
    ned.append("video yok")
else:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", v], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}"); s = (j.get("streams") or [{}])[0]
    vid = dict(w=s.get("width"), h=s.get("height"), sure=round(float((j.get("format") or {}).get("duration") or 0), 2))
    if (vid["w"], vid["h"]) != (1080, 1080) or abs(vid["sure"] - 6.3) > 0.3:
        ned.append(f"video {vid}")
fark = None
if KOD == "CANCER_LIBRA":
    fark = {}
    for p in b:
        rp = os.path.join(REF, os.path.basename(p))
        if not os.path.exists(rp):
            fark[os.path.basename(p)] = "ref yok"; continue
        A = np.asarray(Image.open(p).convert("RGBA")).astype(int); B = np.asarray(Image.open(rp).convert("RGBA")).astype(int)
        fark[os.path.basename(p)] = int(np.abs(A - B).max()) if A.shape == B.shape else f"boyut {A.shape} {B.shape}"
    if any(x != 0 for x in fark.values()):
        ned.append(f"CL baski referanstan farkli {fark}")
ocr = None
b1, b2 = KOD.split("_")
if b1 == b2:
    k10 = [p for p in g if os.path.basename(p).startswith("10_")]
    if k10:
        t = subprocess.run(["tesseract", k10[0], "-", "--psm", "3"], capture_output=True, text=True).stdout
        ocr = re.sub(r"\s+", " ", t)
        if not (re.search(r"left\s+" + b1, ocr, re.I) and re.search(r"right\s+" + b2, ocr, re.I)):
            ned.append("kart10 left/right yok")
    else:
        ned.append("kart10 yok")
R = dict(cift=KOD, PASS=not ned, sorun=ned, baski=len(b), galeri=len(g), video=vid, cl_fark=fark,
         kart10_ocr=(ocr or "")[:300] if ocr is not None else None)
json.dump(R, open(OUT, "w"), ensure_ascii=False, indent=1)
print(("PASS " if not ned else "FAIL ") + KOD + (" " + "; ".join(ned) if ned else ""))
