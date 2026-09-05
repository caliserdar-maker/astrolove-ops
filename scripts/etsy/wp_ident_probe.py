#!/usr/bin/env python3
"""
CIKTI KIMLIGI: hangi surumler birbirinin ayni (SALT OKUM) - 5 Eyl 2026.

1) Verilen surum klasorlerinde ayni sahnenin sha256'lari; ayni olanlar
   gruplanir.
2) Iki calib dosyasinin (orijinal / duzeltilmis kopya) quad'lari kose kose
   karsilastirilir: gercekten farkli mi.
3) Secilen ekranin bir kosesinde iki surum yan yana konur ve farkli piksel
   sayisi yazilir (fark 0 ise duzeltme ciktiya girmemistir).
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, imwrite_jpeg, log  # noqa: E402

KOSE = ["SOL UST", "SAG UST", "SAG ALT", "SOL ALT"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", required=True, help="ETIKET=klasor,...")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--calib-a", required=True)
    ap.add_argument("--calib-b", required=True)
    ap.add_argument("--kose", default="SET07:1:0", help="SAHNE:EKRAN:KOSE_INDEKSI")
    ap.add_argument("--dir-a", required=True, help="kose karsilastirmasi: 1. surum klasoru")
    ap.add_argument("--dir-b", required=True)
    ap.add_argument("--win", type=int, default=300)
    ap.add_argument("--crop-dir", required=True)
    a = ap.parse_args()

    dirs = [(t.split("=")[0], t.split("=")[1]) for t in a.dirs.split(",") if t]
    scenes = [s.strip() for s in a.scenes.split(",") if s.strip()]

    log("=== 1) DOSYA KIMLIGI (sha256) ===")
    tablo = {}
    for scene in scenes:
        ad = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
            scene=scene, pair=a.pair)
        log(f"\n{scene}  ({ad})")
        tablo[scene] = {}
        for et, d in dirs:
            p = Path(d) / ad
            if not p.exists():
                log(f"  {et:<14} YOK")
                tablo[scene][et] = None
                continue
            h = sha(p)
            tablo[scene][et] = h
            log(f"  {et:<14} {p.stat().st_size:>9} B  {h[:16]}")
        gruplar = {}
        for et, h in tablo[scene].items():
            if h:
                gruplar.setdefault(h[:16], []).append(et)
        for h, ets in gruplar.items():
            if len(ets) > 1:
                log(f"  AYNI: {' = '.join(ets)}  ({h})")
        if all(len(v) == 1 for v in gruplar.values()):
            log("  hepsi FARKLI")

    log("\n=== 2) CALIB KARSILASTIRMASI ===")
    ca = json.loads(Path(a.calib_a).read_text())
    cb = json.loads(Path(a.calib_b).read_text())
    for scene in scenes:
        src = SCENES[scene].get("calib_from", scene)
        for sa, sb in zip(ca["scenes"][src]["screens"], cb["scenes"][src]["screens"]):
            qa = np.asarray(sa["quad"], float)
            qb = np.asarray(sb["quad"], float)
            d = [round(float(math.hypot(*(qb[i] - qa[i]))), 2) for i in range(4)]
            log(f"  {scene}/{sa['id']} {sa['device']:<7} kose kaymalari {d} px "
                f"| {'AYNI' if max(d) < 0.01 else 'FARKLI'}")
            if max(d) >= 0.01:
                log(f"      orijinal : {[[round(v,1) for v in p] for p in qa.tolist()]}")
                log(f"      duzeltilmis: {[[round(v,1) for v in p] for p in qb.tolist()]}")

    log("\n=== 3) KOSE KARSILASTIRMASI (piksel farki) ===")
    scene, sid, ki = a.kose.split(":")
    sid, ki = int(sid), int(ki)
    src = SCENES[scene].get("calib_from", scene)
    scr = next(s for s in ca["scenes"][src]["screens"] if s["id"] == sid)
    ad = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
        scene=scene, pair=a.pair)
    A, B = imread(Path(a.dir_a) / ad), imread(Path(a.dir_b) / ad)
    q = np.asarray(scr["quad"], np.float32)
    w = a.win
    x = max(0, min(A.shape[1] - w, int(round(float(q[ki][0]) - w / 2))))
    y = max(0, min(A.shape[0] - w, int(round(float(q[ki][1]) - w / 2))))
    ca_, cb_ = A[y:y + w, x:x + w], B[y:y + w, x:x + w]
    D = np.abs(ca_.astype(np.float32) - cb_.astype(np.float32)).mean(axis=2)
    farkli = int((D > 2).sum())
    log(f"  {scene}/{sid} {KOSE[ki]} penceresi ({x},{y}) {w}x{w} = {w*w} px")
    log(f"  farkli piksel (>2 seviye): {farkli}  (%{100*farkli/(w*w):.2f}) | maks fark {D.max():.1f} | "
        f"ortalama {D.mean():.3f}")
    # tum sahne farki da
    Dt = np.abs(A.astype(np.float32) - B.astype(np.float32)).mean(axis=2)
    log(f"  tum sahne: farkli piksel {int((Dt>2).sum())}, maks {Dt.max():.1f}")
    panel = np.hstack([ca_, np.full((w, 8, 3), 255, np.uint8), cb_])
    Path(a.crop_dir).mkdir(parents=True, exist_ok=True)
    p = Path(a.crop_dir) / f"M15_{a.pair}_{scene}_S{sid}_{KOSE[ki].replace(' ', '')}_URETIM_QUADFIX.jpg"
    imwrite_jpeg(p, panel)
    log(f"  {p.name}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## Kose farki\n\n{scene}/{sid} {KOSE[ki]}: {farkli} px farkli "
                     f"(maks {D.max():.1f})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
