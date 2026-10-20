#!/usr/bin/env python3
"""Pinterest pin degisimi ENVANTER + ESLEME (20 Eki 2026). SALT OKUMA: Metricool'a YAZMA YOK, yalniz GET.
1) /v2/scheduler/posts (simdi -> UFUK, 5 gunluk pencereler): Pinterest saglayicisi PENDING ve yayini simdiden sonra olan
   gonderiler: id, uuid, tarih, pano, baslik, link (Etsy ilan kimligi), mevcut medya URL'si, alt metin.
2) Aile ve cift ilan kimliginden: poster = data/pod/pod78_ids.csv + V6 plan linkleri + PIN_V2 dosya adlari;
   yildonumu = BY78_TASLAKLAR.csv; kupa = KUPA_TASLAK_LISTE.csv. Hicbirinde yoksa aile "bilinmiyor".
3) Yeni pin: poster -> PIN_V2/PIN/<ilan>_<CIFT>.jpg; yildonumu -> KAPAK_Y1/PIN/<CIFT>_PIN.jpg; kupa -> yeni pin yok.
Cikti: ESLEME.csv, BEKLEYEN.csv, KULLANILMAYAN_PIN.csv, OZET.txt, HAM_scheduler_*.json, HAM_boards.json.
Kullanim: pin_degisim_envanter.py TOKEN.json CIKTI --poster-pin LS.json --y1-pin LS.json --by78 T.csv --kupa K.csv
          --pod78 data/pod/pod78_ids.csv --v6 PIN_METIN_234_LINKLI.csv"""
import argparse
import csv
import importlib.util
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
UFUK = datetime(2027, 2, 1)
BURC = r'Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces'


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v or []


def ilan(u):
    m = re.search(r'/listing(?:-editor/edit)?/(\d+)', u or '')
    return m.group(1) if m else ''


def csv_oku(yol):
    return list(csv.DictReader(open(yol, encoding='utf-8-sig'))) if yol and os.path.exists(yol) else []


def baslik_cift(b):
    z = re.findall(BURC, b or '', flags=re.I)
    return '_'.join(sorted(x.upper() for x in z[:2])) if len(z) >= 2 else ''


def yaz(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('poster-pin', 'y1-pin', 'by78', 'kupa', 'pod78', 'v6'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    tok = json.load(open(a.token))
    mc = mpb.MC(tok)
    simdi = datetime.now(IST)
    print(f'OKUMA ANI: {simdi:%Y-%m-%dT%H:%M:%S%z}; blogId {mc.b}; ufuk {UFUK:%Y-%m-%d}')

    # --- aile kaynaklari (ilan -> (aile, cift))
    aile = {}
    kay = Counter()
    for r in csv_oku(a.pod78):
        aile[r['listing_id'].strip()] = ('poster', r['cift'].strip().upper()); kay['poster:pod78_ids'] += 1
    for r in csv_oku(a.v6):
        i = ilan(r.get('etsy_link'))
        if i:
            aile.setdefault(i, ('poster', r['cift_anahtari'].strip().upper())); kay['poster:v6_link'] += 1
    poster_pin, y1_pin = {}, {}
    for f in json.load(open(a.poster_pin)) if a.poster_pin and os.path.exists(a.poster_pin) else []:
        m = re.fullmatch(r'(\d+)_([A-Z]+_[A-Z]+)\.jpg', f.get('Name', ''))
        if m:
            poster_pin[m.group(1)] = (m.group(2), f['Name'])
            aile.setdefault(m.group(1), ('poster', m.group(2))); kay['poster:pin_v2_dosya'] += 1
    for f in json.load(open(a.y1_pin)) if a.y1_pin and os.path.exists(a.y1_pin) else []:
        m = re.fullmatch(r'([A-Z]+_[A-Z]+)_PIN\.jpg', f.get('Name', ''))
        if m:
            y1_pin[m.group(1)] = f['Name']
    celiski = []
    for ad, yol, k in (('yildonumu', a.by78, 'listing_id'), ('kupa', a.kupa, 'listing_id')):
        for r in csv_oku(yol):
            i = (r.get(k) or '').strip()
            if not i:
                continue
            if i in aile and aile[i][0] != ad:
                celiski.append((i, aile[i][0], ad))
            aile[i] = (ad, r['cift'].strip().upper()); kay[f'{ad}:{os.path.basename(yol)}'] += 1
    print(f'AILE KAYNAKLARI: {dict(kay)}; ilan {len(aile)}; aileler arasi celiski {len(celiski)}')
    print(f'YENI PIN: poster PIN_V2 {len(poster_pin)}, yildonumu Y1 {len(y1_pin)}')

    # --- panolar + zamanlayici
    try:
        bj = mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b})
    except SystemExit as e:
        bj = {'_hata': str(e)[:300]}
    json.dump(bj, open(os.path.join(out, 'HAM_boards.json'), 'w'), ensure_ascii=False, indent=1)
    pano = {str(b.get('id')): b.get('name') or '' for b in liste(bj)}
    ps, t, son_dolu = {}, datetime(simdi.year, simdi.month, simdi.day), None
    while t < UFUK:
        e = min(t + timedelta(days=5), UFUK)
        try:
            j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        except SystemExit as ex:
            j = {'_hata': str(ex)[:300]}; print(f'SCHEDULER {t:%Y-%m-%d}: HATA {str(ex)[:150]}')
        json.dump(j, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
        n = 0
        for p in liste(j):
            if mpb.pin_durum(p) is not None:
                ps[str(p.get('uuid') or p.get('id'))] = p; n += 1
        if n:
            son_dolu = t
        t = e
    print(f'SCHEDULER Pinterest gonderi (bugun - ufuk): {len(ps)}; son dolu pencere {son_dolu:%Y-%m-%d}' if son_dolu else 'SCHEDULER: Pinterest gonderisi yok')

    gelecek, durumlar = [], Counter()
    for p in ps.values():
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        try:
            z = datetime.fromisoformat(zt).replace(tzinfo=IST)
        except ValueError:
            continue
        if z <= simdi:
            continue
        durumlar[mpb.pin_durum(p)] += 1
        if mpb.pin_durum(p) == 'PENDING':
            gelecek.append((zt, p))
    gelecek.sort(key=lambda x: x[0])
    print(f'GELECEK Pinterest durumlari: {dict(durumlar)}; PENDING {len(gelecek)}')

    # --- esleme
    bek, es, kullanilan = [], [], set()
    for zt, p in gelecek:
        pd = p.get('pinterestData') or {}
        md = p.get('media') or ['']
        md = [m.get('url') if isinstance(m, dict) else m for m in md]
        lk = pd.get('pinLink') or ''
        i = ilan(lk)
        af, cf = aile.get(i, ('bilinmiyor', ''))
        bc = baslik_cift(pd.get('pinTitle'))
        yeni, durum, neden = '', 'eslesmedi', ''
        if af == 'poster':
            if i in poster_pin:
                yeni, durum = poster_pin[i][1], 'eslesti'
                if poster_pin[i][0] != cf:
                    neden = f'dosya cifti {poster_pin[i][0]} != ilan cifti {cf}'
            else:
                neden = 'PIN_V2 icinde bu ilan kimligi yok'
        elif af == 'yildonumu':
            if cf in y1_pin:
                yeni, durum = y1_pin[cf], 'eslesti'
            else:
                neden = 'KAPAK_Y1 PIN icinde bu cift yok'
        elif af == 'kupa':
            durum, neden = 'kupa', 'yeni pin yok; ayri karar'
        else:
            neden = 'ilan kimligi aile listelerinde yok' if i else 'linkte Etsy ilan kimligi yok'
        if bc and cf and bc != cf:
            neden = (neden + '; ' if neden else '') + f'baslik cifti {bc} != ilan cifti {cf}'
        if yeni:
            kullanilan.add((af, yeni))
        sat = [p.get('id'), p.get('uuid', ''), zt, (p.get('publicationDate') or {}).get('timezone', ''), af, cf, i,
               str(pd.get('boardId') or ''), pano.get(str(pd.get('boardId')), ''), pd.get('pinTitle') or '', lk,
               md[0] if md else '', len([m for m in md if m]), 'evet' if any(p.get('mediaAltText') or []) else 'hayir']
        bek.append(sat)
        es.append([p.get('id'), p.get('uuid', ''), zt, af, cf, md[0] if md else '', yeni, durum, neden])
    yaz(out, 'BEKLEYEN.csv', ['gonderi_id', 'uuid', 'tarih', 'tz', 'aile', 'cift', 'ilan_id', 'pano_id', 'pano', 'baslik', 'link',
                              'mevcut_medya', 'medya_sayisi', 'alt_metin'], bek)
    yaz(out, 'ESLEME.csv', ['gonderi_id', 'uuid', 'tarih', 'aile', 'cift', 'eski_medya', 'yeni_pin_dosyasi', 'durum', 'not'], es)
    kul = [['poster', f[1], ilan_, f[0]] for ilan_, f in sorted(poster_pin.items()) if ('poster', f[1]) not in kullanilan]
    kul += [['yildonumu', f, '', c] for c, f in sorted(y1_pin.items()) if ('yildonumu', f) not in kullanilan]
    yaz(out, 'KULLANILMAYAN_PIN.csv', ['aile', 'dosya', 'ilan_id', 'cift'], kul)

    # --- ozet
    o = [f'Okuma: {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul), blogId {mc.b}, ufuk {UFUK:%Y-%m-%d}, uc /v2/scheduler/posts (GET)',
         f'Gelecek Pinterest gonderileri durum: {dict(durumlar)}',
         f'Bekleyen (PENDING, simdiden sonra): {len(es)}; ilk {es[0][2] if es else "-"}, son {es[-1][2] if es else "-"}']
    for af in ('poster', 'yildonumu', 'kupa', 'bilinmiyor'):
        R = [r for r in es if r[3] == af]
        if R:
            o.append(f'  {af}: {len(R)} gonderi; durum {dict(Counter(r[7] for r in R))}; cift {len({r[4] for r in R})}; '
                     f'gonderi/cift {dict(Counter(Counter(r[4] for r in R).values()))}')
    o.append(f'Pano dagilimi: {dict(Counter((r[4], r[8]) for r in bek))}')
    o.append(f'Eslesmeyen: {sum(1 for r in es if r[7] == "eslesmedi")}; kupa: {sum(1 for r in es if r[7] == "kupa")}; '
             f'notlu: {sum(1 for r in es if r[8] and r[7] == "eslesti")}')
    for r in [r for r in es if r[7] == 'eslesmedi'][:40]:
        o.append(f'  ESLESMEDI {r[2]} {r[3]} {r[4]} id {r[0]}: {r[8]}')
    o.append(f'Kullanilmayan yeni pin: poster {sum(1 for x in kul if x[0] == "poster")}/{len(poster_pin)}, '
             f'yildonumu {sum(1 for x in kul if x[0] == "yildonumu")}/{len(y1_pin)}')
    host = Counter(re.sub(r'^https?://([^/]+)/.*$', r'\1', r[11] or '-') for r in bek)
    o.append(f'Mevcut medya host dagilimi: {dict(host)}')
    o.append(f'Aileler arasi ilan celiskisi: {len(celiski)} {celiski[:5]}')
    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o))


if __name__ == '__main__':
    main()
