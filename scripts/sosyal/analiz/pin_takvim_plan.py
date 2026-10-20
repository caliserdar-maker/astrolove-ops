#!/usr/bin/env python3
"""Pinterest yeni takvim PLANI (Serdar karari 20 Eki 2026): gunde 1 poster + 1 yil donumu + 1 kupa. SALT OKUMA / PLAN:
Metricool'a YAZMA YOK, yalniz GET (/v2/scheduler/posts, /v2/scheduler/boards/pinterest).
1) Bekleyen Pinterest gonderileri (PENDING, simdiden sonra): tarih, saat, id, uuid, pano, baslik, link, aile, cift.
   Aile ilan kimliginden: poster = data/pod/pod78_ids.csv, yil donumu = BY78_TASLAKLAR.csv, kupa = KUPA_TASLAK_LISTE.csv.
2) Plan (BAS = 22 Eki): BAS'tan onceki pinler yerinde kalir. Aile basina mevcut sira (tarih, saat) korunur;
   yeni_gun = max(eski_gun, ayni ailenin onceki pininin yeni_gun + 1, BAS); one cekme yok, gunde aile basina en fazla 1.
   Kuyruk sonuna: yil donumu 12 yeni pin (KULLANILMAYAN_PIN.csv, cift alfabetik), kupa 78 yer (pin dosyasi yok, cift alfabetik,
   BAS'tan gunde 1). Saat: aile basina bekleyen pinlerde en sik saat; kupa = diger iki aileninkinden farkli en sik saat.
3) Pano: poster ve yil donumu mevcut panosunda; yeni yil donumu pinleri yil donumu pinlerinin en sik panosuna;
   kupa sirayla "Zodiac Couple Mugs" (yoksa ONERI, olusturma ayri onay) / "Personalized Couple Gifts".
Cikti: PLAN.csv, OZET.txt, HAM_scheduler_*.json, HAM_boards.json
Kullanim: pin_takvim_plan.py TOKEN.json OUT --pod78 P.csv --by78 B.csv --kupa K.csv --kullanilmayan U.csv"""
import argparse
import csv
import importlib.util
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
UFUK = datetime(2027, 2, 1)
BAS = date(2026, 10, 22)
AILELER = ('poster', 'yildonumu', 'kupa')
KUPA_PANO = ('Zodiac Couple Mugs', 'Personalized Couple Gifts')


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


def yaz(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def oku(mc, out, simdi):
    try:
        bj = mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b})
    except SystemExit as e:
        bj = {'_hata': str(e)[:300]}
    json.dump(bj, open(os.path.join(out, 'HAM_boards.json'), 'w'), ensure_ascii=False, indent=1)
    pano = {str(b.get('id')): b.get('name') or '' for b in liste(bj)}
    ps, t = {}, datetime(simdi.year, simdi.month, simdi.day)
    while t < UFUK:
        e = min(t + timedelta(days=5), UFUK)
        j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        json.dump(j, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
        for p in liste(j):
            if mpb.pin_durum(p) is not None:
                ps[str(p.get('uuid') or p.get('id'))] = p
        t = e
    return pano, ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('pod78', 'by78', 'kupa', 'kullanilmayan', 'sahte'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    simdi = datetime.now(IST)
    if a.sahte:
        pano, ps = json.load(open(a.sahte)).values()
    else:
        mc = mpb.MC(json.load(open(a.token)))
        pano, ps = oku(mc, out, simdi)

    aile, kupa_ilan, by_ilan = {}, {}, {}
    for r in csv_oku(a.pod78):
        aile[r['listing_id'].strip()] = ('poster', r['cift'].strip().upper())
    for r in csv_oku(a.by78):
        if (r.get('listing_id') or '').strip():
            aile[r['listing_id'].strip()] = ('yildonumu', r['cift'].strip().upper()); by_ilan[r['cift'].strip().upper()] = r['listing_id'].strip()
    for r in csv_oku(a.kupa):
        if (r.get('listing_id') or '').strip():
            aile[r['listing_id'].strip()] = ('kupa', r['cift'].strip().upper()); kupa_ilan[r['cift'].strip().upper()] = r['listing_id'].strip()

    # 1) bekleyen
    bek, durumlar = [], Counter()
    for p in ps.values():
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        try:
            z = datetime.fromisoformat(zt).replace(tzinfo=IST)
        except ValueError:
            continue
        if z <= simdi:
            continue
        durumlar[mpb.pin_durum(p)] += 1
        if mpb.pin_durum(p) != 'PENDING':
            continue
        pd = p.get('pinterestData') or {}
        af, cf = aile.get(ilan(pd.get('pinLink')), ('bilinmiyor', ''))
        md = [m.get('url') if isinstance(m, dict) else m for m in p.get('media') or []]
        bek.append(dict(z=z, id=p.get('id'), uuid=str(p.get('uuid') or ''), aile=af, cift=cf, pano_id=str(pd.get('boardId') or ''),
                        pano=pano.get(str(pd.get('boardId')), ''), baslik=pd.get('pinTitle') or '', link=pd.get('pinLink') or '',
                        medya=md[0] if md else ''))
    bek.sort(key=lambda r: (r['z'], r['aile']))
    print(f'OKUMA {simdi:%Y-%m-%d %H:%M} Istanbul; gelecek Pinterest durum {dict(durumlar)}; PENDING {len(bek)}; '
          f'aile {dict(Counter(r["aile"] for r in bek))}')

    # saat duzeni
    saat_say = {f: Counter(r['z'].strftime('%H:%M') for r in bek if r['aile'] == f) for f in AILELER}
    tum_saat = Counter(r['z'].strftime('%H:%M') for r in bek)
    saat = {f: (saat_say[f].most_common(1)[0][0] if saat_say[f] else None) for f in ('poster', 'yildonumu')}
    saat['kupa'] = next((s for s, _ in tum_saat.most_common() if s not in saat.values()), '21:00')
    for f in ('poster', 'yildonumu'):
        saat[f] = saat[f] or next(s for s, _ in tum_saat.most_common() if s not in saat.values())

    # 2) plan
    plan, son = [], {}
    for r in bek:
        f, g = r['aile'], r['z'].date()
        if f not in AILELER or g < BAS:
            plan.append(dict(r, yeni_gun=g, yeni_saat=r['z'].strftime('%H:%M'), islem='YERINDE (22 Eki oncesi)' if g < BAS else 'YERINDE (aile bilinmiyor)',
                             kaynak='mevcut'))
            continue
        yg = max(g, BAS, son.get(f, BAS - timedelta(days=1)) + timedelta(days=1))
        son[f] = yg
        plan.append(dict(r, yeni_gun=yg, yeni_saat=saat[f], islem='KAYDIR' if (yg, saat[f]) != (g, r['z'].strftime('%H:%M')) else 'AYNI',
                         kaynak='mevcut'))
    y_pano = Counter(r['pano'] for r in bek if r['aile'] == 'yildonumu').most_common(1)
    y_pano = y_pano[0][0] if y_pano else '1st Anniversary Gift Ideas'
    yeni_y = sorted(csv_oku(a.kullanilmayan), key=lambda r: r['cift'])
    for r in yeni_y:
        c = r['cift'].strip().upper()
        yg = son.get('yildonumu', BAS - timedelta(days=1)) + timedelta(days=1); son['yildonumu'] = yg
        lid = by_ilan.get(c, '')
        plan.append(dict(z=None, id='', uuid='', aile='yildonumu', cift=c, pano_id='', pano=y_pano, baslik='',
                         link=f'https://www.etsy.com/listing/{lid}' if lid else 'ilan kimligi yok', medya=f"KAPAK_Y1_78_20261019/PIN/{r['dosya']}",
                         yeni_gun=yg, yeni_saat=saat['yildonumu'], islem='YENI (planda olmayan yil donumu pini)', kaynak='KULLANILMAYAN_PIN.csv'))
    var_pano = set(pano.values())
    for i, c in enumerate(sorted(kupa_ilan)):
        yg = son.get('kupa', BAS - timedelta(days=1)) + timedelta(days=1); son['kupa'] = yg
        pn = KUPA_PANO[i % 2]
        plan.append(dict(z=None, id='', uuid='', aile='kupa', cift=c, pano_id='', pano=pn + ('' if pn in var_pano else ' (ONERI: yeni pano)'),
                         baslik='', link=f'https://www.etsy.com/listing/{kupa_ilan[c]}', medya='YOK (kupa pini henuz uretilmedi)',
                         yeni_gun=yg, yeni_saat=saat['kupa'], islem='YENI YER (kupa)', kaynak='KUPA_TASLAK_LISTE.csv'))
    plan.sort(key=lambda r: (r['yeni_gun'], r['yeni_saat'], AILELER.index(r['aile']) if r['aile'] in AILELER else 9))

    yaz(out, 'PLAN.csv', ['yeni_tarih', 'yeni_saat', 'aile', 'cift', 'islem', 'eski_tarih_saat', 'kaydirma_gun', 'gonderi_id', 'uuid',
                          'pano', 'pano_id', 'baslik', 'link', 'medya', 'kaynak'],
        [[str(r['yeni_gun']), r['yeni_saat'], r['aile'], r['cift'], r['islem'], r['z'].strftime('%Y-%m-%d %H:%M') if r['z'] else '',
          (r['yeni_gun'] - r['z'].date()).days if r['z'] else '', r['id'], r['uuid'], r['pano'], r['pano_id'], r['baslik'], r['link'],
          r['medya'], r['kaynak']] for r in plan])

    # dogrulama + ozet
    gun_aile = Counter((r['yeni_gun'], r['aile']) for r in plan if r['yeni_gun'] >= BAS)
    ihlal = [k for k, v in gun_aile.items() if v > 1]
    sira_ok = all([r['uuid'] for r in sorted([x for x in plan if x['aile'] == f and x['z'] and x['z'].date() >= BAS],
                                             key=lambda x: x['yeni_gun'])]
                  == [r['uuid'] for r in sorted([x for x in bek if x['aile'] == f and x['z'].date() >= BAS], key=lambda x: x['z'])]
                  for f in ('poster', 'yildonumu'))
    eksik = len(bek) - sum(1 for r in plan if r['kaynak'] == 'mevcut')
    gunler = sorted({r['yeni_gun'] for r in plan if r['yeni_gun'] >= BAS})
    bitis = {f: max([r['yeni_gun'] for r in plan if r['aile'] == f] or [None], key=lambda x: x or date.min) for f in AILELER}
    gun_say = Counter(r['yeni_gun'] for r in plan if r['yeni_gun'] >= BAS)
    dag = Counter(tuple(gun_aile.get((g, f), 0) for f in AILELER) for g in gunler)
    o = [f'Okuma: {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul), blogId 6974606, GET /v2/scheduler/posts + /v2/scheduler/boards/pinterest; Metricool yazma YOK',
         f'Bekleyen Pinterest (PENDING, simdiden sonra): {len(bek)}; aile {dict(Counter(r["aile"] for r in bek))}; '
         f'ilk {bek[0]["z"]:%Y-%m-%d %H:%M} son {bek[-1]["z"]:%Y-%m-%d %H:%M}' if bek else 'Bekleyen yok',
         f'Mevcut gunluk yogunluk (BAS ve sonrasi, gun basina pin): {dict(Counter(Counter(r["z"].date() for r in bek if r["z"].date() >= BAS).values()))}',
         f'Mevcut saat dagilimi: {dict(tum_saat.most_common())}',
         f'Plan saatleri (en sik saat kurali): poster {saat["poster"]}, yil donumu {saat["yildonumu"]}, kupa {saat["kupa"]}',
         f'Plan: {len(plan)} satir = mevcut {len(bek)} + yeni yil donumu {len(yeni_y)} + kupa yeri {len(kupa_ilan)}; '
         f'22 Eki oncesi yerinde {sum(1 for r in plan if str(r["islem"]).startswith("YERINDE (22"))}',
         f'Islem: {dict(Counter(str(r["islem"]).split(" (")[0] for r in plan))}',
         f'Bitis: poster {bitis["poster"]}, yil donumu {bitis["yildonumu"]}, kupa {bitis["kupa"]}; plan sonu {max(gunler) if gunler else "-"}',
         f'Gun basina (poster, yil donumu, kupa) dagilimi: {dict(sorted(dag.items(), key=lambda x: -x[1]))}',
         f'Gun basina toplam pin: {dict(sorted(Counter(gun_say.values()).items()))}',
         f'Kontrol: gun x aile > 1 ihlal {len(ihlal)}; mevcut sira korundu {sira_ok}; planda olmayan mevcut pin {eksik}; '
         f'one cekilen {sum(1 for r in plan if r["z"] and r["yeni_gun"] < r["z"].date())}',
         f'En buyuk kaydirma: poster {max([(r["yeni_gun"] - r["z"].date()).days for r in plan if r["aile"] == "poster" and r["z"]] or [0])} gun, '
         f'yil donumu {max([(r["yeni_gun"] - r["z"].date()).days for r in plan if r["aile"] == "yildonumu" and r["z"]] or [0])} gun',
         f'Panolar (Metricool): {sorted(var_pano)}',
         f'Pano dagilimi (plan): {dict(Counter((r["aile"], r["pano"]) for r in plan))}',
         f'Kupa panosu: "{KUPA_PANO[0]}" ' + ('VAR' if KUPA_PANO[0] in var_pano else 'YOK -> olusturma uygulama asamasinda, ayri onay')
         + f'; kupa linki olmayan cift {sum(1 for c in kupa_ilan if not kupa_ilan[c])}; yeni yil donumu ilan kimligi olmayan '
         f'{sum(1 for r in plan if r["link"] == "ilan kimligi yok")}',
         'Uygulama (ayri onay): mevcut pinlerde yalniz publicationDate degisir (GET -> PUT -> GET, metricool_pin_baslik.py yolu, PUT yeni id verir,'
         ' uuid korunur); yeni yil donumu pinleri POST (KAPAK_Y1 PIN gorseli github.io uzerinden); kupa pinleri gorsel hazir olunca POST.',
         '', 'ILK 14 GUN:']
    for g in gunler[:14]:
        o.append(f'  {g}: ' + ' | '.join(f"{r['yeni_saat']} {r['aile']} {r['cift']}" for r in plan if r['yeni_gun'] == g))
    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o))
    if ihlal or not sira_ok or eksik:
        raise SystemExit(f'FAIL: ihlal {ihlal[:5]} sira {sira_ok} eksik {eksik}')


if __name__ == '__main__':
    main()
