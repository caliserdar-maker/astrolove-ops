#!/usr/bin/env python3
"""WP siparis DIKIS KAPISI (durdurucu; Serdar 1 Eki: 'yanlis alarmsa esigi o ornekle duzelt, kapiyi tekrar durdurucu
yap'). Kilitli koda dokunmaz: kilitli dedektor (wb.dikis, yanyana ayarlari: ince-uzun bilesen yazi sayilmaz, kontrast
3-120, 30 satir bosluk, isabete gore temsil) bantlarda ADAY uretir; her aday +-10 px icinde OLCULUR:
  seri = cizgi sutunu ile komsu sutunlar (+-4..6 px) farki, cizgi yonunde 15 px duzlenmis, yazi satirlari haric;
  parca = seri >= ESIK olan en uzun kosu (30 satira kadar bosluk kapanir), en az BOY gercek isabet;
  cizgi = parcadaki ortanca sapma, onayli kagidin AYNI parcadaki ortancasindan en az ESIK fazla.
Esik ornekten (v2 YANYANA, CANCER_LIBRA 11x14): e4f65cd'de kilitli d) kapisinin isaretledigi 5 konum yanlis alarm
(kosu ortanca sapmasi 1.9-6.5, onayliya fark <= 3.7: harf kenari / kagit dokusu); v2 dikisi 18.4 (onayli 0.9).
ESIK = 8 (yanlis alarm ust siniri 6.5 ile dikis 18.4 arasinda)."""
import cv2
import numpy as np

import wp_bakir as wb
import wp_katman as wk
import wp_ornek as wo

ESIK = 8.0
BOY = 60          # en az 60 satir gercek isabet (yazi satirlari sayilmaz)
BOSLUK = 30       # cizgi boyunca kapanan bosluk (v2 dikisi kesikli)
ARA = 10
KENAR = 40


def _seri(L, yazi, c, isaret, dd):
    """Cizgi boyunca sapma serisi (cizgi yonunde 15 px duzlenmis; yazi satirlari NaN) ve kosu ofseti."""
    if c['yon'] == 'dikey':
        x = c['x'] + dd; y0, y1 = max(0, c['y'][0] - KENAR), min(L.shape[0], c['y'][1] + 1 + KENAR)
        if x - 6 < 0 or x + 7 > L.shape[1]:
            return None, 0
        k = L[y0:y1, x]; n = 0.5 * (L[y0:y1, x - 6:x - 3].mean(1) + L[y0:y1, x + 4:x + 7].mean(1))
        m = ~yazi[y0:y1, x - 6:x + 7].any(1)
    else:
        y = c['y'] + dd; y0, y1 = max(0, c['x'][0] - KENAR), min(L.shape[1], c['x'][1] + 1 + KENAR)
        if y - 6 < 0 or y + 7 > L.shape[0]:
            return None, 0
        k = L[y, y0:y1]; n = 0.5 * (L[y - 6:y - 3, y0:y1].mean(0) + L[y + 4:y + 7, y0:y1].mean(0))
        m = ~yazi[y - 6:y + 7, y0:y1].any(0)
    v = cv2.blur((isaret * (n - k)).astype(np.float32).reshape(-1, 1), (1, 15)).ravel()
    v[~m] = np.nan
    return v, y0


def _parca(v, esik):
    """En uzun parca: v >= esik (yazi satirlari NaN: kosuyu bolmez, sayilmaz), BOSLUK satira kadar bosluk kapanir.
    Donus (bas, son, gercek_isabet)."""
    hit = np.nan_to_num(v, nan=-1) >= esik
    notr = np.isnan(v)
    en, bas, son, h, son_hit = (0, 0, 0), None, 0, 0, -10 ** 9
    for i in range(len(v)):
        if hit[i]:
            if bas is None or i - son_hit > BOSLUK:
                bas, h = i, 0
            son_hit = i; h += 1
            if h > en[2]:
                en = (bas, i, h)
        elif not notr[i] and bas is not None and i - son_hit > BOSLUK:
            bas = None
    return en


def kapi(yeni, onayli, satirlar, esik=ESIK):
    """yeni, onayli: HxWx3 (ayni geometri). satirlar: bool[H] (bant satirlari). Donus {cizgi, aday_sayi, gecti}."""
    A = np.asarray(yeni, np.float32); B = np.asarray(onayli, np.float32)
    ya, yb = wo._yazi_maskesi(A, ince=True), wo._yazi_maskesi(B, ince=True)
    aday = wb.dikis(A, satirlar, T=(3.0, 120.0), murekkep=ya, bosluk=30, temsil='isabet')
    La, Lb = A @ wb.LUMA, B @ wb.LUMA
    sonuc = []
    for c in aday:
        s = 1.0 if c['tur'] == 'koyu' else -1.0
        en = None
        for dd in range(-ARA, ARA + 1):                  # yerlesik sutun cizgiden 7 px uzak olabilir (v2: 1293/1300)
            v, o = _seri(La, ya, c, s, dd)
            if v is None:
                continue
            b0, b1, h = _parca(v, esik)
            if h and (en is None or h > en[0]):
                en = (h, dd, b0, b1, v, o)
        if en is None or en[0] < BOY:
            continue
        h, dd, b0, b1, v, o = en
        seg = v[b0:b1 + 1]
        c2 = {**c, 'x': c['x'] + dd} if c['yon'] == 'dikey' else {**c, 'y': c['y'] + dd}
        vb, _ = _seri(Lb, yb, c2, s, 0)
        sb = float(np.nanmedian(vb[b0:b1 + 1])) if vb is not None and np.isfinite(vb[b0:b1 + 1]).any() else 0.0
        sa = float(np.nanmedian(seg))
        if sa - sb >= esik:
            yer = [o + b0, o + b1]
            sonuc.append({'yon': c['yon'], 'tur': c['tur'], ('x' if c['yon'] == 'dikey' else 'y'): c2['x' if c['yon'] == 'dikey' else 'y'],
                          ('y' if c['yon'] == 'dikey' else 'x'): yer, 'isabet': h, 'sapma_yeni': round(sa, 1),
                          'sapma_onayli': round(sb, 1)})
    return {'cizgi': sonuc[:10], 'aday_sayi': len(aday), 'esik': esik, 'gecti': not sonuc}


def siparis_kapisi(WP, cift, boy, et):
    """Siparis ciktisi (WP) icin: onayli WP kaynagi + isim/mesaj bantlari (yanyana paneliyle ayni satirlar)."""
    S_wp = wk.dizi(wo.sd.pod_kaynak(cift, 'WARM_PARCHMENT', boy))
    sat = np.zeros(WP.shape[0], bool)
    ic = [v for a, v in (et or {}).items() if a != 'buyuk_sembol']
    if ic:
        sat[max(0, min(v[0] for v in ic) - 60):max(v[1] for v in ic) + 60] = True
    else:
        sat[:] = True
    return kapi(WP, S_wp, sat)
