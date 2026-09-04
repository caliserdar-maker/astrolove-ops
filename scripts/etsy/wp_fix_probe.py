#!/usr/bin/env python3
"""
IKI DUZELTME DENEMESI - OLCUM VE KANIT - 4 Eyl 2026 (Mo gorevi).

A) SAAT: glow yalniz buyuk cihazlarda uygulanacak sekilde (wp_build_pair
   GLOW_DEVICES) MB/DB Watch dosyalari yeniden uretildi ve SET07 bu dosyalarla,
   LANCZOS4 kucultme ile, relight KAPALI render edildi. Burada olculen:
   mevcut render / yeni render (ikisi de saat quad'indan kaynak izgarasina
   dondurulur) / eski kaynak / yeni kaynak / plaka - ayni hale olcutuyle.
   Panel (tam cozunurluk, 1:1): mevcut | yeni | plaka.

B) TASMA: ekran maskesi 2 px erode edilir (0.5 seviyesi iceri alinir, ayni
   0.8 yumusaklik korunur) ve ayni ekran mevcut/yeni maske ile yerlestirilir.
   Tasma HER IKI durumda da AYNI referans sinira (orijinal maskenin 0.5
   konturu) gore olculur; boylece once/sonra karsilastirilabilir.
   Panel: her kenar icin mevcut | yeni, 1:1.

Uretim klasorlerine yazilmaz; cikti olcum CSV'si ve kanit kirpmalaridir.
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
from wp_mockup_common import (DEVICES, SCENES, cover_homography, imread, imwrite_jpeg,  # noqa: E402
                              ink_mask, log, render_screen)
from wp_watch_probe import hale_profili, hale_haritasi  # noqa: E402
from wp_spill_probe import KISA, KENAR_ADI, etiket, tasma_olc  # noqa: E402
from wp_mockup_common import warp_cover  # noqa: E402

SEMBOL = (106, 236, 895, 976)     # WP_LAYOUT_SPEC 3: Watch sembol kutusu
PAY = 40
PENCERE = (420, 280)


def geri(scene, wp_shape, quad):
    H0, W0 = wp_shape[:2]
    Hc, _ = cover_homography(wp_shape, quad)
    return cv2.warpPerspective(scene, np.linalg.inv(Hc.astype(np.float64)), (W0, H0),
                               flags=cv2.INTER_CUBIC)


def hale(ad, bgr, ink, ek, satirlar):
    h, _ = hale_profili(bgr, ink)
    r = np.abs(hale_haritasi(bgr))
    kendi = cv2.dilate((ink > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    halka = (cv2.dilate(kendi, np.ones((21, 21), np.uint8)) > 0) & (kendi == 0)
    uzak = ~(cv2.dilate(kendi, np.ones((41, 41), np.uint8)) > 0)
    row = dict(ek)
    row.update(katman=ad, hale_0_5=h.get("fark_0_5"), hale_5_10=h.get("fark_5_10"),
               hale_10_20=h.get("fark_10_20"), hale_20_40=h.get("fark_20_40"),
               halka_kalinti=round(float(r[halka].mean()), 3) if halka.sum() > 50 else None,
               uzak_zemin=round(float(r[uzak].mean()), 3) if uzak.sum() > 50 else None)
    satirlar.append(row)
    log(f"  {ad:<34} hale 0-5 {row['hale_0_5']} | 5-10 {row['hale_5_10']} | 10-20 {row['hale_10_20']} "
        f"| halka {row['halka_kalinti']} | uzak {row['uzak_zemin']}")
    return row


def sembol_kirp(img):
    l, t, r, b = SEMBOL
    return img[max(0, t - PAY):b + PAY, max(0, l - PAY):r + PAY].copy()


def kisim_a(pair, calib, mock_dir, new_dir, wp_old, wp_new, plates, satirlar, crop_dir, dosyalar):
    up = pair.upper()
    scr = next(s for s in calib["scenes"]["SET07"]["screens"] if s["device"] == "Watch")
    quad = np.asarray(scr["quad"], np.float32)
    W0, H0 = DEVICES["Watch"]
    eski_wp = Path(wp_old) / up / f"AstroLove_{pair}_Midnight_Blue_Watch.jpg"
    yeni_wp = Path(wp_new) / up / f"AstroLove_{pair}_Midnight_Blue_Watch.jpg"
    mevcut_p = Path(mock_dir) / up / f"WA_MOCKUP_V2_SET07_{pair}_FINAL.jpg"
    yeni_p = Path(new_dir) / f"WA_MOCKUP_V2_SET07_{pair}_FINAL.jpg"
    plaka_p = Path(plates) / "PLATE_MIDNIGHT_BLUE_WATCH.png"
    for f in (eski_wp, yeni_wp, mevcut_p, yeni_p):
        if not f.exists():
            log(f"  A atlandi: {f} yok")
            return
    eski = imread(eski_wp)
    yeni = imread(yeni_wp)
    ink = ink_mask(eski)
    ek = dict(cift=pair, kisim="A_SAAT")
    plaka = cv2.imread(str(plaka_p), cv2.IMREAD_COLOR) if plaka_p.exists() else None
    hale("kaynak MEVCUT (glow'lu)", eski, ink, ek, satirlar)
    hale("kaynak YENI (glow yok)", yeni, ink, ek, satirlar)
    if plaka is not None and plaka.shape[:2] == (H0, W0):
        hale("plaka (murekkepsiz)", plaka, ink, ek, satirlar)
    hale("render MEVCUT (relight+cubic)", geri(imread(mevcut_p), eski.shape, quad), ink, ek, satirlar)
    hale("render YENI (paste+lanczos)", geri(imread(yeni_p), eski.shape, quad), ink, ek, satirlar)
    # farklar
    d = np.abs(yeni.astype(np.float32) - eski.astype(np.float32)).mean(axis=2)
    dist = cv2.distanceTransform(1 - (ink > 0).astype(np.uint8), cv2.DIST_L2, 5)
    prof = {}
    for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40)]:
        sel = (dist > lo) & (dist <= hi)
        prof[f"fark_{lo}_{hi}"] = round(float(d[sel].mean()), 2) if sel.sum() > 30 else None
    satirlar.append(dict(cift=pair, kisim="A_SAAT", katman="kaynak YENI - MEVCUT farki", **prof))
    log(f"  kaynak yeni-mevcut fark profili: {prof}")

    def panel(parcalar, adlar, ad):
        ims = [sembol_kirp(x) for x in parcalar]
        for im, t in zip(ims, adlar):
            etiket(im, t)
        p = np.hstack([np.hstack([im, np.full((im.shape[0], 8, 3), 255, np.uint8)]) for im in ims])
        f = Path(crop_dir) / f"M10_{pair}_{ad}.jpg"
        f.parent.mkdir(parents=True, exist_ok=True)
        imwrite_jpeg(f, p)
        dosyalar.append(f.name)

    if plaka is not None:
        panel([geri(imread(mevcut_p), eski.shape, quad), geri(imread(yeni_p), eski.shape, quad), plaka],
              ["MEVCUT render", "YENI render (glow yok + lanczos)", "PLAKA"], "SET07_SAAT_3PANEL")
        panel([eski, yeni, plaka], ["kaynak MEVCUT", "kaynak YENI (glow yok)", "PLAKA"], "WATCH_KAYNAK_3PANEL")


def erode_maske(soft, px):
    hard = (soft >= 0.5).astype(np.uint8)
    k = 2 * px + 1
    er = cv2.erode(hard, np.ones((k, k), np.uint8))
    return cv2.GaussianBlur(er.astype(np.float32), (0, 0), 0.8)


def kenar_pencere(img, a, b):
    c = (np.asarray(a, np.float32) + np.asarray(b, np.float32)) / 2.0
    W, H = PENCERE
    x0 = max(0, min(img.shape[1] - W, int(round(c[0] - W / 2))))
    y0 = max(0, min(img.shape[0] - H, int(round(c[1] - H / 2))))
    return img[y0:y0 + H, x0:x0 + W].copy()


def kisim_b(pair, calib, calib_dir, masters, wp_old, hedefler, erode_px, satirlar, crop_dir, dosyalar):
    up = pair.upper()
    for scene, sid in hedefler:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(masters) / cfg["master"])
        scr = next(s for s in calib["scenes"][src]["screens"] if s["id"] == sid)
        quad = np.asarray(scr["quad"], np.float32)
        ed = scr["edition"]
        wp = imread(Path(wp_old) / up / f"AstroLove_{pair}_{ed}_{scr['device']}.jpg")
        soft = cv2.imread(str(Path(calib_dir) / "masks" / f"{src}_{sid}.png"), cv2.IMREAD_GRAYSCALE)
        if soft is None:
            log(f"  B atlandi: maske yok {src}_{sid}.png")
            continue
        soft = soft.astype(np.float32) / 255.0
        soft_e = erode_maske(soft, erode_px)
        wn = warp_cover(wp, quad, master.shape)
        ciktilar = {}
        for ad, sm in (("MEVCUT", soft), (f"YENI ({erode_px} px erode)", soft_e)):
            out = master.astype(np.float32).copy()
            render_screen(out, master, scr, wp, wp, "paste", sm, edition_swap=False)
            o = np.clip(np.round(out), 0, 255).astype(np.uint8)
            ciktilar[ad] = o
            r = dict(cift=pair, kisim="B_TASMA", sahne=scene, ekran=sid, edisyon=KISA.get(ed, ed), durum=ad)
            r.update(tasma_olc(o, master, sm, quad, wn, ref_soft=soft))
            # eroze ile kaybedilen ekran alani
            r["kapanan_ekran_px"] = int(((soft >= 0.5) & (sm < 0.5)).sum())
            satirlar.append(r)
            kenar = ", ".join(f"{k} {r[f'tasma_{k}']}" for k in KENAR_ADI if r.get(f"tasma_{k}")) or "-"
            log(f"  {scene}/{sid} {KISA.get(ed, ed)} {ad:<22} tasma {r['tasma_px']} px, "
                f"{r['tasma_piksel']} piksel [{kenar}] | kapanan ekran {r['kapanan_ekran_px']} px")
        satir = []
        for i, knm in enumerate(KENAR_ADI):
            a, b = quad[i], quad[(i + 1) % 4]
            ims = []
            for ad in ciktilar:
                w = kenar_pencere(ciktilar[ad], a, b)
                etiket(w, f"{knm} - {ad}")
                ims.append(w)
            satir.append(np.hstack([np.hstack([im, np.full((im.shape[0], 8, 3), 255, np.uint8)]) for im in ims]))
        panel = np.vstack([np.vstack([s, np.full((8, s.shape[1], 3), 255, np.uint8)]) for s in satir])
        f = Path(crop_dir) / f"M10_{pair}_{scene}_S{sid}_KENAR_ONCE_SONRA.jpg"
        f.parent.mkdir(parents=True, exist_ok=True)
        imwrite_jpeg(f, panel)
        dosyalar.append(f.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--mock-dir", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--wp-old", required=True)
    ap.add_argument("--wp-new", required=True)
    ap.add_argument("--plates", required=True)
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--spill-pair", required=True)
    ap.add_argument("--spill-screens", default="SET03:3,SET04:1")
    ap.add_argument("--erode", type=int, default=2)
    ap.add_argument("--crop-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    satirlar, dosyalar = [], []
    for pair in [p.strip() for p in a.pairs.split(",") if p.strip()]:
        log(f"=== A) SAAT: {pair} ===")
        kisim_a(pair, calib, a.mock_dir, a.new_dir, a.wp_old, a.wp_new, a.plates,
                satirlar, a.crop_dir, dosyalar)
    hedefler = [(t.split(":")[0], int(t.split(":")[1])) for t in a.spill_screens.split(",") if t]
    log(f"\n=== B) TASMA: {a.spill_pair}, maske {a.erode} px erode ===")
    kisim_b(a.spill_pair, calib, a.calib, a.masters, a.wp_old, hedefler, a.erode,
            satirlar, a.crop_dir, dosyalar)

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\n{a.out}: {len(satirlar)} satir, {len(dosyalar)} kanit dosyasi")

    lines = ["## A) SAAT (glow yalniz buyuk cihazlarda + lanczos + relight kapali)", "",
             "| cift | katman | hale 0-5 | 5-10 | 10-20 | 20-40 | halka kalinti | uzak zemin |",
             "|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "A_SAAT" and "hale_0_5" in r:
            lines.append(f"| {r['cift']} | {r['katman']} | {r['hale_0_5']} | {r['hale_5_10']} | "
                         f"{r['hale_10_20']} | {r['hale_20_40']} | {r['halka_kalinti']} | {r['uzak_zemin']} |")
    lines += ["", "## B) TASMA (maske erode, ayni referans sinir)", "",
              "| sahne | ekran | edisyon | durum | tasma px | tasan piksel | kenarlar | kapanan ekran px |",
              "|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "B_TASMA":
            kenar = ", ".join(f"{k} {r[f'tasma_{k}']}" for k in KENAR_ADI if r.get(f"tasma_{k}")) or "-"
            lines.append(f"| {r['sahne']} | {r['ekran']} | {r['edisyon']} | {r['durum']} | {r['tasma_px']} | "
                         f"{r['tasma_piksel']} | {kenar} | {r['kapanan_ekran_px']} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
