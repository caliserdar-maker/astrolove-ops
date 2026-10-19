#!/usr/bin/env python3
"""V6 (19 Eki, Serdar): once kupa V6 (referans), sonra poster V6 kupaya gore ayarlanir. Tek script, PASS/FAIL.
Kupa V6 = kupa-orchard video6b.py, yalniz N 5200 -> 10400 ve parcacik sigma 0.9 -> 0.45 (ince toz V5 + 2 kat toz).
Olcumler (iki videoya ayni formul):
  SM = cekirdek sembol pikselleri (kupa: video6b maske('nosym') > 0.95; poster: v6 MS > 0.95), d_t = |f_t - f_son| (kanal max),
  gorunen oran V(t) = ort clip(1 - d_t / d_9, 0, 1) (d_9 = silinmis hal 0,3 sn; d_9 < 20 olan pikseller haric; toz dahil)
  toz yogunlugu D(t) = sembol bolgesinde (SM 7 px genisletilmis) tozlu kare ile toz kapali kopya farki > 8 olan piksel / |SM|
Poster kalibrasyonu: 1) N0 = 26000 ile olc, N = N0 x medyan(D_kupa / D_poster) (D_kupa en buyugunun %20'sinden buyuk kareler);
2) murekkep egrisi c(t) (piksel basina min(c, F), F = yerel toz birikimi): c += V_kupa - V_poster (monoton, son kare 1);
   en fazla 3 tur, tolerans: her 0,5 sn V +-0,05 ve D +-%10 (D_kupa < en buyugunun %20'si ise mutlak %2 en buyuk).
Kullanim: v6_kalibre.py <poster_kapak.jpg> <kupa video/ klasoru> <kupa kapak jpg> <video6b.py> <cikti_dir> <is_dir>"""
import importlib.util, json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('q5', os.path.join(HERE, 'v5_qc.py')); Q = importlib.util.module_from_spec(sp); sp.loader.exec_module(Q)
KAPAK, VD, KK, V6B, OUT, IS = sys.argv[1:7]
os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
FPS, NB = 30, 150
TS = [k * 0.5 for k in range(13)]
PY = sys.executable


def calis(args, env=None):
    r = subprocess.run(args, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    if r.returncode:
        raise SystemExit(f'HATA {args[:3]}: {r.stderr[-800:]}')
    return r.stdout


def olc(F, FT, SM):
    fs = F[-1].astype(np.int16)
    d9 = np.abs(F[9].astype(np.int16) - fs).max(-1)
    gec = SM & (d9 >= 20)
    bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    V, D = [], []
    for i in range(len(F)):
        dt = np.abs(F[i].astype(np.int16) - fs).max(-1)
        V.append(float(np.clip(1 - dt[gec] / d9[gec], 0, 1).mean()))
        tz = np.abs(F[i].astype(np.int16) - FT[i].astype(np.int16)).max(-1) > 8
        D.append(float((tz & bol).sum() / SM.sum()))
    return np.array(V), np.array(D)


def tol(Vk, Dk, Vp, Dp):
    dm = Dk.max(); sat = {}
    for t in TS:
        i = min(len(Vk) - 1, int(round(t * FPS)))
        dv = abs(Vp[i] - Vk[i])
        dd_ok = abs(Dp[i] - Dk[i]) <= (0.10 * Dk[i] if Dk[i] >= 0.2 * dm else 0.02 * dm)
        sat[f'{t:g}'] = {'kare': i, 'kupa_gorunen': round(Vk[i], 3), 'poster_gorunen': round(Vp[i], 3),
                         'kupa_toz_yogunlugu': round(Dk[i], 3), 'poster_toz_yogunlugu': round(Dp[i], 3),
                         'gorunen_ok': dv <= 0.05, 'toz_ok': bool(dd_ok)}
    return sat, all(v['gorunen_ok'] and v['toz_ok'] for v in sat.values())


R = {}
# ---------- A) kupa V6
src = open(V6B).read()
assert src.count('N = 5200 ') == 1 and src.count('(0, 0), 0.9)') == 2, 'video6b beklenen satirlar yok'
v6k = src.replace('N = 5200 ', 'N = 10400', 1).replace('GaussianBlur(al, (0, 0), 0.9)', 'GaussianBlur(al, (0, 0), 0.45)') \
    .replace('GaussianBlur(kat, (0, 0), 0.9)', 'GaussianBlur(kat, (0, 0), 0.45)')
tzk = src.replace('a3 = np.clip(al, 0, 0.9)[..., None]', 'a3 = np.clip(al, 0, 0.9)[..., None] * 0', 1)
open(os.path.join(IS, 'video6b_v6.py'), 'w').write(v6k); open(os.path.join(IS, 'video6b_tozsuz.py'), 'w').write(tzk)
R['kupa_kod_farki'] = [l for l in v6k.splitlines() if l not in src.splitlines()]
K6 = os.path.join(OUT, 'KUPA_CANCER_LIBRA_v6.mp4'); KT = os.path.join(IS, 'kupa_tozsuz.mp4')
calis([PY, '-I', os.path.join(IS, 'video6b_v6.py'), VD.rstrip('/') + '/', KK, K6])
calis([PY, '-I', os.path.join(IS, 'video6b_tozsuz.py'), VD.rstrip('/') + '/', KK, KT])
for f in os.listdir(OUT):                                    # video6b'nin yan kare jpg'leri
    if f.startswith('KUPA_CANCER_LIBRA_v6_') and f.endswith('.jpg'):
        os.remove(os.path.join(OUT, f))
FK, pk = Q.kareler(K6); FKT, _ = Q.kareler(KT)
oku = lambda p_: cv2.resize(np.asarray(Image.open(p_).convert('RGB')).astype(np.float32), (FK.shape[2], FK.shape[1]), interpolation=cv2.INTER_AREA)
mk = np.clip((1 - oku(os.path.join(VD, 'k_mask_nosym.png')).mean(-1) / np.maximum(oku(os.path.join(VD, 'k_beyaz.png')).mean(-1), 1)) * 1.4, 0, 1)
SMK = mk > 0.95
Vk, Dk = olc(FK, FKT, SMK)
R['kupa_v6'] = {'video': pk, 'N': 10400, 'tane_sigma': 0.45, 'sembol_piksel': int(SMK.sum())}

# ---------- B) poster V6 kalibrasyonu


def poster(N, c, ad):
    cj = os.path.join(IS, f'{ad}_c.json'); json.dump([float(x) for x in c], open(cj, 'w'))
    mp, mt = os.path.join(IS, f'{ad}.mp4'), os.path.join(IS, f'{ad}_tozsuz.mp4')
    for m_, ek in ((mp, {}), (mt, {'TOZSUZ': '1'})):
        calis([PY, '-I', os.path.join(HERE, 'poster_video_v6.py'), KAPAK, m_, 'murekkep'], dict(V6_N=str(N), V6_C=cj, **ek))
    F, p = Q.kareler(mp); FT, _ = Q.kareler(mt)
    SM = np.asarray(Image.open(mp + '.sembol_maske.png')) > 127
    V, D = olc(F, FT, SM)
    return mp, V, D, int(SM.sum()), p


ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))
c = np.array([ease((k / (NB - 1) - 0.36) / 0.64) for k in range(NB)])   # baslangic: kupanin murekkep egrisi
N0 = 26000
_, V0, D0, smp, _ = poster(N0, c, 'p0')
sec = Dk[:NB] >= 0.2 * Dk.max()
oran = float(np.median(Dk[:NB][sec] / np.maximum(D0[:NB][sec], 1e-6)))
N = int(round(N0 * oran / 100.0) * 100)
R['parcacik_hesabi'] = {'N0': N0, 'kupa_sembol_px': int(SMK.sum()), 'poster_sembol_px': smp, 'alan_orani': round(smp / SMK.sum(), 2),
                        'yogunluk_orani_kupa_poster_N0': round(oran, 3), 'N': N, 'kupa_N': 10400}
tur = []
for k in range(3):
    mp, Vp, Dp, _, pp = poster(N, c, f'p{k + 1}')
    sat, ok = tol(Vk, Dk, Vp, Dp)
    tur.append({'tur': k + 1, 'ok': ok, 'en_buyuk_V_fark': round(float(np.abs(Vp[:NB] - Vk[:NB]).max()), 3)})
    print('TUR', k + 1, ok, tur[-1]['en_buyuk_V_fark'], flush=True)
    if ok:
        break
    c = np.clip(c + (Vk[:NB] - Vp[:NB]), 0, 1); c = np.maximum.accumulate(c); c[-1] = 1.0
    c = np.maximum.accumulate(np.convolve(np.pad(c, 2, mode='edge'), np.ones(5) / 5, mode='valid')); c[-1] = 1.0
R['kalibrasyon_turlari'] = tur
P6 = os.path.join(OUT, 'CANCER_LIBRA_ilan_video_v6.mp4')
os.replace(mp, P6); ic = json.load(open(mp + '.ic.json')); SMP = np.asarray(Image.open(mp + '.sembol_maske.png')) > 127
FP, pp = Q.kareler(P6)
R['tablo_0_5sn'] = sat
R['poster_v6'] = {'video': pp, 'N': N, 'tane_sigma': 0.45, 'ihlal_en_buyuk': round(max(ic['ihlal']), 4),
                  'c_egri_0_5sn': {f'{t:g}': round(ic['c_egri'][min(NB - 1, int(round(t * FPS)))], 3) for t in TS}}
kap = cv2.resize(np.asarray(Image.open(KAPAK).convert('RGB')), (FP.shape[2], FP.shape[1]), interpolation=cv2.INTER_AREA)
tb = os.path.join(IS, '_t.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{kap.shape[1]}x{kap.shape[0]}', '-r', '30',
                '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=kap.tobytes(), check=True)
R['poster_v6'].update(taban_420=Q.fk(Q.kareler(tb)[0][0], kap), ilk_kare_fark=Q.fk(FP[0], kap), son_kare_fark=Q.fk(FP[-1], kap))
pv = R['poster_v6']
R['kapi'] = {'kupa_10400_045': R['kupa_kod_farki'] and pk['kare'] == 180 and pk['olcu'] == '1080x1080',
             'poster_180_kare_1440x1080': pp['kare'] == 180 and pp['olcu'] == '1440x1080' and not pp['ses_akisi'],
             'ilk_kare_kapak': pv['ilk_kare_fark'] <= pv['taban_420'] + 0.2, 'son_kare_kapak': pv['son_kare_fark'] <= pv['taban_420'] + 0.2,
             'murekkep_tozun_onunde_degil': pv['ihlal_en_buyuk'] <= 0, 'gorunen_ve_toz_kupa_ile_ayni': ok}
R['sonuc'] = 'PASS' if all(bool(v) for v in R['kapi'].values()) else 'FAIL'
json.dump(R, open(os.path.join(OUT, 'QC.json'), 'w'), indent=1, default=str)
# ---------- kontaklar ve yakin karsilastirma
Q.kontak([('KUPA V6', FK)], os.path.join(OUT, 'KUPA_v6_KONTAK.jpg'))
Q.kontak([('POSTER V6', FP)], os.path.join(OUT, 'POSTER_v6_KONTAK.jpg'))
yk = [2, 2.5, 3, 3.5, 4, 4.5, 5]; th = 300
kk, kp = Q.kutu(SMK, 30), Q.kutu(SMP, 30)
kirp = lambda F_, b, t: Image.fromarray(F_[int(round(t * FPS))][b[0]:b[1], b[2]:b[3]])
ws = [round((b[3] - b[2]) * th / (b[1] - b[0])) for b in (kk, kp)]
tw = max(ws); K = Image.new('RGB', (130 + len(yk) * (tw + 6), 32 + 2 * (th + 8)), (245, 245, 245)); dr = ImageDraw.Draw(K)
for j, t in enumerate(yk):
    dr.text((130 + j * (tw + 6) + 4, 4), f'{t:g} sn', fill=(0, 0, 0), font=Q.font(20))
for r_, (ad, F_, b, w_) in enumerate((('KUPA V6', FK, kk, ws[0]), ('POSTER V6', FP, kp, ws[1]))):
    y = 32 + r_ * (th + 8); dr.text((6, y + th // 2 - 10), ad, fill=(0, 0, 0), font=Q.font(20))
    for j, t in enumerate(yk):
        K.paste(kirp(F_, b, t).resize((w_, th), Image.LANCZOS), (130 + j * (tw + 6) + (tw - w_) // 2, y))
K.save(os.path.join(OUT, 'KARSILASTIRMA_YAKIN.jpg'), quality=93)
print(json.dumps({k: R[k] for k in ('parcacik_hesabi', 'kalibrasyon_turlari', 'kapi', 'sonuc')}, default=str))
for t, v in sat.items():
    print('TABLO', t, v)
print('SONUC', R['sonuc'])
sys.exit(0 if R['sonuc'] == 'PASS' else 1)
