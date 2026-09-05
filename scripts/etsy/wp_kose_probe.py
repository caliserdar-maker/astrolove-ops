#!/usr/bin/env python3
"""
KOSE YARICAPI - TELEFON EKRANLARINDA AYNI HESAP NE VERIYOR - 5 Eyl 2026 (Mo).

Her ekranin 4 kosesinde, quad kosesinden ic kosegen boyunca uc sinir olculur:
  - MASKE   : kalibre yumusak maskenin >=0.5 oldugu ilk nokta (uretim yolu
              wallpaper'i bu maskeyle yapistirir)
  - DELIK   : geometrik delik (hole_shape, cerceve-ustte yolu)
  - FOTOGRAF: sahne fotografinda ekran iceriginin bittigi yer (Lab uzakligi:
              ic medyana mi dis medyana mi yakin)
Kosegen uzakligi t'den yaricap: R = t / (sqrt(2) - 1).
TASMA = FOTOGRAF - MASKE (px, +: maske cihazin kosesini asiyor = wallpaper
kagit dokusu disari tasar). Ayrica _kose_yaricapi'nin alan tabanli tahmini
(saatte 45 yerine 130 veren hesap) her ekran icin yazilir.

--out-calib verilirse: tasmasi ESIK'i asan ekranlara cerceve-ustte +
fotograftan olculen yaricap bayragi yazilir (KOPYA calib).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, hole_shape, imread, log  # noqa: E402

PAY = 40
K = math.sqrt(2.0) - 1.0
ESIK = 2.0
KOSE = ("TL", "TR", "BL", "BR")


def yerel(img, quad, pay):
    q = np.asarray(quad, np.float32)
    W = float((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2)
    H = float((np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2)
    hedef = np.float32([[pay, pay], [pay + W, pay], [pay + W, pay + H], [pay, pay + H]])
    M = cv2.getPerspectiveTransform(q, hedef)
    im = cv2.warpPerspective(img, M, (int(round(W + 2 * pay)), int(round(H + 2 * pay))),
                             flags=cv2.INTER_LINEAR)
    return im, W, H


def kosegen(alan, W, H, pay, kose, t0=-30.0, t1=None, adim=0.5):
    """Kosegen boyunca (dis -> ic) ornekler: t (px), deger."""
    if t1 is None:
        t1 = min(W, H) * 0.45
    cx, cy = {"TL": (pay, pay), "TR": (pay + W, pay), "BL": (pay, pay + H), "BR": (pay + W, pay + H)}[kose]
    dx, dy = {"TL": (1, 1), "TR": (-1, 1), "BL": (1, -1), "BR": (-1, -1)}[kose]
    ts = np.arange(t0, t1, adim)
    xs = cx + dx * ts / math.sqrt(2.0)
    ys = cy + dy * ts / math.sqrt(2.0)
    xs = np.clip(xs, 0, alan.shape[1] - 1.001).astype(np.float32)
    ys = np.clip(ys, 0, alan.shape[0] - 1.001).astype(np.float32)
    d = cv2.remap(alan, xs.reshape(1, -1), ys.reshape(1, -1), cv2.INTER_LINEAR)[0]
    return ts, d


def ilk_gecis(ts, d, esik=0.5):
    i = np.where(d >= esik)[0]
    return float(ts[i[0]]) if i.size else None


def foto_sinir(ts, lab):
    """Lab profili: dis medyan (t<-8) ve ic medyan (t> ic yari) -> hangisine yakin."""
    dis = lab[ts < -8]
    ic = lab[ts > ts.max() * 0.6]
    if len(dis) < 4 or len(ic) < 4:
        return None, 0.0
    md, mi = np.median(dis, axis=0), np.median(ic, axis=0)
    kontrast = float(np.linalg.norm(mi - md))
    if kontrast < 6.0:
        return None, kontrast
    yakin_ic = np.linalg.norm(lab - mi, axis=1) < np.linalg.norm(lab - md, axis=1)
    # dis taraftan gelirken ic'e yakin kalan ILK kararli nokta (3 ornek ust uste)
    for i in range(len(ts) - 3):
        if yakin_ic[i] and yakin_ic[i + 1] and yakin_ic[i + 2]:
            return float(ts[i]), kontrast
    return None, kontrast


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--scenes", default="SET01,SET03,SET04,SET06,SET07,SET10Y")
    ap.add_argument("--out-calib", default="")
    ap.add_argument("--out", default="", help="csv")
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    satirlar = []
    duzeltilen = []
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        lab = cv2.cvtColor(master, cv2.COLOR_BGR2Lab).astype(np.float32)
        log(f"\n=== {scene} ===")
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{s['id']}.png"), cv2.IMREAD_GRAYSCALE)
            soft = soft.astype(np.float32) / 255.0
            d = {}
            delik, _, _ = hole_shape(soft, quad, inset=2.0, detay=d)
            l_lab, W, H = yerel(lab, quad, PAY)
            l_mask = yerel(soft, quad, PAY)[0]
            l_delik = yerel(delik, quad, PAY)[0]
            r = dict(sahne=scene, ekran=s["id"], cihaz=s["device"])
            foto_r = []
            tasma_max = 0.0
            log(f"  {scene}/{s['id']} {s['device']:<7} quad {W:.0f}x{H:.0f} | alan tabanli yaricap (TL,TR,BL,BR) {d['rs']}")
            for k in KOSE:
                ts, dm = kosegen(l_mask, W, H, PAY, k)
                _, dd = kosegen(l_delik, W, H, PAY, k)
                _, dl = kosegen(l_lab, W, H, PAY, k)
                t_m, t_d = ilk_gecis(ts, dm), ilk_gecis(ts, dd)
                t_f, kon = foto_sinir(ts, dl.reshape(len(ts), -1))
                R_m = t_m / K if t_m is not None else None
                R_d = t_d / K if t_d is not None else None
                R_f = t_f / K if t_f is not None else None
                tasma = (t_f - t_m) if (t_f is not None and t_m is not None) else None
                tasma_d = (t_f - t_d) if (t_f is not None and t_d is not None) else None
                r[f"{k}_R_alan"] = d["rs"][KOSE.index(k)]
                r[f"{k}_R_maske"] = None if R_m is None else round(R_m, 1)
                r[f"{k}_R_delik"] = None if R_d is None else round(R_d, 1)
                r[f"{k}_R_foto"] = None if R_f is None else round(R_f, 1)
                r[f"{k}_tasma_maske"] = None if tasma is None else round(tasma, 1)
                r[f"{k}_tasma_delik"] = None if tasma_d is None else round(tasma_d, 1)
                r[f"{k}_kontrast"] = round(kon, 1)
                foto_r.append(R_f)
                if tasma is not None:
                    tasma_max = max(tasma_max, tasma)
                fmt = lambda v: "-" if v is None else f"{v:.1f}"
                log(f"     {k}: kosegen t maske {fmt(t_m)} delik {fmt(t_d)} foto {fmt(t_f)} px | "
                    f"R maske {fmt(R_m)} delik {fmt(R_d)} foto {fmt(R_f)} | "
                    f"TASMA maske {fmt(tasma)} delik {fmt(tasma_d)} px (kontrast {kon:.0f})")
            r["tasma_max"] = round(tasma_max, 1)
            satirlar.append(r)
            if a.out_calib and s["device"] != "Watch" and tasma_max > ESIK and all(x is not None for x in foto_r):
                s["frame_top"] = {"disari": 4, "delik": "sekil", "delik_px": 0,
                                  "yaricap": [round(x, 1) for x in foto_r]}
                duzeltilen.append(f"{scene}/{s['id']}")
                log(f"     -> DUZELTME: cerceve-ustte, yaricap fotograftan {[round(x, 1) for x in foto_r]}")
    if a.out_calib:
        Path(a.out_calib).write_text(json.dumps(calib, indent=1))
        log(f"\n{a.out_calib}: {len(duzeltilen)} ekrana kose duzeltmesi yazildi: {duzeltilen}")
    if a.out:
        import csv
        cols = list(dict.fromkeys(k for r in satirlar for k in r))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(satirlar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
