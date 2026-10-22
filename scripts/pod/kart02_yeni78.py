#!/usr/bin/env python3
"""Kart 02 yeni Digital File metni, 78 cift (Serdar 9 Eki, 3 satir onayli). Etsy YOK.
Cift basina: krem 02 (CL: data/pod/cl_galeri_krem_kaynak/02_format.jpg; 77 cift: galeri77_kur.kart02 ile CL krem 02 +
ciftin sanal kapak posteri, galeri77_kur ile birebir) -> kart02_duvar_kur.py iki kez:
  ESKI_DIJITAL=1 : 30 Eyl metni; ONAYLI 02 ile PIKSEL AYNI olmali (CL: data/pod/cl_galeri_final19/02_format.jpg;
                   77 cift: Drive GALERI_77/<CIFT>/02_format.jpg). Farkliysa o cift FAIL (yeni dosya yazilmaz).
  yeni           : kart02_dijital_metin.YENI; ayni kart, yalniz Digital File satirlari farkli olmali (fark kutusu metin bandinda).
OCR (tesseract): yeni kartin Digital File bandi -> TAM_METIN ile birebir (bosluk normalize), uzun/orta tire yok.
Kullanim: kart02_yeni78.py HAZIR.csv KAYNAK_KOK(_KAYNAK) ONAYLI_KOK(GALERI_77) DUVAR.png FONT_DIR OUT_DIR
Cikti: OUT/<CIFT>/02_format.jpg + OUT/TABLO.csv (cift, listing_id, eski_ayni, max_fark, fark_kutusu, ocr, PASS)."""
import csv, os, re, subprocess, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
import galeri77_kur as GK
import kart02_dijital_metin as KD
HAZIR, KAY, ONK, DUVAR, FD, OUT = sys.argv[1:7]
CL = '4570143815'
ids = {r['cift']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data/pod/pod78_ids.csv')))}
liste = [('CANCER_LIBRA', CL)] + [(r['cift'].strip(), r['listing_id'].strip()) for r in csv.DictReader(open(HAZIR, encoding='utf-8'))
                                 if (r.get('listing_id') or '').strip() and r['listing_id'].strip() != CL]
cl_mb = Image.open(os.path.join(KAY, 'CANCER_LIBRA', 'BASKI_MIDNIGHT_BLUE.jpg')).convert('RGB')
BANT = (60, 1500, 940, 1700)          # Digital File aciklama bandi (eski 2 satir, yeni 3 satir; 'Digital File' basligi 1456 ustte)
def kur(krem, ad_a, ad_b, cik, eski):
    env = dict(os.environ); env.pop('ESKI_DIJITAL', None)
    if eski: env['ESKI_DIJITAL'] = '1'
    subprocess.run([sys.executable, os.path.join(HERE, 'kart02_duvar_kur.py'), krem, DUVAR, FD, cik, ad_a, ad_b], env=env, check=True,
                   capture_output=True)
def norm(t): return re.sub(r'\s+', ' ', t).strip()
tab = []; t0 = time.time(); os.makedirs(OUT, exist_ok=True)
for i, (c, lid) in enumerate(liste, 1):
    o = os.path.join(OUT, c); os.makedirs(o, exist_ok=True); w = os.path.join(o, '_is'); os.makedirs(w, exist_ok=True)
    a, b = ids[c]['a'], ids[c]['b']
    if c == 'CANCER_LIBRA':
        krem = os.path.join(ROOT, 'data/pod/cl_galeri_krem_kaynak/02_format.jpg'); onayli = os.path.join(ROOT, 'data/pod/cl_galeri_final19/02_format.jpg')
    else:
        mb = Image.open(os.path.join(KAY, c, 'BASKI_MIDNIGHT_BLUE.jpg')).convert('RGB')
        V, n_v = GK.sanal_kapak(mb, cl_mb)
        im = Image.open(os.path.join(GK.KREM_CL, '02_format.jpg')).convert('RGB'); GK.kart02(im, V)
        krem = os.path.join(w, 'krem02.jpg'); im.save(krem, quality=95, subsampling=0)
        onayli = os.path.join(ONK, c, '02_format.jpg')
    kur(krem, a, b, os.path.join(w, 'eski.jpg'), True)
    E = np.asarray(Image.open(os.path.join(w, 'eski.jpg')).convert('RGB')).astype(int)
    Oy = np.asarray(Image.open(onayli).convert('RGB')).astype(int)
    eski_fark = int(np.abs(E - Oy).max()) if E.shape == Oy.shape else 999
    satir = dict(cift=c, listing_id=lid, eski_max_fark=eski_fark, eski_ayni=eski_fark == 0)
    if eski_fark == 0:
        yeni = os.path.join(o, '02_format.jpg'); kur(krem, a, b, yeni, False)
        Y = np.asarray(Image.open(yeni).convert('RGB')).astype(int)
        d = np.abs(Y - Oy).max(2); ys, xs = np.nonzero(d > 0)
        kutu = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
        # JPEG 8x8 bloklari: fark metin bandinin 16 px payi icinde kalmali
        bant_ok = kutu is not None and kutu[0] >= BANT[0] - 16 and kutu[1] >= BANT[1] - 16 and kutu[2] <= BANT[2] + 16 and kutu[3] <= BANT[3] + 16
        Image.open(yeni).crop(BANT).resize(((BANT[2] - BANT[0]) * 2, (BANT[3] - BANT[1]) * 2), Image.LANCZOS).save(os.path.join(w, 'ocr.png'))
        ocr = norm(subprocess.run(['tesseract', os.path.join(w, 'ocr.png'), '-', '--psm', '6'], capture_output=True, text=True).stdout)
        tire = any(ch in ocr for ch in '—–')
        satir.update(fark_kutusu=kutu, bant_ok=bant_ok, ocr=ocr, ocr_ayni=ocr == KD.TAM_METIN, tire_yok=not tire)
        satir['PASS'] = bool(bant_ok and satir['ocr_ayni'] and not tire)
    else:
        satir.update(fark_kutusu=None, bant_ok=False, ocr='', ocr_ayni=False, tire_yok=True, PASS=False)
    tab.append(satir); g = time.time() - t0
    print(f"[{i}/{len(liste)}] {c} eski_ayni={satir['eski_ayni']} ocr_ayni={satir['ocr_ayni']} PASS={satir['PASS']} | gecen {g/60:.1f} dk | "
          f"kalan ~{g/i*(len(liste)-i)/60:.1f} dk | %{100*i//len(liste)}", flush=True)
with open(os.path.join(OUT, 'TABLO.csv'), 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=list(tab[0].keys())); wr.writeheader(); wr.writerows(tab)
n = sum(1 for x in tab if x['PASS']); print(f'OZET {n}/{len(tab)} PASS', flush=True)
sys.exit(0 if n == len(tab) else 1)
