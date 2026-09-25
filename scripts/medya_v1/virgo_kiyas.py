#!/usr/bin/env python3
"""VIRGO^2 Warm Parchment aykiriligi - SALT OKUR kiyas (Serdar 2. madde).

25 Eyl plate olcumunde WP'nin iki boyunda da VIRGO_VIRGO dosyasi plate'ten
sayfanin ~%60'inda sapti (murekkep orani 0.605-0.619); ayni cift MB'de 0.057,
CI'de 0.061. Bu script neyin farkli oldugunu SAYIYLA gosterir ve uc goruntuyu
yan yana koyar. HICBIR DOSYAYA DOKUNULMAZ - yalniz okunur, yeni bir onizleme
uretilir.

Kiyas: VIRGO_VIRGO/WARM_PARCHMENT/<boy>.jpg | ayni ciftin MIDNIGHT_BLUE dosyasi
       | WARM_PARCHMENT plate  (+ |WP dosya - WP plate| fark haritasi)
Kontrol: ayni uclusu NORMAL bir cift icin de (CAPRICORN_SCORPIO) uretir, boylece
"aykiri olan ne" gozle ve sayiyla kiyaslanabilir.
"""
import json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
CIK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/VIRGO_AYKIRI'
W = Path('_virgo').resolve(); W.mkdir(exist_ok=True)
BOY = '30x40'
CIFTLER = [('VIRGO_VIRGO', 'aykiri'), ('CAPRICORN_SCORPIO', 'kontrol')]
YUK = 1100                 # onizleme yuksekligi


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '180s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def indir(uzak, ad):
    yol = W / ad
    if not yol.exists():
        rc('copy', uzak, str(W), timeout=1800)
        kaynak = W / Path(uzak).name
        if kaynak != yol and kaynak.exists():
            kaynak.replace(yol)
    return yol


def kucult(im, yuk=YUK):
    return im.resize((max(round(im.width * yuk / im.height), 1), yuk), Image.LANCZOS)


def istatistik(a, pl):
    f = np.abs(a.astype(np.int16) - pl.astype(np.int16)).max(axis=2)
    L = a.astype(np.float32).mean(axis=2)
    Lp = pl.astype(np.float32).mean(axis=2)
    return {'fark_p50': float(np.percentile(f, 50)), 'fark_p90': float(np.percentile(f, 90)),
            'fark_p99': float(np.percentile(f, 99)), 'fark_max': int(f.max()),
            'esik30_ustu_oran': round(float((f > 30).mean()), 4),
            'ton_ort_dosya': round(float(L.mean()), 2), 'ton_ort_plate': round(float(Lp.mean()), 2),
            'ton_std_dosya': round(float(L.std()), 2), 'ton_std_plate': round(float(Lp.std()), 2),
            'kanal_ort_dosya': [round(float(a[..., i].mean()), 2) for i in range(3)],
            'kanal_ort_plate': [round(float(pl[..., i].mean()), 2) for i in range(3)]}


def main():
    plate_yol = indir(f'{PLATES}/VINTAGE_{BOY}.png', f'VINTAGE_{BOY}.png')
    with Image.open(plate_yol) as im:
        pl = np.asarray(im.convert('RGB'))
    rapor = {'tarih': datetime.now(timezone.utc).isoformat(), 'boy': BOY,
             'plate': f'VINTAGE_{BOY}.png', 'ciftler': {}}
    for cift, rol in CIFTLER:
        wp = indir(f'{POD}/{cift}/WARM_PARCHMENT/{BOY}.jpg', f'{cift}_WP.jpg')
        mb = indir(f'{POD}/{cift}/MIDNIGHT_BLUE/{BOY}.jpg', f'{cift}_MB.jpg')
        with Image.open(wp) as im:
            a = np.asarray(im.convert('RGB'))
        st = istatistik(a, pl) if a.shape == pl.shape else {'hata': f'boyut {a.shape} != {pl.shape}'}
        st['rol'] = rol
        rapor['ciftler'][cift] = st
        # fark haritasi (gorsel): 0-60 araligi gri tona acilir
        f = np.abs(a.astype(np.int16) - pl.astype(np.int16)).max(axis=2)
        fim = Image.fromarray(np.clip(f * (255 / 60), 0, 255).astype(np.uint8)).convert('RGB')
        with Image.open(wp) as i1, Image.open(mb) as i2:
            parcalar = [(f'{cift} WARM_PARCHMENT (dosya)', kucult(i1.convert('RGB'))),
                        (f'{cift} MIDNIGHT_BLUE (ayni cift)', kucult(i2.convert('RGB'))),
                        (f'VINTAGE_{BOY} plate (medyan)', kucult(Image.fromarray(pl))),
                        ('|WP dosya - plate| (x4 parlak)', kucult(fim))]
        en = sum(im.width for _, im in parcalar) + 20 * (len(parcalar) + 1)
        t = Image.new('RGB', (en, YUK + 70), 'white')
        d = ImageDraw.Draw(t)
        x = 20
        for ad, im in parcalar:
            t.paste(im, (x, 50)); d.text((x, 20), ad, fill='black'); x += im.width + 20
        d.text((20, YUK + 54), json.dumps({k: st[k] for k in (
            'fark_p50', 'fark_p99', 'esik30_ustu_oran', 'ton_ort_dosya', 'ton_ort_plate')}
            if 'hata' not in st else st), fill='black')
        ad = f'VIRGO_KIYAS_{rol.upper()}_{cift}_{BOY}.jpg'
        t.save(W / ad, quality=90)
        log(f'{cift} ({rol}) ' + json.dumps(st))
    (W / 'VIRGO_AYKIRI.json').write_text(json.dumps(rapor, indent=1, ensure_ascii=False),
                                         encoding='utf-8')
    for f in list(W.glob('VIRGO_KIYAS_*.jpg')) + [W / 'VIRGO_AYKIRI.json']:
        rc('copy', str(f), CIK, timeout=900)
    print(json.dumps(rapor, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
