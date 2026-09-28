#!/usr/bin/env python3
"""CL kapak v4b (atmosferik varyant) 3000x2250. Serdar 28 Eyl: kapak cekici olsun ama
cerceve Prodigi kalacak ve tablo alani dolduracak (yazilar okunur).
Zemin: yatak odasi sahnesinin GERCEK duvarindan (yaprak golgesi + pencere isigi) kirpma;
aynali genisletme (ek yeri buyuk cercevenin arkasinda kalir), set_grade ile set koridoruna.
Cerceve/poster/golge: kapak v4 ile birebir (gercek BASKI_11x14 + 059 AG master, cift golge).
QC: NCC >= 0.99, golge yonu alt-sag, cerceve boyu v4 ile ayni (2060), yazi eklenmedi.
Kullanim: kapak_v4b_kur.py BASKI_11x14.jpg AG_BLANK_059.jpg SAHNE_YATAK.png CIKIS.jpg
"""
import sys
import os
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cerceve_master import cerceve_blank, set_grade, sahne_isik

BASKI, AGCH, SAHNE, CIK = sys.argv[1:5]
W, H = 3000, 2250

# zemin: gercek duvar isigi (330,20,690,520) + aynasi, 4:3 kirp, buyut, set koridoru
A = Image.open(SAHNE).convert('RGB').crop((335, 15, 695, 395))     # yapraksiz duvar (isik/golge oyunlu)
B = A.transpose(Image.FLIP_LEFT_RIGHT)
z = Image.new('RGB', (720, 380)); z.paste(A, (0, 0)); z.paste(B, (360, 0))
z = z.crop((107, 0, 613, 380)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
out, kazanc = set_grade(z)

# cerceve + poster (v4 ile ayni olcu)
R_YUZ = 20 / 599.6
DH = 2060
Bk = Image.open(BASKI).convert('RGB')
kx, ky = round(Bk.width * 5 / 279.4), round(Bk.height * 5 / 355.6)
Bk = Bk.crop((kx, ky, Bk.width - kx, Bk.height - ky))
PH = round(DH / (1 + 2 * R_YUZ * Bk.width / Bk.height))
PW = round(PH * Bk.width / Bk.height)
F = round(PW * R_YUZ)
PH = DH - 2 * F
poster = Bk.resize((PW, PH), Image.LANCZOS)
fr = cerceve_blank(AGCH, poster, F)
FX, FY = (W - fr.width) // 2, (H - fr.height) // 2

def golge(taban, dx, dy, sigma, guc):
    sil = Image.new('L', (W, H), 0)
    sil.paste(255, (FX + dx, FY + dy, FX + dx + fr.width, FY + dy + fr.height))
    a = np.asarray(sil.filter(ImageFilter.GaussianBlur(sigma))).astype(np.float32) / 255
    return Image.fromarray(np.clip(np.asarray(taban).astype(np.float32) * (1 - guc * a)[..., None], 0, 255).astype(np.uint8))

out = golge(out, 20, 26, 42, 0.20)
out = golge(out, 6, 8, 8, 0.38)
yuz_ref = np.asarray(fr).astype(np.float32)[2:F - 2, fr.width // 2 - 100:fr.width // 2 + 100].reshape(-1, 3).mean(0)
fr = sahne_isik(fr, out, (FX, FY, FX + fr.width, FY + fr.height), guc=0.10)
out.paste(fr, (FX, FY))
out.save(CIK, quality=95, subsampling=0)

R = np.asarray(Image.open(CIK).convert('RGB')).astype(np.float32)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
px0, py0 = FX + F + 40, FY + F + 40
n = ncc(R[py0:py0 + PH - 80, px0:px0 + PW - 80].mean(2), np.asarray(poster).astype(np.float32)[40:-40, 40:-40].mean(2))
# golge yonu: kenara yakin bant, ayni yondeki uzak banttan koyu olmali (zemin deseninden bagimsiz)
def bant(y0, y1, x0, x1): return float(R[y0:y1, x0:x1].mean())
cy0, cy1 = FY + fr.height // 2 - 60, FY + fr.height // 2 + 60
cx0, cx1 = FX + fr.width // 2 - 60, FX + fr.width // 2 + 60
d_sag = bant(cy0, cy1, FX + fr.width + 6, FX + fr.width + 18) - bant(cy0, cy1, FX + fr.width + 84, FX + fr.width + 120)
d_alt = bant(FY + fr.height + 6, FY + fr.height + 18, cx0, cx1) - bant(FY + fr.height + 84, FY + fr.height + 120, cx0, cx1)
yon = d_sag < -4 and d_alt < -4
yuz_cik = R[FY + 2:FY + F - 2, FX + fr.width // 2 - 100:FX + fr.width // 2 + 100].reshape(-1, 3).mean(0)
sapma = float(np.abs(yuz_cik - yuz_ref).max())
print(f'cerceve dis {fr.width}x{fr.height} yuz {F} | poster NCC {n:.4f} | golge temasi sag {d_sag:.1f} alt {d_alt:.1f} (her ikisi <-4) | set kazanc {kazanc} | cerceve renk sapmasi {sapma:.1f} (<=14)')
print('PASS' if R.shape[:2] == (H, W) and n >= 0.99 and yon and sapma <= 14 else 'FAIL')
