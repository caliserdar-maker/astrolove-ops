#!/usr/bin/env python3
"""Halka (daire) katmani + halkasiz temiz zemin (Serdar 3 Eki: halka da bakir, Test 5'teki gibi). BIR KEZ uretilir,
sha + kayitla saklanir; motor render sirasinda zemine dokunmaz.

1) Halka geometrisi: kilitli wp_bakir.daire_maskesi, duz (dokusuz) CI plate'inden (PLATES/MODERN_<boy>.png).
   Hiza olculdu (3 Eki): WP temiz zemininde ve Test 5'te halka en koyu dx=0, dy=0.
2) Halka katmani: CI plate'inde murekkep gucu (yerel medyan kagit - luma), cekirdek ortancasina bolunur -> alfa 0-1
   (motor/varlik/halka/HALKA_<boy>.png, 8 bit).
3) Halkasiz zemin: temiz zemin + kilitli wp_bakir.kagit_tabani (yalniz halka cizgisinin altinda inpaint, kagidin
   geri kalani birebir) -> motor/varlik/plates/<plate>_temiz_halkasiz.png
QC (PASS/FAIL): halka kalintisi (kilitli wp_katman.plate_iz, halka maskesi, oran <= 1.25); orijinalde olmayan cizgi
(plate_temizle.kusur_bul) = 0; halka disi kagit dE(zemin, orijinal) ort <= 0.5.

Kullanim: halka.py --kaynak DIR --sabit motor/sabitler/X.json --boy 11x14
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
sys.path.insert(0, str(KOK))
import wp_katman as wk                                                # noqa: E402
import wp_bakir as wb                                                 # noqa: E402
from olc import murekkep                                              # noqa: E402
from plate_temizle import kusur_bul                                   # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def oku(f):
    return np.asarray(Image.open(f).convert('RGB'), np.float32)


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--boy', default='11x14')
    ap.add_argument('--orijinal', help='orijinal WP posteri (varsayilan KAYNAK/orijinal_WP_11x14.jpg)')
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    kok = KOK.parent
    zemin0 = kok / Z['zemin']['dosya']
    if Z['zemin'].get('halkasiz'):
        sys.exit('FAIL: sabitlerdeki zemin zaten halkasiz (tek seferlik uretim)')
    if sha(zemin0) != Z['zemin']['sha256']:
        sys.exit('FAIL: temiz zemin sha uyusmuyor')
    Pc = oku(K / 'plates' / f'MODERN_{a.boy}.png')
    Lc = Pc @ wk.LUMA
    H, W = Lc.shape
    # yerel kagit: 31 px medyan (11x14; halka tepesi 15 px = pencerenin %48'i, sinirda). Buyuk boyda pencere
    # 2 x 31 x boy orani (3 Eki: 24x36 tepe 35 px, 67 px pencerede %52 -> medyan halkanin kendisi, tepe alfasi 0)
    kw = 31 if W == 3307 else int(round(62 * W / 3307)) | 1
    z = cv2.medianBlur(np.clip(Lc, 0, 255).astype(np.uint8), kw).astype(np.float32)
    mc = np.clip(z - Lc, 0, None)
    if W == 3307:
        daire = wb.daire_maskesi(Pc)
    else:
        # kilitli wp_bakir.daire_maskesi olcutu (yerel kontrast > 10, genislik >= %35, alan > 500), yerel kagit
        # penceresi boyla olceklenmis (yukarida); 3 Eki: 3307'ye indirilmis maske 24x36 tepesini kaciriyordu
        n, lab, st, _ = cv2.connectedComponentsWithStats((mc > 10).astype(np.uint8), 8)
        q2 = (W / 3307) ** 2
        tut = [i for i in range(1, n) if st[i, cv2.CC_STAT_WIDTH] > 0.35 * W and st[i, cv2.CC_STAT_AREA] > 500 * q2]
        daire = np.isin(lab, tut)
    bolge = cv2.dilate(daire.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    ce = cv2.erode(daire.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    Lk = float(np.median(mc[ce if ce.sum() > 500 else daire]))
    alfa = np.clip(mc / max(Lk, 1.0), 0, 1) * bolge
    alfa[mc < wb.T0] = 0
    hd = KOK / 'varlik' / 'halka'; hd.mkdir(parents=True, exist_ok=True)
    hf = hd / f'HALKA_{a.boy}.png'
    Image.fromarray(np.round(alfa * 255).astype(np.uint8), 'L').save(hf)

    P0 = oku(zemin0)
    P1, _ = wb.kagit_tabani(P0, daire)
    zf = zemin0.with_name(zemin0.stem + '_halkasiz.png')
    Image.fromarray(np.clip(np.round(P1), 0, 255).astype(np.uint8)).save(zf)
    P1 = oku(zf)

    # QC
    ys = np.nonzero(daire.any(1))[0]
    iz0 = wk.plate_iz(P0, daire, {'daire': (int(ys[0]), int(ys[-1]) + 1)}, kontrol_kayma=120)
    iz1 = wk.plate_iz(P1, daire, {'daire': (int(ys[0]), int(ys[-1]) + 1)}, kontrol_kayma=120)
    O = oku(a.orijinal or K / 'orijinal_WP_11x14.jpg')
    # yalniz halka cikarmanin yarattigi cizgi sayilir: temiz zeminin kendisinde ayni olcumle gorunen kosu (3 Eki
    # 16x20: x=484 kenar dokusu, plate_temizle'de ham plate referansiyla gorunmuyor) haric
    once = kusur_bul(P0, O, P0, Z)
    kalan = [c for c in kusur_bul(P1, O, P0, Z) if not wb.ayni_cizgi(c, once)]
    _, ink = murekkep(O, P0)
    haric = cv2.dilate((ink | daire).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    de = wk.dE(P1, O)[~haric]
    qc = {'halka_kalintisi': {'once': iz0, 'sonra': iz1, 'gecti': bool(iz1['gecti'])},
          'cizgi': {'kalan': kalan, 'gecti': len(kalan) == 0},
          'kagit': {'dE_ort': round(float(de.mean()), 3), 'dE_p95': round(float(np.percentile(de, 95)), 3),
                    'esik_ort': 0.5, 'gecti': bool(de.mean() <= 0.5)}}
    qc['gecti'] = all(v['gecti'] for v in qc.values())
    R = {'kaynak_zemin': {'dosya': Z['zemin']['dosya'], 'sha256': Z['zemin']['sha256']},
         'halkasiz_zemin': {'dosya': str(zf.relative_to(kok)), 'sha256': sha(zf)},
         'halka': {'dosya': str(hf.relative_to(kok)), 'sha256': sha(hf), 'daire_px': int(daire.sum()),
                   'Lk_ci': round(Lk, 2), 'y': [int(ys[0]), int(ys[-1])],
                   'kaynak': f'TEMP/SIPARIS_ISIM/PLATES/MODERN_{a.boy}.png (kilitli wp_bakir.daire_maskesi)'},
         'degisen_px': int((np.abs(P1 - P0).max(2) > 0).sum()), 'qc': qc}
    (zf.with_suffix('.json')).write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps({k: R[k] for k in ('halkasiz_zemin', 'halka', 'degisen_px')}, ensure_ascii=False))
    print('QC', json.dumps(qc, ensure_ascii=False)[:1500])
    if not qc['gecti']:
        sys.exit(1)
    Z['zemin'] = {'dosya': R['halkasiz_zemin']['dosya'], 'sha256': R['halkasiz_zemin']['sha256'], 'halkasiz': True,
                  'kaynak': R['kaynak_zemin'], 'kayit': str(zf.with_suffix('.json').relative_to(kok)),
                  'onceki': Z['zemin']}
    Z['halka'] = R['halka']
    Path(a.sabit).write_text(json.dumps(Z, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
