#!/usr/bin/env python3
"""IG karusel ILK SLAYT ornegi (20 Eki 2026, yalniz CANCER_LIBRA; Metricool'a yazma yok). 1080x1350 (4:5), iki surum:
  A  PIN_P2a_v2 kurali 4:5'e: duvar (data/pod/kapak_sahne_v9.png -> leke_azalt GUCLU -> aydinlat ACIK-3, pin ile ayni
     duvar_zemin yolu), ustte tek satir "CANCER & LIBRA" (P2a_v2 gibi tek satir; EB Garamond wght 430, #162641),
     altinda cercevesiz poster + PIN_V2 golgesi.
  B  A'nin aynisi; yalniz baslik "Cancer & Libra, as one?" (mevcut karusel sorusu). Sigmazsa YALNIZ baslik kuculur.
Poster: onayli P2a_v2.jpg (3000x2250) icindeki poster kutusu (787, 326, 2212, 2140) = 1425x1814 (P0 11:14 posterinin
yalniz olceklenmis hali, NCC 0.9999); burada yalniz LANCZOS ile kuculur (olcek <= 1), AI yok, cerceve yok.
Olculer P2a_v2'den oransal: baslik 192 px / poster 1814 px, baslik murekkep alti - poster ust arasi 80 / 1814, ust ve alt
pay esit. IG profil izgarasi 4:5'i ortadan 3:4 kirpar (her yandan 33.75 px): baslik ve poster x [34+PAY, 1046-PAY].
Cikti: A.jpg, B.jpg, ONIZLEME_IZGARA.jpg (iki surumun 3:4 orta kirpimi yan yana), ONIZLEME_AKIS.jpg (4:5 tam), OLCUM.txt.
Kullanim: ig_karusel_ilk_slayt.py --p2a P2a_v2.jpg --font EBGaramond[wght].ttf --out DIR"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'sosyal', 'video_v9'))
import acilis_p as AP  # noqa: E402  (satir, golge, lum, G_P, RENK: PIN_V2 kurali ile ayni)
from duvar_zemin import AYDINLIK, LEKE, aydinlat, leke_azalt  # noqa: E402

W, H = 1080, 1350
KUTU = (787, 326, 2212, 2140)                 # P2a_v2 poster kutusu
P2A_BASLIK, P2A_ARA, P2A_POSTER_H = 192, 80, 1814
IZGARA_KES = (W - H * 3 / 4) / 2              # 33.75 px
PAY = 20
X0, X1 = IZGARA_KES + PAY, W - IZGARA_KES - PAY
BASLIK = {'A': 'CANCER & LIBRA', 'B': 'Cancer & Libra, as one?'}
YASAK = ('.', '+', '=')


def duvar45():
    sc = Image.open(os.path.join(KOK, 'data/pod/kapak_sahne_v9.png')).convert('RGB')
    D = leke_azalt(sc.resize((1213, 910), Image.LANCZOS).resize((2 * W, 2 * H), Image.LANCZOS), LEKE['guclu'])
    return aydinlat(D, *AYDINLIK['acik3']).resize((W, H), Image.LANCZOS)


def tek_satir(font, metin, boy):
    """satir(): siki kirpilmis maske + taban cizgisi (maske ustunden)."""
    return AP.satir(font, metin, boy)


def yerlesim(font):
    """En buyuk poster yuksekligi ph: blok (baslik murekkebi + ara + poster) ust/alt PAY_DIKEY esit, A basligi ve poster
    izgara guvenli alaninda. B basligi ayni boyutta sigmazsa yalniz o kuculur."""
    for ph in range(1300, 400, -2):
        T = P2A_BASLIK * ph / P2A_POSTER_H
        ara = round(P2A_ARA * ph / P2A_POSTER_H)
        m, bl = tek_satir(font, BASLIK['A'], T)
        pw = round(ph * (KUTU[2] - KUTU[0]) / (KUTU[3] - KUTU[1]))
        blok = bl + ara + ph                      # taban cizgisinden (A: caps, murekkep alti = taban) posterin altina
        pay_dikey = round(108 / 2250 * H)         # P2a_v2 ust pay orani (108 / 2250)
        if blok + 2 * pay_dikey <= H and m.shape[1] <= X1 - X0 and pw <= X1 - X0:
            return ph, pw, T, ara, pay_dikey
    raise SystemExit('yerlesim sigmadi')


def ciz(D, font, metin, T, taban_y, ph, pw, px, py, P):
    im = AP.golge(D, (px, py, px + pw, py + ph), [(dx * ph / 990, dy * ph / 990, sg * ph / 990, g) for dx, dy, sg, g in AP.G_P])
    Pk = P.resize((pw, ph), Image.LANCZOS)
    im.paste(Pk, (px, py))
    arr = np.asarray(im).astype(np.float32)
    boy = T
    while True:
        m, bl = tek_satir(font, metin, boy)
        if m.shape[1] <= X1 - X0:
            break
        boy -= 0.5
    x = round((W - m.shape[1]) / 2)
    y = round(taban_y - bl)
    h_, w_ = m.shape
    arr[y:y + h_, x:x + w_] = arr[y:y + h_, x:x + w_] * (1 - m[..., None]) + np.array(AP.RENK, np.float32) * m[..., None]
    return np.clip(arr, 0, 255).astype(np.uint8), (x, y, x + w_, y + h_), boy, Pk


def ncc(a, b):
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))


def main():
    ap = argparse.ArgumentParser()
    for k in ('p2a', 'font', 'out'):
        ap.add_argument('--' + k, required=True)
    o = ap.parse_args()
    os.makedirs(o.out, exist_ok=True)
    P = Image.open(o.p2a).convert('RGB').crop(KUTU)
    ph, pw, T, ara, pay_dikey = yerlesim(o.font)
    mA, blA = tek_satir(o.font, BASLIK['A'], T)
    blok = blA + ara + ph
    taban_y = round((H - blok) / 2 + blA)
    py = taban_y + ara
    px = round((W - pw) / 2)
    D = duvar45()
    sat, ok = [], True

    def k(ad, kosul, ayrinti):
        nonlocal ok
        ok &= bool(kosul)
        sat.append(f"{'PASS' if kosul else 'FAIL'} {ad}: {ayrinti}")

    olcek = ph / P.height
    k('poster olcek <= 1', olcek <= 1, f'kaynak {P.width}x{P.height} -> {pw}x{ph} (olcek {olcek:.4f}, oran {pw / ph:.4f} / kaynak {P.width / P.height:.4f})')
    sonuc = {}
    for s, metin in BASLIK.items():
        k(f'{s} yasak karakter yok (. + =)', not any(c in metin for c in YASAK), repr(metin))
        arr, bk, boy, Pk = ciz(D, o.font, metin, T, taban_y, ph, pw, px, py, P)
        Image.fromarray(arr).save(os.path.join(o.out, f'{s}.jpg'), quality=95, subsampling=0)
        J = np.asarray(Image.open(os.path.join(o.out, f'{s}.jpg')).convert('RGB'))
        n = ncc(J[py:py + ph, px:px + pw], np.asarray(Pk))
        k(f'{s} poster pikseli = kaynak (cercevesiz)', n >= 0.999, f'NCC {n:.5f} (JPEG sonrasi), kutu ({px}, {py}, {px + pw}, {py + ph})')
        kenar = J[py:py + ph, px:px + pw].astype(int)
        halka = np.concatenate([kenar[:3].reshape(-1, 3), kenar[-3:].reshape(-1, 3), kenar[:, :3].reshape(-1, 3), kenar[:, -3:].reshape(-1, 3)])
        kh = np.concatenate([np.asarray(Pk)[:3].reshape(-1, 3), np.asarray(Pk)[-3:].reshape(-1, 3), np.asarray(Pk)[:, :3].reshape(-1, 3), np.asarray(Pk)[:, -3:].reshape(-1, 3)]).astype(int)
        k(f'{s} cerceve yok (poster kenar 3 px = kaynak kenari)', np.abs(halka - kh).mean() < 3, f'ortalama fark {np.abs(halka - kh).mean():.2f}')
        for ad, (gx0, gx1) in {'izgara 3:4': (IZGARA_KES, W - IZGARA_KES), 'akis 4:5': (0, W)}.items():
            for nesne, (a0, b0, a1, b1) in {'baslik': bk, 'poster': (px, py, px + pw, py + ph)}.items():
                sol, sag, ust, alt = a0 - gx0, gx1 - a1, b0, H - b1
                k(f'{s} {ad} {nesne} kesilmez', min(sol, sag, ust, alt) >= PAY,
                  f'kutu ({a0}, {b0}, {a1}, {b1}); pay sol {sol:.1f} sag {sag:.1f} ust {ust} alt {alt} (>= {PAY})')
        k(f'{s} baslik - poster cakismaz', bk[3] < py, f'baslik murekkep alti {bk[3]}, poster ust {py}, bosluk {py - bk[3]}')
        Dl = AP.lum(np.asarray(D).astype(np.float64)[bk[1]:bk[3], bk[0]:bk[2]])
        kon = (float(np.percentile(Dl, 5)) + 0.05) / (float(AP.lum(np.array(AP.RENK))) + 0.05)
        k(f'{s} kontrast >= 4.5', kon >= 4.5, f'{kon:.2f}:1 (#162641, duvar %5 parlakligi baslik kutusunda)')
        sonuc[s] = dict(boy=boy, kutu=bk, J=J)
        sat.append(f'INFO {s}: baslik "{metin}" {boy:.1f} px (A kurali {T:.1f} px, kucultme {boy / T:.4f}), kutu {bk}')
    # onizlemeler: izgara (3:4 orta kirpim) ve akis (4:5 tam), A | B yan yana, 1/2 olcek
    x0, x1 = round(IZGARA_KES), round(W - IZGARA_KES)
    iz = [Image.fromarray(sonuc[s]['J'][:, x0:x1]).resize(((x1 - x0) // 2, H // 2), Image.LANCZOS) for s in 'AB']
    tuval = Image.new('RGB', (iz[0].width * 2 + 30, iz[0].height + 20), 'white')
    for i, t in enumerate(iz):
        tuval.paste(t, (10 + i * (t.width + 10), 10))
    tuval.save(os.path.join(o.out, 'ONIZLEME_IZGARA.jpg'), quality=92)
    ak = [Image.fromarray(sonuc[s]['J']).resize((W // 2, H // 2), Image.LANCZOS) for s in 'AB']
    tuval = Image.new('RGB', (W + 30, H // 2 + 20), 'white')
    for i, t in enumerate(ak):
        tuval.paste(t, (10 + i * (t.width + 10), 10))
    tuval.save(os.path.join(o.out, 'ONIZLEME_AKIS.jpg'), quality=92)
    bas = [f'IG KARUSEL ILK SLAYT (CANCER_LIBRA, 1080x1350; Metricool yazma 0): {"PASS" if ok else "FAIL"}',
           f'Poster kaynagi: P2a_v2.jpg kutu {KUTU} ({P.width}x{P.height}); duvar kapak_sahne_v9 leke_azalt guclu + acik3',
           f'Yerlesim: poster {pw}x{ph} @({px}, {py}); baslik taban y {taban_y}; ara {ara} px; kural baslik {T:.1f} px '
           f'(P2a_v2 192/1814); IG izgara 3:4 kirpimi her yandan {IZGARA_KES} px; guvenli x [{X0}, {X1}]',
           f'Golge (PIN_V2, olcek {ph / 990:.3f}): ' + str([[round(dx * ph / 990, 1), round(dy * ph / 990, 1), round(sg * ph / 990, 1), g] for dx, dy, sg, g in AP.G_P])]
    open(os.path.join(o.out, 'OLCUM.txt'), 'w').write('\n'.join(bas + sat) + '\n')
    print('\n'.join(bas + sat))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
