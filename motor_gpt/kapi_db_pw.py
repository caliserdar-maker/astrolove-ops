# DB / PW yeni altin kapilari (9 Eki 2026, db-pw-altin ORNEK). PASS/FAIL, olculebilir esik.
# Kullanim: python kapi_db_pw.py IS_KLASORU [--json CIKTI]   (IS: db_pw_uret.py ciktisi)
#  b/c/d/e/g/h/i : onayli siparis_kapi.py AYNEN, renk x olcu (24x36, 16x20) basina (a: MB standart poster karsilastirmasi, DB/PW'de uygulanmaz)
#    b) ogeler arasi dE00 (ana ile) <= 1 (tek doku)  d) yazim IoU >= 0.985  g) halka sigma 8 <= 0.10, < 20 MB, 4:4:4, 300 dpi  i) B dikisi
#  L) leke: oge ici L* (renk - MB ayni kosu) ortalama kaydirma cikarilinca |r| > 6 kume <= 0.5*kalinlik^2 (leke_kontrol.py AYNEN):
#     ogeler MB'deki onayli dokuyla ayni mi
#  K) kesik uc: her oge alfasinda kutu kenarina tam genislikte degen parca yok (kesik_uc.py AYNEN)
#  N) not (FAIL degil, Serdar'a sorulacak): zemin uzerinde golge (koyulasma) ve isima (acilma) olcusu, altin/zemin kontrasti (okunurluk)
import sys, os, json, subprocess, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = os.environ.get('MOTOR_KOK', '/home/claude/blender') + '/'; PY = os.environ.get('MOTOR_PY', B + 'venv/bin/python')
IS = sys.argv[1]; JS = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
s = json.load(open(f'{IS}/siparis.json')); c = s['cift']; b1, b2 = c.split('_'); a1, a2 = b1.capitalize(), b2.capitalize()
sys.path.insert(0, B); import kesik_uc
z = np.load(f'{IS}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
sonuc = {}
OLS = [o for o in os.environ.get('KAPI_OLCULER', '24x36,16x20').split(',') if o]   # d3: yalniz 16x20
def lab(x): return cv2.cvtColor((x / 255).astype(np.float32), cv2.COLOR_RGB2Lab)
mb = f'{IS}/MIDNIGHT_BLUE/AstroLoveArt_{a1}_{a2}_Midnight_Blue.jpg'
for r in [k for k in s['renk'] if k != 'MIDNIGHT_BLUE']:
    rn = '_'.join(w.capitalize() for w in r.split('_')); TB = f'{IS}/{r}'; ana = f'{TB}/AstroLoveArt_{a1}_{a2}_{rn}.jpg'
    R = sonuc[r] = {}
    for ol in OLS:                                                      # onayli kapi betigi, beklenen dosya duzeniyle
        D = f'{TB}/kapi_{ol}'; os.makedirs(D, exist_ok=True)
        for src, dst in ((ana, f'AstroLoveArt_{a1}_{a2}.jpg'), (f'{TB}/AstroLoveArt_{a1}_{a2}_{rn}_{ol}.jpg', f'AstroLoveArt_{a1}_{a2}_{ol}.jpg'),
                         (f'{IS}/{c}_alfa.npz', f'{c}_alfa.npz')):
            if os.path.lexists(f'{D}/{dst}'): os.remove(f'{D}/{dst}')
            os.symlink(os.path.abspath(src), f'{D}/{dst}')
        ro = dict(s['renk'][r]); ro['teslim'] = ro['teslim'] if ol == '24x36' else ro['olcu_16x20']
        json.dump(dict(cift=c, isim1=s['isim1'], isim2=s['isim2'], tagline=s['tagline'], olcu=ol, renk=ro), open(f'{D}/siparis.json', 'w'), ensure_ascii=False)
        p = subprocess.run([PY, B + 'siparis_kapi.py', D, '-', '--json', f'{D}/KAPI.json'], capture_output=True, text=True)
        if not os.path.exists(f'{D}/KAPI.json'): print(p.stdout[-500:], p.stderr[-1500:]); R[ol] = dict(PASS=False, hata='siparis_kapi calismadi'); continue
        R[ol] = json.load(open(f'{D}/KAPI.json'))
    # L) leke: MB ayni kosu (onayli doku) -> bu renk
    p = subprocess.run([PY, B + 'leke_kontrol.py', mb, ana, f'{IS}/{c}_alfa.npz', '--json', f'{TB}/LEKE.json'], capture_output=True, text=True)
    R['L'] = json.load(open(f'{TB}/LEKE.json')) if os.path.exists(f'{TB}/LEKE.json') else dict(PASS=False, hata=p.stderr[-300:])
    # K) kesik uc (oge alfalari)
    kk = {ad: kesik_uc.kesikler(z[ad]) for ad in K}
    R['K'] = dict(kesik={ad: v for ad, v in kk.items() if v}, PASS=not any(kk.values()))
    # N) not: golge / isima / kontrast (zemin = plakanin bg degeri; yildizlar haric: |plaka - bg| > 0 olan pikseller disarida)
    P = np.asarray(Image.open(ana).convert('RGB')).astype(np.float32); bg = s['plaka'][f"{'BLACK' if r == 'DEEP_BLACK' else 'PURE_WHITE'}_24x36"]['zemin_bg']
    plk = np.asarray(Image.open(f'{IS}/plaka/{"BLACK" if r == "DEEP_BLACK" else "PURE_WHITE"}_24x36_temiz.png').convert('RGB')).astype(np.int16)
    tum = np.zeros(P.shape[:2], np.uint8)
    for ad, (x, y) in K.items(): a = z[ad]; tum[y:y + a.shape[0], x:x + a.shape[1]] |= (a > 0).astype(np.uint8)
    yakin = cv2.dilate(tum, np.ones((121, 121), np.uint8)).astype(bool) & ~cv2.dilate(tum, np.ones((5, 5), np.uint8)).astype(bool)
    temiz = (np.abs(plk - bg).max(2) == 0)
    Lz = lab(P)[..., 0]; Lbg = float(lab(np.full((1, 1, 3), bg, np.float32))[0, 0, 0]); dL = Lz - Lbg; m = yakin & temiz
    altin = []
    for ad, (x, y) in K.items():
        a = z[ad]; ic = cv2.erode((a > 242).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        altin.append(np.median(lab(P[y:y + a.shape[0], x:x + a.shape[1]])[ic], 0))
    Lg = float(np.median(np.array(altin)[:, 0]))
    def lum(v): v = v / 255; v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4); return float(0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2])
    rgb_g = np.median(np.concatenate([P[y:y + z[ad].shape[0], x:x + z[ad].shape[1]][cv2.erode((z[ad] > 242).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0]
                                      for ad, (x, y) in K.items()]), 0)
    lg, lb = lum(rgb_g), lum(np.full(3, bg, np.float32)); kon = (max(lg, lb) + 0.05) / (min(lg, lb) + 0.05)
    R['N'] = dict(zemin_L=round(Lbg, 1), altin_L_ortanca=round(Lg, 1), altin_RGB=rgb_g.round(0).tolist(), kontrast_orani=round(kon, 2),
                  oge_cevresi_2_60px=dict(px=int(m.sum()), koyulasma_L_p99=round(float(np.percentile(-dL[m], 99)), 2), koyulasma_L_max=round(float((-dL[m]).max()), 2),
                                           acilma_L_p99=round(float(np.percentile(dL[m], 99)), 2), acilma_L_max=round(float(dL[m].max()), 2),
                                           koyu_1L_oran=round(float((dL[m] < -1).mean()), 4), acik_1L_oran=round(float((dL[m] > 1).mean()), 4)),
                  not_='golge/isima MB kurallariyla AYNI (degistirilmedi); FAIL degil, Serdar karari')
    R['PASS'] = bool(all(R[k].get('PASS') for k in (*OLS, 'L', 'K')))
    print(r, 'PASS' if R['PASS'] else 'FAIL', {k: R[k].get('PASS') for k in (*OLS, 'L', 'K')}, flush=True)
sonuc['PASS'] = bool(all(v['PASS'] for v in sonuc.values() if isinstance(v, dict)))
if JS: json.dump(sonuc, open(JS, 'w'), indent=1, ensure_ascii=False)
print(json.dumps({r: {ol: {k: (v.get('PASS') if isinstance(v, dict) else v) for k, v in sonuc[r][ol].items()} for ol in OLS}
                  for r in sonuc if r != 'PASS'}, ensure_ascii=False))
sys.exit(0 if sonuc['PASS'] else 1)
