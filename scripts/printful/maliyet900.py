#!/usr/bin/env python3
"""Printful 900 (seramik ornament, Circle varyant 23133) MALIYET DOGRULAMA (Merkez / Serdar 3 Kas). SALT OKUMA; siparis / taslak YOK.
Izinli istekler (assert): GET /oauth/scopes, GET /orders?limit=5, POST /orders/estimate-costs, POST /shipping/rates,
  GET /products/variant/23133; Printful API disi yalniz GET: resmi dokuman sayfasi (developers.printful.com) ve yardim makalesi.
  TASLAK yolu (POST /orders) YOK (Merkez: yasak).
1 dokuman: developers.printful.com/docs/ (HTML) indirilir, 'estimate-costs' cevresindeki metin kaydedilir.
2 yetki: GET /oauth/scopes.
3a orders/read VARSA: GET /orders?limit=5 (paging.total) ONCE; 14 ulke x 1 ve 2 adet POST /orders/estimate-costs; yanitta siparis id /
   draft varsa DUR (cikis 3); GET /orders?limit=5 SONRA; total farkliysa DUR (cikis 3).
3b orders/read YOKSA: POST /shipping/rates ADRES ulkeleri x 1 ve 2 adet (ek adet = 2 adet - 1 adet), GET /products/variant/23133 (urun fiyati),
   KDV: help.printful.com makale 360014008620 (Zendesk API JSON, olmazsa HTML); acilmazsa 'dogrulanamadi'.
Adresler: kamu binasi / muze adresleri (gercek musteri degil), ad 'Test'. Dosya: bu deponun herkese acik SADE_1 ornek PNG'si.
Kullanim: maliyet900.py <cikti_klasoru>  (env PRINTFUL_TOKEN)"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

PF = 'https://api.printful.com'
UA = 'Mozilla/5.0 (X11; Linux x86_64) astrolove-ops maliyet900'
VARYANT = 23133
DOSYA = 'https://raw.githubusercontent.com/caliserdar-maker/astrolove-ops/6daab364/docs/ornament/ornek/ORNAMENT_5STIL_20261103_1539/CANCER_LIBRA_FILDISI_954.png'
ADRES = {
    'US': dict(country_code='US', state_code='NY', city='New York', zip='10118', address1='350 5th Ave'),
    'CA': dict(country_code='CA', state_code='ON', city='Ottawa', zip='K1A 0A9', address1='111 Wellington St'),
    'GB': dict(country_code='GB', city='London', zip='WC2N 5DN', address1='Trafalgar Square'),
    'DE': dict(country_code='DE', city='Berlin', zip='10557', address1='Platz der Republik 1'),
    'FR': dict(country_code='FR', city='Paris', zip='75007', address1='5 Avenue Anatole France'),
    'NL': dict(country_code='NL', city='Amsterdam', zip='1071 XX', address1='Museumstraat 1'),
    'IT': dict(country_code='IT', city='Roma', zip='00184', address1='Piazza del Colosseo 1'),
    'ES': dict(country_code='ES', city='Madrid', zip='28014', address1='Calle de Ruiz de Alarcon 23'),
    'AU': dict(country_code='AU', state_code='NSW', city='Sydney', zip='2000', address1='Bennelong Point'),
    'NZ': dict(country_code='NZ', city='Wellington', zip='6011', address1='55 Cable Street'),
    'JP': dict(country_code='JP', city='Chiyoda-ku, Tokyo', zip='100-0005', address1='1-9-1 Marunouchi'),
    'CH': dict(country_code='CH', city='Zurich', zip='8001', address1='Museumstrasse 2'),
    'NO': dict(country_code='NO', city='Oslo', zip='0026', address1='Karl Johans gate 22'),
    'TR': dict(country_code='TR', city='Istanbul', zip='34435', address1='Taksim Meydani, Beyoglu'),
    # Serdar 7 Kas "tum ulkelere kargo": ek ulkeler (kamu binasi / muze adresleri, gercek musteri degil)
    'SE': dict(country_code='SE', city='Stockholm', zip='100 12', address1='Riksgatan 1'),
    'PL': dict(country_code='PL', city='Warszawa', zip='00-902', address1='ul. Wiejska 4'),
    'IE': dict(country_code='IE', city='Dublin', zip='D02 FH48', address1='Kildare Street'),
    'DK': dict(country_code='DK', city='Kobenhavn', zip='1240', address1='Christiansborg Slotsplads 1'),
    'AT': dict(country_code='AT', city='Wien', zip='1010', address1='Maria-Theresien-Platz'),
    'BE': dict(country_code='BE', city='Bruxelles', zip='1000', address1='Rue de la Loi 16'),
    'PT': dict(country_code='PT', city='Lisboa', zip='1100-148', address1='Praca do Comercio'),
    'MX': dict(country_code='MX', state_code='CMX', city='Ciudad de Mexico', zip='06000', address1='Plaza de la Constitucion'),
    'BR': dict(country_code='BR', state_code='SP', city='Sao Paulo', zip='01310-200', address1='Av. Paulista 1578'),
    'IN': dict(country_code='IN', state_code='DL', city='New Delhi', zip='110001', address1='Rajpath'),
    'ZA': dict(country_code='ZA', city='Cape Town', zip='8001', address1='25 Queen Victoria Street'),
    'SG': dict(country_code='SG', city='Singapore', zip='178957', address1='1 St Andrews Road'),
    'KR': dict(country_code='KR', city='Seoul', zip='03154', address1='209 Sejong-daero'),
    'AE': dict(country_code='AE', city='Dubai', zip='00000', address1='Sheikh Mohammed bin Rashid Blvd'),
    'IL': dict(country_code='IL', city='Jerusalem', zip='9195016', address1='Ruppin Blvd 11'),
}
IZIN = (('GET', re.compile(r'^/oauth/scopes$')), ('GET', re.compile(r'^/orders\?limit=5$')), ('POST', re.compile(r'^/orders/estimate-costs$')),
        ('POST', re.compile(r'^/shipping/rates$')), ('GET', re.compile(r'^/products/variant/23133$')))
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept': 'application/json'})


def pf(yontem, yol, veri=None):
    assert any(y == yontem and r.match(yol) for y, r in IZIN), f'izin disi {yontem} {yol}'
    for d in range(4):
        r = S.request(yontem, PF + yol, json=veri, timeout=60,
                      headers={'Authorization': f"Bearer {os.environ['PRINTFUL_TOKEN'].strip()}", 'Content-Type': 'application/json'})
        if r.status_code == 429 and d < 3:
            time.sleep(35); continue
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {'ham': r.text[:1500]}


def sonuc(d):
    return d.get('result') if isinstance(d, dict) else None


def siparis_sayisi():
    st, d = pf('GET', '/orders?limit=5')
    p = (d or {}).get('paging') or {}
    return st, p.get('total'), [o.get('id') for o in (sonuc(d) or [])] if isinstance(sonuc(d), list) else None


def dokuman(R):
    try:
        r = S.get('https://developers.printful.com/docs/', timeout=60)
        t = r.text
        idx = [m.start() for m in re.finditer('estimate-costs', t)]
        parca = [re.sub(r'<[^>]+>', ' ', t[max(0, i - 1500):i + 1500]) for i in idx[:4]]
        R['dokuman'] = dict(http=r.status_code, uzunluk=len(t), eslesme=len(idx), parca=[re.sub(r'\s+', ' ', p)[:3000] for p in parca])
    except Exception as e:                                                   # noqa: BLE001
        R['dokuman'] = dict(hata=f'{type(e).__name__}: {e}'[:300])


def kdv_sayfasi(R):
    for u in ('https://help.printful.com/api/v2/help_center/en-us/articles/360014008620.json',
              'https://help.printful.com/hc/en-us/articles/360014008620'):
        try:
            r = S.get(u, timeout=60)
            if r.ok:
                body = r.json()['article']['body'] if u.endswith('.json') else r.text
                metin = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body))
                cum = [c.strip() for c in re.split(r'(?<=[.!?])\s+', metin) if re.search(r'VAT|GST|tax|Switzerland|Norway|Australia|UK|EU', c)]
                R['kdv_sayfasi'] = dict(url=u, http=r.status_code, baslik=(r.json()['article'].get('title') if u.endswith('.json') else None),
                                        ilgili_cumleler=cum[:60], metin_uzunluk=len(metin))
                return
            R.setdefault('kdv_sayfasi_denemeler', []).append(dict(url=u, http=r.status_code))
        except Exception as e:                                               # noqa: BLE001
            R.setdefault('kdv_sayfasi_denemeler', []).append(dict(url=u, hata=f'{type(e).__name__}'[:200]))
    R['kdv_sayfasi'] = 'dogrulanamadi (sayfa acilmadi)'


def main():
    O = Path(sys.argv[1]); O.mkdir(parents=True, exist_ok=True)
    damga = time.strftime('%Y%m%d_%H%M', time.gmtime())
    R = dict(gorev='Printful 900 maliyet dogrulama (salt okuma, siparis yok)', varyant=VARYANT, dosya=DOSYA, damga=damga, satir=[])
    dokuman(R)
    st, d = pf('GET', '/oauth/scopes')
    sc = sonuc(d) or {}
    scopes = [s.get('scope') or s.get('value') for s in sc.get('scopes', [])] if isinstance(sc, dict) else []   # Printful anahtari 'scope' (kosu 41672511992)
    R['yetki'] = dict(http=st, scopes=scopes, ham=d)
    print('yetki', st, scopes, flush=True)
    kod = 0
    if 'orders/read' in scopes or 'orders' in scopes:
        R['yol'] = 'estimate-costs'
        R['siparis_once'] = siparis_sayisi(); print('siparis once', R['siparis_once'][:2], flush=True)
        for ul, adr in ADRES.items():
            satir = dict(ulke=ul)
            for q in (1, 2):
                govde = {'recipient': dict(name='Test', **adr), 'items': [{'variant_id': VARYANT, 'quantity': q, 'files': [{'url': DOSYA}]}]}
                st, d = pf('POST', '/orders/estimate-costs', govde)
                r_ = sonuc(d)
                satir[f'http_{q}'] = st; satir[f'costs_{q}'] = (r_ or {}).get('costs') if isinstance(r_, dict) else None
                if st != 200:
                    satir[f'hata_{q}'] = d
                if isinstance(r_, dict) and (r_.get('id') or str(r_.get('status', '')).lower() == 'draft' or 'order' in r_):
                    R['DUR'] = f'yanitta siparis / taslak izi ({ul}, {q} adet): anahtarlar {list(r_.keys())}'; kod = 3
                time.sleep(0.8)
            R['satir'].append(satir); print(ul, satir.get('http_1'), (satir.get('costs_1') or {}).get('total'), (satir.get('costs_2') or {}).get('total'), flush=True)
            if kod:
                break
        R['siparis_sonra'] = siparis_sayisi(); print('siparis sonra', R['siparis_sonra'][:2], flush=True)
        if R['siparis_once'][1] != R['siparis_sonra'][1] or R['siparis_once'][2] != R['siparis_sonra'][2]:
            R['DUR'] = f"siparis sayisi degisti: {R['siparis_once'][1]} -> {R['siparis_sonra'][1]}"; kod = 3
    else:
        R['yol'] = 'shipping-rates + urun fiyati + KDV yardim sayfasi (orders/read yok)'
        st, d = pf('GET', '/products/variant/23133')
        v = (sonuc(d) or {}).get('variant') or {}
        R['urun'] = dict(http=st, ad=v.get('name'), fiyat=v.get('price'), para='USD (Printful katalog)')
        for ul, adr in ADRES.items():
            satir = dict(ulke=ul)
            for q in (1, 2):
                st, d = pf('POST', '/shipping/rates', {'recipient': {k: v_ for k, v_ in adr.items() if k in ('country_code', 'state_code', 'city', 'zip', 'address1')},
                                                         'items': [{'variant_id': VARYANT, 'quantity': q}], 'currency': 'USD'})
                rates = sonuc(d) if isinstance(sonuc(d), list) else []
                std = next((x for x in rates if x.get('id') == 'STANDARD'), rates[0] if rates else None)
                satir[f'http_{q}'] = st; satir[f'kargo_{q}'] = std
                if st != 200:
                    satir[f'hata_{q}'] = d
                time.sleep(0.8)
            R['satir'].append(satir); print(ul, satir.get('http_1'), (satir.get('kargo_1') or {}).get('rate'), (satir.get('kargo_2') or {}).get('rate'), flush=True)
    kdv_sayfasi(R)
    # tablo
    sat = ['| ulke | urun (1 adet) | kargo 1 adet | ek adet kargo | KDV / vergi satiri | toplam 1 adet | toplam 2 adet | kaynak |', '|---|---|---|---|---|---|---|---|']
    for s in R['satir']:
        if R['yol'] == 'estimate-costs':
            c1, c2 = s.get('costs_1') or {}, s.get('costs_2') or {}
            ek = (round(float(c2['shipping']) - float(c1['shipping']), 2) if c1.get('shipping') is not None and c2.get('shipping') is not None else None)
            vergi = f"tax {c1.get('tax')} / vat {c1.get('vat')}"
            sat.append(f"| {s['ulke']} | {c1.get('subtotal')} | {c1.get('shipping')} | {ek} | {vergi} | {c1.get('total')} {c1.get('currency', '')} | {c2.get('total')} | API estimate-costs (HTTP {s.get('http_1')}/{s.get('http_2')}) |")
        else:
            k1, k2 = s.get('kargo_1') or {}, s.get('kargo_2') or {}
            ek = (round(float(k2['rate']) - float(k1['rate']), 2) if k1.get('rate') and k2.get('rate') else None)
            sat.append(f"| {s['ulke']} | {(R.get('urun') or {}).get('fiyat')} | {k1.get('rate')} | {ek} | API'de yok (yardim sayfasi asagida) | - | - | API shipping/rates (HTTP {s.get('http_1')}/{s.get('http_2')}), katalog fiyati |")
    (O / f'maliyet_tahmin_{damga}.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    (O / f'maliyet_tahmin_{damga}.md').write_text('# Printful 900 maliyet (salt okuma)\n\n' + f"yol: {R['yol']}\n\n" + '\n'.join(sat) + '\n')
    print('OZET', R['yol'], 'satir', len(R['satir']), 'DUR' if kod else 'tamam', flush=True)
    return kod


if __name__ == '__main__':
    sys.exit(main())
