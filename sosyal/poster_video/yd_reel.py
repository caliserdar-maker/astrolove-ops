#!/usr/bin/env python3
"""Yil donumu 9:16 sosyal video ORNEGI (20 Eki 2026, Serdar onayli plan): uretim + QC, tek script, PASS/FAIL. Yazma yok.

Gorunum: Y1 kapagi (KAPAK_Y1_78 KAPAK/<CIFT>.jpg, 2400) ilan videosundaki olcekle (0,45; 1080x1080) 1080x1920 karenin
ortasinda (y 420-1500); zemin kendi pikselleriyle yalniz dikeyde uzar: kenar satirlarinin dusuk frekans profili (sutun
basina dogrusal egim, 40 px yatay ortalama) egimiyle surer ve tau = 60 px'te duzlesir (C1 surekli; pinin uretilmis zemin bandi da ~240 kapak
px'te duzlesir), ince doku ayni zeminin temiz piksellerinden 48 px bloklarla kopyalanir (ilan motorunun kagit dokusu yontemi).
Baslik kapakta x 374-2032 -> 0,45'te x 168-914: arayuz alanlari (sag %15 = 918, solda ayni pay 162) disinda; pin kirpimi
(x 240-2160, 0,5625) basligi sag alana sokardigi icin kapagin tam genisligi kullanilir.
Hareket: onayli ilan videosu yildonumu_video.py (f57fd17, degistirilmeden; V6_C v6_c_egri.json, N 49200 = onayli CL Y1)
calisir; ffmpeg'e giden ham kareler (kayipsiz) bir ara katmanla kopyalanir. Yalniz poster kutusu (kapak 652-1748 x 772-2142)
ilan karesinden alinir; baslik, zemin ve diger yazilar sabit kare. Zaman: 0-1 sn sabit tasarim, 1-6 sn ilan 0-5 sn
(0,3 sn silme, toz, olusum), 6-8 sn sabit. 30 fps, 240 kare, ses yok, H.264 yuv420p crf 17.
QC (mp4 cozulerek): 1080x1920, 30 fps, 240 kare, 8,0 sn, ses akisi yok; ilk kare = tasarim (pin ile NCC >= 0,99: poster
kutusu ve tum tasarim); siyah kare yok (her karenin ortalamasi >= 20); baslik/poster arayuz alanlari disinda; ek yeri
(y 420 ve 1500): sutun ortalama profilinde iki yandan egilimle beklenen degere gore sicrama < 1,0 seviye ve ek satirindaki
dikey fark ortalamasi komsu satirlarin <= 1,5 kati; poster disi (baslik, zemin) tum karelerde sabit; hareket 1-6 sn icinde;
poster bolgesi ilan kareleriyle ayni (PSNR >= 35 dB; varsa Drive'daki onayli ilan mp4'u ile de).
Cikti: <CIFT>_yd_reel.mp4, KONTAK_0_8SN.jpg, ILK_KARE_ARAYUZ.jpg, YAKIN_EK_200.jpg, OLCUM.txt, OLCUM.json.
Kullanim: yd_reel.py <y1_kapak.jpg> <pin.jpg> <CIFT> <cikti_dir> <is_dir> [--onay_ilan ilan.mp4]
"""
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
W, H, FPS = 1080, 1920, 30
S = 0.45                                              # ilan videosu olcegi (2400 -> 1080)
Y0 = (H - W) // 2                                     # kapak y 420-1500
UST, ALT, SAG = round(0.12 * H), round(0.20 * H), round(0.15 * W)   # arayuz alanlari (230, 384, 162); P kurali
SOL = SAG                                             # solda ayni pay (P: yatay ortali)
POSTER_K = (652, 772, 1748, 2142)                     # Y1_v7 poster kutusu (kapak px)
PIN_X0, PIN_Y0, PIN_W = 240, -240, 1920               # kapak_y1_v6.pin6: pin = kapak x 240-2160, y -240..2640 -> 1000x1500
ONCE, HAREKET = 30, 150                               # 0-1 sn sabit, sonra ilan 0-5 sn (150 kare), sonra sabit
TOPLAM = 240
TAU, BL, BS = 60.0, 48, 64
ILAN_ENV = {'V6_C': os.path.join(HERE, 'v6_c_egri.json'), 'V6_N': '49200'}   # onayli CL Y1 ornegi (QC.json: tur 3, N 49200)
SHIM = '''#!/usr/bin/env python3
import os, subprocess, sys
gercek = os.environ['YD_FFMPEG']
if 'rawvideo' in sys.argv and os.environ.get('YD_RAW'):
    p = subprocess.Popen([gercek] + sys.argv[1:], stdin=subprocess.PIPE)
    with open(os.environ['YD_RAW'], 'wb') as fh:
        while True:
            b = sys.stdin.buffer.read(1 << 20)
            if not b:
                break
            fh.write(b); p.stdin.write(b)
    p.stdin.close(); sys.exit(p.wait())
os.execv(gercek, [gercek] + sys.argv[1:])
'''


CALISTIR = '''import sys
motor, kapak, out, v = sys.argv[1:5]
src = open(motor).read(); eski = 'VW, VH = 1080, 1080'
assert src.count(eski) == 1, 'motor satiri bulunamadi'
sys.argv = [motor, kapak, out]
exec(compile(src.replace(eski, f'VW, VH = {int(v)}, {int(v)}'), motor, 'exec'), {'__name__': '__main__', '__file__': motor})
'''


def lum(a):
    return a.astype(np.float32) @ np.float32([0.299, 0.587, 0.114])


def ncc(a, b):
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def psnr(a, b):
    m = float(((a.astype(np.float64) - b.astype(np.float64)) ** 2).mean())
    return 99.0 if m == 0 else round(10 * np.log10(255 ** 2 / m), 2)


def poster_kutu():
    x0, y0, x1, y1 = POSTER_K
    return int(np.floor(x0 * S)), int(np.floor(y0 * S)), int(np.ceil(x1 * S)), int(np.ceil(y1 * S))   # 1080 karede


def uzat(KAP, ozel, n_ust=Y0, n_alt=Y0):
    """Zemini kendi pikselleriyle dikeyde uzatir: (ust, alt) bantlar, n_ust / n_alt x W x 3 float."""
    rng = np.random.default_rng(7)
    k = KAP.astype(np.float32)
    LF = cv2.GaussianBlur(k, (0, 0), sigmaX=6, sigmaY=0.01)          # yalniz yatay yumusatma (dikey egim korunur)
    HF = k - cv2.GaussianBlur(k, (0, 0), 2.0)
    temiz = cv2.erode((~ozel).astype(np.uint8), np.ones((BS, BS), np.uint8), anchor=(0, 0)) > 0
    temiz[-BS:] = False; temiz[:, -BS:] = False
    cy, cx = np.where(temiz)
    if len(cy) < 50:
        raise SystemExit('doku icin temiz zemin bulunamadi')
    bant = {}
    LF40 = cv2.GaussianBlur(k, (0, 0), sigmaX=40, sigmaY=0.01)       # egim ve duzlesen deger: genis yatay ortalama
    for ad, satirlar in (('ust', np.arange(0, 80)), ('alt', np.arange(W - 50, W))):
        ys = satirlar.astype(np.float32); ym = ys.mean(); ke = 0.0 if ad == 'ust' else W - 1.0
        n = n_ust if ad == 'ust' else n_alt
        d = np.arange(1, n + 1, dtype=np.float32)[:, None, None]

        def fit(A):
            P = A[satirlar]
            e = ((ys - ym)[:, None, None] * (P - P.mean(0))).sum(0) / ((ys - ym) ** 2).sum()
            return P.mean(0) + e * (ke - ym), e
        v40, egim = fit(LF40)
        v6, _ = fit(LF)
        yon = -1.0 if ad == 'ust' else 1.0                            # ust: yukari y azalir
        # sutun basina egim gurultusu uzatmada dikey cizgi yapar: egim/duzlesme LF40'tan; kenarin orta frekansi (LF - LF40)
        # 12 px'te soner (ek satirinda surekli, uzatmada cizgi yok)
        lf = v40[None] + yon * egim[None] * TAU * (1 - np.exp(-d / TAU)) + (v6 - v40)[None] * np.exp(-d / 12.0)
        # doku: 64 px bloklar 48 px adimla (16 px yumusak bindirme, varyans korunur); eke bitisik ilk blok satiri = kenar
        # satirlarinin aynasi (ek satirinda doku surekli), sonrakiler temiz zeminden rastgele bloklar
        num = np.zeros_like(lf); den = np.zeros(lf.shape[:2] + (1,), np.float32)
        ram = np.ones(BS, np.float32); ram[:BS - BL] = np.sin(np.linspace(0, np.pi / 2, BS - BL + 2)[1:-1]); ram[BL:] = ram[:BS - BL][::-1]
        for yb in range(0, n, BL):
            for xb in range(-(BS - BL), W, BL):
                hh = min(BS, n - yb); x_a, x_b = max(0, xb), min(W, xb + BS)
                wy = ram[:hh].copy()
                if yb == 0:
                    wy[:BS - BL] = 1.0                                        # ek tarafinda rampa yok
                wx = ram[x_a - xb:x_b - xb]
                if xb <= 0:
                    wx[:] = np.maximum(wx, (np.arange(x_a, x_b) < BS - BL).astype(np.float32))
                if xb + BS >= W:
                    wx[:] = np.maximum(wx, (np.arange(x_a, x_b) >= W - (BS - BL)).astype(np.float32))
                if yb == 0:                                                   # ayna: d. satir = kenardan (d-1). satir
                    kay = HF[0:hh] if ad == 'ust' else HF[W - 1:W - 1 - hh:-1]
                    blok = kay[:, x_a:x_b]
                else:
                    j = rng.integers(len(cy)); sy, sx = cy[j], cx[j]
                    blok = HF[sy:sy + hh, sx:sx + (x_b - x_a)]
                    if blok.shape[1] < x_b - x_a:
                        blok = np.pad(blok, ((0, 0), (0, x_b - x_a - blok.shape[1]), (0, 0)), mode='reflect')
                w2 = (wy[:, None] * wx[None, :])[..., None]
                num[yb:yb + hh, x_a:x_b] += w2 * blok; den[yb:yb + hh, x_a:x_b] += w2 * w2
        dok = num / np.sqrt(np.maximum(den, 1e-6))
        b = lf + dok
        bant[ad] = b[::-1] if ad == 'ust' else b                      # ust: d=1 kapagin hemen ustu (alt satir)
        bant[ad + '_egim'] = egim
    return bant['ust'], bant['alt'], bant


def ilan_uret(kapak, is_dir, v=W, ek_env=None, ad='ilan'):
    """Onayli motoru calistirir. v != 1080: dosya degistirilmeden yalniz 'VW, VH = 1080, 1080' satiri v ile calistirilir."""
    shim = os.path.join(is_dir, 'shim'); os.makedirs(shim, exist_ok=True)
    yol = os.path.join(shim, 'ffmpeg'); open(yol, 'w').write(SHIM)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    raw = os.path.join(is_dir, f'{ad}.rgb'); mp4 = os.path.join(is_dir, f'{ad}.mp4')
    env = dict({**os.environ, **ILAN_ENV, **(ek_env or {})}, YD_RAW=raw, YD_FFMPEG=subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True).stdout.strip(),
               PATH=shim + os.pathsep + os.environ['PATH'])
    motor = os.path.join(HERE, 'yildonumu_video.py')
    cmd = [sys.executable, '-I', motor, kapak, mp4]
    if v != W:
        cmd = [sys.executable, '-I', '-c', CALISTIR, motor, kapak, mp4, str(v)]
    r = subprocess.run(cmd, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(r.stdout[-1500:], flush=True)
    if r.returncode:
        raise SystemExit('ilan videosu uretilemedi')
    ic = json.load(open(mp4 + '.ic.json'))
    n = os.path.getsize(raw) // (v * v * 3)
    return np.memmap(raw, np.uint8, 'r', shape=(n, v, v, 3)), mp4, ic


def kareler(mp4, w, h):
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def main():
    a = sys.argv[1:]
    onay = None
    if '--onay_ilan' in a:
        i = a.index('--onay_ilan'); onay = a[i + 1]; del a[i:i + 2]
    KAPAK, PIN, CIFT, OUT, IS = a
    os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
    t0 = time.time()
    O, kapi = {}, {}

    # ---------- 1. onayli ilan videosu (degistirilmeden), ham kareler
    F, ilan_mp4, ic = ilan_uret(KAPAK, IS)
    O['ilan'] = {'kare': int(F.shape[0]), 'N': ic['N'], 'bolge_px': ic['bolge_px'], 'sure_sn': round(time.time() - t0)}
    kapi['ilan 180 kare, N 49200 (onayli CL Y1)'] = F.shape[0] == 180 and ic['N'] == 49200
    KAP = np.array(F[0])
    kf = np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32)
    KAPr = np.clip(np.round(cv2.resize(kf, (W, W), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
    O['ilan_kare0_kapak_fark'] = int(np.abs(KAP.astype(int) - KAPr.astype(int)).max())
    kapi['ilan ilk/son kare = kapak (0,45)'] = O['ilan_kare0_kapak_fark'] == 0 and int(np.abs(F[-1].astype(int) - KAP.astype(int)).max()) == 0
    px0, py0, px1, py1 = poster_kutu()
    disari = np.ones((W, W), bool); disari[py0:py1, px0:px1] = False
    O['ilan_poster_disi_fark_max'] = int(max(np.abs(F[i].astype(np.int16) - KAP.astype(np.int16)).max(-1)[disari].max() for i in range(F.shape[0])))

    # ---------- 2. sabit 9:16 tasarim: zemin dikeyde uzar
    lk = lum(KAP); bg = lum(cv2.medianBlur(KAP, 31))
    ozel = cv2.dilate(((np.abs(lk - bg) > 6) | (lk > 70)).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    ozel[py0 - 10:py1 + 50, px0 - 30:px1 + 30] = True               # poster + golge
    ust, alt, B = uzat(KAP, ozel)
    T = np.zeros((H, W, 3), np.float32)
    T[:Y0] = ust; T[Y0:Y0 + W] = KAP; T[Y0 + W:] = alt
    T8 = np.clip(np.round(T), 0, 255).astype(np.uint8)
    Image.fromarray(T8).save(os.path.join(IS, 'tasarim.png'))

    # ---------- 3. video: 0-1 sn sabit, 1-6 sn ilan 0-5 sn (yalniz poster kutusu), 6-8 sn sabit
    V = os.path.join(OUT, f'{CIFT}_yd_reel.mp4')
    pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow',
                           '-profile:v', 'high', '-tag:v', 'avc1', '-movflags', '+faststart', V], stdin=subprocess.PIPE)
    kaynak = []
    for i in range(TOPLAM):
        j = i - ONCE
        if 0 <= j < HAREKET:
            f = T8.copy(); f[Y0 + py0:Y0 + py1, px0:px1] = F[j][py0:py1, px0:px1]
            kaynak.append(j)
        else:
            f = T8; kaynak.append(-1)
        pr.stdin.write(f.tobytes())
    pr.stdin.close(); pr.wait()
    if pr.returncode:
        raise SystemExit('kodlama hatasi')

    # ---------- 4. QC: dosya
    pf = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', V],
                                   capture_output=True, text=True).stdout)
    vs = [s for s in pf['streams'] if s['codec_type'] == 'video'][0]
    O['dosya'] = {'boyut': f"{vs['width']}x{vs['height']}", 'codec': vs['codec_name'], 'profil': vs.get('profile'), 'pix_fmt': vs['pix_fmt'],
                  'fps': vs['r_frame_rate'], 'kare': int(vs['nb_read_frames']), 'sure': round(float(pf['format']['duration']), 3),
                  'ses_akisi': sum(s['codec_type'] == 'audio' for s in pf['streams']), 'mb': round(os.path.getsize(V) / 1e6, 2)}
    d = O['dosya']
    kapi['1080x1920, H.264, 30 fps, 240 kare, 8,0 sn, ses yok'] = (d['boyut'] == '1080x1920' and d['codec'] == 'h264' and d['fps'] == '30/1'
                                                                 and d['kare'] == 240 and abs(d['sure'] - 8.0) < 0.05 and d['ses_akisi'] == 0)

    # ---------- 5. QC: kareler (akis halinde)
    pin = np.asarray(Image.open(PIN).convert('RGB'))
    o = 1000 / PIN_W                                                  # pin px / kapak px
    pk = pin[round((0 - PIN_Y0) * o):round((2400 - PIN_Y0) * o), :]   # pin'de kapak y 0-2400, x 240-2160
    pk = np.asarray(Image.fromarray(pk).resize((round(PIN_W * S), W), Image.LANCZOS))   # 864 x 1080
    vx0 = round(PIN_X0 * S)
    ilan_onay = {j: f.copy() for j, f in enumerate(kareler(onay, W, W)) if j % 15 == 0} if onay else None
    ort, sabit_fark, hareket, ps_ilan, ps_onay, kontak = [], [], [], [], [], {}
    KT = [round(t * FPS) for t in np.arange(0, 8.0, 0.5)] + [TOPLAM - 1]
    dis9 = np.ones((H, W), bool); dis9[Y0 + py0:Y0 + py1, px0:px1] = False
    k0 = None
    for i, f in enumerate(kareler(V, W, H)):
        ort.append(float(lum(f).mean()))
        if i == 0:
            k0 = f.copy()
        fd = np.abs(f.astype(np.int16) - k0.astype(np.int16)).max(-1)
        sabit_fark.append(float(fd[dis9].mean()))
        hareket.append(float((fd[~dis9] > 20).mean()))
        j = kaynak[i]
        if j >= 0 and j % 15 == 0:
            ps_ilan.append(psnr(f[Y0 + py0:Y0 + py1, px0:px1], F[j][py0:py1, px0:px1]))
            if ilan_onay is not None and j in ilan_onay:
                ps_onay.append(psnr(f[Y0 + py0:Y0 + py1, px0:px1], ilan_onay[j][py0:py1, px0:px1]))
        if i in KT:
            kontak[i] = f.copy()
    O['kare_ortalama_min'] = round(min(ort), 1); O['kare_ortalama_max'] = round(max(ort), 1)
    kapi['siyah kare yok (her kare ortalama >= 20)'] = len(ort) == 240 and min(ort) >= 20
    O['poster_disi_sabit_fark_max'] = round(max(sabit_fark), 3)
    kapi['baslik/zemin sabit (poster disi ortalama fark <= 0,5; ilan poster disi <= 1)'] = max(sabit_fark) <= 0.5 and O['ilan_poster_disi_fark_max'] <= 1
    hk = [i for i, h in enumerate(hareket) if h > 0.001]
    O['hareket_kareleri'] = [hk[0], hk[-1]] if hk else []
    O['hareket_sn'] = [round(hk[0] / FPS, 2), round(hk[-1] / FPS, 2)] if hk else []
    kapi['hareket yalniz 1-6 sn, 0-1 ve 6-8 sn tam tasarim'] = bool(hk) and hk[0] >= ONCE and hk[-1] < ONCE + HAREKET
    O['poster_ilan_psnr_min'] = min(ps_ilan)
    kapi['poster bolgesi ilan kareleriyle ayni (PSNR >= 35)'] = min(ps_ilan) >= 35
    if ps_onay:
        O['poster_onayli_ilan_mp4_psnr_min'] = min(ps_onay)
        kapi['poster bolgesi Drive onayli ilan mp4 ile ayni (PSNR >= 35)'] = min(ps_onay) >= 35

    # ilk kare urun NCC (pin ile)
    g0 = lum(k0); gp = lum(pk)
    tas = g0[Y0:Y0 + W, vx0:vx0 + pk.shape[1]]
    O['ilk_kare_ncc_tasarim'] = round(ncc(tas, gp), 5)
    O['ilk_kare_ncc_poster'] = round(ncc(g0[Y0 + py0 + 3:Y0 + py1 - 3, px0 + 3:px1 - 3], gp[py0 + 3:py1 - 3, px0 - vx0 + 3:px1 - vx0 - 3]), 5)
    O['ilk_kare_ortalama'] = round(ort[0], 1)
    kapi['ilk kare urun NCC >= 0,99 (pin; poster ve tasarim), siyah degil'] = O['ilk_kare_ncc_tasarim'] >= 0.99 and O['ilk_kare_ncc_poster'] >= 0.99 and ort[0] >= 20
    # pinin uretilmis zemin bandi ile uzatma (bilgi)
    bu = pin[:round((0 - PIN_Y0) * o)]
    bu = np.asarray(Image.fromarray(bu).resize((round(PIN_W * S), round(-PIN_Y0 * S)), Image.LANCZOS)).astype(np.float32)
    uz = k0[Y0 - bu.shape[0]:Y0, vx0:vx0 + bu.shape[1]].astype(np.float32)
    O['pin_ust_bandi_ile_uzatma_ort_fark'] = round(float(np.abs(lum(bu).mean(1) - lum(uz).mean(1)).mean()), 2)

    # arayuz alanlari
    kk = KAP.astype(np.float32); lk2 = lum(kk)
    yazi = (lk2 > 150) & (kk[..., 0] - kk[..., 2] < 60); yazi[py0:] = False
    ys, xs = np.where(yazi)
    bk = (int(xs.min()), int(ys.min()) + Y0, int(xs.max()) + 1, int(ys.max()) + 1 + Y0)
    pk9 = (px0, Y0 + py0, px1, Y0 + py1)
    pay = lambda b: {'sol': b[0] - SOL, 'sag': (W - SAG) - b[2], 'ust': b[1] - UST, 'alt': (H - ALT) - b[3]}
    O['baslik_kutu'] = bk; O['poster_kutu'] = pk9; O['pay_baslik'] = pay(bk); O['pay_poster'] = pay(pk9)
    kapi['baslik ve poster arayuz alanlari disinda (pay >= 0)'] = min(pay(bk).values()) >= 0 and min(pay(pk9).values()) >= 0

    # ek yeri
    ek = {}
    for ad, s in (('ust', Y0), ('alt', Y0 + W)):
        p = lum(k0.astype(np.float32)).mean(1)
        ya = np.arange(s - 24, s); yb = np.arange(s, s + 24)
        fa = np.polyfit(ya, p[ya], 1); fb = np.polyfit(yb, p[yb], 1)
        sic = float(np.polyval(fb, s - 0.5) - np.polyval(fa, s - 0.5))
        dv = np.abs(np.diff(lum(k0.astype(np.float32)), axis=0)).mean(1)   # dv[y] = |row y+1 - row y|
        oran = float(dv[s - 1] / np.median(np.r_[dv[s - 20:s - 2], dv[s + 1:s + 19]]))
        ek[ad] = {'y': s, 'sicrama': round(sic, 3), 'egim_once': round(float(fa[0]), 4), 'egim_sonra': round(float(fb[0]), 4),
                  'ek_satiri_fark_orani': round(oran, 3)}
    dv = np.abs(np.diff(lum(k0.astype(np.float32)), axis=0)).mean(1); md = np.median(dv[Y0 + 20:Y0 + 100])
    O['uzatma_satir_fark_orani_max'] = {'ust': round(float(dv[:Y0 - 1].max() / md), 3), 'alt': round(float(dv[Y0 + W:].max() / md), 3)}
    O['ek_yeri'] = ek
    l0 = lum(k0.astype(np.float32)); hp = l0 - cv2.GaussianBlur(l0, (0, 0), sigmaX=20, sigmaY=0.01)
    cz = float(hp[Y0 + 380:Y0 + 740, 30:250].mean(0).std())            # kapagin kendi zemini (poster solu, 360 satir)
    O['dikey_cizgi'] = {'ust': round(float(hp[0:360, 30:W - 30].mean(0).std()), 3), 'alt': round(float(hp[H - 360:H, 30:W - 30].mean(0).std()), 3),
                        'kapak_zemini': round(cz, 3)}
    kapi['uzatmada dikey cizgi yok (sutun ortalamasi std <= 1,5 x kapak zemini)'] = max(O['dikey_cizgi']['ust'], O['dikey_cizgi']['alt']) <= 1.5 * cz
    kapi['ek yeri gorunmuyor (sicrama < 1,0; ek satiri <= 1,5x komsu)'] = all(abs(e['sicrama']) < 1.0 and e['ek_satiri_fark_orani'] <= 1.5 for e in ek.values())

    # ---------- 6. gorseller
    try:
        fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
        fk = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except OSError:
        fnt = fk = ImageFont.load_default()
    im = Image.fromarray(k0).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for r in ((0, 0, W, UST), (0, H - ALT, W, H), (W - SAG, UST, W, H - ALT)):
        dr.rectangle(r, fill=(255, 0, 0, 70))
    dr.rectangle((SOL, UST, W - SAG, H - ALT), outline=(255, 255, 0, 255), width=2)
    for b, c in ((bk, (0, 255, 0, 255)), (pk9, (0, 200, 255, 255))):
        dr.rectangle(b, outline=c, width=3)
    for s in (Y0, Y0 + W):
        dr.line((0, s, 24, s), fill=(255, 255, 255, 200), width=2); dr.line((W - 24, s, W, s), fill=(255, 255, 255, 200), width=2)
    im = Image.alpha_composite(im, ov).convert('RGB'); dr = ImageDraw.Draw(im)
    dr.text((20, 20), f'{CIFT} ilk kare | arayuz: ust {UST}, alt {H - ALT}, sag {W - SAG} (kirmizi)', font=fk, fill=(255, 255, 255))
    dr.text((20, 48), f"baslik pay {O['pay_baslik']}", font=fk, fill=(0, 255, 0))
    dr.text((20, 76), f"poster pay {O['pay_poster']}", font=fk, fill=(0, 200, 255))
    dr.text((20, H - 60), f'ek yeri: y {Y0} ve {Y0 + W} (beyaz cizgi)', font=fk, fill=(255, 255, 255))
    im.save(os.path.join(OUT, 'ILK_KARE_ARAYUZ.jpg'), quality=92)

    TW, TH = 270, 480
    sh = Image.new('RGB', (20 + 6 * (TW + 14), 20 + 3 * (TH + 50)), 'white'); dr = ImageDraw.Draw(sh)
    for n, i in enumerate(KT):
        x, y = 20 + (n % 6) * (TW + 14), 20 + (n // 6) * (TH + 50)
        sh.paste(Image.fromarray(kontak[i]).resize((TW, TH), Image.LANCZOS), (x, y + 34))
        evre = 'tam tasarim' if kaynak[i] < 0 else f'ilan {kaynak[i] / FPS:.2f} sn'
        dr.text((x, y + 4), f'{i / FPS:.2f} sn  {evre}', font=fk, fill=(20, 20, 20))
    sh.save(os.path.join(OUT, 'KONTAK_0_8SN.jpg'), quality=90)

    parca = []
    for s in (Y0, Y0 + W):
        c = Image.fromarray(k0[s - 100:s + 100, 270:810]).resize((1080, 400), Image.LANCZOS)
        parca.append((s, c))
    yk = Image.new('RGB', (1080, 2 * 400 + 3 * 50), 'white'); dr = ImageDraw.Draw(yk)
    for n, (s, c) in enumerate(parca):
        y = 50 + n * 450
        dr.text((10, y - 40), f'%200 yakin kirpim: ek yeri y {s} (kirpim ortasi), x 270-810; isaret yok', font=fk, fill=(20, 20, 20))
        yk.paste(c, (0, y))
    yk.save(os.path.join(OUT, 'YAKIN_EK_200.jpg'), quality=95)

    # ---------- 7. rapor
    gecti = all(kapi.values())
    O['kapilar'] = kapi; O['sonuc'] = 'PASS' if gecti else 'FAIL'; O['sure_sn'] = round(time.time() - t0)
    O['zemin_uzatma'] = {'tau_px': TAU, 'blok_px': BL, 'ust_egim_ort': round(float(B['ust_egim'].mean()), 4), 'alt_egim_ort': round(float(B['alt_egim'].mean()), 4)}
    json.dump(O, open(os.path.join(OUT, 'OLCUM.json'), 'w'), indent=1, default=str)
    sat = [f'YIL DONUMU 9:16 SOSYAL VIDEO ORNEGI {CIFT}: {O["sonuc"]} (Metricool/hesap yazma 0, toplu uretim 0)',
           f"dosya: {d['boyut']} {d['codec']} {d['profil']} {d['pix_fmt']} {d['fps']} fps, {d['kare']} kare, {d['sure']} sn, ses akisi {d['ses_akisi']}, {d['mb']} MB",
           f"ilan videosu: yildonumu_video.py (f57fd17, degistirilmeden), N {ic['N']}, {F.shape[0]} kare; ilk/son kare = kapak; poster disi fark en cok {O['ilan_poster_disi_fark_max']} (motorun 0,3 sn silme karisiminda tam sayiya kesme; videoda yalniz poster kutusu alinir)",
           f"zaman: 0-1 sn tam tasarim, 1-6 sn ilan 0-5 sn (poster kutusu), 6-8 sn tam tasarim; olculen hareket {O['hareket_sn']} sn (kare {O['hareket_kareleri']})",
           f"ilk kare: pin ile NCC poster {O['ilk_kare_ncc_poster']}, tasarim {O['ilk_kare_ncc_tasarim']}; ortalama parlaklik {O['ilk_kare_ortalama']}",
           f"siyah kare: kare ortalamasi en az {O['kare_ortalama_min']} (esik 20)",
           f"poster bolgesi / ilan kareleri PSNR en az {O['poster_ilan_psnr_min']} dB" + (f"; Drive onayli ilan mp4 ile en az {O['poster_onayli_ilan_mp4_psnr_min']} dB" if ps_onay else ''),
           f"baslik/zemin sabit: poster disi ortalama fark en cok {O['poster_disi_sabit_fark_max']}",
           f"arayuz: baslik kutu {bk} pay {O['pay_baslik']}; poster kutu {pk9} pay {O['pay_poster']}",
           f"ek yeri: " + '; '.join(f"y {e['y']} sicrama {e['sicrama']}, egim {e['egim_once']}/{e['egim_sonra']}, ek satiri orani {e['ek_satiri_fark_orani']}" for e in ek.values()),
           f"dikey cizgi (sutun ortalamasi std): ust {O['dikey_cizgi']['ust']}, alt {O['dikey_cizgi']['alt']}, kapak zemini {O['dikey_cizgi']['kapak_zemini']} (esik 1,5x)",
           f"zemin uzatma: kenar egimi (40 px yatay ortalama) tau {TAU:g} px ile duzlesir, kenarin orta frekansi 12 px'te soner + doku (eke bitisik ayna, sonra {BS} px bloklar {BL} px adim); uzatma icinde satir fark orani en cok {O['uzatma_satir_fark_orani_max']}; pin ust bandi ile ortalama fark {O['pin_ust_bandi_ile_uzatma_ort_fark']} seviye (bilgi)",
           'KAPILAR: ' + '; '.join(f"{'PASS' if v else 'FAIL'} {k}" for k, v in kapi.items()),
           f"sure {O['sure_sn']} sn"]
    open(os.path.join(OUT, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    sys.exit(0 if gecti else 1)


if __name__ == '__main__':
    main()
