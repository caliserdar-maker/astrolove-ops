#!/usr/bin/env python3
"""PLATE ISIM BANDI LEKE OLCUMU (GIFT_9518 bulgusu, 29 Eyl 2026). SALT OKUR: PLATES'e yazma yok.

Bulgu: medyan plate'lerin isim bandi temizlenmemis (plate temizligi yalniz slogan bandini
kapsiyordu); eski burc yazilarinin uclari plate'te kaliyor (BLUE_11x14: 164,126,32 altin).
Olcum, 5 renk x 13 boy PLATES/<ED>_<boy>.png icin:
  isim bandi satirlari = CANCER_LIBRA POD dosyasinin (dosya - plate) olcumu (siparis hatti ile ayni),
  bant +- %25 (sembol / tagline bandina tasmadan), sutun %5-%95;
  leke = yerel medyan zemine gore |L - zemin| > siparis_dosyasi.ISIM_KALINTI_ESIK ve altin (R-B > 20),
  bilesen >= 2 px. Plate'te isim bandinda HIC altin olmamali (isimler siparise gore cizilir).
Cikti: <kok>/PLATE_ISIM_LEKE.md + .json (plate basina bilesen sayisi, toplam alan, en buyuk 5).
"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
BOYLAR = ('8x10', '11x14', '12x16', '12x18', '16x20', '16x24', '18x24', '20x30', '24x36',
          '30x40', 'A4', 'A3', 'A2')
RENKLER = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT')
KISA = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'PURE_WHITE': 'PW',
        'CHAMPAGNE_IVORY': 'CI', 'WARM_PARCHMENT': 'WP'}
KAYNAK_CIFT = 'CANCER_LIBRA'


def leke_olc(plate_yol, olcum):
    import cv2
    B = np.asarray(Image.open(plate_yol).convert('RGB')).astype(np.float32)
    H, Wd = B.shape[:2]
    k = Wd / 2400.0
    r0, r1 = sd._isim_satirlari(olcum, k, H)
    c0, c1 = int(Wd * 0.05), int(Wd * 0.95)
    Bb = B[r0:r1, c0:c1]
    L = Bb @ np.array([0.299, 0.587, 0.114], np.float32)
    m = (np.abs(L - sd._yerel_zemin(L, k)) > sd.ISIM_KALINTI_ESIK) & ((Bb[..., 0] - Bb[..., 2]) > 20)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    parca = [{'x_2400': round(float((st[i][0] + c0) / k), 1), 'y_2400': round(float((st[i][1] + r0) / k), 1),
              'alan': int(st[i][4])} for i in range(1, n) if st[i][4] >= 2]
    parca.sort(key=lambda z: -z['alan'])
    return {'satir': [r0, r1], 'sutun': [c0, c1], 'bilesen': len(parca),
            'toplam_alan': int(sum(z['alan'] for z in parca)), 'en_buyuk': parca[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed = sd.EdisyonPoster()
    liste = {x['Name'] for x in json.loads(sd.rc('lsjson', sd.PLATES, '--files-only'))}
    d = sd.W / '_plate_isim'; d.mkdir(parents=True, exist_ok=True)
    sonuc, n, T0 = {}, 0, time.time()
    toplam = len(RENKLER) * len(BOYLAR)
    for renk in RENKLER:
        ed = sd.RENK_ED[renk]
        for boy in BOYLAR:
            n += 1
            ad = f'{ed.upper()}_{boy}.png'
            r = {'plate': ad}
            if ad not in liste:
                r['durum'] = 'YOK'
            else:
                try:
                    sd.rc('copy', f'{sd.PLATES}/{ad}', str(d), timeout=1800)
                    kaynak = sd.pod_kaynak(KAYNAK_CIFT, renk, boy)
                    o, _duz, _m = P_ed.olc(kaynak, d / ad)
                    r.update(leke_olc(d / ad, o))
                    r['durum'] = 'LEKELI' if r['bilesen'] else 'TEMIZ'
                    kaynak.unlink(missing_ok=True)
                except BaseException as e:                        # noqa: BLE001
                    r['durum'] = 'OLCULEMEDI'
                    r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
                (d / ad).unlink(missing_ok=True)
            sonuc[f'{renk}/{boy}'] = r
            g = time.time() - T0
            print(f"[{n}/{toplam}] {renk} {boy}: {r['durum']} bilesen={r.get('bilesen')} "
                  f"alan={r.get('toplam_alan')} | gecen {g:.0f}s | kalan ~{g / n * (toplam - n):.0f}s | "
                  f"%{100 * n // toplam}", flush=True)
    satir = ['# PLATE ISIM BANDI LEKESI (29 Eyl 2026, salt okur)', '',
             f'Olcut: isim bandinda yerel zemine gore altin murekkep (|L - medyan| > '
             f'{sd.ISIM_KALINTI_ESIK}, R-B > 20, >= 2 px). Hucre: bilesen sayisi / toplam alan (px).', '',
             '| renk | ' + ' | '.join(BOYLAR) + ' |', '|---|' + '---|' * len(BOYLAR)]
    for renk in RENKLER:
        h = []
        for boy in BOYLAR:
            r = sonuc[f'{renk}/{boy}']
            h.append(f"{r['durum']} {r['bilesen']}/{r['toplam_alan']}" if 'bilesen' in r else r['durum'])
        satir.append(f'| {KISA[renk]} | ' + ' | '.join(h) + ' |')
    oz = {}
    for key, r in sonuc.items():
        oz.setdefault(r['durum'], []).append(key)
    satir += ['', '## Ozet', ''] + [f'- **{k}** ({len(v)}): ' + ', '.join(v) for k, v in sorted(oz.items())]
    (d / 'PLATE_ISIM_LEKE.md').write_text('\n'.join(satir) + '\n')
    (d / 'PLATE_ISIM_LEKE.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(d), a.kok, '--include', 'PLATE_ISIM_LEKE.*')
    print('\n'.join(satir))


if __name__ == '__main__':
    main()
