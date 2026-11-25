#!/usr/bin/env python3
"""Pinterest 78 cift x 3 tur (poster, kart, video) = 234 pin KURU takvimi (Serdar 25 Kas 2026, KARARLAR_20261125_49/_50).
YAZMA YOK (Metricool / Pinterest). Kurallar: gunde 7 pin; ayni ilana iki pin arasi >= 7 gun; baslangic --baslangic;
12 Ara 2026'dan once kanal Metricool, sonra kendi sistem (Metricool 12 Ara'da biter, ANA_LISTE_20261123); metin surumu:
yayin 1 Mar 2027'den once "sevgililer", sonra "genel". Sira: oncelikli 4 cift (satan/aranan: CANCER_LEO, SCORPIO_TAURUS,
PISCES_VIRGO, CANCER_LIBRA; kayit [ER] + PINLER_ORNEK), sonra data/sosyal/pinterest/SIRA_78.csv. Tur sirasi: once 78 poster,
sonra 78 kart, sonra 78 video (ayni cift turlar arasi ~11 gun). Saatler (Europe/Istanbul) tahmin: ABD gunduz/aksamina yayilir.
Kontrol (PASS/FAIL, cikis 1): 234 satir, cift basina 3 (her turden 1), gun basina <= 7, ayni ilan arasi >= 7 gun, link biciminde
78 ilan, pano basina <= 100 yeni pin (R4 20-100).
Kullanim: pin78_takvim.py --cikti TAKVIM.csv [--baslangic 2026-11-25]
"""
import argparse, csv, os, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ONCELIK = ['CANCER_LEO', 'SCORPIO_TAURUS', 'PISCES_VIRGO', 'CANCER_LIBRA']
SAAT = ['16:00', '18:00', '20:00', '22:00', '00:00', '02:00', '04:00']   # 00-04 ertesi takvim gunu
PANO = {'poster': "Valentine's Day Gifts for Couples", 'kart': 'Zodiac Compatibility Art', 'video': 'Astrology Wall Art and Home Decor'}
METRICOOL_SON = date(2026, 12, 12)
GENEL_BAS = date(2027, 3, 1)


def sira():
    s = [r['cift'] for r in sorted(csv.DictReader(open(os.path.join(KOK, 'data/sosyal/pinterest/SIRA_78.csv'), encoding='utf-8')),
                                   key=lambda r: int(r['sira']))]
    return ONCELIK + [c for c in s if c not in ONCELIK]


def plan(bas):
    ids = {r['cift']: r['listing_id'] for r in csv.DictReader(open(os.path.join(KOK, 'data/pod/pod78_ids.csv'), encoding='utf-8'))}
    out, n = [], 0
    for tur in ('poster', 'kart', 'video'):
        for c in sira():
            g, s = divmod(n, len(SAAT)); n += 1
            gun = bas + timedelta(days=g)
            hh = SAAT[s]; t = datetime.combine(gun + timedelta(days=1 if hh < '06:00' else 0), datetime.strptime(hh, '%H:%M').time())
            out.append({'plan_gunu': g + 1, 'tarih_saat_tr': t.strftime('%Y-%m-%d %H:%M'), 'cift': c, 'tur': tur,
                        'listing_id': ids.get(c, ''), 'link': f"https://www.etsy.com/listing/{ids.get(c, '')}",
                        'pano': PANO[tur], 'kanal': 'Metricool' if t.date() < METRICOOL_SON else 'kendi sistem',
                        'metin_surumu': 'sevgililer' if t.date() < GENEL_BAS else 'genel'})
    return out


def kontrol(out):
    S = [('234 satir', len(out) == 234, len(out))]
    say = Counter(r['cift'] for r in out); turler = defaultdict(set)
    for r in out:
        turler[r['cift']].add(r['tur'])
    S.append(('78 cift x 3', len(say) == 78 and set(say.values()) == {3}, f'{len(say)} cift'))
    S.append(('cift basina 3 tur', all(len(v) == 3 for v in turler.values()), ''))
    gun = Counter(r['plan_gunu'] for r in out)
    S.append(('gun basina <= 7', max(gun.values()) <= 7, max(gun.values())))
    son = {}; minara = 999
    for r in sorted(out, key=lambda r: r['tarih_saat_tr']):
        t = datetime.strptime(r['tarih_saat_tr'], '%Y-%m-%d %H:%M')
        if r['listing_id'] in son:
            minara = min(minara, (t - son[r['listing_id']]).total_seconds() / 86400)
        son[r['listing_id']] = t
    S.append(('ayni ilan arasi >= 7 gun', minara >= 7, f'en az {minara:.2f} gun'))
    S.append(('78 ilan id, link bicimi', len({r['listing_id'] for r in out if r['listing_id'].isdigit()}) == 78, ''))
    pano = Counter(r['pano'] for r in out)
    S.append(('pano basina <= 100 yeni pin', max(pano.values()) <= 100, dict(pano)))
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cikti', required=True); ap.add_argument('--baslangic', default='2026-11-25'); ap.add_argument('--oz-test', action='store_true')
    a = ap.parse_args()
    out = plan(date.fromisoformat(a.baslangic))
    if a.oz_test:
        bozuk = [dict(r) for r in out]; bozuk[len(SAAT)]['tarih_saat_tr'] = bozuk[0]['tarih_saat_tr']; bozuk[len(SAAT)]['plan_gunu'] = 1
        k1 = not all(o for _, o, _ in kontrol(bozuk))
        yakin = [dict(r) for r in out]; i = next(j for j, r in enumerate(yakin) if r['tur'] == 'kart' and r['cift'] == 'CANCER_LEO')
        yakin[i]['tarih_saat_tr'] = (datetime.strptime(yakin[0]['tarih_saat_tr'], '%Y-%m-%d %H:%M') + timedelta(days=2)).strftime('%Y-%m-%d %H:%M')
        k2 = not all(o for _, o, _ in kontrol(yakin))
        k0 = all(o for _, o, _ in kontrol(out))
        for ad, v in (('bilinen PASS', k0), ('FAIL: gunde 8 pin', k1), ('FAIL: ayni ilan 2 gun arayla', k2)):
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if (k0 and k1 and k2) else 1)
    with open(a.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
    S = kontrol(out)
    for ad, o, d in S:
        print(f"{'PASS' if o else 'FAIL'} {ad} | {d}")
    k = Counter(r['kanal'] for r in out); print('OZET', out[0]['tarih_saat_tr'], '->', out[-1]['tarih_saat_tr'], dict(k))
    sys.exit(0 if all(o for _, o, _ in S) else 1)


if __name__ == '__main__':
    main()
