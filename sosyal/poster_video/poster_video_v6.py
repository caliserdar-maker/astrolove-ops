#!/usr/bin/env python3
"""Poster ilan videosu v6 (Serdar 19 Eki, v5'ten): toz miktari ve murekkep gecisi kupa V6 videosuna (video6b, N 10400,
sigma 0.45) gore ayarlanir; gerisi v5 ile ayni (altin toz, sigma 0.45, zamanlama, silinme, yollar, mesaj, 6 sn, 1440x1080).
 - parcacik sayisi: ortam V6_N (v6_kalibre.py, sembol alanina gore toz yogunlugu kupa ile ayni olacak sekilde hesaplar)
 - murekkep: piksel basina min(c(t), F) (F = yerel toz birikimi; murekkep tozun onune gecmez); c(t) kare basina egri,
   ortam V6_C (json liste, kare 0..nB-1; yoksa kupanin murekkep egrisi ease((tt - 0.36) / 0.64)); v6_kalibre.py c'yi gorunen
   oran kupa V6 ile ayni olacak sekilde duzeltir.
Kaynak aciklama (v5):
Poster ilan videosu v5 (Serdar 19 Eki, v4 ana dosyadan; df252d7): yalniz uc degisiklik, gerisi v4 ile ayni:
 (1) toz 5 kat: N 5200 -> 26000; (2) tane boyu yarim: parcacik bulanikligi GaussianBlur sigma 0.9 -> 0.45 (al ve kat; FWHM
 2,12 -> 1,06 px; *2.0 carpani ve 0.9 ust siniri ayni); (3) sembol murekkebi tozdan once belirmez: her pikselin cevresine
 (sigma 3 px) inen tozun birikim orani F(t) = inen / toplam; murekkep F 0,2'yi gecmeden acilmaz, sonra dogrusal (F - 0,2) / 0,8;
 tum toz tt = 1,0'da (5,0 sn) inmis olur -> sembol en gec 5,0 sn'de tam. Mesaj yazimi, zamanlama, yollar, renk (murekkep =
 altin) ayni. Kaynak aciklama (v4):
Poster ilan videosu v4 (Serdar 19 Eki): YAYINDAKI kupa ilan videosunun (4598525642, Orchard Cancer & Libra) BIREBIR aynisi;
tek fark sahne = poster kapagi (4:3, 1440x1080). Kupa uretici: kupa-orchard dali kupa_orchard/kod/video6b.py (canli dosyayla
kare kare karsilastirma: poster-video-v4 is akisi). Asagidaki akis, sayilar ve formuller video6b.py ile ayni (satir satir):
6 sn, 30 fps, sessiz H.264 crf 17; ilk ve son kare = kapak; ilk 0,3 sn sembol ve mesaj yumusakca kaybolur; toz (5200, rng 11,
gecikme 0.62, yay 8-24 px, %22 altin / %78 yesil, parlaklik 0.55-1.0, bulaniklik 0.9 x 2.0) iki kucuk burc isaretinden (ve
posterde isimler arasindaki sonsuzluktan) akar; sembol ilk varislarla sifirdan yumusakca olusur, mesaj soldan saga yazilir;
toz ve mesaj BITIS (5,0 sn) aninda biter; sonra kapak sabit.
Degisen (yalniz sahne): kupada katmanlar baskidan (full/basem/nosym/noglif/nomes) gelir; posterde ayni katmanlar kapaktaki
posterden olculur: sembol, glif + sonsuzluk ve mesaj maskeleri PosterR (altin alfa); bos hal = kapak + (sembolsuz ve
mesajsiz poster - poster), sembolsuz/mesajsiz poster = kapaktaki posterin kendi pikselleriyle klasik Telea inpaint (yapay zeka
yok). Karisim agirligi maskenin yumusak bolgesi (bos hal yalniz bu bolgede kapaktan farkli; BITIS'te tam kapak).
Toz rengi: kupada %78 YESIL (22,60,36) = kupanin sembol murekkebi (Orange Blossom 10,40,24), %22 ALTIN (196,150,64).
'murekkep' (varsayilan): ayni rol posterde -> %78 posterin sembol murekkebi (olculen medyan), %22 ayni ALTIN.
'yesil': kupa sabitleri aynen.
Kullanim: python3 -I poster_video_v4.py <kapak.jpg> <cikti_mp4> [murekkep|yesil]"""
import os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import pin_uret as PU

KAPAK, OUT = sys.argv[1:3]
RENK_MOD = sys.argv[3] if len(sys.argv) > 3 else 'murekkep'   # murekkep: toz = posterin sembol murekkebi (kupada YESIL =
# kupanin murekkebi); yesil: kupanin sabitleri aynen (lacivert posterde toz zor gorunur, olusma egrisi kupadan ayrilir)
BITIS = 5.0
VW, VH = 1440, 1080                                       # kupada V x V = 1080 x 1080; posterde 4:3, ayni yukseklik
FPS, SURE, SILME = 30, 6.0, 0.3
rng = np.random.default_rng(11)
t0 = time.time()

# ---------- poster kapakta (koyu dikdortgen) ve katmanlar (yalniz sahne farki)
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
kf = kap_src.astype(np.float32); lum_ = kf @ np.float32([0.299, 0.587, 0.114])
lac = cv2.morphologyEx((lum_ < 90).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(lac, 8)
bi = 1 + int(np.argmax(st_[1:, 4]))
x0, y0, cw, ch = (int(v) for v in st_[bi, :4]); x1, y1 = x0 + cw, y0 + ch
s_ = 2000 / cw
tmp = OUT + '._poster.png'
Image.fromarray(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC)).save(tmp)
P = PU.PosterR(tmp); os.remove(tmp)


def vid(m):
    c = np.zeros(kap_src.shape[:2] + m.shape[2:], np.float32)
    c[y0:y1, x0:x1] = cv2.resize(m.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA)
    return cv2.resize(c, (VW, VH), interpolation=cv2.INTER_AREA)


def parcalar(kutu, kosul=lambda c: True):
    _, bx, by, bw, bh, _ = kutu
    return [c for c in P.comps if bx <= c[1] + c[3] / 2 <= bx + bw and by <= c[2] + c[4] / 2 <= by + bh and kosul(c)]


def alfa(cs, d=7):
    m = cv2.dilate(np.isin(P.lab, [c[0] for c in cs]).astype(np.uint8), np.ones((d, d), np.uint8))
    return np.clip(P.alpha * m, 0, 1), m


msym = np.isin(P.lab, [c[0] for c in P.merged_parts]).astype(np.uint8)
MS_p = np.clip(P.alpha * cv2.dilate(msym, np.ones((7, 7), np.uint8)), 0, 1)
sonsuz = parcalar(P.names_row, lambda c: abs(c[1] + c[3] / 2 - P.w / 2) < 0.08 * P.w)
MG_p = np.zeros_like(P.alpha)
for s2 in (P.sign_a, P.sign_b):
    _, x, y, w, h, _ = s2
    MG_p[y:y + h, x:x + w] = P.alpha[y:y + h, x:x + w]
MG_p = np.maximum(MG_p, alfa(sonsuz, 5)[0])
mes = parcalar(P.msg_row)
MM_p, mmes = alfa(mes, 5)
# bos hal bolgeleri: sembol + golgesi (31 px), mesaj (11 px); yumusak kenar
RS_p = cv2.GaussianBlur(cv2.dilate(msym, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 5.0)
RM_p = cv2.GaussianBlur(cv2.dilate(mmes, np.ones((11, 11), np.uint8)).astype(np.float32), (0, 0), 2.0)
R_p = np.maximum(RS_p, RM_p)
hm = cv2.resize((R_p > 0.02).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_NEAREST)
hi = cv2.resize(np.clip(P.img, 0, 255).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_AREA)
bos = cv2.resize(cv2.inpaint(hi, cv2.dilate(hm, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32),
                 (P.w, P.h), interpolation=cv2.INTER_CUBIC)
KAP = np.clip(np.round(cv2.resize(kap_src, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)), 0, 255)
FULL = KAP
BASE = np.clip(KAP + vid((bos - P.img) * R_p[..., None]), 0, 255)
MS, MG, MM = vid(MS_p), vid(MG_p), vid(MM_p)
WS, WM = np.clip(vid(RS_p), 0, 1), np.clip(vid(RM_p), 0, 1)      # karisim agirliklari (kupada maske = katman farki)
MM = cv2.dilate(MM, np.ones((3, 3), np.uint8))
XX = np.arange(VW, dtype=np.float32)[None, :].repeat(VH, 0)
print(f'poster kapakta {x0},{y0} {cw}x{ch} oran {ch / cw:.3f}; sonsuz {len(sonsuz)} parca, mesaj {len(mes)} parca', flush=True)
GLIF = {'sign_a': [int(v) for v in P.sign_a[1:5]], 'sign_b': [int(v) for v in P.sign_b[1:5]], 'poster_w': int(P.w),
        'sonsuz': [[int(v) for v in c[1:5]] for c in sonsuz]}   # QC (78 uretim): glif ve sonsuz yerleri (poster 2000 px olcegi)
_g = [cv2.resize(P.alpha[y:y + h, x:x + w].astype(np.float32), (64, 64), interpolation=cv2.INTER_AREA) for _, x, y, w, h, _ in (P.sign_a, P.sign_b)]
_g = [(g - g.mean()) / (g.std() + 1e-6) for g in _g]
GLIF['benzerlik'] = round(float((_g[0] * _g[1]).mean()), 3)   # iki glifin NCC'si (ayni burcta yuksek olmali)
Image.fromarray(((MS > 0.95) * 255).astype(np.uint8)).save(OUT + '.sembol_maske.png')   # QC: cekirdek sembol pikselleri


def kapsam(m):
    ys, xs = np.where(m > 0.2)
    return xs.min(), xs.max()


mx0, mx1 = kapsam(MM)
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
