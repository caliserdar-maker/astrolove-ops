#!/usr/bin/env python3
"""Orchard ilan videosu (Serdar 18.10, kesin akis + ilk/son kare kapak): sahne SABIT, 6 sn, 1080x1080, 30 fps, sessiz H.264.
Ilk kare ve son kare = onayli kapak dosyasi (birebir). 2. kareden toz baslar; ilk 0,3 sn icinde ozgun sembol ve mesaj
yumusakca kaybolur. Toz iki kucuk burc isaretinden akar, ozgun sembol ilk varislarla sifirdan yumusakca olusur;
mesaj soldan saga yazilir, imza sabit. Toz ve mesaj BITIS sn'de biter; sonra kapak sabit.
Kullanim: python3 -I video6b.py <katman_dizini> <kapak_jpg> <cikti_mp4> [bitis_sn]"""
import subprocess, sys, time
import numpy as np, cv2
from PIL import Image

D, KAPAK, OUT = sys.argv[1:4]
BITIS = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
V, FPS, SURE, SILME = 1080, 30, 6.0, 0.3
rng = np.random.default_rng(11)
t0 = time.time()


def oku(p):
    return cv2.resize(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), (V, V), interpolation=cv2.INTER_AREA)


KAP = np.clip(np.round(oku(KAPAK)), 0, 255)
F_ESKI, B_ESKI, BEY = oku(f'{D}/kb_full_baski_11oz.png'), oku(f'{D}/kb_basem_baski_11oz.png'), oku(f'{D}/k_beyaz.png')
# kapak esas: tam hal = kapak; bos hal = kapak + (sembolsuz/mesajsiz katman - tam katman) farki (fark yalniz sembol ve mesajda)
FULL = KAP
BASE = np.clip(KAP + (B_ESKI - F_ESKI), 0, 255)


def maske(ad, kat=1.4):
    return np.clip((1 - oku(f'{D}/k_mask_{ad}.png').mean(-1) / np.maximum(BEY.mean(-1), 1)) * kat, 0, 1)


MS, MG, MM = maske('nosym'), maske('noglif'), maske('nomes')
MM = cv2.dilate(MM, np.ones((3, 3), np.uint8))
XX = np.arange(V, dtype=np.float32)[None, :].repeat(V, 0)


def kapsam(m):
    ys, xs = np.where(m > 0.2)
    return xs.min(), xs.max()


mx0, mx1 = kapsam(MM)
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))


def yazim(x0, x1, p, yum=10):
    """soldan saga yazilma: p ilerlemesine gore x esiginin solu acik, yumusak kenar"""
    esik = x0 - yum + (x1 - x0 + 2 * yum) * p
    return np.clip((esik - XX) / yum, 0, 1)


def noktalar(m, N):
    ys, xs = np.where(m > 0.35)
    i = rng.choice(len(xs), N, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((N, 2)).astype(np.float32) - 0.5


N = 5200                                                  # toz 2 kat (Serdar 18.10)
src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
yay = -(8 + 16 * rng.random(N).astype(np.float32))
YESIL, ALTIN = np.array([22, 60, 36], np.float32), np.array([196, 150, 64], np.float32)
renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, YESIL)
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)

frames = []
nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
for i in range(nT):
    if i == 0 or i >= nB:
        frames.append(KAP)
        continue
    tt = i / (nB - 1)
    am = yazim(mx0, mx1, ease(tt)) * MM
    uu = np.clip((tt - gec) / 0.38, 0, 1)
    asym = ease((tt - 0.36) / 0.64) * MS                     # ilk varislarla sifirdan baslar, BITIS'te tam
    A = np.clip(am + asym, 0, 1)[..., None]
    f = BASE * (1 - A) + FULL * A
    if i <= nS:                                              # ilk 0,3 sn: kapaktaki sembol ve mesaj yumusakca kaybolur
        e = ease(i / nS)
        f = KAP * (1 - e) + f * e
    ue = uu * uu * (3 - 2 * uu)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
    gor = (uu > 0) & (uu < 1)
    xi, yi = p[gor, 0].astype(int), p[gor, 1].astype(int)
    ok = (xi >= 0) & (xi < V) & (yi >= 0) & (yi < V)
    a_ = (par[gor] * np.sin(np.pi * uu[gor]))[ok]
    al = np.zeros((V, V), np.float32)
    kat = np.zeros((V, V, 3), np.float32)
    np.add.at(al, (yi[ok], xi[ok]), a_)
    for c in range(3):
        np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
    al = cv2.GaussianBlur(al, (0, 0), 0.9) * 2.0
    kat = cv2.GaussianBlur(kat, (0, 0), 0.9) * 2.0
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None]
    frames.append(f * (1 - a3) + rk * a3)
    if i % 15 == 0:
        g = time.time() - t0
        print(f'  kare {i}/{nB} %{100 * i // nB} (gecen {g:.0f}s, kalan ~{g / i * (nB - i):.0f}s)', flush=True)
print(f'{len(frames)} kare ({len(frames) / FPS:.2f} sn), toz/yazi bitis {BITIS} sn, uretim {time.time() - t0:.0f}s', flush=True)
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{V}x{V}',
                      '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                      '-preset', 'slow', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
for i, f in enumerate(frames, 1):
    p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    if i % 50 == 0 or i == len(frames):
        print(f'  kodlama {i}/{len(frames)} %{100 * i // len(frames)} (gecen {time.time() - t0:.0f}s)', flush=True)
p.stdin.close()
p.wait()
for ad, sn in (('0.0', 0), ('0.15', 0.15), ('1.4', 1.4), ('2.8', 2.8), ('son', SURE - 1 / FPS)):
    Image.fromarray(np.clip(frames[min(len(frames) - 1, int(sn * FPS))], 0, 255).astype(np.uint8)).save(
        OUT.replace('.mp4', f'_{ad}.jpg'), quality=90)
print('tamam', OUT)
