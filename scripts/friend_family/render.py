"""Sembol denemesi (Serdar 25 Eki onayi): CG poster uzerinde ChatGPT sembolu silinir, OZGUN sembol (ana.png) kodla malzemelenir."""
import numpy as np, cv2
from PIL import Image
from seg import yukle, ham, temizle
rng = np.random.default_rng(3)
U8 = lambda x: np.clip(x, 0, 255).astype(np.uint8)

def cg_maske(ad, A):
    if ad == "ahsap":
        L = A.mean(2); m = ((L - cv2.GaussianBlur(L, (0, 0), 25)) > 10).astype(np.uint8)
        m[:130] = 0; m[900:] = 0; m[:, :200] = 0; m[:, 920:] = 0
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8); k = 1 + np.argmax(st[1:, 4])
        return (lab == k).astype(np.uint8)
    return temizle(ham(ad, A), ad)

def temiz_yama(A, yasak, k=110):
    """Yazi/sus/sembol icermeyen en sakin yama: buyuk gradyan en az olan pencere."""
    g = cv2.Laplacian(cv2.GaussianBlur(A.mean(2), (0, 0), 1), cv2.CV_32F); g = np.abs(g)
    H, W = g.shape; en = None
    for y in range(20, H - k - 20, 20):
        for x in range(20, W - k - 20, 20):
            if yasak[y:y + k, x:x + k].any(): continue
            v = np.percentile(g[y:y + k, x:x + k], 99.5)
            if en is None or v < en[0]: en = (v, y, x)
    _, y, x = en; return (y, y + k, x, x + k)

def zemin(A, m, dil, doku_kutu, yontem=cv2.INPAINT_TELEA):
    big = cv2.dilate(m, np.ones((dil, dil), np.uint8))
    ip = cv2.inpaint(U8(A), big, 9, yontem).astype(np.float32)
    ip = cv2.GaussianBlur(ip, (0, 0), 3 if yontem == cv2.INPAINT_NS else 5)
    y0, y1, x0, x1 = doku_kutu; p = A[y0:y1, x0:x1]; hf = p - cv2.GaussianBlur(p, (0, 0), 4)
    th, tw = hf.shape[:2]; t = np.tile(hf, (A.shape[0] // th + 2, A.shape[1] // tw + 2, 1))[:A.shape[0], :A.shape[1]]
    w = cv2.GaussianBlur(big.astype(np.float32), (0, 0), 2)[..., None]
    return A * (1 - w) + (ip + t) * w, big

def ozgun_yerlestir(m, H, W):
    ana = np.asarray(Image.open("ana.png"))[..., 3].astype(np.float32) / 255
    ys, xs = np.where(ana > 0.5); ana = ana[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    ys, xs = np.where(m); bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    s = min((bx1 - bx0) / ana.shape[1], (by1 - by0) / ana.shape[0])          # CG kutusuna sigdir (en-boy korunur)
    w, h = int(ana.shape[1] * s), int(ana.shape[0] * s)
    cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
    out = np.zeros((H, W), np.float32)
    out[cy - h // 2:cy - h // 2 + h, cx - w // 2:cx - w // 2 + w] = cv2.resize(ana, (w, h), interpolation=cv2.INTER_AREA)
    return out

def palet(A, m, k=400):
    ys, xs = np.where(cv2.erode(m, np.ones((5, 5), np.uint8)) > 0); i = rng.choice(len(ys), min(k, len(ys)), replace=False)
    return A[ys[i], xs[i]]

def golge(B, a, off=(4, 5), blur=4, op=0.35):
    sh = cv2.GaussianBlur(np.roll(np.roll(a, off[1], 0), off[0], 1), (0, 0), blur)[..., None]
    return B * (1 - sh * op)

def isik(a, yuk=6.0, sig=2.0):
    d = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    hgt = cv2.GaussianBlur(np.minimum(d, yuk) / yuk, (0, 0), sig)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
    L = np.array([-0.6, -0.7, 0.6]); n = np.dstack([-gx * 3, -gy * 3, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (n @ L) / np.linalg.norm(L), d

def voronoi(a, aralik):
    H, W = a.shape; seeds = np.full((H, W), 255, np.uint8)
    ys, xs = np.mgrid[aralik // 2:H:aralik, aralik // 2:W:aralik]
    ys = (ys + rng.integers(-aralik // 3, aralik // 3 + 1, ys.shape)).clip(0, H - 1); xs = (xs + rng.integers(-aralik // 3, aralik // 3 + 1, xs.shape)).clip(0, W - 1)
    seeds[ys.ravel(), xs.ravel()] = 0
    _, lab = cv2.distanceTransformWithLabels(seeds, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    sinir = (cv2.dilate(lab.astype(np.float32), np.ones((3, 3))) != cv2.erode(lab.astype(np.float32), np.ones((3, 3)))).astype(np.float32)
    return lab, sinir

def kagit(A, a, pal):
    renk = np.median(pal, 0)
    B = golge(A, a, (3, 4), 3, 0.30)
    l, _ = isik(a, 3, 1.2)
    hf = A - cv2.GaussianBlur(A, (0, 0), 3)
    sym = renk * (0.85 + 0.25 * l[..., None]) + hf * 0.8
    return B * (1 - a[..., None]) + sym * a[..., None]

def nakis(A, a, pal):
    renk = np.median(pal, 0)
    d = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    gx = cv2.Sobel(cv2.GaussianBlur(d, (0, 0), 2), cv2.CV_32F, 1, 0); gy = cv2.Sobel(cv2.GaussianBlur(d, (0, 0), 2), cv2.CV_32F, 0, 1)
    nm = np.sqrt(gx ** 2 + gy ** 2) + 1e-6; nx, ny = gx / nm, gy / nm                # normal: dikis yonu (seridi enine keser)
    H, W = a.shape; X, Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    noise = rng.random((H, W)).astype(np.float32); acc = noise.copy()
    for s in range(1, 9):                                                        # LIC: gurultu normal boyunca yayilir = iplik
        for sg in (1, -1):
            acc += cv2.remap(noise, X + sg * s * nx, Y + sg * s * ny, cv2.INTER_LINEAR)
    acc = acc / 17; acc = (acc - acc.mean()) / (acc.std() + 1e-6)
    wloc = cv2.dilate(d, np.ones((17, 17), np.uint8)) + 1e-3
    yuvarlak = np.sin(np.clip(d / wloc, 0, 1) * np.pi / 2) ** 0.6
    sh = (0.62 + 0.38 * yuvarlak + 0.10 * acc)[..., None]
    B = golge(A, a, (2, 3), 2, 0.30)
    return B * (1 - a[..., None]) + renk * sh * a[..., None]

def mozaik(A, a, pal):
    lab, sinir = voronoi(a, 13)
    renkler = pal[rng.integers(0, len(pal), lab.max() + 1)]
    tas = renkler[lab]
    tas = tas * (1 - 0.35 * cv2.GaussianBlur(sinir, (0, 0), 0.8)[..., None])
    harc = np.array([205, 190, 165], np.float32)
    sym = tas * (1 - sinir[..., None] * 0.9) + harc * sinir[..., None] * 0.9
    return A * (1 - a[..., None]) + sym * a[..., None]

def vitray(A, a, pal):
    lab, sinir = voronoi(a, 48)
    ids = lab.max() + 1; tonu = 0.8 + 0.4 * rng.random(ids); renk = np.median(pal, 0)
    hf = cv2.GaussianBlur(rng.random(a.shape).astype(np.float32), (0, 0), 6); hf = (hf - hf.mean()) / hf.std()
    cam = renk * tonu[lab][..., None] * (1 + 0.08 * hf[..., None])
    ic = (a > 0.5).astype(np.uint8)
    kontur = (cv2.dilate(ic, np.ones((7, 7), np.uint8)) - cv2.erode(ic, np.ones((3, 3), np.uint8))).astype(np.float32)
    kursun = np.clip(kontur + sinir * a, 0, 1)
    kursun = cv2.GaussianBlur(kursun, (0, 0), 0.7)
    gri = np.array([62, 58, 55], np.float32)
    dis = cv2.dilate(a, np.ones((7, 7), np.uint8))
    sym = cam * a[..., None]
    out = A * (1 - a[..., None]) + sym
    return out * (1 - kursun[..., None] * dis[..., None]) + gri * (kursun * dis)[..., None]

def ahsap(A, a, pal):
    renk = np.median(pal, 0) * 1.12
    l, _ = isik(a, 9, 2.5)
    hf = A - cv2.GaussianBlur(A, (0, 0), 6)
    sym = renk * (0.72 + 0.45 * l[..., None]) + hf * 0.9
    B = golge(A, a, (4, 6), 4, 0.45)
    return B * (1 - a[..., None]) + sym * a[..., None]

STIL = {"kagit": (kagit, 41, None), "nakis": (nakis, 37, None), "mozaik": (mozaik, 31, None), "vitray": (vitray, 31, None), "ahsap": (ahsap, 41, None)}
if __name__ == "__main__":
    for ad, (f, dil, kutu) in STIL.items():
        A = yukle(ad); H, W = A.shape[:2]
        m = cg_maske(ad, A); pal = palet(A, m)
        yasak = np.zeros(m.shape, bool); yasak[60:1000, 180:940] = True          # sembol + yazi bandi
        L = A.mean(2); kenar = np.abs(cv2.Laplacian(cv2.GaussianBlur(L, (0, 0), 2), cv2.CV_32F)) > 12
        yasak |= cv2.dilate(kenar.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & False
        kutu = temiz_yama(A, yasak); print(ad, "doku yamasi", kutu)
        B, _ = zemin(A, m, dil, kutu, cv2.INPAINT_NS if ad in ("vitray", "ahsap") else cv2.INPAINT_TELEA)
        a = ozgun_yerlestir(m, H, W)
        C = f(B, a, pal)
        Image.fromarray(U8(C)).save(f"kod_{ad}.png"); print(ad, "tamam")
