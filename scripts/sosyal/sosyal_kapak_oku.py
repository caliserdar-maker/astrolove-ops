#!/usr/bin/env python3
"""Sosyal video kapagi teshisi (SALT OKUMA, Serdar onayi 15 Eki 2026).

Her platformda (instagram, facebook, tiktok, youtube, threads) son yayinlanan VIDEO gonderileri (platform basina --adet)
icin platformun gosterdigi kapak/onizleme gorseli indirilir ve olculur. Metricool'a ve platformlara YAZMA YOK:
yalniz GET (Metricool /v2/scheduler/posts + /v2/analytics/*, herkese acik sayfa og:image, TikTok oEmbed, i.ytimg.com).

Kapak kaynaklari (hepsi denenir, her biri ayri olculur; ilk basarili olan 'ana'):
  instagram  Metricool analytics reels/posts imageUrl -> herkese acik sayfa og:image
  facebook   Metricool analytics reels/posts gorsel alani -> og:image
  tiktok     Metricool analytics posts/tiktok gorsel alani -> TikTok oEmbed thumbnail_url -> og:image
  youtube    i.ytimg.com oar2 / hq720 / hqdefault
  threads    Metricool analytics posts/threads gorsel alani -> og:image
Olcum: gri parlaklik ortalamasi; bizim kapak (videoThumbnailUrl), videonun ilk karesi (0 sn) ve 8. sn karesiyle
ortalama mutlak fark (90x160 gri, yatay gorselde orta 9:16 bant). Fark < 12 = benzer (yt-kapak-oku ile ayni esik).
Okunamayan kaynak 'okunamadi' + sebep olarak yazilir; tahmin yazilmaz.
Kullanim: sosyal_kapak_oku.py --token T.json --bas 2026-10-12T00:00:00 --cikti _out --is _w [--adet 2]"""
import argparse, csv, html, importlib.util, io, json, os, re, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta

import numpy as np
from PIL import Image

AGLAR = ('instagram', 'facebook', 'tiktok', 'youtube', 'threads')
TZ = 'Europe/Istanbul'
ESIK = 12          # ortalama mutlak gri fark; altinda "benzer"
SIYAH_MUTLAK = 3   # parlaklik ortalamasi; altinda referanstan bagimsiz "siyah" (ilk kare 0.0)
KARELER = [0, 0.04, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
BURCLAR = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius',
           'capricorn', 'aquarius', 'pisces')
UA_TARAYICI = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
               'Chrome/126.0 Safari/537.36')
UA_ONIZLEME = 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
ANALIZ = {'instagram': ['/v2/analytics/reels/instagram', '/v2/analytics/posts/instagram'],
          'facebook': ['/v2/analytics/reels/facebook', '/v2/analytics/posts/facebook'],
          'tiktok': ['/v2/analytics/posts/tiktok'],
          'threads': ['/v2/analytics/posts/threads']}
GORSEL_ANAHTAR = re.compile(r'image|thumb|picture|cover|preview|poster|media_?url', re.I)


def kisa(url):
    """URL'yi sorgu dizesi olmadan yaz (imzali CDN parametreleri dosyaya/loga girmesin)."""
    return (url or '').split('?')[0][:160]


# ---------- Metricool (yalniz GET) ----------
def mc_yukle():
    sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                    'metricool_pin_baslik.py'))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def ham_get(mc, mpb, yol, params):
    """Ham GET: (http kodu, content-type, govde). CSV donen analiz uclari icin (MC.istek yalniz JSON cozer)."""
    q = dict(params or {}, userId=mc.u, blogId=mc.b)
    url = f'{mpb.API}{yol}?{urllib.parse.urlencode(q)}'
    for deneme in range(3):
        bekle = mpb.BEKLE - (time.time() - mc.son)
        if bekle > 0:
            time.sleep(bekle)
        r = urllib.request.Request(url, method='GET', headers={'X-Mc-Auth': mc.t, 'Accept': 'application/json, text/csv'})
        try:
            with urllib.request.urlopen(r, timeout=60) as y:
                mc.son = time.time()
                return y.status, y.headers.get('Content-Type', ''), y.read()
        except urllib.error.HTTPError as e:
            mc.son = time.time()
            if e.code in (429, 502, 503, 504) and deneme < 2:
                time.sleep(int(e.headers.get('Retry-After') or 15) if e.code == 429 else 10)
                continue
            return e.code, e.headers.get('Content-Type', ''), e.read()[:300].replace(mc.t.encode(), b'***')
        except Exception as e:  # zaman asimi vb.
            return 0, '', str(e)[:200].encode()
    return 0, '', b'yeniden deneme bitti'


def kayitlar(govde, ct):
    """JSON (data listesi) ya da CSV govdesinden kayit listesi."""
    metin = govde.decode('utf-8-sig', 'replace')
    try:
        j = json.loads(metin)
        j = j.get('data', j) if isinstance(j, dict) else j
        return j if isinstance(j, list) else [j], 'json'
    except ValueError:
        pass
    if not metin.strip():
        return [], 'bos'
    try:
        lehce = csv.Sniffer().sniff(metin[:4000], delimiters=',;\t')
    except csv.Error:
        lehce = csv.excel
    return list(csv.DictReader(io.StringIO(metin), dialect=lehce)), 'csv'


def duzles(x, on=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from duzles(v, f'{on}.{k}' if on else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from duzles(v, f'{on}[{i}]')
    else:
        yield on, x


def gorsel_alanlari(kayit):
    return [(k, v.strip()) for k, v in duzles(kayit)
            if isinstance(v, str) and v.strip().startswith('http') and GORSEL_ANAHTAR.search(k.split('.')[-1])]


def kimlikler(link):
    """Herkese acik linkten eslestirme parcalari (yol bolumleri, >= 6 karakter)."""
    p = urllib.parse.urlparse(link or '')
    parca = [x for x in re.split(r'[/?=&]', p.path + '?' + p.query) if len(x) >= 6]
    # hesap adi (@astroloveart) her kayitta gecer -> kimlik degil (15 Eki: TikTok yanlis eslesme)
    return [x for x in parca if not x.startswith('@')
            and x.lower() not in ('reel', 'reels', 'video', 'videos', 'shorts', 'watch', 'permalink.php', 'astroloveart')]


def eslestir(recs, post_zaman, link):
    ids = kimlikler(link)
    for r in recs:
        d = json.dumps(r, ensure_ascii=False, default=str)
        if any(i in d for i in ids):
            return r, 'kimlik'
    en, fark = None, None
    for r in recs:
        for m in re.findall(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}', json.dumps(r, default=str)):
            try:
                f = abs((datetime.fromisoformat(m.replace(' ', 'T')) - post_zaman).total_seconds())
            except ValueError:
                continue
            if f <= 30 * 60 and (fark is None or f < fark):
                en, fark = r, f
    return (en, f'zaman ({int(fark // 60)} dk)') if en is not None else (None, None)


# ---------- herkese acik okuma ----------
def indir(url, yol, ua=UA_TARAYICI):
    o = subprocess.run(['curl', '-sL', '-m', '90', '-A', ua, '-o', yol, '-w', '%{http_code}|%{content_type}', url],
                       capture_output=True, text=True).stdout
    return o


def gorsel_mi(yol):
    try:
        with Image.open(yol) as im:
            im.load()
            return list(im.size)
    except Exception:
        return None


OG = [re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|og:image:url|twitter:image)["\'][^>]*content=["\']([^"\']+)', re.I),
      re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|og:image:url|twitter:image)["\']', re.I)]


def og_gorsel(link, isd):
    """Herkese acik sayfanin og:image'i: (url, sebep)."""
    sebep = []
    for ad, ua in (('tarayici', UA_TARAYICI), ('onizleme', UA_ONIZLEME)):
        yol = os.path.join(isd, f'sayfa_{ad}.html')
        o = indir(link, yol, ua)
        if not o.startswith('200') or not os.path.exists(yol):
            sebep.append(f'{ad}: http {o.split("|")[0]}'); continue
        metin = open(yol, encoding='utf-8', errors='replace').read()
        for d in OG:
            m = d.search(metin)
            if m:
                return html.unescape(m.group(1)), None
        sebep.append(f'{ad}: og:image yok ({"giris sayfasi" if re.search(r"login|log in|sign up", metin[:20000], re.I) else "etiket yok"})')
    return None, '; '.join(sebep)


def tiktok_oembed(link, isd):
    yol = os.path.join(isd, 'oembed.json')
    o = indir('https://www.tiktok.com/oembed?url=' + urllib.parse.quote(link, safe=''), yol)
    if not o.startswith('200'):
        return None, f'oembed http {o.split("|")[0]}'
    try:
        j = json.load(open(yol))
    except ValueError:
        return None, 'oembed JSON degil'
    return (j.get('thumbnail_url'), None) if j.get('thumbnail_url') else (None, 'oembed thumbnail_url yok')


# ---------- olcum ----------
def g(yol, w=90, h=160):
    im = Image.open(yol).convert('L')
    W, H = im.size
    if W / H > 0.6:   # 9:16'dan genis (kare / yatay onizleme): orta dikey 9:16 bant
        bw = int(H * 9 / 16)
        im = im.crop(((W - bw) // 2, 0, (W + bw) // 2, H))
    return np.asarray(im.resize((w, h)), np.float32)


def fark(a, b):
    return round(float(np.abs(a - b).mean()), 1)


def sinifla(d):
    """En yakin referans kazanir (bizim kapak da koyu: 15 Eki olcumu parlaklik 10-15; mutlak parlaklik esigi yanilir).
    siyah = en yakin referans videonun ilk karesi (0 sn, parlaklik 0) ya da gorsel neredeyse tamamen siyah."""
    if d['parlaklik'] < SIYAH_MUTLAK:
        return 'siyah'
    aday = {}
    if 'fark_bizim_kapak' in d:
        aday['bizim kapak'] = d['fark_bizim_kapak']
    if 'en_yakin_kare_sn' in d:
        aday['siyah' if d['en_yakin_kare_sn'] <= 0.04 else f"videodan kare (~{d['en_yakin_kare_sn']} sn)"] = d['en_yakin_kare_fark']
    if not aday or min(aday.values()) >= ESIK:
        return 'belirsiz (hicbir referansa benzemiyor)'
    return min(aday, key=aday.get)


def cift_bul(p):
    metin = ' '.join(str(x) for x in (p.get('text'), (p.get('youtubeData') or {}).get('title'), p.get('videoThumbnailUrl'),
                                      ' '.join(m if isinstance(m, str) else json.dumps(m) for m in p.get('media') or [])))
    bul = []
    for m in re.finditer(r'[a-z]+', metin.lower()):
        if m.group(0) in BURCLAR and m.group(0) not in bul:
            bul.append(m.group(0))
    return bul[:2] if len(bul) >= 2 else None


def video_mu(p):
    if p.get('videoThumbnailUrl'):
        return True
    for m in p.get('media') or []:
        u = m if isinstance(m, str) else json.dumps(m)
        if re.search(r'\.(mp4|mov|m4v)(\?|$)|video', u, re.I):
            return True
    return False


def medya_url(p):
    for m in p.get('media') or []:
        u = m if isinstance(m, str) else (m.get('url') or m.get('mediaUrl') or '')
        if u:
            return u
    return ''


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--token', required=True)
    a.add_argument('--bas', required=True)
    a.add_argument('--cikti', required=True)
    a.add_argument('--is', dest='isdir', required=True)
    a.add_argument('--adet', type=int, default=2)
    a.add_argument('--kapak-drive', default=os.environ.get('KD', ''))
    a.add_argument('--video-drive', default=os.environ.get('V', ''))
    o = a.parse_args()
    os.makedirs(o.cikti, exist_ok=True)
    os.makedirs(os.path.join(o.cikti, 'gorsel'), exist_ok=True)
    mpb = mc_yukle()
    mc = mpb.MC(json.load(open(o.token)))
    simdi = datetime.utcnow() + timedelta(hours=3)
    bas = datetime.fromisoformat(o.bas)

    # 1) zamanlayici: yayinlanan video gonderileri
    ps, t = {}, bas
    while t < simdi:
        e = min(simdi, t + timedelta(days=7))
        for p in mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': t.strftime('%Y-%m-%dT%H:%M:%S'),
                                                                  'end': e.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})) or []:
            ps[p.get('id')] = p
        t = e
    secim = {}
    for ag in AGLAR:
        adaylar = []
        for p in ps.values():
            for x in p.get('providers') or []:
                if (x.get('network') or '').lower() == ag and x.get('publicUrl') and video_mu(p):
                    adaylar.append((p, x))
        adaylar.sort(key=lambda px: (px[0].get('publicationDate') or {}).get('dateTime', ''), reverse=True)
        secim[ag] = adaylar[:o.adet]
        print(f'GONDERI {ag}: yayinlanan video {len(adaylar)}, secilen {len(secim[ag])}', flush=True)

    # 2) analiz uclari (her biri 1 GET)
    analiz, alan_ozet = {}, {}
    for ag, yollar in ANALIZ.items():
        for yol in yollar:
            kod, ct, govde = ham_get(mc, mpb, yol, {'from': o.bas, 'to': simdi.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})
            oz = {'http': kod, 'tur': ct.split(';')[0]}
            if kod == 200:
                recs, bic = kayitlar(govde, ct)
                analiz[yol] = recs
                oz.update(bicim=bic, kayit=len(recs), anahtarlar=sorted({k for r in recs[:5] for k, _ in duzles(r)})[:80],
                          gorsel_anahtarlar=sorted({k for r in recs for k, _ in gorsel_alanlari(r)}))
            else:
                oz['hata'] = govde[:200].decode('utf-8', 'replace')
            alan_ozet[yol] = oz
            print(f"ANALIZ {yol}: http {kod} {oz.get('bicim', '')} kayit {oz.get('kayit', '-')} gorsel alan {oz.get('gorsel_anahtarlar', '-')}", flush=True)
    json.dump(alan_ozet, open(os.path.join(o.cikti, 'ANALIZ_ALANLARI.json'), 'w'), ensure_ascii=False, indent=1)

    # 3) her gonderi: kaynaklar, indirme, olcum
    sonuc = []
    for ag in AGLAR:
        if not secim[ag]:
            sonuc.append({'platform': ag, 'gonderi': '-', 'ana_sonuc': 'okunamadi',
                          'sebep': f'{o.bas} sonrasi yayinlanmis (publicUrl dolu) video gonderisi yok'})
            continue
        for p, x in secim[ag]:
            pid = str(p.get('id'))
            isd = os.path.join(o.isdir, f'{ag}_{pid}')
            os.makedirs(isd, exist_ok=True)
            pzaman = datetime.fromisoformat((p.get('publicationDate') or {}).get('dateTime'))
            cift = cift_bul(p)
            d = {'platform': ag, 'gonderi': pid, 'saat': pzaman.strftime('%Y-%m-%d %H:%M'), 'link': x.get('publicUrl'),
                 'durum': x.get('status'), 'cift': '_'.join(c.upper() for c in cift) if cift else '?',
                 'bizim_kapak_gonderildi': bool(p.get('videoThumbnailUrl')), 'kaynaklar': []}
            # referanslar: bizim kapak, video kareleri
            ref = {}
            kp = os.path.join(isd, 'bizim_kapak.jpg')
            if p.get('videoThumbnailUrl'):
                indir(p['videoThumbnailUrl'], kp)
            if not gorsel_mi(kp) and cift and o.kapak_drive:
                subprocess.run(['rclone', 'copyto', f'{o.kapak_drive}/{cift[0]}-and-{cift[1]}-astroloveart-kapak.jpg', kp, '-q'])
                d['bizim_kapak_kaynak'] = 'Drive KAPAK (videoThumbnailUrl indirilemedi)' if p.get('videoThumbnailUrl') else 'Drive KAPAK'
            if gorsel_mi(kp):
                ref['kapak'] = g(kp)
                d.setdefault('bizim_kapak_kaynak', 'videoThumbnailUrl')
                d['bizim_kapak_parlaklik'] = round(float(ref['kapak'].mean()), 1)
            else:
                d['bizim_kapak_kaynak'] = 'okunamadi'
            mp4 = os.path.join(isd, 'v.mp4')
            mu = medya_url(p)
            if mu:
                indir(mu, mp4)
            if (not os.path.exists(mp4) or os.path.getsize(mp4) < 10000) and cift and o.video_drive:
                subprocess.run(['rclone', 'copyto', f'{o.video_drive}/{cift[0]}-and-{cift[1]}-astroloveart-reel.mp4', mp4, '-q'])
                d['video_kaynak'] = 'Drive FINAL'
            kareler = {}
            if os.path.exists(mp4) and os.path.getsize(mp4) >= 10000:
                d.setdefault('video_kaynak', 'Metricool medya')
                for ts in KARELER:
                    f = os.path.join(isd, f'kare_{ts}.jpg')
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(ts), '-i', mp4, '-frames:v', '1', f])
                    if gorsel_mi(f):
                        kareler[ts] = g(f)
                if 0 in kareler:
                    d['ilk_kare_parlaklik'] = round(float(kareler[0].mean()), 1)
                if 8 in kareler:
                    d['kare8_parlaklik'] = round(float(kareler[8].mean()), 1)
            else:
                d['video_kaynak'] = 'okunamadi'

            # platform kapak adaylari: (kaynak adi, url | None, sebep)
            aday = []
            if ag == 'youtube':
                vid = (re.search(r'(?:shorts/|v=|youtu\.be/)([\w-]{6,})', d['link'] or '') or [None, None])[1]
                if vid:
                    for ad in ('oar2', 'hq720', 'hqdefault'):
                        aday.append((f'ytimg {ad}', f'https://i.ytimg.com/vi/{vid}/{ad}.jpg', None))
                else:
                    aday.append(('ytimg', None, 'linkten video kimligi cikmadi'))
            for yol in ANALIZ.get(ag, []):
                if yol not in analiz:
                    aday.append((f'metricool {yol}', None, f"analiz ucu http {alan_ozet[yol]['http']}"))
                    continue
                r, nasil = eslestir(analiz[yol], pzaman, d['link'])
                if r is None:
                    aday.append((f'metricool {yol}', None, f'{len(analiz[yol])} kayit, bu gonderiyle eslesen yok'))
                    continue
                ga = gorsel_alanlari(r)
                if not ga:
                    aday.append((f'metricool {yol}', None, f'eslesti ({nasil}) ama gorsel alani yok'))
                for k, v in ga:
                    aday.append((f'metricool {yol} [{k}] ({nasil})', v, None))
            if ag == 'tiktok':
                u, s = tiktok_oembed(d['link'], isd)
                aday.append(('tiktok oembed thumbnail_url', u, s))
            if ag != 'youtube':
                u, s = og_gorsel(d['link'], isd)
                aday.append(('herkese acik sayfa og:image', u, s))

            for i, (kaynak, url, sebep) in enumerate(aday):
                k = {'kaynak': kaynak, 'url': kisa(url)}
                if not url:
                    k.update(durum='okunamadi', sebep=sebep); d['kaynaklar'].append(k); continue
                yol = os.path.join(isd, f'platform_{i}.img')
                h = indir(url, yol)
                boyut = gorsel_mi(yol) if h.startswith('200') else None
                if not boyut:
                    k.update(durum='okunamadi', sebep=f'indirme http {h.split("|")[0]} {h.split("|")[-1]}'); d['kaynaklar'].append(k); continue
                A = g(yol)
                k.update(durum='okundu', boyut=boyut, parlaklik=round(float(A.mean()), 1))
                if 'kapak' in ref:
                    k['fark_bizim_kapak'] = fark(A, ref['kapak'])
                if 0 in kareler:
                    k['fark_ilk_kare'] = fark(A, kareler[0])
                if 8 in kareler:
                    k['fark_8sn'] = fark(A, kareler[8])
                if kareler:
                    fs = {ts: fark(A, K) for ts, K in kareler.items()}
                    ts = min(fs, key=fs.get)
                    k['en_yakin_kare_sn'], k['en_yakin_kare_fark'] = ts, fs[ts]
                k['sonuc'] = sinifla(k)
                ad = f"{ag}_{d['cift']}_{pid}_platform_{i}.jpg"
                with Image.open(yol) as im:
                    im = im.convert('RGB'); im.thumbnail((360, 640)); im.save(os.path.join(o.cikti, 'gorsel', ad), quality=88)
                k['dosya'] = f'gorsel/{ad}'
                d['kaynaklar'].append(k)
            # referans kopyalari
            for ad, f in (('bizim_kapak', kp), ('ilk_kare', os.path.join(isd, 'kare_0.jpg')), ('kare_8sn', os.path.join(isd, 'kare_8.jpg'))):
                if gorsel_mi(f):
                    with Image.open(f) as im:
                        im = im.convert('RGB'); im.thumbnail((360, 640)); im.save(os.path.join(o.cikti, 'gorsel', f"{ag}_{d['cift']}_{pid}_{ad}.jpg"), quality=88)
            ok = [k for k in d['kaynaklar'] if k['durum'] == 'okundu']
            if ok:
                d['ana_kaynak'], d['ana_sonuc'] = ok[0]['kaynak'], ok[0]['sonuc']
            else:
                d['ana_sonuc'] = 'okunamadi'
                d['sebep'] = ' | '.join(f"{k['kaynak']}: {k['sebep']}" for k in d['kaynaklar']) or 'kaynak yok'
            sonuc.append(d)
            print('KAPAK', json.dumps({k: v for k, v in d.items() if k != 'kaynaklar'}, ensure_ascii=False), flush=True)
            for k in d['kaynaklar']:
                print('   ', json.dumps(k, ensure_ascii=False), flush=True)

    json.dump({'okuma': simdi.strftime('%Y-%m-%dT%H:%M'), 'esik_benzer': ESIK, 'esik_siyah_mutlak': SIYAH_MUTLAK, 'gonderiler': sonuc},
              open(os.path.join(o.cikti, 'SOSYAL_KAPAK_OLCUM.json'), 'w'), ensure_ascii=False, indent=1)
    alanlar = ['platform', 'gonderi', 'saat', 'cift', 'link', 'gosterilen_kapak', 'kaynak', 'parlaklik', 'fark_bizim_kapak',
               'fark_ilk_kare', 'fark_8sn', 'en_yakin_kare_sn', 'en_yakin_kare_fark', 'bizim_kapak_parlaklik',
               'ilk_kare_parlaklik', 'kare8_parlaklik', 'sebep', 'dosya']
    with open(os.path.join(o.cikti, 'SOSYAL_KAPAK_TABLO.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, alanlar, extrasaction='ignore')
        w.writeheader()
        print('\nTABLO platform | gonderi | gosterilen kapak | olcum')
        for d in sonuc:
            ks = [k for k in d.get('kaynaklar') or [] if k['durum'] == 'okundu'] or [None]
            for k in ks:
                satir = dict(d, gosterilen_kapak=k['sonuc'] if k else 'okunamadi', **({kk: k[kk] for kk in k if kk not in ('sonuc', 'durum')} if k else {}))
                w.writerow(satir)
                olc = (f"parlaklik {k['parlaklik']}, fark kapak {k.get('fark_bizim_kapak', '-')}, ilk kare {k.get('fark_ilk_kare', '-')}, "
                       f"8 sn {k.get('fark_8sn', '-')}, en yakin {k.get('en_yakin_kare_sn', '-')} sn") if k else d.get('sebep', '')[:300]
                print(f"| {d['platform']} | {d['gonderi']} {d.get('cift', '')} | {satir['gosterilen_kapak']} [{k['kaynak'] if k else '-'}] | {olc} |")


if __name__ == '__main__':
    main()
