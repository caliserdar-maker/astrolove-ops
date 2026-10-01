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
T0 = 4.0            # murekkep gucu gurultu tabani (luma)
KENAR_PX = 2        # cizgi maskesi genisletme (kenar yumusamasi)
KOYU_ALT = 0.15     # en koyu golge carpani alt siniri
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
            'sektor_yayilim': round(yay, 2), 'sektor_sayisi': len(ort),
            'kahve_orani': round(kahve_orani(P_wp[core], rgb), 4)}


def kahve_orani(px, hedef):
    """Bakir tonundan > KAHVE_DH derece ya da kromasi < KAHVE_C x bakir olan piksel orani."""
    if not len(px):
        return 0.0
    L = wk.lab(px.reshape(-1, 1, 3))[:, 0]
    h0 = _lab1(hedef)
    hh = np.degrees(np.arctan2(L[:, 2], L[:, 1])); h0h = np.degrees(np.arctan2(h0[2], h0[1]))
    dh = np.abs((hh - h0h + 180) % 360 - 180)
    C = np.hypot(L[:, 1], L[:, 2]); C0 = np.hypot(h0[1], h0[2])
    return float(((dh > KAHVE_DH) | (C < KAHVE_C * C0)).mean())


def bakir_bas(Dw, P_wp, hedef_rgb, Lp, kalibre=3):
    """Tek bakir modeli (modul aciklamasi). Donus: (cikti, bilgi{maskeler, Lk, C})."""
    H, W = Dw.shape[:2]
    m = np.clip(-(Dw @ LUMA), 0, None)
    core = wk.murekkep_maskesi(Dw, kenar=0) & (m > wk.ESIK)
    M = cv2.dilate(core.astype(np.uint8), np.ones((2 * KENAR_PX + 1,) * 2, np.uint8)).astype(bool)
    ce = cv2.erode(core.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    if ce.sum() < 1000:
        ce = core
    Lk = float(np.median(m[ce])) if ce.any() else 60.0
    t = m / max(Lk, 1.0)
    t0 = T0 / max(Lk, 1.0)
    te = np.clip((t - t0) / (1 - t0), 0, None)
    te[~M] = 0.0
    f = np.clip((Lp - m) / max(Lp - Lk, 1.0), KOYU_ALT, 1.0)
    hedef = np.asarray(hedef_rgb, np.float32)
    C = hedef.copy()
    acik = M & (te <= 1); koyu = M & (te > 1)
    for i in range(kalibre + 1):
        out = P_wp.copy()
        out[acik] = P_wp[acik] + te[acik, None] * (C - P_wp[acik])
        out[koyu] = C[None] * f[koyu, None]
        ort = out[ce].mean(0) if ce.any() else hedef
        if i < kalibre:
            C = np.clip(C + (hedef - ort), 0, 255)
    return np.clip(out, 0, 255), {'Lk': round(Lk, 2), 'Lp': round(float(Lp), 1), 'C': [round(float(v), 1) for v in C],
                                  'cekirdek_ort': [round(float(v), 1) for v in ort], 'core': core, 'ce': ce, 'M': M,
                                  'maske_px': int(M.sum()), 'acik_px': int(acik.sum()), 'koyu_px': int(koyu.sum())}


def _en_uzun_kosu(hit):
    """hit (N x K): eksen 0 boyunca her sutunda en uzun ardisik True kosusu ve bitis indeksi."""
    run = np.zeros(hit.shape[1], np.int32); best = np.zeros_like(run); son = np.zeros_like(run)
    for i in range(hit.shape[0]):
        run = (run + 1) * hit[i]
        yeni = run > best
        best[yeni] = run[yeni]; son[yeni] = i
    return best, son


def dikis(A, satir_maskesi, boy=DIKIS_BOY, T=DIKIS_T, d=DIKIS_KOMSU):
    """Ince, uzun, duz dikey/yatay cizgi dedektoru (bantlarda). Cizgi pikseli iki yanindaki (+-d px) her iki
    komsudan T[0]..T[1] luma koyu ya da acik. Murekkep vuruslari (kontrast >> 30) ve vurus kenarlari (tek yan
    koyu) sayilmaz. Donus: [{yon, konum, bas, son, boy, kontrast}]."""
    L = (A @ LUMA).astype(np.float32)
    H, W = L.shape
    out = []
    satirlar = np.nonzero(satir_maskesi)[0]
    if not len(satirlar):
        return out
    for yon in ('dikey', 'yatay'):
        X = L if yon == 'dikey' else L[satirlar].T          # dikey: satirlar boyunca; yatay: bant satirlarinda x boyunca
        a = np.roll(X, d, axis=1); b = np.roll(X, -d, axis=1)
        koyu = np.minimum(a, b) - X; acik = X - np.maximum(a, b)
        for isim, V in (('koyu', koyu), ('acik', acik)):
            hit = (V >= T[0]) & (V <= T[1])
            hit[:, :d] = False; hit[:, -d:] = False
            if yon == 'dikey':
                hit &= satir_maskesi[:, None]
            best, son = _en_uzun_kosu(hit)
            ks = np.nonzero(best >= boy)[0]
            # komsu sutunlari tek cizgi say
            grup = []
            for k in ks:
                if grup and k - grup[-1][-1] <= 2:
                    grup[-1].append(k)
                else:
                    grup.append([k])
            for g in grup:
                k = max(g, key=lambda z: best[z])
                s1 = int(son[k]); s0 = s1 - int(best[k]) + 1
                kon = float(V[s0:s1 + 1, k].mean())
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


def qc(out, P_wp, S_wp, bilgi, et, daire, hedef, plate_iz=None):
    """Tek QC, PASS/FAIL. Esikler olculerek: daire (tekdüze bakir oge) yayilimi ve plate/onayli kontrolleri."""
    H, W = out.shape[:2]
    ce, core = bilgi['ce'], bilgi['core']
    hrgb = hedef['rgb']
    yay = hedef.get('sektor_yayilim') or 2.0
    esik_dE = round(max(4.0, 2 * yay), 2)
    r = {}
    # a) renk birligi
    og = ogeler(ce, et, W)
    dc = cv2.erode(daire.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ort = {a: out[m].mean(0) for a, m in og.items()}
    if dc.sum() >= 500:
        ort['daire'] = out[dc].mean(0)
    hed = {a: round(_dE(v, hrgb), 2) for a, v in ort.items()}
    ara = max((_dE(ort[a], ort[b]) for i, a in enumerate(ort) for b in list(ort)[i + 1:]), default=0.0)
    kah_taban = hedef.get('kahve_orani') or 0.0
    esik_k = round(max(0.02, 2 * kah_taban), 4)
    tum = np.zeros_like(ce)
    for m in og.values():
        tum |= m
    kah = kahve_orani(out[tum], hrgb)
    r['a_renk'] = {'oge_ort_rgb': {a: [round(float(x), 1) for x in v] for a, v in ort.items()},
                   'hedefe_dE': hed, 'ogeler_arasi_max_dE': round(ara, 2), 'esik_dE': esik_dE,
                   'kahve_orani': round(kah, 4), 'esik_kahve': esik_k,
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
    ci = dikis(out, sm)
    cp = dikis(P_wp, sm)
    cs = dikis(S_wp, sm)
    # cizgi maskesine girmis (bakira boyanmis) ince uzun cizgi: genisligi <= 4 px olan maske pikselleri (yatay
    # 1x5 acilimla kalmayan) bir sutunda >= 100 px ardisik (harf govdeleri >= 5 px; harfe degen dikis de yakalanir)
    ince = []
    for yon in ('dikey', 'yatay'):
        Cm = core if yon == 'dikey' else core.T
        acik_ = cv2.morphologyEx(Cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((1, 5), np.uint8)).astype(bool)
        best, son = _en_uzun_kosu(Cm & ~acik_)
        for kx in np.nonzero(best >= DIKIS_BOY)[0][:10]:
            ince.append({'yon': yon, 'konum': int(kx), 'son': int(son[kx]), 'boy': int(best[kx])})
    r['d_dikis'] = {'yeni': ci[:10], 'yeni_sayi': len(ci), 'plate_sayi': len(cp), 'onayli_sayi': len(cs),
                    'maskede_ince_bilesen': ince[:10], 'boy_min': DIKIS_BOY, 'kontrast': list(DIKIS_T),
                    'gecti': len(ci) <= len(cp) and not ince}
    # e) bant disi kagit farki (cizgi maskeleri haric)
    ink_s = wk.murekkep_maskesi(S_wp - P_wp, kenar=0)
    haric = cv2.dilate((core | ink_s).astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool) | daire
    de = wk.dE(out, S_wp)[~haric]
    r['e_kagit'] = {'px': int(de.size), 'ort': round(float(de.mean()), 3), 'p99': round(float(np.percentile(de, 99)), 2),
                    'esik_ort': 0.5, 'esik_p99': 3.0,
                    'gecti': bool(de.mean() <= 0.5 and np.percentile(de, 99) <= 3.0)}
    r['gecti'] = all(v['gecti'] for v in r.values() if isinstance(v, dict) and 'gecti' in v)
    return r
