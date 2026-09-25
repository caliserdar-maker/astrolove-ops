"""Pod'un kartpostal fonksiyonu (siparis-onay: scripts/prodigi/kartpostal.py) icin 78 cift testi. Pod dosyasi DEGISTIRILMEZ:
dal FETCH edilip dosya gecici dizine kopyalanir ve oldugu gibi import edilir. Girdiler pod akisiyla ayni:
kaynak kart BRAND/INSERTS/..._V1.jpg, poster A1_77/<CIFT>/POSTER_AM.png, Cinzel kisisel-v1 assets/fonts.
Test: 78 cift x 'EMILY & JAMES' + 3 cift uzun isim. Pod QC kapilarina ek olcum kapilari (pod koduna dokunmadan):
  sembol_kirpilmamis  : pod'un sabit kutudan kestigi sembol, halka olcumlu referans ayristirmadan (bu dosya) en/boy olarak
                        6 px'ten fazla kucuk olmamali (kutu disina tasan sembol kirpilir).
  tr_onayli_esit      : pod'un her posterden olctugu harf araligi onayli ornekle (-0.0697) +-0.01.
  altin_onayli_esit   : pod'un isim altin profili ortalamasi onayli ornekle (ARIES_LEO ALEXANDER) max kanal farki <= 12.
  isim_cap>=16        : kuculme tabani (okunurluk).
Drive'a YALNIZ: TEMP/KARTPOSTAL_ORNEK/KARTPOSTAL_SERIT_78.jpg + KARTPOSTAL_FAIL.csv. Etsy/Prodigi erisimi yok."""
import csv, importlib.util, json, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'scipy'], check=True)       # pod kodu scipy ister
import cv2

POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
KAYNAK = 'gdrive:ASTROLOVE/BRAND/INSERTS/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg'
HEDEF = 'gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK'
CL_REPO = Path(__file__).resolve().parent / 'ref' / 'P_emily_james.png'      # onayli CL Midnight Blue (v5 video kaynagi)
UZUN = [('ARIES_LEO', 'MAXIMILIANA & CHRISTOPHER'),
        ('SAGITTARIUS_SAGITTARIUS', 'ANASTASIA-VICTORIA & MAXIMILIAN-ALEXANDER'),
        ('CANCER_CANCER', 'GUINEVERE ELIZABETH & BARTHOLOMEW JONATHAN')]
TR_ONAY, ALTIN_ONAY = -0.0697, np.array([237.7, 187.4, 69.3])
W = Path(tempfile.mkdtemp(prefix='kpt_')); OUT = Path('out_kp'); OUT.mkdir(exist_ok=True)

def rc(*a):
    return subprocess.run(['rclone', *a], capture_output=True, text=True)

def git_dosya(dal, yol, hedef):
    import os
    ref = f'origin/{dal}' if os.environ.get('KP_YEREL_TEST') else 'FETCH_HEAD'      # yerelde sig fetch yapilmaz
    if ref == 'FETCH_HEAD': subprocess.run(['git', 'fetch', '-q', '--depth', '1', 'origin', dal], check=True)
    Path(hedef).write_bytes(subprocess.run(['git', 'show', f'{ref}:{yol}'], capture_output=True, check=True).stdout)
    return subprocess.run(['git', 'rev-parse', '--short', ref], capture_output=True, text=True).stdout.strip()

pod_sha = git_dosya('siparis-onay', 'scripts/prodigi/kartpostal.py', W / 'kartpostal.py')
git_dosya('kisisel-v1', 'assets/fonts/Cinzel.ttf', W / 'Cinzel.ttf')
spec = importlib.util.spec_from_file_location('kartpostal', W / 'kartpostal.py'); KP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(KP)
assert rc('copyto', KAYNAK, str(W / 'kaynak.jpg')).returncode == 0, 'kaynak kart indirilemedi'
print(f'pod kartpostal.py @ siparis-onay {pod_sha}', flush=True)


def ref_sembol_wh(poster):
    """Referans olcum: halka cemberi olculur, halka ici + kucuk sembollerin ustu -> birlesik sembol en/boy (poster px)."""
    P = np.asarray(Image.open(poster).convert('RGB')).astype(np.float64)
    pz = np.median(P[60:260, 1100:1300].reshape(-1, 3), 0)
    m = np.abs(P - pz).max(2) > 60; m[:200] = False; m[2100:] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0).astype(np.uint8))
    h = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_WIDTH])
    ys, xs = np.where((lab == h) & m)
    cx, cy, c = np.linalg.lstsq(np.c_[2 * xs, 2 * ys, np.ones(len(xs))], xs ** 2 + ys ** 2, rcond=None)[0]
    R = np.sqrt(c + cx ** 2 + cy ** 2); alt = ys.max()
    yy, xx = np.mgrid[0:P.shape[0], 0:P.shape[1]]
    ic = m & (np.hypot(xx - cx, yy - cy) < R - 25)
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(ic.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0).astype(np.uint8))
    ad = [i for i in range(1, n) if st[i, cv2.CC_STAT_TOP] < alt - 100]
    enb = max(st[i, cv2.CC_STAT_AREA] for i in ad)
    sm = np.isin(lab, [i for i in ad if st[i, cv2.CC_STAT_AREA] >= 0.05 * enb]) & m
    ys, xs = np.where(sm)
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1), [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').stdout.split())
import os
if os.environ.get('KP_YEREL_TEST'): ciftler = ciftler[:6]                   # yerel duman testi (sahte rclone)
else: assert len(ciftler) == 78 and 'CANCER_LIBRA' in ciftler, len(ciftler)
isler = [(c, 'EMILY & JAMES', 'EJ') for c in ciftler] + [(c, m, 'UZUN') for c, m in UZUN]
nes, satir, kucuk = {}, [], {}
t0 = time.time()
for i, (c, metin, tur) in enumerate(isler, 1):
    r = {'cift': c, 'tur': tur, 'metin': metin, 'PASS': False, 'fail_kapilar': '', 'isim_cap_px': '', 'isim_en_px': '',
         'pod_sembol_wh': '', 'ref_sembol_wh': '', 'ref_sembol_kutu_poster': '', 'pod_tr': '', 'pod_altin_ort': '', 'hata': ''}
    try:
        if c not in nes:
            poster = W / f'{c}_POSTER_AM.png'
            if rc('copyto', f'{A77}/{c}/POSTER_AM.png', str(poster)).returncode != 0:      # pod akisi: yalniz POSTER_AM
                raise FileNotFoundError(f'POSTER_AM yok (A1_77/{c}); pod akisinda kart uretilmez')
            nes[c] = (KP.Kartpostal(W / 'kaynak.jpg', poster, W / 'Cinzel.ttf'), ref_sembol_wh(poster))
        K, (rw, rh, rk) = nes[c]
        q = K.uret(metin, W / f'{c}_{tur}.jpg')
        pw, ph = K.sem_poster_wh; cap = q['isim_cap_ust_taban'][1] - q['isim_cap_ust_taban'][0]
        ek = {'sembol_kirpilmamis': pw >= rw - 6 and ph >= rh - 6,
              'tr_onayli_esit': abs(K.TR_ORAN - TR_ONAY) <= 0.01,
              'altin_onayli_esit': float(np.abs(K.prof.mean(0) - ALTIN_ONAY).max()) <= 12,
              'isim_cap>=16': cap >= 16}
        kap = {**q['kapilar'], **ek}
        r.update({'PASS': all(kap.values()), 'fail_kapilar': ';'.join(k for k, v in kap.items() if not v), 'isim_cap_px': cap,
                  'isim_en_px': q['isim_en_px'], 'pod_sembol_wh': f'{pw}x{ph}', 'ref_sembol_wh': f'{rw}x{rh}',
                  'ref_sembol_kutu_poster': rk, 'pod_tr': round(K.TR_ORAN, 4), 'pod_altin_ort': np.round(K.prof.mean(0), 1).tolist()})
        if tur == 'EJ':
            kucuk[c] = (Image.open(W / f'{c}_{tur}.jpg').convert('RGB').resize((186, 262), Image.LANCZOS), r['PASS'], '')
    except Exception as e:                                                  # noqa: BLE001  cift FAIL olur, is durmaz
        r.update({'fail_kapilar': 'istisna', 'hata': repr(e)[:200]})
        if tur == 'EJ' and c == 'CANCER_LIBRA':
            # bilgi: pod fonksiyonu depodaki onayli CL posteriyle (pod akisinda bu poster YOK)
            try:
                Kc = KP.Kartpostal(W / 'kaynak.jpg', CL_REPO, W / 'Cinzel.ttf'); qc = Kc.uret(metin, W / 'CL_repo.jpg')
                kucuk[c] = (Image.open(W / 'CL_repo.jpg').convert('RGB').resize((186, 262), Image.LANCZOS), False,
                            f'repo poster: pod QC {"PASS" if qc["PASS"] else "FAIL"}')
                r['hata'] += f' | bilgi: pod fonksiyonu repo CL posteriyle QC {"PASS" if qc["PASS"] else "FAIL"}'
            except Exception as e2:                                         # noqa: BLE001
                r['hata'] += f' | repo CL: {repr(e2)[:100]}'
    satir.append(r)
    g = time.time() - t0; kal = g / i * (len(isler) - i)
    print(f'[{i}/{len(isler)}] %{100 * i / len(isler):.0f} gecen {g:.0f}s kalan ~{kal:.0f}s | {c} {tur} '
          f'{"PASS" if r["PASS"] else "FAIL " + r["fail_kapilar"] + " " + r["hata"]} cap={r["isim_cap_px"]} '
          f'sembol pod/ref={r["pod_sembol_wh"]}/{r["ref_sembol_wh"]} tr={r["pod_tr"]}', flush=True)

tw, th, et, g = 186, 262, 40, 10; kol = 13; sat = (len(ciftler) + kol - 1) // kol
S = Image.new('RGB', (kol * (tw + g) + g, sat * (th + et + g) + g + 50), (236, 233, 226)); dr = ImageDraw.Draw(S)
f = ImageFont.truetype(str(W / 'Cinzel.ttf'), 13); fb = ImageFont.truetype(str(W / 'Cinzel.ttf'), 24)
npass = sum(1 for r in satir if r['tur'] == 'EJ' and r['PASS']); upass = sum(1 for r in satir if r['tur'] == 'UZUN' and r['PASS'])
dr.text((g, 12), f'POD kartpostal.py ({pod_sha})  78 CIFT  EMILY & JAMES  PASS {npass}/78   UZUN ISIM PASS {upass}/3   (kirmizi = FAIL)',
        font=fb, fill=(30, 30, 30))
for i, c in enumerate(ciftler):
    x, y = g + (i % kol) * (tw + g), 50 + g + (i // kol) * (th + et + g)
    if c in kucuk:
        im, ok, notu = kucuk[c]; S.paste(im, (x, y))
        if not ok: dr.rectangle((x - 3, y - 3, x + tw + 2, y + th + 2), outline=(200, 0, 0), width=4)
        if notu: dr.text((x + tw / 2, y + th + 20), notu, font=f, fill=(200, 0, 0), anchor='ma')
    else:
        dr.rectangle((x, y, x + tw, y + th), outline=(200, 0, 0), width=4); dr.text((x + 20, y + th / 2), 'URETILEMEDI', font=f, fill=(200, 0, 0))
    dr.text((x + tw / 2, y + th + 4), c, font=f, fill=(40, 40, 40), anchor='ma')
S.save(OUT / 'KARTPOSTAL_SERIT_78.jpg', quality=90)
alan = list(satir[0].keys())
with open(OUT / 'KARTPOSTAL_FAIL.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=alan); w.writeheader()
    fails = [r for r in satir if not r['PASS']]
    for r in fails: w.writerow(r)
    w.writerow({k: '' for k in alan} | {'cift': f'OZET pod {pod_sha}: EMILY & JAMES {npass}/78 PASS, uzun isim {upass}/3 PASS, FAIL {len(fails)}'})
for r in satir:
    if r['tur'] == 'UZUN' or not r['PASS']: print('SATIR', json.dumps(r, ensure_ascii=False, default=str))
print(json.dumps({'pod_sha': pod_sha, 'EJ_PASS': npass, 'UZUN_PASS': upass, 'FAIL': len(fails), 'sure_s': round(time.time() - t0)}), flush=True)
rc('deletefile', f'{HEDEF}/KARTPOSTAL_SERIT_78.jpg'); rc('deletefile', f'{HEDEF}/KARTPOSTAL_FAIL.csv')    # onceki (kendi fonksiyonum) kosunun ciktisi
subprocess.run(['rclone', 'copy', str(OUT), HEDEF], check=True)
subprocess.run(['rclone', 'lsl', HEDEF, '--include', 'KARTPOSTAL_SERIT_78.jpg', '--include', 'KARTPOSTAL_FAIL.csv'], check=True)
