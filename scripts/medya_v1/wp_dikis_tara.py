#!/usr/bin/env python3
"""SALT OKUR dikis taramasi (Serdar 1 Eki): (1) e4f65cd WP ciktilari (3 cift x 11x14/8x10, TEMP/WP_ORNEK) siparis
dikis kapisiyla (wp_dikis_kapisi); (2) WP plate'leri (PLATES/VINTAGE_<boy>.png, 11x14 / 8x10 / 24x36) tum sayfa,
onayli WP kaynagina (POD_PRINT/<cift>/WARM_PARCHMENT/<boy>.jpg) gore. Sonuc logda; plate/kaynak salt okunur.
--kesit: 24x36 aday kesitleri yalniz TEMP/WP_ORNEK/DIKIS_24x36'ya yazilir."""
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


KESIT = (1837, 2037, 4276, 4540)          # 24x36 adayi (x 1937, y 4376-4440) cevresi, 7200x10800 baski pikseli
KESIT_HEDEF = 'gdrive:ASTROLOVE/TEMP/WP_ORNEK/DIKIS_24x36'


def kesitler(cik):
    """24x36 plate adayinin 1:1 kesiti + 3x buyutme (en yakin komsu) + 8x10/11x14 plate'te ayni goreli merkezde ayni
    boyda (300 dpi: ayni fiziksel alan) kesit + onayli 24x36 WP ayni bolge. Plate'ler baski boyuna olceklenir (taramayla
    ayni koordinat). Drive TEMP/WP_ORNEK/DIKIS_24x36'ya yazilir; plate/kaynak salt okunur."""
    from PIL import Image
    cik.mkdir(parents=True, exist_ok=True)
    x0, x1, y0, y1 = KESIT
    w, h = x1 - x0, y1 - y0
    u8 = lambda a: Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    out = []
    for boy in ('24x36', '8x10', '11x14'):
        yol = sd.W / 'plates' / f'VINTAGE_{boy}.png'
        yol.parent.mkdir(parents=True, exist_ok=True)
        if not yol.exists():
            sd.rc('copy', f'{sd.PLATES}/VINTAGE_{boy}.png', str(yol.parent), timeout=1800)
        S = wk.dizi(sd.pod_kaynak('CANCER_LIBRA', 'WARM_PARCHMENT', boy))
        H, W = S.shape[:2]
        P = wk.boyutla(wk.dizi(yol), (W, H))
        if boy == '24x36':
            a, b, c, d = x0, x1, y0, y1
        else:                                   # ayni goreli merkez, ayni piksel boyu
            cx, cy = round((x0 + x1) / 2 / 7200 * W), round((y0 + y1) / 2 / 10800 * H)
            a, b, c, d = cx - w // 2, cx + w // 2, cy - h // 2, cy + h // 2
        k = P[c:d, a:b]
        ad = f'PLATE_{boy}_x{a}-{b}_y{c}-{d}_1e1.png'
        u8(k).save(cik / ad); out.append(ad)
        if boy == '24x36':
            ad3 = f'PLATE_24x36_x{a}-{b}_y{c}-{d}_3x.png'
            u8(k).resize((w * 3, h * 3), Image.NEAREST).save(cik / ad3); out.append(ad3)
            ado = f'ONAYLI_WP_24x36_CANCER_LIBRA_x{a}-{b}_y{c}-{d}_1e1.png'
            u8(S[c:d, a:b]).save(cik / ado); out.append(ado)
            L = k @ wk.LUMA
            pr = [round(float(v), 1) for v in L[100:165].mean(0)[85:116]]   # aday satirlari (4376-4440), x 1922-1952
            print('KESIT_PROFIL 24x36 x1922-1952 y4376-4440', pr, flush=True)
        print('KESIT', boy, {'x': [a, b], 'y': [c, d], 'sayfa': [W, H]}, flush=True)
        del S, P
    sd.rc('copy', str(cik), KESIT_HEDEF, timeout=900)
    print('KESIT_DOSYALAR', out, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ciftler', default='CANCER_LIBRA,AQUARIUS_CANCER,ARIES_SCORPIO')
    ap.add_argument('--boylar', default='11x14,8x10')
    ap.add_argument('--plateler', default='11x14,8x10,24x36')
    ap.add_argument('--kesit', action='store_true', help='yalniz 24x36 aday kesitleri (Drive TEMP/WP_ORNEK/DIKIS_24x36)')
    a = ap.parse_args()
    if a.kesit:
        return kesitler(sd.W / 'kesit')
    ay = lambda t: [x for x in t.split(',') if x]
    isler = [('cikti', c, b) for c in ay(a.ciftler) for b in ay(a.boylar)] + \
            [('plate', 'CANCER_LIBRA', b) for b in ay(a.plateler)]
    for i, (tur, c, b) in enumerate(isler, 1):
        try:
            r = cikti(c, b) if tur == 'cikti' else plate(b, c)
        except BaseException as e:                                # noqa: BLE001
            r = {'tur': tur, 'cift': c, 'boy': b, 'hata': f'{type(e).__name__}: {e}'[:300]}
        print('DIKIS_TARA', tur.upper(), json.dumps(r, ensure_ascii=False, default=str), flush=True)
        eta(i, len(isler), f'{tur} {c} {b}')


if __name__ == '__main__':
    main()
