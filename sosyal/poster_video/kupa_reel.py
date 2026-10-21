#!/usr/bin/env python3
"""Kupa 9:16 sosyal video ORNEGI (20 Eki 2026, Serdar; yalniz CANCER_LIBRA): uretim + QC, tek script, PASS/FAIL. Yazma yok.

Gorunum: onayli kupa pini S3 (kupa_pin_78.py, kupa_pin_secenek.py e94127d8 S3 yolu) ayni adimlarla kapak olceginde (2048)
yeniden kurulur: eski baslik stil sahnesiyle silinir, ust duvar yansitmali uzar, masa +62 satir, baslik CANCER / & / LIBRA
(Cinzel 650) ayni yerde. Olcek 1080 / 2048 = 0,52734 (Serdar karari A: kapak tam genislik; kupa ilan videosuyla ayni boy,
upscale yok). S3 bolgesinin ustu ve alti yd_reel.py (b11ec836) yontemiyle zeminin kendi pikselleriyle dikeyde uzar
(egim tau 60 px'te duzlesir + 48 px bloklarla doku; ust doku duvardan, alt doku masadan). Icerik (baslik ust - plaka alt)
arayuz bandi 230-1536 icinde ust ve alt bosluk esit. Sag arayuz alanina (x > 918) yalniz sag kupanin kulbu girebilir;
sag kupanin baskisi (mesaj + isimler + nazar boncugu) x <= 898 (pay >= 20) olmali (kulp istisnasi).
Hareket: onayli kupa ilan motoru video6b.py (kupa-orchard) V6 (N 10400, sigma 0,45; ilan78.py ile ayni iki degisiklik, baska
degisiklik yok), V 1080 = bu olcek; ffmpeg'e giden ham kareler (kayipsiz) ara katmanla kopyalanir. Yalniz kupa hareket kutusu
(motor karelerinin kapaktan farkli oldugu piksellerin kutusu + 8 px) ilan karesinden alinir; baslik, plaka, zemin sabit.
Zaman: 0-1 sn tasarim, 1-6 sn ilan 0-5 sn, 6-8 sn tasarim. 30 fps, 240 kare, ses yok, H.264 yuv420p crf 17.
Cikti: <CIFT>_kupa_reel.mp4, ILK_KARE_ARAYUZ.jpg, KONTAK_0_8SN.jpg, YAKIN_EK_200.jpg, OLCUM.txt, OLCUM.json
Kullanim: kupa_reel.py <kapak.jpg> <pin_S3.jpg> <katman_dizini (cift.py ciktisi)> <video6b.py> <sahne_dir> <Cinzel.ttf>
          <B1> <B2> <cikti> <is> [--onay_ilan ilan.mp4]"""
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
sp = importlib.util.spec_from_file_location('kp78', os.path.join(KOK, 'scripts', 'sosyal', 'kupa_pin_78.py'))
kp = importlib.util.module_from_spec(sp); sp.loader.exec_module(kp)
sp = importlib.util.spec_from_file_location('ydr', os.path.join(HERE, 'yd_reel.py'))
yd = importlib.util.module_from_spec(sp); sp.loader.exec_module(yd)
lum, ncc, psnr, kareler, SHIM = yd.lum, yd.ncc, yd.psnr, yd.kareler, yd.SHIM

W, H, FPS = 1080, 1920, 30
S = 2048
K = W / S                                   # 0,52734
UST, ALT_Y, SAG = 230, 1536, 918            # arayuz: ust bant, alt sinir, sag sinir
SAG_PAY = 20
ONCE, HAREKET, TOPLAM = 30, 150, 240
U = 512                                     # kapak ustu satir (256'nin kati: kapak satiri 0 -> 270, INTER_AREA motorla ayni)
TAU, BL, BS = yd.TAU, yd.BL, yd.BS
MASA_PAY = 12                               # kapak px: masa on kenari ~1980; S3 bolgesi 1963'te biter


def s3_buyuk(kapak, sahne_dir, font, b1, b2):
    """kupa_pin_78.is_ ile ayni S3 adimlari; donus: buyuk tuval (U ust satir), S3 bolgesi satirlari, baslik kutusu."""
    kp.init(sahne_dir, font, '')
    a0 = np.asarray(Image.open(kapak).convert('RGB')); f = a0.astype(float)
    st, _ = kp.stil_bul(a0); renk = kp.RENKLER[st]; sc = kp.G['sahne'][st].astype(float)
    koyu = np.abs(f - np.array(renk)).max(2) < 40; koyu[int(0.4 * S):] = False
    bk = kp.kutu(koyu)
    e = f.copy()
    e[bk[1] - 12:bk[3] + 12, bk[0] - 12:bk[2] + 12] = sc[bk[1] - 12:bk[3] + 12, bk[0] - 12:bk[2] + 12]
    s = kp.s; hedef = round(kp.H / s); alt = 2 * kp.MASA_H; ust = hedef - S - alt
    ustb = e[:kp.UST_BANT]
    band = e[kp.MASA_KES - kp.MASA_H:kp.MASA_KES]
    al = np.stack([band[kp.MASA_H - 1 - kp.tri(j, kp.MASA_H)] for j in range(alt)])
    us_s3 = np.stack([ustb[kp.tri(j, kp.UST_BANT)] for j in range(ust)])[::-1]
    big_s3 = np.concatenate([us_s3, e[:kp.MASA_KES], al, e[kp.MASA_KES:]])
    op, _ = kp.olcek(font, b1, b2, (kp.W - 2 * kp.PAY) / s - 2)
    tt = np.zeros((900, S, 3)); bn, _ = kp.baslik_ciz(tt, font, b1, b2, renk, y_ust=0, olcek=op); bh = (bn[3] - bn[1]) * s
    P0 = np.asarray(Image.fromarray(np.clip(np.rint(big_s3), 0, 255).astype(np.uint8)).resize((kp.W, kp.H), Image.LANCZOS)).astype(float)
    nt = (P0.min(2) > 150) & (P0.max(2) - P0.min(2) < 10)
    gv = nt[:, round(327 * s):round(1726 * s)].mean(1)
    yk = round(kp.KUPA_UST * s + ust * s) - 60
    kt = int(np.where(gv[yk:] > 0.3)[0].min()) + yk
    g = (kt - bh) / 2
    y_baslik = round(g / s)                          # S3 buyuk tuvalde
    assert ust <= U, ust
    # reel buyuk tuvali: ayni yansitma U satira kadar surer (S3 satirlari birebir), alt 256 katina tamamlanir
    us = np.stack([ustb[kp.tri(j, kp.UST_BANT)] for j in range(U)])[::-1]
    big = np.concatenate([us, e[:kp.MASA_KES], al, e[kp.MASA_KES:]])
    ek = (-big.shape[0]) % 256
    if ek:
        bb = big[-kp.MASA_H:]
        big = np.concatenate([big, np.stack([bb[kp.MASA_H - 1 - kp.tri(j, kp.MASA_H)] for j in range(ek)])])
    bt, _ = kp.baslik_ciz(big, font, b1, b2, renk, y_ust=y_baslik + (U - ust), olcek=op)
    kp.baslik_ciz(big_s3, font, b1, b2, renk, y_ust=y_baslik, olcek=op)
    pin_yeniden = Image.fromarray(np.clip(np.rint(big_s3), 0, 255).astype(np.uint8)).resize((kp.W, kp.H), Image.LANCZOS)
    return big, (U - ust, U - ust + hedef), bt, pin_yeniden, st


def uzat(A, temiz, n, ad):
    """yd_reel.uzat yontemi (b11ec836), yuksekligi W'den farkli bolge icin: ad 'ust' -> A'nin ust kenarindan n satir yukari,
    'alt' -> alt kenardan n satir asagi. Doku yalniz temiz maskeli piksellerden (ust: duvar, alt: masa)."""
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
                kay = HF[0:hh] if ad == 'ust' else HF[h - 1:h - 1 - hh:-1]
                blok = kay[:, x_a:x_b]
            else:
                j = rng.integers(len(cy)); sy, sx = cy[j], cx[j]
                blok = HF[sy:sy + hh, sx:sx + (x_b - x_a)]
                if blok.shape[1] < x_b - x_a:
                    blok = np.pad(blok, ((0, 0), (0, x_b - x_a - blok.shape[1]), (0, 0)), mode='reflect')
            w2 = (wy[:, None] * wx[None, :])[..., None]
            num[yb:yb + hh, x_a:x_b] += w2 * blok; den[yb:yb + hh, x_a:x_b] += w2 * w2
    b = lf + num / np.sqrt(np.maximum(den, 1e-6))
    return (b[::-1] if ad == 'ust' else b), float(egim.mean())


def motor(v6b, katman, kapak, is_dir):
    """video6b V6 (ilan78.py ile ayni iki degisiklik), ham kareler ara katmanla."""
    src = open(v6b).read()
    assert src.count('N = 5200 ') == 1 and src.count('(0, 0), 0.9)') == 2 and src.count('V, FPS, SURE, SILME = 1080, 30, 6.0, 0.3') == 1
    v6k = src.replace('N = 5200 ', 'N = 10400', 1).replace('GaussianBlur(al, (0, 0), 0.9)', 'GaussianBlur(al, (0, 0), 0.45)') \
        .replace('GaussianBlur(kat, (0, 0), 0.9)', 'GaussianBlur(kat, (0, 0), 0.45)')
    k6 = os.path.join(is_dir, 'video6b_v6.py'); open(k6, 'w').write(v6k)
    shim = os.path.join(is_dir, 'shim'); os.makedirs(shim, exist_ok=True)
    yol = os.path.join(shim, 'ffmpeg'); open(yol, 'w').write(SHIM); os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    raw = os.path.join(is_dir, 'ilan.rgb'); mp4 = os.path.join(is_dir, 'ilan.mp4')
    env = dict(os.environ, YD_RAW=raw, YD_FFMPEG=subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True).stdout.strip(),
               PATH=shim + os.pathsep + os.environ['PATH'])
    r = subprocess.run([sys.executable, '-I', k6, os.path.join(katman, 'video') + '/', kapak, mp4], env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(r.stdout[-800:], flush=True)
    if r.returncode:
        raise SystemExit('ilan videosu uretilemedi')
    n = os.path.getsize(raw) // (W * W * 3)
    return np.memmap(raw, np.uint8, 'r', shape=(n, W, W, 3)), mp4


def main():
    a = sys.argv[1:]
    onay = None
    if '--onay_ilan' in a:
        i = a.index('--onay_ilan'); onay = a[i + 1]; del a[i:i + 2]
    KAPAK, PIN, KAT, V6B, SAHNE, FONT, B1, B2, OUT, IS = a
    CIFT = f'{B1}_{B2}'
    os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
    t0 = time.time()
    O, kapi = {'olcek_kapak_reel': round(K, 5)}, {}

    # ---------- 1. S3 tasarimi (kapak olcegi) ve reel olcegi
    big, (s0, s1), bt, pin_yeni, stil = s3_buyuk(KAPAK, SAHNE, FONT, B1, B2)
    pin = np.asarray(Image.open(PIN).convert('RGB'))
    O['s3_yeniden_kurulum_pin_ncc'] = round(ncc(lum(np.asarray(pin_yeni)), lum(pin)), 5)
    O['stil'] = stil
    kapi['S3 ayni adimlarla yeniden kuruldu (Drive pini ile NCC >= 0,995)'] = O['s3_yeniden_kurulum_pin_ncc'] >= 0.995
    hb = big.shape[0]; hr = hb * W // S
    assert hr * S == hb * W
    R = np.clip(np.round(cv2.resize(big.astype(np.float32), (W, hr), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
    ky = U * W // S                                               # kapak satiri 0 (270)
    r0 = int(np.ceil(s0 * K))                                     # S3 bolgesi ustu (reel olcek, tam satir)
    r1 = int(np.floor((U + kp.MASA_KES - MASA_PAY) * K))           # alt: masa on kenarindan once (kenar + altindaki koyu bant uzatilmaz)
    # icerik: baslik ust (bt) .. plaka alt
    bt_r = (bt[0] * K, bt[1] * K, bt[2] * K, bt[3] * K)
    pl = kp.PLAKA; pl_r = (pl[0] * K, (pl[1] + U) * K, pl[2] * K, (pl[3] + U) * K)
    ct, cb = bt_r[1], pl_r[3]
    Yb = int(round((UST + ALT_Y - ct - cb) / 2))
    O['yerlesim'] = {'Yb': Yb, 's3_reel_satir': [Yb + r0, Yb + r1], 'kapak_satir0': Yb + ky}

    # ---------- 2. onayli motor (V6), ham kareler
    F, ilan_mp4 = motor(V6B, KAT, KAPAK, IS)
    O['ilan_kare'] = int(F.shape[0])
    KAP = np.array(F[0])
    kf = np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32)
    KAPr = np.clip(np.round(cv2.resize(kf, (W, W), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
    O['ilan_kare0_kapak_fark'] = int(np.abs(KAP.astype(int) - KAPr.astype(int)).max())
    kapi['ilan 180 kare; ilk/son kare = kapak (olcek 0,52734)'] = (F.shape[0] == 180 and O['ilan_kare0_kapak_fark'] == 0
                                                                 and int(np.abs(F[-1].astype(int) - KAP.astype(int)).max()) == 0)
    deg = np.zeros((W, W), bool)
    for i in range(F.shape[0]):
        deg |= np.abs(F[i].astype(np.int16) - KAP.astype(np.int16)).max(-1) > 3   # motorun uint8 kesmesi (<= 1-2) disi
    hx0, hy0, hx1, hy1 = kp.kutu(deg)
    hx0, hy0, hx1, hy1 = max(hx0 - 8, 0), max(hy0 - 8, 0), min(hx1 + 8, W), min(hy1 + 8, W)
    O['hareket_kutusu_kapak'] = [hx0, hy0, hx1, hy1]
    tas_kutu = R[ky + hy0:ky + hy1, hx0:hx1].astype(int); mot_kutu = KAP[hy0:hy1, hx0:hx1].astype(int)
    O['tasarim_motor_kutu_fark_max'] = int(np.abs(tas_kutu - mot_kutu).max())
    O['tasarim_motor_kutu_fark_ort'] = round(float(np.abs(tas_kutu - mot_kutu).mean()), 4)
    kapi['tasarimdaki kupa kutusu = motor kapak karesi (max fark <= 2)'] = O['tasarim_motor_kutu_fark_max'] <= 2

    # ---------- 3. 9:16 tasarim: S3 bolgesi + zemin uzatma (ust duvar, alt masa)
    A = R[r0:r1].astype(np.float32); ha = A.shape[0]
    by0r, by1r = int(bt_r[1]) - r0, int(np.ceil(bt_r[3])) - r0
    ku_ust = int(kp.KUPA_UST * K) + ky - r0
    t_ust = np.zeros((ha, W), bool); t_ust[:ku_ust - 20] = True
    t_ust[max(by0r - 20, 0):by1r + 20, int(bt_r[0]) - 20:int(bt_r[2]) + 20] = False
    t_alt = np.zeros((ha, W), bool); t_alt[int(np.ceil(pl_r[3])) - r0 + 4:] = True          # masa: plaka alti
    t_alt[int(pl_r[1]) - r0:, :max(int(pl_r[0]) - 10, 0)] = True; t_alt[int(pl_r[1]) - r0:, int(np.ceil(pl_r[2])) + 10:] = True   # plaka yanlari
    n_ust, n_alt = Yb + r0, H - (Yb + r1)
    assert n_ust > 0 and n_alt > 0, (n_ust, n_alt)
    ub, eg_u = uzat(A, t_ust, n_ust, 'ust')
    ab, eg_a = uzat(A, t_alt, n_alt, 'alt')
    T = np.concatenate([ub, A, ab])
    assert T.shape[0] == H
    T8 = np.clip(np.round(T), 0, 255).astype(np.uint8)
    Image.fromarray(T8).save(os.path.join(IS, 'tasarim.png'))
    oy = Yb + ky                                                  # reelde kapak satiri 0

    # ---------- 4. video
    V = os.path.join(OUT, f'{CIFT}_kupa_reel.mp4')
    pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow',
                           '-profile:v', 'high', '-tag:v', 'avc1', '-movflags', '+faststart', V], stdin=subprocess.PIPE)
    kaynak = []
    for i in range(TOPLAM):
        j = i - ONCE
        if 0 <= j < HAREKET:
            f = T8.copy(); f[oy + hy0:oy + hy1, hx0:hx1] = F[j][hy0:hy1, hx0:hx1]; kaynak.append(j)
        else:
            f = T8; kaynak.append(-1)
        pr.stdin.write(f.tobytes())
    pr.stdin.close(); pr.wait()
    if pr.returncode:
        raise SystemExit('kodlama hatasi')

    # ---------- 5. QC dosya
    pf = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', V],
                                   capture_output=True, text=True).stdout)
    vs = [s for s in pf['streams'] if s['codec_type'] == 'video'][0]
    d = O['dosya'] = {'boyut': f"{vs['width']}x{vs['height']}", 'codec': vs['codec_name'], 'profil': vs.get('profile'), 'pix_fmt': vs['pix_fmt'],
                      'fps': vs['r_frame_rate'], 'kare': int(vs['nb_read_frames']), 'sure': round(float(pf['format']['duration']), 3),
                      'ses_akisi': sum(s['codec_type'] == 'audio' for s in pf['streams']), 'mb': round(os.path.getsize(V) / 1e6, 2)}
    kapi['1080x1920, H.264, 30 fps, 240 kare, 8,0 sn, ses yok'] = (d['boyut'] == '1080x1920' and d['codec'] == 'h264' and d['fps'] == '30/1'
                                                                 and d['kare'] == 240 and abs(d['sure'] - 8.0) < 0.05 and d['ses_akisi'] == 0)

    # ---------- 6. QC kareler
    ilan_onay = {j: f.copy() for j, f in enumerate(kareler(onay, W, W)) if j % 15 == 0} if onay else None
    ort, sabit_fark, hareket, ps_ilan, ps_onay, kontak = [], [], [], [], [], {}
    KT = [round(t * FPS) for t in np.arange(0, 8.0, 0.5)] + [TOPLAM - 1]
    dis = np.ones((H, W), bool); dis[oy + hy0:oy + hy1, hx0:hx1] = False
    k0 = None
    for i, f in enumerate(kareler(V, W, H)):
        ort.append(float(lum(f).mean()))
        if i == 0:
            k0 = f.copy()
        fd = np.abs(f.astype(np.int16) - k0.astype(np.int16)).max(-1)
        sabit_fark.append(float(fd[dis].mean())); hareket.append(float((fd[~dis] > 20).mean()))
        j = kaynak[i]
        if j >= 0 and j % 15 == 0:
            ps_ilan.append(psnr(f[oy + hy0:oy + hy1, hx0:hx1], F[j][hy0:hy1, hx0:hx1]))
            if ilan_onay is not None and j in ilan_onay:
                ps_onay.append(psnr(f[oy + hy0:oy + hy1, hx0:hx1], ilan_onay[j][hy0:hy1, hx0:hx1]))
        if i in KT:
            kontak[i] = f.copy()
    O['kare_ortalama_min'] = round(min(ort), 1)
    kapi['siyah kare yok (her kare ortalama >= 20)'] = len(ort) == 240 and min(ort) >= 20
    O['kupa_disi_sabit_fark_max'] = round(max(sabit_fark), 3)
    kapi['baslik/plaka/zemin sabit (kupa kutusu disi ortalama fark <= 0,5)'] = max(sabit_fark) <= 0.5
    hk = [i for i, h in enumerate(hareket) if h > 0.001]
    O['hareket_sn'] = [round(hk[0] / FPS, 2), round(hk[-1] / FPS, 2)] if hk else []
    kapi['hareket yalniz 1-6 sn, 0-1 ve 6-8 sn tam tasarim'] = bool(hk) and hk[0] >= ONCE and hk[-1] < ONCE + HAREKET
    O['kupa_ilan_psnr_min'] = min(ps_ilan)
    kapi['kupa bolgesi motor kareleriyle ayni (PSNR >= 35)'] = min(ps_ilan) >= 35
    if ps_onay:
        O['kupa_onayli_ilan_mp4_psnr_min'] = min(ps_onay)
        kapi['kupa bolgesi Drive onayli kupa ilan mp4 ile ayni (PSNR >= 35)'] = min(ps_onay) >= 35

    # ilk kare = S3 tasarimi (pin): pin reel olcegine (x 1,08) ve alt piksel kaydirmayla
    o = (S / kp.W) * K                                            # pin px -> reel px (1,08)
    pr_ = cv2.resize(pin.astype(np.float32), (W, round(kp.H * o)), interpolation=cv2.INTER_CUBIC)
    y_pin0 = Yb + s0 * K                                          # pinin ust kenari reelde (kesirli)
    tam = int(np.ceil(y_pin0)); kay = tam - y_pin0
    pr_ = cv2.warpAffine(pr_, np.float32([[1, 0, 0], [0, 1, -kay]]), (W, pr_.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    n_s = min(pr_.shape[0] - 2, Yb + r1 - tam)
    g0, gp = lum(k0), lum(np.clip(pr_, 0, 255))
    reg = lambda y0, y1, x0, x1: ncc(g0[tam + y0:tam + y1, x0:x1], gp[y0:y1, x0:x1])  # noqa: E731
    yo = lambda y: int(round(y + Yb - tam))  # noqa: E731  reel R satiri -> pin_r satiri
    O['ilk_kare_ncc'] = {'tum_S3': round(reg(2, n_s, 0, W), 5),
                         'baslik': round(reg(yo(bt_r[1]) - 4, yo(bt_r[3]) + 4, int(bt_r[0]) - 4, int(bt_r[2]) + 4), 5),
                         'kupa': round(reg(yo(kp.KUPA_UST * K + ky), yo(kp.KUPA_ALT * K + ky), 0, W), 5),
                         'plaka': round(reg(yo(pl_r[1]), yo(pl_r[3]), int(pl_r[0]), int(pl_r[2])), 5)}
    kapi['ilk kare = S3 tasarimi (NCC >= 0,99: tum, baslik, kupa, plaka)'] = min(O['ilk_kare_ncc'].values()) >= 0.99 and ort[0] >= 20

    # arayuz: kutular (reel koordinat)
    kk = KAP.astype(np.float32)
    beyaz = (kk.min(2) > 215) & (kk.max(2) - kk.min(2) < 14)
    by_ = np.where(beyaz.mean(1) > 0.05)[0]; ky0, ky1 = int(by_.min()), int(by_.max())
    sat = beyaz[ky0 + 40:ky1 - 40]
    sag_govde = np.where(sat[:, W // 2:].mean(0) > 0.5)[0] + W // 2
    gr = sag_govde[np.concatenate([[True], np.diff(sag_govde) == 1])] if len(sag_govde) else sag_govde
    gx1 = int(sag_govde[0]);
    for x in sag_govde[1:]:
        if x == gx1 + 1:
            gx1 = int(x)
        else:
            break
    tum_kupa = np.where(beyaz[ky0:ky1].sum(0) > 20)[0]
    mm = np.clip((1 - cv2.resize(np.asarray(Image.open(os.path.join(KAT, 'video', 'k_mask_nomes.png')).convert('RGB')).astype(np.float32),
                                 (W, W), interpolation=cv2.INTER_AREA).mean(-1)
                  / np.maximum(cv2.resize(np.asarray(Image.open(os.path.join(KAT, 'video', 'k_beyaz.png')).convert('RGB')).astype(np.float32),
                                          (W, W), interpolation=cv2.INTER_AREA).mean(-1), 1)) * 1.4, 0, 1)
    mx0, my0, mx1, my1 = kp.kutu(mm > 0.2)
    murek = (kk.max(2) < 110) & (kk.min(2) < 70)
    # isimler: mesajin altindaki ilk murekkep satir bandi (mesaj sutunlari icinde)
    p = murek[:, mx0:mx1].sum(1); y = my1 + 1
    while y < ky1 and p[y] == 0:
        y += 1
    ny0 = y
    while y < ky1 and p[y] > 0:
        y += 1
    ny1 = y
    nb = kp.kutu(murek[ny0:ny1, mx0:mx1]) if ny1 > ny0 else (0, 0, 0, 0)
    mavi = (kk[..., 2] - kk[..., 0] > 60); mavi[:, :W // 2] = False; mavi[:ky0] = False; mavi[ky1:] = False
    nz = kp.kutu(mavi)
    mes = kp.kutu(murek[my0:my1, mx0:mx1] | (mm[my0:my1, mx0:mx1] > 0.2))
    sag_baski = (min(mes[0] + mx0, nb[0] + mx0, nz[0]), min(mes[1] + my0, nz[1]),
                 max(mes[2] + mx0, nb[2] + mx0, nz[2]), max(ny1, nz[3]))
    kutu_r = lambda b, ofs=oy: (int(b[0]), int(b[1] + ofs), int(b[2]), int(b[3] + ofs))  # noqa: E731
    kut = {'baslik': (int(bt_r[0]), int(bt_r[1]) + Yb, int(np.ceil(bt_r[2])), int(np.ceil(bt_r[3])) + Yb),
           'plaka': (int(pl_r[0]), int(pl_r[1]) + Yb, int(np.ceil(pl_r[2])), int(np.ceil(pl_r[3])) + Yb),
           'sag_kupa_baski (mesaj+isim+nazar)': kutu_r(sag_baski),
           'sag_kupa_govde (kulp haric)': kutu_r((int(gr[0]) if len(gr) else 0, ky0, gx1 + 1, ky1)),
           'kupalar (kulp dahil)': kutu_r((int(tum_kupa.min()), ky0, int(tum_kupa.max()) + 1, ky1))}
    O['kutular'] = kut
    pay = lambda b: {'sag_918': SAG - b[2], 'ust_230': b[1] - UST, 'alt_1536': ALT_Y - b[3], 'sol_0': b[0]}  # noqa: E731
    O['paylar'] = {k_: pay(v_) for k_, v_ in kut.items()}
    # plaka yazisi (PERSONALIZED GIFT MUG murekkebi)
    pz = k0[kut['plaka'][1]:kut['plaka'][3], kut['plaka'][0]:kut['plaka'][2]].astype(np.float32)
    pyz = kp.kutu((pz.max(2) < 90))
    kut['plaka_yazisi'] = (kut['plaka'][0] + pyz[0], kut['plaka'][1] + pyz[1], kut['plaka'][0] + pyz[2], kut['plaka'][1] + pyz[3])
    O['paylar']['plaka_yazisi'] = pay(kut['plaka_yazisi'])
    O['plaka_istisnasi'] = {'zemin_arayuze_giris_px': max(0, kut['plaka'][2] - SAG), 'yazi_sag_pay': O['paylar']['plaka_yazisi']['sag_918']}
    kapi['PLAKA ISTISNASI (Serdar A): plaka zemini arayuze <= 11 px, yazi sag pay >= 16, dikey 230-1536 icinde'] = (
        O['plaka_istisnasi']['zemin_arayuze_giris_px'] <= 11 and O['plaka_istisnasi']['yazi_sag_pay'] >= 16
        and O['paylar']['plaka']['ust_230'] >= 0 and O['paylar']['plaka']['alt_1536'] >= 0)
    icerik = ['baslik', 'sag_kupa_baski (mesaj+isim+nazar)']
    kapi['baslik ve sag kupa baskisi: sag pay >= 20 (x <= 898), dikey 230-1536 icinde'] = all(
        O['paylar'][k_]['sag_918'] >= SAG_PAY and O['paylar'][k_]['ust_230'] >= 0 and O['paylar'][k_]['alt_1536'] >= 0 for k_ in icerik)
    kapi['KULP ISTISNASI: x > 918 alanina giren kupa pikseli yalniz sag kulp (govde <= 918), kupalar dikey 230-1536 icinde'] = (
        O['paylar']['sag_kupa_govde (kulp haric)']['sag_918'] >= 0 and O['paylar']['kupalar (kulp dahil)']['ust_230'] >= 0
        and O['paylar']['kupalar (kulp dahil)']['alt_1536'] >= 0)
    O['sag_kulp_arayuze_giris_px'] = max(0, kut['kupalar (kulp dahil)'][2] - SAG)
    ub_ = kut['baslik'][1] - UST; ab_ = ALT_Y - kut['plaka'][3]
    O['bosluk'] = {'ust (230 -> baslik)': ub_, 'alt (plaka -> 1536)': ab_}
    kapi['ust ve alt bosluk dengeli (fark <= 3 px)'] = abs(ub_ - ab_) <= 3

    # ek yeri + dikey cizgi (yd_reel olcumu)
    l0 = lum(k0.astype(np.float32))
    dv = np.abs(np.diff(l0, axis=0)).mean(1)
    ek = {}
    for ad, s in (('ust', Yb + r0), ('alt', Yb + r1)):
        p_ = l0.mean(1)
        ya = np.arange(s - 24, s); yb_ = np.arange(s, s + 24)
        fa = np.polyfit(ya, p_[ya], 1); fb = np.polyfit(yb_, p_[yb_], 1)
        sic = float(np.polyval(fb, s - 0.5) - np.polyval(fa, s - 0.5))
        oran = float(dv[s - 1] / np.median(np.r_[dv[s - 20:s - 2], dv[s + 1:s + 19]]))
        ek[ad] = {'y': int(s), 'sicrama': round(sic, 3), 'ek_satiri_fark_orani': round(oran, 3)}
    O['ek_yeri'] = ek
    hp = l0 - cv2.GaussianBlur(l0, (0, 0), sigmaX=20, sigmaY=0.01)
    su = Yb + r0; sa = Yb + r1
    ref_u = float(hp[su + 10:su + 10 + min(n_ust, 200), 30:W - 30].mean(0).std())       # S3 bolgesinin ust duvari
    tb0 = int(np.ceil(pl_r[3])) + Yb + 10
    ref_a = float(hp[tb0:sa, 30:W - 30].mean(0).std()) if sa - tb0 > 40 else ref_u     # plaka alti masa
    O['dikey_cizgi'] = {'ust': round(float(hp[0:su, 30:W - 30].mean(0).std()), 3), 'ust_ref_duvar': round(ref_u, 3),
                        'alt': round(float(hp[sa:H, 30:W - 30].mean(0).std()), 3), 'alt_ref_masa': round(ref_a, 3)}
    kapi['uzatmada dikey cizgi yok (sutun ortalamasi std <= 1,5 x kendi zemini)'] = (
        O['dikey_cizgi']['ust'] <= 1.5 * max(ref_u, 0.05) and O['dikey_cizgi']['alt'] <= 1.5 * max(ref_a, 0.05))
    kapi['ek yeri gorunmuyor (sicrama < 1,0; ek satiri <= 1,5x komsu)'] = all(abs(e['sicrama']) < 1.0 and e['ek_satiri_fark_orani'] <= 1.5 for e in ek.values())
    kapi['olcek <= 1 (kapak 2048 -> 1080, upscale yok)'] = K <= 1

    # ---------- 7. gorseller
    try:
        fk = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except OSError:
        fk = ImageFont.load_default()
    im = Image.fromarray(k0).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for r in ((0, 0, W, UST), (0, ALT_Y, W, H), (SAG, UST, W, ALT_Y)):
        dr.rectangle(r, fill=(255, 0, 0, 70))
    dr.line((SAG - SAG_PAY, UST, SAG - SAG_PAY, ALT_Y), fill=(255, 255, 0, 255), width=2)
    renk = {'baslik': (0, 255, 0, 255), 'plaka': (0, 200, 255, 255), 'sag_kupa_baski (mesaj+isim+nazar)': (255, 0, 255, 255),
            'sag_kupa_govde (kulp haric)': (255, 160, 0, 255), 'kupalar (kulp dahil)': (255, 255, 255, 200), 'plaka_yazisi': (0, 120, 255, 255)}
    for k_, b in kut.items():
        dr.rectangle(b, outline=renk[k_], width=3)
    for s in (Yb + r0, Yb + r1):
        dr.line((0, s, 24, s), fill=(255, 255, 255, 220), width=2); dr.line((W - 24, s, W, s), fill=(255, 255, 255, 220), width=2)
    im = Image.alpha_composite(im, ov).convert('RGB'); dr = ImageDraw.Draw(im)
    dr.text((20, 20), f'{CIFT} ilk kare | arayuz ust {UST}, alt {ALT_Y}, sag {SAG} (kirmizi); sari cizgi x {SAG - SAG_PAY}', font=fk, fill=(0, 0, 0))
    for n, (k_, b) in enumerate(kut.items()):
        dr.text((20, 50 + 26 * n), f"{k_}: {b} sag pay {O['paylar'][k_]['sag_918']}", font=fk, fill=renk[k_][:3] if k_ != 'kupalar (kulp dahil)' else (60, 60, 60))
    dr.text((20, H - 60), f'ek yeri y {Yb + r0} ve {Yb + r1} (beyaz cizgi); kulp istisnasi: sag kulp {O["sag_kulp_arayuze_giris_px"]} px', font=fk, fill=(0, 0, 0))
    im.save(os.path.join(OUT, 'ILK_KARE_ARAYUZ.jpg'), quality=92)
    TW, TH = 270, 480
    sh = Image.new('RGB', (20 + 6 * (TW + 14), 20 + 3 * (TH + 50)), 'white'); dr = ImageDraw.Draw(sh)
    for n, i in enumerate(KT):
        x, y = 20 + (n % 6) * (TW + 14), 20 + (n // 6) * (TH + 50)
        sh.paste(Image.fromarray(kontak[i]).resize((TW, TH), Image.LANCZOS), (x, y + 34))
        dr.text((x, y + 4), f"{i / FPS:.2f} sn  {'tam tasarim' if kaynak[i] < 0 else f'ilan {kaynak[i] / FPS:.2f} sn'}", font=fk, fill=(20, 20, 20))
    sh.save(os.path.join(OUT, 'KONTAK_0_8SN.jpg'), quality=90)
    yk = Image.new('RGB', (1080, 2 * 400 + 3 * 50), 'white'); dr = ImageDraw.Draw(yk)
    for n, s in enumerate((Yb + r0, Yb + r1)):
        y = 50 + n * 450
        dr.text((10, y - 40), f'%200 yakin kirpim: ek yeri y {s} (kirpim ortasi), x 270-810; isaret yok', font=fk, fill=(20, 20, 20))
        yk.paste(Image.fromarray(k0[s - 100:s + 100, 270:810]).resize((1080, 400), Image.LANCZOS), (0, y))
    yk.save(os.path.join(OUT, 'YAKIN_EK_200.jpg'), quality=95)

    # ---------- 8. rapor
    gecti = all(kapi.values())
    O['kapilar'] = kapi; O['sonuc'] = 'PASS' if gecti else 'FAIL'; O['sure_sn'] = round(time.time() - t0)
    O['zemin_uzatma'] = {'ust_satir': n_ust, 'alt_satir': n_alt, 'ust_egim_ort': round(eg_u, 4), 'alt_egim_ort': round(eg_a, 4)}
    json.dump(O, open(os.path.join(OUT, 'OLCUM.json'), 'w'), indent=1, default=str)
    P = O['paylar']
    sat = [f'KUPA 9:16 SOSYAL VIDEO ORNEGI {CIFT}: {O["sonuc"]} (Metricool/Etsy yazma 0, toplu uretim 0; Serdar karari A, kulp istisnasi)',
           f"dosya: {d['boyut']} {d['codec']} {d['profil']} {d['pix_fmt']} {d['fps']} fps, {d['kare']} kare, {d['sure']} sn, ses akisi {d['ses_akisi']}, {d['mb']} MB",
           f"gorunum: S3 pini ({stil}) ayni adimlarla yeniden kuruldu (Drive pini ile NCC {O['s3_yeniden_kurulum_pin_ncc']}); olcek {K:.5f} (kapak 2048 -> 1080, upscale yok)",
           f"hareket: video6b V6 (N 10400, sigma 0,45; baska degisiklik yok), V 1080 = bu olcek, {O['ilan_kare']} kare; kupa kutusu (kapak px) {O['hareket_kutusu_kapak']}; tasarim/motor kutu farki en cok {O['tasarim_motor_kutu_fark_max']} (ort {O['tasarim_motor_kutu_fark_ort']})",
           f"zaman: 0-1 sn tasarim, 1-6 sn ilan 0-5 sn, 6-8 sn tasarim; olculen hareket {O['hareket_sn']} sn",
           f"ilk kare / S3 NCC: {O['ilk_kare_ncc']}; siyah kare: ortalama en az {O['kare_ortalama_min']}",
           f"kupa bolgesi PSNR: motor kareleri en az {O['kupa_ilan_psnr_min']} dB" + (f"; Drive onayli ilan mp4 en az {O['kupa_onayli_ilan_mp4_psnr_min']} dB" if ps_onay else ''),
           f"sabit alan: kupa kutusu disi ortalama fark en cok {O['kupa_disi_sabit_fark_max']}",
           'arayuz (sag 918, pay 20 -> x <= 898): ' + '; '.join(f"{k_} {kut[k_]} sag pay {P[k_]['sag_918']}" for k_ in kut),
           f"SAG KUPA BASKISI (mesaj + isimler + nazar) sag kenar x {kut['sag_kupa_baski (mesaj+isim+nazar)'][2]} (<= 898: {kut['sag_kupa_baski (mesaj+isim+nazar)'][2] <= 898}); "
           f"KULP ISTISNASI: sag kulp arayuz alanina {O['sag_kulp_arayuze_giris_px']} px girer, sag kupa govdesi x {kut['sag_kupa_govde (kulp haric)'][2]}",
           f"PLAKA ISTISNASI (Serdar A, en buyuk ve ortali): plaka zemini {kut['plaka']} arayuze {O['plaka_istisnasi']['zemin_arayuze_giris_px']} px girer; plaka yazisi {kut['plaka_yazisi']} sag pay {O['plaka_istisnasi']['yazi_sag_pay']} px (kural 20)",
           f"S3 bolgesi reel y {Yb + r0}-{Yb + r1}: masa on kenari (kapak y >= {kp.MASA_KES - MASA_PAY}) ve altindaki koyu bant alinmaz, masa yuzeyi asagi uzar; ilk kare NCC bu satirlarda",
           f"bosluk: {O['bosluk']}",
           'ek yeri: ' + '; '.join(f"y {e['y']} sicrama {e['sicrama']}, ek satiri orani {e['ek_satiri_fark_orani']}" for e in ek.values()),
           f"dikey cizgi (sutun ortalamasi std): {O['dikey_cizgi']} (esik 1,5x kendi zemini)",
           f"zemin uzatma (yd_reel b11ec836 yontemi): ust {n_ust} satir (doku duvardan), alt {n_alt} satir (doku masadan)",
           'KAPILAR: ' + '; '.join(f"{'PASS' if v else 'FAIL'} {k_}" for k_, v in kapi.items()),
           f"sure {O['sure_sn']} sn"]
    open(os.path.join(OUT, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    sys.exit(0 if gecti else 1)


if __name__ == '__main__':
    main()
