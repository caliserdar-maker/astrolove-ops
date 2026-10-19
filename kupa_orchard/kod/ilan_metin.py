#!/usr/bin/env python3
"""Orchard kupa 78 ilan metni (Serdar onayi 19 Eki 2026). Cikti: kupa_orchard/ilan/KUPA78_ORCHARD_METIN.csv
Sutunlar eski kupa_taslak.py ile ayni: kod, baslik, baslik_kr, etiketler, kisisellestirme_talimati, talimat_kr, aciklama.
Baslik ve 13 etiket: 17 Eki Marketplace Insights olcumuyle onayli kalip (ilk etiket: "{a} and {b}", sigmazsa "{a} {b}", o da sigmazsa "wedding mugs").
Kontroller (biri bile FAIL ise CSV yazilmaz): baslik <= 140, 13 tekrarsiz etiket <= 20, talimat <= 256,
uzun/orta tire yok, "Lena" ve "Serdar" yok (ilanda isim olmaz), yer tutucu kalmamis.
Kullanim: python3 -I ilan_metin.py"""
import csv, itertools, os, re, sys

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CIKTI = os.path.join(KOK, 'ilan', 'KUPA78_ORCHARD_METIN.csv')
Z = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
CIFTLER = sorted('_'.join(sorted(p)) for p in itertools.combinations_with_replacement(Z, 2))

BASLIK = '{B1} and {B2} Personalized Mug, Zodiac Symbols with Names, Gift for Couples'
ETIKET = ['personalized mug', 'couple mug', 'custom coffee mug', 'custom name mug', 'gift for couple', 'newlywed gift',
          'zodiac mug', 'zodiac symbols', 'zodiac gift', 'astrology mug', 'evil eye mug', 'engagement mug']

TALIMAT = {
    'farkli': 'Please enter:\n1. Name for {B1} (up to 10 letters)\n2. Name for {B2} (up to 10 letters)\n'
              '3. Message (one line, up to 30 characters including spaces)\nLeave line 3 blank for: My favorite place is with you',
    'ayni': 'Please enter:\n1. Left name (up to 10 letters)\n2. Right name (up to 10 letters)\n'
            '3. Message (one line, up to 30 characters including spaces)\nLeave line 3 blank for: My favorite place is with you',
}
ISIM_SATIRI = {
    'farkli': '1. Name for {B1} (up to 10 letters)\n2. Name for {B2} (up to 10 letters)',
    'ayni': '1. Left name (up to 10 letters)\n2. Right name (up to 10 letters)',
}
ACIKLAMA = """A personalized mug for {B1} and {B2} couples: your two zodiac symbols join into one original fusion symbol, with your names and your message. A custom coffee mug and personalized couple gift made just for the two of you.

[ A GIFT FOR COUPLES ]
A wedding gift for couples who love astrology, an engagement gift for couples, an anniversary surprise or a newlywed gift. A zodiac gift for every morning.

[ WHAT YOU GET ]
One mug, printed on both sides. The cover shows its front and back.
Front: the fusion symbol, two small zodiac signs, your names in capitals joined by ∞, and your zodiac sign names.
Back: your message in italics, your names and a small nazar (evil eye).

[ 8 STYLES: THE ORCHARD WE KEEP ]
Orange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, Lemon Grove, Blue Grape or Golden Loquat. Every style of this zodiac couple mug has the same {B1} and {B2} symbol and an evil eye on the back. See photo 4.

[ TWO SIZES ]
- 11 oz (325 ml)
- 15 oz (444 ml)
Same design on both. See photo 5.

[ HOW TO PERSONALIZE ]
Write three lines in the personalization box:
{ISIM_SATIRI}
3. Message (one line, up to 30 characters including spaces and punctuation)
Leave the message blank and we print:
My favorite place is with you
Please check your spelling. See photos 3 and 6.

[ DETAILS ]
- Glossy white ceramic, white inside
- Dishwasher and microwave safe
- Made to order, just for you
- Original zodiac fusion symbols designed by AstroLoveArt

[ RETURNS ]
Every mug is personalized, so we can't accept returns or exchanges for a change of mind. If your mug arrives damaged, send us a photo within 7 days of delivery and we'll replace it at no cost.

Questions? Send us a message, we're happy to help."""

satirlar, hatalar = [], []
for i, kod in enumerate(CIFTLER, 1):
    b1, b2 = (s.title() for s in kod.split('_'))
    tur = 'ayni' if b1 == b2 else 'farkli'
    baslik = BASLIK.format(B1=b1, B2=b2)
    # ilk etiket (17 Eki onayli kural): "{a} and {b}"; 20'yi asarsa "{a} {b}"; o da asarsa "wedding mugs"
    ilk = next((e for e in (f'{b1.lower()} and {b2.lower()}', f'{b1.lower()} {b2.lower()}') if len(e) <= 20), 'wedding mugs')
    etiket = [ilk] + ETIKET
    talimat = TALIMAT[tur].format(B1=b1, B2=b2)
    aciklama = ACIKLAMA.replace('{ISIM_SATIRI}', ISIM_SATIRI[tur]).format(B1=b1, B2=b2)
    # kontroller
    tum = baslik + ' ' + ' '.join(etiket) + ' ' + talimat + ' ' + aciklama
    if len(baslik) > 140:
        hatalar.append(f'{kod}: baslik {len(baslik)} > 140')
    if len(etiket) != 13 or len(set(etiket)) != 13 or any(len(e) > 20 for e in etiket):
        hatalar.append(f'{kod}: etiket {etiket}')
    if len(talimat) > 256:
        hatalar.append(f'{kod}: talimat {len(talimat)} > 256')
    if re.search('[–—]', tum):
        hatalar.append(f'{kod}: uzun/orta tire')
    if re.search(r'lena|serdar', tum, re.I):
        hatalar.append(f'{kod}: isim (Lena/Serdar) var')
    if re.search(r'[{}]', tum):
        hatalar.append(f'{kod}: yer tutucu kalmis')
    satirlar.append({'kod': kod, 'baslik': baslik, 'baslik_kr': len(baslik), 'etiketler': ', '.join(etiket),
                     'kisisellestirme_talimati': talimat, 'talimat_kr': len(talimat), 'aciklama': aciklama})
    if i % 13 == 0 or i == len(CIFTLER):
        print(f'[{i}/{len(CIFTLER)} %{100 * i // len(CIFTLER)}] {kod}', flush=True)

if hatalar:
    print('FAIL', len(hatalar)); print('\n'.join(hatalar))
    sys.exit(1)
os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
with open(CIKTI, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0]))
    w.writeheader()
    w.writerows(satirlar)
print('PASS', len(satirlar), 'ilan | en uzun baslik', max(r['baslik_kr'] for r in satirlar), '| en uzun talimat',
      max(r['talimat_kr'] for r in satirlar), '| en uzun aciklama', max(len(r['aciklama']) for r in satirlar), '->', CIKTI)
