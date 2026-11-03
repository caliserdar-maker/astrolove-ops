#!/usr/bin/env python3
"""Printful v2 mockup gorevi: urun 900 (seramik ornament), varyant 23133 (Circle), placement front, technique sublimation.
YALNIZ mockup uretimi (Merkez / Serdar 3 Kas, SADE_8). Magazada urun, sablon ya da siparis OLUSTURULMAZ.
Izinli istekler: GET /v2/catalog-products/900/mockup-styles, POST /v2/mockup-tasks, GET /v2/mockup-tasks?id=..., Printful CDN indirme.
Gorsel URL'si once yetkisiz GET ile denetlenir (PNG, 954 x 954); degilse DUR (cikis 2), gorev acilmaz.
Kullanim: ornament_mockup.py <klasor (SADE_<n>_*_954.png)> <ham_url_koku>   Ortam: PRINTFUL_TOKEN"""
import json
import os
import pathlib
import re
import struct
import sys
import time
import urllib.error
import urllib.request

API = 'https://api.printful.com'
URUN, VARYANT, PRINTFILE = 900, 23133, 845
UA = 'Mozilla/5.0 (X11; Linux x86_64) astrolove-ops ornament-mockup'
IZIN = (('GET', re.compile(r'^/v2/catalog-products/900/mockup-styles(\?.*)?$')), ('POST', re.compile(r'^/v2/mockup-tasks$')),
        ('GET', re.compile(r'^/v2/mockup-tasks\?id=\d+$')))


def istek(yol, token, veri=None, deneme=6):
    yontem = 'POST' if veri is not None else 'GET'
    assert any(y == yontem and r.match(yol) for y, r in IZIN), f'izin disi istek {yontem} {yol}'
    for i in range(1, deneme + 1):
        req = urllib.request.Request(API + yol, data=json.dumps(veri).encode() if veri is not None else None, method=yontem,
                                     headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': UA,
                                              'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            govde = e.read().decode()[:3000]
            if e.code == 429 and i < deneme:
                sn = re.search(r'after (\d+) seconds', govde)
                bekle = (int(sn.group(1)) if sn else 60) + 5
                print(f'429 {yol} deneme {i}/{deneme}, {bekle} sn', flush=True); time.sleep(bekle); continue
            print('HATA', yontem, yol, e.code, govde, flush=True)
            return e.code, {'hata': govde}


def png_olcu(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    if b[:8] != b'\x89PNG\r\n\x1a\n' or b[12:16] != b'IHDR':
        return None
    return struct.unpack('>II', b[16:24])


def stiller(d):
    """yanittan front + sublimation stil kayitlarini (id, kategori, gorunum) toplar."""
    out = []
    for blok in d.get('data', []):
        if blok.get('placement') != 'front':
            continue
        for s in blok.get('mockup_styles', []):
            out.append(dict(id=s.get('id'), kategori=s.get('category_name'), gorunum=s.get('view_name'), teknik=blok.get('technique'),
                            varyant=s.get('restricted_to_variants') or []))
    # deneme 1 (kosu 41626773407): diger varyantlarin stilleri 400 verdi; yalniz 23133'e ait (ya da kisitsiz) ve on gorunum
    return [s for s in out if s['id'] is not None and (not s['varyant'] or VARYANT in s['varyant']) and (s['gorunum'] or '').lower() == 'front']


def main():
    K, KOK = pathlib.Path(sys.argv[1]), sys.argv[2].rstrip('/')
    tok = os.environ['PRINTFUL_TOKEN'].strip()
    ham = K / 'mockup_ham'; ham.mkdir(exist_ok=True)
    tum = K / 'mockup_tum'; tum.mkdir(exist_ok=True)
    dosyalar = sorted(K.glob('SADE_*_954.png'), key=lambda p: int(p.name.split('_')[1]))
    if len(dosyalar) != 8:
        print('DUR: 8 SADE PNG yok', [p.name for p in dosyalar]); return 2
    for p in dosyalar:
        o = png_olcu(f'{KOK}/{p.name}')
        print('URL', p.name, o, flush=True)
        if o != (954, 954):
            print('DUR: gorsel URL okunamadi ya da 954 x 954 degil', p.name, o); return 2
    k, st = istek(f'/v2/catalog-products/{URUN}/mockup-styles?placements=front', tok)
    (ham / 'mockup_styles.json').write_text(json.dumps(dict(http=k, yanit=st), indent=1, ensure_ascii=False))
    S = [s for s in stiller(st) if (s['teknik'] or 'sublimation') == 'sublimation']
    print('STIL', json.dumps(S, ensure_ascii=False), flush=True)
    if k != 200 or not S:
        print('DUR: mockup stilleri okunamadi'); return 2
    ana = next((s for s in S if (s['kategori'] or '').lower() == 'flat' and (s['gorunum'] or '').lower() == 'front'), S[0])
    ozet = dict(urun=URUN, varyant=VARYANT, printfile=PRINTFILE, secilen_stil=ana, stiller=S, gorev={})
    for p in dosyalar:
        n = p.name.split('_')[1]
        govde = dict(format='jpg', products=[dict(source='catalog', catalog_product_id=URUN, catalog_variant_ids=[VARYANT],
                                                   mockup_style_ids=[s['id'] for s in S],
                                                   placements=[dict(placement='front', technique='sublimation',
                                                                    layers=[dict(type='file', url=f'{KOK}/{p.name}')])])])
        k, r = istek('/v2/mockup-tasks', tok, govde)
        (ham / f'gorev_{n}_olustur.json').write_text(json.dumps(dict(http=k, govde=govde, yanit=r), indent=1, ensure_ascii=False))
        try:
            gid = r['data'][0]['id']
        except Exception:
            print('DUR: gorev acilamadi', n, k); return 3
        son = None
        for _ in range(60):
            time.sleep(5)
            k2, r2 = istek(f'/v2/mockup-tasks?id={gid}', tok)
            d = (r2.get('data') or [{}])[0] if isinstance(r2, dict) else {}
            if d.get('status') in ('completed', 'failed'):
                son = d; break
        (ham / f'gorev_{n}_sonuc.json').write_text(json.dumps(son or {'durum': 'zaman asimi'}, indent=1, ensure_ascii=False))
        if not son or son.get('status') != 'completed':
            print('DUR: gorev tamamlanmadi', n, (son or {}).get('status'), (son or {}).get('failure_reasons')); return 3
        mk = [m for v in son.get('catalog_variant_mockups', []) for m in v.get('mockups', [])]
        kayit = []
        for m in mk:
            u = m.get('mockup_url')
            ad = f"MOCKUP_{n}_{m.get('style_id')}.jpg"
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as rr:
                (tum / ad).write_bytes(rr.read())
            kayit.append(dict(style_id=m.get('style_id'), ad=m.get('display_name'), dosya=f'mockup_tum/{ad}'))
            if m.get('style_id') == ana['id']:
                (K / f'MOCKUP_{n}.jpg').write_bytes((tum / ad).read_bytes())
        if not (K / f'MOCKUP_{n}.jpg').exists() and kayit:
            (K / f'MOCKUP_{n}.jpg').write_bytes((K / kayit[0]['dosya']).read_bytes())
        ozet['gorev'][n] = dict(gorev_id=gid, mockup=kayit)
        print('MOCKUP', n, gid, len(kayit), flush=True)
    (K / 'MOCKUP_OZET.json').write_text(json.dumps(ozet, indent=1, ensure_ascii=False))
    print('OZET tamam', len(ozet['gorev']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
