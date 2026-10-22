#!/usr/bin/env python3
"""05 karti (duvar zemini) kucuk resim halkasi temizligi (Serdar 1 Eki: CI/WP kucuk resimlerinde kenar tasmasi).
Neden: krem 05'teki onayli CL kucuk resimlerinin JPEG halesi ve krem ara dosyanin JPEG kaydi, kucuk resmin 1-7 px
disinda kremden 4-20 farkli acik pikseller birakir; kart_duvar_genel bunlari 'duz acik dolgu' sayip aynen korur ->
duvar uzerinde acik benek (CI/WP acik posterlerde; MB/DB/PW'de yok). Duzeltme: her kucuk resmin disindaki HALKA px
halkada R+G+B > ESIK olan pikseller ayni koordinattaki duvar zemini (duvar_zemin.duvar) ile degisir. PW kucuk resminin
onayli ince gri konturu (R+G+B ~ 595) ESIK altinda kalir, degismez. Kucuk resim ici (poster) dokunulmaz.
Kullanim: galeri77_halka.py KART05.jpg KAPAK_SAHNE_V9.png   (yerinde yazar; tek satir rapor)
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import duvar          # noqa: E402

KUTULAR = [(145 + i * 570, 470, 430, 537) for i in range(5)]     # galeri77_kur.kart05 ile ayni
HALKA, ESIK = 14, 650

if __name__ == '__main__':
    K, Z = sys.argv[1:3]
    a = np.asarray(Image.open(K).convert('RGB')).copy()
    d = np.asarray(duvar(Z).convert('RGB'))
    n = 0
    for x, y, w, h in KUTULAR:
        m = np.zeros(a.shape[:2], bool)
        m[y - HALKA:y + h + HALKA, x - HALKA:x + w + HALKA] = True
        m[y:y + h, x:x + w] = False
        m &= a.astype(np.int32).sum(2) > ESIK
        a[m] = d[m]; n += int(m.sum())
    Image.fromarray(a).save(K, quality=95, subsampling=0)
    print(f'05 halka: {n} px duvar zeminine alindi')
