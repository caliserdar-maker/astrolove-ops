#!/usr/bin/env python3
"""Kapak videosu v2: isim + tagline dongulu (Serdar 28 Eyl: 'isimlerin ve taglinelarin dongusu').
Her cift icin 3 gercek hat baskisi (siparis_dosyasi.py, degistirilmeden):
  V1 EMILY/JAMES  'It Began With a Kiss in the Rain' (TEMP/POD_KAPAK_V3/SIPARIS onbellegi)
  V2 SOPHIE/LIAM  'Where Our Story Began'
  V3 MIA/NOAH     'Two Signs, One Story'
Her varyant kapak_v8_kur.py ile v9 sahnesine oturur; ffmpeg: 3 klip (hafif zoom) + 0.8 sn crossfade,
toplam ~11.6 sn, 2880x2160, 30 fps, sessiz. Poster/isim/tagline asla yeniden cizilmez.
V2-V3 baskilari TEMP/POD_VIDEO_V2/SIPARIS onbelleginde saklanir (varsa yeniden uretilmez).
QC (her video): boyut, sure 11-12.5 sn, ilk kare = V1 kapagi NCC >= 0.99. FAIL -> cikis 1.
ETA sayaci: islenen/toplam, gecen, kalan, yuzde.
Kullanim: video_v2_toplu.py SB_DIZIN CIFT [CIFT ...]
"""
import base64
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[2]
SB = Path(sys.argv[1])
CIFTLER = sys.argv[2:]
OUT = Path('_out'); OUT.mkdir(exist_ok=True)
W = Path('_work'); (W / 'baski').mkdir(parents=True, exist_ok=True)
SAHNE = W / 'sahne_1213.png'
Image.open(KOK / 'data/pod/kapak_sahne_v9.png').convert('RGB').resize((1213, 910), Image.LANCZOS).save(SAHNE)

V1_SIP = 'gdrive:ASTROLOVE/TEMP/POD_KAPAK_V3/SIPARIS'
V23_SIP = 'gdrive:ASTROLOVE/TEMP/POD_VIDEO_V2/SIPARIS'
VARYANT = [('EMILY', 'JAMES', 'It Began With a Kiss in the Rain'),
           ('SOPHIE', 'LIAM', 'Where Our Story Began'),
           ('MIA', 'NOAH', 'Two Signs, One Story')]
RENK, BOY = 'MIDNIGHT_BLUE', '11x14'


def rc(*a, kontrol=True):
    return subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                          capture_output=True, text=True, check=kontrol)


def baski_al(cift, i1, i2, mesaj, v1):
    rec = f'{cift}_{RENK}_{BOY}' if v1 else f'{cift}_{i1}_{i2}'
    yer = W / 'baski' / rec / f'BASKI_{BOY}.jpg'
    yer.parent.mkdir(parents=True, exist_ok=True)
    kaynak = V1_SIP if v1 else V23_SIP
    if rc('copyto', f'{kaynak}/{rec}/BASKI_{BOY}.jpg', str(yer), kontrol=False).returncode == 0 and yer.exists():
        return yer
    if v1:
        raise SystemExit(f'HATA: V1 onbellekte yok: {rec}. DUR.')
    args = ['--cift', cift, '--renk', RENK, '--boy', BOY, '--isim1', i1, '--isim2', i2,
            '--mesaj-b64', base64.b64encode(mesaj.encode()).decode()]
    kod = ("import sys; sys.path.insert(0, 'scripts/medya_v1'); import siparis_dosyasi as s; "
           f"s.SIP = {V23_SIP!r}; sys.argv = ['siparis_dosyasi.py'] + {args!r}; s.main()")
    subprocess.run([sys.executable, '-c', kod], cwd=SB, check=True)
    hat_cikti = SB / '_siparis' / f'{cift}_{RENK}_{BOY}' / f'BASKI_{BOY}.jpg'
    if not hat_cikti.exists():
        raise SystemExit(f'HATA: hat ciktisi yok: {hat_cikti}. DUR.')
    hat_cikti.replace(yer)
    rc('copyto', str(yer), f'{V23_SIP}/{rec}/BASKI_{BOY}.jpg', kontrol=False)
    return yer


def kapak(baski, cikis):
    r = subprocess.run([sys.executable, str(KOK / 'scripts/pod/kapak_v8_kur.py'), str(SAHNE), str(baski),
                        str(KOK / 'data/pod/cila_cerceve_kaynak.png'), str(cikis),
                        '295', '30', '919', '880'], capture_output=True, text=True)
    son = (r.stdout.strip().splitlines() or ['?'])[-1]
    if son != 'PASS':
        raise SystemExit(f'HATA: kapak FAIL {baski}\n{r.stdout}\n{r.stderr}')


def video(kapaklar, cikis):
    KL, GECIS, FPS = 4.4, 0.8, 30
    girdiler = []
    for k in kapaklar:
        girdiler += ['-loop', '1', '-t', str(KL), '-i', str(k)]
    fil = []
    for j in range(3):
        fil.append(f"[{j}:v]scale=5760:4320,zoompan=z='1+0.03*on/{round(KL*FPS)}':"
                   f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={round(KL*FPS)}:s=2880x2160:fps={FPS}[v{j}]")
    fil.append(f"[v0][v1]xfade=transition=fade:duration={GECIS}:offset={KL - GECIS}[a]")
    fil.append(f"[a][v2]xfade=transition=fade:duration={GECIS}:offset={2 * (KL - GECIS)}[v]")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *girdiler, '-filter_complex', ';'.join(fil),
                    '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium',
                    '-crf', '18', str(cikis)], check=True)


def qc(cikis, kapak1):
    import cv2
    v = cv2.VideoCapture(str(cikis))
    w, h = int(v.get(cv2.CAP_PROP_FRAME_WIDTH)), int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(v.get(cv2.CAP_PROP_FRAME_COUNT)); fps = v.get(cv2.CAP_PROP_FPS)
    ok, kare = v.read(); v.release()
    sure = n / fps
    ref = np.asarray(Image.open(kapak1).convert('RGB').resize((w, h), Image.LANCZOS)).astype(np.float32).mean(2)
    ilk = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB).astype(np.float32).mean(2)
    a = ilk - ilk.mean(); b = ref - ref.mean()
    ncc = float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
    olcum = f'{w}x{h} | {sure:.1f} sn | ilk kare NCC {ncc:.4f}'
    return ((w, h) == (2880, 2160) and 11.0 <= sure <= 12.5 and ncc >= 0.99), olcum


N = len(CIFTLER); fail = 0; t0 = time.time()
sat = ['# VIDEO V2 TOPLU ' + time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), f'Toplam: {N}', '']
for i, c in enumerate(CIFTLER, 1):
    kapaklar = []
    for j, (i1, i2, mesaj) in enumerate(VARYANT):
        b = baski_al(c, i1, i2, mesaj, v1=(j == 0))
        k = W / f'KAP_{c}_{j}.jpg'
        kapak(b, k)
        kapaklar.append(k)
    cikis = OUT / f'VIDEO_{c}.mp4'
    video(kapaklar, cikis)
    ok, olcum = qc(cikis, kapaklar[0])
    sat.append(f'- {c}: {"PASS" if ok else "FAIL"} | {olcum}')
    if not ok:
        fail += 1
    g = time.time() - t0
    print(f'[{i}/{N}] {c} {"PASS" if ok else "FAIL"} | {olcum} | gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s | %{i / N * 100:.0f}', flush=True)

sat += ['', f'PASS: {N - fail} / {N}', 'SONUC ' + ('PASS' if fail == 0 else 'FAIL')]
(OUT / 'OZET.md').write_text('\n'.join(sat) + '\n')
print('SONUC ' + ('PASS' if fail == 0 else 'FAIL'))
sys.exit(1 if fail else 0)
