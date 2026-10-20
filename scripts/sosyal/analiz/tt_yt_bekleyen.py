#!/usr/bin/env python3
"""Bekleyen TikTok + YouTube Shorts video gonderileri envanteri (20 Eki 2026, yeni acilis karari). SALT OKUMA: Metricool'a
YAZMA YOK, yalniz GET. Yontem ig_bekleyen.py ile ayni (kapak_basa.py okumasi, ayni esikler).
1. /v2/scheduler/posts (simdi -> 31 Oca 2027, 3 gunluk parcalar): providers[tiktok|youtube].status == PENDING, yayin > simdi.
   Satir = (gonderi, ag). Alanlar: tarih, ag, baslik (youtubeData.title) / metin basi, media[0], videoThumbnailUrl,
   videoCoverMilliseconds, youtubeData.type/privacy.
2. Cift: youtubeData.title / metin "X and|& Y" (alfabetik); yoksa medya dosya adindaki iki burc.
3. Acilis olcumu: ffmpeg/ffprobe dogrudan medya URL'sinden ilk 1.5 sn (indirme yok): ilk kare parlakligi, en dusuk
   parlaklik, kapak gorseli (videoThumbnailUrl) parlakligi. Siyah acilis = ilk kare < 3 ya da en dusuk < kapak/2
   (ig_bekleyen / kapak_basa kapisi). Ayni URL bir kez olculur.
   Yeni aday (Drive SOSYAL_VIDEO_P_78_20261020/<a>-and-<b>-astroloveart-reel.mp4) varsa ilk kare - aday ilk kare farki
   (kapak_basa ESIK 2.0).
   Karar: ilk kare aday ile ayni -> degismemeli; siyah acilis -> degismeli; diger -> belirsiz.
4. Aday listesi ADAY_DIR/VIDEO_P.txt (rclone lsf), dosyalar ADAY_DIR/video/ (rclone copy).
Kullanim: tt_yt_bekleyen.py TOKEN.json CIKTI_DIR ADAY_DIR"""
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(os.path.dirname(KOK))


def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


mpb = yukle('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
kb = yukle('kb', os.path.join(DEPO, 'sosyal', 'video_v9', 'kapak_basa.py'))

TZ = 'Europe/Istanbul'
SON = datetime(2027, 1, 31)
SIYAH_MUTLAK = 3.0
AGLAR = ('tiktok', 'youtube')
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
ADAY_YOL = 'gdrive:ASTROLOVE/TEMP/SOSYAL_VIDEO_P_78_20261020'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
OZET = None


def log(s):
    print(s, flush=True)
    with open(OZET, 'a', encoding='utf-8') as f:
        f.write(s + '\n')


def cift_ad(*metinler):
    b = '|'.join(BURC)
    for t in metinler:
        m = re.search(r'\b(' + b + r')\s*(?:&|and)\s*(' + b + r')\b', t or '', re.I)
        if m:
            return '_'.join(sorted((m.group(1).upper(), m.group(2).upper())))
    return ''


def dosya_cift(ad):
    z = [x.upper() for x in re.findall('|'.join(BURC), (ad or '').lower())]
    return '_'.join(sorted(z[:2])) if len(z) >= 2 else ''


def kisa(u):
    return (u or '').split('?')[0]


def thumb_parl(url, is_dir, W, H):
    y = os.path.join(is_dir, 't_' + hashlib.md5(kisa(url).encode()).hexdigest()[:12] + '.img')
    if not os.path.exists(y):
        r = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(r, timeout=120) as z, open(y, 'wb') as f:
            f.write(z.read())
    return float(kb.kapak_dizi(y, W, H).mean())


def ac_olc(kaynak):
    """ffprobe + ilk 1.5 sn kareleri (kaynak: URL ya da yerel yol)."""
    v = kb.probe(kaynak)
    W, H = v['w'], v['h']
    ilk = kb.kareler(kaynak, W, H, int(round(kb.KONTROL_SN * v['fps'])) + 1)
    return {'W': W, 'H': H, 'sure': round(v['toplam_sn'], 2), 'ilk': ilk[0], 'parl': [float(f.mean()) for f in ilk]}


def _dene(f, *a):
    try:
        return f(*a), ''
    except Exception as e:
        return None, f'{type(e).__name__}: {str(e)[:150]}'


def main():
    global OZET
    tok, out, aday_dir = sys.argv[1:4]
    is_dir = os.path.join(aday_dir, 'is'); os.makedirs(out, exist_ok=True); os.makedirs(is_dir, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = mpb.MC(json.load(open(tok)))
    simdi = datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)
    log(f'OKUMA ANI (Istanbul): {simdi:%Y-%m-%dT%H:%M:%S}; blogId {mc.b}; donem simdi - {SON:%Y-%m-%d}; uc GET /v2/scheduler/posts')

    ps, t = {}, simdi.replace(minute=0, second=0, microsecond=0)
    while t < SON:
        e = min(t + timedelta(days=3), SON)
        try:
            ls = mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}',
                                                                  'timezone': TZ}))
        except SystemExit as x:
            log(f'SCHEDULER {t:%Y-%m-%d}: HATA {str(x)[:200]}'); ls = None
        ls = ls if isinstance(ls, list) else []
        if len(ls) >= 100:
            log(f'SCHEDULER {t:%Y-%m-%d}: {len(ls)} kayit  UYARI: 100 ve ustu, yanit kesilmis olabilir')
        for p in ls:
            ps[str(p.get('id'))] = p
        t = e
    sat0, durum = [], Counter()
    for p in ps.values():
        pd = p.get('publicationDate') or {}
        zt = pd.get('dateTime') or ''
        try:
            z = datetime.fromisoformat(zt[:19]).replace(tzinfo=ZoneInfo(pd.get('timezone') or TZ)).astimezone(ZoneInfo(TZ)).replace(tzinfo=None)
        except ValueError:
            continue
        if z <= simdi:
            continue
        for pr in p.get('providers') or []:
            ag = (pr.get('network') or '').lower()
            if ag in AGLAR:
                durum[(ag, pr.get('status') or '')] += 1
                if (pr.get('status') or '') == 'PENDING':
                    sat0.append((z, ag, p, pr))
    sat0.sort(key=lambda x: (x[0], x[1]))
    log(f'SCHEDULER: {len(ps)} benzersiz gonderi; TikTok/YouTube (yayin > simdi) durum {dict(durum)}; bekleyen satir {len(sat0)}')
    json.dump([x[2] for x in sat0], open(os.path.join(out, 'HAM_tiktok_youtube_bekleyen.json'), 'w'), ensure_ascii=False, indent=1)
    if sat0:
        p0 = sat0[0][2]
        log(f'ORNEK alanlar: {sorted(p0)}; provider {sorted(sat0[0][3])}; youtubeData {sorted(p0.get("youtubeData") or {})}; '
            f'tiktokData {p0.get("tiktokData")}; ag/gonderi {dict(Counter(len(x[2].get("providers") or []) for x in sat0))}')

    # aday listesi
    lf = os.path.join(aday_dir, 'VIDEO_P.txt')
    al = [x.strip() for x in open(lf)] if os.path.exists(lf) else []
    aday = {dosya_cift(x): x for x in al if x.endswith('.mp4') and dosya_cift(x)}
    log(f'ADAY {ADAY_YOL}: {len(aday)} mp4' + ('' if al else ' (klasor bos / okunamadi; yalniz yol yazilir)'))

    # olcum: benzersiz medya URL + aday dosyalari (8 paralel)
    t0 = time.time()
    url_tam = {}
    for x in sat0:
        m = (x[2].get('media') or [''])[0]
        m = m if isinstance(m, str) else (m or {}).get('url', '')
        url_tam.setdefault(kisa(m), m)
    url = sorted(set(url_tam) - {''})
    with ThreadPoolExecutor(8) as ex:
        V = dict(zip(url, ex.map(lambda u: _dene(ac_olc, url_tam[u]), url)))
    gerekli = sorted({c for c in (cift_ad((x[2].get('youtubeData') or {}).get('title'), x[2].get('text')) for x in sat0) if c in aday})
    with ThreadPoolExecutor(8) as ex:
        A = dict(zip(gerekli, ex.map(lambda c: _dene(ac_olc, os.path.join(aday_dir, 'video', aday[c])), gerekli)))
    log(f'OLCUM: {len(url)} benzersiz video URL ({sum(1 for v in V.values() if v[1])} hata), {len(A)} aday '
        f'({sum(1 for v in A.values() if v[1])} hata), {time.time() - t0:.0f} sn')

    def m0(p):
        m = (p.get('media') or [''])[0]
        return kisa(m if isinstance(m, str) else (m or {}).get('url', ''))
    ayni = Counter(m0(x[2]) for x in sat0)
    satir = []
    for i, (z, ag, p, pr) in enumerate(sat0, 1):
        yd = p.get('youtubeData') or {}
        m = (p.get('media') or [''])[0]
        m = m if isinstance(m, str) else (m or {}).get('url', '')
        metin = p.get('text') or ''
        c = cift_ad(yd.get('title'), metin) or dosya_cift(os.path.basename(kisa(m)))
        q, hata = V.get(kisa(m), (None, 'medya yok'))
        ilk_p = min_p = th_p = fark_a = ''
        siyah = ''
        if q:
            ilk_p, min_p = round(q['parl'][0], 1), round(min(q['parl']), 1)
            esik_alt = None
            if p.get('videoThumbnailUrl'):
                tp, h2 = _dene(thumb_parl, p['videoThumbnailUrl'], is_dir, q['W'], q['H'])
                if tp is not None:
                    th_p, esik_alt = round(tp, 1), tp / 2
                else:
                    hata = (hata + '; ' if hata else '') + 'kapak ' + h2
            siyah = q['parl'][0] < SIYAH_MUTLAK or (esik_alt is not None and min(q['parl']) < esik_alt)
            aq = A.get(c, (None, ''))[0]
            if aq is not None:
                if (aq['W'], aq['H']) == (q['W'], q['H']):
                    fark_a = round(float(np.abs(q['ilk'] - aq['ilk']).mean()), 2)
                else:
                    hata = (hata + '; ' if hata else '') + f'aday boyutu {aq["W"]}x{aq["H"]} != {q["W"]}x{q["H"]}'
        if fark_a != '' and fark_a < kb.ESIK:
            karar, neden = 'degismemeli', f'ilk kare yeni aday ilk karesiyle ayni (fark {fark_a} < {kb.ESIK})'
        elif siyah is True:
            karar, neden = 'degismeli', 'siyah acilis' + ('' if c in aday else '; yeni video adayi henuz yok')
        elif q:
            karar, neden = 'belirsiz', 'siyah acilis yok; ' + ('ilk kare adaydan farkli' if fark_a != '' else 'karsilastirilacak aday yok')
        else:
            karar, neden = 'belirsiz', 'olcum yapilamadi'
        satir.append([z.strftime('%Y-%m-%d %H:%M'), ag, pr.get('status'), c, yd.get('title') or '', re.sub(r'\s+', ' ', metin)[:90],
                      kisa(m), p.get('videoThumbnailUrl') and kisa(p['videoThumbnailUrl']) or '', p.get('videoCoverMilliseconds', ''),
                      yd.get('type', ''), yd.get('privacy', ''), f'{q["W"]}x{q["H"]}' if q else '', q['sure'] if q else '',
                      ilk_p, min_p, th_p, '' if siyah == '' else ('evet' if siyah else 'hayir'), fark_a, karar, neden,
                      f'{ADAY_YOL}/{aday[c]}' if c in aday else f'{ADAY_YOL}/ (bu cift icin dosya yok)',
                      ayni[kisa(m)],
                      p.get('id'), p.get('uuid') or '', hata])
    bas = ['yayin_zamani_istanbul', 'ag', 'durum', 'cift', 'youtube_baslik', 'metin_basi', 'medya_url', 'kapak_gorseli_url',
           'videoCoverMilliseconds', 'youtubeData.type', 'youtubeData.privacy', 'boyut', 'sure_sn', 'ilk_kare_parlaklik',
           'min_parlaklik_0_1.5sn', 'kapak_gorseli_parlaklik', 'siyah_acilis', 'ilk_kare_aday_fark', 'karar', 'neden',
           'yeni_video_adayi', 'ayni_medya_satir_sayisi', 'metricool_id', 'uuid', 'olcum_hatasi']
    with open(os.path.join(out, 'ESLEME.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(bas); w.writerows(satir)
    log(f'CSV ESLEME.csv: {len(satir)} satir')
    if satir:
        log(f'ILK / SON: {satir[0][0]} / {satir[-1][0]}')
    for ag in AGLAR:
        R = [r for r in satir if r[1] == ag]
        if not R:
            continue
        ip = [r[13] for r in R if r[13] != '']
        log(f'{ag.upper()}: {len(R)} satir; karar {dict(Counter(r[18] for r in R))}; siyah acilis {dict(Counter(r[16] or "olculemedi" for r in R))}; '
            f'ilk kare parlaklik min/medyan/max {min(ip) if ip else "-"}/{sorted(ip)[len(ip) // 2] if ip else "-"}/{max(ip) if ip else "-"}; '
            f'kapak gorseli dolu {sum(1 for r in R if r[7])}; cift bos {sum(1 for r in R if not r[3])}; aday dosyasi {sum(1 for r in R if r[20].endswith(".mp4"))}; '
            f'olcum hatasi {sum(1 for r in R if r[24])}')
    log(f'Cift tekrari (ag basina): {[(a, c) for (a, c), k in Counter((r[1], r[3]) for r in satir).items() if k > 1][:20]}')
    log(f'Ayni medya URL paylasan satir dagilimi: {dict(Counter(r[21] for r in satir))}')
    for r in satir[:4] + [x for x in satir if x[24]][:5]:
        log('ORNEK ' + ' | '.join(str(x) for x in (r[0], r[1], r[3], r[11], r[13], r[14], r[15], r[16], r[17], r[18], r[24])))
    for x in YONTEM:
        log(x)


# Depodaki olculmus kayitlar: scripts/sosyal/metricool_video_degistir.py; Drive TEMP/SOSYAL_VIDEO_DEGISTIR_20261015/
# PISCES_SAGITTARIUS_yaz_1249/OZET.txt (15 Eki: IG/TikTok/YouTube PUT PASS); SOSYAL_ANALIZ_20261019/YOUTUBE/YT_KAPAK.csv.
YONTEM = [
    'YONTEM (uygulama ayri onayla; bu kosu hicbir sey yazmadi):',
    '  1. TikTok ve YouTube medya degisimi PUT ile DESTEKLENIYOR (15 Eki olcumu, PISCES_SAGITTARIUS): GET /v2/scheduler/posts/{id}'
    ' -> ayni govde, yalniz media[0] yeni -> PUT -> uuid ile GET. TikTok 394636011 -> 396667159, YouTube 394636026 -> 396667223:'
    ' yeni id, uuid ayni, durum PENDING, izinsiz fark 0, gonderideki video PASS. YouTube S-JK-LlBGcQ (17 Eki) PUBLISHED,'
    ' video 0 sn parlakligi 9.8 (diger yayinlar 0.0; YT_KAPAK.csv 19 Eki).',
    '  2. Izinli fark: id, media[0], creationDate.*; Metricool TikTok/YouTube gonderisine instagramData.type=POST ve'
    ' showReelOnFeed=true ekler (ag Instagram degilse izinli). Metin, baslik, youtubeData, videoThumbnailUrl, saat, durum degisirse FAIL.',
    '  3. Yeni mp4 once Metricool deposuna yuklenir (metricool_5p_yaz.video_yukle), donusturulmus dosya olculur (kapak_basa kapilari);'
    ' ayni cift icin tek yukleme, ayni URL TikTok + YouTube (+ IG/FB) hedeflerine yazilir (metricool_video_degistir.py --hedef ag:id:uuid,...).',
    '  4. YouTube kapak gorseli: alan videoThumbnailUrl (ScheduledPost; youtubeData semasinda kapak alani yok). 19 Eki olcumu'
    ' (YT_KAPAK.csv): videoThumbnailUrl dolu yayinlarda i.ytimg hq720/hqdefault = bizim kapak (fark 0.6-1.0); Shorts akisi oar2'
    ' ise videodan kare (~8 sn), kapak gorselinden degil. Yani YouTube ozel kapagi ayarlanabiliyor, Shorts akisini videonun kendisi belirler.',
    '  5. TikTok: tiktokData semasi bos (swagger); kapak secimi icin alan videoCoverMilliseconds (ms) / videoThumbnailUrl; TikTok\'ta'
    ' yayin sonrasi hangisinin kullanildigi bu kosuda olculmedi.',
    '  6. Kapilar: yalniz PENDING ve yayina >= 2 sa kalan; once tek cift (TikTok + YouTube), geri okuma PASS ise kalanlar; FAIL -> DUR;'
    ' geri alma ONCE.json govdesiyle PUT (mod geri).',
]


if __name__ == '__main__':
    main()
