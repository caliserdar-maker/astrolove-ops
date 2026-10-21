#!/usr/bin/env python3
"""Metricool: bekleyen yil donumu (BY) pinlerinde baski vaadi duzeltmesi (Serdar kararlari 21 Eki 2026, PLAN_KARAR A).
Yalniz Pinterest durumu PENDING olan gonderilerde YALNIZ su alanlar degisir: text (aciklama), mediaAltText, pinterestData.pinTitle.
Degisimler birebir alt dize (DEGIS_*); baska metne dokunulmaz. GET -> degistir -> PUT -> GET; diger alan farki IZINLI_FARK disindaysa FAIL.
Baslik 100'u asarsa once KISALT_BASLIK (Serdar 22 Eki); hala asarsa o pin YAZILMAZ (UZUN). Degisimden sonra metinde vaat kalirsa YAZILMAZ (KALAN).
Ayrica pencere icindeki TUM gonderilerin medya adresleri host bazinda sayilir (Drive kapatma plani C2 on kosulu): MEDYA_HOST.csv.
Uc noktalar: data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json  GET /v2/scheduler/posts?start&end&timezone  GET|PUT /v2/scheduler/posts/{id}
Mod: kuru (liste + CSV, yazma YOK), tek (1 gonderi), hepsi (kalanlar). tek/hepsi --onay SERDAR_PIN_METIN ister. Token loga yazilmaz.
Kullanim: metricool_by_metin.py --token-dosya T.json --mod kuru|tek|hepsi --cikti DIR [--bas ISO] [--son ISO] [--onay KOD]"""
import argparse
import copy
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricool_pin_baslik import IZINLI_FARK, MC, TZ, YOK, fark, pin_durum, veri  # noqa: E402

ONAY = 'SERDAR_PIN_METIN'
DEGIS_METIN = [  # by78_pin_plan.py ACIKLAMA A/B/C (21 Eki onayi)
    ('Get it as a 5x7 digital card, an 8x10 digital file or a shipped 8x10 print.',
     'Get it as a 5x7 digital card or an 8x10 digital file.'),
    ('5 styles to choose from, as a 5x7 digital card, an 8x10 digital file or a shipped 8x10 print.',
     '5 styles to choose from, as a 5x7 digital card or an 8x10 digital file.'),
    ('Pick one of 5 styles and get it as a 5x7 digital card, an 8x10 digital file or a shipped 8x10 print.',
     'Pick one of 5 styles and get it as a 5x7 digital card or an 8x10 digital file.'),
    ('This personalized print joins', 'This personalized design joins'),
]
DEGIS_ALT = [('on a personalized 8x10 paper anniversary print and a 5x7 card',  # by78_pin_zamanla.py alt_metin
              'on a personalized 8x10 digital file and a 5x7 digital card')]
DEGIS_BASLIK = [(' Zodiac Paper Anniversary Print with Names', ' Zodiac Paper Anniversary Printable with Names'),
                (' Zodiac Print with Your Names and Date', ' Zodiac Printable with Your Names and Date')]
VAAT = re.compile(r'shipped 8x10 print|8x10 (?:paper anniversary )?print\b|shipped print|shipped to you|made and shipped|your print\b',
                  re.I)
TIRE = re.compile('[\\u2013\\u2014]')
BASLIK_AZAMI = 100
# Yalniz degisimden sonra 100'u asan basliklara (Serdar 22 Eki: "100'e kisaltilir, anlam korunur"): burc adlari zaten
# zodyak oldugunu soyler, "Zodiac" duser; "Printable with Names" kalir. Hala uzunsa UZUN (yazilmaz).
KISALT_BASLIK = [(' Zodiac Paper Anniversary Printable with Names', ' Paper Anniversary Printable with Names')]


def uygula(s, kurallar):
    for eski, yeni in kurallar:
        s = s.replace(eski, yeni)
    return s


def alanlar(p):
    pd = p.get('pinterestData') or {}
    return {'baslik': pd.get('pinTitle') or '', 'metin': p.get('text') or '', 'alt': list(p.get('mediaAltText') or [])}


def hedef_alanlar(a):
    baslik = uygula(a['baslik'], DEGIS_BASLIK)
    if len(baslik) > BASLIK_AZAMI and baslik != a['baslik']:
        baslik = uygula(baslik, KISALT_BASLIK)
    return {'baslik': baslik, 'metin': uygula(a['metin'], DEGIS_METIN),
            'alt': [uygula(x, DEGIS_ALT) for x in a['alt']]}


def satir(p):
    a = alanlar(p)
    h = hedef_alanlar(a)
    degisen = [k for k in a if a[k] != h[k]]
    kalan = sorted({m.group(0).lower() for k in ('baslik', 'metin') for m in VAAT.finditer(h[k])}
                   | {m.group(0).lower() for x in h['alt'] for m in VAAT.finditer(x)})
    if not degisen:
        islem = 'KALAN' if kalan else 'DOKUNULMAZ'  # bilinen kaliba uymayan vaat: yazilmaz, Serdar'a listelenir
    elif len(h['baslik']) > BASLIK_AZAMI:
        islem = 'UZUN'
    elif kalan or TIRE.search(h['baslik'] + h['metin'] + ''.join(h['alt'])):
        islem = 'KALAN'
    else:
        islem = 'DEGISECEK'
    pd = p.get('pinterestData') or {}
    return {'id': p.get('id'), 'uuid': p.get('uuid', ''), 'tarih': (p.get('publicationDate') or {}).get('dateTime', ''),
            'durum': pin_durum(p), 'pinLink': pd.get('pinLink', ''), 'degisen': '|'.join(degisen), 'kalan_vaat': '|'.join(kalan),
            'eski_baslik': a['baslik'], 'yeni_baslik': h['baslik'], 'yeni_baslik_uzunluk': len(h['baslik']),
            'eski_metin': a['metin'], 'yeni_metin': h['metin'], 'eski_alt': ' || '.join(a['alt']), 'yeni_alt': ' || '.join(h['alt']),
            'islem': islem, '_a': a, '_h': h}


def medya_adresleri(dugum, yol=''):
    """Gonderi govdesindeki tum http(s) adresleri (alan yolu ile)."""
    if isinstance(dugum, dict):
        for k, v in dugum.items():
            yield from medya_adresleri(v, f'{yol}.{k}' if yol else k)
    elif isinstance(dugum, list):
        for i, v in enumerate(dugum):
            yield from medya_adresleri(v, f'{yol}[{i}]')
    elif isinstance(dugum, str) and dugum.startswith(('http://', 'https://')):
        yield yol, dugum


def ag_ozet(p):
    return ','.join(sorted({(pr.get('network') or '').lower() for pr in p.get('providers') or []}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token-dosya', required=True)
    ap.add_argument('--mod', choices=['kuru', 'tek', 'hepsi'], required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--bas', default=datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00'))
    ap.add_argument('--son', default='2026-12-31T23:59:59')
    ap.add_argument('--onay', default='')
    a = ap.parse_args()
    if a.mod != 'kuru' and a.onay != ONAY:
        raise SystemExit(f'DUR: {a.mod} modu --onay {ONAY} ister')
    os.makedirs(a.cikti, exist_ok=True)
    mc = MC(json.load(open(a.token_dosya)))
    pencere = {'start': a.bas, 'end': a.son, 'timezone': TZ}

    liste = veri(mc.istek('GET', '/v2/scheduler/posts', pencere))
    if not isinstance(liste, list):
        raise SystemExit(f'DUR: beklenmeyen liste yaniti: {str(liste)[:200]}')
    json.dump(liste, open(os.path.join(a.cikti, 'HAM_LISTE.json'), 'w'), ensure_ascii=False, indent=1)

    # Drive kapatma on kosulu: tum gonderilerin medya hostlari (her ag, her durum)
    host_say, drive = {}, []
    for p in liste:
        for yol, url in medya_adresleri(p):
            h = urlparse(url).netloc.lower()
            if yol.startswith('pinterestData.pinLink') or 'etsy.com' in h:
                continue
            host_say[h] = host_say.get(h, 0) + 1
            if 'drive.google' in h or 'googleusercontent' in h or 'docs.google' in h:
                drive.append({'id': p.get('id'), 'tarih': (p.get('publicationDate') or {}).get('dateTime', ''),
                              'ag': ag_ozet(p), 'alan': yol, 'url': url})
    with open(os.path.join(a.cikti, 'MEDYA_HOST.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['host', 'adet'])
        for h, n in sorted(host_say.items(), key=lambda x: -x[1]):
            w.writerow([h, n])
    with open(os.path.join(a.cikti, 'MEDYA_DRIVE.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'tarih', 'ag', 'alan', 'url'], lineterminator='\n'); w.writeheader()
        w.writerows(drive)

    pinler = [p for p in liste if pin_durum(p) is not None]
    satirlar = [satir(p) for p in pinler]
    k = ['id', 'uuid', 'tarih', 'durum', 'pinLink', 'islem', 'degisen', 'kalan_vaat', 'eski_baslik', 'yeni_baslik',
         'yeni_baslik_uzunluk', 'eski_metin', 'yeni_metin', 'eski_alt', 'yeni_alt']
    with open(os.path.join(a.cikti, 'KURU_DENEME.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, lineterminator='\n', extrasaction='ignore'); w.writeheader()
        for r in sorted(satirlar, key=lambda r: r['tarih']):
            if r['islem'] != 'DOKUNULMAZ':
                w.writerow(r)
    say = {}
    for r in satirlar:
        if r['islem'] != 'DOKUNULMAZ':
            anahtar = f"{r['durum']}/{r['islem']}"
            say[anahtar] = say.get(anahtar, 0) + 1
    hedef = [r for r in satirlar if r['durum'] == 'PENDING' and r['islem'] == 'DEGISECEK']
    print(f"pencere {a.bas}..{a.son} | liste {len(liste)} gonderi, pinterest {len(pinler)} | {dict(sorted(say.items()))} | "
          f"hedef (PENDING+DEGISECEK) {len(hedef)} | medya host {len(host_say)}, Drive adresi {len(drive)}")
    if a.mod == 'kuru':
        return 0

    sec = sorted(hedef, key=lambda r: r['tarih'], reverse=True)
    if a.mod == 'tek':
        sec = sec[:1]
    k2 = ['id', 'yeni_id', 'tarih', 'degisen', 'sonuc', 'okunan_fark', 'diger_fark']
    t0, sonuc = time.time(), []
    with open(os.path.join(a.cikti, f'ONCE_SONRA_{a.mod}.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k2, lineterminator='\n', extrasaction='ignore'); w.writeheader()
        for i, r in enumerate(sec, 1):
            once = mc.istek('GET', f"/v2/scheduler/posts/{r['id']}", yok404=True)
            once = None if once is YOK or once is None else veri(once)
            if once is None or pin_durum(once) != 'PENDING' or alanlar(once) != r['_a']:
                sonuc.append(dict(r, sonuc='ATLANDI durum/metin degisti ya da yok'))
                w.writerow(sonuc[-1]); f.flush(); continue
            h = r['_h']
            yeni = copy.deepcopy(once)
            yeni['text'] = h['metin']
            if 'mediaAltText' in yeni:
                yeni['mediaAltText'] = h['alt']
            yeni.setdefault('pinterestData', {})['pinTitle'] = h['baslik']
            if mc.istek('PUT', f"/v2/scheduler/posts/{once['id']}", govde=yeni, yok404=True) is YOK:
                sonuc.append(dict(r, sonuc='ATLANDI PUT 404 (yayinlanmis olabilir)'))
                w.writerow(sonuc[-1]); f.flush(); continue
            sonra = mc.istek('GET', f"/v2/scheduler/posts/{once['id']}", yok404=True)
            if sonra is YOK or sonra is None:
                sonuc.append(dict(r, sonuc='ATLANDI PUT sonrasi bulunamadi'))
                w.writerow(sonuc[-1]); f.flush(); continue
            sonra = veri(sonra)
            okunan = alanlar(sonra)
            of = [x for x in okunan if okunan[x] != h[x]]
            tum = [x for x in fark(once, sonra) if x not in ('id', 'text', 'pinterestData.pinTitle')
                   and not x.startswith('mediaAltText')]
            df = [x for x in tum if x not in IZINLI_FARK]
            ok = not of and not df
            sonuc.append(dict(r, yeni_id=sonra.get('id'), okunan_fark='|'.join(of), diger_fark='|'.join(tum),
                              sonuc='PASS' if ok else 'FAIL'))
            w.writerow(sonuc[-1]); f.flush()
            g = time.time() - t0
            print(f"[{i}/{len(sec)}] {r['id']} {sonuc[-1]['sonuc']} | gecen {g:.0f} sn, kalan ~{g / i * (len(sec) - i):.0f} sn, "
                  f"%{100 * i / len(sec):.0f}" + (f' fark: {of + df}' if not ok else ''), flush=True)
            if not ok:
                raise SystemExit(f"DUR: dogrulama FAIL {r['id']} (alan={of}, diger={df})")
    n = sum(s['sonuc'] == 'PASS' for s in sonuc)
    print(f'DEGISEN {n}/{len(sec)} PASS, atlanan {sum(s["sonuc"].startswith("ATLANDI") for s in sonuc)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
