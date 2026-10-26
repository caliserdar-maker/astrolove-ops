#!/usr/bin/env python3
"""5x7 ORNEK (Merkez 26 Eki; yayina girmez): siparis hattinin A4 cikisindan (A oranı 1:1.4142) 5x7 (1:1.4) dosya.
Yontem: yalniz dikey merkez kirpma (A4 2480x3508 -> 2480x3472, ust/alt 18 px = %1), sonra 1500x2100 INTER_AREA,
JPEG q95 4:4:4, 300 dpi. Kapi: olcu 1500x2100, dpi 300, kirpilan bantlarda murekkep yok (bant ile bitisik ic serit
ortalama mutlak farki <= 6 ve bantta |piksel - serit medyani| > 40 olan piksel orani <= taban x 1,5 + %0,1; taban = ayni
olcumun bir ic seritte (doku tabani: WP/CI kagit dokusu) degeri; 2. iterasyon 26 Eki, 1. surum duz zemine gore FAIL verdi).
Kullanim: a4_5x7.py GIRDI.jpg CIKTI.jpg -> stdout JSON (kapi)."""
import json, sys
import numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HW, HH = 1500, 2100


def main(g, c):
    A = np.asarray(Image.open(g).convert('RGB'))
    h, w = A.shape[:2]
    hh = int(round(w * 7 / 5))
    k = h - hh
    ust = k // 2; alt = k - ust
    bant = [A[:ust], A[h - alt:]] if k > 0 else []
    serit = [A[ust:2 * ust], A[h - 2 * alt:h - alt]] if k > 0 else []
    serit2 = [A[2 * ust:3 * ust], A[h - 3 * alt:h - 2 * alt]] if k > 0 else []
    ink, taban, fark = [], [], []
    for b, s, s2 in zip(bant, serit, serit2):
        med = np.median(s.reshape(-1, 3), 0)
        ink.append(float((np.abs(b.astype(np.int16) - med).max(2) > 40).mean()))
        taban.append(float((np.abs(s2.astype(np.int16) - med).max(2) > 40).mean()))
        fark.append(float(np.abs(b.astype(np.float32).mean((0, 1)) - s.astype(np.float32).mean((0, 1))).mean()))
    K = A[ust:h - alt]
    O = cv2.resize(K, (HW, HH), interpolation=cv2.INTER_AREA)
    Image.fromarray(O).save(c, 'JPEG', quality=95, subsampling=0, dpi=(300, 300))
    r = Image.open(c)
    kapi = {'girdi': [w, h], 'kirpma_px': [ust, alt], 'cikti': list(r.size), 'dpi': [round(x) for x in r.info.get('dpi', (0, 0))],
            'bant_murekkep_orani': [round(x, 5) for x in ink], 'doku_tabani': [round(x, 5) for x in taban], 'bant_serit_fark': [round(x, 2) for x in fark]}
    kapi['PASS'] = (tuple(r.size) == (HW, HH) and kapi['dpi'] == [300, 300] and 0 <= k <= 0.02 * h
                    and all(x <= t * 1.5 + 0.001 for x, t in zip(ink, taban)) and all(x <= 6 for x in fark))
    print(json.dumps(kapi))
    return 0 if kapi['PASS'] else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
