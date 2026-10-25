"""Yesil kartlar: zemin kose susleri silinir, fazla satirlar silinir/kaydirilir (Serdar 25 Eki). Yeni yazi cizilmez."""
import numpy as np, cv2
from PIL import Image
from kart_duzelt import zemin_doldur, acik
D = "/mnt/user-data/attachments/f7c170a6-59b5-5b85-ad08-da97d1f9d029/"
# kutu: (y0, y1, x0, x1)
KART = {
 "02_birlesme": dict(dosya="d18b1f60-image.png",
    koru_tam=[(228, 928, 735, 1298), (300, 900, 200, 735)],                 # poster + burc isaretleri/oklar
    koru_harf=[(48, 212, 215, 1235), (1012, 1045, 545, 900)],               # baslik + kucuk not
    kose=[(0, 330, 0, 215), (0, 330, 1235, 9999), (760, 9999, 0, 250), (760, 9999, 1300, 9999), (930, 9999, 1150, 9999), (0, 46, 0, 9999)],
    sil=[(936, 1000, 255, 1185)], tas=[((1010, 1047, 545, 902), -62)], doku=(470, 260, 700, 330)),
 "04_format": dict(dosya="44ad78fd-image.png",
    koru_tam=[(244, 820, 168, 645), (244, 818, 814, 1285), (175, 1005, 715, 735)],
    koru_harf=[(66, 145, 190, 1262), (178, 232, 200, 620), (178, 232, 948, 1152), (845, 888, 215, 597),
               (838, 877, 905, 1195), (1030, 1070, 500, 945)],
    kose=[(0, 340, 0, 168), (0, 62, 0, 330), (0, 160, 0, 195), (0, 340, 1290, 9999), (0, 62, 1120, 9999), (0, 160, 1268, 9999), (730, 9999, 0, 165), (980, 9999, 0, 320), (775, 9999, 1290, 9999), (1000, 9999, 1200, 9999)],
    sil=[(892, 937, 200, 620), (878, 960, 815, 1290)], tas=[((940, 985, 200, 612), -48), ((959, 1000, 815, 1290), -81)], doku=(30, 400, 150, 700)),
 "11_teslimat": dict(dosya="b7bac12e-image.png",
    koru_tam=[(330, 525, 255, 455), (585, 600, 140, 1310), (665, 860, 255, 455)],
    koru_harf=[(140, 225, 160, 1290), (335, 467, 520, 1240), (655, 710, 520, 1268), (730, 912, 520, 1090)],
    kose=[(0, 400, 0, 250), (0, 140, 0, 9999), (0, 420, 1300, 9999), (660, 9999, 0, 250), (940, 9999, 0, 320), (712, 9999, 1230, 9999), (860, 9999, 1100, 9999)],
    sil=[(488, 548, 522, 1148), (990, 1042, 535, 925)], tas=[], doku=(600, 230, 1100, 300)),
}
def isle(ad, c):
    A = np.asarray(Image.open(D + c["dosya"]).convert("RGB")).astype(np.float32); H, W = A.shape[:2]
    a = acik(A).astype(np.uint8)
    koru = np.zeros((H, W), bool)
    for y0, y1, x0, x1 in c["koru_tam"]: koru[y0:y1, x0:x1] = True
    for y0, y1, x0, x1 in c["koru_harf"]:
        b = np.zeros((H, W), np.uint8); b[y0:y1, x0:x1] = a[y0:y1, x0:x1]
        koru |= cv2.dilate(b, np.ones((11, 11), np.uint8)).astype(bool)
    dol = np.zeros((H, W), bool)
    for y0, y1, x0, x1 in c["kose"]: dol[y0:y1, x0:x1] = True
    for y0, y1, x0, x1 in c["sil"]: dol[y0:y1, x0:x1] = True
    parcalar = []
    for (y0, y1, x0, x1), dy in c["tas"]:
        p = A[y0:y1, x0:x1].copy(); parcalar.append((p, acik(p), y0 + dy, x0)); dol[y0:y1, x0:x1] = True
        koru[y0:y1, x0:x1] = False
    x0, y0, x1, y1 = c["doku"]
    B = zemin_doldur(A, dol & ~koru, (x0, y0, x1, y1))
    B = np.where((koru & ~dol)[..., None] | (koru & ~dol)[..., None], A, B)
    for p, pm, yy, xx in parcalar:
        mk = cv2.GaussianBlur(cv2.dilate(pm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)[..., None]
        B[yy:yy + p.shape[0], xx:xx + p.shape[1]] = B[yy:yy + p.shape[0], xx:xx + p.shape[1]] * (1 - mk) + p * mk
    Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).save(f"{ad}_ornek.png"); print(ad, "tamam")
for ad, c in KART.items(): isle(ad, c)
