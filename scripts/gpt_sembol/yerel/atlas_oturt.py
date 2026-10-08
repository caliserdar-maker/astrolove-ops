# ChatGPT atlas ciktilarini motor atlasina oturt, her glif / sembol icin doku yamasi cikar (8 Eki 2026).
# Kullanim: python atlas_oturt.py GPT_KLASORU   (icinde <pafta>_gpt*.png)
# Cikti: atlas/doku/<anahtar>.npz  (rgb uint8, a uint8 = BIZIM alfa, meta)
import sys, os, json, glob, hashlib, shutil, numpy as np, cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender/'; O = B + 'atlas/'; D = O + 'doku/'; shutil.rmtree(D, ignore_errors=True); os.makedirs(D)
GK = sys.argv[1]
J = json.load(open(O + 'atlas.json'))

def altinlik(rgb):
    f = rgb.astype(np.float32) / 255
    V = f.max(axis=2); sari = f[..., 0] - f[..., 2]
    return (np.clip((V - 0.30) / 0.20, 0, 1) * np.clip((sari + 0.05) / 0.15, 0, 1)).astype(np.float32)

# ana palet (onayli ChatGPT ornegi) a/b ortancasi: tum dokular buna kaydirilir (ana sembolle ayni kural)
Pm = np.asarray(Image.open(B + 'palet/chatgpt_altin.png').convert('RGB')).astype(np.float32)
hk = cv2.cvtColor(Pm / 255, cv2.COLOR_RGB2HSV); mk = ((hk[..., 1] > 0.45) & (hk[..., 2] > 0.42)).astype(np.uint8)
lab = lambda x: cv2.cvtColor((x.reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
Lt = lab(Pm[cv2.erode(mk, np.ones((3, 3), np.uint8)) > 0])

def kanvas_alfa(tur):
    z = np.load(f'{O}{tur}_alfa.npz'); A = np.zeros((10800, 7200), np.float32)
    for (x, y), a in zip(z['_konum'], z['_ad']):
        al = z[str(a)].astype(np.float32) / 255; h, w = al.shape
        A[y:y + h, x:x + w] = np.maximum(A[y:y + h, x:x + w], al)
    return A

alfalar = {}
rapor = {}
for p in J['paftalar']:
    ad, tur = p['ad'], p['tur']; x0, y0, x1, y1 = p['kutu']; s = p['olcek']
    gs = sorted(glob.glob(f'{GK}/{ad}_gpt*.png'), key=os.path.getmtime)
    if not gs: print('YOK', ad); continue
    G0 = np.asarray(Image.open(gs[-1]).convert('RGB')).astype(np.float32)
    Ti = np.asarray(Image.open(f'{O}girdi/{ad}_temiz.png').convert('RGB')).astype(np.float32)
    ag, at = altinlik(G0), altinlik(Ti)
    ys, xs = np.nonzero(ag > 0.5); yt, xt = np.nonzero(at > 0.5)
    sx = (xt.max() - xt.min()) / (xs.max() - xs.min()); sy = (yt.max() - yt.min()) / (ys.max() - ys.min())
    M1 = np.array([[sx, 0, xt.min() - xs.min() * sx], [0, sy, yt.min() - ys.min() * sy], [0, 0, 1]])
    w = cv2.warpAffine(ag, M1[:2].astype(np.float32), (Ti.shape[1], Ti.shape[0]))
    wm = np.eye(2, 3, dtype=np.float32)
    try:
        _, wm = cv2.findTransformECC(cv2.GaussianBlur(at, (0, 0), 2), cv2.GaussianBlur(w, (0, 0), 2), wm, cv2.MOTION_AFFINE,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
    except cv2.error as e: print(ad, 'ECC', e)
    M2 = np.linalg.inv(np.vstack([wm, [0, 0, 1]]).astype(np.float64)) @ M1
    w2 = cv2.warpAffine(ag, M2[:2].astype(np.float32), (Ti.shape[1], Ti.shape[0])) > 0.5
    iou = float((w2 & (at > 0.5)).sum() / max((w2 | (at > 0.5)).sum(), 1))
    M = np.array([[1 / s, 0, 0], [0, 1 / s, 0], [0, 0, 1]]) @ M2           # ChatGPT -> pafta (tam cozunurluk, yerel)
    PW, PH = x1 - x0, y1 - y0
    Gw = cv2.warpAffine(G0, M[:2].astype(np.float32), (PW, PH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    gw = cv2.warpAffine(ag, M[:2].astype(np.float32), (PW, PH), flags=cv2.INTER_LINEAR)
    if tur not in alfalar: alfalar[tur] = kanvas_alfa(tur)
    Ap = alfalar[tur][y0:y1, x0:x1]
    # renk: ana palete a/b kaydirma (pafta ici altin)
    Ls = lab(Gw[(gw > 0.8) & (Ap > 0.5)])
    kay = np.array([0, np.median(Lt[:, 1]) - np.median(Ls[:, 1]), np.median(Lt[:, 2]) - np.median(Ls[:, 2])], np.float32)
    rapor[ad] = dict(iou=round(iou, 3), ab=np.round(kay[1:], 2).tolist(), gpt=os.path.basename(gs[-1]))
    print(ad, rapor[ad])
    # pafta icindeki parcalar
    parcalar = []
    for k, g in J['glif'].items():
        if g['tur'] != tur: continue
        cx0, cy0, cx1, cy1 = g['kutu']
        if cx0 >= x0 and cx1 <= x1 + 1 and cy0 >= y0 - 1 and cy1 <= y1 + 1: parcalar.append((k, (cx0, cy0, cx1, cy1), g))
    for b, g in J['sembol'].items():
        if tur != 'sembol': continue
        bx0, by0, bx1, by1 = g['x'], g['y'], g['x'] + g['w'], g['y'] + g['h']
        if bx0 >= x0 and bx1 <= x1 and by0 >= y0 and by1 <= y1: parcalar.append((f'sembol|{b}', (bx0, by0, bx1, by1), g))
    for k, (cx0, cy0, cx1, cy1), g in parcalar:
        lx0, ly0 = max(cx0 - x0, 0), max(cy0 - y0, 0); lx1, ly1 = min(cx1 - x0, PW), min(cy1 - y0, PH)
        a = Ap[ly0:ly1, lx0:lx1].copy()
        if a.max() < 0.5: continue
        rgb = Gw[ly0:ly1, lx0:lx1].copy(); gm = gw[ly0:ly1, lx0:lx1]
        # yerel ince ayar (oteleme): bizim alfa <-> ChatGPT altin maskesi
        tm = np.eye(2, 3, dtype=np.float32)
        try:
            _, tm = cv2.findTransformECC(cv2.GaussianBlur(a, (0, 0), 2), cv2.GaussianBlur(gm, (0, 0), 2), tm, cv2.MOTION_TRANSLATION,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6), None, 5)
        except cv2.error: pass
        rgb = cv2.warpAffine(rgb, tm, (rgb.shape[1], rgb.shape[0]), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        gm = cv2.warpAffine(gm, tm, (gm.shape[1], gm.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        gecerli = cv2.erode(((gm > 0.8) & (a > 0.3)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        if gecerli.sum() < 20: gecerli = (gm > 0.5) & (a > 0.3)
        icerde = a > 0.01
        _, (iy, ix) = distance_transform_edt(~gecerli, return_indices=True)
        eks = icerde & ~gecerli
        rgb[eks] = rgb[iy[eks], ix[eks]]
        L = lab(rgb[icerde]) + kay
        rgb[icerde] = np.clip(cv2.cvtColor(L.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
        meta = dict(anahtar=k, x0=int(x0 + lx0), y0=int(y0 + ly0))
        if 'kalem_x' in g: meta.update(kalem_x=g['kalem_x'] - (x0 + lx0), taban_y=g['taban_y'] - (y0 + ly0), punto=g['punto'], font=g['font'])
        np.savez_compressed(D + hashlib.md5(k.encode()).hexdigest()[:12] + '.npz', rgb=np.clip(rgb, 0, 255).astype(np.uint8),
                            a=np.round(a * 255).astype(np.uint8), meta=json.dumps(meta, ensure_ascii=False))
json.dump(rapor, open(O + 'oturt_rapor.json', 'w'), indent=1)
# dizin: anahtar -> dosya
idx = {}
for f in glob.glob(D + '*.npz'):
    idx[json.loads(str(np.load(f)['meta']))['anahtar']] = os.path.basename(f)
json.dump(idx, open(D + 'dizin.json', 'w'), ensure_ascii=False, indent=1)
print('doku', len(idx))
