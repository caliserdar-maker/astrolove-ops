import numpy as np, cv2
from PIL import Image
from kart_duzelt import zemin_doldur, acik
A = np.asarray(Image.open("/mnt/user-data/attachments/f7c170a6-59b5-5b85-ad08-da97d1f9d029/efcd1c00-image.png").convert("RGB")).astype(np.float32)
H, W = A.shape[:2]
koru = np.zeros((H, W), bool)                                    # korunan: poster, baslik, kalan yazilar, oklar
koru[190:998, 102:716] = True
bk = np.zeros((H, W), np.uint8); bk[68:152, 255:1216] = acik(A)[68:152, 255:1216]
koru |= cv2.dilate(bk, np.ones((11, 11), np.uint8)).astype(bool)      # baslik: yalniz harfler (+golge payi)
koru[305:367, 870:1312] = True; koru[400:455, 805:1340] = True
koru[650:714, 788:1385] = True; koru[742:800, 865:1318] = True
kose = np.zeros((H, W), bool)
kose[0:345, 0:275] = True; kose[0:300, 1140:W] = True; kose[740:H, 1325:W] = True; kose[805:H, 1240:W] = True; kose[930:H, 1140:W] = True
sil = np.zeros((H, W), bool); sil[460:516, 805:1425] = True; sil[803:863, 864:1232] = True
tas_y0, tas_y1, tas_x0, tas_x1, dy = 868, 924, 864, 1094, -64
parca = A[tas_y0:tas_y1, tas_x0:tas_x1].copy(); parca_m = acik(parca)
sil[tas_y0:tas_y1, tas_x0:tas_x1] = True
B = zemin_doldur(A, (kose | sil) & ~koru, (760, 540, 1140, 640))
B = np.where(koru[..., None], A, B)
mk = cv2.GaussianBlur(cv2.dilate(parca_m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)[..., None]
hy0 = tas_y0 + dy
B[hy0:hy0 + parca.shape[0], tas_x0:tas_x1] = B[hy0:hy0 + parca.shape[0], tas_x0:tas_x1] * (1 - mk) + parca * mk
Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).save("10_kisisel_ornek.png")
print("tamam")
