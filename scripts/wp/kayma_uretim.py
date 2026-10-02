#!/usr/bin/env python3
"""WP kayma tanisi, URETIM fonksiyonlariyla (ders 33: test araci uretimin kendi fonksiyonunu cagirir).

surucu.wp_asamasi (siparis-dijital wp isinin AYNISI) iki kez kosar:
  once  : degistirilmemis uretim (e_kagit = wp_bakir.qc, plate = wp_ornek zemin_uyumu + temizlik)
  sonra : tek fark VINTAGE_<boy> plate dizisi, wk.boyutla sonrasi --dx/--dy kadar kaydirilir (kayma_tani olcumu)
Kapi esikleri ve kod degismez. Cikti: <cikti>/once, <cikti>/sonra (OZET_WP_<boy>.json + WP_<boy>.jpg), KAYMA_URETIM_<boy>.json.
Kullanim (siparis-dijital wp isiyle ayni ortam): python kayma_uretim.py --kod _v1 --boy 11x14 --dx .. --dy .. --cikti out
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parents[1] / 'siparis_dijital'
sys.path.insert(0, str(KOK))
import surucu  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kod', required=True); ap.add_argument('--kod-ref', default='')
    ap.add_argument('--boy', required=True)
    ap.add_argument('--dx', type=float, required=True); ap.add_argument('--dy', type=float, required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    cikti = Path(a.cikti).resolve(); kod = str(Path(a.kod).resolve())
    g = surucu.girdi()
    os.chdir(kod)
    sonuc = {'boy': a.boy, 'kayma': {'dx': a.dx, 'dy': a.dy}}
    for tur in ('once', 'sonra'):
        ns = argparse.Namespace(asama='wp', kod=kod, kod_ref=a.kod_ref, boy=a.boy, cikti=str(cikti / tur),
                                renk=None, oran=None)
        if tur == 'sonra':
            import cv2
            import wp_ornek as wo
            wk = wo.wk
            ad_hedef = f'VINTAGE_{a.boy}.png'
            asil_indir, asil_dizi, asil_boyutla = wo.plate_indir, wk.dizi, wk.boyutla
            isaret = {'yol': None, 'dizi': None}

            def plate_indir(ad):
                y = asil_indir(ad)
                if ad == ad_hedef:
                    isaret['yol'] = str(y)
                return y

            def dizi(x):
                d = asil_dizi(x)
                if isaret['yol'] is not None and not isinstance(x, np.ndarray) and str(x) == isaret['yol']:
                    isaret['dizi'] = d
                return d

            def boyutla(arr, wh):
                b = asil_boyutla(arr, wh)
                if isaret['dizi'] is not None and arr is isaret['dizi']:
                    M = np.float32([[1, 0, a.dx], [0, 1, a.dy]])
                    b = cv2.warpAffine(b, M, (b.shape[1], b.shape[0]), flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_REFLECT)
                    isaret['dizi'] = None
                    sonuc['kaydirildi'] = True
                    print('KAYMA_UYGULANDI', a.boy, a.dx, a.dy, flush=True)
                return b
            wo.plate_indir, wk.dizi, wk.boyutla = plate_indir, dizi, boyutla
        rc = surucu.wp_asamasi(ns, g)
        oz = json.loads((cikti / tur / f'OZET_WP_{a.boy}.json').read_text())
        sonuc[tur] = {'rc': rc, 'kapilar_gecti': oz.get('kapilar_gecti'), 'kapi_sayilari': oz.get('kapi_sayilari'),
                      'kapilar': oz.get('kapilar')}
        print('KAYMA_URETIM', tur, a.boy, json.dumps(sonuc[tur]['kapi_sayilari'], default=str), flush=True)
    (cikti / f'KAYMA_URETIM_{a.boy}.json').write_text(json.dumps(sonuc, indent=1, default=str))
    if not sonuc.get('kaydirildi'):
        print('HATA: plate kaydirma uygulanmadi', flush=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
