#!/usr/bin/env python3
"""PINLER.csv (pin_v1_uret.py) -> Metricool toplu CSV'leri, dosya basi en fazla 50 satir.
Kolonlar METRICOOL.md (v4) ve Serdar'in onizlemede kabul edilen PILOT_4PIN bicimi: Time HH:MM:SS, Date YYYY-MM-DD.
Draft=FALSE, Pinterest=TRUE, Facebook/Instagram=FALSE, Shortener=FALSE, Pinterest Pin New Format=FALSE.
Kullanim: metricool_csv.py PINLER.csv CIKTI_DIR [--onek PIN_V1] [--metin-kurali yol]"""
import argparse, csv, importlib.util, re, sys
from pathlib import Path

KOL = ['Text', 'Date', 'Time', 'Draft', 'Facebook', 'Instagram', 'Pinterest', 'Picture Url 1', 'Alt text picture 1',
       'Shortener', 'Pinterest Board', 'Pinterest Pin Title', 'Pinterest Pin Link', 'Pinterest Pin New Format']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pinler'); ap.add_argument('cikti')
    ap.add_argument('--onek', default='PIN_V1'); ap.add_argument('--metin-kurali', default=None)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.pinler, encoding='utf-8')))
    hata = []
    MK = None
    if a.metin_kurali:
        spec = importlib.util.spec_from_file_location('mk', a.metin_kurali)
        MK = importlib.util.module_from_spec(spec); spec.loader.exec_module(MK)
    out = []
    for r in rows:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', r['Date']) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}', r['Time']):
            hata.append(f"bicim {r['no']}")
        if len(r['title']) > 100 or len(r['description']) > 500:
            hata.append(f"uzunluk {r['no']}")
        if not re.fullmatch(r'https://www\.etsy\.com/listing/\d{10}', r['link']):
            hata.append(f"link {r['no']}")
        if MK:
            for v in (r['title'], r['description'], r['alt_text']):
                hata += [f"metin_kurali {r['no']} {x}" for x in MK.denetle(v)]
        out.append({'Text': r['description'], 'Date': r['Date'], 'Time': r['Time'], 'Draft': 'FALSE',
                    'Facebook': 'FALSE', 'Instagram': 'FALSE', 'Pinterest': 'TRUE', 'Picture Url 1': r['url'],
                    'Alt text picture 1': r['alt_text'], 'Shortener': 'FALSE', 'Pinterest Board': r['board'],
                    'Pinterest Pin Title': r['title'], 'Pinterest Pin Link': r['link'], 'Pinterest Pin New Format': 'FALSE'})
    if hata:
        sys.exit('DUR: ' + '; '.join(hata[:20]))
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    dosyalar = []
    for i in range(0, len(out), 50):
        p = Path(a.cikti) / f'{a.onek}_{i // 50 + 1:02d}.csv'
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=KOL, lineterminator='\n'); w.writeheader(); w.writerows(out[i:i + 50])
        dosyalar.append(p.name)
    print(f"CSV {len(dosyalar)} dosya, {len(out)} satir, ilk {out[0]['Date']} {out[0]['Time']}, "
          f"son {out[-1]['Date']} {out[-1]['Time']}: {', '.join(dosyalar)}")


if __name__ == '__main__':
    main()
