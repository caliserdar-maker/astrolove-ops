#!/usr/bin/env python3
"""Yil donumu 9:16 sosyal video ORNEGI v3 (20 Eki 2026, Serdar: v2 iyi, poster daha buyuk). Uretim + QC tek script, PASS/FAIL.
Yazma yok. v2'den (yd_reel_v2.py) yalniz su farklar:
- Poster 850 px: onayli motor (yildonumu_video.py f57fd17, dosya degistirilmeden) kapagi 1862x1862'de dogrudan render eder
  (olcek 1862/2400 = 0,776 <= 1, buyutme yok); tam poster pikselleri 850x1062. Poster sag kenari 898 (918'e 20 px), sol ~48;
  yatayda ortali degil.
- Baslik v1/v2 boyutunda (0,45), posterin yatay merkezine hizali, posterin ARA px ustunde. Basligin kapaktaki yerinden
  tasinmasi: kapakta (2400) baslik alfasi = yerel zemine (maskeli genis bulanik, sigma 40) gore baslik rengine izdusum;
  basligin eski yeri ayni zeminin yuzeyi + ayni zeminin temiz pikselinden doku (sigma 8 kalintisi, 48 px bloklar) ile doldurulur;
  baslik ayni alfa ve renkle yeni yere tam piksel kaydirilarak bindirilir (yeniden cizim yok).
- Dikey: baslik + poster 230-1536 icinde, ust ve alt bosluk esit. Golge ve toz duzeltmesi v2 kuraliyla.
QC: v2'nin 12 kapisi; yerlesim kapisi v3 olculeriyle (poster 848-852 px, sag kenar 898, baslik merkezi = poster merkezi
+-1, ara 40-50, ust/alt farki <= 2); arayuz: ust 230, alt 1536, sag 918 (sol arayuz alani yok; kare icinde); ek yeri kapisinda
basligin eski yeri de olculur (cevre yuzeyine gore ortalama fark <= 1,5, ince doku std orani 0,7-1,3).
Cikti: <CIFT>_yd_reel_v3.mp4, KONTAK_0_8SN.jpg, ILK_KARE_ARAYUZ.jpg, YAKIN_EK_200.jpg, OLCUM.txt, OLCUM.json.
Kullanim: yd_reel_v3.py <y1_kapak.jpg> <pin.jpg> <CIFT> <cikti_dir> <is_dir> [--onay_ilan ilan.mp4]
"""
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yd_reel as R  # noqa: E402

W, H, FPS = R.W, R.H, R.FPS
S = R.S                                               # baslik / zemin olcegi (v1, 0,45)
V = 1862                                              # motor render boyu (yuv420p icin cift): poster 1096 x 1862/2400 = 850 px
SB = V / 2400
ARA = 45                                              # baslik - poster arasi (40-50)
SAG_X = 898                                           # poster sag kenari (918 - 20)
UST, ALT, SAG = R.UST, R.ALT, R.SAG
SOL = 0                                               # sol arayuz alani yok (gorev: ust 230, alt 1536, sag 918)
POSTER_K = R.POSTER_K
G_K = (16, 30, 40, 0.5)                               # by_kapak.poster_yerlestir golgesi (dx, dy, sigma, guc), kapak px
ONCE, HAREKET, TOPLAM = R.ONCE, R.HAREKET, R.TOPLAM
ONAY_TOZ = {2.0: 0.544, 2.5: 0.527, 3.0: 0.514, 3.5: 0.474, 4.0: 0.406}   # onayli CL ilan QC.json (1080, N 49200)


def golge(shape, kutu, dx, dy, sg, guc):
    """by_kapak.poster_yerlestir golge carpani (1 - guc x blur(dikdortgen))."""
    sh = np.zeros(shape, np.float32)
    x0, y0, x1, y1 = kutu
    sh[int(round(y0 + dy)):int(round(y1 + dy)), int(round(x0 + dx)):int(round(x1 + dx))] = 1
    return 1 - guc * cv2.GaussianBlur(sh, (0, 0), sg)


def main():
    a = sys.argv[1:]
    onay = None
    if '--onay_ilan' in a:
        i = a.index('--onay_ilan'); onay = a[i + 1]; del a[i:i + 2]
    KAPAK, PIN, CIFT, OUT, IS = a
    os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
    t0 = time.time()
    O, kapi = {'V': V, 'olcek_poster': round(SB, 4), 'olcek_baslik_zemin': S}, {}

    # ---------- 1. onayli motor V x V (dosya degistirilmeden), ham kareler. Toz: N0 motorun alan kurali; alan basina toz
    # yogunlugu (yildonumu_qc.toz formulu, tozsuz ikinci kosu ile) 2-4 sn onayli CL ilan ile +-%10 tutmazsa onayli 78 kuralinin
    # TEK duzeltme turu (yildonumu_qc YD_TOPLU): N1 = N0 x hed^(1/0,62), hed = sqrt(en kucuk x en buyuk onayli/v2 orani)
    def tur(env, ad):
        F_, _, ic_ = R.ilan_uret(KAPAK, IS, v=V, ek_env=env, ad=ad)
        FT_, _, _ = R.ilan_uret(KAPAK, IS, v=V, ek_env=dict(env, TOZSUZ='1'), ad=ad + '_tozsuz')
        SM = np.asarray(Image.open(os.path.join(IS, f'{ad}.mp4.sembol_maske.png'))) > 127
        bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
        D = np.array([float(((np.abs(F_[i].astype(np.int16) - FT_[i].astype(np.int16)).max(-1) > 20) & bol).sum() / bol.sum()) for i in range(F_.shape[0])])
        D = np.clip(D - D[160:].mean(), 0, None)
        del FT_; os.remove(os.path.join(IS, ad + '_tozsuz.rgb'))
        tb = {f'{t:g}': {'v2': round(float(D[int(round(t * FPS))]), 3), 'onayli': ONAY_TOZ[t],
                         'fark_yuzde': round(100 * (D[int(round(t * FPS))] / ONAY_TOZ[t] - 1), 1)} for t in ONAY_TOZ}
        return F_, ic_, tb
    tutar = lambda tb: all(abs(v['fark_yuzde']) <= 10 for v in tb.values())  # noqa: E731
    nenv = {'V6_N': '49200', 'V6_N_REF': '49200', 'V6_BOLGE_REF': '27311'}
    F, ic, tab = tur(nenv, 'ilan0')
    N_bek = int(round(49200 * ic['bolge_px'] / 27311 / 100.0) * 100)
    O['toz_turlari'] = [{'N': ic['N'], 'kaynak': 'N0 = 49200 x bolge / 27311 (motor alan kurali)', 'toz_2_4sn': tab, 'tutar': tutar(tab)}]
    n_ok = ic['N'] == N_bek
    if not tutar(tab):
        rs = [v['onayli'] / max(v['v2'], 1e-6) for v in tab.values()]; hed = float(np.sqrt(min(rs) * max(rs)))
        N1 = int(round(ic['N'] * hed ** (1 / 0.62) / 100.0) * 100)
        del F; os.remove(os.path.join(IS, 'ilan0.rgb'))
        F, ic, tab = tur({'V6_N': str(N1)}, 'ilan1')
        n_ok = n_ok and ic['N'] == N1
        O['toz_turlari'].append({'N': ic['N'], 'kaynak': f'N0 x {hed:.3f}^(1/0,62) (onayli 78 tek duzeltme kurali)', 'toz_2_4sn': tab, 'tutar': tutar(tab)})
    O['toz_2_4sn'] = tab
    O['ilan'] = {'kare': int(F.shape[0]), 'N': ic['N'], 'N0_alan_kurali': N_bek, 'bolge_px': ic['bolge_px'], 'sure_sn': round(time.time() - t0)}
    kapi['motor 180 kare; toz yogunlugu 2-4 sn onayli CL ilan ile +-%10 (N0 alan kurali, gerekirse tek duzeltme)'] = F.shape[0] == 180 and n_ok and tutar(tab)
    kf = np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32)
    KAPV = np.clip(np.round(cv2.resize(kf, (V, V), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
    O['ilan_kare0_kapak_fark'] = int(np.abs(F[0].astype(int) - KAPV.astype(int)).max())
    kapi[f'ilan ilk/son kare = kapak ({SB:.3f})'] = O['ilan_kare0_kapak_fark'] == 0 and int(np.abs(F[-1].astype(int) - KAPV.astype(int)).max()) == 0
    x0, y0, x1, y1 = POSTER_K
    bx0, by0, bx1, by1 = int(np.ceil(x0 * SB)), int(np.ceil(y0 * SB)), int(np.floor(x1 * SB)), int(np.floor(y1 * SB))   # tam poster pikselleri
    PW, PH = bx1 - bx0, by1 - by0
    disV = np.ones((V, V), bool); disV[int(np.floor(y0 * SB)):int(np.ceil(y1 * SB)), int(np.floor(x0 * SB)):int(np.ceil(x1 * SB))] = False
    O['ilan_poster_disi_fark_max'] = int(max(np.abs(F[i].astype(np.int16) - F[0].astype(np.int16)).max(-1)[disV].max() for i in range(F.shape[0])))
    # ---------- 2. zemin + baslik katmani (kapak 2400; kucuk poster golgesi kaldirilir), buyuk poster yerlesimi
    gk = golge(kf.shape[:2], POSTER_K, *G_K)
    kz = kf / gk[..., None]                                        # kapak golgesi tersi (poster ici sonra ortulur)
    lz = R.lum(kz)
    bant = np.zeros(lz.shape, bool); bant[:y0 - 60] = True         # poster ustu: baslik + zemin
    m0 = bant & (lz > 70)                                          # baslik murekkebi (zemin lum < 60)
    Mt = (cv2.dilate(m0.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0) & bant
    w_ = (~(cv2.dilate((lz > 70).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0)).astype(np.float32); w_[y0 - 60:] = 0
    LF = cv2.GaussianBlur(kz * w_[..., None], (0, 0), 40) / np.maximum(cv2.GaussianBlur(w_, (0, 0), 40), 1e-4)[..., None]
    c1 = np.median(kz[m0 & (lz > np.percentile(lz[m0], 75))], 0)
    dd = c1[None, None] - LF
    alfa = np.clip(((kz - LF) * dd).sum(-1) / np.maximum((dd * dd).sum(-1), 1.0), 0, 1) * Mt
    HFk = kz - cv2.GaussianBlur(kz, (0, 0), 8.0)                  # zemin dokusu (gurultu bandi tam; sigma 2 dolguyu zayif birakiyordu)
    BLK = 48
    uzak = ~(cv2.dilate((lz > 70).astype(np.uint8), np.ones((81, 81), np.uint8)) > 0)   # bulanikliga yazi sizmasin
    temiz = cv2.erode((uzak & bant & (w_ > 0)).astype(np.uint8), np.ones((BLK, BLK), np.uint8), anchor=(0, 0)) > 0
    temiz[-BLK:] = False; temiz[:, -BLK:] = False
    cy_, cx_ = np.where(temiz); rng = np.random.default_rng(9)
    dok = np.zeros_like(kz)
    ry, rx = np.where(Mt)
    for yb in range(ry.min(), ry.max() + 1, BLK):
        for xb in range(rx.min(), rx.max() + 1, BLK):
            j = rng.integers(len(cy_)); hh, ww = min(BLK, kz.shape[0] - yb), min(BLK, kz.shape[1] - xb)
            dok[yb:yb + hh, xb:xb + ww] = HFk[cy_[j]:cy_[j] + hh, cx_[j]:cx_[j] + ww]
    kzz = np.where(Mt[..., None], LF + dok, kz)                    # basligi kaldirilmis zemin
    KAPz = cv2.resize(kzz, (W, W), interpolation=cv2.INTER_AREA)
    As = np.clip(cv2.resize(alfa, (W, W), interpolation=cv2.INTER_AREA), 0, 1)
    qx0, qy0, qx1, qy1 = int(np.floor(x0 * S)), int(np.floor(y0 * S)), int(np.ceil(x1 * S)), int(np.ceil(y1 * S))
    ys, xs = np.where(As > 0.5)
    t_x0, t_y0, t_x1, t_y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1   # eski yer (kapak 1080)
    PX = SAG_X - PW
    dx = int(round((PX + PW / 2) - (t_x0 + t_x1) / 2))             # baslik merkezi = poster merkezi
    Ash = np.zeros_like(As)
    if dx < 0:
        Ash[:, :W + dx] = As[:, -dx:]; assert As[:, :-dx].max() == 0
    else:
        Ash[:, dx:] = As[:, :W - dx]; assert dx == 0 or As[:, W - dx:].max() == 0
    KAP = KAPz * (1 - Ash[..., None]) + c1[None, None] * Ash[..., None]
    KAP8 = np.clip(np.round(KAP), 0, 255).astype(np.uint8)
    p_top = t_y1 + ARA                                             # kapak koordinatinda buyuk poster ustu
    Y0 = int(round((UST + (H - ALT) - t_y0 - p_top - PH) / 2))     # ust bosluk = alt bosluk
    PY = Y0 + p_top
    n_alt = H - Y0 - W
    O['baslik_katmani'] = {'renk': c1.round(1).tolist(), 'kaydirma_px': dx, 'eski_kutu': [t_x0, t_y0, t_x1, t_y1]}
    O['yerlesim'] = {'kapak_y': [Y0, Y0 + W], 'poster': [PX, PY, PX + PW, PY + PH], 'poster_genislik': PW, 'poster_yukseklik': PH,
                     'baslik': [t_x0 + dx, Y0 + t_y0, t_x1 + dx, Y0 + t_y1], 'ara': PY - (Y0 + t_y1)}
    lk = R.lum(KAP8.astype(np.float32)); bg = R.lum(cv2.medianBlur(KAP8, 31))
    ozel = cv2.dilate(((np.abs(lk - bg) > 6) | (lk > 70)).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    ozel[qy0 - 10:qy1 + 50, qx0 - 30:qx1 + 30] = True
    ozel |= cv2.dilate(((As > 0.01) | (Ash > 0.01)).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0   # baslik eski/yeni yer
    ust, alt, B = R.uzat(KAP8, ozel, Y0, n_alt)
    T = np.zeros((H, W, 3), np.float32)
    T[:Y0] = ust; T[Y0:Y0 + W] = KAP8; T[Y0 + W:] = alt
    Tz = T.copy()
    gb = golge((H, W), (PX, PY, PX + PW, PY + PH), *(v * SB for v in G_K[:3]), G_K[3])
    T = T * gb[..., None]
    T8 = np.clip(np.round(T), 0, 255).astype(np.uint8)
    T8[PY:PY + PH, PX:PX + PW] = F[0][by0:by1, bx0:bx1]
    Image.fromarray(T8).save(os.path.join(IS, 'tasarim.png'))
    # basligin eski yeri: cevre yuzeyine (2. derece) gore ortalama fark ve ince doku std orani
    Es = np.zeros((H, W), bool); En = np.zeros((H, W), bool)
    Es[Y0:Y0 + W] = cv2.dilate((As > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    En[Y0:Y0 + W] = cv2.dilate((Ash > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    Es &= ~En
    halka = (cv2.dilate(Es.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0) & ~(cv2.dilate(Es.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~En
    lt = R.lum(Tz); yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    A_ = lambda m: np.stack([np.ones(m.sum()), xx[m], yy[m], xx[m] ** 2, xx[m] * yy[m], yy[m] ** 2], 1) / np.array([1, W, H, W * W, W * H, H * H])  # noqa: E731
    cf = np.linalg.lstsq(A_(halka), lt[halka], rcond=None)[0]
    hfl = lt - cv2.GaussianBlur(lt, (0, 0), 2.0)
    O['baslik_eski_yer'] = {'px': int(Es.sum()), 'ortalama_fark': round(float((lt[Es] - A_(Es) @ cf).mean()), 3),
                            'doku_std_orani': round(float(hfl[Es].std() / hfl[halka].std()), 3)}

    # ---------- 3. video
    Vp = os.path.join(OUT, f'{CIFT}_yd_reel_v3.mp4')
    pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow',
                           '-profile:v', 'high', '-tag:v', 'avc1', '-movflags', '+faststart', Vp], stdin=subprocess.PIPE)
    kaynak = []
    for i in range(TOPLAM):
        j = i - ONCE
        if 0 <= j < HAREKET:
            f = T8.copy(); f[PY:PY + PH, PX:PX + PW] = F[j][by0:by1, bx0:bx1]; kaynak.append(j)
        else:
            f = T8; kaynak.append(-1)
        pr.stdin.write(f.tobytes())
    pr.stdin.close(); pr.wait()
    if pr.returncode:
        raise SystemExit('kodlama hatasi')

    # ---------- 4. QC: dosya
    pf = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', Vp],
                                   capture_output=True, text=True).stdout)
    vs = [s for s in pf['streams'] if s['codec_type'] == 'video'][0]
    d = O['dosya'] = {'boyut': f"{vs['width']}x{vs['height']}", 'codec': vs['codec_name'], 'profil': vs.get('profile'), 'pix_fmt': vs['pix_fmt'],
                      'fps': vs['r_frame_rate'], 'kare': int(vs['nb_read_frames']), 'sure': round(float(pf['format']['duration']), 3),
                      'ses_akisi': sum(s['codec_type'] == 'audio' for s in pf['streams']), 'mb': round(os.path.getsize(Vp) / 1e6, 2)}
    kapi['1080x1920, H.264, 30 fps, 240 kare, 8,0 sn, ses yok'] = (d['boyut'] == '1080x1920' and d['codec'] == 'h264' and d['fps'] == '30/1'
                                                                 and d['kare'] == 240 and abs(d['sure'] - 8.0) < 0.05 and d['ses_akisi'] == 0)

    # ---------- 5. QC: kareler
    ilan_onay = {j: f.copy() for j, f in enumerate(R.kareler(onay, W, W)) if j % 15 == 0} if onay else None
    ort, sabit_fark, hareket, ps_ilan, ncc_onay, kontak = [], [], [], [], [], {}
    KT = [round(t * FPS) for t in np.arange(0, 8.0, 0.5)] + [TOPLAM - 1]
    dis9 = np.ones((H, W), bool); dis9[PY:PY + PH, PX:PX + PW] = False
    k0 = None
    for i, f in enumerate(R.kareler(Vp, W, H)):
        ort.append(float(R.lum(f).mean()))
        if i == 0:
            k0 = f.copy()
        fd = np.abs(f.astype(np.int16) - k0.astype(np.int16)).max(-1)
        sabit_fark.append(float(fd[dis9].mean())); hareket.append(float((fd[~dis9] > 20).mean()))
        j = kaynak[i]
        if j >= 0 and j % 15 == 0:
            ps_ilan.append(R.psnr(f[PY:PY + PH, PX:PX + PW], F[j][by0:by1, bx0:bx1]))
            if ilan_onay is not None and j in ilan_onay:
                kq = cv2.resize(f[PY:PY + PH, PX:PX + PW].astype(np.float32), (qx1 - qx0, qy1 - qy0), interpolation=cv2.INTER_AREA)
                ncc_onay.append(round(R.ncc(R.lum(kq), R.lum(ilan_onay[j][qy0:qy1, qx0:qx1])), 4))
        if i in KT:
            kontak[i] = f.copy()
    O['kare_ortalama_min'] = round(min(ort), 1)
    kapi['siyah kare yok (her kare ortalama >= 20)'] = len(ort) == 240 and min(ort) >= 20
    O['poster_disi_sabit_fark_max'] = round(max(sabit_fark), 3)
    kapi['baslik/zemin sabit (poster disi ortalama fark <= 0,5; ilan poster disi <= 1)'] = max(sabit_fark) <= 0.5 and O['ilan_poster_disi_fark_max'] <= 1
    hk = [i for i, h in enumerate(hareket) if h > 0.001]
    O['hareket_kareleri'] = [hk[0], hk[-1]] if hk else []; O['hareket_sn'] = [round(hk[0] / FPS, 2), round(hk[-1] / FPS, 2)] if hk else []
    kapi['hareket yalniz 1-6 sn, 0-1 ve 6-8 sn tam tasarim'] = bool(hk) and hk[0] >= ONCE and hk[-1] < ONCE + HAREKET
    O['poster_ilan_psnr_min'] = min(ps_ilan)
    kapi['poster bolgesi motor kareleriyle ayni (PSNR >= 35)'] = min(ps_ilan) >= 35
    if ncc_onay:
        O['onayli_ilan_mp4_benzerlik_ncc'] = ncc_onay

    # yerlesim
    sag_pay = (W - SAG) - (PX + PW); ust_b = Y0 + t_y0 - UST; alt_b = (H - ALT) - (PY + PH)
    O['yerlesim'].update(poster_sag_pay=sag_pay, poster_sol_x=PX, poster_sag_x=PX + PW, ust_bosluk=ust_b, alt_bosluk=alt_b)
    tm = (t_x0 + t_x1) / 2 + dx; pm = PX + PW / 2
    O['yerlesim'].update(baslik_merkez=tm, poster_merkez=pm)
    kapi['yerlesim (poster 848-852 px, sag kenar 898; baslik merkezi = poster merkezi +-1; ara 40-50; ust/alt farki <= 2)'] = (
        848 <= PW <= 852 and PX + PW == SAG_X and abs(tm - pm) <= 1 and 40 <= O['yerlesim']['ara'] <= 50 and abs(ust_b - alt_b) <= 2)

    # ilk kare urun NCC (pin ile): poster ve baslik
    pin = Image.open(PIN).convert('RGB'); o = 1000 / R.PIN_W
    pk = lambda cx0, cy0, cx1, cy1, w, h: np.asarray(pin.resize((w, h), Image.LANCZOS, box=((cx0 - R.PIN_X0) * o, (cy0 - R.PIN_Y0) * o,
                                                                                        (cx1 - R.PIN_X0) * o, (cy1 - R.PIN_Y0) * o)))
    g0 = R.lum(k0)
    pp = pk(bx0 / SB, by0 / SB, bx1 / SB, by1 / SB, PW, PH)
    O['ilk_kare_ncc_poster'] = round(R.ncc(g0[PY + 3:PY + PH - 3, PX + 3:PX + PW - 3], R.lum(pp)[3:-3, 3:-3]), 5)
    ty0, ty1 = t_y0 - 8, t_y1 + 8
    pt = pk(R.PIN_X0, ty0 / S, R.PIN_X0 + R.PIN_W, ty1 / S, round(R.PIN_W * S), ty1 - ty0)
    vx0 = round(R.PIN_X0 * S)
    O['ilk_kare_ncc_baslik'] = round(R.ncc(g0[Y0 + ty0:Y0 + ty1, vx0 + dx:vx0 + dx + pt.shape[1]], R.lum(pt)), 5)   # kaydirilmis baslik
    O['ilk_kare_ortalama'] = round(ort[0], 1)
    kapi['ilk kare urun NCC >= 0,99 (pin; poster ve baslik), siyah degil'] = O['ilk_kare_ncc_poster'] >= 0.99 and O['ilk_kare_ncc_baslik'] >= 0.99 and ort[0] >= 20

    # arayuz
    bk = (t_x0 + dx, Y0 + t_y0, t_x1 + dx, Y0 + t_y1); pk9 = (PX, PY, PX + PW, PY + PH)
    pay = lambda b: {'sol': b[0] - SOL, 'sag': (W - SAG) - b[2], 'ust': b[1] - UST, 'alt': (H - ALT) - b[3]}
    O['baslik_kutu'] = bk; O['poster_kutu'] = pk9; O['pay_baslik'] = pay(bk); O['pay_poster'] = pay(pk9)
    kapi['baslik ve poster arayuz icinde (ust 230, alt 1536, sag 918; baslik sag pay >= 3, poster sag pay >= 20; kare icinde)'] = (
        pay(bk)['sag'] >= 3 and pay(pk9)['sag'] >= 20 and min(pay(bk).values()) >= 0 and min(pay(pk9).values()) >= 0)

    # dikey cizgi + ek yeri (yalniz zemin sutunlari: poster ve golgesi disi)
    l0 = R.lum(k0.astype(np.float32)); hp = l0 - cv2.GaussianBlur(l0, (0, 0), sigmaX=20, sigmaY=0.01)
    gol = 1 - gb
    alt0 = max(H - 360, int(np.where(gol.max(1) > 0.002)[0].max()) + 1)
    cz = float(hp[Y0 + 380:Y0 + 740, 1010:1070].mean(0).std())      # kapagin kendi zemini (poster sagi, golge disi)
    O['dikey_cizgi'] = {'ust': round(float(hp[0:Y0 - 20, 30:W - 30].mean(0).std()), 3), 'alt': round(float(hp[alt0:H, 30:W - 30].mean(0).std()), 3),
                        'alt_satirlar': [alt0, H], 'kapak_zemini': round(cz, 3)}
    kapi['uzatmada dikey cizgi yok (sutun ortalamasi std <= 1,5 x kapak zemini)'] = max(O['dikey_cizgi']['ust'], O['dikey_cizgi']['alt']) <= 1.5 * cz
    ek = {}
    for ad, s in (('ust', Y0), ('alt', Y0 + W)):
        sat = slice(s - 24, s + 24)
        kol = (gol[sat].max(0) < 0.002) & ~((np.arange(W) >= PX - 2) & (np.arange(W) < PX + PW + 2) & (PY - 2 < s + 24) & (PY + PH + 2 > s - 24))
        p = l0[:, kol].mean(1)
        ya = np.arange(s - 24, s); yb = np.arange(s, s + 24)
        fa = np.polyfit(ya, p[ya], 1); fb = np.polyfit(yb, p[yb], 1)
        dv = np.abs(np.diff(l0[:, kol], axis=0)).mean(1)
        oran = float(dv[s - 1] / np.median(np.r_[dv[s - 20:s - 2], dv[s + 1:s + 19]]))
        ek[ad] = {'y': s, 'sutun': int(kol.sum()), 'sicrama': round(float(np.polyval(fb, s - 0.5) - np.polyval(fa, s - 0.5)), 3),
                  'egim_once': round(float(fa[0]), 4), 'egim_sonra': round(float(fb[0]), 4), 'ek_satiri_fark_orani': round(oran, 3)}
    O['ek_yeri'] = ek
    be = O['baslik_eski_yer']
    kapi['ek yeri ve basligin eski yeri gorunmuyor (sicrama < 1,0; ek satiri <= 1,5x; eski yer fark <= 1,5, doku 0,7-1,3)'] = (
        all(abs(e['sicrama']) < 1.0 and e['ek_satiri_fark_orani'] <= 1.5 for e in ek.values()) and abs(be['ortalama_fark']) <= 1.5 and 0.7 <= be['doku_std_orani'] <= 1.3)

    # ---------- 6. gorseller
    try:
        fk = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except OSError:
        fk = ImageFont.load_default()
    im = Image.fromarray(k0).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for r in ((0, 0, W, UST), (0, H - ALT, W, H), (W - SAG, UST, W, H - ALT)):
        dr.rectangle(r, fill=(255, 0, 0, 70))
    dr.rectangle((SOL, UST, W - SAG, H - ALT), outline=(255, 255, 0, 255), width=2)
    for b, c in ((bk, (0, 255, 0, 255)), (pk9, (0, 200, 255, 255))):
        dr.rectangle(b, outline=c, width=3)
    for s in (Y0, Y0 + W):
        dr.line((0, s, 24, s), fill=(255, 255, 255, 200), width=2); dr.line((W - 24, s, W, s), fill=(255, 255, 255, 200), width=2)
    im = Image.alpha_composite(im, ov).convert('RGB'); dr = ImageDraw.Draw(im)
    dr.text((20, 20), f'{CIFT} v3 ilk kare | arayuz: ust {UST}, alt {H - ALT}, sag {W - SAG} (kirmizi)', font=fk, fill=(255, 255, 255))
    dr.text((20, 48), f"poster {PW}x{PH} (x {PX}-{PX + PW}, olcek {SB:.3f}), sag pay {sag_pay}", font=fk, fill=(0, 200, 255))
    dr.text((20, 76), f"baslik pay {O['pay_baslik']}", font=fk, fill=(0, 255, 0))
    dr.text((20, 104), f"baslik-poster ara {O['yerlesim']['ara']} px; ust bosluk {ust_b}, alt bosluk {alt_b}; baslik merkezi {tm:g} = poster merkezi {pm:g}", font=fk, fill=(255, 255, 255))
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

    yk = Image.new('RGB', (1080, 2 * 400 + 3 * 50), 'white'); dr = ImageDraw.Draw(yk)
    for n, (s, xa) in enumerate(((Y0, 270), (Y0 + W, 540))):
        y = 50 + n * 450
        dr.text((10, y - 40), f'%200 yakin kirpim: ek yeri y {s} (kirpim ortasi), x {xa}-{xa + 540}; isaret yok', font=fk, fill=(20, 20, 20))
        yk.paste(Image.fromarray(k0[s - 100:s + 100, xa:xa + 540]).resize((1080, 400), Image.LANCZOS), (0, y))
    yk.save(os.path.join(OUT, 'YAKIN_EK_200.jpg'), quality=95)

    # ---------- 7. rapor
    gecti = all(kapi.values())
    O['kapilar'] = kapi; O['sonuc'] = 'PASS' if gecti else 'FAIL'; O['sure_sn'] = round(time.time() - t0)
    json.dump(O, open(os.path.join(OUT, 'OLCUM.json'), 'w'), indent=1, default=str)
    tz = O['toz_2_4sn']
    sat = [f'YIL DONUMU 9:16 SOSYAL VIDEO ORNEGI v3 {CIFT}: {O["sonuc"]} (Metricool/hesap yazma 0, toplu uretim 0)',
           f"poster: {PW}x{PH} px, x {PX}-{PX + PW}, y {PY}-{PY + PH}; olcek {SB:.4f} (motor {V}x{V}, kaynak kapak 2400; buyutme yok); sag pay {sag_pay} (918'e)",
           f"baslik: v1/v2 boyutu (olcek {S}), kuculme yok; poster merkezine hizali ({tm:g} / {pm:g}; kapaktaki yerinden {dx} px), kutu {bk}, pay {O['pay_baslik']}",
           f"basligin eski yeri: {be['px']} px, cevre yuzeyine gore ortalama fark {be['ortalama_fark']}, doku std orani {be['doku_std_orani']}",
           f"baslik-poster ara {O['yerlesim']['ara']} px; ust bosluk {ust_b}, alt bosluk {alt_b} (arayuz 230-1536 icinde); poster pay {O['pay_poster']} (sol = kare kenarina)",
           f"dosya: {d['boyut']} {d['codec']} {d['profil']} {d['pix_fmt']} {d['fps']} fps, {d['kare']} kare, {d['sure']} sn, ses akisi {d['ses_akisi']}, {d['mb']} MB",
           f"motor: yildonumu_video.py (f57fd17, dosya degistirilmeden; VW=VH={V}), N {ic['N']} (" + ' -> '.join(str(t['N']) for t in O['toz_turlari']) + f"), {F.shape[0]} kare; poster disi fark en cok {O['ilan_poster_disi_fark_max']}",
           f"zaman: 0-1 sn tam tasarim, 1-6 sn motor 0-5 sn (poster kutusu), 6-8 sn tam tasarim; olculen hareket {O['hareket_sn']} sn",
           f"ilk kare: pin ile NCC poster {O['ilk_kare_ncc_poster']}, baslik {O['ilk_kare_ncc_baslik']}; ortalama parlaklik {O['ilk_kare_ortalama']}",
           f"siyah kare: kare ortalamasi en az {O['kare_ortalama_min']} (esik 20)",
           f"poster bolgesi / motor kareleri PSNR en az {O['poster_ilan_psnr_min']} dB; baslik/zemin sabit: poster disi ortalama fark en cok {O['poster_disi_sabit_fark_max']}",
           f"ek yeri: " + '; '.join(f"y {e['y']} ({e['sutun']} zemin sutunu) sicrama {e['sicrama']}, egim {e['egim_once']}/{e['egim_sonra']}, ek satiri orani {e['ek_satiri_fark_orani']}" for e in ek.values()),
           f"dikey cizgi (sutun ortalamasi std): ust {O['dikey_cizgi']['ust']}, alt {O['dikey_cizgi']['alt']}, kapak zemini {O['dikey_cizgi']['kapak_zemini']} (esik 1,5x)",
           f"golge: kapak kurali (+16/+30, sigma 40, guc 0,5) poster olcegiyle x {SB:.3f}; kucuk posterin golgesi tersiyle kaldirildi",
           f"toz yogunlugu 2-4 sn (alan basina, onayli CL ilan ile, esik +-%10): " + ', '.join(f"{k} sn {v['v2']}/{v['onayli']} ({v['fark_yuzde']:+.1f}%)" for k, v in tz.items()),
           f"bilgi: onayli ilan mp4 ile poster benzerligi (0,45'e kucultulerek, 0,5 sn arayla) NCC {O.get('onayli_ilan_mp4_benzerlik_ncc')}",
           'KAPILAR: ' + '; '.join(f"{'PASS' if v else 'FAIL'} {k}" for k, v in kapi.items()),
           f"sure {O['sure_sn']} sn"]
    open(os.path.join(OUT, 'OLCUM.txt'), 'w', encoding='utf-8').write('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    sys.exit(0 if gecti else 1)


if __name__ == '__main__':
    main()
