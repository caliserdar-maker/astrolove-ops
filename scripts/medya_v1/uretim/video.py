#!/usr/bin/env python3
"""Kova-Kova video: referans videonun 4 sabit durumu ayni algoritmayla (master.build) Kova'ya cevrilir,
her kare referans zaman cizelgesindeki (durum / cozulme agirligi) ile yeniden kurulur. MB."""
import json, subprocess, sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
import master as M
A = np.load('vid/ref_frames.npy')
STATE_FRAME = {0: 0, 1: 20, 2: 60, 3: 110}
WIDE = ((30, 385), (385, 750))
states = {}; meta = {}
t0 = time.time()
for i, (st, fr) in enumerate(STATE_FRAME.items(), 1):
    meta[st] = M.build('MB', cov=A[fr].astype(np.float64), tag=f'state{st}', rois=WIDE, detect_dst=True)
    states[st] = np.asarray(Image.open(f'out/cover_state{st}.png')).astype(np.float32)
    el = time.time() - t0; print(f'[{i}/4] %{25*i} gecen {el:.0f}s kalan ~{el/i*(4-i):.0f}s durum{st} {meta[st]["glyph_dst_center"]}', flush=True)
json.dump(meta, open('out/video_states_meta.json', 'w'), indent=1)
# zaman cizelgesi: her kare icin referans durum sablonlarina en yakin (a,b,w)
band = lambda X: X[171 + 600:171 + 920, 151:927].astype(np.float32)
S = {k: band(A[v]) for k, v in STATE_FRAME.items()}
order = [0, 1, 2, 3]
plan = []
for i in range(len(A)):
    f = band(A[i]); best = None
    for a in order:
        e = np.abs(S[a] - f).mean()
        if best is None or e < best[0]: best = (e, a, a, 0.0)
    if best[0] >= 1.0:
        for a in order:
            b = (a + 1) % 4
            v = S[b] - S[a]; w = float(np.clip((v * (f - S[a])).sum() / (v * v).sum(), 0, 1))
            e = np.abs(S[a] + w * v - f).mean()
            if e < best[0]: best = (e, a, b, w)
    plan.append([int(best[1]), int(best[2]), round(best[3], 4), round(float(best[0]), 3)])
json.dump(plan, open('out/video_plan.json', 'w'))
out = 'out/AstroLove_AQUARIUS_AQUARIUS_12s.mp4'
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', '30', '-i', '-',
       '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
t1 = time.time()
for i, (a, b, w, e) in enumerate(plan):
    fr = states[a] * (1 - w) + states[b] * w
    proc.stdin.write(np.clip(np.rint(fr), 0, 255).astype(np.uint8).tobytes())
    if (i + 1) % 90 == 0:
        el = time.time() - t1; print(f'kare {i+1}/360 %{100*(i+1)/360:.0f} gecen {el:.0f}s kalan ~{el/(i+1)*(359-i):.0f}s', flush=True)
proc.stdin.close(); assert proc.wait() == 0
print('video yazildi', out)
