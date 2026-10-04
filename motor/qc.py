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


QC_W = 3307         # kapi esikleri 11x14 (3307 px) sayfada olculup kalibre edildi (3 Eki); buyuk boylar bu genislige
                    # INTER_AREA ile indirilerek olculur (24x36'da harf ici e orijinalde bile 18, bellek 7 GB)


def oku_n(f, W=None):
    """QC olcegi: genislik QC_W'den buyukse INTER_AREA ile QC_W'ye (orani koruyarak; W verilirse o genislige)."""
    im = Image.open(f).convert('RGB')
    hw = W or QC_W
    if im.width > hw:
        im = im.resize((hw, int(round(im.height * hw / im.width))), Image.BOX)
    return np.asarray(im, np.float32)


def halka_plate(P):
    """Plate'teki halka (altin edisyonlar): yerel arka plandan (31 px medyan) |fark| > 10 luma, genisligi sayfanin
    >= %35'i olan bilesenler (kilitli wp_bakir.daire_maskesi ile ayni olcut, isaretsiz), KENAR_PX genisletme."""
    L = P @ wk.LUMA
    z = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 31).astype(np.float32)
    n, lab, st, _ = cv2.connectedComponentsWithStats((np.abs(z - L) > 10).astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = (st[1:, cv2.CC_STAT_WIDTH] > 0.35 * L.shape[1]) & (st[1:, cv2.CC_STAT_AREA] > 500)
    return cv2.dilate(tut[lab].astype(np.uint8), np.ones((2 * wb.KENAR_PX + 1,) * 2, np.uint8)).astype(bool)


def halka_alfa(Z, shape):
    al = Image.open(KOK.parent / Z['halka']['dosya'])
    if al.size != (shape[1], shape[0]):
        al = al.resize((shape[1], shape[0]), Image.BOX)
    return np.asarray(al, np.float32)


def ocr(img, beyaz=None, psm='7'):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'a.png'
        Image.fromarray(img).save(p)
        kom = ['tesseract', str(p), 'stdout', '--psm', psm]
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
    if 'halka' not in Z and Z.get('mod') == 'altin':
        # altin edisyonlarda halka plate'te (iki sayfada ayni piksel): onayli b kurali (3 Eki) 'halka cevresi yazi
        # sayilir' -> plate'teki halka cevresi iki sayfada da notr (PW 11x14 / 16x20 / A2: halka kenari kosusu)
        hn = halka_plate(P)
        mo, mx = mo | hn, mx | hn
    if 'halka' in Z:
        # halka iki sayfada da tasarim ogesi (orijinalde kahve, bakir baskida bakir): cevresi IKI sayfada da notr
        # (3 Eki, deneme 3: yalniz bakir sayfada murekkep sayilinca halka yanindaki kagit lifi tek tarafta
        # kopruyle 'cizgi' oluyordu, y=1755). Genel birlesim maskesi KULLANILMAZ (Test 5 kusurlarini da siliyordu).
        ah = halka_alfa(Z, X.shape) > 5
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


F_ESIK = 4.0       # f) sembol rengi dE: dogru oturan en buyuk 3.5 (78 cift, CAPRICORN_LIBRA) x 1.15; bozuk 94-102
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
            # profil yalniz bitisik satir parcalarinda (3 Eki, 78 cift: yukselen harf uclari 2 satir, sonra 4 satir
            # bosluk; atlanan satirlar arasindaki tasarim gradyani 'basamak' olcuyordu). Parca >= 2k+1 satir.
            ys_a, v = np.asarray(ys), np.asarray(v)
            kes = np.nonzero(np.diff(ys_a) > 1)[0] + 1
            en_k = None
            for pv, py in zip(np.split(v, kes), np.split(ys_a, kes)):
                if len(pv) < 2 * k + 1:
                    continue
                sm = np.convolve(np.pad(pv, k, mode='edge'), g, 'valid')
                r = np.abs(pv - sm)
                i = int(np.argmax(r[3:-3])) + 3
                if en_k is None or r[i] > en_k[0]:
                    en_k = (float(r[i]), int(py[i]))
            if en_k is None:
                continue
            sonuc.append({'grup': grup, 'x': [int(x0), int(x1)], 'sapma': round(en_k[0], 2), 'satir': en_k[1]})
    en = max((x['sapma'] for x in sonuc), default=0.0)
    esik = esik or E_ESIK
    return {'kelimeler': sonuc, 'en_buyuk': en, 'esik': esik, 'gecti': bool(sonuc) and en <= esik}


def normal(s):
    return ''.join(c for c in s.lower() if c.isalnum())


H_ESIK = 2.7       # h) oge rengi ana sembole dE (Lab); olculen: yeni (tek doku) 3 ornek en buyugu 2.35 x 1.15


def lab(rgb):
    return cv2.cvtColor(np.asarray(rgb, np.float32).reshape(1, 1, 3) / 255, cv2.COLOR_RGB2LAB)[0, 0]


def yildiz_kapisi(S, ink, kutular):
    """g) yazi kutusu + pay icinde parlak nokta (yildiz) var mi. Sayfanin kendi yerel medyanindan > YILDIZ_T, kucuk
    bilesen, yazi murekkebi (3 px genisletilmis) disi. Kutular sayfadan olculur (isim satiri, tagline)."""
    import tek_doku as tdk
    H, W = S.shape[:2]
    pay = int(round(tdk.PAY_ORAN * W))
    bolge = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in kutular:
        bolge[max(0, y0 - pay):min(H, y1 + pay), max(0, x0 - pay):min(W, x1 + pay)] = True
    bolge &= ~cv2.dilate(ink.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    L = S @ wk.LUMA
    Rr = L - tdk.yerel_medyan(L, W)
    n, lab_, st, cen = cv2.connectedComponentsWithStats(((Rr > tdk.YILDIZ_T) & bolge).astype(np.uint8), 8)
    tepe = np.zeros(n, np.float32)
    np.maximum.at(tepe, lab_.ravel(), Rr.ravel())
    ys = [{'x': int(cen[i][0]), 'y': int(cen[i][1]), 'alan': int(st[i, 4]), 'tepe': round(float(tepe[i]), 1)}
          for i in range(1, n) if st[i, 4] <= tdk.YILDIZ_ALAN * (W / 4800) ** 2 and tepe[i] >= YILDIZ_TEPE]
    return {'pay_px': pay, 'yildiz': ys[:10], 'sayi': len(ys), 'gecti': len(ys) == 0}


YILDIZ_TEPE = 25.0  # g) yildiz sayilan en dusuk tepe (luma, QC olcegi); olculen plate yildizlari >= 25, gurultu p99 3


I_ESIK = 0.072      # i) cember boyuna sureklilik (Serdar 3 Eki); olculen: 78 orijinal 0.0589-0.0624 (en buyuk x 1.15);
                   # kusurlu (ornek-tek-doku 644d435) CANCER_LIBRA 0.165, AQUARIUS_LEO 0.168
J_DE = 6.0         # j) zemin dolgu lekesi: zemin blok ortancasindan dE76 (QC olcegi, sigma 1.5 yumusatma)
J_ALAN = 60        # j) leke sayilan en kucuk bilesen (px, QC olcegi); yildiz tepesi >= YILDIZ_TEPE olan bilesen g'nin isi
_HALKA = {}


def _nb(X, M, k):
    num = cv2.blur(np.where(M, X, 0).astype(np.float32), (k, k))
    den = cv2.blur(M.astype(np.float32), (k, k))
    return num / np.maximum(den, 1e-6)


def cember_kapisi(f_sayfa, f_plate):
    """i) cember dokusu surekli mi (tam cozunurluk). Cember plate'ten (yerel 91 px medyandan > 10 luma, genislik
    > %35 W); sayfada cember cekirdegi (zeminden > 40 luma, 5x5 asindirilmis, diger ogelerden 21 px uzak). Olcu:
    cekirdek lumasi 7 px ile 55 px maske-normalize ortalamalarin farki / ortanca -> std (boyuna leke / kopukluk)."""
    if f_plate not in _HALKA:
        P = np.asarray(Image.open(f_plate).convert('RGB'), np.float32) @ wk.LUMA
        z = cv2.medianBlur(np.clip(P, 0, 255).astype(np.uint8), 91).astype(np.float32)
        n, lab_, st, _ = cv2.connectedComponentsWithStats(((P - z) > 10).astype(np.uint8), 8)
        tut = np.zeros(n, bool); tut[1:] = st[1:, cv2.CC_STAT_WIDTH] > 0.35 * P.shape[1]
        _HALKA[f_plate] = (P, z, cv2.dilate(tut[lab_].astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool))
    LP, z, bolge = _HALKA[f_plate]
    L = np.asarray(Image.open(f_sayfa).convert('RGB'), np.float32) @ wk.LUMA
    if L.shape != LP.shape:
        return {'gecti': False, 'sebep': f'boyut {L.shape} plate {LP.shape}'}
    oth = cv2.dilate(((np.abs(L - LP) > 12) & ~bolge).astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool)
    ce = cv2.erode((bolge & ((L - z) > 40)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~oth
    if ce.sum() < 1000:
        return {'gecti': False, 'sebep': 'cember cekirdegi yok', 'px': int(ce.sum())}
    med = float(np.median(L[ce]))
    bp = float(((_nb(L, ce, 7) - _nb(L, ce, 55))[ce] / med).std())
    return {'boyuna_std': round(bp, 4), 'cekirdek_L': round(med, 1), 'px': int(ce.sum()), 'esik': I_ESIK,
            'gecti': bp <= I_ESIK}


def zemin_kapisi(S, ink, kutular):
    """j) yazi kutusu + pay icinde zemin dolgu lekesi (yildiz temizligi dolgusu). Zemin = pay - murekkep (15 px
    genisletilmis); referans = 48 px bloklarda zemin ortanca rengi (murekkep disi), yumusak buyutme. Sayfa (sigma 1.5)
    referanstan dE76 > J_DE, alan >= J_ALAN ve parlaklik tepesi < YILDIZ_TEPE (yildiz degil) bilesen = leke."""
    import tek_doku as tdk
    H, W = S.shape[:2]
    pay = int(round(tdk.PAY_ORAN * W))
    bolge = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in kutular:
        bolge[max(0, y0 - pay):min(H, y1 + pay), max(0, x0 - pay):min(W, x1 + pay)] = True
    zem = bolge & ~cv2.dilate(ink.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    B = 48
    gh_, gw_ = (H + B - 1) // B, (W + B - 1) // B
    ref = np.zeros((gh_, gw_, 3), np.float32); var = np.zeros((gh_, gw_), bool)
    for i in range(gh_):
        for j in range(gw_):
            mm = zem[i * B:(i + 1) * B, j * B:(j + 1) * B]
            if mm.sum() >= 0.3 * mm.size:
                ref[i, j] = np.median(S[i * B:(i + 1) * B, j * B:(j + 1) * B][mm], 0); var[i, j] = True
    if not var.any():
        return {'gecti': True, 'leke': [], 'sayi': 0, 'not': 'zemin yok'}
    yi, xi = np.nonzero(var)
    for i in range(gh_):                                               # bos bloklar: en yakin dolu blok
        for j in range(gw_):
            if not var[i, j]:
                k = np.argmin((yi - i) ** 2 + (xi - j) ** 2); ref[i, j] = ref[yi[k], xi[k]]
    ref = cv2.resize(ref, (gw_ * B, gh_ * B), interpolation=cv2.INTER_LINEAR)[:H, :W]
    de = wk.dE(cv2.GaussianBlur(S, (0, 0), 1.5), ref)
    L = S @ wk.LUMA
    Rr = L - tdk.yerel_medyan(L, W)
    n, lab_, st, cen = cv2.connectedComponentsWithStats(((de > J_DE) & zem).astype(np.uint8), 8)
    tepe = np.zeros(n, np.float32); np.maximum.at(tepe, lab_.ravel(), Rr.ravel())
    dm = np.zeros(n, np.float32); np.maximum.at(dm, lab_.ravel(), de.ravel())
    ls = [{'x': int(cen[i][0]), 'y': int(cen[i][1]), 'alan': int(st[i, 4]), 'dE': round(float(dm[i]), 1),
           'tepe': round(float(tepe[i]), 1)} for i in range(1, n) if st[i, 4] >= J_ALAN and tepe[i] < YILDIZ_TEPE]
    return {'leke': ls[:10], 'sayi': len(ls), 'esik': {'dE': J_DE, 'alan': J_ALAN}, 'gecti': not ls}


K_ARTIS = 0.05     # k) radyal profil: %1'lik halkalarda ortalama luma disa dogru en fazla bu kadar artabilir. Olculen (3 Eki):
                   # gradient zemin -0.018 (hep azalan); plate zeminli ornekler (ornek-tek-doku e12fad7) +0.15 / +0.23 / +0.27
K_LEKE = 0.50      # k) yerel leke: zemin (sigma 10 px yumusak) - radyal profil, |fark| p99.9 (luma, QC olcegi). Olculen:
                   # gradient + dither 0.05; plate zeminli ornekler ve orijinal 2.98 - 3.01


def zemin_gradient_kapisi(S, P, ink, plate_ad):
    """k) zemin puruzsuz radyal gradient mi (Serdar 3 Eki ek). Geometri: varlik/plates/<plate>_gradient.json (cember
    merkezi, 4:5 elips). Zemin = murekkep (15 px), yildiz (yerel medyandan > 4, 25 px) ve plate cemberi (15 px) disi.
    (1) tekduzelik: %1'lik s halkalarinda ortalama luma disa dogru K_ARTIS'tan fazla artmaz; (2) leke: maskeli Gauss
    (10 px) zemin - halka profili, |fark| p99.9 <= K_LEKE."""
    import tek_doku as tdk
    gf = KOK / 'varlik' / 'plates' / f'{plate_ad}_gradient.json'
    if not gf.exists():
        return {'gecti': False, 'sebep': f'{gf.name} yok'}
    g = json.loads(gf.read_text())['gradient']
    H, W = S.shape[:2]
    f = W / 4800
    cx, cy = g['merkez'][0] * f, g['merkez'][1] * f
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sh = np.hypot(xx - cx, (yy - cy) / g['elips']) / (g['kose'] * f)
    L = S @ wk.LUMA
    R = L - tdk.yerel_medyan(L, W)
    yil = cv2.dilate((R > 4).astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    hm = cv2.dilate(halka_plate(P).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    zem = ~cv2.dilate(ink.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~yil & ~hm
    b = np.clip((sh * 100).astype(int), 0, 99)
    n = np.bincount(b[zem], minlength=100)
    mo = np.bincount(b[zem], L[zem], 100) / np.maximum(n, 1)
    ok = np.nonzero(n >= 500)[0]
    artis = np.diff(mo[ok])
    en_artis = float(artis.max()) if artis.size else 0.0
    prof = np.interp(sh, (ok + 0.5) / 100, mo[ok]).astype(np.float32)
    num = cv2.GaussianBlur(np.where(zem, L, 0).astype(np.float32), (0, 0), 10)
    den = cv2.GaussianBlur(zem.astype(np.float32), (0, 0), 10)
    ic = zem & (den > 0.5)
    res = np.abs(num / np.maximum(den, 1e-6) - prof)[ic]
    leke = float(np.percentile(res, 99.9)) if res.size else 0.0
    return {'en_artis': round(en_artis, 3), 'artis_esik': K_ARTIS, 'leke_p999': round(leke, 3), 'leke_esik': K_LEKE,
            'zemin_px': int(zem.sum()), 'gecti': en_artis <= K_ARTIS and leke <= K_LEKE}


L_SEKIL = 0.10     # l) cember ucu: normalize kesit alani egrisi, orijinalden ortalama mutlak fark (esik olcumle, 4 Eki)
L_RENK = 0.15      # l) cember ucu: tepe rengi altin doygunlugu (orijinal govdeye gore) ortalama mutlak fark
M_Q = 0.03         # m) kabartma: (qc, qs) / core, ana sembolden ortalama vektor farki (goreli derinlik kutulari)
M_ACI = 25.0       # m) kabartma: kenar bandi isik yonu acisi farki (derece); vurgu-golge / core < 0.02 ise uygulanmaz


def _kesit(P, geo, a, d=np.arange(-14, 14.01, 0.5)):
    cx, cy = geo['merkez']
    k = int(round((a + 180) / geo['dilim_derece'])) % len(geo['rc'])
    r0 = geo['R'] + geo['rc'][k]
    t = np.radians(a)
    xs = (cx + (r0 + d) * np.cos(t)).astype(np.float32)[None]
    ys = (cy + (r0 + d) * np.sin(t)).astype(np.float32)[None]
    smp = np.stack([cv2.remap(np.ascontiguousarray(P[..., c]), xs, ys, cv2.INTER_LINEAR)[0] for c in range(3)], -1)
    L = smp @ wk.LUMA
    bg = np.median(np.r_[L[:6], L[-6:]])
    ex = np.clip(L - bg, 0, None)
    i = int(np.argmax(ex))
    rgb = smp[i]
    return float(ex.sum() * 0.5), float((rgb[0] - rgb[2]) / max(rgb.sum(), 1.0))


def uc_kapisi(f_sayfa, f_orijinal, plate_ad):
    """l) cemberin iki ucu (Serdar 4 Eki): uc acisindan -14 / +3 derece, 0.5 derece adimla radyal kesit; kesit alani
    (luma fazlasi) ve tepe rengi altin doygunlugu (R - B) / toplam, -14..-11 derece govdesine normalize. Orijinal posterle
    ortalama mutlak fark: sekil <= L_SEKIL, renk <= L_RENK (renk yalniz orijinal alan > %5 olan acilarda)."""
    gf = KOK / 'varlik' / 'plates' / f'{plate_ad}_halkasiz.json'
    if not gf.exists():
        return {'gecti': False, 'sebep': f'{gf.name} yok'}
    geo = json.loads(gf.read_text())['halka']['geometri']
    hw = np.asarray(geo['hw'])
    nb = len(hw)
    ang = np.arange(nb) * geo['dilim_derece'] - 180
    bos = np.nonzero(hw <= 0.02)[0]
    # en uzun bos aci araligi = cemberin acik oldugu yer; uclari sinirlari
    uclar = [(float(ang[(bos.min() - 1) % nb]), -1), (float(ang[(bos.max() + 1) % nb]), 1)]
    S = np.asarray(Image.open(f_sayfa).convert('RGB'), np.float32)
    O = np.asarray(Image.open(f_orijinal).convert('RGB'), np.float32)
    out = {}
    ok = True
    for ad, (a_uc, yon) in zip(('sag_uc', 'sol_uc'), uclar):
        angs = a_uc + yon * np.arange(-14, 3.01, 0.5) * -1 if yon < 0 else a_uc - np.arange(-14, 3.01, 0.5)
        ks = [_kesit(S, geo, a) for a in angs]
        ko = [_kesit(O, geo, a) for a in angs]
        As, Cs = np.array([k[0] for k in ks]), np.array([k[1] for k in ks])
        Ao, Co = np.array([k[0] for k in ko]), np.array([k[1] for k in ko])
        rs, ro = max(As[:7].mean(), 1e-3), max(Ao[:7].mean(), 1e-3)
        cs, co = max(Cs[:7].mean(), 1e-3), max(Co[:7].mean(), 1e-3)
        sek = float(np.abs(As / rs - Ao / ro).mean())
        v = Ao / ro > 0.05
        ren = float(np.abs(Cs[v] / cs - Co[v] / co).mean()) if v.any() else 0.0
        g = sek <= L_SEKIL and ren <= L_RENK
        ok &= g
        out[ad] = {'uc_aci': round(a_uc, 2), 'sekil': round(sek, 3), 'renk': round(ren, 3), 'gecti': g}
    return {**out, 'esik': {'sekil': L_SEKIL, 'renk': L_RENK}, 'gecti': bool(ok)}


def kabartma_kapisi(f_sayfa, f_zemin, P, Z, isb, alt, ink, W_qc):
    """m) kabartma stili (Serdar 4 Eki): her oge (isimler, sonsuz, kucuk semboller, tagline, cember) icin tam
    cozunurlukte tek_doku.stil_olc (goreli derinlik t kutularinda L = p + qc cos th + qs sin th); ana sembolle:
    (qc, qs) / core ortalama vektor farki <= M_Q ve kenar bandi isik acisi farki <= M_ACI."""
    import tek_doku as tdk
    S = np.asarray(Image.open(f_sayfa).convert('RGB'), np.float32)
    Zm = np.asarray(Image.open(f_zemin).convert('RGB'), np.float32)
    H, W = S.shape[:2]
    f = W / W_qc
    hm = cv2.resize(halka_plate(P).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    L = S @ wk.LUMA
    D = L - Zm @ wk.LUMA
    bolge = {}
    for k in ('buyuk_sembol', 'kucuk_sembol'):
        y0, y1 = Z['bantlar'][k]
        mm = np.zeros((H, W), bool); mm[int(y0 * f):int(y1 * f)] = True
        bolge[k] = mm & ~hm
    if isb:
        y0, y1 = isb[0]
        kk = kumeler(ink[y0:y1], 80 * W_qc / 3307)
        if len(kk) == 3:
            for ad, (x0, x1) in zip(('isim_sol', 'sonsuz', 'isim_sag'), kk):
                mm = np.zeros((H, W), bool); mm[int(y0 * f):int(y1 * f), int(x0 * f):int(x1 * f)] = True
                bolge[ad] = mm
    if alt:
        y0, y1 = alt[-1]
        mm = np.zeros((H, W), bool); mm[int(y0 * f):int(y1 * f)] = True
        bolge['mesaj'] = mm
    bolge['cember'] = cv2.dilate(hm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    st = {}
    for ad, mm in bolge.items():
        ys, xs = np.nonzero(mm)
        if ys.size == 0:
            continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        d = np.where(mm[y0:y1, x0:x1], D[y0:y1, x0:x1], 0)
        if (d > 40).sum() < 200:
            continue
        A = np.clip(d / np.median(d[d > 40]), 0, 1)
        st[ad] = tdk.stil_olc(A, L[y0:y1, x0:x1], W)
    if 'buyuk_sembol' not in st:
        return {'gecti': False, 'sebep': 'ana sembol yok'}
    ref = st['buyuk_sembol']
    vec = lambda s_: np.stack([s_['qc'], s_['qs']], 1) / max(max(s_['p']), 1.0)
    out = {}
    ok = True
    for ad, s_ in st.items():
        if ad == 'buyuk_sembol':
            continue
        dq = float(np.linalg.norm(vec(s_) - vec(ref), axis=1).mean())
        da = abs((s_['isik_aci'] - ref['isik_aci'] + 180) % 360 - 180)
        guclu = s_['vurgu_golge_kenar'] / max(max(s_['p']), 1.0) >= 0.02
        g = dq <= M_Q and (da <= M_ACI or not guclu)
        ok &= g
        out[ad] = {'dq': round(dq, 4), 'isik_aci': s_['isik_aci'], 'aci_farki': round(float(da), 1),
                   'vurgu_golge': s_['vurgu_golge_kenar'], 'gecti': bool(g)}
    return {'ana_sembol': {'isik_aci': ref['isik_aci'], 'vurgu_golge': ref['vurgu_golge_kenar']}, 'ogeler': out,
            'esik': {'dq': M_Q, 'aci': M_ACI}, 'gecti': bool(ok)}


def oge_renkleri(S, P, ink, m, Z, isb, alt):
    """h) ogelerin dolu murekkep ortalama rengi ve cekirdek lumasi; referans buyuk sembol."""
    H, W = S.shape[:2]
    hm = halka_plate(P)
    r = {}

    def ekle(ad, mm):
        mm = mm & ink
        if mm.sum() < 50:
            return
        Lk = np.median(m[mm]); d = mm & (m >= 0.9 * Lk)
        # tam kaplama: 3x3 asindirilmis murekkep cekirdegi, ortanca renk (ince oge kenar karisimi ve dagilim genisligi
        # etkisiz; 'dolu' ortalamasi genis dagilimli ana sembolu ust yariya kaydiriyordu)
        ce = cv2.erode(mm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        ce = ce if ce.sum() >= 50 else mm
        r[ad] = {'rgb': np.median(S[ce], 0), 'L': float(np.median(S[ce] @ wk.LUMA))}
    for k in ('buyuk_sembol', 'kucuk_sembol'):
        y0, y1 = Z['bantlar'][k]
        mm = np.zeros((H, W), bool); mm[y0:y1] = True
        ekle(k, mm & ~hm)
    if isb:
        y0, y1 = isb[0]
        kk = kumeler(ink[y0:y1], 80 * W / 3307)
        if len(kk) == 3:
            for ad, (x0, x1) in zip(('isim_sol', 'sonsuz', 'isim_sag'), kk):
                mm = np.zeros((H, W), bool); mm[y0:y1, x0:x1] = True
                ekle(ad, mm)
    if alt:
        y0, y1 = alt[-1]
        mm = np.zeros((H, W), bool); mm[y0:y1] = True
        ekle('mesaj', mm)
    L = S @ wk.LUMA
    z = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 31).astype(np.float32)
    hc = hm & (np.abs(L - z) > 40)
    hc = cv2.erode(hc.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) if hc.sum() > 500 else hc
    if hc.sum() > 50:
        r['halka'] = {'rgb': np.median(S[hc], 0), 'L': float(np.median(L[hc]))}
    if 'buyuk_sembol' not in r:
        return {'gecti': False, 'sebep': 'buyuk sembol yok'}
    ref = r['buyuk_sembol']
    out = {k: {'dE': round(float(np.linalg.norm(lab(v['rgb']) - lab(ref['rgb']))), 2),
               'dL': round(v['L'] - ref['L'], 1), 'rgb': [round(float(x), 1) for x in v['rgb']]} for k, v in r.items()}
    en = max(v['dE'] for k, v in out.items() if k != 'buyuk_sembol')
    return {'ogeler': out, 'en_buyuk': en, 'esik': H_ESIK, 'gecti': en <= H_ESIK}


def olc(ad, S, P, O, Z, isim1, isim2, mesaj, e_esik=None, gh=False, tam=None, Pz=None, tam_zemin=None):
    H, W = S.shape[:2]
    # Pz: bu sayfanin zemini (gradient zeminli motor sayfasi: ZEMIN.png); yoksa plate
    Pz = P if Pz is None else Pz
    m, ink = murekkep(S, Pz)
    R = {'ad': ad}
    b0 = bantlar(ink)
    top = ink.sum()
    # metin bandi: murekkebin >= %0.5'i (3 Eki olcumu: WP 18x24 orijinal kagit lekesi bandi %0.21; Test 5 11x14 cift
    # tagline parcasi %0.97 -> FAIL kalir)
    b = [x for x in b0 if ink[x[0]:x[1]].sum() >= 0.005 * top]
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
            ocr_m = ocr(ikili(S, Pz, ink, y0, y1, xa, xb, fx=fx))
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
    # gradient zeminli sayfa: kagit dokusu kendi zeminine (ZEMIN.png) karsi; plate zeminli sayfa: orijinale
    de = wk.dE(S, O if Pz is P else Pz)[~yazi]
    R['c_kagit'] = {'dE_ort': round(float(de.mean()), 3), 'dE_p95': round(float(np.percentile(de, 95)), 3),
                    'dE_p99': round(float(np.percentile(de, 99)), 3), 'esik_ort': 0.5,
                    'gecti': bool(de.mean() <= 0.5)}
    # d) isim harf harf (OCR)
    d = {'gecti': False}
    if isb:
        y0, y1 = isb[0]
        kk = kumeler(ink[y0:y1], 80 * W / 3307)
        if len(kk) == 3:
            # tagline ile ayni olcek sirasi (2x, 1x, 0.5x; 3 Eki 78 cift: SIENNA 2x'te 'STENNA'); beklenenle ayni
            # okuyan ilk olcek. Yanlis dizilmis isim hicbir olcekte ayni okunmaz.
            def oku_isim(k, bek):
                # tek kelime: psm 7 (satir) sonra psm 8 (kelime; 3 Eki: SIENNA psm 7'de her olcekte 'STENNA')
                for fx in (2, 1, 0.5):
                    for psm in ('7', '8'):
                        o = ocr(ikili(S, Pz, ink, y0, y1, *k, fx=fx), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', psm)
                        if o == bek:
                            return o
                return ocr(ikili(S, Pz, ink, y0, y1, *k), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ')
            o1, o2 = oku_isim(kk[0], isim1), oku_isim(kk[2], isim2)
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
        al = halka_alfa(Z, S.shape) / 255.0
        dce = al >= 0.9
        rgb = S[dce].mean(0)
        renk['daire'] = {'rgb': [round(float(x), 1) for x in rgb], 'dE_orijinal': round(float(wk.dE(
            rgb[None, None], O[dce].mean(0)[None, None])[0, 0]), 2), 'dE_test5': round(float(wk.dE(
            rgb[None, None], np.asarray(Z['bakir']['ogeler']['daire']['rgb'], np.float32)[None, None])[0, 0]), 2)}
    R['bilgi_renk'] = renk
    R['e_bant'] = renk_bandi(S @ wk.LUMA, ink, Z, e_esik)
    if gh:
        # g) yazi cevresi yildiz (Serdar 3 Eki B); h) tek doku: ogeler ana sembole gore (yalniz motor sayfasinda kapi)
        kut = []
        for bnt in (isb[:1] + alt[-1:]):
            y0, y1 = bnt
            xs = np.nonzero(ink[y0:y1].any(0))[0]
            if bnt in alt:
                xa, xb = max(kumeler(ink[y0:y1], 400 * W / 3307), key=lambda k: k[1] - k[0])
            else:
                xa, xb = xs.min(), xs.max() + 1
            kut.append((int(xa), int(y0), int(xb), int(y1)))
        R['g_yildiz'] = yildiz_kapisi(S, ink, kut)
        R['h_tek_doku'] = oge_renkleri(S, P, ink, m, Z, isb, alt)
        # i) cember dokusu surekliligi (tam cozunurluk); j) yazi cevresi zemin dolgu lekesi (Serdar 3 Eki goz kontrolu)
        R['i_cember'] = cember_kapisi(*tam) if tam else {'gecti': False, 'sebep': 'tam cozunurluk sayfa yok'}
        R['j_zemin'] = zemin_kapisi(S, ink, kut)
        R['k_gradient'] = zemin_gradient_kapisi(S, P, ink, Z['plate'])
        if ad == 'motor' and tam and tam_zemin:
            # l) cember uclari orijinale; m) kabartma stili ana sembole (Serdar 4 Eki; yalniz motor sayfasinda kapi)
            R['l_uc'] = uc_kapisi(tam[0], tam_zemin[1], Z['plate'])
            R['m_kabartma'] = kabartma_kapisi(tam[0], tam_zemin[0], P, Z, isb, alt, ink, W)
    # f) sembol sadakati (altin edisyon; 3 Eki 78 cift: 10 ciftte ana sembol yanlis oturmus, dE 94-102, a-e gecmisti):
    # buyuk / kucuk sembol dolu murekkep rengi orijinalden dE <= F_ESIK. WP bakir tasarim geregi farkli (Test 5 kiyasi).
    if Z.get('mod') == 'altin':
        # tek doku (gh): kucuk semboller ana sembol modeline baglandi (h olcer); f yalniz ana sembol x orijinal
        fd = {k: renk.get(k, {}).get('dE_orijinal') for k in (('buyuk_sembol',) if gh else ('buyuk_sembol', 'kucuk_sembol'))}
        R['f_sembol'] = {'dE': fd, 'esik': F_ESIK, 'gecti': all(v is not None and v <= F_ESIK for v in fd.values())}
    else:
        R['f_sembol'] = {'uygulanmaz': 'bakir (WP)', 'gecti': True}
    K5 = ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'e_bant', 'f_sembol') + (('g_yildiz', 'i_cember', 'j_zemin') if gh else ()) + \
        (('h_tek_doku', 'k_gradient', 'l_uc', 'm_kabartma') if gh and ad == 'motor' else ())
    R['gecti'] = all(R[k]['gecti'] for k in K5)
    R['gecti_eski_kural'] = all(R[k]['gecti'] for k in ('a_tagline', 'b_hat_eski', 'c_kagit', 'd_isim', 'e_bant', 'f_sembol'))
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
    ap.add_argument('--zemin-motor', help='motor sayfasinin zemini (gradient: hucre/ZEMIN.png); murekkep ve c kapisi')
    ap.add_argument('--plate-dosya', help='plate (varsayilan: KAYNAK/plates/<plate>.png)')
    ap.add_argument('--test5', help='eski sistem sayfasi (varsayilan: KAYNAK/test5_WP_11x14.jpeg; "yok": kiyas yok)')
    ap.add_argument('--test5-fail', action='store_true', help='prototip oz testi: Test 5 FAIL vermeli')
    ap.add_argument('--gh', action='store_true', help='g (yazi cevresi yildiz) + h (tek doku, yalniz motor) kapilari')
    ap.add_argument('--e-esik', type=float, help='e esigi (altin edisyon: onayli referanslarin en buyugu x 1.15)')
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    P = oku_n(a.plate_dosya or K / 'plates' / f"{Z['plate']}.png")
    O = oku_n(a.orijinal or K / 'orijinal_WP_11x14.jpg')
    f = P.shape[1] / Z['tuval'][0]
    if f != 1:                                                         # sabit koordinatlari QC olcegine
        Z = json.loads(json.dumps(Z))
        Z['bantlar'] = {k: [int(round(v[0] * f)), int(round(v[1] * f))] for k, v in Z['bantlar'].items()}
    R0 = {'qc_olcek': {'tuval': Z['tuval'], 'qc_px': [P.shape[1], P.shape[0]], 'oran': round(f, 5)}}
    o1, o2, om = a.orijinal_metin.split('|')
    t5 = a.test5 or str(K / 'test5_WP_11x14.jpeg')
    sayfalar = [('orijinal', O, o1, o2, om)]
    if t5 != 'yok':
        sayfalar.append(('test5', oku_n(t5, P.shape[1]), a.isim1, a.isim2, a.mesaj))
    sayfalar.append(('motor', oku_n(a.motor, P.shape[1]), a.isim1, a.isim2, a.mesaj))
    R = dict(R0)
    for ad, S, i1, i2, ms in sayfalar:
        fp = str(a.plate_dosya or K / 'plates' / f"{Z['plate']}.png")
        tam = {'orijinal': (str(a.orijinal or K / 'orijinal_WP_11x14.jpg'), fp), 'motor': (a.motor, fp)}.get(ad)
        Pz = oku_n(a.zemin_motor, P.shape[1]) if (ad == 'motor' and a.zemin_motor) else None
        tz = (a.zemin_motor or fp, str(a.orijinal or K / 'orijinal_WP_11x14.jpg')) if ad == 'motor' else None
        R[ad] = olc(ad, S, P, O, Z, i1, i2, ms, a.e_esik, a.gh, tam, Pz, tz)
        print(ad, json.dumps({k: R[ad][k] for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'gecti')},
                             ensure_ascii=False), flush=True)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    ok = lambda v: 'PASS' if v else 'FAIL'
    if 'test5' not in R:
        R['test5'] = None
    sat = ['| olcum | orijinal | Test 5 eski | yeni motor |', '|---|---|---|---|']
    def h(r, k):
        if r is None or k not in r:
            return '-'
        x = r[k]
        if k == 'a_tagline':
            return f"{ok(x['gecti'])} ({x['isim_alti_metin_bandi']} bant, OCR '{x['ocr']}')"
        if k == 'b_hat':
            return f"{ok(x['gecti'])} ({len(x['orijinalde_olmayan'])} cizgi)"
        if k == 'e_bant':
            return f"{ok(x['gecti'])} (en buyuk {x['en_buyuk']}, esik {x['esik']}; " + ', '.join(
                f"{w['grup']} {w['sapma']}" for w in x['kelimeler']) + ')'
        if k == 'g_yildiz':
            return f"{ok(x['gecti'])} ({x['sayi']} nokta, pay {x['pay_px']} px)"
        if k == 'h_tek_doku':
            if 'ogeler' not in x:
                return f"{ok(x['gecti'])} ({x.get('sebep')})"
            return f"{ok(x['gecti'])} (en buyuk dE {x['en_buyuk']}, esik {x['esik']}; " + ', '.join(
                f"{k2} {v['dE']}" for k2, v in x['ogeler'].items() if k2 != 'buyuk_sembol') + ')'
        if k == 'i_cember':
            return f"{ok(x['gecti'])} (boyuna std {x.get('boyuna_std', x.get('sebep'))}, esik {I_ESIK})"
        if k == 'j_zemin':
            return f"{ok(x['gecti'])} ({x['sayi']} leke)"
        if k == 'l_uc':
            if 'sag_uc' not in x:
                return f"{ok(x['gecti'])} ({x.get('sebep')})"
            return f"{ok(x['gecti'])} (sag sekil {x['sag_uc']['sekil']} renk {x['sag_uc']['renk']}; sol sekil " \
                   f"{x['sol_uc']['sekil']} renk {x['sol_uc']['renk']})"
        if k == 'm_kabartma':
            if 'ogeler' not in x:
                return f"{ok(x['gecti'])} ({x.get('sebep')})"
            return f"{ok(x['gecti'])} (ana isik {x['ana_sembol']['isik_aci']}; " + ', '.join(
                f"{k2} dq {v['dq']} aci {v['aci_farki']}" for k2, v in x['ogeler'].items()) + ')'
        if k == 'k_gradient':
            if 'en_artis' not in x:
                return f"{ok(x['gecti'])} ({x.get('sebep')})"
            return f"{ok(x['gecti'])} (artis {x['en_artis']} / {K_ARTIS}, leke {x['leke_p999']} / {K_LEKE})"
        if k == 'f_sembol':
            return f"{ok(x['gecti'])} ({x.get('dE', x.get('uygulanmaz'))})"
        if k == 'b_hat_eski':
            return f"{ok(x['gecti'])} ({x['sayi']} cizgi)"
        if k == 'c_kagit':
            return f"{ok(x['gecti'])} (dE ort {x['dE_ort']}, p95 {x['dE_p95']})"
        return f"{ok(x['gecti'])} ({x.get('sol')} / {x.get('sag')})"
    for k, ad in (('a_tagline', 'a) tagline tek kopya'), ('b_hat', 'b) ust/alt hat yok - YENI kural (onayli 3 Eki)'),
                  ('b_hat_eski', 'b) ust/alt hat yok - ESKI kural'),
                  ('c_kagit', 'c) kagit dokusu (dE <= 0.5)'), ('d_isim', 'd) isim harf harf (OCR)'),
                  ('e_bant', 'e) harf ici yatay renk bandi yok'), ('f_sembol', 'f) sembol rengi orijinale (altin)'),
                  ('g_yildiz', 'g) yazi cevresi yildiz yok'), ('h_tek_doku', 'h) tek doku: ana sembole dE (motor kapi)'),
                  ('i_cember', 'i) cember dokusu surekli'), ('j_zemin', 'j) yazi cevresi zemin dolgu lekesi yok'),
                  ('k_gradient', 'k) zemin puruzsuz radyal gradient (motor kapi)'),
                  ('l_uc', 'l) cember uclari orijinal gibi (motor kapi)'), ('m_kabartma', 'm) kabartma stili ana sembol (motor kapi)')):
        if k not in R['motor']:
            continue
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
        Sn = oku_n(a.negatif, P.shape[1])
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
