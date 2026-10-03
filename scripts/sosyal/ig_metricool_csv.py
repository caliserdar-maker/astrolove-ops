#!/usr/bin/env python3
"""IG + FB Metricool toplu CSV (Serdar kurallari 3 Eki 2026):
- Gunde 2 gonderi, farkli ciftlerden: gun d carousel = SIRA_78[d], Reel = SIRA_78[(d-7) mod 78].
  Ayni ciftin carousel'i ile Reel'i arasi >= 7x24 sa (kodda denetlenir).
- Saat (Metricool hesap saati Istanbul): carousel IG 18:00 / FB 18:05 (gun d); Reel IG 03:00 / FB 03:05 (gun d+1)
  = New York 11:00 / 20:00.
- IG ve FB AYRI satir. Caption cift basina tek (carousel ve Reel ayni). IG: ig_caption ("Link in bio").
  FB: fb_caption + First Comment Text = fb_first_comment. FB Reel: Facebook Title = "<Sol> & <Sag>".
- Draft=FALSE. Listing ID'ler ILAN_DOGRULA.csv'de 78/78 PASS olmali.
Kullanim: ig_metricool_csv.py --captions C.csv --sira SIRA_78.csv --ilan ILAN_DOGRULA.csv --url-kok URL
            --cikti DIR (--baslangic YYYY-MM-DD | --onizleme N) [--onek IG_FB_V1] [--metin-kurali yol]"""
import argparse, csv, importlib.util, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path

KOL = ['Text', 'Date', 'Time', 'Draft', 'Facebook', 'Instagram', 'Pinterest', 'Picture Url 1', 'Picture Url 2',
       'Picture Url 3', 'Instagram Post Type', 'Instagram Show Reel On Feed', 'Facebook Post Type', 'Facebook Title',
       'First Comment Text']
KAYDIR = 7
SAAT = {('C', 'IG'): (0, '18:00:00'), ('C', 'FB'): (0, '18:05:00'), ('R', 'IG'): (1, '03:00:00'), ('R', 'FB'): (1, '03:05:00')}


def ad(cift):
    a, b = cift.split('_')
    return f'{a.title()} & {b.title()}'


def main():
    ap = argparse.ArgumentParser()
    for k in ('captions', 'sira', 'ilan', 'url-kok', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--baslangic'); ap.add_argument('--onizleme', type=int)
    ap.add_argument('--onek', default='IG_FB_V1'); ap.add_argument('--metin-kurali')
    ap.add_argument('--min-dk', type=int, default=30)
    a = ap.parse_args()
    if bool(a.baslangic) == bool(a.onizleme):
        sys.exit('DUR: --baslangic ya da --onizleme (yalniz biri)')
    cap = {r['pair']: r for r in csv.DictReader(open(a.captions, encoding='utf-8'))}
    sira = [r['cift'] for r in sorted(csv.DictReader(open(a.sira, encoding='utf-8')), key=lambda r: int(r['sira']))]
    ilan = {r['pair']: r for r in csv.DictReader(open(a.ilan, encoding='utf-8'))}
    hata = []
    if len(sira) != 78 or set(sira) != set(cap) or len(cap) != 78:
        hata.append(f'cift kumesi uyusmuyor (sira {len(sira)}, caption {len(cap)})')
    for c in sira:
        i = ilan.get(c)
        if not i or i['sonuc'] != 'PASS' or i['listing_id'] != cap[c]['listing_id_DOGRULANMADI']:
            hata.append(f'ilan dogrulanmadi {c}')
        if not cap[c]['fb_first_comment'].endswith(f"https://www.etsy.com/listing/{cap[c]['listing_id_DOGRULANMADI']}"):
            hata.append(f'ilk yorum linki {c}')
        if 'Link in bio' not in cap[c]['ig_caption'] or 'etsy.com' in cap[c]['ig_caption']:
            hata.append(f'ig caption kurali {c}')
        if 'first comment' not in cap[c]['fb_caption'] or 'etsy.com' in cap[c]['fb_caption']:
            hata.append(f'fb caption kurali {c}')
        if len(cap[c]['ig_caption']) > 2200 or cap[c]['ig_caption'].count('#') > 30:
            hata.append(f'ig uzunluk/etiket {c}')
    MK = None
    if a.metin_kurali:
        sp = importlib.util.spec_from_file_location('mk', a.metin_kurali)
        MK = importlib.util.module_from_spec(sp); sp.loader.exec_module(MK)
    S = date.fromisoformat(a.baslangic) if a.baslangic else date(2000, 1, 1)
    out, ne_zaman = [], {}
    for d in range(78):
        for tur, c in (('C', sira[d]), ('R', sira[(d - KAYDIR) % 78])):
            u = f"{a.url_kok.rstrip('/')}/{c}"
            for ag in ('IG', 'FB'):
                g, saat = SAAT[(tur, ag)]
                t = datetime.fromisoformat(f'{S + timedelta(days=d + g)}T{saat}')
                ne_zaman.setdefault(c, {})[(tur, ag)] = t
                r = dict.fromkeys(KOL, '')
                r.update({'Text': cap[c]['ig_caption' if ag == 'IG' else 'fb_caption'],
                          'Date': f'GUN_{d + g + 1}' if a.onizleme else t.strftime('%Y-%m-%d'), 'Time': saat,
                          'Draft': 'FALSE', 'Facebook': str(ag == 'FB').upper(), 'Instagram': str(ag == 'IG').upper(),
                          'Pinterest': 'FALSE'})
                if tur == 'C':
                    r.update({f'Picture Url {k}': f'{u}/C0{k}_1080x1350.jpg' for k in (1, 2, 3)})
                else:
                    r['Picture Url 1'] = f'{u}/REEL_1080x1920_9sn.mp4'
                if ag == 'IG':
                    r['Instagram Post Type'] = 'POST' if tur == 'C' else 'REEL'
                    if tur == 'R':
                        r['Instagram Show Reel On Feed'] = 'TRUE'
                else:
                    r['Facebook Post Type'] = 'POST' if tur == 'C' else 'REEL'
                    r['First Comment Text'] = cap[c]['fb_first_comment']
                    if tur == 'R':
                        r['Facebook Title'] = ad(c)
                r['_t'] = t; r['_cift'] = c; r['_tur'] = tur
                out.append(r)
    for c, z in ne_zaman.items():
        for ag in ('IG', 'FB'):
            if abs(z[('R', ag)] - z[('C', ag)]) < timedelta(days=KAYDIR):
                hata.append(f'7 gun kurali {c} {ag}')
    gunluk = {}
    for r in out:
        gunluk.setdefault((r['_t'] - timedelta(hours=12)).date(), set()).add((r['_tur'], r['_cift']))
    for g, k in gunluk.items():
        if len(k) != 2 or len({c for _, c in k}) != 2:
            hata.append(f'gun {g}: {sorted(k)}')
    if MK:
        for r in out:
            for v in (r['Text'], r['First Comment Text'], r['Facebook Title']):
                hata += [f"metin_kurali {r['_cift']} {x}" for x in MK.denetle(v)]
    for r in out:
        for k in ('Picture Url 1', 'Picture Url 2', 'Picture Url 3'):
            if r[k] and not re.fullmatch(r'https://[\w.\-/]+\.(jpg|mp4)', r[k]):
                hata.append(f'url {r[k]}')
    out.sort(key=lambda r: r['_t'])
    if a.baslangic:
        simdi = datetime.utcnow() + timedelta(hours=3)
        if out[0]['_t'] < simdi + timedelta(minutes=a.min_dk):
            hata.append(f"ilk gonderi {out[0]['_t']} simdiden (Istanbul {simdi:%Y-%m-%d %H:%M}) {a.min_dk} dk ten yakin")
    if hata:
        sys.exit('DUR: ' + '; '.join(sorted(set(hata))[:25]))
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    if a.onizleme:
        sec = [r for r in out if r['_t'].date() < S + timedelta(days=a.onizleme)
               or (r['_tur'] == 'R' and r['_t'].date() == S + timedelta(days=a.onizleme))]
        p = Path(a.cikti) / f'{a.onek}_ONIZLEME_{a.onizleme}GUN.csv'
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['cift', 'tur'] + KOL, extrasaction='ignore', lineterminator='\n')
            w.writeheader(); w.writerows([dict(r, cift=r['_cift'], tur=r['_tur']) for r in sec])
        print(f'ONIZLEME {len(sec)} satir: {p.name}')
        return
    dosyalar = []
    for i in range(0, len(out), 50):
        p = Path(a.cikti) / f'{a.onek}_{i // 50 + 1:02d}.csv'
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=KOL, extrasaction='ignore', lineterminator='\n')
            w.writeheader(); w.writerows(out[i:i + 50])
        dosyalar.append(p.name)
    print(f"CSV {len(dosyalar)} dosya, {len(out)} satir, ilk {out[0]['Date']} {out[0]['Time']}, "
          f"son {out[-1]['Date']} {out[-1]['Time']}: {', '.join(dosyalar)}")


if __name__ == '__main__':
    main()
