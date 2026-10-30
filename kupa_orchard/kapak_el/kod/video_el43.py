#!/usr/bin/env python3
"""Kupa ilan videosu, el sahnesi 4:3 (1440x1080, 30 fps, 6 sn, sessiz H.264). Onayli V6 akisi (video6b, N 10400, sigma 0.45)
tek kupa on yuz sahnesine uyarlanmistir:
- Ilk ve son kare = o ciftin onayli kapak dosyasi (birebir, 1440x1080'e kucultulmus).
- 2. kareden toz baslar; ilk 0,3 sn icinde kapaktaki ozgun sembol yumusakca kaybolur.
- Toz iki kucuk burc isaretinden ozgun semobole akar; sembol ilk varislarla sifirdan olusur; BITIS sn'de tam, sonra kapak sabit.
- Mesaj kupanin ARKA yuzunde oldugu icin bu sahnede gorunmez; mesaj yazilma adimi yoktur (maske bossa atlanir).
Katmanlar (bos kupa, sembolsuz, maskeler) baski_kes.py bayraklariyla uretilip kapak_canva4.py ile ayni sahneye giydirilir.
Ortam: KAYIT=<kapak78 KAYIT.tsv> verilirse sembol surumu kapaklarla ayni olmali, degilse durur.
Kullanim: python3 -I video_el43.py <CIFT> <kapak_jpg> <cikti_mp4> [bitis_sn]"""
import os, shutil, subprocess, sys, time, pathlib, tempfile
import numpy as np, cv2
from PIL import Image

BURASI = pathlib.Path(__file__).resolve().parent
REPO = BURASI.parents[2]
KOD = REPO / 'kupa_orchard/kod'
IS = BURASI.parent
REF = 'refs/kapak78/sembol'          # kapak78.py'nin cektigi sembol dali (kupa-printful-sonuc)
CIFT, KAPAK, OUT = sys.argv[1:4]
BITIS = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
W, H, FPS, SURE, SILME = 1440, 1080, 30, 6.0, 0.3
N, SIGMA = 20800, 0.45                # toz: onayli V6 (10400) x 2 (Serdar 30 Eki); sigma V6
rng = np.random.default_rng(11)
t0 = time.time()
TEMIZ = ('D_IN', 'SABIT_YUKSEKLIK', 'SEMBOL_YOK', 'GLIF_YOK', 'MESAJ_YOK', 'IMZA_YOK', 'BURC_YOK', 'BURC_DY', 'BURC_MIN')
ENV = {k: v for k, v in os.environ.items() if k not in TEMIZ}
ENV.update(GOLGE_US='1.0', PARLA='0.7')


def adim(m):
    print(f'[{time.time() - t0:5.1f}s] {m}', flush=True)


def kos(*a, ek=None):
    e = dict(ENV, **(ek or {}))
    r = subprocess.run(['python3', '-I', *map(str, a)], capture_output=True, text=True, env=e)
    if r.returncode:
        sys.exit(f'HATA {pathlib.Path(str(a[0])).name}: {r.stderr[-800:]}')


# 0) sembol surumu kapaklarla ayni olmali (KAYIT ortam degiskeni: kapak78 KAYIT.tsv yolu)
_sha = subprocess.run(['git', '-C', str(REPO), 'rev-parse', REF], capture_output=True, text=True).stdout.strip()
if os.environ.get('KAYIT'):
    _ilk = pathlib.Path(os.environ['KAYIT']).read_text().splitlines()[0].split()
    if not _sha or _ilk[-1] != _sha:
        sys.exit(f'HATA: sembol surumu kapaklarla farkli (ref {_sha[:7]}, kapak kaydi {_ilk[-1][:7]})')

# 1) katmanlar
TMP = pathlib.Path(tempfile.mkdtemp(prefix=f'vid_{CIFT}_'))
(TMP / 'sem').mkdir()
for f in ('ana', 'sol', 'sag'):
    r = subprocess.run(['git', '-C', str(REPO), 'show', f'{REF}:kupa_uretim/sembol/{CIFT}/{f}.png'], capture_output=True)
    if r.returncode:
        sys.exit(f'HATA sembol {CIFT}/{f}: {r.stderr.decode(errors="replace")}')
    (TMP / 'sem' / f'{f}.png').write_bytes(r.stdout)
b1, b2 = (x.capitalize() for x in CIFT.split('_'))
for ad, bayrak in (('full', ()), ('basem', ('SEMBOL_YOK', 'MESAJ_YOK')), ('nosym', ('SEMBOL_YOK',)),
                   ('noglif', ('GLIF_YOK',)), ('nomes', ('MESAJ_YOK',))):
    kos(KOD / 'baski_kes.py', KOD.parent / 'varlik/kes/ORANGER', TMP / 'sem', 'Emily', 'James', b1, b2,
        'My favorite place is with you', '10,40,24', TMP / ad, ek={b: '1' for b in bayrak})
full = np.asarray(Image.open(TMP / 'full_baski_11oz.png').convert('RGB')).astype(float)
Image.fromarray(np.full(full.shape, 255, np.uint8)).save(TMP / 'beyaz.png')
for ad in ('nosym', 'noglif', 'nomes'):
    x = np.asarray(Image.open(TMP / f'{ad}_baski_11oz.png').convert('RGB')).astype(float)
    dm = np.clip(255 - np.abs(full - x).max(-1) * 1.1, 0, 255).astype(np.uint8)
    Image.fromarray(np.stack([dm] * 3, -1)).save(TMP / f'mask_{ad}.png')
SAHNE, GEO = IS / 'sahne/A3_uzun2.png', IS / 'sahne/geo_A3b.json'
for ad in ('full_baski_11oz', 'basem_baski_11oz', 'beyaz', 'mask_nosym', 'mask_noglif', 'mask_nomes'):
    kos(BURASI / 'kapak_canva4.py', SAHNE, TMP / f'{ad}.png', GEO, TMP / f'k_{ad}.png')
adim('katmanlar hazir')


# 2) animasyon
def oku(p):
    return cv2.resize(np.asarray(Image.open(p).convert('RGB')).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)


KAP = np.clip(np.round(oku(KAPAK)), 0, 255)
F_ESKI, B_ESKI, BEY = oku(TMP / 'k_full_baski_11oz.png'), oku(TMP / 'k_basem_baski_11oz.png'), oku(TMP / 'k_beyaz.png')
FULL = KAP
BASE = np.clip(KAP + (B_ESKI - F_ESKI), 0, 255)       # fark yalniz sembol (ve gorunmeyen mesaj) bolgesinde


def maske(ad, kat=1.4):
    return np.clip((1 - oku(TMP / f'k_mask_{ad}.png').mean(-1) / np.maximum(BEY.mean(-1), 1)) * kat, 0, 1)


MS, MG, MM = maske('nosym'), maske('noglif'), maske('nomes')
MM = cv2.dilate(MM, np.ones((3, 3), np.uint8))
MESAJ_VAR = (MM > 0.2).sum() > 50
adim(f'maske alanlari: sembol {int((MS > 0.35).sum())} px, glif {int((MG > 0.35).sum())} px, mesaj {int((MM > 0.2).sum())} px '
     f'({"var" if MESAJ_VAR else "gorunmuyor, adim atlanir"})')
assert (MS > 0.35).sum() > 500 and (MG > 0.35).sum() > 50, 'sembol ya da glif maskesi bos'
XX = np.arange(W, dtype=np.float32)[None, :].repeat(H, 0)
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))


def yazim(x0, x1, p, yum=10):
    esik = x0 - yum + (x1 - x0 + 2 * yum) * p
    return np.clip((esik - XX) / yum, 0, 1)


if MESAJ_VAR:
    _xs = np.where(MM > 0.2)[1]
    mx0, mx1 = _xs.min(), _xs.max()


def noktalar(m, n):
    ys, xs = np.where(m > 0.35)
    i = rng.choice(len(xs), n, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((n, 2)).astype(np.float32) - 0.5


src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
yay = -(8 + 16 * rng.random(N).astype(np.float32)) * (H / 1080)
YESIL, ALTIN = np.array([22, 60, 36], np.float32), np.array([196, 150, 64], np.float32)
renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, YESIL)
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)

nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                      '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                      '-preset', 'slow', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
anlar = {0: '0.0', round(0.15 * FPS): '0.15', round(1.4 * FPS): '1.4', round(2.8 * FPS): '2.8', nT - 1: 'son'}
for i in range(nT):
    if i == 0 or i >= nB:
        f = KAP
    else:
        tt = i / (nB - 1)
        am = yazim(mx0, mx1, ease(tt)) * MM if MESAJ_VAR else 0
        uu = np.clip((tt - gec) / 0.38, 0, 1)
        asym = ease((tt - 0.36) / 0.64) * MS
        A = np.clip(am + asym, 0, 1)[..., None]
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
        Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(OUT.replace('.mp4', f'_{anlar[i]}.jpg'), quality=90)
    if i % 30 == 0 or i == nT - 1:
        g = time.time() - t0
        print(f'  kare {i + 1}/{nT} %{100 * (i + 1) // nT} (gecen {g:.0f}s)', flush=True)
p.stdin.close()
if p.wait():
    sys.exit('HATA ffmpeg')
shutil.rmtree(TMP, ignore_errors=True)
print('tamam', OUT, f'{time.time() - t0:.0f}s')
