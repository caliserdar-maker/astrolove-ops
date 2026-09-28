#!/usr/bin/env python3
"""78 ilan icin YALNIZ ACIKLAMA uretimi (28 Eyl duzeltme).
BASLIK ve 13 ETIKET uretilmez: karar Serdar'da verildi ve 78/78 ilanda CANLI
(onayli baslik kalibi: "{A} and {B} Personalized Zodiac Couple Wall Art"); dokunulmaz.
Aciklama: data/pod/aciklama_v3_sablon.txt (canli CL v3) + burc tarihleri.
Ayni burc cifti (Serdar 28 Eyl): burc tarih satiri TEK yazilir ("Leo: July 23 to August 22.").
QC: tire yok, yer tutucu kalmadi, ayni cumle iki kez yok. Herhangi FAIL -> cikis 1.
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


def uret(cift):
    A, B = cift.split('_')
    Ab, Bb = bas(A.lower()), bas(B.lower())
    metin = SABLON
    if A == B:
        metin = metin.replace('{A}: {A_TARIH}. {B}: {B_TARIH}.', '{A}: {A_TARIH}.')
    return metin.replace('{A_TARIH}', TARIH[A]).replace('{B_TARIH}', TARIH[B]) \
                .replace('{A}', Ab).replace('{B}', Bb)


def tekrar_eden_cumleler(metin):
    """Ayni cumle (>= 12 karakter) metinde iki kez geciyorsa listeler."""
    cumleler = [c.strip() for satir in metin.splitlines() for c in re.split(r'(?<=[.!?])\s+', satir)]
    say = {}
    for c in cumleler:
        if len(c) >= 12:
            say[c] = say.get(c, 0) + 1
    return sorted(c for c, n in say.items() if n > 1)


def qc(cift, aciklama):
    h = []
    if re.search(r'[\u2012-\u2015\u2212]', aciklama):
        h.append('tire')
    if re.search(r'\{[A-Z_]+\}', aciklama):
        h.append('yer tutucu kaldi')
    tekrar = tekrar_eden_cumleler(aciklama)
    if tekrar:
        h.append(f'ayni cumle iki kez: {tekrar[:2]}')
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
