#!/usr/bin/env python3
"""ANA SEMBOLUN GERCEK MALZEMESINI AKTAR (Serdar 4 Eki): parametrik doku modeli YOK.

Kaynak (envanter, docs/MOTOR_ENVANTER.md #9): altin efekt DOSYA, Canva efekti degil; ana sembol Canva'dan altin olarak
disa aktarilmis PNG (main_symbols/<a>_<b>_gold.png). Ayri dolgu gorseli / kabartma ayari yok -> doku ana sembolun
kendi piksellerinden alinir.

Yontem (rehberli PatchMatch, yama oylamasi):
  1) kaynak: sayfadaki ana sembol pikselleri; zemin ayrilir (on carpim geri alinir), kapsama = fark / ortanca.
  2) olcek: kaynak, cizgi yaricapi hedefinkine esit olacak sekilde kucultulur (kabartma ve tane cizgiyle orantili).
  3) her hedef pikseli icin, rehberi (goreli derinlik t + kenar yonu) en iyi uyan 7x7 kaynak yamasi aranir (PatchMatch:
     yayilim + rastgele arama, renk tutarliligi); cikti = ortusen kaynak yamalarinin oylamasi (yalniz kaynak pikselleri).
  4) hedef kendi kapsamasiyla zemine bindirilir.

Kullanim (prototip): doku_aktar.py --sayfa MOTOR.png --zemin ZEMIN.png --kutular _oge_kutulari.json --hedef isim1
                     --cikti YENI.png
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import tek_doku as tdk                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
LUMA = tdk.LUMA
W_T, W_N = 1.0, 0.35          # ozellik agirliklari: goreli derinlik, normal (cos, sin)
KOH = 0.03                    # koherans tercihi (ozellik uzakligi birimi)
KNN = 12


def kapsama(rgb, zem):
    D = (rgb - zem) @ LUMA
    return np.clip(D / max(float(np.median(D[D > 40])), 1.0), 0, 1)


def yaricap(A):
    m = (A > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    s = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt > 1)
    return float(np.median(dt[s]))


def ozellik(A):
    """goreli derinlik t (kenar 0, orta 1), disa normal (cos, sin) ve guven; A > 0.5 disi t = 0."""
    pen = int(round(61 * 4800 / 4800)) | 1
    t = tdk.boru_t(A, pen)
    m8 = (A > 0.5).astype(np.uint8)
    din = cv2.distanceTransform(m8, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform(1 - m8, cv2.DIST_L2, 5)
    sd = cv2.GaussianBlur(din - dout, (0, 0), 1.0)                    # isaretli uzaklik: normal kenarin iki yaninda surekli
    gx = cv2.Sobel(sd, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(sd, cv2.CV_32F, 0, 1, ksize=3) / 8
    g = np.hypot(gx, gy)
    nx, ny = -gx / np.maximum(g, 1e-6), -gy / np.maximum(g, 1e-6)
    w = np.clip(g / 0.3, 0, 1)
    return t, nx * w, ny * w


def kaynak_hazirla(rgb, zem, A, olcek):
    """on carpim geri alinmis renk + kapsama, olcekli (INTER_AREA, on carpimli)."""
    un = (rgb - zem * (1 - A[..., None])) / np.maximum(A[..., None], 0.3)
    pre = un * A[..., None]
    sz = (max(1, int(round(A.shape[1] * olcek))), max(1, int(round(A.shape[0] * olcek))))
    pre_s = cv2.resize(pre, sz, interpolation=cv2.INTER_AREA)
    A_s = cv2.resize(A, sz, interpolation=cv2.INTER_AREA)
    un_s = pre_s / np.maximum(A_s[..., None], 1e-3)
    return np.clip(un_s, 0, 255), A_s


YAMA = 7                      # PatchMatch yama boyu (olcekli kaynak pikseli)
TUR = 6                       # PatchMatch turu
W_G, W_C = 1.0, 0.0006        # enerji: rehber (t, normal) + renk tutarliligi (0-255 kare fark)


def _yama_enerji(Gt, Gs, Ct, Cs, T, Q, off):
    """T (N,2) hedef, Q (N,2) kaynak; yama ofsetleri uzerinden rehber + renk kare farki toplami."""
    E = np.zeros(len(T), np.float32)
    Ht, Wt = Gt.shape[:2]; Hs, Ws = Gs.shape[:2]
    for dy, dx in off:
        ty = np.clip(T[:, 0] + dy, 0, Ht - 1); tx = np.clip(T[:, 1] + dx, 0, Wt - 1)
        sy = np.clip(Q[:, 0] + dy, 0, Hs - 1); sx = np.clip(Q[:, 1] + dx, 0, Ws - 1)
        E += W_G * ((Gt[ty, tx] - Gs[sy, sx]) ** 2).sum(1)
        if Ct is not None:
            E += W_C * ((Ct[ty, tx] - Cs[sy, sx]) ** 2).sum(1)
    return E


def aktar(src_rgb, src_A, hedef_A, tohum=1):
    """Rehberli PatchMatch (Image Analogies / PatchMatch): hedef rengi = kaynak yamalarinin oylamasi. Rehber: goreli
    derinlik t ve disa normal (kenar yonu); renk tutarliligi: bir onceki turun ciktisi. Yalniz kaynak pikselleri kopyalanir."""
    rng = np.random.default_rng(tohum)
    ts, nxs, nys = ozellik(src_A)
    Gs = np.stack([ts * W_T, nxs * W_N, nys * W_N], -1).astype(np.float32)
    # kaynak disi (kapsama < 0.5) renkler gecersiz: en yakin ic piksel rengiyle doldur
    ic = (src_A >= 0.5).astype(np.uint8)
    Cs = src_rgb.copy()
    _, lab = cv2.distanceTransformWithLabels(1 - ic, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    iy, ix = np.nonzero(ic)
    lut = np.zeros(lab.max() + 1, np.int64)
    zy, zx = np.nonzero(ic == 1)
    lut[lab[zy, zx]] = np.arange(zy.size)
    Cs = src_rgb[zy[lut[lab]], zx[lut[lab]]]
    gecerli = (src_A >= 0.6)
    gy_, gx_ = np.nonzero(gecerli)
    tt, nxt, nyt = ozellik(hedef_A)
    Gt = np.stack([tt * W_T, nxt * W_N, nyt * W_N], -1).astype(np.float32)
    hm = cv2.dilate((hedef_A > 0.01).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ty, tx = np.nonzero(hm)
    T = np.stack([ty, tx], 1)
    idx_t = -np.ones(hedef_A.shape, np.int64); idx_t[ty, tx] = np.arange(len(T))
    # baslangic: rehbere en yakin gecerli kaynak (kd-agac)
    agac = cKDTree(Gs[gecerli])
    _, nn = agac.query(Gt[ty, tx], k=4)
    pick = nn[np.arange(len(T)), rng.integers(0, 4, len(T))]
    Q = np.stack([gy_[pick], gx_[pick]], 1)
    r = YAMA // 2
    off = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
    Hs, Ws = Gs.shape[:2]
    Ct = None
    for tur in range(TUR):
        E = _yama_enerji(Gt, Gs, Ct, Cs, T, Q, off)
        for yon in ((0, -1), (-1, 0), (0, 1), (1, 0)) if tur % 2 == 0 else ((0, 1), (1, 0), (0, -1), (-1, 0)):
            ny_, nx_ = T[:, 0] + yon[0], T[:, 1] + yon[1]
            ok = (ny_ >= 0) & (ny_ < hedef_A.shape[0]) & (nx_ >= 0) & (nx_ < hedef_A.shape[1])
            j = np.where(ok, idx_t[np.clip(ny_, 0, hedef_A.shape[0] - 1), np.clip(nx_, 0, hedef_A.shape[1] - 1)], -1)
            v = j >= 0
            Qc = Q.copy()
            Qc[v] = Q[j[v]] - np.asarray(yon)
            Qc[:, 0] = np.clip(Qc[:, 0], 0, Hs - 1); Qc[:, 1] = np.clip(Qc[:, 1], 0, Ws - 1)
            v &= gecerli[Qc[:, 0], Qc[:, 1]]
            Ec = _yama_enerji(Gt, Gs, Ct, Cs, T, Qc, off)
            b = v & (Ec < E)
            Q[b] = Qc[b]; E[b] = Ec[b]
        rad = max(Hs, Ws) / 2
        while rad >= 1:
            Qc = Q + rng.integers(-int(rad), int(rad) + 1, Q.shape)
            Qc[:, 0] = np.clip(Qc[:, 0], 0, Hs - 1); Qc[:, 1] = np.clip(Qc[:, 1], 0, Ws - 1)
            v = gecerli[Qc[:, 0], Qc[:, 1]]
            Ec = _yama_enerji(Gt, Gs, Ct, Cs, T, Qc, off)
            b = v & (Ec < E)
            Q[b] = Qc[b]; E[b] = Ec[b]
            rad /= 2
        # oylama: her hedef pikseli, onu kapsayan yamalarin kaynak renklerinin ortalamasi
        acc = np.zeros(hedef_A.shape + (3,), np.float32); n = np.zeros(hedef_A.shape, np.float32)
        for dy, dx in off:
            yy = np.clip(T[:, 0] + dy, 0, hedef_A.shape[0] - 1); xx = np.clip(T[:, 1] + dx, 0, hedef_A.shape[1] - 1)
            sy = np.clip(Q[:, 0] + dy, 0, Hs - 1); sx = np.clip(Q[:, 1] + dx, 0, Ws - 1)
            np.add.at(acc, (yy, xx), Cs[sy, sx]); np.add.at(n, (yy, xx), 1)
        Ct = acc / np.maximum(n[..., None], 1)
    return Ct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sayfa', required=True)
    ap.add_argument('--zemin', required=True)
    ap.add_argument('--kutular', required=True)
    ap.add_argument('--hedef', default='isim1')
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    P = np.asarray(Image.open(a.sayfa).convert('RGB'), np.float32)
    Z = np.asarray(Image.open(a.zemin).convert('RGB'), np.float32)
    K = json.loads(Path(a.kutular).read_text())
    y0, y1, x0, x1 = K['buyuk_sembol']
    As = kapsama(P[y0:y1, x0:x1], Z[y0:y1, x0:x1])
    h0, h1, g0, g1 = K[a.hedef]
    pad = 8
    h0, h1, g0, g1 = h0 - pad, h1 + pad, g0 - pad, g1 + pad
    At = kapsama(P[h0:h1, g0:g1], Z[h0:h1, g0:g1])
    olcek = yaricap(At) / yaricap(As)
    src, As_s = kaynak_hazirla(P[y0:y1, x0:x1], Z[y0:y1, x0:x1], As, olcek)
    renk = aktar(src, As_s, At)
    m = At > 0.01
    zb = Z[h0:h1, g0:g1]
    yeni = zb * (1 - At[..., None]) + renk * At[..., None]
    out = P.copy()
    out[h0:h1, g0:g1] = yeni
    Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)).save(a.cikti)
    print(json.dumps({'olcek': round(olcek, 3), 'kaynak_yaricap': round(yaricap(As), 1),
                      'hedef_yaricap': round(yaricap(At), 1), 'hedef_px': int(m.sum())}))


if __name__ == '__main__':
    main()
