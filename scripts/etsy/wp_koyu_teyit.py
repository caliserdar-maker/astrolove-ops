#!/usr/bin/env python3
"""
KOYU EDISYON TEYIDI - 5 Eyl 2026 (Mo).

Verilen render'da (ekran koyu edisyonla uretilmis) her ekranin 4 kosesini tam
cozunurlukte kirpip 2x2 tek dosyaya koyar (M16_) ve maske ∩ quad DISINDAKI
ince seritte L ortalamasini olcer: serit koyu (cerceve) ise doku maskeden
geliyordu; serit acik kaldiysa doku master'a gomulu.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, log  # noqa: E402
from wp_master_temizle import L_ort, serit_maskesi  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--ekran", action="append", default=[], help="SAHNE:EKRAN")
    ap.add_argument("--boy", type=int, default=220)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for e in a.ekran:
        scene, eid = e.split(":")
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        ad = cfg.get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(scene=scene, pair=a.pair)
        r = imread(Path(a.render_dir) / ad)
        s = next(x for x in calib["scenes"][src]["screens"] if int(x["id"]) == int(eid))
        q = np.asarray(s["quad"], np.float32)
        soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{eid}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        serit, _, halka = serit_maskesi(soft, q, 14, 14, r.shape)
        log(f"{scene}/{eid} {s['device']} ({s['edition']}): serit L {L_ort(r, serit):.1f} | cerceve halkasi L {L_ort(r, halka):.1f} "
            f"| serit {int(serit.sum())} px")
        b = a.boy
        kare = []
        for (x, y) in q:
            x0 = int(round(x)) - b // 2; y0 = int(round(y)) - b // 2
            x0 = max(0, min(x0, r.shape[1] - b)); y0 = max(0, min(y0, r.shape[0] - b))
            kare.append(r[y0:y0 + b, x0:x0 + b].copy())
        ust = np.hstack([kare[0], kare[1]]); alt = np.hstack([kare[3], kare[2]])
        panel = np.vstack([ust, alt])
        yol = Path(a.out_dir) / f"M16_{a.pair}_{scene}_S{eid}_KOYU_KOSELER.jpg"
        cv2.imwrite(str(yol), panel, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log(f"  kanit: {yol.name} ({panel.shape[1]}x{panel.shape[0]}, 1:1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
