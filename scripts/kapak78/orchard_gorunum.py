#!/usr/bin/env python3
"""Kupa bilgi kartlari icin Orchard gorunumleri (Merkez 27 Eki madde 4): kupa_orchard/kod/cift.py bolum 1 (yalniz Orange Blossom 11 oz
baski) ve bolum 3 (tek on / arka, 15 oz, kisa Mia & Leo 'Always', uzun Maximilian & Josephine 'Forever my favorite adventure!') ile
AYNI cagrilar (baski_kes.py, kapak_canva3.py, ayni ortam GOLGE_US 0.4, PARLA 0.7). kupa-orchard78 is akisiyla ayni surumlerle kosulur
(numpy 2.5.3, pillow 12.3.0, scipy 1.18.1, opencv 5.0.0.93). CANCER_LIBRA dogrulamasi: tek_on / tek_arka kirpimi canli Orchard kart 3
ile ortalama mutlak fark 1,53 / 1,32 (JPEG). Merkez 28 Eki (kupa 04 SADE): cift.py bolum 1 + 2'deki 8 stil baskisi (ayni baski_kes / RENKLER)
tek on sahnesine giydirilir (stil_<st>.jpg; kapak sahneleri renkli zeminli oldugu icin kart 4'te tek zemin icin tek on sahnesi).
Yakin plan sahnesi (ahsap masa, orgu, portakal) kupa_zemin ile temiz esitlenmedi (28 Eki yerel: kenar 83 > 3); kupa 02 tek on'dan. Zemin esitleme ayri adim: kupa_zemin.py <cikti>/gorunum <cikti> (kart ortaminda).
Kullanim: orchard_gorunum.py <kupa_orchard klasoru> <sembol klasoru (ana, sol, sag)> <burc1> <burc2> <cikti>"""
import os, subprocess, sys

KO, SEM, B1, B2, OUT = sys.argv[1:6]
K = os.path.abspath(os.path.join(KO, 'kod')) + '/'; V = os.path.abspath(os.path.join(KO, 'varlik')) + '/'
OUT = os.path.abspath(OUT); SEM = os.path.abspath(SEM)
os.makedirs(OUT + '/baski', exist_ok=True); os.makedirs(OUT + '/gorunum', exist_ok=True)
ENV = {'GOLGE_US': '0.4', 'PARLA': '0.7', 'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
PY = sys.executable


def calis(a, env):
    r = subprocess.run(a, capture_output=True, text=True, env=env, cwd=K)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-1500:])
        raise SystemExit('HATA: ' + ' '.join(a[:3]))


ST8 = [('orange', 'Orange Blossom'), ('fig', 'Purple Fig'), ('olive', 'Olive Breeze'), ('pomegranate', 'Pomegranate Bloom'),
       ('almond', 'Almond Blossom'), ('lemon', 'Lemon Grove'), ('grape', 'Blue Grape'), ('loquat', 'Golden Loquat')]     # cift.py ile ayni
RENKLER = {'orange': '10,40,24', 'fig': '52,18,48', 'olive': '12,24,78', 'pomegranate': '100,16,24', 'almond': '52,22,14',
           'lemon': '12,22,76', 'grape': '16,30,90', 'loquat': '62,24,10'}


def baski(i1, i2, m, c, st='orange'):
    calis([PY, '-I', K + 'baski_kes.py', V + 'kes/' + st.upper() + 'R', SEM, i1, i2, B1, B2, m, RENKLER[st], c], dict(ENV))


def giydir(s, b, g, c, d_in=None):
    e = dict(ENV)
    if d_in:
        e['D_IN'] = d_in
    calis([PY, '-I', K + 'kapak_canva3.py', s, b, g, c], e)


baski('Emily', 'James', 'My favorite place is with you', OUT + '/baski/B_orange')
BO = OUT + '/baski/B_orange_baski_11oz.png'; G = OUT + '/gorunum/'
for y in ('tek_on', 'tek_arka'):
    giydir(V + f'gorunum/ORCHARD_OrangeBlossom_sahne_{y}.png', BO, V + f'gorunum/geo_{y}.json', G + f'{y}.jpg')
giydir(V + 'gorunum/sahne15.png', BO, V + 'gorunum/geo15.json', G + 'm15.jpg', d_in='3.35')
baski('Mia', 'Leo', 'Always', OUT + '/baski/ML')
baski('Maximilian', 'Josephine', 'Forever my favorite adventure!', OUT + '/baski/MJ')
for ad in ('ML', 'MJ'):
    for y, kk in (('tek_on', 'on'), ('tek_arka', 'arka')):
        giydir(V + f'gorunum/ORCHARD_OrangeBlossom_sahne_{y}.png', f'{OUT}/baski/{ad}_baski_11oz.png', V + f'gorunum/geo_{y}.json',
               G + f'{ad}_{kk}.jpg')
for st, _ in ST8:
    b = BO if st == 'orange' else OUT + f'/baski/B_{st}_baski_11oz.png'
    if st != 'orange':
        baski('Emily', 'James', 'My favorite place is with you', OUT + f'/baski/B_{st}', st)
    giydir(V + 'gorunum/ORCHARD_OrangeBlossom_sahne_tek_on.png', b, V + 'gorunum/geo_tek_on.json', G + f'stil_{st}.jpg')
print('tamam', sorted(os.listdir(G)), flush=True)
