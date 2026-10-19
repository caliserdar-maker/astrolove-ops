#!/usr/bin/env python3
"""Threads anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve Threads'e YAZMA YOK, yalniz GET.
Uclar ve metrik adlari data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json'dan:
  /v2/analytics/timelines  metric aciklamasi "For Threads (posts metrics): count, views, likes, replies, reposts,
                           engagement, quotes, interactions, shares". Threads icin HESAP metrigi (takipci vb.) belgede YOK;
                           network listesinde 'threads' yazmiyor. 1. kosu (19 Eki 11:42 UTC): subject zorunlu, gecerli
                           [posts, account]; subject=account icin 400 yanitindaki gecerli liste HESAP_METRIK (belgede yok).
  /v2/analytics/aggregation  ayni metrikler, donem toplami (timelines ile capraz kontrol)
  /v2/analytics/posts/threads  ozet "Download a CSV with the list of threads posts"; sema ThreadsPost: publishedDate, id,
                           text, mediaType, shortCode, isQuotePost, permalink, views, likes, replies, reposts, quotes,
                           shares, engagement. Yanit JSON degilse metin olarak saklanir ve CSV diye okunur.
  /v2/analytics/catalogs/threads/scopes  baglanti izinleri (insights izni var mi)
  /v2/scheduler/posts      plan / yayin / hata (12 Eki - bugun), providers[network=threads].status/detail/publicUrl
Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok. Ham yanitlar HAM_*.json, ozet OZET.txt.
Kullanim: threads.py TOKEN.json CIKTI_DIR"""
import csv
import importlib.util
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
BAS, BUGUN = date(2026, 10, 1), date(2026, 10, 19)
PLAN_BAS = date(2026, 10, 12)
YOK = 'erisilemedi'
TL = '/v2/analytics/timelines'
METRIK = ['count', 'views', 'likes', 'replies', 'reposts', 'quotes', 'shares', 'interactions', 'engagement']   # belgede
HESAP_METRIK = ['followers_count', 'delta_followers', 'views', 'likes', 'replies', 'reposts', 'quotes']   # 400 yanitindan
SERI = [(m, 'account', False) for m in HESAP_METRIK] + [(m, 'posts', True) for m in METRIK]
# gonderi tablosu: (sutun, ThreadsPost alani)
GON = [('goruntulenme', 'views'), ('begeni', 'likes'), ('yanit', 'replies'), ('yeniden_paylasim', 'reposts'),
       ('alinti', 'quotes'), ('paylasim', 'shares'), ('engagement', 'engagement')]
BURC = ('ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN',
        'AQUARIUS', 'PISCES')
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
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return YOK
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return YOK
    return int(v) if float(v).is_integer() else round(v, 4)


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v if isinstance(v, list) else None


def al(mc, yol, params):
    """GET; JSON degilse {'_metin', '_content_type'} dondurur (posts/threads ozeti 'CSV' diyor). Token yanitta maskelenir."""
    q = dict(params or {}, userId=mc.u, blogId=mc.b)
    url = f'{mpb.API}{yol}?{urllib.parse.urlencode(q)}'
    for deneme in range(4):
        b = mpb.BEKLE - (time.time() - mc.son)
        if b > 0:
            time.sleep(b)
        r = urllib.request.Request(url, method='GET', headers={'X-Mc-Auth': mc.t, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(r, timeout=60) as y:
                mc.son = time.time()
                g, ct = y.read(), y.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e:
            mc.son = time.time()
            if e.code == 429 and deneme < 3:
                s = int(e.headers.get('Retry-After') or 60); log(f'429: {s} sn bekleniyor'); time.sleep(s); continue
            if e.code in (502, 503, 504) and deneme < 3:
                time.sleep(10 * (deneme + 1)); continue
            raise SystemExit(f'HTTP {e.code} GET {yol}: ' + e.read()[:400].decode('utf-8', 'replace').replace(mc.t, '***'))
        if not g:
            return None
        try:
            return json.loads(g)
        except ValueError:
            return {'_content_type': ct, '_metin': g.decode('utf-8', 'replace').replace(mc.t, '***')}


def guvenli(mc, ad, yol, params, out):
    try:
        j = al(mc, yol, params)
    except SystemExit as e:
        log(f'{ad}: HATA {str(e)[:300]}'); ham(out, ad, {'_hata': str(e)[:2000]})
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


def cift(*metinler):
    """'Aquarius & Aquarius' / 'Leo and Virgo'; alfabetik anahtar (CLAUDE.md). Ayni burc ciftine izin var."""
    b = '|'.join(BURC)
    for t in metinler:
        m = re.search(r'\b(' + b + r')\s*(?:&|and|\+|x)\s*(' + b + r')\b', (t or '').upper())
        if m:
            return '_'.join(sorted((m.group(1), m.group(2))))
    return ''


def kod(url):
    m = re.search(r'threads\.(?:net|com)/@[^/]+/post/([A-Za-z0-9_-]+)', url or '')
    return m.group(1) if m else ''


def zaman(v):
    """DateTimeInfo {dateTime, timezone} ya da ISO metin -> Istanbul saati (yanit TZ'si farkliysa cevrilir)."""
    t, tz = (v.get('dateTime'), v.get('timezone')) if isinstance(v, dict) else (v, None)
    if not t:
        return ''
    try:
        d = datetime.fromisoformat(str(t).replace('Z', '+00:00'))
        d = d if d.tzinfo else d.replace(tzinfo=ZoneInfo(tz or TZ))
        return d.astimezone(ZoneInfo(TZ)).strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        return str(t)


def gonderiler(j):
    """posts/threads: JSON liste ya da CSV metni -> [dict]."""
    if isinstance(j, dict) and '_metin' in j:
        return list(csv.DictReader(io.StringIO(j['_metin']))), 'csv'
    ls = liste(j)
    return (ls, 'json') if ls is not None else (None, '-')


def alan(x, *adlar):
    for a in adlar:
        for k in x:
            if k.lower().replace(' ', '').replace('_', '') == a.lower():
                return x[k]
    return None


def main():
    global OZET
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = mpb.MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    log(f'OKUMA ANI (UTC): {okuma}; userId {mc.u}; blogId {mc.b}; donem {BAS} - {BUGUN} ({TZ})')
    aralik = {'network': 'threads', 'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}
    kaynak = []

    # 0) baglanti izinleri
    j = guvenli(mc, 'catalogs_threads_scopes', '/v2/analytics/catalogs/threads/scopes', {}, out)
    log(f'SCOPES threads: {json.dumps(mpb.veri(j), ensure_ascii=False)[:400] if j is not None else "HTTP hata"}')

    # 1) timelines: subject=account (hesap; adlar 1. kosu 400 yanitindan) + subject=posts (belgedeki posts metrics)
    S, KOL = {}, []
    for m, sj, belge in SERI:
        j = guvenli(mc, f'timeline_{sj}_{m}', TL, dict(aralik, metric=m, subject=sj), out)
        ss = seriler(j) if j is not None else {}
        durum = 'HTTP hata' if j is None else ('bos yanit' if not ss or not any(ss.values()) else 'veri var')
        c = f'{sj}.{m}'
        g = {}
        for k, v in ss.items():
            for d, x in v.items():
                g[d] = g.get(d, 0) + x
        log(f'TIMELINE {c} ({"belgede" if belge else "belgede YOK, 400 yanitindaki liste"}): {durum}; {len(g)} gun'
            + (f', ilk {min(g)}, son {max(g)}, toplam {sayi(sum(g.values()))}' if g else '') + f'; seriler {sorted(ss)}')
        kaynak.append(['TH_HESAP_GUNLUK.csv', c, TL, f'network=threads metric={m} subject={sj}',
                       'evet (posts metrics)' if belge else 'hayir (400 yanitindaki gecerli deger)', durum])
        S[c] = g; KOL.append(c)
    yaz_csv(out, 'TH_HESAP_GUNLUK.csv', ['tarih'] + KOL + ['kaynak'],
            [[str(d)] + [sayi(S[c].get(d)) if d in S[c] else YOK for c in KOL]
             + [f'{TL} network=threads; okuma {okuma}'] for d in gunler])
    tp = []
    for c in KOL:
        g = S[c]
        son_g = max(g) if g else None
        tp.append([f'{BAS} - {BUGUN}', c, len(g), str(min(g)) if g else YOK, str(son_g) if g else YOK,
                   sayi(g[son_g]) if g else YOK, sayi(sum(g.values())) if g else YOK, f'{TL}; okuma {okuma}'])
        log(f'TOPLAM {c}: gun {tp[-1][2]}, ilk {tp[-1][3]}, son {tp[-1][4]} = {tp[-1][5]}, toplam {tp[-1][6]}')
    yaz_csv(out, 'TH_HESAP_TOPLAM.csv', ['donem', 'seri', 'veri_gunu', 'ilk_gun', 'son_gun', 'son_gun_degeri', 'toplam',
                                         'kaynak'], tp)
    # aggregation: 1. kosuda yalniz engagement destekli (digerleri 400 NotImplemented, ThreadsAnalyticsExtractor)
    j = guvenli(mc, 'aggregation_posts_engagement', '/v2/analytics/aggregation', dict(aralik, metric='engagement',
                subject='posts'), out)
    log(f'AGGREGATION posts/engagement: {json.dumps(mpb.veri(j), default=str)[:200] if j is not None else "HTTP hata"}')

    # 3) scheduler (12 Eki - bugun)
    ps, t = {}, datetime.combine(PLAN_BAS, datetime.min.time())
    son = datetime.combine(BUGUN + timedelta(days=1), datetime.min.time())
    while t < son:
        e = min(t + timedelta(days=5), son)
        j = guvenli(mc, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}',
                    'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}, out)
        for p in liste(j) or []:
            ps[str(p.get('id'))] = p
        t = e
    sch, kod_sch = [], {}
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'threads'), None)
        pd = p.get('publicationDate') or {}
        zt = zaman(pd)
        if not pr or not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        sch.append((zt, p, pr))
        if kod(pr.get('publicUrl')):
            kod_sch[kod(pr['publicUrl'])] = (zt, pr.get('status'), cift(p.get('text')))
    if sch:
        log(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:45]} | provider {sorted(sch[0][2])} | '
            f'threadsData {sch[0][1].get("threadsData")}')
    gun_dur, detay = defaultdict(Counter), []
    for zt, p, pr in sorted(sch, key=lambda x: x[0]):
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        h = pr.get('detail') or pr.get('error') or ''
        pd = p.get('publicationDate') or {}
        detay.append([zt, f"{pd.get('dateTime', '')} {pd.get('timezone', '')}".strip(), st, pr.get('detailedStatus') or '',
                      cift(p.get('text')), len(p.get('media') or []), bool(p.get('draft')), pr.get('publicUrl') or '',
                      (h if isinstance(h, str) else json.dumps(h, ensure_ascii=False))[:300]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'TH_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts providers[threads].status; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'TH_PLAN_DETAY.csv', ['plan_zamani_istanbul', 'publicationDate_ham', 'durum', 'ayrintili_durum', 'cift',
                                       'medya_sayisi', 'draft', 'link', 'hata_ayrinti'], detay)
    top = Counter(); [top.update(c) for c in gun_dur.values()]
    log(f'PLAN {PLAN_BAS} - {BUGUN}: planlanan {sum(top.values())}; durum {dict(top)}')
    for r in detay:
        log('PLAN ' + ' | '.join(str(v) for v in r))

    # 2) gonderi bazinda (1 Eki - bugun okunur; tablo 12 Eki+)
    j = guvenli(mc, 'posts_threads', '/v2/analytics/posts/threads',
                {'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, out)
    ls, bicim = gonderiler(j)
    log(f'/v2/analytics/posts/threads: {len(ls) if ls is not None else "yanit yok"} kayit ({bicim}); '
        f'alanlar {sorted(ls[0]) if ls else "-"}')
    satir, gun_top = [], defaultdict(Counter)
    for x in sorted(ls or [], key=lambda x: zaman(alan(x, 'publisheddate', 'publishedat', 'date'))):
        zt = zaman(alan(x, 'publisheddate', 'publishedat', 'date'))
        url = alan(x, 'permalink', 'url', 'link') or ''
        s = kod_sch.get(kod(url) or str(alan(x, 'shortcode') or ''), ('', '', ''))
        deg = [sayi(alan(x, f)) for _, f in GON]
        if zt[:10] >= str(PLAN_BAS):
            for (sut, _), v in zip(GON, deg):
                if v != YOK:
                    gun_top[zt[:10]][sut] += v
        satir.append([zt, json.dumps(alan(x, 'publisheddate', 'publishedat', 'date'), default=str), cift(alan(x, 'text')) or s[2],
                      alan(x, 'mediatype') or '', alan(x, 'isquotepost'), s[0], s[1]] + deg + [url, '/v2/analytics/posts/threads'])
    tablo = [r for r in satir if r[0][:10] >= str(PLAN_BAS)]
    log(f'GONDERI {BAS}+ : {len(satir)}; {PLAN_BAS}+ : {len(tablo)}')
    yaz_csv(out, 'TH_GONDERI.csv', ['yayin_zamani_istanbul', 'publishedDate_ham', 'cift', 'mediaType', 'isQuotePost',
                                    'plan_zamani', 'plan_durum'] + [g[0] for g in GON] + ['permalink', 'kaynak_uc'], tablo)
    for r in tablo:
        log('GONDERI ' + ' | '.join(str(v) for v in r[:-1]))
    yaz_csv(out, 'TH_GONDERI_TUMU_1EKI.csv', ['yayin_zamani_istanbul', 'publishedDate_ham', 'cift', 'mediaType', 'isQuotePost',
                                             'plan_zamani', 'plan_durum'] + [g[0] for g in GON] + ['permalink', 'kaynak_uc'], satir)

    # timelines gunluk degeri gonderi tablosunun yayin gunu toplamina esit mi (olcum; yorum yok)
    kars = []
    for sut, f in GON[:6]:
        for sj in ('posts', 'account'):
            c = f'{sj}.{f}'
            for d in gunler:
                if str(d) < str(PLAN_BAS):
                    continue
                tv = (S.get(c) or {}).get(d)
                gv = gun_top[str(d)].get(sut)
                kars.append([str(d), c, sayi(tv) if tv is not None else YOK, sayi(gv) if gv is not None else 0,
                             '' if tv is None else ('esit' if abs(tv - (gv or 0)) < 1e-9 else 'farkli')])
    yaz_csv(out, 'TH_TIMELINE_GONDERI_KARSILASTIRMA.csv', ['tarih', 'metrik', 'timelines_gunluk', 'gonderi_yayin_gunu_toplami',
                                                            'sonuc'], kars)
    log(f'KARSILASTIRMA timelines vs gonderi yayin gunu: {dict(Counter(r[4] or "timeline yok" for r in kars))}')

    # 4) metrik kaynagi
    for sut, f in GON:
        kaynak.append(['TH_GONDERI.csv', sut, '/v2/analytics/posts/threads', f'ThreadsPost.{f}', 'evet (sema)', bicim])
    kaynak += [['TH_GONDERI.csv', 'yayin_zamani_istanbul', '/v2/analytics/posts/threads', 'ThreadsPost.publishedDate',
                'evet (sema)', f'{TZ} cevrildi'],
               ['TH_GONDERI.csv', 'plan_zamani/plan_durum', '/v2/scheduler/posts', 'publicationDate, providers[threads].status',
                'evet (sema)', 'publicUrl kisa kodu ile eslesme'],
               ['TH_PLAN_*.csv', 'durum / hata_ayrinti', '/v2/scheduler/posts', 'providers[threads].status, detailedStatus, detail',
                'evet (sema)', '']]
    yaz_csv(out, 'TH_METRIK_KAYNAK.csv', ['tablo', 'sutun', 'uc', 'metrik_alan', 'belgede', 'yanit'], kaynak)
    tt = Counter()
    for r in tablo:
        for i, (sut, _) in enumerate(GON):
            if r[7 + i] != YOK:
                tt[sut] += r[7 + i]
    log(f'GONDERI TOPLAM ({len(tablo)} gonderi, {PLAN_BAS}+): {dict(tt)}')


if __name__ == '__main__':
    main()
