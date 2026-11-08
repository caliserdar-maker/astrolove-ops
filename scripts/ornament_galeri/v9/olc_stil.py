# olc_stil.py (8 Kas) - renkli/acik duz disk olcumu (olc_tek.py'nin renkten bagimsiz hali).
# Baslangic: referans sahne olcumu (ayni kadraj, fal edit). Disk kenari gradyanla elips; delik: disk medyan renginden uzak, altin olmayan bolge.
# kullanim: python olc_stil.py sahne.png ref.olc.json
import cv2, numpy as np, sys, json
f_, refj = sys.argv[1], sys.argv[2]
ref = json.load(open(refj))
im = cv2.imread(f_); H, W = im.shape[:2]; f = im.astype(np.float32); b, g, r = cv2.split(f)
cx, cy, R = ref["cx"], ref["cy"], (ref["A"] + ref["B"]) / 4
L = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.5)
Lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
gx = sum(np.abs(cv2.Sobel(cv2.GaussianBlur(Lab[..., k], (0, 0), 1.5), cv2.CV_32F, 1, 0)) for k in range(3))
gy = sum(np.abs(cv2.Sobel(cv2.GaussianBlur(Lab[..., k], (0, 0), 1.5), cv2.CV_32F, 0, 1)) for k in range(3))
for _ in range(2):
    pts = []
    for a in np.deg2rad(np.arange(0, 360, 2)):
        if 75 < np.rad2deg(a) % 360 < 105 + 180 and 255 < np.rad2deg(a) % 360 < 285:
            continue
        ca, sa = np.cos(a), np.sin(a); best = (0, None)
        for rr in np.arange(0.92 * R, 1.08 * R, 0.5):
            x, y = cx + rr * ca, cy + rr * sa
            if 1 <= x < W - 1 and 1 <= y < H - 1:
                v = gx[int(y), int(x)] * abs(ca) + gy[int(y), int(x)] * abs(sa)
                if v > best[0]: best = (v, (x, y))
        if best[1] and not (250 < np.rad2deg(a) % 360 < 290): pts.append(best[1])   # ust (ip) atlanir
    P = np.array(pts, np.float32); (ex, ey), (A, B), ang = cv2.fitEllipse(P); Rm = (A + B) / 4
    cx, cy, R = ex, ey, Rm
yy, xx = np.mgrid[0:H, 0:W]
ic = (xx - ex) ** 2 + (yy - ey) ** 2 < (0.85 * Rm) ** 2
med = np.median(Lab[ic & (yy > ey)], 0)
fark = np.sqrt(((Lab - med) ** 2).sum(2))
alt = ((g - b) > 25) & (g > 0.33 * r) & (r > 0.8 * g)
# delik araniyor: referans delik konumu cevresi
rhx, rhy, rhr = ref["delik"]; rhx, rhy = ex + (rhx - ref["cx"]) * Rm / ((ref["A"] + ref["B"]) / 4), ey + (rhy - ref["cy"]) * Rm / ((ref["A"] + ref["B"]) / 4)
bol = (np.hypot(xx - rhx, yy - rhy) < 2.2 * rhr) & ((xx - ex) ** 2 + (yy - ey) ** 2 < (0.97 * Rm) ** 2)
yab = bol & (fark > 25) & ~cv2.dilate(alt.astype(np.uint8), np.ones((3, 3))).astype(bool)
n, lab, st, cen = cv2.connectedComponentsWithStats(yab.astype(np.uint8))
i = 1 + np.argmax(st[1:, 4]); hx, hy = cen[i]
pts = []
for a in np.deg2rad(np.arange(-30, 211, 6)):
    rs = np.arange(3, 0.2 * Rm, 0.5)
    v = np.array([fark[int(hy + q * np.sin(a)), int(hx + q * np.cos(a))] for q in rs])
    k = int(np.argmax(-np.diff(v))); pts.append((hx + rs[k] * np.cos(a), hy + rs[k] * np.sin(a)))
Q = np.array(pts); A_ = np.c_[2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))]
for _ in range(3):
    s = np.linalg.lstsq(A_, (Q ** 2).sum(1), rcond=None)[0]; c0, c1 = s[0], s[1]; rr = np.sqrt(s[2] + c0 ** 2 + c1 ** 2)
    res = np.abs(np.hypot(Q[:, 0] - c0, Q[:, 1] - c1) - rr); k = res < max(2, np.percentile(res, 70)); A_, Q = A_[k], Q[k]
d = dict(dosya=f_, W=W, H=H, cx=ex, cy=ey, A=A, B=B, aci=ang, R=Rm, delik=[float(c0), float(c1), float(rr)],
         delik_R=float(np.hypot(c0 - ex, c1 - ey) / Rm), r_R=float(rr / Rm), yatay=float((c0 - ex) / Rm))
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()})
json.dump({k: (float(v) if not isinstance(v, (str, list)) else v) for k, v in d.items()}, open(f_ + ".olc.json", "w"), default=float)
