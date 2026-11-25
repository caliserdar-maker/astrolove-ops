#!/usr/bin/env python3
"""Sevgililer pin metin kapisi (25 Kas 2026). Girdi: data/sosyal/pinterest/sevgililer/ORNEK_METIN_*.csv
Kapilar (PASS/FAIL), her satir: baslik <= 100, aciklama <= 500, alt metin <= 500 (Pinterest 100/800; 500 bizim siniri);
etsy_common.METIN_KESIN (tek kaynak: tire, premium, long-lasting, kagit/tedarikci adi ...) + "free" + fiyat ($, USD) +
kesin tarih/sure vaadi ("by Feb", "February 14", "within N hours/days", "arrives", "guaranteed"); marka "AstroLove" yalniz
"AstroLoveArt" olarak; baslik "<A> and <B> Combined Zodiac Symbol" kalibiyla baslar (PINLER_ORNEK kalibi); link
https://astroloveart.etsy.com/listing/<rakam> (Share & Save); ayni setteki aciklamalarda 12+ kelimelik ortak dizi yok (kopya cumle).
Set geneli: aranan terimlerden en az biri her aciklamada ("zodiac couple wall art", "astrology gift ideas for couples",
"zodiac compatibility"). --oz-test: bilinen PASS (gercek dosya) + bilinen FAIL satirlari.
"""
import csv, os, re, sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'scripts', 'etsy'))
from etsy_common import METIN_KESIN  # noqa: E402

EK = [('free', r'\bfree\b'), ('fiyat', r'\$\s*\d|\bUSD\b'),
      ('tarih/sure vaadi', r'\bby\s+(?:feb|february|valentine)|\bfebruary\s+\d|\bfeb\s+\d|\bwithin\s+\d+\s+(?:hours?|days?)\b|\barrives?\b|\bguarantee'
      r'|\bin\s+time\s+for\b|\bships?\s+(?:in|within)\b|\bnext[\s-]day\b|\bfast\s+(?:delivery|shipping)\b|\bexpress\b|\bovernight\b'),
      ('marka AstroLove (Art yok)', r'\bAstroLove(?!Art)\b')]
LINK_RX = r'https://astroloveart\.etsy\.com/listing/\d+'
TERIM = ['zodiac couple wall art', 'astrology gift ideas for couples', 'zodiac compatibility']


def tara(m):
    return [ad for ad, rx in list(METIN_KESIN) + EK if re.search(rx, m, re.I)]


def kontrol(rows):
    S = []
    for r in rows:
        k = f"{r['konsept']} {r['cift']}"
        a, b = (w.capitalize() for w in r['cift'].split('_'))
        S.append((f'{k} baslik <= 100', len(r['baslik']) <= 100, len(r['baslik'])))
        S.append((f'{k} aciklama <= 500', len(r['aciklama']) <= 500, len(r['aciklama'])))
        S.append((f'{k} alt metin <= 500', len(r['alt_metin']) <= 500, len(r['alt_metin'])))
        S.append((f'{k} baslik kalibi', r['baslik'].startswith(f'{a} and {b} Combined Zodiac Symbol'), r['baslik'][:45]))
        # Share & Save (Serdar 25 Kas, KARARLAR_20261125_57): magaza alt alan adi + ilan no; Etsy: uygun linkler shopname.etsy.com bicimi
        S.append((f'{k} link bicimi (Share & Save)', re.fullmatch(LINK_RX, r['link']) is not None, r['link']))
        for alan in ('baslik', 'aciklama', 'alt_metin'):
            y = tara(r[alan]); S.append((f'{k} {alan} yasak yok', not y, y))
        S.append((f'{k} aranan terim', any(t in r['aciklama'].lower() for t in TERIM), ''))
    for r in rows:   # genel (Subat sonrasi) surumde Sevgililer ifadesi yok
        if r.get('surum') == 'genel':
            v = re.findall(r"valentine|14 feb", ' '.join((r['baslik'], r['aciklama'], r['alt_metin'], r.get('pano', ''), r.get('pano_bolumu', ''))), re.I)
            S.append((f"{r['konsept']} {r['cift']} genel surumde Sevgililer yok", not v, v))
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i].get('surum', '') != rows[j].get('surum', ''):
                continue          # ayni pinin iki surumu (Sevgililer / genel) birbirinin yerine kullanilir, kopya sayilmaz
            wi, wj = rows[i]['aciklama'].lower().split(), rows[j]['aciklama'].lower().split()
            gi = {' '.join(wi[n:n + 12]) for n in range(len(wi) - 11)}
            ort = [g for g in (' '.join(wj[n:n + 12]) for n in range(len(wj) - 11)) if g in gi]
            S.append((f"kopya cumle yok {rows[i]['konsept']} / {rows[j]['konsept']}", not ort, ort[:1]))
    return S


def main():
    if len(sys.argv) < 2:
        sys.exit('kullanim: sevgililer_metin.py METIN.csv [--oz-test]')
    rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
    if '--oz-test' in sys.argv:
        ok = all(o for _, o, _ in kontrol(rows))
        kotu = dict(rows[0])
        testler = {'uzun tire': dict(kotu, aciklama=kotu['aciklama'] + ' — x'), 'free': dict(kotu, baslik=kotu['baslik'] + ' free'),
                   'tarih': dict(kotu, aciklama='Arrives by Feb 14.'), 'zamaninda': dict(kotu, aciklama='In time for Valentine.'),
                   'kargo': dict(kotu, aciklama='Ships in 2 days.'), 'ertesi gun': dict(kotu, aciklama='Next day delivery.'),
                   'hizli': dict(kotu, aciklama='Fast shipping.'), 'uzunluk': dict(kotu, aciklama='a ' * 300),
                   'marka': dict(kotu, alt_metin='AstroLove poster'), 'kalip': dict(kotu, baslik='Valentine gift'),
                   'link': dict(kotu, link='https://www.etsy.com/listing/1'), 'premium': dict(kotu, aciklama='premium paper')}
        sonuc = [('bilinen PASS', ok)] + [(f'FAIL: {ad}', not all(o for _, o, _ in kontrol([r]))) for ad, r in testler.items()]
        if any(r.get('surum') == 'genel' for r in rows):
            gr = next(r for r in rows if r.get('surum') == 'genel')
            sonuc.append(('FAIL: genel surum Sevgililer panosunda', not all(o for _, o, _ in kontrol([dict(gr, pano="Valentine's Day Gifts for Couples")]))))
            sonuc.append(('FAIL: genel surumde Valentine', not all(o for _, o, _ in kontrol([dict(gr, aciklama=gr['aciklama'] + " A Valentine's gift.")]))))
        sonuc.append(('FAIL: kopya cumle', not all(o for _, o, _ in kontrol([rows[0], dict(rows[1], aciklama=rows[0]['aciklama'])]))))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    S = kontrol(rows)
    for ad, o, d in S:
        print(f"{'PASS' if o else 'FAIL'} {ad} | {d}")
    sys.exit(0 if all(o for _, o, _ in S) else 1)


if __name__ == '__main__':
    main()
