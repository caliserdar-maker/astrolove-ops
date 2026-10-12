#!/usr/bin/env python3
"""Pinterest V6 (234 pin) Metricool KURU takvimi (Serdar gorevi 12 Eki 2026). Metricool'a YAZMA YOK.
- Baslangic 25 Eki 2026, gunde 10 slot (mevcut plan saatleri, Europe/Istanbul):
  14:00 15:30 17:00 18:30 20:00 21:30 23:00 | ertesi takvim gunu 00:30 02:00 03:30 (plan gunu = 14:00 -> 03:30).
- P1 gun 1-8, P2 gun 9-16, P3 gun 17-24 (bant basi 80 slot, 78 pin; bandin son gununun son 2 slotu bos).
- Cift sirasi SIRA_78; P2 bandi 26, P3 bandi 52 kaydirilir (ayni cift her bantta farkli saate duser).
- Pano: P1 Zodiac Couple Wall Art, P2 Zodiac Compatibility Art, P3 Personalized Couple Gifts; id Metricool
  GET /v2/scheduler/boards/pinterest ciktisindan; bulunamazsa PANO_YOK.
- Metinler PIN_METIN_234_LINKLI.csv'den AYNEN. Kontrol: 234 satir, cift basina 3, ayni plan gununde ayni cift yok,
  art arda ayni cift yok, baslik<=100, aciklama<=500, alt metin<=500, uzun/orta tire yok.
Kullanim: pin_v6_plan.py --metin M.csv --sira SIRA_78.csv --panolar PANOLAR.json --pinler PINLER.json --cikti PLAN.csv"""
import argparse, csv, json, sys
from datetime import date, datetime, timedelta

BAS = date(2026, 10, 25)
SLOT = [('14:00', 0), ('15:30', 0), ('17:00', 0), ('18:30', 0), ('20:00', 0), ('21:30', 0), ('23:00', 0),
        ('00:30', 1), ('02:00', 1), ('03:30', 1)]
PANO = {'p1': 'Zodiac Couple Wall Art', 'p2': 'Zodiac Compatibility Art', 'p3': 'Personalized Couple Gifts'}
KAYDIR = {'p1': 0, 'p2': 26, 'p3': 52}


def kol(r, *adlar):
    for a in adlar:
        for k in r:
            if k.strip().lower() == a:
                return k
    raise SystemExit(f'DUR: metin CSV kolon yok: {adlar} (var: {list(r)})')


def main():
    ap = argparse.ArgumentParser()
    for k in ('metin', 'sira', 'panolar', 'pinler', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    M = list(csv.DictReader(open(a.metin, encoding='utf-8-sig')))
    r0 = M[0]
    K = {'cift': kol(r0, 'cift_anahtari', 'cift', 'pair'), 'pin': kol(r0, 'pin', 'varyant', 'tip'),
         'baslik': kol(r0, 'baslik', 'title', 'pin_title'), 'aciklama': kol(r0, 'aciklama', 'description'),
         'alt': kol(r0, 'alt_metin', 'alt_text', 'alt'), 'link': kol(r0, 'etsy_link', 'link'),
         'dosya': kol(r0, 'dosya', 'gorsel', 'file', 'dosya_adi')}
    metin = {}
    for r in M:
        metin[(r[K['cift']].strip().upper(), r[K['pin']].strip().lower())] = r
    sira = [x['cift'] for x in sorted(csv.DictReader(open(a.sira, encoding='utf-8')), key=lambda x: int(x['sira']))]
    pano_id = {}
    for b in json.load(open(a.panolar)):
        pano_id.setdefault((b.get('name') or b.get('title') or '').strip().lower(), str(b.get('id') or b.get('boardId') or ''))
    dosya_id = {x['Name']: x.get('ID', '') for x in json.load(open(a.pinler))}
    hata, out = [], []
    for g in range(24):
        pin = f'p{g // 8 + 1}'
        bant_gun = g % 8
        for s, (saat, ek) in enumerate(SLOT):
            k = bant_gun * 10 + s
            if k >= 78:
                continue
            c = sira[(k + KAYDIR[pin]) % 78]
            r = metin.get((c, pin))
            if r is None:
                hata.append(f'metin yok {c} {pin}'); continue
            if r.get('pano', PANO[pin]).strip() != PANO[pin]:
                hata.append(f"pano metinde farkli {c} {pin}: {r.get('pano')}")
            pid = pano_id.get(PANO[pin].lower(), '')
            dosya = r[K['dosya']].strip()
            out.append({'plan_gunu': g + 1, 'tarih_saat': f'{BAS + timedelta(days=g + ek)} {saat}', 'cift': c, 'pin': pin.upper(),
                        'pano': PANO[pin], 'pano_id': pid or 'PANO_YOK', 'baslik': r[K['baslik']], 'aciklama': r[K['aciklama']],
                        'alt_metin': r[K['alt']], 'link': r[K['link']], 'gorsel_dosya': dosya,
                        'drive_id': dosya_id.get(dosya, 'DOSYA_YOK')})
    # kontroller
    from collections import Counter
    if len(out) != 234:
        hata.append(f'satir {len(out)} != 234')
    say = Counter(r['cift'] for r in out)
    hata += [f'cift {c} {n} kez' for c, n in say.items() if n != 3]
    if len(say) != 78:
        hata.append(f'cift sayisi {len(say)}')
    gun = Counter((r['plan_gunu'], r['cift']) for r in out)
    hata += [f'ayni gun tekrar {k}' for k, n in gun.items() if n > 1]
    hata += [f"art arda {out[i]['cift']}" for i in range(1, len(out)) if out[i]['cift'] == out[i - 1]['cift']]
    for r in out:
        for alan, lim in (('baslik', 100), ('aciklama', 500), ('alt_metin', 500)):
            if not r[alan] or len(r[alan]) > lim:
                hata.append(f"{alan} uzunluk {r['cift']} {r['pin']} {len(r[alan])}")
            if '—' in r[alan] or '–' in r[alan]:
                hata.append(f"{alan} tire {r['cift']} {r['pin']}")
        if not r['link'].startswith('https://www.etsy.com/listing/'):
            hata.append(f"link {r['cift']} {r['pin']}")
    tarih = [datetime.fromisoformat(r['tarih_saat']) for r in out]
    if tarih != sorted(tarih) or len(set(tarih)) != len(tarih):
        hata.append('saat sirasi/tekrar')
    with open(a.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
    gs = Counter(r['plan_gunu'] for r in out)
    print(f"PLAN {len(out)} satir, ilk {out[0]['tarih_saat']}, son {out[-1]['tarih_saat']}, "
          f"gunluk {dict(sorted(Counter(gs.values()).items()))} (pin sayisi: gun adedi), "
          f"PANO_YOK {sum(r['pano_id'] == 'PANO_YOK' for r in out)}, DOSYA_YOK {sum(r['drive_id'] == 'DOSYA_YOK' for r in out)}")
    print('KONTROL ' + ('PASS' if not hata else 'FAIL: ' + '; '.join(hata[:20])))
    sys.exit(1 if hata else 0)


if __name__ == '__main__':
    main()
