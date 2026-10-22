#!/usr/bin/env python3
"""Iz taramasi gorsel kaniti: her islenen bolge icin [referans | cikti | cikti - yerel zemin (x4, gri=0)].
Yerel zemin: kanal basina 41 px medyan. Cikti: paket/REVIEW/IZ_TARAMA/*.png"""
import json, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, '.')
import master as M, cards as C
OUT = M.ROOT / 'paket/REVIEW/IZ_TARAMA'; OUT.mkdir(parents=True, exist_ok=True)

def amp(O):
    bg = np.stack([ndimage.median_filter(O[..., i], size=41) for i in range(3)], 2)
    return np.clip(128 + (O - bg) * 4, 0, 255)

def save(name, R, O, zoom=1):
    t = np.concatenate([R, O, amp(O)], 1)
    if zoom > 1: t = np.kron(t, np.ones((zoom, zoom, 1)))
    Image.fromarray(np.clip(np.rint(t), 0, 255).astype(np.uint8)).save(OUT / f'{name}.png')

jobs = []
for c in M.COLORS:
    jobs.append(('kapak_' + c, lambda c=c: (M.arr('refs_centered/' + M.COLORS[c][0])[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]],
                                             M.arr(f'out/cover_{c}.png')[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]], 1)))
L = json.load(open('out/cards_log_2_3_4_5_6_7_8_9_10.json'))
for n in ('5', '6', '7', '9'):
    for p in L[n]['poster']:
        def f(n=n, p=p):
            x0, y0, x1, y1 = p['rect']
            return M.arr(C.REF / f'{C.CARDS[int(n)]}.jpg')[y0:y1, x0:x1], M.arr(f'out/card{int(n):02d}.png')[y0:y1, x0:x1], 2 if n == '5' else 1
        jobs.append((f'kart{int(n):02d}_{p["color"]}', f))
for n in ('2', '3'):
    p = L[n]['glyph_panel'][0]
    def f(n=n, p=p):
        x0, y0, x1, y1 = p['rect']; ox0, oy0, ox1, oy1 = p.get('rect_out', p['rect']); H = y1 - y0
        return (M.arr(C.REF / f'{C.CARDS[int(n)]}.jpg')[y0:y0 + int(0.45 * H), x0:x1],
                M.arr(f'out/card{int(n):02d}.png')[oy0:oy0 + int(0.45 * H), ox0:ox1], 1)
    jobs.append((f'kart{int(n):02d}_panel', f))
jobs.append(('kart04_panel', lambda: (M.arr(C.REF / f'{C.CARDS[4]}.jpg')[480:2011, 1320:2831], M.arr('out/card04.png')[480:2011, 1320:2831], 1)))
t0 = time.time()
for i, (name, f) in enumerate(jobs, 1):
    R, O, z = f(); save(name, R, O, z)
    el = time.time() - t0
    print(f'[{i}/{len(jobs)}] %{100 * i / len(jobs):.0f} gecen {el:.0f}s kalan ~{el / i * (len(jobs) - i):.0f}s {name}', flush=True)
