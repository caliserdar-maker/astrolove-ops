#!/usr/bin/env python3
"""Ornament 78 uretim (ornament-78-uretim.yml, uretim78.py, ornek78 PARCA modu) YEREL mantik testleri (Serdar 4 Kas, 1. kisim D/G).
Motor girdisi yalniz Actions'ta; sahte veri. Her vaka bilinen PASS + bilinen FAIL. Cikis 0 hepsi beklendigi gibi, 1 degil, 2 cokus.
Kullanim: uretim78_mantik_testi.py --cikti DIR [--kfake_kova PNG --motor_kenar JSON] [--ornek78_hizli]
  --ornek78_hizli: ornek78 alt surec vakalari (ilk cift CL degilse 4; cift dayanikliligi) da kosar (her biri ~10-30 sn)."""
import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw

_d = Path(__file__).resolve().parent
_k = _d.parent.parent


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cikti', required=True); ap.add_argument('--kfake_kova'); ap.add_argument('--motor_kenar')
    ap.add_argument('--ornek78_hizli', action='store_true')
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    u = yukle('u78', 'uretim78.py'); bk = yukle('bk', 'uretim78_beklenen.py')
    V = []

    def vaka(grup, ad, beklenen, f):
        try:
            sonuc = f()
        except Exception as e:                                                # noqa: BLE001
            sonuc = f'HATA {type(e).__name__}: {str(e)[:120]}'
        g = (sonuc == beklenen) if not (isinstance(beklenen, str) and beklenen.startswith('HATA')) else str(sonuc).startswith(beklenen)
        V.append(dict(grup=grup, vaka=ad, beklenen=beklenen, sonuc=sonuc, gecti=bool(g)))

    J = json.loads((_k / 'docs/ornament/URETIM78_CIFTLER.json').read_text())
    # 1 parca listesi
    Po = u.parcalar(J, 'ornek'); P7 = u.parcalar(J, '78')
    vaka('parca', 'ornek: 2 parca x 4, CL ilk', [2, [5, 5], ['CANCER_LIBRA'] * 2],
         lambda: [Po['parca_sayisi'], [len(p['ciftler']) for p in Po['parcalar']], [p['ciftler'][0] for p in Po['parcalar']]])
    vaka('parca', 'ornek 8 cift yerlesim78 listesinde', True, lambda: all(c in u.CIFT78 for p in Po['parcalar'] for c in p['uretim']))
    tum = [c for p in P7['parcalar'] for c in p['uretim']]
    vaka('parca', "78: 75 cift, tekil, CL / AQU_PIS / GV yok, CL her parcada ilk", [75, 75, False, True],
         lambda: [len(tum), len(set(tum)), any(c in tum for c in u.ONAYLI), all(p['ciftler'][0] == 'CANCER_LIBRA' for p in P7['parcalar'])])
    J2 = copy.deepcopy(J); J2['78']['parcalar'][1].append(J2['78']['parcalar'][0][0])
    vaka('parca', 'bilinen FAIL: tekrar eden cift', 'HATA ValueError', lambda: u.parcalar(J2, '78'))
    J3 = copy.deepcopy(J); J3['78']['parcalar'][0].pop()
    vaka('parca', 'bilinen FAIL: 78 bolumunde eksik cift', 'HATA ValueError', lambda: u.parcalar(J3, '78'))
    J4 = copy.deepcopy(J); J4['ornek']['parcalar'][0].append('CANCER_LIBRA')
    vaka('parca', 'bilinen FAIL: CL parcaya yazilmis', 'HATA ValueError', lambda: u.parcalar(J4, 'ornek'))
    J5 = copy.deepcopy(J); J5['ornek']['parcalar'][0].append('X_Y')
    vaka('parca', 'bilinen FAIL: bilinmeyen cift', 'HATA ValueError', lambda: u.parcalar(J5, 'ornek'))
    # 2 Kova kapisi listesi
    vaka('kova', 'ornek parca 1 kenar_zorunlu = AQUARIUS_CANCER; parca 2 = AQUARIUS_AQUARIUS', [['AQUARIUS_CANCER'], ['AQUARIUS_AQUARIUS']],
         lambda: [p['kenar_zorunlu'] for p in Po['parcalar']])
    vaka('kova', '78: tum Kova ciftleri (11) kenar listesinde', 11, lambda: sum(len(p['kenar_zorunlu']) for p in P7['parcalar']))
    pk = copy.deepcopy(Po['parcalar'][0]); pk['kenar_zorunlu'] = []
    vaka('kova', 'bilinen FAIL: Kova cifti kenar listesinde yok', 'HATA ValueError', lambda: u.kenar_dogrula(pk))
    pc = copy.deepcopy(Po['parcalar'][0]); pc['ciftler'] = pc['ciftler'][1:] + ['CANCER_LIBRA']
    vaka('kova', 'bilinen FAIL: CL ilk degil', 'HATA ValueError', lambda: u.kenar_dogrula(pc))
    # 3 siparis kontrolu
    ak = u.siparis_akislari(['kupa-siparis.yml', 'pod-order-router.yml', 'ornament-78-uretim.yml', 'siparis-giris.yml'])
    vaka('siparis', 'akis secimi (siparis|order)', ['kupa-siparis.yml', 'pod-order-router.yml', 'siparis-giris.yml'], lambda: ak)
    kos = [dict(id=1, path='.github/workflows/kupa-siparis.yml', status='queued'), dict(id=2, path='.github/workflows/ornament-78-uretim.yml', status='in_progress'),
           dict(id=3, path='.github/workflows/siparis-giris.yml', status='completed')]
    vaka('siparis', 'bilinen FAIL: kupa-siparis queued -> etkin', [1], lambda: [x['id'] for x in u.siparis_aktif(ak, kos)])
    vaka('siparis', 'bilinen PASS: ilgisiz akis ve biten siparis -> etkin yok', [], lambda: [x['id'] for x in u.siparis_aktif(ak, kos[1:])])
    # 4 printful_dosya ve dpi
    T = O / 'pf'; T.mkdir(exist_ok=True)
    rng = np.random.default_rng(4)
    rgb = rng.integers(0, 255, (954, 954, 3)).astype(np.uint8); rgba = np.dstack([rgb, rng.integers(0, 255, (954, 954, 1)).astype(np.uint8)])
    Image.fromarray(rgb).save(T / 'X_Y_RUBY_954.png', dpi=(300, 300))
    Image.fromarray(rgba, 'RGBA').save(T / 'X_Y_SADE_ALTIN_954.png')
    Image.fromarray(rgb).save(T / 'X_Y_FILDISI_954.png')
    Image.fromarray(rgb).resize((900, 900)).save(T / 'K900_RUBY_954.png', dpi=(300, 300))
    Image.fromarray(rgba, 'RGBA').save(T / 'KRGBA_RUBY_954.png', dpi=(300, 300))
    Image.fromarray(rgb).convert('P').save(T / 'KP_RUBY_954.png', dpi=(300, 300))
    Image.fromarray(rgb).save(T / 'KRGB_SADE_ALTIN_954.png', dpi=(300, 300))
    lab = ImageCms.ImageCmsProfile(ImageCms.createProfile('LAB')).tobytes()
    Image.fromarray(rgb).save(T / 'KICC_RUBY_954.png', dpi=(300, 300), icc_profile=lab)
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    Image.fromarray(rgb).save(T / 'KSRGB_RUBY_954.png', dpi=(300, 300), icc_profile=srgb)
    pf = lambda f, s: u.printful_dosya(T / f, s)['gecti']
    vaka('printful', 'bilinen PASS: RUBY RGB dpi 300', True, lambda: pf('X_Y_RUBY_954.png', 'RUBY'))
    vaka('printful', 'bilinen PASS: sRGB ICC', True, lambda: pf('KSRGB_RUBY_954.png', 'RUBY'))
    vaka('printful', 'bilinen FAIL: SADE dpi yok (yazim oncesi)', False, lambda: pf('X_Y_SADE_ALTIN_954.png', 'SADE_ALTIN'))
    d_s = {}
    vaka('dpi', 'bilinen PASS: SADE dpi yazimi piksel ayni', [True, True], lambda: (d_s.update(u.dpi_yaz(T / 'X_Y_SADE_ALTIN_954.png')), [d_s['yazildi'], d_s['piksel_ayni']])[1])
    vaka('printful', 'bilinen PASS: dpi yazilmis SADE RGBA', True, lambda: pf('X_Y_SADE_ALTIN_954.png', 'SADE_ALTIN'))
    vaka('printful', 'bilinen FAIL: FILDISI dpi yok', False, lambda: pf('X_Y_FILDISI_954.png', 'FILDISI'))
    vaka('printful', 'bilinen FAIL: 900 px', False, lambda: pf('K900_RUBY_954.png', 'RUBY'))
    vaka('printful', 'bilinen FAIL: RUBY RGBA', False, lambda: pf('KRGBA_RUBY_954.png', 'RUBY'))
    vaka('printful', 'bilinen FAIL: RUBY P (paletli)', False, lambda: pf('KP_RUBY_954.png', 'RUBY'))
    vaka('printful', 'bilinen FAIL: SADE RGB', False, lambda: pf('KRGB_SADE_ALTIN_954.png', 'SADE_ALTIN'))
    vaka('printful', 'bilinen FAIL: sRGB olmayan ICC (LAB)', False, lambda: pf('KICC_RUBY_954.png', 'RUBY'))
    vaka('dpi', 'zaten 300 dpi: yeniden kaydedilmez (bayt ayni)', [False, True],
         lambda: (lambda b0, d: [d['yazildi'], (T / 'X_Y_RUBY_954.png').read_bytes() == b0])((T / 'X_Y_RUBY_954.png').read_bytes(), u.dpi_yaz(T / 'X_Y_RUBY_954.png')))
    Image.fromarray(rgba, 'RGBA').save(T / 'B_SADE_ALTIN_954.png')
    vaka('dpi', 'bilinen FAIL: piksel degistiren yazim tespit edilir (RGBA -> RGB)', False,
         lambda: u.dpi_yaz(T / 'B_SADE_ALTIN_954.png', yazici=lambda y, im: im.convert('RGB').save(y, dpi=(300, 300)))['piksel_ayni'])
    # 5 cift sonu kancasi (sahte Drive / sahte rclone), FAIL siniflandirma, temizlik, ara OLCUM
    def kanca(r, cift='TAURUS_TAURUS', rclone_kod=None, kontrol=False):
        t = Path(tempfile.mkdtemp(dir=O)); Oo, RP, DE, w = t / 'png', t / 'rapor', t / 'de', t / '_is' / cift
        for x in (Oo, RP, DE, w / 'dump'):
            x.mkdir(parents=True)
        (w / 'katman.pkl').write_bytes(b'x' * 100); (w / 'dump' / 'a').write_text('a')
        for s in u.STIL:
            shutil.copyfile(T / 'X_Y_RUBY_954.png', Oo / f'{cift}_{s}_954.png')
        (DE / f'YAKIN_{cift}_aquarius_RUBY_once_954_4x.png').write_bytes(b'png')
        (RP / 'OLCUM_PARCA.json').write_text('{}')
        env = dict(GERCEK_BOY_CIFTLER=cift, ORNEK78_DRIVE_KOK_ID='kok', ORNEK78_RCLONE_BEKLE='0')
        if rclone_kod is None:
            env['ORNEK78_YEREL_DRIVE'] = str(t / 'drive')
        else:
            sc = t / 'rclone_sahte'; sc.write_text(f'#!/bin/sh\nexit {rclone_kod}\n'); sc.chmod(0o755); env['ORNEK78_RCLONE'] = str(sc)
        gb = (lambda c: (shutil.copyfile(T / 'X_Y_RUBY_954.png', RP / f'GERCEK_BOY_{c}_5STIL_300dpi.png'), RP / f'GERCEK_BOY_{c}_5STIL_300dpi.png')[1])
        k = u.cift_sonu(cift if not kontrol else 'CANCER_LIBRA', r, Oo, RP, DE, w, 1, gercek_boy_fn=gb, onizleme_fn=None, env=env)
        return t, k
    rP = dict(kapi=dict(sert=dict(a=True)))
    t, k = kanca(rP)
    lst = sorted(str(p.relative_to(t / 'drive')) for p in (t / 'drive').rglob('*') if p.is_file())
    vaka('kanca', 'bilinen PASS: PASS cift kokte 5 PNG + GERCEK_BOY + YAKIN + RAPOR/PARCA_1', True,
         lambda: all(f'TAURUS_TAURUS_{s}_954.png' in lst for s in u.STIL) and 'GERCEK_BOY/GERCEK_BOY_TAURUS_TAURUS_5STIL_300dpi.png' in lst
         and any(x.startswith('YAKIN/') for x in lst) and 'RAPOR/PARCA_1/OLCUM_PARCA.json' in lst and not any(x.startswith('FAIL/') for x in lst))
    vaka('kanca', 'katman.pkl ve dump/ silindi', [False, False], lambda: [k['temizlik']['katman_pkl_var'], k['temizlik']['dump_var']])
    t2, k2 = kanca(dict(kapi=dict(sert=dict(a=False))))
    lst2 = sorted(str(p.relative_to(t2 / 'drive')) for p in (t2 / 'drive').rglob('*') if p.is_file())
    vaka('kanca', 'bilinen FAIL: FAIL cift FAIL/<CIFT>/ altinda, kokte PNG yok', [True, False],
         lambda: [all(f'FAIL/TAURUS_TAURUS/TAURUS_TAURUS_{s}_954.png' in lst2 for s in u.STIL), any(x.endswith('_954.png') and '/' not in x for x in lst2)])
    rY = dict(kapi=dict(sert=dict(a=True)))
    t3, k3 = kanca(rY, rclone_kod=1)
    vaka('kanca', 'bilinen FAIL: sahte rclone cikis 1 -> 3 deneme, yukleme_hata, cift FAIL', [False, 3, False],
         lambda: [k3['yukleme']['ok'], k3['yukleme']['deneme'], rY['kapi']['sert'].get('yukleme_hata')])
    t4, k4 = kanca(dict(kapi=dict(sert=dict(a=True))), rclone_kod=0)
    vaka('kanca', 'bilinen PASS: sahte rclone cikis 0 -> ok, 1 deneme', [True, 1], lambda: [k4['yukleme']['ok'], k4['yukleme']['deneme']])
    t5, k5 = kanca(dict(kapi=dict(sert=dict(a=True))), kontrol=True)
    lst5 = sorted(str(p.relative_to(t5 / 'drive')) for p in (t5 / 'drive').rglob('*') if p.is_file()) if (t5 / 'drive').exists() else []
    vaka('kanca', 'kontrol cifti (CL) PNG yuklenmez, yalniz RAPOR', True, lambda: not any(x.endswith('_954.png') for x in lst5))
    rG = dict(kapi=dict(sert=dict(a=True)))
    vaka('kanca', 'bilinen FAIL: gercek boy None -> gercek_boy_var False', False,
         lambda: (u.cift_sonu('TAURUS_TAURUS', rG, t / 'png', t / 'rapor', t / 'de', t / '_is' / 'TAURUS_TAURUS', 1, gercek_boy_fn=lambda c: None,
                              env=dict(GERCEK_BOY_CIFTLER='TAURUS_TAURUS', ORNEK78_YEREL_DRIVE=str(t / 'drive2'))), rG['kapi']['sert']['gercek_boy_var'])[1])
    rGF = dict(kapi=dict(sert=dict(a=True))); tG = Path(tempfile.mkdtemp(dir=O))
    for x in ('png', 'rapor', 'de', '_is/TAURUS_TAURUS'):
        (tG / x).mkdir(parents=True)
    for s_ in u.STIL:
        shutil.copyfile(T / 'X_Y_RUBY_954.png', tG / 'png' / f'TAURUS_TAURUS_{s_}_954.png')
    u.cift_sonu('TAURUS_TAURUS', rGF, tG / 'png', tG / 'rapor', tG / 'de', tG / '_is' / 'TAURUS_TAURUS', 1, gercek_boy_fn=lambda c: None,
                env=dict(GERCEK_BOY_CIFTLER='TAURUS_TAURUS', ORNEK78_YEREL_DRIVE=str(tG / 'drive')))
    lG = sorted(str(p.relative_to(tG / 'drive')) for p in (tG / 'drive').rglob('*') if p.is_file())
    vaka('kanca', 'F: gercek boy yoksa 5 PNG FAIL/<CIFT>/ altinda (kokte degil)', [5, 0],
         lambda: [sum(x.startswith('FAIL/TAURUS_TAURUS/') for x in lG), sum(x.endswith('_954.png') and '/' not in x for x in lG)])
    vaka('eta', 'ETA satiri bicimi', 'ETA 3/9 gecen 300 sn kalan 600 sn yuzde 33.3', lambda: u.eta_satiri(3, 9, 300.0))
    # 6 klasor tekligi, Drive karsilastirma, dal kapisi
    vaka('klasor', 'bilinen PASS: tekil', True, lambda: u.klasor_tekligi([dict(Path='FAIL', IsDir=True), dict(Path='RAPOR', IsDir=True)])['gecti'])
    vaka('klasor', 'bilinen FAIL: ayni adli iki klasor', False, lambda: u.klasor_tekligi([dict(Path='RAPOR', IsDir=True), dict(Path='RAPOR', IsDir=True)])['gecti'])
    ls = [dict(Path='A_B_RUBY_954.png', IsDir=False, Hashes=dict(sha256='h1')), dict(Path='GERCEK_BOY/G.png', IsDir=False, Hashes=dict(sha256='h2'))]
    vaka('drive', 'bilinen PASS: sayi ve sha esit', True, lambda: u.drive_karsilastir(ls, [('A_B_RUBY_954.png', 'h1'), ('GERCEK_BOY/G.png', 'h2')])['gecti'])
    vaka('drive', 'bilinen FAIL: sha farkli', False, lambda: u.drive_karsilastir(ls, [('A_B_RUBY_954.png', 'hX')])['gecti'])
    vaka('drive', 'bilinen FAIL: eksik dosya', False, lambda: u.drive_karsilastir(ls, [('C_D_RUBY_954.png', 'h1')])['gecti'])
    vaka('drive', 'bilinen FAIL: Drive icinde fazla dosya (RAPOR disi)', False,
         lambda: u.drive_karsilastir(ls + [dict(Path='FAIL/X/X_RUBY_954.png', IsDir=False, Hashes=dict(sha256='h9'))], [('A_B_RUBY_954.png', 'h1'), ('GERCEK_BOY/G.png', 'h2')])['gecti'])
    vaka('drive', 'bilinen PASS: RAPOR/ altindaki fazla dosya sayilmaz', True,
         lambda: u.drive_karsilastir(ls + [dict(Path='RAPOR/x.json', IsDir=False, Hashes=dict(sha256='h8'))], [('A_B_RUBY_954.png', 'h1'), ('GERCEK_BOY/G.png', 'h2')])['gecti'])
    vaka('drive', 'bilinen FAIL: Drive sha vermiyor (kiyas atlanmaz)', False,
         lambda: u.drive_karsilastir([dict(Path='A_B_RUBY_954.png', IsDir=False, Hashes={})], [('A_B_RUBY_954.png', 'h1')])['gecti'])
    vaka('import', 'F: uretim78 numpy / PIL olmadan yuklenir (hazirlik / birlestir pip oncesi)', 'OK',
         lambda: subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.modules["numpy"]=None; sys.modules["PIL"]=None; import importlib.util as q; '
                                 f's=q.spec_from_file_location("m", "{_d / "uretim78.py"}"); m=q.module_from_spec(s); s.loader.exec_module(m); '
                                 'm.parcalar; m.birlestir({}, 0); m.dal_kapisi(["a.json"]); print("OK")'], capture_output=True, text=True).stdout.strip())
    vaka('drive', 'bilinen FAIL: ayni adli iki dosya', False, lambda: u.drive_karsilastir(ls + [ls[0]], [('A_B_RUBY_954.png', 'h1')])['gecti'])
    vaka('dal', 'bilinen PASS: json/md/txt/log', True, lambda: u.dal_kapisi(['d/OLCUM.json', 'd/INCELEME.md', 'd/log.txt', 'd/a.log'])['gecti'])
    for f in ('d/X_RUBY_954.png', 'd/GERCEK_BOY_X_5STIL_300dpi.png', 'd/ONIZLEME_X.png', 'd/YAKIN_X.json', 'd/aquarius_symbol_gold.json', 'd/X.bin'):
        vaka('dal', f'bilinen FAIL: {f}', False, lambda f=f: u.dal_kapisi([f])['gecti'])
    # 7 birlestirme
    def R_(c, ok=True, kp=True):
        return dict(kontrol_pass=kp, kontrol={}, cift={'CANCER_LIBRA': dict(kapi=dict(sert=dict(a=True))), c: dict(kapi=dict(sert=dict(a=ok)))},
                    kenar_onarim_uyari=[], kucultme=[dict(cift='CANCER_LIBRA'), dict(cift=c)], cift_sonu=[dict(cift='CANCER_LIBRA', kontrol=True), dict(cift=c)],
                    cikis=dict(cokus_ciftler=[]))
    B = u.birlestir({1: R_('TAURUS_TAURUS'), 2: R_('LIBRA_LIBRA')}, 2)
    vaka('birlestir', 'bilinen PASS: CL tekillestirildi, 2 cift, gecti', [['LIBRA_LIBRA', 'TAURUS_TAURUS'], 2, True], lambda: [sorted(B['cift']), len(B['kucultme']), B['gecti']])
    vaka('birlestir', 'bilinen FAIL: eksik parca', [[2], False], lambda: (lambda b: [b['eksik_parca'], b['gecti']])(u.birlestir({1: R_('TAURUS_TAURUS'), 2: None}, 2)))
    vaka('birlestir', 'bilinen FAIL: parca CL kontrolu FAIL', False, lambda: u.birlestir({1: R_('TAURUS_TAURUS', kp=False)}, 1)['gecti'])
    vaka('birlestir', 'bilinen FAIL: cift FAIL', ['TAURUS_TAURUS'], lambda: u.birlestir({1: R_('TAURUS_TAURUS', ok=False)}, 1)['fail'])
    vaka('birlestir', 'bilinen FAIL: ayni cift iki parcada', 'HATA ValueError', lambda: u.birlestir({1: R_('TAURUS_TAURUS'), 2: R_('TAURUS_TAURUS')}, 2))
    # 8 kenar on olcumu (motor yolu)
    kaynak = _k / 'docs/ornament/kaynak'
    K41 = json.loads((_k / 'docs/ornament/ornek/ORNAMENT_SIKILASTIRMA_20261104_1333_41839101824/KENAR_ONARIM.json').read_text())
    ref = {r['kaynak']: (r['n0'], r['degisen_piksel']) for r in K41['satirlar'] if r['cift'] == 'CANCER_LIBRA' and r['kaynak'] in ('cancer', 'libra')}
    vaka('kenar', 'bilinen PASS: cancer / libra gercek kaynak = 41839101824 motor KENAR_ONARIM', [ref['cancer'], ref['libra']],
         lambda: [tuple(u.kenar_olc(kaynak / f'{b}_symbol_gold.png', False)[k] for k in ('n0', 'degisen_piksel')) for b in ('cancer', 'libra')])
    S = O / 'sahte_kenar.png'
    W_, H_ = 8400, 3400
    im = Image.new('L', (W_ // 2, H_ // 2), 0); dr = ImageDraw.Draw(im)
    x = np.linspace(-100, W_ // 2 + 100, 300)
    for y0 in (420, 1280):
        dr.line(list(zip(x, y0 + 420 * np.sin(x / (W_ // 2) * 4 * np.pi))), fill=255, width=440, joint='curve')
    A = np.asarray(im.resize((W_, H_), Image.BILINEAR))
    Image.fromarray(np.dstack([np.full((H_, W_, 3), (212, 170, 90), np.uint8), A]), 'RGBA').save(S)
    kn = u.kenar_olc(S, False); kh = u.kenar_olc_ham(S)
    vaka('kenar', 'sahte buyuk kaynak (kenara degen murekkep): motor yolunda n0 > 0', True, lambda: kn['n0'] > 0)
    vaka('kenar', 'bilinen FAIL: yolu atlayan ham olcum farkli sonuc verir', True, lambda: (kh['n0'], kh['degisen_piksel']) != (kn['n0'], kn['degisen_piksel']))
    if a.kfake_kova and a.motor_kenar:
        mk = json.loads(Path(a.motor_kenar).read_text())
        mr = [r for r in mk['satirlar'] if r['kaynak'] == 'aquarius'][0]
        vaka('kenar', 'bilinen PASS: sahte Kova on olcum = yerel motor KENAR_ONARIM', [mr['n0'], mr['degisen_piksel']],
             lambda: [u.kenar_olc(a.kfake_kova, False)[k] for k in ('n0', 'degisen_piksel')])
    # 9 BEKLENEN_SONUC_ORNEK betigi
    ornek = [c for p in J['ornek']['parcalar'] for c in p]
    pd = O / 'bk_parca'
    for n in (1, 2):
        (pd / f'PARCA_{n}').mkdir(parents=True, exist_ok=True)
        (pd / f'PARCA_{n}' / 'SIPARIS.json').write_text('{}')
        (pd / f'PARCA_{n}' / 'OLCUM.json').write_text(json.dumps(dict(cift_sonu=[{}] * 5)))
        (pd / f'PARCA_{n}' / 'log_ornek78.txt').write_text('\n'.join(['[ 1s] ETA x'] * 5))
    sd = dict(sade1_piksel_sha='p', sade_altin_piksel_sha='p')
    Bs = dict(gecti=True, eksik_parca=[], fail=[], cokus=[], kenar_onarimsiz_ek_fail={}, kontrol_parca={1: dict(kontrol_pass=True), 2: dict(kontrol_pass=True)},
              drive=dict(gecti=True), yukleme=[dict(cift=c, temizlik=dict(katman_pkl_var=False, dump_var=False),
                                                    yukleme=dict(dosyalar=[dict(yol=f'{c}_{s}_954.png') for s in u.STIL])) for c in ornek],
              cift={c: dict(kapi=dict(sert={f'printful_dosya_{s}': True for s in u.STIL}), dpi_yazim={s: dict(piksel_ayni=True) for s in u.STIL},
                            sade=sd, fildisi=dict(girdi_piksel_sha='p'), kaynak_kenar_onarim=dict(aquarius=dict(n0=445, degisen_piksel=464)) if 'AQUARIUS' in c else {},
                            **(dict(kenar_onarimsiz_neden=dict(gecti=True)) if 'AQUARIUS' in c else {})) for c in ornek})
    kapi = dict(kaynaklar=[dict(kaynak='aquarius_symbol_gold.png', mod_acik_bilgi=dict(kenar_onar=dict(n0=445, degisen_piksel=464)))])
    kenar = dict(kaynak=dict(aquarius=dict(n0=445, degisen_piksel=464)))
    sip = dict(akislar=['kupa-siparis.yml'])
    vaka('beklenen', 'bilinen PASS: sahte tam veri', True, lambda: bk.beklenti(Bs, kapi, kenar, sip, pd, ornek)['hepsi_gecti'])
    B2 = copy.deepcopy(Bs); B2['kontrol_parca'][2]['kontrol_pass'] = False
    vaka('beklenen', 'bilinen FAIL: parca 2 CL kontrolu FAIL', False, lambda: bk.beklenti(B2, kapi, kenar, sip, pd, ornek)['hepsi_gecti'])
    B3 = copy.deepcopy(Bs); B3['cift'][ornek[0]]['dpi_yazim']['RUBY']['piksel_ayni'] = False
    vaka('beklenen', 'bilinen FAIL: dpi piksel degisti', False, lambda: bk.beklenti(B3, kapi, kenar, sip, pd, ornek)['hepsi_gecti'])
    vaka('beklenen', 'bilinen FAIL: kenar on olcum farkli (aquarius 440)', False,
         lambda: bk.beklenti(Bs, kapi, dict(kaynak=dict(aquarius=dict(n0=440, degisen_piksel=464))), sip, pd, ornek)['hepsi_gecti'])
    # 9b yeni duzen (Serdar 4 Kas gece; asama 2): bolum, CL sonda, kontrol bayragi, birlestir kontrol_ad, beklenen --bolum yeni_duzen
    Py = u.parcalar(J, 'yeni_duzen')
    tum_y = [c for p in Py['parcalar'] for c in p['uretim']]
    vaka('yeni_duzen', '4 parca, CL her parcada ilk, CL yalniz parca 3 sonunda uretim, 11 tekil cift', [4, True, [False, False, True, False], 11, 11],
         lambda: [Py['parca_sayisi'], all(p['ciftler'][0] == 'CANCER_LIBRA' for p in Py['parcalar']), [p['cl_yeni'] for p in Py['parcalar']], len(tum_y), len(set(tum_y))])
    vaka('yeni_duzen', 'uretim listesi = YD11', sorted(u.YD11), lambda: sorted(tum_y))
    Jy1 = copy.deepcopy(J); Jy1['ornek']['cl_yeni_parca'] = 1
    vaka('yeni_duzen', 'bilinen FAIL: cl_yeni_parca ornek bolumunde', 'HATA ValueError', lambda: u.parcalar(Jy1, 'ornek'))
    Jy2 = copy.deepcopy(J); Jy2['yeni_duzen']['parcalar'][0].pop()
    vaka('yeni_duzen', 'bilinen FAIL: yeni_duzen bolumunde eksik cift', 'HATA ValueError', lambda: u.parcalar(Jy2, 'yeni_duzen'))
    Jy3 = copy.deepcopy(J); Jy3['yeni_duzen']['cl_yeni_parca'] = 9
    vaka('yeni_duzen', 'bilinen FAIL: cl_yeni_parca aralik disi', 'HATA ValueError', lambda: u.parcalar(Jy3, 'yeni_duzen'))
    Jy4 = copy.deepcopy(J); del Jy4['yeni_duzen']['cl_yeni_parca']
    vaka('yeni_duzen', 'bilinen FAIL: cl_yeni_parca yok (CL uretilmez)', 'HATA ValueError', lambda: u.parcalar(Jy4, 'yeni_duzen'))
    py3 = copy.deepcopy(Py['parcalar'][2]); py3['ciftler'] = ['CANCER_LIBRA', 'CANCER_LIBRA'] + py3['ciftler'][1:-1]
    vaka('yeni_duzen', 'bilinen FAIL: yeni duzen CL sonda degil', 'HATA ValueError', lambda: u.kenar_dogrula(py3))
    tY = Path(tempfile.mkdtemp(dir=O))
    for x in ('png', 'rapor', 'de', '_is/CANCER_LIBRA'):
        (tY / x).mkdir(parents=True)
    for s_ in u.STIL:
        shutil.copyfile(T / 'X_Y_RUBY_954.png', tY / 'png' / f'CANCER_LIBRA_{s_}_954.png')
    kY = u.cift_sonu('CANCER_LIBRA', dict(kapi=dict(sert=dict(a=True))), tY / 'png', tY / 'rapor', tY / 'de', tY / '_is' / 'CANCER_LIBRA', 3, gercek_boy_fn=None,
                     env=dict(ORNEK78_YEREL_DRIVE=str(tY / 'drive')), kontrol=False)
    lY = sorted(str(p.relative_to(tY / 'drive')) for p in (tY / 'drive').rglob('*') if p.is_file()) if (tY / 'drive').exists() else []
    vaka('yeni_duzen', 'bilinen PASS: kontrol=False CL 5 PNG yuklenir (kokte)', [False, 5], lambda: [kY['kontrol'], sum(x.endswith('_954.png') and '/' not in x for x in lY)])

    def Ry(ok=True, kp=True):
        return dict(kontrol_pass=kp, kontrol={}, cift={u.KONTROL_ESKI: dict(kapi=dict(sert=dict(a=True))), 'CANCER_LIBRA': dict(kapi=dict(sert=dict(a=ok))),
                                                       'TAURUS_TAURUS': dict(kapi=dict(sert=dict(a=True)))},
                    kenar_onarim_uyari=[], kucultme=[dict(cift=u.KONTROL_ESKI), dict(cift='CANCER_LIBRA')],
                    cift_sonu=[dict(cift='CANCER_LIBRA', kontrol=True), dict(cift='TAURUS_TAURUS'), dict(cift='CANCER_LIBRA', kontrol=False)], cikis=dict(cokus_ciftler=[]))
    By = u.birlestir({1: Ry()}, 1, u.KONTROL_ESKI)
    vaka('yeni_duzen', 'birlestir kontrol_ad=KONTROL_ESKI: CL uretim birlesimde, kontrol yok, yukleme 2', [['CANCER_LIBRA', 'TAURUS_TAURUS'], 2, 1, True],
         lambda: [sorted(By['cift']), len(By['yukleme']), len(By['kucultme']), By['gecti']])
    vaka('yeni_duzen', 'bilinen FAIL: yeni duzen CL uretimi FAIL -> birlesim FAIL', ['CANCER_LIBRA'], lambda: u.birlestir({1: Ry(ok=False)}, 1, u.KONTROL_ESKI)['fail'])
    vaka('yeni_duzen', 'bilinen FAIL: varsayilan kontrol_ad CL uretimini atlar (yeni duzende kullanilmamali)', False,
         lambda: 'CANCER_LIBRA' in u.birlestir({1: Ry()}, 1)['cift'])
    orn_y = [c for p in J['yeni_duzen']['parcalar'] for c in p] + ['CANCER_LIBRA']
    pdy = O / 'bk_parca_yd'
    for n in (1, 2, 3, 4):
        (pdy / f'PARCA_{n}').mkdir(parents=True, exist_ok=True)
        (pdy / f'PARCA_{n}' / 'SIPARIS.json').write_text('{}')
        (pdy / f'PARCA_{n}' / 'OLCUM.json').write_text(json.dumps(dict(cift_sonu=[{}] * 3)))
        (pdy / f'PARCA_{n}' / 'log_ornek78.txt').write_text('\n'.join(['[ 1s] ETA x'] * 3))
    Bsy = copy.deepcopy(Bs)
    Bsy['kontrol_parca'] = {n: dict(kontrol_pass=True) for n in (1, 2, 3, 4)}
    Bsy['yukleme'] = [dict(cift=c, temizlik=dict(katman_pkl_var=False, dump_var=False), yukleme=dict(dosyalar=[dict(yol=f'{c}_{s}_954.png') for s in u.STIL])) for c in orn_y]
    Bsy['cift'] = {c: dict(kapi=dict(sert=dict({f'printful_dosya_{s}': True for s in u.STIL}, yeni_duzen_kapilari_var=True)), dpi_yazim={s: dict(piksel_ayni=True) for s in u.STIL},
                           sade=sd, fildisi=dict(girdi_piksel_sha='p'), kaynak_kenar_onarim=dict(aquarius=dict(n0=445, degisen_piksel=464)) if 'AQUARIUS' in c else {},
                           **(dict(kenar_onarimsiz_neden=dict(gecti=True)) if 'AQUARIUS' in c else {})) for c in orn_y}
    ydt = dict(ref_sabit_esit=True, gecen=78, fail=[], bilinen_fail_hepsi=True, bilinen_fail_sayi=48)
    vaka('yeni_duzen', 'beklenen bilinen PASS: yeni_duzen sahte tam veri', True, lambda: bk.beklenti(Bsy, kapi, kenar, sip, pdy, orn_y, 'yeni_duzen', ydt)['hepsi_gecti'])
    Bsy2 = copy.deepcopy(Bsy); del Bsy2['cift']['CANCER_LIBRA']['kapi']['sert']['yeni_duzen_kapilari_var']
    vaka('yeni_duzen', 'beklenen bilinen FAIL: CL yeni duzen modunda degil', False, lambda: bk.beklenti(Bsy2, kapi, kenar, sip, pdy, orn_y, 'yeni_duzen', ydt)['hepsi_gecti'])
    vaka('yeni_duzen', 'beklenen bilinen FAIL: hazirlik yerel testi yok', False, lambda: bk.beklenti(Bsy, kapi, kenar, sip, pdy, orn_y, 'yeni_duzen', None)['hepsi_gecti'])
    vaka('yeni_duzen', 'beklenen bilinen FAIL: yerel test ref != SABIT', False,
         lambda: bk.beklenti(Bsy, kapi, kenar, sip, pdy, orn_y, 'yeni_duzen', dict(ydt, ref_sabit_esit=False))['hepsi_gecti'])
    vaka('yeni_duzen', 'eski bolum (ornek) beklentisi yeni_duzen kapilarini istemez', True, lambda: bk.beklenti(Bs, kapi, kenar, sip, pd, ornek)['hepsi_gecti'])
    # 10 ornek78 alt surec vakalari
    if a.ornek78_hizli:
        bos = Path(tempfile.mkdtemp(dir=O)); (bos / 'k').mkdir()
        (bos / 'k' / 'font.ttf').write_bytes(subprocess.run(['git', '-C', str(_k), 'show', '2a08a78216ca19dd632e7dedda31c4c53c365c25:motor/font/EBGaramond-Italic.ttf'],
                                                         capture_output=True, check=True).stdout)
        def o78(env, ad):
            e = dict(os.environ); e.update(env)
            r = subprocess.run([sys.executable, '-I', str(_d / 'ornek78.py'), '--kaynak', str(bos / 'k'), '--motor', str(bos / 'k'), '--zemin', str(bos / 'k'),
                                '--son', str(bos / 'k'), '--onayli', str(bos / 'k'), '--cikti', str(bos / ad / 'png'), '--rapor', str(bos / ad / 'rapor'),
                                '--font', str(bos / 'k' / 'font.ttf')], env=e, capture_output=True, text=True, timeout=600)
            (bos / f'{ad}.log').write_text(r.stdout + r.stderr)
            return r.returncode, (json.loads((bos / ad / 'rapor' / 'OLCUM.json').read_text()) if (bos / ad / 'rapor' / 'OLCUM.json').exists() else None)
        vaka('ornek78', 'bilinen FAIL: PARCA modunda ilk cift CL degil -> cikis 4', 4,
             lambda: o78(dict(ORNEK78_PARCA='1', ORNEK78_CIFTLER='TAURUS_TAURUS,CANCER_LIBRA', ORNEK78_YEREL_DRIVE=str(bos / 'drv')), 'c4')[0])
        vaka('ornek78', 'bilinen PASS: ilk cift CL -> cikis 4 degil (girdi yok: CL cokus -> 3)', 3,
             lambda: o78(dict(ORNEK78_PARCA='1', ORNEK78_CIFTLER='CANCER_LIBRA,TAURUS_TAURUS', ORNEK78_YEREL_DRIVE=str(bos / 'drv')), 'c3')[0])
        kd, Rd = o78(dict(ORNEK78_CIFTLER='ARIES_TAURUS,CANCER_TAURUS,LIBRA_LIBRA', ORNEK78_TEST_HATA='CANCER_TAURUS'), 'dayan')
        vaka('ornek78', 'cift dayanikliligi: 2. ciftte hata, 3. cift islendi, cikis 2', [2, True, True],
             lambda: [kd, 'cokus' in Rd['cift']['CANCER_TAURUS'], 'LIBRA_LIBRA' in Rd['cift']])
        kc, Rc = o78(dict(ORNEK78_PARCA='1', ORNEK78_CIFTLER='CANCER_LIBRA,TAURUS_TAURUS', ORNEK78_TEST_HATA='CANCER_LIBRA', ORNEK78_YEREL_DRIVE=str(bos / 'drv2')), 'clhata')
        vaka('ornek78', 'F: CL govdesinde hata -> parca DUR (cikis 3), sonraki cift islenmez', [3, False, False],
             lambda: [kc, 'TAURUS_TAURUS' in Rc['cift'], Rc.get('kontrol_pass')])
        kd2, Rd2 = o78(dict(ORNEK78_CIFTLER='ARIES_TAURUS,CANCER_TAURUS'), 'dayan0')
        vaka('ornek78', 'bilinen PASS: hata yoksa cokus alani yok', False, lambda: 'cokus' in Rd2['cift']['CANCER_TAURUS'])
    R = dict(vakalar=V, test_gecti=all(v['gecti'] for v in V), tur='yerel mantik testi (sahte veri; motor girdisi yalniz Actions)')
    (O / 'URETIM78_MANTIK_TESTI.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    for v in V:
        print('PASS' if v['gecti'] else 'FAIL', v['grup'], '|', v['vaka'], '| sonuc', str(v['sonuc'])[:100], flush=True)
    print('URETIM78 MANTIK TESTI', 'PASS' if R['test_gecti'] else 'FAIL', len(V), 'vaka', flush=True)
    return 0 if R['test_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
