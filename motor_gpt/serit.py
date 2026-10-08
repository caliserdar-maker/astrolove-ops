# Cizgi (serit) modeli: baglantida referanstaki gibi "bir cizgi devam eder, oteki ona kaynasir" (7 Eki 2026, Serdar onayi).
# Mesafe alani (DT) her baglantida sirtlari ortada sert X/Y ile bulusturur ve kavsak merkezini sisirir (piramit).
# Burada oge iskeleti dallara ayrilir; her dal bir cizgi, yuksekligi h(p) = w(q) - |p - q| (q en yakin cizgi noktasi,
# w cizginin KENDI yari kalinligi). Gercek kavsakta (3+ uzun kol) kol kalinligi sismeden once olculur ve kavsak icinde
# o degerle sinirlanir; en duz devam eden iki kol tek cizgi olarak kavsagin icinden gecer. Yukseklik = tum cizgilerin
# maksimumu, ic ve disarida SUREKLI (kenarda sicrama yok). Golge yalniz bu alanin yonunu kullanir (cati profili).
import numpy as np, cv2
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize

K3 = np.ones((3, 3), np.uint8)
import os
KAVSAK_SIGMA = float(os.environ.get('SERIT_YUM', '0.3'))   # kavsak yumusatma (Dm cinsinden)
KAVSAK_R = float(os.environ.get('SERIT_R', '2.5'))
SALIM = 0.15                       # kavsak disinda kalinlik siniri bu egimle serbest kalir (sicrama yok)

def _komsu(sk):
    return cv2.filter2D(sk.astype(np.uint8), -1, K3.astype(np.float32), borderType=cv2.BORDER_CONSTANT) - sk.astype(np.uint8)

def _izle(ys, xs):
    """dal piksellerini sirala: bir uctan en uzak piksele en kisa yol (BFS); acgozlu izleme kopuk kalabiliyordu"""
    from collections import deque
    S = {p: i for i, p in enumerate(zip(ys.tolist(), xs.tolist()))}
    P = list(S)
    def kom(p):
        y, x = p
        return [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (y + dy, x + dx) in S]
    def bfs(bas):
        onc = {bas: None}; q = deque([bas]); son = bas
        while q:
            p = q.popleft(); son = p
            for n in kom(p):
                if n not in onc: onc[n] = p; q.append(n)
        return onc, son
    uclar = [p for p in P if len(kom(p)) <= 1]
    bas = min(uclar) if uclar else min(P)
    _, a = bfs(bas)                      # en uzak uc
    onc, b = bfs(a)                      # a'dan en uzak: yol a..b
    yol = [b]
    while onc[yol[-1]] is not None: yol.append(onc[yol[-1]])
    return np.array(yol[::-1], np.int32)

def serit_yukseklik(A01, sd=None):
    """A01: 0..1 oge alfasi. Donus: (H, bilgi). H: iceride yukseklik, disarida (cizgi koni) negatif; kapsanmayan yer sd."""
    m0 = (A01 > 0.5).astype(np.uint8)
    if sd is None:
        sd = (cv2.distanceTransform(m0, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
              - cv2.distanceTransform(1 - m0, cv2.DIST_L2, cv2.DIST_MASK_PRECISE))
    sd = sd.astype(np.float32)
    d = np.clip(sd, 0, None)
    msk = cv2.GaussianBlur(m0.astype(np.float32), (0, 0), 1.5) > 0.5
    sk = skeletonize(msk) & (m0 > 0)
    v = d[sk & (d > 2)]
    if v.size == 0: return sd, dict(dugum=0, cizgi=0)
    Dm = float(np.median(v))
    J = sk & (_komsu(sk) >= 3)
    Jd = (cv2.dilate(J.astype(np.uint8), K3) > 0) & sk
    nJ, Jl = cv2.connectedComponents(Jd.astype(np.uint8), connectivity=8)
    dal = sk & ~Jd
    nD, Dl = cv2.connectedComponents(dal.astype(np.uint8), connectivity=8)
    Jl2 = cv2.dilate(Jl.astype(np.uint16), K3)
    kmer = {j: tuple(np.mean(np.nonzero(Jl == j), axis=1)) for j in range(1, nJ)}
    dallar = []
    for i in range(1, nD):
        ys, xs = np.nonzero(Dl == i)
        yol = _izle(ys, xs)
        u0 = int(Jl2[yol[0][0], yol[0][1]]); u1 = int(Jl2[yol[-1][0], yol[-1][1]])
        dallar.append(dict(yol=yol, u=[u0, u1], L=len(yol)))
    # kisa ic dal ile bagli kumeler tek dugum (X kesisimi iki Y kumesi + kisa bag olarak cikar)
    ust = {j: j for j in kmer}
    KUME = float(os.environ.get('SERIT_KUME', '2.0'))                     # ic dal bu kat kalinliktan kisaysa iki kavsak tek kume
    def bul(a):
        while ust[a] != a:
            ust[a] = ust[ust[a]]; a = ust[a]
        return a
    for b in dallar:
        a_, c_ = b['u']
        if a_ and c_ and a_ != c_ and b['L'] < KUME * max(float(d[tuple(b['yol'][b['L'] // 2])]), 0.5 * Dm):
            ust[bul(a_)] = bul(c_)
    dugum = {}
    for j in kmer: dugum.setdefault(bul(j), []).append(j)
    dmer = {k: (float(np.mean([kmer[j][0] for j in v])), float(np.mean([kmer[j][1] for j in v]))) for k, v in dugum.items()}
    kume_dugum = {j: bul(j) for j in kmer}
    for b in dallar:
        b['n'] = [kume_dugum.get(u, 0) if u else 0 for u in b['u']]
    # gercek dugum: 3+ kol (serbest uclu kisa kuyruk sayilmaz)
    gercek = {}
    for k in dugum:
        kol = []
        for bi, b in enumerate(dallar):
            if b['n'][0] == k and b['n'][1] == k: continue
            for uc in (0, 1):
                if b['n'][uc] == k:
                    serbest = b['n'][1 - uc] == 0
                    if serbest and b['L'] < 0.8 * Dm: continue
                    kol.append((bi, uc))
        if len(kol) >= 3: gercek[k] = kol
    cizgiler = []
    zinc = list(range(len(dallar)))                                       # fiziksel cizgi (zincir): kavsaktan duz gecen kollar ayni
    def zb(a):
        while zinc[a] != a:
            zinc[a] = zinc[zinc[a]]; a = zinc[a]
        return a
    dugum_bilgi = []                                                      # (cy, cx, zon, wmax)
    ESLES = {}; KOL = {}                                                  # (dal, uc) -> esi / (dugum, kol kalinligi)
    sinir = {}
    CAP = np.full(sd.shape, np.inf, np.float32)                         # her iskelet noktasinda TUM kavsaklarin siniri                                                            # (dal, uc) -> (zon, wkol) kavsak siniri
    cift_bekle = []
    zonlar = []                                                           # tum gercek kavsaklarin sisme bolgeleri
    for k in gercek:
        cy, cx = dmer[k]; dc = float(d[int(round(cy)), int(round(cx))]); zonlar.append((cy, cx, 1.2 * (dc if dc > 0 else Dm)))
    def zon_disi(yol):
        ok = np.ones(len(yol), bool)
        for zy, zx, zr in zonlar:
            ok &= np.hypot(yol[:, 0] - zy, yol[:, 1] - zx) > zr
        return ok
    for k, kol in gercek.items():
        cy, cx = dmer[k]
        dc = float(d[int(round(cy)), int(round(cx))]); dc = dc if dc > 0 else Dm
        zon = 1.2 * dc
        bil = []
        for bi, uc in kol:
            yol = dallar[bi]['yol'] if uc == 0 else dallar[bi]['yol'][::-1]  # dugumden disari
            # r: dugumden YOL BOYU uzaklik (kol geri donup kavsaga yaklasirsa Oklid r yaniltir: kopuk cizgi / yanlis sinir)
            r0 = float(np.hypot(yol[0, 0] - cy, yol[0, 1] - cx))
            r = r0 + np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(yol[:, 0]), np.diff(yol[:, 1])))])
            dd = d[yol[:, 0], yol[:, 1]]
            sec = zon_disi(yol) & (r < zon + 6 * Dm)                    # HICBIR kavsagin sisme bolgesinde olmayan noktalar
            wkol = float(np.percentile(dd[sec], 30)) if sec.sum() >= 3 else float(np.percentile(dd, 10))
            ref = yol[np.argmin(np.abs(r - min(zon + wkol, r.max())))]
            yon = np.arctan2(ref[0] - cy, ref[1] - cx)
            if KUME > 2.0:                                                # kume: kol yonu kumeden cikan uzun parcanin ortalamasi
                ss = (r > zon + wkol) & (r < zon + wkol + 4 * Dm)
                if ss.sum() >= 3:
                    yon = np.arctan2(np.mean(yol[ss, 0]) - cy, np.mean(yol[ss, 1]) - cx)
                if os.environ.get('SERIT_TEGET', '0') == '1':             # 8 Eki: kolun KAVSAGA GIRIS teget yonu (merkezden degil)
                    st = (r > zon) & (r < zon + 2.5 * Dm)
                    if st.sum() >= 4:
                        q = yol[st].astype(np.float64); i0 = int(np.argmin(r[st])); i1 = int(np.argmax(r[st]))
                        yon = np.arctan2(q[i1, 0] - q[i0, 0], q[i1, 1] - q[i0, 1])   # disari dogru
            bil.append(dict(bi=bi, uc=uc, yol=yol, r=r, dd=dd, wkol=wkol, yon=yon))
            sinir[(bi, uc)] = (k, zon, wkol)
            CAP[yol[:, 0], yol[:, 1]] = np.minimum(CAP[yol[:, 0], yol[:, 1]], wkol + SALIM * np.clip(r - zon, 0, None))
        # en duz devam eden kol ciftleri (aci farki en az 120 derece) kavsagin icinden tek cizgi
        ad = []
        for a in range(len(bil)):
            for b in range(a + 1, len(bil)):
                fa = abs((bil[a]['yon'] - bil[b]['yon'] + np.pi) % (2 * np.pi) - np.pi)
                ad.append((fa, a, b))
        kul = set()
        for fa, a, b in sorted(ad, reverse=True):
            if fa < np.deg2rad(120): break
            if a in kul or b in kul: continue
            kul |= {a, b}
            A_, B_ = bil[a], bil[b]
            uz = zon + 4 * max(A_['wkol'], B_['wkol'])
            def kes(K):
                s_ = K['r'] < uz
                return K['yol'][s_], np.minimum(K['dd'][s_], K['wkol'] + SALIM * np.clip(K['r'][s_] - zon, 0, None))
            ya, _ = kes(A_); yb, _ = kes(B_)
            mer = np.array([[int(round(cy)), int(round(cx))]], np.int32)
            cift_bekle.append((ya, yb, mer, 0.5 * (A_['wkol'] + B_['wkol']), A_['bi']))
            zinc[zb(A_['bi'])] = zb(B_['bi'])
            ESLES[(A_['bi'], A_['uc'])] = (B_['bi'], B_['uc'], k); ESLES[(B_['bi'], B_['uc'])] = (A_['bi'], A_['uc'], k)
        for K_ in bil: KOL[(K_['bi'], K_['uc'])] = (k, K_['wkol'])
        dugum_bilgi.append((cy, cx, zon, max(K['wkol'] for K in bil)))
    CAPf = cv2.erode(np.where(np.isinf(CAP), 1e6, CAP).astype(np.float32), np.ones((7, 7), np.uint8))   # komsu iskelet kopyalari da sinirlansin
    def gen(yol):
        return np.minimum(d[yol[:, 0], yol[:, 1]], CAPf[yol[:, 0], yol[:, 1]]).astype(np.float32)
    for ya, yb, mer, wm, bi_ in cift_bekle:
        cizgiler.append((np.concatenate([ya[::-1], mer, yb]), np.concatenate([gen(ya)[::-1], [wm], gen(yb)]), bi_))
    # her dal kendi cizgisi; gercek kavsaga giden ucu kavsak merkezine uzatilir, kalinlik tum kavsak sinirlariyla
    for bi, b in enumerate(dallar):
        if b['n'][0] and b['n'][0] == b['n'][1] and b['n'][0] in gercek: continue   # kavsak ic dali
        yol = b['yol']; w = gen(yol)
        bas, son = [], []
        for uc in (0, 1):
            k = b['n'][uc]
            if not k: continue
            cy, cx = dmer[k]
            mer = np.array([[int(round(cy)), int(round(cx))]], np.int32)
            if (bi, uc) in sinir:
                _, zon, wkol = sinir[(bi, uc)]
                wm = wkol
            else:
                wm = float(d[mer[0, 0], mer[0, 1]])
            (bas if uc == 0 else son).append((mer, wm))
        if bas: yol = np.concatenate([bas[0][0], yol]); w = np.concatenate([[bas[0][1]], w])
        if son: yol = np.concatenate([yol, son[0][0]]); w = np.concatenate([w, [son[0][1]]])
        cizgiler.append((yol, w, bi))
    # kume ici kisa parcalar (dugum kumesinin pikselleri) da kapsansin: kume pikselleri tek noktali cizgi
    Hh, Ww = sd.shape
    from scipy.ndimage import gaussian_filter1d
    ZH = {}                                                               # zincir -> (y0, y1, x0, x1, yukseklik)
    for yol, w, bi in cizgiler:
        if len(w) > 9: w = gaussian_filter1d(w.astype(np.float32), 4, mode='nearest')   # kalinlik basamagi enine serit yapmasin
        pad = int(2.5 * float(np.max(w))) + 12
        y0 = max(0, yol[:, 0].min() - pad); y1 = min(Hh, yol[:, 0].max() + pad + 1)
        x0 = max(0, yol[:, 1].min() - pad); x1 = min(Ww, yol[:, 1].max() + pad + 1)
        cz = np.zeros((y1 - y0, x1 - x0), np.uint8); wi = np.zeros((y1 - y0, x1 - x0), np.float32)
        if len(yol) == 1:
            cz[yol[0, 0] - y0, yol[0, 1] - x0] = 1; wi[yol[0, 0] - y0, yol[0, 1] - x0] = w[0]
        for i in range(len(yol) - 1):
            p0 = (int(yol[i, 1] - x0), int(yol[i, 0] - y0)); p1 = (int(yol[i + 1, 1] - x0), int(yol[i + 1, 0] - y0))
            cv2.line(cz, p0, p1, 1, 1)
            cv2.line(wi, p0, p1, float(0.5 * (w[i] + w[i + 1])), 1)
        dist, (iy, ix) = distance_transform_edt(cz == 0, return_indices=True)
        hh = (wi[iy, ix] - dist).astype(np.float32)
        z = zb(bi)
        if z not in ZH:
            ZH[z] = np.full(sd.shape, -1e9, np.float32)
        ZH[z][y0:y1, x0:x1] = np.maximum(ZH[z][y0:y1, x0:x1], hh)
    MOD = os.environ.get('SERIT_MOD', 'sert')
    def smax(a, b, k):
        h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
        return b + (a - b) * h + k * h * (1 - h)
    Hs = np.full(sd.shape, -1e9, np.float32)
    kk = {'kaynak': 0.5, 'yaka': 1.2}.get(MOD, 0) * Dm
    Hsert = np.full(sd.shape, -1e9, np.float32)
    for z, hz in ZH.items():
        Hsert = np.maximum(Hsert, hz)
    if kk > 0:
        # yuvarlak dolgu yalniz MALZEME ICINDE iki zincirin kesistigi katta: ic yukseklikler (>=0) yumusak birlesir,
        # disaridaki koniler (negatif) dolguya katilmaz (yoksa her iki cizgi arasindaki bisektorde sahte sirt olusur)
        Hs = None
        for z, hz in ZH.items():
            if Hs is None: Hs = hz.copy(); continue
            Hs = np.where((Hs > 0) & (hz > 0), smax(Hs, hz, kk), np.maximum(Hs, hz)).astype(np.float32)
    else:
        Hs = Hsert
    Hs = np.where(Hs > -1e8, Hs, sd).astype(np.float32)
    # kavsak bolgesi agirligi: zon + 1.0 w icinde 1, zon + 2.5 w disinda 0 -> disarisi onayli DT ile BIREBIR
    W = np.zeros(sd.shape, np.float32); PL = np.full(sd.shape, 1e9, np.float32)
    for cy, cx, zon, wmax in dugum_bilgi:
        R_ = zon + 2.5 * wmax
        y0 = int(max(0, cy - R_)); y1 = int(min(Hh, cy + R_ + 1)); x0 = int(max(0, cx - R_)); x1 = int(min(Ww, cx + R_ + 1))
        r = np.hypot(np.arange(y0, y1)[:, None] - cy, np.arange(x0, x1)[None] - cx)
        t = np.clip((R_ - r) / (1.5 * wmax), 0, 1); t = t * t * (3 - 2 * t)
        W[y0:y1, x0:x1] = np.maximum(W[y0:y1, x0:x1], t)
        PL[y0:y1, x0:x1] = np.minimum(PL[y0:y1, x0:x1], np.where(r < R_, 0.55 * wmax, 1e9))
    if MOD == 'kubbe':
        Hs = cv2.GaussianBlur(Hs, (0, 0), 0.45 * Dm)
    elif MOD == 'duz':
        k2 = 0.2 * Dm; a, b = Hs, PL                                      # yumusak tavan (sirt kavsakta duz yuze doner)
        h = np.clip(0.5 + 0.5 * (b - a) / k2, 0, 1)
        Hs = (b + (a - b) * h - k2 * h * (1 - h)).astype(np.float32)
    H = (sd * (1 - W) + Hs * W).astype(np.float32)
    ETK = None
    serit_yukseklik.etk = ETK; serit_yukseklik.cizgiler = [(y_, w_, zb(b_)) for y_, w_, b_ in cizgiler]
    serit_yukseklik.dugumler = [dmer[k] for k in gercek]
    serit_yukseklik.graf = dict(dallar=dallar, dmer=dmer, gercek=set(gercek), ESLES=ESLES, KOL=KOL, CAPf=CAPf, d=d, ZON={k: z for k, z in zip(gercek, [1.2 * (float(d[int(round(dmer[k][0])), int(round(dmer[k][1]))]) or Dm) for k in gercek])})
    return H, dict(dugum=len(gercek), cizgi=len(cizgiler), Dm=round(Dm, 1))
