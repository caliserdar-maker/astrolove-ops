#!/usr/bin/env python3
"""video-v1 v3 zamanlamasi (Serdar karari 25 Eyl 2026). Durumlar v2 ile ayni: E = referans kare 150 (EMILY & JAMES),
N = video_duzelt.py ciktisi *_N.png (ISABELLA & NOAH).
Zaman cizelgesi (30 fps): gecis penceresi 12 kare (0,4 sn, referansta olculen egri); her durum 30 kare (1,0 sn) sabit.
Egrinin ilk 2 karesi (agirlik 0.005, 0.015) kodek gurultusunun altinda, gorunmez (olculdu: kare farki 0.039 < sabit gurultu 0.051);
bu yuzden pencere kare 4'te baslar, ilk GORUNUR gecis karesi (agirlik 0.105) kare 6 = 0,20 sn.
Periyot 2 x (30 + 12) = 84 kare = 2,8 sn. Kesintisiz dongu icin uzunluk periyodun kati: 4 x 84 = 336 kare = 11,20 sn
(12 sn'ye en yakin; 5 periyot 14,0 sn). Video E ile biter: sondaki 26 kare + bastaki 4 kare = 30 kare E.
Kullanim: video_v3.py REF.mp4 N.png v2_meta.json CIKTI.mp4"""
import json, subprocess, sys, time
import numpy as np
from PIL import Image
ref, npng, v2meta, out = sys.argv[1:5]
t0 = time.time()
FPS, BAS, GECIS, SABIT, PERIYOT_N = 30, 4, 12, 30, 4
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
ST = {'E': A[150].astype(np.float32), 'N': np.asarray(Image.open(npng).convert('RGB')).astype(np.float32)}
# referans gecis egrisi: 4 pencerenin ortalamasi, 0..1'e normalize, 12 araliga (13 nokta) yeniden orneklenir
W = np.array(list(json.load(open(v2meta))['agirlik'].values())).mean(0)
W = (W - W[0]) / (W[-1] - W[0])
egri = np.interp(np.arange(GECIS + 1) * (len(W) - 1) / GECIS, np.arange(len(W)), W)   # egri[0]=0 (son sabit kare), egri[12]=1
n = PERIYOT_N * 2 * (SABIT + GECIS)
plan, cur, i, baslar = [], 'E', 0, []
plan += [('E', 'E', 0.0)] * BAS
while len(plan) < n:
    nxt = 'N' if cur == 'E' else 'E'
    baslar.append(len(plan))
    plan += [(cur, nxt, float(egri[k])) for k in range(1, GECIS + 1)]
    cur = nxt
    plan += [(cur, cur, 0.0)] * SABIT
plan = plan[:n]
assert plan[-1][:2] == ('E', 'E') and all(p[:2] == ('E', 'E') for p in plan[-(SABIT - BAS):])
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', str(FPS), '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0',
       '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for j, (x, y, w) in enumerate(plan):
    pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
    if (j + 1) % 84 == 0:
        el = time.time() - t0; print(f'kare {j+1}/{n} %{100*(j+1)/n:.0f} gecen {el:.0f}s kalan ~{el/(j+1)*(n-j-1):.0f}s', flush=True)
pr.stdin.close(); assert pr.wait() == 0
json.dump({'kare': n, 'sure_sn': n / FPS, 'egri': [round(float(e), 4) for e in egri], 'planli_gecis_baslari_kare': baslar,
           'plan': [[x, y, round(w, 4)] for x, y, w in plan]}, open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s kare={n} sure={n/FPS:.2f}s gecis_baslari={baslar}', flush=True)
