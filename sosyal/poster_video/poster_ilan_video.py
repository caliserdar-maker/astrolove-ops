#!/usr/bin/env python3
"""Poster ilan videosu ORNEK (19 Eki 2026). Kupa ilan videosu mantigi (kupa-orchard dali kupa_orchard/kod/video6b.py, Serdar
18.10): sahne SABIT, 6 sn, 30 fps, sessiz H.264; ilk kare ve son kare = onayli kapak (birebir); 2. kareden toz baslar, ilk
0,3 sn icinde kapaktaki birlesik sembol yumusakca kaybolur; toz iki kucuk burc glifinden akar, sembol ilk varislarla
sifirdan yumusakca olusur, BITIS (5,0 sn) aninda tam; sonra kapak sabit. Zamanlama, toz sayisi (5200), gecikme, yay ve
parlaklik kupa koduyla ayni. Fark: mesaj yazilmaz (baslik, duvar, glifler, isimler, mesaj sabit); toz rengi posterin altini.
Kapak 4:3 (3000x2250) -> video 1440x1080.

Poster kapakta lacivert dikdortgen olarak bulunur; sembol ve glif maskeleri dogrudan kapaktaki posterden (PosterR: altin alfa,
birlesik sembol parcalari, kucuk burclar) cikar (kapak uretim kodu depoda yok). Sembolsuz hal: kupadaki gibi
BOS = KAPAK + (sembolsuz poster - poster) farki; sembolsuz poster = lib.Poster.bg (klasik Telea inpaint, yapay zeka yok).
Poster pikselleri yalniz olceklenir/tasinir; ilk ve son karede kapak oldugu gibi.

QC (ayni betik, kodlanmis videodan): sure, olcu, ses akisi yok, dosya MB; ilk ve son kare ile kapak arasindaki ortalama
mutlak fark (kapagin kayipsiz 4:2:0 kodlamasindaki fark + 0.2'den kucuk); sembol kutusunda kapakla farkin kalici olarak son karenin (kapak) kodlama tabanina + 0.5 indigi ilk kare
(sembol tam; crf 12, 4:2:0 kaybi taban olarak olculur); sembol sondugu anda kutudaki altin
artigi (cevre laciverde +-15), kapakta sembol ve gliflerde altinlik >= 40, poster orani 1.40-1.60. KONTAK.jpg: 0/1/2/3/4/5 sn
+ son kare; MASKE.jpg: sembol (kirmizi) ve glif (yesil) maskeleri kapak uzerinde.
Kullanim: python3 -I poster_ilan_video.py <kapak.jpg> <cikti_dizini> <ad>"""
import json, os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import pin_uret as PU

KAPAK, OUT, AD = sys.argv[1:4]
VW, VH, FPS, SURE, SILME, BITIS = 1440, 1080, 30, 6.0, 0.3, 5.0
N = 5200
ESIK_IK = 0.2                     # ilk/son kare: kayipsiz 4:2:0 tabaninin en fazla 0.2 ustu
rng = np.random.default_rng(11)
t0 = time.time()
os.makedirs(OUT, exist_ok=True)
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))
R = {}

# ---------- kapak ve poster
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
R['kapak_olcu'] = f'{kap_src.shape[1]}x{kap_src.shape[0]}'
KAP8 = cv2.resize(kap_src, (VW, VH), interpolation=cv2.INTER_AREA)
KAP = KAP8.astype(np.float32)

# ---------- poster kapakta: koyu dikdortgen (duvar acik bej). 1. kosuda (39291450782)
# kaynak poster -> kapak SIFT eslesmesi yanlis oturdu (61 ic nokta, sembol maskesinde altinlik -1.1): parca ayrimi artik
# dogrudan kapaktaki poster uzerinde (PosterR), eslesme yok.
kf = kap_src.astype(np.float32); lum_ = kf @ np.float32([0.299, 0.587, 0.114])
lac = (lum_ < 90).astype(np.uint8)      # koyu bolge (posterin alt kenari neredeyse siyah, B > R sarti orada tutmaz)
lac = cv2.morphologyEx(lac, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(lac, 8)
bi = 1 + int(np.argmax(st_[1:, 4]))
x0, y0, cw, ch = (int(v) for v in st_[bi, :4]); x1, y1 = x0 + cw, y0 + ch
R['poster_kutu_kapak'] = [x0, y0, cw, ch]; R['poster_oran'] = round(ch / cw, 3)
s_ = 2000 / cw
tmp = os.path.join(OUT, '_poster_kapaktan.png')
Image.fromarray(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC)).save(tmp)
P = PU.PosterR(tmp); os.remove(tmp)


def vid(m):
    """poster (2000 px genislik) uzayindaki katman -> kapak -> video (1440x1080)."""
    c = np.zeros(kap_src.shape[:2] + m.shape[2:], np.float32)
    c[y0:y1, x0:x1] = cv2.resize(m.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA)
    return cv2.resize(c, (VW, VH), interpolation=cv2.INTER_AREA)


# ---------- maskeler (poster uzayi) -> video
ids = [c[0] for c in P.merged_parts]
msym = np.isin(P.lab, ids).astype(np.uint8)
msym_g = cv2.dilate(msym, np.ones((9, 9), np.uint8)).astype(np.float32)
msym_g = cv2.GaussianBlur(msym_g, (0, 0), 2.0)                        # sembol bolgesi (yumusak kenar)
MS_p = np.clip(P.alpha * cv2.dilate(msym, np.ones((7, 7), np.uint8)), 0, 1)   # sembolun altin alfasi
MG_p = np.zeros_like(P.alpha)
for s2 in (P.sign_a, P.sign_b):
    _, x, y, w, h, _ = s2
    MG_p[y:y + h, x:x + w] = P.alpha[y:y + h, x:x + w]
D_p = (P.bg - P.img) * msym_g[..., None]                              # sembolsuz - tam (yalniz sembol bolgesinde)
MS, MG, DIFF, MREG = vid(MS_p), vid(MG_p), vid(D_p), vid(msym_g)
PK = vid(np.ones_like(P.alpha)) > 0.99                                # poster alani (video)
FULL = KAP
BASE = np.clip(KAP + DIFF, 0, 255)
ys, xs = np.where(MREG > 0.05)
SK = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))   # sembol kutusu (video px)
R['sembol_kutu'] = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
rb = lambda im, m=None: float((im[..., 0] - im[..., 2])[(MS > 0.5) if m is None else m].mean())   # altinlik (R - B)
cevre = (MREG < 0.01) & PK & (cv2.dilate((MREG > 0.05).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0)
R['sembol_altinlik'] = {'kapak': round(rb(KAP), 1), 'sembolsuz': round(rb(BASE), 1), 'cevre_lacivert': round(rb(KAP, cevre), 1),
                        'glif_kapak': round(rb(KAP, MG > 0.5), 1)}
dbg = KAP.copy(); dbg[MS > 0.5] = dbg[MS > 0.5] * 0.3 + np.float32([255, 0, 0]) * 0.7
dbg[MG > 0.5] = dbg[MG > 0.5] * 0.3 + np.float32([0, 255, 0]) * 0.7
Image.fromarray(np.clip(dbg, 0, 255).astype(np.uint8)).resize((720, 540), Image.LANCZOS).save(os.path.join(OUT, 'MASKE.jpg'), quality=88)

# ---------- toz (kupa video6b ile ayni davranis)


def noktalar(m, n):
    ys_, xs_ = np.where(m > 0.35)
    i = rng.choice(len(xs_), n, replace=True)
    return np.stack([xs_[i], ys_[i]], 1).astype(np.float32) + rng.random((n, 2)).astype(np.float32) - 0.5


src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
yay = -(8 + 16 * rng.random(N).astype(np.float32))
gold = P.ramp.astype(np.float32)                                      # posterin altin rampasi (karanliktan parlaga)
renk = np.where((rng.random(N) < 0.22)[:, None], gold[235], gold[rng.integers(120, 220, N)])
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)
nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))


def kare(i):
    if i == 0 or i >= nB:
        return KAP8
    tt = i / (nB - 1)
    uu = np.clip((tt - gec) / 0.38, 0, 1)
    # ilk varislarla sifirdan baslar, BITIS'te tam; agirlik sembol bolgesi (BITIS'te tam kapaga doner, kenar artigi yok)
    A = (ease((tt - 0.36) / 0.64) * np.clip(MREG, 0, 1))[..., None]
    f = BASE * (1 - A) + FULL * A
    if i <= nS:                                                        # ilk 0,3 sn: kapaktaki sembol yumusakca kaybolur
        e = ease(i / nS)
        f = KAP * (1 - e) + f * e
    ue = uu * uu * (3 - 2 * uu)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
    gor = (uu > 0) & (uu < 1)
    xi, yi = p[gor, 0].astype(int), p[gor, 1].astype(int)
    ok = (xi >= 0) & (xi < VW) & (yi >= 0) & (yi < VH)
    a_ = (par[gor] * np.sin(np.pi * uu[gor]))[ok]
    al = np.zeros((VH, VW), np.float32); kat = np.zeros((VH, VW, 3), np.float32)
    np.add.at(al, (yi[ok], xi[ok]), a_)
    for c in range(3):
        np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
    al = cv2.GaussianBlur(al, (0, 0), 0.9) * 2.0
    kat = cv2.GaussianBlur(kat, (0, 0), 0.9) * 2.0
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None]
    return np.clip(f * (1 - a3) + rk * a3, 0, 255).astype(np.uint8)


mp4 = os.path.join(OUT, f'{AD}_ilan_video.mp4')
enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                        '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '12',
                        '-preset', 'slow', '-movflags', '+faststart', mp4], stdin=subprocess.PIPE)
for i in range(nT):
    enc.stdin.write(kare(i).tobytes())
    if i % 30 == 0 or i == nT - 1:
        g = time.time() - t0
        print(f'kare {i + 1}/{nT} %{100 * (i + 1) // nT} gecen {g:.0f} sn kalan ~{g / (i + 1) * (nT - i - 1):.0f} sn', flush=True)
enc.stdin.close(); enc.wait()

# ---------- QC (kodlanmis videodan)
j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', mp4],
                              capture_output=True, text=True, check=True).stdout)
vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
R['video'] = {'olcu': f"{vs['width']}x{vs['height']}", 'oran': round(vs['width'] / vs['height'], 4), 'kare': int(vs['nb_read_frames']),
              'sure_sn': round(float(j['format']['duration']), 3), 'fps': vs['r_frame_rate'], 'codec': vs['codec_name'],
              'ses_akisi': any(s['codec_type'] == 'audio' for s in j['streams']),
              'boyut_mb': round(os.path.getsize(mp4) / 1e6, 2)}
dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
FR = np.frombuffer(dec, np.uint8).reshape(-1, VH, VW, 3)
fark = lambda a_, b_: round(float(np.abs(a_.astype(np.float32) - b_.astype(np.float32)).mean()), 3)
R['ilk_kare_fark'] = fark(FR[0], KAP8); R['son_kare_fark'] = fark(FR[-1], KAP8)
tb = os.path.join(OUT, '_taban.mp4')                                   # 4:2:0 donusum tabani: kapak, kayipsiz (crf 0) kodlama
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}', '-r', str(FPS), '-i', '-',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=KAP8.tobytes(), check=True)
tf = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', tb, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  capture_output=True, check=True).stdout, np.uint8).reshape(VH, VW, 3)
R['taban_420_kayipsiz'] = fark(tf, KAP8); os.remove(tb)
sk = [fark(f[SK], KAP8[SK]) for f in FR]
taban = sk[-1]                                                        # son kare = kapak: kutudaki kodlama kaybi tabani
tam = next((i for i in range(1, len(FR)) if all(x <= taban + 0.5 for x in sk[i:])), None)
R['sembol_kutu_taban'] = taban
R['sembol_tam_kare'] = tam; R['sembol_tam_sn'] = round(tam / FPS, 3) if tam is not None else None
R['sembol_kutu_fark_en_buyuk'] = {'kare': int(np.argmax(sk)), 'fark': max(sk)}
R['sembol_altinlik']['sondugu_an_video'] = round(rb(FR[nS].astype(np.float32)), 1)
kapi = {'olcu_4_3': R['video']['olcu'] == f'{VW}x{VH}', 'kare_180': R['video']['kare'] == nT,
        'sure_6': abs(R['video']['sure_sn'] - SURE) < 0.05, 'ses_yok': not R['video']['ses_akisi'],
        'ilk_kare_kapak': R['ilk_kare_fark'] <= R['taban_420_kayipsiz'] + ESIK_IK,
        'son_kare_kapak': R['son_kare_fark'] <= R['taban_420_kayipsiz'] + ESIK_IK,
        'sembol_tam_bitiste': tam is not None and tam <= nB,
        'poster_oran_2_3': 1.40 <= R['poster_oran'] <= 1.60, 'sembol_altin': R['sembol_altinlik']['kapak'] >= 40,
        'glif_altin': R['sembol_altinlik']['glif_kapak'] >= 40,
        'sembol_soner': abs(R['sembol_altinlik']['sondugu_an_video'] - R['sembol_altinlik']['cevre_lacivert']) <= 15}
R['kapi'] = kapi; R['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL'
json.dump(R, open(os.path.join(OUT, f'{AD}_QC.json'), 'w'), indent=1, default=str)

# ---------- KONTAK: 0 / 1 / 2 / 3 / 4 / 5 sn + son kare, 4:3
tw, th, ust = 480, 360, 40
sec = [('0 sn', 0), ('1 sn', 30), ('2 sn', 60), ('3 sn', 90), ('4 sn', 120), ('5 sn', 150), (f'son ({len(FR) - 1})', len(FR) - 1)]
K = Image.new('RGB', (4 * tw + 3 * 8, 2 * (th + ust) + 8), (245, 245, 245)); dr = ImageDraw.Draw(K)
try:
    fo = ImageFont.truetype('DejaVuSans-Bold.ttf', 24)
except OSError:
    fo = ImageFont.load_default()
for n_, (et, i) in enumerate(sec):
    x, y = (n_ % 4) * (tw + 8), (n_ // 4) * (th + ust + 8)
    dr.text((x + 6, y + 6), et, fill=(0, 0, 0), font=fo)
    K.paste(Image.fromarray(FR[i]).resize((tw, th), Image.LANCZOS), (x, y + ust))
K.save(os.path.join(OUT, 'KONTAK.jpg'), quality=92)
print(json.dumps(R, ensure_ascii=False, default=str))
print('SONUC', R['sonuc'], f'{time.time() - t0:.0f} sn')
sys.exit(0 if R['sonuc'] == 'PASS' else 1)
