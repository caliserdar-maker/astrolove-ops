#!/usr/bin/env python3
"""ESKI YOL (CI + WP) YENI "&" (Serdar 10 Eki, B2).

Sekil: onayli ChatGPT & (siparis-gpt motor_gpt/amp, AMP_MANIFEST AMP_KAYNAK sha256 0131...434de; 8 Eki onayli, ders 174-181).
Renk / doku / kabartma: tagline harfleriyle AYNI fonksiyon. Eski yol tagline'i pilot12.tagline_plaka -> pilot12.ciz_cap (maske)
-> altin_sekil (profil + glif kabartmasi) ile cizer. Bu modul yalniz ciz_cap'i sarar: metinde "&" varsa maskede fontun &
glifi yerine onayli & alfasi konur; boyama ayni kodla yapilir (CI kendi murekkebi, WP bakir kabartmasi katmanla tasinir).
Eski yol kodu (renk_ref, kisisel-v1, WP 360cbef) DEGISMEZ; sarma calisma aninda.

Yerlesim (ders 175, 180; motor_gpt/amp_tagline.py ile ayni kural, eski yolun cizim yontemiyle):
  - & murekkep yuksekligi = ayni puntoda "A" buyuk harf murekkep yuksekligi
  - & ile komsu kelime murekkep boslugu = "<onceki kelime> and <sonraki kelime>" (ayni ciz_cap ile) iki boslugun ortalamasi
  - & murekkep alti = tagline tabani (ciz_cap "T" taban satiri)

Kapi (kapi_amp): son JPG'de BAGIMSIZ. Beklenen satir siparis metninden ayni kuralla cizilir, sayfadaki satira olcek + kayma
aramasiyla oturtulur (eleman basina yerel ince ayar). f: her & IoU >= 0.90 (onayli sekle); d: her kelime grubu IoU >= ESIK_D;
renk: & cekirdegi ile harf cekirdegi ortalama RGB dE76 <= 5.0 (WP a_renk mantigi); leke: & cekirdeginde harflerin ayni satir
rengine gore |dL*| > 15 kumesi <= 0.5 * kalinlik^2.
"""
import hashlib, json, os
from pathlib import Path
import numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
KOK = Path(__file__).resolve().parent / 'amp'
ESIK_F, ESIK_D, ESIK_RENK, ESIK_LEKE_DL, ESIK_FARK = 0.90, 0.85, 5.0, 15.0, 1.0
KAYIT = []          # ciz_cap sarmasinin son cizimleri (rapor)


def amp_alfa():
    """Onayli & alfasi (0..1). sha256 manifestle denetlenir; tutmazsa HATA."""
    man = json.loads((KOK / 'AMP_MANIFEST.json').read_text())
    b = (KOK / 'AMP_ALFA.png').read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if h != man['AMP_ALFA.png']['sha256']:
        raise SystemExit(f'HATA AMP_ALFA sha256 {h} != manifest')
    return np.asarray(Image.open(KOK / 'AMP_ALFA.png')).astype(np.float32) / 65535


def _bos_kosular(a):
    """Murekkep (>127) sutunlari arasindaki bosluklar (yalniz murekkep ARASI)."""
    kol = (a > 127).any(0); k = np.r_[False, ~kol, False].astype(np.int8); d = np.diff(k)
    s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    xs = np.nonzero(kol)[0]
    if not len(xs):
        return []
    x0, x1 = xs.min(), xs.max() + 1
    return [int(b - a_) for a_, b in zip(s, e) if a_ > x0 and b < x1]


def amp_olcekli(A, cap):
    """& alfasi murekkep yuksekligi cap olacak sekilde (INTER_AREA), uint8; murekkep kutusu (>127)."""
    ys, xs = np.nonzero(A > 0.5); h = ys.max() + 1 - ys.min(); s = cap / h
    hh, ww = max(int(round(A.shape[0] * s)), 2), max(int(round(A.shape[1] * s)), 2)
    A8 = np.round(cv2.resize(A, (ww, hh), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8)
    ys, xs = np.nonzero(A8 > 127)
    return A8, (int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1), float(s)


def dizgi(ciz, fp, wght, punto, metin, A):
    """ciz = eski yolun ciz_cap(fp, wght, punto, metin) -> (L maske kirpim, cap ustu, taban). Doner: ayni sozlesme + bilgi.
    bilgi['elemanlar'] = [(tur, x0, x1)] cikti kirpiminda murekkep sutun araliklari (tur 'metin' / 'amp')."""
    parcalar = [p.strip() for p in metin.split('&')]
    rA = ciz(fp, wght, punto, 'A')
    cap = int(rA[0].height)                       # "A" murekkep yuksekligi (kirpim = murekkep kutusu)
    A8, ink, s = amp_olcekli(A, cap)
    gaps, olcum = [], []
    for i in range(len(parcalar) - 1):
        once = parcalar[i].split()[-1] if parcalar[i] else ''
        sonra = parcalar[i + 1].split()[0] if parcalar[i + 1] else ''
        if not once and not sonra:
            once, sonra = 'Forever', 'Always'
        m = ' '.join(x for x in (once, 'and', sonra) if x)
        r = sorted(_bos_kosular(np.asarray(ciz(fp, wght, punto, m)[0])), reverse=True)[:int(bool(once)) + int(bool(sonra))]
        gaps.append(int(round(float(np.mean(r))))); olcum.append(dict(metin=m, bosluklar=[int(x) for x in r]))
    dizi = []                                     # (tur, L dizisi, taban satiri (murekkep alti = taban), cap ustu)
    for i, p in enumerate(parcalar):
        if p:
            cr, cu, ct = ciz(fp, wght, punto, p)
            dizi.append(('metin', np.asarray(cr), ct, cu))
        if i < len(parcalar) - 1:
            dizi.append(('amp', A8[ink[2]:ink[3], ink[0]:ink[1]], ink[3] - ink[2], None))
    ai, c = [None] * len(dizi), 0                 # & sira no
    for j, d in enumerate(dizi):
        if d[0] == 'amp':
            ai[j] = c; c += 1
    ara = []                                      # her komsu cift arasi: o &'in boslugu (iki metin yan yana olmaz)
    for j in range(len(dizi) - 1):
        ara.append(gaps[ai[j]] if ai[j] is not None else gaps[ai[j + 1]] if ai[j + 1] is not None else gaps[0])
    yuk = max(d[1].shape[0] for d in dizi) * 2 + 40; B = yuk // 2 + 20
    gen = sum(d[1].shape[1] for d in dizi) + sum(ara) + 40
    tuval = np.zeros((yuk, gen), np.uint8)
    xi, el, cu_t = 20, [], None
    for j, (t, a, tb, cu) in enumerate(dizi):
        y0 = B - tb
        sl = tuval[y0:y0 + a.shape[0], xi:xi + a.shape[1]]; np.maximum(sl, a, out=sl)
        el.append((t, xi, xi + a.shape[1]))
        if t == 'metin' and cu_t is None:
            cu_t = y0 + cu
        xi += a.shape[1] + (ara[j] if j < len(ara) else 0)
    if cu_t is None:                              # yalniz & (metin yok): T ustu ayni puntodan
        rT = ciz(fp, wght, punto, 'T'); cu_t = B - (rT[2] - rT[1])
    ys, xs = np.nonzero(tuval > 40)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = Image.fromarray(tuval[y0:y1, x0:x1])
    bilgi = dict(punto=int(punto), metin_parcalari=parcalar, buyuk_harf_yuksekligi_px=cap, amp_yukseklik_px=int(ink[3] - ink[2]),
                 amp_genislik_px=int(ink[1] - ink[0]), amp_olcek=round(s, 4), amp_bosluklari_px=gaps, bosluk_olcumu=olcum,
                 elemanlar=[(t, int(a - x0), int(b - x0)) for t, a, b in el], taban=int(B - y0))
    return out, int(cu_t - y0), int(B - y0), bilgi


def kur(pilot12, A=None):
    """pilot12.ciz_cap'i sarar (tagline_plaka bu adi cagirir). '&' olmayan metin eskisiyle AYNI."""
    A = amp_alfa() if A is None else A
    eski = getattr(pilot12.ciz_cap, 'eski', pilot12.ciz_cap)

    def ciz_cap(fp, wght, punto, metin):
        if '&' not in metin:
            return eski(fp, wght, punto, metin)
        cr, cu, ct, bilgi = dizgi(eski, fp, wght, punto, metin, A)
        KAYIT.append(bilgi)
        return cr, cu, ct
    ciz_cap.eski = eski
    pilot12.ciz_cap = ciz_cap
    return eski


# ------------------------------------------------------------------ kapi (son JPG, bagimsiz)
def _lab(rgb):
    return cv2.cvtColor((np.clip(rgb, 0, 255) / 255).astype(np.float32).reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)


def _iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def _kaydir(m, dx, dy):
    return np.roll(np.roll(m, dy, 0), dx, 1)


def _beklenen(eski_ciz, fp, wght, metin, cap_px, A, glif=False):
    """Beklenen satir maskesi (0..1) ve eleman araliklari; 'A' yuksekligi ~cap_px olacak punto ile."""
    lo, hi = 4, 900
    for _ in range(24):
        mid = (lo + hi) / 2
        h = eski_ciz(fp, wght, max(int(round(mid)), 4), 'A')[0].height
        lo, hi = (mid, hi) if h < cap_px else (lo, mid)
        if hi - lo < 0.5:
            break
    p = max(int(round((lo + hi) / 2)), 4)
    if '&' in metin and not glif:
        cr, cu, ct, bilgi = dizgi(eski_ciz, fp, wght, p, metin, A)
        el = bilgi['elemanlar']
    else:
        cr, cu, ct = eski_ciz(fp, wght, p, metin); bilgi = {'punto': p}
        el = [('metin', 0, cr.width)]
    return np.asarray(cr).astype(np.float32) / 255, el, bilgi


def _murekkep(L, beklenen_bolge):
    """Murekkep derinligi: yerel kagit (murekkep bolgesi boyanmis) - L. Kagit = beklenen murekkep disi, inpaint."""
    m = cv2.dilate(beklenen_bolge.astype(np.uint8), np.ones((9, 9), np.uint8))
    bg = cv2.inpaint(np.clip(L * 2.55, 0, 255).astype(np.uint8), m, 7, cv2.INPAINT_TELEA).astype(np.float32) / 2.55
    return bg - L


def kapi_amp(rgb, metin, eski_ciz, fp, wght, A=None, y_bant=(0.76, 0.96), kesit=None, glif=False):
    """rgb: son sayfa (H, W, 3) uint8. Doner rapor dict (f, d, renk, leke, PASS). glif=True: beklenen = fontun & glifi
    (yalniz karsilastirma / eski sayfada & yeri; kapi karari icin KULLANILMAZ)."""
    A = amp_alfa() if A is None else A
    H, W = rgb.shape[:2]
    ya, yb = int(H * y_bant[0]), int(H * y_bant[1])
    R = rgb[ya:yb].astype(np.float32)
    L = _lab(R).reshape(R.shape[:2] + (3,))[..., 0]
    koyu = cv2.GaussianBlur(L, (0, 0), 25) - L                       # kaba murekkep (yerel kagittan koyu)
    # 1) kaba olcek + konum: kucuk olcekte cok olcekli sablon arama (koyuluk haritasi ~ beklenen maske)
    f4 = 4.0
    K4 = cv2.resize(np.clip(koyu, 0, 40), None, fx=1 / f4, fy=1 / f4, interpolation=cv2.INTER_AREA)
    cap0 = 71.0 * W / 2400
    E0, _, _ = _beklenen(eski_ciz, fp, wght, metin, cap0, A, glif)
    en_iyi = None
    for s in np.arange(0.70, 1.31, 0.02):
        e = cv2.resize(E0, None, fx=s / f4, fy=s / f4, interpolation=cv2.INTER_AREA)
        if e.shape[0] >= K4.shape[0] or e.shape[1] >= K4.shape[1]:
            continue
        r = cv2.matchTemplate(K4, e, cv2.TM_CCOEFF_NORMED)
        _, v, _, loc = cv2.minMaxLoc(r)
        if en_iyi is None or v > en_iyi[0]:
            en_iyi = (v, s, loc)
    if en_iyi is None:
        return {'PASS': False, 'hata': 'satir bulunamadi'}
    # 2) ince: bulunan olcekte beklenen satir yeniden cizilir, tam cozunurlukte +-%2 olcek, +-8 px
    v0, s0, loc = en_iyi
    en = None
    for ds in np.arange(-0.02, 0.0201, 0.005):
        E, el, bilgi = _beklenen(eski_ciz, fp, wght, metin, cap0 * (s0 + ds), A, glif)
        x0, y0 = int(loc[0] * f4), int(loc[1] * f4)
        xa, xb, ya2, yb2 = max(0, x0 - 24), min(W, x0 + E.shape[1] + 24), max(0, y0 - 24), min(yb - ya, y0 + E.shape[0] + 24)
        r = cv2.matchTemplate(np.clip(koyu[ya2:yb2, xa:xb], 0, 40), E, cv2.TM_CCOEFF_NORMED)
        _, v, _, l2 = cv2.minMaxLoc(r)
        if en is None or v > en[0]:
            en = (v, E, el, bilgi, xa + l2[0], ya2 + l2[1])
    v, E, el, bilgi, ex, ey = en
    h, w = E.shape
    pad = int(0.5 * bilgi.get('buyuk_harf_yuksekligi_px', h))
    bx0, by0, bx1, by1 = max(0, ex - pad), max(0, ey - pad), min(W, ex + w + pad), min(yb - ya, ey + h + pad)
    Lb, Rb = L[by0:by1, bx0:bx1], R[by0:by1, bx0:bx1]
    Eb = np.zeros(Lb.shape, np.float32); Eb[ey - by0:ey - by0 + h, ex - bx0:ex - bx0 + w] = E
    D = _murekkep(Lb, Eb > 0.02)
    cek = Eb > 0.95
    d_cek = float(np.median(D[cek])) if cek.any() else 0.0
    P = D > 0.5 * d_cek                                              # sayfa murekkebi (alfa ~ 0.5 esigi)
    Bm = Eb > 0.5
    rap = {'eslesme': round(float(v), 3), 'kaba_eslesme': round(float(v0), 3), 'olcek': round(float(s0), 3),
           'konum_px': [int(ex), int(ya + ey)], 'murekkep_derinligi': round(d_cek, 2), 'punto': bilgi.get('punto'),
           'f': [], 'd': [], 'renk': [], 'leke': []}
    cap = bilgi.get('buyuk_harf_yuksekligi_px') or h
    t = max(2, int(round(0.04 * cap)))
    # elemanlar: her & ve her KELIME ayri (tek harf hatasi kelime IoU'sunu dusurur); kelime araligi onek cizimiyle
    p_ = bilgi.get('punto')
    metinler = [q for q in ([x.strip() for x in metin.split('&')] if '&' in metin and not glif else [metin]) if q]
    gen = lambda q: eski_ciz(fp, wght, p_, q)[0].width
    el2, mi = [], 0
    for tur, a, b in el:
        if tur == 'amp':
            el2.append(('amp', '&', a, b)); continue
        ks = metinler[mi].split(); mi += 1
        for i, kw in enumerate(ks):
            sag = gen(' '.join(ks[:i + 1])); el2.append(('amp' if kw == '&' else 'metin', kw, a + sag - gen(kw), a + sag))
    harf = np.zeros_like(Bm)
    for tur, ad, a, b in el2:
        if tur == 'metin':
            harf[:, max(0, ex - bx0 + a - t):ex - bx0 + b + t] |= Bm[:, max(0, ex - bx0 + a - t):ex - bx0 + b + t]
    k = max(2, int(0.15 * cap))
    rap['elemanlar'] = []

    def iou_ara(e, x0, y0, sc_liste, dxs, dys):
        en = (-1.0, None)
        for sc in sc_liste:
            es = cv2.resize(e, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR) > 0.5 if sc != 1.0 else e > 0.5
            hh, ww = es.shape
            ox, oy = x0 + (e.shape[1] - ww) // 2, y0 + (e.shape[0] - hh) // 2
            for dy in dys:
                for dx in dxs:
                    X, Y = ox + dx, oy + dy
                    if X < 0 or Y < 0 or X + ww > P.shape[1] or Y + hh > P.shape[0]:
                        continue
                    Ps = P[Y:Y + hh, X:X + ww]
                    u = (es | Ps).sum()
                    i = float((es & Ps).sum() / u) if u else 0.0
                    if i > en[0]:
                        en = (i, (sc, dx, dy, X, Y, es))
        return en
    for tur, ad, a, b in el2:
        X0, X1 = max(0, ex - bx0 + a - t), ex - bx0 + b + t
        rr = np.nonzero((Eb[:, X0:X1] > 0.02).any(1))[0]              # eleman murekkep satirlari +-4 px (olcek payi)
        r0, r1 = max(0, int(rr.min()) - 4), min(Eb.shape[0], int(rr.max()) + 5)
        e = Eb[r0:r1, X0:X1]
        st_ = max(1, k // 6)
        i1, q1 = iou_ara(e, X0, r0, (0.97, 0.985, 1.0, 1.015, 1.03), range(-k, k + 1, st_), range(-k, k + 1, st_))
        sc, dx0, dy0 = q1[0], q1[1], q1[2]
        i2, q2 = iou_ara(e, X0, r0, (sc - 0.005, sc, sc + 0.005), range(dx0 - st_, dx0 + st_ + 1), range(dy0 - st_, dy0 + st_ + 1))
        en_i, (sc, dx, dy, X, Y, es) = (i2, q2) if i2 >= i1 else (i1, q1)
        (rap['f'] if tur == 'amp' else rap['d']).append(round(en_i, 3))
        # yazim farki: hizali XOR'dan kenar seritleri (kalinligin yarisi) acilarak atilir; kalan en buyuk kume / kalinlik^2
        Ps_ = P[Y:Y + es.shape[0], X:X + es.shape[1]]
        dtw = cv2.distanceTransform(es.astype(np.uint8), cv2.DIST_L2, 3)
        kw = max(2.0, 2 * float(np.median(dtw[dtw > 0]))) if (dtw > 0).any() else 2.0
        ko = max(3, int(round(0.6 * kw)) | 1)
        xo = cv2.morphologyEx((es ^ Ps_).astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ko, ko)))
        n_, _, st2, _ = cv2.connectedComponentsWithStats(xo, 8)
        fk = int(st2[1:, 4].max()) if n_ > 1 else 0
        rap['elemanlar'].append({'tur': tur, 'iou': round(en_i, 3), 'olcek': round(sc, 3), 'kayma': [int(dx), int(dy)],
                                 'kutu': [int(bx0 + X), int(ya + by0 + Y), int(bx0 + X + es.shape[1]), int(ya + by0 + Y + es.shape[0])],
                                 'fark_kume': fk, 'fark_sinir': int(round(ESIK_FARK * kw * kw)), 'kalinlik': round(kw, 1),
                                 **({'kelime_no': len(rap['d'])} if tur == 'metin' else {})})
        if tur == 'amp':
            bk = np.zeros_like(Bm); bk[Y:Y + es.shape[0], X:X + es.shape[1]] = es
            dt = cv2.distanceTransform(bk.astype(np.uint8), cv2.DIST_L2, 3)
            kal = max(2.0, 2 * float(np.median(dt[dt > 0]))) if (dt > 0).any() else 2.0
            ac = dt >= max(1.5, 0.3 * kal)                           # & cekirdegi (kenardan kalinligin %30'u iceride)
            dth = cv2.distanceTransform(harf.astype(np.uint8), cv2.DIST_L2, 3)
            hc = dth >= max(1.5, 0.3 * kal)
            if ac.sum() < 30 or hc.sum() < 30:
                rap['renk'].append(None); rap['leke'].append(None); continue
            ma, mh = Rb[ac].mean(0), Rb[hc].mean(0)
            rap['renk'].append(round(float(np.sqrt(((_lab(ma[None]) - _lab(mh[None])) ** 2).sum())), 2))
            # leke: & cekirdegi L*, harf cekirdeginin AYNI satirdaki ortancasina gore
            satir = np.full(Lb.shape[0], np.nan, np.float32)
            for y in np.nonzero(hc.any(1))[0]:
                satir[y] = np.median(Lb[y][hc[y]])
            ok = ~np.isnan(satir)
            if ok.sum() >= 2:
                yy = np.arange(len(satir)); satir = np.interp(yy, yy[ok], satir[ok])
            sap = (np.abs(Lb - satir[:, None]) > ESIK_LEKE_DL) & ac
            n, lab, st, _ = cv2.connectedComponentsWithStats(sap.astype(np.uint8), 8)
            en_k = int(st[1:, 4].max()) if n > 1 else 0
            rap['leke'].append({'en_buyuk_kume': en_k, 'sinir': int(round(0.5 * kal * kal)), 'kalinlik': round(kal, 1),
                                'gecti': bool(en_k <= 0.5 * kal * kal)})
    rap['f_gecti'] = bool(rap['f'] and all(x >= ESIK_F for x in rap['f'])) if '&' in metin else None
    kel = [e for e in rap['elemanlar'] if e['tur'] == 'metin']
    rap['d_gecti'] = bool(kel and all(e['iou'] >= ESIK_D and e['fark_kume'] <= e['fark_sinir'] for e in kel))
    rap['renk_gecti'] = bool(rap['renk'] and all(x is not None and x <= ESIK_RENK for x in rap['renk'])) if '&' in metin else None
    rap['leke_gecti'] = bool(rap['leke'] and all(x and x['gecti'] for x in rap['leke'])) if '&' in metin else None
    rap['esik'] = {'f_iou': ESIK_F, 'd_iou': ESIK_D, 'd_fark_kume': 'kalinlik^2 x %.1f' % ESIK_FARK, 'renk_dE76': ESIK_RENK, 'leke_dL': ESIK_LEKE_DL}
    rap['PASS'] = bool(rap['d_gecti'] and ('&' not in metin or (rap['f_gecti'] and rap['renk_gecti'] and rap['leke_gecti'])))
    if kesit:
        Image.fromarray(rgb[ya + by0:ya + by1, bx0:bx1]).save(kesit, quality=95, subsampling=0)
    return rap
