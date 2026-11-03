# Ornament FILDISI KREM (karar 24): zemin #F4EEDF + eliptik ust isik + ince doku + SADE altin katmani
import sys, hashlib
import numpy as np
from PIL import Image, ImageDraw
altin, cikti = sys.argv[1], sys.argv[2]
N = 954
rng = np.random.default_rng(7)
ga = np.array(Image.open(altin).convert("RGBA")).astype(float)
assert ga.shape == (N, N, 4), ga.shape
yy, xx = np.mgrid[0:N, 0:N]; c = (N - 1) / 2
d = np.sqrt(((xx - c) / (N * 0.62)) ** 2 + ((yy - (c - 90)) / (N * 0.70)) ** 2)
isik = 1.03 - 0.075 * np.clip(d, 0, 1.4) ** 1.6
rgb = np.array([0xF4, 0xEE, 0xDF], float)
z = np.clip(rgb[None, None, :] * isik[..., None] + rng.normal(0, 1.5, (N, N, 1)), 0, 255)
a = ga[..., 3:4] / 255
t = z * (1 - a) + ga[..., :3] * a
mask = Image.new("L", (N, N), 0); ImageDraw.Draw(mask).ellipse((0, 0, N - 1, N - 1), fill=255)
w = Image.new("RGB", (N, N), "white"); w.paste(Image.fromarray(t.round().astype(np.uint8)), (0, 0), mask)
w.save(cikti)
print("sha256", hashlib.sha256(open(cikti, "rb").read()).hexdigest())
