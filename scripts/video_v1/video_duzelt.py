#!/usr/bin/env python3
"""video-v1: referans ilan videosu (AstroLove_Centered_Immediate_12s.mp4) duzeltmesi (Mo karari 25 Eyl 2026).
Sign order alani yok: Libra-solda durumlar (ALEXANDER, MAX) kaldirilir, o bolumlerde poster sabit kalir.
Iki durum: E = EMILY & JAMES (referans kare, aynen), N = ISABELLA & NOAH (referans ISABELLA karesi; sembol+isim bandi
kisisel-v1 onayli isim koduyla uretilmis 2400x3000 posterden, ECC ile olculen afin + kanal bazli ton uydurmasiyla).
Gecisler referanstaki kare pencereleri ve olculen agirliklarla. Sure/cozunurluk/fps/codec referansla ayni.
Kullanim: video_duzelt.py REF.mp4 P_leo.png P_noah.png CIKTI.mp4  (P_*: kis_poster.py ciktisi)"""
import json, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

ref, p_old, p_new, out = sys.argv[1:5]
t0 = time.time()
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
n = len(A)
# referans durumlari (olculdu): E 137-171 | A 182-216 | I 47-81 | M 92-126; gecis pencereleri 11 kare
F_E, F_I = 150, 60
WIN = [(36, 47, 'A', 'I'), (126, 137, 'M', 'E'), (216, 227, 'A', 'I'), (306, 317, 'M', 'E')]
REFST = {'A': 20, 'I': 60, 'M': 105, 'E': 150}
YENI = {36: ('E', 'N'), 126: ('N', 'E'), 216: ('E', 'N'), 306: ('N', 'E')}
OPEN = (151, 171, 927, 1177)
BAND = (785, 975)            # sembol (811-) + isim satiri (-939) kare y; tagline 1032den baslar
g = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)

def hizala(P, F):
    W = np.array([[0.335, 0, 138], [0, 0.335, 172]], np.float32)
    Pw = cv2.warpAffine(cv2.GaussianBlur(g(P), (0, 0), 1.2), W, (1080, 1350), flags=cv2.INTER_AREA)
    m = np.zeros((1350, 1080), np.uint8); m[200:1150, 170:910] = 1
    cc, D = cv2.findTransformECC(g(F), Pw, np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE,
                                 (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-7), m, 5)
    M = (np.linalg.inv(np.vstack([D, [0, 0, 1]])) @ np.vstack([W, [0, 0, 1]]))[:2]
    return M, float(cc)

def yerlestir(P, M):
    return cv2.warpAffine(P, M, (1080, 1350), flags=cv2.INTER_AREA)

FI = A[F_I].astype(np.float32)
Po = np.asarray(Image.open(p_old).convert('RGB')).astype(np.float32)
Pn = np.asarray(Image.open(p_new).convert('RGB')).astype(np.float32)
M, cc = hizala(Po, FI)
Wo, Wn = yerlestir(Po, M), yerlestir(Pn, M)
reg = np.zeros((1350, 1080), bool); reg[OPEN[1]:OPEN[3], OPEN[0]:OPEN[2]] = True
fit = [np.polyfit(Wo[..., c][reg], FI[..., c][reg], 1) for c in range(3)]
tf = lambda X: np.stack([np.polyval(fit[c], X[..., c]) for c in range(3)], 2)
To, Tn = tf(Wo), tf(Wn)
# bant maskesi: poster ici, sembol+isim satiri; kenarlar 6 px yumusak
a = np.zeros((1350, 1080), np.float32); a[BAND[0]:BAND[1], OPEN[0] + 8:OPEN[2] - 8] = 1
a = cv2.GaussianBlur(a, (0, 0), 3)[..., None]
N = FI * (1 - a) + Tn * a
d_old = np.abs(To - FI).mean(2)
meta = {'ecc': round(cc, 5), 'M': np.round(M, 5).tolist(), 'ton': [np.round(f, 4).tolist() for f in fit],
        'eski_bant_fark_ort': round(float(d_old[BAND[0]:BAND[1], OPEN[0]:OPEN[2]].mean()), 3),
        'zemin_fark_ort_bant_kenari': round(float(np.abs(Tn - FI).mean(2)[BAND[0]:BAND[0] + 6, OPEN[0]:OPEN[2]].mean()), 3)}
ST = {'E': A[F_E].astype(np.float32), 'N': N}
# gecis agirliklari: referans penceresinde X->Y izdusumu (video.py yontemi), bant: tagline+isim
band = lambda X: X[930:1010, 151:927].astype(np.float32)
agirlik = {}
for a0, a1, x, y in WIN:
    Sx, Sy = band(A[REFST[x]]), band(A[REFST[y]]); v = Sy - Sx
    agirlik[a0] = [float(np.clip((v * (band(A[i]) - Sx)).sum() / (v * v).sum(), 0, 1)) for i in range(a0, a1 + 1)]
meta['agirlik'] = {k: [round(w, 3) for w in v] for k, v in agirlik.items()}
plan = []
cur = 'E'
for i in range(n):
    st = None
    for a0, (x, y) in YENI.items():
        if a0 <= i <= a0 + 11:
            w = agirlik[a0][i - a0]; plan.append((x, y, w)); st = 1; cur = y if i == a0 + 11 else cur
    if st is None:
        plan.append((cur, cur, 0.0))
# kare 0 = E sabit karesi (Mo, 25 Eyl iterasyon 3): dongu basinda sicrama yok
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', '30', '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', 'keyint=360:min-keyint=360:scenecut=0', '-pix_fmt', 'yuv420p',
       '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
t1 = time.time()
for i, (x, y, w) in enumerate(plan):
    fr = ST[x] * (1 - w) + ST[y] * w
    pr.stdin.write(np.clip(np.rint(fr), 0, 255).astype(np.uint8).tobytes())
    if (i + 1) % 90 == 0:
        el = time.time() - t1; print(f'kare {i+1}/{n} %{100*(i+1)/n:.0f} gecen {el:.0f}s kalan ~{el/(i+1)*(n-i-1):.0f}s', flush=True)
pr.stdin.close(); assert pr.wait() == 0
meta['plan'] = [[x, y, round(w, 3)] for x, y, w in plan]
Image.fromarray(np.clip(np.rint(N), 0, 255).astype(np.uint8)).save(out.replace('.mp4', '_N.png'))
json.dump(meta, open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s ecc={meta["ecc"]} eski_bant_fark={meta["eski_bant_fark_ort"]} kenar={meta["zemin_fark_ort_bant_kenari"]}', flush=True)
