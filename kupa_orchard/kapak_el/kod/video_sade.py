#!/usr/bin/env python3
"""SADE kupa ilan videosu, el sahnesi 4:3 (1440x1080, 30 fps, 6 sn, sessiz H.264). video_el43.py akisinin sade kupaya uyarlamasi:
- Ilk ve son kare = onayli sade kapak dosyasi (birebir, 1440x1080'e kucultulmus).
- 2. kareden toz baslar; ilk 0,3 sn icinde kapaktaki buyuk burc sembolu yumusakca kaybolur.
- Sade kupada kucuk glif yok: toz isim satirindan (isim ve iki kucuk dal) buyuk semobole akar; sembol ilk varislarla olusur.
- Toz miktari ve sigma video_el43 ile ayni (N 20800, sigma 0.45); toz rengi sembol rengi + %22 altin (stile uyar).
- Cikti once gecici dosyaya yazilir; hata olursa yarim video kalmaz, eski ciktilar basta silinir.
Katmanlar: baski_sade3.py ciktisi (baski png) verilir. Sembol satiri ile isim satiri on yuzde dikey bosluga gore ayrilir;
sembolsuz baski = sembol satiri beyaza boyanmis baski. Hepsi kapak_canva4.py ile ayni sahneye giydirilir.
Urun pikselleri (sembol) yapay zekadan gecmez; yalniz kopyalanir ve harmanlanir.
Kullanim: python3 -I video_sade.py <baski_png> <kapak_jpg> <cikti_mp4> [bitis_sn]"""
import os, shutil, subprocess, sys, time, pathlib, tempfile
import numpy as np, cv2
from PIL import Image

BURASI = pathlib.Path(__file__).resolve().parent
IS = BURASI.parent
if len(sys.argv) not in (4, 5):
    sys.exit(__doc__)
BASKI, KAPAK, OUT = sys.argv[1:4]
BITIS = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
if not 1.0 <= BITIS <= 6.0:
    sys.exit(f'HATA: bitis_sn 1 ile 6 arasinda olmali ({BITIS})')
if not OUT.endswith('.mp4'):
    sys.exit('HATA: cikti .mp4 olmali')
for _e in ('.mp4', '_0.0.jpg', '_0.15.jpg', '_1.4.jpg', '_2.8.jpg', '_son.jpg'):   # eski cikti yeni sanilmasin
    pathlib.Path(OUT[:-4] + _e).unlink(missing_ok=True)
W, H, FPS, SURE, SILME = 1440, 1080, 30, 6.0, 0.3
N, SIGMA = 20800, 0.45
rng = np.random.default_rng(11)
t0 = time.time()
TEMIZ = ('D_IN', 'SABIT_YUKSEKLIK', 'SEMBOL_YOK', 'GLIF_YOK', 'MESAJ_YOK', 'IMZA_YOK', 'BURC_YOK', 'BURC_DY', 'BURC_MIN', 'UST_YUM')
ENV = {k: v for k, v in os.environ.items() if k not in TEMIZ}
ENV.update(GOLGE_US='1.0', PARLA='0.7')


def adim(m):
    print(f'[{time.time() - t0:5.1f}s] {m}', flush=True)


def kos(*a):
    r = subprocess.run(['python3', '-I', *map(str, a)], capture_output=True, text=True, env=ENV)
    if r.returncode:
        sys.exit(f'HATA {pathlib.Path(str(a[0])).name}: {r.stderr[-800:]}')


# 1) baski katmanlari (on yuz = baskinin sol yarisi)
TMP = pathlib.Path(tempfile.mkdtemp(prefix='vidsade_'))
p = None
try:
    full = np.asarray(Image.open(BASKI).convert('RGB')).astype(np.int16)
    FH_, FW_ = full.shape[:2]
    if (FW_, FH_) != (2700, 1050):
        sys.exit(f'HATA: baski 2700x1050 (11 oz) olmali, {FW_}x{FH_}')
    murekkep = (255 - full).max(-1) > 20
    on = murekkep[:, :FW_ // 2]
    satir = np.where(on.any(1))[0]
    if len(satir) == 0:
        sys.exit('HATA: on yuzde baski yok')
    bos = np.where(np.diff(satir) > 20)[0]
    if len(bos) < 1:
        sys.exit('HATA: on yuzde sembol ile isim satiri ayrilamadi')
    # isim satiri en alttaki gruptur; sembol ici bosluklar (Libra, Aquarius) sembole dahil kalir
    s0, s1 = satir[0], satir[bos[-1]]
    i0, i1 = satir[bos[-1] + 1], satir[-1]
    if not (i1 - i0) < (s1 - s0):
        sys.exit(f'HATA: isim satiri sembolden yuksek gorunuyor (sembol {s1 - s0} px, isim {i1 - i0} px)')
    orta = (s1 + i0) // 2
    adim(f'sembol satiri y {s0}-{s1}, isim satiri y {i0}-{i1}, ayrim y {orta}')
    nosym = full.copy()
    nosym[:orta, :FW_ // 2] = 255
    if (255 - nosym).max(-1)[:orta, :FW_ // 2].max() != 0:
        sys.exit('HATA: sembol silinemedi')
    Image.fromarray(full.astype(np.uint8)).save(TMP / 'full.png')
    Image.fromarray(nosym.astype(np.uint8)).save(TMP / 'nosym.png')
    Image.fromarray(np.full(full.shape, 255, np.uint8)).save(TMP / 'beyaz.png')
    fark = np.abs(full - nosym).max(-1).astype(float)
    Image.fromarray(np.stack([np.clip(255 - fark * 1.1, 0, 255).astype(np.uint8)] * 3, -1)).save(TMP / 'mask_sym.png')
    kay = np.zeros(full.shape[:2], float)
    kay[orta:, :FW_ // 2] = (255 - full[orta:, :FW_ // 2]).max(-1)
    Image.fromarray(np.stack([np.clip(255 - kay * 1.1, 0, 255).astype(np.uint8)] * 3, -1)).save(TMP / 'mask_kay.png')
    SAHNE, GEO = IS / 'sahne/A3_uzun2.png', IS / 'sahne/geo_A3b.json'
    for ad in ('full', 'nosym', 'beyaz', 'mask_sym', 'mask_kay'):
        kos(BURASI / 'kapak_canva4.py', SAHNE, TMP / f'{ad}.png', GEO, TMP / f'k_{ad}.png')
    adim('katmanlar hazir')

    def oku(p):
        return cv2.resize(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)

    KAP = np.clip(np.round(oku(KAPAK)), 0, 255)
    F_ESKI, B_ESKI, BEY = oku(TMP / 'k_full.png'), oku(TMP / 'k_nosym.png'), oku(TMP / 'k_beyaz.png')
    FULL = KAP
    BASE = np.clip(KAP + (B_ESKI - F_ESKI), 0, 255)

    def maske(ad, kat=1.4):
        return np.clip((1 - oku(TMP / f'k_{ad}.png').mean(-1) / np.maximum(BEY.mean(-1), 1)) * kat, 0, 1)

    MS, MK = maske('mask_sym'), maske('mask_kay')
    adim(f'maske alanlari: sembol {int((MS > 0.35).sum())} px, kaynak {int((MK > 0.35).sum())} px')
    assert (MS > 0.35).sum() > 500 and (MK > 0.35).sum() > 50, 'sembol ya da kaynak maskesi bos'
    # kapak ile katman kapagi ayni mi (baski dosyasi kapaga ait mi): sembol bolgesinde fark kucuk olmali
    _fk = np.abs(KAP - F_ESKI).mean(-1)[MS > 0.5]
    adim(f'kapak ile katman farki (sembol bolgesi, ortalama): {_fk.mean():.1f}')
    if _fk.mean() > 5:            # dogru eslesme ~0.5; yanlis stil 17+ (inceleme 30 Eki)
        sys.exit('HATA: baski dosyasi bu kapaga ait gorunmuyor (sembol bolgesi farkli)')
    ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))

    def noktalar(m, n):
        ys, xs = np.where(m > 0.35)
        i = rng.choice(len(xs), n, replace=True)
        return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((n, 2)).astype(np.float32) - 0.5

    src, dst = noktalar(MK, N), noktalar(MS, N)
    src = src[np.argsort(src[:, 0])]
    dst = dst[np.argsort(dst[:, 0] + rng.random(N).astype(np.float32) * 40)]   # soldan saga eslesme, hafif karisik
    gec = rng.random(N).astype(np.float32) * 0.62
    yay = -(8 + 16 * rng.random(N).astype(np.float32)) * (H / 1080)
    _ink = full[:orta, :FW_ // 2][(255 - full[:orta, :FW_ // 2]).max(-1) > 120]
    ANA = np.median(_ink, 0).astype(np.float32)                       # toz ana rengi = sembol rengi (stile uyar)
    ALTIN = np.array([196, 150, 64], np.float32)
    adim(f'toz rengi {ANA.astype(int).tolist()} + altin')
    renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, ANA)
    par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)

    nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
    GEC = str(TMP / 'video.mp4')
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                          '-preset', 'slow', '-movflags', '+faststart', GEC], stdin=subprocess.PIPE)
    anlar = {0: '0.0', round(0.15 * FPS): '0.15', round(1.4 * FPS): '1.4', round(2.8 * FPS): '2.8', nT - 1: 'son'}
    for i in range(nT):
        if i == 0 or i >= nB:
            f = KAP
        else:
            tt = i / (nB - 1)
            uu = np.clip((tt - gec) / 0.38, 0, 1)
            A = np.clip(ease((tt - 0.36) / 0.64) * MS, 0, 1)[..., None]
            f = BASE * (1 - A) + FULL * A
            if i <= nS:
                e = ease(i / nS)
                f = KAP * (1 - e) + f * e
            ue = uu * uu * (3 - 2 * uu)
            q = src * (1 - ue)[:, None] + dst * ue[:, None]
            q[:, 1] += yay * np.sin(np.pi * ue)
            q[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
            gor = (uu > 0) & (uu < 1)
            xi, yi = q[gor, 0].astype(int), q[gor, 1].astype(int)
            ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
            a_ = (par[gor] * np.sin(np.pi * uu[gor]))[ok]
            al = np.zeros((H, W), np.float32)
            kat = np.zeros((H, W, 3), np.float32)
            np.add.at(al, (yi[ok], xi[ok]), a_)
            for c in range(3):
                np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
            al = cv2.GaussianBlur(al, (0, 0), SIGMA) * 2.0
            kat = cv2.GaussianBlur(kat, (0, 0), SIGMA) * 2.0
            rk = kat / np.maximum(al[..., None], 1e-4)
            a3 = np.clip(al, 0, 0.9)[..., None]
            f = f * (1 - a3) + rk * a3
        p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
        if i in anlar:
            Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(TMP / f'kare_{anlar[i]}.jpg', quality=90)
        if i % 30 == 0 or i == nT - 1:
            print(f'  kare {i + 1}/{nT} %{100 * (i + 1) // nT} (gecen {time.time() - t0:.0f}s)', flush=True)
    p.stdin.close()
    if p.wait():
        sys.exit('HATA ffmpeg')
    p = None
    for k in anlar.values():
        shutil.move(str(TMP / f'kare_{k}.jpg'), OUT[:-4] + f'_{k}.jpg')
    shutil.move(GEC, OUT + '.gecici')
    os.replace(OUT + '.gecici', OUT)
finally:
    if p is not None and p.poll() is None:
        p.kill()
    shutil.rmtree(TMP, ignore_errors=True)
print('tamam', OUT, f'{time.time() - t0:.0f}s')
