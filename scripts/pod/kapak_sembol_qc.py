#!/usr/bin/env python3
"""78 kapak: isimlerin ustundeki kucuk burc sembolu on kontrolu (SALT OKUMA, 28 Eyl hata-kontrol).
Girdi: KAPAK_<A>_<B>.jpg (kapak_v9_toplu.py ciktisi, 3000x2250). Sol sembol = A, sag = B.
Olcum (sembol ornekleri birbirine karsi; ayni burcun diger kapaklardaki ornekleri = referans, kendisi haric medyan):
  yanlis_burc : baska burcun sablonuna benzerlik kendi sablonundan yuksek
  eksik       : sablon murekkebinin ornekte olmayan orani (kesik/kayip)
  fazla       : sablonun 3 px disinda kalan ornek murekkebi / sablon murekkebi (kalinti, kopuk parca)
  boyut       : kutu eni/boyu burc medyanindan farki (px)
  puruz       : kenar bandinda yuksek frekans enerjisi / burc medyani (tirtikli kenar)
Esikler bu 78 kapagin olculen dagilimindan (medyan + MAD) turetilir; sabit sayi tahmini yok.
Cikti: <cikis>/SEMBOL_QC.csv, SEMBOL_QC.md, TEMAS_SAYFASI.jpg (78 kare, 1:1 piksel, cift adi yazili).
Kullanim: kapak_sembol_qc.py KAPAK_KLASORU CIKIS_KLASORU
"""
import csv
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

KUTU = (1060, 1360, 1960, 1570)        # 3000x2250 kapakta sembol bandi (78 kapakta olculdu: y 1390-1539, x 1133-1945)
ORTA = 1510 - KUTU[0]                  # sol/sag ayrimi (kirpim koordinati)
PENC = (300, 200)                      # sablon penceresi (en, boy)
BURCLAR = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO',
           'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']


def altin(a):
    """Lacivert zeminde altin murekkep haritasi 0-1 (R-B farki)."""
    return np.clip((a[..., 0] - a[..., 2] - 25.0) / 120.0, 0, 1)


def ana_maske(g, x0, x1):
    m = g > 0.25
    m[:, :x0] = False
    m[:, x1:] = False
    lab, n = ndi.label(m)
    if not n:
        return m, 0
    alan = ndi.sum(m, lab, range(1, n + 1))
    tut = [i + 1 for i in range(n) if alan[i] >= 40]
    return np.isin(lab, tut), len(tut)


def pencere(g, m):
    ys, xs = np.where(m)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    W, H = PENC
    p = np.zeros((H, W))
    x0, y0 = int(round(cx - W / 2)), int(round(cy - H / 2))
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + W, g.shape[1]), min(y0 + H, g.shape[0])
    p[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = g[sy0:sy1, sx0:sx1]
    return p, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else 0.0


def hizala(p, T, r=4):
    """p'yi T'ye +-r px kaydirarak en iyi NCC hizasi."""
    en, iyi = -2, p
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            q = np.roll(np.roll(p, dy, 0), dx, 1)
            v = ncc(q, T)
            if v > en:
                en, iyi = v, q
    return iyi, en


def puruz(p):
    s = ndi.gaussian_filter(p, 1.5)
    bant = (s > 0.1) & (s < 0.9)
    return float(np.abs(p - ndi.gaussian_filter(p, 1.0))[bant].mean()) if bant.any() else 0.0


def main():
    kaynak, cik = Path(sys.argv[1]), Path(sys.argv[2])
    cik.mkdir(parents=True, exist_ok=True)
    dosyalar = sorted(kaynak.glob('KAPAK_*.jpg'))
    N = len(dosyalar)
    t0 = time.time()
    ornek = []                                     # (cift, taraf, burc, pencere, kutu, parca, ek_bilesen)
    kirpim = {}
    for i, f in enumerate(dosyalar, 1):
        cift = f.stem[6:]
        a, b = cift.split('_')
        im = Image.open(f).convert('RGB')
        k = im.crop(KUTU)
        kirpim[cift] = k
        g = altin(np.asarray(k).astype(np.float32))
        for taraf, burc, (x0, x1) in (('sol', a, (0, ORTA)), ('sag', b, (ORTA, g.shape[1]))):
            m, parca = ana_maske(g, x0, x1)
            if not m.any():
                ornek.append((cift, taraf, burc, None, None, 0))
                continue
            p, kt = pencere(g, m)
            ornek.append((cift, taraf, burc, p, kt, parca))
        if i % 13 == 0 or i == N:
            gc = time.time() - t0
            print(f'[{i}/{N}] okuma | gecen {gc:.0f}s | kalan ~{gc / i * (N - i):.0f}s | %{i / N * 100:.0f}', flush=True)

    # burc sablonlari (hizali medyan)
    grup = {}
    for j, o in enumerate(ornek):
        if o[3] is not None:
            grup.setdefault(o[2], []).append(j)
    hiza = {}
    sablon = {}
    for burc, js in grup.items():
        T0 = np.median([ornek[j][3] for j in js], axis=0)
        for j in js:
            hiza[j] = hizala(ornek[j][3], T0)[0]
        sablon[burc] = np.median([hiza[j] for j in js], axis=0)

    olc = []
    for j, (cift, taraf, burc, p, kt, parca) in enumerate(ornek):
        if p is None:
            olc.append(dict(cift=cift, taraf=taraf, burc=burc, kayip=1))
            continue
        diger = [hiza[k] for k in grup[burc] if k != j]
        T = np.median(diger, axis=0) if diger else sablon[burc]
        q, n_kendi = hizala(p, T)
        Td = ndi.maximum_filter(T, size=7)
        eksik = float(np.clip(T - q, 0, None)[T > 0.3].sum() / max(T[T > 0.3].sum(), 1))
        fazla = float(np.clip(q - Td, 0, None).sum() / max(T.sum(), 1))
        baska = max(((ncc(hizala(p, sablon[b2], 3)[0], sablon[b2]), b2) for b2 in sablon if b2 != burc),
                    default=(0, ''))
        olc.append(dict(cift=cift, taraf=taraf, burc=burc, kayip=0, ncc=round(n_kendi, 4),
                        en_yakin_baska=baska[1], ncc_baska=round(baska[0], 4),
                        eksik=round(eksik, 4), fazla=round(fazla, 4), parca=parca,
                        en=kt[2] - kt[0] + 1, boy=kt[3] - kt[1] + 1, puruz=round(puruz(q), 4)))

    # esikler: olculen dagilim (medyan + 6 MAD, taban) ; boyut burc medyanina gore
    def esik(ad, taban):
        v = np.array([o[ad] for o in olc if not o['kayip']])
        med, mad = np.median(v), np.median(np.abs(v - np.median(v)))
        return max(med + 6 * 1.4826 * mad, taban)
    E = {'eksik': esik('eksik', 0.05), 'fazla': esik('fazla', 0.05)}
    med_boyut = {}
    med_puruz = {}
    for burc in grup:
        oo = [o for o in olc if o['burc'] == burc and not o['kayip']]
        med_boyut[burc] = (np.median([o['en'] for o in oo]), np.median([o['boy'] for o in oo]))
        med_puruz[burc] = np.median([o['puruz'] for o in oo])
    for o in olc:
        h = []
        if o['kayip']:
            h.append('KAYIP')
        else:
            if o['ncc_baska'] > o['ncc']:
                h.append(f"YANLIS_BURC(~{o['en_yakin_baska']})")
            if o['eksik'] > E['eksik']:
                h.append('KESIK/EKSIK')
            if o['fazla'] > E['fazla']:
                h.append('KALINTI/FAZLA')
            me, mb = med_boyut[o['burc']]
            o['boyut_fark'] = f"{o['en'] - me:+.0f}/{o['boy'] - mb:+.0f}"
            if abs(o['en'] - me) > 6 or abs(o['boy'] - mb) > 6:
                h.append('BOYUT')
            o['puruz_oran'] = round(o['puruz'] / med_puruz[o['burc']], 3) if med_puruz[o['burc']] else 0
            if o['puruz_oran'] > 1.25:
                h.append('PURUZ')
        o['bulgu'] = ' '.join(h) or 'TEMIZ'

    alanlar = ['cift', 'taraf', 'burc', 'bulgu', 'ncc', 'en_yakin_baska', 'ncc_baska', 'eksik', 'fazla',
               'parca', 'en', 'boy', 'boyut_fark', 'puruz', 'puruz_oran']
    with open(cik / 'SEMBOL_QC.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar, extrasaction='ignore')
        w.writeheader()
        w.writerows(olc)

    sorunlu = sorted({o['cift'] for o in olc if o['bulgu'] != 'TEMIZ'})
    sat = [f'# Kapak kucuk sembol on kontrolu ({N} kapak)', '',
           f"Esik: eksik > {E['eksik']:.3f}, fazla > {E['fazla']:.3f} (78 kapak dagilimi medyan+6MAD), "
           'boyut > 6 px (burc medyani), puruz > 1.25x burc medyani, yanlis burc = baska sablon daha benzer.', '',
           f'Isaretli cift: {len(sorunlu)} / {N}', '']
    for o in olc:
        if o['bulgu'] != 'TEMIZ':
            sat.append(f"- {o['cift']} {o['taraf']} ({o['burc']}): {o['bulgu']} | ncc {o.get('ncc')} "
                       f"eksik {o.get('eksik')} fazla {o.get('fazla')} boyut {o.get('boyut_fark')} "
                       f"puruz {o.get('puruz_oran')}x")
    sat += ['', 'SONUC ' + ('PASS' if not sorunlu else 'FAIL')]
    (cik / 'SEMBOL_QC.md').write_text('\n'.join(sat) + '\n')

    # temas sayfasi: 3 sutun, kareler 1:1 piksel (900x210), ustte cift adi; isaretliler kirmizi cerceve
    kw, kh, et, bos = KUTU[2] - KUTU[0], KUTU[3] - KUTU[1], 44, 14
    su = 3
    sa = (N + su - 1) // su
    T = Image.new('RGB', (su * (kw + bos) + bos, sa * (kh + et + bos) + bos), (250, 248, 245))
    d = ImageDraw.Draw(T)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    except OSError:
        font = ImageFont.load_default()
    bulgu = {}
    for o in olc:
        if o['bulgu'] != 'TEMIZ':
            bulgu.setdefault(o['cift'], []).append(o['taraf'])
    for i, cift in enumerate(sorted(kirpim)):
        x = bos + (i % su) * (kw + bos)
        y = bos + (i // su) * (kh + et + bos)
        renk = (180, 20, 20) if cift in bulgu else (30, 30, 30)
        d.text((x + 4, y + 6), f"{i + 1:02d} {cift.replace('_', ' + ')}" +
               (f"  [{'/'.join(bulgu[cift])}]" if cift in bulgu else ''), fill=renk, font=font)
        T.paste(kirpim[cift], (x, y + et))
        if cift in bulgu:
            d.rectangle((x - 3, y + et - 3, x + kw + 2, y + et + kh + 2), outline=(200, 20, 20), width=3)
    T.save(cik / 'TEMAS_SAYFASI.jpg', quality=92)
    print('\n'.join(sat))
    print(f'toplam {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
