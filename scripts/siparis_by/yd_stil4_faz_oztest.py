"""F raporu: Timeless kayma olcumu oz-testi. by_stil4.faz (numpy) ve cv2.phaseCorrelate; ozdes girdi ve bilinen yapay kaymalar
(Fourier tam alt piksel kaydirma + bilinear warpAffine). Girdi: kosu 41305506283 Timeless_12x18.jpg, 1/1,5 kucultulmus koyuluk (medianBlur 101; kapinin koyuluk() islevi DEGIL). cv2 cagrisi pencere(Hann)siz; F 3. kosuda kapi icinde ayni kirpim + koyuluk ile faz_oztest() var."""
import sys, json
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import by_stil4 as BS
im = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32)
im = cv2.resize(im, (2400, 3600), interpolation=cv2.INTER_AREA)
L = im @ np.float32([0.299, 0.587, 0.114])
D = 1 - L / np.maximum(cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 101).astype(np.float32), 1)
def fshift(a, dx, dy):
    h, w = a.shape; fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2j * np.pi * (fx * dx + fy * dy))))
def wshift(a, dx, dy):
    return cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
out = []
for ad, (y0, x0, h, w) in {"702x650": (2500, 300, 650, 702), "1968x1842": (900, 216, 1842, 1968)}.items():
    a = D[y0:y0 + h, x0:x0 + w].astype(np.float64)
    for yon in ("x", "y"):
        for k in (0.0, 0.1, 0.25, 0.4, 0.45, 0.5, 0.55, 0.6, 0.75, 1.0, 2.0):
            dx, dy = (k, 0.0) if yon == "x" else (0.0, k)
            for yontem, f in (("fourier", fshift), ("bilinear", wshift)):
                b = f(a.astype(np.float32 if yontem == "bilinear" else np.float64), dx, dy).astype(np.float64)
                nx, ny, _ = BS.faz(a, b)
                (cx, cy), _ = cv2.phaseCorrelate(a, b)
                hn = (nx - dx, ny - dy); hc = (cx - dx, cy - dy)
                out.append(dict(kirpim=ad, yon=yon, bilinen=k, yontem=yontem, numpy=[round(nx, 3), round(ny, 3)],
                                numpy_hata=round(max(map(abs, hn)), 3), cv2=[round(cx, 3), round(cy, 3)], cv2_hata=round(max(map(abs, hc)), 3)))
for r in out:
    if r["yon"] == "x" or r["bilinen"] == 0:
        pass
    print(r)
mx = lambda key, f: max(r[key] for r in out if f(r))
print("OZET numpy en buyuk hata:", mx("numpy_hata", lambda r: True), "| ozdes (0) numpy:", mx("numpy_hata", lambda r: r["bilinen"] == 0),
      "cv2 ozdes:", mx("cv2_hata", lambda r: r["bilinen"] == 0), "| cv2 en buyuk:", mx("cv2_hata", lambda r: True))
json.dump(out, open(sys.argv[2], "w"), indent=1)
