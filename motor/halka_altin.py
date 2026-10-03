#!/usr/bin/env python3
"""Altin edisyon plate'inde halka (cember) katmani + halkasiz zemin (Serdar 3 Eki: TEK DOKU BUTUNLUGU, cember ana
sembolle ayni renk / doku / parlaklikta). BIR KEZ uretilir, sha + kayitla saklanir; render sirasinda zemine dokunulmaz
(yazi cevresi yildiz temizligi haric, Serdar 3 Eki B maddesi).

1) Halka geometrisi: yerel kagittan (medyan pencere 62 x W / 3307) parlak fark > 10 luma, genisligi sayfanin
   >= %35'i olan bilesenler (olc.halka_maskesi ile ayni olcut, genisletmesiz).
2) Halka alfasi: fark / cekirdek ortancasi (0-1), 7 px bolge icinde, gurultu tabani (wb.T0) alti 0.
3) Halkasiz zemin: kilitli wp_bakir.kagit_tabani (yalniz halka altinda inpaint, plate'in geri kalani birebir).
QC (PASS/FAIL): halkasiz zeminde halka bolgesinde kalan parlak fark ortancasi <= 2 luma, p99 <= 8; halka disi birebir.

Kullanim: halka_altin.py --plate PLATES/BLUE_16x20.png --cikti motor/varlik
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
import wp_katman as wk                                                # noqa: E402
import wp_bakir as wb                                                 # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def yerel(L):
    W = L.shape[1]
    kw = 31 if W == 3307 else int(round(62 * W / 3307)) | 1
    return cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), kw).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plate', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    pf = Path(a.plate)
    C = Path(a.cikti)
    P = np.asarray(Image.open(pf).convert('RGB'), np.float32)
    L = P @ wk.LUMA
    H, W = L.shape
    d = L - yerel(L)
    n, lab, st, _ = cv2.connectedComponentsWithStats((np.abs(d) > 10).astype(np.uint8), 8)
    tut = [i for i in range(1, n) if st[i, cv2.CC_STAT_WIDTH] > 0.35 * W and st[i, cv2.CC_STAT_AREA] > 500 * (W / 3307) ** 2]
    daire = np.isin(lab, tut)
    mc = np.clip(d, 0, None)
    bolge = cv2.dilate(daire.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    ce = cv2.erode(daire.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    Lk = float(np.median(mc[ce if ce.sum() > 500 else daire]))
    alfa = np.clip(mc / max(Lk, 1.0), 0, 1) * bolge
    alfa[mc < wb.T0] = 0
    ad = pf.stem
    (C / 'halka').mkdir(parents=True, exist_ok=True); (C / 'plates').mkdir(parents=True, exist_ok=True)
    hf = C / 'halka' / f'HALKA_{ad}.png'
    Image.fromarray(np.round(alfa * 255).astype(np.uint8), 'L').save(hf)
    P1, dd = wb.kagit_tabani(P, alfa > 0.02)
    zf = C / 'plates' / f'{ad}_halkasiz.png'
    Image.fromarray(np.clip(np.round(P1), 0, 255).astype(np.uint8)).save(zf)
    P1 = np.asarray(Image.open(zf).convert('RGB'), np.float32)
    L1 = P1 @ wk.LUMA
    kal = np.clip(L1 - yerel(L1), 0, None)[alfa > 0.5]
    disari = np.abs(P1 - P).max(2)[~cv2.dilate(dd.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)]
    qc = {'halka_kalan_ortanca': round(float(np.median(kal)), 2), 'halka_kalan_p99': round(float(np.percentile(kal, 99)), 2),
          'halka_disi_degisen_px': int((disari > 0).sum())}
    qc['gecti'] = qc['halka_kalan_ortanca'] <= 2 and qc['halka_kalan_p99'] <= 8 and qc['halka_disi_degisen_px'] == 0
    R = {'kaynak_plate': {'dosya': f'TEMP/SIPARIS_ISIM/PLATES/{pf.name}', 'sha256': sha(pf)},
         'halka': {'dosya': str(hf.relative_to(KOK.parent)) if hf.is_absolute() else str(hf), 'sha256': sha(hf),
                   'Lk': round(Lk, 2), 'px': int((alfa > 0.02).sum())},
         'halkasiz_zemin': {'dosya': str(zf), 'sha256': sha(zf)}, 'qc': qc}
    (C / 'plates' / f'{ad}_halkasiz.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, indent=1, ensure_ascii=False))
    sys.exit(0 if qc['gecti'] else 1)


if __name__ == '__main__':
    main()
