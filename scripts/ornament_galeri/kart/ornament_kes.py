#!/usr/bin/env python3
"""Kapak kompozitinden (R3_<STIL>.jpg + .json) ornament + ip kesiti: disk elipsi (json) + ip (altin ton, x 1500 +- 14) kart zemini
#F5F0E7 uzerine, yumusak alt golge. Urun pikselleri kompozitten aynen (yeniden cizim yok). -> RGB PIL"""
import json, math
import numpy as np, cv2
from PIL import Image
ZEMIN = (245, 240, 231)
def kes(jpg, ip_ust_pay=330, kenar=60, golge=None):
    im = np.asarray(Image.open(jpg).convert("RGB")).astype(np.float32)
    J = json.load(open(str(jpg) + ".json")); d = J["disk"]
    cx, cy, ea, eb, aci = d["cx"], d["cy"], d["eksen_a"], d["eksen_b"], d["aci"]
    H, W = im.shape[:2]; yy, xx = np.mgrid[:H, :W]
    t = math.radians(aci)
    ux = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t); uy = -(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)
    el = np.sqrt((ux / (ea / 2)) ** 2 + (uy / (eb / 2)) ** 2)
    R = d["R"]
    disk = np.clip((1.0 - el) * R / 2.0 + 0.5, 0, 1)                 # ~2 px yumusak kenar
    hsv = cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int32)
    ust = int(cy - R) - ip_ust_pay
    ipm = ((hsv[..., 0] >= 10) & (hsv[..., 0] <= 30) & (hsv[..., 1] > 70) & (np.abs(xx - cx) < 16) & (yy >= ust) & (yy < cy)).astype(np.uint8)
    ipm = cv2.morphologyEx(ipm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ipa = cv2.GaussianBlur(ipm.astype(np.float32), (0, 0), 0.8)
    # ip ust ucu: yumusak bitis (60 px)
    ipa *= np.clip((yy - ust) / 60.0, 0, 1)
    # delik: kart zemini gorunur (inceleme: delikte sahne duvari kaliyordu); ip delikten gectigi icin ip maskesi delikte korunur
    hx, hy, hr = J["yeni_delik"]["x"], J["yeni_delik"]["y"], J["delik_r_px"] * 0.8
    dl = np.clip((np.hypot(xx - hx, yy - hy) - hr) / 1.5 + 0.5, 0, 1)
    a = np.maximum(disk * dl, ipa)[..., None]
    # golge: disk maskesinin bulanik, asagi-saga kaydirilmis hali
    g = cv2.GaussianBlur((el < 1).astype(np.float32), (0, 0), 0.06 * R)
    acik = float(np.median(im[el < 0.5].mean(1))) > 180                # White / Ivory: zeminden ayrissin (inceleme K06)
    g = np.roll(g, (int(0.05 * R), int(0.02 * R)), (0, 1)) * (golge if golge is not None else (0.34 if acik else 0.22))
    if acik:                                                             # ince kenar konturu (yalniz disk disi 0..3 px)
        kont = np.clip(1 - np.abs(el - 1.004) * R / 3.0, 0, 1) * (el >= 1)
        g = np.maximum(g, kont * 0.16)
    zem = np.ones_like(im) * np.float32(ZEMIN)
    zem = zem * (1 - g[..., None])
    out = im * a + zem * (1 - a)
    x0, x1 = int(cx - R - kenar), int(cx + R + kenar); y0, y1 = ust, int(cy + R + kenar + 0.06 * R)
    return Image.fromarray(np.clip(out[y0:y1, x0:x1] + 0.5, 0, 255).astype(np.uint8))
if __name__ == "__main__":
    import sys
    kes(sys.argv[1]).save(sys.argv[2], quality=95)
