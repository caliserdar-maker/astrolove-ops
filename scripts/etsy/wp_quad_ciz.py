#!/usr/bin/env python3
"""
QUAD CIZIMI - 5 Eyl 2026.

Verilen gorselin uzerine calib'deki quad'i ince cizgiyle cizer. Isaretleme
sablonu uretmek icin kullanilir: Mo bu cizginin uzerine kendi duzeltmesini
kirmizi ile cizer. Kirpma ve buyutme yapilmaz.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, log  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gorsel", required=True)
    ap.add_argument("--calib-json", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, default=-1, help="-1: tum ekranlar")
    ap.add_argument("--kalinlik", type=int, default=2)
    ap.add_argument("--bgr", default="255,0,0", help="cizgi rengi (varsayilan mavi)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    im = imread(Path(a.gorsel))
    calib = json.loads(Path(a.calib_json).read_text())
    src = SCENES[a.scene].get("calib_from", a.scene)
    renk = tuple(int(v) for v in a.bgr.split(","))
    n = 0
    for s in calib["scenes"][src]["screens"]:
        if a.screen >= 0 and int(s["id"]) != a.screen:
            continue
        q = np.asarray(s["quad"], np.float64)
        cv2.polylines(im, [np.int32(np.round(q))], True, renk, a.kalinlik, cv2.LINE_8)
        log(f"  {a.scene}/{s['id']} {s['device']}: {[[round(float(x), 1), round(float(y), 1)] for x, y in q]}")
        n += 1
    if n == 0:
        log("DUR: cizilecek ekran bulunamadi")
        return 3
    cv2.imwrite(a.out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    log(f"{a.out}: {n} ekran cizildi, {im.shape[1]}x{im.shape[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
