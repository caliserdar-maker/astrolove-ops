#!/usr/bin/env python3
"""Pinterest V1 toplu uretim (Serdar karari 1 Eki 2026). Tasarim ChatGPT'nindir: build_pins.py'deki pin 01, 02, 04
bloklari BIREBIR calistirilir; degisen yalniz cift adi ("{A} & {B}") ve ciftin gercek cerceveli gorseli
(Etsy 1. gorsel 01_kapak.jpg, scripts/sosyal/cerceve_kirp.py kutusu, tam cozunurluk, yalniz kirpim).

Girdi:
  --paket   data/sosyal/pinterest/chatgpt_pilot_cl_20261001 (build_pins.py, pin_copy.csv)
  --sahne   ChatGPT AI bos sahne (assets/scene_empty_master.png); yoksa DUR
  --fontlar P052-Roman.otf + NimbusSans-Regular.otf klasoru (sha256 denetlenir)
  --kapak   klasor: <CIFT>/01_kapak.jpg (77 cift TEMP/GALERI_77, CL data/pod/cl_galeri_final19)
  --cikti   klasor
Cikti: <cikti>/v1/<CIFT>/PIN_0{1,2,4}_*.jpg, QC.csv, PINLER.csv (yayin sirasi + metin), ONIZLEME_2CIFT.jpg
QC (her gorsel): 1000x1500; poster katmani PNG'de kaynak kirpimin LANCZOS olcegiyle piksel farki 0;
cift adi katmani beklenen metin; metin_kurali PASS; baslik <= 100, aciklama <= 500; link listing_id dogru.
FAIL olan ciftin hicbir pini yayin listesine girmez.
"""
import argparse, csv, hashlib, importlib.util, json, re, shutil, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cerceve_kirp import kirp_kutusu  # noqa: E402

FONT_SHA = {'P052-Roman.otf': 'f054a7389d8d0e9f4c5f7b4c21feb7e2b14bec8004a1e92778a78d149524eea9',
            'NimbusSans-Regular.otf': '7c25be4d78155523080ab85b10277150657ff7dabbcad7037bdd536c9b6d0d08'}
TIPLER = [('01', '01_Discovery_1000x1500', "    c=Composition('01_Discovery", "    c=Composition('02_Personalization"),
          ('02', '02_Personalization_1000x1500', "    c=Composition('02_Personalization", "    c=Composition('03_Five_Colors"),
          ('04', '04_Anniversary_Gift_1000x1500', "    c=Composition('04_Anniversary_Gift", "    c=Composition('Profile_Cover")]
PANO = {'01': 'Zodiac Couple Wall Art', '02': 'Personalized Couple Gifts', '03': 'Zodiac Couple Wall Art',
        '04': 'Anniversary Gifts for Couples'}
DALGA = ['01', '04', '02']                       # Serdar: 01 -> 04 -> 02
# Serdar 1 Eki: gunde 10 pin, Istanbul saati (ABD Dogu 07:00-20:30, 1.5 saatte bir); 00:30-03:30 ertesi takvim gunu
SAATLER = [('14:00:00', 0), ('15:30:00', 0), ('17:00:00', 0), ('18:30:00', 0), ('20:00:00', 0), ('21:30:00', 0),
           ('23:00:00', 0), ('00:30:00', 1), ('02:00:00', 1), ('03:30:00', 1)]
ARA_GUN = 7                                       # ayni ciftin iki pini arasi en az 7 x 24 saat
BASLANGIC = date(2026, 10, 2)
PAGES = 'https://caliserdar-maker.github.io/astrolove-media/pinterest'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def metin_uyarla(t, A, B):
    t = re.sub(r'\b([Aa]) (?=Cancer and Libra)', lambda m: m.group(1) + ('n' if A[0] in 'AEIOU' else '') + ' ', t)
    return t.replace('Cancer and Libra', f'{A} and {B}')


def zamanla(akis):
    """Slotlari sirayla doldurur; her slota kuyruktaki ILK uygun pin (ayni ciftin son pininden en az ARA_GUN
    x 24 saat sonra) konur, uygun pin yoksa slot bos kalir. Sira (dalga 01 -> 04 -> 02, SIRA_78) korunur."""
    kuyruk, son, plan, slot = list(akis), {}, [], 0
    while kuyruk:
        gun, s = divmod(slot, len(SAATLER)); saat, kay = SAATLER[s]
        d = BASLANGIC + timedelta(days=gun + kay)
        an = datetime.fromisoformat(f'{d.isoformat()}T{saat}')
        for j, r in enumerate(kuyruk):
            if r['cift'] not in son or an - son[r['cift']] >= timedelta(days=ARA_GUN):
                plan.append((d, saat, r)); son[r['cift']] = an; kuyruk.pop(j); break
        slot += 1
        if slot > 100000: sys.exit('DUR: zamanlama kilitlendi')
    return plan


def main():
    ap = argparse.ArgumentParser()
    for a in ('--paket', '--sahne', '--fontlar', '--kapak', '--cikti', '--metin-kurali'):
        ap.add_argument(a, required=True)
    ap.add_argument('--ciftler', default='HEPSI')
    a = ap.parse_args()
    t0 = time.time()
    paket, cikti = Path(a.paket), Path(a.cikti)
    spec = importlib.util.spec_from_file_location('metin_kurali', a.metin_kurali)
    MK = importlib.util.module_from_spec(spec); spec.loader.exec_module(MK)
    sahne = Path(a.sahne)
    if not sahne.is_file():
        sys.exit(f'DUR: AI sahne yok: {sahne} (ChatGPT paketinin assets/scene_empty_master.png dosyasi gerekli)')
    for f, h in FONT_SHA.items():
        if sha(Path(a.fontlar) / f) != h:
            sys.exit(f'DUR: font sha256 farkli: {f}')
    # calisma kopyasi: build_pins.py + fonts + assets (paket klasoru kirletilmez)
    W = cikti / '_is'
    if W.exists(): shutil.rmtree(W)
    (W / 'fonts').mkdir(parents=True); (W / 'assets').mkdir()
    shutil.copy(paket / 'build_pins.py', W)
    for f in FONT_SHA: shutil.copy(Path(a.fontlar) / f, W / 'fonts' / f)
    shutil.copy(sahne, W / 'assets' / 'scene_empty_master.png')
    sys.path.insert(0, str(W))
    import build_pins as B
    kaynak = (W / 'build_pins.py').read_text()
    for d in ('assets', 'pins', 'profile', 'layers', 'templates'): B.path(d).mkdir(parents=True, exist_ok=True)
    B.make_backgrounds()
    bloklar = {k: '\n'.join(l[4:] for l in kaynak[kaynak.index(s):kaynak.index(e)].splitlines())
               for k, _, s, e in TIPLER}

    ids = {r['cift']: r for r in csv.DictReader(open(KOK / 'data/pod/pod78_ids.csv'))}
    sira = [r['cift'] for r in csv.DictReader(open(KOK / 'data/sosyal/pinterest/SIRA_78.csv'))]
    assert sorted(sira) == sorted(ids), 'SIRA_78 ile pod78_ids uyusmuyor'
    kopya = {r['file'][:2]: r for r in csv.DictReader(open(paket / 'pin_copy.csv', encoding='utf-8-sig'))}
    hedef = sira if a.ciftler == 'HEPSI' else [c for c in sira if c in a.ciftler.split(',')]

    qc_satir, gecen = [], set()
    for n, c in enumerate(hedef, 1):
        A, B_ = ids[c]['a'], ids[c]['b']
        pair = f'{A} & {B_}'
        hata = []
        kapak = Path(a.kapak) / c / '01_kapak.jpg'
        try:
            k = kirp_kutusu(str(kapak))
            if k['boyut'] != [3000, 2250]: hata.append(f"kapak boyutu {k['boyut']}")
            asset = W / 'assets' / f'real_framed_{c}.png'
            Image.open(kapak).convert('RGB').crop(tuple(k['kutu_3000'])).save(asset)
            framed = f'assets/real_framed_{c}.png'
            B.PREFIX = c + '_'; B.CHECKS.clear()
            for tip, ad, _, _ in TIPLER:
                exec(bloklar[tip], {**vars(B), 'pair': pair, 'framed': framed})
            # QC
            hedef_dir = cikti / 'v1' / c; hedef_dir.mkdir(parents=True, exist_ok=True)
            src = Image.open(asset).convert('RGBA')
            for tip, ad, _, _ in TIPLER:
                comp = B.COMPS[f'{c}_{ad}']
                png = Image.open(B.path(f'pins/{c}_{ad}.png')).convert('RGB')
                if png.size != (1000, 1500): hata.append(f'{tip} boyut {png.size}')
                art = [l for l in comp['layers'] if l['type'] == 'artwork'][0]
                x, y, w, h = art['bbox_xywh']
                ref = np.asarray(src.resize((w, h), Image.Resampling.LANCZOS).convert('RGB'), dtype=int)
                fark = int(np.abs(np.asarray(png.crop((x, y, x + w, y + h)), dtype=int) - ref).max())
                if fark != 0: hata.append(f'{tip} poster farki {fark}')
                metinler = ' | '.join(l.get('text', '') for l in comp['layers'] if l['type'] == 'text')
                if pair not in metinler and pair.upper() not in metinler: hata.append(f'{tip} cift adi yok')
                if 'Cancer' in metinler and c != 'CANCER_LIBRA' and 'CANCER' not in c: hata.append(f'{tip} eski cift adi')
                shutil.copy(B.path(f'pins/{c}_{ad}.jpg'), hedef_dir / f'PIN_{ad}.jpg')
                r = kopya[tip]
                ttl, dsc, alt = (metin_uyarla(r[f], A, B_) for f in ('title', 'description', 'alt_text'))
                if len(ttl) > 100 or len(dsc) > 500: hata.append(f'{tip} uzunluk {len(ttl)}/{len(dsc)}')
                for v in (ttl, dsc, alt):
                    for x_ in MK.denetle(v): hata.append(f'{tip} metin_kurali {x_}')
                if c != 'CANCER_LIBRA' and ('Cancer and Libra' in ttl + dsc + alt): hata.append(f'{tip} metin eski cift')
                link = f"https://www.etsy.com/listing/{ids[c]['listing_id']}"
                qc_satir.append({'cift': c, 'tip': tip, 'dosya': f'v1/{c}/PIN_{ad}.jpg',
                                 'url': f'{PAGES}/v1/{c}/PIN_{ad}.jpg', 'title': ttl, 'description': dsc,
                                 'alt_text': alt, 'board': PANO[tip], 'link': link, 'poster_farki': fark,
                                 'kutu_3000': json.dumps(k['kutu_3000'])})
            # bellek: katman PNG'leri silinir
            shutil.rmtree(B.path('layers'), ignore_errors=True); B.path('layers').mkdir()
            for p in B.path('pins').glob(f'{c}_*'): p.unlink()
            B.COMPS.clear()
        except Exception as e:  # noqa: BLE001
            hata.append(f'istisna {type(e).__name__}: {e}')
        durum = 'PASS' if not hata else 'FAIL'
        if not hata: gecen.add(c)
        for q in qc_satir:
            if q['cift'] == c: q['qc'] = durum; q['hata'] = '; '.join(hata)
        if hata and not any(q['cift'] == c for q in qc_satir):
            qc_satir.append({'cift': c, 'tip': '-', 'qc': 'FAIL', 'hata': '; '.join(hata)})
        gec = time.time() - t0
        print(f'[{n}/{len(hedef)}] {c} {durum} gecen {gec:.0f}s kalan ~{gec / n * (len(hedef) - n):.0f}s '
              f'%{100 * n // len(hedef)}' + (f' | {"; ".join(hata)}' if hata else ''), flush=True)

    alanlar = ['cift', 'tip', 'qc', 'hata', 'dosya', 'url', 'title', 'description', 'alt_text', 'board', 'link',
               'poster_farki', 'kutu_3000']
    with open(cikti / 'QC.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(qc_satir)

    # yayin sirasi: dalga 01 -> 04 -> 02, her dalga SIRA_78 sirasiyla; CL 03 (pilot) en sona
    q = {(r['cift'], r['tip']): r for r in qc_satir if r.get('qc') == 'PASS'}
    akis = [q[(c, t)] for t in DALGA for c in sira if (c, t) in q]
    if 'CANCER_LIBRA' in gecen:
        r = kopya['03']
        akis.append({'cift': 'CANCER_LIBRA', 'tip': '03', 'url': f'{PAGES}/pilot_cl/03_Five_Colors_1000x1500.jpg',
                     'title': r['title'], 'description': r['description'], 'alt_text': r['alt_text'],
                     'board': PANO['03'], 'link': f"https://www.etsy.com/listing/{ids['CANCER_LIBRA']['listing_id']}"})
    plan = zamanla(akis)
    with open(cikti / 'PINLER.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['no', 'Date', 'Time', 'cift', 'tip', 'url', 'board', 'title', 'description', 'alt_text', 'link'])
        for i, (d, saat, r) in enumerate(plan):
            w.writerow([i + 1, d.isoformat(), saat, r['cift'], r['tip'], r['url'], r['board'], r['title'],
                        r['description'], r['alt_text'], r['link']])

    # onizleme: ARIES_LEO ve CAPRICORN_PISCES, 01/02/04 yan yana (gercek oran 2:3)
    sat = [c for c in ('ARIES_LEO', 'CAPRICORN_PISCES') if c in gecen]
    if sat:
        on = Image.new('RGB', (3 * 600 + 4 * 20, len(sat) * 900 + (len(sat) + 1) * 20), 'white')
        for i, c in enumerate(sat):
            for j, (_, ad, _, _) in enumerate(TIPLER):
                im = Image.open(cikti / 'v1' / c / f'PIN_{ad}.jpg').resize((600, 900), Image.Resampling.LANCZOS)
                on.paste(im, (20 + j * 620, 20 + i * 920))
        on.save(cikti / 'ONIZLEME_2CIFT.jpg', quality=90)
    shutil.rmtree(W, ignore_errors=True)
    print(json.dumps({'cift': len(hedef), 'pass_cift': len(gecen), 'gorsel_pass': 3 * len(gecen),
                      'fail': sorted(set(hedef) - gecen), 'yayin_satiri': len(akis)}))


if __name__ == '__main__':
    main()
