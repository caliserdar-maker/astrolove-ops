#!/usr/bin/env python3
"""Sosyal takvim PLANI (20 Eki 2026, Serdar karari: haftada 3 poster, 2 kupa, 2 yil donumu). SALT OKUMA: Metricool'a YAZMA YOK.
Sira (22 Eki Car'dan): Car poster, Per kupa, Cum yil donumu, Cmt poster, Paz kupa, Pzt yil donumu, Sal poster.
1. GET /v2/scheduler/posts (simdi -> 1 Sub 2027, 3 gunluk parcalar): instagram, facebook, threads, tiktok, youtube; tek saglayicili
   gonderi. Cift metinden ("X and|& Y", alfabetik). Grup gunu: yayin saati >= 12:00 -> ayni gun, < 12:00 -> onceki gun
   (gun d: IG/FB gorsel 20:00, Threads 21:00; d+1 03:00 IG/FB Reel, TikTok, YouTube; plan_5p.py duzeni).
2. Gun d >= 22 Eki icin sira: poster gunu -> mevcut grup KALIR; kupa/yil donumu gunu -> mevcut poster grubu KAYDIRILIR
   (silinmez): mevcut sirasiyla son grup gununden sonraki ardisik gunlere, her gonderi ayni saatte (+N gun). Kupa/yil donumu
   gunu: 7 bos yer (ayni platform/saat duzeni). Ilk 14 gun (22 Eki - 4 Kas): 4 kupa + 4 yil donumu yeri ciftle doldurulur.
3. Cift secimi: CANCER_LIBRA + Ads gosterimi en yuksek 3 poster cifti (AstroLove_Ads_546_20260923.json, 24 Agu - 23 Eyl;
   POD ilanlari data/pod/pod78_ids.csv ile). Siralama komsu gunlerle ortak burc sayisi en az olan dondurme.
4. Hedef ilan: kupa KUPA_TASLAK_LISTE.csv (19 Eki), yil donumu BY78_TASLAKLAR.csv (14 Eki, state). Yayin durumu bu kosuda
   Etsy'den okunmadi.
Cikti: PLAN.csv, OZET.txt, METIN_SABLON.txt, HAM_scheduler_*.json, HAM_ads_ozet.json.
Kullanim: takvim_plan.py TOKEN.json CIKTI --ads ADS.json --kupa KUPA.csv --by BY78.csv --pod78 data/pod/pod78_ids.csv"""
import argparse
import csv
import json
import os
import re
import importlib.util
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = ZoneInfo(TZ)
BASLA = date(2026, 10, 22)
UFUK = datetime(2027, 2, 1)
AGLAR = ('instagram', 'facebook', 'threads', 'tiktok', 'youtube')
SIRA = {2: 'poster', 3: 'kupa', 4: 'yildonumu', 5: 'poster', 6: 'kupa', 0: 'yildonumu', 1: 'poster'}   # weekday()
SEQ = ['poster', 'kupa', 'yildonumu', 'poster', 'kupa', 'yildonumu', 'poster']   # 22 Eki'den gun sirasi
GUN_AD = ['Pzt', 'Sal', 'Car', 'Per', 'Cum', 'Cmt', 'Paz']
ILK_DOLU = 14
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces')
# gun d icin yer duzeni (platform, tur, saat, gun_kaydir)
YER = [('instagram', 'gorsel (karusel)', '20:00', 0), ('facebook', 'gorsel', '20:00', 0), ('threads', 'karusel', '21:00', 0),
       ('instagram', 'Reel', '03:00', 1), ('facebook', 'Reel', '03:00', 1), ('tiktok', 'video', '03:00', 1),
       ('youtube', 'Shorts', '03:00', 1)]
OZET = []


def log(s):
    print(s, flush=True); OZET.append(s)


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v if isinstance(v, list) else []


def cift_ad(*t):
    b = '|'.join(BURC)
    for x in t:
        m = re.search(r'\b(' + b + r')\s*(?:&|and)\s*(' + b + r')\b', (x or '').lower())
        if m:
            return '_'.join(sorted((m.group(1).upper(), m.group(2).upper())))
    return ''


def tur(p, ag):
    if ag == 'instagram':
        return 'Reel' if ((p.get('instagramData') or {}).get('type') or '').upper() == 'REEL' else 'gorsel (karusel)'
    if ag == 'facebook':
        return 'Reel' if ((p.get('facebookData') or {}).get('type') or '').upper() == 'REEL' else 'gorsel'
    return {'threads': 'karusel', 'tiktok': 'video', 'youtube': 'Shorts'}[ag]


def ads_oku(yol, pod):
    """Ads JSON (23 Eyl) -> {listing_id: gosterim}. Yapi belgesiz: liste icindeki sozlukler taranir; 10 haneli ilan
    kimligi ve 'views|impressions|gosterim' adli sayi alani aranir. Kullanilan alan adlari OZET'e yazilir."""
    j = json.load(open(yol, encoding='utf-8'))
    satir, alanlar = [], Counter()

    def gez(x):
        if isinstance(x, dict):
            satir.append(x)
            for v in x.values():
                gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)
    gez(j)
    out = {}
    for d in satir:
        # 23 Eyl Shop Manager Ads tablosu: {cells: [baslik, baslik, hedef, '', Views, Clicks, CTR, Orders, Revenue, Spend, ROAS],
        # href: /your/shops/me/advertising/listings/<id>} (1. kosu 39473171486: genel arama 0 ilan buldu)
        if isinstance(d.get('cells'), list) and isinstance(d.get('href'), str):
            m = re.search(r'/listings/(\d{9,11})', d['href'])
            if m and len(d['cells']) > 4:
                try:
                    out[m.group(1)] = float(str(d['cells'][4]).replace(',', ''))
                    alanlar['cells[4] (Views)'] += 1
                except ValueError:
                    pass
            continue
        lid = next((str(v) for k, v in d.items() if re.search(r'listing', k, re.I) and re.fullmatch(r'\d{9,11}', str(v))), None)
        if not lid:
            lid = next((m.group(1) for v in d.values() if isinstance(v, str) for m in [re.search(r'/listing/(\d{9,11})', v)] if m), None)
        if not lid:
            continue
        k = next((k for k in d if re.fullmatch(r'(?i)(views|impressions|gosterim|gösterim|ad_?views)', k)), None) \
            or next((k for k in d if re.search(r'(?i)impression|gosterim|gösterim', k)), None)
        if k is None:
            continue
        try:
            n = float(str(d[k]).replace(',', ''))
        except ValueError:
            continue
        alanlar[k] += 1
        out[lid] = max(out.get(lid, 0), n)
    log(f'ADS: {yol}: sozluk {len(satir)}, ilan {len(out)}, gosterim alani {dict(alanlar)}, POD (pod78) eslesen {sum(1 for l in out if l in pod)}')
    return out


def sablon(aile, ag, tur_, A, B):
    """Kupa / yil donumu metinleri; poster metinleriyle ayni yapi (data/sosyal/metin/*_78.csv), CTA 'link in bio'."""
    a_b, ab = f'{A} and {B}', f'{A} & {B}'
    if aile == 'kupa':
        urun, kanca = 'personalized mug', f'{a_b}, one mug?'
        govde = (f'Our {a_b} zodiac couple mug joins both signs into one gold fusion symbol. We add your two names and your '
                 f'personal message, so every morning starts with your own {a_b} symbol.')
        hediye = 'A personal zodiac gift for an anniversary, engagement or wedding.'
        ht5 = '#zodiacmug #zodiaccouple #personalizedmug #couplegift #astrologygift'
        ht3 = '#zodiaccouple #personalizedmug #couplegift'
        yt_b = f'{a_b} Personalized Mug, Two Zodiac Signs as One Symbol'
        th = f'{ab}, one mug? Two zodiac signs become one shared gold symbol, with your two names and your message. A personalized couple mug by AstroLoveArt, link in bio.'
    else:
        urun, kanca = '1st anniversary gift', f'{a_b}, one year together?'
        govde = (f'Our {a_b} first anniversary print joins both signs into one shared symbol. We add your two names and your '
                 f'special date, the day you married or the day you met.')
        hediye = 'A personal paper anniversary gift for your husband or your wife, or for your first year together.'
        ht5 = '#firstanniversary #paperanniversary #anniversarygift #zodiaccouple #personalizedgift'
        ht3 = '#firstanniversary #zodiaccouple #anniversarygift'
        yt_b = f'{a_b} First Anniversary Gift, Two Zodiac Signs as One Symbol'
        th = f'{ab}, one year together? Two zodiac signs become one shared symbol, with your names and your special date. A 1st anniversary gift by AstroLoveArt, link in bio.'
    cta = 'Make it yours on Etsy, link in bio.'
    if ag == 'threads':
        return th
    if ag == 'youtube':
        return (f'BASLIK: {yt_b}\nACIKLAMA: {kanca} Watch the {a_b} zodiac signs become one shared symbol. {govde.split(". ")[1]} '
                f'{hediye} {cta}\n\n{ht3}')
    if ag == 'tiktok':
        return f'{kanca} {govde} {hediye} {cta} {ht5}'
    if tur_ == 'Reel':
        return f'{kanca} Watch two signs become one symbol.\n\n{a_b} {urun} with your names, designed by AstroLoveArt.\n\n{cta}\n\n' \
               + (ht5 if ag == 'instagram' else ht3)
    return f'{kanca} Swipe to see your shared symbol.\n\n{govde}\n\n{hediye}\n\n{cta}\n\n' + (ht5 if ag == 'instagram' else ht3)


def metin_kontrol(t):
    hata = []
    if re.search('[–—]', t):
        hata.append('uzun/orta tire')
    if '+' in t:
        hata.append('+')
    if 'AstroLove ' in t or t.rstrip().endswith('AstroLove'):
        hata.append('marka AstroLove (AstroLoveArt olmali)')
    if len(re.findall(r'#\w+', t)) > 5:
        hata.append('hashtag > 5')
    return hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('ads', 'kupa', 'by', 'pod78'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    simdi = datetime.now(IST).replace(tzinfo=None)
    log(f'OKUMA: {simdi:%Y-%m-%d %H:%M} Istanbul; blogId {mc.b}; uc GET /v2/scheduler/posts; Metricool yazma YOK')

    # 1) bekleyenler
    ps, t = {}, simdi.replace(minute=0, second=0, microsecond=0)
    while t < UFUK:
        e = min(t + timedelta(days=3), UFUK)
        j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        ls = liste(j)
        if len(ls) >= 100:
            raise SystemExit(f'DUR: {t:%Y-%m-%d} penceresinde {len(ls)} kayit (kesilmis olabilir)')
        json.dump(ls, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, default=str)
        for p in ls:
            ps[str(p.get('id'))] = p
        t = e
    kay, durum, digr = [], Counter(), Counter()
    for p in ps.values():
        pr = p.get('providers') or []
        ag = (pr[0].get('network') or '').lower() if len(pr) == 1 else ''
        pd = p.get('publicationDate') or {}
        try:
            z = datetime.fromisoformat((pd.get('dateTime') or '')[:19]).replace(tzinfo=ZoneInfo(pd.get('timezone') or TZ)).astimezone(IST).replace(tzinfo=None)
        except ValueError:
            continue
        if z <= simdi:
            continue
        if ag not in AGLAR:
            digr[ag or f'{len(pr)} ag'] += 1; continue
        st = pr[0].get('status') or ''
        durum[(ag, st)] += 1
        if st != 'PENDING':
            continue
        c = cift_ad((p.get('youtubeData') or {}).get('title'), p.get('text'))
        g = z.date() if z.hour >= 12 else z.date() - timedelta(days=1)
        kay.append(dict(z=z, gun=g, ag=ag, tur=tur(p, ag), cift=c, uuid=str(p.get('uuid') or ''), id=p.get('id'), p=p))
    log(f'BEKLEYEN 5 ag (yayin > simdi): {dict(durum)}; diger aglar {dict(digr)}')
    grup = defaultdict(list)
    for k in kay:
        grup[k['gun']].append(k)
    gunler = sorted(grup)
    hata = []
    for g in gunler:
        cs = {k['cift'] for k in grup[g]}
        if len(cs) != 1:
            hata.append(f'{g}: birden cok cift {sorted(cs)}')
        sayim = Counter((k['ag'], k['tur']) for k in grup[g])
        if g >= BASLA and sorted(sayim) != sorted((y[0], y[1]) for y in YER):
            hata.append(f'{g}: yer duzeni farkli {dict(sayim)}')
    log(f'GRUP: {len(gunler)} gun ({gunler[0]} - {gunler[-1]}); grup basina gonderi {dict(Counter(len(grup[g]) for g in gunler))}; '
        f'tutarsiz {len(hata)}' + (': ' + '; '.join(hata[:10]) if hata else ''))
    for g in gunler[:3]:
        log(f'  ornek {g} {grup[g][0]["cift"]}: ' + ', '.join(f'{k["ag"]}/{k["tur"]} {k["z"]:%m-%d %H:%M}' for k in sorted(grup[g], key=lambda k: k['z'])))

    pod = {r['listing_id'].strip(): r['cift'].strip().upper() for r in csv.DictReader(open(a.pod78, encoding='utf-8-sig'))}
    ads = ads_oku(a.ads, pod)
    pod_ads = sorted(((n, pod[l]) for l, n in ads.items() if l in pod), key=lambda x: (-x[0], x[1]))
    json.dump([{'cift': c, 'gosterim': n} for n, c in pod_ads], open(os.path.join(out, 'HAM_ads_ozet.json'), 'w'), indent=1)
    top = [c for n, c in pod_ads if c != 'CANCER_LIBRA'][:3]
    log('ADS POD ilk 6 (gosterim, 24 Agu - 23 Eyl): ' + ', '.join(f'{c} {int(n)}' for n, c in pod_ads[:6]))
    secilen = ['CANCER_LIBRA'] + top
    kupa = {r['cift'].strip().upper(): r for r in csv.DictReader(open(a.kupa, encoding='utf-8-sig'))}
    by = {r['cift'].strip().upper(): r for r in csv.DictReader(open(a.by, encoding='utf-8-sig'))}
    for mod, ek in (('sira', ''), ('gun', '_GUN_ADINA_GORE')):
        AILE = (lambda d, m=mod: SEQ[(d - BASLA).days % 7] if m == 'sira' else SIRA[d.weekday()])
        # 2) sira (iki yorum: sira = 22 Eki ilk gun poster; gun = gun adina bagli, 22 Eki Persembe)
        son = gunler[-1]
        kalan_gun = [g for g in gunler if g >= BASLA]
        kaydir = [g for g in kalan_gun if AILE(g) != 'poster']
        yeni_gun = {g: son + timedelta(days=i + 1) for i, g in enumerate(kaydir)}
        yerler = [d for d in (BASLA + timedelta(days=i) for i in range((son - BASLA).days + 1)) if AILE(d) != 'poster']
        # alternatif B (yalniz bilgi): kaydirilanlar devam eden sirada yalniz poster gunlerine
        b, d = [], son + timedelta(days=1)
        while len(b) < len(kaydir):
            if AILE(d) == 'poster':
                b.append(d)
            d += timedelta(days=1)
        log(f'[{mod}] SIRA: {BASLA} - {son}: poster gunu {len(kalan_gun) - len(kaydir)} (KALIR), kupa/yil donumu gunu {len(yerler)} '
            f'(kupa {sum(1 for d in yerler if AILE(d) == "kupa")}, yil donumu {sum(1 for d in yerler if AILE(d) == "yildonumu")}); '
            f'KAYDIRILAN poster grubu {len(kaydir)} -> {min(yeni_gun.values()) if yeni_gun else "-"} .. {max(yeni_gun.values()) if yeni_gun else "-"} '
            f'(ardisik gunler). Diger kaydirma secenegi (devam eden sirada yalniz poster gunleri): {b[0] if b else "-"} .. {b[-1] if b else "-"}')

        # 3) cift secimi
        ilk = [d for d in yerler if d < BASLA + timedelta(days=ILK_DOLU)]
        k_gun = [d for d in ilk if AILE(d) == 'kupa']
        y_gun = [d for d in ilk if AILE(d) == 'yildonumu']
        poster_gun = {g: grup[g][0]['cift'] for g in kalan_gun if g not in yeni_gun}

        def komsu_cakisma(atama):
            gunluk = dict(poster_gun); gunluk.update(atama)
            n = 0
            for d_, c_ in atama.items():
                for k_ in (d_ - timedelta(days=1), d_ + timedelta(days=1)):
                    if k_ in gunluk and set(c_.split('_')) & set(gunluk[k_].split('_')):
                        n += 1
            return n
        en = None
        for rk in range(len(secilen)):
            for ry in range(len(secilen)):
                atama = {d_: secilen[(i + rk) % len(secilen)] for i, d_ in enumerate(k_gun)}
                atama.update({d_: secilen[(i + ry) % len(secilen)] for i, d_ in enumerate(y_gun)})
                s_ = (komsu_cakisma(atama), rk, ry)
                if en is None or s_ < en[0]:
                    en = (s_, atama)
        atama = en[1]
        log(f'[{mod}] CIFT SECIMI: {secilen} (CANCER_LIBRA + Ads ilk 3); ilk {ILK_DOLU} gun: kupa {[(str(d_), atama[d_]) for d_ in k_gun]}, '
            f'yil donumu {[(str(d_), atama[d_]) for d_ in y_gun]}; komsu gunle ortak burc {en[0][0]}')

        # 4) PLAN
        bas = ['grup_gunu', 'haftagunu', 'gun_ailesi', 'platform', 'tur', 'eylem', 'mevcut_yayin', 'yeni_yayin', 'cift', 'uuid',
               'metricool_id', 'hedef_aile', 'hedef_cift', 'hedef_ilan_id', 'hedef_ilan_durumu', 'metin', 'not']
        satir = []
        for g in gunler:
            aile = AILE(g) if g >= BASLA else 'poster (22 Eki oncesi)'
            for k in sorted(grup[g], key=lambda k: (k['z'], k['ag'])):
                if g < BASLA:
                    ey, yz, nt = 'KALIR (22 Eki oncesi)', '', ''
                elif g in yeni_gun:
                    ey = 'KAYDIRILIR'
                    yz = f"{k['z'] + (yeni_gun[g] - g):%Y-%m-%d %H:%M}"
                    nt = f'grup {g} -> {yeni_gun[g]} (+{(yeni_gun[g] - g).days} gun, ayni saat)'
                    if k['ag'] == 'instagram' and k['tur'].startswith('gorsel') and g <= date(2026, 10, 27):
                        nt += '; DIKKAT 13 Eki karari: IG karusel duzeni 27 Eki\'ye kadar sabit'
                else:
                    ey, yz, nt = 'KALIR', '', ''
                satir.append([str(g), GUN_AD[g.weekday()], aile, k['ag'], k['tur'], ey, f"{k['z']:%Y-%m-%d %H:%M}", yz, k['cift'],
                              k['uuid'], k['id'], '', '', '', '', '', nt])
        sablon_hata = []
        for d_ in yerler:
            aile = AILE(d_)
            c = atama.get(d_, '')
            for ag, tr, saat, kay_ in YER:
                z = datetime.combine(d_ + timedelta(days=kay_), datetime.strptime(saat, '%H:%M').time())
                if c:
                    A, B = (x.title() for x in c.split('_'))
                    lst = (kupa if aile == 'kupa' else by).get(c, {})
                    lid = lst.get('listing_id', '')
                    ld = (lst.get('durum', '') + ' (KUPA_TASLAK_LISTE 19 Eki)') if aile == 'kupa' else (lst.get('state', '') + ' (BY78_TASLAKLAR 14 Eki)')
                    m = sablon(aile, ag, tr, A, B)
                    h = metin_kontrol(m)
                    if h:
                        sablon_hata.append(f'{d_} {ag} {tr}: {h}')
                    nt = 'icerik (gorsel/video) henuz yok; ilan yayin durumu Etsy\'den dogrulanmadi'
                else:
                    lid, ld, m, nt = '', '', '', 'BOS: icerik yok (ilk 14 gun disi)'
                satir.append([str(d_), GUN_AD[d_.weekday()], aile, ag, tr, f'BOS_{aile.upper()}', '', f'{z:%Y-%m-%d %H:%M}', '', '', '',
                              aile, c, lid, ld, m, nt])
        satir.sort(key=lambda r: (r[0], r[7] or r[6], r[3]))
        with open(os.path.join(out, f'PLAN{ek}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(bas); w.writerows(satir)
        log(f'[{mod}] PLAN{ek}.csv: {len(satir)} satir; eylem {dict(Counter(r[5] for r in satir))}')
        log(f'Sablon metin kontrolu (tire, +, marka, hashtag<=5): {"PASS" if not sablon_hata else "FAIL " + "; ".join(sablon_hata[:5])}')
        ilk_kay = sorted(yeni_gun.items())[:6]
        log(f'[{mod}] KAYDIRMA ilk 6: ' + '; '.join(f'{g} {grup[g][0]["cift"]} -> {n}' for g, n in ilk_kay))
        log('HEDEF ILAN: ' + '; '.join(f'{c}: kupa {kupa.get(c, {}).get("listing_id", "-")} ({kupa.get(c, {}).get("durum", "-")}), '
                                        f'yil donumu {by.get(c, {}).get("listing_id", "-")} ({by.get(c, {}).get("state", "-")})' for c in secilen))
        log('DIKKAT: (1) TikTok poster metinleri "profilde tiklanabilir link yok" kuraliyla "search AstroLoveArt on Etsy" diyor; FB ve YouTube da '
            'ayni CTA. Sablonda istenen "link in bio" kullanildi; TikTok/FB/YT icin "Make it yours: search AstroLoveArt on Etsy." alternatifi '
            'METIN_SABLON.txt\'de. (2) 13 Eki karari IG karuselleri 27 Eki\'ye kadar sabit: 23-27 Eki kaydirmalari bu kararla cakisir. '
            '(3) Hedef ilanlarin yayin durumu bu kosuda Etsy\'den okunmadi (listelerdeki durum yazildi).')
    with open(os.path.join(out, 'METIN_SABLON.txt'), 'w', encoding='utf-8') as f:
        f.write('KUPA / YIL DONUMU GONDERI METIN SABLONU (Ingilizce; uzun/orta tire yok; poster metinleriyle ayni yapi; {A} {B} = cift\n'
                'anahtarindaki ilk ve ikinci burc, alfabetik; CTA "link in bio"). Kontrol: scripts/sosyal/analiz/takvim_plan.py metin_kontrol.\n\n')
        for aile in ('kupa', 'yildonumu'):
            for ag, tr, saat, _ in YER:
                f.write(f'=== {aile.upper()} / {ag} / {tr} ({saat})\n{sablon(aile, ag, tr, "{A}", "{B}")}\n\n')
        f.write('=== ALTERNATIF CTA (TikTok, Facebook, YouTube; mevcut poster metinlerindeki): "Make it yours: search AstroLoveArt on Etsy."\n\n')
        f.write('HEDEF ILAN ID (ilk 14 gun):\n')
        for c in secilen:
            f.write(f'  {c}: kupa {kupa.get(c, {}).get("listing_id", "-")} [{kupa.get(c, {}).get("durum", "-")}], '
                    f'yil donumu {by.get(c, {}).get("listing_id", "-")} [{by.get(c, {}).get("state", "-")}]\n')
    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(OZET) + '\n')


if __name__ == '__main__':
    main()
