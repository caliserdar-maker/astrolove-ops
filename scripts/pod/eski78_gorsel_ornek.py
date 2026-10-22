#!/usr/bin/env python3
"""Eski 78 galeri: cerceve satisini ima eden kartlarin yeni hali (Serdar 15/17 Eki). ORNEK: 1 cift. Etsy/Drive YOK.
Canli rank -> kaynak kart (CL: data/pod/cl_galeri_final19; canli eslesme cerceve-denetim 38707202461):
  r1 01_kapak         etiket "Frame not included"
  r2 02_format        iki sutun (kart02_iki_sutun.py; ayri)
  r5 06_hediye_sahne  etiket
  r6 07_cerceveler    metin: "Four classic frames" -> "Frame it your way." (cerceve adlari ve EVERY FRAME maddeleri kalkar)
  r7 08_boylar        metin: alt satir "...and in all 4 frame colors." -> "...and as a digital file."
  r8 09_yatak_sahne   metin: alt satir + etiket
  r9 10_calisma_sahne metin: alt satir + etiket
  r10 11_yemek_sahne  metin: alt satir + etiket
  r12 13_kagit        genel kagit karti (kart12_kagit_genel.py; ayri)
  r13 14_surec        metin: alt baslik + 04 maddesi (framed kutu cumlesi kalkar)
Kullanim: eski78_gorsel_ornek.py KART_DIR DUVAR.png FONT_DIR OUT_DIR
Cikti: OUT/rXX_<kart>.jpg (3000x2250, JPEG 95, 4:4:4) + OUT/RAPOR.json (olculen font/punto/renk + QC)."""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kart_metin_degis import degistir  # noqa: E402

KD, DUVAR, FD, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
D = Image.open(DUVAR).convert("RGB")
SUT = [(100, 800), (800, 1500), (1500, 2210), (2210, 2900)]       # 07 karti 4 sutun (olculdu: merkezler ~442/1145/1852/2557)
IS = {
    "07_cerceveler": ("r06", [
        dict(kutu=(130, 190, 1500, 325), eski="Four classic frames.", yeni="Frame it your way.", aile="gar", hiza="sol", agirliklar=(400,)),
        dict(kutu=(130, 330, 1500, 395), eski="Choose the finish that suits your space.",
             yeni="Prints ship unframed, in standard frame sizes.", aile="mont", hiza="sol", agirliklar=(500,)),
        *[dict(kutu=(a, 1320, b, 1370), eski=e, yeni="", aile="mont", hiza="merkez", agirliklar=(500,))
          for (a, b), e in zip(SUT, ["Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"])],
        dict(kutu=(1100, 1485, 1900, 1525), eski="EVERY FRAME", yeni="EVERY PRINT", aile="mont", hiza="merkez", izler=tuple(range(0, 16))),
        *[dict(kutu=(a, 1580, b, 1650), eski=e, yeni=n, aile="gar", hiza="merkez", agirliklar=(400,))
          for (a, b), e, n in zip(SUT, ["20 mm wood frame", "Clear acrylic front", "No mat", "Ready to hang"],
                                  ["13 sizes", "Ships unframed", "Standard sizes", "Preview first"])],
        *[dict(kutu=(a, 1660, b, 1705), eski=e, yeni=n, aile="mont", hiza="merkez", agirliklar=(500,))
          for (a, b), e, n in zip(SUT, ["0.8 in face, satin finish", "Protects your print", "Your print fills the frame", "Hook fitted on the back"],
                                  ["From 8 × 10 in to 24 × 36 in", "Rolled or flat, packed with care", "Inch and A series formats",
                                   "We print after your approval"])],
        dict(kutu=(300, 1835, 2700, 1900), eski="Framed prints use 200 gsm enhanced matte fine art paper.",
             yeni="Frames shown for display only. Frame not included.", aile="gar", hiza="merkez", agirliklar=(400,)),
    ], False),
    "08_boylar": ("r07", [
        dict(kutu=(300, 1950, 2700, 2000), eski="Every size is available as a print and in all 4 frame colors.",
             yeni="Every size is available as a print and as a digital file.", aile="mont", hiza="merkez", agirliklar=(500,)),
    ], False),
    "09_yatak_sahne": ("r08", [
        dict(kutu=(300, 1970, 2700, 2020), eski="Five colors, thirteen sizes, four frame finishes.",
             yeni="Five colors and thirteen sizes.", aile="mont", hiza="merkez", agirliklar=(500,)),
    ], True),
    "10_calisma_sahne": ("r09", [
        dict(kutu=(300, 1970, 2700, 2020), eski="Every color comes in all four frame finishes.",
             yeni="Every color comes in all thirteen sizes.", aile="mont", hiza="merkez", agirliklar=(500,)),
    ], True),
    "11_yemek_sahne": ("r10", [
        dict(kutu=(300, 1970, 2700, 2020), eski="Framed prints arrive ready to hang.",
             yeni="Prints ship unframed, ready for your frame.", aile="mont", hiza="merkez", agirliklar=(500,)),
    ], True),
    "14_surec": ("r13", [
        dict(kutu=(130, 330, 1500, 395), eski="Prints and framed prints, made to order.", yeni="Every print is made to order.",
             aile="mont", hiza="sol", agirliklar=(500,)),
        dict(kutu=(1780, 1460, 2900, 1520), eski="size. Framed prints come boxed with corner", yeni="size. US orders are tracked.",
             aile="mont", hiza="sol", agirliklar=(500,)),
        dict(kutu=(1780, 1528, 2900, 1590), eski="guards. US orders are tracked.", yeni="", aile="mont", hiza="sol", agirliklar=(500,)),
    ], False),
}
ETIKET = {"01_kapak": "r01", "06_hediye_sahne": "r05"}
YASAK = ("frame finish", "frame color", "framed print", "wood frame", "acrylic", "gsm", "hahnem", "photo rag", "cotton", "—", "–")
rapor, ok = {}, True


def etiketle(gir, cik):
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cerceve_etiket.py"), gir, cik, FD],
                       capture_output=True, text=True)
    return r.stdout.strip().splitlines()


for ad, (rk, isler, etk) in IS.items():
    K = Image.open(os.path.join(KD, ad + ".jpg")).convert("RGB")
    yeni, rp = degistir(K, D, FD, isler)
    cik = os.path.join(OUT, f"{rk}_{ad}.jpg")
    yeni.save(cik, quality=95, subsampling=0)
    # QC: kutular disinda degisiklik yok
    A = np.asarray(K).astype(int); B = np.asarray(Image.open(cik).convert("RGB")).astype(int)
    m = np.ones(A.shape[:2], bool)
    for i in isler:
        x0, y0, x1, y1 = i["kutu"]; m[y0:y1, x0:x1] = False
    dis = int(np.abs(A - B).max(2)[m].max())
    yazi = " ".join(t for r_ in rp for t in r_["yeni"]).lower()
    yasak = [y for y in YASAK if y in yazi]
    q = dict(kutu_disi_fark=dis, yasak=yasak, olcum_hata_max=max(r_["hata"] for r_ in rp))
    if etk:
        q["etiket"] = etiketle(cik, cik)
    q["PASS"] = dis <= 6 and not yasak and (not etk or q["etiket"][-1] == "PASS")
    ok &= q["PASS"]
    rapor[ad] = dict(rank=rk, olcum=rp, qc=q)
    print(ad, rk, q)
for ad, rk in ETIKET.items():
    cik = os.path.join(OUT, f"{rk}_{ad}.jpg")
    e = etiketle(os.path.join(KD, ad + ".jpg"), cik)
    rapor[ad] = dict(rank=rk, qc=dict(etiket=e, PASS=e[-1] == "PASS")); ok &= e[-1] == "PASS"
    print(ad, rk, e)
json.dump(rapor, open(os.path.join(OUT, "RAPOR.json"), "w"), ensure_ascii=False, indent=1, default=str)
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
