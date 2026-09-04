#!/usr/bin/env python3
"""
CERCEVE-USTTE YONTEMININ OLCUMU (once/sonra) - 4 Eyl 2026.

Iki render klasoru karsilastirilir (ornegin maske-erozyonu ciktisi ile
cerceve-ustte ciktisi). Her sahne/ekran icin RENDER UZERINDE olculur:
  gorunur sinir : |render - master| > ESIK olan bolgenin konturu, yani
                  wallpaper'in fotografi gercekten degistirdigi alan
  tirtik_rms/maks: bu konturun quad kenarina uydurulan dogrudan dik sapmasi
  tasma_px      : orijinal maskenin 0.5 sinirindan DISARI cikan gorunur piksel
Boylece "kenar tirtiklandi mi, tasma kaldi mi" iki yol icin ayni olcutle
yazilir. Uretim yok; yalniz olcum ve tablo.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, log  # noqa: E402
from wp_edge_probe import kenar_tirtik, KENAR_ADI  # noqa: E402

ESIK = 8.0
BANT_N = 8


def gorunur_kontur(render, master):
    D = np.abs(render.astype(np.float32) - master.astype(np.float32)).mean(axis=2)
    b = (D > ESIK).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return D, b


def olc(pair, etiket, render, master, calib, scene, satirlar):
    src = SCENES[scene].get("calib_from", scene)
    D, b = gorunur_kontur(render, master)
    for s in calib["scenes"][src]["screens"]:
        quad = np.asarray(s["quad"], np.float32)
        kutu = np.zeros(b.shape, np.uint8)
        cv2.fillPoly(kutu, [np.round(cv2.boxPoints(cv2.minAreaRect(quad)) ).astype(np.int32)], 1)
        kutu = cv2.dilate(kutu, np.ones((41, 41), np.uint8))
        bs = (b * kutu).astype(np.uint8)
        cs, _ = cv2.findContours(bs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cs:
            continue
        c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
        r = dict(cift=pair, sahne=scene, ekran=s["id"], cihaz=s["device"], yol=etiket)
        rmsler, mxler = [], []
        for i, ad in enumerate(KENAR_ADI):
            rms, mx, n = kenar_tirtik(c, quad[i], quad[(i + 1) % 4])
            r[f"rms_{ad}"], r[f"maks_{ad}"] = rms, mx
            if rms is not None:
                rmsler.append(rms); mxler.append(mx)
        r["tirtik_rms_ort"] = round(float(np.mean(rmsler)), 3) if rmsler else None
        r["tirtik_maks_en"] = max(mxler) if mxler else None
        satirlar.append(r)
        log(f"  {scene}/{s['id']} {s['device']:<7} {etiket:<16} tirtik rms {r['tirtik_rms_ort']} "
            f"maks {r['tirtik_maks_en']}")
    return satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--dir-a", required=True, help="1. render klasoru (or. maske erozyonu)")
    ap.add_argument("--etiket-a", default="MEVCUT")
    ap.add_argument("--dir-b", required=True, help="2. render klasoru (or. cerceve-ustte)")
    ap.add_argument("--etiket-b", default="CERCEVE-USTTE")
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    satirlar = []
    for pair in [p.strip() for p in a.pairs.split(",") if p.strip()]:
        for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
            cfg = SCENES[scene]
            master = imread(Path(a.masters) / cfg["master"])
            ad = cfg.get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg")
            ad = ad.format(scene=scene, pair=pair) if "{" in ad else ad
            log(f"--- {pair} {scene}")
            for d, et in ((a.dir_a, a.etiket_a), (a.dir_b, a.etiket_b)):
                f = Path(d) / ad
                if not f.exists():
                    log(f"  {et}: {f.name} yok")
                    continue
                olc(pair, et, imread(f), master, calib, scene, satirlar)

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)

    lines = ["## Gorunur kenar tirtiklanmasi (render uzerinde)", "",
             "| cift | sahne | ekran | cihaz | yol | tirtik rms | tirtik maks |",
             "|---|---|---|---|---|---|---|"]
    for r in satirlar:
        lines.append(f"| {r['cift']} | {r['sahne']} | {r['ekran']} | {r['cihaz']} | {r['yol']} | "
                     f"{r['tirtik_rms_ort']} | {r['tirtik_maks_en']} |")
    for et in (a.etiket_a, a.etiket_b):
        v = [r["tirtik_rms_ort"] for r in satirlar if r["yol"] == et and r["tirtik_rms_ort"] is not None]
        m = [r["tirtik_maks_en"] for r in satirlar if r["yol"] == et and r["tirtik_maks_en"] is not None]
        if v:
            lines.append(f"\n**{et}: ortalama rms {np.mean(v):.3f}, en buyuk maks {max(m):.2f} px "
                         f"({len(v)} ekran)**")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
