#!/usr/bin/env python3
"""video-v1 v4 QC (PASS/FAIL). Kullanim: qc_video_v4.py REF.mp4 YENI.mp4 N.png M.png V3_QC.json
Durumlar: E (referans kare 150), N, M. Her kare icin sembol+isim bandinda uc cift (E-N, N-M, M-E) uzerine izdusum; en kucuk artikli
cift ve agirlik u secilir. Gorunur gecis baslangici: onceki sabit durumdan u >= 0.05 olan ilk kare.
Duragan kare esigi: v3'te ayni kodlayici ayarlariyla OLCULEN sikistirma gurultusu (sabit karelerde en buyuk ardisik kare farki) x 1.25.
PASS: ozellik (1080x1350, 30 fps, h264 High, yuv420p) referansla ayni; kare = 378 (12,6 sn); ilk gorunur gecis kare 6 (0,20 sn);
9 gecis, sira E->N->M->E x3, aralik 42 kare (1,4 sn); planli sabit kareler 30 (dikis dahil) ve farki < esik;
dongu dikisi |son - ilk| < esik; her karede uc durum artigi < 2.0; M'de semboller Cancer solda (M bandi E'nin sol sembolune NCC > 0.9)."""
import json, re, subprocess, sys
import numpy as np, cv2
from PIL import Image
ref, yeni, npng, mpng, v3qc = sys.argv[1:6]
def props(p):
    s = subprocess.run(['ffmpeg', '-hide_banner', '-i', p], capture_output=True, text=True).stderr
    v = re.search(r'Video: (.*)', s).group(1)
    return {'codec': v.split(',')[0].split(' (avc1')[0], 'pix': 'yuv420p' in v, 'wh': re.search(r'(\d{3,4}x\d{3,4})', v).group(1),
            'fps': re.search(r'([\d.]+) fps', v).group(1)}, re.search(r'Duration: ([\d:.]+)', s).group(1)
def frames(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
(pr, _), (py, sure) = props(ref), props(yeni)
R, Y = frames(ref), frames(yeni); n = len(Y)
ap = (slice(785, 975), slice(151, 927))
S = {'E': R[150][ap].astype(np.float32), 'N': np.asarray(Image.open(npng).convert('RGB'))[ap].astype(np.float32),
     'M': np.asarray(Image.open(mpng).convert('RGB'))[ap].astype(np.float32)}
CIFT = [('E', 'N'), ('N', 'M'), ('M', 'E')]
lab, art = [], []
for f in Y:
    f = f[ap].astype(np.float32); best = None
    for x, y in CIFT:
        v = S[y] - S[x]; u = float(np.clip((v * (f - S[x])).sum() / (v * v).sum(), 0, 1)); r = float(np.abs(S[x] + u * v - f).mean())
        if best is None or r < best[3]: best = (x, y, u, r)
    lab.append(best); art.append(best[3])
def durum(b): return b[0] if b[2] < 0.05 else (b[1] if b[2] > 0.95 else None)
tablo, onceki, i = [], durum(lab[0]), 1
while i < n:
    d = durum(lab[i])
    if d is None or d != onceki:
        x, y = lab[i][0], lab[i][1]
        j = i
        while j < n and durum(lab[j]) != y: j += 1
        tablo.append({'no': len(tablo) + 1, 'yon': f'{x}->{y}', 'bas_kare': i, 'bas_sn': round(i / 30, 3), 'bitis_kare_95': j,
                      'sure_5_95_sn': round((j - i) / 30, 3)})
        onceki, i = y, j + 1
    else:
        i += 1
AD = {'E': 'EMILY & JAMES', 'N': 'ISABELLA & NOAH', 'M': 'ALEXANDER & MIA'}
gurultu_v3 = json.load(open(v3qc))['sabit_gurultu_maks']; ESIK = round(1.25 * gurultu_v3, 4)
meta = json.load(open(yeni.replace('.mp4', '_meta.json'))); plan = meta['plan']
d = np.array([0.0] + [float(np.abs(Y[k][ap].astype(np.int16) - Y[k - 1][ap]).mean()) for k in range(1, n)])
sabit_kare = [k for k in range(1, n) if plan[k][0] == plan[k][1] and plan[k - 1][0] == plan[k - 1][1]]
sabit_maks = float(d[sabit_kare].max())
seg, cur = [], None
for k, p in enumerate(plan):
    if p[0] == p[1]:
        if cur and cur[1] == k - 1: cur[1] = k
        else: cur = [k, k]; seg.append(cur)
uz = [b - a + 1 for a, b in seg]
dikis = float(np.abs(Y[-1][ap].astype(np.int16) - Y[0][ap]).mean())
# M'de sembol sirasi: sol sembol bolgesi E'nin sol (Cancer) sembolune benzemeli
Mi = [k for k in range(n) if plan[k] == ['M', 'M', 0.0]][10]
g = lambda a: cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
solE = g(R[150][800:885, 300:560].astype(np.float32)); Mg = g(Y[Mi][790:895, 250:620].astype(np.float32))
ncc_sol = float(cv2.minMaxLoc(cv2.matchTemplate(Mg, solE, cv2.TM_CCOEFF_NORMED))[1])
beklenen = [f'{a}->{b}' for a, b in CIFT] * 3
ok = {'ozellik': pr == py, 'kare_378': n == 378, 'ilk_gecis_0.20sn': bool(tablo) and tablo[0]['bas_kare'] == 6,
      'sira_ve_sayi': [t['yon'] for t in tablo] == beklenen, 'aralik_42': all(tablo[k + 1]['bas_kare'] - tablo[k]['bas_kare'] == 42 for k in range(len(tablo) - 1)),
      'sabit_30': all(u == 30 for u in uz[1:-1]) and uz[0] + uz[-1] == 30 and sabit_maks < ESIK,
      'dongu_dikisi': dikis < ESIK, 'uc_durum': max(art) < 2.0, 'M_cancer_solda': ncc_sol > 0.9}
s = {'ozellik_yeni': py, 'sure': sure, 'kare': n, 'gecisler': tablo, 'esik': {'v3_olculen_gurultu': gurultu_v3, 'esik_1.25x': ESIK},
     'sabit_uzunluk': uz, 'sabit_fark_maks': round(sabit_maks, 4), 'dongu_dikisi_fark': round(dikis, 4),
     'uc_durum_artik_maks': round(max(art), 3), 'M_sol_sembol_ncc': round(ncc_sol, 4), 'PASS': ok, 'SONUC': 'PASS' if all(ok.values()) else 'FAIL'}
json.dump(s, open(yeni.replace('.mp4', '_qc.json'), 'w'), indent=1)
print('| # | gecis | gorunur baslangic (kare) | gorunur baslangic (sn) | %5-95 sure (sn) |\n|---|---|---|---|---|')
for t in tablo:
    x, y = t['yon'].split('->'); print(f"| {t['no']} | {AD[x]} -> {AD[y]} | {t['bas_kare']} | {t['bas_sn']:.2f} | {t['sure_5_95_sn']:.2f} |")
print(json.dumps({k: s[k] for k in ('sure', 'kare', 'esik', 'sabit_uzunluk', 'sabit_fark_maks', 'dongu_dikisi_fark', 'uc_durum_artik_maks', 'M_sol_sembol_ncc', 'PASS', 'SONUC')}))
sys.exit(0 if s['SONUC'] == 'PASS' else 1)
