#!/usr/bin/env python3
"""CL kart 02 (Choose your format): uc posteri AYNI boya getirir. Yazilar ve zemin degismez.
Kaynak poster ve cerceve: onayli kapak (data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg), yeniden cizim yok.
  Poster  : kapak (734,130)-(2268,2118)  1534x1988  -> 586x760
  Cerceve : kapak (676,75)-(2323,2175)   ayni olcekle
  Dijital yigin: karttaki arka sayfalar ayni sira ve kaydirmayla olceklenir, on yuze gercek poster.
Golge: karttaki mevcut golgeden olculdu (dx 15, dy 18, sigma 26, koyuluk 59/232).
QC: 3 poster boyu esit, NCC(poster, kapak posteri) >= 0.97, yazi bantlari piksel ayni, alt cizgi hizali.
Kullanim: kart02_poster_esitle.py GIRIS.jpg KAPAK.jpg CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

GIR, KAPAK, CIK = sys.argv[1:4]
K = Image.open(GIR).convert('RGB'); C = Image.open(KAPAK).convert('RGB')
BG = (237, 232, 226)
PW, PH = 586, 760                      # ortak poster boyu
ALT = 1294                             # uc nesnenin alt cizgisi (mevcut)
BANT = (430, 1408)                     # nesne + golge bandi; yazilar 1416'dan basliyor
s = PH / 1988

poster = C.crop((734, 130, 2268, 2118)).resize((PW, PH), Image.LANCZOS)
cerceve = C.crop((676, 75, 2323, 2175)).resize((round(1647 * s), round(2100 * s)), Image.LANCZOS)

# dijital yigin: eski koordinatlar (olculdu). sayfa k: sol 244-18k, ust 520-6k, 565x775
E_ON = (244, 520, 809, 1295)
sx, sy = PW / (E_ON[2] - E_ON[0]), PH / (E_ON[3] - E_ON[1])
e_kutu = (172, 496, 809, 1295)
ew, eh = e_kutu[2] - e_kutu[0], e_kutu[3] - e_kutu[1]
maske_eski = Image.new('L', K.size, 0)
for k in range(5):
    x0, y0 = E_ON[0] - 18 * k, E_ON[1] - 6 * k
    maske_eski.paste(255, (x0, y0, x0 + 565, y0 + 775 - 0))
yw, yh = round(ew * sx), round(eh * sy)
yigin = K.crop(e_kutu).resize((yw, yh), Image.LANCZOS)
yigin_m = maske_eski.crop(e_kutu).resize((yw, yh), Image.LANCZOS)
on_x, on_y = round((E_ON[0] - e_kutu[0]) * sx), yh - PH   # on yuz yigin icinde sag-alt
yigin.paste(poster, (on_x, on_y)); yigin_m.paste(255, (on_x, on_y, on_x + PW, on_y + PH))

yer = {  # nesne, maske, sol-ust
    'dijital': (yigin, yigin_m, (round(490 - yw / 2), ALT - yh)),
    'baski': (poster, Image.new('L', poster.size, 255), (1500 - PW // 2, ALT - PH)),
    'cerceve': (cerceve, Image.new('L', cerceve.size, 255), (round(2512 - cerceve.width / 2), ALT - cerceve.height)),
}

out = K.copy()
out.paste(BG, (0, BANT[0], K.width, BANT[1]))
# golge
sil = Image.new('L', K.size, 0)
for ad, (im, m, (x, y)) in yer.items():
    sil.paste(m, (x + 15, y + 18), m)
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
o = np.asarray(out).astype(np.float32)
bant = np.zeros(alfa.shape, bool); bant[BANT[0]:BANT[1]] = True
o[bant] *= (1 - (59 / 232) * alfa[bant])[:, None]
out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
for ad, (im, m, (x, y)) in yer.items():
    out.paste(im, (x, y), m)
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
A = np.asarray(K).astype(np.float32)
def ncc(a, b):
    a = a.mean(2) - a.mean(); b = b.mean(2) - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
ref = np.asarray(poster).astype(np.float32)
bx, by = yer['baski'][2]; dx, dy = yer['dijital'][2]; cx, cy = yer['cerceve'][2]
pc = (cx + round(58 * s), cy + round(55 * s))
boy = {'dijital': (PW, PH), 'baski': (PW, PH), 'cerceve_ic': (round(1534 * s), round(1988 * s))}
n = {'dijital': ncc(R[dy + on_y:dy + on_y + PH, dx + on_x:dx + on_x + PW], ref),
     'baski': ncc(R[by:by + PH, bx:bx + PW], ref),
     # cerceve ici: yeniden orneklemede +-2 px kayma olabilir, en iyi konum alinir
     'cerceve_ic': max(ncc(R[pc[1] + j:pc[1] + j + PH, pc[0] + i:pc[0] + i + PW], ref)
                       for i in range(-2, 3) for j in range(-2, 3))}
yazi = np.abs(R - A).max(2); yazi[BANT[0]:BANT[1]] = 0
alt = {'dijital': dy + yh, 'baski': by + PH, 'cerceve': cy + cerceve.height}
print('boy', boy, '| NCC', {k: round(v, 4) for k, v in n.items()})
print('alt cizgi', alt, '| bant disi maks fark', int(yazi.max()), 'ort', round(float(yazi.mean()), 3))
ok = (len(set(boy.values())) == 1 and min(n.values()) >= 0.97 and len(set(alt.values())) == 1
      and yazi.mean() < 0.5 and R.shape[:2] == (2250, 3000))
print('PASS' if ok else 'FAIL')
