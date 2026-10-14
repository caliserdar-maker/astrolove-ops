#!/usr/bin/env python3
""""Bizim Yilimiz" 78 ilan icin Pinterest pin TASLAK plani (14 Eki 2026). YAYIN YOK; link bos (ilanlar henuz yayinda degil).
Girdi: ilan metni (bizim-yilimiz-v3 BIZIM_YILIMIZ_78_ILAN_METIN.csv), galeri listesi (rclone lsjson), mevcut V6 pin plani.
- Gorsel: --gorsel onekiyle eslesen galeri dosyasi (varsayilan 09_Size_Gift_Scene; kapak duzeltmesinden bagimsiz).
- Metin: ilan grubuna (A kocaya, B sevgiliye, C 1. evlilik yildonumu) gore 3 sablon; V6 poster pin metinleriyle ayni olamaz.
- Takvim: gunde 3 pin, V6 saatleriyle cakismayan yeni slotlar (12:30, 16:15, 19:15 Europe/Istanbul); her gun A/B/C birer;
  ayni gun V6'da pini olan cift o gune konmaz; art arda iki pin ayni burcu paylasmaz.
Kontrol: 78 satir, tekil cift, baslik<=100, aciklama<=500, uzun/orta tire yok, '&amp;' yok, V6 ile ayni an yok ve >=30 dk ara.
Kullanim: by78_pin_plan.py --metin M.csv --galeri GALERI.json --v6 PIN_V6_PLAN.csv --cikti PIN_PLAN_BY78.csv [--baslangic 2026-10-16]"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

SLOT = {'A': '12:30', 'B': '16:15', 'C': '19:15'}
BOARD = '1st Anniversary Gift Ideas'
YASAK = ['—', '–', '&amp;', 'OBA', 'bright white', 'museum', 'foil', '12-colour', 'gold', 'printable']  # gold: 5 stilden 3'u altin degil; printable: format adi digital card (14 Eki)

BASLIK = {
    'A': '1st Anniversary Gift for Husband, {a} & {b} Zodiac Paper Anniversary Print with Names',
    'B': 'One Year Anniversary Gift for Boyfriend, {a} & {b} Zodiac Couple Card with Your Names',
    'C': 'First Wedding Anniversary Gift, {a} & {b} Zodiac Print with Your Names and Date',
}
ACIKLAMA = {
    'A': ('Celebrating your first year together? This paper anniversary gift turns your two signs, {a} and {b}, '
          'into one shared zodiac symbol with your names and your wedding date. Choose from 5 styles: Starlit, '
          'Timeless, First Page, Layers and Botanical. Get it as a 5x7 digital card, an 8x10 digital file or a '
          'shipped 8x10 print. Free preview before you order. Personalized 1st anniversary gift for your husband or your wife by AstroLoveArt.'),
    'B': ('One year of you two. Your signs, {a} and {b}, become one shared zodiac symbol with both of your names and '
          'the day you met, a sweet one year anniversary gift for your boyfriend or your girlfriend. 5 styles to choose '
          'from, as a 5x7 digital card, an 8x10 digital file or a shipped 8x10 print. Ask for a free preview of your '
          'design first. Personalized zodiac couple gift by AstroLoveArt.'),
    'C': ('Paper is the traditional gift for the first wedding anniversary. This personalized print joins {a} and '
          '{b} into one shared zodiac symbol, with your two names and your wedding date. Pick one of 5 styles and '
          'get it as a 5x7 digital card, an 8x10 digital file or a shipped 8x10 print. Free preview before you order. '
          'A keepsake for your first year of marriage by AstroLoveArt.'),
}


def main():
    ap = argparse.ArgumentParser()
    for k in ('metin', 'galeri', 'v6', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--baslangic', default='2026-10-16')
    ap.add_argument('--gorsel', default='09_Size_Gift_Scene')
    a = ap.parse_args()
    M = list(csv.DictReader(open(a.metin, encoding='utf-8-sig')))
    G = json.load(open(a.galeri))
    V6 = list(csv.DictReader(open(a.v6, encoding='utf-8')))
    hata = []
    galeri = defaultdict(list)
    for x in G:
        galeri[x['Path'].split('/')[0]].append(x['Name'])
    v6_an = [datetime.fromisoformat(r['tarih_saat'].replace(' ', 'T')) for r in V6]
    v6_gun = defaultdict(set)
    for r, t in zip(V6, v6_an):
        v6_gun[t.date()].add(r['cift'])
    v6_metin = {r['baslik'] for r in V6} | {r['aciklama'] for r in V6}

    satir = {}
    for r in M:
        c, g = r['cift'], r['grup']
        A, B = (s.capitalize() for s in c.split('_'))
        adlar = sorted(n for n in galeri.get(c, []) if n.startswith(a.gorsel))
        if len(adlar) != 1:
            hata.append(f'{c}: {a.gorsel} gorseli {len(adlar)} adet ({sorted(galeri.get(c, []))[:3]})')
        satir[c] = {'cift': c, 'grup': g, 'gorsel': f"BIZIM_YILIMIZ_78_20261014_v2/{c}/galeri/{adlar[0] if adlar else '?'}",
                    'baslik': BASLIK[g].format(a=A, b=B), 'aciklama': ACIKLAMA[g].format(a=A, b=B), 'board': BOARD}

    # takvim: her gun A/B/C birer; V6 ayni gun cakismasi ve art arda ortak burc yok
    gruplar = {g: sorted(c for c, s in satir.items() if s['grup'] == g) for g in 'ABC'}
    if {g: len(v) for g, v in gruplar.items()} != {'A': 26, 'B': 26, 'C': 26}:
        hata.append(f'grup sayilari {[(g, len(v)) for g, v in gruplar.items()]}')
    bas = date.fromisoformat(a.baslangic)
    sira, onceki = [], None

    def uygun(c, gun, onceki):
        if c in v6_gun.get(gun, set()):
            return False
        return not (onceki and set(c.split('_')) & set(onceki.split('_')))
    kalan = {g: list(v) for g, v in gruplar.items()}
    for d in range(26):
        gun = bas + timedelta(days=d)
        for g in 'ABC':
            aday = [c for c in kalan[g] if uygun(c, gun, onceki)] or \
                   [c for c in kalan[g] if c not in v6_gun.get(gun, set())] or kalan[g]
            # V6'da en yakin pin gunu en uzak olan cift once (gorunurluk tekrari azalsin)
            aday.sort(key=lambda c: (-min((abs((t.date() - gun).days) for r, t in zip(V6, v6_an) if r['cift'] == c), default=99), c))
            c = aday[0]
            kalan[g].remove(c)
            satir[c]['tarih_saat'] = f'{gun} {SLOT[g]}'
            sira.append(c); onceki = c

    out = [dict(satir[c], link='') for c in sira]
    # kontroller
    if len(out) != 78 or len({r['cift'] for r in out}) != 78:
        hata.append(f'satir {len(out)} / tekil {len({r["cift"] for r in out})}')
    for r in out:
        if len(r['baslik']) > 100: hata.append(f"baslik {r['cift']} {len(r['baslik'])}")
        if len(r['aciklama']) > 500: hata.append(f"aciklama {r['cift']} {len(r['aciklama'])}")
        for y in YASAK:
            if y.lower() in (r['baslik'] + r['aciklama']).lower(): hata.append(f"yasak '{y}' {r['cift']}")
        if r['baslik'] in v6_metin or r['aciklama'] in v6_metin: hata.append(f"V6 ile ayni metin {r['cift']}")
        t = datetime.fromisoformat(r['tarih_saat'].replace(' ', 'T'))
        yakin = min(abs((t - v).total_seconds()) for v in v6_an) / 60 if v6_an else 999
        if yakin < 30: hata.append(f"V6'ya {yakin:.0f} dk yakin {r['tarih_saat']}")
        if r['cift'] in v6_gun.get(t.date(), set()): hata.append(f"ayni gun V6 pini {r['cift']} {t.date()}")
    ortak = sum(1 for i in range(1, len(sira)) if set(sira[i].split('_')) & set(sira[i - 1].split('_')))
    with open(a.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['cift', 'gorsel', 'baslik', 'aciklama', 'board', 'tarih_saat', 'link'],
                           extrasaction='ignore', lineterminator='\n')
        w.writeheader(); w.writerows(out)
    gun_say = Counter(r['tarih_saat'][:10] for r in out)
    print(f"PLAN {len(out)} satir; {out[0]['tarih_saat']} -> {out[-1]['tarih_saat']} (Europe/Istanbul); gunde {sorted(set(gun_say.values()))} pin; "
          f"slotlar {sorted(set(SLOT.values()))}; V6 plan {len(V6)} pin {min(v6_an)} -> {max(v6_an)}; art arda ortak burc {ortak}; "
          f"baslik max {max(len(r['baslik']) for r in out)}, aciklama max {max(len(r['aciklama']) for r in out)}")
    for r in out[:3]:
        print(f"ORNEK {r['tarih_saat']} {r['cift']} | {r['gorsel']}\n  {r['baslik']} ({len(r['baslik'])})\n  {r['aciklama']} ({len(r['aciklama'])})")
    print('KONTROL ' + ('PASS' if not hata else 'FAIL: ' + '; '.join(hata[:15])))
    sys.exit(1 if hata else 0)


if __name__ == '__main__':
    main()
