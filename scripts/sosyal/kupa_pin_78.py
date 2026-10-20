#!/usr/bin/env python3
"""Kupa pini x78, S3 kurali (Serdar onayi 20 Eki 2026; kupa_pin_secenek.py e94127d8 S3 yolu). Yayinlama yok.
Her cift kendi V4 kapagindan (KUPA_KAPAK_78_20261019/KAPAK/<lid>_<B1>_<B2>.jpg): stil 8 sahneden yan susleme bolgesiyle
(kupa_kapak_78.stil_bul), eski baslik stilin yazisiz sahnesiyle silinir, ust duvar yansitmali uzatilir, masa +62 satir,
baslik (Cinzel 650, stil rengi, S3 boyu; pin genisligine 40 px payla sigmazsa yalniz o cift en az oranda kuculur) ust kenar
ile kupa arasina esit boslukla yazilir. Kupa ve plaka kapak pikselleri, olcek 2048 -> 1000 (0.48828 <= 1). Yapay zeka yok.
Kapilar (cift basina): sahne = kapak duvari (ort <= 3); baslik cizimi eski yerinde = kapak basligi (NCC >= 0.99, dikey +-4 px arama; sira/renk/
stil/olcek dogrulamasi); eski baslik kalintisi 0; kupa NCC >= 0.99; plaka NCC >= 0.99; baslik guvenli alanda (>= 40 px);
bosluk esit (fark <= 3 px); ek yeri sicramasi yok (kivrim satiri adimi <= max(0.5, 4 x duvar medyani)); uzatmada duvar disi
piksel 0 (kupa/kulp kopyasi yok); ayni burclu ciftte iki glif birbirine (NCC >= 0.60; kupa egimi: 78 kosusunda ayni 0.70-0.95, farkli 0.08-0.13)
ve sablona (>= 0.60; yerel olcum dogru glif 0.70-0.81, farkli glif
0.08-0.13) esit.
Cikti: PIN/PIN_KUPA_<B1>_<B2>.jpg, KONTAK_1..n.jpg (16'li, cift etiketli), KONTROL.csv, OZET.txt
Kullanim: kupa_pin_78.py --kapak DIR --sahne DIR --font Cinzel.ttf --sembol DIR --cikti DIR [--is 4] [--ciftler A_B ...]"""
import argparse, csv, importlib.util, os, re, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('kpo', os.path.join(D, 'kupa_pin_ornek.py'))
kpo = importlib.util.module_from_spec(sp); sp.loader.exec_module(kpo)
yaz, baslik_ciz, kutu, tri, ncc = kpo.yaz, kpo.baslik_ciz, kpo.kutu, kpo.tri, kpo.ncc

W, H, S = 1000, 1250, 2048
s = W / S
RENKLER = kpo.RENKLER
UST_BANT, MASA_KES, MASA_H = kpo.UST_BANT, kpo.MASA_KES, kpo.MASA_H
KUPA_UST, KUPA_ALT = kpo.KUPA_UST, kpo.KUPA_ALT
PLAKA = (288, 1699, 1760, 1827)           # V4 alt yazi zemini (kupa_pin_secenek)
GUVENLI_KAPAK = 1803 - 245                # kupa_kapak_78.GUVENLI_X genisligi (kapak basligi olcek_bul)
PAY = 40
GLIF = ((550, 1290, 640, 1365), (735, 1290, 825, 1365))   # on kupa iki kucuk burc isareti (CL olcumu, yerlesim sabit)
G = {}


def olcek(font, b1, b2, sinir):
    K = S / 1254
    gen = lambda o: max(yaz(font, t, 104 * K * o).shape[1] for t in (b1.upper(), b2.upper()))  # noqa: E731
    w = gen(1.0)
    if w <= sinir:
        return 1.0, w
    o = sinir / w
    while gen(o) > sinir:
        o -= 0.002
    return round(o, 4), gen(o)


def stil_bul(a0):
    f = a0[::4, ::4].astype(np.int16); m = np.zeros(f.shape[:2], bool); m[175:275, :75] = True; m[175:275, 437:] = True
    d = {st: float(np.abs(f - sc[::4, ::4]).max(2)[m].mean()) for st, sc in G['sahne'].items()}
    st = min(d, key=d.get)
    return st, d


def glif_maske(a, b):
    g = 1 - a[b[1]:b[3], b[0]:b[2]].astype(float).mean(2) / 255
    g = np.clip((g - 0.12) / 0.5, 0, 1)
    ys, xs = np.where(g > 0.3)
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def benzer(x, y):
    yi = np.asarray(Image.fromarray((y * 255).astype(np.uint8)).resize(x.shape[::-1], Image.LANCZOS)).astype(float) / 255
    return ncc(x, yi)


def init(sahne_dir, font, sembol):
    G['sahne'] = {st: np.asarray(Image.open(os.path.join(sahne_dir, f'{st}_k40.png')).convert('RGB')).astype(np.int16) for st in RENKLER}
    G['font'], G['sembol'] = font, sembol


def is_(r):
    t0 = time.time()
    b1, b2, out = r['b1'], r['b2'], r['out']
    font = G['font']
    a0 = np.asarray(Image.open(r['kapak']).convert('RGB')); f = a0.astype(float)
    st, dst = stil_bul(a0); renk = RENKLER[st]; sc = G['sahne'][st].astype(float)
    k = {'cift': f'{b1}_{b2}', 'listing_id': r['lid'], 'stil': st, 'stil_fark': round(dst[st], 2),
         'stil_ikinci': round(sorted(dst.values())[1], 2)}
    fail = []

    def kapi(ad, ok):
        if not ok:
            fail.append(ad)
    # eski baslik + sahne
    koyu = np.abs(f - np.array(renk)).max(2) < 40; koyu[int(0.4 * S):] = False
    bk = kutu(koyu)
    dm = np.zeros(koyu.shape, bool); dm[:KUPA_UST - 30] = True
    dm[max(bk[1] - 40, 0):bk[3] + 40, max(bk[0] - 40, 0):bk[2] + 40] = False
    dd = np.abs(f - sc).max(2)[dm]
    k['sahne_fark_ort'] = round(float(dd.mean()), 2); kapi('sahne', dd.mean() <= 3)
    ok_, _ = olcek(font, b1, b2, GUVENLI_KAPAK)
    n0, dy0 = -1.0, 0
    for dy in range(-4, 5):            # kutu ustu esikle 1-2 px asagida olculebilir (yuvarlak harf tasmasi; LEO_VIRGO dy -1)
        t = sc.copy(); bt, _ = baslik_ciz(t, font, b1, b2, renk, y_ust=bk[1] + dy, olcek=ok_)
        x0, y0, x1, y1 = bt
        v = ncc(f[y0:y1, x0:x1].mean(2), t[y0:y1, x0:x1].mean(2))
        if v > n0:
            n0, dy0 = v, dy
    k['kapak_baslik_olcek'] = ok_; k['baslik_dogrulama_ncc'] = round(n0, 4); k['baslik_dogrulama_dy'] = dy0
    kapi('baslik_dogrulama', n0 >= 0.99)
    e = f.copy()
    ex0, ey0, ex1, ey1 = bk[0] - 12, bk[1] - 12, bk[2] + 12, bk[3] + 12
    e[ey0:ey1, ex0:ex1] = sc[ey0:ey1, ex0:ex1]
    kal = int((np.abs(e - np.array(renk)).max(2) < 60)[:KUPA_UST - 30].sum()); k['kalinti'] = kal; kapi('kalinti', kal == 0)
    # uzatma (S3)
    hedef = round(H / s); alt = 2 * MASA_H; ust = hedef - S - alt
    ustb = e[:UST_BANT]
    us = np.stack([ustb[tri(j, UST_BANT)] for j in range(ust)])[::-1]
    band = e[MASA_KES - MASA_H:MASA_KES]
    al = np.stack([band[MASA_H - 1 - tri(j, MASA_H)] for j in range(alt)])
    big = np.concatenate([us, e[:MASA_KES], al, e[MASA_KES:]])
    off = ust * s
    # baslik olcegi (pin): 40 px payla
    op, gw = olcek(font, b1, b2, (W - 2 * PAY) / s - 2)
    k['pin_baslik_olcek'] = op
    tt = np.zeros((900, S, 3)); bn, _ = baslik_ciz(tt, font, b1, b2, renk, y_ust=0, olcek=op); bh = (bn[3] - bn[1]) * s
    P0 = np.asarray(Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(float)
    nt = (P0.min(2) > 150) & (P0.max(2) - P0.min(2) < 10)
    gv = nt[:, round(327 * s):round(1726 * s)].mean(1)
    yk = round(KUPA_UST * s + off) - 60
    kt = int(np.where(gv[yk:] > 0.3)[0].min()) + yk
    g = (kt - bh) / 2
    baslik_ciz(big, font, b1, b2, renk, y_ust=round(g / s), olcek=op)
    pin = Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    P = np.asarray(pin).astype(float)
    K = np.asarray(Image.fromarray(a0).resize((W, W), Image.LANCZOS)).astype(float)
    for ad, (k0, k1) in {'kupa': (KUPA_UST, KUPA_ALT), 'plaka': (PLAKA[1], PLAKA[3])}.items():
        q0, q1 = round(k0 * s), round(k1 * s)
        v = ncc(P[round(q0 + off):round(q1 + off)], K[q0:q1]); k[f'{ad}_ncc'] = round(v, 5); kapi(ad, v >= 0.99)
    m = P[:kt - 10].mean(2) < 90; ys, xs = np.where(m)
    bx0, by0, bx1, by1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    k.update(baslik_x=f'{bx0}-{bx1}', baslik_y=f'{by0}-{by1}', bosluk_ust=by0, bosluk_alt=kt - by1, kupa_ust=kt)
    kapi('baslik_guvenli', bx0 >= PAY and bx1 <= W - 1 - PAY and by0 >= PAY)
    kapi('bosluk_esit', abs(by0 - (kt - by1)) <= 3)
    # ek yeri: kivrim satirlarinda satir ortalamasi adimi (baslik sutunlari disi)
    yu = round(KUPA_UST * s + off) - 30
    gd = np.concatenate([P[:yu, PAY:max(bx0 - 30, PAY + 1)], P[:yu, min(bx1 + 30, W - PAY - 1):W - PAY]], 1).mean(2).mean(1)
    ad_ = np.abs(np.diff(gd)); med = float(np.median(ad_))
    ky = [round((ust - i * UST_BANT) * s) for i in range(ust // UST_BANT + 1) if ust - i * UST_BANT > 0]
    km = max(float(ad_[max(y - 2, 0):y + 2].max()) for y in ky)
    k['ek_adim_max'] = round(km, 3); k['duvar_adim_medyan'] = round(med, 3); kapi('ek_sicrama', km <= max(0.5, 4 * med))
    # uzatma bolgesinde duvar disi piksel (kupa/kulp kopyasi): baslik kutusu disi
    ue = P[:round(off)].copy(); wm = np.median(ue.reshape(-1, 3), 0)
    msk = np.abs(ue - wm).max(2) > 30
    msk[max(by0 - 8, 0):by1 + 8, max(bx0 - 8, 0):bx1 + 8] = False
    k['uzatma_yabanci_px'] = int(msk.sum()); kapi('uzatma_kopya', int(msk.sum()) == 0)
    # glifler
    gl, gr = glif_maske(a0, GLIF[0]), glif_maske(a0, GLIF[1])
    k['glif_lr_ncc'] = round(benzer(gl, gr), 3)
    sem = os.path.join(G['sembol'], '_'.join(sorted([b1, b2])))
    try:
        tl = np.asarray(Image.open(os.path.join(sem, 'sol.png')).convert('RGBA'))[..., 3].astype(float) / 255
        tr = np.asarray(Image.open(os.path.join(sem, 'sag.png')).convert('RGBA'))[..., 3].astype(float) / 255
        def kirp_(x):
            yy, xx = np.where(x > 0.3); return x[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        k['glif_sol_sablon'] = round(benzer(gl, kirp_(tl)), 3); k['glif_sag_sablon'] = round(benzer(gr, kirp_(tr)), 3)
    except (OSError, ValueError):
        k['glif_sol_sablon'] = k['glif_sag_sablon'] = ''
    if b1 == b2:
        kapi('ayni_burc_glif', k['glif_lr_ncc'] >= 0.60 and k['glif_sol_sablon'] != '' and min(k['glif_sol_sablon'], k['glif_sag_sablon']) >= 0.60)
    yol = os.path.join(out, 'PIN', f'PIN_KUPA_{b1}_{b2}.jpg')
    pin.save(yol, quality=92, subsampling=0, optimize=True)
    k['fail'] = ';'.join(fail); k['sonuc'] = 'PASS' if not fail else 'FAIL'; k['sure_sn'] = round(time.time() - t0, 1)
    return k


def kontak(out, satirlar, n=16):
    try:
        ft = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
    except OSError:
        ft = ImageFont.load_default()
    tw, th, lab, gap = 300, 375, 30, 16
    adlar = []
    for p in range(0, len(satirlar), n):
        grup = satirlar[p:p + n]; sut = 4; sat_ = (len(grup) + sut - 1) // sut
        c = Image.new('RGB', (gap + sut * (tw + gap), gap + sat_ * (th + lab + gap)), 'white'); d = ImageDraw.Draw(c)
        for i, r in enumerate(grup):
            x, y = gap + (i % sut) * (tw + gap), gap + (i // sut) * (th + lab + gap)
            c.paste(Image.open(os.path.join(out, 'PIN', f'PIN_KUPA_{r["cift"]}.jpg')).resize((tw, th), Image.LANCZOS), (x, y))
            et = r['cift'] + ('' if r['sonuc'] == 'PASS' else '  FAIL')
            d.text((x + (tw - d.textlength(et, font=ft)) / 2, y + th + 5), et, font=ft, fill=(0, 0, 0) if r['sonuc'] == 'PASS' else (200, 0, 0))
        ad = f'KONTAK_{p // n + 1}.jpg'; c.save(os.path.join(out, ad), quality=88); adlar.append(ad)
    return adlar


def main():
    ap = argparse.ArgumentParser()
    for x in ('--kapak', '--sahne', '--font', '--sembol', '--cikti'):
        ap.add_argument(x, required=True)
    ap.add_argument('--is', dest='isci', type=int, default=4); ap.add_argument('--ciftler', nargs='*', default=[])
    g = ap.parse_args()
    out = os.path.abspath(g.cikti); os.makedirs(os.path.join(out, 'PIN'), exist_ok=True)
    isler = []
    for fn in sorted(os.listdir(g.kapak)):
        m = re.match(r'^(\d+)_([A-Z]+)_([A-Z]+)\.jpg$', fn)
        if not m or (g.ciftler and f'{m.group(2)}_{m.group(3)}' not in g.ciftler):
            continue
        isler.append({'lid': m.group(1), 'b1': m.group(2), 'b2': m.group(3), 'kapak': os.path.join(g.kapak, fn), 'out': out})
    print(f'is {len(isler)}', flush=True)
    t0 = time.time(); sonuc = []
    with ProcessPoolExecutor(g.isci, initializer=init, initargs=(g.sahne, g.font, g.sembol)) as ex:
        for i, r in enumerate(ex.map(is_, isler), 1):
            sonuc.append(r); gc = time.time() - t0
            print(f"[{i}/{len(isler)} %{100 * i // len(isler)}] gecen {gc:.0f}s kalan ~{gc / i * (len(isler) - i):.0f}s  {r['cift']} {r['stil']} "
                  f"kupa {r['kupa_ncc']} plaka {r['plaka_ncc']} olcek {r['pin_baslik_olcek']} bosluk {r['bosluk_ust']}/{r['bosluk_alt']} "
                  f"{r['sonuc']} {r['fail']}", flush=True)
    with open(os.path.join(out, 'KONTROL.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(sonuc[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(sonuc)
    kon = kontak(out, sonuc)
    from collections import Counter
    npass = sum(r['sonuc'] == 'PASS' for r in sonuc)
    kuc = [f"{r['cift']} ({r['pin_baslik_olcek']})" for r in sonuc if r['pin_baslik_olcek'] < 1]
    oz = [f'KUPA PIN x{len(sonuc)} (S3 1000x1250; yayinlama yok, astrolove-media/Metricool yazma 0): {npass} PASS / {len(sonuc) - npass} FAIL',
          f"stil: {dict(Counter(r['stil'] for r in sonuc))}; stil farki max {max(r['stil_fark'] for r in sonuc)}, ikinci en yakin min {min(r['stil_ikinci'] for r in sonuc)}",
          f"kupa NCC min {min(r['kupa_ncc'] for r in sonuc)}, plaka NCC min {min(r['plaka_ncc'] for r in sonuc)}, baslik dogrulama NCC min "
          f"{min(r['baslik_dogrulama_ncc'] for r in sonuc)}; kalinti max {max(r['kalinti'] for r in sonuc)}; sahne farki max {max(r['sahne_fark_ort'] for r in sonuc)}",
          f"bosluk ust {min(r['bosluk_ust'] for r in sonuc)}-{max(r['bosluk_ust'] for r in sonuc)} px, alt {min(r['bosluk_alt'] for r in sonuc)}-"
          f"{max(r['bosluk_alt'] for r in sonuc)} px; ek adimi max {max(r['ek_adim_max'] for r in sonuc)}; uzatma yabanci px max {max(r['uzatma_yabanci_px'] for r in sonuc)}",
          f"pin basligi kuculen ({len(kuc)}): {kuc}; olcek 2048 -> 1000 = {s:.5f} (<=1)",
          f"ayni burclu: {[(r['cift'], r['glif_lr_ncc'], r['glif_sol_sablon']) for r in sonuc if r['cift'].split('_')[0] == r['cift'].split('_')[1]]}",
          f'Kontak: {kon}', f"FAIL: {[(r['cift'], r['fail']) for r in sonuc if r['sonuc'] != 'PASS']}"]
    open(os.path.join(out, 'OZET.txt'), 'w', encoding='utf-8').write('\n'.join(oz) + '\n')
    print('\n'.join(oz))
    raise SystemExit(0 if npass == len(sonuc) else 1)


if __name__ == '__main__':
    main()
