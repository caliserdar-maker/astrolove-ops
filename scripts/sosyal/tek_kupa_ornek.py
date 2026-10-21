#!/usr/bin/env python3
"""TEK KUPA ornegi, yalniz CANCER_LIBRA (Serdar karari 21 Eki 2026). Etsy / Metricool yazma yok, toplu uretim yok.
Kaynak: kupa-orchard tek kupa sahneleri (varlik/gorunum/ORCHARD_OrangeBlossom_sahne_tek_on|arka.png, esitle.py ile
esitlenmis) uzerine onayli kodla giydirilmis CL baskisi (kapak_canva3.py -> tek_on.jpg, tek_arka.jpg, 2048).
Urun pikselleri yalniz kirpilir ve kucultulur (olcek <= 1); duvar/yuzey uzatmasi kenar seritlerinin yansitmasiyla
(kupaya degmeyen serit). Yapay zeka yok.
  KAPAK_TEK.jpg 2048x2048: on yuz kupa, ortali, en buyuk; ustte baslik (V4: Cinzel 650, #0A2818, ust 211+10), altta
    "PERSONALIZED GIFT MUG" plakasi (V4: #E6DBD1, R 40, 102 px, alt 1837-10). 4:5 (x 205-1843), 34:27 (y 211-1837), 1:1.
  GALERI2_ON_ARKA.jpg 2048x2048: on ve arka yan yana, ustlerinde FRONT / BACK; iki sahne genis dogrusal gecisle.
  PIN_TEK.jpg 1000x1250: S3 duzeni (baslik, kupa, plaka; ust kenar-baslik = baslik-kupa), kupa en buyuk (sahne tek
    kucultmeyle pin olceginde; baslik/plaka 2048 olcekte katman olarak cizilip kucultulur).
  ONIZLEME_KIRPIM.jpg: KAPAK_TEK 255x319 | 300x300 | 340x270.
Kontrol: OLCUM.txt (PASS/FAIL) + YAKIN_*.jpg (%200, goz kontrolu).
Kullanim: tek_kupa_ornek.py TEK_ON.jpg TEK_ARKA.jpg FONT.ttf KAPAK_V4.jpg CIKTI_DIR"""
import argparse, importlib.util, os
import numpy as np
from PIL import Image, ImageDraw

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('kpo', os.path.join(D, 'kupa_pin_ornek.py'))
kpo = importlib.util.module_from_spec(sp); sp.loader.exec_module(kpo)
yaz, baslik_ciz, tri, ncc, lum = kpo.yaz, kpo.baslik_ciz, kpo.tri, kpo.ncc, kpo.lum

S = 2048
RENK = (10, 40, 24)                 # #0A2818
ZEMIN = (230, 219, 209)             # #E6DBD1
BOY, ZEMIN_Y, PAD_X, MCU, R = 102, 128, 48, 16, 40      # kupa_alt_yazi_v2/v3
UST, ALT = 211 + 10, 1837 - 10      # V4: 34:27 ust siniri + 10, alt siniri - 10
X45 = (205, 1843)                   # 4:5 kirpim
GUV = (245, 1803)                   # baslik 4:5 guvenli alani (40 px pay)
ARA = 40                            # baslik/plaka ile kupa arasi en az
KENAR = 30                          # serit ile kupa kutusu arasi pay (kaynak px)
PLAKA_KAPAK = (288, 1699, 1760, 1827)
ALT_SERIT = 150                     # kaynak sahnenin son 150 satiri golgesiz yuzey (olcum 21 Eki)


def govde(t):
    nt = (t.min(2) > 200) & (t.max(2) - t.min(2) < 14)
    ys = np.where(nt.mean(1) > 0.15)[0]; xs = np.where(nt[ys.min():ys.max()].mean(0) > 0.3)[0]
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def yerlestir(src, g, k, cx, ust_y, Wc, Hc):
    """src (kaynak sahne) k ile kucultulur; kupa kutusu g'nin ortasi cx'e, ustu ust_y'ye gelir; tuval kenar
    seritlerinin yansitmasiyla doldurulur. Donus: tuval, kaynak 0,0'in tuvaldeki yeri, seritler."""
    assert k <= 1.0
    w = round(S * k)
    a = np.asarray(Image.fromarray(src).resize((w, w), Image.LANCZOS)).astype(float)
    x0 = round(cx - (g[0] + g[2]) / 2 * k); y0 = round(ust_y - g[1] * k)
    sl = round((g[0] - KENAR) * k); sr = round((S - g[2] - KENAR) * k)
    st = round((g[1] - KENAR) * k); sb = round(ALT_SERIT * k)   # alt: yalniz son satirlar (kupa golgesi capraz; yansitmada zikzak)
    # yatay
    sol, sag = x0, Wc - (x0 + w)
    if sol < 0: a = a[:, -sol:]; sol = 0
    if sag < 0: a = a[:, :a.shape[1] + sag]; sag = 0
    L = np.stack([a[:, tri(j, sl)] for j in range(sol)], 1)[:, ::-1] if sol else a[:, :0]
    Rr = np.stack([a[:, a.shape[1] - 1 - tri(j, sr)] for j in range(sag)], 1) if sag else a[:, :0]
    a = np.concatenate([L, a, Rr], 1)
    ust, alt = y0, Hc - (y0 + w)
    if ust < 0: a = a[-ust:]; ust = 0
    if alt < 0: a = a[:a.shape[0] + alt]; alt = 0
    U = np.stack([a[tri(j, st)] for j in range(ust)])[::-1] if ust else a[:0]
    B = np.stack([a[a.shape[0] - 1 - tri(j, sb)] for j in range(alt)]) if alt else a[:0]
    a = np.concatenate([U, a, B])
    assert a.shape[:2] == (Hc, Wc), a.shape
    return a, (x0, y0), dict(sol=sol, sag=sag, ust=ust, alt=alt, serit_sol=sl, serit_sag=sr, serit_ust=st, serit_alt=sb)


def plaka(im, alt_y):
    """V4 alt yazi zemini + metin (kupa_kapak_78 kapak() ile ayni geometri). Donus: kutu."""
    Wi = im.shape[1]
    mk = yaz(FONT, 'PERSONALIZED GIFT MUG', BOY); h, w = mk.shape
    zy1 = alt_y; zy0 = zy1 - ZEMIN_Y
    kk = round((Wi - (w + 2 * PAD_X)) / (2 * MCU)); zx0, zx1 = kk * MCU, Wi - kk * MCU
    x4 = 4
    t = Image.new('L', ((zx1 - zx0) * x4, ZEMIN_Y * x4), 0)
    ImageDraw.Draw(t).rounded_rectangle((0, 0, (zx1 - zx0) * x4 - 1, ZEMIN_Y * x4 - 1), radius=R * x4, fill=255)
    za = np.asarray(t.resize((zx1 - zx0, ZEMIN_Y), Image.BOX)).astype(float) / 255
    sub = im[zy0:zy1, zx0:zx1]
    im[zy0:zy1, zx0:zx1] = sub * (1 - za[..., None]) + np.array(ZEMIN, float) * za[..., None]
    tx0, ty0 = int(round((zx0 + zx1 - w) / 2)), int(round((zy0 + zy1 - h) / 2))
    sub = im[ty0:ty0 + h, tx0:tx0 + w]
    im[ty0:ty0 + h, tx0:tx0 + w] = sub * (1 - mk[..., None]) + np.array(RENK, float) * mk[..., None]
    return (zx0, zy0, zx1, zy1), za


def etiket(im, metin, cx, y_ust, boy=BOY):
    mk = yaz(FONT, metin, boy); h, w = mk.shape
    x0, y0 = int(round(cx - w / 2)), int(round(y_ust))
    sub = im[y0:y0 + h, x0:x0 + w]
    im[y0:y0 + h, x0:x0 + w] = sub * (1 - mk[..., None]) + np.array(RENK, float) * mk[..., None]
    return (x0, y0, x0 + w, y0 + h)


def kupa_ncc(out, src, g, k, xy):
    w = round(S * k)
    ref = np.asarray(Image.fromarray(src).resize((w, w), Image.LANCZOS)).astype(float)
    r0, r1, c0, c1 = round(g[1] * k), round(g[3] * k), round(g[0] * k), round(g[2] * k)
    x, y = xy
    return ncc(out[y + r0:y + r1, x + c0:x + c1], ref[r0:r1, c0:c1]), (x + c0, y + r0, x + c1, y + r1)


def uzatma_kontrol(out, kutular, bolgeler):
    """uzatma bolgelerinde (kenar seritleri) duvar/yuzey disi piksel sayisi (kupa/kulp kopyasi) ve kenar adimi."""
    yab = 0
    for b in bolgeler:                     # her bolge ayri (sol ve sag uzatma ayni satirda farkli aydinlik)
        if b[2] <= b[0] or b[3] <= b[1]:
            continue
        m = np.zeros(out.shape[:2], bool); m[b[1]:b[3], b[0]:b[2]] = True
        for c in kutular:
            m[max(c[1] - 8, 0):c[3] + 8, max(c[0] - 8, 0):c[2] + 8] = False
        for y in np.unique(np.where(m)[0])[::4]:
            row = out[y][m[y]]
            if len(row) > 4:
                yab += int((np.abs(row - np.median(row, 0)).max(1) > 30).sum())
    return yab


def adim(out, x_list, y0, y1):
    """dikey ek cizgilerinde sutun ortalamasi adimi (x_list), duvar medyanina orani."""
    g = out[y0:y1].mean(2).mean(0); d = np.abs(np.diff(g)); med = float(np.median(d))
    return max(float(d[max(x - 2, 0):x + 2].max()) for x in x_list if 0 < x < len(d)), med


def main():
    global FONT
    p = argparse.ArgumentParser()
    for x in ('ton', 'tarka', 'font', 'kapak', 'cikti'):
        p.add_argument(x)
    a = p.parse_args(); FONT = a.font
    os.makedirs(a.cikti, exist_ok=True)
    on = np.asarray(Image.open(a.ton).convert('RGB')); ar = np.asarray(Image.open(a.tarka).convert('RGB'))
    go, ga = govde(on.astype(float)), govde(ar.astype(float))
    kap = np.asarray(Image.open(a.kapak).convert('RGB')).astype(float)
    sat, ok = [], True

    def kayit(ad, gecti, ayr):
        nonlocal ok
        ok &= bool(gecti); sat.append(f'{ad}: {ayr} {"PASS" if gecti else "FAIL"}')
    sat.append(f'kaynak: tek_on kupa kutusu {go}, tek_arka {ga} (2048 sahne, CL baskisi kapak_canva3 ile)')

    # 1. KAPAK_TEK
    t = np.zeros((900, S, 3)); bn, _ = baslik_ciz(t, FONT, 'CANCER', 'LIBRA', RENK, y_ust=0); bh = bn[3] - bn[1]
    bas_alt = UST + bh; pl_ust = ALT - ZEMIN_Y
    kh = go[3] - go[1]
    k1 = min(1.0, (pl_ust - bas_alt - 2 * ARA) / kh, (X45[1] - X45[0] - 2 * ARA) / (go[2] - go[0]))
    g1 = (pl_ust - bas_alt - kh * k1) / 2
    big, xy1, ek1 = yerlestir(on, go, k1, S / 2, bas_alt + g1, S, S)
    baslik_ciz(big, FONT, 'CANCER', 'LIBRA', RENK, y_ust=UST)
    pb, za = plaka(big, ALT)
    o1 = np.clip(np.rint(big), 0, 255).astype(np.uint8)
    O1 = o1.astype(float)
    n1, kb1 = kupa_ncc(O1, on, go, k1, xy1)
    m = O1[:bas_alt + 10].mean(2) < 90; ys, xs = np.where(m); tb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    kayit('KAPAK kupa NCC (kaynak sahne, ayni olcek)', n1 >= 0.99, f'{n1:.5f}; olcek {k1:.4f} (<=1); kupa kutusu {kb1}')
    kayit('KAPAK baslik guvenli alan (4:5 x 245-1803, ust >= 221)', tb[0] >= GUV[0] and tb[2] <= GUV[1] and tb[1] >= UST - 2, f'murekkep {tb}')
    kayit('KAPAK plaka 4:5 ve 34:27 icinde', pb[0] >= X45[0] and pb[2] <= X45[1] and pb[3] <= 1837, f'{pb}')
    kayit('KAPAK kupa 4:5 ve 34:27 icinde', kb1[0] >= X45[0] and kb1[2] <= X45[1] and kb1[1] >= 211 and kb1[3] <= 1837, f'{kb1}')
    pm = za > 0.99
    pn = ncc(O1[pb[1]:pb[3], pb[0]:pb[2]].mean(2)[pm], kap[PLAKA_KAPAK[1]:PLAKA_KAPAK[3], PLAKA_KAPAK[0]:PLAKA_KAPAK[2]].mean(2)[pm]) \
        if (pb[2] - pb[0], pb[3] - pb[1]) == (PLAKA_KAPAK[2] - PLAKA_KAPAK[0], PLAKA_KAPAK[3] - PLAKA_KAPAK[1]) else -1
    kayit('KAPAK plaka = V4 kapak plakasi (NCC, maske ici)', pn >= 0.99, f'{pn:.4f}')
    sat.append(f'KAPAK bosluk: baslik alt {tb[3]} -> kupa ust {kb1[1]} = {kb1[1] - tb[3]} px; kupa alt {kb1[3]} -> plaka ust {pb[1]} = {pb[1] - kb1[3]} px; '
               f'uzatma {ek1}')
    sx = [xy1[0] + ek1['serit_sol'] * 0] if ek1['sol'] else []
    st1, md1 = adim(O1, [ek1['sol']] if ek1['sol'] else [1], 0, S)
    yb1 = uzatma_kontrol(O1, [kb1, tb, pb], [(0, 0, ek1['sol'], S), (S - ek1['sag'], 0, S, S), (0, 0, S, ek1['ust']), (0, S - ek1['alt'], S, S)])
    kayit('KAPAK ek yeri (sol serit siniri sutun adimi <= max(0.5, 4 x medyan))', st1 <= max(0.5, 4 * md1), f'{st1:.3f} (medyan {md1:.3f})')
    kayit('KAPAK uzatmada duvar disi piksel (kulp/kupa kopyasi)', yb1 == 0, f'{yb1}')
    Image.fromarray(o1).save(os.path.join(a.cikti, 'KAPAK_TEK.jpg'), quality=92, subsampling=0, optimize=True)

    # 2. GALERI2_ON_ARKA: iki yari, ortada genis dogrusal gecis
    GEC = 160
    ek_boy = yaz(FONT, 'FRONT', BOY).shape[0]
    k2 = min(1.0, (S - 2 * 60 - GEC - 8) / ((go[2] - go[0]) + (ga[2] - ga[0])))
    grup = ek_boy + ARA + max(go[3] - go[1], ga[3] - ga[1]) * k2          # etiket + kupa, dikeyde ortali
    et_y = round((S - grup) / 2); ust2 = et_y + ek_boy + ARA
    wa, wb = (go[2] - go[0]) * k2, (ga[2] - ga[0]) * k2
    bos = (S - wa - wb - GEC - 8) / 2
    cxa, cxb = bos + wa / 2, S - bos - wb / 2
    A, xya, eka = yerlestir(on, go, k2, cxa, ust2, S, S)
    B, xyb, ekb = yerlestir(ar, ga, k2, cxb, ust2, S, S)
    xs0 = round(bos + wa) + 4; xs1 = xs0 + GEC
    w = np.zeros(S); w[xs1:] = 1; w[xs0:xs1] = np.linspace(0, 1, GEC)
    big = A * (1 - w[None, :, None]) + B * w[None, :, None]
    fa = etiket(big, 'FRONT', cxa, et_y); fb = etiket(big, 'BACK', cxb, et_y)
    o2 = np.clip(np.rint(big), 0, 255).astype(np.uint8); O2 = o2.astype(float)
    na, kba = kupa_ncc(O2, on, go, k2, xya); nb, kbb = kupa_ncc(O2, ar, ga, k2, xyb)
    kayit('GALERI2 on kupa NCC', na >= 0.99, f'{na:.5f}; olcek {k2:.4f}')
    kayit('GALERI2 arka kupa NCC', nb >= 0.99, f'{nb:.5f}')
    kayit('GALERI2 gecis kupalara degmez', kba[2] <= xs0 and kbb[0] >= xs1, f'gecis x {xs0}-{xs1}, on kupa x {kba[0]}-{kba[2]}, arka x {kbb[0]}-{kbb[2]}')
    kayit('GALERI2 etiket ve kupa kenar payi >= 40', min(fa[0], kba[0], S - fb[2], S - kbb[2], fa[1]) >= 40, f'FRONT {fa}, BACK {fb}')
    yb2 = uzatma_kontrol(O2, [kba, kbb, fa, fb], [(0, 0, xs0, eka['ust']), (xs1, 0, S, ekb['ust']), (0, S - eka['alt'], xs0, S), (xs1, S - ekb['alt'], S, S),
                                                   (0, 0, eka['sol'], S), (S - ekb['sag'], 0, S, S)])
    kayit('GALERI2 uzatmada duvar disi piksel', yb2 == 0, f'{yb2}')
    Image.fromarray(o2).save(os.path.join(a.cikti, 'GALERI2_ON_ARKA.jpg'), quality=92, subsampling=0, optimize=True)

    # 3. PIN_TEK 1000x1250: sahne dogrudan pin olceginde (tek kucultme); baslik ve plaka 2048 olcekte ayri katman,
    #    katman (onceden carpilmis renk + alfa) pin olcegine kucultulup bindirilir (S3 ile ayni boy)
    HP = 2560; sP = 1000 / S; PAY = round(40 / sP) + 2
    pl_alt = HP - PAY; pl_ust3 = pl_alt - ZEMIN_Y
    k3 = min(1.0, (S - 2 * PAY) / (go[2] - go[0]))
    kh3 = kh * k3
    g3 = (pl_ust3 - ARA - kh3 - bh) / 2                    # ust kenar -> baslik = baslik -> kupa = g3; kupa -> plaka = ARA
    kk = k3 * sP
    P, xy3, ek3 = yerlestir(on, go, kk, 500, (g3 + bh + g3) * sP, 1000, 1250)
    kat = []
    for zemin in (0.0, 255.0):
        z = np.full((HP, S, 3), zemin)
        baslik_ciz(z, FONT, 'CANCER', 'LIBRA', RENK, y_ust=round(g3)); pb3, _ = plaka(z, pl_alt)
        kat.append(z)
    alfa = np.clip(1 - (kat[1] - kat[0]).mean(2) / 255, 0, 1)
    def kucult(x):
        return np.asarray(Image.fromarray(x.astype(np.float32), 'F').resize((1000, 1250), Image.LANCZOS)).astype(float)
    ak = np.clip(kucult(alfa), 0, 1); pre = np.stack([kucult(kat[0][..., c]) for c in range(3)], 2)
    P = np.clip(P * (1 - ak[..., None]) + pre, 0, 255)
    pin = Image.fromarray(np.rint(P).astype(np.uint8)); P = np.asarray(pin).astype(float)
    ref = np.asarray(Image.fromarray(on).resize((round(S * kk),) * 2, Image.LANCZOS)).astype(float)
    r0, r1, c0, c1 = round(go[1] * kk), round(go[3] * kk), round(go[0] * kk), round(go[2] * kk)
    px, py = xy3
    n3 = ncc(P[py + r0:py + r1, px + c0:px + c1], ref[r0:r1, c0:c1])
    m = P[:py + r0 - 5].mean(2) < 90; ys, xs = np.where(m); tb3 = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    kayit('PIN kupa NCC', n3 >= 0.99, f'{n3:.5f}; olcek {kk:.4f} (<=1, tek kucultme), kupa {c1 - c0}x{r1 - r0} px')
    kayit('PIN baslik/plaka kenar payi >= 40', min(tb3[0], 999 - tb3[2], tb3[1], round(pb3[0] * sP), 1249 - round(pb3[3] * sP)) >= 40,
          f'baslik {tb3}, plaka x {round(pb3[0] * sP)}-{round(pb3[2] * sP)} y {round(pb3[1] * sP)}-{round(pb3[3] * sP)}')
    kayit('PIN bosluk esit (ust kenar-baslik = baslik-kupa)', abs(tb3[1] - (py + r0 - tb3[3])) <= 4, f'{tb3[1]} / {py + r0 - tb3[3]} px; kupa-plaka {round(pb3[1] * sP) - (py + r1)} px')
    yb3 = uzatma_kontrol(P, [(px + c0, py + r0, px + c1, py + r1), tb3, tuple(round(v * sP) for v in pb3)], [(0, 0, ek3['sol'], 1250), (0, 0, 1000, ek3['ust']), (0, 1250 - ek3['alt'], 1000, 1250)])
    kayit('PIN uzatmada duvar disi piksel', yb3 == 0, f'{yb3}')
    pin.save(os.path.join(a.cikti, 'PIN_TEK.jpg'), quality=92, subsampling=0, optimize=True)

    # 4. ONIZLEME_KIRPIM
    im = Image.fromarray(o1)
    kirp = {'255x319': ((205, 0, 1843, 2048), (255, 319)), '300x300': ((0, 0, 2048, 2048), (300, 300)), '340x270': ((0, 211, 2048, 1837), (340, 270))}
    c = Image.new('RGB', (20 + 255 + 20 + 300 + 20 + 340 + 20, 20 + 319 + 20), 'white'); x = 20
    for ad, (bx, bs) in kirp.items():
        c.paste(im.crop(bx).resize(bs, Image.LANCZOS), (x, 20)); x += bs[0] + 20
    c.save(os.path.join(a.cikti, 'ONIZLEME_KIRPIM.jpg'), quality=92)
    # %200 yakin kirpimlar
    for ad, img, (x0, y0) in (('KAPAK_SOL_UZATMA', im, (0, 700)), ('KAPAK_UST', im, (0, 0)), ('GALERI2_GECIS', Image.fromarray(o2), (xs0 - 120, 900)),
                              ('GALERI2_SOL', Image.fromarray(o2), (0, 900)), ('PIN_SOL', pin, (0, 500))):
        wc, hc = (500, 300) if img.size[0] <= 1000 else (1000, 600)
        x0 = int(min(max(x0, 0), img.size[0] - wc)); y0 = int(min(max(y0, 0), img.size[1] - hc))
        img.crop((x0, y0, x0 + wc, y0 + hc)).resize((wc * 2, hc * 2), Image.LANCZOS).save(os.path.join(a.cikti, f'YAKIN_{ad}.jpg'), quality=90)
    sat.append('Yazilar: CANCER & LIBRA, PERSONALIZED GIFT MUG, FRONT, BACK (nokta, +, = yok); kupa uzerindeki "CANCER · LIBRA" urun baskisi')
    sat.append(f'SONUC {"PASS" if ok else "FAIL"} (ek yeri icin YAKIN_*.jpg goz kontrolu)')
    open(os.path.join(a.cikti, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
