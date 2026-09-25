#!/usr/bin/env python3
"""PLATE DENETIMI - SALT OKUR (Serdar acil kontrolu, 25 Eyl 2026).

Medyan plate'te 78 ciftte ORTAK olan ogeler ayakta kalir. Uc soru olculur:
  1) mesaj/slogan bandinda eski slogan ("Two Souls . One Bond") var mi?
  2) isim satirinda sonsuz (infinity) var mi?
  3) dis halka var mi?
Her biri icin x3 kirpim uretilir ve Drive'a konur. Hicbir dosya degistirilmez,
uretim yapilmaz, render kodu cagrilmaz.

Olcut: plate'in KENDI yerel kontrast maskesi (onayli `edisyon_maske` olcutu ile
ayni: buyuk yaricapli medyan zemin cikarilir). Dokulu zeminde duz esik ise
yaramaz (parsomen tum sayfayi doldurur), yerel kontrast yarar.
"""
import json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
CIK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATE_DENETIM'
W = Path('_denetim').resolve(); W.mkdir(exist_ok=True)
NORM_W = 2400
BUYUT = 3
YARICAP = 31          # yerel kontrast medyan yaricapi (2400 uzayi, onayli deger)
ESIK = 26             # yerel kontrast esigi (onayli deger)
MIN_ALAN = 40

# 2400 uzayindaki bantlar (25 Eyl olcumu)
BANT = {'30x40': {'isim': [2355, 2446], 'sembol': [2037, 2231], 'tag': [2742, 2818],
                  'halka': [1100, 1500], 'bos': [2950, 3050]},
        'A3':    {'isim': [2456, 2568], 'sembol': [2174, 2295], 'tag': [2839, 2915],
                  'halka': [1122, 1513], 'bos': [3120, 3220]}}
HEDEF = [('VINTAGE', '30x40'), ('BLUE', 'A3'), ('BLACK', 'A3'),
         ('MODERN', 'A3'), ('PURE_WHITE', 'A3'), ('VINTAGE', 'A3')]


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '180s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def maske(L):
    """Yerel kontrast murekkep maskesi (onayli edisyon_maske olcutu)."""
    import cv2
    zem = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), YARICAP).astype(np.float32)
    acik = float(np.median(L)) > 128
    m = ((zem - L) if acik else (L - zem)) > ESIK
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= MIN_ALAN
    return tut[lab]


def x3(im, kutu, ad):
    k = im.crop(kutu)
    k = k.resize((k.width * BUYUT, k.height * BUYUT), Image.LANCZOS)
    if k.width > 3600:
        k = k.resize((3600, round(k.height * 3600 / k.width)), Image.LANCZOS)
    k.save(W / ad, quality=95)
    return {'dosya': ad, 'kutu_2400': [int(v) for v in kutu], 'px': list(k.size)}


def main():
    rapor = {'tarih': datetime.now(timezone.utc).isoformat(),
             'soru': ['1 slogan', '2 sonsuz', '3 dis halka'],
             'olcut': {'yerel_kontrast_yaricap': YARICAP, 'esik': ESIK,
                       'min_alan': MIN_ALAN, 'uzay': NORM_W},
             'plateler': {}, 'hata': {}}
    for ed, boy in HEDEF:
        anahtar = f'{ed}_{boy}'
        try:
            yol = W / f'{anahtar}.png'
            if not yol.exists():
                rc('copy', f'{PLATES}/{anahtar}.png', str(W), timeout=1800)
            if not yol.exists():
                rapor['hata'][anahtar] = 'PLATES\'te yok (uretim surmus olabilir)'
                continue
            with Image.open(yol) as im0:
                tam = im0.size
                nh = round(tam[1] * NORM_W / tam[0])
                im = im0.convert('RGB').resize((NORM_W, nh), Image.LANCZOS)
            from pilot6 import LUMA
            A = np.asarray(im).astype(np.float32)
            L = A @ LUMA
            m = maske(L)
            B = BANT[boy]
            d = {'tam_px': list(tam), 'norm_px': [NORM_W, nh]}
            for ad, (y0, y1) in B.items():
                y1 = min(y1, nh)
                k = m[y0:y1]
                sut = k.sum(0)
                nz = np.nonzero(sut > 0)[0]
                d[ad] = {'y': [y0, y1], 'murekkep_orani': round(float(k.mean()), 4),
                         'murekkep_px': int(k.sum()),
                         'x_uzanim': [int(nz.min()), int(nz.max())] if len(nz) else None}
            bos = d['bos']['murekkep_orani']
            d['SORU1_slogan_var'] = bool(d['tag']['murekkep_orani'] > max(bos * 5, 0.005))
            d['SORU2_sonsuz_var'] = bool(d['isim']['murekkep_orani'] > max(bos * 5, 0.005))
            d['SORU3_halka_var'] = bool(d['halka']['murekkep_orani'] > max(bos * 5, 0.002))
            d['bos_bant_tabani'] = bos
            d['kirpimlar'] = [
                x3(im, (0, max(B['tag'][0] - 25, 0), NORM_W, min(B['tag'][1] + 25, nh)),
                   f'{anahtar}_1_SLOGAN_BANDI_x3.jpg'),
                x3(im, (0, max(B['isim'][0] - 25, 0), NORM_W, min(B['isim'][1] + 25, nh)),
                   f'{anahtar}_2_ISIM_SATIRI_x3.jpg'),
                x3(im, (int(NORM_W * 0.30), B['halka'][0], int(NORM_W * 0.70),
                        min(B['halka'][0] + 260, nh)), f'{anahtar}_3_DIS_HALKA_x3.jpg')]
            rapor['plateler'][anahtar] = d
            log(anahtar, json.dumps({k2: d[k2] for k2 in
                                     ('SORU1_slogan_var', 'SORU2_sonsuz_var',
                                      'SORU3_halka_var', 'bos_bant_tabani')}))
            yol.unlink()
        except BaseException as e:                                # noqa: BLE001
            rapor['hata'][anahtar] = f'{type(e).__name__}: {e}'
            log(anahtar, 'HATA', type(e).__name__, e)
    (W / 'PLATE_DENETIM.json').write_text(json.dumps(rapor, indent=1, ensure_ascii=False),
                                          encoding='utf-8')
    for f in list(W.glob('*.jpg')) + [W / 'PLATE_DENETIM.json']:
        rc('copy', str(f), CIK, timeout=900)
    print(json.dumps({k: {q: v[q] for q in v if q.startswith('SORU')}
                      for k, v in rapor['plateler'].items()} | {'hata': rapor['hata']},
                     indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
