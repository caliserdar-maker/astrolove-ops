#!/usr/bin/env python3
"""
DELIK KONTURU: MASKEDEN mi GEOMETRIDEN mi - OLCUM (once/sonra) - 4 Eyl 2026.

Her sahne ve ekran icin iki delik uretilir ve ayni olcutle karsilastirilir:
  ONCE  : kalibre maskenin N px erode edilmisi (mevcut yol)
  SONRA : quad icine cizilen yuvarlatilmis dikdortgen (yaricap maskeden
          OLCULUR, sekil 4x cozunurlukte cizilip kucultulur, homografi ile
          quad'a oturur; maskenin ic delikleri - centik / Dynamic Island -
          sekilden cikarilir)
Olcut: delik konturunun ilgili quad kenarina uydurulan DOGRUdan dik sapmasi
(rms ve maks, px). Hedef: maks < 1 px. Uretim yok, yalniz olcum.
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
from wp_mockup_common import SCENES, erode_soft_mask, hole_shape, log  # noqa: E402
from wp_edge_probe import KENAR_ADI, kenar_tirtik  # noqa: E402


def kontur_olc(delik, quad):
    b = (delik >= 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return {}, None, None
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    out, rmsler, mxler = {}, [], []
    for i, ad in enumerate(KENAR_ADI):
        rms, mx, n = kenar_tirtik(c, quad[i], quad[(i + 1) % 4])
        out[f"rms_{ad}"], out[f"maks_{ad}"] = rms, mx
        if rms is not None:
            rmsler.append(rms); mxler.append(mx)
    return out, (round(float(np.mean(rmsler)), 3) if rmsler else None), (max(mxler) if mxler else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--inset", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    satirlar = []
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        src = SCENES[scene].get("calib_from", scene)
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            mp = Path(a.calib) / "masks" / f"{src}_{s['id']}.png"
            soft = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            if soft is None:
                log(f"  {scene}/{s['id']}: maske yok")
                continue
            soft = soft.astype(np.float32) / 255.0
            r = dict(sahne=scene, ekran=s["id"], cihaz=s["device"])
            d1 = erode_soft_mask(soft, int(round(a.inset)))
            o1, rms1, mx1 = kontur_olc(d1, quad)
            d2, yar, koseler = hole_shape(soft, quad, inset=a.inset)
            o2, rms2, mx2 = kontur_olc(d2, quad)
            r.update(once_rms=rms1, once_maks=mx1, sonra_rms=rms2, sonra_maks=mx2,
                     yaricap_medyan=yar, kose_TL=koseler[0], kose_TR=koseler[1],
                     kose_BL=koseler[2], kose_BR=koseler[3],
                     hedef="PASS" if (mx2 is not None and mx2 < 1.0) else "FAIL")
            for k, v in o1.items():
                r[f"once_{k}"] = v
            for k, v in o2.items():
                r[f"sonra_{k}"] = v
            satirlar.append(r)
            log(f"  {scene}/{s['id']} {s['device']:<7} kose SOL-UST {koseler[0]} SAG-UST {koseler[1]} "
                f"SOL-ALT {koseler[2]} SAG-ALT {koseler[3]} (medyan {yar}) | maks {mx1} -> {mx2} | {r['hedef']}")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)

    n_ok = sum(1 for r in satirlar if r["hedef"] == "PASS")
    lines = ["## Delik konturu: maskeden -> geometriden", "",
             "| sahne | ekran | cihaz | kose SOL-UST | SAG-UST | SOL-ALT | SAG-ALT | medyan | "
             "once maks | sonra maks | hedef |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        lines.append(f"| {r['sahne']} | {r['ekran']} | {r['cihaz']} | {r['kose_TL']} | {r['kose_TR']} | "
                     f"{r['kose_BL']} | {r['kose_BR']} | {r['yaricap_medyan']} | {r['once_maks']} | "
                     f"{r['sonra_maks']} | {r['hedef']} |")
    mx_once = [r["once_maks"] for r in satirlar if r["once_maks"] is not None]
    mx_sonra = [r["sonra_maks"] for r in satirlar if r["sonra_maks"] is not None]
    lines.append(f"\n**{n_ok}/{len(satirlar)} ekran hedefi tutturdu. En buyuk maks: once "
                 f"{max(mx_once) if mx_once else '-'} px -> sonra {max(mx_sonra) if mx_sonra else '-'} px**")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
