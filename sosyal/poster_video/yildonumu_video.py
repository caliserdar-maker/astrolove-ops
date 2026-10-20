#!/usr/bin/env python3
"""Yil donumu (Y1) ilan videosu (20 Eki 2026, Serdar): onayli V6 ile ayni mantik ve kod. Sahne = Y1 kapagi (KAPAK_Y1_78
<CIFT>.jpg, 2400x2400), video 1080x1080, 6 sn, 30 fps, ses yok; ilk ve son kare kapak.
Motor (toz, murekkep = min(c(t), F), ince tane sigma 0.45, 0,3 sn silme, BITIS 5,0 sn, sonra sabit kapak) poster_video_v6.py'den
birebir kopya (asagida 'V6 MOTORU' bolumu). Yalniz sahne ayristirmasi Y1 kapagina gore:
- buyuk birlesik sembol: kart ortasindaki terracotta murekkep (R - B > 80, lum < 170) parcalari; alfa = yerel kagit ile
  murekkep arasindaki oran (kapak pikselleri; yeniden cizim yok). Silinip yeniden olusan YALNIZ bu sembol.
- toz kaynagi: sembol ile isim satiri arasindaki iki kucuk glif (sol / sag). Aralarinda isaret yok (Y1 tasariminda sonsuz yok).
- mesaj satiri YOK: yazim adimi bos (WM = 0). Baslik, "A & B", YEAR ONE, isimler, Paper Anniversary, tarih sabit.
- bos hal: sembol + kabartma golgesi (olculen golge <= 22 px; 2400 px'te 31 px genisletme) Telea ile kagittan doldurulur,
  ince kagit dokusu ayni kartin temiz kagidindan 48 px bloklarla kopyalanir (duz leke izi kalmasin).
Toz rengi (kupa kurali): %78 sembolun kendi murekkebi (olculen medyan), %22 acik vurgu = murekkep 0,55 + kagit isigi 0,45.
Kullanim: yildonumu_video.py <y1_kapak.jpg> <cikti.mp4>   (ortam: V6_N, V6_C, TOZSUZ ayni)"""
import os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

KAPAK, OUT = sys.argv[1:3]
RENK_MOD = 'murekkep'
BITIS = 5.0
VW, VH = 1080, 1080                                       # Y1 kapagi kare: kupadaki gibi V x V
FPS, SURE, SILME = 30, 6.0, 0.3
rng = np.random.default_rng(11)
t0 = time.time()

# ---------- Y1 sahnesi: sembol, glifler, bos hal (kapak pikselleri)
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
kf = kap_src.astype(np.float32); Hk, Wk = kf.shape[:2]
lum_ = kf @ np.float32([0.299, 0.587, 0.114])
bg_ = cv2.medianBlur(kap_src, 61).astype(np.float32)          # yerel kagit (ince cizgiler medyanda kaybolur)
lbg = bg_ @ np.float32([0.299, 0.587, 0.114])
tm = ((kf[..., 0] - kf[..., 2] > 80) & (lum_ < 170)).astype(np.uint8)
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(tm, 8)
cx_ = Wk / 2
# kart ortasi: sembol parcalari kapak merkezinin +-%22'si icinde (yan kagit seritleri disarida)
sym_ids = [i for i in range(1, n_) if st_[i, 4] > 200 and st_[i, 0] > cx_ - 0.22 * Wk and st_[i, 0] + st_[i, 2] < cx_ + 0.22 * Wk
           and st_[i, 1] > 0.38 * Hk and st_[i, 1] + st_[i, 3] < 0.68 * Hk]
if not sym_ids:
    raise RuntimeError('sembol bulunamadi')
_ref = max(sym_ids, key=lambda i: st_[i, 4]); _rc = np.median(kf[lab_ == _ref], 0)   # en buyuk parcanin murekkep rengi
sym_ids = [i for i in sym_ids if np.abs(np.median(kf[lab_ == i], 0) - _rc).max() < 25]   # ayni murekkep (kagit seridi golgesi disarida)
msym = np.isin(lab_, sym_ids).astype(np.uint8)
ys_, xs_ = np.where(msym > 0); sy0, sy1 = int(ys_.min()), int(ys_.max())
INK = np.median(kf[(msym > 0) & (lum_ < 150)], 0)
d_ = bg_ - INK[None, None]
alfa_ = np.clip(((bg_ - kf) * d_).sum(-1) / np.maximum((d_ * d_).sum(-1), 1.0), 0, 1)
MS_p = alfa_ * cv2.dilate(msym, np.ones((7, 7), np.uint8))
# altta: koyu parcalar (kagittan >= 25 koyu)
dk = ((lbg - lum_) > 25).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(dk, 8)
alt = sorted([(i, *st2[i]) for i in range(1, n2) if st2[i, 4] > 100 and st2[i, 1] > sy1 + 10 and abs(st2[i, 0] + st2[i, 2] / 2 - cx_) < 0.25 * Wk],
             key=lambda c: c[2])
# isim satiri: ust kenarlari +-4 px icinde en az 4 parca (harfler); glif satiri = sembol ile isim satiri arasi
tops = sorted(c[2] for c in alt)
isim_y = next((t for t in tops if sum(abs(u - t) <= 4 for u in tops) >= 4), None)
if isim_y is None:
    raise RuntimeError('isim satiri bulunamadi')
glif = [c for c in alt if c[2] + c[4] < isim_y - 2]
left = [c for c in glif if c[1] + c[3] / 2 < cx_]; right = [c for c in glif if c[1] + c[3] / 2 >= cx_]
if not left or not right:
    raise RuntimeError('sol veya sag kucuk burc bulunamadi')
bands = [glif]
kutu_ = lambda cs: [int(min(c[1] for c in cs)), int(min(c[2] for c in cs)), int(max(c[1] + c[3] for c in cs) - min(c[1] for c in cs)),
                    int(max(c[2] + c[4] for c in cs) - min(c[2] for c in cs))]
galfa = np.clip((lbg - lum_) / np.maximum(lbg - np.median(lum_[np.isin(lab2, [c[0] for c in left + right])]), 1.0), 0, 1)
MG_p = galfa * cv2.dilate(np.isin(lab2, [c[0] for c in left + right]).astype(np.uint8), np.ones((5, 5), np.uint8))
RS_p = cv2.GaussianBlur(cv2.dilate(msym, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 5.0)
hm = cv2.resize((RS_p > 0.02).astype(np.uint8), (Wk // 2, Hk // 2), interpolation=cv2.INTER_NEAREST)
hi = cv2.resize(kap_src, (Wk // 2, Hk // 2), interpolation=cv2.INTER_AREA)
bos = cv2.resize(cv2.inpaint(hi, cv2.dilate(hm, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32),
                 (Wk, Hk), interpolation=cv2.INTER_CUBIC)
# kagit dokusu: Telea dolgusu duz kalir (iz). Ince doku (kf - blur 2) ayni kartin temiz kagidindan 48 px bloklarla kopyalanir
# (kapagin kendi pikselleri; yeniden cizim yok). Temiz = murekkep/yazi/serit kenari yok, silme bolgesi disi.
HFk = kf - cv2.GaussianBlur(kf, (0, 0), 2.0)
ozel = cv2.dilate((np.abs(kf - bg_).max(-1) > 12).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
BL = 48
kart_ = (np.abs(lbg - np.median(lbg[(RS_p > 0.02)])) < 6) & ~ozel & ~(cv2.dilate((RS_p > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
temiz = cv2.erode(kart_.astype(np.uint8), np.ones((BL, BL), np.uint8), anchor=(0, 0)) > 0   # blok sol-ust koseleri
cy_, cx2 = np.where(temiz)
if len(cy_) < 50:
    raise RuntimeError('doku icin temiz kagit bulunamadi')
dok = np.zeros_like(kf)
ry, rx = np.where(RS_p > 0.02); rng_d = np.random.default_rng(5)
for yb in range(ry.min() - ry.min() % BL, ry.max() + 1, BL):
    for xb in range(rx.min() - rx.min() % BL, rx.max() + 1, BL):
        j = rng_d.integers(len(cy_)); sy_, sx_ = cy_[j], cx2[j]
        hh, ww = min(BL, Hk - yb, Hk - sy_), min(BL, Wk - xb, Wk - sx_)
        dok[yb:yb + hh, xb:xb + ww] = HFk[sy_:sy_ + hh, sx_:sx_ + ww]
bos = bos + dok * (cv2.resize(hm, (Wk, Hk), interpolation=cv2.INTER_NEAREST)[..., None] > 0)
vid = lambda m: cv2.resize(m.astype(np.float32), (VW, VH), interpolation=cv2.INTER_AREA)
KAP = np.clip(np.round(vid(kf)), 0, 255)
FULL = KAP
BASE = np.clip(KAP + vid((bos - kf) * RS_p[..., None]), 0, 255)
MS, MG = vid(MS_p), vid(MG_p)
WS = np.clip(vid(RS_p), 0, 1)
WM = np.zeros((VH, VW), np.float32)                           # mesaj satiri yok: yazim adimi bos
XX = np.arange(VW, dtype=np.float32)[None, :].repeat(VH, 0)
mx0, mx1 = 0, 0
GLIF = {'sign_a': kutu_(left), 'sign_b': kutu_(right), 'poster_w': int(Wk), 'sonsuz': [], 'bantlar': len(bands),
        'sembol_kutu': [int(xs_.min()), sy0, int(xs_.max()), sy1], 'murekkep_rengi': INK.round().tolist()}
_g = [cv2.resize(galfa[y:y + h, x:x + w].astype(np.float32), (64, 64), interpolation=cv2.INTER_AREA) for x, y, w, h in (GLIF['sign_a'], GLIF['sign_b'])]
_g = [(g - g.mean()) / (g.std() + 1e-6) for g in _g]
GLIF['benzerlik'] = round(float((_g[0] * _g[1]).mean()), 3)
print(f"Y1 sahne: sembol {len(sym_ids)} parca {GLIF['sembol_kutu']}, murekkep {GLIF['murekkep_rengi']}, glif {GLIF['sign_a']} / {GLIF['sign_b']}", flush=True)
Image.fromarray(((MS > 0.95) * 255).astype(np.uint8)).save(OUT + '.sembol_maske.png')   # QC: cekirdek sembol pikselleri
Image.fromarray(BASE.astype(np.uint8)).save(OUT + '.bos.png')                            # QC: silinmis hal (iz kontrolu)
Image.fromarray((WS * 255).astype(np.uint8)).save(OUT + '.silme.png')                     # QC: silme agirligi


class _P:   # V6 motorunun 'murekkep' toz rengi icin P.img / P.lab / P.merged_parts / P.alpha arayuzu
    img = kf; lab = msym.astype(np.int32); merged_parts = [(1,)]; alpha = alfa_


P = _P
# ======================== V6 MOTORU (poster_video_v6.py, mx0/mx1 satirindan sonrasi, birebir) ========================
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))


def yazim(x0_, x1_, p, yum=10):
    """soldan saga yazilma: p ilerlemesine gore x esiginin solu acik, yumusak kenar"""
    esik = x0_ - yum + (x1_ - x0_ + 2 * yum) * p
    return np.clip((esik - XX) / yum, 0, 1)


def noktalar(m, N):
    ys, xs = np.where(m > 0.35)
    i = rng.choice(len(xs), N, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((N, 2)).astype(np.float32) - 0.5


N = int(os.environ.get('V6_N', '26000'))                 # v6: kalibre (v5: 26000)
BOLGE_PX = int((cv2.dilate((MS > 0.95).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0).sum())   # olcum bolgesi (v6_kalibre)
if os.environ.get('V6_BOLGE_REF'):   # 78 uretim (20 Eki): N = 58000 x bolge alani / CL bolge alani
    N = int(round(float(os.environ.get('V6_N_REF', '58000')) * BOLGE_PX / float(os.environ['V6_BOLGE_REF']) / 100.0) * 100)
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
ALTIN = np.round(INK * 0.55 + np.array([255, 236, 214], np.float32) * 0.45)   # Y1: acik vurgu (kupada ALTIN)
if RENK_MOD == 'murekkep':   # kupada ana toz rengi YESIL = kupanin sembol murekkebi; posterde ayni rol: sembolun kendi rengi
    YESIL = np.median(P.img[np.isin(P.lab, [c[0] for c in P.merged_parts]) & (P.alpha > 0.98)], 0).astype(np.float32)
print(f'toz renkleri ({RENK_MOD}): ana {YESIL.round().tolist()} %78, ALTIN {ALTIN.tolist()} %22', flush=True)
renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, YESIL)
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)

nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
TANE = 0.45                                                 # v5: parcacik bulanikligi sigma (v4 0.9)
# v5 murekkep kurali: yerel toz birikimi
from scipy.ndimage import distance_transform_edt
TARR = gec + 0.38                                           # parcacigin indigi an (uu = 1), tt birimi
dxi = np.clip(np.round(dst[:, 0]).astype(int), 0, VW - 1); dyi = np.clip(np.round(dst[:, 1]).astype(int), 0, VH - 1)
H_TUM = np.zeros((VH, VW), np.float32); np.add.at(H_TUM, (dyi, dxi), 1.0)
CF = cv2.GaussianBlur(H_TUM, (0, 0), 3.0)
iyi = CF > 0.02 * CF[MS > 0.5].max()
II = distance_transform_edt(~iyi, return_indices=True)[1]  # tozun az indigi kenar pikselleri en yakin iyi pikselin oranini alir
F_A, F_B = 0.2, 1.0                                         # (v5 esikleri; v6'da kullanilmaz, kayit icin)
import json as _j
C_EGRI = _j.load(open(os.environ['V6_C'])) if os.environ.get('V6_C') else [ease((k / (nB - 1) - 0.36) / 0.64) for k in range(nB)]
CEK = MS > 0.95                                             # cekirdek sembol pikselleri (olcum)
SIRA = np.argsort(TARR); TS = TARR[SIRA]; H_T = np.zeros((VH, VW), np.float32); k_ = 0
IC = {'kare': [], 'murekkep': [], 'toz_ortusu': [], 'ihlal': []}


def murekkep(tt):
    global k_
    j = int(np.searchsorted(TS, tt, side='right'))
    if j > k_:
        np.add.at(H_T, (dyi[SIRA[k_:j]], dxi[SIRA[k_:j]]), 1.0); k_ = j
    F = (cv2.GaussianBlur(H_T, (0, 0), 3.0) / np.maximum(CF, 1e-6))[II[0], II[1]]
    F = np.clip(F, 0, 1)
    return np.minimum(C_EGRI[min(len(C_EGRI) - 1, int(round(tt * (nB - 1))))], F), F   # v6: min(c(t), F)
KAP8 = KAP.astype(np.uint8)
pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                       '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                       '-preset', 'slow', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
for i in range(nT):
    if i == 0 or i >= nB:
        pr.stdin.write(KAP8.tobytes())
        continue
    tt = i / (nB - 1)
    am = yazim(mx0, mx1, ease(tt)) * WM
    uu = np.clip((tt - gec) / 0.38, 0, 1)
    mk, F = murekkep(tt)                                     # v5: murekkep yalniz toz birikince (v4: ease((tt-0.36)/0.64))
    asym = mk * WS
    IC['kare'].append(i); IC['murekkep'].append(float(mk[CEK].mean())); IC['toz_ortusu'].append(float(F[CEK].mean()))
    IC['ihlal'].append(float((mk[CEK] - F[CEK]).max()))     # > 0 ise bir pikselde murekkep tozun onunde
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
    ok = (xi >= 0) & (xi < VW) & (yi >= 0) & (yi < VH)
    a_ = (par[gor] * np.sin(np.pi * uu[gor]))[ok]
    al = np.zeros((VH, VW), np.float32)
    kat = np.zeros((VH, VW, 3), np.float32)
    np.add.at(al, (yi[ok], xi[ok]), a_)
    for c in range(3):
        np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
    al = cv2.GaussianBlur(al, (0, 0), TANE) * 2.0             # v5: tane boyu yarim (v4 sigma 0.9)
    kat = cv2.GaussianBlur(kat, (0, 0), TANE) * 2.0
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None] * (0 if os.environ.get('TOZSUZ') else 1)   # TOZSUZ=1: yalniz QC (murekkep olusumu)
    pr.stdin.write(np.clip(f * (1 - a3) + rk * a3, 0, 255).astype(np.uint8).tobytes())
    if i % 15 == 0:
        g = time.time() - t0
        print(f'  kare {i}/{nB} %{100 * i // nB} (gecen {g:.0f}s, kalan ~{g / i * (nB - i):.0f}s)', flush=True)
pr.stdin.close(); pr.wait()
print(f'{nT} kare ({nT / FPS:.2f} sn), toz/yazi bitis {BITIS} sn, uretim {time.time() - t0:.0f}s', flush=True)
import json
json.dump({'N': N, 'bolge_px': BOLGE_PX, 'glif': GLIF, 'tane_sigma': {'v4': 0.9, 'v5': TANE}, 'c_egri': [round(float(x), 4) for x in C_EGRI], **IC}, open(OUT + '.ic.json', 'w'))
print('tamam', OUT)
