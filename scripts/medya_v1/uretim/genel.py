#!/usr/bin/env python3
"""Ciftten bagimsiz 4 genel kart (Serdar, 25 Eyl): onayli Kova-Kova kart stilinden, ust etiket yalniz ASTROLOVE,
burc sembolu / cift adi yok. Kaynak: out/card02, 06, 08, 10 (onayli Kova-Kova). Cikti: paket/GENEL/*.png"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
import master as M, textlayer as T
from cards import BG
OUT = M.ROOT / 'paket/GENEL'; OUT.mkdir(parents=True, exist_ok=True)
log = {}

def etiket(card, n):
    """'ASTROLOVE / AQUARIUS + AQUARIUS' -> 'ASTROLOVE': ASTROLOVE kelimesi olculur, satir silinir, ayni yere yeniden yazilir."""
    p = T.fit(card, (130, 85, 385, 130), 'ASTROLOVE', 'mont', BG, (500,), sub=True)
    card = card.copy(); card[80:140, 130:1000] = BG
    card = T.draw_with(card, p, 'ASTROLOVE', x=p['ox'], base=p['oy'] + p['base0'])
    log.setdefault(n, {})['etiket_rms'] = round(float(np.sqrt(p['mse'])), 1)
    return card, p

def satir(card, n, p, metin, x, base):
    log.setdefault(n, {}).setdefault('satirlar', []).append(metin)
    return T.draw_with(card, p, metin, x=x, base=base)

def kart1():
    c = M.arr('out/card02.png'); c, _ = etiket(c, 1)
    # lacivert bant: panelin sembol satirlari (707-862, gold) DISINDA kalan kismi (isim + tagline); silme yok, kirpma
    Y0 = 950; band = c[Y0:1768, 145:2855].copy()
    c[536:1768, 145:2855] = BG
    c[560:560 + band.shape[0], 145:2855] = band
    yb = 560 + band.shape[0]
    # alt metin: kartin alt yazi olcusu (Montserrat) 'Personalize the names...' satirindan olculur
    ps = T.fit(c, (140, 325, 1500, 395), 'Personalize the names and the line beneath them.', 'mont', BG, (500,))
    c[1880:2070, 130:2870] = BG   # NAMES / YOUR MESSAGE bloklari
    x = ps['ox']; b1 = yb + 260
    c = satir(c, 1, ps, 'Your two names replace the zodiac names on the poster.', x, b1)
    c = satir(c, 1, ps, 'Names: up to 11 letters. Message: up to 35 characters.', x, b1 + 90)
    log[1]['bant'] = [145, 560, 2855, yb]; log[1]['alt_metin_rms'] = round(float(np.sqrt(ps['mse'])), 1)
    return c

def kart2():
    c = M.arr('out/card08.png'); c, _ = etiket(c, 2); return c

def kart3():
    c = M.arr('out/card06.png'); c, _ = etiket(c, 3)
    c[560:1860, 150:1240] = BG   # kucuk poster + golgesi yerine bosluk (Serdar: sade doku veya bosluk); olculen golge 176-1183 x 592-1823
    # sag sutunu (olculen bbox x 1362-2330) karta ortala
    blk = c[540:1810, 1330:2360].copy(); c[540:1810, 1330:2360] = BG
    dx = 1500 - (1362 + 2330) // 2
    c[540:1810, 1330 + dx:2360 + dx] = blk
    log.setdefault(3, {}).update(poster_alani='bos (BG)', sutun_kaydirma_dx=int(dx))
    return c

def kart4():
    c = M.arr('out/card10.png'); c, _ = etiket(c, 4)
    out, p = T.replace(c, (430, 1215, 1230, 1285), 'the size and fulfilment location.', 'the size and fulfillment location.', 'mont', bg=BG)
    log.setdefault(4, {})['fulfillment_rms'] = round(float(np.sqrt(p['mse'])), 1)
    return out

ADLAR = {1: 'GENEL_1_kisisellestirme', 2: 'GENEL_2_olcu', 3: 'GENEL_3_kagit', 4: 'GENEL_4_siparis'}
for n, f in ((1, kart1), (2, kart2), (3, kart3), (4, kart4)):
    im = Image.fromarray(np.clip(np.rint(f()), 0, 255).astype(np.uint8))
    im.save(OUT / f'{ADLAR[n]}.png'); im.save(OUT / f'{ADLAR[n]}.jpg', quality=95, subsampling=0)
    print(n, ADLAR[n], log.get(n), flush=True)
json.dump(log, open(OUT / 'genel_log.json', 'w'), indent=1)
