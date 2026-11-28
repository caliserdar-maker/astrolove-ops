"""ESKI (sol) / YENI (sag) paftalari: tam boy + 1:1 yakin kesit.
Kullanim: python pafta.py            (1. pilot: yeni/*_YENI_ALTIN.jpg -> PAFTA_ALTIN_PILOT_CL_*)
          python pafta.py pin        (2. gorev: yeni_pin/*_YENI_PIN_ALTIN.jpg -> PAFTA_ALTIN_PIN_CL_*)
          python pafta.py tum        (3. gorev: yeni_tum/*_YENI_TUM_ALTIN.jpg -> PAFTA_ALTIN_TUM_CL_*; yakin kesitte sembol +
                                      halka + poster disi baslik satirlari)"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

MOD = sys.argv[1] if len(sys.argv) > 1 else 'pilot'
KOK = os.path.dirname(os.path.abspath(__file__))
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 56)
FONT_K = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 40)
BAS = (1060, 330, 1940, 440)                       # Canva basligi "CANCER & LIBRA"
# dosya -> (kisa ad, sembol 1:1 kesit, halka 1:1 kesit)
IS = {
    'r01_8749216062': ('01_KAPAK_MB', (1150, 820, 1850, 1520), (1000, 830, 1500, 1130)),
    'r03_8812062435': ('03_KISISEL_MB', (650, 700, 1400, 1400), (500, 640, 1000, 940)),
    'r06_8812065289': ('06_RENKLER_MB_DB_PW', (523, 560, 2470, 1000), (523, 560, 2470, 760)),
    'r07_8812066177': ('07_MB', (1150, 820, 1850, 1520), (1000, 830, 1500, 1130)),
    'r08_8812066995': ('08_DB', (1150, 820, 1850, 1520), (1000, 830, 1500, 1130)),
    'r09_8812067931': ('09_PW', (1150, 820, 1850, 1520), (950, 700, 1450, 1000)),
}
if MOD == 'tum':
    IS['r10_8764250162'] = ('10_WP_BASLIK', None, None)
    IS['r11_8822288409'] = ('11_CI_BASLIK', None, None)
DIR, EK, ON = {'pilot': ('yeni', '_YENI_ALTIN.jpg', 'PILOT'), 'pin': ('yeni_pin', '_YENI_PIN_ALTIN.jpg', 'PIN'),
               'tum': ('yeni_tum', '_YENI_TUM_ALTIN.jpg', 'TUM')}[MOD]
SAG = {'pilot': 'YENI (pin altini)', 'pin': 'YENI (pin altin sembol)', 'tum': 'YENI (tum ogeler yeni altin)'}[MOD]
BANT, ARA = 100, 24


def yan_yana(e, y, baslik, font=FONT, bant=BANT):
    W, H = e.width * 2 + ARA, e.height + bant
    S = Image.new('RGB', (W, H), (255, 255, 255))
    S.paste(e, (0, bant)); S.paste(y, (e.width + ARA, bant))
    d = ImageDraw.Draw(S)
    d.text((20, 15), f'ESKI  {baslik}', fill=(0, 0, 0), font=font)
    d.text((e.width + ARA + 20, 15), SAG, fill=(0, 0, 0), font=font)
    return S


def dikey(parcalar):
    W = max(p.width for p in parcalar); H = sum(p.height for p in parcalar) + 20 * (len(parcalar) - 1)
    S = Image.new('RGB', (W, H), (255, 255, 255)); yy = 0
    for p in parcalar:
        S.paste(p, (0, yy)); yy += p.height + 20
    return S


for f, (ad, kutu, halka) in IS.items():
    e = Image.open(os.path.join(KOK, 'eski', f + '.jpg')).convert('RGB')
    y = Image.open(os.path.join(KOK, DIR, f + EK)).convert('RGB')
    yan_yana(e, y, f).save(os.path.join(KOK, f'PAFTA_ALTIN_{ON}_CL_{ad}.jpg'), quality=90)
    satir = []
    if kutu:
        satir.append(yan_yana(e.crop(kutu), y.crop(kutu), f + ' sembol 1:1', FONT_K, 60))
    if MOD == 'tum':
        if halka:
            satir.append(yan_yana(e.crop(halka), y.crop(halka), 'halka 1:1', FONT_K, 60))
        if f in ('r01_8749216062', 'r07_8812066177', 'r08_8812066995', 'r09_8812067931', 'r10_8764250162', 'r11_8822288409'):
            satir.append(yan_yana(e.crop(BAS), y.crop(BAS), 'Canva baslik 1:1', FONT_K, 60))
    if satir:
        dikey(satir).save(os.path.join(KOK, f'PAFTA_ALTIN_{ON}_CL_{ad}_YAKIN.jpg'), quality=92)
    print(ad)
