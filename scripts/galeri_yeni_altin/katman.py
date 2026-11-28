"""Yeni altin katmanlari (RGBA): Merkez pilotu scripts/altin_pilot/pin_katman.py (dal altin-pilot-kaynak c964f94a) depo uyarlamasi.
Ayni cagri, degistirilmeden: sosyal/pin_v6/pin_uret.py PosterR(poster).layer(parca, pad=10, only_label=...).
Degisen yalniz yollar: --poster (cift basina Drive TEMP/PIN_V6_20261012/_POSTER2000/<CIFT>.jpg), --cikti.
Cikti <cikti>/KATMAN_<ad>.png (sembol, burc_a, burc_b, isimler, mesaj, halka) + KATMAN_BILGI.json.
Kullanim: python katman.py --poster POSTER2000_<CIFT>.jpg --cikti DIR
"""
import argparse, json, os, sys
KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'sosyal', 'pin_v6'))
import pin_uret as PU  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--poster', required=True)
ap.add_argument('--cikti', required=True)
a = ap.parse_args()
os.makedirs(a.cikti, exist_ok=True)
P = PU.PosterR(a.poster)
parca = {'sembol': (P.merged, False), 'burc_a': (P.sign_a, False), 'burc_b': (P.sign_b, False),
         'isimler': (P.names_row, False), 'mesaj': (P.msg_row, False), 'halka': (P.ring, True)}
bilgi = {}
for ad, (c, ol) in parca.items():
    L = P.layer(c, pad=10, only_label=ol)
    L.save(os.path.join(a.cikti, f'KATMAN_{ad}.png'))
    _, x, y, w, h, _ = c
    bilgi[ad] = dict(kutu_poster=[int(x), int(y), int(w), int(h)], boyut=list(L.size), ofset=[int(max(0, x - 10)), int(max(0, y - 10))])
    print(ad, bilgi[ad])
json.dump(bilgi, open(os.path.join(a.cikti, 'KATMAN_BILGI.json'), 'w'), indent=1)
