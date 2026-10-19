#!/usr/bin/env python3
"""Facebook anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve Facebook'a YAZMA YOK, yalniz GET.
Uclar ve metrik adlari data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json'dan (GET /v2/analytics/timelines aciklamasi):
  /v2/analytics/timelines network=facebook subject=account   belgede (account metrics): page_posts_impressions,
      page_actions_post_reactions_total, postsCount, postsInteractions, likes, pageFollows, pageImpressions, pageViews,
      page_daily_follows_unique, page_daily_unfollows_unique
      belgede OLMAYAN, 1. kosu 400 yanitinin "Valid values" listesinde olan (19 Eki 11:42 UTC): Follows, Unfollows,
      page_media_view, page_website_clicks_logged_in_unique, ctaClicks, page_total_actions
      (ayni listede reach / page_impressions_unique YOK: sayfa erisimi bu uctan okunamaz)
      subject=account 400 verirse ayni metrik subject'siz bir kez daha okunur (FB icin subject zorunlulugu belgede yok)
  /v2/analytics/timelines subject=posts|reels|stories         belgedeki posts / reels metrikleri; reels ve stories icin
      1. kosu "Valid values" listesindekiler (reels: post_total_media_view_unique, post_video_avg_time_watched,
      post_video_view_time, interactions; stories: count)
  /v2/analytics/aggregation, /stats/aggregations/facebook     sayfa toplami (ham)
  /v2/analytics/posts/facebook, /v2/analytics/reels/facebook  gonderi bazinda (FacebookPost / FacebookReel semasi)
  /stats/facebook/posts                                        gonderi bazinda ucuncu kaynak (totalMediaViewUnique, permalinkUrl)
  /v2/analytics/stories/facebook                               ham (sayi + alanlar loga)
  /v2/scheduler/posts                                          plan / yayin / hata (12 Eki - bugun)
Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok. Ham yanitlar HAM_*.json, ozet OZET.txt.
Kullanim: facebook.py TOKEN.json CIKTI_DIR"""
import csv
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
BAS, BUGUN = date(2026, 10, 1), date(2026, 10, 19)
PLAN_BAS = date(2026, 10, 12)
YOK = 'erisilemedi'
TL = '/v2/analytics/timelines'
# (metric, subject, belgede)
HESAP = [(m, 'account', True) for m in ('likes', 'pageFollows', 'page_daily_follows_unique', 'page_daily_unfollows_unique',
                                        'pageImpressions', 'page_posts_impressions', 'pageViews', 'postsCount',
                                        'postsInteractions', 'page_actions_post_reactions_total')] \
    + [(m, 'account', False) for m in ('Follows', 'Unfollows', 'page_media_view', 'page_website_clicks_logged_in_unique',
                                       'ctaClicks', 'page_total_actions')]
ICERIK = [(m, 'posts', True) for m in ('count', 'impressionsunique', 'impressions', 'reactions', 'comments', 'shares',
                                       'clicks', 'interactions', 'engagement')] \
    + [(m, 'reels', True) for m in ('count', 'blue_reels_play_count', 'post_impressions_unique',
                                    'post_video_likes_by_reaction_type', 'post_video_social_actions', 'engagement')] \
    + [(m, 'reels', False) for m in ('post_total_media_view_unique', 'post_video_avg_time_watched', 'post_video_view_time',
                                     'interactions')] \
    + [('count', 'stories', False)]
KUMULATIF = ('likes', 'pageFollows')   # toplam degil son gunun degeri
# gonderi tablosu: (sutun, {kaynak: alan}); ayni icerik birden cok uctan gelirse sira posts > reels > stats
GON = [('erisim', {'posts': 'impressionsUnique', 'reels': 'postImpressionsUnique', 'stats': 'impressionsUnique'}),
       ('medya_izlenme_tekil', {'stats': 'totalMediaViewUnique'}),
       ('gosterim', {'posts': 'impressions', 'stats': 'impressions'}),
       ('tepki', {'posts': 'reactions', 'reels': 'postVideoReactions', 'stats': 'reactions'}),
       ('yorum', {'posts': 'comments', 'stats': 'comments'}), ('paylasim', {'posts': 'shares', 'stats': 'shares'}),
       ('tiklama', {'posts': 'clicks', 'stats': 'clicks'}), ('link_tiklama', {'posts': 'linkclicks', 'stats': 'linkclicks'}),
       ('etkilesim_engagement', {'posts': 'engagement', 'reels': 'engagement', 'stats': 'engagement'}),
       ('reel_sosyal_eylem', {'reels': 'postVideoSocialActions'}),
       ('izlenme', {'posts': 'videoViews', 'reels': 'blueReelsPlayCount', 'stats': 'videoViews'}),
       ('reel_ort_izleme_sn', {'reels': 'postVideoAvgTimeWatchedSeconds'}),
       ('toplam_izleme_sn', {'posts': 'videoTimeWatched', 'reels': 'postVideoViewTimeSeconds', 'stats': 'videoTimeWatched'}),
       ('reel_sure_sn', {'reels': 'length'})]
KAYNAKLAR = (('/v2/analytics/posts/facebook', 'posts', 'postId'), ('/v2/analytics/reels/facebook', 'reels', 'reelId'),
             ('/stats/facebook/posts', 'stats', 'postId'))
SAYFA_ID = {'1331479546706857', '122109181653467288'}   # Metricool pageId ve yeni sayfa kimligi (URL'de); icerik kimligi DEGIL
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
OZET = None


class MC(mpb.MC):
    """Yalniz GET; hata govdesi 2000 karakter (mpb 300'de keser, 400 "Valid values" listesi kaybolur)."""
    def istek(self, yontem, yol, params=None, govde=None, yok404=False):
        assert yontem == 'GET'
        url = f'{mpb.API}{yol}?{urllib.parse.urlencode(dict(params or {}, userId=self.u, blogId=self.b))}'
        for deneme in range(4):
            b = mpb.BEKLE - (time.time() - self.son)
            if b > 0:
                time.sleep(b)
            r = urllib.request.Request(url, method='GET', headers={'X-Mc-Auth': self.t, 'Accept': 'application/json'})
            try:
                with urllib.request.urlopen(r, timeout=60) as y:
                    self.son = time.time(); g = y.read()
                    return json.loads(g) if g else None
            except urllib.error.HTTPError as e:
                self.son = time.time()
                if e.code == 429 and deneme < 3:
                    s = int(e.headers.get('Retry-After') or 60); print(f'429: {s} sn bekleniyor', flush=True); time.sleep(s); continue
                if e.code in (502, 503, 504) and deneme < 3:
                    time.sleep(10 * (deneme + 1)); continue
                raise SystemExit(f'HTTP {e.code} GET {yol}: ' + e.read()[:2000].decode('utf-8', 'replace').replace(self.t, '***'))


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
    """Sayi; sayisal degerli sozluk (orn. tepki turleri) ise toplami."""
    if isinstance(v, dict):
        n = [x for x in v.values() if isinstance(x, (int, float)) and not isinstance(x, bool)]
        return sayi(sum(n)) if n else YOK
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
        log(f'{ad}: HATA {str(e)[:400]}'); ham(out, ad, {'_hata': str(e)})
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


def alan(x, ad):
    """Alan adi belgede camelCase; yanit farkli harf buyuklugu verirse de bulunur."""
    if not ad or not isinstance(x, dict):
        return None
    if ad in x:
        return x[ad]
    return next((v for k, v in x.items() if k.lower() == ad.lower()), None)


def kimlikler(*metin):
    """Icerik kimligi: her metindeki (postId 'sayfa_gonderi', .../posts/N, /reel/N) SON 8+ haneli sayi; sayfa kimlikleri haric.
    1. kosu: tum sayilar alininca sayfa kimligi 122109181653467288 ortak cikti, 7 gonderi tek kayitta birlesti."""
    out = set()
    for m in metin:
        s = [x for x in re.findall(r'\d{8,}', str(m or '')) if x not in SAYFA_ID]
        if s:
            out.add(s[-1])
    return out


def zaman(x):
    """Yayin zamani -> Istanbul. Alan: publishedAt | created | timestamp; {dateTime, timezone}, ISO metin ya da epoch."""
    for k in ('publishedAt', 'created', 'timestamp', 'createdTime'):
        v = alan(x, k)
        if v in (None, ''):
            continue
        t, tz = (v.get('dateTime'), v.get('timezone')) if isinstance(v, dict) else (v, None)
        try:
            if isinstance(t, (int, float)):
                d = datetime.fromtimestamp(t / 1000 if t > 1e11 else t, timezone.utc)
            else:
                d = datetime.fromisoformat(str(t).replace('Z', '+00:00'))
                if d.tzinfo is None:
                    d = d.replace(tzinfo=ZoneInfo(tz or TZ))
            return d.astimezone(ZoneInfo(TZ)).strftime('%Y-%m-%dT%H:%M:%S'), f'{k}={t} {tz or ""}'.strip()
        except Exception:
            return str(t), f'{k}={t} {tz or ""}'.strip()
    return '', ''


def main():
    global OZET
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    log(f'OKUMA ANI (UTC): {okuma}; userId {mc.u}; blogId {mc.b}; donem {BAS} - {BUGUN} ({TZ})')
    aralik = {'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}
    kaynak = []   # FB_METRIK_KAYNAK.csv

    # 1) sayfa geneli gunluk + icerik timeline'lari
    def timeline_oku(tanim, csv_ad):
        kol, S = [], {}
        for m, subj, belgede in tanim:
            ad = f'timeline_{subj}_{m}'
            p = dict(aralik, network='facebook', metric=m, subject=subj)
            j = guvenli(mc, ad, TL, p, out)
            if j is None and subj == 'account':
                p.pop('subject'); ad += '_subjectsiz'
                j = guvenli(mc, ad, TL, p, out)
            ss = seriler(j) if j is not None else {}
            durum = 'HTTP hata' if j is None else ('bos yanit' if not ss else
                                                   ('deger yok' if not any(ss.values()) else 'veri var'))
            log(f'TIMELINE {subj}/{m} ({"belgede" if belgede else "belgede YOK, Valid values listesinde"}; {ad}): {durum}; '
                + '; '.join(f'{k}: {len(g)} gun, toplam {sayi(sum(g.values()))}' for k, g in ss.items()))
            if not ss:
                ss = {m: None}
            for k, g in ss.items():
                c = (m if subj == 'account' else f'{subj}.{m}') + ('' if len(ss) == 1 else f'[{k}]')
                kol.append(c); S[c] = g
                kaynak.append([csv_ad, c, TL, f'network=facebook metric={m}' + (' subject YOK (subject=account 400)' if ad.endswith('_subjectsiz') else f' subject={subj}')
                               + ('' if len(ss) == 1 else f' seri={k}'), 'evet' if belgede else 'hayir (1. kosu Valid values listesinde)', durum])
        yaz_csv(out, csv_ad, ['tarih'] + kol + ['kaynak'],
                [[str(d)] + [sayi(S[c].get(d)) if S[c] and d in S[c] else YOK for c in kol]
                 + [f'{TL} network=facebook; okuma {okuma}'] for d in gunler])
        yaz_csv(out, csv_ad.replace('GUNLUK', 'TOPLAM'), ['donem'] + kol + ['kaynak'],
                [[f'{BAS} - {BUGUN} ({"/".join(KUMULATIF)}: ilk ve son gunun degeri; digerleri toplam)']
                 + [(f'{sayi(S[c][min(S[c])])} -> {sayi(S[c][max(S[c])])} ({min(S[c])} -> {max(S[c])})'
                     if c in KUMULATIF else sayi(sum(S[c].values()))) if S[c] else YOK for c in kol]
                 + [f'{TL}; okuma {okuma}']])
    timeline_oku(HESAP, 'FB_SAYFA_GUNLUK.csv')
    timeline_oku(ICERIK, 'FB_ICERIK_GUNLUK.csv')

    for m in ('likes', 'pageFollows'):
        j = guvenli(mc, f'aggregation_account_{m}', '/v2/analytics/aggregation', dict(aralik, network='facebook', metric=m,
                    subject='account'), out)
        log(f'AGGREGATION account/{m}: {json.dumps(mpb.veri(j), default=str)[:200] if j is not None else "HTTP hata"}')
    j = guvenli(mc, 'stats_aggregations_facebook', '/stats/aggregations/facebook',
                {'start': f'{BAS:%Y%m%d}', 'end': f'{BUGUN:%Y%m%d}', 'timezone': TZ}, out)
    log(f'STATS/AGGREGATIONS/facebook (eski uc): {json.dumps(j, default=str)[:800] if j is not None else "HTTP hata"}')

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
    sch = []
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'facebook'), None)
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        if not pr or not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        fd = p.get('facebookData') or {}
        tur = 'Reel' if (fd.get('type') or '').upper() == 'REEL' else ('Story' if (fd.get('type') or '').upper() == 'STORY'
                                                                       else 'gonderi')
        sch.append((zt, p, pr, tur))
    if sch:
        log(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:30]} | provider {sorted(sch[0][2])} | facebookData {sch[0][1].get("facebookData")}')
    gun_dur, detay = defaultdict(Counter), []
    for zt, p, pr, tur in sorted(sch, key=lambda x: x[0]):
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        h = pr.get('detail') or pr.get('error') or ''
        detay.append([zt, (p.get('publicationDate') or {}).get('timezone') or '', tur, (p.get('facebookData') or {}).get('type') or '',
                      st, pr.get('detailedStatus') or '', cift(p.get('text')), len(p.get('media') or []),
                      pr.get('publicUrl') or '', (h if isinstance(h, str) else json.dumps(h, ensure_ascii=False))[:200]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'FB_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts providers[facebook].status; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'FB_PLAN_DETAY.csv', ['plan_zamani', 'saat_dilimi', 'tur', 'facebookData_type', 'durum', 'ayrintili_durum',
                                       'cift', 'medya_sayisi', 'link', 'hata_ayrinti'], detay)
    top = Counter(); [top.update(c) for c in gun_dur.values()]
    log(f'PLAN {PLAN_BAS} - {BUGUN}: planlanan {sum(top.values())}; durum {dict(top)}; tur {dict(Counter(x[3] for x in sch))}')
    for r in detay:
        log(f'PLAN {r[0]} {r[2]} {r[4]} {r[5]} {r[6]} medya={r[7]} {r[8]} {r[9][:120]}')

    # 2) gonderi bazinda (12 Eki - bugun)
    a2 = {'from': f'{PLAN_BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}
    kay = {}   # kimlik -> {'posts': x, 'reels': y}
    eski = {'start': f'{PLAN_BAS:%Y%m%d}', 'end': f'{BUGUN:%Y%m%d}', 'timezone': TZ}
    for uc, ad, idk in KAYNAKLAR:
        j = guvenli(mc, 'stats_facebook_posts' if ad == 'stats' else f'{ad}_facebook', uc, eski if ad == 'stats' else a2, out)
        ls = liste(j)
        log(f'{uc}: {len(ls) if ls is not None else "yanit yok"} kayit; alanlar {sorted(ls[0]) if ls else "-"}')
        for x in ls or []:
            ids = kimlikler(alan(x, idk), alan(x, 'link'), alan(x, 'reelUrl'), alan(x, 'url'), alan(x, 'permalinkUrl'))
            k = next((kk for kk in kay if ids & kay[kk]['_id']), None) or (sorted(ids)[0] if ids else f'{ad}_{len(kay)}')
            r = kay.setdefault(k, {'_id': set()})
            r['_id'] |= ids
            if ad in r:
                log(f'  {ad}: {k} ayni uctan iki kez geldi (ilk kayit tutulur)'); continue
            r[ad] = x
    ls = liste(guvenli(mc, 'stories_facebook', '/v2/analytics/stories/facebook', a2, out))
    log(f'/v2/analytics/stories/facebook (ham): {len(ls) if ls is not None else "yanit yok"} kayit; '
        f'alanlar {sorted(ls[0]) if ls and isinstance(ls[0], dict) else "-"}')

    plan_id = {}
    for zt, p, pr, tur in sch:
        for i in kimlikler(pr.get('publicUrl'), pr.get('id')):
            plan_id[i] = (zt, pr.get('status'), tur, cift(p.get('text')))
    satir, tur_deger, eslesen_plan = [], defaultdict(lambda: defaultdict(list)), set()
    for k, r in sorted(kay.items(), key=lambda kv: zaman(kv[1].get('posts') or kv[1].get('reels') or kv[1].get('stats'))[0]):
        xp, xr, xs = r.get('posts'), r.get('reels'), r.get('stats')
        zi, zham = zaman(xp or xr or xs)
        s = next((plan_id[i] for i in r['_id'] if i in plan_id), None)
        esl = 'kimlik'
        if s is None and zi:   # kimlik eslesmezse: ayni gun +-90 dk icindeki plan
            yak = [(abs((datetime.fromisoformat(zi) - datetime.fromisoformat(zt[:19])).total_seconds()), zt, pr, tur, p)
                   for zt, p, pr, tur in sch]
            yak = [y for y in yak if y[0] <= 5400]
            if yak:
                _, zt, pr, tur, p = min(yak, key=lambda y: y[0]); s = (zt, pr.get('status'), tur, cift(p.get('text'))); esl = 'saat (+-90 dk)'
        s = s or ('', '', '', '')
        if s[0]:
            eslesen_plan.add(s[0])
        tip = str(alan(xp, 'type') or alan(xs, 'type') or '')
        tur = 'Reel' if xr is not None or s[2] == 'Reel' else 'gonderi'
        deg, kaynak_alan = [], []
        for sut, alanlar in GON:
            v, nereden = None, ''
            for kn in ('posts', 'reels', 'stats'):
                if kn in alanlar and alan(r.get(kn), alanlar[kn]) is not None:
                    v, nereden = alan(r.get(kn), alanlar[kn]), f'{kn}.{alanlar[kn]}'; break
            deg.append(sayi(v)); kaynak_alan.append(nereden)
            if sayi(v) != YOK:
                tur_deger[tur][sut].append(sayi(v))
        tur_deger[tur]['_n'].append(1)
        metin = ' '.join(str(alan(x, a) or '') for x in (xp, xr, xs) for a in ('text', 'description'))
        satir.append([zi, zham, tur, tip, cift(metin) or s[3], s[0], s[1], esl if s[0] else ''] + deg
                     + [json.dumps(alan(xr, 'postVideoReactions'), ensure_ascii=False) if xr is not None else '',
                        json.dumps(alan(xr, 'postVideoSocialActions'), ensure_ascii=False) if xr is not None else '',
                        alan(xp, 'link') or alan(xs, 'link') or alan(xr, 'reelUrl') or '', '+'.join(a for a in ('posts', 'reels', 'stats') if a in r),
                        ';'.join(sorted({a for a in kaynak_alan if a}))])
    yaz_csv(out, 'FB_GONDERI.csv', ['yayin_zamani_istanbul', 'zaman_ham', 'tur', 'metricool_type', 'cift', 'plan_zamani',
                                    'plan_durum', 'plan_eslesme'] + [g[0] for g in GON]
            + ['reel_tepki_ham', 'reel_sosyal_eylem_ham', 'link', 'kaynak_uc', 'kullanilan_alanlar'], satir)
    for r in satir:
        log('GONDERI ' + ' | '.join(str(v) for v in r[:-3]))
    log(f'ESLESMEYEN PLAN (analitikte yok): {[d[0] + " " + d[2] + " " + d[4] for d in detay if d[0] not in eslesen_plan]}')

    # 3) gonderi / Reel karsilastirmasi (yalniz olculen degerler)
    kar = []
    for tur, d in sorted(tur_deger.items()):
        for sut, _ in GON:
            v = d.get(sut) or []
            kar.append([tur, len(d['_n']), sut, len(v), sayi(sum(v) / len(v)) if v else YOK, sayi(sum(v)) if v else YOK])
    yaz_csv(out, 'FB_TUR_KARSILASTIRMA.csv', ['tur', 'icerik_sayisi', 'olcu', 'olculen_n', 'ortalama', 'toplam'], kar)
    for r in kar:
        if r[3]:
            log(f'TUR {r[0]} (n={r[1]}) {r[2]}: olculen {r[3]}, ort {r[4]}, toplam {r[5]}')

    # 5) metrik kaynagi
    uc_ad = {ad: uc for uc, ad, _ in KAYNAKLAR}
    for sut, alanlar in GON:
        kaynak.append(['FB_GONDERI.csv', sut, ' | '.join(uc_ad[k] for k in alanlar), ' | '.join(f'{k}.{a}' for k, a in alanlar.items()),
                       'evet (FacebookPost/FacebookReel semasi)' if sut != 'medya_izlenme_tekil' else 'hayir (1. kosu yanitinda)',
                       'birden cok uctan varsa sira posts > reels > stats; kullanilan alan: kullanilan_alanlar sutunu'])
    kaynak += [['FB_GONDERI.csv', 'plan_zamani/plan_durum', '/v2/scheduler/posts', 'publicationDate.dateTime, providers[facebook].status',
                'evet (sema)', 'publicUrl/postId kimligi, yoksa +-90 dk saat eslesmesi (plan_eslesme sutunu)'],
               ['FB_PLAN_*.csv', 'durum', '/v2/scheduler/posts', 'providers[facebook].status, detailedStatus, facebookData.type, media',
                'evet (sema)', '']]
    yaz_csv(out, 'FB_METRIK_KAYNAK.csv', ['tablo', 'sutun', 'uc', 'metrik_alan', 'belgede', 'yanit'], kaynak)


if __name__ == '__main__':
    main()
