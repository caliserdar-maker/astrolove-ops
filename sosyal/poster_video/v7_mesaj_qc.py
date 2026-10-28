#!/usr/bin/env python3
"""v7 QC kapisi 'mesaj_isim' (Merkez 28 Eki, Serdar onayi: mesaj tam silinip soldan saga yeniden yazilir; isim ve kucuk burclar
degismez). Motordan BAGIMSIZ murekkep maskesi: kapak karesinde (videonun 0. karesi) mesaj bandinda parlaklik - yerel zemin (31 px
medyan) > MUREKKEP_T. Mesaj bandi: isim satirinin altindan poster altina kadar, parlaklik fazlasi > MUREKKEP_T satir kumelerinin en
buyugu (motordaki gibi komsu kumeler <= 10 px bosluk ile), +-3 / +-5 px. Yazim cephesi motorun kendi yazim() ilerleyisi
(ic.json 'yazim': mx0, mx1, yum, nB, nS; eski videolar icin bilgi_kaynaktan ile eski motor kaynagindan).
 a) 0,3-5,0 sn (kare nS..nB-1): cephenin saginda (x >= esik, yazim agirligi 0) kalan murekkep konumlarinda ya mürekkep gibi gorunen
    (parlaklik fazlasi > MUREKKEP_T) ya da kapakla ayni kalan (|parlaklik - kapak| < AYNI_T) piksel sayisi + ayni bolgede (bant x >= esik)
    yerel zeminden belirgin koyu / acik (|parlaklik fazlasi| > LEKE_T) piksel sayisi. Her karede 0 olmali.
 b) son 0,5 sn (kare 165-179): mesaj bandi ile 0. kare (kapak) farki: en buyuk mutlak fark <= taban + PAY; asan piksel 0.
 c) tum kareler, TOZSUZ=1 ile yeniden uretilmis video: isim bandi (sonsuz kutulari haric) ve iki kucuk burc kutusu ile 0. kare farki
    <= taban + PAY; asan piksel 0; ve motorun ham (kodlanmamis) kutu farki (tozsuz ic.json yazim.ham_kutu_fark_max) <= HAM_T (1, nicemleme).
    (Glifler ve sonsuz toz kaynagi; tozlu videoda olculmez.)
 Kodlama tabani: ayni bolgede |kare 179 - kare 0| (ikisi de kapak) en buyugu. Esikler olcumle (asagida kaynak).
Kullanim: v7_mesaj_qc.py <video.mp4> <tozsuz.mp4|-> <ic.json> <cikti.json>"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_qc as Q  # noqa: E402

MUREKKEP_T = 40.0   # Merkez 28 Eki tanimi (AQUARIUS_GEMINI ~1813 px)
AYNI_T = 10.0       # silinmis murekkep pikseli kapaktan >= MUREKKEP_T farkli olur (kapakta murekkep fazlasi > 40, dolgu ~ yerel zemin);
                    # |parlaklik - kapak| < 10 = silinmemis. 78 videoda bu kosulla sayim 0 (40688160261).
LEKE_T = 25.0       # silinmis bantta murekkep disi |yerel zemin farki|: 78 video en buyuk 21,2 (40688160261), 6 yerel cift 20,3; pay 3,8.
HAYALET_T = 3.0     # inceleme 28 Eki bulgu 1. Cephe saginda (silinmis) murekkep konumlarinda ortalama murekkep fazlasi, kare basina en
                    # buyugu. Olcum: v7d 78 video (40688160261) en buyuk 1,49; yapay hayalet AQUARIUS_GEMINI %5 4,67, %10 8,78, %15 13,03.
SOL_T = 10.0        # Cephe solunda (yazim agirligi 1) murekkep konumlarinda kapaktan ortalama |parlaklik farki|, kare basina en buyugu; ayni
                    # olcu cephenin hemen gerisindeki PENCERE (40 px) icin. Olcum: 78 video sol en buyuk 5,08, pencere 4,87; yapay: harfler %80
                    # parlaklik 18,08, %60 35,72; orta 12 px harf gec 25,44, son 60 px gec 31,24.
PENCERE = 40        # video px
YD_DOYGUN = 27      # YD murekkep parcasi doygunluk medyani ust siniri (mesaj 19-20 / kenar 33 / yaprak 44; tek kapak olcumu, gecici)
HAY_PAY = 4         # hayalet olcusu cephenin bu kadar sagindan baslar: v7d ikinci surumde (yazim araligi mesajin tamami) yazimin sonunda
                    # cephe sagindaki az sayida piksel x264 tasmasiyla ortalamayi 2,85'e cikariyordu (AQUARIUS_GEMINI, cephe dibi 1-3 px)
PAY = 10.0          # mp4 kodlama payi (b, c). 78 video (40688160261) c en buyuk - taban: isim 3, sol glif 6, sag glif 7 -> pay 7 + 3.
                    # Ilk turetim: 6 yerel ciftin (AQUARIUS_GEMINI, ARIES_GEMINI, CANCER_SAGITTARIUS, CAPRICORN_SAGITTARIUS,
                    # ARIES_SCORPIO, LIBRA_SAGITTARIUS; tozsuz) isim / iki glif kutusunda tum karelerin en buyuk farki - taban (kare 179 - 0)
                    # en fazla 6 (ARIES_GEMINI sol glif, 5-8. kareler: 0-0,3 sn gecisinde x264 gurultusu; ham karede fark 0); pay 6 + 2.
                    # Ham (kodlanmamis) kutu farki ayrica motordan: ic.json yazim.ham_kutu_fark_max (TOZSUZ=1) <= HAM_T.
HAM_T = 1           # float -> uint8 kesme (astype) nicemlemesi: kutularda BASE = KAP + Gauss kuyrugu (~1e-7); olcum ARIES_GEMINI ve
                    # AQUARIUS_GEMINI ham fark 1 (motor kutulara dokunmuyor: BASE - KAP en buyuk 0,0, WS / WM 0)
W3 = np.float32([0.299, 0.587, 0.114])


def lum(f):
    return f.astype(np.float32) @ W3


def fazla(f, isaret=1.0):
    """murekkep yonunde parlaklik fazlasi: poster (altin, lacivert zemin) isaret +1; YD (yesil, krem kagit) isaret -1 (koyuluk)"""
    l = lum(f)
    return isaret * (l - cv2.medianBlur(np.clip(l, 0, 255).astype(np.uint8), 31).astype(np.float32))


def p2v(d, x, y):
    return (d['x0'] + x * d['cw'] / d['pw']) * d['vw'] / d['kw'], (d['y0'] + y * d['ch'] / d['ph']) * d['vh'] / d['kh']


def kutu_v(d, b, pay=0):
    """poster kutusu [x, y, w, h] -> video [x0, y0, x1, y1] (disa yuvarlanmis, pay px)"""
    xa, ya = p2v(d, b[0], b[1]); xb, yb = p2v(d, b[0] + b[2], b[1] + b[3])
    return int(np.floor(xa)) - pay, int(np.floor(ya)) - pay, int(np.ceil(xb)) + pay, int(np.ceil(yb)) + pay


def ease(x):
    y = min(1.0, max(0.0, x))
    return y * y * (3 - 2 * y)


def mesaj_bandi(F0, d, isim, isaret=1.0):
    """kapak karesinden (motordan bagimsiz) mesaj bandi + murekkep maskesi. Satir kumeleri (<= 10 px bosluk) icinden en buyugu;
    <= max(40 poster px, 1,5 x ana kume yuksekligi) bosluklu ve en buyugun %10'undan buyuk komsu kumeler katilir (iki satirli mesaj)."""
    px0, _, px1, py1 = kutu_v(d, [0, 0, d['pw'], d['ph']])
    _, _, _, iy1 = kutu_v(d, isim)
    ya = iy1 + 4 + int(round(0.4 * isim[3] * d['ch'] / d['ph'] * d['vh'] / d['kh']))   # isim alt uzantilari (J kuyrugu) mesaj sayilmaz
    ex = fazla(F0, isaret)
    m = np.zeros(ex.shape, bool); m[ya:py1, px0:px1] = ex[ya:py1, px0:px1] > MUREKKEP_T
    if isaret < 0:   # YD: yaprak susleri ve yirtik kagit kenari da koyu (silinmez). Parca bazinda renk doygunlugu (max - min kanal)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)   # medyani <= YD_DOYGUN olan parcalar mesaj murekkebi.
        if n > 1:                                  # Olcum (AQUARIUS_AQUARIUS Y01, 0. kare): mesaj 19-20, yaprak 44, kagit kenari 33.
            dy = F0.astype(np.int16).max(-1) - F0.astype(np.int16).min(-1)
            for k in range(1, n):
                if float(np.median(dy[lab == k])) > YD_DOYGUN:
                    m[lab == k] = False
    sat = m.sum(1); kum = []
    for r in np.where(sat > 0)[0]:
        if kum and r - kum[-1][1] <= 10:
            kum[-1][1] = r
        else:
            kum.append([r, r])
    if not kum:
        return None, None
    ag = lambda k: sat[k[0]:k[1] + 1].sum()
    ki = max(range(len(kum)), key=lambda k: ag(kum[k]))
    a, b = kum[ki]
    bos = max(40 * d['vw'] / d['kw'] * d['cw'] / d['pw'], 1.5 * (b - a))   # YD: iki satir (tarih + YEAR ONE) arasi ~17 px
    for k in range(ki - 1, -1, -1):
        if a - kum[k][1] <= bos and ag(kum[k]) > 0.1 * ag(kum[ki]):
            a = kum[k][0]
        else:
            break
    for k in range(ki + 1, len(kum)):
        if kum[k][0] - b <= bos and ag(kum[k]) > 0.1 * ag(kum[ki]):
            b = kum[k][1]
        else:
            break
    a, b = a - 3, b + 4
    cols = np.where(m[a:b].any(0))[0]
    bant = (int(cols.min()) - 5, int(a), int(cols.max()) + 6, int(b))
    ink = np.zeros(ex.shape, bool); ink[a:b, bant[0]:bant[2]] = m[a:b, bant[0]:bant[2]]
    return bant, ink


def olc(F, T, ic, ic_tz=None):
    d, y = ic['donusum'], ic['yazim']
    R = {}
    F0 = F[0]
    isaret = -1.0 if y.get('murekkep') == 'koyu' else 1.0
    bant, ink = mesaj_bandi(F0, d, y['isim_poster'], isaret)
    if bant is None:
        return {'gecti': False, 'deger': {'hata': 'kapakta mesaj murekkebi yok'}}
    x0, y0, x1, y1 = bant
    R['bant'] = list(bant); R['murekkep_px'] = int(ink.sum())
    XX = np.arange(F0.shape[1])[None, :].repeat(F0.shape[0], 0)
    l0 = lum(F0)
    bm = np.zeros(ink.shape, bool); bm[y0:y1, x0:x1] = True
    a_max, a_kare, a_fmax, seri = 0, None, -1e9, []
    hay, sol_f, pen_f = [], [], []
    nS, nB, mx0, mx1, yum = y['nS'], y['nB'], y['mx0'], y['mx1'], y['yum']
    for i in range(nS, nB):
        esik = mx0 - yum + (mx1 - mx0 + 2 * yum) * ease(i / (nB - 1))
        sag = XX >= esik
        sol = XX <= esik - yum                                   # yazim agirligi 1: kapakla ayni olmali
        ex = fazla(F[i], isaret); li = lum(F[i])
        hs = ink & (XX >= esik + HAY_PAY)                         # cephenin 4 px sagindan itibaren (x264 kenar tasmasi haric)
        if hs.sum() >= 30:
            hay.append((round(float(ex[hs].mean()), 2), i))       # silinmis murekkep konumunda ortalama murekkep fazlasi (hayalet)
        if (ink & sol).sum() >= 30:
            sol_f.append((round(float(np.abs(li - l0)[ink & sol].mean()), 2), i))   # yazilmis murekkep: kapaktan ortalama fark
        pen = ink & sol & (XX >= esik - yum - PENCERE)            # cephenin hemen gerisi: gec gelen harf / kelime
        if pen.sum() >= 30:
            pen_f.append((round(float(np.abs(li - l0)[pen].mean()), 2), i))
        kal = ink & sag & ((ex > MUREKKEP_T) | (np.abs(li - l0) < AYNI_T))
        leke = bm & sag & ~ink & (np.abs(ex) > LEKE_T)
        n = int(kal.sum() + leke.sum())
        seri.append(n)
        if (bm & sag).any():
            a_fmax = max(a_fmax, float(np.abs(ex[bm & sag]).max()))
        if n > a_max:
            a_max, a_kare = n, i
    hm = max(hay) if hay else (None, None); sm = max(sol_f) if sol_f else (None, None); pm = max(pen_f) if pen_f else (None, None)
    R['a'] = {'en_cok_piksel': a_max, 'kare': a_kare, 'sag_bant_fazla_max': round(a_fmax, 1), 'kare_araligi': [nS, nB - 1],
              'hayalet_ort_max': hm[0], 'hayalet_kare': hm[1], 'sol_fark_ort_max': sm[0], 'sol_kare': sm[1], 'pencere_fark_ort_max': pm[0], 'pencere_kare': pm[1],
              'esik': {'murekkep': MUREKKEP_T, 'ayni': AYNI_T, 'leke': LEKE_T, 'hayalet': HAYALET_T, 'sol': SOL_T}, 'piksel_seri_ilk20': seri[:20]}
    ok_hay = hm[0] is not None and hm[0] <= HAYALET_T
    ok_sol = sm[0] is not None and sm[0] <= SOL_T and pm[0] is not None and pm[0] <= SOL_T
    dfn = lambda A, B, sl: np.abs(A[sl].astype(np.int16) - B[sl].astype(np.int16)).max(-1)
    sl = (slice(y0, y1), slice(x0, x1))
    tb = int(dfn(F[-1], F0, sl).max())                        # kodlama tabani: kare 179 ve 0 (ikisi de kapak)
    # inceleme 28 Eki bulgu 2: kare >= nB motorda dogrudan kapak; gercek denetim son motor karesi (nB - 1) ile kapak ve nB-1 -> nB sicramasi
    d1 = dfn(F[nB - 1], F0, sl); d2 = dfn(F[nB], F[nB - 1], sl)
    bmx, bn = int(d1.max()), int((d1 > tb + PAY).sum())
    R['b'] = {'taban': tb, 'pay': PAY, 'kare': nB - 1, 'en_buyuk': bmx, 'asan_piksel': bn,
              'sicrama_en_buyuk': int(d2.max()), 'sicrama_asan_piksel': int((d2 > tb + PAY).sum()),
              'sicrama_ort': round(float(d2.mean()), 3)}
    bn += R['b']['sicrama_asan_piksel']
    if T is not None:
        T0 = T[0]
        bol = []
        ip = list(y['isim_poster']); ip[3] = ip[3] + int(y.get('isim_alt', 0) * ip[3])   # alt uzantilar (J, y kuyruklari)
        isim = kutu_v(d, ip, 2)
        mI = np.zeros(T0.shape[:2], bool); mI[isim[1]:isim[3], isim[0]:isim[2]] = True
        for s in ic['glif'].get('sonsuz', []):
            k = kutu_v(d, s, 4); mI[k[1]:k[3], k[0]:k[2]] = False
        bol.append(('isim', mI))
        for g in ('sign_a', 'sign_b'):
            k = kutu_v(d, ic['glif'][g], 2); mg = np.zeros(T0.shape[:2], bool); mg[k[1]:k[3], k[0]:k[2]] = True
            bol.append((g, mg))
        C = {}
        for ad, mm in bol:
            tb_ = int(np.abs(T[-1][mm].astype(np.int16) - T0[mm].astype(np.int16)).max())
            mx_, n_, kr = 0, 0, None
            for i in range(len(T)):
                dd = np.abs(T[i][mm].astype(np.int16) - T0[mm].astype(np.int16)).max(-1)
                if int(dd.max()) > mx_:
                    mx_, kr = int(dd.max()), i
                n_ += int((dd > tb_ + PAY).sum())
            C[ad] = {'taban': tb_, 'en_buyuk': mx_, 'kare': kr, 'asan_piksel': n_, 'px': int(mm.sum())}
        R['c'] = dict(C, pay=PAY)
    else:
        R['c'] = {'hata': 'tozsuz video yok'}
    # yazim araligi disinda kalan murekkep (sol: hic silinmez, sag: yalniz kare nB'de birden gelir), inceleme 28 Eki bulgu 3
    kd = ink & ((XX < mx0 - yum) | (XX > mx1))
    R['a']['kapsam_disi_px'] = int(kd.sum())
    ok_a = bool(a_max == 0 and ok_hay and ok_sol and int(kd.sum()) == 0)
    ok_b = bool(bn == 0)
    ok_c = T is not None and all(v['asan_piksel'] == 0 for k, v in R['c'].items() if isinstance(v, dict))
    if T is not None:
        ham = (ic_tz or {}).get('yazim', {}).get('ham_kutu_fark_max')
        R['c']['ham_kutu_fark_max'] = ham
        ok_c = ok_c and ham is not None and ham <= HAM_T
    R['gecti_abc'] = [ok_a, ok_b, ok_c]
    return {'gecti': ok_a and ok_b and ok_c, 'deger': R}


def bilgi_kaynaktan(pv, kapak, tmpdir):
    """eski videolar (ic.json'da 'yazim' yok): verilen motor kaynagini 'mx0, mx1 = kapsam(MM)' satirina kadar calistirir"""
    src = open(pv, encoding='utf-8').read()
    son = src.index('mx0, mx1 = kapsam(MM)')
    son = src.index('\n', son) + 1
    out = os.path.join(tmpdir, f'_bilgi_{os.getpid()}.mp4')
    eski = sys.argv
    sys.argv = [pv, kapak, out, 'murekkep']
    os.environ['V7_HALKASIZ'] = '1'
    g = {'__name__': 'v7_mesaj_qc_bilgi', '__file__': pv}
    try:
        exec(compile(src[:son], pv, 'exec'), g)
    finally:
        sys.argv = eski
        for e in ('.sembol_maske.png', '.silme_maske.png'):
            if os.path.exists(out + e):
                os.remove(out + e)
    P = g['P']
    return {'donusum': {'x0': g['x0'], 'y0': g['y0'], 'cw': g['cw'], 'ch': g['ch'], 'pw': int(P.w), 'ph': int(P.h),
                        'kw': int(g['kap_src'].shape[1]), 'kh': int(g['kap_src'].shape[0]), 'vw': g['VW'], 'vh': g['VH']},
            'yazim': {'mx0': int(g['mx0']), 'mx1': int(g['mx1']), 'yum': 10, 'nB': int(round(g['BITIS'] * g['FPS'])),
                      'nS': int(round(g['SILME'] * g['FPS'])), 'isim_poster': [int(v) for v in P.names_row[1:5]]},
            'glif': {'sign_a': [int(v) for v in P.sign_a[1:5]], 'sign_b': [int(v) for v in P.sign_b[1:5]],
                     'sonsuz': [[int(v) for v in c[1:5]] for c in g['sonsuz']]}}


if __name__ == '__main__' and len(sys.argv) == 6 and sys.argv[1] == 'eski':
    # dogruluk testi (eski TAM78 videolari, ic.json yok): eski <video.mp4> <kapak.jpg> <eski_motor.py> <cikti.json>; (c) tozsuz yok
    v, kap, pv, out = sys.argv[2:6]
    F, _ = Q.kareler(v)
    r = olc(F, None, bilgi_kaynaktan(pv, kap, os.path.dirname(os.path.abspath(out))))
    r['deger']['a_gecti'] = r['deger']['gecti_abc'][0]
    json.dump(r, open(out, 'w'), indent=1)
    print(os.path.basename(v), 'a', 'PASS' if r['deger']['a_gecti'] else 'FAIL', json.dumps(r['deger']['a'])[:300], 'b', r['deger']['b'])
    sys.exit(0)
elif __name__ == '__main__':
    v, tz, icp, out = sys.argv[1:5]
    F, _ = Q.kareler(v)
    T = Q.kareler(tz)[0] if tz != '-' else None
    r = olc(F, T, json.load(open(icp)), json.load(open(tz + '.ic.json')) if tz != '-' and os.path.exists(tz + '.ic.json') else None)
    json.dump(r, open(out, 'w'), indent=1)
    print(('PASS' if r['gecti'] else 'FAIL'), 'mesaj_isim', json.dumps({k: r['deger'].get(k) for k in ('a', 'b', 'c', 'gecti_abc')})[:900])
    sys.exit(0 if r['gecti'] else 1)
