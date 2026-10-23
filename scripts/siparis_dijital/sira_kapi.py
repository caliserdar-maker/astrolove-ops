#!/usr/bin/env python3
"""sira=ters QC (Serdar 23 Eki; bagimsiz inceleme bulgusu 2-3): ayni siparisin ILK (ilandaki duzen) ve TERS dosyasini
olcer, PASS/FAIL. Esik uydurulmaz: degismemesi gereken bantlar ayni dosya ciftinin bos kagit bandindaki farkla
(olculen gurultu tabani) karsilastirilir; sembol takasi goreli eslesmeyle (dogru eslesme yanlis eslesmeden kucuk).
  1. birlesik sembol bandi: MUREKKEP piksellerinde fark <= ayni bandin KAGIT piksellerindeki fark (aynalama / dondurme yok)
  2. mesaj bandi: ayni olcut. Murekkep / kagit ayrimi bant basina Otsu esigi (sabit esik yok). Kagit pikselleri olcut
     disi: paket asamasi (tek_jpg gren) her kosuda farkli kagit gurultusu ekler (23 Eki olcumu: mesaj kagit 0.77, murekkep 0.57).
  3. kucuk semboller: ILK'in sag glifi TERS'in solunda, ILK'in sol glifi TERS'in saginda (goreli)
  4. isimler (OCR, istege bagli): sol = SIRA_SOL, sag = SIRA_SAG (ortam degiskeni; isim loga / dosyaya yazilmaz)
Bant y oranlari 11x14 WP sayfasindan (1100x1400 onizleme olcumu): birlesik 0.107-0.571, kucuk sembol 0.629-0.700,
isim 0.729-0.771, mesaj 0.843-0.893, kagit (bos) 0.786-0.836. Kullanim: sira_kapi.py ILK.jpg TERS.jpg"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageOps

BANT = {'birlesik': (0.107, 0.571), 'kucuk': (0.629, 0.700), 'isim': (0.729, 0.771), 'mesaj': (0.843, 0.893),
        'kagit': (0.786, 0.836)}


def gri(yol, w=1100):
    im = Image.open(yol).convert('L')
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def fark(a, b, y):
    h = a.shape[0]; y0, y1 = int(y[0] * h), int(y[1] * h)
    return float(np.abs(a[y0:y1] - b[y0:y1]).mean())


def otsu(v):
    h, _ = np.histogram(v, 256, (0, 256)); p = h / max(h.sum(), 1); w = np.cumsum(p); m = np.cumsum(p * np.arange(256))
    s = (m[-1] * w - m) ** 2 / np.maximum(w * (1 - w), 1e-12)
    return int(np.argmax(s))


def murekkep_fark(a, b, y):
    """bant icinde: murekkep (a ya da b Otsu altinda) ve kagit piksellerinin ayri ortalama mutlak farki."""
    h = a.shape[0]; y0, y1 = int(y[0] * h), int(y[1] * h)
    A, B = a[y0:y1], b[y0:y1]
    e = otsu(np.concatenate([A.ravel(), B.ravel()]))
    ink = (A < e) | (B < e); d = np.abs(A - B)
    return round(float(d[ink].mean()), 3), round(float(d[~ink].mean()), 3), e


def eslesme(sablon, bant, x0, x1):
    """sablon'u bant icinde [x0, x1) araliginda kaydirarak en kucuk ortalama mutlak fark."""
    w = sablon.shape[1]
    return min(float(np.abs(bant[:, x:x + w] - sablon).mean()) for x in range(x0, min(x1, bant.shape[1] - w)))


def ocr(im, kutu):
    c = ImageOps.autocontrast(im.crop(kutu).resize(((kutu[2] - kutu[0]) * 3, (kutu[3] - kutu[1]) * 3)))
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        c.save(f.name)
        return subprocess.run(['tesseract', f.name, 'stdout', '--psm', '7', '-l', 'eng'],
                              capture_output=True, text=True).stdout.strip()


def olc(ilk, ters):
    A, B = gri(ilk), gri(ters)
    a, b = np.asarray(A, np.float32), np.asarray(B, np.float32)
    if a.shape != b.shape:
        return {'PASS': False, 'hata': f'boyut {a.shape} != {b.shape}'}
    W, H = a.shape[1], a.shape[0]
    R = {'kagit_taban': round(fark(a, b, BANT['kagit']), 3)}
    for k in ('birlesik', 'mesaj'):
        mk, kg, e = murekkep_fark(a, b, BANT[k])
        R[k] = {'murekkep': mk, 'kagit': kg, 'otsu': e}
        R[f'{k}_gecti'] = mk <= kg
    y0, y1 = int(BANT['kucuk'][0] * H), int(BANT['kucuk'][1] * H)
    m = W // 2
    sol_a, sag_a, ba = a[y0:y1, int(W * 0.22):int(W * 0.43)], a[y0:y1, int(W * 0.57):int(W * 0.78)], b[y0:y1]
    R['sol_glif'] = {'ilk_sag_ile': round(eslesme(sag_a, ba[:, :m], 0, m), 2), 'ilk_sol_ile': round(eslesme(sol_a, ba[:, :m], 0, m), 2)}
    R['sag_glif'] = {'ilk_sol_ile': round(eslesme(sol_a, ba[:, m:], 0, m), 2), 'ilk_sag_ile': round(eslesme(sag_a, ba[:, m:], 0, m), 2)}
    R['takas_gecti'] = (R['sol_glif']['ilk_sag_ile'] < R['sol_glif']['ilk_sol_ile']
                        and R['sag_glif']['ilk_sol_ile'] < R['sag_glif']['ilk_sag_ile'])
    sol, sag = os.environ.get('SIRA_SOL'), os.environ.get('SIRA_SAG')
    if sol and sag:
        iy0, iy1 = int(BANT['isim'][0] * H), int(BANT['isim'][1] * H)
        o_sol, o_sag = ocr(B, (int(W * 0.2), iy0, int(W * 0.44), iy1)), ocr(B, (int(W * 0.56), iy0, int(W * 0.8), iy1))
        R['isim_gecti'] = o_sol == sol.upper() and o_sag == sag.upper()     # degerler yazilmaz
    gec = [R['birlesik_gecti'], R['mesaj_gecti'], R['takas_gecti']] + ([R['isim_gecti']] if 'isim_gecti' in R else [])
    R['PASS'] = all(gec)
    return R


if __name__ == '__main__':
    r = olc(sys.argv[1], sys.argv[2])
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r['PASS'] else 2)
