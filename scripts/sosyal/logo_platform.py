#!/usr/bin/env python3
"""Yeni altin logo: platform boylari + yuvarlak kirpma kontrolu + altin kiyas ve buyutulmus goz kontrolu gorselleri.

Boylar (kaynak: platformun resmi yardim sayfasi, 25 Kas 2026 kontrol; resmi olcu yoksa yazili):
  Etsy dukkan ikonu 500x500 (help.etsy.com/hc/en-us/articles/115015663347: "recommended size for logos is 500 x 500px")
  Facebook Sayfa profil 320x320 (facebook.com/help/125379114252045: en iyi kalite 320x320, daire kirpilir)
  YouTube 800x800 (support.google.com/youtube/answer/10456525: 98x98 gorunur, en cok 15 MB; 800 resmi DEGIL)
  Instagram, Threads, TikTok, Pinterest 1080x1080 (resmi piksel olcusu YOK; kare, platform kucultur)
QC: her boy kare ve dogru boyutta; altin en uzak noktasi daire yaricapinin <= %90'i (yuvarlak kirpmada guvenli alan).
Kullanim: logo_platform.py --logo LOGO_YENI_ALTIN_3000.png --eski ICON_LIVE_CAPTURE_1254.png --pin PIN_ALTIN_CANCER_LEO.jpg --out DIR
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BOY = {'ETSY_IKON': 500, 'FACEBOOK': 320, 'YOUTUBE': 800, 'INSTAGRAM': 1080, 'THREADS': 1080, 'TIKTOK': 1080, 'PINTEREST': 1080}
RESMI = {'ETSY_IKON', 'FACEBOOK'}                 # oteki boylar resmi sayfada yok (YouTube yalniz 98x98 gosterim yaziyor)
DAIRE = {'FACEBOOK', 'YOUTUBE', 'INSTAGRAM', 'THREADS', 'TIKTOK', 'PINTEREST'}


def altin_r(a):
    m = (a[..., 0].astype(int) - a[..., 2]) > 40
    ys, xs = np.where(m); n = a.shape[0]
    return float((np.sqrt((xs - n / 2) ** 2 + (ys - n / 2) ** 2) / (n / 2)).max())


def main():
    ap = argparse.ArgumentParser()
    for x in ('logo', 'eski', 'pin', 'out'):
        ap.add_argument('--' + x, required=True)
    g = ap.parse_args(); os.makedirs(g.out, exist_ok=True)
    src = Image.open(g.logo).convert('RGB'); S = []
    kont = Image.new('RGB', (len(BOY) * 340 + 20, 400), 'white'); d = ImageDraw.Draw(kont)
    for i, (ad, n) in enumerate(BOY.items()):
        im = src.resize((n, n), Image.LANCZOS)
        yol = os.path.join(g.out, f'LOGO_{ad}_{n}x{n}' + ('' if ad in RESMI else '_RESMI_OLCU_YOK') + '.png'); im.save(yol, optimize=True)
        a = np.asarray(Image.open(yol).convert('RGB')); r = altin_r(a)
        ok = a.shape[:2] == (n, n) and (r <= 0.90 if ad in DAIRE else True)
        S.append({'kapi': f'{ad} {n}x{n}' + (' daire guvenli (altin r <= 0.90)' if ad in DAIRE else ''), 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': f'r {r:.3f}' + ('' if ad in RESMI else ' | boy resmi degil')})
        t = im.resize((300, 300), Image.LANCZOS)
        if ad in DAIRE:
            mk = Image.new('L', (300, 300), 0); ImageDraw.Draw(mk).ellipse((0, 0, 299, 299), fill=255)
            bg = Image.new('RGB', (300, 300), (235, 235, 235)); bg.paste(t, (0, 0), mk); t = bg
            ImageDraw.Draw(t).ellipse((15, 15, 285, 285), outline=(255, 60, 60), width=2)   # %90 guvenli alan
        kont.paste(t, (20 + i * 340, 20)); d.text((20 + i * 340, 335), f'{ad} {n}px  r={r:.2f}', fill='black')
    kont.save(os.path.join(g.out, 'KONTROL_YUVARLAK_KIRPMA.jpg'), quality=92)
    # yan yana altin kiyasi: eski logo | yeni logo | onayli pin altini (ayni olcekte yakin cekim)
    eski = Image.open(g.eski).convert('RGB').resize((3000, 3000), Image.LANCZOS); pin = Image.open(g.pin).convert('RGB')
    k = Image.new('RGB', (1900, 1340), 'white'); dk = ImageDraw.Draw(k)
    k.paste(eski.resize((600, 600)), (20, 60)); k.paste(src.resize((600, 600)), (650, 60)); k.paste(pin.crop((104, 258, 897, 1312)).resize((450, 600)), (1300, 60))
    for i, b in enumerate([(1250, 1000, 1950, 1700)]):
        k.paste(eski.crop(b).resize((600, 600), Image.LANCZOS), (20, 700)); k.paste(src.crop(b).resize((600, 600), Image.LANCZOS), (650, 700))
    k.paste(pin.crop((330, 290, 630, 590)).resize((600, 600), Image.LANCZOS), (1280, 700))
    for x, t in ((20, 'ESKI ALTIN (canli logo)'), (650, 'YENI ALTIN (bu is)'), (1300, 'ONAYLI PIN ALTINI')):
        dk.text((x, 20), t, fill='black')
    dk.text((20, 670), 'Buyutulmus goz kontrolu (orta kesisim, ayni olcek)', fill='black')
    k.save(os.path.join(g.out, 'KIYAS_ESKI_YENI_PIN_ALTIN.jpg'), quality=92)
    for s in S:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}")
    json.dump(S, open(os.path.join(g.out, 'QC_PLATFORM.json'), 'w'), indent=1)
    raise SystemExit(0 if all(s['sonuc'] == 'PASS' for s in S) else 1)


if __name__ == '__main__':
    main()
