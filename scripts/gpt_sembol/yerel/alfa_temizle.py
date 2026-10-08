# Kaynak alfa temizligi (7 Eki 2026, Serdar: "baglanti yerleri daha guzel olmali, bazi ogelerde tasmalar var").
# 1) TASMA: kaynak altin PNG'de duz kenara yapisik kucuk kabarciklar (ARIES_LIBRA bandi). Gri acma ile kalan parca;
#    yalniz yuksekligi kucuk VE tabaninda ince ic bukey yarik olan parca silinir (kare kose / sivri uc korunur).
# 2) KAVSAK: cizgilerin birlestigi ic koseye yuvarlak dolgu (fillet). Gri kapama ile dolan parca, topoloji
#    degismiyorsa (iki ayri parcayi birlestirmiyor, delik acip kapatmiyorsa) kabul edilir.
# Olcuer: yerel yari kalinlik medyani Dm (iskelet uzerinde d); tum yaricaplar Dm ile oranli -> her boyda ayni gorunum.
import numpy as np, cv2

def _disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

def _topo(m):
    nf = cv2.connectedComponents(m.astype(np.uint8), connectivity=8)[0]
    nb = cv2.connectedComponents((~m).astype(np.uint8), connectivity=4)[0]
    return nf, nb

def yari_kalinlik(a):
    from skimage.morphology import skeletonize
    m = a > 127
    d = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    sk = skeletonize(m)
    v = d[sk & (d > 2)]
    return float(np.median(v)) if v.size else 10.0

def tasma_sil(a, Dm, acma=0.2, hmax=0.16, yarik=0.06):
    a = a.copy()
    q = int(acma * Dm) + 12; ap = np.pad(a, q)
    ac = cv2.morphologyEx(ap, cv2.MORPH_OPEN, _disk(acma * Dm))[q:-q, q:-q]
    kp = cv2.morphologyEx(ap, cv2.MORPH_CLOSE, _disk(max(2, yarik * Dm)))[q:-q, q:-q]
    yrk = (kp.astype(np.int16) - a) > 64                               # bir kabarcigin tabanindaki ince yarik
    fark = (a.astype(np.int16) - ac) > 64
    dist = cv2.distanceTransform((ac <= 127).astype(np.uint8), cv2.DIST_L2, 5)
    n, l, st, _ = cv2.connectedComponentsWithStats(fark.astype(np.uint8), connectivity=8)
    sil = 0
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        p = max(4, int(0.1 * Dm))
        ys, xs = slice(max(0, y - p), y + h + p), slice(max(0, x - p), x + w + p)
        ci = l[ys, xs] == i
        if dist[ys, xs][ci].max() > hmax * Dm: continue                 # uzun cikinti = sivri uc, dokunma
        if not (cv2.dilate(ci.astype(np.uint8), _disk(3)) > 0)[yrk[ys, xs]].any(): continue   # yarik yok = kose
        mk = cv2.dilate(ci.astype(np.uint8), _disk(2)) > 0
        a[ys, xs][mk] = np.minimum(a[ys, xs], ac[ys, xs])[mk]
        sil += 1
    return a, sil

def gercek_kavsak(m, Dm):
    """Budanmis iskelette 3+ uzun dalin bulustugu noktalar (uc/kose/teget temas kaynakli kisa dallar elenir)."""
    from skimage.morphology import skeletonize
    skp = skeletonize(m).astype(np.uint8)
    d0 = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    K3 = np.ones((3, 3), np.float32)
    for _ in range(int(1.5 * Dm)):
        nbp = cv2.filter2D(skp, -1, K3) - skp
        uc = (skp == 1) & (nbp <= 1)
        if not uc.any(): break
        skp[uc] = 0
    nb = cv2.filter2D(skp, -1, K3) - skp
    return (skp > 0) & (nb >= 3) & (d0 > 0.5 * Dm)

def kavsak_dolgu(a, Dm, oran=0.55, uzunluk=2.0, yakin=2.5):
    """Yalniz genis acili ic koseye yuvarlak dolgu. 7 Eki ders: (1) kenara degen uc kutuk olmasin -> once dolgu payi,
    (2) dar aci / teget temasta perde olmasin -> dolgu boyu 'uzunluk * r' den uzunsa reddedilir."""
    r = oran * Dm
    q = int(r) + 12
    ap = np.pad(a, q)
    kp = cv2.morphologyEx(ap, cv2.MORPH_CLOSE, _disk(r))[q:-q, q:-q]
    dol = (kp.astype(np.int16) - a) > 8
    m0 = a > 127; t0 = _topo(m0)
    n, l, st, _ = cv2.connectedComponentsWithStats(dol.astype(np.uint8), connectivity=8)
    out = a.copy(); kabul = red = 0
    H, W = a.shape
    bp = gercek_kavsak(m0, Dm)
    dk = cv2.distanceTransform((~bp).astype(np.uint8), cv2.DIST_L2, 5)  # gercek kavsaga uzaklik
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if ar < 4: continue
        if max(w, h) > uzunluk * r: red += 1; continue                    # dar aci kamasi / teget temas
        if x == 0 or y == 0 or x + w >= W or y + h >= H: red += 1; continue   # goruntu kenari
        ci = l == i
        if dk[ci].min() > yakin * Dm: red += 1; continue                 # gercek kavsakta degil (teget temas vb.)
        m1 = m0 | (ci & (kp > 127))
        if _topo(m1) != t0: red += 1; continue                            # iki parcayi birlestiriyor / delik kapatiyor
        out[ci] = np.maximum(out[ci], kp[ci]); kabul += 1
    return out, kabul, red

def temizle(a, kavsak=None):
    import os
    if kavsak is None: kavsak = os.environ.get('ALFA_KAVSAK', '0') == '1'
    Dm = yari_kalinlik(a)
    a, sil = tasma_sil(a, Dm)
    k = r = 0
    if kavsak:
        a, k, r = kavsak_dolgu(a, Dm, oran=float(os.environ.get('ALFA_KAVSAK_ORAN', '0.55')))
    return a, dict(Dm=round(Dm, 1), tasma=sil, dolgu=k, red=r)
