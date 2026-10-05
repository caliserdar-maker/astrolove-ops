#!/usr/bin/env python3
"""DOKU_AI ornek poster (Serdar 4 Eki, ADIM 2): Canva dokulu oge seti (KESIN SET 77bf681, cila sonrasi) + supurulmus
cember (cember_supur deneme 2) ile 24x36 MIDNIGHT BLUE poster. Ana sembol simdilik ORIJINAL altin asset.

Katmanlar (alt -> ust, normal alfa bindirme):
  zemin       : radyal gradient (zemin_gradient egrisi, BLUE_16x20 olcumu; merkez = 24x36 halka merkezi, mesafe
                halka yaricap orani ile olceklenir) + BLUE_24x36 plate yildizlari (zg.yildizlar), yazi kutusu + pay
                icindeki yildizlar atilir; TPDF dither
  cember      : supurulmus doku RGBA (alfa = HALKA_24x36, onayli uclar)
  ana sembol  : main_<a>_<b>_gold.png, olcek ve konum 16x20 orijinal posterden (NCC eslesme) x halka orani
  kucuk sembol: KUCUK sayfalari (24x36 olcegi), yatay merkez = isim merkezi, dikey merkez SCORPIO_VIRGO sabitlerinden
  isimler     : ISIM_1-3 glif bankasi (Cinzel 408), alfa = vektor metin, doku = glif hucresi (maske disina dolgu)
  sonsuz      : LOGO_1 (636 px), isimler arasinda (motor SECENEK D kurali)
  tagline     : TAGLINE_1-4 glif bankasi (EB Garamond Italic 372); bankada olmayan karakter YEDEK tablosundan doku alir
Sekil her yerde bizim vektor maskemiz; Canva'dan yalniz doku.

Kullanim: doku_poster.py --set S17 --sayfa-json DIR --cember rgba.npy --cember-kutu x0,y0,x1,y1 --ana main.png
          --ana16 ana16.json --plate BLUE_24x36.png --cift CANCER_LIBRA --isim1 EMILY --isim2 JAMES --mesaj "..." --cikti DIR
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import zemin_gradient as zg                                          # noqa: E402
import tek_doku as tdk                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
SABIT = KOK / 'sabitler' / 'SCORPIO_VIRGO_MB_24x36.json'
GRAD = KOK / 'varlik' / 'plates' / 'BLUE_16x20_gradient.json'
HALKA16 = KOK / 'varlik' / 'halka' / 'HALKA_16x20.png'
HALKA24 = KOK / 'varlik' / 'halka' / 'HALKA_24x36.png'
ISIM_S = ['ISIM_1', 'ISIM_2', 'ISIM_3']
TAG_S = ['TAGLINE_1', 'TAGLINE_2', 'TAGLINE_3', 'TAGLINE_4']
KUCUK_S = ['KUCUK_1A_P', 'KUCUK_1B_P', 'KUCUK_2']
YEDEK = {'·': '.'}                     # bankada yok: sekil vektor, doku yedek glif hucresinden (murekkep merkezine)
KUCUK_Y = (7071.5 + 7084.0) / 2        # SCORPIO_VIRGO 24x36 kucuk sembol kutu merkezleri ortalamasi


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def font(d, p, w=None):
    f = ImageFont.truetype(str(KOK / 'font' / d), int(round(p)))
    if w:
        f.set_variation_by_axes([w])
    return f


def doldur(t, m):
    """doku maske disina normalize evrisimle uzatilir (alt piksel kayma / yedek glifte kenar bos kalmasin)."""
    t = t.astype(np.float32); m = m.astype(np.float32)
    out = t * m[..., None]; w = m.copy()
    for s in (1.5, 3, 6, 12, 24):
        bt = cv2.GaussianBlur(t * m[..., None], (0, 0), s); bw = cv2.GaussianBlur(m, (0, 0), s)
        ek = (w < 0.5) & (bw > 1e-3)
        out[ek] = bt[ek] / bw[ek][:, None]; w[ek] = 1
    return out


def banka(S, J, sayfalar):
    B = {}
    for ad in sayfalar:
        z = np.load(Path(S) / f'{ad}.npz'); t, O = z['t1'], z['O'].astype(np.float32) / 255
        j = json.loads((Path(J) / f'DOKU_AI_{ad}.json').read_text())
        for g in j['glifler']:
            x0, y0, x1, y1 = g['hucre']
            o = O[y0:y1, x0:x1]
            B[g['karakter']] = {'rgb': doldur(t[y0:y1, x0:x1], o > 0.5), 'alfa': o,
                                'koken': (g['koken_ls'][0] - x0, g['koken_ls'][1] - y0), 'sayfa': ad}
        B['_font'], B['_punto'], B['_wght'] = j['font'], j['punto'], j['wght']
    return B


def murekkep_merkez(F, c):
    b = F.getbbox(c, anchor='ls'); pad = 4
    im = Image.new('L', (b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), c, font=F, fill=255, anchor='ls')
    ys, xs = np.nonzero(np.asarray(im) > 127)
    return (xs.min() + xs.max()) / 2 - (pad - b[0]), (ys.min() + ys.max()) / 2 - (pad - b[1])


def kelime(metin, B, punto):
    """-> rgb (h, w, 3), alfa (h, w), taban y, murekkep kutusu; alfa = vektor metin (punto), doku = bankadan."""
    F = font(B['_font'], punto, B['_wght'])
    s = punto / B['_punto']
    x0, y0, x1, y1 = F.getbbox(metin, anchor='ls')
    pad = 24
    Wk, Hk = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    ox, oy = pad - x0, pad - y0
    im = Image.new('L', (Wk, Hk), 0)
    ImageDraw.Draw(im).text((ox, oy), metin, font=F, fill=255, anchor='ls')
    alfa = np.asarray(im, np.float32) / 255
    rgb = np.zeros((Hk, Wk, 3), np.float32); agr = np.zeros((Hk, Wk), np.float32)
    yedek = []
    for i, c in enumerate(metin):
        if c == ' ':
            continue
        lx = ox + F.getlength(metin[:i + 1]) - F.getlength(c)
        ex = ey = 0.0
        if c not in B:
            g = YEDEK[c]
            (cx, cy), (gx, gy) = murekkep_merkez(F, c), murekkep_merkez(F, g)
            ex, ey = cx - gx, cy - gy
            yedek.append({'karakter': c, 'doku': g, 'kayma_px': [round(ex, 1), round(ey, 1)]})
            b = B[g]
        else:
            b = B[c]
        t = b['rgb'] if s == 1 else cv2.resize(b['rgb'], None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        m = cv2.dilate(b['alfa'], np.ones((15, 15), np.uint8))
        m = m if s == 1 else cv2.resize(m, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if c not in B:                                               # yedek: kendi seklinin cevresi agirlik
            gi = Image.new('L', (Wk, Hk), 0)
            ImageDraw.Draw(gi).text((lx, oy), c, font=F, fill=255, anchor='ls')
            mw = cv2.dilate(np.asarray(gi, np.float32) / 255, np.ones((15, 15), np.uint8))
        kx, ky = b['koken'][0] * s, b['koken'][1] * s
        M = np.float32([[1, 0, lx - kx + ex], [0, 1, oy - ky + ey]])
        tw = cv2.warpAffine(t, M, (Wk, Hk), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if c in B:
            mw = cv2.warpAffine(m, M, (Wk, Hk), flags=cv2.INTER_LINEAR)
        rgb += tw * mw[..., None]; agr += mw
    rgb = rgb / np.maximum(agr, 1e-3)[..., None]
    ys, xs = np.nonzero(alfa > 0.5)
    if ((alfa > 0.02) & (agr < 1e-3)).any():
        sys.exit(f'FAIL: {metin} dokusuz murekkep pikseli var')
    return rgb, alfa, oy, [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], yedek


def oge(S, J, sayfalar, ad):
    for sf in sayfalar:
        j = json.loads((Path(J) / f'DOKU_AI_{sf}.json').read_text())
        for o in j.get('ogeler', []):
            if o['oge'] == ad:
                z = np.load(Path(S) / f'{sf}.npz')
                x0, y0, x1, y1 = o['kutu']
                O = z['O'][y0:y1, x0:x1].astype(np.float32) / 255
                return doldur(z['t1'][y0:y1, x0:x1], O > 0.5), O, sf
    sys.exit(f'FAIL: {ad} oge bulunamadi')


def halka_geo(f):
    h = np.asarray(Image.open(f).convert('L'), np.float32)
    ys, xs = np.nonzero(h > 128)
    M = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; b = (xs ** 2 + ys ** 2).astype(np.float64)
    cx, cy, c = np.linalg.lstsq(M, b, rcond=None)[0]
    return float(cx), float(cy), float(np.sqrt(c + cx ** 2 + cy ** 2))

def cekirdek(al):
    """oge cekirdegi: alfa > 0.95, 3 px asindirilmis (renk olcumu ve esitleme ayni maske)."""
    return cv2.erode((al > 0.95).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)


def omuz(L, diz=90.0):
    """L' <= 100: diz ustu yumusak omuz (tanh), kirpilma yok."""
    return np.where(L > diz, diz + (100 - diz) * np.tanh((L - diz) / (100 - diz)), L)


def renk_esitle(rgb, al, hedef, duz):
    """OGE RENK ESITLEME (Serdar 4 Eki): ogenin TAMAMINA tek kural, bolgesel yama yok. Cekirdek medyan Lab olculur;
    L' = L x (hedef_L / L_med) x kL, a' = a + (hedef_a - a_med) + da, b' = b + (hedef_b - b_med) + db (kL, da, db: kapali
    dongu duzeltmesi, ilk turda 1 / 0 / 0). L' tepede yumusak omuzla 100'u gecmez."""
    Lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    med = np.median(Lab[cekirdek(al)], 0)
    k = hedef[0] / med[0] * duz.get('kL', 1.0)
    da = hedef[1] - med[1] + duz.get('da', 0.0); db = hedef[2] - med[2] + duz.get('db', 0.0)
    Lab[..., 0] = omuz(Lab[..., 0] * k); Lab[..., 1] += da; Lab[..., 2] += db
    out = np.clip(cv2.cvtColor(Lab, cv2.COLOR_LAB2RGB), 0, 1) * 255
    return out, {'med_once': [round(float(v), 2) for v in med], 'kL': round(float(k), 4), 'da': round(float(da), 2),
                 'db': round(float(db), 2)}

DUZ_SIGMA = 220.0        # 7200 px genislikte (2000 px'te 60 px, koordinator denemesi)
DUZ_SINIR = (0.80, 1.25)


def l_duzle(rgb, al, W):
    """OGE ICI BOLGESEL PARLAKLIK (Serdar 4 Eki): her piksele ayni surekli kural, yama yok. low = blur(L w) / blur(w)
    (w = oge alfasi, sigma = DUZ_SIGMA x W / 7200); kazanc = cekirdek medyan L / low, DUZ_SINIR ile sinirli;
    L' = L x (1 + w (kazanc - 1)). Ana sembol disindaki tum ogelere, yuzdelik eslemeden ONCE."""
    Lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    w = np.clip(al, 0, 1).astype(np.float32)
    sg = DUZ_SIGMA * W / 7200
    low = cv2.GaussianBlur(Lab[..., 0] * w, (0, 0), sg) / np.maximum(cv2.GaussianBlur(w, (0, 0), sg), 1e-4)
    med = float(np.median(Lab[..., 0][cekirdek(al)]))
    k = np.clip(med / np.maximum(low, 1e-3), *DUZ_SINIR)
    Lab[..., 0] = np.clip(Lab[..., 0] * (1 + w * (k - 1)), 0, 100)
    ce = cekirdek(al)
    return np.clip(cv2.cvtColor(Lab, cv2.COLOR_LAB2RGB), 0, 1) * 255, {
        'duz_kazanc_p1_p50_p99': [round(float(v), 3) for v in np.percentile(k[ce], (1, 50, 99))]}


def duzle(rgb, al, W):
    """GENIS OLCEKLI DUZLEME (Serdar onayli koordinator uygulamasi, 5 Eki; 2000 px'te sigma 60 = 7200 px'te ~216):
    yuzdelik eslemeden SONRA, bitmis oge uzerinde. Her piksele ayni surekli kural, yama yok. w = doygunluk / parlaklik
    rampasi x oge alfasi; low = blur(L w) / blur(w); g = medyan(L | w > 0.9) / low, 0.8-1.25; L' = L (1 - w) + L g w."""
    sigma = 60.0 * W / 2000
    x = np.clip(rgb, 0, 255).astype(np.float32) / 255
    lab = cv2.cvtColor(x, cv2.COLOR_RGB2LAB)
    L = lab[..., 0]
    hsv = cv2.cvtColor(x, cv2.COLOR_RGB2HSV)
    w = np.clip((hsv[..., 1] - 0.25) / 0.2, 0, 1) * np.clip((hsv[..., 2] - 0.35) / 0.2, 0, 1) * np.clip(al, 0, 1)
    low = cv2.GaussianBlur(L * w, (0, 0), sigma) / (cv2.GaussianBlur(w, (0, 0), sigma) + 1e-6)
    med = float(np.median(L[w > 0.9]))
    g = np.clip(med / np.maximum(low, 1), 0.8, 1.25)
    lab[..., 0] = L * (1 - w) + np.clip(L * g, 0, 100) * w
    ce = w > 0.9
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1) * 255, {
        'duzle_sigma': round(sigma, 1), 'duzle_g_p1_p50_p99': [round(float(v), 3) for v in np.percentile(g[ce], (1, 50, 99))]}


METIN = ('isim1', 'isim2', 'tagline')
PARCA_Q = np.linspace(1, 99, 25)


def parca_esitle(rgb, al, hedef):
    """HARF BAZLI ESITLEME (Serdar onayli koordinator uygulamasi, 5 Eki): metin ogesi Canva harf setinden harf harf
    gelir, harflerin parlaklik ve tonu farkli. Parca = cekirdegin (oge maskesi, renk_kapi ile ayni) 5x5 genisletilmis baglantili bilesenleri
    (harf, i noktasi, kuyruk); her oge pikseli en yakin parcaya baglanir. Her parcada L yuzdelikleri (1-99, 25) hedef
    yuzdeliklere eslenir (a*, b* de ayni); w (alfa) ile harmanlanir. Her piksele ayni kural. Hedef (5 Eki,
    8e9c727 RED): ogenin KENDI cekirdek dagilimi (global eslemeden sonra). a*, b* de L gibi yuzdelik esleme (Serdar onayi,
    5 Eki): medyan kaydirma parlak yesilimsi harflerin (a* -10..-12) ic yayilimini +20 tasiyip bakir yapiyordu."""
    from scipy import ndimage as ndi
    w = np.clip(al, 0, 1).astype(np.float32)
    lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    core = cekirdek(al)                       # oge maskesi cekirdegi (renk_kapi ile ayni maske; w > 0.9 kapiyla uyusmuyordu)
    n, pl = cv2.connectedComponents(cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)))
    pl = pl * core
    _, idx = ndi.distance_transform_edt(pl == 0, return_indices=True)
    near = pl[idx[0], idx[1]]
    near[w <= 0.05] = 0
    out = lab.copy()
    say = 0
    for i in range(1, n):
        c = pl == i
        if c.sum() < 30:
            continue
        reg = near == i
        ww = w[reg]
        for k, X in enumerate((L, A, B)):
            src = np.maximum.accumulate(np.percentile(X[c], PARCA_Q) + np.arange(25) * 1e-4)
            out[..., k][reg] = np.interp(X[reg], src, hedef[k]) * ww + X[reg] * (1 - ww)
        say += 1
    return np.clip(cv2.cvtColor(out, cv2.COLOR_LAB2RGB), 0, 1) * 255, {'yontem': 'parca (harf) bazli yuzdelik esleme',
                                                                       'parca': say}


YUZDE = np.linspace(0, 100, 201)


def l_yuzdelik(rgb, al):
    Lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    return np.percentile(Lab[..., 0][cekirdek(al)], YUZDE)


def l_esitle(rgb, al, ref, hedef, duz):
    """TEK DOKU BUTUNLUGU (Serdar 4 Eki): ogenin L dagilimi ana sembol cekirdeginin L dagilimina yuzdelik esleme ile
    cekilir. Tek surekli, monoton, yumusak egri (201 yuzdelik cifti; fark egrisi 2 yuzdelik adim Gauss yumusatma;
    aralik disinda uc farki sabit kayma), ogenin TUM piksellerine ayni egri; bolgesel yama yok. Kapali dongu (Lq): ikinci
    turda hedef, poster uzerinde olculen yuzdelik farki kadar duzeltilir (cember alfasi cekirdekte ~0.95, zeminle karisir). a, b medyani ortak
    hedefe (+ kapali dongu da / db)."""
    Lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    ce = cekirdek(al)
    q = np.maximum.accumulate(np.percentile(Lab[..., 0][ce], YUZDE)) + np.arange(len(YUZDE)) * 1e-6
    ref = ref + np.asarray(duz.get('Lq', 0.0))                  # kapali dongu: posterde olculen yuzdelik farki (bindirme alfasi < 1)
    d = cv2.GaussianBlur((ref - q)[None].astype(np.float32), (0, 0), 2)[0]
    y = np.maximum.accumulate(q + d)
    L = Lab[..., 0]
    Ln = np.interp(L, q, y)
    Ln = np.where(L < q[0], L + d[0], np.where(L > q[-1], L + d[-1], Ln))
    med = np.median(Lab[ce], 0)
    da = hedef[1] - med[1] + duz.get('da', 0.0); db = hedef[2] - med[2] + duz.get('db', 0.0)
    Lab[..., 0] = np.clip(Ln, 0, 100); Lab[..., 1] += da; Lab[..., 2] += db
    out = np.clip(cv2.cvtColor(Lab, cv2.COLOR_LAB2RGB), 0, 1) * 255
    return out, {'yontem': 'L yuzdelik esleme (ana sembol)', 'med_once': [round(float(v), 2) for v in med],
                 'L_p5_p50_p99_once': [round(float(np.interp(p, YUZDE, q)), 2) for p in (5, 50, 99)],
                 'da': round(float(da), 2), 'db': round(float(db), 2)}


def main():
    ap = argparse.ArgumentParser()
    for k in ('set', 'sayfa-json', 'cember', 'cember-kutu', 'ana', 'ana16', 'plate', 'cift', 'isim1', 'isim2', 'mesaj',
              'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--ana-sayfa', help='ASAMA 2: dokulu ana sembol sayfasi adi (SET dizininde <ad>.npz cila sonrasi, '
                                       'sayfa-json dizininde DOKU_AI_<ad>.json; oge = cift); verilmezse orijinal asset')
    ap.add_argument('--renk-hedef', default='71.5,8.5,49.5',
                    help='oge renk esitleme ortak hedefi Lab (Serdar 4 Eki); "yok" = esitleme kapali')
    ap.add_argument('--l-esleme', default='ana', help='TEK DOKU (Serdar 4 Eki): ogelerin L dagilimi ana sembol cekirdek '
                                                      'L dagilimina yuzdelik esleme; "yok" = yalniz medyan esitleme')
    ap.add_argument('--l-duzle', default='var', help='oge ici bolgesel parlaklik duzleme (Serdar 4 Eki); "yok" = kapali')
    ap.add_argument('--renk-kazanc', help='kapali dongu duzeltmesi JSON {oge: {kL, da, db}} (renk_kapi.py ciktisi)')
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    Z = json.loads(SABIT.read_text())
    W, H = Z['tuval']
    rap = {'cift': a.cift, 'isim': [a.isim1, a.isim2], 'mesaj': a.mesaj, 'boy': '24x36', 'renk': 'MIDNIGHT_BLUE'}
    sol, sag = a.cift.split('_')
    h16, h24 = halka_geo(HALKA16), halka_geo(HALKA24)
    k = h24[2] / h16[2]
    rap['halka_orani'] = round(k, 5)

    # 1 zemin: gradient (merkez 24x36 halka merkezi, mesafe halka oraniyla) + plate yildizlari
    GJ = json.loads(GRAD.read_text())
    g = dict(GJ['gradient']); g['merkez'] = [h24[0], h24[1]]; g['kose'] = GJ['gradient']['kose'] * k
    P = zg.gradient(H, W, g)
    plate = np.asarray(Image.open(a.plate).convert('RGB'), np.float32)
    YL, y_kat = zg.yildizlar(plate)
    del plate
    log('zemin gradient + yildiz', len(YL))

    Cp = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32); kutu = {}

    hedef = None if a.renk_hedef == 'yok' else [float(v) for v in a.renk_hedef.split(',')]
    kazanc = json.loads(Path(a.renk_kazanc).read_text()) if a.renk_kazanc else {}
    maske = {}

    bekleyen = []
    l_esle = a.l_esleme != 'yok'

    def bindir(ad, rgb, al, x, y):
        """oge sira ile toplanir; renk islemi ana sembol referansi bilindikten sonra (bas)."""
        bekleyen.append((ad, rgb, al, x, y))

    def bas():
        if hedef is not None:
            ref = None
            if l_esle:
                i = [b[0] for b in bekleyen].index('ana_sembol')
                ad, rgb, al, x, y = bekleyen[i]
                rgb, rap.setdefault('renk_esitleme', {})[ad] = renk_esitle(rgb, al, hedef, kazanc.get(ad, {}))
                bekleyen[i] = (ad, rgb, al, x, y)
                ref = l_yuzdelik(rgb, al)
            for i, (ad, rgb, al, x, y) in enumerate(bekleyen):
                if l_esle and ad == 'ana_sembol':
                    continue
                if ref is not None:
                    # oge bazli yuzdelik esleme + a, b kaydirma (ana sembole; genis olcekli duzleme 5 Eki kaldirildi)
                    rgb, rap.setdefault('renk_esitleme', {})[ad] = l_esitle(rgb, al, ref, hedef, kazanc.get(ad, {}))
                    if ad in METIN:
                        # Serdar 5 Eki (8e9c727 RED, bakir harfler): SONRA harfler ogenin KENDI ortak dagilimina
                        # esitlenir (L yuzdelikleri + medyan a, b, tum parcalar birlikte, global eslemeden sonra)
                        Lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
                        ce = cekirdek(al)
                        oz = [np.percentile(Lab[..., k][ce], PARCA_Q) for k in range(3)]
                        rgb, rap['renk_esitleme'][ad]['parca'] = parca_esitle(rgb, al, oz)
                else:
                    rgb, rap.setdefault('renk_esitleme', {})[ad] = renk_esitle(rgb, al, hedef, kazanc.get(ad, {}))
                bekleyen[i] = (ad, rgb, al, x, y)
        for ad, rgb, al, x, y in bekleyen:
            x, y = int(round(x)), int(round(y))
            h, w = al.shape
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
            aa = al[y0 - y:y1 - y, x0 - x:x1 - x]; cc = rgb[y0 - y:y1 - y, x0 - x:x1 - x]
            Cp[y0:y1, x0:x1] = Cp[y0:y1, x0:x1] * (1 - aa[..., None]) + cc * aa[..., None]
            A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - aa) + aa
            ys, xs = np.nonzero(aa > 0.02)
            kutu[ad] = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max()) + 1, int(y0 + ys.max()) + 1]
            maske[ad] = (x0, y0, np.packbits(cekirdek(aa)), aa.shape)
        bekleyen.clear()

    # 2 cember (supurulmus)
    R = np.load(a.cember).astype(np.float32)
    cx0, cy0, _, _ = [int(v) for v in a.cember_kutu.split(',')]
    bindir('cember', R[..., :3], R[..., 3] / 255, cx0, cy0)
    del R
    # 3 ana sembol (orijinal)
    J16 = json.loads(Path(a.ana16).read_text())['p'][a.cift]['tm']
    ks = 0.500657280135945 / json.loads(Path(a.ana16).read_text())['p']['SCORPIO_VIRGO']['tm']['olcek16']
    s = J16['olcek16'] * ks
    im = Image.open(a.ana).convert('RGBA')
    kk = im.getchannel('A').getbbox()                               # ana sayfa maskesi alfa > 0 kutusundan kirpilir
    im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    an = np.asarray(im, np.float32); del im
    mx = h24[0] + J16['merkez_halkaya_gore16'][0] * k; my = h24[1] + J16['merkez_halkaya_gore16'][1] * k
    if a.ana_sayfa:
        # dokulu: sekil = sayfa maskesi (asset alfasi, ayni olcek), doku = cila sonrasi Canva; asset kirpma kutusunun
        # merkezi ayni yere
        ar, aa, _ = oge(a.set, a.sayfa_json, [a.ana_sayfa], a.cift)
        kx = (kk[0] + kk[2]) / 2 * s - an.shape[1] / 2; ky = (kk[1] + kk[3]) / 2 * s - an.shape[0] / 2
        bindir('ana_sembol', ar, aa, mx + kx - aa.shape[1] / 2, my + ky - aa.shape[0] / 2)
        rap['ana_sembol_doku'] = a.ana_sayfa
    else:
        bindir('ana_sembol', an[..., :3], an[..., 3] / 255, mx - an.shape[1] / 2, my - an.shape[0] / 2)
    rap['ana_sembol'] = {'dosya': Path(a.ana).name, 'olcek': round(s, 5), 'merkez': [round(mx, 1), round(my, 1)],
                         'kaynak': f'16x20 orijinal NCC {J16["ncc"]}, olcek16 {J16["olcek16"]} x {ks:.4f}'}
    del an
    log('cember + ana sembol', rap['ana_sembol'])

    # 4 isim satiri (motor SECENEK D): isim1 + bosluk + sonsuz + bosluk + isim2, ortali
    I = Z['isim']
    BI = banka(a.set, a.sayfa_json, ISIM_S)
    g_bos = (I['bosluk_sol'] + I['bosluk_sag']) / 2
    lr, la, lsf = oge(a.set, a.sayfa_json, ['LOGO_1'], 'LOGO')
    p = I['punto']['kullanilan']; olc = 1.0
    for _ in range(20):
        r1, a1, t1, k1, _ = kelime(a.isim1.upper(), BI, p * olc)
        r2, a2, t2, k2, _ = kelime(a.isim2.upper(), BI, p * olc)
        w1, w2 = k1[2] - k1[0], k2[2] - k2[0]
        top = w1 + 2 * g_bos * olc + la.shape[1] * olc + w2
        if top <= W - 2 * I['kenar_payi']:
            break
        olc *= (W - 2 * I['kenar_payi']) / top * 0.999
    sx = W / 2 - top / 2; taban = I['taban_y']
    bindir('isim1', r1, a1, sx - k1[0], taban - t1)
    ix = sx + w1 + g_bos * olc
    if olc != 1:
        lr = cv2.resize(lr, None, fx=olc, fy=olc, interpolation=cv2.INTER_AREA)
        la = cv2.resize(la, None, fx=olc, fy=olc, interpolation=cv2.INTER_AREA)
    sk = Z['sonsuz']['kutu']
    bindir('sonsuz', lr, la, ix, (sk[1] + sk[3]) / 2 - la.shape[0] / 2)
    x2 = ix + la.shape[1] + g_bos * olc
    bindir('isim2', r2, a2, x2 - k2[0], taban - t2)
    merk = {'sol': sx + w1 / 2, 'sag': x2 + w2 / 2}
    rap['isim_satiri'] = {'olcek': round(olc, 4), 'punto': round(p * olc, 1), 'genislik': round(top, 1),
                          'isim_merkez': {kk: round(v, 1) for kk, v in merk.items()}, 'sonsuz': lsf}
    log('isimler + sonsuz', rap['isim_satiri'])

    # 5 kucuk semboller
    for t, burc in (('sol', sol), ('sag', sag)):
        kr, ka, ksf = oge(a.set, a.sayfa_json, KUCUK_S, burc)
        bindir(f'kucuk_{t}', kr, ka, merk[t] + Z['sembol_isim_dx'][t] - ka.shape[1] / 2, KUCUK_Y - ka.shape[0] / 2)
        rap.setdefault('kucuk_sembol', {})[t] = {'burc': burc, 'sayfa': ksf, 'boyut': [ka.shape[1], ka.shape[0]]}

    # 6 tagline
    MS = Z['mesaj']
    BT = banka(a.set, a.sayfa_json, TAG_S)
    pm = MS['punto']
    for _ in range(20):
        rm, am, tm, km, yd = kelime(a.mesaj, BT, pm)
        wm = km[2] - km[0]
        if wm <= MS['genislik_siniri']:
            break
        pm *= MS['genislik_siniri'] / wm * 0.999
    bindir('tagline', rm, am, W / 2 - wm / 2 - km[0], MS['taban_y'] - tm)
    rap['tagline'] = {'punto': round(pm, 1), 'genislik': wm, 'kuculme': round(pm / MS['punto'], 4), 'yedek_doku': yd}
    log('tagline', rap['tagline'])

    bas()
    log('renk', rap.get('renk_esitleme'))

    # 7 yazi kutusu + pay icindeki yildizlar atilir (motor 3 Eki B kurali)
    pay = int(round(tdk.PAY_ORAN * tdk.TEMIZLIK_PAYI * W))
    yaz = [kutu[x] for x in ('isim1', 'isim2', 'sonsuz', 'tagline')]
    sil = np.zeros((H, W), bool); at = 0
    for cx_, cy_, rd_, _ in YL:
        for x0_, y0_, x1_, y1_ in yaz:
            dx_ = max(x0_ - pay - cx_, 0, cx_ - (x1_ + pay)); dy_ = max(y0_ - pay - cy_, 0, cy_ - (y1_ + pay))
            if np.hypot(dx_, dy_) <= rd_:
                ya, yb = max(0, int(cy_ - rd_) - 1), min(H, int(cy_ + rd_) + 2)
                xa, xb = max(0, int(cx_ - rd_) - 1), min(W, int(cx_ + rd_) + 2)
                yy_, xx_ = np.mgrid[ya:yb, xa:xb]
                sil[ya:yb, xa:xb] |= np.hypot(xx_ - cx_, yy_ - cy_) <= rd_
                at += 1
                break
    P += np.where(sil[..., None], 0, y_kat)
    del y_kat
    rap['yildiz'] = {'toplam': len(YL), 'atilan': at, 'pay_px': pay}
    out = P * (1 - A[..., None]) + Cp
    # 8 bit donusum: kanal basina bagimsiz TPDF +-1 LSB titresim (zemin; 5 Eki: ortak kanal titresimi JPEG q100'de
    # kayboluyordu, kanal basina olan kaliyor). Ogeler uzerinde (1 - alfa) ile azalir.
    rng = np.random.default_rng(zg.TOHUM)
    za = (1 - np.clip(A, 0, 1))
    for c in range(3):
        out[..., c] += (rng.random((H, W), np.float32) + rng.random((H, W), np.float32) - 1) * za
    u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
    del out, P, Cp
    Image.fromarray(u8).save(C / 'POSTER.png', dpi=(300, 300))
    Image.fromarray(np.clip(np.round(A * 255), 0, 255).astype(np.uint8)).save(C / 'ALFA.png')   # butunlestirme katmani icin
    rap['kutu'] = kutu
    np.savez_compressed(C / 'OGE_MASKE.npz', **{ad: np.concatenate([[x0, y0, sh[0], sh[1]], m.astype(np.int64)])
                                               for ad, (x0, y0, m, sh) in maske.items()})
    rap['sure_sn'] = round(time.time() - T0, 1)
    (C / 'POSTER.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    log('bitti', C)


if __name__ == '__main__':
    main()
