#!/usr/bin/env python3
"""SALT OKUMA (Serdar 23 Eki, siparis 4208728285): TEK receipt'in kisisellestirme alanlari. Etsy'ye yazma YOK, mesaj YOK.
Ham dokum YOK: yalniz kalem basina listing_id, sku ve varyasyonlar (formatted_name / formatted_value; isim ve mesaj
alanlari dahil) <out>/KISISEL.json'a yazilir; alici adi, adres, e-posta, tutar yazilmaz. Loga deger yazilmaz (yalniz alan
adlari ve sayilar). Kullanim: siparis_kisisel.py --receipt N --out DIR"""
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore  # noqa: E402


def ozet(rc):
    """receipt -> yalniz kalem / varyasyon (musteri kimligi yok)."""
    return {'receipt_id': rc.get('receipt_id'), 'kalemler': [
        {'listing_id': t.get('listing_id'), 'sku': t.get('sku'),
         'varyasyon': [{'ad': v.get('formatted_name'), 'deger': v.get('formatted_value')} for v in t.get('variations') or []]}
        for t in rc.get('transactions') or []]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if not a.receipt.isdigit():
        raise SystemExit('DUR: receipt yalniz rakam')
    store = TokenStore(os.environ['TOKEN_FILE'], os.environ['ETSY_API_KEY'], os.environ['ETSY_SHARED_SECRET'])
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    rc = api.get(f"/shops/{os.environ['ETSY_SHOP_ID']}/receipts/{a.receipt}") or {}
    o = ozet(rc)
    if str(o['receipt_id']) != a.receipt:
        raise SystemExit('DUR: receipt okunamadi')
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'KISISEL.json').write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8')
    for k in o['kalemler']:                      # yalniz alan adlari (degerler loga girmez)
        print('KALEM', k['listing_id'], k['sku'], '| alanlar:', [v['ad'] for v in k['varyasyon']], flush=True)
    print(f"PASS | kalem {len(o['kalemler'])} | istek {api.calls} | kota {api.remaining}", flush=True)
    store.write()


if __name__ == '__main__':
    main()
