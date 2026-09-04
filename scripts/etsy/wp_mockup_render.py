#!/usr/bin/env python3
"""
wp-mockup render: kalibre sahne masterlarina yeni ciftin FINAL_V2
wallpaper'larini isler, 3000x2250 galeri gorsellerini uretir ve QC yapar.
Drive'a/Etsy'ye yazmaz; workflow ciktiyi Drive'a kopyalar.

  --calib      kalibrasyon klasoru (calib.json + masks/)
  --masters    pilot *_FINAL.jpg klasoru
  --pilot      pilot FINAL_V2 wallpaper klasoru
  --wallpapers yeni ciftin FINAL_V2 klasoru
  --pair       yeni cift (Aries_Taurus); pilotun kendisi de olabilir
  --scenes     SET01,SET03,SET04,SET06,SET07,SET10Y (varsayilan hepsi)
  --compare    istege bagli: SET04 icin mevcut 2048x1536 FINAL ile kiyas
  --out        cikti klasoru (jpg + qc/ + report.md + qc.json)

QC (her ekran):
  a) bagimsiz geri-tespit: yazilan JPEG'de yeni wallpaper SIFT/sablon ile
     yeniden bulunur; dortgen kalibre dortgene <=1.5 px, inlier >= 20
     (Watch: sablon corr >= 0.90);
  b) sahne disi: out - master farki (dortgenler disinda) <= 1.0 (JPEG);
  c) murekkep degisimi: pair != pilot ise yeni murekkep bolgesinde out !=
     master (degisim gerceklesti);
  d) boyut 3000x2250, JPEG kalite 95, 4:4:4, baseline.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from wp_mockup_common import (GALLERY_ORDER, SCENES, cover_homography, dump_json, imread, imwrite_jpeg, ink_mask,
                              load_wallpapers, log, poly_mask, qc_sheet, render_screen, set_warp_mode,
                              sift_matches,
                              template_candidate, warp_mask)


def out_name(scene, pair):
    return SCENES[scene].get("out_name", "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(scene=scene, pair=pair)


def recheck(out_bgr, screen, wp_new):
    """Bagimsiz geri tespit: yeni wallpaper'i ciktida bul, kalibre dortgenle kiyasla."""
    gray = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2GRAY)
    q0 = np.asarray(screen["quad"], np.float32)
    if screen["device"] == "Watch":
        qi = np.round(q0).astype(int)
        pad = 60
        roi = (max(0, qi[:, 0].min() - pad), max(0, qi[:, 1].min() - pad),
               min(gray.shape[1], qi[:, 0].max() + pad), min(gray.shape[0], qi[:, 1].max() + pad))
        c = template_candidate(gray, wp_new, roi=roi, s_lo=screen["scale"] - 0.02, s_hi=screen["scale"] + 0.02)
        if c is None:
            return dict(ok=False, reason="sablon bulunamadi")
        dev = float(np.abs(c["quad"] - q0).max())
        return dict(ok=(c["corr"] >= 0.90 and dev <= 1.5), corr=c["corr"], max_dev_px=dev, center_dev_px=dev)
    # SIFT: ciktida bulunan eslesmeler render'in KULLANDIGI cover homografisi
    # (warp_cover; render_screen ile ayni - stretch-to-fill DEGIL) ile yeniden
    # yansitilir; >= 20 eslesme 3 px icinde ve medyan hata <= 1.5 px ise
    # yerlesim dogrulanir.
    inq = poly_mask(gray.shape, q0)
    excl = (cv2.dilate(inq, np.ones((41, 41), np.uint8)) == 0).astype(np.uint8) * 255   # dortgen disi haric
    p1, p2, _ = sift_matches(gray, wp_new, exclude=excl)
    if len(p1) < 20:
        return dict(ok=False, reason=f"SIFT eslesme {len(p1)} < 20")
    Hc, _ = cover_homography(wp_new.shape, q0)
    proj = cv2.perspectiveTransform(p1.reshape(-1, 1, 2), Hc).reshape(-1, 2)
    err = np.linalg.norm(proj - p2, axis=1)
    inl = int((err < 3.0).sum())
    med = float(np.median(err[err < 3.0])) if inl else float("nan")
    return dict(ok=(inl >= 20 and med <= 1.5), inliers=inl, matches=int(len(p1)), median_err_px=med,
                center_dev_px=med, max_dev_px=float(np.percentile(err[err < 3.0], 95)) if inl else float("nan"))


def render_scene(scene, calib, masters_dir, pilot_wps, new_wps, pair, out_dir, compare=None,
                 no_relight=False):
    cfg = SCENES[scene]
    src = cfg.get("calib_from", scene)
    cs = calib["scenes"][src]
    master = imread(Path(masters_dir) / cfg["master"])
    out = master.astype(np.float32).copy()
    edition_map = cfg.get("edition_map")
    used = []
    for s in cs["screens"]:
        pilot_ed = s["edition"]
        new_ed = edition_map[s["id"]] if edition_map else pilot_ed
        wp_pilot = pilot_wps[(pilot_ed, s["device"])]
        wp_new = new_wps.get((new_ed, s["device"]))
        if wp_new is None:
            raise SystemExit(f"HATA: {pair} {new_ed}/{s['device']} wallpaper yok")
        # 4 Eyl 2026 (Mo): relight kod tarafinda kapatilabilir; calib.json'a
        # DOKUNULMAZ. Kapaliyken relight ekranlari paste ile uretilir (kalibre
        # yumusak maske gerekir), diger modlar aynen kalir.
        mode = "paste" if new_ed != pilot_ed else s["mode"]
        if no_relight and mode == "relight":
            mode = "paste"
        soft = None
        if mode == "paste":
            soft = cv2.imread(str(Path(calib["dir"]) / "masks" / f"{src}_{s['id']}.png"), cv2.IMREAD_GRAYSCALE)
            if soft is None:
                raise SystemExit(f"HATA: maske yok {src}_{s['id']}.png")
            soft = soft.astype(np.float32) / 255.0
        render_screen(out, master, s, wp_new, wp_pilot, mode, soft, edition_swap=(new_ed != pilot_ed))
        used.append(dict(id=s["id"], device=s["device"], pilot_edition=pilot_ed, edition=new_ed, mode=mode,
                         quad=s["quad"], scale=s["scale"], H=s["H"]))
    out_u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
    name = out_name(scene, pair)
    path = Path(out_dir) / name
    imwrite_jpeg(path, out_u8)
    # ---- QC
    back = imread(path)
    im = Image.open(path)
    qc = dict(file=name, size=[back.shape[1], back.shape[0]], subsampling=__import__("PIL.JpegImagePlugin", fromlist=["x"]).get_sampling(im),
              progressive=bool(im.info.get("progressive")), screens=[], ok=True)
    allq = np.zeros(master.shape[:2], np.uint8)
    for u in used:
        cv2.fillPoly(allq, [np.round(np.asarray(u["quad"])).astype(np.int32)], 255)
    outside = cv2.dilate(allq, np.ones((5, 5), np.uint8)) == 0
    d_out = float(np.abs(back.astype(np.float32) - master.astype(np.float32)).mean(axis=2)[outside].mean())
    qc["outside_mean_diff"] = d_out
    qc["ok"] &= d_out <= 1.0 and back.shape[1] == 3000 and back.shape[0] == 2250 and qc["subsampling"] == 0 and not qc["progressive"]
    for u in used:
        wp_new = new_wps[(u["edition"], u["device"])]
        r = recheck(back, u, wp_new)
        # murekkep degisimi (pilot disi cift veya edisyon degisimi)
        ink_w = warp_mask(ink_mask(wp_new), u["H"], master.shape) > 0
        chg = float(np.abs(back.astype(np.float32) - master.astype(np.float32)).mean(axis=2)[ink_w].mean()) if ink_w.any() else 0.0
        r.update(id=u["id"], device=u["device"], edition=u["edition"], mode=u["mode"], ink_change=chg)
        if pair != calib["pilot_pair"] or u["edition"] != u["pilot_edition"]:
            r["ok"] = bool(r.get("ok")) and chg > 5.0
        qc["screens"].append(r)
        qc["ok"] &= bool(r.get("ok"))
    if compare and scene == "SET04":
        cmp_ = imread(compare)
        small = cv2.resize(back, (cmp_.shape[1], cmp_.shape[0]), interpolation=cv2.INTER_AREA)
        d = np.abs(small.astype(np.float32) - cmp_.astype(np.float32)).mean(axis=2)
        sq = cv2.resize(allq, (cmp_.shape[1], cmp_.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        qc["compare"] = dict(file=Path(compare).name, size=[cmp_.shape[1], cmp_.shape[0]],
                             inside_quads_mean=float(d[sq].mean()), outside_quads_mean=float(d[~sq].mean()))
    qc_dir = Path(out_dir) / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    qc_sheet(back, used, qc_dir / f"{scene}_{pair}.png")
    return qc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--wallpapers", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--scenes", default=",".join(GALLERY_ORDER))
    ap.add_argument("--compare", default="")
    ap.add_argument("--warp", default="mevcut", choices=("mevcut", "lanczos"),
                    help="ekran kucultme yolu")
    ap.add_argument("--no-relight", action="store_true",
                    help="relight modundaki ekranlari paste ile uret (calib.json degismez)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    set_warp_mode(a.warp)
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    calib["dir"] = a.calib
    pilot_wps = load_wallpapers(a.pilot, calib["pilot_pair"])
    same = Path(a.wallpapers).resolve() == Path(a.pilot).resolve() and a.pair == calib["pilot_pair"]
    new_wps = pilot_wps if same else load_wallpapers(a.wallpapers, a.pair)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    results = {}
    all_ok = True
    rows = ["| Sahne | Dosya | # | Cihaz | Edisyon | Mod | Geri tespit (inlier/corr) | Hata medyan/p95 px | Murekkep degisimi | Sahne disi fark | QC |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for scene in [s for s in a.scenes.split(",") if s]:
        log(f"== {scene}")
        qc = render_scene(scene, calib, a.masters, pilot_wps, new_wps, a.pair, a.out,
                          a.compare or None, no_relight=a.no_relight)
        results[scene] = qc
        all_ok &= bool(qc["ok"])
        for r in qc["screens"]:
            det = r.get("inliers", r.get("corr", "-"))
            rows.append(f"| {scene} | {qc['file']} | {r['id']} | {r['device']} | {r['edition']} | {r['mode']} | {det} | "
                        f"{r.get('center_dev_px', float('nan')):.2f} / {r.get('max_dev_px', float('nan')):.2f} | {r['ink_change']:.1f} | {qc['outside_mean_diff']:.2f} | {'PASS' if r.get('ok') else 'FAIL'} |")
        if "compare" in qc:
            c = qc["compare"]
            rows.append(f"| {scene} | kiyas {c['file']} {c['size'][0]}x{c['size'][1]} | | | | | | | ekran ici {c['inside_quads_mean']:.2f} | sahne disi {c['outside_quads_mean']:.2f} | |")
        log(json.dumps(qc, indent=1, default=float))
    dump_json(results, Path(a.out) / "qc.json")
    md = "\n".join(rows) + f"\n\nSONUC: {'PASS' if all_ok else 'FAIL'}\n"
    (Path(a.out) / "report.md").write_text(md)
    log(md)
    if not all_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
