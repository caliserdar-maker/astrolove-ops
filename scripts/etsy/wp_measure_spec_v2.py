#!/usr/bin/env python3
"""
Wallpaper yerlesim olcumu V2 (doku ve gradyan dayanikli).

V1 (wp_measure_spec.py) zeminden farkli en buyuk bolgeyi buluyordu; dokulu
(CI, WP) ve gradyanli (MB) tuvallerde bu "parlak bolge" oluyor, ogeler
okunamiyordu. V2:
  - MUREKKEP MASKESI: yuksek gecirgen filtre (gri - medyan_blur) + Otsu esigi.
    Polarite POSTER ALANINDAN (orta bant) olculur: acik kagit -> koyu murekkep
    (bg-g), koyu kagit -> acik murekkep (g-bg). B62/B63/B69 kurallari.
  - BILESENLER: halka (buyuk, dusuk doluluk, kare-yakin), sembol (halkanin
    icinde, en buyuk), METIN SATIRLARI (halkanin altinda, dikey ortusen
    bilesenler satir olarak gruplanir: satir 1 = isimler, satir 2 = tagline).
  - DESKTOP YAN BANT: sol/sag bant genisligi (poster alani disinda kalan),
    banda ait metrikler: ayna korelasyonu (bant vs ic seridin yansimasi),
    keskinlik orani (Laplace varyansi bant/ic), renk sapmasi, luma egimi.
  - TAGLINE KAYNAGI: OPTIMIZED 3X4 posterin kendisi ayni analizden gecirilir;
    posterde tagline satiri varsa "poster ici" (ayri basilmaz).

Kullanim:
  wp_measure_spec_v2.py --dir _work/final [--posters _work/posters] --json out.json --md out.md
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
WORK_W = 1400          # analiz olcegi (genislik); koordinatlar geri olceklenir
MIN_AREA_FRAC = 2e-5   # bilesen alt siniri (tuval alanina oran)

NAME_RE = re.compile(r"AstroLove_(?P<s1>[A-Za-z]+)_(?P<s2>[A-Za-z]+)_(?P<ed>[A-Za-z]+_[A-Za-z]+)_(?P<dev>[A-Za-z]+)\.jpe?g$")
POSTER_RE = re.compile(r"WA_POSTER_(?P<s1>[A-Z]+)_(?P<s2>[A-Z]+)_(?P<ed>[A-Z]+_[A-Z]+)_3X4\.jpe?g$", re.I)


def otsu(values):
    hist, edges = np.histogram(values, bins=256, range=(0, 255))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total == 0:
        return 0
    w0 = np.cumsum(hist); w1 = total - w0
    m = np.cumsum(hist * np.arange(256))
    mu0 = np.divide(m, w0, out=np.zeros_like(m), where=w0 > 0)
    mu1 = np.divide(m[-1] - m, w1, out=np.zeros_like(m), where=w1 > 0)
    var = w0 * w1 * (mu0 - mu1) ** 2
    return int(np.argmax(var))


def ink_mask(rgb):
    """Donus: mask(bool), polarite('light'|'dark'), esik, kagit_luma"""
    g = rgb.mean(axis=2)
    H, W = g.shape
    # poster alani = orta %50 x %50 bant (sahne kenarlarindan bagimsiz)
    cy0, cy1, cx0, cx1 = int(H * .25), int(H * .75), int(W * .25), int(W * .75)
    paper = float(np.median(g[cy0:cy1, cx0:cx1]))
    # Arka plan: 1/8 olcekte medyan (hiz), sonra geri buyutme. Tam cozunurlukte
    # k~130 medyan filtresi pratikte kosulamaz (k^2 maliyet).
    ds = 8
    small_g = np.asarray(Image.fromarray(g.astype(np.float32)).resize((max(1, W // ds), max(1, H // ds)), Image.BOX), dtype=np.float64)
    k = max(5, (int(min(small_g.shape) * 0.09) // 2) * 2 + 1)
    bg_s = ndimage.median_filter(small_g, size=k, mode="reflect")
    bg = np.asarray(Image.fromarray(bg_s.astype(np.float32)).resize((W, H), Image.BILINEAR), dtype=np.float64)
    d = (bg - g) if paper > 128 else (g - bg)
    d = np.clip(d, 0, 255)
    t = otsu(d[d > 2])          # sifir tabani otsu'yu bozmasin
    t = int(min(max(t, 12), 90))
    mask = d > t
    mask = ndimage.binary_opening(mask, structure=np.ones((2, 2)))
    return mask, ("light" if paper > 128 else "dark"), t, paper


def components(mask, min_area):
    lab, n = ndimage.label(mask)
    out = []
    if n:
        areas = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
        objs = ndimage.find_objects(lab)
        for i, (a, sl) in enumerate(zip(areas, objs), start=1):
            if a < min_area or sl is None:
                continue
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            w, h = x1 - x0, y1 - y0
            out.append(dict(id=i, area=int(a), bbox=[x0, y0, x1, y1], w=w, h=h,
                            fill=round(float(a) / float(w * h), 3), aspect=round(w / h, 3),
                            cx=(x0 + x1) / 2, cy=(y0 + y1) / 2))
    out.sort(key=lambda c: -c["area"])
    return out, lab


def group_rows(comps, y_top):
    """y_top altindaki bilesenleri dikey ortusmeye gore satirlara ayirir."""
    cs = sorted([c for c in comps if c["cy"] > y_top], key=lambda c: c["cy"])
    rows = []
    for c in cs:
        for r in rows:
            if c["bbox"][1] < r["y1"] and c["bbox"][3] > r["y0"]:   # dikey ortusme
                r["x0"] = min(r["x0"], c["bbox"][0]); r["x1"] = max(r["x1"], c["bbox"][2])
                r["y0"] = min(r["y0"], c["bbox"][1]); r["y1"] = max(r["y1"], c["bbox"][3])
                r["n"] += 1; r["area"] += c["area"]
                break
        else:
            rows.append(dict(x0=c["bbox"][0], y0=c["bbox"][1], x1=c["bbox"][2], y1=c["bbox"][3], n=1, area=c["area"]))
    rows.sort(key=lambda r: r["y0"])
    return rows


def scale_box(b, s):
    return [int(round(v * s)) for v in b]


def band_metrics(rgb_full, x0, x1, side):
    """Bant [x0,x1) icin metrikler (tam cozunurlukte, orta %60 satirlar)."""
    H = rgb_full.shape[0]
    rows = slice(int(H * .2), int(H * .8))
    band = rgb_full[rows, x0:x1].astype(np.float64)
    w = x1 - x0
    if w < 8:
        return None
    inner = rgb_full[rows, x1:x1 + w] if side == "left" else rgb_full[rows, x0 - w:x0]
    inner = inner.astype(np.float64)
    if inner.shape[1] != w:
        return None
    g_b, g_i = band.mean(axis=2), inner.mean(axis=2)
    mirror = g_i[:, ::-1]
    def corr(a, b):
        a = a - a.mean(); b = b - b.mean()
        d = np.sqrt((a * a).sum() * (b * b).sum())
        return float((a * b).sum() / d) if d else 0.0
    def lapvar(g):
        return float(ndimage.laplace(g).var())
    lv_b, lv_i = lapvar(g_b), lapvar(g_i)
    col_mean = g_b.mean(axis=0)  # x boyunca luma
    prof = col_mean if side == "left" else col_mean[::-1]   # dis kenardan ice
    return dict(width=int(w), mirror_corr=round(corr(g_b, mirror), 3),
                direct_corr=round(corr(g_b, g_i), 3),
                sharp_ratio=round(lv_b / lv_i, 3) if lv_i else None,
                band_lapvar=round(lv_b, 2), inner_lapvar=round(lv_i, 2),
                color_std=[round(float(v), 1) for v in band.reshape(-1, 3).std(axis=0)],
                luma_outer=round(float(prof[:max(2, w // 8)].mean()), 1),
                luma_inner=round(float(prof[-max(2, w // 8):].mean()), 1),
                luma_profile=[round(float(v), 1) for v in prof[:: max(1, w // 8)][:9]])


def analyze(path, is_poster=False):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    s = WORK_W / W
    small = np.asarray(im.resize((WORK_W, int(H * s)), Image.LANCZOS), dtype=np.float64)
    h, w = small.shape[:2]
    mask, pol, thr, paper = ink_mask(small)
    comps, lab = components(mask, MIN_AREA_FRAC * h * w)
    inv = 1.0 / s
    ink_rgb = [int(v) for v in np.median(small[mask].reshape(-1, 3), axis=0)] if mask.any() else None
    # kagit rengi: poster orta bandinda maske disi
    cy0, cy1, cx0, cx1 = int(h * .25), int(h * .75), int(w * .25), int(w * .75)
    sub, subm = small[cy0:cy1, cx0:cx1], mask[cy0:cy1, cx0:cx1]
    paper_rgb = [int(v) for v in np.median(sub[~subm].reshape(-1, 3), axis=0)] if (~subm).any() else None

    out = dict(file=Path(path).name, W=W, H=H, polarity=pol, otsu=thr, paper_luma=round(paper, 1),
               paper_rgb=paper_rgb, ink_rgb=ink_rgb, n_components=len(comps))
    m = NAME_RE.search(Path(path).name) or POSTER_RE.search(Path(path).name)
    if m:
        out.update(pair=f"{m['s1']}_{m['s2']}".upper(), edition=m["ed"].upper(),
                   device=(m.groupdict().get("dev") or "POSTER"))
    # halka adayi: kare-yakin, dusuk doluluk, buyuk
    ring = None
    for c in comps[:12]:
        if 0.75 <= c["aspect"] <= 1.35 and c["fill"] < 0.25 and c["w"] > w * 0.15:
            ring = c; break
    # sembol adayi: halka icinde en buyuk (halka disinda ise en buyuk ust yari)
    symbol = None
    if ring:
        inside = [c for c in comps if c is not ring and c["cx"] > ring["bbox"][0] and c["cx"] < ring["bbox"][2]
                  and c["cy"] > ring["bbox"][1] and c["cy"] < ring["bbox"][3]]
        if inside:
            symbol = max(inside, key=lambda c: c["area"])
    y_ref = ring["bbox"][3] if ring else (symbol["bbox"][3] if symbol else h * 0.5)
    rows = group_rows([c for c in comps if c is not ring], y_ref - 2)
    rows = [r for r in rows if (r["x1"] - r["x0"]) > w * 0.08 or r["n"] >= 3][:4]

    def pack(c):
        if not c:
            return None
        b = scale_box(c["bbox"], inv)
        return dict(bbox=b, w=b[2] - b[0], h=b[3] - b[1], fill=c["fill"], aspect=c["aspect"],
                    cx_pct=round(c["cx"] * inv / W * 100, 2), cy_pct=round(c["cy"] * inv / H * 100, 2),
                    w_pct=round((b[2] - b[0]) / W * 100, 2), h_pct=round((b[3] - b[1]) / H * 100, 2))
    out["ring"] = pack(ring)
    out["symbol"] = pack(symbol)
    out["text_rows"] = []
    for r in rows:
        b = scale_box([r["x0"], r["y0"], r["x1"], r["y1"]], inv)
        d = dict(bbox=b, n=r["n"], h=b[3] - b[1], cx_pct=round((b[0] + b[2]) / 2 / W * 100, 2),
                 cy_pct=round((b[1] + b[3]) / 2 / H * 100, 2), h_pct=round((b[3] - b[1]) / H * 100, 2),
                 w_pct=round((b[2] - b[0]) / W * 100, 2))
        if ring:
            rb = out["ring"]
            d["rel_ring"] = dict(dy_over_ring_h=round((d["cy_pct"] / 100 * H - (rb["bbox"][1] + rb["bbox"][3]) / 2) / rb["h"], 4),
                                 h_over_ring_h=round(d["h"] / rb["h"], 4),
                                 w_over_ring_w=round((b[2] - b[0]) / rb["w"], 4))
        out["text_rows"].append(d)
    # buyuk bilesen ozeti (ilk 8)
    out["top_components"] = [dict(bbox=scale_box(c["bbox"], inv), fill=c["fill"], aspect=c["aspect"],
                                  area_pct=round(c["area"] / (h * w) * 100, 3)) for c in comps[:8]]
    # Desktop yan bant
    if not is_poster and W > H:
        full = np.asarray(im, dtype=np.uint8)
        cols = mask.any(axis=0)
        xs = np.where(cols)[0]
        # murekkep icermeyen dis bolgeler
        if xs.size:
            l_ink, r_ink = int(xs.min() * inv), int((xs.max() + 1) * inv)
        else:
            l_ink, r_ink = 0, W
        # bant siniri: V1'deki "parlak bolge" yerine, satir-luma profilinin dis kenardan
        # ilk %15 degisim noktasi
        g = full.mean(axis=2)[int(H * .2):int(H * .8)].mean(axis=0)
        gmax = g.max(); gedge_l, gedge_r = g[:20].mean(), g[-20:].mean()
        def first_cross(profile, edge):
            thr_v = edge + 0.5 * (gmax - edge)
            idx = np.where(profile >= thr_v)[0]
            return int(idx[0]) if idx.size else 0
        lb = first_cross(g, gedge_l)
        rb = W - first_cross(g[::-1], gedge_r)
        out["bands"] = dict(left=dict(x1=lb, **(band_metrics(full, 0, lb, "left") or {})),
                            right=dict(x0=rb, **(band_metrics(full, rb, W, "right") or {})),
                            ink_extent=[l_ink, r_ink])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--posters", default="")
    ap.add_argument("--json", default="spec_v2.json")
    ap.add_argument("--md", default="spec_v2.md")
    a = ap.parse_args()
    rows = []
    for p in sorted(Path(a.dir).glob("*.jp*g")):
        r = analyze(p); rows.append(r)
        print(f"{r['file']}: {r['W']}x{r['H']} pol={r['polarity']} otsu={r['otsu']} ring={r['ring'] and r['ring']['bbox']} "
              f"sym={r['symbol'] and r['symbol']['bbox']} rows={[t['bbox'] for t in r['text_rows']]}", flush=True)
    if a.posters and Path(a.posters).is_dir():
        for p in sorted(Path(a.posters).glob("*.jp*g")):
            r = analyze(p, is_poster=True); r["kind"] = "poster"; rows.append(r)
            print(f"POSTER {r['file']}: ring={r['ring'] and r['ring']['bbox']} rows={[t['bbox'] for t in r['text_rows']]}", flush=True)
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    md = ["| dosya | pol | halka bbox (w%,cx%,cy%) | sembol bbox | satir1 (cy%, h%) | satir2 (cy%, h%) | murekkep | kagit |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rg = r["ring"]; sy = r["symbol"]; tr = r["text_rows"]
        def rowtxt(i):
            return f"{tr[i]['bbox']} ({tr[i]['cy_pct']}, {tr[i]['h_pct']})" if len(tr) > i else "-"
        md.append(f"| {r['file']} | {r['polarity']} | {rg['bbox'] if rg else '-'} ({rg['w_pct'] if rg else ''},{rg['cx_pct'] if rg else ''},{rg['cy_pct'] if rg else ''}) | "
                  f"{sy['bbox'] if sy else '-'} | {rowtxt(0)} | {rowtxt(1)} | {r['ink_rgb']} | {r['paper_rgb']} |")
    Path(a.md).write_text("\n".join(md) + "\n", encoding="utf-8")
    print("===JSON_BEGIN===\n" + json.dumps(rows) + "\n===JSON_END===")


if __name__ == "__main__":
    sys.exit(main())
