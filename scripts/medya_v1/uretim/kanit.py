#!/usr/bin/env python3
"""E01-E06 %100 kanit kirpimlari (eski paket = baslangic ZIP'indeki production_run/completed/AQUARIUS_AQUARIUS)."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import master as M
FD = os.environ.get('FONT_DIR', '/home/user/astrolove-ops/work/fonts/')
F = ImageFont.truetype(FD + 'Montserrat[wght].ttf', 22)
R = M.ROOT; O = str(R / 'eski/images') + '/'; D = R / 'paket/REVIEW/HATA_KANIT'; D.mkdir(parents=True, exist_ok=True)
def lab(im, t):
    p = Image.new('RGB', (im.width, im.height + 40), 'white'); p.paste(im, (0, 40)); ImageDraw.Draw(p).text((5, 8), t, fill='black', font=F); return p
def row(ims):
    h = max(i.height for i in ims); w = sum(i.width for i in ims) + 20 * (len(ims) - 1); p = Image.new('RGB', (w, h), 'white'); x = 0
    for i in ims: p.paste(i, (x, 0)); x += i.width + 20
    return p
gb = (151 + 100, 171 + 615, 151 + 680, 171 + 740)
for c, f in [('MB', '01_Cover.png'), ('DB', '12_DEEP_BLACK.png'), ('CI', '13_CHAMPAGNE_IVORY.png'), ('PW', '14_PURE_WHITE.png'), ('WP', '15_WARM_PARCHMENT.png')]:
    row([lab(Image.open(O + f).convert('RGB').crop(gb), f'ESKI {f} %100'), lab(Image.open(R / f'out/cover_{c}.png').convert('RGB').crop(gb), f'YENI cover_{c} %100')]).save(D / f'E01_E02_E03_sembol_{c}_100.png')
cov = Image.open(O + '01_Cover.png').convert('RGB').crop((151 + 100, 171 + 600, 151 + 680, 171 + 780))
c6 = Image.open(O + '06_card06.jpg').convert('RGB').crop((180, 1600, 1200, 2100))
row([lab(cov, 'ESKI 01_Cover %100 (sembol+isim)'), lab(c6, 'ESKI 06 inset alt bolum %100')]).save(D / 'E04_eski_kapak_vs_kart06_100.png')
for f, box, t in [('05_Palette.jpg', (0, 0, 3000, 560), 'ESKI 05 ust yazi'), ('11_Delivery.jpg', (0, 0, 3000, 700), 'ESKI 11 ust yazi'), ('08_card08.jpg', (0, 0, 1600, 500), 'ESKI 08 ust etiket yamasi')]:
    lab(Image.open(O + f).convert('RGB').crop(box), t + ' %100').save(D / f'E05_{f[:2]}_100.png')
lab(Image.open(O + '07_card07.jpg').convert('RGB').crop((1500, 700, 2950, 1850)), 'ESKI 07 detay paneli %100').save(D / 'E06_eski_07_detay_100.png')
lab(Image.open(R / 'out/card07.png').convert('RGB').crop((1169, 569, 2821, 1854)), 'YENI 07 detay paneli %100').save(D / 'E06_yeni_07_detay_100.png')
L = json.load(open(R / 'out/cards_log_2_3_4_5_6_7_8_9_10.json'))
p = [q for q in L['5']['poster'] if q['color'] == 'CI'][0]; x0, y0, x1, y1 = p['rect']
o = Image.open(R / 'out/card05.png').convert('RGB').crop((x0, y0, x1, y1)); r = Image.open(R / 'etsy/REF_4570143815/05_8567954574.jpg').convert('RGB').crop((x0, y0, x1, y1))
row([lab(r.resize((r.width * 2, r.height * 2), Image.NEAREST), 'REF 05 CI %200'), lab(o.resize((o.width * 2, o.height * 2), Image.NEAREST), 'YENI 05 CI %200 (QC K3)')]).save(D / 'QC_K3_kart05_CI_200.png')
print('kanit ok')
