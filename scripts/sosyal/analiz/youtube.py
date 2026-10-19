#!/usr/bin/env python3
"""YouTube Shorts anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve YouTube'a YAZMA YOK, yalniz GET.
Uclar ve metrik adlari (data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json):
  /v2/analytics/timelines network=youtube  belgede "For Youtube": views, interactions, likes, dislikes, comments, shares;
                                           scope belgede 'viewed'/'published', API'de gecerli: all, publishedInRange, revenue
                                           (1. kosu 400 yaniti). Abone ve izlenme suresi belgede YOK:
                                           belgesiz adlar (ABONE_ADAY, SURE_ADAY) denenir, CSV'de "belgesiz" diye isaretlenir.
  /v2/analytics/aggregation network=youtube 1. kosuda NotImplemented (YouTubeAnalyticsExtractor); yalniz views denenir
  /v2/analytics/posts/youtube              /stats/youtube/videos'un belgedeki halefi ("Deprecated. Use GET
                                           /v2/analytics/posts/youtube"); sema YouTubeGlobalVideo: videoId, publishedAt,
                                           views, engagedViews, watchMinutes, averageViewDuration, likes, dislikes, comments,
                                           shares, duration, thumbnailUrl, watchUrl. Bos/hata ise /stats/youtube/videos.
  /v2/settings/brands/connections/youtube/media-feed  kanal RSS son 15 video (videoId, publishedAt, thumbnailUrl)
  /v2/scheduler/posts                      plan / yayin / hata (13 Eki - bugun), providers[network=youtube].status/detail,
                                           youtubeData (type, category, isAiGeneratedContent), videoThumbnailUrl (bizim kapak)
Kapak: i.ytimg.com oar2 / hq720 / hqdefault + bizim kapak + videonun 0. ve 8. sn karesi; olcum sosyal_kapak_oku.py
(g, fark, sinifla: siyah = parlaklik < 3 ya da en yakin referans 0 sn karesi; fark < 12 = benzer). Tahmin yok:
Metricool bir degeri vermiyorsa "erisilemedi". Ham yanitlar HAM_*.json, kucuk resimler KAPAK_*.jpg.
Kullanim: youtube.py TOKEN.json CIKTI_DIR IS_DIR"""
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yukle(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(KOK, dosya))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


mpb = yukle('mpb', 'metricool_pin_baslik.py')
sko = yukle('sko', 'sosyal_kapak_oku.py')      # g, fark, sinifla, indir, gorsel_mi, kisa (degistirilmez)

TZ = 'Europe/Istanbul'
BAS, BUGUN = date(2026, 10, 1), date(2026, 10, 19)
PLAN_BAS = date(2026, 10, 13)
METRIK = ['views', 'interactions', 'likes', 'dislikes', 'comments', 'shares']          # belgede
# 1. kosu (39246155757) ham yanitlari: 'subscribers' gecersiz, gecerli alanlar "viewerPercentage, totalViews, totalLikes,
# totalDisLikes, totalComments, totalVideos, totalSubscribers, subscribersGained, subscriber..." (mesaj 300 krk kesik);
# scope 'viewed'/'published' gecersiz, gecerli "all, publishedInRange, revenue"; aggregation YouTube'da NotImplemented.
ABONE_ADAY = ['totalSubscribers', 'subscribersGained', 'subscribersLost', 'viewerPercentage', 'totalViews']   # belgesiz
SURE_ADAY = ['estimatedMinutesWatched', 'averageViewDuration']                                              # belgesiz
SCOPE = [('yok', {}), ('all', {'scope': 'all'}), ('publishedInRange', {'scope': 'publishedInRange'})]
VID_K = [('views', 'goruntulenme'), ('engagedViews', 'etkin_goruntulenme'), ('likes', 'begeni'), ('dislikes', 'begenmeme'),
         ('comments', 'yorum'), ('shares', 'paylasim'), ('watchMinutes', 'izlenme_dk'),
         ('averageViewDuration', 'ort_izleme_sn'), ('averageViewPercentage', 'ort_izlenme_orani'), ('duration', 'sure')]
BURC = ('ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN',
        'AQUARIUS', 'PISCES')
YOK = 'erisilemedi'


def yaz_csv(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def ham(out, ad, veri):
    json.dump(veri, open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def sayi(v):
    return YOK if v is None else (int(v) if float(v).is_integer() else round(v, 4))


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


def cift(*metinler):
    """'X and Y' ya da dosya/baslikta iki burc adi; alfabetik anahtar (CLAUDE.md)."""
    for t in metinler:
        m = re.search(r'\b([A-Z][a-z]+) (?:and|&) ([A-Z][a-z]+)\b', t or '')
        if m and m.group(1).upper() in BURC and m.group(2).upper() in BURC:
            return '_'.join(sorted((m.group(1).upper(), m.group(2).upper())))
    for t in metinler:
        b = re.findall(r'(?<![A-Z])(' + '|'.join(BURC) + r')(?![A-Z])', (t or '').upper())
        if len(b) >= 2:
            return '_'.join(sorted(b[:2]))
    return ''


def video_id(url):
    m = re.search(r'(?:shorts/|watch\?v=|youtu\.be/|/vi/|embed/)([A-Za-z0-9_-]{11})', url or '')
    return m.group(1) if m else ''


def yerel(t):
    """ISO metin ya da Metricool {dateTime, timezone} (publishedAt Europe/Madrid gelir) -> Istanbul yerel."""
    if isinstance(t, dict) and t.get('dateTime'):
        try:
            d = datetime.fromisoformat(t['dateTime'])
            if d.tzinfo is None:
                d = d.replace(tzinfo=ZoneInfo(t.get('timezone') or 'UTC'))
            return d.astimezone(ZoneInfo(TZ)).strftime('%Y-%m-%d %H:%M')
        except (ValueError, KeyError):
            return str(t)
    if not isinstance(t, str) or not t:
        return str(t or '')
    try:
        d = datetime.fromisoformat(t.replace('Z', '+00:00'))
    except ValueError:
        return t
    return (d.astimezone(ZoneInfo(TZ)) if d.tzinfo else d).strftime('%Y-%m-%d %H:%M')


def zaman_dt(p):
    pd = p.get('publicationDate') or {}
    return pd.get('dateTime') or '', pd.get('timezone') or ''


def kare(video, sn, yol):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(sn), '-i', video, '-frames:v', '1', yol],
                       capture_output=True, text=True)
    return os.path.exists(yol) and r.returncode == 0


def kapak_olc(vid, bizim_url, video_url, isd, out):
    """Her ytimg varyanti ayri satir. Referans: bizim kapak, video 0 sn ve 8 sn karesi."""
    ref = {}
    if bizim_url:
        y = os.path.join(isd, f'{vid}_bizim.img')
        kod = sko.indir(bizim_url, y)
        if sko.gorsel_mi(y):
            ref['bizim'] = sko.g(y)
        else:
            print(f'KAPAK {vid}: bizim kapak okunamadi ({kod})')
    if video_url:
        v = os.path.join(isd, f'{vid}.mp4')
        kod = sko.indir(video_url, v)
        for sn in (0, 8):
            k = os.path.join(isd, f'{vid}_k{sn}.png')
            if os.path.exists(v) and kare(v, sn, k):
                ref[f'k{sn}'] = sko.g(k)
        if 'k0' not in ref:
            print(f'KAPAK {vid}: video karesi alinamadi ({kod})')
    sat = []
    for ad in ('oar2', 'hq720', 'hqdefault'):
        url = f'https://i.ytimg.com/vi/{vid}/{ad}.jpg'
        y = os.path.join(isd, f'{vid}_{ad}.jpg')
        kod = sko.indir(url, y)
        boy = sko.gorsel_mi(y) if kod.startswith('200') else None
        if not boy:
            sat.append([ad, url, kod.split('|')[0], '', YOK, YOK, YOK, YOK, YOK]); continue
        a = sko.g(y)
        d = {'parlaklik': round(float(a.mean()), 1)}
        if 'bizim' in ref:
            d['fark_bizim_kapak'] = sko.fark(a, ref['bizim'])
        kf = {sn: sko.fark(a, ref[f'k{sn}']) for sn in (0, 8) if f'k{sn}' in ref}
        if kf:
            sn = min(kf, key=kf.get)
            d['en_yakin_kare_sn'], d['en_yakin_kare_fark'] = (0.0 if sn == 0 else sn), kf[sn]
        os.replace(y, os.path.join(out, f'KAPAK_{vid}_{ad}.jpg'))
        sat.append([ad, url, '200', f'{boy[0]}x{boy[1]}', d['parlaklik'], d.get('fark_bizim_kapak', YOK),
                    kf.get(0, YOK), kf.get(8, YOK), sko.sinifla(d)])
    bp = round(float(ref['bizim'].mean()), 1) if 'bizim' in ref else YOK
    k0 = round(float(ref['k0'].mean()), 1) if 'k0' in ref else YOK
    return sat, bp, k0


def main():
    tok, out, isd = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True); os.makedirs(isd, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'OKUMA ANI (UTC): {okuma}')
    kay = []   # sutun -> kaynak eslemesi
    ara = {'network': 'youtube', 'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}

    # 1) kanal geneli gunluk: belgedeki metrikler x scope; abone / izlenme suresi belgesiz adaylar
    S, KOL = {}, []
    for m in METRIK + ABONE_ADAY + SURE_ADAY:
        belge = 'belgede' if m in METRIK else 'belgesiz'
        for sc, ek in SCOPE:
            j = guvenli(mc, f'timeline_{m}_{sc}', '/v2/analytics/timelines', dict(ara, metric=m, **ek), out)
            g = seri(j) if j is not None else None
            ad = f'{m}' + ('' if sc == 'yok' else f'_{sc}')
            print(f'TIMELINE {m} scope={sc} ({belge}): ' + ('yanit yok' if g is None else
                  f'{len(g)} gun, toplam {sayi(sum(g.values()))}, ilk {min(g) if g else "-"}, son {max(g) if g else "-"}'))
            if g:
                S[ad] = g; KOL.append(ad)
                kay.append(['YT_KANAL_GUNLUK.csv', ad, '/v2/analytics/timelines', f'network=youtube metric={m} '
                            f'{"scope=" + sc if sc != "yok" else "scope yok"}', f'{belge}; gunluk deger (dateTime ilk 10 karakter)'])
            if m not in METRIK and sc == 'yok' and j is None:
                break      # belgesiz aday scope'suz 400 ise (gecersiz alan) scope'lu deneme yapilmaz
    for m in METRIK + ABONE_ADAY:
        if not any(k == m or k.startswith(m + '_') for k in KOL):
            kay.append(['YT_KANAL_GUNLUK.csv', m, '/v2/analytics/timelines', f'network=youtube metric={m}',
                        f'{"belgede" if m in METRIK else "belgesiz"}; veri yok -> {YOK}'])
    yaz_csv(out, 'YT_KANAL_GUNLUK.csv', ['tarih'] + KOL + ['kaynak'],
            [[str(d)] + [sayi(S[a].get(d)) if d in S[a] else YOK for a in KOL]
             + [f'/v2/analytics/timelines network=youtube; okuma {okuma}'] for d in gunler])
    print(f'KANAL GUNLUK veri olan sutunlar: {KOL or "yok"}; abone: '
          f'{[k for k in KOL if k.split("_")[0] in ABONE_ADAY] or YOK}; sure: {[k for k in KOL if k.split("_")[0] in SURE_ADAY] or YOK}')
    ag = []
    for m in METRIK[:1]:
        j = guvenli(mc, f'aggregation_{m}', '/v2/analytics/aggregation', dict(ara, metric=m), out)
        v = mpb.veri(j) if j is not None else None
        v = v if isinstance(v, (int, float)) else (v.get('value') if isinstance(v, dict) else None)
        tl = sum(S[m].values()) if m in S else None
        ag.append([f'{BAS} - {BUGUN}', m, 'belgede' if m in METRIK else 'belgesiz', sayi(v) if isinstance(v, (int, float)) else YOK,
                   sayi(tl), '/v2/analytics/aggregation | /v2/analytics/timelines toplam', okuma])
        print(f'AGGREGATION {m}: {ag[-1][3]} | timelines toplam {ag[-1][4]}')
    yaz_csv(out, 'YT_KANAL_TOPLAM.csv', ['donem', 'metrik', 'belge', 'aggregation', 'timelines_toplam', 'kaynak', 'okuma'], ag)

    # 3) scheduler (13 Eki - bugun+1)
    ps, t = {}, datetime.combine(PLAN_BAS, datetime.min.time())
    son = datetime.combine(BUGUN + timedelta(days=2), datetime.min.time())
    while t < son:
        e = min(t + timedelta(days=5), son)
        j = guvenli(mc, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}',
                    'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}, out)
        for p in liste(j) or []:
            ps[str(p.get('id'))] = p
        t = e
    sch, vid_sch = [], {}
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'youtube'), None)
        if not pr:
            continue
        zt, ztz = zaman_dt(p)
        sch.append((zt, p, pr))
        if video_id(pr.get('publicUrl')):
            vid_sch[video_id(pr['publicUrl'])] = (zt, p, pr)
    print(f'SCHEDULER YouTube gonderi ({PLAN_BAS} - {BUGUN + timedelta(days=1)}): {len(sch)}; '
          f'durumlar {dict(Counter(x[2].get("status") for x in sch))}')
    if sch:
        print(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:45]} | provider {sorted(sch[0][2])} | '
              f'youtubeData {sorted(sch[0][1].get("youtubeData") or {})}')
    gun_dur, detay = defaultdict(Counter), []
    for zt, p, pr in sorted(sch, key=lambda x: x[0]):
        if not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        h = pr.get('detail') or pr.get('error') or ''
        yd = p.get('youtubeData') or {}
        medya = (p.get('media') or [''])[0]
        medya = medya.get('url', '') if isinstance(medya, dict) else medya
        detay.append([zt, zaman_dt(p)[1], st, cift(yd.get('title'), p.get('text'), sko.kisa(medya)), video_id(pr.get('publicUrl')),
                      pr.get('publicUrl') or '', yd.get('title') or '', yd.get('type', ''), yd.get('category', ''),
                      yd.get('isAiGeneratedContent', ''), yd.get('privacy', ''), bool(p.get('videoThumbnailUrl')),
                      p.get('videoCoverMilliseconds', ''), os.path.basename(sko.kisa(medya)),
                      (h if isinstance(h, str) else json.dumps(h, ensure_ascii=False))[:300]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'YT_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'YT_PLAN_DETAY.csv', ['yayin_zamani', 'saat_dilimi', 'durum', 'cift', 'video_id', 'youtube_link', 'baslik',
                                       'youtubeData.type', 'youtubeData.category', 'youtubeData.isAiGeneratedContent',
                                       'youtubeData.privacy', 'videoThumbnailUrl_var', 'videoCoverMilliseconds',
                                       'medya_dosya', 'hata_ayrinti'], detay)
    tp = Counter(); [tp.update(c) for c in gun_dur.values()]
    print(f'PLAN {PLAN_BAS} - {BUGUN}: planlanan {sum(tp.values())}; {dict(tp)}')
    for r in detay:
        print('PLAN', r[0], r[2], r[3], r[4], 'tip', r[7], 'kat', r[8], 'AI', r[9], 'kapak', r[11], r[14][:120])
    for zt, p, pr in sch:
        if (pr.get('status') or '') not in ('PUBLISHED', 'PENDING'):
            print('HATA_PROVIDER', zt, json.dumps(pr, ensure_ascii=False, default=str)[:800])
            print('HATA_GONDERI_ALANLARI', zt, {k: v for k, v in p.items() if re.search(r'err|fail|warn|detail|status', k, re.I)})
    kay += [['YT_PLAN_*.csv', 'durum', '/v2/scheduler/posts', 'providers[network=youtube].status', ''],
            ['YT_PLAN_DETAY.csv', 'hata_ayrinti', '/v2/scheduler/posts', 'providers[network=youtube].detail', ''],
            ['YT_PLAN_DETAY.csv', 'yayin_zamani', '/v2/scheduler/posts', 'publicationDate.dateTime', 'publicationDate.timezone'],
            ['YT_PLAN_DETAY.csv', 'youtubeData.*', '/v2/scheduler/posts', 'youtubeData (ScheduledPostYoutubeData)', ''],
            ['YT_PLAN_DETAY.csv', 'videoThumbnailUrl_var', '/v2/scheduler/posts', 'videoThumbnailUrl', 'bizim kapak']]

    # 2) video bazinda
    vids, kaynak_uc = None, ''
    for yol, prm in (('/v2/analytics/posts/youtube', {'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}),
                     ('/stats/youtube/videos', {'start': f'{BAS:%Y%m%d}', 'end': f'{BUGUN:%Y%m%d}', 'timezone': TZ})):
        j = guvenli(mc, 'posts_youtube' if 'v2' in yol else 'stats_youtube_videos', yol, prm, out)
        v = liste(j)
        print(f'{yol}: {len(v) if v is not None else "yanit yok"} video; '
              f'alanlar {sorted({k for x in v or [] for k in x})}')
        if v:
            vids, kaynak_uc = v, yol; break
    fj = guvenli(mc, 'media_feed', '/v2/settings/brands/connections/youtube/media-feed', {}, out)
    fv = mpb.veri(fj) if fj is not None else None
    feed = (fv.get('videos') if isinstance(fv, dict) else None) or []
    print(f'MEDIA-FEED: {len(feed) if fj is not None else "yanit yok"} video; '
          + ', '.join(f"{x.get('videoId')} {x.get('publishedAt')}" for x in feed))
    yaz_csv(out, 'YT_MEDIA_FEED.csv', ['video_id', 'yayin_zamani', 'yayin_zamani_istanbul', 'kaynak'],
            [[x.get('videoId'), x.get('publishedAt'), yerel(x.get('publishedAt')),
              f'/v2/settings/brands/connections/youtube/media-feed; okuma {okuma}'] for x in feed])

    an = {}
    for v in vids or []:
        vid = str(v.get('videoId') or video_id(v.get('watchUrl')) or '')
        if vid:
            an[vid] = v
    tum = set(an) | {i for i, (zt, _, _) in vid_sch.items() if zt[:10] >= str(PLAN_BAS)} \
        | {x.get('videoId') for x in feed if yerel(x.get('publishedAt'))[:10] >= str(PLAN_BAS)}
    satir, kap = [], []
    for vid in sorted(tum, key=lambda i: yerel((an.get(i) or {}).get('publishedAt')) or (vid_sch.get(i) or ('',))[0]):
        v = an.get(vid, {})
        zt = yerel(v.get('publishedAt'))
        if zt[:10] and zt[:10] < str(PLAN_BAS):
            continue
        szt, sp_, spr = vid_sch.get(vid, ('', {}, {}))
        yd = sp_.get('youtubeData') or {}
        medya = (sp_.get('media') or [''])[0]
        medya = medya.get('url', '') if isinstance(medya, dict) else medya
        deg = [v.get(k) if isinstance(v.get(k), (int, float)) else None for k, _ in VID_K]
        sure = v.get('duration') if isinstance(v.get('duration'), str) and v.get('duration') else None
        c = cift(yd.get('title'), v.get('title'), sp_.get('text'), sko.kisa(medya))
        satir.append([zt or YOK, szt, vid, c] + [sayi(x) for x in deg[:-1]] + [sure or sayi(deg[-1])]
                     + ['var' if vid in an else f'{kaynak_uc or "analytics"} yanitinda yok', spr.get('status', ''),
                        v.get('title') or yd.get('title') or '', v.get('watchUrl') or spr.get('publicUrl') or ''])
        ks, bp, k0 = kapak_olc(vid, sp_.get('videoThumbnailUrl'), medya, isd, out)
        for r in ks:
            kap.append([szt or zt, vid, c, spr.get('status', ''), bool(sp_.get('videoThumbnailUrl')), bp, k0] + r)
    yaz_csv(out, 'YT_VIDEO.csv', ['yayin_zamani_istanbul', 'scheduler_zamani', 'video_id', 'cift'] + [a for _, a in VID_K]
            + ['analytics_kaydi', 'scheduler_durum', 'baslik', 'link'], satir)
    for r in satir:
        print('VIDEO', r[:4], dict(zip([a for _, a in VID_K], r[4:4 + len(VID_K)])), r[4 + len(VID_K)])
    for k, a in VID_K:
        kay.append(['YT_VIDEO.csv', a, kaynak_uc or '/v2/analytics/posts/youtube', k,
                    ('YouTubeGlobalVideo semasinda var' if k != 'averageViewPercentage' else 'semada YOK; yanitta varsa yazilir')
                    + '; birim Metricool yanitindaki gibi'])
    kay.append(['YT_VIDEO.csv', 'yayin_zamani_istanbul', kaynak_uc or '/v2/analytics/posts/youtube', 'publishedAt', f'{TZ} cevrildi'])

    # 4) kapak
    yaz_csv(out, 'YT_KAPAK.csv', ['zaman', 'video_id', 'cift', 'scheduler_durum', 'videoThumbnailUrl_var',
                                  'bizim_kapak_parlaklik', 'video_0sn_parlaklik', 'ytimg', 'url', 'http', 'boyut',
                                  'parlaklik', 'fark_bizim_kapak', 'fark_0sn', 'fark_8sn', 'sinif'], kap)
    for r in kap:
        print('KAPAK', r[0], r[1], r[2], r[7], 'parl', r[11], 'f_bizim', r[12], 'f_0sn', r[13], 'f_8sn', r[14], '->', r[15])
    kay += [['YT_KAPAK.csv', 'parlaklik / fark_*', 'i.ytimg.com/vi/{id}/{oar2,hq720,hqdefault}.jpg',
             'sosyal_kapak_oku.g (gri 90x160, yatayda orta 9:16 bant) + fark (ortalama mutlak fark)', 'esik: benzer < 12'],
            ['YT_KAPAK.csv', 'sinif', 'sosyal_kapak_oku.sinifla', 'siyah = parlaklik < 3 ya da en yakin 0 sn karesi',
             'en yakin referans < 12 kazanir'],
            ['YT_KAPAK.csv', 'bizim_kapak_parlaklik', '/v2/scheduler/posts', 'videoThumbnailUrl indirildi', ''],
            ['YT_KAPAK.csv', 'video_0sn_parlaklik', '/v2/scheduler/posts', 'media[0] indirildi, ffmpeg 0 sn', '']]
    yaz_csv(out, 'YT_METRIK_KAYNAK.csv', ['dosya', 'sutun', 'uc', 'metrik_alan', 'not'], kay)
    tv = Counter()
    for r in satir:
        for i, (_, a) in enumerate(VID_K[:7]):
            if isinstance(r[4 + i], (int, float)):
                tv[a] += r[4 + i]
    print(f'VIDEO TOPLAM ({len(satir)} video, {PLAN_BAS}+): {dict(tv)}')
    print(f'KAPAK SINIF (oar2): {dict(Counter(r[15] for r in kap if r[7] == "oar2"))}')


if __name__ == '__main__':
    main()
