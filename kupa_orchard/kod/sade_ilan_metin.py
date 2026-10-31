#!/usr/bin/env python3
"""Sade kupa 12 ilan metni TASLAGI, tasarim v2 (canli Orchard susleme, on tek sembol + isim, arka nazar + mesaj; 31 Eki 2026). Cikti: kupa_orchard/ilan/SADE12_METIN.csv
Kurallar: tek burc hediye ifadesi ("Cancer Gifts") baslik, aciklama ve etiketlerde birebir (Serdar 22 Eki);
marka AstroLoveArt; ilanda kisi adi yok; uzun/orta tire yok; baslik <= 140; 13 tekrarsiz etiket <= 20;
kisisellestirme talimati <= 120 (Etsy panel siniri). On yazi en fazla 12, mesaj en fazla 30 karakter, mesaj zorunlu
(sade kupa karari 30 Eki). Siparis oncesi onizleme (Serdar 28 Eki: kupa siparislerine de onizleme).
Kontrollerden biri bile FAIL ise CSV yazilmaz.
Kullanim: python3 -I sade_ilan_metin.py"""
import csv, os, re, sys

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CIKTI = os.path.join(KOK, 'ilan', 'SADE12_METIN.csv')
Z = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']

BASLIK = '{B} Gifts, Personalized {B} Zodiac Mug with Name or Date, Custom Coffee Mug, Astrology Birthday Gift for Her or Him'
ETIKET_BURC = ['{b} gifts', '{b} mug', '{b} zodiac', '{b} birthday']
ETIKET = ['zodiac mug', 'personalized mug', 'custom name mug', 'star sign mug', 'astrology mug', 'zodiac gift',
          'astrology gift', 'star sign gift', 'horoscope mug']   # 78 cift kupayla ortak etiket 5 (inceleme 31 Eki)
TALIMAT = '1. Front: name or date, printed in capitals (max 12)\n2. Back: your message, printed as typed (required, max 30)'
ACIKLAMA = """{B} gifts made personal: a mug with the {B} zodiac symbol and a name or date on the front, and your own message on the back.

[ A ZODIAC BIRTHDAY GIFT ]
A birthday gift for the {B} in your life: a friend, a partner, a mom or a dad. Or a little treat for yourself in {B} season. A zodiac gift for every morning.

[ WHAT YOU GET ]
One mug, printed on both sides.
Front: the {B} symbol in the middle and the name or date you choose below it, framed by fruit branches.
Back: matching branches, an evil eye bead (nazar) and your message in italics.

[ 8 STYLES: THE ORCHARD WE KEEP ]
Orange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, Lemon Grove, Blue Grape or Golden Loquat. Each style has its own fruit branches, and the symbol and text are printed in a matching color. See the style photos.

[ TWO SIZES ]
- 11 oz (325 ml)
- 15 oz (444 ml)
Same design on both.

[ HOW TO PERSONALIZE ]
Write two lines in the personalization box:
1. Front: a name or a date (up to 12 characters)
2. Back: your message (one line, up to 30 characters including spaces and punctuation). The message is required.
For a date, keep it short, for example 12 JUL 2025. Please use Latin letters, numbers and simple punctuation, no emoji.
Names and dates are printed in capital letters; your message is printed exactly as you type it. Long text prints smaller, and if it does not fit, we will message you before printing.
Please check your spelling. We send you a preview via Etsy Messages and print once you approve it.

[ DETAILS ]
- Glossy white ceramic, white inside
- Dishwasher and microwave safe
- Made to order, just for you
- Zodiac symbol designed by AstroLoveArt
- The fruit branch artwork was made with the help of AI tools and finished by AstroLoveArt

[ RETURNS ]
Every mug is personalized, so we can't accept returns or exchanges for a change of mind. If your mug arrives damaged, send us a photo within 7 days of delivery and we'll replace it at no cost.

Questions? Send us a message, we're happy to help."""

satirlar, hatalar = [], []
for i, kod in enumerate(Z, 1):
    B = kod.title()
    baslik = BASLIK.format(B=B)
    etiket = [e.format(b=B.lower()) for e in ETIKET_BURC] + ETIKET
    aciklama = ACIKLAMA.format(B=B)
    tum = baslik + ' ' + ' '.join(etiket) + ' ' + TALIMAT + ' ' + aciklama
    if len(baslik) > 140:
        hatalar.append(f'{kod}: baslik {len(baslik)} > 140')
    if len(etiket) != 13 or len(set(etiket)) != 13 or any(len(e) > 20 for e in etiket):
        hatalar.append(f'{kod}: etiket {[(e, len(e)) for e in etiket if len(e) > 20] or etiket}')
    if len(TALIMAT) > 120:
        hatalar.append(f'{kod}: talimat {len(TALIMAT)} > 120')
    if re.search(rf'{B} (?!Gifts)\w+ Gifts', baslik):
        hatalar.append(f'{kod}: burc ile Gifts arasinda kelime')
    if f'{B} Gifts' not in baslik or f'{B.lower()} gifts' not in etiket or f'{B} gifts' not in aciklama:
        hatalar.append(f'{kod}: tek burc hediye ifadesi eksik')
    if re.search('[–—]', tum):
        hatalar.append(f'{kod}: uzun/orta tire')
    if re.search(r'lena|serdar', tum, re.I):
        hatalar.append(f'{kod}: kisi adi var')
    if re.search(r'astrolove(?!art)', tum, re.I):
        hatalar.append(f'{kod}: marka AstroLoveArt degil')
    if re.search(r'[{}]', tum):
        hatalar.append(f'{kod}: yer tutucu kalmis')
    satirlar.append({'kod': kod, 'baslik': baslik, 'baslik_kr': len(baslik), 'etiketler': ', '.join(etiket),
                     'kisisellestirme_talimati': TALIMAT, 'talimat_kr': len(TALIMAT), 'aciklama': aciklama})
    print(f'[{i}/{len(Z)} %{100 * i // len(Z)}] {kod} baslik {len(baslik)}', flush=True)

if hatalar:
    print('FAIL', len(hatalar)); print('\n'.join(hatalar))
    sys.exit(1)
os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
with open(CIKTI, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0]))
    w.writeheader()
    w.writerows(satirlar)
print('PASS', len(satirlar), 'ilan | en uzun baslik', max(r['baslik_kr'] for r in satirlar), '| talimat', len(TALIMAT),
      '| en uzun aciklama', max(len(r['aciklama']) for r in satirlar), '->', CIKTI)
