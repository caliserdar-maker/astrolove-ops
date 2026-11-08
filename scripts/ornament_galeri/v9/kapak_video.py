# kapak_video.py (7 Kas) - G2, Serdar: "ilk kare kapak; burclardan cikan altin tozlarla halka ve ozgun sembolun kademeli olusumu"
# AI (Kling, sabit kamera): yalniz arka plan isigi ve bokeh. Urun pikselleri yalniz onayli kapak gorselinden (SET_kapak.jpg, set_yerlestir.py).
# Akis: 0-0,7 s kapak | 0,7-1,8 halka, sembol, isim, tarih toza donusup dagilir; iki burc kalir | 1,8-2,4 burclar parlar |
#       2,4-4,4 burclardan cikan toz halkayi alttan uca cizer | 3,7-6,2 sembol: Libra kismi Libra'dan, Cancer kismi Cancer'dan |
#       6,0-7,0 isimler, tarih | 7,0-9,0 kapak (son 0,4 s birebir kapak)
# kullanim: python kapak_video.py kling.mp4 cikis.mp4
import sys, json, subprocess, os
import numpy as np, cv2

KLING, CIKIS = sys.argv[1], sys.argv[2]
VW, VH, FPS, SURE = 1440, 1080, 30, 9.0
E = os.environ   # 8 Kas v9: yollar ortamdan (cift basina)
C = cv2.imread(E["V_SET"])                                               # cift kapagi (yazisiz, SET_kapak.jpg)
O = json.load(open(E["V_OLC"]))                                          # kapak sahnesi olcumu
J = json.load(open(E["V_JSON"]))                                         # SET_kapak.json
k3 = VW / 3000.0
Cv = cv2.resize(C, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)
hx, hy, hr = [v * k3 for v in J["delik_bizim"]]
R = J["R"] * k3
cx, cy = hx, hy + 0.699 * R
yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
X, Y = (xx - cx) / R, (yy - cy) / R
dr = np.hypot(X, Y)
yuz = np.clip((0.985 * R - dr * R) / 2.0, 0, 1)
b_, g_, r_ = Cv[..., 0], Cv[..., 1], Cv[..., 2]
ipbol = ((np.abs(xx - hx) < 0.9 * hr) & (yy < hy)) | (np.hypot(xx - hx, yy - hy) < 1.02 * hr) | ((np.abs(xx - hx) < 2.6 * hr) & (yy < hy - 1.6 * hr))   # yalniz ip sutunu ve delik
altin = ((g_ - b_) > 35) & (r_ > 100) & (yuz > 0.9) & ~ipbol

# parcalar (kapak olcumu, R biriminde)
burc_L = altin & (X > -0.47) & (X < -0.20) & (Y > 0.24) & (Y < 0.46)       # Cancer
burc_R = altin & (X > 0.18) & (X < 0.47) & (Y > 0.24) & (Y < 0.46)          # Libra
burclar = burc_L | burc_R
isim = altin & ~burclar & (Y > 0.46) & (Y < 0.60) & (np.abs(X) < 0.52)
tarih = altin & ~burclar & (Y >= 0.60) & (Y < 0.76) & (np.abs(X) < 0.32)
halka = altin & ~burclar & ~isim & ~tarih & (dr > 0.60)
sembol = altin & ~burclar & ~isim & ~tarih & ~halka
sem_L = sembol & (Y > -0.17)                                                 # Cancer kivrimlari
sem_R = sembol & (Y <= -0.17)                                                # Libra ust kismi
EL = np.array([cx - 0.335 * R, cy + 0.35 * R]); ER = np.array([cx + 0.33 * R, cy + 0.35 * R])

rng = np.random.default_rng(11)
jit = cv2.GaussianBlur(rng.random((VH, VW)).astype(np.float32), (0, 0), 3) * 0.6
ang = np.degrees(np.abs(np.arctan2(X, -Y)))                                  # 0 ust, 180 alt
# olusum zamani (giris)
Tin = np.full((VH, VW), 99.0, np.float32)
Tin[halka] = 2.4 + 1.9 * np.clip((125 - ang[halka]) / 125, 0, 1)
Tin[sem_L] = 3.7 + 2.2 * np.clip((Y[sem_L] + 0.17) / 0.33 * -1 + 1, 0, 1) * 0.5 + 1.1 * np.hypot(X[sem_L], Y[sem_L] - 0.0) / 0.4 * 0.5 + 0.4 * jit[sem_L]
Tin[sem_R] = 4.3 + 1.6 * np.clip((-0.17 - Y[sem_R]) / 0.32, 0, 1) + 0.4 * jit[sem_R]
Tin[isim] = 6.0 + 0.6 * np.clip((X[isim] + 0.5) / 1.0, 0, 1)
Tin[tarih] = 6.4 + 0.5 * np.clip((X[tarih] + 0.3) / 0.6, 0, 1)
Tin[burclar] = 0.0
# dagilma zamani (cikis), burclar haric
Tout = np.full((VH, VW), 99.0, np.float32)
dag = altin & ~burclar
Tout[dag] = 0.75 + 0.8 * np.clip((0.95 - dr[dag]) / 0.95, 0, 1) + 0.25 * jit[dag]


def yay(T):                                                                    # kenar isiltisi de ayni zamanda
    T = cv2.erode(T, np.ones((11, 11), np.uint8))
    T[~(cv2.dilate(altin.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0)] = 99.0
    return T


Tin, Tout = yay(Tin), yay(Tout)
gbol = Tin < 50
zem = cv2.inpaint(np.clip(Cv, 0, 255).astype(np.uint8), (gbol & ~(cv2.dilate(burclar.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0)).astype(np.uint8),
                  3, cv2.INPAINT_TELEA).astype(np.float32)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# giris parcaciklari: hedefe burctan akar (halka sol yarisi ve Cancer kismi Cancer'dan, sag yari ve Libra kismi Libra'dan)
hedefler = []
for m, n in ((halka, 900), (sem_L, 900), (sem_R, 700)):
    p = np.argwhere(m); p = p[rng.choice(len(p), size=min(n, len(p)), replace=False)]; hedefler.append(p)
hed = np.vstack(hedefler)
P_ty, P_tx = hed[:, 0].astype(np.float32), hed[:, 1].astype(np.float32)
P_t = Tin[hed[:, 0], hed[:, 1]]
solmu = np.concatenate([P_tx[:len(hedefler[0])] < cx, np.ones(len(hedefler[1]), bool), np.zeros(len(hedefler[2]), bool)])
P_sx = np.where(solmu, EL[0], ER[0]) + rng.normal(0, 0.03 * R, len(hed))
P_sy = np.where(solmu, EL[1], ER[1]) + rng.normal(0, 0.03 * R, len(hed))
P_d = np.where(np.arange(len(hed)) < len(hedefler[0]), rng.uniform(0.7, 1.1, len(hed)), rng.uniform(0.9, 1.4, len(hed)))
P_dis = rng.uniform(0.15, 0.35, len(hed)) * R                                  # disa kivrilma (akis yayi)
P_br = rng.uniform(0.55, 1.0, len(hed))
# dagilma parcaciklari: cizgiden kalkar, yukari ve disa savrulur
cik = np.argwhere(dag); cik = cik[rng.choice(len(cik), size=min(1600, len(cik)), replace=False)]
Q_y, Q_x = cik[:, 0].astype(np.float32), cik[:, 1].astype(np.float32)
Q_t = Tout[cik[:, 0], cik[:, 1]]
_v = np.stack([Q_x - cx, Q_y - cy], 1); _v /= np.linalg.norm(_v, axis=1, keepdims=True) + 1e-6
Q_vx = _v[:, 0] * rng.uniform(40, 140, len(cik)) + rng.normal(0, 25, len(cik))
Q_vy = _v[:, 1] * rng.uniform(40, 140, len(cik)) - rng.uniform(40, 120, len(cik))
Q_br = rng.uniform(0.5, 1.0, len(cik))


def nokta(katman, px, py, br):
    ix, iy = np.round(px).astype(int), np.round(py).astype(int)
    ok = (ix >= 0) & (ix < VW) & (iy >= 0) & (iy < VH)
    np.add.at(katman, (iy[ok], ix[ok]), br[ok])


def giris_konum(t):
    u = (t - (P_t - P_d)) / P_d
    act = (u > 0) & (u < 1.04)
    e = np.clip(u[act], 0, 1); e = e * e * (3 - 2 * e)
    sx, sy, tx, ty = P_sx[act], P_sy[act], P_tx[act], P_ty[act]
    # disa dogru kivrilan egri (kontrol noktasi hedefin merkezden disari yonunde)
    nx, ny = tx - cx, ty - cy; nn = np.hypot(nx, ny) + 1e-6
    kx, ky = (sx + tx) / 2 + nx / nn * P_dis[act], (sy + ty) / 2 + ny / nn * P_dis[act]
    px = (1 - e) ** 2 * sx + 2 * (1 - e) * e * kx + e * e * tx
    py = (1 - e) ** 2 * sy + 2 * (1 - e) * e * ky + e * e * ty
    br = P_br[act] * np.where(u[act] > 1, np.clip(1 - (u[act] - 1) / 0.04, 0, 1), 1.0)
    return px, py, br


p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", KLING],
                   capture_output=True, text=True, check=True)
s0 = json.loads(p.stdout)["streams"][0]; KW, KH = s0["width"], s0["height"]
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", KLING, "-vf", f"fps={FPS}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
hs = int(round(O["H"] * (3000 / O["W"]))); pad = (2250 - hs) // 2
tmp = CIKIS + ".tmp.mp4"
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
ipb = cv2.GaussianBlur(ipbol.astype(np.float32), (0, 0), 6)
glow_b = cv2.GaussianBlur(burclar.astype(np.float32), (0, 0), 6)
NF = int(SURE * FPS)
# kapak yazisi duzeni (kapak_yazi.py katmanlari): %8 yakinlastirma, ip dugum ustunde kaybolur, yazi ilk ve son karede
KT = np.load(E["V_KATMAN"])
def vk(x, kanal=False):
    x = np.asarray(x, np.float32)
    return cv2.resize(x, (VW, VH), interpolation=cv2.INTER_AREA)
SIL, ARKA, TK, TG = vk(KT["sil"]), vk(KT["arka"]), vk(KT["k"]), vk(KT["g"])
ARKA = ARKA[..., ::-1].copy() if ARKA.ndim == 3 else ARKA                         # katman RGB, video BGR
KREM_, GOLGE_ = KT["krem"][::-1].astype(np.float32), KT["golge"][::-1].astype(np.float32)
RENK_ = vk(KT["renk"])[..., ::-1].copy()                                     # altin yazi rengi (kapakla ayni)
YAK = float(KT["yakin"])
SON_KARE = cv2.imread(E["V_SON"]); SON_KARE = cv2.resize(SON_KARE, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)
def yakinlas(a):
    b = cv2.resize(a, (round(VW * YAK), round(VH * YAK)), interpolation=cv2.INTER_LINEAR)
    x0 = (b.shape[1] - VW) // 2
    return b[:VH, x0:x0 + VW]
ALTIN = np.array([40, 168, 240], np.float32) / 255.0                         # BGR, sicak altin (R 240, G 168, B 40)
kay_max = 0.0; ref = None; son_k = None
for i in range(NF):
    t = i / FPS
    raw = dec.stdout.read(KW * KH * 3)
    if len(raw) == KW * KH * 3:
        f = np.frombuffer(raw, np.uint8).reshape(KH, KW, 3)
        g = cv2.resize(f, (3000, hs), interpolation=cv2.INTER_AREA)
        g = cv2.copyMakeBorder(g, pad, 2250 - hs - pad, 0, 0, cv2.BORDER_REFLECT)
        son_k = cv2.resize(g, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)
        gg = cv2.cvtColor(son_k.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) * (dr < 1.1)
        if ref is None:
            ref = gg
        elif i % 15 == 0:
            (dx, dy), _ = cv2.phaseCorrelate(ref, gg); kay_max = max(kay_max, float(np.hypot(dx, dy)))
    f = son_k
    # disk yuzu: baski zemini + altin (cikis ve giris zamanina gore)
    a_out = 1 - ss(Tout - 0.08, Tout + 0.25, t)
    a_in = ss(Tin - 0.12, Tin + 0.22, t)
    a_g = np.where(t < 2.0, a_out, a_in)
    a_g[burclar] = 1.0
    yuzr = zem + (Cv - zem) * a_g[..., None]
    out = f * (1 - yuz[..., None]) + yuzr * yuz[..., None]
    out = out * (1 - ipb[..., None]) + Cv * ipb[..., None]
    # burc parlamasi (1,6-2,6 s) ve akis boyunca hafif nabiz
    nab = 0.55 * np.exp(-((t - 2.1) / 0.35) ** 2) + 0.18 * ss(2.3, 2.6, t) * (1 - ss(6.0, 6.6, t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.6 * t))
    out += (glow_b * nab)[..., None] * np.array([90, 190, 255], np.float32)
    # varis / kalkis parlamasi
    par = (np.exp(-((t - Tin) / 0.16) ** 2) * (t >= 2.0) + np.exp(-((t - Tout) / 0.16) ** 2) * (t < 2.0)) * altin * 0.30
    out = out + (255 - np.clip(out, 0, 255)) * (np.clip(par, 0, 1)[..., None] * ALTIN)   # v3: altin ekran karisimi (beyaza donmez)
    # parcaciklar (iz ile)
    kat = np.zeros((VH, VW), np.float32)
    for gec, ag in ((0.0, 1.0), (0.025, 0.55), (0.05, 0.3), (0.075, 0.15)):
        px, py, br = giris_konum(t - gec); nokta(kat, px, py, br * ag)
    u = t - Q_t; act = (u > 0) & (u < 0.9)
    nokta(kat, Q_x[act] + Q_vx[act] * u[act], Q_y[act] + Q_vy[act] * u[act] + 0.5 * -60 * u[act] ** 2, Q_br[act] * (1 - u[act] / 0.9))
    kat = cv2.GaussianBlur(kat, (0, 0), 1.0) * 5 + cv2.GaussianBlur(kat, (0, 0), 3.5) * 6
    out = out + (255 - np.clip(out, 0, 255)) * (np.clip(kat, 0, 1.0)[..., None] * ALTIN)   # v3: toz altin tonunda
    # ilk kare ve son 0,4 s birebir kapak
    bas = 1 - ss(0.0, 0.5, t); son = ss(SURE - 0.6, SURE - 0.2, t)
    out = out * (1 - max(bas, son)) + Cv * max(bas, son)
    out = yakinlas(out)
    out = out * (1 - SIL[..., None]) + ARKA * SIL[..., None]
    at = 1.0                                                                     # Serdar: ustteki yazilar video boyunca sabit
    out = out * (1 - (TG * at)[..., None]) + GOLGE_ * (TG * at)[..., None]
    out = out * (1 - (TK * at)[..., None]) + RENK_ * (TK * at)[..., None]
    son2 = max(1 - ss(0.0, 0.35, t), ss(SURE - 0.5, SURE - 0.2, t))
    out = out * (1 - son2) + SON_KARE * son2
    if i == 0 or i == NF - 1:
        out = SON_KARE
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
dec.stdout.close(); dec.wait()
enc.stdin.close()
assert enc.wait() == 0
os.replace(tmp, CIKIS)
print("tamam", CIKIS, "sure", SURE, "kamera kaymasi en cok px", round(kay_max, 2),
      "parca px", dict(halka=int(halka.sum()), sem_L=int(sem_L.sum()), sem_R=int(sem_R.sum()), burc=int(burclar.sum()), isim=int(isim.sum()), tarih=int(tarih.sum())))
