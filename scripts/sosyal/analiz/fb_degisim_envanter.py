#!/usr/bin/env python3
"""Facebook bekleyen gonderi ENVANTER + yeni kapak ESLEME (20 Eki 2026). SALT OKUMA: Metricool'a YAZMA YOK, yalniz GET.
1) /v2/scheduler/posts (bugun -> UFUK, 5 gunluk pencereler): Facebook saglayicisi PENDING ve yayini simdiden sonra olanlar.
   Tur: facebookData.type REEL -> video; POST + medya > 1 -> album; POST + 1 medya -> tek gorsel (mp4 ise video).
2) Aile: metin 'mug' -> kupa; 'first year' / 'year together' / 'our year' -> yildonumu; medya instagram/v6/ ya da
   'gold symbol' -> poster; yoksa bilinmiyor. Cift: metindeki ilk iki burc (alfabetik); medya klasoru / Reel basligi ile capraz.
3) Gorunum olcumu (gorsel_benzerlik.benzerlik, NCC; esikler 20 Eki kalibrasyonu: ayni gorsel 0.98-1.00, eski-yeni kapak 0.82):
   video  kareler 0.1 / 0.3 / 1.5 sn + videoThumbnailUrl; s_yeni = yeni kapak, s_eski = VIDEO_V9 KAPAK (eski video acilisi).
          s_yeni >= 0.90 ve s_yeni - s_eski >= 0.05 -> degismemeli; kare okunamadi -> belirsiz; aksi -> degismeli
          (karar: sosyal video acilisi yeni kapak gorunumune gecer).
   gorsel her medya; s_eski = eski Etsy ilk gorseli (KAPAK_P2 YEDEK, yalniz poster ve yedegi olan ilan), s_yeni = yeni kapak.
          herhangi bir medya s_eski >= 0.90 ve s_eski - s_yeni >= 0.05 -> degismeli (albumde eski ilan kapagi);
          medya instagram/v6 karusel slayti ve eski kapak eslesmesi yok -> degismemeli (ilan kapagi degil, karar kapsami disi);
          diger -> belirsiz.
4) Yeni medya adayi: poster KAPAK_P2 BASLIK_A/KAPAK_A (oncelikli) > KAPAK; kupa KUPA_KAPAK KAPAK; yildonumu KAPAK_Y1 KAPAK;
   video icin aday yok.
Cikti: ESLEME.csv, OZET.txt, KONTAK_REEL.jpg, HAM_scheduler_*.json.
Kullanim: fb_degisim_envanter.py TOKEN.json CIKTI --ls-p2a LS --ls-p2 LS --ls-kupa LS --ls-y1 LS --ls-yedek LS --ls-vkapak LS
          --pod78 data/pod/pod78_ids.csv --kok-p2a D --kok-p2 D --kok-kupa D --kok-y1 D --kok-yedek D --kok-vkapak D --is DIR"""
import argparse
import csv
import importlib.util
import json
import os
import re
import subprocess
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(D)
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
sp = importlib.util.spec_from_file_location('gb', os.path.join(D, 'gorsel_benzerlik.py'))
gb = importlib.util.module_from_spec(sp); sp.loader.exec_module(gb)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
UFUK = datetime(2027, 2, 1)
BURC = r'Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces'
ESIK, PAY = 0.90, 0.05
KARELER = (0.1, 0.3, 1.5)


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v or []


def ls(yol):
    return json.load(open(yol)) if yol and os.path.exists(yol) and os.path.getsize(yol) else []


def cift_ad(s):
    z = re.findall(BURC.upper(), (s or '').upper())
    return '_'.join(sorted(z[:2])) if len(z) >= 2 else ''


def metin_cift(t):
    z = re.findall(BURC, t or '', flags=re.I)
    return '_'.join(sorted(x.upper() for x in z[:2])) if len(z) >= 2 else ''


def aile_bul(metin, medya):
    t = (metin or '').lower()
    if re.search(r'\bmugs?\b', t):
        return 'kupa', "metinde 'mug'"
    if re.search(r'first year|year together|our year', t):
        return 'yildonumu', "metinde 'first year/year together/our year'"
    if any('/instagram/v6/' in m for m in medya) or 'gold symbol' in t:
        return 'poster', 'medya instagram/v6 (IG v6 poster karuseli) / metin gold symbol'
    return 'bilinmiyor', 'kural yok'


def indir(url, yol):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'astrolove-ops'}), timeout=60) as r:
            open(yol, 'wb').write(r.read())
        return Image.open(yol).convert('RGB')
    except Exception as e:
        print(f'  indirilemedi {url[:90]}: {str(e)[:80]}')
        return None


def kare(url, t, yol):
    try:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', url, '-frames:v', '1', yol],
                           capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f'  kare {t} sn okunamadi: {str(e)[:120]}')
        return None
    if r.returncode or not os.path.exists(yol):
        print(f'  kare {t} sn okunamadi: {r.stderr.decode()[:120]}')
        return None
    return Image.open(yol).convert('RGB')


def rclone_al(kok, adlar, hedef):
    adlar = sorted({a for a in adlar if a})
    if not adlar or not kok:
        return
    os.makedirs(hedef, exist_ok=True)
    lst = os.path.join(hedef, '_liste.txt'); open(lst, 'w').write('\n'.join(adlar) + '\n')
    r = subprocess.run(['rclone', 'copy', kok, hedef, '--files-from', lst, '-q'], capture_output=True, timeout=900)
    print(f'rclone {os.path.basename(kok.rstrip("/"))}: {len(adlar)} istendi, rc {r.returncode}')


def yaz(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    for k in ('ls-p2a', 'ls-p2', 'ls-kupa', 'ls-y1', 'ls-yedek', 'ls-vkapak', 'pod78',
              'kok-p2a', 'kok-p2', 'kok-kupa', 'kok-y1', 'kok-yedek', 'kok-vkapak', 'is'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    isd = a.__dict__['is'] or os.path.join(out, '_is'); os.makedirs(isd, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    simdi = datetime.now(IST)
    print(f'OKUMA ANI: {simdi:%Y-%m-%dT%H:%M:%S%z}; blogId {mc.b}; ufuk {UFUK:%Y-%m-%d}')

    # --- aday klasorleri: cift -> dosya adi
    lid = {r['cift'].strip().upper(): r['listing_id'].strip() for r in csv.DictReader(open(a.pod78, encoding='utf-8-sig'))}
    aday = {'poster_A': {}, 'poster': {}, 'kupa': {}, 'yildonumu': {}}
    for anah, yol in (('poster_A', a.ls_p2a), ('poster', a.ls_p2), ('kupa', a.ls_kupa), ('yildonumu', a.ls_y1)):
        for f in ls(yol):
            c = cift_ad(f.get('Name')) if f.get('Name', '').lower().endswith('.jpg') else ''
            if c:
                aday[anah].setdefault(c, f['Name'])
    yedek = {}
    for f in ls(a.ls_yedek):
        m = re.fullmatch(r'(\d+)_(\d+)\.jpg', f.get('Name', ''))
        if m:
            yedek[m.group(1)] = f['Name']
    vkapak = {f['Name'].replace('-astroloveart-kapak.jpg', ''): f['Name'] for f in ls(a.ls_vkapak)
              if f.get('Name', '').endswith('-astroloveart-kapak.jpg')}
    print('ADAY: ' + ', '.join(f'{k} {len(v)}' for k, v in aday.items())
          + f'; eski Etsy kapak yedegi {len(yedek)}; eski video kapagi {len(vkapak)}; pod78 cift {len(lid)}')

    # --- zamanlayici
    ps, t = {}, datetime(simdi.year, simdi.month, simdi.day)
    while t < UFUK:
        e = min(t + timedelta(days=5), UFUK)
        try:
            j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        except SystemExit as ex:
            j = {'_hata': str(ex)[:300]}; print(f'SCHEDULER {t:%Y-%m-%d}: HATA {str(ex)[:150]}')
        json.dump(j, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
        for p in liste(j):
            if any((x.get('network') or '').lower() == 'facebook' for x in p.get('providers') or []):
                ps[str(p.get('uuid') or p.get('id'))] = p
        t = e
    gelecek, durumlar = [], Counter()
    for p in ps.values():
        pr = next(x for x in p['providers'] if (x.get('network') or '').lower() == 'facebook')
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        try:
            z = datetime.fromisoformat(zt).replace(tzinfo=IST)
        except ValueError:
            continue
        if z <= simdi:
            continue
        durumlar[pr.get('status')] += 1
        if pr.get('status') == 'PENDING':
            gelecek.append((zt, p, pr))
    gelecek.sort(key=lambda x: x[0])
    print(f'GELECEK Facebook durumlari: {dict(durumlar)}; PENDING {len(gelecek)}')

    # --- satir hazirligi
    S = []
    for zt, p, pr in gelecek:
        fd = p.get('facebookData') or {}
        md = [m.get('url') if isinstance(m, dict) else m for m in p.get('media') or []]
        md = [m for m in md if m]
        video = (fd.get('type') or '').upper() == 'REEL' or any(m.lower().split('?')[0].endswith('.mp4') for m in md)
        tur = 'video' if video else ('album' if len(md) > 1 else 'tek gorsel')
        af, kural = aile_bul(p.get('text'), md)
        cm = metin_cift(p.get('text'))
        ck = next((c for m in md for c in [re.search(r'/instagram/v6/([A-Z]+_[A-Z]+)/', m)] if c), None)
        ck = ck.group(1) if ck else ''
        cb = metin_cift(fd.get('title'))
        cift = cm or ck or cb
        notlar = [f'{ad} cifti {c} != {cift}' for ad, c in (('medya klasoru', ck), ('Reel basligi', cb)) if c and c != cift]
        if af == 'poster':
            ad_ = aday['poster_A'].get(cift) or aday['poster'].get(cift) or ''
            kay = 'KAPAK_P2 BASLIK_A/KAPAK_A' if cift in aday['poster_A'] else ('KAPAK_P2 KAPAK' if ad_ else '')
        elif af in ('kupa', 'yildonumu'):
            ad_ = aday[af].get(cift, ''); kay = ('KUPA_KAPAK KAPAK' if af == 'kupa' else 'KAPAK_Y1 KAPAK') if ad_ else ''
        else:
            ad_, kay = '', ''
        linkler = sorted(set(re.findall(r'https?://\S+', (p.get('text') or '') + ' ' + (p.get('firstCommentText') or ''))))
        S.append(dict(p=p, pr=pr, zt=zt, tur=tur, aile=af, kural=kural, cift=cift, md=md, notlar=notlar, aday=ad_, aday_kay=kay,
                      link=' | '.join(([pr.get('publicUrl')] if pr.get('publicUrl') else []) + linkler)))

    # --- referanslari indir
    kd = os.path.join(isd, 'ref')
    istek = {'poster_A': set(), 'poster': set(), 'kupa': set(), 'yildonumu': set()}
    for s in S:
        if s['aday']:
            istek['poster_A' if s['aday_kay'].endswith('KAPAK_A') else ('poster' if s['aile'] == 'poster' else s['aile'])].add(s['aday'])
    for anah, kok in (('poster_A', a.kok_p2a), ('poster', a.kok_p2), ('kupa', a.kok_kupa), ('yildonumu', a.kok_y1)):
        rclone_al(kok, istek[anah], os.path.join(kd, anah))
    rclone_al(a.kok_yedek, [yedek.get(lid.get(s['cift'], ''), '') for s in S if s['aile'] == 'poster' and s['tur'] != 'video'],
              os.path.join(kd, 'yedek'))
    rclone_al(a.kok_vkapak, [vkapak.get(s['cift'].lower().replace('_', '-and-'), '') for s in S if s['tur'] == 'video'],
              os.path.join(kd, 'vkapak'))

    def ref(alt, ad):
        y = os.path.join(kd, alt, ad) if ad else ''
        return Image.open(y).convert('RGB') if y and os.path.exists(y) else None

    # --- olcum
    satir, kontak = [], []
    for i, s in enumerate(S, 1):
        p = s['p']
        yeni = ref('poster_A' if s['aday_kay'].endswith('KAPAK_A') else ('poster' if s['aile'] == 'poster' else s['aile']), s['aday'])
        olc, s_y, s_e, eski_ref = [], 0.0, 0.0, ''
        if s['tur'] == 'video':
            vk = vkapak.get(s['cift'].lower().replace('_', '-and-'), '')
            eski = ref('vkapak', vk); eski_ref = f'VIDEO_V9 KAPAK/{vk}' if eski else 'yok'
            ims = [(f'{tt} sn', kare(s['md'][0], tt, os.path.join(isd, f'k{i}_{tt}.jpg'))) for tt in KARELER] if s['md'] else []
            if p.get('videoThumbnailUrl'):
                ims.append(('thumbnail', indir(p['videoThumbnailUrl'], os.path.join(isd, f'k{i}_th.jpg'))))
            okunan = [(ad, im) for ad, im in ims if im is not None]
            for ad, im in okunan:
                y = gb.benzerlik(im, yeni) if yeni else None
                e = gb.benzerlik(im, eski) if eski else None
                olc.append(f'{ad}: yeni {y} eski {e}')
                s_y, s_e = max(s_y, y or 0), max(s_e, e or 0)
            if not okunan:
                karar, neden = 'belirsiz', 'video karesi okunamadi'
            elif yeni is None:
                karar, neden = 'belirsiz', 'yeni kapak referansi yok'
            elif s_y >= ESIK and s_y - s_e >= PAY:
                karar, neden = 'degismemeli', 'acilis yeni kapak gorunumunde'
            else:
                karar = 'degismeli'
                neden = ('acilis eski video kapagi' if s_e >= ESIK else 'acilis yeni kapak degil') + '; karar: sosyal video acilisi yeni kapaga gecer'
            if okunan and len(kontak) < 30:
                kontak.append((f"{s['zt'][:16]} {s['cift']}", okunan[0][1], yeni))
        else:
            l = lid.get(s['cift'], '')
            eski = ref('yedek', yedek.get(l, '')) if s['aile'] == 'poster' else None
            eski_ref = f"KAPAK_P2 YEDEK/{yedek.get(l, '')}" if eski else 'yok'
            ig = all('/instagram/v6/' in m for m in s['md'])
            eski_var = False
            for j, m in enumerate(s['md'], 1):
                im = indir(m, os.path.join(isd, f'g{i}_{j}.jpg'))
                if im is None:
                    olc.append(f'medya {j}: okunamadi'); continue
                y = gb.benzerlik(im, yeni) if yeni else None
                e = gb.benzerlik(im, eski) if eski else None
                olc.append(f'medya {j}: yeni {y} eski {e}')
                s_y, s_e = max(s_y, y or 0), max(s_e, e or 0)
                eski_var |= bool(e is not None and e >= ESIK and e - (y or 0) >= PAY)
            if eski_var:
                karar, neden = 'degismeli', 'albumde eski Etsy ilan kapagi var'
            elif ig and s['md']:
                karar, neden = 'degismemeli', 'medya IG v6 karusel slaytlari (2-4); eski ilan kapagi degil, karar kapsami disi'
            else:
                karar, neden = 'belirsiz', 'medya kaynagi IG v6 degil ve eski kapak eslesmesi olculemedi'
        aday_ = 'yok (video icin henuz yok)' if s['tur'] == 'video' else (f"{s['aday_kay']}/{s['aday']}" if s['aday'] else 'yok')
        if s['tur'] != 'video' and karar == 'degismemeli' and s['aday']:
            aday_ = f"istege bagli: {aday_}"
        satir.append([p.get('id'), p.get('uuid', ''), s['zt'], s['tur'], (p.get('facebookData') or {}).get('type', ''), s['aile'],
                      s['cift'], lid.get(s['cift'], '') if s['aile'] == 'poster' else '',
                      re.sub(r'\s+', ' ', p.get('text') or '')[:90], s['link'], ' | '.join(s['md']), p.get('videoThumbnailUrl') or '',
                      karar, neden, aday_, f"{s['aday_kay']}/{s['aday']}" if s['tur'] == 'video' and s['aday'] else '',
                      round(s_y, 4), round(s_e, 4), eski_ref, '; '.join(olc), s['kural'], '; '.join(s['notlar'])])
        print(f"{i}/{len(S)} {s['zt']} {s['tur']} {s['aile']} {s['cift']}: {karar} (s_yeni {round(s_y, 3)}, s_eski {round(s_e, 3)})")
    yaz(out, 'ESLEME.csv', ['gonderi_id', 'uuid', 'tarih', 'tur', 'facebookData_type', 'aile', 'cift', 'poster_ilan_id',
                            'aciklama_basi', 'link', 'medya_url', 'video_kapak_url', 'karar', 'neden', 'yeni_medya_adayi',
                            'video_acilis_referansi', 's_yeni', 's_eski', 'eski_referans', 'olcumler', 'aile_kurali', 'not'], satir)

    if kontak:
        W = 3 * 240; k = Image.new('RGB', (W, 300 * len(kontak)), 'white')
        from PIL import ImageDraw
        dr = ImageDraw.Draw(k)
        for r, (ad, im, yn) in enumerate(kontak):
            for c, x in enumerate((im, yn)):
                if x is not None:
                    x = x.copy(); x.thumbnail((230, 270)); k.paste(x, (c * 240 + 5, r * 300 + 25))
            dr.text((5, r * 300 + 5), f'{ad}  (sol: video karesi, orta: yeni kapak)', fill='black')
        k.save(os.path.join(out, 'KONTAK_REEL.jpg'), quality=80)

    # --- ozet
    o = [f'Okuma: {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul), blogId {mc.b}, uc GET /v2/scheduler/posts, pencere bugun - {UFUK:%Y-%m-%d}',
         f'Gelecek Facebook gonderileri durum: {dict(durumlar)}; bekleyen (PENDING): {len(satir)}'
         + (f'; ilk {satir[0][2]}, son {satir[-1][2]}' if satir else ''),
         f"Tur: {dict(Counter(r[3] for r in satir))}; aile: {dict(Counter(r[5] for r in satir))}; cift sayisi {len({r[6] for r in satir})}",
         f"Karar: {dict(Counter(r[12] for r in satir))}",
         f"Karar x tur: {dict(Counter((r[3], r[12]) for r in satir))}",
         f"Yeni kapak adayi bulunan gorsel gonderi: {sum(1 for r in satir if r[3] != 'video' and 'yok' not in r[14])}; "
         f"video acilis referansi bulunan: {sum(1 for r in satir if r[15])}",
         f"Notlu satir (cift celiskisi): {sum(1 for r in satir if r[21])}",
         f"Esikler: s >= {ESIK} ve fark >= {PAY} (NCC, 20 Eki kalibrasyonu: ayni gorsel 0.98-1.00, eski-yeni kapak 0.82)",
         '',
         'METRICOOL DEGISIKLIK YOLU (UYGULANMADI; ayri onay):',
         '  Video (Reel): scripts/sosyal/metricool_video_degistir.py (15 Eki onayli yol): mod kuru -> yaz. GET ile govde (ONCE.json),',
         '    yeni acilisli mp4 Metricool S3e yuklenir (metricool_5p_yaz.video_yukle), PUT /v2/scheduler/posts/{id} ayni govde',
         '    YALNIZ media[0] degisir; PUT yeni id verir, uuid ayni; uuid ile yeniden GET + FARK.csv; izinli fark disi = FAIL/DUR.',
         '    videoThumbnailUrl (kapak) ayri alan: yeni kapak gorunumu icin o da degisecekse izinli farka eklenmeli (Serdar onayi).',
         '    Kapi: PENDING ve yayina >= 2 sa. Yeni video henuz yok: once uretim, sonra kuru kosu, sonra onay.',
         '  Album / tek gorsel: ayni GET -> PUT yolu; media[] dizisinde yalniz degisecek URL (yeni kapak once github.io',
         '    astrolove-media altina yayinlanir, Metricool herkese acik URL ister); mediaAltText ayni sirada guncellenir;',
         '    metin, saat, facebookData, providers degismez. Once 1 gonderi kuru + 1 gonderi yaz + kontrol, sonra toplu.',
         '  Metricool arayuzu: Planlama > gonderi > Duzenle > medyayi kaldir/ekle > Kaydet (uuid korunur; tek tek).',
         '']
    for r in satir:
        o.append(f'  {r[2]} {r[3]:<10} {r[5]:<9} {r[6]:<20} {r[12]:<11} s_yeni {r[16]} s_eski {r[17]} | {r[14]}')
    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o[:9]))


if __name__ == '__main__':
    main()
