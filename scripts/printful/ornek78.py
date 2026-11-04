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
from PIL import Image, ImageDraw, ImageFont

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


N_ = 954
DPI = 300                                                                    # ORNAMENT_KARAR 6: Printful 900 Circle, 954 px = 300 dpi = 80,8 mm tuval
MM_PX = 25.4 / DPI
KESIM = (476.0, 477.0, 449.0)                                                # urun kesim dairesi r 449 px = 76 mm (KARAR 6)
DIS_R, GUVENLI_R = 474.0, 380.0                                              # dis daire r ~474, guvenli alan r ~380 (KARAR 6)
DELIK_K = (476.0, 163.0, 34.0)                                               # delik merkez (476,163), dis r ~34 (KARAR 6)
CIZGI = (150, 150, 150)


def sinir_ciz(im):
    """onizleme (yalniz onizleme, uretim PNG'sine dokunmaz): kesim dairesi (gri 2 px), delik (gri 2 px), dis daire ve guvenli alan (acik gri 1 px)."""
    im = im.convert('RGB').copy(); d = ImageDraw.Draw(im)
    cx, cy, r = KESIM
    for r_, renk, w in ((DIS_R, (205, 205, 205), 1), (GUVENLI_R, (205, 205, 225), 1), (r, CIZGI, 2)):
        d.ellipse((cx - r_, cy - r_, cx + r_, cy + r_), outline=renk, width=w)
    x, y, r = DELIK_K
    d.ellipse((x - r, y - r, x + r, y + r), outline=CIZGI, width=2)
    return im


def gercek_boy(O, cift, stiller, dosya):
    """gercek boy onizleme: 954 px karolar yan yana (30 px ara), 300 dpi (1 px = 25,4/300 mm); karo basina sinir_ciz."""
    kar = []
    for s in stiller:
        f = O / f'{cift}_{s}_954.png'
        if not f.exists():
            return None
        im = Image.open(f)
        if im.mode == 'RGBA':
            b = Image.new('RGB', im.size, (255, 255, 255)); b.paste(im, (0, 0), im); im = b
        kar.append(sinir_ciz(im))
    T = Image.new('RGB', (len(kar) * N_ + (len(kar) - 1) * 30, N_), 'white')
    for i, k in enumerate(kar):
        T.paste(k, (i * (N_ + 30), 0))
    T.save(dosya, dpi=(DPI, DPI))
    return dict(dosya=Path(dosya).name, stiller=list(stiller), dpi=DPI, tuval_mm=round(N_ * MM_PX, 2), kesim_cap_mm=round(2 * KESIM[2] * MM_PX, 2))


def acik_kontrast(rgb, D):
    """FILDISI (bilgi): ornament_sade kati kontrast ile ayni ogeler ve yontem (o5.kontrast_yeni 'acik'); kati = en kotu oge, ortanca = en kotu ortanca."""
    M = D['M']
    ok = {k: o5.kontrast_yeni(rgb, M[k], 'acik') for k in ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag', 'sonsuz')}
    ok['halka_govde'] = o5.kontrast_yeni(rgb, M['halka'] * D['govde'], 'acik')
    ok['halka_uclari'] = o5.kontrast_yeni(rgb, M['halka'] * D['um'][0], 'acik')
    kk = {k: v['deger'] for k, v in ok.items() if v.get('deger') is not None}
    oo = {k: v['ortanca_bilgi'] for k, v in ok.items() if v.get('ortanca_bilgi') is not None}
    return dict(kati=min(kk.values()), kati_en_kotu_oge=min(kk, key=kk.get), ortanca=min(oo.values()), oge=kk, oge_ortanca=oo)


def kenar_kayit(a, cift, w, M_, O, DE, KENAR):
    """C (Serdar 4 Kas O1): kenar_onar kaydi + degisen varsa onarimsiz motor (ORN_KENAR_ONARIM_KAPALI=1, yalniz test parametresi) ve
    954 4x once / sonra yakin plani (RUBY; kova_kanit KOVA_954_YAKIN_4x yontemi: kaynak bilesen kutusu -> oge kutusu dogrusal esleme)."""
    KO = M_.get('kaynak_kenar_onarim') or {}
    b1, b2 = cift.lower().split('_')
    degisen = [ad for ad, k_ in KO.items() if k_.get('degisen_piksel')]
    k_on = None
    if degisen:
        k_on = kos([_d / 'ornament_motor.py', '--kaynak', a.kaynak, '--motor', a.motor, '--cikti', w / 'motor_onarimsiz', '--son', a.son, '--zemin', a.zemin,
                    '--cift', cift], env={'ORN_KENAR_ONARIM_KAPALI': '1'}, log_dosya=w / 'log_motor_onarimsiz.txt')
        log('onarimsiz motor', cift, 'cikis', k_on)
    for ad, k_ in KO.items():
        row = dict(cift=cift, kaynak=ad, n0=k_['n0'], degisen_piksel=k_['degisen_piksel'], alfa_farki_en_buyuk=k_['alfa_farki_en_buyuk'],
                   tur=k_['tur'], bilesen=k_['bilesen'], bilesen_sayisi=k_.get('bilesen_sayisi', 0), kenara_uzaklik=k_['kenara_uzaklik'],
                   kaynak_boyut=k_['boyut'], olcum=k_['olcum'], zayif_test=bool(k_['n0'] == 0))
        if ad in degisen:
            row['onarimsiz_motor_cikis'] = k_on
            yerler = ['sembol'] if ad == 'ana' else [y for y, b in (('kucuk_sol', b1), ('kucuk_sag', b2)) if b == ad]
            once_f, sonra_f = w / 'motor_onarimsiz' / f'{cift}_RUBY_954.png', O / f'{cift}_RUBY_954.png'
            row['yakin_954'] = {}
            if once_f.exists() and sonra_f.exists():
                on_ = np.asarray(Image.open(once_f).convert('RGB')); so_ = np.asarray(Image.open(sonra_f).convert('RGB'))
                for yer in yerler:
                    kb = M_['kutu'][yer]; sb = k_['sb']
                    fx = (kb[2] - kb[0]) / max(1, sb[2] - sb[0]); fy = (kb[3] - kb[1]) / max(1, sb[3] - sb[1])
                    X0, Y0, X1, Y1 = kb[0] - 8, kb[1] - 8, kb[2] + 8, kb[3] + 8
                    fark = np.abs(on_[Y0:Y1, X0:X1].astype(int) - so_[Y0:Y1, X0:X1].astype(int))
                    row['yakin_954'][yer] = dict(kutu=kb, esleme_olcek=[round(fx, 6), round(fy, 6)], ruby_farkli_piksel=int((fark > 0).any(-1).sum()),
                                                 ruby_en_buyuk_fark=int(fark.max()))
                    for ad_s, arr in (('once', on_), ('sonra', so_)):
                        cr = Image.fromarray(arr).crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * 4, (Y1 - Y0) * 4), Image.NEAREST); dr = ImageDraw.Draw(cr)
                        for b_ in k_['bilesen']:
                            x0 = kb[0] + (b_['x'] - sb[0]) * fx; y0 = kb[1] + (b_['y'] - sb[1]) * fy
                            x1 = kb[0] + (b_['x'] + b_['w'] - sb[0]) * fx; y1 = kb[1] + (b_['y'] + b_['h'] - sb[1]) * fy
                            dr.rectangle(((x0 - X0) * 4 - 2, (y0 - Y0) * 4 - 2, (x1 - X0) * 4 + 2, (y1 - Y0) * 4 + 2), outline=(0, 255, 255))
                        cr.save(DE / f'YAKIN_{cift}_{ad}_{ad_s}_954_4x.png')
            else:
                row['yakin_954'] = dict(eksik='onarimsiz ya da onarimli RUBY yok')
        KENAR.append(row)


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
    DE = Path(os.environ.get('ORNEK78_DRIVE_EK', str(O / '_drive_ek'))); DE.mkdir(parents=True, exist_ok=True)   # kaynak kirpimlari: YALNIZ Drive
    KENAR = []
    for cift in CIFTLER:
        w = W / cift; w.mkdir(exist_ok=True)
        log('cift', cift)
        k1 = kos([_d / 'ornament_motor.py', '--kaynak', a.kaynak, '--motor', a.motor, '--cikti', w / 'motor', '--son', a.son, '--zemin', a.zemin, '--cift', cift],
                 env={'ORN_YAKIN_DIR': str(DE)}, log_dosya=w / 'log_motor.txt')
        motor_png = all((w / 'motor' / f'{cift}_{s}_954.png').exists() for s in ('RUBY', 'SAPPHIRE', 'EMERALD'))
        mlog = (w / 'log_motor.txt').read_text() if (w / 'log_motor.txt').exists() else ''
        r = dict(cikis_kodlari=dict(motor=k1))
        if k1 == 2 or not motor_png:                                         # cokus ya da cikti yok: dump / sade / fildisi CALISMAZ
            tb = mlog[mlog.find('Traceback'):] if 'Traceback' in mlog else None
            fail = [l for l in mlog.splitlines() if 'FAIL' in l or 'DUR' in l]
            mo = json.loads((w / 'motor' / 'OLCUM.json').read_text()) if (w / 'motor' / 'OLCUM.json').exists() else None
            r.update(eksik=list(STIL), atlanan=['dump', 'sade', 'fildisi'], traceback=tb, hata_satiri=fail[-3:], log_kuyruk=mlog.splitlines()[-25:],
                     motor_olcum=mo, not_=('motor cokus (cikis 2), traceback asagida' if k1 == 2 else
                                           f'motor cikti uretmedi (cikis {k1}): ' + (fail[-1] if fail else 'neden logda yok')))
            R['cift'][cift] = r
            log('FAIL', cift, r['not_'])
            if tb:
                print(tb, flush=True)
            if cift == 'CANCER_LIBRA':
                (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str)); return 3
            continue
        k2 = kos([_d / 'ornament_motor.py', '--kaynak', a.kaynak, '--motor', a.motor, '--cikti', w / 'dump', '--son', a.son, '--cift', cift],
                 env={'ORN_DUMP': str(w / 'katman.pkl')}, log_dosya=w / 'log_dump.txt')
        k3 = kos([_d / 'ornament_sade.py', '--katman', w / 'katman.pkl', '--cikti', w / 'sade', '--cift', cift], log_dosya=w / 'log_sade.txt') if k2 == 0 else 9
        sade1 = w / 'sade' / 'SADE_1_ALTIN_TONU_954.png'                  # FILDISI girdisi: aday 1 (koyulastirilmamis; Serdar 4 Kas: diger stiller degismez)
        sadek = w / 'sade' / 'SADE_KOYU_954.png'                           # SADE ALTIN: kati kontrast >= 1.54 olana kadar koyulasmis (karar 2)
        k4 = kos([_d / 'ornament_fildisi.py', sade1, O / f'{cift}_FILDISI_954.png'], log_dosya=w / 'log_fildisi.txt') if sade1.exists() else 9
        for s in ('RUBY', 'SAPPHIRE', 'EMERALD'):
            shutil.copyfile(w / 'motor' / f'{cift}_{s}_954.png', O / f'{cift}_{s}_954.png')
        if sadek.exists():
            shutil.copyfile(sadek, O / f'{cift}_SADE_ALTIN_954.png')
        r['cikis_kodlari'] = dict(motor=k1, dump=k2, sade=k3, fildisi=k4)
        eksik = [s for s in STIL if not (O / f'{cift}_{s}_954.png').exists()]
        r['eksik'] = eksik
        if eksik:
            r['not_'] = 'eksik dosya: ' + ', '.join(eksik) + ' (dump / sade / fildisi loglari: ' + \
                        ' | '.join(((w / f).read_text().splitlines() or [''])[-1][:200] for f in ('log_dump.txt', 'log_sade.txt', 'log_fildisi.txt') if (w / f).exists()) + ')'
            R['cift'][cift] = r
            log('FAIL eksik', cift, r['not_'])
            if cift == 'CANCER_LIBRA':
                (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str)); return 3
            continue
        M_ = json.loads((w / 'motor' / 'OLCUM.json').read_text())
        S_all = json.loads((w / 'sade' / 'OLCUM.json').read_text()); S_ = S_all['aday']['1']; SK = S_all['sade_koyu']
        D = pickle.load(open(w / 'katman.pkl', 'rb'))
        _, yb, cak, ok = o4.kapi(D['E'])
        cv2 = __import__('cv2')
        ink = np.maximum.reduce([D['M'][k] for k in D['M'] if k != 'halka']) > 0.02     # halka haric (delikten gecer, muaf)
        uzak = {}
        for yk, ym in o4.YASAK.items():
            dd = cv2.distanceTransform((~ym.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
            uzak[yk] = round(float(dd[ink].min()), 1) if ink.any() else None
        SERT = dict({f'koyu_{k}': v for k, v in M_['kapi_sert'].items()}, **{f'sade1_{k}': bool(v) for k, v in S_['kapi'].items()},
                    **{f'sade_koyu_{k}': bool(v) for k, v in SK['kapi'].items()}, fildisi_cikis_0=bool(k4 == 0))                           # tek kaynak: motor kapi_sert + SADE_1 teknik kapi + fildisi cikisi
        r['not_'] = 'sert kapilar: ' + ('gecti' if all(SERT.values()) else 'FAIL ' + ', '.join(k for k, v in SERT.items() if not v))
        r.update(
            yerlesim=dict(maske_yasak_px=yb, maske_yasak_not_='o4.kapi oge maskesinden olcum (kapi sonucu motor kapi_sert goruntu_yasak_0)', cakisma=cak[:4], bosluk_px=M_['sonuc']['RUBY']['bosluk_px'], sembol_kutu=M_['kutu']['sembol'],
                          halka_kutu=M_['kutu']['halka'], kucuk_sol_kutu=M_['kutu']['kucuk_sol'], kucuk_sag_kutu=M_['kutu']['kucuk_sag'],
                          sembol_ust_y=M_['kutu']['sembol'][1], sembol_ust_y_cancer_libra=246, yasak_bolgeye_en_kisa_uzaklik_px=uzak,
                          yerlesim_bilgi=M_['yerlesim']),
            koyu={s: dict(kontrast_ortanca=M_['sonuc'][s]['kontrast_ortanca_en_kotu'], kati_koyu5_bilgi=M_['sonuc'][s]['kati_koyu5_en_kotu_bilgi'],
                          dE00_ham_maks=max(M_['sonuc'][s]['dE00_son_ham'].values()), goruntu_yasak=M_['sonuc'][s]['goruntu_yasak'],
                          halka_sureklilik_bilgi=M_['sonuc'][s]['halka_sureklilik']['oran'], kucuk_oge_artis=M_['sonuc'][s]['kucuk_oge_parlaklik_artisi'])
                  for s in ('RUBY', 'SAPPHIRE', 'EMERALD')},
            iou=M_['iou_954'], alfa_fark={k: v['ort_mutlak_fark_murekkep'] for k, v in M_['iou_954_bilgi'].items()},
            kapi=dict(sert=SERT, bilgi=dict(M_['kapi_bilgi'], sade1_okunur=S_['okunur'], sade1_sembol_ust_y=S_.get('sembol_ust_y_bilgi')),
                      kaynak='koyu: ornament_motor OLCUM kapi_sert / kapi_bilgi; sade1: ornament_sade OLCUM aday 1 kapi; fildisi: cikis kodu'),
            kaynak_leke=M_.get('kaynak_leke_onarim_sonrasi'), kaynak_kenar_onarim=M_.get('kaynak_kenar_onarim'),
            cikti_leke_a={s: sum(v['alfa_lt_09'] for k2, v in M_['sonuc'][s]['leke'].items() if k2 in o5.LEKE_KAPI_OGE) for s in ('RUBY', 'SAPPHIRE', 'EMERALD')},
            sade=dict(kati_kontrast=SK['kati_kontrast'], en_kotu_oge=SK['en_kotu_oge'], carpan_L=SK['carpan_L'], hedef=SK['hedef'],
                      koyulasma_oncesi_kati=S_['kati_kontrast_en_kotu'], aday1_ile_ayni=SK['aday1_ile_ayni'], gamut_kroma_kuculen_piksel=SK['gamut_kroma_kuculen_piksel'],
                      goruntu_yasak=S_['goruntu_yasak'], leke_a=S_['leke_a'], zemin_seffaf=S_['zemin_seffaf']),
            fildisi=dict(kontrast_bilgi=acik_kontrast(np.asarray(Image.open(O / f'{cift}_FILDISI_954.png').convert('RGB')), D),
                         merkez_istisna=2.53, merkez_not_='2.53 Merkez olcumu (yontem kayitli degil); bizim olcumde ortanca olcegine uyar, kati (en kotu) ayri',
                         yerlesim_yasak_px=yb, not_='fildisi girdisi aday 1 (koyulastirilmamis SADE) + krem zemin; yasak px yerlesimden'))
        R['cift'][cift] = r
        kenar_kayit(a, cift, w, M_, O, DE, KENAR)
        log(cift, 'yasak', yb, 'kontrast', {s: r['koyu'][s]['kontrast_ortanca'] for s in r['koyu']}, 'dE00', {s: r['koyu'][s]['dE00_ham_maks'] for s in r['koyu']},
            'sembol', r['yerlesim']['sembol_kutu'], 'uzaklik', uzak, 'sert FAIL', [k for k, v in SERT.items() if not v], 'cikis', r['cikis_kodlari'])
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
            if s == 'SADE_ALTIN':
                im = sinir_ciz(im)                                            # Serdar 4 Kas karar 3: beyaz sayfada dis cizgi ve delik
            liste.append(np.asarray(im.convert('RGB')))
            k = R['cift'][cift]
            v = (f'kontrast {k["koyu"][s]["kontrast_ortanca"]}, dE00 {k["koyu"][s]["dE00_ham_maks"]}' if s in k['koyu'] else
                 (f'kati {k["sade"]["kati_kontrast"]} (L x {k["sade"]["carpan_L"]})' if s == 'SADE_ALTIN' else
                  f'kati {k["fildisi"]["kontrast_bilgi"]["kati"]}, ortanca {k["fildisi"]["kontrast_bilgi"]["ortanca"]}'))
            et.append(f'{cift} / {s}\n{v}\nyasak px {sum(k["yerlesim"]["maske_yasak_px"].values())}')
        satir.append(son.onizleme_etiketli(liste, et, font, h_et=96))
    if satir:                                                                 # tum ciftler atlandiysa onizleme yok (OLCUM yine yazilir)
        Wd = max(x.width for x in satir)
        u = Image.new('RGB', (Wd, sum(x.height + 16 for x in satir)), 'white'); y = 0
        for x in satir:
            u.paste(x, (0, y)); y += x.height + 16
        u.save(RP / 'ONIZLEME_76mm_6CIFT.png', dpi=(300, 300))
    (RP / 'KENAR_ONARIM.json').write_text(json.dumps(dict(
        satirlar=KENAR, not_='her cift x kaynak (o5.kenar_onar cagrisi); n0 = 0 satirinda "degisen piksel 0" FAIL veremez: zayif test (KALITE 3). '
                            'Yakin planlar (kaynak 1:1 ve 954 4x) yalniz Drive.'), indent=1, ensure_ascii=False))
    R['gercek_boy'] = {}                                                       # gercek boy onizleme (300 dpi; KARAR 6). GV SADE tek gorsel (O2 kaniti) + liste
    if (O / 'GEMINI_VIRGO_SADE_ALTIN_954.png').exists():
        R['gercek_boy']['GEMINI_VIRGO_SADE'] = gercek_boy(O, 'GEMINI_VIRGO', ('SADE_ALTIN',), RP / 'GEMINI_VIRGO_SADE_GERCEK_BOY_300dpi.png')
    for c in [x for x in os.environ.get('GERCEK_BOY_CIFTLER', 'AQUARIUS_PISCES').split(',') if x]:
        R['gercek_boy'][c] = gercek_boy(O, c, ('SADE_ALTIN', 'RUBY', 'SAPPHIRE', 'EMERALD'), RP / f'GERCEK_BOY_{c}_SADE_3KOYU_300dpi.png')
    R['png_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.glob('*_954.png'))}
    fail = {c: v.get('not_') for c, v in R['cift'].items() if v.get('eksik') or not all((v.get('kapi') or {}).get('sert', {'x': False}).values())}
    cokus = [c for c, v in R['cift'].items() if 2 in (v.get('cikis_kodlari') or {}).values()]
    R['cikis'] = dict(kod=2 if cokus else (1 if fail else 0),
                      aciklama='0 tum ciftlerde sert kapilar gecti, 1 en az bir cift sert FAIL / eksik, 2 en az bir adim cokus (exception), 3 kontrol cifti DUR',
                      fail=fail, cokus_ciftler=cokus)
    (RP / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    log('BITTI', len(R['png_sha256']), 'PNG | cikis', R['cikis']['kod'], fail)
    return R['cikis']['kod']


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
