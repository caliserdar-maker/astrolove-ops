#!/usr/bin/env python3
"""Kupa tek cift yeniden uretim ek kontrolu (Serdar 18 Eki).

Kullanim: kupa_ek_kontrol.py <KOD> <qc_json> <yeni_klasor> <eski_klasor> <isaret_bulunan> <isaret_beklenen>
- baski/KUPA_*_baski_2700x1050.png (7) ve galeri/01-13 jpg: yeni = eski, piksel farki 0
- video_kupa "isaret parca" bulunan = beklenen
Sonuc mevcut qc_json'a eklenir (eski_fark, isaret_parca); biri tutmazsa PASS=False.
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

KOD, QC, YENI, ESKI, BUL, BEK = sys.argv[1:7]
q = json.load(open(QC))
sorun = list(q.get("sorun") or [])

desen = ["baski/KUPA_*_baski_2700x1050.png", "galeri/[01][0-9]_*.jpg"]
fark = {}
for d in desen:
    yeni = sorted(glob.glob(os.path.join(YENI, d)))
    eski = sorted(glob.glob(os.path.join(ESKI, d)))
    yb = [os.path.relpath(p, YENI) for p in yeni]
    eb = [os.path.relpath(p, ESKI) for p in eski]
    if yb != eb:
        sorun.append(f"eski/yeni dosya listesi farkli ({d}): yeni {len(yb)} eski {len(eb)} | yalniz yeni {sorted(set(yb) - set(eb))} yalniz eski {sorted(set(eb) - set(yb))}")
    for r in sorted(set(yb) & set(eb)):
        A = np.asarray(Image.open(os.path.join(YENI, r)).convert("RGBA")).astype(int)
        B = np.asarray(Image.open(os.path.join(ESKI, r)).convert("RGBA")).astype(int)
        fark[r] = int(np.abs(A - B).max()) if A.shape == B.shape else -1
if len(fark) != 20:
    sorun.append(f"karsilastirilan dosya {len(fark)} (beklenen 20)")
kotu = {k: v for k, v in fark.items() if v != 0}
if kotu:
    sorun.append(f"eski ile fark 0 degil: {kotu}")

try:
    bul = int(BUL)
except ValueError:
    bul = None
if str(bul) != BEK.strip():
    sorun.append(f"isaret parca {bul} (beklenen {BEK})")

q["eski_fark"] = fark
q["eski_fark_max"] = max(fark.values()) if fark else None
q["isaret_parca"] = bul
q["isaret_beklenen"] = BEK
q["sorun"] = sorun
q["PASS"] = bool(q.get("PASS")) and not sorun
json.dump(q, open(QC, "w"), ensure_ascii=False, indent=1)
v = q.get("video") or {}
print(("PASS" if q["PASS"] else "FAIL"), KOD, f"isaret {bul}/{BEK}", f"eski fark max {q['eski_fark_max']} ({len(fark)} dosya)",
      f"video {v}", "|", " | ".join(sorun)[:600])
sys.exit(0 if q["PASS"] else 1)
