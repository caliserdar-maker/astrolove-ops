#!/usr/bin/env python3
"""Ornament ilan videosu ORNEK (Serdar 6 Kas fikri): canli video dili (ilk ve son kare = kapak, 0-0,3 sn sembol ve halka
yumusakca kaybolur, altin toz iki kucuk burctan akar, sembol tozla yeniden olusur, kamera sabit, sessiz, 6 sn, 1440x1080, 30 fps)
+ YENI: sol kucuk burcun tozu halkanin SOL yarisini, sag kucuk burcun tozu SAG yarisini kurar; halka alttaki iki ucundan baslayip
yukarida delikte birlesir. Sembolun sol yarisi sol burctan, sag yarisi sag burctan.
Katmanlar kapak kompozitinin kendisinden (ayni kod, baski katmani eksik): KAPAK_tam (onayli R3_RUBY), KAPAK_semsiz (sembol yok),
KAPAK_bos (sembol + halka yok). Kare = bos + halka_farki * g_h + sembol_farki * g_s; g = max(kaybolma, toz birikimi). BITIS'te tam kapak.
Kullanim: video_orn.py <dir> <cikti.mp4>"""
import os, sys, json, math, subprocess, time
import numpy as np, cv2
from PIL import Image
D, OUT = sys.argv[1], sys.argv[2]
VW, VH, FPS, SURE, SILME, BITIS = 1440, 1080, 30, 6.0, 0.3, 5.0
rng = np.random.default_rng(11)
t0 = time.time()
def yukle(ad):
    im = Image.open(f"{D}/KAPAK_{ad}.jpg").convert("RGB")
    return np.asarray(im.resize((VW, VH), Image.LANCZOS)).astype(np.float32)
TAM, SEM, BOS = yukle("tam"), yukle("semsiz"), yukle("bos")
s = VW / 3000.0
J = json.load(open(f"{D}/KAPAK_tam.json")); d = J["disk"]
cx, cy, R = d["cx"] * s, d["cy"] * s, d["R"] * s
k = R / 449.0                                                   # baski 954 (r 449 kesim) -> video
def bv(px, py):
    return cx + (px - 476.0) * k, cy + (py - 477.0) * k
lum = lambda a: a @ np.float32([0.299, 0.587, 0.114])
ink_s = np.clip(np.abs(lum(TAM) - lum(SEM)) / 30.0, 0, 1)      # sembol murekkebi (video pikseli)
ink_h = np.clip(np.abs(lum(SEM) - lum(BOS)) / 30.0, 0, 1)      # halka murekkebi
dl_s, dl_h = TAM - SEM, SEM - BOS                               # katman farklari (isarelti)
# ---- kaynaklar: kucuk burc pikselleri (baski maskesinden, video koordinatina)
M = np.load(f"{D}/maske954.npz")
def kaynak(m):
    ys, xs = np.nonzero(m)
    X, Y = bv(xs.astype(np.float32), ys.astype(np.float32))
    return np.c_[X, Y]
KS, KR = kaynak(M["sol"]), kaynak(M["sag"])
H_ = json.load(open(f"{D}/halka.json")); hcx, hcy = bv(H_["cx"], H_["cy"]); hr = H_["r"] * k; H0X = hcx
# ---- hedefler: murekkep pikselleri, agirlikla ornekleme
def hedef(ink, n):
    ys, xs = np.nonzero(ink > 0.08); w = ink[ys, xs]; w = w / w.sum()
    i = rng.choice(len(xs), n, p=w)
    return np.c_[xs[i] + rng.uniform(-0.5, 0.5, n), ys[i] + rng.uniform(-0.5, 0.5, n)]
alan_s, alan_h = float(ink_s.sum()), float(ink_h.sum())
YOG = 3.2 * float(os.environ.get('V_YOGX', '1'))                                                        # parcacik / murekkep pikseli (ornek; olcumle ayarlanir)
NS, NH = int(alan_s * YOG), int(alan_h * YOG)
hx_, hy_, hr_ = J['yeni_delik']['x'] * s, J['yeni_delik']['y'] * s, J['delik_r_px'] * s + 2.0   # inceleme 3: delige hedef ve toz yok
yy_, xx_ = np.mgrid[:VH, :VW]; DELIK = np.hypot(xx_ - hx_, yy_ - hy_) < hr_
ink_h = ink_h * ~DELIK; ink_s = ink_s * ~DELIK
# inceleme 2: halka iki yarisina esit hedef
def hedef_yari(ink, n, sol):
    m = ink.copy(); xs_ = np.arange(VW)[None, :]
    m = m * ((xs_ < H0X) if sol else (xs_ >= H0X))
    return hedef(m, n)
TS = hedef(ink_s, NS)
TH = np.r_[hedef_yari(ink_h, NH // 2, True), hedef_yari(ink_h, NH - NH // 2, False)]
# halka: aci (delik ust = -90 derece); alt uclardan delige ilerleme orani 0..1
aci = np.degrees(np.arctan2(TH[:, 1] - hcy, TH[:, 0] - hcx))    # -180..180, ust -90
uzak = np.abs(((aci + 90) + 180) % 360 - 180)                   # deligin tepesinden acisal uzaklik 0..180
u_max = float(np.percentile(uzak, 99.5))
ilerleme = np.clip(1 - uzak / u_max, 0, 1)                       # uc 0 -> delik 1
sol_h = TH[:, 0] < hcx
# varis zamanlari
var_h = 0.75 + 3.75 * ilerleme ** 1.0 + rng.normal(0, 0.10, NH)
# Serdar 6 Kas: ozgun sembol birden belirmesin, tozlar doldukca sifirdan kademeli olussun -> varis zamani konuma bagli:
# toz alttan (kucuk burclardan) geldigi icin sembol ALTTAN USTE dolar; yerel dagilim +-0,12 sn (v6: tum sembolde rastgele 1,1-4,85)
ys_s = TS[:, 1]; yn = (ys_s - ys_s.min()) / max(1.0, ys_s.max() - ys_s.min())
var_s = 1.2 + 3.55 * (1 - yn) + rng.normal(0, 0.12, NS)
var_h = np.clip(var_h, 0.6, 4.9); var_s = np.clip(var_s, 0.8, 4.9)
yol_h = rng.uniform(0.9, 1.5, NH); yol_s = rng.uniform(1.0, 1.7, NS)
# cikis: erken varanlar ayni anda cikip kucuk burcu leke yapmasin; cikislar 0,05-0,9 sn'ye yayilir, yol en az 0,5 sn
def cikis(var, yol):
    c = np.maximum(var - yol, rng.uniform(0.05, 0.9, len(var)))
    return np.minimum(c, var - 0.5)
cik_h = cikis(var_h, yol_h); cik_s = cikis(var_s, yol_s)
# kaynak secimi
def kaynak_sec(sol_mask):
    n = len(sol_mask); P = np.zeros((n, 2), np.float32)
    a = rng.integers(0, len(KS), n); b = rng.integers(0, len(KR), n)
    P[sol_mask] = KS[a[sol_mask]]; P[~sol_mask] = KR[b[~sol_mask]]
    return P
sol_s = TS[:, 0] < cx
PH0, PS0 = kaynak_sec(sol_h), kaynak_sec(sol_s)
# inceleme 1: cikis isaretin ~8 px cevresine yayilir
P0 = np.r_[PH0, PS0] + rng.normal(0, 4.0, (NH + NS, 2)).astype(np.float32); P3 = np.r_[TH, TS]; CIK = np.r_[cik_h, cik_s]; VAR = np.r_[var_h, var_s]
N = len(P0); TUR = np.r_[np.zeros(NH, np.int8), np.ones(NS, np.int8)]
# yol: kubik Bezier; kontrol noktalari once yukari (toz kalkar), sonra hedefe yanal yay
dv = P3 - P0; L = np.linalg.norm(dv, axis=1, keepdims=True) + 1e-6; nrm = np.c_[-dv[:, 1], dv[:, 0]] / L
yay = rng.uniform(-0.28, 0.28, (N, 1)) * L
P1 = P0 + np.c_[rng.normal(0, 6, N), -rng.uniform(25, 70, N)] + nrm * yay * 0.3
P2 = P3 + nrm * yay - dv * 0.18
PARLAK = rng.uniform(0.55, 1.0, N).astype(np.float32)
ALTIN = np.float32([200, 146, 52]); ALTIN2 = np.float32([228, 180, 86])      # Serdar 6 Kas: daha koyu, altin tozu rengi (v3: 224,178,92 / 255,226,150)
RK = np.where(rng.random(N) < 0.18, 1, 0)
ease = lambda x: x * x * (3 - 2 * x)
# birikim haritasi icin hedef pikselleri
HX = np.clip(np.round(P3[:, 0]).astype(int), 0, VW - 1); HY = np.clip(np.round(P3[:, 1]).astype(int), 0, VH - 1)
def birikim(mask):
    g = np.zeros((VH, VW), np.float32); np.add.at(g, (HY[mask], HX[mask]), 1.0)
    return cv2.GaussianBlur(g, (0, 0), 3.0)
TOPLAM_H = birikim(TUR == 0) + 1e-6; TOPLAM_S = birikim(TUR == 1) + 1e-6
nF = int(FPS * SURE); nB = int(FPS * BITIS)
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
                       "-i", "-", "-an", "-threads", "3", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
tam8 = np.clip(TAM + 0.5, 0, 255).astype(np.uint8)
olc = []
for f in range(nF):
    t = f / FPS
    if f == 0 or f >= nB:
        ff.stdin.write(tam8.tobytes()); continue
    kay = 1 - ease(min(1.0, t / SILME))                             # 0-0,3 sn eski sembol ve halka kaybolur
    var = VAR <= t
    rh = np.clip(birikim(var & (TUR == 0)) / TOPLAM_H / 0.9, 0, 1)   # Serdar 6 Kas: murekkep ilk tozla sifirdan, biriktikce (esik yok)
    rs = np.clip(birikim(var & (TUR == 1)) / TOPLAM_S / 0.9, 0, 1)
    gh = np.maximum(kay, rh)[..., None]; gs = np.maximum(kay, rs)[..., None]
    kare = BOS + dl_h * gh + dl_s * gs
    # ucan toz
    uc = (CIK <= t) & (VAR > t)
    if uc.any():
        tt = ease(np.clip((t - CIK[uc]) / (VAR[uc] - CIK[uc]), 0, 1))[:, None]
        a, b, c, e = P0[uc], P1[uc], P2[uc], P3[uc]
        p = (1 - tt) ** 3 * a + 3 * (1 - tt) ** 2 * tt * b + 3 * (1 - tt) * tt ** 2 * c + tt ** 3 * e
        uzak_ = np.linalg.norm(p - P0[uc], axis=1)
        sol_ = np.clip((VAR[uc] - t) / 0.12, 0, 1) * np.clip(uzak_ / 80.0, 0, 1) ** 1.8   # inceleme 1: burctan 38 px uzaklasana dek saydam (isaret leke olmasin)
        sol_ = sol_ * ~DELIK[np.clip(p[:, 1].astype(int), 0, VH - 1), np.clip(p[:, 0].astype(int), 0, VW - 1)]
        SS = int(os.environ.get('V_SS', '4'))                               # Serdar 6 Kas: taneler cok daha kucuk -> 4x ust ornek (v4-v5: 2x)
        x, y = p[:, 0] * SS, p[:, 1] * SS; ok = (x >= 0) & (x < VW * SS - 1) & (y >= 0) & (y < VH * SS - 1)
        al = np.zeros((VH * SS, VW * SS), np.float32); ren = np.zeros((VH * SS, VW * SS, 3), np.float32)
        x0 = np.floor(x[ok]).astype(int); y0 = np.floor(y[ok]).astype(int); fx = x[ok] - x0; fy = y[ok] - y0
        w = (PARLAK[uc][ok] * sol_[ok])
        col = np.where(RK[uc][ok][:, None] == 1, ALTIN2, ALTIN)
        for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(al, (y0 + dy, x0 + dx), w * ww)
            np.add.at(ren, (y0 + dy, x0 + dx), col * (w * ww)[:, None])
        sg = float(os.environ.get('V_SG', '0.35'))
        alb = cv2.GaussianBlur(al, (0, 0), sg); renb = cv2.GaussianBlur(ren, (0, 0), sg)
        alk = cv2.resize(alb, (VW, VH), interpolation=cv2.INTER_AREA); renk_ = cv2.resize(renb, (VW, VH), interpolation=cv2.INTER_AREA)
        al_b = np.clip(alk * float(os.environ.get('V_KAZANC', str(1.5 * SS * SS))), 0, 0.9)   # tek tanenin tepe opakligi ~v5 ile ayni
        ren_b = renk_ / (alk[..., None] + 1e-6)
        kare = kare * (1 - al_b[..., None]) + ren_b * al_b[..., None]
        olc.append((round(t, 2), int(uc.sum())))
    ff.stdin.write(np.clip(kare + 0.5, 0, 255).astype(np.uint8).tobytes())
    if f % 30 == 0:
        print(f"{f}/{nF} | {time.time() - t0:.0f} sn | ucan {int(uc.sum())}", flush=True)
ff.stdin.close(); ff.wait()
print(json.dumps(dict(N=N, NH=NH, NS=NS, alan_h=round(alan_h), alan_s=round(alan_s), sure=round(time.time() - t0))))
