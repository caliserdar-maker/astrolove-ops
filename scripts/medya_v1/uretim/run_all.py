#!/usr/bin/env python3
"""medya-v1 Kova-Kova tam hat (tek surec). Girdi dizini hazir oldugunda sirayla:
master (5 renk) -> QC master -> video (4 durum, referans zaman cizelgesi) -> QC video -> kartlar 02-10 -> QC kart
-> REVIEW + images + kanit. Her adimda ETA. Etsy/Prodigi erisimi yok."""
import subprocess, sys, time, json
ALL = {'uretim': [['master.py'], ['video.py'], ['cards.py'], ['review.py'], ['kanit.py']],
       'qc': [['qc_master.py'], ['qc_video.py'], ['qc_cards.py'], ['iz_tarama.py'], ['iz_kanit.py']]}
mode = sys.argv[1] if len(sys.argv) > 1 else 'hepsi'
steps = ALL['uretim'] + ALL['qc'] if mode == 'hepsi' else ALL[mode]
t0 = time.time()
import os, numpy as np
os.makedirs('vid', exist_ok=True); os.makedirs('out', exist_ok=True)
if not os.path.exists('vid/ref_frames.npy'):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'refs_centered/AstroLove_Centered_Immediate_12s.mp4', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    np.save('vid/ref_frames.npy', np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3))
for i, st in enumerate(steps, 1):
    r = subprocess.run([sys.executable, '-u', '-W', 'ignore'] + st)
    el = time.time() - t0
    print(f'### [{i}/{len(steps)}] %{100*i/len(steps):.0f} gecen {el:.0f}s kalan ~{el/i*(len(steps)-i):.0f}s {st[0]} cikis={r.returncode}', flush=True)
    if r.returncode != 0: sys.exit(r.returncode)
