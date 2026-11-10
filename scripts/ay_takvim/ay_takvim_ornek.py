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

Kullanim:
  ay_takvim_ornek.py sembol --katman K.png --cikti D                       katman olcumu + bicim kapisi (SEMBOL_OLCUM.json)
  ay_takvim_ornek.py uret --cift CANCER_LIBRA --isim1 A --isim2 B --yerlesim halkalar [--satir "..."]x0-3
                          --katman K.png --motor MD --cikti D --ad ORNEK_1_halkalar [--onbellek DIR]
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
AYLAR = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')
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
YERLESIM = dict(halkalar=dict(katsayi=0.36, sembol_alan=205), spiral=dict(katsayi=0.36, sembol_alan=205),
                girdap=dict(katsayi=0.36, sembol_alan=205), rozet=dict(katsayi=0.34, sembol_alan=320))
KATSAYI_ADIM, KATSAYI_ALT = 0.01, 0.20
MOTOR_DOSYA = ('KILIT_GPTGIRDI.json', 'golge_motor.py', 'vektor_yuzey.py', 'alfa_temizle.py', 'kure/k4.npy', 'palet/chatgpt_altin.png',
               'yerlesim78.json', 'cember.json', 'zemin_profil.json', 'ref/ref.png', 'font/Cinzel.ttf', 'font/EBGaramond-Italic.ttf')
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


def yerlesim_kur(ad, gunler, katsayi):
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
        for m in range(1, 13):                                               # ay adi: kolun dis ucunda, son gun diskinin 58 px otesinde (kol tegeti yonunde)
            rs = r0 + (gunler[ay_son[m - 1]]['gun'] - 1) * (r1 - r0) / 30
            ps, pt = nokta(m, rs), nokta(m, rs + 0.01)
            tx, ty = pt[0] - ps[0], pt[1] - ps[1]
            tn = math.hypot(tx, ty)
            yer.append(((ps[0] + 58 * tx / tn) * S, (ps[1] + 58 * ty / tn) * S))
        out['ay_yeri'] = yer
        out['bilgi'] = dict(b=b, aralik=aralik, r_disk_ref=r_disk)
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
        raise Dur('girdi_yerlesim', f'bilinmeyen yerlesim {ad!r}', girdi=True)
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


def yerlesim_bul(ad, gunler, ay_kutu, sembol_r, katsayi=None):
    """Kapi 6 (analitik on kontrol): bosluklar tutmuyorsa YALNIZ o yerlesimin disk katsayisi 0,01 adimla kuculur; baska hicbir sayi
    (yaricap, aci, yazi boyu, sembol orani) degismez. Doner (yerlesim, katsayi, iz). KATSAYI_ALT altina inerse DUR."""
    kat = YERLESIM[ad]['katsayi'] if katsayi is None else katsayi
    iz = []
    while True:
        Y = yerlesim_kur(ad, gunler, kat)
        dd, _ = disk_disk_bosluk(Y['disk'], Y['r_tot'])
        if Y['ay_yeri'] is None:
            Y['ay_yeri'] = spiral_ay_yeri(Y, ay_kutu, sembol_r, W / 2 - BOSLUK_KENAR)
        yd = [kutu_disk_bosluk((x - gw / 2, y - gh / 2, x + gw / 2, y + gh / 2), Y['disk'], Y['r_tot']) for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
        sd = float(np.min(np.hypot(Y['disk'][:, 0], Y['disk'][:, 1]) - Y['r_tot']) - sembol_r)
        iz.append(dict(katsayi=round(kat, 2), disk_disk=round(dd, 2), yazi_disk=round(min(yd), 2), sembol_disk=round(sd, 2)))
        if dd >= BOSLUK_DISK_DISK and min(yd) >= BOSLUK_YAZI_DISK and sd >= BOSLUK_SEMBOL_DISK:
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


def isim_sigdir(metin, font_yolu, sinir=None, cap0=CAP_ISIM, cap_alt=CAP_AY):
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
        if cap < cap_alt:
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
    ogeler: dict(ad, metin, font, wght, ref, cap, k, A (1x alfa), x, y). Ogelere punto, atest, uyum, yari_kal, ic_oran yazar. Doner boya listesi."""
    rng = np.random.default_rng(11)
    out = []
    for o in ogeler:
        t1 = time.time()
        a_k, pt = metin_alfa_k(o['metin'], o['font'], o['cap'], o['k'], o['wght'], o['ref'])
        if a_k.shape != (o['A'].shape[0] * o['k'], o['A'].shape[1] * o['k']):
            raise Dur('cerceve', f"{o['ad']}: k kat cerceve 1x cercevenin tam kati degil")       # ornament_motor.py :409-411
        kat_g, _, atest = mt.oge_katman(a_k, o['k'], rng, har, qa_goz)
        kat_u, uy = renk_uyum(kat_g, o['A'], Lana)
        yk = yari_kal(a_k) / o['k']
        r_ = min(1.0, yk / D_ana)
        o.update(punto=pt, atest=atest, uyum=uy, yari_kal=round(yk, 3), ic_oran=round(r_, 4))
        out.append(dict(ad=o['ad'], x=o['x'], y=o['y'], rgb=kat_u, m=o['A'],
                        ic=dict(kayma=IC_GOLGE['kayma'] * r_, sigma=IC_GOLGE['sigma'] * r_, guc=IC_GOLGE['guc']), carpan=1.0))
        log(f"oge {o['ad']:9s} k {o['k']} cap {o['cap']:.1f} cerceve {a_k.shape} piksel {uy['piksel']} dE {uy['dE00_once']}->{uy['dE00_sonra']} {time.time() - t1:.1f}s")
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
    olc['olcek'] = {ad: round(SEMBOL_ORAN * v['sembol_alan'] * S / r, 5) for ad, v in YERLESIM.items()}
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
def uret(a):
    cift = cift_dogrula(a.cift)
    isim1, isim2 = isim_dogrula(a.isim1, 'isim1'), isim_dogrula(a.isim2, 'isim2')
    satirlar = metin_dogrula(a.satir)
    if a.yerlesim not in YERLESIM:
        raise Dur('girdi_yerlesim', f'bilinmeyen yerlesim {a.yerlesim!r}', girdi=True)
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', a.ad or ''):
        raise Dur('girdi_ad', 'cikti adi yalniz harf / rakam / alt cizgi', girdi=True)
    O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    raqm = bool(features.check('raqm'))
    if Image.__version__ != '11.0.0' or not raqm:
        raise Dur('ortam', f'pillow {Image.__version__} raqm {raqm}; ornament ortami pillow 11.0.0 + raqm acik olmali')
    # 1 veri
    gunler = ay_verisi(YIL)
    vk = veri_kapisi(gunler)
    if not vk['PASS']:
        raise Dur('veri', json.dumps(vk))
    # 2 sembol (olcum kapilardan ONCE yazilir)
    g, s_olc = sembol_yukle(a.katman)
    (O / f'{a.ad}_SEMBOL_OLCUM.json').write_text(json.dumps(s_olc, indent=1))
    YA = YERLESIM[a.yerlesim]
    s_rgb, s_a, s_x, s_y, s_bilgi = sembol_yerlestir(g, s_olc, SEMBOL_ORAN * YA['sembol_alan'] * S)
    s_r = SEMBOL_ORAN * YA['sembol_alan'] * S
    # D_ana: ornament_motor.py :264-265, 552-553 (kaynak en fazla 1600 px genislikte olculur, yerlesen piksele cevrilir)
    kx0, ky0, kx1, ky1 = kutu(g[..., 3], 0.02)                                 # o1.kirp(ana0, alfa, pad=2)
    gk = g[max(0, ky0 - 2):ky1 + 2, max(0, kx0 - 2):kx1 + 2]
    a16 = gk[..., 3] if gk.shape[1] <= 1600 else rgba_olcek(gk, 1600 / gk.shape[1])[1]
    k16 = kutu(a16, 0.5)
    D_ana = yari_kal(a16) * (s_bilgi['kutu_05'][2] - s_bilgi['kutu_05'][0]) / (k16[2] - k16[0])
    del g, gk, a16
    log('sembol', s_olc['mod'], s_olc['boyut'], 'olcek', s_bilgi['olcek'], 'D_ana', round(D_ana, 3))
    # 3 motor + renk haritasi
    mt = Motor(a.motor)
    hr = mt.harita_kur(cift, a.onbellek)
    har, qa_goz = hr['har'], hr['qa_goz']
    # 4 yazi sekilleri (1x; son alfa)
    FI, FM = mt.font_isim, mt.font_metin
    isim_metni = f'{isim1} & {isim2}'
    Ai, ti, cap_isim, kuc = isim_sigdir(isim_metni, FI)
    ogeler = [dict(ad='isimler', tur='isim', metin=isim_metni, font=FI, wght=500, ref='H', cap=cap_isim, A=Ai, taban=ti)]
    Ab, tb = metin_alfa(BASLIK, FI, CAP_BASLIK, 500)
    ogeler.append(dict(ad='baslik', tur='baslik', metin=BASLIK, font=FI, wght=500, ref='H', cap=float(CAP_BASLIK), A=Ab, taban=tb))
    for m, ay in enumerate(AYLAR):
        Am, tm = metin_alfa(ay, FI, CAP_AY, 500)
        ogeler.append(dict(ad=f'ay_{m + 1:02d}', tur='ay', metin=ay, font=FI, wght=500, ref='H', cap=float(CAP_AY), A=Am, taban=tm))
    for i, s in enumerate(satirlar):
        As, ts = metin_alfa(s, FM, T_METIN, None, ref='T')
        ks = kutu(As)
        if ks[2] - ks[0] > GEN_ORAN * W:
            raise Dur('metin_genis', f'metin satiri {i + 1} genisligi {ks[2] - ks[0]} px > sayfanin %{int(GEN_ORAN * 100)}i (kucultulmez)')
        ogeler.append(dict(ad=f'metin_{i + 1}', tur='metin', metin=s, font=FM, wght=None, ref='T', cap=float(T_METIN), A=As, taban=ts))
    for o in ogeler:
        o['kutu'] = kutu(o['A'])                                              # murekkep kutusu (cerceve ici)
        o['k'] = cizim_katsayisi(o['cap'])
    ay_oge = [o for o in ogeler if o['tur'] == 'ay']
    # 5 yerlesim + bosluk kapisi (analitik; tutmazsa YALNIZ disk katsayisi 0,01 adimla kuculur)
    ay_kutu = [(o['kutu'][2] - o['kutu'][0], o['kutu'][3] - o['kutu'][1]) for o in ay_oge]
    Y, kat, iz = yerlesim_bul(a.yerlesim, gunler, ay_kutu, s_r)
    log('yerlesim', a.yerlesim, 'katsayi', kat, iz[-1])
    # 6 dikey yerlesim (karar 8): cember blogunun ust / alt siniri = diskler, ay adlari, rakamlar
    ust = [float(np.min(Y['disk'][:, 1] - Y['r_tot']))] + [y - gh / 2 for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
    alt = [float(np.max(Y['disk'][:, 1] + Y['r_tot']))] + [y + gh / 2 for (x, y), (gw, gh) in zip(Y['ay_yeri'], ay_kutu)]
    rakam = []
    for mtn, rx, ry in Y['rakam']:
        Ar, tr = metin_alfa(mtn, FI, CAP_RAKAM, 500)
        kr = kutu(Ar)
        rakam.append(dict(metin=mtn, A=Ar, x=rx, y=ry, kutu=kr))
        ust.append(ry - (kr[3] - kr[1]) / 2); alt.append(ry + (kr[3] - kr[1]) / 2)
    DY = dikey_yerlesim(cap_isim, min(ust), max(alt), len(satirlar))
    cx, cy = W / 2.0, float(round(DY['cy']))
    if DY['ust'] < BOSLUK_KENAR or H - DY['alt'] < BOSLUK_KENAR:
        raise Dur('dikey_sigmadi', f"blok {DY['blok']:.0f} px; ust bosluk {DY['ust']:.0f} px < {BOSLUK_KENAR}")

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
    for o in ogeler:
        h_, w_ = o['A'].shape
        if o['x'] < 0 or o['y'] < 0 or o['x'] + w_ > W or o['y'] + h_ > H:
            raise Dur('tasma', f"{o['ad']} tuval disina tasiyor")
    # 7 zemin (yeniden uretim; profil ve yildiz yolu es oranli olcek W / 7200, merkez = cember merkezi)
    Zp = json.load(open(mt.md / 'zemin_profil.json'))
    f_z = W / float(Zp['olcek'])
    zem = zemin_radyal(mt.md, mt.P, W, H, f_z, cx, cy)
    y_maske = np.zeros((H, W), np.uint8)
    ox, oy = cx - Zp['cx'] * f_z, cy - Zp['cy'] * f_z
    sx, sy = int(round(cx)) + s_x, int(round(cy)) + s_y
    engel = np.zeros((H, W), np.uint8)                                        # yildiz konmayacak bolge: tum ogeler + pay (motor 61 px, tuvale oranli)
    for o in ogeler:
        sl = engel[o['y']:o['y'] + o['A'].shape[0], o['x']:o['x'] + o['A'].shape[1]]
        sl[o['A'] > 0.02] = 255
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
    # 9 altin: sembol (dokunulmaz) + yazi ogeleri (ornament yolu)
    Lana = np.median(labf(s_rgb[s_a >= 0.9]), 0)                              # ornament_motor.py :516-518 (hedef: sembol katmani, alfa >= 0.9)
    boya_oge = [dict(ad='sembol', x=sx, y=sy, rgb=s_rgb, m=s_a, ic=None, carpan=1.0)] + altin_ogeler(mt, ogeler, har, qa_goz, Lana, D_ana)
    son = boya(img, boya_oge)
    del img
    # 10 kayit: PNG (300 dpi, sRGB), onizleme, 1:1 kesitler, kapi icin DUMP + META
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    Image.fromarray(son).save(O / f'{a.ad}.png', dpi=(DPI, DPI), icc_profile=icc, compress_level=6)
    Image.fromarray(cv2.resize(son, (W // 4, H // 4), interpolation=cv2.INTER_AREA)).save(O / f'{a.ad}_onizleme.jpg', quality=92, subsampling=0, dpi=(DPI // 4, DPI // 4))

    def kes(x0, y0, x1, y1):
        return son[max(0, int(y0)):min(H, int(y1)), max(0, int(x0)):min(W, int(x1))]
    o_i = ogeler[0]; pay = 90
    ust_k = kes(o_i['x'] - pay, o_i['y'] - pay, o_i['x'] + o_i['A'].shape[1] + pay, ogeler[1]['y'] + ogeler[1]['A'].shape[0] + pay)
    alt_k = kes(sx - pay, sy - pay, sx + s_a.shape[1] + pay, sy + s_a.shape[0] + pay)
    gen = max(ust_k.shape[1], alt_k.shape[1])
    bir = np.zeros((ust_k.shape[0] + alt_k.shape[0] + 12, gen, 3), np.uint8)
    bir[:ust_k.shape[0], :ust_k.shape[1]] = ust_k; bir[ust_k.shape[0] + 12:, :alt_k.shape[1]] = alt_k
    Image.fromarray(bir).save(O / f'{a.ad}_kesit1_sembol_isimler.png', dpi=(DPI, DPI))
    o_a = ay_oge[0]
    Image.fromarray(kes(o_a['x'] - 420, o_a['y'] - 420, o_a['x'] + o_a['A'].shape[1] + 420, o_a['y'] + o_a['A'].shape[0] + 420)).save(
        O / f'{a.ad}_kesit2_ay_adi.png', dpi=(DPI, DPI))
    mo = [q for q in ogeler if q['tur'] == 'metin']
    if mo:
        x0 = min(q['x'] for q in mo) - pay; x1 = max(q['x'] + q['A'].shape[1] for q in mo) + pay
        Image.fromarray(kes(x0, mo[0]['y'] - pay, x1, mo[-1]['y'] + mo[-1]['A'].shape[0] + pay)).save(O / f'{a.ad}_kesit3_metin.png', dpi=(DPI, DPI))
    else:
        o_b = ogeler[1]
        Image.fromarray(kes(o_b['x'] - pay, o_b['y'] - pay, o_b['x'] + o_b['A'].shape[1] + pay, o_b['y'] + o_b['A'].shape[0] + pay)).save(
            O / f'{a.ad}_kesit3_baslik.png', dpi=(DPI, DPI))
    dump = dict(disk_maske=d_maske, diger_maske=e_maske, yildiz_maske=y_maske, sembol_a=s_a.astype(np.float32), sembol_rgb=s_rgb.astype(np.float32),
                altinsiz=altinsiz)
    for i, o in enumerate(ogeler):
        dump[f'm_{i}'] = o['A'].astype(np.float32); dump[f't_{i}'] = o['atest'].astype(np.float32)
    np.savez_compressed(O / f'{a.ad}_DUMP.npz', **dump)
    meta = dict(
        ad=a.ad, yerlesim=a.yerlesim, cift=cift, tuval=[W, H], dpi=DPI, sure_sn=round(time.time() - T0, 1),
        veri=vk, sembol=dict(olcum=s_olc, yerlesim=s_bilgi, x=sx, y=sy, hedef_yaricap=s_r, D_ana=round(D_ana, 3),
                             islem='yalniz es oranli kucultme (on carpimli INTER_AREA); ic golge / dusus / onarim yok'),
        ogeler=[dict(ad=o['ad'], tur=o['tur'], x=o['x'], y=o['y'], gen=int(o['A'].shape[1]), yuk=int(o['A'].shape[0]), cap=round(o['cap'], 2),
                     k=o['k'], punto=o['punto'], taban_y=round(o['taban_y'], 2), karakter=len(o['metin']), uyum=o['uyum'],
                     yari_kal=o['yari_kal'], ic_oran=o['ic_oran']) for o in ogeler],
        isim=dict(harf=[len(isim1), len(isim2)], cap_baslangic=CAP_ISIM, cap=round(cap_isim, 2), kuculme_orani=round(cap_isim / CAP_ISIM, 4),
                  deneme=kuc, genislik=int(ogeler[0]['kutu'][2] - ogeler[0]['kutu'][0]), sinir=round(GEN_ORAN * W, 1)),
        metin=dict(satir=len(satirlar), karakter=[len(s) for s in satirlar]),
        disk=dict(katsayi_baslangic=YA['katsayi'], katsayi=kat, iz=iz, n=int(len(gunler)), merkez=[cx, cy], bilgi=Y['bilgi'],
                  liste=[[round(float(cx + d[0]), 2), round(float(cy + d[1]), 2), round(float(d[2]), 3), round(float(rt), 3), i]
                         for i, (d, rt) in enumerate(zip(Y['disk'], Y['r_tot']))],          # x, y, r, dis yaricap, gun indeksi (yil sirasi)
                  ay_yeri=[[round(float(x), 1), round(float(y), 1)] for x, y in Y['ay_yeri']]),
        dikey={k: (v if isinstance(v, list) else round(float(v), 2)) for k, v in DY.items()},
        zemin=zemin_bilgi,
        altin=dict(yol='ornament yazi yolu (ornament-printful-katalog c950151627 ornament_motor.py), motor siparis-gpt 6da763a',
                   k={o['ad']: o['k'] for o in ogeler}, esit='goz', dis_golge=DIS_GOLGE, ic_golge=IC_GOLGE, dusus_carpani=1.0,
                   dusus_not='ornament: kucuk ogelerde dusus = sembol ortanca carpani; sembol degismedigi icin 1,0',
                   kontrast_artisi='yok (karar 9)', dis_golge_not='tum altin ogelerin (sembol dahil) altina duser; sembol pikselleri degismez', Lana=[round(float(v), 2) for v in Lana], harita=hr['bilgi']),
        secilen=dict(G_ISIM_BASLIK=G_ISIM_BASLIK, G_BASLIK_CEMBER=G_BASLIK_CEMBER, G_CEMBER_METIN=G_CEMBER_METIN, CAP_RAKAM=CAP_RAKAM,
                     KENAR_CIZGI=KENAR_CIZGI, YORUNGE_KALIN=YORUNGE_KALIN, not_='Merkez metninde olmayan, bu betikte secilen degerler'),
        motor_sha256=mt.sha, kilit=mt.KILIT,
        paketler=dict(python=sys.version.split()[0], numpy=np.__version__, opencv=cv2.__version__, pillow=Image.__version__, raqm=raqm,
                      ephem=__import__('ephem').__version__))
    (O / f'{a.ad}_META.json').write_text(json.dumps(meta, indent=1, default=float))
    bildir(f'OZET {a.ad}', f"yerlesim {a.yerlesim} | disk katsayisi {kat} (baslangic {YA['katsayi']}) | isim buyuk harf {cap_isim:.1f} px "
                           f"(oran {cap_isim / CAP_ISIM:.3f}) | metin {len(satirlar)} satir | k {sorted(set(o['k'] for o in ogeler))} | "
                           f"zemin: yeniden uretim, olcek {f_z:.2f}, yildiz {n_yildiz} (ogeye degdigi icin atlanan {ysay.get('engel', 0)}) | sure {time.time() - T0:.0f} sn")
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
    Path(str(f) + '.json').write_text(json.dumps(dict(x=0, y=0, w=int(rgba.shape[1]), h=int(rgba.shape[0]), pay=pay, deneme=True)))
    log('deneme sembolu', f, rgba.shape, bilgi)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='ay takvimi ornek uretimi')
    sp = ap.add_subparsers(dest='komut', required=True)
    p = sp.add_parser('sembol'); p.add_argument('--katman', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('uret')
    for k_ in ('cift', 'isim1', 'isim2', 'yerlesim', 'katman', 'motor', 'cikti', 'ad'):
        p.add_argument('--' + k_, required=True)
    p.add_argument('--satir', action='append', default=[]); p.add_argument('--onbellek')
    p = sp.add_parser('deneme'); p.add_argument('--cift', required=True); p.add_argument('--motor', required=True); p.add_argument('--cikti', required=True)
    a = ap.parse_args(argv)
    try:
        return dict(sembol=sembol_komut, uret=uret, deneme=deneme_komut)[a.komut](a)
    except Dur as e:
        kod = 3 if e.girdi else 4
        bildir('DUR', f"{getattr(a, 'ad', a.komut)}: {e.kod}: {e.neden} (cikis {kod})")
        try:
            O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
            (O / f"{getattr(a, 'ad', a.komut)}_DUR.json").write_text(json.dumps(dict(kod=e.kod, neden=e.neden, girdi_hatasi=e.girdi, cikis=kod), indent=1))
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
