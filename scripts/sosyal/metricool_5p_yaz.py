#!/usr/bin/env python3
"""5 platform: TEK GUN canli zamanlama (Serdar karari 12 Eki 2026 gece denemesi: GEMINI_LEO).
- PLAN_5_PLATFORM.csv'den --gun satirlari (7 satir) alinir; saatler --kar / --th / --vid ile verilir (Europe/Istanbul, acik).
- Karusel saati simdi+10 dk'ya yetismezse karusel ve Threads 30'ar dk kaydirilir; --sinir'i (01:00) gecerse DUR.
- Video Metricool S3 (planner) akisiyla yuklenir, convertedFileUrl kullanilir (metricool_s3_test.py ile dogrulandi).
- Ayni ag + ayni metin zaten varsa tekrar yazilmaz (ZATEN_VAR). POST yeniden denenmez (cift gonderi olmasin).
- Yazimdan sonra liste ucundan geri okunur: metin, medya, saat, ag, ag alanlari karsilastirilir -> DOGRULAMA.json.
Kullanim: metricool_5p_yaz.py --token-dosya T --plan PLAN.csv --gun 1 --video V.mp4 --kar 2026-10-12T23:00
          --th 2026-10-12T23:15 --vid 2026-10-13T03:00 --sinir 2026-10-13T01:00 --mod kuru|yaz --cikti DIR"""
import argparse, csv, importlib.util, json, os, sys
from datetime import datetime, timedelta

D = os.path.dirname(__file__)


def yukle_mod(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(D, dosya))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


mpb = yukle_mod('mpb', 'metricool_pin_baslik.py')
s3 = yukle_mod('s3', 'metricool_s3_test.py')
TZ = 'Europe/Istanbul'


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def video_yukle(mc, yol):
    """S3 planner yuklemesi; donus (url, rapor). Presigned URL'ler maskelenir, yazilmaz."""
    veri = open(yol, 'rb').read()
    n = len(veri)
    parca = [(0, n)] if n < 5 * 1024 * 1024 else [(s, min(n, s + s3.PARCA)) for s in range(0, n, s3.PARCA)]
    istek = {'resourceType': 'planner', 'contentType': 'video/mp4', 'fileExtension': 'mp4',
             'parts': [{'size': e - s, 'startByte': s, 'endByte': e, 'hash': s3.b64sha(veri[s:e])} for s, e in parca]}
    y = mpb.veri(mc.istek('PUT', '/v2/media/s3/upload-transactions', govde=istek))
    for u in ([y.get('presignedUrl')] if y.get('presignedUrl') else [p.get('presignedUrl') for p in y.get('parts') or []]):
        print(f'::add-mask::{u}', flush=True)
    if y.get('presignedUrl'):
        st, _ = s3.put_parca(y['presignedUrl'], veri, istek['parts'][0]['hash'], True)
        if st >= 400:
            st, _ = s3.put_parca(y['presignedUrl'], veri, istek['parts'][0]['hash'], False)
        if st >= 400:
            sys.exit(f'DUR: video PUT {st}')
        tamam = {'simple': {'fileUrl': y.get('fileUrl')}}
    else:
        et = []
        for p in sorted(y.get('parts') or [], key=lambda p: p['partNumber']):
            b = veri[p['startByte']:p['endByte']]
            # presigned URL sha256 basligini imzaliyor (s3 testinde basliksiz 403): once baslikli
            st, e = s3.put_parca(p['presignedUrl'], b, s3.b64sha(b), True)
            if st >= 400:
                st, e = s3.put_parca(p['presignedUrl'], b, s3.b64sha(b), False)
            if st >= 400:
                sys.exit(f"DUR: video parca {p['partNumber']} PUT {st}")
            et.append({'partNumber': p['partNumber'], 'etag': e})
        tamam = {'multipart': {'uploadId': y.get('uploadId'), 'key': y.get('key'), 'parts': et}}
    c = mpb.veri(mc.istek('PATCH', '/v2/media/s3/upload-transactions', govde=tamam))
    url = c.get('convertedFileUrl') or c.get('fileUrl')
    import subprocess
    o = subprocess.run(['curl', '-s', '-o', '/dev/null', '-m', '120', '-w', '%{http_code}|%{content_type}|%{size_download}', url],
                       capture_output=True, text=True).stdout
    if not o.startswith('200'):
        sys.exit(f'DUR: video URL prob {o} {url}')
    return url, {'boyut': n, 'url': url, 'prob': o}


def liste(mc, bas, bit):
    return mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': bas.strftime('%Y-%m-%dT%H:%M:%S'),
                                                             'end': bit.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})) or []


def ag(p):
    return [(x.get('network') or '').lower() for x in p.get('providers') or []]


def govde(r, saat, video_url):
    ek = json.loads(r['ek_alanlar'] or '{}')
    medya = [video_url] if r['medya_url'].startswith('VIDEO:') else r['medya_url'].split(' | ')
    alt = [x for x in r['alt_metinler'].split(' | ') if x] if r['alt_metinler'] else []
    metin = r['metin']
    if r['platform'] == 'threads' and ek.get('konu_etiketi'):
        # Metricool threadsData'da konu alani yok: Threads metindeki ilk hashtag'i konu etiketi yapar
        etiket = '#' + ''.join(w[:1].upper() + w[1:] for w in ek['konu_etiketi'].split())
        if etiket.lower() not in metin.lower():
            metin = f'{metin} {etiket}'
    g = {'publicationDate': {'dateTime': saat.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ},
         'text': metin, 'providers': [{'network': r['platform']}], 'media': medya, 'autoPublish': True,
         'draft': False, 'shortener': False, 'saveExternalMediaFiles': False}
    if alt:
        g['mediaAltText'] = alt
    for k, v in ek.items():
        if k.endswith('Data'):
            g[k] = v
    return g


def karsilastir(g, p):
    f = []
    if p.get('text') != g['text']:
        f.append(f"metin: {str(p.get('text'))[:80]!r}")
    if ag(p) != [g['providers'][0]['network']]:
        f.append(f'ag: {ag(p)}')
    pd = p.get('publicationDate') or {}
    if (pd.get('dateTime') or '')[:16] != g['publicationDate']['dateTime'][:16]:
        f.append(f"saat: {pd.get('dateTime')} {pd.get('timezone')}")
    m = p.get('media') or []
    if len(m) != len(g['media']):
        f.append(f'medya sayisi {len(m)} != {len(g["media"])}')
    elif m != g['media']:
        f.append('medya URL farkli (Metricool kopyalamis olabilir): ' + ' | '.join(x[:90] for x in m))
    if g.get('mediaAltText') and p.get('mediaAltText') != g['mediaAltText']:
        f.append(f"alt metin: {str(p.get('mediaAltText'))[:80]!r}")
    for k, v in g.items():
        if k.endswith('Data'):
            o = p.get(k) or {}
            for a, b in v.items():
                if o.get(a) != b:
                    f.append(f'{k}.{a}: gonderilen {b!r}, okunan {o.get(a)!r}')
    return f


def main():
    ap = argparse.ArgumentParser()
    for k in ('token-dosya', 'plan', 'video', 'kar', 'th', 'vid', 'sinir', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--gun', type=int, default=1)
    ap.add_argument('--mod', choices=['kuru', 'yaz'], default='kuru')
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    satir = [r for r in csv.DictReader(open(a.plan, encoding='utf-8')) if int(r['gun']) == a.gun]
    if len(satir) != 7 or len({r['cift'] for r in satir}) != 1:
        sys.exit(f'DUR: gun {a.gun} satir {len(satir)}')
    cift = satir[0]['cift']
    kar, th, vid, sinir = (datetime.fromisoformat(x) for x in (a.kar, a.th, a.vid, a.sinir))
    kay = timedelta(0)
    while kar + kay < simdi_ist() + timedelta(minutes=10):
        kay += timedelta(minutes=30)
    if kar + kay > sinir:
        sys.exit(f'DUR: karusel saati {kar + kay} sinir {sinir} gecti; zamanlama yapilmadi')
    saat = {'20:00': kar + kay, '21:00': th + kay, '03:00': vid}
    print(f'CIFT {cift}; karusel {saat["20:00"]:%d.%m %H:%M}, threads {saat["21:00"]:%d.%m %H:%M}, video {vid:%d.%m %H:%M} '
          f'({TZ}); kaydirma {int(kay.total_seconds() // 60)} dk; simdi {simdi_ist():%H:%M}', flush=True)
    mc = mpb.MC(json.load(open(a.token_dosya)))
    rapor = {'cift': cift, 'kaydirma_dk': int(kay.total_seconds() // 60), 'mod': a.mod, 'gonderi': []}
    if a.mod == 'yaz':
        vurl, rapor['video'] = video_yukle(mc, a.video)
        print(f"VIDEO {rapor['video']}", flush=True)
    else:
        vurl = 'https://static.metricool.com/video/KURU.mp4'
    g = [(r, govde(r, saat[r['tarih_saat'][11:16]] if r['tarih_saat'][11:16] in saat else None, vurl)) for r in satir]
    pencere = (min(saat.values()) - timedelta(hours=2), max(saat.values()) + timedelta(hours=2))
    var = liste(mc, *pencere)
    for r, b in g:
        es = [p for p in var if ag(p) == [r['platform']] and p.get('text') == b['text']]
        if es:
            durum, pid = 'ZATEN_VAR', es[0].get('id')
        elif a.mod == 'kuru':
            durum, pid = 'KURU', ''
        else:
            y = mpb.veri(mc.istek('POST', '/v2/scheduler/posts', govde=b))
            durum, pid = 'YAZILDI', (y or {}).get('id') if isinstance(y, dict) else ''
        rapor['gonderi'].append({'platform': r['platform'], 'tur': r['tur'], 'saat': b['publicationDate']['dateTime'],
                                 'id': pid, 'durum': durum, 'govde': b})
        print(f"{durum} {r['platform']} {r['tur']} {b['publicationDate']['dateTime']} id={pid}", flush=True)
    # geri okuma
    hata = 0
    if a.mod == 'yaz':
        oku = liste(mc, *pencere)
        for x in rapor['gonderi']:
            b = x['govde']
            p = next((p for p in oku if x['id'] and p.get('id') == x['id']), None) or \
                next((p for p in oku if ag(p) == [x['platform']] and p.get('text') == b['text']), None)
            if p is None:
                x['dogrulama'] = ['GERI OKUNAMADI']
            else:
                x['okunan'] = p
                x['dogrulama'] = karsilastir(b, p)
            sert = [f for f in x['dogrulama'] if not f.startswith('medya URL farkli')]
            hata += bool(sert)
            print(f"DOGRULAMA {x['platform']} {x['tur']} {x['saat']}: " + ('PASS' if not sert else 'FAIL ' + '; '.join(sert))
                  + ''.join(f' [not: {f}]' for f in x['dogrulama'] if f.startswith('medya URL farkli')), flush=True)
    json.dump(rapor, open(os.path.join(a.cikti, 'DOGRULAMA.json'), 'w'), ensure_ascii=False, indent=1)
    print('SONUC ' + ('PASS' if not hata else f'FAIL {hata}'), flush=True)
    sys.exit(1 if hata else 0)


if __name__ == '__main__':
    main()
