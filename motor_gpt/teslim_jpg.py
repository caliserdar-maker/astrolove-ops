# Etsy teslim dosyasi (8 Eki 2026, Serdar onayli aday B q97, ders 199): 7200x10800, 4:4:4, TPDF titresim (genlik 0.5) YALNIZ koyu zeminde
# (oge alfasi 0), mozjpeg 4.1.1 q97 (-sample 1x1 -optimize -progressive), JFIF 300 dpi. Etsy "Complete order" dosya basi en fazla 20 MB.
# Halka olcusu (ders 190 duzeltilmis, teslim2.py ile ayni): std(G4(cozulmus - ideal kayan nokta)) koyu zemin kutularinda, en kotu kutu.
#   Kalibrasyon (Test 6): q100 0.049, B q97 0.066 (onayli), bilinen bozuk (Pillow q95) 0.098, q90 0.166.
import os, subprocess, numpy as np, cv2
from PIL import Image
KUTU = [(200, 5600, 1400, 6800), (5800, 5600, 7000, 6800), (300, 300, 1500, 1500), (2400, 10000, 4800, 10600)]
def dpi_yaz(yol, dpi=300):
    # JFIF APP0 yogunluk alanlari yerinde yazilir (yeniden sikistirma yok): units=1 (inc), Xdensity, Ydensity
    b = bytearray(open(yol, 'rb').read())
    assert b[0:2] == b'\xff\xd8' and b[2:4] == b'\xff\xe0' and b[6:11] == b'JFIF\x00', 'JFIF APP0 yok'
    b[13] = 1; b[14:16] = dpi.to_bytes(2, 'big'); b[16:18] = dpi.to_bytes(2, 'big')
    open(yol, 'wb').write(bytes(b))
def zemin_maskesi(shape, z, ekler=()):
    bg = np.ones(shape[:2], bool)
    for (x, y), ad in zip(z['_konum'], z['_ad']):
        a = z[str(ad)]; x, y = int(x), int(y); bg[y:y + a.shape[0], x:x + a.shape[1]] &= a == 0
    for (x, y, a) in ekler: bg[y:y + a.shape[0], x:x + a.shape[1]] &= a == 0
    return bg
def halka(dec, ideal, bg):
    v = {}
    for (x0, y0, x1, y1) in KUTU:
        if not bg[y0:y1, x0:x1].all(): continue                       # kutuda oge varsa olculmez
        E = (dec[y0:y1, x0:x1].astype(np.float32) - ideal[y0:y1, x0:x1]).mean(2)
        v[f'{x0},{y0}'] = round(float(cv2.GaussianBlur(E, (0, 0), 4)[40:-40, 40:-40].std()), 4)
    return (max(v.values()) if v else None), v
def yaz(P, z, yol, cjpeg, q=97, ekler=(), seed=11):
    H, W = P.shape[:2]; bg = zemin_maskesi(P.shape, z, ekler)
    U = np.empty(P.shape, np.uint8)
    for y0 in range(0, H, 1200):                                        # bant bant (bellek)
        r = np.random.default_rng([seed, y0]); s = P[y0:y0 + 1200]
        n = (r.random(s.shape, dtype=np.float32) - r.random(s.shape, dtype=np.float32)) * 0.5 * bg[y0:y0 + 1200, :, None]
        U[y0:y0 + 1200] = np.clip(np.round(s + n), 0, 255).astype(np.uint8)
    ppm = yol + '.ppm'; Image.fromarray(U).save(ppm); del U
    subprocess.run([cjpeg, '-quality', str(q), '-sample', '1x1', '-optimize', '-progressive', '-outfile', yol, ppm], check=True)
    os.remove(ppm); dpi_yaz(yol)
    dec = np.asarray(Image.open(yol).convert('RGB'))
    hk, kutular = halka(dec, P, bg)
    return dict(dosya=os.path.basename(yol), bayt=os.path.getsize(yol), mb=round(os.path.getsize(yol) / 1e6, 2), q=q, halka=hk, halka_kutular=kutular)
