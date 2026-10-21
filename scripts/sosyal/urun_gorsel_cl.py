#!/usr/bin/env python3
"""URUN GORSELI, yalniz CANCER_LIBRA (Serdar onayi 21 Eki 2026): arka plan, sahne, yazi YOK; saydam PNG. Etsy yazma yok.
Urun pikselleri kaynakla birebir (kopya; olcek 1, yapay zeka yok).
  kupa : kupa-orchard tek on/arka sahnelerine onayli kodla giydirilmis 8 stil (kapak_canva3.py ciktisi, 2048) ->
         KUPA_<STIL>_ON.png / KUPA_<STIL>_ARKA.png. Govde maskesi sahne geometrisinden (geo_tek_on/arka.json: govde
         x0, x1, ust/alt elips merkezi, elips yari yukseklikleri), kulp: satir basina zemin modeli (kupasiz sutunlardan
         ikinci derece uyum) ile fark; kenar alfasi farktan yumusak. Kupanin kendi golgesi/parlamasi kalir; masa/duvar ve
         masaya dusen golge saydam. Tuval sahnenin kendisi (2048x2048), kupa kendi cozunurlugunde.
  duz  : poster / yil donumu baski JPG'si -> PNG (duz dikdortgen, kirpma yok, tam opak).
  paket: KONTAK.jpg (gri dama zemin, etiketli), URUN_GORSEL_CL.zip, LISTE.txt.
Kullanim: urun_gorsel_cl.py kupa KUPA_DIR GEO_ON GEO_ARKA CIKTI | duz GIRDI.jpg CIKTI.png URUN STIL | paket CIKTI"""
import json, os, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

STIL = [('orange', 'ORANGE_BLOSSOM'), ('fig', 'PURPLE_FIG'), ('olive', 'OLIVE_BREEZE'), ('pomegranate', 'POMEGRANATE_BLOOM'),
        ('almond', 'ALMOND_BLOSSOM'), ('lemon', 'LEMON_GROVE'), ('grape', 'BLUE_GRAPE'), ('loquat', 'GOLDEN_LOQUAT')]   # cift.py ST8
ESIK, BANT = 14.0, 3          # kulp farki (RGB max, 8 bit); kenar bandi (px)
ESIK_ON = 8.0                 # on yuz kulp esigi (aynalanmis kulp bolgesi icinde)
# kulp bolgesi: dikeyde kulbun beyaz pikselleri +-25 px (21 Eki deneme 1: masaya dusen kulp golgesi maskeye girmisti)


def govde_maske(g, H, W, x4=4):
    xl, xr, yt, yb, et, eb = g
    cx, rx = (xl + xr) / 2, (xr - xl) / 2
    t = Image.new('L', (W * x4, H * x4), 0); d = ImageDraw.Draw(t)
    d.ellipse(((cx - rx) * x4, (yt - et) * x4, (cx + rx) * x4, (yt + et) * x4), fill=255)
    d.rectangle(((cx - rx) * x4, yt * x4, (cx + rx) * x4, yb * x4), fill=255)
    d.ellipse(((cx - rx) * x4, (yb - eb) * x4, (cx + rx) * x4, (yb + eb) * x4), fill=255)
    return np.asarray(t.resize((W, H), Image.BOX)).astype(float) / 255


def zemin_modeli(a, bilinen):
    """satir basina x'e gore ikinci derece uyum (yalniz kupasiz sutunlar)."""
    H, W, _ = a.shape
    x = np.arange(W, dtype=float); xs = x[bilinen]
    A = np.stack([xs ** 2, xs, np.ones_like(xs)], 1)
    P = np.linalg.pinv(A)                                  # (3, n)
    B = np.zeros_like(a)
    X = np.stack([x ** 2, x, np.ones_like(x)], 1)          # (W, 3)
    for c in range(3):
        coef = P @ a[:, bilinen, c].T                       # (3, H)
        B[..., c] = (X @ coef).T
    return B


def kupa_kes(a, g, taraf, kulp_bolge=None, esik=ESIK):
    H, W, _ = a.shape
    xl, xr, yt, yb, et, eb = g
    gm = govde_maske(g, H, W)
    bilinen = np.zeros(W, bool)
    if taraf == 'sol':      # kulp solda (on yuz)
        bilinen[:40] = True; bilinen[int(xr) + 40:] = True
        kx0, kx1 = 40, int(xl) + 2
    else:                   # kulp sagda (arka yuz)
        bilinen[:int(xl) - 40] = True; bilinen[W - 40:] = True
        kx0, kx1 = int(xr) - 2, W - 40
    B = zemin_modeli(a, bilinen)
    fark = np.abs(a - B).max(2)
    # kulp dikey sinirlari kulbun beyaz piksellerinden (govdeye 60 px'ten uzak sutunlar); masaya dusen golge beyaz degil
    w = (a.min(2) > 200) & (a.max(2) - a.min(2) < 14)
    cx0, cx1 = (kx0, kx1 - 60) if taraf == 'sol' else (kx0 + 60, kx1)
    ys = np.where(w[:, cx0:cx1].sum(1) > 3)[0]
    ky0, ky1 = int(ys.min()) - 25, int(ys.max()) + 25
    km = np.zeros((H, W), bool); km[ky0:ky1, kx0:kx1] = fark[ky0:ky1, kx0:kx1] > esik
    if kulp_bolge is not None:                              # on yuz: arka yuzun temiz kulp siniri aynalanmis (deneme 3)
        km &= kulp_bolge
    km = ndimage.binary_opening(km, iterations=2)
    km = ndimage.binary_closing(km, iterations=2)
    sert = (gm > 0.5) | km
    lab, n = ndimage.label(sert)
    if n > 1:                                              # govdeye bagli bilesen
        bil = np.bincount(lab.ravel()); bil[0] = 0; sert = lab == bil.argmax()
    # alfa: ic = 1; kenar bandinda farktan yumusak (govde kenari geometri ile fark kesisimi)
    ic = ndimage.binary_erosion(sert, iterations=BANT)
    dis = ndimage.binary_dilation(sert, iterations=BANT)
    bant = dis & ~ic
    yum = np.clip((fark - 4) / (esik + 6 - 4), 0, 1)
    alfa = np.where(ic, 1.0, np.where(bant, yum, 0.0))
    # govdenin alt kenari: masaya dusen golge farki yuksek; alt elips disinda alfa sifir
    alt = np.zeros((H, W), bool); alt[int(yb):, :] = True
    alfa = np.where(alt & (gm < 0.5), 0.0, alfa)
    alfa = np.where(alt & (gm >= 0.5), np.maximum(alfa, gm), alfa)
    return alfa, sert, fark, B


def kupa(kdir, geo_on, geo_arka, out):
    os.makedirs(out, exist_ok=True)
    g_on = json.load(open(geo_on))['sol']; g_ar = json.load(open(geo_arka))['sag']
    # on yuz kulp bolgesi: arka yuzde (orange, kulp ayni sahne pikselleri) temiz cikan kulp maskesi dikey eksende aynalanir
    # (iki sahnede govde merkezi x 1024; esitle.py ayna konum), 15 px genisletilir; icinde esik 8 (kulp duvarla ayni tonda)
    ar = np.asarray(Image.open(os.path.join(kdir, 'orange_tek_arka.jpg')).convert('RGB')).astype(float)
    _, sert_ar, _, _ = kupa_kes(ar, g_ar, 'sag')
    kulp_ar = sert_ar & (govde_maske(g_ar, *sert_ar.shape) < 0.5); kulp_ar[:, :int(g_ar[1]) - 2] = False
    kulp_on = ndimage.binary_dilation(kulp_ar[:, ::-1], iterations=15)
    sat = []
    for kisa, ad in STIL:
        for yuz, g, taraf, dos in (('ON', g_on, 'sol', f'{kisa}_tek_on.jpg'), ('ARKA', g_ar, 'sag', f'{kisa}_tek_arka.jpg')):
            a = np.asarray(Image.open(os.path.join(kdir, dos)).convert('RGB')).astype(float)
            alfa, sert, fark, B = kupa_kes(a, g, taraf, kulp_on if yuz == 'ON' else None, ESIK_ON if yuz == 'ON' else ESIK)
            rgba = np.dstack([a, alfa * 255]).round().clip(0, 255).astype(np.uint8)
            yol = os.path.join(out, f'KUPA_{ad}_{yuz}.png')
            Image.fromarray(rgba, 'RGBA').save(yol, optimize=True)
            ys, xs = np.where(alfa > 0)
            kut = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            tam = alfa >= 0.999
            esit = int((np.abs(rgba[..., :3].astype(float) - a)[tam].max()) == 0)
            dis_alfa = float(alfa[~ndimage.binary_dilation(sert, iterations=BANT + 1)].max()) if (~sert).any() else 0
            sat.append(dict(dosya=os.path.basename(yol), urun='kupa', stil=ad, yuz=yuz, olcu='2048x2048',
                            urun_kutusu=f'{kut[2] - kut[0]}x{kut[3] - kut[1]} @ {kut[0]},{kut[1]}',
                            piksel_birebir=bool(esit), dis_alfa_max=round(dis_alfa, 3), opak_px=int(tam.sum())))
            print(sat[-1], flush=True)
    json.dump(sat, open(os.path.join(out, 'KUPA_OLCUM.json'), 'w'), indent=1)


def duz(gir, cik, urun, stil):
    im = Image.open(gir).convert('RGB')
    a = np.dstack([np.asarray(im), np.full(im.size[::-1], 255, np.uint8)])
    Image.fromarray(a, 'RGBA').save(cik, optimize=True)
    geri = np.asarray(Image.open(cik).convert('RGB'))
    print(json.dumps(dict(dosya=os.path.basename(cik), urun=urun, stil=stil, olcu=f'{im.size[0]}x{im.size[1]}',
                          piksel_birebir=bool((geri == np.asarray(im)).all()))))


def dama(w, h, k=24):
    y, x = np.mgrid[0:h, 0:w]
    v = np.where(((x // k) + (y // k)) % 2 == 0, 200, 230).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v]))


def paket(out):
    pngs = sorted(f for f in os.listdir(out) if f.endswith('.png'))
    sira = [f for p in ('POSTER_', 'YD_', 'KUPA_') for f in pngs if f.startswith(p)]
    try:
        ft = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
    except OSError:
        ft = ImageFont.load_default()
    tw, th, lab, gap, sut = 300, 360, 26, 14, 6
    sat_ = (len(sira) + sut - 1) // sut
    c = Image.new('RGB', (gap + sut * (tw + gap), gap + sat_ * (th + lab + gap)), 'white'); d = ImageDraw.Draw(c)
    liste = ['dosya\turun\tstil\tpiksel']
    for i, f in enumerate(sira):
        im = Image.open(os.path.join(out, f)).convert('RGBA')
        x, y = gap + (i % sut) * (tw + gap), gap + (i // sut) * (th + lab + gap)
        z = dama(tw, th); t = im.copy(); t.thumbnail((tw, th), Image.LANCZOS)
        z.paste(t, ((tw - t.size[0]) // 2, (th - t.size[1]) // 2), t)
        c.paste(z, (x, y))
        et = f[:-4]
        d.text((x + (tw - d.textlength(et, font=ft)) / 2 if d.textlength(et, font=ft) < tw else x, y + th + 5), et, font=ft, fill=(0, 0, 0))
        urun = {'POSTER': 'poster 8x10', 'YD': 'yil donumu 8x10', 'KUPA': 'kupa 11 oz'}[f.split('_')[0]]
        stil = f[:-4].split('_', 1)[1]
        liste.append(f'{f}\t{urun}\t{stil}\t{im.size[0]}x{im.size[1]}')
    c.save(os.path.join(out, 'KONTAK.jpg'), quality=90)
    with zipfile.ZipFile(os.path.join(out, 'URUN_GORSEL_CL.zip'), 'w', zipfile.ZIP_STORED) as z:
        for f in sira:
            z.write(os.path.join(out, f), f)
    open(os.path.join(out, 'LISTE.txt'), 'w', encoding='utf-8').write('\n'.join(liste) + f'\nToplam {len(sira)} PNG\n')
    print('\n'.join(liste), f'\nToplam {len(sira)} PNG')


if __name__ == '__main__':
    k = sys.argv[1]
    if k == 'kupa':
        kupa(*sys.argv[2:6])
    elif k == 'duz':
        duz(*sys.argv[2:6])
    elif k == 'paket':
        paket(sys.argv[2])
    else:
        raise SystemExit(__doc__)
