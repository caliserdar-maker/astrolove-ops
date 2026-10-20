#!/usr/bin/env python3
"""78 ilan videosu (20 Eki 2026, Serdar V6 onayi): bir cift icin kupa + poster videosu ve kontrolu. Kural V6 (ae01cd4) birebir.
Kupa: kupa-orchard video6b.py, yalniz N 5200 -> 10400 ve sigma 0.9 -> 0.45 (v6_kalibre ile ayni degisiklik); katmanlar
      cift.py ciktisi (video/), sahne = ilanin yeni kupa kapagi (KUPA_KAPAK_78 KAPAK/).
Poster: poster_video_v6.py (altin toz, sigma 0.45, murekkep egrisi v6_c_egri.json), N = 58000 x bolge alani / CL bolge alani.
Kontrol (satir/<CIFT>.json): kare sayisi/olcu/ses; ilk ve son kare = kapak (kayipsiz 4:2:0 tabani + 0,2; kupada ilk kare
  icin CL'de olculen crf 17 duzeyi kabul: max(1,765, taban + 0,245)); sembol 5,0 sn'de tam (gorunen oran >= 0,98);
  poster: murekkep tozun onunde degil (ihlal <= 0), alan basina toz yogunlugu 2,0-4,0 sn kupa V6 referansi +-%10,
  glif + sonsuz yerlesimi (ayni burcta iki glif benzerligi >= 0,8); kupa: kupa bolgesinde kapak - katman kapagi fark <= 3.
Kullanim: ilan78.py <CIFT> <kupa_kapak.jpg> <cift.py cikti dizini> <video6b.py> <poster_kapak.jpg> <poster_klasoru> <cikti> <is>"""
import importlib.util, json, os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('q5', os.path.join(HERE, 'v5_qc.py')); Q = importlib.util.module_from_spec(sp); sp.loader.exec_module(Q)
CIFT, KK, KO, V6B, PK, PKL, OUT, IS = sys.argv[1:9]
REF = json.load(open(os.path.join(HERE, 'v6_kupa_ref.json')))
PY = sys.executable
for d in ('KUPA', 'POSTER', 'satir', 'kare'):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)
os.makedirs(IS, exist_ok=True)
t0 = time.time()


def calis(args, env=None):
    r = subprocess.run(args, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    if r.returncode:
        raise SystemExit(f'HATA {CIFT} {args[:3]}: {r.stderr[-800:]}')
    return r.stdout


def gorunen(F, SM):
    """v6_kalibre olcumu: V(t) = ort clip(1 - d_t / d_9) (d_9 >= 20 olan cekirdek sembol pikselleri)"""
    fs = F[-1].astype(np.int16); d9 = np.abs(F[9].astype(np.int16) - fs).max(-1); g = SM & (d9 >= 20)
    return np.array([float(np.clip(1 - np.abs(f.astype(np.int16) - fs).max(-1)[g] / d9[g], 0, 1).mean()) for f in F])


def toz(F, FT, SM):
    """v6_kalibre olcumu: alan basina toz yogunlugu (bolge = SM 15x15 genisletilmis, fark > 20, kodlama tabani 5,3-6 sn)"""
    bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    D = np.array([float(((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(-1) > 20) & bol).sum() / bol.sum()) for a, b in zip(F, FT)])
    return np.clip(D - D[160:].mean(), 0, None)


def kapak(F, yol):
    h, w = F.shape[1:3]
    kap = np.clip(np.round(cv2.resize(np.asarray(Image.open(yol).convert('RGB')).astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
    tb = os.path.join(IS, f'_{CIFT}_t.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', '30', '-i', '-',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=kap.tobytes(), check=True)
    r = {'taban_420': Q.fk(Q.kareler(tb)[0][0], kap), 'ilk_kare_fark': Q.fk(F[0], kap), 'son_kare_fark': Q.fk(F[-1], kap)}
    os.remove(tb)
    return r


def kucuk(F, ad):
    for t, ek in ((3.0, '3sn'), (None, 'son')):
        f = F[Q.ix(F, t)] if t is not None else F[-1]
        Image.fromarray(f).resize((round(360 * f.shape[1] / f.shape[0]), 360), Image.LANCZOS).save(
            os.path.join(OUT, 'kare', f'{CIFT}_{ad}_{ek}.jpg'), quality=88)


R = {'cift': CIFT}
# ---------- KUPA
src = open(V6B).read()
assert src.count('N = 5200 ') == 1 and src.count('(0, 0), 0.9)') == 2, 'video6b beklenen satirlar yok'
v6k = src.replace('N = 5200 ', 'N = 10400', 1).replace('GaussianBlur(al, (0, 0), 0.9)', 'GaussianBlur(al, (0, 0), 0.45)') \
    .replace('GaussianBlur(kat, (0, 0), 0.9)', 'GaussianBlur(kat, (0, 0), 0.45)')
k6 = os.path.join(IS, 'video6b_v6.py'); open(k6, 'w').write(v6k)
VD = os.path.join(KO, 'video') + '/'
KV = os.path.join(OUT, 'KUPA', os.path.splitext(os.path.basename(KK))[0] + '.mp4')
calis([PY, '-I', k6, VD, KK, KV])
for f in os.listdir(os.path.dirname(KV)):                 # video6b'nin yan kare jpg'leri
    if f.startswith(os.path.splitext(os.path.basename(KV))[0] + '_') and f.endswith('.jpg'):
        os.remove(os.path.join(os.path.dirname(KV), f))
F, pk = Q.kareler(KV)
oku = lambda p_: cv2.resize(np.asarray(Image.open(p_).convert('RGB')).astype(np.float32), (F.shape[2], F.shape[1]), interpolation=cv2.INTER_AREA)
mk = np.clip((1 - oku(VD + 'k_mask_nosym.png').mean(-1) / np.maximum(oku(VD + 'k_beyaz.png').mean(-1), 1)) * 1.4, 0, 1)
SMK = mk > 0.95
V = gorunen(F, SMK)
kv = {'video': os.path.basename(KV), 'kapak': os.path.basename(KK), 'probe': pk, 'sembol_px': int(SMK.sum()),
      'gorunen_5sn': round(V[150], 3), **kapak(F, KK)}
bol_ = cv2.dilate(SMK.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
kv['kapak_katman_kupa_bolgesi_fark'] = round(float(np.abs(oku(KK) - oku(os.path.join(KO, 'galeri', '01_Orange_Blossom_kapak.jpg')))[bol_].mean()), 3)
kv['ilk_kare_kabul_esigi'] = round(max(1.765, kv['taban_420'] + 0.245), 3)
kv['kapi'] = {'olcu_6sn_sessiz': pk['olcu'] == '1080x1080' and pk['kare'] == 180 and not pk['ses_akisi'],
              'ilk_kare_kapak': kv['ilk_kare_fark'] <= kv['ilk_kare_kabul_esigi'],
              'son_kare_kapak': kv['son_kare_fark'] <= kv['taban_420'] + 0.2,
              'sembol_5sn_tam': kv['gorunen_5sn'] >= 0.98, 'kapak_katman_ayni': kv['kapak_katman_kupa_bolgesi_fark'] <= 3.0}
kv['ilk_kare_taban_02_icinde'] = kv['ilk_kare_fark'] <= kv['taban_420'] + 0.2
kucuk(F, 'kupa'); del F
R['kupa'] = kv
# ---------- POSTER
PV = os.path.join(OUT, 'POSTER', os.path.splitext(os.path.basename(PK))[0] + '.mp4'); PT = os.path.join(IS, f'{CIFT}_tozsuz.mp4')
env = {'V6_N': str(REF['poster_N']), 'V6_BOLGE_REF': str(REF['poster_bolge_px']), 'V6_N_REF': str(REF['poster_N']),
       'V6_C': os.path.join(HERE, 'v6_c_egri.json')}
calis([PY, '-I', os.path.join(HERE, 'poster_video_v6.py'), PK, PV, 'murekkep'], env)
calis([PY, '-I', os.path.join(HERE, 'poster_video_v6.py'), PK, PT, 'murekkep'], dict(env, TOZSUZ='1'))
ic = json.load(open(PV + '.ic.json')); SMP = np.asarray(Image.open(PV + '.sembol_maske.png')) > 127
for e in ('.ic.json', '.sembol_maske.png'):
    os.replace(PV + e, os.path.join(IS, os.path.basename(PV) + e))
F, pp = Q.kareler(PV); FT, _ = Q.kareler(PT)
D = toz(F, FT, SMP); del FT; os.remove(PT)
for e in ('.ic.json', '.sembol_maske.png'):
    if os.path.exists(PT + e):
        os.remove(PT + e)
V = gorunen(F, SMP)
tab = {}
for t in (2.0, 2.5, 3.0, 3.5, 4.0):
    i = Q.ix(F, t); ref = REF['kupa_toz_alan_basina'][f'{t:g}']
    tab[f'{t:g}'] = {'poster': round(D[i], 3), 'kupa_ref': ref, 'fark_yuzde': round(100 * (D[i] / ref - 1), 1)}
g = ic['glif']; W = g['poster_w']
ax, bx = g['sign_a'][0] + g['sign_a'][2] / 2, g['sign_b'][0] + g['sign_b'][2] / 2
ss = [c[0] + c[2] / 2 for c in g['sonsuz']]
ayni = CIFT.split('_')[0] == CIFT.split('_')[1]
glif_ok = (min(g['sign_a'][2:] + g['sign_b'][2:]) > 10 and ax < W / 2 < bx and g['sign_a'][0] + g['sign_a'][2] <= g['sign_b'][0]
           and abs(g['sign_a'][1] + g['sign_a'][3] / 2 - g['sign_b'][1] - g['sign_b'][3] / 2) < 0.5 * max(g['sign_a'][3], g['sign_b'][3])
           and len(ss) >= 1 and all(ax < x < bx for x in ss) and (not ayni or g['benzerlik'] >= 0.8))
pv = {'video': os.path.basename(PV), 'kapak': os.path.basename(PK), 'kapak_klasoru': PKL, 'probe': pp, 'N': ic['N'],
      'bolge_px': ic['bolge_px'], 'sembol_px': int(SMP.sum()), 'ihlal_en_buyuk': round(max(ic['ihlal']), 4),
      'gorunen_5sn': round(V[150], 3), 'toz_2_4sn': tab, 'glif': g, 'ayni_burc': ayni, **kapak(F, PK)}
pv['kapi'] = {'olcu_6sn_sessiz': pp['olcu'] == '1440x1080' and pp['kare'] == 180 and not pp['ses_akisi'],
              'ilk_kare_kapak': pv['ilk_kare_fark'] <= pv['taban_420'] + 0.2, 'son_kare_kapak': pv['son_kare_fark'] <= pv['taban_420'] + 0.2,
              'sembol_5sn_tam': pv['gorunen_5sn'] >= 0.98, 'murekkep_tozun_onunde_degil': pv['ihlal_en_buyuk'] <= 0,
              'toz_2_4sn_10yuzde': all(abs(v['fark_yuzde']) <= 10 for v in tab.values()), 'glif_sonsuz': bool(glif_ok)}
kucuk(F, 'poster'); del F
R['poster'] = pv
R['sonuc'] = 'PASS' if all(kv['kapi'].values()) and all(pv['kapi'].values()) else 'FAIL'
R['sure_sn'] = round(time.time() - t0)
json.dump(R, open(os.path.join(OUT, 'satir', f'{CIFT}.json'), 'w'), indent=1, default=str)
dus = [f'kupa.{k}' for k, v in kv['kapi'].items() if not v] + [f'poster.{k}' for k, v in pv['kapi'].items() if not v]
print(f"{CIFT} {R['sonuc']} N {pv['N']} toz% {[v['fark_yuzde'] for v in tab.values()]} kupa ilk {kv['ilk_kare_fark']} "
      f"glif {g['benzerlik']} {R['sure_sn']}s {' '.join(dus)}", flush=True)
