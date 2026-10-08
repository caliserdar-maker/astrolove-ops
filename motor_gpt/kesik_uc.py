# Kesik uc kapisi (8 Eki 2026, Serdar gozle buldu: CAPRICORN_SAGITTARIUS ok ucu ve kemer tepesi duz cizgiyle kesik).
# Olcu: alfanin goruntu/kutu KENARINA degdigi her parca icin kenardaki genislik w0 ve D px iceride ayni parcanin genisligi wD.
#   Dogal uc / teget tepe kenara cok dar degir (w0 << wD; yuvarlak tepe icin w0/wD ~ 0.25), kesik uc kenara tam genislikte
#   degir (w0 ~ wD). KESIK: w0 >= MIN_W ve w0 / wD >= ORAN.
# Ayrica kaynakta olup sonucta olmayan altin (kenara bitisik) olculur.
# Kullanim (modul): kesikler(alfa_uint8) -> [dict(kenar, konum, w0, wD, oran)]
import numpy as np
D, MIN_W, ORAN = 8, 8, 0.5
def _kosular(satir):
    m = np.r_[False, satir, False].astype(np.int8); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1))
def kesikler(a, esik=127):
    m = a > esik; H, W = m.shape; out = []
    kenarlar = {'ust': (m[0], m[D]), 'alt': (m[-1], m[-1 - D]), 'sol': (m[:, 0], m[:, D]), 'sag': (m[:, -1], m[:, -1 - D])}
    for ad, (k0, kD) in kenarlar.items():
        ic = _kosular(kD)
        for a0, a1 in _kosular(k0):
            w0 = a1 - a0 + 1
            ust = [(b0, b1) for b0, b1 in ic if b1 >= a0 - 2 and b0 <= a1 + 2]       # iceride ayni parca
            wD = max([b1 - b0 + 1 for b0, b1 in ust], default=0)
            oran = w0 / max(wD, 1)
            if w0 >= MIN_W and oran >= ORAN:
                orta = (a0 + a1) // 2
                xy = {'ust': (orta, 0), 'alt': (orta, H - 1), 'sol': (0, orta), 'sag': (W - 1, orta)}[ad]
                out.append(dict(kenar=ad, x=int(xy[0]), y=int(xy[1]), w0=int(w0), wD=int(wD), oran=round(float(oran), 2)))
    return out
def kenar_temas(a, esik=127):
    m = a > esik
    return dict(ust=int(m[0].sum()), alt=int(m[-1].sum()), sol=int(m[:, 0].sum()), sag=int(m[:, -1].sum()))
