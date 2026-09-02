#!/usr/bin/env python3
"""
wp-build-pair: bir ciftin 16 wallpaper'i (4 edisyon x 4 cihaz) = temiz plaka
(PLATE_<ED>_<DEV>.png) + posterden FARK AKTARIMI.

Ink katmani (Mo, 2 Eyl kapsam 2): posterden YALNIZ sembol + iki glif + iki isim
alinir (wp_plate_pilot.ink_layer_mask: halka elipsi ve posterin kendi ∞'si haric).
Aktarim = plaka + w * (poster - MEDIAN_<ED>) : murekkep ve kabartma halosu,
posterin medyandan sapmasi olarak (murekkep maskesi + 20 px, 6 px yumusak
kenar) tasinir; plaka tonu korunur. Poster ve fark, olculen afin yerlesimle
(wp_plate_pilot.PLACEMENT; Watch merkez kurali) cihaz olcegine INTER_AREA ile
indirilir. Bant/halka/tagline/∞ plakadan gelir.

Cikti: AstroLove_<Pair>_<Edition>_<Device>.jpg (16) + CONTACT_<PAIR>.jpg.
--compare <pilot dir>: Cancer_Libra icin FINAL_V2 ile kiyas (murekkep bolgesi
ort. |fark|, bolge disi maks fark) -> compare_<pair>.json.
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, EDITIONS, imread, imwrite_jpeg, log
from wp_plate_pilot import PLACEMENT, ink_layer_mask, placement

INK_DILATE = 20      # poster px: murekkep + halo (olcum: halo 5 px cihaz olcegi ~ 25 poster px)
INK_SOFT = 6.0       # poster px: agirlik kenari Gauss sigma
CONTACT_W = 300


def transfer_weight(poster, ed):
    ink = ink_layer_mask(poster, ed)
    k = 2 * INK_DILATE + 1
    w = cv2.dilate(ink, np.ones((k, k), np.uint8)).astype(np.float32)
    return cv2.GaussianBlur(w, (0, 0), INK_SOFT), ink


def place(src, dev, canvas_shape):
    """Poster olcegindeki (7200x9600) goruntuyu cihaz olcegine indirip tuvale yerlestirir (disi 0)."""
    s, (w, h), x0, y0 = placement(dev)
    small = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
    H, W = canvas_shape[:2]
    out = np.zeros((H, W) + src.shape[2:], np.float32)
    x0i, y0i = int(round(x0)), int(round(y0))
    ys0, ys1 = max(0, y0i), min(H, y0i + h); xs0, xs1 = max(0, x0i), min(W, x0i + w)
    out[ys0:ys1, xs0:xs1] = small[ys0 - y0i:ys1 - y0i, xs0 - x0i:xs1 - x0i]
    return out


def build_edition(pair, ed, plates, poster_path, median_path, out_dir, devices, compare_dir=None):
    poster = imread(poster_path)
    if poster.shape[1] != 7200 or poster.shape[0] != 9600:
        raise SystemExit(f"HATA: poster {poster.shape[1]}x{poster.shape[0]}")
    median = imread(median_path)
    w_full, ink = transfer_weight(poster, ed)
    diff = poster.astype(np.float32) - median.astype(np.float32)
    del median
    results = {}
    for dev in devices:
        plate = imread(plates / f"PLATE_{ed.upper()}_{dev.upper()}.png")
        W, H = DEVICES[dev]
        if plate.shape[1] != W or plate.shape[0] != H:
            raise SystemExit(f"HATA: plaka {dev} {plate.shape[1]}x{plate.shape[0]}")
        D = place(diff, dev, plate.shape)
        Wt = place(w_full, dev, plate.shape)[..., None]
        outp = np.clip(np.round(plate.astype(np.float32) + Wt * D), 0, 255).astype(np.uint8)
        name = f"AstroLove_{pair}_{ed}_{dev}.jpg"
        imwrite_jpeg(out_dir / name, outp)
        info = dict(file=name, ink_px_canvas=int((Wt[..., 0] > 0.5).sum()))
        if compare_dir is not None:
            ref = imread(Path(compare_dir) / name)
            d = np.abs(outp.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
            inkc = Wt[..., 0] > 0.5
            info.update(cmp_ink_mean=float(d[inkc].mean()) if inkc.any() else 0.0, cmp_ink_p95=float(np.percentile(d[inkc], 95)) if inkc.any() else 0.0,
                        cmp_outside_mean=float(d[~inkc].mean()), cmp_outside_max=float(d[~inkc].max()))
        results[dev] = info
        log(f"  {ed} {dev:8s} -> {name}" + (f" | pilot kiyas: murekkep ort {info['cmp_ink_mean']:.2f} p95 {info['cmp_ink_p95']:.1f}, disi ort {info['cmp_outside_mean']:.2f} maks {info['cmp_outside_max']:.0f}" if compare_dir else ""))
    return results


def contact_sheet(pair, in_dir, out_path, editions=EDITIONS, devices=("Phone", "Tablet", "Desktop", "Watch")):
    tiles = []
    for ed in editions:
        row = []
        for dev in devices:
            f = Path(in_dir) / f"AstroLove_{pair}_{ed}_{dev}.jpg"
            W, H = DEVICES[dev]
            th = int(CONTACT_W * H / W)
            cell = np.full((max(th, 1) if False else 420, CONTACT_W, 3), 40, np.uint8)
            if f.exists():
                im = imread(f)
                t = cv2.resize(im, (CONTACT_W, th), interpolation=cv2.INTER_AREA)
                if th > 400:
                    t = t[:400]
                cell[:t.shape[0], :] = t
                cv2.putText(cell, f"{ed[:2]} {dev}", (6, 415), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.putText(cell, f"{ed[:2]} {dev} YOK", (6, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
            row.append(cell)
        tiles.append(np.hstack(row))
    sheet = np.vstack(tiles)
    cv2.putText(sheet, f"{pair}  16 wallpaper", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(str(out_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--pair", required=True, help="Aries_Leo")
    b.add_argument("--plates", required=True)
    b.add_argument("--posters", required=True, help="WA_POSTER_<PAIR>_<ED>_3X4.jpg dosyalari")
    b.add_argument("--medians", required=True, help="MEDIAN_<ED>.png dosyalari")
    b.add_argument("--out", required=True)
    b.add_argument("--editions", default=",".join(EDITIONS))
    b.add_argument("--devices", default="Phone,Tablet,Desktop,Watch")
    b.add_argument("--compare", default="", help="pilot dizini (ayni cift): FINAL_V2 ile kiyas")
    c = sub.add_parser("contact")
    c.add_argument("--pair", required=True)
    c.add_argument("--dir", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "contact":
        contact_sheet(a.pair, a.dir, a.out)
        log(f"kontak sayfasi: {a.out}")
        return
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    eds = [e for e in a.editions.split(",") if e]
    devs = [d for d in a.devices.split(",") if d]
    t0 = time.time(); rep = {}
    for i, ed in enumerate(eds):
        poster = Path(a.posters) / f"WA_POSTER_{a.pair.upper()}_{ed.upper()}_3X4.jpg"
        median = Path(a.medians) / f"MEDIAN_{ed.upper()}.png"
        if not poster.exists() or not median.exists():
            raise SystemExit(f"HATA: eksik girdi {poster if not poster.exists() else median}")
        rep[ed] = build_edition(a.pair, ed, Path(a.plates), poster, median, out, devs, a.compare or None)
        el = time.time() - t0
        log(f"edisyon {i + 1}/{len(eds)}  gecen {el:4.0f}s  kalan {el / (i + 1) * (len(eds) - i - 1):4.0f}s  %{100 * (i + 1) / len(eds):.0f}")
    (out / f"build_{a.pair}.json").write_text(json.dumps(dict(pair=a.pair, editions=rep), indent=1))
    if len(eds) == len(EDITIONS):
        contact_sheet(a.pair, out, out / f"CONTACT_{a.pair.upper()}.jpg")
    log(f"toplam {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
