#!/usr/bin/env python3
"""Pinterest anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve Pinterest'e YAZMA YOK, yalniz GET.
Uclar (data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json):
  /v2/analytics/timelines (network=pinterest)   hesap geneli gunluk: impression, pin_click, outbound_click, save, followers
  /v2/analytics/posts/pinterest                 pin bazinda: impressions, pinClicks, outboundClicks, saves, boardId, createdAt
  /v2/scheduler/posts                           plan / yayin / hata (13 Eki - bugun) + pin -> gorsel eslesmesi
  /v2/scheduler/boards/pinterest                pano adlari
Tur (P1/P2/P3) pano adindan (pin_v6_plan.py PANO); eslesmeyen pano "bilinmiyor". Cift basliktan ("X and Y").
Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok. Ham yanitlar HAM_*.json.
Kullanim: pinterest.py TOKEN.json CIKTI_DIR [ONCEKI_DIR (17 Eki HAM_timeline_*.json, HAM_posts_pinterest.json)]"""
import csv
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
BAS, BUGUN = date(2026, 10, 1), date(2026, 10, 19)
PLAN_BAS = date(2026, 10, 13)
SCH_BAS = date(2026, 9, 1)                      # pin -> scheduler eslesmesi icin genis pencere
POST_BAS = date(2026, 1, 1)                     # pin listesi: tum pinler (createdAt ile filtrelenir)
METRIK = [('impression', 'gosterim'), ('pin_click', 'pin_tiklama'), ('outbound_click', 'disa_tiklama'), ('save', 'kayit')]
PIN_K = [('impressions', 'gosterim'), ('pinClicks', 'pin_tiklama'), ('outboundClicks', 'disa_tiklama'), ('saves', 'kayit')]
TUR = {'zodiac couple wall art': 'P1', 'zodiac compatibility art': 'P2', 'personalized couple gifts': 'P3'}
YOK = 'erisilemedi'


def yaz_csv(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def ham(out, ad, veri):
    json.dump(veri, open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def sayi(v):
    return YOK if v is None else (int(v) if float(v).is_integer() else round(v, 2))


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v


def seri(j):
    """timelines yaniti: data[].values[{dateTime, value}] -> {date: float}; tarih ilk 10 karakterden (yerel gun)."""
    out = {}
    for blok in liste(j) or []:
        for x in (blok.get('values') or []) if isinstance(blok, dict) else []:
            t, v = x.get('dateTime'), x.get('value')
            if isinstance(t, str) and re.match(r'\d{4}-\d{2}-\d{2}', t) and isinstance(v, (int, float)):
                d = date.fromisoformat(t[:10]); out[d] = out.get(d, 0) + float(v)
    return out


def guvenli(mc, ad, yol, params, out):
    try:
        j = mc.istek('GET', yol, params)
    except SystemExit as e:
        print(f'{ad}: HATA {str(e)[:200]}'); j = {'_hata': str(e)[:300]}
        ham(out, ad, j); return None
    ham(out, ad, j)
    return j


def cift(baslik):
    m = re.match(r'\s*([A-Za-z]+) and ([A-Za-z]+)\b', baslik or '')
    return '_'.join(sorted((m.group(1).upper(), m.group(2).upper()))) if m else ''


def pin_id(url):
    m = re.search(r'/pin/(\d+)', url or '')
    return m.group(1) if m else ''


def main():
    tok, out = sys.argv[1], sys.argv[2]
    onceki = sys.argv[3] if len(sys.argv) > 3 else ''
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'OKUMA ANI (UTC): {okuma}')

    # 1) hesap geneli gunluk
    S = {}
    for m, ad in METRIK:
        j = guvenli(mc, f'timeline_{m}', '/v2/analytics/timelines', {'network': 'pinterest', 'metric': m,
                    'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, out)
        S[ad] = seri(j) if j is not None else None
    takip = None
    for etiket, ek in (('followers', {}), ('followers_account', {'subject': 'account'})):
        j = guvenli(mc, f'timeline_{etiket}', '/v2/analytics/timelines', dict({'network': 'pinterest', 'metric': 'followers',
                    'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, **ek), out)
        g = seri(j) if j is not None else {}
        print(f'TAKIPCI ({etiket}): {len(g)} gun')
        if g:
            takip = g; break
    S['takipci'] = takip
    for ad, g in S.items():
        print(f'TIMELINE {ad}: ' + ('yanit yok' if g is None else f'{len(g)} gun, toplam {sayi(sum(g.values()))}'))
    kol = [ad for _, ad in METRIK] + ['takipci']
    yaz_csv(out, 'PIN_HESAP_GUNLUK.csv', ['tarih'] + kol + ['kaynak'],
            [[str(d)] + [sayi(S[a].get(d)) if S[a] and d in S[a] else YOK for a in kol]
             + [f'/v2/analytics/timelines network=pinterest; okuma {okuma}'] for d in gunler])
    yaz_csv(out, 'PIN_HESAP_TOPLAM.csv', ['donem'] + [ad for _, ad in METRIK] + ['kaynak'],
            [[f'{BAS} - {BUGUN}'] + [sayi(sum(v for d, v in S[a].items() if BAS <= d <= BUGUN)) if S[a] else YOK
                                     for _, a in METRIK] + [f'/v2/analytics/timelines; okuma {okuma}']])

    # panolar
    panolar = {}
    bj = guvenli(mc, 'boards_pinterest', '/v2/scheduler/boards/pinterest', {'brandId': mc.b}, out)
    for b in liste(bj) or []:
        panolar[str(b.get('id') or b.get('boardId'))] = b.get('name') or b.get('title') or ''
    print(f'PANOLAR: {len(panolar)} {sorted(panolar.values())}')

    # scheduler (13 Eki oncesi de: pin -> gorsel eslesmesi)
    ps, t = {}, datetime.combine(SCH_BAS, datetime.min.time())
    son = datetime.combine(BUGUN + timedelta(days=1), datetime.min.time())
    while t < son:
        e = min(t + timedelta(days=5), son)
        j = guvenli(mc, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}',
                    'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}, out)
        for p in liste(j) or []:
            ps[str(p.get('id'))] = p
        t = e
    pin_sch = {}
    sch = []
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'pinterest'), None)
        if not pr:
            continue
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        pd = p.get('pinterestData') or {}
        medya = (p.get('media') or [''])[0]
        medya = medya.get('url', '') if isinstance(medya, dict) else medya
        sch.append((zt, p, pr, pd, medya))
        if pin_id(pr.get('publicUrl')):
            pin_sch[pin_id(pr['publicUrl'])] = (zt, pr.get('status'), medya)
    print(f'SCHEDULER Pinterest gonderi ({SCH_BAS} - {BUGUN}): {len(sch)}; durumlar {dict(Counter(x[2].get("status") for x in sch))}')
    if sch:
        print(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:30]} | provider {sorted(sch[0][2])}')

    # 4) plan / gercek (13 Eki - bugun)
    gun_dur = defaultdict(Counter)
    detay = []
    for zt, p, pr, pd, medya in sorted(sch, key=lambda x: x[0]):
        if not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        detay.append([zt, st, panolar.get(str(pd.get('boardId')), pd.get('boardId')), cift(pd.get('pinTitle')),
                      pd.get('pinTitle') or '', pr.get('publicUrl') or '', (pr.get('detail') or pr.get('error') or '')[:200]
                      if isinstance(pr.get('detail') or pr.get('error') or '', str) else json.dumps(pr.get('detail') or pr.get('error'))[:200]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'PIN_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'PIN_PLAN_DETAY.csv', ['yayin_zamani', 'durum', 'pano', 'cift', 'baslik', 'pin_link', 'hata_ayrinti'], detay)
    top = Counter(); [top.update(c) for c in gun_dur.values()]
    print(f'PLAN 13 Eki - {BUGUN}: planlanan {sum(top.values())}; {dict(top)}')

    # 2) pin bazinda
    pj = guvenli(mc, 'posts_pinterest', '/v2/analytics/posts/pinterest',
                 {'from': f'{POST_BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, out)
    pins = liste(pj)
    satir, pano_top = [], defaultdict(lambda: [0] + [0.0] * 4)
    for p in pins or []:
        pano = panolar.get(str(p.get('boardId')), str(p.get('boardId') or ''))
        tur = TUR.get(pano.strip().lower(), 'bilinmiyor')
        s = pin_sch.get(str(p.get('id')), ('', '', ''))
        deg = [p.get(k) if isinstance(p.get(k), (int, float)) else None for k, _ in PIN_K]
        satir.append([p.get('createdAt') or '', p.get('id'), pano, cift(p.get('title')), tur] + [sayi(v) for v in deg]
                     + [p.get('title') or '', os.path.basename(s[2].split('?')[0]) if s[2] else ''])
        t_ = pano_top[(pano, tur)]; t_[0] += 1
        for i, v in enumerate(deg):
            t_[i + 1] = None if v is None or t_[i + 1] is None else t_[i + 1] + v
    satir.sort(key=lambda x: x[0])
    yaz_csv(out, 'PIN_PIN_BAZINDA.csv', ['yayin_tarihi', 'pin_id', 'pano', 'cift', 'tur'] + [a for _, a in PIN_K]
            + ['baslik', 'scheduler_gorsel'], satir)
    print(f'POSTS/PINTEREST: {len(pins) if pins is not None else "yanit yok"} pin; ilk {satir[0][0] if satir else "-"}, '
          f'son {satir[-1][0] if satir else "-"}; tur {dict(Counter(r[4] for r in satir))}')

    # 3) pano kirilimi
    yaz_csv(out, 'PIN_PANO.csv', ['pano', 'tur', 'pin_sayisi'] + [a for _, a in PIN_K] + ['kaynak'],
            [[b, tr, v[0]] + [sayi(x) for x in v[1:]] + [f'/v2/analytics/posts/pinterest from={POST_BAS}; okuma {okuma}']
             for (b, tr), v in sorted(pano_top.items(), key=lambda x: -(x[1][1] or 0))])
    for (b, tr), v in pano_top.items():
        print(f'PANO {b} ({tr}): {v[0]} pin, gosterim {sayi(v[1])}, pin_tik {sayi(v[2])}, disa {sayi(v[3])}, kayit {sayi(v[4])}')

    # 5) 14-16 Eki: 17 Eki okumasi ile bugun
    kar = []
    for m, ad in METRIK:
        eski = {}
        f = os.path.join(onceki, f'HAM_timeline_{m}.json') if onceki else ''
        if f and os.path.exists(f):
            eski = seri(json.load(open(f)))
        for d in (date(2026, 10, 13), date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 16), date(2026, 10, 17)):
            e = sayi(eski.get(d)) if d in eski else YOK
            b = sayi(S[ad].get(d)) if S[ad] and d in S[ad] else YOK
            kar.append([str(d), ad, e, b, '' if YOK in (e, b) else ('degisti' if e != b else 'ayni'),
                        '17 Eki 10:59 UTC HAM_timeline (PINTEREST_20261017) / bugun /v2/analytics/timelines'])
    eski_p = {}
    f = os.path.join(onceki, 'HAM_posts_pinterest.json') if onceki else ''
    if f and os.path.exists(f):
        eski_p = {str(p.get('id')): p for p in liste(json.load(open(f))) or []}
    bugun_p = {str(p.get('id')): p for p in pins or []}
    for i in sorted(set(eski_p) | set(bugun_p)):
        p = bugun_p.get(i) or eski_p.get(i)
        if not (p.get('createdAt') or '')[:10] in ('2026-10-14', '2026-10-15', '2026-10-16'):
            continue
        e = eski_p.get(i, {}).get('impressions'); b = bugun_p.get(i, {}).get('impressions')
        kar.append([(p.get('createdAt') or '')[:10], f'pin {i} gosterim', sayi(e) if i in eski_p else YOK,
                    sayi(b) if i in bugun_p else YOK, 'degisti' if i in eski_p and i in bugun_p and e != b else '',
                    '/v2/analytics/posts/pinterest (17 Eki HAM / bugun)'])
    yaz_csv(out, 'PIN_14_16_EKI_KARSILASTIRMA.csv', ['tarih', 'olcu', 'okuma_17eki', 'okuma_bugun', 'fark', 'kaynak'], kar)
    for r in kar[:20]:
        print('KARS', r[:5])
    pz = [r for r in kar if r[1].startswith('pin ')]
    print(f'KARS pin (14-16 Eki yayin): {len(pz)}; bugun >0 gosterim: {sum(1 for r in pz if isinstance(r[3], int) and r[3] > 0)}')


if __name__ == '__main__':
    main()
