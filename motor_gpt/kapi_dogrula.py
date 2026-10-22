# Her kapi icin 1 bilinen PASS + 1 bilinen FAIL (ders 80). PASS: /tmp/is1 (standart isimler, yeni yol).
import os, sys, json, shutil, subprocess, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender'; IS = '/tmp/is1'; c = 'AQUARIUS_ARIES'; SON = f'{IS}/AstroLoveArt_Aquarius_Aries.jpg'
REF = f'{B}/renkli78/{c}/{c}_7200x10800.jpg'; ENV = dict(os.environ, REF_ALFA=f'{B}/gb_all/{c}_alfa.npz')
def kos(d):
    p = subprocess.run([f'{B}/venv/bin/python', f'{B}/siparis_kapi.py', d, REF], capture_output=True, text=True, env=ENV)
    return json.loads(p.stdout.strip().splitlines()[-1])
def kopya(ad):
    d = f'/tmp/kapi_{ad}'; shutil.rmtree(d, ignore_errors=True); shutil.copytree(IS, d, ignore=shutil.ignore_patterns(c, 'son')); return d
z = np.load(f'{IS}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
x0, y0 = K['ana']; h, w = z['ana'].shape
sonuc = {'PASS_ornegi': {k: v['PASS'] for k, v in kos(IS).items() if isinstance(v, dict)}}
# a) ana bolgesinde sembol pikselleri +6 (gorunmez kucuk degisiklik bile yakalanmali)
d = kopya('a'); P = np.asarray(Image.open(SON)).astype(np.int16); m = z['ana'] > 128
P[y0:y0 + h, x0:x0 + w][m] += 6; Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).save(f'{d}/AstroLoveArt_Aquarius_Aries.jpg', quality=100, subsampling=0)
sonuc['a_FAIL'] = kos(d)['a']
# b) renk uyumu uygulanmamis ara dosya
d = kopya('b'); shutil.copy(f'{IS}/{c}/{c}_GPT_7200x10800.jpg', f'{d}/AstroLoveArt_Aquarius_Aries.jpg'); sonuc['b_FAIL'] = kos(d)['b']
# c) kucuk semboller yer degistirmis (isim-burc eslesmesi bozuk)
d = kopya('c'); zz = dict(np.load(f'{d}/{c}_alfa.npz')); ad = [str(a) for a in zz['_ad']]; kon = zz['_konum'].copy()
i1, i2 = ad.index('kucuk1'), ad.index('kucuk2'); zz['kucuk1'], zz['kucuk2'] = zz['kucuk2'], zz['kucuk1']; zz['_konum'] = kon
np.savez_compressed(f'{d}/{c}_alfa.npz', **zz); sonuc['c_FAIL'] = kos(d)['c']
# d) tagline yazimi girdiden farkli (tek harf)
d = kopya('d'); s = json.load(open(f'{d}/siparis.json')); s['tagline'] = s['tagline'][:-1] + 'x'; json.dump(s, open(f'{d}/siparis.json', 'w'))
sonuc['d_FAIL'] = kos(d)['d']
# e) ana kutusuna sert kenarli +8 (dikis)
d = kopya('e'); P = np.asarray(Image.open(SON)).astype(np.int16); P[y0:y0 + h, x0:x0 + w] += 8
Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).save(f'{d}/AstroLoveArt_Aquarius_Aries.jpg', quality=100, subsampling=0)
sonuc['e_FAIL'] = kos(d)['e']
ozet = {k: (v['PASS'] if 'PASS' in v else v) for k, v in sonuc.items() if k != 'PASS_ornegi'}
print(json.dumps(dict(PASS_ornegi=sonuc['PASS_ornegi'], FAIL_ornekleri=ozet)))
json.dump(sonuc, open(f'{B}/kapi_dogrula.json', 'w'), indent=1, ensure_ascii=False)
