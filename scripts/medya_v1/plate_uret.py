#!/usr/bin/env python3
"""MEDYAN PLATE URETIMI (Serdar onayi 25 Eyl 2026).

Her (edisyon, boy) icin 78 ciftin POD_PRINT dosyasinin PIKSEL ORTANCASI =
yazisiz temiz zemin. Cift basina degisen ogeler (sembol, glif, isim, tagline)
78 dosyada farkli yerlerde oldugu icin ortancada yok olur.

SALT OKUR girdi: POD_PRINT'e yazma yok, Etsy/Prodigi yok, render kodu cagrilmaz.
Cikti: gdrive TEMP/SIPARIS_ISIM/PLATES/<EDISYON>_<BOY>.png (tam cozunurluk, PNG)
       + PLATES/RAPOR_<parca>.json (her plate icin p50/p99).

BELLEK: 78 dosyanin tam sayfa yigini 30x40 icin 25.3 GB olur; RAM'e sigmaz.
Sayfa SATIR KAROLARINA bolunur, her karo icin dosyalar yeniden cozulur ve
ortanca o karoda alinir. Karo yuksekligi YIGIN_AZAMI_GB'ye gore secilir.
Ortanca `np.partition` ile uint8 uzerinde alinir (np.median float64'e yukseltip
bellegi ~8 katina cikarir).

PARALELLIK: `--parca i/n` is listesini boler. Her parca ayri matris isi olarak
kosar; boylece her is 45 dk sinirinin altinda kalir.
"""
import argparse, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_plate').resolve(); W.mkdir(exist_ok=True)

RENK_ED = {'MIDNIGHT_BLUE': 'blue', 'DEEP_BLACK': 'black', 'PURE_WHITE': 'pure_white',
           'CHAMPAGNE_IVORY': 'modern', 'WARM_PARCHMENT': 'vintage'}
# SATILAN BOYLAR (Serdar karari 25 Eyl, 4. madde). Tek kaynak:
# scripts/etsy/pod_listing_create.py SIZE_SPEC -> ilan metni "13 SIZES".
# order_router.TUM_BOYLAR bunu "13 mevcut + 5x7 + A1" diye ayirir; 5x7 ve A1
# satilmadigi icin plate uretilmez. Dijital paketin bes boyu (16x20, 18x24,
# 24x36, 11x14, A2) zaten bu listenin icinde.
# POD_PRINT'te >=40 dosyasi olan boylar (kosu 36159554453 is listesi: 15 boy
# x 5 edisyon = 75 plate). 5x7 satilmiyor (Serdar 25 Eyl), disarida birakildi.
# Dijital paketin bes boyu (16x20, 18x24, 24x36, 11x14, A2) bu listenin icinde.
# NOT: Serdar 16 boy bildirdi ve kaynak olarak scripts/pod/fiyat_b.py'yi gosterdi;
# o dosya hicbir dalda yok, POD_PRINT'te de 15 boy var. Fark raporlandi.
ATLANAN = ('5x7',)
YIGIN_AZAMI_GB = 6.0      # karo yigini icin tepe bellek butcesi
ASGARI_DOSYA = 40         # bu sayidan az dosya varsa ortanca guvenilmez
FARK_ESIK = 30            # murekkep cekirdegi (p50/p99 raporu icin)
FARK_GENIS = 12
ORNEK = 3                 # p50/p99 raporu icin kac cift


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:7.1f}s]",
          *a, flush=True)


def rc(*a, timeout=2400):
    r = subprocess.run(['rclone', '--timeout', '180s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def mevcut_plateler():
    """PLATES'te zaten olan plate'ler - kosu 45 dk sinirinda kesilirse devam
    edilebilsin diye (kosu 36159554453 boyle kesildi)."""
    try:
        return {x.strip() for x in rc('lsf', PLATES, '--include', '*.png',
                                      '--files-only', timeout=300).split()}
    except RuntimeError:
        return set()


def is_listesi():
    """POD_PRINT'i tek listede tarayip gercek (renk, boy) matrisini cikarir."""
    sayac = {}
    for satir in rc('lsf', POD, '-R', '--include', '*.jpg', '--files-only').split():
        p = satir.split('/')
        if len(p) != 3:
            continue
        _cift, renk, dosya = p
        if renk not in RENK_ED or not dosya.endswith('.jpg'):
            continue
        sayac.setdefault((renk, dosya[:-4]), 0)
        sayac[(renk, dosya[:-4])] += 1
    isler = sorted(k for k, v in sayac.items()
                   if v >= ASGARI_DOSYA and k[1] not in ATLANAN)
    return isler, {f'{r}/{b}': v for (r, b), v in sorted(sayac.items())}


def indir(renk, boy):
    hed = W / f'{renk}_{boy}'
    hed.mkdir(exist_ok=True)
    if not list(hed.glob('*.jpg')):
        rc('copy', POD, str(hed / '_ham'), '--include', f'*/{renk}/{boy}.jpg',
           '--transfers', '8')
        for src in (hed / '_ham').glob(f'*/{renk}/{boy}.jpg'):
            src.replace(hed / f'{src.parent.parent.name}.jpg')
    return sorted(hed.glob('*.jpg'))


def karo_ortanca(yollar, tam_px, satir):
    """Satir karolarinda ortanca. Her karo icin dosyalar yeniden cozulur."""
    Wd, H = tam_px
    n = len(yollar)
    k = n // 2
    plate = np.empty((H, Wd, 3), np.uint8)
    karo = max(int(YIGIN_AZAMI_GB * 1e9 / (n * Wd * 3)), 64)
    sayi = (H + karo - 1) // karo
    log(f'  karo {karo} satir x {sayi} gecis (yigin {n * karo * Wd * 3 / 1e9:.2f} GB)')
    for t, y0 in enumerate(range(0, H, karo)):
        y1 = min(y0 + karo, H)
        yig = np.empty((n, y1 - y0, Wd, 3), np.uint8)
        for i, y in enumerate(yollar):
            with Image.open(y) as im:
                # JPEG satir bazli rastgele erisim vermez; dosya cozulur ve karo
                # dilimlenir. Maliyet karo sayisi kadar cozme, kazanc bellek.
                yig[i] = np.asarray(im.convert('RGB'))[y0:y1]
        for s0 in range(0, y1 - y0, 200):
            s1 = min(s0 + 200, y1 - y0)
            p = np.partition(yig[:, s0:s1], k, axis=0)
            if n % 2:
                plate[y0 + s0:y0 + s1] = p[k]
            else:
                q = np.partition(yig[:, s0:s1], k - 1, axis=0)[k - 1]
                plate[y0 + s0:y0 + s1] = ((p[k].astype(np.uint16) + q) // 2).astype(np.uint8)
        del yig
        log(f'  karo {t + 1}/{sayi} bitti ({satir})')
    return plate


# ------------------------------------------------------------------ SLOGAN TEMIZLIGI
# Medyan plate 78 ciftte ORTAK olan ogeleri KORUR. Isimler, semboller ve burc
# resmi cifte gore degistigi icin silinir; sonsuz (infinity) da "ISIM oo ISIM"
# satiri ortalandigi icin kayar ve silinir. Ama SLOGAN ("Two Souls . One Bond")
# her sayfada ayni metin, ayni yerdedir: medyanda AYAKTA KALIR (olculdu, MB A3:
# bant murekkebi %9.10, max 250). Temizlenmezse siparis ureticisi o bandi plate
# ile doldurdugunda eski slogan geri gelir ve musteri mesajiyla ust uste biner;
# "temiz ara zemin" kapisi bunu goremez (o bantta temiz_a ile plate zaten esit).
# Serdar onayi 25 Eyl: temizlik PLATE URETIMINDE tek seferlik yapilir, siparis
# ureticisi degismez. Yalniz slogan GLIFLERI degistirilir (bandin geri kalani
# dokunulmaz), dolgu plate'in KENDI pikselleridir (inpaint yok, dis kaynak yok).
MASKE_YARICAP = 31        # yerel kontrast medyan yaricapi (2400 uzayi, onayli)
MASKE_ESIK = 26           # yerel kontrast esigi (onayli)
MASKE_MIN_ALAN = 40
GLIF_PAY = 3              # glif maskesi bu kadar genisletilir (kenar yumusamasi)
DOLGU_ESIK = 18.0         # |serit - dolgu| bu esigin ustunde ise glif (olculen doku p99 <= 3)
DOLGU_MAD = 6.0           # ... ya da medyan + bu kadar MAD (hangisi buyukse)
KAPI_MUREKKEP_TABAN = 0.0008   # komsu bant tamamen bossa mutlak taban
TUY = 2.0                 # dolgu kenari bu sigma ile yumusatilir
KAPI_MUREKKEP_KAT = 1.5   # temizlenen bant / komsu bos bant murekkep orani
KAPI_DOKU_KAT = 1.6       # doku enerjisi orani (her iki yonde)
KAPI_TON = 4.0            # ton farki (0-255)
KAPI_HAYALET = 1.5        # eski glif bolgesi ile bandin geri kalani arasinda
                          # DUSUK FREKANSLI ton farki (harf hayaleti)
TON_SIGMA = 18.0          # ton eslemesi ve hayalet olcumu icin bulanikligin sigmasi
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def yerel_maske(L, yaricap, esik, min_alan):
    """Onayli `edisyon_maske` olcutu: buyuk yaricapli zemin medyani cikarilir."""
    import cv2
    r = max(int(yaricap), 3); r = r if r % 2 else r + 1
    zem = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), r).astype(np.float32)
    acik = float(np.median(L)) > 128
    m = ((zem - L) if acik else (L - zem)) > esik
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= min_alan
    return tut[lab]


def slogan_bandi(plate):
    """Slogan bandini PLATE'IN KENDISINDEN bulur (renk/boy basina degisir).

    Plate'te geriye yalniz halka ve slogan kalir. Slogan sayfanin alt ucte
    birinde, yatayda genis ama dikeyde ince, ortalanmis bir metin blogudur.
    """
    import cv2
    H, Wd = plate.shape[:2]
    k = 2400 / Wd
    kucuk = cv2.resize(plate, (2400, max(int(round(H * k)), 1)), interpolation=cv2.INTER_AREA)
    L = kucuk.astype(np.float32) @ LUMA
    m = yerel_maske(L, MASKE_YARICAP, MASKE_ESIK, MASKE_MIN_ALAN)
    h = m.shape[0]
    sat = m.sum(1)
    aday, cur, bos = [], None, 0
    for y in range(int(h * 0.60), h):                   # alt %40
        if sat[y] > 3:
            cur = [y, y + 1] if cur is None else [cur[0], y + 1]
            bos = 0
        elif cur is not None:
            bos += 1
            if bos > 8:
                aday.append(cur); cur = None
    if cur is not None:
        aday.append(cur)
    en_iyi = None
    for y0, y1 in aday:
        yuk = y1 - y0
        if yuk < 15 or yuk > 200:                       # metin satiri: ince
            continue
        sut = m[y0:y1].sum(0) > 0
        nz = np.nonzero(sut)[0]
        if len(nz) < 100:
            continue
        gen = nz.max() - nz.min()
        merkez = (nz.min() + nz.max()) / 2
        if gen < 300 or gen > 2000:
            continue
        if abs(merkez - 1200) > 200:                    # ortalanmis olmali
            continue
        yog = float(m[y0:y1, nz.min():nz.max()].mean())
        if en_iyi is None or yog > en_iyi['yogunluk']:
            en_iyi = {'y2400': [y0, y1], 'x2400': [int(nz.min()), int(nz.max())],
                      'yogunluk': round(yog, 4)}
    if en_iyi is None:
        return None
    o = 1.0 / k
    en_iyi['y'] = [int(en_iyi['y2400'][0] * o), int(np.ceil(en_iyi['y2400'][1] * o))]
    en_iyi['x'] = [int(en_iyi['x2400'][0] * o), int(np.ceil(en_iyi['x2400'][1] * o))]
    return en_iyi


def slogan_temizle(plate, bant):
    """Slogan GLIFLERINI plate'in kendi arka plan pikselleriyle degistirir.

    Dolgu kaynagi bandin bir bant boyu USTU ve ALTIdir; ikisi dikey capraz
    karisimla harmanlanir. Dokulu renklerde (parsomen, sampanya) bu karisim
    tekrar eden bir yama desenini onler - desen stokastik oldugu icin iki
    kaynagin harmani taninmaz; dokusuz renklerde de ayni karisim dikey gradyani
    dogru tasir, bu yuzden tek yol kullanilir. Kenar TUY sigmasiyla yumusatilir.
    Inpaint yok, dis kaynak yok.
    """
    import cv2
    y0, y1 = bant['y']
    yuk = y1 - y0
    pay = max(int(yuk * 0.35), 8)
    a0, a1 = max(y0 - pay, 0), min(y1 + pay, plate.shape[0])
    D = (a1 - a0) + max(int(yuk * 0.6), 10)             # kaynak otelemesi
    if a0 - D < 0 or a1 + D > plate.shape[0]:
        return None, {'sebep': f'kaynak serit sigmiyor (D={D})'}
    kes = plate[a0:a1].astype(np.float32)
    ust = plate[a0 - D:a1 - D].astype(np.float32)
    alt = plate[a0 + D:a1 + D].astype(np.float32)
    h = kes.shape[0]
    w = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    dolgu = ust * (1.0 - w) + alt * w
    # GLIF MASKESI iki olcutun birlesimi:
    #  (a) yerel kontrast (onayli edisyon_maske olcutu) - ince harf govdesini bulur,
    #      ama medyan yaricapindan KALIN bir gövdenin ICINI goremez (icerde zemin
    #      medyani harfin kendisidir, kontrast 0 cikar).
    #  (b) |serit - dolgu| - dolgu zaten arka plandir, dolayisiyla harfin her
    #      pikseli (icerisi dahil) buradan cikar. Esik doku/JPEG gurultusunun
    #      cok ustunde: medyan + 6 MAD, en az 18 (olculen doku p99 <= 3).
    # Ikisinin birlesimi hem ince hem kalin glifi kapsar; delikler kapatilir.
    k = plate.shape[1] / 2400.0
    L = kes @ LUMA
    m_yerel = yerel_maske(L, MASKE_YARICAP * k, MASKE_ESIK, MASKE_MIN_ALAN * k * k)
    fark = np.abs(kes - dolgu).max(axis=2)
    med = float(np.median(fark))
    mad = float(np.median(np.abs(fark - med))) * 1.4826
    esik = max(med + DOLGU_MAD * mad, DOLGU_ESIK)
    m_fark = fark > esik
    m = m_yerel | m_fark
    kap = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                    (2 * max(int(round(4 * k)), 1) + 1,) * 2)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, kap)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                    (2 * max(int(round(GLIF_PAY * k)), 1) + 1,) * 2)
    m = cv2.dilate(m, ker).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), max(TUY * k, 0.8))
    m = np.clip(m, 0.0, 1.0)[..., None]
    # TON ESLEMESI: capraz karisim dokuyu dogru getirir ama bandin KENDI yerel
    # aydinlanmasini tasimaz; ham haliyle harf yerinde dusuk frekansli bir
    # hayalet kaliyor (yerel kontrast maskesi bunu goremez, cunku dusuk frekans).
    # Cozum: bandin dusuk frekansli alani, YALNIZ slogan disi pikselleri
    # kullanilarak (maskeli normalize bulaniklik) olculur ve dolguya eklenir.
    # Yuksek frekansli doku ust/alt seritlerden, dusuk frekansli ton bandin
    # KENDI slogan disi pikselerinden gelir - ikisi de plate'in kendi pikselleri.
    # DOLGU = bitisik satirlarin TONU + uzak seritlerin DOKUSU.
    #   Dusuk frekans (ton/aydinlanma): bandin HEMEN ustundeki ve altindaki
    #   temiz satirlarin sutun ortalamasi arasinda dikey ramp. Bu, bandin kendi
    #   yerel tonunu birebir tasir - capraz karisimin tek basina birakti izi
    #   (sentetik dokulu olcumde hayalet 3.14) buradan cozulur.
    #   Yuksek frekans (doku): +-D seritlerinin capraz karisimindan, cunku
    #   bitisik satirlarin dokusunu kopyalamak taninabilir tekrar yapar.
    # Ikisi de plate'in KENDI pikselleri; inpaint yok, dis kaynak yok.
    sg = max(TON_SIGMA * k, 3.0)
    P = max(int(round(8 * k)), 3)
    ust_k = plate[max(a0 - P, 0):a0].astype(np.float32).mean(axis=0, keepdims=True)
    alt_k = plate[a1:min(a1 + P, plate.shape[0])].astype(np.float32).mean(axis=0, keepdims=True)
    lf_hedef = ust_k * (1.0 - w) + alt_k * w
    hf = dolgu - cv2.GaussianBlur(dolgu, (0, 0), sg)
    dolgu = lf_hedef + hf
    yeni = plate.copy()
    yeni[a0:a1] = np.clip(kes * (1 - m) + dolgu * m, 0, 255).astype(np.uint8)
    return yeni, {'serit': [a0, a1], 'oteleme': D, 'glif_px': int((m > 0.5).sum()),
                  'glif_orani': round(float((m > 0.5).mean()), 4),
                  'dolgu_esik': round(esik, 2), 'fark_medyan': round(med, 2),
                  'yerel_px': int(m_yerel.sum()), 'fark_px': int(m_fark.sum()),
                  'maske': (m[..., 0] > 0.5)}


def doku_enerji(a):
    import cv2
    L = (a.astype(np.float32) @ LUMA)
    r = 9
    b = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), r).astype(np.float32)
    return float(np.abs(L - b).mean())


def temizlik_kapilari(eski, yeni, bant, bilgi):
    """Serdar'in zorunlu kildigi kapilar + harf hayaleti kapisi."""
    import cv2
    a0, a1 = bilgi['serit']
    yuk = a1 - a0
    k = yeni.shape[1] / 2400.0
    bant_y = yeni[a0:a1]
    ust = yeni[max(a0 - yuk, 0):a0]
    alt = yeni[a1:min(a1 + yuk, yeni.shape[0])]
    komsu = np.concatenate([ust, alt], axis=0)
    mb = yerel_maske(bant_y.astype(np.float32) @ LUMA,
                     MASKE_YARICAP * k, MASKE_ESIK, MASKE_MIN_ALAN * k * k)
    mk = yerel_maske(komsu.astype(np.float32) @ LUMA,
                     MASKE_YARICAP * k, MASKE_ESIK, MASKE_MIN_ALAN * k * k)
    o_b, o_k = float(mb.mean()), float(mk.mean())
    e_b, e_k = doku_enerji(bant_y), doku_enerji(komsu)
    t_b = float((bant_y.astype(np.float32) @ LUMA).mean())
    t_k = float((komsu.astype(np.float32) @ LUMA).mean())
    eski_o = float(yerel_maske(eski[a0:a1].astype(np.float32) @ LUMA,
                               MASKE_YARICAP * k, MASKE_ESIK, MASKE_MIN_ALAN * k * k).mean())
    d = {'murekkep_bant': round(o_b, 5), 'murekkep_komsu': round(o_k, 5),
         'murekkep_bant_ONCE': round(eski_o, 5),
         'murekkep_kat': round(o_b / max(o_k, 1e-6), 2), 'esik_kat': KAPI_MUREKKEP_KAT,
         'doku_bant': round(e_b, 3), 'doku_komsu': round(e_k, 3),
         'doku_kat': round(e_b / max(e_k, 1e-6), 3), 'esik_doku': KAPI_DOKU_KAT,
         'ton_bant': round(t_b, 2), 'ton_komsu': round(t_k, 2),
         'ton_fark': round(abs(t_b - t_k), 2), 'esik_ton': KAPI_TON}
    # HAYALET: eski glif bolgesi, bandin geri kalanina gore sistematik olarak
    # acik/koyu kalmis mi? Dusuk frekansta olculur; yerel kontrast maskesi bunu
    # goremez. (Sentetik dogrulamada ham capraz karisim burada 2.4 veriyordu.)
    gm = bilgi.get('maske')
    if gm is not None and gm.any() and (~gm).any():
        sg = max(TON_SIGMA * k, 3.0)
        lf = cv2.GaussianBlur((bant_y.astype(np.float32) @ LUMA), (0, 0), sg)
        d['hayalet'] = round(abs(float(lf[gm].mean()) - float(lf[~gm].mean())), 3)
    else:
        d['hayalet'] = None
    d['esik_hayalet'] = KAPI_HAYALET
    d['murekkep_siniri'] = round(max(o_k * KAPI_MUREKKEP_KAT, KAPI_MUREKKEP_TABAN), 6)
    d['gecti'] = bool(o_b <= max(o_k * KAPI_MUREKKEP_KAT, KAPI_MUREKKEP_TABAN)
                      and 1 / KAPI_DOKU_KAT <= d['doku_kat'] <= KAPI_DOKU_KAT
                      and d['ton_fark'] <= KAPI_TON
                      and (d['hayalet'] is None or d['hayalet'] <= KAPI_HAYALET))
    return d



def slogan_kirpim(eski, yeni, bilgi, etiket, buyut=3, azami_en=2400):
    """Temizlenen slogan bandinin x3 buyutmesi: USTTE once, ALTTA sonra.
    Serdar gorsel onayi icin (2. madde)."""
    from PIL import ImageDraw
    a0, a1 = bilgi['serit']
    parcalar = []
    for ad, im_a in (('ONCE', eski), ('SONRA', yeni)):
        k = Image.fromarray(im_a[a0:a1])
        g = min(buyut, max(azami_en / max(k.width, 1), 1.0))
        k = k.resize((int(k.width * g), int(k.height * g)), Image.LANCZOS)
        if k.width > azami_en:
            k = k.resize((azami_en, round(k.height * azami_en / k.width)), Image.LANCZOS)
        parcalar.append((ad, k))
    en = max(i.width for _, i in parcalar)
    yuk = sum(i.height for _, i in parcalar) + 3 * 26
    t = Image.new('RGB', (en, yuk), 'white')
    d = ImageDraw.Draw(t)
    y = 4
    for ad, im in parcalar:
        d.text((4, y), f'{etiket}  {ad}', fill='black')
        t.paste(im, (0, y + 18)); y += im.height + 26
    dosya = f'SLOGAN_{etiket}_x3.jpg'
    t.save(W / dosya, quality=95)
    return {'dosya': dosya, 'px': list(t.size), 'buyutme': buyut}



def fark_olc(a, plate):
    import cv2
    f = np.abs(a.astype(np.int16) - plate.astype(np.int16)).max(axis=2).astype(np.uint8)
    cek = (f > FARK_ESIK).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * FARK_GENIS + 1,) * 2)
    m = cv2.dilate(cek, ker) > 0
    dis = f[~m]
    if dis.size < 1000:
        return {'gecerli': False, 'murekkep_orani': round(float(m.mean()), 4)}
    return {'gecerli': True, 'murekkep_orani': round(float(m.mean()), 4),
            'p50': float(np.percentile(dis, 50)), 'p99': float(np.percentile(dis, 99)),
            'ort': round(float(dis.mean()), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parca', default='1/1', help='i/n - is listesinin i. dilimi')
    ap.add_argument('--yenile', action='store_true',
                    help='PLATES\'te olanlari da yeniden uret (slogan temizligi gibi '
                         'icerik degisikliginden sonra gerekir)')
    a = ap.parse_args()
    i, n = (int(x) for x in a.parca.split('/'))
    isler, sayac = is_listesi()
    var = set() if a.yenile else mevcut_plateler()
    kalan = [(r, b) for r, b in isler if f'{RENK_ED[r].upper()}_{b}.png' not in var]
    benim = [x for j, x in enumerate(kalan) if j % n == i - 1]
    log(f'toplam {len(isler)} plate, {len(var)} tanesi PLATES\'te var, '
        f'{len(kalan)} kaldi; parca {i}/{n} -> {len(benim)}: '
        + ', '.join(f'{r}/{b}' for r, b in benim))
    rapor = {'parca': a.parca, 'tarih': datetime.now(timezone.utc).isoformat(),
             'matris': sayac, 'toplam_plate': len(isler), 'onceden_var': sorted(var),
             'bu_kosuda_kalan': [f'{r}/{b}' for r, b in kalan],
             'plateler': {}, 'hata': {}}
    for renk, boy in benim:
        anahtar = f'{renk}/{boy}'
        try:
            t0 = time.time()
            yollar = indir(renk, boy)
            boyutlar = {}
            for y in yollar:
                with Image.open(y) as im:
                    boyutlar.setdefault(im.size, []).append(y)
            tam_px = max(boyutlar, key=lambda s: len(boyutlar[s]))
            aykiri = [y.stem for s, ys in boyutlar.items() if s != tam_px for y in ys]
            yollar = sorted(boyutlar[tam_px])
            if len(yollar) < ASGARI_DOSYA:
                rapor['hata'][anahtar] = f'yalniz {len(yollar)} dosya'
                continue
            log(f'{anahtar}: {len(yollar)} dosya, {tam_px[0]}x{tam_px[1]}'
                + (f', aykiri {aykiri}' if aykiri else ''))
            ham_plate = karo_ortanca(yollar, tam_px, anahtar)
            ed = RENK_ED[renk]
            ad = f'{ed.upper()}_{boy}.png'

            # SLOGAN TEMIZLIGI (Serdar onayi 25 Eyl, 1. madde) - zorunlu.
            bant = slogan_bandi(ham_plate)
            if bant is None:
                rapor['hata'][anahtar] = 'slogan bandi bulunamadi - plate yazilmadi'
                log(f'{anahtar} slogan bandi bulunamadi, ATLANDI')
                continue
            plate, tb = slogan_temizle(ham_plate, bant)
            if plate is None:
                rapor['hata'][anahtar] = f'slogan temizligi yapilamadi: {tb["sebep"]}'
                log(f'{anahtar} temizlik yapilamadi: {tb["sebep"]}')
                continue
            kapi = temizlik_kapilari(ham_plate, plate, bant, tb)
            tb.pop('maske', None)                 # dizi rapora yazilmaz
            if not kapi['gecti']:
                rapor['hata'][anahtar] = {'slogan_temizlik_kapisi': 'KALDI', **kapi}
                log(f'{anahtar} TEMIZLIK KAPISI KALDI ' + json.dumps(kapi))
                continue
            kirp = slogan_kirpim(ham_plate, plate, tb, f'{ed.upper()}_{boy}')
            del ham_plate
            Image.fromarray(plate, 'RGB').save(W / ad, 'PNG', optimize=False,
                                               compress_level=6)
            orn = {}
            for ix in {0, len(yollar) // 2, len(yollar) - 1}:
                with Image.open(yollar[ix]) as im:
                    orn[yollar[ix].stem] = fark_olc(np.asarray(im.convert('RGB')), plate)
            rapor['plateler'][anahtar] = {
                'edisyon': ed, 'boy': boy, 'dosya': ad, 'n': len(yollar),
                'aykiri_boyut': aykiri, 'px': list(tam_px),
                'png_MB': round((W / ad).stat().st_size / 1e6, 1),
                'slogan_bandi': {k2: bant[k2] for k2 in ('y', 'x', 'y2400', 'x2400')},
                'slogan_temizlik': tb, 'temizlik_kapisi': kapi, 'kirpim': kirp,
                'sure_sn': round(time.time() - t0, 1), 'ornekler': orn}
            rc('copy', str(W / ad), PLATES, timeout=2400)
            (W / ad).unlink()
            if kirp:
                rc('copy', str(W / kirp['dosya']), f'{PLATES}/SLOGAN_KIRPIM', timeout=900)
            rp = W / f'RAPOR_{i}_{n}.json'      # her plate sonrasi yaz: kesilirse kaybolmasin
            rp.write_text(json.dumps(rapor, indent=1, ensure_ascii=False), encoding='utf-8')
            rc('copy', str(rp), PLATES, timeout=600)
            for f in (W / f'{renk}_{boy}').glob('*.jpg'):
                f.unlink()
            log(f'{anahtar} bitti {time.time() - t0:.0f}s ' + json.dumps(orn)[:300])
        except BaseException as e:                                # noqa: BLE001
            rapor['hata'][anahtar] = f'{type(e).__name__}: {e}'
            log(f'{anahtar} HATA: {type(e).__name__}: {e}')
    rp = W / f'RAPOR_{i}_{n}.json'
    rp.write_text(json.dumps(rapor, indent=1, ensure_ascii=False), encoding='utf-8')
    rc('copy', str(rp), PLATES, timeout=600)
    print(json.dumps({'parca': a.parca, 'uretilen': sorted(rapor['plateler']),
                      'hata': rapor['hata']}, indent=1))
    if rapor['hata']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
