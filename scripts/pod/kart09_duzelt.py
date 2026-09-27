#!/usr/bin/env python3
"""CL kart 09 (Look a little closer.) duzeltmesi. Taban: ChatGPT karti (3000x2250), baslik/etiket/metinler kalir.
ChatGPT'nin buyutme paneli yapay 3B altin cizimdi (kabartma gorunumu, 'No raised surface' ile celisiyor) ve
kucuk poster yeniden cizilmisti. Ikisi de GERCEK CL baski dosyasindan (hat ciktisi BASKI_11x14, 3307x4200,
EMILY/JAMES) birebir alinir:
  - kucuk poster: dosyanin tamami, ayni yukseklik/merkez
  - panel: dosyadan sag Cancer kivrimi kirpimi (1150x894 px -> 1654x1286, 1.44x), yeniden cizim yok
  - kutu ve baglanti cizgisi kirpimin gercek yerini gosterir
Alt cizgi+satir kart 03 v2'den (Lato idi). Golge kart 02/08 ile ayni.
QC: boyut, poster NCC >= 0.99, panel NCC >= 0.99, kutu konumu kirpimla ayni, izin disi degisim yok.
Kullanim: kart09_duzelt.py CHATGPT_09.jpg BASKI_11x14.jpg KART03_V2.jpg CIKIS.jpg
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

G09, BASKI, K03V2, CIK = sys.argv[1:5]
BG = (237, 232, 226); CIZGI = (136, 120, 94)
K = Image.open(G09).convert('RGB'); A0 = np.asarray(K).astype(np.float32)
B = Image.open(BASKI).convert('RGB'); V2 = Image.open(K03V2).convert('RGB')
out = K.copy()
ORTA = (100, 540, 2900, 1900)                       # poster + panel + cizgi bolgesi
out.paste(BG, ORTA)

TH = 974; TW = round(B.width * TH / B.height); TX = round((170 + 951) / 2 - TW / 2); TY = 717
thumb = B.resize((TW, TH), Image.LANCZOS)
PX0, PY0, PX1, PY1 = 1168, 568, 2822, 1854
KX0, KY0, KW = 1530, 1403, 1150
KH = round(KW * (PY1 - PY0) / (PX1 - PX0))
panel = B.crop((KX0, KY0, KX0 + KW, KY0 + KH)).resize((PX1 - PX0, PY1 - PY0), Image.LANCZOS)

sil = Image.new('L', out.size, 0)
for x, y, w, h in ((TX, TY, TW, TH), (PX0, PY0, PX1 - PX0, PY1 - PY0)):
    sil.paste(255, (x + 15, y + 18, x + 15 + w, y + 18 + h))
alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
o = np.asarray(out).astype(np.float32); m = np.zeros(alfa.shape, bool); m[ORTA[1]:ORTA[3], ORTA[0]:ORTA[2]] = True
o[m] *= (1 - (59 / 232) * alfa[m])[:, None]
out = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
out.paste(thumb, (TX, TY)); out.paste(panel, (PX0, PY0))
d = ImageDraw.Draw(out)
s = TH / B.height
bx0, by0 = TX + KX0 * s, TY + KY0 * s; bx1, by1 = TX + (KX0 + KW) * s, TY + (KY0 + KH) * s
d.rectangle((bx0, by0, bx1, by1), outline=CIZGI, width=3)
ym = (by0 + by1) / 2
d.line((bx1, ym, PX0, ym), fill=CIZGI, width=3)
out.paste(V2.crop((0, 2130, 3000, 2250)), (0, 2130))
out.save(CIK, quality=95, subsampling=0)

# QC
R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
tm = np.ones((TH, TW), bool); tm[int(by0 - TY) - 4:int(by1 - TY) + 5, int(bx0 - TX) - 4:int(bx1 - TX) + 5] = False
n_t = ncc(R[TY:TY + TH, TX:TX + TW].mean(2)[tm], np.asarray(thumb).astype(np.float32).mean(2)[tm])
n_p = ncc(R[PY0:PY1, PX0:PX1].mean(2), np.asarray(panel).astype(np.float32).mean(2))
izin = np.zeros(R.shape[:2], bool); izin[ORTA[1]:ORTA[3], ORTA[0]:ORTA[2]] = True; izin[2130:, :] = True
fark = np.abs(R - A0).max(2)[~izin]
print(f'boyut {R.shape[1]}x{R.shape[0]} | poster {TW}x{TH} NCC {n_t:.4f} | panel NCC {n_p:.4f} (buyutme {(PX1 - PX0) / KW:.2f}x) | '
      f'kutu ({bx0:.0f},{by0:.0f})-({bx1:.0f},{by1:.0f}) | izin disi fark ort {fark.mean():.3f}')
print('PASS' if R.shape[:2] == (2250, 3000) and n_t >= 0.99 and n_p >= 0.99 and fark.mean() < 0.5 else 'FAIL')
