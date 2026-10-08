# zemin-4: YENI zeminli motor ciktisina siparis_uret.py adim 4 (ana katman bindirme) + adim 5 (renk_uyum) AYNEN uygulanir.
# Referans is klasorundeki alfa/& dosyalari kullanilir (ogeler, yerlesim, & ayni).
# Kullanim: python bindir_renk.py REF_IS_KLASORU YENI_SV_PNG KATMAN_PNG YENI_IS_KLASORU
import sys, os, json, shutil, subprocess, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
IS, SV, katman, IY = sys.argv[1:5]
B = os.environ.get('MOTOR_KOK', '/home/claude/blender') + '/'
PY = os.environ.get('MOTOR_PY', B + 'venv/bin/python')
s = json.load(open(f'{IS}/siparis.json')); c = s['cift']
os.makedirs(f'{IY}/{c}', exist_ok=True)
shutil.copy(f'{IS}/{c}_alfa.npz', f'{IY}/{c}_alfa.npz')
ka = np.asarray(Image.open(katman).convert('RGBA')); kj = json.load(open(katman + '.json'))
# --- siparis_uret.py adim 4 ile ayni ---
x0, y0 = kj['x'], kj['y']; H, W = ka.shape[:2]
Pp = np.asarray(Image.open(SV).convert('RGB')).astype(np.float32)
A = ka[..., 3].astype(np.float32) / 255; Gw = ka[..., :3].astype(np.float32)
reg = Pp[y0:y0 + H, x0:x0 + W]; a3 = A[..., None]
Pp[y0:y0 + H, x0:x0 + W] = Gw * a3 + reg * (1 - a3)
rs = np.random.default_rng(11)
out = np.clip(np.round(Pp + rs.random(Pp.shape, dtype=np.float32) - rs.random(Pp.shape, dtype=np.float32)), 0, 255).astype(np.uint8)
Image.fromarray(out).save(f'{IY}/{c}/{c}_GPT_7200x10800.jpg', quality=100, subsampling=0)
del Pp, out
# --- adim 5 ---
amp = os.path.exists(f'{IS}/amp.json')
p = subprocess.run([PY, B + 'renk_uyum.py', c, IY, f'{IY}/son'], capture_output=True, text=True,
                   env=dict(os.environ, **({'AMP_JSON': f'{IS}/amp.json'} if amp else {})))
print(p.stdout[-600:])
if p.returncode: print(p.stderr[-1500:]); sys.exit(5)
b1, b2 = c.split('_'); ad1, ad2 = b1.capitalize(), b2.capitalize()
os.replace(f'{IY}/son/{c}/{c}_7200x10800.jpg', f'{IY}/AstroLoveArt_{ad1}_{ad2}.jpg')
os.replace(f'{IY}/son/{c}/{c}_2000.jpg', f'{IY}/AstroLoveArt_{ad1}_{ad2}_2000.jpg')
s['renk'] = json.load(open(f'{IY}/son/{c}/renk_olcum.json')); s['zemin4'] = True
json.dump(s, open(f'{IY}/siparis.json', 'w'), indent=1, ensure_ascii=False)
print('bindir_renk tamam', s['renk']['PASS'])
