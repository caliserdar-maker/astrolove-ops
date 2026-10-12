"""Fill etsy_link in PIN_METIN_234.csv with each pair's own personalized listing. READ ONLY (public GET, API key only).

Usage: python3 etsy_link.py <PIN_METIN_234.csv> <out_dir>
Match: active shop listings whose title names the two signs of the pair ("X and Y"), personalizable.
Exactly one listing per pair is required; otherwise the pair is listed as FAIL (nothing is guessed).
Writes PIN_METIN_234_LINKLI.csv, ETSY_ESLESME.csv.
"""
import csv, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts', 'etsy'))
from etsy_common import APIKeyStore, Etsy  # noqa: E402

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn',
         'Aquarius', 'Pisces']
RX = re.compile(r'\b(' + '|'.join(SIGNS) + r')\s+(?:and|&)\s+(' + '|'.join(SIGNS) + r')\b', re.I)


def main(src, out):
    os.makedirs(out, exist_ok=True)
    api = Etsy(APIKeyStore(os.environ.get('ETSY_API_KEY'), os.environ.get('ETSY_SHARED_SECRET')))
    shop = os.environ['ETSY_SHOP_ID']
    listings, off = [], 0
    while True:
        r = api.get(f'/shops/{shop}/listings/active', params={'limit': 100, 'offset': off})
        listings += r.get('results', [])
        off += 100
        if off >= r.get('count', 0):
            break
    print(f'aktif ilan {len(listings)} (kota kalan {api.remaining})')
    cand = defaultdict(list)
    for L in listings:
        m = RX.search(L.get('title') or '')
        if not m:
            continue
        key = '_'.join(sorted(s.upper() for s in m.groups()))
        cand[key].append(L)
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    pairs = sorted({r['cift_anahtari'] for r in rows})
    esl, link = [], {}
    for k in pairs:
        cs = cand.get(k, [])
        pers = [c for c in cs if c.get('is_personalizable')]
        ok = len(pers) == 1
        if ok:
            link[k] = f"https://www.etsy.com/listing/{pers[0]['listing_id']}"
        esl.append({'cift': k, 'aday': len(cs), 'kisisel_aday': len(pers), 'PASS': ok,
                    'listing_id': pers[0]['listing_id'] if ok else ' '.join(str(c['listing_id']) for c in cs),
                    'baslik': pers[0]['title'] if ok else ' || '.join(c['title'] for c in cs),
                    'etsy_link': link.get(k, '')})
    for r in rows:
        r['etsy_link'] = link.get(r['cift_anahtari'], '')
    with open(os.path.join(out, 'PIN_METIN_234_LINKLI.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out, 'ETSY_ESLESME.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, list(esl[0])); w.writeheader(); w.writerows(esl)
    nf = [e['cift'] for e in esl if not e['PASS']]
    dup = len(set(link.values())) != len(link)
    print(f'OZET LINK {len(link)}/{len(pairs)} eslesti; tekrar eden link {"VAR" if dup else "yok"}; FAIL: {" ".join(nf) or "yok"}')
    return 0 if not nf and not dup and len(pairs) == 78 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
