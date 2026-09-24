#!/usr/bin/env python3
"""Video QC. TEKNIK (ayri; gorsel dogruluk kaniti sayilmaz): 1080x1350, 30 fps, 360 kare, 12.0 s, ses yok.
GORSEL: V1 zaman cizelgesi: her karede Kova karesi ile (durum a,b,w) beklenen harman arasi MAE <= 2.5 (kodlama)
V2 referansla hizalilik: her karede baski acikligi disi (sahne) Kova kare ile referans kare MAE <= 2.5
V3 her sabit durumda sembol merkezi - isim merkezi (referans sembol merkezi) |dx|,|dy| <= 1.5 px
V4 burc sirasi sabit: her durumda sol ve sag sembol ayni kaynak (Aquarius) -> sol/sag kucuk sembol maskeleri NCC >= 0.9"""
import json, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
import master as M
V = 'out/AstroLove_AQUARIUS_AQUARIUS_12s.mp4'
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', V], capture_output=True, text=True).stdout) if False else None
info = subprocess.run(['ffmpeg', '-hide_banner', '-i', V], capture_output=True, text=True).stderr
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', V, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
tek = {'kare': int(F.shape[0]), 'boyut': '1080x1350' if F.shape[1:3] == (1350, 1080) else str(F.shape[1:3]),
       '30fps': ' 30 fps' in info, 'sure_12s': 'Duration: 00:00:12.00' in info, 'ses_yok': 'Audio:' not in info}
tek['SONUC'] = 'PASS' if tek['kare'] == 360 and tek['boyut'] == '1080x1350' and tek['30fps'] and tek['sure_12s'] and tek['ses_yok'] else 'FAIL'
plan = json.load(open('out/video_plan.json'))
st = {i: np.asarray(Image.open(f'out/cover_state{i}.png')).astype(np.float32) for i in range(4)}
A = np.load('vid/ref_frames.npy')
v1 = []; v2 = []
mask = np.ones((1350, 1080), bool); mask[171:1177, 151:927] = False
for i, (a, b, w, e) in enumerate(plan):
    exp = st[a] * (1 - w) + st[b] * w
    v1.append(float(np.abs(F[i].astype(np.float32) - exp).mean()))
    v2.append(float(np.abs(F[i].astype(np.float32)[mask] - A[i].astype(np.float32)[mask]).mean()))
meta = json.load(open('out/video_states_meta.json'))
v3 = {}; v4 = {}
for s in range(4):
    img = st[s][171:1177, 151:927].astype(np.float64)
    dev = np.abs(img - M.local_bg(img, 41)).max(2)
    res = []; pats = []
    for (cx, cy) in meta[str(s)]['glyph_dst_center']:
        box = (slice(int(cy) - 30, int(cy) + 30), slice(int(cx) - 60, int(cx) + 60))
        g = M.components(dev[box] > 30, 30); ys, xs = np.where(g)
        res.append([float((xs.min() + xs.max()) / 2 + box[1].start - cx), float((ys.min() + ys.max()) / 2 + box[0].start - cy)])
        pats.append(g[ys.min():ys.min() + 36, xs.min():xs.min() + 88].astype(float))
    v3[s] = res
    a, b = pats; h = min(a.shape[0], b.shape[0]); w = min(a.shape[1], b.shape[1]); a, b = a[:h, :w], b[:h, :w]
    v4[s] = float(((a - a.mean()) * (b - b.mean())).sum() / np.sqrt(((a - a.mean()) ** 2).sum() * ((b - b.mean()) ** 2).sum()))
gor = {'V1_maks_MAE': max(v1), 'V2_sahne_maks_MAE': max(v2), 'V3_hiza': v3, 'V4_sol_sag_NCC': v4}
ok = max(v1) <= 2.5 and max(v2) <= 2.5 and all(abs(x) <= 1.5 and abs(y) <= 1.5 for r in v3.values() for x, y in r) and min(v4.values()) >= 0.9
gor['SONUC'] = 'PASS' if ok else 'FAIL'
json.dump({'teknik': tek, 'gorsel': gor}, open('out/qc_video.json', 'w'), indent=1)
print('TEKNIK', tek); print('GORSEL', gor)
