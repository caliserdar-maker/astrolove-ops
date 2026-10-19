#!/usr/bin/env python3
"""K2 (sosyal -> Etsy) link envanteri (19 Eki 2026). SALT OKUMA: Metricool'a ve hicbir platforma YAZMA YOK, yalniz GET.
Uclar (data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json):
  /v2/scheduler/posts (12 Eki - 29 Ara, 1 gunluk parcalar; 1. kosu 5 gunde 100 kayitta kesiliyordu)  text, firstCommentText, pinterestData.pinLink,
      tiktokData.articleLink, smartLinkData.targetUrl, providers[].status/publicUrl
  /v2/settings/brands, /v2/settings/brands/{id}, /admin/simpleProfiles   profil kullanici adlari / profil URL'leri
  /linkinbio/instagram/getbioButtons, /linkinbio/instagram/getbiocatalog  Metricool link-in-bio icerigi (okuma)
  YAZAN GET uclari (setproperty, add-profile, editcatalog*, addcatalog*, delete*) CAGRILMAZ.
URL kontrolu: her benzersiz URL'ye GET, yonlendirmeler elle izlenir (en fazla 10), her adimin kodu yazilir.
Okunamayan deger "erisilemedi"; tahmin yok. Ham yanitlar HAM_*.json, ozet OZET.txt.
Kullanim: k2_link.py TOKEN.json CIKTI_DIR"""
import csv
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
BAS, SON = date(2026, 10, 12), date(2026, 12, 29)
AGLAR = ('pinterest', 'instagram', 'facebook', 'threads', 'tiktok', 'youtube')
YOK = 'erisilemedi'
URL_RE = re.compile(r'(?:https?://|(?<![\w/.])(?:www\.)?(?:etsy\.com|etsy\.me)/)[^\s<>"\')\]]+', re.I)
CTA_RE = re.compile(r'link in bio|in bio|first comment|search .{0,40}etsy|on etsy|find us|shop[: ]|etsy|link below|tap the link', re.I)
SHARE_PARAM = re.compile(r'^(share_time|utm_\w+|click_key|click_sum|ref|ls|sts|ga_\w+|dd_referrer|bes|epik|frs|logging_key)$', re.I)
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36')
OZET = None


def log(s):
    print(s, flush=True)
    with open(OZET, 'a', encoding='utf-8') as f:
        f.write(s + '\n')


def yaz_csv(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    log(f'CSV {ad}: {len(satirlar)} satir')


def ham(out, ad, veri):
    json.dump(veri, open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def guvenli(mc, ad, yol, params, out):
    try:
        j = mc.istek('GET', yol, params)
    except SystemExit as e:
        log(f'{ad}: HATA {str(e)[:220]}'); ham(out, ad, {'_hata': str(e)[:2000]})
        return None
    ham(out, ad, j)
    return j


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v if isinstance(v, list) else None


def urller(metin):
    out = []
    for u in URL_RE.findall(metin or ''):
        u = u.rstrip('.,;:!?')
        if not u.lower().startswith('http'):
            u = 'https://' + u
        out.append(u)
    return out


def tur(u):
    p = urllib.parse.urlsplit(u)
    h = p.netloc.lower().removeprefix('www.')
    if h == 'etsy.me':
        return 'etsy.me kisa'
    if h.endswith('etsy.com'):
        if re.match(r'/(?:[a-z]{2}(?:-[a-z]{2})?/)?listing/\d+', p.path, re.I):
            return 'ilan'
        if re.match(r'/(?:[a-z]{2}(?:-[a-z]{2})?/)?shop/', p.path, re.I):
            return 'magaza'
        return 'etsy diger'
    return 'etsy disi'


def parametreler(u):
    return sorted({k for k, _ in urllib.parse.parse_qsl(urllib.parse.urlsplit(u).query, keep_blank_values=True)})


def share_save(u):
    """Etsy Share & Save bicimi: etsy.me kisa link veya share_time/utm_* vb. parametre. Hangi isaretin goruldugu yazilir."""
    isaret = [k for k in parametreler(u) if SHARE_PARAM.match(k)]
    if tur(u) == 'etsy.me kisa':
        isaret.insert(0, 'etsy.me')
    return isaret


def cta(metin):
    satir = [s.strip() for s in re.split(r'[\n\r]+|(?<=[.!?])\s+', metin or '') if s.strip()]
    return [s[:120] for s in satir if CTA_RE.search(s)]


class Yonlendirme(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


ACICI = urllib.request.build_opener(Yonlendirme)


def kontrol(u):
    """GET + elle yonlendirme izleme. Donus: (zincir [(kod, url)], son_kod, son_url, hata).
    hata alani 4xx/5xx yanitta engel isaretlerini de tasir: Server basligi, x-datadome / x-dd-b basliklari,
    govdede captcha-delivery / datadome gecisi (1. kosu: 156 URL'nin hepsi Actions'tan 403)."""
    zincir, simdi = [], u
    for _ in range(10):
        r = urllib.request.Request(simdi, method='GET', headers={'User-Agent': UA, 'Accept': 'text/html,*/*',
                                                                 'Accept-Language': 'en-US,en;q=0.9'})
        try:
            with ACICI.open(r, timeout=30) as y:
                y.read(2048)
                zincir.append((y.status, simdi))
                return zincir, y.status, simdi, ''
        except urllib.error.HTTPError as e:
            zincir.append((e.code, simdi))
            yer = e.headers.get('Location') if e.code in (301, 302, 303, 307, 308) else None
            if not yer:
                try:
                    g = e.read(4096).decode('utf-8', 'replace').lower()
                except Exception:
                    g = ''
                isaret = [f"server={e.headers.get('Server', '')}"] + [f'{h}={e.headers.get(h)}' for h in ('x-datadome', 'x-dd-b')
                                                                       if e.headers.get(h)]
                isaret += [m for m in ('captcha-delivery', 'datadome') if m in g]
                return zincir, e.code, simdi, ' '.join(isaret)
            simdi = urllib.parse.urljoin(simdi, yer)
        except Exception as e:
            return zincir, 0, simdi, f'{type(e).__name__}: {str(e)[:120]}'
    return zincir, zincir[-1][0] if zincir else 0, simdi, 'yonlendirme 10 adimi asti'


def main():
    global OZET
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    OZET = os.path.join(out, 'OZET.txt'); open(OZET, 'w').close()
    mc = mpb.MC(json.load(open(tok)))
    okuma = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    log(f'OKUMA ANI (UTC): {okuma}; userId {mc.u}; blogId {mc.b}; donem {BAS} - {SON} ({TZ})')

    # 1) zamanlayici
    ps, t = {}, datetime.combine(BAS, datetime.min.time())
    son = datetime.combine(SON + timedelta(days=1), datetime.min.time())
    while t < son:
        e = min(t + timedelta(days=1), son)
        j = guvenli(mc, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}',
                    'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ}, out)
        ls = liste(j)
        log(f'SCHEDULER {t:%Y-%m-%d}: {len(ls) if ls is not None else "yanit yok"} kayit'
            + ('  UYARI: 100 ve ustu, yanit kesilmis olabilir' if ls and len(ls) >= 100 else ''))
        for p in ls or []:
            ps[str(p.get('id'))] = p
        t = e
    log(f'SCHEDULER toplam benzersiz gonderi: {len(ps)}')

    # 2) gonderi x ag satirlari
    satir, url_kul = [], defaultdict(Counter)
    ozet = defaultdict(lambda: defaultdict(Counter))
    for p in sorted(ps.values(), key=lambda x: (x.get('publicationDate') or {}).get('dateTime') or ''):
        zt = (p.get('publicationDate') or {}).get('dateTime') or ''
        if not zt or not (BAS <= date.fromisoformat(zt[:10]) <= SON):
            continue
        metin, yorum = p.get('text') or '', p.get('firstCommentText') or ''
        alanlar = {'pinterestData.pinLink': (p.get('pinterestData') or {}).get('pinLink'),
                   'tiktokData.articleLink': (p.get('tiktokData') or {}).get('articleLink'),
                   'smartLinkData.targetUrl': (p.get('smartLinkData') or {}).get('targetUrl')}
        for pr in p.get('providers') or []:
            ag = (pr.get('network') or '').lower()
            if ag not in AGLAR:
                continue
            st = pr.get('status') or ''
            mu, yu = urller(metin), urller(yorum)
            la = {k: v for k, v in alanlar.items() if v and (k != 'pinterestData.pinLink' or ag == 'pinterest')
                  and (k != 'tiktokData.articleLink' or ag == 'tiktok')}
            hepsi = [('metin', u) for u in mu] + [('ilk_yorum', u) for u in yu] + [(k, v) for k, v in la.items()]
            for yer, u in hepsi:
                url_kul[u][f'{ag}:{yer}'] += 1
            c = cta(metin)
            o = ozet[ag]
            o['durum'][st] += 1
            o['say']['toplam'] += 1
            o['say']['metinde_etsy_url'] += any(tur(u) != 'etsy disi' for u in mu)
            o['say']['metinde_herhangi_url'] += bool(mu)
            o['say']['ilk_yorum_var'] += bool(yorum.strip())
            o['say']['ilk_yorumda_url'] += bool(yu)
            o['say']['ilk_yorumda_etsy_url'] += any(tur(u) != 'etsy disi' for u in yu)
            o['say']['link_alani_dolu'] += bool(la)
            o['say']['share_save_isaretli_url_iceren'] += any(share_save(u) for _, u in hepsi)
            for yer, u in hepsi:
                o['url_turu'][f'{yer}:{tur(u)}'] += 1
                for k in parametreler(u):
                    o['parametre'][k] += 1
            for x in c:
                o['cta'][re.sub(r'\b[A-Z][a-z]+ (?:and|&) [A-Z][a-z]+\b', '<CIFT>', x)] += 1
            if not c:
                o['cta']['(CTA satiri yok)'] += 1
            satir.append([zt, ag, st, pr.get('detailedStatus') or '', p.get('id'), pr.get('publicUrl') or '',
                          ' '.join(mu), ' | '.join(f'{tur(u)}' for u in mu),
                          ' '.join(f'{k}={v}' for k, v in la.items()),
                          ' || '.join(c), 'evet' if yorum.strip() else 'hayir', ' '.join(yu), yorum[:200].replace('\n', ' '),
                          ' '.join(sorted({','.join(share_save(u)) for _, u in hepsi if share_save(u)})),
                          ' '.join(sorted({k for _, u in hepsi for k in parametreler(u)}))])
    yaz_csv(out, 'K2_GONDERI.csv', ['plan_zamani', 'ag', 'durum', 'ayrintili_durum', 'gonderi_id', 'yayin_linki',
                                    'metindeki_url', 'metin_url_turu', 'link_alani', 'cta_satirlari', 'ilk_yorum_var',
                                    'ilk_yorumdaki_url', 'ilk_yorum_ilk200', 'share_save_isaretleri', 'url_parametreleri'], satir)

    oz = []
    for ag in AGLAR:
        o = ozet.get(ag)
        if not o:
            oz.append([ag, 0] + [''] * 13 + ['/v2/scheduler/posts: bu agda kayit yok']); continue
        d = o['durum']
        oz.append([ag, o['say']['toplam'], d.get('PUBLISHED', 0), d.get('PENDING', 0),
                   '; '.join(f'{k}={v}' for k, v in sorted(d.items()) if k not in ('PUBLISHED', 'PENDING')),
                   o['say']['metinde_herhangi_url'], o['say']['metinde_etsy_url'],
                   '; '.join(f'{k}={v}' for k, v in sorted(o['url_turu'].items())), o['say']['link_alani_dolu'],
                   o['say']['ilk_yorum_var'], o['say']['ilk_yorumda_url'], o['say']['ilk_yorumda_etsy_url'],
                   o['say']['share_save_isaretli_url_iceren'],
                   '; '.join(f'{k}={v}' for k, v in o['parametre'].most_common()),
                   ' || '.join(f'{k} [{v}]' for k, v in o['cta'].most_common(6)),
                   f'/v2/scheduler/posts {BAS} - {SON}; okuma {okuma}'])
        log(f'AG {ag}: toplam {o["say"]["toplam"]}, durum {dict(d)}, metinde etsy url {o["say"]["metinde_etsy_url"]}, '
            f'link alani {o["say"]["link_alani_dolu"]}, ilk yorum {o["say"]["ilk_yorum_var"]} (url {o["say"]["ilk_yorumda_url"]}), '
            f'url turu {dict(o["url_turu"])}, param {dict(o["parametre"])}')
        for k, v in o['cta'].most_common(6):
            log(f'  CTA {ag} [{v}]: {k}')
    yaz_csv(out, 'K2_AG_OZET.csv', ['ag', 'gonderi', 'yayinlanmis', 'bekleyen', 'diger_durum', 'metinde_url_olan',
                                    'metinde_etsy_url_olan', 'url_yer_tur_sayimi', 'link_alani_dolu', 'ilk_yorum_var',
                                    'ilk_yorumda_url_olan', 'ilk_yorumda_etsy_url_olan', 'share_save_isaretli',
                                    'url_parametre_anahtarlari', 'cta_ilk6', 'kaynak'], oz)

    # 3) URL kontrolu (yalniz GET)
    us = sorted(url_kul)
    log(f'URL kontrolu: {len(us)} benzersiz URL')
    ur, t0 = [], time.time()
    for i, u in enumerate(us, 1):
        zincir, kod, son_u, hata = kontrol(u)
        ur.append([u, tur(u), ' '.join(parametreler(u)), ','.join(share_save(u)) or 'hayir',
                   '; '.join(f'{k}={v}' for k, v in sorted(url_kul[u].items())), sum(url_kul[u].values()),
                   zincir[0][0] if zincir else 0, kod, son_u, tur(son_u), ' -> '.join(f'{c}' for c, _ in zincir), hata,
                   datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')])
        if i % 10 == 0 or i == len(us):
            g = time.time() - t0
            log(f'  URL {i}/{len(us)} ({100 * i // len(us)}%), gecen {g:.0f} sn, kalan ~{g / i * (len(us) - i):.0f} sn')
        time.sleep(0.5)
    yaz_csv(out, 'K2_URL.csv', ['url', 'tur', 'parametreler', 'share_save', 'kullanim_ag_yer', 'kullanim_toplam',
                                'ilk_http', 'son_http', 'son_url', 'son_url_turu', 'zincir_kodlari', 'hata', 'kontrol_utc'], ur)
    for k, v in Counter((r[1], r[7]) for r in ur).most_common():
        log(f'URL tur={k[0]} son_http={k[1]}: {v}')

    # 4) profil / bio linki (Metricool'dan okunabiliyorsa)
    prof = []
    bj = guvenli(mc, 'settings_brands', '/v2/settings/brands', {}, out)
    bt = guvenli(mc, f'settings_brand_{mc.b}', f'/v2/settings/brands/{mc.b}', {}, out)
    sj = guvenli(mc, 'admin_simpleProfiles', '/admin/simpleProfiles', {}, out)
    gb = guvenli(mc, 'linkinbio_getbioButtons', '/linkinbio/instagram/getbioButtons', {'blogid': mc.b}, out)
    gc = guvenli(mc, 'linkinbio_getbiocatalog', '/linkinbio/instagram/getbiocatalog', {'blogid': mc.b}, out)
    marka = mpb.veri(bt) if bt is not None else None
    nd = (marka or {}).get('networksData') if isinstance(marka, dict) else None
    pub = next((x for x in (sj if isinstance(sj, list) else liste(sj) or []) if str(x.get('id')) == mc.b), {}) if sj is not None else {}
    log(f'BRAND networksData anahtarlari: {sorted(nd) if isinstance(nd, dict) else YOK}; simpleProfiles marka alanlari: '
        f'{sorted(k for k, v in pub.items() if v not in (None, "", [], {}))[:60] if pub else YOK}')
    for ag, nd_k, pub_k in (('pinterest', 'pinterestData', 'pinterest'), ('instagram', 'instagramData', 'instagram'),
                            ('facebook', 'facebookData', 'facebook'), ('threads', 'threadsData', 'threads'),
                            ('tiktok', 'tiktokData', 'tiktok'), ('youtube', 'youtubeData', 'youtube')):
        v = nd.get(nd_k) if isinstance(nd, dict) else None
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                pass
        v = v if isinstance(v, dict) else {}
        bio_alan = {k: x for k, x in v.items() if re.search(r'website|bio|link', k, re.I) and x}
        prof.append([ag, v.get('username') or pub.get(pub_k) or YOK, v.get('profileURL') or YOK,
                     json.dumps(bio_alan, ensure_ascii=False) if bio_alan else YOK,
                     f'/v2/settings/brands/{{id}} networksData.{nd_k}; /admin/simpleProfiles .{pub_k}'])
    for b in (gb if isinstance(gb, list) else liste(gb) or []):
        prof.append(['instagram (Metricool link-in-bio butonu)', '', '', f"{b.get('text')} -> {b.get('link')} (kisa {b.get('shortUrl')})",
                     '/linkinbio/instagram/getbioButtons'])
    if gb is None:
        prof.append(['instagram (Metricool link-in-bio butonu)', '', '', YOK, '/linkinbio/instagram/getbioButtons (HTTP hata)'])
    nkat = len(gc if isinstance(gc, list) else liste(gc) or [])
    prof.append(['instagram (Metricool link-in-bio katalog)', '', '', f'{nkat} oge' if gc is not None else YOK,
                 '/linkinbio/instagram/getbiocatalog'])
    yaz_csv(out, 'K2_PROFIL.csv', ['ag', 'kullanici_adi', 'profil_url', 'bio_link', 'kaynak'], prof)
    for r in prof:
        log('PROFIL ' + ' | '.join(str(x) for x in r[:4]))


if __name__ == '__main__':
    main()
