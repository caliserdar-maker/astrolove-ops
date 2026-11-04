#!/usr/bin/env python3
"""Siparis 8x10 baski dosyasi -> cercevesiz onizleme + isim/mesaj bolgesi 1:1 kesit + OCR kontrolu (yalniz PASS/FAIL basar).
Deger (isim/mesaj) loga ve OZET'e YAZILMAZ. Kullanim: onizle_8x10.py BASKI.jpg KISISEL.json CIKTI_DIR AD_KOK"""
import json, sys, subprocess, difflib, re
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

baski, kis, out, kok = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
out.mkdir(parents=True, exist_ok=True)
v = {x['ad']: x['deger'] for x in json.load(open(kis))['kalemler'][0]['varyasyon']}
i1, i2, m = v['Name under Cancer'], v['Name under Libra'], v['Your message']
im = Image.open(baski); dpi = im.info.get('dpi'); W, H = im.size; im = im.convert('RGB')
oz = dict(boyut=[W, H], dpi=[round(float(d)) for d in dpi] if dpi else None, olcu_ok=(W, H) == (2400, 3000),
          dpi_ok=bool(dpi) and all(round(float(d)) == 300 for d in dpi))
# 1:1 kesit: alt %45 (isimler, sonsuz, kucuk isaretler, mesaj); piksel olcegi 1:1
y0 = int(H * 0.55)
kes = im.crop((0, y0, W, H))
kes.save(out / f'{kok}_KESIT_1x1.jpg', quality=95, dpi=(300, 300), subsampling=0)
oz['kesit'] = dict(kutu=[0, y0, W, H], olcek='1:1')
# cercevesiz baski onizleme (gercek oran 8:10) acik duvar zemininde, hafif golge
dw, dh = 1800, 2200; pw, ph = 1040, 1300
zemin = Image.new('RGB', (dw, dh), (236, 233, 228))
x, y = (dw - pw) // 2, (dh - ph) // 2 - 40
g = Image.new('L', (dw, dh), 0); g.paste(150, (x + 14, y + 22, x + pw + 14, y + ph + 22)); g = g.filter(ImageFilter.GaussianBlur(22))
zemin = Image.composite(Image.new('RGB', (dw, dh), (150, 146, 140)), zemin, g)
zemin.paste(im.resize((pw, ph), Image.LANCZOS), (x, y))
zemin.save(out / f'{kok}_ONIZLEME.jpg', quality=92)
# kontrol icin kucuk (yalniz gizli Drive KONTROL/)
k = ImageOps.grayscale(kes); k = k.resize((800, int(800 * k.height / k.width)), Image.LANCZOS)
(out / 'KONTROL').mkdir(exist_ok=True); k.save(out / 'KONTROL' / 'KESIT_KUCUK.jpg', quality=60)
# OCR (tesseract varsa): metin degerleri basilmaz, yalniz sonuc
ocr = dict(calisti=False)
try:
    g2 = ImageOps.grayscale(kes).point(lambda p: 0 if p > 70 else 255)
    g2.save('/tmp/ocr_in.png')
    t = subprocess.run(['tesseract', '/tmp/ocr_in.png', '-', '--psm', '6'], capture_output=True, text=True, timeout=120).stdout
    Path('/tmp/ocr_in.png').unlink()
    satir = [re.sub(r'\s+', ' ', s).strip() for s in t.splitlines() if s.strip()]
    tok = set(re.findall(r'[A-Za-z]+', t))
    en_iyi = max((difflib.SequenceMatcher(None, s, m).ratio() for s in satir), default=0.0)
    ocr = dict(calisti=True, isim1_buyuk_harf_bulundu=i1.upper() in tok, isim2_buyuk_harf_bulundu=i2.upper() in tok,
               isim1_kucuk_harfli_gecti=i1 in tok and i1 != i1.upper(), isim2_kucuk_harfli_gecti=i2 in tok and i2 != i2.upper(),
               mesaj_tam_satir=any(s == m for s in satir), mesaj_benzerlik=round(en_iyi, 3), satir_sayisi=len(satir))
except FileNotFoundError:
    pass
oz['ocr'] = ocr
json.dump(oz, open(out / 'ONIZLE_OZET.json', 'w'), indent=1)
print('ONIZLE:', json.dumps(oz))
