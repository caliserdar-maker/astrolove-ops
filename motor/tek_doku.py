"""TEK DOKU BUTUNLUGU + yazi cevresi yildiz temizligi (Serdar 3 Eki, altin edisyonlar).

Referans = o posterin ANA SEMBOLU (sayfaya basilmis hali; orijinal poster degil). Olculenler:
  egri     : luma -> RGB (ana sembol cekirdek piksellerinde 4 luma'lik kutularda ortanca renk, kenarlar sabit)
  Lmed     : ana sembol cekirdek luma ortancasi (parlaklik)
  doku     : boru profili L(t) (t = goreli kenar uzakligi; kenar koyu, govde parlak) x kabartma (1 + a dh/dy +
             b dh/dx, h = sigma ile bulanik alfa; kilitli wp_bakir kabartma bicimi). Olculdu (3 Eki): profil 106-186
             luma, kalan ile dikey egim korelasyonu 0.71 (CANCER_LIBRA)
Uygulama (her oge kendi alfasi ile, kabartma tek kez):
  dokulu ogeler (kucuk semboller, sonsuz): kendi luma dokusu
  duz ogeler (isimler, tagline, cember)  : luma = profil(t) x kabartma
  hepsinde renk = egri(luma x k); k, qc olcumuyle (QC olcegi cekirdek ortancasi) Lmed olacak sekilde (3 tur)
Yildiz: yazi kutusu + pay icinde plate'in parlak noktalari (yerel 31 px medyandan > YILDIZ_T luma, kucuk bilesen)
yerel medyanla doldurulur (yalniz bu pay icinde).
"""
import cv2
import numpy as np

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
YILDIZ_T = 15.0          # luma; plate yerel ortancasindan parlaklik (olculen: gurultu p99 3.0, yildiz tepesi >= 25)
YILDIZ_ALAN = 2000       # px (16x20); daha buyuk parlak bilesen yildiz degil (cember parcasi vb.)
TEMIZLIK_PAYI = 1.10   # motor temizligi, g kapisi payinin 1.1 kati (motor kutusu katman, kapi kutusu sayfa bandi)
PAY_ORAN = 0.0625        # yazi kutusu payi = W x 0.0625 (16x20: 300 px). Olculen: orijinallerde yazi-yildiz en yakin
                         # 356 px (78 cift); kusurlu ciktilarda 0 / 207 / 208 / 214 / 288 px


def egri_olc(rgb):
    """rgb: (n, 3) ana sembol cekirdek renkleri -> (256, 3) luma -> RGB tablosu."""
    L = rgb @ LUMA
    b = np.clip((L / 4).astype(int), 0, 63)
    xs, ys = [], []
    for i in range(64):
        s = b == i
        if s.sum() >= 30:
            xs.append(float(np.median(L[s]))); ys.append(np.median(rgb[s], 0))
    xs, ys = np.asarray(xs), np.asarray(ys)
    return np.stack([np.interp(np.arange(256), xs, ys[:, c]) for c in range(3)], 1).astype(np.float32)


def renk(l, egri):
    li = np.clip(l, 0, 255)
    return np.stack([np.interp(li, np.arange(256), egri[:, c]) for c in range(3)], -1).astype(np.float32)


def yukseklik_egim(A, sigma):
    h = cv2.GaussianBlur(A.astype(np.float32), (0, 0), sigma)
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8.0 * sigma
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8.0 * sigma
    return gy, gx


def boru_t(A, pencere):
    """goreli kenar uzakligi t (0 kenar, 1 govde ortasi): uzaklik donusumu / yerel en buyugu."""
    m = (A > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    mx = cv2.dilate(dt, np.ones((pencere, pencere), np.uint8))
    return np.where(m > 0, dt / np.maximum(mx, 1), 0).astype(np.float32)


def doku_olc(A, L, W):
    """Ana sembol dokusu: (1) boru profili L(t), t 10 kutu ortancasi; (2) kalan oran ~ 1 + a dh/dy + b dh/dx
    (kabartma; sigma en iyi R^2). Doner model parcasi."""
    pencere = int(round(61 * W / 4800)) | 1
    full = A >= 0.9
    t = boru_t(A, pencere)
    tb = np.clip((t[full] * 10).astype(int), 0, 9)
    Lf = L[full]
    prof = np.array([float(np.median(Lf[tb == i])) if (tb == i).sum() >= 30 else np.nan for i in range(10)])
    ok = ~np.isnan(prof)
    prof = np.interp(np.arange(10), np.nonzero(ok)[0], prof[ok])
    pred = prof[tb]
    r = Lf / np.maximum(pred, 1) - 1
    en = None
    for s_ in (1.0, 1.5, 2.0, 3.0, 4.0, 6.0):
        sig = s_ * W / 3307
        gy, gx = yukseklik_egim(A, sig)
        X = np.stack([gy[full], gx[full]], 1)
        coef, *_ = np.linalg.lstsq(X, r, rcond=None)
        if en is None or np.abs(r - X @ coef).sum() < en[0]:
            en = (np.abs(r - X @ coef).sum(), sig, coef)
    _, sig, coef = en
    gy, gx = yukseklik_egim(A, sig)
    tam = pred * np.clip(1 + coef[0] * gy[full] + coef[1] * gx[full], 0.5, 1.6)
    r2 = 1 - float(((Lf - tam) ** 2).sum() / max(((Lf - Lf.mean()) ** 2).sum(), 1e-6))
    return {'profil': [round(float(v), 1) for v in prof], 'pencere': pencere,
            'kabartma': {'sigma': round(float(sig), 2), 'a': round(float(coef[0]), 4), 'b': round(float(coef[1]), 4)},
            'r2': round(r2, 3)}


def duz_l(A, model):
    """isim / tagline / cember luma dokusu: boru profili x kabartma (tek kez)."""
    d = model['doku']
    t = boru_t(A, d['pencere'])
    l = np.interp(t * 10 - 0.5, np.arange(10), np.asarray(d['profil'], np.float32)).astype(np.float32)
    kb = d['kabartma']
    gy, gx = yukseklik_egim(A, kb['sigma'])
    return l * np.clip(1 + kb['a'] * gy + kb['b'] * gx, 0.5, 1.6)


def qc_cekirdek_L(rgb, A, Pb, W, isaret):
    """qc.oge_renkleri ile ayni olcum: bolge plate ustune birlestirilir, QC olcegine (3307, BOX) indirilir, murekkep
    (|fark| > 12) 3x3 asindirilmis cekirdeginin ortanca lumasi."""
    from PIL import Image
    f = 3307 / W
    comp = Pb * (1 - A[..., None]) + rgb * A[..., None]
    sz = (max(1, int(round(comp.shape[1] * f))), max(1, int(round(comp.shape[0] * f))))
    c = np.asarray(Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8)).resize(sz, Image.BOX), np.float32)
    p = np.asarray(Image.fromarray(np.clip(Pb, 0, 255).astype(np.uint8)).resize(sz, Image.BOX), np.float32)
    m = np.clip(((p - c) @ LUMA) * isaret, 0, None)
    ce = cv2.erode((m > 12).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ce = ce if ce.sum() >= 50 else m > 12
    return float(np.median((c @ LUMA)[ce]))


def boya(l, A, Pb, W, isaret, model, tur=3):
    """luma dokusu l -> renk = egri(l x k); k, qc olcumuyle cekirdek ortancasi Lmed olacak sekilde (3 tur)."""
    k = model['Lmed'] / max(float(np.median(l[A > 0.9])) if (A > 0.9).any() else 1.0, 1.0)
    for _ in range(tur):
        k *= model['Lmed'] / max(qc_cekirdek_L(renk(l * k, model['egri']), A, Pb, W, isaret), 1.0)
    return renk(l * k, model['egri']), round(k, 4)


def yerel_medyan(L, W):
    kw = 31 if W == 3307 else int(round(31 * W / 3307)) | 1
    return cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), kw).astype(np.float32)


def yildiz_maskesi(P, bolge):
    """P (H, W, 3) plate; bolge bool (yazi kutusu + pay). Parlak kucuk bilesenler (yildiz), 3 px genisletilmis."""
    H, W = P.shape[:2]
    L = P @ LUMA
    R = L - yerel_medyan(L, W)
    adaylar = (R > YILDIZ_T) & bolge
    n, lab, st, _ = cv2.connectedComponentsWithStats(adaylar.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] <= YILDIZ_ALAN * (W / 4800) ** 2
    m = tut[lab]
    return cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & bolge, int(n - 1)


def yildiz_temizle(P, kutular, W):
    """kutular: [(x0, y0, x1, y1)] yazi kutulari; pay = W x PAY_ORAN. Plate kopyasinda yildizlar yerel kanal
    medyaniyla doldurulur (yalniz pay icinde). Doner (P', kayit)."""
    H = P.shape[0]
    pay = int(round(PAY_ORAN * TEMIZLIK_PAYI * W))                    # kapi payindan %10 genis (kutu olcum farki)
    bolge = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in kutular:
        bolge[max(0, y0 - pay):min(H, y1 + pay), max(0, x0 - pay):min(W, x1 + pay)] = True
    m, n = yildiz_maskesi(P, bolge)
    if not m.any():
        return P, {'pay_px': pay, 'yildiz_px': 0}
    kw = 31 if W == 3307 else int(round(31 * W / 3307)) | 1
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = max(0, ys.min() - kw), min(H, ys.max() + kw + 1), max(0, xs.min() - kw), min(W, xs.max() + kw + 1)
    alt = np.clip(P[y0:y1, x0:x1], 0, 255).astype(np.uint8)
    med = np.stack([cv2.medianBlur(np.ascontiguousarray(alt[..., c]), kw) for c in range(3)], -1).astype(np.float32)
    P2 = P.copy()
    mm = m[y0:y1, x0:x1]
    P2[y0:y1, x0:x1][mm] = med[mm]
    n2, _, _, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    return P2, {'pay_px': pay, 'yildiz_px': int(m.sum()), 'yildiz': int(n2 - 1)}
