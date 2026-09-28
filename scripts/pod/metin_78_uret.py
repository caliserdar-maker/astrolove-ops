#!/usr/bin/env python3
"""78 ilan icin YALNIZ ACIKLAMA uretimi (28 Eyl duzeltme).
BASLIK ve 13 ETIKET uretilmez: karar Serdar'da verildi ve 78/78 ilanda CANLI
(onayli baslik kalibi: "{A} and {B} Personalized Zodiac Couple Wall Art"); dokunulmaz.
Aciklama: data/pod/aciklama_v3_sablon.txt (canli CL v3) + burc tarihleri.
QC: tire yok, yer tutucu kalmadi. Herhangi FAIL -> cikis 1.
Kullanim: metin_78_uret.py CIKTI_KLASORU CIFT [CIFT ...]   (CIFT: CANCER_LIBRA gibi)
"""
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
TARIH = {
    'ARIES': 'March 21 to April 19', 'TAURUS': 'April 20 to May 20', 'GEMINI': 'May 21 to June 20',
    'CANCER': 'June 21 to July 22', 'LEO': 'July 23 to August 22', 'VIRGO': 'August 23 to September 22',
    'LIBRA': 'September 23 to October 22', 'SCORPIO': 'October 23 to November 21',
    'SAGITTARIUS': 'November 22 to December 21', 'CAPRICORN': 'December 22 to January 19',
    'AQUARIUS': 'January 20 to February 18', 'PISCES': 'February 19 to March 20',
}
SABLON = (KOK / 'data/pod/aciklama_v3_sablon.txt').read_text()


def bas(s):
    return s.capitalize()


def etiket1(a, b):
    for aday in (f'{a} and {b}', f'{a} {b}', f'{min(a, b, key=len)} couple'):
        if len(aday) <= 20:
            return aday
    return f'{min(a, b, key=len)} love'


def etiket2(a, b):
    k = min(a, b, key=len)
    for aday in (f'{a} {b} gift', f'{k} couple gift', f'{k} zodiac gift', f'{k} gift'):
        if len(aday) <= 20:
            return aday
    return f'{k} gift'


def uret(cift):
    A, B = cift.split('_')
    a, b = A.lower(), B.lower()
    Ab, Bb = bas(a), bas(b)
    baslik = f'{Ab} and {Bb} Zodiac Couple Print with Names, Personalized Wall Art, Framed or Digital'
    etiketler = [etiket1(a, b), etiket2(a, b), 'zodiac couple print', 'zodiac couple gift',
                 'personalized couple', 'couple names print', 'zodiac wall art', 'astrology wall art',
                 'anniversary gift', 'wedding gift couple', 'engagement gift', 'framed zodiac art',
                 'zodiac digital file']
    aciklama = SABLON.replace('{A_TARIH}', TARIH[A]).replace('{B_TARIH}', TARIH[B]) \
                     .replace('{A}', Ab).replace('{B}', Bb)
    return baslik, etiketler, aciklama


def qc(cift, baslik, etiketler, aciklama):
    h = []
    if len(etiketler) != 13 or len(set(etiketler)) != 13:
        h.append('etiket sayisi/benzersizlik')
    h += [f'etiket uzun: {e}' for e in etiketler if len(e) > 20]
    if len(baslik) > 140:
        h.append('baslik uzun')
    for ad, m in (('baslik', baslik), ('etiket', ' '.join(etiketler)), ('aciklama', aciklama)):
        if re.search(r'[‒-―−]', m):
            h.append(f'{ad} tire')
    if re.search(r'\{[A-Z_]+\}', aciklama):
        h.append('yer tutucu kaldi')
    return h


def main():
    cik = Path(sys.argv[1]); cik.mkdir(parents=True, exist_ok=True)
    ciftler = sys.argv[2:]
    hata_toplam = 0
    kayit = {}
    for c in ciftler:
        aciklama = uret(c)
        h = qc(c, aciklama)
        kayit[c] = {'aciklama': aciklama, 'qc': h or 'PASS'}
        (cik / f'{c}.txt').write_text(aciklama)
        if h:
            hata_toplam += 1
            print(f'FAIL {c}: {h}')
        else:
            print(f'PASS {c}')
    (cik / 'metinler.json').write_text(json.dumps(kayit, indent=1, ensure_ascii=False))
    print(f'SONUC ' + ('PASS' if hata_toplam == 0 else f'FAIL ({hata_toplam})'))
    sys.exit(1 if hata_toplam else 0)


if __name__ == '__main__':
    main()
