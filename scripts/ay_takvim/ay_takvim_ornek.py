#!/usr/bin/env python3
"""AY TAKVIMI ORNEK (Serdar 10 Kas 2026, 2. adim; plan: dal ay-takvim-plan docs/ay_takvim/PLAN_AY_TAKVIM.md, yol S2 / 2a).
2027 cift ay takvimi, 4 yerlesim (halkalar, spiral, girdap, rozet), 18x24 in, 300 dpi (5400x7200). Etsy / Printful / musteri YOK.
Cikti yalniz --cikti klasorune (is akisi Drive'a tasir); depoya gorsel yazilmaz.

ALTIN (ornament yazi yolu; kaynak dal ornament-printful-katalog c950151627 scripts/printful/ornament_motor.py, motor siparis-gpt 6da763a):
  motor dosyalari DEGISMEZ, --motor klasorunden ICE ALINIR (golge_motor, vektor_yuzey.yon_alani, alfa_temizle.temizle, KILIT_GPTGIRDI.json).
  ornament_motor.py'nin main() icindeki ic ice fonksiyonlar ice alinamadigi icin TASINDI; her biri icin test_ay_takvim.py kaynakla
  esdegerlik testi kosar (kaynak satirlari sabit sha'li dosyadan cikarilip ayni girdiyle calistirilir):
    metin_alfa        <- ornament_ornek.py metin_alfa (:85-106)            sekil (son alfa), 4 kat ust ornekleme
    metin_alfa_k      <- ornament_motor.py metin_alfa10 (:389-407)        renk cizimi; K10 = 10 yerine oge basina k (asagida)
    Motor.golgele_oge <- ornament_motor.py golgele_oge (:160-203)
    Motor.harita_kur  <- ornament_motor.py :148-151, 205-231             poster ana alfasi -> renk haritasi + goz dagilimi
    Motor.oge_katman  <- ornament_motor.py :455-486                       esit 'goz' x2, harita, kenar 0.5, gren, dogrusal kucultme
    renk_uyum         <- ornament_motor.py :514-531                       Lab ortanca kaydirmasi (hedef: SEMBOL katmani), < 200 piksel DUR
    yari_kal, boya    <- ornament_motor.py :548-551, 573-597 + ornament_altin.py DIS_GOLGE / IC_GOLGE (:34-35)
    zemin_*           <- motor uret_tam.py :18-40 (radyal profil), :111-135 (yildiz 'refkopya'), :371-392 (sRGB + titresim + gren)
  ORNAMENT'TEN BILEREK FARKLI (Serdar 10 Kas kararlari; OZET'e yazilir):
    k        cizim katsayisi 10 degil; oge basina buyuk harf x k ~ 298 px (poster buyuk harfi) olacak tam sayi (plan bolum 3).
    sembol   <CIFT>_ana.png yalniz es oranli kucultulur (on carpimli INTER_AREA); ic golge / dusus / onarim UYGULANMAZ (karar 3).
    dusus    ornament kurali "kucuk ogelerde dusus = sembolun ortanca carpani"; sembol degismedigi icin carpan 1,0.
    kontrast esigin altindaysa kod parlaklik ARTIRMAZ (karar 9); karar kapi betiginde (ay_takvim_kapi.py), DUR.
    dis golge ornament notr dis golgesi (1,5 / 1,2 / 0,45) tum altin ogelerin (sembol dahil) ALTINA duser: zemini koyulastirir, sembolun
             kendi pikselleri degismez (tam alfada son dosya = katman rengi); yari saydam kenar pikselleri golgeli zeminle karisir.
    yildiz   motorun 'refkopya' yildiz yolu aynen; ek olarak altin ogelere, disklere ve rakamlara degen yildiz yamasi ATLANIR (motorun
             kendi kurali: uret_tam.py :53-56, 66 yildizlar "oge bolgeleri disi", 61 px genisletme; burada tuvale oranli). Sayisi OZET'te.
  Altin OLMAYAN: ay diskleri, isaret halkasi, yorunge cizgisi, gun rakami (duz renk).
  SEMBOL GRUBU (Serdar 11 Kas; halkalar, girdap, rozet): ana sembol + posterdeki ince altin HALKA + ciftin iki KUCUK BURC sembolu
    (1. burc sol altta, 2. burc sag altta). Grup posterdeki goreli duzenle TEK parca kurulur (motor cember.json, yerlesim78.json,
    alfa_ogeler.npz 'cember', girdi/KUCUK_1-2.png + olustur_alfa_sablon.py kutulari / KUCUK_Y) ve TEK oranla kucultulur; buyutme yok.
    Hal 'grup': grubun en kucuk cevreleyen dairesi = sembol alani, daire merkezi takvim merkezinde. Hal 'halka': halkanin geometrik
    merkezi takvim merkezinde, en uzak grup pikseli = sembol alani yaricapi. Halka ve kucuk semboller AYNI altin yolundan gecer
    (Motor.oge_katman: 'cember' / 'kucuk1' / 'kucuk2'; renk_uyum hedefi ana sembol). alfa_ogeler.npz'nin diger ogeleri (SCORPIO_VIRGO)
    ve eski *_symbol_gold.png dosyalari KULLANILMAZ. Spiral eski kuralla (SEMBOL_ORAN, grup yok) kalir; ornek setinde yok.

Kullanim:
  ay_takvim_ornek.py sembol --katman K.png --cikti D                       katman olcumu + bicim kapisi (SEMBOL_OLCUM.json)
  ay_takvim_ornek.py uret --cift CANCER_LIBRA --isim1 A --isim2 B --yerlesim halkalar [--satir "..."]x0-3
                          --katman K.png --motor MD --cikti D --ad ORNEK_1A_halkalar [--onbellek DIR] [--grup-merkez grup|halka]
                          [--ayar '{"kucuk_u": 0.6, ...}'] [--mod ornek|deneme]
  ay_takvim_ornek.py ayar-dogrula --env AY_TAKVIM_AYAR --cikti D        mod deneme girdisi (JSON liste, ortam degiskeninden) -> D/AYAR.json, AYAR_N.txt, AYAR_AD.txt
  ay_takvim_ornek.py uret --cift CANCER_LIBRA --katman K.png --motor MD --cikti D --mod deneme --ayar-dosya D/AYAR.json --sira 1     (ad koddan: DENEME_1_<yerlesim>)
  AYAR (Serdar 11 Kas "A"): tasarim denemeleri kod degismeden. Anahtarlar AYAR_ANAHTAR, araliklar AYAR_ARALIK, varsayilan ayar_varsayilan() (= 2. ornek
    gorevi; ayar verilmezse cikti ayni). Etkin ayarin TAMAMI META.json 'ayar' alanina yazilir; kapi betigi ayara bagli degerleri oradan okur.
  MOD deneme: 'bosluk', 'metin_genis', 'isim_kucuk', 'dikey_sigmadi', 'tasma' DUR vermez, META 'uretim_kontrol'e FAIL yazilir ve gorsel yine cikar;
    disk katsayisi kendiliginden dusmez; tuval disina tasan ogeyi tuval siniri keser (FAIL yazilir). SERT kalanlar: girdi, veri, ortam, motor, sembol bicimi,
    buyutme yok (grup_olcek), renk uyumu icin 200 cekirdek piksel. Cizim yolu mod ornek ile AYNI (tam boy; onizleme tam boyun kucultulmusu).
    Sure (yerel olcum 11 Kas, 4 cekirdek): deneme basina uretim 46 - 52 sn (zemin 5 - 6, altin 18 - 22, PNG + DUMP kaydi 20 - 21) + kapi 8 - 10 sn;
    kurulum (renk haritasi onbelleksiz ilk ornek) +15 sn. Ust sinir DENEME_AZAMI = 6: floor((50 dk - kurulum) / deneme suresi) > 6 (60 dk zaman asimi).
  ay_takvim_ornek.py deneme --cift CANCER_LIBRA --motor MD --cikti D       YALNIZ yerel deneme sembolu (DENEME_ adli; yuklenmez)
Cikis: 0 tamam, 3 girdi hatasi (karakter, satir, sembol bicimi), 4 DUR (uretim kapisi), 2 cokus."""
import argparse
import datetime
import hashlib
import json
import math
import os
import pickle
import re
import string
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, features

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()

# ---------------------------------------------------------------- sabitler (Serdar 10 Kas; Merkez baslangic degerleri)
REF_W, REF_H, S = 1800, 2400, 3                       # geometri 1800x2400 referans tuvalde; 5400x7200 icin x3
W, H = REF_W * S, REF_H * S
DPI = 300
YIL = 2027
AYLAR = ('JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER')   # Serdar 11 Kas: kisaltmasiz
BASLIK = 'MOON PHASES 2027'
RENK_KOYU, RENK_ACIK, RENK_KENAR = (40, 50, 100), (240, 226, 190), (86, 98, 150)
RENK_YORUNGE, RENK_RAKAM = (88, 92, 136), (176, 178, 200)
CAP_AY, CAP_ISIM, CAP_BASLIK, T_METIN = 53, 150, 75, 90      # buyuk harf yuksekligi (px, 5400 tuval); metin: "T" yuksekligi
CAP_RAKAM = 40                                         # gun rakami (1, 31) boyu: Merkez metninde yok, bu betikte secildi (altin degil)
SATIR_ARALIK = 1.6                                     # kisisel metin taban araligi = 1,6 x T
POSTER_CAP = 298                                       # motor olustur_alfa_sablon.py:23 CAP_H (poster isim buyuk harfi, px)
GEN_ORAN = 0.86                                        # isim satiri / metin satiri en fazla sayfa genisliginin %86'si
BOSLUK_YAZI_DISK, BOSLUK_DISK_DISK, BOSLUK_SEMBOL_DISK, BOSLUK_KENAR = 12, 6, 150, 180   # kapi 6 (px, 5400 tuval)
G_ISIM_BASLIK, G_BASLIK_CEMBER, G_CEMBER_METIN = 105, 150, 165   # dikey bosluklar: Merkez metninde yok, bu betikte secildi
SEMBOL_ORAN = 0.78                                     # sembolu cevreleyen daire = 0,78 x sembol alani yaricapi
ISARET_DIS, ISARET_KALIN = 5, 2                        # isaret halkasi: dis kenar = disk r + 5, kalinlik 2 (referans px)
KENAR_CIZGI = 2                                        # disk ince kenar cizgisi (px)
YORUNGE_KALIN = 3                                      # halkalar yorunge cizgisi (px)
YERLESIM = dict(halkalar=dict(katsayi=0.36, sembol_alan=205, grup=True), spiral=dict(katsayi=0.36, sembol_alan=205, grup=False),
                girdap=dict(katsayi=0.36, sembol_alan=205, grup=True), rozet=dict(katsayi=0.34, sembol_alan=320, grup=True))
GRUP_MERKEZ = ('grup', 'halka')                        # hal A: grup ortali; hal B: halka ortali (Serdar 11 Kas "C")
GIRDAP_AD_UZAK, GIRDAP_AD_UZAK_UST = 58, 300           # ay adi son gun diskinden uzakligi (referans px): 58'den baslar, 1 adimla artar (Serdar 11 Kas "A")
# kucuk burc sembolleri: motor olustur_alfa_sablon.py :17-22 kutulari (girdi/KUCUK_1.png, KUCUK_2.png) ve :23 KUCUK_Y (poster pikseli)
KUCUK = {'AQUARIUS': ('KUCUK_1', [1095, 219, 2010, 600]), 'ARIES': ('KUCUK_1', [2257, 102, 2917, 717]),
         'CANCER': ('KUCUK_1', [175, 933, 859, 1527]), 'CAPRICORN': ('KUCUK_1', [1200, 880, 1905, 1580]),
         'GEMINI': ('KUCUK_1', [2285, 923, 2889, 1537]), 'LEO': ('KUCUK_1', [254, 1743, 781, 2357]),
         'LIBRA': ('KUCUK_2', [1001, 94, 1822, 709]), 'PISCES': ('KUCUK_2', [2023, 95, 2682, 708]),
         'SAGITTARIUS': ('KUCUK_2', [217, 875, 723, 1533]), 'SCORPIO': ('KUCUK_2', [1038, 897, 1784, 1512]),
         'TAURUS': ('KUCUK_2', [2045, 898, 2659, 1510]), 'VIRGO': ('KUCUK_2', [130, 1666, 811, 2349])}
KUCUK_Y = 7078.5
# kucuk sembollerin yatay merkezi (halka merkezine gore, R biriminde): posterde altindaki ismin merkezi. Takvimde isim yok; ciftin ONAYLI
# posterinin yeri sabit alinir (CANCER_LIBRA: EMILY / JAMES, isim_tagline_78.csv no 28; sablon formulunden; test formulle karsilastirir).
KUCUK_U = {'CANCER_LIBRA': (-0.491, 0.490)}
GRUP_ALFA_ESIK = 0.02                                  # grubun siniri: alfa > 0,02
# AYAR (Serdar 11 Kas "A": tasarim denemeleri kod degismeden, yalniz ayarla). Varsayilan = 2. ornek gorevinin degerleri (ayar verilmezse
# cikti ayni). Araliklar Merkez baslangic degeridir (yalniz yanlis girisi yakalar; tasarim karari degil). AYAR OLAMAZ: sembolun, halkanin ve
# kucuk sembollerin SEKLI (yalniz es oranli olcek), altin yolu, zemin, fontlar. Cift bu asamada sabit (CANCER_LIBRA).
AYAR_YERLESIM = ('halkalar', 'girdap', 'rozet')
AYAR_ANAHTAR = ('yerlesim', 'grup_merkez', 'grup_oran', 'sembol_alan', 'kucuk_u', 'kucuk_v', 'kucuk_oran', 'halka_kalinlik', 'ay_adi_cap', 'girdap_ad_uzaklik',
                'isim_cap', 'baslik_cap', 'metin_cap', 'disk_katsayi', 'isim1', 'isim2', 'satirlar')
AYAR_ARALIK = dict(grup_oran=(0.60, 1.30), sembol_alan=(150, 400), kucuk_u=(0.30, 0.90), kucuk_v=(0.60, 1.30), kucuk_oran=(0.60, 1.80),
                   halka_kalinlik=(1.00, 4.00),                         # Serdar 11 Kas "sadece halkayi, orantili olarak kalinlastiralim": cizgi kalinligi carpani
                   ay_adi_cap=(30, 90), girdap_ad_uzaklik=(58, 200), disk_katsayi=(0.20, 0.45),
                   isim_cap=(0.5 * 150, 1.6 * 150), baslik_cap=(0.5 * 75, 1.6 * 75), metin_cap=(0.5 * 90, 1.6 * 90))
AYAR_SERBEST = dict(kucuk_u='poster', kucuk_v='poster', girdap_ad_uzaklik='oto')   # sayi yerine verilebilen tek sozcuk (varsayilan)
AYAR_UZUNLUK, DENEME_AZAMI = 4000, 6                   # mod deneme: ayar metni en cok 4000 karakter; kosu basina en cok 6 deneme (sure olcumu: baslik notu)
MODLAR = ('ornek', 'deneme')
KATSAYI_ADIM, KATSAYI_ALT = 0.01, 0.20
MOTOR_DOSYA = ('KILIT_GPTGIRDI.json', 'golge_motor.py', 'vektor_yuzey.py', 'alfa_temizle.py', 'kure/k4.npy', 'palet/chatgpt_altin.png',
               'yerlesim78.json', 'cember.json', 'zemin_profil.json', 'ref/ref.png', 'font/Cinzel.ttf', 'font/EBGaramond-Italic.ttf',
               'alfa_ogeler.npz', 'girdi/KUCUK_1.png', 'girdi/KUCUK_2.png')
# motor uret_tam.py:10 (6da763a) varsayilanlari; KILIT AYAR ustune yazilir (ornament_motor.py:57-60 ile ayni)
P_VARSAYILAN = dict(pah=0.6, k=0.8, karisim=0.0, g=0.5, gs=60, golge_sigma=12, golge_dx=6, golge_dy=10, golge_opak=0.55, m1=0.0, m2=0.0, poz=1.0,
                    pah_px=0.0, kubbe=0.0, kure='studio2', mot_yer='Y', esit='goz', temas=0.0, zemin_daire=0, sarma=0.0, arka_isik=0.0, renk_ayar=0.0,
                    kararma=0.0, yansima=0.0, isima=0.0, isima_sigma=30.0, gren=0.0, kenar_yum=0.0, egim_max=0.0, pah_oran_max=0.0, ton=0.0, yildiz='t5',
                    parilti=0.0, parilti_esik=2.3, isik_leke=0.0, mot_poz=0, mot_s2=5.0, harita='sira')
QS = [2, 5, 25, 50, 75, 95, 98]
DIS_GOLGE = dict(kayma=1.5, sigma=1.2, opak=0.45)      # ornament_altin.py:34 (notr dis golge)
IC_GOLGE = dict(kayma=1.0, sigma=0.6, guc=0.35)        # ornament_altin.py:35; genislik x min(1, D_oge / D_ana) (ornament_motor.py:557-561)
UYUM_MIN_PIKSEL = 200                                  # ornament_motor.py:520-524
ISIM_DESEN = re.compile(r"[A-Za-z'\-]+", re.ASCII)     # ornament siparis_girdi.py:29
HARF = re.compile(r'[A-Za-z]', re.ASCII)
METIN_IZINLI = frozenset(string.ascii_letters + string.digits + " .,'-!?&")   # Serdar 10 Kas karar 7
METIN_SATIR_AZAMI, METIN_KARAKTER_AZAMI = 3, 35


class Dur(Exception):
    """girdi=True: girdi hatasi (cikis 3; gorsel uretilmez). girdi=False: uretim kapisi DUR (cikis 4)."""

    def __init__(self, kod, neden, girdi=False):
        super().__init__(f'{kod}: {neden}')
        self.kod, self.neden, self.girdi = kod, neden, girdi


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def bildir(baslik, metin):
    """Actions annotation (is logu okunamadiginda da gorunur) + duz satir."""
    print(f'::notice title={baslik}::{metin}', flush=True)


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


# ---------------------------------------------------------------- girdi kapilari
def isim_dogrula(ham, alan):
    """ornament siparis_girdi.isim_bicimle (:41-55) kurali: yalniz [A-Za-z'-], en az 1 harf, kenarda / cift isaret yok; sonra buyuk harf."""
    if not isinstance(ham, str) or not ham.strip():
        raise Dur('girdi_isim', f'{alan} bos', girdi=True)
    s = ham.strip()
    if not ISIM_DESEN.fullmatch(s):
        raise Dur('girdi_isim', f'{alan} izinsiz karakter', girdi=True)
    if not HARF.search(s):
        raise Dur('girdi_isim', f'{alan} harf yok', girdi=True)
    if s[0] in "'-" or s[-1] in "'-" or '--' in s or "''" in s:
        raise Dur('girdi_isim', f'{alan} kenar / cift isaret', girdi=True)
    u = s.upper()
    if not ISIM_DESEN.fullmatch(u) or len(u) != len(s):
        raise Dur('girdi_isim', f'{alan} izinsiz karakter', girdi=True)
    return u


def metin_dogrula(satirlar):
    """0-3 satir; satir <= 35 karakter (bosluk dahil); izinli: A-Z a-z 0-9 bosluk . , ' - ! ? &. Satirlari girdi verir (kod bolmez)."""
    satirlar = list(satirlar or [])
    if len(satirlar) > METIN_SATIR_AZAMI:
        raise Dur('girdi_metin', f'{len(satirlar)} satir > {METIN_SATIR_AZAMI}', girdi=True)
    for i, s in enumerate(satirlar, 1):
        if not isinstance(s, str) or not s or s != s.strip():
            raise Dur('girdi_metin', f'satir {i} bos ya da kenar boslugu', girdi=True)
        if len(s) > METIN_KARAKTER_AZAMI:
            raise Dur('girdi_metin', f'satir {i}: {len(s)} karakter > {METIN_KARAKTER_AZAMI}', girdi=True)
        kotu = sorted({c for c in s if c not in METIN_IZINLI})
        if kotu:
            raise Dur('girdi_metin', f'satir {i}: izinsiz karakter (kod noktalari {[hex(ord(c)) for c in kotu]})', girdi=True)
        if not any(c.isalnum() for c in s):
            raise Dur('girdi_metin', f'satir {i}: harf ya da rakam yok', girdi=True)
    return satirlar


def cift_dogrula(cift):
    c = (cift or '').strip().upper()
    p = c.split('_')
    if len(p) != 2 or not all(q.isalpha() for q in p) or '_'.join(sorted(p)) != c:
        raise Dur('girdi_cift', 'cift anahtari alfabetik BURC1_BURC2 olmali', girdi=True)
    return c


def ayar_varsayilan(yerlesim):
    """Etkin AYAR'in varsayilani (2. ornek gorevinin degerleri). 'poster': kucuk semboller posterdeki yerinde; 'oto': girdap ad uzakligi aramasi."""
    Yv = YERLESIM[yerlesim]
    return dict(yerlesim=yerlesim, grup_merkez='grup', grup_oran=1.0, sembol_alan=Yv['sembol_alan'], kucuk_u='poster', kucuk_v='poster', kucuk_oran=1.0,
                halka_kalinlik=1.0,
                ay_adi_cap=CAP_AY, girdap_ad_uzaklik='oto', isim_cap=CAP_ISIM, baslik_cap=CAP_BASLIK, metin_cap=T_METIN, disk_katsayi=Yv['katsayi'],
                isim1='EMILY', isim2='JAMES', satirlar=[])


def ayar_dogrula(ham, spiral=False):
    """AYAR sozlugu: bilinmeyen anahtar, aralik disi deger, yanlis tur = girdi hatasi (DUR, uretim yok). Eksik anahtar = varsayilan.
    Hata mesajinda HAM girdi YOK (log komutu enjeksiyonu): yalniz hata turu ve anahtarin sirasi (#1'den). Doner TAM ayar sozlugu."""
    def hata(i, tur):
        raise Dur('girdi_ayar', f'{tur} #{i}', girdi=True)
    if not isinstance(ham, dict):
        raise Dur('girdi_ayar', 'ayar sozluk degil', girdi=True)
    sira = {}
    for i, k_ in enumerate(ham, 1):
        if not isinstance(k_, str) or k_ not in AYAR_ANAHTAR:
            hata(i, 'bilinmeyen anahtar')
        sira[k_] = i
    y = ham.get('yerlesim', 'halkalar')
    if not isinstance(y, str):
        hata(sira['yerlesim'], 'yanlis tur')
    if y not in AYAR_YERLESIM + (('spiral',) if spiral else ()):
        hata(sira['yerlesim'], 'aralik disi')
    AY = ayar_varsayilan(y)
    if 'grup_merkez' in ham:
        if not isinstance(ham['grup_merkez'], str):
            hata(sira['grup_merkez'], 'yanlis tur')
        if ham['grup_merkez'] not in GRUP_MERKEZ:
            hata(sira['grup_merkez'], 'aralik disi')
        AY['grup_merkez'] = ham['grup_merkez']
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
        AY[k_] = isim_dogrula(AY[k_], k_)
    if 'satirlar' in ham:
        if not isinstance(ham['satirlar'], list) or not all(isinstance(v, str) for v in ham['satirlar']):
            hata(sira['satirlar'], 'yanlis tur')
        AY['satirlar'] = list(ham['satirlar'])
    AY['satirlar'] = metin_dogrula(AY['satirlar'])
    return AY


def ayar_listesi(metin):
    """mod deneme girdisi: JSON metni = 1 - DENEME_AZAMI denemelik liste, her oge AYAR sozlugu. Doner TAM ayar sozlukleri listesi.
    Hata mesaji yalniz deneme sirasi + hata turu + anahtar sirasi verir (ham girdi basilmaz)."""
    if not isinstance(metin, str) or not metin.strip():
        raise Dur('girdi_ayar', 'ayar bos', girdi=True)
    if len(metin) > AYAR_UZUNLUK:
        raise Dur('girdi_ayar', f'ayar {len(metin)} karakter > {AYAR_UZUNLUK}', girdi=True)
    def sabit_yok(_):
        raise ValueError('sabit')

    def tekil(ciftler):                                                       # yinelenen anahtar = bozuk girdi (son deger sessizce gecmez)
        d = dict(ciftler)
        if len(d) != len(ciftler):
            raise ValueError('yinelenen anahtar')
        return d
    try:
        L = json.loads(metin, parse_constant=sabit_yok, object_pairs_hook=tekil)
    except (ValueError, RecursionError):
        raise Dur('girdi_ayar', 'bozuk JSON', girdi=True) from None
    if not isinstance(L, list):
        raise Dur('girdi_ayar', 'ayar liste degil', girdi=True)
    if not 1 <= len(L) <= DENEME_AZAMI:
        raise Dur('girdi_ayar', f'{len(L)} deneme (1 - {DENEME_AZAMI} olmali)', girdi=True)
    out = []
    for i, d in enumerate(L, 1):
        try:
            out.append(ayar_dogrula(d))
        except Dur as e:
            raise Dur(e.kod, f'deneme {i}: {e.neden}', girdi=True) from None
    return out


# ---------------------------------------------------------------- ay verisi (PyEphem 4.2.1)
def ay_verisi(yil=YIL):
    """Her gun 12:00 UTC: oran = Moon.phase / 100; buyuyor = (ay ekliptik boylami - gunes ekliptik boylami) mod 2pi < pi.
    Yeni ay / dolunay: next_new_moon / next_full_moon aninin UTC tarihi. Doner: gun listesi (yil sirasinda)."""
    import ephem

    def anlar(fonk):
        out, t = set(), ephem.Date(f'{yil - 1}/12/1')
        while True:
            t = fonk(t)
            d = t.datetime()
            if d.year > yil:
                return out
            if d.year == yil:
                out.add(d.date())
            t = ephem.Date(t + 1.0)                      # bir gun sonrasindan aramaya devam
    yeni, dolun = anlar(ephem.next_new_moon), anlar(ephem.next_full_moon)
    gunler, d = [], datetime.date(yil, 1, 1)
    while d.year == yil:
        e = ephem.Date(datetime.datetime(d.year, d.month, d.day, 12, 0, 0))
        ay, gunes = ephem.Moon(e), ephem.Sun(e)
        fark = (float(ephem.Ecliptic(ay).lon) - float(ephem.Ecliptic(gunes).lon)) % (2 * math.pi)
        gunler.append(dict(ay=d.month, gun=d.day, oran=float(ay.phase) / 100.0, buyuyor=bool(fark < math.pi),
                           yeni=d in yeni, dolun=d in dolun))
        d += datetime.timedelta(days=1)
    return gunler


def veri_kapisi(gunler, yil=YIL):
    """Kapi 1: 2027 icin 365 gun, 13 yeni ay, 12 dolunay (Merkez USNO karsilastirmasi)."""
    o = dict(gun=len(gunler), yeni=sum(g['yeni'] for g in gunler), dolun=sum(g['dolun'] for g in gunler),
             oran_araligi=[round(min(g['oran'] for g in gunler), 4), round(max(g['oran'] for g in gunler), 4)])
    o['PASS'] = bool(o['gun'] == 365 and o['yeni'] == 13 and o['dolun'] == 12 and yil == 2027)
    return o


# ---------------------------------------------------------------- yerlesim geometrisi (cember merkezine goreli, px = referans x S)
def _kutup(r, derece):
    a = np.radians(derece)
    return r * np.cos(a), r * np.sin(a)                  # goruntu koordinati: y asagi, artan aci = saat yonu; -90 = saat 12


def yerlesim_kur(ad, gunler, katsayi, ad_uzak=GIRDAP_AD_UZAK):
    """Doner dict: disk (n, 3: x, y, r), isaret (n bool), ay_ilk (12: ayin ilk gun indeksi), ay_yeri (12 x (x, y) ya da None: spiral),
    yorunge [(yaricap, ilk aci, son aci)], rakam [(metin, x, y)], tur (spiral tur araligi), bilgi."""
    n = len(gunler)
    disk = np.zeros((n, 3), np.float64)
    isaret = np.array([g['yeni'] or g['dolun'] for g in gunler], bool)
    ay_ilk = [next(i for i, g in enumerate(gunler) if g['ay'] == m) for m in range(1, 13)]
    ay_son = [max(i for i, g in enumerate(gunler) if g['ay'] == m) for m in range(1, 13)]
    out = dict(ad=ad, katsayi=float(katsayi), isaret=isaret, ay_ilk=ay_ilk, yorunge=[], rakam=[], ay_yeri=None, tur=None)
    if ad == 'halkalar':
        adim = (775 - 290) / 11
        R = [775 - i * adim for i in range(12)]
        r_disk = min(adim * katsayi, 290 * math.radians(320) / 30 * 0.40)
        for i, g in enumerate(gunler):
            x, y = _kutup(R[g['ay'] - 1], -90 + 20 + (g['gun'] - 1) * (320 / 30))
            disk[i] = (x, y, r_disk)
        out['yorunge'] = [(R[m] * S, -90 + 20, -90 + 20 + (gunler[ay_son[m]]['gun'] - 1) * (320 / 30)) for m in range(12)]   # (yaricap, ilk gun, son gun acisi)
        out['ay_yeri'] = [(0.0, -r * S) for r in R]
        out['rakam'] = [('1',) + tuple(v * S for v in _kutup(775 + 50, -90 + 20)), ('31',) + tuple(v * S for v in _kutup(775 + 50, -90 + 20 + 320))]
        out['bilgi'] = dict(adim=adim, r_disk_ref=r_disk)
    elif ad == 'spiral':
        tur = (770 - 300) / 6
        th = np.linspace(0, 12 * math.pi, 240001)
        r = 300 + (770 - 300) * th / (12 * math.pi)
        x, y = r * np.cos(th - math.pi / 2), r * np.sin(th - math.pi / 2)
        s = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
        yay = s[-1] / (n - 1)
        hedef = np.arange(n) * yay
        r_disk = katsayi * min(yay, tur)
        disk[:, 0], disk[:, 1], disk[:, 2] = np.interp(hedef, s, x), np.interp(hedef, s, y), r_disk
        out['tur'] = tur * S
        out['bilgi'] = dict(yay=float(yay), tur=tur, r_disk_ref=float(r_disk))
    elif ad == 'girdap':
        r0, r1, sup = 290.0, 735.0, math.radians(150)
        b = math.log(r1 / r0) / sup

        def nokta(m, r):
            return _kutup(r, -90 + (m - 1) * 30 + math.degrees(math.log(r / r0) / b))
        p1, p2 = nokta(1, r0), nokta(1, r0 + (r1 - r0) / 30)
        aralik = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        r_disk = katsayi * aralik
        for i, g in enumerate(gunler):
            x, y = nokta(g['ay'], r0 + (g['gun'] - 1) * (r1 - r0) / 30)
            disk[i] = (x, y, r_disk)
        yer = []
        for m in range(1, 13):                                               # ay adi: kolun dis ucunda, son gun diskinin ad_uzak px otesinde (kol tegeti yonunde)
            rs = r0 + (gunler[ay_son[m - 1]]['gun'] - 1) * (r1 - r0) / 30
            ps, pt = nokta(m, rs), nokta(m, rs + 0.01)
            tx, ty = pt[0] - ps[0], pt[1] - ps[1]
            tn = math.hypot(tx, ty)
            yer.append(((ps[0] + ad_uzak * tx / tn) * S, (ps[1] + ad_uzak * ty / tn) * S))
        out['ay_yeri'] = yer
        out['bilgi'] = dict(b=b, aralik=aralik, r_disk_ref=r_disk, ad_uzak_ref=ad_uzak)
    elif ad == 'rozet':
        Rb, rk = 640.0, 140.0
        r_disk = katsayi * 2 * math.pi * rk / 31
        mer = [_kutup(Rb, -90 + (m - 1) * 30) for m in range(1, 13)]
        for i, g in enumerate(gunler):
            dx, dy = _kutup(rk, -90 + (g['gun'] - 1) * 360 / 31)
            disk[i] = (mer[g['ay'] - 1][0] + dx, mer[g['ay'] - 1][1] + dy, r_disk)
        out['ay_yeri'] = [(x * S, y * S) for x, y in mer]
        out['bilgi'] = dict(r_disk_ref=r_disk)
    else:
        raise Dur('girdi_yerlesim', 'bilinmeyen yerlesim', girdi=True)
    out['disk'] = disk * S
    out['r_tot'] = out['disk'][:, 2] + np.where(isaret, ISARET_DIS * S, 0.0)   # isaret halkasi dahil dis yaricap
    return out


def disk_disk_bosluk(disk, r_tot):
    """komsu diskler (isaret halkasi dahil) arasi en kucuk bosluk (px) ve cift."""
    d = np.hypot(disk[:, None, 0] - disk[None, :, 0], disk[:, None, 1] - disk[None, :, 1]) - r_tot[:, None] - r_tot[None, :]
    d[np.arange(len(disk)), np.arange(len(disk))] = np.inf
    i, j = np.unravel_index(int(np.argmin(d)), d.shape)
    return float(d[i, j]), (int(i), int(j))


def kutu_disk_bosluk(kutu, disk, r_tot):
    """eksenlere paralel kutu (x0, y0, x1, y1) ile daireler arasi en kucuk bosluk (px); negatif = binme."""
    x0, y0, x1, y1 = kutu
    dx = np.maximum(np.maximum(x0 - disk[:, 0], disk[:, 0] - x1), 0)
    dy = np.maximum(np.maximum(y0 - disk[:, 1], disk[:, 1] - y1), 0)
    return float(np.min(np.hypot(dx, dy) - r_tot))


def kutu_kutu_bosluk(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def spiral_ay_yeri(Y, kutular, sembol_r, kenar_x):
    """Spiral: ay adi DUZ; o ayin 1. gun diskinin cevresinde (merkezden en cok 1,5 x tur araligi) yazi ile en yakin disk arasindaki
    boslugu en buyuk yapan nokta. kutular: 12 x (gen, yuk) murekkep kutusu. Onceki ay adlariyla ve sembol dairesiyle de boslukta kalir."""
    disk, r_tot, tur = Y['disk'], Y['r_tot'], Y['tur']
    yer, konan = [], []
    aci = np.radians(np.arange(0, 360, 5))
    for m in range(12):
        c = disk[Y['ay_ilk'][m]]
        gw, gh = kutular[m]
        en = None
        for rad in np.linspace(0, 1.5 * tur, 31):
            for a in (aci if rad > 0 else aci[:1]):
                px, py = c[0] + rad * math.cos(a), c[1] + rad * math.sin(a)
                k = (px - gw / 2, py - gh / 2, px + gw / 2, py + gh / 2)
                if abs(px) + gw / 2 > kenar_x:
                    continue
                b = kutu_disk_bosluk(k, disk, r_tot)
                b = min([b] + [kutu_kutu_bosluk(k, q) for q in konan])
                b = min(b, kutu_disk_bosluk(k, np.zeros((1, 2)), np.array([sembol_r])))
                if en is None or b > en[0] + 1e-9:
                    en = (b, px, py, k)
        yer.append((en[1], en[2])); konan.append(en[3])
    return yer


def girdap_ad_uzakligi(gunler, ay_kutu, katsayi=None):
    """Girdap (Serdar 11 Kas "A"): ay adi kol tegeti yonunde kalir; uzaklik 12 ay icin ORTAK tek deger = 58 referans px'ten baslayip
    1 referans px adimla, 12 adin hepsinde yazi kutusu ile en yakin ay diski (isaret halkasi dahil) arasi >= 12 px olan en kucuk deger.
    YERLESIM katsayisinda aranir (yerlesim_bul'dan ONCE); katsayi bu kosul icin dusurulmez."""
    kat = YERLESIM['girdap']['katsayi'] if katsayi is None else katsayi
    for u in range(GIRDAP_AD_UZAK, GIRDAP_AD_UZAK_UST + 1):
        Y = yerlesim_kur('girdap', gunler, kat, ad_uzak=u)
        yd = [kutu_disk_bosluk((x - gw / 2, y - gh / 2, x + gw / 2, y + gh / 2), Y['disk'], Y['r_tot']) for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
        if min(yd) >= BOSLUK_YAZI_DISK:
            return u, [round(v, 2) for v in yd]
    raise Dur('girdap_ad', f'ay adi uzakligi {GIRDAP_AD_UZAK_UST} referans px\'e kadar yazi - disk >= {BOSLUK_YAZI_DISK} px tutmuyor')


def yerlesim_bul(ad, gunler, ay_kutu, sembol_r, katsayi=None, ad_uzak=GIRDAP_AD_UZAK, dusur=True):
    """Kapi 6 (analitik on kontrol): bosluklar tutmuyorsa YALNIZ o yerlesimin disk katsayisi 0,01 adimla kuculur (dusur=True); baska hicbir sayi
    (yaricap, aci, yazi boyu, sembol orani) degismez. Doner (yerlesim, katsayi, iz). KATSAYI_ALT altina inerse DUR."""
    kat = YERLESIM[ad]['katsayi'] if katsayi is None else katsayi
    iz = []
    while True:
        Y = yerlesim_kur(ad, gunler, kat, ad_uzak)
        dd, _ = disk_disk_bosluk(Y['disk'], Y['r_tot'])
        if Y['ay_yeri'] is None:
            Y['ay_yeri'] = spiral_ay_yeri(Y, ay_kutu, sembol_r, W / 2 - BOSLUK_KENAR)
        yd = [kutu_disk_bosluk((x - gw / 2, y - gh / 2, x + gw / 2, y + gh / 2), Y['disk'], Y['r_tot']) for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
        sd = float(np.min(np.hypot(Y['disk'][:, 0], Y['disk'][:, 1]) - Y['r_tot']) - sembol_r)
        iz.append(dict(katsayi=round(kat, 2), disk_disk=round(dd, 2), yazi_disk=round(min(yd), 2), sembol_disk=round(sd, 2), yazi_disk_ay=[round(v, 2) for v in yd]))
        iz[-1]['PASS'] = bool(dd >= BOSLUK_DISK_DISK and min(yd) >= BOSLUK_YAZI_DISK and sd >= BOSLUK_SEMBOL_DISK)
        if iz[-1]['PASS'] or not dusur:                                       # dusur=False (mod deneme): katsayi kendiliginden dusmez
            return Y, kat, iz
        kat = round(kat - KATSAYI_ADIM, 2)
        if kat < KATSAYI_ALT:
            raise Dur('bosluk', f'disk katsayisi {KATSAYI_ALT} altina indi; bosluk kapisi tutmuyor: {iz[-1]}')


def dikey_yerlesim(cap_isim, cember_ust, cember_alt, n_satir, yuk=H, cap_baslik=CAP_BASLIK, t_metin=T_METIN):
    """Karar 8: isimler + baslik + cember + (varsa) metin blogu sayfada dikey ortalanir. cember_ust / alt: cember merkezine goreli
    (ust negatif). Olcu buyuk harf kutusuyla (taban cizgisi; inisler sayilmaz). Doner taban cizgileri ve cember merkezi y."""
    adim = SATIR_ARALIK * t_metin
    blok = cap_isim + G_ISIM_BASLIK + cap_baslik + G_BASLIK_CEMBER + (cember_alt - cember_ust)
    if n_satir:
        blok += G_CEMBER_METIN + t_metin + (n_satir - 1) * adim
    ust = (yuk - blok) / 2.0
    isim_taban = ust + cap_isim
    baslik_taban = isim_taban + G_ISIM_BASLIK + cap_baslik
    cy = baslik_taban + G_BASLIK_CEMBER - cember_ust
    metin_taban = [cy + cember_alt + G_CEMBER_METIN + t_metin + i * adim for i in range(n_satir)]
    return dict(ust=ust, alt=ust + blok, blok=blok, isim_taban=isim_taban, baslik_taban=baslik_taban, cy=cy, metin_taban=metin_taban)


# ---------------------------------------------------------------- yazi cizimi (ornament yolu)
def _font(font_yolu, pt, wght):
    f = ImageFont.truetype(str(font_yolu), max(4, int(round(pt))))
    if wght:
        f.set_variation_by_axes([wght])
    return f


def _punto(font_yolu, cap_px, wght, ref, ss):
    pt = cap_px * ss * 1.45
    for _ in range(4):
        b = _font(font_yolu, pt, wght).getbbox(ref, anchor='ls')
        pt *= cap_px * ss / max(1, -b[1])
    return pt


def metin_alfa(metin, font_yolu, cap_px, wght=None, ref='H', ss=4):
    """ornament_ornek.py metin_alfa: metni ss kat buyuk cizip es oranli kucultur; buyuk harf yuksekligi (ref) = cap_px. Doner (A, taban)."""
    f = _font(font_yolu, _punto(font_yolu, cap_px, wght, ref, ss), wght)
    b = f.getbbox(metin, anchor='ls')
    pad = 6 * ss
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), metin, font=f, fill=255, anchor='ls')
    A = np.asarray(im, np.float32) / 255.0
    taban = (pad - b[1]) / ss
    A = cv2.resize(A, (max(1, round(w / ss)), max(1, round(h / ss))), interpolation=cv2.INTER_AREA)
    return A, taban


def metin_alfa_k(metin, font_yolu, cap_px, k, wght=None, ref='H', ss=4):
    """ornament_motor.py metin_alfa10 (K10 -> k): ayni punto arama; 1x cercevesinin TAM k kati tuval, punto x k, INTER_AREA."""
    pt_i = max(4, int(round(_punto(font_yolu, cap_px, wght, ref, ss))))
    b1 = _font(font_yolu, pt_i, wght).getbbox(metin, anchor='ls')
    pad = 6 * ss
    W1, H1 = b1[2] - b1[0] + 2 * pad, b1[3] - b1[1] + 2 * pad
    w9, h9 = max(1, round(W1 / ss)), max(1, round(H1 / ss))
    im = Image.new('L', (W1 * k, H1 * k), 0)
    ImageDraw.Draw(im).text(((pad - b1[0]) * k, (pad - b1[1]) * k), metin, font=_font(font_yolu, pt_i * k, wght), fill=255, anchor='ls')
    return cv2.resize(np.asarray(im, np.float32) / 255.0, (w9 * k, h9 * k), interpolation=cv2.INTER_AREA), pt_i


def isim_sigdir(metin, font_yolu, sinir=None, cap0=CAP_ISIM, cap_alt=CAP_AY, yumusak=False):
    """Kapi 8: isim satiri (ISIM1 & ISIM2, tek dizi) sayfa genisliginin %86'sini asarsa iki isim BIRLIKTE kuculur (poster kurali);
    buyuk harf cap_alt (53 px) altina inerse DUR. Doner (A, taban, cap, deneme listesi)."""
    sinir = GEN_ORAN * W if sinir is None else sinir
    cap, deneme = float(cap0), []
    for _ in range(8):
        A, taban = metin_alfa(metin, font_yolu, cap, 500)
        k_ = kutu(A)
        if k_[2] - k_[0] <= sinir:
            break
        yeni = math.floor(cap * sinir / (k_[2] - k_[0]) * 100) / 100.0
        cap = min(yeni, cap - 0.01); deneme.append(round(cap, 2))
        if cap < cap_alt and not yumusak:                                      # mod deneme: kuculmeye devam eder, FAIL'i cagiran yazar
            raise Dur('isim_kucuk', f'isim buyuk harfi {cap:.2f} px < {cap_alt} px (isim satiri sigmiyor)')
    else:
        raise Dur('isim_sigmadi', 'isim satiri 8 denemede sigmadi')
    return A, taban, cap, deneme


def cizim_katsayisi(cap_px):
    """oge basina: buyuk harf x k ~ POSTER_CAP (298 px) olacak tam sayi (motor sabitleri poster pikselinde kalir; plan bolum 3)."""
    return max(1, int(round(POSTER_CAP / float(cap_px))))


def kutu(a, t=0.02):
    ys, xs = np.nonzero(a > t)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def labf(x):
    return cv2.cvtColor((np.clip(x, 0, 255).reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)


def de00(Lab1, Lab2):
    """ornament_motor.py de00 (:840-862; motor renk_uyum.py ile ayni formul): CIEDE2000."""
    L1, a1, b1 = [float(v) for v in Lab1]; L2, a2, b2 = [float(v) for v in Lab2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    if C1p * C2p == 0: hpm = hs
    elif abs(h1p - h2p) <= 180: hpm = hs / 2
    else: hpm = (hs + 360) / 2 if hs < 360 else (hs - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def renk_uyum(katman, M, Lana):
    """ornament_motor.py :514-531: oge katmaninin Lab ortancasi (alfa >= 0.9) hedef Lana'ya (SEMBOL katmani) tam kaydirilir.
    < 200 cekirdek piksel: DUR. Doner (yeni katman, olcum)."""
    m = M >= 0.9
    if m.sum() < UYUM_MIN_PIKSEL:
        raise Dur('renk_uyum_piksel', f'cekirdek piksel {int(m.sum())} < {UYUM_MIN_PIKSEL}')
    Lo = np.median(labf(katman[m]), 0)
    d = Lana - Lo
    sec = M > 0.001
    out = katman.copy()
    L = labf(out[sec]) + d[None, :]
    out[sec] = np.clip(cv2.cvtColor(L.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
    Ls = np.median(labf(out[m]), 0)
    return out, dict(piksel=int(m.sum()), kaydirma_Lab=[round(float(v), 2) for v in d], dE00_once=round(de00(Lana, Lo), 3),
                     dE00_sonra=round(de00(Lana, Ls), 3))


def yari_kal(a):
    """ornament_motor.py :548-551: iskelet uzerinde mesafe donusumu ortancasi (cizgi yari kalinligi, px)."""
    from skimage.morphology import skeletonize
    m = (a > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return float(np.median(dt[skeletonize(m > 0)]))


def boya(taban, ogeler, dis=None):
    """ornament_motor.py boya_motor (:573-597) genellestirilmis (kare 954 tuval yerine herhangi tuval; ogeler yerel cerceveyle):
    1 notr dis golge: tum oge alfalarinin birlesimi, sigma / kayma / opak (zemin carpimla koyulasir)
    2 her oge: ic golge (kayma, sigma, guc; None = yok) ve carpan (skaler ya da tuval boyu alan); doygunluk kirpmasi; alfa ile bindirme
    ogeler: dict(x, y, rgb (h, w, 3) 0-255, m (h, w) 0-1, ic=None | dict(kayma, sigma, guc), carpan=1.0). Doner uint8 (H, W, 3)."""
    dis = dis or DIS_GOLGE
    Hh, Ww = taban.shape[:2]
    out = taban.astype(np.float32).copy()
    tum = np.zeros((Hh, Ww), np.float32)
    for o in ogeler:
        h, w = o['m'].shape
        sl = tum[o['y']:o['y'] + h, o['x']:o['x'] + w]
        np.maximum(sl, o['m'], out=sl)
    g_ = cv2.GaussianBlur(tum, (0, 0), dis['sigma'])
    g_ = cv2.warpAffine(g_, np.float32([[1, 0, dis['kayma']], [0, 1, dis['kayma']]]), (Ww, Hh))
    out = out * (1 - dis['opak'] * g_)[..., None]
    del tum, g_
    PAD = 16
    for o in ogeler:
        m = o['m']; h, w = m.shape
        cc = o['rgb'].astype(np.float32)
        carpan = o.get('carpan', 1.0)
        if isinstance(carpan, np.ndarray):
            carpan = carpan[o['y']:o['y'] + h, o['x']:o['x'] + w]
        q = o.get('ic')
        if q:
            mp = np.pad(m, PAD)
            kay = cv2.warpAffine(mp, np.float32([[1, 0, q['kayma']], [0, 1, q['kayma']]]), (mp.shape[1], mp.shape[0]))
            ic = (cv2.GaussianBlur(np.clip(mp - kay, 0, 1), (0, 0), q['sigma']) * mp)[PAD:-PAD, PAD:-PAD]
            carpan = carpan * (1 - q['guc'] * ic)
        if isinstance(carpan, np.ndarray):
            cc = cc * carpan[..., None]
        elif carpan != 1.0:
            cc = cc * carpan
        sat = cc.max(2, keepdims=True)
        cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
        sl = out[o['y']:o['y'] + h, o['x']:o['x'] + w]
        sl[:] = sl * (1 - m[..., None]) + cc * m[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- motor (ice alma + tasinan ornament adimlari)
class Motor:
    def __init__(self, md):
        self.md = md = Path(md)
        eksik = [f for f in MOTOR_DOSYA if not (md / f).is_file()]
        if eksik:
            raise Dur('motor_eksik', f'motor dosyasi yok: {eksik}')
        KL = json.loads((md / 'KILIT_GPTGIRDI.json').read_text())
        ortam = dict(KL['ortam'])
        ortam['PALET_KAYNAK'] = str(md / 'palet' / 'chatgpt_altin.png')
        os.environ.update(ortam)                                              # KILIT ortami motor ice alinmadan ONCE (ornament_motor.py:119-122)
        self.P = P = dict(P_VARSAYILAN); P.update(KL['AYAR'])
        self.KILIT = KL
        if not (P['g'] == 0 and P['m1'] == 0 and P['m2'] == 0 and P['parilti'] == 0 and P['isik_leke'] == 0 and P['ton'] == 0
                and P['esit'] == 'kazanc' and P['harita'] == 'dogrusal'):
            raise Dur('kilit', 'KILIT beklenen dallar disinda (ornament_motor.py:130)')
        if not (float(os.environ.get('KAVSAK_YUM', '0')) == 0 and float(os.environ.get('KEMER_KAVSAK', '0')) == 0
                and os.environ.get('SERIT', '0') == '0' and os.environ.get('SIRT_SUREKLI', '0') == '0'):
            raise Dur('kilit', 'KILIT ortami: KAVSAK / SERIT acik (ornament_motor.py:157)')
        if str(md) not in sys.path:
            sys.path.insert(0, str(md))
        import golge_motor as gm
        from alfa_temizle import temizle
        from vektor_yuzey import yon_alani
        self.gm, self.temizle, self.yon_alani = gm, temizle, yon_alani
        self.K = gm.kure_yukle(str(md / 'kure' / f"{P['kure']}.exr"))          # kure_yukle .exr -> .npy
        pk = np.asarray(Image.open(os.environ['PALET_KAYNAK']).convert('RGB')).astype(np.float32) / 255      # palet (uret_tam 143-147)
        hk = cv2.cvtColor(pk, cv2.COLOR_RGB2HSV); mk = ((hk[..., 1] > 0.45) & (hk[..., 2] > 0.42)).astype(np.uint8)
        self.ref_ana = pk[cv2.erode(mk, np.ones((3, 3), np.uint8)) > 0]
        self.VEK = os.environ.get('VEKTOR', '0') == '1'
        self.VEK_OGE = os.environ.get('VEKTOR_OGELER', 'ana,kucuk1,kucuk2,sonsuz').split(',')
        self.sha = {f: sha(md / f) for f in MOTOR_DOSYA}
        self.font_isim = md / 'font' / 'Cinzel.ttf'
        self.font_metin = md / 'font' / 'EBGaramond-Italic.ttf'

    def golgele_oge(self, a8, ad):
        """ornament_motor.py golgele_oge (:160-203; uret_tam.py 149-213 ile ayni; gurultu g = 0, KAVSAK / SERIT kapali)."""
        gm, P, Kk = self.gm, self.P, self.K
        A = a8.astype(np.float32) / 255
        h, w = A.shape; Yt = np.zeros((h, w), np.float32); At = np.zeros((h, w), np.float32)
        VYN = None
        if self.VEK and ad in self.VEK_OGE:
            assert P['karisim'] == 1.0 and P['pah_px'] == 0 and not P['kubbe']
            Ap = np.pad(A, 32)
            (vy_, vx_), alt_ = self.yon_alani(Ap)
            VYN = []
            for ux_s, uy_s in alt_:
                gxa = np.zeros(Ap.shape, np.float32); gya = np.zeros(Ap.shape, np.float32)
                gxa[vy_, vx_] = ux_s; gya[vy_, vx_] = uy_s
                VYN.append((gxa[32:-32, 32:-32], gya[32:-32, 32:-32]))
        KR, PD = 2048, 128
        for y0 in range(0, h, KR):
            for x0 in range(0, w, KR):
                ya, xa = max(0, y0 - PD), max(0, x0 - PD); yb, xb = min(h, y0 + KR + PD), min(w, x0 + KR + PD)
                Ak = A[ya:yb, xa:xb]
                if Ak.max() == 0: continue
                Ak = np.pad(Ak, 16)
                gm.egim_tup.kv = None; gm.egim_tup.H = None; gm.egim_tup.yon = None
                if VYN is not None:
                    Al = A[ya:yb, xa:xb]
                    kk_ = P['k'] / P['pah']
                    Y = np.zeros(Al.shape, np.float32)
                    for gxa, gya in VYN:
                        Y += gm.luma(gm.golgele_g(kk_ * gxa[ya:yb, xa:xb], kk_ * gya[ya:yb, xa:xb], Kk))
                    Y /= len(VYN)
                    ia, ib, ja, jb = y0 - ya, min(KR, h - y0) + (y0 - ya), x0 - xa, min(KR, w - x0) + (x0 - xa)
                    Yt[y0:y0 + ib - ia, x0:x0 + jb - ja] = Y[ia:ib, ja:jb]; At[y0:y0 + ib - ia, x0:x0 + jb - ja] = Al[ia:ib, ja:jb]
                    continue
                gx, gy, Al = gm.egim_tup(Ak, P['k'], pah=P['pah'], karisim=P['karisim'], pah_px=P['pah_px'], kubbe=P['kubbe'], egim_max=P['egim_max'],
                                         pah_oran_max=P['pah_oran_max'])
                gx, gy, Al = gx[16:-16, 16:-16], gy[16:-16, 16:-16], Al[16:-16, 16:-16]
                Y = gm.luma(gm.golgele_g(gx, gy, Kk))
                sr = getattr(gm.egim_tup, 'sirt', None)
                if sr is not None:
                    sr = sr[16:-16, 16:-16] if sr.shape != Y.shape else sr
                    Yb = cv2.GaussianBlur(Y, (0, 0), 0.7)
                    Y = np.where(sr, Yb, Y).astype(np.float32)
                    gm.egim_tup.sirt = None
                ia, ib, ja, jb = y0 - ya, min(KR, h - y0) + (y0 - ya), x0 - xa, min(KR, w - x0) + (x0 - xa)
                Yt[y0:y0 + ib - ia, x0:x0 + jb - ja] = Y[ia:ib, ja:jb]; At[y0:y0 + ib - ia, x0:x0 + jb - ja] = Al[ia:ib, ja:jb]
        return Yt, At

    @staticmethod
    def gorunen(Y, A):
        """uret_tam.py gorunen (ornament_motor.py:225-230): goz olcegi (1/3.6), alfa agirlikli kucultme, aa > 0.85."""
        f = 1 / 3.6
        ya = cv2.resize(Y * A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        aa = cv2.resize(A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        return (ya / np.maximum(aa, 1e-4))[aa > 0.85]

    def poster_ana(self, cift):
        """ornament_motor.py :205-218 (olustur_alfa_sablon.py 45-61): ciftin POSTER ana alfasi poster olceginde, temizlenmis, golgelenmis."""
        md = self.md

        def kirp8(x):
            ys, xs = np.nonzero(x > 8)
            return x[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        yol = md / 'girdi78' / 'ana' / f'{cift.lower()}_alfa.png'
        if not yol.is_file():
            raise Dur('motor_eksik', f'poster ana alfasi yok: girdi78/ana/{cift.lower()}_alfa.png')
        src = kirp8(np.asarray(Image.open(yol)).astype(np.float32))
        Yl = json.loads((md / 'yerlesim78.json').read_text())[cift]
        Cm = json.loads((md / 'cember.json').read_text())['cember']
        sp = (Cm['cx'] + Yl['u1'] * Cm['R'] - (Cm['cx'] + Yl['u0'] * Cm['R'])) / src.shape[1]
        tpa = np.clip(cv2.resize(src, None, fx=sp, fy=sp, interpolation=cv2.INTER_AREA if sp < 1 else cv2.INTER_CUBIC), 0, 255).astype(np.uint8)
        tpa, b_ = self.temizle(tpa)
        Ya, Aa = self.golgele_oge(tpa, 'ana')
        return Ya, Aa, dict(olcek=round(float(sp), 5), boyut=list(tpa.shape), temizle=b_, alfa_sha256=sha(yol))

    def harita_kur(self, cift, onbellek=None):
        """ornament_motor.py :219-231: renk haritasi (dogrusal, ChatGPT paleti) + goz dagilimi qa_goz. Onbellek: motor sha + alfa sha anahtari."""
        anahtar = hashlib.sha256(json.dumps([self.sha, cift, sha(self.md / 'girdi78' / 'ana' / f'{cift.lower()}_alfa.png')], sort_keys=True).encode()).hexdigest()[:20]
        dosya = Path(onbellek) / f'HARITA_{cift}_{anahtar}.pkl' if onbellek else None
        if dosya and dosya.is_file():
            with open(dosya, 'rb') as f:
                d = pickle.load(f)
            log('harita onbellekten', dosya.name)
            return d
        gm = self.gm
        Ya, Aa, bilgi = self.poster_ana(cift)
        cm = cv2.erode((Aa > 0.99).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        har = gm.renk_haritasi_dogrusal(Ya[cm], self.ref_ana)
        qa_goz = np.percentile(self.gorunen(Ya, Aa), QS)
        d = dict(har=har, qa_goz=qa_goz, bilgi=bilgi)
        log('harita', [round(float(v), 4) for v in har[1:6]], 'qa_goz50', round(float(qa_goz[3]), 4), bilgi['boyut'])
        if dosya:
            dosya.parent.mkdir(parents=True, exist_ok=True)
            with open(dosya, 'wb') as f:
                pickle.dump(d, f)
        return d

    def oge_katman(self, a_k, k, rng, har, qa_goz, ad='yazi'):
        """ornament_motor.py :455-486 (K10 -> k): k kat alfada golgeleme, esit 'goz' x2, renk haritasi, kenar yumusatma, gren (yalniz ogede),
        dogrusal isikta alfa agirlikli INTER_AREA 1/k. Doner (grenli katman, grensiz katman, kucultulmus alfa) (h, w[, 3]) 0-255 / 0-1."""
        gm, P = self.gm, self.P
        a8 = np.clip(np.round(a_k * 255), 0, 255).astype(np.uint8)
        Yo, Ao = self.golgele_oge(a8, ad)
        for _ in range(2):                                                    # esit 'goz' (uret_tam.py ile ayni dongu)
            qo = np.percentile(self.gorunen(Yo, Ao), QS); qo = np.maximum.accumulate(qo + np.arange(len(qo)) * 1e-5)
            Yo = np.interp(Yo, qo, qa_goz).astype(np.float32)
        rgb_s = gm.uygula_harita2(Yo, har)                                    # sRGB 0-1
        rgb = gm.lineer(rgb_s) * P['poz']
        Ak = cv2.GaussianBlur(Ao, (0, 0), P['kenar_yum']) if P['kenar_yum'] else Ao
        c255 = gm.srgb(rgb) * 255
        gn = cv2.GaussianBlur(rng.standard_normal(Ao.shape).astype(np.float32), (0, 0), 0.8)
        c255g = c255 + (gn / 0.35 * P['gren'])[..., None]                      # gren yalniz ogede (uret_tam formulu)
        out = []
        h9, w9 = a_k.shape[0] // k, a_k.shape[1] // k
        for cc in (c255g, c255):
            lin = gm.lineer(np.clip(cc, 0, 255) / 255)
            num = cv2.resize(lin * Ak[..., None], (w9, h9), interpolation=cv2.INTER_AREA)
            den = cv2.resize(Ak, (w9, h9), interpolation=cv2.INTER_AREA)
            col = num / np.maximum(den, 1e-6)[..., None]
            bos = den < 0.02                                                  # destek disi piksel: normalize bulanik doldurma (yalniz maske kenari icin)
            if bos.any():
                nb = cv2.GaussianBlur(num, (0, 0), 2.0); db = cv2.GaussianBlur(den, (0, 0), 2.0)
                col = np.where(bos[..., None], nb / np.maximum(db, 1e-6)[..., None], col)
            out.append(gm.srgb(np.clip(col, 0, 1)) * 255)
        atest = cv2.resize(Ao, (w9, h9), interpolation=cv2.INTER_AREA)
        return out[0], out[1], atest


def altin_ogeler(mt, ogeler, har, qa_goz, Lana, D_ana):
    """Altin yazi ogeleri, ornament yazi yolu (uretimin TEK giris noktasi; test_ay_takvim bunu ornament zinciriyle karsilastirir):
    k kat cizim (metin_alfa_k) -> Motor.oge_katman (ad 'yazi': egim_tup yolu; tek rng, tohum 11, oge sirasiyla) -> renk_uyum (hedef Lana)
    -> ic golge parametreleri (genislik x min(1, yari kalinlik / D_ana); ornament_motor.py :557-561). Sembol burada YOK (dokunulmaz).
    ogeler: dict(ad, metin, font, wght, ref, cap, k, A (1x alfa), x, y). Ogelere punto, atest, uyum, yari_kal, ic_oran yazar. Doner boya listesi.
    GRUP ogeleri (halka, kucuk semboller; Serdar 11 Kas): dict(ad, kaynak (uint8 poster alfasi), motor_ad ('cember' | 'kucuk1' | 'kucuk2'), k, A, x, y).
    Renk cizimi a_k = kaynak alfanin A cercevesinin TAM k katina TEK adim INTER_AREA kucultulmusu (buyutme yok); oge_katman(motor_ad) ile
    (kucuk semboller VEKTOR yolu, halka egim_tup yolu: posterdeki gibi). Yazi ogeleri once, grup ogeleri sonra (yazi rng sirasi degismez)."""
    rng = np.random.default_rng(11)
    out = []
    for o in ogeler:
        t1 = time.time()
        if 'kaynak' in o:
            hk, wk = o['A'].shape[0] * o['k'], o['A'].shape[1] * o['k']
            if wk > o['kaynak'].shape[1] or hk > o['kaynak'].shape[0]:
                raise Dur('grup_buyutme', f"{o['ad']}: k kat cizim kaynaktan buyuk (buyutme yok)")
            a_k, pt = cv2.resize(o['kaynak'].astype(np.float32) / 255.0, (wk, hk), interpolation=cv2.INTER_AREA), None
        else:
            a_k, pt = metin_alfa_k(o['metin'], o['font'], o['cap'], o['k'], o['wght'], o['ref'])
        if a_k.shape != (o['A'].shape[0] * o['k'], o['A'].shape[1] * o['k']):
            raise Dur('cerceve', f"{o['ad']}: k kat cerceve 1x cercevenin tam kati degil")       # ornament_motor.py :409-411
        if o.get('rng_boy'):                                                  # kalinlasmis halka (AYAR halka_kalinlik != 1): gren AYRI uretecten; ana uretec OZGUN
            kat_g, _, atest = mt.oge_katman(a_k, o['k'], np.random.default_rng([11, 1]), har, qa_goz, o.get('motor_ad', 'yazi'))
            rng.standard_normal(tuple(o['rng_boy']))                          # halka boyu kadar ilerler: sonraki ogelerin (kucuk semboller) greni carpandan etkilenmez
        else:
            kat_g, _, atest = mt.oge_katman(a_k, o['k'], rng, har, qa_goz, o.get('motor_ad', 'yazi'))
        if kat_g.shape[:2] != o['A'].shape:
            raise Dur('cerceve', f"{o['ad']}: katman boyu maske ile ayni degil")
        kat_u, uy = renk_uyum(kat_g, o['A'], Lana)
        yk = yari_kal(a_k) / o['k']
        r_ = min(1.0, yk / D_ana)
        o.update(punto=pt, atest=atest, uyum=uy, yari_kal=round(yk, 3), ic_oran=round(r_, 4))
        out.append(dict(ad=o['ad'], x=o['x'], y=o['y'], rgb=kat_u, m=o['A'],
                        ic=dict(kayma=IC_GOLGE['kayma'] * r_, sigma=IC_GOLGE['sigma'] * r_, guc=IC_GOLGE['guc']), carpan=1.0))
        log(f"oge {o['ad']:9s} k {o['k']} cap {o.get('cap', 0):.1f} cerceve {a_k.shape} piksel {uy['piksel']} dE {uy['dE00_once']}->{uy['dE00_sonra']} {time.time() - t1:.1f}s")
    return out


# ---------------------------------------------------------------- zemin (posterin Midnight Blue motor zemini; karar 5)
def zemin_radyal(md, P, Wc, Hc, f, cx, cy):
    """motor uret_tam.py :18-40: radyal profil (zemin_profil.json), dogrusal isik. f = tuval px / profil birimi (poster 7200 / 2000 = 3,6).
    Merkez (cx, cy) tuval pikselinde. Yatay / dikey ayni olcek (zemin_daire = 1 -> daire)."""
    Z = json.load(open(Path(md) / 'zemin_profil.json'))
    rr = np.array(Z['r'], np.float32) * f
    e = Z['e']
    LIN = [np.array(Z['lin'][c], np.float32) for c in range(3)]
    if P['zemin_daire']:                                                 # 360 derece ayni koyulasma: daire, tekduze azalan, yumusak profil
        e = 1.0
        Ly = 0.2126 * LIN[0] + 0.7152 * LIN[1] + 0.0722 * LIN[2]
        Ly = np.minimum.accumulate(Ly)                                   # merkezden disa hic aydinlanma yok
        Ly = cv2.GaussianBlur(np.r_[np.full(60, Ly[0]), Ly, np.full(60, Ly[-1])].reshape(-1, 1).astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=25).ravel()[60:-60]
        Ly = np.minimum.accumulate(Ly)
        oran = [LIN[c] / np.maximum(0.2126 * LIN[0] + 0.7152 * LIN[1] + 0.0722 * LIN[2], 1e-6) for c in range(3)]
        renk = [float(np.median(o[:80])) for o in oran]                   # merkez rengi
        renk2 = [float(np.median(o[-80:])) for o in oran]                 # dis renk
        tt = np.linspace(0, 1, len(Ly)).astype(np.float32)
        LIN = [(Ly * (renk[c] * (1 - tt) + renk2[c] * tt)).astype(np.float32) for c in range(3)]
    zemin = np.empty((Hc, Wc, 3), np.float32)
    xs = np.arange(Wc, dtype=np.float32)
    for y0 in range(0, Hc, 600):
        yy = np.arange(y0, min(Hc, y0 + 600), dtype=np.float32)[:, None]
        r = np.hypot(xs[None] - cx, (yy - cy) * e)
        for c in range(3):
            zemin[y0:y0 + len(yy), :, c] = np.interp(r, rr, LIN[c])
    return zemin


def zemin_yildiz(zemin, md, gm, f, ox=0.0, oy=0.0, maske=None, engel=None, sayac=None):
    """motor uret_tam.py :111-135 ('refkopya'): REF yildizlarinin KENDISI (ref/ref.png yamasi, yerel zemin cikarilmis fazlalik), f kat
    buyutulup ayni goreli yere eklenir. Poster: f = 3,6, ox = oy = 0. Ay takvimi: f = 2,7 ve (ox, oy) profil merkezini cember merkezine
    oturtan kayma; tuval disina dusen yama atlanir. maske verilirse yildiz eklenen pikseller isaretlenir. engel (uint8, tuval boyu)
    verilirse engele degen yama atlanir (ogelerin ustune / yanina yildiz konmaz); sayac['engel'] atlanan sayisi. Doner yildiz sayisi."""
    lineer = gm.lineer
    Hc, Wc = zemin.shape[:2]
    rf = np.asarray(Image.open(Path(md) / 'ref' / 'ref.png').convert('RGB')).astype(np.float32) / 255
    rl = lineer(rf)
    Lr = rf.mean(2); mr = cv2.medianBlur((Lr * 255).astype(np.uint8), 15).astype(np.float32) / 255
    fr = ((Lr - mr) > 0.06).astype(np.uint8); fr[400:2700, 150:1850] = 0
    n_, lr_, st_, cr_ = cv2.connectedComponentsWithStats(fr)
    zem = np.stack([cv2.medianBlur(np.ascontiguousarray((rf[..., k] * 255).astype(np.uint8)), 21) for k in range(3)], -1).astype(np.float32) / 255
    fz = np.clip(rl - lineer(zem), 0, None)                              # yildiz isigi (lineer fazlalik)
    sy = 0
    for i in range(1, n_):
        if st_[i, 4] < 2: continue
        cx_, cy_ = cr_[i]; S2 = 16
        x0r, y0r = int(round(cx_)) - S2, int(round(cy_)) - S2
        if x0r < 0 or y0r < 0 or x0r + 2 * S2 >= 2000 or y0r + 2 * S2 >= 3000: continue
        yama = fz[y0r:y0r + 2 * S2, x0r:x0r + 2 * S2]
        ag = np.hypot(*np.mgrid[-S2:S2, -S2:S2]); yama = yama * np.clip((S2 - ag) / 4, 0, 1)[..., None]   # yumusak kenar
        B = cv2.resize(yama, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        B = np.clip(B, 0, None)
        X0, Y0 = int(round(x0r * f + ox)), int(round(y0r * f + oy))
        hh, ww = B.shape[:2]
        if X0 < 0 or Y0 < 0 or X0 + ww > Wc or Y0 + hh > Hc:
            if sayac is not None: sayac['tuval_disi'] = sayac.get('tuval_disi', 0) + 1
            continue
        if engel is not None and engel[Y0:Y0 + hh, X0:X0 + ww].any():
            if sayac is not None: sayac['engel'] = sayac.get('engel', 0) + 1
            continue
        zemin[Y0:Y0 + hh, X0:X0 + ww] += B
        if maske is not None:
            sl = maske[Y0:Y0 + hh, X0:X0 + ww]
            sl[B.max(2) > 0.0005] = 255                                       # dogrusal isik; sRGB'de ~ 1,6 seviye ustu
        sy += 1
    return sy


def zemin_8bit(zemin, gm, P):
    """motor uret_tam.py :371-392: sRGB + TPDF titresim + ince gren (tum zemine; KILIT gren) -> 8 bit. renk_ayar / kararma KILIT'te 0."""
    assert not P['renk_ayar'] and not P['kararma']
    Hc, Wc = zemin.shape[:2]
    rs = np.random.default_rng(11)
    out = np.empty((Hc, Wc, 3), np.uint8)
    for y0 in range(0, Hc, 600):
        zb = zemin[y0:y0 + 600]
        b = gm.srgb(zb) * 255
        tp_ = rs.random(b.shape, np.float32) - rs.random(b.shape, np.float32)
        b += tp_
        if P['gren']:                                                   # tum postere ayni ince gren
            gn = cv2.GaussianBlur(rs.standard_normal(b.shape[:2]).astype(np.float32), (0, 0), 0.8)
            b += (gn / 0.35 * P['gren'])[..., None]
        out[y0:y0 + 600] = np.clip(np.round(b), 0, 255).astype(np.uint8)
    return out


# ---------------------------------------------------------------- sembol katmani
def sembol_yukle(yol):
    """<CIFT>_ana.png: RGBA zorunlu. Doner (rgba float32: RGB 0-255, A 0-1; olcum). Bicim hatasi = girdi hatasi (cikis 3)."""
    yol = Path(yol)
    if not yol.is_file():
        raise Dur('sembol_yok', 'sembol katmani dosyasi yok', girdi=True)
    im = Image.open(yol)
    olc = dict(mod=im.mode, boyut=list(im.size), sha256=sha(yol), bayt=yol.stat().st_size)
    yan = Path(str(yol) + '.json')
    if yan.is_file():
        try:
            j = json.loads(yan.read_text())
            olc['yan_json'] = {k: j[k] for k in sorted(j) if isinstance(j[k], (int, float, bool))}
            olc['yan_json_alanlar'] = sorted(j)
        except Exception as e:                                               # noqa: BLE001
            olc['yan_json_hata'] = type(e).__name__
    else:
        olc['yan_json'] = None
    if im.mode != 'RGBA':
        olc['hata'] = f'mod {im.mode}, RGBA degil (alfa yok)'
        raise Dur('sembol_bicim', olc['hata'], girdi=True)
    g = np.asarray(im, np.float32).copy(); g[..., 3] /= 255.0
    a = g[..., 3]
    if not (a > 0.5).any() or (a > 0.5).all():
        olc['hata'] = 'alfa bos ya da tam dolu'
        raise Dur('sembol_bicim', olc['hata'], girdi=True)
    k05, k002 = kutu(a, 0.5), kutu(a, 0.02)
    cx, cy = (k05[0] + k05[2]) / 2.0, (k05[1] + k05[3]) / 2.0
    ys, xs = np.nonzero(a > 0.5)
    r = float(np.hypot(xs + 0.5 - cx, ys + 0.5 - cy).max())
    olc.update(kutu_alfa_05=list(k05), kutu_alfa_002=list(k002), merkez_05=[cx, cy], cevre_yaricap_05=round(r, 2),
               en_boy_05=round((k05[2] - k05[0]) / (k05[3] - k05[1]), 5), alfa_05_piksel=int(len(ys)),
               alfa_tam_oran=round(float((a >= 0.999).mean()), 4), alfa_yari_oran=round(float(((a > 0.02) & (a < 0.98)).mean()), 4))
    olc['olcek'] = {ad: round(SEMBOL_ORAN * v['sembol_alan'] * S / r, 5) for ad, v in YERLESIM.items() if not v['grup']}   # grup yerlesimleri: grup_kur
    if max(olc['olcek'].values()) > 1.0:
        olc['hata'] = f"sembol kucuk: gereken olcek {max(olc['olcek'].values())} > 1 (buyutme yok)"
        raise Dur('sembol_bicim', olc['hata'], girdi=True)
    return g, olc


def rgba_olcek(rgba, k):
    """ornament_ornek.py rgba_olcek (:76-82) + olcek (:70-73): on carpilmis RGB ile es oranli kucultme (INTER_AREA)."""
    a = rgba[..., 3:4]
    h, w = rgba.shape[:2]
    pm = cv2.resize(np.concatenate([rgba[..., :3] * a, a], -1), (max(1, round(w * k)), max(1, round(h * k))), interpolation=cv2.INTER_AREA)
    a2 = pm[..., 3]
    rgb = pm[..., :3] / np.maximum(a2[..., None], 1e-4)
    return np.clip(rgb, 0, 255), np.clip(a2, 0, 1)


def sembol_yerlestir(g, olc, hedef_r):
    """yalniz es oranli kucultme (karar 3). Doner (rgb, a, x, y: merkez (0, 0)'a gore sol ust kose, olcek, bilgi)."""
    k = hedef_r / olc['cevre_yaricap_05']
    if k > 1.0:
        raise Dur('sembol_olcek', f'olcek {k:.4f} > 1 (buyutme yok)')
    rgb, a = rgba_olcek(g, k)
    k05 = kutu(a, 0.5)
    x = int(round(-(k05[0] + k05[2]) / 2.0)); y = int(round(-(k05[1] + k05[3]) / 2.0))
    eb = (k05[2] - k05[0]) / (k05[3] - k05[1])
    return rgb, a, x, y, dict(olcek=float(k), kutu_05=list(k05), en_boy_05=round(eb, 5), en_boy_fark=round(abs(eb - olc['en_boy_05']), 5),
                              boyut=[int(a.shape[1]), int(a.shape[0])])


# ---------------------------------------------------------------- sembol grubu (Serdar 11 Kas): ana sembol + halka + 2 kucuk burc
def grup_kaynak(mt, cift, kucuk_u='poster', kucuk_v='poster'):
    """Poster pikselinde (7200x10800) halka ve iki kucuk burc semboludun KAYNAK alfalari (uint8) ve sol ust koseleri.
    Halka: alfa_ogeler.npz 'cember' + _konum (ciftten bagimsiz; npz'nin diger ogeleri SCORPIO_VIRGO'ya aittir, okunmaz).
    Kucuk semboller: olustur_alfa_sablon.py :94-103 (sayfadan kutuyla kes, kirp > 8, pad 40 + temizle, merkez (cx + u R, KUCUK_Y), ekle kirpimi).
    AYAR: kucuk_u 'poster' (KUCUK_U[cift]) ya da sayi (simetrik -u / +u); kucuk_v 'poster' (KUCUK_Y) ya da sayi (cy + v R)."""
    md = mt.md
    if cift not in KUCUK_U:
        raise Dur('grup_cift', f'{cift}: kucuk sembol yeri (onayli poster) tanimli degil')
    C = json.loads((md / 'cember.json').read_text())['cember']
    z = np.load(md / 'alfa_ogeler.npz')
    adlar = [str(a_) for a_ in z['_ad']]
    i = adlar.index('cember')
    out = [dict(ad='halka', motor_ad='cember', alfa=np.ascontiguousarray(z['cember']), px=float(z['_konum'][i][0]), py=float(z['_konum'][i][1]))]
    uu = KUCUK_U[cift] if kucuk_u == 'poster' else (-float(kucuk_u), float(kucuk_u))
    y_mer = KUCUK_Y if kucuk_v == 'poster' else C['cy'] + float(kucuk_v) * C['R']
    for ad, burc, u in zip(('kucuk1', 'kucuk2'), cift.split('_'), uu):
        sayfa, kk = KUCUK[burc]
        k_ = np.asarray(Image.open(md / 'girdi' / f'{sayfa}.png').convert('L')).astype(np.float32)[kk[1]:kk[3], kk[0]:kk[2]]
        ys, xs = np.nonzero(k_ > 8)
        k_ = k_[ys.min():ys.max() + 1, xs.min():xs.max() + 1]                    # kirp
        q = 40
        k8, _ = mt.temizle(np.pad(np.clip(k_, 0, 255).astype(np.uint8), q))
        x0 = int(round(C['cx'] + u * C['R'] - k_.shape[1] / 2)) - q
        y0 = int(round(y_mer - k_.shape[0] / 2)) - q
        ys, xs = np.nonzero(k8 > 0)                                             # ekle(): 8 px payli kirpim
        a_, b_, c_, d_ = max(0, ys.min() - 8), min(k8.shape[0], ys.max() + 9), max(0, xs.min() - 8), min(k8.shape[1], xs.max() + 9)
        out.append(dict(ad=ad, motor_ad=ad, burc=burc, u=u, alfa=np.ascontiguousarray(k8[a_:b_, c_:d_]), px=float(x0 + c_), py=float(y0 + a_),
                        mer=[C['cx'] + u * C['R'], y_mer]))
    return out, C, y_mer


def halka_kalinlastir(alfa, px, py, C, carpan, hizala=None):
    """AYAR halka_kalinlik (Serdar 11 Kas): halkanin CIZGI KALINLIGI her noktada ayni carpanla buyur ("orantili"); yaricap, merkez, aciklik (acisal
    kapsam) ve uclara dogru incelme bicimi korunur. Yontem: kaynak alfa (poster pikseli), halkanin kendi MERKEZ CIZGISI etrafinda radyal olarak
    carpan kadar genisletilir: cikti(r, aci) = kaynak(Rc(aci) + (r - Rc(aci)) / carpan, aci). Rc(aci) = o acidaki alfa agirlikli ortalama yaricap
    (0,5 derecelik kutular, dairesel yumusatma; aciklikta en yakin dolu kutu). Aci degismedigi icin uc noktalar ve aciklik aynen kalir.
    Ornekleme cift dogrusal (cv2.remap). carpan 1,0: kaynak AYNEN doner (islem yok). Doner (alfa uint8, px, py): tuval radyal buyume kadar genisler.
    hizala=(ex, ey, olcek): tuval payi, kucultme ve tam sayi yerlesim yuvarlamasi OZGUN halkayla ayni fazda kalacak bicimde secilir (halkanin
    yeri yuvarlama yuzunden kaymasin; payin 60 px'lik araliginda en kucuk faz farki)."""
    c = float(carpan)
    if c == 1.0:
        return alfa, px, py
    a = alfa.astype(np.float32) / 255.0
    h, w = a.shape
    ys, xs = np.nonzero(alfa > 0)
    ww = a[ys, xs].astype(np.float64)
    dx, dy = xs + 0.5 + px - C['cx'], ys + 0.5 + py - C['cy']
    r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
    NB = 720
    b = np.floor((t + np.pi) / (2 * np.pi) * NB).astype(np.int64) % NB
    sw, sr = np.bincount(b, ww, NB), np.bincount(b, ww * r, NB)
    dolu = np.nonzero(sw > 1.0)[0]
    if len(dolu) < NB // 4:
        raise Dur('halka_kaynak', 'halka kaynaginda merkez cizgisi olculemedi')
    rc = np.zeros(NB)
    rc[dolu] = sr[dolu] / sw[dolu]
    uz = np.abs(np.arange(NB)[:, None] - dolu[None, :]); uz = np.minimum(uz, NB - uz)
    rc = rc[dolu[np.argmin(uz, 1)]]                                           # bos kutu (aciklik): en yakin dolu kutunun yaricapi
    g_ = np.exp(-0.5 * (np.arange(-18, 19) / 6.0) ** 2); g_ /= g_.sum()
    rc = np.convolve(np.r_[rc[-18:], rc, rc[:18]], g_, 'valid')               # dairesel yumusatma (sigma 3 derece)
    pad = int(math.ceil((c - 1.0) * (r.max() - r.min()) / 2.0)) + 3
    if hizala is not None:
        ex_, ey_, ol_ = hizala

        def faz(v):
            return v - round(v)

        def fark(p_):                                                         # ozgun halkaya gore: sol ust kose yuvarlama fazi (x, y) + boy yuvarlama fazi (w, h)
            d = [faz((px - p_ - ex_) * ol_) - faz((px - ex_) * ol_), faz((py - p_ - ey_) * ol_) - faz((py - ey_) * ol_),
                 faz((w + 2 * p_) * ol_) - faz(w * ol_), faz((h + 2 * p_) * ol_) - faz(h * ol_)]
            return max(abs(v) for v in d)
        pad = min(range(pad, pad + 61), key=fark)
    H2, W2 = h + 2 * pad, w + 2 * pad
    ddx = (np.arange(W2, dtype=np.float32) + 0.5 + px - pad - C['cx'])[None, :]
    ddy = (np.arange(H2, dtype=np.float32) + 0.5 + py - pad - C['cy'])[:, None]
    rr = np.sqrt(ddx * ddx + ddy * ddy).astype(np.float32)
    tt = np.arctan2(np.broadcast_to(ddy, (H2, W2)), np.broadcast_to(ddx, (H2, W2))).astype(np.float32)
    fi = (tt + np.float32(np.pi)) / np.float32(2 * np.pi) * NB - 0.5           # kutu merkezleri arasi dogrusal (dairesel) aradeger
    del tt
    i0 = np.floor(fi).astype(np.int32)
    f_ = (fi - i0).astype(np.float32)
    del fi
    rcf = rc.astype(np.float32)
    rct = rcf[i0 % NB] * (1 - f_) + rcf[(i0 + 1) % NB] * f_
    del i0, f_
    olc_ = (rct + (rr - rct) / np.float32(c)) / np.maximum(rr, 1e-3)           # kaynak yaricapi / cikti yaricapi
    del rct, rr
    mx = (np.float32(C['cx']) + ddx * olc_ - np.float32(px) - 0.5).astype(np.float32)
    my = (np.float32(C['cy']) + ddy * olc_ - np.float32(py) - 0.5).astype(np.float32)
    del olc_
    out = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return np.clip(np.round(out * 255.0), 0, 255).astype(np.uint8), float(px - pad), float(py - pad)


def _dis_noktalar(alfa01, px, py, olcek=1.0):
    """alfa > GRUP_ALFA_ESIK piksellerinin dis bukey kabugu, poster koordinatinda (piksel koseleri dahil)."""
    pts = cv2.findNonZero((alfa01 > GRUP_ALFA_ESIK).astype(np.uint8))
    h = cv2.convexHull(pts).reshape(-1, 2).astype(np.float64)
    k4 = np.concatenate([h, h + [1, 0], h + [0, 1], h + [1, 1]])
    return k4 * olcek + [px, py]


def grup_kur(mt, cift, g, yan_json, hedef_r, merkez='grup', kucuk_u='poster', kucuk_v='poster', kucuk_oran=1.0, halka_kalinlik=1.0):
    """Sembol grubu: posterdeki goreli duzen, TEK oran. g: ana katman (RGBA float; RGB 0-255, A 0-1); yan_json: katmanin .json alanlari
    (x, y, w, h [, kaynak_x, kaynak_y, kaynak_w, kaynak_h]: paysiz kutu). Ana sembol posterde: genislik (u1 - u0) R, sol ust (u0, v0)
    (olustur_alfa_sablon.py :52-57; yukseklik katmanin kendi oranindan). Doner dict(olcek, ana=(rgb, a, x, y), ogeler=[...], bilgi);
    x, y takvim merkezine gore tam sayi sol ust kose. hedef_r = grubun cevreleyen dairesinin (hal 'halka': en uzak pikselinin) yaricapi (px).
    AYAR kucuk_oran: kucuk semboller kendi merkezleri (cx + u R, y) etrafinda es oranli carpilir (1,0 = poster boyu); toplam olcek <= 1.
    AYAR halka_kalinlik: yalniz halkanin cizgi kalinligi (halka_kalinlastir). Grubun cevreleyen dairesi, olcegi ve tum yerler OZGUN (carpan 1) halkadan
    hesaplanir: carpan baska hicbir ogeyi buyutmez / kaydirmaz; kalin halka cevreleyen daireyi yaklasik (carpan - 1) x kalinlik / 2 x olcek kadar asar
    (yumusak kenar da carpanla genisledigi icin olculen asim biraz fazladir). Gren: kalin halka ayri uretecten, ana uretec ozgun halka boyu kadar ilerler."""
    if merkez not in GRUP_MERKEZ:
        raise Dur('girdi_grup', 'grup merkezi taninmadi', girdi=True)
    if not yan_json or not all(k_ in yan_json for k_ in ('x', 'y', 'w', 'h')):
        raise Dur('sembol_json', 'sembol yan json (x, y, w, h) yok: grup yerlesimi icin paysiz kutu gerekir', girdi=True)
    j = yan_json
    pay_x, pay_y = j.get('kaynak_x', j['x']) - j['x'], j.get('kaynak_y', j['y']) - j['y']
    kw = j.get('kaynak_w', j['w'])
    if g.shape[1] != j['w'] or g.shape[0] != j['h'] or pay_x < 0 or pay_y < 0 or kw <= 0 or kw + pay_x > j['w']:
        raise Dur('sembol_json', f"sembol yan json katmanla tutarsiz (katman {g.shape[1]}x{g.shape[0]}, json {j['w']}x{j['h']})", girdi=True)
    kay, C, y_mer = grup_kaynak(mt, cift, kucuk_u, kucuk_v)
    ko = float(kucuk_oran)
    for o in kay:                                                             # ogenin kendi carpani ve poster sol ust kosesi
        o['oran'] = ko if 'mer' in o else 1.0
        if o['oran'] != 1.0:
            o['px'], o['py'] = o['mer'][0] - (o['mer'][0] - o['px']) * ko, o['mer'][1] - (o['mer'][1] - o['py']) * ko
    Yl = json.loads((mt.md / 'yerlesim78.json').read_text())[cift]
    s_ana = (Yl['u1'] - Yl['u0']) * C['R'] / kw                               # katman pikseli -> poster pikseli
    ana_px, ana_py = C['cx'] + Yl['u0'] * C['R'] - pay_x * s_ana, C['cy'] + Yl['v0'] * C['R'] - pay_y * s_ana
    nok = [_dis_noktalar(g[..., 3], ana_px, ana_py, s_ana)] + [_dis_noktalar(o['alfa'].astype(np.float32) / 255.0, o['px'], o['py'], o['oran']) for o in kay]
    tum = np.concatenate(nok)
    if merkez == 'grup':
        (ex, ey), er = cv2.minEnclosingCircle(tum.astype(np.float32))
        ex, ey, er = float(ex), float(ey), float(er)
    else:
        ex, ey = float(C['cx']), float(C['cy'])
        er = float(np.hypot(tum[:, 0] - ex, tum[:, 1] - ey).max())
    olcek = hedef_r / er
    if olcek > 1.0 or olcek * s_ana > 1.0 or olcek * ko > 1.0:
        raise Dur('grup_olcek', f'grup olcegi {olcek:.4f} (ana {olcek * s_ana:.4f}, kucuk {olcek * ko:.4f}) > 1 (buyutme yok)')
    hk = float(halka_kalinlik)
    rng_boy = None
    if hk != 1.0:                                                             # olcek ve merkez yukarida OZGUN halkayla hesaplandi; simdi yalniz halka kaynagi kalinlasir
        o0 = kay[0]
        h0_, w0_ = o0['alfa'].shape                                           # ozgun halkanin k kat cizim boyu (gren ureteci bu kadar ilerler: altin_ogeler)
        mw0, mh0 = max(1, round(w0_ * olcek)), max(1, round(h0_ * olcek))
        k0 = max(1, int(math.floor(1.0 / olcek)))
        while k0 > 1 and (mw0 * k0 > w0_ or mh0 * k0 > h0_):
            k0 -= 1
        rng_boy = [mh0 * k0, mw0 * k0]
        o0['alfa'], o0['px'], o0['py'] = halka_kalinlastir(o0['alfa'], o0['px'], o0['py'], C, hk, (ex, ey, olcek))
    rgb, a = rgba_olcek(g, olcek * s_ana)
    hx, hy = (ana_px - ex) * olcek, (ana_py - ey) * olcek
    ana = dict(rgb=rgb, a=a, x=int(round(hx)), y=int(round(hy)), hedef=[hx, hy], olcek=float(olcek * s_ana))
    ogeler = []
    for o in kay:
        h_, w_ = o['alfa'].shape
        so = olcek * o['oran']                                                # ogenin toplam olcegi (kaynak pikseli -> tuval pikseli)
        mw, mh = max(1, round(w_ * so)), max(1, round(h_ * so))
        m = cv2.resize(o['alfa'].astype(np.float32) / 255.0, (mw, mh), interpolation=cv2.INTER_AREA)   # TEK adim
        k = max(1, int(math.floor(1.0 / so)))
        while k > 1 and (mw * k > w_ or mh * k > h_):                         # k kat cizim kaynaktan buyuk olamaz (yuvarlama kenari)
            k -= 1
        hx, hy = (o['px'] - ex) * olcek, (o['py'] - ey) * olcek
        ogeler.append(dict(ad=o['ad'], tur='grup', motor_ad=o['motor_ad'], kaynak=o['alfa'], A=m, k=k, x=int(round(hx)), y=int(round(hy)),
                           hedef=[hx, hy], poster=[o['px'], o['py']], olcek=float(so), kutu=kutu(m)))
        if o['ad'] == 'halka' and rng_boy:
            ogeler[-1]['rng_boy'] = rng_boy
    bilgi = dict(merkez=merkez, olcek=float(olcek), s_ana=float(s_ana), k={o['ad']: o['k'] for o in ogeler}, cevre_merkez_poster=[ex, ey], cevre_yaricap_poster=er, hedef_yaricap=float(hedef_r),
                 halka_merkez_kayma_px=[round((C['cx'] - ex) * olcek, 2), round((C['cy'] - ey) * olcek, 2)],
                 halka_kalinlik_px=round(C['kalinlik'] * olcek * hk, 3), halka_kalinlik_mm=round(C['kalinlik'] * olcek * hk * 25.4 / DPI, 3), halka_carpan=hk,
                 halka_yaricap_px=round(C['R'] * olcek, 2), cember=C, yerlesim78={k_: Yl[k_] for k_ in ('u0', 'u1', 'v0', 'v1')},
                 kucuk_u=[o['u'] for o in kay if 'u' in o], kucuk_v=round((y_mer - C['cy']) / C['R'], 5), kucuk_oran=ko, pay=[pay_x, pay_y])
    return dict(olcek=float(olcek), ana=ana, ogeler=ogeler, bilgi=bilgi)


# ---------------------------------------------------------------- altin disi cizim (duz renk)
def disk_ciz(img, maske, x, y, r, oran, buyuyor, isaret):
    """ay diski: koyu disk + aydinlik kisim (buyuyen ayda SAG; terminator elipsi yatay yari ekseni (1 - 2 x oran) x r) + ince kenar;
    yeni ay / dolunay: isaret halkasi (altin degil). Alt piksel dogrulugu: cv2 shift = 4."""
    SH, F = 4, 16
    c = (int(round(x * F)), int(round(y * F)))
    cv2.circle(img, c, int(round(r * F)), RENK_KOYU, -1, cv2.LINE_AA, SH)
    if oran > 0.004:
        sg = 1.0 if buyuyor else -1.0
        t = np.linspace(-math.pi / 2, math.pi / 2, 97)
        yy = r * np.sin(t)
        yan = np.sqrt(np.maximum(r * r - yy * yy, 0))
        kenar = np.c_[x + sg * yan, y + yy]                                   # aydinlik taraf yayi (ustten alta)
        term = np.c_[x + sg * (1 - 2 * oran) * yan, y + yy][::-1]             # terminator (alttan uste)
        pts = np.round(np.r_[kenar, term] * F).astype(np.int32)
        cv2.fillPoly(img, [pts], RENK_ACIK, cv2.LINE_AA, SH)
    cv2.circle(img, c, int(round((r - KENAR_CIZGI / 2.0) * F)), RENK_KENAR, KENAR_CIZGI, cv2.LINE_AA, SH)
    r_tot = r
    if isaret:
        kal = ISARET_KALIN * S
        r_tot = r + ISARET_DIS * S
        cv2.circle(img, c, int(round((r_tot - kal / 2.0) * F)), RENK_ACIK, kal, cv2.LINE_AA, SH)
    cv2.circle(maske, c, int(round(r_tot * F)), 255, -1, cv2.LINE_8, SH)


def duz_yazi(img, maske, A, x, y, renk):
    """duz renkli yazi (gun rakami; altin DEGIL): alfa ile bindirme."""
    h, w = A.shape
    sl = img[y:y + h, x:x + w].astype(np.float32)
    img[y:y + h, x:x + w] = np.clip(np.round(sl * (1 - A[..., None]) + np.array(renk, np.float32) * A[..., None]), 0, 255).astype(np.uint8)
    np.maximum(maske[y:y + h, x:x + w], (A > 0.02).astype(np.uint8) * 255, out=maske[y:y + h, x:x + w])


# ---------------------------------------------------------------- uretim
def ayar_kur(a):
    """uret girdisinden etkin AYAR ve cikti adi. --ayar-dosya + --sira (mod deneme; ayar-dogrula'nin yazdigi dosya): ad KODDAN uretilir
    (DENEME_<sira>_<yerlesim>), girdiden degil. Yoksa komut satiri (yerlesim, isim1, isim2, satir, grup-merkez) + istege bagli --ayar JSON sozlugu."""
    if getattr(a, 'ayar_dosya', None):
        try:
            L = json.loads(Path(a.ayar_dosya).read_text())
        except Exception:                                                     # noqa: BLE001
            raise Dur('girdi_ayar', 'ayar dosyasi okunamadi', girdi=True) from None
        if not isinstance(L, list) or not 1 <= len(L) <= DENEME_AZAMI or a.sira is None or not 1 <= a.sira <= len(L):
            raise Dur('girdi_ayar', 'ayar dosyasi / sira gecersiz', girdi=True)
        try:
            AY = ayar_dogrula(L[a.sira - 1])
        except Dur as e:
            raise Dur(e.kod, f'deneme {a.sira}: {e.neden}', girdi=True) from None
        return AY, f"DENEME_{a.sira}_{AY['yerlesim']}"
    ham = {}
    if getattr(a, 'ayar', None):
        try:
            ham = json.loads(a.ayar)
        except ValueError:
            raise Dur('girdi_ayar', 'bozuk JSON', girdi=True) from None
        if not isinstance(ham, dict):
            raise Dur('girdi_ayar', 'ayar sozluk degil', girdi=True)
    for k_, v in (('yerlesim', a.yerlesim), ('isim1', a.isim1), ('isim2', a.isim2), ('grup_merkez', getattr(a, 'grup_merkez', None))):
        if v is not None:
            if k_ in ham:
                raise Dur('girdi_ayar', f'{k_} hem komut satirinda hem ayarda', girdi=True)
            ham[k_] = v
    if a.satir:
        if 'satirlar' in ham:
            raise Dur('girdi_ayar', 'satirlar hem komut satirinda hem ayarda', girdi=True)
        ham['satirlar'] = list(a.satir)
    for k_ in ('yerlesim', 'isim1', 'isim2'):
        if k_ not in ham:
            raise Dur('girdi_ayar', f'{k_} verilmedi', girdi=True)
    if not isinstance(ham['yerlesim'], str) or ham['yerlesim'] not in YERLESIM:
        raise Dur('girdi_yerlesim', 'bilinmeyen yerlesim', girdi=True)
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', a.ad or ''):
        raise Dur('girdi_ad', 'cikti adi yalniz harf / rakam / alt cizgi', girdi=True)
    return ayar_dogrula(ham, spiral=True), a.ad


def _kesisim(x, y, h, w):
    """Ogenin (sol ust x, y; boy h, w) tuvalle kesisimi: (y0, y1, x0, x1, yerel y, yerel x) ya da None."""
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return None
    return y0, y1, x0, x1, y0 - y, x0 - x


def uret(a):
    cift = cift_dogrula(a.cift)
    mod = getattr(a, 'mod', None) or 'ornek'
    if mod not in MODLAR:
        raise Dur('girdi_mod', 'bilinmeyen mod', girdi=True)
    AY, ad = ayar_kur(a)
    a.ad = ad                                                                 # DUR kaydi da koddan uretilen adla yazilir
    deneme = mod == 'deneme'
    isim1, isim2, satirlar, yerlesim = AY['isim1'], AY['isim2'], AY['satirlar'], AY['yerlesim']
    kontrol = {}                                                              # mod ornek: tutmayan DUR; mod deneme: FAIL yazilir, gorsel yine cikar

    def denetle(kod, tamam, neden):
        kontrol[kod] = dict(PASS=bool(tamam), neden=None if tamam else neden)
        if not tamam and not deneme:
            raise Dur(kod, neden)
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    raqm = bool(features.check('raqm'))
    if Image.__version__ != '11.0.0' or not raqm:
        raise Dur('ortam', f'pillow {Image.__version__} raqm {raqm}; ornament ortami pillow 11.0.0 + raqm acik olmali')
    sure = {}
    t_ = time.time()
    # 1 veri
    gunler = ay_verisi(YIL)
    vk = veri_kapisi(gunler)
    if not vk['PASS']:
        raise Dur('veri', json.dumps(vk))
    # 2 sembol (olcum kapilardan ONCE yazilir) + motor
    g, s_olc = sembol_yukle(a.katman)
    (O / f'{ad}_SEMBOL_OLCUM.json').write_text(json.dumps(s_olc, indent=1))
    YA = YERLESIM[yerlesim]
    mt = Motor(a.motor)
    grup_oge, grup_bilgi = [], None
    if YA['grup']:
        s_r = AY['grup_oran'] * AY['sembol_alan'] * S
        G = grup_kur(mt, cift, g, s_olc.get('yan_json'), s_r, AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'], AY['halka_kalinlik'])
        s_rgb, s_a, s_x, s_y = G['ana']['rgb'], G['ana']['a'], G['ana']['x'], G['ana']['y']
        k05 = kutu(s_a, 0.5)
        eb = (k05[2] - k05[0]) / (k05[3] - k05[1])
        s_bilgi = dict(olcek=G['ana']['olcek'], kutu_05=list(k05), en_boy_05=round(eb, 5), en_boy_fark=round(abs(eb - s_olc['en_boy_05']), 5),
                       boyut=[int(s_a.shape[1]), int(s_a.shape[0])], hedef=G['ana']['hedef'])
        grup_oge, grup_bilgi = G['ogeler'], G['bilgi']
    else:                                                                     # spiral: eski kural (SEMBOL_ORAN; grup yok)
        s_r = SEMBOL_ORAN * AY['sembol_alan'] * S
        s_rgb, s_a, s_x, s_y, s_bilgi = sembol_yerlestir(g, s_olc, s_r)
    # D_ana: ornament_motor.py :264-265, 552-553 (kaynak en fazla 1600 px genislikte olculur, yerlesen piksele cevrilir)
    kx0, ky0, kx1, ky1 = kutu(g[..., 3], 0.02)                                 # o1.kirp(ana0, alfa, pad=2)
    gk = g[max(0, ky0 - 2):ky1 + 2, max(0, kx0 - 2):kx1 + 2]
    a16 = gk[..., 3] if gk.shape[1] <= 1600 else rgba_olcek(gk, 1600 / gk.shape[1])[1]
    k16 = kutu(a16, 0.5)
    D_ana = yari_kal(a16) * (s_bilgi['kutu_05'][2] - s_bilgi['kutu_05'][0]) / (k16[2] - k16[0])
    del g, gk, a16
    log('sembol', s_olc['mod'], s_olc['boyut'], 'olcek', s_bilgi['olcek'], 'D_ana', round(D_ana, 3), 'grup', grup_bilgi and {k_: grup_bilgi[k_] for k_ in
        ('merkez', 'olcek', 'k', 'halka_merkez_kayma_px', 'halka_kalinlik_px')})
    # 3 renk haritasi
    hr = mt.harita_kur(cift, a.onbellek)
    har, qa_goz = hr['har'], hr['qa_goz']
    sure['kurulum'] = round(time.time() - t_, 1); t_ = time.time()
    # 4 yazi sekilleri (1x; son alfa)
    FI, FM = mt.font_isim, mt.font_metin
    isim_metni = f'{isim1} & {isim2}'
    Ai, ti, cap_isim, kuc = isim_sigdir(isim_metni, FI, cap0=AY['isim_cap'], cap_alt=AY['ay_adi_cap'], yumusak=deneme)
    denetle('isim_kucuk', cap_isim >= AY['ay_adi_cap'], f"isim buyuk harfi {cap_isim:.2f} px < {AY['ay_adi_cap']} px (isim satiri sigmiyor)")
    ogeler = [dict(ad='isimler', tur='isim', metin=isim_metni, font=FI, wght=500, ref='H', cap=cap_isim, A=Ai, taban=ti)]
    Ab, tb = metin_alfa(BASLIK, FI, AY['baslik_cap'], 500)
    ogeler.append(dict(ad='baslik', tur='baslik', metin=BASLIK, font=FI, wght=500, ref='H', cap=float(AY['baslik_cap']), A=Ab, taban=tb))
    for m, ay in enumerate(AYLAR):
        Am, tm = metin_alfa(ay, FI, AY['ay_adi_cap'], 500)
        ogeler.append(dict(ad=f'ay_{m + 1:02d}', tur='ay', metin=ay, font=FI, wght=500, ref='H', cap=float(AY['ay_adi_cap']), A=Am, taban=tm))
    genis = []
    for i, s in enumerate(satirlar):
        As, ts = metin_alfa(s, FM, AY['metin_cap'], None, ref='T')
        ks = kutu(As)
        if ks[2] - ks[0] > GEN_ORAN * W:
            genis.append(f'metin satiri {i + 1} genisligi {ks[2] - ks[0]} px > sayfanin %{int(GEN_ORAN * 100)}i (kucultulmez)')
        ogeler.append(dict(ad=f'metin_{i + 1}', tur='metin', metin=s, font=FM, wght=None, ref='T', cap=float(AY['metin_cap']), A=As, taban=ts))
    denetle('metin_genis', not genis, '; '.join(genis))
    for o in ogeler:
        o['kutu'] = kutu(o['A'])                                              # murekkep kutusu (cerceve ici)
        o['k'] = cizim_katsayisi(o['cap'])
    ay_oge = [o for o in ogeler if o['tur'] == 'ay']
    # 5 yerlesim + bosluk kapisi (analitik; mod ornek: tutmazsa YALNIZ disk katsayisi 0,01 adimla kuculur; mod deneme: katsayi dusmez)
    ay_kutu = [(o['kutu'][2] - o['kutu'][0], o['kutu'][3] - o['kutu'][1]) for o in ay_oge]
    ad_uzak, ad_arama = GIRDAP_AD_UZAK, None
    if yerlesim == 'girdap':
        if AY['girdap_ad_uzaklik'] == 'oto':                                  # arama yerlesim_bul'dan ONCE, baslangic katsayisinda
            ad_uzak, yd0 = girdap_ad_uzakligi(gunler, ay_kutu, AY['disk_katsayi'])
            ad_arama = dict(yontem='oto', uzaklik_ref=ad_uzak, katsayi=AY['disk_katsayi'], yazi_disk=yd0)
        else:
            ad_uzak = AY['girdap_ad_uzaklik']
            ad_arama = dict(yontem='ayar', uzaklik_ref=ad_uzak)
    try:
        Y, kat, iz = yerlesim_bul(yerlesim, gunler, ay_kutu, s_r, AY['disk_katsayi'], ad_uzak, dusur=not deneme)
    except Dur as e:
        if e.kod != 'bosluk':
            raise
        kontrol['bosluk'] = dict(PASS=False, neden=e.neden)
        raise
    denetle('bosluk', iz[-1]['PASS'], f'bosluk kapisi tutmuyor: {iz[-1]}')
    log('yerlesim', yerlesim, 'katsayi', kat, iz[-1], 'ad uzakligi', ad_arama)
    # 6 dikey yerlesim (karar 8): cember blogunun ust / alt siniri = diskler, ay adlari, rakamlar
    ust = [float(np.min(Y['disk'][:, 1] - Y['r_tot']))] + [y - gh / 2 for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
    alt = [float(np.max(Y['disk'][:, 1] + Y['r_tot']))] + [y + gh / 2 for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
    rakam = []
    for mtn, rx, ry in Y['rakam']:
        Ar, tr = metin_alfa(mtn, FI, CAP_RAKAM, 500)
        kr = kutu(Ar)
        rakam.append(dict(metin=mtn, A=Ar, x=rx, y=ry, kutu=kr))
        ust.append(ry - (kr[3] - kr[1]) / 2); alt.append(ry + (kr[3] - kr[1]) / 2)
    DY = dikey_yerlesim(cap_isim, min(ust), max(alt), len(satirlar), cap_baslik=AY['baslik_cap'], t_metin=AY['metin_cap'])
    cx, cy = W / 2.0, float(round(DY['cy']))
    denetle('dikey_sigmadi', DY['ust'] >= BOSLUK_KENAR and H - DY['alt'] >= BOSLUK_KENAR, f"blok {DY['blok']:.0f} px; ust bosluk {DY['ust']:.0f} px < {BOSLUK_KENAR}")

    def yerles(o, xc, taban_y=None, yc=None):
        """yatay: murekkep kutusu merkezi xc; dikey: taban cizgisi taban_y ya da murekkep kutusu merkezi yc (ay adlari)."""
        k_ = o['kutu']
        o['x'] = int(round(xc - (k_[0] + k_[2]) / 2.0))
        o['y'] = int(round(taban_y - o['taban'])) if taban_y is not None else int(round(yc - (k_[1] + k_[3]) / 2.0))
        o['taban_y'] = o['y'] + o['taban']
    yerles(ogeler[0], cx, DY['isim_taban'])
    yerles(ogeler[1], cx, DY['baslik_taban'])
    for o, (x, y) in zip(ay_oge, Y['ay_yeri']):
        yerles(o, cx + x, yc=cy + y)
    for o, ty in zip([q for q in ogeler if q['tur'] == 'metin'], DY['metin_taban']):
        yerles(o, cx, ty)
    sx, sy = int(round(cx)) + s_x, int(round(cy)) + s_y
    for o in grup_oge:                                                        # grup ogeleri: ana sembolle AYNI tam sayi merkezden
        o['x'], o['y'] = int(round(cx)) + o['x'], int(round(cy)) + o['y']
    tasan = [o['ad'] for o in ogeler + grup_oge
             if o['x'] < 0 or o['y'] < 0 or o['x'] + o['A'].shape[1] > W or o['y'] + o['A'].shape[0] > H]
    if sx < 0 or sy < 0 or sx + s_a.shape[1] > W or sy + s_a.shape[0] > H:
        raise Dur('tasma', 'sembol tuval disina tasiyor')
    for o in ogeler + grup_oge:
        if _kesisim(o['x'], o['y'], *o['A'].shape) is None:
            raise Dur('tasma', f"{o['ad']} tumuyle tuval disinda")
    denetle('tasma', not tasan, f"{', '.join(tasan)} tuval disina tasiyor")
    # 7 zemin (yeniden uretim; profil ve yildiz yolu es oranli olcek W / 7200, merkez = cember merkezi)
    Zp = json.load(open(mt.md / 'zemin_profil.json'))
    f_z = W / float(Zp['olcek'])
    zem = zemin_radyal(mt.md, mt.P, W, H, f_z, cx, cy)
    y_maske = np.zeros((H, W), np.uint8)
    ox, oy = cx - Zp['cx'] * f_z, cy - Zp['cy'] * f_z
    engel = np.zeros((H, W), np.uint8)                                        # yildiz konmayacak bolge: tum ogeler + pay (motor 61 px, tuvale oranli)
    for o in ogeler + grup_oge:
        y0, y1, x0, x1, ly, lx = _kesisim(o['x'], o['y'], *o['A'].shape)
        engel[y0:y1, x0:x1][o['A'][ly:ly + y1 - y0, lx:lx + x1 - x0] > 0.02] = 255
    engel[sy:sy + s_a.shape[0], sx:sx + s_a.shape[1]][s_a > 0.02] = 255
    for d_, rt_ in zip(Y['disk'], Y['r_tot']):
        cv2.circle(engel, (int(round(cx + d_[0])), int(round(cy + d_[1]))), int(math.ceil(rt_)), 255, -1)
    for r_ in rakam:
        k_ = r_['kutu']
        cv2.rectangle(engel, (int(cx + r_['x'] - (k_[2] - k_[0]) / 2), int(cy + r_['y'] - (k_[3] - k_[1]) / 2)),
                      (int(cx + r_['x'] + (k_[2] - k_[0]) / 2) + 1, int(cy + r_['y'] + (k_[3] - k_[1]) / 2) + 1), 255, -1)
    ek = int(round(61 * W / 7200.0)) | 1
    engel = cv2.dilate(engel, np.ones((ek, ek), np.uint8))
    ysay = {}
    n_yildiz = zemin_yildiz(zem, mt.md, mt.gm, f_z, ox, oy, y_maske, engel, ysay) if mt.P['yildiz'] == 'refkopya' else 0
    del engel
    img = zemin_8bit(zem, mt.gm, mt.P)
    del zem
    zemin_bilgi = dict(yontem='yeniden uretim: motor radyal profili ve yildiz yolu (refkopya), es oranli olcek, merkez = cember merkezi',
                       olcek_profil=round(f_z, 4), poster_orani=round(W / 7200.0, 4), merkez=[cx, cy], kayma=[round(ox, 1), round(oy, 1)],
                       yildiz=int(n_yildiz), yildiz_atlanan=dict(ogeye_degen=int(ysay.get('engel', 0)), tuval_disi=int(ysay.get('tuval_disi', 0))),
                       yildiz_engel_cekirdek_px=ek, yildizli_satir_araligi=[int(np.nonzero(y_maske.any(1))[0].min()), int(np.nonzero(y_maske.any(1))[0].max())] if n_yildiz else None,
                       yildizli_piksel_oran=round(float((y_maske > 0).mean()), 5),
                       zemin_profil_sha256=mt.sha['zemin_profil.json'], ref_sha256=mt.sha['ref/ref.png'])
    log('zemin', zemin_bilgi['olcek_profil'], 'yildiz', n_yildiz)
    sure['zemin'] = round(time.time() - t_, 1); t_ = time.time()
    # 8 altin disi ogeler: yorunge, diskler, rakamlar
    d_maske = np.zeros((H, W), np.uint8)       # ay diskleri (isaret halkasi dahil)
    e_maske = np.zeros((H, W), np.uint8)       # diger altin disi cizimler (yorunge, rakam)
    F = 16
    for R, a0, a1 in Y['yorunge']:                                            # yorunge yayi: ayin ilk gununden son gunune (yogun nokta, puruzsuz)
        t = np.radians(np.linspace(a0, a1, max(8, int(R * math.radians(a1 - a0) / 3))))
        pts = np.round(np.c_[cx + R * np.cos(t), cy + R * np.sin(t)] * F).astype(np.int32)
        cv2.polylines(img, [pts], False, RENK_YORUNGE, YORUNGE_KALIN, cv2.LINE_AA, 4)
        cv2.polylines(e_maske, [pts], False, 255, YORUNGE_KALIN + 2, cv2.LINE_8, 4)
    for i, gun in enumerate(gunler):
        disk_ciz(img, d_maske, cx + Y['disk'][i, 0], cy + Y['disk'][i, 1], Y['disk'][i, 2], gun['oran'], gun['buyuyor'], bool(Y['isaret'][i]))
    for r_ in rakam:
        k_ = r_['kutu']
        duz_yazi(img, e_maske, r_['A'], int(round(cx + r_['x'] - (k_[0] + k_[2]) / 2.0)), int(round(cy + r_['y'] - (k_[1] + k_[3]) / 2.0)), RENK_RAKAM)
    altinsiz = img.copy()
    sure['duz_cizim'] = round(time.time() - t_, 1); t_ = time.time()
    # 9 altin: sembol (dokunulmaz) + yazi ogeleri (ornament yolu) + grup ogeleri (halka, kucuk semboller; ayni yol)
    Lana = np.median(labf(s_rgb[s_a >= 0.9]), 0)                              # ornament_motor.py :516-518 (hedef: sembol katmani, alfa >= 0.9)
    altin = altin_ogeler(mt, ogeler + grup_oge, har, qa_goz, Lana, D_ana)
    for o, b_ in zip(ogeler + grup_oge, altin):                               # tuval disina tasan oge (yalniz mod deneme): tuval siniri keser, FAIL 'tasma'da
        y0, y1, x0, x1, ly, lx = _kesisim(o['x'], o['y'], *o['A'].shape)
        if (y1 - y0, x1 - x0) != o['A'].shape:
            dl = (slice(ly, ly + y1 - y0), slice(lx, lx + x1 - x0))
            o['A'], o['atest'] = np.ascontiguousarray(o['A'][dl]), np.ascontiguousarray(o['atest'][dl])
            o['x'], o['y'] = x0, y0
            b_.update(x=x0, y=y0, rgb=np.ascontiguousarray(b_['rgb'][dl]), m=o['A'])
    boya_oge = [dict(ad='sembol', x=sx, y=sy, rgb=s_rgb, m=s_a, ic=None, carpan=1.0)] + altin
    son = boya(img, boya_oge)
    del img
    sure['altin'] = round(time.time() - t_, 1); t_ = time.time()
    # 10 kayit: PNG (300 dpi, sRGB), onizleme, 1:1 kesitler, kapi icin DUMP + META
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    Image.fromarray(son).save(O / f'{ad}.png', dpi=(DPI, DPI), icc_profile=icc, compress_level=6)
    Image.fromarray(cv2.resize(son, (W // 4, H // 4), interpolation=cv2.INTER_AREA)).save(O / f'{ad}_onizleme.jpg', quality=92, subsampling=0, dpi=(DPI // 4, DPI // 4))

    def kes(x0, y0, x1, y1):
        return son[max(0, int(y0)):min(H, int(y1)), max(0, int(x0)):min(W, int(x1))]
    pay = 90
    # kesit 1: sembol grubunun tamami (grup yoksa sembol)
    gx0 = min([sx] + [o['x'] for o in grup_oge]); gy0 = min([sy] + [o['y'] for o in grup_oge])
    gx1 = max([sx + s_a.shape[1]] + [o['x'] + o['A'].shape[1] for o in grup_oge]); gy1 = max([sy + s_a.shape[0]] + [o['y'] + o['A'].shape[0] for o in grup_oge])
    Image.fromarray(kes(gx0 - pay, gy0 - pay, gx1 + pay, gy1 + pay)).save(O / f'{ad}_kesit1_sembol_grubu.png', dpi=(DPI, DPI))
    dar = int(np.argmin(iz[-1]['yazi_disk_ay']))
    if not deneme:
        # kesit 2: diske en yakin (en dar araligi olan) ay adi ve cevresi
        o_a = ay_oge[dar]
        Image.fromarray(kes(o_a['x'] - 420, o_a['y'] - 420, o_a['x'] + o_a['A'].shape[1] + 420, o_a['y'] + o_a['A'].shape[0] + 420)).save(
            O / f'{ad}_kesit2_ay_adi.png', dpi=(DPI, DPI))
        # kesit 3: kisisel metin; yoksa isimler + baslik
        mo = [q for q in ogeler if q['tur'] == 'metin']
        if mo:
            x0 = min(q['x'] for q in mo) - pay; x1 = max(q['x'] + q['A'].shape[1] for q in mo) + pay
            Image.fromarray(kes(x0, mo[0]['y'] - pay, x1, mo[-1]['y'] + mo[-1]['A'].shape[0] + pay)).save(O / f'{ad}_kesit3_metin.png', dpi=(DPI, DPI))
        else:
            o_i, o_b = ogeler[0], ogeler[1]
            Image.fromarray(kes(min(o_i['x'], o_b['x']) - pay, o_i['y'] - pay, max(o_i['x'] + o_i['A'].shape[1], o_b['x'] + o_b['A'].shape[1]) + pay,
                                o_b['y'] + o_b['A'].shape[0] + pay)).save(O / f'{ad}_kesit3_isim_baslik.png', dpi=(DPI, DPI))
    dump = dict(disk_maske=d_maske, diger_maske=e_maske, yildiz_maske=y_maske, sembol_a=s_a.astype(np.float32), sembol_rgb=s_rgb.astype(np.float32),
                altinsiz=altinsiz)
    for i, o in enumerate(ogeler):
        dump[f'm_{i}'] = o['A'].astype(np.float32); dump[f't_{i}'] = o['atest'].astype(np.float32)
    for i, o in enumerate(grup_oge):
        dump[f'gm_{i}'] = o['A'].astype(np.float32); dump[f'gt_{i}'] = o['atest'].astype(np.float32)
    np.savez_compressed(O / f'{ad}_DUMP.npz', **dump)
    sure['kayit'] = round(time.time() - t_, 1)
    meta = dict(
        ad=ad, mod=mod, ayar=AY, yerlesim=yerlesim, cift=cift, tuval=[W, H], dpi=DPI, sure_sn=round(time.time() - T0, 1), sure_adim=sure,
        uretim_kontrol=kontrol,
        veri=vk, sembol=dict(olcum=s_olc, yerlesim=s_bilgi, x=sx, y=sy, hedef_yaricap=s_r, D_ana=round(D_ana, 3),
                             islem='yalniz es oranli kucultme (on carpimli INTER_AREA); ic golge / dusus / onarim yok'),
        grup=None if grup_bilgi is None else dict(
            bilgi=grup_bilgi, merkez=[int(round(cx)), int(round(cy))],
            ogeler=[dict(ad=o['ad'], motor_ad=o['motor_ad'], x=o['x'], y=o['y'], gen=int(o['A'].shape[1]), yuk=int(o['A'].shape[0]), k=o['k'], olcek=o['olcek'],
                         hedef=o['hedef'], poster=o['poster'], uyum=o['uyum'], yari_kal=o['yari_kal'], ic_oran=o['ic_oran']) for o in grup_oge]),
        ogeler=[dict(ad=o['ad'], tur=o['tur'], x=o['x'], y=o['y'], gen=int(o['A'].shape[1]), yuk=int(o['A'].shape[0]), cap=round(o['cap'], 2),
                     k=o['k'], punto=o['punto'], taban_y=round(o['taban_y'], 2), karakter=len(o['metin']), uyum=o['uyum'],
                     yari_kal=o['yari_kal'], ic_oran=o['ic_oran']) for o in ogeler],
        isim=dict(harf=[len(isim1), len(isim2)], cap_baslangic=AY['isim_cap'], cap=round(cap_isim, 2), kuculme_orani=round(cap_isim / AY['isim_cap'], 4),
                  deneme=kuc, genislik=int(ogeler[0]['kutu'][2] - ogeler[0]['kutu'][0]), sinir=round(GEN_ORAN * W, 1)),
        metin=dict(satir=len(satirlar), karakter=[len(s) for s in satirlar]),
        disk=dict(katsayi_baslangic=AY['disk_katsayi'], katsayi=kat, iz=iz, n=int(len(gunler)), merkez=[cx, cy], bilgi=Y['bilgi'],
                  liste=[[round(float(cx + d[0]), 2), round(float(cy + d[1]), 2), round(float(d[2]), 3), round(float(rt), 3), i]
                         for i, (d, rt) in enumerate(zip(Y['disk'], Y['r_tot']))],          # x, y, r, dis yaricap, gun indeksi (yil sirasi)
                  ay_yeri=[[round(float(x), 1), round(float(y), 1)] for x, y in Y['ay_yeri']], en_dar_ay=dar + 1, girdap_ad=ad_arama),
        dikey={k: (v if isinstance(v, list) else round(float(v), 2)) for k, v in DY.items()},
        zemin=zemin_bilgi,
        altin=dict(yol='ornament yazi yolu (ornament-printful-katalog c950151627 ornament_motor.py), motor siparis-gpt 6da763a; '
                       'grup ogeleri ayni yol (Motor.oge_katman: cember / kucuk1 / kucuk2)',
                   k={o['ad']: o['k'] for o in ogeler + grup_oge}, esit='goz', dis_golge=DIS_GOLGE, ic_golge=IC_GOLGE, dusus_carpani=1.0,
                   dusus_not='ornament: kucuk ogelerde dusus = sembol ortanca carpani; sembol degismedigi icin 1,0',
                   kontrast_artisi='yok (karar 9)', dis_golge_not='tum altin ogelerin (sembol dahil) altina duser; sembol pikselleri degismez', Lana=[round(float(v), 2) for v in Lana], harita=hr['bilgi']),
        secilen=dict(G_ISIM_BASLIK=G_ISIM_BASLIK, G_BASLIK_CEMBER=G_BASLIK_CEMBER, G_CEMBER_METIN=G_CEMBER_METIN, CAP_RAKAM=CAP_RAKAM,
                     KENAR_CIZGI=KENAR_CIZGI, YORUNGE_KALIN=YORUNGE_KALIN, not_='Merkez metninde olmayan, bu betikte secilen degerler'),
        motor_sha256=mt.sha, kilit=mt.KILIT,
        paketler=dict(python=sys.version.split()[0], numpy=np.__version__, opencv=cv2.__version__, pillow=Image.__version__, raqm=raqm,
                      ephem=__import__('ephem').__version__))
    (O / f'{ad}_META.json').write_text(json.dumps(meta, indent=1, default=float))
    gs = '' if grup_bilgi is None else (f" | grup {grup_bilgi['merkez']} olcek {grup_bilgi['olcek']:.4f} ana {s_bilgi['olcek']:.4f} halka kayma {grup_bilgi['halka_merkez_kayma_px']} px "
                                        f"kalinlik {grup_bilgi['halka_kalinlik_px']} px ({grup_bilgi['halka_kalinlik_mm']} mm)")
    fl = sorted(k_ for k_, v in kontrol.items() if not v['PASS'])
    bildir(f'OZET {ad}', f"mod {mod} | yerlesim {yerlesim} | disk katsayisi {kat} (baslangic {AY['disk_katsayi']}) | isim buyuk harf {cap_isim:.1f} px "
                         f"(oran {cap_isim / AY['isim_cap']:.3f}) | metin {len(satirlar)} satir | k {sorted(set(o['k'] for o in ogeler + grup_oge))}{gs}"
                         f"{'' if ad_arama is None else ' | girdap ad uzakligi ' + str(ad_arama['uzaklik_ref']) + ' ref px'} | uretim kontrolu FAIL {fl} | "
                         f"zemin: yeniden uretim, olcek {f_z:.2f}, yildiz {n_yildiz} (ogeye degdigi icin atlanan {ysay.get('engel', 0)}) | sure {time.time() - T0:.0f} sn {sure}")
    return 0


def ayar_komut(a):
    """mod deneme girdi dogrulamasi: ayar metni ORTAM DEGISKENINDEN okunur (kabuk satirina girmez); gecerliyse TAM ayar listesi
    <cikti>/AYAR.json, deneme sayisi <cikti>/AYAR_N.txt (yalniz rakam) ve cikti adlari <cikti>/AYAR_AD.txt (DENEME_<sira>_<yerlesim>) yazilir. Gecersizse hicbir sey yazilmaz, cikis 3."""
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    L = ayar_listesi(os.environ.get(a.env, ''))
    (O / 'AYAR.json').write_text(json.dumps(L, indent=1))
    (O / 'AYAR_N.txt').write_text(str(len(L)))
    (O / 'AYAR_AD.txt').write_text(''.join(f"DENEME_{i}_{d['yerlesim']}\n" for i, d in enumerate(L, 1)))   # cikti adlari KODDAN (girdiden degil)
    bildir('AYAR', f"{len(L)} deneme | yerlesim {[d['yerlesim'] for d in L]}")
    return 0


def sembol_komut(a):
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    olc = {}
    try:
        _, olc = sembol_yukle(a.katman)
        return 0
    except Dur as e:
        olc = dict(olc, hata=f'{e.kod}: {e.neden}')
        try:                                                                  # bicim hatasinda da olcum yazilir (mod, boyut)
            im = Image.open(a.katman); olc.update(mod=im.mode, boyut=list(im.size))
        except Exception:                                                     # noqa: BLE001
            pass
        raise
    finally:
        (O / 'SEMBOL_OLCUM.json').write_text(json.dumps(olc, indent=1))
        bildir('SEMBOL', ' | '.join(f'{k} {olc[k]}' for k in ('mod', 'boyut', 'kutu_alfa_05', 'kutu_alfa_002', 'cevre_yaricap_05', 'en_boy_05', 'olcek',
                                                             'yan_json_alanlar', 'hata') if k in olc))


def deneme_komut(a):
    """YALNIZ yerel deneme: motor dalindaki ana alfanin motorla golgelenmis hali. Dosya adi DENEME ile baslar; yuklenmez, push edilmez."""
    cift = cift_dogrula(a.cift)
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    mt = Motor(a.motor)
    Ya, Aa, bilgi = mt.poster_ana(cift)
    cm = cv2.erode((Aa > 0.99).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    har = mt.gm.renk_haritasi_dogrusal(Ya[cm], mt.ref_ana)
    rgb = np.clip(mt.gm.uygula_harita2(Ya, har) * 255, 0, 255)
    Ak = cv2.GaussianBlur(Aa, (0, 0), mt.P['kenar_yum']) if mt.P['kenar_yum'] else Aa
    rgba = np.dstack([np.round(rgb), np.round(Ak * 255)]).astype(np.uint8)
    pay = 150
    rgba = np.pad(rgba, ((pay, pay), (pay, pay), (0, 0)))
    f = O / f'DENEME_{cift}_ana.png'
    Image.fromarray(rgba, 'RGBA').save(f)
    Path(str(f) + '.json').write_text(json.dumps(dict(x=0, y=0, w=int(rgba.shape[1]), h=int(rgba.shape[0]), kaynak_x=pay, kaynak_y=pay,
                                                        kaynak_w=int(rgba.shape[1] - 2 * pay), kaynak_h=int(rgba.shape[0] - 2 * pay), pay=pay, deneme=True)))
    log('deneme sembolu', f, rgba.shape, bilgi)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='ay takvimi ornek uretimi')
    sp = ap.add_subparsers(dest='komut', required=True)
    p = sp.add_parser('sembol'); p.add_argument('--katman', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('uret')
    for k_ in ('cift', 'katman', 'motor', 'cikti'):
        p.add_argument('--' + k_, required=True)
    for k_ in ('isim1', 'isim2', 'yerlesim', 'ad'):
        p.add_argument('--' + k_)
    p.add_argument('--satir', action='append', default=[]); p.add_argument('--onbellek')
    p.add_argument('--grup-merkez', dest='grup_merkez'); p.add_argument('--mod', default='ornek')
    p.add_argument('--ayar'); p.add_argument('--ayar-dosya', dest='ayar_dosya'); p.add_argument('--sira', type=int)
    p = sp.add_parser('ayar-dogrula'); p.add_argument('--env', default='AY_TAKVIM_AYAR'); p.add_argument('--cikti', required=True)
    p = sp.add_parser('deneme'); p.add_argument('--cift', required=True); p.add_argument('--motor', required=True); p.add_argument('--cikti', required=True)
    a = ap.parse_args(argv)
    try:
        return {'sembol': sembol_komut, 'uret': uret, 'deneme': deneme_komut, 'ayar-dogrula': ayar_komut}[a.komut](a)
    except Dur as e:
        kod = 3 if e.girdi else 4
        ad = getattr(a, 'ad', None) or (f'DENEME_{a.sira}' if getattr(a, 'sira', None) else a.komut)
        if not re.fullmatch(r'[A-Za-z0-9_\-]{1,60}', ad):                     # gecersiz ad girdisi log satirina / dosya adina girmez
            ad = a.komut
        bildir('DUR', f"{ad}: {e.kod}: {e.neden} (cikis {kod})")
        try:
            O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
            (O / f"{ad}_DUR.json").write_text(json.dumps(dict(kod=e.kod, neden=e.neden, girdi_hatasi=e.girdi, cikis=kod), indent=1))
        except Exception:                                                     # noqa: BLE001
            pass
        return kod


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001  (cikis 2 = cokus, tam traceback)
        traceback.print_exc()
        print('::error title=COKUS::ay_takvim_ornek beklenmeyen hata (cikis 2)', flush=True)
        sys.exit(2)
