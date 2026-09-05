#!/usr/bin/env python3
"""
QUAD DUZELTMESI: WALLPAPER SINIRI vs GERCEK EKRAN SINIRI - 5 Eyl 2026 (Mo).

Luminans gradyani KULLANILMAZ (cihazin dis hattini yakaliyordu). Bunun yerine
RENK (kroma) kullanilir: ekran icerigi renklidir (Lab a/b), cihazin cercevesi
notrdur. Her kenar icin:
  - yerel dewarp (PAY px), Lab kromasi C = sqrt(a^2 + b^2)
  - icerideki medyan C_ic ile disaridaki C_dis karsilastirilir; fark ESIK'in
    altindaysa o kenar OLCULEMEDI sayilir ve kaydirilmaz
  - esik (C_ic + C_dis)/2'nin gecildigi yer gercek ekran siniri
  - ayrica uretim render'inda |render - master| ile WALLPAPER'IN BITTIGI sinir
    olculur; ikisi arasindaki fark kose kose yazilir
Yeni quad: her kenar dogrusunu olculen kadar kaydirip komsu kenarlarla
kesistirerek kurulur (en fazla SINIR px). calib.json KOPYASINA yazilir.
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
from wp_mockup_common import SCENES, imread, log  # noqa: E402

PAY = 30
UC_PAY = 0.18
ORNEK = 140
ESIK_KROMA = 6.0      # ic/dis kroma farki bunun altindaysa olculemedi
ESIK_FARK = 6.0       # render-master farkinda wallpaper sayilma esigi
SINIR = 30.0          # bir kenari en fazla bu kadar kaydir
KENAR = ["UST", "SAG", "ALT", "SOL"]


def yerel(img, quad, pay):
    q = np.asarray(quad, np.float32)
    W = float((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2)
    H = float((np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2)
    hedef = np.float32([[pay, pay], [pay + W, pay], [pay + W, pay + H], [pay, pay + H]])
    M = cv2.getPerspectiveTransform(q, hedef)
    im = cv2.warpPerspective(img, M, (int(round(W + 2 * pay)), int(round(H + 2 * pay))),
                             flags=cv2.INTER_LINEAR)
    return im, M, W, H


def profiller(alan, W, H, pay, kenar):
    """Kenar boyunca (dis -> ic) profil dizisi verir."""
    ps = []
    if kenar in ("UST", "ALT"):
        xs = np.linspace(pay + UC_PAY * W, pay + (1 - UC_PAY) * W, ORNEK)
        for x in xs:
            xi = int(round(x))
            if not (0 <= xi < alan.shape[1]):
                continue
            if kenar == "UST":
                ps.append(alan[0:int(2 * pay), xi])
            else:
                ps.append(alan[int(pay + H - pay):int(pay + H + pay), xi][::-1])
    else:
        ys = np.linspace(pay + UC_PAY * H, pay + (1 - UC_PAY) * H, ORNEK)
        for y in ys:
            yi = int(round(y))
            if not (0 <= yi < alan.shape[0]):
                continue
            if kenar == "SOL":
                ps.append(alan[yi, 0:int(2 * pay)])
            else:
                ps.append(alan[yi, int(pay + W - pay):int(pay + W + pay)][::-1])
    return [p.astype(np.float32) for p in ps if p.size >= 2 * pay - 2]


def sinir_bul(ps, pay, esik_fark):
    """Her profilde disaridan iceri bakip gecis noktasini bulur.
    Donus: (kaydirma_px, ic_ort, dis_ort, ornek). + = sinir quad'in DISINDA."""
    kayd, icler, disler = [], [], []
    for p in ps:
        ic = float(np.median(p[pay + 8:pay + 20])) if p.size >= pay + 20 else float(np.median(p[pay:]))
        dis = float(np.median(p[0:max(4, pay - 8)]))
        icler.append(ic); disler.append(dis)
        if ic - dis < esik_fark:
            continue
        T = (ic + dis) / 2.0
        i = pay + 18
        while i > 0 and p[i] >= T:
            i -= 1
        kayd.append(pay - i)
    if not kayd:
        return None, float(np.median(icler)) if icler else None, \
            float(np.median(disler)) if disler else None, 0
    return float(np.median(kayd)), float(np.median(icler)), float(np.median(disler)), len(kayd)


def kenar_dogrulari(quad, sap):
    """Her kenari sap[kenar] kadar DISARI oteleyip kesistir -> yeni quad."""
    q = np.asarray(quad, np.float64)
    c = q.mean(axis=0)
    dog = []
    for i, kenar in enumerate(KENAR):
        a, b = q[i], q[(i + 1) % 4]
        d = b - a
        L = float(np.linalg.norm(d)) or 1.0
        n = np.array([-d[1], d[0]]) / L
        if np.dot(n, a - c) < 0:
            n = -n
        s = sap.get(kenar) or 0.0
        s = float(max(-SINIR, min(SINIR, s)))
        dog.append((a + n * s, d))
    out = []
    for i in range(4):
        p0, d0 = dog[(i - 1) % 4]
        p1, d1 = dog[i]
        A = np.array([d0, -d1]).T
        if abs(np.linalg.det(A)) < 1e-9:
            out.append(q[i]); continue
        t = np.linalg.solve(A, p1 - p0)
        out.append(p0 + t[0] * d0)
    return [[float(x), float(y)] for x, y in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--render-dir", required=True, help="uretim ciktilari (wallpaper siniri icin)")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out-calib", required=True, help="duzeltilmis calib.json (KOPYA)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    satirlar = []
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(a.masters) / cfg["master"])
        ad = cfg.get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(scene=scene, pair=a.pair)
        rp = Path(a.render_dir) / ad
        render = imread(rp) if rp.exists() else None
        lab = cv2.cvtColor(master, cv2.COLOR_BGR2Lab).astype(np.float32)
        kroma = np.sqrt((lab[..., 1] - 128) ** 2 + (lab[..., 2] - 128) ** 2)
        fark = (np.abs(render.astype(np.float32) - master.astype(np.float32)).mean(axis=2)
                if render is not None else None)
        log(f"\n=== {scene} ({ad}) ===")
        for s in calib["scenes"][src]["screens"]:
            quad = np.asarray(s["quad"], np.float32)
            k_yerel, _, W, H = yerel(kroma, quad, PAY)
            f_yerel = yerel(fark, quad, PAY)[0] if fark is not None else None
            sap_ekran, sap_wp, r = {}, {}, dict(sahne=scene, ekran=s["id"], cihaz=s["device"])
            for kenar in KENAR:
                se, ic, dis, n = sinir_bul(profiller(k_yerel, W, H, PAY, kenar), PAY, ESIK_KROMA)
                sap_ekran[kenar] = se
                r[f"ekran_{kenar}"] = round(se, 2) if se is not None else None
                r[f"kroma_ic_{kenar}"] = round(ic, 1) if ic is not None else None
                r[f"kroma_dis_{kenar}"] = round(dis, 1) if dis is not None else None
                r[f"ornek_{kenar}"] = n
                if f_yerel is not None:
                    sw, _, _, nw = sinir_bul(profiller(f_yerel, W, H, PAY, kenar), PAY, ESIK_FARK)
                    sap_wp[kenar] = sw
                    r[f"wallpaper_{kenar}"] = round(sw, 2) if sw is not None else None
                    r[f"fark_{kenar}"] = (round(se - sw, 2) if (se is not None and sw is not None) else None)
            yeni = kenar_dogrulari(quad, sap_ekran)
            s["quad_yeni"] = yeni
            kose_sap = [round(math.hypot(yeni[i][0] - float(quad[i][0]), yeni[i][1] - float(quad[i][1])), 2)
                        for i in range(4)]
            r["kose_kaymasi"] = str(kose_sap)
            r["en_buyuk_kose_kaymasi"] = max(kose_sap)
            satirlar.append(r)
            log(f"  {scene}/{s['id']} {s['device']:<7} ekran sapmasi "
                f"UST {r['ekran_UST']} SAG {r['ekran_SAG']} ALT {r['ekran_ALT']} SOL {r['ekran_SOL']} | "
                f"wallpaper siniri UST {r.get('wallpaper_UST')} SAG {r.get('wallpaper_SAG')} "
                f"ALT {r.get('wallpaper_ALT')} SOL {r.get('wallpaper_SOL')} | kose kaymasi {kose_sap}")

    # kopya calib: yalniz olculen sahnelerin quad'lari degisir
    yeni_calib = json.loads((Path(a.calib) / "calib.json").read_text())
    degisen = 0
    for scene in [s.strip() for s in a.scenes.split(",") if s.strip()]:
        src = SCENES[scene].get("calib_from", scene)
        for s0, s1 in zip(calib["scenes"][src]["screens"], yeni_calib["scenes"][src]["screens"]):
            if "quad_yeni" in s0:
                s1["quad"] = s0["quad_yeni"]
                degisen += 1
    Path(a.out_calib).write_text(json.dumps(yeni_calib, indent=1))
    log(f"\n{a.out_calib}: {degisen} ekranin quad'i guncellendi (orijinal dosyaya dokunulmadi)")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    lines = ["## Quad duzeltmesi (kroma ile olculdu)", "",
             "| sahne | ekran | cihaz | ekran UST | SAG | ALT | SOL | wallpaper UST | SAG | ALT | SOL | kose kaymasi |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        lines.append(f"| {r['sahne']} | {r['ekran']} | {r['cihaz']} | {r['ekran_UST']} | {r['ekran_SAG']} | "
                     f"{r['ekran_ALT']} | {r['ekran_SOL']} | {r.get('wallpaper_UST')} | {r.get('wallpaper_SAG')} | "
                     f"{r.get('wallpaper_ALT')} | {r.get('wallpaper_SOL')} | {r['en_buyuk_kose_kaymasi']} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
