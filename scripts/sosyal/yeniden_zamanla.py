#!/usr/bin/env python3
"""V1_PINLER.csv'yi (ayni sira, ayni gorsel/URL/metin) yeni esikten yeniden zamanlar. Gorsel uretmez.
Kural pin_v1_uret.py ile ayni: gunde 10 slot (Istanbul), ayni cift arasi en az 7 x 24 saat.
Kullanim: yeniden_zamanla.py ESKI_PINLER.csv YENI_PINLER.csv --dk 35   (esik = simdi Istanbul + dk)"""
import argparse, csv, sys
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pin_v1_uret as P

ap = argparse.ArgumentParser(); ap.add_argument('eski'); ap.add_argument('yeni'); ap.add_argument('--dk', type=int, default=35)
a = ap.parse_args()
rows = sorted(csv.DictReader(open(a.eski, encoding='utf-8')), key=lambda r: int(r['no']))
esik = (datetime.utcnow() + timedelta(hours=3, minutes=a.dk)).replace(second=0, microsecond=0)
P.BASLANGIC = esik.date() - timedelta(days=1)
plan = P.zamanla(rows, esik)
assert len(plan) == len(rows)
with open(a.yeni, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(['no', 'Date', 'Time', 'cift', 'tip', 'url', 'board', 'title', 'description', 'alt_text', 'link'])
    for i, (d, saat, r) in enumerate(plan):
        w.writerow([i + 1, d.isoformat(), saat, r['cift'], r['tip'], r['url'], r['board'], r['title'],
                    r['description'], r['alt_text'], r['link']])
print(f'esik (Istanbul) {esik:%Y-%m-%d %H:%M}, {len(plan)} pin, ilk {plan[0][0]} {plan[0][1]}, son {plan[-1][0]} {plan[-1][1]}')
