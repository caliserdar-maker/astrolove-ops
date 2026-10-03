#!/usr/bin/env python3
"""MOTOR olcum (3 Eki 2026, Serdar onayi): satistaki orijinal posterden konum / olcek / renk sabitleri.
Tahmin yok: her sayi orijinal poster (POD_PRINT/<cift>/<renk>/<boy>.jpg) - kagit (PLATES) farkindan olculur.

m = kagit lumasi - poster lumasi (murekkep gucu, wp_katman.ESIK ile ayni esik). Ogeler satir bantlariyla ayrilir:
buyuk_sembol, kucuk_sembol (sol/sag), isim satiri (sol isim, sonsuz, sag isim), mesaj (tagline).
Katman yerlesimi: katman alfasi (> 0.5) kutusu orijinal oge kutusuna oturtulur, sonra +-%3 olcek / +-6 px kayma
araliginda alfa ile m arasindaki NCC en buyuk secilir. Isim ve tagline puntosu: harf govdesi (buyuk harf, inen
harf yok) yuksekligi fonttan olculerek esitlenir.

Kullanim: olc.py --kaynak DIR --cift SCORPIO_VIRGO --renk WARM_PARCHMENT --boy 11x14 --plate VINTAGE_B3_11x14 \
          --cikti motor/sabitler/SCORPIO_VIRGO_WP_11x14.json
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent / 'kilitli'))
import wp_katman as wk                                                # noqa: E402 (kilitli, degistirilmedi)

Image.MAX_IMAGE_PIXELS = None
FONT = Path(__file__).resolve().parent / 'font'
ORAN = {'16x20': '4x5', '8x10': '4x5', '18x24': '3x4', '12x16': '3x4', '24x36': '2x3', '12x18': '2x3', '11x14': '11x14',
        'A2': 'A', 'A3': 'A', 'A4': 'A'}
TAG_SINIR = {'2x3': 1905, '3x4': 1788, '4x5': 1670, '11x14': 1694, 'A': 1788}   # kisisel-v1 ORAN_SABITLERI (2400 px)
MIN_ALAN = 150         # gurultu bileseni alt siniri (olculen: kagit benekleri kenar seritlerinde, tagline noktasi > 150)
ORTA = (0.10, 0.90)    # tasarim ogeleri bu yatay aralikta (kenar payi %10); disi kagit dokusu


def oku(f, mod='RGB'):
    return np.asarray(Image.open(f).convert(mod), np.float32)


def isaret(P):
    """+1: acik kagit (murekkep kagittan koyu); -1: koyu kagit (MIDNIGHT_BLUE / DEEP_BLACK, altin kagittan acik)."""
    return -1.0 if float(np.median(P[::16, ::16] @ wk.LUMA)) < 128 else 1.0


def guc(S, P):
    """murekkep gucu: |kagit - poster| lumasi, kagit yonune gore isaretli (acik kagitta P - S)."""
    return np.clip(((P - S) @ wk.LUMA) * isaret(P), 0, None)


def murekkep(S, P):
    m = guc(S, P)
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > wk.ESIK).astype(np.uint8), 8)
    W = m.shape[1]
    cx = st[:, cv2.CC_STAT_LEFT] + st[:, cv2.CC_STAT_WIDTH] / 2
    tut = np.zeros(n, bool)
    q2 = (W / 3307) ** 2                                               # alan esigi 11x14'te olculdu; boyla olceklenir
    tut[1:] = (st[1:, cv2.CC_STAT_AREA] >= MIN_ALAN * q2) & (cx[1:] > ORTA[0] * W) & (cx[1:] < ORTA[1] * W)
    return m, tut[lab]


def halka_maskesi(P):
    """Plate'teki halka (tasarim cemberi): yerel kagittan (medyan pencere 31 px @ 3307, buyuk boyda 62 x oran)
    |fark| > 10 luma, genisligi sayfanin >= %35'i olan bilesenler; W x 0.006 px genisletilir. 3 Eki (78 cift): 10
    ciftin orijinalinde halka plate'tekiyle birebir cakismiyor, fark ana sembol kutusuna giriyordu (NCC 0.07)."""
    L = P @ wk.LUMA
    W = L.shape[1]
    kw = 31 if W == 3307 else int(round(62 * W / 3307)) | 1
    z = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), kw).astype(np.float32)
    n, lab, st, _ = cv2.connectedComponentsWithStats((np.abs(z - L) > 10).astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = (st[1:, cv2.CC_STAT_WIDTH] > 0.35 * W) & (st[1:, cv2.CC_STAT_AREA] > 500 * (W / 3307) ** 2)
    r = max(1, int(round(0.006 * W)))
    return cv2.dilate(tut[lab].astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)).astype(bool)


NCC_MIN = 0.80      # ana sembol oturtma alt siniri (olculen: dogru oturan 0.88-0.98, bozuk 0.07)


def bantlar(ink, bosluk=40):
    on = ink.sum(1) > 0
    b, y, H = [], 0, len(on)
    while y < H:
        if on[y]:
            y0 = y
            while y < H and on[y:y + bosluk].any():
                y += 1
            b.append([y0, int(np.nonzero(on[y0:y])[0].max()) + y0 + 1])
        y += 1
    return b


def kutu(mask):
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def kumeler(ink_bant, bosluk):
    """Bant icindeki murekkebi sutun boslugu >= bosluk px olan kumelere ayirir (soldan saga kutular)."""
    on = ink_bant.any(0)
    xs = np.nonzero(on)[0]
    gr, bas = [], xs[0]
    for a, b in zip(xs[:-1], xs[1:]):
        if b - a > bosluk:
            gr.append((bas, a + 1)); bas = b
    gr.append((bas, xs[-1] + 1))
    return gr


def alfa_katman(f):
    a = np.asarray(Image.open(f).convert('RGBA'), np.float32)[..., 3] / 255.0
    k = kutu(a > 0.5)
    return a, k


def oturt(m, ink, hedef_kutu, alfa, akutu, ara=0.03, kay=6):
    """alfa katmanini hedef kutuya oturtur, olcek/kayma araliginda NCC ile ince ayar. Doner: yerlesim sozlugu."""
    x0, y0, x1, y1 = hedef_kutu
    ax0, ay0, ax1, ay1 = akutu
    s0 = ((x1 - x0) / (ax1 - ax0) + (y1 - y0) / (ay1 - ay0)) / 2
    pad = 40
    X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
    hed = m[Y0:y1 + pad, X0:x1 + pad]
    hed = hed / max(np.percentile(hed[hed > wk.ESIK], 50), 1)
    en = None
    for s in np.linspace(s0 * (1 - ara), s0 * (1 + ara), 13):
        w, h = int(round(alfa.shape[1] * s)), int(round(alfa.shape[0] * s))
        a = cv2.resize(alfa, (w, h), interpolation=cv2.INTER_AREA)
        bx0, by0 = int(round(ax0 * s)), int(round(ay0 * s))
        for dx in range(-kay, kay + 1, 2):
            for dy in range(-kay, kay + 1, 2):
                ox, oy = x0 - bx0 + dx, y0 - by0 + dy          # katmanin sol ust kosesi (sayfa)
                tuv = np.zeros_like(hed)
                sx0, sy0 = ox - X0, oy - Y0
                cx0, cy0 = max(0, sx0), max(0, sy0)
                cx1, cy1 = min(tuv.shape[1], sx0 + w), min(tuv.shape[0], sy0 + h)
                if cx1 <= cx0 or cy1 <= cy0:
                    continue
                tuv[cy0:cy1, cx0:cx1] = a[cy0 - sy0:cy1 - sy0, cx0 - sx0:cx1 - sx0]
                u, v = tuv - tuv.mean(), hed - hed.mean()
                ncc = float((u * v).sum() / np.sqrt((u * u).sum() * (v * v).sum()))
                if en is None or ncc > en['ncc']:
                    en = {'olcek': float(s), 'x': int(ox), 'y': int(oy), 'w': w, 'h': h, 'ncc': round(ncc, 4)}
    return en


def punto_bul(dosya, wght, metin, hedef_px, kucuk=False):
    """hedef govde yuksekligine (px) esit punto. kucuk=True: x-yuksekligi (kucuk harf) esitlenir."""
    lo, hi = 10.0, 1000.0
    for _ in range(40):
        p = (lo + hi) / 2
        f = ImageFont.truetype(str(dosya), int(round(p)))
        if wght:
            f.set_variation_by_axes([wght])
        h = -f.getbbox('x' if kucuk else 'H', anchor='ls')[1]
        lo, hi = (p, hi) if h < hedef_px else (lo, p)
    return int(round((lo + hi) / 2))


def lut_olc(cifler):
    """Altin edisyonlar: katman rengi -> orijinal renk, kanal basina 256 girisli tablo. Girdi: (katman RGB, orijinal RGB)
    cekirdek piksel ciftleri (alfa > 0.98). Kutu basina ortalama, >= 20 piksel olan degerler arasi dogrusal."""
    G = np.concatenate([g for g, _ in cifler]); S = np.concatenate([s for _, s in cifler])
    lut = []
    for c in range(3):
        gi = np.clip(np.round(G[:, c]).astype(int), 0, 255)
        n = np.bincount(gi, minlength=256); t = np.bincount(gi, weights=S[:, c], minlength=256)
        v = np.nonzero(n >= 20)[0]
        lut.append([round(float(x), 1) for x in np.interp(np.arange(256), v, t[v] / n[v])])
    return {'lut': lut, 'n': int(len(G))}


def katman_cifti(S, f, yer):
    """oturtulmus katmanin cekirdek pikselleri: (katman RGB, orijinal RGB)."""
    A = np.asarray(Image.open(f).convert('RGBA').resize((yer['w'], yer['h']), Image.LANCZOS), np.float32)
    x, y = yer['x'], yer['y']
    H, W = S.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + yer['w']), min(H, y + yer['h'])
    A = A[y0 - y:y1 - y, x0 - x:x1 - x]
    ce = A[..., 3] > 0.98 * 255
    return A[..., :3][ce], S[y0:y1, x0:x1][ce]


def profil_olc(S, ink, x0, x1, ust, taban, govde=0.0):
    """Altin yazi dokusu ORIJINALDEN: kelimenin harf cekirdegi (5x5 asindirilmis murekkep) satir ortanca RGB'si,
    ust..taban satirlari. Gecerli satir: cekirdek >= 15 piksel ve >= satir ortancasinin %25'i (serif / yatay cubuk
    satirlarinda birkac pikselin ortancasi gurultu: 3 Eki olcumu, ardisik satir 101 / 173 luma). Gecersiz satir en
    yakin gecerli satirlardan dogrusal; profil sigma 2 satir Gauss ile yumusatilir (qc e olcegi; orijinal kelimenin
    kendi e degeri 1.6-2.2)."""
    ce = cv2.erode(ink.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if govde:
        # yalniz dikey govde: sutundaki dikey kosusu >= govde x yukseklik olan cekirdek pikselleri (3 Eki, 78 cift:
        # AQUARIUS'ta A yatay cizgisi satir profiline tumsek ekliyordu, yeni isimde e 5.2; govde kosusu tum boyuyla
        # kalir, yatay cubuk / serif dusar)
        y0, y1 = max(0, ust - 2), min(ce.shape[0], taban + 2)
        b = ce[y0:y1, x0:x1]
        yukari = np.zeros(b.shape, np.int32); asagi = np.zeros(b.shape, np.int32)
        for i in range(b.shape[0]):
            yukari[i] = (yukari[i - 1] + 1) * b[i] if i else b[i]
        for i in range(b.shape[0] - 1, -1, -1):
            asagi[i] = (asagi[i + 1] + 1) * b[i] if i < b.shape[0] - 1 else b[i]
        L = max(5, int(govde * (taban - ust)))
        g = np.zeros_like(ce); g[y0:y1, x0:x1] = b & (yukari + asagi - 1 >= L)
        ce = g
    pr, n = [], []
    for y in range(ust, taban):
        sel = ce[y, x0:x1]
        n.append(int(sel.sum()))
        pr.append(np.median(S[y, x0:x1][sel], 0) if sel.sum() else np.zeros(3))
    pr, n = np.asarray(pr, np.float32), np.asarray(n)
    ok = n >= max(15, 0.25 * np.median(n[n > 0]))
    i = np.nonzero(ok)[0]
    g = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2); g /= g.sum()
    for c in range(3):
        pr[:, c] = np.interp(np.arange(len(pr)), i, pr[i, c])
        pr[:, c] = np.convolve(np.pad(pr[:, c], 6, mode='edge'), g, 'valid')
    return [[round(float(v), 1) for v in r] for r in pr]


def renk_olc(S, m, maske):
    """Ogenin dolu murekkep pikselleri (m >= 0.9 x ortanca) ortalama RGB'si (wp_bakir.DOLU ile ayni tanim).
    cv: cekirdek (3x3 asindirilmis murekkep) icinde m std / ortanca = golgelenme genligi (kabartma, parilti)."""
    v = m[maske]
    Lk = float(np.median(v[v > wk.ESIK]))
    dolu = maske & (m >= 0.9 * Lk)
    ce = cv2.erode(maske.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    cv = float(m[ce].std() / max(np.median(m[ce]), 1))
    return [round(float(x), 1) for x in S[dolu].mean(0)], int(dolu.sum()), round(Lk, 1), round(cv, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cift', required=True)
    ap.add_argument('--renk', required=True)
    ap.add_argument('--boy', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--orijinal', help='orijinal satis posteri (varsayilan: KAYNAK/orijinal_WP_11x14.jpg)')
    ap.add_argument('--plate-dosya', help='plate dosyasi (varsayilan: KAYNAK/plates/<plate>.png)')
    ap.add_argument('--altin', action='store_true', help='altin edisyon: katman tablosu (LUT) + yazi dokusu olc')
    ap.add_argument('--govde-profil', type=float, default=0.0,
                    help='yazi profili yalniz dikey govdeden (kosu >= oran x yukseklik; 78 cift: 0.15)')
    ap.add_argument('--mesaj-isim-tonu', action='store_true', help='tagline dokusu = isim altini (Serdar: DEEP_BLACK)')
    a = ap.parse_args()
    K = Path(a.kaynak)
    sol, sag = (x.lower() for x in a.cift.split('_'))
    S = oku(a.orijinal or K / 'orijinal_WP_11x14.jpg'); P = oku(a.plate_dosya or K / 'plates' / f'{a.plate}.png')
    H, W = S.shape[:2]
    q = W / 3307                                                       # kume bosluklari 11x14'te olculdu
    m, ink = murekkep(S, P)
    # plate halkasi disi murekkep: bantlar ve sembol yerlesimi bununla (orijinal halka plate'tekiyle birebir
    # cakismayan ciftlerde fark bantlari birlestiriyordu; LIBRA_LIBRA). Halka farki yoksa ink ile ayni.
    hm = halka_maskesi(P)
    ink_b = ink & ~hm
    b0 = bantlar(ink_b)
    toplam = ink_b.sum()
    b = [x for x in b0 if ink_b[x[0]:x[1]].sum() >= 0.01 * toplam]    # gurultu bantlari (kagit lekesi) < %1
    if len(b) > 4:
        # ana sembol birden cok banda bolunebilir (3 Eki, ARIES_LIBRA: terazi alt cubugu > 40 px bosluk): yerlesim
        # sabit, son uc bant kucuk sembol / isim / mesaj; ustteki bantlar tek buyuk sembol bandi
        b = [[b[0][0], b[-4][1]]] + b[-3:]
    if len(b) != 4:
        sys.exit(f'FAIL: 4 bant bekleniyordu (buyuk sembol, kucuk sembol, isim, mesaj), bulunan {b}')
    bb, kb, ib, mb = b
    R = {'bant_eleme': {'tum': b0, 'piksel': [int(ink_b[x[0]:x[1]].sum()) for x in b0]},
         'cift': a.cift, 'renk': a.renk, 'boy': a.boy, 'tuval': [W, H], 'plate': a.plate,
         'kaynak': {'orijinal': 'POD_PRINT/%s/%s/%s.jpg' % (a.cift, a.renk, a.boy)},
         'bantlar': {'buyuk_sembol': bb, 'kucuk_sembol': kb, 'isim': ib, 'mesaj': mb}}
    # buyuk sembol (plate halkasi disinda: orijinalin halkasi plate'tekiyle birebir cakismayabilir)
    al, ak = alfa_katman(K / f'main_{sol}_{sag}_gold.png')
    hk = kutu(ink_b[bb[0]:bb[1]]); hk = [hk[0], hk[1] + bb[0], hk[2], hk[3] + bb[0]]
    R['buyuk_sembol'] = {'katman': f'main_symbols/{sol}_{sag}_gold.png', 'kutu': hk,
                         **oturt(np.where(hm, 0, m), ink_b, hk, al, ak)}
    if R['buyuk_sembol']['ncc'] < NCC_MIN:
        sys.exit(f"FAIL: ana sembol oturtma NCC {R['buyuk_sembol']['ncc']} < {NCC_MIN}")
    # kucuk semboller
    kk = kumeler(ink_b[kb[0]:kb[1]], 200 * q)
    if len(kk) != 2:
        sys.exit(f'FAIL: kucuk sembol kume sayisi {len(kk)}')
    for taraf, burc, (x0, x1) in (('sol', sol, kk[0]), ('sag', sag, kk[1])):
        yy = np.nonzero(ink_b[kb[0]:kb[1], x0:x1].any(1))[0]
        hk = [int(x0), int(kb[0] + yy.min()), int(x1), int(kb[0] + yy.max() + 1)]
        al, ak = alfa_katman(K / f'sym_{burc}_gold.png')
        R[f'kucuk_sembol_{taraf}'] = {'katman': f'zodiac_symbols_gold/{burc}_symbol_gold.png', 'kutu': hk,
                                     **oturt(np.where(hm, 0, m), ink_b, hk, al, ak)}
        if R[f'kucuk_sembol_{taraf}']['ncc'] < NCC_MIN:
            sys.exit(f"FAIL: kucuk sembol ({taraf}) oturtma NCC {R[f'kucuk_sembol_{taraf}']['ncc']} < {NCC_MIN}")
    # isim satiri: sol isim / sonsuz / sag isim (kelime ici harf boslugu < 80 px)
    ik = kumeler(ink[ib[0]:ib[1]], 80 * q)
    if len(ik) != 3:
        sys.exit(f'FAIL: isim satiri kume sayisi {len(ik)} (sol, sonsuz, sag bekleniyordu)')
    kut = []
    for x0, x1 in ik:
        yy = np.nonzero(ink[ib[0]:ib[1], x0:x1].any(1))[0]
        kut.append([int(x0), int(ib[0] + yy.min()), int(x1), int(ib[0] + yy.max() + 1)])
    isim_sol, sonsuz, isim_sag = kut
    # inen harf (AQUARIUS'ta Q kuyrugu): harf kumelerinin alt kenar ortancasi taban olur, kutu tabana kirpilir.
    # Inen harf yoksa (SCORPIO / VIRGO, CANCER / LIBRA) kutu degismez (sabitler birebir ayni).
    inen = {}
    for t, k in (('sol', isim_sol), ('sag', isim_sag)):
        alt = []
        for x0, x1 in kumeler(ink[k[1]:k[3], k[0]:k[2]], 2):
            yy = np.nonzero(ink[k[1]:k[3], k[0] + x0:k[0] + x1].any(1))[0]
            alt.append(k[1] + int(yy.max()) + 1)
        orta = int(np.median(alt))
        if k[3] - orta > 0.08 * (orta - k[1]):
            inen[t] = {'kutu_alt': k[3], 'taban': orta}
            k[3] = orta
    # taban cizgisi: isim kutusunun alti (inen harf haric)
    taban = int(round((isim_sol[3] + isim_sag[3]) / 2))
    cap = {'sol': isim_sol[3] - isim_sol[1], 'sag': isim_sag[3] - isim_sag[1]}
    cinzel = FONT / 'Cinzel.ttf'
    p_sol = punto_bul(cinzel, 500, sol.upper(), cap['sol']); p_sag = punto_bul(cinzel, 500, sag.upper(), cap['sag'])
    satir_merkez = (isim_sol[0] + isim_sag[2]) / 2
    R['isim'] = {'font': 'Cinzel.ttf', 'wght': 500, 'taban_y': taban, 'govde_px': cap,
                 'punto': {'sol': p_sol, 'sag': p_sag, 'kullanilan': int(round((p_sol + p_sag) / 2))},
                 'kutu_sol': isim_sol, 'kutu_sag': isim_sag,
                 'bosluk_sol': sonsuz[0] - isim_sol[2], 'bosluk_sag': isim_sag[0] - sonsuz[2],
                 'satir_merkez_x': round(satir_merkez, 1), 'poster_merkez_x': W / 2,
                 'kenar_payi': int(round(0.10 * W))}
    if inen:
        R['isim']['inen_harf'] = inen
    R['sonsuz'] = {'kutu': sonsuz, 'merkez_x': (sonsuz[0] + sonsuz[2]) / 2, 'genislik': sonsuz[2] - sonsuz[0],
                   'katman': 'orijinal posterden murekkep gucu (yuksek cozunurluklu kaynak yok: HAZIR/infinity.png 187x58)'}
    # sembol-isim hizasi (SECENEK D): kucuk sembol merkezi isim merkezinin ustunde
    R['sembol_isim_dx'] = {t: round((R[f'kucuk_sembol_{t}']['kutu'][0] + R[f'kucuk_sembol_{t}']['kutu'][2]) / 2
                                    - (k[0] + k[2]) / 2, 1) for t, k in (('sol', isim_sol), ('sag', isim_sag))}
    R['sembol_isim_dy'] = {t: R['isim']['kutu_' + t][1] - R[f'kucuk_sembol_{t}']['kutu'][3] for t in ('sol', 'sag')}
    # mesaj (tagline): 'T' govdesi ile punto, taban = ilk kelimenin (Two) alt kenari
    # tagline kumesi: kelime boslugu < 400 px kumelerin en genisi (bant icindeki tek yildiz / kagit beneki disarida)
    tx0, tx1 = max(kumeler(ink[mb[0]:mb[1]], 400 * q), key=lambda k: k[1] - k[0])
    ink_m = np.zeros_like(ink); ink_m[mb[0]:mb[1], tx0:tx1] = ink[mb[0]:mb[1], tx0:tx1]
    mk = kutu(ink_m[mb[0]:mb[1]]); mk = [mk[0], mk[1] + mb[0], mk[2], mk[3] + mb[0]]
    ilk = [k for k in kumeler(ink_m[mb[0]:mb[1]], 30 * q) if k[0] >= tx0][0]
    t_x = kumeler(ink_m[mb[0]:mb[1], ilk[0]:ilk[1]], 3)[0]                 # ilk harf (T)
    yy = np.nonzero(ink_m[mb[0]:mb[1], ilk[0] + t_x[0]:ilk[0] + t_x[1]].any(1))[0]
    t_govde = int(yy.max() - yy.min() + 1)
    yy_w = np.nonzero(ink_m[mb[0]:mb[1], ilk[0]:ilk[1]].any(1))[0]
    ebg = FONT / 'EBGaramond-Italic.ttf'
    R['mesaj'] = {'font': 'EBGaramond-Italic.ttf', 'wght': 400, 'kutu': mk, 'T_govde_px': t_govde,
                  'punto': punto_bul(ebg, 400, 'T', t_govde), 'taban_y': int(mb[0] + yy_w.max() + 1),
                  'merkez_x': round((mk[0] + mk[2]) / 2, 1),
                  'genislik_siniri': round(TAG_SINIR[ORAN[a.boy]] / 2400 * W)}   # ORAN_SABITLERI tagline_genislik_siniri
    # renk: dolu murekkep ortalamasi (oge gruplari)
    renk = {}
    for ad, (y0, y1) in R['bantlar'].items():
        mm = np.zeros_like(ink); mm[y0:y1] = ink[y0:y1]
        renk[ad] = dict(zip(('rgb', 'dolu_px', 'Lk', 'cv'), renk_olc(S, m, mm)))
    tum = renk_olc(S, m, ink)
    R['renk'] = {'ogeler': renk, 'hepsi': dict(zip(('rgb', 'dolu_px', 'Lk', 'cv'), tum))}
    if a.altin:
        # altin edisyon (koyu / acik kagit): semboller katman + olculen tablo; yazi dokusu orijinal satir profili
        R['mod'] = 'altin'
        cf = {'buyuk_sembol': [katman_cifti(S, K / f'main_{sol}_{sag}_gold.png', R['buyuk_sembol'])],
              'kucuk_sembol': [katman_cifti(S, K / f'sym_{b}_gold.png', R[f'kucuk_sembol_{t}'])
                               for t, b in (('sol', sol), ('sag', sag))]}
        R['altin'] = {k: lut_olc(v) for k, v in cf.items()}
        gv = a.govde_profil
        R['altin']['isim_sol'] = profil_olc(S, ink, isim_sol[0], isim_sol[2], isim_sol[1], isim_sol[3], gv)
        R['altin']['isim_sag'] = profil_olc(S, ink, isim_sag[0], isim_sag[2], isim_sag[1], isim_sag[3], gv)
        R['altin']['mesaj'] = profil_olc(S, ink_m, mk[0], mk[2], int(mb[0] + yy.min()), R['mesaj']['taban_y'], gv)
        if gv:
            R['altin']['profil_olcum'] = f'dikey govde kosusu >= {gv} x yukseklik'
        R['isaret'] = isaret(P)
        if a.mesaj_isim_tonu:
            # Serdar 3 Eki (ADIM 1): DEEP_BLACK tagline tonu isim altini ile ayni -> tagline dokusu = iki isim
            # profilinin ortalamasi (her biri ayni satir sayisina yeniden orneklenir)
            p1, p2 = np.asarray(R['altin']['isim_sol']), np.asarray(R['altin']['isim_sag'])
            n = max(len(p1), len(p2))
            rs = lambda p: np.stack([np.interp(np.linspace(0, len(p) - 1, n), np.arange(len(p)), p[:, c]) for c in range(3)], 1)
            R['altin']['isim'] = [[round(float(v), 1) for v in r] for r in (rs(p1) + rs(p2)) / 2]
            R['altin']['mesaj_profili'] = 'isim'
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
