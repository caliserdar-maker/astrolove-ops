#!/usr/bin/env python3
"""Kupa pini 3 yerlesim secenegi, ORNEK (20 Eki 2026; yalniz CANCER_LIBRA, yalniz yerel). Yapay zeka yok; yalniz kod ile
kirpma, kucultme (oran <= 1.0), yansitmali duvar/masa uzatmasi (kupa_pin_ornek.py deneme 3 yontemi).
  S1 1000x1500: deneme 3 tabani (kupalar altta) + baslik ustte + aradaki boslukta on yuz baski dosyasindan sembol + glifler +
     EMILY ∞ JAMES (CANCER · LIBRA satiri noktali oldugu icin alinmaz) beyaz yumusak koseli alanda; bosluklar esit.
  S2 1000x1500: baslik ustte, tek on gorunum kupasi ustte, tek arka (mesajli) kupa altta, plaka en altta. Tam genislik
     sigmiyor (olcu OLCUM.txt); iki kupa ayni olcekle sigan en buyuk boyda.
  S3 1000x1250: deneme 3'un aynisi, kisa tuval; ust kenar-baslik ve baslik-kupa bosluklari esit.
Baslik kupa_kapak_78.baslik_ciz (Cinzel 650, stil rengi, ayni boy); plaka kapak pikselleri (V4 zemin maskesi R 40).
Kullanim: kupa_pin_secenek.py KAPAK.jpg SAHNE.png FONT.ttf BASKI_11oz.png TEK_ON.jpg TEK_ARKA.jpg CIKTI_DIR"""
import argparse, importlib.util, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('kpo', os.path.join(D, 'kupa_pin_ornek.py'))
kpo = importlib.util.module_from_spec(sp); sp.loader.exec_module(kpo)
baslik_ciz, kutu, tri, ncc, lum = kpo.baslik_ciz, kpo.kutu, kpo.tri, kpo.ncc, kpo.lum

W = 1000
S = 2048
s = W / S                                  # 2048 -> 1000
RENK = kpo.RENKLER['orange']
UST_BANT, MASA_KES, MASA_H = kpo.UST_BANT, kpo.MASA_KES, kpo.MASA_H
KUPA_UST, KUPA_ALT = kpo.KUPA_UST, kpo.KUPA_ALT
PLAKA = (288, 1699, 1760, 1827)            # kapak "PERSONALIZED GIFT MUG" zemini (V4: x k*MCU, alt 1827, yukseklik 128)
PLAKA_R = 40                               # kupa_alt_yazi_v2.R
# on yuz baski dosyasi (2700x1050) kirpimlari: susleme tasmasi 0 olculdu (kenar beyaz disi 0, yaprak px 0)
BASKI_UST = (416, 252, 804, 692)           # sembol + iki glif
BASKI_ISIM = (322, 786, 918, 856)          # EMILY ∞ JAMES
NCC_ESIK = 0.99


def yuvarlak(w, h, r, x4=4):
    t = Image.new('L', (w * x4, h * x4), 0)
    ImageDraw.Draw(t).rounded_rectangle((0, 0, w * x4 - 1, h * x4 - 1), radius=r * x4, fill=255)
    return np.asarray(t.resize((w, h), Image.BOX)).astype(float) / 255


def murekkep(P, y0, y1, x0=0, x1=W):
    m = P[y0:y1, x0:x1].mean(2) < 90
    ys, xs = np.where(m)
    return int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0, int(ys.max()) + y0


def kupa_ust(P, x0=round(327 * s), x1=round(1726 * s), y0=0):
    nt = (P.min(2) > 150) & (P.max(2) - P.min(2) < 10)
    g = nt[y0:, x0:x1].mean(1)
    return int(np.where(g > 0.3)[0].min()) + y0


def taban(a0, sc, hedef_satir):
    """deneme 3: eski baslik sahneyle silinir, ust duvar yansitmali uzatilir, masa +62 satir (tek periyot)."""
    f = a0.astype(float)
    koyu = np.abs(f - np.array(RENK)).max(2) < 40; koyu[int(0.4 * S):] = False
    bk = kutu(koyu)
    e = f.copy()
    ex0, ey0, ex1, ey1 = bk[0] - 12, bk[1] - 12, bk[2] + 12, bk[3] + 12
    e[ey0:ey1, ex0:ex1] = sc[ey0:ey1, ex0:ex1]
    kal = int((np.abs(e - np.array(RENK)).max(2) < 60)[:KUPA_UST - 30].sum())
    alt = 2 * MASA_H; ust = hedef_satir - S - alt
    ustb = e[:UST_BANT]
    us = np.stack([ustb[tri(k, UST_BANT)] for k in range(ust)])[::-1]
    band = e[MASA_KES - MASA_H:MASA_KES]
    al = np.stack([band[MASA_H - 1 - tri(k, MASA_H)] for k in range(alt)])
    return np.concatenate([us, e[:MASA_KES], al, e[MASA_KES:]]), ust, kal


def kapak_ncc(P, K, off):
    o = {}
    for ad, (k0, k1) in {'kupa': (KUPA_UST, KUPA_ALT), 'plaka': (PLAKA[1], PLAKA[3])}.items():
        q0, q1 = round(k0 * s), round(k1 * s)
        o[ad] = ncc(P[round(q0 + off):round(q1 + off)], K[q0:q1])
    return o


def s3(a0, sc, font, K):
    H = 1250
    big, ust, kal = taban(a0, sc, round(H / s))
    off = ust * s
    ku = round(KUPA_UST * s + off)      # yaklasik; olcum asagida
    t = big.copy(); bn, _ = baslik_ciz(t, font, 'CANCER', 'LIBRA', RENK, y_ust=0)
    bh = (bn[3] - bn[1]) * s
    P0 = np.asarray(Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(float)
    kt = kupa_ust(P0, y0=ku - 60)
    g = (kt - bh) / 2
    baslik_ciz(big, font, 'CANCER', 'LIBRA', RENK, y_ust=round(g / s))
    pin = Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    P = np.asarray(pin).astype(float)
    bx0, by0, bx1, by1 = murekkep(P, 0, kt - 10)
    n = kapak_ncc(P, K, off)
    sat = [f'S3 1000x1250: kapak olcek {s:.5f} (<=1); ust duvar uzatma {ust * s:.1f} px, masa {2 * MASA_H * s:.1f} px; eski baslik kalintisi {kal} px',
           f'S3 kupa NCC {n["kupa"]:.5f}, plaka NCC {n["plaka"]:.5f}',
           f'S3 bosluk: ust kenar -> baslik {by0} px, baslik -> kupa ust kenari {kt - by1} px (kupa ust y {kt}); baslik x {bx0}-{bx1}']
    ok = min(n.values()) >= NCC_ESIK and kal == 0 and abs(by0 - (kt - by1)) <= 3
    return pin, sat, ok


def s1(a0, sc, font, K, baski):
    H = 1500
    big, ust, kal = taban(a0, sc, round(H / s))
    off = ust * s
    t = big.copy(); bn, _ = baslik_ciz(t, font, 'CANCER', 'LIBRA', RENK, y_ust=0)
    bh = (bn[3] - bn[1]) * s
    P0 = np.asarray(Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(float)
    kt = kupa_ust(P0, y0=round(KUPA_UST * s + off) - 60)
    # panel icerigi: iki kirpim, baskidaki goreli yerlerinde, beyaz zeminde (piksel degismez)
    x0 = min(BASKI_UST[0], BASKI_ISIM[0]); y0 = BASKI_UST[1]
    x1 = max(BASKI_UST[2], BASKI_ISIM[2]); y1 = BASKI_ISIM[3]
    ic = Image.new('RGB', (x1 - x0, y1 - y0), (255, 255, 255))
    for b in (BASKI_UST, BASKI_ISIM):
        ic.paste(baski.crop(b), (b[0] - x0, b[1] - y0))
    PAD = 34
    g = 56                                   # esit bosluk (ust, baslik-panel, panel-kupa) icin baslangic
    ph = kt - bh - 3 * g
    c = (ph - 2 * PAD) / ic.size[1]
    assert c <= 1.0, c
    icw, ich = round(ic.size[0] * c), round(ic.size[1] * c)
    ph = ich + 2 * PAD; pw = icw + 2 * PAD
    g = (kt - bh - ph) / 3
    baslik_ciz(big, font, 'CANCER', 'LIBRA', RENK, y_ust=round(g / s))
    pin = Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    P = np.asarray(pin).astype(float)
    bx0, by0, bx1, by1 = murekkep(P, 0, kt - 10)
    py0 = round(by1 + g); px0 = round((W - pw) / 2)
    m = yuvarlak(pw, ph, PAD)
    reg = P[py0:py0 + ph, px0:px0 + pw]
    P[py0:py0 + ph, px0:px0 + pw] = reg * (1 - m[..., None]) + 255 * m[..., None]
    P[py0 + PAD:py0 + PAD + ich, px0 + PAD:px0 + PAD + icw] = np.asarray(ic.resize((icw, ich), Image.LANCZOS)).astype(float)
    pin = Image.fromarray(np.clip(np.rint(P), 0, 255).astype(np.uint8))
    P = np.asarray(pin).astype(float)
    n = kapak_ncc(P, K, off)
    icn = ncc(P[py0 + PAD:py0 + PAD + ich, px0 + PAD:px0 + PAD + icw], np.asarray(ic.resize((icw, ich), Image.LANCZOS)))
    sat = [f'S1 1000x1500: kapak olcek {s:.5f}; baski kirpimi {ic.size[0]}x{ic.size[1]} -> {icw}x{ich}, olcek {c:.4f} (<=1); '
           f'panel {pw}x{ph} beyaz, kose {PAD}, kenarlik yok; eski baslik kalintisi {kal} px',
           f'S1 kupa NCC {n["kupa"]:.5f}, plaka NCC {n["plaka"]:.5f}, panel icerik NCC {icn:.5f}',
           f'S1 bosluk: ust kenar -> baslik {by0}, baslik -> panel {py0 - by1}, panel -> kupa ust {kt - (py0 + ph)} px '
           f'(panel y {py0}-{py0 + ph}, kupa ust y {kt})']
    ok = min(n.values()) >= NCC_ESIK and icn >= NCC_ESIK and kal == 0 and c <= 1
    return pin, sat, ok


def yatay_uzat(a, sol, sag, bsol, bsag):
    """sutunlari yansitmali uzatir; yalniz kenardaki kupasiz serit (bsol / bsag sutun) dosenir (kulp kopyasi olmaz)."""
    L = np.stack([a[:, tri(k, bsol)] for k in range(sol)], 1)[:, ::-1] if sol > 0 else a[:, :0]
    w = a.shape[1]
    R = np.stack([a[:, w - 1 - tri(k, bsag)] for k in range(sag)], 1) if sag > 0 else a[:, :0]
    return np.concatenate([L, a, R], 1)


def s2(font, kap, ton, tarka):
    H = 1500; HB = round(H / s)            # 3072
    on, ar = np.asarray(ton).astype(float), np.asarray(tarka).astype(float)
    # olcu: kupa govde+kulp (beyaz) kutusu
    def govde(t):
        nt = (t.min(2) > 200) & (t.max(2) - t.min(2) < 14)
        ys = np.where(nt.mean(1) > 0.15)[0]; xs = np.where(nt[ys.min():ys.max()].mean(0) > 0.3)[0]
        return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    go, ga = govde(on), govde(ar)
    tam_k = S / max(go[2] - go[0], ga[2] - ga[0])               # tam genislik icin buyuk tuval olcegi
    tam_h = ((go[3] - go[1]) + (ga[3] - ga[1])) * tam_k * s       # iki kupa govde yuksekligi (pin)
    G_UST, G_PL, OV = 50, 34, 64                                  # pin px: baslik bosluklari, plaka bosluklari; gecis (buyuk)
    t = np.zeros((600, S, 3)); bn, _ = baslik_ciz(t, font, 'CANCER', 'LIBRA', RENK, y_ust=0); bh = bn[3] - bn[1]
    baslik_bolge = (2 * G_UST) / s + bh                          # buyuk olcek
    plaka_bolge = (2 * G_PL) / s + (PLAKA[3] - PLAKA[1])
    on_alt = go[3] + 50; ar_ust = ga[1] - 60
    # E(k) + k*on_alt + k*(ga[3]-ar_ust) + plaka_bolge - OV = HB, E = baslik_bolge - k*go[1]
    k = (HB + OV - baslik_bolge - plaka_bolge) / (on_alt - go[1] + ga[3] - ar_ust)
    assert k <= 1.0
    def olc(a, y0, y1):
        im = Image.fromarray(a[y0:y1].astype(np.uint8))
        return np.asarray(im.resize((round(S * k), round((y1 - y0) * k)), Image.LANCZOS)).astype(float)
    A = olc(on, 0, on_alt); B = olc(ar, ar_ust, S)
    # yatay: kupa merkezi tuval ortasina
    def ortala(a, g):
        x0 = round(S / 2 - (g[0] + g[2]) / 2 * k)          # tek gorunum sutun 0'in tuvaldeki yeri (negatif olabilir)
        sol, sag = x0, S - (a.shape[1] + x0)
        if sol < 0: a = a[:, -sol:]
        if sag < 0: a = a[:, :a.shape[1] + sag]
        bs = round(g[0] * k) - max(-x0, 0) - 12; bg = a.shape[1] - (round(g[2] * k) - max(-x0, 0)) - 12
        assert (sol <= 0 or bs > 8) and (sag <= 0 or bg > 8), (bs, bg)
        return yatay_uzat(a, max(sol, 0), max(sag, 0), bs, bg), x0, max(sol, 0), max(sag, 0), bs, bg
    A, ax0, asol, asag, abs_, abg = ortala(A, go); B, bx0_, bsol, bsag, bbs, bbg = ortala(B, ga)
    E = round(baslik_bolge - k * go[1])
    ub = A[:UST_BANT]
    Ue = np.stack([ub[tri(j, UST_BANT)] for j in range(E)])[::-1] if E > 0 else A[:0]
    A = np.concatenate([Ue, A])
    # gecis: A alt OV satiri ile B ust OV satiri dogrusal
    w = np.linspace(0, 1, OV)[:, None, None]
    mid = A[-OV:] * (1 - w) + B[:OV] * w
    big = np.concatenate([A[:-OV], mid, B[OV:]])
    eksik = HB - big.shape[0]
    if eksik > 0:                          # alt yuzey yansitmali uzatma
        bb = big[-UST_BANT:]
        big = np.concatenate([big, np.stack([bb[UST_BANT - 1 - tri(j, UST_BANT)] for j in range(eksik)])])
    big = big[:HB]
    by = round(G_UST / s)
    baslik_ciz(big, font, 'CANCER', 'LIBRA', RENK, y_ust=by)
    pin = Image.fromarray(np.clip(np.rint(big), 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    P = np.asarray(pin).astype(float)
    # plaka: kapak pikselleri (pin olcegi), V4 zemin maskesiyle
    K = np.asarray(kap).astype(float)
    p0 = [round(v * s) for v in PLAKA]; pw, ph = p0[2] - p0[0], p0[3] - p0[1]
    m = yuvarlak(pw, ph, round(PLAKA_R * s))
    py0 = H - round(G_PL) - ph; px0 = p0[0]
    reg = P[py0:py0 + ph, px0:px0 + pw]
    P[py0:py0 + ph, px0:px0 + pw] = reg * (1 - m[..., None]) + K[p0[1]:p0[3], p0[0]:p0[2]] * m[..., None]
    pin = Image.fromarray(np.clip(np.rint(P), 0, 255).astype(np.uint8)); P = np.asarray(pin).astype(float)
    pn = ncc(P[py0:py0 + ph, px0:px0 + pw][m > 0.99], K[p0[1]:p0[3], p0[0]:p0[2]][m > 0.99])
    # kupa NCC: tek gorunum kupa kutusu, ayni toplam olcek (k*s) ile
    def kn(t, g, y_pin, x_pin):
        kk = k * s
        ref = np.asarray(Image.fromarray(t.astype(np.uint8)).resize((round(S * kk), round(S * kk)), Image.LANCZOS)).astype(float)
        r0, r1, c0, c1 = round(g[1] * kk), round(g[3] * kk), round(g[0] * kk), round(g[2] * kk)
        return ncc(P[y_pin + r0:y_pin + r1, x_pin + c0:x_pin + c1], ref[r0:r1, c0:c1]), (c1 - c0, r1 - r0)
    a_y = round(E * s); a_x = round(ax0 * s)
    b_y = round((E + (on_alt * k) - OV) * s) - round(ar_ust * k * s); b_x = round(bx0_ * s)
    n_on, bo = kn(on, go, a_y, a_x); n_ar, ba = kn(ar, ga, b_y, b_x)
    bx0, by0, bx1, by1 = murekkep(P, 0, round(baslik_bolge * s) + 20)
    ku_on = a_y + round(go[1] * k * s)
    gecis = round((E + on_alt * k - OV) * s)
    sat = [f'S2 1000x1500: tam genislik SIGMAZ: kupa {max(go[2] - go[0], ga[2] - ga[0])} px kaynak -> 1000 px icin iki kupa govdesi '
           f'{tam_h:.0f} px + baslik + plaka > 1500. Sigan en buyuk: kaynak olcek {k * s:.4f} (<=1), kupa {bo[0]}x{bo[1]} ve '
           f'{ba[0]}x{ba[1]} px (genislik %{100 * bo[0] / W:.0f})',
           f'S2 on kupa NCC {n_on:.5f}, arka kupa NCC {n_ar:.5f}, plaka NCC {pn:.5f} (kapak pikselleri, maske ici)',
           f'S2 bosluk: ust kenar -> baslik {by0}, baslik -> on kupa ust {ku_on - by1}, plaka alti -> alt kenar {H - (py0 + ph)} px; '
           f'iki sahne gecisi y {gecis}-{gecis + round(OV * s)} (dogrusal {round(OV * s)} px); yan yuzey yansitma (yalniz kupasiz kenar seridi) on sol {round(asol * s)} px (serit {round(abs_ * s)}), on sag {round(asag * s)}, arka sol {round(bsol * s)}, arka sag {round(bsag * s)} px (serit {round(bbg * s)})']
    ok = min(n_on, n_ar, pn) >= NCC_ESIK and k * s <= 1
    return pin, sat, ok, gecis


def main():
    p = argparse.ArgumentParser()
    for x in ('kapak', 'sahne', 'font', 'baski', 'ton', 'tarka', 'cikti'):
        p.add_argument(x)
    a = p.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    a0 = np.asarray(Image.open(a.kapak).convert('RGB'))
    sc = np.asarray(Image.open(a.sahne).convert('RGB')).astype(float)
    kap = Image.fromarray(a0).resize((W, W), Image.LANCZOS); K = np.asarray(kap).astype(float)
    baski = Image.open(a.baski).convert('RGB')
    p1, l1, o1 = s1(a0, sc, a.font, K, baski)
    p2, l2, o2, gecis = s2(a.font, kap, Image.open(a.ton).convert('RGB'), Image.open(a.tarka).convert('RGB'))
    p3, l3, o3 = s3(a0, sc, a.font, K)
    for ad, im in (('S1', p1), ('S2', p2), ('S3', p3)):
        im.save(os.path.join(a.cikti, f'{ad}.jpg'), quality=92, subsampling=0, optimize=True)
    # kontak: ayni yukseklik 1250, alt etiket
    Hk = 1250
    ims = [im.resize((round(im.size[0] * Hk / im.size[1]), Hk), Image.LANCZOS) for im in (p1, p2, p3)]
    try:
        ft = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
    except OSError:
        ft = ImageFont.load_default()
    Wk = sum(i.size[0] for i in ims) + 40 * 4
    c = Image.new('RGB', (Wk, Hk + 40 + 90), 'white'); d = ImageDraw.Draw(c); x = 40
    for et, i in zip(('S1', 'S2', 'S3'), ims):
        c.paste(i, (x, 40)); tw = d.textlength(et, font=ft); d.text((x + (i.size[0] - tw) / 2, Hk + 60), et, font=ft, fill=(0, 0, 0))
        x += i.size[0] + 40
    c.save(os.path.join(a.cikti, 'KONTAK_SECENEK.jpg'), quality=90)
    # %200 yakin kirpimlar (goz kontrolu)
    for ad, im, (x0, y0) in (('S2_GECIS', p2, (250, gecis - 75)), ('S2_YAN_SOL', p2, (0, 600)), ('S2_YAN_SAG', p2, (500, 1100)),
                             ('S1_PANEL', p1, (250, 0)), ('S3_UST', p3, (250, 0))):
        y0 = int(min(max(y0, 0), im.size[1] - 300))
        im.crop((x0, y0, x0 + 500, y0 + 300)).resize((1000, 600), Image.LANCZOS).save(os.path.join(a.cikti, f'YAKIN_{ad}_y{y0}.jpg'), quality=92)
    sat = l1 + [f'S1 SONUC {"PASS" if o1 else "FAIL"}'] + l2 + [f'S2 SONUC {"PASS" if o2 else "FAIL"} (tam genislik sarti saglanamadi)'] \
        + l3 + [f'S3 SONUC {"PASS" if o3 else "FAIL"}', 'Not: kupa uzerindeki "CANCER · LIBRA" satiri kupa pikseli, degistirilmedi.']
    open(os.path.join(a.cikti, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat))


if __name__ == '__main__':
    main()
