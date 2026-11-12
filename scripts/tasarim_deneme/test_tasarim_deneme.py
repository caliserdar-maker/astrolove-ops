#!/usr/bin/env python3
"""TASARIM DENEME testleri, dilim 1 + 1b (Serdar 11 ve 12 Kas 2026; plan bolum 8 + gorev metinleri). ETSY YOK, ag yok, Drive yok.
TEST AGI (CLAUDE.md, main 5a3d85e): test surecinde ag BASTAN kapatilir (emsal scripts/sosyal/test_metricool_yedek.py:19-25); alt surecte kosan
Python kodu da ayni on ekle (AG_KAPALI) kosar. Kapatilan aga giden cagri AssertionError verir, test FAIL eder.
Her kapi bilinen PASS + bilinen FAIL ornegiyle denenir; test GERCEK fonksiyonu calistirir; mutasyon denemesi (kod bozulunca test FAIL).

Kullanim:
  python3 scripts/tasarim_deneme/test_tasarim_deneme.py                                   kaynaksiz testler; digerleri ATLANDI satiri basar
  python3 scripts/tasarim_deneme/test_tasarim_deneme.py --kaynak K [--ornament OD] [--katman P.png] [--zorunlu]
    K  = `git archive` klasoru: K/ay/scripts/ay_takvim (main a9b1323) ve K/motor/motor_gpt (siparis-gpt 6da763a)
    OD = scripts/printful klasoru (ornament-printful-katalog c950151): ornament tanimlariyla esdegerlik testleri
    P  = sembol katmani (yoksa yerel deneme sembolu test klasorunde uretilir, ~18 sn)
    --zorunlu: atlanan test varsa cikis 1
Paketler: is akisi surumleri (pillow 11.0.0 + raqm, numpy, opencv-python-headless, scipy, scikit-image, potracer).
"[sahte veri]" yazan testler kendi kurduklari maske / dosya / sozlukle yalniz kapi mantigini sinar; gercek motorlu PASS kanitlari t_motor'dadir.
"[bozulmus gercek veri]" yazan testler gercek kosunun verisini test icinde bozup GERCEK olcum fonksiyonunu cagirir (uretim yeniden kosmaz).
Kapsam DISI (dilim 1): onbellek, kayittan yeniden uretim, kombinasyon, adim 2 = adim 1, en kotu set on olcumu, is akisi kabuk adimlari,
ay takvimi test dosyasinin motorlu kosusu (ay takvimi dosyalari degismiyor)."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import shutil
import socket
import ssl  # noqa: F401  (ag kapatilmadan ONCE yuklenir: sonra yuklenirse socket sinifini bulamaz)
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms

AG_KAPALI = """import socket, ssl, urllib.request
def _ag_yok(*a, **k):
    raise AssertionError('gercek ag acilmaya calisildi')
socket.socket = _ag_yok
socket.create_connection = _ag_yok
socket.getaddrinfo = _ag_yok
urllib.request.urlopen = _ag_yok
"""
exec(AG_KAPALI)                                                              # TEST AGI: bu surecte ag bastan kapali (ice almalardan sonra)
ALT_SUREC = AG_KAPALI + "import runpy, sys\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n"   # alt surec: ag kapali + betik

BU = Path(__file__).resolve().parent
KOK = BU.parents[1]
sys.path.insert(0, str(BU))
import tasarim_deneme as TD  # noqa: E402
import tasarim_kapi as KP  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SAYAC = dict(pas=0, fail=0, atla=0)
URUN_DOSYA = KOK / 'data' / 'tasarim_deneme' / 'urun' / 'DENEME_YUVARLAK_1087.json'
ORNAMENT_SHA256 = {                                                          # `git archive c950151` ciktisindan; degisirse esdegerlik testi FAIL
    'ornament_ornek.py': 'eff1e16fcf8ff210ce26a952cb3f0838a27c0ea85cfccd3907509e293540e19f',
    'ornament_ornek2.py': 'd895c92522631937836310d96bb874518af9c1f2ee96894af4ea6a02552abb83',
    'ornament_ornek3.py': '895b7b5c516269a30406fa80cef220753713aba932da4d2370dd98cb7167358b',
    'ornament_ornek4.py': '6d905934a248ffd8c794f7cb2ccb5eaa504f749a0451e7111e15f88cb2a9dc88'}
# 5400 girdisi (test ici sozluk; gorsel uretimi yok): dikey sekil, Rg = guvenli kutunun kisa kenarinin yarisi = 2520
DIKEY = dict(ad='TEST_DIKEY_5400', sekil='dikey', baski_px=[5400, 7200], gercek_mm=[457.2, 609.6], mm_kaynak=dict(tur='resmi'),
             guvenli=dict(x0=180, y0=180, x1=5220, y1=7020), guvenli_pay_px=0, yasak=[], zemin='motor')


class Kes(Exception):
    """Test gozcusu: gereken kayit alininca cizimi erken keser (uretim kodunda yok)."""


def k(ad, kosul, bilgi=''):
    ok = bool(kosul)
    SAYAC['pas' if ok else 'fail'] += 1
    print(('PASS ' if ok else 'FAIL ') + ad + ('' if ok or bilgi == '' else f'  [{str(bilgi)[:500]}]'), flush=True)
    return ok


def atla(neden, n):
    SAYAC['atla'] += n
    print(f'ATLANDI: {neden} ({n} test)', flush=True)


def dur(fonk):
    """fonk'u calistirir; Dur (TD.Dur ya da AT.Dur) firlatirsa istisnayi, firlatmazsa None doner."""
    try:
        fonk()
    except Exception as e:                                                   # noqa: BLE001
        if TD._dur_mu(e):
            return e
        raise
    return None


def dur_mu(fonk, kod=None, girdi=None):
    e = dur(fonk)
    return bool(e is not None and (kod is None or e.kod == kod) and (girdi is None or bool(e.girdi) == girdi))


def urun_oku():
    return json.loads(URUN_DOSYA.read_text(encoding='utf-8'))


def sahte_sure(secenek, kurulum=20.0, mod='olcum', kimlik=None):
    """[sahte veri] olcum kosusu SURE kaydi (alanlar tam); kimlik = gercek urun girdisi + sabit kaynak sha'lari."""
    return dict(mod=mod, kimlik=kimlik or TD.kosu_kimligi(URUN_DOSYA), kurulum_sn=kurulum, toplam_sn=kurulum + sum(q['toplam_sn'] for q in secenek),
                secenek=[dict(dict(no=i, ad=f'SEC_{i:02d}_tekil', kod=None), **q) for i, q in enumerate(secenek, 1)],
                asama=dict(baslangic='2026-01-01T00:00:00Z', bitis='2026-01-01T00:05:00Z'))


def png_yaz(arr, yol, dpi=1087.0, icc=True, mod='RGB'):
    im = Image.fromarray(arr)
    if mod != 'RGB':
        im = im.convert(mod)
    kw = dict(dpi=(dpi, dpi))
    if icc:
        kw['icc_profile'] = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    im.save(yol, **kw)


# ---------------------------------------------------------------- kaynaksiz testler
def t_ag(td):
    dener = td / 'ag_dener.py'
    dener.write_text("import socket\nsocket.create_connection(('192.0.2.1', 9), 1)\n")
    pr = subprocess.run([sys.executable, '-c', ALT_SUREC, str(dener)], capture_output=True, text=True)
    k('test agi, ALT_SUREC on eki (bilinen FAIL yonu; inceleme 1b bulgu 2): bu on ekle kosan betik aga cikmaya calisirsa sifir olmayan cikis verir',
      pr.returncode != 0 and 'gercek ag acilmaya calisildi' in pr.stderr, (pr.returncode, pr.stderr[-200:]))
    sakin = td / 'ag_sakin.py'
    sakin.write_text("import sys\nprint('tamam', len(sys.argv))\n")
    pr = subprocess.run([sys.executable, '-c', ALT_SUREC, str(sakin), 'x'], capture_output=True, text=True)
    k('test agi, ALT_SUREC on eki (bilinen PASS): aga cikmayan betik cikis 0; betik kendi argumanlarini gorur', pr.returncode == 0 and pr.stdout.strip() == 'tamam 2',
      (pr.returncode, pr.stdout, pr.stderr[-200:]))
    for ack, f in (('socket.create_connection', lambda: socket.create_connection(('192.0.2.1', 9), 1)), ('socket.socket', lambda: socket.socket()),
                   ('socket.getaddrinfo', lambda: socket.getaddrinfo('ornek.invalid', 80)), ('urllib urlopen', lambda: urllib.request.urlopen('http://192.0.2.1/'))):
        try:
            f()
            ok = False
        except AssertionError as e:
            ok = 'gercek ag' in str(e)
        k(f'test agi (bilinen FAIL yonu): kapali aga {ack} cagrisi AssertionError verir (yakalanmazsa test FAIL eder)', ok)
    pr = subprocess.run([sys.executable, '-c', AG_KAPALI + "socket.create_connection(('192.0.2.1', 9), 1)\n"], capture_output=True, text=True)
    k('test agi, alt surec (bilinen FAIL yonu): ag kapatma on ekiyle kosan Python alt sureci aga cikmaya calisirsa sifir olmayan cikis verir',
      pr.returncode != 0 and 'gercek ag acilmaya calisildi' in pr.stderr, (pr.returncode, pr.stderr[-200:]))
    pr = subprocess.run([sys.executable, '-c', AG_KAPALI + "print('tamam')\n"], capture_output=True, text=True)
    k('test agi, alt surec (bilinen PASS): aga cikmayan alt surec cikis 0', pr.returncode == 0 and pr.stdout.strip() == 'tamam')


def t_urun():
    U = urun_oku()
    k('urun semasi: deneme girdisi dosyasi gecerli (yuvarlak 1087, varsayim etiketli)', TD.urun_dogrula(copy.deepcopy(U))['ad'] == 'DENEME_YUVARLAK_1087'
      and U['mm_kaynak']['tur'] == 'varsayım' and U['guvenli_pay_px'] == 3 and U['yasak'] == [] and U['alt_sinir']['yazi_mm'] == 1.5)
    k('urun semasi: test ici 5400 dikey sozluk gecerli (sema dikey sekli kabul eder)', TD.urun_dogrula(copy.deepcopy(DIKEY))['sekil'] == 'dikey'
      and TD.birim(DIKEY)[2] == 2520.0)

    def boz(**d):
        u = copy.deepcopy(U)
        for a_, v in d.items():
            if v is None:
                u.pop(a_, None)
            else:
                u[a_] = v
        return u
    kotu = [('eksik alan (guvenli)', boz(guvenli=None)), ('negatif px', boz(baski_px=[-1087, 1087])), ('px tam sayi degil', boz(baski_px=[1087.5, 1087])),
            ('eksen orani ayrisiyor', boz(gercek_mm=[25.4, 26.0])), ('desen disi ad', boz(ad='deneme yuvarlak')), ('ad yol iceriyor', boz(ad='A/../B')),
            ('bilinmeyen sekil', boz(sekil='ucgen')), ('bilinmeyen alan', boz(renk='mavi')), ('zemin motor degil', boz(zemin='duz')),
            ('mm_kaynak bilinmiyor', boz(mm_kaynak=dict(tur='tahmin'))), ('guvenli yaricap 0', boz(guvenli=dict(cx=543.5, cy=543.5, r=0))),
            ('yasak tur bilinmiyor', boz(yasak=[dict(tur='yildiz', cx=1, cy=1, r=1)])), ('alt_sinir negatif', boz(alt_sinir=dict(yazi_mm=-1, cizgi_mm=0.2))),
            ('pay bool', boz(guvenli_pay_px=True)), ('sozluk degil', [1])]
    for ack, u in kotu:
        k(f'bilinen FAIL urun semasi: {ack} -> girdi hatasi', dur_mu(lambda u=u: TD.urun_dogrula(u), 'girdi_urun', True))
    e = dur(lambda: TD.urun_dogrula(boz(ad='ENJEKTE\n::error::x')))
    k('urun hata mesajinda ham deger yok', e is not None and 'ENJEKTE' not in e.neden and '::' not in e.neden)
    k('mm formulu [varsayim girdisi; yalniz formul]: 1087 px = 25,4 mm; 64,19 px = 1,5 mm; 8,56 px = 0,2 mm',
      abs(TD.mm_px(U) * 1087 - 25.4) < 1e-9 and abs(1.5 / TD.mm_px(U) - 64.193) < 1e-3 and abs(0.2 / TD.mm_px(U) - 8.559) < 1e-3)
    k('tuval = urun baski alani (tam boy)', TD.tuval_boyu(U) == (1087, 1087) and TD.tuval_boyu(DIKEY) == (5400, 7200))
    k('kiris: merkez satirinda 2 x (Rg - pay); guvenli dairenin disindaki satirda 0', abs(TD.kiris(U, 543.5, 543.5) - 2 * 540.5) < 1e-6
      and TD.kiris(U, 1084.0, 1086.0) == 0.0 and abs(TD.kiris(U, 856.5, 896.8) - 2 * (540.5 ** 2 - 353.3 ** 2) ** 0.5) < 0.01)
    ay = dict(grup_x=0.0, grup_y=0.071)
    bm = KP.beklenen_merkez(U, ay)
    k('beklenen merkez (kapi, bagimsiz hesap) = uretimin grup merkezi (yuvarlanmis): [544, 582]',
      [int(round(bm[0])), int(round(bm[1]))] == list(TD.grup_merkezi(U, ay)) == [544, 582], (bm, TD.grup_merkezi(U, ay)))
    k('bilinen FAIL beklenen merkez: grup_y 0,10 ile ayni nokta cikmaz', [int(round(v)) for v in KP.beklenen_merkez(U, dict(grup_x=0.0, grup_y=0.10))] != [544, 582])


def t_butce():
    KIM = TD.kosu_kimligi(URUN_DOSYA)
    S = sahte_sure([dict(durum='tamam', toplam_sn=23.0), dict(durum='tamam', toplam_sn=25.0), dict(durum='DUR', kod='renk_uyum_piksel', toplam_sn=90.0)])
    b = TD.butce_kontrol(11, S, 900, False, KIM)
    k('[sahte veri] butce (bilinen PASS): 11 secenek, kurulum 20 + 11 x 25 = 295 sn <= 900; secenek suresi = cizimi BITENLERIN en buyugu; cizimden ONCE DUR veren '
      '(renk_uyum_piksel, 90 sn) hesaba GIRMEZ', b['istek_sn'] == 295.0 and b['secenek_sn'] == 25.0 and b['sigan_en_buyuk'] == 35, b)
    S33 = sahte_sure([dict(durum='tamam', toplam_sn=23.0), dict(durum='DUR', kod='kapi_sert', toplam_sn=33.0), dict(durum='DUR', kod='tasma', toplam_sn=90.0)])
    b33 = TD.butce_kontrol(11, S33, 900, False, KIM)
    k('[sahte veri] butce (Serdar 12 Kas girdi kurali a): cizimi biten DUR secenegi (kapi_sert, 33 sn) hesaba GIRER: 20 + 11 x 33 = 383 sn; bilinen FAIL yonu: '
      'ayni kayitta kod kapi_sert degilken (tasma) sure 23 sn kalir', b33['secenek_sn'] == 33.0 and b33['istek_sn'] == 383.0
      and TD.butce_kontrol(11, sahte_sure([dict(durum='tamam', toplam_sn=23.0), dict(durum='DUR', kod='tasma', toplam_sn=33.0)]), 900, False, KIM)['secenek_sn'] == 23.0, b33)
    k('[sahte veri] butce: yalniz cizimi biten DUR (kapi_sert) secenegi olan olcum kaydi kabul; 27 secenek x 33 + 20 = 911 sn > 900 -> girdi hatasi, sigan 26',
      TD.butce_kontrol(26, sahte_sure([dict(durum='DUR', kod='kapi_sert', toplam_sn=33.0)]), 900, False, KIM)['sigan_en_buyuk'] == 26
      and dur_mu(lambda: TD.butce_kontrol(27, sahte_sure([dict(durum='DUR', kod='kapi_sert', toplam_sn=33.0)]), 900, False, KIM), 'girdi_butce', True))
    kim_k = dict(KIM, kod_sha256=dict(KIM['kod_sha256'], **{'tasarim_kapi.py': '0' * 64}))
    k('[sahte veri] SURE kimligi (Serdar 12 Kas girdi kurali b): kimlikte kod sha256 var (2 kod dosyasi); kod sha256 farkliyken (bilinen FAIL) asil kosu baslamaz',
      sorted(KIM['kod_sha256']) == ['tasarim_deneme.py', 'tasarim_kapi.py'] and all(len(v) == 64 for v in KIM['kod_sha256'].values())
      and dur_mu(lambda: TD.butce_kontrol(2, S, 900, False, kim_k), 'girdi_butce', True) and TD.butce_kontrol(2, S, 900, False, KIM)['mod'] == 'asil')
    e = dur(lambda: TD.butce_kontrol(36, S, 900, False, KIM))
    k('[sahte veri] bilinen FAIL butce: 36 secenek (920 sn) > 900 -> uretmeden girdi hatasi; mesajda sigan en buyuk sayi 35', e is not None and e.kod == 'girdi_butce'
      and e.girdi and 'sigan en buyuk secenek sayisi 35' in e.neden and 'kirpilmadi' in e.neden, e)
    k('[sahte veri] butce sinirda: 35 secenek (895 sn) kabul', TD.butce_kontrol(35, S, 900, False, KIM)['istek_sn'] == 895.0)
    k('[sahte veri] bilinen FAIL butce: asil kosuda olcum SURE yok -> girdi hatasi', dur_mu(lambda: TD.butce_kontrol(2, None, 900, False, KIM), 'girdi_butce', True))
    k('[sahte veri] bilinen FAIL butce: olcum kosusunda tam cizimi biten secenek yok -> girdi hatasi',
      dur_mu(lambda: TD.butce_kontrol(2, sahte_sure([dict(durum='DUR', kod='tasma', toplam_sn=5.0)]), 900, False, KIM), 'girdi_butce', True))
    k('olcum kosusu: en cok 3 secenek', TD.butce_kontrol(3, None, 900, True)['mod'] == 'olcum' and dur_mu(lambda: TD.butce_kontrol(4, None, 900, True), 'girdi_butce', True))
    k('sabit: yerel butce 900 sn (Serdar 11 Kas soru 14 "A")', TD.BUTCE_SN == 900)
    k('[sahte veri] bilinen FAIL butce ust siniri (inceleme 1. tur bulgu 6): butce 901 sn verilemez (asil ve olcum kosusunda girdi hatasi); 600 sn (kucultme) kabul',
      dur_mu(lambda: TD.butce_kontrol(2, S, 901, False, KIM), 'girdi_butce', True) and dur_mu(lambda: TD.butce_kontrol(2, None, 901, True), 'girdi_butce', True)
      and TD.butce_kontrol(2, S, 600, False, KIM)['butce_sn'] == 600 and dur_mu(lambda: TD.butce_kontrol(2, S, 0, False, KIM), 'girdi_butce', True))
    S_asil = sahte_sure([dict(durum='tamam', toplam_sn=23.0)], mod='asil')
    k('[sahte veri] bilinen FAIL butce: SURE dosyasi olcum kosusundan degil (mod asil) -> girdi hatasi', dur_mu(lambda: TD.butce_kontrol(2, S_asil, 900, False, KIM), 'girdi_butce', True))
    k('[sahte veri] bilinen FAIL butce: SURE baska urun girdisi / baska kaynak icin olculmus -> girdi hatasi',
      dur_mu(lambda: TD.butce_kontrol(2, S, 900, False, dict(KIM, urun_sha256='0' * 64)), 'girdi_butce', True)
      and dur_mu(lambda: TD.butce_kontrol(2, S, 900, False, dict(KIM, motor_sha='0000000')), 'girdi_butce', True)
      and dur_mu(lambda: TD.butce_kontrol(2, S, 900, False, None), 'girdi_butce', True))
    k('[sahte veri] sure kaydi (bilinen PASS): alanlar tam, bitis >= baslangic', TD.sure_dogrula(copy.deepcopy(S))['mod'] == 'olcum')
    for ack, boz in (('eksik alan kurulum_sn', lambda d: d.pop('kurulum_sn')), ('eksik alan asama', lambda d: d.pop('asama')), ('eksik alan kimlik', lambda d: d.pop('kimlik')),
                     ('secenek kaydinda toplam_sn yok', lambda d: d['secenek'][0].pop('toplam_sn')), ('secenek kaydinda kod yok', lambda d: d['secenek'][0].pop('kod')), ('bitis baslangictan once', lambda d: d['asama'].update(bitis='2025-12-31T23:59:59Z')),
                     ('negatif sure', lambda d: d.update(toplam_sn=-1.0)), ('bos secenek listesi', lambda d: d.update(secenek=[]))):
        d = copy.deepcopy(S)
        boz(d)
        k(f'[sahte veri] bilinen FAIL sure kaydi: {ack} -> DUR sure_kayit; asil kosu bu kaydi kabul etmez', dur_mu(lambda d=d: TD.sure_dogrula(d), 'sure_kayit')
          and dur_mu(lambda d=d: TD.butce_kontrol(2, d, 900, False, KIM), 'girdi_butce', True))
    for ack, m in (('bozuk JSON', '{"taban": '), ('yinelenen anahtar', '{"taban": "B1", "taban": "B1"}'), ('NaN sabiti', '{"x": NaN}')):
        k(f'bilinen FAIL JSON: {ack} -> girdi hatasi', dur_mu(lambda m=m: TD._json_oku(m, 'istek'), 'girdi_json', True))


def t_urun_23mm():
    """D0 (Serdar 12 Kas 2026): yeni urun girdisi DENEME_YUVARLAK_1087_23MM (23,0 mm; guvenli r 515). Arac kodu degismedi; testler
    yeni DOSYAYI gercek fonksiyonlarla (urun_dogrula, mm_px, birim, kiris, kosu_kimligi, butce_kontrol) sinar. Eski dosya aynen kalir."""
    YENI = KOK / 'data' / 'tasarim_deneme' / 'urun' / 'DENEME_YUVARLAK_1087_23MM.json'
    ESKI_SHA = '0d170c64939240ed9129d0d4fbcc670249b5df9d1914b90e42d61bfb052c8d90'
    U = json.loads(YENI.read_text(encoding='utf-8'))
    D = TD.urun_dogrula(copy.deepcopy(U))

    def mm_sayi(u):                                                           # (baski alani mm, 1,5 mm px, 0,2 mm px), uc ondalik
        return (round(TD.mm_px(u) * 1087, 3), round(1.5 / TD.mm_px(u), 3), round(0.2 / TD.mm_px(u), 3))

    def geo_sayi(u):                                                          # (birim, merkez satirinda kiris, guvenli dairenin disindaki satirda kiris)
        return (TD.birim(u), round(TD.kiris(u, 543.5, 543.5), 6), TD.kiris(u, 1060.0, 1062.0))
    k('urun girdisi 23MM: dosya urun_dogrula\'dan gecer; alanlar gorev metniyle ayni (ad, mm kaynagi resmi, 23,0 x 23,0 mm, guvenli merkez 543,5 / 543,5 ve r 515, '
      'pay 3, yasak bos, alt sinir yazi 1,5 / cizgi 0,2 mm, zemin motor)',
      D['ad'] == 'DENEME_YUVARLAK_1087_23MM' and U['sekil'] == 'yuvarlak' and U['baski_px'] == [1087, 1087] and U['gercek_mm'] == [23.0, 23.0]
      and U['mm_kaynak']['tur'] == 'resmi' and (U['guvenli']['cx'], U['guvenli']['cy'], U['guvenli']['r']) == (543.5, 543.5, 515.0)
      and U['guvenli_pay_px'] == 3 and U['yasak'] == [] and U['alt_sinir']['yazi_mm'] == 1.5 and U['alt_sinir']['cizgi_mm'] == 0.2 and U['zemin'] == 'motor'
      and YENI.name == U['ad'] + '.json', {a_: U.get(a_) for a_ in ('ad', 'gercek_mm', 'guvenli_pay_px')})
    k('urun girdisi 23MM, mm formulu: 1087 px = 23,0 mm; 1,5 mm = 70,891 px; 0,2 mm = 9,452 px', mm_sayi(U) == (23.0, 70.891, 9.452), mm_sayi(U))
    k('urun girdisi 23MM, yerlesim birimi (543,5; 543,5; 515); merkez satirinda kiris 2 x (515 - 3) = 1024 px; guvenli dairenin disindaki satirda (y 1060 - 1062) kiris 0',
      geo_sayi(U) == ((543.5, 543.5, 515.0), 1024.0, 0.0), geo_sayi(U))
    U_mm = dict(copy.deepcopy(U), gercek_mm=[25.4, 25.4])
    U_r = copy.deepcopy(U)
    U_r['guvenli']['r'] = 543.5
    k('urun girdisi 23MM, bilinen FAIL: kopyada gercek_mm 25,4 yapilinca mm sayilari tutmaz (25,4; 64,193; 8,559); r 543,5 yapilinca birim ve kiris tutmaz '
      '(543,5; kiris 1081; y 1060 satirinda kiris > 0)', mm_sayi(U_mm) == (25.4, 64.193, 8.559) and mm_sayi(U_mm) != mm_sayi(U) and geo_sayi(U_mm) == geo_sayi(U)
      and geo_sayi(U_r)[0] == (543.5, 543.5, 543.5) and geo_sayi(U_r)[1] == 1081.0 and geo_sayi(U_r)[2] > 0 and mm_sayi(U_r) == mm_sayi(U),
      (mm_sayi(U_mm), geo_sayi(U_r)))
    KE, KY = TD.kosu_kimligi(URUN_DOSYA), TD.kosu_kimligi(YENI)
    S_eski = sahte_sure([dict(durum='tamam', toplam_sn=25.0)])                # olcum kaydi ESKI girdinin kimligini tasir
    k('[sahte veri] urun girdisi 23MM, kosu kimligi: yeni dosyanin kimligi eskisinden farkli (yalniz urun_sha256); eski girdinin kimligini tasiyan olcum kaydiyla '
      'yeni girdide asil kosu baslamaz (girdi hatasi)', KE != KY and KE['urun_sha256'] != KY['urun_sha256'] and {a_: v for a_, v in KE.items() if a_ != 'urun_sha256'}
      == {a_: v for a_, v in KY.items() if a_ != 'urun_sha256'} and S_eski['kimlik'] == KE and dur_mu(lambda: TD.butce_kontrol(3, S_eski, 900, False, KY), 'girdi_butce', True))
    k('[sahte veri] urun girdisi 23MM, bilinen FAIL yonu: olcum kaydi YENI girdinin kimligini tasiyinca ayni istekle asil kosu baslar; eski kayit eski girdiyle de baslar',
      (not dur_mu(lambda: TD.butce_kontrol(3, sahte_sure([dict(durum='tamam', toplam_sn=25.0)], kimlik=KY), 900, False, KY)))
      and not dur_mu(lambda: TD.butce_kontrol(3, S_eski, 900, False, KE)))
    eski_bayt = URUN_DOSYA.read_bytes()
    k('eski urun girdisi DEGISMEDI: DENEME_YUVARLAK_1087.json sha256 = dilim 1 / 1B kosularinin kaydindaki deger; bilinen FAIL yonu: tek bayt eklenmis icerik '
      'ayni sha256\'yi vermez', hashlib.sha256(eski_bayt).hexdigest() == ESKI_SHA and TD.sha_dosya(URUN_DOSYA) == ESKI_SHA
      and hashlib.sha256(eski_bayt + b' ').hexdigest() != ESKI_SHA and KE['urun_sha256'] == ESKI_SHA, TD.sha_dosya(URUN_DOSYA))


def t_olcer_sahte():
    U = urun_oku()
    W = H = 1087
    ic = np.zeros((40, 200), np.float32); ic[5:35, 5:195] = 1.0
    M_ic = dict(a=KP.tuvale(ic, 400, 500, W, H), b=KP.tuvale(ic, 400, 600, W, H))
    son = np.zeros((H, W, 3), np.uint8)
    t = KP.tasma_olc(U, M_ic, son, son, dict(a=0, b=0))
    k('[sahte veri] tasma (bilinen PASS): guvenli dairenin icindeki iki oge -> uc olcum de 0', t['PASS'] and t['toplam'] == dict(isik_0=0, isik_8=0, goruntu_farki=0, tuval_disi=0), t['toplam'])
    M_dis = dict(a=KP.tuvale(ic, 400, 500, W, H), b=KP.tuvale(ic, 880, 100, W, H))   # sag ust kose: guvenli dairenin disinda
    son2 = son.copy(); son2[100:140, 880:1080] = 200
    t2 = KP.tasma_olc(U, M_dis, son2, son, dict(a=0, b=7))
    k('[sahte veri] bilinen FAIL tasma: koseye itilmis oge -> isik 0 > 0, isik 8 >= isik 0, goruntu farki > 0, tuval disi 7; FAIL',
      (not t2['PASS']) and t2['toplam']['isik_0'] > 0 and t2['toplam']['isik_8'] >= t2['toplam']['isik_0'] and t2['toplam']['goruntu_farki'] > 0
      and t2['toplam']['tuval_disi'] == 7 and t2['oge']['a']['isik_0'] == 0 and t2['oge']['b']['isik_0'] > 0, t2['toplam'])
    sinir = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    sinir[(np.hypot(xx + 0.5 - 543.5, yy + 0.5 - 543.5) < 538.0) & (np.hypot(xx + 0.5 - 543.5, yy + 0.5 - 543.5) > 536.0)] = 1.0
    t3 = KP.tasma_olc(U, dict(c=sinir), son, son, dict(c=0))
    k('[sahte veri] tasma: guvenli sinirin 2,5 px icindeki cizgi isik 0 ile 0, isik 8 ile > 0 (iki olcum ayri deger verir)',
      t3['toplam']['isik_0'] == 0 and t3['toplam']['isik_8'] > 0, t3['toplam'])
    Uy = copy.deepcopy(U); Uy['yasak'] = [dict(tur='daire', cx=500.0, cy=515.0, r=10.0, halka_haric=True)]
    t4 = KP.tasma_olc(Uy, dict(halka=M_ic['a'], isim=M_ic['a']), son, son, {})
    k('[sahte veri] yasak bolge: ayni maske "halka" adiyla (halka haric) 0, baska adla > 0', t4['oge']['halka']['isik_0'] == 0 and t4['oge']['isim']['isik_0'] > 0, t4['oge'])
    sira = [('a', M_ic['a']), ('b', M_ic['b'])]
    k('[sahte veri] cakisma (bilinen PASS): ayrik iki oge -> takvim tanimi 0 px, ornament tanimi 0 cift', KP.cakisma_takvim(sira) == 0 and KP.cakisma_ornament(M_ic) == {})
    ust = dict(a=M_ic['a'], b=KP.tuvale(ic, 500, 520, W, H))
    co = KP.cakisma_ornament(ust)
    k('[sahte veri] bilinen FAIL cakisma: binen iki oge -> takvim tanimi > 0 px; ornament tanimi cift listesi + cift basina piksel',
      KP.cakisma_takvim([('a', ust['a']), ('b', ust['b'])]) == int(((ust['a'] > 0.02) & (ust['b'] > 0.02)).sum()) > 0 and list(co) == ['a/b'] and co['a/b'] > 0, co)
    yakin = dict(sembol=M_ic['a'], isim=KP.tuvale(ic, 400, 532, W, H))      # 2 px aralik: takvim tanimi 0, ornament (sembol 7 x 7 genisletme) > 0
    k('[sahte veri] iki tanim ayri olcer: 2 px aralikli oge takvim taniminda 0, ornament taniminda (7 x 7) cift verir',
      KP.cakisma_takvim([('isim', yakin['isim']), ('sembol', yakin['sembol'])]) == 0 and list(KP.cakisma_ornament(yakin)) == ['sembol/isim'])
    cp = KP.cift_px_olc(dict(a=ust['a'], b=ust['b'], c=M_ic['b']))
    k('[sahte veri] BILGI cift basina cakisma: binen cift = iki maskenin kesisim pikseli (> 0), ayrik ciftler 0; butun ciftler adlariyla',
      cp == {'a/b': int(((ust['a'] > 0.02) & (ust['b'] > 0.02)).sum()), 'a/c': 0, 'b/c': 0} and cp['a/b'] > 0, cp)
    kare = np.ones((10, 10), np.float32)
    My = dict(isimler=M_ic['a'], kucuk1=KP.tuvale(kare, 300, 510, W, H), kucuk2=KP.tuvale(kare, 420, 510, W, H))   # isim murekkebi x 405 - 594, y 505 - 534
    ky = KP.kucuk_yazi_olc(My, ['isimler'])
    k('[sahte veri] BILGI kucuk burc - yazi en az uzakligi: 96 px uzaktaki kucuk1 -> 96,0; yaziya binen kucuk2 -> 0 (binme)',
      ky == {'kucuk1/isimler': 96.0, 'kucuk2/isimler': 0.0}, ky)
    k('[sahte veri] bilinen FAIL yonu: kucuk1 5 px yaklasinca uzaklik 91,0 olur (olcum yere duyarli); murekkebi olmayan yazi maskesi atlanir',
      KP.kucuk_yazi_olc(dict(My, kucuk1=KP.tuvale(kare, 305, 510, W, H)), ['isimler'])['kucuk1/isimler'] == 91.0
      and KP.kucuk_yazi_olc(dict(My, metin_1=np.zeros((H, W), np.float32)), ['isimler', 'metin_1']) == ky)
    cubuk = np.zeros((40, 160), np.uint8); cubuk[12:36, 8:152] = 1
    w = KP.sirt_genislik(cubuk, 4)
    k('[sahte veri] sirt genisligi: 4 kat ornekli 24 px cubuk -> en ince ~ 5,75 px (2 x (12 - 0,5) / 4)', abs(float(w.min()) - 5.75) < 0.01, float(w.min()))
    c = KP.cizgi_olc(np.pad(np.ones((6, 80), np.float32), 8))
    k('[sahte veri] cizgi olcumu: 6 px kalin cizgi -> 1. yuzdelik 5 - 7 px', c['p1_px'] is not None and 5.0 <= c['p1_px'] <= 7.0, c)


def t_cikti_sahte(td):
    U = urun_oku()
    a = np.zeros((1087, 1087, 3), np.uint8)
    png_yaz(a, td / 'iyi.png')
    r = KP.cikti_olc(td / 'iyi.png', U)
    k('[sahte veri] cikti (bilinen PASS): 1087 x 1087, dpi etiketi 1087, RGB, sRGB', r['PASS'], r)
    png_yaz(np.zeros((1000, 1087, 3), np.uint8), td / 'boyut.png')
    png_yaz(a, td / 'dpi.png', dpi=300.0)
    png_yaz(a, td / 'rgba.png', mod='RGBA')
    png_yaz(a, td / 'profilsiz.png', icc=False)
    for ad in ('boyut', 'dpi', 'rgba', 'profilsiz'):
        k(f'[sahte veri] bilinen FAIL cikti: {ad} -> FAIL', not KP.cikti_olc(td / f'{ad}.png', U)['PASS'])


def sahte_ozet(td, n_tamam=2):
    U = urun_oku()
    rng = np.random.default_rng(3)
    sec = []
    for i in range(1, 4):
        tamam = i <= n_tamam
        s = dict(no=i, ad=f'SEC_{i:02d}_tekil' if i < 3 else 'SEC_03_grup', tur='tekil' if i < 3 else 'grup', durum='tamam' if tamam else 'DUR',
                 kod=None if tamam else 'kapi_sert', neden=None if tamam else 'sert kapi FAIL: 2_grup', ayar=dict(taban='B1'), degisen=dict(logo=1.0) if i == 2 else {},
                 geri_donus=[], satir=None if i < 3 else 0, sutun=None if i < 3 else 0, png_sha256=None)
        if tamam:
            png_yaz(rng.integers(0, 255, (300, 300, 3), dtype=np.uint8), td / f"{s['ad']}.png")
            s['png_sha256'] = TD.sha_dosya(td / f"{s['ad']}.png")
            s['olcum_ozet'] = dict(yazi_en_kucuk_mm=0.8, isim_kuculme=1.0, cizgi_mm=dict(en_ince=0.01, p1=0.02, ortanca=0.06),
                                   sinir_alti=dict(yazi=2, cizgi_en_ince=7, cizgi_p1=7, cizgi_ortanca=6), tasma_px=dict(isik_0=11, isik_8=22, goruntu_farki=33, tuval_disi=0),
                                   cakisma=dict(takvim_px=692, ornament_cift=2, ornament_px=1067), grup_yazi_en_az_px=44.2, cikti='PASS', olcer_fail=['cakisma'],
                                   cift_px={'isimler/metin_1': 0, 'kucuk1/sembol': 315, 'kucuk2/sembol': 377}, kucuk_yazi_px=dict(isim=30.5, metin=120.0), isim_guvenli_disinda=False)
        else:
            s['olcum_ozet'] = dict(sert_fail=['2_grup'], kok_neden='grup ogesi tuvalden tasiyor: halka; konum farki 10.665 px', kapi2_boyut_fark=0.188)
        sec.append(s)
    return dict(urun=U, taban='B1', taban_etiket=TD.B1_ETIKET, geri_donus=['isim_duzen iki_yan -> tek_satir'], mm_px=TD.mm_px(U), secenek=sec)


def t_pafta_sahte(td):
    oz = sahte_ozet(td)
    bilgi, hucreler = TD.pafta_yaz(oz, td, td / 'PAFTA.jpg', hucre=200)
    bek = {s['no']: cv2.resize(np.asarray(Image.open(td / f"{s['ad']}.png").convert('RGB')), (200, 200), interpolation=cv2.INTER_AREA) for s in oz['secenek'][:2]}
    k('[sahte veri] pafta: tek sayfa, 3 hucre (2 gorsel + 1 DUR hucresi), <= 3 MB', bilgi['hucre'] == 3 and (td / 'PAFTA.jpg').stat().st_size <= TD.PAFTA_AZAMI_BAYT
      and sorted(hucreler) == [1, 2])
    k('[sahte veri] pafta hucresi = kaydedilmis son gorselin TEK adim INTER_AREA kucultulmusu (bagimsiz yeniden kucultmeyle birebir)',
      all(np.array_equal(hucreler[n], bek[n]) for n in bek))
    E = TD.etiket_satirlari(oz['secenek'][1])
    k('[sahte veri] hucre etiketi: tasma uc deger, cakisma iki tanim, cikti kapisi, degisen anahtar; vurgu / siralama sozcugu yok',
      any('isik 0: 11' in e and 'isik 8: 22' in e and 'goruntu farki: 33' in e for e in E) and any('takvim tanimi 692 px' in e and '2 cift, 1067 px' in e for e in E)
      and any('cikti kapisi PASS' in e for e in E) and any('logo=1.0' in e for e in E)
      and not any(s_ in ' '.join(E).lower() for s_ in ('onerilen', 'en iyi', 'puan', 'tavsiye')), E)
    k('[sahte veri] hucre etiketi (dilim 1b): cakisan cift adlari + pikselleri (0 olan cift etikete yazilmaz), kucuk burc - yazi en az uzakligi; K3 notu yalniz isim '
      'guvenli alanin disindayken', 'cakisan cift px (alfa > 0,02): kucuk1/sembol 315, kucuk2/sembol 377' in E and 'kucuk burc - yazi en az uzaklik px: isim 30.5 | metin 120.0' in E
      and 'isim guvenli alan disinda' not in E
      and 'isim guvenli alan disinda' in TD.etiket_satirlari(dict(oz['secenek'][1], olcum_ozet=dict(oz['secenek'][1]['olcum_ozet'], isim_guvenli_disinda=True))), E)
    Ed = TD.etiket_satirlari(oz['secenek'][2], 'varsayım')
    k('[sahte veri] K2 etiketi hucrede: DUR kaydinda kok neden varsa yazar; yoksa (bilinen FAIL yonu) yazmaz; kapi kodu ayni kalir',
      'grup ogesi tuvalden tasiyor: halka; konum farki 10.665 px' in Ed and 'DUR kapi_sert: 2_grup' in Ed
      and not any('tuvalden tasiyor' in e for e in TD.etiket_satirlari(dict(oz['secenek'][2], olcum_ozet=dict(sert_fail=['2_grup'], kok_neden=None)))), Ed)
    k('[sahte veri] K1: DUR veren secenegin hucresinde olculen boy kosulu farki yazar; olcum yoksa (bilinen FAIL yonu) satir yok',
      'kapi 2 boy kosulu farki 0.188 px' in Ed
      and not any('boy kosulu' in e for e in TD.etiket_satirlari(dict(oz['secenek'][2], olcum_ozet=dict(sert_fail=['2_grup'], kok_neden=None, kapi2_boyut_fark=None)))), Ed)
    k('[sahte veri] sert DUR veren secenegin hucre etiketi: "DUR" + kapi kodu + kapi adi (secenek gizlenmez); neden satiri kesilmez',
      'DUR kapi_sert: 2_grup' in Ed and 'sert kapi FAIL: 2_grup' in Ed, Ed)
    k('[sahte veri] mm kaynagi "varsayim" etiketi HUCREDE (plan 5.1); kaynak resmi iken yok (bilinen FAIL yonu)',
      'mm kaynagi: varsayim' in TD.etiket_satirlari(oz['secenek'][1], 'varsayım') and 'mm kaynagi: varsayim' in Ed
      and 'mm kaynagi: varsayim' not in TD.etiket_satirlari(oz['secenek'][1], 'resmi'))
    f13 = TD._font(13)
    uzun = 'olcer FAIL: ' + ', '.join(['cakisma', 'isim', 'gercek_olcu', 'tasma', 'tuval_tasma', 'metin_genis', 'grup_yazi', 'kontrast', 'tek_doku', 'yildiz', 'cikti'])
    kr = TD._kir(uzun, f13, 196)
    k('[sahte veri] etiket kirma (inceleme 1. tur bulgu 11): hucreden genis satir (bilinen FAIL yonu: kirilmadan once genis) hucre genisligine bolunur, metin kesilmez / kaybolmaz',
      f13.getlength(uzun) > 196 and len(kr) > 1 and all(f13.getlength(q) <= 196 for q in kr) and ' '.join(kr) == uzun, kr)
    kx = TD._kir('x' * 200, f13, 196)
    k('[sahte veri] etiket kirma: tek sozcuk hucreden genisse harften bolunur (kayip yok)', ''.join(kx) == 'x' * 200 and len(kx) > 1 and all(f13.getlength(q) <= 196 for q in kx))
    td0 = td / 'hepsi_dur'; td0.mkdir()
    oz0 = sahte_ozet(td0, n_tamam=0)
    TD.pafta_yaz(oz0, td0, td0 / 'P0.jpg', hucre=200)

    def renkli(yol):
        a = np.asarray(Image.open(yol).convert('RGB')).astype(np.int16)
        return int(((np.abs(a[..., 0] - a[..., 1]) > 24) | (np.abs(a[..., 1] - a[..., 2]) > 24)).sum())
    k('[sahte veri] pafta tek renk, vurgu yok (plan 5.1): yalniz DUR hucreli sayfada renkli piksel 0; gorselli sayfada > 0 (olcum renk gorebiliyor)',
      renkli(td0 / 'P0.jpg') == 0 and renkli(td / 'PAFTA.jpg') > 0, (renkli(td0 / 'P0.jpg'), renkli(td / 'PAFTA.jpg')))
    B = TD.pafta_basligi(oz)
    k('[sahte veri] pafta basligi: sinir notu, VARSAYIM etiketi, B1 bilinen cakisma, geri donus, "siralama, puan, oneri yok"',
      TD.SINIR_NOTU_ASCII in B[0] and 'VARSAYIM' in B[1] and 'BILINEN CAKISMA' in B[2] and 'geri donus: isim_duzen' in B[3] and 'siralama, puan, oneri yok' in B[4], B)
    oz2 = copy.deepcopy(oz); oz2['urun']['mm_kaynak']['tur'] = 'resmi'
    k('[sahte veri] bilinen FAIL yonu: mm kaynagi resmi iken baslikta VARSAYIM etiketi yok', 'VARSAYIM' not in TD.pafta_basligi(oz2)[1])
    png_yaz(np.zeros((300, 300, 3), np.uint8), td / 'SEC_01_tekil.png')     # dosya degisti: sha OZET'tekiyle ayni degil
    k("[sahte veri] bilinen FAIL pafta: OZET'teki sha256 ile uyusmayan son gorsel -> DUR pafta_sha", dur_mu(lambda: TD.pafta_yaz(oz, td, td / 'P2.jpg', hucre=200), 'pafta_sha'))
    (td / 'SEC_02_tekil.png').unlink()
    oz3 = copy.deepcopy(oz); oz3['secenek'] = oz3['secenek'][1:]
    k('[sahte veri] bilinen FAIL pafta: son gorsel dosyasi yok -> DUR', dur_mu(lambda: TD.pafta_yaz(oz3, td, td / 'P3.jpg', hucre=200), 'pafta_sha'))
    td2 = td / 'buyuk'; td2.mkdir()
    oz4 = sahte_ozet(td2)
    eski = TD.PAFTA_AZAMI_BAYT
    TD.PAFTA_AZAMI_BAYT = 2000
    try:
        k('[sahte veri] bilinen FAIL pafta: kalite 70 ile de sinir asiliyor -> DUR pafta_boyut, dosya yazilmaz',
          dur_mu(lambda: TD.pafta_yaz(oz4, td2, td2 / 'P4.jpg', hucre=200), 'pafta_boyut') and not (td2 / 'P4.jpg').exists())
    finally:
        TD.PAFTA_AZAMI_BAYT = eski


# ---------------------------------------------------------------- kaynakli testler (ay takvimi modulu ice alinir)
def t_kaynak(K, td):
    sha = TD.baglan(K)
    AT, ATK = TD.AT, TD.ATK
    k('sabit kaynak kapisi (bilinen PASS): ay takvimi 2 + motor 17 dosyanin sha256 tablosu tutuyor', len(sha) == 19
      and len(TD.KAYNAK_SHA256['motor']) == len(AT.MOTOR_DOSYA) + 1 and all(f in TD.KAYNAK_SHA256['motor'] for f in AT.MOTOR_DOSYA), len(sha))
    k('tek modul: aracin AT nesnesi = kapi kodunun gordugu U = sys.modules kaydi (ikinci kopya yok)', ATK.U is AT and KP._at() == (AT, ATK)
      and sys.modules['ay_takvim_ornek'] is AT)
    k('yuzey (bilinen PASS): ice alinan 26 adin imzasi beklenenle ayni', TD.yuzey_kontrol(AT, ATK) == [] and len(TD.YUZEY) == 26)
    asil = AT.kutu
    AT.kutu = lambda a: None
    try:
        k('bilinen FAIL yuzey: imzasi degismis fonksiyon -> fark listesinde', TD.yuzey_kontrol(AT, ATK) == ['AT.kutu'])
    finally:
        AT.kutu = asil
    kop = td / 'kaynak_kopya'
    for grup, yol in (('ay', TD.AY_YOL), ('motor', TD.MOTOR_YOL)):
        for ad in TD.KAYNAK_SHA256[grup]:
            (kop / yol / ad).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(K) / yol / ad, kop / yol / ad)
    k('sabit kaynak kapisi: birebir kopya klasor tabloyu gecer', len(TD.kaynak_dogrula(kop)) == 19)
    k('bilinen FAIL tek modul: ayni modul baska klasorden ikinci kez baglanamaz -> DUR kaynak_cift', dur_mu(lambda: TD.baglan(kop), 'kaynak_cift', False))
    f = kop / TD.AY_YOL / 'ay_takvim_kapi.py'
    f.write_bytes(f.read_bytes() + b'\n')
    k('bilinen FAIL sabit kaynak: ay takvimi dosyasinda tek bayt fark -> DUR kaynak_sha', dur_mu(lambda: TD.kaynak_dogrula(kop), 'kaynak_sha', False))
    shutil.copyfile(Path(K) / TD.AY_YOL / 'ay_takvim_kapi.py', f)
    kl = kop / TD.MOTOR_YOL / 'KILIT_GPTGIRDI.json'
    j = json.loads(kl.read_text()); j['AYAR']['esit'] = 'goz'
    kl.write_text(json.dumps(j))
    k('bilinen FAIL motor / KILIT: KILIT dali degismis kopya -> DUR kaynak_sha (Motor kurulmadan)', dur_mu(lambda: TD.kaynak_dogrula(kop), 'kaynak_sha', False))
    k('bilinen FAIL KILIT (ikinci savunma): ayni kopyada AT.Motor da DUR kilit verir', dur_mu(lambda: AT.Motor(kop / TD.MOTOR_YOL), 'kilit'))
    shutil.copyfile(Path(K) / TD.MOTOR_YOL / 'KILIT_GPTGIRDI.json', kl)
    (kop / TD.MOTOR_YOL / 'girdi' / 'LOGO_1.png').unlink()
    k('bilinen FAIL motor dosyasi: logo dosyasi eksik -> DUR kaynak_eksik', dur_mu(lambda: TD.kaynak_dogrula(kop), 'kaynak_eksik', False))
    pv = TD.Image.__version__
    k('ortam kapisi (bilinen PASS): pillow 11.0.0 + raqm', TD.ortam_kapisi()['pillow'] == '11.0.0')
    asil_fc = TD.features.check
    TD.features.check = lambda ad: False if ad == 'raqm' else asil_fc(ad)
    try:
        k('bilinen FAIL ortam: raqm bayragi kapali (sahte ortam) -> DUR ortam', dur_mu(TD.ortam_kapisi, 'ortam', False))
    finally:
        TD.features.check = asil_fc
    TD.Image.__version__ = '12.3.0'
    try:
        k('bilinen FAIL ortam: pillow surumu 12.3.0 -> DUR ortam', dur_mu(TD.ortam_kapisi, 'ortam', False))
    finally:
        TD.Image.__version__ = pv


def t_ayar():
    B1 = TD.TABAN['B1']
    AY, geri = TD.ayar_dogrula(dict(taban='B1'))
    k('ayar: taban B1 verilince eksik anahtarlar tabandan (halka merkez, halka_r 0,884, grup_y 0,071, kucuk_v 0,37, isim_cap 0,0742, metin_y 0,817)',
      AY['grup_merkez'] == 'halka' and AY['halka_r'] == 0.884 and AY['grup_r'] is None and AY['grup_y'] == 0.071 and AY['kucuk_v'] == 0.37 and AY['kucuk_u'] == 'poster'
      and AY['isim_cap'] == 0.0742 and AY['metin_y'] == 0.817 and AY['satirlar'] == ['JUNE 14, 2025'] and (AY['isim1'], AY['isim2']) == ('EMILY', 'JAMES')
      and abs(AY['metin_cap'] - 0.0742 * 144 / 169.5) < 1e-5 and sorted(AY) == sorted(TD.AYAR_ANAHTAR))
    k('geri donus (plan 3.3): B1 emsali iki_yan + isim arasi logo -> tek_satir + logo yok, iki etiket; DUR yok',
      AY['isim_duzen'] == 'tek_satir' and AY['logo'] == 'yok' and len(geri) == 2 and all('->' in g for g in geri), geri)
    AY2, geri2 = TD.ayar_dogrula(dict(taban='B1', logo=1.0, logo_yer='kucuk_arasi'))
    k('logo kucuk_arasi acik: carpan 1,0 kabul; geri donus yalniz isim duzeni', AY2['logo'] == 1.0 and AY2['logo_yer'] == 'kucuk_arasi' and len(geri2) == 1)
    AY3, geri3 = TD.ayar_dogrula(dict(taban='B1', logo=1.25, logo_yer='isim_arasi'))
    k('geri donus: logo_yer isim_arasi + carpan istenirse logo yok ve etiket (bilinen FAIL yonu: etiketsiz gecmez)', AY3['logo'] == 'yok' and len(geri3) == 2)
    k('halka_r / grup_r: grup_r verilince halka_r None (tam biri)', TD.ayar_dogrula(dict(taban='B1', grup_r=0.9))[0]['halka_r'] is None
      and TD.ayar_dogrula(dict(taban='B1', halka_r=0.5))[0]['grup_r'] is None)
    k('ayar: aralik uclari kabul (halka_r 0,30 / 1,20; kucuk_v 0,20 / 1,30; logo 0,50 / 2,00; grup_y -1 / 1; kucuk_u "poster")',
      all(TD.ayar_dogrula(dict(taban='B1', **{a_: x_}))[0][a_] == x_ for a_, x_ in (('halka_r', 0.30), ('halka_r', 1.20), ('kucuk_v', 0.20), ('kucuk_v', 1.30),
                                                                                    ('grup_y', -1.0), ('grup_y', 1.0), ('kucuk_u', 'poster'), ('kucuk_v', 'poster')))
      and all(TD.ayar_dogrula(dict(taban='B1', logo=x_, logo_yer='kucuk_arasi'))[0]['logo'] == x_ for x_ in (0.50, 2.00)))
    kotu = [('taban yok', dict(logo='yok')), ('bilinmeyen taban (B2 bu dilimde yok)', dict(taban='B2')), ('bilinmeyen anahtar', dict(taban='B1', renk='mavi')),
            ('ogeler anahtari (kombinasyon dilim 2)', dict(taban='B1', ogeler=['isim'])), ('aralik disi (halka_r 1,21)', dict(taban='B1', halka_r=1.21)),
            ('aralik disi (kucuk_v 0,19)', dict(taban='B1', kucuk_v=0.19)), ('aralik disi (logo 2,01)', dict(taban='B1', logo=2.01)),
            ('yanlis tur (halka_r metin)', dict(taban='B1', halka_r='0.9')), ('yanlis tur (bool)', dict(taban='B1', kucuk_oran=True)),
            ('yanlis tur (liste)', dict(taban='B1', grup_y=[0.1])), ('serbest sozcuk yanlis (kucuk_u "orta")', dict(taban='B1', kucuk_u='orta')),
            ('sonsuz', dict(taban='B1', halka_r=float('inf'))), ('NaN', dict(taban='B1', grup_y=float('nan'))), ('cok buyuk tam sayi 10^400', dict(taban='B1', halka_r=10 ** 400)),
            ('halka_r ve grup_r birlikte', dict(taban='B1', halka_r=0.8, grup_r=0.9)), ('KAPALI: halka_kalinlik 2,0', dict(taban='B1', halka_kalinlik=2.0)),
            ('KAPALI: halka_centik yumusak', dict(taban='B1', halka_centik='yumusak')), ('grup_merkez taninmiyor', dict(taban='B1', grup_merkez='sol')),
            ('logo_yer taninmiyor (ust)', dict(taban='B1', logo_yer='ust')), ('iki satir metin (dilim 1 tek satir)', dict(taban='B1', satirlar=['a', 'b'])),
            ('metin_tur yok + satir', dict(taban='B1', metin_tur='yok', satirlar=['a'])), ('satirlar metin', dict(taban='B1', satirlar='a')),
            ('isim sayi', dict(taban='B1', isim1=5)), ('kabuk karakteri iceren isim', dict(taban='B1', isim1='A; rm -rf /')),
            ('kabuk karakteri iceren satir', dict(taban='B1', satirlar=['$(id)'])), ('sozluk degil', [1])]
    for ack, d in kotu:
        k(f'bilinen FAIL ayar: {ack} -> girdi hatasi', dur_mu(lambda d=d: TD.ayar_dogrula(d), None, True))
    k('halka_kalinlik 1,0 ve halka_centik ozgun acikca verilebilir (kapali ayarin tek kabul edilen degeri)',
      TD.ayar_dogrula(dict(taban='B1', halka_kalinlik=1.0, halka_centik='ozgun'))[0]['halka_kalinlik'] == 1.0)
    iz = 'ENJEKTE\n::error::x'
    mesaj = []
    for d in ({'taban': 'B1', iz: 1}, dict(taban='B1', halka_r=iz), dict(taban=iz), dict(taban='B1', isim1=iz), dict(taban='B1', satirlar=[iz]),
              dict(taban='B1', grup_merkez=iz), dict(taban='B1', kucuk_u=iz)):
        e = dur(lambda d=d: TD.ayar_dogrula(d))
        mesaj.append('DUR YOK' if e is None else f'{e.kod}: {e.neden}')
    k('enjeksiyon (bilinen FAIL): kabuk karakteri / satir sonu / log komutu iceren deger -> DUR; mesajda HAM girdi yok, yalniz tur + anahtar sirasi',
      all('ENJEKTE' not in m and '::' not in m and '\n' not in m and m != 'DUR YOK' for m in mesaj) and mesaj[0].endswith('bilinmeyen anahtar #2'), mesaj)
    sec = TD.istek_kur(dict(taban='B1', tekil=[dict(satirlar=["You & me, 2019!"], metin_tur='mesaj')]))
    k('enjeksiyon (bilinen PASS): izinli ozel karakterli ornek metin kabul; dosya adi KODDAN (SEC_01_tekil), girdiden degil',
      sec[0]['ayar']['satirlar'] == ["You & me, 2019!"] and sec[0]['ad'] == 'SEC_01_tekil')
    sec = TD.istek_kur(dict(taban='B1', tekil=[{}, dict(logo=1.0, logo_yer='kucuk_arasi')],
                            izgara=dict(halka_r_carpan=[0.85, 1.0, 1.15], grup_y_fark=[-0.05, 0, 0.05])))
    k('istek: 2 tekil + 3 x 3 grup izgarasi = 11 secenek; uretim sirasi: once tekiller, sonra izgara (satir = boyut, sutun = yer); adlar koddan',
      len(sec) == 11 and [s['ad'] for s in sec[:3]] == ['SEC_01_tekil', 'SEC_02_tekil', 'SEC_03_grup'] and [(s['satir'], s['sutun']) for s in sec[2:5]] == [(0, 0), (0, 1), (0, 2)]
      and sec[6]['ayar']['halka_r'] == 0.884 and sec[6]['ayar']['grup_y'] == 0.071 and sec[2]['ayar']['halka_r'] == round(0.884 * 0.85, 6)
      and sec[10]['ayar']['grup_y'] == round(0.071 + 0.05, 6) and sec[6]['degisen'] == dict(halka_r=0.884, grup_y=0.071))
    k('izgaranin taban hucresi (x1,00 / 0) tabanla ayni ayar (yeniden uretilir)', sec[6]['ayar'] == sec[0]['ayar'])
    gk_ = TD.istek_kur(dict(taban='B1', tekil=[{}], izgara=dict(kucuk_oran_carpan=[0.8, 1.0, 1.2], kucuk_v_fark=[-0.08, 0, 0.08, 0.16, 0.24, 0.32])))
    k('kucuk burc izgarasi (Serdar 12 Kas): 1 tekil + 3 x 6 = 19 secenek; adlar SEC_NN_kucuk; satir = boyut adimi (kucuk_oran carpani), sutun = yer adimi '
      '(kucuk_v farki); hucre ayari tabandan YALNIZ kucuk_oran / kucuk_v ile ayrilir',
      len(gk_) == 19 and all(q['tur'] == 'kucuk' and q['ad'] == f"SEC_{q['no']:02d}_kucuk" for q in gk_[1:])
      and [(q['satir'], q['sutun']) for q in gk_[1:]] == [(i, j) for i in range(3) for j in range(6)]
      and [q['ayar']['kucuk_v'] for q in gk_[1:7]] == [0.29, 0.37, 0.45, 0.53, 0.61, 0.69] and [gk_[i]['ayar']['kucuk_oran'] for i in (1, 7, 13)] == [0.8, 1.0, 1.2]
      and all({k_ for k_ in q['ayar'] if q['ayar'][k_] != gk_[0]['ayar'][k_]} <= {'kucuk_oran', 'kucuk_v'} for q in gk_[1:]), [q['ad'] for q in gk_[:3]])
    k('kucuk burc izgarasinin taban hucresi (carpan 1,0; fark 0) tabanla TAM ayni ayar', gk_[8]['ayar'] == gk_[0]['ayar'] and gk_[8]['satir'] == 1 and gk_[8]['sutun'] == 1)
    TD.TABAN['T_GRUP'] = dict(TD.TABAN['B1'], grup_merkez='grup')
    try:
        k('[sahte veri] bilinen FAIL kucuk burc izgarasi: taban halka merkez modunda degilse girdi hatasi ("tek oge degisir" yalniz halka_r + halka merkezde)',
          dur_mu(lambda: TD.istek_kur(dict(taban='T_GRUP', izgara=dict(kucuk_oran_carpan=[1.0], kucuk_v_fark=[0]))), 'girdi_istek', True))
    finally:
        del TD.TABAN['T_GRUP']
    ikot = [('taban yok', dict(tekil=[{}])),
            ('iki izgara turu birlikte', dict(taban='B1', izgara=dict(halka_r_carpan=[1], grup_y_fark=[0], kucuk_oran_carpan=[1], kucuk_v_fark=[0]))),
            ('izgara turleri karisik (halka_r_carpan + kucuk_v_fark)', dict(taban='B1', izgara=dict(halka_r_carpan=[1], kucuk_v_fark=[0]))),
            ('kucuk burc izgarasi eksik eksen', dict(taban='B1', izgara=dict(kucuk_oran_carpan=[1]))),
            ('kucuk burc izgarasi aralik disi (kucuk_v 0,37 - 0,20 = 0,17 < 0,20)', dict(taban='B1', izgara=dict(kucuk_oran_carpan=[1.0], kucuk_v_fark=[-0.20]))),
            ('kucuk burc izgarasi aralik disi (kucuk_oran x 2 = 2,0 > 1,8)', dict(taban='B1', izgara=dict(kucuk_oran_carpan=[2.0], kucuk_v_fark=[0]))), ('bilinmeyen alan', dict(taban='B1', tekil=[{}], sira=[2, 1])), ('secenek yok', dict(taban='B1')),
            ('tekil icinde taban', dict(taban='B1', tekil=[dict(taban='B1')])), ('izgara bilinmeyen anahtar', dict(taban='B1', izgara=dict(isim_cap_carpan=[1], grup_y_fark=[0]))),
            ('izgara 8 deger', dict(taban='B1', izgara=dict(halka_r_carpan=[1, 2, 3, 4, 5, 6, 7, 8], grup_y_fark=[0]))),
            ('izgara yinelenen deger', dict(taban='B1', izgara=dict(halka_r_carpan=[1, 1], grup_y_fark=[0]))),
            ('izgara aralik disi (halka_r x 1,4 = 1,24)', dict(taban='B1', izgara=dict(halka_r_carpan=[1.4], grup_y_fark=[0]))),
            ('2. secenekte bilinmeyen anahtar', dict(taban='B1', tekil=[{}, dict(x=1)]))]
    for ack, d in ikot:
        k(f'bilinen FAIL istek: {ack} -> girdi hatasi (uretim yok)', dur_mu(lambda d=d: TD.istek_kur(d), None, True))
    e = dur(lambda: TD.istek_kur(dict(taban='B1', tekil=[{}, dict(zz=1)])))
    k('istek hata mesaji secenek ve anahtar sirasini verir (secenek 2: bilinmeyen anahtar #1), ham girdi yok', e is not None and e.neden == 'secenek 2: bilinmeyen anahtar #1', e)


def t_ornament(OD):
    OD = Path(OD)
    ok = all((OD / f).is_file() and hashlib.sha256((OD / f).read_bytes()).hexdigest() == h for f, h in ORNAMENT_SHA256.items())
    k('ornament kaynak sha sabit (4 dosya, c950151)', ok)
    if not ok:
        return
    spec = importlib.util.spec_from_file_location('ornek4_test', OD / 'ornament_ornek4.py')
    o4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(o4)
    rng = np.random.default_rng(5)
    m = (cv2.GaussianBlur(rng.random((240, 320)).astype(np.float32), (0, 0), 6) > 0.5).astype(np.uint8)
    k('esdegerlik: sirt_genislik = ornament_ornek4.py sirt_genislik (O4:164-168), ayni girdiyle birebir', np.array_equal(KP.sirt_genislik(m, 4), o4.sirt_genislik(m, 4)))
    src = (OD / 'ornament_ornek4.py').read_text()
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'sirt_genislik')
    ns = dict(cv2=cv2, np=np)
    exec(ast.get_source_segment(src, fn).replace('dt[r] - 0.5', 'dt[r]'), ns)                    # mutasyon: yarim piksel duzeltmesi cikarildi
    k('bilinen FAIL esdegerlik: bir satiri degismis kaynak kopyasi ayni ciktiyi vermez (test FAIL verebiliyor)',
      not np.array_equal(KP.sirt_genislik(m, 4), ns['sirt_genislik'](m, 4)))
    U954 = dict(ad='TEST_ORNAMENT_954', sekil='yuvarlak', baski_px=[954, 954], gercek_mm=[80.772, 80.772], mm_kaynak=dict(tur='resmi'),
                guvenli=dict(cx=o4.CX, cy=o4.CY, r=o4.GUV_R), guvenli_pay_px=o4.PAY,
                yasak=[dict(tur='daire', ad='delik', cx=o4.DELIK[0], cy=o4.DELIK[1], r=o4.DELIK[2], halka_haric=True),
                       dict(tur='ust_cizgi', ad='ust_cizgi', y=o4.UST_YASAK, halka_haric=True)], zemin='motor')
    TD.urun_dogrula(copy.deepcopy(U954))
    Y = o4.yasak_m()
    disi, yasak = KP.guvenli_disi(U954, 954, 954, o4.PAY)
    k('esdegerlik: yasak bolge maskeleri = ornament_ornek4.py yasak_m (O4:219-224), 954 sabitleriyle birebir (guvenli disi, delik, ust cizgi)',
      np.array_equal(disi, Y['guvenli_disi']) and np.array_equal(yasak[0][1], Y['delik']) and np.array_equal(yasak[1][1], Y['ust_cizgi']))
    U955 = copy.deepcopy(U954); U955['guvenli']['r'] = o4.GUV_R + 1
    k('bilinen FAIL esdegerlik: yaricapi 1 px buyutulmus urun girdisi ayni maskeyi vermez', not np.array_equal(KP.guvenli_disi(U955, 954, 954, o4.PAY)[0], Y['guvenli_disi']))
    o4.YASAK = Y
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    yy, xx = np.mgrid[0:954, 0:954]
    rr = np.hypot(xx + 0.5 - o4.CX, yy + 0.5 - 500.0)
    halka = ((rr > 368) & (rr < 372)).astype(np.float32)                    # halka: guvenli siniri (r 377) yakininda; delik ve ust cizgiden gecer
    blok = np.ones((40, 120), np.float32)
    E = dict(halka=(None, halka, 0, 0), sembol=(None, np.ones((200, 200), np.float32), 376, 380), isim1=(None, blok, 300, 582),
             isim2=(None, blok, 421, 600), tarih=(None, blok, 430, 110), kose=(None, blok, 760, 120))
    Mo, yb, cak, _ = o4.kapi(E)
    M2 = {ad: (a if ad == 'halka' else KP.tuvale(a, x, y, 954, 954)) for ad, (_, a, x, y) in E.items()}
    bos = np.zeros((954, 954, 3), np.uint8)
    t = KP.tasma_olc(U954, M2, bos, bos, {})
    k('esdegerlik: tasma (isik payi 8) = ornament_ornek4.py kapi yasak piksel toplami (O4:239-254; halka yalniz guvenli daire)',
      t['toplam']['isik_8'] == yb['guvenli_disi'] + yb['delik'] + yb['ust_cizgi'] > 0 and t['toplam']['isik_0'] < t['toplam']['isik_8'], (t['toplam'], yb))
    rgb0 = np.zeros((954, 954, 3), np.uint8)
    rgb1 = rgb0.copy()
    rgb1[100:260, 380:600] = 90                                               # delik + ust cizgi bolgesi (halka buradan gecer)
    rgb1[430:470, 20:90] = 90                                                 # guvenli dairenin disi
    yb_g, _ = o4.goruntu_yasak(rgb1, rgb0, halka)
    tg = KP.tasma_olc(U954, M2, rgb1, rgb0, {})
    k('esdegerlik (inceleme 1. tur bulgu 7): tasma goruntu farki = ornament_ornek4.py goruntu_yasak toplami (O4:425-433; sinir payi yok, halka 8 px genisletilip haric)',
      tg['toplam']['goruntu_farki'] == sum(yb_g.values()) and all(v > 0 for v in yb_g.values()), (tg['toplam'], yb_g))
    k('bilinen FAIL esdegerlik goruntu farki: halka maskesi verilmezse (haric tutma yok) ayni sayi cikmaz',
      KP.tasma_olc(U954, {a_: m_ for a_, m_ in M2.items() if a_ != 'halka'}, rgb1, rgb0, {})['toplam']['goruntu_farki'] != sum(yb_g.values()))
    co = KP.cakisma_ornament(M2)
    k('esdegerlik: ornament cakisma tanimi cift listesi = ornament_ornek4.py kapi cakisma listesi (O4:255-269); cift basina piksel > 0',
      sorted(co) == sorted(cak) and {'halka/tarih', 'sembol/isim1', 'isim1/isim2'} <= set(cak) and all(v > 0 for v in co.values()), (sorted(co), sorted(cak)))
    k('GLOW_R 8 = arac isik payi 8; PAY 3 = urun girdisi guvenli payi (ornament degerleri, oranlanmadan)', o4.GLOW_R == KP.ISIK_PAY[1] == 8 and o4.PAY == urun_oku()['guvenli_pay_px'] == 3)


# ---------------------------------------------------------------- motorlu testler (gercek cizim)
def grup_verisi(ort, AY):
    """Kapi 2 grup bolumu icin veri (altin cizimi olmadan): uretimin grup_yerlestir fonksiyonu + kapinin bekledigi alanlar."""
    Y = TD.grup_yerlestir(ort, AY)
    return dict(urun=ort.urun, ayar=AY, cift=TD.CIFT, sembol=Y['sembol'], grup_oge=Y['grup_oge'], merkez=Y['merkez'], hedef_r=Y['hedef_r'],
                sembol_alan=Y['sembol_alan'], s_olc=ort.s_olc, motor=ort.md, grup_bilgi=Y['G']['bilgi'])


def t_motor(K, katman, td):
    AT, ATK = TD.AT, TD.ATK
    U = urun_oku()
    KS = str(K)
    istek = td / 'istek1.json'
    istek.write_text(json.dumps(dict(taban='B1', tekil=[dict(logo=1.0, logo_yer='kucuk_arasi')])))
    # --- A: gercek `kos` komutu (olcum kosusu, 1 secenek): OZET, SURE, OLCUM_TUMU, pafta
    cA = td / 'A'
    rc = TD.main(['kos', '--kaynak', KS, '--urun', str(URUN_DOSYA), '--istek', str(istek), '--katman', str(katman), '--cikti', str(cA), '--olcum'])
    oz = json.loads((cA / 'OZET.json').read_text(encoding='utf-8')) if (cA / 'OZET.json').is_file() else {}
    sA = (oz.get('secenek') or [{}])[0]
    k('GERCEK MOTORLU PASS: kos (olcum, B1 + logo kucuk_arasi) -> cikis 0, secenek tamam, son gorsel 1087 x 1087, sert kapilar PASS',
      rc == 0 and sA.get('durum') == 'tamam' and (cA / 'SEC_01_tekil.png').is_file() and Image.open(cA / 'SEC_01_tekil.png').size == (1087, 1087)
      and sA['olcum_ozet']['sert_fail'] == [], (rc, sA.get('durum'), sA.get('kod'), sA.get('neden')))
    if sA.get('durum') != 'tamam':
        return
    om = json.loads((cA / 'SEC_01_tekil_OLCUM.json').read_text(encoding='utf-8'))
    ol = om['kapi']['olcer']
    k('kos ciktilari: OZET (sinir notu, sha tablolari, tam ayar), SURE (kurulum, secenek suresi), OLCUM_TUMU, AYAR, tek sayfa pafta <= 3 MB',
      oz['not_'] == TD.SINIR_NOTU and len(oz['kaynak_sha256']) == 19 and oz['secenek'][0]['ayar']['logo'] == 1.0 and oz['sembol_katmani']['tur'] == 'deneme'
      and json.loads((cA / 'SURE.json').read_text())['secenek'][0]['toplam_sn'] > 0 and 'SEC_01_tekil' in json.loads((cA / 'OLCUM_TUMU.json').read_text(encoding='utf-8'))['secenek']
      and (cA / 'AYAR.json').is_file() and (cA / oz['pafta']['dosya']).stat().st_size <= TD.PAFTA_AZAMI_BAYT and oz['pafta']['hucre'] == 1)
    sj = json.loads((cA / 'SURE.json').read_text())
    k('GERCEK sure kaydi (bilinen PASS): kosunun yazdigi SURE.json alanlari tam, bitis >= baslangic, mod olcum, kimlik = urun girdisi + kaynak sha',
      TD.sure_dogrula(copy.deepcopy(sj))['mod'] == 'olcum' and sj['kimlik'] == TD.kosu_kimligi(URUN_DOSYA) and sj['secenek'][0]['durum'] == 'tamam'
      and sj['secenek'][0]['kod'] is None and sj['kimlik']['kod_sha256'] == oz['kod_sha256'] and sj['cizimi_biten_en_cok_sn'] == sj['secenek'][0]['toplam_sn'])
    k('GERCEK: olcer kapilar PASS (tek doku dE00 <= 2, kontrast >= 4,5, yazim farki, duz renk, yildiz, oge sayisi, grup - yazi >= 12 px, metin tabani, '
      'metin genisligi, tasma)', all(ol[q]['PASS'] for q in ('tek_doku', 'kontrast', 'yazim', 'duz_renk', 'yildiz', 'oge_sayisi', 'grup_yazi',
                                                             'metin_taban', 'metin_genis', 'tasma')), {q: ol[q]['PASS'] for q in ol})
    k('GERCEK K4 (bilinen PASS): cikti kapisi SERT listede ve PASS (1087 x 1087, dpi etiketi, RGB, sRGB); olcer listesinde yok',
      om['kapi']['sert']['cikti']['PASS'] and 'cikti' not in ol and om['ozet']['cikti'] == 'PASS' and sorted(om['kapi']['sert']) == ['2_grup', '2_sembol', 'cikti'])
    bl = om['bilgi']
    k('GERCEK BILGI olcumleri (esik yok): cift basina cakisma: sembol - kucuk burc ciftleri > 0 ve toplami = takvim tanimi (B1 bilinen cakisma); isim - metin 0; '
      'kucuk burc - yazi en az uzakligi > 0; OZET kaydinda cift adlari, ornament ciftleri ve yerlesen yildiz sayisi',
      bl['cift_px']['kucuk1/sembol'] > 0 and bl['cift_px']['kucuk2/sembol'] > 0 and bl['cift_px']['isimler/metin_1'] == 0
      and sum(bl['cift_px'].values()) == ol['cakisma']['takvim_binme_piksel'] and len(bl['cift_px']) == 21
      and om['ozet']['cift_px'] == bl['cift_px'] and om['ozet']['kucuk_yazi_px']['isim'] == min(bl['kucuk_yazi_uzaklik']['kucuk1/isimler'], bl['kucuk_yazi_uzaklik']['kucuk2/isimler']) > 0
      and om['ozet']['kucuk_yazi_px']['metin'] > 0 and om['ozet']['cakisma']['ornament_ciftler'] == ol['cakisma']['ornament_cift']
      and om['ozet']['yildiz_sayi'] == ol['yildiz']['sayi'] > 0 and sA['olcum_ozet']['yildiz_sayi'] == ol['yildiz']['sayi'], (bl['cift_px'], om['ozet']['kucuk_yazi_px']))
    k('GERCEK bilinen FAIL (olcer; gorsel VAR): B1 BILINEN CAKISMA: kucuk burclar ana sembole biner -> takvim tanimi > 0 px, ornament tanimi sembol / kucuk ciftleri',
      (not ol['cakisma']['PASS']) and ol['cakisma']['takvim_binme_piksel'] > 0 and 'sembol/kucuk1' in ol['cakisma']['ornament_cift']
      and 'sembol/kucuk2' in ol['cakisma']['ornament_cift'] and (cA / 'SEC_01_tekil.png').is_file(), ol['cakisma'])
    k('GERCEK bilinen FAIL (olcer; gorsel VAR): gercek olcu uyarisi: isim buyuk harfi 0,94 mm < 1,5 mm isaretli; isim kapisi FAIL; secenek gizlenmedi',
      om['oge']['isimler']['yazi_sinir_alti'] and abs(om['oge']['isimler']['buyuk_harf_mm'] - 0.942) < 0.005 and not ol['isim']['PASS'] and not ol['gercek_olcu']['PASS']
      and 'gercek_olcu' in om['ozet']['olcer_fail'] and om['ozet']['durum'] == 'tamam' and (cA / 'SEC_01_tekil_isaret.jpg').is_file())
    k('OLCUM: mm kaynagi "varsayım" etiketi, oge kayitlarinda metnin kendisi yok (yalniz karakter sayisi), logo / isim buyuk harf orani ve temizlik farki yazili',
      om['mm_kaynak']['tur'] == 'varsayım' and 'EMILY' not in json.dumps(om['oge']) and om['oge']['isimler']['karakter'] == 13
      and om['oge']['logo']['logo_isim_buyuk_harf_orani'] > 0 and om['oge']['logo']['temizlik']['degisen_piksel'] >= 0 and om['oge']['halka']['nominal_kalinlik_px'] > 0)
    bb = om['kapi']['sert']['2_grup']['boyut_bagimsiz']
    k('kapi 2 boy (bilinen PASS, gercek kosu; inceleme 1. tur bulgu 2): OLCULEN halka yaricapi = halka_r x Rg = 480,45 px (ayardan, uretimden bagimsiz), fark <= 2 px',
      bb['PASS'] and bb['mod'] == 'halka_r' and abs(bb['beklenen_px'] - 0.884 * 543.5) < 1e-3 and bb['fark'] <= 2.0 and om['ozet']['kapi2_boyut_fark'] == bb['fark'], bb)
    k('kapi 2 grup: olculen en buyuk fark <= 2 px (pay); logo 4. oge; beklenen merkez [543.5, 582.09], uretim [544, 582]',
      om['kapi']['sert']['2_grup']['PASS'] and om['kapi']['sert']['2_grup']['olculen_fark_en_buyuk'] <= 2.0 and list(om['kapi']['sert']['2_grup']['oge']) == ['halka', 'kucuk1', 'kucuk2', 'logo']
      and om['kapi']['sert']['2_grup']['uretim_merkez'] == [544, 582], om['kapi']['sert']['2_grup'].get('olculen_fark_en_buyuk'))

    # --- B: `uret` komutu (yeniden uretim) + calisma anindaki GERCEK degerlerin kaydi (plan 5.1 uc halka; inceleme bulgusu 3)
    kayit = dict(katman=[], zemin=[], boya=[], veri=None, ort=None, png=None)
    asil = dict(oge_katman=AT.Motor.oge_katman, zemin_radyal=AT.zemin_radyal, boya=AT.boya, olc=KP.olc, Ortam=TD.Ortam)

    def w_katman(self, a_k, k_, rng, har, qa_goz, ad='yazi'):
        kayit['katman'].append(dict(ad=ad, boyut=tuple(a_k.shape), k=int(k_)))
        return asil['oge_katman'](self, a_k, k_, rng, har, qa_goz, ad)

    def w_zemin(md, P, Wc, Hc, f, cx, cy):
        kayit['zemin'].append((int(Wc), int(Hc)))
        return asil['zemin_radyal'](md, P, Wc, Hc, f, cx, cy)

    def w_boya(taban, ogeler, dis=None):
        kayit['boya'].append(tuple(taban.shape))
        return asil['boya'](taban, ogeler, dis)

    def w_olc(veri):
        kayit['veri'] = veri
        kayit['png'] = Image.open(veri['png']).size                          # diske YAZILAN son gorselin gercek boyutu
        if kayit.get('kes') == 'olc':                                        # mutasyon kosulari: cizim ve kayit bitti; kapi olcumu oncesi kes
            raise Kes()
        return asil['olc'](veri)

    class OrtamKayit(asil['Ortam']):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            kayit['ort'] = self

    def gozcu(ac):
        AT.Motor.oge_katman = w_katman if ac else asil['oge_katman']
        AT.zemin_radyal = w_zemin if ac else asil['zemin_radyal']
        AT.boya = w_boya if ac else asil['boya']
        KP.olc = w_olc if ac else asil['olc']
        TD.Ortam = OrtamKayit if ac else asil['Ortam']

    def gercek_yol(kayit_, veri, png_boyut, urun):
        """3. halka: calisma aninda OLCULEN degerler, ayardan BAGIMSIZ hesaplanan beklenenle karsilastirilir. Doner (tamam mi, ayrinti)."""
        Wb, Hb = urun['baski_px']
        cx, cy, Rg = urun['guvenli']['cx'], urun['guvenli']['cy'], urun['guvenli']['r']
        AYv = veri['ayar']
        bek = {}
        for o in veri['ogeler']:                                              # yazi: k = buyuk harf x k ~ 298 px olacak tam sayi (AT:577, POSTER_CAP)
            cap = (AYv['isim_cap'] if o['tur'] == 'isim' else AYv['metin_cap']) * Rg
            bek[o['ad']] = max(1, int(round(298.0 / cap)))
        R_c = json.loads((Path(veri['motor']) / 'cember.json').read_text())['cember']['R']
        so = AYv['halka_r'] * Rg / R_c                                        # grup: k = floor(1 / olcek), kaynaktan buyuk olamaz (AT:1265-1267)
        for o in veri['grup_oge']:
            s_o = so * (float(AYv['kucuk_oran']) if o['ad'].startswith('kucuk') else float(AYv['logo']) if o['ad'] == 'logo' else 1.0)
            kk = max(1, int(np.floor(1.0 / s_o)))
            h_, w_ = o['kaynak'].shape
            while kk > 1 and (o['A'].shape[1] * kk > w_ or o['A'].shape[0] * kk > h_):
                kk -= 1
            bek[o['ad']] = kk
        sira = veri['ogeler'] + veri['grup_oge']
        ayr = dict(katman=len(kayit_['katman']), beklenen=len(sira), zemin=kayit_['zemin'], boya=kayit_['boya'], png=png_boyut)
        ok = len(kayit_['katman']) == len(sira)
        for kay, o in zip(kayit_['katman'], sira):
            kb = bek[o['ad']]
            if kay['k'] != kb or kay['boyut'] != (o['A'].shape[0] * kb, o['A'].shape[1] * kb):
                ok = False
                ayr.setdefault('fark', []).append((o['ad'], kay, kb))
        ok = ok and kayit_['zemin'] == [(Wb, Hb)] and kayit_['boya'] == [(Hb, Wb, 3)] and tuple(png_boyut) == (Wb, Hb)
        return ok, ayr

    cB = td / 'B'
    gozcu(True)
    try:
        rcB = TD.main(['uret', '--kaynak', KS, '--ozet', str(cA / 'OZET.json'), '--secenek', '1', '--katman', str(katman), '--cikti', str(cB)])
    finally:
        gozcu(False)
    yj = json.loads((cB / 'SEC_01_tekil_YENIDEN.json').read_text()) if (cB / 'SEC_01_tekil_YENIDEN.json').is_file() else {}
    k("ayni girdi, ayni cikti + tek secenek yeniden uretimi (2. halka): `uret --ozet --secenek 1` yeni kurulumla ayni PNG sha256'yi verir",
      rcB == 0 and yj.get('ayni') is True and yj.get('png_sha256') == sA['png_sha256'] == TD.sha_dosya(cB / 'SEC_01_tekil.png'), yj)
    veri, ort = kayit['veri'], kayit['ort']
    if veri is None or ort is None:
        k('gozcu kaydi alindi', False)
        return
    okB, ayrB = gercek_yol(kayit, veri, kayit['png'], U)
    k('kural kontrolu 3. halka (bilinen PASS): calisma aninda OLCULEN k kat cizim boyutlari (6 altin oge), zemin ve boya tuvali, PNG boyutu = ayardan bagimsiz beklenen '
      f"(k: {[c['k'] for c in kayit['katman']]})", okB and len(kayit['katman']) == 6, ayrB)
    k("OZET'teki k ve tuval degerleri calisma aninda olculenle ayni", sA['k'] == {o['ad']: c['k'] for o, c in zip(veri['ogeler'] + veri['grup_oge'], kayit['katman'])}
      and sA['tuval'] == [1087, 1087] and sA['altin_sirasi'] == ['isimler', 'metin_1', 'halka', 'kucuk1', 'kucuk2', 'logo'])
    sec1 = TD.istek_kur(dict(taban='B1', tekil=[dict(logo=1.0, logo_yer='kucuk_arasi')]))[0]

    def mutasyon(kur, geri):
        """Mutasyon TEK uretim fonksiyonunun (secenek_uret) ICINDE: bagimlilik bozulur, uretim GERCEKTEN calisir (grup, zemin, altin, boya, PNG
        kaydi). Gozcu calisma anindaki degerleri ve diske YAZILAN PNG'nin boyutunu kaydeder; kosu kapi olcumunden hemen once kesilir.
        Doner (3. halka sonucu, ayrinti). Hicbir deger test tarafindan doldurulmaz (inceleme 1. tur bulgu 1)."""
        eski = dict(kayit)
        kayit.clear(); kayit.update(katman=[], zemin=[], boya=[], veri=None, ort=None, png=None, kes='olc')
        kur()
        gozcu(True)
        try:
            try:
                TD.secenek_uret(ort, sec1, td / 'mut')
            except Kes:
                pass
        finally:
            gozcu(False)
            geri()
        kay3 = dict(kayit)
        kayit.clear(); kayit.update(eski)
        if kay3['veri'] is None or kay3['png'] is None:
            return False, dict(neden='uretim PNG kaydina ulasmadi', katman=len(kay3['katman']))
        return gercek_yol(kay3, kay3['veri'], kay3['png'], U)

    okn, ayrn = mutasyon(lambda: None, lambda: None)
    k('kural kontrolu 3. halka KONTROL (bilinen PASS, mutasyon testleriyle AYNI yol): hicbir sey bozulmadan uretim -> PASS (mutasyon testlerindeki FAIL '
      'mutasyonun kendisinden gelir)', okn, ayrn)
    asil_ck, asil_tb, asil_gk = AT.cizim_katsayisi, TD.tuval_boyu, AT.grup_kur
    okm, ayr = mutasyon(lambda: setattr(AT, 'cizim_katsayisi', lambda c: max(1, asil_ck(c) - 2)), lambda: setattr(AT, 'cizim_katsayisi', asil_ck))
    k('bilinen FAIL kural kontrolu 3. halka (mutasyon uretim fonksiyonunun icinde): yazi cizim katsayisi k dusuruldu -> OLCULEN k beklenenden farkli, FAIL',
      (not okm) and sorted(f_[0] for f_ in ayr.get('fark', [])) == ['isimler', 'metin_1'] and ayr.get('zemin') == [(1087, 1087)] and tuple(ayr.get('png', ())) == (1087, 1087), ayr)

    def gk_bozuk(*a, **kw):
        G = asil_gk(*a, **kw)
        for o in G['ogeler']:
            if o['ad'] == 'halka' and o['k'] > 1:
                o['k'] -= 1
        return G
    okm, ayr = mutasyon(lambda: setattr(AT, 'grup_kur', gk_bozuk), lambda: setattr(AT, 'grup_kur', asil_gk))
    k('bilinen FAIL kural kontrolu 3. halka: halkanin k kat cizimi 1 dusuruldu -> OLCULEN halka k beklenenden farkli, FAIL',
      (not okm) and [f_[0] for f_ in ayr.get('fark', [])] == ['halka'], ayr)
    okm, ayr = mutasyon(lambda: setattr(TD, 'tuval_boyu', lambda u: (asil_tb(u)[0] + 64, asil_tb(u)[1] + 64)), lambda: setattr(TD, 'tuval_boyu', asil_tb))
    k('bilinen FAIL kural kontrolu 3. halka: tuval urun baski alanindan 64 px buyuk -> OLCULEN zemin, boya ve YAZILAN PNG 1151 x 1151, FAIL',
      (not okm) and ayr.get('zemin') == [(1151, 1151)] and ayr.get('boya') == [(1151, 1151, 3)] and tuple(ayr.get('png', ())) == (1151, 1151) and 'fark' not in ayr, ayr)
    # 2. halka AYRI SUREC (plan 5.1; inceleme 1. tur bulgu 8): komut satirindan yeni surecte yeniden uretim
    cB2 = td / 'B2'
    pr = subprocess.run([sys.executable, '-c', ALT_SUREC, str(BU / 'tasarim_deneme.py'), 'uret', '--kaynak', KS, '--ozet', str(cA / 'OZET.json'), '--secenek', '1',
                         '--katman', str(katman), '--cikti', str(cB2)], capture_output=True, text=True)
    yj2 = json.loads((cB2 / 'SEC_01_tekil_YENIDEN.json').read_text()) if (cB2 / 'SEC_01_tekil_YENIDEN.json').is_file() else {}
    k("2. halka AYRI SUREC (ag kapali on ekle): `uret` komutu yeni Python surecinde ayni PNG sha256'yi verir (cikis 0)",
      pr.returncode == 0 and yj2.get('ayni') is True and yj2.get('png_sha256') == sA['png_sha256'], (pr.returncode, yj2, pr.stdout[-300:]))

    # --- C: degisen ayar -> farkli cikti (B1 logosuz); bilinen cakisma B1 tabaninda da var
    sec0 = TD.istek_kur(dict(taban='B1', tekil=[{}]))[0]
    rC = TD.secenek_uret(ort, sec0, td / 'C')
    k('bilinen FAIL yonu (ayni girdi, ayni cikti): bir anahtari degismis ayar (logo yok) farkli PNG sha256 verir; logosuz grup 3 oge',
      rC['durum'] == 'tamam' and rC['png_sha256'] != sA['png_sha256'] and rC['altin_sirasi'] == ['isimler', 'metin_1', 'halka', 'kucuk1', 'kucuk2'], (rC['durum'], rC['kod']))
    k('geri donus etiketi kosu kaydinda (B1 taban ayari: iki etiket)', len(rC['geri_donus']) == 2 and len(sA['geri_donus']) == 1)

    # --- kapi 2 sembol bolumu: gercek veriyle PASS + mutasyonlar
    img = np.asarray(Image.open(cB / 'SEC_01_tekil.png').convert('RGB'))
    S = veri['sembol']
    diger = [(o['x'], o['y'], o['A']) for o in veri['ogeler'] + veri['grup_oge']]
    s2, g, yan = KP.sembol_kapisi(img, veri['altinsiz'], S, diger, veri['katman'], veri['s_olc'])
    k('kapi 2 sembol (bilinen PASS, gercek): en boy farki <= 0,005, renk farki <= 1, kenar sinir disi 0, kaynak sha ayni, yeniden kucultme birebir',
      s2['PASS'] and s2['en_boy_fark'] <= 0.005 and s2['renk_fark_en_buyuk'] <= 1 and s2['kenar_sinir_disi_piksel'] == 0 and s2['yeniden_kucultme_birebir'], s2)
    tam = (S['a'] >= 0.999)
    ys, xs = np.nonzero(tam[:40])                                             # sembolun ust kismi: baska oge ortmez
    img2 = img.copy()
    p0 = img2[S['y'] + ys[0], S['x'] + xs[0]].astype(np.int16)
    img2[S['y'] + ys[0], S['x'] + xs[0]] = (p0 - 2 if p0.min() >= 2 else p0 + 2).astype(np.uint8)
    k('bilinen FAIL kapi 2 sembol: son gorselde tam alfa sembol pikseli 2 seviye degismis (esik 1) -> FAIL', not KP.sembol_kapisi(img2, veri['altinsiz'], S, diger, veri['katman'], veri['s_olc'])[0]['PASS'])
    kat2 = td / 'DENEME_degismis_ana.png'
    kim = np.asarray(Image.open(veri['katman'])).copy()
    kim[kim.shape[0] // 2, kim.shape[1] // 2, 0] ^= 1
    Image.fromarray(kim, 'RGBA').save(kat2)
    shutil.copyfile(str(veri['katman']) + '.json', str(kat2) + '.json')
    s2k = KP.sembol_kapisi(img, veri['altinsiz'], S, diger, kat2, veri['s_olc'])[0]
    k('bilinen FAIL kapi 2 sembol: katman dosyasi degismis (sha256 farkli) -> FAIL', (not s2k['PASS']) and not s2k['kaynak_sha_ayni'])
    Se = dict(S, a=cv2.resize(S['a'], (int(S['a'].shape[1] * 1.03), S['a'].shape[0]), interpolation=cv2.INTER_AREA),
              rgb=cv2.resize(S['rgb'], (int(S['a'].shape[1] * 1.03), S['a'].shape[0]), interpolation=cv2.INTER_AREA))
    s2e = KP.sembol_kapisi(img, veri['altinsiz'], Se, diger, veri['katman'], veri['s_olc'])[0]
    k('bilinen FAIL sekil degismez: yatayda %3 esnetilmis sembol -> en boy farki > 0,005, FAIL', (not s2e['PASS']) and s2e['en_boy_fark'] > 0.005, s2e['en_boy_fark'])

    # --- kapi 2 grup bolumu: ATK.grup_kapisi (degistirilmeden) + mutasyonlar
    def gk(v):
        return KP.grup_kapisi(v, g, yan)
    gv = grup_verisi(ort, veri['ayar'])
    r0 = gk(gv)
    k('kapi 2 grup (bilinen PASS, yeniden kurulan grup verisiyle): PASS; grup merkezi = bagimsiz hesaplanan nokta', r0['PASS'] and r0['bagimsiz']['grup_merkez_disk_merkezi'], r0.get('bagimsiz'))

    def kopya(v):
        v2 = dict(v)
        v2['grup_oge'] = [dict(o) for o in v['grup_oge']]
        v2['sembol'] = dict(v['sembol'])
        return v2
    v = kopya(gv); v['sembol']['x'] += 3
    k('bilinen FAIL kapi 2 grup: ana sembol 3 px kaydirilmis -> FAIL', not gk(v)['PASS'])
    v = kopya(gv); v['grup_oge'][1]['x'] += 3
    k('bilinen FAIL kapi 2 grup: kucuk burc 3 px kaydirilmis -> FAIL', not gk(v)['PASS'])
    v = kopya(gv); v['grup_oge'][3]['x'] += 3
    k('bilinen FAIL kapi 2 grup / logo yalniz olcek: logo 3 px kaydirilmis -> FAIL', not gk(v)['PASS'])
    v = kopya(gv); m_ = v['grup_oge'][3]['A'].copy(); m_ = cv2.dilate(m_, np.ones((3, 3), np.uint8)); v['grup_oge'][3]['A'] = m_
    k('bilinen FAIL logo yalniz olcek: kalinlastirilmis (genisletilmis) logo maskesi -> FAIL (maske kaynagin kucultulmusu degil)', not gk(v)['PASS'])
    v = kopya(gv); v['ayar'] = dict(v['ayar'], logo='yok')
    k('bilinen FAIL kapi 2 grup: logolu gorsel + logosuz ayar -> FAIL', not gk(v)['PASS'])
    gv0 = grup_verisi(ort, sec0['ayar'])
    k('kapi 2 grup (bilinen PASS): logosuz grup + logosuz ayar -> PASS (3 oge)', gk(gv0)['PASS'])
    v = kopya(gv0); v['ayar'] = dict(v['ayar'], logo=1.0)
    k('bilinen FAIL kapi 2 grup: logosuz gorsel + logolu ayar -> FAIL', not gk(v)['PASS'])
    v = kopya(gv); v['ayar'] = dict(v['ayar'], logo=1.25)
    k('bilinen FAIL logo yalniz olcek: gorsel carpan 1,0, ayar 1,25 -> FAIL', not gk(v)['PASS'])
    asil_gm = TD.grup_merkezi
    TD.grup_merkezi = lambda u, a: (asil_gm(u, a)[0] + 3, asil_gm(u, a)[1])
    try:
        gvk = grup_verisi(ort, veri['ayar'])
    finally:
        TD.grup_merkezi = asil_gm
    rk = gk(gvk)
    k('bilinen FAIL kapi 2 (Serdar soru 6 "n"; inceleme bulgusu 7 / 9): URETIM grup merkezini 3 px kaydirirsa sert FAIL (beklenen nokta uretimden bagimsiz hesaplanir)',
      (not rk['PASS']) and not rk['bagimsiz']['grup_merkez_disk_merkezi'] and rk['uretim_merkez'] == [547, 582], rk.get('uretim_merkez'))
    k('kapi 2 grup / logo yalniz olcek (bilinen PASS): logo carpani 1,25 ile kurulan grup + ayni ayar -> PASS',
      gk(grup_verisi(ort, TD.ayar_dogrula(dict(taban='B1', logo=1.25, logo_yer='kucuk_arasi'))[0]))['PASS'])
    asil_ok = TD.olcek_kontrol
    TD.olcek_kontrol = lambda o_, a_: asil_ok(o_, a_) * 1.05
    try:
        gvb = grup_verisi(ort, veri['ayar'])
    finally:
        TD.olcek_kontrol = asil_ok
    rb = gk(gvb)
    k('bilinen FAIL kapi 2 boy (inceleme 1. tur bulgu 2): URETIM olcegi %5 buyutulurse ATK kosullari uretimi kendisiyle karsilastirir (atk_PASS), '
      'bagimsiz boy kosulu sert FAIL verir (olculen halka yaricapi - halka_r x Rg > 20 px)',
      (not rb['PASS']) and rb['atk_PASS'] and (not rb['boyut_bagimsiz']['PASS']) and rb['boyut_bagimsiz']['fark'] > 20, rb['boyut_bagimsiz'])
    ay_r = TD.ayar_dogrula(dict(taban='B1', grup_r=0.9))[0]
    rr = gk(grup_verisi(ort, ay_r))
    k('kapi 2 boy, grup_r modu (bilinen PASS): en uzak piksel = grup_r x Rg (hedef AYARDAN hesaplanir), fark <= 2 px',
      rr['PASS'] and rr['boyut_bagimsiz']['mod'] == 'grup_r' and abs(rr['boyut_bagimsiz']['beklenen_px'] - 0.9 * 543.5) < 1e-3, rr['boyut_bagimsiz'])
    AT.grup_kur = lambda mt_, c_, g_, y_, hedef_, *a_: asil_gk(mt_, c_, g_, y_, hedef_ * 1.05, *a_)
    try:
        gvr = grup_verisi(ort, ay_r)
    finally:
        AT.grup_kur = asil_gk
    rr2 = gk(gvr)
    k('bilinen FAIL kapi 2 boy, grup_r modu: URETIM hedefi %5 buyutulurse sert FAIL (boy kosulu FAIL; kapi hedefi uretimden almaz)',
      (not rr2['PASS']) and not rr2['boyut_bagimsiz']['PASS'], rr2['boyut_bagimsiz'])
    TD.grup_merkezi = lambda u, a: (asil_gm(u, a)[0] + 3, asil_gm(u, a)[1])
    try:
        rk3 = TD.secenek_uret(ort, sec1, td / 'kay3')
    finally:
        TD.grup_merkezi = asil_gm
    k('bilinen FAIL SERT kapi 2, URETIM ICINDE tam yol (inceleme 1. tur bulgu 3): grup merkezi 3 px kaymis uretim -> secenek DUR kapi_sert (2_grup), '
      'son gorsel SILINDI, onizleme / isaret yok, OLCUM kaydi var, sha yok',
      rk3['durum'] == 'DUR' and rk3['kod'] == 'kapi_sert' and '2_grup' in rk3['neden'] and rk3['png_sha256'] is None
      and not (td / 'kay3' / 'SEC_01_tekil.png').exists() and not (td / 'kay3' / 'SEC_01_tekil_onizleme.jpg').exists()
      and not (td / 'kay3' / 'SEC_01_tekil_isaret.jpg').exists() and (td / 'kay3' / 'SEC_01_tekil_OLCUM.json').is_file()
      and TD.dur_kodu(rk3) == 'kapi_sert: 2_grup', (rk3['durum'], rk3['kod'], rk3['neden']))
    # kalin halka: YALNIZ ay takvimi kapisiyla karsilastirma (arac girdisi olarak kapali; inceleme bulgusu 10)
    Yk = TD.grup_yerlestir(ort, veri['ayar'])
    Gk = AT.grup_kur(ort.mt, TD.CIFT, ort.g, ort.yan_json, Yk['hedef_r'], 'halka', 'poster', 0.37, 1.0, 2.0, 'ozgun', 1.0)
    for o in Gk['ogeler']:
        o['x'], o['y'] = Yk['merkez'][0] + o['x'], Yk['merkez'][1] + o['y']
    vk = dict(gv, grup_oge=Gk['ogeler'], ayar=dict(veri['ayar'], halka_kalinlik=2.0))
    k('esdegerlik grup kapisi (yalniz ATK ile karsilastirma; arac girdisi degil): kalin halka gorseli + ayni carpan -> PASS; carpan 1,0 ayariyla -> FAIL',
      gk(vk)['atk_PASS'] and not gk(dict(vk, ayar=veri['ayar']))['atk_PASS'])

    # --- olcer kapilar: tek cagrida bagimsiz bozulmalar (her kapinin kendi anahtari)
    y0i, x0i = veri['ogeler'][1]['y'], veri['ogeler'][1]['x']
    hm, wm = veri['ogeler'][1]['A'].shape
    img3 = img.copy()
    img3[y0i:y0i + hm, x0i:x0i + wm] = np.clip(veri['altinsiz'][y0i:y0i + hm, x0i:x0i + wm].astype(np.int16) + 4, 0, 255).astype(np.uint8)   # metin zemin rengine boyandi
    png3 = td / 'bozuk.png'
    png_yaz(img3, png3)
    vb = dict(veri, png=png3, ayar=dict(veri['ayar'], logo='yok'))
    vb['ogeler'] = [dict(o) for o in veri['ogeler']]
    vb['ogeler'][0]['atest'] = np.roll(veri['ogeler'][0]['atest'], 3, axis=1)
    vb['ogeler'][0]['y'] = S['y'] + 60                                        # isim satiri grubun icine tasindi (maske yeri)
    vb['ogeler'][1]['taban_y'] = veri['ogeler'][1]['taban_y'] - 30
    ym = veri['yildiz_maske'].copy()
    k1 = veri['grup_oge'][1]
    iy, ix = np.nonzero(k1['A'] > 0.5)                                        # kucuk burcun ust murekkep pikselinin 5 px ustu (kapi payi 12 px icinde)
    ym[k1['y'] + iy[0] - 6:k1['y'] + iy[0] - 4, k1['x'] + ix[0]:k1['x'] + ix[0] + 2] = 255
    vb['yildiz_maske'] = ym
    vb['isim'] = dict(veri['isim'], sinir=10.0)
    ob = asil['olc'](vb)['kapi']['olcer']
    for q, ack in (('tek_doku', 'metin zemin rengine boyanmis -> dE00 > 2'), ('kontrast', 'metin zemin rengine boyanmis -> kontrast < 4,5'),
                   ('duz_renk', 'metin duz renk -> yayilim < 40'), ('yazim', 'isim motor alfasi 3 px kaymis -> alfa farki > 0,035'),
                   ('yildiz', 'kucuk burcun 5 px yaninda yildiz -> binme > 0'), ('oge_sayisi', 'ayar logosuz, cizilen logolu -> liste farkli'),
                   ('grup_yazi', 'isim satiri grubun icinde -> bosluk < 12 px'), ('metin_taban', 'metin tabani 30 px kaymis'),
                   ('isim', 'isim satiri sinirdan genis')):
        k(f'[bozulmus gercek veri] bilinen FAIL olcer {q}: {ack} -> FAIL (ayni kapi gercek veride PASS' + (')' if q != 'isim' else ' degil: alt sinir; burada genislik kosulu)'),
          not ob[q]['PASS'], {a_: b_ for a_, b_ in ob[q].items() if not isinstance(b_, (dict, list))})
    k('[bozulmus gercek veri] isim genisligi > sinir (genislik kosulu gercekten olculdu)', ob['isim']['genislik'] > ob['isim']['sinir'])
    # cikti kapisi SERT (Serdar 12 Kas K4; dilim 1'de olcerdi: bu testler o yuzden degisti). Sert FAIL listesi YALNIZ 'cikti', kapi 2 sembol PASS.
    def cikti_sert(o_):
        return bool((not o_['kapi']['sert']['cikti']['PASS']) and o_['ozet']['sert_fail'] == ['cikti'] and o_['ozet']['durum'] == 'DUR'
                    and o_['ozet']['cikti'] == 'FAIL' and o_['kapi']['sert']['2_sembol']['PASS'] and o_['kapi']['sert']['2_grup']['PASS']
                    and o_['ozet']['kok_neden'] is None)
    png4 = td / 'profilsiz_gercek.png'
    png_yaz(img, png4, icc=False)
    k('[bozulmus gercek veri] K4 bilinen FAIL: profilsiz son gorsel -> sert FAIL listesi yalniz cikti, durum DUR (kapi 2 PASS)', cikti_sert(asil['olc'](dict(veri, png=png4))))
    png5 = td / 'dpi300_gercek.png'
    png_yaz(img, png5, dpi=300.0)
    o5_ = asil['olc'](dict(veri, png=png5, urun=dict(U, alt_sinir=dict(yazi_mm=0.95, cizgi_mm=0.2))))
    k('[bozulmus gercek veri] K4 bilinen FAIL: yanlis dpi etiketli dosya -> sert FAIL listesi yalniz cikti, durum DUR', cikti_sert(o5_))
    png6 = td / 'rgba_gercek.png'
    png_yaz(img, png6, mod='RGBA')
    k('[bozulmus gercek veri] K4 bilinen FAIL: RGBA dosya -> sert FAIL listesi yalniz cikti, durum DUR', cikti_sert(asil['olc'](dict(veri, png=png6))))
    png7 = td / 'boyut_gercek.png'
    png_yaz(img[:, :1000], png7)
    k('[bozulmus gercek veri] K4 bilinen FAIL: sembolu kesmeyen yanlis boyut (1000 x 1087) -> sert FAIL listesi yalniz cikti, durum DUR', cikti_sert(asil['olc'](dict(veri, png=png7))))
    o_iyi = asil['olc'](dict(veri, png=cB / 'SEC_01_tekil.png'))
    k('[gercek veri] K4 bilinen PASS: degismemis son gorsel -> cikti PASS, sert FAIL bos, durum tamam', o_iyi['kapi']['sert']['cikti']['PASS'] and o_iyi['ozet']['sert_fail'] == []
      and o_iyi['ozet']['durum'] == 'tamam')

    def w_olc_boyut(v):                                                       # uretim icinde: KAYDEDILEN dosya 1000 x 1087'ye kirpilir, sonra GERCEK olc
        im_ = Image.open(v['png']); im_.load()
        im_.crop((0, 0, 1000, 1087)).save(v['png'], dpi=im_.info['dpi'], icc_profile=im_.info.get('icc_profile'))
        return asil['olc'](v)
    KP.olc = w_olc_boyut
    try:
        rb5 = TD.secenek_uret(ort, sec0, td / 'boyut')
    finally:
        KP.olc = asil['olc']
    ob5 = json.loads((td / 'boyut' / 'SEC_01_tekil_OLCUM.json').read_text(encoding='utf-8'))
    k('K4, URETIM ICINDE tam yol: yanlis boyutlu (1000 x 1087) kaydedilmis dosya -> cokme yok, secenek DUR kapi_sert (cikti), son gorsel SILINDI, onizleme yok, '
      'OLCUM kaydinda sert FAIL yalniz cikti; hucre kodu "kapi_sert: cikti"',
      rb5['durum'] == 'DUR' and rb5['kod'] == 'kapi_sert' and rb5['png_sha256'] is None and not (td / 'boyut' / 'SEC_01_tekil.png').exists()
      and not (td / 'boyut' / 'SEC_01_tekil_onizleme.jpg').exists() and ob5['ozet']['sert_fail'] == ['cikti'] and ob5['kapi']['sert']['cikti']['tuval_boyut_farki']
      and TD.dur_kodu(rb5) == 'kapi_sert: cikti' and 'DUR kapi_sert: cikti' in TD.etiket_satirlari(rb5), (rb5['durum'], rb5['kod'], rb5['neden']))
    o6_ = asil['olc'](dict(veri, urun=dict(U, alt_sinir=dict(yazi_mm=0.93, cizgi_mm=0.2))))
    k('mm uyarisi esigin iki yaninda [varsayim girdisi; yalniz formul]: isim 0,942 mm, sinir 0,95 iken isaretli, 0,93 iken isaretsiz',
      o5_['oge']['isimler']['yazi_sinir_alti'] and not o6_['oge']['isimler']['yazi_sinir_alti'] and o6_['oge']['metin_1']['yazi_sinir_alti'])
    o7_ = asil['olc'](dict(veri, urun={k_: v_ for k_, v_ in U.items() if k_ != 'alt_sinir'}))
    k('alt sinir tanimsiz urun: uyari uretilmez, OLCUM "sinir tanimsiz" yazar, gercek olcu PASS', o7_['kapi']['olcer']['gercek_olcu']['PASS']
      and o7_['kapi']['olcer']['gercek_olcu']['not_'] == 'sinir tanimsiz' and o7_['kapi']['olcer']['isim']['alt_sinir_px'] is None)

    u_as = {k_: v_ for k_, v_ in U.items() if k_ != 'alt_sinir'}
    o9_ = asil['olc'](dict(veri, urun=u_as, isim=dict(veri['isim'], guvenli_disinda=True)))
    k('[bozulmus gercek veri] K3 isim olceri: alt sinir tanimsizken isim olceri PASS (bilinen PASS, ustteki olcum); ayni veride "guvenli alanin disinda" isaretliyse FAIL '
      '(FAIL nedeni alt sinir degil, K3 kosulu) ve OLCUM ozetinde not var; sert FAIL yok',
      o7_['kapi']['olcer']['isim']['PASS'] and (not o9_['kapi']['olcer']['isim']['PASS']) and o9_['kapi']['olcer']['isim']['guvenli_disinda']
      and o9_['ozet']['isim_guvenli_disinda'] and 'isim' in o9_['ozet']['olcer_fail'] and o9_['ozet']['sert_fail'] == [])

    # --- tek oge degisir: birlestirme ONCESI katmanda (plan 4.2; gorev B4)
    def ayar(**f):
        return TD.ayar_dogrula(dict(taban='B1', **f))[0]

    def ana_halka(Y):
        h = Y['grup_oge'][0]
        return (Y['sembol']['rgb'], Y['sembol']['a'], Y['sembol']['x'], Y['sembol']['y'], h['A'], h['x'], h['y'], h['k'], h['kaynak'])

    def ayni(a, b):
        return all((np.array_equal(p, q) if isinstance(p, np.ndarray) else p == q) for p, q in zip(a, b))
    Y1 = TD.grup_yerlestir(ort, ayar())
    k('tek oge degisir (bilinen PASS; halka_r + halka merkez): kucuk_v 0,47 ya da kucuk_oran 1,2 ile ana sembolun (rgb, alfa, yer) ve halkanin (maske, yer, k, kaynak) '
      'dizileri bayt bayt ayni', ayni(ana_halka(Y1), ana_halka(TD.grup_yerlestir(ort, ayar(kucuk_v=0.47))))
      and ayni(ana_halka(Y1), ana_halka(TD.grup_yerlestir(ort, ayar(kucuk_oran=1.2)))))
    k('bilinen FAIL tek oge degisir: grup_r modunda, kucuk burclar halkanin disindayken (kucuk_v 0,95) kucuk_oran 1,8 ana sembolu yeniden boyutlar (bag yakalaniyor)',
      not ayni(ana_halka(TD.grup_yerlestir(ort, ayar(grup_r=0.9, kucuk_v=0.95))), ana_halka(TD.grup_yerlestir(ort, ayar(grup_r=0.9, kucuk_v=0.95, kucuk_oran=1.8)))))
    k('bilinen FAIL tek oge degisir: grup merkezde (halka_r), kucuk_v 0,95 iken kucuk_oran 1,8 ana sembolu kaydirir',
      not ayni(ana_halka(TD.grup_yerlestir(ort, ayar(grup_merkez='grup', kucuk_v=0.95))),
               ana_halka(TD.grup_yerlestir(ort, ayar(grup_merkez='grup', kucuk_v=0.95, kucuk_oran=1.8)))))
    k('olgu: B1 yerinde (kucuk_v 0,37; halkanin icinde) kucuk burc ayari grup_r modunda da cevre yaricapini degistirmez (cevreyi halka belirler)',
      ayni(ana_halka(TD.grup_yerlestir(ort, ayar(grup_r=0.9))), ana_halka(TD.grup_yerlestir(ort, ayar(grup_r=0.9, kucuk_oran=1.8)))))
    hx, hy, hr_ = ATK.cember_uydur(Y1['grup_oge'][0]['A'])
    k('halka_r iki gecis (1087): olculen halka yaricapi = halka_r x Rg = 480,45 px (pay 1 px)', abs(hr_ - 0.884 * 543.5) <= 1.0, hr_)
    # sinir: isim boyu degisince sonraki ogenin GRENI degisir, maskesi ve yeri degismez (AT:854 tek uretec)
    Lana = np.median(AT.labf(S['rgb'][S['a'] >= 0.9]), 0)

    def isim_kucuk(cap):
        A, taban = AT.metin_alfa('EMILY & JAMES', ort.mt.font_isim, cap, 500)
        oi = dict(ad='isimler', tur='isim', metin='EMILY & JAMES', font=ort.mt.font_isim, wght=500, ref='H', cap=float(cap), A=A, taban=taban, x=0, y=0,
                  k=AT.cizim_katsayisi(cap))
        ok1 = dict(Y1['grup_oge'][1])
        return AT.altin_ogeler(ort.mt, [oi, ok1], ort.hr['har'], ort.hr['qa_goz'], Lana, veri['D_ana'])[1]
    b1, b2 = isim_kucuk(40.3), isim_kucuk(46.4)
    k('tek oge degisir SINIRI: isim boyu degisince kucuk burcun motor katmani (gren) degisir; maskesi ayni kalir',
      np.array_equal(b1['m'], b2['m']) and not np.array_equal(b1['rgb'], b2['rgb']))
    k('ayni girdiyle motor katmani bayt bayt ayni (belirlenimcilik)', np.array_equal(b1['rgb'], isim_kucuk(40.3)['rgb']))

    # --- K2 etiketi (Serdar 12 Kas): tuvalden tasan grup ogesi DUR vermeye DEVAM eder; kapi sonucu / kodu ayni; kok neden etikette ve OZET kaydinda
    kt = {}

    def w_olc_tasan(v):
        shutil.copyfile(v['png'], td / 'tasan_kopya.png')
        kt['veri'] = v
        return asil['olc'](v)
    sec_t = TD.istek_kur(dict(taban='B1', tekil=[dict(halka_r=1.0166)]))[0]
    KP.olc = w_olc_tasan
    try:
        rt = TD.secenek_uret(ort, sec_t, td / 'tasan')
    finally:
        KP.olc = asil['olc']
    ozt = rt.get('olcum_ozet') or {}
    kn = ozt.get('kok_neden')
    k('GERCEK K2: halka tuvalden tasiyor (halka_r 1,0166) -> secenek DUR kapi_sert, sert FAIL yalniz 2_grup (AYNEN), gorsel yok; kok neden OZET kaydinda ve hucre '
      'etiketinde: "grup ogesi tuvalden tasiyor: halka; konum farki <kapi degeri> px"; boy kosulu farki yine yazili',
      rt['durum'] == 'DUR' and rt['kod'] == 'kapi_sert' and ozt.get('sert_fail') == ['2_grup'] and not (td / 'tasan' / 'SEC_01_tekil.png').exists()
      and kn == f"grup ogesi tuvalden tasiyor: halka; konum farki {ozt.get('kapi2_konum_fark')} px" and ozt.get('kapi2_konum_fark') > 1.0
      and kn in TD.etiket_satirlari(rt) and TD.dur_kodu(rt) == 'kapi_sert: 2_grup' and ozt.get('kapi2_boyut_fark') is not None and ozt['kapi2_boyut_fark'] <= 2.0, (rt['kod'], kn))
    vt = kt.get('veri')
    if vt is None:
        k('K2 kosu verisi alindi', False)
        return
    ot1 = asil['olc'](dict(vt, png=td / 'tasan_kopya.png'))
    k('K2 kontrol: ayni kosu verisiyle olcum yeniden -> ayni kok neden (asagidaki bozulmalarin karsilastirma tabani)', ot1['ozet']['kok_neden'] == kn and ot1['ozet']['sert_fail'] == ['2_grup'])
    png_t = td / 'tasan_profilsiz.png'
    png_yaz(np.asarray(Image.open(td / 'tasan_kopya.png').convert('RGB')), png_t, icc=False)
    ot2 = asil['olc'](dict(vt, png=png_t))
    k('[bozulmus gercek veri] bilinen FAIL yonu K2 etiketi: baska sert FAIL de varken (2_grup + cikti) kok neden YAZILMAZ',
      sorted(ot2['ozet']['sert_fail']) == ['2_grup', 'cikti'] and ot2['ozet']['kok_neden'] is None, ot2['ozet']['sert_fail'])
    vt2 = dict(vt, png=td / 'tasan_kopya.png')
    vt2['grup_oge'] = [dict(o) for o in vt['grup_oge']]
    vt2['grup_oge'][1]['x'] += 2                                              # kucuk1: KIRPILMAMIS oge, 2 px kaymis -> yeniden kurulumda o da duser
    ot3 = asil['olc'](vt2)
    k('[bozulmus gercek veri] bilinen FAIL yonu K2 etiketi: kirpilmamis bir oge (kucuk1) de dusmusken kok neden YAZILMAZ (sert FAIL yine yalniz 2_grup)',
      ot3['ozet']['sert_fail'] == ['2_grup'] and ot3['ozet']['kok_neden'] is None and not ot3['kapi']['sert']['2_grup']['oge']['kucuk1']['yer_ayni']
      and 'kucuk1' not in vt['tuval_kirpilan'] and vt['tuval_kirpilan'] == ['halka'], (ot3['ozet']['sert_fail'], ot3['ozet']['kok_neden']))
    k('bilinen FAIL yonu K2 etiketi (GERCEK uretim): kirpilma yokken dusen 2_grup (merkezi 3 px kaymis uretim) kok neden YAZMAZ',
      rk3['olcum_ozet']['sert_fail'] == ['2_grup'] and rk3['olcum_ozet']['kok_neden'] is None and not any('tuvalden tasiyor' in e_ for e_ in TD.etiket_satirlari(rk3)))

    # --- kucuk burc izgarasi: "tek oge degisir" GERCEK uretim verisiyle (kapi olcumunden once kesilir) + taban hucresi = taban
    gk_ = TD.istek_kur(dict(taban='B1', izgara=dict(kucuk_oran_carpan=[0.8, 1.0, 1.2], kucuk_v_fark=[-0.08, 0, 0.08, 0.16, 0.24, 0.32])))

    def veri_al(sec_, ad_):
        kv = {}

        def w_(v):
            kv['veri'] = v
            kv['sha'] = TD.sha_dosya(v['png'])
            raise Kes()
        KP.olc = w_
        try:
            try:
                TD.secenek_uret(ort, sec_, td / ad_)
            except Kes:
                pass
        finally:
            KP.olc = asil['olc']
        return kv
    kb, kh = veri_al(gk_[7], 'kb'), veri_al(gk_[17], 'kh')                   # taban hucresi (x1,0; fark 0) ve kose hucresi (x1,2; +0,32)

    def oge3(v, ad_):
        o = next(o for o in v['ogeler'] + v['grup_oge'] if o['ad'] == ad_)
        return o['A'], o['x'], o['y']

    def motor3(v, ad_):                                                       # k kat cizim katsayisi ve motor katmaninin alfasi (inceleme 1b bulgu 3)
        o = next(o for o in v['ogeler'] + v['grup_oge'] if o['ad'] == ad_)
        return o['atest'], int(o['k']), 0

    def smb(v):
        return v['sembol']['a'], v['sembol']['x'], v['sembol']['y']

    def ayni3(p_, q_):
        return bool(p_[0].shape == q_[0].shape and np.array_equal(p_[0], q_[0]) and p_[1:] == q_[1:])
    if 'veri' not in kb or 'veri' not in kh:
        k('kucuk burc izgarasi kosu verisi alindi', False)
        return
    vb_, vh_ = kb['veri'], kh['veri']
    k('tek oge degisir, kucuk burc izgarasi (GERCEK uretim verisi; kucuk_oran x1,2 + kucuk_v 0,69): sembol (maske, renk, yer), halka, isimler ve metin_1 maskeleri, '
      'yerleri, k katsayilari ve motor katmani alfalari AYNI (halka_r degisen kosuda halkaninki farkli: karsilastirma FAIL verebiliyor); kucuk1 ve kucuk2 maskeleri DEGISIR',
      gk_[17]['ayar']['kucuk_oran'] == 1.2 and gk_[17]['ayar']['kucuk_v'] == 0.69 and ayni3(smb(vb_), smb(vh_)) and np.array_equal(vb_['sembol']['rgb'], vh_['sembol']['rgb'])
      and all(ayni3(oge3(vb_, a_), oge3(vh_, a_)) and ayni3(motor3(vb_, a_), motor3(vh_, a_)) for a_ in ('halka', 'isimler', 'metin_1'))
      and not ayni3(motor3(vb_, 'halka'), motor3(vt, 'halka'))
      and not ayni3(oge3(vb_, 'kucuk1'), oge3(vh_, 'kucuk1')) and not ayni3(oge3(vb_, 'kucuk2'), oge3(vh_, 'kucuk2')))
    k('bilinen FAIL yonu tek oge degisir: halka_r degisen secenekte (K2 kosu verisi) halka ve sembol AYNI DEGIL (karsilastirma FAIL verebiliyor)',
      not ayni3(oge3(vb_, 'halka'), oge3(vt, 'halka')) and not ayni3(smb(vb_), smb(vt)))
    k('kucuk burc izgarasinin taban hucresi = taban (GERCEK): taban hucresinin PNG sha256 = tekil B1 kosusunun sha256; kose hucresinin sha256 farkli',
      kb['sha'] == rC['png_sha256'] and kh['sha'] != kb['sha'], (kb.get('sha'), rC['png_sha256']))

    # --- pafta 3 MB sinirini asarsa OZET / SURE / OLCUM_TUMU yine yazilir (Serdar 12 Kas; sinir test icinde 2000 bayta cekilir)
    istek0 = td / 'istek0.json'
    istek0.write_text(json.dumps(dict(taban='B1', tekil=[{}])))
    cP = td / 'P3'
    eski_p = TD.PAFTA_AZAMI_BAYT
    TD.PAFTA_AZAMI_BAYT = 2000
    try:
        rcP = TD.main(['kos', '--kaynak', KS, '--urun', str(URUN_DOSYA), '--istek', str(istek0), '--katman', str(katman), '--cikti', str(cP), '--olcum'])
    finally:
        TD.PAFTA_AZAMI_BAYT = eski_p
    ozP = json.loads((cP / 'OZET.json').read_text(encoding='utf-8')) if (cP / 'OZET.json').is_file() else {}
    k('bilinen FAIL pafta boyutu (komut): pafta sinirin ustunde -> pafta dosyasi YOK, OZET / SURE / OLCUM_TUMU YINE yazildi, OZET pafta kaydi DUR pafta_boyut, cikis 1; '
      'ayni kosu sinir 3 MB iken (kosu A) pafta yazar, cikis 0',
      rcP == 1 and all((cP / f_).is_file() for f_ in ('OZET.json', 'SURE.json', 'OLCUM_TUMU.json')) and not list(cP.glob('PAFTA_*.jpg'))
      and ozP.get('pafta', {}).get('dosya') is None and ozP.get('pafta', {}).get('kod') == 'pafta_boyut' and ozP['secenek'][0]['durum'] == 'tamam'
      and ozP['secenek'][0]['png_sha256'] == rC['png_sha256'] and oz['pafta']['dosya'] is not None, (rcP, ozP.get('pafta')))

    # --- 5400 girdisi (test ici sozluk; gorsel uretimi yok): iki gecis ve ust uclar
    ortD = copy.copy(ort)
    ortD.urun = TD.urun_dogrula(copy.deepcopy(DIKEY))
    ortD.cevre = {}
    Gd, _, hed = TD.grup_hesapla(ortD, ayar(halka_r=0.60, kucuk_oran=1.8))
    k('halka_r iki gecis (5400 girdisi, Rg 2520): halka_r 0,60 + kucuk_oran 1,8 (son olcek x 1,8 = 0,96) DUR vermez; olcek = 0,60 x 2520 / cember R',
      abs(Gd['bilgi']['olcek'] - 0.60 * 2520 / Gd['bilgi']['cember']['R']) < 1e-6 and Gd['bilgi']['olcek'] * 1.8 <= 1.0, Gd['bilgi']['olcek'])
    eski = TD.ILK_GECIS_HEDEF
    TD.ILK_GECIS_HEDEF = 2520.0
    ortD.cevre = {}
    try:
        k('bilinen FAIL iki gecis: ilk gecisi Rg hedefiyle yapan bozuk kopya ayni ayarda DUR verir (duzeltilen hatanin kaniti)',
          dur_mu(lambda: TD.grup_hesapla(ortD, ayar(halka_r=0.60, kucuk_oran=1.8)), 'grup_olcek'))
    finally:
        TD.ILK_GECIS_HEDEF = eski
        ortD.cevre = {}
    k('bilinen FAIL ust uc (5400 girdisi): halka_r 1,15 -> olcek > 1, girdi hatasi (aralik 0,30 - 1,20 bu tuvalde 1,125 ustunde DUR)',
      dur_mu(lambda: TD.olcek_kontrol(ortD, ayar(halka_r=1.15)), 'girdi_olcek', True) and TD.olcek_kontrol(ortD, ayar(halka_r=1.12)) > 0)
    k('bilinen FAIL ust uc (5400 girdisi): halka_r 0,884 + kucuk_oran 1,8 -> girdi hatasi (0,7855 x 1,8 = 1,41 > 1)',
      dur_mu(lambda: TD.olcek_kontrol(ortD, ayar(kucuk_oran=1.8)), 'girdi_olcek', True))
    k('bilinen FAIL logo yalniz olcek (5400 girdisi): halka_r 0,60 + logo 2,0 -> toplam olcek 1,07 > 1, girdi hatasi (buyutme yok)',
      dur_mu(lambda: TD.olcek_kontrol(ortD, ayar(halka_r=0.60, logo=2.0, logo_yer='kucuk_arasi')), 'girdi_olcek', True))
    k('on kontrol: ust ucu asan secenek varsa kosu baslamaz (girdi hatasi, secenek numarasiyla)',
      dur_mu(lambda: TD.on_kontrol(ortD, [dict(no=1, ayar=ayar()), dict(no=2, ayar=ayar(halka_r=1.15))]), 'girdi_olcek', True))
    k('bilinen FAIL: dikey urunle gorsel uretimi yok (dilim 1) -> secenek DUR girdi_sekil, dosya yok',
      TD.secenek_uret(ortD, sec0, td / 'dikey')['kod'] == 'girdi_sekil' and not (td / 'dikey' / 'SEC_01_tekil.png').exists())

    # --- sert DUR'lar (uretim icinde): gorsel yok, secenek gizlenmez
    def sdur(fark, cikti):
        s = TD.istek_kur(dict(taban='B1', tekil=[fark]))[0]
        r = TD.secenek_uret(ort, s, td / cikti)
        return r, (td / cikti / f"{s['ad']}.png").exists(), (td / cikti / f"{s['ad']}_OLCUM.json").is_file()
    r, var, olcum_var = sdur(dict(metin_cap=0.03, satirlar=['I'], metin_tur='mesaj'), 'd200')
    k('bilinen FAIL SERT (Serdar soru 6 "m"): renk uyumu icin < 200 cekirdek pikselli oge -> secenek DUR renk_uyum_piksel, gorsel YOK, OLCUM kaydi var',
      r['durum'] == 'DUR' and r['kod'] == 'renk_uyum_piksel' and not var and olcum_var, (r['durum'], r['kod'], r['neden']))
    r, var, _ = sdur(dict(grup_y=0.9), 'dtasma')
    k('bilinen FAIL SERT: ana sembol tuval disina tasiyor -> DUR tasma, gorsel yok', r['kod'] == 'tasma' and not var, (r['kod'], r['neden']))
    # K3 (Serdar 12 Kas "evet"; onayli tek gevsetme): isim buyuk harf bandi guvenli dairenin disinda (kiris 0) -> DUR YOK (dilim 1'de DUR isim_sigmadi idi)
    r, var, _ = sdur(dict(isim_y=0.995), 'disim')
    omk = json.loads((td / 'disim' / 'SEC_01_tekil_OLCUM.json').read_text(encoding='utf-8')) if var else {}
    k('GERCEK K3: isim guvenli dairenin disinda (isim_y 0,995; kiris 0) -> DUR YOK, gorsel VAR; isim kuculmedi (oran 1,0), sinir = tuval genisligi 1087; '
      'isimler ogesinin tasmasi olculdu (isik payi 0 > 0); isim olceri FAIL; etikette "isim guvenli alan disinda"',
      r['durum'] == 'tamam' and var and omk['ozet']['isim_guvenli_disinda'] and omk['ozet']['isim_kuculme'] == 1.0 and omk['kapi']['olcer']['isim']['sinir'] == 1087.0
      and omk['kapi']['olcer']['tasma']['oge']['isimler']['isik_0'] > 0 and (not omk['kapi']['olcer']['isim']['PASS']) and omk['ozet']['sert_fail'] == []
      and 'isim guvenli alan disinda' in TD.etiket_satirlari(r), (r['durum'], r['kod'], r['neden']))
    k('K3 bilinen FAIL yonu: isim guvenli alanin icindeyken (kosu A) not yok, isimler tasmasi 0, sinir = kiris (< tuval genisligi)',
      (not om['ozet']['isim_guvenli_disinda']) and ol['tasma']['oge']['isimler']['isik_0'] == 0 and ol['isim']['sinir'] < 1087.0
      and 'isim guvenli alan disinda' not in TD.etiket_satirlari(sA))
    r, var, _ = sdur(dict(isim_y=0.994475), 'd8')
    k('K3 DEGISMEYEN (GERCEK uretim): kiris 0\'dan buyuk ama cok kucukken (3,5 px) isim 8 denemede sigmaz -> DUR isim_sigmadi, gorsel yok',
      r['kod'] == 'isim_sigmadi' and '8 denemede' in r['neden'] and not var, (r['kod'], r['neden']))
    k('K3 DEGISMEYEN (gercek fonksiyon): AT.isim_sigdir sinir 1,5 px ile 8 denemede sigmaz -> DUR isim_sigmadi; genis sinirla (bilinen PASS) doner',
      dur_mu(lambda: AT.isim_sigdir('EMILY & JAMES', ort.mt.font_isim, sinir=1.5, cap0=40.0, cap_alt=0.0, yumusak=True), 'isim_sigmadi')
      and AT.isim_sigdir('EMILY & JAMES', ort.mt.font_isim, sinir=1087.0, cap0=40.0, cap_alt=0.0, yumusak=True)[2] == 40.0)
    asil_kiris = TD.kiris
    TD.kiris = lambda u_, y0_, y1_: 0.5 if abs(y1_ - (543.5 + 0.65 * 543.5)) < 1e-6 else asil_kiris(u_, y0_, y1_)   # yalniz isim satirinin kirisi 0,5 px
    try:
        r, var, _ = sdur({}, 'dkiris')
    finally:
        TD.kiris = asil_kiris
    k('[sahte veri] K3 DEGISMEYEN (inceleme 1b bulgu 1): kiris 0\'dan buyuk ama 1 px altinda (0,5; kiris fonksiyonu test icinde degistirildi) -> DUR isim_sigmadi '
      'AYNEN (K3 yalniz kiris tam 0 iken gecerli), gorsel yok', r['durum'] == 'DUR' and r['kod'] == 'isim_sigmadi' and '1 px altinda' in r['neden'] and not var,
      (r['durum'], r['kod'], r['neden']))
    r, var, _ = sdur(dict(halka_r=1.2, kucuk_v=1.3), 'dkucuk')
    k('K3 DEGISMEYEN (GERCEK uretim): bir oge (kucuk1) tumuyle tuval disinda -> DUR tasma, gorsel yok', r['kod'] == 'tasma' and 'tumuyle tuval disinda' in r['neden'] and not var,
      (r['kod'], r['neden']))
    asil_is = AT.isim_sigdir

    def kayik_isim(*a_, **kw_):                                               # [sahte veri] murekkebi tabanin USTUNDE, altinda 200 bos satir olan isim maskesi
        A_, t_, c_, d_ = asil_is(*a_, **kw_)
        A2 = np.zeros((int(np.ceil(t_)) + 200, A_.shape[1]), np.float32)
        h_ = min(A_.shape[0], int(t_))
        A2[:h_] = A_[:h_]
        return A2, t_, c_, d_
    AT.isim_sigdir = kayik_isim
    try:
        r, var, _ = sdur(dict(isim_y=-1.0), 'dbos')
    finally:
        AT.isim_sigdir = asil_is
    k('[sahte veri] K3: isim maskesi tuvalde BOS kalirsa (cerceve tuvalle kesisiyor, murekkep tumuyle disarida) kosu cokmez -> DUR isim_sigmadi, gorsel yok',
      r['durum'] == 'DUR' and r['kod'] == 'isim_sigmadi' and 'tuval disinda' in r['neden'] and not var, (r['kod'], r['neden']))
    r, var, _ = sdur(dict(isim_y=-1.0), 'dust')
    k('K3 (GERCEK; bilinen PASS yonu): ayni yerde (isim_y -1,0) gercek isim maskesinin murekkebi kismen tuvalde -> DUR yok, gorsel VAR', r['durum'] == 'tamam' and var,
      (r['durum'], r['kod'], r['neden']))
    r, var, _ = sdur(dict(metin_y=1.0), 'mtasma')
    omt = json.loads((td / 'mtasma' / 'SEC_01_tekil_OLCUM.json').read_text(encoding='utf-8'))['kapi']['olcer'] if var else {}
    k('GERCEK bilinen FAIL (olcer; gorsel VAR; inceleme 1. tur bulgu 4): metin satiri tuvalin alt kenarinda (metin_y 1,0) -> uretimin kiris hesabi metin_genis FAIL, '
      'tuval_tasma FAIL, tasma FAIL (isik 0 > 0, goruntu farki > 0, tuval disi > 0); ayni kapilar gercek kosu A\'da PASS; secenek tamam',
      r['durum'] == 'tamam' and var and (not omt['metin_genis']['PASS']) and (not omt['tuval_tasma']['PASS']) and (not omt['tasma']['PASS'])
      and omt['tasma']['toplam']['isik_0'] > 0 and omt['tasma']['toplam']['goruntu_farki'] > 0 and omt['tasma']['toplam']['tuval_disi'] > 0
      and omt['tasma']['oge']['metin_1']['isik_0'] > 0 and ol['metin_genis']['PASS'] and ol['tuval_tasma']['PASS'] and ol['tasma']['PASS'],
      (r['durum'], r['kod'], omt.get('tasma', {}).get('toplam')))
    r, var, _ = sdur(dict(isim1='MAXIMILIANO', isim2='CAGLAYANGUL', isim_y=0.9), 'uzun')
    omu = json.loads((td / 'uzun' / 'SEC_01_tekil_OLCUM.json').read_text(encoding='utf-8')) if var else {}
    k('GERCEK cok uzun isim + dar kiris (Serdar soru 6 "g": sinir guvenli alan kirisi; DUR degil, olcer): isim kirise sigacak kadar kuculur (oran < 0,6), '
      'genislik <= kiris, isim olceri FAIL (alt sinirin altinda), secenek tamam',
      r['durum'] == 'tamam' and var and omu['ozet']['isim_kuculme'] < 0.6 and omu['kapi']['olcer']['isim']['genislik'] <= omu['kapi']['olcer']['isim']['sinir']
      and not omu['kapi']['olcer']['isim']['PASS'], (r['durum'], r['kod'], omu.get('ozet', {}).get('isim_kuculme')))
    Ai, ti = AT.metin_alfa('EMILY', ort.mt.font_isim, 40.0, 500)
    oc = dict(ad='isimler', tur='isim', metin='EMILY', font=ort.mt.font_isim, wght=500, ref='H', cap=40.0, A=np.pad(Ai, ((0, 1), (0, 0))), taban=ti, x=0, y=0, k=7)
    k('bilinen FAIL SERT cerceve: 1 px buyutulmus 1x maske -> k kat cerceve tam kati degil, DUR cerceve',
      dur_mu(lambda: AT.altin_ogeler(ort.mt, [oc], ort.hr['har'], ort.hr['qa_goz'], Lana, veri['D_ana']), 'cerceve'))
    ob_ = dict(Y1['grup_oge'][1])
    ob_['k'] = ob_['k'] + 60
    k('bilinen FAIL SERT buyutme yok: k kat cizimi kaynaktan buyuk grup ogesi -> DUR grup_buyutme (AT:860-861)',
      dur_mu(lambda: AT.altin_ogeler(ort.mt, [ob_], ort.hr['har'], ort.hr['qa_goz'], Lana, veri['D_ana']), 'grup_buyutme'))
    rgb = td / 'rgb.png'
    Image.new('RGB', (64, 64)).save(rgb)
    bos = td / 'bos.png'
    Image.new('RGBA', (64, 64), (0, 0, 0, 0)).save(bos)
    dolu = td / 'dolu.png'
    Image.new('RGBA', (64, 64), (200, 150, 50, 255)).save(dolu)
    k('bilinen FAIL SERT sembol bicimi: RGB katman, bos alfali katman ve tam dolu alfali katman -> girdi hatasi sembol_bicim',
      dur_mu(lambda: AT.sembol_yukle(rgb), 'sembol_bicim', True) and dur_mu(lambda: AT.sembol_yukle(bos), 'sembol_bicim', True)
      and dur_mu(lambda: AT.sembol_yukle(dolu), 'sembol_bicim', True))
    # bilinen cakisma, PASS yonu (geometri; altin cizimi olmadan): kucuk burclar posterdeki yerinde (v 0,95) sembolden ayrik
    Yp = TD.grup_yerlestir(ort, ayar(kucuk_v=0.95))
    Mp = {o['ad']: KP.tuvale(o['A'], o['x'], o['y'], 1087, 1087) for o in Yp['grup_oge'][1:3]}
    Mp['sembol'] = KP.tuvale(Yp['sembol']['a'], Yp['sembol']['x'], Yp['sembol']['y'], 1087, 1087)
    k('bilinen cakisma olceri iki yonde calisir: kucuk_v 0,95 (poster yeri) ile sembol / kucuk burc cakismasi iki tanimda da 0; B1 (0,37) ile > 0',
      KP.cakisma_takvim([('kucuk1', Mp['kucuk1']), ('kucuk2', Mp['kucuk2']), ('sembol', Mp['sembol'])]) == 0 and KP.cakisma_ornament(Mp) == {}
      and ol['cakisma']['takvim_binme_piksel'] > 0)

    # --- butce: `kos` asil modda, butceyi asan istekte URETMEDEN durur (liste kirpilmaz)
    sure = td / 'SURE_olcum.json'
    sure.write_text(json.dumps(sahte_sure([dict(durum='tamam', toplam_sn=100.0)])))
    ist11 = td / 'istek11.json'
    ist11.write_text(json.dumps(dict(taban='B1', tekil=[{}, dict(logo=1.0, logo_yer='kucuk_arasi')],
                                     izgara=dict(halka_r_carpan=[0.85, 1.0, 1.15], grup_y_fark=[-0.05, 0, 0.05]))))
    cb = td / 'butce'
    rcb = TD.main(['kos', '--kaynak', KS, '--urun', str(URUN_DOSYA), '--istek', str(ist11), '--katman', str(katman), '--cikti', str(cb), '--sure', str(sure)])
    dj = json.loads((cb / 'DUR.json').read_text(encoding='utf-8')) if (cb / 'DUR.json').is_file() else {}
    k('bilinen FAIL butce (komut): 11 secenek x 100 sn + 20 = 1120 sn > 900 -> cikis 3, hicbir secenek uretilmedi, mesajda sigan en buyuk sayi 8; liste kirpilmadi',
      rcb == 3 and dj.get('kod') == 'girdi_butce' and 'sigan en buyuk secenek sayisi 8' in dj.get('neden', '') and not list(cb.glob('SEC_*')) and not (cb / 'OZET.json').exists(), (rcb, dj))
    cs = td / 'suresiz'
    k('bilinen FAIL butce (komut): asil kosu olcum SURE dosyasi olmadan -> cikis 3, uretim yok',
      TD.main(['kos', '--kaynak', KS, '--urun', str(URUN_DOSYA), '--istek', str(ist11), '--katman', str(katman), '--cikti', str(cs)]) == 3 and not list(cs.glob('SEC_*')))
    sure_k = td / 'SURE_kisa.json'
    sure_k.write_text(json.dumps(sahte_sure([dict(durum='tamam', toplam_sn=1.0)])))
    cb9 = td / 'butce901'
    k('bilinen FAIL butce (komut; inceleme 1. tur bulgu 6): --butce 901 -> cikis 3, uretim yok (butce 900 sn sabitinden buyutulemez)',
      TD.main(['kos', '--kaynak', KS, '--urun', str(URUN_DOSYA), '--istek', str(ist11), '--katman', str(katman), '--cikti', str(cb9), '--sure', str(sure_k),
               '--butce', '901']) == 3 and not list(cb9.glob('SEC_*')))
    k("GERCEK SURE dosyasi (kosu A): ayni urun girdisiyle asil kosu butcesine girdi olur; baska urun girdisi kimligiyle (bilinen FAIL) kullanilamaz",
      TD.butce_kontrol(1, sj, 900, False, TD.kosu_kimligi(URUN_DOSYA))['mod'] == 'asil'
      and dur_mu(lambda: TD.butce_kontrol(1, sj, 900, False, dict(sj['kimlik'], urun_sha256='0' * 64)), 'girdi_butce', True))
    ud = td / 'dikey.json'
    ud.write_text(json.dumps(DIKEY))
    k('bilinen FAIL komut: dikey urun girdisiyle kos -> cikis 3 (dilim 1: gorsel yalniz yuvarlak)',
      TD.main(['kos', '--kaynak', KS, '--urun', str(ud), '--istek', str(istek), '--katman', str(katman), '--cikti', str(td / 'dk'), '--olcum']) == 3)
    k("bilinen FAIL komut: `uret` OZET'te olmayan secenek numarasi -> cikis 3",
      TD.main(['uret', '--kaynak', KS, '--ozet', str(cA / 'OZET.json'), '--secenek', '9', '--katman', str(katman), '--cikti', str(td / 'u9')]) == 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak'); ap.add_argument('--ornament'); ap.add_argument('--katman'); ap.add_argument('--zorunlu', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    with tempfile.TemporaryDirectory(dir=str(Path(a.kaynak).resolve().parent) if a.kaynak else None) as td_:
        td = Path(td_)
        (td / 'ag').mkdir(); t_ag(td / 'ag')
        t_urun()
        t_butce()
        t_urun_23mm()
        t_olcer_sahte()
        (td / 'c').mkdir(); t_cikti_sahte(td / 'c')
        (td / 'p').mkdir(); t_pafta_sahte(td / 'p')
        if a.kaynak:
            (td / 'k').mkdir(); t_kaynak(a.kaynak, td / 'k')
            t_ayar()
            if a.ornament:
                t_ornament(a.ornament)
            else:
                atla('ornament yolu yok (ornament tanimlariyla esdegerlik)', 8)
            katman = Path(a.katman) if a.katman else None
            if katman is None:
                (td / 's').mkdir()
                rc = TD.main(['sembol', '--kaynak', str(a.kaynak), '--cikti', str(td / 's')])
                katman = td / 's' / f'DENEME_{TD.CIFT}_ana.png'
                k('yerel deneme sembolu uretildi (AT deneme komutu aynen; DENEME_ adli)', rc == 0 and katman.is_file())
            (td / 'm').mkdir(); t_motor(Path(a.kaynak).resolve(), katman.resolve(), td / 'm')
        else:
            atla('kaynak yolu yok (ay takvimi modulu, ayar dogrulama, motorlu testler)', 183)
    top = SAYAC['pas'] + SAYAC['fail']
    print(f"tasarim_deneme testleri: {SAYAC['pas']}/{top} PASS" + (f", {SAYAC['atla']} test ATLANDI" if SAYAC['atla'] else '') + f" | {time.time() - t0:.0f} sn", flush=True)
    return 1 if SAYAC['fail'] or (a.zorunlu and SAYAC['atla']) else 0


if __name__ == '__main__':
    sys.exit(main())
