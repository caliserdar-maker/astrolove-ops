# ChatGPT girdisi: temiz ana sembol + kavsaklarda kirmizi tepe hatlari (7 Eki 2026).
# Kullanim: SERIT_KUME=3.5 python kirmizi_hat.py CIFT POSTER_KLASORU CIKTI_KLASORU
# Cikti: <CIFT>_temiz.png, <CIFT>_kirmizi.png (uzun kenar 1536)
import sys, os, numpy as np, cv2
sys.path.insert(0, '/home/claude/blender')
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from serit_vektor import zincirler
import serit
c, D, O = sys.argv[1:4]
os.makedirs(O, exist_ok=True)
PAY = int(os.environ.get('GIRDI_PAY', '150'))
z = np.load(f'{D}/{c}_alfa.npz'); K = dict(zip([str(a) for a in z['_ad']], z['_konum'])); x0, y0 = K['ana']; h, w = z['ana'].shape
A = z['ana'].astype(np.float32) / 255
Z = zincirler(np.pad(A, 32))
G = serit.serit_yukseklik.graf
dug = [(G['dmer'][k], G['ZON'][k]) for k in G['gercek']]
s = 1536 / (max(w, h) + 2 * PAY); W2, H2 = round((w + 2 * PAY) * s), round((h + 2 * PAY) * s)
if os.path.exists(f'{D}/{c}/{c}_7200x10800.jpg'):
    B = Image.open(f'{D}/{c}/{c}_7200x10800.jpg').crop((x0 - PAY, y0 - PAY, x0 + w + PAY, y0 + h + PAY))
    temiz = B.resize((W2, H2), Image.LANCZOS)
else:                                                       # poster silindiyse onceki temiz girdi (ayni kirpim/olcek)
    temiz = Image.open(os.environ.get('TEMIZ_KAYNAK', '/home/claude/blender/gi_all_girdi') + f'/{c}_temiz.png').convert('RGB')
    W2, H2 = temiz.size
temiz.save(f'{O}/{c}_temiz.png')
img = np.asarray(temiz).copy()
for P, Wd, u in Z:
    q = P - 32 + PAY
    yak = np.zeros(len(P), bool)
    for (cy, cx), zon in dug:
        yak |= np.hypot(P[:, 0] - cx, P[:, 1] - cy) < zon + 2.2 * np.median(Wd)
    idx = np.nonzero(yak)[0]
    if len(idx) == 0: continue
    for g in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1):
        pts = (q[g] * s).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, (235, 45, 45), max(3, int(round(4 * W2 / 1536))), cv2.LINE_AA)
Image.fromarray(img).save(f'{O}/{c}_kirmizi.png')
print(c, 'kavsak', len(dug), 'zincir', len(Z), W2, 'x', H2)
