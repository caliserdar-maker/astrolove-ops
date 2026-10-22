"""Rewrite PIN_METIN_234_LINKLI.csv from the current PIN_METIN_234.csv, keeping the already matched etsy_link per pair.
No Etsy call. PASS/FAIL: 234 rows, 78 pairs, every row linked, link per pair identical to the old file,
every row of a Cancer pair has 'Cancerian' in aciklama and no other row has it.

Usage: python3 link_birlestir.py <PIN_METIN_234.csv> <old PIN_METIN_234_LINKLI.csv> <out csv>
"""
import csv, sys


def main(src, old, out):
    oldr = list(csv.DictReader(open(old, encoding='utf-8')))
    link = {}
    for r in oldr:
        if link.setdefault(r['cift_anahtari'], r['etsy_link']) != r['etsy_link']:
            raise SystemExit(f"HATA eski dosyada {r['cift_anahtari']} icin birden fazla link")
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    for r in rows:
        r['etsy_link'] = link.get(r['cift_anahtari'], '')
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    pairs = {r['cift_anahtari'] for r in rows}
    bos = [r['cift_anahtari'] + '/' + r['pin'] for r in rows if not r['etsy_link'].startswith('https://www.etsy.com/listing/')]
    can = [r for r in rows if 'CANCER' in r['cift_anahtari'].split('_')]
    can_eksik = [r['cift_anahtari'] + '/' + r['pin'] for r in can if 'Cancerian' not in r['aciklama']]
    fazla = [r['cift_anahtari'] + '/' + r['pin'] for r in rows if r not in can and 'Cancerian' in r['aciklama']]
    ayni = all(link[k] == link.get(k) for k in pairs) and pairs == set(link)
    ok = len(rows) == 234 and len(pairs) == 78 and not bos and not can_eksik and not fazla and ayni
    print(f"OZET LINKLI satir {len(rows)} cift {len(pairs)} linkli {len(rows) - len(bos)} | Cancer satiri {len(can)} "
          f"Cancerian {len(can) - len(can_eksik)} | baska satirda Cancerian {len(fazla)} | linkler eskiyle ayni {ayni} | "
          f"{'PASS' if ok else 'FAIL'} {' '.join(bos + can_eksik + fazla)}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
