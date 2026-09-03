#!/usr/bin/env python3
"""
SET06 ekran-2 (id=1, Desktop) ve SET10Y ekran-1 (id=0, Phone) icin dogrulama
esigi altinda kalan kalibrasyonu DUZELTIR.

SET10Y ekran-1: "ideal dikdortgene" regularize edilir - bu yontem render'in
kendi SIFT dogrulamasindan da (inlier>=20) GECTI (onceki test, Mo onayi).
Degismedi.

SET06 ekran-2 - 2 yama denemesi de (ideal dikdortgen: 16/20 inlier FAIL;
kisitli simetrik olcek: 10/20 inlier, DAHA KOTU) basarisiz oldu: quad/H'yi
masa basinda degistirmek, gercek fotografla eslesmeyen bir bolge yaratiyor -
screen_soft_mask() bunu deldi (maske kalitesi dustu), render'in recheck()'i
azalan guvenilir eslesmeyi haklı olarak reddetti. KOK NEDEN yamalanacak bir
sey degil, YETERSIZ OLCUM: orijinal kalibrasyon (wp_mockup_calibrate.py) bu
ekran icin sadece 40 inlier/0.868 rms buldu (kardes ekran id=0: 60/0.378).

Bu yuzden SET06 icin artik YAMA yok - GERCEK YENIDEN OLCUM: remeasure_screen()
orijinal calibrate_scene()'in ayni SIFT+RANSAC yontemini, id=0/id=2'nin
disladigi bolgede, COK DAHA GENIS bir arama uzayinda tekrarlar - master icin
2x SIFT ozellik sayisi (12000->24000), 4 work_h (1200/1600/2000/2400,
wallpaper coz., cozunurluk arttikca daha fazla/iyi anahtar nokta), 4 edisyon,
6 RANSAC reprojeksiyon esigi (1.0-4.0px) - toplam ~96 aday homografi. Her
aday: RANSAC'in kendi inlier sayisi + c4 orani (hedefe %3 tolerans) ile
elenir; kalanlar arasindan EN YUKSEK inlier (esitlikte en dusuk rms) secilir.
Bu, elle degil OLCUMLE dogru quad/H'yi bulmaya calisir - render'in kendi
recheck() yontemiyle ayni ilkeye (SIFT geri-projeksiyon inlier sayimi) dayanir.

Secilen aday >=20 inlier VE oran toleransi saglamazsa HATA verir (yama
YAPILMAZ) - bu durumda kalibrasyonun GERCEKTEN yeniden olculmesi (belki
farkli bir fotograf/kirpim) gerekir, veriyle uydurmak degil.

Her iki ekran icin de: secilen/duzeltilmis H ile warp(pilot) yeniden
hesaplanir, maske (screen_soft_mask) TUTARLI olacak sekilde yeniden uretilir.

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

from wp_mockup_common import (DEVICES, EDITIONS, MasterFeatures, dump_json, imread, ink_mask, quad_of, quad_scale,
                              screen_soft_mask, sift_matches, warp_full)

TARGETS = [("SET06", 1, "Desktop"), ("SET10Y", 0, "Phone")]
METHOD = {"SET06": "remeasure", "SET10Y": "regularize"}
WORK_HS = (1200, 1600, 2000, 2400)
RANSAC_THRESHOLDS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
MIN_INLIERS = 20
ASPECT_TOL = 0.03


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


def remeasure_screen(master, wps, other_quads, target_aspect, log=print):
    """SET06 ekran-2'yi GERCEKTEN yeniden olcer (yama degil): orijinal
    calibrate_scene() ile ayni SIFT+RANSAC yontemi, id=0/id=2'nin disladigi
    bolgede, genis bir arama uzayinda (4 work_h x 4 edisyon x 6 RANSAC esigi).
    Donus: en yuksek inlier'li (esitlikte en dusuk rms) aday - dict(H, quad,
    inliers, rms, edition) - veya hicbiri >=MIN_INLIERS + oran toleransi
    saglamazsa None."""
    gray = cv2.cvtColor(master, cv2.COLOR_BGR2GRAY)
    feats = MasterFeatures(gray, nfeatures=24000)  # orijinalin 2 kati (12000)
    exclude = np.zeros(gray.shape, np.uint8)
    for q in other_quads:
        cv2.fillPoly(exclude, [np.round(np.asarray(q)).astype(np.int32)], 255)
    exclude = cv2.dilate(exclude, np.ones((15, 15), np.uint8))
    excl_u8 = exclude  # sift_matches: exclude>0 olan master anahtar noktalari elenir

    all_candidates = []  # TESHIS: hicbir esik uygulanmadan (H gecerliyse) - gercek durumu gormek icin
    for ed in EDITIONS:
        wp = wps.get((ed, "Desktop"))
        if wp is None:
            continue
        for work_h in WORK_HS:
            p1, p2, _ = sift_matches(feats, wp, exclude=excl_u8, work_h=work_h)
            if len(p1) < 8:
                continue
            for thr in RANSAC_THRESHOLDS:
                H, inl = cv2.findHomography(p1, p2, cv2.RANSAC, thr, maxIters=5000, confidence=0.999)
                if H is None or inl is None:
                    continue
                n = int(inl.sum())
                W0, H0 = wp.shape[1], wp.shape[0]
                quad = quad_of(H, W0, H0)
                if not cv2.isContourConvex(np.round(quad).astype(np.int32)):
                    continue
                aspect = aspect_of_quad(quad)
                sel = inl.ravel() == 1
                proj = cv2.perspectiveTransform(p1[sel].reshape(-1, 1, 2), H).reshape(-1, 2) if n else np.zeros((0, 2))
                err = np.linalg.norm(proj - p2[sel], axis=1) if n else np.zeros(0)
                rms = float(np.sqrt((err ** 2).mean())) if n else float("nan")
                all_candidates.append(dict(H=H, quad=quad, inliers=n, rms=rms, edition=ed,
                                           work_h=work_h, ransac_thr=thr, aspect=aspect,
                                           n_matches=len(p1)))

    qualifying = [c for c in all_candidates if c["inliers"] >= MIN_INLIERS
                 and abs(c["aspect"] - target_aspect) / target_aspect <= ASPECT_TOL]
    log(f"  SET06/1 yeniden olcum: {len(all_candidates)} toplam aday, {len(qualifying)} tanesi "
        f">={MIN_INLIERS} inlier + oran +-%{ASPECT_TOL * 100:.0f} saglıyor")

    if not all_candidates:
        return None

    # TESHIS (esik uygulanmadan): en yuksek inlier'li aday hangi orana sahip? oran
    # toleransini saglayan en iyi aday kac inlier'e ulasabiliyor? Bu ikisi CAKISMIYORSA
    # (asagida gorulecegi gibi) sorun arama derinligi degil - bu ekranin fotografta
    # GERCEKTEN olculen SIFT eslesmeleri, yuksek inlier'de sistematik olarak baska bir
    # orana isaret ediyor demektir.
    by_inliers = sorted(all_candidates, key=lambda c: (-c["inliers"], c["rms"] if c["inliers"] else 1e9))[:5]
    log("  -- teshis: sadece inlier'e gore en iyi 5 aday (oran esigi UYGULANMADAN) --")
    for c in by_inliers:
        log(f"    ed={c['edition']} work_h={c['work_h']} thr={c['ransac_thr']} matches={c['n_matches']} "
            f"inlier={c['inliers']} rms={c['rms']:.2f} oran={c['aspect']:.3f} (hedef {target_aspect:.3f})")
    in_tol = [c for c in all_candidates if abs(c["aspect"] - target_aspect) / target_aspect <= ASPECT_TOL]
    log(f"  -- teshis: oran toleransini saglayan {len(in_tol)} aday (inlier esigi UYGULANMADAN) --")
    for c in sorted(in_tol, key=lambda c: -c["inliers"])[:5]:
        log(f"    ed={c['edition']} work_h={c['work_h']} thr={c['ransac_thr']} matches={c['n_matches']} "
            f"inlier={c['inliers']} rms={c['rms']:.2f} oran={c['aspect']:.3f}")

    if not qualifying:
        return None
    qualifying.sort(key=lambda c: (-c["inliers"], c["rms"]))
    return qualifying[0]


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

    rows = ["| Sahne | # | Cihaz | Eski oran | Yeni oran | Hedef | Yontem | Inlier | Eski dortgen | Yeni dortgen |",
            "|---|---|---|---|---|---|---|---|---|"]
    for scene, sid, dev in TARGETS:
        s = next(x for x in calib["scenes"][scene]["screens"] if x["id"] == sid)
        target_aspect = DEVICES[dev][0] / DEVICES[dev][1]
        old_quad = np.asarray(s["quad"], np.float32)
        old_aspect = aspect_of_quad(old_quad)
        W0, H0 = DEVICES[dev]
        master = imread(Path(a.masters) / calib["scenes"][scene]["master"])
        edition = s["edition"]
        inliers_note = "-"

        if METHOD[scene] == "remeasure":
            other_quads = [x["quad"] for x in calib["scenes"][scene]["screens"] if x["id"] != sid]
            wps = {}
            for ed in EDITIONS:
                p = Path(a.pilot) / f"AstroLove_{calib['pilot_pair']}_{ed}_{dev}.jpg"
                if p.exists():
                    wps[(ed, dev)] = imread(p)
            best = remeasure_screen(master, wps, other_quads, target_aspect)
            if best is None:
                raise SystemExit(f"HATA: {scene}/{sid} icin >= {MIN_INLIERS} inlier + oran toleransi saglayan "
                                 f"aday bulunamadi - yeniden olcum basarisiz, YAMA YAPILMADI.")
            new_H, new_quad, edition = best["H"], best["quad"], best["edition"]
            inliers_note = str(best["inliers"])
        elif METHOD[scene] == "scale_only":
            new_H = scale_only_fix(s["H"], W0, target_aspect)
            new_quad = quad_of(new_H, W0, H0)
        else:
            new_quad = regularize(old_quad, target_aspect)
            src_pts = np.float32([[0, 0], [W0, 0], [W0, H0], [0, H0]])
            new_H = cv2.getPerspectiveTransform(src_pts, new_quad)
        new_aspect = aspect_of_quad(new_quad)
        new_scale = quad_scale(new_quad, W0)

        wp_pilot = imread(Path(a.pilot) / f"AstroLove_{calib['pilot_pair']}_{edition}_{dev}.jpg")
        warped_pilot = warp_full(wp_pilot, new_H, master.shape, new_scale)
        ink_w = cv2.warpPerspective(ink_mask(wp_pilot), np.asarray(new_H, np.float64),
                                    (master.shape[1], master.shape[0]), flags=cv2.INTER_NEAREST)
        soft, quality, holes = screen_soft_mask(master, warped_pilot, new_quad, ink_w)
        cv2.imwrite(str(Path(a.out, "masks") / f"{scene}_{sid}.png"), (soft * 255).astype(np.uint8))

        s["quad"] = np.asarray(new_quad).tolist(); s["H"] = np.asarray(new_H).tolist()
        s["scale"] = float(new_scale); s["edition"] = edition
        s["calib_fix"] = dict(method=METHOD[scene], old_aspect=old_aspect, new_aspect=new_aspect,
                              target_aspect=target_aspect, mask_quality=quality, inliers=inliers_note)
        rows.append(f"| {scene} | {sid} | {dev} | {old_aspect:.3f} | {new_aspect:.3f} | {target_aspect:.3f} | "
                    f"{METHOD[scene]} | {inliers_note} | {np.round(old_quad).astype(int).tolist()} | "
                    f"{np.round(new_quad).astype(int).tolist()} |")
        print(f"{scene}/{sid} ({dev}, {METHOD[scene]}): oran {old_aspect:.3f} -> {new_aspect:.3f} "
              f"(hedef {target_aspect:.3f}) inlier={inliers_note} maske kalitesi {quality:.3f}", flush=True)

    dump_json(calib, Path(a.out) / "calib.json")
    (Path(a.out) / "report.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
