#!/usr/bin/env python3
"""siparis_girdi.py birim testi: bilinen PASS + bilinen DUR (ANA_2 ders 14). Test adlari kurgusal (EMILY / JAMES ve karar test adlari).
Kullanim: python -I test_siparis_girdi.py  -> cikis 0 = hepsi PASS."""
import importlib.util
import sys
from pathlib import Path

_s = importlib.util.spec_from_file_location('sg', Path(__file__).resolve().parent / 'siparis_girdi.py')
sg = importlib.util.module_from_spec(_s); _s.loader.exec_module(sg)

BAZ = dict(cift='CANCER_LIBRA', stil='RUBY', isim1='Emily', isim2='James', tarih='June 14, 2025')


def kos(degisim):
    g = dict(BAZ); g.update(degisim)
    try:
        r = sg.dogrula(g)
        return ('PASS', r)
    except sg.Dur as d:
        return (d.kod + ':' + d.neden, None)


VAKALAR = [
    # (ad, degisim, beklenen durum, beklenen alan degerleri)
    ('baz', {}, 'PASS', dict(isim1='EMILY', isim2='JAMES', tarih='JUNE 14, 2025')),
    ('kucuk_harf_tarih', dict(tarih='june 14 2025'), 'PASS', dict(tarih='JUNE 14, 2025')),
    ('gun_once', dict(tarih='14 June 2025'), 'PASS', dict(tarih='JUNE 14, 2025')),
    ('ek_th', dict(tarih='june 14th, 2025'), 'PASS', dict(tarih='JUNE 14, 2025')),
    ('kisaltma', dict(tarih='Sept 10 2026'), 'PASS', dict(tarih='SEPTEMBER 10, 2026')),
    ('en_uzun_ay', dict(tarih='SEPTEMBER 10, 2026'), 'PASS', dict(tarih='SEPTEMBER 10, 2026')),
    ('en_genis_2007', dict(tarih='September 10, 2007'), 'PASS', dict(tarih='SEPTEMBER 10, 2007')),
    ('tire_kesme', dict(isim1='Mary-Jane', isim2="O'Neil"), 'PASS', dict(isim1='MARY-JANE', isim2="O'NEIL")),
    ('ayni_burc', dict(cift='LEO_LEO'), 'PASS', dict(cift='LEO_LEO')),
    ('stil_bosluklu', dict(stil='sade altin'), 'PASS', dict(stil='SADE_ALTIN')),
    ('sondaki_bosluk', dict(isim1='  Emily '), 'PASS', dict(isim1='EMILY')),
    ('rakamla_tarih', dict(tarih='06/07/2025'), 'DUR_GIRDI:rakamla_tarih', None),
    ('iso_tarih', dict(tarih='2025-06-14'), 'DUR_GIRDI:rakamla_tarih', None),
    ('gun_yok', dict(tarih='June 2025'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('iki_haneli_yil', dict(tarih='June 14 25'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('takvimde_yok', dict(tarih='february 30 2026'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('subat29_artik_degil', dict(tarih='February 29, 2025'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('subat29_artik', dict(tarih='February 29, 2024'), 'PASS', dict(tarih='FEBRUARY 29, 2024')),
    ('ay_yazim_hatasi', dict(tarih='Jnue 14 2025'), 'DUR_SERDAR:ay_okunamadi', None),
    ('aksan', dict(isim1='ÇAĞLAYANGÜL'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('bosluk', dict(isim1='Mary Ann'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('kivrik_kesme', dict(isim2='O’Neil'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('eszet', dict(isim1='Strauß'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('noktasiz_i', dict(isim1='Iıl'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('rakam', dict(isim1='Emily2'), 'DUR_SERDAR:izinsiz_karakter', None),
    ('yalniz_tire', dict(isim1='-'), 'DUR_SERDAR:harf_yok', None),
    ('bos_isim', dict(isim2=''), 'DUR_SERDAR:eksik_alan', None),
    ('eksik_isim', dict(isim2=None), 'DUR_SERDAR:eksik_alan', None),
    ('bos_tarih', dict(tarih=' '), 'DUR_SERDAR:eksik_alan', None),
    ('istisna_GS', dict(cift='GEMINI_SAGITTARIUS'), 'DUR_SERDAR:istisna_cifti_K7', None),
    ('istisna_GV', dict(cift='GEMINI_VIRGO'), 'DUR_SERDAR:istisna_cifti_K7', None),
    ('cift_alfabetik_degil', dict(cift='LIBRA_CANCER'), 'DUR_SERDAR:cift_gecersiz', None),
    ('stil_yok', dict(stil='ONYX'), 'DUR_SERDAR:stil_gecersiz', None),
    ('sira_ters', dict(sira='ters'), 'DUR_SERDAR:sira_ters_K5', None),
    ('yil_0025', dict(tarih='June 14 0025'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('yil_2200', dict(tarih='June 14 2200'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('tam_genislik_rakam', dict(tarih='June \uff11\uff14 2025'), 'DUR_SERDAR:gecersiz_tarih', None),
    ('tire_kenar', dict(isim1='-A-'), 'DUR_SERDAR:kenar_isaret', None),
    ('kesme_bas', dict(isim1="'Neil"), 'DUR_SERDAR:kenar_isaret', None),
    ('cift_tire', dict(isim1='Mary--Jane'), 'DUR_SERDAR:kenar_isaret', None),
]


def main():
    hata = 0
    for ad, deg, bek, alanlar in VAKALAR:
        dur, r = kos(deg)
        ok = dur == bek and (alanlar is None or all(r.get(k) == v for k, v in alanlar.items()))
        hata += not ok
        print(('PASS' if ok else 'FAIL'), ad, '| beklenen', bek, '| gelen', dur, flush=True)
    n_pass = sum(1 for v in VAKALAR if v[2] == 'PASS'); n_dur = len(VAKALAR) - n_pass
    print(f'TOPLAM {len(VAKALAR)} vaka (bilinen PASS {n_pass}, bilinen DUR {n_dur}), hata {hata}', flush=True)
    return 1 if hata or n_pass == 0 or n_dur == 0 else 0


if __name__ == '__main__':
    sys.exit(main())
