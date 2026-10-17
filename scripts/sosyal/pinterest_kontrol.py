#!/usr/bin/env python3
"""Pinterest 17 Eki kontrolu (SALT OKUMA; Metricool'a ve Pinterest'e yazma YOK). Yalniz GET.
1) Metricool /v2/analytics/timelines (network=pinterest; metric impression, pin_click, outbound_click, save):
   30 gun (18 Eyl - 17 Eki) ve 7 gun (10 - 17 Eki) toplam; 10 - 17 Eki gunluk gosterim.
2) Pano bazinda: /v2/analytics/posts/pinterest pin satirlarinda pano alani varsa pano toplami; yoksa "yok".
3) Scheduler'da 13 Eki ve sonrasi YAYINLANMIS en yeni 5 Pinterest gonderisinin pin linki; sayfa HTML'i (masaustu UA) indirilir,
   "PDF" / "5 print ready PDF files" aranir. Sayfada pin basligi da yoksa (giris/engel sayfasi) "erisilemedi".
Metricool bir degeri vermiyorsa "yok" yazilir; tahmin yok. Ham yanitlar HAM_*.json (token icermez).
Kullanim: pinterest_kontrol.py TOKEN.json CIKTI_DIR"""
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
TZ = 'Europe/Istanbul'
METRIK = [('impression', 'gosterim'), ('pin_click', 'pin_tiklama'), ('outbound_click', 'disa_tiklama'), ('save', 'kayit')]
B30, B7, SON = date(2026, 9, 18), date(2026, 10, 10), date(2026, 10, 17)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'


def ham(out, ad, veri):
    json.dump(veri, open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)


def gun_degerleri(j):
    """Yanittaki (tarih, deger) ciftlerini bulur; bicim bilinmediginden genel tarama. Donus: {date: float}."""
    out = {}

    def tarih(v):
        if isinstance(v, (int, float)) and v > 1e9:
            return datetime.utcfromtimestamp(v / 1000 if v > 1e12 else v).date()
        if isinstance(v, str) and re.match(r'\d{4}-\d{2}-\d{2}', v):
            return date.fromisoformat(v[:10])
        if isinstance(v, str) and re.fullmatch(r'\d{8}', v):
            return date(int(v[:4]), int(v[4:6]), int(v[6:]))
        return None

    def gez(x):
        if isinstance(x, dict):
            t = next((tarih(x[k]) for k in ('dateTime', 'date', 'datetime', 'timestamp', 'x', 'day') if k in x and tarih(x[k])), None)
            v = next((x[k] for k in ('value', 'y', 'count', 'total') if k in x and isinstance(x[k], (int, float))), None)
            if t and v is not None:
                out[t] = out.get(t, 0) + float(v)
                return
            for y in x.values():
                gez(y)
        elif isinstance(x, list):
            if len(x) == 2 and tarih(x[0]) and isinstance(x[1], (int, float)):
                out[tarih(x[0])] = out.get(tarih(x[0]), 0) + float(x[1]); return
            for y in x:
                gez(y)
    gez(j)
    return out


def sayi(v):
    return 'yok' if v is None else (int(v) if float(v).is_integer() else round(v, 2))


def main():
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    rapor = {}

    # 1) zaman serileri
    seri = {}
    for m, ad in METRIK:
        try:
            j = mc.istek('GET', '/v2/analytics/timelines', {'network': 'pinterest', 'metric': m, 'from': f'{B30}T00:00:00',
                                                            'to': f'{SON}T23:59:59', 'timezone': TZ})
        except SystemExit as e:
            print(f'TIMELINE {m}: HATA {str(e)[:150]}'); j = None
        ham(out, f'timeline_{m}', j)
        seri[ad] = gun_degerleri(j) if j is not None else None
        g = seri[ad]
        ozet = 'yanit yok' if g is None else f"{len(g)} gun, ilk {min(g) if g else '-'}, son {max(g) if g else '-'}"
        print(f'TIMELINE {m}: {ozet}')

    def toplam(ad, bas):
        g = seri.get(ad)
        if not g:
            return None
        return sum(v for t, v in g.items() if bas <= t <= SON)
    for ad_dosya, bas in (('PIN_30G_20261017.csv', B30), ('PIN_7G_20261017.csv', B7)):
        with open(os.path.join(out, ad_dosya), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(['donem', 'gosterim', 'pin_tiklama', 'disa_tiklama', 'kayit'])
            sat = [f'{bas} - {SON}'] + [sayi(toplam(ad, bas)) for _, ad in METRIK]
            w.writerow(sat); rapor[ad_dosya] = sat
            print(ad_dosya, sat)
    with open(os.path.join(out, 'PIN_GUNLUK_20261017.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['tarih', 'gosterim'])
        g = seri.get('gosterim') or {}
        gunluk = []
        for i in range((SON - B7).days + 1):
            t = B7 + timedelta(days=i)
            gunluk.append((str(t), sayi(g.get(t)) if g else 'yok'))
            w.writerow(gunluk[-1])
        print('GUNLUK', gunluk)

    # 2) pano bazinda
    try:
        pj = mc.istek('GET', '/v2/analytics/posts/pinterest', {'from': f'{B30}T00:00:00', 'to': f'{SON}T23:59:59', 'timezone': TZ})
    except SystemExit as e:
        print(f'POSTS/PINTEREST: HATA {str(e)[:150]}'); pj = None
    ham(out, 'posts_pinterest', pj)
    pins = mpb.veri(pj) if pj is not None else None
    if isinstance(pins, dict):
        pins = next((v for v in pins.values() if isinstance(v, list)), [])
    panolar = {}
    try:
        bl = mpb.veri(mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b}))
        if isinstance(bl, dict):
            bl = next((v for v in bl.values() if isinstance(v, list)), [])
        panolar = {str(b.get('id')): b.get('name') for b in bl or []}
    except SystemExit as e:
        print(f'PANOLAR: HATA {str(e)[:150]}')
    anahtarlar = sorted({k for p in pins or [] if isinstance(p, dict) for k in p})
    print(f'POSTS/PINTEREST: {len(pins) if pins is not None else "yanit yok"} pin; alanlar {anahtarlar[:40]}')
    pano_k = next((k for k in ('boardId', 'board_id', 'board', 'boardName', 'board_name') if k in anahtarlar), None)

    def al(p, *ks):
        for k in ks:
            v = p.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        return None
    with open(os.path.join(out, 'PIN_PANO_20261017.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['pano', 'pin_sayisi', 'gosterim', 'tiklama', 'kayit', 'not'])
        if not pins or not pano_k:
            w.writerow(['yok', '', '', '', '', 'Metricool pin satirlarinda pano alani yok' if pins else 'Metricool pin listesi bos/yanit yok'])
            print('PANO: yok')
        else:
            top = {}
            for p in pins:
                b = p.get(pano_k)
                b = b.get('name') or b.get('id') if isinstance(b, dict) else b
                b = panolar.get(str(b), b)
                t = top.setdefault(b, [0, 0.0, 0.0, 0.0, set()])
                t[0] += 1
                for i, ks in ((1, ('impressions', 'impression')), (2, ('pinClicks', 'pin_click', 'clicks', 'outboundClicks')), (3, ('saves', 'save'))):
                    v = al(p, *ks)
                    if v is None:
                        t[4].add(ks[0])
                    else:
                        t[i] += v
            for b, t in sorted(top.items(), key=lambda x: -x[1][1]):
                w.writerow([b, t[0], sayi(t[1]) if 'impressions' not in t[4] else 'yok', sayi(t[2]) if 'pinClicks' not in t[4] else 'yok',
                            sayi(t[3]) if 'saves' not in t[4] else 'yok', 'yalniz donemde yayinlanan pinler'])
            print('PANO', {b: t[:4] for b, t in top.items()})

    # 3) en yeni 5 yayinlanmis pin + sayfa kontrolu
    ps, t = {}, datetime(2026, 10, 13)
    while t < datetime(2026, 10, 18):
        e = t + timedelta(days=5)
        for p in mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': t.strftime('%Y-%m-%dT%H:%M:%S'),
                                                                    'end': e.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})) or []:
            ps[p.get('id')] = p
        t = e
    yay = []
    for p in ps.values():
        pr = next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'pinterest'), None)
        if pr and pr.get('status') == 'PUBLISHED' and pr.get('publicUrl'):
            yay.append((p['publicationDate']['dateTime'], p, pr))
    yay.sort(key=lambda x: x[0], reverse=True)
    print(f'YAYINLANMIS Pinterest (13 Eki+): {len(yay)}; en yeni 5 incelenecek')
    sd = os.path.join(out, '_sayfa'); os.makedirs(sd, exist_ok=True)
    pdf_var = 0
    with open(os.path.join(out, 'PIN_SAYFA_20261017.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['yayin', 'link', 'pano', 'baslik', 'pdf_ifadesi_var_mi', 'http', 'not'])
        for zt, p, pr in yay[:5]:
            pd = p.get('pinterestData') or {}
            link, baslik = pr['publicUrl'], pd.get('pinTitle') or ''
            pano = panolar.get(str(pd.get('boardId')), pd.get('boardId'))
            yol = os.path.join(sd, re.sub(r'\W', '_', link)[-60:] + '.html')
            kod = subprocess.run(['curl', '-sL', '-m', '25', '-A', UA, '-H', 'Accept-Language: en-US,en;q=0.9', '-o', yol, '-w', '%{http_code}', link],
                                 capture_output=True, text=True).stdout
            html = open(yol, encoding='utf-8', errors='replace').read() if os.path.exists(yol) else ''
            baslik_var = bool(baslik) and (baslik[:40] in html or baslik[:40].replace('&', '&amp;') in html)
            acik = (p.get('text') or '').strip()
            i = html.find(acik[:50]) if len(acik) >= 20 else -1
            pencere = html[i:i + len(acik) + 300] if i >= 0 else ''
            tam = '5 print ready PDF files' in html
            pdf = tam or 'PDF' in pencere                      # yalniz pinin kendi aciklamasinda (yan pinlerin metni sayilmaz)
            if kod != '200' or not baslik_var:
                sonuc, notu = 'erisilemedi', f'http {kod}; sayfada pin basligi {"var" if baslik_var else "yok"} (giris/engel ya da istemci tarafi sayfa)'
            else:
                sonuc = 'evet' if pdf else 'hayir'
                notu = ('tam ifade "5 print ready PDF files" var; ' if tam else '') + \
                       (f'aciklama sayfada bulundu; sayfada toplam "PDF" {html.count("PDF")}' if i >= 0 else 'aciklama metni sayfada bulunamadi; yalniz tam ifade arandi')
                pdf_var += sonuc == 'evet'
            w.writerow([zt, link, pano, baslik, sonuc, kod, notu])
            print(f'SAYFA {zt} {link} | {pano} | pdf={sonuc} | {notu}')
    print(f'PDF ifadesi: {pdf_var}/{min(5, len(yay))}')


if __name__ == '__main__':
    main()
