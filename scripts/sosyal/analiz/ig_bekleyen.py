#!/usr/bin/env python3
"""Bekleyen Instagram gonderileri envanteri (20 Eki 2026, yeni kapak kararlari). SALT OKUMA: Metricool'a YAZMA YOK, yalniz GET.
1. /v2/scheduler/posts (simdi -> 31 Oca 2027, 3 gunluk parcalar): providers[instagram].status == PENDING ve yayin > simdi.
   Tur: instagramData.type REEL -> Reels; birden cok medya -> karusel; tek gorsel -> tek gorsel.
2. Aile + cift: metinden (kupa: mug/cup; yil donumu: anniversary + paper/first/1st/one year; poster: wall art/poster/
   couple art/compatibility art); cift metindeki "X and|& Y" (alfabetik). Kanit sutunu yazilir.
3. Medya olcumu (indirilir, yalniz GET):
   Reels  ffmpeg ilk 1.5 sn (sosyal/video_v9/kapak_basa.py ile ayni okuma): ilk kare parlakligi, en dusuk parlaklik,
          videoThumbnailUrl parlakligi, ilk kare - yeni kapak adayi farki (cover-fit, ESIK 2.0).
          Siyah acilis = ilk kare parlakligi < 3 (sosyal_kapak_oku SIYAH_MUTLAK) ya da en dusuk < kapak/2 (kapak_basa kapisi).
   Gorsel ilk gorsel - yeni kapak adayi farki (ayni yontem).
   Karar: Reels siyah acilis -> degismeli (aday yok: acilis ornegi bekleniyor); ilk kare yeni kapakla ayni -> degismemeli;
          diger -> belirsiz. Karusel: <= 27 Eki degismemeli (13 Eki karari), sonrasi belirsiz; ikisi de ISARETLI, oneri yok.
          Tek gorsel: aday ile ayni -> degismemeli; aday var -> degismeli; aday yok -> belirsiz.
4. Aday: Drive TEMP/KAPAK_P2_78_20261019/BASLIK_A/KAPAK_A (oncelikli), .../KAPAK; KUPA_KAPAK_78_20261019/KAPAK;
   KAPAK_Y1_78_20261019/KAPAK. Dosya adi <listing>_<CIFT>.jpg; liste ADAY_DIR/*.txt (rclone lsf), dosya gerekince rclone copyto.
Kullanim: ig_bekleyen.py TOKEN.json CIKTI_DIR ADAY_DIR IS_DIR"""
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image

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
KARUSEL_SABIT = datetime(2026, 10, 27, 23, 59, 59)
SIYAH_MUTLAK = 3.0
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
DRIVE = 'gdrive:ASTROLOVE/TEMP'
ADAY = [('poster', 'P2_A', f'{DRIVE}/KAPAK_P2_78_20261019/BASLIK_A/KAPAK_A'), ('poster', 'P2', f'{DRIVE}/KAPAK_P2_78_20261019/KAPAK'),
        ('kupa', 'KUPA', f'{DRIVE}/KUPA_KAPAK_78_20261019/KAPAK'), ('yil donumu', 'Y1', f'{DRIVE}/KAPAK_Y1_78_20261019/KAPAK')]
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
OZET = None


def log(s):
    print(s, flush=True)
    with open(OZET, 'a', encoding='utf-8') as f:
        f.write(s + '\n')


def cift_ad(metin):
    m = re.search(r'\b(' + '|'.join(BURC) + r')\s*(?:&|and)\s*(' + '|'.join(BURC) + r')\b', metin or '', re.I)
    return '_'.join(sorted((m.group(1).upper(), m.group(2).upper()))) if m else ''


def dosya_cift(ad):
    b = [x.upper() for x in re.findall('|'.join(BURC), ad.lower())]
    return '_'.join(sorted(b[:2])) if len(b) >= 2 else ''


def aile(metin, medya):
    t = (metin or '').lower()
    if re.search(r'\bmugs?\b|\bcup\b|coffee', t):
        return 'kupa', 'metin: mug/cup'
    if 'anniversary' in t and re.search(r'paper|first (?:year|wedding)|1st|one year', t):
        return 'yil donumu', 'metin: anniversary + paper/first/1st/one year'
    if re.search(r'wall art|poster|couple art|compatibility art', t):
        return 'poster', 'metin: wall art/poster/couple art/compatibility art'
    if any('/instagram/v6/' in u for u in medya):
        return 'poster', 'medya yolu instagram/v6 (poster karusel seti)'
    return 'belirsiz', 'metin ve medyada aile isareti yok'


def indir(url, hedef):
    if os.path.exists(hedef):
        return hedef
    r = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=120) as y, open(hedef, 'wb') as f:
        f.write(y.read())
    return hedef


def adaylar(aday_dir):
    out = {}
    for _, kod, yol in ADAY:
        f = os.path.join(aday_dir, f'{kod}.txt')
        ls = [x.strip() for x in open(f)] if os.path.exists(f) else []
        out[kod] = {dosya_cift(x): f'{yol}/{x}' for x in ls if x.lower().endswith(('.jpg', '.jpeg', '.png')) and dosya_cift(x)}
        log(f'ADAY {kod}: {len(out[kod])} cift ({yol})' + ('' if ls else '  liste bos / okunamadi'))
    return out


def aday_sec(ad, aile_, cift):
    for a, kod, _ in ADAY:
        if a == aile_ and cift in ad.get(kod, {}):
            return kod, ad[kod][cift]
    return '', ''


def aday_yerel(yol, is_dir):
    hedef = os.path.join(is_dir, 'aday_' + os.path.basename(yol))
    if not os.path.exists(hedef):
        subprocess.run(['rclone', 'copyto', yol, hedef, '-q'], check=True, timeout=300)
    return hedef


def gorsel_fark(a_yol, b_yol):
    a = np.asarray(Image.open(a_yol).convert('RGB'), np.float32)
    B = kb.kapak_dizi(b_yol, a.shape[1], a.shape[0])
    return round(float(np.abs(a - B).mean()), 2), f'{a.shape[1]}x{a.shape[0]}'


def reel_olc(yol, thumb, aday):
    v = kb.probe(yol)
    W, H = v['w'], v['h']
    n = int(round(kb.KONTROL_SN * v['fps'])) + 1
    ilk = kb.kareler(yol, W, H, n)
    parl = [float(f.mean()) for f in ilk]
    q = {'boyut': f'{W}x{H}', 'sure_sn': round(v['video_sn'], 2), 'ilk_kare_parlaklik': round(parl[0], 1),
         'min_parlaklik_0_1.5': round(min(parl), 1), 'thumb_parlaklik': '', 'ilk_kare_aday_fark': ''}
    esik_alt = None
    if thumb:
        T = kb.kapak_dizi(thumb, W, H)
        q['thumb_parlaklik'] = round(float(T.mean()), 1)
        q['ilk_kare_thumb_fark'] = round(float(np.abs(ilk[0] - T).mean()), 2)
        esik_alt = float(T.mean()) / 2
    if aday:
        q['ilk_kare_aday_fark'] = round(float(np.abs(ilk[0] - kb.kapak_dizi(aday, W, H)).mean()), 2)
    q['siyah_acilis'] = parl[0] < SIYAH_MUTLAK or (esik_alt is not None and min(parl) < esik_alt)
    return q


def main():
    global OZET
    tok, out, aday_dir, is_dir = sys.argv[1:5]
    for d in (out, is_dir):
        os.makedirs(d, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = mpb.MC(json.load(open(tok)))
    simdi = datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)
    log(f'OKUMA ANI (Istanbul): {simdi:%Y-%m-%dT%H:%M:%S}; blogId {mc.b}; donem simdi - {SON:%Y-%m-%d}')

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
    ig = []
    for p in ps.values():
        pr = [x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'instagram']
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        if pr and zt and datetime.fromisoformat(zt[:19]) > simdi:
            ig.append((zt, p, pr[0]))
    ig.sort(key=lambda x: x[0])
    log(f'SCHEDULER: {len(ps)} benzersiz gonderi; Instagram (yayin > simdi): {len(ig)}; durum {dict(Counter(x[2].get("status") for x in ig))}')
    json.dump([x[1] for x in ig], open(os.path.join(out, 'HAM_instagram_bekleyen.json'), 'w'), ensure_ascii=False, indent=1)

    ad = adaylar(aday_dir)
    satir, t0 = [], time.time()
    for i, (zt, p, pr) in enumerate(ig, 1):
        st = pr.get('status') or ''
        medya = [m if isinstance(m, str) else (m or {}).get('url', '') for m in p.get('media') or []]
        tip = ((p.get('instagramData') or {}).get('type') or '').upper()
        tur = 'Reels' if tip == 'REEL' else ('karusel' if len(medya) > 1 else ('tek gorsel' if medya else 'medya yok'))
        if tip not in ('', 'POST', 'REEL'):
            tur += f' ({tip})'
        metin = p.get('text') or ''
        a, kanit = aile(metin, medya)
        c = cift_ad(metin) or next((dosya_cift(os.path.basename(u)) for u in medya if dosya_cift(os.path.basename(u))), '')
        kod, ay = aday_sec(ad, a, c)
        link = ' '.join(re.findall(r'https?://\S+', metin + ' ' + (p.get('firstCommentText') or '')))
        q, karar, neden, hata = {}, 'belirsiz', '', ''
        try:
            if st != 'PENDING':
                karar, neden = 'belirsiz', f'durum {st} (bekleyen degil)'
            elif tur.startswith('Reels'):
                v = indir(medya[0], os.path.join(is_dir, f"r_{p.get('id')}.mp4"))
                th = indir(p['videoThumbnailUrl'], os.path.join(is_dir, f"t_{p.get('id')}.jpg")) if p.get('videoThumbnailUrl') else ''
                q = reel_olc(v, th, aday_yerel(ay, is_dir) if ay else '')
                os.remove(v)
                if q['siyah_acilis']:
                    karar, neden = 'degismeli', 'siyah acilis; yeni Reels acilisi henuz yok (acilis ornegi bekleniyor)'
                elif q['ilk_kare_aday_fark'] != '' and q['ilk_kare_aday_fark'] < kb.ESIK:
                    karar, neden = 'degismemeli', f'ilk kare yeni kapak adayi ile ayni (fark < {kb.ESIK})'
                else:
                    karar, neden = 'belirsiz', 'siyah acilis yok (kapakli acilis); yeni kapak gorunumlu acilis ornegi yokken karsilastirilamaz'
            elif tur.startswith('karusel'):
                g = indir(medya[0], os.path.join(is_dir, f"k_{p.get('id')}_1.jpg"))
                if ay:
                    q['ilk_gorsel_aday_fark'], q['boyut'] = gorsel_fark(g, aday_yerel(ay, is_dir))
                sabit = datetime.fromisoformat(zt[:19]) <= KARUSEL_SABIT
                karar = 'degismemeli' if sabit else 'belirsiz'
                neden = ('ISARETLI karusel: 13 Eki karari, duzen 27 Eki\'ye kadar sabit' if sabit
                         else 'ISARETLI karusel: 27 Eki sonrasi; degisim onerilmez (karar bekleniyor)')
            elif tur.startswith('tek gorsel'):
                g = indir(medya[0], os.path.join(is_dir, f"g_{p.get('id')}.jpg"))
                if ay:
                    q['ilk_gorsel_aday_fark'], q['boyut'] = gorsel_fark(g, aday_yerel(ay, is_dir))
                    ayni = q['ilk_gorsel_aday_fark'] < kb.ESIK
                    karar, neden = ('degismemeli', 'gorsel yeni kapak adayi ile ayni') if ayni else ('degismeli', 'gorsel yeni kapak adayindan farkli')
                else:
                    karar, neden = 'belirsiz', 'bu aile/cift icin yeni kapak adayi yok'
        except Exception as e:  # indirme / olcum hatasi: belirsiz + neden
            hata = f'{type(e).__name__}: {str(e)[:160]}'
            karar, neden = 'belirsiz', 'olcum yapilamadi'
        satir.append([zt, (p.get('publicationDate') or {}).get('timezone') or '', tur, st, a, kanit, c,
                      re.sub(r'\s+', ' ', metin)[:90], link, ' '.join(medya), p.get('videoThumbnailUrl') or '',
                      q.get('boyut', ''), q.get('ilk_kare_parlaklik', ''), q.get('min_parlaklik_0_1.5', ''), q.get('thumb_parlaklik', ''),
                      q.get('ilk_kare_aday_fark', q.get('ilk_gorsel_aday_fark', '')),
                      '' if 'siyah_acilis' not in q else ('evet' if q['siyah_acilis'] else 'hayir'),
                      karar, neden + (f'; olcum referansi {kod}' if tur.startswith('Reels') and ay else ''),
                      'REELS: yok (acilis ornegi bekleniyor)' if tur.startswith('Reels') else kod,
                      '' if tur.startswith('Reels') else ay, p.get('id'), p.get('uuid') or '', hata])
        if i % 10 == 0 or i == len(ig):
            g_ = time.time() - t0
            log(f'  {i}/{len(ig)} ({100 * i // len(ig)}%), gecen {g_:.0f} sn, kalan ~{g_ / i * (len(ig) - i):.0f} sn')
    bas = ['yayin_zamani', 'saat_dilimi', 'tur', 'durum', 'aile', 'aile_kaniti', 'cift', 'aciklama_basi', 'link', 'medya_url',
           'video_kapak_url', 'boyut', 'ilk_kare_parlaklik', 'min_parlaklik_0_1.5sn', 'kapak_gorseli_parlaklik',
           'ilk_kare_veya_gorsel_yeni_aday_fark', 'siyah_acilis', 'karar', 'neden', 'aday_klasor', 'yeni_medya_adayi',
           'metricool_id', 'uuid', 'olcum_hatasi']
    with open(os.path.join(out, 'ESLEME.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(bas); w.writerows(satir)
    log(f'CSV ESLEME.csv: {len(satir)} satir')
    for k, v in sorted(Counter((r[2], r[17]) for r in satir).items()):
        log(f'KARAR {k[0]} / {k[1]}: {v}')
    log(f'AILE: {dict(Counter(r[4] for r in satir))}; cift bos: {sum(1 for r in satir if not r[6])}; '
        f'aday bulunan: {sum(1 for r in satir if r[20])}; olcum hatasi: {sum(1 for r in satir if r[23])}')
    if satir:
        log(f'ILK / SON: {satir[0][0]} / {satir[-1][0]}')
    sr = [r for r in satir if r[2].startswith('Reels') and r[12] != '']
    if sr:
        log(f'REELS ilk kare parlaklik min/max: {min(r[12] for r in sr)} / {max(r[12] for r in sr)}; siyah acilis: '
            f'{sum(1 for r in sr if r[16] == "evet")}/{len(sr)}')
    for r in satir[:6] + [x for x in satir if x[23]][:5]:
        log('ORNEK ' + ' | '.join(str(x) for x in (r[0], r[2], r[4], r[6], r[12], r[13], r[14], r[15], r[16], r[17], r[23])))
    for x in YONTEM:
        log(x)


# Metricool'da degisim yontemi: depodaki olculmus kayitlardan (scripts/sosyal/metricool_video_degistir.py, 15 Eki
# 38712850093 / 38714561537; scripts/sosyal/metricool_pin_baslik.py IZINLI_FARK). Bu betik UYGULAMAZ.
YONTEM = [
    'YONTEM (uygulama ayri onayla; bu kosu hicbir sey yazmadi):',
    '  1. Medya guncelleme, sil-yeniden-planla DEGIL: GET /v2/scheduler/posts/{id} -> ayni govde, yalniz media[] (Reels: media[0])'
    ' degisir -> PUT /v2/scheduler/posts/{id} -> uuid ile yeniden GET + tam fark.',
    '  2. 15 Eki olcumu: PUT gonderiye YENI id verir, uuid ayni kalir; publicationDate govdede gittigi icin tarih/saat korunur.'
    ' Izinli fark yalniz id, media, creationDate.*; metin, kapak, saat, durum, ag alanlari degisirse FAIL.',
    '  3. Reels: yeni mp4 once Metricool deposuna yuklenir (metricool_5p_yaz.video_yukle), donusmus dosya olculur; instagramData.type'
    ' REEL ve showReelOnFeed degismemeli (degisirse Reel normal gonderiye doner). Kapak (videoThumbnailUrl) ayri alan.',
    '  4. Karusel / tek gorsel: media[] herkese acik, suresi dolmayan URL olmali (Metricool API rehberi); yeni gorsel once'
    ' astrolove-media (GitHub Pages) yoluna konur, sonra PUT. Karuseller 27 Eki\'ye kadar dokunulmaz (13 Eki karari).',
    '  5. Kapilar: yalniz PENDING ve yayina >= 2 sa kalan gonderi; tek tek, her FAIL -> DUR; geri alma ONCE govdesiyle PUT.',
    '  Sil + yeniden planla: uuid ve gecmis kaybolur, yeni gonderi olusur; gerekmedikce kullanilmaz.',
]


if __name__ == '__main__':
    main()
