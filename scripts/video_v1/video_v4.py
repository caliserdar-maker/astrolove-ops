#!/usr/bin/env python3
"""video-v1 v4 (Serdar karari 25 Eyl 2026): 3 cift doner, sembol sirasi hep Cancer solda.
Durumlar: E = referans kare 150 (EMILY & JAMES, aynen); N = v2 *_N.png (ISABELLA & NOAH);
M = referans kare 20 (ALEXANDER & MIA; tagline 'You Feel Like Home' ORIJINAL piksel) + sembol/isim bandi kisisel-v1
isim koduyla (P_alexander_mia.png, Cancer solda), v2'de olculen afin (ECC) ve ton uydurmasiyla.
Zamanlama v3 ile ayni: pencere 12 kare (0,4 sn, referans egrisi), ilk gorunur gecis kare 6 = 0,20 sn, her durum 30 kare (1,0 sn).
Tur E->N->M->E = 3 x 42 = 126 kare = 4,2 sn; 3 tur = 378 kare = 12,6 sn; video E ile biter (26 + 4 = 30 kare).
Kullanim: video_v4.py REF.mp4 N.png P_alexander_mia.png v2_meta.json CIKTI.mp4"""
import json, subprocess, sys, time
import numpy as np, cv2
from PIL import Image
ref, npng, p_m, v2meta, out = sys.argv[1:6]
t0 = time.time()
FPS, BAS, GECIS, SABIT, TUR, SIRA = 30, 4, 12, 30, 3, ['E', 'N', 'M']
BAND, OPEN = (785, 975), (151, 171, 927, 1177)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
v2 = json.load(open(v2meta))
Maf = np.array(v2['M'], np.float32); ton = [np.array(t) for t in v2['ton']]
P = np.asarray(Image.open(p_m).convert('RGB')).astype(np.float32)
W = cv2.warpAffine(P, Maf, (1080, 1350), flags=cv2.INTER_AREA)
Tm = np.stack([np.polyval(ton[c], W[..., c]) for c in range(3)], 2)
a = np.zeros((1350, 1080), np.float32); a[BAND[0]:BAND[1], OPEN[0] + 8:OPEN[2] - 8] = 1
a = cv2.GaussianBlur(a, (0, 0), 3)[..., None]
F20 = A[20].astype(np.float32)
Mst = F20 * (1 - a) + Tm * a
ST = {'E': A[150].astype(np.float32), 'N': np.asarray(Image.open(npng).convert('RGB')).astype(np.float32), 'M': Mst}
Image.fromarray(np.clip(np.rint(Mst), 0, 255).astype(np.uint8)).save(out.replace('.mp4', '_M.png'))
kontrol = {'M_disi_fark_F20_F150': round(float(np.abs(F20 - ST['E'])[:BAND[0], OPEN[0]:OPEN[2]].mean()), 4),
           'M_bant_kenar_fark': round(float(np.abs(Tm - F20).mean(2)[BAND[0]:BAND[0] + 6, OPEN[0]:OPEN[2]].mean()), 3)}
Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
n = TUR * len(SIRA) * (SABIT + GECIS)
plan, baslar, k = [('E', 'E', 0.0)] * BAS, [], 0
while len(plan) < n:
    x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
    baslar.append(len(plan))
    plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
plan = plan[:n]
assert all(p[:2] == ('E', 'E') for p in plan[-(SABIT - BAS):])
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', str(FPS), '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0',
       '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for j, (x, y, w) in enumerate(plan):
    pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
    if (j + 1) % 126 == 0:
        el = time.time() - t0; print(f'kare {j+1}/{n} %{100*(j+1)/n:.0f} gecen {el:.0f}s kalan ~{el/(j+1)*(n-j-1):.0f}s', flush=True)
pr.stdin.close(); assert pr.wait() == 0
json.dump({'kare': n, 'sure_sn': n / FPS, 'sira': SIRA, 'egri': [round(float(e), 4) for e in egri], 'pencere_baslari': baslar,
           'kontrol': kontrol, 'tagline_M': 'You Feel Like Home', 'plan': [[x, y, round(w, 4)] for x, y, w in plan]},
          open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s kare={n} sure={n/FPS:.2f}s pencereler={baslar} {kontrol}', flush=True)
