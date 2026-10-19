#!/usr/bin/env python3
"""Orchard: bir burc cifti icin tam ilan seti (Cancer + Libra ile onaylanan yontemin aynisi).
Uretir: 8 stil baski dosyasi (11 oz 2700x1050 ve 15 oz 2700x1140), 8 kapak, galeri 1-14 (2048 JPG), 400 px mobil pafta, 6 sn video (ilk/son kare = kapak).
Kullanim: python3 -I cift.py <burc1> <burc2> <isim1> <isim2> <mesaj> <sembol_klasoru> <cikti_klasoru>
Sembol klasoru: ana.png (ozgun sembol), sol.png, sag.png (iki kucuk burc isareti).
"""
import os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

B1, B2, ISIM1, ISIM2, MESAJ, SEM, OUT = sys.argv[1:8]
KOD = os.path.dirname(os.path.abspath(__file__)) + '/'
V = os.path.abspath(os.path.join(KOD, '..', 'varlik')) + '/'
SEM, OUT = os.path.abspath(SEM), os.path.abspath(OUT)
for d in ('', '/baski', '/kapak', '/gorunum', '/kart', '/galeri', '/video'):
    os.makedirs(OUT + d, exist_ok=True)
CIN, GAR = V + 'font/Cinzel[wght].ttf', V + 'font/EBGaramond[wght].ttf'
KREM, YESIL = (246, 241, 233), (22, 52, 34)
S = 2048
ST8 = [('orange', 'Orange Blossom'), ('fig', 'Purple Fig'), ('olive', 'Olive Breeze'), ('pomegranate', 'Pomegranate Bloom'),
       ('almond', 'Almond Blossom'), ('lemon', 'Lemon Grove'), ('grape', 'Blue Grape'), ('loquat', 'Golden Loquat')]
RENKLER = {'orange': '10,40,24', 'fig': '52,18,48', 'olive': '12,24,78', 'pomegranate': '100,16,24', 'almond': '52,22,14',
           'lemon': '12,22,76', 'grape': '16,30,90', 'loquat': '62,24,10'}
ENV = {'GOLGE_US': '0.4', 'PARLA': '0.7', 'PATH': '/usr/bin:/bin'}
ADIM = 8 + 8 + 8 + 8 + 6 + 1 + 3
sayac = [0]
t0 = time.time()
LOG = open(OUT + '/olcum.txt', 'w')


def ilerle(m):
    sayac[0] += 1
    g = time.time() - t0
    print(f'[{sayac[0]}/{ADIM} %{100 * sayac[0] // ADIM}] {m} (gecen {g:.0f}s, kalan ~{g / sayac[0] * (ADIM - sayac[0]):.0f}s)', flush=True)


def calis(args, env=None):
    r = subprocess.run(args, capture_output=True, text=True, env=env, cwd=KOD)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-1500:])
        raise SystemExit('HATA: ' + ' '.join(args[:3]))
    return r.stdout


def baski(st, isim1, isim2, mesaj, cikti, bayrak=(), d_in=None):
    env = dict(ENV)
    if d_in:
        env['D_IN'] = d_in
    for b in bayrak:
        env[b] = '1'
    o = calis(['python3', '-I', KOD + 'baski_kes.py', V + 'kes/' + st.upper() + 'R', SEM, isim1, isim2, B1, B2, mesaj, RENKLER[st], cikti], env)
    return [l.split('] ', 1)[1] for l in o.splitlines() if ('on:' in l or 'arka:' in l or 'tasma' in l)]


def giydir(sahne, baski_png, geo, cikti, d_in=None):
    env = dict(ENV)
    if d_in:
        env['D_IN'] = d_in
    calis(['python3', '-I', KOD + 'kapak_canva3.py', sahne, baski_png, geo, cikti], env)


def baslik(src, cikti, renk):
    env = dict(ENV)
    env['RENK'] = renk
    calis(['python3', '-I', KOD + 'baslik4.py', src, B1, B2, cikti], env)


# 1) 8 stil baski dosyasi
for st, ad in ST8:
    o = baski(st, ISIM1, ISIM2, MESAJ, f'{OUT}/baski/B_{st}')
    LOG.write(f'{ad}: ' + ' | '.join(o) + '\n')
    ilerle(f'baski {ad}')

# 1b) 8 stil 15 oz baski dosyasi (Serdar 19.10): desen 11 oz ile ayni fiziksel boyda, on/arka 15 oz capina (8,5 cm = 3,35 inc)
# gore yerlesir, 2700x1050 cizilip dikeyde ortalanarak 2700x1140'a tamamlanir
for st, ad in ST8:
    tmp = f'{OUT}/baski/T15_{st}'
    o = baski(st, ISIM1, ISIM2, MESAJ, tmp, d_in='3.35')
    a = np.asarray(Image.open(tmp + '_baski_11oz.png').convert('RGB'))
    b = np.full((1140, 2700, 3), 255, np.uint8)
    b[45:45 + 1050] = a
    Image.fromarray(b).save(f'{OUT}/baski/B_{st}_baski_15oz.png', dpi=(300, 300))
    os.remove(tmp + '_baski_11oz.png')
    os.replace(tmp + '_onizleme.jpg', f'{OUT}/baski/B_{st}_onizleme_15oz.jpg')
    LOG.write(f'{ad} 15 oz: ' + ' | '.join(x for x in o if 'kaydedildi' not in x) + '\n')
    ilerle(f'baski 15 oz {ad}')

# 2) 8 kapak (onayli sahneler, ayni giydirme ve baslik)
for st, ad in ST8:
    giydir(V + f'sahne/{st}_k40.png', f'{OUT}/baski/B_{st}_baski_11oz.png', V + 'gorunum/geo_kapak_k40.json', f'{OUT}/kapak/{st}_giydir.jpg')
    baslik(f'{OUT}/kapak/{st}_giydir.jpg', f'{OUT}/kapak/KAPAK_{st}.jpg', RENKLER[st])
    ilerle(f'kapak {ad}')

# 3) gorunumler (Orange Blossom): tek on/arka, yakin plan, 15 oz; kisa ve uzun ornek
BO = f'{OUT}/baski/B_orange_baski_11oz.png'
G = f'{OUT}/gorunum/'
for y in ('tek_on', 'tek_arka'):
    giydir(V + f'gorunum/ORCHARD_OrangeBlossom_sahne_{y}.png', BO, V + f'gorunum/geo_{y}.json', G + f'{y}.jpg')
    ilerle(f'gorunum {y}')
giydir(V + 'gorunum/ORCHARD_OrangeBlossom_sahne_yakin_plan.png', BO, V + 'gorunum/geo_yakin.json', G + 'yakin.jpg')
ilerle('gorunum yakin')
giydir(V + 'gorunum/sahne15.png', BO, V + 'gorunum/geo15.json', G + 'm15.jpg', d_in='3.35')
ilerle('gorunum 15 oz')
o = baski('orange', 'Mia', 'Leo', 'Always', f'{OUT}/baski/ML')
LOG.write('Kisa ornek (Mia & Leo, Always): ' + ' | '.join(o) + '\n')
ilerle('kisa ornek baski')
o = baski('orange', 'Maximilian', 'Josephine', 'Forever my favorite adventure!', f'{OUT}/baski/MJ')
LOG.write('Uzun ornek (Maximilian & Josephine): ' + ' | '.join(o) + '\n')
ilerle('uzun ornek baski')
for ad in ('ML', 'MJ'):
    for y, kk in (('tek_on', 'on'), ('tek_arka', 'arka')):
        giydir(V + f'gorunum/ORCHARD_OrangeBlossom_sahne_{y}.png', f'{OUT}/baski/{ad}_baski_11oz.png', V + f'gorunum/geo_{y}.json', G + f'{ad}_{kk}.jpg')
    ilerle(f'gorunum {ad}')


# 4) kartlar 2-7 (onayli kart dili)
def f(yol, px, w):
    ft = ImageFont.truetype(yol, px)
    ft.set_variation_by_axes([w])
    return ft


def orta(d, y, m, ft, x=S // 2, renk=YESIL, aralik=0):
    if aralik:
        W = sum(d.textlength(c, font=ft) for c in m) + aralik * (len(m) - 1)
        xx = x - W / 2
        for c in m:
            d.text((xx, y), c, font=ft, fill=renk)
            xx += d.textlength(c, font=ft) + aralik
    else:
        w = d.textlength(m, font=ft)
        d.text((x - w / 2, y), m, font=ft, fill=renk)


def kart():
    return Image.new('RGB', (S, S), KREM)


def kupa_kirp(yol, kutu=(400, 330, 1680, 1780)):
    return Image.open(yol).convert('RGB').crop(kutu)


KD = f'{OUT}/kart/'
# 2 yakin plan
im = Image.open(G + 'yakin.jpg').convert('RGB')
d = ImageDraw.Draw(im)
orta(d, 150, 'YOUR TWO SIGNS,', f(CIN, 92, 600), aralik=4)
orta(d, 270, 'ONE ORIGINAL SYMBOL', f(CIN, 92, 600), aralik=4)
im.save(KD + 'K2.jpg', quality=90)
ilerle('kart 2')

# 3 how to personalize
im = kart()
d = ImageDraw.Draw(im)
orta(d, 120, 'HOW TO PERSONALIZE', f(CIN, 96, 600), aralik=4)
for j, (yol, etiket) in enumerate(((G + 'tek_on.jpg', 'FRONT'), (G + 'tek_arka.jpg', 'BACK'))):
    k = kupa_kirp(yol).resize((860, 975), Image.LANCZOS)
    x = 120 + j * 948
    im.paste(k, (x, 330))
    orta(d, 1330, etiket, f(CIN, 60, 600), x=x + 430, aralik=6)
g = f(GAR, 67, 560)
g2 = f(GAR, 60, 480)
s1, s2 = (('1  Left name', '2  Right name') if B1 == B2 else (f'1  Name for {B1}', f'2  Name for {B2}'))
orta(d, 1425, s1, g, x=550)
orta(d, 1510, s2, g, x=550)
orta(d, 1595, 'Up to 10 letters per name', g2, x=550)
orta(d, 1425, '3  Your message', g, x=1498)
orta(d, 1510, 'Up to 30 characters', g2, x=1498)
d.line((240, 1700, S - 240, 1700), fill=YESIL, width=3)
orta(d, 1760, 'You receive one mug,', f(GAR, 82, 640))
orta(d, 1860, 'printed on both sides', f(GAR, 82, 640))
LOG.write(f'Kart 3 satir genislikleri: "{s1}" {d.textlength(s1, font=g):.0f} px, "{s2}" {d.textlength(s2, font=g):.0f} px '
          f'(sol sutun 120-980, merkez 550)\n')
im.save(KD + 'K3.jpg', quality=90)
ilerle('kart 3')

# 4 choose your style
im = kart()
d = ImageDraw.Draw(im)
orta(d, 110, 'CHOOSE YOUR STYLE', f(CIN, 96, 600), aralik=4)
hw, hh = 440, 700
for j, (st, ad) in enumerate(ST8):
    k = Image.open(f'{OUT}/kapak/KAPAK_{st}.jpg').convert('RGB').crop((330, 770, 1010, 1660)).resize((hw, hh - 90), Image.LANCZOS)
    x = 104 + (j % 4) * (hw + 40)
    y = 290 + (j // 4) * (hh + 190)
    im.paste(k.crop((0, 0, hw, hh - 90)), (x, y))
    w1, w2 = ad.split(' ', 1)
    orta(d, y + hh - 90 + 35, w1, f(GAR, 65, 600), x=x + hw // 2)
    orta(d, y + hh - 90 + 35 + 68, w2, f(GAR, 65, 600), x=x + hw // 2)
im.save(KD + 'K4.jpg', quality=90)
ilerle('kart 4')

# 5 two sizes
im = kart()
d = ImageDraw.Draw(im)
orta(d, 120, 'TWO SIZES', f(CIN, 96, 600), aralik=6)
SC = 0.66
taban_kart = 1430
for cx, yol, kutu, oz, olc, inc, ml in (
        (540, G + 'tek_on.jpg', (215, 380, 1575, 1705), '11 oz', '9.6 x 8.2 cm', '3.8 x 3.2 in', '325 ml'),
        (1500, G + 'm15.jpg', (230, 400, 1635, 2005), '15 oz', '11.9 x 8.5 cm', '4.7 x 3.3 in', '444 ml')):
    k = Image.open(yol).convert('RGB').crop(kutu)
    k = k.resize((round(k.width * SC), round(k.height * SC)), Image.LANCZOS)
    im.paste(k, (round(cx - k.width / 2), round(taban_kart - k.height)))
    orta(d, taban_kart + 50, oz.upper(), f(CIN, 80, 650), x=cx)
    orta(d, taban_kart + 160, olc, f(GAR, 62, 560), x=cx)
    orta(d, taban_kart + 240, inc, f(GAR, 56, 480), x=cx)
    orta(d, taban_kart + 312, ml, f(GAR, 56, 480), x=cx)
orta(d, 1860, 'Height x diameter', f(GAR, 54, 480))
orta(d, 1930, 'Approximate size comparison', f(GAR, 50, 480))
im.save(KD + 'K5.jpg', quality=90)
ilerle('kart 5')

# 6 your names, your message
im = kart()
d = ImageDraw.Draw(im)
orta(d, 110, 'YOUR NAMES, YOUR MESSAGE', f(CIN, 88, 600), aralik=3)
SUT = 864
xs = (128, 128 + SUT + 64)
KUTU = {'on': (585, 1090, 1465, 1610), 'arka': (555, 1060, 1495, 1520)}
orta(d, 290, 'FRONT', f(CIN, 60, 600), x=xs[0] + SUT // 2, aralik=6)
orta(d, 290, 'BACK', f(CIN, 60, 600), x=xs[1] + SUT // 2, aralik=6)
y = 400
for etiket, on, ar in (('Short example', G + 'ML_on.jpg', G + 'ML_arka.jpg'), ('Long example', G + 'MJ_on.jpg', G + 'MJ_arka.jpg')):
    orta(d, y, etiket, f(GAR, 60, 600))
    hmax = 0
    for x, yol, kk in ((xs[0], on, 'on'), (xs[1], ar, 'arka')):
        k = Image.open(yol).convert('RGB').crop(KUTU[kk])
        k = k.resize((SUT, round(k.height * SUT / k.width)), Image.LANCZOS)
        im.paste(k, (x, y + 90))
        hmax = max(hmax, k.height)
    y += 90 + hmax + 70
orta(d, y + 30, 'Up to 10 letters per name', f(GAR, 58, 500))
orta(d, y + 110, 'Message up to 30 characters', f(GAR, 58, 500))
im.save(KD + 'K6.jpg', quality=90)
ilerle('kart 6')

# 7 care & making
im = kart()
d = ImageDraw.Draw(im)
orta(d, 120, 'CARE & MAKING', f(CIN, 96, 600), aralik=6)
k = kupa_kirp(G + 'tek_on.jpg').resize((800, 907), Image.LANCZOS)
im.paste(k, (1130, 420))
y = 520
g = f(GAR, 66, 560)
for s_ in ['Dishwasher safe', 'Microwave safe', 'Glossy white ceramic,', 'white inside', 'Made to order, just for you']:
    if s_ != 'white inside':
        d.ellipse((150, y + 30, 168, y + 48), fill=YESIL)
    d.text((200, y), s_, font=g, fill=YESIL)
    y += 105 if not s_.endswith(',') else 80
d.line((240, 1480, S - 240, 1480), fill=YESIL, width=3)
orta(d, 1560, 'Original zodiac fusion symbols', f(GAR, 70, 600))
orta(d, 1650, 'designed by AstroLoveArt', f(GAR, 70, 600))
im.save(KD + 'K7.jpg', quality=90)
ilerle('kart 7')

# 5) galeri 1-14 + pafta + 400 px mobil pafta
GD = f'{OUT}/galeri/'
sira = [('01_Orange_Blossom_kapak', f'{OUT}/kapak/KAPAK_orange.jpg'), ('02_Yakin_plan', KD + 'K2.jpg'),
        ('03_How_to_personalize', KD + 'K3.jpg'), ('04_Choose_your_style', KD + 'K4.jpg'), ('05_Two_sizes', KD + 'K5.jpg'),
        ('06_Names_and_message', KD + 'K6.jpg'), ('07_Care_and_making', KD + 'K7.jpg')]
sira += [(f'{8 + j:02d}_{ad.replace(" ", "_")}', f'{OUT}/kapak/KAPAK_{st}.jpg') for j, (st, ad) in enumerate(ST8[1:])]
kucuk, mobil = [], []
for ad, yol in sira:
    im = Image.open(yol).convert('RGB')
    im.save(GD + ad + '.jpg', quality=88)
    kucuk.append(im.resize((512, 512), Image.LANCZOS))
    mobil.append(im.resize((400, 400), Image.LANCZOS))
p = Image.new('RGB', (7 * 512 + 8 * 16, 2 * 512 + 3 * 16), (255, 255, 255))
for j, im in enumerate(kucuk):
    p.paste(im, (16 + (j % 7) * 528, 16 + (j // 7) * 528))
p.save(GD + 'GALERI_1_14.jpg', quality=88)
p = Image.new('RGB', (7 * 400 + 8 * 10, 2 * 400 + 3 * 10), (255, 255, 255))
for j, im in enumerate(mobil):
    p.paste(im, (10 + (j % 7) * 410, 10 + (j // 7) * 410))
p.save(GD + 'MOBIL_400px.png')
ilerle('galeri')

# baslik olcumu (kapak 2048): baslik metninin yatay kapsami
a = np.asarray(Image.open(f'{OUT}/kapak/KAPAK_orange.jpg').convert('RGB')).astype(float)
b = np.asarray(Image.open(f'{OUT}/kapak/orange_giydir.jpg').convert('RGB')).astype(float)
dd = np.abs(a - b).max(-1)[:760] > 40
ys, xs_ = np.where(dd)
LOG.write(f'Kapak basligi: x {xs_.min()}-{xs_.max()} (genislik {xs_.max() - xs_.min()} / 2048, kenar payi sol {xs_.min()} sag {2047 - xs_.max()}), '
          f'y {ys.min()}-{ys.max()}\n')

# 6) video katmanlari (Orange Blossom kapak sahnesi) ve video
VD = f'{OUT}/video/'
for ad, bayrak in (('full', ()), ('basem', ('SEMBOL_YOK', 'MESAJ_YOK')), ('nosym', ('SEMBOL_YOK',)), ('noglif', ('GLIF_YOK',)),
                   ('nomes', ('MESAJ_YOK',))):
    baski('orange', ISIM1, ISIM2, MESAJ, VD + ad, bayrak)
full = np.asarray(Image.open(VD + 'full_baski_11oz.png').convert('RGB')).astype(float)
Image.fromarray(np.full(full.shape, 255, np.uint8)).save(VD + 'beyaz.png')
for ad in ('nosym', 'noglif', 'nomes'):
    x = np.asarray(Image.open(VD + f'{ad}_baski_11oz.png').convert('RGB')).astype(float)
    dm = np.clip(255 - np.abs(full - x).max(-1) * 1.1, 0, 255).astype(np.uint8)
    Image.fromarray(np.stack([dm] * 3, -1)).save(VD + f'mask_{ad}.png')
ilerle('video katman baskilari')
SC_ = V + 'sahne/orange_k40.png'
GK = V + 'gorunum/geo_kapak_k40.json'
for ad in ('full', 'basem'):
    giydir(SC_, VD + f'{ad}_baski_11oz.png', GK, VD + f'k_{ad}.jpg')
    baslik(VD + f'k_{ad}.jpg', VD + f'kb_{ad}_baski_11oz.png', RENKLER['orange'])
giydir(SC_, VD + 'beyaz.png', GK, VD + 'k_beyaz.png')
for ad in ('nosym', 'noglif', 'nomes'):
    giydir(SC_, VD + f'mask_{ad}.png', GK, VD + f'k_mask_{ad}.png')
ilerle('video katman giydirme')
calis(['python3', '-I', KOD + 'video6b.py', VD, GD + '01_Orange_Blossom_kapak.jpg', VD + f'ORCHARD_{B1}_{B2}_video_6sn.mp4'])
ilerle('video')
LOG.close()
print(open(OUT + '/olcum.txt').read())
print('tamam', OUT)
