#!/usr/bin/env python3
"""Pinterest 78 cift x 3 tur (poster, kart, video) = 234 pin KURU takvimi (Serdar 25 Kas 2026, KARARLAR_20261125_49/_50).
YAZMA YOK (Metricool / Pinterest). Kurallar: gunde 7 pin; ayni ilana iki pin arasi >= 7 gun; baslangic --baslangic;
12 Ara 2026'dan once kanal Metricool, sonra kendi sistem (Metricool 12 Ara'da biter, ANA_LISTE_20261123); metin surumu:
yayin 1 Mar 2027'den once "sevgililer", sonra "genel". Sira: oncelikli 4 cift (satan/aranan: CANCER_LEO, SCORPIO_TAURUS,
PISCES_VIRGO, CANCER_LIBRA; kayit [ER] + PINLER_ORNEK), sonra data/sosyal/pinterest/SIRA_78.csv. Tur sirasi: once 78 poster,
sonra 78 kart, sonra 78 video (ayni cift turlar arasi ~11 gun). Saatler: 02:00-05:00 TR, 30 dk arayla (strateji raporu 7.3:
ABD Dogu 18:00-21:00; raporda da tahmin). Plan gunu 1 = --baslangic gecesi (ertesi takvim gunu 02:00).
Pano / bolum (strateji 7.5 onerisi, Serdar onayi gerekir): poster -> Valentine's Day Gifts for Couples / Posters, video -> ayni pano /
Videos, kart -> Zodiac Compatibility Art / Combined Symbol Cards (ana panoda 78 pin var, strateji 7.5 kayit).
Kontrol (PASS/FAIL, cikis 1): 234 satir, cift basina 3 (her turden 1), TAKVIM GUNU basina <= 7, ayni ilan arasi >= 7 gun,
78 ilan, pano/bolum basina (mevcut pinler dahil) <= 100 (R4 20-100), Metricool satirlari 12 Ara'dan once.
Not: Metricool kuyrugunda 12 Ara'ya kadar gunde ~4 kupa pini daha var (strateji 7.1 [09]); gunluk toplam ~11 olur.
Kullanim: pin78_takvim.py --cikti TAKVIM.csv [--baslangic 2026-11-25]
"""
import argparse, csv, os, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ONCELIK = ['CANCER_LEO', 'SCORPIO_TAURUS', 'PISCES_VIRGO', 'CANCER_LIBRA']
SAAT = ['02:00', '02:30', '03:00', '03:30', '04:00', '04:30', '05:00']   # hepsi plan gununun ertesi takvim gunu
PANO = {'poster': ("Valentine's Day Gifts for Couples", 'Posters'), 'kart': ('Zodiac Compatibility Art', 'Combined Symbol Cards'),
        'video': ("Valentine's Day Gifts for Couples", 'Videos')}
MEVCUT = {("Zodiac Compatibility Art", ''): 78, ("Zodiac Couple Wall Art", ''): 156}   # strateji 7.5 (22 Kas okuma); bolumsuz = ana pano
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
            hh = SAAT[s]; t = datetime.combine(gun + timedelta(days=1), datetime.strptime(hh, '%H:%M').time())
            out.append({'plan_gunu': g + 1, 'tarih_saat_tr': t.strftime('%Y-%m-%d %H:%M'), 'cift': c, 'tur': tur,
                        'listing_id': ids.get(c, ''), 'link': f"https://www.etsy.com/listing/{ids.get(c, '')}",
                        'pano': PANO[tur][0], 'pano_bolumu': PANO[tur][1],
                        'kanal': 'Metricool' if t.date() < METRICOOL_SON else 'kendi sistem (Pinterest yolu HAZIR DEGIL)',
                        'metin_surumu': 'sevgililer' if t.date() < GENEL_BAS else 'genel'})
    return out


def kontrol(out):
    S = [('234 satir', len(out) == 234, len(out))]
    say = Counter(r['cift'] for r in out); turler = defaultdict(set)
    for r in out:
        turler[r['cift']].add(r['tur'])
    S.append(('78 cift x 3', len(say) == 78 and set(say.values()) == {3}, f'{len(say)} cift'))
    S.append(('cift basina 3 tur', all(len(v) == 3 for v in turler.values()), ''))
    gun = Counter(r['tarih_saat_tr'][:10] for r in out)
    S.append(('takvim gunu basina <= 7', max(gun.values()) <= 7, max(gun.values())))
    S.append(('Metricool satirlari 12 Ara oncesi', all(r['tarih_saat_tr'][:10] < str(METRICOOL_SON) for r in out if r['kanal'] == 'Metricool'), ''))
    son = {}; minara = 999
    for r in sorted(out, key=lambda r: r['tarih_saat_tr']):
        t = datetime.strptime(r['tarih_saat_tr'], '%Y-%m-%d %H:%M')
        if r['listing_id'] in son:
            minara = min(minara, (t - son[r['listing_id']]).total_seconds() / 86400)
        son[r['listing_id']] = t
    S.append(('ayni ilan arasi >= 7 gun', minara >= 7, f'en az {minara:.2f} gun'))
    S.append(('78 ilan id, link bicimi', len({r['listing_id'] for r in out if r['listing_id'].isdigit()}) == 78, ''))
    pano = Counter((r['pano'], r['pano_bolumu']) for r in out)
    for k, n in MEVCUT.items():
        if k in pano:          # yalniz bu planin pin ekledigi pano/bolum
            pano[k] += n
    S.append(('pano/bolum basina <= 100 (mevcut dahil)', max(pano.values()) <= 100, {f'{a}/{b or "ana"}': n for (a, b), n in pano.items()}))
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cikti', required=True); ap.add_argument('--baslangic', default='2026-11-25'); ap.add_argument('--oz-test', action='store_true')
    a = ap.parse_args()
    out = plan(date.fromisoformat(a.baslangic))
    if a.oz_test:
        bozuk = [dict(r) for r in out]; bozuk[len(SAAT)]['tarih_saat_tr'] = bozuk[0]['tarih_saat_tr']   # 8. pin ayni takvim gununde
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
