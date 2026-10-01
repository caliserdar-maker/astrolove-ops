#!/usr/bin/env python3
"""SALT OKUR dikis taramasi (Serdar 1 Eki): (1) e4f65cd WP ciktilari (3 cift x 11x14/8x10, TEMP/WP_ORNEK) siparis
dikis kapisiyla (wp_dikis_kapisi); (2) WP plate'leri (PLATES/VINTAGE_<boy>.png, 11x14 / 8x10 / 24x36) tum sayfa,
onayli WP kaynagina (POD_PRINT/<cift>/WARM_PARCHMENT/<boy>.jpg) gore. Hicbir dosya yazilmaz/yuklenmez; sonuc logda."""
import argparse, json, sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import wp_dikis_kapisi as dk                                     # noqa: E402
import wp_katman as wk                                           # noqa: E402

ORNEK = 'gdrive:ASTROLOVE/TEMP/WP_ORNEK'
T0 = time.time()


def eta(i, n, ad):
    g = time.time() - T0
    print(f'[{i}/{n}] {ad} | gecen {g:.0f}s | kalan ~{g / i * (n - i):.0f}s | %{100 * i // n}', flush=True)


def seritli(A, B, satirlar, yuk=2400, ort=200):
    """Buyuk sayfa: satir seritleri (ort px ortusme), koordinatlar sayfaya cevrilir, ortusen tekrarlar atilir."""
    H = A.shape[0]; cizgi, aday = [], 0
    for y0 in range(0, H, yuk - ort):
        y1 = min(H, y0 + yuk)
        r = dk.kapi(A[y0:y1], B[y0:y1], satirlar[y0:y1])
        aday += r['aday_sayi']
        for c in r['cizgi']:
            c = dict(c)
            if c['yon'] == 'dikey':
                c['y'] = [c['y'][0] + y0, c['y'][1] + y0]
            else:
                c['y'] += y0
            if not any(d['yon'] == c['yon'] and d['tur'] == c['tur'] and abs((d['x'] if c['yon'] == 'dikey' else d['y'])
                       - (c['x'] if c['yon'] == 'dikey' else c['y'])) <= 3 for d in cizgi):
                cizgi.append(c)
        if y1 == H:
            break
    return {'cizgi': cizgi, 'aday_sayi': aday, 'gecti': not cizgi}


def cikti(cift, boy):
    d = sd.W / 'tara' / cift; d.mkdir(parents=True, exist_ok=True)
    sd.rc('copy', f'{ORNEK}/{cift}', str(d), '--include', f'WP_{cift}_{boy}_BASKI.jpg', '--include',
          f'RAPOR_{boy}.json', timeout=900)
    WP = wk.dizi(d / f'WP_{cift}_{boy}_BASKI.jpg')
    et = json.loads((d / f'RAPOR_{boy}.json').read_text()).get('bantlar')
    r = dk.siparis_kapisi(WP, cift, boy, et)
    return {'cift': cift, 'boy': boy, **r}


def plate(boy, cift):
    yol = sd.W / 'plates' / f'VINTAGE_{boy}.png'
    yol.parent.mkdir(parents=True, exist_ok=True)
    if not yol.exists():
        sd.rc('copy', f'{sd.PLATES}/VINTAGE_{boy}.png', str(yol.parent), timeout=1800)
    S = wk.dizi(sd.pod_kaynak(cift, 'WARM_PARCHMENT', boy))
    P = wk.boyutla(wk.dizi(yol), (S.shape[1], S.shape[0]))
    r = seritli(P, S, np.ones(S.shape[0], bool))
    return {'plate': f'VINTAGE_{boy}', 'px': [S.shape[1], S.shape[0]], 'onayli': f'{cift}/{boy}', **r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ciftler', default='CANCER_LIBRA,AQUARIUS_CANCER,ARIES_SCORPIO')
    ap.add_argument('--boylar', default='11x14,8x10')
    ap.add_argument('--plateler', default='11x14,8x10,24x36')
    a = ap.parse_args()
    isler = [('cikti', c, b) for c in a.ciftler.split(',') for b in a.boylar.split(',')] + \
            [('plate', 'CANCER_LIBRA', b) for b in a.plateler.split(',')]
    for i, (tur, c, b) in enumerate(isler, 1):
        try:
            r = cikti(c, b) if tur == 'cikti' else plate(b, c)
        except BaseException as e:                                # noqa: BLE001
            r = {'tur': tur, 'cift': c, 'boy': b, 'hata': f'{type(e).__name__}: {e}'[:300]}
        print('DIKIS_TARA', tur.upper(), json.dumps(r, ensure_ascii=False, default=str), flush=True)
        eta(i, len(isler), f'{tur} {c} {b}')


if __name__ == '__main__':
    main()
