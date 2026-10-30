#!/usr/bin/env python3
"""Wall art galeri: Champagne Ivory renk karti (diger renk kartlari W07 MB, W08 DB, W09 PW, W10 WP ile ayni tarz; Serdar 30 Eki).
Yontem: ayni oda sahnesi. Ust bolum (y < 450) o ciftin W07_MB kartindan alinir; renk adi satiri (y 150-330) temiz duvar bandiyla
(ci_duvar_bant_150_330.png, MB/DB/PW/W01 kartlarindan uretildi) degistirilip "Champagne Ivory" yazilir (Liberation Sans Bold 104,
renk 9,22,56; ust hizasi MB'deki "Midnight Blue" ile ayni y 188, yatay orta 1501). Alt bolum (y >= 450) o ciftin W01 CI kapagindan
(CI poster, siyah cerceve, paspartusuz; PW karti ile ayni duzen). Iki kaynak y 120-520 disinda ve 450-520 araliginda birebir ayni duvar.
Kapilar: boyut 3000x2250; MB ve W01'in y 450-520 bandi ayni (ort fark <= 2); MB renk satiri bandi CANCER_LIBRA referansiyla ayni
(ort fark <= 3, yani ayni "Midnight Blue" ve ayni duvar). Biri FAIL ise dosya yazilmaz.
Kullanim: python3 -I ci_renk_karti.py <W07_MB.jpg> <W01_KAPAK.jpg> <cikti.jpg>"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

MB, W01, OUT = sys.argv[1:4]
BURASI = os.path.dirname(os.path.abspath(__file__))
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
BANT = np.asarray(Image.open(os.path.join(BURASI, 'ci_duvar_bant_150_330.png')).convert('RGB'))
REF_MB_BANT = os.path.join(BURASI, 'ref_mb_bant_150_330.png')
Y0, Y1, KES = 150, 330, 450
mb = np.asarray(Image.open(MB).convert('RGB'))
w1 = np.asarray(Image.open(W01).convert('RGB'))
assert mb.shape == w1.shape == (2250, 3000, 3), 'boyut'
f_bag = np.abs(mb[KES:520].astype(int) - w1[KES:520].astype(int)).mean()
assert f_bag <= 2, f'MB ve W01 birlesim bandi farkli: {f_bag:.2f}'
if os.path.exists(REF_MB_BANT):
    ref = np.asarray(Image.open(REF_MB_BANT).convert('RGB')).astype(int)
    f_ref = np.abs(mb[Y0:Y1].astype(int) - ref).mean()
    assert f_ref <= 3, f'MB renk satiri referanstan farkli: {f_ref:.2f}'
out = np.concatenate([mb[:KES], w1[KES:]], 0).copy()
out[Y0:Y1] = BANT
im = Image.fromarray(out)
d = ImageDraw.Draw(im)
ft = ImageFont.truetype(FONT, 104)
ust = ft.getbbox('Champagne Ivory', anchor='ls')[1]
d.text((1501, 188 - ust), 'Champagne Ivory', font=ft, fill=(9, 22, 56), anchor='ms')
gecici = OUT + '.gecici.jpg'
im.save(gecici, quality=95)
os.replace(gecici, OUT)
print('tamam', OUT, f'bag farki {f_bag:.2f}')
