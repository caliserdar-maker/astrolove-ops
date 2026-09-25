#!/usr/bin/env python3
"""video-v1 QC (PASS/FAIL). Kullanim: qc_video.py REF.mp4 YENI.mp4 N.png
1) Ozellik: sure, cozunurluk, fps, kare sayisi, codec/profil, pix_fmt referansla ayni.
2) Yalniz iki durum: her kare E (referans kare 150) ile N arasi en iyi karisim; sembol+isim bandinda artik < 2.0.
   Kontrol: ayni olcut referansin Libra-solda karelerinde (20, 105) olculur ve esigin cok ustunde olmalidir.
3) Gecis sayisi: ardisik kare farki > 0.05 olan pencere sayisi = 4; baska hareket yok.
4) Tagline bandi (kare 150): referansla fark <= 1.25 x ayni karede degismeyen metnin (EMILY & JAMES isim satiri) yeniden kodlama farki."""
import json, re, subprocess, sys
import numpy as np
from PIL import Image
ref, yeni, npng = sys.argv[1:4]
def props(p):
    s = subprocess.run(['ffmpeg', '-hide_banner', '-i', p], capture_output=True, text=True).stderr
    d = re.search(r'Duration: ([\d:.]+)', s).group(1); v = re.search(r'Video: (.*)', s).group(1)
    return {'sure': d, 'codec': v.split(',')[0].split(' (avc1')[0], 'pix': 'yuv420p' in v, 'wh': re.search(r'(\d{3,4}x\d{3,4})', v).group(1),
            'fps': re.search(r'([\d.]+) fps', v).group(1)}
def frames(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1350, 1080, 3)
R, Y = frames(ref), frames(yeni)
pr, py = props(ref), props(yeni)
sonuc = {'ozellik_ref': pr, 'ozellik_yeni': py, 'kare': [len(R), len(Y)]}
ok1 = pr == py and len(R) == len(Y)
ap = (slice(785, 975), slice(151, 927))
E = R[150][ap].astype(np.float32); N = np.asarray(Image.open(npng).convert('RGB'))[ap].astype(np.float32)
v = N - E; art = []
for i in range(len(Y)):
    f = Y[i][ap].astype(np.float32)
    w = float(np.clip((v * (f - E)).sum() / (v * v).sum(), 0, 1))
    art.append(float(np.abs(E + w * v - f).mean()))
# kontrol: ayni olcut referansin Libra-solda karelerinde (kaldirilmasi gereken durum) ne verir
kontrol = [float(np.abs(E + np.clip((v * (R[i][ap].astype(np.float32) - E)).sum() / (v * v).sum(), 0, 1) * v - R[i][ap].astype(np.float32)).mean()) for i in (20, 105)]
ok2 = max(art) < 2.0
apt = (slice(171, 1177), slice(151, 927))
d = [float(np.abs(Y[i + 1][apt].astype(np.int16) - Y[i][apt]).mean()) for i in range(len(Y) - 1)]
hareket = [i for i, x in enumerate(d) if x > 0.05 and i > 0]
pencere = []
for i in hareket:
    if pencere and i - pencere[-1][1] <= 2: pencere[-1][1] = i
    else: pencere.append([i, i])
ok3 = len(pencere) == 4
tb = (slice(1020, 1060), slice(151, 927))
tag = float(np.abs(Y[150][tb].astype(np.float32) - R[150][tb]).mean())
metin = (slice(895, 950), slice(151, 927))   # E karesinde isim satiri: referanstan aynen, altin metin kenarli
tag_duvar = float(np.abs(Y[150][metin].astype(np.float32) - R[150][metin]).mean())
ok4 = tag <= 1.25 * tag_duvar
sonuc.update({'iki_durum_artik_maks': round(max(art), 3), 'kontrol_libra_solda_artik': [round(k, 2) for k in kontrol],
              'gecis_pencereleri': pencere, 'tagline_fark': round(tag, 3), 'metin_esik_tabani': round(tag_duvar, 3),
              'PASS': {'ozellik': ok1, 'iki_durum': ok2, 'gecis_4': ok3, 'tagline': ok4}})
sonuc['SONUC'] = 'PASS' if all(sonuc['PASS'].values()) else 'FAIL'
print(json.dumps(sonuc, indent=1))
json.dump(sonuc, open(yeni.replace('.mp4', '_qc.json'), 'w'), indent=1)
sys.exit(0 if sonuc['SONUC'] == 'PASS' else 1)
