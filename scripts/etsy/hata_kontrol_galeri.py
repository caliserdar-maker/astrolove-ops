#!/usr/bin/env python3
"""HATA KONTROL 28 Eyl (SALT OKUMA; Etsy'ye yazma YOK, yalniz API anahtari ile GET).

1 GALERI : 04_77_CIFT_LINK_DIZINI.csv'deki her ilanin canli galerisi (sira, gorsel id, alt metin, 570 px kucuk
           gorsel). Her gorsel iki referans kumesine benzerlikle siniflanir:
             ESKI = pano/codex/veri/kart_seti_20260924 (24 Eyl paketi: 01 kapak .. 11 teslim)
             YENI = data/pod/cl_galeri_final19 (27-28 Eyl onayli 19'lu set)
           Benzerlik: 64x48 gri kucultme NCC. Sinif = en yakin kume (esik alti -> BILINMIYOR).
2 ALT    : E08 kontrolu - alt metinde 'mockup' / 'framed room' / 'room' + 'frame' gibi yanlis tanim aranir.
3 ESLEME : 04 dosyasindaki cift -> ilan no, canli baslik ('{A} and {B} Personalized ...') ile karsilastirilir.
4 KLASOR : 04 dosyasindaki 77 x 5 renk kaynak klasoru rclone ile listelenebiliyor mu (dosya sayisi).
Cikti (<out>): GALERI.csv, ALT_METIN.csv, ESLEME.csv, KLASOR.csv, GALERI_TEMAS.jpg, OZET.md
Kullanim: hata_kontrol_galeri.py 04.csv OUT [--klasor-atla]
"""
import argparse
import csv
import io
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
ESKI = KOK / 'pano/codex/veri/kart_seti_20260924'
YENI = KOK / 'data/pod/cl_galeri_final19'
KOTA_TABAN = 1500
ALT_YASAK = [r'mock-?up', r'framed room', r'room mock', r'frame mock', r'on a warm stone', r'stone-gray wall']
RENKLER = ['MB', 'DB', 'WP', 'CI', 'PW']


def oz(im):
    g = np.asarray(im.convert('L').resize((64, 48), Image.BILINEAR)).astype(np.float32)
    g = g - g.mean()
    return g / (np.linalg.norm(g) + 1e-6)


def referanslar():
    R = []
    for kume, d in (('ESKI', ESKI), ('YENI', YENI)):
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in ('.jpg', '.png'):
                with Image.open(p) as im:
                    R.append((kume, p.stem, oz(im), im.width / im.height))
    return R


def sinifla(im, R):
    f, oran = oz(im), im.width / im.height
    skor = sorted(((float((f * r).sum()), k, ad) for k, ad, r, ro in R if abs(ro - oran) < 0.08), reverse=True)
    if not skor:
        return 'BILINMIYOR', '', 0.0, '', 0.0
    s, k, ad = skor[0]
    s2 = next((x for x in skor if x[1] != k), (0.0, '', ''))
    # olculen (referanslar arasi): ayni kart baska ciftte ~0.99; farkli kartlar arasi en cok 0.98 (eski 06/10 ayni
    # iskelet), eski/yeni arasi en cok 0.83 -> esik 0.90 + diger kumeye en az 0.05 fark
    return (k if s >= 0.90 and s - s2[0] >= 0.05 else 'BILINMIYOR'), ad, round(s, 3), s2[2], round(s2[0], 3)


def cift_basliktan(baslik):
    m = re.match(r'\s*([A-Za-z]+)\s+and\s+([A-Za-z]+)\b', baslik or '')
    return (m.group(1).upper(), m.group(2).upper()) if m else None


def klasor_id(url):
    m = re.search(r'/folders/([A-Za-z0-9_-]+)', url or '')
    return m.group(1) if m else ''


def klasor_say(fid):
    r = subprocess.run(['rclone', 'lsf', 'gdrive:', '--drive-root-folder-id', fid, '--max-depth', '1',
                        '--timeout', '60s', '--retries', '2'], capture_output=True, text=True, timeout=300)
    if r.returncode:
        return 'ERISILEMEZ', 0, r.stderr.strip().splitlines()[-1][:160] if r.stderr.strip() else ''
    satir = [x for x in r.stdout.splitlines() if x.strip()]
    return ('BOS' if not satir else 'ACIK'), len(satir), ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv04'); ap.add_argument('out')
    ap.add_argument('--klasor-atla', action='store_true')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satirlar = list(csv.DictReader(open(a.csv04, encoding='utf-8-sig')))
    N = len(satirlar)
    api = Etsy(APIKeyStore(os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')))
    R = referanslar()
    repo_ids = {r['cift']: r['listing_id'] for r in csv.DictReader(open(KOK / 'data/pod/pod78_ids.csv'))}
    print(f'cift {N} | referans {len(R)}', flush=True)

    gal, esl, altm, kls = [], [], [], []
    serit = []
    t0 = time.time()
    for i, s in enumerate(satirlar, 1):
        cift, lid = s['pair'].strip(), s['existing_etsy_listing_id'].strip()
        L = api.get(f'/listings/{lid}', ok404=True) or {}
        durum = L.get('state') or ('YOK/404' if not L else '?')
        baslik = L.get('title') or ''
        cb = cift_basliktan(baslik)
        beklenen = tuple(cift.split('_'))
        esl.append(dict(cift=cift, ilan=lid, state=durum, baslik=baslik[:90],
                        baslik_cift='_'.join(cb) if cb else '', pod78_ids_ilan=repo_ids.get(cift, 'YOK'),
                        uyum='UYUMLU' if cb and sorted(cb) == sorted(beklenen) and repo_ids.get(cift) == lid
                        else 'UYUMSUZ'))
        imgs = sorted((api.get(f'/listings/{lid}/images', ok404=True) or {}).get('results') or [],
                      key=lambda x: x.get('rank') or 0)
        kucuk = []
        for im in imgs:
            u = im.get('url_570xN') or im.get('url_fullxfull')
            try:
                b = requests.get(u, timeout=60).content
                I = Image.open(io.BytesIO(b)).convert('RGB')
            except Exception as e:                                   # noqa: BLE001
                gal.append(dict(cift=cift, ilan=lid, sira=im.get('rank'), gorsel_id=im.get('listing_image_id'),
                                sinif='INDIRILEMEDI', en_yakin=str(e)[:60]))
                continue
            k, ad, sk, ad2, sk2 = sinifla(I, R)
            alt = im.get('alt_text') or ''
            yasak = [p for p in ALT_YASAK if re.search(p, alt, re.I)]
            gal.append(dict(cift=cift, ilan=lid, sira=im.get('rank'), gorsel_id=im.get('listing_image_id'),
                            boyut=f"{im.get('full_width')}x{im.get('full_height')}", sinif=k, en_yakin=ad,
                            skor=sk, ikinci_kume_en_yakin=ad2, ikinci_skor=sk2,
                            yuklenme=time.strftime('%Y-%m-%d', time.gmtime(im.get('created_timestamp') or 0)),
                            alt=alt))
            altm.append(dict(cift=cift, ilan=lid, sira=im.get('rank'), alt=alt,
                             e08=('E08:' + '|'.join(yasak)) if yasak else ''))
            t = I.copy(); t.thumbnail((160, 160))
            kucuk.append((t, f"{im.get('rank')}{'E' if k == 'ESKI' else ('Y' if k == 'YENI' else '?')}"))
        serit.append((cift, lid, kucuk))
        if not a.klasor_atla:
            for r in RENKLER:
                fid = klasor_id(s.get(f'source_{r}', ''))
                d, n, h = klasor_say(fid) if fid else ('LINK_YOK', 0, '')
                kls.append(dict(cift=cift, renk=r, klasor_id=fid, durum=d, oge=n, hata=h))
        g = time.time() - t0
        print(f'[{i}/{N}] {cift} {lid} {durum} gorsel {len(imgs)} | gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s '
              f'| %{i / N * 100:.0f} | kota {api.remaining}', flush=True)
        if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
            print(f'DUR: kota {api.remaining} < {KOTA_TABAN}', flush=True)
            break

    def yaz(ad, rows):
        if not rows:
            return
        alan = list(dict.fromkeys(k for r in rows for k in r))
        with open(out / ad, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(rows)
    yaz('GALERI.csv', gal); yaz('ALT_METIN.csv', altm); yaz('ESLEME.csv', esl); yaz('KLASOR.csv', kls)

    # temas: her ilan bir satir
    H = 130
    Wt = 22 * 168 + 330
    T = Image.new('RGB', (Wt, H * len(serit) + 10), (250, 248, 245))
    d = ImageDraw.Draw(T)
    for j, (cift, lid, kucuk) in enumerate(serit):
        y = 5 + j * H
        d.text((5, y + 5), f'{cift}\n{lid}', fill=(0, 0, 0))
        for n, (t, et) in enumerate(kucuk):
            t2 = t.copy(); t2.thumbnail((160, H - 18))
            T.paste(t2, (330 + n * 168, y + 16))
            d.text((330 + n * 168, y + 2), et, fill=(180, 0, 0) if 'E' in et else (0, 0, 0))
    T.save(out / 'GALERI_TEMAS.jpg', quality=85)

    eski = [g for g in gal if g.get('sinif') == 'ESKI']
    e08 = [x for x in altm if x['e08']]
    uy = [x for x in esl if x['uyum'] != 'UYUMLU']
    ke = [x for x in kls if x['durum'] != 'ACIK']
    oz_ = [f'# HATA KONTROL galeri/eslesme/klasor ({time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())})', '',
           f'Ilan: {len(esl)} | gorsel: {len(gal)} | ESKI (24 Eyl set) eslesen gorsel: {len(eski)} '
           f'({len({g["ilan"] for g in eski})} ilan) | BILINMIYOR: {sum(g.get("sinif") == "BILINMIYOR" for g in gal)}',
           f'E08 alt metin: {len(e08)} gorsel ({len({x["ilan"] for x in e08})} ilan)',
           f'Esleme uyumsuz: {len(uy)} | klasor acilmayan/bos: {len(ke)} / {len(kls)}', '']
    for x in uy:
        oz_.append(f'- ESLEME {x["cift"]} {x["ilan"]}: state {x["state"]}, baslik cifti {x["baslik_cift"]}, '
                   f'pod78_ids {x["pod78_ids_ilan"]}')
    for x in ke:
        oz_.append(f'- KLASOR {x["cift"]} {x["renk"]}: {x["durum"]} {x["hata"]}')
    (out / 'OZET.md').write_text('\n'.join(oz_) + '\n')
    print('\n'.join(oz_))


if __name__ == '__main__':
    main()
