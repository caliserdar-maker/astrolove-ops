#!/usr/bin/env python3
"""
KOSE KIRPMALARI - ONCE / SONRA (tam cozunurluk) - 5 Eyl 2026.

Her sahnede her ekranin DORT KOSESINDEN pencere kirpilir ve iki (ya da uc)
render yan yana konur. Olcek degismez. Satirlar: ekran x kose.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, imwrite_jpeg, log  # noqa: E402

KOSE = ["SOL UST", "SAG UST", "SAG ALT", "SOL ALT"]   # quad sirasi TL,TR,BR,BL


def etiket(img, metin):
    cv2.putText(img, metin, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(img, metin, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def pencere(img, p, w):
    x = int(round(float(p[0]) - w / 2)); y = int(round(float(p[1]) - w / 2))
    x = max(0, min(img.shape[1] - w, x)); y = max(0, min(img.shape[0] - w, y))
    return img[y:y + w, x:x + w].copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--dirs", required=True, help="ETIKET=klasor,...")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--win", type=int, default=300)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    dirs = [(t.split("=")[0], t.split("=")[1]) for t in a.dirs.split(",") if t]
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    w = a.win
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        ad = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
            scene=scene, pair=a.pair)
        var = [(et, Path(d) / ad) for et, d in dirs if (Path(d) / ad).exists()]
        if len(var) < 2:
            log(f"  {scene}: yeterli dosya yok"); continue
        imgs = {et: imread(p) for et, p in var}
        src = SCENES[scene].get("calib_from", scene)
        satirlar = []
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            for i, knm in enumerate(KOSE):
                hucreler = []
                for et, _ in var:
                    c = pencere(imgs[et], quad[i], w)
                    etiket(c, f"{et}  ekran {s['id']} {knm}")
                    hucreler.append(c)
                satir = np.hstack([np.hstack([c, np.full((w, 8, 3), 255, np.uint8)])
                                   for c in hucreler])
                satirlar.append(satir)
        panel = np.vstack([np.vstack([r, np.full((8, r.shape[1], 3), 255, np.uint8)])
                           for r in satirlar])
        p = Path(a.out_dir) / f"M12_{a.pair}_{scene}_KOSELER.jpg"
        imwrite_jpeg(p, panel)
        log(f"  {p.name}: {len(satirlar)} satir ({len(var)} surum) -> {panel.shape[1]}x{panel.shape[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
