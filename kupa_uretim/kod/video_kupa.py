#!/usr/bin/env python3
"""Kupa ilan videosu (Bizim Yilimiz videosuyla ayni fikir, Serdar 17 Eki): kapak sabit, kare 1080x1080, sessiz.
Sol kupadaki (on yuz) ozgun sembol sessizce silinir; iki kucuk burc isaretinden tozlar akar ve ozgun sembolu yeniden
olusturur. Son kare = ilk kare (Etsy dongusu kesintisiz). Arka kupa degismez.
Akis: 0,2 sn kapak, 0,7 sn sembol tamamen silinir, 3,8 sn toz akisi, 1,6 sn kapak (toplam 6,3 sn).
Kullanim: python video_kupa.py <sahne_jpg> <geo_json> <baski_png> <kapak_jpg> <cikti_mp4>
kapak_jpg: ayni sahne+baski ile kapak_canva.py ciktisi (ilk/son kare bununla birebir).
Maske kurali (Rose Ribbon on yuz): bordo (130,18,46) murekkep; sembol = isaret satirinin ustu, isaretler = isim satirinin ustu.
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image
from scipy import ndimage

SAHNE, GEO, BASKI, KAPAK, OUT = sys.argv[1:6]
V, FPS = 1080, 30
DPI, FW, FH = 300, 2700, 1050
D_IN = 3.35
FACE_ON = FW / 2 - D_IN * math.pi / 4 * DPI
MUREKKEP = np.array([130, 18, 46], np.float32)
rng = np.random.default_rng(7)

# ---------- baski uzayinda maskeler ----------
P = np.asarray(Image.open(BASKI).convert("RGB")).astype(np.float32)
uzak = np.abs(P - MUREKKEP).sum(-1)
m = uzak < 90
m[:, FW // 2:] = False                                   # yalniz on yuz yarisi
lab, n = ndimage.label(m)
nesne = ndimage.find_objects(lab)
boy = ndimage.sum(m, lab, range(1, n + 1))
buyuk = [(i + 1, o) for i, (o, s) in enumerate(zip(nesne, boy)) if s > 150]
# satirlar: en alttaki kalabalik satir isimler; onun ustundeki satir isaretler; daha ustu sembol
en_alt = max(o[0].start for _, o in buyuk)
isim_ust = min(o[0].start for _, o in buyuk if en_alt - o[0].start < 15)
aday = [(i, o) for i, o in buyuk if o[0].stop <= isim_ust - 5 and o[0].start > isim_ust - 140]
isaret_ust = min(o[0].start for _, o in aday)
# sembol: isaret satirinin ustundeki BUYUK parcalar (cicek tomurcuklari kucuk ve renkleri sembole yakin)
sembol = [(i, o) for i, o in buyuk if o[0].stop <= isaret_ust - 5 and boy[i - 1] > 1000]
sy0 = min(o[0].start for _, o in sembol); sy1 = max(o[0].stop for _, o in sembol)
sx0, sx1 = min(o[1].start for _, o in sembol) - 60, max(o[1].stop for _, o in sembol) + 60
# kucuk kopuk sembol parcalari (cizgi uclari): sembol kutusunda ve renk sembolle ayni (cicek koyu kirmizisi degil)
ana_renk = np.median(P[np.isin(lab, [i for i, _ in sembol])], 0)
for i, o in enumerate(nesne, 1):
    if (i, o) in sembol or o is None:
        continue
    if o[0].start >= sy0 - 5 and o[0].stop <= sy1 + 5 and o[1].start >= sx0 + 50 and o[1].stop <= sx1 - 50:
        if np.abs(np.median(P[lab == i], 0) - ana_renk).sum() < 25:
            sembol.append((i, o))
# isaretler: isim satirinin hemen ustu, yuz ortasina yakin (+-340 px) ve sembolle ayni murekkep rengi
# (18 Eki duzeltme: dar sembollerde, ornegin Aries-Capricorn, isaretler sembolun x araligi disinda kaliyordu)
isaret = [(i, o) for i, o in aday
          if abs((o[1].start + o[1].stop) / 2 - FACE_ON) <= 340 and np.abs(np.median(P[lab == i], 0) - ana_renk).sum() < 40]
print("isim satiri y", isim_ust, "isaret ust", isaret_ust, "sembol parca", len(sembol), "isaret parca", len(isaret))
if not isaret or not sembol:
    sys.exit(f"HATA: isaret ({len(isaret)}) veya sembol ({len(sembol)}) bulunamadi")
if os.environ.get("SADECE_TESPIT"):
    sys.exit(0)
HERO = np.isin(lab, [i for i, _ in sembol])
ISARET = np.isin(lab, [i for i, _ in isaret])
# yumusak (kenar yumusatmali) maske: koyuluk orani, sembol cevresiyle sinirli
koyu = np.clip(1 - uzak / 400.0, 0, 1)
HERO_S = koyu * ndimage.binary_dilation(HERO, iterations=3)
ISARET_S = koyu * ndimage.binary_dilation(ISARET, iterations=3)
SIL_M = ndimage.gaussian_filter(ndimage.binary_dilation(HERO, iterations=14).astype(np.float32), 1.0)   # tam silme: kenar pikselleri dahil
P_BOS = P * (1 - SIL_M[..., None]) + 255 * SIL_M[..., None]

# ---------- sahneye giydirme (kapak_canva.py ile ayni geometri) ----------
geo = json.load(open(GEO))["sol"]
sahne = np.asarray(Image.open(SAHNE).convert("RGB")).astype(np.float32)
xl, xr, yt, yb, et, eb = geo
xc, R = (xl + xr) / 2, (xr - xl) / 2
pxin = R / (D_IN / 2); H = yb - yt; H_in = H / pxin; marj_in = (H_in - FH / DPI) / 2
y0, y1 = max(0, int(yt - 4)), min(sahne.shape[0], int(yb + eb + 6))
x0, x1 = max(0, int(math.floor(xl)) - 5), min(sahne.shape[1], int(math.ceil(xr)) + 5)
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
u = (xx + 0.5 - xc) / R
ic = np.abs(u) < 0.995
th = np.arcsin(np.clip(u, -1, 1)); c = np.cos(th)
t = (yy - yt - et * c) / (H + (eb - et) * c)
fy = (t * H_in - marj_in) * DPI
fx = FACE_ON + th * (D_IN / 2) * DPI
icerde = ic & (fy >= 0) & (fy <= FH - 1) & (fx >= 0) & (fx <= FW - 1)
kenar = np.clip((0.995 - np.abs(u)) * R / 1.5, 0, 1) * icerde


def ornekle(a):
    return ndimage.map_coordinates(a, [fy, fx], order=1, mode="constant", cval=0) * kenar


def giydir(baski):
    orn = np.stack([ndimage.map_coordinates(baski[..., ch], [fy, fx], order=1, mode="nearest") for ch in range(3)], -1)
    bolge = sahne[y0:y1, x0:x1].copy()
    L = bolge.mean(-1)
    sonuc = bolge * orn / 255.0
    taban = ndimage.gaussian_filter(L, 18)
    parla = np.clip(L - taban, 0, None)[..., None] * 2.2
    koyu_ = 1 - orn.mean(-1, keepdims=True) / 255.0
    sonuc = np.clip(sonuc + parla * koyu_ + np.clip(L - 235, 0, None)[..., None] * 1.5 * koyu_, 0, 255)
    k = kenar[..., None]
    return bolge * (1 - k) + sonuc * k


KAP = np.asarray(Image.open(KAPAK).convert("RGB")).astype(np.float32)
BOS = KAP.copy(); BOS[y0:y1, x0:x1] = giydir(P_BOS)
HM = np.zeros(KAP.shape[:2], np.float32); HM[y0:y1, x0:x1] = ornekle(HERO_S)
IM = np.zeros(KAP.shape[:2], np.float32); IM[y0:y1, x0:x1] = ornekle(ISARET_S)
k1080 = lambda a: cv2.resize(a, (V, V), interpolation=cv2.INTER_AREA)
KAPAK_V, BOS_V, HM_V, IM_V = k1080(KAP), k1080(BOS), k1080(HM), k1080(IM)
RENK = MUREKKEP * 0.85 + 255 * 0.15
if os.environ.get("HATA_AYIKLA"):
    Image.fromarray(np.clip(BOS_V, 0, 255).astype(np.uint8)).save("hata_bos.png")
    Image.fromarray((np.clip(HM_V, 0, 1) * 255).astype(np.uint8)).save("hata_hm.png")

frames = []
def kare(f): frames.append(np.clip(f, 0, 255).astype(np.uint8))
T = lambda s: int(round(s * FPS))
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)

for _ in range(T(0.2)): kare(KAPAK_V)


def pts(mm, n_):
    ys, xs = np.where(mm > 0.35); i = rng.choice(len(xs), n_, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((n_, 2)).astype(np.float32) - 0.5


# once ozgun sembol tamamen silinir (Serdar 17 Eki: toz akisi baslarken sembol tamamen yok olmali)
for i in range(T(0.7)):
    ks = 1 - ease(i / (T(0.7) - 1))
    kare(BOS_V + (KAPAK_V - BOS_V) * ks)

N = 5200                                                 # toz miktari 2 kat (Serdar 17 Eki)
src, dst = pts(IM_V, N), pts(HM_V, N)
orta = np.median(dst[:, 0])
sol = src[:, 0] < np.median(src[:, 0])
src = np.concatenate([src[sol][np.argsort(src[sol][:, 1])], src[~sol][np.argsort(src[~sol][:, 1])]])
dsol, dsag = dst[dst[:, 0] < orta], dst[dst[:, 0] >= orta]
nl = int(sol.sum())
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.35
yay = -(12 + 22 * rng.random(N).astype(np.float32))
par = 0.5 + 0.5 * rng.random(N).astype(np.float32)
DUR = 3.8; n_ = T(DUR)
for i in range(n_):
    tt = i / (n_ - 1)
    uu = np.clip((tt - gec) / 0.6, 0, 1); ue = uu * uu * (3 - 2 * uu)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 1.2 * np.sin(np.pi * ue)
    gor = (uu > 0) & (uu < 1)
    acc = np.zeros((V, V), np.float32)
    x = np.clip(p[gor, 0].astype(int), 0, V - 1); y = np.clip(p[gor, 1].astype(int), 0, V - 1)
    np.add.at(acc, (y, x), par[gor])
    k = np.clip(cv2.GaussianBlur(acc, (0, 0), 0.5) * 0.9 + cv2.GaussianBlur(acc, (0, 0), 1.6) * 0.5, 0, 1)
    ks = ease((tt - 0.40) / 0.60)                        # sembol yalniz tozlar geldikce belirir
    base = BOS_V + (KAPAK_V - BOS_V) * ks
    kare(base + (RENK - base) * k[..., None] * 0.85)
for _ in range(T(1.6)): kare(KAPAK_V)

pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{V}x{V}", "-r", str(FPS),
                       "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
for f in frames: pr.stdin.write(f.tobytes())
pr.stdin.close(); pr.wait()
print(round(len(frames) / FPS, 1), "sn", round(os.path.getsize(OUT) / 1e6, 2), "MB", "kare", len(frames))
