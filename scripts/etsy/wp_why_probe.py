#!/usr/bin/env python3
"""
NEDEN DEGISMEDI: uc render'in ayni bolgede karsilastirmasi (SALT OKUM) - 5 Eyl 2026.

1) sha256 ve boyut: uretimdeki MOCKUP_V2 dosyasi ile yeni ciktilar ayni mi.
2) Fark haritasi: |yeni - eski| > 2 olan piksellerin sayisi, sinir kutusu ve
   bu piksellerin ekran quad'inin kenarina uzakligi (yani degisim nerede).
3) Delik ile kalibre maske arasindaki iliski: geometrik delik maskenin 0.5
   sinirinin DISINA kac px cikiyor / ICINDE kac px kaliyor. Delik quad'dan
   turedigi icin, quad gercek ekrandan buyukse delik cerceveye tasar; bu
   sayilar bunu gosterir.
Uretim yok, duzeltme yok.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, erode_soft_mask, hole_shape, imread, log  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--dirs", required=True, help="etiket=klasor,... (ilki referans)")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--inset", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    dirs = [(t.split("=")[0], t.split("=")[1]) for t in a.dirs.split(",") if t]
    satirlar = []
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        ad = SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(
            scene=scene, pair=a.pair)
        yollar = [(et, Path(d) / ad) for et, d in dirs if (Path(d) / ad).exists()]
        if len(yollar) < 2:
            log(f"{scene}: yeterli dosya yok"); continue
        log(f"\n=== {scene} ===")
        imgs = {}
        for et, p in yollar:
            imgs[et] = imread(p)
            log(f"  {et:<12} {p.name}  {p.stat().st_size:>9} B  sha256 {sha(p)[:16]}")
        ref_et = yollar[0][0]
        src = SCENES[scene].get("calib_from", scene)
        for et, _ in yollar[1:]:
            D = np.abs(imgs[et].astype(np.float32) - imgs[ref_et].astype(np.float32)).mean(axis=2)
            deg = D > 2.0
            r = dict(sahne=scene, karsilastirma=f"{ref_et} -> {et}",
                     ayni_dosya="EVET" if not deg.any() else "HAYIR",
                     degisen_px=int(deg.sum()), maks_fark=round(float(D.max()), 1))
            if deg.any():
                ys, xs = np.nonzero(deg)
                r["kutu"] = f"({xs.min()},{ys.min()})-({xs.max()},{ys.max()})"
            satirlar.append(r)
            log(f"  {ref_et} -> {et}: degisen {r['degisen_px']} px, maks fark {r['maks_fark']}, "
                f"kutu {r.get('kutu', '-')}")
        # delik / maske iliskisi
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{s['id']}.png"), cv2.IMREAD_GRAYSCALE)
            if soft is None:
                continue
            soft = soft.astype(np.float32) / 255.0
            maske = (soft >= 0.5).astype(np.uint8)
            delik = (hole_shape(soft, quad, inset=a.inset)[0] >= 0.5).astype(np.uint8)
            eski = (erode_soft_mask(soft, int(round(a.inset))) >= 0.5).astype(np.uint8)
            dis = (delik > 0) & (maske == 0)
            dist_dis = cv2.distanceTransform(1 - maske, cv2.DIST_L2, 5)
            ic = (maske > 0) & (delik == 0)
            rr = dict(sahne=scene, ekran=s["id"], cihaz=s["device"],
                      maske_px=int(maske.sum()), delik_px=int(delik.sum()),
                      eski_delik_px=int(eski.sum()),
                      delik_maske_disinda_px=int(dis.sum()),
                      delik_maske_disinda_maks_px=round(float(dist_dis[dis].max()), 1) if dis.any() else 0.0,
                      maske_delik_disinda_px=int(ic.sum()))
            satirlar.append(rr)
            log(f"  {scene}/{s['id']} {s['device']:<7} maske {rr['maske_px']} px | delik {rr['delik_px']} px "
                f"(eski {rr['eski_delik_px']}) | delik maskenin DISINDA {rr['delik_maske_disinda_px']} px "
                f"(en fazla {rr['delik_maske_disinda_maks_px']} px) | maske delik disinda "
                f"{rr['maske_delik_disinda_px']} px")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("## Neden degismedi - olcum\n\n```\n" + "\n".join(str(r) for r in satirlar) + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
