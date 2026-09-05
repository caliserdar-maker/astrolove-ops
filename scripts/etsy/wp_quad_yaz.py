#!/usr/bin/env python3
"""
VERILEN QUAD'I CALIB KOPYASINA YAZ - 5 Eyl 2026.

Quad disaridan (Mo'nun isaretinden okunmus olarak) verilir; bu script yalniz
belirtilen sahne/ekranin quad'ini degistirip KOPYA calib.json yazar.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, log  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib-json", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True)
    ap.add_argument("--quad", required=True, help="JSON: [[x,y],[x,y],[x,y],[x,y]] TL,TR,BR,BL")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    quad = json.loads(a.quad)
    if len(quad) != 4 or any(len(p) != 2 for p in quad):
        log("DUR: quad dort kose olmali")
        return 3
    calib = json.loads(Path(a.calib_json).read_text())
    src = SCENES[a.scene].get("calib_from", a.scene)
    hedef = next((s for s in calib["scenes"][src]["screens"] if int(s["id"]) == a.screen), None)
    if hedef is None:
        log(f"DUR: {src}/{a.screen} yok")
        return 3
    eski = hedef["quad"]
    kayma = [round(math.hypot(quad[i][0] - eski[i][0], quad[i][1] - eski[i][1]), 2) for i in range(4)]
    log(f"{a.scene}/{a.screen} {hedef['device']}")
    log(f"  eski quad: {[[round(float(x), 1), round(float(y), 1)] for x, y in eski]}")
    log(f"  yeni quad: {quad}")
    log(f"  kose kaymasi: {kayma} px | en buyuk {max(kayma)} px")
    hedef["quad"] = [[float(x), float(y)] for x, y in quad]
    Path(a.out).write_text(json.dumps(calib, indent=1))
    log(f"{a.out}: quad yazildi (orijinale dokunulmadi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
