#!/usr/bin/env python3
"""IG + FB Metricool toplu CSV (Serdar kurallari 3 Eki 2026):
- Gunde 2 gonderi, farkli ciftlerden: gun d carousel = SIRA_78[d], Reel = SIRA_78[(d-7) mod 78].
  Ayni ciftin carousel'i ile Reel'i arasi >= 7x24 sa (kodda denetlenir).
- Saat (Metricool hesap saati Istanbul): carousel IG 18:00 / FB 18:05 (gun d); Reel IG 03:00 / FB 03:05 (gun d+1)
  = New York 11:00 / 20:00.
- IG ve FB AYRI satir. Caption cift basina tek (carousel ve Reel ayni). IG: ig_caption ("Link in bio").
  FB: fb_caption + First Comment Text = fb_first_comment. FB Reel: Facebook Title = "<Sol> & <Sag>".
- Draft=FALSE. Listing ID'ler ILAN_DOGRULA.csv'de 78/78 PASS olmali.
- EK (Serdar 3 Eki): her Reel gununde ayni cift YouTube Short 03:10, TikTok 03:15 (ayni MP4). Aciklama = IG caption;
  "Link in bio" satiri YT'de "Shop: <etsy link>", TT'de "Find us on Etsy: AstroLoveArt"; hashtag yalniz ilk 3.
  Kolon adlari/degerleri: help.metricool.com CSV yardim sayfasi (data/sosyal/kaynak/metricool/). YT ve TT ayri dosya.
Kullanim: ig_metricool_csv.py --captions C.csv --sira SIRA_78.csv --ilan ILAN_DOGRULA.csv --url-kok URL
            --cikti DIR (--baslangic YYYY-MM-DD | --onizleme N) [--onek IG_FB_V1] [--metin-kurali yol]"""
import argparse, csv, importlib.util, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path

KOL = ['Text', 'Date', 'Time', 'Draft', 'Facebook', 'Instagram', 'Pinterest', 'Picture Url 1', 'Picture Url 2',
       'Picture Url 3', 'Instagram Post Type', 'Instagram Show Reel On Feed', 'Facebook Post Type', 'Facebook Title',
       'First Comment Text', 'TikTok', 'YouTube', 'YouTube Video Title', 'YouTube Video Type', 'YouTube Video Privacy',
       'YouTube video for kids', 'YouTube Video Category', 'YouTube Video Tags', 'YouTube Notify Subscribers',
       'TikTok disable comments', 'TikTok disable duet', 'TikTok disable stitch']
# Metricool CSV yardim sayfasi yalniz MUSIC, SPORTS, EDUCATION orneklerini veriyor; "Howto & Style" anahtari
# kimlik dogrulamali uctan (GET /v2/scheduler/catalogs/youtube/categories) okunabilir, dogrulanamadi -> belgelenmis EDUCATION.
YT_KATEGORI = 'EDUCATION'
LINK_BIO = 'Link in bio: AstroLoveArt on Etsy'
KAYDIR = 7
SAAT = {('C', 'IG'): (0, '18:00:00'), ('C', 'FB'): (0, '18:05:00'), ('R', 'IG'): (1, '03:00:00'), ('R', 'FB'): (1, '03:05:00'),
        ('R', 'YT'): (1, '03:10:00'), ('R', 'TT'): (1, '03:15:00')}
DOSYA = {'IG': 'IG_FB', 'FB': 'IG_FB', 'YT': 'YT', 'TT': 'TT'}


def kisa_metin(ig, yeni_satir):
    """IG caption: 'Link in bio' satiri -> yeni_satir, hashtag satiri -> ilk 3 etiket."""
    s = ig.split('\n')
    if s.count(LINK_BIO) != 1 or not s[-1].startswith('#'):
        raise SystemExit(f'DUR: IG caption kalibi beklenmedik: {ig[:60]}')
    s[s.index(LINK_BIO)] = yeni_satir
    s[-1] = ' '.join(s[-1].split()[:3])
    return '\n'.join(s)


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
            for ag in (('IG', 'FB') if tur == 'C' else ('IG', 'FB', 'YT', 'TT')):
                g, saat = SAAT[(tur, ag)]
                t = datetime.fromisoformat(f'{S + timedelta(days=d + g)}T{saat}')
                ne_zaman.setdefault(c, {})[(tur, ag)] = t
                r = dict.fromkeys(KOL, '')
                r.update({'Text': cap[c]['ig_caption' if ag == 'IG' else 'fb_caption'],
                          'Date': f'GUN_{d + g + 1}' if a.onizleme else t.strftime('%Y-%m-%d'), 'Time': saat,
                          'Draft': 'FALSE', 'Facebook': str(ag == 'FB').upper(), 'Instagram': str(ag == 'IG').upper(),
                          'Pinterest': 'FALSE', 'TikTok': str(ag == 'TT').upper(), 'YouTube': str(ag == 'YT').upper()})
                if tur == 'C':
                    r.update({f'Picture Url {k}': f'{u}/C0{k}_1080x1350.jpg' for k in (1, 2, 3)})
                else:
                    r['Picture Url 1'] = f'{u}/REEL_1080x1920_9sn.mp4'
                if ag == 'IG':
                    r['Instagram Post Type'] = 'POST' if tur == 'C' else 'REEL'
                    if tur == 'R':
                        r['Instagram Show Reel On Feed'] = 'TRUE'
                elif ag == 'FB':
                    r['Facebook Post Type'] = 'POST' if tur == 'C' else 'REEL'
                    r['First Comment Text'] = cap[c]['fb_first_comment']
                    if tur == 'R':
                        r['Facebook Title'] = ad(c)
                elif ag == 'YT':
                    lid = cap[c]['listing_id_DOGRULANMADI']
                    a_, b_ = c.lower().split('_')
                    r.update({'Text': kisa_metin(cap[c]['ig_caption'], f'Shop: https://www.etsy.com/listing/{lid}'),
                              'YouTube Video Title': f'{ad(c)} Personalized Zodiac Couple Print | AstroLoveArt',
                              'YouTube Video Type': 'SHORT', 'YouTube Video Privacy': 'PUBLIC',
                              'YouTube video for kids': 'false', 'YouTube Video Category': YT_KATEGORI,
                              'YouTube Video Tags': f'{a_}{b_}, zodiac couple, couple gift, personalized gift, zodiac art',
                              'YouTube Notify Subscribers': 'true'})
                    if len(r['YouTube Video Title']) > 100:
                        hata.append(f'YT baslik > 100 {c}')
                else:
                    r.update({'Text': kisa_metin(cap[c]['ig_caption'], 'Find us on Etsy: AstroLoveArt'),
                              'TikTok disable comments': 'false', 'TikTok disable duet': 'false',
                              'TikTok disable stitch': 'false'})
                r['_ag'] = ag
                r['_t'] = t; r['_cift'] = c; r['_tur'] = tur
                out.append(r)
    for c, z in ne_zaman.items():
        for ag in ('IG', 'FB', 'YT', 'TT'):
            if min(abs(z[('R', ag)] - z[('C', x)]) for x in ('IG', 'FB')) < timedelta(days=KAYDIR):
                hata.append(f'7 gun kurali {c} {ag}')
    gunluk = {}
    for r in out:
        gunluk.setdefault((r['_t'] - timedelta(hours=12)).date(), set()).add((r['_tur'], r['_cift']))
    for g, k in gunluk.items():
        if len(k) != 2 or len({c for _, c in k}) != 2:
            hata.append(f'gun {g}: {sorted(k)}')
    if MK:
        for r in out:
            for v in (r['Text'], r['First Comment Text'], r['Facebook Title'], r['YouTube Video Title'], r['YouTube Video Tags']):
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
    for grup in ('IG_FB', 'YT', 'TT'):
        g = [r for r in out if DOSYA[r['_ag']] == grup]
        onek = a.onek if grup == 'IG_FB' else a.onek.replace('IG_FB', grup)
        dosyalar = []
        for i in range(0, len(g), 50):
            p = Path(a.cikti) / f'{onek}_{i // 50 + 1:02d}.csv'
            with open(p, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=KOL, extrasaction='ignore', lineterminator='\n')
                w.writeheader(); w.writerows(g[i:i + 50])
            dosyalar.append(p.name)
        print(f"CSV {grup}: {len(dosyalar)} dosya, {len(g)} satir, ilk {g[0]['Date']} {g[0]['Time']}, "
              f"son {g[-1]['Date']} {g[-1]['Time']}: {', '.join(dosyalar)}")


if __name__ == '__main__':
    main()
