#!/usr/bin/env python3
"""TASARIM DENEME ARACI, dilim 1 (Serdar 11 Kas 2026; plan: dal plan/tasarim-deneme 3fdcc5b docs/tasarim_deneme/PLAN_TASARIM_DENEME.md).
Urunun baski alani verilince sabit ogelerle (ana sembol + halka + iki kucuk burc + logo + isimler + tek satir metin) yerlesim seceneklerini
GERCEK oranda, sistematik uretir. Arac secenekleri puanlamaz, siralamaz, "onerilen" diye isaretlemez; secenek numarasi uretim sirasidir.
Etsy / Printful / musteri YOK. Cikti yalniz --cikti klasorune; depoya gorsel yazilmaz. YEREL kosu, deneme semboluyle (Serdar 11 Kas "C"):
kapi sonucu gercek katman icin kanit DEGILDIR (OZET ve pafta basliginda yazar).

ALTIN YOLU, SEMBOL GRUBU, LOGO: ay takvimi kodundan DEGISTIRILMEDEN ice alinir (deneme araci sifirdan yazilmaz). Kaynaklar sabit sha ile
`git archive` klasorunden: ay takvimi a9b1323 (ay_takvim_ornek.py = AT, ay_takvim_kapi.py = ATK), motor siparis-gpt 6da763a (motor_gpt/).
Kullanilan her kaynak dosyanin sha256'si kosudan ONCE KAYNAK_SHA256 ile karsilastirilir; biri farkliysa DUR (sert). AT / ATK normal `import`
ile TEK modul olarak yuklenir (ATK:68-69 ayni adi arar). Yuklenen modulun sabiti DEGISTIRILMEZ.

Kapsam (dilim 1): yuvarlak sekil; taban B1 (ornament cevrimi; BILINEN CAKISMA: kucuk burclar ana sembole biner, plan 3.4); logo yalniz
'kucuk_arasi' (AT logo_kaynak aynen: poster kesimi + temizlik); isimler 'tek_satir' ("A & B", AT:1433); tek satir metin; grup izgarasi.
Kapsam DISI: B2, diger izgaralar, iki ornek seti, kombinasyonlar, cok sayfali pafta, 'isim_arasi' logo, onbellek, kutuphane, dikey / yatay
gorsel uretimi, is akisi. GERI DONUS (plan 3.3): isim_duzen 'iki_yan' ya da logo_yer 'isim_arasi' istenirse DUR yok; 'tek_satir' ve logo
'yok' uygulanir, OZET ve pafta basligina "geri donus" yazilir.
KAPALI AYARLAR (Serdar'a sorulmadi; plan 3.3): halka_kalinlik yalniz 1,0; halka_centik yalniz 'ozgun'; baska deger girdi hatasi.
BUTCE (Serdar 11 Kas "A"; plan 4.5 b): yerel kosu basina 900 sn. Istek suresi = kurulum + secenek sayisi x olculen secenek suresi (olcum
kosusunun SURE.json'u; tam cizimi biten seceneklerin EN BUYUGU). Asiyorsa uretmeden DUR ve sigan en buyuk sayi yazilir; arac listeyi KIRPMAZ.

Kullanim (hepsi --kaynak K: icinde ay/scripts/ay_takvim ve motor/motor_gpt olan `git archive` klasoru):
  tasarim_deneme.py sembol --kaynak K --cikti D                         yerel deneme sembolu (AT deneme komutu aynen; DENEME_ adli)
  tasarim_deneme.py kos --kaynak K --urun U.json --istek I.json --katman P.png --cikti D (--olcum | --sure SURE.json) [--butce 900]
  tasarim_deneme.py uret --kaynak K --ozet OZET.json --secenek N --katman P.png --cikti D     tek secenegi OZET'teki ayardan yeniden uretir
Cikis: 0 tamam, 1 en az bir secenek sert DUR (digerleri uretildi) ya da yeniden uretim sha'si farkli, 3 girdi hatasi (uretim yok),
4 DUR (kaynak / ortam), 2 cokus."""
import argparse
import hashlib
import json
import math
import re
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, features

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()

AY_SHA = 'a9b13230d64e9c0f5937e0e8af07530dc13f3079'
MOTOR_SHA = '6da763aa5b9820027420f73264fc69d30e120a33'
ORNAMENT_SHA = 'c950151627b4aba29bdea8f75e4c533cea599424'
# `git archive <sha>` ciktisindan uretildi (11 Kas 2026). motor: AT.MOTOR_DOSYA (AT:127-129; KILIT ve logo dahil) + ciftin poster ana alfasi.
KAYNAK_SHA256 = {
    'ay': {
        'ay_takvim_ornek.py': '28110f3872fd1147e992a7cbbe236cdbdf5713db794d4ee0be7364245998c9a1',
        'ay_takvim_kapi.py': '2aaa1b95fef43ad0f342305d13783caf8a441efaac606a91516260ba8ee6753f',
    },
    'motor': {
        'KILIT_GPTGIRDI.json': '8ab7a9ea4725b41a9187dfe44f4e062912a243c066dfbe649d291273d4ccba43',
        'golge_motor.py': 'e7592412d5fc370c465fb628c5e8955ac219fb5f98a47b08c7dfc53eac42094f',
        'vektor_yuzey.py': '92aa56eae68d9e199780d683e893d1edc892993533c665addfb2e402b228a4b5',
        'alfa_temizle.py': '8e3f34dc80032572798ed8d7e056fe96869a03121bc6cda45e1f3f40766bdaeb',
        'kure/k4.npy': '21816b3bc961a293cdf06d60cda6f06da533d0343978722eda91fb3d83fd2a65',
        'palet/chatgpt_altin.png': 'b4480319399f7c5a8a152e59ab3ad5df9ee3b3eb426b0e1fa6e74abd0e3a33e8',
        'yerlesim78.json': 'a833ffec0d05aa35dfdd6608fd9003784ccb5cc7546e55f96e4c38bbe96af783',
        'cember.json': '8fc9dc92bf9c63bf7b37afdbdc2a215eba3ba37e41438d661e4118e9a262c70b',
        'zemin_profil.json': '092257b74bb7f9d1054dd9e1e4521b061d7fdd4799139646cc53181ee6d4e0bb',
        'ref/ref.png': '42e3a771928fe26a3b1c4cee044114dd85046280a5c4f84234f043b8effb532c',
        'font/Cinzel.ttf': 'f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34',
        'font/EBGaramond-Italic.ttf': 'bba2c4499c93c9612b90b9825d32b07da52fce2fe57562a1eb6b833553f93c4e',
        'alfa_ogeler.npz': 'd373403191a6245eccf386f0aa01d6380996b72e22d20e3ae8c7c5f6839d16e9',
        'girdi/KUCUK_1.png': '7df6b609d1017537a162c9b1564d930ca870d3e7499b101fb01b2a54ebeacca6',
        'girdi/KUCUK_2.png': 'd3effe1672458c60fb417388864a0b63b444eedb59433e10d98dc29c413a4abc',
        'girdi/LOGO_1.png': '62239238b25dbc5417dab4dc353fdbf15129599c9372737d5d8ddb86b3042061',
        'girdi78/ana/cancer_libra_alfa.png': 'f946f5611431bdf976dce3475db8fd653faf1242ca267c365e2e29c8b3c8a8c2',
    },
}
AY_YOL, MOTOR_YOL = 'ay/scripts/ay_takvim', 'motor/motor_gpt'
# YUZEY (plan 2.3): aracin ice aldigi her AT / ATK adinin beklenen imzasi. AY_SHA yukseltilirken fark burada gorunur (baglan DUR verir).
YUZEY = {
    'AT.isim_dogrula': "(ham, alan)",
    'AT.metin_dogrula': "(satirlar)",
    'AT.metin_alfa': "(metin, font_yolu, cap_px, wght=None, ref='H', ss=4)",
    'AT.isim_sigdir': "(metin, font_yolu, sinir=None, cap0=150, cap_alt=53, yumusak=False)",
    'AT.cizim_katsayisi': "(cap_px)",
    'AT.kutu': "(a, t=0.02)",
    'AT.labf': "(x)",
    'AT.de00': "(Lab1, Lab2)",
    'AT.yari_kal': "(a)",
    'AT.boya': "(taban, ogeler, dis=None)",
    'AT.altin_ogeler': "(mt, ogeler, har, qa_goz, Lana, D_ana)",
    'AT.zemin_radyal': "(md, P, Wc, Hc, f, cx, cy)",
    'AT.zemin_yildiz': "(zemin, md, gm, f, ox=0.0, oy=0.0, maske=None, engel=None, sayac=None)",
    'AT.zemin_8bit': "(zemin, gm, P)",
    'AT.sembol_yukle': "(yol)",
    'AT.rgba_olcek': "(rgba, k)",
    'AT.grup_kur': "(mt, cift, g, yan_json, hedef_r, merkez='grup', kucuk_u='poster', kucuk_v='poster', kucuk_oran=1.0, halka_kalinlik=1.0, "
                   "halka_centik='ozgun', logo='yok')",
    'AT.logo_kaynak': "(mt, C, y_mer)",
    'AT.main': "(argv=None)",
    'AT.Motor.harita_kur': "(self, cift, onbellek=None)",
    'AT.Motor.oge_katman': "(self, a_k, k, rng, har, qa_goz, ad='yazi')",
    'ATK.grup_kapisi': "(meta, D, katman_g, yan_json, motor, sa, sx, sy)",
    'ATK.kontrast_olc': "(rgb, m, cekirdek=0.9, haric=None)",
    'ATK.cember_uydur': "(m)",
    'ATK.halka_kalinlik_olc': "(m, cx, cy)",
    'ATK.lum': "(rgb)",
}
CIFT = 'CANCER_LIBRA'                                   # bu parcada tek cift (AT:107; plan soru 10 a)
SINIR_NOTU = 'yerel, deneme sembolü; kapı sonucu gerçek katman için kanıt değildir'       # OZET (Serdar 11 Kas, Genel Merkez notu)
SINIR_NOTU_ASCII = 'yerel, deneme sembolu; kapi sonucu gercek katman icin kanit degildir'  # pafta basligi: ASCII (Pillow gomulu yazi tipinde
#                                                                                             Turkce harf glifi yok: olcum); OZET.json'da tam yazim
B1_ETIKET = 'B1 ornament cevrimi: BILINEN CAKISMA (kucuk burclar ana sembole biner; plan 3.4). Etiket olcumdur, oneri ya da siralama degildir.'
BUTCE_SN = 900                                          # Serdar 11 Kas soru 14 "A": yerel kosu basina
OLCUM_AZAMI = 3                                         # olcum kosusu en cok 3 secenek (baslangic degeri; plan 4.5 b)
ILK_GECIS_HEDEF = 64.0                                  # halka_r iki gecis: ilk gecis KUCUK sabit hedef (px; baslangic degeri; plan 3.3)
ONIZLEME_TAM = 1600                                     # tuval kisa kenari <= 1600 px ise onizleme tam boy (baslangic degeri; plan 5)
PAFTA_AZAMI_BAYT, PAFTA_KALITE = 3 * 1024 * 1024, (88, 82, 76, 70)
URUN_AD = re.compile(r'[A-Z0-9_]{1,40}', re.ASCII)
SEKILLER = ('yuvarlak', 'dikey', 'yatay')
MM_KAYNAK = ('resmi', 'ölçüm', 'varsayım')
EKSEN_ORAN = 0.005                                      # iki eksenin px / mm orani en cok %0,5 ayrisabilir (baslangic degeri; plan 5)

# AYAR (plan 3.3). Uzunluklar yerlesim biriminde (yuvarlakta Rg = guvenli yaricap); kucuk_u / kucuk_v halka yaricapi biriminde (AT:1057-1058),
# logo AT biriminde (carpan; 1,0 = posterdeki logo boyu x grup olcegi; AT:116). Araliklar BASLANGIC DEGERIDIR (yalniz yanlis girisi yakalar).
AYAR_ANAHTAR = ('taban', 'grup_merkez', 'grup_x', 'grup_y', 'halka_r', 'grup_r', 'kucuk_u', 'kucuk_v', 'kucuk_oran', 'halka_kalinlik',
                'halka_centik', 'isim_duzen', 'isim_cap', 'isim_y', 'logo', 'logo_yer', 'metin_tur', 'metin_cap', 'metin_y', 'satir_aralik',
                'isim1', 'isim2', 'satirlar')
AYAR_ARALIK = dict(grup_x=(-1.0, 1.0), grup_y=(-1.0, 1.0), halka_r=(0.30, 1.20), grup_r=(0.30, 1.20), kucuk_u=(0.30, 0.90),
                   kucuk_v=(0.20, 1.30), kucuk_oran=(0.60, 1.80), halka_kalinlik=(1.0, 1.0), isim_cap=(0.03, 0.30), isim_y=(-1.0, 1.0),
                   logo=(0.50, 2.00), metin_cap=(0.03, 0.30), metin_y=(-1.0, 1.0), satir_aralik=(1.2, 2.2))
AYAR_SERBEST = dict(kucuk_u='poster', kucuk_v='poster', logo='yok')
AYAR_SECIM = dict(grup_merkez=('grup', 'halka'), halka_centik=('ozgun',), isim_duzen=('tek_satir', 'iki_yan'),
                  logo_yer=('kucuk_arasi', 'isim_arasi'), metin_tur=('yok', 'tarih', 'mesaj'))
METIN_SATIR_AZAMI = 1                                   # dilim 1: tek satir metin
# TABAN: kod varsayilani YOK; her kosu `taban` ister (plan 3.3; soru 5 karari yok). B2 bu dilimde tanimli degil (Serdar 11 Kas "A").
# B1 = ornament yerlesiminin goreli birimlere cevrimi (plan 3.4; O4:34, 37; YD:28-29, 44-45): hesap, onayli kayit degil ("aday").
TABAN = {'B1': dict(grup_merkez='halka', grup_x=0.0, grup_y=0.071, halka_r=0.884, grup_r=None, kucuk_u='poster', kucuk_v=0.37,
                    kucuk_oran=1.0, halka_kalinlik=1.0, halka_centik='ozgun', isim_duzen='iki_yan', isim_cap=0.0742, isim_y=0.650,
                    logo='yok', logo_yer='isim_arasi', metin_tur='tarih', metin_cap=round(0.0742 * 144 / 169.5, 5), metin_y=0.817,
                    satir_aralik=1.6, isim1='EMILY', isim2='JAMES', satirlar=['JUNE 14, 2025'])}
IZGARA_AZAMI = 7                                        # izgara ekseni basina en cok 7 deger (baslangic degeri)
IZGARA_ANAHTAR = ('halka_r_carpan', 'grup_y_fark')      # grup izgarasi (boyut = halka_r carpani, yer = grup_y farki; plan 4.2)
IZGARA_TUR = {'grup': IZGARA_ANAHTAR,                   # bir istekte TEK izgara turu (dilim 1b; Serdar 12 Kas)
              'kucuk': ('kucuk_oran_carpan', 'kucuk_v_fark')}   # kucuk burc izgarasi (boyut = kucuk_oran carpani, yer = kucuk_v farki; plan 4.2)

AT = ATK = None                                         # baglan() sonrasi: ice alinan ay takvimi modulleri (TEK nesne)


class Dur(Exception):
    """girdi=True: girdi hatasi (cikis 3; uretim yok). girdi=False: DUR (cikis 4). AT.Dur ile ayni alanlar (kod, neden, girdi)."""

    def __init__(self, kod, neden, girdi=False):
        super().__init__(f'{kod}: {neden}')
        self.kod, self.neden, self.girdi = kod, neden, girdi


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def sha_dosya(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def _dur_mu(e):
    return isinstance(e, Dur) or (AT is not None and isinstance(e, AT.Dur))


# ---------------------------------------------------------------- kaynak (sabit sha256) ve ice alma
def kaynak_dogrula(kaynak):
    """Sabit kaynak kapisi (SERT): tablodaki her dosyanin sha256'si ayni olmali. Doner {'ay/..': sha, ...}. Eksik / farkli: DUR."""
    K = Path(kaynak)
    out = {}
    for grup, yol in (('ay', AY_YOL), ('motor', MOTOR_YOL)):
        for ad, beklenen in KAYNAK_SHA256[grup].items():
            f = K / yol / ad
            if not f.is_file():
                raise Dur('kaynak_eksik', f'{grup}/{ad} yok')
            h = sha_dosya(f)
            if h != beklenen:
                raise Dur('kaynak_sha', f'{grup}/{ad} sha256 sabit tabloyla ayni degil')
            out[f'{grup}/{ad}'] = h
    return out


def yuzey_kontrol(at, atk):
    """Ice alinan adlarin varligi ve imzasi (YUZEY). Doner uyusmayanlarin listesi (bos = tamam)."""
    import inspect
    kok = dict(AT=at, ATK=atk)
    fark = []
    for ad, beklenen in YUZEY.items():
        nesne = None
        try:
            parca = ad.split('.')
            nesne = kok[parca[0]]
            for q in parca[1:]:
                nesne = getattr(nesne, q)
            imza = str(inspect.signature(nesne))
        except (AttributeError, TypeError, ValueError):
            imza = None
        if imza != beklenen:
            fark.append(ad)
    return fark


def baglan(kaynak):
    """Kaynaklari dogrular, sonra AT ve ATK'yi normal import ile TEK modul olarak yukler (plan 2.3). Ikinci cagri ayni klasorle zararsizdir."""
    global AT, ATK
    sha = kaynak_dogrula(kaynak)
    ay = str((Path(kaynak) / AY_YOL).resolve())
    if AT is not None:
        if str(Path(AT.__file__).resolve().parent) != ay:
            raise Dur('kaynak_cift', 'ay takvimi modulu baska klasorden yuklu')
        return sha
    if 'ay_takvim_ornek' in sys.modules or 'ay_takvim_kapi' in sys.modules:
        raise Dur('kaynak_cift', 'ay takvimi modulu onceden yuklenmis')
    sys.path.insert(0, ay)
    import ay_takvim_ornek
    import ay_takvim_kapi
    if str(Path(ay_takvim_ornek.__file__).resolve().parent) != ay or ay_takvim_kapi.U is not ay_takvim_ornek:
        raise Dur('kaynak_cift', 'ay takvimi modulu beklenen klasorden yuklenmedi')
    fark = yuzey_kontrol(ay_takvim_ornek, ay_takvim_kapi)
    if fark:
        raise Dur('kaynak_yuzey', f'ay takvimi yuzeyi beklenen imzalarla ayni degil: {fark}')
    AT, ATK = ay_takvim_ornek, ay_takvim_kapi
    return sha


def ortam_kapisi():
    """SERT (AT:1389-1391; CM "PILLOW"): pillow 11.0.0 + raqm."""
    raqm = bool(features.check('raqm'))
    if Image.__version__ != '11.0.0' or not raqm:
        raise Dur('ortam', f'pillow {Image.__version__} raqm {raqm}; pillow 11.0.0 + raqm acik olmali')
    return dict(python=sys.version.split()[0], numpy=np.__version__, opencv=cv2.__version__, pillow=Image.__version__, raqm=raqm)


# ---------------------------------------------------------------- urun girdisi
def _sayi(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def urun_dogrula(d):
    """Urun girdisi (plan 3.1). Bilinmeyen alan, eksik alan, yanlis tur, aralik disi = girdi hatasi. Hata mesajinda ham deger yok."""
    def hata(alan, tur):
        raise Dur('girdi_urun', f'{tur}: {alan}', girdi=True)
    if not isinstance(d, dict):
        raise Dur('girdi_urun', 'urun sozluk degil', girdi=True)
    zorunlu = ('ad', 'sekil', 'baski_px', 'gercek_mm', 'mm_kaynak', 'guvenli', 'guvenli_pay_px', 'yasak', 'zemin')
    serbest = ('alt_sinir', 'kesim', 'ornek_en_kotu', 'not')
    for k_ in d:
        if k_ not in zorunlu + serbest:
            hata('#' + str(list(d).index(k_) + 1), 'bilinmeyen alan')
    for k_ in zorunlu:
        if k_ not in d:
            hata(k_, 'eksik alan')
    if not isinstance(d['ad'], str) or not URUN_AD.fullmatch(d['ad']):
        hata('ad', 'desen disi')
    if d['sekil'] not in SEKILLER:
        hata('sekil', 'bilinmeyen sekil')
    for alan in ('baski_px', 'gercek_mm'):
        v = d[alan]
        if not isinstance(v, list) or len(v) != 2 or not all(_sayi(x) and x > 0 for x in v):
            hata(alan, 'yanlis tur / deger')
    if not all(isinstance(x, int) and 64 <= x <= 20000 for x in d['baski_px']):
        hata('baski_px', 'aralik disi')
    ox, oy = d['baski_px'][0] / d['gercek_mm'][0], d['baski_px'][1] / d['gercek_mm'][1]
    if abs(ox / oy - 1.0) > EKSEN_ORAN:
        hata('gercek_mm', 'eksen orani ayrisiyor')
    mk = d['mm_kaynak']
    if not isinstance(mk, dict) or mk.get('tur') not in MM_KAYNAK or set(mk) - {'tur', 'not'}:
        hata('mm_kaynak', 'yanlis tur / deger')
    g = d['guvenli']
    W, H = d['baski_px']
    if d['sekil'] == 'yuvarlak':
        if not isinstance(g, dict) or set(g) - {'cx', 'cy', 'r', 'etiket'} or not all(_sayi(g.get(k_)) for k_ in ('cx', 'cy', 'r')):
            hata('guvenli', 'yanlis tur / deger')
        if not (0 < g['r'] <= max(W, H) and 0 <= g['cx'] <= W and 0 <= g['cy'] <= H):
            hata('guvenli', 'aralik disi')
    else:
        if not isinstance(g, dict) or set(g) - {'x0', 'y0', 'x1', 'y1', 'etiket'} or not all(_sayi(g.get(k_)) for k_ in ('x0', 'y0', 'x1', 'y1')):
            hata('guvenli', 'yanlis tur / deger')
        if not (0 <= g['x0'] < g['x1'] <= W and 0 <= g['y0'] < g['y1'] <= H):
            hata('guvenli', 'aralik disi')
    if not _sayi(d['guvenli_pay_px']) or not 0 <= d['guvenli_pay_px'] <= 100:
        hata('guvenli_pay_px', 'aralik disi')
    if not isinstance(d['yasak'], list):
        hata('yasak', 'yanlis tur')
    for i, y in enumerate(d['yasak'], 1):                                    # delik, aski, centik (emsal O4:38-41, 219-224)
        if not isinstance(y, dict) or y.get('tur') not in ('daire', 'kutu', 'ust_cizgi'):
            hata(f'yasak #{i}', 'yanlis tur / deger')
        alan = dict(daire=('cx', 'cy', 'r'), kutu=('x0', 'y0', 'x1', 'y1'), ust_cizgi=('y',))[y['tur']]
        if set(y) - set(alan) - {'tur', 'ad', 'halka_haric'} or not all(_sayi(y.get(k_)) for k_ in alan) \
                or not isinstance(y.get('halka_haric', False), bool):
            hata(f'yasak #{i}', 'yanlis tur / deger')
    if d['zemin'] != 'motor':
        hata('zemin', 'bu parcada yalniz motor')
    a = d.get('alt_sinir')
    if a is not None:
        if not isinstance(a, dict) or set(a) - {'yazi_mm', 'cizgi_mm', 'kaynak', 'etiket'} \
                or not all(_sayi(a.get(k_)) and a[k_] > 0 for k_ in ('yazi_mm', 'cizgi_mm')):
            hata('alt_sinir', 'yanlis tur / deger')
    return d


def tuval_boyu(urun):
    """Cizim tuvali = urunun baski alani (TAM boy; cikti degistiren kisayol yok, plan 5.1)."""
    return int(urun['baski_px'][0]), int(urun['baski_px'][1])


def mm_px(urun):
    """mm = px x gercek mm / baski alani px (Dayanak 5). Doner px basina mm (x ekseni; eksen farki urun_dogrula'da sinirli)."""
    return float(urun['gercek_mm'][0]) / float(urun['baski_px'][0])


def birim(urun):
    """Yerlesim birimi: yuvarlakta (cx, cy, Rg = guvenli yaricap); dikdortgende guvenli kutunun merkezi ve kisa kenarin yarisi."""
    g = urun['guvenli']
    if urun['sekil'] == 'yuvarlak':
        return float(g['cx']), float(g['cy']), float(g['r'])
    return (g['x0'] + g['x1']) / 2.0, (g['y0'] + g['y1']) / 2.0, min(g['x1'] - g['x0'], g['y1'] - g['y0']) / 2.0


def grup_merkezi(urun, ayar):
    """Grup merkezinin tuval noktasi (tam sayi): ayardaki grup_x / grup_y. (Kapi bu noktayi BAGIMSIZ hesaplar: tasarim_kapi.beklenen_merkez.)"""
    cx, cy, Rg = birim(urun)
    return int(round(cx + ayar['grup_x'] * Rg)), int(round(cy + ayar['grup_y'] * Rg))


def kiris(urun, y0, y1):
    """Guvenli alanin [y0, y1] satir araligindaki en dar yatay genisligi (px; pay dusulmus). Yuvarlakta kiris; dikdortgende kutu genisligi."""
    pay = float(urun['guvenli_pay_px'])
    if urun['sekil'] != 'yuvarlak':
        g = urun['guvenli']
        return max(0.0, g['x1'] - g['x0'] - 2 * pay) if (y0 >= g['y0'] + pay and y1 <= g['y1'] - pay) else 0.0
    cx, cy, Rg = birim(urun)
    r = Rg - pay
    dy = max(abs(y0 - cy), abs(y1 - cy))
    return 2.0 * math.sqrt(r * r - dy * dy) if dy < r else 0.0


# ---------------------------------------------------------------- AYAR ve istek
def ayar_dogrula(ham):
    """AYAR sozlugu (plan 3.3): `taban` ZORUNLU (kod varsayilani yok). Bilinmeyen anahtar, aralik disi, yanlis tur = girdi hatasi (uretim yok).
    Hata mesajinda HAM girdi YOK: yalniz hata turu ve anahtarin sirasi (AT:219-306 kalibi). Doner (TAM ayar, geri donus listesi).
    Etkin ayarda halka_r / grup_r'den tam biri sayidir, digeri None."""
    def hata(i, tur):
        raise Dur('girdi_ayar', f'{tur} #{i}', girdi=True)
    if not isinstance(ham, dict):
        raise Dur('girdi_ayar', 'ayar sozluk degil', girdi=True)
    sira = {}
    for i, k_ in enumerate(ham, 1):
        if not isinstance(k_, str) or k_ not in AYAR_ANAHTAR:
            hata(i, 'bilinmeyen anahtar')
        sira[k_] = i
    if 'taban' not in ham:
        raise Dur('girdi_ayar', 'taban verilmedi (kod varsayilani yok)', girdi=True)
    if not isinstance(ham['taban'], str) or ham['taban'] not in TABAN:
        hata(sira['taban'], 'bilinmeyen taban')
    AY = dict(TABAN[ham['taban']], taban=ham['taban'])
    AY['satirlar'] = list(AY['satirlar'])
    if 'halka_r' in ham and 'grup_r' in ham:
        hata(sira['grup_r'], 'halka_r ve grup_r birlikte')
    if 'grup_r' in ham:
        AY['halka_r'] = None
    if 'halka_r' in ham:
        AY['grup_r'] = None
    for k_, secim in AYAR_SECIM.items():
        if k_ in ham:
            if not isinstance(ham[k_], str):
                hata(sira[k_], 'yanlis tur')
            if ham[k_] not in secim:
                hata(sira[k_], 'aralik disi')
            AY[k_] = ham[k_]
    for k_, (lo, hi) in AYAR_ARALIK.items():
        if k_ not in ham:
            continue
        v = ham[k_]
        if isinstance(v, str) and k_ in AYAR_SERBEST:
            if v != AYAR_SERBEST[k_]:
                hata(sira[k_], 'aralik disi')
        elif isinstance(v, bool) or not isinstance(v, (int, float)):
            hata(sira[k_], 'yanlis tur')
        elif not (isinstance(v, int) or math.isfinite(v)) or not lo <= v <= hi:      # cok buyuk tam sayi da aralik disi (tasma yok)
            hata(sira[k_], 'aralik disi')
        AY[k_] = v
    for k_ in ('isim1', 'isim2'):
        if k_ in ham:
            if not isinstance(ham[k_], str):
                hata(sira[k_], 'yanlis tur')
            AY[k_] = ham[k_]
        AY[k_] = AT.isim_dogrula(AY[k_], k_)
    if 'satirlar' in ham:
        if not isinstance(ham['satirlar'], list) or not all(isinstance(v, str) for v in ham['satirlar']):
            hata(sira['satirlar'], 'yanlis tur')
        AY['satirlar'] = list(ham['satirlar'])
    if AY['metin_tur'] == 'yok':
        if 'satirlar' in ham and ham['satirlar']:
            hata(sira['satirlar'], 'metin_tur yok iken satir')
        AY['satirlar'] = []
    AY['satirlar'] = AT.metin_dogrula(AY['satirlar'])
    if len(AY['satirlar']) > METIN_SATIR_AZAMI:
        raise Dur('girdi_metin', f"{len(AY['satirlar'])} satir > {METIN_SATIR_AZAMI} (dilim 1)", girdi=True)
    if AY['metin_tur'] != 'yok' and not AY['satirlar']:
        raise Dur('girdi_metin', 'metin_tur var, satir yok', girdi=True)
    geri = []                                                                 # GERI DONUS (plan 3.3): DUR yok, etiket var
    if AY['isim_duzen'] == 'iki_yan':
        AY['isim_duzen'] = 'tek_satir'
        geri.append('isim_duzen iki_yan -> tek_satir (isimlerin arasi logo kodu dilim 3)')
    if AY['logo_yer'] == 'isim_arasi':
        AY['logo'] = 'yok'
        geri.append('logo_yer isim_arasi -> logo yok (isimlerin arasi logo kodu dilim 3)')
    return AY, geri


def _json_oku(metin, ne):
    """Yinelenen anahtar, NaN / Infinity sabiti, bozuk JSON = girdi hatasi (AT:284-295 kalibi)."""
    def sabit_yok(_):
        raise ValueError('sabit')

    def tekil(ciftler):
        d = dict(ciftler)
        if len(d) != len(ciftler):
            raise ValueError('yinelenen anahtar')
        return d
    try:
        return json.loads(metin, parse_constant=sabit_yok, object_pairs_hook=tekil)
    except (ValueError, RecursionError):
        raise Dur('girdi_json', f'{ne}: bozuk JSON', girdi=True) from None


def istek_kur(ham):
    """Istek (dogrulanan girdi): {taban, tekil: [ayar farki sozlugu ...], izgara: {halka_r_carpan: [...], grup_y_fark: [...]} YA DA
    {kucuk_oran_carpan: [...], kucuk_v_fark: [...]}} (bir istekte tek izgara turu).
    Doner secenek listesi: dict(no, ad (KODDAN: SEC_<NN>_<tur>), tur, ayar (TAM), geri_donus, degisen (tabana gore), satir, sutun).
    Sira = uretim sirasi: once tekiller, sonra izgara (satir = boyut adimi, sutun = yer adimi). Arac listeyi kirpmaz, siralamaz."""
    if not isinstance(ham, dict) or set(ham) - {'taban', 'tekil', 'izgara'}:
        raise Dur('girdi_istek', 'istek sozluk degil ya da bilinmeyen alan', girdi=True)
    if 'taban' not in ham:
        raise Dur('girdi_ayar', 'taban verilmedi (kod varsayilani yok)', girdi=True)
    taban = ham['taban']
    if not isinstance(taban, str) or taban not in TABAN:
        raise Dur('girdi_ayar', 'bilinmeyen taban', girdi=True)
    tekil = ham.get('tekil', [])
    if not isinstance(tekil, list) or not all(isinstance(t, dict) for t in tekil):
        raise Dur('girdi_istek', 'tekil liste degil', girdi=True)
    sec = []

    def ekle(fark, tur, satir=None, sutun=None):
        if 'taban' in fark:
            raise Dur('girdi_istek', 'taban yalniz istek duzeyinde verilir', girdi=True)
        try:
            AY, geri = ayar_dogrula(dict(fark, taban=taban))
        except Exception as e:                                               # noqa: BLE001
            if not _dur_mu(e):
                raise
            raise Dur(e.kod, f'secenek {len(sec) + 1}: {e.neden}', girdi=True) from None
        no = len(sec) + 1
        sec.append(dict(no=no, ad=f'SEC_{no:02d}_{tur}', tur=tur, ayar=AY, geri_donus=geri, degisen={k_: AY[k_] for k_ in fark},
                        satir=satir, sutun=sutun))
    for t in tekil:
        ekle(t, 'tekil')
    iz = ham.get('izgara')
    if iz is not None:
        tur_ = next((t_ for t_, an_ in IZGARA_TUR.items() if isinstance(iz, dict) and set(iz) == set(an_)), None)
        if tur_ is None:
            raise Dur('girdi_istek', 'izgara: TEK tur olmali: grup (halka_r_carpan + grup_y_fark) ya da kucuk burc (kucuk_oran_carpan + kucuk_v_fark)',
                      girdi=True)
        an = IZGARA_TUR[tur_]
        for k_ in an:
            v = iz[k_]
            if not isinstance(v, list) or not 1 <= len(v) <= IZGARA_AZAMI or not all(_sayi(x) for x in v) or len(set(v)) != len(v):
                raise Dur('girdi_istek', f'izgara {k_}: 1 - {IZGARA_AZAMI} farkli sayi olmali', girdi=True)
        T = TABAN[taban]
        if T['halka_r'] is None or T['grup_merkez'] != 'halka':               # "tek oge degisir" yalniz halka_r + 'halka' merkezde (plan 4.2)
            raise Dur('girdi_istek', 'izgara tabani halka_r + halka merkez modunda degil', girdi=True)
        if tur_ == 'kucuk' and not (_sayi(T['kucuk_v']) and _sayi(T['kucuk_oran'])):
            raise Dur('girdi_istek', 'kucuk burc izgarasi: tabanda kucuk_v ve kucuk_oran sayi olmali', girdi=True)
        for i, c in enumerate(iz[an[0]]):                                     # satir = boyut adimi
            for j, f in enumerate(iz[an[1]]):                                 # sutun = yer adimi
                if tur_ == 'grup':
                    ekle(dict(halka_r=round(T['halka_r'] * c, 6), grup_y=round(T['grup_y'] + f, 6)), 'grup', i, j)
                else:
                    ekle(dict(kucuk_oran=round(T['kucuk_oran'] * c, 6), kucuk_v=round(T['kucuk_v'] + f, 6)), 'kucuk', i, j)
    if not sec:
        raise Dur('girdi_istek', 'secenek yok', girdi=True)
    return sec


SURE_ALAN = ('mod', 'kimlik', 'kurulum_sn', 'toplam_sn', 'secenek', 'asama')
SURE_SECENEK_ALAN = ('no', 'ad', 'durum', 'kod', 'toplam_sn')
CIZIMI_BITEN_DUR = ('kapi_sert',)                       # cizim ve kayit bittikten SONRA verilen DUR kodlari (butce suresine girer)


def sure_dogrula(d):
    """Sure kaydi (plan 8 "sure kaydi"): alanlar tam, sureler sayi ve >= 0, bitis >= baslangic. Eksik / bozuk alan = DUR 'sure_kayit'."""
    def hata(n_):
        raise Dur('sure_kayit', n_)
    if not isinstance(d, dict):
        hata('sure kaydi sozluk degil')
    for a_ in SURE_ALAN:
        if a_ not in d:
            hata(f'eksik alan: {a_}')
    if d['mod'] not in ('olcum', 'asil') or not isinstance(d['kimlik'], dict):
        hata('mod / kimlik gecersiz')
    for a_ in ('kurulum_sn', 'toplam_sn'):
        if not _sayi(d[a_]) or d[a_] < 0:
            hata(f'{a_} sayi degil ya da negatif')
    if not isinstance(d['secenek'], list) or not d['secenek']:
        hata('secenek listesi bos')
    for s_ in d['secenek']:
        if not isinstance(s_, dict) or any(a_ not in s_ for a_ in SURE_SECENEK_ALAN) or not _sayi(s_['toplam_sn']) or s_['toplam_sn'] < 0:
            hata('secenek kaydinda eksik / bozuk alan')
    A = d['asama']
    if not isinstance(A, dict) or not all(isinstance(A.get(a_), str) and len(A[a_]) == 20 for a_ in ('baslangic', 'bitis')):
        hata('asama baslangic / bitis eksik')
    try:
        b0, b1 = (time.strptime(A[a_], '%Y-%m-%dT%H:%M:%SZ') for a_ in ('baslangic', 'bitis'))
    except ValueError:
        hata('asama zamani okunamadi')
    if b1 < b0:
        hata('bitis baslangictan once')
    return d


def kod_sha():
    """Arac kod dosyalarinin (tasarim_deneme.py, tasarim_kapi.py) sha256'lari."""
    return {f.name: sha_dosya(f) for f in sorted(Path(__file__).resolve().parent.glob('tasarim_*.py'))}


def kosu_kimligi(urun_yolu):
    """Bir kosunun sure olcumu baska urun / kaynak / KOD icin kullanilamasin diye: urun girdisi sha256 + sabit kaynak sha'lari + kod sha256
    (kod degisirse olcum kosusu yeniden yapilir; Serdar 12 Kas)."""
    return dict(urun_sha256=sha_dosya(urun_yolu), ay_sha=AY_SHA, motor_sha=MOTOR_SHA, kod_sha256=kod_sha())


def cizimi_biten(s_):
    """Butce kurali: cizimi BITEN secenek = durumu 'tamam' olan ya da DUR kodu cizimden sonra verilen (kapi_sert). Cizimden once DUR veren girmez."""
    return isinstance(s_, dict) and (s_.get('durum') == 'tamam' or (s_.get('durum') == 'DUR' and s_.get('kod') in CIZIMI_BITEN_DUR))


def butce_kontrol(n, sure, butce, olcum, kimlik=None):
    """Butce kurali (plan 4.5 b; Serdar soru 14 "A": 900 sn). Butce 900 sn'den BUYUK verilemez (kucuk verilebilir). Olcum kosusu: en cok
    OLCUM_AZAMI secenek. Asil kosu: OLCUM kosusunun SURE'si ZORUNLU (mod 'olcum', ayni urun girdisi ve ayni kaynak); istek suresi =
    kurulum + n x (cizimi BITEN seceneklerin en buyugu: 'tamam' ya da DUR 'kapi_sert'; cizimden once DUR veren haric). Asiyorsa URETMEDEN girdi
    hatasi; mesajda sigan en buyuk sayi. Liste kirpilmaz."""
    if not _sayi(butce) or butce <= 0 or butce > BUTCE_SN:
        raise Dur('girdi_butce', f'butce {BUTCE_SN} sn sabitinden buyuk ya da gecersiz (Serdar soru 14)', girdi=True)
    if olcum:
        if n > OLCUM_AZAMI:
            raise Dur('girdi_butce', f'olcum kosusu en cok {OLCUM_AZAMI} secenek ({n} istendi)', girdi=True)
        return dict(mod='olcum', secenek=n, butce_sn=butce)
    if not isinstance(sure, dict):
        raise Dur('girdi_butce', 'asil kosu olcum kosusunun SURE.json dosyasini ister', girdi=True)
    try:
        sure_dogrula(sure)
    except Exception as e:                                                   # noqa: BLE001
        if not _dur_mu(e):
            raise
        raise Dur('girdi_butce', f'olcum SURE kaydi gecersiz: {e.neden}', girdi=True) from None
    if sure['mod'] != 'olcum':
        raise Dur('girdi_butce', 'SURE dosyasi olcum kosusundan degil', girdi=True)
    if kimlik is None or sure['kimlik'] != kimlik:
        raise Dur('girdi_butce', 'SURE dosyasi baska urun girdisi, baska kaynak ya da baska kod icin olculmus (olcum kosusunu yeniden yap)', girdi=True)
    tam = [s['toplam_sn'] for s in sure['secenek'] if cizimi_biten(s) and _sayi(s.get('toplam_sn'))]
    if not tam or max(tam) <= 0:
        raise Dur('girdi_butce', 'olcum kosusunda cizimi biten secenek yok', girdi=True)
    t_kur, t_sec = float(sure['kurulum_sn']), float(max(tam))
    istek = t_kur + n * t_sec
    sigan = max(0, int(math.floor((butce - t_kur) / t_sec)))
    b = dict(mod='asil', secenek=n, butce_sn=butce, kurulum_sn=round(t_kur, 1), secenek_sn=round(t_sec, 1), istek_sn=round(istek, 1),
             sigan_en_buyuk=sigan)
    if istek > butce:
        raise Dur('girdi_butce', f'istek suresi {istek:.0f} sn > butce {butce} sn; sigan en buyuk secenek sayisi {sigan} (liste kirpilmadi)',
                  girdi=True)
    return b


# ---------------------------------------------------------------- kurulum (kosu basina bir kez)
class Ortam:
    """Kosu ortami: kaynak sha'lari, Motor (tek), ana sembol katmani, renk haritasi. Kurulum suresi SURE'ye yazilir."""

    def __init__(self, kaynak, katman, urun):
        t = time.time()
        self.kaynak = Path(kaynak).resolve()
        self.kaynak_sha = baglan(self.kaynak)
        self.paketler = ortam_kapisi()
        self.urun = urun_dogrula(urun)
        self.md = self.kaynak / MOTOR_YOL
        self.mt = AT.Motor(self.md)
        self.katman = Path(katman)
        self.g, self.s_olc = AT.sembol_yukle(self.katman)
        self.yan_json = self.s_olc.get('yan_json')
        self.hr = self.mt.harita_kur(CIFT, None)                              # renk haritasi (onbelleksiz; dilim 1'de onbellek yok)
        self.cevre = {}                                                       # halka_r ilk gecis sonucu: (merkez, u, v, oran) -> bilgi
        self.kurulum_sn = round(time.time() - t, 1)
        log('kurulum', self.kurulum_sn, 'sn | sembol', self.s_olc['boyut'], '| motor', len(self.mt.sha), 'dosya')


def olcek_kontrol(ort, AY):
    """halka_r modu, ilk gecis ve "buyutme yok" ust uclari (plan 3.3). Ilk gecis: AT.grup_kur KUCUK sabit hedefle (ILK_GECIS_HEDEF),
    halka_kalinlik 1,0, halka_centik 'ozgun', logo 'yok' -> grubun cevre yaricapi (olcek ve cevre dairesi ozgun halkadan ve logosuz
    hesaplanir, AT:1193-1198, 1217-1225). olcek = halka_r x Rg / cember R. olcek, ana sembol olcegi, olcek x kucuk_oran ya da logo toplam
    olcegi 1'i asarsa girdi hatasi (AT:1226-1227, 1249-1250 ile ayni kosullar, uretimden once). grup_r modunda None doner."""
    if AY['halka_r'] is None:
        return None
    cx, cy, Rg = birim(ort.urun)
    anahtar = (AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'])
    if anahtar not in ort.cevre:
        B1 = AT.grup_kur(ort.mt, CIFT, ort.g, ort.yan_json, ILK_GECIS_HEDEF, AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'],
                         1.0, 'ozgun', 'yok')['bilgi']
        ort.cevre[anahtar] = dict(er=B1['cevre_yaricap_poster'], R=B1['cember']['R'], s_ana=B1['s_ana'])
    c = ort.cevre[anahtar]
    olcek = AY['halka_r'] * Rg / c['R']
    ko = float(AY['kucuk_oran'])
    if olcek > 1.0 or olcek * c['s_ana'] > 1.0 or olcek * ko > 1.0:
        raise Dur('girdi_olcek', f"olcek {olcek:.4f} (ana {olcek * c['s_ana']:.4f}, kucuk {olcek * ko:.4f}) > 1 (buyutme yok)", girdi=True)
    if AY['logo'] != 'yok' and olcek * float(AY['logo']) > 1.0:
        raise Dur('girdi_olcek', f"logo toplam olcegi {olcek * float(AY['logo']):.4f} > 1 (buyutme yok)", girdi=True)
    return olcek * c['er']


def grup_hesapla(ort, AY):
    """Sembol grubu, AT.grup_kur AYNEN (AT:1186-1286). halka_r modu IKI GECIS (olcek_kontrol); grup_r modu hedef = grup_r x Rg.
    Hedef yaricap kapi 2'nin kurdugu ifadeyle AYNI kayan sayi olsun diye 1,0 x (hedef / S) x S olarak verilir (ATK:219).
    Doner (G, sembol_alan, hedef_r)."""
    cx, cy, Rg = birim(ort.urun)
    hedef = olcek_kontrol(ort, AY)
    if hedef is None:
        hedef = AY['grup_r'] * Rg
    sembol_alan = hedef / AT.S
    hedef_r = 1.0 * sembol_alan * AT.S
    G = AT.grup_kur(ort.mt, CIFT, ort.g, ort.yan_json, hedef_r, AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'],
                    AY['halka_kalinlik'], AY['halka_centik'], AY['logo'])
    return G, sembol_alan, hedef_r


def grup_yerlestir(ort, AY):
    """Grubu kurar ve tuvale yerlestirir: grup ogeleri ana sembolle AYNI tam sayi merkezden (AT:1499-1500). Doner dict(G, sembol_alan,
    hedef_r, merkez [mx, my], sembol (rgb, a, x, y, bilgi), grup_oge (x, y mutlak))."""
    mx, my = grup_merkezi(ort.urun, AY)
    G, sembol_alan, hedef_r = grup_hesapla(ort, AY)
    s_rgb, s_a = G['ana']['rgb'], G['ana']['a']
    grup_oge = G['ogeler']
    for o in grup_oge:
        o['x'], o['y'] = mx + o['x'], my + o['y']
    k05 = AT.kutu(s_a, 0.5)
    eb = (k05[2] - k05[0]) / (k05[3] - k05[1])
    s_bilgi = dict(olcek=G['ana']['olcek'], kutu_05=list(k05), en_boy_05=round(eb, 5), en_boy_fark=round(abs(eb - ort.s_olc['en_boy_05']), 5),
                   boyut=[int(s_a.shape[1]), int(s_a.shape[0])], hedef=G['ana']['hedef'])
    return dict(G=G, sembol_alan=sembol_alan, hedef_r=hedef_r, merkez=[mx, my],
                sembol=dict(rgb=s_rgb, a=s_a, x=mx + G['ana']['x'], y=my + G['ana']['y'], bilgi=s_bilgi), grup_oge=grup_oge)


def on_kontrol(ort, secenekler):
    """Uretimden ONCE: her secenegin "buyutme yok" ust uclari hesaplanir; asan = girdi hatasi (kosu baslamaz, hicbir secenek uretilmez)."""
    for s in secenekler:
        try:
            olcek_kontrol(ort, s['ayar'])
        except Exception as e:                                               # noqa: BLE001
            if not _dur_mu(e):
                raise
            raise Dur(e.kod, f"secenek {s['no']}: {e.neden}", girdi=True) from None


# ---------------------------------------------------------------- tek secenek (TEK uretim yolu: pafta kosusu da `uret` komutu da bunu cagirir)
def srgb_icc():
    """sRGB ICC profili, BELIRLENIMCI: ImageCms profil basligina olusturma anini yazar (bayt 24-35), bu yuzden ayni piksellerin PNG sha256'si
    kosudan kosuya degisirdi (11 Kas olcumu: piksel farki 0, dosya sha'si farkli). Tarih alani sabitlenir; profilin kendisi degismez."""
    icc = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
    icc[24:36] = bytes([0x07, 0xEA, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0])            # 2026-01-01 00:00:00 (6 x uint16, buyuk uclu)
    return bytes(icc)


def _kesisim(x, y, h, w, W, H):
    """Ogenin (sol ust x, y; boy h, w) tuvalle kesisimi: (y0, y1, x0, x1, yerel y, yerel x) ya da None. (AT:1365-1370, tuval parametreli.)"""
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return None
    return y0, y1, x0, x1, y0 - y, x0 - x


def secenek_uret(ort, sec, cikti):
    """Bir secenegi GERCEK yolla, TAM boyda cizer, kapilari olcer, dosyalari yazar. Doner sonuc sozlugu (durum 'tamam' | 'DUR').
    Cizim sirasi emsal (AT:853): yazilar once, grup ogeleri sonra, logo sonda. Sert DUR'da gorsel yoktur; secenek gizlenmez."""
    import tasarim_kapi as KP
    O = Path(cikti)
    O.mkdir(parents=True, exist_ok=True)
    ad, AY, urun = sec['ad'], sec['ayar'], ort.urun
    t_bas = time.time()
    sure = {}
    sonuc = dict(no=sec['no'], ad=ad, tur=sec['tur'], durum='DUR', kod=None, neden=None, ayar=AY, degisen=sec['degisen'],
                 geri_donus=sec['geri_donus'], satir=sec.get('satir'), sutun=sec.get('sutun'), png_sha256=None, sure=sure)
    png = O / f'{ad}.png'
    for f in (png, O / f'{ad}_onizleme.jpg', O / f'{ad}_isaret.jpg', O / f'{ad}_OLCUM.json'):
        if f.exists():
            f.unlink()
    try:
        if urun['sekil'] != 'yuvarlak':
            raise Dur('girdi_sekil', 'dilim 1: gorsel uretimi yalniz yuvarlak sekil', girdi=True)
        t_ = time.time()
        mt = ort.mt
        W, H = tuval_boyu(urun)
        cx, cy, Rg = birim(urun)
        # 1 sembol grubu (AT.grup_kur aynen)
        Y = grup_yerlestir(ort, AY)
        G, sembol_alan, hedef_r, (mx, my) = Y['G'], Y['sembol_alan'], Y['hedef_r'], Y['merkez']
        s_rgb, s_a, sx, sy, s_bilgi = Y['sembol']['rgb'], Y['sembol']['a'], Y['sembol']['x'], Y['sembol']['y'], Y['sembol']['bilgi']
        grup_oge = Y['grup_oge']
        k05 = s_bilgi['kutu_05']
        # D_ana: ana sembolun yari kalinligi, yerlesen piksele cevrilmis (AT:1418-1423 ile ayni satirlar)
        g = ort.g
        kx0, ky0, kx1, ky1 = AT.kutu(g[..., 3], 0.02)
        gk = g[max(0, ky0 - 2):ky1 + 2, max(0, kx0 - 2):kx1 + 2]
        a16 = gk[..., 3] if gk.shape[1] <= 1600 else AT.rgba_olcek(gk, 1600 / gk.shape[1])[1]
        k16 = AT.kutu(a16, 0.5)
        D_ana = AT.yari_kal(a16) * (k05[2] - k05[0]) / (k16[2] - k16[0])
        del gk, a16
        sure['grup'] = round(time.time() - t_, 1); t_ = time.time()
        # 2 yazi sekilleri (1x; son alfa). Isim satiri tek dizi "A & B" (AT:1433); sinir = guvenli alanin o satirdaki kirisi.
        FI, FM = mt.font_isim, mt.font_metin
        ogeler, kontrol = [], {}
        isim_metni = f"{AY['isim1']} & {AY['isim2']}"
        cap0 = AY['isim_cap'] * Rg
        isim_taban_y = cy + AY['isim_y'] * Rg
        sinir = kiris(urun, isim_taban_y - cap0, isim_taban_y)
        isim_disinda = bool(sinir == 0.0)                                     # buyuk harf bandinin bir kismi guvenli dairenin (pay dusulmus) disinda
        if isim_disinda:                                                      # K3 (Serdar 12 Kas "evet"; onayli tek gevsetme): DUR YOK; isim de tarih satiri
            sinir = float(W)                                                  # gibi olcerdir; genislik siniri = tuval genisligi (pay dusulmez)
        elif sinir < 1.0:                                                     # kiris 0'dan buyukken davranis AYNEN (kiris cok kucukse isim kuculur ya da DUR)
            raise AT.Dur('isim_sigmadi', 'isim satiri icin guvenli alan kirisi 1 px altinda')
        Ai, ti, cap_isim, kuc = AT.isim_sigdir(isim_metni, FI, sinir=sinir, cap0=cap0, cap_alt=0.0, yumusak=True)
        ogeler.append(dict(ad='isimler', tur='isim', metin=isim_metni, font=FI, wght=500, ref='H', cap=float(cap_isim), A=Ai, taban=ti,
                           taban_hedef=isim_taban_y))
        genis = []
        cap_m = AY['metin_cap'] * Rg
        for i, s in enumerate(AY['satirlar']):
            As, ts = AT.metin_alfa(s, FM, cap_m, None, ref='T')
            ty = cy + AY['metin_y'] * Rg + i * AY['satir_aralik'] * cap_m
            ks = AT.kutu(As)
            sm = kiris(urun, ty - cap_m, ty)
            if ks[2] - ks[0] > sm:
                genis.append(f'metin satiri {i + 1} genisligi {ks[2] - ks[0]} px > kiris {sm:.0f} px (kucultulmez)')
            ogeler.append(dict(ad=f'metin_{i + 1}', tur='metin', metin=s, font=FM, wght=None, ref='T', cap=float(cap_m), A=As, taban=ts,
                               taban_hedef=ty, sinir=sm))
        kontrol['metin_genis'] = dict(PASS=not genis, neden='; '.join(genis) or None)
        for o in ogeler:                                                      # yerlesim: yatay murekkep kutusu merkezi = guvenli merkez; dikey taban (AT:1486-1491)
            k_ = AT.kutu(o['A'])
            o['kutu'] = k_
            o['k'] = AT.cizim_katsayisi(o['cap'])
            o['x'] = int(round(cx - (k_[0] + k_[2]) / 2.0))
            o['y'] = int(round(o['taban_hedef'] - o['taban']))
            o['taban_y'] = o['y'] + o['taban']
        # 3 tuval disi: sembol tasarsa ya da bir oge tumuyle disaridaysa DUR; kismi tasma olcer (AT:1501-1508)
        tasan = [o['ad'] for o in ogeler + grup_oge if o['x'] < 0 or o['y'] < 0 or o['x'] + o['A'].shape[1] > W or o['y'] + o['A'].shape[0] > H]
        if sx < 0 or sy < 0 or sx + s_a.shape[1] > W or sy + s_a.shape[0] > H:
            raise AT.Dur('tasma', 'sembol tuval disina tasiyor')
        for o in ogeler + grup_oge:
            if _kesisim(o['x'], o['y'], *o['A'].shape, W, H) is None:
                raise AT.Dur('tasma', f"{o['ad']} tumuyle tuval disinda")
        kontrol['tasma'] = dict(PASS=not tasan, neden=(', '.join(tasan) + ' tuval disina tasiyor') if tasan else None, oge=list(tasan))
        tuval_kesilen = {}
        for o in ogeler + grup_oge:
            y0, y1, x0, x1, ly, lx = _kesisim(o['x'], o['y'], *o['A'].shape, W, H)
            ic = o['A'][ly:ly + y1 - y0, lx:lx + x1 - x0]
            tuval_kesilen[o['ad']] = int((o['A'] > 0.02).sum() - (ic > 0.02).sum())
            if o['tur'] == 'isim' and not (ic > 0.02).any():                  # isim maskesi tuvalde BOS kalirsa cokme yok: DUR (cizimden once)
                raise AT.Dur('isim_sigmadi', 'isim murekkebi tumuyle tuval disinda')
        sure['yazi'] = round(time.time() - t_, 1); t_ = time.time()
        # 4 zemin: motor radyal profili + yildiz yolu, es oranli olcek, merkez = grup merkezi (AT:1510-1531 kalibi; disk / rakam yok)
        Zp = json.loads((ort.md / 'zemin_profil.json').read_text())
        f_z = W / float(Zp['olcek'])
        zem = AT.zemin_radyal(ort.md, mt.P, W, H, f_z, float(mx), float(my))
        y_maske = np.zeros((H, W), np.uint8)
        ox, oy = mx - Zp['cx'] * f_z, my - Zp['cy'] * f_z
        engel = np.zeros((H, W), np.uint8)
        for o in ogeler + grup_oge:
            y0, y1, x0, x1, ly, lx = _kesisim(o['x'], o['y'], *o['A'].shape, W, H)
            engel[y0:y1, x0:x1][o['A'][ly:ly + y1 - y0, lx:lx + x1 - x0] > 0.02] = 255
        engel[sy:sy + s_a.shape[0], sx:sx + s_a.shape[1]][s_a > 0.02] = 255
        ek = int(round(61 * W / 7200.0)) | 1                                  # yildiz engel payi tuvale oranli, AYNEN (AT:1526; Serdar soru 6 j)
        engel = cv2.dilate(engel, np.ones((ek, ek), np.uint8))
        ysay = {}
        n_yildiz = AT.zemin_yildiz(zem, ort.md, mt.gm, f_z, ox, oy, y_maske, engel, ysay) if mt.P['yildiz'] == 'refkopya' else 0
        del engel
        img = AT.zemin_8bit(zem, mt.gm, mt.P)
        del zem
        altinsiz = img.copy()
        sure['zemin'] = round(time.time() - t_, 1); t_ = time.time()
        # 5 altin: sembol (dokunulmaz) + yazilar + grup ogeleri, AT.altin_ogeler AYNEN (200 cekirdek piksel alti: DUR 'renk_uyum_piksel')
        Lana = np.median(AT.labf(s_rgb[s_a >= 0.9]), 0)
        altin = AT.altin_ogeler(mt, ogeler + grup_oge, ort.hr['har'], ort.hr['qa_goz'], Lana, D_ana)
        for o, b_ in zip(ogeler + grup_oge, altin):                           # tuval disina tasan ogeyi tuval siniri keser (AT:1560-1566)
            y0, y1, x0, x1, ly, lx = _kesisim(o['x'], o['y'], *o['A'].shape, W, H)
            if (y1 - y0, x1 - x0) != o['A'].shape:
                dl = (slice(ly, ly + y1 - y0), slice(lx, lx + x1 - x0))
                o['A'], o['atest'] = np.ascontiguousarray(o['A'][dl]), np.ascontiguousarray(o['atest'][dl])
                o['x'], o['y'] = x0, y0
                b_.update(x=x0, y=y0, rgb=np.ascontiguousarray(b_['rgb'][dl]), m=o['A'])
        son = AT.boya(img, [dict(ad='sembol', x=sx, y=sy, rgb=s_rgb, m=s_a, ic=None, carpan=1.0)] + altin)
        del img
        sure['altin'] = round(time.time() - t_, 1); t_ = time.time()
        # 6 kayit: son gorsel PNG (dpi etiketi urun girdisinden; sRGB)
        dpi = 25.4 / mm_px(urun)
        Image.fromarray(son).save(png, dpi=(dpi, dpi), icc_profile=srgb_icc(), compress_level=6)
        sure['kayit'] = round(time.time() - t_, 1); t_ = time.time()
        # 7 kapilar: son gorsel KAYDEDILEN dosyadan, maskeler bellekten (plan 7.3 madde 2)
        veri = dict(urun=urun, ayar=AY, cift=CIFT, png=png, altinsiz=altinsiz, yildiz_maske=y_maske, sembol=dict(rgb=s_rgb, a=s_a, x=sx, y=sy, bilgi=s_bilgi),
                    ogeler=ogeler, grup_oge=grup_oge, grup_bilgi=G['bilgi'], merkez=[mx, my], hedef_r=hedef_r, sembol_alan=sembol_alan,
                    katman=ort.katman, s_olc=ort.s_olc, motor=ort.md, mt=mt, kontrol=kontrol, tuval_kesilen=tuval_kesilen, D_ana=D_ana,
                    isim=dict(cap_baslangic=cap0, cap=float(cap_isim), deneme=kuc, sinir=sinir, guvenli_disinda=isim_disinda), tuval_kirpilan=list(tasan),
                    yildiz=dict(sayi=int(n_yildiz), atlanan=ysay,
                                                                                                    engel_cekirdek_px=ek))
        olcum = KP.olc(veri)
        sure['kapi'] = round(time.time() - t_, 1); t_ = time.time()
        sonuc['olcum_ozet'] = olcum['ozet']
        sonuc['k'] = {o['ad']: int(o['k']) for o in ogeler + grup_oge}
        sonuc['tuval'] = [W, H]
        sonuc['altin_sirasi'] = [o['ad'] for o in ogeler + grup_oge]
        olcum['sure'] = sure
        if olcum['ozet']['sert_fail']:
            png.unlink()
            sonuc.update(kod='kapi_sert', neden='sert kapi FAIL: ' + ', '.join(olcum['ozet']['sert_fail']))
        else:
            sonuc.update(durum='tamam', png_sha256=sha_dosya(png))
            onz = son
            if min(W, H) > ONIZLEME_TAM:                                      # buyuk tuval: tam boyun kucultulmusu (AT:1574 kalibi)
                f_ = ONIZLEME_TAM / float(min(W, H))
                onz = cv2.resize(son, (int(round(W * f_)), int(round(H * f_))), interpolation=cv2.INTER_AREA)
            Image.fromarray(onz).save(O / f'{ad}_onizleme.jpg', quality=92, subsampling=0)
            isaret_ciz(son, olcum, urun).save(O / f'{ad}_isaret.jpg', quality=90, subsampling=0)
        (O / f'{ad}_OLCUM.json').write_text(json.dumps(olcum, indent=1, ensure_ascii=False, default=float))
    except Exception as e:                                                    # noqa: BLE001
        if not _dur_mu(e):
            raise
        if png.exists():
            png.unlink()
        sonuc.update(kod=e.kod, neden=e.neden, girdi_hatasi=bool(e.girdi))
        (O / f'{ad}_OLCUM.json').write_text(json.dumps(dict(ozet=dict(ad=ad, durum='DUR', kod=e.kod, neden=e.neden, sert_fail=[e.kod])),
                                                         indent=1, ensure_ascii=False))
    sure['toplam_sn'] = round(time.time() - t_bas, 1)
    log(f"{ad}: {sonuc['durum']}" + (f" {sonuc['kod']}: {sonuc['neden']}" if sonuc['durum'] != 'tamam' else '') + f" | {sure['toplam_sn']} sn")
    return sonuc


# ---------------------------------------------------------------- gorsel yardimcilari (isaret, pafta); cizim fonksiyonlarina ERISMEZ
def _font(boy):
    return ImageFont.load_default(size=boy)                                  # Pillow'un gomulu yazi tipi (sistem fontuna bagli degil)


def isaret_ciz(son, olcum, urun):
    """Onizlemenin KOPYASI: alt sinirin altindaki ya da guvenli alani asan ogeler cerceveyle, yaninda mm degeri. Temiz onizleme degismez."""
    im = Image.fromarray(son).convert('RGB')
    d = ImageDraw.Draw(im)
    f = _font(max(11, min(im.size) // 70))
    for ad, o in olcum['oge'].items():
        isaret = o.get('isaret') or []
        if not isaret:
            continue
        x0, y0, x1, y1 = o['kutu']
        d.rectangle([x0 - 3, y0 - 3, x1 + 2, y1 + 2], outline=(255, 64, 64), width=2)
        d.text((x0, max(0, y0 - 5 - f.size * len(isaret))), '\n'.join(f'{ad}: {s}' for s in isaret), fill=(255, 220, 220), font=f)
    if urun['sekil'] == 'yuvarlak':
        cx, cy, Rg = birim(urun)
        r = Rg - float(urun['guvenli_pay_px'])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(120, 200, 255), width=1)
    return im


def dur_kodu(s):
    """DUR veren secenegin kapi kodu; sert kapi FAIL'inde kapi adlariyla (orn. "kapi_sert: 2_grup")."""
    sf = (s.get('olcum_ozet') or {}).get('sert_fail') or []
    return f"{s['kod']}" + (': ' + ', '.join(sf) if s['kod'] == 'kapi_sert' and sf else '')


def _kir(metin, font, gen):
    """Metni font ile en cok `gen` px genislikte satirlara boler (sozcuk sinirindan; tek sozcuk sigmazsa harften). Metin KESILMEZ."""
    out, satir = [], ''
    for soz in str(metin).split(' '):
        while font.getlength(soz) > gen and len(soz) > 1:                     # tek sozcuk hucreden genis: harften bol
            n_ = len(soz) - 1
            while n_ > 1 and font.getlength(soz[:n_]) > gen:
                n_ -= 1
            if satir:
                out.append(satir)
                satir = ''
            out.append(soz[:n_])
            soz = soz[n_:]
        if satir and font.getlength(satir + ' ' + soz) > gen:
            out.append(satir)
            satir = soz
        else:
            satir = (satir + ' ' + soz).strip()
    out.append(satir)
    return out


def etiket_satirlari(s, mm_kaynak=None):
    """Pafta hucre etiketi (plan 5.1): yalniz olcum; duz metin, tek renk, vurgu ve siralama yok. Girdi: OZET'teki secenek kaydi.
    mm_kaynak 'varsayım' ise etikette yazar (plan 5.1)."""
    L = [f"{s['no']:02d} {s['ad']}"]
    if s['degisen']:
        L.append(', '.join(f'{k_}={v}' for k_, v in s['degisen'].items()))
    else:
        L.append('taban ayari')
    if mm_kaynak == 'varsayım':
        L.append('mm kaynagi: varsayim')
    if s['durum'] != 'tamam':
        L.append(f"DUR {dur_kodu(s)}")
        L.append(str(s['neden']))
        kok = (s.get('olcum_ozet') or {}).get('kok_neden')
        if kok:                                                               # K2 (Serdar 12 Kas): kapi sonucu ve kodu ayni; hucrede kok neden de yazar
            L.append(kok)
        boy = (s.get('olcum_ozet') or {}).get('kapi2_boyut_fark')
        if boy is not None:                                                   # K1: DUR veren secenekte de olculen boy kosulu farki yazilir
            L.append(f'kapi 2 boy kosulu farki {boy} px')
        return L
    o = s['olcum_ozet']
    L.append(f"yazi buyuk harf en kucuk {o['yazi_en_kucuk_mm']} mm | isim kuculme {o['isim_kuculme']}")
    L.append(f"cizgi mm en ince {o['cizgi_mm']['en_ince']} / p1 {o['cizgi_mm']['p1']} / ortanca {o['cizgi_mm']['ortanca']}")
    a = o['sinir_alti']
    L.append(f"sinir alti oge: yazi {a['yazi']} | cizgi en ince {a['cizgi_en_ince']}, p1 {a['cizgi_p1']}, ortanca {a['cizgi_ortanca']}")
    t = o['tasma_px']
    L.append(f"tasma px: isik 0: {t['isik_0']} | isik 8: {t['isik_8']} | goruntu farki: {t['goruntu_farki']} | tuval disi: {t['tuval_disi']}")
    c = o['cakisma']
    L.append(f"cakisma: takvim tanimi {c['takvim_px']} px | ornament tanimi {c['ornament_cift']} cift, {c['ornament_px']} px")
    L.append('cakisan cift px (alfa > 0,02): ' + (', '.join(f'{k_} {v}' for k_, v in o.get('cift_px', {}).items() if v) or 'yok'))
    ky = o.get('kucuk_yazi_px') or {}
    L.append(f"kucuk burc - yazi en az uzaklik px: isim {ky.get('isim')} | metin {ky.get('metin')}")
    L.append(f"grup-yazi bosluk en az {o['grup_yazi_en_az_px']} px | cikti kapisi {o['cikti']}")
    if o.get('isim_guvenli_disinda'):                                         # K3 notu
        L.append('isim guvenli alan disinda')
    L.append('olcer FAIL: ' + (', '.join(o['olcer_fail']) or 'yok'))
    return L


def pafta_basligi(ozet):
    """Pafta baslik satirlari (ASCII): sinir notu, mm kaynagi (varsayimsa etiket), taban etiketi, geri donus, siralama yok notu."""
    mk = ozet['urun']['mm_kaynak']['tur']
    bas = [f"TASARIM DENEME | urun {ozet['urun']['ad']} | taban {ozet['taban']} | {SINIR_NOTU_ASCII}",
           f"mm kaynagi: {mk} (px basina {ozet['mm_px']:.5f} mm)" + (' | VARSAYIM: mm degerleri dogrulanmamis eslemeyle' if mk == 'varsayım' else ''),
           ozet['taban_etiket'], 'geri donus: ' + ('; '.join(ozet['geri_donus']) or 'yok'),
           'Hucre sirasi uretim sirasidir; etiketler yalniz olcumdur (siralama, puan, oneri yok).']
    return [b.replace('ı', 'i').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ş', 's').replace('ğ', 'g') for b in bas]


def pafta_yaz(ozet, klasor, out, hucre=520):
    """Tek sayfa pafta. Girdi YALNIZ OZET ve kaydedilmis son gorsel dosyalari (cizim fonksiyonu cagirmaz). Her dosyanin sha256'si OZET'teki
    ile ayni olmali (degilse DUR). Hucre = son gorselin TEK adim INTER_AREA kucultulmusu. Dizilis: ust satir tekiller, altinda izgara
    (satir = boyut adimi, sutun = yer adimi); sira uretim sirasidir. JPEG en cok 3 MB (kalite 88 -> 70; yine asarsa DUR)."""
    K = Path(klasor)
    sec = ozet['secenek']
    tekil = [s for s in sec if s['tur'] == 'tekil']
    izg = [s for s in sec if s['tur'] != 'tekil']
    n_sut = max([len(tekil)] + [s['sutun'] + 1 for s in izg] + [1])
    n_sat = (1 if tekil else 0) + (max(s['satir'] for s in izg) + 1 if izg else 0)
    f, fb = _font(13), _font(17)
    mk = ozet['urun']['mm_kaynak']['tur']
    etk = {s['no']: [q for t in etiket_satirlari(s, mk) for q in _kir(t, f, hucre - 4)] for s in sec}   # satirlar hucre genisligine kirilir
    e_sat = max(len(v) for v in etk.values())
    bant = e_sat * (f.size + 3) + 10
    pay = 12
    bas = pafta_basligi(ozet)
    Wp = pay + n_sut * (hucre + pay)
    bas = [q for b in bas for q in _kir(b, fb, Wp - 2 * pay)]                 # baslik satirlari sayfa genisligine gore kirilir (kesilmez)
    ust = len(bas) * (fb.size + 5) + 14
    Hp = ust + n_sat * (hucre + bant + pay) + pay
    sayfa = Image.new('RGB', (Wp, Hp), (246, 246, 246))
    d = ImageDraw.Draw(sayfa)
    for i, b in enumerate(bas):
        d.text((pay, 8 + i * (fb.size + 5)), b, fill=(0, 0, 0), font=fb)
    hucreler = {}

    def koy(s, sat, sut):
        x, y = pay + sut * (hucre + pay), ust + sat * (hucre + bant + pay)
        if s['durum'] == 'tamam':
            p = K / f"{s['ad']}.png"
            if not p.is_file() or sha_dosya(p) != s['png_sha256']:
                raise Dur('pafta_sha', f"{s['ad']}: son gorsel dosyasi OZET'teki sha256 ile ayni degil")
            a = np.asarray(Image.open(p).convert('RGB'))
            h_, w_ = a.shape[:2]
            o_ = hucre / float(max(h_, w_))
            kucuk = cv2.resize(a, (max(1, int(round(w_ * o_))), max(1, int(round(h_ * o_)))), interpolation=cv2.INTER_AREA)
            hucreler[s['no']] = kucuk
            sayfa.paste(Image.fromarray(kucuk), (x + (hucre - kucuk.shape[1]) // 2, y + (hucre - kucuk.shape[0]) // 2))
        else:
            d.rectangle([x, y, x + hucre - 1, y + hucre - 1], fill=(246, 246, 246), outline=(0, 0, 0), width=1)   # tek renk, vurgu yok
            fd = _font(22)
            for i, t in enumerate(['DUR'] + _kir(dur_kodu(s), fd, hucre - 24)):
                d.text((x + 12, y + 12 + i * (fd.size + 6)), t, fill=(0, 0, 0), font=fd)
        for i, t in enumerate(etk[s['no']]):
            d.text((x + 2, y + hucre + 5 + i * (f.size + 3)), t, fill=(0, 0, 0), font=f)
    for j, s in enumerate(tekil):
        koy(s, 0, j)
    for s in izg:
        koy(s, (1 if tekil else 0) + s['satir'], s['sutun'])
    if len(tekil) + len(izg) != len(sec):
        raise Dur('pafta_hucre', 'hucre sayisi secenek sayisiyla ayni degil')
    out = Path(out)
    for q in PAFTA_KALITE:
        sayfa.save(out, quality=q, subsampling=0)
        if out.stat().st_size <= PAFTA_AZAMI_BAYT:
            return dict(dosya=out.name, boyut=[Wp, Hp], kalite=q, bayt=out.stat().st_size, hucre=len(sec), hucre_px=hucre), hucreler
    out.unlink()
    raise Dur('pafta_boyut', f'pafta kalite {PAFTA_KALITE[-1]} ile de {PAFTA_AZAMI_BAYT} bayti asiyor')


# ---------------------------------------------------------------- komutlar
def _ozet_secenek(r):
    return {k_: r.get(k_) for k_ in ('no', 'ad', 'tur', 'durum', 'kod', 'neden', 'ayar', 'degisen', 'geri_donus', 'satir', 'sutun', 'png_sha256',
                                     'tuval', 'k', 'altin_sirasi', 'olcum_ozet', 'sure')}


def kos(a):
    urun = urun_dogrula(_json_oku(Path(a.urun).read_text(encoding='utf-8'), 'urun'))
    if urun['sekil'] != 'yuvarlak':
        raise Dur('girdi_sekil', 'dilim 1: gorsel uretimi yalniz yuvarlak sekil', girdi=True)
    baglan(a.kaynak)                                                          # ayar dogrulamasi AT fonksiyonlarini cagirir
    sec = istek_kur(_json_oku(Path(a.istek).read_text(encoding='utf-8'), 'istek'))
    sure_olcum = None if a.olcum else (_json_oku(Path(a.sure).read_text(encoding='utf-8'), 'sure') if a.sure else None)
    kimlik = kosu_kimligi(a.urun)
    butce = butce_kontrol(len(sec), sure_olcum, a.butce, a.olcum, kimlik)     # URETIMDEN ONCE
    O = Path(a.cikti)
    O.mkdir(parents=True, exist_ok=True)
    t_kos = time.time()
    ort = Ortam(a.kaynak, a.katman, urun)
    on_kontrol(ort, sec)
    (O / 'AYAR.json').write_text(json.dumps([dict(no=s['no'], ad=s['ad'], ayar=s['ayar']) for s in sec], indent=1, ensure_ascii=False))
    sonuc = []
    for i, s in enumerate(sec, 1):
        r = secenek_uret(ort, s, O)
        sonuc.append(r)
        gecen = time.time() - t_kos
        kalan = gecen / i * (len(sec) - i)
        print(f'ETA {i}/{len(sec)} | gecen {gecen:.0f} sn | kalan {kalan:.0f} sn | %{100.0 * i / len(sec):.0f}', flush=True)
    tum_geri = sorted({g_ for r in sonuc for g_ in r['geri_donus']})
    ozet = dict(arac='tasarim_deneme dilim 1b', not_=SINIR_NOTU, taban=sec[0]['ayar']['taban'], taban_etiket=B1_ETIKET, geri_donus=tum_geri,
                urun=urun, urun_sha256=sha_dosya(a.urun), mm_px=mm_px(urun), cift=CIFT,
                sembol_katmani=dict(sha256=ort.s_olc['sha256'], tur='deneme' if ort.katman.name.startswith('DENEME_') else 'gercek',
                                    olcum={k_: ort.s_olc.get(k_) for k_ in ('boyut', 'kutu_alfa_05', 'kutu_alfa_002', 'merkez_05',
                                                                            'cevre_yaricap_05', 'en_boy_05', 'alfa_05_piksel', 'yan_json')}),
                ay_sha=AY_SHA, motor_sha=MOTOR_SHA, ornament_sha=ORNAMENT_SHA, kaynak_sha256=ort.kaynak_sha, kod_sha256=kimlik['kod_sha256'],
                paketler=ort.paketler, butce=butce, secenek=[_ozet_secenek(r) for r in sonuc],
                musteri_verisi='YOK: girdi yalniz ornek isim ve ornek metin olabilir (W:8-9)')
    try:
        pafta, _ = pafta_yaz(ozet, O, O / f"PAFTA_{urun['ad']}_01.jpg")
    except Exception as e:                                                    # noqa: BLE001
        if not _dur_mu(e) or e.kod != 'pafta_boyut':
            raise
        pafta = dict(dosya=None, durum='DUR', kod=e.kod, neden=e.neden, bayt=None, hucre=len(sonuc))   # 3 MB asildi: OZET / SURE / OLCUM_TUMU yine yazilir
        log(f'pafta YAZILMADI: {e.kod}: {e.neden}')
    ozet['pafta'] = pafta
    toplam = round(time.time() - t_kos, 1)
    tam = [r['sure']['toplam_sn'] for r in sonuc if r['durum'] == 'tamam']
    sure = dict(mod='olcum' if a.olcum else 'asil', kimlik=kimlik, kurulum_sn=ort.kurulum_sn, toplam_sn=toplam, butce=butce,
                secenek=[dict(no=r['no'], ad=r['ad'], durum=r['durum'], kod=r['kod'], tur='tam cizim', **r['sure']) for r in sonuc],
                cizimi_biten_en_cok_sn=max([r['sure']['toplam_sn'] for r in sonuc if cizimi_biten(r)], default=None),
                secenek_sn=dict(en_az=min(tam) if tam else None, ortanca=float(np.median(tam)) if tam else None, en_cok=max(tam) if tam else None),
                asama=dict(asama='yerlesim denemesi', baslangic=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_kos)),
                           bitis=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), serdar_bekleme=None, deneme_sayisi=None, inceleme_turu=None,
                           not_='insan alanlarini arac olcemez; Merkez girer'))
    ozet['sure_toplam_sn'] = toplam
    sure_dogrula(sure)
    (O / 'OZET.json').write_text(json.dumps(ozet, indent=1, ensure_ascii=False, default=float))
    (O / 'SURE.json').write_text(json.dumps(sure, indent=1, ensure_ascii=False, default=float))
    tumu = {}
    for r in sonuc:
        tumu[r['ad']] = json.loads((O / f"{r['ad']}_OLCUM.json").read_text(encoding='utf-8'))
    (O / 'OLCUM_TUMU.json').write_text(json.dumps(dict(not_=SINIR_NOTU, urun=urun['ad'], secenek=tumu), indent=1, ensure_ascii=False))
    dur = [r['ad'] for r in sonuc if r['durum'] != 'tamam']
    log(f"kosu bitti: {len(sonuc)} secenek, {len(sonuc) - len(dur)} tamam, {len(dur)} DUR | toplam {toplam} sn | pafta {pafta['bayt']} bayt")
    return 1 if dur or pafta['dosya'] is None else 0


def uret(a):
    """Tek secenegi OZET'teki TAM ayardan ve urun girdisinden yeniden uretir (ayri surec; plan 5.1 kural kontrolu, 2. halka)."""
    oz = _json_oku(Path(a.ozet).read_text(encoding='utf-8'), 'ozet')
    kayit = [s for s in oz.get('secenek', []) if s.get('no') == a.secenek]
    if len(kayit) != 1:
        raise Dur('girdi_secenek', 'OZET icinde bu numarada secenek yok', girdi=True)
    s0 = kayit[0]
    urun = urun_dogrula(oz['urun'])
    baglan(a.kaynak)
    AY, geri = ayar_dogrula({k_: v for k_, v in s0['ayar'].items() if v is not None})
    if AY != s0['ayar']:
        raise Dur('girdi_ayar', "OZET'teki ayar yeniden dogrulaninca ayni degil", girdi=True)
    ort = Ortam(a.kaynak, a.katman, urun)
    if ort.s_olc['sha256'] != oz['sembol_katmani']['sha256']:
        raise Dur('katman_sha', "sembol katmani OZET'teki katmanla ayni degil")
    sec = dict(no=s0['no'], ad=s0['ad'], tur=s0['tur'], ayar=AY, geri_donus=s0['geri_donus'], degisen=s0['degisen'], satir=s0.get('satir'),
               sutun=s0.get('sutun'))
    on_kontrol(ort, [sec])
    r = secenek_uret(ort, sec, a.cikti)
    ayni = r['png_sha256'] == s0['png_sha256'] and r['durum'] == s0['durum']
    (Path(a.cikti) / f"{s0['ad']}_YENIDEN.json").write_text(json.dumps(dict(secenek=s0['no'], ad=s0['ad'], durum=r['durum'], png_sha256=r['png_sha256'],
                                                                             ozet_sha256=s0['png_sha256'], ayni=ayni), indent=1))
    log(f"yeniden uretim {s0['ad']}: {'AYNI' if ayni else 'FARKLI'} | {r['png_sha256']} | ozet {s0['png_sha256']}")
    return 0 if ayni else 1


def sembol(a):
    """Yerel deneme sembolu: AT `deneme` komutu AYNEN (AT:1679-1697). Dosya adi DENEME_ ile baslar; yuklenmez, depoya girmez."""
    baglan(a.kaynak)
    ortam_kapisi()
    return AT.main(['deneme', '--cift', CIFT, '--motor', str(Path(a.kaynak) / MOTOR_YOL), '--cikti', str(a.cikti)])


def main(argv=None):
    ap = argparse.ArgumentParser(description='tasarim deneme araci (dilim 1)')
    sp = ap.add_subparsers(dest='komut', required=True)
    p = sp.add_parser('sembol'); p.add_argument('--kaynak', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('kos')
    for k_ in ('kaynak', 'urun', 'istek', 'katman', 'cikti'):
        p.add_argument('--' + k_, required=True)
    p.add_argument('--olcum', action='store_true'); p.add_argument('--sure')
    p.add_argument('--butce', type=int, default=BUTCE_SN)                     # yalniz KUCULTULEBILIR (butce_kontrol: > 900 girdi hatasi)
    p = sp.add_parser('uret')
    for k_ in ('kaynak', 'ozet', 'katman', 'cikti'):
        p.add_argument('--' + k_, required=True)
    p.add_argument('--secenek', type=int, required=True)
    a = ap.parse_args(argv)
    try:
        return {'sembol': sembol, 'kos': kos, 'uret': uret}[a.komut](a)
    except Exception as e:                                                    # noqa: BLE001
        if not _dur_mu(e):
            raise
        kod = 3 if e.girdi else 4
        print(f'DUR {e.kod}: {e.neden} (cikis {kod})', flush=True)
        try:
            O = Path(a.cikti)
            O.mkdir(parents=True, exist_ok=True)
            (O / 'DUR.json').write_text(json.dumps(dict(kod=e.kod, neden=e.neden, girdi_hatasi=bool(e.girdi), cikis=kod), indent=1, ensure_ascii=False))
        except Exception:                                                     # noqa: BLE001
            pass
        return kod


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import tasarim_deneme as _TD                                              # TEK modul nesnesi: betik `__main__` olarak ikinci kopya tutmaz
    try:
        sys.exit(_TD.main())
    except Exception:                                                          # noqa: BLE001  (cikis 2 = cokus, tam traceback)
        traceback.print_exc()
        print('COKUS: tasarim_deneme beklenmeyen hata (cikis 2)', flush=True)
        sys.exit(2)
