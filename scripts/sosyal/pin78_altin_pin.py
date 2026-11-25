#!/usr/bin/env python3
"""Pinterest altin yakin cekim pini (C), 1000x1500 (Serdar 25 Kas 2026, KARARLAR_20261125_51): PIN_03 / PIN_05 v6 kalibi,
semboller arasindaki "+" yerine onayli altin dokulu AstroLoveArt sonsuz logosu (sosyal/kapak_v1/assets/logo_sonsuz.png).
Yeni tasarim dili YOK:
  - cerceve, panel golgesi, "Add your names": onayli PIN_03_SCORPIO_TAURUS_A_GOLD_v6.jpg pikselleri AYNEN (panel disi);
  - baslik bandi (y 0-256: "<A> & <B>" + "Combined Zodiac Symbol"): ayni ciftin onayli v6 poster pininden AYNEN
    (ornek: PIN_01_CANCER_LEO_A_POSTER_v6.jpg; 78 icin baslik ureticisi ayri is);
  - panel (x 104-896, y 258-1311, olculdu): onayli kapak_v1 kodunun parcalari: lacivert zemin (IGU.navy_glow, posterin kendi
    zemin profili), posterden birlesik sembol (PosterR, yalniz KUCULTME), posterden kucuk burc sembolleri, onayli logo, burc
    adlari (lib.metal_text, posterin altin rampasi). Olculer PIN_03 v6'dan: sembol kutusu 728x771 (panel ici y 34-804),
    kucuk burc satiri 76 px (y 848-923), ad satiri 49 px (y 943-991).
QC (PASS/FAIL): 1000x1500; panel ve baslik bandi disinda PIN_03 ile fark 0; baslik bandi kaynak poster pinle fark 0; sembol
yalniz kucultme (olcek <= 1); ogeler panel icinde >= 24 px pay ve birbirine >= 16 px bosluk; sembol >= 0.9 x PIN_03 sembol
yuksekligi (yakin cekim). Oz-test: bilinen PASS + bilinen FAIL'ler.
Kullanim: pin78_altin_pin.py --poster POSTER2000.jpg --a Cancer --b Leo --cerceve PIN_03_v6.jpg --baslik PIN_01_v6.jpg --out DIR [--oz-test]
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'sosyal', 'ig_v6'))
import ig_uret as IGU   # noqa: E402  (navy_glow + pin_v6: PosterR, sign_pair, lib, layouts)
PU, lib, L = IGU.PU, IGU.lib, IGU.L
LOGO = os.path.join(KOK, 'sosyal', 'kapak_v1', 'assets', 'logo_sonsuz.png')

PX0, PY0, PX1, PY1 = 104, 258, 897, 1312          # panel (x1/y1 haric); PIN_03 v6 olcumu
PW, PH = PX1 - PX0, PY1 - PY0                      # 793 x 1054
BASLIK_Y1 = 257                                    # baslik bandi y < 257 (alt baslik murekkebi 172-244)
SEMBOL_KUTU = (728, 771); SEMBOL_Y = (34, 804)     # PIN_03 panel ici
BURC_H, BURC_Y = 76, (848, 923)
AD_H, AD_Y = 49, (943, 991)
PAY, BOSLUK = 24, 16


def kutu(im, cx, cy):
    a = np.asarray(im)[..., 3] > 20; ys, xs = np.where(a)
    x0 = round(cx - im.size[0] / 2); y0 = round(cy - im.size[1] / 2)
    return (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()), y0 + int(ys.max()))


def panel(poster, A, B):
    IGU.W, IGU.H = PW, PH
    P = PU.PosterR(poster)
    BR = L.bright_ramp(P)
    cv = IGU.navy_glow(P.bg_profile(), 0.42)
    R, bilgi = {}, {}

    def put(ad, im, cx, cy, golge=True):
        lib.paste(cv, im, cx, cy, shadow=golge); R[ad] = kutu(im, cx, cy)

    ham = P.layer(P.merged, only_label=False)
    ol = min(SEMBOL_KUTU[0] / ham.size[0], SEMBOL_KUTU[1] / ham.size[1])
    bilgi['sembol_olcek'] = round(ol, 4); bilgi['sembol_kaynak'] = list(ham.size)
    m = ham.resize((round(ham.size[0] * ol), round(ham.size[1] * ol)), Image.LANCZOS)
    put('sembol', m, PW / 2, (SEMBOL_Y[0] + SEMBOL_Y[1]) / 2)
    sa, sb, sw, r = PU.sign_pair(P, BURC_H)
    yb = (BURC_Y[0] + BURC_Y[1]) / 2
    off = 190                                      # PIN_03: kucuk burc satiri x 168-614 (merkezler ~206 / ~576)
    put('burc_a', sa, PW / 2 - off, yb); put('burc_b', sb, PW / 2 + off, yb)
    logo = Image.open(LOGO).convert('RGBA')
    put('logo', lib.scale_h(logo, round(BURC_H * 0.55)), PW / 2, yb)
    ls = 70
    mk = lambda t, s: lib.metal_text(t.upper(), s, BR, tracking=0.08, bevel=1.0)
    la, lb = mk(A, ls), mk(B, ls)
    while max(la.size[0], lb.size[0]) > 2 * off - 40 or max(la.size[1], lb.size[1]) > AD_H + 26:
        ls -= 2; la, lb = mk(A, ls), mk(B, ls)
    ya = (AD_Y[0] + AD_Y[1]) / 2
    put('ad_a', la, PW / 2 - off, ya, golge=False); put('ad_b', lb, PW / 2 + off, ya, golge=False)
    bilgi['ad_punto'] = ls
    return cv.convert('RGB'), R, bilgi


def uret(poster, A, B, cerceve, baslik):
    fr = Image.open(cerceve).convert('RGB'); bs = Image.open(baslik).convert('RGB')
    im = fr.copy()
    im.paste(bs.crop((0, 0, 1000, BASLIK_Y1)), (0, 0))
    pn, R, bilgi = panel(poster, A, B)
    im.paste(pn, (PX0, PY0))
    return im, R, bilgi


def qc(im, R, bilgi, cerceve, baslik):
    S = []
    k = lambda ad, ok, d='': S.append({'kapi': ad, 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': d})
    a = np.asarray(im).astype(int); fr = np.asarray(Image.open(cerceve).convert('RGB')).astype(int)
    bs = np.asarray(Image.open(baslik).convert('RGB')).astype(int)
    k('boyut 1000x1500', im.size == (1000, 1500), str(im.size))
    m = np.ones(a.shape[:2], bool); m[:BASLIK_Y1] = False; m[PY0:PY1, PX0:PX1] = False
    k('cerceve (panel ve baslik disi) PIN_03 v6 ile fark 0', int(np.abs(a - fr)[m].max()) == 0, f'max {int(np.abs(a - fr)[m].max())}')
    k('baslik bandi kaynak v6 pinle fark 0', int(np.abs(a[:BASLIK_Y1] - bs[:BASLIK_Y1]).max()) == 0, '')
    k('sembol yalniz kucultme', bilgi['sembol_olcek'] <= 1.0, str(bilgi['sembol_olcek']))
    sy = R['sembol'][3] - R['sembol'][1] + 1
    k('sembol yakin cekim (>= 0.9 x 771 px)', sy >= 0.9 * SEMBOL_KUTU[1] or R['sembol'][2] - R['sembol'][0] + 1 >= 0.9 * SEMBOL_KUTU[0], f'{R["sembol"]}')
    ic = all(x0 >= PAY and y0 >= PAY and x1 <= PW - PAY and y1 <= PH - PAY for x0, y0, x1, y1 in R.values())
    k('ogeler panel icinde >= 24 px pay', ic, json.dumps(R))
    ad = list(R); en = 999
    for i in range(len(ad)):
        for j in range(i + 1, len(ad)):
            p, q = R[ad[i]], R[ad[j]]
            en = min(en, max(q[0] - p[2], p[0] - q[2], q[1] - p[3], p[1] - q[3]))
    k('ogeler arasi bosluk >= 16 px', en >= BOSLUK, f'en az {en}')
    return S


def main():
    ap = argparse.ArgumentParser()
    for x in ('poster', 'a', 'b', 'cerceve', 'baslik'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--out'); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    im, R, bilgi = uret(g.poster, g.a, g.b, g.cerceve, g.baslik)
    S = qc(im, R, bilgi, g.cerceve, g.baslik)
    if g.oz_test:
        sonuc = [('bilinen PASS', all(s['sonuc'] == 'PASS' for s in S))]
        b1 = im.copy(); b1.paste((0, 0, 0), (20, 1400, 40, 1420))
        sonuc.append(('FAIL: cerceve bozuldu', any(s['sonuc'] == 'FAIL' for s in qc(b1, R, bilgi, g.cerceve, g.baslik))))
        b2 = dict(bilgi, sembol_olcek=1.2)
        sonuc.append(('FAIL: buyutme', any(s['sonuc'] == 'FAIL' for s in qc(im, R, b2, g.cerceve, g.baslik))))
        R3 = dict(R); R3['logo'] = (R['burc_a'][0] + 5, R['burc_a'][1], R['burc_a'][2] + 5, R['burc_a'][3])
        sonuc.append(('FAIL: ogeler ust uste', any(s['sonuc'] == 'FAIL' for s in qc(im, R3, bilgi, g.cerceve, g.baslik))))
        R4 = dict(R); R4['sembol'] = (300, 300, 500, 500)
        sonuc.append(('FAIL: sembol kucuk (yakin cekim degil)', any(s['sonuc'] == 'FAIL' for s in qc(im, R4, bilgi, g.cerceve, g.baslik))))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    os.makedirs(g.out, exist_ok=True)
    yol = os.path.join(g.out, f'PIN_ALTIN_{g.a.upper()}_{g.b.upper()}.jpg')
    im.save(yol, quality=95, subsampling=0)
    for s in S:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}")
    json.dump({'kapilar': S, 'bilgi': bilgi, 'kutular': R}, open(os.path.join(g.out, 'QC_ALTIN_PIN.json'), 'w'), indent=1)
    sys.exit(0 if all(s['sonuc'] == 'PASS' for s in S) else 1)


if __name__ == '__main__':
    main()
