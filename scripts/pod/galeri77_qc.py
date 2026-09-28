#!/usr/bin/env python3
"""77 cift galerisi: cifte ozgu QC (sembol, kapak, eski metin, dosya seti). duvar_qc.py (zemin/poster/kontrast/tire)
ve metin_qc.py (yazim/tire/yasak ifade) ile birlikte kosar. Her satir PASS/FAIL; cikis 0 = hepsi PASS.
  dosya    : 19 gorsel, adlar CL kesin paketiyle birebir, hepsi 3000x2250
  kapak    : 01 kapaktaki poster ciftin MB baskisi (cok olcekli sablon NCC >= 0.80; CL disi ciftte CL MB'den
             en az 0.02 yuksek -> baska ciftin kapagi degil)
  sembol   : 5 renk baskinin sembol + kucuk sembol bolgesi murekkep maskesi ciftin MB'sine CL MB'den daha yakin
             (fark >= 0.05; CL disi ciftte) ve NCC >= 0.60 (renkler arasi ayni tasarim)
  eski metin: 03-14 ust etiket ve degisen satirlar CL metnini tasimiyor (CL krem karta NCC < 0.90), yeni metin
             yazili (taze render maskesine NCC >= 0.90); 02 satirlari ve METIN.json'da eski burc adi yok
Kullanim: galeri77_qc.py CIFT KAYNAK_DIR KREM_DIR PAKET_DIR CL_MB.jpg
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import galeri77_kur as G                                           # noqa: E402

C, KAY, KR, P, CL_MB = sys.argv[1:6]
J = json.load(open(os.path.join(KR, 'KUR.json')))
A, B = J['a'], J['b']
CL = C == 'CANCER_LIBRA'
hepsi = True


def sonuc(ad, ok, bilgi):
    global hepsi
    hepsi &= bool(ok)
    print(f'{ad}: {bilgi} | {"PASS" if ok else "FAIL"}')


def ncc(a, b):
    a = a.astype(np.float32) - a.mean(); b = b.astype(np.float32) - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9))


# --- dosya seti
beklenen = sorted(os.listdir(os.path.join(ROOT, 'data/pod/cl_galeri_final19')))
var = sorted(f for f in os.listdir(P) if f.endswith('.jpg'))
boy = {f: Image.open(os.path.join(P, f)).size for f in var}
sonuc('dosya', var == beklenen and all(v == (3000, 2250) for v in boy.values()),
      f'{len(var)} gorsel, ad seti {"ayni" if var == beklenen else "FARKLI"}, boyut {set(boy.values())}')


# --- kapak: MB baski sablonu kapakta (1/4 olcek, cok olcekli)
def sablon_skor(kapak, baski):
    K = cv2.cvtColor(np.asarray(Image.open(kapak).convert('RGB')), cv2.COLOR_RGB2GRAY)
    K = cv2.resize(K, (750, 562), interpolation=cv2.INTER_AREA).astype(np.float32)
    Bm = G.rebate(Image.open(baski).convert('RGB')).convert('L')
    en = 0.0
    for h in range(440, 520, 4):                                    # kapakta poster boyu ~1850-2000 px (1/4: 460-500)
        t = np.asarray(Bm.resize((round(h * Bm.width / Bm.height), h), Image.LANCZOS)).astype(np.float32)
        en = max(en, float(cv2.minMaxLoc(cv2.matchTemplate(K, t, cv2.TM_CCOEFF_NORMED))[1]))
    return en


kapak = os.path.join(P, '01_kapak.jpg')
s_p = sablon_skor(kapak, os.path.join(KAY, 'BASKI_MIDNIGHT_BLUE.jpg'))
s_c = s_p if CL else sablon_skor(kapak, CL_MB)
sonuc('kapak', s_p >= 0.80 and (CL or s_p - s_c >= 0.02), f'cift MB NCC {s_p:.3f} | CL MB NCC {s_c:.3f}')


# --- sembol: 5 renk baskinin sembol bolgeleri ciftin MB'siyle ayni tasarim
def maske(yol):
    a = np.asarray(Image.open(yol).convert('L').resize((1100, 1400), Image.LANCZOS))
    bg = cv2.medianBlur(a, 41).astype(np.float32)
    m = (np.abs(a.astype(np.float32) - bg) > 18).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 3)


BOLGE = (slice(140, 990), slice(150, 950))                          # halka + birlesik sembol + kucuk semboller
mb = maske(os.path.join(KAY, 'BASKI_MIDNIGHT_BLUE.jpg'))[BOLGE]
clm = maske(CL_MB)[BOLGE]
for r in G.RENKLER[1:]:
    m = maske(os.path.join(KAY, f'BASKI_{r}.jpg'))[BOLGE]
    n_p, n_c = ncc(m, mb), ncc(m, clm)
    sonuc(f'sembol {r}', n_p >= 0.60 and (CL or n_p - n_c >= 0.05), f'cift MB NCC {n_p:.3f} | CL MB NCC {n_c:.3f}')


# --- eski metin kalmadi, yeni metin yazili (krem kartlar; duvar hatti metin piksellerini tasir)
def murekkep(im, kutu, pay=4):
    x0, y0, x1, y1 = (int(round(v)) for v in kutu)
    a = np.asarray(im.convert('RGB')).astype(np.float32)[y0 - pay:y1 + pay, x0 - pay:x1 + pay]
    zemin = np.median(a.reshape(-1, 3), 0)
    return np.abs(a - zemin).max(2)


MON = os.path.join(os.environ.get('FD', 'fonts'), 'Montserrat[wght].ttf')
fe = G.font(MON, G.ETIKET['boy'], G.ETIKET['w'])
eski_e = 'ASTROLOVE  /  CANCER + LIBRA'; yeni_e = f'ASTROLOVE  /  {A.upper()} + {B.upper()}'
kutu_e = G.murekkep_kutu(fe, yeni_e, G.ETIKET['x'], G.ETIKET['taban'])


def render(t, f, x, taban, boyut):
    im = Image.new('RGB', boyut, G.BG); ImageDraw.Draw(im).text((x, taban), t, font=f, fill=(0, 0, 0), anchor='ls'); return im


ref_yeni = murekkep(render(yeni_e, fe, G.ETIKET['x'], G.ETIKET['taban'], (3000, 300)), kutu_e)
kotu = []
for k in ['03_konsept', '04_kisisellestirme', '05_renk_ve_dijital', '06_hediye_sahne', '07_cerceveler', '08_boylar',
          '09_yatak_sahne', '10_calisma_sahne', '11_yemek_sahne', '12_zoom', '13_kagit', '14_surec']:
    im = Image.open(os.path.join(KR, k + '.jpg'))
    n_y = ncc(murekkep(im, kutu_e), ref_yeni)
    n_e = ncc(murekkep(im, kutu_e), murekkep(Image.open(os.path.join(G.KREM_CL, k + '.jpg')), kutu_e)) if not CL else 0
    if n_y < 0.90 or n_e >= 0.90:
        kotu.append(f'{k} yeni {n_y:.2f} eski {n_e:.2f}')
satir = [(k, s) for k, v in J['satirlar'].items() for s in v]
for k, s in satir:
    if s['eski'] != s['yeni'] and not CL:
        ad = {'03': '03_konsept', '04': '04_kisisellestirme'}[k]
        n_e = ncc(murekkep(Image.open(os.path.join(KR, ad + '.jpg')), s['kutu']),
                  murekkep(Image.open(os.path.join(G.KREM_CL, ad + '.jpg')), s['kutu']))
        if n_e >= 0.90:
            kotu.append(f'{ad} "{s["eski"][:24]}" degismedi ({n_e:.2f})')
j02 = json.load(open(os.path.join(P, '02_format.json')))
m02 = ' '.join(s['metin'] for s in j02['satirlar'])
if f'{A.upper()} + {B.upper()}' not in m02 or f'{A} and {B} couples' not in m02:
    kotu.append('02 ust etiket / hediye satiri cift adini tasimiyor')
eski_ad = {'Cancer', 'Libra'} - {A, B}
metin = json.dumps(json.load(open(os.path.join(KR, 'METIN.json'))), ensure_ascii=False)
for e in eski_ad:
    if re.search(rf'\b{e}\b', metin, re.I) or re.search(rf'\b{e}\b', m02, re.I):
        kotu.append(f'eski burc adi metinde: {e}')
sonuc('eski metin', not kotu, f'{len(satir)} satir + 12 ust etiket + 02 | {"; ".join(kotu) or "temiz"}')
print('GENEL', 'PASS' if hepsi else 'FAIL')
sys.exit(0 if hepsi else 1)
