#!/usr/bin/env python3
"""Pinterest 78 cift x 4 pin (poster, kart, altin, video) x 2 surum (sevgililer / genel) = 624 metin satiri + kapi.
Dayanak: KARARLAR_20261125_49/_50/_51/_57; Serdar 25 Kas ABD kitlesi onayi (Merkez aktarimi, RAPOR_SOSYAL_ABD_DENETIM_20261125):
  1) baslik alici terimiyle baslar ve cift basina donusumlu (or. "Aries and Scorpio Gift for Couples, Personalized Zodiac Wall Art
     with Names"); 312 baslik ayni kalipla baslamaz.
  2) aciklamada "gift for boyfriend, girlfriend, husband or wife" + iki burc adi; donem ifadesi (Valentine) yalniz metinde ve yalniz
     sevgililer surumunde.
  3) dil English (US).
Olgular (eski sablon + onayli v6 metinleri; canli ilanla DOGRULANMADI): 5 renk, mesaj <= 35 karakter, dijital dosya ya da baski,
Etsy Messages ile onizleme. Link: https://astroloveart.etsy.com/listing/<id> (Share & Save, KARARLAR_20261125_57).
Kapilar (PASS/FAIL): sevgililer_metin.tara (etsy_common.METIN_KESIN + free / fiyat / tarih-kargo vaadi / AstroLove marka) tum alanlarda;
baslik <= 100, aciklama <= 500, alt metin <= 500; baslik "<A> and <B> " + alici terimi ile baslar; 312 baslik benzersiz; ayni
baslangic kalibi (adlardan sonraki ilk 3 kelime) en cok %20; aciklamada alici ifadesi + iki burc adi; aranan terim; genel surumde
Valentine / 14 Feb yok (metin + pano); kopya cumle: AYNI CIFTIN 4 pininde (ayni surum) 12+ kelimelik ortak dizi yok ve 312 aciklama
benzersiz (312 pin geneli sablon metin: sevgililer_metin'in set geneli kopya kapisi bu kapsamda uygulanamaz, rapor); ABD yazimi (colour/personalised/
favourite yok); uzun/orta tire yok (METIN_KESIN).
Kullanim: pin78_metin.py --cikti METIN.csv [--oz-test]
"""
import argparse, csv, os, re, sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'scripts', 'sosyal'))
import sevgililer_metin as SM   # noqa: E402

TURLER = ('poster', 'kart', 'altin', 'video')
ALICI_IFADE = 'gift for boyfriend, girlfriend, husband or wife'
ALICI_BAS = {   # baslikta adlardan hemen sonra gelen alici terimi (donusumlu)
    'sevgililer': ["Valentine's Day Gift for Couples", 'Gift for Couples', 'Valentine Gift for Him or Her', 'Couple Gift',
                   'Gift for Boyfriend or Girlfriend', "Valentine's Gift for Husband or Wife", 'Anniversary Gift for Couples',
                   'Zodiac Gift for Her or Him'],
    'genel': ['Gift for Couples', 'Couple Gift', 'Gift for Boyfriend or Girlfriend', 'Gift for Husband or Wife', 'Anniversary Gift for Couples',
              'Zodiac Gift for Her or Him', 'Engagement Gift for Couples', 'Wedding Gift for a Zodiac Couple'],
}
NITELIK = {
    'poster': ['Personalized Zodiac Wall Art with Names', 'Custom Astrology Poster with Your Names', 'Combined Zodiac Symbol Print'],
    'kart': ['Two Signs as One Symbol', 'Combined Zodiac Symbol Art', 'Zodiac Compatibility Art'],
    'altin': ['Gold Combined Zodiac Symbol Print', 'Gold Zodiac Couple Wall Art', 'Personalized Gold Zodiac Art'],
    'video': ['Watch Two Signs Become One', 'Combined Zodiac Symbol Wall Art', 'Personalized Zodiac Couple Art'],
}
DONEM = {'sevgililer': ["for Valentine's Day", 'this Valentine season', "for Valentine's Day or an anniversary"],
         'genel': ['for an anniversary', 'for a wedding or engagement', 'for a birthday or anniversary']}
GIRIS = {   # her cumle bir degisken (burc adi / renk / donem) icerir: 12 kelimelik sabit dizi olusmaz
    'poster': ['{A} and {B} as one gold symbol on Midnight Blue.',
               'A {A} and {B} poster: both signs become one gold symbol.',
               'Your {A} and {B} signs, joined into one gold symbol.'],
    'kart': ['How {A} and {B} look as one: both signs drawn into a single combined zodiac symbol.',
             'The {A} sign and the {B} sign, joined into one shared symbol for your zodiac compatibility.',
             'One symbol for a {A} and {B} couple, drawn from both signs.'],
    'altin': ['A close look at the gold {A} and {B} combined zodiac symbol.',
              'Gold {A} and {B} combined symbol, up close, with both sign glyphs below.',
              'The {A} and {B} symbol in gold detail, the way it looks on your poster.'],
    'video': ['Watch {A} and {B} turn into one combined zodiac symbol.',
              'A short look at the {A} and {B} combined symbol and how it looks on a wall.',
              'See the {A} and {B} combined zodiac symbol come together in gold.'],
}
# 4 varyant: ayni ciftin 4 pini (ayni surum) hep farkli cumle alir (indeks (i + k) % 4)
ALICI_CUMLE = ['A personalized {A} and {B} {ifade}, {donem}.', '{Donem}, a {ifade}: {A} and {B} in one symbol.',
               'Looking for a {ifade}? This {A} and {B} design works {donem}.',
               'Your {A} and {B} pairing makes a thoughtful {ifade} {donem}.']
OLGU = ['Add two names and a message up to 35 characters.', 'Your two names and a message (up to 35 characters) go below.',
        'Both names and a short message, up to 35 characters.', 'Two names plus your message, 35 characters at most.']
TERIM_CUMLE = ['Among our astrology gift ideas for couples: digital file or print, 5 colors.',
               'Digital file or print in 5 colors; zodiac couple wall art by AstroLoveArt.',
               'One of our astrology gift ideas for couples, in 5 colors, digital or printed.',
               'Zodiac couple wall art in 5 colors, as a digital file or a print.']
KAPANIS = {'poster': 'We send a preview via Etsy Messages before we print or prepare your file.',
           'kart': 'You get a preview via Etsy Messages before your file or print is made.',
           'altin': 'A preview comes via Etsy Messages before we prepare your file or your print.',
           'video': 'We share a preview via Etsy Messages before anything is printed or sent.'}
ALT = {'poster': '{A} and {B} combined zodiac symbol poster in Midnight Blue with gold lines, both small sign symbols and two sample '
                 'names, under the title {AU} & {BU} Combined Zodiac Symbol and the line Add your names',
       'kart': '{A} and {B} signs on a cream background joining through a curved line into one combined zodiac symbol, dark lines, '
               'title {A} and {B} with the gold AstroLoveArt infinity logo between them',
       'altin': 'Close-up of the gold {A} and {B} combined zodiac symbol on navy, with the small {A} and {B} sign symbols, a gold '
                'infinity logo and the sign names {AU} and {BU}, under the title {AU} & {BU} Combined Zodiac Symbol',
       'video': 'Short video: the gold {A} and {B} combined zodiac symbol on navy, the poster on a wall, an end card that says '
                'Make it yours, AstroLoveArt, On Etsy, and back to the gold symbol'}
DOSYA = {'poster': '{s}-poster.jpg', 'kart': '{s}-kart.jpg', 'altin': '{s}-altin.jpg', 'video': '{s}-pin-video.mp4'}
PANO = {('poster', 'sevgililer'): ("Valentine's Day Gifts for Couples", 'Posters'), ('video', 'sevgililer'): ("Valentine's Day Gifts for Couples", 'Videos'),
        ('poster', 'genel'): ('Wedding and Engagement Gifts', ''), ('video', 'genel'): ('Wedding and Engagement Gifts', '')}
for _s in ('sevgililer', 'genel'):
    PANO[('kart', _s)] = ('Zodiac Compatibility Art', 'Combined Symbol Cards'); PANO[('altin', _s)] = ('Astrology Wall Art and Home Decor', '')
BILGI = {}
UK = r'\b(colour|colours|personalised|favourite|centre|jewellery|grey)\b'


def ciftler():
    return [(r['cift'], r['listing_id'], r['a'], r['b']) for r in csv.DictReader(open(os.path.join(KOK, 'data/pod/pod78_ids.csv'), encoding='utf-8'))]


def uret():
    out = []
    for i, (c, lid, A, B) in enumerate(ciftler()):
        s = f'{A.lower()}-and-{B.lower()}'
        for k, tur in enumerate(TURLER):
            for sur in ('sevgililer', 'genel'):
                al = ALICI_BAS[sur][(i + 3 * k) % len(ALICI_BAS[sur])]
                for d_ in range(3):                         # 100 karakteri asarsa siradaki nitelik
                    ni = NITELIK[tur][(i + k + d_) % 3]; baslik = f'{A} and {B} {al}, {ni}'
                    if len(baslik) <= 100:
                        break
                v = (i + k) % 3
                don = DONEM[sur][(i + 2 * k) % 3]
                q = (i + k) % 4
                ac = ' '.join([GIRIS[tur][v], ALICI_CUMLE[q].format(A=A, B=B, ifade=ALICI_IFADE, donem=don, Donem=don[0].upper() + don[1:]),
                               OLGU[q], TERIM_CUMLE[(q + 1) % 4], KAPANIS[tur]]).format(A=A, B=B)
                out.append({'konsept': tur, 'surum': sur, 'cift': c, 'dosya': DOSYA[tur].format(s=s),
                            'pano': PANO[(tur, sur)][0], 'pano_bolumu': PANO[(tur, sur)][1],
                            'link': f'https://astroloveart.etsy.com/listing/{lid}', 'baslik': baslik, 'aciklama': ac,
                            'alt_metin': ALT[tur].format(A=A, B=B, AU=A.upper(), BU=B.upper()), 'dil': 'en-US'})
    return out


def kontrol(rows, tam=True):
    S = []
    for r in rows:
        k = f"{r['konsept']} {r['surum']} {r['cift']}"
        a, b = (w.capitalize() for w in r['cift'].split('_'))
        S.append((f'{k} baslik <= 100', len(r['baslik']) <= 100, len(r['baslik'])))
        S.append((f'{k} aciklama <= 500', len(r['aciklama']) <= 500, len(r['aciklama'])))
        S.append((f'{k} alt metin <= 500', len(r['alt_metin']) <= 500, len(r['alt_metin'])))
        bas = f'{a} and {b} '
        S.append((f'{k} baslik adlar + alici terimi ile baslar', r['baslik'].startswith(bas) and
                  any(r['baslik'][len(bas):].startswith(x) for x in ALICI_BAS[r['surum']]), r['baslik'][:60]))
        S.append((f'{k} aciklamada alici ifadesi', ALICI_IFADE in r['aciklama'].lower(), ''))
        S.append((f'{k} aciklamada iki burc adi', a in r['aciklama'] and b in r['aciklama'], ''))
        S.append((f'{k} link (Share & Save)', re.fullmatch(SM.LINK_RX, r['link']) is not None, r['link']))
        S.append((f'{k} aranan terim', any(t in r['aciklama'].lower() for t in SM.TERIM), ''))
        for alan in ('baslik', 'aciklama', 'alt_metin'):
            y = SM.tara(r[alan]); S.append((f'{k} {alan} yasak yok', not y, y))
            u = re.findall(UK, r[alan], re.I); S.append((f'{k} {alan} ABD yazimi', not u, u))
        if r['surum'] == 'genel':
            v = re.findall(r'valentine|14 feb', ' '.join((r['baslik'], r['aciklama'], r['alt_metin'], r['pano'], r['pano_bolumu'])), re.I)
            S.append((f'{k} genel surumde Sevgililer yok', not v, v))
        v = re.findall(r'valentine', r['alt_metin'], re.I)
        S.append((f'{k} alt metinde donem ifadesi yok (gorselde yok)', not v, v))
    if tam:
        for sur in ('sevgililer', 'genel'):
            R = [r for r in rows if r['surum'] == sur]
            bl = [r['baslik'] for r in R]
            S.append((f'{sur}: basliklar benzersiz', len(set(bl)) == len(bl), f'{len(set(bl))}/{len(bl)}'))
            kal = Counter(' '.join(r['baslik'].split(' and ', 1)[1].split()[1:4]) for r in R)
            en = kal.most_common(1)[0]
            S.append((f'{sur}: ayni baslangic kalibi <= %20', en[1] <= 0.20 * len(R), f'{en[0]} {en[1]}/{len(R)}'))
            # kopya cumle (sevgililer_metin kapisi, kapsam = bir ciftin pin seti, 25 Kas ornek kapisiyla ayni): ayni ciftin 4 pininde
            # 12+ kelimelik ortak dizi yok. 312 pin geneli: aciklamalar benzersiz ve iki aciklamanin 5 kelimelik dizi benzerligi
            # (Jaccard) bilgi olarak raporlanir (sablon metin; 312 pinde sifir ortak dizi sablonla uretilemez, kapsam raporda yazili).
            kopya = []
            for c in {r['cift'] for r in R}:
                C = [r for r in R if r['cift'] == c]; g12 = Counter()
                for r in C:
                    w = r['aciklama'].lower().split()
                    for gram in {' '.join(w[n:n + 12]) for n in range(len(w) - 11)}:
                        g12[gram] += 1
                kopya += [(c, g) for g, n in g12.items() if n > 1]
            S.append((f'{sur}: ayni ciftin pinlerinde 12+ kelimelik ortak dizi yok', not kopya, kopya[:2]))
            ac = [r['aciklama'] for r in R]
            S.append((f'{sur}: aciklamalar benzersiz', len(set(ac)) == len(ac), f'{len(set(ac))}/{len(ac)}'))
            G = [{' '.join(x.lower().split()[n:n + 5]) for n in range(len(x.split()) - 4)} for x in ac]
            mx = 0.0
            for a_ in range(len(G)):
                for b_ in range(a_ + 1, len(G)):
                    mx = max(mx, len(G[a_] & G[b_]) / len(G[a_] | G[b_]))
            BILGI[f'{sur} en yuksek 5-kelime benzerligi (Jaccard, bilgi)'] = round(mx, 3)
    return S


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cikti', required=True); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    rows = uret()
    if g.oz_test:
        ok = all(o for _, o, _ in kontrol(rows))
        r0 = rows[0]; g0 = next(r for r in rows if r['surum'] == 'genel')
        tek = {'uzun tire': dict(r0, aciklama=r0['aciklama'] + ' — x'), 'free': dict(r0, baslik=r0['baslik'][:60] + ' free'),
               'tarih': dict(r0, aciklama=r0['aciklama'] + ' Arrives by Feb 14.'), 'premium': dict(r0, aciklama=r0['aciklama'] + ' premium paper'),
               'eski kalip': dict(r0, baslik='Aquarius and Aquarius Combined Zodiac Symbol, Gift'), 'alici ifadesi yok':
               dict(r0, aciklama=r0['aciklama'].replace(ALICI_IFADE, 'gift')), 'UK yazim': dict(r0, aciklama=r0['aciklama'] + ' 5 colours'),
               'genel surumde Valentine': dict(g0, aciklama=g0['aciklama'] + " A Valentine's gift."), 'link': dict(r0, link='https://www.etsy.com/listing/1'),
               'alt metinde Valentine': dict(r0, alt_metin=r0['alt_metin'] + ' Valentine')}
        sonuc = [('bilinen PASS (624 satir)', ok)] + [(f'FAIL: {ad}', not all(o for _, o, _ in kontrol([r], tam=False))) for ad, r in tek.items()]
        ay = [dict(r) for r in rows]
        for r in ay:
            if r['surum'] == 'sevgililer':
                r['baslik'] = r['baslik'].split(',')[0].rsplit(' and ', 1)[0] + ' and ' + r['cift'].split('_')[1].capitalize() + ' Gift for Couples, X'
        sonuc.append(('FAIL: tum basliklar ayni kalip', not all(o for _, o, _ in kontrol(ay))))
        ko = [dict(r) for r in rows]; ko[8]['aciklama'] = ko[0]['aciklama']
        sonuc.append(('FAIL: kopya aciklama', not all(o for _, o, _ in kontrol(ko))))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    with open(g.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    S = kontrol(rows)
    bad = [s for s in S if not s[1]]
    for ad, o, d in bad[:40]:
        print(f'FAIL {ad} | {d}')
    print(f'KAPI {len(S) - len(bad)}/{len(S)} PASS; satir {len(rows)}; BILGI {BILGI}')
    sys.exit(0 if not bad else 1)


if __name__ == '__main__':
    main()
