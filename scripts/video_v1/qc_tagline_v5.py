#!/usr/bin/env python3
"""v5 tagline QC (PASS/FAIL): videonun kendi sabit karelerinden (E, N, M ortasi) uc tagline olculur.
Buyuk harf yuksekligi: ilk harf bileseni (I / I / Y, hepsi buyuk harf) yuksekligi. Taban: tagline_olc (satir yogunlugu).
Altin ortalama: cekirdek piksel RGB. PASS: yukseklik farki <= 1 px; M tabani = E tabani +-1 px (E ve N orijinal piksel, aralarindaki fark raporlanir); altin kanal farki <= 6.
Ayrica 4x buyutulmus yan yana gorsel. Kullanim: qc_tagline_v5.py YENI.mp4 GORSEL.jpg"""
import json, subprocess, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
sys.path.insert(0, __import__('os').path.dirname(__file__))
from tagline_olc import olc, Y0, Y1, X0, X1
yeni, gorsel = sys.argv[1:3]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', yeni, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
Y = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
plan = json.load(open(yeni.replace('.mp4', '_meta.json')))['plan']
AD = {'E': 'EMILY & JAMES', 'N': 'ISABELLA & NOAH', 'M': 'ALEXANDER & MIA'}
def ilk_harf(F):
    b = F[Y0:Y1, X0:X1].astype(np.float32); m = (b[..., 0] - b[..., 2]) > 40
    lab, n = ndimage.label(ndimage.binary_dilation(m, structure=np.ones((3, 51))))
    m &= lab == (np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1)
    l2, n2 = ndimage.label(m); sl = ndimage.find_objects(l2)
    ilk = min(sl, key=lambda s: s[1].start)
    return ilk[0].stop - ilk[0].start
sat, kirp = {}, {}
for st in 'ENM':
    k = [i for i, p in enumerate(plan) if p == [st, st, 0.0]]; F = Y[k[len(k) // 2]]
    r = olc(F); r['buyuk_harf_yuk'] = int(ilk_harf(F)); r['kare'] = k[len(k) // 2]; sat[st] = r
    kirp[st] = Image.fromarray(F[1015:1070, 300:780]).resize((480 * 4, 55 * 4), Image.NEAREST)
fark = lambda key: max(sat[a][key] for a in 'ENM') - min(sat[a][key] for a in 'ENM')
altin_fark = max(max(sat[a]['altin_ort'][c] for a in 'ENM') - min(sat[a]['altin_ort'][c] for a in 'ENM') for c in range(3))
ok = {'yukseklik_<=1': fark('buyuk_harf_yuk') <= 1, 'taban_M_E_<=1': abs(sat['M']['taban_y'] - sat['E']['taban_y']) <= 1, 'altin_<=6': altin_fark <= 6}
s = {'taglinelar': sat, 'fark': {'buyuk_harf_yuk': fark('buyuk_harf_yuk'), 'taban_y': fark('taban_y'), 'altin_kanal_maks': round(altin_fark, 1)},
     'PASS': ok, 'SONUC': 'PASS' if all(ok.values()) else 'FAIL'}
json.dump(s, open(yeni.replace('.mp4', '_tagline_qc.json'), 'w'), indent=1)
W, H = kirp['E'].size
pg = Image.new('RGB', (W, 3 * (H + 60)), 'white'); d = ImageDraw.Draw(pg)
for i, st in enumerate('ENM'):
    r = sat[st]; y = i * (H + 60)
    d.text((10, y + 8), f"{AD[st]}  |  buyuk harf {r['buyuk_harf_yuk']} px  |  taban y {r['taban_y']}  |  altin {r['altin_ort']}  (4x, video karesi {r['kare']})", fill='black')
    pg.paste(kirp[st], (0, y + 50))
    ty = (r['taban_y'] - 1015) * 4 + y + 50; d.line([(0, ty), (W, ty)], fill=(255, 0, 0), width=2)
pg.save(gorsel, quality=92)
print('| tagline | buyuk harf yuk. (px) | taban y | altin ort (R,G,B) | genislik |\n|---|---|---|---|---|')
for st in 'ENM':
    r = sat[st]; print(f"| {AD[st]} | {r['buyuk_harf_yuk']} | {r['taban_y']} | {tuple(r['altin_ort'])} | {r['genislik']} |")
print(json.dumps({k: s[k] for k in ('fark', 'PASS', 'SONUC')}))
sys.exit(0 if s['SONUC'] == 'PASS' else 1)
