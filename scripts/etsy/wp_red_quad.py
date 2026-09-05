#!/usr/bin/env python3
"""
KIRMIZI ISARETTEN QUAD OKUMA - 5 Eyl 2026 (Mo karari).

Olcum yapilmaz. Mo'nun mockup gorseli uzerine KIRMIZI ile cizdigi ekran
siniri tek kaynaktir: saf kirmizi pikseller (R yuksek, G/B dusuk) bulunur,
kontur cikarilir, dort kose okunur ve calib KOPYASINA yazilir. Orijinal
calib.json'a dokunulmaz.

Cizgi kalinligi icin: konturun disi ve (varsa) ici ayri okunur, iki quad'in
ortalamasi cizginin ORTA hatti sayilir.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, log  # noqa: E402

R_MIN = 100          # kirmizi sayilmak icin en az R
FARK_MIN = 45        # R - max(G,B)
KAPAT = 5            # morfolojik kapatma cekirdegi
KUCUK_KAYMA = 6.0    # kose kaymasi bunun altindaysa DUR (Mo: 4-5 px yanlis)


def kirmizi_maske(img):
    b, g, r = (img[..., i].astype(np.int16) for i in range(3))
    m = (r >= R_MIN) & ((r - np.maximum(g, b)) >= FARK_MIN)
    m = m.astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KAPAT, KAPAT))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)


def dort_kose(cnt):
    cev = cv2.arcLength(cnt, True)
    for eps in np.arange(0.005, 0.12, 0.005):
        ap = cv2.approxPolyDP(cnt, eps * cev, True)
        if len(ap) == 4:
            return ap.reshape(4, 2).astype(np.float64), f"approxPolyDP eps={eps:.3f}"
    kutu = cv2.boxPoints(cv2.minAreaRect(cnt))
    return kutu.astype(np.float64), "minAreaRect"


def sirala(p):
    p = np.asarray(p, np.float64)
    s, d = p.sum(1), (p[:, 0] - p[:, 1])
    return np.array([p[np.argmin(s)], p[np.argmax(d)], p[np.argmax(s)], p[np.argmin(d)]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--isaret", required=True, help="Mo'nun kirmizi isaretli gorseli")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True, help="calib ekran id")
    ap.add_argument("--out-calib", required=True)
    ap.add_argument("--kanit", default="", help="isaretli quad ciziminin yazilacagi jpg")
    a = ap.parse_args()

    cfg = SCENES[a.scene]
    src = cfg.get("calib_from", a.scene)
    master = imread(Path(a.masters) / cfg["master"])
    im = imread(Path(a.isaret))
    mh, mw = master.shape[:2]
    ih, iw = im.shape[:2]
    sx, sy = mw / iw, mh / ih
    log(f"isaret {iw}x{ih}, master {mw}x{mh}, olcek {sx:.4f}x{sy:.4f}")
    if abs(sx - sy) / max(sx, sy) > 0.01:
        log("DUR: isaretli gorselin en-boy orani master ile uyusmuyor")
        return 3

    m = kirmizi_maske(im)
    say = int((m > 0).sum())
    log(f"kirmizi piksel: {say}")
    if say < 200:
        log("DUR: kirmizi cizgi bulunamadi")
        return 3

    cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        log("DUR: kontur yok")
        return 3
    dis_i = max(range(len(cnts)), key=lambda i: cv2.contourArea(cnts[i]))
    q_dis, yon_dis = dort_kose(cnts[dis_i])
    log(f"dis kontur alani {cv2.contourArea(cnts[dis_i]):.0f} px ({yon_dis})")
    cocuklar = [i for i in range(len(cnts)) if hier[0][i][3] == dis_i]
    if cocuklar:
        ic_i = max(cocuklar, key=lambda i: cv2.contourArea(cnts[i]))
        q_ic, yon_ic = dort_kose(cnts[ic_i])
        log(f"ic kontur alani {cv2.contourArea(cnts[ic_i]):.0f} px ({yon_ic}) -> orta hat")
        quad = (sirala(q_dis) + sirala(q_ic)) / 2.0
    else:
        log("ic kontur yok -> dis kontur kullanildi")
        quad = sirala(q_dis)

    quad = np.array([[float(x) * sx, float(y) * sy] for x, y in quad])
    quad_r = [[round(float(x), 1), round(float(y), 1)] for x, y in quad]

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    ekranlar = calib["scenes"][src]["screens"]
    hedef = next((s for s in ekranlar if int(s["id"]) == a.screen), None)
    if hedef is None:
        log(f"DUR: {src} sahnesinde {a.screen} numarali ekran yok")
        return 3
    eski = np.asarray(hedef["quad"], np.float64)
    kayma = [round(math.hypot(quad[i][0] - eski[i][0], quad[i][1] - eski[i][1]), 2) for i in range(4)]
    log(f"\n{a.scene}/{a.screen} {hedef['device']}")
    log(f"  eski quad : {[[round(float(x),1), round(float(y),1)] for x, y in eski]}")
    log(f"  yeni quad : {quad_r}")
    log(f"  kose kaymasi (TL,TR,BR,BL): {kayma} px | en buyuk {max(kayma)} px")

    if a.kanit:
        kan = master.copy()
        cv2.polylines(kan, [np.int32(eski)], True, (255, 0, 0), 3)
        cv2.polylines(kan, [np.int32(quad)], True, (0, 0, 255), 3)
        cv2.imwrite(a.kanit, kan, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {a.kanit} (mavi eski, kirmizi yeni)")

    if max(kayma) < KUCUK_KAYMA:
        log(f"\nDUR: en buyuk kose kaymasi {max(kayma)} px (< {KUCUK_KAYMA}). "
            "Kirmizi kontur eski quad ile ayni yeri gosteriyor, bir sey yanlis.")
        return 4

    hedef["quad"] = quad_r
    Path(a.out_calib).write_text(json.dumps(calib, indent=1))
    log(f"\n{a.out_calib}: {a.scene}/{a.screen} quad'i guncellendi (orijinale dokunulmadi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
