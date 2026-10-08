# ChatGPT ana sembol birlestirme v2 (7 Eki 2026). Kirmizi tepe hatli ChatGPT ciktisini baski posterine yerlestirir.
# 1) ChatGPT ciktisi -> girdi resmi (kutu olcegi + ECC affine) -> poster koordinati (girdi kirpma bilgisi)
# 2) ChatGPT altin maskesinden yumusak alfa, baski cozunurlugunde keskinlestirilir (kenar ~1.5 px)
# 3) Bu alfa ana oge olarak npz'ye yazilir, motor posteri bu alfayla cizer (golge/parlama ChatGPT silueti ile uyumlu)
# 4) ChatGPT pikselleri ana palete (Lab yuzdelik) esitlenip ayni alfayla bindirilir
# Kullanim: python gpt_birlestir2.py CIFT GPT_CIKTI GIRDI_PNG KAYNAK_KLASOR CIKTI_KLASOR KILIT
import sys, os, json, subprocess, time, numpy as np, cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt
Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
B = '/home/claude/blender/'
c, gpt_yol, girdi_yol, KD, OD, kilit = sys.argv[1:7]
PAY = 150
os.makedirs(OD, exist_ok=True)

def altinlik(rgb):
    # zemin koyu lacivert; sembol = parlak ve mavi olmayan. Tepe parlakliklari (dusuk doygunluk, beyaza yakin) DAHIL.
    f = rgb.astype(np.float32) / 255
    V = f.max(axis=2); sari = f[..., 0] - f[..., 2]
    g = np.clip((V - 0.30) / 0.20, 0, 1) * np.clip((sari + 0.05) / 0.15, 0, 1)
    # ic delikleri kapat (kucuk), cevre ile bagli olmayan zemin degil
    m = (g > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - m, 4)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 60: g[lab == i] = 1
    return g.astype(np.float32)

z = dict(np.load(f'{KD}/{c}_alfa.npz'))
K = dict(zip([str(a) for a in z['_ad']], z['_konum'])); x0, y0 = K['ana']; H, W = z['ana'].shape
G0 = np.asarray(Image.open(gpt_yol).convert('RGB')).astype(np.float32)
Ti = np.asarray(Image.open(girdi_yol).convert('RGB')).astype(np.float32)
s = Ti.shape[1] / (W + 2 * PAY)                       # girdi resmi olcegi (poster kirpma -> girdi)
# KESIK UC duzeltmesi (8 Eki, ders 170-173): ana kutusu PAYLI (ChatGPT girdisindeki pay kadar, poster sinirinda kirpik).
# Eskiden ChatGPT alfasi kaynagin siki kutusuna eslenip kutu disi altin kirpiliyordu (62 ciftte 117 duz kesik).
KPAY = int(os.environ.get('KUTU_PAY', '150'))
kx0, ky0, kW, kH = int(x0), int(y0), W, H                              # kaynak (siki) kutu
px0, py0 = max(0, kx0 - KPAY), max(0, ky0 - KPAY); px1, py1 = min(7200, kx0 + kW + KPAY), min(10800, ky0 + kH + KPAY)
ox, oy = kx0 - px0, ky0 - py0
x0, y0, W, H = px0, py0, px1 - px0, py1 - py0                          # bundan sonra tum isler payli kutuda

# 1) ChatGPT -> girdi
ag = altinlik(G0); at = altinlik(Ti)
mg = ag > 0.5; mt = at > 0.5
ys, xs = np.nonzero(mg); yt, xt = np.nonzero(mt)
sx = (xt.max() - xt.min()) / (xs.max() - xs.min()); sy = (yt.max() - yt.min()) / (ys.max() - ys.min())
M1 = np.array([[sx, 0, xt.min() - xs.min() * sx], [0, sy, yt.min() - ys.min() * sy], [0, 0, 1]])
w = cv2.warpAffine(ag, M1[:2].astype(np.float32), (Ti.shape[1], Ti.shape[0]))
wm = np.eye(2, 3, dtype=np.float32)
_, wm = cv2.findTransformECC(cv2.GaussianBlur(at, (0, 0), 2), cv2.GaussianBlur(w, (0, 0), 2), wm, cv2.MOTION_AFFINE,
                             (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
# ECC: girdi(p) = w(wm*p)  -> w koordinati = wm*p ; tersi: p = inv(wm) * q
E = np.vstack([wm, [0, 0, 1]]).astype(np.float64)
M2 = np.linalg.inv(E) @ M1                             # ChatGPT -> girdi
w2 = cv2.warpAffine(ag, M2[:2].astype(np.float32), (Ti.shape[1], Ti.shape[0])) > 0.5
iou = (w2 & mt).sum() / (w2 | mt).sum()
log('ChatGPT -> girdi IoU', round(float(iou), 3))
# girdi -> ana kutusu: u = (X + PAY) * s  ->  X = u / s - PAY
M3 = np.array([[1 / s, 0, -PAY + ox], [0, 1 / s, -PAY + oy], [0, 0, 1]])
M = M3 @ M2                                            # ChatGPT -> ana kutusu (tam cozunurluk)
F = float(np.sqrt(abs(np.linalg.det(M[:2, :2]))))
log('buyutme', round(F, 2), 'ana', W, 'x', H)

# 2) alfa (tam cozunurluk, keskin kenar)
aw = cv2.warpAffine(cv2.GaussianBlur(ag, (0, 0), 1.0), M[:2].astype(np.float32), (W, H), flags=cv2.INTER_CUBIC)
A = np.clip((aw - 0.5) * F / 2.0 + 0.5, 0, 1).astype(np.float32)
# kucuk adaciklari at (ChatGPT parlama lekeleri)
n, lab, st, _ = cv2.connectedComponentsWithStats((A > 0.5).astype(np.uint8), 8)
buyuk = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
tut = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.002 * st[buyuk, cv2.CC_STAT_AREA]])
tut = cv2.dilate(tut.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
A[~tut] = 0
eski = np.zeros((H, W), np.float32); eski[oy:oy + kH, ox:ox + kW] = z['ana'].astype(np.float32) / 255
# yalniz kaynak sembole DEGEN ChatGPT parcalari (cember parcasi vb. ayri parca disarida kalir). Eski piksel maskesi
# (kaynak + 30 px) kaynaktan uzun ChatGPT uclarini da kesiyordu; artik parca bazli.
yakin = cv2.dilate((eski > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))) > 0
A_ham = A.copy()
n_, lb_, st_, _ = cv2.connectedComponentsWithStats((A > 0.02).astype(np.uint8), 8)
degen = np.unique(lb_[yakin & (lb_ > 0)])
A[~np.isin(lb_, degen)] = 0
iou2 = ((A > 0.5) & (eski > 0.5)).sum() / ((A > 0.5) | (eski > 0.5)).sum()
log('yeni alfa / eski alfa IoU', round(float(iou2), 3))
# --- sekil kapisi (8 Eki): topoloji + yerel fazla/eksik (IoU tek basina CANCER_LEO ek kopruyu kacirdi) ---
def topoloji(m):
    m = np.pad(m.astype(np.uint8), 4); n, _, st, _ = cv2.connectedComponentsWithStats(m, 8)   # pay: dis zemin tek parca
    alan = m.sum(); parca = int(sum(st[1:, cv2.CC_STAT_AREA] > 0.002 * alan))
    nh, _, sth, _ = cv2.connectedComponentsWithStats(1 - m, 4)
    delik = int(sum(sth[1:, cv2.CC_STAT_AREA] > 0.0005 * alan)) - 1          # dis zemin haric
    return parca, delik
ms, mg_ = eski > 0.5, A_ham > 0.5                  # ham ChatGPT silueti (kirpmadan once)
Dm = float(np.median(cv2.distanceTransform(ms.astype(np.uint8), cv2.DIST_L2, 5)[ms])) * 2      # tipik cizgi kalinligi
k_ = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(0.35 * Dm) + 1,) * 2)
mg_ = mg_ & (cv2.dilate(ms.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(3 * Dm) + 1,) * 2)) > 0)   # uzak poster ogeleri (cember yayi) haric
fazla = mg_ & ~(cv2.dilate(ms.astype(np.uint8), k_) > 0)
eksik_ = ms & ~(cv2.dilate(mg_.astype(np.uint8), k_) > 0)
def en_buyuk(m):
    n, _, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8); return int(st[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0
ts, tg = topoloji(ms), topoloji(mg_)
fb, eb = en_buyuk(fazla), en_buyuk(eksik_)
kapi = dict(iou=round(float(iou2), 3), topoloji_kaynak=ts, topoloji_gpt=tg, fazla_px=fb, eksik_px=eb, esik_px=int(0.5 * Dm * Dm))
kapi['PASS'] = bool(iou2 >= 0.88 and ts == tg and fb <= kapi['esik_px'] and eb <= kapi['esik_px'])
# kesik uc kapisi (ders 172): alfa payli kutu kenarina duz kesikle degmemeli (poster siniri haric)
sys.path.insert(0, B); from kesik_uc import kesikler
A8 = np.round(A * 255).astype(np.uint8)
kk = [q for q in kesikler(A8) if not ((q['kenar'] == 'ust' and y0 == 0) or (q['kenar'] == 'sol' and x0 == 0)
                                      or (q['kenar'] == 'alt' and y0 + H == 10800) or (q['kenar'] == 'sag' and x0 + W == 7200))]
kapi['kesik_uc'] = kk; kapi['kutu'] = [int(x0), int(y0), int(W), int(H)]
kapi['PASS'] = bool(kapi['PASS'] and not kk)
log('SEKIL_KAPI', json.dumps(kapi))
if os.environ.get('KAPI_SADECE') == '1': sys.exit(0 if kapi['PASS'] else 3)
z['ana'] = A8
_ad = [str(a) for a in z['_ad']]; kon = z['_konum'].copy(); kon[_ad.index('ana')] = (x0, y0); z['_konum'] = kon
np.savez_compressed(f'{OD}/{c}_alfa.npz', **z)

def gw_hesapla():
    # 4) ChatGPT pikselleri OLDUGU GIBI (tepe parlakliklari korunur). Yalniz dis kenar halkasi icten doldurulur
    #    (ChatGPT'nin kenar parlamasi/koyu hatti), renk tonu ana ornege yalniz ortalama a/b kaydirmasiyla yaklastirilir.
    Gw = cv2.warpAffine(G0, M[:2].astype(np.float32), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    sil = (A > 0.5).astype(np.uint8)
    kes = max(2, int(round(1.2 * F)))
    icg = cv2.erode(sil, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * kes + 1, 2 * kes + 1))) > 0
    bizim = A > 0.01
    eksik = bizim & ~icg
    _, (iy, ix) = distance_transform_edt(~icg, return_indices=True)
    Gw[eksik] = Gw[iy[eksik], ix[eksik]]
    Pm = np.asarray(Image.open(B + 'palet/chatgpt_altin.png').convert('RGB')).astype(np.float32)
    hk = cv2.cvtColor(Pm / 255, cv2.COLOR_RGB2HSV); mk = ((hk[..., 1] > 0.45) & (hk[..., 2] > 0.42)).astype(np.uint8)
    pm = Pm[cv2.erode(mk, np.ones((3, 3), np.uint8)) > 0]
    lab = lambda x: cv2.cvtColor((x.reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    Ls = lab(Gw[icg]); Lt = lab(pm)
    kay = np.array([0, np.median(Lt[:, 1]) - np.median(Ls[:, 1]), np.median(Lt[:, 2]) - np.median(Ls[:, 2])], np.float32)
    log('ton kaydirma a/b', np.round(kay[1:], 2))
    Lall = lab(Gw[bizim]) + kay
    Gw[bizim] = np.clip(cv2.cvtColor(Lall.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
    log('renk esitlendi')
    return Gw

# KATMAN modu (8 Eki, siparis hatti): onayli ana sembol katmanini (RGBA, konum) kaydet ve cik; motor cizimi yok
if os.environ.get('KATMAN_YOL'):
    Gw = gw_hesapla()
    rgba = np.dstack([np.clip(np.round(Gw), 0, 255).astype(np.uint8), z['ana']])
    Image.fromarray(rgba, 'RGBA').save(os.environ['KATMAN_YOL'], optimize=False, compress_level=6)
    json.dump(dict(cift=c, x=int(x0), y=int(y0), w=int(W), h=int(H), kaynak_x=kx0, kaynak_y=ky0, kaynak_w=int(kW), kaynak_h=int(kH),
                   pay=KPAY, gpt=os.path.basename(gpt_yol)), open(os.environ['KATMAN_YOL'] + '.json', 'w'))
    log('katman kaydedildi', os.environ['KATMAN_YOL']); sys.exit(0)

# 3) motor posteri yeni alfayla
Kj = json.load(open(B + kilit))
e = dict(os.environ, **Kj['ortam'], AYAR=json.dumps(Kj['AYAR']), ALFA=f'{OD}/{c}_alfa.npz')
d = f'{OD}/{c}'
p = subprocess.run([B + 'venv/bin/python', B + 'uret_tam.py', d], env=e, capture_output=True, text=True)
if p.returncode: print(p.stderr[-1500:]); sys.exit(1)
log('motor posteri bitti')

Gw = gw_hesapla()
Pp = np.asarray(Image.open(f'{d}/SV_BLENDER_tam.png').convert('RGB')).astype(np.float32)
reg = Pp[y0:y0 + H, x0:x0 + W]; a3 = A[..., None]
Pp[y0:y0 + H, x0:x0 + W] = Gw * a3 + reg * (1 - a3)
rs = np.random.default_rng(11)
out = np.clip(np.round(Pp + rs.random(Pp.shape, dtype=np.float32) - rs.random(Pp.shape, dtype=np.float32)), 0, 255).astype(np.uint8)
Image.fromarray(out).save(f'{d}/{c}_GPT_7200x10800.jpg', quality=100, subsampling=0)
on = np.empty((3000, 2000, 3), np.uint8)
for yy in range(0, 10800, 1800):
    bf = cv2.resize(Pp[yy:yy + 1800], (2000, 500), interpolation=cv2.INTER_AREA)
    bf += rs.random(bf.shape, dtype=np.float32) - rs.random(bf.shape, dtype=np.float32)
    on[yy // 1800 * 500:yy // 1800 * 500 + 500] = np.clip(np.round(bf), 0, 255).astype(np.uint8)
Image.fromarray(on).save(f'{d}/{c}_GPT_2000.jpg', quality=100, subsampling=0)
# ana sembol yakin plani (girdi olceginde) karsilastirma icin
Image.fromarray(out[max(0, ky0 - PAY):ky0 + kH + PAY, max(0, kx0 - PAY):kx0 + kW + PAY]).resize((Ti.shape[1], Ti.shape[0]), Image.LANCZOS).save(f'{d}/{c}_GPT_ana.png')
os.remove(f'{d}/SV_BLENDER_tam.png')
for f_ in ('SV_BLENDER_tam_q100.jpg', 'SV_BLENDER_2000.jpg'):   # disk: motor ara ciktilari gereksiz
    if os.path.exists(f'{d}/{f_}'): os.remove(f'{d}/{f_}')
log('bitti', d)
