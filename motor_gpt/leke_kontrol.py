# Leke kontrolu (8 Eki 2026, Serdar: deneme 2'de dokularda leke, TUM ogelerde). Kaynak ve yeni poster karsilastirilir.
# Kullanim: python leke_kontrol.py KAYNAK_JPG YENI_JPG ALFA_NPZ [--json CIKTI]
# Oge basina (ana, kucuk1/2, sonsuz, isim1/2, tagline, cember), oge ICI (alfa > 127, kenardan 3 px iceride):
#   r = L*(yeni) - L*(kaynak) - ortanca(L* farki)      (ortalama kaydirma cikarilir; kalan = yerel doku bozulmasi)
#   |r| > 6 bagli kumeler (8 komsuluk); en buyuk kume alani > 0.5 * kalinlik^2 ise FAIL
#   kalinlik = oge alfasi mesafe donusumu ortancasi x 2 (ders 139 olcusu)
import sys, json, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
KAY, YENI, ALFA = sys.argv[1:4]
JS = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
z = np.load(ALFA)
# --eski NPZ: oge ici = yeni VE eski alfa ici (kesik uc duzeltmesinde yeni eklenen altin "leke" sayilmaz; yalniz ortak doku olculur)
ze = np.load(sys.argv[sys.argv.index('--eski') + 1]) if '--eski' in sys.argv else None
def eski_maske(ad, x, y, h, w):
    if ze is None: return np.ones((h, w), bool)
    Ke = {str(a): (int(xx), int(yy)) for (xx, yy), a in zip(ze['_konum'], ze['_ad'])}; ex, ey = Ke[ad]; ea = ze[ad] > 127
    out = np.zeros((h, w), bool); x0, y0 = max(ex, x), max(ey, y); x1, y1 = min(ex + ea.shape[1], x + w), min(ey + ea.shape[0], y + h)
    if x1 > x0 and y1 > y0: out[y0 - y:y1 - y, x0 - x:x1 - x] = ea[y0 - ey:y1 - ey, x0 - ex:x1 - ex]
    return out
A, B = Image.open(KAY), Image.open(YENI)
def L_(im, kutu): return cv2.cvtColor(np.asarray(im.crop(kutu).convert('RGB')).astype(np.float32) / 255, cv2.COLOR_RGB2Lab)[..., 0]
sonuc = {}
for (x, y), ad in zip(z['_konum'], z['_ad']):
    ad = str(ad); al = z[ad]; h, w = al.shape; x, y = int(x), int(y)
    m = al > 127
    kal = float(np.median(cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)[m])) * 2
    ic = cv2.distanceTransform((m & eski_maske(ad, x, y, h, w)).astype(np.uint8), cv2.DIST_L2, 5) > 3
    d = L_(B, (x, y, x + w, y + h)) - L_(A, (x, y, x + w, y + h))
    kay = float(np.median(d[ic])); r = d - kay
    n, _, st, _ = cv2.connectedComponentsWithStats(((np.abs(r) > 6) & ic).astype(np.uint8), 8)
    kume = int(st[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0
    esik = int(0.5 * kal * kal)
    sonuc[ad] = dict(kaydirma_L=round(kay, 2), kalan_std=round(float(r[ic].std()), 2), kume_px=kume, esik_px=esik,
                     kalinlik=round(kal, 1), PASS=bool(kume <= esik))
sonuc['PASS'] = bool(all(v['PASS'] for v in sonuc.values()))
print(json.dumps(sonuc, ensure_ascii=False))
if JS: json.dump(sonuc, open(JS, 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if sonuc['PASS'] else 1)
