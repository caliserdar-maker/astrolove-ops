#!/usr/bin/env python3
"""Canva kaynakli plate'lerde slogan izi denetimi (GOREV_0015 + GOREV_0014).

ONCE/SONRA cifti burada silme adimindan degil, iki AYRI plate'ten gelir:
  ONCE  = PLATES/HAM/<ED>_<BOY>.png   (ortanca plate; slogan DURUYOR)
  SONRA = PLATES/<ED>_CANVA_<BOY>.png (Canva kopyasi; slogan katmani SILINDI)
Maske ikisinin farkidir, yani tam olarak sloganin kapladigi alan.

Olcut GOREV_0014 kurali: sapma (maske ici/disi p99) VE Sobel kenar enerjisi.
Ikisi de temiz demeden TEMIZ yazilmaz. Salt okur: Drive'a hicbir sey yazmaz.
"""
import argparse, json, subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from slogan_sayfa import KENAR_ESIK, KENAR_MUTLAK

Image.MAX_IMAGE_PIXELS = None
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_cdenetim').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
# Slogan katmaninin Canva SAYFA koordinati ve sayfa genisligi, oran basina
# (read-design ciktisindan olculdu, 26 Eyl). Modern/Vintage 4/5 ve A'da
# yerlesim Blue/Black'ten farkli oldugu icin edisyon istisnasi var.
ORAN = {'30x40': '3_4', '24x32': '3_4', '18x24': '3_4', '12x16': '3_4',
        '24x30': '4_5', '16x20': '4_5', '8x10': '4_5',
        '24x36': '2_3', '20x30': '2_3', '16x24': '2_3', '12x18': '2_3',
        '11x14': '11_14', 'A1': 'A', 'A2': 'A', 'A3': 'A', 'A4': 'A'}
KUTU = {'3_4': ((1035, 3427, 1965, 3523), 3000),
        '4_5': ((1419.84, 4280.58, 2580.16, 4400.0), 4000),
        '2_3': ((1343.50, 5014.87, 2656.50, 5150.0), 4000),
        '11_14': ((1161.75, 3598.50, 2138.25, 3699.0), 3300),
        'A': ((1210.26, 4149.31, 2297.74, 4261.23), 3508)}
KUTU_ISTISNA = {('MODERN', '4_5'): ((1418.75, 4283.93, 2581.25, 4403.57), 4000),
                ('VINTAGE', '4_5'): ((1418.75, 4283.93, 2581.25, 4403.57), 4000),
                ('MODERN', 'A'): ((1189.11, 4214.23, 2318.89, 4330.50), 3508),
                ('VINTAGE', 'A'): ((1189.11, 4214.23, 2318.89, 4330.50), 3508),
                ('MODERN', '11_14'): ((1161.44, 3599.44, 2138.56, 3700.0), 3300),
                ('VINTAGE', '11_14'): ((1161.44, 3599.44, 2138.56, 3700.0), 3300)}
PAY_3000 = 60          # bandin disindan referans doku icin pay (3000 genislik olcegi)
SAPMA_ESIK = 4.0       # ic_p99 - dis_p99 (kalinti_olc2 ile ayni esik)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def serit(yol, kutu, sayfa_en):
    """Plate'ten slogan bandini (payli) gri olarak keser."""
    with Image.open(yol) as im:
        k = im.width / float(sayfa_en)
        x0, y0, x1, y1 = kutu
        p = PAY_3000 * sayfa_en / 3000.0 * k
        kutu = (max(int(x0 * k - p), 0), max(int(y0 * k - p), 0),
                min(int(x1 * k + p), im.width), min(int(y1 * k + p), im.height))
        return np.asarray(im.crop(kutu).convert('L')).astype(np.float32)


def maske(once, sonra):
    m = cv2.dilate((np.abs(once - sonra) > 10).astype(np.uint8),
                   np.ones((5, 5), np.uint8)) > 0
    return m


def sapma_olc(once, sonra, m):
    """Maske ICI p99 - DISI p99; zemin dokuyu izleyen medyan (yaricap 41)."""
    z = cv2.medianBlur(np.clip(sonra, 0, 255).astype(np.uint8), 41).astype(np.float32)
    ic, dis = np.abs(sonra - z)[m], np.abs(sonra - z)[~m]
    o_ic = np.abs(once - z)[m]
    ic99, dis99 = float(np.percentile(ic, 99)), float(np.percentile(dis, 99))
    d = {'ONCE_ic_ort': round(float(o_ic.mean()), 2),
         'SONRA_ic_ort': round(float(ic.mean()), 2),
         'ic_p99': round(ic99, 1), 'dis_p99': round(dis99, 1),
         'FARK': round(ic99 - dis99, 1)}
    d['sonuc'] = ('olculemedi (zemin dokusu cok guclu)' if dis99 > 40
                  else 'TEMIZ' if d['FARK'] <= SAPMA_ESIK else 'IZ VAR')
    return d


def kenar_olc(once, sonra, m):
    def enerji(a):
        gx = cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3)
        return np.abs(gx) + np.abs(gy)
    e_s, e_o = enerji(sonra), enerji(once)
    ic, dis = float(e_s[m].mean()), float(e_s[~m].mean())
    o_ic = float(e_o[m].mean())
    duz = dis < 1.0
    oran = ic / max(dis, 1e-6)
    d = {'SONRA_ic_kenar': round(ic, 2), 'SONRA_dis_kenar': round(dis, 2),
         'ONCE_ic_kenar': round(o_ic, 2), 'oran': round(oran, 3),
         'SONRA/ONCE': round(ic / max(o_ic, 1e-6), 3),
         'zemin': 'duz' if duz else 'dokulu'}
    d['sonuc'] = ('TEMIZ' if ic <= dis + KENAR_MUTLAK else 'IZ VAR') if duz else \
                 ('TEMIZ' if oran <= KENAR_ESIK else 'IZ VAR')
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boy', default='30x40', help='virgulle; "hepsi" = tum satilan boylar')
    ap.add_argument('--edisyon', default='')
    a = ap.parse_args()
    eds = [e for e in EDISYONLAR if not a.edisyon or e in a.edisyon.split(',')]
    boylar = list(ORAN) if a.boy == 'hepsi' else a.boy.split(',')
    rapor, say = {}, {'TEMIZ': 0, 'IZ/OLCULEMEDI': 0, 'hata': 0}
    for ed in eds:
        for boy in boylar:
            anahtar = f'{ed}_{boy}'
            try:
                oran = ORAN[boy]
                kutu, sayfa_en = KUTU_ISTISNA.get((ed, oran), KUTU[oran])
                ham, yeni = W / f'HAM_{anahtar}.png', W / f'CANVA_{anahtar}.png'
                try:
                    rc('copyto', f'{PLATES}/HAM/{ed}_{boy}.png', str(ham))
                except RuntimeError:
                    # HAM yalniz POD_PRINT boylarini tutar; turev boyda once
                    # (slogan duran) plate yok -> maske kurulamaz.
                    rapor[anahtar] = {'hata': 'HAM plate yok (turev boy)'}
                    say['hata'] += 1
                    continue
                rc('copyto', f'{PLATES}/{ed}_CANVA_{boy}.png', str(yeni))
                once, sonra = serit(ham, kutu, sayfa_en), serit(yeni, kutu, sayfa_en)
                ham.unlink(missing_ok=True); yeni.unlink(missing_ok=True)
                if once.shape != sonra.shape:
                    rapor[anahtar] = {'hata': f'serit olcusu farkli {once.shape} {sonra.shape}'}
                    say['hata'] += 1
                    continue
                m = maske(once, sonra)
                if m.sum() < 200 or (~m).sum() < 200:
                    rapor[anahtar] = {'hata': f'maske kucuk ({int(m.sum())} px)'}
                    say['hata'] += 1
                    continue
                s, k = sapma_olc(once, sonra, m), kenar_olc(once, sonra, m)
                temiz = s['sonuc'] == 'TEMIZ' and k['sonuc'] == 'TEMIZ'
                say['TEMIZ' if temiz else 'IZ/OLCULEMEDI'] += 1
                rapor[anahtar] = {'maske_px': int(m.sum()), 'sapma': s, 'kenar': k,
                                  'SONUC': 'TEMIZ' if temiz else f"{s['sonuc']} / {k['sonuc']}"}
            except BaseException as e:                                # noqa: BLE001
                rapor[anahtar] = {'hata': f'{type(e).__name__}: {e}'}
                say['hata'] += 1
    # Ozet once: uzun JSON log kuyrugunda kesiliyor (plate_ozet dersi).
    for anahtar, d in rapor.items():
        print(f"{anahtar:24s} {d.get('SONUC') or d.get('hata')}"
              + (f"  sapma FARK {d['sapma']['FARK']}  kenar oran {d['kenar']['oran']}"
                 if 'sapma' in d else ''))
    print('OZET', json.dumps(say))
    Path('out').mkdir(exist_ok=True)
    Path('out/canva_denetim.json').write_text(json.dumps(rapor, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
