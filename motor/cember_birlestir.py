#!/usr/bin/env python3
"""CEMBER dilimlerinden tam halka dokusu (Serdar 4 Eki). Canva ciktilari gelince kosulur.

Girdi: GIRDI/DOKU_AI_CEMBER_{SAG,UST,SOL,UC}.png + .json (doku_ai_ek_sayfa_r.py) ve Canva ciktilari
       CANVA_CIKTI/DOKU_AI_CEMBER_<AD>_CANVA*.jpg (sonekli surum varsa --surum ile secilir).
Akis : her dilim doku_cila ile hizalanir + renk eslenir (sekil vektor maskeden, doku Canva'dan, hedef orijinal
       AQUARIUS_ARIES) -> dilim dokusu HALKA_24x36 cercevesine (json halka.sayfa_kaydirma) yerlestirilir ->
       her piksel halka acisina (u = (aci - sag_uc) mod 360) gore kendi diliminden doku alir; komsu dilimlerin
       ortusme araliginda yumusak gecis (yukseltilmis kosinus agirlik, toplam 1). Halka uclarinda (u = 0, u = son)
       rampa yok. Alfa = HALKA_24x36 (sekil degismez).
Cikti: CEMBER_DOKU_24x36.png (RGBA, halka kutusu kirpik) + .json (kutu, dilimler, ortusmeler, olcumler).

Kullanim: cember_birlestir.py --girdi GIRDI --canva CANVA_CIKTI --referans main_aquarius_aries_gold.png --cikti DIR
          [--surum _v2]
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_cila as dc                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SIRA = ['CEMBER_SAG', 'CEMBER_UST', 'CEMBER_SOL', 'CEMBER_UC']


def agirlik(u, u0, u1, ov0, ov1):
    """dilim agirligi: [u0, u0+ov0] ve [u1-ov1, u1] araliklarinda 0 -> 1 -> 0 yukseltilmis kosinus, disi 0."""
    w = ((u >= u0) & (u < u1)).astype(np.float32)
    if ov0 > 0:
        r = np.clip((u - u0) / ov0, 0, 1); w *= 0.5 - 0.5 * np.cos(np.pi * r)
    if ov1 > 0:
        r = np.clip((u1 - u) / ov1, 0, 1); w *= 0.5 - 0.5 * np.cos(np.pi * r)
    return w


def ortusmeler(js):
    """komsu dilimler arasi ortusme (derece): her dilim icin (sol ortusme, sag ortusme)."""
    u = [j['halka']['u_araligi'] for j in js]
    ov = []
    for i, (u0, u1) in enumerate(u):
        a = max(0, u[i - 1][1] - u0) if i > 0 else 0
        b = max(0, u1 - u[i + 1][0]) if i < len(u) - 1 else 0
        ov.append((a, b))
    return ov


def cila_dilim(girdi_png, girdi_json, canva_jpg, ref):
    rr, rA, ric = ref
    t, O, ic, h = dc.hizala(girdi_png, girdi_json, canva_jpg)
    E = dc.esleme_olc(t, ic, rr, ric)
    t1 = dc.esleme_uygula(t, E)
    return t1, O, h, dc.dagilim(t1, ic)


def birlestir(js, dokular, halka):
    """js: dilim json listesi (SIRA sirasi), dokular: dilim sayfa dokusu (H x W x 3, cila sonrasi), halka: HALKA alfa."""
    g = js[0]['halka']; cx, cy = g['merkez']; sag_uc = g['sag_uc_aci']
    ys, xs = np.nonzero(halka > 0)
    X0, Y0, X1, Y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
    u = (np.degrees(np.arctan2(-(yy - cy), xx - cx)) - sag_uc) % 360
    top = np.zeros((Y1 - Y0, X1 - X0, 3), np.float32); wt = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    for j, t, (ov0, ov1) in zip(js, dokular, ortusmeler(js)):
        dx, dy = j['halka']['sayfa_kaydirma']                         # halka = sayfa + kaydirma
        u0, u1 = j['halka']['u_araligi']
        w = agirlik(u, u0, u1, ov0, ov1)
        # dilim sayfasini halka cercevesine yerlestir (referans hucresi disinda, yalniz dilim kutusu)
        k = j['ogeler'][0]['kutu']
        T = np.zeros_like(top); M = np.zeros(wt.shape, bool)
        sx0, sy0 = k[0] + dx - X0, k[1] + dy - Y0
        a0, b0 = max(sx0, 0), max(sy0, 0)
        a1, b1 = min(sx0 + k[2] - k[0], X1 - X0), min(sy0 + k[3] - k[1], Y1 - Y0)
        T[b0:b1, a0:a1] = t[k[1] + b0 - sy0:k[1] + b1 - sy0, k[0] + a0 - sx0:k[0] + a1 - sx0]
        M[b0:b1, a0:a1] = True
        w = w * M
        top += T * w[..., None]; wt += w
    alfa = halka[Y0:Y1, X0:X1].astype(np.float32) / 255
    eksik = int(((alfa > 0) & (wt < 1e-3)).sum())
    rgb = top / np.maximum(wt, 1e-6)[..., None]
    return rgb, alfa, [int(X0), int(Y0), int(X1), int(Y1)], eksik


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--girdi', required=True)
    ap.add_argument('--canva', required=True)
    ap.add_argument('--referans', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--surum', default='')
    a = ap.parse_args()
    G, CV, C = Path(a.girdi), Path(a.canva), Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    ref = dc.referans(a.referans)
    js, dokular, olc = [], [], {}
    for ad in SIRA:
        j = json.loads((G / f'DOKU_AI_{ad}.json').read_text())
        t1, O, h, D = cila_dilim(G / f'DOKU_AI_{ad}.png', G / f'DOKU_AI_{ad}.json', CV / f'DOKU_AI_{ad}_CANVA{a.surum}.jpg', ref)
        js.append(j); dokular.append(t1)
        olc[ad] = {'hizalama': h, 'sonra': D}
        print(ad, 'ecc', h['ecc_cc'], 'kayma', h['kayma_px'], 'L', D['L_p10_50_90'], flush=True)
    halka = np.asarray(Image.open(KOK / 'varlik' / 'halka' / 'HALKA_24x36.png').convert('L'))
    rgb, alfa, kutu, eksik = birlestir(js, dokular, halka)
    if eksik:
        sys.exit(f'FAIL: {eksik} halka pikseli hicbir dilimden doku almadi')
    rgba = np.dstack([np.clip(np.round(rgb), 0, 255), np.round(alfa * 255)]).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(C / 'CEMBER_DOKU_24x36.png', optimize=True)
    (C / 'CEMBER_DOKU_24x36.json').write_text(json.dumps({
        'kutu_24x36': kutu, 'dilimler': SIRA, 'ortusme_derece': dict(zip(SIRA, ortusmeler(js))),
        'gecis': 'yukseltilmis kosinus, toplam agirlik 1', 'olcum': olc}, ensure_ascii=False, indent=1))
    print('CEMBER_DOKU_24x36.png', kutu)


if __name__ == '__main__':
    main()
