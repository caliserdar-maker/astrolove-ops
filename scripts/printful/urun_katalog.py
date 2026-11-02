#!/usr/bin/env python3
"""Printful urun taramasi (Merkez 2 Kas 2026, Serdar onayi): ornament tasarimi (yuvarlak daire, altin sembol, isimler, tarih) hangi Printful
urunlerine uyarlanir. YALNIZ OKUMA: GET + kargo ucreti sorgusu (POST /v2/shipping-rates). Siparis / urun / magaza kaydi OLUSTURULMAZ.
Etsy yok. istek() ornament_katalog.py'den (POST izin listesi koda gomulu).

Kapsam: v1 + v2 katalogunda kok kategorisi 'Home & living' ya da 'Accessories' olan urunler; giyim sayilan alt kategoriler
(Shoes, Socks, Flip flops) haric. Giyim / sapka kokleri (Men's, Women's, Kids' clothing, Hats) haric.

Modlar:
  liste <ham>                  urun basina GET: v1 urun, printfiles, v2 urun, v2 varyantlar, v2 fiyat (worldwide / north_america, USD)
  tablo <cikti>                ham'dan TUM_LISTE.csv + sinif (A / B / C) (API yok)
  detay <ham> <id1,id2,...>    secilen urunler: tum varyantlar icin POST /v2/shipping-rates (US DE GB CA AU; 1 ve 2 adet) + v2 availability
  secilen <cikti> <ids>        ham'dan SECILEN25.csv (API yok)"""
import csv
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

_s = importlib.util.spec_from_file_location('ok', Path(__file__).resolve().parent / 'ornament_katalog.py')
ok = importlib.util.module_from_spec(_s); _s.loader.exec_module(ok)

HARIC_ALT = {'Shoes', 'Socks', 'Flip flops'}
KOKLER = {'Home & living', 'Accessories'}
ULKELER = ['US', 'DE', 'GB', 'CA', 'AU']
ADRES = {'US': {'state_code': 'NY', 'city': 'New York', 'zip': '10001'}, 'DE': {'city': 'Berlin', 'zip': '10115'},
         'GB': {'city': 'London', 'zip': 'SW1A 1AA'}, 'CA': {'state_code': 'ON', 'city': 'Toronto', 'zip': 'M5V 2T6'},
         'AU': {'state_code': 'NSW', 'city': 'Sydney', 'zip': '2000'}}
KARGO_VARYANT_SINIR = int(os.environ.get('KARGO_VARYANT_SINIR', '6'))   # urun basina en ucuz (v2 WW) N varyant
# sinif esikleri (tasarim kurali; olculur, tahmin degil): ornament gorunen dairesi 70 mm; yazi isim buyuk harfi 2.38 mm icin daire capi en az
# 2.0 inc (51 mm) gerekir (ornament duzeni %73 olcek). Sarma: en / boy > 2.2.
MIN_KISA_INC = 2.0
SARMA_ORAN = 2.2
YUVARLAK = re.compile(r'\b(round|circle|circular)\b', re.I)
SARMA_AD = re.compile(r'\b(mug|tumbler|bottle|pint glass|wine glass|rocks glass|can-shaped glass|can cooler|candle|socks)\b', re.I)


def j(p):
    return json.loads(Path(p).read_text(encoding='utf-8')) if Path(p).exists() else None


def yaz(p, v):
    Path(p).write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding='utf-8')


def sar(y, yol, g, k, v):
    return {'istek': {'yontem': y, 'yol': yol, 'govde': g}, 'http': k, 'yanit': v}


def liste_l(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def kategori_kok(kat):
    by = {c['id']: c for c in kat}
    def kok(i):
        seen = 0
        while i in by and by[i]['parent_id'] and seen < 10:
            i = by[i]['parent_id']; seen += 1
        return by[i]['title'] if i in by else None
    return by, kok


def cmd_liste(ham):
    ham = Path(ham); ham.mkdir(parents=True, exist_ok=True)
    token = os.environ['PRINTFUL_TOKEN'].strip()
    t0 = time.time()
    k, v1 = ok.istek('/products', token); yaz(ham / 'v1_products.json', sar('GET', '/products', None, k, v1))
    k, kt = ok.istek('/categories', token); yaz(ham / 'v1_categories.json', sar('GET', '/categories', None, k, kt))
    sayfa, off = [], 0
    while off < 5000:
        yol = f'/v2/catalog-products?limit=100&offset={off}&selling_region_name=worldwide'
        k, v = ok.istek(yol, token); sayfa.append(sar('GET', yol, None, k, v))
        d = v.get('data') if isinstance(v, dict) and isinstance(v.get('data'), list) else []
        if k != 200 or not d:
            break
        off += len(d)
        top = (v.get('paging') or {}).get('total') if isinstance(v.get('paging'), dict) else None
        if top is None or off >= int(top):
            break
    yaz(ham / 'v2_catalog_products.json', {'sayfalar': sayfa})
    kat = liste_l(((kt or {}).get('result') or {}).get('categories'))
    by, kok = kategori_kok(kat)
    aday = {}
    for kaynak, urunler in (('v1', liste_l((v1 or {}).get('result'))),
                            ('v2', [p for s in sayfa for p in liste_l((s['yanit'] or {}).get('data'))])):
        for p in urunler:
            cid = p.get('main_category_id')
            kk = kok(cid)
            alt = by.get(cid, {}).get('title')
            if kk in KOKLER and alt not in HARIC_ALT:
                a = aday.setdefault(str(p['id']), dict(kok=kk, alt=alt, kaynak=[]))
                a['kaynak'].append(kaynak)
    haric = sorted({by.get(p.get('main_category_id'), {}).get('title') for p in liste_l((v1 or {}).get('result'))
                    if kok(p.get('main_category_id')) in KOKLER and by.get(p.get('main_category_id'), {}).get('title') in HARIC_ALT})
    yaz(ham / '_adaylar.json', dict(aday=aday, haric_alt=sorted(HARIC_ALT), haric_alt_bulunan=haric))
    print(f'ADAY {len(aday)} urun (haric alt kategori {sorted(HARIC_ALT)})', flush=True)
    ids = sorted(aday, key=int)
    for n, pid in enumerate(ids, 1):
        for ad, yol in (('v1', f'/products/{pid}'), ('printfiles', f'/mockup-generator/printfiles/{pid}'),
                        ('v2', f'/v2/catalog-products/{pid}?selling_region_name=worldwide'),
                        ('v2_variants', f'/v2/catalog-products/{pid}/catalog-variants?limit=100&selling_region_name=worldwide'),
                        ('v2_prices_WW', f'/v2/catalog-products/{pid}/prices?currency=USD&selling_region_name=worldwide'),
                        ('v2_prices_NA', f'/v2/catalog-products/{pid}/prices?currency=USD&selling_region_name=north_america')):
            k, v = ok.istek(yol, token)
            yaz(ham / f'urun_{pid}_{ad}.json', sar('GET', yol, None, k, v))
        if n % 10 == 0 or n == len(ids):
            g = time.time() - t0
            print(f'[{n}/{len(ids)} %{100 * n // len(ids)}] gecen {int(g)}s kalan ~{int(g * (len(ids) - n) / n)}s', flush=True)
    yaz(ham / '_istekler_liste.json', ok.ISTEKLER)
    post = [x for x in ok.ISTEKLER if x['yontem'] != 'GET']
    print(f'ISTEK {len(ok.ISTEKLER)} | GET {len(ok.ISTEKLER) - len(post)} | diger {len(post)}', flush=True)
    return 0


def urun_ozet(ham, pid, a):
    v1 = j(ham / f'urun_{pid}_v1.json') or {}
    r1 = (v1.get('yanit') or {}).get('result')
    p1 = r1.get('product', {}) if isinstance(r1, dict) else {}
    vs1 = liste_l(r1.get('variants')) if isinstance(r1, dict) else []
    v2 = ((j(ham / f'urun_{pid}_v2.json') or {}).get('yanit') or {}).get('data')
    p2 = v2 if isinstance(v2, dict) else {}
    vs2 = liste_l(((j(ham / f'urun_{pid}_v2_variants.json') or {}).get('yanit') or {}).get('data'))
    pf = ((j(ham / f'urun_{pid}_printfiles.json') or {}).get('yanit') or {}).get('result')
    pf = pf if isinstance(pf, dict) else {}
    pfid = {x.get('printfile_id'): x for x in liste_l(pf.get('printfiles'))}
    yerler = pf.get('available_placements') or {}
    def fiyat(etk):
        d = ((j(ham / f'urun_{pid}_v2_prices_{etk}.json') or {}).get('yanit') or {}).get('data')
        d = d if isinstance(d, dict) else {}
        r = {}
        for v in liste_l(d.get('variants')):
            ps = [float(t['price']) for t in liste_l(v.get('techniques')) if t.get('price') not in (None, '')]
            if ps:
                r[v.get('id')] = min(ps)
        return r
    fWW, fNA = fiyat('WW'), fiyat('NA')
    # ana baski alani: ilk varyantin 'default' / 'front' yerlesimi
    ana_yer, pfs = None, []
    for v in liste_l(pf.get('variant_printfiles')):
        pl = v.get('placements') or {}
        for y in ('default', 'front', 'front_large'):
            if y in pl:
                pfs.append((v.get('variant_id'), y, pfid.get(pl[y]) or {}))
                break
        else:
            # ana yerlesim adi farkliysa (or. 'embroidery_front', 'sticker'): mockup / etiket disi en buyuk baski dosyasi
            ad_ = [(y, pfid.get(i) or {}) for y, i in pl.items() if not re.search(r'mockup|label|inside', y)]
            if ad_:
                y, x = max(ad_, key=lambda t: (t[1].get('width') or 0) * (t[1].get('height') or 0))
                pfs.append((v.get('variant_id'), y, x))
    boyutlar = sorted({(x.get('width'), x.get('height'), x.get('dpi')) for _, _, x in pfs if x.get('width')})
    ad = p1.get('title') or p2.get('name') or ''
    acik = ' '.join(x for x in (p2.get('description') or '', p1.get('description') or '') if isinstance(x, str))
    pf_var = {vid: x for vid, _, x in pfs}
    # varyant basina sinif (kural; kanit turu yazilir). Fiziksel boyut: v2 placement_dimensions (inc), yoksa printfile / dpi.
    siniflar = []
    for v in (vs2 or vs1):
        vid = v.get('id')
        vad = str(v.get('name') or '') + ' ' + str(v.get('size') or '')
        dims = [d for d in liste_l(v.get('placement_dimensions')) if not re.search(r'mockup|label|inside', str(d.get('placement')))]
        if dims:
            d = max(dims, key=lambda d: (d.get('width') or 0) * (d.get('height') or 0))
            w_in, h_in, bk = float(d.get('width') or 0), float(d.get('height') or 0), 'v2 placement_dimensions'
        elif vid in pf_var and pf_var[vid].get('dpi'):
            x = pf_var[vid]; w_in, h_in, bk = x['width'] / x['dpi'], x['height'] / x['dpi'], 'printfile / dpi'
        else:
            siniflar.append(('C', vid, 'baski olcusu API vermedi')); continue
        kisa, oran = min(w_in, h_in), max(w_in, h_in) / max(min(w_in, h_in), 1e-6)
        tek_olcu = bool(re.fullmatch(r'\s*[\d.]+\s*(″|"|in)\s*', str(v.get('size') or '')))
        kanit = ('adda round/circle' if YUVARLAK.search(ad) or YUVARLAK.search(vad) else
                 'aciklamada diameter' if re.search(r'diameter', acik, re.I) else
                 'die-cut: kesim tasarim kenarini izler (urun adi)' if re.search(r'die-cut', ad, re.I) else
                 'varyant boyutu tek olcu (cap)' if tek_olcu else '')
        if re.search(r'square shape|square', acik, re.I) and not re.search(r'round|circle|diameter', ad + vad + acik, re.I):
            kanit = ''                                                   # aciklama kare diyor (or. Wall Clock 10x10 square shape)
        nakis = bool(re.search(r'embroider', ad, re.I)) or (bool(liste_l(p2.get('techniques'))) and
                                                              all(t.get('key') == 'embroidery' for t in liste_l(p2.get('techniques'))))
        if nakis:
            siniflar.append(('C', vid, 'nakis (urun adi / teknik): altin doku ve 2.4 mm yazi nakisla uygulanamaz'))
        elif SARMA_AD.search(ad) or oran > SARMA_ORAN:
            siniflar.append(('C', vid, f'sarma / uzun bant baski (en/boy {oran:.2f})'))
        elif re.search(r'\bslit\b', acik, re.I):
            siniflar.append(('C', vid, 'ortada yarik (aciklama): daire ortasi kesilir'))
        elif kisa < MIN_KISA_INC:
            siniflar.append(('C', vid, f'kucuk: kisa kenar {kisa:.2f} inc < {MIN_KISA_INC} ({bk}); isim 2.38 mm sigmaz'))
        elif kanit and oran < 1.05:
            siniflar.append(('A', vid, f'yuvarlak ({kanit}); {w_in:g}x{h_in:g} inc ({bk})'))
        elif oran < 1.05:
            siniflar.append(('B', vid, f'kare {w_in:g}x{h_in:g} inc ({bk}): daire ortada, zemin koselere uzar'))
        else:
            siniflar.append(('B', vid, f'dikdortgen {w_in:g}x{h_in:g} inc (en/boy {oran:.2f}; {bk}): daire ortada, zemin uzar'))
    if siniflar:
        en_iyi = min(x[0] for x in siniflar)
        uygun = [x for x in siniflar if x[0] == en_iyi]
        sinif, gerekce = en_iyi, uygun[0][2] + (f' (+{len(uygun) - 1} varyant ayni sinif)' if len(uygun) > 1 else '')
        uygun_var = ','.join(str(x[1]) for x in uygun)
    else:
        sinif, gerekce, uygun_var = 'C', 'varyant / baski olcusu API vermedi', ''
    yuvarlak = sinif == 'A'
    sekil = 'daire' if yuvarlak else ('kare' if boyutlar and max(boyutlar, key=lambda b: b[0] * b[1])[0] == max(boyutlar, key=lambda b: b[0] * b[1])[1] else ('dikdortgen' if boyutlar else ''))
    bolge = sorted({x.get('region') for v in vs1 for x in liste_l(v.get('availability_status')) if x.get('status') in ('in_stock', 'stocked_on_demand')})
    v1min = min((float(v['price']) for v in vs1 if v.get('price') not in (None, '')), default=None)
    return dict(urun_id=pid, ad=ad, kok_kategori=a['kok'], alt_kategori=a['alt'], katalog=('v1+v2' if 'v1' in a['kaynak'] and 'v2' in a['kaynak'] else '+'.join(a['kaynak'])),
                durdurulmus=p2.get('is_discontinued', p1.get('is_discontinued', '')), varyant_sayisi=len(vs2 or vs1),
                baski_yerlesimleri=';'.join(sorted(yerler)) if yerler else '', cift_yuz=('back' in yerler) if yerler else '',
                sekil=sekil, baski_px=';'.join(f'{w}x{h}' for w, h, _ in boyutlar), baski_dpi=';'.join(sorted({str(d) for _, _, d in boyutlar})),
                en_ucuz_usd_v2_WW=min(fWW.values()) if fWW else '', en_ucuz_usd_v2_NA=min(fNA.values()) if fNA else '',
                en_ucuz_usd_v1=v1min if v1min is not None else '',
                v1_bolgeler=','.join(b for b in bolge if b), sinif=sinif, uygun_varyantlar=uygun_var, gerekce=gerekce,
                kaynak='Printful API (v1 /products, /mockup-generator/printfiles, v2 catalog-products, v2 prices)')


def cmd_tablo(cikti):
    c = Path(cikti); ham = c / 'ham'
    A = j(ham / '_adaylar.json')['aday']
    rows = [urun_ozet(ham, pid, A[pid]) for pid in sorted(A, key=int)]
    with open(c / 'TUM_LISTE.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print('SINIF', dict(Counter(r['sinif'] for r in rows)), 'toplam', len(rows), flush=True)
    return 0


def cmd_detay(ham, ids):
    ham = Path(ham)
    ok.POST_IZIN = {'/v2/shipping-rates'}
    token = os.environ['PRINTFUL_TOKEN'].strip()
    ok.ISTEKLER.clear()
    plan = []
    for pid in ids:
        k, v = ok.istek(f'/v2/catalog-products/{pid}/availability?limit=100&selling_region_name=worldwide', token)
        yaz(ham / f'urun_{pid}_v2_availability.json', sar('GET', f'/v2/catalog-products/{pid}/availability?selling_region_name=worldwide', None, k, v))
        vs = liste_l(((j(ham / f'urun_{pid}_v2_variants.json') or {}).get('yanit') or {}).get('data'))
        pr = ((j(ham / f'urun_{pid}_v2_prices_WW.json') or {}).get('yanit') or {}).get('data')
        pr = {v.get('id'): min((float(t['price']) for t in liste_l(v.get('techniques')) if t.get('price') not in (None, '')), default=9e9)
              for v in liste_l(pr.get('variants'))} if isinstance(pr, dict) else {}
        vs = sorted(vs, key=lambda v: (pr.get(v.get('id'), 9e9), v.get('id')))
        for vv in vs[:KARGO_VARYANT_SINIR]:
            for u in ULKELER:
                for q in (1, 2):
                    plan.append((pid, vv['id'], u, q))
    print(f'KARGO plani {len(plan)} istek', flush=True)
    kayit, t0 = [], time.time()
    for n, (pid, vid, u, q) in enumerate(plan, 1):
        g = {'recipient': {'country_code': u, **ADRES[u]}, 'order_items': [{'source': 'catalog', 'catalog_variant_id': vid, 'quantity': q}], 'currency': 'USD'}
        k, v = ok.istek('/v2/shipping-rates', token, g)
        kayit.append({'urun': pid, 'varyant': vid, 'ulke': u, 'adet': q, **sar('POST', '/v2/shipping-rates', g, k, v)})
        if n % 25 == 0 or n == len(plan):
            gg = time.time() - t0
            print(f'[kargo {n}/{len(plan)} %{100 * n // len(plan)}] gecen {int(gg)}s kalan ~{int(gg * (len(plan) - n) / n)}s', flush=True)
    yaz(ham / 'kargo_v2.json', kayit)
    yaz(ham / '_istekler_detay.json', ok.ISTEKLER)
    post = sorted({x['yol'] for x in ok.ISTEKLER if x['yontem'] == 'POST'})
    print(f'ISTEK {len(ok.ISTEKLER)} | POST yollar {post}', flush=True)
    return 0


def cmd_secilen(cikti, ids):
    c = Path(cikti); ham = c / 'ham'
    A = j(ham / '_adaylar.json')['aday']
    kg = j(ham / 'kargo_v2.json') or []
    K = {}
    for x in kg:
        K[(str(x['urun']), x['varyant'], x['ulke'], x['adet'])] = x
    rows = []
    for pid in ids:
        oz = urun_ozet(ham, pid, A[pid])
        vs = liste_l(((j(ham / f'urun_{pid}_v2_variants.json') or {}).get('yanit') or {}).get('data'))
        v1 = (j(ham / f'urun_{pid}_v1.json') or {}).get('yanit') or {}
        vs1 = {v['id']: v for v in liste_l((v1.get('result') or {}).get('variants'))} if isinstance(v1.get('result'), dict) else {}
        pf = ((j(ham / f'urun_{pid}_printfiles.json') or {}).get('yanit') or {}).get('result') or {}
        pfid = {x.get('printfile_id'): x for x in liste_l(pf.get('printfiles'))}
        vpf = {x.get('variant_id'): x.get('placements') or {} for x in liste_l(pf.get('variant_printfiles'))}
        def fiy(etk):
            d = ((j(ham / f'urun_{pid}_v2_prices_{etk}.json') or {}).get('yanit') or {}).get('data')
            d = d if isinstance(d, dict) else {}
            return {v.get('id'): min((float(t['price']) for t in liste_l(v.get('techniques')) if t.get('price') not in (None, '')), default=None)
                    for v in liste_l(d.get('variants'))}
        fWW, fNA = fiy('WW'), fiy('NA')
        av = liste_l(((j(ham / f'urun_{pid}_v2_availability.json') or {}).get('yanit') or {}).get('data'))
        avm = {x.get('catalog_variant_id'): ';'.join(f"{sr.get('name')}:{sr.get('availability')}" for t in liste_l(x.get('techniques')) for sr in liste_l(t.get('selling_regions'))) for x in av}
        for i, v in enumerate(vs):
            vid = v['id']
            pl = vpf.get(vid, {})
            pfa = [(y, pfid.get(i_) or {}) for y, i_ in pl.items()]
            r = dict(urun_id=pid, urun_ad=oz['ad'], sinif=oz['sinif'], varyant_id=vid, varyant_ad=v.get('name'), boyut=v.get('size'), renk=v.get('color'),
                     malzeme=';'.join(f"{m.get('name')} {m.get('percentage')}%" for m in liste_l((vs1.get(vid) or {}).get('material'))),
                     baski=';'.join(f"{y}={x.get('width')}x{x.get('height')}@{x.get('dpi')}" for y, x in pfa),
                     baski_inc_v2=';'.join(f"{d.get('placement')}={d.get('width')}x{d.get('height')}" for d in liste_l(v.get('placement_dimensions'))),
                     cift_yuz=any(y == 'back' for y, _ in pfa), fiyat_usd_v2_WW=fWW.get(vid) if fWW.get(vid) is not None else '',
                     fiyat_usd_v2_NA=fNA.get(vid) if fNA.get(vid) is not None else '', fiyat_usd_v1=(vs1.get(vid) or {}).get('price', ''),
                     uygunluk_v2=avm.get(vid, ''))
            for u in ULKELER:
                x1, x2 = K.get((pid, vid, u, 1)), K.get((pid, vid, u, 2))
                if x1 is None:
                    r[f'{u}_ilk'] = f'sorgulanmadi (urun basina en ucuz {KARGO_VARYANT_SINIR} varyant)'
                    continue
                def ucuz(x):
                    d = (x or {}).get('yanit') or {}
                    d = d.get('data') if isinstance(d.get('data'), list) else []
                    d = [o for o in d if isinstance(o, dict) and o.get('rate') not in (None, '')]
                    return min(d, key=lambda o: float(o['rate'])) if d else None
                e1, e2 = ucuz(x1), ucuz(x2)
                if e1:
                    r[f'{u}_ilk'] = e1['rate']
                    r[f'{u}_ek'] = round(float(e2['rate']) - float(e1['rate']), 2) if e2 and e2.get('shipping') == e1.get('shipping') else ''
                    r[f'{u}_yontem'] = e1.get('shipping')
                    r[f'{u}_gun'] = f"{e1.get('min_delivery_days')}-{e1.get('max_delivery_days')}"
                    sh = liste_l(e1.get('shipments'))
                    r[f'{u}_cikis'] = ','.join(sorted({s.get('departure_country') for s in sh if s.get('departure_country')}))
                    r[f'{u}_gumruk'] = ','.join(sorted({str(s.get('customs_fees_possible')) for s in sh if 'customs_fees_possible' in s}))
                else:
                    y = (x1.get('yanit') or {})
                    m = (y.get('error') or {}).get('message') if isinstance(y.get('error'), dict) else y.get('data')
                    r[f'{u}_ilk'] = f"HATA {x1.get('http')}: {str(m)[:80]}"
            r['kaynak'] = 'Printful API (v2 catalog-variants, prices WW/NA, availability, shipping-rates; v1 products, printfiles)'
            rows.append(r)
    alan = list(dict.fromkeys(k for r in rows for k in r))
    with open(c / 'SECILEN25.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(rows)
    print('SECILEN satir', len(rows), flush=True)
    return 0


if __name__ == '__main__':
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    if m == 'liste':
        sys.exit(cmd_liste(sys.argv[2]))
    if m == 'tablo':
        sys.exit(cmd_tablo(sys.argv[2]))
    if m == 'detay':
        sys.exit(cmd_detay(sys.argv[2], sys.argv[3].split(',')))
    if m == 'secilen':
        sys.exit(cmd_secilen(sys.argv[2], sys.argv[3].split(',')))
    sys.exit(__doc__)
