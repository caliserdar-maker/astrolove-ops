#!/usr/bin/env python3
"""TikTok anlik durum tespiti (19 Eki 2026). SALT OKUMA: Metricool'a ve TikTok'a YAZMA YOK, yalniz GET.
Uclar ve metrik adlari (data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json):
  /v2/analytics/timelines network=tiktok   "For TikTok Account": video_views, profile_views, followers_count,
                                           followers_delta_count, likes, comments, shares (subject=account, bos ise subjectsiz)
  /v2/analytics/posts/tiktok               TikTokPost: createTime, videoId, viewCount, reach, likeCount, commentCount,
                                           shareCount, averageTimeWatched, fullVideoWatchedRate, totalTimeWatched,
                                           impressionSources{forYou, follow, hashtag, sound, personalProfile, search}
  /v2/scheduler/posts                      plan / yayin / hata (13 Eki - bugun), providers[network=tiktok].status/detail
Kayit (save/favorite) TikTokPost semasinda yok; yanitta belgelenmemis bir kayit alani varsa o kullanilir ve adi yazilir.
Cift videoDescription / scheduler metninden ("X and Y"). Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok.
Ham yanitlar HAM_*.json. Kullanim: tiktok.py TOKEN.json CIKTI_DIR"""
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
METRIK = [('followers_count', 'takipci'), ('followers_delta_count', 'takipci_degisim'), ('video_views', 'video_goruntulenme'),
          ('profile_views', 'profil_goruntulenme'), ('likes', 'begeni'), ('comments', 'yorum'), ('shares', 'paylasim')]
VID_K = [('viewCount', 'goruntulenme'), ('reach', 'erisim'), ('likeCount', 'begeni'), ('commentCount', 'yorum'),
         ('shareCount', 'paylasim'), (None, 'kayit'), ('averageTimeWatched', 'ort_izleme_sn'),
         ('fullVideoWatchedRate', 'tam_izlenme_orani'), ('totalTimeWatched', 'toplam_izleme_sn'), ('duration', 'sure_sn')]
KAYNAK = ['forYou', 'follow', 'hashtag', 'sound', 'personalProfile', 'search']
KAYIT_ADAY = ('favorites', 'favoriteCount', 'favouriteCount', 'collectCount', 'saveCount', 'saves', 'saved', 'bookmarks')
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


def cift(metin):
    m = re.search(r'\b([A-Z][a-z]+) and ([A-Z][a-z]+)\b', metin or '')
    return '_'.join(sorted((m.group(1).upper(), m.group(2).upper()))) if m else ''


def video_id(url):
    m = re.search(r'/video/(\d+)', url or '')
    return m.group(1) if m else ''


def yerel(t):
    """createTime -> Istanbul yerel 'YYYY-MM-DD HH:MM' (yanit ofsetsizse oldugu gibi)."""
    if not isinstance(t, str) or not t:
        return str(t or '')
    try:
        d = datetime.fromisoformat(t.replace('Z', '+00:00'))
    except ValueError:
        return t
    if d.tzinfo is None:
        return d.strftime('%Y-%m-%d %H:%M')
    from zoneinfo import ZoneInfo
    return d.astimezone(ZoneInfo(TZ)).strftime('%Y-%m-%d %H:%M')


def main():
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    gunler = [BAS + timedelta(days=i) for i in range((BUGUN - BAS).days + 1)]
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'OKUMA ANI (UTC): {okuma}')
    kay = []   # sutun -> kaynak eslemesi

    # 1) hesap geneli gunluk
    S, SUBJ = {}, {}
    for m, ad in METRIK:
        S[ad] = None
        for etiket, ek in (('account', {'subject': 'account'}), ('nosubj', {})):
            j = guvenli(mc, f'timeline_{m}_{etiket}', '/v2/analytics/timelines', dict({'network': 'tiktok', 'metric': m,
                        'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, **ek), out)
            g = seri(j) if j is not None else None
            if g:
                S[ad], SUBJ[ad] = g, etiket; break
            if g is not None and S[ad] is None:
                S[ad], SUBJ[ad] = g, etiket
        g = S[ad]
        print(f'TIMELINE {m} ({SUBJ.get(ad, "-")}): ' + ('yanit yok' if g is None else
              f'{len(g)} gun, toplam {sayi(sum(g.values()))}, ilk {min(g) if g else "-"}, son {max(g) if g else "-"}'))
        kay.append(['TT_HESAP_GUNLUK.csv', ad, '/v2/analytics/timelines', f'network=tiktok metric={m} '
                    f'{"subject=account" if SUBJ.get(ad) == "account" else "subject yok"}', 'gunluk deger (dateTime ilk 10 karakter)'])
    kol = [ad for _, ad in METRIK]
    yaz_csv(out, 'TT_HESAP_GUNLUK.csv', ['tarih'] + kol + ['kaynak'],
            [[str(d)] + [sayi(S[a].get(d)) if S[a] and d in S[a] else YOK for a in kol]
             + [f'/v2/analytics/timelines network=tiktok; okuma {okuma}'] for d in gunler])
    top = [a for a in kol if a != 'takipci']
    yaz_csv(out, 'TT_HESAP_TOPLAM.csv', ['donem'] + top + ['takipci_ilk', 'takipci_son', 'kaynak'],
            [[f'{BAS} - {BUGUN}'] + [sayi(sum(S[a].values())) if S[a] else YOK for a in top]
             + ([sayi(S['takipci'][min(S['takipci'])]), sayi(S['takipci'][max(S['takipci'])])] if S['takipci'] else [YOK, YOK])
             + [f'/v2/analytics/timelines; okuma {okuma}']])

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
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'tiktok'), None)
        if not pr:
            continue
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        sch.append((zt, p, pr))
        if video_id(pr.get('publicUrl')):
            vid_sch[video_id(pr['publicUrl'])] = (zt, pr.get('status'))
    print(f'SCHEDULER TikTok gonderi ({PLAN_BAS} - {BUGUN + timedelta(days=1)}): {len(sch)}; '
          f'durumlar {dict(Counter(x[2].get("status") for x in sch))}')
    if sch:
        print(f'SCHEDULER ornek alanlar: {sorted(sch[0][1])[:40]} | provider {sorted(sch[0][2])}')
    gun_dur, detay = defaultdict(Counter), []
    for zt, p, pr in sorted(sch, key=lambda x: x[0]):
        if not zt or not (PLAN_BAS <= date.fromisoformat(zt[:10]) <= BUGUN):
            continue
        st = pr.get('status') or ''
        gun_dur[zt[:10]][st] += 1
        h = pr.get('detail') or pr.get('error') or ''
        td = p.get('tiktokData') or {}
        detay.append([zt, st, cift(p.get('text')), pr.get('publicUrl') or '', td.get('isAigc', ''),
                      bool(p.get('videoThumbnailUrl')), (h if isinstance(h, str) else json.dumps(h, ensure_ascii=False))[:300]])
    durumlar = sorted({s for c in gun_dur.values() for s in c})
    yaz_csv(out, 'TT_PLAN_GUNLUK.csv', ['tarih', 'planlanan_toplam'] + [f'durum_{s or "BOS"}' for s in durumlar] + ['kaynak'],
            [[g, sum(c.values())] + [c.get(s, 0) for s in durumlar] + [f'/v2/scheduler/posts; okuma {okuma}']
             for g, c in sorted(gun_dur.items())])
    yaz_csv(out, 'TT_PLAN_DETAY.csv', ['yayin_zamani', 'durum', 'cift', 'tiktok_link', 'tiktokData.isAigc',
                                       'videoThumbnailUrl_var', 'hata_ayrinti'], detay)
    tp = Counter(); [tp.update(c) for c in gun_dur.values()]
    print(f'PLAN {PLAN_BAS} - {BUGUN}: planlanan {sum(tp.values())}; {dict(tp)}')
    for r in detay:
        print('PLAN', r[0], r[1], r[2], r[3], r[6][:120])
    kay += [['TT_PLAN_*.csv', 'durum', '/v2/scheduler/posts', 'providers[network=tiktok].status', ''],
            ['TT_PLAN_DETAY.csv', 'hata_ayrinti', '/v2/scheduler/posts', 'providers[network=tiktok].detail', ''],
            ['TT_PLAN_DETAY.csv', 'yayin_zamani', '/v2/scheduler/posts', 'publicationDate.dateTime', TZ]]

    # 2) video bazinda
    vj = guvenli(mc, 'posts_tiktok', '/v2/analytics/posts/tiktok',
                 {'from': f'{BAS}T00:00:00', 'to': f'{BUGUN}T23:59:59', 'timezone': TZ}, out)
    vids = liste(vj)
    alanlar = sorted({k for v in vids or [] for k in v}) if vids else []
    print(f'POSTS/TIKTOK: {len(vids) if vids is not None else "yanit yok"} video; alanlar {alanlar}')
    kayit_k = next((k for k in KAYIT_ADAY if k in alanlar), None)
    print(f'KAYIT alani: {kayit_k or "yok (" + YOK + ")"}')
    satir = []
    for v in vids or []:
        zt = yerel(v.get('createTime'))
        if zt[:10] and zt[:10] < str(PLAN_BAS):
            continue
        deg = [v.get(k if k else kayit_k) if (k or kayit_k) and isinstance(v.get(k if k else kayit_k), (int, float)) else None
               for k, _ in VID_K]
        isrc = v.get('impressionSources') if isinstance(v.get('impressionSources'), dict) else {}
        vid = str(v.get('videoId') or '')
        s = vid_sch.get(vid, ('', ''))
        satir.append([zt, vid, cift(v.get('videoDescription') or v.get('title'))] + [sayi(x) for x in deg]
                     + [sayi(isrc[k]) if isinstance(isrc.get(k), (int, float)) else YOK for k in KAYNAK]
                     + [s[0], s[1], v.get('shareUrl') or ''])
    satir.sort(key=lambda x: x[0])
    yaz_csv(out, 'TT_VIDEO.csv', ['yayin_zamani_istanbul', 'video_id', 'cift'] + [a for _, a in VID_K]
            + [f'kaynak_{k}' for k in KAYNAK] + ['scheduler_zamani', 'scheduler_durum', 'link'], satir)
    for r in satir:
        print('VIDEO', r[:13], 'kaynak', r[13:19])
    for k, a in VID_K:
        kay.append(['TT_VIDEO.csv', a, '/v2/analytics/posts/tiktok',
                    (k or kayit_k or 'TikTokPost semasinda yok'), 'birim/olcek Metricool yanitindaki gibi'])
    kay += [['TT_VIDEO.csv', f'kaynak_{k}', '/v2/analytics/posts/tiktok', f'impressionSources.{k}', 'Metricool yanitindaki gibi']
            for k in KAYNAK]
    kay.append(['TT_VIDEO.csv', 'yayin_zamani_istanbul', '/v2/analytics/posts/tiktok', 'createTime', f'{TZ} cevrildi'])
    yaz_csv(out, 'TT_METRIK_KAYNAK.csv', ['dosya', 'sutun', 'uc', 'metrik_alan', 'not'], kay)
    if satir:
        tv = Counter()
        for r in satir:
            for i, (_, a) in enumerate(VID_K):
                if isinstance(r[3 + i], (int, float)) and a in ('goruntulenme', 'erisim', 'begeni', 'yorum', 'paylasim', 'kayit'):
                    tv[a] += r[3 + i]
        print(f'VIDEO TOPLAM ({len(satir)} video, {PLAN_BAS}+): {dict(tv)}')


if __name__ == '__main__':
    main()
