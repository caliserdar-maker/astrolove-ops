"""D (galeri yeni altin) girdi kapisi: Drive asil galeri dosyalari -> degistir.py --is JSON'u.
Kutular Merkez pilotunun canli CL olcumu (altin_pilot.py:24-32, dal altin-pilot-kaynak c964f94a); v11 dosya adlariyla
(galeri_v11_liste.py:47-69): r03 = W03_KISISEL, r06 = W06_GENEL, r07-r09 = W07_MB / W08_DB / W09_PW, r10 = W10_WP, r11 = W01_KAPAK (CI).
r10 / r11 posterleri kahve murekkep: yalniz Canva basligi (kutu yok). r01 kapak ve video D disinda (KARARLAR_92).
KAPI (DUR = cikis 1): her dosya var ve 3000x2250 (pilot kutularinin olculdugu boyut). Bilgi: koyu kutularda koyu poster
dikdortgeninin olculen sinirlari (pilot kutusuyla fark, px). Kullanim:
  python hazirla.py --girdi DIR --cift CANCER_LIBRA --is-cikti is.json --rapor HAZIRLA.json
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image

KUTU = {
    'W03_KISISEL': [[[441, 498, 1581, 1923], 'koyu']],
    'W06_GENEL': [[[523, 497, 950, 1052], 'koyu'], [[1283, 497, 1710, 1052], 'koyu'], [[2043, 497, 2470, 1052], 'acik']],
    'W07_MB': [[[984, 680, 2023, 2031], 'koyu']],
    'W08_DB': [[[984, 680, 2023, 2031], 'koyu']],
    'W09_PW': [[[984, 680, 2023, 2031], 'acik']],
    'W10_WP': [],
    'W01_KAPAK': [],
}
BOYUT = (3000, 2250)


def koyu_sinir(im, kutu, pay=40):
    """kutu +- pay icinde satir / sutunlarin %30'undan fazlasi koyu (L < 60) olan bolgenin sinirlari"""
    x0, y0, x1, y1 = kutu
    X0, Y0 = max(0, x0 - pay), max(0, y0 - pay)
    p = np.asarray(im.crop((X0, Y0, min(im.width, x1 + pay), min(im.height, y1 + pay))).convert('L')).astype(np.float32)
    m = p < 60
    r = np.where(m.mean(1) > 0.3)[0]; c = np.where(m.mean(0) > 0.3)[0]
    if not len(r) or not len(c):
        return None
    return [int(c.min() + X0), int(r.min() + Y0), int(c.max() + 1 + X0), int(r.max() + 1 + Y0)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--girdi', required=True)
    ap.add_argument('--cift', required=True)
    ap.add_argument('--is-cikti', required=True)
    ap.add_argument('--rapor', required=True)
    a = ap.parse_args()
    IS, rap, hata = {}, {'cift': a.cift, 'dosyalar': {}}, []
    for ek, kutular in KUTU.items():
        f = f'{a.cift}_{ek}.jpg'
        yol = os.path.join(a.girdi, f)
        if not os.path.isfile(yol):
            hata.append(f'YOK {f}'); continue
        im = Image.open(yol)
        r = {'boyut': list(im.size)}
        if im.size != BOYUT:
            hata.append(f'BOYUT {f} {im.size} != {BOYUT}')
        r['koyu_sinir'] = [dict(pilot=k, olculen=(o := koyu_sinir(im, k)),
                                fark=None if o is None else [o[i] - k[i] for i in range(4)]) for k, z in kutular if z == 'koyu']
        rap['dosyalar'][f] = r
        IS[f] = kutular
    rap['hata'] = hata
    rap['durum'] = 'PASS' if not hata else 'DUR'
    json.dump(rap, open(a.rapor, 'w'), indent=1)
    json.dump(IS, open(a.is_cikti, 'w'), indent=1)
    print('HAZIRLA', rap['durum'], hata, flush=True)
    return 0 if not hata else 1


if __name__ == '__main__':
    sys.exit(main())
