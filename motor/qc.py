#!/usr/bin/env python3
"""MOTOR prototip olcumu (tek script, PASS/FAIL). Ayni olcum uc sayfaya uygulanir: orijinal satis posteri, Test 5
eski sistem sayfasi, yeni motor. Kapi kendini test eder: Test 5'teki bilinen hatalar (cift tagline, kagit kusuru)
FAIL vermelidir.

a) tagline tek kopya : isim satirinin altindaki metin bandi sayisi = 1 ve OCR metni girdiyle ayni
b) ust/alt hat yok   : kilitli wp_bakir.dikis dedektoru (ince uzun duz cizgi, oge bantlari +-150 px, tasarim alani
                       x %10-%90; maske: m > T0
                       ve murekkep cevresi 20 px, KENAR_PX genisletme; kosunun >= %60'i gercek isabet); orijinalde
                       olmayan cizgi sayisi = 0
c) kagit dokusu      : yazi disi kagitta dE(sayfa, orijinal) ortalamasi <= 0.5 (wp_ornek zemin_uyumu esigi)
d) isim harf harf    : isim satirindaki sol / sag kume tesseract OCR (psm 7, buyuk harf) == girdi
Bilgi: oge renkleri (dE orijinal), satir merkezi, sembol-isim merkez farki.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
sys.path.insert(0, str(KOK))
import wp_katman as wk                                                # noqa: E402
import wp_bakir as wb                                                 # noqa: E402
from olc import murekkep, bantlar, kumeler, ORTA                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def oku(f):
    return np.asarray(Image.open(f).convert('RGB'), np.float32)


def ocr(img, beyaz=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'a.png'
        Image.fromarray(img).save(p)
        kom = ['tesseract', str(p), 'stdout', '--psm', '7']
        if beyaz:
            kom += ['-c', f'tessedit_char_whitelist={beyaz}']
        return subprocess.run(kom, capture_output=True, text=True).stdout.strip()


def ikili(S, P, ink, y0, y1, x0, x1, pad=20):
    """OCR icin: murekkep gucu -> siyah yazi beyaz zemin, 2x."""
    m = np.clip((P - S) @ wk.LUMA, 0, None)[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
    v = np.clip(255 - m * 2.5, 0, 255).astype(np.uint8)
    return cv2.resize(v, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)


def hat_maskesi(P, X):
    """Hat dedektoru maskesi: murekkep gurultu tabani wp_bakir.T0 (4 luma), yalniz gercek murekkebin (olc.murekkep:
    esik 12, bilesen >= 150 px, orta bolge) 20 px cevresinde, wp_bakir.KENAR_PX genisletme. 12 luma esigi tek basina
    italik kilcallari disarida birakip harf aralarini 'cizgi' sayiyordu (3 Eki olcumu)."""
    mm = np.clip((P - X) @ wk.LUMA, 0, None) > wb.T0
    mm &= cv2.dilate(murekkep(X, P)[1].astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    return cv2.dilate(mm.astype(np.uint8), np.ones((2 * wb.KENAR_PX + 1,) * 2, np.uint8)).astype(bool)


def satirlar(Z, H, pay=150):
    sm = np.zeros(H, bool)
    for v in Z['bantlar'].values():
        sm[max(0, v[0] - pay):min(H, v[1] + pay)] = True
    return sm


def tasarim_alani(c, W):
    """Cizgi tasarim alaninda mi (yatay ORTA araligi, olc.py ile ayni). Sayfa kenari vinyet dokusu (orijinalde de
    onlarca 'cizgi' veriyor) disarida."""
    a, b = ORTA[0] * W, ORTA[1] * W
    if c['yon'] == 'dikey':
        return a <= c['x'] <= b
    return min(c['x'][1], b) > max(c['x'][0], a)


def gorunur_oran(X, c, maske):
    """Cizgi kosusunda GERCEK isabet orani: wp_bakir.dikis ile ayni V (cizgi yonunde DIKIS_DUZLE duzleme, +-d ve
    +-(d+1) komsu farki, T araligi), cizgi sutunu +-1; maske (notr) satirlari isabet sayilmaz. dikis notr
    pikselleri kosuya katar; kosunun cogu notr kopru ise cizgi gorunmez (3 Eki: x=1342, kontrast -0.2)."""
    L = (X @ wk.LUMA).astype(np.float32)
    d, T = wb.DIKIS_KOMSU, wb.DIKIS_T
    q = d + 3                                                          # sayfa kenari cizgileri icin kenar kopyasi
    if c['yon'] == 'dikey':
        y0, y1, k = c['y'][0], c['y'][1] + 1, c['x']
        B = np.pad(cv2.blur(L, (1, wb.DIKIS_DUZLE)), ((0, 0), (q, q)), mode='edge')
        A = B[y0:y1, k + q - d - 2:k + q + d + 3]
        mk = np.pad(maske, ((0, 0), (1, 1)))[y0:y1, k:k + 3].any(1)
    else:
        y0, y1, k = c['x'][0], c['x'][1] + 1, c['y']
        B = np.pad(cv2.blur(L, (wb.DIKIS_DUZLE, 1)), ((q, q), (0, 0)), mode='edge')
        A = B[k + q - d - 2:k + q + d + 3, y0:y1].T
        mk = np.pad(maske, ((1, 1), (0, 0)))[k:k + 3, y0:y1].any(0)
    j = d + 2
    en = np.zeros(A.shape[0], bool)
    for o in (-1, 0, 1):
        x = A[:, j + o]
        V = None
        for dd in (d, d + 1):
            a, b = A[:, j + o - dd], A[:, j + o + dd]
            v = (np.minimum(a, b) - x) if c['tur'] == 'koyu' else (x - np.maximum(a, b))
            V = v if V is None else np.maximum(V, v)
        en |= (V >= T[0]) & (V <= T[1])
    en &= ~mk
    return float(en.mean())


GORUNUR = 0.6       # wp_bakir.dikis: gercek isabet >= %60 (orada boy'a gore; burada kosunun kendisine gore)


def hat_bul(X, O, P, Z, mask_x=None, eski=False):
    """X'te olup orijinal O'da olmayan ince uzun duz cizgiler (kilitli wp_bakir.dikis, oge bantlari +-150 px).
    eski=False (yeni kural, Serdar onayi bekliyor): tasarim alani + kosunun >= %60'i gercek isabet.
    eski=True (onceki kural): filtre yok, dikis'in buldugu ve orijinalde olmayan her cizgi.
    mask_x: X icin murekkep maskesi (None: hat_maskesi(P, X)). Donus: (tum cizgiler, kusur sayilanlar)."""
    W = X.shape[1]
    sm = satirlar(Z, X.shape[0])
    c_o = wb.dikis(O, sm, murekkep=hat_maskesi(P, O))
    mx = hat_maskesi(P, X) if mask_x is None else mask_x
    c_x = []
    for c in wb.dikis(X, sm, murekkep=mx):
        c['gorunur_oran'] = round(gorunur_oran(X, c, mx), 3)
        c['tasarim_alani'] = tasarim_alani(c, W)
        c_x.append(c)
    yeni = [c for c in c_x if not wb.ayni_cizgi(c, c_o)]
    if not eski:
        yeni = [c for c in yeni if c['tasarim_alani'] and c['gorunur_oran'] >= GORUNUR]
    return c_x, yeni


def normal(s):
    return ''.join(c for c in s.lower() if c.isalnum())


def olc(ad, S, P, O, Z, isim1, isim2, mesaj):
    H, W = S.shape[:2]
    m, ink = murekkep(S, P)
    R = {'ad': ad}
    b0 = bantlar(ink)
    top = ink.sum()
    b = [x for x in b0 if ink[x[0]:x[1]].sum() >= 0.002 * top]
    ib = Z['bantlar']['isim']
    # isim bandi: sabitteki isim bandiyla kesisen bant
    isb = [x for x in b if x[0] < ib[1] + 20 and x[1] > ib[0] - 20]
    alt = [x for x in b if isb and x[0] >= isb[0][1]]
    R['bantlar'] = b
    # a) tagline tek kopya + OCR
    a_ok = len(alt) == 1
    ocr_m = ''
    if alt:
        y0, y1 = alt[-1]
        xs = np.nonzero(ink[y0:y1].any(0))[0]
        ocr_m = ocr(ikili(S, P, ink, y0, y1, xs.min(), xs.max() + 1))
    a_ocr = normal(ocr_m) == normal(mesaj)
    R['a_tagline'] = {'isim_alti_metin_bandi': len(alt), 'bantlar': alt, 'ocr': ocr_m,
                      'gecti': bool(a_ok and a_ocr)}
    # b) ust/alt hat: kilitli dedektor, orijinalde olmayan cizgiler
    _, ink_o = murekkep(O, P)
    c_s, yeni = hat_bul(S, O, P, Z)
    _, yeni_e = hat_bul(S, O, P, Z, eski=True)
    R['b_hat'] = {'kural': 'yeni (tasarim alani + gorunur >= %60)', 'cizgi': c_s[:20],
                  'orijinalde_olmayan': yeni[:10], 'gecti': len(yeni) == 0}
    R['b_hat_eski'] = {'kural': 'eski (filtre yok)', 'orijinalde_olmayan': yeni_e[:20], 'sayi': len(yeni_e),
                       'gecti': len(yeni_e) == 0}
    # c) kagit dokusu
    yazi = cv2.dilate((ink | ink_o).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    de = wk.dE(S, O)[~yazi]
    R['c_kagit'] = {'dE_ort': round(float(de.mean()), 3), 'dE_p95': round(float(np.percentile(de, 95)), 3),
                    'dE_p99': round(float(np.percentile(de, 99)), 3), 'esik_ort': 0.5,
                    'gecti': bool(de.mean() <= 0.5)}
    # d) isim harf harf (OCR)
    d = {'gecti': False}
    if isb:
        y0, y1 = isb[0]
        kk = kumeler(ink[y0:y1], 80)
        if len(kk) == 3:
            o1 = ocr(ikili(S, P, ink, y0, y1, *kk[0]), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ')
            o2 = ocr(ikili(S, P, ink, y0, y1, *kk[2]), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ')
            d = {'sol': o1, 'sag': o2, 'beklenen': [isim1, isim2], 'gecti': o1 == isim1 and o2 == isim2,
                 'satir_merkez_x': round((kk[0][0] + kk[2][1]) / 2, 1), 'poster_merkez_x': W / 2}
        else:
            d['sebep'] = f'isim satiri kume sayisi {len(kk)}'
    R['d_isim'] = d
    # bilgi: renk
    renk = {}
    for k, (y0, y1) in Z['bantlar'].items():
        mm = np.zeros_like(ink); mm[y0:y1] = ink[y0:y1]
        v = m[mm]
        if v.size == 0:
            continue
        Lk = float(np.median(v)); dolu = mm & (m >= 0.9 * Lk)
        rgb = S[dolu].mean(0)
        de = lambda ref: round(float(wk.dE(rgb[None, None], np.asarray(ref, np.float32)[None, None])[0, 0]), 2)
        renk[k] = {'rgb': [round(float(x), 1) for x in rgb], 'dE_orijinal': de(Z['renk']['ogeler'][k]['rgb'])}
        if 'bakir' in Z:
            renk[k]['dE_test5'] = de(Z['bakir']['ogeler'][k]['rgb'])
    R['bilgi_renk'] = renk
    R['gecti'] = all(R[k]['gecti'] for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim'))
    R['gecti_eski_kural'] = all(R[k]['gecti'] for k in ('a_tagline', 'b_hat_eski', 'c_kagit', 'd_isim'))
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--motor', required=True)
    ap.add_argument('--isim1', required=True)
    ap.add_argument('--isim2', required=True)
    ap.add_argument('--mesaj', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    P = oku(K / 'plates' / f"{Z['plate']}.png")
    O = oku(K / 'orijinal_WP_11x14.jpg')
    sayfalar = [('orijinal', O, 'SCORPIO', 'VIRGO', 'Two Souls · One Bond'),
                ('test5', oku(K / 'test5_WP_11x14.jpeg'), a.isim1, a.isim2, a.mesaj),
                ('motor', oku(a.motor), a.isim1, a.isim2, a.mesaj)]
    R = {}
    for ad, S, i1, i2, ms in sayfalar:
        R[ad] = olc(ad, S, P, O, Z, i1, i2, ms)
        print(ad, json.dumps({k: R[ad][k] for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'gecti')},
                             ensure_ascii=False), flush=True)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    ok = lambda v: 'PASS' if v else 'FAIL'
    sat = ['| olcum | orijinal | Test 5 eski | yeni motor |', '|---|---|---|---|']
    def h(r, k):
        x = r[k]
        if k == 'a_tagline':
            return f"{ok(x['gecti'])} ({x['isim_alti_metin_bandi']} bant, OCR '{x['ocr']}')"
        if k == 'b_hat':
            return f"{ok(x['gecti'])} ({len(x['orijinalde_olmayan'])} cizgi)"
        if k == 'b_hat_eski':
            return f"{ok(x['gecti'])} ({x['sayi']} cizgi)"
        if k == 'c_kagit':
            return f"{ok(x['gecti'])} (dE ort {x['dE_ort']}, p95 {x['dE_p95']})"
        return f"{ok(x['gecti'])} ({x.get('sol')} / {x.get('sag')})"
    for k, ad in (('a_tagline', 'a) tagline tek kopya'), ('b_hat', 'b) ust/alt hat yok - YENI kural (onay bekliyor)'),
                  ('b_hat_eski', 'b) ust/alt hat yok - ESKI kural'),
                  ('c_kagit', 'c) kagit dokusu (dE <= 0.5)'), ('d_isim', 'd) isim harf harf (OCR)')):
        sat.append(f"| {ad} | {h(R['orijinal'], k)} | {h(R['test5'], k)} | {h(R['motor'], k)} |")
    sat.append(f"| SONUC (yeni kural) | {ok(R['orijinal']['gecti'])} | {ok(R['test5']['gecti'])} | {ok(R['motor']['gecti'])} |")
    sat.append(f"| SONUC (eski kural) | {ok(R['orijinal']['gecti_eski_kural'])} | {ok(R['test5']['gecti_eski_kural'])} | "
               f"{ok(R['motor']['gecti_eski_kural'])} |")
    sat.append('')
    if 'bakir' in Z:
        sat.append('Bakir renk farki, motor vs Test 5 bakiri (dolu murekkep dE): ' + ', '.join(
            f"{k} {v['dE_test5']}" for k, v in R['motor']['bilgi_renk'].items()))
    sat.append('Renk farki orijinale (dE): ' + ', '.join(
        f"{k} {v['dE_orijinal']}" for k, v in R['motor']['bilgi_renk'].items()) + ' (motor); ' + ', '.join(
        f"{k} {v['dE_orijinal']}" for k, v in R['test5']['bilgi_renk'].items()) + ' (Test 5)')
    sat.append('Eski kural cizgileri (motor): ' + (', '.join(
        f"{c['yon']} {c.get('x')} {c.get('y')} gorunur {c['gorunur_oran']}{'' if c['tasarim_alani'] else ' kenar'}"
        for c in R['motor']['b_hat_eski']['orijinalde_olmayan']) or 'yok'))
    Path(a.cikti).with_suffix('.md').write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    sys.exit(0 if R['motor']['gecti'] and R['orijinal']['gecti'] and not R['test5']['gecti'] else 1)


if __name__ == '__main__':
    main()
