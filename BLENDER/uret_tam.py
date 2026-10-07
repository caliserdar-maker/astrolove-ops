# SCORPIO_VIRGO tam poster 7200x10800: Blender altin malzeme (tek kure haritasi) + REF renk paleti, tum ogelere AYNI kural
import sys, os, time, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/home/claude/blender')
from golge_motor import kure_yukle, egim_tup, gurultu_egim, golgele_g, luma, renk_haritasi, uygula_harita, srgb, lineer, renk_haritasi_dogrusal, uygula_harita2
Image.MAX_IMAGE_PIXELS = None
T = time.time()
def log(*a): print(f'[{time.time()-T:6.1f}s]', *a, flush=True)
W, H = 7200, 10800
P = dict(pah=0.6, k=0.8, karisim=0.0, g=0.5, gs=60, golge_sigma=12, golge_dx=6, golge_dy=10, golge_opak=0.55, m1=0.0, m2=0.0, poz=1.0, pah_px=0.0, kubbe=0.0, kure='studio2', mot_yer='Y', esit='goz', temas=0.0, zemin_daire=0, sarma=0.0, arka_isik=0.0, renk_ayar=0.0, kararma=0.0, yansima=0.0, isima=0.0, isima_sigma=30.0, gren=0.0, kenar_yum=0.0, egim_max=0.0, pah_oran_max=0.0, ton=0.0, yildiz='t5', parilti=0.0, parilti_esik=2.3, isik_leke=0.0, mot_poz=0, mot_s2=5.0, harita='sira')
P.update(json.loads(os.environ.get('AYAR', '{}')))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/blender/cikti'
import os; os.makedirs(OUT, exist_ok=True)
z = np.load(os.environ.get('ALFA', '/home/claude/blender/alfa_ogeler.npz'))
ogeler = [(str(a), int(x), int(y), z[str(a)]) for (x, y), a in zip(z['_konum'], z['_ad'])]
K = kure_yukle(f"/home/claude/blender/kure/{P['kure']}.exr")

# --- 1 zemin: REF radyal profil, lineer isikta, kayan nokta; TPDF titresim ile 8 bit (halka yok) ---
Z = json.load(open('/home/claude/blender/zemin_profil.json'))
s = W / Z['olcek']; rr = np.array(Z['r'], np.float32) * s
cx, cy, e = Z['cx'] * s, Z['cy'] * s, Z['e']
LIN = [np.array(Z['lin'][c], np.float32) for c in range(3)]
if P['zemin_daire']:                                                 # 360 derece ayni koyulasma: daire, tekduze azalan, yumusak profil
    e = 1.0
    Ly = 0.2126 * LIN[0] + 0.7152 * LIN[1] + 0.0722 * LIN[2]
    Ly = np.minimum.accumulate(Ly)                                   # merkezden disa hic aydinlanma yok
    Ly = cv2.GaussianBlur(np.r_[np.full(60, Ly[0]), Ly, np.full(60, Ly[-1])].reshape(-1, 1).astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=25).ravel()[60:-60]
    Ly = np.minimum.accumulate(Ly)
    oran = [LIN[c] / np.maximum(0.2126 * LIN[0] + 0.7152 * LIN[1] + 0.0722 * LIN[2], 1e-6) for c in range(3)]
    renk = [float(np.median(o[:80])) for o in oran]                   # merkez rengi
    renk2 = [float(np.median(o[-80:])) for o in oran]                 # dis renk
    tt = np.linspace(0, 1, len(Ly)).astype(np.float32)
    LIN = [(Ly * (renk[c] * (1 - tt) + renk2[c] * tt)).astype(np.float32) for c in range(3)]
zemin = np.empty((H, W, 3), np.float32)
xs = np.arange(W, dtype=np.float32)
for y0 in range(0, H, 600):
    yy = np.arange(y0, min(H, y0 + 600), dtype=np.float32)[:, None]
    r = np.hypot(xs[None] - cx, (yy - cy) * e)
    for c in range(3):
        zemin[y0:y0 + len(yy), :, c] = np.interp(r, rr, LIN[c])
log('zemin')

# --- 2 yildizlar: T5 posterden (oge bolgeleri disi), yerel zemine gore fazlalik; satir bloklariyla (bellek) ---
t5 = np.asarray(Image.open('/home/claude/ao/KANIT/SCORPIO_VIRGO_T5_FAIL_tam.png').convert('RGB'))
oge_maske = np.zeros((H, W), np.uint8)
for ad, x, y, a in ogeler:
    oge_maske[y:y + a.shape[0], x:x + a.shape[1]] |= (a > 0).astype(np.uint8)
oge_maske = cv2.dilate(oge_maske, np.ones((61, 61), np.uint8))
kucuk = cv2.resize(t5.mean(2).astype(np.float32) / 255 if False else cv2.cvtColor(t5, cv2.COLOR_RGB2GRAY), (W // 16, H // 16), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
ny_ = 0
B, PD = 1200, 200
for y0 in range(0, H if P['yildiz'] == 't5' else 0, B):
    ya, yb = max(0, y0 - PD), min(H, y0 + B + PD)
    blk = t5[ya:yb].astype(np.float32) / 255
    lum = blk.mean(2)
    yerel = cv2.resize(kucuk, (W, H // 16 * 16 // 16 * 16), interpolation=cv2.INTER_LINEAR) if False else None
    yerel = cv2.resize(kucuk[ya // 16:yb // 16 + 2], (W, (yb // 16 + 2 - ya // 16) * 16), interpolation=cv2.INTER_LINEAR)[ya % 16:ya % 16 + (yb - ya)]
    fazla = np.clip(lum - yerel - 0.02, 0, None) * (1 - oge_maske[ya:yb])
    n, lab, st, _ = cv2.connectedComponentsWithStats((fazla > 0.03).astype(np.uint8))
    iyi = np.zeros(n, bool); iyi[1:] = (st[1:, 4] >= 4) & (st[1:, 4] <= 20000)
    yil = iyi[lab]
    yil = cv2.dilate(yil.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    ya_ = (np.clip(fazla / 0.08, 0, 1) * yil)[y0 - ya:y0 - ya + B]
    if ya_.max() == 0: continue
    yrgb = lineer(blk[y0 - ya:y0 - ya + B])
    z = zemin[y0:y0 + B]
    z[:] = z * (1 - ya_[..., None]) + np.maximum(yrgb, z) * ya_[..., None]
    ny_ += int(iyi.sum())
del t5, oge_maske
log('yildizlar', ny_)

if P['yildiz'] == 'ref':
    # REF yildizlari: konum, boyut ve parlaklik REF'ten; tam cozunurlukte keskin isilti (cekirdek + hale + 8 isin)
    rf = np.asarray(Image.open('/home/claude/ref/ref.png').convert('RGB')).astype(np.float32)
    Lr = rf.mean(2); mr = cv2.medianBlur(Lr.astype(np.uint8), 15).astype(np.float32)
    fr = ((Lr - mr) > 25).astype(np.uint8); fr[400:2700, 150:1850] = 0
    n_, lr_, st_, cr_ = cv2.connectedComponentsWithStats(fr)
    sy = 0
    for i in range(1, n_):
        a_ = st_[i, 4]
        if a_ < 3: continue
        tepe = float((Lr - mr)[lr_ == i].max()) / 255
        cx_, cy_ = cr_[i] * 3.6; R = 3.6 * np.sqrt(a_ / np.pi)          # tam cozunurluk yaricap
        S = int(R * 7) + 8
        x0_, y0_ = int(cx_) - S, int(cy_) - S
        if x0_ < 0 or y0_ < 0 or x0_ + 2 * S >= W or y0_ + 2 * S >= H: continue
        yy, xx = np.mgrid[-S:S, -S:S].astype(np.float32); xx += (S - (cx_ - x0_)); yy += (S - (cy_ - y0_))
        r = np.hypot(xx, yy); th = np.arctan2(yy, xx)
        cek = np.exp(-(r / (0.45 * R)) ** 2)
        hale = 0.35 * np.exp(-(r / (1.3 * R)) ** 2)
        isin = np.zeros_like(r)
        for k_ in range(8):
            t0 = k_ * np.pi / 4 + 0.3; boy = (4.5 if k_ % 2 == 0 else 3.2) * R
            dt_ = np.abs(np.angle(np.exp(1j * (th - t0))))
            gen = 0.06 + 0.04 * R / 10
            isin += 0.45 * np.exp(-(r * np.sin(np.minimum(dt_, np.pi / 2)) / (gen * R + 0.8)) ** 2) * np.clip(1 - r / boy, 0, 1) * (np.cos(dt_) > 0)
        I_ = cek[..., None] * np.array([1.0, 0.95, 0.82])[None, None]
        I_ = I_ + (hale + isin)[..., None] * np.array([0.95, 0.72, 0.36])[None, None]
        zemin[y0_:y0_ + 2 * S, x0_:x0_ + 2 * S] += (I_ * tepe * 1.3).astype(np.float32)
        sy += 1
    log('REF yildizlari', sy)

if P['yildiz'] == 'refkopya':
    # REF yildizlarinin KENDISI: REF yamasi (yerel zemin cikarilmis fazlalik), 3.6x buyutulup ayni yere eklenir
    rf = np.asarray(Image.open('/home/claude/ref/ref.png').convert('RGB')).astype(np.float32) / 255
    rl = lineer(rf)
    Lr = rf.mean(2); mr = cv2.medianBlur((Lr * 255).astype(np.uint8), 15).astype(np.float32) / 255
    fr = ((Lr - mr) > 0.06).astype(np.uint8); fr[400:2700, 150:1850] = 0
    n_, lr_, st_, cr_ = cv2.connectedComponentsWithStats(fr)
    zem = np.stack([cv2.medianBlur(np.ascontiguousarray((rf[..., k] * 255).astype(np.uint8)), 21) for k in range(3)], -1).astype(np.float32) / 255
    fz = np.clip(rl - lineer(zem), 0, None)                              # yildiz isigi (lineer fazlalik)
    sy = 0
    for i in range(1, n_):
        if st_[i, 4] < 2: continue
        cx_, cy_ = cr_[i]; S2 = 16
        x0r, y0r = int(round(cx_)) - S2, int(round(cy_)) - S2
        if x0r < 0 or y0r < 0 or x0r + 2 * S2 >= 2000 or y0r + 2 * S2 >= 3000: continue
        yama = fz[y0r:y0r + 2 * S2, x0r:x0r + 2 * S2]
        ag = np.hypot(*np.mgrid[-S2:S2, -S2:S2]) ; yama = yama * np.clip((S2 - ag) / 4, 0, 1)[..., None]   # yumusak kenar
        B = cv2.resize(yama, None, fx=3.6, fy=3.6, interpolation=cv2.INTER_CUBIC)
        B = np.clip(B, 0, None)
        X0, Y0 = int(round(x0r * 3.6)), int(round(y0r * 3.6))
        hh, ww = B.shape[:2]
        if X0 + ww > W or Y0 + hh > H: continue
        zemin[Y0:Y0 + hh, X0:X0 + ww] += B
        sy += 1
    log('REF yildiz kopya', sy)

# --- 3 harita: ana sembolden (REF paleti) ---
ref = np.asarray(Image.open('/home/claude/ref/ref.png').convert('RGB')).astype(np.float32) / 255
hsv = cv2.cvtColor(ref, cv2.COLOR_RGB2HSV); rm = ((hsv[..., 1] > 0.45) & (hsv[..., 2] > 0.42)).astype(np.uint8)
s36 = 3.6; ry0, ry1, rx0, rx1 = int(2848 / s36), int(5710 / s36), int(1866 / s36), int(5337 / s36)
core = cv2.erode(rm, np.ones((3, 3), np.uint8))[ry0:ry1, rx0:rx1] > 0
ref_ana = ref[ry0:ry1, rx0:rx1][core]

def golgele_oge(a, ox, oy):
    """parca parca (bellek): 2048 karo, 128 bindirme. Gurultu poster koordinatinda (ayni alan)."""
    A = a.astype(np.float32) / 255
    h, w = A.shape; Yt = np.zeros((h, w), np.float32); At = np.zeros((h, w), np.float32)
    KR, PD = 2048, 128
    for y0 in range(0, h, KR):
        for x0 in range(0, w, KR):
            ya, xa = max(0, y0 - PD), max(0, x0 - PD); yb, xb = min(h, y0 + KR + PD), min(w, x0 + KR + PD)
            Ak = A[ya:yb, xa:xb]
            if Ak.max() == 0: continue
            Ak = np.pad(Ak, 16)
            gx, gy, Al = egim_tup(Ak, P['k'], pah=P['pah'], karisim=P['karisim'], pah_px=P['pah_px'], kubbe=P['kubbe'], egim_max=P['egim_max'], pah_oran_max=P['pah_oran_max'])
            gx, gy, Al = gx[16:-16, 16:-16], gy[16:-16, 16:-16], Al[16:-16, 16:-16]
            # gurultu: poster koordinatinda sabit tohumlu alan (her ogede ayni istatistik)
            Nx, Ny = gurultu_egim_poster(oy + ya, ox + xa, yb - ya, xb - xa)
            gx = gx + Nx * Al; gy = gy + Ny * Al
            Y = luma(golgele_g(gx, gy, K))
            sr = getattr(egim_tup, 'sirt', None)
            if sr is not None:                                      # sirt kenar yumusatma RENK uzayinda (iki yuzun ortasi, ucuncu renk yok)
                sr = sr[16:-16, 16:-16] if sr.shape != Y.shape else sr
                Yb = cv2.GaussianBlur(Y, (0, 0), 0.7)
                Y = np.where(sr, Yb, Y).astype(np.float32)
                egim_tup.sirt = None
            ia, ib, ja, jb = y0 - ya, min(KR, h - y0) + (y0 - ya), x0 - xa, min(KR, w - x0) + (x0 - xa)
            Yt[y0:y0 + ib - ia, x0:x0 + jb - ja] = Y[ia:ib, ja:jb]
            At[y0:y0 + ib - ia, x0:x0 + jb - ja] = Al[ia:ib, ja:jb]
    return Yt, At

# poster genelinde tek gurultu alani (bir kez uretilir, parcalardan okunur)
NZ = None
def gurultu_egim_poster(y, x, h, w):
    global NZ
    if NZ is None:
        nx_, ny_ = gurultu_egim((H // 2, W // 2), 7, P['gs'] / 2, P['g'])   # yarim cozunurluk alan, sonra 2x
        NZ = (nx_ * 0.5, ny_ * 0.5)                                         # turev olcegi (yarim cozunurluk)
    gx = cv2.resize(NZ[0][y // 2:(y + h) // 2 + 2, x // 2:(x + w) // 2 + 2], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gy = cv2.resize(NZ[1][y // 2:(y + h) // 2 + 2, x // 2:(x + w) // 2 + 2], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    o0, o1 = y % 2, x % 2
    return gx[o0:o0 + h, o1:o1 + w], gy[o0:o0 + h, o1:o1 + w]

# cekic/benek dokusu: poster koordinatinda TEK alan (yarim cozunurluk, 2 olcek), carpimsal, ortalamasi 0
rs_m = np.random.default_rng(23)
def alan(sig):
    n = cv2.GaussianBlur(rs_m.standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), sig)
    return n / n.std()
MOT = (alan(1.5), alan(P['mot_s2']))
def benek(x, y, h, w):
    o = np.zeros((h, w), np.float32)
    for n, a in zip(MOT, (P['m1'], P['m2'])):
        if a == 0: continue
        b = cv2.resize(n[y // 2:(y + h) // 2 + 2, x // 2:(x + w) // 2 + 2], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        b = b[y % 2:y % 2 + h, x % 2:x % 2 + w]
        if P['mot_poz']: b = np.clip(b - 0.3, 0, None)                # yalniz aciga (isik lekesi), koyu leke yok
        o += a * b
    return o
Ys = {}
for ad, x, y, a in ogeler:
    Yo, Ao = golgele_oge(a, x, y)
    if (P['m1'] or P['m2']) and P['mot_yer'] == 'Y':
        Yo = Yo * np.exp(benek(x, y, *Ao.shape))                  # benek parlaklik uzayinda, REF paleti ondan sonra
    Ys[ad] = (Yo, Ao)
    log('golge', ad, a.shape)
Y, A = Ys['ana']
cm = cv2.erode((A > 0.99).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
har = renk_haritasi_dogrusal(Y[cm], ref_ana) if P['harita'] == 'dogrusal' else renk_haritasi(Y[cm], ref_ana)
np.save(f'{OUT}/harita.npy', np.array(har, dtype=object), allow_pickle=True)
log('harita')

# --- 4 golge (tum ogeler ayni) ---
Atum = np.zeros((H, W), np.float32)
for ad, x, y, a in ogeler:
    Y, A = Ys[ad]; sl = Atum[y:y + A.shape[0], x:x + A.shape[1]]; np.maximum(sl, A, out=sl)
g = cv2.GaussianBlur(Atum, (0, 0), P['golge_sigma'])
M = np.float32([[1, 0, P['golge_dx']], [0, 1, P['golge_dy']]])
g = cv2.warpAffine(g, M, (W, H)) * P['golge_opak']
if P['temas']:                                                      # temas golgesi: oge zemine degdigi yerde dar koyuluk
    gt = cv2.GaussianBlur(Atum, (0, 0), 4.0)
    gt = cv2.warpAffine(gt, np.float32([[1, 0, 2], [0, 1, 3]]), (W, H)) * P['temas']
    g = 1 - (1 - g) * (1 - gt); del gt
zemin *= (1 - g[..., None]); del g
log('golge katmani')

# --- 5 altin ogeler ---
ISIK = np.zeros((H // 4 + 2, W // 4 + 2, 3), np.float32) if P['isima'] else None
olcum = {}
QS = [2, 5, 25, 50, 75, 95, 98]
def gorunen(Y, A):
    """goz olcegi (2000 px poster): alfa agirlikli kucultme, dolu pikseller"""
    f = 1 / 3.6
    ya = cv2.resize(Y * A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    aa = cv2.resize(A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return (ya / np.maximum(aa, 1e-4))[aa > 0.85]
def cekirdek_Y(Y, A): return Y[cv2.erode((A > 0.99).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0]
ESIT = gorunen if P['esit'] == 'goz' else cekirdek_Y
Ya, Aa = Ys['ana']; qa = np.percentile(ESIT(Ya, Aa), QS)
# parilti (yalniz PARLAK yonde): seyrek beyaz parilti + yumusak isik lekeleri; poster koordinatinda tek alan
rs_p = np.random.default_rng(31)
def alan2(sig):
    n = cv2.GaussianBlur(rs_p.standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), sig)
    return n / n.std()
PAR = (alan2(1.2), alan2(7.0)) if (P['parilti'] or P['isik_leke']) else None
def parilti(x, y, h, w):
    o = np.zeros((h, w), np.float32)
    for n, a, esik in zip(PAR, (P['parilti'], P['isik_leke']), (P['parilti_esik'], 0.8)):
        if a == 0: continue
        b = cv2.resize(n[y // 2:(y + h) // 2 + 2, x // 2:(x + w) // 2 + 2], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        b = b[y % 2:y % 2 + h, x % 2:x % 2 + w]
        o += a * np.clip(b - esik, 0, None) ** 1.5
    return o
duzelt = {}
for ad, x, y, a in ogeler:
    Y, A = Ys[ad]
    if ad != 'ana':   # oge butunu icin TEK yumusak parlaklik egrisi (harf/parca bazli DEGIL), goz olceginde ana sembole
        if P['esit'] == 'kazanc':                                   # tek carpan: ortanca ana sembole (dik egri yok)
            Y = (Y * (qa[3] / max(np.percentile(cekirdek_Y(Y, A), 50), 1e-6))).astype(np.float32)
        else:
          for _ in range(2):
            qo = np.percentile(ESIT(Y, A), QS); qo = np.maximum.accumulate(qo + np.arange(len(qo)) * 1e-5)
            Y = np.interp(Y, qo, qa).astype(np.float32)
        duzelt[ad] = P['esit']
    rgb_s = uygula_harita2(Y, har)
    if P['ton']:                                                    # ton dondurme (derece, + = turuncuya), tum ogeler ayni
        lab = cv2.cvtColor(np.clip(rgb_s, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)
        c, s_ = np.cos(np.radians(-P['ton'])), np.sin(np.radians(-P['ton']))
        a_, b_ = lab[..., 1].copy(), lab[..., 2].copy()
        lab[..., 1] = a_ * c - b_ * s_; lab[..., 2] = a_ * s_ + b_ * c
        rgb_s = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
    rgb = lineer(rgb_s) * P['poz']
    if PAR is not None:                                             # parilti beyaza dogru (renk doygunlugu azalir)
        pp = parilti(x, y, *A.shape)[..., None]
        rgb = rgb + pp * (np.array([1.0, 0.93, 0.78], np.float32) - rgb * 0.3)
    if (P['m1'] or P['m2']) and P['mot_yer'] == 'rgb':              # benek REF paletinden SONRA: dik esleme buyutmez
        rgb *= np.exp(benek(x, y, *A.shape))[..., None]
    sl = zemin[y:y + A.shape[0], x:x + A.shape[1]]
    if P['yansima']:                                                # koyu yuzler cevredeki laciverti yansitir (ayni kural her ogede)
        zr = cv2.GaussianBlur(sl, (0, 0), 25)
        yk = np.clip(1 - luma(rgb) / max(float(np.percentile(luma(rgb)[A > 0.9], 90)), 1e-4), 0, 1)[..., None]
        rgb = rgb * (1 - P['yansima'] * yk) + zr * 6.0 * P['yansima'] * yk
    if P['sarma'] or P['arka_isik']:
        Ab = cv2.GaussianBlur(A, (0, 0), 3.0)
        bant = np.clip(A - Ab, 0, None) * 2.0                       # ic kenar bandi (~3 px), kenarda 1'e yakin
        bant = np.clip(bant, 0, 1)[..., None]
        if P['sarma']:                                              # kenar sarmasi: zeminin isigi/rengi kenara sizar
            ia = (1 - A).astype(np.float32)
            zw = cv2.GaussianBlur(sl * ia[..., None], (0, 0), 6.0) / np.maximum(cv2.GaussianBlur(ia, (0, 0), 6.0), 1e-4)[..., None]
            rgb = rgb * (1 - P['sarma'] * bant) + zw * 4.0 * P['sarma'] * bant
        if P['arka_isik']:                                          # arka isik: zeminin parlak merkezine bakan kenarlarda ince parilti
            nx_ = cv2.Sobel(Ab, cv2.CV_32F, 1, 0, ksize=3); ny_ = cv2.Sobel(Ab, cv2.CV_32F, 0, 1, ksize=3)
            nn = np.sqrt(nx_ ** 2 + ny_ ** 2) + 1e-6
            yy_, xx_ = np.mgrid[y:y + A.shape[0], x:x + A.shape[1]].astype(np.float32)
            dx_, dy_ = cx - xx_, cy - yy_; dd = np.sqrt(dx_ ** 2 + dy_ ** 2) + 1e-6
            yon = np.clip(-(nx_ * dx_ + ny_ * dy_) / (nn * dd), 0, 1)  # dis normal merkeze bakiyor (gradyan ice dogru)
            yak = np.exp(-(dd / (W * 0.55)) ** 2)                     # merkeze yakin ogeler daha cok
            rgb = rgb + (P['arka_isik'] * yon * yak)[..., None] * bant * np.array([1.0, 0.85, 0.55], np.float32)
            del yy_, xx_, dx_, dy_, dd, yon, nx_, ny_, nn
    if P['kenar_yum']:
        A = cv2.GaussianBlur(A, (0, 0), P['kenar_yum'])
    sl[:] = sl * (1 - A[..., None]) + rgb * A[..., None]
    if P['isima']:
        x4, y4 = x // 4, y // 4; px_, py_ = x - x4 * 4, y - y4 * 4
        pad = np.pad((rgb * A[..., None]).astype(np.float32), ((py_, (-(A.shape[0] + py_)) % 4), (px_, (-(A.shape[1] + px_)) % 4), (0, 0)))
        sm4 = pad.reshape(pad.shape[0] // 4, 4, pad.shape[1] // 4, 4, 3).mean((1, 3))
        hh_, ww_ = min(sm4.shape[0], ISIK.shape[0] - y4), min(sm4.shape[1], ISIK.shape[1] - x4)
        ISIK[y4:y4 + hh_, x4:x4 + ww_] += sm4[:hh_, :ww_]; del pad, sm4
    cm = cv2.erode((A > 0.99).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    olcum[ad] = srgb(rgb[cm])
log('ogeler')

if P['isima']:                                                       # altin isigi zemine hafif tasar (bloom), tum ogeler ayni
    k = 0.25
    sm = cv2.GaussianBlur(ISIK[:H // 4, :W // 4], (0, 0), P['isima_sigma'] * k)
    for y0_ in range(0, H, 1200):
        y1_ = min(H, y0_ + 1200)
        a0, a1 = max(0, y0_ // 4 - 2), min(sm.shape[0], y1_ // 4 + 2)
        bl = cv2.resize(sm[a0:a1], (W, (a1 - a0) * 4), interpolation=cv2.INTER_LINEAR)
        zemin[y0_:y1_] += bl[y0_ - a0 * 4:y1_ - a0 * 4] * P['isima']
    del sm, ISIK
    log('isima')
# --- 6 sRGB + TPDF titresim -> 8 bit ---
rs = np.random.default_rng(11)
out = np.empty((H, W, 3), np.uint8)
for y0 in range(0, H, 600):
    zb = zemin[y0:y0 + 600]
    if P['renk_ayar'] or P['kararma']:                              # tek ortak renk dokunusu: tum poster ayni
        if P['renk_ayar']:
            lm = np.clip(luma(zb) / 0.6, 0, 1)[..., None]
            sicak = np.array([1.04, 1.0, 0.94], np.float32); soguk = np.array([0.97, 0.99, 1.06], np.float32)
            zb = zb * (1 + P['renk_ayar'] * ((sicak - 1) * lm + (soguk - 1) * (1 - lm)))
        if P['kararma']:
            yy_ = (np.arange(y0, y0 + zb.shape[0], dtype=np.float32)[:, None] - H / 2) / (H / 2)
            xx_ = (np.arange(W, dtype=np.float32)[None] - W / 2) / (W / 2)
            zb = zb * (1 - P['kararma'] * np.clip((xx_ ** 2 + yy_ ** 2) / 2, 0, 1) ** 1.5)[..., None]
    b = srgb(zb) * 255
    b += rs.random(b.shape, np.float32) - rs.random(b.shape, np.float32)
    if P['gren']:                                                   # tum postere ayni ince gren (zemin ve oge ayni malzeme hissi)
        gn = cv2.GaussianBlur(rs.standard_normal(b.shape[:2]).astype(np.float32), (0, 0), 0.8)
        b += (gn / 0.35 * P['gren'])[..., None]
    out[y0:y0 + 600] = np.clip(np.round(b), 0, 255).astype(np.uint8)
del zemin
im = Image.fromarray(out)
im.save(f'{OUT}/SV_BLENDER_tam.png', optimize=False, compress_level=3)
im.save(f'{OUT}/SV_BLENDER_tam_q100.jpg', quality=100, subsampling=0)
im.resize((2000, 3000), Image.LANCZOS).save(f'{OUT}/SV_BLENDER_2000.jpg', quality=95)
log('kaydedildi')

# --- 7 olcum: oge basina Lab ortanca ve yuzdelikler, ogeler arasi dE00 ---
def lab(rgb):
    return cv2.cvtColor(rgb.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
def de00(a, b):
    L1, a1, b1 = a; L2, a2, b2 = b
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p; dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hm = (h1p + h2p) / 2 + (180 if abs(h1p - h2p) > 180 else 0)
    Tt = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.2 * np.cos(np.radians(4 * hm - 63))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2); SC = 1 + 0.045 * Cmp; SH = 1 + 0.015 * Cmp * Tt
    RT = -2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH)))
rap = {}
for ad, v in olcum.items():
    L = lab(v); rap[ad] = {'Lab_medyan': np.median(L, 0).round(2).tolist(), 'L_p5_50_95': np.percentile(L[:, 0], [5, 50, 95]).round(1).tolist(), 'px': int(len(v))}
ana = rap['ana']['Lab_medyan']
for ad in rap: rap[ad]['dE00_ana'] = round(de00(ana, rap[ad]['Lab_medyan']), 2)
rap['_ayar'] = P; rap['_oge_duzeltme_Y_p50_p95'] = duzelt
json.dump(rap, open(f'{OUT}/olcum.json', 'w'), indent=1)
for ad in rap: print(ad, rap[ad])
log('bitti')
