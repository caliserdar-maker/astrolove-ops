#!/usr/bin/env python3
"""video-v1 v5 (Serdar, 25 Eyl): v4 + ALEXANDER & MIA tagline'i orijinal piksel DEGIL; kisisel-v1 tagline koduyla
(kis_tagline.py: EB Garamond Italic, punto 102, SECENEK 1 altin doku), taban cizgisi EMILY & JAMES ile ayni (poster y 2627).
Tagline tonu: kisisel E tagline'i (P_emily_james) -> orijinal E tagline'i (kare 150) kanal bazli dogrusal uydurma; N'de dogrulanir.\nAltin seviyesi: M cekirdek altin ortalamasi E/N ortalamasina kanal kazanciyla esitlenir (yalniz murekkep agirligi).
v4 aciklamasi:
video-v1 v4 (Serdar karari 25 Eyl 2026): 3 cift doner, sembol sirasi hep Cancer solda.
Durumlar: E = referans kare 150 (EMILY & JAMES, aynen); N = v2 *_N.png (ISABELLA & NOAH);
M = referans kare 20 (ALEXANDER & MIA; tagline 'You Feel Like Home' ORIJINAL piksel) + sembol/isim bandi kisisel-v1
isim koduyla (P_alexander_mia.png, Cancer solda), v2'de olculen afin (ECC) ve ton uydurmasiyla.
Zamanlama v3 ile ayni: pencere 12 kare (0,4 sn, referans egrisi), ilk gorunur gecis kare 6 = 0,20 sn, her durum 30 kare (1,0 sn).
Tur E->N->M->E = 3 x 42 = 126 kare = 4,2 sn; 3 tur = 378 kare = 12,6 sn; video E ile biter (26 + 4 = 30 kare).
Kullanim: video_v5.py REF.mp4 N.png P_alexander_mia.png v2_meta.json CIKTI.mp4 T_M_taban.png P_emily_james.png P_isabella_noah.png"""
import json, subprocess, sys, time
import numpy as np, cv2
from PIL import Image
ref, npng, p_m, v2meta, out, t_m, p_e, p_n = sys.argv[1:9]
t0 = time.time()
FPS, BAS, GECIS, SABIT, TUR, SIRA = 30, 4, 12, 30, 3, ['E', 'N', 'M']
BAND, OPEN = (785, 975), (151, 171, 927, 1177)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
A = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
v2 = json.load(open(v2meta))
Maf = np.array(v2['M'], np.float32); ton = [np.array(t) for t in v2['ton']]
P = np.asarray(Image.open(p_m).convert('RGB')).astype(np.float32)
W = cv2.warpAffine(P, Maf, (1080, 1350), flags=cv2.INTER_AREA)
Tm = np.stack([np.polyval(ton[c], W[..., c]) for c in range(3)], 2)
a = np.zeros((1350, 1080), np.float32); a[BAND[0]:BAND[1], OPEN[0] + 8:OPEN[2] - 8] = 1
a = cv2.GaussianBlur(a, (0, 0), 3)[..., None]
F20 = A[20].astype(np.float32)
Mst = F20 * (1 - a) + Tm * a
# tagline: kisisel katman, ton E'de uydurulur, N'de dogrulanir
TB = (995, 1075)
warp = lambda pn: cv2.warpAffine(np.asarray(Image.open(pn).convert('RGB')).astype(np.float32), Maf, (1080, 1350), flags=cv2.INTER_AREA)
tb = (slice(TB[0], TB[1]), slice(OPEN[0], OPEN[2]))
We, Wn, Wt = warp(p_e), warp(p_n), warp(t_m)
Fe, Fn = A[150].astype(np.float32), A[60].astype(np.float32)
tton = [np.polyfit(We[tb][..., c].ravel(), Fe[tb][..., c].ravel(), 1) for c in range(3)]
tt = lambda X: np.stack([np.polyval(tton[c], X[..., c]) for c in range(3)], 2)
dogrulama_N = float(np.abs(tt(Wn)[tb] - Fn[tb]).mean()); uyum_E = float(np.abs(tt(We)[tb] - Fe[tb]).mean())
b = np.zeros((1350, 1080), np.float32); b[TB[0]:TB[1], OPEN[0] + 8:OPEN[2] - 8] = 1
b = cv2.GaussianBlur(b, (0, 0), 3)[..., None]
Tt = tt(Wt)
# altin seviyesi: M tagline cekirdek altin ortalamasi E ve N'nin (videodaki) ortalamasina kanal bazli kazancla esitlenir;
# kazanc yalniz altin murekkep agirligiyla (R-B 20..80 rampasi) uygulanir, gradyan sekli korunur.
sys.path.insert(0, __import__('os').path.dirname(__file__))
from tagline_olc import olc
hedef = (np.array(olc(A[150])['altin_ort']) + np.array(olc(ST_N := np.asarray(Image.open(npng).convert('RGB')).astype(np.float32))['altin_ort'])) / 2
dene = F20 * (1 - a) + Tm * a; dene = dene * (1 - b) + Tt * b
simdi = np.array(olc(dene)['altin_ort']); kazanc = hedef / simdi
w_ink = np.clip(((Tt[..., 0] - Tt[..., 2]) - 20) / 60, 0, 1)[..., None]
Tt = Tt * (1 - w_ink) + np.clip(Tt * kazanc, 0, 255) * w_ink
Mst = Mst * (1 - b) + Tt * b
ST = {'E': A[150].astype(np.float32), 'N': np.asarray(Image.open(npng).convert('RGB')).astype(np.float32), 'M': Mst}
Image.fromarray(np.clip(np.rint(Mst), 0, 255).astype(np.uint8)).save(out.replace('.mp4', '_M.png'))
kontrol = {'M_disi_fark_F20_F150': round(float(np.abs(F20 - ST['E'])[:BAND[0], OPEN[0]:OPEN[2]].mean()), 4),
           'M_bant_kenar_fark': round(float(np.abs(Tm - F20).mean(2)[BAND[0]:BAND[0] + 6, OPEN[0]:OPEN[2]].mean()), 3),
           'tagline_ton': [np.round(t, 4).tolist() for t in tton], 'tagline_ton_uyum_E': round(uyum_E, 3), 'tagline_ton_dogrulama_N': round(dogrulama_N, 3),
           'altin_hedef_EN': np.round(hedef, 1).tolist(), 'altin_once': np.round(simdi, 1).tolist(), 'altin_kazanc': np.round(kazanc, 4).tolist()}
Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
n = TUR * len(SIRA) * (SABIT + GECIS)
plan, baslar, k = [('E', 'E', 0.0)] * BAS, [], 0
while len(plan) < n:
    x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
    baslar.append(len(plan))
    plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
plan = plan[:n]
assert all(p[:2] == ('E', 'E') for p in plan[-(SABIT - BAS):])
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-video_size', '1080x1350', '-framerate', str(FPS), '-i', '-',
       '-an', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '14', '-x264-params', f'keyint={n}:min-keyint={n}:scenecut=0',
       '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', '-movflags', '+faststart', out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for j, (x, y, w) in enumerate(plan):
    pr.stdin.write(np.clip(np.rint(ST[x] * (1 - w) + ST[y] * w), 0, 255).astype(np.uint8).tobytes())
    if (j + 1) % 126 == 0:
        el = time.time() - t0; print(f'kare {j+1}/{n} %{100*(j+1)/n:.0f} gecen {el:.0f}s kalan ~{el/(j+1)*(n-j-1):.0f}s', flush=True)
pr.stdin.close(); assert pr.wait() == 0
json.dump({'kare': n, 'sure_sn': n / FPS, 'sira': SIRA, 'egri': [round(float(e), 4) for e in egri], 'pencere_baslari': baslar,
           'kontrol': kontrol, 'tagline_M': 'You Feel Like Home (kisisel-v1, taban = E)', 'plan': [[x, y, round(w, 4)] for x, y, w in plan]},
          open(out.replace('.mp4', '_meta.json'), 'w'), indent=1)
print(f'bitti {time.time()-t0:.0f}s kare={n} sure={n/FPS:.2f}s pencereler={baslar} {kontrol}', flush=True)
