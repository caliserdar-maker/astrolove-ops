#!/usr/bin/env python3
"""Temiz ana zemine TEK SEFERLIK ek onarim (3 Eki 2026). plate_temizle tam boyda olcer; buyuk boylarda QC (3307 px
olcegi, qc.py QC_W) tam boyda gorulmeyen bir kosu bulabilir (A2: x=2805, Test 5'te de var). Bu betik QC olceginde
verilen cizgiyi tam boy zeminde kilitli wp_bakir.serit_onar ile onarir (zeminin kendi komsu sutunlari; orijinalden
piksel alinmaz), zemini yerinde gunceller, sha + kaydi sabitlere yazar. Render sirasinda zemin rotusu YOK.
QC (PASS/FAIL): cizgi QC olceginde artik bulunmaz, yeni cizgi yok; yazi disi kagit dE(zemin, orijinal) ort <= 0.5.

Kullanim: zemin_ek_onar.py --kaynak DIR --sabit X.json --orijinal O.jpg --cizgi dikey:2805:4094:4218
"""
import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
sys.path.insert(0, str(KOK))
import wp_bakir as wb                                                 # noqa: E402
import qc                                                             # noqa: E402
from plate_temizle import YARI                              # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def cizgiler(Pq, Oq, Pref, Z):
    """QC olceginde, qc.hat_bul ile (bos maske + orijinal yazi maskesi; plate_temizle.kusur_bul ile ayni)."""
    bos = np.zeros(Pq.shape[:2], bool)
    _, k1 = qc.hat_bul(Pq, Oq, Pref, Z, mask_x=bos)
    _, k2 = qc.hat_bul(Pq, Oq, Pref, Z, mask_x=qc.hat_maskesi(Pref, Oq))
    return k1 + [c for c in k2 if not wb.ayni_cizgi(c, k1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--orijinal', required=True)
    ap.add_argument('--cizgi', action='append', required=True, help='yon:x:y0:y1 (dikey) / yon:y:x0:x1 (yatay), QC px')
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    zf = KOK.parent / Z['zemin']['dosya']
    if sha(zf) != Z['zemin']['sha256']:
        sys.exit('FAIL: zemin sha uyusmuyor')
    P = np.asarray(Image.open(zf).convert('RGB'), np.float32)
    H, W = P.shape[:2]
    P_once = P.copy()
    Pq0 = qc.oku_n(zf)
    f = Pq0.shape[1] / W
    Oq, Pref = qc.oku_n(a.orijinal), qc.oku_n(K / 'plates' / f"{Z['plate']}.png")
    Zq = json.loads(json.dumps(Z))
    Zq['bantlar'] = {k: [int(round(v[0] * f)), int(round(v[1] * f))] for k, v in Z['bantlar'].items()}
    once = cizgiler(Pq0, Oq, Pref, Zq)
    yari = int(np.ceil((YARI + 1) / f))
    kayit = []
    for c in a.cizgi:
        yon, k, u0, u1 = c.split(':')
        k, u0, u1 = int(k) / f, int(u0) / f, int(u1) / f
        if yon == 'dikey':
            x = int(round(k))
            P, r = wb.serit_onar(P, x - yari, x + yari + 1, max(0, int(u0) - 15), min(H, int(u1) + 16))
        else:
            y = int(round(k))
            Pt, r = wb.serit_onar(P.transpose(1, 0, 2), y - yari, y + yari + 1, max(0, int(u0) - 15), min(W, int(u1) + 16))
            P = np.ascontiguousarray(Pt.transpose(1, 0, 2))
        kayit.append({'cizgi_qc': c, 'tam_boy': {'yon': yon, 'merkez': round(k, 1), 'aralik': [round(u0), round(u1)],
                                                 'yari_genislik': yari}, 'onarim': r})
    eski_sha = Z['zemin']['sha256']
    gecici = zf.with_name(zf.stem + '_aday.png')
    Image.fromarray(np.clip(np.round(P), 0, 255).astype(np.uint8)).save(gecici)
    zf, zf_asil = gecici, zf
    Pq1 = qc.oku_n(zf)
    sonra = cizgiler(Pq1, Oq, Pref, Zq)
    hedef = [dict(zip(('yon', 'k', 'u0', 'u1'), c.split(':'))) for c in a.cizgi]
    kalan = [c for c in sonra if any(c['yon'] == h['yon'] and abs((c['x'] if c['yon'] == 'dikey' else c['y']) - int(h['k'])) <= 4
                                     for h in hedef)]
    yeni = [c for c in sonra if not wb.ayni_cizgi(c, once)]
    # kagit: orijinal yazisi ve halka cevresi disi (halkasiz zeminde halka yok, orijinalde var; halka.py QC ile ayni)
    import cv2
    _, ink = qc.murekkep(Oq, Pref)
    har = ink | (qc.halka_alfa(Z, Oq.shape) > 5) if 'halka' in Z else ink
    har = cv2.dilate(har.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    d0, d1 = qc.wk.dE(Pq0, Oq)[~har], qc.wk.dE(qc.oku_n(zf), Oq)[~har]
    de = {'dE_ort': round(float(d1.mean()), 3), 'dE_ort_once': round(float(d0.mean()), 3)}
    q = {'hedef_kalan': kalan, 'yeni_cizgi': yeni, 'kagit': de, 'esik_dE_ort': 0.5,
         'gecti': not kalan and not yeni and de['dE_ort'] <= 0.5}
    R = {'zemin': str(Z['zemin']['dosya']), 'once_sha256': eski_sha, 'sonra_sha256': sha(zf), 'qc_olcek': round(f, 5),
         'onarim': kayit, 'degisen_px': int((np.abs(P - P_once).max(2) > 0).sum()),
         'qc': q}
    kf = zf_asil.with_name(zf_asil.stem + '_ek_onarim.json')
    R['zemin'] = str(Z['zemin']['dosya'])
    kf.write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False)[:2000])
    if not q['gecti']:
        gecici.unlink()
        sys.exit(1)
    gecici.replace(zf_asil)
    Z['zemin'] = {**Z['zemin'], 'sha256': R['sonra_sha256'], 'ek_onarim': str(kf.relative_to(KOK.parent)),
                  'ek_onarim_oncesi_sha256': eski_sha}
    Path(a.sabit).write_text(json.dumps(Z, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
