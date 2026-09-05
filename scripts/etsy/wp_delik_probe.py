#!/usr/bin/env python3
"""
DELIK NEDEN QUAD'DAN KUCUK - 5 Eyl 2026 (Mo).

Tek ekran icin uc boyut olculur: quad, cizilen delik (>=0.5 bolgesi),
render'da wallpaper'in gorunen kutusu. Sonra delik zincirinin her adimi
(erode/inset, kose yuvarlatma, ic delik cikarma) tek tek acilip kapatilarak
her birinin kenar basina kac px kucuttugu yazilir. Olcum yapar, uretmez.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import SCENES, hole_shape, imread, log  # noqa: E402

ESIK_FARK = 8.0


def kenarlar(sekil):
    """Yerel sekilde >=0.5 bolgesinin cerceve kenarlarina uzakligi (px):
    orta hat ve ceyrek hatlarda UST/ALT/SOL/SAG."""
    H, W = sekil.shape[:2]
    m = sekil >= 0.5
    if not m.any():
        return None
    out = {}
    for ad, c in (("orta", W // 2), ("c1", W // 4), ("c3", 3 * W // 4)):
        s = np.where(m[:, c])[0]
        out[f"UST@{ad}"] = int(s[0]) if s.size else None
        out[f"ALT@{ad}"] = int(H - 1 - s[-1]) if s.size else None
    for ad, r in (("orta", H // 2), ("c1", H // 4), ("c3", 3 * H // 4)):
        s = np.where(m[r, :])[0]
        out[f"SOL@{ad}"] = int(s[0]) if s.size else None
        out[f"SAG@{ad}"] = int(W - 1 - s[-1]) if s.size else None
    ys, xs = np.where(m)
    out["kutu"] = (int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
    out["alan_yuzde"] = round(100.0 * m.sum() / (W * H), 1)
    return out


def yaz(ad, k):
    if k is None:
        log(f"  {ad:34s} bos")
        return
    log(f"  {ad:34s} kutu {k['kutu'][0]}x{k['kutu'][1]} alan %{k['alan_yuzde']:5.1f} | "
        f"orta hat UST {k['UST@orta']} ALT {k['ALT@orta']} SOL {k['SOL@orta']} SAG {k['SAG@orta']} | "
        f"ceyrekte UST {k['UST@c1']}/{k['UST@c3']} ALT {k['ALT@c1']}/{k['ALT@c3']} "
        f"SOL {k['SOL@c1']}/{k['SOL@c3']} SAG {k['SAG@c1']}/{k['SAG@c3']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True, help="calib klasoru (calib.json + masks)")
    ap.add_argument("--masters", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--screen", type=int, required=True)
    ap.add_argument("--render", default="", help="gorunen kutu icin render")
    ap.add_argument("--inset", type=float, default=2.0)
    a = ap.parse_args()

    cfg = SCENES[a.scene]
    src = cfg.get("calib_from", a.scene)
    master = imread(Path(a.masters) / cfg["master"])
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    s = next(x for x in calib["scenes"][src]["screens"] if int(x["id"]) == a.screen)
    quad = np.asarray(s["quad"], np.float32)
    soft = cv2.imread(str(Path(a.calib) / "masks" / f"{src}_{a.screen}.png"), cv2.IMREAD_GRAYSCALE)
    soft = soft.astype(np.float32) / 255.0
    W = float((np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2)
    H = float((np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2)
    log(f"=== {a.scene}/{a.screen} {s['device']} ===")
    log(f"quad: {[[round(float(x), 1), round(float(y), 1)] for x, y in quad]} -> {W:.1f} x {H:.1f} px")

    # maske yeni quad'in yerel cercevesinde nerede?
    d = {}
    hole_shape(soft, quad, inset=a.inset, detay=d)
    yerel = d["yerel"]
    log(f"\n--- kalibre maske, quad'in yerel cercevesinde ({d['W']}x{d['H']}) ---")
    yaz("maske >=0.5", kenarlar(yerel))
    log(f"  olculen kose yaricaplari (TL,TR,BL,BR): {d['rs']} px  | cizim siniri {min(d['W'], d['H']) // 2 - int(a.inset)} px")

    log(f"\n--- delik zinciri (yerel cerceve, >=0.5) ---")
    varyant = [
        ("E) delik = quad (hicbir kucultme yok)", dict(inset=0.0, yuvarlat=False, ic_cikar=False)),
        (f"B) yalniz inset {a.inset:g} px", dict(inset=a.inset, yuvarlat=False, ic_cikar=False)),
        ("C) yalniz kose yuvarlatma", dict(inset=0.0, yuvarlat=True, ic_cikar=False)),
        ("D) yalniz ic delik cikarma", dict(inset=0.0, yuvarlat=False, ic_cikar=True)),
        (f"A) MEVCUT: inset {a.inset:g} + yuvarlatma + ic", dict(inset=a.inset, yuvarlat=True, ic_cikar=True)),
    ]
    for ad, kw in varyant:
        dd = {}
        hole_shape(soft, quad, detay=dd, **kw)
        yaz(ad, kenarlar(dd["sekil"]))
        if kw.get("ic_cikar") and dd.get("ic_alan"):
            log(f"      ic delik olarak cikarilan alan: {dd['ic_alan']} px")

    if a.render:
        r = imread(Path(a.render))
        x0, y0 = np.floor(quad.min(axis=0) - 90).astype(int)
        x1, y1 = np.ceil(quad.max(axis=0) + 90).astype(int)
        f = np.abs(r[y0:y1, x0:x1].astype(np.float32) - master[y0:y1, x0:x1].astype(np.float32)).mean(axis=2)
        m = (f > ESIK_FARK).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cnts, key=cv2.contourArea)
        xs, ys, w, h = cv2.boundingRect(c)
        kutu = np.array([xs + x0, ys + y0, xs + x0 + w, ys + y0 + h], float)
        qb = np.array([quad[:, 0].min(), quad[:, 1].min(), quad[:, 0].max(), quad[:, 1].max()])
        log(f"\n--- render'da gorunen kutu (|render-master|>{ESIK_FARK:g}) ---")
        log(f"  kutu {w}x{h} @ ({kutu[0]:.0f},{kutu[1]:.0f}) | quad kutusu {qb[2] - qb[0]:.0f}x{qb[3] - qb[1]:.0f}")
        log(f"  quad kenarindan iceride: SOL {kutu[0] - qb[0]:.0f} UST {kutu[1] - qb[1]:.0f} "
            f"SAG {qb[2] - kutu[2]:.0f} ALT {qb[3] - kutu[3]:.0f} px")
        log("  NOT: bu olcum koyu-ustune-koyu kenarlarda gorunen alani KUCUK gosterebilir; delik olcumu kesindir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
