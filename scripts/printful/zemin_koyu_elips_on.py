#!/usr/bin/env python3
"""KOYU_G1 ON OLCUM (Merkez 3 Kas, A; deneme sayilmaz, motor kosmaz): serbest yonlu, kaydirilmis merkezli ELIPTIK isik modeli.
Model: c(x, y) = max(f(x, y) x G1(rho), 3) + tane
  rho = eliptik yaricap: merkez (cx, cy) kaydirilmis, eksenler theta kadar donuk, en / boy orani e^q (alan korunur: sx = e^(q/2), sy = e^(-q/2))
  G1(rho) = merkez (1 - t) + kenar t, t = clip(rho, 0, 1)^us
  f = 1 + a (cos phi xn + sin phi yn): serbest yonlu dogrusal isik
  3 = en koyu kanala +3 taban; tane = zemin_gradyan.tane(2.0), default_rng(7) ilk cekim (BEIGE_G1 ile ayni alan)
Hedef: eski zemin medianBlur 129 px; 8 sektor x 18 halka (r <= 0.96) hucre ortancasi (zemin_koyu_g1_isik ile ayni hucreler).
Uydurma: geometri (cx, cy, q, theta, us, a, phi) Nelder-Mead, 24 baslangic; merkez / kenar RGB her adimda dogrusal en kucuk kareler;
  amac = yumusak maksimum (sum dE00^8)^(1/8) hucre merkezlerinde; KESIN deger = uretilen 1264 px goruntunun hucre ortancalari.
Leke: duzgun alan AYNI aile (eliptik rho profili x dogrusal isik), her goruntuye ayri uydurulur (BEIGE dahil); olcu = 32 px pencere
  ortalamalarinin std'si (r <= 0.94). Esik = BEIGE G1 bu yontemle.
Gorsel: yalniz zemin (ogesiz), 7.6 cm daire (954 px baski dosyasi olcegi, ornament onizleme), 3 renk x ESKI | DENEME 2 | DENEME 3 | ELIPTIK.
Kullanim: zemin_koyu_elips_on.py --kaynak DIR --g1 DIR(ORNAMENT_KOYU_G1) --cikti DIR --font TTF"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFont
from scipy.optimize import minimize

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('zi', _d / 'zemin_koyu_g1_isik.py'); zi = importlib.util.module_from_spec(_s); _s.loader.exec_module(zi)
_s = importlib.util.spec_from_file_location('son', _d / 'ornament_son.py'); son = importlib.util.module_from_spec(_s); _s.loader.exec_module(son)
g1 = zi.g1
N, rr, lab, luma = g1.N, g1.rr, g1.lab, g1.luma
yy, xx = np.mgrid[0:N, 0:N]
xn = (xx - N / 2) / (N / 2); yn = (yy - N / 2) / (N / 2)
HX = np.array([float(xn[m].mean()) for m in zi.HUC]); HY = zi.HY
TABAN = 3.0


def rho(g, X, Y):
    cx, cy, q, th = g[0], g[1], g[2], g[3]
    c, s = np.cos(th), np.sin(th)
    u, v = (X - cx) * c + (Y - cy) * s, -(X - cx) * s + (Y - cy) * c
    return np.hypot(u / np.exp(q / 2), v / np.exp(-q / 2))


def isik(g, X, Y):
    return 1 + g[5] * (np.cos(g[6]) * X + np.sin(g[6]) * Y)


def cozum(g, H, X, Y):
    t = np.clip(rho(g, X, Y), 0, 1) ** max(g[4], 0.2); f = isik(g, X, Y)
    A = np.c_[f * (1 - t), f * t]
    sol = np.clip(np.linalg.lstsq(A, H, rcond=None)[0], 0, 255)
    return np.maximum(A @ sol, TABAN), sol


def uydur(H, rng):
    LH = lab(H)

    def amac(g):
        C, _ = cozum(g, H, HX, HY)
        return float((zi.de00v(LH, lab(C)) ** 8).sum() ** (1 / 8))
    best = None
    bas = [np.array([0, 0, 0, 0, 1.3, 0.1, -np.pi / 2])] + [np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.25, 0.1), rng.uniform(-0.5, 0.5),
                                                                       rng.uniform(0, np.pi), rng.uniform(0.8, 2.0), rng.uniform(0, 0.4),
                                                                       rng.uniform(-np.pi, np.pi)]) for _ in range(23)]
    for x0 in bas:
        r = minimize(amac, x0, method='Nelder-Mead', options=dict(maxiter=3000, xatol=1e-4, fatol=1e-4))
        if best is None or r.fun < best.fun:
            best = r
    g = best.x
    _, sol = cozum(g, H, HX, HY)
    return g, sol, float(best.fun)


def uret(g, sol, tn):
    t = np.clip(rho(g, xn, yn), 0, 1) ** max(g[4], 0.2); f = isik(g, xn, yn)
    c = (sol[0][None, None] * (1 - t[..., None]) + sol[1][None, None] * t[..., None]) * f[..., None]
    c = np.maximum(c, TABAN) + tn[..., None]
    return np.clip(c, 0, 255).astype(np.uint8)


ALT = (slice(None, None, 4), slice(None, None, 4))


def leke_elips(img):
    """duzgun alan = eliptik rho halka ortalamasi profili x dogrusal isik; geometri Nelder-Mead (4 px seyreltilmis, r <= 0.94)."""
    L = luma(img); m94 = rr <= g1.RMAX_LEKE
    Ls, ms, Xs, Ys = L[ALT], m94[ALT], xn[ALT], yn[ALT]
    BIN = np.linspace(0, 1.3, 53)

    def alan(g, LL, X, Y):
        f = 1 + g[4] * (np.cos(g[5]) * X + np.sin(g[5]) * Y)
        rh = rho(np.r_[g[:4]], X, Y); ri = np.clip(np.digitize(rh, BIN) - 1, 0, len(BIN) - 2)
        ok = rh <= 1.25
        prof = np.bincount(ri[ok], (LL / f)[ok], minlength=len(BIN) - 1) / np.maximum(np.bincount(ri[ok], minlength=len(BIN) - 1), 1)
        rc = (BIN[:-1] + BIN[1:]) / 2
        return np.interp(rh, rc, prof) * f

    def amac(g):
        return float(((Ls - alan(g, Ls, Xs, Ys))[ms] ** 2).mean())
    best = None
    for x0 in (np.zeros(6), np.array([0, -0.1, 0.2, 1.57, 0.1, -1.57]), np.array([0, -0.1, -0.2, 0, 0.1, -1.57])):
        r = minimize(amac, x0, method='Nelder-Mead', options=dict(maxiter=1500, xatol=1e-4, fatol=1e-5))
        if best is None or r.fun < best.fun:
            best = r
    kal = L - alan(best.x, L, xn, yn); k = 32
    mu = cv2.blur(kal.astype(np.float32), (k, k)); gg = mu[k // 2::k, k // 2::k]; gm = m94[k // 2::k, k // 2::k]
    return dict(pencere_ortalama_std=round(float(gg[gm].std()), 3), geometri=[round(float(v), 4) for v in best.x])


def main():
    ap = argparse.ArgumentParser()
    for k in ('kaynak', 'g1', 'cikti', 'font'): ap.add_argument('--' + k, required=True)
    a_ = ap.parse_args(); K_, G1D, O = Path(a_.kaynak), Path(a_.g1), Path(a_.cikti); O.mkdir(parents=True, exist_ok=True)
    tn = g1.tane(np.random.default_rng(7), 2.0)
    rng = np.random.default_rng(1)
    D3 = json.loads((G1D / 'OLCUM_ZEMIN_ISIK.json').read_text())['renk']
    beige = np.asarray(Image.open(K_ / 'BEIGE_1264.png').convert('RGB'))
    esik = leke_elips(beige)
    R = dict(yontem=__doc__.split('Kullanim')[0].strip(), beige_g1_leke_elips=esik, renk={})
    print('BEIGE G1 leke (eliptik alan)', esik, flush=True)
    satirlar = []
    font = ImageFont.truetype(a_.font, 26)
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        eski = np.asarray(Image.open(K_ / f'{renk}_1264.png').convert('RGB'))
        H = zi.hucre(cv2.medianBlur(eski, 129))
        g, sol, yum = uydur(H, rng)
        yeni = uret(g, sol, tn)
        Image.fromarray(yeni).save(O / f'{renk}_ELIPS_1264.png')
        d3 = D3[renk]['model']
        isikli = zi.uret(np.array(d3['merkez']), np.array(d3['kenar']), d3['us'], d3['isik_a'], d3['isik_p'], tn)   # deneme 3 parametreleri
        Image.fromarray(isikli).save(O / f'{renk}_DENEME3_ISIK_1264.png')
        d2 = np.asarray(Image.open(G1D / f'{renk}_G1_1264.png').convert('RGB'))
        olc = {}
        for ad, im in (('deneme2_radyal', d2), ('deneme3_duseyisik', isikli), ('eliptik', yeni)):
            dE = zi.de00v(lab(H), lab(zi.hucre(im)))
            olc[ad] = dict(hucre_dE00_maks=round(float(dE.max()), 3), p95=round(float(np.percentile(dE, 95)), 3), ortanca=round(float(np.median(dE)), 3),
                           hucre_gt2=int((dE > 2).sum()), leke=leke_elips(im)['pencere_ortalama_std'])
        lk_e = leke_elips(eski)
        R['renk'][renk] = dict(eliptik_model=dict(cx=round(float(g[0]), 4), cy=round(float(g[1]), 4), en_boy=round(float(np.exp(g[2])), 4),
                                                  theta_derece=round(float(np.degrees(g[3])) % 180, 2), us=round(float(g[4]), 4), isik_a=round(float(g[5]), 4),
                                                  isik_yon_derece=round(float(np.degrees(g[6])) % 360, 2), merkez=[round(float(v), 2) for v in sol[0]],
                                                  kenar=[round(float(v), 2) for v in sol[1]], taban=TABAN, yumusak_maks_amac=round(yum, 3)),
                               olcum=olc, leke_eski=lk_e,
                               kirpilan_piksel_yuzde_eliptik={c: round(float((yeni[..., i][rr <= 0.941] == 0).mean() * 100), 2) for i, c in enumerate('RGB')})
        print(renk, json.dumps(olc), '| leke eski', lk_e['pencere_ortalama_std'], '| model', json.dumps(R['renk'][renk]['eliptik_model']), flush=True)
        # gorsel: yalniz zemin, 954 olcegi, 7.6 cm daire
        dosyalar = [('ESKI (Canva AI, lekeli)', eski), ('DENEME 2 (yalniz radyal)', d2), ('DENEME 3 (duseyde isik)', isikli), ('ELIPTIK (serbest yon)', yeni)]
        rgbler = [np.clip(cv2.resize(im.astype(np.float32), (954, 954), interpolation=cv2.INTER_AREA), 0, 255).round().astype(np.uint8)
                  for _, im in dosyalar]                                    # o1.zemin_canva ile ayni kucultme
        et = [f'{renk}: {ad}' + (f'\nhucre dE00 maks {olc[k]["hucre_dE00_maks"]}, p95 {olc[k]["p95"]}' if k else f'\nleke {lk_e["pencere_ortalama_std"]}')
              for (ad, _), k in zip(dosyalar, (None, 'deneme2_radyal', 'deneme3_duseyisik', 'eliptik'))]
        satirlar.append(son.onizleme_etiketli(rgbler, et, font, h_et=90))
    W = max(s.width for s in satirlar)
    u = Image.new('RGB', (W, sum(s.height + 20 for s in satirlar)), 'white'); y = 0
    for s in satirlar:
        u.paste(s, (0, y)); y += s.height + 20
    u.save(O / 'ZEMIN_KARSILASTIRMA_76mm.png', dpi=(300, 300))
    (O / 'OLCUM_ELIPS.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
