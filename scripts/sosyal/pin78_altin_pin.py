#!/usr/bin/env python3
"""Pinterest altin yakin cekim pini (C), 1000x1500 (Serdar 25 Kas 2026, KARARLAR_20261125_51): PIN_03 / PIN_05 v6 kalibi,
semboller arasindaki "+" yerine onayli altin dokulu AstroLoveArt sonsuz logosu (sosyal/kapak_v1/assets/logo_sonsuz.png).
2. surum (bagimsiz inceleme 25 Kas: 1. surum zemini ve kucuk glifleri kapak_v1'den aliyordu, PIN_03 yonteminden degil).
PIN_03 v6 yontemi (PINLER_ORNEK 6.1): duz lacivert zemin, yeni altin birlesik sembol, kucuk burc glifleri B kartlarindan
(koyu cizgi) yeni altin degradeyle boyanmis, burc adlari Palatino buyuk harf altin degrade. Burada:
  - cerceve, panel golgesi, "Add your names": onayli PIN_03_SCORPIO_TAURUS_A_GOLD_v6.jpg pikselleri AYNEN (panel disi);
  - baslik bandi (y 0-256): ayni ciftin onayli v6 poster pininden AYNEN (ornek CANCER_LEO; 78 icin baslik ureticisi ayri is);
  - panel zemini: PIN_03 panelinin altin (ve 7 px hale) disi piksellerinden OLCULEN radyal renk profili;
  - birlesik sembol: posterden (PosterR, yeni altin; yalniz KUCULTME), PIN_03 sembol kutusuna (728x771);
  - kucuk glifler: ciftin onayli v6 B kartindaki (ornek PIN_02_CANCER_LEO_B_SYMBOL_v6.jpg) koyu cizgi glifleri, maske olarak;
    renk = PIN_03 glif satirindan OLCULEN dikey altin degrade; yukseklik 76 px (PIN_03 satiri y 848-923);
  - burc adlari: TeX Gyre Pagella (Palatino klonu; Palatino Linotype Linux'ta yok) buyuk harf, buyuk harf yuksekligi 49 px
    (PIN_03 ad satiri y 943-991), renk PIN_03 ad satirindan OLCULEN dikey degrade;
  - logo: onayli dosya, "+" yerine, glif satirinin ortasinda.
QC (kaydedilen JPEG uzerinde; PASS/FAIL): boyut; panel disi PIN_03 ve baslik bandi kaynakla p99.9 <= 8 (JPEG gurultusu 4);
panel zemini radyal profili (altin ve hale disi) PIN_03 profiliyle kanal farki <= 8; glif satiri ve ad satiri ortalama altin rengi PIN_03
ile kanal farki <= 15; ad buyuk harf yuksekligi >= 45 px (168 px akista >= 11 CSS px: 45 / 0.69 x 0.168 = 11.0); sembol
yuksekligi >= 0.9 x 771 ya da genisligi >= 0.9 x 728; sembol olcegi <= 1 (kaynak ve cikti boyundan HESAPLANIR); ogeler panel
icinde >= 24 px pay ve birbirine >= 12 px bosluk (cikti maskesinden). Oz-test: bilinen PASS + bilinen FAIL'ler (1. surumun
kapak zemini, sembol icin buyutme, kucuk ad, cerceve bozulmasi).
Kullanim: pin78_altin_pin.py --poster POSTER2000.jpg --a Cancer --b Leo --cerceve PIN_03_v6.jpg --baslik PIN_01_v6.jpg
          --kart PIN_02_v6.jpg --out DIR [--oz-test]
"""
import argparse, json, os, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'sosyal', 'ig_v6'))
import ig_uret as IGU   # noqa: E402  (pin_v6: PosterR, lib)
PU, lib = IGU.PU, IGU.lib
LOGO = os.path.join(KOK, 'sosyal', 'kapak_v1', 'assets', 'logo_sonsuz.png')
FONT = '/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-regular.otf'

PX0, PY0, PX1, PY1 = 104, 258, 897, 1312          # panel (x1/y1 haric); PIN_03 v6 olcumu
PW, PH = PX1 - PX0, PY1 - PY0                      # 793 x 1054
BASLIK_Y1 = 257
SEMBOL_KUTU = (728, 771); SEMBOL_Y = (34, 804)     # PIN_03 panel ici
GLIF_H, GLIF_Y = 76, (848, 923)
AD_H, AD_Y = 49, (943, 991)
GLIF_CX = (206, 576)                               # PIN_03 glif satiri x 168-614: sol/sag glif merkezleri (panel ici)
PAY, BOSLUK = 24, 12
# Serdar 25 Kas karari A (Merkez aktarimi): bu 6 ciftte ad BUYUK HARF, sigan en buyuk boyda (36-44 px); 45 px kapisina istisna
AD_ISTISNA = {'AQUARIUS_CAPRICORN', 'AQUARIUS_SAGITTARIUS', 'CAPRICORN_CAPRICORN', 'CAPRICORN_SAGITTARIUS', 'SAGITTARIUS_SAGITTARIUS',
              'SAGITTARIUS_SCORPIO'}


def altin_maske(p):
    return (p[..., 0] > 110) & (p[..., 0] > p[..., 2] + 50)


def profil(a):
    """panelin altin (ve 7 px halesi) disindaki piksellerinin radyal medyan renk profili (40 halka)."""
    g = altin_maske(a.astype(int))
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))) > 0   # altin + hale disi
    yy, xx = np.mgrid[0:PH, 0:PW]
    r = np.sqrt(((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2)
    kut = np.linspace(0, r.max() + 1e-6, 41)
    prof = []
    for i in range(40):
        m = (~g) & (r >= kut[i]) & (r < kut[i + 1])
        prof.append(np.median(a[m], 0) if m.sum() > 50 else None)
    son = None
    for i in range(40):                  # bos halkalar komsudan doldurulur
        if prof[i] is None:
            prof[i] = son
        son = prof[i]
    for i in range(39, -1, -1):
        if prof[i] is None:
            prof[i] = prof[i + 1]
    return (kut[:-1] + kut[1:]) / 2, np.array(prof)


def olc_pin03(cerceve):
    a = np.asarray(Image.open(cerceve).convert('RGB')).astype(float)[PY0:PY1, PX0:PX1]
    kut, prof = profil(a)

    def degrade(y0, y1):
        sub = a[y0:y1]; gg = altin_maske(sub.astype(int)) & (sub.sum(2) > 350)
        sat = [sub[i][gg[i]].mean(0) for i in range(y1 - y0) if gg[i].sum() > 3]
        return np.array(sat)
    return {'kut': kut, 'prof': prof, 'glif': degrade(*GLIF_Y), 'ad': degrade(*AD_Y), 'pin03': a}


def zemin(olc):
    yy, xx = np.mgrid[0:PH, 0:PW]
    r = np.sqrt(((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2)
    out = np.stack([np.interp(r, olc['kut'], olc['prof'][:, c]) for c in range(3)], -1)
    rng = np.random.default_rng(3)
    out += rng.uniform(-0.5, 0.5, out.shape) + rng.uniform(-0.5, 0.5, out.shape)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGB')


def boya(maske, deg):
    """maske (L, 0-255) -> RGBA; renk = olculen dikey degrade (ust -> alt)."""
    m = np.asarray(maske).astype(float) / 255
    ys = np.where(m.max(1) > 0.2)[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, m.shape[0] - 1)
    t = np.clip((np.arange(m.shape[0]) - y0) / max(1, y1 - y0), 0, 1)
    idx = np.linspace(0, 1, len(deg))
    col = np.stack([np.interp(t, idx, deg[:, c]) for c in range(3)], -1)
    rgb = np.repeat(col[:, None, :], m.shape[1], 1)
    return Image.fromarray(np.dstack([rgb, m * 255]).clip(0, 255).astype(np.uint8), 'RGBA')


def kart_glifleri(kart):
    a = np.asarray(Image.open(kart).convert('L')).astype(float)[395:600]
    d = a < 120
    cols = np.where(d.any(0))[0]
    bos = [(cols[i], cols[i + 1]) for i in range(len(cols) - 1) if cols[i + 1] - cols[i] > 40]
    if len(bos) != 1:
        raise SystemExit(f'DUR: kartta iki glif ayrilamadi {bos}')
    out = []
    for x0, x1 in ((cols.min(), bos[0][0]), (bos[0][1], cols.max())):
        sub = a[:, x0:x1 + 1]; yy = np.where((sub < 120).any(1))[0]
        sub = sub[yy.min():yy.max() + 1]
        alfa = np.clip((240 - sub) / (240 - 23), 0, 1)          # zemin 240, cizgi ~23 (olculdu)
        out.append(Image.fromarray((alfa * 255).astype(np.uint8), 'L'))
    return out


def ad_maske(t, h_buyuk):
    for s in range(120, 20, -1):
        f = ImageFont.truetype(FONT, s)
        b = f.getbbox('H')
        if b[3] - b[1] <= h_buyuk:
            break
    w = f.getbbox(t)
    im = Image.new('L', (w[2] - w[0] + 20, int(s * 1.4)), 0)
    ImageDraw.Draw(im).text((10 - w[0], int(s * 0.2)), t, font=f, fill=255)
    bb = im.getbbox()
    return im.crop(bb), s


def panel(poster, A, B, kart, olc, buyut=False):
    cv = zemin(olc).convert('RGBA')
    bilgi = {}

    def put(im, cx, cy, golge=False):
        lib.paste(cv, im, cx, cy, shadow=golge)
    P = PU.PosterR(poster)
    ham = P.layer(P.merged, only_label=False)
    ol = min(SEMBOL_KUTU[0] / ham.size[0], SEMBOL_KUTU[1] / ham.size[1]) * (1.3 if buyut else 1.0)
    m = ham.resize((round(ham.size[0] * ol), round(ham.size[1] * ol)), Image.LANCZOS)
    bilgi['sembol_kaynak'] = list(ham.size); bilgi['sembol_cikti'] = list(m.size)
    put(m, PW / 2, (SEMBOL_Y[0] + SEMBOL_Y[1]) / 2, golge=True)
    ga, gb = kart_glifleri(kart)
    yb = (GLIF_Y[0] + GLIF_Y[1]) / 2
    for g_, cx in ((ga, GLIF_CX[0]), (gb, GLIF_CX[1])):
        k = g_.resize((max(1, round(g_.size[0] * GLIF_H / g_.size[1])), GLIF_H), Image.LANCZOS)
        put(boya(k, olc['glif']), cx, yb)
    logo = Image.open(LOGO).convert('RGBA')
    put(lib.scale_h(logo, round(GLIF_H * 0.55)), PW / 2, yb)
    ya = (AD_Y[0] + AD_Y[1]) / 2
    # ad glif merkezine ortali; panel payini asarsa iceri kaydirilir (Serdar 25 Kas: 18 ciftte kaydirma uygun); sigmazsa sigan en buyuk
    # boy (Serdar 25 Kas A: 6 ciftte 45 px kapisina istisna, BUYUK HARF)
    h = AD_H
    while True:
        ma, sa_ = ad_maske(A.upper(), h); mb, sb_ = ad_maske(B.upper(), h)
        xa = min(max(GLIF_CX[0], PAY + ma.size[0] / 2), PW - PAY - ma.size[0] / 2)
        xb = max(min(GLIF_CX[1], PW - PAY - mb.size[0] / 2), PAY + mb.size[0] / 2)
        eksik = 40 - ((xb - mb.size[0] / 2) - (xa + ma.size[0] / 2))
        if eksik > 0:          # adlar disari (sol ada sola, sag ada saga) payi gecmeden, esit paylasarak kayar
            la = max(0.0, xa - (PAY + ma.size[0] / 2)); rb = max(0.0, (PW - PAY - mb.size[0] / 2) - xb)
            da = min(la, max(eksik / 2, eksik - rb)); db = min(rb, eksik - da)
            xa -= da; xb += db
        if (xb - mb.size[0] / 2) - (xa + ma.size[0] / 2) >= 40 and xa - ma.size[0] / 2 >= PAY and xb + mb.size[0] / 2 <= PW - PAY:
            break
        h -= 1
        if h < 20:
            raise SystemExit('DUR: ad 20 px altinda bile sigmiyor')
    bilgi['ad_buyuk_harf_px'] = h; bilgi['ad_punto'] = sa_; bilgi['ad_x'] = [round(xa, 1), round(xb, 1)]
    bilgi['cift'] = f'{A.upper()}_{B.upper()}'
    put(boya(ma, olc['ad']), xa, ya); put(boya(mb, olc['ad']), xb, ya)
    return cv.convert('RGB'), bilgi


def uret(poster, A, B, cerceve, baslik, kart, buyut=False):
    olc = olc_pin03(cerceve)
    im = Image.open(cerceve).convert('RGB').copy()
    im.paste(Image.open(baslik).convert('RGB').crop((0, 0, 1000, BASLIK_Y1)), (0, 0))
    pn, bilgi = panel(poster, A, B, kart, olc, buyut)
    im.paste(pn, (PX0, PY0))
    return im, bilgi, olc


def kutular(p):
    """cikti panelinden oge kutulari: sembol, glif satiri, ad satiri (altin maske, bantlara gore)."""
    g = altin_maske(p)
    R = {}
    for ad, (y0, y1) in (('sembol', (0, 830)), ('glif_satiri', (830, 935)), ('ad_satiri', (935, PH))):
        ys, xs = np.where(g[y0:y1])
        R[ad] = (int(xs.min()), int(ys.min()) + y0, int(xs.max()), int(ys.max()) + y0) if len(xs) else None
    return R


def qc(yol, bilgi, olc, cerceve, baslik):
    S = []
    k = lambda ad, ok, d='': S.append({'kapi': ad, 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': d})
    im = Image.open(yol).convert('RGB'); a = np.asarray(im).astype(int)
    fr = np.asarray(Image.open(cerceve).convert('RGB')).astype(int); bs = np.asarray(Image.open(baslik).convert('RGB')).astype(int)
    k('boyut 1000x1500', im.size == (1000, 1500), str(im.size))
    m = np.ones(a.shape[:2], bool); m[:BASLIK_Y1] = False; m[PY0:PY1, PX0:PX1] = False
    # JPEG yeniden kodlama gurultusu (25 Kas olcum p99.9 = 4); esik 8 (eski78_gorsel_uret kutu disi p99.9 <= 12 kurali alti)
    f1 = int(np.percentile(np.abs(a - fr)[m], 99.9)); f2 = int(np.percentile(np.abs(a[:BASLIK_Y1] - bs[:BASLIK_Y1]), 99.9))
    k('panel disi PIN_03 v6 ile fark p99.9 <= 8 (JPEG)', f1 <= 8, f'p99.9 {f1}')
    k('baslik bandi kaynak v6 ile fark p99.9 <= 8 (JPEG)', f2 <= 8, f'p99.9 {f2}')
    p = a[PY0:PY1, PX0:PX1]; p3 = olc['pin03'].astype(int)
    _, pr1 = profil(p.astype(float)); fz = int(np.abs(pr1 - olc['prof']).max())
    k('panel zemini (radyal profil, altin ve hale disi) PIN_03 ile kanal farki <= 8', fz <= 8, f'max {fz}')
    for ad, (y0, y1) in (('glif satiri', GLIF_Y), ('ad satiri', AD_Y)):
        c1 = p[y0:y1 + 1][altin_maske(p[y0:y1 + 1])].mean(0); c3 = p3[y0:y1 + 1][altin_maske(p3[y0:y1 + 1])].mean(0)
        k(f'{ad} altin rengi PIN_03 ile kanal farki <= 15', np.abs(c1 - c3).max() <= 15, f'{c1.round()} / {c3.round()}')
    if bilgi.get('cift') in AD_ISTISNA:
        k('ad buyuk harf >= 36 px (Serdar 25 Kas A istisnasi: sigan en buyuk boy)', bilgi['ad_buyuk_harf_px'] >= 36, bilgi['ad_buyuk_harf_px'])
    else:
        k('ad buyuk harf >= 45 px (168 akista >= 11 CSS px)', bilgi['ad_buyuk_harf_px'] >= 45, bilgi['ad_buyuk_harf_px'])
    ol = bilgi['sembol_cikti'][0] / bilgi['sembol_kaynak'][0]
    k('sembol yalniz kucultme (cikti / kaynak <= 1)', ol <= 1.0, round(ol, 4))
    R = kutular(p)
    s_ = R['sembol']
    k('sembol yakin cekim (>= 0.9 x PIN_03 kutusu)', s_ is not None and ((s_[3] - s_[1] + 1) >= 0.9 * SEMBOL_KUTU[1] or (s_[2] - s_[0] + 1) >= 0.9 * SEMBOL_KUTU[0]), str(s_))
    ic = all(r_ and r_[0] >= PAY and r_[1] >= PAY and r_[2] <= PW - PAY and r_[3] <= PH - PAY for r_ in R.values())
    k('ogeler panel icinde >= 24 px pay', ic, json.dumps(R))
    bo = (R['glif_satiri'][1] - R['sembol'][3], R['ad_satiri'][1] - R['glif_satiri'][3]) if all(R.values()) else (0, 0)
    k('satirlar arasi bosluk >= 12 px', min(bo) >= BOSLUK, str(bo))
    return S


def main():
    ap = argparse.ArgumentParser()
    for x in ('poster', 'a', 'b', 'cerceve', 'baslik', 'kart'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--out'); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    out = g.out or tempfile.mkdtemp(); os.makedirs(out, exist_ok=True)
    im, bilgi, olc = uret(g.poster, g.a, g.b, g.cerceve, g.baslik, g.kart)
    yol = os.path.join(out, f'PIN_ALTIN_{g.a.upper()}_{g.b.upper()}.jpg')
    im.save(yol, quality=95, subsampling=0)
    S = qc(yol, bilgi, olc, g.cerceve, g.baslik)
    if g.oz_test:
        t = tempfile.mkdtemp(); sonuc = [('bilinen PASS', all(s['sonuc'] == 'PASS' for s in S))]
        # FAIL 1: 1. surumun zemini (kapak_v1 navy_glow: koseler siyaha yakin)
        b1 = im.copy(); z = np.asarray(b1).copy().astype(float)
        yy, xx = np.mgrid[0:PH, 0:PW]; rr = np.sqrt(((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2)
        kar = (1 - np.clip(rr - 0.6, 0, 1))[..., None]                    # kapak_v1 gibi koselere dogru kararan zemin
        z[PY0:PY1, PX0:PX1] = z[PY0:PY1, PX0:PX1] * kar; z = z.astype(np.uint8)
        Image.fromarray(z).save(os.path.join(t, 'b1.jpg'), quality=95, subsampling=0)
        sonuc.append(('FAIL: kapak zemini', any(s['sonuc'] == 'FAIL' and 'zemini' in s['kapi'] for s in qc(os.path.join(t, 'b1.jpg'), bilgi, olc, g.cerceve, g.baslik))))
        # FAIL 2: sembol buyutme (gercek uretim yolu, olcek x1.3)
        im2, bi2, _ = uret(g.poster, g.a, g.b, g.cerceve, g.baslik, g.kart, buyut=True)
        im2.save(os.path.join(t, 'b2.jpg'), quality=95, subsampling=0)
        sonuc.append(('FAIL: buyutme', any(s['sonuc'] == 'FAIL' for s in qc(os.path.join(t, 'b2.jpg'), bi2, olc, g.cerceve, g.baslik))))
        # FAIL 3: istisna listesinde olmayan cok uzun adlar -> ad < 45 px -> kapi FAIL
        im3, bi3, _ = uret(g.poster, 'Sagittariuss', 'Capricornn', g.cerceve, g.baslik, g.kart)
        im3.save(os.path.join(t, 'b3.jpg'), quality=95, subsampling=0)
        sonuc.append((f"FAIL: istisna disi uzun ad ({bi3['ad_buyuk_harf_px']} px)",
                      any(s['sonuc'] == 'FAIL' and 'ad buyuk' in s['kapi'] for s in qc(os.path.join(t, 'b3.jpg'), bi3, olc, g.cerceve, g.baslik))))
        # PASS 2: istisna cifti (SAGITTARIUS_SAGITTARIUS) 36 px ile ad kapisindan gecer
        im5, bi5, _ = uret(g.poster, 'Sagittarius', 'Sagittarius', g.cerceve, g.baslik, g.kart)
        im5.save(os.path.join(t, 'b5.jpg'), quality=95, subsampling=0)
        sonuc.append((f"istisna cifti ad kapisi PASS ({bi5['ad_buyuk_harf_px']} px)",
                      all(s['sonuc'] == 'PASS' for s in qc(os.path.join(t, 'b5.jpg'), bi5, olc, g.cerceve, g.baslik) if 'ad buyuk' in s['kapi'])))
        # FAIL 4: cerceve bozulmasi
        b4 = im.copy(); b4.paste((0, 0, 0), (20, 1400, 60, 1440)); b4.save(os.path.join(t, 'b4.jpg'), quality=95, subsampling=0)
        sonuc.append(('FAIL: cerceve', any(s['sonuc'] == 'FAIL' for s in qc(os.path.join(t, 'b4.jpg'), bilgi, olc, g.cerceve, g.baslik))))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    for s in S:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}")
    json.dump({'kapilar': S, 'bilgi': bilgi}, open(os.path.join(out, 'QC_ALTIN_PIN.json'), 'w'), indent=1, default=str)
    sys.exit(0 if all(s['sonuc'] == 'PASS' for s in S) else 1)


if __name__ == '__main__':
    main()
