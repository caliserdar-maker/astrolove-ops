#!/usr/bin/env python3
"""
QUAD'I DIK DORTGENE OTURT - 5 Eyl 2026.

Isaretten okunan quad egik olabilir. Bu script ayni quad'i, merkezini ve
boyunu koruyarak eksene paralel dikdortgene oturtur: sol/sag kenar iki
kosenin x ortalamasi, ust/alt kenar iki kosenin y ortalamasidir.
calib KOPYASINA yazar.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, log  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib-json", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads(Path(a.calib_json).read_text())
    src = SCENES[a.scene].get("calib_from", a.scene)
    hedef = next((s for s in calib["scenes"][src]["screens"] if int(s["id"]) == a.screen), None)
    if hedef is None:
        log(f"DUR: {src}/{a.screen} yok")
        return 3
    q = np.asarray(hedef["quad"], np.float64)          # TL, TR, BR, BL
    x0 = (q[0][0] + q[3][0]) / 2.0
    x1 = (q[1][0] + q[2][0]) / 2.0
    y0 = (q[0][1] + q[1][1]) / 2.0
    y1 = (q[2][1] + q[3][1]) / 2.0
    yeni = [[float(x0), float(y0)], [float(x1), float(y0)],
            [float(x1), float(y1)], [float(x0), float(y1)]]
    ust = math.degrees(math.atan2(q[1][1] - q[0][1], q[1][0] - q[0][0]))
    log(f"egik quad : {[[round(float(x), 1), round(float(y), 1)] for x, y in q]}")
    log(f"dik quad  : {[[round(v, 1) for v in p] for p in yeni]}")
    log(f"ust kenar egimi {ust:.2f} derece | dik dortgen {x1 - x0:.1f} x {y1 - y0:.1f} px")
    kaymalar = [round(math.hypot(yeni[i][0] - q[i][0], yeni[i][1] - q[i][1]), 2) for i in range(4)]
    log(f"kose kaymasi (egik -> dik): {kaymalar} px")
    hedef["quad"] = [[round(v, 1) for v in p] for p in yeni]
    Path(a.out).write_text(json.dumps(calib, indent=1))
    log(f"{a.out}: {a.scene}/{a.screen} dik dortgene oturtuldu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
