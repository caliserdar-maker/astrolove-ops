#!/usr/bin/env python3
"""ORNAMENT_78_ORNEK6 (Merkez karar 28, 3 Kas): 6 cift x 5 stil ornek. Kapi listesi: docs/ornament/ornek/ORNEK78_KAPI_LISTESI.md.
Cift basina (onayli 5 stil hatti, degisiklik yok): ornament_motor.py --cift --zemin (RUBY / SAPPHIRE / EMERALD, deneme 4 ogeler, eliptik zemin),
ORN_DUMP + ornament_sade.py (SADE ALTIN = SADE_1), ornament_fildisi.py (birebir; girdi o ciftin SADE_1'i).
Sira: once CANCER_LIBRA (kontrol): 5 PNG onayli 5STIL dosyalarina ham pikselde <= 1 seviye ve <= 10 px; FAIL ise DUR (cikis 3, diger ciftler yok).
Olcum: motor OLCUM (kontrast, dE00, IoU, alfa farki, leke, goruntu yasak, bosluk, sembol kutusu, halka), SADE OLCUM, yerlesim kapisi
(o4.kapi: delik / guvenli daire disi / ust yasak px, oge maskesinden; stilden bagimsiz) ve stil basina goruntu yasak (motor: koyu 3; SADE).
Cikti: --cikti altina 30 PNG (<CIFT>_<STIL>_954.png); --rapor altina ONIZLEME_76mm_6CIFT.png + OLCUM.json.
Kullanim: ornek78.py --kaynak K --motor MD --zemin ZE --son SON --onayli ON5 --cikti O --rapor R --font TTF"""
import argparse
import hashlib
import importlib.util
import json
import os
import pickle
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o4, o3, o1, son = al.o5, al.o4, al.o3, al.o1, al.son
CIFTLER = tuple(os.environ.get('ORNEK78_CIFTLER', 'CANCER_LIBRA,ARIES_ARIES,CAPRICORN_SAGITTARIUS,AQUARIUS_PISCES,GEMINI_VIRGO,LEO_SCORPIO').split(','))
STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
TOL_SEVIYE, TOL_PIKSEL = 1, 10
PY = sys.executable
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def kos(arg, env=None, log_dosya=None):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run([PY, '-I'] + [str(x) for x in arg], env=e, capture_output=True, text=True)
    if log_dosya:
        Path(log_dosya).write_text(r.stdout + r.stderr)
    return r.returncode


def ham(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    for k in ('kaynak', 'motor', 'zemin', 'son', 'onayli', 'cikti', 'rapor', 'font'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    O, RP = Path(a.cikti), Path(a.rapor); O.mkdir(parents=True, exist_ok=True); RP.mkdir(parents=True, exist_ok=True)
    W = O / '_is'; W.mkdir(exist_ok=True)
    o4.YASAK = o4.yasak_m(); o3.YASAK = o4.YASAK
    o4.GLOW_K = __import__('cv2').getStructuringElement(__import__('cv2').MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    R = dict(gorev='ORNAMENT_78_ORNEK6 (karar 28)', kapi_listesi='docs/ornament/ornek/ORNEK78_KAPI_LISTESI.md', cift={}, kontrol={})
    for cift in CIFTLER:
        w = W / cift; w.mkdir(exist_ok=True)
        log('cift', cift)
        k1 = kos([_d / 'ornament_motor.py', '--kaynak', a.kaynak, '--motor', a.motor, '--cikti', w / 'motor', '--son', a.son, '--zemin', a.zemin, '--cift', cift],
                 log_dosya=w / 'log_motor.txt')
        k2 = kos([_d / 'ornament_motor.py', '--kaynak', a.kaynak, '--motor', a.motor, '--cikti', w / 'dump', '--son', a.son, '--cift', cift],
                 env={'ORN_DUMP': str(w / 'katman.pkl')}, log_dosya=w / 'log_dump.txt')
        k3 = kos([_d / 'ornament_sade.py', '--katman', w / 'katman.pkl', '--cikti', w / 'sade'], log_dosya=w / 'log_sade.txt')
        sade1 = w / 'sade' / 'SADE_1_ALTIN_TONU_954.png'
        k4 = kos([_d / 'ornament_fildisi.py', sade1, O / f'{cift}_FILDISI_954.png'], log_dosya=w / 'log_fildisi.txt') if sade1.exists() else 9
        for s in ('RUBY', 'SAPPHIRE', 'EMERALD'):
            f = w / 'motor' / f'{cift}_{s}_954.png'
            if f.exists():
                shutil.copyfile(f, O / f'{cift}_{s}_954.png')
        if sade1.exists():
            shutil.copyfile(sade1, O / f'{cift}_SADE_ALTIN_954.png')
        cikis = dict(motor=k1, dump=k2, sade=k3, fildisi=k4)
        eksik = [s for s in STIL if not (O / f'{cift}_{s}_954.png').exists()]
        r = dict(cikis_kodlari=cikis, eksik=eksik, not_='motor cikis 1 beklenen (halka surekliligi bilgi kapisi)')
        if eksik:
            r['hata'] = 'eksik dosya'
            R['cift'][cift] = r
            log('FAIL eksik', cift, eksik, cikis)
            if cift == 'CANCER_LIBRA':
                (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False)); return 3
            continue
        M_ = json.loads((w / 'motor' / 'OLCUM.json').read_text())
        S_ = json.loads((w / 'sade' / 'OLCUM.json').read_text())['aday']['1']
        D = pickle.load(open(w / 'katman.pkl', 'rb'))
        _, yb, cak, ok = o4.kapi(D['E'])
        cv2 = __import__('cv2')
        ink = np.maximum.reduce([D['M'][k] for k in D['M'] if k != 'halka']) > 0.02     # halka haric (delikten gecer, muaf)
        uzak = {}
        for yk, ym in o4.YASAK.items():
            dd = cv2.distanceTransform((~ym.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
            uzak[yk] = round(float(dd[ink].min()), 1) if ink.any() else None
        r.update(
            yerlesim=dict(kapi_ok=bool(ok), yasak_px=yb, cakisma=cak[:4], bosluk_px=M_['sonuc']['RUBY']['bosluk_px'], sembol_kutu=M_['kutu']['sembol'],
                          halka_kutu=M_['kutu']['halka'], kucuk_sol_kutu=M_['kutu']['kucuk_sol'], kucuk_sag_kutu=M_['kutu']['kucuk_sag'],
                          sembol_ust_y=M_['kutu']['sembol'][1], sembol_ust_y_cancer_libra=246, yasak_bolgeye_en_kisa_uzaklik_px=uzak,
                          yerlesim_bilgi=M_['yerlesim']),
            koyu={s: dict(kontrast_ortanca=M_['sonuc'][s]['kontrast_ortanca_en_kotu'], kati_koyu5_bilgi=M_['sonuc'][s]['kati_koyu5_en_kotu_bilgi'],
                          dE00_ham_maks=max(M_['sonuc'][s]['dE00_son_ham'].values()), goruntu_yasak=M_['sonuc'][s]['goruntu_yasak'],
                          halka_sureklilik_bilgi=M_['sonuc'][s]['halka_sureklilik']['oran'], kucuk_oge_artis=M_['sonuc'][s]['kucuk_oge_parlaklik_artisi'])
                  for s in ('RUBY', 'SAPPHIRE', 'EMERALD')},
            iou=M_['iou_954'], alfa_fark={k: v['ort_mutlak_fark_murekkep'] for k, v in M_['iou_954_bilgi'].items()},
            motor_kapi=M_['kapi'], kaynak_leke=M_.get('kaynak_leke_onarim_sonrasi'),
            sade=dict(kati_kontrast_bilgi=S_['kati_kontrast_en_kotu'], goruntu_yasak=S_['goruntu_yasak'], leke_a=S_['leke_a'], zemin_seffaf=S_['zemin_seffaf']),
            fildisi=dict(yerlesim_yasak_px=yb, not_='fildisi ayni oge katmani (SADE_1) + krem zemin; yasak px yerlesimden'))
        R['cift'][cift] = r
        log(cift, 'yasak', yb, 'kontrast', {s: r['koyu'][s]['kontrast_ortanca'] for s in r['koyu']}, 'dE00', {s: r['koyu'][s]['dE00_ham_maks'] for s in r['koyu']},
            'sembol', r['yerlesim']['sembol_kutu'], 'uzaklik', uzak, 'kapi', {k: v for k, v in M_['kapi'].items() if not v})
        if cift == 'CANCER_LIBRA':
            hepsi = True
            for s in STIL:
                u = np.asarray(Image.open(O / f'{cift}_{s}_954.png')); on = np.asarray(Image.open(Path(a.onayli) / f'CANCER_LIBRA_{s}_954.png'))
                ayni = u.shape == on.shape
                fark = int(np.abs(u.astype(int) - on.astype(int)).max()) if ayni else None
                n = int((u != on).any(-1).sum()) if ayni else None
                ok_ = bool(ayni and fark <= TOL_SEVIYE and n <= TOL_PIKSEL)
                hepsi &= ok_
                R['kontrol'][s] = dict(en_buyuk_fark=fark, farkli_piksel=n, tolerans_icinde=ok_, uretim_ham=ham(u), onayli_ham=ham(on))
                log('KONTROL', s, fark, n, 'PASS' if ok_ else 'FAIL')
            R['kontrol_pass'] = bool(hepsi)
            if not hepsi:
                (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False)); log('DUR kontrol cifti FAIL'); return 3
    # onizleme: satir = cift, sutun = 5 stil
    font = ImageFont.truetype(a.font, 24)
    satir = []
    for cift in CIFTLER:
        if R['cift'].get(cift, {}).get('eksik'):
            continue
        liste, et = [], []
        for s in STIL:
            im = Image.open(O / f'{cift}_{s}_954.png')
            if im.mode == 'RGBA':
                b = Image.new('RGB', im.size, (255, 255, 255)); b.paste(im, (0, 0), im); im = b
            liste.append(np.asarray(im.convert('RGB')))
            k = R['cift'][cift]
            v = (f'kontrast {k["koyu"][s]["kontrast_ortanca"]}, dE00 {k["koyu"][s]["dE00_ham_maks"]}' if s in k['koyu'] else
                 (f'kati kontrast {k["sade"]["kati_kontrast_bilgi"]} (bilgi)' if s == 'SADE_ALTIN' else 'krem zemin (bilgi)'))
            et.append(f'{cift} / {s}\n{v}\nyasak px {sum(k["yerlesim"]["yasak_px"].values())}')
        satir.append(son.onizleme_etiketli(liste, et, font, h_et=96))
    Wd = max(x.width for x in satir)
    u = Image.new('RGB', (Wd, sum(x.height + 16 for x in satir)), 'white'); y = 0
    for x in satir:
        u.paste(x, (0, y)); y += x.height + 16
    u.save(RP / 'ONIZLEME_76mm_6CIFT.png', dpi=(300, 300))
    R['png_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.glob('*_954.png'))}
    (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    log('BITTI', len(R['png_sha256']), 'PNG')
    return 0


if __name__ == '__main__':
    sys.exit(main())
