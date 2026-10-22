#!/usr/bin/env python3
"""AI sahnelerindeki istenmeyen yazilari siler (OpenCV Telea inpaint). Yalniz verilen kutularda,
yerel medyandan sapan cizgiler maskelenir; kenarlar (kitap sirti, mum kenari) korunur.
Kullanim: sahne_yazi_sil.py GIRIS.png CIKIS.png "x0,y0,x1,y1,mod,esik" ...
  mod: 'duvar' (acik/koyu her sapma, medyan 31) | 'koyu' (yalniz koyu yazi, medyan 11)
"""
import sys
import cv2
import numpy as np

GIR, CIK = sys.argv[1:3]
im = cv2.imread(GIR); mask = np.zeros(im.shape[:2], np.uint8)
for arg in sys.argv[3:]:
    x0, y0, x1, y1, mod, esik = arg.split(','); x0, y0, x1, y1, esik = int(x0), int(y0), int(x1), int(y1), int(esik)
    if mod == 'duvar':
        sub = im[y0:y1, x0:x1]; d = np.abs(sub.astype(int) - cv2.medianBlur(sub, 31).astype(int)).max(2)
        m = cv2.dilate(((d > esik) * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    else:
        sub = im[y0:y1, x0:x1].astype(int); med = cv2.medianBlur(im[y0 - 6:y1 + 6, x0 - 6:x1 + 6], 11)[6:-6, 6:-6].astype(int)
        m = cv2.dilate((((med - sub).max(2) > esik) * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], m)
cv2.imwrite(CIK, cv2.inpaint(im, mask, 4, cv2.INPAINT_TELEA))
print('maske px', int((mask > 0).sum()))
