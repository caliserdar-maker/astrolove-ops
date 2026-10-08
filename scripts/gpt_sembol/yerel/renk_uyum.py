# Ogeler arasi renk uyumu (8 Eki 2026): kucuk semboller, sonsuz, isimler, tagline, cember -> ana sembolun (ChatGPT) altini.
# Golge/doku AYNI kalir (Serdar eski ogeleri begendi); yalniz Lab ortanca kaydirmasi. Hedef: her oge dE00 <= 1 (ana ile).
# Kullanim: python renk_uyum.py CIFT TABAN_KLASOR CIKTI_KLASOR [--olc]
import sys, os, json, time, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
c, TB, OD = sys.argv[1:4]; SADECE_OLC = '--olc' in sys.argv
OGELER = ('kucuk1', 'kucuk2', 'sonsuz', 'isim1', 'isim2', 'tagline', 'cember')

def de00(L1, L2):
    L1, a1, b1 = L1; L2, a2, b2 = L2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    if C1p * C2p == 0: hpm = hs
    elif abs(h1p - h2p) <= 180: hpm = hs / 2
    else: hpm = (hs + 360) / 2 if hs < 360 else (hs - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))

lab = lambda x: cv2.cvtColor((x.reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
z = np.load(f'{TB}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
src = f'{TB}/{c}/{c}_GPT_7200x10800.jpg'
P = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)

def ic(ad):
    a = z[ad].astype(np.float32) / 255
    m = cv2.erode((a > 0.95).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return a, m

def ortanca(ad):
    x, y = K[ad]; a, m = ic(ad)
    return np.median(lab(P[y:y + a.shape[0], x:x + a.shape[1]][m]), 0)

Lana = ortanca('ana')
once = {ad: round(de00(Lana, ortanca(ad)), 2) for ad in OGELER if ad in K}
log('dE00 once', once)
if SADECE_OLC: print(json.dumps(once)); sys.exit(0)
kay = {}
for ad in OGELER:
    if ad not in K: continue
    x, y = K[ad]; a, m = ic(ad); h, w = a.shape
    d = Lana - ortanca(ad); kay[ad] = np.round(d, 2).tolist()
    reg = P[y:y + h, x:x + w]; sec = a > 0.003
    L = lab(reg[sec]) + d[None, :] * a[sec][:, None]                       # kenarda alfa kadar (yumusak gecis)
    reg[sec] = np.clip(cv2.cvtColor(L.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
sonra = {ad: round(de00(Lana, ortanca(ad)), 2) for ad in OGELER if ad in K}
log('kaydirma Lab', kay); log('dE00 sonra', sonra)
os.makedirs(f'{OD}/{c}', exist_ok=True)
rs = np.random.default_rng(11)
out = np.clip(np.round(P + rs.random(P.shape, dtype=np.float32) - rs.random(P.shape, dtype=np.float32)), 0, 255).astype(np.uint8)
Image.fromarray(out).save(f'{OD}/{c}/{c}_7200x10800.jpg', quality=100, subsampling=0)
on = np.empty((3000, 2000, 3), np.uint8)
for yy in range(0, 10800, 1800):
    bf = cv2.resize(P[yy:yy + 1800], (2000, 500), interpolation=cv2.INTER_AREA)
    bf += rs.random(bf.shape, dtype=np.float32) - rs.random(bf.shape, dtype=np.float32)
    on[yy // 1800 * 500:yy // 1800 * 500 + 500] = np.clip(np.round(bf), 0, 255).astype(np.uint8)
Image.fromarray(on).save(f'{OD}/{c}/{c}_2000.jpg', quality=100, subsampling=0)
json.dump(dict(once=once, sonra=sonra, kaydirma=kay, PASS=all(v <= 1.0 for v in sonra.values())), open(f'{OD}/{c}/renk_olcum.json', 'w'), indent=1)
log('bitti', 'PASS' if all(v <= 1.0 for v in sonra.values()) else 'FAIL')
