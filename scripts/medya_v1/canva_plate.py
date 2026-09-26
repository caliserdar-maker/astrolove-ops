#!/usr/bin/env python3
"""Canva kaynagindan plate (GOREV_0015).

Canva'da posterin orijinal katmanlari duruyor; slogan ve cifte ozel ogeler
AYRI KATMAN. Kopyada bunlar silinip disa aktarilinca temiz zemin dogrudan
cikiyor - 6 iterasyondur piksel duzeyinde silmeye calistigimiz sey kaynakta
cozuluyor.

Bu script yalnizca disa aktarilmis PNG'yi alir, MEVCUT plate ile karsilastirir
(slogan bandi disinda fark ~0 olmali - ayni kaynak) ve PLATES'e YENI adla
yukler. Eski plate'lere DOKUNMAZ.

Export URL'leri imzali ve gecici oldugu icin Drive'daki bir JSON'dan okunur:
  TEMP/SIPARIS_ISIM/CANVA_EXPORT.json = {"<ad>": {"url": ..., "kiyas": ...}}
"""
import argparse, json, subprocess, urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
KOK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM'
PLATES = f'{KOK}/PLATES'
W = Path('_canva').resolve(); W.mkdir(exist_ok=True)
# Canva sayfasi 3000x4000; slogan katmani top 3427, left 1035, 930x95.7.
# Orana gore olceklenir (plate genisligi / 3000).
SLOGAN_KUTU_3000 = (1035, 3427, 1035 + 930, 3427 + 96)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def indir(url, hedef):
    with urllib.request.urlopen(url, timeout=600) as r, open(hedef, 'wb') as f:
        while True:
            p = r.read(1 << 20)
            if not p:
                break
            f.write(p)
    return hedef


def uzak_px(yol):
    """PLATES'teki PNG'nin px olcusu - 33 bayt basliktan (dosyayi indirmeden)."""
    ham = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3',
                          'cat', '--count', '33', f'{PLATES}/{yol}'],
                         capture_output=True, timeout=300)
    if ham.returncode or len(ham.stdout) < 33 or ham.stdout[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError(f'PNG basligi okunamadi: {yol}')
    en = int.from_bytes(ham.stdout[16:20], 'big')
    boy = int.from_bytes(ham.stdout[20:24], 'big')
    return en, boy


def odaklar(d, disi, k, esik=40, en_az=200):
    """Bant disindaki buyuk farkin NEREDE oldugu: Canva sayfa koordinatinda kutular.

    Ortanca plate'te sabit ogeler (sonsuz, glif yuvasi) kalir; Canva kopyasinda
    silindigi icin fark ORADA birikir. 'Tepe yuksek ama onemsiz' demek yerine
    kutusu olculur.
    """
    m = ((d > esik) & disi).astype(np.uint8)
    kucuk = cv2.resize(m, (m.shape[1] // 8, m.shape[0] // 8),
                       interpolation=cv2.INTER_AREA)
    kucuk = (kucuk > 0).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(kucuk, 8)
    kutu = []
    for i in range(1, n):
        x, y, w, h, alan = st[i]
        if alan * 64 < en_az:
            continue
        kutu.append({'kutu_sayfa': [round(x * 8 / k), round(y * 8 / k),
                                  round((x + w) * 8 / k), round((y + h) * 8 / k)],
                     'px': int(alan * 64)})
    kutu.sort(key=lambda z: -z['px'])
    return kutu[:6]


def kiyas(yeni, eski, kutu=SLOGAN_KUTU_3000, sayfa_en=3000.0):
    """Slogan bandi DISINDA fark ~0 mi? (ayni kaynak, ayni olcek beklenir)

    kutu: slogan katmaninin Canva SAYFA koordinati (read-design ciktisi);
    sayfa_en: o sayfanin genisligi. Oran basina farkli oldugu icin girdi.
    """
    a = np.asarray(Image.open(yeni).convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(eski).convert('RGB')).astype(np.float32)
    if a.shape != b.shape:
        return {'hata': f'boyut farkli: yeni {a.shape[:2]} eski {b.shape[:2]}'}
    k = a.shape[1] / float(sayfa_en)
    x0, y0, x1, y1 = (int(round(v * k)) for v in kutu)
    pay = int(round(60 * sayfa_en / 3000.0 * k))
    m = np.ones(a.shape[:2], bool)
    m[max(y0 - pay, 0):y1 + pay, max(x0 - pay, 0):x1 + pay] = False   # bant DISI
    d = np.abs(a - b).max(axis=2)
    dis, ic = d[m], d[~m]
    return {'bant_DISI': {'ort': round(float(dis.mean()), 3),
                          'p99': round(float(np.percentile(dis, 99)), 1),
                          'tepe': round(float(dis.max()), 1),
                          'odak': odaklar(d, m, k)},
            'bant_ICI': {'ort': round(float(ic.mean()), 2),
                         'p99': round(float(np.percentile(ic, 99)), 1)},
            'px': list(a.shape[:2])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--liste', default='CANVA_EXPORT.json')
    ap.add_argument('--yukle', action='store_true', help='PLATES\'e yeni adla yukle')
    a = ap.parse_args()
    # tek dosya: copyto (copy kaynagi DIZIN sanip 'directory not found' veriyor)
    rc('copyto', f'{PLATES}/{a.liste}', str(W / a.liste))
    isler = json.loads((W / a.liste).read_text())
    rapor = {}
    for ad, d in isler.items():
        try:
            f = indir(d['url'], W / f'{ad}.ham')
            r = {'MB': round(f.stat().st_size / 1e6, 1)}
            # Canva 9000x12000 PNG'yi agir dokulu sayfalarda zaman asimina
            # ugratiyor; o durumda JPG q100 alinip burada PNG'ye cevriliyor.
            with Image.open(f) as im:
                r['kaynak_bicim'] = im.format
                png = W / f'{ad}.png'
                if im.format == 'PNG':
                    f.rename(png)
                else:
                    im.convert('RGB').save(png, 'PNG', optimize=False)
                    f.unlink(missing_ok=True)
            f = png
            if d.get('kiyas'):
                rc('copyto', f'{PLATES}/{d["kiyas"]}', str(W / d['kiyas']))
                r['kiyas'] = kiyas(f, W / d['kiyas'])
                (W / d['kiyas']).unlink(missing_ok=True)
            if d.get('boylar'):
                # Ayni orandaki her satilan boy TEK export'tan yeniden
                # orneklenir (plate hattinin TUREV mantigi). Hedef px, mevcut
                # plate'in PNG basligindan okunur - tahmin yok.
                r['boylar'] = {}
                with Image.open(f) as im:
                    kaynak = im.convert('RGB')
                    kaynak.load()
                for boy, ref in d['boylar'].items():
                    try:
                        if ref.startswith('px:'):
                            # Karsilastirilacak eski plate yok (turev boy / HAM'da yok):
                            # hedef px elle verilir, kiyas yapilmaz.
                            en, yuk = (int(v) for v in ref[3:].split('x'))
                        else:
                            en, yuk = uzak_px(ref)
                        cik = W / f'{d["ad"]}_{boy}.png'
                        (kaynak if (en, yuk) == kaynak.size
                         else kaynak.resize((en, yuk), Image.LANCZOS)).save(cik, 'PNG')
                        kv = {}
                        if d.get('kutu') and not ref.startswith('px:'):
                            rf = W / Path(ref).name
                            rc('copyto', f'{PLATES}/{ref}', str(rf))
                            kv = kiyas(cik, rf, d['kutu'], d.get('sayfa_en', 3000.0))
                            rf.unlink(missing_ok=True)
                        if a.yukle:
                            rc('copyto', str(cik), f'{PLATES}/{d["ad"]}_{boy}.png')
                        r['boylar'][boy] = {'px': [en, yuk], 'MB': round(cik.stat().st_size / 1e6, 1),
                                            'ref': ref, 'kiyas': kv, 'yuklendi': a.yukle}
                        cik.unlink(missing_ok=True)
                    except BaseException as e:                        # noqa: BLE001
                        r['boylar'][boy] = {'hata': f'{type(e).__name__}: {e}'}
                kaynak.close()
            elif a.yukle:
                rc('copyto', str(f), f'{PLATES}/{ad}.png')
                r['yuklendi'] = f'{ad}.png'
            f.unlink(missing_ok=True)
            rapor[ad] = r
        except BaseException as e:                                # noqa: BLE001
            rapor[ad] = {'hata': f'{type(e).__name__}: {e}'}
    print(json.dumps(rapor, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
