"""Yeni altin katmanlari (RGBA) - 25 Kas Pinterest "altin" pininin kaynagi (Merkez 28 Kas).
Kaynak poster: pin78-girdi is akisinin gecici/pin78-girdi dalindaki POSTER_CANCER_LIBRA.jpg
(= Drive TEMP/PIN_V6_20261012/_POSTER2000/CANCER_LIBRA.jpg, 2000x3000, MB). pin78_altin_pin.py:136-138 birlesik sembolu
bu posterden PU.PosterR(poster).layer(P.merged, only_label=False) ile alip YALNIZ KUCULTEREK pine koyar; burada ayni cagri
(kod: logo_wt/sosyal/pin_v6/pin_uret.py:31-77 PosterR, lib.py:20-100 Poster.layer) degistirilmeden kullanilir.
Cikti pin_kaynak/KATMAN_<ad>.png: sembol, burc_a, burc_b, isimler (sonsuz dahil), mesaj, halka.
"""
import os, sys, json
import numpy as np
from PIL import Image
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KOK, '..', 'logo_wt', 'sosyal', 'pin_v6'))
import pin_uret as PU  # noqa: E402

P = PU.PosterR(os.path.join(KOK, 'pin_kaynak', 'POSTER2000_CANCER_LIBRA.jpg'))
parca = {'sembol': (P.merged, False), 'burc_a': (P.sign_a, False), 'burc_b': (P.sign_b, False),
         'isimler': (P.names_row, False), 'mesaj': (P.msg_row, False), 'halka': (P.ring, True)}
bilgi = {}
for ad, (c, ol) in parca.items():
    L = P.layer(c, pad=10, only_label=ol)
    L.save(os.path.join(KOK, 'pin_kaynak', f'KATMAN_{ad}.png'))
    _, x, y, w, h, _ = c
    bilgi[ad] = dict(kutu_poster=[int(x), int(y), int(w), int(h)], boyut=list(L.size), ofset=[int(max(0, x - 10)), int(max(0, y - 10))])
    print(ad, bilgi[ad])
json.dump(bilgi, open(os.path.join(KOK, 'pin_kaynak', 'KATMAN_BILGI.json'), 'w'), indent=1)
