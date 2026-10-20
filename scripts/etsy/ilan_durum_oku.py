#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK): verilen ilanlarin state'i. GET /listings/batch (1 cagri; by78_yayinla.toplu ile ayni uc,
taslaklari da dondurur). Kota tabani 10 (CLAUDE.md): x-remaining-today < 10 ise DUR. Kilit: workflow'da kilit_bekle.py.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, TOKEN_FILE. Cikti: --out JSON {listing_id: {state, title, url}}, _meta.
Kullanim: ilan_durum_oku.py --ids 1,2,3 --out DURUM.json"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
KOTA_TABAN = 10


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--ids', required=True); a.add_argument('--out', required=True)
    o = a.parse_args()
    from etsy_common import Etsy, TokenStore, log, mask
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    ids = [x.strip() for x in o.ids.split(',') if x.strip()]
    if not ids or len(ids) > 100:
        raise SystemExit(f'DUR: ilan sayisi {len(ids)} (1-100)')
    store = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    d = api.get('/listings/batch', params={'listing_ids': ','.join(ids)}) or {}
    log(f'cagri {api.calls} | kota {api.remaining}')
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        log(f'UYARI: kota {api.remaining} < {KOTA_TABAN} (baska cagri yapilmadi)')
    sonuc = {str(x.get('listing_id')): {'state': x.get('state'), 'title': x.get('title'), 'url': (x.get('url') or '').split('?')[0]}
             for x in d.get('results') or []}
    for i in ids:
        sonuc.setdefault(i, {'state': 'YANITTA_YOK', 'title': '', 'url': ''})
    sonuc['_meta'] = {'okuma_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), 'uc': 'GET /listings/batch',
                      'cagri': api.calls, 'kota_son': api.remaining}
    json.dump(sonuc, open(o.out, 'w'), ensure_ascii=False, indent=1)
    for i in ids:
        log(f'{i}: {sonuc[i]["state"]}')


if __name__ == '__main__':
    main()
