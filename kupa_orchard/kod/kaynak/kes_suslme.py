#!/usr/bin/env python3
"""Onayli kupa gorselinden (1254 kare, ChatGPT) on ve arka susleme katmanini keser, kupa golgesini duzler,
on gorunus tuvali olcegine (1 px = baski px) buyutur. Yeniden cizim YOK: piksel kaynagi onayli gorsel.
Kullanim: python3 -I kes_suslme.py <onayli_png> <geo_json> <cikti_onek>
geo_json: {"on": {"xc":..,"R":..,"ust":..,"alt":..}, "arka": {...},
           "yazi_on": [[x0,y0,x1,y1],...], "yazi_arka": [[...]], "s": olcek}
  ust/alt: susleme katmaninin dikey siniri (onayli gorsel px); bu aralik on gorunus y -496..+497'ye eslenir.
Cikti: <onek>_on.png, <onek>_arka.png (RGB, beyaz zemin, on gorunus olceginde) + <onek>_kes.json (yerlesim)
"""
import json, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage

t0 = time.time()
SRC, GEO, OUT = sys.argv[1:4]
g = json.load(open(GEO))
a = np.asarray(Image.open(SRC).convert('RGB')).astype(float)


def adim(m):
    print(f'[{time.time() - t0:5.1f}s] {m}', flush=True)


def kes(yuz, yazi):
    G = g[yuz]
    xc, R, ust, alt = G['xc'], G['R'], G['ust'], G['alt']
    x0, x1 = int(xc - R) - 2, int(xc + R) + 3
    y0, y1 = int(ust) - 12, int(alt) + 12
    c = a[y0:y1, x0:x1].copy()
    L = c.mean(-1)
    sat = c.max(-1) - c.min(-1)
    # kupa zemini (golge/parlama dahil): susleme olmayan piksellerden genis median
    on_aday = (sat > 22) | (L < 200)
    bgL = L.copy()
    bgL[ndimage.binary_dilation(on_aday, iterations=4)] = np.nan
    # nan doldurma: en yakin gecerli deger + genis yumusatma
    gecerli = ~np.isnan(bgL)
    idx = ndimage.distance_transform_edt(~gecerli, return_distances=False, return_indices=True)
    bgL = bgL[tuple(idx)]
    bgL = ndimage.gaussian_filter(bgL, 6)
    # susleme maskesi: zeminden belirgin fark veya renk
    fark = bgL - L
    m = (sat > 30) | (fark > 28)
    m = ndimage.binary_opening(m, iterations=1)
    # yazi/sembol kutularini cikar
    for (bx0, by0, bx1, by1) in yazi:
        m[max(0, by0 - y0):max(0, by1 - y0), max(0, bx0 - x0):max(0, bx1 - x0)] = False
    # kucuk kirintilari at, beyaz tac yapraklari icin delikleri doldur
    lab, n = ndimage.label(m)
    sz = ndimage.sum(np.ones_like(L), lab, range(1, n + 1))
    m = np.isin(lab, np.where(sz > 60)[0] + 1)
    m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2))
    # kupa kenarindaki parlama/kontur (dikey ince seritler) disarida kalsin
    m[:, :6] = False
    m[:, -6:] = False
    # kupa alt kenari (taban elipsi) ve masa disarida: alt(y) = taban_kenar + sarkma * sqrt(1-u^2) - pay
    yy, xx = np.mgrid[y0:y1, x0:x1]
    u = np.clip((xx - xc) / R, -1, 1)
    taban = G.get('taban_kenar', alt) + G.get('taban_sarkma', 0) * np.sqrt(1 - u * u) - 8
    m &= yy < taban
    # alt bant ve kenar seritlerinde dusuk renkli gri (kupa golgesi, masa yansimasi) elenir
    gri = sat < 30
    m &= ~(gri & ((yy > alt - 70) | (np.abs(u) > 0.9)))
    m &= ~((np.abs(u) > 0.97) & (sat < 60))
    m &= ~(np.abs(u) > 0.985)
    m &= ~((np.abs(u) > 0.85) & (yy > G.get('kenar_alt', alt - 22)))   # kenarda taban kavsi / masa
    m &= ~((np.abs(u) > 0.35) & (yy > alt + 1))                           # taban cizgisi kiriklari
    m &= ~((np.abs(u) > 0.55) & (yy > alt - 11))
    # yalniz renkli bilesenler (susleme her zaman renkli; gri golge/parlama elenir)
    lab, n = ndimage.label(m)
    renk_max = ndimage.maximum(sat, lab, range(1, n + 1))
    m = np.isin(lab, np.where(np.asarray(renk_max) > 45)[0] + 1)
    lab, n = ndimage.label(m)
    sz = ndimage.sum(np.ones_like(L), lab, range(1, n + 1))
    m = np.isin(lab, np.where(np.asarray(sz) > 80)[0] + 1)
    alfa = ndimage.gaussian_filter(m.astype(float), 0.8)
    # golge duzleme: renk / zemin parlakligi
    duz = np.clip(c / np.maximum(bgL, 1)[..., None] * 255.0, 0, 255)
    duz = duz * alfa[..., None] + 255.0 * (1 - alfa[..., None])
    return duz, (x0, y0), m


on, (ox, oy), m_on = kes('on', g['yazi_on'])
adim(f'on katman kesildi: {on.shape[1]}x{on.shape[0]} px, susleme orani %{m_on.mean() * 100:.1f}')
ar, (ax, ay), m_ar = kes('arka', g['yazi_arka'])
adim(f'arka katman kesildi: {ar.shape[1]}x{ar.shape[0]} px, susleme orani %{m_ar.mean() * 100:.1f}')

s = g['s']
for ad, img, (bx, by), yuz in (('on', on, (ox, oy), 'on'), ('arka', ar, (ax, ay), 'arka')):
    G = g[yuz]
    H, W = img.shape[:2]
    big = Image.fromarray(img.astype(np.uint8)).resize((round(W * s), round(H * s)), Image.LANCZOS)
    big.save(f'{OUT}_{ad}.png')
    # on gorunus koordinati: x = (px - xc) * s, y = (py - orta) * s; orta = (ust+alt)/2
    orta = (G['ust'] + G['alt']) / 2
    G['sol_ust_fv'] = [round((bx - G['xc']) * s, 1), round((by - orta) * s, 1)]
    G['orta'] = orta
    adim(f'{ad}: {big.width}x{big.height} on gorunus px, sol ust {G["sol_ust_fv"]}')
json.dump(g, open(f'{OUT}_kes.json', 'w'), indent=1)
adim('bitti')
