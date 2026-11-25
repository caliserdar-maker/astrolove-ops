#!/usr/bin/env python3
"""Sunum paftasi: yeni altin logo (kare + yuvarlak) ve 3 header secenegi; her header masaustu (tam) + mobil (resmi olmayan orta %60).
Kullanim: pafta_logo_header.py --logo LOGO_YENI_ALTIN_3000.png --header_dir DIR --out PAFTA.jpg
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(KOK, 'scripts', 'kapak78', 'yd_kart', 'fonts', 'CormorantGaramond.ttf')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logo', required=True); ap.add_argument('--header_dir', required=True); ap.add_argument('--out', required=True)
    g = ap.parse_args()
    W = 3300; f = ImageFont.truetype(FONT, 52); fk = ImageFont.truetype(FONT, 38)
    satir_h = 800 + 120
    H = 120 + 700 + 120 + 3 * (90 + 800 + 30 + 60 + 504 + 60)      # bolum yuksekligi: baslik + masaustu + mobil cerceve
    P = Image.new('RGB', (W, H), (246, 243, 236)); d = ImageDraw.Draw(P)
    d.text((50, 30), 'AstroLoveArt - yeni altin logo ve Etsy header secenekleri (25 Kas 2026)', font=f, fill=(20, 28, 60))
    lg = Image.open(g.logo).convert('RGB').resize((700, 700), Image.LANCZOS)
    P.paste(lg, (50, 120)); d.text((50, 830), 'Logo (kare: Etsy dukkan ikonu)', font=fk, fill=(20, 28, 60))
    mk = Image.new('L', (700, 700), 0); ImageDraw.Draw(mk).ellipse((0, 0, 699, 699), fill=255)
    P.paste(lg, (850, 120), mk); d.text((850, 830), 'Logo (yuvarlak: Instagram, Facebook, TikTok...)', font=fk, fill=(20, 28, 60))
    k = Image.open(g.logo).convert('RGB').resize((180, 180), Image.LANCZOS)
    P.paste(k, (1650, 120)); d.text((1650, 310), 'Etsy gorunum boyu 180 px', font=fk, fill=(20, 28, 60))
    y = 120 + 700 + 120
    for h in 'ABC':
        im = Image.open(os.path.join(g.header_dir, f'HEADER_SECENEK_{h}_3200x800.jpg')).convert('RGB')
        d.text((50, y), f'Secenek {h} - masaustu (3200x800; Etsy resmi oneri 1600x400)', font=f, fill=(20, 28, 60))
        P.paste(im, (50, y + 90))
        mob = im.crop((640, 0, 2560, 800)).resize((1152, 480), Image.LANCZOS)
        y2 = y + 90 + 800 + 30
        d.text((50, y2), f'Secenek {h} - mobil (tahmini gorunen orta %60; Etsy resmi kirpma bilgisi vermiyor)', font=fk, fill=(20, 28, 60))
        fr = Image.new('RGB', (1152 + 24, 480 + 24), (30, 30, 30)); fr.paste(mob, (12, 12)); P.paste(fr, (50, y2 + 60))
        y = y2 + 60 + 520 - 30 + 40
    P = P.crop((0, 0, W, y))
    P.save(g.out, quality=90)
    print(g.out, P.size)


if __name__ == '__main__':
    main()
