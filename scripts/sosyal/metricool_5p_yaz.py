#!/usr/bin/env python3
"""5 platform: TEK GUN canli zamanlama (Serdar karari 12 Eki 2026 gece denemesi: GEMINI_LEO).
- PLAN_5_PLATFORM.csv'den --gun satirlari (7 satir) alinir; saatler --kar / --th / --vid ile verilir (Europe/Istanbul, acik).
- Karusel saati simdi+10 dk'ya yetismezse karusel ve Threads 30'ar dk kaydirilir; --sinir'i (01:00) gecerse DUR.
- Video Metricool S3 (planner) akisiyla yuklenir, convertedFileUrl kullanilir (metricool_s3_test.py ile dogrulandi).
- Ayni ag + ayni metin zaten varsa tekrar yazilmaz (ZATEN_VAR). POST yeniden denenmez (cift gonderi olmasin).
- Yazimdan sonra liste ucundan geri okunur: metin, medya, saat, ag, ag alanlari karsilastirilir -> DOGRULAMA.json.
Kullanim: metricool_5p_yaz.py --token-dosya T --plan PLAN.csv --gun 1 --video V.mp4 --kar 2026-10-12T23:00
          --th 2026-10-12T23:15 --vid 2026-10-13T03:00 --sinir 2026-10-13T01:00 --mod kuru|yaz --cikti DIR"""
import argparse, csv, importlib.util, json, os, sys, time
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


def video_yukle(mc, yol, ctype='video/mp4', uzanti='mp4'):
    """S3 planner yuklemesi (video ya da kapak jpg); donus (url, rapor). Presigned URL'ler maskelenir, yazilmaz."""
    veri = open(yol, 'rb').read()
    n = len(veri)
    parca = [(0, n)] if n < 5 * 1024 * 1024 else [(s, min(n, s + s3.PARCA)) for s in range(0, n, s3.PARCA)]
    istek = {'resourceType': 'planner', 'contentType': ctype, 'fileExtension': uzanti,
             'parts': [{'size': e - s, 'startByte': s, 'endByte': e, 'hash': s3.b64sha(veri[s:e])} for s, e in parca]}
    y = mpb.veri(mc.istek('PUT', '/v2/media/s3/upload-transactions', govde=istek))
    for u in ([y.get('presignedUrl')] if y.get('presignedUrl') else [p.get('presignedUrl') for p in y.get('parts') or []]):
        print(f'::add-mask::{u}', flush=True)
    if y.get('presignedUrl'):
        st, _ = s3.put_parca(y['presignedUrl'], veri, istek['parts'][0]['hash'], True, ctype)
        if st >= 400:
            st, _ = s3.put_parca(y['presignedUrl'], veri, istek['parts'][0]['hash'], False, ctype)
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


def govde(r, saat, video_url, kapak_url=''):
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
    if r['medya_url'].startswith('VIDEO:') and kapak_url:
        g['videoThumbnailUrl'] = kapak_url   # kapak_v1 gorseli (IG Reel, FB Reel, TikTok business, YouTube)
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
    if g.get('videoThumbnailUrl') and not p.get('videoThumbnailUrl'):
        f.append('kapak (videoThumbnailUrl) okunamadi')
    if g.get('mediaAltText') and p.get('mediaAltText') != g['mediaAltText']:
        f.append(f"alt metin: {str(p.get('mediaAltText'))[:80]!r}")
    for k, v in g.items():
        if k.endswith('Data'):
            o = p.get(k) or {}
            for a, b in v.items():
                ok = o.get(a)
                # Metricool normallestirmesi: buyuk/kucuk harf (SHORT->short), false -> alan yok (None)
                if ok == b or (isinstance(b, str) and isinstance(ok, str) and ok.lower() == b.lower()) or (b is False and ok is None):
                    continue
                if True:
                    f.append(f'{k}.{a}: gonderilen {b!r}, okunan {o.get(a)!r}')
    return f


def coklu(a):
    """--gunler 2-78: plan saatleriyle; video + kapak cift basina Metricool S3'e. kuru: POST yok.
    yaz: cift cift; her ciftin 7 gonderisi yazilir, hemen geri okunup dogrulanir; FAIL -> DUR (cikis 3).
    Saati gecmis (simdi+15 dk'dan once) satirlar ATLANIR ve raporlanir."""
    g1, g2 = (int(x) for x in a.gunler.split('-'))
    plan = [r for r in csv.DictReader(open(a.plan, encoding='utf-8')) if g1 <= int(r['gun']) <= g2]
    hata, out = [], []
    sinir = simdi_ist() + timedelta(minutes=15)
    atla = [r for r in plan if datetime.fromisoformat(r['tarih_saat']) < sinir]
    plan = [r for r in plan if r not in atla]
    for r in atla:
        out.append({'gun': r['gun'], 'cift': r['cift'], 'platform': r['platform'], 'tur': r['tur'], 'saat': r['tarih_saat'],
                    'kapak': '', 'durum': 'ATLANDI_SAAT_GECMIS', 'id': ''})
    if 'GEMINI_LEO' in {r['cift'] for r in plan}:
        hata.append('GEMINI_LEO planda (Metricool da zaten var)')
    vdir, kdir = a.video_dir, a.kapak_dir
    mc = mpb.MC(json.load(open(a.token_dosya)))
    yol = os.path.join(a.cikti, f'KURU_{a.gunler}.json' if a.mod == 'kuru' else f'YAZIM_{a.gunler}.json')

    def kaydet():
        json.dump(out, open(yol, 'w'), ensure_ascii=False, indent=1)

    def aralik(rs):
        t = [datetime.fromisoformat(r['tarih_saat']) for r in rs]
        return min(t) - timedelta(hours=1), max(t) + timedelta(hours=1)
    var = []
    if plan:
        bas, son = aralik(plan)
        t = bas
        while t < son:   # liste ucu 7 gunluk parcalarla (mevcut gonderi = ZATEN_VAR, tekrar yazilmaz)
            var += liste(mc, t, min(son, t + timedelta(days=7))); t += timedelta(days=7)
    t0 = time.time()
    ciftler = sorted({r['cift'] for r in plan}, key=lambda c: min(r['tarih_saat'] for r in plan if r['cift'] == c))
    for i, c in enumerate(ciftler, 1):
        rs = sorted([r for r in plan if r['cift'] == c], key=lambda r: (r['tarih_saat'], r['platform']))
        vd = next((r['video_dosya'] for r in rs if r['video_dosya']), '')
        kd = next((r.get('kapak_dosya', '') for r in rs if r.get('kapak_dosya')), '')
        for ad, d, kok in (('video', vd, vdir), ('kapak', kd, kdir)):
            if any(r['medya_url'].startswith('VIDEO:') for r in rs) and (
                    not d or (kok and not os.path.exists(os.path.join(kok, d))) or 'YOK' in (rs[0].get(f'{ad}_drive_id') or '') + d):
                hata.append(f'{c} {ad} yok: {d}')
        if hata and a.mod == 'yaz':
            break
        yazilacak = [r for r in rs if not any(ag(p) == [r['platform']] and (p.get('text') or '') == govde(r, datetime.fromisoformat(r['tarih_saat']), '')['text'] for p in var)]
        if a.mod == 'yaz' and any(r['medya_url'].startswith('VIDEO:') for r in yazilacak):
            vurl, _ = video_yukle(mc, os.path.join(vdir, vd))
            kurl, _ = video_yukle(mc, os.path.join(kdir, kd), 'image/jpeg', 'jpg')
        else:
            vurl, kurl = 'https://static.metricool.com/video/KURU.mp4', f'https://static.metricool.com/KURU/{kd}'
        yeni = []
        for r in rs:
            b = govde(r, datetime.fromisoformat(r['tarih_saat']), vurl, kurl)
            if r['medya_url'].startswith('VIDEO:') and not b.get('videoThumbnailUrl'):
                hata.append(f"{c} {r['platform']} kapak alani yok")
            if r not in yazilacak:
                durum, pid = 'ZATEN_VAR', ''
            elif a.mod == 'kuru':
                durum, pid = 'KURU', ''
            else:
                y = mpb.veri(mc.istek('POST', '/v2/scheduler/posts', govde=b))
                durum, pid = 'YAZILDI', str((y or {}).get('id') if isinstance(y, dict) else '')
            x = {'gun': r['gun'], 'cift': c, 'platform': r['platform'], 'tur': r['tur'], 'saat': b['publicationDate']['dateTime'],
                 'kapak': b.get('videoThumbnailUrl', ''), 'durum': durum, 'id': pid, 'govde': b}
            out.append(x)
            if durum == 'YAZILDI':
                yeni.append(x)
        if yeni:   # geri okuma: bu ciftin yazdigi her gonderi
            oku = liste(mc, *aralik(rs))
            for x in yeni:
                b = x.pop('govde')
                p = next((p for p in oku if x['id'] and str(p.get('id')) == x['id']), None) or \
                    next((p for p in oku if ag(p) == [x['platform']] and p.get('text') == b['text']), None)
                f = ['GERI OKUNAMADI'] if p is None else [k for k in karsilastir(b, p) if not k.startswith('medya URL farkli')]
                x['dogrulama'] = f or 'PASS'
                if f:
                    hata.append(f"{c} {x['platform']} {x['tur']} {x['saat']}: {'; '.join(f)}")
        for x in out:
            x.pop('govde', None) if a.mod == 'yaz' else None
        kaydet()
        g = time.time() - t0
        if a.mod == 'yaz' or i % 10 == 0 or i == len(ciftler):
            print(f"[{i}/{len(ciftler)}] {c} {'FAIL' if hata else 'PASS'} yazilan {sum(x['durum'] == 'YAZILDI' for x in out)} | gecen {g:.0f} sn, "
                  f"kalan ~{g / i * (len(ciftler) - i):.0f} sn, %{100 * i / len(ciftler):.0f}", flush=True)
        if hata and a.mod == 'yaz':
            break
    from collections import Counter
    yz = [x for x in out if x['durum'] != 'ATLANDI_SAAT_GECMIS']
    n = Counter((x['platform'], x['tur']) for x in yz)
    tek = Counter((x['platform'], x['tur'], x['cift']) for x in yz)
    if not hata and a.mod == 'kuru' and (len(yz) != len(plan) or any(v != 1 for v in tek.values())):
        hata.append(f'satir {len(yz)} / plan {len(plan)} / tekrar {[k for k, v in tek.items() if v != 1][:3]}')
    if not hata and a.mod == 'yaz' and any(v != 1 for v in tek.values()):
        hata.append(f'tekrar {[k for k, v in tek.items() if v != 1][:3]}')
    kaydet()
    say = Counter(x['durum'] for x in out)
    zs = [x['saat'] for x in yz]
    print(f"{a.mod.upper()} gun {a.gunler}: {len(ciftler)} cift, durum {dict(say)}, kapakli video gonderisi {sum(1 for x in yz if x['kapak'])}, "
          f"ilk {min(zs) if zs else '-'}, son {max(zs) if zs else '-'}; atlanan (saat gecmis) {len(atla)}", flush=True)
    print('SONUC ' + ('PASS' if not hata else 'FAIL: ' + '; '.join(hata[:15])), flush=True)
    sys.exit(0 if not hata else (3 if a.mod == 'yaz' else 1))


def main():
    ap = argparse.ArgumentParser()
    for k in ('token-dosya', 'plan', 'cikti'):
        ap.add_argument('--' + k, required=True)
    for k in ('video', 'kar', 'th', 'vid', 'sinir', 'gunler', 'video-dir', 'kapak-dir', 'kapak'):
        ap.add_argument('--' + k, default='')
    ap.add_argument('--gun', type=int, default=1)
    ap.add_argument('--mod', choices=['kuru', 'yaz'], default='kuru')
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    if a.gunler:
        return coklu(a)
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
