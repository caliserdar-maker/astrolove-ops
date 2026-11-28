#!/usr/bin/env python3
"""kapak_video2 (KARARLAR_20261128_87): kapak_video.py + ortam degiskenleri:
N_KAT (zerre sayisi carpani, Serdar "miktar 2 katina"), TOZ_S (zerre boyu 1/TOZ_S, Serdar "yariya" -> 2),
OLUSUM=dolum (Serdar "sembol birden belirmeyecek, zerreler doldukca olusacak"): murekkep yalniz inen toz kadar (zaman egrisi yok,
F^1.5), toz alttan uste sirayla iner, inen zerre 0,25 sn parlayip soner. OLUSUM=eski: v7 davranisi.
Poster ilan videosu, YENI kapak (TikTok kapagi, 3000x2250) icin (Serdar 28 Kas: "video da suan mevcut poster videolarinin
mantiginda olacak, yani ilgili burclar ve logodan altin tozlari ozgun sembolu olusturacak").
Kaynak mantik: astrolove-ops sosyal/poster_video/poster_video_v7.py (canli 78 poster videosu). Ayni olanlar: 6 sn, 30 fps,
1440x1080, sessiz H.264 crf 17; ilk kare ve son kare (>= 5,0 sn) = kapak; ilk 0,3 sn kapaktaki sembol yumusakca kaybolur;
toz iki kucuk burc isaretinden ve sonsuzluk isaretinden cikar (rng 11, gecikme 0.62, yay 8-24 px, %22 ALTIN (196,150,64) /
%78 sembolun kendi rengi, parlaklik 0.55-1.0, tane sigma 0.45); sembol murekkebi tozun onune gecmez (min(c(t), F), F = yerel
toz birikimi, c(t) = ease((tt - 0.36) / 0.64)); 5,0 sn'de tam.
Farklar (yalniz sahne): kapakta mockup/poster yok, tum kare lacivert zemin. Katmanlar kapagin kendisinden: altin alfa = R - B
esigi; satir bantlari (bosluk > 20 px): son iki bant = kucuk burclar + sonsuzluk satiri ve burc adlari satiri, ustundeki her
sey sembol. Sembolsuz hal: sembol bolgesi (31 px genisletilmis) normalize Gauss dolgusu (v7 V7_DOLGU=nk ile ayni yontem).
Mesaj yok (kapakta mesaj yok). Toz sayisi: canli CL videosu yogunlugu (N 58000 / eski CL kapagi sembol bolgesi 28154 px,
video olcegi) x yeni sembol bolgesi.
Kullanim: python -I kapak_video.py <kapak.jpg> <cikti.mp4>
Laptopta ffmpeg yok: mp4v yazilir, sonra sahne_kapak/video_h264.ps1 ile H.264 (Windows kodlayicisi) yapilir."""
import json, os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt

KAPAK, OUT = sys.argv[1:3]
VW, VH, FPS, SURE, SILME, BITIS = 1440, 1080, 30, 6.0, 0.3, 5.0
N_REF, BOLGE_REF = 58000, 28154
rng = np.random.default_rng(11)
t0 = time.time()
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))

kap = np.asarray(Image.open(KAPAK).convert('RGB'))
KAP = np.clip(np.round(cv2.resize(kap, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)), 0, 255)
rb = KAP[..., 0] - KAP[..., 2]
alpha = np.clip((rb + 10) / 130.0, 0, 1)            # zemin R-B ~ -60..-80 -> 0; altin ~ +150 -> 1; parilti kismi
core = (rb > 40).astype(np.uint8)
# satir bantlari
rows = np.where(core.any(1))[0]
bands = []
for r in rows:
    if bands and r - bands[-1][1] <= 20:
        bands[-1][1] = r
    else:
        bands.append([r, r])
if len(bands) < 3:
    raise SystemExit(f'beklenen en az 3 bant, bulunan {len(bands)}')
g0, g1 = bands[-2]; n0, n1 = bands[-1]
s1 = bands[-3][1]
print('bantlar', bands, flush=True)
def bant(y0, y1, pad=6):
    m = np.zeros((VH, VW), np.float32); m[max(0, y0 - pad):y1 + pad + 1] = 1; return m
MS = alpha * bant(0, s1, 12)                          # sembol (+ parilti)
MS[g0 - 6:] = 0
MG = alpha * bant(g0, g1, 6)                          # iki kucuk burc + sonsuzluk
msym = (core * bant(0, s1, 12)).astype(np.uint8); msym[g0 - 6:] = 0
# bos hal: sembol bolgesi normalize Gauss dolgusu
RS = cv2.GaussianBlur(cv2.dilate(msym, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 5.0)
hm = cv2.dilate((RS > 0.02).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
w = (~hm).astype(np.float32); dol = KAP.copy(); kalan = hm.copy()
for sg in (6, 12, 24, 48, 96, 192):
    den = cv2.GaussianBlur(w, (0, 0), sg)
    nk = cv2.GaussianBlur(KAP * w[..., None], (0, 0), sg) / np.maximum(den, 1e-6)[..., None]
    ok = kalan & (den >= 0.25); dol[ok] = nk[ok]; kalan &= ~ok
if kalan.any():
    dol[kalan] = nk[kalan]
BASE = np.clip(KAP + (dol - KAP) * RS[..., None], 0, 255)
FULL = KAP
WS = np.clip(RS, 0, 1)
# QC: bos halde sembol bolgesinde altin kalmamali
art = float(np.clip(BASE[..., 0] - BASE[..., 2], -255, 255)[msym > 0].max())
print(f'bos hal sembol bolgesi R-B max {art:.1f} (zemin ~ -60)', flush=True)

def noktalar(m, n):
    ys, xs = np.where(m > 0.35)
    i = rng.choice(len(xs), n, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((n, 2)).astype(np.float32) - 0.5

BOLGE = int((cv2.dilate((MS > 0.95).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0).sum())
N_KAT = float(os.environ.get('N_KAT', '1')); OLUSUM = os.environ.get('OLUSUM', 'eski')
N = int(round(N_REF * BOLGE / BOLGE_REF * N_KAT / 100.0) * 100)
print(f'sembol bolgesi {BOLGE} px -> N {N}', flush=True)
src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
SON = 0.05                                             # inen zerrenin parlayip sonme suresi (tt; 0,25 sn)
UCUS = float(os.environ.get('UCUS', '0.4'))            # dolum: ucan zerre parlakligi
if OLUSUM == 'dolum':
    # alttan uste: sembolun alt kismi (kaynak gliflere yakin) once dolar; ayni yukseklikte rastgele dagilim
    ys_ = dst[:, 1]; rank = (ys_.max() - ys_) / max(1.0, ys_.max() - ys_.min())
    GMAX = 1.0 - 0.38 - SON
    RANK = float(os.environ.get('RANK', '0.7'))       # sira agirligi (kalan rastgele: kalkis yayilir, duvar olusmaz)
    gec = (GMAX * (RANK * rank + (1 - RANK) * rng.random(N))).astype(np.float32)
yay = -(8 + 16 * rng.random(N).astype(np.float32)) * (VW / 1440.0)
ALTIN = np.array([196, 150, 64], np.float32)
ANA = np.median(KAP[(MS > 0.98)], 0).astype(np.float32)
renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, ANA)
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)
print(f'toz renkleri: ana {ANA.round().tolist()} %78, ALTIN %22', flush=True)

nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
TANE = 0.45
TOZ_S = int(os.environ.get('TOZ_S', '1')); TOZ_KAZANC = float(os.environ.get('TOZ_KAZANC', str(TOZ_S)))
TARR = gec + 0.38
dxi = np.clip(np.round(dst[:, 0]).astype(int), 0, VW - 1); dyi = np.clip(np.round(dst[:, 1]).astype(int), 0, VH - 1)
H_TUM = np.zeros((VH, VW), np.float32); np.add.at(H_TUM, (dyi, dxi), 1.0)
CF = cv2.GaussianBlur(H_TUM, (0, 0), 3.0)
iyi = CF > 0.02 * CF[MS > 0.5].max()
II = distance_transform_edt(~iyi, return_indices=True)[1]
C_EGRI = [ease((k / (nB - 1) - 0.36) / 0.64) for k in range(nB)]
CEK = MS > 0.95
SIRA = np.argsort(TARR); TS = TARR[SIRA]; H_T = np.zeros((VH, VW), np.float32); k_ = 0
IC = {'kare': [], 'murekkep': [], 'toz_ortusu': [], 'ihlal': []}

def murekkep(tt):
    global k_
    j = int(np.searchsorted(TS, tt, side='right'))
    if j > k_:
        np.add.at(H_T, (dyi[SIRA[k_:j]], dxi[SIRA[k_:j]]), 1.0); k_ = j
    F = np.clip((cv2.GaussianBlur(H_T, (0, 0), 3.0) / np.maximum(CF, 1e-6))[II[0], II[1]], 0, 1)
    if OLUSUM == 'dolum':
        return F ** 1.5, F
    return np.minimum(C_EGRI[min(len(C_EGRI) - 1, int(round(tt * (nB - 1))))], F), F

KAP8 = KAP.astype(np.uint8)
def yazici():
    """ffmpeg yok (laptop): OpenCV H.264 yazicisi (sahne_kapak/video_kur.py yazici_sec ile ayni sira), deneme dosyasiyla sinanir"""
    import tempfile
    for ad, arka, kod in (("FFMPEG", cv2.CAP_FFMPEG, "avc1"), ("MSMF", cv2.CAP_MSMF, "avc1"), ("MSMF", cv2.CAP_MSMF, "H264"), ("FFMPEG", cv2.CAP_FFMPEG, "mp4v")):
        yol = os.path.join(tempfile.gettempdir(), f"kv_deneme_{ad}_{kod}.mp4")
        y = cv2.VideoWriter(yol, arka, cv2.VideoWriter_fourcc(*kod), FPS, (VW, VH))
        if y.isOpened():
            for _ in range(5): y.write(np.zeros((VH, VW, 3), np.uint8))
            y.release(); c = cv2.VideoCapture(yol); n = 0
            while c.read()[0]: n += 1
            c.release(); os.remove(yol)
            if n >= 4:
                print('yazici', ad, kod, flush=True)
                return cv2.VideoWriter(OUT, arka, cv2.VideoWriter_fourcc(*kod), FPS, (VW, VH))
    raise SystemExit('H.264 yazici yok')
class _Yaz:
    def __init__(s): s.w = yazici()
    def write(s, b): s.w.write(cv2.cvtColor(np.frombuffer(b, np.uint8).reshape(VH, VW, 3), cv2.COLOR_RGB2BGR))
class _Pr:
    def __init__(s): s.stdin = _Yaz()
    def wait(s): s.stdin.w.release()
_Yaz.close = lambda s: None
pr = _Pr()
KARELER = {}
for i in range(nT):
    if i == 0 or i >= nB:
        pr.stdin.write(KAP8.tobytes())
        if i in (0, nT - 1): KARELER[i] = KAP8
        continue
    tt = i / (nB - 1)
    uu = np.clip((tt - gec) / 0.38, 0, 1)
    mk, F = murekkep(tt)
    IC['kare'].append(i); IC['murekkep'].append(float(mk[CEK].mean())); IC['toz_ortusu'].append(float(F[CEK].mean()))
    IC['ihlal'].append(float((mk[CEK] - F[CEK]).max()))
    A = np.clip(mk * WS, 0, 1)[..., None]
    f = BASE * (1 - A) + FULL * A
    if i <= nS:
        e = ease(i / nS); f = KAP * (1 - e) + f * e
    ue = uu * uu * (3 - 2 * uu)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
    if OLUSUM == 'dolum':
        son = np.clip(1 - (tt - TARR) / SON, 0, 1)          # indikten sonra 0,25 sn'de soner
        gor = (uu > 0) & (son > 0)
        # ucarken soluk (yogun kutle gorunmesin), inince parlar ve soner
        zarf = np.where(uu < 1, UCUS * np.clip(uu / 0.15, 0, 1), son)
    else:
        gor = (uu > 0) & (uu < 1)
        zarf = np.sin(np.pi * uu)
    # Serdar 28 Kas "zerreler cok daha kucuk": toz katmani TOZ_S kat buyuk tuvalde cizilir, sonra kucultulur (zerre ~1/TOZ_S boy)
    WW, HH = VW * TOZ_S, VH * TOZ_S
    xi, yi = (p[gor, 0] * TOZ_S).astype(int), (p[gor, 1] * TOZ_S).astype(int)
    ok = (xi >= 0) & (xi < WW) & (yi >= 0) & (yi < HH)
    a_ = (par[gor] * zarf[gor])[ok]
    idx = yi[ok] * WW + xi[ok]
    al = np.bincount(idx, weights=a_, minlength=WW * HH).reshape(HH, WW).astype(np.float32)
    kat = np.zeros((HH, WW, 3), np.float32); rg = renk[gor][ok]
    for c in range(3):
        kat[..., c] = np.bincount(idx, weights=rg[:, c] * a_, minlength=WW * HH).reshape(HH, WW)
    al = cv2.GaussianBlur(al, (0, 0), TANE) * 2.0; kat = cv2.GaussianBlur(kat, (0, 0), TANE) * 2.0
    if TOZ_S > 1:
        al = cv2.resize(al, (VW, VH), interpolation=cv2.INTER_AREA) * TOZ_KAZANC
        kat = cv2.resize(kat, (VW, VH), interpolation=cv2.INTER_AREA) * TOZ_KAZANC
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None]
    o = np.clip(f * (1 - a3) + rk * a3, 0, 255).astype(np.uint8)
    pr.stdin.write(o.tobytes())
    if i in (9, 30, 60, 90, 120, 140): KARELER[i] = o
    if i % 30 == 0:
        g = time.time() - t0; print(f'  kare {i}/{nB} (gecen {g:.0f}s)', flush=True)
pr.stdin.close(); pr.wait()
# kontak
ks = sorted(KARELER); th = [cv2.resize(KARELER[k], (480, 360)) for k in ks]
kon = np.concatenate([np.concatenate(th[:4], 1), np.concatenate(th[4:8] + [np.zeros_like(th[0])] * (8 - len(th)), 1)], 0)
Image.fromarray(kon).save(OUT + '.KONTAK.jpg', quality=88)
json.dump({'N': N, 'bolge': BOLGE, 'bantlar': [[int(a), int(b)] for a, b in bands], 'bos_artik_rb_max': art, 'kontak_kareler': ks, 'ihlal_max': max(IC['ihlal']),
           'murekkep_son': IC['murekkep'][-1], 'mb': round(os.path.getsize(OUT) / 1e6, 2), 'sure_sn': nT / FPS},
          open(OUT + '.qc.json', 'w'), indent=1)
print('tamam', OUT, round(os.path.getsize(OUT) / 1e6, 2), 'MB', f'{time.time() - t0:.0f}s')
