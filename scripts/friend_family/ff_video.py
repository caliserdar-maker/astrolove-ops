"""Friend & Family Gifts ilan videosu (Serdar 25 Eki: diger kategorilerle ayni, tek sahne, burclardan toz ozgun sembole; 25 Eki duzeltme: toz KISI ISIMLERINDEN cikar).
by_video.py (bizim-yilimiz-v3 b90f334) mantigi: 0,2 sn kapak; 3,8 sn sembol silinir + EMMA/OLIVIA isimlerinden toz akar ve
sembolu yeniden olusturur; 1,6 sn kapak (son kare = ilk kare). Kapak 4:3 -> 1440x1080, 30 fps, sessiz.
Kullanim: python3 ff_video.py KAPAK.png OUT.mp4"""
import sys, subprocess
import numpy as np, cv2
from PIL import Image
KAPAK_YOL, OUT = sys.argv[1], sys.argv[2]
VW, VH, FPS = 1440, 1080, 30
rng = np.random.default_rng(7)
A = np.asarray(Image.open(KAPAK_YOL).convert("RGB")).astype(np.float32)
dk = ((A.mean(2) < 140) & (A[:, :, 1] > A[:, :, 0])).astype(np.uint8)
kagit = np.zeros_like(dk); kagit[162:1040, 378:1070] = 1; dk *= kagit
n, lab, st, cen = cv2.connectedComponentsWithStats(dk, 8)
SEM = np.zeros_like(dk); BURC = np.zeros_like(dk)
for i in range(1, n):
    x, y, w, h, ar = st[i]; cx, cy = cen[i]
    if ar > 300 and 500 < cx < 900 and 240 < cy < 740: SEM[lab == i] = 1
    if 765 < cy < 815 and 480 < cx < 980 and h < 50: BURC[lab == i] = 1   # kisi isimleri
assert SEM.sum() > 20000 and BURC.sum() > 1000, (SEM.sum(), BURC.sum())
# sembolsuz kagit: golge dahil genis bolge inpaint + kagit dokusu (bos kagit seridinden yuksek frekans)
# kabartma golgesi: sembol cevresinde kagittan koyu pikseller de bolgeye girer (ilk ornekte iz kaldi)
ref = np.median(A[430:720, 392:500].reshape(-1, 3), 0)
golge = ((ref.mean() - A.mean(2)) > 5).astype(np.uint8) & cv2.dilate(SEM, np.ones((61, 61), np.uint8))
bolge = cv2.dilate(cv2.morphologyEx(SEM | golge, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((13, 13), np.uint8))
duz = cv2.inpaint(np.clip(A, 0, 255).astype(np.uint8), bolge, 9, cv2.INPAINT_TELEA).astype(np.float32)
duz = cv2.GaussianBlur(duz, (0, 0), 6) * bolge[..., None] + duz * (1 - bolge[..., None])
serit = A[430:720, 392:500]                                   # bos kagit (sol kenar, yapraklar arasi)
hf = serit - cv2.GaussianBlur(serit, (0, 0), 4)
th, tw = hf.shape[:2]; doku = np.tile(hf, (A.shape[0] // th + 2, A.shape[1] // tw + 2, 1))[:A.shape[0], :A.shape[1]]
BOS = duz + doku * bolge[..., None]
yum = cv2.GaussianBlur(bolge.astype(np.float32), (0, 0), 3)[..., None]
BOS = A * (1 - yum) + BOS * yum
sx, sy = VW / A.shape[1], VH / A.shape[0]
kuc = lambda im: cv2.resize(im, (VW, VH), interpolation=cv2.INTER_AREA)
TAM, BOS = kuc(A), kuc(BOS)
SEM_M = kuc(SEM.astype(np.float32)); BURC_M = kuc(BURC.astype(np.float32))
YESIL = np.array([30, 74, 48], np.float32)
def ease(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
frames = []
T = lambda s: int(round(s * FPS))
def kare(f): frames.append(np.clip(f, 0, 255).astype(np.uint8))
for _ in range(T(0.2)): kare(TAM)
def pts(m, k):
    ys, xs = np.where(m > 0.35); i = rng.choice(len(xs), k, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((k, 2)).astype(np.float32) - 0.5
N = 56000                                                     # Serdar 25 Eki: toz 2 kat, sonra 2 kat daha
src, dst = pts(BURC_M, N), pts(SEM_M, N)
sol = src[:, 0] < VW / 2
src = np.concatenate([src[sol][np.argsort(src[sol][:, 1])], src[~sol][np.argsort(src[~sol][:, 1])]])
med = np.median(dst[:, 0]); dsol = dst[dst[:, 0] < med]; dsag = dst[dst[:, 0] >= med]; nl = int(sol.sum())
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])   # sol isim -> sol yari, sag isim -> sag yari
gec = rng.random(N).astype(np.float32) * 0.35
yay = -(40 + 60 * rng.random(N).astype(np.float32))
par = 0.5 + 0.5 * rng.random(N).astype(np.float32)
DUR = 11.2; nk = T(DUR); SIL = 0.9 / DUR                       # Serdar 25 Eki: hareket %50 yavas (hiz yarim, sure 2 kat)
for i in range(nk):
    t = i / (nk - 1)
    u = np.clip((t - gec) / 0.6, 0, 1); ue = u * u * (3 - 2 * u)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(t * 8 + np.arange(N) * 0.41) * 2.5 * np.sin(np.pi * ue)
    gor = (u > 0) & (u < 1)
    acc = np.zeros((VH, VW), np.float32)
    x = np.clip(p[gor, 0].astype(int), 0, VW - 1); y = np.clip(p[gor, 1].astype(int), 0, VH - 1)
    np.add.at(acc, (y, x), par[gor])
    k = np.clip(cv2.GaussianBlur(acc, (0, 0), 0.7) * 0.9 + cv2.GaussianBlur(acc, (0, 0), 3) * 1.2, 0, 1)
    gel = float((u >= 1).mean())                               # yerine oturan toz orani: sembol tozlar doldukca belirginlesir
    ks = (1 - ease(t / SIL)) if t < SIL else ease(gel)
    base = BOS + (TAM - BOS) * ks
    kare(base + (YESIL - base) * k[..., None] * 0.85)
for _ in range(T(1.6)): kare(TAM)
pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
                       "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
for f in frames: pr.stdin.write(f.tobytes())
pr.stdin.close(); pr.wait()
Image.fromarray(np.clip(BOS, 0, 255).astype(np.uint8)).save(OUT.rsplit(".", 1)[0] + "_sembolsuz.png")
print(len(frames), "kare", round(len(frames) / FPS, 1), "sn")
