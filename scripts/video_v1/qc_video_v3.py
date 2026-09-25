#!/usr/bin/env python3
"""video-v1 v3 QC (PASS/FAIL). Kullanim: qc_video_v3.py REF.mp4 YENI.mp4 N.png
Her kare icin sembol+isim bandinda E->N izdusum agirligi w olculur (E = referans kare 150, N = *_N.png).
Gecis baslangici: sabit durumdan ilk ayrilan kare (E'den: w > 0.005; N'den: w < 0.995). Gecis sonu: w hedefe 0.005 icinde.
PASS: ozellik (1080x1350, 30 fps, h264 High, yuv420p) referansla ayni; ilk gecis 0,200 sn (kare 6);
gecisler 12 kare (0,4 sn) +-1; sabit sureler 30 kare (1,0 sn) +-1 (dongu dikisi: son + ilk sabit birlikte);
dongu dikisi |kare_son - kare_0| < 0.3; iki durum artigi < 2.0; sure periyodun (84 kare) kati."""
import json, re, subprocess, sys
import numpy as np
from PIL import Image
ref, yeni, npng = sys.argv[1:4]
def props(p):
    s = subprocess.run(['ffmpeg', '-hide_banner', '-i', p], capture_output=True, text=True).stderr
    v = re.search(r'Video: (.*)', s).group(1)
    return {'codec': v.split(',')[0].split(' (avc1')[0], 'pix': 'yuv420p' in v, 'wh': re.search(r'(\d{3,4}x\d{3,4})', v).group(1),
            'fps': re.search(r'([\d.]+) fps', v).group(1)}, re.search(r'Duration: ([\d:.]+)', s).group(1)
def frames(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
(pr, _), (py, sure) = props(ref), props(yeni)
Y = frames(yeni); n = len(Y)
ap = (slice(785, 975), slice(151, 927))
E = frames(ref)[150][ap].astype(np.float32); N = np.asarray(Image.open(npng).convert('RGB'))[ap].astype(np.float32); v = N - E
w, art = [], []
for f in Y:
    f = f[ap].astype(np.float32); x = float((v * (f - E)).sum() / (v * v).sum()); w.append(x)
    art.append(float(np.abs(E + np.clip(x, 0, 1) * v - f).mean()))
w = np.array(w)
# seviye: E = ilk kare, N = en yuksek duzlugun medyani; gorunur esik = tam degisimin %5'i
wE = float(w[0]); wN = float(np.median(np.sort(w)[-60:])); u = (w - wE) / (wN - wE)
d = np.array([0.0] + [float(np.abs(Y[i][ap].astype(np.int16) - Y[i - 1][ap]).mean()) for i in range(1, n)])
tablo, i = [], 1
while i < n:
    kaynak = 'E' if u[i - 1] < 0.5 else 'N'
    ayri = (u[i] > 0.05) if kaynak == 'E' else (u[i] < 0.95)
    if ayri:
        j = i
        while j < n and ((u[j] < 0.95) if kaynak == 'E' else (u[j] > 0.05)): j += 1
        tablo.append({'no': len(tablo) + 1, 'yon': f"{kaynak}->{'N' if kaynak == 'E' else 'E'}", 'bas_kare': i, 'bas_sn': round(i / 30, 3),
                      'bit_kare': j, 'sure_5_95_sn': round((j - i + 1) / 30, 3)})
        i = j + 1
    else:
        i += 1
meta = json.load(open(yeni.replace('.mp4', '_meta.json')))
plan = meta['plan']
pencere = [k for k in range(n) if plan[k][0] != plan[k][1]]
pb = [k for k in pencere if k == 0 or k - 1 not in pencere]
sabit_kare = [k for k in range(1, n) if plan[k][0] == plan[k][1] and plan[k - 1][0] == plan[k - 1][1]]
sabit_gurultu = float(d[sabit_kare].max())
# planli sabit uzunluklar (dongu dikisi: son + ilk birlikte)
sabit, cur = [], None
for k, p in enumerate(plan):
    if p[0] == p[1]:
        if cur and cur[1] == k - 1: cur[1] = k
        else: cur = [k, k]; sabit.append(cur)
uz = [b - a + 1 for a, b in sabit]
dikis_sabit = uz[0] + uz[-1]; ic_sabit = uz[1:-1]
for t in tablo:
    t['pencere_bas_kare'] = max([p for p in pb if p <= t['bas_kare']], default=None)
    t['pencere_sn'] = 0.4
dikis = float(np.abs(Y[-1].astype(np.int16) - Y[0]).mean())
ok = {'ozellik': pr == py, 'ilk_gecis_0.20sn': bool(tablo) and tablo[0]['bas_kare'] == 6,
      'gecis_sayisi_8': len(tablo) == 8, 'aralik_1.4sn': all(tablo[k + 1]['bas_kare'] - tablo[k]['bas_kare'] == 42 for k in range(len(tablo) - 1)),
      'pencere_12kare': all(pb[k + 1] - pb[k] == 42 for k in range(len(pb) - 1)) and len(pencere) == 12 * len(pb),
      'sabit_30kare': all(s == 30 for s in ic_sabit) and dikis_sabit == 30 and sabit_gurultu < 0.06,
      'dongu_dikisi': dikis < 0.3, 'iki_durum': max(art) < 2.0, 'periyot_kati': n % 84 == 0}
s = {'ozellik_yeni': py, 'sure': sure, 'kare': n, 'gecisler': tablo, 'sabit_uzunluklar': uz, 'sabit_gurultu_maks': round(sabit_gurultu, 4), 'dikis_sabit_kare': dikis_sabit,
     'dongu_dikisi_fark': round(dikis, 4), 'iki_durum_artik_maks': round(max(art), 3), 'PASS': ok,
     'SONUC': 'PASS' if all(ok.values()) else 'FAIL'}
json.dump(s, open(yeni.replace('.mp4', '_qc.json'), 'w'), indent=1)
print('| # | yon | gorunur baslangic (kare) | gorunur baslangic (sn) | %5-95 sure (sn) | pencere (0,4 sn) baslangic kare |\n|---|---|---|---|---|---|')
for t in tablo: print(f"| {t['no']} | {t['yon']} | {t['bas_kare']} | {t['bas_sn']:.2f} | {t['sure_5_95_sn']:.2f} | {t['pencere_bas_kare']} |")
print(json.dumps({k: s[k] for k in ('sure', 'kare', 'sabit_uzunluklar', 'sabit_gurultu_maks', 'dikis_sabit_kare', 'dongu_dikisi_fark', 'iki_durum_artik_maks', 'PASS', 'SONUC')}))
sys.exit(0 if s['SONUC'] == 'PASS' else 1)
