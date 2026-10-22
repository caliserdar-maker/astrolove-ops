#!/usr/bin/env python3
"""
MASTER'DAKI GOMULU WALLPAPER DOKUSUNU TEMIZLE - 5 Eyl 2026 (Mo).

Uretim (paste) yolu wallpaper'i yalniz MASKE ∩ QUAD icine yapistirir; disinda
master olduğu gibi kalir. Master AI ile uretilmis bir sahne oldugundan pilot
edisyonun dokusu maskenin disina (cihazin ekran bolgesine) gomulu olabilir.
Bu script her ekran icin maske ∩ quad disinda kalan ama ekran bolgesine ait
INCE SERIDI (BANT px genislik, quad+PAY icinde) cerceve/cevre rengiyle doldurur
(Telea inpaint; ic bolge once notr renge boyanir ki dolgu yalniz DISARIDAN
beslensin, sonra ic bolge geri konur). Temiz master AYRI kopyaya yazilir.

Ayrica olcum: serit L ortalamasi (once/sonra) ve dis halka (cerceve) L'si.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, expand_quad, imread, log, poly_mask_aa  # noqa: E402
import json  # noqa: E402


def serit_maskesi(soft, quad, bant, pay, shape, img=None):
    """serit: paste alani (maske ∩ quad) disinda, bant px icinde ve quad+pay icinde kalan
    pikseller; img verilirse yalniz EKRAN rengine (ic medyan) cerceve rengine (dis halka
    medyani) oldugundan daha yakin olanlar - yani gomulu doku - secilir."""
    hard = (soft >= 0.5).astype(np.uint8)
    q_ic = (poly_mask_aa(shape, quad) >= 0.5).astype(np.uint8)
    gorunen = hard & q_ic                                   # paste'in yapistirdigi alan
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * bant + 1, 2 * bant + 1))
    genis = cv2.dilate(gorunen, k)
    q_dis = (poly_mask_aa(shape, expand_quad(quad, pay)) >= 0.5).astype(np.uint8)
    aday = ((genis | hard) & q_dis) & (1 - gorunen)
    kh = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * (bant + 10) + 1, 2 * (bant + 10) + 1))
    halka = (cv2.dilate(gorunen, kh) & (1 - genis) & (1 - hard))   # dis halka: cerceve/cevre
    if img is None or halka.sum() == 0:
        return aday, gorunen, halka
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32)
    ic_kenar = gorunen & (1 - cv2.erode(gorunen, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))))
    ref_ic = np.median(lab[ic_kenar > 0], axis=0)          # ekranin kenar rengi
    ref_dis = np.median(lab[halka > 0], axis=0)            # cerceve/cevre rengi
    d_ic = np.linalg.norm(lab - ref_ic, axis=2)
    d_dis = np.linalg.norm(lab - ref_dis, axis=2)
    serit = aday & (d_ic < d_dis).astype(np.uint8)
    serit = cv2.dilate(serit, np.ones((3, 3), np.uint8)) & aday
    return serit, gorunen, halka


def L_ort(img, m):
    if m.sum() == 0:
        return None
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    return float(lab[..., 0][m > 0].mean()) * 100.0 / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--scenes", default="SET03,SET04")
    ap.add_argument("--bant", type=int, default=14)
    ap.add_argument("--pay", type=int, default=14)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        temiz = master.copy()
        log(f"\n=== {scene} ({cfg['master']}) bant {a.bant} px ===")
        for s in calib["scenes"][src]["screens"]:
            soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{s['id']}.png"), cv2.IMREAD_GRAYSCALE)
            soft = soft.astype(np.float32) / 255.0
            serit, gorunen, halka = serit_maskesi(soft, np.asarray(s["quad"], np.float32), a.bant, a.pay,
                                                 master.shape, img=master)
            L_once, L_halka = L_ort(master, serit), L_ort(master, halka)
            # ic bolgeyi notr (halka medyani) boya, seridi inpaint et, ic bolgeyi geri koy
            ref = np.median(master[halka > 0].reshape(-1, 3), axis=0) if halka.sum() else np.array([40, 40, 40])
            calis = temiz.copy()
            calis[gorunen > 0] = ref.astype(np.uint8)
            dolgu = cv2.inpaint(calis, (serit * 255).astype(np.uint8), 7, cv2.INPAINT_TELEA)
            temiz[serit > 0] = dolgu[serit > 0]
            L_sonra = L_ort(temiz, serit)
            f = lambda v: "-" if v is None else f"{v:.1f}"
            log(f"  {scene}/{s['id']} {s['device']:<7} ed {s['edition']:<16} serit {int(serit.sum())} px | "
                f"L serit once {f(L_once)} sonra {f(L_sonra)} | L cerceve halkasi {f(L_halka)}")
        cv2.imwrite(str(Path(a.out_dir) / cfg["master"]), temiz, [cv2.IMWRITE_JPEG_QUALITY, 97])
        fark = np.abs(temiz.astype(np.int16) - master.astype(np.int16)).max(axis=2)
        log(f"  yazildi: {Path(a.out_dir) / cfg['master']} | degisen piksel {int((fark > 0).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
