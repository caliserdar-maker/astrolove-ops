#!/usr/bin/env python3
"""CL kart 02 (Choose your format) kapak duvari zeminli yeniden kurulum (Serdar 28 Eyl).
Zemin: duvar_zemin.duvar(kapak_sahne_v9.png). Krem renk anahtariyla silinmez; kart yeniden kurulur:
  - nesneler (dijital yigin, baski, cerceve): onayli 02'den, kart02_poster_esitle.py geometrisiyle (ayni sabitler).
    Nesne pikseli yeni = eski + (1 - m) * (yeni zemin - eski zemin); m = nesne maskesi (tam ic: eski piksel aynen,
    yumusak kenar: krem payi duvarla degisir -> hale kalmaz). Golge ayni model (dx 15, dy 18, sigma 26, 59/232).
  - yazilar duvarin ustune dogrudan basilir: font/punto/konum/renk onayli 02'den olculdu (krem uzerinde alfa farki
    Lato 0.003-0.03, EB Garamond 0.02-0.06). Kontrast < 4.5 ise renk ayni tonda koyulastirilir.
  - ayirici cizgi: y 2100-2101, x 140-2860, (205,191,169), olculdu.
  - Serdar 28 Eyl duzeltmeleri: 'print ready' -> 'print-ready' (satir eski merkezinde kalir); hediye satiri aciklama
    alti (1610) ile ayirici cizgi (2100) arasina ortalanir (taban 1955 -> 1865).
Cikti: CIKIS.jpg + CIKIS.json (yazi satirlari, poster kutulari; duvar_qc.py icin).
Kullanim: kart02_duvar_kur.py ESKI_02.jpg KAPAK_SAHNE_V9.png FONT_KLASORU CIKIS.jpg
"""
import json
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import KREM, duvar, duvar_lum, kontrast, lum, yazi_rengi

ESKI, SAHNE, FD, CIK = sys.argv[1:5]
K = Image.open(ESKI).convert('RGB')
D = duvar(SAHNE)

# --- kart02_poster_esitle.py geometrisi (ayni sabitler) ---
PW, PH, ALT, BANT = 586, 760, 1294, (430, 1408)
FC = round(PW * 20 / 599.6)
CW, CH = PW + 2 * FC, PH + 2 * FC
E_ON, e_kutu = (244, 520, 809, 1295), (172, 496, 809, 1295)
sx, sy = PW / (E_ON[2] - E_ON[0]), PH / (E_ON[3] - E_ON[1])
ew, eh = e_kutu[2] - e_kutu[0], e_kutu[3] - e_kutu[1]
maske_eski = Image.new('L', K.size, 0)
for k in range(5):
    x0, y0 = E_ON[0] - 18 * k, E_ON[1] - 6 * k
    maske_eski.paste(255, (x0, y0, x0 + 565, y0 + 775))
yw, yh = round(ew * sx), round(eh * sy)
yigin_m = maske_eski.crop(e_kutu).resize((yw, yh), Image.LANCZOS)
on_x, on_y = round((E_ON[0] - e_kutu[0]) * sx), yh - PH
yigin_m.paste(255, (on_x, on_y, on_x + PW, on_y + PH))
yer = {'dijital': (yigin_m, (round(490 - yw / 2), ALT - yh)),
       'baski': (Image.new('L', (PW, PH), 255), (1500 - PW // 2, ALT - PH)),
       'cerceve': (Image.new('L', (CW, CH), 255), (round(2512 - CW / 2), ALT - CH))}
M = Image.new('L', K.size, 0); sil = Image.new('L', K.size, 0)
for m, (x, y) in yer.values():
    M.paste(m, (x, y), m); sil.paste(m, (x + 15, y + 18), m)
m = np.asarray(M).astype(np.float32)[..., None] / 255
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
golge = np.ones(alfa.shape, np.float32); golge[BANT[0]:BANT[1]] = 1 - (59 / 232) * alfa[BANT[0]:BANT[1]]
zemin_eski = np.array(KREM, np.float32)[None, None, :] * golge[..., None]
zemin_yeni = np.asarray(D).astype(np.float32) * golge[..., None]
A = np.asarray(K).astype(np.float32)
o = np.where(m > 0, A + (1 - m) * (zemin_yeni - zemin_eski), zemin_yeni)
out = Image.fromarray(np.clip(np.rint(o), 0, 255).astype(np.uint8))
d = ImageDraw.Draw(out)
d.rectangle((140, 2100, 2860, 2101), fill=(205, 191, 169))

# --- yazilar (olculdu: metin, font, wght, punto, x, taban y, onayli renk) ---
YAZI = [
    ('ASTROLOVE / CANCER + LIBRA', 'Lato-Regular.ttf', None, 40, 140, 130, (174, 143, 83)),
    ('Choose your format.', 'EBGaramond[wght].ttf', 430, 102, 140, 246, (22, 38, 65)),
    ('One design, three ways to enjoy it.', 'Lato-Regular.ttf', None, 52, 145, 367, (37, 45, 57)),
    ('Digital File', 'EBGaramond[wght].ttf', 400, 64, 355, 1456, (22, 38, 65)),
    ('Print', 'EBGaramond[wght].ttf', 400, 64, 1437, 1456, (22, 38, 65)),
    ('Framed', 'EBGaramond[wght].ttf', 400, 64, 2416, 1456, (22, 38, 65)),
    ('All 5 colors as print-ready PDFs. 300 dpi. Sent', 'Lato-Regular.ttf', None, 38, 110, 1558, (37, 44, 57)),
    ('Hahnemühle Photo Rag fine art paper.', 'Lato-Regular.ttf', None, 38, 1182, 1558, (37, 44, 56)),
    ('Classic wood frame in Antique Gold, Black,', 'Lato-Regular.ttf', None, 38, 2155, 1558, (37, 45, 57)),
    ('within 24 hours via Etsy Messages.', 'Lato-Regular.ttf', None, 38, 200, 1603, (37, 45, 56)),
    ('Unframed, ready for your frame.', 'Lato-Regular.ttf', None, 38, 1233, 1603, (37, 45, 57)),
    ('White or Natural. Arrives ready to hang.', 'Lato-Regular.ttf', None, 38, 2179, 1603, (37, 44, 56)),
    ('A personal gift for Cancer and Libra couples.', 'EBGaramond[wght].ttf', 430, 43, 1128, 1865, (23, 39, 66)),
    ('PERSONALIZED ZODIAC COUPLE WALL ART', 'Lato-Regular.ttf', None, 30, 140, 2172, (174, 143, 83)),
]
# metni degisen satir onayli metnin merkezinde kalir (onayli metin -> olculen x)
ESKI_METIN = {'All 5 colors as print-ready PDFs. 300 dpi. Sent': 'All 5 colors as print ready PDFs. 300 dpi. Sent'}
satirlar = []
for t, fy, w, s, x, y, renk in YAZI:
    f = ImageFont.truetype(os.path.join(FD, fy), s)
    if w:
        f.set_variation_by_axes([w])
    b = f.getbbox(t, anchor='ls')
    if t in ESKI_METIN:
        e = f.getbbox(ESKI_METIN[t], anchor='ls'); x = round(x + (e[0] + e[2]) / 2 - (b[0] + b[2]) / 2)
    kutu = (x + b[0], y + b[1], x + b[2], y + b[3])
    lw = duvar_lum(D, kutu)
    r = yazi_rengi(renk, lw)
    d.text((x, y), t, font=f, fill=r, anchor='ls')
    satirlar.append(dict(metin=t, kutu=kutu, renk=r, onayli_renk=list(renk),
                         kontrast=round(kontrast(float(lum(np.array(r))), lw), 2)))
out.save(CIK, quality=95, subsampling=0)
bx, by = yer['baski'][1]; dx, dy = yer['dijital'][1]; cx, cy = yer['cerceve'][1]
poster = [(bx, by, PW, PH), (dx + on_x, dy + on_y, PW, PH), (cx + FC, cy + FC, PW, PH)]
json.dump(dict(satirlar=satirlar, poster=poster), open(os.path.splitext(CIK)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
for s_ in satirlar:
    print(f"{s_['metin'][:34]:34s} renk {tuple(s_['onayli_renk'])} -> {tuple(s_['renk'])} kontrast {s_['kontrast']}")
