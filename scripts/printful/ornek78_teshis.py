#!/usr/bin/env python3
"""ORNAMENT_78_ORNEK6 TESHIS (Merkez / Serdar 3 Kas; deneme SAYILMAZ, uretim yok, Drive'a PNG yazilmaz).
1 GEMINI_VIRGO: ornament_motor.py tam log + traceback + (FAIL ise) motorun yazdigi hata OLCUM'u; kaynak olculeri (ana / burc murekkep kutusu).
2 ARIES_ARIES: ORN_DUMP + ornament_sade.py (SADE adimi) log + olcum.
3 Kaynak leke (aquarius): kucuk burc zinciri (kirp pad 2 + delik_kapat + leke_ic_kaynak, ornament_motor ile ayni) -> alfa < 0.9 ic pikseller:
  sayi, bilesenler (kutu, merkez, alan), kaynak koordinati; AQUARIUS_PISCES motor ciktisinda (RUBY 954) ayni yer (murekkep kutusu orani ile esleme)
  ve ciktidaki leke olcusu (motor leke alfa_lt_09, kucuk_sol). Kirpimlar: LEKE_AQUARIUS_KAYNAK.png (kaynak, leke kirmizi), LEKE_AQUARIUS_CIKTI_8x.png.
  Kaynak dosyaya DOKUNULMAZ.
Kullanim: ornek78_teshis.py --kaynak K --motor MD --zemin ZE --cikti DIR"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o1 = al.o5, al.o1
PY = sys.executable


def kos(arg, env=None, log_dosya=None):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run([PY, '-I'] + [str(x) for x in arg], env=e, capture_output=True, text=True)
    t = r.stdout + r.stderr
    if log_dosya:
        Path(log_dosya).write_text(t)
    return r.returncode, t


def murekkep(f):
    g = np.asarray(Image.open(f).convert('RGBA'))
    b = o1.bbox(g[..., 3].astype(np.float32) / 255, 0.5)
    return dict(boyut=list(g.shape[:2]), murekkep_kutu=list(b), murekkep_w=b[2] - b[0], murekkep_h=b[3] - b[1])


def main():
    ap = argparse.ArgumentParser()
    for k in ('kaynak', 'motor', 'zemin', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True); W = Path('/tmp/teshis_is'); W.mkdir(exist_ok=True)
    K = Path(a.kaynak); son = '/tmp/son_yok'; Path(son).mkdir(exist_ok=True)
    T = {}
    import traceback as _tb
    if os.environ.get('TESHIS_GV_YD') == '1':                              # Merkez / Serdar 5 Kas: GV yeni duzen dE00 nedeni (yalniz olcum)
        try:
            bolum_gv_yd(a, K, W, O, son, T)
        except Exception:                                                      # noqa: BLE001
            T['gv_yd_hata'] = _tb.format_exc(); print(T['gv_yd_hata'], flush=True)
        (O / 'TESHIS.json').write_text(json.dumps(T, indent=1, ensure_ascii=False, default=str))
        print('TESHIS bitti', flush=True)
        return 0
    if os.environ.get('TESHIS_YALNIZ_LEKE') != '1':
        try:
            bolum12(a, K, W, O, son, T)
        except Exception:                                                      # noqa: BLE001
            T['bolum12_hata'] = _tb.format_exc(); print(T['bolum12_hata'], flush=True)
    try:
        bolum3(a, K, W, O, son, T)
    except Exception:                                                          # noqa: BLE001
        T['bolum3_hata'] = _tb.format_exc(); print(T['bolum3_hata'], flush=True)
    (O / 'TESHIS.json').write_text(json.dumps(T, indent=1, ensure_ascii=False, default=str))
    print('TESHIS bitti', flush=True)
    return 0


OGE_TABLO = ('dE00_butunlesme_oncesi', 'dE00_son_ham', 'dE00_son_dusus_bolunmus_bilgi', 'L_dagilim_bilgi', 'sembol_kutu', 'kontrast_ortanca_en_kotu')


def bolum_gv_yd(a, K, W, O, son, T):
    """GEMINI_VIRGO: motor eski (YENI_DUZEN=0) ve yeni (YENI_DUZEN=1) duzende; oge basina dE00 tablolari (butunlesme oncesi, son ham,
    dusus bolunmus), L dagilimi, renk_uyum satiri (log), sembol kutusu. Yalniz sayi: PNG dala yazilmaz (is akisi kapisi)."""
    for mod in ('0', '1'):
        ad = f'gv_yd{mod}'
        k, t = kos([_d / 'ornament_motor.py', '--kaynak', K, '--motor', a.motor, '--cikti', W / ad, '--son', son, '--zemin', a.zemin, '--cift', 'GEMINI_VIRGO'],
                   env={'YENI_DUZEN': mod}, log_dosya=O / f'log_motor_GEMINI_VIRGO_YD{mod}.txt')
        f = W / ad / 'OLCUM.json'
        mo = json.loads(f.read_text()) if f.exists() else {}
        son_ = mo.get('sonuc') or {}
        T[f'GEMINI_VIRGO_YD{mod}'] = dict(
            cikis=k, traceback=t[t.find('Traceback'):] if 'Traceback' in t else None,
            renk_uyum_log=[x for x in t.splitlines() if 'renk_uyum' in x][:3],
            sert_fail=[x for x in t.splitlines() if 'FAIL' in x][:10],
            kapi_sert=mo.get('kapi_sert'), sembol_kutu=(mo.get('kutu') or {}).get('sembol'),
            oge={r: {kk: son_[r].get(kk) for kk in OGE_TABLO} for r in ('RUBY', 'SAPPHIRE', 'EMERALD') if r in son_})
        print('GV YD', mod, 'cikis', k, json.dumps({r: (v or {}).get('dE00_son_ham') for r, v in T[f'GEMINI_VIRGO_YD{mod}']['oge'].items()}), flush=True)


def bolum12(a, K, W, O, son, T):
    # 1 GEMINI_VIRGO
    k, t = kos([_d / 'ornament_motor.py', '--kaynak', K, '--motor', a.motor, '--cikti', W / 'gv', '--son', son, '--zemin', a.zemin, '--cift', 'GEMINI_VIRGO'],
               log_dosya=O / 'log_motor_GEMINI_VIRGO.txt')
    mo = json.loads((W / 'gv' / 'OLCUM.json').read_text()) if (W / 'gv' / 'OLCUM.json').exists() else None
    T['GEMINI_VIRGO'] = dict(cikis=k, traceback=t[t.find('Traceback'):] if 'Traceback' in t else None,
                             fail_satirlari=[l for l in t.splitlines() if 'FAIL' in l or 'DUR' in l][-5:], log_kuyruk=t.splitlines()[-30:],
                             motor_olcum=(mo if (mo or {}).get('hata') else (dict(kapi_sert=mo.get('kapi_sert'), kapi_bilgi=mo.get('kapi_bilgi')) if mo else None)),
                             kaynak=dict(ana=murekkep(K / 'GEMINI_VIRGO_ana.png'), gemini=murekkep(K / 'gemini_symbol_gold.png'),
                                         virgo=murekkep(K / 'virgo_symbol_gold.png')))
    print('GEMINI_VIRGO cikis', k, T['GEMINI_VIRGO']['fail_satirlari'], flush=True)
    if T['GEMINI_VIRGO']['traceback']:
        print(T['GEMINI_VIRGO']['traceback'], flush=True)
    # 2 ARIES_ARIES SADE adimi
    k2, t2 = kos([_d / 'ornament_motor.py', '--kaynak', K, '--motor', a.motor, '--cikti', W / 'aa_dump', '--son', son, '--cift', 'ARIES_ARIES'],
                 env={'ORN_DUMP': str(W / 'aa.pkl')}, log_dosya=O / 'log_dump_ARIES_ARIES.txt')
    k3, t3 = kos([_d / 'ornament_sade.py', '--katman', W / 'aa.pkl', '--cikti', W / 'aa_sade', '--cift', 'ARIES_ARIES'], log_dosya=O / 'log_sade_ARIES_ARIES.txt') if k2 == 0 else (9, '')
    so = json.loads((W / 'aa_sade' / 'OLCUM.json').read_text())['aday']['1'] if (W / 'aa_sade' / 'OLCUM.json').exists() else None
    T['ARIES_ARIES_SADE'] = dict(dump_cikis=k2, sade_cikis=k3, traceback=(t2 + t3)[(t2 + t3).find('Traceback'):] if 'Traceback' in (t2 + t3) else None,
                                 sade_kuyruk=t3.splitlines()[-4:], sade_olcum=dict(kati=so['kati_kontrast_en_kotu'], yasak=so['goruntu_yasak'],
                                                                                    leke_a=so['leke_a'], zemin_seffaf=so['zemin_seffaf'], kapi=so['kapi']) if so else None)
    print('ARIES_ARIES sade', k2, k3, flush=True)


def bolum3(a, K, W, O, son, T):
    # 3 aquarius kaynak leke
    g = np.asarray(Image.open(K / 'aquarius_symbol_gold.png').convert('RGBA'), np.float32); g[..., 3] /= 255.0
    g = o1.kirp(g, g[..., 3], pad=2)
    g, _ = o5.delik_kapat(g)
    ic, _ = o5.leke_ic_kaynak(g[..., 3])
    lk = ic & (g[..., 3] < 0.9)
    n, lab, st, cen = cv2.connectedComponentsWithStats(lk.astype(np.uint8), 8)
    bil = [dict(kutu=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])], alan=int(st[i, 4]),
                merkez=[round(float(cen[i, 0]), 1), round(float(cen[i, 1]), 1)]) for i in range(1, n)]
    bil.sort(key=lambda x: -x['alan'])
    ys, xs = np.nonzero(lk)
    sb = o1.bbox(g[..., 3], 0.5)
    T['AQUARIUS_KAYNAK_LEKE'] = dict(piksel=int(lk.sum()), kaynak_kirpim_boyut=list(g.shape[:2]), kaynak_murekkep_kutu=list(sb),
                                     leke_kutu=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                                     bilesen_sayisi=n - 1, bilesenler=bil[:20], koordinat_ornek=[[int(x), int(y)] for x, y in list(zip(xs, ys))[::max(1, len(xs) // 40)]],
                                     alfa_degerleri=dict(min=round(float(g[..., 3][lk].min()), 3), ortanca=round(float(np.median(g[..., 3][lk])), 3)) if len(xs) else None,
                                     not_='koordinatlar kirp(pad 2) + delik_kapat sonrasi kaynak cercevesinde (ornament_motor kucuk() ile ayni)')
    # kaynak kirpim: leke kutusu +%15 pay, gri zemin, leke kirmizi
    if len(xs):
        x0, y0, x1, y1 = T['AQUARIUS_KAYNAK_LEKE']['leke_kutu']; p = int(0.15 * max(x1 - x0, y1 - y0)) + 8
        x0, y0, x1, y1 = max(0, x0 - p), max(0, y0 - p), min(g.shape[1], x1 + p), min(g.shape[0], y1 + p)
        cr = g[y0:y1, x0:x1]; zem = np.array([60, 60, 66], np.float32)
        rgb = cr[..., :3] * cr[..., 3:] + zem * (1 - cr[..., 3:])
        rgb2 = rgb.copy(); rgb2[lk[y0:y1, x0:x1]] = [255, 0, 0]
        im = np.concatenate([rgb, np.full((rgb.shape[0], 8, 3), 255, np.float32), rgb2], 1)
        im = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
        s_ = max(1, int(600 / max(im.size)))
        im = im.resize((im.width * s_, im.height * s_), Image.NEAREST) if s_ > 1 else im
        im.save(O / 'LEKE_AQUARIUS_KAYNAK.png')
        T['AQUARIUS_KAYNAK_LEKE']['kaynak_kirpim'] = dict(dosya='LEKE_AQUARIUS_KAYNAK.png', bolge=[x0, y0, x1, y1], buyutme=s_,
                                                          not_='sol kaynak, sag ayni yer leke pikselleri kirmizi')
    # cikti: AQUARIUS_PISCES motor (RUBY)
    if os.environ.get('TESHIS_YALNIZ_LEKE') == '1' and (W / 'ap' / 'OLCUM.json').exists():
        k4 = 'onceki'
    else:
        k4, t4 = kos([_d / 'ornament_motor.py', '--kaynak', K, '--motor', a.motor, '--cikti', W / 'ap', '--son', son, '--zemin', a.zemin, '--cift', 'AQUARIUS_PISCES'],
                     log_dosya=O / 'log_motor_AQUARIUS_PISCES.txt')
    mp = json.loads((W / 'ap' / 'OLCUM.json').read_text()) if (W / 'ap' / 'OLCUM.json').exists() else {}
    if (W / 'ap' / 'AQUARIUS_PISCES_RUBY_954.png').exists() and len(xs):
        kb = mp['kutu']['kucuk_sol']
        out = np.asarray(Image.open(W / 'ap' / 'AQUARIUS_PISCES_RUBY_954.png').convert('RGB'))
        # esleme: kaynak murekkep kutusu (alfa > 0.5) -> cikti kucuk_sol kutusu (dogrusal, oran)
        fx = (kb[2] - kb[0]) / (sb[2] - sb[0]); fy = (kb[3] - kb[1]) / (sb[3] - sb[1])
        nok = [(kb[0] + (b_['merkez'][0] - sb[0]) * fx, kb[1] + (b_['merkez'][1] - sb[1]) * fy, b_['alan']) for b_ in bil[:20]]
        X0, Y0, X1, Y1 = kb[0] - 6, kb[1] - 6, kb[2] + 6, kb[3] + 6
        cr = Image.fromarray(out).crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * 8, (Y1 - Y0) * 8), Image.NEAREST)
        dr = ImageDraw.Draw(cr)
        for x, y, ar in nok:
            r_ = max(4, int(8 * (ar * fx * fy) ** 0.5))
            dr.ellipse(((x - X0) * 8 - r_, (y - Y0) * 8 - r_, (x - X0) * 8 + r_, (y - Y0) * 8 + r_), outline=(0, 255, 255), width=2)
        cr.save(O / 'LEKE_AQUARIUS_CIKTI_8x.png')
        lk_out = {r: mp['sonuc'][r]['leke'].get('kucuk_sol') for r in ('RUBY', 'SAPPHIRE', 'EMERALD')}
        T['AQUARIUS_CIKTI'] = dict(motor_cikis=k4, kucuk_sol_kutu=kb, esleme_olcek=[round(fx, 5), round(fy, 5)],
                                   leke_noktalari_954=[[round(x, 1), round(y, 1)] for x, y, _ in nok], cikti_leke_kucuk_sol=lk_out,
                                   kirpim=dict(dosya='LEKE_AQUARIUS_CIKTI_8x.png', bolge=[X0, Y0, X1, Y1], buyutme=8,
                                               not_='AQUARIUS_PISCES RUBY 954; camgobegi daire = kaynak leke bileseninin ciktidaki yeri'),
                                   kapi_sert=mp.get('kapi_sert'))


if __name__ == '__main__':
    sys.exit(main())
