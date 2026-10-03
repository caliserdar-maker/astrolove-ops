#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK): caption CSV'deki listing_id'leri canli ilanla eslestirir.
getListingsByListingIds (/listings/batch, 100'luk parti). Eslesme: ilan var, state=active, shop_id dogru,
baslikta iki burc adi da geciyor (ayni burc: bir kez yeter).
Cikti: out/ILAN_DOGRULA.csv (pair, listing_id, state, shop_ok, title, sonuc, neden). Eslesmeyen varsa cikis 3.
Kullanim: ig_ilan_dogrula.py CAPTIONS.csv"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etsy'))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

OUT = Path('out')


def main():
    rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    store = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = str(os.environ['ETSY_SHOP_ID'])
    ids = [r['listing_id_DOGRULANMADI'] for r in rows]
    canli = {}
    for i in range(0, len(ids), 100):
        d = api.get('/listings/batch', params={'listing_ids': ','.join(ids[i:i + 100])}) or {}
        for L in d.get('results') or []:
            canli[str(L['listing_id'])] = L
    print(f'okunan {len(canli)}/{len(ids)}, cagri {api.calls}, kota {api.remaining}', flush=True)
    out = []
    for r in rows:
        lid = r['listing_id_DOGRULANMADI']
        a, b = (x.title() for x in r['pair'].split('_'))
        L = canli.get(lid)
        neden = []
        if not L:
            neden.append('ilan bulunamadi')
        else:
            if L.get('state') != 'active':
                neden.append(f"state={L.get('state')}")
            if str(L.get('shop_id')) != shop:
                neden.append('baska magaza')
            t = (L.get('title') or '').lower()
            if a.lower() not in t or b.lower() not in t:
                neden.append('baslikta burc adi yok')
        out.append({'pair': r['pair'], 'listing_id': lid, 'state': (L or {}).get('state', ''),
                    'shop_ok': str(bool(L) and str(L.get('shop_id')) == shop), 'title': (L or {}).get('title', ''),
                    'sonuc': 'FAIL' if neden else 'PASS', 'neden': '; '.join(neden)})
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'ILAN_DOGRULA.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
    fail = [x for x in out if x['sonuc'] == 'FAIL']
    print(f'ILAN {len(out) - len(fail)}/{len(out)} PASS' + ''.join(f"\n  {x['pair']} {x['listing_id']}: {x['neden']}" for x in fail))
    sys.exit(3 if fail else 0)


if __name__ == '__main__':
    main()
