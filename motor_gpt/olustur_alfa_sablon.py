# 2:3 sablonla herhangi bir cift + isimler + tagline icin alfa (7200x10800). Onizleme GEREKMEZ (kisisel siparis icin de).
# Kurallar onayli SV/CL/AA olcumlerinden: kucuk sembol merkez y 7078.5, x = isim merkezi; isim satiri ortali (x 3600),
# Cinzel 500 buyuk harf yuksekligi 298 px, taban 8068; sonsuz merkez y 7945.5, isimden bosluk 465; tagline EB Garamond
# Italic 372, ortali, taban 9278. Ana sembol: eski 78 posterden cembere goreli kutu (yerlesim78.json), kaynak Drive alfasi.
# Kullanim: python olustur_alfa_sablon.py CIFT ISIM1 ISIM2 "TAGLINE" CIKTI.npz
import sys, os, json, time, numpy as np, cv2
sys.path.insert(0, '/home/claude/blender')
from alfa_temizle import temizle
TEMIZ = os.environ.get('ALFA_TEMIZ', '1') == '1'   # 7 Eki: tasma silme + kavsak dolgusu
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
T = time.time()
def log(*a): print(f'[{time.time()-T:6.1f}s]', *a, flush=True)
cift, isim1, isim2, tag, cikti = sys.argv[1:6]
B = '/home/claude/blender/'; G = B + 'girdi/'; FONT = '/home/claude/motor_klon/motor/font/'
W, H = 7200, 10800
KUCUK = {'AQUARIUS': ('KUCUK_1', [1095, 219, 2010, 600]), 'ARIES': ('KUCUK_1', [2257, 102, 2917, 717]),
         'CANCER': ('KUCUK_1', [175, 933, 859, 1527]), 'CAPRICORN': ('KUCUK_1', [1200, 880, 1905, 1580]),
         'GEMINI': ('KUCUK_1', [2285, 923, 2889, 1537]), 'LEO': ('KUCUK_1', [254, 1743, 781, 2357]),
         'LIBRA': ('KUCUK_2', [1001, 94, 1822, 709]), 'PISCES': ('KUCUK_2', [2023, 95, 2682, 708]),
         'SAGITTARIUS': ('KUCUK_2', [217, 875, 723, 1533]), 'SCORPIO': ('KUCUK_2', [1038, 897, 1784, 1512]),
         'TAURUS': ('KUCUK_2', [2045, 898, 2659, 1510]), 'VIRGO': ('KUCUK_2', [130, 1666, 811, 2349])}
KUCUK_Y, TABAN_ISIM, CAP_H, SONSUZ_Y, BOSLUK, TABAN_TAG, TAG_PUNTO, ORTA = 7078.5, 8062, 298, 7945.5, 465, 9271, 372, 3600
KENAR = 700
ISIM_PUNTO = 405                                                         # isim satiri kenar payi (sigmazsa kuculur)
OUT = {}

def ekle(ad, x0, y0, al):
    ys, xs = np.nonzero(al > 0)
    a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    q = 8; a, c = max(0, a - q), max(0, c - q); b, d = min(al.shape[0], b + q), min(al.shape[1], d + q)
    OUT[ad] = (int(x0 + c), int(y0 + a), al[a:b, c:d].copy())

def kirp(a):
    ys, xs = np.nonzero(a > 8)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

def yaz(metin, fontad, wght, punto):
    F = ImageFont.truetype(FONT + fontad, punto); F.set_variation_by_axes([wght])
    b = F.getbbox(metin, anchor='ls')
    im = Image.new('L', (b[2] - b[0] + 40, b[3] - b[1] + 40), 0)
    ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), metin, font=F, fill=255, anchor='ls')
    a = np.asarray(im)
    ys, xs = np.nonzero(a > 127)
    # (alfa, murekkep sol x, murekkep sag x, taban y) yerel koordinatta
    return a, xs.min(), xs.max() + 1, 20 - b[1]

# --- ana sembol ---
a_, b_ = sorted(cift.lower().split('_'))
src = np.asarray(Image.open(f'{B}girdi78/ana/{a_}_{b_}_alfa.png')).astype(np.float32)
src = kirp(src)
Y = json.load(open(B + 'yerlesim78.json'))[cift.upper()]
C = json.load(open(B + 'cember.json'))['cember']
gx0, gx1 = C['cx'] + Y['u0'] * C['R'], C['cx'] + Y['u1'] * C['R']
gy0 = C['cy'] + Y['v0'] * C['R']
s = (gx1 - gx0) / src.shape[1]
t = cv2.resize(src, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
log('ana olcek', round(s, 4), 'yukseklik tahmin/gercek', round((Y['v1'] - Y['v0']) * C['R']), t.shape[0])
t = np.clip(t, 0, 255).astype(np.uint8)
if TEMIZ:
    t, bilgi = temizle(t); log('ana temizlik', bilgi)
ekle('ana', int(round(gx0)), int(round(gy0)), t)

# --- isim satiri: isim1  sonsuz  isim2 (ortali) ---
def satir(olc):
    # Cinzel buyuk harf yuksekligi CAP_H olacak punto
    p = int(round(ISIM_PUNTO * olc))
    r1 = yaz(isim1.upper(), 'Cinzel.ttf', 500, p); r2 = yaz(isim2.upper(), 'Cinzel.ttf', 500, p)
    lg = np.asarray(Image.open(G + 'LOGO_1.png').convert('L'))[192:388, 760:1396].astype(np.float32)
    lg = kirp(lg); lg = cv2.resize(lg, None, fx=0.994 * olc, fy=0.994 * olc, interpolation=cv2.INTER_AREA)
    w1, w2 = r1[2] - r1[1], r2[2] - r2[1]
    top = w1 + w2 + lg.shape[1] + 2 * BOSLUK * olc
    return p, r1, r2, lg, w1, w2, top
olc = 1.0
p, r1, r2, lg, w1, w2, top = satir(olc)
if top > W - 2 * KENAR:
    olc = (W - 2 * KENAR) / top; p, r1, r2, lg, w1, w2, top = satir(olc)
x = ORTA - top / 2
for ad, r in (('isim1', r1),):
    ekle(ad, int(round(x - r[1])), int(round(TABAN_ISIM - r[3])), r[0])
c1 = x + w1 / 2
x += w1 + BOSLUK * olc
lg8 = np.clip(lg, 0, 255).astype(np.uint8)
if TEMIZ:
    lg8, bilgi = temizle(np.pad(lg8, 40)); log('sonsuz temizlik', bilgi)
    ekle('sonsuz', int(round(x)) - 40, int(round(SONSUZ_Y - lg.shape[0] / 2)) - 40, lg8)
else:
    ekle('sonsuz', int(round(x)), int(round(SONSUZ_Y - lg.shape[0] / 2)), lg8)
x += lg.shape[1] + BOSLUK * olc
ekle('isim2', int(round(x - r2[1])), int(round(TABAN_ISIM - r2[3])), r2[0])
c2 = x + w2 / 2
log('isim punto', p, 'olcek', round(olc, 3), 'satir', int(top))

# --- kucuk semboller: x = isim merkezi, y = KUCUK_Y ---
s1, s2 = (cift.upper().split('_') if '_' in cift else (cift, cift))
for ad, burc, cx_ in (('kucuk1', s1, c1), ('kucuk2', s2, c2)):
    sayfa, kk = KUCUK[burc]
    k = np.asarray(Image.open(G + sayfa + '.png').convert('L')).astype(np.float32)[kk[1]:kk[3], kk[0]:kk[2]]
    k = kirp(k)
    k8 = np.clip(k, 0, 255).astype(np.uint8); q = 0
    if TEMIZ:
        q = 40; k8, bilgi = temizle(np.pad(k8, q)); log(ad, 'temizlik', bilgi)
    ekle(ad, int(round(cx_ - k.shape[1] / 2)) - q, int(round(KUCUK_Y - k.shape[0] / 2)) - q, k8)

# --- tagline ---
F = ImageFont.truetype(FONT + 'EBGaramond-Italic.ttf', TAG_PUNTO); F.set_variation_by_axes([400])
tp = TAG_PUNTO
r = yaz(tag, 'EBGaramond-Italic.ttf', 400, tp)
while r[2] - r[1] > W - 2 * KENAR:
    tp -= 4; r = yaz(tag, 'EBGaramond-Italic.ttf', 400, tp)
ekle('tagline', int(round(ORTA - (r[2] - r[1]) / 2 - r[1])), int(round(TABAN_TAG - r[3])), r[0])
log('tagline punto', tp)

# --- cember: onayli ---
zs = np.load(B + 'alfa_ogeler.npz'); Ks = dict(zip([str(a) for a in zs['_ad']], zs['_konum']))
OUT['cember'] = (int(Ks['cember'][0]), int(Ks['cember'][1]), zs['cember'])
np.savez_compressed(cikti, **{k: v[2] for k, v in OUT.items()}, _konum=np.array([[*OUT[k][:2]] for k in OUT]), _ad=np.array(list(OUT)))
log('bitti', cikti)
