#!/usr/bin/env python3
"""WARM PARCHMENT BAKIR BASKI + QC (1 Eki 2026, Serdar kesin karari). Etsy/Prodigi/musteri YOK.

Karar: WP'de TUM ogeler (buyuk sembol, daire, kucuk semboller, isimler, sonsuz, mesaj) BAKIR; kagit/plate
HIC degismez. Hedef bakir = plate'teki dairenin OLCULEN ortalamasi (Serdar: ~169/109/47). Daire plate'te zaten
bakir oldugu icin dokunulmaz; geri kalan cizgi katmani tek modelle bakira basilir.

TEK BAKIR MODELI (cizgi katmaninin tamami, oge ayrimi yok):
  m  = murekkep gucu = -(D @ LUMA), D = hizalanmis (duz renk baskisi - duz renk plate'i)
  Lk = cekirdek murekkep piksellerinde m ortancasi  ->  t = m / Lk
  t <= 1 : kagit -> bakir dogrusu  P + t (C - P)          (kenar yumusamasi, kabartma isigi)
  t >  1 : bakir koyulasir         C (Lp - m) / (Lp - Lk)  (kabartma golgesi)
  Ton bakir dogrusunun disina cikamaz (karisik bakir/kahverengi yok). C, cekirdek ortalamasi hedefe
  esit olacak sekilde olculerek kalibre edilir.
TASMA / IZ / DIKIS: cizgi maskesi = |dL| > 12 bilesenleri (alan >= 40) + KENAR_PX genisletme; disi BIREBIR
plate. Eski yontemde 2-6 luma'lik kucuk farklar (hibrit bant kenari, plate-kaynak gurultusu) renk modelinde
kagida tasiniyordu (Serdar: "With" ile "a" arasi 260 px dikey cizgi, gri 184 / cevre 196). Simdi t0 = 4 luma
gurultu tabani + maske disi sifir.
"""
import cv2
import numpy as np

import wp_katman as wk
from wp_katman import LUMA

BAKIR_VARSAYILAN = np.array([169, 109, 47], np.float32)   # Serdar 1 Eki (yaklasik); kosuda daireden olculur
BAKIR_KOYU = np.array([140, 72, 28], np.float32)         # Serdar 1 Eki (2): 'cok silik'; kontrast ~4.2 baslangic
T0 = 4.0            # murekkep gucu gurultu tabani (luma)
KENAR_PX = 2        # cizgi maskesi genisletme (kenar yumusamasi)
KOYU_ALT = 0.55     # en koyu golge carpani alt siniri (1. kosu 0.15: derin golge koyu kahve gibi gorunuyordu)
KOYU_SIKISTIR = 0.6 # golge derinligi carpani (kabartma korunur, bakir ailesinde kalir)
ESIK_DE = 5.0       # oge-hedef ve ogeler arasi dE (sabit; daire yay dilimi yayilimi 16.9 -> esik turetilemedi)
MIN_ALAN_BAKIR = 12 # cizgi maskesi bilesen alt siniri (CI farki dokusuz; i noktasi / nokta kaybolmasin)
DOLU = 0.9          # tam murekkep pikseli: te >= 0.9 (kenar yumusamasi haric renk olcumu)
DIKIS_DUZLE = 15    # dikis dedektoru: cizgi boyunca kutu ortalama (doku gurultusu tek sutun kosuyu bolmesin)
KABARTMA_SIGMA = (1.0, 1.5, 2.5, 4.0)   # x (W/2400); onayli yaziya en iyi uyan secilir
KABARTMA_ESIK = (0.7, 1.43)            # f) yeni/onayli kenar isik-golge kontrasti orani
DIKIS_BOY = 100     # Serdar: en az 100 px
DIKIS_T = (3.0, 30.0)   # ince cizgi kontrasti (luma): seritteki dikis 12; murekkep vurusu >> 30
DIKIS_KOMSU = 3
KAHVE_DH = 15.0     # derece: bakir tonundan sapma
KAHVE_C = 0.6       # bakir kromasinin bu oranindan az = gri/kahve


def _lab1(rgb):
    return wk.lab(np.asarray(rgb, np.float32).reshape(1, 1, 3))[0, 0]


def _dE(a, b):
    return float(np.sqrt(((_lab1(a) - _lab1(b)) ** 2).sum()))


def daire_maskesi(P_c, oran=0.35):
    """Duz renk plate'inde (dokusuz) daire: yerel kontrastla koyu, genisligi sayfanin >= %35'i olan bilesenler."""
    L = P_c @ LUMA
    z = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 31).astype(np.float32)
    m = (z - L) > 10
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    W = L.shape[1]
    tut = [i for i in range(1, n) if st[i, cv2.CC_STAT_WIDTH] > oran * W and st[i, cv2.CC_STAT_AREA] > 500]
    return np.isin(lab, tut)


def bakir_hedef(P_wp, daire, sektor=8):
    """Hedef bakir = plate'teki dairenin cekirdek ortalamasi; dogal yayilim = 8 yay dilimi ortalamalari arasi
    en buyuk dE (tekdüze bir bakir ogenin kendi icindeki farki; QC esigi bundan turetilir)."""
    core = cv2.erode(daire.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    if core.sum() < 500:
        core = daire
    if core.sum() < 500:
        return {'rgb': BAKIR_VARSAYILAN.tolist(), 'kaynak': 'varsayilan (daire bulunamadi)',
                'sektor_yayilim': None, 'px': int(core.sum())}
    rgb = P_wp[core].mean(0)
    ys, xs = np.nonzero(core)
    a = np.arctan2(ys - ys.mean(), xs - xs.mean())
    b = ((a + np.pi) / (2 * np.pi) * sektor).astype(int).clip(0, sektor - 1)
    ort = [P_wp[ys[b == i], xs[b == i]].mean(0) for i in range(sektor) if (b == i).sum() >= 200]
    yay = max((_dE(p, q) for i, p in enumerate(ort) for q in ort[i + 1:]), default=0.0)
    return {'rgb': [round(float(v), 1) for v in rgb], 'kaynak': 'daire (plate)', 'px': int(core.sum()),
            'sektor_yayilim': round(yay, 2), 'sektor_sayisi': len(ort)}


def _ton(rgb_px):
    L = wk.lab(np.asarray(rgb_px, np.float32).reshape(-1, 1, 3))[:, 0]
    return np.degrees(np.arctan2(L[:, 2], L[:, 1]))


def kahve_orani(px, hedef, kahve_ref):
    """Tonu (Lab hue) olculen onayli gri-kahveye bakirdan daha yakin piksel orani. Koyu bakir (golge) tonunu
    korur (bakir 64.4, x0.7 65.2, x0.5 65.4 derece); gri-kahve ~72-74, kagit ~76 (1 Eki olcumu)."""
    if not len(px):
        return 0.0
    h = _ton(px)
    hc = float(_ton(hedef)[0]); hb = float(_ton(kahve_ref)[0])
    def fark(a, b):
        return np.abs((a - b + 180) % 360 - 180)
    return float((fark(h, hb) < fark(h, hc)).mean())


def _yukseklik_egim(A, sigma):
    h = cv2.GaussianBlur(A.astype(np.float32), (0, 0), sigma)
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8.0 * sigma
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8.0 * sigma
    return gy, gx


def kabartma_olc(A, S_wp, P_wp, satirlar, k=1.0):
    """Onayli WP yazisinin (isim + mesaj) kabartma profili. A = ayni glif geometrisinin alfasi (duz CI kaynagindan,
    dokusuz). Tam murekkep piksellerinde goreli parlaklik r = L / ortanca(L) ~ 1 + a dh/dy + b dh/dx (h = sigma ile
    bulanik alfa). a > 0: ust kenar isik, alt kenar golge. sigma en iyi R^2 ile secilir. kenar_kontrast = ust kenar
    (dh/dy ust %20) - alt kenar (alt %20) ortalama r farki."""
    L = S_wp @ LUMA
    full = (A >= DOLU) & satirlar[:, None]
    full &= wk.murekkep_maskesi(S_wp - P_wp, kenar=0)
    if full.sum() < 2000:
        return None
    r = L[full] / max(float(np.median(L[full])), 1.0)
    en = None
    for s_ in KABARTMA_SIGMA:
        sig = s_ * k
        gy, gx = _yukseklik_egim(A, sig)
        X = np.stack([gy[full], gx[full]], 1)
        coef, *_ = np.linalg.lstsq(X, r - 1, rcond=None)
        kal = (r - 1) - X @ coef
        r2 = 1 - float((kal ** 2).sum() / max(((r - r.mean()) ** 2).sum(), 1e-6))
        if en is None or r2 > en['r2']:
            en = {'sigma': round(float(sig), 2), 'a': round(float(coef[0]), 4), 'b': round(float(coef[1]), 4),
                  'r2': round(r2, 3), 'kenar_kontrast': round(kenar_kontrast(r, gy[full]), 4)}
    return en


def kenar_kontrast(r, gy):
    if len(r) < 100:
        return 0.0
    ust = gy > np.percentile(gy, 80); alt = gy < np.percentile(gy, 20)
    return float(r[ust].mean() - r[alt].mean())


def kabartma_haritasi(A, kb):
    gy, gx = _yukseklik_egim(A, kb['sigma'])
    g = np.clip(1 + kb['a'] * gy + kb['b'] * gx, 0.5, 1.6).astype(np.float32)
    g[~kb['satirlar']] = 1.0
    return g


def kabartma_kontrol(out, A, satirlar, sigma, onayli):
    """f) yeni baskida ayni olcum: kenar isik-golge kontrasti onaylininkine yakin mi (oran KABARTMA_ESIK)."""
    L = out @ LUMA
    full = (A >= DOLU) & satirlar[:, None]
    if full.sum() < 2000 or not onayli:
        return {'gecti': False, 'sebep': 'olculemedi'}
    r = L[full] / max(float(np.median(L[full])), 1.0)
    gy, _ = _yukseklik_egim(A, sigma)
    kk = kenar_kontrast(r, gy[full])
    oran = kk / onayli['kenar_kontrast'] if onayli['kenar_kontrast'] else 0.0
    return {'yeni_kenar_kontrast': round(kk, 4), 'onayli_kenar_kontrast': onayli['kenar_kontrast'],
            'oran': round(oran, 3), 'esik': list(KABARTMA_ESIK),
            'gecti': bool(KABARTMA_ESIK[0] <= oran <= KABARTMA_ESIK[1])}


def _rl(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(c @ np.array([0.2126, 0.7152, 0.0722]))


def wcag(a, b):
    la, lb = _rl(a), _rl(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def kontrast_olc(img, P_wp, ogeler_maske, ink_haric):
    """Her oge: murekkep (tam murekkep pikselleri ortalamasi) / kagit (ogenin 6-20 px cevresi, murekkepsiz,
    plate'ten) WCAG kontrast orani."""
    out = {}
    for ad, m in ogeler_maske.items():
        if m.sum() < 50:
            continue
        d20 = cv2.dilate(m.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
        d6 = cv2.dilate(m.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
        halka = d20 & ~d6 & ~ink_haric
        if halka.sum() < 100:
            continue
        ink = img[m].mean(0); kag = P_wp[halka].mean(0)
        out[ad] = {'kontrast': round(wcag(ink, kag), 2), 'murekkep': [round(float(x), 1) for x in ink],
                   'kagit': [round(float(x), 1) for x in kag]}
    return out


def kagit_tabani(P, daire, yaricap=5):
    """Daireyi plate'ten cikarir (daire de murekkep: tek bakir modeline girer). Duz plate'te yerel medyan,
    dokulu plate'te inpaint (yalniz daire cizgisinin altinda; kagidin geri kalani birebir)."""
    dd = cv2.dilate(daire.astype(np.uint8), np.ones((2 * yaricap + 1,) * 2, np.uint8))
    u8 = np.clip(P, 0, 255).astype(np.uint8)
    return np.where(dd[..., None] > 0, cv2.inpaint(u8, dd, 7, cv2.INPAINT_TELEA).astype(np.float32), P), dd > 0


def dikis_onar(P_wp, S_wp, cizgiler, glif, yari=4):
    """Plate'te olup onayli kagitta OLMAYAN dikisleri onayli kagittan onarir: cizgi boyunca +-yari px serit,
    onayli glif disinda onayli WP pikseli (kagidin kendisi), glif altinda serit disindaki plate sutunlarinin ortalamasi."""
    out = P_wp.copy()
    H, W = P_wp.shape[:2]
    gd = cv2.dilate(glif.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
    for c in cizgiler:
        if c['yon'] == 'dikey':
            x0, x1 = max(0, c['x'] - yari), min(W, c['x'] + yari + 1)
            y0, y1 = max(0, c['y'][0] - 10), min(H, c['y'][1] + 11)
            ser = (slice(y0, y1), slice(x0, x1))
            yedek = 0.5 * (P_wp[y0:y1, max(0, x0 - 6):max(1, x0 - 1)].mean(1, keepdims=True)
                           + P_wp[y0:y1, min(W - 1, x1 + 1):min(W, x1 + 6)].mean(1, keepdims=True))
            yedek = np.repeat(yedek, x1 - x0, 1)
        else:
            y0, y1 = max(0, c['y'] - yari), min(H, c['y'] + yari + 1)
            x0, x1 = max(0, c['x'][0] - 10), min(W, c['x'][1] + 11)
            ser = (slice(y0, y1), slice(x0, x1))
            yedek = 0.5 * (P_wp[max(0, y0 - 6):max(1, y0 - 1), x0:x1].mean(0, keepdims=True)
                           + P_wp[min(H - 1, y1 + 1):min(H, y1 + 6), x0:x1].mean(0, keepdims=True))
            yedek = np.repeat(yedek, y1 - y0, 0)
        g = gd[ser]
        out[ser] = np.where(g[..., None], yedek, S_wp[ser])
    return out


def ayni_cizgi(c, liste, tol=4):
    for d in liste:
        if d['yon'] != c['yon']:
            continue
        if c['yon'] == 'dikey' and abs(d['x'] - c['x']) <= tol and min(d['y'][1], c['y'][1]) > max(d['y'][0], c['y'][0]):
            return True
        if c['yon'] == 'yatay' and abs(d['y'] - c['y']) <= tol and min(d['x'][1], c['x'][1]) > max(d['x'][0], c['x'][0]):
            return True
    return False


def _cekirdek(m):
    c = m > wk.ESIK
    n, lab, st, _ = cv2.connectedComponentsWithStats(c.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= MIN_ALAN_BAKIR
    return tut[lab]


def bakir_bas(Dw, P_wp, hedef_rgb, Lp, bantlar=None, haric=None, kalibre=3, kabartma=None):
    """Tek bakir modeli (modul aciklamasi). bantlar: {ad: (y0, y1)} satirlari icin murekkep gucu ortancasi (Lk)
    ayri olculur (ince oge kenar yumusamasi ortalamayi kaydirmasin); model ve renk ayni. haric: cizgi katmanindan
    cikarilacak maske. kabartma: {'satirlar': bool[H], 'a', 'b', 'sigma'} -> isim/mesaj murekkebine onayli
    yazidan olculen isik/golge (g = 1 + a dh/dy + b dh/dx, h = bulanik alfa)."""
    H, W = Dw.shape[:2]
    m = np.clip(-(Dw @ LUMA), 0, None)
    core = _cekirdek(m)
    if haric is not None:
        core &= ~haric
    M = cv2.dilate(core.astype(np.uint8), np.ones((2 * KENAR_PX + 1,) * 2, np.uint8)).astype(bool)
    if haric is not None:
        M &= ~haric
    ce = cv2.erode(core.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    if ce.sum() < 1000:
        ce = core
    Lk0 = float(np.median(m[ce])) if ce.any() else 60.0
    Lk = np.full(H, Lk0, np.float32)
    lk_bant = {}
    for ad, (y0, y1) in (bantlar or {}).items():
        sec = ce[y0:y1]
        if sec.sum() >= 2000:
            Lk[y0:y1] = float(np.median(m[y0:y1][sec])); lk_bant[ad] = round(float(Lk[y0]), 1)
    Lk = Lk[:, None]
    t = m / np.maximum(Lk, 1.0)
    t0 = T0 / np.maximum(Lk, 1.0)
    te = np.clip((t - t0) / (1 - t0), 0, None)
    te[~M] = 0.0
    fr = (Lp - m) / np.maximum(Lp - Lk, 1.0)
    f = np.clip(1 - KOYU_SIKISTIR * (1 - fr), KOYU_ALT, 1.0)
    hedef = np.asarray(hedef_rgb, np.float32)
    C = hedef.copy()
    acik = M & (te <= 1); koyu = M & (te > 1)
    dolu = core & (te >= DOLU)
    g = np.ones((H, W), np.float32)
    if kabartma:
        g = kabartma_haritasi(np.clip(te, 0, 1), kabartma)
    fk = np.where(koyu, f, 1.0).astype(np.float32) * g
    w = np.clip(te, 0, 1)
    for i in range(kalibre + 1):
        out = P_wp.copy()
        I = C[None, None] * fk[..., None]
        out[M] = P_wp[M] + w[M, None] * (I[M] - P_wp[M])
        ort = out[dolu].mean(0) if dolu.any() else hedef
        if i < kalibre:
            C = np.clip(C + (hedef - ort), 0, 255)
    return np.clip(out, 0, 255), {'Lk': round(Lk0, 2), 'Lk_bant': lk_bant, 'Lp': round(float(Lp), 1),
                                  'C': [round(float(v), 1) for v in C],
                                  'dolu_ort': [round(float(v), 1) for v in ort], 'core': core, 'ce': ce, 'M': M,
                                  'dolu': dolu, 'maske_px': int(M.sum()), 'acik_px': int(acik.sum()),
                                  'koyu_px': int(koyu.sum()), 'dolu_px': int(dolu.sum()), 'te': w}


def _en_uzun_kosu(hit):
    """hit (N x K): eksen 0 boyunca her sutunda en uzun ardisik True kosusu ve bitis indeksi."""
    run = np.zeros(hit.shape[1], np.int32); best = np.zeros_like(run); son = np.zeros_like(run)
    for i in range(hit.shape[0]):
        run = (run + 1) * hit[i]
        yeni = run > best
        best[yeni] = run[yeni]; son[yeni] = i
    return best, son


def dikis(A, satir_maskesi, boy=DIKIS_BOY, T=DIKIS_T, d=DIKIS_KOMSU, duzle=DIKIS_DUZLE, murekkep=None):
    """Ince, uzun, duz dikey/yatay cizgi dedektoru (bantlarda). Goruntu once cizgi YONUNDE `duzle` px kutu
    ortalamasiyla duzlenir (parsomen dokusu tek sutunluk kosuyu bolmesin; 1. bakir kosusunda plate'teki 260 px
    dikis bu yuzden kacti). Cizgi pikseli iki yanindaki (+-d ve +-d+1 px) komsulardan T[0]..T[1] luma koyu ya da
    acik; komsu 1 sutun tolerans, 2 satira kadar bosluk kapatilir. Murekkep vuruslari (kontrast >> 30) ve vurus
    kenarlari (tek yan koyu) sayilmaz. murekkep: yazi maskesi; cevresi (duzleme + komsu kadar) NOTR sayilir:
    kosuyu bolmez ama isabet sayilmaz (yazi satirlari yatay duzlemede cizgi gibi gorunur); kosudaki gercek
    isabet en az %60 x boy olmali. Donus: [{yon, tur, x|y, y|x araligi, boy, kontrast}]."""
    L = (A @ LUMA).astype(np.float32)
    H, W = L.shape
    out = []
    r_ = duzle // 2 + d + 2
    notr_tam = (cv2.dilate(murekkep.astype(np.uint8), np.ones((2 * r_ + 1,) * 2, np.uint8)).astype(bool)
                if murekkep is not None else np.zeros((H, W), bool))
    satirlar = np.nonzero(satir_maskesi)[0]
    if not len(satirlar):
        return out
    for yon in ('dikey', 'yatay'):
        if yon == 'dikey':
            X = cv2.blur(L, (1, duzle))                      # dikey cizgi: satirlar boyunca duzle
            notr = notr_tam
        else:
            X = cv2.blur(L, (duzle, 1))[satirlar].T          # yatay cizgi: bant satirlarinda x boyunca
            notr = notr_tam[satirlar].T
        for isim in ('koyu', 'acik'):
            V = None
            for dd in (d, d + 1):
                a = np.roll(X, dd, axis=1); b = np.roll(X, -dd, axis=1)
                v = (np.minimum(a, b) - X) if isim == 'koyu' else (X - np.maximum(a, b))
                V = v if V is None else np.maximum(V, v)
            hit = (V >= T[0]) & (V <= T[1])
            hit[:, :d + 1] = False; hit[:, -(d + 1):] = False
            if yon == 'dikey':
                hit &= satir_maskesi[:, None]
            hit &= ~notr
            hit = cv2.dilate(hit.astype(np.uint8), np.ones((1, 3), np.uint8))          # +-1 sutun
            hit = cv2.morphologyEx(hit, cv2.MORPH_CLOSE, np.ones((5, 1), np.uint8)).astype(bool)  # 2 satir bosluk
            kos = hit | (notr if yon == 'yatay' else (notr & satir_maskesi[:, None]))
            best, son = _en_uzun_kosu(kos)
            ks = [k for k in np.nonzero(best >= boy)[0]
                  if hit[son[k] - best[k] + 1:son[k] + 1, k].sum() >= 0.6 * boy]
            grup = []
            for k in ks:
                if grup and k - grup[-1][-1] <= 3:
                    grup[-1].append(k)
                else:
                    grup.append([k])
            for g_ in grup:
                k = max(g_, key=lambda z: best[z])
                s1 = int(son[k]); s0 = s1 - int(best[k]) + 1
                kon = float(V[s0:s1 + 1, max(0, k - 1):k + 2].max(1).mean())
                if yon == 'dikey':
                    out.append({'yon': yon, 'tur': isim, 'x': int(k), 'y': [s0, s1], 'boy': int(best[k]),
                                'kontrast': round(kon, 1)})
                else:
                    out.append({'yon': yon, 'tur': isim, 'y': int(satirlar[k]), 'x': [s0, s1], 'boy': int(best[k]),
                                'kontrast': round(kon, 1)})
    return out


def _kume(m, bosluk):
    kol = np.nonzero(m.sum(0) > 0)[0]
    if not len(kol):
        return []
    out, a, b = [], kol[0], kol[0]
    for x in kol[1:]:
        if x - b > bosluk:
            out.append([int(a), int(b) + 1]); a = x
        b = x
    out.append([int(a), int(b) + 1])
    return out


def ogeler(ce, et, W):
    """Cekirdek murekkep maskesini ogelere ayirir: buyuk_sembol, kucuk_sembol_sol/sag, isim1, sonsuz, isim2, mesaj."""
    o = {}
    def bant(ad):
        m = np.zeros_like(ce)
        if ad in et:
            y0, y1 = et[ad]; m[y0:y1] = ce[y0:y1]
        return m
    if 'buyuk_sembol' in et:
        o['buyuk_sembol'] = bant('buyuk_sembol')
    if 'kucuk_sembol' in et:
        k = bant('kucuk_sembol'); s = k.copy(); s[:, W // 2:] = False; g = k.copy(); g[:, :W // 2] = False
        o['kucuk_sembol_sol'], o['kucuk_sembol_sag'] = s, g
    if 'isim' in et:
        b = bant('isim'); ys = np.nonzero(b.any(1))[0]
        h = (ys[-1] - ys[0] + 1) if len(ys) else 1
        kk = _kume(b, max(int(0.45 * h), 6))
        if len(kk) == 3:
            for ad, (a, z) in zip(('isim1', 'sonsuz', 'isim2'), kk):
                m = np.zeros_like(b); m[:, a:z] = b[:, a:z]; o[ad] = m
        else:
            o['isim_satiri'] = b
    if 'mesaj' in et:
        o['mesaj'] = bant('mesaj')
    return {a: m for a, m in o.items() if m.sum() >= 50}


def qc(out, P_wp, S_wp, bilgi, et, daire, hedef, plate_iz=None, ek=None):
    """Tek QC, PASS/FAIL (a-e burada; f kabartma ve g kontrast `ek` ile gelir). P_wp = baskinin kagidi (daire
    cikarilmis plate). Daire artik murekkep (tek bakir modeli); ogelerden ayri tutulur."""
    H, W = out.shape[:2]
    dd = cv2.dilate(daire.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
    ce, core = bilgi.get('dolu', bilgi['ce']), bilgi['core']
    ce_d = ce & dd
    ce = ce & ~dd
    hrgb = hedef['rgb']
    esik_dE = ESIK_DE
    # gri-kahve referansi: onayli WP'nin kendi cizgi cekirdegi (olculur)
    ink_s0 = wk.murekkep_maskesi(S_wp - P_wp, kenar=0)
    ks = cv2.erode(ink_s0.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    kahve_ref = S_wp[ks].mean(0) if ks.sum() >= 500 else np.array([120, 84, 36], np.float32)
    r = {}
    # a) renk birligi
    og = ogeler(ce, et, W)
    ort = {a: out[m].mean(0) for a, m in og.items()}
    if ce_d.sum() >= 300:
        ort['daire'] = out[ce_d].mean(0)
    hed = {a: round(_dE(v, hrgb), 2) for a, v in ort.items()}
    ara = max((_dE(ort[a], ort[b]) for i, a in enumerate(ort) for b in list(ort)[i + 1:]), default=0.0)
    esik_k = 0.02
    tum = ce_d.copy()
    for m in og.values():
        tum |= m
    kah = kahve_orani(out[tum], hrgb, kahve_ref)
    r['a_renk'] = {'oge_ort_rgb': {a: [round(float(x), 1) for x in v] for a, v in ort.items()},
                   'hedefe_dE': hed, 'ogeler_arasi_max_dE': round(ara, 2), 'esik_dE': esik_dE,
                   'kahve_orani': round(kah, 4), 'esik_kahve': esik_k,
                   'kahve_ref_rgb': [round(float(x), 1) for x in kahve_ref], 'daire_yayilim': hedef.get('sektor_yayilim'),
                   'gecti': bool(hed and max(hed.values()) <= esik_dE and ara <= esik_dE and kah <= esik_k)}
    # b) tasma / hale: cizgi maskesinin 3-8 px disi = plate
    d8 = cv2.dilate(core.astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool)
    d3 = cv2.dilate(core.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    halka = d8 & ~d3
    dh = wk.dE(out[halka].reshape(-1, 1, 3), P_wp[halka].reshape(-1, 1, 3)).ravel() if halka.any() else np.zeros(1)
    r['b_tasma'] = {'halka_px': int(halka.sum()), 'ort': round(float(dh.mean()), 3),
                    'p99': round(float(np.percentile(dh, 99)), 3), 'max': round(float(dh.max()), 2),
                    'esik_p99': 1.0, 'gecti': bool(np.percentile(dh, 99) <= 1.0)}
    # c) iz
    r['c_iz'] = {**(plate_iz or {}), 'gecti': bool((plate_iz or {}).get('gecti'))}
    # d) dikis: bant satirlari +-150 px; kontrol = plate ve onayli kaynak
    sm = np.zeros(H, bool)
    for a in ('kucuk_sembol', 'isim', 'mesaj'):
        if a in et:
            sm[max(0, et[a][0] - 150):min(H, et[a][1] + 150)] = True
    ink_s = wk.murekkep_maskesi(S_wp - P_wp, kenar=0)
    ci = dikis(out, sm, murekkep=core | dd)
    cp = dikis(P_wp, sm, murekkep=dd)
    cs = dikis(S_wp, sm, murekkep=ink_s | dd)
    fazla = [c for c in ci if not ayni_cizgi(c, cs)]          # onayli kagitta olmayan cizgi = kusur
    # cizgi maskesine girmis (bakira boyanmis) ince uzun cizgi: genisligi <= 4 px olan maske pikselleri (yatay
    # 1x5 acilimla kalmayan) bir sutunda >= 100 px ardisik (harf govdeleri >= 5 px; harfe degen dikis de yakalanir)
    ince = []
    for yon in ('dikey', 'yatay'):
        Cm = (core & ~dd) if yon == 'dikey' else (core & ~dd).T
        acik_ = cv2.morphologyEx(Cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((1, 5), np.uint8)).astype(bool)
        best, son = _en_uzun_kosu(Cm & ~acik_)
        for kx in np.nonzero(best >= DIKIS_BOY)[0][:10]:
            ince.append({'yon': yon, 'konum': int(kx), 'son': int(son[kx]), 'boy': int(best[kx])})
    r['d_dikis'] = {'yeni': ci[:10], 'yeni_sayi': len(ci), 'plate_sayi': len(cp), 'onayli_sayi': len(cs),
                    'onaylida_olmayan': fazla[:10], 'maskede_ince_bilesen': ince[:10], 'boy_min': DIKIS_BOY,
                    'kontrast': list(DIKIS_T), 'gecti': not fazla and not ince}
    # e) bant disi kagit farki (cizgi maskeleri haric)
    ink_s = wk.murekkep_maskesi(S_wp - P_wp, kenar=0)
    haric = cv2.dilate((core | ink_s).astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool) | dd
    de = wk.dE(out, S_wp)[~haric]
    r['e_kagit'] = {'px': int(de.size), 'ort': round(float(de.mean()), 3), 'p99': round(float(np.percentile(de, 99)), 2),
                    'esik_ort': 0.5, 'esik_p99': 3.0,
                    'gecti': bool(de.mean() <= 0.5 and np.percentile(de, 99) <= 3.0)}
    r.update(ek or {})
    r['gecti'] = all(v['gecti'] for v in r.values() if isinstance(v, dict) and 'gecti' in v)
    return r


def alfa(D):
    """Duz renk murekkep alfasi (0..1): m / ortanca(m, cekirdek)."""
    m = np.clip(-(D @ LUMA), 0, None)
    core = _cekirdek(m)
    Lk = float(np.median(m[core])) if core.any() else 60.0
    A = np.clip(m / max(Lk, 1.0), 0, 1)
    A[~cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)] = 0
    return A


def _grupla(og):
    """QC ogelerini kontrast gruplarina topla: isim (iki isim), sonsuz, mesaj, buyuk_sembol, kucuk_sembol."""
    g = {}
    for a, m in og.items():
        k = 'isim' if a in ('isim1', 'isim2', 'isim_satiri') else 'kucuk_sembol' if a.startswith('kucuk') else a
        g[k] = (g[k] | m) if k in g else m.copy()
    return g


def bakir_hatti(D_cu, D_src, P_wp0, S_wp, daire, et, Lp, k, plate_iz=None, hedef0=None, tur=3):
    """WP bakir baski: D_cu / D_src = WP geometrisine tasinmis (duz renk baskisi / onayli duz renk kaynagi) - duz
    renk KAGIDI (daire cikarilmis plate). Donus: (cikti, kagit, rapor)."""
    H, W = S_wp.shape[:2]
    rap = {}
    dd = cv2.dilate(daire.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
    # 1) kagit: daire cikar (daire murekkep), plate'te olup onayli kagitta olmayan dikisleri onar
    P_k0, _ = kagit_tabani(P_wp0, daire)
    sm = np.zeros(H, bool)
    for a in ('kucuk_sembol', 'isim', 'mesaj'):
        if a in et:
            sm[max(0, et[a][0] - 150):min(H, et[a][1] + 150)] = True
    ink_s0 = wk.murekkep_maskesi(S_wp - P_wp0, kenar=0)
    cp = dikis(P_k0, sm, murekkep=dd); cs = dikis(S_wp, sm, murekkep=ink_s0 | dd)
    plate_dikis = [c for c in cp if not ayni_cizgi(c, cs)]
    G = alfa(D_src) > 0.3
    P_k = dikis_onar(P_k0, S_wp, plate_dikis, G) if plate_dikis else P_k0
    rap['plate_dikis'] = {'plate': cp[:10], 'onayli': cs[:10], 'onaylida_olmayan': plate_dikis[:10],
                          'onarildi': bool(plate_dikis)}
    # 2) kabartma: onayli yazidan (isim + mesaj) olc
    sat = np.zeros(H, bool)
    for a in ('isim', 'mesaj'):
        if a in et:
            sat[max(0, et[a][0] - 10):min(H, et[a][1] + 10)] = True
    A_src = alfa(D_src)
    kb = kabartma_olc(A_src, S_wp, P_wp0, sat, k)
    rap['kabartma_onayli'] = kb
    kab = {'satirlar': sat, **kb} if kb else None
    # 3) onayli oge kontrastlari (ayni olcum)
    ink_s = wk.murekkep_maskesi(S_wp - P_wp0, kenar=0)
    og_s = _grupla(ogeler((A_src >= DOLU) & ink_s & ~dd, et, W))
    hs = cv2.dilate(ink_s.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) | dd
    c_app = kontrast_olc(S_wp, P_wp0, og_s, hs)
    # 4) bakir: 140/72/28'den basla; her oge onayli kontrastina ulasana kadar bakir dogrusunda koyulastir
    hedef = np.asarray(hedef0 if hedef0 is not None else BAKIR_KOYU, np.float32)
    bant = {a: et[a] for a in ('buyuk_sembol', 'kucuk_sembol', 'isim', 'mesaj') if a in et}
    gecmis = []
    for i in range(tur):
        out, bb = bakir_bas(D_cu, P_k, hedef, Lp, bant, None, kabartma=kab)
        hn = cv2.dilate(bb['M'].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) | dd
        c_new = kontrast_olc(out, P_k, _grupla(ogeler(bb['dolu'] & ~dd, et, W)), hn)
        eksik = {a: v for a, v in c_new.items() if a in c_app and v['kontrast'] < c_app[a]['kontrast']}
        gecmis.append({'hedef': [round(float(x), 1) for x in hedef],
                       'kontrast': {a: v['kontrast'] for a, v in c_new.items()}})
        if not eksik or i == tur - 1:
            break
        s_ = 1.0
        for a, v in eksik.items():
            Lreq = (_rl(v['kagit']) + 0.05) / c_app[a]['kontrast'] - 0.05
            s_ = min(s_, (max(Lreq, 1e-4) / max(_rl(v['murekkep']), 1e-4)) ** (1 / 2.2) * 0.985)
        hedef = hedef * s_
    rap['bakir'] = {a: v for a, v in bb.items() if a not in ('core', 'ce', 'M', 'dolu', 'te')}
    rap['hedef_gecmis'] = gecmis
    f = kabartma_kontrol(out, bb['te'], sat, kb['sigma'], kb) if kb else {'gecti': False, 'sebep': 'onayli kabartma olculemedi'}
    g = {'yeni': {a: v['kontrast'] for a, v in c_new.items()}, 'onayli': {a: v['kontrast'] for a, v in c_app.items()},
         'ayrinti_yeni': c_new, 'ayrinti_onayli': c_app,
         'gecti': bool(c_app) and all(c_new.get(a, {}).get('kontrast', 0) >= v['kontrast'] for a, v in c_app.items())}
    hedef_d = {'rgb': [round(float(x), 1) for x in hedef], 'kaynak': 'Serdar 140/72/28 + kontrast koyulastirma'}
    q = qc(out, P_k, S_wp, bb, et, daire, hedef_d, plate_iz, ek={'f_kabartma': f, 'g_kontrast': g})
    # dedektorun gercek ornekte calistigi: onarimsiz kagitla ayni cikti
    if plate_dikis:
        o0 = out.copy(); o0[~bb['M']] = P_k0[~bb['M']]
        rap['onarimsiz_d'] = [c for c in dikis(o0, sm, murekkep=bb['core'] | dd) if not ayni_cizgi(c, cs)][:10]
    rap['qc'] = q
    rap['_te'] = np.clip(bb['te'], 0, 1)
    rap['hedef'] = hedef_d
    return out, P_k, rap
