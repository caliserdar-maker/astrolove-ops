# Vektor + tam geometri yuzeyi (7 Eki 2026, Serdar onayi "Ok").
# Eski yol: piksel siluetinden mesafe haritasi + sigma 6 bulaniklastirma -> kat (sirt/birlesim) cizgileri tirtikli, kivrik,
# kavsakta centik/leke. Yeni yol: oge siniri potrace ile vektore cevrilir (matematiksel egri), her piksel merkezinin
# sinira EN YAKIN noktasi yogun ornekli egriden bulunur. Yon = (p - q)/|p - q| (mesafe alaninin tam egimi). Bulaniklastirma
# yok; kat cizgileri tam medial eksen. Kat pikselleri 2x2 alt ornekle yumusatilir (1 px kenar yumusatma, tirtik yok).
import numpy as np, potrace
from scipy.spatial import cKDTree

def _bez(p0, c1, c2, p3, n):
    t = np.linspace(0, 1, n, endpoint=False)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * c1 + 3 * (1 - t) * t * t * c2 + (t ** 3) * p3

def sinir_noktalari(m, turdsize=4, alphamax=1.0, adim=0.3):
    """ikili maske (True = oge) -> sinir egrileri uzerinde ~adim px aralikli noktalar (x, y), piksel koordinati"""
    path = potrace.Bitmap(m.astype(bool)).trace(turdsize=turdsize, alphamax=alphamax, opticurve=False)
    P = []
    for c in path:
        a = np.array([c.start_point.x, c.start_point.y], np.float64)
        for g in c.segments:
            e = np.array([g.end_point.x, g.end_point.y], np.float64)
            if g.is_corner:
                b = np.array([g.c.x, g.c.y], np.float64)
                for u, v in ((a, b), (b, e)):
                    n = max(2, int(np.ceil(np.hypot(*(v - u)) / adim)))
                    t = np.linspace(0, 1, n, endpoint=False)[:, None]; P.append(u + (v - u) * t)
            else:
                c1 = np.array([g.c1.x, g.c1.y]); c2 = np.array([g.c2.x, g.c2.y])
                L = np.hypot(*(c1 - a)) + np.hypot(*(c2 - c1)) + np.hypot(*(e - c2))
                P.append(_bez(a, c1, c2, e, max(2, int(np.ceil(L / adim)))))
            a = e
    return np.concatenate(P) if P else np.zeros((0, 2))

def yon_alani(A01, turdsize=4, alphamax=1.0):
    """A01 (0..1). Donus: [(ys, xs), [(ux, uy) her alt ornek icin]] - birim yon (iceri dogru, mesafe alaninin egimi).
    Alt ornek ici/disi alfadan (iki dogrusal) okunur; yonler ORTALANMAZ, golge her alt ornekte ayri hesaplanip ortalanir
    (yon ortalamasi kat pikselinde duz normal = parlak nokta yapiyordu)."""
    import cv2
    m = A01 > 0.5
    P = sinir_noktalari(m, turdsize, alphamax)
    sec = cv2.dilate((A01 > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ys, xs = np.nonzero(sec)
    if len(P) == 0: return (ys, xs), []
    T = cKDTree(P)
    Af = A01.astype(np.float32)
    out = []
    for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        q = np.c_[xs + ox, ys + oy]
        dist, idx = T.query(q, workers=-1)
        v = (q - P[idx]) / np.maximum(dist, 1e-6)[:, None]
        # alt ornegin alfa degeri (piksel merkezleri x+0.5): iki dogrusal
        from scipy.ndimage import map_coordinates
        a_s = map_coordinates(Af, [ys + oy - 0.5, xs + ox - 0.5], order=1, mode='constant')
        isr = np.where(a_s > 0.5, 1.0, -1.0)
        out.append(((isr * v[:, 0]).astype(np.float32), (isr * v[:, 1]).astype(np.float32)))
    return (ys, xs), out
