"""K-1b-16 bilinen PASS / FAIL: yakin_ana_kutu. Cikis 0 hepsi beklenen; 1 degil."""
import importlib.util, sys
import numpy as np
from PIL import Image
s = importlib.util.spec_from_file_location('yd', sys.argv[1] if len(sys.argv) > 1 else __import__("pathlib").Path(__file__).resolve().parent / "yeni_duzen.py"); yd = importlib.util.module_from_spec(s); s.loader.exec_module(yd)
ok = []
def eski_kutu(a, x, y):
    b = yd.kutu(a); return (x + b[0] + 20, y + b[1] + 150, x + b[0] + 120, y + b[1] + 230)
def dolu(a, x, y, k):
    p = (a > 0.5)[max(0, k[1] - y):max(0, k[3] - y), max(0, k[0] - x):max(0, k[2] - x)]; return float(p.sum())   # dizi disi = bos
# 1 bilinen PASS: CL buyuklugunde halka (425 x 404): eski kutu aynen
a = np.zeros((420, 440), np.float32); yy, xx = np.mgrid[:420, :440]
r = np.hypot((xx - 220) / 212.0, (yy - 210) / 202.0); a[(r > 0.85) & (r < 1.0)] = 1
k, d = yd.yakin_ana_kutu(a, 100, 50); ok.append(('CL boyu eski kutu aynen', k == eski_kutu(a, 100, 50) and d['yol'] == 'eski'))
# 2 bilinen FAIL (eski kural): h 117 sembolde eski kutu sembol disina tasar ve bos
a2 = np.zeros((130, 300), np.float32); a2[5:122, 10:290][::6] = 1
ek = eski_kutu(a2, 0, 0); ok.append(('eski kural h117 bos (bilinen FAIL)', ek[3] > yd.kutu(a2)[3] and dolu(a2, 0, 0, ek) == 0))
# 3 bilinen PASS (yeni kural): ayni sembolde kutu sembol icinde ve dolu
k2, d2 = yd.yakin_ana_kutu(a2, 0, 0); b2 = yd.kutu(a2)
ok.append(('yeni kural h117 icinde ve dolu', b2[0] <= k2[0] and b2[1] <= k2[1] and k2[2] <= b2[2] and k2[3] <= b2[3] and d2['dolu_oran'] > 0 and d2['yol'] == 'en_dolu'))
# 4 bilinen PASS: eski kutu icerde ama bos -> en dolu pencere
a3 = np.zeros((420, 440), np.float32); a3[:, :8] = 1; a3[:, -8:] = 1; a3[:8, :] = 1; a3[-8:, :] = 1
k3, d3 = yd.yakin_ana_kutu(a3, 0, 0); ok.append(('eski kutu bos ise en dolu', d3['yol'] == 'en_dolu' and d3['dolu_oran'] > 0))
for ad, v in ok: print('PASS' if v else 'FAIL', ad)
sys.exit(0 if all(v for _, v in ok) else 1)
