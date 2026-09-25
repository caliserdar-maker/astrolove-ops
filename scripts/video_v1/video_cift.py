#!/usr/bin/env python3
"""video-v1: 77 cift videosu (Serdar onayli v5 sablonu, 25 Eyl 2026). Girdi: medya-v1 A1_77/<CIFT>/POSTER_EJ|IN|AM.png
(kisisel-v1 kodu, 2400x3000). AM yoksa cikis kodu 3 (BEKLE).
Her durum: referans kare 150 (maket) + poster acikligina cift posteri: v2'de olculen afin (ECC) + kanal bazli ton (Cancer-Libra
kisisel E posteri -> kare 150) + duzgun aydinlatma haritasi (sigma 30; Cancer-Libra'da olculdu: E ort fark 1.77, N capraz 1.54).
Aciklik kenari 3 px asindirilir, 2 px yumusak (cerceve golgesi referanstan kalir).
Zamanlama v5 ile ayni: EJ -> IN -> AM -> EJ, pencere 12 kare (referans egrisi), ilk gorunur gecis 0,20 sn, sabit 30 kare, 378 kare = 12,6 sn.
Kullanim: video_cift.py REF.mp4 v2_meta.json P_emily_james.png CIFT_DIZINI CIKTI.mp4"""
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image
ref, v2meta, p_ref, cdir, out = sys.argv[1:6]
cdir = Path(cdir)
eksik = [k for k in ('EJ', 'IN', 'AM') if not (cdir / f'POSTER_{k}.png').exists()]
if eksik: print(f'BEKLE: {cdir.name} eksik {eksik}'); sys.exit(3)
t0 = time.time()
FPS, BAS, GECIS, SABIT, TUR, SIRA = 30, 4, 12, 30, 3, ['EJ', 'IN', 'AM']
X0, Y0, X1, Y1 = 151, 171, 927, 1177
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
F = A[150].astype(np.float32)
v2 = json.load(open(v2meta)); Maf = np.array(v2['M'], np.float32)
warp = lambda p: cv2.warpAffine(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), Maf, (1080, 1350), flags=cv2.INTER_AREA)
reg = np.zeros((1350, 1080), bool); reg[Y0:Y1, X0:X1] = True
Wr = warp(p_ref)
ton = [np.polyfit(Wr[..., c][reg], F[..., c][reg], 1) for c in range(3)]
tf = lambda W: np.stack([np.polyval(ton[c], W[..., c]) for c in range(3)], 2)
m = reg.astype(np.float32)[..., None]
Tr = tf(Wr)
G = np.clip(cv2.GaussianBlur(F * m, (0, 0), 30) / np.maximum(cv2.GaussianBlur(Tr * m, (0, 0), 30), 1), 0.6, 1.6)
al = np.zeros((1350, 1080), np.float32); al[Y0 + 3:Y1 - 3, X0 + 3:X1 - 3] = 1
al = cv2.GaussianBlur(al, (0, 0), 1.0)[..., None]
ST = {k: F * (1 - al) + np.clip(G * tf(warp(cdir / f'POSTER_{k}.png')), 0, 255) * al for k in SIRA}
dogrulama = round(float(np.abs(G * Tr - F).mean(2)[Y0 + 3:Y1 - 3, X0 + 3:X1 - 3].mean()), 3)
Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
n = TUR * len(SIRA) * (SABIT + GECIS)
plan, k = [('EJ', 'EJ', 0.0)] * BAS, 0
while len(plan) < n:
    x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
    plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
plan = plan[:n]
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', str(FPS), '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0',
       '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for j, (x, y, w) in enumerate(plan):
    pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
pr.stdin.close(); assert pr.wait() == 0
for kk in SIRA: Image.fromarray(np.clip(np.rint(ST[kk]), 0, 255).astype(np.uint8)).save(out.replace('.mp4', f'_{kk}.png'))
json.dump({'cift': cdir.name, 'kare': n, 'sure_sn': n / FPS, 'sira': SIRA, 'aydinlatma_dogrulama_E_ort': dogrulama,
           'plan': [[x, y, round(w, 4)] for x, y, w in plan]}, open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s {cdir.name} kare={n} dogrulama={dogrulama}', flush=True)
