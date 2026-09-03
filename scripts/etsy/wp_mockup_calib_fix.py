#!/usr/bin/env python3
"""
SET06 ekran-2 (id=1, Desktop) ve SET10Y ekran-1 (id=0, Phone) icin dogrulama
esigi altinda kalan kalibrasyonu (dusuk inlier/yuksek RMS ya da beklenen
cihaz oranindan sapan dortgen) ELLE DUZELTIR:

  - dortgenin MERKEZI ve GENISLIK yonu/uzunlugu (ust+alt kenar ortalamasi -
    en genis/en cok SIFT eslesmesi alan boyut) korunur;
  - dik acili GERCEK bir dikdortgene regularize edilir (olculen kesme/carpiklik
    atilir - fiziksel ekran zaten dikdortgen);
  - YUKSEKLIK, hedef cihaz oranina gore yeniden hesaplanir (Desktop 3840/2160
    =1.778, Phone 1440/3200=0.45 - DEVICES sozlugunden, wp_audit_drive.py'nin
    c4 kontrolundeki AYNI kaynak);
  - yeni H = getPerspectiveTransform(wallpaper koseleri -> duzeltilmis dortgen);
  - maske (screen_soft_mask) YENI H/warp ile TUTARLI olacak sekilde yeniden
    uretilir (eski maske yeni geometriyle uyumsuz kalmasin diye - paste modu
    bunu ister).

SADECE bu 2 ekran icin calisir; calib.json'un geri kalanina dokunmaz. Girdi
calib.json'u DEGISTIRMEZ - duzeltilmis kopyayi --out'a yazar (onay bekleyen
TEST script'idir).
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, dump_json, imread, ink_mask, quad_scale, screen_soft_mask, warp_full

TARGETS = [("SET06", 1, "Desktop"), ("SET10Y", 0, "Phone")]


def aspect_of_quad(quad):
    q = np.asarray(quad, np.float32)
    top = np.linalg.norm(q[1] - q[0]); bottom = np.linalg.norm(q[2] - q[3])
    left = np.linalg.norm(q[3] - q[0]); right = np.linalg.norm(q[2] - q[1])
    w = (top + bottom) / 2; h = (left + right) / 2
    return w / h if h else 0.0


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
        new_quad = regularize(old_quad, target_aspect)
        new_aspect = aspect_of_quad(new_quad)

        W0, H0 = DEVICES[dev]
        src_pts = np.float32([[0, 0], [W0, 0], [W0, H0], [0, H0]])
        new_H = cv2.getPerspectiveTransform(src_pts, new_quad)
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
