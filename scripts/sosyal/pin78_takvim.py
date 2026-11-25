#!/usr/bin/env python3
"""Pinterest 78 cift x 4 tur (poster, kart, altin yakin cekim, video) = 312 pin KURU takvimi (Serdar 25 Kas 2026,
KARARLAR_20261125_49/_50/_51).
YAZMA YOK (Metricool / Pinterest). Kurallar: gunde 7 pin; ayni ilana iki pin arasi >= 7 gun (plan geregi >= 11.1 gun cikar); baslangic --baslangic;
12 Ara 2026'dan once kanal Metricool, sonra kendi sistem (Metricool 12 Ara'da biter, ANA_LISTE_20261123); metin surumu:
yayin 1 Mar 2027'den once "sevgililer", sonra "genel". Sira: oncelikli 4 cift (satan/aranan: CANCER_LEO, SCORPIO_TAURUS,
PISCES_VIRGO, CANCER_LIBRA; kayit [ER] + PINLER_ORNEK), sonra data/sosyal/pinterest/SIRA_78.csv. Tur sirasi: once 78 poster,
sonra 78 kart, 78 altin yakin cekim, 78 video (ayni cift turlar arasi ~11 gun). Saatler: Serdar KARAR 10 (SOSYAL_KARAR 20 Eki)
"saatler 09:00-23:30" (20 Eki) YERINE Serdar 25 Kas ABD karari: Istanbul 15:00-07:00, 7 slot (asagida SAAT). Baslangic: --baslangic gununun --simdi sonrasi ilk slotu (Serdar: takvim bugunden).
SAAT (Serdar 25 Kas, ABD): Istanbul 15:00-07:00, 7 slot; tarih_saat_et sutunu New York saati (bilgi).
Tur dagilimi: her gun turler karisik (cift i, tur k -> TURLER[(i + k) % 4]).
Pano / bolum (strateji 7.5 onerisi, Serdar onayi gerekir; bolumler Pinterest'te YOK, acilmasi yazim): sevgililer surumu:
poster -> Valentine's Day Gifts for Couples / Posters, video -> ayni pano / Videos, kart -> Zodiac Compatibility Art / Combined
Symbol Cards (ana panoda 78 pin), altin -> Astrology Wall Art and Home Decor (bos pano; strateji 7.5 "C yakin cekim").
genel surum (1 Mar 2027 sonrasi): poster ve video -> Wedding and Engagement Gifts, kart ve altin ayni.
Kontrol (PASS/FAIL, cikis 1): 312 satir, cift basina 4 (her turden 1), TAKVIM GUNU basina <= 7, ayni ilan arasi >= 7 gun,
78 ilan, pano/bolum basina (mevcut pinler dahil) <= 100 (R4 20-100), Metricool satirlari 12 Ara'dan once.
Not: Metricool kuyrugunda 12 Ara'ya kadar gunde ~4 kupa pini daha var (strateji 7.1 [09]); gunluk toplam ~11 olur.
Kullanim: pin78_takvim.py --cikti TAKVIM.csv [--baslangic 2026-11-25]
"""
import argparse, csv, os, re, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
TR, ET = ZoneInfo('Europe/Istanbul'), ZoneInfo('America/New_York')

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ONCELIK = ['CANCER_LEO', 'SCORPIO_TAURUS', 'PISCES_VIRGO', 'CANCER_LIBRA']
# Serdar 25 Kas (ABD kitlesi, Merkez aktarimi; RAPOR_SOSYAL_ABD_DENETIM_20261125): Istanbul 15:00-07:00 (ABD gunduz); 7 slot esit aralik
# (2 sa 40 dk). 20 Eki KARAR 10 (09:00-23:30) yerine. Gece yarisini gecen slotlar (01:40, 04:20, 07:00) pencerenin ertesi gunundedir.
SAAT = ['15:00', '17:40', '20:20', '23:00', '01:40', '04:20', '07:00']
PENCERE_BAS = '15:00'
TURLER = ('poster', 'kart', 'altin', 'video')
PANO = {('poster', 'sevgililer'): ("Valentine's Day Gifts for Couples", 'Posters'),
        ('video', 'sevgililer'): ("Valentine's Day Gifts for Couples", 'Videos'),
        ('poster', 'genel'): ('Wedding and Engagement Gifts', ''), ('video', 'genel'): ('Wedding and Engagement Gifts', '')}
for _s in ('sevgililer', 'genel'):
    PANO[('kart', _s)] = ('Zodiac Compatibility Art', 'Combined Symbol Cards')
    PANO[('altin', _s)] = ('Astrology Wall Art and Home Decor', '')
MEVCUT = {("Zodiac Compatibility Art", ''): 78, ("Zodiac Couple Wall Art", ''): 156}   # strateji 7.5 (22 Kas okuma); bolumsuz = ana pano
METRICOOL_SON = date(2026, 12, 12)
GENEL_BAS = date(2027, 3, 1)


def sira():
    s = [r['cift'] for r in sorted(csv.DictReader(open(os.path.join(KOK, 'data/sosyal/pinterest/SIRA_78.csv'), encoding='utf-8')),
                                   key=lambda r: int(r['sira']))]
    return ONCELIK + [c for c in s if c not in ONCELIK]


def slotlar(bas, simdi):
    """bas gununun simdi'den sonraki slotlarindan baslayarak sirali yayin anlari (Serdar: takvim bugunden)."""
    g = 0
    while True:
        for hh in SAAT:
            ek = 1 if hh < PENCERE_BAS else 0          # 15:00 penceresinin gece yarisi sonrasi slotlari
            t = datetime.combine(bas + timedelta(days=g + ek), datetime.strptime(hh, '%H:%M').time())
            if t > simdi:
                yield t
        g += 1


def plan(bas, simdi=None):
    ids = {r['cift']: r['listing_id'] for r in csv.DictReader(open(os.path.join(KOK, 'data/pod/pod78_ids.csv'), encoding='utf-8'))}
    simdi = simdi or datetime.combine(bas, datetime.min.time())
    sl = slotlar(bas, simdi); out = []
    cs = sira()
    # 4 tur; her turda her cift bir pin, tur turdan ture doner (cift i, tur k -> TURLER[(i + k) % 4]); boylece her gun
    # turler karisik (strateji 7.4 / 7.7 test dengesi) ve ayni cift turlar arasi ~11 gun
    for k_ in range(len(TURLER)):
        for i, c in enumerate(cs):
            tur = TURLER[(i + k_) % len(TURLER)]
            t = next(sl)
            g = (t.date() - bas).days
            sur = 'sevgililer' if t.date() < GENEL_BAS else 'genel'
            et = t.replace(tzinfo=TR).astimezone(ET)
            out.append({'plan_gunu': g + 1, 'tarih_saat_tr': t.strftime('%Y-%m-%d %H:%M'), 'tarih_saat_et': et.strftime('%Y-%m-%d %H:%M'),
                        'cift': c, 'tur': tur,
                        'listing_id': ids.get(c, ''), 'link': f"https://astroloveart.etsy.com/listing/{ids.get(c, '')}",   # Share & Save bicimi (KARARLAR_20261125_57)
                        'pano': PANO[(tur, sur)][0], 'pano_bolumu': PANO[(tur, sur)][1],
                        'kanal': 'Metricool' if t.date() < METRICOOL_SON else 'kendi sistem (Pinterest yolu HAZIR DEGIL)',
                        'metin_surumu': sur})
    return out


def kontrol(out):
    N = 78 * len(TURLER)
    S = [(f'{N} satir', len(out) == N, len(out))]
    say = Counter(r['cift'] for r in out); turler = defaultdict(set)
    for r in out:
        turler[r['cift']].add(r['tur'])
    S.append((f'78 cift x {len(TURLER)}', len(say) == 78 and set(say.values()) == {len(TURLER)}, f'{len(say)} cift'))
    S.append((f'cift basina {len(TURLER)} tur', all(len(v) == len(TURLER) for v in turler.values()), ''))
    S.append(('genel surum Sevgililer panosunda degil', not any(r['metin_surumu'] == 'genel' and 'valentine' in r['pano'].lower() for r in out), ''))
    gun = Counter(r['tarih_saat_tr'][:10] for r in out)
    S.append(('takvim gunu basina <= 7', max(gun.values()) <= 7, max(gun.values())))
    # Serdar 25 Kas: yayin Istanbul 15:00-07:00 (07:00 dahil)
    S.append(('saat Istanbul 15:00-07:00 icinde', all(r['tarih_saat_tr'][11:] >= '15:00' or r['tarih_saat_tr'][11:] <= '07:00' for r in out),
              sorted({r['tarih_saat_tr'][11:] for r in out})))
    S.append(('Metricool satirlari 12 Ara oncesi', all(r['tarih_saat_tr'][:10] < str(METRICOOL_SON) for r in out if r['kanal'] == 'Metricool'), ''))
    son = {}; minara = 999
    for r in sorted(out, key=lambda r: r['tarih_saat_tr']):
        t = datetime.strptime(r['tarih_saat_tr'], '%Y-%m-%d %H:%M')
        if r['listing_id'] in son:
            minara = min(minara, (t - son[r['listing_id']]).total_seconds() / 86400)
        son[r['listing_id']] = t
    S.append(('ayni ilan arasi >= 7 gun', minara >= 7, f'en az {minara:.2f} gun'))
    S.append(('78 ilan id', len({r['listing_id'] for r in out if r['listing_id'].isdigit()}) == 78, ''))
    S.append(('link Share & Save bicimi (astroloveart.etsy.com/listing/<id>)',
              all(re.fullmatch(r'https://astroloveart\.etsy\.com/listing/\d+', r['link']) for r in out), ''))
    pano = Counter((r['pano'], r['pano_bolumu']) for r in out)
    for k, n in MEVCUT.items():
        if k in pano:          # yalniz bu planin pin ekledigi pano/bolum
            pano[k] += n
    S.append(('pano/bolum basina <= 100 (mevcut dahil; ZAYIF: yalniz 22 Kas kayit sayilari, bolumler henuz yok)', max(pano.values()) <= 100,
              {f'{a}/{b or "ana"}': n for (a, b), n in pano.items()}))
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cikti', required=True); ap.add_argument('--baslangic', default='2026-11-25')
    ap.add_argument('--simdi', default='2026-11-25 15:00', help='bu andan sonraki ilk slottan baslar (TR saati)')
    ap.add_argument('--oz-test', action='store_true')
    a = ap.parse_args()
    out = plan(date.fromisoformat(a.baslangic), datetime.strptime(a.simdi, '%Y-%m-%d %H:%M'))
    if a.oz_test:
        bozuk = [dict(r) for r in out]
        for j in range(8):                     # 8 pin ayni takvim gununde
            bozuk[j]['tarih_saat_tr'] = '2026-12-01 ' + f'{9 + j:02d}:00'
        k1 = not all(o for _, o, _ in kontrol(bozuk))
        yakin = [dict(r) for r in out]; i = next(j for j, r in enumerate(yakin) if r['tur'] == 'kart' and r['cift'] == 'CANCER_LEO')
        yakin[i]['tarih_saat_tr'] = (datetime.strptime(yakin[0]['tarih_saat_tr'], '%Y-%m-%d %H:%M') + timedelta(days=2)).strftime('%Y-%m-%d %H:%M')
        k2 = not all(o for _, o, _ in kontrol(yakin))
        k0 = all(o for _, o, _ in kontrol(out))
        sa = [dict(r) for r in out]; sa[5]['tarih_saat_tr'] = sa[5]['tarih_saat_tr'][:11] + '11:25'
        k3 = not all(o for _, o, _ in kontrol(sa))
        for ad, v in (('bilinen PASS', k0), ('FAIL: gunde 8 pin', k1), ('FAIL: ayni ilan 2 gun arayla', k2), ('FAIL: 11:25 (ABD gecesi)', k3)):
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if (k0 and k1 and k2 and k3) else 1)
    with open(a.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
    S = kontrol(out)
    for ad, o, d in S:
        print(f"{'PASS' if o else 'FAIL'} {ad} | {d}")
    k = Counter(r['kanal'] for r in out); print('OZET', out[0]['tarih_saat_tr'], '->', out[-1]['tarih_saat_tr'], dict(k))
    eng = [r for r in out if 'HAZIR DEGIL' in r['kanal']]
    print(f'ENGELLI {len(eng)} pin: yayin yolu hazir degil ({dict(Counter(r["tur"] for r in eng))}); 12 Ara sonrasi yol Serdar karari')
    gt = Counter(r['tarih_saat_tr'][:10] for r in out); print('GUNLUK TUR KARISIMI ilk gun', dict(Counter(r['tur'] for r in out if r['tarih_saat_tr'][:10] == out[0]['tarih_saat_tr'][:10])))
    sys.exit(0 if all(o for _, o, _ in S) else 1)


if __name__ == '__main__':
    main()
