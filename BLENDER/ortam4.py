# Isik ortami (equirect, lineer): sol ust ana yumusak kutu isik, ufuk halkasi (kenar parlak), parlak tepe, kucuk parilti kaynaklari
import bpy, numpy as np, sys
W, H = 2048, 1024
u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H          # satir 0 = alt (Blender piksel sirasi)
U, V = np.meshgrid(u, v)
phi = (0.5 - U) * 2 * np.pi; el = (V - 0.5) * np.pi
d = np.stack([np.cos(phi) * np.cos(el), np.sin(phi) * np.cos(el), np.sin(el)], -1)   # Blender yon: x sag, y yukari(goruntu), z kameraya
def kutu(yon, aci, guc, yumusak):
    yon = np.array(yon, float); yon /= np.linalg.norm(yon)
    c = np.clip(d @ yon, -1, 1); a = np.degrees(np.arccos(c))
    return guc * np.clip((aci - a) / yumusak + 0.5, 0, 1)
z = d[..., 2]
I = np.zeros(d.shape[:2])
I += 0.50 * np.clip(z / 0.3, 0, 1) + 0.25 * np.clip((z - 0.5) / 0.5, 0, 1)   # ust yarim kure: yumusak, tepeye dogru acik
I += 0.9 * np.exp(-((z - 0.35) / 0.28) ** 2)                                  # genis ufuk aydinligi: dik kenarlar parlak (ince halka YOK)
I += kutu([-1, 1, 1.3], 34, 4.0, 30)                                          # ANA ISIK: sol ust, genis yumusak
I += kutu([1, -1, 1.0], 40, 0.8, 35)                                          # sag alt dolgu
rs = np.random.default_rng(5)
for _ in range(7):                                                            # kucuk parilti kaynaklari
    a = rs.uniform(0, 2 * np.pi); e = rs.uniform(np.radians(45), np.radians(75))
    I += kutu([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), np.sin(e)], 3.0, 5.0, 2.5)
I += 0.04
rgb = np.stack([I, I * 0.97, I * 0.92], -1)                          # hafif sicak beyaz
img = bpy.data.images.new('ortam3', W, H, alpha=True, float_buffer=True)
px = np.concatenate([rgb, np.ones((H, W, 1))], -1).astype(np.float32).ravel()
img.pixels.foreach_set(px)
img.filepath_raw = '/home/claude/blender/kure/ortam4.exr'; img.file_format = 'OPEN_EXR'; img.save()
print('ortam yazildi', I.max(), I.mean())
