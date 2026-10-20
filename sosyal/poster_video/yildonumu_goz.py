#!/usr/bin/env python3
"""Yil donumu goz kontrolu (Serdar karar b, 21 Eki): silme izi kapisi dusen ciftler icin silme bolgesinin %200 yakin kirpimi.
Her cift bir satir: KAPAK (ayni yer) | 0,5 sn | 1,5 sn (sembol silinmis, toz henuz bolgeyi kaplamamis / kismen). Bolge = sembol
kutusu (satir JSON glif.sembol_kutu, 2400 px kapakta) + 60 px pay, 1080 videoya olcekli. Sayfa basina en fazla 7 cift.
Kullanim: yildonumu_goz.py <satir_dir> <video_dir> <kapak_dir> <cikti_dir>"""
import glob, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SAT, VID, KAP, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
TS = (0.5, 1.5)


def font(n):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', n)
    except OSError:
        return ImageFont.load_default()


def kare(v, t):
    d = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', v, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True, check=True).stdout
    return Image.fromarray(np.frombuffer(d, np.uint8).reshape(1080, 1080, 3))


ciftler = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(SAT, '*.json'))
                 if not json.load(open(f))['kapi'].get('silme_izi_yok', True))
satir = []
for c in ciftler:
    r = json.load(open(os.path.join(SAT, f'{c}.json')))
    x0, y0, x1, y1 = r['glif']['sembol_kutu']; s = 1080 / r['glif']['poster_w']; p = 60
    kut = tuple(int(round(v * s)) for v in (x0 - p, y0 - p, x1 + p, y1 + p))
    kap = Image.open(os.path.join(KAP, f'{c}.jpg')).convert('RGB').resize((1080, 1080), Image.LANCZOS)
    v = os.path.join(VID, f'{c}_yd_video.mp4')
    ims = [kap.crop(kut)] + [kare(v, t).crop(kut) for t in TS]
    ims = [im.resize((im.width * 2, im.height * 2), Image.LANCZOS) for im in ims]
    iz = r['silme_izi']
    satir.append((c, ims, f"doku {iz['doku_std_orani']}  parlaklik {iz['parlaklik_farki']:+.2f}"))
basl = ['KAPAK (ayni yer)', '0,5 sn', '1,5 sn']
for sayfa in range(0, len(satir), 7):
    sec = satir[sayfa:sayfa + 7]
    cw = max(im.width for _, ims, _ in sec for im in ims); ch = max(im.height for _, ims, _ in sec for im in ims)
    K = Image.new('RGB', (40 + 3 * (cw + 12), 50 + len(sec) * (ch + 56)), (245, 245, 245)); dr = ImageDraw.Draw(K)
    for j, b in enumerate(basl):
        dr.text((40 + j * (cw + 12), 12), f'{b}  (%200)', fill=(0, 0, 0), font=font(26))
    for i, (c, ims, ek) in enumerate(sec):
        y = 50 + i * (ch + 56)
        dr.text((40, y), f'{c}   {ek}', fill=(150, 0, 0), font=font(26))
        for j, im in enumerate(ims):
            K.paste(im, (40 + j * (cw + 12), y + 40))
    K.save(os.path.join(OUT, f'KONTAK_DOKU_{sayfa // 7 + 1}.jpg'), quality=90)
print(f'goz kontrolu: {len(ciftler)} cift, {(len(ciftler) + 6) // 7} sayfa: {" ".join(ciftler)}')
