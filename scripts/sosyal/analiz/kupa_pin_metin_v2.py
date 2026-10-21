#!/usr/bin/env python3
"""Kupa pin metni v2 (21 Eki 2026): 78 kupa pin KURU metnindeki her urun iddiasi canli kupa ilaniyla dogrulanir. Metricool YOK.
Etsy: tek GET /listings/<id>?includes=Inventory (salt okuma, kota tabani 10). Kanit:
  - canli aciklama (her iddia icin aranan ifade), canli aciklama = KUPA78_ORCHARD_METIN.csv satiri (bosluk normalize),
    78 CSV aciklamasinin iddia satirlari ayni (yalniz kisisellestirme satiri farkli) -> 78 ilana genellenir;
  - stil sayisi: inventory Style (513) degerleri (etkin urunler), aciklamadaki "<n> STYLES" ve 8 stil adi;
  - nazar: aciklamada "Every style ... evil eye on the back" + baski kaynagi (kupa-orchard geo_<stil>.json x8: nazar_d > 0).
Dogrulanmayan iddianin cumlesi metinden cikar; stil sayisi canli degerle yazilir.
Girdi: --once-csv KUPA_PIN_KURU.csv --once-govde KUPA_PIN_GOVDE.json --metin KUPA78_ORCHARD_METIN.csv --geo-dir DIR
       (--ilan-json ILAN.json yerel test | canli: TOKEN_FILE, ETSY_* ortam) --listing ID --out OUT
Cikti: OUT/KUPA_PIN_KURU.csv, OUT/KUPA_PIN_GOVDE.json, OUT/KUPA_METIN_DOGRULAMA.txt, OUT/ILAN_CANLI.json"""
import argparse
import csv
import html
import json
import os
import re
import sys
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


def canli_oku(listing, log):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'etsy'))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    st = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    j = api.get(f'/listings/{listing}', params={'includes': 'Inventory'})
    log(f'Etsy GET /listings/{listing}?includes=Inventory: cagri {api.calls}, kota {api.remaining} (taban {KOTA_TABAN})')
    if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
        log(f'DUR: kota {api.remaining} < {KOTA_TABAN} (baska cagri yok)')
    return j


def main():
    ap = argparse.ArgumentParser()
    for k in ('once-csv', 'once-govde', 'metin', 'geo-dir', 'listing', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--ilan-json', default='')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rap = []

    def log(m):
        print(m, flush=True); rap.append(m)

    j = json.load(open(a.ilan_json)) if a.ilan_json else canli_oku(a.listing, log)
    desc, title, state = html.unescape(j.get('description') or ''), html.unescape(j.get('title') or ''), j.get('state')
    inv = j.get('inventory') or {}
    stil, boy = set(), set()
    for p in inv.get('products') or []:
        if p.get('is_deleted') or not any(o.get('is_enabled', True) for o in p.get('offerings') or [{}]):
            continue
        for pv in p.get('property_values') or []:
            (stil if pv.get('property_id') == P_STYLE else boy if pv.get('property_id') == P_SIZE else set()).update(pv.get('values') or [])
    json.dump({'listing_id': j.get('listing_id'), 'state': state, 'title': title, 'description': desc,
               'stil_degerleri': sorted(stil), 'boy_degerleri': sorted(boy), 'urun_sayisi': len(inv.get('products') or [])},
              open(os.path.join(a.out, 'ILAN_CANLI.json'), 'w'), ensure_ascii=False, indent=1)
    log(f'Canli ilan {j.get("listing_id")} state {state}: "{title}"')
    log(f'Inventory: {len(inv.get("products") or [])} urun; Style ({len(stil)}): {", ".join(sorted(stil))}; Size: {", ".join(sorted(boy))}')

    # canli aciklama = CSV satiri, CSV iddia satirlari 78'de ayni
    M = list(csv.DictReader(open(a.metin, encoding='utf-8')))
    kod = next((r['kod'] for r in M if norm(r['baslik']) == norm(title)), None)
    csv_ayni = kod is not None and norm(next(r['aciklama'] for r in M if r['kod'] == kod)) == norm(desc)
    Z = r'(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)'
    kalip = {re.sub(Z, 'X', '\n'.join(l for l in r['aciklama'].splitlines() if not re.match(r'^[12]\. ', l))) for r in M}
    log(f'Canli aciklama = CSV ({kod}) satiri: {"EVET" if csv_ayni else "HAYIR"}; 78 CSV aciklamasinda iddia kalibi sayisi '
        f'(kisisellestirme satirlari haric): {len(kalip)}')
    genel = csv_ayni and len(kalip) == 1

    dog = {}
    for ad, ifadeler in KANIT.items():
        dog[ad] = all(re.search(x, desc, re.I) for x in ifadeler)
    m = re.search(r'(\d+) STYLES', desc)
    n_desc = int(m.group(1)) if m else None
    adlar = [s for s in STIL_GEO if s in desc]
    # stil sayisi envanterden (alicinin secebildigi); aciklama ile uyum ayrica raporlanir
    dog['stil'] = bool(stil)
    log(f'Stil: envanter {len(stil)}, aciklama "{n_desc} STYLES", aciklamadaki stil adlari {len(adlar)}; uyum '
        f'{"EVET" if len(stil) == n_desc == len(adlar) and set(stil) == set(adlar) else "HAYIR"}')
    dog['boy'] = dog['boy'] and any('11' in b for b in boy) and any('15' in b for b in boy)
    geo = {}
    for s, g in STIL_GEO.items():
        try:
            Y = json.load(open(os.path.join(a.geo_dir, f'geo_{g}.json')))
            Y = Y.get('yerlesim', Y)
            geo[s] = (Y.get('nazar_d') or 0) > 0 and Y.get('nazar_x') is not None
        except (OSError, ValueError):
            geo[s] = False
    nazar_kaynak = all(geo.get(s) for s in stil) and len(stil) > 0
    log(f'Nazar: aciklama {"VAR" if dog["nazar"] else "YOK"}; baski kaynagi (geo nazar_d > 0) '
        f'{sum(geo.get(s, False) for s in stil)}/{len(stil)} stil')
    dog['nazar'] = dog['nazar'] and nazar_kaynak
    if not genel:
        log('UYARI: canli metin 78 ilana genellenemedi; tum urun iddialari dogrulanmamis sayilir')
        dog = {k: False for k in dog}
    N = len(stil)
    log('Iddia dogrulama: ' + ', '.join(f'{k} {"OK" if v else "YOK"}' for k, v in sorted(dog.items())))

    def kur(cumleler, A, B):
        out, cik = [], []
        for c, idd in cumleler:
            if all(dog[i] for i in idd):
                out.append(c.format(A=A, B=B, N=N, NZ=' and a small evil eye' if dog['nazar'] else ''))
            else:
                cik.append(c[:40])
        return ' '.join(out), cik

    once = list(csv.DictReader(open(a.once_csv, encoding='utf-8')))
    govde = json.load(open(a.once_govde))
    if len(once) != 78 or len(govde) != 78:
        sys.exit(f'DUR: once {len(once)} satir / {len(govde)} govde (78 olmali)')
    degisen, hata, cikan = 0, [], {}
    for r, g in zip(once, govde):
        if g['pinterestData']['pinLink'] != r['link'] or not g['publicationDate']['dateTime'].startswith(f"{r['plan_tarih']}T{r['plan_saat']}"):
            sys.exit(f"DUR: {r['cift']} CSV/govde sirasi uyusmuyor")
        A, B = re.match(r'^(\w+) and (\w+) ', r['baslik']).groups()
        j_ = int(r['sablon']) - 1
        baslik = BASLIK[j_].format(A=A, B=B) if all(dog[i] for i in BASLIK_IDDIA[j_]) else f'{A} and {B} Personalized Zodiac Couple Mug'
        aciklama, cik = kur(METIN[j_], A, B)
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
        if re.search(r'\b8 styles', aciklama) and N != 8:
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
        f'{sum(1 for r in once if "evil eye" in r["aciklama"])}; "{N} styles" gecen {sum(1 for r in once if f"{N} styles" in r["aciklama"])}; '
        f'denetim PASS {78 - len(hata)}/78; en uzun baslik {max(int(r["baslik_uzunluk"]) for r in once)}, '
        f'aciklama {max(int(r["aciklama_uzunluk"]) for r in once)}' + ''.join('\n  ' + x for x in hata[:5]))
    open(os.path.join(a.out, 'KUPA_METIN_DOGRULAMA.txt'), 'w').write('\n'.join(rap) + '\n')
    sys.exit(0 if not hata and genel else 4)


if __name__ == '__main__':
    main()
