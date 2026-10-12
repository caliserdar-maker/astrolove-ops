"""YouTube Shorts ve Threads: 78 cift metinleri (TASLAK) + PASS/FAIL denetimi.
Kaynak: data/sosyal/arastirma/raporlar/YOUTUBE_SHORTS_CLAUDE.md ve THREADS_CLAUDE.md."""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
S = ['Aquarius', 'Aries', 'Cancer', 'Capricorn', 'Gemini', 'Leo', 'Libra', 'Pisces', 'Sagittarius', 'Scorpio', 'Taurus', 'Virgo']
PAIRS = [(S[i], S[j]) for i in range(12) for j in range(i, 12)]
assert len(PAIRS) == 78

YT_TITLE = '{A} and {B} Compatibility Art, Two Zodiac Signs as One Symbol'
YT_DESC = ('{A} and {B}, as one? Watch the {A} and {B} zodiac signs become one shared gold symbol. '
           'This zodiac couple art adds your two names and a personal message, made by AstroLoveArt. '
           'A personalized gift idea for an anniversary, engagement or wedding. '
           'Make it yours: search AstroLoveArt on Etsy.\n\n#zodiaccompatibility #zodiaccouple #zodiacart')
YT_KATEGORI = 'HOWTO_STYLE'  # Howto & Style (YouTube 26); Serdar karari 12 Eki 2026, EDUCATION kullanilmaz
YT_TAGS = '{a} and {b} compatibility,{a} and {b},zodiac compatibility,zodiac couple art,personalized zodiac gift'
TH_TEXT = ('{A} & {B}, as one? Two zodiac signs become one shared gold symbol, with your two names and your message. '
           'Zodiac couple art by AstroLoveArt, made for you on Etsy.')
TH_TOPIC = 'Zodiac Compatibility'
TH_ALT = [
    'Slide 1. A navy background with the gold {A} sign on the left and the gold {B} sign on the right, and a gold question mark between them inside a thin gold circle. Text on the image reads: {A} & {B}, as one? Zodiac art with your names & message. Swipe to reveal.',
    'Slide 2. The {A} sign and the {B} sign in gold on navy, and one gold symbol that merges both signs. Below it, the couple\'s two names joined by an infinity sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.',
    'Slide 3. The personalized poster hanging on a cream wall. It shows the merged {A} and {B} gold symbol on navy, the two signs, the couple\'s two names and a short message.',
    'Slide 4. Close-up of the poster with the couple\'s two names under the gold {A} and {B} signs, and a short message. Text below the poster reads: Make it yours, AstroLoveArt, On Etsy.',
]
BAD = ['–', '—', '+', 'constellation', 'tarot', 'tattoo', 'wallpaper', 'friendship', 'framed', 'best seller',
       'tag your', 'comment your', 'Emily', 'James']

yt, th, err = [], [], []
for A, B in PAIRS:
    k = f'{A.upper()}_{B.upper()}'
    f = dict(A=A, B=B, a=A.lower(), b=B.lower())
    r = dict(cift_anahtari=k, baslik=YT_TITLE.format(**f), aciklama=YT_DESC.format(**f), etiketler=YT_TAGS.format(**f),
             kategori=YT_KATEGORI, made_for_kids='false', sentetik_icerik='true')
    yt.append(r)
    t = dict(cift_anahtari=k, metin=TH_TEXT.format(**f), konu_etiketi=TH_TOPIC, **{f'alt_metin_{i+1}': x.format(**f) for i, x in enumerate(TH_ALT)})
    th.append(t)
    if len(r['baslik']) > 100: err.append((k, 'yt baslik > 100'))
    if len(r['aciklama'].encode()) > 5000: err.append((k, 'yt aciklama > 5000 bayt'))
    if len(r['etiketler']) + r['etiketler'].count(' ') * 0 > 500: err.append((k, 'yt etiket > 500'))
    if r['kategori'] != 'HOWTO_STYLE': err.append((k, 'yt kategori HOWTO_STYLE degil'))
    if r['aciklama'].count('#') > 3: err.append((k, 'yt hashtag > 3'))
    if len(t['metin']) > 500: err.append((k, 'threads metin > 500'))
    if '&' in TH_TOPIC or '.' in TH_TOPIC or not 1 <= len(TH_TOPIC) <= 50: err.append((k, 'konu etiketi kurali'))
    for row in (r, t):
        for c, v in row.items():
            for w in BAD:
                if w.lower() in v.lower():
                    err.append((k, f'{c}: yasak "{w}"'))
    if A not in r['baslik'] or B not in r['baslik'] or A not in t['metin'] or B not in t['metin']: err.append((k, 'burc eksik'))

for name, rows in (('YOUTUBE_SHORTS_78.csv', yt), ('THREADS_78.csv', th)):
    with open(os.path.join(HERE, name), 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)
L = lambda rows, c: (min(len(x[c]) for x in rows), max(len(x[c]) for x in rows))
print('YT baslik', L(yt, 'baslik'), 'aciklama', L(yt, 'aciklama'), 'etiket', L(yt, 'etiketler'), '| Threads metin', L(th, 'metin'))
print('PASS' if not err else f'FAIL {len(err)}: {err[:5]}')
sys.exit(1 if err else 0)
