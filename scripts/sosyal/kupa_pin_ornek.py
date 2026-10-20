#!/usr/bin/env python3
"""Kupa kapagindan 2:3 Pinterest pini, ORNEK (20 Eki 2026, deneme 3: Merkez secenek (a), Serdar onayli). Yapay zeka yok.
Kapak 2048x2048 (kupa_kapak_78.py V4 ciktisi). Kurulum 2048 olceginde (2048x3072), sonra esit olcekle 1000x1500:
  1. Eski baslik (kutu + PAY) stilin yazisiz sahnesiyle (kupa-orchard varlik/sahne/<stil>_k40.png) silinir (V4 yontemi).
  2. Ust: en ust duvar bandi [0, UST_BANT) yansitmali dosenerek yukari uzatilir (deneme 1'de ek yeri gorunmuyordu).
  3. Alt: masa bandi [MASA_KES - h, MASA_KES) tek tam periyot yansitmayla MASA_KES'e eklenir (<= 60 px pin olcegi);
     on kenar yerinde kalir.
  4. Baslik kupa_kapak_78.baslik_ciz ile (Cinzel 650, 104*K, & %62, ara %12, stil rengi) ayni boyda, pin ust kenarindan
     ~BASLIK_UST px'e yeniden yazilir. Kupalar ve "PERSONALIZED GIFT MUG" zemini kapak pikselleri (degismez).
Kontrol (OLCUM.txt, PASS/FAIL): sahne = kapak duvari (ort <= 3); baslik cizimi eski yerinde kapak basligina NCC >= 0.99
  (font/boy/renk dogrulamasi); eski baslik kalintisi 0; kupa ve alt yazi zemini NCC >= 0.99; baslik/alt yazi kenar payi
  >= 40 px; baslik kontrasti >= 4.5; ek satiri komsu fark orani (gosterge; ek yeri icin GOZ KONTROLU ZORUNLU: %200 kirpimlar).
Kullanim: kupa_pin_ornek.py KAPAK.jpg SAHNE.png FONT.ttf CIKTI_DIR [--ad CANCER_LIBRA] [--b1 CANCER --b2 LIBRA] [--stil orange]"""
import argparse, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500
UST_BANT = 190                 # en ust duvar bandi (baslik murekkebi ~200'de basliyordu; satir profili)
MASA_KES, MASA_H = 1975, 31     # on kenar ~1980'de basliyor; alt ek = 2*MASA_H = 62 kaynak satir = ~30 px pin
BASLIK_UST = 120               # pin olceginde baslik ilk satir ust kenari
PAY_SIL = 12                   # kupa_alt_yazi_v4 PAY (eski baslik silme kutusu payi)
NCC_ESIK, PAY, KONTRAST_ESIK, EK_ESIK = 0.99, 40, 4.5, 1.5
RENKLER = {'orange': (10, 40, 24), 'fig': (52, 18, 48), 'olive': (12, 24, 78), 'pomegranate': (100, 16, 24),
           'almond': (52, 22, 14), 'lemon': (12, 22, 76), 'grape': (16, 30, 90), 'loquat': (62, 24, 10)}   # kupa_kapak_78
KUPA_UST, KUPA_ALT, ZEMIN_ALT = 760, 1690, 1830   # 2048 kapak: duvar biter / kupa tabani / alt yazi zemini biter


def yaz(font, m, boy):
    """kupa_alt_yazi_v4.yaz (baslik4.py) ile ayni."""
    f = ImageFont.truetype(str(font), round(boy)); f.set_variation_by_axes([650])
    bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), m, font=f)
    t = Image.new('L', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
    ImageDraw.Draw(t).text((20 - bb[0], 20 - bb[1]), m, font=f, fill=255)
    a = np.asarray(t).astype(float) / 255
    ys, xs = np.where(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def baslik_ciz(im, font, b1, b2, renk, y_ust=None, olcek=1.0):
    """kupa_kapak_78.baslik_ciz ile ayni (K = genislik / 1254). Donus: (kutu, ilk y)."""
    Wi = im.shape[1]; K = Wi / 1254; boy = 104 * K * olcek
    satirlar = [yaz(font, b1.upper(), boy), yaz(font, '&', boy * 0.62), yaz(font, b2.upper(), boy)]
    ara = boy * 0.12
    toplam = sum(s.shape[0] for s in satirlar) + 2 * ara
    y = (300 * K + 40) - toplam / 2 if y_ust is None else float(y_ust)
    y_ilk = y; xs0, xs1, ys = [], [], []
    for s in satirlar:
        h, w = s.shape
        x0, y0 = int(round((Wi - w) / 2)), int(round(y))
        sub = im[y0:y0 + h, x0:x0 + w]
        im[y0:y0 + h, x0:x0 + w] = sub * (1 - s[..., None]) + np.array(renk, float) * s[..., None]
        xs0.append(x0); xs1.append(x0 + w); ys += [y0, y0 + h]
        y += h + ara
    return (min(xs0), min(ys), max(xs1), max(ys)), y_ilk


def kutu(m):
    ys, xs = np.where(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def tri(k, h):
    m = k % (2 * h)
    return m if m < h else 2 * h - 1 - m


def ncc(x, y):
    x = x.astype(float).ravel(); y = y.astype(float).ravel()
    x -= x.mean(); y -= y.mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))


def lum(c):
    c = np.asarray(c, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2])


def main():
    p = argparse.ArgumentParser()
    for x in ('kapak', 'sahne', 'font', 'cikti'):
        p.add_argument(x)
    p.add_argument('--ad', default='CANCER_LIBRA'); p.add_argument('--b1', default='CANCER'); p.add_argument('--b2', default='LIBRA')
    p.add_argument('--stil', default='orange')
    a = p.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    renk = RENKLER[a.stil]
    a0 = np.asarray(Image.open(a.kapak).convert('RGB')); f = a0.astype(float)
    sc = np.asarray(Image.open(a.sahne).convert('RGB')).astype(float)
    S = a0.shape[1]; assert a0.shape[:2] == (2048, 2048) == sc.shape[:2]
    s = W / S
    sat, ok = [], True

    def kayit(ad, gecti, ayr):
        nonlocal ok
        ok &= bool(gecti); sat.append(f'{ad}: {ayr} {"PASS" if gecti else "FAIL"}')

    # 1. eski baslik -> yazisiz sahne
    koyu = np.abs(f - np.array(renk)).max(2) < 40; koyu[int(0.4 * S):] = False
    bk = kutu(koyu)
    dm = np.zeros(koyu.shape, bool); dm[:KUPA_UST - 30] = True
    dm[max(bk[1] - 40, 0):bk[3] + 40, max(bk[0] - 40, 0):bk[2] + 40] = False
    dd = np.abs(f - sc).max(2)[dm]
    kayit('yazisiz sahne = kapak duvari (baslik disi duvar, ort fark)', dd.mean() <= 3, f'ort {dd.mean():.2f}, max {int(dd.max())}')
    t = sc.copy(); bt, _ = baslik_ciz(t, a.font, a.b1, a.b2, renk, y_ust=bk[1])   # V4: ilk satir ust kenari = eski kutu ustu
    x0, y0, x1, y1 = bt
    n0 = ncc(f[y0:y1, x0:x1].mean(2), t[y0:y1, x0:x1].mean(2))
    kayit('baslik cizimi eski yerinde = kapak basligi (font/boy/renk)', n0 >= NCC_ESIK, f'NCC {n0:.4f}')
    e = f.copy()
    ex0, ey0, ex1, ey1 = bk[0] - PAY_SIL, bk[1] - PAY_SIL, bk[2] + PAY_SIL, bk[3] + PAY_SIL
    e[ey0:ey1, ex0:ex1] = sc[ey0:ey1, ex0:ex1]
    kal = int((np.abs(e - np.array(renk)).max(2) < 60)[:KUPA_UST - 30].sum())
    kayit('eski baslik kalintisi', kal == 0, f'{kal} px')

    # 2-3. uzatma
    hedef = round(S * H / W); alt = 2 * MASA_H; ust = hedef - S - alt
    ustb = e[:UST_BANT]
    ust_satir = np.stack([ustb[tri(k, UST_BANT)] for k in range(ust)])[::-1]
    band = e[MASA_KES - MASA_H:MASA_KES]
    alt_satir = np.stack([band[MASA_H - 1 - tri(k, MASA_H)] for k in range(alt)])
    big = np.concatenate([ust_satir, e[:MASA_KES], alt_satir, e[MASA_KES:]])
    assert big.shape[0] == hedef

    # 4. baslik
    by = round(BASLIK_UST / s)
    duvar8 = np.clip(np.rint(big), 0, 255).astype(np.uint8)   # ek olcumu baslik cizilmeden once (baslik murekkebi ek degil)
    bn, _ = baslik_ciz(big, a.font, a.b1, a.b2, renk, y_ust=by)
    big8 = np.clip(np.rint(big), 0, 255).astype(np.uint8)
    pin = Image.fromarray(big8).resize((W, H), Image.LANCZOS)
    kap = Image.fromarray(a0).resize((W, W), Image.LANCZOS)
    P, K = np.asarray(pin).astype(float), np.asarray(kap).astype(float)
    off = ust * s
    sat.insert(0, f'PIN {W}x{H}; kapak {S}x{S} esit olcek {s:.5f}; ust uzatma {ust * s:.1f} px (duvar bandi 0-{UST_BANT} yansitma), '
                  f'alt uzatma {alt * s:.1f} px (masa bandi {MASA_KES - MASA_H}-{MASA_KES} tek periyot yansitma, on kenar korunur); '
                  f'eski baslik {bk} +{PAY_SIL} px {a.stil}_k40 sahnesiyle silindi; baslik Cinzel 650 #{renk[0]:02X}{renk[1]:02X}{renk[2]:02X} '
                  f'ayni boy (olcek 1.0); yapay zeka yok')
    for ad, (k0, k1) in {'kupa': (KUPA_UST, KUPA_ALT), 'alt yazi zemini': (KUPA_ALT, ZEMIN_ALT)}.items():
        q0, q1 = round(k0 * s), round(k1 * s)
        v = ncc(P[round(q0 + off):round(q1 + off)], K[q0:q1])
        kayit(f'NCC {ad} (kapak y {q0}-{q1}, pin y {round(q0 + off)}-{round(q1 + off)})', v >= NCC_ESIK, f'{v:.5f}')
    # yerlesim (pin olcegi)
    g = P.mean(2)
    def murekkep(y0, y1):
        m = g[y0:y1] < 90; ys, xs = np.where(m)
        return int(xs.min()), int(ys.min()) + y0, int(xs.max()), int(ys.max()) + y0
    bx0, bY0, bx1, bY1 = murekkep(0, round(KUPA_UST * s + off) - 20)
    zx0, zY0, zx1, zY1 = murekkep(round(KUPA_ALT * s + off), round(ZEMIN_ALT * s + off))
    for ad, (u0, v0, u1, v1) in {'baslik': (bx0, bY0, bx1, bY1), 'alt yazi': (zx0, zY0, zx1, zY1)}.items():
        pay = min(u0, W - 1 - u1, v0, H - 1 - v1)
        kayit(f'{ad} murekkep x {u0}-{u1}, y {v0}-{v1}; en dar kenar payi', pay >= PAY, f'{pay} px (esik {PAY})')
    # kupa ust kenari (pin): kupa govdesi notr beyaz ilk satir
    nt = (P.min(2) > 150) & (P.max(2) - P.min(2) < 10)
    gov = nt[:, round(327 * s):round(1726 * s)].mean(1)
    kupa_ust = int(np.where(gov > 0.3)[0].min())
    sat.append(f'bosluk: pin ust kenar -> baslik {bY0} px; baslik alt -> kupa ust kenari {kupa_ust - bY1} px (kupa ust y {kupa_ust})')
    duv = np.median(big8[max(bn[1] - 60, 0):bn[1] - 5, bn[0]:bn[2]].reshape(-1, 3), 0)
    L1, L2 = lum(np.array(renk)), lum(duv)
    kt = (max(L1, L2) + 0.05) / (min(L1, L2) + 0.05)
    kayit('baslik kontrasti', kt >= KONTRAST_ESIK, f'{kt:.2f}')
    # ek satirlari (gosterge)
    d = np.abs(np.diff(duvar8.astype(float), axis=0)).mean((1, 2))
    ref_u = float(np.median(np.abs(np.diff(e[:UST_BANT], axis=0)).mean((1, 2))))
    ref_a = float(np.median(np.abs(np.diff(e[MASA_KES - 4 * MASA_H:], axis=0)).mean((1, 2))))
    ekler = [ust - 1 - i * UST_BANT for i in range(ust // UST_BANT + 1)] + [ust + MASA_KES - 1 + i * MASA_H for i in range(3)]
    orl = {y: d[y] / (ref_u if y < ust else ref_a) for y in ekler if y >= 0}
    oran = max(orl.values())
    kayit(f'ek satiri komsu fark orani (gosterge, {len(ekler)} ek)', oran <= EK_ESIK,
          f'en kotu {oran:.2f} (esik {EK_ESIK}); ' + ', '.join(f'{y}:{v:.2f}' for y, v in orl.items()))
    # pin olceginde duvar satir ortalamasi adimi (baslik sutunlari disi): kivrim satirlari vs tum duvar medyani
    yk = round(KUPA_UST * s + off) - 30
    gd = np.concatenate([P[:yk, 40:max(bx0 - 30, 41)], P[:yk, min(bx1 + 30, W - 41):W - 40]], 1).mean(2).mean(1)
    ad_ = np.abs(np.diff(gd)); med = float(np.median(ad_))
    ky = [round((y + 1) * s) for y in ekler if 0 <= y < ust]
    km = max(float(ad_[max(y - 2, 0):y + 2].max()) for y in ky)
    sat.append(f'duvar satir ortalamasi adimi (pin, baslik disi sutunlar): kivrim satirlarinda max {km:.3f}, tum duvar max '
               f'{float(ad_.max()):.3f} (y {int(ad_.argmax())}), medyan {med:.3f} (8 bit; gosterge)')
    sat.append('EK YERI GOZ KONTROLU: YAKIN_*.jpg (%200) ve KONTAK; olcum tek basina yeterli degil (deneme 1-2)')
    sat.append(f'SONUC (olculebilir kapilar) {"PASS" if ok else "FAIL"}')

    pin.save(os.path.join(a.cikti, f'PIN_KUPA_{a.ad}.jpg'), quality=92, subsampling=0, optimize=True)
    try:
        ft = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except OSError:
        ft = ImageFont.load_default()
    c = Image.new('RGB', (W * 2 + 60, H + 80), 'white')
    c.paste(kap, (20, 60 + (H - W) // 2)); c.paste(pin, (W + 40, 60))
    dr = ImageDraw.Draw(c)
    dr.text((20, 20), 'KAPAK 2048 -> 1000x1000', font=ft, fill=(0, 0, 0))
    dr.text((W + 40, 20), 'PIN 1000x1500', font=ft, fill=(0, 0, 0))
    c.save(os.path.join(a.cikti, f'KONTAK_KAPAK_PIN_{a.ad}.jpg'), quality=90)
    # %200 yakin kirpimlar (pin olceginden 500x300 alan -> 1000x600)
    ty = round(off)
    yakin = {'1_UST_DUVAR_KIVRIM': (250, max(ty - UST_BANT * s - 150, 0)), '2_UST_EK_KAPAK_SINIRI': (250, ty - 150),
             '3_ESKI_BASLIK_SILINEN': (250, round(ty + (bk[1] + bk[3]) / 2 * s - 150)), '4_BASLIK_YENI': (250, max(bY0 - 60, 0)),
             '5_ALT_MASA_EK': (250, H - 300), '6_ALT_MASA_EK_SOL': (0, H - 300), '7_ALT_MASA_EK_SAG': (500, H - 300)}
    for ad, (x, y) in yakin.items():
        y = int(min(max(y, 0), H - 300))
        pin.crop((x, y, x + 500, y + 300)).resize((1000, 600), Image.LANCZOS).save(os.path.join(a.cikti, f'YAKIN_{ad}_y{y}.jpg'), quality=92)
    ky0 = max(min(ky, key=lambda y: abs(y - (bY1 + 60))) - 90, 0)
    c6 = P[ky0:ky0 + 180, 250:750]; c6 = np.clip((c6 - c6.mean()) * 6 + 128, 0, 255).astype(np.uint8)
    Image.fromarray(c6).resize((1000, 360), Image.LANCZOS).save(os.path.join(a.cikti, f'YAKIN_8_UST_KIVRIM_KONTRAST_x6_y{ky0}.jpg'), quality=92)
    open(os.path.join(a.cikti, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
