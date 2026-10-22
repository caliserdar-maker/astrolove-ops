# Yabanci yay / ikinci cember taramasi (Serdar 10 Eki, WP 19 AQUARIUS_AQUARIUS ikinci cember).
# Kullanim: python yay_tara.py PLATE.png GORSEL.jpg [GORSEL2.jpg ...] --json CIKTI.json [--kesit KLASOR]
# Yontem: plakadaki asil cember (merkez, yaricap) olculur. Gorselde ince koyu cizgiler (yuksek gecis) bulunur, asil cember
# bandi cikarilir; kalan her bilesene cember uydurulur. Yaricapi asil cembere yakin (+-%15), uyum artigi kucuk ve yay acisi
# >= 15 derece olan, merkezi asil cemberden ayri (> %3 R) bilesen = YABANCI YAY -> FAIL.
import sys, json, os, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

HP_SIGMA = 6.0      # yuksek gecis (px, 3307 genislik olceginde; genislikle olceklenir)
HP_ESIK = 7.0       # L* birimi: ince koyu cizgi esigi
BANT = 0.012        # asil cember bandi (R'nin orani) cikarilir
R_TOL = 0.15        # yabanci yay yaricapi asil R'ye gore
ARTIK = 0.006       # cember uyum artigi (R orani, std)
ACI_MIN = 15.0      # derece
MERKEZ_MIN = 0.03   # merkez ayrimi (R orani)
MIN_PX = 400        # bilesen en az (3307 olcegi; alanla olceklenir)
# Serdar 10 Eki goz onayi (ders 305): bilinen yanlis alarm, deger bugunkuyle ayni kaldigi surece istisna (cift, boy) ->
# (aci derece, merkez farki px, bilesen px). Tolerans: aci +-1, merkez +-5 px, px +-%2 (3307 olceginde).
ISTISNA = {('SAGITTARIUS_VIRGO', '11x14'): (24.1, 1296.7, 2522)}


def istisna_mi(cift, boy, y, s=1.0):
    """s = goruntu genisligi / 3307 (istisna degerleri 3307 olceginde; 19 karti kesiti ~0.417). s=1'de eski davranis."""
    t = ISTISNA.get((cift, boy))
    return bool(t and abs(y['aci'] - t[0]) <= 1.0 and abs(y['merkez_fark'] / s - t[1]) <= 5.0
                and abs(y['px'] / (s * s) - t[2]) <= 0.02 * t[2])


def L_kanal(rgb):
    return cv2.cvtColor((rgb.astype(np.float32) / 255), cv2.COLOR_RGB2Lab)[..., 0]


def ince_cizgi(rgb, s):
    L = L_kanal(rgb)
    hp = cv2.GaussianBlur(L, (0, 0), HP_SIGMA * s) - L
    return hp > HP_ESIK


def cember_uydur(ys, xs):
    A = np.c_[xs, ys, np.ones_like(xs)].astype(np.float64)
    k = np.linalg.lstsq(A, -(xs.astype(np.float64) ** 2 + ys.astype(np.float64) ** 2), rcond=None)[0]
    cx, cy = -k[0] / 2, -k[1] / 2
    R = float(np.sqrt(max(cx * cx + cy * cy - k[2], 1e-9)))
    r = np.hypot(xs - cx, ys - cy)
    return cx, cy, R, float(np.std(r - R))


def asil_cember(plate):
    h, w = plate.shape[:2]; s = w / 3307
    m = ince_cizgi(plate, s)
    sm = cv2.resize(m.astype(np.uint8) * 255, (800, int(800 * h / w)), interpolation=cv2.INTER_AREA)
    c = cv2.HoughCircles(cv2.GaussianBlur(sm, (5, 5), 1.5), cv2.HOUGH_GRADIENT, dp=1, minDist=200, param1=60, param2=25,
                         minRadius=int(800 * 0.30), maxRadius=int(800 * 0.42))
    if c is None:
        raise SystemExit('plakada cember bulunamadi')
    f = w / 800; cx, cy, R = (float(v) * f for v in c[0][0])
    yy, xx = np.nonzero(m)
    for bant in (0.03, 0.012):                                  # iki tur daraltarak incelt
        sec = np.abs(np.hypot(xx - cx, yy - cy) - R) < bant * R
        cx, cy, R, art = cember_uydur(yy[sec], xx[sec])
    return dict(cx=round(cx, 1), cy=round(cy, 1), R=round(R, 1), artik=round(art, 2))


def tara(rgb, ac, kesit=None, ad='', cift=None, boy=None):
    h, w = rgb.shape[:2]; s = w / 3307
    cx0, cy0, R0 = ac['cx'] * s, ac['cy'] * s, ac['R'] * s
    m = ince_cizgi(rgb, s)
    yy, xx = np.mgrid[0:h, 0:w]
    m &= ~(np.abs(np.hypot(xx - cx0, yy - cy0) - R0) < BANT * R0)
    del yy, xx
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    yab = []
    for i in range(1, n):
        if st[i, 4] < MIN_PX * s * s:
            continue
        ys, xs = np.nonzero(lab[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]] == i)
        ys = ys + st[i, 1]; xs = xs + st[i, 0]
        cx, cy, R, art = cember_uydur(ys, xs)
        if not (abs(R - R0) <= R_TOL * R0 and art <= ARTIK * R0):
            continue
        a = np.degrees(np.arctan2(ys - cy, xs - cx)); a = np.sort(a)
        bos = np.max(np.diff(np.r_[a, a[0] + 360]))                   # en buyuk bosluk -> yay acisi = 360 - bosluk
        aci = 360 - bos
        dm = float(np.hypot(cx - cx0, cy - cy0))
        if aci >= ACI_MIN and dm > MERKEZ_MIN * R0:
            yab.append(dict(kutu=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])], px=int(st[i, 4]),
                            merkez=[round(cx, 1), round(cy, 1)], R=round(R, 1), artik=round(art, 2), aci=round(aci, 1),
                            merkez_fark=round(dm, 1)))
    ist = [y for y in yab if istisna_mi(cift, boy, y, s)]
    yab = [y for y in yab if not istisna_mi(cift, boy, y, s)]
    r = dict(boyut=[w, h], olcek=round(s, 4), asil=dict(cx=round(cx0, 1), cy=round(cy0, 1), R=round(R0, 1)), yabanci=yab, istisna=ist,
             esik=dict(R_tol=R_TOL, artik=ARTIK, aci_min=ACI_MIN, merkez_min=MERKEZ_MIN), PASS=not yab)
    if kesit and yab:
        os.makedirs(kesit, exist_ok=True)
        for j, y in enumerate(yab):
            x0, y0, x1, y1 = y['kutu']; p = int(60 * s)
            Image.fromarray(rgb[max(0, y0 - p):y1 + p, max(0, x0 - p):x1 + p]).save(f'{kesit}/{ad}_yay{j}.jpg', quality=92)
    return r


if __name__ == '__main__':
    a = sys.argv[1:]
    js = a[a.index('--json') + 1] if '--json' in a else None
    ks = a[a.index('--kesit') + 1] if '--kesit' in a else None
    ct = a[a.index('--cift') + 1] if '--cift' in a else None          # istisna icin (tek gorsel)
    by = a[a.index('--boy') + 1] if '--boy' in a else None
    yol = [x for x in a if not x.startswith('--') and x not in (js, ks, ct, by)]
    plate = np.asarray(Image.open(yol[0]).convert('RGB'))
    ac = asil_cember(plate); print('asil cember', ac, flush=True)
    out = dict(plate=os.path.basename(yol[0]), asil=ac, sonuc={})
    for g in yol[1:]:
        rgb = np.asarray(Image.open(g).convert('RGB'))
        ad = os.path.splitext(os.path.basename(os.path.dirname(g)) + '__' + os.path.basename(g))[0]
        r = tara(rgb, ac, ks, ad, ct, by); out['sonuc'][g] = r
        print(('PASS' if r['PASS'] else 'FAIL'), g, len(r['yabanci']), [(y['aci'], y['merkez_fark'], y['px']) for y in r['yabanci']], flush=True)
    out['PASS'] = all(v['PASS'] for v in out['sonuc'].values())
    if js:
        json.dump(out, open(js, 'w'), indent=1)
    sys.exit(0 if out['PASS'] else 1)
