#!/usr/bin/env python3
"""Acilis P ile toplu sosyal video (20 Eki 2026, Serdar: P onayli). Yazma yok; yalniz dosya uretir.

Kural --acilis P (8fb44080) ile birebir: her cift icin acilis_p.p_kare (kendi pin gorunumu; olcek s onayli CANCER_LIBRA ile
ayni, sigmayan baslik yalniz kendisi kuculur), video_uret --acilis P (muzikli, 24 sn), B ile esitlik kareleri ve
p_qc.olc (kontaksiz) kontrolleri. Paralel isci sayisi --is.
Cikti (OUT): <slug>-astroloveart-reel.mp4, ILK/<CIFT>.jpg (arayuz alanlari isaretli ilk kare), satir/<CIFT>.json (KONTROL
satiri), olcum/<CIFT>_OLCUM.txt. CANCER_LIBRA icin --onay_p verilirse P karesi onayli P_kare.png ile karsilastirilir (fark 0).
Kullanim: video_p_toplu.py --posters DIR --pairs A_B,C_D --font EBGaramond[wght].ttf --muzik muzik.m4a --out OUT [--is 4] [--onay_p P.png]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acilis_p as AP  # noqa: E402
import p_qc  # noqa: E402

ESIT_T = ','.join(f'{s:g}' for s in p_qc.ESIT_T)


def calis(cmd, log):
    with open(log, 'a') as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f'{os.path.basename(cmd[1])} cikis {r.returncode} (log {log})')


def is_(arg):
    cift, posters, font, muzik, out, onay_p = arg
    t0 = time.time()
    a, b = (x.capitalize() for x in cift.split('_'))
    slug = f'{a.lower()}-and-{b.lower()}'
    d = os.path.join(out, '_is', cift); os.makedirs(os.path.join(d, 'kare'), exist_ok=True)
    log = os.path.join(d, 'log.txt')
    satir = {'cift': cift, 'baslik': f'{cift.split("_")[0]} / & / {cift.split("_")[1]}'}
    try:
        shutil.copy(os.path.join(posters, f'{cift}.jpg'), os.path.join(d, 'poster.jpg'))
        shutil.copy(muzik, os.path.join(d, 'muzik.m4a'))
        k, bi = AP.p_kare(os.path.join(d, 'poster.jpg'), a, b, font)
        Image.fromarray(k).save(os.path.join(d, 'P_kare.png'))
        json.dump(bi, open(os.path.join(d, 'p.json'), 'w'), indent=1)
        if onay_p and cift == 'CANCER_LIBRA':
            fk = int(np.abs(k.astype(int) - np.asarray(Image.open(onay_p).convert('RGB')).astype(int)).max())
            satir['onayli_p_fark'] = fk
        vu = [sys.executable, os.path.join(HERE, 'video_uret.py'), '--poster', os.path.join(d, 'poster.jpg'), '--a', a, '--b', b]
        vt = [sys.executable, os.environ.get('VIDEO_URET_TAM', os.path.join(HERE, 'video_uret.py'))] + vu[2:]   # yerel deneme: hizli taklit
        calis(vt + ['--out', os.path.join(d, 'v'), '--muzik', os.path.join(d, 'muzik.m4a'), '--acilis', 'P',
                    '--acilis_kare', os.path.join(d, 'P_kare.png')], log)
        os.replace(os.path.join(d, 'v', f'{slug}-astroloveart-reel.mp4'), os.path.join(d, f'P_{cift}.mp4'))
        calis(vu + ['--out', os.path.join(d, 'kare', 'B_esit'), '--acilis', 'B', '--kareler', ESIT_T], log)
        calis(vu + ['--out', os.path.join(d, 'kare', 'P_esit'), '--acilis', 'P', '--acilis_kare', os.path.join(d, 'P_kare.png'),
                    '--kareler', ESIT_T], log)
        olc, M = p_qc.olc(d, cift, kontak=False)
        satir.update(M)
        if 'onayli_p_fark' in satir and satir['onayli_p_fark'] != 0:
            satir['sonuc'] = 'FAIL'; satir['fail'] = (satir.get('fail', '') + '; onayli P karesinden farkli').strip('; ')
        os.replace(os.path.join(d, f'P_{cift}.mp4'), os.path.join(out, f'{slug}-astroloveart-reel.mp4'))
        shutil.copy(os.path.join(d, 'ILK_KARE_ARAYUZ.jpg'), os.path.join(out, 'ILK', f'{cift}.jpg'))
        shutil.copy(os.path.join(d, 'OLCUM.txt'), os.path.join(out, 'olcum', f'{cift}_OLCUM.txt'))
    except Exception as e:  # noqa: BLE001
        satir.update(sonuc='FAIL', fail=f'{type(e).__name__}: {e}'[:300])
        with open(log, 'a') as fh:
            fh.write(traceback.format_exc())
    satir['sure_sn'] = round(time.time() - t0)
    json.dump(satir, open(os.path.join(out, 'satir', f'{cift}.json'), 'w'), indent=1, default=str)
    if satir.get('sonuc') == 'PASS':
        shutil.rmtree(d, ignore_errors=True)
    return satir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posters', required=True)
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--font', required=True)
    ap.add_argument('--muzik', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--is', dest='isci', type=int, default=4)
    ap.add_argument('--onay_p')
    g = ap.parse_args()
    out = os.path.abspath(g.out)
    for s in ('ILK', 'satir', 'olcum', '_is'):
        os.makedirs(os.path.join(out, s), exist_ok=True)
    ciftler = [c for c in g.pairs.split(',') if c]
    arglar = [(c, os.path.abspath(g.posters), os.path.abspath(g.font), os.path.abspath(g.muzik), out,
               os.path.abspath(g.onay_p) if g.onay_p else None) for c in ciftler]
    t0 = time.time(); sonuc = []
    with ProcessPoolExecutor(g.isci) as ex:
        for i, s in enumerate(ex.map(is_, arglar), 1):
            sonuc.append(s); gec = time.time() - t0
            print(f"ILERLEME {i}/{len(ciftler)} %{100 * i // len(ciftler)} gecen {gec:.0f} sn kalan ~{gec / i * (len(ciftler) - i):.0f} sn | "
                  f"{s['cift']} {s.get('sonuc')} baslik {s.get('baslik_px')}px x{s.get('baslik_kucultme')} NCC {s.get('poster_ncc')} "
                  f"{s.get('fail', '')}", flush=True)
    n = sum(s.get('sonuc') == 'PASS' for s in sonuc)
    print(f'OZET {n}/{len(sonuc)} PASS; FAIL: {[s["cift"] for s in sonuc if s.get("sonuc") != "PASS"]}')
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == '__main__':
    main()
