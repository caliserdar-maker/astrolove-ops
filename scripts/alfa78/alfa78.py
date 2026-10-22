#!/usr/bin/env python3
"""78 SEMBOL ALFASI (Serdar 22 Eki, API YOK, yalniz dosya islemi).
Kaynak: Drive ANA_SEMBOL78_KATMAN_20261008/<CIFT>_ana.png. Her dosyadan yalniz alfa kanali; alfa > 0 sinir kutusuna
kirpilir; uzun kenar 3400 px'ten buyukse en / boy korunarak LANCZOS ile 3400'e kucultulur (buyutme yok); 8 bit gri PNG
<CIFT>_alfa3400.png. Kaynak md5 KATMAN_md5.txt ile karsilastirilir. Cikti: LISTE.csv + OZET.json.
Kullanim: alfa78.py KAYNAK_DIZIN MD5_DIZIN CIKTI_DIZIN
"""
import csv, hashlib, json, sys, time
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
UZUN = 3400
K, MD, C = (Path(a) for a in sys.argv[1:4])
C.mkdir(parents=True, exist_ok=True)

# md5 listesi: Drive'daki tum KATMAN_md5.txt kopyalari okunur, birbirleriyle tutarli olmali
kop = sorted(MD.glob('*.txt'))
tablolar = []
for f in kop:
    t = {}
    for sat in f.read_text().splitlines():
        if sat.strip():
            h, ad = sat.split(None, 1); t[ad.strip()] = h
    tablolar.append(t)
ref = tablolar[0]
kopya_tutarli = all(t == ref for t in tablolar)

dosyalar = sorted(K.glob('*_ana.png'))
satir, uymayan, hata = [], [], []
T0 = time.time()
for i, f in enumerate(dosyalar, 1):
    cift = f.name[:-len('_ana.png')]
    md5 = hashlib.md5(f.read_bytes()).hexdigest()
    beklenen = ref.get(f.name)
    uyum = 'EVET' if beklenen == md5 else ('LISTEDE_YOK' if beklenen is None else 'HAYIR')
    if uyum != 'EVET':
        uymayan.append(dict(cift=cift, kaynak_md5=md5, liste_md5=beklenen, durum=uyum))
    im = Image.open(f)
    kaynak_boyut = f'{im.width}x{im.height}'
    if 'A' not in im.getbands():
        im = im.convert('RGBA')                                   # P / LA saydamligi -> RGBA
    if 'A' not in im.getbands():
        hata.append(dict(cift=cift, hata='alfa yok')); continue
    a = im.getchannel('A')
    kutu = a.getbbox()                                            # alfa > 0 sinir kutusu
    if kutu is None:
        hata.append(dict(cift=cift, hata='alfa bos')); continue
    a = a.crop(kutu)
    w, h = a.size
    if max(w, h) > UZUN:
        s = UZUN / max(w, h)
        yeni = (UZUN, max(1, round(h * s))) if w >= h else (max(1, round(w * s)), UZUN)
        a = a.resize(yeni, Image.LANCZOS)
    a.save(C / f'{cift}_alfa3400.png', optimize=True)
    satir.append(dict(cift=cift, kaynak_md5=md5, md5_uyum=uyum, kaynak_boyut=kaynak_boyut,
                      kirpik_boyut=f'{w}x{h}', yeni_boyut=f'{a.width}x{a.height}'))
    gec = time.time() - T0
    print(f'[{i}/{len(dosyalar)}] {cift} {kaynak_boyut} -> {a.width}x{a.height} md5 {uyum} | gecen {gec:.0f} sn | '
          f'kalan ~{gec / i * (len(dosyalar) - i):.0f} sn | %{100 * i / len(dosyalar):.0f}', flush=True)

with open(C / 'LISTE.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['cift', 'kaynak_md5', 'md5_uyum', 'kaynak_boyut', 'kirpik_boyut', 'yeni_boyut'])
    w.writeheader(); w.writerows(satir)
ozet = dict(kaynak_dosya=len(dosyalar), cikti=len(satir), md5_kopya_sayisi=len(kop), md5_kopyalar_tutarli=kopya_tutarli,
            md5_uymayan=uymayan, hata=hata, sonuc='PASS' if len(satir) == 78 and not uymayan and not hata else 'FAIL')
(C.parent / 'OZET.json').write_text(json.dumps(ozet, indent=1, ensure_ascii=False))
print(json.dumps(ozet, ensure_ascii=False))
sys.exit(0 if ozet['sonuc'] == 'PASS' else 1)
