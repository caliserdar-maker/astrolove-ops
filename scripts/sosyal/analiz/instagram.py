#!/usr/bin/env python3
"""Instagram anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve Instagram'a YAZMA YOK, yalniz GET.
Uclar ve metrik adlari data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json'dan (GET /v2/analytics/timelines aciklamasi):
  /v2/analytics/timelines network=instagram subject=account   belgede: delta_followers, followers_gained, followers_lost,
                                                             clicks_total, postsCount, postsInteractions
      ayni uc, belgede OLMAYAN adlar (DENEME; yanit ne derse o): followers, reach, views, impressions, profile_views,
      website_clicks, profile_links_taps, accounts_engaged
      breakdown (belgede: subject media_product_type|follow_type|contact_button_type): profile_links_taps, reach, views
  /v2/analytics/timelines subject=posts|reels                 belgedeki gonderi/reel metrikleri (yayin gunune gore)
  /v2/analytics/aggregation, /stats/aggregations/instagram     takipci toplami icin (ham)
  /v2/analytics/posts/instagram, /v2/analytics/reels/instagram  gonderi bazinda (InstagramPost / InstagramReel semasi)
  /v2/scheduler/posts                                          plan / yayin / hata (12 Eki - bugun), publicUrl ile eslesme
Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok. Ham yanitlar HAM_*.json, ozet OZET.txt.
Kullanim: instagram.py TOKEN.json CIKTI_DIR"""
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
PLAN_BAS = date(2026, 10, 12)
YOK = 'erisilemedi'
TL = '/v2/analytics/timelines'
# (metric, subject, scope, belgede)
HESAP = [(m, 'account', None, True) for m in ('delta_followers', 'followers_gained', 'followers_lost', 'clicks_total',
                                               'postsCount', 'postsInteractions')] \
    + [(m, 'account', None, False) for m in ('followers', 'reach', 'views', 'impressions', 'profile_views',
                                              'website_clicks', 'profile_links_taps', 'accounts_engaged')] \
    + [('profile_links_taps', 'contact_button_type', None, True), ('views', 'media_product_type', None, True),
       ('reach', 'media_product_type', None, True), ('reach', 'follow_type', None, True)]
ICERIK = [(m, 'posts', None, True) for m in ('count', 'reach', 'impressions', 'likes', 'comments', 'saves', 'shares',
                                              'interactions', 'engagement')] \
    + [(m, 'reels', None, True) for m in ('count', 'reach', 'videoviews', 'impressions', 'likes', 'comments', 'saved',
                                          'shares', 'interactions', 'engagement')]
# gonderi tablosu: (sutun, posts alani, reels alani)
GON = [('erisim', 'reach', 'reach'), ('goruntulenme_views', 'views', 'views'), ('gosterim_impressions', 'impressions',
       'impressions'), ('begeni', 'likes', 'likes'), ('yorum', 'comments', 'comments'), ('kayit', 'saved', 'saved'),
       ('paylasim', 'shares', 'shares'), ('etkilesim', 'interactions', 'interactions'),
       ('reel_izlenme_videoViews', None, 'videoViews'), ('reel_ort_izleme_suresi', None, 'averageWatchTime'),
       ('reel_toplam_izleme_suresi', None, 'videoViewTotalTime'), ('reel_sure_sn', None, 'durationSeconds')]
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
OZET = None


def log(s):
    print(s, flush=True)
    with open(OZET, 'a', encoding='utf-8') as f:
        f.write(s + '\n')


def yaz_csv(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    log(f'CSV {ad}: {len(satirlar)} satir')


def ham(out, ad, veri):
    json.dump(veri, open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def sayi(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return YOK
    return int(v) if float(v).is_integer() else round(v, 2)


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v if isinstance(v, list) else None


def guvenli(mc, ad, yol, params, out):
    try:
        j = mc.istek('GET', yol, params)
    except SystemExit as e:
        log(f'{ad}: HATA {str(e)[:220]}'); ham(out, ad, {'_hata': str(e)[:300]})
        return None
    ham(out, ad, j)
    return j


def seriler(j):
    """timelines yaniti: data[{metric, values[{dateTime, value}]}] -> {seri_adi: {date: float}} (tarih ilk 10 karakter)."""
    out = {}
    for i, blok in enumerate(liste(j) or []):
        if not isinstance(blok, dict):
            continue
        g = out.setdefault(str(blok.get('metric') or i), {})
        for x in blok.get('values') or []:
            t, v = x.get('dateTime'), x.get('value')
            if isinstance(t, str) and re.match(r'\d{4}-\d{2}-\d{2}', t) and isinstance(v, (int, float)):
                d = date.fromisoformat(t[:10]); g[d] = g.get(d, 0) + float(v)
    return out


def cift(metin):
    m = re.search(r'\b(' + '|'.join(BURC) + r')\s*(?:&|and|\+|x)\s*(' + '|'.join(BURC) + r')\b', metin or '', re.I)
    return '_'.join(sorted((m.group(1).upper(), m.group(2).upper()))) if m else ''


def kod(url):
    m = re.search(r'instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', url or '')
    return m.group(1) if m else ''


def zaman(x):
    v = x.get('publishedAt') if isinstance(x, dict) else None
    return (v.get('dateTime') if isinstance(v, dict) else v) or ''


def main():
    global OZET
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = mpb.MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    log(f'OKUMA ANI (UTC): {okuma}; userId {mc.u}; blogId {mc.b}; donem {BAS} - {BUGUN} ({TZ})')
    aralik = {'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}
    kaynak = []   # IG_METRIK_KAYNAK.csv

    # 1) hesap geneli gunluk + icerik timeline'lari
    def timeline_oku(tanim, csv_ad):
        kol, S = [], {}
        for m, subj, scope, belgede in tanim:
            p = dict(aralik, network='instagram', metric=m, subject=subj)
            if scope:
                p['scope'] = scope
            ad = f'timeline_{subj}_{m}'
            j = guvenli(mc, ad, TL, p, out)
            ss = seriler(j) if j is not None else {}
            durum = 'HTTP hata' if j is None else ('bos yanit' if not ss else
                                                   ('deger yok' if not any(ss.values()) else 'veri var'))
            log(f'TIMELINE {subj}/{m} ({"belgede" if belgede else "belgede YOK, deneme"}): {durum}; '
                + '; '.join(f'{k}: {len(g)} gun, toplam {sayi(sum(g.values()))}' for k, g in ss.items()))
            if not ss:
                ss = {m: None}
            for k, g in ss.items():
                c = f'{m}' if (len(ss) == 1 and subj in ('account', 'posts', 'reels')) else f'{m}[{subj}:{k}]'
                c = f'{subj}.{c}' if subj in ('posts', 'reels') else c
                kol.append(c); S[c] = g
                kaynak.append([csv_ad, c, TL, f'network=instagram metric={m} subject={subj}' + (f' scope={scope}' if scope else '')
                               + (f' seri={k}' if c.endswith(']') else ''), 'evet' if belgede else 'hayir (deneme)', durum])
        yaz_csv(out, csv_ad, ['tarih'] + kol + ['kaynak'],
                [[str(d)] + [sayi(S[c].get(d)) if S[c] and d in S[c] else YOK for c in kol]
                 + [f'{TL} network=instagram; okuma {okuma}'] for d in gunler])
        yaz_csv(out, csv_ad.replace('GUNLUK', 'TOPLAM'), ['donem'] + kol + ['kaynak'],
                [[f'{BAS} - {BUGUN}'] + [sayi(sum(S[c].values())) if S[c] else YOK for c in kol]
                 + [f'{TL}; okuma {okuma}']])
    timeline_oku(HESAP, 'IG_HESAP_GUNLUK.csv')
    timeline_oku(ICERIK, 'IG_ICERIK_GUNLUK.csv')

    # takipci toplami (aggregation; ham + ozet)
    for m, subj in (('followers', 'account'), ('delta_followers', 'account')):
        j = guvenli(mc, f'aggregation_{subj}_{m}', '/v2/analytics/aggregation', dict(aralik, network='instagram', metric=m,
                    subject=subj), out)
        log(f'AGGREGATION {subj}/{m}: {json.dumps(mpb.veri(j), default=str)[:200] if j is not None else "HTTP hata"}')
    j = guvenli(mc, 'stats_aggregations_instagram', '/stats/aggregations/instagram',
                {'start': f'{BAS:%Y%m%d}', 'end': f'{BUGUN:%Y%m%d}', 'timezone': TZ}, out)
    log(f'STATS/AGGREGATIONS/instagram (eski uc): {json.dumps(j, default=str)[:600] if j is not None else "HTTP hata"}')

    # 4) scheduler (12 Eki - bugun)
    ps, t = {}, datetime.combine(PLAN_BAS, datetime.min.time())
    son = datetime.combine(BUGUN + timedelta(days=1), datetime.min.time())
    while t < son:
        e = min(t + timedelta(days=5), son)
        j = guvenli(mc, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}',
                    'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}, out)
        for p in liste(j) or []:
            ps[str(p.get('id'))] = p
        t = e
    sch, url_sch = [], {}
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'instagram'), None)
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        if not pr or not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        idt = p.get('instagramData') or {}
        n = len(p.get('media') or [])
        tur = 'Reel' if (idt.get('type') or '').upper() == 'REEL' else ('karusel' if n > 1 else f'tek ({idt.get("type")})')
        sch.append((zt, p, pr, tur))
        if kod(pr.get('publicUrl')):
            url_sch[kod(pr['publicUrl'])] = (zt, pr.get('status'), tur, cift(p.get('text')))
    if sch:
        log(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:30]} | provider {sorted(sch[0][2])}')
    gun_dur, detay = defaultdict(Counter), []
    for zt, p, pr, tur in sorted(sch, key=lambda x: x[0]):
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        h = pr.get('detail') or pr.get('error') or ''
        detay.append([zt, tur, st, pr.get('detailedStatus') or '', cift(p.get('text')), len(p.get('media') or []),
                      pr.get('publicUrl') or '', (h if isinstance(h, str) else json.dumps(h, ensure_ascii=False))[:200]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'IG_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts providers[instagram].status; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'IG_PLAN_DETAY.csv', ['plan_zamani', 'tur', 'durum', 'ayrintili_durum', 'cift', 'medya_sayisi', 'link',
                                       'hata_ayrinti'], detay)
    top = Counter(); [top.update(c) for c in gun_dur.values()]
    log(f'PLAN {PLAN_BAS} - {BUGUN}: planlanan {sum(top.values())}; durum {dict(top)}; tur {dict(Counter(x[3] for x in sch))}')
    for r in detay:
        log(f'PLAN {r[0]} {r[1]} {r[2]} {r[3]} {r[4]} {r[6]} {r[7][:80]}')

    # 2) gonderi bazinda (12 Eki - bugun)
    a2 = {'from': f'{PLAN_BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}
    kay = {}
    for uc, ad, idk in (('/v2/analytics/posts/instagram', 'posts', 'postId'), ('/v2/analytics/reels/instagram', 'reels', 'reelId')):
        j = guvenli(mc, f'{ad}_instagram', uc, a2, out)
        ls = liste(j)
        log(f'{uc}: {len(ls) if ls is not None else "yanit yok"} kayit; alanlar {sorted(ls[0]) if ls else "-"}')
        for x in ls or []:
            k = kod(x.get('url')) or str(x.get(idk))
            if k in kay:
                log(f'  {ad}: {k} iki uctan da geldi (ilk kayit tutulur: {kay[k][0]})'); continue
            kay[k] = (ad, uc, x)
    satir, tur_deger = [], defaultdict(lambda: defaultdict(list))
    for k, (ad, uc, x) in sorted(kay.items(), key=lambda kv: zaman(kv[1][2])):
        s = url_sch.get(kod(x.get('url')), ('', '', '', ''))
        tip = (x.get('type') or '').upper()
        tur = 'Reel' if ad == 'reels' or 'REEL' in tip else ('karusel' if 'CAROUSEL' in tip else (s[2] or f'diger ({tip})'))
        deg = []
        for sut, fp, fr in GON:
            alan = fr if ad == 'reels' else fp
            v = x.get(alan) if alan else None
            deg.append(sayi(v))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                tur_deger[tur][sut].append(v)
        tur_deger[tur]['_n'].append(1)
        satir.append([zaman(x), tur, x.get('type') or '', cift(x.get('content')) or s[3],
                      s[0], s[1]] + deg + [x.get('url') or '', uc])
    yaz_csv(out, 'IG_GONDERI.csv', ['yayin_zamani', 'tur', 'metricool_type', 'cift', 'plan_zamani', 'plan_durum']
            + [g[0] for g in GON] + ['url', 'kaynak_uc'], satir)
    for r in satir:
        log('GONDERI ' + ' | '.join(str(v) for v in r[:-1]))

    # 3) karusel / Reel karsilastirmasi (yalniz olculen degerler)
    kar = []
    for tur, d in sorted(tur_deger.items()):
        for sut, _, _ in GON:
            v = d.get(sut) or []
            kar.append([tur, len(d['_n']), sut, len(v), sayi(sum(v) / len(v)) if v else YOK, sayi(sum(v)) if v else YOK])
    yaz_csv(out, 'IG_TUR_KARSILASTIRMA.csv', ['tur', 'gonderi_sayisi', 'olcu', 'olculen_n', 'ortalama', 'toplam'], kar)
    for r in kar:
        if r[3]:
            log(f'TUR {r[0]} (n={r[1]}) {r[2]}: olculen {r[3]}, ort {r[4]}, toplam {r[5]}')

    # 5) metrik kaynagi
    for sut, fp, fr in GON:
        kaynak.append(['IG_GONDERI.csv', sut, '/v2/analytics/posts/instagram | /v2/analytics/reels/instagram',
                       f'InstagramPost.{fp or "-"} | InstagramReel.{fr or "-"}', 'evet (sema)', ''])
    kaynak += [['IG_GONDERI.csv', 'plan_zamani/plan_durum', '/v2/scheduler/posts', 'publicationDate.dateTime, providers[instagram].status',
                'evet (sema)', 'publicUrl kisa kodu ile eslesme'],
               ['IG_PLAN_*.csv', 'durum', '/v2/scheduler/posts', 'providers[instagram].status, detailedStatus, instagramData.type, media',
                'evet (sema)', '']]
    yaz_csv(out, 'IG_METRIK_KAYNAK.csv', ['tablo', 'sutun', 'uc', 'metrik_alan', 'belgede', 'yanit'], kaynak)


if __name__ == '__main__':
    main()
