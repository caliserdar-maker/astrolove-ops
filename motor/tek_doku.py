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
Yildiz: yazi kutusu + pay icinde plate'in parlak noktalari (yerel 31 px medyandan > YILDIZ_T luma, kucuk bilesen),
isinlariyla birlikte ayni plate'in yildizsiz bir parcasiyla degistirilir (doku kopyasi; 3 Eki goz kontrolu: medyan
dolgusu gri leke birakiyordu). Cember: halka_altin geometrisi (t) + cizgi kalinligina olcekli kabartma.
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
    m8 = (A > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m8, cv2.DIST_L2, 5)
    sirt = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt > 1)
    return {'profil': [round(float(v), 1) for v in prof], 'pencere': pencere,
            'yaricap': round(float(np.median(dt[sirt])), 2),
            'kabartma': {'sigma': round(float(sig), 2), 'a': round(float(coef[0]), 4), 'b': round(float(coef[1]), 4)},
            'r2': round(r2, 3)}


def cizgi_yaricapi(A):
    m8 = (A > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m8, cv2.DIST_L2, 5)
    sirt = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt > 1)
    return float(np.median(dt[sirt])) if sirt.any() else 1.0


def duz_l(A, model, olcekli=False, t=None):
    """isim / tagline / cember luma dokusu: boru profili x kabartma (tek kez).
    olcekli (cember): kabartma sigmasi cizgi kalinligina gore (sigma x oge yaricapi / ana sembol yaricapi, <= sigma).
    3 Eki goz kontrolu: ana sembolun kalin cizgisinde olculen sigma (6-9 px) 12 px cembere aynen uygulaninca cemberin
    tamami kenar golgesi oluyor, alfa dalgalanmasi boyuna leke veriyordu (CANCER_LIBRA, AQUARIUS_LEO a ~ 1.65).
    t: hazir kesit konumu (cember: halka_altin geometrisi, 0 kenar 1 merkez); yoksa boru_t."""
    d = model['doku']
    if t is None:
        t = boru_t(A, d['pencere'])
    l = np.interp(t * 10 - 0.5, np.arange(10), np.asarray(d['profil'], np.float32)).astype(np.float32)
    kb = d['kabartma']
    sig = kb['sigma']
    if olcekli and d.get('yaricap'):
        sig = kb['sigma'] * min(1.0, cizgi_yaricapi(A) / d['yaricap'])
    gy, gx = yukseklik_egim(A, sig)
    return l * np.clip(1 + kb['a'] * gy + kb['b'] * gx, 0.5, 1.6)


STIL_NB = 16               # kabartma stili: goreli derinlik t kutulari (0 kenar, 1 cizgi ortasi)


def stil_alan(A, W, t=None, th=None):
    """goreli derinlik t (boru_t) ve disa kenar normali th (kenar uzakligi alaninin egimi); w: normal guveni."""
    if t is None:
        t = boru_t(A, int(round(61 * W / 4800)) | 1)
    m8 = (A > 0.5).astype(np.uint8)
    ds = cv2.GaussianBlur(cv2.distanceTransform(m8, cv2.DIST_L2, 5), (0, 0), 1.0)
    gx = cv2.Sobel(ds, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(ds, cv2.CV_32F, 0, 1, ksize=3) / 8
    if th is None:
        th = np.arctan2(-gy, -gx)
        w = np.clip(np.hypot(gx, gy) / 0.3, 0, 1)
    else:
        w = np.ones_like(t)
    return t.astype(np.float32), th.astype(np.float32), w.astype(np.float32)


def stil_olc(A, L, W):
    """Ana sembol kabartma stili (Serdar 4 Eki): goreli derinlik t kutularinda L = p(t) + qc(t) cos th + qs(t) sin th
    (p: boru / kenar profili, q: vurgu-golge genligi, atan2(qs, qc): isik yonu, disa normal acisi). Kenar pikselleri
    dahil (A >= 0.5). Kutular arasi Gauss (1 kutu) yumusatma."""
    t, th, w = stil_alan(A, W)
    ok = (A >= 0.5) & (w > 0.6)
    b = np.clip((t * STIL_NB).astype(int), 0, STIL_NB - 1)
    C = np.full((STIL_NB, 3), np.nan)
    for i in range(STIL_NB):
        s = ok & (b == i)
        if s.sum() >= 60:
            X = np.stack([np.ones(s.sum()), np.cos(th[s]), np.sin(th[s])], 1)
            C[i] = np.linalg.lstsq(X, L[s], rcond=None)[0]
    v = ~np.isnan(C[:, 0])
    for j in range(3):
        C[:, j] = np.interp(np.arange(STIL_NB), np.nonzero(v)[0], C[v, j])
        C[:, j] = cv2.GaussianBlur(np.pad(C[:, j], 3, mode='edge').astype(np.float32)[None], (0, 0), 1.0)[0][3:-3]
    q = np.hypot(C[:, 1], C[:, 2])
    kenar = slice(0, int(0.45 * STIL_NB))
    aci = float(np.degrees(np.arctan2(C[kenar, 2].sum(), C[kenar, 1].sum())))
    return {'p': [round(float(x), 2) for x in C[:, 0]], 'qc': [round(float(x), 3) for x in C[:, 1]],
            'qs': [round(float(x), 3) for x in C[:, 2]], 'isik_aci': round(aci, 1),
            'vurgu_golge_kenar': round(float(2 * q[kenar].max()), 2)}


def stil_l(A, model, W, t=None, th=None):
    """oge luma dokusu = ana sembol stili (kendi t ve normaliyle): p(t) + w (qc(t) cos th + qs(t) sin th)."""
    st = model['stil']
    t, th, w = stil_alan(A, W, t, th)
    x = np.clip(t * STIL_NB - 0.5, 0, STIL_NB - 1)
    k = np.arange(STIL_NB)
    p, qc, qs = (np.interp(x, k, np.asarray(st[n], np.float32)).astype(np.float32) for n in ('p', 'qc', 'qs'))
    return p + w * (qc * np.cos(th) + qs * np.sin(th))


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


UZANIM = 4.5             # yildiz isini / cekirdek yaricapi (olculen 117 plate yildizi, alan > 200: p95 3.6, en buyuk 4.0)


def yildiz_temizle(P, kutular, W, haric=None):
    """kutular: [(x0, y0, x1, y1)] yazi kutulari; pay = W x PAY_ORAN x TEMIZLIK_PAYI. Her yildiz (cekirdek + isinlar,
    yaricap UZANIM x cekirdek + 16 px) ayni plate'in yakindaki yildizsiz bir parcasiyla degistirilir (doku kopyasi):
    aday parcalar 16 yonde, gecis halkasinda kanal ortalamasi esitlenmis kare fark en kucuk olan; dairesel kosinus
    gecis (F px). Duz medyan dolgusu YOK (3 Eki goz kontrolu: gri leke + kirik isin). haric: aday parca olamayacak
    bolge (cember zemini). Doner (P', kayit)."""
    H = P.shape[0]
    q = W / 4800
    pay = int(round(PAY_ORAN * TEMIZLIK_PAYI * W))
    bolge = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in kutular:
        bolge[max(0, y0 - pay):min(H, y1 + pay), max(0, x0 - pay):min(W, x1 + pay)] = True
    L = P @ LUMA
    R = L - yerel_medyan(L, W)
    n, lab, st, cen = cv2.connectedComponentsWithStats((R > YILDIZ_T).astype(np.uint8), 8)
    kucuk = np.zeros(n, bool)
    kucuk[1:] = st[1:, cv2.CC_STAT_AREA] <= YILDIZ_ALAN * q ** 2
    tum = kucuk[lab]                                                   # sayfadaki tum yildiz cekirdekleri
    yasak = cv2.dilate(tum.astype(np.uint8), np.ones((int(120 * q) | 1,) * 2, np.uint8)).astype(bool)
    if haric is not None:
        yasak |= haric
    hedef = [i for i in range(1, n) if kucuk[i] and bolge[lab == i].any()] if n > 1 else []
    P2 = P.copy()
    F = max(4, int(round(8 * q)))
    kayit = []
    for i in hedef:
        cx, cy = cen[i]
        rs = UZANIM * np.sqrt(st[i, cv2.CC_STAT_AREA] / np.pi) + 16 * q
        h = int(np.ceil(rs)) + F
        x0, y0 = int(round(cx)) - h, int(round(cy)) - h
        if x0 < 0 or y0 < 0 or x0 + 2 * h + 1 > W or y0 + 2 * h + 1 > H:
            continue
        T = P2[y0:y0 + 2 * h + 1, x0:x0 + 2 * h + 1]
        yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
        d = np.hypot(xx, yy)
        w = np.clip((rs + F - d) / F, 0, 1)
        w = 0.5 - 0.5 * np.cos(np.pi * w)                              # 1 icerde, kosinus gecis
        ban = (d > rs) & (d <= rs + F)
        en = None
        for r_ in (2.2 * h, 3.0 * h, 4.0 * h, 5.5 * h):
            for t_ in np.arange(16) * np.pi / 8:
                dx, dy = int(round(r_ * np.cos(t_))), int(round(r_ * np.sin(t_)))
                u0, v0 = x0 + dx, y0 + dy
                if u0 < 0 or v0 < 0 or u0 + 2 * h + 1 > W or v0 + 2 * h + 1 > H:
                    continue
                if yasak[v0:v0 + 2 * h + 1, u0:u0 + 2 * h + 1].any():
                    continue
                D = P[v0:v0 + 2 * h + 1, u0:u0 + 2 * h + 1]
                ofs = T[ban].mean(0) - D[ban].mean(0)
                sk = float(((D[ban] + ofs - T[ban]) ** 2).mean())
                if en is None or sk < en[0]:
                    en = (sk, D + ofs, dx, dy)
        if en is None:
            kayit.append({'x': int(cx), 'y': int(cy), 'durum': 'aday parca yok'})
            continue
        P2[y0:y0 + 2 * h + 1, x0:x0 + 2 * h + 1] = T * (1 - w[..., None]) + en[1] * w[..., None]
        kayit.append({'x': int(cx), 'y': int(cy), 'r': round(float(rs), 1), 'kaynak': [en[2], en[3]],
                      'gecis_rmse': round(float(np.sqrt(en[0])), 2)})
    return P2, {'pay_px': pay, 'yildiz': len(kayit), 'parca': kayit,
                'eksik': sum(1 for k in kayit if 'durum' in k)}
