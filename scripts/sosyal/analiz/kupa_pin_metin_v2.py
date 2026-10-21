#!/usr/bin/env python3
"""Kupa pin metni v2 (21 Eki 2026): 78 kupa pin KURU metnindeki her urun iddiasi canli kupa ilaniyla dogrulanir. Metricool YOK.
Etsy: tek GET /listings/batch?listing_ids=<78 kupa ilani>&includes=Inventory (salt okuma, kota tabani 10;
  getListing includes Inventory kabul etmiyor, 21 Eki 1. deneme 400). Kanit:
  - her iddia 78 canli aciklamanin HEPSINDE aranan ifadeyle gecmeli (bilgi: canli aciklama = KUPA78_ORCHARD_METIN.csv satiri);
  - stil sayisi: her ilanin inventory Style (513) degerleri (etkin urunler); metinde o ilanin sayisi yazilir;
  - nazar: aciklamada "Every style ... evil eye on the back" + baski kaynagi (kupa-orchard geo_<stil>.json x8: nazar_d > 0).
Dogrulanmayan iddianin cumlesi metinden cikar; stil sayisi canli degerle yazilir.
Girdi: --once-csv KUPA_PIN_KURU.csv --once-govde KUPA_PIN_GOVDE.json --metin KUPA78_ORCHARD_METIN.csv --geo-dir DIR
       (--ilan-json ILAN.json yerel test | canli: TOKEN_FILE, ETSY_* ortam) --out OUT (ilan kimlikleri once-csv link'lerinden)
Cikti: OUT/KUPA_PIN_KURU.csv, OUT/KUPA_PIN_GOVDE.json, OUT/KUPA_METIN_DOGRULAMA.txt, OUT/ILAN_CANLI.json"""
import argparse
import csv
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

KOTA_TABAN = 10
P_STYLE, P_SIZE = 513, 514
STIL_GEO = {'Orange Blossom': 'orange', 'Purple Fig': 'fig', 'Olive Breeze': 'olive', 'Pomegranate Bloom': 'pomegranate',
            'Almond Blossom': 'almond', 'Lemon Grove': 'lemon', 'Blue Grape': 'grape', 'Golden Loquat': 'loquat'}
# iddia -> canli aciklamada aranan ifade(ler) (hepsi gecmeli)
KANIT = {'fusion': [r'one original fusion symbol'], 'on_isim': [r'Front:[^\n]*your names'], 'arka_mesaj': [r'Back: your message'],
         'buyuk_harf': [r'your names in capitals'], 'iki_yuz': [r'printed on both sides'], 'seramik': [r'Glossy white ceramic'],
         'boy': [r'11 oz \(325 ml\)', r'15 oz \(444 ml\)'], 'bulasik': [r'Dishwasher and microwave safe'],
         'siparis': [r'Made to order'], 'vesile': [r'wedding gift', r'engagement gift', r'anniversary', r'newlywed'],
         'astroloji': [r'couples who love astrology'], 'kahve': [r'custom coffee mug'], 'kisa_mesaj': [r'Message \(one line'],
         'sabah': [r'every morning'], 'nazar': [r'small nazar \(evil eye\)', r'Every style[^\n]*evil eye on the back']}
# (cumle, iddialar); {N} = canli stil sayisi ('stil' iddiasi), {NZ} = nazar parcasi
BASLIK = ('{A} and {B} Zodiac Couple Mug with Names, Personalized Coffee Mug Gift for Couples',
          '{A} and {B} Personalized Mug, Fusion Zodiac Symbol with Your Names and Message',
          '{A} and {B} Couple Mug, Custom Zodiac Gift for Wedding, Engagement or Anniversary')
BASLIK_IDDIA = (('kahve',), ('fusion', 'kisa_mesaj'), ('vesile',))
METIN = (
    [('Two signs, one shared symbol.', ()),
     ('This {A} and {B} zodiac couple mug joins your two signs into one original fusion symbol, with your names on the front '
      'and your message on the back.', ('fusion', 'on_isim', 'arka_mesaj')),
     ('Glossy white ceramic, printed on both sides, in {N} styles and two sizes, 11 oz or 15 oz.', ('seramik', 'iki_yuz', 'stil', 'boy')),
     ('Personalized zodiac couple mug by AstroLoveArt. Tap the Pin to see it on Etsy.', ())],
    [('Start the morning with your two signs.', ('sabah',)),
     ('A custom {A} and {B} coffee mug with one fusion symbol made from both zodiac signs, your two names and a short message '
      'of your own.', ('kahve', 'fusion', 'kisa_mesaj')),
     ('Choose from {N} styles, 11 oz or 15 oz, made to order.', ('stil', 'boy', 'siparis')),
     ('A personalized couple gift for a wedding, engagement, anniversary or newlyweds.', ('vesile',)),
     ('By AstroLoveArt, available on Etsy.', ())],
    [('{A} and {B} compatibility, on a mug.', ()),
     ('Your two zodiac signs become one original symbol, with your names in capitals on the front and your message{NZ} on the '
      'back.', ('fusion', 'buyuk_harf', 'arka_mesaj')),
     ('Glossy white ceramic, dishwasher and microwave safe, 11 oz or 15 oz.', ('seramik', 'bulasik', 'boy')),
     ('A zodiac gift for couples who love astrology.', ('astroloji',)),
     ('Personalized couple mug by AstroLoveArt. Tap the Pin to personalize yours on Etsy.', ())])
ALT = ('{A} and {B} zodiac couple mug with names, personalized white ceramic coffee mug with a fusion zodiac symbol',
       ('seramik', 'kahve', 'fusion'))


def norm(t):
    return re.sub(r'\s+', ' ', (t or '').replace('\r', '')).strip()


def canli_oku(ids, log):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'etsy'))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    st = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    j = api.get('/listings/batch', params={'listing_ids': ','.join(ids), 'includes': 'Inventory'})
    log(f'Etsy GET /listings/batch ({len(ids)} ilan, includes=Inventory): cagri {api.calls}, kota {api.remaining} (taban {KOTA_TABAN})')
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        log(f'DUR: kota {api.remaining} < {KOTA_TABAN} (baska cagri yok)')
    return j


def main():
    ap = argparse.ArgumentParser()
    for k in ('once-csv', 'once-govde', 'metin', 'geo-dir', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--ilan-json', default='')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rap = []

    def log(m):
        print(m, flush=True); rap.append(m)

    once = list(csv.DictReader(open(a.once_csv, encoding='utf-8')))
    govde = json.load(open(a.once_govde))
    if len(once) != 78 or len(govde) != 78:
        sys.exit(f'DUR: once {len(once)} satir / {len(govde)} govde (78 olmali)')
    ids = [r['link'].rstrip('/').rsplit('/', 1)[1] for r in once]
    j = json.load(open(a.ilan_json)) if a.ilan_json else canli_oku(ids, log)
    ilan = {str(x.get('listing_id')): x for x in (j.get('results') or [])}
    eksik = [i for i in ids if i not in ilan]
    log(f'Canli okunan ilan {len(ilan)}/78; eksik {eksik[:5]}; state {dict(Counter(x.get("state") for x in ilan.values()))}')
    M = {norm(r['baslik']): r for r in csv.DictReader(open(a.metin, encoding='utf-8'))}
    stil, csv_ayni, dog_ilan = {}, 0, {k: 0 for k in KANIT}
    adlar_ok = 0
    for i, x in ilan.items():
        desc, title = html.unescape(x.get('description') or ''), html.unescape(x.get('title') or '')
        st = set()
        for p in (x.get('inventory') or {}).get('products') or []:
            if p.get('is_deleted') or not any(o.get('is_enabled', True) for o in p.get('offerings') or [{}]):
                continue
            for pv in p.get('property_values') or []:
                if pv.get('property_id') == P_STYLE:
                    st.update(pv.get('values') or [])
        stil[i] = st
        m = re.search(r'(\d+) STYLES', desc)
        adlar = {s_ for s_ in STIL_GEO if s_ in desc}
        adlar_ok += bool(st) and m is not None and int(m.group(1)) == len(st) and adlar == st
        csv_ayni += norm(title) in M and norm(M[norm(title)]['aciklama']) == norm(desc)
        for k, ifadeler in KANIT.items():
            dog_ilan[k] += all(re.search(y, desc, re.I) for y in ifadeler)
    json.dump({i: {'state': x.get('state'), 'title': x.get('title'), 'stil': sorted(stil[i])} for i, x in ilan.items()},
              open(os.path.join(a.out, 'ILAN_CANLI.json'), 'w'), ensure_ascii=False, indent=1)
    sayilar = Counter(len(v) for v in stil.values())
    log(f'Stil (envanter, etkin urun): ilan basina stil sayisi {dict(sayilar)}; aciklamadaki "<n> STYLES" + stil adlari envanterle '
        f'ayni: {adlar_ok}/{len(ilan)}')
    log(f'Canli aciklama = KUPA78_ORCHARD_METIN.csv satiri: {csv_ayni}/{len(ilan)}')
    tam = not eksik and len(ilan) == 78
    dog = {k: tam and v == 78 for k, v in dog_ilan.items()}
    dog['stil'] = tam and all(stil.values())
    geo = {}
    for s_, g in STIL_GEO.items():
        try:
            Y = json.load(open(os.path.join(a.geo_dir, f'geo_{g}.json')))
            Y = Y.get('yerlesim', Y)
            geo[s_] = (Y.get('nazar_d') or 0) > 0 and Y.get('nazar_x') is not None
        except (OSError, ValueError):
            geo[s_] = False
    tum_stil = set().union(*stil.values()) if stil else set()
    nazar_kaynak = bool(tum_stil) and all(geo.get(s_) for s_ in tum_stil)
    log(f'Nazar: canli aciklamada {dog_ilan["nazar"]}/78; baski kaynagi (kupa-orchard geo nazar_d > 0) '
        f'{sum(geo.get(s_, False) for s_ in tum_stil)}/{len(tum_stil)} stil ({", ".join(sorted(tum_stil))})')
    dog['nazar'] = dog['nazar'] and nazar_kaynak
    log('Iddia dogrulama (78 canli ilanin hepsinde): ' + ', '.join(f'{k} {"OK" if v else "YOK"} ({dog_ilan.get(k, "-")})'
                                                                  for k, v in sorted(dog.items())))
    genel = tam

    def kur(cumleler, A, B, N):
        out, cik = [], []
        for c, idd in cumleler:
            if all(dog[i] for i in idd):
                out.append(c.format(A=A, B=B, N=N, NZ=' and a small evil eye' if dog['nazar'] else ''))
            else:
                cik.append(c[:40])
        return ' '.join(out), cik

    degisen, hata, cikan = 0, [], {}
    for r, g in zip(once, govde):
        if g['pinterestData']['pinLink'] != r['link'] or not g['publicationDate']['dateTime'].startswith(f"{r['plan_tarih']}T{r['plan_saat']}"):
            sys.exit(f"DUR: {r['cift']} CSV/govde sirasi uyusmuyor")
        A, B = re.match(r'^(\w+) and (\w+) ', r['baslik']).groups()
        j_ = int(r['sablon']) - 1
        baslik = BASLIK[j_].format(A=A, B=B) if all(dog[i] for i in BASLIK_IDDIA[j_]) else f'{A} and {B} Personalized Zodiac Couple Mug'
        N = len(stil.get(r['link'].rstrip('/').rsplit('/', 1)[1], ()))
        aciklama, cik = kur(METIN[j_], A, B, N)
        alt = ALT[0].format(A=A, B=B) if all(dog[i] for i in ALT[1]) else f'{A} and {B} personalized zodiac couple mug'
        for c in cik:
            cikan[c] = cikan.get(c, 0) + 1
        h = []
        for t in (baslik, aciklama, alt):
            if '—' in t or '–' in t or any(ch in t for ch in '+=&') or re.search(r'AstroLove(?!Art)', t):
                h.append('yasak karakter/marka')
        if len(baslik) > 100 or len(aciklama) > 500:
            h.append('uzunluk')
        if not dog['nazar'] and re.search(r'evil eye|nazar', aciklama + alt, re.I):
            h.append('nazar kaldi')
        if re.search(r'\b(\d+) styles', aciklama) and f'{N} styles' not in aciklama:
            h.append('stil sayisi')
        if (baslik, aciklama, alt) != (r['baslik'], r['aciklama'], r['alt_metin']):
            degisen += 1
        r.update(baslik=baslik, baslik_uzunluk=len(baslik), aciklama=aciklama, aciklama_uzunluk=len(aciklama), alt_metin=alt,
                 denetim='PASS' if not h else '; '.join(h))
        g['text'], g['mediaAltText'], g['pinterestData']['pinTitle'] = aciklama, [alt], baslik
        if h:
            hata.append(f"{r['cift']}: {h}")
    with open(os.path.join(a.out, 'KUPA_PIN_KURU.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(once[0]), lineterminator='\n'); w.writeheader(); w.writerows(once)
    json.dump(govde, open(os.path.join(a.out, 'KUPA_PIN_GOVDE.json'), 'w'), ensure_ascii=False, indent=1)
    log(f'Metin: {degisen}/78 pin degisti; cikan cumle: {cikan or "yok"}; nazar ifadesi kalan pin '
        f'{sum(1 for r in once if "evil eye" in r["aciklama"])}; "<n> styles" {dict(Counter(re.findall(r"(\d+) styles", " ".join(r["aciklama"] for r in once))))}; '
        f'denetim PASS {78 - len(hata)}/78; en uzun baslik {max(int(r["baslik_uzunluk"]) for r in once)}, '
        f'aciklama {max(int(r["aciklama_uzunluk"]) for r in once)}' + ''.join('\n  ' + x for x in hata[:5]))
    open(os.path.join(a.out, 'KUPA_METIN_DOGRULAMA.txt'), 'w').write('\n'.join(rap) + '\n')
    sys.exit(0 if not hata and genel else 4)


if __name__ == '__main__':
    main()
