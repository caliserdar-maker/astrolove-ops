#!/usr/bin/env python3
"""Prodigi urun sayfalarindaki gorselleri indirir (salt okuma, API anahtari yok).
Cikti: OUT/<nn>_<ad>, OUT/index.csv (url, dosya, en, boy, kaynak_sayfa), OUT/KONTAK_<k>.jpg (etiketli kucuk resimler).
Kullanim: sayfa_gorsel_indir.py --out OUT --azami 120 URL [URL ...]
"""
import argparse
import csv
import hashlib
import io
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, ImageDraw

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
RX = re.compile(r'''(?:src|data-src|data-srcset|srcset|href|content)\s*=\s*["']([^"']+)["']|url\(([^)]+)\)|"(https?:\\?/\\?/[^"\s]+?\.(?:jpe?g|png|webp)[^"\s]*)"''', re.I)
UZ = ('.jpg', '.jpeg', '.png', '.webp')


def adaylar(html, taban):
    out = []
    for m in RX.finditer(html):
        ham = next(g for g in m.groups() if g)
        for parca in ham.split(','):
            u = parca.strip().split(' ')[0].strip('\'"').replace('\\/', '/')
            if not u or u.startswith('data:'):
                continue
            u = urljoin(taban, u)
            yol = urlparse(u).path.lower()
            if yol.endswith(UZ) or any(k in u.lower() for k in ('format=jpg', 'format=webp', 'fm=jpg', '/image/')):
                out.append(u)
    return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--azami', type=int, default=120)
    ap.add_argument('urls', nargs='+')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    T0 = time.time(); kayit = []; gorulen = set()
    tum = []
    for s in a.urls:
        r = requests.get(s, headers=UA, timeout=60); print(s, r.status_code, len(r.text), flush=True)
        (out / f'sayfa_{hashlib.md5(s.encode()).hexdigest()[:6]}.html').write_text(r.text, encoding='utf-8')
        tum += [(u, s) for u in adaylar(r.text, s)]
    print('aday gorsel', len(tum), flush=True)
    for i, (u, s) in enumerate(tum):
        if len(kayit) >= a.azami:
            break
        try:
            r = requests.get(u, headers=UA, timeout=60)
            if r.status_code != 200 or len(r.content) < 3000:
                continue
            h = hashlib.md5(r.content).hexdigest()
            if h in gorulen:
                continue
            im = Image.open(io.BytesIO(r.content)); im.load()
            if min(im.size) < 200:
                continue
            gorulen.add(h)
            ad = f'{len(kayit):03d}_' + re.sub(r'[^A-Za-z0-9._-]', '_', Path(urlparse(u).path).name)[-60:]
            if not ad.lower().endswith(UZ):
                ad += '.jpg'
            im.convert('RGB').save(out / (Path(ad).stem + '.jpg'), quality=92)
            kayit.append({'url': u, 'dosya': Path(ad).stem + '.jpg', 'en': im.width, 'boy': im.height, 'sayfa': s})
        except Exception as e:  # noqa: BLE001
            print('atla', u[:120], type(e).__name__, flush=True)
        gecen = time.time() - T0; n = i + 1
        print(f'[{n}/{len(tum)}] %{100*n/len(tum):.0f} gecen {gecen:.0f}s kalan ~{gecen/n*(len(tum)-n):.0f}s', flush=True)
    with open(out / 'index.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dosya', 'en', 'boy', 'url', 'sayfa']); w.writeheader(); w.writerows(kayit)
    # kontak sayfalari: 5x4, 300 px, dosya adi etiketli
    for k in range(0, len(kayit), 20):
        sheet = Image.new('RGB', (5 * 310, 4 * 340), 'white'); d = ImageDraw.Draw(sheet)
        for j, rec in enumerate(kayit[k:k + 20]):
            im = Image.open(out / rec['dosya']); im.thumbnail((300, 300))
            x, y = (j % 5) * 310 + 5, (j // 5) * 340 + 5
            sheet.paste(im, (x, y)); d.text((x, y + 305), rec['dosya'][:40], fill='black')
        sheet.save(out / f'KONTAK_{k // 20 + 1}.jpg', quality=85)
    print('indirilen', len(kayit), flush=True)


if __name__ == '__main__':
    sys.exit(main())
