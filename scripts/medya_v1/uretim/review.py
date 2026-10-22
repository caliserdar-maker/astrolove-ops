#!/usr/bin/env python3
"""REVIEW: her galeri pozisyonu icin referans (canli 4570143815) | Kova-Kova yan yana, GERCEK ORAN (ayni yukseklik,
orani korunur, esnetme yok). 5 rengin kucuk sembol bolgesi %100 kirpma; video 4 durumu; paket gorselleri."""
import json, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import master as M
R = M.ROOT; OUT = R / 'paket'; RV = OUT / 'REVIEW'; IM = OUT / 'images'; VD = OUT / 'video'
for d in (RV, IM, VD): d.mkdir(parents=True, exist_ok=True)
import os
FNT = ImageFont.truetype(os.environ.get('FONT_DIR', '/home/user/astrolove-ops/work/fonts/') + 'Montserrat[wght].ttf', 28)
REF = sorted((R / 'etsy/REF_4570143815').glob('[01]*.jpg'))
from review_ad import NAMES as names
src = ['out/cover_MB.png'] + [f'out/card{n:02d}.png' for n in range(2, 11)] + ['out/cover_DB.png', 'out/cover_CI.png', 'out/cover_PW.png', 'out/cover_WP.png']
man = []
for i, (nm, s) in enumerate(zip(names, src)):
    im = Image.open(R / s).convert('RGB')
    im.save(IM / f'{nm}.jpg', quality=95, subsampling=0)
    ref = Image.open(REF[i]).convert('RGB')
    H = 1350 if im.height == 1350 else 1125
    a = ref.resize((round(ref.width * H / ref.height), H), Image.LANCZOS); b = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
    page = Image.new('RGB', (a.width + b.width + 60, H + 70), 'white'); d = ImageDraw.Draw(page)
    page.paste(a, (20, 60)); page.paste(b, (a.width + 40, 60))
    d.text((20, 15), f'{i+1:02d} REFERANS 4570143815 ({ref.width}x{ref.height})', fill='black', font=FNT)
    d.text((a.width + 40, 15), f'{i+1:02d} KOVA-KOVA v1 ({im.width}x{im.height})', fill='black', font=FNT)
    page.save(RV / f'P{i+1:02d}_{nm}_yan_yana.jpg', quality=92)
    man.append({'rank': i + 1, 'file': f'images/{nm}.jpg', 'size': [im.width, im.height], 'ref_size': [ref.width, ref.height]})
# 5 renk kucuk sembol %100
tiles = []
for c in ['MB', 'DB', 'CI', 'PW', 'WP']:
    cov = Image.open(R / f'out/cover_{c}.png'); x0, y0 = 151 + 150, 171 + 620
    t = cov.crop((x0, y0, x0 + 480, y0 + 170)); tiles.append((c, t))
page = Image.new('RGB', (480 + 180, 170 * 5 + 20), 'white'); d = ImageDraw.Draw(page)
for k, (c, t) in enumerate(tiles):
    page.paste(t, (170, 10 + k * 170)); d.text((10, 70 + k * 170), c, fill='black', font=FNT)
page.save(RV / 'SEMBOL_5_renk_100.png')
# video 4 durum (Kova | referans), %100 kare olcegi
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(R / 'out/AstroLove_AQUARIUS_AQUARIUS_12s.mp4'), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3); A = np.load(R / 'vid/ref_frames.npy')
for s, fr in {0: 0, 1: 20, 2: 60, 3: 110}.items():
    page = Image.new('RGB', (2200, 1420), 'white'); d = ImageDraw.Draw(page)
    page.paste(Image.fromarray(A[fr]), (20, 60)); page.paste(Image.fromarray(F[fr]), (1120, 60))
    d.text((20, 15), f'Durum {s} (kare {fr}) REFERANS video', fill='black', font=FNT); d.text((1120, 15), f'Durum {s} (kare {fr}) KOVA-KOVA v1', fill='black', font=FNT)
    page.save(RV / f'VIDEO_durum{s}_kare{fr:03d}.jpg', quality=92)
shutil.copy(R / 'out/AstroLove_AQUARIUS_AQUARIUS_12s.mp4', VD / 'AstroLove_AQUARIUS_AQUARIUS_12s.mp4')
json.dump(man, open(OUT / 'images_manifest.json', 'w'), indent=1)
print('REVIEW', len(list(RV.iterdir())), 'dosya')
