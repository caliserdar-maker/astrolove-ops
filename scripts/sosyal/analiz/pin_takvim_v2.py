#!/usr/bin/env python3
"""Pinterest takvim PLANI v2 (20 Eki 2026). SALT OKUMA / PLAN: Metricool'a YAZMA YOK, yalniz GET.
Girdi kumesi v1 ile ayni (pin_takvim_plan.py): bekleyen Pinterest pinleri + 12 yeni yil donumu pini + 78 kupa yeri.
Kurallar:
 1. Gunde en fazla 10 pin; kota poster 4, yil donumu 3, kupa 3. Ailenin kotasi bos kalirsa (kuyruk bitti, kural engeli,
    kupa 1 Kas oncesi) bos slotlari once yil donumu, sonra poster doldurur.
 2. Kural BAS = 21 Eki'den baslar. BAS oncesi bekleyen pinler yerinde kalir: GECMIS (uygulama aninda saati gecmis olur).
 3. Kupa slotlari KUPA_BAS = 1 Kas'tan baslar.
 4. Ayni ilan baglantisina giden iki pin arasinda en az 3 gun; ayni gunde ayni cift (aileden bagimsiz) en fazla 1 pin.
    Gecmis/yayinlanmis pinler (bugun - 3 gun) bu kurallara gecmis olarak katilir.
 5. Aile ici sira korunur (kuyruk basi engelliyse aile o gun durur, atlama yok); plandan dusen pin 0.
 6. Saat: o gunun n pini 09:00-23:30 arasina esit yayilir (5 dk yuvarlama); gunun sirasi aileler arasinda donusumlu,
    baslangic ailesi gunden gune doner.
 7. Pano: v1 ile ayni (mevcut pinler kendi panosunda; yeni yil donumu en sik yil donumu panosu; kupa sirayla
    "Zodiac Couple Mugs" (olusturulacak) / "Personalized Couple Gifts").
Cikti: OUT/PLAN_V2.csv, OUT/OZET_V2.txt, OUT/HAM_*.json
Kullanim: pin_takvim_v2.py TOKEN.json OUT --pod78 P.csv --by78 B.csv --kupa K.csv --kullanilmayan U.csv [--sahte S.json]"""
import argparse
import csv
import importlib.util
import json
import os
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('v1', os.path.join(D, 'pin_takvim_plan.py'))
v1 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v1)
mpb, IST, TZ = v1.mpb, v1.IST, v1.TZ

BAS, KUPA_BAS = date(2026, 10, 21), date(2026, 11, 1)
GUNLUK, KOTA = 10, {'poster': 4, 'yildonumu': 3, 'kupa': 3}
DOLDUR = ('yildonumu', 'poster')
AILELER = ('poster', 'yildonumu', 'kupa')
LINK_ARA = 3
SAAT_BAS, SAAT_SON = 9 * 60, 23 * 60 + 30
KUPA_PANO = ('Zodiac Couple Mugs', 'Personalized Couple Gifts')


IZGARA = [f'{m // 60:02d}:{m % 60:02d}' for m in (int(round((SAAT_BAS + k * (SAAT_SON - SAAT_BAS) / (GUNLUK - 1)) / 5.0) * 5)
                                                   for k in range(GUNLUK))]


def saatler(n, gi):
    """n pin icin 10'lu izgaradan (09:00-23:30, ~1,5 sa) esit aralikli secim; n < 10 ise kayma gunden gune doner."""
    if n >= GUNLUK:
        return IZGARA[:n]
    adim = GUNLUK / n
    return sorted(IZGARA[(int(i * adim) + gi) % GUNLUK] for i in range(n))


def harmanla(sec, gi):
    """Ailelerin pinlerini gune esit yayar (agirlikli sira); esitlikte baslangic ailesi gunden gune doner."""
    rot = [AILELER[(gi + i) % 3] for i in range(3)]
    kalan = {f: list(sec[f]) for f in AILELER}
    n = {f: len(sec[f]) for f in AILELER}
    alinan = {f: 0 for f in AILELER}
    etiket = []
    while sum(alinan.values()) < sum(n.values()):
        f = min((f for f in rot if alinan[f] < n[f]), key=lambda f: ((alinan[f] + 0.5) / n[f], rot.index(f)))
        etiket.append(f); alinan[f] += 1
    k = gi % len(etiket) if etiket else 0
    etiket = etiket[k:] + etiket[:k]          # aile -> saat eslemesi gunden gune kayar; aile ici sira korunur
    return [kalan[f].pop(0) for f in etiket]


def oku(mc, out, simdi):
    try:
        bj = mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b})
    except SystemExit as e:
        bj = {'_hata': str(e)[:300]}
    json.dump(bj, open(os.path.join(out, 'HAM_boards.json'), 'w'), ensure_ascii=False, indent=1)
    pano = {str(b.get('id')): b.get('name') or '' for b in v1.liste(bj)}
    ps, t = {}, datetime(simdi.year, simdi.month, simdi.day) - timedelta(days=LINK_ARA)
    while t < v1.UFUK:
        e = min(t + timedelta(days=5), v1.UFUK)
        j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        json.dump(j, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
        for p in v1.liste(j):
            if mpb.pin_durum(p) is not None:
                ps[str(p.get('uuid') or p.get('id'))] = p
        t = e
    return pano, ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('pod78', 'by78', 'kupa', 'kullanilmayan', 'sahte', 'simdi'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    simdi = datetime.fromisoformat(a.simdi).replace(tzinfo=IST) if a.simdi else datetime.now(IST)
    if a.sahte:
        pano, ps = json.load(open(a.sahte)).values()
    else:
        pano, ps = oku(mpb.MC(json.load(open(a.token))), out, simdi)

    aile, kupa_ilan, by_ilan = {}, {}, {}
    for r in v1.csv_oku(a.pod78):
        aile[r['listing_id'].strip()] = ('poster', r['cift'].strip().upper())
    for r in v1.csv_oku(a.by78):
        if (r.get('listing_id') or '').strip():
            aile[r['listing_id'].strip()] = ('yildonumu', r['cift'].strip().upper()); by_ilan[r['cift'].strip().upper()] = r['listing_id'].strip()
    for r in v1.csv_oku(a.kupa):
        if (r.get('listing_id') or '').strip():
            aile[r['listing_id'].strip()] = ('kupa', r['cift'].strip().upper()); kupa_ilan[r['cift'].strip().upper()] = r['listing_id'].strip()

    # canli pinler: bekleyen (gelecek) + gecmis (link/cift kurallari icin)
    bek, gecmis, durumlar = [], [], Counter()
    for p in ps.values():
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        try:
            z = datetime.fromisoformat(zt).replace(tzinfo=IST)
        except ValueError:
            continue
        pd = p.get('pinterestData') or {}
        lid = v1.ilan(pd.get('pinLink'))
        af, cf = aile.get(lid, ('bilinmiyor', ''))
        md = [m.get('url') if isinstance(m, dict) else m for m in p.get('media') or []]
        r = dict(z=z, id=p.get('id'), uuid=str(p.get('uuid') or ''), aile=af, cift=cf, lid=lid, pano_id=str(pd.get('boardId') or ''),
                 pano=pano.get(str(pd.get('boardId')), ''), baslik=pd.get('pinTitle') or '', link=pd.get('pinLink') or '',
                 medya=md[0] if md else '', durum=mpb.pin_durum(p), kaynak='mevcut')
        if z > simdi:
            durumlar[r['durum']] += 1
        if z > simdi and r['durum'] == 'PENDING':
            bek.append(r)
        else:
            gecmis.append(r)
    bek.sort(key=lambda r: (r['z'], r['aile']))

    # sabitler: BAS oncesi bekleyen (GECMIS) + yayinlanmis/gecmis
    sabit = [r for r in bek if r['z'].date() < BAS or r['aile'] not in AILELER]
    kuyruk = {f: deque(r for r in bek if r['aile'] == f and r['z'].date() >= BAS) for f in AILELER}
    y_pano = Counter(r['pano'] for r in bek if r['aile'] == 'yildonumu').most_common(1)
    y_pano = y_pano[0][0] if y_pano else '1st Anniversary Gift Ideas'
    yeni_y = sorted(v1.csv_oku(a.kullanilmayan), key=lambda r: r['cift'])
    for r in yeni_y:
        c = r['cift'].strip().upper(); lid = by_ilan.get(c, '')
        kuyruk['yildonumu'].append(dict(z=None, id='', uuid='', aile='yildonumu', cift=c, lid=lid or f'YOK_{c}', pano_id='', pano=y_pano,
                                        baslik='', link=f'https://www.etsy.com/listing/{lid}' if lid else 'ilan kimligi yok',
                                        medya=f"KAPAK_Y1_78_20261019/PIN/{r['dosya']}", durum='', kaynak='YENI yil donumu (KULLANILMAYAN_PIN)'))
    var_pano = set(pano.values())
    for i, c in enumerate(sorted(kupa_ilan)):
        pn = KUPA_PANO[i % 2]
        kuyruk['kupa'].append(dict(z=None, id='', uuid='', aile='kupa', cift=c, lid=kupa_ilan[c], pano_id='',
                                   pano=pn + ('' if pn in var_pano else ' (OLUSTURULACAK)'), baslik='',
                                   link=f'https://www.etsy.com/listing/{kupa_ilan[c]}', medya='YOK (kupa pini hazirlaniyor)', durum='',
                                   kaynak='YENI kupa yeri (KUPA_TASLAK_LISTE)'))
    sira0 = {f: [id(x) for x in kuyruk[f]] for f in AILELER}
    toplam_kuyruk = sum(len(q) for q in kuyruk.values())

    son_link, gun_cift = {}, defaultdict(set)
    for r in gecmis + sabit:
        g = r['z'].date()
        if r['lid']:
            son_link[r['lid']] = max(son_link.get(r['lid'], g), g)
        if r['cift']:
            gun_cift[g].add(r['cift'])

    plan, gun, gi = [], BAS, 0
    while any(kuyruk.values()):
        if gi > 500:
            raise SystemExit('FAIL: 500 gunde bitmedi (kural cikmazi)')
        sec = defaultdict(list)

        def uygun(x):
            s = son_link.get(x['lid'])
            return (s is None or (gun - s).days >= LINK_ARA) and (not x['cift'] or x['cift'] not in gun_cift[gun])

        def al(f, n):
            k = 0
            while k < n and kuyruk[f] and uygun(kuyruk[f][0]):
                x = kuyruk[f].popleft(); sec[f].append(x); k += 1
                son_link[x['lid']] = gun
                if x['cift']:
                    gun_cift[gun].add(x['cift'])
            return k
        kap = GUNLUK - sum(1 for r in sabit if r['z'].date() == gun)
        for f in AILELER:
            al(f, min(KOTA[f] if (f != 'kupa' or gun >= KUPA_BAS) else 0, kap - sum(len(v) for v in sec.values())))
        for f in DOLDUR:
            al(f, kap - sum(len(v) for v in sec.values()))
        sira = harmanla(sec, gi)
        for x, s in zip(sira, saatler(len(sira), gi)):
            plan.append(dict(x, yeni_gun=gun, yeni_saat=s, islem='YENI' if x['z'] is None else
                             ('AYNI' if (x['z'].date(), x['z'].strftime('%H:%M')) == (gun, s) else 'KAYDIR')))
        gun += timedelta(days=1); gi += 1
    for r in sabit:
        plan.append(dict(r, yeni_gun=r['z'].date(), yeni_saat=r['z'].strftime('%H:%M'),
                         islem='GECMIS (21 Eki oncesi, yerinde)' if r['aile'] in AILELER else 'YERINDE (aile bilinmiyor)'))
    plan.sort(key=lambda r: (r['yeni_gun'], r['yeni_saat']))

    yaz_ = [[str(r['yeni_gun']), r['yeni_saat'], r['aile'], r['cift'], r['islem'], r['z'].strftime('%Y-%m-%d %H:%M') if r['z'] else '',
             (r['yeni_gun'] - r['z'].date()).days if r['z'] else '', r['id'], r['uuid'], r['pano'], r['pano_id'], r['baslik'], r['link'],
             r['medya'], r['kaynak']] for r in plan]
    v1.yaz(out, 'PLAN_V2.csv', ['yeni_tarih', 'yeni_saat', 'aile', 'cift', 'islem', 'eski_tarih_saat', 'kaydirma_gun', 'gonderi_id',
                                'uuid', 'pano', 'pano_id', 'baslik', 'link', 'medya', 'kaynak'], yaz_)

    # kontroller
    P = [r for r in plan if r['yeni_gun'] >= BAS]
    gun_say = Counter(r['yeni_gun'] for r in P)
    gun_cift_say = Counter((r['yeni_gun'], r['cift']) for r in plan if r['cift'])
    kupa_erken = [r for r in P if r['aile'] == 'kupa' and r['yeni_gun'] < KUPA_BAS]
    tum = sorted([(r['yeni_gun'], r['lid']) for r in plan if r['lid']] + [(r['z'].date(), r['lid']) for r in gecmis if r['lid']])
    son, ara = {}, []
    for g, l in tum:
        if l in son:
            ara.append(((g - son[l]).days, l))
        son[l] = g
    min_ara = min(ara) if ara else (None, '')
    # sira: plandaki aile sirasi == kuyruk sirasi
    sira_ok = True
    for f in AILELER:
        sp_ = [r for r in sorted([r for r in P if r['aile'] == f and not str(r['islem']).startswith('GECMIS')],
                                 key=lambda r: (r['yeni_gun'], r['yeni_saat']))]
        bekl = [r['uuid'] for r in bek if r['aile'] == f and r['z'].date() >= BAS]
        ek = sorted(r['cift'].strip().upper() for r in yeni_y) if f == 'yildonumu' else (sorted(kupa_ilan) if f == 'kupa' else [])
        if [(r['uuid'] or r['cift']) for r in sp_] != bekl + ek:
            sira_ok = False
        if len(sp_) != len(sira0[f]):
            sira_ok = False
    dusen = len(bek) + len(yeni_y) + len(kupa_ilan) - len(plan)
    ihlal_gun = [g for g, v in gun_say.items() if v > GUNLUK]
    ihlal_cift = [k for k, v in gun_cift_say.items() if v > 1]
    ihlal_link = [x for x in ara if x[0] < LINK_ARA]
    bitis = {f: max(r['yeni_gun'] for r in plan if r['aile'] == f) for f in AILELER if any(r['aile'] == f for r in plan)}
    kay = {f: [(r['yeni_gun'] - r['z'].date()).days for r in P if r['aile'] == f and r['z']] for f in AILELER}
    saat_cesit = {f: len({r['yeni_saat'] for r in P if r['aile'] == f}) for f in AILELER}
    sira_bas = Counter((r['aile'], r['yeni_saat']) for r in P)
    en_cok = {f: max([v for (a_, s), v in sira_bas.items() if a_ == f] or [0]) for f in AILELER}
    dag = Counter(tuple(sum(1 for r in P if r['yeni_gun'] == g and r['aile'] == f) for f in AILELER) for g in sorted(gun_say))
    gecmis_n = sum(1 for r in plan if str(r['islem']).startswith('GECMIS'))
    o = [f'Okuma: {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul), blogId 6974606, GET /v2/scheduler/posts + boards; Metricool yazma YOK',
         f'Bekleyen Pinterest (PENDING): {len(bek)}; aile {dict(Counter(r["aile"] for r in bek))}; gecmis/yayinlanmis (bugun-3 gun) {len(gecmis)}',
         f'Plan: {len(plan)} satir = mevcut bekleyen {len(bek)} + yeni yil donumu {len(yeni_y)} + kupa yeri {len(kupa_ilan)}; '
         f'GECMIS (21 Eki oncesi, yerinde) {gecmis_n}; islem {dict(Counter(str(r["islem"]).split(" (")[0] for r in plan))}',
         f'BITIS: poster {bitis.get("poster")}, yil donumu {bitis.get("yildonumu")}, kupa {bitis.get("kupa")}; plan sonu {max(gun_say) if gun_say else "-"}',
         f'Gunluk pin sayisi dagilimi (gun sayisi): {dict(sorted(Counter(gun_say.values()).items()))}; 10 pinli gun {sum(1 for v in gun_say.values() if v == 10)}',
         f'Gun basina (poster, yil donumu, kupa) en sik: {dict(dag.most_common(8))}',
         f'En buyuk kaydirma (gun, + ileri / - geri): ' + ', '.join(f'{f} max {max(v)} min {min(v)}' for f, v in kay.items() if v),
         f'Ayni ilan arasi en kisa: {min_ara[0]} gun (ilan {min_ara[1]}); 3 gunden kisa {len(ihlal_link)}',
         f'Saat: gunun n pini 09:00-23:30 esit; aile basina farkli saat sayisi {saat_cesit}; ayni aile x ayni saat en cok {en_cok} gun',
         f'KONTROL: gun > 10 ihlal {len(ihlal_gun)}; gun x cift > 1 ihlal {len(ihlal_cift)}; kupa 1 Kas oncesi {len(kupa_erken)}; '
         f'ayni link < 3 gun {len(ihlal_link)}; aile ici sira korundu {sira_ok}; dusen pin {dusen}',
         f'Panolar: {dict(Counter((r["aile"], r["pano"]) for r in plan))}',
         '', 'ILK 12 GUN:']
    for g in sorted(gun_say)[:12]:
        o.append(f'  {g} ({gun_say[g]}): ' + ' | '.join(f"{r['yeni_saat']} {r['aile'][:4]} {r['cift']}" for r in P if r['yeni_gun'] == g))
    open(os.path.join(out, 'OZET_V2.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o))
    if ihlal_gun or ihlal_cift or kupa_erken or ihlal_link or not sira_ok or dusen:
        raise SystemExit('FAIL: kural kontrolu (OZET_V2.txt KONTROL satiri)')


if __name__ == '__main__':
    main()
