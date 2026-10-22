# Sirt surekliligi (7 Eki 2026, Serdar cizimi): her cizginin orta sirti baglantinin ICINDEN kesintisiz gecer.
# Kesismede iki sirt "+" / "X" gibi kesisir, Y'de kol sirti ana sirta katilir.
# Iskelet dallari gercek kavsaklarda en duz devam eden kol ciftiyle birbirine baglanip TEK sirali yol (zincir) olur;
# eslesmeyen kol kavsak merkezinde biter (Y). Her zincirin orta cizgisi yumusatilip yogun orneklenir.
# Her alt ornek noktasinda zincir basina goreli yukseklik h = 1 - mesafe / yari kalinlik; en yuksek zincir baskin,
# yon = noktadan o zincirin orta cizgisine. Goreli yukseklik: her sirt ayni yukseklikte -> kesismede ikisi de gorunur.
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d

SIG = float(__import__('os').environ.get('SIRT_SIG', '25'))      # orta cizgi yumusatma (px): baglanti kirigi kat cizgisi yapmasin
def _yogun(p, w, adim=0.3, kapali=False):
    m = 'wrap' if kapali else 'nearest'
    if len(p) > 7:
        p = np.c_[gaussian_filter1d(p[:, 0], SIG, mode=m), gaussian_filter1d(p[:, 1], SIG, mode=m)]
        w = gaussian_filter1d(w, 4, mode=m)
    if kapali: p = np.r_[p, p[:1]]; w = np.r_[w, w[:1]]
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    if s[-1] < 1e-6: return p[:1], w[:1]
    t = np.arange(0, s[-1], adim)
    return np.c_[np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], np.interp(t, s, w)

def zincirler(A01):
    """Hedef (ChatGPT ornegi, 7 Eki): kesismede iki tepe hatti TEK noktada kesisir, Y'de kol tepesi ana tepeye akar.
    Kavsak sisme bolgesindeki (zon) iskelet parcalari atilir; eslesen kollar DUZ baglanti ile birlesir (iki duz baglanti
    tek noktada kesisir), eslesmeyen kol ana baglantinin uzerindeki noktaya uzatilir."""
    from serit import serit_yukseklik
    serit_yukseklik(A01)
    G = serit_yukseklik.graf
    D, dmer, gercek, ES, KOL, CAP, d, ZON = G['dallar'], G['dmer'], G['gercek'], G['ESLES'], G['KOL'], G['CAPf'], G['d'], G['ZON']
    def kol_yolu(bi, uc):
        """dalin uc tarafindan disari dogru yolu (x, y) ve kalinlik; uc gercek kavsaktaysa zon ici atilir"""
        yol = D[bi]['yol'] if uc == 0 else D[bi]['yol'][::-1]
        P = np.c_[yol[:, 1] + 0.5, yol[:, 0] + 0.5].astype(np.float64)
        W = np.minimum(d[yol[:, 0], yol[:, 1]], CAP[yol[:, 0], yol[:, 1]]).astype(np.float64)
        if (bi, uc) in KOL:
            k = KOL[(bi, uc)][0]; cy, cx = dmer[k]
            r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
            ilk = int(np.argmax(r > ZON[k])) if (r > ZON[k]).any() else len(P) - 1
            P, W = P[ilk:], W[ilk:]
        return P, W
    # her gercek kavsak icin duz baglantilar (eslesen kol ciftleri)
    bag = {}
    for (bi, uc), (bj, ucj, k) in ES.items():
        if (bj, ucj, bi, uc) in [(a, b, c, e) for (a, b, c, e, _, _) in bag.get(k, [])]: continue
        Pa, Wa = kol_yolu(bi, uc); Pb, Wb = kol_yolu(bj, ucj)
        bag.setdefault(k, []).append((bi, uc, bj, ucj, (Pa[0], Wa[0]), (Pb[0], Wb[0])))
    def dogru(a, b, wa, wb, adim=1.0):
        n = max(2, int(np.ceil(np.hypot(*(b - a)) / adim)))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        return a + (b - a) * t, wa + (wb - wa) * t[:, 0]
    def hedef_nokta(k, A=None, dA=None):
        """eslesmeyen kolun bitecegi nokta ve ana tepe yonu. Kol tepesi ana tepeye TEGET katilir (referans Y):
        kavsak merkezinin ana baglanti uzerindeki izdusumunden, kolun akis yonunde biraz ilerideki nokta."""
        cy, cx = dmer[k]; m = np.array([cx, cy])
        best = None
        for (_, _, _, _, (a, wa), (b, wb)) in bag.get(k, []):
            v = b - a; L2 = max(np.dot(v, v), 1e-9); t = np.clip(np.dot(m - a, v) / L2, 0, 1); p = a + t * v
            dd = np.hypot(*(p - m))
            if best is None or dd < best[0]: best = (dd, a, b, wa, wb, t)
        if best is None: return m, 1.0, None
        _, a, b, wa, wb, t = best
        v = b - a; L = np.sqrt(max(np.dot(v, v), 1e-9)); u = v / L
        if dA is not None and np.dot(u, dA) < 0: u = -u
        sgn = 1.0 if np.dot(u, v) > 0 else -1.0
        t2 = np.clip(t + sgn * (0.45 * ZON[k]) / L, 0.02, 0.98)
        return a + t2 * v, wa + (wb - wa) * t2, u
    def egri(A, dA, T, uT, wa, wb, adim=1.0):
        """A'dan (yon dA) T'ye (yon uT) teget kubik egri"""
        Lc = 0.45 * np.hypot(*(T - A))
        C1 = A + dA * Lc; C2 = T - uT * Lc
        n = max(3, int(np.ceil(np.hypot(*(T - A)) * 1.3 / adim)))
        tt = np.linspace(0, 1, n, endpoint=False)[:, None]
        P = ((1 - tt) ** 3) * A + 3 * ((1 - tt) ** 2) * tt * C1 + 3 * (1 - tt) * tt * tt * C2 + (tt ** 3) * T
        return P, wa + (wb - wa) * tt[:, 0]
    def yon_son(P):
        k_ = min(len(P) - 1, 12)
        dv = P[-1] - P[-1 - k_] if k_ > 0 else np.array([1.0, 0.0])
        n = np.hypot(*dv); return dv / n if n > 0 else np.array([1.0, 0.0])
    ic = set(i for i, b in enumerate(D) if b['n'][0] and b['n'][0] == b['n'][1] and b['n'][0] in gercek)
    gor = set(ic); out = []
    def yurut(bi, giris_uc):
        P, W = [], []; kapali = False; uc_k = [False, False]
        bas = (bi, giris_uc)
        if bas in KOL and bas not in ES:                                  # eslesmeyen kol: ana tepe hattindan basla
            k = KOL[bas][0]; pa, wa = kol_yolu(bi, giris_uc)
            dA = -yon_son(pa[::-1][-13:]) if len(pa) > 1 else None          # kolun kavsaga dogru yonu
            dA = (pa[0] - pa[min(12, len(pa) - 1)]); dA = dA / max(np.hypot(*dA), 1e-9)
            p, w_, uT = hedef_nokta(k, pa[0], dA)
            w_ = 0.97 * min(float(w_), float(wa[0]))
            if uT is not None:
                seg, sw = egri(pa[0], dA, p, uT, float(wa[0]), float(w_)); seg, sw = seg[::-1], sw[::-1]
            else:
                seg, sw = dogru(p, pa[0], float(w_), wa[0])
            P.append(seg); W.append(sw); uc_k[0] = True
        while True:
            gor.add(bi)
            # dal: giris ucundan cikis ucuna, iki uctaki zon parcalari atilmis
            pa, wa = kol_yolu(bi, giris_uc)                               # giris tarafindan baslar
            pb, wb = kol_yolu(bi, 1 - giris_uc)                           # cikis tarafindan baslar (ters)
            n = len(D[bi]['yol']); kes_bas = n - len(pa); kes_son = n - len(pb)
            yol = D[bi]['yol'] if giris_uc == 0 else D[bi]['yol'][::-1]
            yol = yol[kes_bas:n - kes_son] if n - kes_son > kes_bas else yol[kes_bas:kes_bas + 1]
            Pd = np.c_[yol[:, 1] + 0.5, yol[:, 0] + 0.5].astype(np.float64)
            Wd = np.minimum(d[yol[:, 0], yol[:, 1]], CAP[yol[:, 0], yol[:, 1]]).astype(np.float64)
            P.append(Pd); W.append(Wd)
            cik = (bi, 1 - giris_uc)
            if cik in ES:
                bj, ucj, k = ES[cik]
                pn, wn = kol_yolu(bj, ucj)
                uN = pn[min(12, len(pn) - 1)] - pn[0]; uN = uN / max(np.hypot(*uN), 1e-9)   # sonraki kolun disari yonu
                seg, sw = dogru(Pd[-1], pn[0], Wd[-1], wn[0]); P.append(seg); W.append(sw)
                if bj in gor:
                    kapali = (bj, ucj) == bas; break
                bi, giris_uc = bj, ucj; continue
            if cik in KOL:                                                # eslesmeyen kol: ana tepe hattina uzat
                k = KOL[cik][0]; dA = yon_son(Pd)
                p, w_, uT = hedef_nokta(k, Pd[-1], dA)
                w_ = 0.97 * min(float(w_), float(Wd[-1]))
                if uT is not None:
                    seg, sw = egri(Pd[-1], dA, p, uT, float(Wd[-1]), float(w_))
                else:
                    seg, sw = dogru(Pd[-1], p, Wd[-1], float(w_))
                P.append(seg[1:]); W.append(sw[1:])
                P.append(p[None]); W.append(np.array([float(w_)])); uc_k[1] = True
            break
        return np.concatenate(P), np.concatenate(W), kapali, uc_k
    for bi in range(len(D)):
        if bi in gor: continue
        for uc in (0, 1):
            if (bi, uc) not in ES:
                P, W, k, u = yurut(bi, uc); out.append((*_yogun(P, np.maximum(W, 1.0), kapali=k), u)); break
    for bi in range(len(D)):
        if bi not in gor:
            P, W, k, u = yurut(bi, 0); out.append((*_yogun(P, np.maximum(W, 1.0), kapali=k), u))
    return out

def yon_alani_serit(A01):
    Z = zincirler(A01)
    sec = cv2.dilate((A01 > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ys, xs = np.nonzero(sec)
    agac = [(cKDTree(P), P, W, u) for P, W, u in Z if len(P)]
    # Serdar (7 Eki): YALNIZ cizgilerin orta sirtlari tepe; baska kat cizgisi yok, cizgiler arasi yumusak gecis.
    # Zincirler sert max yerine yumusak max ile birlesir: yon = sum(e_i * v_i) / sum(e_i), e_i = exp(B * (h_i - hmax)).
    # Tek zincirin kendi sirti (iki yuzu ayni zincir) keskin kalir; iki zincirin bulustugu yerde kat yerine yumusak gecis.
    B = float(__import__('os').environ.get('SIRT_YUMUSAK_B', '2000'))   # sert kat (alt ornekle 1 px yumusak); ara normal = parlak cizgi yapiyordu
    out = []
    for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        q = np.c_[xs + ox, ys + oy]
        HL, VL = [], []
        for T, P, W, u in agac:
            dist, idx = T.query(q, workers=-1, distance_upper_bound=4 * float(W.max()) + 20)
            ok = np.isfinite(dist)
            if not ok.any(): continue
            # MUTLAK yukseklik (gercek pah/egim): h = kalinlik - mesafe. Kavsakta biten kolun ucu ana sirttan alcak
            # oldugu icin ucun otesi ana cizginin altinda kalir (gaga/kesik olusmaz); kol tepesi ana tepeye akar.
            h = np.full(len(q), -np.inf, np.float32); h[ok] = 1.0 - dist[ok] / W[idx[ok]]   # goreli: her tepe ayni yukseklik, kesismede iki tepe tek noktada
            v = np.zeros((len(q), 2), np.float32)
            vv = P[idx[ok]] - q[ok]; n = np.maximum(np.hypot(vv[:, 0], vv[:, 1]), 1e-6)
            v[ok] = vv / n[:, None]
            HL.append(h); VL.append(v)
        Hm = np.max(np.stack(HL), 0) if HL else np.zeros(len(q))
        sx = np.zeros(len(q)); sy = np.zeros(len(q)); se = np.zeros(len(q))
        for h, v in zip(HL, VL):
            e = np.where(np.isfinite(h), np.exp(B * (h - Hm)), 0.0)
            sx += e * v[:, 0]; sy += e * v[:, 1]; se += e
        sx /= np.maximum(se, 1e-9); sy /= np.maximum(se, 1e-9)
        n = np.maximum(np.hypot(sx, sy), 1e-6)
        out.append(((sx / n).astype(np.float32), (sy / n).astype(np.float32)))
    yon_alani_serit.zincir = Z
    return (ys, xs), out
