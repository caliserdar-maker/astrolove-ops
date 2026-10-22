#!/usr/bin/env python3
"""POD_PRINT ve kaynak cozunurluk olcumu (SALT OKUR).

Siparis baski dosyasi ureticisi icin gereken sayilar:
 1) POD_PRINT'te hangi boylar var, dosyalar kac piksel, hangi dpi'ye denk geliyor
 2) Canva'dan indirilen ornek sayfalarin gercek pikselleri (A1_BOY_LISTE.json ile)
 3) Onayli render hattinin cikti genisligi (pilot11.NORM_W)
Etsy/Prodigi'ye erisim YOK, hicbir sey yazilmaz (yalnizca rapor Drive'a).
"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KP = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
SIP = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM'
W = Path('_olcum').resolve(); W.mkdir(exist_ok=True)


def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def rc(*a, timeout=600):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def maskele(u):
    print(f'::add-mask::{u}', flush=True)
    for p in u.split('&'):
        if p.startswith('X-Amz-Signature='):
            print(f'::add-mask::{p.split("=", 1)[1]}', flush=True)


def indir(u, hedef):
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=300) as r:
                hedef.write_bytes(r.read())
            return hedef.stat().st_size
        except Exception as e:                                    # noqa: BLE001
            son = e; time.sleep(2 ** i)
    raise RuntimeError(f'indirilemedi: {son}')


def dpi(px, boy):
    """boy: '12x16' (inc) ya da 'A3'. -> (en_dpi, boy_dpi) ya da None."""
    INC = {'A3': (11.693, 16.535), 'A4': (8.268, 11.693), 'A2': (16.535, 23.386)}
    if boy in INC:
        w, h = INC[boy]
    elif 'x' in boy:
        try:
            w, h = (float(x) for x in boy.split('x'))
        except ValueError:
            return None
    else:
        return None
    return [round(px[0] / w, 1), round(px[1] / h, 1)]


R = {'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}

# 1) POD_PRINT yapisi
ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
R['pod_cift_sayisi'] = len(ciftler)
R['pod_ilk5'] = ciftler[:5]
R['sayfa_no'] = {c: i + 1 for i, c in enumerate(ciftler)
                 if c in ('ARIES_LEO', 'AQUARIUS_AQUARIUS', 'CANCER_LIBRA')}
renkler = sorted(x.strip('/') for x in rc('lsf', f'{POD}/{ciftler[0]}', '--dirs-only').split())
R['pod_renkler'] = renkler
log('POD ciftler', len(ciftler), 'renkler', renkler, 'sayfa_no', R['sayfa_no'])

# 2) Bir ciftin butun boylarini olc (CANCER_LIBRA, her renk icin ayni boy listesi beklenir)
R['pod_boylar'] = {}
for renk in renkler:
    dosyalar = sorted(x for x in rc('lsf', f'{POD}/CANCER_LIBRA/{renk}').split() if x.endswith('.jpg'))
    R['pod_boylar'][renk] = dosyalar
log('CANCER_LIBRA boylari', R['pod_boylar'])

hedef = W / 'pod'; hedef.mkdir(exist_ok=True)
renk0 = renkler[0]
rc('copy', f'{POD}/CANCER_LIBRA/{renk0}', str(hedef), timeout=900)
R['pod_piksel'] = {}
for p in sorted(hedef.glob('*.jpg')):
    with Image.open(p) as im:
        px = list(im.size)
    boy = p.stem
    R['pod_piksel'][boy] = {'renk': renk0, 'px': px, 'MB': round(p.stat().st_size / 1e6, 2),
                            'dpi': dpi(px, boy), 'oran': round(px[0] / px[1], 4)}
log('POD piksel', json.dumps(R['pod_piksel'], ensure_ascii=False))

# 3) Onayli render hattinin cikti genisligi
try:
    subprocess.run(['git', 'fetch', '--depth', '1', 'origin', 'kisisel-v1'], check=True)
    arc = subprocess.run(['git', 'archive', 'FETCH_HEAD', 'scripts/kisisel'],
                         capture_output=True, check=True).stdout
    kk = W / 'kisisel'; kk.mkdir(exist_ok=True)
    subprocess.run(['tar', '-x', '-C', str(kk)], input=arc, check=True)
    sys.path.insert(0, str(kk / 'scripts' / 'kisisel'))
    import pilot11
    R['render_norm_w'] = pilot11.NORM_W
    sab = json.loads((kk / 'scripts' / 'kisisel' / 'ORAN_SABITLERI.json').read_text())
    R['edisyon_kilit_var'] = sorted(k for k in sab.get('edisyonlar', {}) if not k.startswith('_'))
except Exception as e:                                            # noqa: BLE001
    R['render_norm_w'] = f'okunamadi: {e}'
log('render NORM_W', R['render_norm_w'])

# 4) Canva ornek sayfalari (varsa): gercek piksel
try:
    rc('copy', f'{KP}/A1_BOY_LISTE.json', str(W))
    L = json.loads((W / 'A1_BOY_LISTE.json').read_text())
    R['canva'] = {}
    ham = W / 'ham'; ham.mkdir(exist_ok=True)
    for ad, v in L.items():
        u = v['url'] if isinstance(v, dict) else v
        maskele(u)
        p = ham / f'{ad}.png'
        n = indir(u, p)
        with Image.open(p) as im:
            px = list(im.size); mod = im.mode
        R['canva'][ad] = {'px': px, 'MB': round(n / 1e6, 2), 'mod': mod,
                          'istenen': (v.get('istenen') if isinstance(v, dict) else None)}
        log('canva', ad, R['canva'][ad])
except Exception as e:                                            # noqa: BLE001
    R['canva'] = f'liste yok ya da indirilemedi: {e}'

# 5) Siparis kartlari klasoru
try:
    R['siparis_kartlari'] = sorted(rc('lsf', SIP).split())[:20]
except Exception as e:                                            # noqa: BLE001
    R['siparis_kartlari'] = f'okunamadi: {e}'

R['toplam_sn'] = round(time.time() - T0, 1)
(W / 'POD_OLCUM.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
rc('copy', str(W / 'POD_OLCUM.json'), f'{KP}')
print(json.dumps(R, ensure_ascii=False, indent=1)[:6000], flush=True)
