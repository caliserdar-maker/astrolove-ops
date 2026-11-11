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
    'uret_tam.py': '5a9078ea2ed4496343d1d5fcc3d2c5bfbb38d08d202f63e04430257caa17dfcd',
    'olustur_alfa_sablon.py': 'd67b54a020d749de8ffa4ae9a170fceced111a9105bf46268d456d6a7434f807'}
MOTOR_KAYNAK = ('uret_tam.py', 'olustur_alfa_sablon.py')                     # motor klasorunden okunanlar (digerleri ornament)


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
    t_ayar()


def t_ayar():
    """AYAR sozlugu (Serdar 11 Kas "A"): varsayilan = 2. ornek gorevinin degerleri; bilinen PASS + bilinen FAIL girdileri; hata mesajinda ham girdi yok."""
    v = {y: U.ayar_varsayilan(y) for y in U.AYAR_YERLESIM}
    k('ayar varsayilani = 2. ornek gorevi degerleri (grup ortali, oran 1, alan 205 / 205 / 320, poster yeri, kucuk oran 1, ay adi 53, oto, 150 / 75 / 90, 0,36 / 0,36 / 0,34)',
      all(d['grup_merkez'] == 'grup' and d['grup_oran'] == 1.0 and d['kucuk_u'] == 'poster' and d['kucuk_v'] == 'poster' and d['kucuk_oran'] == 1.0
          and d['ay_adi_cap'] == 53 == U.CAP_AY and d['girdap_ad_uzaklik'] == 'oto' and (d['isim_cap'], d['baslik_cap'], d['metin_cap']) == (150, 75, 90)
          and d['satirlar'] == [] for d in v.values())
      and [v[y]['sembol_alan'] for y in U.AYAR_YERLESIM] == [205, 205, 320] and [v[y]['disk_katsayi'] for y in U.AYAR_YERLESIM] == [0.36, 0.36, 0.34]
      and all(sorted(d) == sorted(U.AYAR_ANAHTAR) for d in v.values()))
    k('ayar: bos sozluk = halkalar varsayilani; verilen anahtar yerine gecer, kalanlar varsayilan',
      U.ayar_dogrula({}) == v['halkalar'] and U.ayar_dogrula(dict(yerlesim='rozet', kucuk_u=0.6, isim1='anna')) == dict(v['rozet'], kucuk_u=0.6, isim1='ANNA'))
    k('ayar: aralik uclari kabul (grup_oran 0,60 / 1,30; ay_adi_cap 30 / 90; girdap uzaklik 58 / 200 / "oto"; isim_cap 75 / 240)',
      all(U.ayar_dogrula({a_: x_})[a_] == x_ for a_, x_ in (('grup_oran', 0.6), ('grup_oran', 1.3), ('ay_adi_cap', 30), ('ay_adi_cap', 90), ('girdap_ad_uzaklik', 58),
                                                           ('girdap_ad_uzaklik', 200), ('girdap_ad_uzaklik', 'oto'), ('isim_cap', 75), ('isim_cap', 240), ('kucuk_v', 'poster'))))
    kotu = [('bilinmeyen anahtar', dict(renk='mavi')), ('aralik disi (grup_oran 1,31)', dict(grup_oran=1.31)), ('aralik disi (ay_adi_cap 29)', dict(ay_adi_cap=29)),
            ('aralik disi (kucuk_u 0,2)', dict(kucuk_u=0.2)), ('aralik disi (sembol_alan 401)', dict(sembol_alan=401)), ('aralik disi (disk_katsayi 0,46)', dict(disk_katsayi=0.46)),
            ('aralik disi (isim_cap 241)', dict(isim_cap=241)), ('yanlis tur (grup_oran metin)', dict(grup_oran='1.0')), ('yanlis tur (bool)', dict(kucuk_oran=True)),
            ('yanlis tur (liste)', dict(sembol_alan=[205])), ('yanlis tur (satirlar metin)', dict(satirlar='a')), ('yanlis tur (isim sayi)', dict(isim1=5)),
            ('serbest sozcuk yanlis (kucuk_u "orta")', dict(kucuk_u='orta')), ('yerlesim spiral (ayarda yok)', dict(yerlesim='spiral')),
            ('yerlesim taninmiyor', dict(yerlesim='kare')), ('grup_merkez taninmiyor', dict(grup_merkez='sol')), ('sonsuz', dict(grup_oran=float('inf'))),
            ('NaN', dict(kucuk_oran=float('nan'))), ('kabuk karakteri iceren isim', dict(isim1='A; rm -rf /')), ('kabuk karakteri iceren satir', dict(satirlar=['$(id)'])),
            ('cok buyuk tam sayi (10^400; cokus degil DUR)', dict(grup_oran=10 ** 400)), ('sozluk degil', [1])]
    for ack, d in kotu:
        k(f'bilinen FAIL ayar: {ack} -> girdi hatasi', dur_mu(lambda d=d: U.ayar_dogrula(d), None, True))
    k('ayar: spiral yalniz komut satiri yolunda (spiral=True) kabul', U.ayar_dogrula(dict(yerlesim='spiral'), spiral=True)['yerlesim'] == 'spiral')
    iz = 'ENJEKTE\n::error::x'
    mesaj = []
    for d in ({iz: 1}, dict(grup_oran=iz), dict(yerlesim=iz), dict(isim1=iz), dict(satirlar=[iz]), dict(grup_merkez=iz), dict(kucuk_u=iz)):
        try:
            U.ayar_dogrula(d); mesaj.append('DUR YOK')
        except U.Dur as e:
            mesaj.append(f'{e.kod}: {e.neden}')
    k('ayar hata mesajinda HAM girdi yok (log komutu enjeksiyonu): yalniz hata turu + anahtar sirasi', all('ENJEKTE' not in m_ and '::' not in m_ and '\n' not in m_ for m_ in mesaj)
      and mesaj[0].endswith('bilinmeyen anahtar #1'), mesaj)
    L = U.ayar_listesi('[{"yerlesim": "girdap", "kucuk_oran": 1.4}, {}]')
    k('ayar listesi: 2 deneme -> TAM sozlukler (varsayilanlar dahil)', len(L) == 2 and L[0]['kucuk_oran'] == 1.4 and L[0]['yerlesim'] == 'girdap' and L[1] == v['halkalar'])
    for ack, m_ in (('7 deneme', json.dumps([{}] * 7)), ('0 deneme', '[]'), ('bozuk JSON', '[{"yerlesim": '), ('4001 karakter', '[{}]' + ' ' * 3997), ('bos', ''),
                    ('liste degil', '{"yerlesim": "girdap"}'), ('NaN sabiti', '[{"grup_oran": NaN}]'), ('2. denemede bilinmeyen anahtar', '[{}, {"x": 1}]'),
                    ('kabuk karakteri iceren deger', '[{"isim1": "`id`"}]'), ('oge sozluk degil', '[1]'),
                    ('yinelenen anahtar (son deger sessizce gecmez)', '[{"grup_oran": 99, "grup_oran": 1.1}]'), ('cok buyuk tam sayi', '[{"sembol_alan": 1' + '0' * 400 + '}]')):
        k(f'bilinen FAIL ayar listesi: {ack} -> girdi hatasi', dur_mu(lambda m_=m_: U.ayar_listesi(m_), 'girdi_ayar' if 'kabuk' not in ack else None, True))
    k('ayar listesi: tam 4000 karakter kabul; hata mesaji deneme ve anahtar sirasini verir (deneme 2: bilinmeyen anahtar #3)',
      len(U.ayar_listesi('[{}]' + ' ' * 3996)) == 1
      and str(_dur(lambda: U.ayar_listesi('[{}, {"isim1": "A", "isim2": "B", "zz": 1}]'))) == 'girdi_ayar: deneme 2: bilinmeyen anahtar #3')
    k('deneme ust siniri kodda: en cok 6 (is akisi zaman asimi 60 dk; sure olcumu ay_takvim_ornek.py basliginda)', U.DENEME_AZAMI == 6 and U.AYAR_UZUNLUK == 4000)
    with tempfile.TemporaryDirectory() as td:
        os.environ['AY_TEST_AYAR'] = '[{"yerlesim": "rozet"}, {"yerlesim": "girdap", "isim1": "Anna"}]'
        rc = U.main(['ayar-dogrula', '--env', 'AY_TEST_AYAR', '--cikti', td])
        k('komut ayar-dogrula: gecerli -> cikis 0; AYAR.json (tam), AYAR_N.txt (2), AYAR_AD.txt (adlar KODDAN: DENEME_<sira>_<yerlesim>)',
          rc == 0 and (Path(td) / 'AYAR_N.txt').read_text() == '2' and (Path(td) / 'AYAR_AD.txt').read_text() == 'DENEME_1_rozet\nDENEME_2_girdap\n'
          and json.loads((Path(td) / 'AYAR.json').read_text())[1]['isim1'] == 'ANNA')
        os.environ['AY_TEST_AYAR'] = '[{"yerlesim": "rozet", "ad": "x/../y"}]'
        td2 = Path(td) / 'b'
        rc = U.main(['ayar-dogrula', '--env', 'AY_TEST_AYAR', '--cikti', str(td2)])
        k('bilinen FAIL komut ayar-dogrula: gecersiz -> cikis 3, AYAR dosyalari YAZILMAZ', rc == 3 and not (td2 / 'AYAR.json').exists() and not (td2 / 'AYAR_N.txt').exists())
        del os.environ['AY_TEST_AYAR']
        ortak = ['uret', '--cift', 'CANCER_LIBRA', '--katman', td + '/yok.png', '--motor', td, '--cikti', td]
        k('bilinen FAIL komut: bilinmeyen mod -> cikis 3', U.main(ortak + ['--ad', 'T', '--yerlesim', 'halkalar', '--isim1', 'A', '--isim2', 'B', '--mod', 'hizli']) == 3)
        k('bilinen FAIL komut: --ayar araligi disi -> cikis 3 (agir is baslamadan)',
          U.main(ortak + ['--ad', 'T', '--yerlesim', 'halkalar', '--isim1', 'A', '--isim2', 'B', '--ayar', '{"grup_oran": 9}']) == 3)
        k('bilinen FAIL komut: ayni anahtar hem komut satirinda hem --ayar icinde -> cikis 3',
          U.main(ortak + ['--ad', 'T', '--yerlesim', 'halkalar', '--isim1', 'A', '--isim2', 'B', '--ayar', '{"isim1": "C"}']) == 3)
        k('bilinen FAIL komut: --ayar-dosya sirasi liste disinda -> cikis 3',
          U.main(ortak + ['--mod', 'deneme', '--ayar-dosya', td + '/AYAR.json', '--sira', '3']) == 3)
        a1 = types.SimpleNamespace(ayar_dosya=None, ayar=None, yerlesim='halkalar', isim1='EMILY', isim2='JAMES', grup_merkez=None, satir=[], ad='X')
        a2 = types.SimpleNamespace(ayar_dosya=None, ayar=json.dumps(U.ayar_varsayilan('halkalar')), yerlesim=None, isim1=None, isim2=None, grup_merkez=None, satir=[], ad='X')
        a3 = types.SimpleNamespace(ayar_dosya=td + '/AYAR.json', sira=2, ad='girdiden/gelen')
        k('etkin ayar: ayarsiz komut satiri == varsayilanlarin TAMAMI acikca verilmis ayar (tek yol; uret yalniz bu sozlugu okur)',
          U.ayar_kur(a1) == U.ayar_kur(a2) == (U.ayar_varsayilan('halkalar'), 'X'))
        k('mod deneme adi KODDAN uretilir (girdiden gelen ad kullanilmaz): DENEME_2_girdap', U.ayar_kur(a3)[1] == 'DENEME_2_girdap')


def _dur(f):
    try:
        f()
    except U.Dur as e:
        return e
    return None


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
    Yd, katd, izd = U.yerlesim_bul('halkalar', g, kutu12, hr, katsayi=0.45, dusur=False)
    k('yerlesim_bul dusur=False (mod deneme): tutmayan katsayi kendiliginden DUSMEZ, tek adim, PASS False yazilir',
      katd == 0.45 and len(izd) == 1 and izd[0]['PASS'] is False and len(izd[0]['yazi_disk_ay']) == 12, izd[0])
    ak = [(U.kutu(U.metin_alfa(ay, KOK / 'sosyal' / 'pin_v6' / 'assets' / 'EBGaramond-Regular.ttf', 53)[0])) for ay in U.AYLAR] \
        if (KOK / 'sosyal' / 'pin_v6' / 'assets' / 'EBGaramond-Regular.ttf').is_file() else None
    kutu_ay = [(q[2] - q[0], q[3] - q[1]) for q in ak] if ak else [(60 + 34 * len(ay), 60) for ay in U.AYLAR]
    uz, yd0 = U.girdap_ad_uzakligi(g, kutu_ay)

    def en_az(u_):
        Yg = U.yerlesim_kur('girdap', g, 0.36, ad_uzak=u_)
        return min(U.kutu_disk_bosluk((x - gw / 2, y - gh / 2, x + gw / 2, y + gh / 2), Yg['disk'], Yg['r_tot']) for (x, y), (gw, gh) in zip(Yg['ay_yeri'], kutu_ay))
    k(f'girdap ad uzakligi aramasi: 58 ref px\'ten 1 adimla, 12 adin hepsi diskten >= 12 px olan EN KUCUK ortak deger ({uz}); bir eksigi tutmaz',
      uz >= 58 and min(yd0) >= 12 and en_az(uz) >= 12 and (uz == 58 or en_az(uz - 1) < 12) and len(yd0) == 12, (uz, min(yd0)))
    k('girdap ad uzakligi: kisa adlarda (JAN .. DEC genisligi) 58 yeter; uzun adlarda artar (tam ay adlari)',
      U.girdap_ad_uzakligi(g, [(170, 60)] * 12)[0] == 58 and U.girdap_ad_uzakligi(g, [(700, 60)] * 12)[0] > 58)
    k('bilinen FAIL girdap ad uzakligi: sayfadan genis ad kutusu hicbir uzaklikta tutmaz -> DUR', dur_mu(lambda: U.girdap_ad_uzakligi(g, [(4000, 4000)] * 12), 'girdap_ad', False))
    Yg1, Yg2 = U.yerlesim_kur('girdap', g, 0.36, ad_uzak=58), U.yerlesim_kur('girdap', g, 0.36, ad_uzak=98)
    d12 = [np.hypot(a_[0] - b_[0], a_[1] - b_[1]) for a_, b_ in zip(Yg1['ay_yeri'], Yg2['ay_yeri'])]
    k('girdap ad uzakligi: ad yalniz kol tegeti yonunde kayar (12 ayda ayni 40 ref px = 120 px), diskler ayni',
      all(abs(d_ - 120) < 1e-6 for d_ in d12) and np.array_equal(Yg1['disk'], Yg2['disk']), d12)
    k('ay adlari kisaltmasiz (Serdar 11 Kas): JANUARY .. DECEMBER, 12 ad', U.AYLAR == ('JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER',
                                                                                      'OCTOBER', 'NOVEMBER', 'DECEMBER'))
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
        tanim.append((f'ay_{i + 1:02d}', 'ay', ay, 40.0 if not (m.get('kucuk_oge') and i == 0) else 9.0, 400 + (i % 4) * 400, 1050 + (i // 4) * 80))      # tam ay adlari: satirda 4 ad
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
        if oad == 'ay_04' and m.get('sembol_ustu'):                           # ay adi sembol halkasinin ust bandinin ustune
            x, y = int(round(1000 - (kk[0] + kk[2]) / 2)), int(round(720 - 103 - (kk[1] + kk[3]) / 2))
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
    grup_meta = None
    if m.get('grup'):                                                         # sahte sembol grubu: halka (r 150, kalinlik 5) + iki kucuk sembol (elips halka)
        gyy, gxx = np.mgrid[0:320, 0:320].astype(np.float32)
        gr = np.hypot(gxx - 160, gyy - 160)
        halka = np.clip(2.5 - np.abs(gr - 150), 0, 1).astype(np.float32)
        kyy, kxx = np.mgrid[0:60, 0:80].astype(np.float32)
        kr = np.hypot((kxx - 40) / 1.4, kyy - 30)
        kucuk = np.clip(6.0 - np.abs(kr - 16), 0, 1).astype(np.float32)
        scx, scy = 1000, sy - s_y
        yerler = [('halka', halka, scx - 160, scy - 160), ('kucuk1', kucuk, scx - 110, scy + 170), ('kucuk2', kucuk, scx + 30, scy + 170)]
        if m.get('grup_disk'):                                                # kucuk2 ilk diskin (isaretsiz, r 20) 100 px soluna
            yerler[2] = ('kucuk2', kucuk, int(411 - 20 - 100 - 80 + 12), 1330 + 62 - 30)
        if m.get('grup_ay'):                                                  # kucuk1 ay_01 murekkebinin 5 px altina
            o1 = next(o for o in ogeler if o['ad'] == 'ay_01'); k1 = U.kutu(o1['A'])
            yerler[1] = ('kucuk1', kucuk, o1['x'] + k1[0], o1['y'] + k1[3] + 5 - 9)
        gog = []
        for gad, GA, gx_, gy_ in yerler:
            kat = altin(GA) if not (m.get('kucuk_duz') and gad == 'kucuk1') else np.full(GA.shape + (3,), (215, 146, 60), np.float32)
            kat, uy = U.renk_uyum(kat, GA, Lana + (np.array([8.0, 0, 0], np.float32) if m.get('halka_renk') and gad == 'halka' else 0))
            if m.get('halka_duz') and gad == 'halka':
                kat = np.broadcast_to(np.median(kat[GA >= 0.9], 0), kat.shape).astype(np.float32).copy()
            if m.get('grup_kontrast') and gad == 'kucuk2':
                kat = kat * 0.10 + np.array([8, 14, 60], np.float32)
            gog.append(dict(ad=gad, motor_ad=gad, x=int(gx_), y=int(gy_), gen=int(GA.shape[1]), yuk=int(GA.shape[0]), k=2, olcek=0.2, hedef=[0, 0], poster=[0, 0], uyum=uy,
                            yari_kal=2.0, ic_oran=0.5, A=GA))
            boya_oge.append(dict(x=int(gx_), y=int(gy_), rgb=kat, m=GA, ic=None))
        if m.get('grup_eksik'):
            gog = gog[:2]; boya_oge = boya_oge[:-1]
        grup_meta = dict(bilgi=dict(merkez='grup', olcek=0.2, halka_merkez_kayma_px=[0, 0], halka_kalinlik_px=5.0, halka_kalinlik_mm=0.42, k=dict(halka=2)),
                         merkez=[scx, scy], ogeler=gog)
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
    if grup_meta:
        for i, o in enumerate(grup_meta['ogeler']):
            A_ = o.pop('A').astype(np.float32)
            dump[f'gm_{i}'] = A_; dump[f'gt_{i}'] = A_
    np.savez(td / f'{ad}_DUMP.npz', **dump)
    ayar = dict(U.ayar_varsayilan('halkalar'), **m.get('ayar', {}))
    meta = dict(ad=ad, mod=m.get('mod', 'ornek'), ayar=ayar, grup=grup_meta, uretim_kontrol=m.get('uretim_kontrol', {}),
                yerlesim='halkalar' if grup_meta else 'sahte', tuval=[Wt, Ht], sembol=dict(olcum=olc, yerlesim=s_b, x=sx, y=sy), ogeler=ogeler,
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
        k('sahte kosu (bilinen PASS): kapilarin hepsi PASS (0 uretim + 10 kapi)', r['ozet']['PASS'] and len(r['kapi']) == 11, {a: v['PASS'] for a, v in r['kapi'].items()})
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
        # --- sembol grubu (Serdar 11 Kas): halka + kucuk semboller kapi 3, 4, 6, 7'de; kapi 2 grup bolumu --motor ister
        kg = sahte_kosu(td, 'g_iyi', font, gunler, grup=True)
        rg = KP.kapi_olc(td, 'g_iyi', kg)
        K_ = rg['kapi']
        k('sahte grup (bilinen PASS): kapi 3, 4, 5, 6, 7 PASS; halka + kucuk1 + kucuk2 tek doku / kontrast olcumunde; grup - disk >= 150, grup - ay adi >= 12',
          all(K_[a]['PASS'] for a in ('3_tek_doku', '4_kontrast', '5_yazim', '6_bosluk', '7_altin')) and all(a in K_['3_tek_doku']['oge'] and a in K_['4_kontrast']['oge']
                                                                                                    for a in ('halka', 'kucuk1', 'kucuk2'))
          and K_['3_tek_doku']['oge_sayisi']['grup'] == 3 and K_['6_bosluk']['sembol_disk'] >= 150 and K_['6_bosluk']['grup_ay_adi_en_az'] >= 12
          and K_['6_bosluk']['sembol_disk_olcum'].startswith('grup') and sorted(K_['5_yazim']['grup_bilgi']) == ['halka', 'kucuk1', 'kucuk2']
          and 'halka' not in K_['7_altin']['duz_renk']['oge'] and K_['7_altin']['duz_renk']['halka_bilgi'] > KP.ESIK['duz_yayilim'],
          ({a: v['PASS'] for a, v in K_.items()}, K_['6_bosluk']['sembol_disk'], K_['6_bosluk']['grup_ay_adi_en_az']))
        k('bilinen FAIL kapi 2_sembol (grup): --motor verilmezse grup kapisi FAIL (atlanamaz)', not K_['2_sembol']['PASS'] and K_['2_sembol']['grup']['PASS'] is False)
        mg_ = json.loads((td / 'g_iyi_META.json').read_text()); mg_['grup'] = None; mg_['ad'] = 'g_yok'
        (td / 'g_yok_META.json').write_text(json.dumps(mg_)); shutil.copy(td / 'g_iyi.png', td / 'g_yok.png'); shutil.copy(td / 'g_iyi_DUMP.npz', td / 'g_yok_DUMP.npz')
        rgy = KP.kapi_olc(td, 'g_yok', kg)
        k('bilinen FAIL kapi 2_sembol (grup): grup yerlesiminde META grup alani silinmis -> FAIL (alan silinerek atlanamaz)',
          '2_sembol' in rgy['ozet']['fail'] and 'META grup alani yok' in rgy['kapi']['2_sembol']['grup']['neden'])
        for mut, kapi, ack, ek in (('kucuk_duz', '7_altin', 'kucuk sembol duz renk', lambda q: q['7_altin']['duz_renk']['oge']['kucuk1'] < KP.ESIK['duz_yayilim']),
                                   ('halka_renk', '3_tek_doku', 'halka rengi sembolden kaymis (L +8)', lambda q: q['3_tek_doku']['oge']['halka']['dE00'] > 2.0),
                                   ('grup_kontrast', '4_kontrast', 'kucuk sembol zemine yakin koyulukta', lambda q: q['4_kontrast']['oge']['kucuk2']['ortanca_bilgi'] < 4.5),
                                   ('grup_disk', '6_bosluk', 'grup (kucuk sembol) diske 100 px', lambda q: 95 <= q['6_bosluk']['sembol_disk'] <= 105),
                                   ('grup_ay', '6_bosluk', 'kucuk sembol ay adina 5 px', lambda q: q['6_bosluk']['grup_ay_adi_en_az'] < 12),
                                   ('grup_eksik', '3_tek_doku', 'grupta 2 oge (halka + 1 kucuk; sayim)', lambda q: q['3_tek_doku']['oge_sayisi']['grup'] == 2)):
            sahte_kosu(td, 'g_' + mut, font, gunler, grup=True, **{mut: True})
            r2 = KP.kapi_olc(td, 'g_' + mut, kg)
            k(f'bilinen FAIL kapi {kapi} (grup): {ack}', kapi in r2['ozet']['fail'] and ek(r2['kapi']), r2['ozet']['fail'])
            for f in td.glob(f'g_{mut}*'):
                f.unlink()
        sahte_kosu(td, 'g_hduz', font, gunler, grup=True, halka_duz=True)
        r2 = KP.kapi_olc(td, 'g_hduz', kg)
        k('halka duz renk: yayilim BILGI olarak yazilir (~0), kapi 7 bu yuzden FAIL vermez (Serdar 11 Kas: halka yayilimi bilgi)',
          r2['kapi']['7_altin']['PASS'] and r2['kapi']['7_altin']['duz_renk']['halka_bilgi'] < 5, r2['kapi']['7_altin']['duz_renk'])
        # --- AYAR ve MOD: kapi ayara bagli degeri META'dan okur; mod deneme'de yalniz sert kapilar cikisi belirler
        sahte_kosu(td, 'a_cap', font, gunler, cap_kucuk=True, ayar=dict(ay_adi_cap=30), mod='deneme')
        ra = KP.kapi_olc(td, 'a_cap', kay, None, 'deneme')
        k('mod deneme: kapi 8 isim alt sinirini META ayarindan okur: isim 40 px, ayar ay_adi_cap 30 -> PASS (varsayilan 53 ile ayni gorsel FAIL: cap_kucuk)',
          ra['kapi']['8_isim']['PASS'] and ra['kapi']['8_isim']['cap_alt_siniri'] == 30 and ra['ozet']['ayar']['ay_adi_cap'] == 30 and ra['kapi']['0_uretim']['PASS'])
        sahte_kosu(td, 'a_cap3', font, gunler, cap_kucuk=True, ayar=dict(ay_adi_cap=30))
        ra = KP.kapi_olc(td, 'a_cap3', kay)
        k('bilinen FAIL mod ornek: META ayari varsayilandan farkli (ay_adi_cap 30) -> kapi 0 FAIL (esik urunden okunarak gevsetilemez)',
          '0_uretim' in ra['ozet']['fail'] and ra['kapi']['0_uretim']['ayar_varsayilan_disi'] == ['ay_adi_cap'])
        ra = KP.kapi_olc(td, 'a_cap', kay)
        k('bilinen FAIL mod uyusmazligi: META mod deneme, kapi mod ornek ile cagrildi -> kapi 0 FAIL ve SERT FAIL (yumusaklik META\'dan alinmaz)',
          '0_uretim' in ra['ozet']['sert_fail'] and ra['kapi']['0_uretim']['mod_tutarli'] is False)
        sahte_kosu(td, 'a_cap2', font, gunler, ayar=dict(ay_adi_cap=90), mod='deneme')
        k('bilinen FAIL kapi 8: ayni gorsel, META ayar ay_adi_cap 90 -> isim 80 px < 90 FAIL', '8_isim' in KP.kapi_olc(td, 'a_cap2', kay, None, 'deneme')['ozet']['fail'])
        sahte_kosu(td, 'd_duz', font, gunler, duz=True, mod='deneme', uretim_kontrol=dict(bosluk=dict(PASS=False, neden='x')))
        k('mod deneme: sert olmayan kapi FAIL (7_altin, 0_uretim) -> OLCUM FAIL yazar, cikis 0, gorsel KALIR',
          KP.main([str(td), 'd_duz', '--katman', str(kay), '--mod', 'deneme']) == 0 and (td / 'd_duz.png').is_file()
          and (lambda o: not o['PASS'] and '7_altin' in o['fail'] and '0_uretim' in o['fail'] and o['sert_fail'] == [] and o['uretim_kontrol_fail'] == ['bosluk']
               and o['mod'] == 'deneme')(json.loads((td / 'd_duz_OLCUM.json').read_text())['ozet']))
        sahte_kosu(td, 'd_esnet', font, gunler, sembol_esnet=True, mod='deneme')
        k('bilinen FAIL mod deneme: sert kapi 2 (sembol sekli) FAIL -> cikis 1, gorsel SILINIR (atlanamaz)',
          KP.main([str(td), 'd_esnet', '--katman', str(kay), '--mod', 'deneme']) == 1 and not (td / 'd_esnet.png').exists()
          and json.loads((td / 'd_esnet_OLCUM.json').read_text())['ozet']['sert_fail'] == ['2_sembol'])
        sahte_kosu(td, 'o_boya', font, gunler, sembol_boya=True, mod='deneme')
        sahte_kosu(td, 'o_ortu', font, gunler, sembol_ustu=True, mod='deneme')
        sahte_kosu(td, 'o_ortu2', font, gunler, sembol_ustu=True)
        ro, ro2 = KP.kapi_olc(td, 'o_ortu', kay, None, 'deneme'), KP.kapi_olc(td, 'o_ortu2', kay)
        k('mod deneme: ay adinin ORTTUGU sembol pikseli renk karsilastirmasina girmez (kapi 2 PASS, binme kapi 6 FAIL); mod ornek ayni gorselde kapi 2 FAIL',
          ro['kapi']['2_sembol']['PASS'] and ro['kapi']['2_sembol']['ortulen_piksel_haric'] > 0 and '6_bosluk' in ro['ozet']['fail']
          and '2_sembol' in ro2['ozet']['fail'] and ro2['kapi']['2_sembol']['ortulen_piksel_haric'] == 0,
          (ro['kapi']['2_sembol']['ortulen_piksel_haric'], ro['ozet']['fail'], ro2['ozet']['fail']))
        k('bilinen FAIL mod deneme: sembolun KENDI rengi degismisse (ortulme yok) kapi 2 yine FAIL', '2_sembol' in KP.kapi_olc(td, 'o_boya', kay, None, 'deneme')['ozet']['sert_fail'])
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
        (oz / 'AYAR.json').write_text(json.dumps([U.ayar_varsayilan('rozet')]))
        k('ozet komutu: OZET.json (2 ornek, 1 DUR, cikis kodlari; mod; her ornegin TAM ayari + dogrulanmis ayar listesi)',
          KP.main(['--ozet', str(oz), '--kosu', '1', '--rc', 'kapi=1,test=0', '--mod', 'deneme']) == 0
          and (lambda o: sorted(o['ornek']) == ['iyi', 'm_duz'] and o['ornek']['iyi']['PASS'] and not o['ornek']['m_duz']['PASS']
               and 'x' in o['dur'] and o['cikis'] == dict(kapi='1', test='0') and o['mod'] == 'deneme'
               and sorted(o['ornek']['iyi']['ayar']) == sorted(U.AYAR_ANAHTAR) and o['ayar_listesi'] == [U.ayar_varsayilan('rozet')])(json.loads((oz / 'OZET.json').read_text())))
    finally:
        U.W, U.H = eski
    k('emsal esikleri degismedi: dE00 2,0 / kontrast 4,5 / alfa farki 0,035 / 200 piksel',
      (KP.ESIK['dE00'], KP.ESIK['kontrast'], KP.ESIK['alfa_fark'], KP.ESIK['cekirdek_piksel'], U.UYUM_MIN_PIKSEL) == (2.0, 4.5, 0.035, 200, 200))
    k('Merkez baslangic esikleri: yazi-disk 12, disk-disk 6, sembol-disk 150, kenar 180, %86, 53 px, +- 6 px',
      (KP.ESIK['yazi_disk'], KP.ESIK['disk_disk'], KP.ESIK['sembol_disk'], KP.ESIK['kenar'], KP.ESIK['gen_oran'], U.ayar_varsayilan('halkalar')['ay_adi_cap'], KP.ESIK['blok_merkez'])
      == (12, 6, 150, 180, 0.86, 53, 6) and 'cap_min' not in KP.ESIK and (KP.ESIK['grup_yazi'], KP.ESIK['grup_konum'], KP.ESIK['grup_konum_olculen']) == (12, 1.0, 2.0) and (U.BOSLUK_YAZI_DISK, U.BOSLUK_DISK_DISK, U.BOSLUK_SEMBOL_DISK, U.BOSLUK_KENAR, U.GEN_ORAN, U.CAP_AY) == (12, 6, 150, 180, 0.86, 53))


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
    gir = wf[True]['workflow_dispatch']['inputs']
    k('is akisi girdileri: onay, mod (choice: ornek | deneme; varsayilan ornek), ayar; girdiler YALNIZ env uzerinden (run satirinda inputs ifadesi yok)',
      sorted(gir) == ['ayar', 'mod', 'onay'] and gir['mod']['type'] == 'choice' and gir['mod']['options'] == ['ornek', 'deneme'] and gir['mod']['default'] == 'ornek'
      and all('github.event.inputs' not in (s_.get('run') or '') for s_ in wf['jobs']['ornek']['steps'])
      and sum('github.event.inputs' in json.dumps(s_.get('env') or {}) for s_ in wf['jobs']['ornek']['steps']) == 2
      and 'MUSTERI VERISI' in Path(yml).read_text().split('on:', 1)[0])
    tam = dict(ONAY='AY-ORNEK-CL2', MOD_GIRDI='ornek', GITHUB_RUN_ATTEMPT='1', GITHUB_REF='refs/heads/main')
    (kutu_ / 'env.txt').write_text('')
    k('kabuk Kapi: mod ornek + AY-ORNEK-CL2 + deneme 1 + ref main -> 0, MOD=ornek yazilir',
      kos('Kapi (onay, deneme 1, ref main)', tam)[0] == 0 and (kutu_ / 'env.txt').read_text() == 'MOD=ornek\n')
    (kutu_ / 'env.txt').write_text('')
    k('kabuk Kapi: mod deneme + AY-DENEME -> 0, MOD=deneme yazilir',
      kos('Kapi (onay, deneme 1, ref main)', dict(tam, MOD_GIRDI='deneme', ONAY='AY-DENEME'))[0] == 0 and (kutu_ / 'env.txt').read_text() == 'MOD=deneme\n')
    (kutu_ / 'env.txt').write_text('')
    for ack, deg in (('eski onay (AY-ORNEK-CL)', dict(ONAY='AY-ORNEK-CL')), ('mod deneme + ornek onayi', dict(MOD_GIRDI='deneme')),
                     ('mod ornek + deneme onayi', dict(ONAY='AY-DENEME')), ('mod bos', dict(MOD_GIRDI='')), ('mod taninmiyor (kabuk karakterli)', dict(MOD_GIRDI='deneme; echo ENJEKTE')),
                     ('yanlis onay', dict(ONAY='AY-ORNEK')), ('bos onay', dict(ONAY='')), ('deneme 2 (Re-run)', dict(GITHUB_RUN_ATTEMPT='2')),
                     ('ref main degil', dict(GITHUB_REF='refs/heads/ay-takvim-plan')), ('bos ref', dict(GITHUB_REF='')), ('bos deneme no', dict(GITHUB_RUN_ATTEMPT=''))):
        rc, cikti = kos('Kapi (onay, deneme 1, ref main)', dict(tam, **deg))
        k(f'bilinen FAIL kabuk Kapi: {ack} -> cikis != 0 ve DUR satiri (MOD yazilmaz, ham girdi basilmaz)',
          rc != 0 and 'title=DUR' in cikti and (kutu_ / 'env.txt').read_text() == '' and 'ENJEKTE' not in cikti, (rc, cikti[-200:]))
    ad = 'Ayar dogrulama (mod deneme; gecersiz girdi = DUR, uretim yok)'

    def ayar(metin, mod='deneme'):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True)
        rc_, c_ = kos(ad, dict(MOD=mod, AY_TAKVIM_AYAR=metin))
        return rc_, c_, sorted(p_.name for p_ in (kutu_ / 'ay' / 'cikti').iterdir()) if (kutu_ / 'ay' / 'cikti').is_dir() else []
    rc, cikti, ds = ayar('[{"yerlesim": "girdap", "kucuk_oran": 1.2}, {"yerlesim": "rozet"}]')
    k('kabuk Ayar: mod deneme + gecerli ayar -> 0; AYAR.json, AYAR_N.txt, AYAR_AD.txt yazildi', rc == 0 and ds == ['AYAR.json', 'AYAR_AD.txt', 'AYAR_N.txt'], (rc, ds, cikti[-300:]))
    k('kabuk Ayar: mod ornek -> 0, ayar girdisi okunmaz (dosya yazilmaz)', (lambda r_: r_[0] == 0 and r_[2] == [])(ayar('[{"x": 1}]', 'ornek')))
    for ack, metin in (('bozuk JSON', '[{"yerlesim": '), ('bos ayar', ''), ('7 deneme', json.dumps([{}] * 7)), ('bilinmeyen anahtar', '[{"renk": 1}]'),
                       ('aralik disi', '[{"grup_oran": 5}]'), ('kabuk karakteri + log komutu iceren deger', '[{"isim1": "$(echo ENJEKTE)\\n::error::ENJEKTE"}]'),
                       ('4001 karakter', '[{}]' + ' ' * 3997)):
        rc, cikti, ds = ayar(metin)
        k(f'bilinen FAIL kabuk Ayar: {ack} -> cikis != 0, DUR satiri, AYAR dosyasi yok, ham girdi basilmaz',
          rc != 0 and 'title=DUR' in cikti and not any(d_.startswith('AYAR') for d_ in ds) and 'ENJEKTE' not in cikti, (rc, ds, cikti[-300:]))
    rc, cikti = kos(ad, dict(MOD='', AY_TAKVIM_AYAR='[{}]'))
    k('bilinen FAIL kabuk Ayar: MOD bos -> cikis != 0', rc != 0 and 'title=DUR' in cikti)
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
        return kos(ad, {**dict(SAHTE_MOD=mod, GITHUB_RUN_ID='123', MOD='ornek'), **e})
    rc, cikti = drive()
    k('kabuk Drive: 5 dosya yuklendi, sayi tutuyor -> 0 ve DRIVE_YOLU satiri (mod ornek: ASTROLOVE/TEMP/AY_TAKVIM_ORNEK2_<UTC>_<kosu no>)',
      rc == 0 and re.search(r'title=DRIVE_YOLU::ASTROLOVE/TEMP/AY_TAKVIM_ORNEK2_\d{8}_\d{4}_123 \| 5 dosya', cikti), (rc, cikti[-300:]))
    rc, cikti = drive(MOD='deneme')
    k('kabuk Drive: mod deneme -> ASTROLOVE/TEMP/AY_TAKVIM_DENEME_<UTC>_<kosu no>',
      rc == 0 and re.search(r'title=DRIVE_YOLU::ASTROLOVE/TEMP/AY_TAKVIM_DENEME_\d{8}_\d{4}_123 \| 5 dosya', cikti), (rc, cikti[-300:]))
    for ack, mod_ in (('MOD bos', ''), ('MOD taninmiyor', 'baska')):
        rc, cikti = drive(MOD=mod_)
        k(f'bilinen FAIL kabuk Drive: {ack} -> cikis != 0', rc != 0 and 'title=DUR' in cikti, (rc, cikti[-200:]))
    for ack, mod, n, env in (('Drive dosya sayisi eksik', 'eksik', 5, {}), ('yukleme 3 denemede basarisiz', 'copy_hata', 5, {}), ('yuklenecek dosya yok', '', 0, {}),
                             ('kosu no bos', '', 5, dict(GITHUB_RUN_ID=''))):
        rc, cikti = drive(mod, n, **env)
        k(f'bilinen FAIL kabuk Drive: {ack} -> cikis != 0', rc != 0 and 'title=DUR' in cikti, (rc, cikti[-200:]))
    rc, cikti = kos(ad, dict(GITHUB_RUN_ID='123', MOD='ornek'), yerine={' --files-only': ''})
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
    k('is akisi ornek seti (2. tur): halkalar iki halde (grup / halka), girdap, rozet; spiral YOK; metinler ve isimler gorev metniyle ayni',
      all(s in um for s in ('uret ORNEK_1A_halkalar --isim1 EMILY --isim2 JAMES --yerlesim halkalar --grup-merkez grup\n',
                            'uret ORNEK_1B_halkalar --isim1 EMILY --isim2 JAMES --yerlesim halkalar --grup-merkez halka\n',
                            'uret ORNEK_3_girdap --isim1 EMILY --isim2 JAMES --yerlesim girdap --grup-merkez grup --satir "Do you remember our first moonrise?"',
                            '--satir "Two hearts, one sky, since 2019."', '--satir "We\'ll keep star-gazing, you & me!"',
                            'uret ORNEK_4_rozet --isim1 ALEXANDRINA --isim2 CHRISTOPHER --yerlesim rozet --grup-merkez grup --satir "Our first year under one roof" --satir "Lisbon, June 14, 2027"'))
      and 'spiral' not in um and um.count('\n  uret ORNEK_') == 4)
    # Uretim adimi sahte uretim / kapi betikleriyle (cagri kaydi): mod ornek 4 ornek, mod deneme ayar dosyasindan
    for ad_, govde in (('sahte_uret', 'echo "URET $*" >> "$SAHTE_KAYIT"; exit "${SAHTE_URC:-0}"'), ('sahte_kapi', 'echo "KAPI $*" >> "$SAHTE_KAYIT"; exit "${SAHTE_KRC:-0}"')):
        (kutu_ / 'bin' / ad_).write_text('#!/bin/bash\n' + govde + '\n'); os.chmod(kutu_ / 'bin' / ad_, 0o755)
    yer_u = {'python3 "$KOD/ay_takvim_ornek.py"': 'sahte_uret', 'python3 "$KOD/ay_takvim_kapi.py"': 'sahte_kapi'}

    def uretim(mod, n=None, adlar=None, dosya=(), **e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True); (kutu_ / 'ay' / 'cikti').mkdir(parents=True)
        for d_ in dosya:
            (kutu_ / 'ay' / 'cikti' / d_).write_text('x')
        (kutu_ / 'env.txt').write_text(''); (kutu_ / 'kayit.txt').write_text('')
        if n is not None:
            (kutu_ / 'ay' / 'cikti' / 'AYAR_N.txt').write_text(str(n))
        if adlar is not None:
            (kutu_ / 'ay' / 'cikti' / 'AYAR_AD.txt').write_text(''.join(a_ + '\n' for a_ in adlar))
        rc_, c_ = kos('Uretim + kapilar (4 ornek)', dict(dict(MOD=mod, SEMBOL_RC='0', SAHTE_KAYIT=str(kutu_ / 'kayit.txt')), **e), yer_u)
        return rc_, c_, (kutu_ / 'kayit.txt').read_text().splitlines(), dict(x.split('=', 1) for x in (kutu_ / 'env.txt').read_text().split())
    rc, cikti, kay_, ev = uretim('ornek')
    k('kabuk Uretim mod ornek: 4 uretim + 4 kapi (kapi --motor ve --onek ile; ayar dosyasi / mod deneme YOK); cikislar 0',
      rc == 0 and [x.split()[0] for x in kay_] == ['URET', 'KAPI'] * 4 and all('--motor' in x and '--onek' in x and '--mod ornek' in x for x in kay_ if x.startswith('KAPI'))
      and [re.search(r'--ad (\S+)', x).group(1) for x in kay_ if x.startswith('URET')] == ['ORNEK_1A_halkalar', 'ORNEK_1B_halkalar', 'ORNEK_3_girdap', 'ORNEK_4_rozet']
      and not any('--mod deneme' in x or '--ayar-dosya' in x for x in kay_) and ev == dict(URETIM_RC='0', KAPI_RC='0', GIRDI_RC='0'), (rc, kay_, ev))
    rc, cikti, kay_, ev = uretim('deneme', 2, ['DENEME_1_girdap', 'DENEME_2_rozet'])
    k('kabuk Uretim mod deneme: N = 2 -> 2 uretim (--mod deneme --ayar-dosya --sira i; komut satirinda isim / metin / ad YOK) + 2 kapi (adlar listeden, --onek YOK)',
      rc == 0 and len(kay_) == 4 and all('--mod deneme' in x and '--ayar-dosya' in x and '--isim1' not in x and '--ad ' not in x and '--satir' not in x for x in kay_[0::2])
      and kay_[0].endswith('--sira 1') and kay_[2].endswith('--sira 2') and ' DENEME_1_girdap ' in kay_[1] and ' DENEME_2_rozet ' in kay_[3]
      and not any('--onek' in x for x in kay_) and all('--mod deneme' in x for x in kay_[1::2]) and ev == dict(URETIM_RC='0', KAPI_RC='0', GIRDI_RC='0'), (rc, kay_, ev))
    for ack, n_, adlar_, env_, bek in (('deneme sayisi 7', 7, ['DENEME_1_girdap'], {}, dict(GIRDI_RC='1')), ('deneme sayisi dosyasi yok', None, ['DENEME_1_girdap'], {}, dict(GIRDI_RC='1')),
                                       ('ad listesinde kabuk karakteri', 1, ['DENEME_1_girdap; echo ENJEKTE'], {}, dict(GIRDI_RC='1')),
                                       ('ad sirasi tutmuyor', 1, ['DENEME_2_girdap'], {}, dict(GIRDI_RC='1')), ('ad listesi bos', 1, [], {}, dict(GIRDI_RC='1')),
                                       ('MOD bos', 1, ['DENEME_1_girdap'], dict(MOD=''), dict(GIRDI_RC='1')), ('sembol olcumu FAIL', 1, ['DENEME_1_girdap'], dict(SEMBOL_RC='3'), dict(GIRDI_RC='1'))):
        rc, cikti, kay_, ev = uretim('deneme', n_, adlar_, **env_)
        k(f'bilinen FAIL kabuk Uretim mod deneme: {ack} -> hicbir uretim cagrisi yok, GIRDI_RC=1, ham ad basilmaz',
          kay_ == [] and all(ev.get(a_) == b_ for a_, b_ in bek.items()) and 'ENJEKTE' not in cikti and 'title=DUR' in cikti, (kay_, ev, cikti[-200:]))
    rc, cikti, kay_, ev = uretim('deneme', 2, ['DENEME_1_girdap', 'DENEME_2_rozet'], SAHTE_URC='4')
    k('kabuk Uretim mod deneme: uretim cikis 4 (DUR) -> URETIM_RC=1, o denemenin kapisi kosmaz, sonraki deneme yine denenir',
      [x.split()[0] for x in kay_] == ['URET', 'URET'] and ev['URETIM_RC'] == '1' and ev['GIRDI_RC'] == '0', (kay_, ev))
    rc, cikti, kay_, ev = uretim('deneme', 2, ['DENEME_1_girdap', 'DENEME_2_rozet'], SAHTE_URC='3')
    k('kabuk Uretim mod deneme: uretim cikis 3 (girdi hatasi) -> GIRDI_RC=1, kalan denemeler kosmaz', [x.split()[0] for x in kay_] == ['URET'] and ev['GIRDI_RC'] == '1', (kay_, ev))
    gd = ['DENEME_1_girdap.png', 'DENEME_1_girdap_onizleme.jpg', 'DENEME_1_girdap_kesit1_sembol_grubu.png', 'DENEME_1_girdap_META.json']
    kalan = lambda: sorted(p_.name for p_ in (kutu_ / 'ay' / 'cikti').iterdir() if p_.suffix in ('.png', '.jpg'))   # noqa: E731
    rc, cikti, kay_, ev = uretim('deneme', 1, ['DENEME_1_girdap'], gd, SAHTE_KRC='1')
    k('kabuk Uretim mod deneme: kapi cikis 1 (sert kapi FAIL) -> KAPI_RC=1 (kosu kirmizi)', ev['KAPI_RC'] == '1' and ev['URETIM_RC'] == '0', ev)
    rc, cikti, kay_, ev = uretim('deneme', 1, ['DENEME_1_girdap'], gd, SAHTE_URC='2')
    k('kabuk Uretim mod deneme: uretim yarida coktu (cikis 2) -> yazilmis gorseller SILINIR (dogrulanmamis gorsel Drive\'a gitmez), URETIM_RC=1',
      kalan() == [] and ev['URETIM_RC'] == '1' and (kutu_ / 'ay' / 'cikti' / 'DENEME_1_girdap_META.json').is_file(), (kalan(), ev))
    rc, cikti, kay_, ev = uretim('deneme', 1, ['DENEME_1_girdap'], gd, SAHTE_KRC='2')
    k('kabuk Uretim mod deneme: kapi betigi coktu (cikis 2) -> gorseller SILINIR (sert kapi dogrulanamadi; onekli de gitmez), KAPI_RC=1', kalan() == [] and ev['KAPI_RC'] == '1', (kalan(), ev))
    go = ['ORNEK_1A_halkalar.png', 'ORNEK_1A_halkalar_onizleme.jpg', 'ORNEK_1B_halkalar.png']
    rc, cikti, kay_, ev = uretim('ornek', None, None, go, SAHTE_KRC='2')
    k('kabuk Uretim mod ornek: kapi betigi coktu -> gorseller KAPI_COKUS_ onekli (temiz adli kalmaz)',
      kalan() == ['KAPI_COKUS_ORNEK_1A_halkalar.png', 'KAPI_COKUS_ORNEK_1A_halkalar_onizleme.jpg', 'KAPI_COKUS_ORNEK_1B_halkalar.png'] and ev['KAPI_RC'] == '1', (kalan(), ev))
    rc, cikti, kay_, ev = uretim('ornek', None, None, go, SAHTE_URC='4')
    k('kabuk Uretim mod ornek: uretim DUR / cokus -> o ornegin yazilmis gorselleri SILINIR, URETIM_RC=1', kalan() == [] and ev['URETIM_RC'] == '1', (kalan(), ev))
    rc, cikti, kay_, ev = uretim('deneme', 1, ['DENEME_1_girdap'], gd)
    k('kabuk Uretim mod deneme: uretim ve kapi 0 -> gorseller yerinde kalir', kalan() == sorted(gd[:3]), kalan())
    def paket(**e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True)
        c = kutu_ / 'ay' / 'cikti'; c.mkdir(parents=True)
        for ad_ in ('ORNEK_1_halkalar.png', 'ORNEK_1_halkalar_onizleme.jpg', 'KAPI_FAIL_ORNEK_2_spiral.png', 'ORNEK_1_halkalar_DUMP.npz', 'SEMBOL_OLCUM.json',
                    'ORNEK_3_girdap_DUR.json'):
            (c / ad_).write_text('{"kod": "x", "neden": "y"}' if ad_.endswith('.json') else 'x')
        (kutu_ / 'ay' / 'onb').mkdir(); (kutu_ / 'ay' / 'onb' / 'HARITA.pkl').write_text('x')
        rc_, cikti_ = kos('Paket (yuklenecek dosyalar; DUMP ve onbellek haric)', dict(dict(MOTOR_SHA='m', ORNAMENT_SHA='o', GITHUB_RUN_ID='7', GITHUB_SHA='s', MOD='ornek'), **e))
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
    def paket_d(**e):
        shutil.rmtree(kutu_ / 'ay', ignore_errors=True)
        c = kutu_ / 'ay' / 'cikti'; c.mkdir(parents=True)
        oz_ = json.dumps(dict(ozet=dict(PASS=False, fail=['6_bosluk'], en_kotu_kontrast=7.0, en_kotu_dE00=1.0, ayar=U.ayar_varsayilan('girdap'))))
        for ad_ in ('DENEME_1_girdap.png', 'DENEME_1_girdap_onizleme.jpg', 'DENEME_1_girdap_kesit1_sembol_grubu.png', 'DENEME_1_girdap_DUMP.npz', 'DENEME_1_girdap_META.json',
                    'DENEME_1_girdap_SEMBOL_OLCUM.json', 'DENEME_1_girdap_OLCUM.json', 'DENEME_2_rozet_DUR.json', 'SEMBOL_OLCUM.json', 'AYAR.json', 'AYAR_N.txt', 'AYAR_AD.txt'):
            (c / ad_).write_text(oz_ if ad_.endswith('_OLCUM.json') and 'SEMBOL' not in ad_ else '[{}]' if ad_ == 'AYAR.json' else '{"kod": "x", "neden": "y"}' if ad_.endswith('.json') else 'x')
        rc_, cikti_ = kos('Paket (yuklenecek dosyalar; DUMP ve onbellek haric)', dict(dict(MOTOR_SHA='m', ORNAMENT_SHA='o', GITHUB_RUN_ID='7', GITHUB_SHA='s', MOD='deneme',
                                                                                    TEST_RC='0', SEMBOL_RC='0', URETIM_RC='0', KAPI_RC='0', GIRDI_RC='0'), **e))
        return rc_, cikti_, sorted(p_.name for p_ in (kutu_ / 'ay' / 'yukle').iterdir()) if (kutu_ / 'ay' / 'yukle').is_dir() else []
    rc, cikti, dosyalar = paket_d()
    k('kabuk Paket mod deneme: yalniz onizleme JPG + sembol grubu kesiti + OLCUM / DUR json + AYAR.json + OZET.json; TAM BOY PNG, META, DUMP, ad listeleri YOK',
      rc == 0 and dosyalar == ['AYAR.json', 'DENEME_1_girdap_OLCUM.json', 'DENEME_1_girdap_kesit1_sembol_grubu.png', 'DENEME_1_girdap_onizleme.jpg', 'DENEME_2_rozet_DUR.json',
                               'OZET.json', 'SEMBOL_OLCUM.json']
      and (lambda o: o['mod'] == 'deneme' and o['ornek']['DENEME_1_girdap']['ayar'] == U.ayar_varsayilan('girdap') and o['ayar_listesi'] == [{}])(
          json.loads((kutu_ / 'ay' / 'yukle' / 'OZET.json').read_text())), (rc, dosyalar, cikti[-300:]))
    rc, cikti, dosyalar = paket_d(MOD='')
    k('bilinen FAIL kabuk Paket: MOD bos -> cikis != 0', rc != 0 and 'title=DUR' in cikti)
    tm = adimlar['Testler (motor + ornament kaynagiyla esdegerlik; atlanan test FAIL)']['run']
    k('is akisi: mod deneme test adimi test_ay_takvim kosmaz (TEST_RC=0 + TEST notu); mod ornek --zorunlu ile kosar',
      'if [ "${MOD:-}" = "deneme" ]' in tm and tm.index('"${MOD:-}" = "deneme"') < tm.index('test_ay_takvim.py') and '--zorunlu' in tm)
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
        f = (md if ad in MOTOR_KAYNAK else od) / ad
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
    t_grup(md, mt, src['olustur_alfa_sablon.py'], td)


def t_grup(md, mt, SB, td):
    """SEMBOL GRUBU (Serdar 11 Kas): poster goreli duzeni, tek oran, hal A / B; kucuk sembol yeri sablon formuluyle; uctan uca ornek + deneme.
    Sembol: motor dalindaki ana alfadan yerel DENEME katmani (Drive katmani degil; tek doku kapisi bu katmanla kolay gecer: zayif yon, raporda)."""
    C = json.loads((md / 'cember.json').read_text())['cember']
    # --- sabitler kaynaktan
    sb = ast.parse(SB)
    kd = next(ast.literal_eval(d.value) for d in sb.body if isinstance(d, ast.Assign) and getattr(d.targets[0], 'id', '') == 'KUCUK')
    k('KUCUK kutulari ve KUCUK_Y == motor olustur_alfa_sablon.py (:17-23)', kd == U.KUCUK and 'KUCUK_Y, TABAN_ISIM, CAP_H, SONSUZ_Y, BOSLUK, TABAN_TAG, TAG_PUNTO, ORTA = 7078.5,' in SB
      and U.KUCUK_Y == 7078.5)
    # --- kucuk sembol yatay yeri: sablon formulu (isim satiri; EMILY / JAMES = ciftin onayli posteri, isim_tagline_78.csv)
    satir78 = [x.split(',') for x in (md / 'isim_tagline_78.csv').read_text().splitlines() if x.startswith('CANCER_LIBRA,') or ',CANCER_LIBRA,' in x]
    k('ciftin poster isimleri: isim_tagline_78.csv CANCER_LIBRA satiri EMILY / JAMES', len(satir78) == 1 and 'EMILY' in satir78[0] and 'JAMES' in satir78[0], satir78)
    ns = dict(np=np, cv2=cv2, Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont, isim1='EMILY', isim2='JAMES', G=str(md / 'girdi') + '/', FONT=str(md / 'font') + '/',
              W=7200, H=10800, KENAR=700, ISIM_PUNTO=405, BOSLUK=465, ORTA=3600, TABAN_ISIM=8062, SONSUZ_Y=7945.5, TEMIZ=False, ekle=lambda *a_: None, log=lambda *a_: None)
    for f_ in ('kirp', 'yaz'):
        exec(ic_fonk(SB, f_), ns)
    exec(blok(SB, '# --- isim satiri: isim1  sonsuz  isim2 (ortali) ---', "log('isim punto'"), ns)
    u1, u2 = (ns['c1'] - C['cx']) / C['R'], (ns['c2'] - C['cx']) / C['R']
    k(f'kucuk sembol yatay yeri: sablon formulu (EMILY / JAMES) u = {u1:.4f} / {u2:.4f}; koddaki sabit -0,491 / +0,490 ile fark <= 0,005 R',
      abs(u1 - U.KUCUK_U['CANCER_LIBRA'][0]) <= 0.005 and abs(u2 - U.KUCUK_U['CANCER_LIBRA'][1]) <= 0.005, (u1, u2))
    k('bilinen FAIL kucuk sembol yeri: baska isimlerle (ALEXANDRINA / CHRISTOPHER) formul sabitten 0,005 R\'den fazla sapar (karsilastirma kor degil)',
      (lambda n2: (exec(blok(SB, '# --- isim satiri: isim1  sonsuz  isim2 (ortali) ---', "log('isim punto'"), n2),
                   abs((n2['c1'] - C['cx']) / C['R'] - U.KUCUK_U['CANCER_LIBRA'][0]) > 0.005)[1])(dict(ns, isim1='ALEXANDRINA', isim2='CHRISTOPHER')))
    k('kucuk sembol dikey yeri: KUCUK_Y halka merkezinin 0,948 R altinda', abs((U.KUCUK_Y - C['cy']) / C['R'] - 0.948) < 0.0005)
    # --- deneme katmani + grup kurulumu
    gk = td / 'grup'; gk.mkdir()
    k('deneme katmani (yerel): cikis 0, RGBA + yan json (kaynak kutusu alanlari)', U.main(['deneme', '--cift', 'CANCER_LIBRA', '--motor', str(md), '--cikti', str(gk)]) == 0)
    kat = gk / 'DENEME_CANCER_LIBRA_ana.png'
    g, olc = U.sembol_yukle(kat)
    Yl = json.loads((md / 'yerlesim78.json').read_text())['CANCER_LIBRA']
    kay, C2, ymer = U.grup_kaynak(mt, 'CANCER_LIBRA')
    z = np.load(md / 'alfa_ogeler.npz')
    k('grup kaynagi: halka = alfa_ogeler.npz cember (bayt bayt, _konum); npz\'nin diger ogeleri okunmaz; kucuk semboller CANCER (KUCUK_1) + LIBRA (KUCUK_2)',
      [o['ad'] for o in kay] == ['halka', 'kucuk1', 'kucuk2'] and np.array_equal(kay[0]['alfa'], z['cember']) and [kay[0]['px'], kay[0]['py']] == [752.0, 1531.0]
      and [o['burc'] for o in kay[1:]] == ['CANCER', 'LIBRA'] and ymer == 7078.5)
    for o in kay[1:]:                                                         # kucuk sembol: kaynak sayfadaki kutunun kirpilmisi; merkez (cx + u R, KUCUK_Y) +- 1 px
        sayfa, kk = U.KUCUK[o['burc']]
        ham = np.asarray(Image.open(md / 'girdi' / f'{sayfa}.png').convert('L'))[kk[1]:kk[3], kk[0]:kk[2]]
        ys, xs = np.nonzero(ham > 8)
        hk = ham[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        ka = U.kutu(o['alfa'].astype(np.float32) / 255, 0.03)
        ic = o['alfa'][ka[1]:ka[3], ka[0]:ka[2]]
        k(f"kucuk sembol {o['burc']}: murekkep kutusu kaynak kirpimiyla ayni boyda (+- 2 px), merkezi (cx + u R, KUCUK_Y) +- 1,5 px; alfa kaynakla uyumlu (ortalama fark < 12 seviye)",
          abs(ic.shape[0] - hk.shape[0]) <= 2 and abs(ic.shape[1] - hk.shape[1]) <= 2
          and abs(o['px'] + (ka[0] + ka[2]) / 2 - (C['cx'] + o['u'] * C['R'])) <= 1.5 and abs(o['py'] + (ka[1] + ka[3]) / 2 - U.KUCUK_Y) <= 1.5
          and float(np.abs(cv2.resize(ic, (hk.shape[1], hk.shape[0])).astype(np.float32) - hk).mean()) < 12, (ic.shape, hk.shape))
    hr_ = 205 * U.S
    GA = U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], hr_, 'grup')
    GB = U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], hr_, 'halka')

    def uzak(G):                                                              # yerlesen tum grup pikselleri (alfa > 0,02): merkeze en uzak nokta
        en = 0.0
        for a_, x_, y_ in [(G['ana']['a'], G['ana']['x'], G['ana']['y'])] + [(o['A'], o['x'], o['y']) for o in G['ogeler']]:
            ys, xs = np.nonzero(a_ > 0.02)
            en = max(en, float(max(np.hypot(xs + x_ + dx, ys + y_ + dy).max() for dx in (0, 1) for dy in (0, 1))))   # piksel koseleri
        return en

    def halka_mer(G):
        o = G['ogeler'][0]
        fx, fy, fr = KP.cember_uydur(o['A'])
        return o['x'] + fx, o['y'] + fy, fr
    k(f"grup hal A (grup ortali): en uzak grup pikseli takvim merkezinden {uzak(GA):.1f} px = sembol alani yaricapi {hr_} (+- 2 px); cevreleyen daire merkezde",
      abs(uzak(GA) - hr_) <= 2.0 and GA['olcek'] <= 1 and GA['bilgi']['merkez'] == 'grup', (uzak(GA), GA['bilgi']['halka_merkez_kayma_px']))
    hx, hy, hr2 = halka_mer(GB)
    k(f'grup hal B (halka ortali): halkanin (maskeye uydurulan) merkezi takvim merkezinde (+- 1 px: {hx:.2f}, {hy:.2f}); en uzak piksel = sembol alani yaricapi (+- 2 px)',
      abs(hx) <= 1.0 and abs(hy) <= 1.0 and abs(uzak(GB) - hr_) <= 2.0 and GB['bilgi']['halka_merkez_kayma_px'] == [0.0, 0.0], (hx, hy, uzak(GB)))
    k('hal A halkayi merkezden kaydirir (grup ortali), hal B kaydirmaz; hal B olcegi hal A\'dan kucuk (ayni alan)',
      float(np.hypot(*GA['bilgi']['halka_merkez_kayma_px'])) > 20 and GB['olcek'] < GA['olcek'], (GA['bilgi']['halka_merkez_kayma_px'], GA['olcek'], GB['olcek']))
    for ad_, G in (('A', GA), ('B', GB)):
        ol = G['olcek']
        mx_, my_, mr_ = halka_mer(G)
        es = abs(mr_ - C['R'] * ol) <= 1.0
        for o, u_ in zip(G['ogeler'][1:], U.KUCUK_U['CANCER_LIBRA']):
            kk = U.kutu(o['A'], 0.02)
            es &= abs(o['x'] + (kk[0] + kk[2]) / 2 - mx_ - u_ * C['R'] * ol) <= 1.5 and abs(o['y'] + (kk[1] + kk[3]) / 2 - my_ - (U.KUCUK_Y - C['cy']) * ol) <= 1.5
        ks = U.kutu(G['ana']['a'], 0.5)
        k5 = olc['kutu_alfa_05']; py_ = olc['yan_json']['kaynak_x'] - olc['yan_json']['x']
        sa_ = (Yl['u1'] - Yl['u0']) * C['R'] / olc['yan_json']['kaynak_w']
        es &= abs(G['ana']['x'] + ks[0] - mx_ - (Yl['u0'] * C['R'] + (k5[0] - py_) * sa_) * ol) <= 1.5
        es &= abs(G['ana']['y'] + ks[1] - my_ - (Yl['v0'] * C['R'] + (k5[1] - py_) * sa_) * ol) <= 1.5
        es &= all(abs(o['olcek'] - ol) < 1e-12 for o in G['ogeler']) and abs(G['ana']['olcek'] - ol * sa_) < 1e-9
        k(f'grup goreli konum hal {ad_}: OLCULEN halka merkezine gore ana sembol (u0, v0), kucuk semboller (u, 0,948 R), halka yaricapi R x olcek poster degerleriyle +- 1,5 px; '
          f'TEK oran (her ogenin olcegi = grup olcegi {ol:.4f})', bool(es))
        for o in G['ogeler']:
            m2 = cv2.resize(o['kaynak'].astype(np.float32) / 255.0, (o['A'].shape[1], o['A'].shape[0]), interpolation=cv2.INTER_AREA)
            es &= np.array_equal(m2, o['A']) and o['k'] == int(np.floor(1 / o['olcek'])) and o['A'].shape[1] * o['k'] <= o['kaynak'].shape[1]
        k(f'grup maskeleri hal {ad_}: kaynak alfanin TEK adim INTER_AREA kucultulmusu (birebir); k = floor(1 / olcek) = {G["ogeler"][0]["k"]}; k kat cizim kaynaktan buyuk degil', bool(es))
    k(f"halka kalinligi: 19,07 x olcek = {GA['bilgi']['halka_kalinlik_px']} px (hal A), {GB['bilgi']['halka_kalinlik_px']} px (hal B); mm = px x 25,4 / 300",
      abs(GA['bilgi']['halka_kalinlik_px'] - C['kalinlik'] * GA['olcek']) < 1e-3 and abs(GA['bilgi']['halka_kalinlik_mm'] - GA['bilgi']['halka_kalinlik_px'] * 25.4 / 300) < 1e-3)
    k('bilinen FAIL grup: yan json yok -> girdi hatasi; hedef yaricap kaynaktan buyuk -> DUR (buyutme yok); taninmayan cift -> DUR; kucuk_oran 1,8 buyutme gerektirirse DUR',
      dur_mu(lambda: U.grup_kur(mt, 'CANCER_LIBRA', g, None, hr_), 'sembol_json', True) and dur_mu(lambda: U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], 4000.0), 'grup_olcek', False)
      and dur_mu(lambda: U.grup_kur(mt, 'ARIES_LEO', g, olc['yan_json'], hr_), 'grup_cift', False)
      and dur_mu(lambda: U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], 2400.0, 'halka', 'poster', 'poster', 1.8), 'grup_olcek', False)
      and U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], 2400.0, 'halka')['olcek'] <= 1.0)       # ayni yaricap kucuk_oran 1,0 ile kurulur (DUR'un nedeni carpan)
    GK = U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], hr_, 'halka', 0.6, 1.1, 1.5)
    mx_, my_, mr_ = halka_mer(GK)
    es = True
    for o, u_ in zip(GK['ogeler'][1:], (-0.6, 0.6)):
        kk = U.kutu(o['A'], 0.02)
        es &= abs(o['x'] + (kk[0] + kk[2]) / 2 - mx_ - u_ * C['R'] * GK['olcek']) <= 1.5 and abs(o['y'] + (kk[1] + kk[3]) / 2 - my_ - 1.1 * C['R'] * GK['olcek']) <= 1.5
        es &= abs(o['olcek'] - 1.5 * GK['olcek']) < 1e-12
    k('AYAR kucuk_u 0,6 / kucuk_v 1,1 / kucuk_oran 1,5: kucuk semboller simetrik (-u / +u), dikey v R, boy = grup olcegi x 1,5 (merkezleri etrafinda); halka ve ana sembol tek oranda',
      bool(es) and abs(GK['ogeler'][0]['olcek'] - GK['olcek']) < 1e-12)
    # --- kapi 2 grup bolumu DOGRUDAN (uretimsiz; grup_kur ciktisindan sentetik META / DUMP): bagimsiz olcum uretim hatasini yakalar mi (inceleme O1, O6)
    def kapi_grup(G, ayar=None):
        AYx = dict(U.ayar_varsayilan('halkalar'), **(ayar or {}))
        mx_, my_ = 2700, 3600
        meta = dict(cift='CANCER_LIBRA', ayar=AYx, disk=dict(merkez=[2700.0, 3600.0]),
                    sembol=dict(olcum=olc, yerlesim=dict(olcek=G['ana']['olcek']), hedef_yaricap=AYx['grup_oran'] * AYx['sembol_alan'] * U.S),
                    grup=dict(merkez=[mx_, my_], ogeler=[dict(ad=o['ad'], x=mx_ + o['x'], y=my_ + o['y']) for o in G['ogeler']]))
        D_ = {f'gm_{i}': o['A'].astype(np.float32) for i, o in enumerate(G['ogeler'])}
        return KP.grup_kapisi(meta, D_, g, olc['yan_json'], md, G['ana']['a'], mx_ + G['ana']['x'], my_ + G['ana']['y'])
    kA, kB = kapi_grup(GA), kapi_grup(GB, dict(grup_merkez='halka'))
    kK = kapi_grup(GK, dict(grup_merkez='halka', kucuk_u=0.6, kucuk_v=1.1, kucuk_oran=1.5))
    k('kapi 2 grup (bilinen PASS, dogrudan): hal A, hal B ve ayarli (u 0,6 / v 1,1 / oran 1,5) -> PASS; bagimsiz olcum farki <= 2 px; kucuk1 solda / kucuk2 sagda',
      all(q['PASS'] and q['bagimsiz']['PASS'] and q['bagimsiz']['fark_en_buyuk'] <= 2.0 and q['bagimsiz']['kucuk1_solda_kucuk2_sagda'] for q in (kA, kB, kK)),
      [q['bagimsiz'] for q in (kA, kB, kK)])
    print(f"BILGI kapi 2 bagimsiz olcum farki (px): hal A {kA['bagimsiz']['fark_en_buyuk']}, hal B {kB['bagimsiz']['fark_en_buyuk']}, ayarli {kK['bagimsiz']['fark_en_buyuk']}", flush=True)
    k('bilinen FAIL kapi 2 grup: ayar META\'da hal B, gorsel hal A -> FAIL', not kapi_grup(GA, dict(grup_merkez='halka'))['PASS'])

    def uretim_mutasyonu(ack, kur, geri, alan, hal='grup'):
        '''Uretim kodu BOZUK (kapinin cagirdigi U.grup_kur da ayni bozuk kod): yeniden kurulum kaniti tutar, BAGIMSIZ olcum FAIL vermeli.'''
        try:
            kur()
            Gm = U.grup_kur(mt, 'CANCER_LIBRA', g, olc['yan_json'], hr_, hal)
            q = kapi_grup(Gm, dict(grup_merkez=hal))
        finally:
            geri()
        k(f'bilinen FAIL kapi 2 grup (uretim mutasyonu, kapi ayni bozuk kodu cagirir): {ack} -> yeniden kurulum tutar AMA bagimsiz olcum FAIL',
          not q['PASS'] and all(v['yeniden_kucultme_birebir'] and v['yer_ayni'] for v in q['oge'].values()) and not q['bagimsiz']['PASS'] and alan(q['bagimsiz']),
          q.get('bagimsiz'))
    es_u, es_y, es_kur = dict(U.KUCUK_U), U.KUCUK_Y, U.grup_kur
    uretim_mutasyonu('kucuk semboller yer degistirmis (u isareti ters: Cancer sagda)', lambda: U.KUCUK_U.update(CANCER_LIBRA=(0.491, -0.490)),
                     lambda: U.KUCUK_U.update(es_u), lambda b_: b_['kucuk1_solda_kucuk2_sagda'] is False)
    uretim_mutasyonu('kucuk sembol yatay yeri kaymis (u -0,52: 0,029 R)', lambda: U.KUCUK_U.update(CANCER_LIBRA=(-0.52, 0.490)),
                     lambda: U.KUCUK_U.update(es_u), lambda b_: b_['kucuk1']['yer_fark'] > 2.0 and b_['kucuk2']['yer_fark'] <= 2.0)
    uretim_mutasyonu('kucuk sembol dikey yeri kaymis (KUCUK_Y + 60 poster px)', lambda: setattr(U, 'KUCUK_Y', es_y + 60),
                     lambda: setattr(U, 'KUCUK_Y', es_y), lambda b_: b_['kucuk1']['yer_fark'] > 2.0)
    uretim_mutasyonu('grup 0,80 oraninda kucuk kurulmus (cevreleyen daire sembol alanindan kucuk)',
                     lambda: setattr(U, 'grup_kur', lambda mt_, c_, g_, j_, h_, *a_: es_kur(mt_, c_, g_, j_, h_ * 0.8, *a_)),
                     lambda: setattr(U, 'grup_kur', es_kur), lambda b_: b_['en_uzak_fark'] > 100)
    def kur_buyuk():
        def f(mt_, c_, g_, j_, h_, *a_):
            G_ = es_kur(mt_, c_, g_, j_, h_, *a_)
            o_ = G_['ogeler'][1]                                              # kucuk1 ayrica 1,15 kat (TEK oran kurali cignenir), merkezi ayni
            w_, h2 = o_['kaynak'].shape[1], o_['kaynak'].shape[0]
            m_ = cv2.resize(o_['kaynak'].astype(np.float32) / 255.0, (round(w_ * o_['olcek'] * 1.15), round(h2 * o_['olcek'] * 1.15)), interpolation=cv2.INTER_AREA)
            o_.update(x=o_['x'] - (m_.shape[1] - o_['A'].shape[1]) // 2, y=o_['y'] - (m_.shape[0] - o_['A'].shape[0]) // 2, A=m_)
            return G_
        U.grup_kur = f
    uretim_mutasyonu('kucuk1 ayrica 1,15 kat olceklenmis (TEK oran kurali)', kur_buyuk, lambda: setattr(U, 'grup_kur', es_kur),
                     lambda b_: b_['kucuk1']['boy_fark'] > 2.0 and b_['kucuk1']['yer_fark'] <= 2.0 and b_['kucuk2']['boy_fark'] <= 2.0)
    def kur_ana(dx=0, kat=1.0):
        def f(mt_, c_, g_, j_, h_, *a_):
            G_ = es_kur(mt_, c_, g_, j_, h_, *a_)
            an = G_['ana']
            if kat != 1.0:                                                    # ana sembol ayrica olceklenmis (TEK oran kurali), merkezi ayni
                rgb_, a2_ = U.rgba_olcek(g_, an['olcek'] * kat)
                an.update(x=an['x'] - (a2_.shape[1] - an['a'].shape[1]) // 2, y=an['y'] - (a2_.shape[0] - an['a'].shape[0]) // 2, rgb=rgb_, a=a2_, olcek=an['olcek'] * kat)
            an['x'] += dx
            return G_
        U.grup_kur = f
    uretim_mutasyonu('ana sembol 5 px saga kaymis (halka ve kucuk semboller yerinde)', lambda: kur_ana(dx=5), lambda: setattr(U, 'grup_kur', es_kur),
                     lambda b_: b_['ana']['yer_fark'] > 2.0 and b_['ana']['boy_fark'] <= 2.0 and b_['kucuk1']['yer_fark'] <= 2.0)
    uretim_mutasyonu('ana sembol ayrica 1,05 kat olceklenmis (TEK oran kurali)', lambda: kur_ana(kat=1.05), lambda: setattr(U, 'grup_kur', es_kur),
                     lambda b_: b_['ana']['boy_fark'] > 2.0 and b_['kucuk1']['boy_fark'] <= 2.0)

    def kur_kay():
        def f(mt_, c_, g_, j_, h_, *a_):                                      # hal halka: tum grup 8 px saga (halka merkezi merkezde degil; en uzak piksel de buyur)
            G_ = es_kur(mt_, c_, g_, j_, h_, *a_)
            G_['ana']['x'] += 8
            for o_ in G_['ogeler']:
                o_['x'] += 8
            return G_
        U.grup_kur = f
    uretim_mutasyonu('hal halka: tum grup 8 px kaymis (halka merkezi takvim merkezinde degil)', kur_kay, lambda: setattr(U, 'grup_kur', es_kur),
                     lambda b_: b_['halka_merkezde_fark'] > 2.0 and b_['kucuk1']['yer_fark'] <= 2.0 and b_['ana']['yer_fark'] <= 2.0, hal='halka')
    asil_kg = KP.grup_kapisi

    def kapi_merkez(meta, *a_):                                               # sentetik META: grup merkezi disk merkezinden 6 px farkli
        meta['disk'] = dict(merkez=[2706.0, 3600.0])
        return asil_kg(meta, *a_)
    KP.grup_kapisi = kapi_merkez
    try:
        qm = kapi_grup(GA)
    finally:
        KP.grup_kapisi = asil_kg
    k('bilinen FAIL kapi 2 grup: grup merkezi disk (takvim) merkezi degil (6 px) -> bagimsiz olcum FAIL, diger olcutler tutar',
      not qm['PASS'] and qm['bagimsiz']['grup_merkez_disk_merkezi'] is False and qm['bagimsiz']['fark_en_buyuk'] <= 2.0, qm['bagimsiz'])
    k('mutasyonlar geri alindi (sabitler ve grup_kur ozgun)', U.KUCUK_U == es_u and U.KUCUK_Y == es_y and U.grup_kur is es_kur
      and KP.POSTER_KUCUK_U == U.KUCUK_U and KP.POSTER_KUCUK_Y == U.KUCUK_Y)
    del g
    # --- altin yolu: grup ogeleri uretimin TEK giris noktasindan (altin_ogeler), kucuk semboller VEKTOR yolu, halka egim_tup yolu
    hrt = mt.harita_kur('CANCER_LIBRA', str(gk / 'onb'))
    cagri = []
    asil = mt.golgele_oge
    mt.golgele_oge = lambda a8, ad: (cagri.append((ad, a8.shape)), asil(a8, ad))[1]
    Lana = np.array([70.0, 12.0, 60.0], np.float32)
    og2 = [dict(o, x=0, y=0) for o in GA['ogeler'][1:]]
    b2 = U.altin_ogeler(mt, og2, hrt['har'], hrt['qa_goz'], Lana, 20.0)
    mt.golgele_oge = asil
    k('altin yolu (grup): altin_ogeler -> Motor.oge_katman motor adiyla (kucuk1 / kucuk2: VEKTOR ogeleri); cizim k kat (maske x k); cikti maske boyunda; renk_uyum hedefe <= 2',
      [c[0] for c in cagri] == ['kucuk1', 'kucuk2'] and all(c[1] == (o['A'].shape[0] * o['k'], o['A'].shape[1] * o['k']) for c, o in zip(cagri, og2))
      and all(b_['rgb'].shape[:2] == o['A'].shape and b_['m'] is o['A'] and o['uyum']['dE00_sonra'] <= 2.0 for b_, o in zip(b2, og2))
      and all(a_ in mt.VEK_OGE for a_ in ('kucuk1', 'kucuk2')) and 'cember' not in mt.VEK_OGE, cagri)
    k('altin yolu (grup): duz renk degil (kucuk sembol cekirdek luma yayilimi p95 - p5 >= 40)',
      all(float(np.percentile(KP.lum(b_['rgb'][o['A'] >= 0.9]), 95) - np.percentile(KP.lum(b_['rgb'][o['A'] >= 0.9]), 5)) >= 40 for b_, o in zip(b2, og2)))
    # --- uctan uca: 1 ornek (mod ornek, ayarsiz) + kapi; META ayari = varsayilan
    ortak = ['uret', '--cift', 'CANCER_LIBRA', '--katman', str(kat), '--motor', str(md), '--cikti', str(gk), '--onbellek', str(gk / 'onb')]
    rc = U.main(ortak + ['--ad', 'E1', '--isim1', 'EMILY', '--isim2', 'JAMES', '--yerlesim', 'halkalar', '--grup-merkez', 'grup'])
    me = json.loads((gk / 'E1_META.json').read_text()) if rc == 0 else {}
    k('uctan uca ornek (halkalar, hal A, ayarsiz): cikis 0; META ayar = varsayilanlarin tamami; mod ornek; 3 kesit (grup, en dar ay adi, isim + baslik)',
      rc == 0 and me['ayar'] == U.ayar_varsayilan('halkalar') and me['mod'] == 'ornek' and all((gk / f'E1_{x}.png').is_file() for x in
                                                                                      ('kesit1_sembol_grubu', 'kesit2_ay_adi', 'kesit3_isim_baslik')), rc)
    if rc == 0:
        k('uctan uca ornek: META olculeri varsayilan sabitlerle (hedef yaricap 615, ay adi 53 px x 12, isim 150, baslik 75, katsayi 0,36, grup k 5, grup 3 oge)',
          me['sembol']['hedef_yaricap'] == 615.0 and [o['cap'] for o in me['ogeler'] if o['tur'] == 'ay'] == [53.0] * 12 and me['isim']['cap'] == 150.0
          and me['ogeler'][1]['cap'] == 75.0 and me['disk']['katsayi'] == 0.36 and [o['ad'] for o in me['grup']['ogeler']] == ['halka', 'kucuk1', 'kucuk2']
          and all(o['k'] == 5 for o in me['grup']['ogeler']) and all(not v['PASS'] is False for v in me['uretim_kontrol'].values()))
        r1 = KP.kapi_olc(gk, 'E1', kat, md)
        k('uctan uca ornek kapilar (bilinen PASS): hepsi PASS; grup konum farki <= 1 px, olculen <= 2 px; halka / kucuk sembol dE00 <= 2, kontrast >= 4,5; kucuk semboller yayilim >= 40',
          r1['ozet']['PASS'] and r1['kapi']['2_sembol']['grup']['konum_fark_en_buyuk'] <= 1.0 and r1['kapi']['2_sembol']['grup']['olculen_fark_en_buyuk'] <= 2.0
          and r1['kapi']['2_sembol']['grup']['bagimsiz']['PASS'] and r1['kapi']['0_uretim']['PASS']
          and all(r1['kapi']['3_tek_doku']['oge'][a_]['dE00'] <= 2.0 and r1['kapi']['4_kontrast']['oge'][a_]['ortanca_bilgi'] >= 4.5 for a_ in ('halka', 'kucuk1', 'kucuk2'))
          and min(r1['kapi']['7_altin']['duz_renk']['oge'][a_] for a_ in ('kucuk1', 'kucuk2')) >= 40, (r1['ozet']['fail'], r1['kapi']['2_sembol'].get('grup')))
        print(f"BILGI E1: grup {r1['ozet']['grup']} | halka yayilimi {r1['kapi']['7_altin']['duz_renk']['halka_bilgi']} | sure {me['sure_adim']}", flush=True)
        k('bilinen FAIL kapi 2 (grup): --motor verilmezse FAIL', '2_sembol' in KP.kapi_olc(gk, 'E1', kat)['ozet']['fail'])

        def meta_mut(ad, f):                                                  # ayni gorsel + DUMP, degistirilmis META
            m2 = json.loads((gk / 'E1_META.json').read_text()); f(m2); m2['ad'] = ad
            (gk / f'{ad}_META.json').write_text(json.dumps(m2))
            for uz_ in ('.png', '_DUMP.npz'):
                if not (gk / f'{ad}{uz_}').exists():
                    os.link(gk / f'E1{uz_}', gk / f'{ad}{uz_}')
            return KP.kapi_olc(gk, ad, kat, md)
        rgs = None
        for ack, f in (('META grup alani silinmis (grup yerlesimi)', lambda m2: m2.update(grup=None)),
                       ('META mod deneme (kapi mod ornek ile cagrildi)', lambda m2: m2.update(mod='deneme')),
                       ('META ayar ay_adi_cap 40 (mod ornek: varsayilan disi ayar)', lambda m2: m2['ayar'].update(ay_adi_cap=40))):
            rm = meta_mut('E1n', f)
            k(f'bilinen FAIL kapi (mod ornek): {ack}', not rm['ozet']['PASS'] and ('2_sembol' in rm['ozet']['fail'] or '0_uretim' in rm['ozet']['fail']), rm['ozet']['fail'])
        for ack, f in (('kucuk sembol 3 px kaydirilmis', lambda m2: m2['grup']['ogeler'][1].update(x=m2['grup']['ogeler'][1]['x'] + 3)),
                       ('halka 2 px kaydirilmis', lambda m2: m2['grup']['ogeler'][0].update(y=m2['grup']['ogeler'][0]['y'] - 2)),
                       ('ana sembol 2 px kaydirilmis', lambda m2: m2['sembol'].update(x=m2['sembol']['x'] + 2)),
                       ('META ayar kucuk_u 0,6 (gorsel poster yerinde)', lambda m2: m2['ayar'].update(kucuk_u=0.6)),
                       ('META ayar kucuk_oran 1,2 (gorsel 1,0)', lambda m2: m2['ayar'].update(kucuk_oran=1.2)),
                       ('META ayar grup_merkez halka (gorsel grup ortali)', lambda m2: m2['ayar'].update(grup_merkez='halka')),
                       ('META ayar sembol_alan 250 (gorsel 205)', lambda m2: m2['ayar'].update(sembol_alan=250))):
            rm = meta_mut('E1m', f)
            k(f'bilinen FAIL kapi 2 (grup): {ack}', '2_sembol' in rm['ozet']['fail'] and not rm['kapi']['2_sembol']['grup']['PASS'], rm['kapi']['2_sembol']['grup'].get('bagimsiz'))
        D_ = dict(np.load(gk / 'E1_DUMP.npz'))
        D_['gm_1'] = np.clip(cv2.GaussianBlur(D_['gm_1'], (0, 0), 1.2), 0, 1)
        (gk / 'E1b_DUMP.npz').unlink(missing_ok=True); np.savez(gk / 'E1b_DUMP.npz', **D_)
        del D_
        rm = meta_mut('E1b', lambda m2: None)
        k('bilinen FAIL kapi 2 (grup): kucuk sembol maskesi kaynagin kucultulmusu degil (bulaniklastirilmis)',
          '2_sembol' in rm['ozet']['fail'] and rm['kapi']['2_sembol']['grup']['oge']['kucuk1']['yeniden_kucultme_birebir'] is False)
    # --- uctan uca: mod deneme, varsayilan disi ayar (kucuk_u, ay_adi_cap, disk_katsayi) -> kapi degerleri META'dan
    os.environ['AY_TEST_AYAR'] = json.dumps([dict(yerlesim='girdap', kucuk_u=0.6, kucuk_v=1.05, kucuk_oran=1.3, ay_adi_cap=40, disk_katsayi=0.30, satirlar=['Two hearts, one sky']),
                                             dict(yerlesim='halkalar', sembol_alan=400, grup_oran=1.3, grup_merkez='halka')])
    k('deneme ayari dogrulandi (2 deneme)', U.main(['ayar-dogrula', '--env', 'AY_TEST_AYAR', '--cikti', str(gk)]) == 0)
    del os.environ['AY_TEST_AYAR']
    rc = U.main(ortak + ['--mod', 'deneme', '--ayar-dosya', str(gk / 'AYAR.json'), '--sira', '1'])
    k('uctan uca deneme 1 (girdap, varsayilan disi ayar): cikis 0; ad koddan (DENEME_1_girdap); yalniz sembol grubu kesiti (kesit 2 / 3 yok)',
      rc == 0 and (gk / 'DENEME_1_girdap_onizleme.jpg').is_file() and (gk / 'DENEME_1_girdap_kesit1_sembol_grubu.png').is_file()
      and not list(gk.glob('DENEME_1_girdap_kesit2*')) and not list(gk.glob('DENEME_1_girdap_kesit3*')), rc)
    if rc == 0:
        md1 = json.loads((gk / 'DENEME_1_girdap_META.json').read_text())
        rd = KP.kapi_olc(gk, 'DENEME_1_girdap', kat, md, 'deneme')
        k('deneme 1 kapi 2 (bilinen PASS): hedef AYARDAN (kucuk_u 0,6, kucuk_v 1,05, kucuk_oran 1,3) -> PASS; sert FAIL yok; onizleme 1350x1800',
          rd['kapi']['2_sembol']['PASS'] and rd['ozet']['sert_fail'] == [] and abs(rd['kapi']['2_sembol']['grup']['oge']['kucuk1']['olcek'] / rd['kapi']['2_sembol']['grup']['olcek'] - 1.3) < 1e-9
          and Image.open(gk / 'DENEME_1_girdap_onizleme.jpg').size == (1350, 1800), (rd['ozet']['fail'], rd['kapi']['2_sembol']['grup']))
        k('deneme 1: kapi degerleri META ayarindan (isim alt siniri = ay_adi_cap 40; ay adlari 40 px; disk katsayisi 0,30 ve disk yaricapi buna gore; ayar OZET\'te tam)',
          rd['kapi']['8_isim']['cap_alt_siniri'] == 40 and [o['cap'] for o in md1['ogeler'] if o['tur'] == 'ay'] == [40.0] * 12 and rd['ozet']['disk_katsayisi'] == 0.30
          and abs(md1['disk']['liste'][0][2] - 0.30 * md1['disk']['bilgi']['aralik'] * U.S) < 0.01 and rd['ozet']['ayar'] == md1['ayar']
          and sorted(rd['ozet']['ayar']) == sorted(U.AYAR_ANAHTAR) and rd['kapi']['1_veri']['PASS'])
        (gk / 'Dm_META.json').write_text(json.dumps(dict(md1, ad='Dm', ayar=dict(md1['ayar'], kucuk_u=0.7))))
        for uz_ in ('.png', '_DUMP.npz'):
            os.link(gk / f'DENEME_1_girdap{uz_}', gk / f'Dm{uz_}')
        k('bilinen FAIL deneme kapi 2: ayni gorsel, META ayar kucuk_u 0,7 (yanlis konum) -> kapi 2 FAIL, sert FAIL; komut cikis 1 ve gorsel silinir',
          KP.main([str(gk), 'Dm', '--katman', str(kat), '--motor', str(md), '--mod', 'deneme']) == 1 and not (gk / 'Dm.png').exists()
          and json.loads((gk / 'Dm_OLCUM.json').read_text())['ozet']['sert_fail'] == ['2_sembol'])
    # --- kapi 6 tutmayan ayar: mod deneme gorsel uretir + OLCUM FAIL; mod ornek ayni ayarla DUR
    rc = U.main(ortak + ['--mod', 'deneme', '--ayar-dosya', str(gk / 'AYAR.json'), '--sira', '2'])
    k('uctan uca deneme 2 (sembol alani 400 x 1,3: grup disklere biner): mod deneme yine gorsel uretir (cikis 0)', rc == 0 and (gk / 'DENEME_2_halkalar_onizleme.jpg').is_file(), rc)
    if rc == 0:
        rc2 = KP.main([str(gk), 'DENEME_2_halkalar', '--katman', str(kat), '--motor', str(md), '--mod', 'deneme'])
        o2 = json.loads((gk / 'DENEME_2_halkalar_OLCUM.json').read_text())
        k('deneme 2: OLCUM kapi 6 FAIL + uretim kontrolu bosluk FAIL yazar; sert kapilar PASS -> cikis 0, gorsel kalir; katsayi kendiliginden DUSMEDI',
          rc2 == 0 and '6_bosluk' in o2['ozet']['fail'] and o2['ozet']['uretim_kontrol_fail'] == ['bosluk'] and o2['ozet']['sert_fail'] == []
          and o2['ozet']['disk_katsayisi'] == 0.36 and (gk / 'DENEME_2_halkalar_onizleme.jpg').is_file(), (rc2, o2['ozet']['fail']))
    a2 = json.loads((gk / 'AYAR.json').read_text())[1]
    rc = U.main(ortak + ['--ad', 'E2', '--ayar', json.dumps(a2)])
    k('bilinen FAIL mod ornek: ayni ayar (kapi 6 tutmaz) -> DUR (cikis 4), gorsel YOK', rc == 4 and not (gk / 'E2.png').exists() and not (gk / 'E2_onizleme.jpg').exists()
      and json.loads((gk / 'E2_DUR.json').read_text())['kod'] == 'bosluk', rc)
    rc = U.main(ortak + ['--mod', 'deneme', '--ad', 'E3', '--ayar', json.dumps(dict(yerlesim='halkalar', isim1='W' * 30, isim2='W' * 30, isim_cap=240, ay_adi_cap=90,
                                                                                    girdap_ad_uzaklik=200, satirlar=['W' * 35]))])
    if rc == 0:
        m3 = json.loads((gk / 'E3_META.json').read_text())
        k('mod deneme: isim_kucuk + metin_genis tutmasa da gorsel cikar; uretim kontrolunde FAIL yazilir (isim buyuk harfi ay adi boyunun altinda)',
          m3['uretim_kontrol']['isim_kucuk']['PASS'] is False and m3['uretim_kontrol']['metin_genis']['PASS'] is False and m3['isim']['cap'] < 90
          and (gk / 'E3_onizleme.jpg').is_file(), m3['uretim_kontrol'])
    else:
        k('mod deneme: isim_kucuk + metin_genis tutmasa da gorsel cikar', False, rc)


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
