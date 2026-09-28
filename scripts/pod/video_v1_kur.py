#!/usr/bin/env python3
"""Kapak videosu v1: yavas zoom (Ken Burns), 2880x2160, 12 sn, 30 fps, sessiz.
Girdi: kapak 3000x2250 (v9 hatti). Zoom 1.00 -> 1.08, merkez sabit; ffmpeg zoompan.
QC: cikti var, boyut 2880x2160, sure 11.5-12.5 sn, ilk kare kapakla NCC >= 0.99.
Kullanim: video_v1_kur.py KAPAK.jpg CIKIS.mp4
"""
import subprocess
import sys

import numpy as np

KAPAK, CIK = sys.argv[1:3]
SURE, FPS = 12, 30
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', KAPAK,
       '-vf', (f"scale=5760:4320,zoompan=z='1+0.08*on/{SURE*FPS}':"
               f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={SURE*FPS}:s=2880x2160:fps={FPS}"),
       '-t', str(SURE), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '18', CIK]
subprocess.run(cmd, check=True)

# QC
import cv2
from PIL import Image
v = cv2.VideoCapture(CIK)
w, h = int(v.get(cv2.CAP_PROP_FRAME_WIDTH)), int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))
n = int(v.get(cv2.CAP_PROP_FRAME_COUNT)); fps = v.get(cv2.CAP_PROP_FPS)
ok, kare = v.read(); v.release()
sure = n / fps
ref = np.asarray(Image.open(KAPAK).convert('RGB').resize((w, h), Image.LANCZOS)).astype(np.float32).mean(2)
ilk = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB).astype(np.float32).mean(2)
a = ilk - ilk.mean(); b = ref - ref.mean()
ncc = float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
print(f'{w}x{h} | {sure:.1f} sn @ {fps:.0f} fps | ilk kare NCC {ncc:.4f}')
print('PASS' if (w, h) == (2880, 2160) and 11.5 <= sure <= 12.5 and ncc >= 0.99 else 'FAIL')
