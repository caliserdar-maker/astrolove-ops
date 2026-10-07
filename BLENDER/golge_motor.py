# Blender altin malzeme haritasi (kure) -> her oge piksel normaline gore ayni malzeme. Tum ogeler ayni kural.
import os
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
import numpy as np, cv2

KS = float(os.environ.get("KURE_SIGMA", "3"))
SIRT_KESKIN = os.environ.get("SIRT_KESKIN", "0") == "1"
def kure_yukle(yol):
    k = np.load(yol.replace('.exr', '.npy'))  # RGBA float lineer, ust satir ilk
    a = k[..., 3:4].astype(np.float32); c = k[..., :3].astype(np.float32) * a
    # Monte Carlo taneciklerini temizle (kure ornekleme gurultusu cizgide serit yapar); disk disina tasir
    c = cv2.GaussianBlur(c, (0, 0), KS); w = cv2.GaussianBlur(a, (0, 0), KS)[..., None]
    return np.ascontiguousarray(c / np.maximum(w, 1e-4)).astype(np.float32)

def gurultu(shape, tohum, olcek, genlik):
    """cekic izi: ayni tohum + ayni olcek, poster koordinatinda (tum ogeler ayni alan)"""
    rs = np.random.default_rng(tohum)
    h, w = shape
    k = max(1, int(olcek / 2))
    n = rs.standard_normal((h // k + 3, w // k + 3)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 1.2)
    n = cv2.resize(n, ((w // k + 3) * k, (h // k + 3) * k), interpolation=cv2.INTER_CUBIC)[:h, :w]
    return n / (n.std() + 1e-6) * genlik

def yukseklik(A, w, sirt=0.0):
    """A: alfa 0-1. kenardan uzaklik d; yuvarlak pah w px; sirt>0 ise ic bolgede merkez cizgiye hafif egim"""
    m = (A > 0.5).astype(np.uint8)
    sd = cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    sd = sd + (A - 0.5)  # alt piksel
    x = np.clip(sd / w, 0, 1)
    h = np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)) * w
    if sirt > 0:
        h = h + sirt * np.clip(sd - w, 0, None)
    return cv2.GaussianBlur(h.astype(np.float32), (0, 0), 0.8)

def golgele(A, K, w, poz, ofs=(0, 0), tohum=7, g_olcek=28, g_genlik=0.0, sirt=0.0, nz=None):
    """A: alfa (H,W) 0-1 ; K: kure lineer RGB ; poz: pozlama carpani ; ofs: oge sol ust poster koordinati"""
    h = yukseklik(A, w, sirt)
    if g_genlik > 0:
        if nz is None:
            nz = gurultu(A.shape, tohum, g_olcek, g_genlik)
        h = h + nz
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8
    nx, ny, nzz = -gx, gy, np.ones_like(gx)
    L = np.sqrt(nx * nx + ny * ny + 1)
    nx /= L; ny /= L
    S = K.shape[0]
    u = ((nx * 0.995 + 1) / 2 * (S - 1)).astype(np.float32)
    v = ((1 - ny * 0.995) / 2 * (S - 1)).astype(np.float32)
    c = cv2.remap(K, u, v, cv2.INTER_LINEAR) * poz
    return c  # lineer RGB

def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)

def lineer(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

def egim_tup(A, k=0.8, karisim=0.0, pah=1.0, kenar_yumusak=2.5, pah_px=0.0, kubbe=0.0, egim_max=0.0, pah_oran_max=0.0):
    """Egim alani (gx, gy) ve temiz alfa. Her cizgi kendi yerel yari kalinligina D gore: x = d/D.
    Egim = k * p'(x) * grad(d)  (genislik degisimi D'nin turevi ALINMAZ -> cizgi boyunca serit olusmaz).
    Ayni k, ayni profil -> ince/kalin her cizgide ayni egim dagilimi (tek doku)."""
    from skimage.morphology import skeletonize
    from scipy.ndimage import distance_transform_edt
    m0 = (A > 0.5).astype(np.uint8)
    sd = (cv2.distanceTransform(m0, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
          - cv2.distanceTransform(1 - m0, cv2.DIST_L2, cv2.DIST_MASK_PRECISE))
    sdy = cv2.GaussianBlur(sd, (0, 0), float(os.environ.get("YON_SIGMA", "6")))  # yalniz YON icin: kaynak kenar basamaklari silinir
    sd = cv2.GaussianBlur(sd, (0, 0), kenar_yumusak)
    alfa = A.astype(np.float32)                                    # kaynagin kendi yumusak (AA) kenari
    m = sd > 0
    d = np.clip(sd, 0, None)
    sk = skeletonize(m)
    _, (iy, ix) = distance_transform_edt(~sk, return_indices=True)
    D = np.maximum(d[iy, ix], 1.0); del iy, ix
    mf = m.astype(np.float32)
    D = cv2.GaussianBlur(D * mf, (0, 0), 6) / np.maximum(cv2.GaussianBlur(mf, (0, 0), 6), 1e-3)
    D = np.maximum(D, 1.0)
    xr = np.clip(d / D, 0, 1)                                       # goreli konum (kubbe icin)
    x = np.clip(d / D / pah, 0, 1)
    if pah_px > 0:                                                  # MUTLAK pah: her yerde ayni kenar genisligi, ust yuz duz
        pw = np.minimum(pah_px, pah_oran_max * D) if pah_oran_max > 0 else pah_px   # ince cizgide pah ust yuzu yemesin
        x = np.clip(d / pw, 0, 1); pah = 1.0
    # p'(x)/pah : tup = sqrt(1-(1-x)^2) -> (1-x)/sqrt(1-(1-x)^2) ; cati -> 1 ; x=1 (duz ust) -> 0
    u = 1 - x
    dt = u / np.sqrt(np.clip(1 - u * u, 0.02, 1))
    dt = np.minimum(dt, 6.0)
    dp = (dt * (1 - karisim) + 1.0 * karisim) / pah
    if pah_px > 0 or karisim < 1:                                   # duz ust yuz yalniz pah modunda; catida sirt egimi korunur
        dp = np.where(x >= 1, 0, dp)
    if kubbe > 0:                                                   # yastik: ust yuz hafif kubbeli (kivrimda isik oyunu)
        ur = 1 - xr
        dp = dp + kubbe / k * np.minimum(ur / np.sqrt(np.clip(1 - ur * ur, 0.02, 1)), 3.0)
    ddx = cv2.Sobel(sdy, cv2.CV_32F, 1, 0, ksize=3) / 8
    ddy = cv2.Sobel(sdy, cv2.CV_32F, 0, 1, ksize=3) / 8
    gm = np.sqrt(ddx * ddx + ddy * ddy) + 1e-6
    ddx = ddx / gm; ddy = ddy / gm                                 # birim yon (|grad d| = 1)
    if SIRT_KESKIN:                                                 # sirtta yon belirsiz: egim |grad| ile yumusakca sifira (gurultulu nokta yok)
        dp = dp * np.clip((gm - 0.15) / 0.45, 0, 1) ** 0.5
    gx = (k * dp * ddx).astype(np.float32); gy = (k * dp * ddy).astype(np.float32)
    if egim_max > 0:                                                # en dik egim siniri: kenar yere (karanliga) bakmasin
        g = np.sqrt(gx * gx + gy * gy) + 1e-6; f = egim_max * np.tanh(g / egim_max) / g
        gx = (gx * f).astype(np.float32); gy = (gy * f).astype(np.float32)
    if SIRT_KESKIN:
        # sirt: yon alani komsusuna gore >90 derece donuyorsa sirt pikseli; egim BULANIKLASTIRILMAZ (ucuncu renk cizgisi olusmaz)
        dxn = ddx; dyn = ddy
        sirt = np.zeros(dxn.shape, bool)
        for sy_, sx_ in ((0, 1), (1, 0), (1, 1), (1, -1)):
            dot = dxn * np.roll(np.roll(dxn, sy_, 0), sx_, 1) + dyn * np.roll(np.roll(dyn, sy_, 0), sx_, 1)
            sirt |= dot < 0
        egim_tup.sirt = cv2.dilate(sirt.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        return gx, gy, alfa
    gx = cv2.GaussianBlur(gx, (0, 0), 1.0); gy = cv2.GaussianBlur(gy, (0, 0), 1.0)
    return gx, gy, alfa

def gurultu_egim(shape, tohum, olcek, genlik):
    n = gurultu(shape, tohum, olcek, genlik)
    return cv2.Sobel(n, cv2.CV_32F, 1, 0, ksize=3) / 8, cv2.Sobel(n, cv2.CV_32F, 0, 1, ksize=3) / 8

def golgele_g(gx, gy, K, poz=1.0):
    nx, ny = -gx, gy
    L = np.sqrt(nx * nx + ny * ny + 1); nx = nx / L; ny = ny / L
    S = K.shape[0]
    u = ((nx * 0.995 + 1) / 2 * (S - 1)).astype(np.float32)
    v = ((1 - ny * 0.995) / 2 * (S - 1)).astype(np.float32)
    return cv2.remap(K, u, v, cv2.INTER_LINEAR) * poz

def golgele_h(h, K, poz):
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8
    nx, ny = -gx, gy
    L = np.sqrt(nx * nx + ny * ny + 1); nx /= L; ny /= L
    S = K.shape[0]
    u = ((nx * 0.995 + 1) / 2 * (S - 1)).astype(np.float32)
    v = ((1 - ny * 0.995) / 2 * (S - 1)).astype(np.float32)
    return cv2.remap(K, u, v, cv2.INTER_LINEAR) * poz


def luma(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722

def renk_haritasi(Y_bizim, ref_rgb, n=64):
    """REF renk paleti, yumusak: (1) parlaklik eslemesi g: bizim -> REF, az sayida yuzdelik noktadan parcali dogrusal
    (dik basamak yok, serit olusmaz); (2) REF parlaklik -> REF ortanca renk (n kutu, yumusatilmis). Tum ogelere ayni."""
    qs = np.array([0.0, 0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98, 1.0])
    Yr = luma(ref_rgb)
    xb = np.quantile(Y_bizim, qs); xr = np.quantile(Yr, qs)
    xb = np.maximum.accumulate(xb + np.arange(len(xb)) * 1e-4)
    kut = np.quantile(Yr, np.linspace(0, 1, n + 1))
    lc = (kut[:-1] + kut[1:]) / 2
    idx = np.clip(np.searchsorted(kut, Yr) - 1, 0, n - 1)
    lut = np.array([np.median(ref_rgb[idx == b], 0) if (idx == b).any() else [np.nan] * 3 for b in range(n)], np.float32)
    for k in range(3):
        v = lut[:, k]; ok = ~np.isnan(v); lut[:, k] = np.interp(np.arange(n), np.nonzero(ok)[0], v[ok])
    lut = cv2.GaussianBlur(lut[:, None, :], (1, 9), 2.0)[:, 0, :]
    return xb.astype(np.float32), xr.astype(np.float32), lc.astype(np.float32), lut

def uygula_harita(Y, harita):
    xb, xr, lc, lut = harita
    L = np.interp(Y, xb, xr)
    return np.stack([np.interp(L, lc, lut[:, k]) for k in range(3)], -1).astype(np.float32)

def renk_haritasi_dogrusal(Y_bizim, ref_rgb, n=64):
    """Sira-esleme YOK (esit degerler kamuflaj yapmasin): t = (Y - p1)/(p99 - p1), gama ile orta ton REF ortancasina,
    sonra REF parlaklik -> REF ortanca renk. Yapi (isik/pah) birebir korunur. Tum ogelere ayni."""
    Yr = luma(ref_rgb)
    lo, hi = np.percentile(Y_bizim, [1, 99]); rlo, rhi = np.percentile(Yr, [1, 99])
    tm = np.clip((np.median(Y_bizim) - lo) / (hi - lo), 1e-3, 0.999)
    trm = np.clip((np.median(Yr) - rlo) / (rhi - rlo), 1e-3, 0.999)
    gama = float(np.log(trm) / np.log(tm))
    kut = np.quantile(Yr, np.linspace(0, 1, n + 1)); lc = (kut[:-1] + kut[1:]) / 2
    idx = np.clip(np.searchsorted(kut, Yr) - 1, 0, n - 1)
    lut = np.array([np.median(ref_rgb[idx == b], 0) if (idx == b).any() else [np.nan] * 3 for b in range(n)], np.float32)
    for k in range(3):
        v = lut[:, k]; ok = ~np.isnan(v); lut[:, k] = np.interp(np.arange(n), np.nonzero(ok)[0], v[ok])
    lut = cv2.GaussianBlur(lut[:, None, :], (1, 9), 2.0)[:, 0, :]
    return ('dogrusal', float(lo), float(hi), float(rlo), float(rhi), gama, lc.astype(np.float32), lut)

def uygula_harita2(Y, h):
    if isinstance(h, tuple) and len(h) and isinstance(h[0], str):
        _, lo, hi, rlo, rhi, gama, lc, lut = h
        t = np.clip((Y - lo) / (hi - lo), 0, 1.15)
        t = np.power(np.clip(t, 0, None), gama)
        ka, kb = float(os.environ.get('KONT_A', '1')), float(os.environ.get('KONT_B', '1'))
        if ka != 1 or kb != 1:                                       # kontrast: koyular koyulasir (a), parlak alan daralir (b); orta ton sabit
            m = min(max(float(os.environ.get('KONT_M', '0.55')), 0.05), 0.95)
            tl = m * np.power(np.clip(t / m, 0, 1), ka)
            th = m + (1 - m) * np.power(np.clip((t - m) / (1 - m), 0, None), kb)
            t = np.where(t < m, tl, th)
        L = rlo + (rhi - rlo) * t
        return np.stack([np.interp(L, lc, lut[:, k]) for k in range(3)], -1).astype(np.float32)
    return uygula_harita(Y, h)
