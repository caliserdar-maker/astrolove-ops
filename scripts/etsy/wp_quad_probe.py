#!/usr/bin/env python3
"""
QUAD KONUMU: KALIBRASYON DOGRU MU (SALT OLCUM) - 5 Eyl 2026.

Gercek ekran siniri sahne FOTOGRAFINDAN bulunur (maskeden DEGIL):
  - ekranin yerel dikdortgenine pay (PAY px) ile dewarp edilir,
  - her kenar icin dik yonde luminans profilinin turevi alinir; en guclu
    gecis noktasi o kenarin gercek yeri sayilir (kenar boyunca ortanca),
  - kenar sapmasi = gercek kenar - calib quad kenari (px).
      + deger: gercek ekran quad'in DISINDA (quad kucuk)
      - deger: gercek ekran quad'in ICINDE (quad buyuk, cerceveye tasar)
  - dort kenarin kaydirilmis dogrulari kesistirilerek olculen koseler ve
    her kose icin sapma (dx, dy, buyukluk, yon) yazilir.
  - gecisin kuvveti (kontrast) de yazilir; dusukse olcum guvenilmez.
calib.json'a DOKUNULMAZ. Kanit: quad (kirmizi) + olculen sinir (yesil) cizili
kose kirpmalari.
"""
import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, imread, imwrite_jpeg, log  # noqa: E402

PAY = 40          # yerel dewarp payi (px)
UC_PAY = 0.15     # kenar uclarindan atilan oran (kose yuvarlamasi disarida)
ORNEK = 160       # kenar boyunca ornek sayisi
PENCERE = 300     # kanit kose penceresi
KENAR = ["UST", "SAG", "ALT", "SOL"]


def yerel_donusum(quad, pay):
    q = np.asarray(quad, np.float32)
    W = float((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2)
    H = float((np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2)
    Wp, Hp = int(round(W + 2 * pay)), int(round(H + 2 * pay))
    hedef = np.float32([[pay, pay], [pay + W, pay], [pay + W, pay + H], [pay, pay + H]])
    M = cv2.getPerspectiveTransform(q, hedef)
    return M, Wp, Hp, W, H


def kenar_sapmasi(g, W, H, pay):
    """Her kenar icin (sapma_px, kontrast, ornek_sayisi)."""
    out = {}
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    for kenar in KENAR:
        sapmalar, kontrastlar = [], []
        if kenar in ("UST", "ALT"):
            y0 = pay if kenar == "UST" else pay + H
            xs = np.linspace(pay + UC_PAY * W, pay + (1 - UC_PAY) * W, ORNEK)
            for x in xs:
                xi = int(round(x))
                if not (0 <= xi < g.shape[1]):
                    continue
                a, b = int(max(0, y0 - pay)), int(min(g.shape[0], y0 + pay))
                prof = g[a:b, xi].astype(np.float32)
                if prof.size < 8:
                    continue
                d = np.abs(np.gradient(prof))
                i = int(np.argmax(d))
                sapmalar.append((a + i) - y0 if kenar == "UST" else y0 - (a + i))
                kontrastlar.append(float(d[i]))
        else:
            x0 = pay if kenar == "SOL" else pay + W
            ys = np.linspace(pay + UC_PAY * H, pay + (1 - UC_PAY) * H, ORNEK)
            for y in ys:
                yi = int(round(y))
                if not (0 <= yi < g.shape[0]):
                    continue
                a, b = int(max(0, x0 - pay)), int(min(g.shape[1], x0 + pay))
                prof = g[yi, a:b].astype(np.float32)
                if prof.size < 8:
                    continue
                d = np.abs(np.gradient(prof))
                i = int(np.argmax(d))
                sapmalar.append((a + i) - x0 if kenar == "SOL" else x0 - (a + i))
                kontrastlar.append(float(d[i]))
        if not sapmalar:
            out[kenar] = (None, None, 0)
            continue
        s = np.asarray(sapmalar, np.float32)
        med = float(np.median(s))
        # UST/SOL icin + deger quad'in DISI demek; ALT/SAG icin de ayni isaret
        out[kenar] = (round(-med if kenar in ("UST", "SOL") else -med, 2),
                      round(float(np.median(kontrastlar)), 2), int(len(s)))
    return out


def kose_sapmalari(sap, W, H, pay):
    """Kaydirilmis kenar dogrularinin kesisimi -> olculen koseler (yerel px)."""
    d = {k: (sap[k][0] if sap[k][0] is not None else 0.0) for k in KENAR}
    ust = pay - d["UST"]
    alt = pay + H + d["ALT"]
    sol = pay - d["SOL"]
    sag = pay + W + d["SAG"]
    olculen = {"SOL UST": (sol, ust), "SAG UST": (sag, ust),
               "SAG ALT": (sag, alt), "SOL ALT": (sol, alt)}
    quadk = {"SOL UST": (pay, pay), "SAG UST": (pay + W, pay),
             "SAG ALT": (pay + W, pay + H), "SOL ALT": (pay, pay + H)}
    out = {}
    for k in olculen:
        dx = olculen[k][0] - quadk[k][0]
        dy = olculen[k][1] - quadk[k][1]
        yon = []
        if abs(dx) >= 0.5:
            yon.append("sola" if dx < 0 else "saga")
        if abs(dy) >= 0.5:
            yon.append("yukari" if dy < 0 else "asagi")
        out[k] = (round(dx, 2), round(dy, 2), round(math.hypot(dx, dy), 2),
                  "+".join(yon) or "yerinde")
    return out, olculen, quadk


def kanit(master, quad, sap, W, H, pay, Minv, yol, baslik):
    im = master.copy()
    q = np.round(np.asarray(quad, np.float32)).astype(np.int32)
    cv2.polylines(im, [q], True, (0, 0, 255), 2, cv2.LINE_AA)          # calib quad: kirmizi
    _, olculen, _ = kose_sapmalari(sap, W, H, pay)
    pts = np.float32([olculen["SOL UST"], olculen["SAG UST"],
                      olculen["SAG ALT"], olculen["SOL ALT"]]).reshape(-1, 1, 2)
    sahne = cv2.perspectiveTransform(pts, Minv).reshape(-1, 2)
    cv2.polylines(im, [np.round(sahne).astype(np.int32)], True, (0, 255, 0), 2, cv2.LINE_AA)
    hucre = []
    for i, ad in enumerate(["SOL UST", "SAG UST", "SAG ALT", "SOL ALT"]):
        c = np.asarray(quad, np.float32)[i]
        w = PENCERE
        x = max(0, min(im.shape[1] - w, int(round(c[0] - w / 2))))
        y = max(0, min(im.shape[0] - w, int(round(c[1] - w / 2))))
        p = im[y:y + w, x:x + w].copy()
        cv2.putText(p, ad, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(p, ad, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        hucre.append(p)
    ust = np.hstack([hucre[0], np.full((PENCERE, 8, 3), 255, np.uint8), hucre[1]])
    alt = np.hstack([hucre[3], np.full((PENCERE, 8, 3), 255, np.uint8), hucre[2]])
    panel = np.vstack([ust, np.full((8, ust.shape[1], 3), 255, np.uint8), alt])
    cv2.putText(panel, baslik + "  (kirmizi=calib quad, yesil=olculen ekran siniri)",
                (10, panel.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(panel, baslik + "  (kirmizi=calib quad, yesil=olculen ekran siniri)",
                (10, panel.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    imwrite_jpeg(yol, panel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--kanit", default="SET07:1,SET03:0")
    ap.add_argument("--tam", default="", help="tam sahne cizimi uretilecek sahneler (virgul)")
    ap.add_argument("--kalinlik", type=int, default=6)
    ap.add_argument("--crop-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    kanitlar = {(t.split(":")[0], int(t.split(":")[1])) for t in a.kanit.split(",") if t}
    tam_sahneler = {t.strip() for t in a.tam.split(",") if t.strip()}
    tam_ciz = {}
    Path(a.crop_dir).mkdir(parents=True, exist_ok=True)
    satirlar = []
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            M, Wp, Hp, W, H = yerel_donusum(quad, PAY)
            yerel = cv2.warpPerspective(master, M, (Wp, Hp), flags=cv2.INTER_LINEAR)
            g = cv2.cvtColor(yerel, cv2.COLOR_BGR2GRAY).astype(np.float32)
            sap = kenar_sapmasi(g, W, H, PAY)
            koseler, _, _ = kose_sapmalari(sap, W, H, PAY)
            r = dict(sahne=scene, ekran=s["id"], cihaz=s["device"],
                     quad_px=f"{W:.1f}x{H:.1f}")
            for k in KENAR:
                r[f"kenar_{k}"] = sap[k][0]
                r[f"kontrast_{k}"] = sap[k][1]
            for k, v in koseler.items():
                kk = k.replace(" ", "_")
                r[f"{kk}_dx"], r[f"{kk}_dy"] = v[0], v[1]
                r[f"{kk}_sapma"], r[f"{kk}_yon"] = v[2], v[3]
            buyuk = max(v[2] for v in koseler.values())
            r["en_buyuk_kose_sapmasi"] = buyuk
            satirlar.append(r)
            log(f"  {scene}/{s['id']} {s['device']:<7} kenar UST {sap['UST'][0]} SAG {sap['SAG'][0]} "
                f"ALT {sap['ALT'][0]} SOL {sap['SOL'][0]} px | en buyuk kose sapmasi {buyuk} px "
                f"| kontrast {[sap[k][1] for k in KENAR]}")
            if scene in tam_sahneler:
                tam_ciz.setdefault(scene, master.copy())
                im = tam_ciz[scene]
                q = np.round(quad).astype(np.int32)
                cv2.polylines(im, [q], True, (0, 0, 255), a.kalinlik, cv2.LINE_AA)
                _, olculen, _ = kose_sapmalari(sap, W, H, PAY)
                pts = np.float32([olculen["SOL UST"], olculen["SAG UST"],
                                  olculen["SAG ALT"], olculen["SOL ALT"]]).reshape(-1, 1, 2)
                sahne_pts = cv2.perspectiveTransform(pts, np.linalg.inv(M.astype(np.float64))).reshape(-1, 2)
                cv2.polylines(im, [np.round(sahne_pts).astype(np.int32)], True, (0, 255, 0),
                              a.kalinlik, cv2.LINE_AA)
            if (scene, s["id"]) in kanitlar:
                kanit(master, quad, sap, W, H, PAY, np.linalg.inv(M.astype(np.float64)),
                      Path(a.crop_dir) / f"M13_{scene}_S{s['id']}_QUAD_vs_EKRAN.jpg",
                      f"{scene} ekran {s['id']} ({s['device']})")

    for scene, im in tam_ciz.items():
        p = Path(a.crop_dir) / f"M14_{scene}_QUAD_TAM.jpg"
        imwrite_jpeg(p, im)
        log(f"  {p.name}: tam sahne {im.shape[1]}x{im.shape[0]}")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)

    lines = ["## Quad vs gercek ekran siniri (sahne fotografindan olculdu)", "",
             "| sahne | ekran | cihaz | UST | SAG | ALT | SOL | en buyuk kose sapmasi |",
             "|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        lines.append(f"| {r['sahne']} | {r['ekran']} | {r['cihaz']} | {r['kenar_UST']} | "
                     f"{r['kenar_SAG']} | {r['kenar_ALT']} | {r['kenar_SOL']} | "
                     f"{r['en_buyuk_kose_sapmasi']} |")
    lines.append("\n(+ = gercek ekran quad'in DISINDA / quad kucuk; - = quad gercek ekrandan BUYUK)")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
