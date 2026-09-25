#!/usr/bin/env python3
"""video-v1 77 cift QC (PASS/FAIL). Kullanim: qc_cift.py VIDEO.mp4  (yaninda *_meta.json ve *_EJ|IN|AM.png)
Zamanlama: her kare sembol+isim bandinda uc cift (EJ-IN, IN-AM, AM-EJ) izdusumu; gorunur gecis = onceki durumdan u >= 0.05.
PASS: 1080x1350, 30 fps, h264 High, yuv420p; 378 kare; ilk gorunur gecis kare 6 (0,20 sn); 9 gecis EJ->IN->AM->EJ x3, aralik 42 kare;
planli sabit karelerde ardisik fark < 0.102 (v3'te olculen sikistirma gurultusu 0.0819 x 1.25); uc durum artigi < 2.0.
Tagline (Serdar): uc sabit kareden taban y farki <= 1 px ve altin kanal ortalama farki <= 6. Dongu dikisi olculur, kapi degil (Serdar kabul)."""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tagline_olc import olc
v = sys.argv[1]; base = v[:-4]
s = subprocess.run(['ffmpeg', '-hide_banner', '-i', v], capture_output=True, text=True).stderr
vi = re.search(r'Video: (.*)', s).group(1)
oz = {'codec': 'h264 (High)' in vi, 'pix': 'yuv420p' in vi, 'wh': '1080x1350' in vi, 'fps': ' 30 fps' in vi}
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
Y = np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3); n = len(Y)
meta = json.load(open(base + '_meta.json')); plan = meta['plan']
ap = (slice(785, 975), slice(151, 927))
S = {k: np.asarray(Image.open(f'{base}_{k}.png').convert('RGB'))[ap].astype(np.float32) for k in ('EJ', 'IN', 'AM')}
CIFT = [('EJ', 'IN'), ('IN', 'AM'), ('AM', 'EJ')]
lab, art = [], []
for f in Y:
    f = f[ap].astype(np.float32); best = None
    for x, y in CIFT:
        d = S[y] - S[x]; dd = float((d * d).sum())
        u = float(np.clip((d * (f - S[x])).sum() / dd, 0, 1)) if dd > 0 else 0.0
        r = float(np.abs(S[x] + u * d - f).mean())
        if best is None or r < best[3]: best = (x, y, u, r)
    lab.append(best); art.append(best[3])
dur = lambda b: b[0] if b[2] < 0.05 else (b[1] if b[2] > 0.95 else None)
gec, onceki, i = [], dur(lab[0]), 1
while i < n:
    d = dur(lab[i])
    if d is None or d != onceki:
        x, y = lab[i][0], lab[i][1]; j = i
        while j < n and dur(lab[j]) != y: j += 1
        gec.append({'yon': f'{x}->{y}', 'bas_kare': i, 'bas_sn': round(i / 30, 3)}); onceki, i = y, j + 1
    else: i += 1
fd = np.array([0.0] + [float(np.abs(Y[k][ap].astype(np.int16) - Y[k - 1][ap]).mean()) for k in range(1, n)])
sabit = [k for k in range(1, n) if plan[k][0] == plan[k][1] and plan[k - 1][0] == plan[k - 1][1]]
ESIK = round(1.25 * 0.0819, 4)
tag = {}
for st in ('EJ', 'IN', 'AM'):
    k = [q for q, p in enumerate(plan) if p == [st, st, 0.0]]; r = olc(Y[k[len(k) // 2]]); tag[st] = {'taban_y': r['taban_y'], 'altin_ort': r['altin_ort'], 'genislik': r['genislik']}
taban_f = max(t['taban_y'] for t in tag.values()) - min(t['taban_y'] for t in tag.values())
altin_f = max(max(t['altin_ort'][c] for t in tag.values()) - min(t['altin_ort'][c] for t in tag.values()) for c in range(3))
ok = {'ozellik': all(oz.values()), 'kare_378': n == 378, 'ilk_gecis_0.20': bool(gec) and gec[0]['bas_kare'] == 6,
      'sira_9': [g['yon'] for g in gec] == [f'{a}->{b}' for a, b in CIFT] * 3,
      'aralik_42': all(gec[q + 1]['bas_kare'] - gec[q]['bas_kare'] == 42 for q in range(len(gec) - 1)),
      'sabit': float(fd[sabit].max()) < ESIK, 'uc_durum': max(art) < 2.0, 'tagline_taban_<=1': taban_f <= 1, 'tagline_altin_<=6': altin_f <= 6}
sonuc = {'cift': meta['cift'], 'gecis_bas_sn': [g['bas_sn'] for g in gec], 'sabit_fark_maks': round(float(fd[sabit].max()), 4),
         'uc_durum_artik': round(max(art), 3), 'tagline': tag, 'tagline_fark': {'taban_px': taban_f, 'altin_kanal': round(altin_f, 1)},
         'dongu_dikisi_bilgi': round(float(np.abs(Y[-1][ap].astype(np.int16) - Y[0][ap]).mean()), 3),
         'PASS': ok, 'SONUC': 'PASS' if all(ok.values()) else 'FAIL'}
json.dump(sonuc, open(base + '_qc.json', 'w'), indent=1)
print(json.dumps({k: sonuc[k] for k in ('cift', 'gecis_bas_sn', 'tagline_fark', 'SONUC')}), [k for k, x in ok.items() if not x])
sys.exit(0 if sonuc['SONUC'] == 'PASS' else 1)
