#!/usr/bin/env python3
"""YD (1st Anniversary) ilan videosu ORNEGI (Merkez 27 Eki gorev B): poster v7b ile ayni sure ve tarz (6 sn, 30 fps, 1440x1080,
sessiz H.264 crf 17; ilk / son kare kapak; ilk 0,3 sn silme; toz iki kucuk burc glifinden ortak sembole akar, murekkep
min(c(t), F); mesaj soldan saga yazilir; BITIS 5,0 sn, sonra sabit kapak). Sahne = YD kapagi <CIFT>_Y01.jpg (3000x2250, Canva).
Motor: poster_video_v7.py (v7b) 'def vid' satirindan sona kadar BIREBIR kopya (asagida 'V7B MOTORU'); tek fark sonsuz = []
(YD posterinde isimler arasinda sonsuz isareti yok). Yalniz sahne ayristirmasi YD Botanical posterine gore (v7 PosterR / halka
koyu poster varsayar, krem kagitta calismaz):
- poster kutusu: kapakta en buyuk krem kagit parcasi (lum > 185, doygunluk < 60; 25 px kapama), 2000 px genislige buyutulur (v7 gibi).
- murekkep rengi: en buyuk koyu yesil parca (lum < 140, G - R > 8) medyani; parcalar: alfa > 0,4 ve G - R > 5; alfa = yerel kagit (61 px medyan) ile murekkep medyani arasindaki oran (kapak
  pikselleri, yeniden cizim yok). Rengi murekkep medyanindan > 45 uzak parcalar (yapraklar, altin tohumlar) disarida.
- satirlar: alan > 300 parcalar ust kenara gore 40 px bosluk kuraliyla bantlara ayrilir (v7 _halkasiz ile ayni); en buyuk parcanin
  bandi = ortak sembol; ustundeki bantlar (Paper Anniversary) sabit; altindakiler: kucuk burclar, isimler; isimlerin altindaki tum parcalar mesaj (tarih + YEAR ONE).
Kullanim: yd_video.py <y01_kapak.jpg> <cikti_mp4>   (ortam: V7_DOLGU, V6_C, V6_N, V6_BOLGE_REF, V6_N_REF, TOZSUZ v7 ile ayni)"""
import os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

KAPAK, OUT = sys.argv[1:3]
RENK_MOD = 'murekkep'
BITIS = 5.0
VW, VH = 1440, 1080
FPS, SURE, SILME = 30, 6.0, 0.3
rng = np.random.default_rng(11)
t0 = time.time()
_src = None

# ---------- YD sahnesi: krem kagit kutusu, murekkep alfasi, satir bantlari
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
kf = kap_src.astype(np.float32); lum_ = kf @ np.float32([0.299, 0.587, 0.114])
kag = ((lum_ > 185) & (kf.max(2) - kf.min(2) < 60)).astype(np.uint8)
kag = cv2.morphologyEx(kag, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(kag, 8)
bi = 1 + int(np.argmax(st_[1:, 4]))
x0, y0, cw, ch = (int(v) for v in st_[bi, :4]); x1, y1 = x0 + cw, y0 + ch
if st_[bi, 4] < 0.08 * kag.size:
    raise SystemExit(f'krem kagit bulunamadi (en buyuk parca {st_[bi, 4]} px)')


class PosterYD:
    def __init__(self, img):
        self.img = img.astype(np.float32); self.h, self.w = img.shape[:2]
        lum = self.img @ np.float32([0.299, 0.587, 0.114])
        lbg = cv2.medianBlur(np.clip(img, 0, 255).astype(np.uint8), 61).astype(np.float32) @ np.float32([0.299, 0.587, 0.114])
        koyu = ((lum < 140) & (self.img[..., 1] - self.img[..., 0] > 8)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(koyu, 8)
        en = 1 + int(np.argmax(st[1:, 4]))
        self.ink_rgb = np.median(self.img[lab == en], 0)
        il = float(self.ink_rgb @ np.float32([0.299, 0.587, 0.114]))
        self.alpha = np.clip((lbg - lum) / np.maximum(lbg - il, 1.0), 0, 1).astype(np.float32)
        # ince satirlar (tarih, YEAR ONE) kapakta ~1274 px posterde yumusak: parcalar alfa > 0,4 ve yesil tonla
        ink = ((self.alpha > 0.4) & (self.img[..., 1] - self.img[..., 0] > 5)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
        keep = np.zeros(n, bool)
        for i in range(1, n):
            if st[i, 4] > 50 and np.abs(np.median(self.img[lab == i], 0) - self.ink_rgb).max() <= 45:
                keep[i] = True
        self.lab = np.where(keep[lab], lab, 0).astype(np.int32)
        self.comps = [(i, *(int(v) for v in st[i])) for i in range(1, n) if keep[i]]
        self._parts()

    @staticmethod
    def _union(cs):
        bx0 = min(c[1] for c in cs); by0 = min(c[2] for c in cs)
        bx1 = max(c[1] + c[3] for c in cs); by1 = max(c[2] + c[4] for c in cs)
        return (-1, bx0, by0, bx1 - bx0, by1 - by0, sum(c[5] for c in cs))

    def _parts(self):
        Wp = self.w
        comps = sorted(self.comps, key=lambda c: -c[5])
        bands = []
        for c in sorted([c for c in comps if c[5] > 300], key=lambda c: c[2]):
            if bands and c[2] <= bands[-1]['y1'] + 40:
                bands[-1]['cs'].append(c); bands[-1]['y1'] = max(bands[-1]['y1'], c[2] + c[4])
            else:
                bands.append({'cs': [c], 'y1': c[2] + c[4]})
        i = next(k for k, b in enumerate(bands) if comps[0] in b['cs'])
        sym = list(bands[i]['cs'])
        sx0 = min(c[1] for c in sym); sy0 = min(c[2] for c in sym)
        sx1 = max(c[1] + c[3] for c in sym); sy1 = max(c[2] + c[4] for c in sym)
        ids = {c[0] for c in sym}
        sym += [c for c in comps if c[0] not in ids and c[5] <= 300 and sx0 < c[1] + c[3] / 2 < sx1 and sy0 < c[2] + c[4] / 2 < sy1]
        self.merged_parts = sym
        self.merged = self._union(sym)
        alt = bands[i + 1:]
        if len(alt) < 3:
            raise RuntimeError(f'YD: beklenen en az 3 satir (burclar, isimler, mesaj), bulunan {len(alt)}')
        left = [c for c in alt[0]['cs'] if c[1] + c[3] / 2 < Wp / 2]
        right = [c for c in alt[0]['cs'] if c[1] + c[3] / 2 >= Wp / 2]
        if not left or not right:
            raise RuntimeError('YD: sol veya sag kucuk burc bulunamadi')
        self.sign_a, self.sign_b = self._union(left), self._union(right)
        self.names_row = self._union(alt[1]['cs'])
        # mesaj = isim satirinin altindaki tum murekkep parcalari (tarih + YEAR ONE; v7'de isimlerin altindaki tum bantlar).
        # YEAR ONE harfleri bu olcekte alan < 300 (bant esigi), bu yuzden bantla degil parca ust kenariyla
        ny1 = self.names_row[2] + self.names_row[4]
        self.msg_row = self._union([c for c in comps if c[2] > ny1])
        print(f'YD ayristirma: ust sabit bant {i}, sembol {len(sym)} parca ({sx0},{sy0})-({sx1},{sy1}), alt bant {len(alt)}, '
              f'murekkep {self.ink_rgb.round().tolist()}', flush=True)


s_ = 2000 / cw
P = PosterYD(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC).astype(np.float32))


# ---------- V7B MOTORU (poster_video_v7.py 'def vid' satirindan sona kadar birebir; yalniz sonsuz = [])
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
sonsuz = []   # YD: isimler arasinda sonsuz isareti yok (v7: parcalar(P.names_row, merkez +-0,08 W))
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
# v7b (26 Eki): bos hal KAPAKTAKI posterin kendi piksellerinden (POSTER_SRC yalniz maske icin). Kaynak ile Canva kapagi
# arasindaki kucuk keskinlik/konum farki (ort 2,65) BASE = KAP + (bos - P.img) farkinda sembolu hayalet olarak birakiyordu.
P_KAP = cv2.resize(kap_src[y0:y1, x0:x1], (P.w, P.h), interpolation=cv2.INTER_CUBIC).astype(np.float32) if _src else P.img
hi = cv2.resize(np.clip(P_KAP, 0, 255).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_AREA)
if os.environ.get('V7_DOLGU') == 'nk':
    # v7 toplu 2. iterasyon (Serdar 26 Eki): Telea yalniz bolge sinirindan doldurur; 18 FAIL ciftte dolgu sembolun icinden gorunen
    # gercek zeminden mavi / acik (TAURUS_VIRGO R-B -42,35 / -41,14). Normalize Gauss: bilinmeyen bolge disindaki (ve sembolun ic
    # bosluklarindaki) tum zemin pikselleri agirlikli ortalamayla; sigma kucukten buyuge, agirlik toplami >= 0,25 olan ilk olcek.
    hmk = cv2.dilate(hm, np.ones((3, 3), np.uint8)) > 0
    w = (~hmk).astype(np.float32)
    hf = hi.astype(np.float32); dol = hf.copy(); kalan = hmk.copy()
    for sg in (6, 12, 24, 48, 96):
        den = cv2.GaussianBlur(w, (0, 0), sg)
        nk = cv2.GaussianBlur(hf * w[..., None], (0, 0), sg) / np.maximum(den, 1e-6)[..., None]
        ok = kalan & (den >= 0.25)
        dol[ok] = nk[ok]; kalan &= ~ok
    if kalan.any():
        dol[kalan] = nk[kalan]
    bos = cv2.resize(dol, (P.w, P.h), interpolation=cv2.INTER_CUBIC)
else:
    bos = cv2.resize(cv2.inpaint(hi, cv2.dilate(hm, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32),
                     (P.w, P.h), interpolation=cv2.INTER_CUBIC)
KAP = np.clip(np.round(cv2.resize(kap_src, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)), 0, 255)
FULL = KAP
BASE = np.clip(KAP + vid((bos - P_KAP) * R_p[..., None]), 0, 255)
MS, MG, MM = vid(MS_p), vid(MG_p), vid(MM_p)
WS, WM = np.clip(vid(RS_p), 0, 1), np.clip(vid(RM_p), 0, 1)      # karisim agirliklari (kupada maske = katman farki)
MM = cv2.dilate(MM, np.ones((3, 3), np.uint8))
XX = np.arange(VW, dtype=np.float32)[None, :].repeat(VH, 0)
print(f'poster kapakta {x0},{y0} {cw}x{ch} oran {ch / cw:.3f}; sonsuz {len(sonsuz)} parca, mesaj {len(mes)} parca', flush=True)
GLIF = {'sign_a': [int(v) for v in P.sign_a[1:5]], 'sign_b': [int(v) for v in P.sign_b[1:5]], 'poster_w': int(P.w),
        'sonsuz': [[int(v) for v in c[1:5]] for c in sonsuz], 'halka_alti_sembol_parcasi': getattr(P, 'halka_alti', [])}   # QC (78 uretim): glif ve sonsuz yerleri (poster 2000 px olcegi)
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
