#!/usr/bin/env python3
"""Kupa kapagindan 2:3 Pinterest pini (ORNEK, 20 Eki 2026). Yapay zeka yok; uzatma kapagin kendi pikselleriyle.
Kapak 2048x2048 (baslik ustte, altta "PERSONALIZED GIFT MUG" zemini, en altta masa on kenari).
Yontem (2048 olceginde kurulur, sonra esit olcekle 1000x1500'e indirilir):
  ust: en ust duvar bandi [0, UST_BANT) yansitmali dosenerek yukari uzatilir (UST satir).
  alt: masa ust yuzeyi bandi [MASA_KES - h, MASA_KES) ayrilir: doku (yuksek frekans) tam periyot yansitmayla (n kez),
       isik (satir basina yatay alcak geciren) MASA_KES-1 -> MASA_KES dogrusal surer; MASA_KES'e eklenir;
       on kenar (MASA_KES..2048) yerinde kalir. Tam periyot -> eklemin iki ucu da kaynak satira bitisik (sureklilik).
  Kupa, baslik ve alt yazi pikselleri kaydirilir, degistirilmez.
Kontrol (PASS/FAIL): kupa/baslik/alt yazi bolgeleri NCC >= 0.99 (pin vs kapagin ayni olcekli hali);
  her ek/kivrim satirinda komsu satir farki / kaynak bandin medyan komsu satir farki <= EK_ESIK;
  baslik ve alt yazi murekkebi kenarlara >= 40 px.
Kullanim: kupa_pin_ornek.py KAPAK.jpg CIKTI_DIR [--ad CANCER_LIBRA]"""
import argparse, os
import numpy as np
from PIL import Image, ImageDraw

W, H = 1000, 1500
UST_BANT = 190            # duvar, baslik murekkebi ~200'de basliyor (satir profili)
MASA_KES, MASA_H, MASA_N = 1975, 106, 2   # on kenar ~1980'de basliyor; alt yazi zemini ~1820'de bitiyor
MASA_SIGMA = 25          # masa isik bileseni yatay Gauss sigma (px, 2048 olcek)
EK_ESIK = 1.5
NCC_ESIK = 0.99
PAY = 40
# 2048 olcekli bolgeler (y0, y1): satir profili olcumu (koyu piksel / std)
BOLGE = {'baslik': (190, 610), 'kupa': (760, 1690), 'alt_yazi': (1690, 1830)}


def tri(k, h):
    """0,1..h-1,h-1..0,0,1.. (yansitmali doseme indeksi)"""
    m = k % (2 * h)
    return m if m < h else 2 * h - 1 - m


def kur(a):
    S = a.shape[1]
    hedef = round(S * H / W)                 # 2048 -> 3072
    ek = hedef - S
    alt = 2 * MASA_H * MASA_N
    ust = ek - alt
    ustb = a[:UST_BANT]
    ust_satir = np.stack([ustb[tri(k, UST_BANT)] for k in range(ust)])[::-1]   # yukari dogru
    # masa: isik (yatay alcak geciren, satir basina) + doku (yuksek frekans) ayrimi. Yansitma yalniz dokuya uygulanir;
    # isik bileseni MASA_KES-1 ve MASA_KES satirlari arasinda dogrusal surer (capraz golge yansitmada zikzak yapiyordu).
    af = a.astype(float)
    Lb = yatay_alcak(af[MASA_KES - MASA_H:MASA_KES + 1])
    hp = af[MASA_KES - MASA_H:MASA_KES] - Lb[:MASA_H]
    l0, l1 = Lb[MASA_H - 1], Lb[MASA_H]
    alt_satir = np.stack([l0 + (l1 - l0) * (k + 1) / (alt + 1) + hp[MASA_H - 1 - tri(k, MASA_H)] for k in range(alt)])
    alt_satir = np.clip(np.rint(alt_satir), 0, 255).astype(np.uint8)
    b = np.concatenate([ust_satir, a[:MASA_KES], alt_satir, a[MASA_KES:]])
    assert b.shape[0] == hedef, b.shape
    ekler = [ust - 1] + [ust + MASA_KES - 1 + i * MASA_H for i in range(2 * MASA_N + 1)]  # kivrim/eklem satirlari
    ust_kivrim = [ust - 1 - i * UST_BANT for i in range(1, ust // UST_BANT + 1)]
    return b, ust, ekler + ust_kivrim


def yatay_alcak(x, sigma=MASA_SIGMA):
    """satir basina yatay Gauss (dikey karisma yok); kenarlar yansitmali"""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    xp = np.pad(x, ((0, 0), (r, r), (0, 0)), mode='reflect')
    o = np.zeros_like(x)
    for i, w in enumerate(k):
        o += w * xp[:, i:i + x.shape[1]]
    return o


def ncc(x, y):
    x = x.astype(float).ravel(); y = y.astype(float).ravel()
    x -= x.mean(); y -= y.mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))


def murekkep_x(img, y0, y1):
    g = img[y0:y1].mean(2)
    cols = np.where((g < 90).sum(0) > 0)[0]   # koyu yesil yazi
    return (int(cols.min()), int(cols.max())) if len(cols) else (None, None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('kapak'); p.add_argument('cikti'); p.add_argument('--ad', default='CANCER_LIBRA')
    a = p.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    src = np.asarray(Image.open(a.kapak).convert('RGB'))
    assert src.shape[:2] == (2048, 2048), src.shape
    big, ust, ekler = kur(src)
    s = W / src.shape[1]
    pin = Image.fromarray(big).resize((W, H), Image.LANCZOS)
    kap = Image.fromarray(src).resize((W, W), Image.LANCZOS)
    P, K = np.asarray(pin).astype(float), np.asarray(kap).astype(float)
    sat = []
    ok = True
    off = round(ust * s)
    for ad, (y0, y1) in BOLGE.items():
        k0, k1 = round(y0 * s), round(y1 * s)
        v = ncc(P[k0 + off:k1 + off], K[k0:k1])
        ok &= v >= NCC_ESIK
        sat.append(f'NCC {ad} (kapak y {k0}-{k1}, pin y {k0 + off}-{k1 + off}): {v:.5f} {"PASS" if v >= NCC_ESIK else "FAIL"} (esik {NCC_ESIK})')
    # ek yeri: 2048 olcekli kurulumda komsu satir farki
    B = big.astype(float)
    d = np.abs(np.diff(B, axis=0)).mean((1, 2))
    ref_ust = float(np.median(np.abs(np.diff(src[:UST_BANT].astype(float), axis=0)).mean((1, 2))))
    ref_alt = float(np.median(np.abs(np.diff(src[MASA_KES - MASA_H:].astype(float), axis=0)).mean((1, 2))))
    enk = 0.0
    for y in sorted(set(ekler)):
        ref = ref_ust if y < ust else ref_alt
        r = d[y] / ref if ref else 0
        enk = max(enk, r)
        sat.append(f'ek satiri {y} ({"ust duvar" if y < ust else "masa"}): komsu fark {d[y]:.2f} / kaynak medyan {ref:.2f} = {r:.2f}')
    ok &= enk <= EK_ESIK
    sat.append(f'EK YERI en kotu oran {enk:.2f} {"PASS" if enk <= EK_ESIK else "FAIL"} (esik {EK_ESIK})')
    for ad in ('baslik', 'alt_yazi'):
        y0, y1 = BOLGE[ad]
        x0, x1 = murekkep_x(P, round(y0 * s) + off, round(y1 * s) + off)
        ys = np.where((P[round(y0 * s) + off:round(y1 * s) + off].mean(2) < 90).sum(1) > 0)[0]
        ty, by = int(ys.min()) + round(y0 * s) + off, int(ys.max()) + round(y0 * s) + off
        pay = min(x0, W - 1 - x1, ty, H - 1 - by)
        ok &= pay >= PAY
        sat.append(f'{ad} murekkep x {x0}-{x1}, y {ty}-{by}; en dar kenar payi {pay} px {"PASS" if pay >= PAY else "FAIL"} (esik {PAY})')
    sat.insert(0, f'PIN {W}x{H}, kapak {src.shape[1]}x{src.shape[0]} -> esit olcek {s:.5f}; ust uzatma {round(ust * s)} px '
                  f'(duvar bandi 0-{UST_BANT} yansitma), alt uzatma {round(2 * MASA_H * MASA_N * s)} px (masa bandi '
                  f'{MASA_KES - MASA_H}-{MASA_KES} doku yansitma x{MASA_N} + isik dikey surdurme, on kenar korunur); yapay zeka yok')
    sat.append(f'SONUC {"PASS" if ok else "FAIL"}')
    jp = os.path.join(a.cikti, f'PIN_KUPA_{a.ad}.jpg')
    pin.save(jp, quality=92, subsampling=0, optimize=True)
    # kontak: kapak (1000x1000, dikey ortali) | pin, 1500 yukseklik
    c = Image.new('RGB', (W * 2 + 60, H + 80), (245, 245, 245))
    c.paste(kap, (20, 40 + (H - W) // 2)); c.paste(pin, (W + 40, 40))
    dr = ImageDraw.Draw(c)
    dr.text((20, 12), 'KAPAK 2048 -> 1000x1000', fill=(0, 0, 0)); dr.text((W + 40, 12), f'PIN 1000x1500  {sat[-1]}', fill=(0, 0, 0))
    c.save(os.path.join(a.cikti, f'KONTAK_KAPAK_PIN_{a.ad}.jpg'), quality=88)
    open(os.path.join(a.cikti, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
