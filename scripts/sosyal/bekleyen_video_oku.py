#!/usr/bin/env python3
"""Metricool BEKLEYEN video gonderileri, KURU liste (SALT OKUMA, Serdar 15 Eki 2026). Yalniz GET /v2/scheduler/posts.

Simdiden --bit'e kadar (7 gunluk parcalar) zamanlanmis gonderiler okunur; video iceren ve en az bir saglayicisi
yayinlanmamis (PENDING vb.) olanlar listelenir: gonderi id, uuid, saat, cift, platform, durum, kapak alani,
medya (sorgu dizesi olmadan), ag alanlari. Ayni video URL'sini paylasan gonderiler isaretlenir.
Ayrica 1 ornek gonderinin tam yapisi (URL'ler kisaltilmis) yazilir: degistirme (PUT) planinda korunacak alanlar icin.
Ciktilar: BEKLEYEN_VIDEO.csv, BEKLEYEN_VIDEO.json, BEKLEYEN_ORNEK_GONDERI.json
Kullanim: bekleyen_video_oku.py --token T.json --cikti DIR [--bit 2026-12-31T23:59:59]"""
import argparse, csv, importlib.util, json, os, re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
TZ = 'Europe/Istanbul'


def yukle(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(D, dosya))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


sko = yukle('sko', 'sosyal_kapak_oku.py')   # video_mu, cift_bul, medya_url, kisa


def kisalt(x):
    """Tum metin URL'lerinde sorgu dizesini at (imzali parametreler dosyaya girmesin)."""
    if isinstance(x, dict):
        return {k: kisalt(v) for k, v in x.items()}
    if isinstance(x, list):
        return [kisalt(v) for v in x]
    if isinstance(x, str) and x.startswith('http'):
        return x.split('?')[0]
    return x


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--token', required=True); a.add_argument('--cikti', required=True)
    a.add_argument('--bit', default='2026-12-31T23:59:59')
    o = a.parse_args()
    os.makedirs(o.cikti, exist_ok=True)
    mpb = sko.mc_yukle()
    mc = mpb.MC(json.load(open(o.token)))
    simdi = datetime.utcnow() + timedelta(hours=3)
    son = datetime.fromisoformat(o.bit)
    ps, t = {}, simdi - timedelta(hours=1)
    while t < son:
        e = min(son, t + timedelta(days=7))
        for p in mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': t.strftime('%Y-%m-%dT%H:%M:%S'),
                                                                  'end': e.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})) or []:
            ps[p.get('id')] = p
        t = e
    satir, ornek = [], {}
    url_say = Counter(kisa for kisa in (sko.kisa(sko.medya_url(p)) for p in ps.values() if sko.video_mu(p)) if kisa)
    for p in ps.values():
        if not sko.video_mu(p):
            continue
        prs = p.get('providers') or []
        bekleyen = [x for x in prs if (x.get('status') or '').upper() != 'PUBLISHED' and not x.get('publicUrl')]
        if not bekleyen:
            continue
        saat = (p.get('publicationDate') or {}).get('dateTime', '')
        if saat and datetime.fromisoformat(saat) < simdi:
            gecmis = 'EVET'
        else:
            gecmis = ''
        c = sko.cift_bul(p)
        mu = sko.kisa(sko.medya_url(p))
        r = {'id': p.get('id'), 'uuid': p.get('uuid', ''), 'saat': saat, 'cift': '_'.join(x.upper() for x in c) if c else '?',
             'platform': '+'.join((x.get('network') or '').lower() for x in prs), 'durum': '+'.join(x.get('status') or '' for x in prs),
             'detay': '+'.join(str(x.get('detailedStatus') or '') for x in prs), 'saati_gecmis': gecmis,
             'kapak_alani': bool(p.get('videoThumbnailUrl')), 'kapak_url': sko.kisa(p.get('videoThumbnailUrl') or ''),
             'video_url': mu, 'video_url_paylasan': url_say.get(mu, 0), 'medya_sayisi': len(p.get('media') or []),
             'draft': p.get('draft'), 'autoPublish': p.get('autoPublish'),
             'ag_alanlari': '|'.join(sorted(k for k, v in p.items() if k.endswith('Data') and v)),
             'videoCoverMilliseconds': p.get('videoCoverMilliseconds')}
        satir.append(r)
        ag = r['platform']
        if ag not in ornek:
            ornek[ag] = kisalt(p)
    satir.sort(key=lambda r: (r['saat'], r['platform']))
    alan = list(satir[0]) if satir else ['id']
    with open(os.path.join(o.cikti, 'BEKLEYEN_VIDEO.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, alan); w.writeheader(); [w.writerow(r) for r in satir]
    json.dump(satir, open(os.path.join(o.cikti, 'BEKLEYEN_VIDEO.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump(ornek, open(os.path.join(o.cikti, 'BEKLEYEN_ORNEK_GONDERI.json'), 'w'), ensure_ascii=False, indent=1)

    print(f'OKUMA {simdi:%Y-%m-%d %H:%M} Istanbul -> {o.bit}; listelenen gonderi {len(ps)}, bekleyen video gonderisi {len(satir)}')
    print('PLATFORM', dict(Counter(r['platform'] for r in satir)))
    print('DURUM', dict(Counter(r['durum'] for r in satir)), '| saati gecmis ama yayinlanmamis', sum(1 for r in satir if r['saati_gecmis']))
    print('KAPAK ALANI', dict(Counter((r['platform'], r['kapak_alani']) for r in satir)))
    gun = defaultdict(list)
    for r in satir:
        gun[r['saat'][:10]].append(r)
    if satir:
        print(f"ILK {satir[0]['saat']} {satir[0]['cift']} | SON {satir[-1]['saat']} {satir[-1]['cift']} | gun {len(gun)}, cift {len({r['cift'] for r in satir})}")
    fbyt = [r for r in satir if any(x in r['platform'] for x in ('facebook', 'youtube'))]
    print(f"FACEBOOK/YOUTUBE iceren {len(fbyt)} (facebook {sum('facebook' in r['platform'] for r in satir)}, youtube {sum('youtube' in r['platform'] for r in satir)})")
    print('VIDEO URL paylasimi (ayni URL kac gonderide):', dict(Counter(r['video_url_paylasan'] for r in satir)))
    print('AG ALANLARI', dict(Counter((r['platform'], r['ag_alanlari']) for r in satir)))
    for d in sorted(gun)[:3] + ['...'] + sorted(gun)[-2:] if len(gun) > 5 else sorted(gun):
        if d == '...':
            print('  ...'); continue
        print(f"  {d}: " + ', '.join(f"{r['platform']} {r['id']} {r['cift']} {r['saat'][11:16]} {r['durum']}" for r in gun[d]))
    print('ORNEK GONDERI anahtarlari:', {k: sorted(v.keys()) for k, v in ornek.items()})


if __name__ == '__main__':
    main()
