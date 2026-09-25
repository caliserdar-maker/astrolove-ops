"""Kisiye ozel A6 kartpostal uretimi (Serdar onayi 25 Eyl 2026: EMILY & JAMES ornegi, video-v1 2d94393).

Pod cagrisi:
    import sys; sys.path.insert(0, 'scripts/kartpostal')
    from kartpostal_uret import kartpostal_uret
    yol, qc = kartpostal_uret('ARIES_LEO', 'Emily', 'James', cikti='out/kart.jpg')
    # qc['PASS'] False ise KartpostalQCHatasi atilir (kati=True); kart basilmaz.

Girdi: cift = POD_PRINT klasor adi (orn. ARIES_LEO), isim1/isim2 = siparis isimleri (satirda isim1 & isim2, BUYUK harf).
Cikti: 1240x1748 JPG, 300 dpi (Prodigi A6 105x148 mm, ~4 mm beyaz kenar dahil, tasma payi yok; mevcut V1 kartla ayni olcu).
Sembol kaynagi: ciftin onayli Midnight Blue posteri Drive A1_77/<CIFT>/POSTER_AM.png (yoksa POSTER_IN, POSTER_EJ);
CANCER_LIBRA icin depodaki onayli poster (assets/CANCER_LIBRA_MIDNIGHT_BLUE.png, v5 video kaynagi).
Kart: assets/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg (Drive BRAND/INSERTS, B99).
Degisen yalniz ust blok: ∞ yerine ciftin birlesik sembolu (∞ kutusu ALANI kadar), Thank you 75 px yukari, altina isim satiri.
Alt baslik ve altindaki her piksel AYNEN (QC kapisi). Bagimlilik: pillow, numpy, opencv, fonttools. Etsy/Prodigi erisimi YOK."""
import json, re, subprocess, tempfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSET = Path(__file__).resolve().parent / 'assets'
KART_V1 = ASSET / 'ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg'
FONT = ASSET / 'Cinzel.ttf'
CL_POSTER = ASSET / 'CANCER_LIBRA_MIDNIGHT_BLUE.png'
A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
POSTER_ADLARI = ('POSTER_AM.png', 'POSTER_IN.png', 'POSTER_EJ.png')

# ---- onayli ornekten olculen sabitler (kaynak kart V1 + A1_77/ARIES_LEO/POSTER_AM)
ZEMIN = np.array([6., 20., 46.])                       # kart zemini (std 0)
CERCEVE = (76, 76, 1163, 1671)                         # altin cerceve
SUTUN = (169, 1066)                                    # govde metni sutunu -> isim satiri azami eni
SONSUZ = (519, 244, 720, 305)                          # ∞ kutusu (sembol alani = bu kutunun alani)
TY = (361, 423)                                        # Thank you bandi
ALT_BAS = 456                                          # alt baslik ust siniri: buradan asagisi DOKUNULMAZ
IS_CAP = 32                                            # isim cap yuksekligi (px), sigmazsa kuculur
IS_CAP_MIN = 16                                        # kuculme tabani (~1.35 mm); altina inerse FAIL
G_TY_IS, G_IS_ALT, G_SEM_TY = 32, 44, 44               # Thank you -> isim, isim tabani -> alt baslik, sembol -> Thank you
IS_WGHT = 500                                          # kisisel-v1 ONAYLI.json isimler.agirlik
TR_ORAN = -0.0697                                      # harf araligi / punto: onayli posterdeki ALEXANDER'dan olculdu
PROFIL = np.array(json.loads((ASSET / 'isim_altin_profil.json').read_text())['profil'])
SEMBOL_CERCEVE_PAYI = 40


class KartpostalQCHatasi(RuntimeError):
    pass


def _rc(*a):
    return subprocess.run(['rclone', *a], capture_output=True, text=True)


def poster_getir(cift, hedef_dir):
    """Ciftin onayli Midnight Blue posteri (yerel yol). CANCER_LIBRA depodan; digerleri Drive A1_77."""
    if cift == 'CANCER_LIBRA':
        return CL_POSTER, 'repo:assets/CANCER_LIBRA_MIDNIGHT_BLUE.png'
    for ad in POSTER_ADLARI:
        yol = Path(hedef_dir) / f'{cift}_{ad}'
        if _rc('copyto', f'{A77}/{cift}/{ad}', str(yol)).returncode == 0 and yol.exists():
            return yol, f'A1_77/{cift}/{ad}'
    raise FileNotFoundError(f'{cift}: A1_77 altinda onayli poster yok ({", ".join(POSTER_ADLARI)})')


def _bilesenler(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    return n, lab, st


def sembol_katmani(poster):
    """Posterden birlesik sembol: halka cemberi olculup maskelenir; halka ici, kucuk sembollerin ustundeki murekkep.
    Alfa = |poster - inpaint zemin| / cekirdek; renk zeminden ayristirilir (sembol yeniden cizilmez)."""
    P = np.asarray(Image.open(poster).convert('RGB')).astype(np.float64)
    assert P.shape[:2] == (3000, 2400), f'poster olcusu {P.shape[1]}x{P.shape[0]} (beklenen 2400x3000, 4x5)'
    pz = np.median(P[60:260, 1100:1300].reshape(-1, 3), 0)
    m = np.abs(P - pz).max(2) > 60
    m[:200] = False; m[2100:] = False
    md = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    n, lab, st = _bilesenler(md)
    halka = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_WIDTH])
    assert st[halka, cv2.CC_STAT_WIDTH] > 1200, 'halka bulunamadi'
    ys, xs = np.where((lab == halka) & m)
    A_ = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; b = xs ** 2 + ys ** 2
    cx, cy, c = np.linalg.lstsq(A_, b, rcond=None)[0]; R = np.sqrt(c + cx ** 2 + cy ** 2)
    halka_alt = ys.max()
    yy, xx = np.mgrid[0:P.shape[0], 0:P.shape[1]]
    d = np.hypot(xx - cx, yy - cy)
    ic = m & (d < R - 25)
    icd = cv2.dilate(ic.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    n, lab, st = _bilesenler(icd)
    aday = [i for i in range(1, n) if st[i, cv2.CC_STAT_TOP] < halka_alt - 100]
    assert aday, 'birlesik sembol bulunamadi'
    enb = max(st[i, cv2.CC_STAT_AREA] for i in aday)
    tut = [i for i in aday if st[i, cv2.CC_STAT_AREA] >= 0.05 * enb]
    sm = np.isin(lab, tut) & m
    ys, xs = np.where(sm)
    pad = 24
    x0, y0, x1, y1 = xs.min() - pad, ys.min() - pad, xs.max() + 1 + pad, ys.max() + 1 + pad
    I = P[y0:y1, x0:x1]; smk = sm[y0:y1, x0:x1]
    mk = cv2.dilate(smk.astype(np.uint8), np.ones((17, 17), np.uint8))
    zem = cv2.inpaint(np.clip(I, 0, 255).astype(np.uint8), mk * 255, 9, cv2.INPAINT_TELEA).astype(np.float64)
    dd = np.abs(I - zem).max(2)
    cek = np.percentile(dd[smk], 95)
    A = np.clip(dd / cek, 0, 1) * (cv2.dilate(smk.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    F = np.where(A[..., None] > 0.02, (I - zem * (1 - A[..., None])) / np.maximum(A[..., None], 0.02), I)
    ys, xs = np.where(A > 0.3)
    F = np.clip(F, 0, 255)[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; A = A[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    bilgi = {'halka_merkez_R': [round(cx), round(cy), round(R)], 'sembol_poster_px': [A.shape[1], A.shape[0]],
             'bilesen': len(tut), 'kutu_poster': [int(x0 + xs.min()), int(y0 + ys.min())]}
    return F, A, bilgi


def _font(boy):
    f = ImageFont.truetype(str(FONT), boy); f.set_variation_by_axes([IS_WGHT]); return f


def _cap(boy):
    return -_font(boy).getbbox('H', anchor='ls')[1]


def _ciz(metin, boy):
    f = _font(boy); tr = boy * TR_ORAN
    gen = sum(f.getlength(c) for c in metin) + abs(tr) * len(metin)
    im = Image.new('L', (int(gen) + 4 * boy, 3 * boy), 0); dr = ImageDraw.Draw(im); x = 2 * boy
    for c in metin:
        dr.text((x, boy), c, font=f, fill=255, anchor='ls'); x += f.getlength(c) + (0 if c == ' ' else tr)   # bosluk daraltilmaz
    return np.asarray(im).astype(np.float64) / 255, boy


def _fontta_yok(metin):
    from fontTools.ttLib import TTFont
    cmap = TTFont(str(FONT)).getBestCmap()
    return sorted({c for c in metin if c != ' ' and ord(c) not in cmap})


def isim_metni(isim1, isim2):
    t = lambda s: re.sub(r'\s+', ' ', str(s)).strip().upper()
    return f'{t(isim1)} & {t(isim2)}'


def isim_katmani(metin):
    boy = next(b for b in range(8, 400) if _cap(b) >= IS_CAP); tam = boy
    maks = SUTUN[1] - SUTUN[0] + 1
    while True:
        a, taban = _ciz(metin, boy)
        xs = np.where(a.max(0) > 0.5)[0]; w = xs.max() - xs.min() + 1
        if w <= maks or boy <= 6: break
        boy -= 1
    cap = _cap(boy)
    xs = np.where(a.max(0) > 0.01)[0]; a = a[:, xs.min():xs.max() + 1]
    rgb = np.zeros(a.shape + (3,))
    for r in range(a.shape[0]):                          # altin: onayli satir profili cap kutusuna gerilir
        t = (r - (taban - cap)) / max(cap - 1, 1)
        rgb[r] = PROFIL[int(round(np.clip(t, 0, 1) * (len(PROFIL) - 1)))]
    return a, rgb, taban, cap, boy, round(boy / tam, 3), int(w), maks


def _bantlar(a):
    m = (np.abs(a - ZEMIN).max(2) > 40)[CERCEVE[1] + 4:CERCEVE[3] - 3, CERCEVE[0] + 4:CERCEVE[2] - 3]
    r = np.where(m.any(1))[0] + CERCEVE[1] + 4; b = []; s = p = r[0]
    for x in r[1:]:
        if x > p + 1: b.append((int(s), int(p))); s = x
        p = x
    return b + [(int(s), int(p))]


def kart_ciz(sembol, metin):
    """sembol = (F, A) katmani, metin = isim satiri -> (uint8 kart, yerlesim bilgisi)."""
    K = np.asarray(Image.open(KART_V1).convert('RGB')).astype(np.float64)
    C = K.copy(); H, W = C.shape[:2]
    is_ust = ALT_BAS - G_IS_ALT - IS_CAP
    D = is_ust - G_TY_IS - TY[1]
    xs0, xs1 = CERCEVE[0] + 4, CERCEVE[2] - 3
    blok = C[TY[0] - 2:TY[1] + 2, xs0:xs1].copy()
    C[SONSUZ[1] - 4:TY[1] + 2, xs0:xs1] = ZEMIN
    C[TY[0] - 2 + D:TY[1] + 2 + D, xs0:xs1] = blok
    F, A = sembol
    alan = (SONSUZ[2] - SONSUZ[0]) * (SONSUZ[3] - SONSUZ[1])
    sh, sw = A.shape; s = (alan / (sw * sh)) ** 0.5
    nw, nh = round(sw * s), round(sh * s)
    Fi = np.asarray(Image.fromarray(F.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)
    Ai = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)[..., None] / 255
    sx = int(round((SONSUZ[0] + SONSUZ[2]) / 2 - nw / 2)); sy = TY[0] + D - G_SEM_TY - nh
    assert sy >= 0 and sx >= 0, 'sembol kart disina tasiyor'
    C[sy:sy + nh, sx:sx + nw] = C[sy:sy + nh, sx:sx + nw] * (1 - Ai) + Fi * Ai
    a, rgb, taban, cap, boy, olcek, w, maks = isim_katmani(metin)
    ix = int(round(W / 2 - a.shape[1] / 2)); iy = is_ust + (IS_CAP - cap) // 2 + cap - taban   # kucuk puntoda cap bandi ortalanir
    Aa = a[..., None]
    C[iy:iy + a.shape[0], ix:ix + a.shape[1]] = C[iy:iy + a.shape[0], ix:ix + a.shape[1]] * (1 - Aa) + rgb * Aa
    C8 = np.clip(np.round(C), 0, 255).astype(np.uint8)
    y = {'metin': metin, 'punto': boy, 'isim_cap_px': int(cap), 'olcek': olcek, 'isim_en_px': w, 'isim_azami_en_px': maks,
         'isim_x': [ix, ix + a.shape[1]], 'ust_blok_kayma_px': D, 'sembol_kutu': [sx, sy, sx + nw, sy + nh],
         'sembol_alan_px2': nw * nh, 'sonsuz_alan_px2': alan}
    return C8, K, y


def qc(C8, K, y, jpg=None):
    bn = _bantlar(C8.astype(np.float64))
    yb = [x for x in bn if x[0] < ALT_BAS] + [x for x in bn if x[0] >= ALT_BAS][:1]
    bosluk = min(yb[i + 1][0] - yb[i][1] - 1 for i in range(len(yb) - 1))
    ham = float(np.abs(C8[ALT_BAS - 2:].astype(np.float64) - K[ALT_BAS - 2:]).max())
    k = {'yeni_bant_sayisi=3': len(yb) == 4,                 # sembol, Thank you, isim (+ alt baslik)
         'isim_tek_satir_sutun_ici': y['isim_x'][0] >= SUTUN[0] and y['isim_x'][1] <= SUTUN[1] + 1 and y['isim_en_px'] <= y['isim_azami_en_px'],
         f'isim_cap>={IS_CAP_MIN}': y['isim_cap_px'] >= IS_CAP_MIN,
         'sembol_alan_orani_%5': abs(y['sembol_alan_px2'] / y['sonsuz_alan_px2'] - 1) <= 0.05,
         f'sembol_cerceve_payi>={SEMBOL_CERCEVE_PAYI}': y['sembol_kutu'][1] - CERCEVE[1] >= SEMBOL_CERCEVE_PAYI,
         'yeni_bantlar_arasi_bosluk>=20': bosluk >= 20,
         'alt_bolge_ham_fark=0': ham == 0}
    out = {'bantlar_ust': yb, 'min_bant_boslugu': int(bosluk), 'alt_fark_ham_max': ham}
    if jpg is not None:
        J = Image.open(jpg); Ja = np.asarray(J.convert('RGB')).astype(np.float64)
        k['olcu_1240x1748_300dpi'] = J.size == (1240, 1748) and round(J.info.get('dpi', (0,))[0]) == 300
        out['alt_fark_jpg_ort'] = round(float(np.abs(Ja[ALT_BAS - 2:] - K[ALT_BAS - 2:]).mean()), 3)
        k['alt_bolge_jpg_ort_fark<1'] = out['alt_fark_jpg_ort'] < 1.0
    out['kapilar'] = k; out['PASS'] = all(k.values())
    return out


def kartpostal_uret(cift, isim1, isim2, cikti=None, poster=None, kati=True, _sembol_onbellek=None):
    """-> (jpg yolu, qc dict). kati=True iken QC FAIL -> KartpostalQCHatasi (kart yine diske yazilir, incelemek icin)."""
    metin = isim_metni(isim1, isim2)
    eksik = _fontta_yok(metin)
    tmp = Path(tempfile.mkdtemp(prefix='kartpostal_'))
    kaynak = 'verildi'
    if poster is None:
        poster, kaynak = poster_getir(cift, tmp)
    if _sembol_onbellek is not None and cift in _sembol_onbellek:
        F, A, sb = _sembol_onbellek[cift]
    else:
        F, A, sb = sembol_katmani(poster)
        if _sembol_onbellek is not None: _sembol_onbellek[cift] = (F, A, sb)
    C8, K, y = kart_ciz((F, A), metin)
    cikti = Path(cikti or tmp / f'KARTPOSTAL_{cift}.jpg'); cikti.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(C8).save(cikti, quality=95, subsampling=0, dpi=(300, 300))
    q = qc(C8, K, y, cikti)
    q['kapilar']['glifler_fontta'] = not eksik
    q['PASS'] = all(q['kapilar'].values())
    q.update({'cift': cift, 'poster': kaynak, 'sembol': sb, 'yerlesim': y, 'fontta_olmayan': eksik})
    if kati and not q['PASS']:
        raise KartpostalQCHatasi(json.dumps({k: v for k, v in q['kapilar'].items() if not v} | {'cift': cift, 'metin': metin}))
    return cikti, q


if __name__ == '__main__':
    import sys
    c, i1, i2, o = sys.argv[1:5]
    p = sys.argv[5] if len(sys.argv) > 5 else None
    yol, q = kartpostal_uret(c, i1, i2, o, poster=p, kati=False)
    print(json.dumps(q, ensure_ascii=False))
