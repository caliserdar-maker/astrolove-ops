#!/usr/bin/env python3
"""
SET06 ekran-2 (id=1, Desktop) ve SET10Y ekran-1 (id=0, Phone) icin dogrulama
esigi altinda kalan kalibrasyonu (dusuk inlier/yuksek RMS ya da beklenen
cihaz oranindan sapan dortgen) ELLE DUZELTIR.

SET10Y ekran-1: "ideal dikdortgene" regularize edilir (merkez + genislik
yonu/uzunlugu korunur, dik acili hale getirilir, yukseklik hedef orana gore
yeniden hesaplanir) - bu yontem render'in kendi SIFT dogrulamasindan da
(inlier>=20) GECTI (onceki test, Mo onayi).

SET06 ekran-2: "ideal dikdortgene zorlama" yontemi render'in kendi SIFT
dogrulamasinda FAIL verdi (16/20 inlier) - fotografdaki GERCEK perspektif
(keystone) atilinca dortgen ~35-40px kayiyor. Bunun yerine KISITLI duzeltme:
H'nin DOGRUSAL kismi A=[[a,b],[c,d]] iki sutuna ayrilir - sutun-1 (a,c) =
YATAY (genislik) yonu/olcegi, sutun-2 (b,d) = DIKEY (yukseklik) yonu/olcegi.
codebase'in kendi "scale" alani zaten sutun-1'in normu (bkz. quad_scale()).
SADECE sutun-2'nin BUYUKLUGU (olcegi) sutun-1'e esitlenecek sekilde
olceklenir - YONU (dolayisiyla kesme/donme) DEGISMEZ; sutun-1, kesme/donme
terimleri (b,c) ve perspektif satiri (e,f) HIC DOKUNULMEZ. W0/H0 (wallpaper
kendi orani) = hedef oran oldugundan (Desktop 3840/2160=1.778), sutun
normlarini esitlemek c4 oranini tam hedefe getirir; gercek kamera
perspektifi (kesme + perspektif satiri) korunur.

Her iki ekran icin de: yeni H ile warp(pilot) yeniden hesaplanir, maske
(screen_soft_mask) YENI H/warp ile TUTARLI olacak sekilde yeniden uretilir
(eski maske yeni geometriyle uyumsuz kalmasin diye - paste modu bunu ister).

SADECE bu 2 ekran icin calisir; calib.json'un geri kalanina dokunmaz. Girdi
calib.json'u DEGISTIRMEZ - duzeltilmis kopyayi --out'a yazar (onay bekleyen
TEST script'idir).
"""
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, dump_json, imread, ink_mask, quad_of, quad_scale, screen_soft_mask, warp_full

TARGETS = [("SET06", 1, "Desktop"), ("SET10Y", 0, "Phone")]
METHOD = {"SET06": "scale_only", "SET10Y": "regularize"}


def aspect_of_quad(quad):
    q = np.asarray(quad, np.float32)
    top = np.linalg.norm(q[1] - q[0]); bottom = np.linalg.norm(q[2] - q[3])
    left = np.linalg.norm(q[3] - q[0]); right = np.linalg.norm(q[2] - q[1])
    w = (top + bottom) / 2; h = (left + right) / 2
    return w / h if h else 0.0


def scale_only_fix(H, W0, target_aspect):
    """H'nin dogrusal kismini sutunlarina ayirir: sutun-1 (a,c)=yatay yon/olcek
    (codebase'in "scale" alaniyla ayni - quad_scale()), sutun-2 (b,d)=dikey
    yon/olcek. Her iki sutunun YONU (dolayisiyla kesme/donme) DEGISMEZ;
    perspektif satiri (H[2]) HIC DOKUNULMEZ. Sutunlarin BUYUKLUGU, GEOMETRIK
    ORTALARINA esitlenecek sekilde simetrik olceklenir (tek sutunu digerine
    zorlamak - ilk denemede - dortgeni gereksiz yere fazla kaydirdi, 83px;
    simetrik dagitim toplam kaymayi kucultur). W0/H0=target_aspect oldugundan
    (wallpaper kendi orani) bu, dortgen oranini tam target_aspect'e getirir."""
    H = np.asarray(H, np.float64).copy()
    a, b = H[0, 0], H[0, 1]
    c, d = H[1, 0], H[1, 1]
    scale_x = float(np.hypot(a, c))
    scale_y = float(np.hypot(b, d))
    geo = math.sqrt(scale_x * scale_y)
    H[0, 0] = a * (geo / scale_x); H[1, 0] = c * (geo / scale_x)
    H[0, 1] = b * (geo / scale_y); H[1, 1] = d * (geo / scale_y)
    return H


def regularize(quad, target_aspect):
    """Merkez + genislik yonu/uzunlugu korunur; dik acili, hedef oranli yeni dortgen."""
    q = np.asarray(quad, np.float32)
    center = q.mean(axis=0)
    width_vec = ((q[1] - q[0]) + (q[2] - q[3])) / 2.0
    width = float(np.linalg.norm(width_vec))
    unit_w = width_vec / width
    unit_h = np.float32([-unit_w[1], unit_w[0]])  # 90 derece dik
    height = width / target_aspect
    hw, hh = unit_w * width / 2, unit_h * height / 2
    return np.float32([center - hw - hh, center + hw - hh, center + hw + hh, center - hw + hh])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True, help="orijinal kalibrasyon klasoru (calib.json)")
    ap.add_argument("--masters", required=True, help="pilot *_FINAL.jpg klasoru")
    ap.add_argument("--pilot", required=True, help="pilot FINAL_V2 wallpaper klasoru")
    ap.add_argument("--out", required=True, help="duzeltilmis calib.json + masks buraya yazilir")
    a = ap.parse_args()
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out, "masks").mkdir(parents=True, exist_ok=True)

    rows = ["| Sahne | # | Cihaz | Eski oran | Yeni oran | Hedef | Eski dortgen | Yeni dortgen |",
            "|---|---|---|---|---|---|---|---|"]
    for scene, sid, dev in TARGETS:
        s = next(x for x in calib["scenes"][scene]["screens"] if x["id"] == sid)
        target_aspect = DEVICES[dev][0] / DEVICES[dev][1]
        old_quad = np.asarray(s["quad"], np.float32)
        old_aspect = aspect_of_quad(old_quad)
        W0, H0 = DEVICES[dev]

        if METHOD[scene] == "scale_only":
            new_H = scale_only_fix(s["H"], W0, target_aspect)
            new_quad = quad_of(new_H, W0, H0)
        else:
            new_quad = regularize(old_quad, target_aspect)
            src_pts = np.float32([[0, 0], [W0, 0], [W0, H0], [0, H0]])
            new_H = cv2.getPerspectiveTransform(src_pts, new_quad)
        new_aspect = aspect_of_quad(new_quad)
        new_scale = quad_scale(new_quad, W0)

        master = imread(Path(a.masters) / calib["scenes"][scene]["master"])
        wp_pilot = imread(Path(a.pilot) / f"AstroLove_{calib['pilot_pair']}_{s['edition']}_{dev}.jpg")
        warped_pilot = warp_full(wp_pilot, new_H, master.shape, new_scale)
        ink_w = cv2.warpPerspective(ink_mask(wp_pilot), np.asarray(new_H, np.float64),
                                    (master.shape[1], master.shape[0]), flags=cv2.INTER_NEAREST)
        soft, quality, holes = screen_soft_mask(master, warped_pilot, new_quad, ink_w)
        cv2.imwrite(str(Path(a.out, "masks") / f"{scene}_{sid}.png"), (soft * 255).astype(np.uint8))

        s["quad"] = new_quad.tolist(); s["H"] = new_H.tolist(); s["scale"] = float(new_scale)
        s["calib_fix"] = dict(old_aspect=old_aspect, new_aspect=new_aspect, target_aspect=target_aspect,
                              mask_quality=quality)
        rows.append(f"| {scene} | {sid} | {dev} | {old_aspect:.3f} | {new_aspect:.3f} | {target_aspect:.3f} | "
                    f"{np.round(old_quad).astype(int).tolist()} | {np.round(new_quad).astype(int).tolist()} |")
        print(f"{scene}/{sid} ({dev}): oran {old_aspect:.3f} -> {new_aspect:.3f} (hedef {target_aspect:.3f}) "
              f"maske kalitesi {quality:.3f}", flush=True)

    dump_json(calib, Path(a.out) / "calib.json")
    (Path(a.out) / "report.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
