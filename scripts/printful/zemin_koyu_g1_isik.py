#!/usr/bin/env python3
"""KOYU ZEMIN G1 + UST ISIK (Serdar 3 Kas, deneme 3): lekesiz, merkez-kenar G1 aynen, eski zemindeki ustten gelen isik geri.
Model: c(x, y) = max(G1(r) x (1 + a S), 3) + tane
  G1(r) = merkez (1 - t) + kenar t, t = clip(r, 0, 1)^us (zemin_gradyan.py G1)
  S = -yn x r^p (yn = (y - N/2) / (N/2), ust -1 -> isik +; carpimsal, ton degismez); 3 = en koyu kanala +3 taban (Merkez onayi)
  tane = zemin_gradyan.tane(2.0), default_rng(7) ilk cekim (BEIGE_G1 ile ayni alan)
Hedef: eski zemin cv2.medianBlur(129 px) ile yumusatilir (leke silinir); 8 sektor x 18 halka (r <= 0.96) hucre ORTANCASI.
Uydurma: us (0.6-3.0), a (-0.2-0.8), p (0, 0.5, 1, 1.5, 2) izgarasi; her uclude merkez / kenar RGB dogrusal en kucuk kareler (kapali cozum);
  secim = hucrelerde en buyuk dE00 (vektorel CIEDE2000, renk_uyum.py ile ayni formul) en kucuk. Ince arama: kaba izgara etrafinda.
Kapilar: (1) her hucrede dE00(yeni hucre ortancasi, yumusatilmis eski hucre ortancasi) <= 2.0; asilirsa DUR (cikis 2, motor kosulmaz).
  (2) leke: kalan = luma - duzgun alan; duzgun alan = halka ortalamasi profili x (1 + b (-yn)), b her goruntuye en kucuk karelerle
  (BEIGE'e de AYNI yontem; esik = BEIGE G1 bu yontemle; 0.206 = onceki radyal yontem, bilgi); olcu = 32 px pencere ortalamalarinin std'si.
Kullanim: zemin_koyu_g1_isik.py --kaynak DIR --cikti DIR"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('g1', _d / 'zemin_koyu_g1.py'); g1 = importlib.util.module_from_spec(_s); _s.loader.exec_module(g1)
N, rr, lab, luma, tane = g1.N, g1.rr, g1.lab, g1.luma, g1.tane
yy, xx = np.mgrid[0:N, 0:N]
yn = (yy - N / 2) / (N / 2)
ang = (np.degrees(np.arctan2(yy - N / 2, xx - N / 2)) + 360) % 360
RB = np.linspace(0, 0.96, 19)
SEK = 8
TABAN = 3.0


def de00v(L1, L2):
    """CIEDE2000 vektorel (renk_uyum.py / ornament_motor.de00 ile ayni formul)."""
    L1, a1, b1 = L1[..., 0], L1[..., 1], L1[..., 2]; L2, a2, b2 = L2[..., 0], L2[..., 1], L2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)); dh = np.where(C1p * C2p == 0, 0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


# hucreler
HUC = []
for i in range(len(RB) - 1):
    for s in range(SEK):
        m = (rr >= RB[i]) & (rr < RB[i + 1]) & (ang >= s * 360 / SEK) & (ang < (s + 1) * 360 / SEK)
        HUC.append(m)
HR = np.array([float(rr[m].mean()) for m in HUC]); HY = np.array([float(yn[m].mean()) for m in HUC])


def hucre(img):
    return np.array([np.median(img[m].reshape(-1, 3), 0) for m in HUC], float)


def uydur(H):
    """H: hedef hucre RGB (yumusatilmis eski). Doner (en buyuk dE00, us, a, p, M, K)."""
    LH = lab(H)
    best = None

    def dene(us, a, p):
        t = np.clip(HR, 0, 1) ** us; f = 1 + a * (-HY) * HR ** p
        A = np.c_[f * (1 - t), f * t]
        sol = np.clip(np.linalg.lstsq(A, H, rcond=None)[0], 0, 255)
        C = np.maximum(A @ sol, TABAN)
        return float(de00v(LH, lab(C)).max()), sol
    for p in (0.0, 0.5, 1.0, 1.5, 2.0):
        for us in np.arange(0.6, 3.001, 0.05):
            for a in np.arange(-0.2, 0.801, 0.02):
                d, sol = dene(us, a, p)
                if best is None or d < best[0]:
                    best = (d, float(us), float(a), p, sol)
    d0, us0, a0, p0, _ = best
    for p in np.arange(max(0, p0 - 0.5), p0 + 0.501, 0.1):            # ince arama
        for us in np.arange(max(0.6, us0 - 0.06), us0 + 0.061, 0.01):
            for a in np.arange(a0 - 0.03, a0 + 0.031, 0.005):
                d, sol = dene(us, a, p)
                if d < best[0]:
                    best = (d, float(us), float(a), float(p), sol)
    return best


def uret(M, K, us, a, p, tn):
    t = np.clip(rr, 0, 1) ** us
    c = (M[None, None] * (1 - t[..., None]) + K[None, None] * t[..., None]) * (1 + a * (-yn) * rr ** p)[..., None]
    c = np.maximum(c, TABAN) + tn[..., None]
    return np.clip(c, 0, 255).astype(np.uint8)


RI = np.digitize(rr, g1.BIN) - 1; RI_OK = (RI >= 0) & (RI < 48); RC = (g1.BIN[:-1] + g1.BIN[1:]) / 2


def leke_isik(img):
    """kalan = luma - halka ortalamasi profili x (1 + b (-yn)); b en kucuk kareler (b izgarasi, kalan pencere ortalamasi std degil, piksel
    kalani karesi en kucuk); 32 px pencere ortalamalarinin std'si (r <= 0.94)."""
    L = luma(img); m94 = rr <= g1.RMAX_LEKE
    best = None
    for b in np.arange(-0.4, 0.4001, 0.005):
        f = 1 + b * (-yn)
        Lb = (L / f)[RI_OK]
        Lp = np.bincount(RI[RI_OK], Lb, minlength=48) / np.maximum(np.bincount(RI[RI_OK], minlength=48), 1)
        alan = np.interp(rr, RC, Lp).astype(np.float32) * f
        e = float(((L - alan)[m94] ** 2).mean())
        if best is None or e < best[0]:
            best = (e, float(b), alan)
    _, b, alan = best
    kal = L - alan; k = 32
    mu = cv2.blur(kal, (k, k)); gg = mu[k // 2::k, k // 2::k]; gm = m94[k // 2::k, k // 2::k]
    return dict(pencere_ortalama_std=round(float(gg[gm].std()), 3), b=round(b, 3), pencere_ortalama_maks_sapma=round(float(np.abs(gg[gm]).max()), 2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--kaynak', required=True); ap.add_argument('--cikti', required=True)
    a_ = ap.parse_args(); K_, O = Path(a_.kaynak), Path(a_.cikti); O.mkdir(parents=True, exist_ok=True)
    tn = tane(np.random.default_rng(7), 2.0)
    beige = np.asarray(Image.open(K_ / 'BEIGE_1264.png').convert('RGB'))
    esik = leke_isik(beige)
    R = dict(yontem=__doc__.split('Kullanim')[0].strip(), beige_g1_leke=esik, beige_g1_leke_onceki_radyal_bilgi=0.206, renk={})
    print('BEIGE G1 leke (isik yontemi)', esik, flush=True)
    hepsi = True
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        eski = np.asarray(Image.open(K_ / f'{renk}_1264.png').convert('RGB'))
        yum = cv2.medianBlur(eski, 129)
        H = hucre(yum)
        d, us, a, p, sol = uydur(H)
        M, Kc = sol[0], sol[1]
        yeni = uret(M, Kc, us, a, p, tn)
        Hn = hucre(yeni)
        dE = de00v(lab(H), lab(Hn))
        g1_eski = json.loads((O / 'OLCUM_ZEMIN.json').read_text())['renk'][renk]['g1'] if (O / 'OLCUM_ZEMIN.json').exists() else None
        ust = [i for i in range(len(HUC)) if HY[i] < -0.3]; alt = [i for i in range(len(HUC)) if HY[i] > 0.3]
        lk_e, lk_n = leke_isik(eski), leke_isik(yeni)
        ok_h = bool(dE.max() <= 2.0); ok_l = bool(lk_n['pencere_ortalama_std'] <= esik['pencere_ortalama_std'])
        R['renk'][renk] = dict(
            model=dict(merkez=[round(float(v), 2) for v in M], kenar=[round(float(v), 2) for v in Kc], us=round(us, 3), isik_a=round(a, 4), isik_p=round(p, 2),
                       taban=TABAN, tane='zemin_gradyan.tane(2.0), default_rng(7) ilk cekim'),
            uydurma_tahmini_maks_dE00=round(d, 3), hucre_dE00_maks=round(float(dE.max()), 3), hucre_dE00_ortanca=round(float(np.median(dE)), 3),
            hucre_dE00_p95=round(float(np.percentile(dE, 95)), 3), en_kotu_hucre=dict(r=round(float(HR[int(dE.argmax())]), 3), yn=round(float(HY[int(dE.argmax())]), 3),
                                                                                         eski=[round(float(v), 1) for v in H[int(dE.argmax())]], yeni=[round(float(v), 1) for v in Hn[int(dE.argmax())]]),
            ust_alt_luma=dict(eski_ust=round(float(luma(H[ust]).mean()), 2), eski_alt=round(float(luma(H[alt]).mean()), 2),
                              yeni_ust=round(float(luma(Hn[ust]).mean()), 2), yeni_alt=round(float(luma(Hn[alt]).mean()), 2)),
            leke_eski=lk_e, leke_yeni=lk_n,
            kirpilan_piksel_yuzde={c: round(float((yeni[..., i][rr <= 0.941] == 0).mean() * 100), 2) for i, c in enumerate('RGB')},
            kapi=dict(hucre_dE00_le_2=ok_h, leke_le_beige=ok_l), onceki_g1=g1_eski)
        if ok_h:
            Image.fromarray(yeni).save(O / f'{renk}_G1_1264.png')
        hepsi &= ok_h and ok_l
        x = R['renk'][renk]
        print(renk, 'us', x['model']['us'], 'a', x['model']['isik_a'], 'p', x['model']['isik_p'], '| hucre dE00 maks', x['hucre_dE00_maks'], 'p95', x['hucre_dE00_p95'],
              '| ust/alt eski', x['ust_alt_luma']['eski_ust'], x['ust_alt_luma']['eski_alt'], 'yeni', x['ust_alt_luma']['yeni_ust'], x['ust_alt_luma']['yeni_alt'],
              '| leke eski', lk_e['pencere_ortalama_std'], 'yeni', lk_n['pencere_ortalama_std'], '| kirpma', x['kirpilan_piksel_yuzde'], flush=True)
    R['kapi_zemin'] = bool(hepsi)
    (O / 'OLCUM_ZEMIN_ISIK.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print('KAPI zemin', 'PASS' if hepsi else 'FAIL (DUR)', flush=True)
    return 0 if hepsi else 2


if __name__ == '__main__':
    sys.exit(main())
