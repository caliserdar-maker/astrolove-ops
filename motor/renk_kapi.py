#!/usr/bin/env python3
"""RENK KAPISI (Serdar 4 Eki): poster uzerinde (golge sonrasi) oge renk olcumu ve PASS/FAIL.

Her oge cekirdegi (doku_poster OGE_MASKE.npz: alfa > 0.95, 3 px asindirilmis) icinde medyan Lab (skimage, D65).
Gecme sarti (Serdar 4 Eki, TEK DOKU): ogeler arasi EN BUYUK medyan dE00 <= ESIK; her oge ana sembolle L yuzdelikleri
(p5, p25, p50, p75, p95, p99) farki <= YUZDE_ESIK; cok parlak piksel orani (L > ana sembol p99) farki <= PARLAK_ESIK puan;
ana sembol leke = 0; oge ici (ana sembol haric, Serdar 4 Eki): oge boyunca en az 10 esit dilim (cember 12 aci dilimi)
arasinda cok parlak oran (L > ana p99) farki, ana sembolun kendi dilim farkini gecemez (Serdar 5 Eki; dilim medyan L
ve HSV V > 0.95 farki yalniz rapor). Serdar 5 Eki: dilim kapisi YALNIZ RAPOR; metin ogelerinde (isim1, isim2, tagline)
PARCA kapisi: parcalar (harf, i noktasi, kuyruk; cekirdek baglantili bilesenleri) arasi medyan L farki <= 1.0, b* <= 1.0,
ton <= 3 derece. DOKU (yalniz rapor): L yerel std (9 px pencere), cekirdekte medyan. Kapali dongu: hedefe kalan fark bir sonraki tur icin kazanc JSON'una yazilir
(kL = kL_onceki x hedef_L / L_olculen, da / db = onceki + (hedef - olculen)).

Kullanim: renk_kapi.py --poster GOLGE_1.png --dizin POSTER_DIZINI [--hedef 71.5,8.5,49.5] [--kazanc-cikti K.json]
Cikis kodu 1 = FAIL.
"""
import argparse, itertools, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import leke_kapi as lk                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ESIK = 1.0
YUZDE = (5, 25, 50, 75, 95, 99)
YUZDE_ESIK = 1.5
PARLAK_ESIK = 1.0
DILIM_N = 10            # oge boyunca esit dilim (cember: aci dilimi 12)
HALKA_MERKEZ = (3598.97, 4388.09)
METIN = ('isim1', 'isim2', 'tagline')
PARCA_L_ESIK, PARCA_B_ESIK, PARCA_TON_ESIK = 1.0, 1.5, 3.0   # b* 1.5: Serdar 7 Eki      # Serdar 5 Eki: harf bazli esitleme kapisi
PARCA_MIN_PX = 300
KIRMIZI_A, KIRMIZI_ESIK = 25.0, 1.5    # Serdar 5 Eki (8e9c727 RED): metin cekirdeginde a* > 25 orani <= %1.5


def parcalar(Lc, m):
    """metin ogesi parcalari (harf, i noktasi, kuyruk): cekirdegin 5x5 genisletilmis baglantili bilesenleri; parca
    basina medyan L, b*, ton (derece). Parcalar arasi en buyuk farklar."""
    n, pl = cv2.connectedComponents(cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)))
    pl = pl * m
    P = []
    for i in range(1, n):
        c = pl == i
        if c.sum() < PARCA_MIN_PX:
            continue
        med = np.median(Lc[c], 0)
        P.append((float(med[0]), float(med[2]), float(np.degrees(np.arctan2(med[2], med[1])))))
    P = np.array(P)
    return {'parca_n': len(P), 'parca_L_fark': round(float(np.ptp(P[:, 0])), 2), 'parca_b_fark': round(float(np.ptp(P[:, 1])), 2),
            'parca_ton_fark': round(float(np.ptp(P[:, 2])), 2)}


def dilimler(ad, Lk, V, m, x0, y0):
    """oge ici bolgesel parlaklik (Serdar 4 Eki): oge boyunca esit dilimlerde medyan L ve HSV V > 0.95 orani."""
    ys, xs = np.nonzero(m)
    if ad == 'cember':
        t = np.degrees(np.arctan2(-(ys + y0 - HALKA_MERKEZ[1]), xs + x0 - HALKA_MERKEZ[0])) % 360
        n = 12; k = np.minimum(((t - t.min()) / (np.ptp(t) + 1e-6) * n).astype(int), n - 1)
    else:
        n = DILIM_N
        u = xs if (xs.max() - xs.min()) >= (ys.max() - ys.min()) else ys
        k = np.minimum(((u - u.min()) / (np.ptp(u) + 1e-6) * n).astype(int), n - 1)
    Lm, Vo = [], []
    for i in range(n):
        q = k == i
        if q.sum() < 300:
            continue
        Lm.append(float(np.median(Lk[ys[q], xs[q]]))); Vo.append(100 * float((V[ys[q], xs[q]] > 0.95 * 255).mean()))
    Ld = [Lk[ys[k == i], xs[k == i]] for i in range(n) if (k == i).sum() >= 300]
    return {'dilim_n': len(Lm), 'dilim_L_med': [round(v, 1) for v in Lm], 'dilim_V095': [round(v, 1) for v in Vo],
            'dilim_L_fark': round(max(Lm) - min(Lm), 2), 'dilim_V_fark': round(max(Vo) - min(Vo), 2), '_dilim_L': Ld}


def olc(poster, dizin, hedef):
    P = np.asarray(Image.open(poster).convert('RGB'))
    Z = np.load(Path(dizin) / 'OGE_MASKE.npz')
    rap = json.loads((Path(dizin) / 'POSTER.json').read_text())
    T = {}
    for ad in Z.files:
        v = Z[ad]; x0, y0, h, w = (int(q) for q in v[:4])
        m = np.unpackbits(v[4:].astype(np.uint8))[:h * w].reshape(h, w).astype(bool)
        Lc = rgb2lab(P[y0:y0 + h, x0:x0 + w] / 255.0).astype(np.float32)
        L = np.median(Lc[m], 0)
        Lk = Lc[..., 0]
        mu = cv2.blur(Lk, (9, 9)); sd = np.sqrt(np.maximum(cv2.blur(Lk * Lk, (9, 9)) - mu * mu, 0))
        T[ad] = {'Lab': [round(float(q), 2) for q in L], 'px': int(m.sum()), '_L': Lk[m],
                 '_q': np.percentile(Lk[m], np.linspace(0, 100, 201)),
                 'L_yuzdelik': [round(float(q), 2) for q in np.percentile(Lk[m], YUZDE)],
                 'doku_std9': round(float(np.median(sd[m])), 3)}
        Vc = cv2.cvtColor(np.ascontiguousarray(P[y0:y0 + h, x0:x0 + w]), cv2.COLOR_RGB2HSV)[..., 2]
        T[ad].update(dilimler(ad, Lk, Vc, m, x0, y0))
        if ad in METIN:
            T[ad].update(parcalar(Lc, m))
            T[ad]['kirmizi_yuzde'] = round(100 * float((Lc[..., 1][m] > KIRMIZI_A).mean()), 3)
        del Lc, Lk, mu, sd, Vc
        if ad == 'ana_sembol':
            T[ad]['leke'] = lk.olc(np.ascontiguousarray(P[y0:y0 + h, x0:x0 + w]), m.astype(np.float32))[0]
    ana = np.array(T['ana_sembol']['Lab'])
    qa = T['ana_sembol']['_q']
    for ad, t in T.items():
        t['_Lq'] = qa - t.pop('_q')                                  # kapali dongu: poster uzerinde yuzdelik farki
    p99 = T['ana_sembol']['L_yuzdelik'][-1]
    for ad, t in T.items():
        t['parlak_oran_yuzde'] = round(100 * float((t.pop('_L') > p99).mean()), 3)
    for ad, t in T.items():
        t['L_yuzdelik_fark'] = [round(a_ - b_, 2) for a_, b_ in zip(t['L_yuzdelik'], T['ana_sembol']['L_yuzdelik'])]
        t['parlak_fark_puan'] = round(t['parlak_oran_yuzde'] - T['ana_sembol']['parlak_oran_yuzde'], 3)
        t['doku_oran_ana'] = round(t['doku_std9'] / max(T['ana_sembol']['doku_std9'], 1e-6), 3)
        # Serdar 5 Eki: dilim kapisi = dilimler arasi cok parlak oran (L > ana p99) farki, ana sembolun KENDI dilim
        # farkindan buyuk olamaz (2.0 L esigi kaldirildi; dilim L / V farki yalniz rapor)
        t['dilim_parlak'] = [round(100 * float((d > p99).mean()), 2) for d in t.pop('_dilim_L')]
        t['dilim_parlak_fark'] = round(max(t['dilim_parlak']) - min(t['dilim_parlak']), 2)
    for ad, t in T.items():
        t['dilim_esik'] = T['ana_sembol']['dilim_parlak_fark']
        t['dilim_gecti'] = bool(ad == 'ana_sembol' or t['dilim_parlak_fark'] <= t['dilim_esik'])
        # Serdar 5 Eki: dilim kapisi yalniz RAPOR (FAIL vermez); metin ogelerinde parca kapisi
        t['parca_gecti'] = bool(ad not in METIN or (t['parca_L_fark'] <= PARCA_L_ESIK and t['parca_b_fark'] <= PARCA_B_ESIK
                                                     and t['parca_ton_fark'] <= PARCA_TON_ESIK
                                                     and t['kirmizi_yuzde'] <= KIRMIZI_ESIK))
        t['gecti'] = bool(max(abs(v) for v in t['L_yuzdelik_fark']) <= YUZDE_ESIK and abs(t['parlak_fark_puan']) <= PARLAK_ESIK
                          and t['parca_gecti'])
    for ad, t in T.items():
        t['dE00_ana'] = round(float(deltaE_ciede2000(ana[None], np.array(t['Lab'])[None])[0]), 3)
        t['dE00_hedef'] = round(float(deltaE_ciede2000(np.array(hedef)[None], np.array(t['Lab'])[None])[0]), 3)
    cift = {f'{p}|{q}': float(deltaE_ciede2000(np.array(T[p]['Lab'])[None], np.array(T[q]['Lab'])[None])[0])
            for p, q in itertools.combinations(T, 2)}
    en = max(cift, key=cift.get)
    for ad in T:
        T[ad]['dE00_oge_max'] = round(max(v for k, v in cift.items() if ad in k.split('|')), 3)
    sonuc = {'ogeler': T, 'en_buyuk_cift': [en, round(cift[en], 3)], 'esik': ESIK,
             'leke_ana': T['ana_sembol'].get('leke'), 'renk_esitleme': rap.get('renk_esitleme', {})}
    sonuc['yuzde_esik'] = YUZDE_ESIK; sonuc['parlak_esik_puan'] = PARLAK_ESIK
    sonuc['sonuc'] = 'PASS' if (cift[en] <= ESIK and T['ana_sembol'].get('leke', 0) == 0
                                and all(t['gecti'] for t in T.values())) else 'FAIL'
    return sonuc


def kazanc(sonuc, hedef, onceki):
    K = {}
    for ad, t in sonuc['ogeler'].items():
        o = onceki.get(ad, {})
        L, a_, b_ = t['Lab']
        K[ad] = {'kL': o.get('kL', 1.0) * hedef[0] / L, 'da': o.get('da', 0.0) + hedef[1] - a_,
                 'db': o.get('db', 0.0) + hedef[2] - b_,
                 'Lq': (np.asarray(o.get('Lq', 0.0)) + t['_Lq']).tolist()}
    return K


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True); ap.add_argument('--dizin', required=True)
    ap.add_argument('--hedef', default='71.5,8.5,49.5'); ap.add_argument('--onceki-kazanc')
    ap.add_argument('--kazanc-cikti'); ap.add_argument('--rapor')
    a = ap.parse_args()
    hedef = [float(v) for v in a.hedef.split(',')]
    s = olc(a.poster, a.dizin, hedef)
    if a.kazanc_cikti:
        on = json.loads(Path(a.onceki_kazanc).read_text()) if a.onceki_kazanc else {}
        Path(a.kazanc_cikti).write_text(json.dumps(kazanc(s, hedef, on), indent=1))
    if a.rapor:
        Path(a.rapor).write_text(json.dumps({**s, 'ogeler': {k: {kk: vv for kk, vv in v.items() if kk != '_Lq'}
                                                            for k, v in s['ogeler'].items()}}, indent=1, ensure_ascii=False))
    for ad, t in s['ogeler'].items():
        print(f"{ad:11s} Lab {t['Lab'][0]:5.1f} {t['Lab'][1]:4.1f} {t['Lab'][2]:4.1f} dE_ana {t['dE00_ana']:4.2f} "
              f"dE_max {t['dE00_oge_max']:4.2f} | Lp {' '.join(f'{v:5.1f}' for v in t['L_yuzdelik'])} | fark maks "
              f"{max(abs(v) for v in t['L_yuzdelik_fark']):4.2f} | parlak% {t['parlak_oran_yuzde']:5.2f} | doku {t['doku_std9']:5.2f}"
              f" ({t['doku_oran_ana']:.2f}x) | dilim(rapor) {t['dilim_parlak_fark']:5.2f}/{t['dilim_esik']:.2f}"
              + (f" | parca L {t['parca_L_fark']:5.2f} b {t['parca_b_fark']:5.2f} ton {t['parca_ton_fark']:5.2f} (n {t['parca_n']}) kirmizi% {t['kirmizi_yuzde']:.2f}"
                 if 'parca_n' in t else '') + f" {'OK' if t['gecti'] else 'X'}")
    print('en buyuk cift', s['en_buyuk_cift'], 'leke_ana', s['leke_ana'], s['sonuc'])
    sys.exit(0 if s['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
