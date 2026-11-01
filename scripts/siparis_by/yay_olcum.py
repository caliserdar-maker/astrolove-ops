#!/usr/bin/env python3
"""YD Starlit yayi olcumu (Serdar 1 Kas, Denetim 20261101B: "YD ORNEK3: elips hatali"). ETSY YOK. numpy + OpenCV (scipy yok).
sirt(): yayin sirti (en parlak cizgi), her 0,25 derecede yaricap dogrultusunda alt-piksel tepe (parabol); dar bant (+-14 px @2400) bir onceki
        egri etrafinda; kontrast (tepe - bant disi halka medyani) >= 25; tepe yildizi sektoru 258-282 haric (yildiz yayin ustunde).
        Yinelemeli: yerel kayan medyandan > 3 px sapan sirt noktasi (yay ustundeki isiltilar) atilir.
daire_otur / elips_otur: tum sirt noktalarina geometrik en kucuk kareler (Gauss-Newton); sapma = noktanin egriye uzakligi.
kiyas(): iki sirt (ornegin eski 8x10 ve yeni cikti, yeni olcekli ise @2400'e indirgenir) ayni acida (+-0,13 derece) radyal fark.
Yontem kaynagi: kendi olcumumuz (eski 8x10 1_Starlit_8x10_300ppi.png, KOD_REF e3d168ce)."""
import numpy as np
import cv2

HARIC = (258.0, 282.0)
YUMUSAK = 1.0     # yol tablosu Gauss sigma (ornek = 0,25 derece). Yerel olcum 1 Kas (TEGET 0,5): komsu fark en buyuk 1,26 px, kapi en buyuk 1,39 px (FAIL, 6/802 aci; taneli 1,75-3,25 ve 14 derece). YUMUSAK ~0 + TEGET 0: kapi 0,49 px PASS ama yol sirt gurultusunu kopyalar (komsu sicrama 5,8 px). Karar Serdar'da.


def gri(img):
    a = img.astype(np.float32)
    return a[..., 0] * 0.5 + a[..., 1] * 0.4 + a[..., 2] * 0.1


TEGET = 0.5      # derece: radyal profil +- bu acida 9 profilin ortalamasi (noktali / taneli bolgede sirt taneler arasinda atlamasin;
                 # yay egriligi yanliligi ~ L^2 / (8 r) = 16^2 / 7440 = 0,03 px @2400; yerel olcum 1 Kas: TEGET 0'da komsu sirt farki 5,8 px'e cikiyordu)


def _tepe(g, cx, cy, th, r0, bant, esik):
    t = np.radians(th)
    rs = np.arange(r0 - bant, r0 + bant, 0.25)
    ts = np.radians(th + np.linspace(-TEGET, TEGET, 9)) if TEGET > 0 else np.array([t])
    xs = cx + rs[None] * np.cos(ts)[:, None]; ys = cy + rs[None] * np.sin(ts)[:, None]
    v = cv2.remap(g, xs.astype(np.float32), ys.astype(np.float32), cv2.INTER_LINEAR).mean(0)
    v = cv2.GaussianBlur(v[None], (0, 0), 2)[0]
    j = int(v.argmax())
    if j in (0, len(v) - 1):
        return None
    rr = np.r_[np.arange(r0 - 2.5 * bant, r0 - 1.6 * bant, 1.0), np.arange(r0 + 1.6 * bant, r0 + 2.5 * bant, 1.0)]
    zb = cv2.remap(g, (cx + rr * np.cos(t)).astype(np.float32)[None], (cy + rr * np.sin(t)).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
    k = float(v[j] - np.median(zb))
    if k < esik:
        return None
    y0, y1, y2 = v[j - 1], v[j], v[j + 1]
    den = y0 - 2 * y1 + y2
    return rs[j] + (0.5 * (y0 - y2) / den if den != 0 else 0.0) * 0.25, k


def tablo_r(tab, th):
    n = len(tab)
    return np.interp(np.asarray(th) % 360, np.arange(n + 1) * 360.0 / n, np.r_[tab, tab[:1]])


def sirt(g, cx, cy, tab, k=1.0, adim=0.25, bant=14.0, esik=25.0, tur=3, haric=HARIC):
    """-> P (aci, x, y, r, kontrast) ; tab: merkez etrafinda yaricap tablosu (olcekli goruntude). Yinelemeli aykiri atma."""
    P = None
    for _ in range(tur):
        sat = []
        for th in np.arange(0, 360, adim):
            if haric and haric[0] <= th <= haric[1]:
                continue
            r0 = float(tablo_r(tab, th))
            x = _tepe(g, cx, cy, th, r0, bant * k, esik)
            if x:
                t = np.radians(th)
                sat.append((th, cx + x[0] * np.cos(t), cy + x[0] * np.sin(t), x[0], x[1]))
        P = np.array(sat)
        if len(P) < 50:
            return P
        # yerel kayan medyan (21 ornek = ~5 derece; sirala, dairesel) ve 3 px uzerini at
        r = P[:, 3]; n = len(r); w = 10
        ek = np.r_[r[-w:], r, r[:w]]
        med = np.array([np.median(ek[i:i + 2 * w + 1]) for i in range(n)])
        P = P[np.abs(r - med) <= 3.0 * k]
        tab = tablo_yap(P, len(tab))
    return P


def tablo_yap(P, n=1440, yumusak=1.0):
    """sirt noktalarindan dairesel yaricap tablosu (n deger); bos acilar dairesel dogrusal; kucuk Gauss yumusatma (sigma = yumusak ornek)"""
    ang, r = P[:, 0], P[:, 3]
    o = np.argsort(ang); ang, r = ang[o], r[o]
    a = np.arange(n) * 360.0 / n
    tab = np.interp(a, np.r_[ang - 360, ang, ang + 360], np.r_[r, r, r])
    if yumusak > 0:
        w = int(4 * yumusak) + 1
        ek = np.r_[tab[-w:], tab, tab[:w]]
        tab = np.convolve(ek, cv2.getGaussianKernel(2 * w + 1, yumusak).ravel(), "same")[w:-w]
    return tab


def bos_aci(P):
    ang = np.sort(P[:, 0]); b = np.diff(np.r_[ang, ang[0] + 360]); i = int(np.argmax(b))
    return [round(float(ang[i]) % 360, 2), round(float(ang[i] + b[i]) % 360, 2)]


def daire_otur(xy):
    A = np.c_[2 * xy[:, 0], 2 * xy[:, 1], np.ones(len(xy))]
    s = np.linalg.lstsq(A, xy[:, 0] ** 2 + xy[:, 1] ** 2, rcond=None)[0]
    p = np.array([s[0], s[1], np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2)])
    for _ in range(30):                                   # geometrik Gauss-Newton
        dx, dy = xy[:, 0] - p[0], xy[:, 1] - p[1]; d = np.hypot(dx, dy)
        f = d - p[2]; J = np.c_[-dx / d, -dy / d, -np.ones(len(d))]
        p = p - np.linalg.lstsq(J, f, rcond=None)[0]
    d = np.abs(np.hypot(xy[:, 0] - p[0], xy[:, 1] - p[1]) - p[2])
    return dict(cx=float(p[0]), cy=float(p[1]), r=float(p[2])), d


def elips_mesafe(xy, e, n=14400):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ca, sa = np.cos(np.radians(e["aci"])), np.sin(np.radians(e["aci"]))
    ex = e["cx"] + e["a"] * np.cos(t) * ca - e["b"] * np.sin(t) * sa
    ey = e["cy"] + e["a"] * np.cos(t) * sa + e["b"] * np.sin(t) * ca
    out = np.empty(len(xy))
    for i in range(0, len(xy), 256):
        q = xy[i:i + 256]
        out[i:i + 256] = np.sqrt(((q[:, None, 0] - ex[None]) ** 2 + (q[:, None, 1] - ey[None]) ** 2).min(1))
    return out


def elips_otur(xy):
    (cx, cy), (w, h), an = cv2.fitEllipse(xy.astype(np.float32))
    p = np.array([cx, cy, w / 2, h / 2, an], float)

    def f(p):
        ca, sa = np.cos(np.radians(p[4])), np.sin(np.radians(p[4]))
        x, y = xy[:, 0] - p[0], xy[:, 1] - p[1]
        u, v = x * ca + y * sa, -x * sa + y * ca
        th = np.arctan2(v * p[2], u * p[3])
        return np.hypot(u - p[2] * np.cos(th), v - p[3] * np.sin(th)) * np.sign(np.hypot(u / p[2], v / p[3]) - 1)
    for _ in range(40):                                   # sayisal Jacobian Gauss-Newton
        f0 = f(p); J = np.empty((len(xy), 5))
        for i, h_ in enumerate((1e-3, 1e-3, 1e-3, 1e-3, 1e-4)):
            q = p.copy(); q[i] += h_; J[:, i] = (f(q) - f0) / h_
        dp = np.linalg.lstsq(J, -f0, rcond=None)[0]; p = p + dp
        if np.abs(dp).max() < 1e-6:
            break
    e = dict(cx=float(p[0]), cy=float(p[1]), a=float(p[2]), b=float(p[3]), aci=float(p[4]))
    return e, elips_mesafe(xy, e)


def ozet(x):
    x = np.asarray(x)
    return dict(medyan=round(float(np.median(x)), 3), p95=round(float(np.percentile(x, 95)), 3), en_buyuk=round(float(x.max()), 3), n=int(len(x)))


def kiyas(P_eski, P_yeni, cx, cy, k=1.0, oy=0.0, tol=0.13):
    """yeni sirt -> @2400 (x / k, (y - oy) / k); eski ile ayni acida (merkez cx, cy @2400) radyal fark. -> (ozet, [(aci, fark)])"""
    xn, yn = P_yeni[:, 1] / k, (P_yeni[:, 2] - oy) / k
    an = (np.degrees(np.arctan2(yn - cy, xn - cx)) + 360) % 360; rn = np.hypot(xn - cx, yn - cy)
    ae = (np.degrees(np.arctan2(P_eski[:, 2] - cy, P_eski[:, 1] - cx)) + 360) % 360; re_ = np.hypot(P_eski[:, 1] - cx, P_eski[:, 2] - cy)
    o = np.argsort(ae); ae, re_ = ae[o], re_[o]
    out = []
    for a, r in zip(an, rn):
        j = int(np.searchsorted(ae, a))
        for jj in ((j - 1) % len(ae), j % len(ae)):
            if abs(((ae[jj] - a + 180) % 360) - 180) <= tol:
                out.append((float(a), float(r - re_[jj]))); break
    out = np.array(out)
    return ozet(np.abs(out[:, 1])), out


def isilti_sektorleri(g, cx, cy, tab, esik=100.0, en_az=3.0, pay=1.0):
    """yay USTUNDEKI buyuk isilti yildizlari (isinlari yayin iki yanina tasar): her 0,25 derecede yay bandi DISI (r +- 12..30) p90 parlaklik;
    p90 > (tum acilarin medyani + esik) ve ardisik genislik >= en_az derece olan sektorler, +- pay derece. Bu acilarda sirt yildizin
    isinlarina kayar (gercek yay geometrisi degil): yol komsu acilardan ara degerle, kapi bu acilari olcmez (listelenir)."""
    ang = np.arange(0, 360, 0.25); dis = np.empty(len(ang))
    for i, th in enumerate(ang):
        t = np.radians(th); r0 = float(tablo_r(tab, th))
        rr = np.r_[np.arange(r0 - 30, r0 - 12, 1.0), np.arange(r0 + 12, r0 + 30, 1.0)]
        v = cv2.remap(g, (cx + rr * np.cos(t)).astype(np.float32)[None], (cy + rr * np.sin(t)).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        dis[i] = np.percentile(v, 90)
    tepe = ang[dis > np.median(dis) + esik]
    gr = []
    for a in tepe:
        if gr and a - gr[-1][1] <= 2.0:
            gr[-1][1] = a
        else:
            gr.append([a, a])
    return [(round(a0 - pay, 2), round(a1 + pay, 2)) for a0, a1 in gr if a1 - a0 >= en_az]


def sektorde(ang, sek):
    ang = np.asarray(ang) % 360
    m = np.zeros(ang.shape, bool)
    for a0, a1 in sek:
        m |= ((ang - a0) % 360) <= ((a1 - a0) % 360)
    return m


def eski_yol(eski, seed):
    """eski 8x10'dan yayin gercek yolu: seed daire (cx, cy, r) -> merkez = sirt noktalarinin geometrik daire merkezi; tablo 0,25 derece."""
    g = gri(eski)
    cx, cy, r = seed
    tab = np.full(1440, float(r))
    P = sirt(g, cx, cy, tab, bant=40.0, esik=25.0, tur=2)          # genis ilk bant (seed dairesi yanlarda 10+ px sapiyordu)
    d, _ = daire_otur(P[:, 1:3])
    cx, cy = d["cx"], d["cy"]
    tab = np.full(1440, d["r"])
    for _ in range(3):
        P = sirt(g, cx, cy, tab, bant=14.0, esik=25.0, tur=2)
        tab = tablo_yap(P, 1440, yumusak=0.5)
    sek = isilti_sektorleri(g, cx, cy, tab)
    Pt = P[~sektorde(P[:, 0], sek)]
    tab = tablo_yap(Pt, 1440, yumusak=YUMUSAK)              # isilti sektorlerinde komsu acilardan ara deger
    return dict(cx=cx, cy=cy, r=tab, bos=bos_aci(P), P=P, P_kapi=Pt, isilti=sek)
