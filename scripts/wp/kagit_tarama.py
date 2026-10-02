#!/usr/bin/env python3
"""WP kagit TARAMASI (salt okur; Serdar onayi 2 Eki, Tani 2): onayli WARM_PARCHMENT kaynak kagidi vs VINTAGE_<boy> plate.

Olcum uretimin plate zemin_uyumu'nun AYNISI (wp_ornek.cift_boy): P0 = wk.boyutla(wk.dizi(plate), kaynak boyutu),
mk = wk.murekkep_maskesi(S - P0, kenar=0), wk.ozet(wk.dE(P0, S), ~mk); esik ort <= 0.5 (tahmin PASS/FAIL).
Koken icin: dosya bilgisi (boyut, dpi, ICC, JPEG alt ornekleme/kalite tahmini) + kagit Lab ortalamasi (murekkep disi).
Isim / mesaj / musteri verisi YOK. Girdi: --dizin altinda <CIFT>.jpg dosyalari. Cikti: JSON satirlari.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def dE_parca(wk, A, B, parca=512):
    out = np.empty(A.shape[:2], np.float32)
    for y in range(0, A.shape[0], parca):
        out[y:y + parca] = wk.dE(A[y:y + parca], B[y:y + parca])
    return out


def bilgi(yol):
    with Image.open(yol) as im:
        q = getattr(im, 'quantization', None) or {}
        icc = im.info.get('icc_profile')
        return {'px': list(im.size), 'dpi': [round(float(v), 1) for v in im.info.get('dpi', (0, 0))],
                'icc_md5': hashlib.md5(icc).hexdigest()[:10] if icc else None,
                'jpeg_q0_ort': round(float(np.mean(q[0])), 2) if 0 in q else None,
                'progressive': bool(im.info.get('progressive') or im.info.get('progression')),
                'yazilim': str(im.info.get('software') or (im.getexif() or {}).get(305, ''))[:40]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wp-kod', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--dizin', required=True)
    ap.add_argument('--cik', required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.wp_kod)
    import wp_katman as wk
    t_tum = time.time()
    pl = wk.dizi(a.plate)
    P_cache = {}
    dosyalar = sorted(Path(a.dizin).glob('*.jpg'))
    with open(a.cik, 'w') as f:
        for i, yol in enumerate(dosyalar):
            t0 = time.time()
            cift = yol.stem
            try:
                S = wk.dizi(yol); H, W = S.shape[:2]
                if (W, H) not in P_cache:
                    P_cache[(W, H)] = wk.boyutla(pl, (W, H))
                P0 = P_cache[(W, H)]
                mk = wk.murekkep_maskesi(S - P0, kenar=0)
                d = dE_parca(wk, P0, S)
                z = wk.ozet(d, ~mk)
                kag = wk.lab(S[~mk][::97].reshape(-1, 1, 3))   # kaynak kagidi Lab (alt ornek)
                kp = wk.lab(P0[~mk][::97].reshape(-1, 1, 3))
                r = {'cift': cift, 'zemin_uyumu': z, 'tahmin': 'PASS' if z.get('ort', 99) <= 0.5 else 'FAIL',
                     'kagit_lab_kaynak': [round(float(v), 2) for v in kag.reshape(-1, 3).mean(0)],
                     'kagit_lab_plate': [round(float(v), 2) for v in kp.reshape(-1, 3).mean(0)],
                     'murekkep_pay': round(float(mk.mean()), 4), 'dosya': bilgi(yol), 'sn': round(time.time() - t0, 1)}
            except Exception as e:                        # noqa: BLE001
                r = {'cift': cift, 'hata': f'{type(e).__name__}: {e}'}
            f.write(json.dumps(r) + '\n'); f.flush()
            g = time.time() - t_tum
            print(f"TARA {i + 1}/{len(dosyalar)} {cift} {r.get('tahmin', 'HATA')} ort {(r.get('zemin_uyumu') or {}).get('ort')} "
                  f"| gecen {g:.0f} sn, kalan ~{g / (i + 1) * (len(dosyalar) - i - 1):.0f} sn, %{100 * (i + 1) / len(dosyalar):.0f}",
                  flush=True)


if __name__ == '__main__':
    main()
