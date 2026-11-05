#!/usr/bin/env python3
"""ornament_siparis.siniflama ve gizlilik_tara birim testi (bilinen PASS + bilinen FAIL; ANA_2 ders 14). Ag yok, motor yok.
Kullanim: python -I test_ornament_siparis.py  -> cikis 0 = hepsi beklendigi gibi."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_d = Path(__file__).resolve().parent


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


osp = yukle('osp', 'ornament_siparis.py')
gt = yukle('gt', 'gizlilik_tara.py')
C = 'CANCER_LIBRA'
SERT_OK = {'koyu_kontrast_ortanca': True, 'koyu_yd_murekkep_r_le_336': True, 'koyu_yd_bosluk_32_32': True, 'sade1_yerlesim_ayni': True}


KONTROL_OK = {'kapi': {'sert': {'koyu_kontrast_ortanca': True, 'fildisi_cikis_0': True}}}


def R_(kontrol=True, kontrol_kayit=KONTROL_OK, **r):
    c = {C: r}
    if kontrol_kayit is not None:
        c[osp.KONTROL_ESKI] = kontrol_kayit
    return {'cift': c, 'kontrol_pass': kontrol}


def MO(bt, bk):
    return {'yeni_duzen': {'olcum': {'bosluk_tarih_isim': bt, 'bosluk_isim_kucuk': bk}}}


def main():
    hata = 0
    vakalar = [
        ('pass', R_(kapi={'sert': dict(SERT_OK)}, cikis_kodlari={'motor': 0}), 'PASS'),
        ('o4_yerlesim', R_(motor_olcum={'hata': 'yeni_duzen_kapi'}, eksik=['RUBY'], cikis_kodlari={'motor': 1}), 'DUR_GIRDI'),
        ('murekkep_r', R_(kapi={'sert': dict(SERT_OK, koyu_yd_murekkep_r_le_336=False)}, cikis_kodlari={'motor': 1}), 'DUR_GIRDI'),
        ('bosluk_K8_Jsiz', R_(kapi={'sert': dict(SERT_OK, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'DUR_SERDAR', MO(39, 32)),
        ('bosluk_K8_Qlu', R_(kapi={'sert': dict(SERT_OK, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'DUR_SERDAR', MO(29, 32)),
        ('bosluk_desen_disi_sikisma', R_(kapi={'sert': dict(SERT_OK, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'MOTOR_KAPI_FAIL', MO(18, 32)),
        ('bosluk_desen_disi_kucuk', R_(kapi={'sert': dict(SERT_OK, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'MOTOR_KAPI_FAIL', MO(39, 27)),
        ('bosluk_olcum_yok', R_(kapi={'sert': dict(SERT_OK, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'MOTOR_KAPI_FAIL', {}),
        ('sade_K8', R_(kapi={'sert': dict(SERT_OK, sade1_yerlesim_ayni=False)}, yerlesim={'bosluk_px': [40, 32, 39]}, cikis_kodlari={'motor': 0}), 'DUR_SERDAR', MO(39, 32)),
        ('sade_sembol_kucuk_dar', R_(kapi={'sert': dict(SERT_OK, sade1_yerlesim_ayni=False)}, yerlesim={'bosluk_px': [25, 32, 39]}, cikis_kodlari={'motor': 0}), 'MOTOR_KAPI_FAIL', MO(39, 32)),
        ('isim_ve_K8', R_(kapi={'sert': dict(SERT_OK, koyu_yd_murekkep_r_le_336=False, koyu_yd_bosluk_32_32=False)}, cikis_kodlari={'motor': 1}), 'DUR_SERDAR', MO(39, 32)),
        ('isim_ve_kontrast', R_(kapi={'sert': dict(SERT_OK, koyu_yd_murekkep_r_le_336=False, koyu_kontrast_ortanca=False)}, cikis_kodlari={'motor': 1}), 'MOTOR_KAPI_FAIL'),
        ('kontrol_CL_fail', {'cift': {}, 'kontrol_pass': False}, 'MOTOR_KAPI_FAIL'),
        ('kontrol_yok', R_(kontrol=None, kapi={'sert': dict(SERT_OK)}, cikis_kodlari={'motor': 0}), 'MOTOR_KAPI_FAIL'),
        ('kontrast', R_(kapi={'sert': dict(SERT_OK, koyu_kontrast_ortanca=False)}, cikis_kodlari={'motor': 1}), 'MOTOR_KAPI_FAIL'),
        ('cokus', R_(cokus='tb', cikis_kodlari={'cokus': 2}), 'COKUS'),
        ('kayit_yok', {'cift': {}}, 'COKUS'),
        ('sert_yok', R_(cikis_kodlari={'motor': 0}), 'COKUS'),
        ('eksik', R_(eksik=['FILDISI'], cikis_kodlari={'motor': 0, 'fildisi': 9}), 'MOTOR_KAPI_FAIL'),
        ('kontrol_kayit_sert_fail', R_(kontrol_kayit={'kapi': {'sert': {'koyu_kontrast_ortanca': False}}}, kapi={'sert': dict(SERT_OK)}, cikis_kodlari={'motor': 0}), 'MOTOR_KAPI_FAIL'),
        ('kontrol_kayit_yok', R_(kontrol_kayit=None, kapi={'sert': dict(SERT_OK)}, cikis_kodlari={'motor': 0}), 'MOTOR_KAPI_FAIL'),
        ('sade_K8_bp_yok', R_(kapi={'sert': dict(SERT_OK, sade1_yerlesim_ayni=False)}, cikis_kodlari={'motor': 0}), 'MOTOR_KAPI_FAIL', MO(39, 32)),
    ]
    for v in vakalar:
        ad, R, bek = v[:3]
        d, n, f = osp.siniflama(R, C, v[3] if len(v) > 3 else None)
        ok = d == bek; hata += not ok
        print('PASS' if ok else 'FAIL', 'siniflama', ad, '| beklenen', bek, '| gelen', d, n, f, flush=True)
    g = {'isim1': 'AL', 'isim2': "O'NEIL", 'tarih': 'JUNE 14, 2025'}
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / 'temiz.txt').write_text('ALBERT kosu PASS kapi ALMANAC 2025')
        (t / 'isim.txt').write_text('satir: al geldi')
        (t / 'tarih.txt').write_text('tarih june 14, 2025')
        (t / 'kesme.txt').write_text("o'neil")
        gv = [('temiz', ['temiz.txt'], []), ('kisa_isim_kelime', ['isim.txt'], [('isim.txt', 'isim1')]),
              ('tarih', ['tarih.txt'], [('tarih.txt', 'tarih')]), ('kesme', ['kesme.txt'], [('kesme.txt', 'isim2')])]
        for ad, fl, bek in gv:
            b, _ = gt.tara(g, [t / x for x in fl])
            ok = b == bek; hata += not ok
            print('PASS' if ok else 'FAIL', 'gizlilik', ad, '| beklenen', bek, '| gelen', b, flush=True)
        (t / 'g.json').write_text(json.dumps({'isim1': '', 'isim2': '', 'tarih': ''}))
        bos = gt.main(['x', str(t / 'g.json'), str(t / 'temiz.txt')])
        ok = bos == 1; hata += not ok
        print('PASS' if ok else 'FAIL', 'gizlilik bos_girdi_FAIL', bos, flush=True)
    n = len(vakalar) + len(gv) + 1
    print('TOPLAM', n, 'vaka, hata', hata, flush=True)
    return 1 if hata else 0


if __name__ == '__main__':
    sys.exit(main())
