#!/usr/bin/env python3
"""Kupa stil gorselleri (galeri 7-14, Style secenegine bagli): her stil kendi el sahnesinde (Canva, ayni el ve kupa,
arka planda o stilin meyvesi; aynali, 11 oz oranina uzatilmis: sahne/stil/STIL_<S>_uzun.png, uzat.py
1066 2284 762 2056 730 800 905, UST_YUM=24), o stilin baskisi giydirilir.
Baslik: 1. satir 'BURC1 & BURC2', 2. satir stil adi; kapakla ayni yerlesim (ALT_REF kapak alt yazisi), krem, guclu golge.
Sembol kaynagi kapak78.py ile ayni ref (refs/kapak78/sembol); kapak KAYIT.tsv SHA'si ile ayni olmali.
Cikti: <cikti>/KUPA_STIL_<CIFT>_<NN>_<STIL>.jpg (NN = 07..14 galeri sirasi) + KAYIT.tsv.
Tum set uretiminde (cift verilmezse) eski gorsel varsa durur; YENIDEN=1 ile silinir. Baskida tasma uyarisi hata sayilir.
Kullanim: python3 -I stil78.py <kapak_klasoru(KAYIT.tsv)> <cikti_klasoru> [CIFT ...]"""
import os, shutil, subprocess, sys, time, pathlib, tempfile

BURASI = pathlib.Path(__file__).resolve().parent
REPO = BURASI.parents[2]
KOD = REPO / 'kupa_orchard/kod'
IS = BURASI.parent
REF = 'refs/kapak78/sembol'
KAP, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
STILLER = [  # (galeri no, sahne, kes oneki, yazi rengi, stil adi) - 18 Eki Orchard karari, sira ve adlar sabit
    ('07', 'ORANGE', 'ORANGER', '10,40,24', 'Orange Blossom'),
    ('08', 'FIG', 'FIGR', '52,18,48', 'Purple Fig'),
    ('09', 'OLIVE', 'OLIVER', '12,24,78', 'Olive Breeze'),
    ('10', 'POMEGRANATE', 'POMEGRANATER', '100,16,24', 'Pomegranate Bloom'),
    ('11', 'ALMOND', 'ALMONDR', '52,22,14', 'Almond Blossom'),
    ('12', 'LEMON', 'LEMONR', '12,22,76', 'Lemon Grove'),
    ('13', 'GRAPE', 'GRAPER', '16,30,90', 'Blue Grape'),
    ('14', 'LOQUAT', 'LOQUATR', '62,24,10', 'Golden Loquat'),
]
TEMIZ = ('D_IN', 'SABIT_YUKSEKLIK', 'SEMBOL_YOK', 'GLIF_YOK', 'MESAJ_YOK', 'IMZA_YOK', 'BURC_YOK', 'BURC_DY', 'BURC_MIN')
ENV = {k: v for k, v in os.environ.items() if k not in TEMIZ}
ENV.update(GOLGE_US='1.0', PARLA='0.7', ALT_ORAN='0.55', IZ_ORAN='0.05', ALT_AGIRLIK='600', GOLGE_GUC='1.6',
           ALT_REF='PERSONALIZED GIFT MUG')   # baslik satirlari kapakla ayni yerde (stil adindaki Q kuyrugu oynatmaz)


def git(*a, metin=True):
    r = subprocess.run(['git', '-C', str(REPO), *a], capture_output=True, text=metin)
    if r.returncode:
        sys.exit(f'HATA git {" ".join(a)}')
    return r.stdout


sha = git('rev-parse', REF).strip()
ilk = (KAP / 'KAYIT.tsv').read_text().splitlines()[0].split()
if ilk[-1] != sha:
    sys.exit(f'HATA: sembol surumu kapaklarla farkli (ref {sha[:7]}, kapak kaydi {ilk[-1][:7]})')
hepsi = [c.split('/')[-1] for c in git('ls-tree', '--name-only', REF, 'kupa_uretim/sembol/').split()]
if len(hepsi) != 78:
    sys.exit(f'HATA: 78 cift bekleniyordu, {len(hepsi)}')
ciftler = sys.argv[3:] or hepsi
for c in ciftler:
    p = c.split('_')
    if c not in hepsi or p != sorted(p):
        sys.exit(f'HATA: gecersiz cift adi {c}')
for _, s, k, _, _ in STILLER:
    for f in (IS / f'sahne/stil/STIL_{s}_uzun.png', KOD.parent / f'varlik/kes/{k}_kes.json',
              KOD.parent / f'varlik/kes/{k}_on.png', KOD.parent / f'varlik/kes/{k}_arka.png'):
        if not f.exists():
            sys.exit(f'HATA: eksik dosya {f}')
OUT.mkdir(parents=True, exist_ok=True)
if not sys.argv[3:]:
    eski = list(OUT.glob('KUPA_STIL_*.jpg'))
    if eski and os.environ.get('YENIDEN') != '1':
        sys.exit(f'HATA: {OUT} icinde {len(eski)} eski gorsel var; YENIDEN=1 ile silinip yeniden uretilir')
    for f in eski:
        f.unlink()
kayit = OUT / ('KAYIT.tsv' if not sys.argv[3:] else f'KAYIT_{os.getpid()}.tsv')
kayit.write_text(f'# sembol {sha}\ncift\tstil\tbaski\tbaslik\n')


def kos(c, *a):
    r = subprocess.run(['python3', '-I', *map(str, a)], capture_output=True, text=True, env=ENV)
    satir = r.stdout.strip().splitlines()
    if r.returncode or not satir:
        sys.exit(f'HATA {c} ({pathlib.Path(str(a[0])).name}): {r.stderr[-600:]}')
    return satir[-1]


t0, n = time.time(), len(ciftler) * len(STILLER)
i = 0
for c in ciftler:
    b1, b2 = (x.capitalize() for x in c.split('_'))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f'stil_{c}_'))
    try:
        (tmp / 'sem').mkdir()
        for f in ('ana', 'sol', 'sag'):
            (tmp / 'sem' / f'{f}.png').write_bytes(git('show', f'{REF}:kupa_uretim/sembol/{c}/{f}.png', metin=False))
        for no, s, k, renk, ad in STILLER:
            bk = kos(c, KOD / 'baski_kes.py', KOD.parent / f'varlik/kes/{k}', tmp / 'sem', 'Emily', 'James', b1, b2,
                     'My favorite place is with you', renk, tmp / k)
            if 'True' in bk:
                sys.exit(f'HATA {c} {s}: baskida tasma: {bk}')
            kos(c, BURASI / 'kapak_canva4.py', IS / f'sahne/stil/STIL_{s}_uzun.png', tmp / f'{k}_baski_11oz.png',
                IS / 'sahne/geo_A3b.json', tmp / f'{k}.png')
            bs = kos(c, BURASI / 'baslik2.py', tmp / f'{k}.png', OUT / f'KUPA_STIL_{c}_{no}_{s}.jpg', b1, b2, 1500, 535,
                     185, '252,248,240', ad.upper(), 1)
            with kayit.open('a') as kf:
                kf.write(f'{c}\t{s}\t{bk[-60:]}\t{bs[:70]}\n')
            i += 1
            g = time.time() - t0
            print(f'{i}/{n} {c} {s} | {g:.0f} sn, kalan ~{g / i * (n - i):.0f} sn, %{100 * i // n}', flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
print('tamam', OUT)
