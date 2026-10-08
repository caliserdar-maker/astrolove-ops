# Ana sembol altininin isik yonu (zemin-4, ders 160): ChatGPT katmani (RGBA) ic kenar bandinda L*, dis normal acisina gore
# L = a + b cos(t) + c sin(t) en kucuk kareler. Isik yonu phi = atan2(c, b) (goruntu koordinati, y asagi): en parlak kenarin
# baktigi yon. Golge ofseti = isigin tersi, buyukluk mevcut golgeyle ayni (|(10,16)|), temas ayni sekilde (|(2,3)|).
# Kullanim: python isik_yonu.py KATMAN_PNG CIKTI_JSON
import sys, json, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ka = np.asarray(Image.open(sys.argv[1]).convert('RGBA'))
A = ka[..., 3].astype(np.float32) / 255
m = (A > 0.5).astype(np.uint8)
d = cv2.distanceTransform(m, cv2.DIST_L2, 5)
Ab = cv2.GaussianBlur(A, (0, 0), 3.0)
gx = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
gm = np.hypot(gx, gy)
L = cv2.cvtColor(ka[..., :3].astype(np.float32) / 255, cv2.COLOR_RGB2Lab)[..., 0]
sonuc = {}
for ad, (d0, d1) in {'bant_2_6': (2, 6), 'bant_2_10': (2, 10), 'bant_6_14': (6, 14)}.items():
    s = (A > 0.95) & (d >= d0) & (d < d1) & (gm > 1e-3)
    t = np.arctan2(-gy[s], -gx[s])                                   # dis normal (alfa azalan yon)
    X = np.stack([np.ones_like(t), np.cos(t), np.sin(t)], 1); y = L[s]
    co, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ co) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    # 8 yon ortancasi (aciklik icin): 0 = sag, 90 = asagi
    yon8 = {int(k): round(float(np.median(y[(np.round(np.degrees(t) / 45) % 8) == k // 45])), 2) for k in range(0, 360, 45)}
    sonuc[ad] = dict(n=int(s.sum()), a=round(float(co[0]), 2), genlik=round(float(np.hypot(co[1], co[2])), 2),
                     phi_derece=round(float(np.degrees(np.arctan2(co[2], co[1]))) % 360, 1), r2=round(float(r2), 3), yon8_L=yon8)
phi = np.radians(sonuc['bant_2_10']['phi_derece'])
mg, mt = float(np.hypot(10, 16)), float(np.hypot(2, 3))
sonuc['golge'] = dict(dx=round(-mg * np.cos(phi), 2), dy=round(-mg * np.sin(phi), 2), tdx=round(-mt * np.cos(phi), 2), tdy=round(-mt * np.sin(phi), 2),
                      mevcut=dict(dx=10, dy=16, tdx=2, tdy=3, isik_phi_derece=round(float(np.degrees(np.arctan2(-16, -10))) % 360, 1)))
fz = [sonuc[k]['phi_derece'] for k in ('bant_2_6', 'bant_2_10', 'bant_6_14')]
sonuc['tutarlilik_derece'] = round(max(abs((a - b + 180) % 360 - 180) for a in fz for b in fz), 1)   # bantlar arasi en buyuk aci farki
print(json.dumps(sonuc, ensure_ascii=False))
json.dump(sonuc, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
