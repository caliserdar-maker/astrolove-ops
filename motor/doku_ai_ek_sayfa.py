#!/usr/bin/env python3
"""DOKU_AI ek maske sayfalari (Serdar 4 Eki): KUCUK (12 kucuk burc sembolu), PLAKA (12 burc ismi plakasi),
CEMBER (halka), LOGO (sonsuz logo). Duzen doku_ai_sayfa.py ile ayni: siyah zemin, duz beyaz maske (asset alfasi,
sekil degistirilmez), sol ust hucrede REFERANS ana sembol (orijinal altin), 24x36 / 300 dpi baski olcegi, JSON konum.

Olcek (asset px -> 24x36 baski px):
  kucuk sembol : 16x20 orijinal posterden (BURC_BURC.jpg, sol sembol) olculen olcek x KUCUK_24 (SCORPIO_VIRGO 24x36 /
                 16x20 sabitleri: 0.5485/0.3238, 0.5754/0.3394)
  plaka        : 16x20 orijinal posterden (sol isim) olculen olcek (ncc >= 0.9); eslesmeyenlerde (poster yazisi plakadan
                 farkli) buyuk harf yuksekligi kurali (iyi eslesmelerin medyani); x PLAKA_24 (isim punto 408 / 241)
  cember       : motor/varlik/halka/HALKA_24x36.png (zaten 24x36), tam sekil
  logo         : sonsuz genisligi 24x36 sabitlerinde 636 px -> 636 / logo genisligi

Kullanim: doku_ai_ek_sayfa.py --olcek olcek_16x20.json --sym DIR --plaka DIR --logo logo.png --referans main_..png --cikti DIR
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_ai_sayfa as das                                          # noqa: E402

Image.MAX_IMAGE_PIXELS = None
BURC = ['aquarius', 'aries', 'cancer', 'capricorn', 'gemini', 'leo', 'libra', 'pisces', 'sagittarius', 'scorpio',
        'taurus', 'virgo']
KUCUK_24 = (0.5485 / 0.3238 + 0.5754 / 0.3394) / 2                 # 1.6946
PLAKA_24 = 408 / 241                                                 # 1.6929
SONSUZ_W24 = 636
NCC_MIN = 0.9
REF = (640, 580)                                                     # referans hucresi (diger sayfalarla ayni)
PAY = 60


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def maske(f, s):
    a = np.asarray(Image.open(f).convert('RGBA'))[..., 3]
    ys, xs = np.nonzero(a > 0)
    k = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    a = a[k[1]:k[3], k[0]:k[2]].astype(np.float32)
    m = cv2.resize(a, (max(1, round(a.shape[1] * s)), max(1, round(a.shape[0] * s))), interpolation=cv2.INTER_AREA)
    return m, k


def izgara(ad, ogeler, nx, ny, ref):
    """ogeler: [(ad, maske, bilgi)] -> sayfa; hucre = en buyuk oge + 2 x PAY; sol ust hucre referans."""
    cw = max(max(m.shape[1] for _, m, _ in ogeler) + 2 * PAY, REF[0])
    ch = max(max(m.shape[0] for _, m, _ in ogeler) + 2 * PAY, REF[1])
    W, H = nx * cw, ny * ch
    out = np.zeros((H, W, 3), np.float32)
    rw, rh = min(cw, REF[0]), min(ch, REF[1])
    out[:rh, :rw] = das.referans(ref, rw, rh)
    kayit = []
    for i, (oad, m, bilgi) in enumerate(ogeler):
        k = i + 1; gx, gy = k % nx, k // nx
        x = gx * cw + (cw - m.shape[1]) // 2; y = gy * ch + (ch - m.shape[0]) // 2
        out[y:y + m.shape[0], x:x + m.shape[1]] = np.maximum(out[y:y + m.shape[0], x:x + m.shape[1]], m[..., None])
        kayit.append({'oge': oad, 'hucre': [gx * cw, gy * ch, gx * cw + cw, gy * ch + ch],
                      'kutu': [x, y, x + m.shape[1], y + m.shape[0]]} | bilgi)
    return ad, out, {'tur': ad.rsplit('_', 1)[0].lower(), 'boyut': [W, H], 'referans_kutu': [0, 0, rw, rh], 'ogeler': kayit}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--olcek', required=True)
    ap.add_argument('--sym', required=True)
    ap.add_argument('--plaka', required=True)
    ap.add_argument('--logo', required=True)
    ap.add_argument('--halka', default=str(KOK / 'varlik' / 'halka' / 'HALKA_24x36.png'))
    ap.add_argument('--referans', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    O = json.loads(Path(a.olcek).read_text())
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    sayfalar = []
    # KUCUK: 6 / sayfa, 3x3 izgara (referans + 6)
    kk = []
    for b in BURC:
        f = Path(a.sym) / f'sym_{b}_gold.png'
        s16 = O[b]['kucuk_16x20']['olcek']; s = s16 * KUCUK_24
        m, k = maske(f, s)
        kk.append((b.upper(), m, {'kaynak': f.name, 'sha256': sha(f), 'kaynak_kirp': k, 'olcek': round(s, 5),
                                  'olcek_kaynagi': f'16x20 orijinal {b.upper()}_{b.upper()}.jpg eslesme {s16} '
                                                   f'(ncc {O[b]["kucuk_16x20"]["ncc"]}) x {KUCUK_24:.4f}'}))
    for i in range(2):
        sayfalar.append(izgara(f'KUCUK_{i + 1}', kk[6 * i:6 * i + 6], 3, 3, a.referans))
    # PLAKA: 6 / sayfa, 2x4 izgara (referans + 6)
    pp = []
    for b in BURC:
        f = Path(a.plaka) / f'{b}_name_gold.png'
        P = O[b]['plaka_16x20']
        if P['ncc'] >= NCC_MIN:
            s16, ka = P['olcek'], f'16x20 orijinal {b.upper()}_{b.upper()}.jpg eslesme (ncc {P["ncc"]})'
        else:
            s16 = P['kural_olcek']
            ka = (f'poster yazisi plakadan farkli (ncc {P["ncc"]}); buyuk harf yuksekligi kurali '
                  f'{O["_plaka_buyuk_harf_16x20"]} px (16x20)')
        s = s16 * PLAKA_24
        m, k = maske(f, s)
        pp.append((b.upper(), m, {'kaynak': f.name, 'sha256': sha(f), 'kaynak_kirp': k, 'olcek': round(s, 5),
                                  'olcek_kaynagi': f'{ka}: {s16} x {PLAKA_24:.4f}'}))
    for i in range(2):
        sayfalar.append(izgara(f'PLAKA_{i + 1}', pp[6 * i:6 * i + 6], 2, 4, a.referans))
    # CEMBER: tam halka 1:1; referans sol ust kosede (halka disinda kalan kose)
    h = np.asarray(Image.open(a.halka).convert('L'), np.float32)
    ys, xs = np.nonzero(h > 0)
    k = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    m = h[k[1]:k[3], k[0]:k[2]]
    W, H = m.shape[1] + 2 * PAY, m.shape[0] + 2 * PAY
    out = np.zeros((H, W, 3), np.float32)
    out[PAY:PAY + m.shape[0], PAY:PAY + m.shape[1]] = m[..., None]
    if (out[:REF[1], :REF[0]] > 0).any():
        sys.exit('FAIL: referans hucresi halkaya degiyor')
    out[:REF[1], :REF[0]] = das.referans(a.referans, *REF)
    sayfalar.append(('CEMBER_1', out, {'tur': 'cember', 'boyut': [W, H], 'referans_kutu': [0, 0, *REF], 'ogeler': [
        {'oge': 'HALKA', 'kutu': [PAY, PAY, PAY + m.shape[1], PAY + m.shape[0]], 'kaynak': Path(a.halka).name,
         'sha256': sha(a.halka), 'kaynak_kirp': k, 'olcek': 1.0, 'olcek_kaynagi': 'HALKA_24x36 zaten 24x36 baski olcegi'}]}))
    # LOGO
    f = Path(a.logo)
    w0 = Image.open(f).size[0]
    s = SONSUZ_W24 / w0
    m, k = maske(f, s)
    W, H = REF[0] + m.shape[1] + 3 * PAY, max(REF[1], m.shape[0] + 2 * PAY)
    out = np.zeros((H, W, 3), np.float32)
    out[:REF[1], :REF[0]] = das.referans(a.referans, *REF)
    x, y = REF[0] + 2 * PAY, (H - m.shape[0]) // 2
    out[y:y + m.shape[0], x:x + m.shape[1]] = m[..., None]
    sayfalar.append(('LOGO_1', out, {'tur': 'logo', 'boyut': [W, H], 'referans_kutu': [0, 0, *REF], 'ogeler': [
        {'oge': 'LOGO', 'kutu': [x, y, x + m.shape[1], y + m.shape[0]], 'kaynak': f.name, 'sha256': sha(f),
         'kaynak_kirp': k, 'olcek': round(s, 5), 'olcek_kaynagi': f'24x36 sonsuz genisligi {SONSUZ_W24} px / {w0}'}]}))
    ozet = []
    for ad, rgb, j in sayfalar:
        p = C / f'DOKU_AI_{ad}.png'
        Image.fromarray(np.clip(np.round(rgb), 0, 255).astype(np.uint8)).save(p, optimize=True)
        j |= {'dosya': p.name, 'sha256': sha(p), 'referans': Path(a.referans).name, 'olcek': '24x36 baski, 300 dpi, 1:1'}
        (C / f'DOKU_AI_{ad}.json').write_text(json.dumps(j, ensure_ascii=False, indent=1))
        ozet.append({'sayfa': ad, 'boyut': j['boyut'], 'oge': len(j['ogeler'])})
    print(json.dumps(ozet, ensure_ascii=False))


if __name__ == '__main__':
    main()
