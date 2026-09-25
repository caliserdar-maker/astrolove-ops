#!/usr/bin/env python3
"""MEDYAN PLATE URETIMI (Serdar onayi 25 Eyl 2026).

Her (edisyon, boy) icin 78 ciftin POD_PRINT dosyasinin PIKSEL ORTANCASI =
yazisiz temiz zemin. Cift basina degisen ogeler (sembol, glif, isim, tagline)
78 dosyada farkli yerlerde oldugu icin ortancada yok olur.

SALT OKUR girdi: POD_PRINT'e yazma yok, Etsy/Prodigi yok, render kodu cagrilmaz.
Cikti: gdrive TEMP/SIPARIS_ISIM/PLATES/<EDISYON>_<BOY>.png (tam cozunurluk, PNG)
       + PLATES/RAPOR_<parca>.json (her plate icin p50/p99).

BELLEK: 78 dosyanin tam sayfa yigini 30x40 icin 25.3 GB olur; RAM'e sigmaz.
Sayfa SATIR KAROLARINA bolunur, her karo icin dosyalar yeniden cozulur ve
ortanca o karoda alinir. Karo yuksekligi YIGIN_AZAMI_GB'ye gore secilir.
Ortanca `np.partition` ile uint8 uzerinde alinir (np.median float64'e yukseltip
bellegi ~8 katina cikarir).

PARALELLIK: `--parca i/n` is listesini boler. Her parca ayri matris isi olarak
kosar; boylece her is 45 dk sinirinin altinda kalir.
"""
import argparse, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_plate').resolve(); W.mkdir(exist_ok=True)

RENK_ED = {'MIDNIGHT_BLUE': 'blue', 'DEEP_BLACK': 'black', 'PURE_WHITE': 'pure_white',
           'CHAMPAGNE_IVORY': 'modern', 'WARM_PARCHMENT': 'vintage'}
YIGIN_AZAMI_GB = 6.0      # karo yigini icin tepe bellek butcesi
ASGARI_DOSYA = 40         # bu sayidan az dosya varsa ortanca guvenilmez
FARK_ESIK = 30            # murekkep cekirdegi (p50/p99 raporu icin)
FARK_GENIS = 12
ORNEK = 3                 # p50/p99 raporu icin kac cift


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:7.1f}s]",
          *a, flush=True)


def rc(*a, timeout=2400):
    r = subprocess.run(['rclone', '--timeout', '180s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def is_listesi():
    """POD_PRINT'i tek listede tarayip gercek (renk, boy) matrisini cikarir."""
    sayac = {}
    for satir in rc('lsf', POD, '-R', '--include', '*.jpg', '--files-only').split():
        p = satir.split('/')
        if len(p) != 3:
            continue
        _cift, renk, dosya = p
        if renk not in RENK_ED or not dosya.endswith('.jpg'):
            continue
        sayac.setdefault((renk, dosya[:-4]), 0)
        sayac[(renk, dosya[:-4])] += 1
    isler = sorted(k for k, v in sayac.items() if v >= ASGARI_DOSYA)
    return isler, {f'{r}/{b}': v for (r, b), v in sorted(sayac.items())}


def indir(renk, boy):
    hed = W / f'{renk}_{boy}'
    hed.mkdir(exist_ok=True)
    if not list(hed.glob('*.jpg')):
        rc('copy', POD, str(hed / '_ham'), '--include', f'*/{renk}/{boy}.jpg',
           '--transfers', '8')
        for src in (hed / '_ham').glob(f'*/{renk}/{boy}.jpg'):
            src.replace(hed / f'{src.parent.parent.name}.jpg')
    return sorted(hed.glob('*.jpg'))


def karo_ortanca(yollar, tam_px, satir):
    """Satir karolarinda ortanca. Her karo icin dosyalar yeniden cozulur."""
    Wd, H = tam_px
    n = len(yollar)
    k = n // 2
    plate = np.empty((H, Wd, 3), np.uint8)
    karo = max(int(YIGIN_AZAMI_GB * 1e9 / (n * Wd * 3)), 64)
    sayi = (H + karo - 1) // karo
    log(f'  karo {karo} satir x {sayi} gecis (yigin {n * karo * Wd * 3 / 1e9:.2f} GB)')
    for t, y0 in enumerate(range(0, H, karo)):
        y1 = min(y0 + karo, H)
        yig = np.empty((n, y1 - y0, Wd, 3), np.uint8)
        for i, y in enumerate(yollar):
            with Image.open(y) as im:
                # JPEG satir bazli rastgele erisim vermez; dosya cozulur ve karo
                # dilimlenir. Maliyet karo sayisi kadar cozme, kazanc bellek.
                yig[i] = np.asarray(im.convert('RGB'))[y0:y1]
        for s0 in range(0, y1 - y0, 200):
            s1 = min(s0 + 200, y1 - y0)
            p = np.partition(yig[:, s0:s1], k, axis=0)
            if n % 2:
                plate[y0 + s0:y0 + s1] = p[k]
            else:
                q = np.partition(yig[:, s0:s1], k - 1, axis=0)[k - 1]
                plate[y0 + s0:y0 + s1] = ((p[k].astype(np.uint16) + q) // 2).astype(np.uint8)
        del yig
        log(f'  karo {t + 1}/{sayi} bitti ({satir})')
    return plate


def fark_olc(a, plate):
    import cv2
    f = np.abs(a.astype(np.int16) - plate.astype(np.int16)).max(axis=2).astype(np.uint8)
    cek = (f > FARK_ESIK).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * FARK_GENIS + 1,) * 2)
    m = cv2.dilate(cek, ker) > 0
    dis = f[~m]
    if dis.size < 1000:
        return {'gecerli': False, 'murekkep_orani': round(float(m.mean()), 4)}
    return {'gecerli': True, 'murekkep_orani': round(float(m.mean()), 4),
            'p50': float(np.percentile(dis, 50)), 'p99': float(np.percentile(dis, 99)),
            'ort': round(float(dis.mean()), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parca', default='1/1', help='i/n - is listesinin i. dilimi')
    a = ap.parse_args()
    i, n = (int(x) for x in a.parca.split('/'))
    isler, sayac = is_listesi()
    benim = [x for j, x in enumerate(isler) if j % n == i - 1]
    log(f'toplam {len(isler)} plate; parca {i}/{n} -> {len(benim)}: '
        + ', '.join(f'{r}/{b}' for r, b in benim))
    rapor = {'parca': a.parca, 'tarih': datetime.now(timezone.utc).isoformat(),
             'matris': sayac, 'plateler': {}, 'hata': {}}
    for renk, boy in benim:
        anahtar = f'{renk}/{boy}'
        try:
            t0 = time.time()
            yollar = indir(renk, boy)
            boyutlar = {}
            for y in yollar:
                with Image.open(y) as im:
                    boyutlar.setdefault(im.size, []).append(y)
            tam_px = max(boyutlar, key=lambda s: len(boyutlar[s]))
            aykiri = [y.stem for s, ys in boyutlar.items() if s != tam_px for y in ys]
            yollar = sorted(boyutlar[tam_px])
            if len(yollar) < ASGARI_DOSYA:
                rapor['hata'][anahtar] = f'yalniz {len(yollar)} dosya'
                continue
            log(f'{anahtar}: {len(yollar)} dosya, {tam_px[0]}x{tam_px[1]}'
                + (f', aykiri {aykiri}' if aykiri else ''))
            plate = karo_ortanca(yollar, tam_px, anahtar)
            ed = RENK_ED[renk]
            ad = f'{ed.upper()}_{boy}.png'
            Image.fromarray(plate, 'RGB').save(W / ad, 'PNG', optimize=False,
                                               compress_level=6)
            orn = {}
            for ix in {0, len(yollar) // 2, len(yollar) - 1}:
                with Image.open(yollar[ix]) as im:
                    orn[yollar[ix].stem] = fark_olc(np.asarray(im.convert('RGB')), plate)
            rapor['plateler'][anahtar] = {
                'edisyon': ed, 'boy': boy, 'dosya': ad, 'n': len(yollar),
                'aykiri_boyut': aykiri, 'px': list(tam_px),
                'png_MB': round((W / ad).stat().st_size / 1e6, 1),
                'sure_sn': round(time.time() - t0, 1), 'ornekler': orn}
            rc('copy', str(W / ad), PLATES, timeout=2400)
            (W / ad).unlink()
            for f in (W / f'{renk}_{boy}').glob('*.jpg'):
                f.unlink()
            log(f'{anahtar} bitti {time.time() - t0:.0f}s ' + json.dumps(orn)[:300])
        except BaseException as e:                                # noqa: BLE001
            rapor['hata'][anahtar] = f'{type(e).__name__}: {e}'
            log(f'{anahtar} HATA: {type(e).__name__}: {e}')
    rp = W / f'RAPOR_{i}_{n}.json'
    rp.write_text(json.dumps(rapor, indent=1, ensure_ascii=False), encoding='utf-8')
    rc('copy', str(rp), PLATES, timeout=600)
    print(json.dumps({'parca': a.parca, 'uretilen': sorted(rapor['plateler']),
                      'hata': rapor['hata']}, indent=1))
    if rapor['hata']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
