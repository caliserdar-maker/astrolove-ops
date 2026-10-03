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
e) harf ici renk bandi: isim ve mesaj kelimelerinde harf cekirdegi satir profilinin yumusatilmisindan sapmasi
                       <= 3.6 luma (renk_bandi; Serdar 3 Eki: deneme 2 "Always" / QUINN ufuk cizgisi)
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
from olc import murekkep, bantlar, kumeler, ORTA, guc                     # noqa: E402

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


def ikili(S, P, ink, y0, y1, x0, x1, pad=20, fx=2):
    """OCR icin: murekkep gucu -> siyah yazi beyaz zemin, fx olcek (varsayilan 2x)."""
    m = guc(S, P)[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
    v = np.clip(255 - m * 2.5, 0, 255).astype(np.uint8)
    return cv2.resize(v, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC if fx > 1 else cv2.INTER_AREA)


def hat_maskesi(P, X):
    """Hat dedektoru maskesi: murekkep gurultu tabani wp_bakir.T0 (4 luma), yalniz gercek murekkebin (olc.murekkep:
    esik 12, bilesen >= 150 px, orta bolge) 20 px cevresinde, wp_bakir.KENAR_PX genisletme. 12 luma esigi tek basina
    italik kilcallari disarida birakip harf aralarini 'cizgi' sayiyordu (3 Eki olcumu)."""
    mm = guc(X, P) > wb.T0
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
    mo = hat_maskesi(P, O)
    mx = hat_maskesi(P, X) if mask_x is None else mask_x
    if 'halka' in Z:
        # halka iki sayfada da tasarim ogesi (orijinalde kahve, bakir baskida bakir): cevresi IKI sayfada da notr
        # (3 Eki, deneme 3: yalniz bakir sayfada murekkep sayilinca halka yanindaki kagit lifi tek tarafta
        # kopruyle 'cizgi' oluyordu, y=1755). Genel birlesim maskesi KULLANILMAZ (Test 5 kusurlarini da siliyordu).
        ah = np.asarray(Image.open(KOK.parent / Z['halka']['dosya']), np.float32) > 5
        hn = cv2.dilate(ah.astype(np.uint8), np.ones((2 * wb.KENAR_PX + 1,) * 2, np.uint8)).astype(bool)
        mo, mx = mo | hn, mx | hn
    c_o = wb.dikis(O, sm, murekkep=mo)
    c_x = []
    for c in wb.dikis(X, sm, murekkep=mx):
        c['gorunur_oran'] = round(gorunur_oran(X, c, mx), 3)
        c['tasarim_alani'] = tasarim_alani(c, W)
        c_x.append(c)
    yeni = [c for c in c_x if not wb.ayni_cizgi(c, c_o)]
    if not eski:
        yeni = [c for c in yeni if c['tasarim_alani'] and c['gorunur_oran'] >= GORUNUR]
    return c_x, yeni


E_CEKIRDEK = 10     # harf ici: ustunde ve altinda >= 10 px murekkep (kabartma kenarin ~5 px icinde kalir)
E_SIGMA = 2.0       # satir profili yumusatma (satir); basamak/ince serit kalir, yumusak gradyan kalmaz
E_ESIK = 3.6        # luma; onayli referanslarin (orijinal + Test 5) olculen en buyugu 3.1 x 1.15 (3 Eki)
# Altin edisyonlarda ayni yontem (onayli referanslarin en buyugu x 1.15, en az 3.6): --e-esik ile verilir.


def renk_bandi(L, ink, Z, esik=None):
    """e) harf ici yatay renk basamagi / bandi: isim ve mesaj bantlarinda her kelime kumesi icin harf cekirdegi
    (dikey E_CEKIRDEK px asindirilmis murekkep) satir ortanca lumasi; profilin kendi E_SIGMA yumusatilmisindan en
    buyuk mutlak sapmasi. Yumusak tasarim gradyani (orijinal altin) sapma vermez; satirda keskin gecis (deneme 2:
    altin plaka profilinin ufuk cizgisi) verir."""
    ce = cv2.erode(ink.astype(np.uint8), np.ones((2 * E_CEKIRDEK + 1, 3), np.uint8)).astype(bool)
    k = int(3 * E_SIGMA)
    g = np.exp(-0.5 * (np.arange(-k, k + 1) / E_SIGMA) ** 2); g /= g.sum()
    sonuc = []
    b0 = bantlar(ink)
    for grup, bosluk in (('isim', 80), ('mesaj', 400)):
        y0s, y1s = Z['bantlar'][grup]
        aday = [b for b in b0 if min(b[1], y1s + 60) > max(b[0], y0s - 60)]
        if not aday:
            continue
        y0, y1 = max(aday, key=lambda b: b[1] - b[0])
        for x0, x1 in kumeler(ink[y0:y1], bosluk):
            if x1 - x0 < 300:
                continue
            ys, v = [], []
            for y in range(y0, y1):
                sel = ce[y, x0:x1]
                if sel.sum() >= 15:
                    ys.append(y); v.append(float(np.median(L[y, x0:x1][sel])))
            if len(v) < 20:
                continue
            v = np.asarray(v)
            sm = np.convolve(np.pad(v, k, mode='edge'), g, 'valid')
            r = np.abs(v - sm)
            i = int(np.argmax(r[3:-3])) + 3
            sonuc.append({'grup': grup, 'x': [int(x0), int(x1)], 'sapma': round(float(r[i]), 2), 'satir': ys[i]})
    en = max((x['sapma'] for x in sonuc), default=0.0)
    esik = esik or E_ESIK
    return {'kelimeler': sonuc, 'en_buyuk': en, 'esik': esik, 'gecti': bool(sonuc) and en <= esik}


def normal(s):
    return ''.join(c for c in s.lower() if c.isalnum())


def olc(ad, S, P, O, Z, isim1, isim2, mesaj, e_esik=None):
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
        # tagline kumesi (kelime boslugu < 400 px kumelerin en genisi; bant icindeki tek yildiz OCR'a girmez)
        xa, xb = max(kumeler(ink[y0:y1], 400 * W / 3307), key=lambda k: k[1] - k[0])
        # tesseract harf yuksekligine duyarli (3 Eki: 16x20 orijinal 'Two' 2x'te 'lwo', 0.5x'te dogru): 2x, 1x, 0.5x
        # sirayla, girdiyle ayni okuyan ilk olcek. Yanlis / cift tagline hicbir olcekte ayni okunmaz.
        for fx in (2, 1, 0.5):
            ocr_m = ocr(ikili(S, P, ink, y0, y1, xa, xb, fx=fx))
            if normal(ocr_m) == normal(mesaj):
                break
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
        kk = kumeler(ink[y0:y1], 80 * W / 3307)
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
    if 'halka' in Z and 'bakir' in Z and 'daire' in Z['bakir']['ogeler']:
        al = np.asarray(Image.open(KOK.parent / Z['halka']['dosya']), np.float32) / 255.0
        dce = al >= 0.9
        rgb = S[dce].mean(0)
        renk['daire'] = {'rgb': [round(float(x), 1) for x in rgb], 'dE_orijinal': round(float(wk.dE(
            rgb[None, None], O[dce].mean(0)[None, None])[0, 0]), 2), 'dE_test5': round(float(wk.dE(
            rgb[None, None], np.asarray(Z['bakir']['ogeler']['daire']['rgb'], np.float32)[None, None])[0, 0]), 2)}
    R['bilgi_renk'] = renk
    R['e_bant'] = renk_bandi(S @ wk.LUMA, ink, Z, e_esik)
    R['gecti'] = all(R[k]['gecti'] for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'e_bant'))
    R['gecti_eski_kural'] = all(R[k]['gecti'] for k in ('a_tagline', 'b_hat_eski', 'c_kagit', 'd_isim', 'e_bant'))
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
    ap.add_argument('--negatif', help='e kapisi negatif testi: bilinen kusurlu sayfa (deneme 2), FAIL beklenir')
    ap.add_argument('--orijinal', help='orijinal satis posteri (varsayilan: KAYNAK/orijinal_WP_11x14.jpg)')
    ap.add_argument('--orijinal-metin', default='SCORPIO|VIRGO|Two Souls · One Bond', help='isim1|isim2|tagline')
    ap.add_argument('--plate-dosya', help='plate (varsayilan: KAYNAK/plates/<plate>.png)')
    ap.add_argument('--test5', help='eski sistem sayfasi (varsayilan: KAYNAK/test5_WP_11x14.jpeg; "yok": kiyas yok)')
    ap.add_argument('--test5-fail', action='store_true', help='prototip oz testi: Test 5 FAIL vermeli')
    ap.add_argument('--e-esik', type=float, help='e esigi (altin edisyon: onayli referanslarin en buyugu x 1.15)')
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    P = oku(a.plate_dosya or K / 'plates' / f"{Z['plate']}.png")
    O = oku(a.orijinal or K / 'orijinal_WP_11x14.jpg')
    o1, o2, om = a.orijinal_metin.split('|')
    t5 = a.test5 or str(K / 'test5_WP_11x14.jpeg')
    sayfalar = [('orijinal', O, o1, o2, om)]
    if t5 != 'yok':
        sayfalar.append(('test5', oku(t5), a.isim1, a.isim2, a.mesaj))
    sayfalar.append(('motor', oku(a.motor), a.isim1, a.isim2, a.mesaj))
    R = {}
    for ad, S, i1, i2, ms in sayfalar:
        R[ad] = olc(ad, S, P, O, Z, i1, i2, ms, a.e_esik)
        print(ad, json.dumps({k: R[ad][k] for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'gecti')},
                             ensure_ascii=False), flush=True)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    ok = lambda v: 'PASS' if v else 'FAIL'
    if 'test5' not in R:
        R['test5'] = None
    sat = ['| olcum | orijinal | Test 5 eski | yeni motor |', '|---|---|---|---|']
    def h(r, k):
        if r is None:
            return '-'
        x = r[k]
        if k == 'a_tagline':
            return f"{ok(x['gecti'])} ({x['isim_alti_metin_bandi']} bant, OCR '{x['ocr']}')"
        if k == 'b_hat':
            return f"{ok(x['gecti'])} ({len(x['orijinalde_olmayan'])} cizgi)"
        if k == 'e_bant':
            return f"{ok(x['gecti'])} (en buyuk {x['en_buyuk']}, esik {x['esik']}; " + ', '.join(
                f"{w['grup']} {w['sapma']}" for w in x['kelimeler']) + ')'
        if k == 'b_hat_eski':
            return f"{ok(x['gecti'])} ({x['sayi']} cizgi)"
        if k == 'c_kagit':
            return f"{ok(x['gecti'])} (dE ort {x['dE_ort']}, p95 {x['dE_p95']})"
        return f"{ok(x['gecti'])} ({x.get('sol')} / {x.get('sag')})"
    for k, ad in (('a_tagline', 'a) tagline tek kopya'), ('b_hat', 'b) ust/alt hat yok - YENI kural (onayli 3 Eki)'),
                  ('b_hat_eski', 'b) ust/alt hat yok - ESKI kural'),
                  ('c_kagit', 'c) kagit dokusu (dE <= 0.5)'), ('d_isim', 'd) isim harf harf (OCR)'),
                  ('e_bant', 'e) harf ici yatay renk bandi yok')):
        sat.append(f"| {ad} | {h(R['orijinal'], k)} | {h(R['test5'], k)} | {h(R['motor'], k)} |")
    t = R['test5'] or {'gecti': None, 'gecti_eski_kural': None}
    ok2 = lambda v: '-' if v is None else ok(v)
    sat.append(f"| SONUC (yeni kural) | {ok(R['orijinal']['gecti'])} | {ok2(t['gecti'])} | {ok(R['motor']['gecti'])} |")
    sat.append(f"| SONUC (eski kural) | {ok(R['orijinal']['gecti_eski_kural'])} | {ok2(t['gecti_eski_kural'])} | "
               f"{ok(R['motor']['gecti_eski_kural'])} |")
    sat.append('')
    if 'bakir' in Z:
        sat.append('Bakir renk farki, motor vs Test 5 bakiri (dolu murekkep dE): ' + ', '.join(
            f"{k} {v['dE_test5']}" for k, v in R['motor']['bilgi_renk'].items()))
    sat.append('Renk farki orijinale (dE): ' + ', '.join(
        f"{k} {v['dE_orijinal']}" for k, v in R['motor']['bilgi_renk'].items()) + ' (motor); ' + ', '.join(
        f"{k} {v['dE_orijinal']}" for k, v in (R['test5'] or {'bilgi_renk': {}})['bilgi_renk'].items()) + ' (Test 5)')
    sat.append('Eski kural cizgileri (motor): ' + (', '.join(
        f"{c['yon']} {c.get('x')} {c.get('y')} gorunur {c['gorunur_oran']}{'' if c['tasarim_alani'] else ' kenar'}"
        for c in R['motor']['b_hat_eski']['orijinalde_olmayan']) or 'yok'))
    neg_ok = True
    if a.negatif:
        Sn = oku(a.negatif)
        en = renk_bandi(Sn @ wk.LUMA, murekkep(Sn, P)[1], Z, a.e_esik)
        R['negatif_e'] = {'dosya': a.negatif, **en}
        neg_ok = not en['gecti']
        sat.append(f"e) negatif test (deneme 2 ciktisi, FAIL beklenir): {ok(en['gecti'])} (en buyuk {en['en_buyuk']}; "
                   + ', '.join(f"{w['grup']} {w['sapma']}" for w in en['kelimeler']) + ') -> kapi '
                   + ('CALISIYOR' if neg_ok else 'CALISMIYOR'))
        Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    Path(a.cikti).with_suffix('.md').write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    t5_ok = not (a.test5_fail and R['test5'] and R['test5']['gecti'])   # prototip oz testi: Test 5 kusurlari FAIL
    sys.exit(0 if R['motor']['gecti'] and R['orijinal']['gecti'] and t5_ok and neg_ok else 1)


if __name__ == '__main__':
    main()
