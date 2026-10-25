"""ChatGPT dokusu + ozgun maske kilidi (pilot degerlendirme). Doku: CG ham PNG (1254) -> 2048 Lanczos; alfa = ozgun maske; ozgun icinde CG'nin
kaplamadigi pikseller (<=7 px) komsu dokudan inpaint. Sonuc onayli posterin sembolsuz zeminine ayni yontemle (render.py) yerlestirilir."""
import numpy as np, cv2, glob
from PIL import Image
from seg import yukle
from render import cg_maske, zemin, temiz_yama, U8
P = "/tmp/claude-0/-home-claude/f7c170a6-59b5-5b85-ad08-da97d1f9d029/scratchpad/cg_pilot1/"
R = 1 - np.asarray(Image.open(P + "02_REFERANS/CANCER_TAURUS__OZGUN__2048x2048.png").convert("L")).astype(np.float32) / 255
ESLE = {"PAPER_RELIEF": ("kagit", 41), "EMBROIDERY": ("nakis", 37), "MOSAIC": ("mozaik", 31), "STAINED_GLASS": ("vitray", 31), "WOOD_CARVING": ("ahsap", 41)}
def kilitle(f):
    a = np.asarray(Image.open(f).convert("RGBA").resize((2048, 2048), Image.LANCZOS)).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3] / 255
    eksik = ((R > 0.5) & (al < 0.5)).astype(np.uint8)
    rgb = cv2.inpaint(U8(rgb), cv2.dilate(eksik, np.ones((3, 3), np.uint8)), 5, cv2.INPAINT_TELEA).astype(np.float32) if eksik.any() else rgb
    return rgb, R.copy(), int(eksik.sum())
out = {}
for f in sorted(glob.glob(P + "01_DOKU_DENEMELERI/*.png")):
    st = f.split("__")[1]; ad, dil = ESLE[st]
    rgb, al, ek = kilitle(f)
    A = yukle(ad); H, W = A.shape[:2]
    m = cg_maske(ad, A)
    yasak = np.zeros(m.shape, bool); yasak[60:1000, 180:940] = True
    B, _ = zemin(A, m, dil, temiz_yama(A, yasak), cv2.INPAINT_NS if ad in ("vitray", "ahsap") else cv2.INPAINT_TELEA)
    # yerlesim: render.ozgun_yerlestir ile ayni kutu (CG sembol kutusuna sigdir)
    ys, xs = np.where(al > 0.5); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, al = rgb[y0:y1, x0:x1], al[y0:y1, x0:x1]
    ys, xs = np.where(m); bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    s = min((bx1 - bx0) / al.shape[1], (by1 - by0) / al.shape[0]); w, h = int(al.shape[1] * s), int(al.shape[0] * s)
    cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2; X0, Y0 = cx - w // 2, cy - h // 2
    rr = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA); aa = cv2.resize(al, (w, h), interpolation=cv2.INTER_AREA)[..., None]
    C = B.copy(); C[Y0:Y0 + h, X0:X0 + w] = C[Y0:Y0 + h, X0:X0 + w] * (1 - aa) + rr * aa
    Image.fromarray(U8(C)).save(f"kilit_{ad}.png"); out[ad] = ek; print(st, "dolgu piksel", ek)
