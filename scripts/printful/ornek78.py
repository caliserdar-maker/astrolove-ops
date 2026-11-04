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
KENAR_ZORUNLU = tuple(x for x in os.environ.get('ORNEK78_KENAR_ZORUNLU', '').split(',') if x)      # B: onarimsiz motorun nedeni leke olmali (sert)
ONAYLI_EK = dict(x.split('=', 1) for x in os.environ.get('ORNEK78_ONAYLI_EK', '').split(',') if '=' in x)   # E: CIFT=klasor (onayli 3 koyu stil kiyasi)
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
    kh = {k: v['deger_ham'] for k, v in ok.items() if v.get('deger_ham') is not None}
    oh = {k: v['ortanca_ham'] for k, v in ok.items() if v.get('ortanca_ham') is not None}
    return dict(kati=min(kk.values()), kati_en_kotu_oge=min(kk, key=kk.get), ortanca=min(oo.values()), oge=kk, oge_ortanca=oo,
                kati_ham=min(kh.values()), ortanca_ham=min(oh.values()))


def sade_kontrast(S_):
    """SADE_ALTIN (= SADE_1, O2 b: koyulastirma yok) kati / ortanca: ornament_sade aday 1 kontrast sozlugu (bilgi ogeleri haric), ham ve yuvarlanmis."""
    ok = {k: v for k, v in S_['kontrast'].items() if not k.endswith('_bilgi') and v.get('deger') is not None}
    kh = {k: v['deger_ham'] for k, v in ok.items()}                          # ham alan zorunlu (yoksa KeyError: sessiz yuvarlanmis deger yok)
    oh = {k: v['ortanca_ham'] for k, v in ok.items()}
    en = min(kh, key=kh.get)
    return dict(kati=round(kh[en], 2), kati_ham=kh[en], en_kotu_oge=en, ortanca=round(min(oh.values()), 2), ortanca_ham=min(oh.values()))


DUZEY = dict(SADE_ALTIN=dict(kati=1.54, ortanca=None, kaynak='3 Kas CL SADE kati 1,54 olcumu (O2 b karari listesi; sert kapi degil)'),
             FILDISI=dict(kati=1.31, ortanca=2.48, kaynak='ORNAMENT_KARAR 24 onayli istisna duzeyi CL kati 1,31 / ortanca 2,48 (O4 a)'))


def dusuk_kontrast_liste(ciftler):
    """O2 + O4 (bilgi, sert kapi degil): ham deger duzeyin altindaysa (kati YA DA ortanca; SADE yalniz kati) satir. Girdi {cift: {stil: {kati_ham,
    ortanca_ham, kati, ortanca, en_kotu_oge}}}. CANCER_LIBRA degerleri ayri bilgi alani (duzeyi degistirmez)."""
    L = {s: [] for s in DUZEY}
    cl = {}
    for c, st in ciftler.items():
        for s, d in DUZEY.items():
            v = st.get(s)
            if not v:
                continue
            if c == 'CANCER_LIBRA':
                cl[s] = dict(kati_ham=v['kati_ham'], ortanca_ham=v['ortanca_ham'])
            alt = v['kati_ham'] < d['kati'] or (d['ortanca'] is not None and v['ortanca_ham'] < d['ortanca'])
            if alt:
                L[s].append(dict(cift=c, stil=s, kati=v['kati'], ortanca=v['ortanca'], kati_ham=round(v['kati_ham'], 4), ortanca_ham=round(v['ortanca_ham'], 4),
                                 en_kotu_oge=v['en_kotu_oge'], duzey=dict(kati=d['kati'], ortanca=d['ortanca']), duzey_kaynak=d['kaynak']))
    return dict(liste=L, cancer_libra_bu_kosu_bilgi=cl, not_='bilgi; FILDISI listesindeki ciftler 78 sonrasi Serdar goz onayina (O4 a)')


def dusuk_kontrast_girdi(cift):
    """R['cift'] -> dusuk_kontrast_liste girdisi (SADE: sade.kati_kontrast / ortanca / *_ham / en_kotu_oge; FILDISI: fildisi.kontrast_bilgi)."""
    out = {}
    for c, v in cift.items():
        if not (v.get('sade') and v.get('fildisi')):
            continue
        sd, fk = v['sade'], v['fildisi']['kontrast_bilgi']
        out[c] = dict(SADE_ALTIN=dict(kati=sd['kati_kontrast'], ortanca=sd['ortanca'], kati_ham=sd['kati_ham'], ortanca_ham=sd['ortanca_ham'],
                                      en_kotu_oge=sd['en_kotu_oge']),
                      FILDISI=dict(kati=fk['kati'], ortanca=fk['ortanca'], kati_ham=fk['kati_ham'], ortanca_ham=fk['ortanca_ham'],
                                   en_kotu_oge=fk['kati_en_kotu_oge']))
    return out


def onarimsiz_neden(k_on, mo, burclar):
    """B (O1): onarimsiz motor beklenen FAIL'i: cikis 1 VE kapi_sert.leke_a_kaynak_0 False VE cikis.fail icinde leke_a_kaynak_0 VE
    kaynak_leke_onarim_sonrasi[burc] > 0 (onarilan kaynaklardan en az biri). Doner (gecti, neden)."""
    if k_on is None:
        return False, 'onarimsiz motor kosmadi'
    if k_on != 1:
        return False, f'onarimsiz motor cikis {k_on} (1 beklenir)'
    if not mo:
        return False, 'onarimsiz OLCUM yok'
    ks = mo.get('kapi_sert') or {}
    fl = (mo.get('cikis') or {}).get('fail') or []
    kl = mo.get('kaynak_leke_onarim_sonrasi') or {}
    if ks.get('leke_a_kaynak_0') is not False:
        return False, 'kapi_sert.leke_a_kaynak_0 False degil'
    if 'leke_a_kaynak_0' not in fl:
        return False, f'cikis.fail leke_a_kaynak_0 icermiyor: {fl}'
    if not any((kl.get(b) or 0) > 0 for b in burclar):
        return False, f'kaynak_leke_onarim_sonrasi {burclar} > 0 degil: {kl}'
    if fl != ['leke_a_kaynak_0']:                                            # F 4 Kas: tek neden (sikilastirma); baska sert FAIL varsa beklenen FAIL degil
        return False, f'baska sert FAIL de var: {fl}'
    return True, 'tek neden leke_a_kaynak_0 (' + ', '.join(f'{b} {kl.get(b)}' for b in burclar) + ' px)'


def kenar_kayit(a, cift, w, M_, O, DE, KENAR, r, RP, UYARI):
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
        for src, dst in ((w / 'log_motor_onarimsiz.txt', RP / f'log_motor_onarimsiz_{cift}.txt'), (w / 'motor_onarimsiz' / 'OLCUM.json', RP / f'OLCUM_onarimsiz_{cift}.json')):
            if src.exists():
                shutil.copyfile(src, dst)
    for ad in degisen:                                                       # C: kenar onarimi gorunur (uyari, FAIL degil)
        k_ = KO[ad]
        u = dict(cift=cift, kaynak=ad, degisen_piksel=k_['degisen_piksel'], alfa_farki_en_buyuk=k_['alfa_farki_en_buyuk'])
        UYARI.append(u)
        print(f"::warning::kenar onarimi {cift} {ad}: degisen piksel {u['degisen_piksel']}, en buyuk alfa farki {u['alfa_farki_en_buyuk']}", flush=True)
    if cift in KENAR_ZORUNLU:                                                # B: onarimsiz motorun beklenen FAIL'i, nedeni kaynak lekesi (sert)
        mo = json.loads((w / 'motor_onarimsiz' / 'OLCUM.json').read_text()) if (w / 'motor_onarimsiz' / 'OLCUM.json').exists() else None
        ok_, neden = onarimsiz_neden(k_on, mo, degisen)
        r['kapi']['sert']['kenar_onarimsiz_neden_leke'] = bool(ok_)
        r['kenar_onarimsiz_neden'] = dict(gecti=bool(ok_), neden=neden, onarimsiz_motor_cikis=k_on, onarilan_kaynak=degisen)
        SERT = r['kapi']['sert']
        r['not_'] = 'sert kapilar: ' + ('gecti' if all(SERT.values()) else 'FAIL ' + ', '.join(k for k, v in SERT.items() if not v))
        log('onarimsiz neden', cift, ok_, neden)
    for ad, k_ in KO.items():
        row = dict(cift=cift, kaynak=ad, n0=k_['n0'], degisen_piksel=k_['degisen_piksel'], alfa_farki_en_buyuk=k_['alfa_farki_en_buyuk'],
                   tur=k_['tur'], bilesen=k_['bilesen'], bilesen_sayisi=k_.get('bilesen_sayisi', 0), kenara_uzaklik=k_['kenara_uzaklik'],
                   kaynak_boyut=k_['boyut'], olcum=k_['olcum'], zayif_test=bool(k_['n0'] == 0))
        if ad in degisen:
            row['onarimsiz_motor_cikis'] = k_on
            yerler = ['sembol'] if ad == 'ana' else [y for y, b in (('kucuk_sol', b1), ('kucuk_sag', b2)) if b == ad]
            row['yakin_954'] = {}
            row['yakin_954_yapilmadi'] = dict(SADE_ALTIN='yapilmadi: onarimsiz motor ORN_DUMP / ornament_sade kosmaz, onarimsiz SADE katmani yok',
                                              FILDISI='yapilmadi: girdisi onarimsiz SADE_1, uretilmedi')
            for stl in ('RUBY', 'SAPPHIRE', 'EMERALD'):
              once_f, sonra_f = w / 'motor_onarimsiz' / f'{cift}_{stl}_954.png', O / f'{cift}_{stl}_954.png'
              if once_f.exists() and sonra_f.exists():
                on_ = np.asarray(Image.open(once_f).convert('RGB')); so_ = np.asarray(Image.open(sonra_f).convert('RGB'))
                for yer in yerler:
                    kb = M_['kutu'][yer]; sb = k_['sb']
                    fx = (kb[2] - kb[0]) / max(1, sb[2] - sb[0]); fy = (kb[3] - kb[1]) / max(1, sb[3] - sb[1])
                    X0, Y0, X1, Y1 = kb[0] - 8, kb[1] - 8, kb[2] + 8, kb[3] + 8
                    fark = np.abs(on_[Y0:Y1, X0:X1].astype(int) - so_[Y0:Y1, X0:X1].astype(int))
                    row['yakin_954'][f'{stl}/{yer}'] = dict(kutu=kb, esleme_olcek=[round(fx, 6), round(fy, 6)], farkli_piksel=int((fark > 0).any(-1).sum()),
                                                            en_buyuk_fark=int(fark.max()))
                    for ad_s, arr in (('once', on_), ('sonra', so_)):
                        cr = Image.fromarray(arr).crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * 4, (Y1 - Y0) * 4), Image.NEAREST); dr = ImageDraw.Draw(cr)
                        for b_ in k_['bilesen']:
                            x0 = kb[0] + (b_['x'] - sb[0]) * fx; y0 = kb[1] + (b_['y'] - sb[1]) * fy
                            x1 = kb[0] + (b_['x'] + b_['w'] - sb[0]) * fx; y1 = kb[1] + (b_['y'] + b_['h'] - sb[1]) * fy
                            dr.rectangle(((x0 - X0) * 4 - 2, (y0 - Y0) * 4 - 2, (x1 - X0) * 4 + 2, (y1 - Y0) * 4 + 2), outline=(0, 255, 255))
                        cr.save(DE / f'YAKIN_{cift}_{ad}_{stl}_{ad_s}_954_4x.png')
              else:
                row['yakin_954'][stl] = dict(eksik=f'onarimsiz ya da onarimli {stl} yok')
        KENAR.append(row)


def onayli_kiyas(O, cift, klasor, stiller=('RUBY', 'SAPPHIRE', 'EMERALD')):
    """onayli dosyalara ham piksel kiyasi (CL kontrolu ile ayni tolerans: en buyuk fark <= 1 seviye ve farkli piksel <= 10); eksik dosya FAIL."""
    R_ = {}
    for s_ in stiller:
        f_ = Path(klasor) / f'{cift}_{s_}_954.png'; g_ = Path(O) / f'{cift}_{s_}_954.png'
        if not (f_.exists() and g_.exists()):
            R_[s_] = dict(eksik=[str(x) for x in (f_, g_) if not x.exists()], tolerans_icinde=False); continue
        u = np.asarray(Image.open(g_)); on = np.asarray(Image.open(f_))
        ay = u.shape == on.shape
        fk = int(np.abs(u.astype(int) - on.astype(int)).max()) if ay else None; nn = int((u != on).any(-1).sum()) if ay else None
        R_[s_] = dict(en_buyuk_fark=fk, farkli_piksel=nn, tolerans_icinde=bool(ay and fk <= TOL_SEVIYE and nn <= TOL_PIKSEL),
                      onayli_sha256=hashlib.sha256(f_.read_bytes()).hexdigest())
    return R_


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
    KENAR, UYARI = [], []
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
        sade1 = w / 'sade' / 'SADE_1_ALTIN_TONU_954.png'                  # O2 b (Serdar 4 Kas): SADE ALTIN = aday 1, koyulastirma yok; FILDISI girdisi ayni dosya
        k4 = kos([_d / 'ornament_fildisi.py', sade1, O / f'{cift}_FILDISI_954.png'], log_dosya=w / 'log_fildisi.txt') if sade1.exists() else 9
        for s in ('RUBY', 'SAPPHIRE', 'EMERALD'):
            shutil.copyfile(w / 'motor' / f'{cift}_{s}_954.png', O / f'{cift}_{s}_954.png')
        if sade1.exists():
            shutil.copyfile(sade1, O / f'{cift}_SADE_ALTIN_954.png')
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
        S_all = json.loads((w / 'sade' / 'OLCUM.json').read_text()); S_ = S_all['aday']['1']; SKK = sade_kontrast(S_)
        D = pickle.load(open(w / 'katman.pkl', 'rb'))
        _, yb, cak, ok = o4.kapi(D['E'])
        cv2 = __import__('cv2')
        ink = np.maximum.reduce([D['M'][k] for k in D['M'] if k != 'halka']) > 0.02     # halka haric (delikten gecer, muaf)
        uzak = {}
        for yk, ym in o4.YASAK.items():
            dd = cv2.distanceTransform((~ym.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
            uzak[yk] = round(float(dd[ink].min()), 1) if ink.any() else None
        SERT = dict({f'koyu_{k}': v for k, v in M_['kapi_sert'].items()}, **{f'sade1_{k}': bool(v) for k, v in S_['kapi'].items()},
                    fildisi_cikis_0=bool(k4 == 0))                           # tek kaynak: motor kapi_sert + SADE_1 teknik kapi + fildisi cikisi
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
            sade=dict(kati_kontrast=SKK['kati'], kati_ham=SKK['kati_ham'], ortanca=SKK['ortanca'], ortanca_ham=SKK['ortanca_ham'], en_kotu_oge=SKK['en_kotu_oge'],
                      dosya='SADE_1_ALTIN_TONU_954.png (O2 b: koyulastirma yok)', sade1_sha256=hashlib.sha256(sade1.read_bytes()).hexdigest(),
                      goruntu_yasak=S_['goruntu_yasak'], leke_a=S_['leke_a'], zemin_seffaf=S_['zemin_seffaf']),
            fildisi=dict(kontrast_bilgi=acik_kontrast(np.asarray(Image.open(O / f'{cift}_FILDISI_954.png').convert('RGB')), D),
                         duzey=DUZEY['FILDISI'], girdi_sha256=hashlib.sha256(sade1.read_bytes()).hexdigest(),
                         yerlesim_yasak_px=yb, not_='fildisi girdisi aday 1 (koyulastirilmamis SADE) + krem zemin; yasak px yerlesimden'))
        R['cift'][cift] = r
        kenar_kayit(a, cift, w, M_, O, DE, KENAR, r, RP, UYARI)
        r['kucultme'] = M_.get('kucultme')
        if cift in ONAYLI_EK:                                                # E: onayli Kova 3 koyu stil kiyasi (sert; CL kontrolu ile ayni tolerans)
            r['onayli_kiyas'] = onayli_kiyas(O, cift, ONAYLI_EK[cift])
            for s_, v_ in r['onayli_kiyas'].items():
                r['kapi']['sert'][f'onayli_kiyas_{s_}'] = v_['tolerans_icinde']
                log('ONAYLI KIYAS', cift, s_, v_.get('en_buyuk_fark'), v_.get('farkli_piksel'), 'PASS' if v_['tolerans_icinde'] else 'FAIL')
            SERT_ = r['kapi']['sert']
            r['not_'] = 'sert kapilar: ' + ('gecti' if all(SERT_.values()) else 'FAIL ' + ', '.join(k for k, v in SERT_.items() if not v))
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
                 (f'kati {k["sade"]["kati_kontrast"]}, ortanca {k["sade"]["ortanca"]}' if s == 'SADE_ALTIN' else
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
    R['kenar_onarim_uyari'] = UYARI if UYARI else 'kenar onarimi yok'
    R['kucultme'] = []                                                       # O3 a: her cift toplam kucultme (motor OLCUM); sinir FAIL ya da sigmayan cift Serdar'a
    for c, v in R['cift'].items():
        ku = v.get('kucultme') or {}
        mo = v.get('motor_olcum') or {}
        if mo.get('hata') == 'yerlesim_V5':
            R['kucultme'].append(dict(cift=c, sigmadi=True, not_='sembol sigmadi, gorsel yok (Serdar\'a bildirilir)', iz=(mo.get('kutu') or {}).get('kucultme_iz')))
            print(f'::warning::{c}: sembol sigmadi, gorsel yok (Serdar onayi)', flush=True)
        elif ku:
            gec = bool(ku['toplam_px'] <= ku['sinir_px'])
            R['kucultme'].append(dict(cift=c, toplam_px=ku['toplam_px'], sinir_px=ku['sinir_px'], sinir_kaynak=ku['sinir_kaynak'], iz=ku['iz'], sinir_gecti=gec))
            if not gec:
                print(f"::warning::{c}: kucultme {ku['toplam_px']} px > sinir {ku['sinir_px']} px, is durur, gorsel Serdar'a", flush=True)
    R['dusuk_kontrast'] = dusuk_kontrast_liste(dusuk_kontrast_girdi(R['cift']))
    R['gercek_boy'] = {}                                                       # gercek boy onizleme 5 stil (300 dpi; KARAR 6): liste + kucultme siniri FAIL ciftleri
    gb_c = [x for x in os.environ.get('GERCEK_BOY_CIFTLER', 'AQUARIUS_PISCES').split(',') if x]
    gb_c += [k['cift'] for k in R['kucultme'] if k.get('sinir_gecti') is False and k['cift'] not in gb_c]
    for c in gb_c:
        R['gercek_boy'][c] = gercek_boy(O, c, STIL, RP / f'GERCEK_BOY_{c}_5STIL_300dpi.png')
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
