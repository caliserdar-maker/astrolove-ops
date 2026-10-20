#!/usr/bin/env python3
"""Sosyal takvim PLANI v2 + KURU uygulama (Serdar kararlari 20 Eki 2026). Metricool'a YAZMA YOK: yalniz GET; yazilacak
istekler KURU_ISTEKLER.json'a dokulur (yazma ayri onayla, ayri betik/kosu).
Kurallar:
  1. Sira 28 Eki 2026'dan (gun adi degil): P K Y P K Y P tekrar (haftada 3 poster, 2 kupa, 2 yil donumu). 27 Eki'ye kadar
     degisiklik yok (IG karusel 27 Eki'ye kadar sabit).
  2. Yalniz icerigi olan yer acilir: ilk parti 4 kupa + 4 yil donumu (CANCER_LIBRA, AQUARIUS_LIBRA, SCORPIO_TAURUS,
     ARIES_LIBRA); ilan Etsy'de active degilse o ilanin yeri acilmaz (DURUM.json, GET /listings/batch). Acilan her yerdeki
     poster grubu silinmez: mevcut sirasiyla son grup gununden (28 Ara) sonraki ardisik gunlere, ayni saatle (+N gun).
     Acilmayan kupa/yil donumu gunlerinde poster surer.
  3. CTA: IG "Make it yours on Etsy, link in bio."; TikTok, Facebook, YouTube "Make it yours: search AstroLoveArt on Etsy.";
     Threads poster metnindeki gibi ("... by AstroLoveArt, made for you on Etsy.").
  4. Medya adayi (Drive, olculur): gorsel = KUPA_KAPAK_78/KAPAK | KAPAK_Y1_78/KAPAK; video = kupa ILAN_VIDEO_78/KUPA,
     yil donumu SOSYAL_VIDEO_YD_ORNEK (Reel) yoksa ILAN_VIDEO_78/YILDONUMU.
Cikti: PLAN_V2.csv, OZET_V2.txt, KURU_UYGULAMA.txt, KURU_ISTEKLER.json, HAM_scheduler_*.json.
Kullanim: takvim_v2.py TOKEN.json CIKTI --durum DURUM.json --medya-ls LS.json --medya-dir DIR"""
import argparse
import csv
import importlib.util
import itertools
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('tp', os.path.join(D, 'takvim_plan.py'))
tp = importlib.util.module_from_spec(sp); sp.loader.exec_module(tp)
mpb = tp.mpb

TZ = 'Europe/Istanbul'
IST = ZoneInfo(TZ)
BASLA = date(2026, 10, 28)
SEQ = ['poster', 'kupa', 'yildonumu', 'poster', 'kupa', 'yildonumu', 'poster']
UFUK = datetime(2027, 2, 1)
MIN_SAAT = 2
CIFT = {'CANCER_LIBRA': ('4598525642', '4595350971'), 'AQUARIUS_LIBRA': ('4598523005', '4595377314'),
        'SCORPIO_TAURUS': ('4598541811', '4595402683'), 'ARIES_LIBRA': ('4598525779', '4595364151')}
CTA_IG, CTA_ARA = 'Make it yours on Etsy, link in bio.', 'Make it yours: search AstroLoveArt on Etsy.'
OZET = []


def log(s):
    print(s, flush=True); OZET.append(s)


def aile(d):
    return SEQ[(d - BASLA).days % 7] if d >= BASLA else 'poster'


def metin(aile_, ag, tur_, A, B):
    a_b, ab = f'{A} and {B}', f'{A} & {B}'
    if aile_ == 'kupa':
        kanca, urun = f'{a_b}, one mug?', 'personalized mug'
        govde = (f'Our {a_b} zodiac couple mug joins both signs into one gold fusion symbol. We add your two names and your '
                 f'personal message, so every morning starts with your own {a_b} symbol.')
        hediye = 'A personal zodiac gift for an anniversary, engagement or wedding.'
        ht5, ht3 = '#zodiacmug #zodiaccouple #personalizedmug #couplegift #astrologygift', '#zodiaccouple #personalizedmug #couplegift'
        yt_b = f'{a_b} Personalized Mug, Two Zodiac Signs as One Symbol'
        th = f'{ab}, one mug? Two zodiac signs become one shared gold symbol, with your two names and your message. A personalized couple mug by AstroLoveArt, made for you on Etsy.'
    else:
        kanca, urun = f'{a_b}, one year together?', '1st anniversary gift'
        govde = (f'Our {a_b} first anniversary print joins both signs into one shared symbol. We add your two names and your '
                 f'special date, the day you married or the day you met.')
        hediye = 'A personal paper anniversary gift for your husband or your wife, or for your first year together.'
        ht5, ht3 = '#firstanniversary #paperanniversary #anniversarygift #zodiaccouple #personalizedgift', '#firstanniversary #zodiaccouple #anniversarygift'
        yt_b = f'{a_b} First Anniversary Gift, Two Zodiac Signs as One Symbol'
        th = f'{ab}, one year together? Two zodiac signs become one shared symbol, with your names and your special date. A 1st anniversary gift by AstroLoveArt, made for you on Etsy.'
    if ag == 'threads':
        return th, ''
    if ag == 'youtube':
        return f'{kanca} Watch the {a_b} zodiac signs become one shared symbol. {govde.split(". ")[1]} {hediye} {CTA_ARA}\n\n{ht3}', yt_b
    if ag == 'tiktok':
        return f'{kanca} {govde} {hediye} {CTA_ARA} {ht5}', ''
    cta, ht = (CTA_IG, ht5) if ag == 'instagram' else (CTA_ARA, ht3)
    if tur_ == 'Reel':
        return f'{kanca} Watch two signs become one symbol.\n\n{a_b} {urun} with your names, designed by AstroLoveArt.\n\n{cta}\n\n{ht}', ''
    return f'{kanca}\n\n{govde}\n\n{hediye}\n\n{cta}\n\n{ht}', ''


def olc(yol):
    if not yol or not os.path.exists(yol):
        return None
    if yol.lower().endswith(('.mp4', '.mov')):
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                            '-of', 'json', yol], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout); s = j['streams'][0]
            return {'w': s['width'], 'h': s['height'], 'sn': round(float(j['format']['duration']), 1)}
        except (KeyError, IndexError, ValueError):
            return None
    from PIL import Image
    with Image.open(yol) as im:
        return {'w': im.width, 'h': im.height}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('durum', 'medya-ls', 'medya-dir'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    simdi = datetime.now(IST).replace(tzinfo=None)
    log(f'OKUMA: {simdi:%Y-%m-%d %H:%M} Istanbul; blogId {mc.b}; Metricool yalniz GET; yazma YOK')

    # Etsy durumu
    dj = json.load(open(a.durum))
    meta = dj.get('_meta', {})
    log(f"ETSY: {meta.get('uc')} {meta.get('okuma_utc')} UTC; cagri {meta.get('cagri')}, kota {meta.get('kota_son')}")
    acik = {'kupa': [], 'yildonumu': []}
    cikan = []
    for c, (k_id, y_id) in CIFT.items():
        for ail, lid in (('kupa', k_id), ('yildonumu', y_id)):
            st = (dj.get(lid) or {}).get('state', 'OKUNAMADI')
            log(f'  {c} {ail} {lid}: {st}')
            (acik[ail].append(c) if st == 'active' else cikan.append(f'{c} {ail} {lid} ({st})'))
    log(f'YAYINDA: kupa {acik["kupa"]}; yil donumu {acik["yildonumu"]}; plandan cikan {cikan or "yok"}')

    # Metricool bekleyenler
    ps, t = {}, simdi.replace(minute=0, second=0, microsecond=0)
    while t < UFUK:
        e = min(t + timedelta(days=3), UFUK)
        ls = tp.liste(mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}))
        if len(ls) >= 100:
            raise SystemExit(f'DUR: {t:%Y-%m-%d} penceresinde {len(ls)} kayit')
        json.dump(ls, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, default=str)
        for p in ls:
            ps[str(p.get('id'))] = p
        t = e
    kay, sablon_p = [], {}
    for p in ps.values():
        pr = p.get('providers') or []
        ag = (pr[0].get('network') or '').lower() if len(pr) == 1 else ''
        if ag not in tp.AGLAR or (pr[0].get('status') or '') != 'PENDING':
            continue
        pd = p.get('publicationDate') or {}
        try:
            z = datetime.fromisoformat((pd.get('dateTime') or '')[:19]).replace(tzinfo=ZoneInfo(pd.get('timezone') or TZ)).astimezone(IST).replace(tzinfo=None)
        except ValueError:
            continue
        if z <= simdi:
            continue
        g = z.date() if z.hour >= 12 else z.date() - timedelta(days=1)
        k = dict(z=z, gun=g, ag=ag, tur=tp.tur(p, ag), cift=tp.cift_ad((p.get('youtubeData') or {}).get('title'), p.get('text')),
                 uuid=str(p.get('uuid') or ''), id=p.get('id'), p=p)
        kay.append(k)
        sablon_p.setdefault((ag, k['tur']), p)
    grup = defaultdict(list)
    for k in kay:
        grup[k['gun']].append(k)
    gunler = sorted(grup)
    son = gunler[-1]
    log(f'BEKLEYEN: {len(kay)} gonderi, {len(gunler)} grup gunu ({gunler[0]} - {son}); grup basina {dict(Counter(len(grup[g]) for g in gunler))}')

    # yerler: ilk len(acik) kupa ve yil donumu gunu (28 Eki'den)
    kg = [d for d in (BASLA + timedelta(days=i) for i in range((son - BASLA).days + 1)) if aile(d) == 'kupa'][:len(acik['kupa'])]
    yg = [d for d in (BASLA + timedelta(days=i) for i in range((son - BASLA).days + 1)) if aile(d) == 'yildonumu'][:len(acik['yildonumu'])]
    poster_cift = {g: (Counter(k['cift'] for k in grup[g] if k['cift']).most_common(1) or [('', 0)])[0][0] for g in gunler}

    def cakisma(at):
        n = 0
        for d_, c_ in at.items():
            for k_ in (d_ - timedelta(days=1), d_ + timedelta(days=1)):
                diger = at.get(k_) or (poster_cift.get(k_) if k_ not in at else None)
                if diger and set(c_.split('_')) & set(diger.split('_')):
                    n += 3 if c_ == diger else 1   # ayni cift ardisik gun: agir ceza
        return n
    en = None
    for pk in itertools.permutations(acik['kupa']):
        for py in itertools.permutations(acik['yildonumu']):
            at = dict(zip(kg, pk)); at.update(zip(yg, py))
            s_ = (cakisma(at), list(pk), list(py))
            if en is None or s_[0] < en[0][0]:
                en = (s_, at)
    atama = en[1] if en else {}
    acilan = sorted(atama)
    yeni_gun = {g: son + timedelta(days=i + 1) for i, g in enumerate(acilan)}
    for g in acilan:
        if g not in grup:
            log(f'UYARI: acilan gun {g} icin mevcut poster grubu yok')
    log(f'SIRA (28 Eki dan P K Y P K Y P): acilan kupa {[(str(d_), atama[d_]) for d_ in kg]}; yil donumu '
        f'{[(str(d_), atama[d_]) for d_ in yg]}; komsu gun ortak burc cezasi {en[0][0] if en else 0} (ortak burc 1, ayni cift 3)')
    log('KAYDIRILAN poster grubu: ' + '; '.join(f'{g} {poster_cift.get(g)} -> {yeni_gun[g]}' for g in acilan))
    cakis_hedef = [d_ for d_ in yeni_gun.values() if d_ in grup]
    if cakis_hedef:
        log(f'UYARI: kaydirma hedef gunlerinde mevcut grup var: {cakis_hedef}')

    # medya
    ls = json.load(open(a.medya_ls))
    def bul(kok, desen):
        return next((f'{kok}/{x["Path"]}' for x in ls.get(kok, []) if re.search(desen, x['Path'])), '')
    medya = {}
    for c in CIFT:
        k_id = CIFT[c][0]
        medya[('kupa', 'gorsel', c)] = bul('KUPA_KAPAK', rf'(^|[_/]){c}\.(jpe?g|png)$') or bul('KUPA_KAPAK', c)
        medya[('kupa', 'video', c)] = bul('ILAN_VIDEO_KUPA', rf'{k_id}_{c}\.mp4$') or bul('ILAN_VIDEO_KUPA', c)
        medya[('yildonumu', 'gorsel', c)] = bul('Y1_KAPAK', rf'(^|[_/]){c}[_.]') or bul('Y1_KAPAK', c)
        medya[('yildonumu', 'video', c)] = bul('YD_REEL', rf'^{c}_yd_reel\.mp4$') or bul('ILAN_VIDEO_YD', rf'^{c}_yd_video\.mp4$')
    olcum = {}
    for key, yol in medya.items():
        q = olc(os.path.join(a.medya_dir, yol)) if yol else None
        olcum[key] = q
        log(f'MEDYA {key[0]}/{key[1]}/{key[2]}: {yol or "YOK"} ' + (f'{q["w"]}x{q["h"]}' + (f' {q["sn"]} sn' if "sn" in q else '') if q else '(olculemedi)'))

    # PLAN + KURU istekler
    bas = ['grup_gunu', 'haftagunu', 'gun_ailesi', 'platform', 'tur', 'eylem', 'mevcut_yayin', 'yeni_yayin', 'cift', 'uuid',
           'metricool_id', 'hedef_ilan_id', 'ilan_state', 'medya', 'medya_olcu', 'metin', 'youtube_baslik', 'not']
    satir, istek, hata = [], [], []
    for g in gunler:
        for k in sorted(grup[g], key=lambda k: (k['z'], k['ag'])):
            if g in yeni_gun:
                yz = k['z'] + (yeni_gun[g] - g)
                ey, nt = 'KAYDIRILIR', f'grup {g} -> {yeni_gun[g]} (+{(yeni_gun[g] - g).days} gun, ayni saat)'
                kapi = k['z'] - simdi >= timedelta(hours=MIN_SAAT)
                if not kapi:
                    hata.append(f'{k["uuid"]} yayina {MIN_SAAT} sa dan az')
                istek.append({'sira': len(istek) + 1, 'islem': 'TASI', 'cagrilar': ['GET /v2/scheduler/posts/{id}', 'PUT /v2/scheduler/posts/{id}',
                              'GET uuid ile geri okuma'], 'id': k['id'], 'uuid': k['uuid'], 'ag': k['ag'], 'tur': k['tur'], 'cift': k['cift'],
                              'publicationDate.dateTime': {'once': f"{k['z']:%Y-%m-%dT%H:%M:%S}", 'sonra': f'{yz:%Y-%m-%dT%H:%M:%S}'},
                              'izinli_fark': ['id', 'publicationDate.dateTime', 'creationDate.*'], 'kapi_yayina_>=2sa': kapi})
                yzs = f'{yz:%Y-%m-%d %H:%M}'
            else:
                ey, nt, yzs = ('KALIR', '', '')
            satir.append([str(g), tp.GUN_AD[g.weekday()], aile(g) if g not in yeni_gun else f'{aile(g)} (yer acildi)', k['ag'], k['tur'], ey,
                          f"{k['z']:%Y-%m-%d %H:%M}", yzs, k['cift'], k['uuid'], k['id'], '', '', '', '', '', '', nt])
    yukle = {}
    for d_ in acilan:
        ail, c = aile(d_), atama[d_]
        A, B = (x.title() for x in c.split('_'))
        lid = CIFT[c][0 if ail == 'kupa' else 1]
        for ag, tr, saat, kay_ in tp.YER:
            z = datetime.combine(d_ + timedelta(days=kay_), datetime.strptime(saat, '%H:%M').time())
            tip = 'gorsel' if tr.startswith('gorsel') or ag == 'threads' else 'video'
            m_yol = medya[(ail, tip, c)]
            q = olcum[(ail, tip, c)]
            m, yt = metin(ail, ag, tr, A, B)
            h = tp.metin_kontrol(m + ' ' + yt)
            notlar = []
            if h:
                hata.append(f'{d_} {ag} {tr} metin: {h}')
            if not m_yol:
                notlar.append('MEDYA YOK'); hata.append(f'{d_} {c} {ail} {ag} {tr}: medya yok')
            elif tip == 'video' and q and q['h'] <= q['w']:
                notlar.append(f'video dikey degil ({q["w"]}x{q["h"]})')
            if tip == 'gorsel' and ag in ('instagram', 'threads'):
                notlar.append('tek gorsel (poster karuseli 4 slayt; kupa/yil donumu karuseli yok)')
            yukle.setdefault(m_yol, tip)
            ornek = sablon_p.get((ag, tr), {})
            govde = {'text': m, 'providers': [{'network': ag}], 'publicationDate': {'dateTime': f'{z:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ},
                     'media': [f'<YUKLENECEK:{m_yol}>'], 'autoPublish': ornek.get('autoPublish', True), 'draft': False}
            for alan_ in ('instagramData', 'facebookData', 'threadsData', 'tiktokData', 'youtubeData', 'saveExternalMediaFiles', 'shortener'):
                if alan_ in ornek and ornek[alan_] is not None:
                    v_ = json.loads(json.dumps(ornek[alan_]))
                    if isinstance(v_, dict):   # baska ciftin kapak/thumbnail/etiketi tasinmaz
                        for x_ in [x_ for x_ in v_ if re.search('thumb|cover|frame|tag|title', x_, re.I)]:
                            v_.pop(x_)
                    govde[alan_] = v_
            if ag == 'youtube':
                govde.setdefault('youtubeData', {})['title'] = yt
            istek.append({'sira': len(istek) + 1, 'islem': 'OLUSTUR', 'cagrilar': ['POST /v2/scheduler/posts', 'GET geri okuma'], 'aile': ail,
                          'cift': c, 'ilan': lid, 'ag': ag, 'tur': tr, 'govde': govde, 'ag_alanlari_kaynagi': f"mevcut bekleyen {ag}/{tr} gonderisi {ornek.get('id', '-')}",
                          'kapi_yayina_>=2sa': z - simdi >= timedelta(hours=MIN_SAAT)})
            satir.append([str(d_), tp.GUN_AD[d_.weekday()], ail, ag, tr, f'YENI_{ail.upper()}', '', f'{z:%Y-%m-%d %H:%M}', c, '', '', lid,
                          (dj.get(lid) or {}).get('state', ''), m_yol, (f'{q["w"]}x{q["h"]}' + (f' {q["sn"]}sn' if 'sn' in q else '')) if q else '',
                          m, yt, '; '.join(notlar)])
    satir.sort(key=lambda r: (r[0], r[7] or r[6], r[3]))
    with open(os.path.join(out, 'PLAN_V2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(bas); w.writerows(satir)
    json.dump(istek, open(os.path.join(out, 'KURU_ISTEKLER.json'), 'w'), ensure_ascii=False, indent=1)
    n_tasi = sum(1 for x in istek if x['islem'] == 'TASI'); n_yeni = sum(1 for x in istek if x['islem'] == 'OLUSTUR')
    n_yuk = len([y for y in yukle if y])
    log(f'PLAN_V2.csv: {len(satir)} satir; {dict(Counter(r[5] for r in satir))}')
    log(f'KURU: TASI {n_tasi} gonderi (GET + PUT + geri GET = {3 * n_tasi} cagri), OLUSTUR {n_yeni} gonderi (POST + geri GET = '
        f'{2 * n_yeni} cagri), medya yukleme {n_yuk} dosya (S3 upload-transactions PUT + PATCH = {2 * n_yuk} Metricool cagrisi + S3 PUT); '
        f'toplam Metricool cagrisi ~{3 * n_tasi + 2 * n_yeni + 2 * n_yuk}')
    log(f'KAPI/HATA: {len(hata)}' + (': ' + '; '.join(hata[:12]) if hata else ' (yok)'))
    with open(os.path.join(out, 'KURU_UYGULAMA.txt'), 'w', encoding='utf-8') as f:
        f.write('KURU UYGULAMA (Metricool YAZMA YOK; yazma ayri onayla)\n' + '\n'.join(OZET) + '\n\nSIRA: 1) medya yukle (video '
                'metricool_5p_yaz.video_yukle, gorsel ayni akis image/jpeg) 2) TASI: her gonderi GET -> yalniz publicationDate.dateTime '
                'degisir -> PUT -> uuid ile geri okuma (metin, medya, ag alanlari ayni) 3) OLUSTUR: POST -> geri okuma. Her adim tek tek; '
                'ilk FAIL -> DUR. Once 1 grup (TASI 7 + OLUSTUR 7), temizse kalanlar.\n\n')
        for x in istek:
            if x['islem'] == 'TASI':
                f.write(f"{x['sira']:3d} TASI {x['ag']}/{x['tur']} {x['cift']} uuid {x['uuid']}: {x['publicationDate.dateTime']['once']} -> "
                        f"{x['publicationDate.dateTime']['sonra']}  kapi>=2sa {x['kapi_yayina_>=2sa']}\n")
            else:
                g_ = x['govde']
                f.write(f"{x['sira']:3d} OLUSTUR {x['ag']}/{x['tur']} {x['aile']} {x['cift']} ilan {x['ilan']} {g_['publicationDate']['dateTime']} "
                        f"medya {g_['media'][0]} | metin: {g_['text'][:70].replace(chr(10), ' ')}...\n")
    open(os.path.join(out, 'OZET_V2.txt'), 'w').write('\n'.join(OZET) + '\n')


if __name__ == '__main__':
    main()
