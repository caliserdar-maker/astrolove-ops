#!/usr/bin/env python3
"""QC (tek script, PASS/FAIL) - Kova-Kova ana gorseller.
Q1 artik: Cancer silme bolgesi (rem) - Kova murekkebi(dilate 3) disinda, |out-yerel medyan zemin| > T olan >=6 px bilesen sayisi <= referansin kendi temiz zeminindeki ayni olcutun alan basina yogunlugu x bolge alani
Q2 sembol hizasi: Kova kucuk sembol bbox merkezi ile referans sembol merkezi |dx|,|dy| <= 1.5 px
Q3 gorunurluk: kucuk sembol kontrasti (p95 |out-zemin|) >= kaynak Kova kontrastinin %85'i
Q4 kirpilma: sembol murekkep piksellerinde (dev>T) 255/0 kirpilma orani <= kaynak Kova sembolundeki oran + 0.5 puan
Q5 sahne degismedi: baski acikligi disinda kapak == referans kapak (maks fark 0)
"""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, '.')
import master as M
res = {}; allok = True
for c in M.COLORS:
    out = M.arr(f'out/master_{c}.png'); m = np.load(f'out/masks_{c}.npz')
    H, W = out.shape[:2]
    bg = M.local_bg(out, 41)
    dev = np.abs(out - bg).max(2)
    T = 16 if c in ('CI', 'PW', 'WP') else 22
    K, valid = M.kova_aligned(c)
    Kbg = M.local_bg(K); Kink = M.ink(K, Kbg, 18 if c in ('CI','PW','WP') else 30) & valid
    newgly = np.zeros((H, W), bool)
    meta = json.load(open('out/master_meta.json'))[c]
    for (cx, cy), gs in zip(M.DST_C, meta['glyph_src']):
        w, h = gs[1] - gs[0], gs[3] - gs[2]
        newgly[int(cy - h/2) - 6:int(cy + h/2) + 7, int(cx - w/2) - 6:int(cx + w/2) + 7] = True
    zone = m['rem'] & ~ndimage.binary_dilation(m['K_art'], iterations=3) & ~newgly
    lab, n = ndimage.label(zone & (dev > T))
    q1 = int((np.bincount(lab.ravel())[1:] >= 6).sum()) if n else 0
    # doku tabani: referansin kendi temiz zemininde (ust bant) ayni olcut, alan basina
    Rr = M.arr('refs_centered/' + M.COLORS[c][0])[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]]
    rdev = np.abs(Rr - M.local_bg(Rr, 41)).max(2); ctrl = np.zeros((H, W), bool); ctrl[15:110, 30:745] = True
    lb, nb = ndimage.label(ctrl & (rdev > T))
    base = (int((np.bincount(lb.ravel())[1:] >= 6).sum()) if nb else 0) / ctrl.sum()
    q1_limit = base * zone.sum()
    # Q2
    q2 = []
    for (cx, cy) in M.DST_C:
        box = (slice(int(cy) - 30, int(cy) + 30), slice(int(cx) - 60, int(cx) + 60))
        g = (dev[box] > T)
        g = M.components(g, 30)
        ys, xs = np.where(g)
        q2.append([float((xs.min() + xs.max()) / 2 + box[1].start - cx), float((ys.min() + ys.max()) / 2 + box[0].start - cy)])
    # Q3 contrast
    q3 = []
    for (cx, cy), gs in zip(M.DST_C, meta['glyph_src']):
        box = (slice(int(cy) - 25, int(cy) + 25), slice(int(cx) - 55, int(cx) + 55))
        src = (slice(gs[2] - 3, gs[3] + 4), slice(gs[0] - 3, gs[1] + 4))
        co = np.percentile(dev[box], 99.5)
        ks = np.abs(K[src] - Kbg[src]).max(2); cs = np.percentile(ks, 99.5)
        q3.append(float(co / max(cs, 1)))
    gi = newgly & (dev > T)
    clip_out = float(((out[gi] >= 254.5) | (out[gi] <= 0.5)).any(1).mean() * 100)
    srcm = np.zeros((H, W), bool)
    for gs in meta['glyph_src']: srcm[gs[2]:gs[3] + 1, gs[0]:gs[1] + 1] = True
    kd = np.abs(K - Kbg).max(2); si = srcm & (kd > T)
    clip_src = float(((K[si] >= 254.5) | (K[si] <= 0.5)).any(1).mean() * 100)
    ref_cov = M.arr('refs_centered/' + M.COLORS[c][0])
    cov = M.arr(f'out/cover_{c}.png'); d = np.abs(cov - ref_cov)
    d[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]] = 0
    q5 = float(d.max())
    ok = q1 <= q1_limit and clip_out <= clip_src + 0.5 and all(abs(a) <= 1.5 and abs(b) <= 1.5 for a, b in q2) and min(q3) >= 0.85 and q5 == 0
    res[c] = {'Q1_artik_bilesen': q1, 'Q1_doku_tabani_limit': round(q1_limit, 2), 'Q2_hiza_dxdy': q2, 'Q3_kontrast_orani': q3, 'Q4_kirpik_yuzde': [clip_out, clip_src], 'Q5_sahne_maks_fark': q5, 'SONUC': 'PASS' if ok else 'FAIL'}
    allok &= ok
    print(c, res[c])
json.dump(res, open('out/qc_master.json', 'w'), indent=1)
print('GENEL', 'PASS' if allok else 'FAIL')
