#!/usr/bin/env python3
"""Yil donumu (Y1) ilan videosu ornegi: uretim + QC, tek script, PASS/FAIL (20 Eki 2026, Serdar).
Uretim: yildonumu_video.py (V6 motoru), N = 58000 x bolge / CL poster bolgesi; alan basina toz yogunlugu 2,0-4,0 sn kupa V6
referansiyla +-%10: tutmazsa tur 2 = N x olculen oran (78 poster kurali), yine tutmazsa tur 3 = olculen us (D ~ N^a) ile
bandi ortalayan N (en fazla 3 uretim). Olcumler ilan78.py ile ayni formul.
Kapilar: 1080x1080, 180 kare, ses yok; ilk/son kare = kapak (kayipsiz 4:2:0 tabani + 0,2); murekkep tozun onunde degil;
sembol 5,0 sn'de tam (gorunen >= 0,98); toz 2,0-4,0 sn +-%10; sembol pikselleri kapaktan (4,97 sn karesi sembol bolgesinde
kapakla son kare kadar ayni, + 0,2; ikisi de crf 17); silme izi yok (bos halde silinen bolge, cevre kagitla: ortalama parlaklik farki <= 1,5,
ince doku std orani 0,7-1,3, 8'den buyuk sapma orani <= cevre + %1); glifler degismedi (bos halde glif fark <= 0,5).
Kullanim: yildonumu_qc.py <y1_kapak.jpg> <CIFT> <cikti_dir> <is_dir>"""
import importlib.util, json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('q5', os.path.join(HERE, 'v5_qc.py')); Q = importlib.util.module_from_spec(sp); sp.loader.exec_module(Q)
KAPAK, CIFT, OUT, IS = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True); os.makedirs(IS, exist_ok=True)
REF = json.load(open(os.path.join(HERE, 'v6_kupa_ref.json')))
PY = sys.executable
V = os.path.join(OUT, f'{CIFT}_yd_video.mp4'); VT = os.path.join(IS, f'{CIFT}_tozsuz.mp4')
ENV0 = {'V6_C': os.path.join(HERE, 'v6_c_egri.json')}
TS4 = (2.0, 2.5, 3.0, 3.5, 4.0)


def calis(args, env):
    r = subprocess.run(args, capture_output=True, text=True, env=dict(os.environ, **env))
    if r.returncode:
        raise SystemExit(f'HATA {args[:3]}: {r.stderr[-800:]}')
    return r.stdout


def toz(F, FT, SM):   # ilan78.py ile ayni
    bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    D = np.array([float(((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(-1) > 20) & bol).sum() / bol.sum()) for a, b in zip(F, FT)])
    return np.clip(D - D[160:].mean(), 0, None)


def gorunen(F, SM):   # ilan78.py ile ayni
    fs = F[-1].astype(np.int16); d9 = np.abs(F[9].astype(np.int16) - fs).max(-1); g = SM & (d9 >= 20)
    return np.array([float(np.clip(1 - np.abs(f.astype(np.int16) - fs).max(-1)[g] / d9[g], 0, 1).mean()) for f in F])


def tur(env):
    out = calis([PY, '-I', os.path.join(HERE, 'yildonumu_video.py'), KAPAK, V], dict(ENV0, **env))
    calis([PY, '-I', os.path.join(HERE, 'yildonumu_video.py'), KAPAK, VT], dict(ENV0, **env, TOZSUZ='1'))
    ic = json.load(open(V + '.ic.json')); SM = np.asarray(Image.open(V + '.sembol_maske.png')) > 127
    F, _ = Q.kareler(V); FT, _ = Q.kareler(VT)
    D = toz(F, FT, SM); del FT
    tb = {f'{t:g}': {'video': round(D[Q.ix(F, t)], 3), 'kupa_ref': REF['kupa_toz_alan_basina'][f'{t:g}'],
                     'fark_yuzde': round(100 * (D[Q.ix(F, t)] / REF['kupa_toz_alan_basina'][f'{t:g}'] - 1), 1)} for t in TS4}
    return ic, SM, F, tb, out


tutar = lambda tb: all(abs(v['fark_yuzde']) <= 10 for v in tb.values())
ic, SM, F, tab, log = tur({'V6_N': str(REF['poster_N']), 'V6_BOLGE_REF': str(REF['poster_bolge_px']), 'V6_N_REF': str(REF['poster_N'])})
turlar = [{'N': ic['N'], 'kaynak': 'N = 58000 x bolge / CL poster bolgesi', 'toz_2_4sn': tab, 'tutar': tutar(tab)}]
if not tutar(tab):   # tur 2: N x olculen oran (78 poster kurali)
    oran = float(np.median([v['kupa_ref'] / max(v['video'], 1e-6) for v in tab.values()]))
    del F
    ic, SM, F, tab, log = tur({'V6_N': str(int(round(ic['N'] * oran / 100.0) * 100))})
    turlar.append({'N': ic['N'], 'kaynak': f'N1 x {oran:.3f} (olculen oran)', 'toz_2_4sn': tab, 'tutar': tutar(tab)})
if not tutar(tab):   # tur 3: olculen us (D ~ N^a, tur 1-2) ile bandi ortala: hedef oran = sqrt(en kucuk x en buyuk kupa/video)
    t1, t2 = turlar[0], turlar[1]
    a_ = float(np.median([np.log(t2['toz_2_4sn'][k]['video'] / t1['toz_2_4sn'][k]['video']) for k in tab]) / np.log(t2['N'] / t1['N']))
    rs = [v['kupa_ref'] / max(v['video'], 1e-6) for v in tab.values()]
    hed = float(np.sqrt(min(rs) * max(rs)))
    N3 = int(round(ic['N'] * hed ** (1 / max(a_, 0.2)) / 100.0) * 100)
    del F
    ic, SM, F, tab, log = tur({'V6_N': str(N3)})
    turlar.append({'N': ic['N'], 'kaynak': f'N2 x {hed:.3f}^(1/{a_:.2f}) (olculen us, bant ortalama)', 'toz_2_4sn': tab, 'tutar': tutar(tab)})
os.remove(VT)
p = Q.probe(V); Vv = gorunen(F, SM)
h, w = F.shape[1:3]
kap = np.clip(np.round(cv2.resize(np.asarray(Image.open(KAPAK).convert('RGB')).astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
tb_ = os.path.join(IS, '_t.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', '30', '-i', '-',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb_], input=kap.tobytes(), check=True)
T0 = Q.kareler(tb_)[0][0]
bol = cv2.dilate(SM.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
fk_b = lambda a: round(float(np.abs(a.astype(np.float32) - kap.astype(np.float32))[bol].mean()), 3)
# silme izi: bos hal (BASE) silinen bolgede, cevre kagitla
B = np.asarray(Image.open(V + '.bos.png')).astype(np.float32); Wsil = np.asarray(Image.open(V + '.silme.png')).astype(np.float32) / 255
lb = B @ np.float32([0.299, 0.587, 0.114]); lk = kap.astype(np.float32) @ np.float32([0.299, 0.587, 0.114])
E = Wsil > 0.5
kagit_k = cv2.medianBlur(kap, 31).astype(np.float32) @ np.float32([0.299, 0.587, 0.114])
ozellik = cv2.dilate(((kagit_k - lk) > 12).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0   # kapakta murekkep/yazi/glif
halka = (cv2.dilate(E.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0) & ~(Wsil > 0.02) & ~ozellik
hf = lambda l: l - cv2.GaussianBlur(l, (0, 0), 2.0)
bgB = cv2.medianBlur(np.clip(B, 0, 255).astype(np.uint8), 31).astype(np.float32) @ np.float32([0.299, 0.587, 0.114])
iz = {'silinen_px': int(E.sum()), 'cevre_px': int(halka.sum()),
      'parlaklik_farki': round(float(lb[E].mean() - lk[halka].mean()), 3),
      'doku_std_orani': round(float(hf(lb)[E].std() / hf(lk)[halka].std()), 3),
      'sapma8_orani_silinen': round(float((np.abs(lb - bgB)[E] > 8).mean()), 4),
      'sapma8_orani_cevre': round(float((np.abs(lk - kagit_k)[halka] > 8).mean()), 4)}
GL = np.zeros((h, w), bool)
for x, y, gw, gh in (ic['glif']['sign_a'], ic['glif']['sign_b']):
    s_ = w / ic['glif']['poster_w']; GL[int(y * s_):int((y + gh) * s_) + 1, int(x * s_):int((x + gw) * s_) + 1] = True
iz['glif_bos_hal_farki'] = round(float(np.abs(B - kap.astype(np.float32))[GL].mean()), 3)
R = {'cift': CIFT, 'kapak': os.path.basename(KAPAK), 'video': os.path.basename(V), 'probe': p,
     'silinip_yeniden_olusan': ['buyuk birlesik sembol'],
     'sabit_kalan': ['1st Anniversary Gift', 'A & B satiri', 'YEAR ONE', 'iki kucuk glif (toz kaynagi)', 'isimler', 'Paper Anniversary', 'tarih'],
     'mesaj_satiri': 'yok (Y1 tasariminda mesaj satiri yok; yazim adimi bos)', 'toz_kaynagi': 'iki kucuk glif (aralarinda isaret yok)',
     'toz_rengi': {'ana_%78_sembol_murekkebi': ic['glif']['murekkep_rengi'], 'acik_vurgu_%22': 'murekkep x 0,55 + kagit isigi (255,236,214) x 0,45'},
     'N_turlari': turlar, 'N': ic['N'], 'bolge_px': ic['bolge_px'], 'glif': ic['glif'], 'toz_2_4sn': tab,
     'ihlal_en_buyuk': round(max(ic['ihlal']), 4), 'gorunen_5sn': round(Vv[150], 3),
     'gorunen_0_5sn': {f'{t / 2:g}': round(Vv[Q.ix(F, t / 2)], 3) for t in range(13)},
     'taban_420': Q.fk(T0, kap), 'ilk_kare_fark': Q.fk(F[0], kap), 'son_kare_fark': Q.fk(F[-1], kap),
     'sembol_bolgesi_4_97sn_fark': fk_b(F[149]), 'sembol_bolgesi_son_kare_fark': fk_b(F[-1]), 'sembol_bolgesi_taban_420': fk_b(T0),
     'silme_izi': iz}
R['kapi'] = {k: bool(v) for k, v in {
    'olcu_6sn_sessiz': p['olcu'] == '1080x1080' and p['kare'] == 180 and not p['ses_akisi'],
    'ilk_kare_kapak': R['ilk_kare_fark'] <= R['taban_420'] + 0.2, 'son_kare_kapak': R['son_kare_fark'] <= R['taban_420'] + 0.2,
    'murekkep_tozun_onunde_degil': R['ihlal_en_buyuk'] <= 0, 'sembol_5sn_tam': R['gorunen_5sn'] >= 0.98,
    'toz_2_4sn_10yuzde': tutar(tab), 'sembol_pikselleri_kapaktan': R['sembol_bolgesi_4_97sn_fark'] <= R['sembol_bolgesi_son_kare_fark'] + 0.2,
    'silme_izi_yok': abs(iz['parlaklik_farki']) <= 1.5 and 0.7 <= iz['doku_std_orani'] <= 1.3
                     and iz['sapma8_orani_silinen'] <= iz['sapma8_orani_cevre'] + 0.01,
    'glifler_degismedi': iz['glif_bos_hal_farki'] <= 0.5}.items()}
R['sonuc'] = 'PASS' if all(R['kapi'].values()) else 'FAIL'
json.dump(R, open(os.path.join(OUT, 'QC.json'), 'w'), indent=1, default=str)
# kontak 0-6 sn her 0,5 sn; 3 sn sembol bolgesi %200
Q.kontak([('Y1 VIDEO', F)], os.path.join(OUT, f'{CIFT}_yd_KONTAK.jpg'))
y0, y1, x0, x1 = Q.kutu(SM, 40)
Image.fromarray(F[Q.ix(F, 3.0)][y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS).save(
    os.path.join(OUT, f'{CIFT}_yd_3sn_yakin_200.jpg'), quality=93)
for e in ('.ic.json', '.sembol_maske.png', '.bos.png', '.silme.png'):
    os.replace(V + e, os.path.join(IS, os.path.basename(V) + e))
print(json.dumps({k: R[k] for k in ('N_turlari', 'kapi', 'silme_izi', 'ilk_kare_fark', 'son_kare_fark', 'taban_420', 'gorunen_5sn', 'sonuc')}, default=str))
print('SONUC', R['sonuc'])
sys.exit(0 if R['sonuc'] == 'PASS' else 1)
