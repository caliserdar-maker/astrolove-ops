#!/usr/bin/env python3
"""yeni_duzen.siparis_murekkep birim testi (plan 2.1b): bilinen PASS + bilinen FAIL + eksik oge FAIL (ANA_2 ders 14).
Kullanim: python -I test_siparis_kapi.py  -> cikis 0 = hepsi beklendigi gibi."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

_s = importlib.util.spec_from_file_location('yd', Path(__file__).resolve().parent / 'yeni_duzen.py')
yd = importlib.util.module_from_spec(_s); _s.loader.exec_module(yd)


def blok(w, h):
    return np.ones((h, w), np.float32)


def E_kur(kaydir_x=0, kaydir_y=0, eksik=None):
    # gercek duzene yakin yerler (SABIT: isim 695-732, tarih 764-795, kucuk alt 663)
    E = {'isim1': (None, blok(120, 37), 300 + kaydir_x, 695 + kaydir_y), 'isim2': (None, blok(120, 37), 540, 695),
         'sonsuz': (None, blok(40, 30), 455, 696), 'kucuk_sol': (None, blok(60, 69), 330, 594), 'kucuk_sag': (None, blok(60, 69), 570, 594),
         'tarih': (None, blok(300, 31), 325, 764)}
    if eksik:
        E.pop(eksik)
    return E


def main():
    vakalar = [('icerde', E_kur(), True), ('isim1_halka_disinda', E_kur(kaydir_x=-200), False),
               ('isim1_asagi_tasma', E_kur(kaydir_y=150), False), ('tarih_eksik', E_kur(eksik='tarih'), False)]
    hata = 0
    for ad, E, bek in vakalar:
        ok, r = yd.siparis_murekkep(E)
        hata += ok != bek
        print('PASS' if ok == bek else 'FAIL', ad, '| beklenen', bek, '| gelen', ok, r, flush=True)
    print('TOPLAM', len(vakalar), 'hata', hata, flush=True)
    return 1 if hata else 0


if __name__ == '__main__':
    sys.exit(main())
