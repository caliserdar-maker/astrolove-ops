#!/usr/bin/env python3
"""VURGU ALTIN (Serdar 4 Eki onayi): ana sembollerdeki solgun/beyazimsi lekeleri giderir.
Bolge/yama yok: her piksele ayni surekli kural. Parlak (V 0.62-0.92 arasi yumusak gecis) ve
dusuk doygunluklu pikseller altin tonuna (H 43) ve hedef doygunluga (0.60, en tepe vurguda 0.50) cekilir,
beyaz tepe hafifce bastirilir. Koyu zemin (V < 0.62) degismez, desen korunur.
Kullanim: vurgu_altin.py GIRDI.jpg CIKTI.png
"""
import sys
import cv2
import numpy as np
from PIL import Image


def ss(x, e0, e1):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def vurgu_altin(rgb_u8):
    hsv = cv2.cvtColor(rgb_u8.astype(np.float32) / 255, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    wt = ss(V, 0.62, 0.92)
    St = 0.60 - 0.10 * ss(V, 0.96, 1.0)
    nS = S + wt * np.clip(St - S, 0, None)
    hw = wt * (1 - ss(S, 0.15, 0.45))
    nH = H * (1 - hw) + 43.0 * hw
    nV = V - wt * 0.10 * ss(V, 0.85, 1.0)
    out = cv2.cvtColor(np.stack([nH, nS, nV], -1).astype(np.float32), cv2.COLOR_HSV2RGB)
    return (out * 255).clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    a = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
    Image.fromarray(vurgu_altin(a)).save(sys.argv[2])
