#!/usr/bin/env python3
"""poster_burc.py (8 Kas, Serdar "Poster 7200x10800'den"): ayni burc posterlerinden (X_X_7200x10800.jpg, POSTER78_CHATGPT_20261008)
kucuk burc sembolunu yeni dokusuyla KODLA keser; yeniden uretim yok, piksel posterden.
Yontem: alt bolgede (isimlerin ustu) altin bilesenler (R - B kanali > esik) -> sol glif kutusu (+ pay). Zemin (lacivert gradyan) altin
olmayan piksellerden yumusak tahmin; alfa = (R-B) farkinin zemine gore orani; renk on-carpimdan cozulur (F = (P - (1-a) Z) / a).
Cikti: <burc>_yeni_gold.png (RGBA, kirpilmis) + KONTAK.jpg. kullanim: python poster_burc.py POSTER_BURC.json poster_dir cikti_dir"""
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
c = json.load(open(sys.argv[1])); P, O = Path(sys.argv[2]), Path(sys.argv[3])
rap = {}
kontak = []
for cift in c["posterler"]:
    b = cift.split("_")[0].lower()
    im = np.asarray(Image.open(P / f"{cift}_7200x10800.jpg").convert("RGB")).astype(np.float32)
    H, W = im.shape[:2]
    y0, y1 = int(0.58 * H), int(0.71 * H)                         # onizlemede kucuk burclar ~0.62-0.68 H, isimler ~0.72 H
    bol = im[y0:y1, :W // 2]
    m = bol[..., 0] - bol[..., 2]                                  # altin R >> B, lacivert zemin B > R
    alt = (m > 25).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(alt)
    kut = [st[i] for i in range(1, n) if st[i][4] > 400]
    x0 = min(k[0] for k in kut); xa = max(k[0] + k[2] for k in kut); ya = min(k[1] for k in kut); yb = max(k[1] + k[3] for k in kut)
    pay = 60
    X0, X1, Y0, Y1 = max(0, x0 - pay), min(W // 2, xa + pay), max(0, ya - pay), min(y1 - y0, yb + pay)
    kes = bol[Y0:Y1, X0:X1]; mk = m[Y0:Y1, X0:X1]
    # zemin: altin ve yakini disindaki piksellerden, buyuk bulanik normalize doldurma
    uzak = cv2.dilate((mk > 0).astype(np.uint8), np.ones((31, 31), np.uint8)) == 0
    Z = np.zeros_like(kes)
    for ch in range(3):
        num = cv2.GaussianBlur(kes[..., ch] * uzak, (0, 0), 40); den = cv2.GaussianBlur(uzak.astype(np.float32), (0, 0), 40)
        Z[..., ch] = num / np.maximum(den, 1e-4)
    mz = Z[..., 0] - Z[..., 2]
    tam = np.percentile(mk[mk > 25], 20)                          # altinin koyu tarafi bile tam ortu
    a = np.clip((mk - mz) / max(tam - mz.mean(), 1e-3), 0, 1)
    a[a < 0.03] = 0
    F = (kes - (1 - a[..., None]) * Z) / np.maximum(a[..., None], 1e-3)
    F = np.where(a[..., None] > 0.02, np.clip(F, 0, 255), 0)
    rgba = np.dstack([F, a * 255]).astype(np.uint8)
    al = Image.fromarray(rgba, "RGBA"); al = al.crop(al.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())
    al.save(O / f"{b}_yeni_gold.png")
    rap[b] = dict(poster=cift, kutu=[int(X0), int(Y0 + y0), int(X1), int(Y1 + y0)], boyut=list(al.size), bilesen=len(kut),
                  tam_esik=round(float(tam), 1), zemin_m=round(float(mz.mean()), 1))
    print(b, rap[b], flush=True)
    t = Image.new("RGB", (520, 520), (245, 240, 231)); s = al.copy(); s.thumbnail((480, 480)); t.paste(s, (20, 20), s)
    kontak.append(t)
json.dump(rap, open(O / "POSTER_BURC.json", "w"), indent=1)
k = Image.new("RGB", (520 * 6, 520 * ((len(kontak) + 5) // 6)), (245, 240, 231))
for i, t in enumerate(kontak):
    k.paste(t, ((i % 6) * 520, (i // 6) * 520))
k.save(O / "KONTAK.jpg", quality=90)
