#!/usr/bin/env python3
"""Bakir WP ornegi (AQUARIUS_CANCER) inceleme paketi olcumu. Salt okur; uretim dosyalarina dokunmaz.
Girdi (ayni klasor, workflow Drive'dan indirir):
  19_renk_warm_parchment.jpg   galeri karti (3000x2250), poster kutusu renk_varyasyon_kur geometrisi
  WP_BASKI.jpg                 bu ornegin WP baskisi (11x14, 3307x4200)
  REF_WP_BASKI.jpg             onayli referans WP baskisi (e4f65cd, run 36848215749; TEMP/WP_ORNEK/AQUARIUS_CANCER)
  KAPI_WARM_PARCHMENT.json     WP kapi raporu (d dikis bilgisi)   KAPI_MIDNIGHT_BLUE.json  bant olcumleri (2400 birim)
Cikti (tam baskilar depoya girmez; 05 kenar tasmasi duzeltmesi sonrasi 2abf0c2 ile yenilendi): REF_WP_KESIT_isim_mesaj_sembol.jpg + WP_KESIT_isim_mesaj_sembol.jpg (1:1), OLCUM.txt
"""
import hashlib, json, os, sys
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(D, f)
HEDEF = (129, 72, 32)
K2400 = 3307 / 2400


def bantlar():
    o = {}
    try:
        o = json.load(open(P('KAPI_MIDNIGHT_BLUE.json'))).get('olcum') or {}
    except Exception:
        pass
    b = {'sembol': o.get('sembol_bant') or [1933, 2123], 'isim': o.get('isim_bant') or [2237, 2324],
         'mesaj': o.get('tag_bant') or [2614, 2687]}
    return b, ('KAPI_MIDNIGHT_BLUE olcum' if o else 'varsayilan (MB olcumu yok)')


def lumrel(c):
    c = np.asarray(c, np.float64) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def kontrast(a, b):
    la, lb = sorted((lumrel(a), lumrel(b)))
    return (lb + 0.05) / (la + 0.05)


def olc(a):
    """Bolgedeki murekkep (zeminden >= 25 koyu luma) ortalamasi, zemin ortalamasi, kontrast."""
    a = a.reshape(-1, 3).astype(np.float64)
    L = a @ [0.299, 0.587, 0.114]
    zl = np.percentile(L, 75)                 # zemin (seyrek yazi: piksellerin cogu kagit)
    m = L < zl - 25
    z = (L > zl - 6) & (L < zl + 6)
    if m.sum() < 20:
        return None
    ink, bg = a[m].mean(0), a[z].mean(0)
    return dict(ink=ink.round(1).tolist(), zemin=bg.round(1).tolist(), px=int(m.sum()), kontrast=round(kontrast(ink, bg), 2),
                hedef_fark=round(float(np.abs(ink - HEDEF).mean()), 1))


def baski_bolge(im, y0, y1, x0=250, x1=2150):
    """2400 birim bant -> baski px kesiti."""
    return np.asarray(im)[int(y0 * K2400):int(y1 * K2400), int(x0 * K2400):int(x1 * K2400)]


def kart_bolge(kart, baski_wh, y0, y1, x0=250, x1=2150):
    """2400 birim bant -> 19 kartindaki poster koordinati (renk_varyasyon_kur: 11:14 kirp, PH 1755, PY 150)."""
    W, H = baski_wh
    PH = 1755; PW = round(PH * 11 / 14); PX = (3000 - PW) // 2; PY = 150
    if W / H > 11 / 14:
        cw = round(H * 11 / 14); cx = (W - cw) // 2; cy = 0; ch = H
    else:
        ch = round(W * 14 / 11); cy = (H - ch) // 2; cx = 0; cw = W
    s = PW / cw
    f = lambda v, o, c0: int(round((v * K2400 - c0) * s)) + o
    return np.asarray(kart)[f(y0, PY, cy):f(y1, PY, cy), f(x0, PX, cx):f(x1, PX, cx)]


def sha(f):
    return hashlib.sha1(open(P(f), 'rb').read()).hexdigest()[:12]


B, kaynak = bantlar()
wp = Image.open(P('WP_BASKI.jpg')).convert('RGB')
ref = Image.open(P('REF_WP_BASKI.jpg')).convert('RGB')
kart = Image.open(P('19_renk_warm_parchment.jpg')).convert('RGB')
y0, y1 = B['sembol'][0] - 40, B['mesaj'][1] + 40
for ad, im in (('WP_KESIT_isim_mesaj_sembol.jpg', wp), ('REF_WP_KESIT_isim_mesaj_sembol.jpg', ref)):
    Image.fromarray(baski_bolge(im, y0, y1)).save(P(ad), quality=95, subsampling=0)

L = [f'# Bakir WP ornegi AQUARIUS_CANCER: olcum ({kaynak}; bantlar 2400 birim {B})',
     f'hedef bakir RGB {HEDEF}; kontrast = WCAG (murekkep ort. vs zemin ort.); murekkep = zeminden >= 25 koyu luma',
     f'boyut: 19 kart {kart.size}, WP baski {wp.size}, REF baski {ref.size}',
     f'sha1: WP_BASKI {sha("WP_BASKI.jpg")} | REF_WP_BASKI {sha("REF_WP_BASKI.jpg")} | ayni dosya: {sha("WP_BASKI.jpg") == sha("REF_WP_BASKI.jpg")}', '']
L.append('bolge | 19 kart: murekkep RGB / zemin RGB / kontrast / hedefe fark | WP baski 1:1 | REF 1:1 | 19-REF kontrast farki')
for ad in ('isim', 'mesaj', 'sembol'):
    a, b = B[ad]
    k19 = olc(kart_bolge(kart, wp.size, a, b))
    kw = olc(baski_bolge(wp, a, b))
    kr = olc(baski_bolge(ref, a, b))
    fmt = lambda r: '-' if r is None else f"{r['ink']} / {r['zemin']} / {r['kontrast']} / {r['hedef_fark']}"
    fark = '-' if (k19 is None or kr is None) else round(k19['kontrast'] - kr['kontrast'], 2)
    L.append(f'{ad} | {fmt(k19)} | {fmt(kw)} | {fmt(kr)} | {fark}')
try:
    k = json.load(open(P('KAPI_WARM_PARCHMENT.json')))
    L += ['', f"WP kapilar: {k.get('kapilar')} | kapilar_gecti {k.get('kapilar_gecti')} | yontem {k.get('yontem')}",
          f"d) dikis (bilgi, kabul kosulu degil): {json.dumps(k.get('bilgi_d_dikis'), ensure_ascii=False)[:600]}"]
except Exception as e:
    L += ['', f'KAPI_WARM_PARCHMENT.json okunamadi: {e}']
open(P('OLCUM.txt'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
