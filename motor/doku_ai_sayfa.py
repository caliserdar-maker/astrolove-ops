#!/usr/bin/env python3
"""DOKU_AI harf sayfalari (Serdar 4 Eki, YENI YONTEM: altin dokuyu ChatGPT uretir, harf sekli bizden).

Sayfalar: siyah zemin, duz beyaz glif (ve beyaz maske). Olcek = en buyuk baski boyu 24x36, 300 dpi, 1:1
(motor/sabitler/*_24x36.json: isim Cinzel wght 500 punto 408, buyuk harf govdesi 286 px; tagline EB Garamond
Italic punto 372, T govdesi 248 px; kucuk sembol olcek 0.548; sonsuz genislik 636 px; halka cizgisi 34 px).
Her sayfanin sol ust hucresinde REFERANS ana sembol (orijinal altin, siyah ustune). Glif konumlari JSON'da:
cizim = ImageDraw.text(koken, karakter, font(punto, wght), anchor='ls'); ayni cagri sekil maskesini yeniden uretir
(sekil sadakati kapisi bu maskeyi kullanir, AI gorselinden yalniz doku alinir).

Kullanim: doku_ai_sayfa.py --referans main_capricorn_scorpio_gold.png --halka motor/varlik/halka/HALKA_24x36.png
          --kucuk sym_cancer_gold.png --sonsuz-poster CANCER_LIBRA.jpg --cikti DIR
"""
import argparse, hashlib, json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None

ISIM = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + list('ÇĞİÖŞÜ') + list("&'-.")
TAG = (list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + list('abcdefghijklmnopqrstuvwxyz') + list('çğıöşüİÇĞÖŞÜ')
       + list('0123456789') + list(".,'!?&-:;"))
# 24x36 (7200 x 10800, 300 dpi) sabitlerinden
YAZI = {'isim': {'font': 'Cinzel.ttf', 'wght': 500, 'punto': 408, 'glifler': ISIM, 'hucre': (640, 580), 'izgara': (4, 4)},
        'tagline': {'font': 'EBGaramond-Italic.ttf', 'wght': None, 'punto': 372, 'glifler': TAG, 'hucre': (540, 520),
                    'izgara': (5, 5)}}
KUCUK_OLCEK = 0.548          # SCORPIO_VIRGO_*_24x36 kucuk_sembol olcek (asset -> baski px)
SONSUZ_W = 636               # 24x36 sonsuz genisligi (px)
SONSUZ_KUTU = (4420, 4590, 2300, 2760)   # CANCER_LIBRA orijinal 16x20 sonsuz cevresi (y0, y1, x0, x1; isim harfi yok)
HALKA_KESIT = (1500, 1780, 2700, 4500)   # HALKA_24x36 ust yay (y0, y1, x0, x1): 1800 px kiris, 34 px cizgi


def sha(b):
    return hashlib.sha256(b).hexdigest()


def font(d, p, w):
    f = ImageFont.truetype(str(KOK / 'font' / d), p)
    if w:
        f.set_variation_by_axes([w])
    return f


def referans(f, W, H):
    """orijinal altin ana sembol, siyah ustune, W x H hucreye sigdirilmis (RGB)."""
    im = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)[..., [2, 1, 0, 3]]
    ys, xs = np.nonzero(im[..., 3] > 8)
    im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)
    k = min((W - 40) / im.shape[1], (H - 40) / im.shape[0])
    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    out = np.zeros((H, W, 3), np.float32)
    y, x = (H - im.shape[0]) // 2, (W - im.shape[1]) // 2
    out[y:y + im.shape[0], x:x + im.shape[1]] = im[..., :3] * (im[..., 3:] / 255)
    return out


def yazi_sayfalari(ad, Y, ref):
    F = font(Y['font'], Y['punto'], Y['wght'])
    cw, ch = Y['hucre']; nx, ny = Y['izgara']
    asc = -min(F.getbbox(c, anchor='ls')[1] for c in Y['glifler'])
    dsc = max(F.getbbox(c, anchor='ls')[3] for c in Y['glifler'])
    pay_y = (ch - asc - dsc) // 2
    yer = nx * ny - 1                                                     # sol ust hucre referans
    n_say = -(-len(Y['glifler']) // yer)
    per = -(-len(Y['glifler']) // n_say)                                  # sayfalara esit dagit
    sayfalar = []
    for s in range(n_say):
        gl = Y['glifler'][s * per:(s + 1) * per]
        W, H = nx * cw, ny * ch
        im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
        kayit = []
        for i, c in enumerate(gl):
            k = i + 1; gx, gy = k % nx, k // nx
            x0, y0 = gx * cw, gy * ch
            b = F.getbbox(c, anchor='ls')
            ox = int(round(x0 + (cw - (b[2] - b[0])) / 2 - b[0])); oy = y0 + pay_y + asc
            d.text((ox, oy), c, font=F, fill=255, anchor='ls')
            kayit.append({'karakter': c, 'kod': f'U+{ord(c):04X}', 'hucre': [x0, y0, x0 + cw, y0 + ch],
                          'koken_ls': [ox, oy], 'murekkep': [ox + b[0], oy + b[1], ox + b[2], oy + b[3]]})
        rgb = np.repeat(np.asarray(im, np.float32)[..., None], 3, 2)
        rgb[:ch, :cw] = referans(ref, cw, ch)
        sayfalar.append((f'{ad.upper()}_{s + 1}', rgb, {
            'tur': ad, 'font': Y['font'], 'wght': Y['wght'], 'punto': Y['punto'], 'anchor': 'ls',
            'boyut': [W, H], 'referans_kutu': [0, 0, cw, ch], 'glifler': kayit}))
    return sayfalar


def maske_sayfasi(ref, a):
    # 1 halka yayi (1:1 baski maskesi)
    h = np.asarray(Image.open(a.halka).convert('L'), np.float32)
    y0, y1, x0, x1 = HALKA_KESIT
    halka = np.clip(h[y0:y1, x0:x1] * 255 / np.percentile(h[h > 0], 90), 0, 255)   # govde tam beyaz
    # 2 kucuk burc sembolu: asset alfasi, 24x36 olcegi
    k = cv2.imread(a.kucuk, cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32)
    k = cv2.resize(k, None, fx=KUCUK_OLCEK, fy=KUCUK_OLCEK, interpolation=cv2.INTER_AREA)
    ys, xs = np.nonzero(k > 8); k = k[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # 3 sonsuz: yuksek cozunurluklu kaynak yok; orijinal 16x20 posterden kapsama -> 24x36 boyuna yumusak buyutme
    P = np.asarray(Image.open(a.sonsuz_poster).convert('RGB'), np.float32)
    sy0, sy1, sx0, sx1 = SONSUZ_KUTU
    r = P[sy0:sy1, sx0:sx1]
    kenar = np.concatenate([r[:6].reshape(-1, 3), r[-6:].reshape(-1, 3), r[:, :6].reshape(-1, 3), r[:, -6:].reshape(-1, 3)])
    zem = np.median(kenar, 0)
    D = (r - zem) @ np.array([0.299, 0.587, 0.114], np.float32)
    rb = (r[..., 0] - r[..., 2]) - (zem[0] - zem[2])
    A = np.maximum(np.clip(D / np.percentile(D[D > 40], 50), 0, 1), np.clip(rb / np.percentile(rb[rb > 60], 50), 0, 1))
    ys, xs = np.nonzero(A > 0.5); A = A[ys.min() - 2:ys.max() + 3, xs.min() - 2:xs.max() + 3]
    s = SONSUZ_W / (xs.max() - xs.min() + 1)
    A = cv2.resize(A, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    A = cv2.GaussianBlur(A, (0, 0), 0.6 * s)
    A = np.clip((A - 0.5) * 4 + 0.5, 0, 1) * 255                        # yumusak kenarli ikili maske
    pay = 100
    cw, ch = YAZI['isim']['hucre']
    W = max(halka.shape[1], cw + pay + k.shape[1] + pay + A.shape[1]) + 2 * pay
    H = pay + max(ch, k.shape[0], A.shape[0]) + pay + halka.shape[0] + pay
    out = np.zeros((H, W, 3), np.float32)
    out[:ch, :cw] = referans(ref, cw, ch)
    kayit = []

    def koy(ad, m, x, y, not_):
        out[y:y + m.shape[0], x:x + m.shape[1]] = np.maximum(out[y:y + m.shape[0], x:x + m.shape[1]], m[..., None])
        kayit.append({'oge': ad, 'kutu': [x, y, x + m.shape[1], y + m.shape[0]], 'not': not_})
    x = cw + pay
    koy('kucuk_sembol', k, x, pay, f'{Path(a.kucuk).name} alfa x {KUCUK_OLCEK}')
    x += k.shape[1] + pay
    koy('sonsuz', A, x, pay, f'orijinal 16x20 posterden kapsama x {s:.3f} (yuksek cozunurluklu kaynak yok)')
    koy('halka_yayi', halka, (W - halka.shape[1]) // 2, pay + max(ch, k.shape[0], A.shape[0]) + pay,
        f'{Path(a.halka).name} [{y0}:{y1}, {x0}:{x1}]')
    return ('MASKE_1', out, {'tur': 'maske', 'boyut': [W, H], 'referans_kutu': [0, 0, cw, ch], 'ogeler': kayit})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--referans', required=True)
    ap.add_argument('--halka', required=True)
    ap.add_argument('--kucuk', required=True)
    ap.add_argument('--sonsuz-poster', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    sayfalar = yazi_sayfalari('isim', YAZI['isim'], a.referans) + yazi_sayfalari('tagline', YAZI['tagline'], a.referans)
    sayfalar.append(maske_sayfasi(a.referans, a))
    ozet = []
    for ad, rgb, j in sayfalar:
        f = C / f'DOKU_AI_{ad}.png'
        Image.fromarray(np.clip(np.round(rgb), 0, 255).astype(np.uint8)).save(f, optimize=True)
        j |= {'dosya': f.name, 'sha256': sha(f.read_bytes()), 'referans': Path(a.referans).name,
              'olcek': '24x36 baski, 300 dpi, 1:1'}
        (C / f'DOKU_AI_{ad}.json').write_text(json.dumps(j, ensure_ascii=False, indent=1))
        ozet.append({'sayfa': ad, 'boyut': j['boyut'], 'glif': len(j.get('glifler', j.get('ogeler', [])))})
    print(json.dumps(ozet, ensure_ascii=False))


if __name__ == '__main__':
    main()
