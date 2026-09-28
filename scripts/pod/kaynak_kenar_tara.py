#!/usr/bin/env python3
"""POD_PRINT kaynak dosyalarinda sembol cevresindeki koyu/noktali dis kenar taramasi (SALT OKUMA, 28 Eyl hata-kontrol).
Girdi: KOK/<CIFT>/<RENK>/11x14.jpg (3307x4200). Bolge (78 ciftte ayni yerlesim, CL kaynaklarindan olculdu):
  ANA   = ana birlesik sembol  x %27-73, y %20-54
  KUCUK = iki kucuk sembol     x %20-80, y %62.5-70.5 (isimler %72'den baslar)
Olcut (renkten bagimsiz, 'goreli'):
  murekkep = zeminden (buyuk medyan) L farki > 25; dis kenar = murekkep & ~asindir(murekkep, 2)
  ic referans = kenarin 3-6 px icindeki murekkebin yerel ortalamasi (normalize konvolusyon)
  koyu kenar pikseli: L < ic_ref - 35  (duzgun kenar yumusatmasi ic renk ile zemin arasinda kalir; hale ic renkten koyudur)
  oran = koyu kenar px / murekkep px x 1000 (binde)
Ek (yalniz bilgi): 'mutlak' = 28 Eyl ilk olcut (altin maske R-B>40, halka dilate3 & ~erode2, L<120), PW icin.
Cikti: KENAR.csv (cift, renk, bolge bazli oran), KENAR.md (siralı), TEMAS_EN_KOTU12_EN_IYI3.jpg (3x kirpim).
Kullanim: kaynak_kenar_tara.py KOK CIKIS
"""
import csv
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

RENKLER = ['PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT']
BOLGE = {'ANA': (0.27, 0.20, 0.73, 0.54), 'KUCUK': (0.20, 0.625, 0.80, 0.705)}
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def olc(a):
    """a: HxWx3 float bolge. Donus: (goreli binde, mutlak binde, murekkep px, koyu px maskesi)."""
    L = a @ LUMA
    kucuk = L[::8, ::8]
    zem = ndi.median_filter(kucuk, size=15)
    zem = np.asarray(Image.fromarray(zem.astype(np.float32)).resize((L.shape[1], L.shape[0]), Image.BILINEAR))
    ink = (zem - L) > 25
    ink = ndi.binary_opening(ink, iterations=1)
    n = int(ink.sum())
    if n < 500:
        return 0.0, 0.0, n, np.zeros_like(ink)
    kenar = ink & ~ndi.binary_erosion(ink, iterations=2)
    ic = ndi.binary_erosion(ink, iterations=3) & ~ndi.binary_erosion(ink, iterations=6)
    w = ndi.uniform_filter(ic.astype(np.float32), 9)
    s = ndi.uniform_filter(np.where(ic, L, 0).astype(np.float32), 9)
    ic_ref = np.where(w > 1e-3, s / np.maximum(w, 1e-3), np.nan)
    koyu = kenar & ~np.isnan(ic_ref) & (L < np.nan_to_num(ic_ref, nan=0) - 35)
    goreli = koyu.sum() / n * 1000
    g = (a[..., 0] - a[..., 2]) > 40
    g = ndi.binary_opening(g, iterations=1)
    ring = ndi.binary_dilation(g, iterations=3) & ~ndi.binary_erosion(g, iterations=2)
    mutlak = (ring & (L < 120)).sum() / max(g.sum(), 1) * 1000
    return round(float(goreli), 2), round(float(mutlak), 2), n, koyu


def kirp(im, bolge):
    W, H = im.size
    x0, y0, x1, y1 = bolge
    return im.crop((round(W * x0), round(H * y0), round(W * x1), round(H * y1)))


def main():
    kok, cik = Path(sys.argv[1]), Path(sys.argv[2])
    cik.mkdir(parents=True, exist_ok=True)
    isler = sorted((c.name, r) for c in kok.iterdir() if c.is_dir() for r in RENKLER
                   if (c / r / '11x14.jpg').is_file())
    N = len(isler)
    print(f'dosya: {N}', flush=True)
    t0 = time.time()
    sat = []
    for i, (c, r) in enumerate(isler, 1):
        im = Image.open(kok / c / r / '11x14.jpg').convert('RGB')
        d = {'cift': c, 'renk': r, 'boyut': f'{im.width}x{im.height}'}
        for b, kutu in BOLGE.items():
            gor, mut, n, _ = olc(np.asarray(kirp(im, kutu)).astype(np.float32))
            d[f'{b}_goreli'] = gor; d[f'{b}_mutlak'] = mut; d[f'{b}_murekkep'] = n
        d['oran'] = round(max(d['ANA_goreli'], d['KUCUK_goreli']), 2)
        sat.append(d)
        if i % 20 == 0 or i == N:
            g = time.time() - t0
            print(f'[{i}/{N}] gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s | %{i / N * 100:.0f}', flush=True)
    sat.sort(key=lambda d: -d['oran'])
    with open(cik / 'KENAR.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(sat[0].keys())); w.writeheader(); w.writerows(sat)
    md = ['# POD_PRINT kaynak koyu kenar taramasi (11x14, acik renkler)', '',
          'oran = max(ANA, KUCUK) goreli binde (koyu kenar px / murekkep px x 1000)', '',
          '| sira | cift | renk | oran | ANA | KUCUK | PW mutlak ANA/KUCUK |', '|---|---|---|---|---|---|---|']
    for k, d in enumerate(sat, 1):
        md.append(f"| {k} | {d['cift']} | {d['renk']} | {d['oran']} | {d['ANA_goreli']} | {d['KUCUK_goreli']} | "
                  f"{d['ANA_mutlak']}/{d['KUCUK_mutlak']} |")
    for r in RENKLER:
        v = np.array([d['oran'] for d in sat if d['renk'] == r])
        if len(v):
            md.insert(2, f'- {r}: n {len(v)}, medyan {np.median(v):.2f}, p90 {np.percentile(v, 90):.2f}, en cok {v.max():.2f}')
    (cik / 'KENAR.md').write_text('\n'.join(md) + '\n')

    # temas: en kotu 12 + en iyi 3; her satir ana sembol ust yayi + sol kucuk sembol, 3x (LANCZOS)
    sec = [('KOTU', d) for d in sat[:12]] + [('IYI', d) for d in sat[-3:]]
    try:
        F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    except OSError:
        F = ImageFont.load_default()
    parcalar = []
    for et, d in sec:
        im = Image.open(kok / d['cift'] / d['renk'] / '11x14.jpg').convert('RGB')
        W, H = im.size
        a = im.crop((round(W * .44), round(H * .205), round(W * .58), round(H * .275)))    # ana sembol ust yay
        k = im.crop((round(W * .28), round(H * .630), round(W * .38), round(H * .700)))    # sol kucuk sembol
        a = a.resize((a.width * 3, a.height * 3), Image.LANCZOS)
        k = k.resize((k.width * 3, k.height * 3), Image.LANCZOS)
        parcalar.append((et, d, a, k))
    rw = max(p[2].width + p[3].width for p in parcalar) + 60
    rh = max(max(p[2].height, p[3].height) for p in parcalar) + 60
    T = Image.new('RGB', (rw, rh * len(parcalar)), (128, 128, 128))
    dr = ImageDraw.Draw(T)
    for j, (et, d, a, k) in enumerate(parcalar):
        y = j * rh
        dr.text((10, y + 8), f"{et} {d['cift']} {d['renk']}  oran {d['oran']} (ANA {d['ANA_goreli']}, KUCUK {d['KUCUK_goreli']})",
                fill=(255, 255, 255) if et == 'IYI' else (255, 230, 0), font=F)
        T.paste(a, (10, y + 50)); T.paste(k, (30 + a.width, y + 50))
    T.save(cik / 'TEMAS_EN_KOTU12_EN_IYI3.jpg', quality=88)
    print('\n'.join(md[:8]))
    print(f'toplam {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
