"""Compare frames written by video_uret.py --kareler with onayli/kare_{s}s.jpg. PASS if every frame mean |diff| < 2.5.

Usage: python3 dogrula.py <dir with gemini-and-leo-kare_{s}s.jpg> [--slug gemini-and-leo]
"""
import argparse, glob, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ESIK = 2.5
ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--slug', default='gemini-and-leo'); g = ap.parse_args()
ok = True; n = 0
for ref in sorted(glob.glob(os.path.join(HERE, 'onayli', 'kare_*s.jpg')), key=lambda p: float(re.findall(r'kare_([\d.]+)s', p)[0])):
    sec = re.findall(r'kare_([\d.]+)s', ref)[0]
    p = os.path.join(g.dir, f'{g.slug}-kare_{float(sec):g}s.jpg')
    if not os.path.exists(p):
        print(f'kare {sec}s: YOK FAIL'); ok = False; continue
    a = np.asarray(Image.open(ref).convert('RGB')).astype(np.float32); b = np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
    if a.shape != b.shape:
        print(f'kare {sec}s: olcu {a.shape} vs {b.shape} FAIL'); ok = False; continue
    d = float(np.abs(a - b).mean()); n += 1
    print(f'kare {sec}s: ortalama fark {d:.3f} {"PASS" if d < ESIK else "FAIL"}'); ok &= d < ESIK
print(f'OZET dogrulama {n} kare, esik {ESIK}: {"PASS" if ok and n else "FAIL"}')
sys.exit(0 if ok and n else 1)
