# T5 tam posterden altin maskesi (7200x10800), bolge ayirma, delik istatistigi
import numpy as np, cv2, json, time
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
T = time.time()
im = np.asarray(Image.open('/home/claude/ao/KANIT/SCORPIO_VIRGO_T5_FAIL_tam.png').convert('RGB'))
H, W = im.shape[:2]
M = np.zeros((H, W), np.uint8)
for y in range(0, H, 1200):
    b = im[y:y + 1200].astype(np.float32) / 255
    hsv = cv2.cvtColor(b, cv2.COLOR_RGB2HSV)
    a = np.clip((hsv[..., 1] - 0.25) / 0.2, 0, 1) * np.clip((hsv[..., 2] - 0.22) / 0.2, 0, 1)
    M[y:y + 1200] = (a > 0.5)
print('maske', round(time.time() - T, 1), 'sn', H, W)
k = 5.4  # 1333x2000 goruntu -> 7200x10800
Z = {  # x0,y0,x1,y1 (goruntu koordinati)
    'ana': (330, 515, 1000, 1075), 'kucuk1': (305, 1235, 470, 1380), 'kucuk2': (925, 1235, 1075, 1385),
    'isimler': (185, 1420, 1145, 1525), 'tagline': (230, 1650, 1100, 1755)}
out = {}
for ad, z in Z.items():
    x0, y0, x1, y1 = [int(v * k) for v in z]
    m = M[y0:y1, x0:x1].copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    ana_bilesen = sorted([int(s[4]) for s in st[1:]], reverse=True)[:12]
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(1 - m, connectivity=4)
    delik = sorted([int(s[4]) for i, s in enumerate(sh[1:], 1)
                    if s[0] > 0 and s[1] > 0 and s[0] + s[2] < m.shape[1] and s[1] + s[3] < m.shape[0]], reverse=True)
    out[ad] = dict(kutu=[x0, y0, x1, y1], bilesen=ana_bilesen, delik_ilk=delik[:25], delik_n=len(delik))
    print(ad, out[ad])
# cember: halka bolgesi = genel kutu eksi diger bolgeler
x0, y0, x1, y1 = [int(v * k) for v in (130, 275, 1205, 1190)]
m = M[y0:y1, x0:x1].copy()
ax0, ay0, ax1, ay1 = out['ana']['kutu']; m[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = 0
n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
out['cember'] = dict(kutu=[x0, y0, x1, y1], bilesen=sorted([int(s[4]) for s in st[1:]], reverse=True)[:12])
print('cember', out['cember'])
np.save('/home/claude/blender/M_tam.npy', M)
json.dump(out, open('/home/claude/blender/bolgeler.json', 'w'))
print('bitti', round(time.time() - T, 1))
