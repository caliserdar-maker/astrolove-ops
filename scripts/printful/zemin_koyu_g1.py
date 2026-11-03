#!/usr/bin/env python3
"""KOYU ZEMIN G1 (Serdar 3 Kas): RUBY / SAPPHIRE / EMERALD zemini duz radyal gradyan + ince tane (BEIGE / AGED_PAPYRUS G1 yontemi,
dal gecici/ornament-sembol-renk 2877495 zemin_acik/zemin_gradyan.py). Klasik yontem, AI yok; leke / bulut / desen yok.
1 Profil: mevcut 1264 px zeminde merkezden kenara 48 halka (r = hypot(x - N/2, y - N/2) / (N/2), 0..1), halka ORTANCA rengi (leke ortancayla silinir).
2 Uydurma: zemin_gradyan.py G1 formulu c = merkez (1 - t) + kenar t, t = clip(r, 0, 1)^us x guc (guc 1; kenar = r 1'deki renk).
  us 0.60-3.00 izgarasi (0.01 adim); her us icin merkez ve kenar RGB halka ortancalarina dogrusal en kucuk kareler (kapali cozum);
  secilen us = halkalarda (r <= 0.96; kesim r 0.941 + pay) en buyuk dE00'i en kucuk yapan. (deneme 1: Lab least_squares us 1.8'de kaldi, dE00 3.8)
3 Tane: zemin_gradyan.py tane(2.0) AYNEN (rng default_rng(7) ilk cekim = BEIGE_G1 ile ayni tane alani; GaussianBlur 1.0, std 2), uint8 ayni kirpma.
Kapilar: (a) leke: zeminden kendi radyal profili (halka ORTALAMASI, piksel r'sine dogrusal) cikarilir; kalan luma (deneme 2: ortanca profil
  kanali 0'a yakin zeminde kirpilan tanenin ortanca / ortalama farkini radyal kalinti olarak sayiyordu; ortanca surumu bilgi); olcu = 32 x 32 pencere
  ORTALAMALARININ std'si (desen / bulut, tane disi) ve pencere ICI std ortancasi (Merkez onerisi); r <= 0.94; yeni <= BEIGE G1 (her iki olcu).
  (b) renk sadakati: yeni zeminin halka ortancalari ile eski halka ortancalari arasinda her halkada (r <= 0.96) dE00 <= 2.
Kullanim: zemin_koyu_g1.py --kaynak DIR(kay7: *_1264.png) --cikti DIR"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter
from scipy.optimize import least_squares

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('motor', _d / 'ornament_motor.py'); mo = importlib.util.module_from_spec(_s); _s.loader.exec_module(mo)
de00 = mo.de00
N = 1264
yy, xx = np.mgrid[0:N, 0:N]
rr = np.hypot(xx - N / 2, yy - N / 2) / (N / 2)
BIN = np.linspace(0, 1.0, 49)
RMAX_FIT, RMAX_LEKE = 0.96, 0.94


def tane(rng, amp=2.0):                                             # zemin_gradyan.py ile ayni
    n = rng.normal(0, 1, (N, N)); im = Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    a = np.array(im).astype(float); return (a - a.mean()) / a.std() * amp


def yap(merkez, kenar, us, guc, tn):                                # zemin_gradyan.py yap() ile ayni (tane disaridan, ayni alan)
    t = np.clip(rr / 1.0, 0, 1) ** us * guc
    c = np.array(merkez, float) * (1 - t[..., None]) + np.array(kenar, float) * t[..., None]
    c += tn[..., None]
    return np.clip(c, 0, 255).astype(np.uint8)


def lab(x):
    return cv2.cvtColor((np.clip(np.asarray(x, np.float32), 0, 255).reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)


def profil(img):
    """48 halka: (r_orta, ortanca RGB, piksel)."""
    out = []
    for a, b in zip(BIN[:-1], BIN[1:]):
        m = (rr >= a) & (rr < b)
        out.append(((a + b) / 2, np.median(img[m].reshape(-1, 3), 0), int(m.sum())))
    return out


def luma(img):
    return img[..., :3].astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def leke(img, ortanca=False):
    L = luma(img); rc, Lp = [], []
    for a, b in zip(BIN[:-1], BIN[1:]):
        m_ = (rr >= a) & (rr < b); rc.append((a + b) / 2); Lp.append(float(np.median(L[m_]) if ortanca else L[m_].mean()))
    kal = L - np.interp(rr, rc, Lp).astype(np.float32)
    m = rr <= RMAX_LEKE
    k = 32
    mu = cv2.blur(kal, (k, k)); mu2 = cv2.blur(kal * kal, (k, k))
    std_ic = np.sqrt(np.maximum(mu2 - mu * mu, 0))
    # pencere ortalamalari: 32 px izgara (orneklenmis, ortusmez) disk icinde
    g = mu[k // 2::k, k // 2::k]; gm = m[k // 2::k, k // 2::k]
    return dict(pencere_ortalama_std=round(float(g[gm].std()), 3), pencere_ici_std_ortanca=round(float(np.median(std_ic[m])), 3),
                pencere_ortalama_maks_sapma=round(float(np.abs(g[gm]).max()), 2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--kaynak', required=True); ap.add_argument('--cikti', required=True)
    a = ap.parse_args(); K, O = Path(a.kaynak), Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    tn = tane(np.random.default_rng(7), 2.0)
    R = dict(yontem=__doc__.split('Kullanim')[0].strip(), referans={}, renk={})
    for ad in ('BEIGE', 'AGED_PAPYRUS'):                            # BEIGE G1 / AGED_PAPYRUS G1 (onayli, 2877495)
        im_ = np.asarray(Image.open(K / f'{ad}_1264.png').convert('RGB'))
        R['referans'][ad] = leke(im_); R['referans'][ad]['ortanca_profil_bilgi'] = leke(im_, True)['pencere_ortalama_std']
    esik = R['referans']['BEIGE']
    print('BEIGE G1 leke', esik, '| AGED_PAPYRUS G1', R['referans']['AGED_PAPYRUS'], flush=True)
    hepsi = True
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        eski = np.asarray(Image.open(K / f'{renk}_1264.png').convert('RGB'))
        assert eski.shape[:2] == (N, N)
        P = profil(eski)
        sec = [p for p in P if p[0] <= RMAX_FIT]
        r_ = np.array([p[0] for p in sec]); L_ = lab(np.array([p[1] for p in sec]))

        C = np.array([p[1] for p in sec], float)
        best = None
        for us_ in np.arange(0.60, 3.0001, 0.01):
            t = r_ ** us_; A = np.c_[1 - t, t]; sol = np.clip(np.linalg.lstsq(A, C, rcond=None)[0], 0, 255)
            d = max(de00(x, y) for x, y in zip(L_, lab(A @ sol)))
            if best is None or d < best[0]:
                best = (d, float(us_), sol)
        _, us, sol = best; M, Kc = sol[0], sol[1]
        yeni = yap(M, Kc, us, 1.0, tn)
        Image.fromarray(yeni).save(O / f'{renk}_G1_1264.png')
        Pn = profil(yeni)
        dE = [round(de00(lab(pe[1][None])[0], lab(pn[1][None])[0]), 3) for pe, pn in zip(P, Pn) if pe[0] <= RMAX_FIT]
        le, ln = leke(eski), leke(yeni)
        le['ortanca_profil_bilgi'] = leke(eski, True)['pencere_ortalama_std']; ln['ortanca_profil_bilgi'] = leke(yeni, True)['pencere_ortalama_std']
        k_leke = ln['pencere_ortalama_std'] <= esik['pencere_ortalama_std']   # inceleme: pencere ici std leke yakalamiyor (eski RUBY 1.10 < BEIGE 1.99), bilgi
        k_renk = max(dE) <= 2.0
        hepsi &= bool(k_leke and k_renk)
        R['renk'][renk] = dict(g1=dict(merkez=[round(float(v), 2) for v in M], kenar=[round(float(v), 2) for v in Kc], us=round(us, 4), guc=1.0,
                                       tane='zemin_gradyan.tane(2.0), default_rng(7) ilk cekim (BEIGE_G1 ile ayni tane ALANI); 0\'a yakin '
                                            'kanallarda uint8 kirpma: tane tek yonlu (inceleme: kirpilan piksel %28-54, tane std %20-37 dusuk)',
                                       kirpilan_piksel_yuzde={c: round(float((yeni[..., i][rr <= 0.941] == 0).mean() * 100), 1) for i, c in enumerate('RGB')}),
                               leke_eski=le, leke_yeni=ln, renk_dE00_halka_maks=max(dE), renk_dE00_halka_ortanca=round(float(np.median(dE)), 3),
                               renk_dE00_halka=dE, profil_eski=[[round(p[0], 4)] + [round(float(v), 1) for v in p[1]] for p in P],
                               profil_yeni=[[round(p[0], 4)] + [round(float(v), 1) for v in p[1]] for p in Pn],
                               kapi=dict(leke_le_beige=bool(k_leke), renk_dE00_le_2=bool(k_renk)),
                               bilgi_pencere_ici_std_le_beige=bool(ln['pencere_ici_std_ortanca'] <= esik['pencere_ici_std_ortanca']))
        print(renk, 'G1 merkez', [round(float(v), 1) for v in M], 'kenar', [round(float(v), 1) for v in Kc], 'us', round(us, 3),
              '| leke eski', le, 'yeni', ln, '| dE00 halka maks', max(dE), flush=True)
    R['kapi_zemin'] = bool(hepsi)
    (O / 'OLCUM_ZEMIN.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print('KAPI zemin', 'PASS' if hepsi else 'FAIL', flush=True)
    return 0 if hepsi else 1


if __name__ == '__main__':
    sys.exit(main())
