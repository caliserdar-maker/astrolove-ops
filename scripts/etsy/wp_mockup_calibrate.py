#!/usr/bin/env python3
"""
wp-mockup kalibrasyonu: pilot (Cancer_Libra) galeri mockup'larindaki ekran
dortgenlerini OLCER, her ekrana cihaz/edisyon atar, render modunu secer ve
paste maskelerini cikarir. SALT OLCUM; Etsy'ye dokunmaz.

Girdi:
  --masters  pilot *_FINAL.jpg klasoru (MOCKUP_V2/CANCER_LIBRA)
  --pilot    pilot FINAL_V2 wallpaper klasoru (16 dosya)
  --pair     pilot cift adi (Cancer_Libra)
Cikti (--out):
  calib.json        sahne -> ekranlar (H, quad, cihaz, edisyon, mod, metrikler)
  masks/<scene>_<i>.png   paste maskeleri (0-255)
  qc/<scene>.png    kose/merkez kesit sayfasi
  report.md         job summary'ye basilan tablo

Yontem (docs/WP_MOCKUP_PIPELINE.md):
  1) her (cihaz, edisyon) wallpaper'i SIFT+RANSAC ile master'da aranir,
     bulunan her ornek maskelenip tekrar aranir (ayni cihazin 4 edisyonu ayni
     geometride oldugu icin yanlis edisyon da bulur; bu istenir);
  2) adaylar IoU>0.5 ile kumelenir; her kume icin (H, edisyon) ciftlerinden
     ekran ici farki en dusuk olan secilir (edisyon ayrimi 1.5 vs 27-45);
  3) Watch: sablon eslestirme (SIFT 15 eslesmede kaliyor);
  4) mod: murekkep disi uzak fark > 3 -> relight (parlama/vinyet), degilse paste;
  5) beklenen ekran sayisi (SCENES.expect) tutmazsa HATA.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import (EDITIONS, SCENES, MasterFeatures, center_inside, corner_radius, dump_json, imread, iou,
                              load_wallpapers, log, qc_sheet, quad_scale, screen_metrics, screen_soft_mask,
                              sift_candidates, template_candidate, warp_full, warp_mask, ink_mask, quad_of)

RELIGHT_MIN_BG = 3.0     # murekkep disi uzak fark bu degerin ustundeyse ekranda parlama/vinyet var -> relight
MIN_TEMPLATE_CORR = 0.90


def calibrate_scene(scene, cfg, masters_dir, wps, out_dir):
    master = imread(Path(masters_dir) / cfg["master"])
    if master.shape[1] != 3000 or master.shape[0] != 2250:
        raise SystemExit(f"HATA: {cfg['master']} {master.shape[1]}x{master.shape[0]}, 3000x2250 degil")
    gray = cv2.cvtColor(master, cv2.COLOR_BGR2GRAY)
    feats = MasterFeatures(gray)
    log(f"  master SIFT: {len(feats.kp)} anahtar nokta")
    expect = cfg["expect"]
    cands = []  # dict(device, edition, H, quad, inliers, rms, corr)
    for dev in expect:
        for ed in EDITIONS:
            wp = wps.get((ed, dev))
            if wp is None:
                log(f"  uyari: {ed}/{dev} wallpaper yok, atlandi")
                continue
            if dev == "Watch":
                c = template_candidate(gray, wp)
                if c and c["corr"] >= MIN_TEMPLATE_CORR:
                    cands.append(dict(device=dev, edition=ed, **c))
                    log(f"  sablon {ed}/{dev}: corr {c['corr']:.3f} olcek {c['scale']:.4f}")
            else:
                for c in sift_candidates(feats, wp):
                    cands.append(dict(device=dev, edition=ed, corr=None, **c))
                    log(f"  SIFT {ed}/{dev}: inl {c['inliers']} rms {c['rms']:.2f} quad {np.round(c['quad']).astype(int).tolist()}")
    # kumele
    clusters = []
    for c in sorted(cands, key=lambda c: -(c["inliers"] or 0)):
        for cl in clusters:
            if center_inside(c["quad"], cl[0]["quad"]) or center_inside(cl[0]["quad"], c["quad"]):
                cl.append(c)
                break
        else:
            clusters.append([c])
    screens = []
    for cl in clusters:
        best = None
        for c in cl:
            for ed in EDITIONS:
                wp = wps.get((ed, c["device"]))
                if wp is None:
                    continue
                m, _, _ = screen_metrics(master, wp, c["H"])
                key = m["inside_mean"]
                if best is None or key < best[0]:
                    best = (key, c, ed, m)
        _, c, ed, m = best
        # secilen edisyonla yeniden uydur (daha cok inlier, daha iyi rms)
        H = c["H"]
        if c["device"] != "Watch" and ed != c["edition"]:
            excl = np.full(gray.shape, 255, np.uint8)
            cv2.fillPoly(excl, [np.round(c["quad"]).astype(np.int32)], 0)
            refit = [r for r in sift_candidates(feats, wps[(ed, c["device"])], exclude=excl)
                     if iou(r["quad"], c["quad"], master.shape) > 0.5]
            if refit and refit[0]["inliers"] >= c["inliers"]:
                c = dict(c, H=refit[0]["H"], quad=refit[0]["quad"], inliers=refit[0]["inliers"], rms=refit[0]["rms"])
                H = c["H"]
                m, _, _ = screen_metrics(master, wps[(ed, c["device"])], H)
        wp = wps[(ed, c["device"])]
        W0, H0 = wp.shape[1], wp.shape[0]
        quad = quad_of(H, W0, H0)
        sc = quad_scale(quad, W0)
        mode = "relight" if (m["bg_far_mean"] is not None and m["bg_far_mean"] > RELIGHT_MIN_BG) else "paste"
        warped = warp_full(wp, H, master.shape, sc)
        ink_w = warp_mask(ink_mask(wp), H, master.shape)
        soft, quality, holes = screen_soft_mask(master, warped, quad, ink_w)
        mask_u8 = (soft * 255).astype(np.uint8)
        radii = corner_radius(mask_u8, quad, sc)
        screens.append(dict(device=c["device"], edition=ed, H=H, quad=quad, scale=sc, inliers=c["inliers"], rms=c["rms"],
                            corr=c.get("corr"), mode=mode, metrics=m, mask_quality=quality, mask_holes=holes,
                            corner_radius_wp=radii))
    screens.sort(key=lambda s: float(np.asarray(s["quad"])[:, 0].mean()))
    for i, s in enumerate(screens):
        s["id"] = i
    # beklenti kontrolu
    found = {}
    for s in screens:
        found[s["device"]] = found.get(s["device"], 0) + 1
    if found != expect:
        raise SystemExit(f"HATA: {scene} beklenen {expect}, bulunan {found}")
    # maskeler + qc
    (Path(out_dir) / "masks").mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "qc").mkdir(parents=True, exist_ok=True)
    for s in screens:
        wp = wps[(s["edition"], s["device"])]
        warped = warp_full(wp, s["H"], master.shape, s["scale"])
        soft, _, _ = screen_soft_mask(master, warped, s["quad"], warp_mask(ink_mask(wp), s["H"], master.shape))
        cv2.imwrite(str(Path(out_dir) / "masks" / f"{scene}_{s['id']}.png"), (soft * 255).astype(np.uint8))
    qc_sheet(master, screens, Path(out_dir) / "qc" / f"{scene}.png")
    return dict(master=cfg["master"], screens=screens)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masters", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--pair", default="Cancer_Libra")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    wps = load_wallpapers(a.pilot, a.pair)
    log(f"pilot wallpaper: {len(wps)} dosya")
    want = [s for s in a.scenes.split(",") if s] or [s for s, c in SCENES.items() if "calib_from" not in c]
    calib = dict(pilot_pair=a.pair, scenes={})
    rows = []
    for scene in want:
        cfg = SCENES[scene]
        if "calib_from" in cfg:
            continue
        log(f"== {scene} ({cfg['master']})")
        res = calibrate_scene(scene, cfg, a.masters, wps, a.out)
        calib["scenes"][scene] = res
        for s in res["screens"]:
            m = s["metrics"]
            ink = "-" if m["ink_mean"] is None else f"{m['ink_mean']:.2f}"
            far = "-" if m["bg_far_mean"] is None else f"{m['bg_far_mean']:.2f}"
            rows.append(f"| {scene} | {s['id']} | {s['device']} | {s['edition']} | {np.round(np.asarray(s['quad'])).astype(int).tolist()} | "
                        f"{s['scale']:.4f} | {s['inliers'] or '-'} | {s['rms']:.2f} | {m['inside_mean']:.2f} | {ink} | "
                        f"{far} | "
                        f"{m['luma_ratio_p50']:.3f} | {s['mode']} | {s['mask_quality']:.3f} | {s['mask_holes']} |")
    dump_json(calib, Path(a.out) / "calib.json")
    md = ["| Sahne | # | Cihaz | Edisyon | Dortgen TL,TR,BR,BL | Olcek | Inlier | RMS px | Ic fark | Murekkep fark | Uzak fark | Luma orani | Mod | Maske/dortgen | Delikler (alan,x,y,w,h) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"] + rows
    (Path(a.out) / "report.md").write_text("\n".join(md) + "\n")
    log("\n".join(md))


if __name__ == "__main__":
    main()
