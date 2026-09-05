#!/usr/bin/env python3
"""
ISARET DENETIMI - 5 Eyl 2026.

Iki soru olculur:
1) Isaretli dosya hangi render'in uzerine cizilmis? (cizim pikselleri
   disarida birakilarak adaylarla ortalama fark)
2) Render'da wallpaper GERCEKTEN nerede bitiyor? |render - master| farkinin
   siniri quad ile karsilastirilir. Boylece quad degisikliginin goruntuye
   yansiyip yansimadigi sayiyla gorulur.

Olcum yapar, hicbir sey uretmez.
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
from wp_red_quad import renk_maske, quad_oku, dikdortgen, kaymalar  # noqa: E402

ESIK_FARK = 8.0


def kaynak_bul(isaret, adaylar):
    ih, iw = isaret.shape[:2]
    ciz = cv2.dilate(cv2.bitwise_or(renk_maske(isaret, "kirmizi"), renk_maske(isaret, "yesil")),
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    gecerli = (ciz == 0)
    log(f"\n=== 1) ISARET HANGI DOSYANIN UZERINE CIZILDI ===")
    log(f"  isaret {iw}x{ih}, cizim disi piksel {int(gecerli.sum())}")
    sonuc = []
    for ad, yol in adaylar:
        p = Path(yol)
        if not p.exists():
            log(f"  {ad:12s} yok")
            continue
        c = imread(p)
        c = cv2.resize(c, (iw, ih), interpolation=cv2.INTER_AREA)
        f = np.abs(c.astype(np.float32) - isaret.astype(np.float32)).mean(axis=2)
        d = float(f[gecerli].mean())
        sonuc.append((d, ad))
        log(f"  {ad:12s} ortalama fark {d:.3f}")
    if sonuc:
        sonuc.sort()
        log(f"  -> kaynak: {sonuc[0][1]} (fark {sonuc[0][0]:.3f})")
    return sonuc


def wp_siniri(render, master, quad, ad):
    q = np.asarray(quad, np.float64)
    x0, y0 = np.floor(q.min(axis=0) - 90).astype(int)
    x1, y1 = np.ceil(q.max(axis=0) + 90).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, master.shape[1]), min(y1, master.shape[0])
    f = np.abs(render[y0:y1, x0:x1].astype(np.float32) - master[y0:y1, x0:x1].astype(np.float32)).mean(axis=2)
    m = (f > ESIK_FARK).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        log(f"  {ad}: degisen bolge yok")
        return None
    c = max(cnts, key=cv2.contourArea)
    xs, ys, w, h = cv2.boundingRect(c)
    kutu = np.array([[xs, ys], [xs + w, ys], [xs + w, ys + h], [xs, ys + h]], np.float64) + [x0, y0]
    log(f"  {ad}: degisen alan {cv2.contourArea(c):.0f} px, kutu {[[round(v, 1) for v in p] for p in kutu]}")
    log(f"     quad ile kose farki {kaymalar(kutu, q)} px | quad {q[1][0] - q[0][0]:.1f}x{q[2][1] - q[1][1]:.1f}, "
        f"degisen {w}x{h}")
    return kutu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--isaret", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True)
    ap.add_argument("--aday", action="append", default=[], help="etiket=yol")
    ap.add_argument("--quad", action="append", default=[], help="etiket=json_dosyasi (calib)")
    ap.add_argument("--render", action="append", default=[], help="etiket=yol (wp siniri olculecek)")
    a = ap.parse_args()

    cfg = SCENES[a.scene]
    src = cfg.get("calib_from", a.scene)
    master = imread(Path(a.masters) / cfg["master"])
    isaret = imread(Path(a.isaret))

    kaynak_bul(isaret, [tuple(x.split("=", 1)) for x in a.aday])

    quadlar = {}
    for x in a.quad:
        ad, yol = x.split("=", 1)
        c = json.loads(Path(yol).read_text())
        s = next((s for s in c["scenes"][src]["screens"] if int(s["id"]) == a.screen), None)
        if s:
            quadlar[ad] = np.asarray(s["quad"], np.float64)

    log("\n=== 2) ISARETTEN OKUNAN QUAD'LAR ===")
    olc = master.shape[1] / isaret.shape[1]
    log(f"  olcek {olc:.4f} (isaret {isaret.shape[1]}x{isaret.shape[0]})")
    okunan = {}
    for ad, renk in (("KIRMIZI", "kirmizi"), ("YESIL", "yesil")):
        q = quad_oku(renk_maske(isaret, renk), ad)
        if q is None:
            continue
        q = q * olc
        okunan[ad] = q
        log(f"  {ad} master: {[[round(float(x), 1), round(float(y), 1)] for x, y in q]}")
        for qad, qq in quadlar.items():
            k = kaymalar(q, qq)
            log(f"     {qad:22s} kose farki {k} | maks {max(k)} px")
    if "KIRMIZI" in okunan:
        d = dikdortgen(okunan["KIRMIZI"])
        ust = math.degrees(math.atan2(okunan["KIRMIZI"][1][1] - okunan["KIRMIZI"][0][1],
                                      okunan["KIRMIZI"][1][0] - okunan["KIRMIZI"][0][0]))
        log(f"  KIRMIZI dik dortgen: {[[round(float(x), 1), round(float(y), 1)] for x, y in d]} "
            f"({d[1][0] - d[0][0]:.1f}x{d[2][1] - d[1][1]:.1f}, egim {ust:.2f} derece)")

    log("\n=== 3) RENDER'DA WALLPAPER NEREDE BITIYOR ===")
    for x in a.render:
        ad, yol = x.split("=", 1)
        p = Path(yol)
        if not p.exists():
            log(f"  {ad}: dosya yok")
            continue
        r = imread(p)
        q = quadlar.get(ad if ad in quadlar else next(iter(quadlar), ""), None)
        if q is None:
            continue
        wp_siniri(r, master, q, ad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
