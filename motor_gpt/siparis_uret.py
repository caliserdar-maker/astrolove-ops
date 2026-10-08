# Kisisel siparis posteri, yeni yol (8 Eki 2026): ChatGPT ana sembol KATMANI (onayli, hazir) + motor (isim/tagline ve
# diger ogeler onayli ayarla) + renk_uyum. ChatGPT GEREKMEZ.
# Kullanim: python siparis_uret.py CIFT ISIM1 ISIM2 MESAJ_B64 KATMAN_PNG IS_KLASORU
#   CIFT ters sirada gelirse alfabetige cevrilir ve isimler de yer degistirir (isim1 = cift adindaki ILK burc, solda).
# Cikti: IS_KLASORU/AstroLoveArt_<Burc1>_<Burc2>.jpg (7200x10800 JPEG q100) + _2000 onizleme + siparis.json
import sys, os, re, json, time, base64, subprocess, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
B = os.environ.get('MOTOR_KOK', '/home/claude/blender') + '/'
PY = os.environ.get('MOTOR_PY', B + 'venv/bin/python')
cift, isim1, isim2, mesaj_b64, katman, IS = sys.argv[1:7]
tag_orijinal = base64.b64decode(mesaj_b64).decode('utf-8').strip()
# & -> "and" (Serdar, 8 Eki 2026): her & "and" olur, cevresinde tek bosluk; cift bosluk olusmaz. Sonra 35 karakter sinirina
# yeniden bakilir; asarsa kisaltma YOK, FAIL (cikis 6).
def ve_cevir(t):
    return re.sub(r' {2,}', ' ', re.sub(r'\s*&\s*', ' and ', t)).strip()
tag = ve_cevir(tag_orijinal)
if tag != tag_orijinal: log('tagline: & -> and', f'({len(tag_orijinal)} -> {len(tag)} karakter)')
if len(tag) > 35:
    log(f'FAIL tagline donusumden sonra {len(tag)} karakter > 35; kisaltma yapilmaz')
    os.makedirs(IS, exist_ok=True)
    json.dump(dict(cift=cift, tagline_orijinal=tag_orijinal, tagline=tag, karakter=len(tag), hata='tagline > 35 karakter (& -> and sonrasi)'),
              open(f'{IS}/siparis.json', 'w'), indent=1, ensure_ascii=False)
    sys.exit(6)
b1, b2 = cift.upper().split('_')
if [b1, b2] != sorted([b1, b2]):
    b1, b2 = b2, b1; isim1, isim2 = isim2, isim1; log('cift alfabetige cevrildi, isimler yer degistirdi')
c = f'{b1}_{b2}'
os.makedirs(f'{IS}/{c}', exist_ok=True)
K = json.load(open(B + 'KILIT_GPTGIRDI.json'))
ortam = dict(os.environ, **K['ortam'], AYAR=json.dumps(K['AYAR']))
ortam['PALET_KAYNAK'] = B + 'palet/chatgpt_altin.png'
# 1) sablon alfa (isim, tagline, kucuk semboller, sonsuz; ana yerlesimi)
p = subprocess.run([PY, B + 'olustur_alfa_sablon.py', c, isim1, isim2, tag, f'{IS}/{c}_alfa.npz'], env=ortam, capture_output=True, text=True)
if p.returncode: print(p.stdout[-800:], p.stderr[-1500:]); sys.exit(2)
log('sablon tamam')
# 2) ana: onayli ChatGPT katmani (alfa + yuzey)
z = dict(np.load(f'{IS}/{c}_alfa.npz'))
ad = [str(a) for a in z['_ad']]; kon = z['_konum'].copy()
ka = np.asarray(Image.open(katman).convert('RGBA')); kj = json.load(open(katman + '.json'))
i_ana = ad.index('ana')
if tuple(kon[i_ana]) != (kj['x'], kj['y']) or z['ana'].shape != ka.shape[:2]:
    log('HATA ana konum/boyut uyusmuyor', tuple(kon[i_ana]), z['ana'].shape, (kj['x'], kj['y']), ka.shape[:2]); sys.exit(3)
z['ana'] = ka[..., 3].copy()
np.savez_compressed(f'{IS}/{c}_alfa.npz', **z)
# 3) motor
p = subprocess.run([PY, B + 'uret_tam.py', f'{IS}/{c}'], env=dict(ortam, ALFA=f'{IS}/{c}_alfa.npz'), capture_output=True, text=True)
if p.returncode: print(p.stderr[-1500:]); sys.exit(4)
log('motor tamam')
# 4) ana katmani bindir (gpt_birlestir2 ile ayni)
x0, y0 = kj['x'], kj['y']; H, W = ka.shape[:2]
Pp = np.asarray(Image.open(f'{IS}/{c}/SV_BLENDER_tam.png').convert('RGB')).astype(np.float32)
A = ka[..., 3].astype(np.float32) / 255; Gw = ka[..., :3].astype(np.float32)
reg = Pp[y0:y0 + H, x0:x0 + W]; a3 = A[..., None]
Pp[y0:y0 + H, x0:x0 + W] = Gw * a3 + reg * (1 - a3)
rs = np.random.default_rng(11)
out = np.clip(np.round(Pp + rs.random(Pp.shape, dtype=np.float32) - rs.random(Pp.shape, dtype=np.float32)), 0, 255).astype(np.uint8)
Image.fromarray(out).save(f'{IS}/{c}/{c}_GPT_7200x10800.jpg', quality=100, subsampling=0)
for f_ in ('SV_BLENDER_tam.png', 'SV_BLENDER_tam_q100.jpg', 'SV_BLENDER_2000.jpg'):
    if os.path.exists(f'{IS}/{c}/{f_}'): os.remove(f'{IS}/{c}/{f_}')
log('ana bindirildi')
# 5) renk uyumu (ogeler -> ana altini)
p = subprocess.run([PY, B + 'renk_uyum.py', c, IS, f'{IS}/son'], capture_output=True, text=True)
print(p.stdout[-600:])
if p.returncode: print(p.stderr[-1500:]); sys.exit(5)
ad1, ad2 = b1.capitalize(), b2.capitalize()
son = f'{IS}/AstroLoveArt_{ad1}_{ad2}.jpg'
os.replace(f'{IS}/son/{c}/{c}_7200x10800.jpg', son)
os.replace(f'{IS}/son/{c}/{c}_2000.jpg', f'{IS}/AstroLoveArt_{ad1}_{ad2}_2000.jpg')
json.dump(dict(cift=c, isim1=isim1, isim2=isim2, tagline_orijinal=tag_orijinal, tagline=tag, katman=os.path.basename(katman),
               renk=json.load(open(f'{IS}/son/{c}/renk_olcum.json')), sure_sn=round(time.time() - T0, 1)),
          open(f'{IS}/siparis.json', 'w'), indent=1, ensure_ascii=False)
log('bitti', son)
