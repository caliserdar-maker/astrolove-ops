# DB / PW yeni altin (9 Eki 2026, Serdar; ORNEK, db-pw-altin dali): MB'de onayli yeni altin dokusu (ChatGPT ana sembol katmani + motor +
# renk_uyum) DEEP_BLACK ve PURE_WHITE zeminine. Zemin = eski sistemin plakasi (PLATES/<ED>_<boy>.png, renk_ref b8c8c4b ile ayni), DEGISMEZ;
# yalniz plakadaki ESKI altin cember (78 posterin ortak ogesi, ortancada kaldi) halka bandinda zemin rengine cekilir (yeni cember motordan).
# Ogeler MB ile AYNI hesap (ayni rgb, golge, isima, gren); siparis_uret.py ile ayni adimlar. MB ciktisi referans (tek doku / leke kapisi).
# Kullanim: python db_pw_uret.py CIFT ISIM1 ISIM2 MESAJ_B64 KATMAN_PNG PLAKA_KLASORU IS_KLASORU
# Cikti (renk basina): IS/<RENK>/AstroLoveArt_<B1>_<B2>_<Renk>.jpg (7200x10800 q100 ana kopya) + _24x36.jpg (teslim) + _16x20.jpg (yontem B)
import sys, os, json, time, base64, subprocess, shutil, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
B = os.environ.get('MOTOR_KOK', '/home/claude/blender') + '/'
PY = os.environ.get('MOTOR_PY', B + 'venv/bin/python')
cift, isim1, isim2, mesaj_b64, katman, PL, IS = sys.argv[1:8]
tag = base64.b64decode(mesaj_b64).decode('utf-8').strip()
if len(tag) > 35: log('FAIL tagline > 35 karakter'); sys.exit(6)
RENK = {'DEEP_BLACK': ('BLACK', 0), 'PURE_WHITE': ('PURE_WHITE', 255)}
RENKLER = [r for r in os.environ.get('RENKLER', 'DEEP_BLACK,PURE_WHITE').split(',') if r]
OLCULER = ('24x36', '16x20')
# SIPARIS (9 Eki gece, Serdar: DB/PW yeni yola): SIPARIS_OLCU = musterinin olcusu (13 olcu). Yan zemin = ayni AILE plakasi
# (eski sistemin 5 dijital boyu: 4:5 -> 16x20, 3:4 -> 18x24, 2:3 -> 24x36, 11:14 -> 11x14, A -> A2); 24x36 plakasi motor zemini.
AILE_PLAKA = {'4:5': '16x20', '3:4': '18x24', '2:3': '24x36', '11:14': '11x14', 'A': 'A2'}
SIP_OL = os.environ.get('SIPARIS_OLCU', '')
if SIP_OL:
    sys.path.insert(0, B); import olcu as _olcu
    if SIP_OL not in _olcu.OLCU: log('HATA olcu', SIP_OL); sys.exit(7)
    FAM = AILE_PLAKA[_olcu.AILE[SIP_OL]]; OLCULER = tuple(dict.fromkeys(('24x36', FAM)))
YALNIZ16 = os.environ.get('OLCULER_TESLIM', '24x36,16x20') == '16x20'   # d3 (Serdar 9 Eki aksam): yalniz 16x20 teslim; 24x36 teslim URETILMEZ
b1, b2 = cift.upper().split('_')
if [b1, b2] != sorted([b1, b2]):
    b1, b2 = b2, b1; isim1, isim2 = isim2, isim1; log('cift alfabetige cevrildi, isimler yer degistirdi')
c = f'{b1}_{b2}'
os.makedirs(f'{IS}/{c}', exist_ok=True); os.makedirs(f'{IS}/plaka', exist_ok=True)

# 0) plaka temizligi: eski cember (en buyuk bilesen) cemberle uydurulur; |r - R| < HALKA bandi zemin rengine (yildizlar korunur)
HALKA = 60
plaka_rapor = {}
def plaka_temizle(ad, bg):
    a = np.asarray(Image.open(f'{PL}/{ad}.png').convert('RGB')).copy(); H, W = a.shape[:2]
    d = np.abs(a.astype(np.int16) - bg).max(2)
    n, lab, st, _ = cv2.connectedComponentsWithStats((d > 0).astype(np.uint8), 8)
    i = 1 + int(np.argmax(st[1:, 4])); ys, xs = np.nonzero(lab == i)
    k = np.linalg.lstsq(np.c_[xs, ys, np.ones_like(xs)].astype(np.float64), -(xs.astype(np.float64) ** 2 + ys.astype(np.float64) ** 2), rcond=None)[0]
    cx, cy = -k[0] / 2, -k[1] / 2; R = float(np.sqrt(cx ** 2 + cy ** 2 - k[2]))
    hb = HALKA * W / 7200
    yy, xx = np.mgrid[0:H, 0:W]; ring = np.abs(np.hypot(xx - cx, yy - cy) - R) < hb; del yy, xx
    kalan = int(((d > 0) & ring & (lab != i)).sum())                    # bantta kaybolan cember disi piksel (yildiz) sayisi
    a[ring] = bg
    d2 = np.abs(a.astype(np.int16) - bg).max(2)
    plaka_rapor[ad] = dict(cember=[round(cx, 1), round(cy, 1), round(R, 1)], bant_px=round(hb, 1), silinen_cember_px=int(st[i, 4]),
                           bantta_kaybolan_diger_px=kalan, sonra_halka_ici_max=int(d2[ring].max()), zemin_bg=bg,
                           zemin_disi_oran=round(float((d2 > 0).mean()), 5), zemin_disi_tepe_p99=float(np.percentile(d2[d2 > 0], 99)) if (d2 > 0).any() else 0)
    yol = f'{IS}/plaka/{ad}_temiz.png'; Image.fromarray(a).save(yol, compress_level=3)
    log('plaka', ad, plaka_rapor[ad]); return yol
TEMIZ = {r: {o: plaka_temizle(f'{RENK[r][0]}_{o}', RENK[r][1]) for o in OLCULER} for r in RENKLER}
json.dump(plaka_rapor, open(f'{IS}/plaka/PLAKA.json', 'w'), indent=1)

K = json.load(open(B + 'KILIT_GPTGIRDI.json'))
ortam = dict(os.environ, **K['ortam'], AYAR=json.dumps(K['AYAR']))
ortam['PALET_KAYNAK'] = B + 'palet/chatgpt_altin.png'
# 1) sablon alfa (siparis_uret ile ayni)
p = subprocess.run([PY, B + 'olustur_alfa_sablon.py', c, isim1, isim2, tag, f'{IS}/{c}_alfa.npz'], env=ortam, capture_output=True, text=True)
if p.returncode: print(p.stdout[-800:], p.stderr[-1500:]); sys.exit(2)
log('sablon tamam')
# 2) ana: onayli ChatGPT katmani (siparis_uret ile ayni)
z = dict(np.load(f'{IS}/{c}_alfa.npz'))
ad = [str(a) for a in z['_ad']]; kon = z['_konum'].copy()
ka = np.asarray(Image.open(katman).convert('RGBA')); kj = json.load(open(katman + '.json'))
i_ana = ad.index('ana')
kk_ = (kj.get('kaynak_x', kj['x']), kj.get('kaynak_y', kj['y']), kj.get('kaynak_h', kj['h']), kj.get('kaynak_w', kj['w']))
if (int(kon[i_ana][0]), int(kon[i_ana][1]), *z['ana'].shape) != tuple(int(v) for v in kk_) or ka.shape[:2] != (kj['h'], kj['w']):
    log('HATA ana konum/boyut uyusmuyor'); sys.exit(3)
z['ana'] = ka[..., 3].copy(); kon[i_ana] = (kj['x'], kj['y'])
amp = None
if '&' in tag:
    sys.path.insert(0, B); from amp_tagline import dizgi, amp_yukle
    amp = dizgi(tag, os.environ.get('FONT_KOK', '/home/claude/motor_klon/motor/font/'), *amp_yukle(B))
    i_t = ad.index('tagline'); z['tagline'] = amp['alfa']; kon[i_t] = (amp['x'], amp['y'])
    liste = []
    for i, q in enumerate(amp['ampler'], 1):
        np.save(f'{IS}/amp{i}_alfa.npy', q['alfa']); np.save(f'{IS}/amp{i}_yuzey.npy', q['yuzey'])
        liste.append(dict(x=q['x'], y=q['y'], alfa=f'{IS}/amp{i}_alfa.npy', yuzey=f'{IS}/amp{i}_yuzey.npy'))
    json.dump(liste, open(f'{IS}/amp.json', 'w'), indent=1)
z['_konum'] = kon
np.savez_compressed(f'{IS}/{c}_alfa.npz', **z)
# 3) motor: MB + ek zeminler (ayni ogeler)
ZM = ','.join(f'{r}={TEMIZ[r]["24x36"]}' for r in RENKLER)
p = subprocess.run([PY, B + 'uret_tam.py', f'{IS}/{c}'], env=dict(ortam, ALFA=f'{IS}/{c}_alfa.npz', ZEMINLER=ZM), capture_output=True, text=True)
print(p.stdout[-1500:])
if p.returncode: print(p.stderr[-1500:]); sys.exit(4)
log('motor tamam')
# 4) ana katmani bindir (gpt_birlestir2 / siparis_uret ile ayni) - MB referans + her renk
x0, y0 = kj['x'], kj['y']; H, W = ka.shape[:2]
A = ka[..., 3].astype(np.float32) / 255; Gw = ka[..., :3].astype(np.float32); a3 = A[..., None]
def bindir(png, hedef, mb):
    Pp = np.asarray(Image.open(png).convert('RGB')).astype(np.float32)
    reg = Pp[y0:y0 + H, x0:x0 + W]; Pp[y0:y0 + H, x0:x0 + W] = Gw * a3 + reg * (1 - a3)
    rs = np.random.default_rng(11)
    tp = rs.random(Pp.shape, dtype=np.float32) - rs.random(Pp.shape, dtype=np.float32)
    if not mb:                                                          # DB/PW: titresim (ayni gerceklesme) yalniz ana katmanin degistirdigi yerde
        m = np.zeros(Pp.shape[:2], np.float32); m[y0:y0 + H, x0:x0 + W] = A > 0; tp *= m[..., None]
    out = np.clip(np.round(Pp + tp), 0, 255).astype(np.uint8); del tp
    os.makedirs(os.path.dirname(hedef), exist_ok=True); Image.fromarray(out).save(hedef, quality=100, subsampling=0)
SV = {'MIDNIGHT_BLUE': f'{IS}/{c}/SV_BLENDER_tam.png', **{r: f'{IS}/{c}/SV_{r}_tam.png' for r in RENKLER}}
for r, png in SV.items():
    bindir(png, f'{IS}/{r}/{c}/{c}_GPT_7200x10800.jpg', r == 'MIDNIGHT_BLUE'); shutil.copy(f'{IS}/{c}_alfa.npz', f'{IS}/{r}/{c}_alfa.npz'); os.remove(png)
    log('ana bindirildi', r)
# 5) renk uyumu (ogeler -> ana altini) + teslim (24x36 onayli yol; 16x20 yontem B, yan zemin = ayni rengin 16x20 plakasi, gren hedefi = 24x36 zemin greni)
ad1, ad2 = b1.capitalize(), b2.capitalize()
rapor = dict(cift=c, isim1=isim1, isim2=isim2, tagline=tag, katman=os.path.basename(katman), plaka=plaka_rapor, renk={}, siparis_olcu=SIP_OL or None)
for r in ['MIDNIGHT_BLUE'] + RENKLER:
    TB = f'{IS}/{r}'; ek = {'AMP_JSON': f'{IS}/amp.json'} if amp else {}
    if r != 'MIDNIGHT_BLUE' and SIP_OL:
        ek.update(TESLIM_JPG=f'{TB}/son/{c}_teslim.jpg', CJPEG=B + 'bin/cjpeg-mozjpeg-4.1.1', OLCU=SIP_OL, GREN_HEDEF_KAYNAK='1',
                  TITRESIM_YALNIZ_DEGISEN='1', **{'ZEMIN_TUVAL_' + SIP_OL.upper(): TEMIZ[r][FAM]})
    elif r != 'MIDNIGHT_BLUE':
        ek.update(TESLIM_JPG=f'{TB}/son/{c}_teslim.jpg', CJPEG=B + 'bin/cjpeg-mozjpeg-4.1.1', OLCU='24x36', OLCU_HEPSI=f'{TB}/OLCU',
                  OLCU_HEPSI_LISTE='16x20', ZEMIN_TUVAL_16X20=TEMIZ[r]['16x20'], GREN_HEDEF_KAYNAK='1', TITRESIM_YALNIZ_DEGISEN='1')
        if YALNIZ16: ek['OLCU'] = '16x20'; ek.pop('OLCU_HEPSI'); ek.pop('OLCU_HEPSI_LISTE')     # ayni tek_olcu('16x20') cagrisi
    p = subprocess.run([PY, B + 'renk_uyum.py', c, TB, f'{TB}/son'], capture_output=True, text=True, env=dict(os.environ, **ek))
    print(p.stdout[-900:])
    if p.returncode: print(p.stderr[-1500:]); sys.exit(5)
    ro = json.load(open(f'{TB}/son/{c}/renk_olcum.json'))
    rn = '_'.join(w.capitalize() for w in r.split('_'))
    os.replace(f'{TB}/son/{c}/{c}_7200x10800.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}.jpg')
    os.replace(f'{TB}/son/{c}/{c}_2000.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}_2000.jpg')
    if r != 'MIDNIGHT_BLUE' and SIP_OL:
        os.replace(f'{TB}/son/{c}_teslim.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}_{SIP_OL}.jpg'); ro['olcu_' + SIP_OL] = ro['teslim']
    elif r != 'MIDNIGHT_BLUE':
        if YALNIZ16:
            os.replace(f'{TB}/son/{c}_teslim.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}_16x20.jpg'); ro['olcu_16x20'] = ro['teslim']
        else:
            os.replace(f'{TB}/son/{c}_teslim.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}_24x36.jpg')
            os.replace(f'{TB}/OLCU/{c}_16x20.jpg', f'{TB}/AstroLoveArt_{ad1}_{ad2}_{rn}_16x20.jpg')
            ro['olcu_16x20'] = json.load(open(f'{TB}/OLCU/OLCU_TABLO.json'))['16x20']
    rapor['renk'][r] = ro
    log('renk tamam', r, 'dE00 sonra', ro['sonra'])
rapor['sure_sn'] = round(time.time() - T0, 1)
json.dump(rapor, open(f'{IS}/siparis.json', 'w'), indent=1, ensure_ascii=False)
log('bitti')
