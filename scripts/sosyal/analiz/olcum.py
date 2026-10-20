#!/usr/bin/env python3
"""Sosyal once/sonra olcumu (baslangic kaydi 20 Eki 2026; 27 Eki ve 3 Kas ayni betikle). SALT OKUMA: yalniz GET.
Tek komut:  olcum.py TOKEN.json CIKTI_DIR --tarih 2026-10-20 [--degisim 2026-10-21T00:00]
Donem (Europe/Istanbul gunleri, --tarih HARIC; o gun bitmemis): 14 gun = tarih-14 .. tarih-1, 7 gun = tarih-7 .. tarih-1.
1) Hesap gunluk: GET /v2/analytics/timelines (network, metric, subject/scope, from/to, timezone=Europe/Istanbul).
   Her metrik icin VARYANT listesi sirayla denenir (19-20 Eki kosularinda olculen subject/scope kurallari); veri veren ilk
   varyant kullanilir ve TANIMLAR.txt'ye yazilir. Pinterest ayrica eski uc /stats/timeline/PIEV01|05|06|07 (ham + gunluk).
2) Gonderi: GET /v2/analytics/{posts|reels}/{ag} (from = tarih-14, to = tarih 23:59:59): yayin zamani (UTC + Istanbul),
   gorunum etiketi: yayin >= --degisim (Istanbul) -> "yeni", oncesi -> "eski".
Cikti: <AG>_GUNLUK.csv, <AG>_GONDERI.csv, OZET.txt (7/14 gun toplamlari), TANIMLAR.txt, HAM/*.json.
Metricool bir degeri vermiyorsa "erisilemedi"; tahmin yok."""
import argparse
import csv
import importlib.util
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = ZoneInfo(TZ)
TL = '/v2/analytics/timelines'
YOK = 'erisilemedi'
A, P_, N = {'subject': 'account'}, {'subject': 'posts'}, {}
# metrik tanimlari: (sutun, metric, [varyantlar], tur) ; tur: toplam (gunluk akis) | son (birikimli seviye, toplanmaz)
HESAP = {
    'pinterest': [('gosterim', 'impression', [A, N], 'toplam'), ('pin_tiklama', 'pin_click', [A, N], 'toplam'),
                  ('kaydetme', 'save', [A, N], 'toplam'), ('dis_tiklama', 'outbound_click', [A, N], 'toplam'),
                  ('takipci', 'followers', [A], 'son')],
    'instagram': [('erisim', 'reach', [A], 'toplam'), ('goruntulenme', 'views', [A], 'toplam'),
                  ('gosterim', 'impressions', [A], 'toplam'), ('profil_ziyaret', 'profile_views', [A], 'toplam'),
                  ('web_tiklama', 'website_clicks', [A], 'toplam'), ('profil_link_tiklama', 'profile_links_taps', [A], 'toplam'),
                  ('takipci', 'followers', [A], 'son'), ('takipci_degisim', 'delta_followers', [A], 'toplam'),
                  ('gonderi_erisim', 'reach', [P_], 'toplam'), ('reel_izlenme', 'videoviews', [{'subject': 'reels'}], 'toplam'),
                  ('reel_erisim', 'reach', [{'subject': 'reels'}], 'toplam')],
    'facebook': [('sayfa_gosterim', 'pageImpressions', [A, N], 'toplam'), ('sayfa_medya_izlenme', 'page_media_view', [A, N], 'toplam'),
                 ('sayfa_ziyaret', 'pageViews', [A, N], 'toplam'),
                 ('web_tiklama', 'page_website_clicks_logged_in_unique', [A, N], 'toplam'), ('cta_tiklama', 'ctaClicks', [A, N], 'toplam'),
                 ('takipci', 'pageFollows', [A, N], 'son'), ('yeni_takip', 'page_daily_follows_unique', [A, N], 'toplam'),
                 ('gonderi_gosterim', 'impressions', [P_], 'toplam'), ('gonderi_erisim', 'impressionsunique', [P_], 'toplam'),
                 ('reel_izlenme_tekil', 'post_total_media_view_unique', [{'subject': 'reels'}], 'toplam'),
                 ('reel_ort_izleme', 'post_video_avg_time_watched', [{'subject': 'reels'}], 'son'),
                 ('reel_toplam_izleme', 'post_video_view_time', [{'subject': 'reels'}], 'toplam')],
    'tiktok': [('video_goruntulenme', 'video_views', [A, N], 'toplam'), ('profil_ziyaret', 'profile_views', [A, N], 'toplam'),
               ('takipci', 'followers_count', [A, N], 'son'), ('takipci_degisim', 'followers_delta_count', [A, N], 'toplam'),
               ('begeni', 'likes', [A, N], 'toplam'), ('yorum', 'comments', [A, N], 'toplam'), ('paylasim', 'shares', [A, N], 'toplam')],
    'youtube': [('izlenme', 'views', [{'scope': 'viewed'}, N], 'toplam'), ('etkilesim', 'interactions', [{'scope': 'viewed'}, N], 'toplam'),
                ('begeni', 'likes', [{'scope': 'viewed'}, N], 'toplam'), ('yorum', 'comments', [{'scope': 'viewed'}, N], 'toplam'),
                ('paylasim', 'shares', [{'scope': 'viewed'}, N], 'toplam'),
                ('izleme_dk', 'watchMinutes', [{'scope': 'viewed'}, N], 'toplam'),
                ('abone', 'subscribers', [{'scope': 'viewed'}, N], 'son')],
    'threads': [('goruntulenme', 'views', [A], 'toplam'), ('begeni', 'likes', [A], 'toplam'), ('yanit', 'replies', [A], 'toplam'),
                ('yeniden_paylasim', 'reposts', [A], 'toplam'), ('alinti', 'quotes', [A], 'toplam'),
                ('takipci', 'followers_count', [A], 'son'), ('takipci_degisim', 'delta_followers', [A], 'toplam')],
}
# gonderi uclari: (uc, tur, {sutun: [alan adaylari]})
ZAMAN = ['publishedAt', 'publishedDate', 'createdAt', 'createTime', 'created', 'timestamp', 'createdTime', 'date']
GON = {
    'pinterest': [('/v2/analytics/posts/pinterest', 'pin', {'gosterim': ['impressions'], 'pin_tiklama': ['pinClicks'],
                   'kaydetme': ['saves'], 'dis_tiklama': ['outboundClicks'], 'video_izlenme': ['videoViews', 'videoMrcViews'],
                   'ort_izleme_sn': ['videoAvgWatchTime'], 'kimlik': ['id', 'pinId'], 'baslik': ['title'], 'link': ['url', 'link']})],
    'instagram': [('/v2/analytics/posts/instagram', 'gonderi', {'erisim': ['reach'], 'goruntulenme': ['views'],
                   'gosterim': ['impressionsTotal', 'impressions'], 'begeni': ['likes'], 'yorum': ['comments'], 'kaydetme': ['saved'],
                   'paylasim': ['shares'], 'kimlik': ['postId', 'id'], 'link': ['url'], 'baslik': ['content']}),
                  ('/v2/analytics/reels/instagram', 'reel', {'erisim': ['reach'], 'goruntulenme': ['views'], 'izlenme': ['videoViews'],
                   'gosterim': ['impressionsTotal', 'impressions'], 'ort_izleme_sn': ['averageWatchTime'],
                   'toplam_izleme': ['videoViewTotalTime'], 'begeni': ['likes'], 'yorum': ['comments'], 'kaydetme': ['saved'],
                   'paylasim': ['shares'], 'kimlik': ['reelId', 'id'], 'link': ['url'], 'baslik': ['content']})],
    'facebook': [('/v2/analytics/posts/facebook', 'gonderi', {'erisim': ['impressionsUnique'], 'gosterim': ['impressions'],
                  'tepki': ['reactions'], 'yorum': ['comments'], 'paylasim': ['shares'], 'tiklama': ['clicks'],
                  'link_tiklama': ['linkclicks'], 'izlenme': ['videoViews'], 'kimlik': ['postId', 'id'], 'link': ['url', 'link'],
                  'baslik': ['text', 'message']}),
                 ('/v2/analytics/reels/facebook', 'reel', {'erisim': ['postImpressionsUnique'], 'izlenme': ['blueReelsPlayCount'],
                  'ort_izleme_sn': ['postVideoAvgTimeWatchedSeconds'], 'toplam_izleme_sn': ['postVideoViewTimeSeconds'],
                  'tepki': ['postVideoReactions'], 'kimlik': ['reelId', 'id'], 'link': ['url', 'link'], 'baslik': ['description', 'title']})],
    'tiktok': [('/v2/analytics/posts/tiktok', 'video', {'izlenme': ['viewCount'], 'erisim': ['reach'], 'begeni': ['likeCount'],
                'yorum': ['commentCount'], 'paylasim': ['shareCount'], 'ort_izleme_sn': ['averageTimeWatched'],
                'tam_izlenme_orani': ['fullVideoWatchedRate'], 'toplam_izleme_sn': ['totalTimeWatched'], 'kimlik': ['videoId', 'id'],
                'link': ['shareUrl', 'url'], 'baslik': ['videoDescription', 'title']})],
    'youtube': [('/v2/analytics/posts/youtube', 'video', {'izlenme': ['views'], 'etkin_izlenme': ['engagedViews'],
                 'izleme_dk': ['watchMinutes'], 'ort_izleme_sn': ['averageViewDuration'], 'begeni': ['likes'], 'yorum': ['comments'],
                 'paylasim': ['shares'], 'kimlik': ['videoId', 'id'], 'link': ['watchUrl'], 'baslik': ['title']})],
    'threads': [('/v2/analytics/posts/threads', 'gonderi', {'goruntulenme': ['views'], 'begeni': ['likes'], 'yanit': ['replies'],
                 'yeniden_paylasim': ['reposts'], 'alinti': ['quotes'], 'paylasim': ['shares'], 'kimlik': ['id', 'shortCode'],
                 'link': ['permalink'], 'baslik': ['text']})],
}
GORUNUM_NOT = {'threads': 'Threads karuselleri degismedi (20 Eki karari); etiket yalniz tarih',
               'pinterest': 'pin degisimi 20 Eki (PINTEREST_PIN_DEGISIM_20261020)',
               'instagram': 'Reels P acilisi 20 Eki (reels-p-degistir)', 'facebook': 'Reels P acilisi 20 Eki (reels-p-degistir)',
               'tiktok': 'video P acilisi 20 Eki (UYGULAMA_TT_YT)', 'youtube': 'video P acilisi + kapak 20 Eki (UYGULAMA_TT_YT)'}
OZET, TANIM = [], []


def log(s):
    print(s, flush=True); OZET.append(s)


def sayi(v):
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return YOK
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return YOK
    return int(v) if float(v).is_integer() else round(float(v), 4)


def ham(out, ad, j):
    os.makedirs(os.path.join(out, 'HAM'), exist_ok=True)
    json.dump(j, open(os.path.join(out, 'HAM', f'{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def get(mc, out, ad, yol, p):
    try:
        j = mc.istek('GET', yol, p)
    except SystemExit as e:
        j = {'_hata': str(e)[:400]}
    ham(out, ad, j)
    return j


def liste(j):
    v = mpb.veri(j) if isinstance(j, (dict, list)) and not (isinstance(j, dict) and '_hata' in j) else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), None)
    return v if isinstance(v, list) else None


def seri(j):
    """timelines: data[{metric, values[{dateTime, value}]}] -> {date: float}; gun = dateTime'in ilk 10 karakteri (yerel gun)."""
    out = {}
    for b in liste(j) or []:
        for x in (b.get('values') or []) if isinstance(b, dict) else []:
            t, v = x.get('dateTime'), x.get('value')
            if isinstance(t, str) and re.match(r'\d{4}-\d{2}-\d{2}', t) and isinstance(v, (int, float)):
                d = date.fromisoformat(t[:10]); out[d] = out.get(d, 0) + float(v)
    return out


def zaman(x):
    """Yayin zamani -> (utc, istanbul, ham). dict{dateTime,timezone} | ISO (ofsetli/ofsetsiz) | epoch. Ofsetsiz + tz yok: Istanbul."""
    for k in ZAMAN:
        v = x.get(k)
        if v in (None, ''):
            continue
        try:
            if isinstance(v, dict):
                d = datetime.fromisoformat(str(v.get('dateTime'))[:19]).replace(tzinfo=ZoneInfo(v.get('timezone') or TZ))
            elif isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
                n = float(v); d = datetime.fromtimestamp(n / 1000 if n > 1e11 else n, timezone.utc)
            else:
                d = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
                d = d if d.tzinfo else d.replace(tzinfo=IST)
            return d.astimezone(timezone.utc), d.astimezone(IST), f'{k}={json.dumps(v, default=str)}'
        except (ValueError, TypeError):
            continue
    return None, None, ''


def alan(x, adaylar):
    for a in adaylar:
        if a in x and x[a] not in (None, ''):
            return a, x[a]
    return '', None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    ap.add_argument('--tarih', required=True, help='olcum gunu YYYY-MM-DD (Istanbul); veri tarih-1 gunune kadar')
    ap.add_argument('--degisim', default='2026-10-21T00:00', help='yeni gorunum esigi (Istanbul): yayin >= bu an -> yeni')
    ap.add_argument('--aglar', default=','.join(HESAP))
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    T = date.fromisoformat(a.tarih)
    g14 = [T - timedelta(days=i) for i in range(14, 0, -1)]
    g7 = g14[-7:]
    deg = datetime.fromisoformat(a.degisim).replace(tzinfo=IST)
    okuma = datetime.now(timezone.utc)
    log(f'OKUMA: {okuma:%Y-%m-%dT%H:%M:%SZ} UTC = {okuma.astimezone(IST):%Y-%m-%d %H:%M} Istanbul; blogId {mc.b}; --tarih {T}')
    log(f'14 gun: {g14[0]} .. {g14[-1]}; 7 gun: {g7[0]} .. {g7[-1]} (Europe/Istanbul gunleri; {T} haric)')
    log(f'Gorunum esigi: yayin >= {deg:%Y-%m-%d %H:%M} Istanbul = {deg.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC -> yeni')
    TANIM.extend([
        'OLCUM TANIMLARI (scripts/sosyal/analiz/olcum.py; salt okuma, yalniz GET; blogId ' + str(mc.b) + ')',
        f'Olcum gunu --tarih {T}; okuma {okuma:%Y-%m-%dT%H:%M:%SZ} UTC ({okuma.astimezone(IST):%Y-%m-%d %H:%M} Istanbul).',
        f'Gunler Europe/Istanbul (UTC+3). 14 gun {g14[0]}..{g14[-1]}, 7 gun {g7[0]}..{g7[-1]}; olcum gunu dahil degil (tamamlanmamis).',
        'Timelines istegi: from=<ilk gun>T00:00:00, to=<son gun>T23:59:59, timezone=Europe/Istanbul. Yanittaki dateTime ofseti',
        '  Metricool tarafindan +0200 (Europe/Madrid) yazilabiliyor (19 Eki Pinterest yaniti "T12:00:00+0200"); gun = ilk 10 karakter.',
        'Toplam: "toplam" turu metrikler gunluk degerlerin toplami; "son" turu (takipci, ortalama sure) son gunun degeri.',
        f'Gonderi gorunumu: yayin >= {deg:%Y-%m-%d %H:%M} Istanbul ({deg.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC) -> "yeni", oncesi "eski".',
        '  20 Eki degisimleri gun icinde uygulandi; 20 Eki yayinlari "eski" sayilir (degistirilecekse --degisim).',
        'Gonderi listesi: from=<tarih-14>T00:00:00, to=<tarih>T23:59:59, timezone=Europe/Istanbul; yayin zamani hem UTC hem Istanbul.',
        '  Ofsetsiz zaman ve timezone alani yoksa Europe/Istanbul varsayildi (istekteki timezone).',
        'Gonderi degerleri okuma anindaki KUMULATIF degerlerdir (yayindan okumaya kadar); farkli yastaki gonderiler dogrudan',
        '  karsilastirilamaz: yas_saat sutunu (yayin -> okuma) yazilir.',
        '"erisilemedi": Metricool vermedi (HTTP hata, bos yanit ya da alan yok). Tahmin yok.', ''])

    for ag in [x for x in a.aglar.split(',') if x in HESAP]:
        log(f'--- {ag.upper()}')
        TANIM.append(f'[{ag.upper()}] gunluk: {TL} network={ag}')
        kol, S = [], {}
        for sut, m, varyant, tur in HESAP[ag]:
            secilen, durum = None, []
            for v in varyant:
                p = dict(network=ag, metric=m, **{'from': f'{g14[0]}T00:00:00', 'to': f'{g14[-1]}T23:59:59', 'timezone': TZ}, **v)
                vad = '_'.join(f'{k}-{x}' for k, x in v.items()) or 'yok'
                j = get(mc, out, f'{ag}_timeline_{m}_{vad}', TL, p)
                s = seri(j)
                durum.append(f'{vad}: ' + ('HTTP ' + str(j.get('_hata', ''))[:90] if isinstance(j, dict) and '_hata' in j
                                            else ('veri var' if s else 'bos')))
                if s:
                    secilen = (v, s); break
            S[sut] = (secilen[1] if secilen else {}, tur); kol.append(sut)
            TANIM.append(f'  {sut:22s} metric={m} ' + (('; '.join(f'{k}={x}' for k, x in secilen[0].items()) or 'subject/scope yok')
                                                       if secilen else 'ERISILEMEDI') + f'  [{tur}]  denemeler: {" | ".join(durum)}')
        if ag == 'pinterest':
            for kod in ('PIEV01', 'PIEV05', 'PIEV06', 'PIEV07'):
                j = get(mc, out, f'pinterest_stats_timeline_{kod}', f'/stats/timeline/{kod}',
                        {'start': f'{g14[0]:%Y%m%d}', 'end': f'{g14[-1]:%Y%m%d}', 'timezone': TZ})
                s = {}
                for x in j if isinstance(j, list) else []:
                    if isinstance(x, list) and len(x) >= 2 and re.fullmatch(r'\d{8}', str(x[0])):
                        try:
                            d = datetime.strptime(str(x[0]), '%Y%m%d').date(); s[d] = s.get(d, 0) + float(x[1])
                        except ValueError:
                            pass
                S[kod] = (s, 'toplam'); kol.append(kod)
                TANIM.append(f'  {kod:22s} eski uc /stats/timeline/{kod} start/end YYYYMMDD (yanit [["YYYYMMDD","deger"],...]); '
                             f'{len(s)} gun; anlam Metricool belgesinde yok (ham HAM/pinterest_stats_timeline_{kod}.json)')
        with open(os.path.join(out, f'{ag.upper()}_GUNLUK.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(['tarih_istanbul', 'donem'] + kol)
            for d in g14:
                w.writerow([str(d), '7+14' if d in g7 else '14'] + [sayi(S[c][0].get(d)) if d in S[c][0] else YOK for c in kol])
            for ad_, gl in (('TOPLAM_7', g7), ('TOPLAM_14', g14)):
                r = [ad_, '']
                for c in kol:
                    s, tur = S[c]
                    v = [s[d] for d in gl if d in s]
                    r.append(YOK if not v else (sayi(s[max(d for d in gl if d in s)]) if tur == 'son' else sayi(sum(v))))
                w.writerow(r)
        for c in kol:
            s, tur = S[c]
            v7, v14 = [s[d] for d in g7 if d in s], [s[d] for d in g14 if d in s]
            f_ = (lambda v, gl: YOK if not v else (sayi(s[max(d for d in gl if d in s)]) if tur == 'son' else sayi(sum(v))))
            log(f'  {c}: 7 gun {f_(v7, g7)} ({len(v7)} gun veri), 14 gun {f_(v14, g14)} ({len(v14)} gun veri) [{tur}]')

        # gonderiler
        satir, kolg = [], []
        for uc, tur_, alanlar in GON.get(ag, []):
            kolg += [k for k in alanlar if k not in kolg]
        TANIM.append(f'[{ag.upper()}] gonderi: ' + '; '.join(f'{uc} ({t})' for uc, t, _ in GON.get(ag, [])) + f'; not: {GORUNUM_NOT[ag]}')
        for uc, tur_, alanlar in GON.get(ag, []):
            j = get(mc, out, f'{ag}_{uc.strip("/").replace("/", "_")}', uc,
                    {'from': f'{T - timedelta(days=14)}T00:00:00', 'to': f'{T}T23:59:59', 'timezone': TZ})
            ls = liste(j)
            if ls is None:
                log(f'  {uc}: {"HTTP " + str(j.get("_hata"))[:150] if isinstance(j, dict) and "_hata" in j else "yanit liste degil"}')
                TANIM.append(f'  {uc}: ERISILEMEDI'); continue
            kullanilan = {}
            for x in ls:
                if not isinstance(x, dict):
                    continue
                u, i, zh = zaman(x)
                if u is None or not (T - timedelta(days=14) <= i.date() <= T):
                    continue
                r = {'tur': tur_, 'yayin_utc': f'{u:%Y-%m-%d %H:%M}', 'yayin_istanbul': f'{i:%Y-%m-%d %H:%M}',
                     'gorunum': 'yeni' if i >= deg else 'eski', 'yas_saat': round((okuma - u).total_seconds() / 3600, 1),
                     'zaman_ham': zh, 'uc': uc}
                for k, ad_ in alanlar.items():
                    an, v = alan(x, ad_)
                    kullanilan.setdefault(k, set()).add(an or '-')
                    r[k] = (re.sub(r'\s+', ' ', str(v))[:80] if k in ('baslik', 'link', 'kimlik') else sayi(v)) if an else YOK
                satir.append(r)
            log(f'  {uc}: {len(ls)} kayit, donemde {sum(1 for r in satir if r["uc"] == uc)}; alanlar {sorted(ls[0])[:40] if ls else "-"}')
            for k, ad_ in alanlar.items():
                TANIM.append(f'  {uc} {k:18s} <- {"|".join(sorted(kullanilan.get(k, {"-"})))} (adaylar {"/".join(ad_)})')
        satir.sort(key=lambda r: r['yayin_utc'])
        bas = ['yayin_istanbul', 'yayin_utc', 'gorunum', 'tur', 'yas_saat'] + kolg + ['zaman_ham', 'uc']
        with open(os.path.join(out, f'{ag.upper()}_GONDERI.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(bas)
            for r in satir:
                w.writerow([r.get(k, YOK) for k in bas])
        for gr in ('eski', 'yeni'):
            R = [r for r in satir if r['gorunum'] == gr]
            ozet = []
            for k in kolg:
                if k in ('baslik', 'link', 'kimlik'):
                    continue
                v = [r[k] for r in R if isinstance(r.get(k), (int, float))]
                if v:
                    ozet.append(f'{k} toplam {sayi(sum(v))} ort {sayi(sum(v) / len(v))}')
            log(f'  gonderi {gr}: {len(R)}' + (f'; {"; ".join(ozet)}' if ozet else ''))
        TANIM.append('')

    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(OZET) + '\n')
    open(os.path.join(out, 'TANIMLAR.txt'), 'w').write('\n'.join(TANIM) + '\n')


if __name__ == '__main__':
    main()
