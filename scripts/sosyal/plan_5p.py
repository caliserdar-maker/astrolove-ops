#!/usr/bin/env python3
"""IG + FB + Threads + TikTok + YouTube Shorts KURU takvimi (Serdar onayli takvim, 12 Eki 2026). Metricool'a YAZMA YOK.
Gun d (Europe/Istanbul): 20:00 IG karusel (4 slayt) + FB 3 gorsel (slayt 2-4); 21:00 Threads karusel (4 slayt);
ertesi gun 03:00 ayni video: IG Reel, FB Reel, TikTok, YouTube Shorts. Her gun 1 cift, 78 gun.
Cift sirasi: ilk gun GEMINI_LEO; art arda iki gunde ortak burc yok; deterministik DFS (aday sirasi: burclarin son
kullanimindan bu yana gecen gun en cok olan once, esitlikte alfabetik).
Saat: dateTime Europe/Istanbul olarak acikca yazilir; utc ve Europe/Madrid karsiligi da verilir. Madrid yerel saati
belirsiz/yok olan (yaz saati gecisi) satirlar 5 dk ONCEYE alinir ve 'dst_notu' ile isaretlenir (25 Eki 2026 03:00 -> 02:55).
Metinler data/sosyal/metin/*_78.csv'den AYNEN; referans_hashtag gonderilmez.
Kullanim: plan_5p.py --metin-dir D --karusel KARUSEL.json --video VIDEO.json --url-kok URL --baslangic 2026-10-14
                      [--yt-kategori 26] --cikti PLAN_5_PLATFORM.csv"""
import argparse, csv, json, re, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

IST, MAD, UTC = ZoneInfo('Europe/Istanbul'), ZoneInfo('Europe/Madrid'), ZoneInfo('UTC')
ILK = 'GEMINI_LEO'
KOL = ['gun', 'tarih_saat', 'timezone', 'utc', 'madrid', 'dst_notu', 'platform', 'cift', 'tur', 'metin', 'medya_url', 'alt_metinler',
       'baslik', 'ek_alanlar', 'video_dosya', 'video_drive_id']


def oku(d, ad):
    return {r['cift_anahtari']: r for r in csv.DictReader(open(f'{d}/{ad}', encoding='utf-8-sig'))}


def sira(ciftler):
    """Deterministik DFS. Aday onceligi: (1) son 6 gunde ayni-burc cifti kullanildiysa ayni-burc ciftleri sona,
    (2) iki burcun en son kullanildigi gun en eski olan once (max, min), (3) alfabetik."""
    burc = {c: c.split('_') for c in ciftler}
    yol, kul = [ILK], {ILK}

    def son(b):
        for g in range(len(yol) - 1, -1, -1):
            if b in burc[yol[g]]:
                return g
        return -1

    def anahtar(c):
        a, b = burc[c]
        ayni_yakin = a == b and any(burc[x][0] == burc[x][1] for x in yol[-6:])
        return (ayni_yakin, max(son(a), son(b)), min(son(a), son(b)), c)

    def dfs():
        if len(yol) == len(ciftler):
            return True
        on = set(burc[yol[-1]])
        for c in sorted((c for c in ciftler if c not in kul and not (set(burc[c]) & on)), key=anahtar):
            yol.append(c); kul.add(c)
            if dfs():
                return True
            yol.pop(); kul.discard(c)
        return False
    sys.setrecursionlimit(10000)
    if not dfs():
        sys.exit('DUR: kurala uyan sira bulunamadi')
    return yol


def belirsiz(t):
    """t: Istanbul duvar saati. Madrid'deki karsiligi belirsiz ya da yoksa True."""
    m = t.replace(tzinfo=IST).astimezone(MAD).replace(tzinfo=None)
    return m.replace(tzinfo=MAD).astimezone(UTC) != m.replace(tzinfo=MAD, fold=1).astimezone(UTC)


def zaman(gun, saat):
    t0 = t = datetime.combine(gun, datetime.strptime(saat, '%H:%M').time())
    k = 0
    while belirsiz(t) and k < 13:
        t -= timedelta(minutes=5); k += 1
    n = '' if t == t0 else (f'Madrid karsiligi belirsiz (yaz saati gecisi); {t0:%H:%M} yerine {t:%H:%M}'
                            + (' (DUZELMEDI)' if belirsiz(t) else ''))
    u = t.replace(tzinfo=IST).astimezone(UTC)
    return t, u, u.astimezone(MAD), n


def main():
    ap = argparse.ArgumentParser()
    for k in ('metin-dir', 'karusel', 'video', 'url-kok', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--baslangic', default='2026-10-14'); ap.add_argument('--yt-kategori', default='26')
    a = ap.parse_args()
    D = a.metin_dir
    IGK, IGR, FB, TH, TT, YT = (oku(D, x) for x in ('IG_KARUSEL_78.csv', 'IG_REEL_78.csv', 'FACEBOOK_78.csv', 'THREADS_78.csv',
                                                     'TIKTOK_78.csv', 'YOUTUBE_SHORTS_78.csv'))
    ciftler = sorted(IGK)
    hata = []
    for ad, t in (('IG_REEL', IGR), ('FACEBOOK', FB), ('THREADS', TH), ('TIKTOK', TT), ('YOUTUBE', YT)):
        if sorted(t) != ciftler:
            hata.append(f'{ad} cift kumesi farkli')
    if len(ciftler) != 78 or ILK not in ciftler:
        hata.append(f'cift sayisi {len(ciftler)} / {ILK} yok')
    # karusel: KARUSEL/<CIFT>/<dosya>; slayt sirasi dosya adina gore
    kar = defaultdict(list)
    for x in json.load(open(a.karusel)):
        if not x.get('IsDir') and re.search(r'\.(jpe?g|png)$', x['Name'], re.I) and '/' in x['Path']:
            kar[x['Path'].split('/')[0]].append(x['Name'])
    vid = {x['Name']: x.get('ID', '') for x in json.load(open(a.video)) if x['Name'].endswith('.mp4')}
    if hata:
        sys.exit('DUR: ' + '; '.join(hata))
    s = sira(ciftler)
    bas = date.fromisoformat(a.baslangic)
    out = []
    for g, c in enumerate(s):
        A, B = (x.title() for x in c.split('_'))
        sl = sorted(kar.get(c, []))
        urls = [f"{a.url_kok.rstrip('/')}/{c}/{n}" for n in sl]
        vdosya = f"{c.lower().replace('_', '-and-')}-astroloveart-reel.mp4"
        gun = bas + timedelta(days=g)

        def satir(saat, gun_, platform, tur, metin, medya, alt, baslik='', ek=None, video=False):
            t, u, m, n = zaman(gun_, saat)
            out.append({'gun': g + 1, 'tarih_saat': t.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': 'Europe/Istanbul',
                        'utc': u.strftime('%Y-%m-%dT%H:%M:%SZ'), 'madrid': m.strftime('%Y-%m-%d %H:%M %Z'), 'dst_notu': n,
                        'platform': platform, 'cift': c, 'tur': tur, 'metin': metin, 'medya_url': ' | '.join(medya),
                        'alt_metinler': ' | '.join(alt), 'baslik': baslik, 'ek_alanlar': json.dumps(ek or {}, ensure_ascii=False),
                        'video_dosya': vdosya if video else '', 'video_drive_id': vid.get(vdosya, 'VIDEO_YOK') if video else ''})
        k, f, th, tt, yt = IGK[c], FB[c], TH[c], TT[c], YT[c]
        satir('20:00', gun, 'instagram', 'KARUSEL', k['caption'], urls, [k[f'alt_metin_{i}'] for i in (1, 2, 3, 4)],
              ek={'instagramData': {'type': 'POST', 'autoPublish': True}})
        satir('20:00', gun, 'facebook', 'GONDERI_3_GORSEL', f['gonderi_metni'], urls[1:4], [f[f'alt_metin_{i}'] for i in (2, 3, 4)],
              ek={'facebookData': {'type': 'POST'}})
        satir('21:00', gun, 'threads', 'KARUSEL', th['metin'], urls, [th[f'alt_metin_{i}'] for i in (1, 2, 3, 4)],
              ek={'threadsData': {'type': 'POST', 'replyControl': 'EVERYONE', 'shareAsInstagramStory': False},
                  'konu_etiketi': th['konu_etiketi'], 'NOT': 'Metricool threadsData konu etiketi alani yok (dogrulanmadi)'})
        g2 = gun + timedelta(days=1)
        vurl = ['VIDEO:' + vdosya]
        satir('03:00', g2, 'instagram', 'REEL', IGR[c]['caption'], vurl, [], video=True,
              ek={'instagramData': {'type': 'REEL', 'showReelOnFeed': True, 'autoPublish': True}})
        satir('03:00', g2, 'facebook', 'REEL', f['reel_caption'], vurl, [], baslik=f'{A} & {B}', video=True,
              ek={'facebookData': {'type': 'REEL', 'title': f'{A} & {B}'}})
        satir('03:00', g2, 'tiktok', 'VIDEO', tt['caption'], vurl, [], video=True,
              ek={'tiktokData': {'disableComment': False, 'disableDuet': False, 'disableStitch': False, 'isAigc': True,
                                 'commercialContentOwnBrand': True, 'commercialContentThirdParty': False},
                  'kapak_yazisi': tt['kapak_yazisi'], 'NOT': 'API metin ustu yazi desteklemez; kapak videodan/thumbnail'})
        satir('03:00', g2, 'youtube', 'SHORT', yt['aciklama'], vurl, [], baslik=yt['baslik'], video=True,
              ek={'youtubeData': {'title': yt['baslik'], 'type': 'SHORT', 'privacy': 'PUBLIC', 'category': a.yt_kategori,
                                  'madeForKids': yt['made_for_kids'].lower() == 'true',
                                  'isAiGeneratedContent': yt['sentetik_icerik'].lower() == 'true', 'notifySubscribers': True,
                                  'tags': [x.strip() for x in yt['etiketler'].split(',') if x.strip()]}})
    # kontroller
    hata = []
    say = Counter((r['platform'], r['tur'], r['cift']) for r in out)
    hata += [f'{k} {n} kez' for k, n in say.items() if n != 1]
    for (p, t) in {(r['platform'], r['tur']) for r in out}:
        n = sum(1 for r in out if (r['platform'], r['tur']) == (p, t))
        if n != 78:
            hata.append(f'{p}/{t} {n} satir')
    for i in range(1, len(s)):
        if set(s[i].split('_')) & set(s[i - 1].split('_')):
            hata.append(f'ortak burc gun {i}-{i + 1}: {s[i - 1]} {s[i]}')
    if s[0] != ILK:
        hata.append('ilk gun GEMINI_LEO degil')
    SINIR = {'instagram': 2200, 'facebook': 63206, 'threads': 500, 'tiktok': 2200, 'youtube': 5000}
    for r in out:
        m = r['metin']
        if not m or len(m) > SINIR[r['platform']]:
            hata.append(f"metin uzunluk {r['platform']} {r['cift']} {len(m)}")
        if '—' in m or '–' in m:
            hata.append(f"tire {r['platform']} {r['cift']}")
        if r['platform'] == 'instagram' and m.count('#') > 30:
            hata.append(f"ig hashtag {r['cift']}")
        if r['platform'] == 'youtube':
            yd = json.loads(r['ek_alanlar'])['youtubeData']
            if len(yd['title']) > 100 or len(','.join(yd['tags'])) > 500:
                hata.append(f"youtube baslik/etiket {r['cift']}")
        for al in [x for x in r['alt_metinler'].split(' | ') if x]:
            if len(al) > 1000:
                hata.append(f"alt metin > 1000 {r['platform']} {r['cift']}")
        if r['tur'] in ('KARUSEL',) and len(r['medya_url'].split(' | ')) != 4:
            hata.append(f"karusel 4 slayt degil {r['platform']} {r['cift']}: {len(kar.get(r['cift'], []))}")
        if r['tur'] == 'GONDERI_3_GORSEL' and len(r['medya_url'].split(' | ')) != 3:
            hata.append(f"fb 3 gorsel degil {r['cift']}")
        if r['video_drive_id'] == 'VIDEO_YOK':
            hata.append(f"video yok {r['cift']}")
        if 'DUZELMEDI' in r['dst_notu']:
            hata.append(f"dst {r['tarih_saat']}")
    out.sort(key=lambda r: (r['utc'], r['platform']))
    with open(a.cikti, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=KOL, lineterminator='\n'); w.writeheader(); w.writerows(out)
    open(a.cikti.replace('.csv', '_SIRA.csv'), 'w').write('gun,tarih,cift\n' + ''.join(
        f'{i + 1},{bas + timedelta(days=i)},{c}\n' for i, c in enumerate(s)))
    dst = [r for r in out if r['dst_notu']]
    print(f"PLAN {len(out)} satir, ilk {out[0]['tarih_saat']} (IST), son {out[-1]['tarih_saat']} (IST), gun {len(s)}, "
          f"sira ilk 5 {s[:5]}, dst kaydirilan {len(dst)}: {sorted({r['tarih_saat'] for r in dst})}")
    eks = Counter()
    for h in hata:
        eks[h.split(' ')[0] + ' ' + h.split(' ')[1]] += 1
    print('KONTROL ' + ('PASS' if not hata else f'FAIL ({len(hata)}): ' + '; '.join(hata[:12]) + f' | ozet {dict(eks)}'))
    sys.exit(0 if not hata else 1)


if __name__ == '__main__':
    main()
