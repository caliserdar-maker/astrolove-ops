#!/usr/bin/env python3
"""AY TAKVIMI testleri (Serdar 10 Kas 2026). ETSY YOK, ag yok, Drive yok. Her kapi bilinen PASS + bilinen FAIL ornegiyle denenir.

Kullanim:
  python3 scripts/ay_takvim/test_ay_takvim.py                                        motorsuz testler; motor isteyenler ATLANDI satiri basar
  python3 scripts/ay_takvim/test_ay_takvim.py --motor MD --ornament OD [--is-akisi YML] [--zorunlu]
    MD = motor_gpt klasoru (dal siparis-gpt, sabit sha 6da763a); OD = scripts/printful klasoru (dal ornament-printful-katalog, sabit sha c950151627)
    --zorunlu: atlanan test varsa cikis 1 (is akisi bununla kosar)
Paketler: numpy, opencv-python-headless, pillow (+ ephem: ay verisi; pyyaml: is akisi kabuk testleri; motorlu testler: scipy, scikit-image, potracer).

ESDEGERLIK TESTLERI (tasinan ornament / motor adimlari): kaynak dosyalarin sha256'si sabitlenir; ilgili fonksiyon ya da satir blogu KAYNAK
DOSYADAN cikarilip ayni girdiyle calistirilir ve tasinan fonksiyonun ciktisiyla bayt bayt karsilastirilir (kopya referans yok)."""
import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import types
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont

BU = Path(__file__).resolve().parent
KOK = BU.parents[1]
sys.path.insert(0, str(BU))
import ay_takvim_kapi as KP  # noqa: E402
import ay_takvim_ornek as U  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SAYAC = dict(pas=0, fail=0, atla=0)
KAYNAK_SHA = {                                                               # sabit sha'li kaynaklar (degisirse esdegerlik testi FAIL)
    'ornament_motor.py': 'e3e15ebb9b66bcf994a982a8a74e871fe0eec3a4ace1619303f18563ea5d5b81',
    'ornament_ornek.py': 'eff1e16fcf8ff210ce26a952cb3f0838a27c0ea85cfccd3907509e293540e19f',
    'ornament_ornek5.py': 'c8f4f65dce673423ea255229c9bcc01a0f8e3ffc8d6782e520967ee19cc43c25',
    'ornament_altin.py': 'c4ef4ff906659a718fc211fee23b0161eada76c0e413aff7f4a6de9a9ce6e4e0',
    'siparis_girdi.py': 'ed994f226b3896c9ffed0a1692850eb5e2aa9c83fc2d36a28ea1adf9567a9b31',
    'uret_tam.py': '5a9078ea2ed4496343d1d5fcc3d2c5bfbb38d08d202f63e04430257caa17dfcd'}


def k(ad, kosul, bilgi=''):
    ok = bool(kosul)
    SAYAC['pas' if ok else 'fail'] += 1
    print(('PASS ' if ok else 'FAIL ') + ad + ('' if ok or bilgi == '' else f'  [{str(bilgi)[:400]}]'), flush=True)
    return ok


def atla(neden, n):
    SAYAC['atla'] += n
    print(f'ATLANDI: {neden} ({n} test)', flush=True)


def dur_mu(fonk, kod=None, girdi=None):
    """fonk Dur firlatir mi (istenirse kod / girdi turu ile)."""
    try:
        fonk()
    except U.Dur as e:
        return (kod is None or e.kod == kod) and (girdi is None or e.girdi == girdi)
    return False


def ayni(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b)


# ---------------------------------------------------------------- kaynaktan cikarma (esdegerlik testleri)
def ic_fonk(src, ad):
    """kaynaktaki (ust duzey ya da main() icindeki) def'in metni, girintisi alinmis."""
    for d in ast.walk(ast.parse(src)):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return textwrap.dedent('\n'.join(src.splitlines()[d.lineno - 1:d.end_lineno]))
    raise KeyError(ad)


def blok(src, bas, son):
    """bas iceren satirdan son iceren satira kadar (son haric), girintisi alinmis."""
    L = src.splitlines()
    i = next(n for n, s in enumerate(L) if bas in s)
    j = next(n for n in range(i + 1, len(L)) if son in L[n])
    return textwrap.dedent('\n'.join(L[i:j]))


def fonk_blok(kod, ns):
    """'return' iceren satir blogunu fonksiyona sarip calistirir; yerel degiskenleri dondurur (erken return: {'_return': deger})."""
    sar = 'def _blok():\n' + textwrap.indent(kod, '    ') + '\n    return locals()\n'
    exec(sar, ns)
    r = ns['_blok']()
    return r if isinstance(r, dict) else {'_return': r}


# ---------------------------------------------------------------- 1 girdi kapilari (motorsuz)
def t_girdi():
    k('isim: EMILY -> EMILY', U.isim_dogrula('EMILY', 'isim1') == 'EMILY')
    k("isim: Mary-Jane / O'Neil buyuk harfe", U.isim_dogrula('Mary-Jane', 'x') == 'MARY-JANE' and U.isim_dogrula("O'Neil", 'x') == "O'NEIL")
    for ad, v in (('rakam', 'EM1LY'), ('aksan', 'Zo\u00e9'), ('bosluk', 'ANNA MARIA'), ('bos', ''), ('emoji', 'EMILY\U0001F600'), ('kenar isaret', '-ANNA'),
                  ('cift isaret', 'MARY--JANE'), ('kivrik kesme', 'O\u2019NEIL'), ('yalniz isaret', "'-'")):
        k(f'bilinen FAIL isim: {ad} -> girdi hatasi', dur_mu(lambda v=v: U.isim_dogrula(v, 'isim1'), 'girdi_isim', True))
    s3 = ['Do you remember our first moonrise?', 'Two hearts, one sky, since 2019.', "We'll keep star-gazing, you & me!"]
    k('metin: 3 satir (35, 32, 33 karakter; rakam . , \' - ? & !) PASS', U.metin_dogrula(s3) == s3 and [len(x) for x in s3] == [35, 32, 33])
    k('metin: 0 satir PASS', U.metin_dogrula([]) == [] and U.metin_dogrula(None) == [])
    k('bilinen FAIL metin: 36 karakter', dur_mu(lambda: U.metin_dogrula(['a' * 36]), 'girdi_metin', True))
    k('metin: tam 35 karakter PASS', U.metin_dogrula(['a' * 35]) == ['a' * 35])
    k('bilinen FAIL metin: 4 satir', dur_mu(lambda: U.metin_dogrula(['a', 'b', 'c', 'd']), 'girdi_metin', True))
    k('bilinen FAIL metin: yalniz noktalama (harf / rakam yok)', dur_mu(lambda: U.metin_dogrula(['...!']), 'girdi_metin', True))
    for ad, v in (('emoji', 'love \U0001F319'), ('aksan', 'caf\u00e9'), ('uzun tire', 'you \u2014 me'), ('iki nokta', 'a: b'), ('kenar boslugu', ' a'),
                  ('bos satir', ''), ('sekme', 'a\tb'), ('kivrik kesme', 'we\u2019ll')):
        k(f'bilinen FAIL metin: {ad}', dur_mu(lambda v=v: U.metin_dogrula([v]), 'girdi_metin', True))
    k('cift: CANCER_LIBRA PASS; ters sira / tek burc FAIL', U.cift_dogrula('cancer_libra') == 'CANCER_LIBRA'
      and dur_mu(lambda: U.cift_dogrula('LIBRA_CANCER'), 'girdi_cift', True) and dur_mu(lambda: U.cift_dogrula('CANCER'), 'girdi_cift', True))
    with tempfile.TemporaryDirectory() as td:                                 # komut satiri: girdi hatasi = cikis 3, agir is baslamadan
        ortak = ['uret', '--cift', 'CANCER_LIBRA', '--yerlesim', 'halkalar', '--katman', td + '/yok.png', '--motor', td, '--cikti', td, '--ad', 'T']
        k('bilinen FAIL komut: 36 karakterlik satir -> cikis 3', U.main(ortak + ['--isim1', 'EMILY', '--isim2', 'JAMES', '--satir', 'a' * 36]) == 3)
        k('bilinen FAIL komut: 4 satir -> cikis 3', U.main(ortak + ['--isim1', 'EMILY', '--isim2', 'JAMES'] + ['--satir', 'a'] * 4) == 3)
        k('bilinen FAIL komut: isimde rakam -> cikis 3', U.main(ortak + ['--isim1', 'EM1LY', '--isim2', 'JAMES']) == 3)
        k('bilinen FAIL komut: bilinmeyen yerlesim -> cikis 3', U.main(ortak[:3] + ['--yerlesim', 'kare'] + ortak[5:] + ['--isim1', 'A', '--isim2', 'B']) == 3)
        k('DUR.json yazildi (girdi_hatasi true)', json.loads((Path(td) / 'T_DUR.json').read_text())['girdi_hatasi'] is True)


# ---------------------------------------------------------------- 2 sembol bicimi (motorsuz)
def sahte_sembol(yol, boy=1700, mod='RGBA', esnet=1.0):
    """dokulu altin halka (RGBA). boy: kare kenar; cevre yaricapi ~ 0,46 x boy."""
    yy, xx = np.mgrid[0:boy, 0:int(boy * esnet)].astype(np.float32)
    cx, cy = boy * esnet / 2, boy / 2
    r = np.hypot((xx - cx) / esnet, yy - cy)
    a = np.clip((0.46 * boy - r), 0, 1) * np.clip(r - 0.33 * boy, 0, 1)
    doku = 150 + 60 * np.sin(xx / 37.0) * np.cos(yy / 23.0) + 25 * (yy / boy)
    rgb = np.stack([doku + 40, doku * 0.8 + 10, doku * 0.35], -1)
    rgba = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, 'RGBA')
    (im if mod == 'RGBA' else im.convert(mod)).save(yol)
    return yol


def t_sembol(td):
    iyi = sahte_sembol(td / 'iyi_ana.png')
    Path(str(iyi) + '.json').write_text(json.dumps(dict(x=1, y=2, w=1700, h=1700, pay=150, not_='metin')))
    g, olc = U.sembol_yukle(iyi)
    k('sembol: RGBA 1700 px PASS; olcum (mod, boyut, iki esikte alfa kutusu, yan json sayisal alanlari)',
      olc['mod'] == 'RGBA' and olc['boyut'] == [1700, 1700] and len(olc['kutu_alfa_05']) == 4 and len(olc['kutu_alfa_002']) == 4
      and olc['yan_json'] == dict(x=1, y=2, w=1700, h=1700, pay=150) and max(olc['olcek'].values()) <= 1.0, olc)
    k('bilinen FAIL sembol: RGB (alfasiz) -> girdi hatasi', dur_mu(lambda: U.sembol_yukle(sahte_sembol(td / 'rgb_ana.png', mod='RGB')), 'sembol_bicim', True))
    k('bilinen FAIL sembol: 100x100 -> girdi hatasi (buyutme yok)', dur_mu(lambda: U.sembol_yukle(sahte_sembol(td / 'kucuk_ana.png', boy=100)), 'sembol_bicim', True))
    k('bilinen FAIL sembol: dosya yok -> girdi hatasi', dur_mu(lambda: U.sembol_yukle(td / 'yok.png'), 'sembol_yok', True))
    k('komut sembol: PASS cikis 0 + SEMBOL_OLCUM.json; RGB cikis 3 + olcum yine yazilir',
      U.main(['sembol', '--katman', str(iyi), '--cikti', str(td / 's1')]) == 0 and json.loads((td / 's1' / 'SEMBOL_OLCUM.json').read_text())['mod'] == 'RGBA'
      and U.main(['sembol', '--katman', str(td / 'rgb_ana.png'), '--cikti', str(td / 's2')]) == 3
      and json.loads((td / 's2' / 'SEMBOL_OLCUM.json').read_text())['mod'] == 'RGB')
    rgb, a, x, y, b = U.sembol_yerlestir(g, olc, 300.0)
    k05 = U.kutu(a, 0.5)
    k('sembol yerlesimi: es oranli (en boy farki <= 0,005), cevre yaricapi hedefe +- 1 px, merkez (0, 0)',
      b['en_boy_fark'] <= 0.005 and abs(np.hypot((k05[2] - k05[0]) / 2, 0) - 300) < 3 and abs(x + (k05[0] + k05[2]) / 2) <= 0.5 and b['olcek'] <= 1, b)
    k('bilinen FAIL sembol: hedef yaricap kaynaktan buyuk -> DUR (buyutme yok)', dur_mu(lambda: U.sembol_yerlestir(g, olc, 2000.0), 'sembol_olcek', False))


# ---------------------------------------------------------------- 3 ay verisi (ephem)
def t_veri():
    g = U.ay_verisi(2027)
    v = U.veri_kapisi(g)
    k('veri kapisi 2027: 365 gun, 13 yeni ay, 12 dolunay', v['PASS'] and (v['gun'], v['yeni'], v['dolun']) == (365, 13, 12), v)
    k('bilinen FAIL veri: bir gun eksik', not U.veri_kapisi(g[:-1])['PASS'])
    g2 = [dict(x) for x in g]; next(x for x in g2 if x['yeni'])['yeni'] = False
    k('bilinen FAIL veri: bir yeni ay eksik', not U.veri_kapisi(g2)['PASS'])
    k('bilinen FAIL veri: yil 2026 (12 / 13 sayimi tutsa da yil farkli)', not U.veri_kapisi(U.ay_verisi(2026), 2026)['PASS'])
    # bagimsiz saglama: ortalama kavusum ayi (29,530588853 gun; referans yeni ay 2000-01-06 18:14 UTC) ile +- 1 gun
    import datetime
    ref = datetime.datetime(2000, 1, 6, 18, 14)
    yeni = [datetime.date(2027, x['ay'], x['gun']) for x in g if x['yeni']]
    sapma = []
    for d in yeni:
        gun = (datetime.datetime(d.year, d.month, d.day, 12) - ref).total_seconds() / 86400
        sapma.append(abs(gun / 29.530588853 - round(gun / 29.530588853)) * 29.530588853)
    k('yeni ay tarihleri ortalama kavusum ayiyla +- 1 gun (bagimsiz saglama)', max(sapma) <= 1.0, [round(s, 2) for s in sapma])
    ok = True
    for i, x in enumerate(g):
        if x['yeni'] and 0 < i < len(g) - 1:
            ok &= x['oran'] < 0.03 and g[i + 1]['buyuyor'] and not g[i - 1]['buyuyor']
        if x['dolun'] and 0 < i < len(g) - 1:
            ok &= x['oran'] > 0.97 and g[i - 1]['buyuyor'] and not g[i + 1]['buyuyor']
    k('yeni ay gunu oran < 0,03 ve sonrasi buyuyor; dolunay gunu oran > 0,97 ve sonrasi kuculuyor', ok)
    k('ay uzunluklari 31 28 31 30 31 30 31 31 30 31 30 31', [sum(1 for x in g if x['ay'] == m) for m in range(1, 13)] == [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    return g


# ---------------------------------------------------------------- 4 geometri (motorsuz; veri gerekir)
def t_geometri(g):
    kutu12 = [(170, 60)] * 12
    for ad in U.YERLESIM:
        hr = U.SEMBOL_ORAN * U.YERLESIM[ad]['sembol_alan'] * U.S
        Y, kat, iz = U.yerlesim_bul(ad, g, kutu12, hr)
        dd, _ = U.disk_disk_bosluk(Y['disk'], Y['r_tot'])
        yd = min(U.kutu_disk_bosluk((x - 85, y - 30, x + 85, y + 30), Y['disk'], Y['r_tot']) for x, y in Y['ay_yeri'])
        k(f'{ad}: 365 disk, 12 ay yeri; disk-disk >= 6, yazi-disk >= 12, sembol-disk >= 150 (katsayi {kat})',
          Y['disk'].shape == (365, 3) and len(Y['ay_yeri']) == 12 and dd >= 6 and yd >= 12 and iz[-1]['sembol_disk'] >= 150, iz[-1])
        k(f'{ad}: isaret halkasi 25 gunde (13 + 12); dis yaricap = r + {U.ISARET_DIS * U.S}',
          int(Y['isaret'].sum()) == 25 and np.allclose(Y['r_tot'] - Y['disk'][:, 2], np.where(Y['isaret'], U.ISARET_DIS * U.S, 0)))
        Yb, katb, izb = U.yerlesim_bul(ad, g, kutu12, hr, katsayi=0.60)        # bilinen FAIL baslangic: buyuk katsayi
        k(f'bilinen FAIL {ad}: katsayi 0,60 bosluk tutmaz -> YALNIZ katsayi 0,01 adimla kuculur ({katb}), disk merkezleri ayni',
          izb[0]['disk_disk'] < 6 and katb < 0.60 and len(izb) > 1 and np.allclose(Yb['disk'][:, :2], U.yerlesim_kur(ad, g, 0.10)['disk'][:, :2])
          and all(abs(izb[i]['katsayi'] - izb[i + 1]['katsayi'] - 0.01) < 1e-9 for i in range(len(izb) - 1)), izb[-1])
    H = U.yerlesim_kur('halkalar', g, 0.36)
    r1 = np.hypot(H['disk'][0, 0], H['disk'][0, 1])
    k('halkalar: OCAK r 775 x3, ARALIK r 290 x3, 1. gun acisi -70 derece, disk r = adim x 0,36',
      abs(r1 - 775 * 3) < 1e-6 and abs(np.hypot(*H['disk'][-1, :2]) - 290 * 3) < 1e-6
      and abs(np.degrees(np.arctan2(H['disk'][0, 1], H['disk'][0, 0])) + 70) < 1e-6 and abs(H['disk'][0, 2] - 485 / 11 * 0.36 * 3) < 1e-9)
    R = U.yerlesim_kur('rozet', g, 0.34)
    k('rozet: disk r = 0,34 x 2 pi x 140 / 31 x3; OCAK cemberi saat 12 (merkez R 640 x3)',
      abs(R['disk'][0, 2] - 0.34 * 2 * np.pi * 140 / 31 * 3) < 1e-9 and abs(R['ay_yeri'][0][0]) < 1e-6 and abs(R['ay_yeri'][0][1] + 640 * 3) < 1e-6)
    Sp = U.yerlesim_kur('spiral', g, 0.36)
    ar = np.hypot(np.diff(Sp['disk'][:, 0]), np.diff(Sp['disk'][:, 1]))
    k('spiral: r 300 -> 770 x3, esit yay araligi (sapma < %2), 1 Ocak en icte saat 12',
      abs(np.hypot(*Sp['disk'][0, :2]) - 900) < 1e-3 and abs(np.hypot(*Sp['disk'][-1, :2]) - 2310) < 1e-3 and ar.std() / ar.mean() < 0.02
      and abs(Sp['disk'][0, 0]) < 1e-6 and Sp['disk'][0, 1] < 0, (ar.min(), ar.max()))
    G = U.yerlesim_kur('girdap', g, 0.36)
    k('girdap: kol 1 ilk gun r 290 x3 saat 12; 31. gun r 735 x3, supurme 150 derece',
      abs(np.hypot(*G['disk'][0, :2]) - 870) < 1e-6 and abs(G['disk'][0, 0]) < 1e-6 and abs(np.hypot(*G['disk'][30, :2]) - 2205) < 1e-6
      and abs((np.degrees(np.arctan2(G['disk'][30, 1], G['disk'][30, 0])) + 90) % 360 - 150) < 1e-6)
    k('kutu-disk boslugu: bilinen degerler (yan 10 px; kose; binme negatif)',
      abs(U.kutu_disk_bosluk((0, 0, 10, 10), np.array([[30.0, 5.0]]), np.array([10.0])) - 10) < 1e-9
      and abs(U.kutu_disk_bosluk((0, 0, 10, 10), np.array([[13.0, 14.0]]), np.array([2.0])) - 3) < 1e-9
      and U.kutu_disk_bosluk((0, 0, 10, 10), np.array([[5.0, 5.0]]), np.array([2.0])) < 0)
    for n in range(4):                                                        # karar 8: yeniden ortalama
        D = U.dikey_yerlesim(150.0, -2300.0, 2400.0, n)
        son = D['metin_taban'][-1] if n else D['cy'] + 2400
        k(f'dikey yerlesim {n} satir: blok sayfa ortasinda (+- 0,01 px), sira isim < baslik < cember < metin',
          abs((D['ust'] + D['alt']) / 2 - U.H / 2) < 0.01 and abs(D['alt'] - son) < 1e-6 and D['isim_taban'] < D['baslik_taban'] < D['cy'] - 2300
          and len(D['metin_taban']) == n, D)
    a0, a3 = U.dikey_yerlesim(150.0, -2300.0, 2400.0, 0), U.dikey_yerlesim(150.0, -2300.0, 2400.0, 3)
    k('metin yokken cember asagi kayar (yeniden dengeleme): cy(0 satir) > cy(3 satir)', a0['cy'] > a3['cy'] + 100, (a0['cy'], a3['cy']))
    k('cizim katsayisi: 53 -> 6, 75 -> 4, 150 -> 2, 90 -> 3, 298 -> 1', [U.cizim_katsayisi(c) for c in (53, 75, 150, 90, 298)] == [6, 4, 2, 3, 1])


# ---------------------------------------------------------------- 5 kapi betigi: sahte kosu (motorsuz), bilinen PASS + her kapi icin bilinen FAIL
def sahte_kosu(td, ad, font, gunler, **m):
    """Kucuk tuvalde (2000x3000) kapi betiginin bekledigi dosyalari kurar: 365 disk (gercek ay verisi), sembol, 1 isim satiri, baslik,
    12 ay adi, 1 metin satiri. m: mutasyonlar (bilinen FAIL)."""
    Wt, Ht = 2000, 3000
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:Ht, 0:Wt].astype(np.float32)
    uz = np.hypot(xx - 1000, yy - 1500) / 1900
    zem = np.stack([8 + 0 * xx, 14 + 6 * (1 - uz), 70 - 40 * uz], -1)
    img = np.clip(zem + rng.normal(0, 1.0, zem.shape), 0, 255).astype(np.uint8)
    del zem, yy, xx, uz
    dmask = np.zeros((Ht, Wt), np.uint8); emask = np.zeros((Ht, Wt), np.uint8); ymask = np.zeros((Ht, Wt), np.uint8)
    diskler = []
    for i, g in enumerate(gunler):
        if m.get('gun_eksik') and i == 200:
            continue
        x, y = 411.0 + (i % 20) * 62, 1330.0 + (i // 20) * 62
        if m.get('disk_degiyor') and i == 5:
            x += 30
        isr = bool(g['yeni'] or g['dolun'])
        if m.get('halka_eksik') and isr and i < 40:
            isr = False
        diskler.append((x, y, 20.0, isr, i))
        U.disk_ciz(img, dmask, x, y, 20.0, g['oran'], (not g['buyuyor']) if m.get('evre_ters') else g['buyuyor'], isr)
    altinsiz = img.copy()
    kay = sahte_sembol(td / f'{ad}_kaynak_ana.png')
    g_, olc = U.sembol_yukle(kay)
    s_rgb, s_a, s_x, s_y, s_b = U.sembol_yerlestir(g_, olc, 120.0)
    del g_
    if m.get('sembol_esnet'):
        s_a = cv2.resize(s_a, (int(s_a.shape[1] * 1.03), s_a.shape[0]), interpolation=cv2.INTER_AREA)
        s_rgb = cv2.resize(s_rgb, (s_a.shape[1], s_a.shape[0]), interpolation=cv2.INTER_AREA)
    if m.get('olcek_buyuk'):
        s_b = dict(s_b, olcek=1.2)
    sx, sy = 1000 + s_x, (720 if not m.get('sembol_disk') else 1330 - 35 - 120 - 100) + s_y
    Lana = np.median(U.labf(s_rgb[s_a >= 0.9]), 0)
    if m.get('renk_kay'):
        Lana = Lana + np.array([8.0, 0, 0], np.float32)

    def altin(A):
        h, w = A.shape
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        l = 150 + 55 * np.sin(gx / 9.0) + 25 * np.cos(gy / 5.0)
        if m.get('duz'):
            l = np.full((h, w), 170, np.float32)
        return np.clip(np.stack([l + 45, l * 0.8 + 10, l * 0.35], -1), 0, 255).astype(np.float32)
    isim_metni = 'EMILY & JAMES'
    if m.get('isim_genis'):                                                   # %86'dan genis ama tuvale sigan satir
        isim_metni = 'W'
        while U.kutu(U.metin_alfa(isim_metni, font, 80.0)[0])[2] - U.kutu(U.metin_alfa(isim_metni, font, 80.0)[0])[0] <= 0.86 * Wt + 20:
            isim_metni += 'W'
    metin = 'It Began With a Kiss'
    if m.get('metin_genis'):
        metin = 'W'
        while U.kutu(U.metin_alfa(metin, font, 44.0)[0])[2] - U.kutu(U.metin_alfa(metin, font, 44.0)[0])[0] <= 0.86 * Wt + 20:
            metin += 'W'
    # (ad, tur, metin, buyuk harf, murekkep sol ust x merkez | None = ortali, murekkep ust y | None = taban Ht - 300)
    tanim = [('isimler', 'isim', isim_metni, 80.0, None, 300), ('baslik', 'baslik', 'MOON PHASES 2027', 40.0, None, 440 if not m.get('altin_binme') else 320)]
    for i, ay in enumerate(U.AYLAR):
        tanim.append((f'ay_{i + 1:02d}', 'ay', ay, 40.0 if not (m.get('kucuk_oge') and i == 0) else 9.0, 375 + (i % 6) * 250, 1050 + (i // 6) * 90))
    tanim.append(('metin_1', 'metin', metin, 44.0, None, None))
    if m.get('ay_eksik'):
        tanim = [t for t in tanim if t[0] != 'ay_07']
    ogeler, boya_oge = [], [dict(x=sx, y=sy, rgb=s_rgb if not m.get('sembol_boya') else s_rgb * 0.8, m=s_a)]
    if m.get('sembol_kenar'):                                                 # yalniz yari saydam kenar pikselleri boyanir (tam alfa ayni)
        kn = ((s_a > 0.02) & (s_a < 0.999))[..., None]
        boya_oge[0]['rgb'] = np.where(kn, s_rgb * np.array([0.5, 1.0, 1.6], np.float32), s_rgb).astype(np.float32)
    for oad, tur, mt_, cap, xm, yu in tanim:
        A, taban = U.metin_alfa(mt_, font, cap)
        kk = U.kutu(A)
        x = int(round((1000 if xm is None else xm) - (kk[0] + kk[2]) / 2))
        y = yu - kk[1] if yu is not None else int(round((Ht - 300 + m.get('blok_kay', 0)) - taban))
        if oad == 'ay_01' and m.get('disk_yakin'):                            # 4. gun diskinin (isaretsiz) 6 px ustune
            x, y = int(round(diskler[3][0] - (kk[0] + kk[2]) / 2)), int(round(diskler[3][1] - 20 - 6 - kk[3]))
        if oad == 'ay_02' and m.get('yazi_kenarda'):
            x = 40
        if oad == 'ay_03' and m.get('altin_disk_ustu'):
            x, y = int(diskler[0][0] - 30), int(diskler[0][1] - 20)
        kat = altin(A)
        uy = dict(piksel=int((A >= 0.9).sum()))
        if (A >= 0.9).sum() >= U.UYUM_MIN_PIKSEL:
            kat, uy = U.renk_uyum(kat, A, Lana)
        if m.get('kontrast_dusuk'):
            kat = kat * 0.10 + np.array([8, 14, 60], np.float32)
        at = A.copy() if not m.get('alfa_boz') else np.clip(cv2.GaussianBlur(A, (0, 0), 2.5) * 1.1, 0, 1)
        ogeler.append(dict(ad=oad, tur=tur, x=x, y=y, gen=int(A.shape[1]), yuk=int(A.shape[0]), cap=cap if not (m.get('cap_kucuk') and tur == 'isim') else 40.0,
                           k=2, punto=10, taban_y=y + taban + (m.get('taban_kay', 0) if tur == 'metin' else 0),
                           karakter=len(mt_) if not (m.get('uzun_satir') and tur == 'metin') else 36, uyum=uy, yari_kal=2.0, ic_oran=0.5, A=A, at=at))
        boya_oge.append(dict(x=x, y=y, rgb=kat, m=A, ic=None))
    if m.get('yildiz_altin'):                                                 # isim satirinin 5 px ustunde yildiz
        o0 = ogeler[0]
        ys0, xs0 = np.nonzero(o0['A'] > 0.5)                                    # murekkebin en ust noktasi
        mu, xk = o0['y'] + int(ys0.min()), o0['x'] + int(xs0[ys0 == ys0.min()][0])
        img[mu - 10:mu - 4, xk:xk + 10] = (240, 220, 160); altinsiz = img.copy()
        ymask[mu - 10:mu - 4, xk:xk + 10] = 255
    son = U.boya(img, boya_oge)
    if m.get('disk_altin'):                                                   # altin disi ogeye altin renk bulasir
        son[int(diskler[1][1]) - 8:int(diskler[1][1]) + 8, int(diskler[1][0]) - 8:int(diskler[1][0]) + 8] = (212, 170, 60)
    if m.get('disk_degisti'):                                                 # altindan uzak bir disk son dosyada koyulasmis (altin renk degil)
        son[int(diskler[300][1]) - 6:int(diskler[300][1]) + 6, int(diskler[300][0]) - 6:int(diskler[300][0]) + 6] //= 2
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    kw = dict(dpi=(300, 300), icc_profile=icc)
    if m.get('dpi_yok'):
        kw.pop('dpi')
    if m.get('icc_yok'):
        kw.pop('icc_profile')
    Image.fromarray(son).save(td / f'{ad}.png', compress_level=1, **kw)
    dump = dict(disk_maske=dmask, diger_maske=emask, yildiz_maske=ymask, sembol_a=s_a.astype(np.float32), sembol_rgb=s_rgb.astype(np.float32), altinsiz=altinsiz)
    for i, o in enumerate(ogeler):
        dump[f'm_{i}'] = o.pop('A').astype(np.float32); dump[f't_{i}'] = o.pop('at').astype(np.float32)
    np.savez(td / f'{ad}_DUMP.npz', **dump)
    meta = dict(ad=ad, yerlesim='sahte', tuval=[Wt, Ht], sembol=dict(olcum=olc, yerlesim=s_b, x=sx, y=sy), ogeler=ogeler,
                isim=dict(harf=[5, 5], kuculme_orani=1.0), metin=dict(satir=1 if not m.get('satir_4') else 4, karakter=[20]),
                disk=dict(katsayi=0.36, liste=[[x, y, r, r + (U.ISARET_DIS * U.S if isr else 0), gi] for x, y, r, isr, gi in diskler]),
                altin=dict(k={o['ad']: 2 for o in ogeler}))
    (td / f'{ad}_META.json').write_text(json.dumps(meta, default=float))
    return kay


def t_disk(gunler):
    """disk_ciz: evre yonu ve alani (bilinen PASS + ters yon bilinen FAIL), isaret halkasi."""
    def ciz(oran, buyuyor, isaret=False, r=47.0):
        im = np.zeros((200, 200, 3), np.uint8); mk = np.zeros((200, 200), np.uint8)
        U.disk_ciz(im, mk, 100.0, 100.0, r, oran, buyuyor, isaret)
        g = dict(oran=oran, buyuyor=buyuyor, yeni=isaret, dolun=False)
        return im, mk, KP.evre_olc(im, [[100.0, 100.0, r, r + (15 if isaret else 0), 0]], [g])
    for oran in (0.25, 0.5, 0.75):
        for buy in (True, False):
            im, mk, e = ciz(oran, buy)
            acik = (np.abs(im.astype(int) - np.array(U.RENK_ACIK)).sum(2) < 60)
            xs = np.nonzero(acik)[1]
            k(f"disk_ciz oran {oran} {'buyuyen: aydinlik SAGDA' if buy else 'kuculen: aydinlik SOLDA'}; olculen aydinlik alan orani +- 0,05; evre olcumu PASS",
              ((xs.mean() > 100) == buy) and e['oran_fark_en_buyuk'] <= 0.05 and e['PASS'], (xs.mean(), e))
    im, mk, _ = ciz(0.3, True)
    ters = KP.evre_olc(im, [[100.0, 100.0, 47.0, 47.0, 0]], [dict(oran=0.3, buyuyor=False, yeni=False, dolun=False)])
    k('bilinen FAIL evre olcumu: cizim buyuyen, veri kuculen -> yon hatasi', not ters['PASS'] and ters['yon_hatasi'] == [0])
    yanlis = KP.evre_olc(im, [[100.0, 100.0, 47.0, 47.0, 0]], [dict(oran=0.7, buyuyor=True, yeni=False, dolun=False)])
    k('bilinen FAIL evre olcumu: cizim 0,3, veri 0,7 -> oran farki > 0,15', not yanlis['PASS'] and yanlis['oran_fark_en_buyuk'] > 0.15)
    im0, _, e0 = ciz(0.0, True, True); im1, _, e1 = ciz(1.0, False)
    k('disk_ciz: yeni ay (oran 0) tum koyu + isaret halkasi; dolunay (oran 1) tum aydinlik', e0['PASS'] and e1['PASS']
      and not (np.abs(im0[80:120, 80:120].astype(int) - np.array(U.RENK_ACIK)).sum(2) < 60).any()
      and (np.abs(im1[80:120, 80:120].astype(int) - np.array(U.RENK_ACIK)).sum(2) < 60).all(), (e0, e1))
    hk = KP.evre_olc(im0, [[100.0, 100.0, 47.0, 62.0, 0]], [dict(oran=0.0, buyuyor=True, yeni=False, dolun=False)])
    k('bilinen FAIL evre olcumu: isaret halkasi var ama gun yeni ay / dolunay degil', not hk['PASS'] and hk['halka_hatasi'] == [0])
    _, mk, _ = ciz(0.4, True, True)
    k('disk maskesi: isaret halkasi dahil dis yaricap (r + 15)', abs(np.sqrt((mk > 0).sum() / np.pi) - 62) < 1.0)
    G = U.yerlesim_kur('girdap', gunler, 0.36)
    uz = [np.hypot(G['ay_yeri'][m][0] - G['disk'][max(i for i, x in enumerate(gunler) if x['ay'] == m + 1)][0],
                   G['ay_yeri'][m][1] - G['disk'][max(i for i, x in enumerate(gunler) if x['ay'] == m + 1)][1]) for m in range(12)]
    k('girdap: ay adi son gun diskinin 58 x3 px otesinde (kol tegeti yonunde, disa dogru)', np.allclose(uz, 58 * 3, atol=1e-6)
      and all(np.hypot(*G['ay_yeri'][m]) > np.hypot(*G['disk'][max(i for i, x in enumerate(gunler) if x['ay'] == m + 1)][:2]) for m in range(12)), uz[:3])


def t_kapi(td, font, gunler):
    eski = (U.W, U.H)
    U.W, U.H = 2000, 3000                                                     # sahte kosu tuvali (kapi 10 ve %86 siniri bu tuvale gore)
    try:
        kay = sahte_kosu(td, 'iyi', font, gunler)
        r = KP.kapi_olc(td, 'iyi', kay)
        k('sahte kosu (bilinen PASS): 10 kapinin hepsi PASS', r['ozet']['PASS'], {a: v['PASS'] for a, v in r['kapi'].items()})
        k('bilinen PASS olcumleri makul: dE00 < 2, kontrast > 4,5, alfa farki 0, duz yayilim > esik, evre farki <= 0,15',
          r['ozet']['en_kotu_dE00'] < 2 and r['ozet']['en_kotu_kontrast'] > 4.5 and r['ozet']['en_kotu_alfa_fark'] == 0
          and r['ozet']['en_dusuk_duz_yayilim'] > KP.ESIK['duz_yayilim'] and r['kapi']['1_veri']['evre']['oran_fark_en_buyuk'] <= 0.15,
          (r['ozet'], r['kapi']['1_veri']['evre']))
        beklenen = [('evre_ters', '1_veri', 'aydinlik taraf ters cizilmis'), ('halka_eksik', '1_veri', 'yeni ay / dolunay gununde isaret halkasi yok'),
                    ('gun_eksik', '1_veri', 'bir gunun diski yok (364 disk)'),
                    ('duz', '7_altin', 'duz renkle cizilmis yazi'), ('renk_kay', '3_tek_doku', 'yazi rengi sembolden kaymis (L +8)'),
                    ('kucuk_oge', '3_tek_doku', 'oge cekirdegi < 200 piksel'), ('ay_eksik', '3_tek_doku', '11 ay adi (oge sayimi)'),
                    ('kontrast_dusuk', '4_kontrast', 'yazi zemine yakin koyulukta'), ('alfa_boz', '5_yazim', 'renk cizimi alfasi sekilden farkli'),
                    ('disk_yakin', '6_bosluk', 'ay diski altin yaziya 12 px\'ten yakin'), ('disk_degiyor', '6_bosluk', 'komsu diskler arasi < 6 px'),
                    ('sembol_disk', '6_bosluk', 'sembol en yakin diske 150 px\'ten yakin'), ('altin_binme', '6_bosluk', 'iki altin oge birbirine biniyor'),
                    ('yazi_kenarda', '6_bosluk', 'altin yazi sayfa kenarina 180 px\'ten yakin'), ('altin_disk_ustu', '6_bosluk', 'altin yazi diskin ustunde'),
                    ('altin_disk_ustu', '7_altin', 'altin yazi diskin ustunde (altin disi ogede altin)'),
                    ('disk_altin', '7_altin', 'ay diskinde altin renk'), ('disk_degisti', '7_altin', 'altindan uzak disk pikseli son dosyada degismis'),
                    ('yildiz_altin', '7_altin', 'yildiz altin yaziya 12 px\'ten yakin'),
                    ('sembol_esnet', '2_sembol', 'sembol yatay %3 esnetilmis'), ('sembol_boya', '2_sembol', 'sembol rengi son dosyada degismis'),
                    ('sembol_kenar', '2_sembol', 'sembolun yari saydam kenar pikselleri boyanmis'), ('olcek_buyuk', '2_sembol', 'olcek > 1 (buyutme)'),
                    ('isim_genis', '8_isim', 'isim satiri %86\'dan genis'), ('cap_kucuk', '8_isim', 'isim buyuk harfi < 53 px'),
                    ('blok_kay', '9_metin', 'blok dikey ortadan 40 px kaymis'), ('uzun_satir', '9_metin', '36 karakterlik satir'),
                    ('satir_4', '9_metin', 'satir sayisi META ile tutarsiz'), ('metin_genis', '9_metin', 'metin satiri %86\'dan genis'),
                    ('taban_kay', '9_metin', 'metin tabani murekkeple tutarsiz'),
                    ('dpi_yok', '10_cikti', 'dpi etiketi yok'), ('icc_yok', '10_cikti', 'sRGB profili yok')]
        onbellek = {}
        for mut, kapi, ack in beklenen:
            if mut not in onbellek:
                kay2 = sahte_kosu(td, 'm_' + mut, font, gunler, **{mut: 40 if mut in ('blok_kay', 'taban_kay') else True})
                onbellek[mut] = KP.kapi_olc(td, 'm_' + mut, kay2)
                if mut != 'duz':
                    for f in td.glob(f'm_{mut}*'):
                        f.unlink()
            r2 = onbellek[mut]
            k(f'bilinen FAIL kapi {kapi}: {ack}', not r2['ozet']['PASS'] and kapi in r2['ozet']['fail'], r2['ozet']['fail'])
        U.W, U.H = 2000, 3001
        rb = KP.kapi_olc(td, 'iyi', kay)
        U.W, U.H = 2000, 3000
        k('bilinen FAIL kapi 10_cikti: tuval boyutu beklenenden farkli', '10_cikti' in rb['ozet']['fail'])
        baska = sahte_sembol(td / 'baska_ana.png', boy=1800)
        r3 = KP.kapi_olc(td, 'iyi', baska)
        k('bilinen FAIL kapi 2_sembol: --katman baska dosya (yerlesen sembol kaynagin kucultulmusu degil)',
          '2_sembol' in r3['ozet']['fail'] and r3['kapi']['2_sembol']['kaynak_sha_ayni'] is False)
        # komut satiri: FAIL -> cikis 1, --onek ile gorseller KAPI_FAIL_ onekli; PASS -> cikis 0
        k('kapi komutu: PASS cikis 0, OLCUM.json yazildi', KP.main([str(td), 'iyi', '--katman', str(kay)]) == 0 and (td / 'iyi_OLCUM.json').is_file())
        k('kapi komutu: FAIL cikis 1 ve --onek ile PNG KAPI_FAIL_ onekli',
          KP.main([str(td), 'm_duz', '--onek']) == 1 and (td / 'KAPI_FAIL_m_duz.png').is_file() and not (td / 'm_duz.png').exists())
        oz = td / 'oz'; oz.mkdir()
        shutil.copy(td / 'iyi_OLCUM.json', oz / 'iyi_OLCUM.json'); shutil.copy(td / 'm_duz_OLCUM.json', oz / 'm_duz_OLCUM.json')
        (oz / 'x_DUR.json').write_text(json.dumps(dict(kod='isim_kucuk', neden='deneme')))
        k('ozet komutu: OZET.json (2 ornek, 1 DUR, cikis kodlari)', KP.main(['--ozet', str(oz), '--kosu', '1', '--rc', 'kapi=1,test=0']) == 0
          and (lambda o: sorted(o['ornek']) == ['iyi', 'm_duz'] and o['ornek']['iyi']['PASS'] and not o['ornek']['m_duz']['PASS']
               and 'x' in o['dur'] and o['cikis'] == dict(kapi='1', test='0'))(json.loads((oz / 'OZET.json').read_text())))
    finally:
        U.W, U.H = eski
    k('emsal esikleri degismedi: dE00 2,0 / kontrast 4,5 / alfa farki 0,035 / 200 piksel',
      (KP.ESIK['dE00'], KP.ESIK['kontrast'], KP.ESIK['alfa_fark'], KP.ESIK['cekirdek_piksel'], U.UYUM_MIN_PIKSEL) == (2.0, 4.5, 0.035, 200, 200))
    k('Merkez baslangic esikleri: yazi-disk 12, disk-disk 6, sembol-disk 150, kenar 180, %86, 53 px, +- 6 px',
      (KP.ESIK['yazi_disk'], KP.ESIK['disk_disk'], KP.ESIK['sembol_disk'], KP.ESIK['kenar'], KP.ESIK['gen_oran'], KP.ESIK['cap_min'], KP.ESIK['blok_merkez'])
      == (12, 6, 150, 180, 0.86, 53, 6) and (U.BOSLUK_YAZI_DISK, U.BOSLUK_DISK_DISK, U.BOSLUK_SEMBOL_DISK, U.BOSLUK_KENAR, U.GEN_ORAN, U.CAP_AY) == (12, 6, 150, 180, 0.86, 53))


# ---------------------------------------------------------------- 6 is akisi kabuk adimlari (sahte rclone, bash -e)
SAHTE_RCLONE = r'''#!/bin/bash
# sahte rclone: gercek aracin bu is akisinda kullanilan davranisi (resmi belge): copy SRC DST [--include F]... ; lsf DIR [--files-only]
# lsf --files-only olmadan klasorleri de "ad/" diye listeler. Davranis SAHTE_MOD ile bozulur (bilinen FAIL).
kom="$1"; shift
case "$kom" in
  copy)
    src="$1"; dst="$2"; shift 2
    [ "${SAHTE_MOD:-}" = "copy_hata" ] && exit 1
    if [[ "$src" == gdrive,* ]]; then
      mkdir -p "$dst"
      for a in "$@"; do case "$a" in /*_ana.png) f="${a#/}"
          case "${SAHTE_MOD:-}" in inmedi) : ;; bos) : > "$dst/$f" ;; *) echo PNG > "$dst/$f" ;; esac ;;
        /*_ana.png.json) f="${a#/}"; [ "${SAHTE_MOD:-}" = "json_yok" ] || echo '{}' > "$dst/$f" ;; esac; done
      [ "${SAHTE_MOD:-}" = "fazla" ] && echo x > "$dst/FAZLA.png"
      exit 0
    fi
    mkdir -p "$SAHTE_DRIVE"; cp "$src"/* "$SAHTE_DRIVE"/ ;;
  lsf)
    ls -1 "$SAHTE_DRIVE" | { if [ "${SAHTE_MOD:-}" = "eksik" ]; then tail -n +2; else cat; fi; }
    case " $* " in *" --files-only "*) : ;; *) echo "altklasor/" ;; esac ;;
  *) exit 2 ;;
esac
'''


def t_is_akisi(yml, td):
    import yaml
    wf = yaml.safe_load(Path(yml).read_text())
    adimlar = {s.get('name'): s for s in wf['jobs']['ornek']['steps'] if s.get('name')}
    k('is akisi: yalniz workflow_dispatch; ust izin {}; is izni contents: read + actions: read; ubuntu-24.04; Etsy / token / artifact adimi yok',
      list(wf[True].keys()) == ['workflow_dispatch'] and wf['permissions'] == {} and wf['jobs']['ornek']['permissions'] == dict(contents='read', actions='read')
      and wf['jobs']['ornek']['runs-on'] == 'ubuntu-24.04' and not re.search(r'ETSY|etsy|upload-artifact|kilit_bekle', Path(yml).read_text().split('jobs:', 1)[1]))
    k('is akisi: motor 6da763a ve ornament c950151627 sabit sha; python 3.13; paket sabitleri + ephem 4.2.1',
      wf['env']['MOTOR_SHA'] == '6da763aa5b9820027420f73264fc69d30e120a33' and wf['env']['ORNAMENT_SHA'] == 'c950151627b4aba29bdea8f75e4c533cea599424'
      and all(p in adimlar['Paketler (ornament ortami + ephem)']['run'] for p in ('pillow==11.0.0', 'numpy==2.5.4', 'opencv-python-headless==5.0.0.93',
                                                                                  'scipy==1.18.1', 'scikit-image==0.26.0', 'potracer==0.0.4', 'ephem==4.2.1')))
    son = [s.get('name') for s in wf['jobs']['ornek']['steps']][-1]
    k('is akisi: son adim always() temizlik (rclone.conf + gecici dosyalar)', son == 'Temizlik' and 'always()' in adimlar['Temizlik']['if']
      and '~/.config/rclone' in adimlar['Temizlik']['run'] and '/tmp/ay' in adimlar['Temizlik']['run'])
    kutu_ = td / 'kabuk'; (kutu_ / 'bin').mkdir(parents=True)
    (kutu_ / 'bin' / 'rclone').write_text(SAHTE_RCLONE); os.chmod(kutu_ / 'bin' / 'rclone', 0o755)
    (kutu_ / 'bin' / 'sleep').write_text('#!/bin/bash\nexit 0\n'); os.chmod(kutu_ / 'bin' / 'sleep', 0o755)

    def kos(ad, env=None, yerine=None):
        """adimin kabuk metni is akisinin kabuguyla: varsayilan 'bash -e' (betik dosyasi)."""
        metin = adimlar[ad]['run']
        for a_, b_ in (yerine or {}).items():
            metin = metin.replace(a_, b_)
        assert '${{' not in metin, f'{ad}: cozulmemis ifade'
        f = kutu_ / 'adim.sh'; f.write_text(metin)
        A = kutu_ / 'ay'
        e = dict(PATH=f"{kutu_ / 'bin'}:{Path(sys.executable).parent}:{os.environ['PATH']}", HOME=str(kutu_), A=str(A), SAHTE_DRIVE=str(kutu_ / 'drive'), GITHUB_ENV=str(kutu_ / 'env.txt'),
                 CIFT='CANCER_LIBRA')
        e.update(env or {})
        p = subprocess.run(['bash', '-e', str(f)], env=e, capture_output=True, text=True, cwd=str(KOK))
        return p.returncode, p.stdout + p.stderr
    tam = dict(ONAY='AY-ORNEK-CL', GITHUB_RUN_ATTEMPT='1', GITHUB_REF='refs/heads/main')
    k('kabuk Kapi: dogru onay + deneme 1 + ref main -> 0', kos('Kapi (onay, deneme 1, ref main)', tam)[0] == 0)
    for ack, deg in (('yanlis onay', dict(ONAY='AY-ORNEK')), ('bos onay', dict(ONAY='')), ('deneme 2 (Re-run)', dict(GITHUB_RUN_ATTEMPT='2')),
                     ('ref main degil', dict(GITHUB_REF='refs/heads/ay-takvim-plan')), ('bos ref', dict(GITHUB_REF='')), ('bos deneme no', dict(GITHUB_RUN_ATTEMPT=''))):
        rc, cikti = kos('Kapi (onay, deneme 1, ref main)', dict(tam, **deg))
        k(f'bilinen FAIL kabuk Kapi: {ack} -> cikis != 0 ve DUR satiri', rc != 0 and 'title=DUR' in cikti, (rc, cikti[-200:]))
    ad = 'Sembol katmani (Drive\'dan yalniz 2 dosya)'

    def sembol(mod='', **e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True)
        return kos(ad, dict(SAHTE_MOD=mod, **e))
    k('kabuk Sembol: 2 dosya indi -> 0', sembol()[0] == 0)
    k('kabuk Sembol: Drive\'dan yalniz <CIFT>_ana.png ve .json istenir (--include iki desen, --max-depth 1)',
      adimlar[ad]['run'].count('--include') == 2 and '--max-depth 1' in adimlar[ad]['run'] and adimlar[ad]['run'].count('rclone copy') == 1)
    for ack, mod, env in (('sembol inmedi', 'inmedi', {}), ('sembol bos dosya', 'bos', {}), ('yan json yok', 'json_yok', {}), ('3 dosya (fazla)', 'fazla', {}),
                          ('rclone hata', 'copy_hata', {}), ('CIFT bos', '', dict(CIFT=''))):
        rc, cikti = sembol(mod, **env)
        k(f'bilinen FAIL kabuk Sembol: {ack} -> cikis != 0', rc != 0, (rc, cikti[-200:]))
    ad = "Drive'a yaz"

    def drive(mod='', n=5, **e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True); shutil.rmtree(kutu_ / 'drive', ignore_errors=True)
        (kutu_ / 'ay' / 'yukle').mkdir(parents=True)
        for i in range(n):
            (kutu_ / 'ay' / 'yukle' / f'd{i}.png').write_text('x')
        return kos(ad, {**dict(SAHTE_MOD=mod, GITHUB_RUN_ID='123'), **e})
    rc, cikti = drive()
    k('kabuk Drive: 5 dosya yuklendi, sayi tutuyor -> 0 ve DRIVE_YOLU satiri (ASTROLOVE/TEMP/AY_TAKVIM_ORNEK_<UTC>_<kosu no>)',
      rc == 0 and re.search(r'title=DRIVE_YOLU::ASTROLOVE/TEMP/AY_TAKVIM_ORNEK_\d{8}_\d{4}_123 \| 5 dosya', cikti), (rc, cikti[-300:]))
    for ack, mod, n, env in (('Drive dosya sayisi eksik', 'eksik', 5, {}), ('yukleme 3 denemede basarisiz', 'copy_hata', 5, {}), ('yuklenecek dosya yok', '', 0, {}),
                             ('kosu no bos', '', 5, dict(GITHUB_RUN_ID=''))):
        rc, cikti = drive(mod, n, **env)
        k(f'bilinen FAIL kabuk Drive: {ack} -> cikis != 0', rc != 0 and 'title=DUR' in cikti, (rc, cikti[-200:]))
    rc, cikti = kos(ad, dict(GITHUB_RUN_ID='123'), yerine={' --files-only': ''})
    k('bilinen FAIL kabuk Drive: --files-only kaldirilirsa klasor satiri sayiyi bozar -> cikis != 0', rc != 0)
    iyi = dict(SEMBOL_RC='0', TEST_RC='0', URETIM_RC='0', KAPI_RC='0', GIRDI_RC='0')
    yer = {'${{ steps.drive.outcome }}': 'success'}
    k('kabuk Sonuc: tum cikislar 0 + drive success -> 0', kos('Sonuc', iyi, yer)[0] == 0)
    for ack, deg, yr in (('kapi FAIL', dict(KAPI_RC='1'), yer), ('test FAIL', dict(TEST_RC='1'), yer), ('uretim DUR', dict(URETIM_RC='1'), yer),
                         ('girdi hatasi', dict(GIRDI_RC='1'), yer), ('sembol olcumu FAIL', dict(SEMBOL_RC='3'), yer),
                         ('drive basarisiz', {}, {'${{ steps.drive.outcome }}': 'failure'}), ('drive atlandi', {}, {'${{ steps.drive.outcome }}': 'skipped'})):
        rc, cikti = kos('Sonuc', dict(iyi, **deg), yr)
        k(f'bilinen FAIL kabuk Sonuc: {ack} -> cikis != 0 (kosu kirmizi)', rc != 0 and 'title=DUR' in cikti, (rc, cikti[-200:]))
    rc, cikti = kos('Sonuc', {}, yer)
    k('bilinen FAIL kabuk Sonuc: cikis kodlari hic yazilmamis (bos) -> cikis != 0', rc != 0)
    um = adimlar['Uretim + kapilar (4 ornek)']['run']
    k('is akisi ornek seti: 4 ornek, metinler ve isimler gorev metniyle ayni',
      all(s in um for s in ('ORNEK_1_halkalar --isim1 EMILY --isim2 JAMES --yerlesim halkalar --satir "It Began With a Kiss in the Rain"',
                            'ORNEK_2_spiral --isim1 EMILY --isim2 JAMES --yerlesim spiral\n', '--satir "Do you remember our first moonrise?"',
                            '--satir "Two hearts, one sky, since 2019."', '--satir "We\'ll keep star-gazing, you & me!"',
                            'ORNEK_4_rozet --isim1 ALEXANDRINA --isim2 CHRISTOPHER --yerlesim rozet --satir "Our first year under one roof" --satir "Lisbon, June 14, 2027"')))
    def paket(**e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True)
        c = kutu_ / 'ay' / 'cikti'; c.mkdir(parents=True)
        for ad_ in ('ORNEK_1_halkalar.png', 'ORNEK_1_halkalar_onizleme.jpg', 'KAPI_FAIL_ORNEK_2_spiral.png', 'ORNEK_1_halkalar_DUMP.npz', 'SEMBOL_OLCUM.json',
                    'ORNEK_3_girdap_DUR.json'):
            (c / ad_).write_text('{"kod": "x", "neden": "y"}' if ad_.endswith('.json') else 'x')
        (kutu_ / 'ay' / 'onb').mkdir(); (kutu_ / 'ay' / 'onb' / 'HARITA.pkl').write_text('x')
        rc_, cikti_ = kos('Paket (yuklenecek dosyalar; DUMP ve onbellek haric)', dict(MOTOR_SHA='m', ORNAMENT_SHA='o', GITHUB_RUN_ID='7', GITHUB_SHA='s', **e))
        return rc_, cikti_, sorted(p_.name for p_ in (kutu_ / 'ay' / 'yukle').iterdir()) if (kutu_ / 'ay' / 'yukle').is_dir() else []
    rc, cikti, dosyalar = paket(TEST_RC='0', SEMBOL_RC='0', URETIM_RC='0', KAPI_RC='1', GIRDI_RC='0')
    k('kabuk Paket: gorseller + OLCUM / DUR json + OZET.json; DUMP.npz ve onbellek YOK; test PASS iken onek eklenmez',
      rc == 0 and dosyalar == ['KAPI_FAIL_ORNEK_2_spiral.png', 'ORNEK_1_halkalar.png', 'ORNEK_1_halkalar_onizleme.jpg', 'ORNEK_3_girdap_DUR.json', 'OZET.json',
                               'SEMBOL_OLCUM.json'], (rc, dosyalar, cikti[-300:]))
    rc, cikti, dosyalar = paket(TEST_RC='1', SEMBOL_RC='0', URETIM_RC='0', KAPI_RC='0', GIRDI_RC='0')
    k('kabuk Paket: test FAIL iken gorseller TEST_FAIL_ onekli (KAPI_FAIL_ onekli olan ayni kalir); temiz adli gorsel kalmaz',
      rc == 0 and 'TEST_FAIL_ORNEK_1_halkalar.png' in dosyalar and 'TEST_FAIL_ORNEK_1_halkalar_onizleme.jpg' in dosyalar and 'KAPI_FAIL_ORNEK_2_spiral.png' in dosyalar
      and 'ORNEK_1_halkalar.png' not in dosyalar, (rc, dosyalar))
    rc, cikti, dosyalar = paket(SEMBOL_RC='0')
    k('kabuk Paket: TEST_RC hic yazilmamis (bos) -> gorseller TEST_FAIL_ onekli (bos deger PASS sayilmaz)', 'TEST_FAIL_ORNEK_1_halkalar.png' in dosyalar, dosyalar)
    um2 = adimlar['Uretim + kapilar (4 ornek)']['run']
    k('is akisi: kapi betigi cokerse (cikis 0 / 1 disi) gorseller KAPI_COKUS_ onekiyle isaretlenir; test logu annotation uretmez (sed)',
      'KAPI_COKUS_' in um2 and '[ "$r" != "0" ] && [ "$r" != "1" ]' in um2 and "sed 's/^::/ ::/'" in adimlar['Testler (motor + ornament kaynagiyla esdegerlik; atlanan test FAIL)']['run'])
    pk = adimlar['Paket (yuklenecek dosyalar; DUMP ve onbellek haric)']['run']
    k('is akisi paket: DUMP.npz ve onbellek yuklenmez; yalniz png / jpg / OLCUM / META / DUR json', 'DUMP' not in pk.replace('DUMP ve', '') and "'*.npz'" not in pk and 'onb' not in pk)


# ---------------------------------------------------------------- 7 motorlu testler: tasinan adimlarin kaynakla esdegerligi
def t_motor(md, od, td):
    md, od = Path(md), Path(od)
    src = {}
    for ad in KAYNAK_SHA:
        f = (md if ad == 'uret_tam.py' else od) / ad
        ok = f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() == KAYNAK_SHA[ad]
        k(f'kaynak sha sabit: {ad}', ok)
        src[ad] = f.read_text() if f.is_file() else ''
    if not all(src.values()):
        return
    OM, O1, O5, OA, SG, UT = (src[a] for a in ('ornament_motor.py', 'ornament_ornek.py', 'ornament_ornek5.py', 'ornament_altin.py', 'siparis_girdi.py', 'uret_tam.py'))
    mt = U.Motor(md)
    gm = mt.gm
    sus = lambda *a, **kw: None                                               # noqa: E731
    # --- sabitler
    Pk = next(d for d in ast.parse(UT).body if isinstance(d, ast.Assign) and getattr(d.targets[0], 'id', '') == 'P')
    k('P_VARSAYILAN == motor uret_tam.py P (satir 10)', {kw.arg: ast.literal_eval(kw.value) for kw in Pk.value.keywords} == U.P_VARSAYILAN)

    def sabit(kaynak, ad):
        d = next(d for d in ast.parse(kaynak).body if isinstance(d, ast.Assign) and getattr(d.targets[0], 'id', '') == ad)
        return {kw.arg: ast.literal_eval(kw.value) for kw in d.value.keywords}
    icg = sabit(OA, 'IC_GOLGE')
    k('DIS_GOLGE / IC_GOLGE == ornament_altin.py (:34-35)', sabit(OA, 'DIS_GOLGE') == U.DIS_GOLGE and {a: icg[a] for a in ('kayma', 'sigma', 'guc')} == U.IC_GOLGE, icg)
    k('ISIM_DESEN == ornament siparis_girdi.py (:29); 200 piksel ve QS == ornament_motor.py',
      "ISIM_DESEN = re.compile(r\"[A-Za-z'\\-]+\", re.ASCII)" in SG and U.ISIM_DESEN.pattern == "[A-Za-z'\\-]+" and 'if m.sum() < 200:' in OM
      and 'QS = [2, 5, 25, 50, 75, 95, 98]' in OM and U.QS == [2, 5, 25, 50, 75, 95, 98])
    k('KILIT: esit kazanc, harita dogrusal, gren 1,0, kenar_yum 0,5, yildiz refkopya, zemin_daire 1 (uretimin varsaydigi dallar)',
      mt.P['esit'] == 'kazanc' and mt.P['harita'] == 'dogrusal' and mt.P['gren'] == 1.0 and mt.P['kenar_yum'] == 0.5 and mt.P['yildiz'] == 'refkopya'
      and mt.P['zemin_daire'] == 1 and mt.VEK is True)
    # --- metin_alfa, rgba_olcek, kontrast (ornament_ornek.py)
    n1 = dict(np=np, cv2=cv2, Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont)
    for ad in ('olcek', 'rgba_olcek', 'metin_alfa', 'kontrast'):
        exec(ic_fonk(O1, ad), n1)
    FI, FM = mt.font_isim, mt.font_metin
    es = True
    for metin, f, cap, w, ref in (('EMILY & JAMES', FI, 150, 500, 'H'), ('MOON PHASES 2027', FI, 75, 500, 'H'), ('JAN', FI, 53, 500, 'H'),
                                  ("We'll keep star-gazing, you & me!", FM, 90, None, 'T'), ('ALEXANDRINA & CHRISTOPHER', FI, 131.7, 500, 'H')):
        a_, t_ = U.metin_alfa(metin, f, cap, w, ref)
        b_, u_ = n1['metin_alfa'](metin, f, cap, w, ref)
        es &= ayni(a_, b_) and t_ == u_
    k('esdegerlik metin_alfa == ornament_ornek.py metin_alfa (5 metin, 2 font; bayt bayt)', es)
    rr = np.random.default_rng(1)
    g4 = np.dstack([rr.random((301, 417, 3), np.float32) * 255, rr.random((301, 417), np.float32)])
    e1 = U.rgba_olcek(g4, 0.3713); e2 = n1['rgba_olcek'](g4, 0.3713)
    k('esdegerlik rgba_olcek == ornament_ornek.py rgba_olcek (bayt bayt)', ayni(e1[0], e2[0]) and ayni(e1[1], e2[1]))
    # --- metin_alfa_k (ornament_motor.py metin_alfa10)
    n2 = dict(np=np, cv2=cv2, Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont, K10=10, PUNTO={})
    exec(ic_fonk(OM, 'metin_alfa10'), n2)
    es = True
    for metin, f, cap, w, ref in (('EMILY', FI, 28.2, 500, 'H'), ('JUNE 14, 2025', FM, 144 / 169.5 * 28.2, None, 'T'), ('JAN', FI, 21.0, 500, 'H')):
        es &= ayni(U.metin_alfa_k(metin, f, cap, 10, w, ref)[0], n2['metin_alfa10'](metin, f, cap, w, ref))
    k('esdegerlik metin_alfa_k(k=10) == ornament_motor.py metin_alfa10 (3 metin; bayt bayt)', es)
    a1, _ = U.metin_alfa('JAN', FI, 53, 500); a6, _ = U.metin_alfa_k('JAN', FI, 53, 6, 500)
    k('metin_alfa_k cercevesi 1x cercevenin TAM k kati (k = 6) ve kucultulmus hali 1x cizime yakin (ort. alfa farki <= 0,035)',
      a6.shape == (a1.shape[0] * 6, a1.shape[1] * 6)
      and float(np.abs(cv2.resize(a6, (a1.shape[1], a1.shape[0]), interpolation=cv2.INTER_AREA) - a1)[(a1 > 0.02)].mean()) <= 0.035)
    # --- golgele_oge, gorunen, cekirdek_Y (ornament_motor.py)
    n3 = dict(np=np, cv2=cv2, gm=gm, P=mt.P, Kk=mt.K, VEK=mt.VEK, VEK_OGE=mt.VEK_OGE, yon_alani=mt.yon_alani)
    for ad in ('golgele_oge', 'gorunen', 'cekirdek_Y'):
        exec(ic_fonk(OM, ad), n3)
    yz8 = np.clip(np.round(U.metin_alfa_k('Rain', FM, 60, 4, None, 'T')[0] * 255), 0, 255).astype(np.uint8)
    y1, y2 = mt.golgele_oge(yz8, 'yazi'), n3['golgele_oge'](yz8, 'tagline')
    k('esdegerlik golgele_oge (yazi, egim_tup yolu) == ornament_motor.py golgele_oge (bayt bayt)', ayni(y1[0], y2[0]) and ayni(y1[1], y2[1]))
    v1, v2 = mt.golgele_oge(yz8, 'ana'), n3['golgele_oge'](yz8, 'ana')
    k('esdegerlik golgele_oge (ana, vektor yolu) == ornament_motor.py golgele_oge (bayt bayt); iki yol farkli sonuc verir',
      ayni(v1[0], v2[0]) and ayni(v1[1], v2[1]) and not np.array_equal(v1[0], y1[0]))
    k('esdegerlik gorunen == ornament_motor.py gorunen', ayni(mt.gorunen(y1[0], y1[1]), n3['gorunen'](y1[0], y1[1])))
    # --- palet + poster ana + harita (ornament_motor.py :148-151, :208-231)
    n4 = dict(np=np, cv2=cv2, Image=Image, os=os)
    exec(blok(OM, '# palet (uret_tam 143-147)', "log('palet'"), n4)
    k('esdegerlik palet (ref_ana) == ornament_motor.py :148-151', ayni(mt.ref_ana, n4['ref_ana']))
    n5 = dict(n3, Image=Image, json=json, MD=md, POSTER_ALFA='girdi78/ana/cancer_libra_alfa.png', CIFT='CANCER_LIBRA', temizle=mt.temizle, ref_ana=n4['ref_ana'], log=sus)
    exec(blok(OM, '# --- poster ana (renk haritasi icin)', "log('harita'"), n5)
    hr = mt.harita_kur('CANCER_LIBRA')
    har, qa_goz = hr['har'], hr['qa_goz']
    k('esdegerlik harita_kur (poster ana alfasi -> har, qa_goz) == ornament_motor.py :208-231 (bayt bayt)',
      len(har) == len(n5['har']) and all((ayni(x, y) if isinstance(x, np.ndarray) else x == y) for x, y in zip(har, n5['har'])) and ayni(qa_goz, n5['qa_goz']),
      (har[1:6], n5['har'][1:6]))
    hr2 = mt.harita_kur('CANCER_LIBRA', td / 'onb'); hr3 = mt.harita_kur('CANCER_LIBRA', td / 'onb')
    k('harita onbellegi: ikinci okuma ayni sonucu verir', ayni(hr2['qa_goz'], hr3['qa_goz']) and ayni(hr3['har'][7], har[7]) and len(list((td / 'onb').glob('HARITA_*.pkl'))) == 1)
    # --- oge_katman (ornament_motor.py :455-492 dongusu)
    AD_MOTOR = {'kucuk_sol': 'kucuk1', 'kucuk_sag': 'kucuk2', 'sonsuz': 'sonsuz', 'isim1': 'isim1', 'isim2': 'isim2', 'tarih': 'tagline', 'halka': 'cember'}
    A10 = {}
    for ad, (metin, f, cap, w, ref) in zip(AD_MOTOR, (('C', FI, 22, 500, 'H'), ('L', FI, 22, 500, 'H'), ('O', FI, 20, 500, 'H'), ('EMILY', FI, 28.2, 500, 'H'),
                                                     ('JAMES', FI, 28.2, 500, 'H'), ('June 14', FM, 24, None, 'T'), ('I', FI, 30, 500, 'H'))):
        A10[ad] = U.metin_alfa_k(metin, f, cap, 10, w, ref)[0]
    (td / 'o').mkdir(exist_ok=True)
    n6 = dict(n3, A10=A10, AD_MOTOR=AD_MOTOR, QS=U.QS, qa_goz=qa_goz, har=har, K10=10, lum=KP.lum, log=sus, O=td / 'o')
    exec(blok(OM, '# --- golgeleme + renk (10x), zeminsiz katman, dogrusal kucultme ---', '# tam tuval renkleri (954) ve IoU'), n6)
    rng = np.random.default_rng(11)
    es, benim = True, {}
    for ad in ('kucuk_sol', 'kucuk_sag', 'sonsuz', 'isim1', 'isim2', 'tarih', 'halka'):
        g_, s_, at_ = mt.oge_katman(A10[ad], 10, rng, har, qa_goz, AD_MOTOR[ad])
        benim[ad] = (g_, at_)
        es &= ayni(g_, n6['katman'][ad]) and ayni(at_, n6['Atest'][ad])
    k('esdegerlik oge_katman(k=10) == ornament_motor.py :455-492 (7 oge, ayni rng sirasi; grenli katman + kucultulmus alfa bayt bayt)', es)
    g2, s2, _ = mt.oge_katman(A10['isim1'], 10, np.random.default_rng(3), har, qa_goz)
    k('oge_katman: gren katmani degistirir (grenli != grensiz) ve katman duz renk degil (cekirdek luma p95 - p5 > 12)',
      not np.array_equal(g2, s2) and float(np.ptp(np.percentile(KP.lum(g2[benim['isim1'][1] >= 0.9]), [5, 95]))) > 12)
    # --- altin_ogeler (URETIMIN giris noktasi) == ornament zinciri: metin_alfa10 -> dongu (tum ogeler yazi yolu) -> renk_uyum blogu
    tn = (('CANCER', FI, 30, 500, 'H'), ('LIBRA', FI, 30, 500, 'H'), ('MOON PHASES', FI, 26, 500, 'H'), ('EMILY', FI, 28.2, 500, 'H'),
          ('JAMES', FI, 28.2, 500, 'H'), ('June 14, you & me!', FM, 30, None, 'T'), ('JANUARY', FI, 30, 500, 'H'))
    Nz = 700
    og7, Ar = [], {}
    for i, (ad, (metin, f, cap, w, ref)) in enumerate(zip(AD_MOTOR, tn)):
        A1, _ = U.metin_alfa(metin, f, cap, w, ref)
        og7.append(dict(ad=ad, metin=metin, font=f, wght=w, ref=ref, cap=cap, k=10, A=A1, x=20, y=20 + 90 * i))
        Ar[ad] = n2['metin_alfa10'](metin, f, cap, w, ref)                        # referans k kat alfa: KAYNAK metin_alfa10
    n6b = dict(n3, VEK_OGE=[], A10=Ar, AD_MOTOR=AD_MOTOR, QS=U.QS, qa_goz=qa_goz, har=har, K10=10, lum=KP.lum, log=sus, O=td / 'o')
    for ad in ('golgele_oge', 'gorunen'):
        exec(ic_fonk(OM, ad), n6b)                                              # VEK_OGE bos: tum ogeler yazi (egim_tup) yolundan
    exec(blok(OM, '# --- golgeleme + renk (10x), zeminsiz katman, dogrusal kucultme ---', '# tam tuval renkleri (954) ve IoU'), n6b)
    sem_rgb, sem_a = benim['sonsuz']
    Yz = dict(E={'sembol': (sem_rgb, sem_a, 0, 0)}, M={})
    CCz = {}
    for o in og7:
        m_ = np.zeros((Nz, Nz), np.float32); c_ = np.zeros((Nz, Nz, 3), np.float32)
        h, w = o['A'].shape
        m_[o['y']:o['y'] + h, o['x']:o['x'] + w] = o['A']; c_[o['y']:o['y'] + h, o['x']:o['x'] + w] = n6b['katman'][o['ad']]
        Yz['M'][o['ad']] = m_; CCz[o['ad']] = c_
    n7b = dict(np=np, cv2=cv2, json=json, log=sus, O=td / 'o')
    exec(ic_fonk(OM, 'de00'), n7b)
    rz = fonk_blok(blok(OM, '    labf = lambda x: cv2.cvtColor', "    log('renk_uyum'"), dict(n7b, Y=Yz, katman=dict.fromkeys(CCz), CC=CCz))
    Lana_u = np.median(U.labf(sem_rgb[sem_a >= 0.9]), 0)                       # uret() icindeki Lana satiri
    n8b = dict(np=np, cv2=cv2)
    from skimage.morphology import skeletonize as _sk
    n8b['skeletonize'] = _sk
    exec(ic_fonk(OM, 'yari_kal'), n8b)
    D_test = 4.0
    bo = U.altin_ogeler(mt, og7, har, qa_goz, Lana_u, D_test)
    es = ayni(Lana_u, rz['Lana'])
    for o, b_ in zip(og7, bo):
        h, w = o['A'].shape
        es &= ayni(b_['rgb'], CCz[o['ad']][o['y']:o['y'] + h, o['x']:o['x'] + w]) and o['uyum'] == rz['ru'][o['ad']] and ayni(o['atest'], n6b['Atest'][o['ad']])
        r_ = min(1.0, n8b['yari_kal'](Ar[o['ad']]) / 10 / D_test)
        es &= b_['ic'] == dict(kayma=1.0 * r_, sigma=0.6 * r_, guc=0.35) and b_['carpan'] == 1.0 and b_['x'] == o['x'] and b_['y'] == o['y'] and b_['m'] is o['A']
    k('esdegerlik altin_ogeler (URETIM giris noktasi; 7 oge, k = 10) == ornament zinciri (kaynak metin_alfa10 -> dongu -> renk_uyum; ic golge formulu; bayt bayt)', es)
    og2 = [dict(o, k=5) for o in og7[:2]]
    b5 = U.altin_ogeler(mt, og2, har, qa_goz, Lana_u, D_test)
    k('altin_ogeler k = 5: cerceve ayni, katman k = 10 ile yakin ama ayni degil (oge basina k kullaniliyor); renk uyumu sonrasi dE00 <= 1',
      b5[0]['rgb'].shape == bo[0]['rgb'].shape and not np.array_equal(b5[0]['rgb'], bo[0]['rgb']) and all(o['uyum']['dE00_sonra'] <= 1.0 for o in og2)
      and float(np.abs(b5[1]['rgb'] - bo[1]['rgb'])[og7[1]['A'] >= 0.9].mean()) < 12)
    # --- renk_uyum (ornament_motor.py :515-531) + de00
    n7 = dict(np=np, cv2=cv2, json=json, log=sus, O=td / 'o')
    exec(ic_fonk(OM, 'de00'), n7)
    rr = np.random.default_rng(2)
    es = all(abs(U.de00(p, q) - n7['de00'](p, q)) == 0 for p, q in zip(rr.random((40, 3)) * [100, 80, 80] - [0, 40, 40], rr.random((40, 3)) * [100, 80, 80] - [0, 40, 40]))
    k('esdegerlik de00 == ornament_motor.py de00 (40 rastgele Lab cifti; fark 0)', es and abs(U.de00((50, 2.5, 0), (50, 0, -2.5)) - 4.3065) < 2e-3)
    N = 420
    srgb_, sa_ = benim['sonsuz'][0], benim['sonsuz'][1]
    Yd = dict(E={'sembol': (srgb_, sa_, 0, 0)}, M={})
    CC = {}
    for i, ad in enumerate(('isim1', 'isim2', 'tarih')):
        m_ = np.zeros((N, N), np.float32); c_ = np.zeros((N, N, 3), np.float32)
        h, w = benim[ad][1].shape
        A1x = cv2.resize(A10[ad], (w, h), interpolation=cv2.INTER_AREA)
        m_[20 + 120 * i:20 + 120 * i + h, 30:30 + w] = A1x; c_[20 + 120 * i:20 + 120 * i + h, 30:30 + w] = benim[ad][0]
        Yd['M'][ad] = m_; CC[ad] = c_
    CC0 = {a_: v.copy() for a_, v in CC.items()}
    r7 = fonk_blok(blok(OM, '    labf = lambda x: cv2.cvtColor', "    log('renk_uyum'"), dict(n7, Y=Yd, katman=dict.fromkeys(CC), CC=CC))
    es = True
    for ad in CC0:
        yeni, olc_ = U.renk_uyum(CC0[ad], Yd['M'][ad], r7['Lana'])
        es &= ayni(yeni, CC[ad]) and olc_ == r7['ru'][ad]
    k('esdegerlik renk_uyum == ornament_motor.py :515-531 (3 oge; kaydirilmis katman bayt bayt + olcum sozlugu)', es and all(v['dE00_sonra'] <= 1.0 for v in r7['ru'].values()))
    kucuk = np.zeros((40, 40), np.float32); kucuk[10:20, 10:25] = 1.0
    k('bilinen FAIL renk_uyum: cekirdek 150 piksel < 200 -> DUR', dur_mu(lambda: U.renk_uyum(np.full((40, 40, 3), 128, np.float32), kucuk, r7['Lana']), 'renk_uyum_piksel', False))
    # --- yari_kal, boya (ornament_motor.py :549-552, f_dus_hesap, boya_motor)
    al = types.SimpleNamespace(DIS_GOLGE=sabit(OA, 'DIS_GOLGE'), DUSUS=sabit(OA, 'DUSUS'), oge_renk=lambda Y_, model_, td_, ad, varyant, kazanc: CC[ad].copy())
    n8 = dict(np=np, cv2=cv2, N=N, CX=N / 2, CY=N / 2, lum=KP.lum, al=al)
    from skimage.morphology import skeletonize
    n8['skeletonize'] = skeletonize
    for ad in ('yari_kal', 'f_dus_hesap', 'boya_motor'):
        exec(ic_fonk(OM, ad), n8)
    k('esdegerlik yari_kal == ornament_motor.py yari_kal', all(U.yari_kal(A10[a_]) == n8['yari_kal'](A10[a_]) for a_ in ('isim1', 'tarih', 'halka')))
    sm = np.zeros((N, N), np.float32); sc = np.zeros((N, N, 3), np.float32)
    sm[330:330 + sa_.shape[0], 200:200 + sa_.shape[1]] = sa_; sc[330:330 + sa_.shape[0], 200:200 + sa_.shape[1]] = srgb_
    Yb = dict(E=dict.fromkeys(['sembol', 'isim1', 'isim2', 'tarih']), M=dict(Yd['M'], sembol=sm)); CC['sembol'] = sc
    yy_, xx_ = np.mgrid[0:N, 0:N].astype(np.float32)
    z = np.clip(np.stack([20 + 0 * xx_, 30 + 0 * xx_, 110 - 80 * np.hypot(xx_ - N / 2, yy_ - N / 2) / N], -1), 0, 255).astype(np.float32)
    icp = {ad: dict(kayma=1.0 * r_, sigma=0.6 * r_, guc=0.35) for ad, r_ in zip(Yb['E'], (1.0, 0.47, 0.47, 0.31))}
    fd = n8['f_dus_hesap'](z); dus = float(np.median(fd[sm >= 0.9]))
    ref, _ = n8['boya_motor'](Yb, None, z, None, 'G2', 1.0, icp, dus)
    tam_ = [dict(x=0, y=0, rgb=CC[ad], m=Yb['M'][ad], ic=icp[ad], carpan=(fd if ad == 'sembol' else dus)) for ad in Yb['E']]
    k('esdegerlik boya (tam tuval cerceveler) == ornament_motor.py boya_motor (deneme 4 ayari: ic golge oranli, kucuk ogede sabit dusus; uint8 bayt bayt)',
      ayni(U.boya(z, tam_), ref))
    yerel = []
    for ad in Yb['E']:
        kx0, ky0, kx1, ky1 = U.kutu(Yb['M'][ad], 0.0)
        kx0, ky0, kx1, ky1 = max(0, kx0 - 3), max(0, ky0 - 3), min(N, kx1 + 3), min(N, ky1 + 3)
        yerel.append(dict(x=kx0, y=ky0, rgb=CC[ad][ky0:ky1, kx0:kx1], m=Yb['M'][ad][ky0:ky1, kx0:kx1], ic=icp[ad], carpan=(fd if ad == 'sembol' else dus)))
    by = U.boya(z, yerel)
    fy = np.abs(by.astype(np.int16) - ref.astype(np.int16)).max(2)
    k('esdegerlik boya (yerel cerceveler, uretimdeki kullanim) == boya_motor (uint8; en cok 5 pikselde 1 seviye: kayan nokta yuvarlamasi)',
      by.shape == ref.shape and int(fy.max()) <= 1 and int((fy > 0).sum()) <= 5,
      (int((fy > 0).sum()), int(fy.max()), [(int(y_), int(x_)) for y_, x_ in zip(*np.nonzero(fy))][:5]))
    dokunma = [dict(o, ic=None, carpan=1.0) if i == 0 else dict(o, carpan=1.0) for i, o in enumerate(yerel)]
    b3 = U.boya(z, dokunma)
    tamalfa = sm >= 0.999
    fark3 = np.abs(b3[tamalfa].astype(np.int16) - np.clip(np.round(sc[tamalfa]), 0, 255).astype(np.int16))
    k('boya uretim ayari: sembol pikselleri DEGISMEZ (alfa >= 0,999 pikselde son dosya = katman rengi, fark <= 1 seviye; ornament ayariyla fark > 1)',
      tamalfa.sum() >= 20 and int(fark3.max()) <= 1 and int(np.abs(ref[tamalfa].astype(np.int16) - np.round(sc[tamalfa]).astype(np.int16)).max()) > 1
      and not np.array_equal(b3, ref), (int(tamalfa.sum()), int(fark3.max())))
    # --- kontrast (ornament_ornek5.py kontrast_yeni, tur 'koyu')
    n9 = dict(np=np, cv2=cv2, lum=KP.lum, o1=types.SimpleNamespace(kontrast=n1['kontrast']))
    for ad in ('kontrast_ham', 'kontrast_yeni'):
        exec(ic_fonk(O5, ad), n9)
    es = True
    for ad in ('isim1', 'tarih'):
        q1 = KP.kontrast_olc(ref, Yb['M'][ad]); q2 = n9['kontrast_yeni'](ref, Yb['M'][ad], 'koyu')
        es &= all(q1[a_] == q2[a_] for a_ in ('deger', 'ortanca_bilgi', 'zemin_rgb', 'oge_rgb', 'cekirdek_piksel'))
    k('esdegerlik kontrast_olc == ornament_ornek5.py kontrast_yeni (tur koyu; deger, ortanca, renkler)', es and KP.kontrast((255, 255, 255), (0, 0, 0)) == 21.0)
    # --- zemin (motor uret_tam.py)
    Wk, Hk = 1440, 2160
    n10 = dict(np=np, cv2=cv2, json=json, W=Wk, H=Hk, P=mt.P, log=sus)
    exec(blok(UT, '# --- 1 zemin: REF radyal profil', "log('zemin')").replace("'/home/claude/blender/zemin_profil.json'", repr(str(md / 'zemin_profil.json'))), n10)
    Zp = json.load(open(md / 'zemin_profil.json'))
    s_ = Wk / Zp['olcek']
    zr = U.zemin_radyal(md, mt.P, Wk, Hk, s_, Zp['cx'] * s_, Zp['cy'] * s_)
    k('esdegerlik zemin_radyal == motor uret_tam.py :18-40 (1440x2160; bayt bayt)', ayni(zr, n10['zemin']))
    k('zemin_radyal: merkezden disa tekduze kararir; merkez kaydirilinca profil kayar (es oranli, esnetme yok)',
      zr[int(Zp['cy'] * s_), int(Zp['cx'] * s_), 2] > zr[10, 10, 2]
      and ayni(U.zemin_radyal(md, mt.P, 400, 400, 2.7, 200.0, 200.0)[100:300, 200], U.zemin_radyal(md, mt.P, 400, 400, 2.7, 200.0, 200.0)[200, 100:300]))
    n11 = dict(np=np, cv2=cv2, Image=Image, W=7200, H=10800, P=mt.P, lineer=gm.lineer, log=sus, zemin=np.zeros((10800, 7200, 3), np.float32))
    exec(blok(UT, "if P['yildiz'] == 'refkopya':", '# --- 3 harita').replace("'/home/claude/ref/ref.png'", repr(str(md / 'ref' / 'ref.png'))), n11)
    h_ref = hashlib.sha256(n11['zemin'].tobytes()).hexdigest(); n_ref = n11['sy']; del n11
    zy = np.zeros((10800, 7200, 3), np.float32)
    n_ben = U.zemin_yildiz(zy, md, gm, 3.6, 0.0, 0.0)
    k(f'esdegerlik zemin_yildiz(f=3,6) == motor uret_tam.py :111-135 (7200x10800 poster; sha256 ayni, {n_ben} yildiz)',
      hashlib.sha256(zy.tobytes()).hexdigest() == h_ref and n_ben == n_ref and n_ben > 0)
    del zy
    zk = np.zeros((7200, 5400, 3), np.float32); mk_ = np.zeros((7200, 5400), np.uint8)
    nk = U.zemin_yildiz(zk, md, gm, 2.7, 0.0, 3600 - Zp['cy'] * 2.7, mk_)
    k('zemin_yildiz ay takvimi (f = 2,7, dikey kayma): yildiz eklenir, tuval disi yama atlanir, maske yildizli pikselleri isaretler',
      0 < nk < n_ben and (mk_ > 0).sum() > 0 and float(zk[mk_ == 0].max()) <= 0.0021 and float(zk.max()) > 0.01, (nk, n_ben, float(zk[mk_ == 0].max())))
    eng = np.zeros((7200, 5400), np.uint8); ys_, xs_ = np.nonzero(mk_)
    eng[ys_[0] - 2:ys_[0] + 3, xs_[0] - 2:xs_[0] + 3] = 255                      # ilk yildizin ustune engel
    zk2 = np.zeros((7200, 5400, 3), np.float32); mk2 = np.zeros((7200, 5400), np.uint8); sy_ = {}
    nk2 = U.zemin_yildiz(zk2, md, gm, 2.7, 0.0, 3600 - Zp['cy'] * 2.7, mk2, eng, sy_)
    k('zemin_yildiz engel: engele degen yildiz yamasi atlanir (sayac), engel bolgesine isik eklenmez, diger yildizlar ayni',
      nk2 < nk and sy_.get('engel', 0) == nk - nk2 and float(zk2[eng > 0].max()) == 0.0 and sy_.get('tuval_disi', 0) == n_ben - nk
      and not (mk2[eng > 0] > 0).any(), (nk, nk2, sy_))
    del zk, mk_, zk2, mk2, eng
    n12 = dict(np=np, cv2=cv2, W=Wk, H=Hk, P=mt.P, srgb=gm.srgb, luma=gm.luma, ZEK={}, ZPL={}, zemin=n10['zemin'].copy())
    exec(blok(UT, '# --- 6 sRGB + TPDF titresim -> 8 bit ---', 'del zemin, ZEK, ZPL'), n12)
    k('esdegerlik zemin_8bit == motor uret_tam.py :371-392 (sRGB + TPDF + gren; uint8 bayt bayt)', ayni(U.zemin_8bit(zr, gm, mt.P), n12['out']))
    # --- isim satiri kuculme yolu (kapi 8) genis harfli sentetik isimle
    for h_ in ('W', 'M'):
        A_, t_, cap_, dn_ = U.isim_sigdir(f"{h_ * 11} & {h_ * 11}", FI)
        kk = U.kutu(A_)
        k(f'isim kuculme: 11 x {h_} & 11 x {h_} kuculur (buyuk harf {cap_:.1f} px, oran {cap_ / 150:.3f}) ve sigar (<= %86), >= 53 px',
          cap_ < 150 and cap_ >= 53 and kk[2] - kk[0] <= 0.86 * U.W and len(dn_) >= 1, (cap_, kk[2] - kk[0]))
    A_, t_, cap_, dn_ = U.isim_sigdir('ALEXANDRINA & CHRISTOPHER', FI)
    k('isim: ALEXANDRINA & CHRISTOPHER (11 + 11 harf) kuculmeden sigar (150 px)', cap_ == 150 and dn_ == [], (cap_, U.kutu(A_)))
    k('bilinen FAIL isim: 40 x W & 40 x W -> buyuk harf 53 px altina iner -> DUR', dur_mu(lambda: U.isim_sigdir(f"{'W' * 40} & {'W' * 40}", FI), 'isim_kucuk', False))
    en = 11
    while True:                                                               # en genis sigan durum (bilgi): W harfiyle kac + kac harf 53 px ustunde kalir
        try:
            U.isim_sigdir(f"{'W' * (en + 1)} & {'W' * (en + 1)}", FI); en += 1
        except U.Dur:
            break
    print(f'BILGI en genis sigan isim satiri (en genis harf W ile): {en} + {en} harf (buyuk harf >= 53 px)', flush=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--motor'); ap.add_argument('--ornament'); ap.add_argument('--is-akisi'); ap.add_argument('--zorunlu', action='store_true')
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        t_girdi()
        t_sembol(td)
        g = None
        try:
            import ephem  # noqa: F401
            g = t_veri()
            t_geometri(g)
        except ModuleNotFoundError:
            atla('ephem paketi yok (ay verisi, geometri)', 30)
        font = KOK / 'sosyal' / 'pin_v6' / 'assets' / 'EBGaramond-Regular.ttf'      # depodaki font (yalniz sahte kosu icin; uretim fontu motor klasorunden)
        if a.motor:
            font = Path(a.motor) / 'font' / 'Cinzel.ttf'
        if g is not None and font.is_file():
            (td / 'kp').mkdir()
            t_disk(g)
            t_kapi(td / 'kp', font, g)
        else:
            atla('sahte kosu icin font ya da ephem yok (kapi betigi testleri)', 25)
        yml = Path(a.is_akisi) if a.is_akisi else KOK / '.github' / 'workflows' / 'ay-takvim-ornek.yml'
        try:
            import yaml  # noqa: F401
            if yml.is_file():
                t_is_akisi(yml, td)
            else:
                atla('is akisi dosyasi yok', 30)
        except ModuleNotFoundError:
            atla('pyyaml yok (is akisi kabuk testleri)', 30)
        if a.motor and a.ornament:
            t_motor(a.motor, a.ornament, td)
        else:
            atla('motor yolu yok', 30)
    top = SAYAC['pas'] + SAYAC['fail']
    print(f"ay_takvim testleri: {SAYAC['pas']}/{top} PASS" + (f", {SAYAC['atla']} test ATLANDI" if SAYAC['atla'] else ''), flush=True)
    return 1 if SAYAC['fail'] or (a.zorunlu and SAYAC['atla']) else 0


if __name__ == '__main__':
    sys.exit(main())
