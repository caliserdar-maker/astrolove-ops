# Kapi a yerel kontrol dogrulamasi (ders 80): bilinen PASS (GEMINI_VIRGO standart) + bilinen FAIL (1 kalinlik capinda leke)
import os, json, shutil, subprocess, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender'; IS = '/tmp/isgv'; c = 'GEMINI_VIRGO'; SON = f'{IS}/AstroLoveArt_Gemini_Virgo.jpg'
REF = f'{B}/renkli78/{c}/{c}_7200x10800.jpg'; ENV = dict(os.environ, REF_ALFA=f'{B}/gb_api/{c}_alfa.npz')
def kos(d):
    p = subprocess.run([f'{B}/venv/bin/python', f'{B}/siparis_kapi.py', d, REF], capture_output=True, text=True, env=ENV)
    return json.loads(p.stdout.strip().splitlines()[-1])['a']
pas = kos(IS)
z = np.load(f'{IS}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
x0, y0 = K['ana']; am = z['ana'] > 127
kal = float(np.median(cv2.distanceTransform(am.astype(np.uint8), cv2.DIST_L2, 5)[am])) * 2
dt = cv2.distanceTransform(am.astype(np.uint8), cv2.DIST_L2, 5); yy, xx = np.unravel_index(np.argmax(dt), dt.shape)   # en kalin yer
d = '/tmp/kapi_leke'; shutil.rmtree(d, ignore_errors=True); shutil.copytree(IS, d, ignore=shutil.ignore_patterns(c, 'son'))
P = np.asarray(Image.open(SON)).astype(np.int16)
m = np.zeros(P.shape[:2], np.uint8); cv2.circle(m, (x0 + int(xx), y0 + int(yy)), int(round(kal / 2)), 1, -1)
P[m > 0] -= 30                                                   # 1 kalinlik capinda koyu leke
Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).save(f'{d}/AstroLoveArt_Gemini_Virgo.jpg', quality=100, subsampling=0)
fail = kos(d)
out = dict(kalinlik=round(kal, 1), leke_alan_px=int(m.sum()), PASS_ornegi=pas, FAIL_ornegi=fail,
           dogru=bool(pas['PASS'] and not fail['PASS']))
print(json.dumps(out)); json.dump(out, open(f'{B}/kapi_yerel_dogrula.json', 'w'), indent=1)
