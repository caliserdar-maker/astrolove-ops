#!/usr/bin/env python3
"""
Wallpaper yerlesim olcumu (WALLPAPER/FINAL_V2/<PAIR>).

Onayli pilot dosyalarindan uretim kuralini TURETIR (tahmin etmez):
  - zemin rengi        : kenar bandinin medyani
  - ana kutu (poster)  : zeminden farkli en buyuk baglantili bilesen bbox'i
                          (doluluk yuksekse dolu dikdortgen = poster; dusukse
                          yalniz murekkep, yani poster zemini tuvalle ayni)
  - murekkep/altin     : ana kutu icindeki en belirgin farkli piksellerin medyani
  - tagline            : ana kutunun ALTINDA kalan kucuk bilesenlerin birlesimi
  - watch              : tum farkli piksellerin birlesimi = sembol kutusu

Kullanim:
  wp_measure_spec.py --dir _work/final --json _out/spec.json --md _out/spec.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None

NAME_RE = re.compile(
    r"AstroLove_(?P<s1>[A-Za-z]+)_(?P<s2>[A-Za-z]+)_(?P<ed>[A-Za-z]+_[A-Za-z]+)_(?P<dev>[A-Za-z]+)\.jpe?g$"
)
DIFF_T = 14      # zeminden fark esigi (JPEG gurultusu ~3-6)
INK_T = 40       # murekkep icin daha sert esik
MIN_AREA = 30    # piksel; daha kucuk bilesenler gurultu sayilir


def bbox_of(mask):
    ys, xs = np.where(mask)
    if ys.size == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def median_rgb(pixels):
    if pixels.size == 0:
        return None
    return [int(v) for v in np.median(pixels.reshape(-1, 3), axis=0)]


def measure(path):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    H, W = im.shape[:2]
    band = max(8, int(min(W, H) * 0.02))
    border = np.concatenate(
        [im[:band].reshape(-1, 3), im[-band:].reshape(-1, 3),
         im[:, :band].reshape(-1, 3), im[:, -band:].reshape(-1, 3)]
    )
    bg = np.median(border, axis=0)
    bg_spread = [int(v) for v in np.percentile(border, 95, axis=0) - np.percentile(border, 5, axis=0)]
    diff = np.abs(im - bg).max(axis=2)
    mask = diff > DIFF_T

    lab, n = ndimage.label(mask)
    comps = []
    if n:
        areas = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
        objs = ndimage.find_objects(lab)
        for i, (a, sl) in enumerate(zip(areas, objs), start=1):
            if a < MIN_AREA or sl is None:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            comps.append(dict(id=i, area=int(a), bbox=[int(x0), int(y0), int(x1), int(y1)]))
    comps.sort(key=lambda c: -c["area"])

    out = dict(file=Path(path).name, W=W, H=H, bg_rgb=[int(v) for v in bg],
               bg_spread=bg_spread, n_components=len(comps))
    m = NAME_RE.search(Path(path).name)
    if m:
        out.update(pair=f"{m['s1']}_{m['s2']}", edition=m["ed"], device=m["dev"])
    if not comps:
        out["main_bbox"] = None
        return out

    main = comps[0]
    mb = main["bbox"]
    mw, mh = mb[2] - mb[0], mb[3] - mb[1]
    fill = main["area"] / float(mw * mh)
    out["main_bbox"] = mb
    out["main_size"] = [mw, mh]
    out["main_fill"] = round(fill, 3)
    out["main_ratio_w_h"] = round(mw / mh, 4)
    out["main_center_pct"] = [round((mb[0] + mb[2]) / 2 / W * 100, 2),
                              round((mb[1] + mb[3]) / 2 / H * 100, 2)]
    out["main_pct"] = dict(l=round(mb[0] / W * 100, 2), t=round(mb[1] / H * 100, 2),
                           r=round(mb[2] / W * 100, 2), b=round(mb[3] / H * 100, 2),
                           w=round(mw / W * 100, 2), h=round(mh / H * 100, 2))
    # poster ic zemini: ana kutu icinde zeminden farkli ama murekkep olmayan piksel medyani
    sub = im[mb[1]:mb[3], mb[0]:mb[2]]
    sub_diff = diff[mb[1]:mb[3], mb[0]:mb[2]]
    soft = (sub_diff > DIFF_T) & (sub_diff <= INK_T)
    hard = sub_diff > INK_T
    out["main_soft_rgb"] = median_rgb(sub[soft]) if soft.any() else None
    out["ink_rgb"] = median_rgb(sub[hard]) if hard.any() else None
    out["ink_pixels"] = int(hard.sum())

    # tum farkli piksellerin birlesimi (watch icin sembol kutusu)
    areas_all = np.bincount(lab.ravel())
    union = bbox_of(mask & (areas_all[lab] >= MIN_AREA))
    out["union_bbox"] = union

    # tagline: ana kutunun altinda kalan bilesenler (yukseklik < %6 H)
    below = [c for c in comps[1:] if c["bbox"][1] >= mb[3] - 2 and (c["bbox"][3] - c["bbox"][1]) < H * 0.06]
    if below:
        xs0 = min(c["bbox"][0] for c in below); ys0 = min(c["bbox"][1] for c in below)
        xs1 = max(c["bbox"][2] for c in below); ys1 = max(c["bbox"][3] for c in below)
        tb = [xs0, ys0, xs1, ys1]
        tsub = im[ys0:ys1, xs0:xs1]
        tmask = diff[ys0:ys1, xs0:xs1] > INK_T
        out["tagline_bbox"] = tb
        out["tagline_pct"] = dict(cx=round((xs0 + xs1) / 2 / W * 100, 2),
                                  cy=round((ys0 + ys1) / 2 / H * 100, 2),
                                  h=round((ys1 - ys0) / H * 100, 2),
                                  gap_from_main=round((ys0 - mb[3]) / H * 100, 2))
        out["tagline_rgb"] = median_rgb(tsub[tmask]) if tmask.any() else None
        out["tagline_components"] = len(below)
    else:
        out["tagline_bbox"] = None

    # ana kutu disinda, tagline disinda kalan buyuk bilesenler (beklenmeyen ogeler)
    others = [c for c in comps[1:] if c not in below and c["area"] > 0.001 * W * H]
    out["other_components"] = [dict(area=c["area"], bbox=c["bbox"]) for c in others[:5]]
    return out


def fmt(v):
    return "" if v is None else (",".join(str(x) for x in v) if isinstance(v, list) else str(v))


def to_markdown(rows):
    md = ["| dosya | tuval | zemin RGB | ana kutu l,t,r,b | boyut | doluluk | oran w/h | murekkep RGB | tagline kutu | tagline RGB |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| {f} | {W}x{H} | {bg} | {mb} | {ms} | {fill} | {ratio} | {ink} | {tb} | {tc} |".format(
            f=r["file"], W=r["W"], H=r["H"], bg=fmt(r["bg_rgb"]), mb=fmt(r.get("main_bbox")),
            ms=fmt(r.get("main_size")), fill=r.get("main_fill", ""), ratio=r.get("main_ratio_w_h", ""),
            ink=fmt(r.get("ink_rgb")), tb=fmt(r.get("tagline_bbox")), tc=fmt(r.get("tagline_rgb"))))
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--json", default="spec.json")
    ap.add_argument("--md", default="spec.md")
    a = ap.parse_args()
    files = sorted(Path(a.dir).glob("*.jp*g"))
    if not files:
        sys.exit(f"HATA: {a.dir} altinda jpg yok.")
    rows = []
    for p in files:
        r = measure(p)
        rows.append(r)
        print(f"{r['file']}: {r['W']}x{r['H']} bg={r['bg_rgb']} main={r.get('main_bbox')} "
              f"fill={r.get('main_fill')} tagline={r.get('tagline_bbox')}", flush=True)
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    Path(a.md).write_text(to_markdown(rows) + "\n", encoding="utf-8")
    print("===JSON_BEGIN===")
    print(json.dumps(rows))
    print("===JSON_END===")


if __name__ == "__main__":
    main()
