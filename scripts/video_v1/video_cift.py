#!/usr/bin/env python3
"""video-v1: 77 cift videosu (Serdar onayli v5 sablonu, 25 Eyl 2026). Girdi: medya-v1 A1_77/<CIFT>/POSTER_EJ|IN|AM.png
(kisisel-v1 kodu, 2400x3000). AM yoksa cikis kodu 3 (BEKLE).
Her durum: referans kare 150 (maket) + poster acikligina cift posteri: v2'de olculen afin (ECC) + kanal bazli ton (Cancer-Libra
kisisel E posteri -> kare 150) + duzgun aydinlatma haritasi (sigma 30; Cancer-Libra'da olculdu: E ort fark 1.77, N capraz 1.54).
Aciklik kenari 3 px asindirilir, 2 px yumusak (cerceve golgesi referanstan kalir).
Zamanlama v5 ile ayni: EJ -> IN -> AM -> EJ, pencere 12 kare (referans egrisi), ilk gorunur gecis 0,20 sn, sabit 30 kare, 378 kare = 12,6 sn.
AM tagline duzeltmesi (Serdar onayli v5 kurali): kisisel-v1 tagline'i kutu merkezine gore yerlestirdigi icin inen harfi olmayan
'You Feel Like Home' EJ'den asagida kalir (olculdu: poster taban 2638 / 2625). AM tagline katmani EJ tabanina kaydirilir (zemin: uc
posterden piksel bazinda en az murekkepli olan); videoda altin seviyesi EJ/IN ortalamasina kanal kazanciyla esitlenir (v5 ile ayni).
Kullanim: video_cift.py REF.mp4 v2_meta.json P_emily_james.png CIFT_DIZINI CIKTI.mp4"""
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image
ref, v2meta, p_ref, cdir, out = sys.argv[1:6]
cdir = Path(cdir)
eksik = [k for k in ('EJ', 'IN', 'AM') if not (cdir / f'POSTER_{k}.png').exists()]
if eksik: print(f'BEKLE: {cdir.name} eksik {eksik}'); sys.exit(3)
t0 = time.time()
FPS, BAS, GECIS, SABIT, TUR, SIRA = 30, 4, 12, 30, 3, ['EJ', 'IN', 'AM']
X0, Y0, X1, Y1 = 151, 171, 927, 1177
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
F = A[150].astype(np.float32)
v2 = json.load(open(v2meta)); Maf = np.array(v2['M'], np.float32)
warp = lambda p: cv2.warpAffine(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), Maf, (1080, 1350), flags=cv2.INTER_AREA)
reg = np.zeros((1350, 1080), bool); reg[Y0:Y1, X0:X1] = True
Wr = warp(p_ref)
ton = [np.polyfit(Wr[..., c][reg], F[..., c][reg], 1) for c in range(3)]
tf = lambda W: np.stack([np.polyval(ton[c], W[..., c]) for c in range(3)], 2)
m = reg.astype(np.float32)[..., None]
Tr = tf(Wr)
G = np.clip(cv2.GaussianBlur(F * m, (0, 0), 30) / np.maximum(cv2.GaussianBlur(Tr * m, (0, 0), 30), 1), 0.6, 1.6)
al = np.zeros((1350, 1080), np.float32); al[Y0 + 3:Y1 - 3, X0 + 3:X1 - 3] = 1
al = cv2.GaussianBlur(al, (0, 0), 1.0)[..., None]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tagline_olc import olc
from scipy import ndimage
TB0, TB1 = 2480, 2720
def taban_poster(P):
    b = P[TB0:TB1, 300:2100]; m = (b[..., 0] - b[..., 2]) > 40
    lab, nn = ndimage.label(ndimage.binary_dilation(m, structure=np.ones((5, 101))))
    m &= lab == (np.argmax(ndimage.sum(m, lab, range(1, nn + 1))) + 1)
    pr = m.sum(1).astype(float); return TB0 + int(np.where(pr > 0.5 * pr.max())[0][-1])
POS = {k: np.asarray(Image.open(cdir / f'POSTER_{k}.png').convert('RGB')).astype(np.float32) for k in SIRA}
tb_ej, tb_am = taban_poster(POS['EJ']), taban_poster(POS['AM']); dy = tb_am - tb_ej
duzeltme = {'taban_poster_EJ': tb_ej, 'taban_poster_AM_once': tb_am, 'kaydirma_px': dy}
if dy:
    bant = {k: POS[k][TB0 - 40:TB1 + 40] for k in SIRA}
    rb = np.stack([bant[k][..., 0] - bant[k][..., 2] for k in SIRA]); sec = np.argmin(rb, 0)
    zemin = np.choose(sec[..., None], [bant[k] for k in SIRA])
    w = np.clip((rb[2] - 20) / 60, 0, 1)[..., None]            # AM murekkep agirligi
    ks = lambda X: np.roll(X, -dy, axis=0)
    yeni = zemin * (1 - ks(w)) + ks(bant['AM']) * ks(w)
    POS['AM'] = POS['AM'].copy(); POS['AM'][TB0 - 40:TB1 + 40] = yeni
    duzeltme['taban_poster_AM_sonra'] = taban_poster(POS['AM'])
warpP = lambda P: cv2.warpAffine(P, Maf, (1080, 1350), flags=cv2.INTER_AREA)
ST = {k: F * (1 - al) + np.clip(G * tf(warpP(POS[k])), 0, 255) * al for k in SIRA}
# altin seviyesi (v5 kurali): AM tagline cekirdek altin ortalamasi EJ/IN ortalamasina, yalniz murekkep agirligiyla
hedef = (np.array(olc(ST['EJ'])['altin_ort']) + np.array(olc(ST['IN'])['altin_ort'])) / 2
simdi = np.array(olc(ST['AM'])['altin_ort']); kaz = hedef / simdi
b_ = np.zeros((1350, 1080), np.float32); b_[995:1075, X0 + 8:X1 - 8] = 1; b_ = cv2.GaussianBlur(b_, (0, 0), 3)[..., None]
wi = np.clip(((ST['AM'][..., 0] - ST['AM'][..., 2]) - 20) / 60, 0, 1)[..., None] * b_
ST['AM'] = ST['AM'] * (1 - wi) + np.clip(ST['AM'] * kaz, 0, 255) * wi
duzeltme.update({'altin_hedef': np.round(hedef, 1).tolist(), 'altin_once': np.round(simdi, 1).tolist(), 'altin_kazanc': np.round(kaz, 4).tolist(),
                 'altin_sonra': olc(ST['AM'])['altin_ort']})
dogrulama = round(float(np.abs(G * Tr - F).mean(2)[Y0 + 3:Y1 - 3, X0 + 3:X1 - 3].mean()), 3)
Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
n = TUR * len(SIRA) * (SABIT + GECIS)
plan, k = [('EJ', 'EJ', 0.0)] * BAS, 0
while len(plan) < n:
    x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
    plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
plan = plan[:n]
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', str(FPS), '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0',
       '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for j, (x, y, w) in enumerate(plan):
    pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
pr.stdin.close(); assert pr.wait() == 0
for kk in SIRA: Image.fromarray(np.clip(np.rint(ST[kk]), 0, 255).astype(np.uint8)).save(out.replace('.mp4', f'_{kk}.png'))
json.dump({'cift': cdir.name, 'kare': n, 'sure_sn': n / FPS, 'sira': SIRA, 'aydinlatma_dogrulama_E_ort': dogrulama, 'am_tagline_duzeltme': duzeltme,
           'plan': [[x, y, round(w, 4)] for x, y, w in plan]}, open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s {cdir.name} kare={n} dogrulama={dogrulama} {duzeltme}', flush=True)
