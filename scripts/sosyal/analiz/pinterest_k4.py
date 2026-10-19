#!/usr/bin/env python3
"""Pinterest K4 analizi (19 Eki 2026). SALT OKUMA: Metricool'a ve Pinterest'e YAZMA YOK, yalniz GET + gorsel indirme.
1) Eylul / Ekim pin farki: /v2/analytics/posts/pinterest (from 2026-01-01) pin satirlari; gorsel turu (mediaType + kontak
   sayfasi), baslik kalibi (burc adlari {Z}), aciklama, link hedefi, pano, yayin saati, yayin yasi.
   Yas esitleme: pin bazinda yalniz birikimli deger var; 17 Eki ve 19 Eki ham okumalari + bu okuma = en fazla 3 nokta.
   Yasi [7,8) / [14,15) gun olan bir okuma varsa o deger yazilir, yoksa "erisilemedi".
   Hesap duzeyi gunluk seri (subject=account, 1 Eyl - 19 Eki) ayri CSV.
2) P3 panosu: PIN_METIN_234.csv (+ varsa PIN_V6_PLAN_YAYIN.csv) ile /v2/scheduler/posts 13 Eki - 6 Kas karsilastirmasi.
   Eslesme: pinTitle == plan basligi (234 baslik benzersiz). DUZELTME YOK.
Kullanim: pinterest_k4.py TOKEN.json CIKTI_DIR GORSEL_DIR --onceki 17EKI_HAM.json --k1 19EKI_HAM.json --metin PIN_METIN_234.csv
          [--plan PIN_V6_PLAN_YAYIN.csv] [--panolar PANOLAR_HAM.json]"""
import argparse
import csv
import importlib.util
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
BURC = r'Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces'
MET = [('impressions', 'gosterim'), ('pinClicks', 'pin_tiklama'), ('outboundClicks', 'disa_tiklama'), ('saves', 'kayit')]
YOK = 'erisilemedi'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'


def yaz(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir')


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v or []


def zaman(s):
    """'2026-10-16T12:30:47+0300' -> aware datetime; ofset yoksa None."""
    m = re.fullmatch(r'(.{19})([+-]\d\d):?(\d\d)', s or '')
    return datetime.fromisoformat(f'{m.group(1)}{m.group(2)}:{m.group(3)}') if m else None


def kalip(s):
    return re.sub(BURC, '{Z}', s or '', flags=re.I)


def link_kalip(u):
    p = urllib.parse.urlparse(u or '')
    return f'{p.netloc}{re.sub(r"[0-9]+", "{n}", p.path)}' + ('?' + '&'.join(sorted(urllib.parse.parse_qs(p.query))) if p.query else '')


def oku(mc, out, ad, yol, params):
    try:
        j = mc.istek('GET', yol, params)
    except SystemExit as e:
        print(f'{ad}: HATA {str(e)[:200]}'); j = {'_hata': str(e)[:300]}
    json.dump(j, open(os.path.join(out, f'HAM_K4_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
    return j


def indir(url, yol):
    for u in (url.replace('/400x300/', '/736x/'), url):
        try:
            r = urllib.request.Request(u, headers={'User-Agent': UA})
            with urllib.request.urlopen(r, timeout=30) as y:
                open(yol, 'wb').write(y.read())
            return u
        except Exception:
            continue
    return ''


def kontak(yollar, etiketler, hedef, baslik, sutun=6):
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
    except OSError:
        f = fb = ImageFont.load_default()
    W, H, E = 240, 330, 58
    sat = max(1, -(-len(yollar) // sutun))
    im = Image.new('RGB', (sutun * W, 40 + sat * (H + E)), 'white')
    d = ImageDraw.Draw(im); d.text((8, 10), baslik, fill='black', font=fb)
    for i, (y, et) in enumerate(zip(yollar, etiketler)):
        x0, y0 = (i % sutun) * W, 40 + (i // sutun) * (H + E)
        try:
            g = Image.open(y).convert('RGB'); g.thumbnail((W - 8, H - 8))
            im.paste(g, (x0 + (W - g.width) // 2, y0 + (H - g.height) // 2))
        except Exception:
            d.rectangle([x0 + 4, y0 + 4, x0 + W - 4, y0 + H - 4], outline='red'); d.text((x0 + 10, y0 + 10), 'gorsel yok', fill='red', font=f)
        for k, s in enumerate(et.split('\n')[:3]):
            d.text((x0 + 6, y0 + H + 2 + k * 18), s[:34], fill='black', font=f)
    im.save(hedef, quality=88)
    print(f'KONTAK {os.path.basename(hedef)}: {len(yollar)} pin')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti'); ap.add_argument('gorsel')
    for k in ('onceki', 'k1', 'metin', 'plan', 'panolar'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True); os.makedirs(a.gorsel, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    simdi = datetime.now(timezone.utc)
    print(f'OKUMA ANI (UTC): {simdi:%Y-%m-%dT%H:%M:%SZ}')

    # --- okumalar
    pins = liste(oku(mc, out, 'posts_pinterest', '/v2/analytics/posts/pinterest',
                     {'from': '2026-01-01T00:00:00', 'to': '2026-10-19T23:59:59', 'timezone': TZ}))
    hesap = {}
    for m, ad in [('impression', 'gosterim'), ('pin_click', 'pin_tiklama'), ('outbound_click', 'disa_tiklama'), ('save', 'kayit')]:
        j = oku(mc, out, f'account_{m}', '/v2/analytics/timelines', {'network': 'pinterest', 'metric': m, 'subject': 'account',
                'from': '2026-09-01T00:00:00', 'to': '2026-10-19T23:59:59', 'timezone': TZ})
        for b in liste(j):
            for x in b.get('values') or [] if isinstance(b, dict) else []:
                hesap.setdefault(x['dateTime'][:10], {})[ad] = x.get('value')
    panolar = {}
    for b in liste(oku(mc, out, 'boards_pinterest', '/v2/scheduler/boards/pinterest', {'brandId': mc.b})):
        panolar[str(b.get('id'))] = b.get('name') or ''
    ps, t = {}, datetime(2026, 10, 13)
    while t < datetime(2026, 11, 7):
        e = min(t + timedelta(days=5), datetime(2026, 11, 7))
        for p in liste(oku(mc, out, f'scheduler_{t:%Y%m%d}', '/v2/scheduler/posts',
                           {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})):
            ps[str(p.get('id'))] = p
        t = e
    print(f'POSTS/PINTEREST: {len(pins)} pin; PANOLAR {len(panolar)}; SCHEDULER {len(ps)} gonderi (13 Eki - 6 Kas)')

    # --- anlik goruntuler (birikimli): 17 Eki, 19 Eki K1, bu okuma
    anlik = []
    for etiket, yol, an in (('17Eki', a.onceki, datetime(2026, 10, 17, 10, 59, tzinfo=timezone.utc)),
                            ('19Eki_K1', a.k1, datetime(2026, 10, 19, 11, 16, tzinfo=timezone.utc))):
        if yol and os.path.exists(yol):
            anlik.append((etiket, an, {str(p.get('id')): p for p in liste(json.load(open(yol)))}))
    anlik.append(('bu_okuma', simdi, {str(p.get('id')): p for p in pins}))
    print('ANLIK: ' + ', '.join(f'{e} {len(d)} pin' for e, _, d in anlik))

    # --- pin satirlari
    satir = []
    for p in pins:
        c = zaman(p.get('createdAt') or '')
        grup = 'Eylul' if c and c.month == 9 else ('Ekim' if c and c.month == 10 else 'diger')
        yas = round((simdi - c).total_seconds() / 86400, 2) if c else ''
        nok = []
        for e, an, d in anlik:
            q = d.get(str(p.get('id')))
            if q and c:
                nok.append((e, (an - c).total_seconds() / 86400, q.get('impressions')))
        g7 = next((f'{v} ({e}, yas {y:.2f})' for e, y, v in nok if 7 <= y < 8), YOK)
        g14 = next((f'{v} ({e}, yas {y:.2f})' for e, y, v in nok if 14 <= y < 15), YOK)
        lk = p.get('link') or ''
        satir.append({
            'grup': grup, 'pin_id': p.get('id'), 'yayin': p.get('createdAt') or '',
            'yayin_saat_ist': c.astimezone(IST).strftime('%H:%M') if c else '', 'yas_gun': yas,
            'pano_id': p.get('boardId'), 'pano': panolar.get(str(p.get('boardId')), YOK), 'medya_turu': p.get('mediaType'),
            **{ad: p.get(k) for k, ad in MET},
            'baslik': p.get('title') or '', 'baslik_kalibi': kalip(p.get('title')), 'baslik_uzunluk': len(p.get('title') or ''),
            'aciklama_uzunluk': len(p.get('description') or ''), 'aciklama_kalibi_ilk80': kalip(p.get('description'))[:80],
            'alt_metin_var': 'evet' if (p.get('altText') or '').strip() else 'hayir',
            'link': lk, 'link_kalibi': link_kalip(lk), 'gosterim_7g': g7, 'gosterim_14g': g14,
            'anlik_noktalar': ' | '.join(f'{e}: yas {y:.2f} g, gosterim {v}' for e, y, v in nok), 'gorsel_url': p.get('imageUrl') or ''})
    satir.sort(key=lambda r: r['yayin'])
    K = list(satir[0]) if satir else []
    yaz(out, 'K4_PINLER.csv', K, [[r[k] for k in K] for r in satir])

    # --- grup ozeti
    oz = []
    for g in ('Eylul', 'Ekim'):
        R = [r for r in satir if r['grup'] == g]
        if not R:
            continue
        top = {ad: sum(r[ad] or 0 for r in R) for _, ad in MET}
        gs = [r['gosterim'] or 0 for r in R]
        oz += [[g, 'pin_sayisi', len(R)], [g, 'ilk_yayin', R[0]['yayin']], [g, 'son_yayin', R[-1]['yayin']]]
        oz += [[g, f'toplam_{ad}', top[ad]] for _, ad in MET]
        oz += [[g, 'pin_basi_gosterim_ort', round(top['gosterim'] / len(R), 2)], [g, 'pin_basi_gosterim_medyan', statistics.median(gs)],
               [g, 'gosterim_0_pin', sum(1 for x in gs if x == 0)], [g, 'yas_gun_min', min(r['yas_gun'] for r in R)],
               [g, 'yas_gun_max', max(r['yas_gun'] for r in R)],
               [g, 'baslik_uzunluk_ort', round(statistics.mean(r['baslik_uzunluk'] for r in R), 1)],
               [g, 'aciklama_uzunluk_ort', round(statistics.mean(r['aciklama_uzunluk'] for r in R), 1)],
               [g, 'alt_metin_var', sum(1 for r in R if r['alt_metin_var'] == 'evet')],
               [g, 'gosterim_7g_olculen_pin', sum(1 for r in R if r['gosterim_7g'] != YOK)],
               [g, 'gosterim_14g_olculen_pin', sum(1 for r in R if r['gosterim_14g'] != YOK)]]
        for alan in ('medya_turu', 'pano', 'baslik_kalibi', 'link_kalibi', 'aciklama_kalibi_ilk80'):
            oz += [[g, f'{alan}: {k}', v] for k, v in Counter(r[alan] for r in R).most_common(8)]
        oz += [[g, f'yayin_saati: {k}', v] for k, v in sorted(Counter(r['yayin_saat_ist'][:2] for r in R).items())]
    yaz(out, 'K4_GRUP_OZET.csv', ['grup', 'olcu', 'deger'], oz)

    yas_sat = [[r['grup'], r['pin_id'], r['yayin'], r['gosterim_7g'], r['gosterim_14g'], r['anlik_noktalar']] for r in satir]
    yaz(out, 'K4_YAS_ESIT.csv', ['grup', 'pin_id', 'yayin', 'gosterim_ilk7g', 'gosterim_ilk14g', 'anlik_noktalar'], yas_sat)
    yaz(out, 'K4_HESAP_GUNLUK_1EYL_19EKI.csv', ['dateTime_etiketi', 'gosterim', 'pin_tiklama', 'disa_tiklama', 'kayit', 'kaynak'],
        [[d] + [v.get(k, '') for k in ('gosterim', 'pin_tiklama', 'disa_tiklama', 'kayit')]
         + ['/v2/analytics/timelines subject=account (ham dateTime etiketi)'] for d, v in sorted(hesap.items())])

    # --- en iyi / en kotu 10 + gorseller
    iyi = sorted(satir, key=lambda r: (-(r['gosterim'] or 0), r['yayin']))[:10]
    kotu = sorted(satir, key=lambda r: ((r['gosterim'] or 0), r['yayin']))[:10]   # esitlikte en eski once
    KB = ['sira', 'grup', 'pin_id', 'yayin', 'pano', 'gosterim', 'pin_tiklama', 'disa_tiklama', 'kayit', 'baslik', 'gorsel_url']
    yaz(out, 'K4_EN_IYI_10.csv', KB, [[i + 1] + [r[k] for k in KB[1:]] for i, r in enumerate(iyi)])
    yaz(out, 'K4_EN_KOTU_10.csv', KB, [[i + 1] + [r[k] for k in KB[1:]] for i, r in enumerate(kotu)])

    def yol(r):
        return os.path.join(a.gorsel, f"{r['pin_id']}.jpg")
    with ThreadPoolExecutor(8) as ex:
        sonuc = list(ex.map(lambda r: indir(r['gorsel_url'], yol(r)) if r['gorsel_url'] else '', satir))
    print(f'GORSEL: {sum(1 for s in sonuc if s)}/{len(satir)} indirildi; 736x: {sum(1 for s in sonuc if "/736x/" in s)}')
    et = lambda r, i=None: (f"{'#' + str(i) + ' ' if i else ''}{r['yayin'][:10]} {r['yayin_saat_ist']}\n"
                            f"gos {r['gosterim']} tik {r['pin_tiklama']} dis {r['disa_tiklama']} kay {r['kayit']}\n{r['pano'][:30]}")
    kontak([yol(r) for r in iyi], [et(r, i + 1) for i, r in enumerate(iyi)], os.path.join(out, 'K4_KONTAK_EN_IYI_10.jpg'),
           'En iyi 10 pin (gosterim, /v2/analytics/posts/pinterest)', 5)
    kontak([yol(r) for r in kotu], [et(r, i + 1) for i, r in enumerate(kotu)], os.path.join(out, 'K4_KONTAK_EN_KOTU_10.jpg'),
           'En kotu 10 pin (gosterim; esitlikte en eski once)', 5)
    for g in ('Eylul', 'Ekim'):
        R = [r for r in satir if r['grup'] == g]
        for s in range(0, len(R), 60):
            kontak([yol(r) for r in R[s:s + 60]], [et(r) for r in R[s:s + 60]],
                   os.path.join(out, f'K4_KONTAK_{g.upper()}_{s // 60 + 1}.jpg'), f'{g} pinleri {s + 1}-{min(s + 60, len(R))} / {len(R)} (yayin sirasi)')

    # --- P3: plan / zamanlayici
    M = list(csv.DictReader(open(a.metin, encoding='utf-8-sig'))) if a.metin else []
    plan_bas = {r['baslik'].strip(): r for r in M}
    plan_dosya = {r['dosya'].strip(): r for r in M}
    plan_pano = Counter((r['pin'], r['pano']) for r in M)
    pano_ad_id = {n.strip().lower(): i for i, n in panolar.items()}          # canli liste once
    if a.panolar and os.path.exists(a.panolar):
        for b in liste(json.load(open(a.panolar))):
            pano_ad_id.setdefault((b.get('name') or '').strip().lower(), str(b.get('id')))
    yayin_plan = {}
    if a.plan and os.path.exists(a.plan):
        for r in csv.DictReader(open(a.plan, encoding='utf-8-sig')):
            yayin_plan[(r.get('baslik') or '').strip()] = r
    print(f'PLAN: {len(M)} satir; pin/pano {dict(plan_pano)}; PIN_V6_PLAN_YAYIN {len(yayin_plan)} satir')
    zs, eslesen = [], set()
    for p in sorted(ps.values(), key=lambda x: (x.get('publicationDate') or {}).get('dateTime', '')):
        st = mpb.pin_durum(p)
        if st is None:
            continue
        pd = p.get('pinterestData') or {}
        b = (pd.get('pinTitle') or '').strip()
        md = (p.get('media') or [''])[0]
        md = os.path.basename(((md.get('url') if isinstance(md, dict) else md) or '').split('?')[0])
        pr, kaynak = (plan_dosya[md], 'dosya') if md in plan_dosya else ((plan_bas[b], 'baslik') if b in plan_bas else (None, ''))
        yp = yayin_plan.get(pr['baslik'].strip(), {}) if pr else {}
        tur = pr['pin'].upper() if pr else 'plan_disi'
        plan_id = pano_ad_id.get(pr['pano'].strip().lower(), YOK) if pr else ''
        z_id = str(pd.get('boardId') or '')
        if pr:
            eslesen.add(pr['baslik'].strip())
        zs.append([(p.get('publicationDate') or {}).get('dateTime', ''), st, tur, pr['cift_anahtari'] if pr else '', b,
                   z_id, panolar.get(z_id, YOK), pr['pano'] if pr else '', plan_id, yp.get('pano_id', ''), yp.get('tarih_saat', ''),
                   ('AYNI' if z_id == plan_id else 'FARKLI') if pr else '', kaynak, md])
    yaz(out, 'K4_ZAMANLAYICI_13EKI_6KAS.csv', ['yayin_zamani', 'durum', 'tur', 'cift', 'baslik', 'zamanlayici_pano_id', 'zamanlayici_pano',
        'plan_pano (PIN_METIN_234)', 'plan_pano_id (ad->id)', 'plan_yayin_pano_id (PIN_V6_PLAN_YAYIN)', 'plan_yayin_tarih', 'pano_fark', 'eslesme', 'medya_dosya'], zs)
    p3 = [z for z in zs if z[2] == 'P3']
    yaz(out, 'K4_P3_FARK.csv', ['yayin_zamani', 'durum', 'cift', 'baslik', 'zamanlayici_pano_id', 'zamanlayici_pano', 'plan_pano', 'plan_pano_id',
                                'plan_yayin_pano_id', 'plan_yayin_tarih'],
        [[z[0], z[1], z[3], z[4], z[5], z[6], z[7], z[8], z[9], z[10]] for z in p3 if z[11] == 'FARKLI'])
    yok = [r for r in M if r['pin'] == 'p3' and r['baslik'].strip() not in eslesen]
    yaz(out, 'K4_P3_ZAMANLAYICIDA_YOK.csv', ['cift', 'baslik', 'plan_pano', 'plan_yayin_tarih'],
        [[r['cift_anahtari'], r['baslik'], r['pano'], yayin_plan.get(r['baslik'].strip(), {}).get('tarih_saat', '')] for r in yok])
    tp = Counter((z[2], z[5], z[6]) for z in zs)
    yaz(out, 'K4_ZAMANLAYICI_TUR_PANO.csv', ['tur', 'pano_id', 'pano', 'adet'], [list(k) + [v] for k, v in sorted(tp.items())])
    for k, v in sorted(tp.items()):
        print(f'TUR/PANO {k}: {v}')
    print(f'P3: zamanlayicida {len(p3)}; pano farkli {sum(1 for z in p3 if z[11] == "FARKLI")}; plandaki 78 P3 icinden zamanlayicida yok {len(yok)}')


if __name__ == '__main__':
    main()
