"""Bizim Yilimiz minimal ilan videosu (Serdar 15 Eki): tek sabit gorsel = Etsy kapagi, kare 1080x1080, sessiz.
Posterdeki ozgun sembol sessizce silinir; soldaki ve sagdaki kucuk burc isaretlerinden tozlar akar ve ozgun sembolu
yeniden olusturur. Son kare = ilk kare (Etsy dongusu kesintisiz).
Kullanim: BY_ROOT=.. PAIR=.. python3 kod/by_video.py OUT.mp4  (Serdar onayi 15 Eki; 5,6 sn, ~1 MB)"""
import os, sys, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
ROOT = os.environ["BY_ROOT"]; sys.path.insert(0, f"{ROOT}/kod")
import by_poster as bp
import by_kapak as kp
OUT = sys.argv[1]
V, FPS = 1080, 30
K = V / kp.S
rng = np.random.default_rng(7)

# ---------- kapak: zemin + yazilar (2400'de cizilir, 1080'e kucultulur) ----------
s1 = 230
while kp.serif(s1).getlength(kp.BASLIK, features=["lnum"]) > kp.S * kp.GUVENLI: s1 -= 2
PY = kp.S - round(kp.POSTER_W * 1.25) - kp.ALT_BOSLUK
PX = (kp.S - kp.POSTER_W) // 2
bos = Image.open(kp.POSTER)                                   # gecici: kapagi posteri BOS kare ile ciz, posteri sonra yapistir
tmp = f"{os.path.dirname(OUT) or '.'}/_kapak_tmp.jpg"
kp.OUT = tmp; kp.main()
KAPAK = np.asarray(Image.open(tmp).convert("RGB").resize((V, V), Image.LANCZOS)).astype(np.float32)
os.remove(tmp)
x0, y0 = round(PX * K), round(PY * K)
pw, ph = round(kp.POSTER_W * K), round(kp.POSTER_W * 1.25 * K)

# ---------- poster: tam hali (dosyadan) ve ozgun sembolsuz hali (ayni motorla, sembol adimi atlanir) ----------
e = bp.els("4_Layers")
def layers_sembolsuz():
    bg = bp.bgimg("4_Layers")
    bg = bp.apply_ink(bg, bp.signs_mask(e["left"], e["right"]), "#6E3A24")
    w1, w2 = (bp.HEADING.split(" ", 1) + [""])[:2] if bp.HEADING != "Paper Anniversary" else ("Paper", "Anniversary")
    title = bp.union(bp.same_size_full(w1, "Paper", bp.fs("DMSerif"), -0.10, e["Paper"], "w", max_w=0.86 * bp.W),
                     bp.same_size_full(w2, "Anniversary", bp.fs("DMSerif"), -0.15, e["Anniversary"], "w", max_w=0.86 * bp.W))
    bg = bp.apply_papercut(bg, title, "#A34729", lift=5)
    names = bp.names_full(bp.N1, bp.N2, bp.fs("Montserrat", 600), 0.35, e["SERDAR"], e["LENA"])
    sub = bp.union(bp.same_size_full(bp.LINE, "YEAR ONE", bp.fs("Montserrat", 600), 0.65, e["YEAR ONE"], "w", max_w=0.32 * bp.W),
                   bp.text_full(bp.DATE, bp.fs("Montserrat", 600), 0.40, e["12 JUNE 2025"], "w"))
    return bp.apply_ink(bg, bp.union(names, sub), "#592319")
kucult = lambda im: np.asarray(im.convert("RGB").resize((pw, ph), Image.LANCZOS)).astype(np.float32)
P_TAM = KAPAK[y0:y0 + ph, x0:x0 + pw].copy()                  # kapaktaki poster pikselleri (ilk kare ile birebir)
HERO_M = cv2.resize(np.asarray(bp.hero_mask(e["hero"])).astype(np.float32) / 255, (pw, ph), interpolation=cv2.INTER_AREA)
# sembolsuz poster: yalniz sembol + golgesi bolgesi yeni cizimden alinir; isim/tarih vb. her zaman kapaktaki posterden (P_TAM)
BOLGE = cv2.GaussianBlur(cv2.dilate((HERO_M > 0.02).astype(np.uint8), np.ones((23, 23), np.uint8)).astype(np.float32), (0, 0), 4)[..., None]
P_BOS = P_TAM * (1 - BOLGE) + kucult(layers_sembolsuz()) * BOLGE
ISARET_M = cv2.resize(np.asarray(bp.signs_mask(e["left"], e["right"])).astype(np.float32) / 255, (pw, ph), interpolation=cv2.INTER_AREA)
TERRA = np.array([168, 74, 44], np.float32)

def ease(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
frames = []
def kare(p):
    f = KAPAK.copy(); f[y0:y0 + ph, x0:x0 + pw] = p
    frames.append(np.clip(f, 0, 255).astype(np.uint8))
T = lambda s: int(round(s * FPS))
def sembol(k): return P_BOS + (P_TAM - P_BOS) * k             # k=1 tam poster, k=0 sembolsuz

# 1) kapak
for _ in range(T(0.2)): kare(P_TAM)                           # hareket hemen baslar (Serdar 15 Eki)
# 2+3) ozgun sembol silinirken ayni anda iki kucuk isaretten tozlar cikar (Serdar 15 Eki), sembole akar ve onu yeniden olusturur
def pts(m, n_):
    ys, xs = np.where(m > 0.35); i = rng.choice(len(xs), n_, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((n_, 2)).astype(np.float32) - 0.5
N = 14000                                                     # toz miktari 2 kat (Serdar 15 Eki)
src, dst = pts(ISARET_M, N), pts(HERO_M, N)
sol = src[:, 0] < pw / 2
src = np.concatenate([src[sol][np.argsort(src[sol][:, 1])], src[~sol][np.argsort(src[~sol][:, 1])]])
dsol = dst[dst[:, 0] < np.median(dst[:, 0])]; dsag = dst[dst[:, 0] >= np.median(dst[:, 0])]
nl = int(sol.sum())
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])    # sol isaret -> sembolun sol yarisi
gec = rng.random(N).astype(np.float32) * 0.35
yay = -(40 + 60 * rng.random(N).astype(np.float32))           # yukari dogru hafif kavis
par = 0.5 + 0.5 * rng.random(N).astype(np.float32)
DUR = 3.8; n = T(DUR)
SIL = 0.9 / DUR                                               # silinme suresi (sn) -> t orani
for i in range(n):
    t = i / (n - 1)
    u = np.clip((t - gec) / 0.6, 0, 1); ue = u * u * (3 - 2 * u)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(t * 8 + np.arange(N) * 0.41) * 2.5 * np.sin(np.pi * ue)
    gor = (u > 0) & (u < 1)                                    # yola cikmis, henuz yerine oturmamis
    acc = np.zeros((ph, pw), np.float32)
    x = np.clip(p[gor, 0].astype(int), 0, pw - 1); y = np.clip(p[gor, 1].astype(int), 0, ph - 1)
    np.add.at(acc, (y, x), par[gor])
    k = np.clip(cv2.GaussianBlur(acc, (0, 0), 0.7) * 0.9 + cv2.GaussianBlur(acc, (0, 0), 3) * 1.2, 0, 1)
    ks = 1 - ease(t / SIL) if t < SIL else ease((t - 0.40) / 0.60)   # once silinir, sonra tozlar geldikce belirir
    base = sembol(ks)
    kare(base + (TERRA - base) * k[..., None] * 0.85)
# 4) kapak (son kare = ilk kare)
for _ in range(T(1.6)): kare(P_TAM)

pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{V}x{V}", "-r", str(FPS),
                       "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
for f in frames: pr.stdin.write(f.tobytes())
pr.stdin.close(); pr.wait()
print(bp.PAIR, round(len(frames) / FPS, 1), "sn", round(os.path.getsize(OUT) / 1e6, 1), "MB")
