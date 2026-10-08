# Siparis posteri kapilari (8 Eki 2026). PASS/FAIL, olculebilir esik.
# Kullanim: python siparis_kapi.py IS_KLASORU REFERANS_POSTER(standart, ayni cift; yoksa '-') [--json CIKTI]
#  a) ANA bolgesi referansla ayni: ana kutusunda |fark| ortalama <= 0.5 ve %99.9 <= 10 (olculen: 0.29 / 6; katman uint8 + JPEG payi);
#     YEREL: fark > 10 bagli kume alani <= 0.5 * kalinlik^2 (ders 139 olcusu);
#     ayrica degisebilir bant (isim satiri, kucuk semboller, sonsuz, tagline + 200 px parlama payi) DISINDA ayni.
#  b) ogeler arasi dE00 (ana ile) <= 1 (renk_olcum.json)
#  c) isim-burc: isim1 solda (x isim1 < x isim2), kucuk1 = ilk burcun sembolu (12 sembolle korelasyon en yuksek), kucuk1 isim1 uzerinde
#  d) yazim: isim1, isim2, tagline alfalari girdiden bagimsiz cizimle ayni (IoU >= 0.985)
#  e) dikis yok: ana kutusu kenarlarinda (zemin pikselleri) kenar adimi <= komsu adim * 1.5 + 0.6
import sys, os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
B = os.environ.get('MOTOR_KOK', '/home/claude/blender') + '/'; G = B + 'girdi/'; FONT = os.environ.get('FONT_KOK', '/home/claude/motor_klon/motor/font/')
IS, REF = sys.argv[1], sys.argv[2]
JS = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
s = json.load(open(f'{IS}/siparis.json')); c = s['cift']; b1, b2 = c.split('_')
son = f"{IS}/AstroLoveArt_{b1.capitalize()}_{b2.capitalize()}.jpg"
z = np.load(f'{IS}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
P = np.asarray(Image.open(son).convert('RGB')).astype(np.int16)
sonuc = {}
def kutu(ad, pay=0):
    x, y = K[ad]; h, w = z[ad].shape; return max(0, y - pay), min(10800, y + h + pay), max(0, x - pay), min(7200, x + w + pay)
# a)
if REF != '-':
    R = np.asarray(Image.open(REF).convert('RGB')).astype(np.int16)
    y0, y1, x0, x1 = kutu('ana'); d = np.abs(P[y0:y1, x0:x1] - R[y0:y1, x0:x1]).max(2)
    serbest = np.zeros((10800, 7200), bool)
    for ad in ('isim1', 'isim2', 'sonsuz', 'kucuk1', 'kucuk2', 'tagline'):
        a, b_, c_, d_ = kutu(ad, 200); serbest[a:b_, c_:d_] = True
    if os.environ.get('REF_ALFA'):                                   # referansin oge yerleri (isim boyu degisince kayar)
        zr = np.load(os.environ['REF_ALFA']); Kr = {str(a): (int(x), int(y)) for (x, y), a in zip(zr['_konum'], zr['_ad'])}
        for ad in ('isim1', 'isim2', 'sonsuz', 'kucuk1', 'kucuk2', 'tagline'):
            x, y = Kr[ad]; h, w = zr[ad].shape; serbest[max(0, y - 200):y + h + 200, max(0, x - 200):x + w + 200] = True
    # yerel kontrol (ders 139): genel ortalama %0.1'den kucuk yerel kusuru kacirir. Fark > 10 piksellerinden bagli kumeler;
    # en buyuk kume alani 0.5 * kalinlik^2'yi asarsa FAIL (kalinlik: ana alfasi mesafe donusumu ortancasi x 2).
    am = z['ana'] > 127
    kal = float(np.median(cv2.distanceTransform(am.astype(np.uint8), cv2.DIST_L2, 5)[am])) * 2
    n_, _, st_, _ = cv2.connectedComponentsWithStats((d > 10).astype(np.uint8), 8)
    en_buyuk_kume = int(st_[1:, cv2.CC_STAT_AREA].max()) if n_ > 1 else 0
    dd = np.abs(P - R).max(2)
    dis = dd[~serbest]
    sonuc['a'] = dict(ana_ort=round(float(d.mean()), 3), ana_p999=int(np.percentile(d, 99.9)), dis_ort=round(float(dis.mean()), 3),
                      dis_p999=int(np.percentile(dis, 99.9)), kume_px=en_buyuk_kume, kume_esik=int(0.5 * kal * kal), kalinlik=round(kal, 1))
    sonuc['a']['PASS'] = bool(sonuc['a']['ana_ort'] <= 0.5 and sonuc['a']['ana_p999'] <= 10 and sonuc['a']['dis_ort'] <= 0.5 and sonuc['a']['dis_p999'] <= 10
                               and en_buyuk_kume <= sonuc['a']['kume_esik'])
# b)
_src = open(B + 'renk_uyum.py').read()
_ns = {}; exec('import numpy as np\n' + _src[_src.index('def de00'):_src.index('lab = lambda')], _ns)   # renk_uyum ile AYNI de00
de00 = _ns['de00']
lab = lambda x: cv2.cvtColor((x.reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
def ortanca(ad):
    x, y = K[ad]; a = z[ad]; m = cv2.erode((a > 242).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return np.median(lab(P[y:y + a.shape[0], x:x + a.shape[1]].astype(np.float32)[m]), 0)
La = ortanca('ana')
dE = {ad: round(de00(La, ortanca(ad)), 2) for ad in ('kucuk1', 'kucuk2', 'sonsuz', 'isim1', 'isim2', 'tagline', 'cember')}
sonuc['b'] = dict(dE00=dE, en_kotu=max(dE.values()), PASS=bool(max(dE.values()) <= 1.0))
# c)
KUCUK = {'AQUARIUS': ('KUCUK_1', [1095, 219, 2010, 600]), 'ARIES': ('KUCUK_1', [2257, 102, 2917, 717]),
         'CANCER': ('KUCUK_1', [175, 933, 859, 1527]), 'CAPRICORN': ('KUCUK_1', [1200, 880, 1905, 1580]),
         'GEMINI': ('KUCUK_1', [2285, 923, 2889, 1537]), 'LEO': ('KUCUK_1', [254, 1743, 781, 2357]),
         'LIBRA': ('KUCUK_2', [1001, 94, 1822, 709]), 'PISCES': ('KUCUK_2', [2023, 95, 2682, 708]),
         'SAGITTARIUS': ('KUCUK_2', [217, 875, 723, 1533]), 'SCORPIO': ('KUCUK_2', [1038, 897, 1784, 1512]),
         'TAURUS': ('KUCUK_2', [2045, 898, 2659, 1510]), 'VIRGO': ('KUCUK_2', [130, 1666, 811, 2349])}
def kirp(a):
    ys, xs = np.nonzero(a > 127); return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
def benzer(a, b):
    h, w = max(a.shape[0], b.shape[0]) + 4, max(a.shape[1], b.shape[1]) + 4
    A_ = np.zeros((h, w), np.float32); B_ = np.zeros((h, w), np.float32)
    A_[:a.shape[0], :a.shape[1]] = a > 127; B_[:b.shape[0], :b.shape[1]] = b > 127
    return float((A_ * B_).sum() / max(np.sqrt((A_ ** 2).sum() * (B_ ** 2).sum()), 1))
kaynak = {}
for b, (sf, kk) in KUCUK.items():
    kaynak[b] = kirp(np.asarray(Image.open(G + sf + '.png').convert('L'))[kk[1]:kk[3], kk[0]:kk[2]])
def kim(ad):
    a = kirp(z[ad]); sk = {b: benzer(a, cv2.resize(k, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)) for b, k in kaynak.items()}
    return max(sk, key=sk.get)
k1, k2 = kim('kucuk1'), kim('kucuk2')
x_i1 = K['isim1'][0] + z['isim1'].shape[1] / 2; x_i2 = K['isim2'][0] + z['isim2'].shape[1] / 2
x_k1 = K['kucuk1'][0] + z['kucuk1'].shape[1] / 2
sonuc['c'] = dict(kucuk1=k1, kucuk2=k2, beklenen=[b1, b2], isim1_solda=bool(x_i1 < x_i2), kucuk1_isim1_ustunde=bool(abs(x_k1 - x_i1) < 60))
sonuc['c']['PASS'] = bool(k1 == b1 and k2 == b2 and sonuc['c']['isim1_solda'] and sonuc['c']['kucuk1_isim1_ustunde'])
# d)
def ciz(metin, font, wght, punto):
    F = ImageFont.truetype(FONT + font, punto); F.set_variation_by_axes([wght])
    bb = F.getbbox(metin, anchor='ls'); im = Image.new('L', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), metin, font=F, fill=255, anchor='ls'); return kirp(np.asarray(im))
def iou(a, b):
    a, b = kirp(a), kirp(b)
    if abs(a.shape[0] - b.shape[0]) > 3 or abs(a.shape[1] - b.shape[1]) > 3: return 0.0
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1]); A_, B_ = a[:h, :w] > 127, b[:h, :w] > 127
    return float((A_ & B_).sum() / max((A_ | B_).sum(), 1))
def en_iyi(ad, metin, font, wght, p0):
    return max((iou(z[ad], ciz(metin, font, wght, p)), p) for p in range(p0 - 120, p0 + 1, 4))
d = {}
for ad, isim in (('isim1', s['isim1']), ('isim2', s['isim2'])):
    v, p = en_iyi(ad, isim.upper(), 'Cinzel.ttf', 500, 405); d[ad] = dict(iou=round(v, 4), punto=p)
v, p = en_iyi('tagline', s['tagline'], 'EBGaramond-Italic.ttf', 400, 372); d['tagline'] = dict(iou=round(v, 4), punto=p)
sonuc['d'] = dict(**d, PASS=bool(all(x['iou'] >= 0.985 for x in d.values())))
# e) dikis: ana kutusu kenarlarinda (yalniz sembolun OLMADIGI zemin pikselleri) kenar adimi komsu adimla ayni olmali
y0, y1, x0, x1 = kutu('ana'); Pf = P.astype(np.float32).mean(2); e = {}
ana_a = z['ana'] > 0
zem = cv2.dilate(ana_a.astype(np.uint8), np.ones((41, 41), np.uint8)) == 0            # sembol + parlama payi disi
for ad_, (ic, dis_, yon) in {'ust': (y0, y0 - 1, 1), 'alt': (y1 - 1, y1, -1), 'sol': (x0, x0 - 1, 1), 'sag': (x1 - 1, x1, -1)}.items():
    if ad_ in ('ust', 'alt'):
        m = zem[0 if ad_ == 'ust' else -1, :]
        adim = np.abs(Pf[ic, x0:x1] - Pf[dis_, x0:x1])[m].mean() if m.any() else 0.0
        ref = np.abs(Pf[ic + 5 * yon, x0:x1] - Pf[dis_ + 5 * yon, x0:x1])[m].mean() if m.any() else 0.0
    else:
        m = zem[:, 0 if ad_ == 'sol' else -1]
        adim = np.abs(Pf[y0:y1, ic] - Pf[y0:y1, dis_])[m].mean() if m.any() else 0.0
        ref = np.abs(Pf[y0:y1, ic + 5 * yon] - Pf[y0:y1, dis_ + 5 * yon])[m].mean() if m.any() else 0.0
    e[ad_] = dict(adim=round(float(adim), 3), komsu=round(float(ref), 3), n=int(m.sum()), PASS=bool(adim <= ref * 1.5 + 0.6))
sonuc['e'] = dict(**e, PASS=bool(all(v['PASS'] for v in e.values())))
sonuc['PASS'] = bool(all(v['PASS'] for k, v in sonuc.items() if isinstance(v, dict)))
print(json.dumps(sonuc, ensure_ascii=False))
if JS: json.dump(sonuc, open(JS, 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if sonuc['PASS'] else 1)
