#!/usr/bin/env python3
"""TEK KUPA 9:16 sosyal video ORNEGI (21 Eki 2026, Serdar; yalniz CANCER_LIBRA): uretim + QC, tek script, PASS/FAIL. Yazma yok.

Kaynak: kupa-orchard tek kupa on/arka sahneleri (Orange Blossom, varlik/gorunum/*_sahne_tek_on|arka.png + geo), baski
cift.py ciktisindan (video/ full, basem, beyaz, mask_*), giydirme kapak_canva3.py (cift.py ile ayni ortam). On/arka esitleme
kupa-printful-sonuc esitle.py matematigi (kucuk kupali sahne kirpilip buyutulur; buyutulen sahnenin tum katmanlarina ayni
donusum uygulanir; esitle.py ciktisi ile fark olculur). Urun pikselleri yalniz giydirme + yeniden ornekleme, AI yok.
Yerlesim (Serdar: en buyuk ve ortali): kupa govdesi merkezi x 540; olcek s = V / 2048 (<= 1): on ve arka kulp tuvalde
(kenar payi 10 px) ve baslik + kupa + plaka 230-1536 icine sigan en buyuk; sahne tuvali yatayda kaplar (V >= 1080).
Baslik "CANCER & LIBRA" kupa kapak V4 cizimi (Cinzel 650, 104*K, & %62, ara %12; #0A2818); plaka "PERSONALIZED GIFT MUG"
V4 olculeri (102 px yazi, 128 px zemin, kose 40, ic pay 48; 2048 -> 1080 orani) #E6DBD1 zeminde. Bosluklar: baslik-kupa ve
kupa-plaka 48 px, ust ve alt bosluk esit. Sahne disi satirlar yd_reel.py (b11ec836) yontemiyle zeminin kendi pikselleriyle uzar.
Hareket: video6b V6 (sigma 0,45; N = 10400 x ön yuz sembol bolgesi / kapak sembol bolgesi, "toz 10400 tabani"; 2,0-4,0 sn
alan basina yogunluk onayli kupa ilan videosu referansinin (v6_kupa_ref.json) +-%10 disindaysa bir kez N x olculen oran,
ilan78 kurali), V = bu olcek (upscale yok). Motorda yalniz N, sigma, V ve bos mesaj maskesi korumasi degisir (on yuzde mesaj
yok: MM = 0, yazim katmani zaten 0; cikti ayni). Yalniz on yuz baski kutusu motor karesinden alinir; baslik, plaka, zemin sabit.
Zaman: 0-1 sn tasarim (on), 1-6 sn motor 0-5 sn, 6,0-6,4 sn on -> arka yumusak gecis, 6,4-8 sn arka yuz sabit.
30 fps, 240 kare, ses yok, H.264 yuv420p crf 14.
Cikti: CANCER_LIBRA_tek_kupa_reel.mp4, ILK_KARE_ARAYUZ.jpg, KONTAK_0_8SN.jpg, OLCUM.txt, OLCUM.json
Kullanim: tek_kupa_reel.py <kupa_orchard dizini> <cift.py video/ dizini> <esitle.py> <B1> <B2> <cikti> <is>"""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(HERE, '..', '..'))
sp = importlib.util.spec_from_file_location('kpo', os.path.join(KOK, 'scripts', 'sosyal', 'kupa_pin_ornek.py'))
kpo = importlib.util.module_from_spec(sp); sp.loader.exec_module(kpo)
sp = importlib.util.spec_from_file_location('ydr', os.path.join(HERE, 'yd_reel.py'))
yd = importlib.util.module_from_spec(sp); sp.loader.exec_module(yd)
lum, ncc, psnr, kareler, SHIM = yd.lum, yd.ncc, yd.psnr, yd.kareler, yd.SHIM
REF = json.load(open(os.path.join(HERE, 'v6_kupa_ref.json')))

W, H, FPS = 1080, 1920, 30
S = 2048
UST, ALT_Y, SAG = 230, 1536, 918
ONCE, HAREKET, GECIS, TOPLAM = 30, 150, 12, 240              # 0-1 sn, 1-6 sn, 6,0-6,4 sn, 6,4-8 sn
KENAR = 10                                                  # kulp - tuval kenari payi
G_ARA = 48                                                  # baslik-kupa ve kupa-plaka boslugu
RENK = (10, 40, 24)                                         # #0A2818 (cift.py orange)
PLAKA_RENK = (230, 219, 209)                                # #E6DBD1
Q4 = W / S                                                  # V4 olculeri 2048 kapakta -> 1080
TS4 = (2.0, 2.5, 3.0, 3.5, 4.0)
ENV_G = {'GOLGE_US': '0.4', 'PARLA': '0.7'}                 # cift.py giydirme ortami


def calis(args, env=None, cwd=None):
    r = subprocess.run(args, capture_output=True, text=True, env=dict(os.environ, **(env or {})), cwd=cwd)
    if r.returncode:
        raise SystemExit(f'HATA {args[:3]}: {r.stdout[-400:]} {r.stderr[-800:]}')
    return r.stdout


def esitle_mat(g_on, g_ar, Wi):
    """esitle.py ile ayni hesap; donus: (buyutulen ad, s, x0, y0)."""
    def bilgi(g):
        xl, xr, yt, yb, et, eb = g
        return (xl + xr) / 2, (xr - xl) / 2, yb + eb
    c_on, r_on, t_on = bilgi(g_on); c_ar, r_ar, t_ar = bilgi(g_ar)
    if r_on >= r_ar:
        rc, rr, rt = c_on, r_on, t_on; ad, c, r, t = 'arka', c_ar, r_ar, t_ar
    else:
        rc, rr, rt = c_ar, r_ar, t_ar; ad, c, r, t = 'on', c_on, r_on, t_on
    s = rr / r
    x0 = c - (Wi - rc) / s; y0 = t - rt / s; boy = Wi / s
    return ad, s, min(max(x0, 0), Wi - boy), min(max(y0, 0), Wi - boy)


def donustur(yol, s, x0, y0, Wi, cikti):
    im = Image.open(yol).convert('RGB')
    im.resize((Wi, Wi), Image.LANCZOS, box=(x0, y0, x0 + Wi / s, y0 + Wi / s)).save(cikti)


def maske_oku(d, ad, v):
    o = lambda p: cv2.resize(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), (v, v), interpolation=cv2.INTER_AREA)  # noqa: E731
    return np.clip((1 - o(os.path.join(d, f'k_mask_{ad}.png')).mean(-1) / np.maximum(o(os.path.join(d, 'k_beyaz.png')).mean(-1), 1)) * 1.4, 0, 1)


def bolge_px(d, v):
    sm = maske_oku(d, 'nosym', v) > 0.95
    return int((cv2.dilate(sm.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0).sum()), sm


def motor_kod(v6b, N, V, tozsuz=False):
    src = open(v6b).read()
    for a_, n_ in (('N = 5200 ', 1), ('(0, 0), 0.9)', 2), ('V, FPS, SURE, SILME = 1080, 30, 6.0, 0.3', 1), ('mx0, mx1 = kapsam(MM)', 1),
                   ('a3 = np.clip(al, 0, 0.9)[..., None]', 1)):
        assert src.count(a_) == n_, a_
    k = src.replace('N = 5200 ', f'N = {N} ', 1).replace('GaussianBlur(al, (0, 0), 0.9)', 'GaussianBlur(al, (0, 0), 0.45)') \
        .replace('GaussianBlur(kat, (0, 0), 0.9)', 'GaussianBlur(kat, (0, 0), 0.45)') \
        .replace('V, FPS, SURE, SILME = 1080, 30, 6.0, 0.3', f'V, FPS, SURE, SILME = {V}, 30, 6.0, 0.3') \
        .replace('mx0, mx1 = kapsam(MM)', 'mx0, mx1 = kapsam(MM) if (MM > 0.2).any() else (0, 1)   # on yuzde mesaj yok: MM = 0')
    if tozsuz:   # yalniz QC (v6_kalibre ile ayni): toz kapali kopya
        k = k.replace('a3 = np.clip(al, 0, 0.9)[..., None]', 'a3 = np.clip(al, 0, 0.9)[..., None] * 0', 1)
    return k


def motor(v6b, kat, kapak, N, V, is_dir, ad, tozsuz=False):
    k6 = os.path.join(is_dir, f'{ad}.py'); open(k6, 'w').write(motor_kod(v6b, N, V, tozsuz))
    mp4 = os.path.join(is_dir, f'{ad}.mp4')
    env = {}
    raw = None
    if not tozsuz:
        shim = os.path.join(is_dir, 'shim'); os.makedirs(shim, exist_ok=True)
        y = os.path.join(shim, 'ffmpeg'); open(y, 'w').write(SHIM); os.chmod(y, os.stat(y).st_mode | stat.S_IEXEC)
        raw = os.path.join(is_dir, f'{ad}.rgb')
        env = dict(YD_RAW=raw, YD_FFMPEG=subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True).stdout.strip(),
                   PATH=shim + os.pathsep + os.environ['PATH'])
    calis([sys.executable, '-I', k6, kat.rstrip('/') + '/', kapak, mp4], env)
    for f in os.listdir(is_dir):
        if f.startswith(ad + '_') and f.endswith('.jpg'):
            os.remove(os.path.join(is_dir, f))
    if raw:
        n = os.path.getsize(raw) // (V * V * 3)
        return mp4, np.memmap(raw, np.uint8, 'r', shape=(n, V, V, 3))
    return mp4, None


def toz_olc(mp, mt, SM, V):
    """v6_kalibre.olc ile ayni: alan basina toz yogunlugu (bolge = SM 15x15 genisletilmis, fark > 20, taban 5,3-6 sn)"""
    bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    D = np.array([float(((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(-1) > 20) & bol).sum() / bol.sum())
                  for a, b in zip(kareler(mp, V, V), kareler(mt, V, V))])
    D = np.clip(D - D[160:].mean(), 0, None)
    tb = {}
    for t in TS4:
        i = int(round(t * FPS)); ref = REF['kupa_toz_alan_basina'][f'{t:g}']
        tb[f'{t:g}'] = {'tek_kupa': round(float(D[i]), 3), 'kupa_ref': ref, 'fark_yuzde': round(100 * (D[i] / ref - 1), 1)}
    return tb


def uzat(A, temiz, n, ad):
    """yd_reel.uzat yontemi (b11ec836), yukseklik serbest; doku yalniz temiz maskeli piksellerden."""
    TAU, BL, BS = yd.TAU, yd.BL, yd.BS
    rng = np.random.default_rng(7)
    k = A.astype(np.float32); h = k.shape[0]
    LF = cv2.GaussianBlur(k, (0, 0), sigmaX=6, sigmaY=0.01)
    HF = k - cv2.GaussianBlur(k, (0, 0), 2.0)
    LF40 = cv2.GaussianBlur(k, (0, 0), sigmaX=40, sigmaY=0.01)
    tz = cv2.erode(temiz.astype(np.uint8), np.ones((BS, BS), np.uint8), anchor=(0, 0)) > 0
    tz[-BS:] = False; tz[:, -BS:] = False
    cy, cx = np.where(tz)
    if len(cy) < 50:
        raise SystemExit(f'{ad}: doku icin temiz zemin yok')
    satirlar = np.arange(0, 80) if ad == 'ust' else np.arange(h - 50, h)
    ys = satirlar.astype(np.float32); ym = ys.mean(); ke = 0.0 if ad == 'ust' else h - 1.0
    d = np.arange(1, n + 1, dtype=np.float32)[:, None, None]

    def fit(B):
        P = B[satirlar]
        e = ((ys - ym)[:, None, None] * (P - P.mean(0))).sum(0) / ((ys - ym) ** 2).sum()
        return P.mean(0) + e * (ke - ym), e
    v40, egim = fit(LF40)
    v6, _ = fit(LF)
    yon = -1.0 if ad == 'ust' else 1.0
    lf = v40[None] + yon * egim[None] * TAU * (1 - np.exp(-d / TAU)) + (v6 - v40)[None] * np.exp(-d / 12.0)
    num = np.zeros_like(lf); den = np.zeros(lf.shape[:2] + (1,), np.float32)
    ram = np.ones(BS, np.float32); ram[:BS - BL] = np.sin(np.linspace(0, np.pi / 2, BS - BL + 2)[1:-1]); ram[BL:] = ram[:BS - BL][::-1]
    for yb in range(0, n, BL):
        for xb in range(-(BS - BL), W, BL):
            hh = min(BS, n - yb); x_a, x_b = max(0, xb), min(W, xb + BS)
            wy = ram[:hh].copy()
            if yb == 0:
                wy[:BS - BL] = 1.0
            wx = ram[x_a - xb:x_b - xb]
            if xb <= 0:
                wx[:] = np.maximum(wx, (np.arange(x_a, x_b) < BS - BL).astype(np.float32))
            if xb + BS >= W:
                wx[:] = np.maximum(wx, (np.arange(x_a, x_b) >= W - (BS - BL)).astype(np.float32))
            if yb == 0:
                blok = (HF[0:hh] if ad == 'ust' else HF[h - 1:h - 1 - hh:-1])[:, x_a:x_b]
            else:
                j = rng.integers(len(cy)); sy, sx = cy[j], cx[j]
                blok = HF[sy:sy + hh, sx:sx + (x_b - x_a)]
                if blok.shape[1] < x_b - x_a:
                    blok = np.pad(blok, ((0, 0), (0, x_b - x_a - blok.shape[1]), (0, 0)), mode='reflect')
            w2 = (wy[:, None] * wx[None, :])[..., None]
            num[yb:yb + hh, x_a:x_b] += w2 * blok; den[yb:yb + hh, x_a:x_b] += w2 * w2
    b = lf + num / np.sqrt(np.maximum(den, 1e-6))
    return b[::-1] if ad == 'ust' else b


def kupa_kutu(a):
    """beyaz govde + kulp (doygunluk < 9; bej zemin 18-27): x0, y0, x1, y1"""
    w = (a.min(2) > 170) & (a.max(2) - a.min(2) < 9)
    ys = np.where(w.sum(1) > 20)[0]; xs = np.where(w.sum(0) > 20)[0]
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def plaka(font):
    m = kpo.yaz(font, 'PERSONALIZED GIFT MUG', 102 * Q4)
    h, w = m.shape
    zh = round(128 * Q4); zw = w + 2 * round(48 * Q4); r = round(40 * Q4)
    t = Image.new('L', (zw * 4, zh * 4), 0)
    ImageDraw.Draw(t).rounded_rectangle((0, 0, zw * 4 - 1, zh * 4 - 1), radius=r * 4, fill=255)
    za = np.asarray(t.resize((zw, zh), Image.BOX)).astype(np.float32) / 255
    return m, za


def main():
    KO, VD, ESITLE, B1, B2, OUT, IS = sys.argv[1:8]
    KO, VD, ESITLE, OUT, IS = (os.path.abspath(p) for p in (KO, VD, ESITLE, OUT, IS))   # giydirme cwd=kod/ ile calisir
    CIFT = f'{B1}_{B2}'
    os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
    t0 = time.time()
    O, kapi = {}, {}
    KOD, VG = os.path.join(KO, 'kod'), os.path.join(KO, 'varlik', 'gorunum')
    FONT = os.path.join(KO, 'varlik', 'font', 'Cinzel[wght].ttf')
    V6B = os.path.join(KOD, 'video6b.py')

    # ---------- 1. giydirme (cift.py ile ayni) + esitleme
    ham = {'on': os.path.join(IS, 'ham_on'), 'arka': os.path.join(IS, 'ham_arka')}
    for y in ham:
        os.makedirs(ham[y], exist_ok=True)
    sah = {y: os.path.join(VG, f'ORCHARD_OrangeBlossom_sahne_tek_{y}.png') for y in ham}
    geo = {y: os.path.join(VG, f'geo_tek_{y}.json') for y in ham}
    isler = [('on', 'full_baski_11oz.png', 'kb_full_baski_11oz.png'), ('on', 'basem_baski_11oz.png', 'kb_basem_baski_11oz.png'),
             ('on', 'beyaz.png', 'k_beyaz.png')] + [('on', f'mask_{a}.png', f'k_mask_{a}.png') for a in ('nosym', 'noglif', 'nomes')] \
        + [('arka', 'full_baski_11oz.png', 'kb_full_baski_11oz.png')]
    for y, src, dst in isler:
        calis([sys.executable, '-I', os.path.join(KOD, 'kapak_canva3.py'), sah[y], os.path.join(VD, src), geo[y], os.path.join(ham[y], dst)], ENV_G, cwd=KOD)
    g_on = json.load(open(geo['on']))['sol']; g_ar = json.load(open(geo['arka']))['sag']
    ad_b, s_e, x0e, y0e = esitle_mat(g_on, g_ar, S)
    kat = {'on': os.path.join(IS, 'kat_on'), 'arka': os.path.join(IS, 'kat_arka')}
    for y in kat:
        os.makedirs(kat[y], exist_ok=True)
        for f in os.listdir(ham[y]):
            if y == ad_b:
                donustur(os.path.join(ham[y], f), s_e, x0e, y0e, S, os.path.join(kat[y], f))
            else:
                Image.open(os.path.join(ham[y], f)).convert('RGB').save(os.path.join(kat[y], f))
    # esitle.py'nin kendisiyle karsilastirma (JPEG 95 ciktisi)
    calis([sys.executable, '-I', ESITLE, os.path.join(ham['on'], 'kb_full_baski_11oz.png'), geo['on'],
           os.path.join(ham['arka'], 'kb_full_baski_11oz.png'), geo['arka'], os.path.join(IS, 'es')])
    es_f = {y: float(np.abs(np.asarray(Image.open(os.path.join(IS, f'es_{y}.jpg')).convert('RGB')).astype(int)
                             - np.asarray(Image.open(os.path.join(kat[y], 'kb_full_baski_11oz.png')).convert('RGB')).astype(int)).mean()) for y in kat}
    O['esitle'] = {'buyutulen': ad_b, 'olcek': round(s_e, 5), 'kirpma': [round(x0e, 1), round(y0e, 1)],
                   'esitle_py_ciktisi_ile_ort_fark': {k_: round(v_, 3) for k_, v_ in es_f.items()}}
    kapi['on/arka esitleme = esitle.py (ort fark <= 1,5; JPEG 95)'] = max(es_f.values()) <= 1.5
    ON = os.path.join(kat['on'], 'kb_full_baski_11oz.png'); AR = os.path.join(kat['arka'], 'kb_full_baski_11oz.png')
    a_on = np.asarray(Image.open(ON).convert('RGB')).astype(int); a_ar = np.asarray(Image.open(AR).convert('RGB')).astype(int)

    # ---------- 2. olcek ve yerlesim
    kb = {'on': kupa_kutu(a_on), 'arka': kupa_kutu(a_ar)}
    xl, xr = (g_on[0], g_on[1]) if ad_b != 'on' else ((g_on[0] - x0e) * s_e, (g_on[1] - x0e) * s_e)
    cx = (xl + xr) / 2                                            # on govde merkezi (esitlenmis sahne)
    erisim = max(max(cx - b[0], b[2] - cx) for b in kb.values())   # merkezden en uzak kulp ucu
    tt = np.zeros((600, W, 3)); bt0, _ = kpo.baslik_ciz(tt, FONT, B1, B2, RENK, y_ust=0); th = bt0[3] - bt0[1]
    mk, za = plaka(FONT); ph = za.shape[0]
    ky0 = min(b[1] for b in kb.values()); ky1 = max(b[3] for b in kb.values())
    s_w = (W / 2 - KENAR) / erisim
    s_h = (ALT_Y - UST - th - ph - 2 * G_ARA) / (ky1 - ky0)
    s = min(s_w, s_h, 1.0)
    V = int(np.floor(S * s / 2)) * 2; s = V / S
    assert V >= W, f'V {V} < 1080: sahne tuvali yatayda kaplamaz'
    ox = int(round(W / 2 - cx * s))                               # sahne x 0 -> tuval
    icerik = th + G_ARA + (ky1 - ky0) * s + G_ARA + ph
    bos = (ALT_Y - UST - icerik) / 2
    y_baslik = int(round(UST + bos))
    y_kupa = y_baslik + th + G_ARA                                # kupa ust kenari (tuval)
    oy = int(round(y_kupa - ky0 * s))
    y_plaka = int(round(oy + ky1 * s + G_ARA))
    O['olcek'] = {'s': round(s, 5), 'V': V, 'sinir_genislik': round(s_w, 4), 'sinir_yukseklik': round(s_h, 4), 'kulp_erisim_px': round(erisim, 1)}
    O['yerlesim'] = {'ox': ox, 'oy': oy, 'baslik_y': y_baslik, 'kupa_y': [y_kupa, int(round(oy + ky1 * s))], 'plaka_y': [y_plaka, y_plaka + ph],
                     'govde_merkez_x': round(ox + cx * s, 2)}
    kapi['olcek <= 1 (upscale yok) ve sahne tuvali yatayda kaplar'] = s <= 1 and ox <= 0 and ox + V >= W

    # ---------- 3. tasarim (on, arka)
    def tasarim(a_yol):
        R = np.clip(np.round(cv2.resize(np.asarray(Image.open(a_yol).convert('RGB')).astype(np.float32), (V, V), interpolation=cv2.INTER_AREA)), 0, 255)
        Rc = R[:, -ox:-ox + W]
        kk = kupa_kutu(Rc.astype(int))
        r0, r1 = max(0, -oy), min(V, H - oy)
        A = Rc[r0:r1]
        T = np.zeros((H, W, 3), np.float32); ya = oy + r0; yb = oy + r1
        T[ya:yb] = A
        tem_u = np.zeros(A.shape[:2], bool); tem_u[:max(kk[1] - 40 - r0, 0)] = True
        tem_a = np.zeros(A.shape[:2], bool); tem_a[min(kk[3] + 60 - r0, A.shape[0]):] = True
        if ya > 0:
            T[:ya] = uzat(A, tem_u, ya, 'ust')
        if yb < H:
            T[yb:] = uzat(A, tem_a, H - yb, 'alt')
        tasarim_ham = np.clip(np.round(T), 0, 255).astype(np.uint8)
        T2 = T.copy()
        bt, _ = kpo.baslik_ciz(T2, FONT, B1, B2, RENK, y_ust=y_baslik)
        zx0 = (W - za.shape[1]) // 2
        sub = T2[y_plaka:y_plaka + ph, zx0:zx0 + za.shape[1]]
        T2[y_plaka:y_plaka + ph, zx0:zx0 + za.shape[1]] = sub * (1 - za[..., None]) + np.array(PLAKA_RENK, np.float32) * za[..., None]
        mh, mw = mk.shape; tx0 = (W - mw) // 2; ty0 = y_plaka + (ph - mh) // 2
        sub = T2[ty0:ty0 + mh, tx0:tx0 + mw]
        T2[ty0:ty0 + mh, tx0:tx0 + mw] = sub * (1 - mk[..., None]) + np.array(RENK, np.float32) * mk[..., None]
        kut = {'baslik': tuple(int(v) for v in bt), 'plaka': (zx0, y_plaka, zx0 + za.shape[1], y_plaka + ph),
               'plaka_yazisi': (tx0, ty0, tx0 + mw, ty0 + mh), 'kupa (kulp dahil)': (kk[0], kk[1] + oy, kk[2], kk[3] + oy)}
        return np.clip(np.round(T2), 0, 255).astype(np.uint8), (ya, yb), kut, R, tasarim_ham
    TON, ek_on, kut, R_on, ham_on = tasarim(ON)
    TAR, ek_ar, kut_ar, _, _ = tasarim(AR)
    Image.fromarray(TON).save(os.path.join(IS, 'tasarim_on.png')); Image.fromarray(TAR).save(os.path.join(IS, 'tasarim_arka.png'))

    # ---------- 4. motor: N (toz 10400 tabani, alan orani), V = bu olcek; yogunluk kapisi, gerekirse bir kez N x oran
    bol_t, SMt = bolge_px(kat['on'], V)
    bol_k, _ = bolge_px(VD, W)                                    # onayli kupa ilan videosu: kapak katmanlari 1080'de (cift.py video/)
    N1 = int(round(10400 * bol_t / bol_k / 100.0) * 100)
    turlar = []
    N = N1
    for tur in (1, 2):
        mp, F = motor(V6B, kat['on'], ON, N, V, IS, f'motor{tur}')
        mt, _ = motor(V6B, kat['on'], ON, N, V, IS, f'tozsuz{tur}', tozsuz=True)
        tb = toz_olc(mp, mt, SMt, V)
        ok = all(abs(v['fark_yuzde']) <= 10 for v in tb.values())
        turlar.append({'N': N, 'toz_2_4sn': tb, 'tutar': ok})
        if ok or tur == 2:
            break
        oran = float(np.median([v['kupa_ref'] / max(v['tek_kupa'], 1e-6) for v in tb.values()]))
        N = int(round(N * oran / 100.0) * 100)
    O['toz'] = {'bolge_px_tek': bol_t, 'bolge_px_kapak_1080': bol_k, 'N1': N1, 'turlar': turlar}
    kapi['toz yogunlugu 2-4 sn onayli kupa ilan videosu ile alan basina +-%10'] = turlar[-1]['tutar']
    KAP = np.array(F[0])
    O['motor_kare0_tasarim_fark'] = int(np.abs(KAP.astype(int) - R_on.astype(int)).max())
    kapi['motor ilk/son kare = on sahne (bu olcek)'] = O['motor_kare0_tasarim_fark'] == 0 and int(np.abs(F[-1].astype(int) - KAP.astype(int)).max()) == 0
    deg = np.zeros((V, V), bool)
    for i in range(F.shape[0]):
        deg |= np.abs(F[i].astype(np.int16) - KAP.astype(np.int16)).max(-1) > 3
    hx0, hy0, hx1, hy1 = kpo.kutu(deg)
    hx0, hy0, hx1, hy1 = max(hx0 - 8, 0), max(hy0 - 8, 0), min(hx1 + 8, V), min(hy1 + 8, V)
    cx0, cx1 = hx0 + ox, hx1 + ox; cy0, cy1 = hy0 + oy, hy1 + oy        # tuvalde
    O['hareket_kutusu_tuval'] = [cx0, cy0, cx1, cy1]
    kapi['hareket kutusu on yuz baskisi icinde ve tuvalde'] = cx0 >= 0 and cx1 <= W and kut['kupa (kulp dahil)'][1] <= cy0 and cy1 <= kut['kupa (kulp dahil)'][3]
    O['tasarim_motor_kutu_fark_max'] = int(np.abs(TON[cy0:cy1, cx0:cx1].astype(int) - KAP[hy0:hy1, hx0:hx1].astype(int)).max())
    kapi['tasarimdaki on yuz kutusu = motor karesi (max fark <= 2)'] = O['tasarim_motor_kutu_fark_max'] <= 2

    # ---------- 5. video
    VID = os.path.join(OUT, f'{CIFT}_tek_kupa_reel.mp4')
    pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '14', '-preset', 'slow',
                           '-profile:v', 'high', '-tag:v', 'avc1', '-movflags', '+faststart', VID], stdin=subprocess.PIPE)
    evre = []
    ease = lambda x: x * x * (3 - 2 * x)  # noqa: E731
    for i in range(TOPLAM):
        j = i - ONCE
        if i < ONCE:
            f = TON; evre.append('on tasarim')
        elif j < HAREKET:
            f = TON.copy(); f[cy0:cy1, cx0:cx1] = F[j][hy0:hy1, hx0:hx1]; evre.append(f'motor {j / FPS:.2f} sn')
        elif i < ONCE + HAREKET + GECIS:
            e = ease((i - ONCE - HAREKET + 1) / (GECIS + 1))
            f = np.clip(np.round(TON.astype(np.float32) * (1 - e) + TAR.astype(np.float32) * e), 0, 255).astype(np.uint8); evre.append(f'gecis {e:.2f}')
        else:
            f = TAR; evre.append('arka')
        pr.stdin.write(f.tobytes())
    pr.stdin.close(); pr.wait()
    if pr.returncode:
        raise SystemExit('kodlama hatasi')

    # ---------- 6. QC
    pf = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', VID],
                                   capture_output=True, text=True).stdout)
    vs = [x for x in pf['streams'] if x['codec_type'] == 'video'][0]
    d = O['dosya'] = {'boyut': f"{vs['width']}x{vs['height']}", 'codec': vs['codec_name'], 'profil': vs.get('profile'), 'pix_fmt': vs['pix_fmt'],
                      'fps': vs['r_frame_rate'], 'kare': int(vs['nb_read_frames']), 'sure': round(float(pf['format']['duration']), 3),
                      'ses_akisi': sum(x['codec_type'] == 'audio' for x in pf['streams']), 'mb': round(os.path.getsize(VID) / 1e6, 2), 'crf': 14}
    kapi['1080x1920, H.264, 30 fps, 240 kare, 8,0 sn, ses yok, crf 14'] = (d['boyut'] == '1080x1920' and d['codec'] == 'h264' and d['fps'] == '30/1'
                                                                         and d['kare'] == 240 and abs(d['sure'] - 8.0) < 0.05 and d['ses_akisi'] == 0)
    dis = np.ones((H, W), bool); dis[cy0:cy1, cx0:cx1] = False
    ort, sabit, hareket, ps, kontak = [], [], [], [], {}
    KT = [round(t * FPS) for t in np.arange(0, 8.0, 0.5)] + [TOPLAM - 1]
    k0 = kson = None
    for i, f in enumerate(kareler(VID, W, H)):
        ort.append(float(lum(f).mean()))
        if i == 0:
            k0 = f.copy()
        if i < ONCE + HAREKET:
            fd = np.abs(f.astype(np.int16) - k0.astype(np.int16)).max(-1)
            sabit.append(float(fd[dis].mean())); hareket.append(float((fd[~dis] > 20).mean()))
            j = i - ONCE
            if 0 <= j < HAREKET and j % 15 == 0:
                ps.append(psnr(f[cy0:cy1, cx0:cx1], F[j][hy0:hy1, hx0:hx1]))
        if i == TOPLAM - 1:
            kson = f.copy()
        if i in KT:
            kontak[i] = f.copy()
    O['ilk_kare_ncc'] = {'tum': round(ncc(lum(k0), lum(TON)), 5), 'on_yuz_kutu': round(ncc(lum(k0[cy0:cy1, cx0:cx1]), lum(TON[cy0:cy1, cx0:cx1])), 5),
                         'baslik': round(ncc(lum(k0[slice(kut['baslik'][1], kut['baslik'][3]), slice(kut['baslik'][0], kut['baslik'][2])]),
                                             lum(TON[slice(kut['baslik'][1], kut['baslik'][3]), slice(kut['baslik'][0], kut['baslik'][2])])), 5)}
    O['son_kare_arka_ncc'] = round(ncc(lum(kson), lum(TAR)), 5)
    kapi['ilk kare = tasarim (NCC >= 0,99: tum, on yuz, baslik); son kare = arka yuz (>= 0,99)'] = min(O['ilk_kare_ncc'].values()) >= 0.99 and O['son_kare_arka_ncc'] >= 0.99
    O['kare_ortalama_min'] = round(min(ort), 1)
    kapi['siyah kare yok (her kare ortalama >= 20)'] = len(ort) == 240 and min(ort) >= 20
    O['on_yuz_disi_sabit_fark_max_0_6sn'] = round(max(sabit), 3)
    kapi['0-6 sn baslik/plaka/zemin sabit (on yuz kutusu disi ortalama fark <= 0,5)'] = max(sabit) <= 0.5
    hk = [i for i, h_ in enumerate(hareket) if h_ > 0.001]
    O['hareket_sn'] = [round(hk[0] / FPS, 2), round(hk[-1] / FPS, 2)] if hk else []
    kapi['hareket yalniz 1-6 sn'] = bool(hk) and hk[0] >= ONCE and hk[-1] < ONCE + HAREKET
    O['on_yuz_motor_psnr_min'] = min(ps)
    O['mukerrep_not'] = 'murekkep tozun onune gecmez: video6b toz katmani her karede en ustte (f * (1 - a) + toz * a)'
    # arayuz / ortalama
    pay = lambda b: {'sag_918': SAG - b[2], 'ust_230': b[1] - UST, 'alt_1536': ALT_Y - b[3], 'sol_0': b[0]}  # noqa: E731
    kut_tum = dict(kut); kut_tum['kupa arka (kulp dahil)'] = kut_ar['kupa (kulp dahil)']
    O['kutular'] = kut_tum; O['paylar'] = {k_: pay(v_) for k_, v_ in kut_tum.items()}
    kapi['baslik, kupa (on/arka), plaka 230-1536 icinde ve tuvalde'] = all(
        p_['ust_230'] >= 0 and p_['alt_1536'] >= 0 and p_['sol_0'] >= 0 and kut_tum[k_][2] <= W for k_, p_ in O['paylar'].items())
    O['sag_918_bilgi'] = {k_: p_['sag_918'] for k_, p_ in O['paylar'].items()}
    gm = O['yerlesim']['govde_merkez_x']
    kapi['kupa govdesi yatayda ortali (merkez x 540 +- 1), baslik ve plaka ortali (+- 1)'] = (abs(gm - 540) <= 1
        and abs((kut['baslik'][0] + kut['baslik'][2]) / 2 - 540) <= 1 and abs((kut['plaka'][0] + kut['plaka'][2]) / 2 - 540) <= 1)
    ub_ = kut['baslik'][1] - UST; ab_ = ALT_Y - kut['plaka'][3]
    O['bosluk'] = {'ust (230 -> baslik)': ub_, 'alt (plaka -> 1536)': ab_}
    kapi['ust ve alt bosluk dengeli (fark <= 3 px)'] = abs(ub_ - ab_) <= 3
    # ek yeri + dikey cizgi: referans sahnenin kendi bandi (ust duvar, alt zemin/masa)
    ek, dc = {}, {}
    for ad_t, T_, (ya, yb) in (('on', ham_on, ek_on),):
        l0 = lum(T_.astype(np.float32)); dv = np.abs(np.diff(l0, axis=0)).mean(1)
        hp = l0 - cv2.GaussianBlur(l0, (0, 0), sigmaX=20, sigmaY=0.01)
        for ad, s_, b0, b1 in (('ust', ya, ya + 4, min(ya + 150, kut['kupa (kulp dahil)'][1] - 40)), ('alt', yb, max(yb - 150, kut['kupa (kulp dahil)'][3] + 60), yb - 4)):
            if (ad == 'ust' and ya <= 0) or (ad == 'alt' and yb >= H):
                continue
            p_ = l0.mean(1)
            yA = np.arange(s_ - 24, s_); yB = np.arange(s_, s_ + 24)
            fa = np.polyfit(yA, p_[yA], 1); fb = np.polyfit(yB, p_[yB], 1)
            sic = float(np.polyval(fb, s_ - 0.5) - np.polyval(fa, s_ - 0.5))
            oran = float(dv[s_ - 1] / np.median(np.r_[dv[s_ - 20:s_ - 2], dv[s_ + 1:s_ + 19]]))
            dog = []
            for y in range(b0 + 2, b1 - 2):
                kom = np.r_[dv[max(b0, y - 20):y - 2], dv[y + 1:min(b1, y + 19)]]
                if len(kom) >= 10:
                    dog.append(float(dv[y - 1] / np.median(kom)))
            esik = max(1.5, max(dog)) if dog else 1.5
            uz = hp[0:ya, 30:W - 30] if ad == 'ust' else hp[yb:H, 30:W - 30]
            ref = hp[b0:b1, 30:W - 30]
            ek[ad] = {'y': int(s_), 'sicrama': round(sic, 3), 'ek_satiri_orani': round(oran, 3), 'esik': round(esik, 3), 'referans_satir': len(dog)}
            dc[ad] = {'uzatma': round(float(uz.mean(0).std()), 3), 'kendi_zemini': round(float(ref.mean(0).std()), 3)}
    O['ek_yeri'] = ek; O['dikey_cizgi'] = dc
    kapi['ek yeri temiz (sicrama < 1,0; ek satiri orani <= max(1,5, kendi zemininin en buyuk orani))'] = all(
        abs(e['sicrama']) < 1.0 and e['ek_satiri_orani'] <= e['esik'] for e in ek.values())
    kapi['uzatmada dikey cizgi yok (sutun ortalamasi std <= 1,5 x kendi zemini)'] = all(
        v['uzatma'] <= 1.5 * max(v['kendi_zemini'], 0.05) for v in dc.values())

    # ---------- 7. gorseller
    try:
        fk = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except OSError:
        fk = ImageFont.load_default()
    im = Image.fromarray(k0).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for r in ((0, 0, W, UST), (0, ALT_Y, W, H), (SAG, UST, W, ALT_Y)):
        dr.rectangle(r, fill=(255, 0, 0, 60))
    dr.line((540, UST, 540, ALT_Y), fill=(0, 0, 255, 160), width=1)
    renk = {'baslik': (0, 170, 0, 255), 'plaka': (0, 160, 230, 255), 'plaka_yazisi': (0, 90, 255, 255),
            'kupa (kulp dahil)': (255, 140, 0, 255), 'kupa arka (kulp dahil)': (200, 0, 200, 255)}
    for k_, b in kut_tum.items():
        dr.rectangle(b, outline=renk[k_], width=3)
    dr.rectangle((cx0, cy0, cx1, cy1), outline=(255, 255, 0, 255), width=2)
    for y in (ek_on[0], ek_on[1]):
        if 0 < y < H:
            dr.line((0, y, 24, y), fill=(0, 0, 0, 200), width=2); dr.line((W - 24, y, W, y), fill=(0, 0, 0, 200), width=2)
    im = Image.alpha_composite(im, ov).convert('RGB'); dr = ImageDraw.Draw(im)
    dr.text((20, 20), f'{CIFT} ilk kare | arayuz ust {UST}, alt {ALT_Y}, sag {SAG} (kirmizi, sag yalniz bilgi); mavi x 540', font=fk, fill=(0, 0, 0))
    for n, (k_, b) in enumerate(kut_tum.items()):
        dr.text((20, 48 + 24 * n), f"{k_}: {b} sag 918 pay {O['paylar'][k_]['sag_918']}", font=fk, fill=renk[k_][:3])
    dr.text((20, 48 + 24 * len(kut_tum)), f'sari: hareket kutusu {O["hareket_kutusu_tuval"]}; olcek {s:.4f} (V {V})', font=fk, fill=(120, 110, 0))
    im.save(os.path.join(OUT, 'ILK_KARE_ARAYUZ.jpg'), quality=92)
    TW, TH = 270, 480
    sh = Image.new('RGB', (20 + 6 * (TW + 14), 20 + 3 * (TH + 50)), 'white'); dr = ImageDraw.Draw(sh)
    for n, i in enumerate(KT):
        x, y = 20 + (n % 6) * (TW + 14), 20 + (n // 6) * (TH + 50)
        sh.paste(Image.fromarray(kontak[i]).resize((TW, TH), Image.LANCZOS), (x, y + 34))
        dr.text((x, y + 4), f'{i / FPS:.2f} sn  {evre[i]}', font=fk, fill=(20, 20, 20))
    sh.save(os.path.join(OUT, 'KONTAK_0_8SN.jpg'), quality=90)

    # ---------- 8. rapor
    gecti = all(kapi.values())
    O['kapilar'] = kapi; O['sonuc'] = 'PASS' if gecti else 'FAIL'; O['sure_sn'] = round(time.time() - t0)
    json.dump(O, open(os.path.join(OUT, 'OLCUM.json'), 'w'), indent=1, default=str)
    tz = turlar[-1]
    sat = [f'TEK KUPA 9:16 SOSYAL VIDEO ORNEGI {CIFT}: {O["sonuc"]} (Metricool/Etsy yazma 0, toplu uretim 0)',
           f"dosya: {d['boyut']} {d['codec']} {d['profil']} {d['pix_fmt']} {d['fps']} fps, {d['kare']} kare, {d['sure']} sn, ses akisi {d['ses_akisi']}, crf 14, {d['mb']} MB",
           f"kaynak: kupa-orchard tek kupa on/arka (Orange Blossom) + cift.py baskilari, kapak_canva3 giydirme; esitle.py: buyutulen {ad_b}, olcek {s_e:.5f}, esitle.py ciktisi ile ort fark {O['esitle']['esitle_py_ciktisi_ile_ort_fark']}",
           f"olcek {s:.5f} (V {V}; sinir genislik {O['olcek']['sinir_genislik']}, yukseklik {O['olcek']['sinir_yukseklik']}; upscale yok); govde merkezi x {gm}",
           f"zaman: 0-1 sn on tasarim, 1-6 sn motor 0-5 sn (yalniz on yuz kutusu {O['hareket_kutusu_tuval']}), 6,0-6,4 sn gecis, 6,4-8 sn arka; olculen hareket {O['hareket_sn']} sn",
           f"motor: video6b V6 sigma 0,45, N {tz['N']} (N1 = 10400 x {bol_t} / {bol_k} = {N1}; tur {len(turlar)}), V {V}; bos mesaj maskesi korumasi (cikti ayni); {O['mukerrep_not']}",
           'toz 2-4 sn (alan basina; tek kupa / ref / fark %): ' + '; '.join(f"{t_} sn {v['tek_kupa']} / {v['kupa_ref']} / {v['fark_yuzde']}" for t_, v in tz['toz_2_4sn'].items()),
           f"ilk kare NCC {O['ilk_kare_ncc']}; son kare arka NCC {O['son_kare_arka_ncc']}; siyah kare: ortalama en az {O['kare_ortalama_min']}",
           f"on yuz / motor PSNR en az {O['on_yuz_motor_psnr_min']} dB (bilgi); 0-6 sn kutu disi sabit fark en cok {O['on_yuz_disi_sabit_fark_max_0_6sn']}",
           'yerlesim: ' + '; '.join(f"{k_} {b}" for k_, b in kut_tum.items()) + f"; bosluk {O['bosluk']}",
           'sag 918 (yalniz bilgi): ' + '; '.join(f"{k_} {v_}" for k_, v_ in O['sag_918_bilgi'].items()),
           'ek yeri: ' + '; '.join(f"{a_} y {e['y']} sicrama {e['sicrama']}, oran {e['ek_satiri_orani']} (esik {e['esik']}, kendi zemini {e['referans_satir']} satir)" for a_, e in ek.items()),
           f"dikey cizgi (sutun ortalamasi std): {dc}",
           'KAPILAR: ' + '; '.join(f"{'PASS' if v else 'FAIL'} {k_}" for k_, v in kapi.items()),
           f"sure {O['sure_sn']} sn"]
    open(os.path.join(OUT, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    sys.exit(0 if gecti else 1)


if __name__ == '__main__':
    main()
