#!/usr/bin/env python3
"""Printful kupa mockup kalibrasyon olcumu (QC, PASS/FAIL).
Kullanim: python kalibrasyon_olc.py <boy 11|15> <mockup.png> [<mockup.png> ...]
Kalibrasyon dosyasi: kirmizi FRONT cizgisi x=560.7, mavi BACK x=2139.3, yesil CENTER x=1350; siyah cerceve
tasarimin 1050 px yuksekligi (15 oz dosyasinda y=45..1094, ust/alt 45 px beyaz).
Her mockup icin: govde yatay merkezi (alfa, orta bant en genis kosu), gorunen renkli cizgi, olcek s = cerceve yuksekligi / 1050,
govde merkezine dusen printfile x = cizgi_x + (merkez - cizgi_px) / s; cerceve ust/alt cizgisi ile govde
ust/alt kenari arasi bosluk (printfile px). Seffaf arka planli olmayan mockup atlanir."""
import json
import sys

import numpy as np
from PIL import Image

CIZGI = {"kirmizi": 560.7, "mavi": 2139.3, "yesil": 1350.0}


def renk_maske(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return {"kirmizi": (r > 140) & (g < 80) & (b < 80),
            "mavi": (b > 140) & (r < 80) & (g < 80),
            "yesil": (g > 90) & (r < 80) & (b < 80) & (g - b > 40)}


def olc(yol):
    im = Image.open(yol).convert("RGBA")
    a = np.asarray(im)
    al = a[..., 3] > 200
    if al.mean() > 0.9 or (~al).sum() == 0:
        return {"dosya": yol, "atla": "seffaf arka plan yok"}
    m = renk_maske(a)
    m = {k: v & al for k, v in m.items()}
    # dikey cizgi: en cok piksel iceren sutun (uzun dikey cizgi)
    adaylar = {}
    for k, v in m.items():
        sut = v.sum(0)
        if sut.max() >= 150:
            x = int(sut.argmax())
            xs = np.arange(max(0, x - 6), min(a.shape[1], x + 7))
            w = sut[xs].astype(float)
            adaylar[k] = (float((xs * w).sum() / w.sum()), int(sut.max()))
    if not adaylar:
        return {"dosya": yol, "atla": "dikey cizgi bulunamadi"}
    # siyah cerceve satirlari (koyu, yatay)
    koyu = (a[..., :3].max(-1) < 70) & al
    sat = koyu.sum(1)
    satirlar = np.where(sat > 0.25 * sat.max())[0]
    y_ust, y_alt = int(satirlar.min()), int(satirlar.max())
    s = (y_alt - y_ust) / 1050.0
    # govde kenarlari: cercevenin orta %40'lik bandinda her satirin EN GENIS alfa kosusu (kulp ayri kosu kalir)
    sol, sag = [], []
    h = y_alt - y_ust
    for y in range(int(y_ust + 0.3 * h), int(y_ust + 0.7 * h)):
        xs = np.where(al[y])[0]
        if not len(xs):
            continue
        br = np.where(np.diff(xs) > 1)[0]
        bas = np.r_[xs[0], xs[br + 1]]
        son = np.r_[xs[br], xs[-1]]
        i = int(np.argmax(son - bas))
        sol.append(bas[i])
        sag.append(son[i])
    merkez = (float(np.median(sol)) + float(np.median(sag))) / 2
    # merkeze en yakin cizgi
    k, (x_c, _) = min(adaylar.items(), key=lambda kv: abs(kv[1][0] - merkez))
    pf_x = CIZGI[k] + (merkez - x_c) / s
    # dikey: govde ust/alt (merkez sutunu, alfa) ile cerceve arasi
    kol = np.where(al[:, int(round(merkez))])[0]
    g_ust, g_alt = int(kol.min()), int(kol.max())
    # on agiz kenari: agiz elipsinin merkez satiri = govde tam genisligine ilk ulasilan satir; on kenar = 2*merkez - arka kenar
    gl, gr = float(np.median(sol)), float(np.median(sag))
    kulp_sag = (gr - merkez) > (merkez - gl) + 30
    y_el = g_ust
    for y in range(g_ust, y_ust):
        xs = np.where(al[y])[0]
        if len(xs) and (xs.min() <= gl + 2 if not kulp_sag else xs.max() >= gr - 2) and \
                (xs.max() >= gr - 2 if not kulp_sag else xs.min() <= gl + 2):
            y_el = y
            break
    on_agiz = 2 * y_el - g_ust
    return {"dosya": yol, "cizgi": k, "cizgi_px": round(x_c, 1), "govde_merkez_px": round(merkez, 1),
            "olcek": round(s, 4), "printfile_x_merkez": round(pf_x, 1), "cerceve_y": [y_ust, y_alt],
            "govde_y": [g_ust, g_alt], "ust_bosluk_pf": round((y_ust - g_ust) / s, 1),
            "alt_bosluk_pf": round((g_alt - y_alt) / s, 1), "on_agiz_y": on_agiz,
            "ust_bosluk_on_agiz_pf": round((y_ust - on_agiz) / s, 1)}


if __name__ == "__main__":
    boy = sys.argv[1]
    for p in sys.argv[2:]:
        print(json.dumps({"boy": boy, **olc(p)}, ensure_ascii=False))
