#!/usr/bin/env python3
"""BY78 dikey pin zamanlama (14 Eki 2026). Etsy API KULLANILMAZ.
mod=kuru  : BY78_TASLAKLAR.csv (cift, listing_id) -> PIN_PLAN_BY78.csv link = https://www.etsy.com/listing/<id>;
            78 Metricool istegi ISTEKLER.json'a yazilir (gorsel = Drive PIN_BY78_V1/<CIFT>.jpg). Metricool'a HIC istek yok.
mod=gonder: YALNIZ Takip/Serdar acik onayiyla. Ayni istekler: gorsel Metricool S3'e (planner) yuklenir, POST
            /v2/scheduler/posts; her satirin sonucu GONDERIM.csv'ye aninda yazilir. Tekrar kosuda --onceki GONDERIM.csv'de
            YAZILDI/ZATEN_VAR olan ya da Metricool'da ayni saat + ayni link ile bulunan pin ATLANIR. POST yeniden denenmez.
            Sonunda liste ucundan geri okunup baslik/pano/link/metin/durum dogrulanir.
Kontroller (iki modda): 78 satir, taslak asama=tamam, 78 farkli link, listing_id yalniz rakam, gorsel Drive'da var, tarih_saat gelecekte
(Europe/Istanbul, simdi + 30 dk), V6 plani ile ayni dakikada pin yok, uzun/orta tire yok.
Kullanim: by78_pin_zamanla.py --mod kuru|gonder --plan P.csv --taslak T.csv --pin-liste PIN.json --v6 V6.csv --cikti DIR
          [--token-dosya MC.json --pin-dir DIR --onceki GONDERIM.csv --adet N]"""
import argparse
import csv
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
BOARD = '839358517992010910'
TZ = 'Europe/Istanbul'
ALANLAR = ['cift', 'gorsel', 'baslik', 'aciklama', 'board', 'tarih_saat', 'link']


def yukle_mod(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(D, dosya))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def alt_metin(c):
    a, b = (s.capitalize() for s in c.split('_'))
    return (f'{a} and {b} shared zodiac symbol on a personalized 8x10 paper anniversary print and a 5x7 card, '
            f'1st anniversary gift by AstroLoveArt')


def govde(r, medya_url):
    return {'publicationDate': {'dateTime': r['tarih_saat'].replace(' ', 'T') + ':00', 'timezone': TZ},
            'text': r['aciklama'], 'firstCommentText': '', 'providers': [{'network': 'pinterest'}],
            'media': [medya_url], 'mediaAltText': [alt_metin(r['cift'])], 'autoPublish': True,
            'saveExternalMediaFiles': False, 'shortener': False, 'draft': False,
            'pinterestData': {'boardId': BOARD, 'pinTitle': r['baslik'], 'pinLink': r['link'], 'pinNewFormat': False}}


def kontrol(plan, taslak, pin_adlari, v6):
    hata = []
    ids = {}
    for t in taslak:
        c, lid = (t.get('cift') or '').strip().upper(), (t.get('listing_id') or '').strip()
        if not lid.isdigit():
            hata.append(f'{c}: listing_id rakam degil {lid!r}')
        if 'asama' in t and (t.get('asama') or '').strip() != 'tamam':
            hata.append(f"{c}: taslak asamasi {t.get('asama')!r} (tamam olmali)")
        if c in ids and ids[c] != lid:
            hata.append(f'{c}: iki farkli listing_id')
        ids[c] = lid
    if len(plan) != 78:
        hata.append(f'plan {len(plan)} satir (78 olmali)')
    eksik = [r['cift'] for r in plan if r['cift'] not in ids]
    if eksik:
        hata.append(f'BY78_TASLAKLAR.csv icinde olmayan {len(eksik)} cift: {eksik[:5]}')
    fazla = sorted(set(ids) - {r['cift'] for r in plan})
    if fazla:
        hata.append(f'planda olmayan taslak cift: {fazla[:5]}')
    for r in plan:
        if r['cift'] in ids and ids[r['cift']].isdigit():
            r['link'] = f"https://www.etsy.com/listing/{ids[r['cift']]}"
        r['board'] = BOARD
        r['gorsel'] = f"PIN_BY78_V1/{r['cift']}.jpg"
    linkler = [r['link'] for r in plan if r.get('link')]
    if len(linkler) != 78 or len(set(linkler)) != 78:
        hata.append(f'link {len(linkler)}, farkli {len(set(linkler))} (78/78 olmali)')
    yok = [r['cift'] for r in plan if f"{r['cift']}.jpg" not in pin_adlari]
    if yok:
        hata.append(f'Drive PIN_BY78_V1 icinde olmayan gorsel {len(yok)}: {yok[:5]}')
    sinir = simdi_ist() + timedelta(minutes=30)
    gecmis = [r['tarih_saat'] for r in plan if datetime.fromisoformat(r['tarih_saat']) < sinir]
    if gecmis:
        hata.append(f'gecmiste ya da 30 dk icinde {len(gecmis)} pin: {gecmis[:3]}')
    v6_dk = {x['tarih_saat'][:16] for x in v6}
    ayni = [r['tarih_saat'] for r in plan if r['tarih_saat'][:16] in v6_dk]
    if ayni:
        hata.append(f'V6 ile ayni saatte {len(ayni)} pin: {ayni[:3]}')
    for r in plan:
        for alan in ('baslik', 'aciklama'):
            if '—' in r[alan] or '–' in r[alan]:
                hata.append(f"{r['cift']} {alan}: uzun/orta tire")
        if len(r['baslik']) > 100 or len(r['aciklama']) > 500:
            hata.append(f"{r['cift']}: baslik/aciklama uzun")
    return hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mod', choices=['kuru', 'gonder'], default='kuru')
    for k in ('plan', 'taslak', 'pin-liste', 'v6', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--token-dosya'); ap.add_argument('--pin-dir'); ap.add_argument('--onceki')
    ap.add_argument('--adet', type=int, default=0, help='gonder: en fazla bu kadar YENI pin (0 = hepsi)')
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    plan = list(csv.DictReader(open(a.plan, encoding='utf-8')))
    taslak = list(csv.DictReader(open(a.taslak, encoding='utf-8-sig')))
    pin_adlari = {x['Name'] for x in json.load(open(a.pin_liste))}
    v6 = list(csv.DictReader(open(a.v6, encoding='utf-8')))
    hata = kontrol(plan, taslak, pin_adlari, v6)
    print(f"KONTROL {'PASS' if not hata else 'FAIL'}: plan {len(plan)}, taslak {len(taslak)}, Drive pin {len(pin_adlari)}, "
          f"V6 {len(v6)}; ilk {plan[0]['tarih_saat'] if plan else '-'}, son {plan[-1]['tarih_saat'] if plan else '-'}"
          + ''.join('\n  ' + h for h in hata[:15]), flush=True)
    with open(os.path.join(a.cikti, 'PIN_PLAN_BY78.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(plan)
    istekler = [dict(cift=r['cift'], gorsel=r['gorsel'], govde=govde(r, f"<S3:{r['gorsel']}>")) for r in plan]
    json.dump(istekler, open(os.path.join(a.cikti, 'ISTEKLER.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'ISTEKLER {len(istekler)} (board {BOARD}); ornek: {json.dumps(istekler[0]["govde"], ensure_ascii=False)[:400]}', flush=True)
    if hata:
        sys.exit(1)
    if a.mod == 'kuru':
        print('KURU: Metricool istegi YOK, gonderim YOK.')
        return

    # --- gonder (yalniz acik onayla) ---
    if not (a.token_dosya and a.pin_dir):
        sys.exit('DUR: gonder icin --token-dosya ve --pin-dir gerekli')
    mpb = yukle_mod('mpb', 'metricool_pin_baslik.py')
    y5 = yukle_mod('y5', 'metricool_5p_yaz.py')
    v6y = yukle_mod('v6y', 'metricool_pin_v6_yaz.py')
    mc = mpb.MC(json.load(open(a.token_dosya)))
    onceki = {}
    if a.onceki and os.path.exists(a.onceki):
        onceki = {r['cift']: r for r in csv.DictReader(open(a.onceki, encoding='utf-8')) if r.get('sonuc') in ('YAZILDI', 'ZATEN_VAR')}
    bas = datetime.fromisoformat(plan[0]['tarih_saat'][:10])
    gun = (datetime.fromisoformat(max(r['tarih_saat'] for r in plan)[:10]) - bas).days + 2

    def mevcut():
        return {(p['publicationDate']['dateTime'][:16], (p.get('pinterestData') or {}).get('pinLink')): p
                for p in v6y.liste(mc, bas, gun) if v6y.aglar(p) == ['pinterest']}
    var = mevcut()
    k = ['cift', 'tarih_saat', 'link', 'gorsel', 'medya_url', 'id', 'sonuc', 'not']
    yol = os.path.join(a.cikti, 'GONDERIM.csv')
    t0, yeni = time.time(), 0
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, extrasaction='ignore', lineterminator='\n'); w.writeheader()
        for i, r in enumerate(plan, 1):
            ak = (r['tarih_saat'].replace(' ', 'T'), r['link'])
            if r['cift'] in onceki:
                s = dict(onceki[r['cift']], sonuc=onceki[r['cift']]['sonuc'], **{'not': 'onceki kosuda gonderildi'})
            elif ak in var:
                s = dict(r, id=var[ak].get('id'), sonuc='ZATEN_VAR', **{'not': 'Metricool listesinde ayni saat+link'})
            elif a.adet and yeni >= a.adet:
                s = dict(r, sonuc='BEKLIYOR', **{'not': f'--adet {a.adet} siniri'})
            elif datetime.fromisoformat(r['tarih_saat']) < simdi_ist() + timedelta(minutes=10):
                s = dict(r, sonuc='ATLANDI', **{'not': 'yayin saati gecmis/cok yakin'})
            else:
                url, _ = y5.video_yukle(mc, os.path.join(a.pin_dir, f"{r['cift']}.jpg"), 'image/jpeg', 'jpg')
                y = mpb.veri(mc.istek('POST', '/v2/scheduler/posts', govde=govde(r, url)))
                s = dict(r, medya_url=url, id=(y or {}).get('id') if isinstance(y, dict) else '', sonuc='YAZILDI')
                yeni += 1
            w.writerow(s); f.flush()
            g = time.time() - t0
            if i % 10 == 0 or i == len(plan) or s['sonuc'] == 'YAZILDI' and yeni <= 1:
                print(f"[{i}/{len(plan)}] {r['tarih_saat']} {r['cift']} {s['sonuc']} | yeni {yeni} | gecen {g:.0f} sn, "
                      f"kalan ~{g / i * (len(plan) - i):.0f} sn, %{100 * i / len(plan):.0f}", flush=True)
    sonuc = list(csv.DictReader(open(yol, encoding='utf-8')))
    var = mevcut()
    hata = []
    for r, s in zip(plan, sonuc):
        if s['sonuc'] not in ('YAZILDI', 'ZATEN_VAR'):
            continue
        p = var.get((r['tarih_saat'].replace(' ', 'T'), r['link']))
        if p is None:
            hata.append(f"{r['cift']}: Metricool listesinde yok"); continue
        pd = p.get('pinterestData') or {}
        for ad, b, o in (('baslik', r['baslik'], pd.get('pinTitle')), ('pano', BOARD, str(pd.get('boardId'))),
                         ('link', r['link'], pd.get('pinLink')), ('aciklama', r['aciklama'], p.get('text')),
                         ('ag', ['pinterest'], v6y.aglar(p))):
            if b != o:
                hata.append(f"{r['cift']} {ad}: {str(o)[:60]!r}")
    say = {x: sum(1 for s in sonuc if s['sonuc'] == x) for x in ('YAZILDI', 'ZATEN_VAR', 'BEKLIYOR', 'ATLANDI')}
    print(f'GONDERIM {say}; DOGRULAMA {"PASS" if not hata else "FAIL"}' + ''.join('\n  ' + h for h in hata[:10]), flush=True)
    sys.exit(0 if not hata else 5)


if __name__ == '__main__':
    main()
