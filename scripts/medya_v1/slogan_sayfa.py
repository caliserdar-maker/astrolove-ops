#!/usr/bin/env python3
"""Slogan temizligi ONAY SAYFASI (Serdar 2. madde, 25 Eyl 2026).

PLATES/SLOGAN_KIRPIM altindaki once/sonra x3 kirpimlarini TEK SAYFADA toplar:
5 edisyon x istenen boylar. Serdar onaylamadan plate'ler uretimde kullanilmaz.
SALT OKUR: yalniz kirpimlari indirir, birlestirir, Drive'a tek dosya yazar.
"""
import argparse, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KIRPIM = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES/SLOGAN_KIRPIM'
CIK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_sayfa').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
GENISLIK = 2200


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def kalinti_olc(yol):
    """Kirpimdaki ONCE/SONRA bloklarini ayirip kalan slogan izini OLCER.

    Kirpim: ustte ONCE, altta SONRA; aralarinda beyaz etiket seritleri var.
    ONCE'deki slogan maskesi cikarilir, ayni maske SONRA'da olculur. Boylece
    "slogan ne kadar kaldi" gozle degil SAYIYLA gorulur.
    """
    import cv2
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    H = a.shape[0]
    beyaz = a.mean(1) > 200
    gruplar, cur = [], None
    for y, v in enumerate(beyaz):
        if v:
            cur = [y, y + 1] if cur is None else [cur[0], y + 1]
        elif cur is not None:
            gruplar.append(cur); cur = None
    if cur:
        gruplar.append(cur)
    bloklar, prev = [], 0
    for g in gruplar:
        if g[0] - prev > 40:
            bloklar.append([prev, g[0]])
        prev = g[1]
    if H - prev > 40:
        bloklar.append([prev, H])
    if len(bloklar) < 2:
        return {'hata': f'blok ayrilamadi ({len(bloklar)})'}
    once = a[bloklar[0][0] + 2:bloklar[0][1] - 2]
    sonra = a[bloklar[1][0] + 2:bloklar[1][1] - 2]
    n = min(once.shape[0], sonra.shape[0])
    once, sonra = once[:n], sonra[:n]
    z = float(np.median(once))
    acik = z > 128
    m = (once < z - 25) if acik else (once > z + 25)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if m.sum() < 200 or (~m).sum() < 200:
        return {'hata': 'slogan maskesi kucuk'}
    ic, dis = sonra[m], sonra[~m]
    lf = cv2.GaussianBlur(sonra, (0, 0), 9)
    return {'slogan_orani_ONCE': round(float(m.mean()), 4),
            'SONRA_glif_ort': round(float(ic.mean()), 3),
            'SONRA_disi_ort': round(float(dis.mean()), 3),
            'FARK_seviye': round(abs(float(ic.mean()) - float(dis.mean())), 3),
            'dusuk_frekans_farki': round(abs(float(lf[m].mean()) - float(lf[~m].mean())), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boylar', default='30x40,A3')
    a = ap.parse_args()
    boylar = [x.strip() for x in a.boylar.split(',') if x.strip()]
    rc('copy', KIRPIM, str(W), '--include', '*.jpg')
    satirlar, eksik, olcumler = [], [], {}
    for boy in boylar:
        for ed in EDISYONLAR:
            f = W / f'SLOGAN_{ed}_{boy}_x3.jpg'
            if f.exists():
                o = kalinti_olc(f)
                olcumler[f'{ed}_{boy}'] = o
                et = (f'{ed}  {boy}   |  slogan %{o["slogan_orani_ONCE"] * 100:.2f}'
                      f'  ->  kalinti {o["FARK_seviye"]} seviye (255 uzerinden)'
                      f',  dusuk frekans {o["dusuk_frekans_farki"]}'
                      if 'hata' not in o else f'{ed}  {boy}   |  OLCULEMEDI: {o["hata"]}')
                satirlar.append((et, Image.open(f).convert('RGB')))
            else:
                eksik.append(f'{ed}_{boy}')
    if not satirlar:
        raise SystemExit(f'hic kirpim yok (eksik: {eksik})')
    parcalar = []
    for ad, im in satirlar:
        if im.width != GENISLIK:
            im = im.resize((GENISLIK, round(im.height * GENISLIK / im.width)), Image.LANCZOS)
        parcalar.append((ad, im))
    bas = 86
    yuk = bas + sum(i.height + 38 for _, i in parcalar) + 20
    t = Image.new('RGB', (GENISLIK + 40, yuk), 'white')
    d = ImageDraw.Draw(t)
    d.text((20, 16), 'SLOGAN TEMIZLIGI - ONAY SAYFASI  (her blokta ustte ONCE, altta SONRA, x3)',
           fill='black')
    d.text((20, 50), 'KALINTI = eski slogan pikselleri ile bandin geri kalani arasindaki '
                     'ortalama fark (0-255). Kucuk = temiz.', fill='black')
    d.text((20, 36), f'{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")} UTC'
                     + (f'   EKSIK: {", ".join(eksik)}' if eksik else ''), fill='black')
    y = bas
    for ad, im in parcalar:
        d.text((20, y), ad, fill='black')
        t.paste(im, (20, y + 16)); y += im.height + 38
    ad = 'SLOGAN_ONAY_SAYFASI.jpg'
    t.save(W / ad, quality=94)
    rc('copy', str(W / ad), CIK, timeout=900)
    import json
    print(json.dumps({'dosya': ad, 'px': list(t.size), 'blok': len(parcalar),
                      'eksik': eksik, 'olcumler': olcumler}, indent=1))


if __name__ == '__main__':
    main()
