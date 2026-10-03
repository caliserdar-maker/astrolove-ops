#!/usr/bin/env python3
"""Temiz ana zemin (Serdar 3 Eki karari): PLATES/<plate>.png BIR KEZ onarilir, motor/varlik/plates/<plate>_temiz.png
olarak sha + onarim kaydiyla saklanir. Motor her zaman bu dosyayi kullanir; render sirasinda zemin rotusu YOK.

Kusur: plate'te olup orijinal satis posterinde olmayan ince uzun duz cizgi (kilitli wp_bakir.dikis, oge bantlari
+-150 px, tasarim alani; orijinalde yazi altinda kalan plate dikisi dahil). Iki maske: maskesiz + orijinal yazi
maskesi (yazi yaninda belirecek kisa izler). Onarim: kilitli wp_bakir.serit_onar (plate'in kendi
komsu sutunlari; orijinalden piksel alinmaz).
QC (PASS/FAIL): temiz zeminde orijinalde olmayan cizgi = 0; yazi disi kagitta dE(temiz, orijinal) ort <= 0.5;
kilitli wp_katman.plate_iz (eski yazi izi, oran <= 1.25).
Bilgi: ayni olcum diger 11x14 VINTAGE plate'lerinde (yalniz liste, duzeltme yok).

Kullanim: plate_temizle.py --kaynak DIR --sabit motor/sabitler/X.json --plate VINTAGE_B3_11x14 --cikti motor/varlik/plates
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
from qc import hat_bul, hat_maskesi                                   # noqa: E402

Image.MAX_IMAGE_PIXELS = None
YARI = 4            # serit yari genisligi (wp_bakir.dikis_onar varsayilani)


def oku(f):
    return np.asarray(Image.open(f).convert('RGB'), np.float32)


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def onar(P, cizgiler):
    H, W = P.shape[:2]
    kayit = []
    for c in cizgiler:
        if c['yon'] == 'dikey':
            P, r = wb.serit_onar(P, c['x'] - YARI, c['x'] + YARI + 1, max(0, c['y'][0] - 10), min(H, c['y'][1] + 11))
        else:
            Pt, r = wb.serit_onar(P.transpose(1, 0, 2), c['y'] - YARI, c['y'] + YARI + 1, max(0, c['x'][0] - 10),
                                  min(W, c['x'][1] + 11))
            P = np.ascontiguousarray(Pt.transpose(1, 0, 2))
        kayit.append({'cizgi': c, 'onarim': r})
    return P, kayit


def kagit_dE(P, O, P_ref):
    _, ink = murekkep(O, P_ref)
    yazi = cv2.dilate(ink.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    de = wk.dE(P, O)[~yazi]
    return {'dE_ort': round(float(de.mean()), 3), 'dE_p95': round(float(np.percentile(de, 95)), 3)}


def kusur_bul(Px, O, P_ref, Z):
    """Iki maske ile (birlesim): (1) maskesiz: zeminin kendisinde >= 100 px cizgi; (2) orijinalin yazi maskesi ile:
    yazinin yaninda kopruyle belirecek kisa iz (dedektor yazi cevresini notr sayar; yeni yazi baska yere duser)."""
    bos = np.zeros(Px.shape[:2], bool)
    _, k1 = hat_bul(Px, O, P_ref, Z, mask_x=bos)
    _, k2 = hat_bul(Px, O, P_ref, Z, mask_x=hat_maskesi(P_ref, O))
    return k1 + [c for c in k2 if not wb.ayni_cizgi(c, k1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K, C = Path(a.kaynak), Path(a.cikti)
    C.mkdir(parents=True, exist_ok=True)
    Z = json.loads(Path(a.sabit).read_text())
    O = oku(K / 'orijinal_WP_11x14.jpg')
    kf = K / 'plates' / f'{a.plate}.png'
    P0 = oku(kf)
    kusur = kusur_bul(P0, O, P0, Z)
    P1, kayit = onar(P0.copy(), kusur)
    u8 = np.clip(np.round(P1), 0, 255).astype(np.uint8)
    hedef = C / f'{a.plate}_temiz.png'
    Image.fromarray(u8).save(hedef, optimize=False)
    P1 = oku(hedef)
    kalan = kusur_bul(P1, O, P0, Z)
    de0, de1 = kagit_dE(P0, O, P0), kagit_dE(P1, O, P0)
    degisen = np.abs(P1 - P0).max(2) > 0
    _, G = murekkep(O, P0)                                             # orijinal glifleri (eski yazi izi olcumu)
    bnt = {k: Z['bantlar'][k] for k in ('kucuk_sembol', 'isim', 'mesaj')}
    iz = wk.plate_iz(P1, G, bnt, kontrol_kayma=400)                     # kilitli iz kapisi (esik 1.25)
    qc = {'kalan_cizgi': kalan, 'kagit': de1, 'esik_dE_ort': 0.5, 'iz': iz,
          'gecti': len(kalan) == 0 and de1['dE_ort'] <= 0.5 and bool(iz['gecti'])}
    # bilgi: ayni olcum diger 11x14 VINTAGE plate'lerinde (orijinal SCORPIO_VIRGO; baska ciftin yazi altinda kalan
    # kusurlari bu olcumle gorulemez, yalniz gosterge)
    diger = {}
    for f in sorted((K / 'plates').glob('VINTAGE*_11x14.png')):
        if f.stem == a.plate:
            continue
        Px = oku(f)
        kx = kusur_bul(Px, O, Px, Z)
        diger[f.stem] = [(c['yon'], c.get('x'), c.get('y')) for c in kx]
    R = {'kaynak': {'dosya': f'TEMP/SIPARIS_ISIM/PLATES/{a.plate}.png', 'sha256': sha(kf)},
         'temiz': {'dosya': str(hedef), 'sha256': sha(hedef)},
         'kusur': kusur, 'onarim': kayit, 'degisen_px': int(degisen.sum()),
         'kagit_once': de0, 'qc': qc, 'diger_plateler_gosterge': diger}
    (C / f'{a.plate}_temiz.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    if qc['gecti']:                                                    # motor yalniz QC'den gecmis zemini kullanir
        Z['zemin'] = {'dosya': str(hedef), 'sha256': R['temiz']['sha256'], 'kaynak': R['kaynak'],
                      'kayit': str(C / f'{a.plate}_temiz.json')}
        Path(a.sabit).write_text(json.dumps(Z, indent=1, ensure_ascii=False))
    print(json.dumps({k: R[k] for k in ('kaynak', 'temiz', 'degisen_px', 'kagit_once', 'qc')}, ensure_ascii=False))
    print('kusur', [(c['yon'], c.get('x'), c.get('y')) for c in kusur])
    print('diger', json.dumps(diger))
    sys.exit(0 if qc['gecti'] else 1)


if __name__ == '__main__':
    main()
