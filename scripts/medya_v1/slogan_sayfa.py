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


def _bloklar(yol):
    """Kirpimi ONCE/SONRA bloklarina ayirir (aralarindaki beyaz etiket seridinden)."""
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    H = a.shape[0]
    # Etiket seridi TAM beyaz ve tekduze; acik zeminli edisyonlarda (Champagne
    # 209, Parchment ~205) sadece parlaklik esigi yetmez, std de gerekir.
    beyaz = np.array([(r.mean() > 250 and r.std() < 12) for r in a])
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
        return None, None
    once = a[bloklar[0][0] + 2:bloklar[0][1] - 2]
    sonra = a[bloklar[1][0] + 2:bloklar[1][1] - 2]
    n = min(once.shape[0], sonra.shape[0])
    return once[:n], sonra[:n]


def kalinti_olc(yol):
    """SONRA blogunda kalan slogan izini OLCER.

    ONEMLI (26 Eyl olcumu): maskeyi "ONCE'de koyu olan piksel" diye kurmak
    YANLIS sonuc verir - bandin icinde slogan DISI, temizlenMEmesi gereken
    ogeler de koyudur (Champagne 30x40'ta kirpimin ust/alt satirlarinda
    ONCE=SONRA=177). O maske ile olculen fark (15.2) slogan kalintisi degil,
    o ogelerin kendisidir. Dogru maske DEGISEN pikseldir: |ONCE - SONRA|.
    Kalinti = SONRA'nin o maskede yerel zeminden sapmasi; yerel zemin satir
    bazli medyandir, cunku bantta dusey gradyan var (209.5 -> 204.5).
    """
    import cv2
    once, sonra = _bloklar(yol)
    if once is None:
        return {'hata': 'blok ayrilamadi'}
    degisim = np.abs(once - sonra)
    m = cv2.dilate((degisim > 8).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if m.sum() < 200 or (~m).sum() < 200:
        return {'hata': 'temizlenen alan bulunamadi'}
    # Yerel zemin: her satirda maske DISI piksellerin medyani (gradyani izler).
    zemin = np.zeros_like(sonra)
    for y in range(sonra.shape[0]):
        d = sonra[y][~m[y]]
        zemin[y] = np.median(d) if d.size >= 20 else np.median(sonra[y])
    sap_s = np.abs(sonra - zemin)[m]
    sap_o = np.abs(once - zemin)[m]
    return {'temizlenen_oran': round(float(m.mean()), 4),
            'ONCE_sapma_ort': round(float(sap_o.mean()), 2),
            'SONRA_sapma_ort': round(float(sap_s.mean()), 2),
            'SONRA_sapma_p99': round(float(np.percentile(sap_s, 99)), 2),
            'SONRA_sapma_tepe': round(float(sap_s.max()), 2),
            'iyilesme_orani': round(float(sap_s.mean() / max(sap_o.mean(), 1e-6)), 3)}


def kontrast_ger(yol, cik, pay=18.0):
    """Kirpimi yerel zemin etrafinda +-pay seviyeye gerer: goz kalintiyi boyle gorur.

    Kontrast germeden 15-20 seviyelik bir kontur acik zeminde zor secilir;
    onay sayfasinda "gormedim" ile "yok" karismasin diye gerilmis kopya da konur.
    """
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    z = float(np.median(a[a > np.percentile(a, 20)])) if a.mean() > 128 else float(np.median(a))
    g = np.clip((a - (z - pay)) / (2 * pay) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(g).save(cik)
    return cik


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
