#!/usr/bin/env python3
"""Pinterest takvim v2 YENI pinler (21 Eki 2026, Serdar onayi). Yalniz Pinterest; baska aga dokunulmaz.
alt komut liste: PLAN_V2.csv -> yayinlanacak dosya adlari (yd: <CIFT>_PIN.jpg, kupa: PIN_KUPA_<CIFT>.jpg); Metricool yok.
alt komut yeni (onay PIN_YENI_V2):
  1) "Zodiac Couple Mugs" panosu: metricool_pano_ac.py (tek kosu; varsa acmaz) + ayri GET geri okuma -> PANO.json
  2) 12 yil donumu pini: 90 gorsel adresi GET (HTTP + JPEG boyut); 12/12 200 ve tire denetimi PASS ise YENI_PIN_GOVDE.json govdeleri
     PLAN_V2 tarihinde POST (ayni saat + link Metricool'da varsa ATLA, POST yeniden denenmez) -> pencere geri okumasi -> YD_SONUC.csv
  3) 78 kupa pini KURU (Metricool'a EKLEME YOK): pano/link/tarih PLAN_V2'den, metin ilan metninden (KUPA78_ORCHARD_METIN.csv)
     -> KUPA_MEDYA.csv, KUPA_PIN_KURU.csv, KUPA_PIN_GOVDE.json; OZET.txt
Kullanim: pin_yeni_uygula.py liste --plan PLAN_V2.csv --tur yd|kupa
          pin_yeni_uygula.py yeni TOKEN.json --plan P --govde YENI_PIN_GOVDE.json --kupa-metin M.csv --kupa-liste L.csv --out OUT
                             --confirm PIN_YENI_V2 [--sahte-pano P.json --kuru]"""
import argparse
import copy
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))


def _yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


v1 = _yukle('v1', os.path.join(D, 'pin_takvim_plan.py'))
uy = _yukle('uy', os.path.join(D, 'pin_takvim_uygula.py'))
mpb, TZ = v1.mpb, v1.TZ
MEDYA = 'https://caliserdar-maker.github.io/astrolove-media/pinterest/v7/'
KUPA_PANO = 'Zodiac Couple Mugs'
KUPA_PANO_ACIKLAMA = 'Personalized zodiac couple mugs with your two signs, names and message by AstroLoveArt.'
ONAY = 'PIN_YENI_V2'
ZOD = ('Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces')

# Kupa pin metni: poster pin yapisi (cift adi + urun, kanca, urun bilgisi, kullanim/hediye, "by AstroLoveArt", Etsy cagrisi).
# Urun bilgisi yalniz kupa ilan aciklamasindan; her olgu ilan metninde ILAN_OLGU ile denetlenir.
KUPA_BASLIK = ('{A} and {B} Zodiac Couple Mug with Names, Personalized Coffee Mug Gift for Couples',
               '{A} and {B} Personalized Mug, Fusion Zodiac Symbol with Your Names and Message',
               '{A} and {B} Couple Mug, Custom Zodiac Gift for Wedding, Engagement or Anniversary')
KUPA_METIN = ('Two signs, one shared symbol. This {A} and {B} zodiac couple mug joins your two signs into one original fusion '
              'symbol, with your names on the front and your message on the back. One glossy white ceramic mug, printed on both '
              'sides, in 8 styles and two sizes, 11 oz or 15 oz. Personalized zodiac couple mug by AstroLoveArt. Tap the Pin to see '
              'it on Etsy.',
              'Start the morning with your two signs. A custom {A} and {B} coffee mug with one fusion symbol made from both zodiac '
              'signs, your two names and a short message of your own. Choose from 8 styles, 11 oz or 15 oz, made to order. A '
              'personalized couple gift for a wedding, engagement, anniversary or newlyweds. By AstroLoveArt, available on Etsy.',
              '{A} and {B} compatibility, on a mug. Your two zodiac signs become one original symbol, with your names in capitals '
              'on the front and your message and a small evil eye on the back. Glossy white ceramic, dishwasher and microwave safe, '
              '11 oz or 15 oz. A zodiac gift for couples who love astrology. Personalized couple mug by AstroLoveArt. Tap the Pin to '
              'personalize yours on Etsy.')
KUPA_ALT = '{A} and {B} zodiac couple mug with names, personalized white ceramic coffee mug with a fusion zodiac symbol'
ILAN_OLGU = ('One mug, printed on both sides', 'fusion symbol', 'your names in capitals', 'Back: your message',
             'nazar (evil eye)', '8 STYLES', '11 oz (325 ml)', '15 oz (444 ml)', 'Glossy white ceramic',
             'Dishwasher and microwave safe', 'Made to order', 'wedding gift', 'engagement gift', 'anniversary', 'newlywed',
             'couples who love astrology')


def metin_denetim(*metinler, kupa=False):
    """Bos liste = PASS. Uzun/orta tire her zaman yasak; kupa metninde '+', '=', '&' ve yalin 'AstroLove' de yasak."""
    h = []
    for t in metinler:
        if '—' in t or '–' in t:
            h.append('uzun/orta tire')
        if kupa:
            for c in '+=&':
                if c in t:
                    h.append(f'yasak karakter {c!r}')
        if re.search(r'AstroLove(?!Art)', t):
            h.append('yalin AstroLove')
    return sorted(set(h))


def plan_oku(yol, tur):
    on = 'YENI yil donumu' if tur == 'yd' else 'YENI kupa'
    return [r for r in csv.DictReader(open(yol, encoding='utf-8')) if r['kaynak'].startswith(on)]


def dosya_adi(r, tur):
    return f"{r['cift']}_PIN.jpg" if tur == 'yd' else f"PIN_KUPA_{r['cift']}.jpg"


def url(r, tur):
    return MEDYA + ('y1/' if tur == 'yd' else 'kupa/') + dosya_adi(r, tur)


def jpeg_boyut(b):
    i = 2
    while i + 9 < len(b) and b[:2] == b'\xff\xd8':
        if b[i] != 0xFF:
            return None
        m, n = b[i + 1], int.from_bytes(b[i + 2:i + 4], 'big')
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
        i += 2 + n
    return None


def gorsel(u):
    """(http, bayt, 'GxY') - GET (HEAD yerine: boyut olculur)."""
    for deneme in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'astrolove-ops'}), timeout=30) as r:
                b = r.read()
                wh = jpeg_boyut(b)
                return r.status, len(b), f'{wh[0]}x{wh[1]}' if wh else '?'
        except urllib.error.HTTPError as e:
            return e.code, 0, ''
        except Exception as e:
            if deneme:
                return f'hata {str(e)[:50]}', 0, ''
            time.sleep(3)


def ad(b):
    return b.capitalize()


def yaz_csv(yol, baslik, satirlar):
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)


def pano_ac(a, ozet):
    """metricool_pano_ac.py tek kosu (ayni adli pano varsa acmaz) + ayri GET geri okuma. (id, panolar{ad: id})."""
    gecici = os.path.join(a.out, '_pano')
    if a.sahte_pano:
        panolar = json.load(open(a.sahte_pano)); ac = {'sonuc': 'SAHTE'}
    else:
        p = subprocess.run([sys.executable, os.path.join(D, '..', 'metricool_pano_ac.py'), a.token, KUPA_PANO, KUPA_PANO_ACIKLAMA,
                            gecici], capture_output=True, text=True)
        print(p.stdout.strip()[-600:], p.stderr.strip()[-300:], sep='\n', flush=True)
        yol = os.path.join(gecici, 'PANO_AC.json')
        ac = json.load(open(yol)) if os.path.exists(yol) else {'sonuc': f'HATA rc={p.returncode}'}
        mc = mpb.MC(json.load(open(a.token)))
        panolar = v1.liste(mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b}))
    pid = {(b.get('name') or '').strip(): str(b.get('id')) for b in panolar}
    bul = [b for b in panolar if (b.get('name') or '').strip() == KUPA_PANO]
    dog = 'PASS' if len(bul) == 1 and str(bul[0].get('id')) == str(ac.get('id', bul[0].get('id'))) else 'FAIL'
    rapor = {'pano': KUPA_PANO, 'acma_sonucu': ac.get('sonuc'), 'id_post_yaniti_veya_ac': ac.get('id'),
             'id_geri_okuma': str(bul[0].get('id')) if bul else None, 'geri_okuma_ayni_adli_pano_sayisi': len(bul),
             'dogrulama': dog, 'description': (bul[0].get('description') if bul else None),
             'privacy': (bul[0].get('privacy') if bul else None), 'link_tahmini': ac.get('link_tahmini'),
             'pano_sayisi_once': ac.get('pano_sayisi_once'), 'pano_sayisi_sonra': len(panolar),
             'okuma_utc': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
    json.dump(rapor, open(os.path.join(a.out, 'PANO.json'), 'w'), ensure_ascii=False, indent=1)
    if os.path.isdir(gecici):
        for f in os.listdir(gecici):
            os.remove(os.path.join(gecici, f))
        os.rmdir(gecici)
    ozet.append(f"1) Pano \"{KUPA_PANO}\": {rapor['acma_sonucu']}; geri okuma id {rapor['id_geri_okuma']} ({dog}); "
                f"pano sayisi {rapor['pano_sayisi_once']} -> {rapor['pano_sayisi_sonra']}")
    return (rapor['id_geri_okuma'] if dog == 'PASS' else None), pid


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def yd_post(a, plan, govdeler, medya, ozet):
    """12 yil donumu pini POST + geri okuma. Dondurur: hata sayisi."""
    sutun = ['plan_tarih', 'plan_saat', 'cift', 'gorsel_url', 'gorsel_http', 'gorsel_boyut', 'pano_id', 'link', 'baslik',
             'metin_denetim', 'sonuc', 'id', 'uuid', 'geri_okuma', 'not']
    satir, hata = [], 0
    gov = {(g['publicationDate']['dateTime'][:16], g['pinterestData']['pinLink']): g for g in govdeler}
    on_hata = []
    if len(plan) != 12 or len(govdeler) != 12:
        on_hata.append(f'plan {len(plan)} / govde {len(govdeler)} (12 olmali)')
    eslesme = []
    for r in plan:
        k = (f"{r['yeni_tarih']}T{r['yeni_saat']}", r['link'])
        g = gov.get(k)
        if g is None:
            on_hata.append(f"{r['cift']}: govdede ayni tarih+link yok"); continue
        if g['media'] != [url(r, 'yd')]:
            on_hata.append(f"{r['cift']}: govde medyasi farkli")
        d = metin_denetim(g['pinterestData']['pinTitle'], g['text'], *g.get('mediaAltText', []))
        if d:
            on_hata.append(f"{r['cift']}: {d}")
        if medya[url(r, 'yd')][0] != 200:
            on_hata.append(f"{r['cift']}: gorsel HTTP {medya[url(r, 'yd')][0]}")
        if datetime.fromisoformat(k[0]) < simdi_ist() + timedelta(minutes=30):
            on_hata.append(f"{r['cift']}: yayin saati gecmis/yakin")
        eslesme.append((r, g, d))
    gecti = not on_hata
    mc = None if a.kuru else mpb.MC(json.load(open(a.token)))
    bas = datetime.fromisoformat(min(r['yeni_tarih'] for r in plan))
    son = datetime.fromisoformat(max(r['yeni_tarih'] for r in plan)) + timedelta(days=1)

    def mevcut():
        if mc is None:
            return {}
        return {(((p.get('publicationDate') or {}).get('dateTime') or '')[:16], (p.get('pinterestData') or {}).get('pinLink')): p
                for p in uy.pencere(mc, bas, son).values()}
    var = mevcut() if gecti else {}
    sonuc = {}
    for r, g, d in eslesme:
        k = (f"{r['yeni_tarih']}T{r['yeni_saat']}", r['link'])
        if not gecti:
            sonuc[k] = ('YAZILMADI', '', '', 'on kontrol FAIL: ' + '; '.join(on_hata)[:300])
        elif k in var:
            sonuc[k] = ('ZATEN_VAR', var[k].get('id'), var[k].get('uuid'), 'Metricool listesinde ayni saat + link')
        elif a.kuru:
            sonuc[k] = ('KURU', '', '', 'POST yok (--kuru)')
        else:
            try:
                y = mpb.veri(mc.istek('POST', '/v2/scheduler/posts', govde=g))
                y = y if isinstance(y, dict) else {}
                sonuc[k] = ('YAZILDI', y.get('id', ''), y.get('uuid', ''), '')
            except SystemExit as e:
                sonuc[k] = ('HATA', '', '', str(e)[:200])
            print(f"POST {r['yeni_tarih']} {r['yeni_saat']} {r['cift']}: {sonuc[k][0]}", flush=True)
    var = mevcut() if gecti and not a.kuru else {}
    for r, g, d in eslesme:
        k = (f"{r['yeni_tarih']}T{r['yeni_saat']}", r['link'])
        s, pid, puid, nt = sonuc[k]
        geri = '-'
        if s in ('YAZILDI', 'ZATEN_VAR'):
            p = var.get(k)
            if p is None:
                geri = 'FAIL: listede yok'
            else:
                pd, gpd = p.get('pinterestData') or {}, g['pinterestData']
                fark = [ad_ for ad_, b, o in (('baslik', gpd['pinTitle'], pd.get('pinTitle')), ('pano', gpd['boardId'], str(pd.get('boardId'))),
                                             ('link', gpd['pinLink'], pd.get('pinLink')), ('metin', g['text'], p.get('text')),
                                             ('medya', g['media'], p.get('media')), ('alt', g.get('mediaAltText'), p.get('mediaAltText')),
                                             ('ag', ['pinterest'], sorted(x.get('network') for x in p.get('providers') or [])))
                        if b != o]
                geri = 'PASS' if not fark else 'FAIL: ' + ','.join(fark)
                pid, puid = pid or p.get('id'), puid or p.get('uuid')
        if s in ('HATA', 'YAZILMADI') or geri.startswith('FAIL'):
            hata += 1
        m = medya[url(r, 'yd')]
        satir.append([r['yeni_tarih'], r['yeni_saat'], r['cift'], url(r, 'yd'), m[0], m[2], g['pinterestData']['boardId'], r['link'],
                      g['pinterestData']['pinTitle'], 'PASS' if not d else ';'.join(d), s, pid, puid, geri, nt])
    yaz_csv(os.path.join(a.out, 'YD_SONUC.csv'), sutun, satir)
    say = {x: sum(1 for s in satir if s[10] == x) for x in ('YAZILDI', 'ZATEN_VAR', 'KURU', 'HATA', 'YAZILMADI')}
    ozet.append(f"2) Yil donumu 12 pin: on kontrol {'PASS' if gecti else 'FAIL'}; gorsel 200 "
                f"{sum(1 for s in satir if s[4] == 200)}/12; sonuc {say}; geri okuma PASS {sum(1 for s in satir if s[13] == 'PASS')}"
                + ''.join('\n   ' + h for h in on_hata[:12]))
    return hata


def kupa_kuru(a, plan, mugs_id, pid, medya, ozet):
    metin = {r['kod']: r for r in csv.DictReader(open(a.kupa_metin, encoding='utf-8'))}
    liste = {r['cift']: r for r in csv.DictReader(open(a.kupa_liste, encoding='utf-8-sig'))}
    pano_id = dict(pid, **({KUPA_PANO: mugs_id} if mugs_id else {}))
    sutun = ['plan_tarih', 'plan_saat', 'cift', 'pano', 'pano_id', 'link', 'ilan_durum_taslak_liste', 'gorsel_url', 'gorsel_http',
             'gorsel_boyut', 'sablon', 'baslik', 'baslik_uzunluk', 'aciklama', 'aciklama_uzunluk', 'alt_metin', 'denetim']
    satir, govdeler, hata = [], [], []
    for i, r in enumerate(plan):
        c = r['cift']
        il, li = metin.get(c), liste.get(c)
        h = []
        if il is None or li is None:
            h.append('ilan metni/listesi yok')
        m = re.match(r'^(\w+) and (\w+) Personalized Mug', (il or {}).get('baslik', ''))
        A, B = (m.group(1), m.group(2)) if m else (ad(x) for x in c.split('_'))
        if not m or {A.upper(), B.upper()} != set(c.split('_')) or A not in ZOD or B not in ZOD:
            h.append('ilan basliginda burc sirasi okunamadi')
        if li and r['link'] != f"https://www.etsy.com/listing/{li['listing_id']}":
            h.append('link KUPA_TASLAK_LISTE listing_id ile ayni degil')
        eksik = [o for o in ILAN_OLGU if o.lower() not in (il or {}).get('aciklama', '').lower()]
        if eksik:
            h.append('ilanda yok: ' + ','.join(eksik))
        j = i % 3
        baslik, aciklama, alt = KUPA_BASLIK[j].format(A=A, B=B), KUPA_METIN[j].format(A=A, B=B), KUPA_ALT.format(A=A, B=B)
        h += metin_denetim(baslik, aciklama, alt, kupa=True)
        if len(baslik) > 100:
            h.append(f'baslik {len(baslik)} > 100')
        if len(aciklama) > 500:
            h.append(f'aciklama {len(aciklama)} > 500')
        if re.search(r'\b(two|2)[- ]mug|set of', baslik + aciklama, re.I):
            h.append('iki kupa seti ifadesi')
        pn = r['pano'].replace(' (OLUSTURULACAK)', '')
        if pn not in pano_id:
            h.append(f'pano id yok: {pn}')
        u = url(r, 'kupa'); g = medya[u]
        if g[0] != 200:
            h.append(f'gorsel HTTP {g[0]}')
        if g[2] != '1000x1250':
            h.append(f'gorsel boyut {g[2]}')
        govdeler.append({'publicationDate': {'dateTime': f"{r['yeni_tarih']}T{r['yeni_saat']}:00", 'timezone': TZ},
                         'text': aciklama, 'firstCommentText': '', 'providers': [{'network': 'pinterest'}], 'media': [u],
                         'autoPublish': True, 'saveExternalMediaFiles': False, 'mediaAltText': [alt], 'shortener': False,
                         'draft': False, 'pinterestData': {'boardId': pano_id.get(pn, f'PANO_YOK:{pn}'), 'pinTitle': baslik,
                                                           'pinLink': r['link'], 'pinNewFormat': False}})
        satir.append([r['yeni_tarih'], r['yeni_saat'], c, pn, pano_id.get(pn, 'YOK'), r['link'], (li or {}).get('durum', ''), u,
                      g[0], g[2], j + 1, baslik, len(baslik), aciklama, len(aciklama), alt, 'PASS' if not h else '; '.join(h)])
        if h:
            hata.append(f'{c}: ' + '; '.join(h))
    yaz_csv(os.path.join(a.out, 'KUPA_PIN_KURU.csv'), sutun, satir)
    json.dump(govdeler, open(os.path.join(a.out, 'KUPA_PIN_GOVDE.json'), 'w'), ensure_ascii=False, indent=1)
    from collections import Counter
    ozet.append(f"3) Kupa 78 pin KURU (Metricool'a ekleme YOK): denetim PASS {len(satir) - len(hata)}/{len(satir)}; "
                f"gorsel 200 {sum(1 for s in satir if s[8] == 200)}/{len(satir)}, 1000x1250 {sum(1 for s in satir if s[9] == '1000x1250')}; "
                f"pano {dict(Counter(s[3] for s in satir))}; baslik en uzun {max(s[12] for s in satir)}, aciklama en uzun "
                f"{max(s[14] for s in satir)}; ilan durumu (taslak liste) {dict(Counter(s[6] for s in satir))}; "
                f"tarih {plan[0]['yeni_tarih']} .. {plan[-1]['yeni_tarih']}" + ''.join('\n   ' + h for h in hata[:10]))
    return len(hata)


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest='komut', required=True)
    l = alt.add_parser('liste'); l.add_argument('--plan', required=True); l.add_argument('--tur', choices=['yd', 'kupa'], required=True)
    y = alt.add_parser('yeni'); y.add_argument('token')
    for k in ('plan', 'govde', 'kupa-metin', 'kupa-liste', 'out', 'confirm'):
        y.add_argument('--' + k, required=True)
    y.add_argument('--sahte-pano', default=''); y.add_argument('--kuru', action='store_true')
    a = ap.parse_args()
    if a.komut == 'liste':
        print('\n'.join(dosya_adi(r, a.tur) for r in plan_oku(a.plan, a.tur)))
        return
    if a.confirm != ONAY:
        sys.exit(f'DUR: onay {ONAY} degil')
    os.makedirs(a.out, exist_ok=True)
    yd, kupa = plan_oku(a.plan, 'yd'), plan_oku(a.plan, 'kupa')
    if len(yd) != 12 or len(kupa) != 78:
        sys.exit(f'DUR: plan yd {len(yd)} / kupa {len(kupa)} (12 / 78 olmali)')
    ozet = [f"PINTEREST YENI PINLER (21 Eki 2026, onay {ONAY}; yalniz Pinterest) - {simdi_ist():%Y-%m-%d %H:%M} Istanbul"]
    mugs_id, pid = pano_ac(a, ozet)
    t0, adres = time.time(), [url(r, 'yd') for r in yd] + [url(r, 'kupa') for r in kupa]
    medya = {}
    for i, u in enumerate(adres, 1):
        medya[u] = gorsel(u)
        if i % 15 == 0 or i == len(adres):
            g = time.time() - t0
            print(f'[gorsel {i}/{len(adres)}] gecen {g:.0f} sn, kalan ~{g / i * (len(adres) - i):.0f} sn, %{100 * i / len(adres):.0f}',
                  flush=True)
    yaz_csv(os.path.join(a.out, 'KUPA_MEDYA.csv'), ['cift', 'drive_kaynak', 'medya_drive', 'url', 'http', 'bayt', 'boyut'],
            [[r['cift'], f"ASTROLOVE/TEMP/KUPA_PIN_78_20261020/{dosya_adi(r, 'kupa')}",
              f"ASTROLOVE/TEMP/SOSYAL/PINTEREST/MEDYA/v7/kupa/{dosya_adi(r, 'kupa')}", url(r, 'kupa'), *medya[url(r, 'kupa')]]
             for r in kupa])
    ok = sum(1 for u in adres if medya[u][0] == 200)
    ozet.append(f"Gorsel adresleri: {ok}/{len(adres)} HTTP 200 (yd {sum(1 for r in yd if medya[url(r, 'yd')][0] == 200)}/12, "
                f"kupa {sum(1 for r in kupa if medya[url(r, 'kupa')][0] == 200)}/78)")
    h1 = 0 if mugs_id else 1
    h2 = yd_post(a, yd, json.load(open(a.govde)), medya, ozet)
    h3 = kupa_kuru(a, kupa, mugs_id, pid, medya, ozet)
    ozet.append(f"SONUC: {'PASS' if not (h1 or h2 or h3) else 'FAIL'} (pano {'PASS' if not h1 else 'FAIL'}, yd hata {h2}, kupa hata {h3})")
    open(os.path.join(a.out, 'OZET.txt'), 'w').write('\n'.join(ozet) + '\n')
    print('\n'.join(ozet), flush=True)
    sys.exit(0 if not (h1 or h2 or h3) else 4)


if __name__ == '__main__':
    main()
