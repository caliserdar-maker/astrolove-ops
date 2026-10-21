#!/usr/bin/env python3
"""Yil donumu 9:16 sosyal video partisi (v4 kurali, 21 Eki 2026): cift ciktilarini birlestirir. Yazma yok; yalniz dosya.

Girdi (G): <CIFT>/ (yd_reel_v4.py ciktisi: <CIFT>_yd_reel_v4.mp4, OLCUM.txt, OLCUM.json; baslik sigmayan ciftte yalniz OLCUM.txt).
Cikti (OUT): <CIFT>_yd_reel_v4.mp4 (PASS olanlar), KONTAK_ILK_KARE.jpg (ilk kareler yan yana, mp4'ten), OLCUM.txt.
Cikis 0 yalniz tum ciftler PASS ise.
Kullanim: yd_parti_topla.py G OUT CIFT1,CIFT2,...
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
TW, TH, ARA, UST = 540, 960, 24, 96


def ilk_kare(mp4):
    b = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', mp4, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True).stdout
    return Image.fromarray(np.frombuffer(b, np.uint8).reshape(H, W, 3))


def main():
    G, OUT, ciftler = sys.argv[1], sys.argv[2], [c for c in sys.argv[3].split(',') if c]
    os.makedirs(OUT, exist_ok=True)
    try:
        f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
        f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 19)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    sh = Image.new('RGB', (ARA + len(ciftler) * (TW + ARA), UST + TH + ARA), 'white'); dr = ImageDraw.Draw(sh)
    sat, ozet = [], []
    for n, c in enumerate(ciftler):
        d = os.path.join(G, c); mp4 = os.path.join(d, f'{c}_yd_reel_v4.mp4')
        js = os.path.join(d, 'OLCUM.json'); tx = os.path.join(d, 'OLCUM.txt')
        O = json.load(open(js)) if os.path.isfile(js) else {}
        sonuc = O.get('sonuc', 'URETILMEDI' if os.path.isfile(tx) else 'YOK')
        x = ARA + n * (TW + ARA)
        if sonuc == 'PASS' and os.path.isfile(mp4):
            shutil.copy(mp4, os.path.join(OUT, os.path.basename(mp4)))
        if os.path.isfile(mp4):
            sh.paste(ilk_kare(mp4).resize((TW, TH), Image.LANCZOS), (x, UST))
        y = O.get('yerlesim', {})
        renk = (20, 20, 20) if sonuc == 'PASS' else (200, 0, 0)
        dr.text((x, 12), f'{c}  {sonuc}', font=f1, fill=renk)
        if y:
            dr.text((x, 50), f"poster {y.get('poster_genislik')}x{y.get('poster_yukseklik')}, 918 asimi {y.get('poster_918_asimi_px')} px, ara {y.get('ara')}",
                    font=f2, fill=renk)
        ozet.append((c, sonuc, O))
        sat.append(f'===== {c} =====')
        sat += open(tx, encoding='utf-8').read().rstrip('\n').split('\n') if os.path.isfile(tx) else ['OLCUM.txt yok (is calismadi)']
    sh.save(os.path.join(OUT, 'KONTAK_ILK_KARE.jpg'), quality=90)
    n_pass = sum(s == 'PASS' for _, s, _ in ozet)
    bas = [f'YIL DONUMU 9:16 SOSYAL VIDEO PARTI 1 (v4 kurali): {n_pass}/{len(ciftler)} PASS (Metricool/hesap yazma 0)']
    for c, s, O in ozet:
        y = O.get('yerlesim', {}); tz = O.get('toz_2_4sn', {})
        bas.append(f"{c}: {s}" + (f"; poster {y.get('poster_genislik')}x{y.get('poster_yukseklik')} (olcek {O.get('olcek_poster')}), "
                                  f"918 asimi {y.get('poster_918_asimi_px')} px, ara {y.get('ara')}, ust/alt {y.get('ust_bosluk')}/{y.get('alt_bosluk')}; "
                                  f"N {O.get('ilan', {}).get('N')}; toz % " + ', '.join(f"{k}:{v['fark_yuzde']:+.1f}" for k, v in tz.items())
                                  + f"; FAIL kapilar: {[k for k, v in O.get('kapilar', {}).items() if not v]}" if O else ''))
    bas.append('mp4: ' + ', '.join(sorted(f for f in os.listdir(OUT) if f.endswith('.mp4'))))
    open(os.path.join(OUT, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(bas + [''] + sat) + '\n')
    print('\n'.join(bas))
    sys.exit(0 if n_pass == len(ciftler) else 1)


if __name__ == '__main__':
    main()
