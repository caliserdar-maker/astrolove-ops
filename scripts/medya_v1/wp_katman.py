#!/usr/bin/env python3
"""WARM PARCHMENT KATMAN YONTEMI (30 Eyl 2026, Serdar talimati). Etsy/Prodigi/musteri erisimi YOK.

Sorun: eski WP yolu dokulu parsomende eski yaziyi SILIP yeniden yaziyordu (leke, iz, isim satiri
bulunamamasi, sembol kaymasi; Drive TEMP/WP_KALIBRASYON_30EYL.md).
Yontem (SILME YOK):
  1) Ayni siparis duz zeminli renkte (Champagne Ivory; olmazsa Midnight Blue) mevcut hatla uretilir
     (tum kapilar o renkte kosar).
  2) Murekkep katmani = baski - ayni rengin temiz plate'i (fark; alfa renk modelinde ogrenilir).
  3) Zemin = yazisiz WP plate'i (slogan / eski iz kapisi: `plate_temizlik`).
  4) Murekkep WP'nin kendi murekkep rengiyle basilir. Geometri (bant bazli afin) ve renk eslemesi
     TAHMIN EDILMEZ: ayni ciftin onayli CI kaynagi ile onayli WP kaynagindaki ayni piksellerden ogrenilir.
        cikti = b(D) * P_wp + c(D),  D = hizalanmis (baski - P_ci)
     b, c: D'nin 3. derece polinomu (b skaler, c RGB); b=1, c=0 -> zemin, b=0 -> opak murekkep.
  5) Kimlik testi: kaynagin kendi burc adlari + slogani ile uretilen WP, onayli WP kaynagini yeniden
     uretmeli; fark (CIE76 dE) bant bazinda olculur (`fark_tablosu`).
"""
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
ESIK = 12.0               # murekkep: |dL| > ESIK (siparis_dosyasi.PLATE_ESIK ile ayni olcum)
MIN_ALAN = 40             # parsomen benegi eleme (edisyon_uret.MASKE_MIN_ALAN)
KENAR = 0.10              # sayfa kenar payi (edisyon_uret.MASKE_KENAR)
BOSLUK = 12               # bant ayirma: bu kadar bos satir -> yeni bant
PAY = 80                  # hizalama penceresi (bant disina)
RAMPA = (2.0, 6.0)        # max|D| bu araliktayken zemin -> model gecisi
DERECE = 3
ORNEK = 300000            # renk modeli icin piksel ornegi
IZ_MIN_ALAN = 20          # eski iz: bu alandan kucuk bilesen kenar kirintisidir (yeni glif kenari)


def dizi(x):
    if isinstance(x, np.ndarray):
        return x.astype(np.float32)
    im = x if isinstance(x, Image.Image) else Image.open(x)
    return np.asarray(im.convert('RGB')).astype(np.float32)


def boyutla(a, wh):
    if (a.shape[1], a.shape[0]) == tuple(wh):
        return a
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return np.asarray(im.resize(tuple(wh), Image.LANCZOS)).astype(np.float32)


def murekkep_maskesi(D, esik=ESIK, kenar=KENAR):
    import cv2
    m = np.abs(D @ LUMA) > esik
    if kenar:
        w = m.shape[1]
        m[:, :int(w * kenar)] = False
        m[:, int(w * (1 - kenar)):] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= MIN_ALAN
    return tut[lab]


def bantlar(m, bosluk=BOSLUK, min_yuk=6):
    """Satir profilinden murekkep bantlari [(y0, y1)]."""
    satir = np.nonzero(m.sum(1) >= 2)[0]
    if not len(satir):
        return []
    out, a, b = [], satir[0], satir[0]
    for y in satir[1:]:
        if y - b > bosluk:
            out.append((int(a), int(b) + 1)); a = y
        b = y
    out.append((int(a), int(b) + 1))
    return [x for x in out if x[1] - x[0] >= min_yuk]


def _oz(D):
    import cv2
    f = np.clip(np.abs(D @ LUMA) / 40.0, 0, 1).astype(np.float32)
    return cv2.GaussianBlur(f, (0, 0), 2.0)


def hizala(D_ci, D_wp, bant_listesi, pay=PAY):
    """Her WP bandi icin CI -> WP afin donusumu (tam sayfa koordinatinda, WARP_INVERSE_MAP):
    x_ci = A @ x_wp + t. Faz korelasyonu (baslangic) + ECC afin (inceltme)."""
    import cv2
    H, Wd = D_wp.shape[:2]
    Fc, Fw = _oz(D_ci), _oz(D_wp)
    sonuc = []
    for i, (y0, y1) in enumerate(bant_listesi):
        onc = bant_listesi[i - 1][1] if i else 0
        son = bant_listesi[i + 1][0] if i + 1 < len(bant_listesi) else H
        w0 = max(0, y0 - min(pay, max((y0 - onc) // 2, 8)))
        w1 = min(H, y1 + min(pay, max((son - y1) // 2, 8)))
        T, I = Fw[w0:w1], Fc[w0:w1]
        pen = cv2.createHanningWindow((Wd, w1 - w0), cv2.CV_32F)
        (sx, sy), yanit = cv2.phaseCorrelate(T.astype(np.float64), I.astype(np.float64), pen.astype(np.float64))
        M = np.array([[1, 0, sx], [0, 1, sy]], np.float32)
        cc, ecc_ok = None, False
        try:
            cc, M2 = cv2.findTransformECC(T, I, M.copy(), cv2.MOTION_AFFINE,
                                          (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6),
                                          None, 5)
            if abs(M2[0, 2] - sx) < pay and abs(M2[1, 2] - sy) < pay:
                M, ecc_ok = M2, True
        except cv2.error:
            pass
        A = M[:, :2].astype(np.float64)
        o = np.array([0.0, w0])
        t = M[:, 2].astype(np.float64) + o - A @ o          # pencere -> tam sayfa
        c = np.array([Wd / 2.0, (y0 + y1) / 2.0])            # kayma bant merkezinde raporlanir
        sonuc.append({'bant': [int(y0), int(y1)], 'pencere': [int(w0), int(w1)],
                      'A': A.tolist(), 't': t.tolist(),
                      'dx': round(float((A @ c + t - c)[0]), 2), 'dy': round(float((A @ c + t - c)[1]), 2),
                      'olcek': [round(float(A[0, 0]), 5), round(float(A[1, 1]), 5)],
                      'faz': [round(float(sx), 2), round(float(sy), 2), round(float(yanit), 3)],
                      'ecc': None if cc is None else round(float(cc), 4), 'ecc_ok': ecc_ok})
    # bolge: bantlar arasi bosluklarin ortasindan bolunur (tum sayfa kaplanir)
    for i, s in enumerate(sonuc):
        a = 0 if i == 0 else (sonuc[i - 1]['bant'][1] + s['bant'][0]) // 2
        b = H if i + 1 == len(sonuc) else (s['bant'][1] + sonuc[i + 1]['bant'][0]) // 2
        s['bolge'] = [int(a), int(b)]
    return sonuc


def katman_tasi(D_ci, hiz, boyut):
    """CI murekkep katmanini WP geometrisine tasir (bolge bazinda afin)."""
    import cv2
    Wd, H = boyut
    out = np.zeros((H, Wd, 3), np.float32)
    if not hiz:
        return D_ci.copy()
    for s in hiz:
        a, b = s['bolge']
        A = np.array(s['A']); t = np.array(s['t']) + A @ np.array([0.0, a])
        M = np.hstack([A, t[:, None]]).astype(np.float32)
        out[a:b] = cv2.warpAffine(D_ci, M, (Wd, b - a), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out


def _phi(D):
    d = (D / 128.0).astype(np.float32)
    r, g, b = d[:, 0], d[:, 1], d[:, 2]
    t = [np.ones_like(r), r, g, b]
    if DERECE >= 2:
        t += [r * r, g * g, b * b, r * g, r * b, g * b]
    if DERECE >= 3:
        t += [r * r * r, g * g * g, b * b * b, r * r * g, r * r * b, g * g * r, g * g * b,
              b * b * r, b * b * g, r * g * b]
    return np.stack(t, 1)


def _agirlik(D):
    m = np.abs(D).max(-1)
    return np.clip((m - RAMPA[0]) / (RAMPA[1] - RAMPA[0]), 0, 1)


def renk_ogren(Dw, P_wp, S_wp, ornek=ORNEK, tohum=0):
    """S_wp ~ b(D)*P_wp + c(D). Egitim: murekkep pikselleri (+ %10 zemin: b=1, c=0 ucu)."""
    rng = np.random.default_rng(tohum)
    D = Dw.reshape(-1, 3); P = P_wp.reshape(-1, 3); S = S_wp.reshape(-1, 3)
    w = _agirlik(Dw).reshape(-1)
    ink = np.nonzero(w > 0)[0]
    zem = np.nonzero(w == 0)[0]
    ink = rng.choice(ink, min(len(ink), ornek), replace=False)
    zem = rng.choice(zem, min(len(zem), max(len(ink) // 10, 1000)), replace=False)
    idx = np.concatenate([ink, zem])
    F = _phi(D[idx]); K = F.shape[1]; n = len(idx)
    X = np.zeros((n * 3, K * 4), np.float32); y = np.zeros(n * 3, np.float32)
    for ch in range(3):
        X[ch * n:(ch + 1) * n, :K] = F * P[idx, ch:ch + 1]
        X[ch * n:(ch + 1) * n, K * (ch + 1):K * (ch + 2)] = F
        y[ch * n:(ch + 1) * n] = S[idx, ch]
    lam = 1e-3 * n
    XtX = X.T.astype(np.float64) @ X; Xty = X.T.astype(np.float64) @ y
    XtX[np.diag_indices_from(XtX)] += lam
    beta = np.linalg.solve(XtX, Xty)
    kal = y - X @ beta.astype(np.float32)
    return {'beta': beta[:K].tolist(), 'gamma': [beta[K * (c + 1):K * (c + 2)].tolist() for c in range(3)],
            'derece': DERECE, 'egitim_px': int(n), 'murekkep_px': int(len(ink)),
            'egitim_rmse': round(float(np.sqrt((kal ** 2).mean())), 2)}


def renk_uygula(Dw, P_wp, model, parca=512):
    beta = np.array(model['beta'], np.float32)
    gam = np.array(model['gamma'], np.float32).T                   # K x 3
    out = P_wp.copy()
    H = Dw.shape[0]
    for y0 in range(0, H, parca):
        D = Dw[y0:y0 + parca].reshape(-1, 3); P = P_wp[y0:y0 + parca].reshape(-1, 3)
        w = _agirlik(Dw[y0:y0 + parca]).reshape(-1)
        sec = w > 0
        if not sec.any():
            continue
        F = _phi(D[sec])
        m = (F @ beta)[:, None] * P[sec] + F @ gam
        o = P.copy()
        o[sec] = P[sec] + w[sec, None] * (m - P[sec])
        out[y0:y0 + parca] = o.reshape(-1, Dw.shape[1], 3)
    return np.clip(out, 0, 255)


def lab(a):
    import cv2
    return cv2.cvtColor((np.clip(a, 0, 255) / 255.0).astype(np.float32), cv2.COLOR_RGB2Lab)


def dE(A, B):
    return np.sqrt(((lab(A) - lab(B)) ** 2).sum(-1))


def ozet(d, m=None):
    v = d[m] if m is not None else d.reshape(-1)
    if not v.size:
        return {'px': 0}
    return {'px': int(v.size), 'ort': round(float(v.mean()), 2),
            'p95': round(float(np.percentile(v, 95)), 1), 'p99': round(float(np.percentile(v, 99)), 1),
            'max': round(float(v.max()), 1), 'pay_gt10': round(float((v > 10).mean()), 4)}


def fark_tablosu(uretilen, onayli, P_wp, etiketli_bantlar, P_uretilen=None):
    """Kimlik farki: tum sayfa, murekkep bolgesi (her iki tarafin murekkebi, 3 px genisletilmis),
    bant bazinda. Ayrica zemin tabani: |P_wp - onayli| murekkep disi (plate'in kendi hatasi)."""
    import cv2
    d = dE(uretilen, onayli)
    ma = murekkep_maskesi(onayli - P_wp, kenar=0)
    mb = murekkep_maskesi(uretilen - (P_wp if P_uretilen is None else P_uretilen), kenar=0)
    mk = cv2.dilate((ma | mb).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    r = {'tum': ozet(d), 'murekkep': ozet(d, mk),
         'zemin_tabani': ozet(dE(P_wp, onayli), ~mk)}
    for ad, (y0, y1) in etiketli_bantlar.items():
        bm = np.zeros(d.shape, bool); bm[y0:y1] = True
        r[ad] = ozet(d, bm & mk)
        # IoU: murekkep maskelerinin ortusmesi (sembol / isim kaymasi olcusu)
        a, b = ma[y0:y1], mb[y0:y1]
        u = (a | b).sum()
        r[ad]['iou'] = round(float((a & b).sum() / u), 4) if u else None
    return r


def plate_temizlik(P_wp, S_wp, bant_listesi, esik_oran=1.25, esik_pay=0.25):
    """WP plate'inde slogan / eski yazi izi var mi? (bant listesi: isim + mesaj bantlari)

    Onayli WP kaynaginin kendi glifleri YEREL KONTRASTLA (plate'ten bagimsiz) bulunur.
    - pay: glif piksellerinde |S - P| > 12 orani; plate'te ayni glif varsa ~0 (plate_slogan_kapisi olcutu).
    - iz_orani: plate'in yerel kontrasti glif piksellerinde / cevresindeki halkada. Temiz plate ~1
      (glif yerinde yalniz doku), iz kalmis plate > 1.
    """
    import cv2
    Lp = P_wp @ LUMA; Ls = S_wp @ LUMA
    zp = cv2.medianBlur(np.clip(Lp, 0, 255).astype(np.uint8), 31).astype(np.float32)
    zs = cv2.medianBlur(np.clip(Ls, 0, 255).astype(np.uint8), 31).astype(np.float32)
    lc = np.abs(Lp - zp)
    out = {}
    for ad, (y0, y1) in bant_listesi.items():
        g = np.abs(Ls - zs)[y0:y1] > 26
        w = g.shape[1]; g[:, :int(w * KENAR)] = False; g[:, int(w * (1 - KENAR)):] = False
        if g.sum() < 200:
            out[ad] = {'gecti': False, 'sebep': f'glif yok ({int(g.sum())} px)'}
            continue
        gd = cv2.dilate(g.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
        gi = cv2.dilate(g.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        halka = gd & ~gi
        pay = float((np.abs(Ls - Lp)[y0:y1][g] > ESIK).mean())
        oran = float(lc[y0:y1][g].mean() / max(lc[y0:y1][halka].mean(), 1e-3))
        out[ad] = {'glif_px': int(g.sum()), 'pay': round(pay, 4), 'iz_orani': round(oran, 3),
                   'gecti': bool(pay >= esik_pay and oran <= esik_oran)}
    out['gecti'] = all(v.get('gecti') for v in out.values() if isinstance(v, dict))
    out['esik'] = {'pay_min': esik_pay, 'iz_orani_max': esik_oran}
    return out


def _nc_bulanik(a, gecerli, sigma):
    """Normalize konvolusyon: yalniz gecerli piksellerden bulanik ortalama (maske ici doldurulur)."""
    import cv2
    w = gecerli.astype(np.float32)
    pay = cv2.GaussianBlur(a * w[..., None], (0, 0), sigma)
    payda = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    return pay / np.maximum(payda, 1e-4)


def plate_onar(P_wp, S_wp, bant_listesi, genislet=21, sigma=12.0, pay=40):
    """Plate'teki eski glif izini (medyan plate'e sizan slogan / isim) KAYNAGIN KENDI DOKUSUYLA onarir.

    R = onayli WP kaynaginin bu bantlardaki glifleri (yerel kontrast, plate'ten bagimsiz), `genislet` px.
    R icinde: dusuk frekans = R disindan normalize bulanik (leke/ton korunur), yuksek frekans = ayni
    sutunlarda murekkepsiz bir bagis seridinden (bant yuksekligi + pay kadar asagi ya da yukari).
    Kenar 4 px yumusatilir. Silme yok: yalniz zemin plate'i duzeltilir; musteri baskisinda yazi yine katmandir."""
    import cv2
    H = P_wp.shape[0]
    Ls = S_wp @ LUMA
    zs = cv2.medianBlur(np.clip(Ls, 0, 255).astype(np.uint8), 31).astype(np.float32)
    lc = np.abs(Ls - zs) > 26
    lc[:, :int(lc.shape[1] * KENAR)] = False; lc[:, int(lc.shape[1] * (1 - KENAR)):] = False
    ink_tum = cv2.dilate(lc.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    out = P_wp.copy()
    rapor = {}
    for ad, (y0, y1) in bant_listesi.items():
        g = np.zeros_like(lc); g[y0:y1] = lc[y0:y1]
        R = cv2.dilate(g.astype(np.uint8), np.ones((genislet, genislet), np.uint8)).astype(bool)
        if not R.any():
            continue
        ys = np.nonzero(R.any(1))[0]; a, b = int(ys[0]), int(ys[-1]) + 1
        d = None
        for aday in ((b - a) + pay, -((b - a) + pay), 2 * (b - a) + pay, -(2 * (b - a) + pay)):
            if 0 <= a + aday and b + aday <= H and not ink_tum[a + aday:b + aday][R[a:b]].any():
                d = aday; break
        if d is None:
            rapor[ad] = {'onarildi': False, 'sebep': 'murekkepsiz bagis seridi yok'}
            continue
        seg = slice(max(0, a - 3 * int(sigma)), min(H, b + 3 * int(sigma)))
        Pseg = out[seg]; Rseg = R[seg]
        dus = _nc_bulanik(Pseg, ~Rseg, sigma)
        dseg = slice(seg.start + d, seg.stop + d)
        if dseg.start < 0 or dseg.stop > H:
            dseg = slice(a + d, b + d); seg = slice(a, b)
            Pseg = out[seg]; Rseg = R[seg]; dus = _nc_bulanik(Pseg, ~Rseg, sigma)
        Dn = P_wp[dseg]
        yuksek = Dn - _nc_bulanik(Dn, np.ones(Dn.shape[:2], bool), sigma)
        f = cv2.GaussianBlur(Rseg.astype(np.float32), (0, 0), 4.0)[..., None]
        f = np.maximum(f, Rseg[..., None].astype(np.float32))
        out[seg] = Pseg * (1 - f) + (dus + yuksek) * f
        rapor[ad] = {'onarildi': True, 'satir': [a, b], 'bagis_kayma': int(d), 'px': int(R.sum())}
    return np.clip(out, 0, 255), rapor


def eski_iz(D_ci_eski, D_ci_yeni, yeni, maske_bolge):
    """CI baskisinda silinen eski yazidan kalan: kaynakta murekkep olup yeni yazi maskesinde
    (render'in kendi ham maskesi, 3 px genisletilmis) OLMAYAN piksellerde |dL| > ESIK kalan bilesenler.
    Katman yontemi silmedigi icin WP'ye tasinan iz yalniz buradan gelebilir."""
    import cv2
    eski = murekkep_maskesi(D_ci_eski, kenar=0)
    yeni = cv2.dilate(yeni.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    aday = eski & ~yeni & maske_bolge
    kal = (np.abs(D_ci_yeni @ LUMA) > ESIK) & aday
    n, lab, st, _ = cv2.connectedComponentsWithStats(kal.astype(np.uint8), 8)
    buyuk = st[1:, cv2.CC_STAT_AREA] >= IZ_MIN_ALAN if n > 1 else np.zeros(0, bool)
    return {'aday_px': int(aday.sum()), 'kalinti_px': int(kal.sum()),
            'kalinti_bileseni': int(buyuk.sum()), 'en_buyuk_px': int(st[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0,
            'gecti': int(buyuk.sum()) == 0}


def katman_bas(B_ci, P_ci, P_wp, hiz, model):
    """Tam yol: baski (CI) -> WP. Donus: (wp dizisi, tasinan katman)."""
    D = katman_tasi(B_ci - P_ci, hiz, (P_wp.shape[1], P_wp.shape[0]))
    return renk_uygula(D, P_wp, model), D
