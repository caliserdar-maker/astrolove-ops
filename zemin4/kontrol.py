# zemin-4 kontrol + olcum + gorseller. PASS/FAIL, olculebilir esik.
# Kullanim: python kontrol.py REF_JPG YENI_JPG ALFA_NPZ TABAN_PNG ISIK_JSON CIKTI_KLASOR [AMP_JSON]
#  1) oge ici degismezlik: alfa > 0.95 (tum ogeler + &) |yeni - ref| ortalama <= 0.5 (JPEG duzeyi)          (ders 128)
#  2) degisiklik yeri: oge ici / oge kenari (0 < alfa <= 0.95) / cevre bandi (0-128 px) / ara (128-256) / uzak zemin (> 256)
#  3) cevre parlaklik farki dL (ders 160, 2000x3000 olcekte, ders 161): L*(poster) - L*(golgesiz ogesiz zemin tabani),
#     bantlar 2000 olceginde (1-8 px ~ tam cozunurlukte 3.6-29 px), isik tarafi / golge tarafi; ana ve diger ogeler ayri
#  4) gorseller: yan yana tam cozunurluk (7200 + 200 + 7200, ders 169) + 3 kesit (sol mevcut, sag yeni)
import sys, os, json, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
REF, YENI, ALFA, TABAN, ISIK, OD = sys.argv[1:7]
AMP = sys.argv[7] if len(sys.argv) > 7 and os.path.exists(sys.argv[7]) else None
os.makedirs(OD, exist_ok=True)
H, W = 10800, 7200
z = np.load(ALFA)
og = [(str(a), int(x), int(y), z[str(a)]) for (x, y), a in zip(z['_konum'], z['_ad'])]
if AMP:
    for i, q in enumerate(json.load(open(AMP)), 1):
        og.append((f'amp{i}', int(q['x']), int(q['y']), np.load(q['alfa'])))
isik = json.load(open(ISIK)); gd = isik['golge']
gyon = np.array([gd['dx'], gd['dy']], np.float32); gyon /= np.linalg.norm(gyon)       # golge yonu (birim)
Ar = np.asarray(Image.open(REF).convert('RGB')); An = np.asarray(Image.open(YENI).convert('RGB'))
assert Ar.shape == An.shape == (H, W, 3)
sonuc = dict(isik=dict(isik_phi=isik['bant_2_10']['phi_derece'], golge=gd, r2=isik['bant_2_10']['r2'], tutarlilik=isik['tutarlilik_derece']))
# --- 1, 2 ---
U = np.zeros((H, W), np.float32)
for ad, x, y, a in og:
    sl = U[y:y + a.shape[0], x:x + a.shape[1]]; np.maximum(sl, a.astype(np.float32) / 255, out=sl)
d = np.zeros((H, W), np.float32)
for y0 in range(0, H, 1200):
    d[y0:y0 + 1200] = np.abs(An[y0:y0 + 1200].astype(np.float32) - Ar[y0:y0 + 1200].astype(np.float32)).mean(2)
dist = cv2.distanceTransform((U <= 0).astype(np.uint8), cv2.DIST_L2, 5)
bolge = {'oge_ici (alfa>0.95)': U > 0.95, 'oge_kenari (0<alfa<=0.95)': (U > 0) & (U <= 0.95),
         'cevre_bandi (0-128 px)': (U <= 0) & (dist <= 128), 'ara (128-256 px)': (dist > 128) & (dist <= 256), 'uzak_zemin (>256 px)': dist > 256}
yer = {}
for k, m in bolge.items():
    v = d[m]
    yer[k] = dict(px=int(m.sum()), ort=round(float(v.mean()), 3), p999=round(float(np.percentile(v, 99.9)), 1),
                  fark_gt2_yuzde=round(float((v > 2).mean() * 100), 2))
sonuc['degisiklik_yeri'] = yer
sonuc['oge_ici'] = dict(ort=yer['oge_ici (alfa>0.95)']['ort'], esik=0.5, PASS=bool(yer['oge_ici (alfa>0.95)']['ort'] <= 0.5))
oge_basi = {}
for ad, x, y, a in og:
    m = a > 242; oge_basi[ad] = round(float(d[y:y + a.shape[0], x:x + a.shape[1]][m].mean()), 3)
sonuc['oge_ici']['oge_basi_ort'] = oge_basi
del d, dist, bolge
# --- 3: 2000x3000 olcekte cevre dL ---
def k2(im): return cv2.resize(im.astype(np.float32) / 255, (2000, 3000), interpolation=cv2.INTER_AREA)
def Lab_L(rgb): return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)[..., 0]
Lr, Ln = Lab_L(k2(Ar)), Lab_L(k2(An))
Lt = Lab_L(k2(np.asarray(Image.open(TABAN).convert('RGB'))))
U2 = cv2.resize(U, (2000, 3000), interpolation=cv2.INTER_AREA)
def grup_maske(adlar):
    G = np.zeros((H, W), np.float32)
    for ad, x, y, a in og:
        if ad in adlar:
            sl = G[y:y + a.shape[0], x:x + a.shape[1]]; np.maximum(sl, a.astype(np.float32) / 255, out=sl)
    return cv2.resize(G, (2000, 3000), interpolation=cv2.INTER_AREA)
diger = [ad for ad, *_ in og if ad != 'ana']
tablo = {}
for gad, adlar in (('ana', ['ana']), ('diger_ogeler', diger)):
    G2 = grup_maske(adlar)
    gm = (G2 > 0.02).astype(np.uint8)
    dg = cv2.distanceTransform(1 - gm, cv2.DIST_L2, 5)
    dgb = cv2.GaussianBlur(dg, (0, 0), 1.5)
    nx, ny = cv2.Sobel(dgb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(dgb, cv2.CV_32F, 0, 1, ksize=3)
    nn = np.hypot(nx, ny) + 1e-6; c_ = (nx * gyon[0] + ny * gyon[1]) / nn                   # dis normal . golge yonu
    baska = (U2 > 0.02) & (gm == 0)                                                       # diger grubun ogeleri haric
    satir = {}
    # bant: 2000 olceginde px (tam cozunurluk = x3.6). '1-8' ~ tam cozunurlukte 3.6-29 px (ders 160 bandi)
    for bad, (b0, b1) in (('1-3', (1, 3)), ('3-8', (3, 8)), ('1-8 (ders160)', (1, 8)), ('8-30', (8, 30))):
        bm = (dg >= b0) & (dg < b1) & ~baska
        for tad, tm in (('tum', bm), ('isik_tarafi', bm & (c_ < -0.5)), ('golge_tarafi', bm & (c_ > 0.5))):
            satir[f'{bad}|{tad}'] = dict(once=round(float(np.median((Lr - Lt)[tm])), 2), sonra=round(float(np.median((Ln - Lt)[tm])), 2),
                                         px=int(tm.sum()))
    tablo[gad] = satir
sonuc['dL_cevre_2000'] = tablo
sonuc['zemin_L_taban_bant'] = round(float(np.median(Lt[(U2 <= 0.02)])), 2)
del Lr, Ln, Lt, U2
# --- 4: gorseller ---
y_ = Image.new('RGB', (W * 2 + 200, H), (255, 255, 255))
y_.paste(Image.fromarray(Ar), (0, 0)); y_.paste(Image.fromarray(An), (W + 200, 0))
y_.save(f'{OD}/KARSILASTIRMA_ZEMIN_DENEME4.jpg', quality=95, subsampling=0); del y_
def kesit(ad_, x0, y0, x1, y1):
    x0, y0, x1, y1 = int(max(0, x0)), int(max(0, y0)), int(min(W, x1)), int(min(H, y1))
    w, h = x1 - x0, y1 - y0
    im = Image.new('RGB', (2 * w + 100, h), (255, 255, 255))
    im.paste(Image.fromarray(Ar[y0:y1, x0:x1]), (0, 0)); im.paste(Image.fromarray(An[y0:y1, x0:x1]), (w + 100, 0))
    im.save(f'{OD}/{ad_}', quality=95, subsampling=0); return [x0, y0, x1, y1]
K = {ad: (x, y, a) for ad, x, y, a in og}
x, y, a = K['ana']; ys, xs = np.nonzero(a > 127); cy_, cx_ = ys.mean(), xs.mean()
pr = (xs - cx_) * gyon[0] + (ys - cy_) * gyon[1]; i = int(np.argmax(pr))                  # golge yonundeki en uc kenar noktasi
ex, ey = x + xs[i], y + ys[i]
kes = {'KESIT_ANA_KENAR.jpg': kesit('KESIT_ANA_KENAR.jpg', ex - 1000, ey - 1000, ex + 600, ey + 600)}
def kutu(adlar, pay):
    bx = [(K[a_][0], K[a_][1], K[a_][0] + K[a_][2].shape[1], K[a_][1] + K[a_][2].shape[0]) for a_ in adlar]
    return min(b[0] for b in bx) - pay, min(b[1] for b in bx) - pay, max(b[2] for b in bx) + pay, max(b[3] for b in bx) + pay
kes['KESIT_ISIM_KUCUK.jpg'] = kesit('KESIT_ISIM_KUCUK.jpg', *kutu(['isim1', 'kucuk1'], 150))
kes['KESIT_TAGLINE.jpg'] = kesit('KESIT_TAGLINE.jpg', *kutu(['tagline'], 150))
sonuc['kesitler'] = kes
sonuc['PASS'] = sonuc['oge_ici']['PASS']
print(json.dumps(sonuc, ensure_ascii=False))
json.dump(sonuc, open(f'{OD}/ZEMIN4_KONTROL.json', 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if sonuc['PASS'] else 1)
