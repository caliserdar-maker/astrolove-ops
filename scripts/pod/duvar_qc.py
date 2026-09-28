#!/usr/bin/env python3
"""Kapak duvari zeminli galeri gorselleri icin tek QC (PASS/FAIL, her gorsel; Serdar 28 Eyl).
 - 3000x2250
 - krem hale yok: nesne kutulari disinda, ciktida (237,232,226)+-3 olup duvarda o piksel boyle olmayan piksel <= 50
 - poster NCC >= 0.99: CIKIS.json poster kutulari, onayli (eski) gorselle ayni kutu; iki tarafta sigma1 Gauss,
   kenardan 20 px ic, +-3 px hiza taramasi (kapak_v8_kur.py yontemi)
 - yazi kontrasti >= 4.5: her satirin rengi, kutusunun arkasindaki duvarin en koyu %5'ine karsi (WCAG)
 - tire yok (uzun/orta tire, eksi)
 - kose zemini secilen ZEMIN ile ayni (+-6, 4 kose); kapakla parlaklik farki bilgi olarak: yan seritlerde (x<500,
   x>2500) ortalama L* farki (kapakta orta alan poster oldugu icin yan seritler)
Kullanim: duvar_qc.py ZEMIN.png KAPAK_SAHNE_V9.png CIKIS1.jpg ESKI1.jpg [CIKIS2.jpg ESKI2.jpg ...]
  ZEMIN: kartlarin kuruldugu duvar (leke seviyeli 3000x2250 ya da kapak_sahne_v9.png)
"""
import json
import os
import re
import sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import KREM, duvar, duvar_lum, kontrast, lum

D = duvar(sys.argv[1]); Dz = np.asarray(D).astype(np.int16)
Kz = np.asarray(duvar(sys.argv[2], 'yok', None)).astype(np.int16)   # kapak duvari (orijinal, ham)
ciftler = list(zip(sys.argv[3::2], sys.argv[4::2]))


def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))


def krem(a):
    return (np.abs(a - np.array(KREM)) <= 3).all(2)


import cv2 as _c
_yan = np.zeros((2250, 3000), bool); _yan[:, :500] = True; _yan[:, 2500:] = True
_L = lambda a: _c.cvtColor(a.astype(np.float32) / 255, _c.COLOR_RGB2Lab)[..., 0][_yan].mean()
dL_kapak = _L(Dz) - _L(Kz)
print(f'zemin: yan seritler L* {_L(Dz):.1f} | kapak duvari L* {_L(Kz):.1f} | kapakla parlaklik farki dL* {dL_kapak:+.1f}')
hepsi = True
for cik, eski in ciftler:
    R = np.asarray(Image.open(cik).convert('RGB')).astype(np.int16)
    E = np.asarray(Image.open(eski).convert('RGB')).astype(np.float32)
    J = json.load(open(os.path.splitext(cik)[0] + '.json'))
    # hale: nesne kutulari (poster, panel, cerceve, boy kutusu) DISINDA kalan krem; kutu ici krem tasarimin kendisi
    nes = np.zeros(R.shape[:2], bool)
    for x, y, w, h in J['poster'] + J.get('kutu', []):
        nes[y:y + h, x:x + w] = True
    hale = int((krem(R) & ~krem(Dz) & ~nes).sum())
    Rg = cv2.GaussianBlur(R.astype(np.float32).mean(2), (0, 0), 1.0); Eg = cv2.GaussianBlur(E.mean(2), (0, 0), 1.0)
    nler = []
    for x, y, w, h in J['poster']:
        P = Eg[y + 20:y + h - 20, x + 20:x + w - 20]
        nler.append(max(ncc(Rg[y + 20 + j:y + h - 20 + j, x + 20 + i:x + w - 20 + i], P)
                        for i in range(-3, 4) for j in range(-3, 4)))
    # zemin_lum: kartin gercek zemini (kutu ici yari saydam ton dahil, kart_duvar_genel); ayirici cizgiler (acik) yazi degil
    kon = [(s.get('metin', f"satir@{s['kutu'][0]},{s['kutu'][1]}"),
            kontrast(float(lum(np.array(s['renk']))), s['zemin_lum'] if 'zemin_lum' in s else duvar_lum(D, s['kutu'])))
           for s in J['satirlar'] if not s.get('acik')]
    kmin = min(k for _, k in kon)
    tire = bool(re.search(r'[\u2012-\u2015\u2212]', ' '.join(s.get('metin', '') for s in J['satirlar'])))   # metin dokumu: metin_qc.py
    kose = max(int(np.abs(R[y, x] - Dz[y, x]).max()) for x, y in [(60, 60), (2940, 60), (60, 2190), (2940, 2190)])
    renk_deg = [f"{s.get('metin', 'satir')[:22]} {tuple(s['onayli_renk'])}->{tuple(s['renk'])}" for s in J['satirlar'] if list(s['renk']) != s['onayli_renk']]
    ok = R.shape[:2] == (2250, 3000) and hale <= 50 and min(nler, default=1.0) >= 0.99 and kmin >= 4.5 and not tire and kose <= 6
    hepsi &= ok
    print(f"{os.path.basename(cik)}: boyut {R.shape[1]}x{R.shape[0]} | krem hale {hale} px | poster NCC "
          f"{' '.join(f'{v:.4f}' for v in nler)} | kontrast min {kmin:.2f} ({min(kon, key=lambda z: z[1])[0][:24]}) | "
          f"tire {tire} | kose fark {kose} | koyulasan renk {len(renk_deg)}: {'; '.join(renk_deg) or '-'} | {'PASS' if ok else 'FAIL'}")
    print('   kontrast: ' + ' | '.join(f'{m[:18]} {k:.2f}' for m, k in kon))
print('GENEL', 'PASS' if hepsi else 'FAIL')
sys.exit(0 if hepsi else 1)
