#!/usr/bin/env python3
"""
ONCE / SONRA TEK DOSYA (tam cozunurluk, buyutme yok) - 4 Eyl 2026.

Ayni bolgeden iki kirpma alinir ve ust uste konur: ustte ESKI (uretimdeki
MOCKUP_V2), altta YENI. Aralarina ayirici cizgi cizilir. Bolge sahneye gore
kalibrasyondaki quad'lardan turetilir:
  ust   : ekranlarin UST kenar bandi
  alt   : ekranlarin ALT kenar bandi
  ekran : secilen cihazin quad'i (ornegin Watch) + pay
Olcek degistirilmez; piksel piksel kirpilir.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, imwrite_jpeg, log  # noqa: E402

BANT_IC, BANT_DIS, PAY = 150, 60, 60
CIZGI = 6


def etiket(img, metin):
    cv2.putText(img, metin, (14, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(img, metin, (14, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def bolge(calib, scene, kip, sekil):
    src = SCENES[scene].get("calib_from", scene)
    ekranlar = calib["scenes"][src]["screens"]
    if kip.startswith("ekran:"):
        dev = kip.split(":", 1)[1]
        ekranlar = [s for s in ekranlar if s["device"] == dev]
    qs = [np.asarray(s["quad"], np.float32) for s in ekranlar]
    x0 = min(float(q[:, 0].min()) for q in qs) - PAY
    x1 = max(float(q[:, 0].max()) for q in qs) + PAY
    if kip == "ust":
        y = min((float(q[0][1]) + float(q[1][1])) / 2 for q in qs)
        y0, y1 = y - BANT_DIS, y + BANT_IC
    elif kip == "alt":
        y = max((float(q[2][1]) + float(q[3][1])) / 2 for q in qs)
        y0, y1 = y - BANT_IC, y + BANT_DIS
    else:
        y0 = min(float(q[:, 1].min()) for q in qs) - PAY
        y1 = max(float(q[:, 1].max()) for q in qs) + PAY
    H, W = sekil[:2]
    x0 = int(max(0, round(x0))); y0 = int(max(0, round(y0)))
    x1 = int(min(W, round(x1))); y1 = int(min(H, round(y1)))
    return x0, y0, x1, y1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--old-dir", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--spec", required=True, help="SET03:ust,SET04:alt,SET07:ekran:Watch")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for tok in [t for t in a.spec.split(",") if t]:
        parca = tok.split(":")
        scene, kip = parca[0], ":".join(parca[1:])
        ad = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
            scene=scene, pair=a.pair)
        f_old, f_new = Path(a.old_dir) / ad, Path(a.new_dir) / ad
        if not f_old.exists() or not f_new.exists():
            log(f"  {scene}: eksik ({f_old.name if not f_old.exists() else f_new.name})")
            continue
        eski, yeni = imread(f_old), imread(f_new)
        x0, y0, x1, y1 = bolge(calib, scene, kip, eski.shape)
        a1, a2 = eski[y0:y1, x0:x1].copy(), yeni[y0:y1, x0:x1].copy()
        etiket(a1, "ESKI"); etiket(a2, "YENI")
        cizgi = np.full((CIZGI, a1.shape[1], 3), (0, 0, 255), np.uint8)
        panel = np.vstack([a1, cizgi, a2])
        p = Path(a.out_dir) / f"M11_{a.pair}_{scene}_{kip.replace(':', '_')}_ESKI_YENI.jpg"
        imwrite_jpeg(p, panel)
        log(f"  {p.name}: bolge ({x0},{y0})-({x1},{y1}) = {x1 - x0}x{y1 - y0} px, panel "
            f"{panel.shape[1]}x{panel.shape[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
