#!/usr/bin/env python3
"""Kupa kapagi (Orange Blossom, el sahnesi A3, Serdar onayi 30 Eki) uretimi.
Her cift: sembol (kupa-printful-sonuc dali, yalniz okuma) -> baski_kes.py (Emily & James, mesaj) -> kapak_canva4.py -> baslik2.py
Sembol kaynagi her koşuda taze cekilir; commit SHA'si kayit dosyasina yazilir. Tam kosuda 78 cift zorunlu.
Cikti klasorunde onceki KUPA_KAPAK dosyasi varsa durur (karisik set olmasin); YENIDEN=1 ile once silinir.
Kullanim: python3 -I kapak78.py <cikti_klasoru> [CIFT ...]   (cift verilmezse 78'in hepsi)"""
import os, re, shutil, subprocess, sys, time, pathlib

BURASI = pathlib.Path(__file__).resolve().parent            # kupa_orchard/kapak_el/kod
REPO = BURASI.parents[2]
KOD = REPO / 'kupa_orchard/kod'
IS = BURASI.parent                                          # kupa_orchard/kapak_el
OUT = pathlib.Path(sys.argv[1])
DAL = 'kupa-printful-sonuc'
REF = 'refs/kapak78/sembol'
BURCLAR = {'ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO',
           'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES'}


def git(*a, metin=True):
    r = subprocess.run(['git', '-C', str(REPO), *a], capture_output=True, text=metin)
    if r.returncode:
        sys.exit(f'HATA git {" ".join(a)}: {r.stderr if metin else r.stderr.decode(errors="replace")}')
    return r.stdout


git('fetch', '-q', 'origin', f'+{DAL}:{REF}')
SHA = git('rev-parse', REF).strip()
hepsi = [c.split('/')[-1] for c in git('ls-tree', '--name-only', REF, 'kupa_uretim/sembol/').split()]
if len(hepsi) != 78:
    sys.exit(f'HATA: {DAL} dalinda 78 cift bekleniyordu, {len(hepsi)} bulundu')
ciftler = sys.argv[2:] or hepsi
for c in ciftler:
    p = c.split('_')
    if c not in hepsi or len(p) != 2 or not set(p) <= BURCLAR or p != sorted(p):
        sys.exit(f'HATA: gecersiz cift adi {c} (BUYUK harf, alfabetik, ornek CANCER_LIBRA)')

OUT.mkdir(parents=True, exist_ok=True)
eski = sorted(OUT.glob('KUPA_KAPAK_*.jpg'))
if eski:
    if os.environ.get('YENIDEN') != '1':
        sys.exit(f'HATA: {OUT} icinde {len(eski)} eski kapak var; YENIDEN=1 ile silinip yeniden uretilir')
    for f in eski:
        f.unlink()
shutil.rmtree(OUT / 'ara', ignore_errors=True)

ENV = {k: v for k, v in os.environ.items() if k not in ('D_IN', 'SABIT_YUKSEKLIK')}
ENV.update(GOLGE_US='1.0', PARLA='0.7', ALT_ORAN='0.55', IZ_ORAN='0.05', ALT_AGIRLIK='600', GOLGE_GUC='1.6')
kayit = OUT / 'KAYIT.tsv'
kayit.write_text(f'# sembol {DAL} {SHA}\ncift\tbaslik\n')


def kos(c, *a):
    r = subprocess.run(['python3', '-I', *map(str, a)], capture_output=True, text=True, env=ENV)
    satir = r.stdout.strip().splitlines()
    if r.returncode or not satir:
        sys.exit(f'HATA {c} ({pathlib.Path(str(a[0])).name}): {r.stderr[-800:]}')
    return satir[-1]


t0 = time.time()
for i, c in enumerate(ciftler, 1):
    b1, b2 = (x.capitalize() for x in c.split('_'))
    tmp = OUT / 'ara' / c
    (tmp / 'sem').mkdir(parents=True, exist_ok=True)
    for f in ('ana', 'sol', 'sag'):
        (tmp / 'sem' / f'{f}.png').write_bytes(git('show', f'{REF}:kupa_uretim/sembol/{c}/{f}.png', metin=False))
    kos(c, KOD / 'baski_kes.py', KOD.parent / 'varlik/kes/ORANGER', tmp / 'sem', 'Emily', 'James', b1, b2,
        'My favorite place is with you', '10,40,24', tmp / 'b')
    kos(c, BURASI / 'kapak_canva4.py', IS / 'sahne/A3_uzun2.png', tmp / 'b_baski_11oz.png', IS / 'sahne/geo_A3b.json', tmp / 'k.png')
    bilgi = kos(c, BURASI / 'baslik2.py', tmp / 'k.png', OUT / f'KUPA_KAPAK_{c}.jpg', b1, b2, 1500, 535, 185,
                '252,248,240', 'PERSONALIZED GIFT MUG', 1)
    with kayit.open('a') as k:
        k.write(f'{c}\t{bilgi}\n')
    g = time.time() - t0
    print(f'{i}/{len(ciftler)} {c} | {g:.0f} sn, kalan ~{g / i * (len(ciftler) - i):.0f} sn, %{100 * i // len(ciftler)}', flush=True)
print('tamam', OUT, 'sembol', SHA[:7])
