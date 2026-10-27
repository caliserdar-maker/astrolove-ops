"""YD (1st Anniversary) kapak: cift icin kaynak URL (mod url), edit ops (mod ops) ya da log (mod log).
Kullanim:
  python3 -I yd_ops.py url CIFT
  python3 -I yd_ops.py ops CIFT PAGE_ID ASSET_ID
  python3 -I yd_ops.py log CIFT DESIGN_ID ASSET_ID YD_LOG_B<n>.tsv
  python3 -I yd_ops.py liste           (uretilecek 75 cift, 4 gruba bolunmus)
Sablon: Canva DAHZHemU2a4 sayfa 1 (onayli "Yesil B", CANCER & LIBRA). Karar: claude/AstroLove_YD_KAPAK_KARAR_20261026.md
"""
import csv
import json
import os
import re
import sys

D = os.path.dirname(os.path.abspath(__file__))
ROWS = [r for r in csv.DictReader(open(os.path.join(D, 'KAPAK_KAYNAK.csv'), encoding='utf-8')) if r['tur'] == 'yd']
K = {r['cift']: r for r in ROWS}
assert len(K) == 78, len(K)
ORNEK = {'SAGITTARIUS_SAGITTARIUS': 'DAHZHr2mx2E', 'CAPRICORN_SAGITTARIUS': 'DAHZHkbHFBk', 'ARIES_LEO': 'DAHZHvJi_UE'}
POSTER = 'LBsvZqCP090GyX5k'
SATIR = 'LBjKvHxqtVWBr6Bf'
KIRP = dict(top=-116.4, left=-93.2, width=1552.5, height=1940.6)


def ad(s):
    return s.capitalize()


def ops(cift, page, asset):
    a, b = cift.split('_')
    return [
        dict(type='update_fill', locator_id=f'{page}-{POSTER}', asset_type='image', asset_id=asset,
             alt_text=f'{ad(a)} and {ad(b)} floral first anniversary print'),
        dict(type='crop_media', locator_id=f'{page}-{POSTER}', **KIRP),
        dict(type='replace_text', locator_id=f'{page}-{SATIR}', text=f'{a} & {b}'),
        dict(type='update_title', title=f'YD_KAPAK_V1 {cift}'),
    ]


def liste():
    kalan = [c for c in K if c not in ORNEK]
    return {f'B{i + 1}': kalan[i::4] for i in range(4)}


if __name__ == '__main__':
    mod = sys.argv[1]
    if mod == 'url':
        r = K[sys.argv[2]]
        assert r['kaynak_boyut'] == '2400x3000', r['kaynak_boyut']
        print(r['kaynak_url'])
    elif mod == 'ops':
        print(json.dumps(ops(sys.argv[2], sys.argv[3], sys.argv[4]), ensure_ascii=False))
    elif mod == 'log':
        cift, design, asset, dosya = sys.argv[2:6]
        assert cift in K and cift not in ORNEK, cift
        assert re.fullmatch(r'YD_LOG_B[1-4]\.tsv', dosya), dosya
        with open(os.path.join(D, dosya), 'a') as f:
            f.write('\t'.join([cift, design, asset, K[cift]['listing_id'], K[cift]['kaynak_image_id']]) + '\n')
        print(dosya, open(os.path.join(D, dosya)).read().count('\n'), 'satir')
    elif mod == 'liste':
        for g, cs in liste().items():
            print(g, len(cs), ' '.join(cs))
