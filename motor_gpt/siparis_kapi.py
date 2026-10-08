# Siparis posteri kapilari (8 Eki 2026). PASS/FAIL, olculebilir esik.
# Kullanim: python siparis_kapi.py IS_KLASORU REFERANS_POSTER(standart, ayni cift; yoksa '-') [--json CIKTI]
#  a) ANA bolgesi referansla ayni: ana kutusunda |fark| ortalama <= 0.5 ve %99.9 <= 10 (olculen: 0.29 / 6; katman uint8 + JPEG payi);
#     YEREL: fark > 10 bagli kume alani <= 0.5 * kalinlik^2 (ders 139 olcusu);
#     ayrica degisebilir bant (isim satiri, kucuk semboller, sonsuz, tagline + 200 px parlama payi) DISINDA ayni.
#  b) ogeler arasi dE00 (ana ile) <= 1 (renk_olcum.json)
#  c) isim-burc: isim1 solda (x isim1 < x isim2), kucuk1 = ilk burcun sembolu (12 sembolle korelasyon en yuksek), kucuk1 isim1 uzerinde
#  d) yazim: isim1, isim2, tagline alfalari girdiden bagimsiz cizimle ayni (IoU >= 0.985)
#  e) dikis yok: ana kutusu kenarlarinda (zemin pikselleri) kenar adimi <= komsu adim * 1.5 + 0.6
#  g) Etsy teslim dosyasi: < 20 MB, 7200x10800, 4:4:4, 300 dpi (ana kopya da), halka <= 0.075
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
if '&' not in s['tagline']:
    v, p = en_iyi('tagline', s['tagline'], 'EBGaramond-Italic.ttf', 400, 372); d['tagline'] = dict(iou=round(v, 4), punto=p)
else:
    # & iceren tagline (8 Eki 2026): tam satir bagimsiz cizilir; her & yerine AYNI ChatGPT & alfasi (amp/AMP_ALFA.png),
    # boy = ayni puntoda "A" buyuk harf yuksekligi, & ile komsu kelime arasi = tagline kelime bosluklari ortalamasi, taban ortak.
    AMP_A = np.asarray(Image.open(B + 'amp/AMP_ALFA.png')).astype(np.float32) / 65535
    def amp_satir(tag, tp):
        F = ImageFont.truetype(FONT + 'EBGaramond-Italic.ttf', tp); F.set_variation_by_axes([400])
        def yz(m):
            bb = F.getbbox(m, anchor='ls'); im = Image.new('L', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
            ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), m, font=F, fill=255, anchor='ls'); a = np.asarray(im)
            yy, xx = np.nonzero(a > 127); return a, xx.min(), xx.max() + 1, 20 - bb[1], yy.min()
        def bosluk(a):
            k = ~(a > 127).any(0); yy, xx = np.nonzero(a > 127); out, i = [], xx.min()
            while i < xx.max():
                if k[i]:
                    j = i
                    while k[j]: j += 1
                    out.append(j - i); i = j
                else: i += 1
            return out
        A_ = yz('A'); cap = A_[3] - A_[4]
        pr = [q.strip() for q in tag.split('&')]
        gl = []                                                     # her & icin: "<onceki> and <sonraki>" murekkep bosluklari ortalamasi
        for i in range(len(pr) - 1):
            o_ = pr[i].split()[-1] if pr[i] else ''; s_ = pr[i + 1].split()[0] if pr[i + 1] else ''
            if not o_ and not s_: o_, s_ = 'Forever', 'Always'
            r = sorted(bosluk(yz(' '.join(x for x in (o_, 'and', s_) if x))[0]), reverse=True)[:int(bool(o_)) + int(bool(s_))]
            gl.append(int(round(float(np.mean(r)))))
        yy, xx = np.nonzero(AMP_A > 0.5); sc = cap / (yy.max() + 1 - yy.min())
        As = cv2.resize(AMP_A, (int(round(AMP_A.shape[1] * sc)), int(round(AMP_A.shape[0] * sc))), interpolation=cv2.INTER_AREA)
        A8 = np.round(As * 255).astype(np.uint8); yy, xx = np.nonzero(A8 > 127); ik = (xx.min(), xx.max() + 1, yy.max() + 1)
        par, ara = [], []
        for i, q in enumerate(pr):
            if q:
                if par: ara.append(gl[i - 1])                       # onceki eleman & (metinler & ile ayrilir)
                r = yz(q); par.append((r[0], r[1], r[2], r[3]))
            if i < len(pr) - 1:
                if par: ara.append(gl[i])
                par.append((A8, ik[0], ik[1], ik[2]))
        top = sum(q[2] - q[1] for q in par) + sum(ara)
        tv = np.zeros((max(q[0].shape[0] for q in par) + 400, top + 400), np.uint8); tb = tv.shape[0] - 150; xi = 0
        for j, (a, il, ir, bl) in enumerate(par):
            sl = tv[tb - bl:tb - bl + a.shape[0], xi - il + 200:xi - il + 200 + a.shape[1]]; np.maximum(sl, a, out=sl)
            xi += ir - il + (ara[j] if j < len(ara) else 0)
        return tv, top, A8
    tp = 372
    while True:
        tv, top, A8b = amp_satir(s['tagline'], tp)
        if top <= 7200 - 1400 or tp <= 200: break
        tp -= 4
    d['tagline'] = dict(iou=round(iou(z['tagline'], tv), 4), punto=tp, amp=True)
sonuc['d'] = dict(**d, PASS=bool(all(x['iou'] >= 0.985 for x in d.values())))
# f) & kapisi (8 Eki 2026): her & icin son goruntudeki altin silueti / beklenen & alfasi IoU >= 0.90; leke (ChatGPT & yuzeyine gore,
#    ortalama kaydirma cikarildiktan sonra |L farki| > 6 kume <= 0.5*kalinlik^2); dE00 (ana ile) <= 1
if '&' in s['tagline']:
    f = dict(beklenen=s['tagline'].count('&'), ampler=[])
    kon = (s.get('amp') or {}).get('konum') or []
    G_ = np.asarray(Image.open(B + 'amp/AMP_YUZEY.png').convert('RGB')).astype(np.float32) / 255
    AA = np.asarray(Image.open(B + 'amp/AMP_ALFA.png')).astype(np.float32) / 65535
    for (x, y, h, w) in kon:
        a8 = A8b if A8b.shape == (h, w) else cv2.resize(A8b, (w, h))
        Pc = P[y:y + h, x:x + w].astype(np.float32)
        fv = Pc / 255; V = fv.max(2); sari = fv[..., 0] - fv[..., 2]
        sil = (np.clip((V - 0.30) / 0.20, 0, 1) * np.clip((sari + 0.05) / 0.15, 0, 1)) > 0.5
        m = a8 > 127; io = float((sil & m).sum() / max((sil | m).sum(), 1))
        As = cv2.resize(AA, (w, h), interpolation=cv2.INTER_AREA); Gs = cv2.resize(G_ * AA[..., None], (w, h), interpolation=cv2.INTER_AREA) / np.maximum(As, 1e-4)[..., None]
        Lk = cv2.cvtColor(np.clip(Gs, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)[..., 0]; Lp = cv2.cvtColor(fv.astype(np.float32), cv2.COLOR_RGB2Lab)[..., 0]
        icm = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) > 3; r_ = Lp - Lk; r_ -= np.median(r_[icm])
        kal = float(np.median(cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)[m])) * 2
        n_, _, st_, _ = cv2.connectedComponentsWithStats(((np.abs(r_) > 6) & icm).astype(np.uint8), 8); kume = int(st_[1:, cv2.CC_STAT_AREA].max()) if n_ > 1 else 0
        ic2 = cv2.erode((a8 > 242).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        de = round(de00(La, np.median(cv2.cvtColor(fv.astype(np.float32), cv2.COLOR_RGB2Lab)[ic2], 0)), 2)
        f['ampler'].append(dict(konum=[x, y], iou=round(io, 3), leke_kume=kume, leke_esik=int(0.5 * kal * kal), dE00=de,
                                PASS=bool(io >= 0.90 and kume <= int(0.5 * kal * kal) and de <= 1.0)))
    f['PASS'] = bool(len(f['ampler']) == f['beklenen'] and all(q['PASS'] for q in f['ampler']))
    sonuc['f'] = f
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
# g) Etsy teslim dosyasi (8 Eki 2026, ders 199): < 20 MB, 7200x10800, 4:4:4, 300 dpi (ana kopya dahil), halka <= 0.075 (onayli B q97 0.066,
#    bilinen bozuk Pillow q95 0.093-0.098; olcu renk_uyum'da kayan nokta goruntuye gore, teslim_jpg.py)
from PIL import JpegImagePlugin
tes = son.replace('.jpg', '_7200x10800.jpg'); g = dict(dosya=os.path.basename(tes))
if os.path.exists(tes):
    it, im0 = Image.open(tes), Image.open(son); ro_t = s.get('renk', {}).get('teslim') or {}
    g.update(bayt=os.path.getsize(tes), mb=round(os.path.getsize(tes) / 1e6, 2), boyut=list(it.size), ornekleme_444=JpegImagePlugin.get_sampling(it) == 0,
             dpi_teslim=[round(float(v)) for v in it.info.get('dpi', (0, 0))], dpi_ana=[round(float(v)) for v in im0.info.get('dpi', (0, 0))],
             halka=ro_t.get('halka'), halka_kutular=ro_t.get('halka_kutular'))
    g['PASS'] = bool(g['bayt'] < 20_000_000 and g['boyut'] == [7200, 10800] and g['ornekleme_444'] and g['dpi_teslim'] == [300, 300]
                     and g['dpi_ana'] == [300, 300] and g['halka'] is not None and g['halka'] <= 0.075)
else:
    g['PASS'] = False; g['hata'] = 'teslim dosyasi yok'
sonuc['g'] = g
sonuc['PASS'] = bool(all(v['PASS'] for k, v in sonuc.items() if isinstance(v, dict)))
print(json.dumps(sonuc, ensure_ascii=False))
if JS: json.dump(sonuc, open(JS, 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if sonuc['PASS'] else 1)
