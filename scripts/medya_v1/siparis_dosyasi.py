#!/usr/bin/env python3
"""Siparis baski dosyasi ureticisi (Serdar 25 Eyl 2026). Etsy/Prodigi'ye erisim YOK.

Girdi: router karti Drive TEMP/SIPARIS_ISIM/<receipt>.md (cift, renk, boy, isim1, isim2, mesaj)
       ya da elle parametre (--cift --renk --boy --isim1 --isim2 --mesaj).
Cikti: Drive TEMP/SIPARIS_ISIM/<receipt>/BASKI_<boy>.jpg + ONIZLEME_<boy>.jpg + KAPI_RAPORU.json

Render kodu DEGISMEZ: kisisel-v1 dal arsivi cikarilir, medya-v1'deki onayli sarmalayici
(a1_poster: sayfa basina olcum, olcum_duzelt, sembol kapisi, isim/tagline ust siniri) kullanilir.
Blue icin pilot16 yolu (a1_poster.Poster), diger dort edisyon icin edisyon_uret yolu; ikisinde de
girdi degisir, kod degismez (REF_SAYFA modul degiskeni + sayfanin kendi olcumu).

COZUNURLUK (25 Eyl olcumu, POD_OLCUM.json):
  - POD_PRINT'teki mevcut baski dosyalari ZATEN 300 dpi: 8x10 2400x3000, 12x16 3600x4800,
    18x24 5400x7200, 30x40 9000x12000, A3 3507x4960, A2 4960x7015. (5x7 10962x15175 ile
    listede tek aykiri dosya; ayri bulgu olarak raporlanir.)
  - Canva 3/4 tasariminin YEREL disa aktarimi 3000x4000 (kayipsiz PNG 19.5 MB). Istenen
    olcu verilirse Canva o olcuyu birebir veriyor (3600x4800 ve 3508x4961 dogrulandi) ama
    dosya 1.6 MB'a dusuyor, yani yeniden sikistiriyor.
  - Onayli render hatti sayfayi NORM_W=2400 genislige normalize eder; kisisellestirilen
    isim/tagline bandi bu yuzden 2400 px genislikte uretilir.
KARAR: tuval Canva'dan yeniden uretilmez; KAYNAK = POD_PRINT/<cift>/<renk>/<boy>.jpg, yani
uretimde kullanilan onayli baski dosyasinin kendisi (dogru boy, dogru dpi, dogru renk).
Baski dosyasi HIBRIT birlestirmeyle kurulur: tuval o dosyadir, yalnizca degisen bant
(eski oge maskesi + yeni yazi maskesi) 2400'luk render'dan olceklenip yumusak kenarla oturur.
Rapor hem gorsel dpi'yi hem de kisisellestirilen bandin gercek dpi'sini yazar.
`--kaynak canva` secenegi POD_PRINT'te olmayan boylar icin durur (imzali URL listesi gerekir).
"""
import argparse, io, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KP = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
SIP = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM'
PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'   # medyan zemin (Serdar onayi 25 Eyl)
# Plate kumesi: '' = medyan plate (<ED>_<boy>.png), '_CANVA' = Canva katman
# kaynakli plate (<ED>_CANVA_<boy>.png, GOREV_0015/0017). Varsayilan medyan;
# Canva kumesi onay sayfasi onaylanana kadar yalniz --plate canva ile kullanilir.
PLATE_EK = ''
PLATE_ESIK = 12.0      # |dosya - plate| murekkep esigi (olculen: disi p99 0-3, cekirdek > 30)
W = Path('_siparis').resolve(); W.mkdir(exist_ok=True)
K = W / 'kisisel'                                   # kisisel-v1 dal arsivi (degistirilmez)

# renk adi (router karti / POD_PRINT) -> kisisel-v1 edisyon anahtari
RENK_ED = {'MIDNIGHT_BLUE': 'blue', 'DEEP_BLACK': 'black', 'PURE_WHITE': 'pure_white',
           'CHAMPAGNE_IVORY': 'modern', 'WARM_PARCHMENT': 'vintage'}
RENK_TAKMA = {'BLUE': 'MIDNIGHT_BLUE', 'BLACK': 'DEEP_BLACK', 'MODERN': 'CHAMPAGNE_IVORY',
              'VINTAGE': 'WARM_PARCHMENT', 'WHITE': 'PURE_WHITE'}

# boy -> (oran, en_inc, boy_inc). A serisi metrik, digerleri inc.
BOY = {'8x10': ('4x5', 8, 10), '16x20': ('4x5', 16, 20),
       '11x14': ('11x14', 11, 14),
       '12x16': ('3x4', 12, 16), '18x24': ('3x4', 18, 24), '30x40': ('3x4', 30, 40),
       '12x18': ('2x3', 12, 18), '16x24': ('2x3', 16, 24), '20x30': ('2x3', 20, 30),
       '24x36': ('2x3', 24, 36),     # 28 Eyl: 13 satilan boyun tamami (12x18/16x24/20x30 eksikti)
       'A4': ('A', 8.268, 11.693), 'A3': ('A', 11.693, 16.535), 'A2': ('A', 16.535, 23.386)}
DPI = 300                                            # Prodigi onerisi

CANVA = {
    'blue':       {'4x5': 'DAHPdJACZLI', '3x4': 'DAHPL01XVHQ', '2x3': 'DAHPdHUjsoo', '11x14': 'DAHPdLqeCg0', 'A': 'DAHPdHwphnk'},
    'black':      {'4x5': 'DAHPc83q0zA', '3x4': 'DAHPLrR9Vw8', '2x3': 'DAHPcuidLMk', '11x14': 'DAHPcxEOzDc', 'A': 'DAHPc5ZeTl8'},
    'pure_white': {'4x5': 'DAHSQxiT-FM', '3x4': 'DAHSQvQojyQ', '2x3': 'DAHSQ1VUTbg', '11x14': 'DAHSQ6am6pM', 'A': 'DAHSQ8yhNuI'},
    'modern':     {'4x5': 'DAHPeNlT5dY', '3x4': 'DAHPMJyUzUA', '2x3': 'DAHPeC-DVDU', '11x14': 'DAHPeTaB0uc', 'A': 'DAHPeDYoEYQ'},
    'vintage':    {'4x5': 'DAHPeXwAKXA', '3x4': 'DAHPQZxUwII', '2x3': 'DAHPeU4sjRE', '11x14': 'DAHPeYBzqXU', 'A': 'DAHPeVe1sxw'},
}
KENAR_YUMUSAT = 2.0      # hibrit birlestirmede maske yumusatmasi (2400 uzayinda px)
# Edisyon hatti (kilitler, bulma maskesi esikleri) Canva'nin YEREL disa aktarim boyunda
# dogrulandi. POD baski dosyasi cok daha buyuk olabilir (30x40 = 9000x12000); 9000 -> 2400
# kuculmesi (3.75x) parsomen dokusunda isim satirini bulunamaz yapiyor (olculdu: "16 bant").
# Bu yuzden RENDER GIRDISI once bu genislige indirilir; BASKI TUVALI tam boyda kalir.
OLCUM_EN = {'2x3': 4000, '3x4': 3000, '4x5': 4000, '11x14': 3300, 'A': 3508}
OLCUM_MERDIVEN = (1.0, 0.8, 1.2)        # olcum basarisizsa denenecek genislik carpanlari

# Urun turu (router kartindan). POD: tek renk+boy baski dosyasi. DIJITAL: 5 renk x 5 oran, renk basina 1 PDF.
# DUVAR_KAGIDI: dijital-78 oturumunun wallpaper kodu (henuz onaylanmadi) -> BEKLIYOR.
URUN_ES = {'pod': 'POD', 'print': 'POD', 'baski': 'POD', 'poster': 'POD',
           'dijital': 'DIJITAL', 'digital': 'DIJITAL', 'dijital_duvar_sanati': 'DIJITAL',
           'duvar_kagidi': 'DUVAR_KAGIDI', 'wallpaper': 'DUVAR_KAGIDI'}
# Dijital pakette her oran icin kullanilan onayli baski dosyasi (hepsi 300 dpi)
DIJITAL_BOY = {'4x5': '16x20', '3x4': '18x24', '2x3': '24x36', '11x14': '11x14',
               'a_series': 'A2'}
DIJITAL_ORANLAR = ('4x5', '3x4', '2x3', '11x14', 'a_series')
# Teslim: Etsy Messages yalniz jpg/gif/pdf/png kabul eder (ZIP yok), mesaj basina en fazla 3 dosya,
# gorsel en fazla 10000x10000 px / 100 MB; 24x36 JPG (7200x10800) siniri asar. Bu yuzden DIJITAL cikti
# renk basina TEK PDF: 5 sayfa (DIJITAL_ORANLAR sirasi), sayfa = fiziksel boy, gomulu JPEG 300 dpi,
# yeniden sikistirilmadan (img2pdf) gomulur (Serdar, 27 Eyl 2026).
PDF_AZAMI_MB = 100.0
PDF_HEDEF_MB = 40.0
DIJITAL_KALITE = 95
SAYFA_TOL_MM = 0.5                      # sayfa olcusu toleransi
DPI_TOL = 0.01                          # gomulu gorsel dpi toleransi (oran)
RENKLER = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT')
BUYUT = 3                               # kontrol paketinde bant buyutme
_TANI = None                            # baski_tani.py bir dict atarsa pod_uret goruntuleri buraya koyar


def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def dijital_oran(oran):
    """Eski A anahtarini kabul et, disariya kanonik a_series yaz."""
    if oran == 'A':
        log('UYARI: dijital oran A eskidi; a_series kullaniliyor')
        return 'a_series'
    return oran


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def maskele(u):
    print(f'::add-mask::{u}', flush=True)
    for p in u.split('&'):
        if p.startswith('X-Amz-Signature='):
            print(f'::add-mask::{p.split("=", 1)[1]}', flush=True)


def indir(u):
    son = None
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=300) as r:
                return r.read()
        except Exception as e:                                    # noqa: BLE001
            son = e; time.sleep(2 ** i)
    raise RuntimeError(f'indirilemedi: {son}')


def kisisel_hazirla():
    subprocess.run(['git', 'fetch', '--depth', '1', 'origin', 'kisisel-v1'], check=True)
    K.mkdir(exist_ok=True)
    arc = subprocess.run(['git', 'archive', 'FETCH_HEAD', 'scripts/kisisel', 'assets'],
                         capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-C', str(K)], input=arc, check=True)
    sys.path.insert(0, str(K / 'scripts' / 'kisisel'))


# ------------------------------------------------------------------ router karti
def kart_oku(metin):
    """Router karti (markdown): 'anahtar: deger' satirlari. Turkce/Ingilizce anahtarlar."""
    ES = {'cift': 'cift', 'çift': 'cift', 'pair': 'cift',
          'renk': 'renk', 'color': 'renk', 'edisyon': 'renk', 'edition': 'renk',
          'boy': 'boy', 'size': 'boy', 'olcu': 'boy', 'ölçü': 'boy',
          'isim1': 'isim1', 'isim 1': 'isim1', 'name1': 'isim1', 'name 1': 'isim1',
          'isim2': 'isim2', 'isim 2': 'isim2', 'name2': 'isim2', 'name 2': 'isim2',
          'mesaj': 'mesaj', 'message': 'mesaj', 'tagline': 'mesaj',
          'urun': 'urun', 'product': 'urun', 'urun_turu': 'urun', 'tur': 'urun'}
    d = {}
    for satir in metin.splitlines():
        s = satir.strip().lstrip('-*# ').strip()
        if ':' not in s:
            continue
        a, b = s.split(':', 1)
        a = a.strip().strip('*_`').lower()
        if a in ES:
            d[ES[a]] = b.strip().strip('*_`')
    zorunlu = ('cift', 'isim1', 'isim2')
    if URUN_ES.get(str(d.get('urun', 'pod')).strip().lower().replace(' ', '_'), 'POD') == 'POD':
        zorunlu += ('renk', 'boy')
    else:
        d.setdefault('renk', 'MIDNIGHT_BLUE')          # dijitalde 5 renk uretilir; alan sart degil
    eksik = [k for k in zorunlu if not d.get(k)]
    if eksik:
        raise SystemExit(f'kartta eksik alan: {eksik}')
    return d


def normalize(d):
    cift = d['cift'].upper().replace(' ', '_').replace('+', '_').replace('-', '_')
    cift = re.sub(r'_+', '_', cift)
    urun = URUN_ES.get(str(d.get('urun', 'pod')).strip().lower().replace(' ', '_'), 'POD')
    ham_renk = d.get('renk') or ('MIDNIGHT_BLUE' if urun != 'POD' else '')
    if not ham_renk:
        raise SystemExit('POD siparisinde renk zorunlu')
    renk = RENK_TAKMA.get(ham_renk.upper().replace(' ', '_').replace('-', '_'),
                          ham_renk.upper().replace(' ', '_').replace('-', '_'))
    if renk not in RENK_ED:
        raise SystemExit(f'bilinmeyen renk: {ham_renk} (beklenen {sorted(RENK_ED)})')
    out = {**d, 'cift': cift, 'renk': renk, 'urun': urun, 'edisyon': RENK_ED[renk]}
    if urun != 'POD':
        return {**out, 'boy': d.get('boy') or '-', 'oran': None, 'hedef_px': None, 'inc': None}
    if not d.get('boy'):
        raise SystemExit('POD siparisinde boy zorunlu')
    boy = d['boy'].strip().upper().replace(' ', '').replace('×', 'x').replace('X', 'x')
    if boy not in BOY:
        raise SystemExit(f'bilinmeyen boy: {d["boy"]} (beklenen {sorted(BOY)})')
    return {**out, 'boy': boy, 'oran': BOY[boy][0],
            'hedef_px': [round(BOY[boy][1] * DPI), round(BOY[boy][2] * DPI)],
            'inc': [BOY[boy][1], BOY[boy][2]]}


class PlateHatasi(RuntimeError):
    """Plate yok ya da kirli: siparis dosyasi URETILMEZ (fail-closed)."""

    def __init__(self, mesaj, ayrinti=None):
        super().__init__(mesaj)
        self.ayrinti = ayrinti or {}


# ------------------------------------------------------------------ PLATE SLOGAN KAPISI
# 28 Eyl hata kontrolu (baski-duzelt): 25 Eyl medyan plate'lerinin bir kismi eski slogani
# ICERIYOR (slogan temizlik kapisi o boylarda KALDI, temizlenmis plate yuklenmedi). Boyle bir
# plate'le eski slogan "zemin" sayilir ve silinmez: CI 12x16 BASKI'da eski slogan yeni
# mesajin altinda kaldi, kalinti / temiz ara zemin kapilari goremedi (o bantta temiz_a ile
# plate zaten esit). Kapi: siparisin KENDI dosyasinda slogan bandi plate'ten BAGIMSIZ olculur
# (Blue: a1 esigi, digerleri edisyon_maske); slogan GLIF piksellerinde |dosya - plate| >
# PLATE_ESIK olan pay olculur. Temiz plate'te glif plate'te yoktur (pay yuksek), kirli
# plate'te glif plate'te de vardir (pay ~0). Olculen (tani kosusu 36425530758, slogan kutusu,
# 3 cift): temiz DB/CI/PW 11x14 esik ustu pay 0.28-0.29 (kutu; glif ~%9), kirli WP 11x14 /
# CI 12x16 0.0 (p99 fark 0-1.6).
PLATE_SLOGAN_ESIK = 0.25


def plate_fark_maskesi(plate_yol):
    """`sayfa_olc` maske ureticisi: |dosya - plate| > PLATE_ESIK (siparis render'inin olcumu)."""
    import cv2
    import pilot11
    from pilot6 import LUMA
    eu = _mod('edisyon_uret')
    pl = pilot11.norm(Image.open(plate_yol).convert('RGB'))[0]
    Lp = np.asarray(pl).astype(np.float32) @ LUMA

    def maske(L, acik):                                        # noqa: ARG001
        h = min(L.shape[0], Lp.shape[0])
        m = np.zeros(L.shape, bool)
        m[:h] = np.abs(L[:h] - Lp[:h]) > PLATE_ESIK
        k = eu.MASKE_KENAR
        if k:
            Wd = L.shape[1]
            m[:, :int(Wd * k)] = False
            m[:, int(Wd * (1 - k)):] = False
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        tut = np.zeros(n, bool)
        tut[1:] = st[1:, cv2.CC_STAT_AREA] >= eu.MASKE_MIN_ALAN
        return tut[lab]
    return maske


def plate_slogan_kapisi(kaynak, plate_yol, ed):
    """Plate'te eski slogan kaldi mi? gecti=False ise siparis durur (SISTEM HATASI).

    1 Eki (siparis 4188621967, yanlis alarm): bayt girdi her cagrida AYNI gecici dosyaya
    (W/_plate_kapisi_kaynak.jpg) yaziliyordu; dijital yolda 3 paralel isci ayni klasorde birbirinin
    sayfasini olcuyordu (CANCER_LEO DB / CI 2x3 'slogan glifi yok (0 px)'; ayni dosyalar seri tanida
    25/25 PASS, glif 16202 px, pay 1.0). Gecici dosya artik cagriya ozel; kapi ve esik ayni."""
    if isinstance(kaynak, (bytes, bytearray)):
        import os, uuid
        yol = W / f'_plate_kapisi_kaynak_{os.getpid()}_{uuid.uuid4().hex}.jpg'
        yol.write_bytes(kaynak) if kaynak[:3] == b'\xff\xd8\xff' else \
            Image.open(io.BytesIO(kaynak)).convert('RGB').save(yol, 'PNG')
        try:
            return _plate_slogan_kapisi(yol, plate_yol, ed)
        finally:
            yol.unlink(missing_ok=True)
    return _plate_slogan_kapisi(kaynak, plate_yol, ed)


def _plate_slogan_kapisi(kaynak, plate_yol, ed):
    import pilot11
    from pilot6 import LUMA
    eu = _mod('edisyon_uret')
    olcek_kur(2400)
    yol = kaynak
    if isinstance(kaynak, (bytes, bytearray)):
        yol = W / '_plate_kapisi_kaynak.jpg'
        yol.write_bytes(kaynak) if kaynak[:3] == b'\xff\xd8\xff' else \
            Image.open(io.BytesIO(kaynak)).convert('RGB').save(yol, 'PNG')
    yol = Path(yol)
    d = {'plate': Path(plate_yol).name, 'esik': PLATE_SLOGAN_ESIK,
         'olcut': 'slogan glif piksellerinde |dosya - plate| > PLATE_ESIK payi'}
    maske = None if ed == 'blue' else (lambda L, acik: eu.edisyon_maske(L, acik))
    try:
        o = pilot11.sayfa_olc(yol, maske=maske)
    except SystemExit as e:
        o = {'hata': str(e)}
    if 'tag_bant' not in o:
        # Yerel kontrast maskesi dokulu zeminde isim satirini bulamayabilir (28 Eyl: WP 18x24,
        # 30x40, AQ 12x16 'isim satiri bulunamadi'). Siparis render'i bantlari ZATEN
        # |dosya - plate| maskesiyle olcer; ayni olcum burada da denenir. Kirli plate'te slogan
        # farkta gorunmez -> bant yok -> FAIL (fail-closed korunur). Glif pikselleri asagida
        # yine bagimsiz yerel kontrast maskesinden alinir.
        try:
            o2 = pilot11.sayfa_olc(yol, maske=plate_fark_maskesi(plate_yol))
        except SystemExit as e:
            o2 = {'hata': str(e)}
        if 'tag_bant' not in o2:
            return {**d, 'gecti': False,
                    'sebep': f"dosya olculemedi: {o.get('hata') or 'slogan bandi yok'}; "
                             f"plate farkiyla: {o2.get('hata') or 'slogan bandi yok'}"}
        o, d['olcum'] = o2, 'plate farki maskesi'
    (y0, y1), (x0, x1) = o['tag_bant'], o['tag_x']
    A = np.asarray(pilot11.norm(Image.open(yol).convert('RGB'))[0]).astype(np.float32) @ LUMA
    pl = pilot11.norm(Image.open(plate_yol).convert('RGB'))[0]
    if pl.size != (A.shape[1], A.shape[0]):
        pl = pl.resize((A.shape[1], A.shape[0]), Image.LANCZOS)
    P = np.asarray(pl).astype(np.float32) @ LUMA
    g = eu.edisyon_maske(A, float(np.median(A)) > 128)[y0:y1, x0:x1]
    if g.sum() < 200:
        return {**d, 'gecti': False, 'sebep': f'slogan glifi yok ({int(g.sum())} px)',
                'tag_bant': [y0, y1], 'tag_x': [x0, x1]}
    fark = np.abs(A[y0:y1, x0:x1] - P[y0:y1, x0:x1])[g]
    pay = float((fark > PLATE_ESIK).mean())
    return {**d, 'gecti': bool(pay >= PLATE_SLOGAN_ESIK), 'glif_farkli_payi': round(pay, 4),
            'glif_px': int(g.sum()), 'fark_p50': round(float(np.percentile(fark, 50)), 1),
            'tag_bant': [y0, y1], 'tag_x': [x0, x1]}


def plate_bildir(bi, receipt=''):
    """Fail-closed bildirim: Actions ::error notu + rapor alani (musteriye hicbir sey gitmez)."""
    msj = f"{receipt} {bi.get('hata')}".strip()
    print(f'::error title=PLATE HATASI::{msj}', flush=True)
    bi['bildirim'] = {'kanal': 'GitHub Actions ::error + kosu FAIL', 'mesaj': msj}
    return bi


# ------------------------------------------------------------------ ISIM PLAKASI (olcek tutarliligi)
# 28 Eyl olcumu (uretim cizim yolu, 2400 vs 3307, 5 isim seti x 3 zemin): hi-res'te punto cap
# hedefinden YENIDEN aranirsa onayli 2400 puntosuyla orantili cikmiyor (MAXIMILIANA 118 -> 164,
# orantili 162.6: harf kenari 4.4 px); ayrica FreeType hinting glif yuksekligini her puntoda ayri
# piksele oturttugu icin cap/taban 1.7 px'e kadar sapiyor. Cozum (cizim kodu degismez, girdi):
# Blue disi edisyonlarda isim glifi SS kat buyuk cizilip alan ortalamasiyla indirilir (hinting
# izgarasi 1/SS px'e iner) ve hi-res punto = onayli 2400 punto x k (yeniden arama yok).
# Simulasyon: en kotu konum 1.71 -> 1.09, harf kenari 4.4 -> 0.55.
ISIM_SS = 4


def plaka_ss(metin, prof, hedef_cap, olcek=1.0, tam=None, orijinal=None):
    """pilot12.plaka ile ayni sozlesme; glif SS kat cizilip indirilir, boyut ondalikli olabilir."""
    p12 = _mod('pilot12')
    from kisisel_pilot import font_yukle, ciz_metin, cap_icin_boyut
    from pilot6 import ISIM_FONT, ISIM_W
    fp = p12.FONT_DIR / ISIM_FONT
    tam = tam or cap_icin_boyut(fp, p12.govde(metin, fp, ISIM_W), hedef_cap, ISIM_W)
    boy = max(tam * olcek, 4.0)
    s4 = max(int(round(boy * ISIM_SS)), 4 * ISIM_SS)
    cr, _ = ciz_metin(font_yukle(fp, s4, ISIM_W), metin, s4 * -0.0388)   # onayli harf araligi
    a = np.asarray(cr).astype(np.float32)
    h, w = a.shape
    H, Wd = -(-h // ISIM_SS) * ISIM_SS, -(-w // ISIM_SS) * ISIM_SS
    b = np.zeros((H, Wd), np.float32)
    b[:h, :w] = a
    m = b.reshape(H // ISIM_SS, ISIM_SS, Wd // ISIM_SS, ISIM_SS).mean(axis=(1, 3))
    ys, xs = np.nonzero(m > 40)                     # ciz_metin ile ayni kirpim olcutu
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return (p12.altin_isim(Image.fromarray(np.clip(m, 0, 255).astype(np.uint8)), prof),
            int(round(boy)), tam)


class IsimPlakasi:
    """Render suresince pilot12/pilot16 `plaka` adini plaka_ss'e baglar (kod degismez).

    kayit: 2400 render'da (metin, cap) -> son kullanilan boy. sabit: hi-res'te
    {(metin, cap_hi): boy_2400 * k}; varsa d_olcek dahil her cagri bu boyu kullanir."""

    def __init__(self, kayit=None, sabit=None):
        self.kayit, self.sabit = kayit, sabit

    def __call__(self, metin, prof, hedef_cap, olcek=1.0, tam=None):
        if self.sabit is not None and (metin, hedef_cap) in self.sabit:
            return plaka_ss(metin, prof, hedef_cap, 1.0, tam=self.sabit[(metin, hedef_cap)])
        r = plaka_ss(metin, prof, hedef_cap, olcek, tam)
        if self.kayit is not None:
            self.kayit[(metin, hedef_cap)] = r[2] * olcek
        return r

    def __enter__(self):
        self._eski = (_mod('pilot12').plaka, _mod('pilot16').plaka)
        _mod('pilot12').plaka = self
        _mod('pilot16').plaka = self
        return self

    def __exit__(self, *a):
        _mod('pilot12').plaka, _mod('pilot16').plaka = self._eski
        return False


# ------------------------------------------------------------------ edisyon sarmalayicisi
class EdisyonPoster:
    """Blue disi dort edisyon: edisyon_uret yolu. Girdi degisir, render kodu degismez."""

    def __init__(self):
        import pilot11, pilot12, pilot16
        import edisyon_uret as eu
        self.p11, self.p12, self.p16, self.eu = pilot11, pilot12, pilot16, eu
        import mesaj_kapisi                       # GOREV_0020: koyu murekkep tagline duzeltmesi
        mesaj_kapisi.duzeltme_uygula(pilot12, pilot16)
        self.sab = json.loads((K / 'scripts' / 'kisisel' / 'ORAN_SABITLERI.json').read_text())
        self.kilitler = self.sab.get('edisyonlar', {})
        self.plate_indi = {}

    def plate(self, ed, oran, boy):
        """ZEMIN = MEDYAN PLATE (Serdar onayi 25 Eyl 2026).

        Eski `HAZIR/zemin_<ed>_<oran>.png` yerine 78 ciftin ortancasi kullanilir.
        Olcum (kosu 36153249586): eski zemin ile WP dosyasi arasinda murekkep disi
        fark p50 = 8 / p90 = 25 idi; plate ile p50 = 0 / p99 = 3. Ogeler ancak bu
        girdiyle ayrilabiliyor. Render kodu degismez: `oran_kur` zemin dosyasini
        ayni yerden okur, yalnizca icerigi degisir.
        Plate (edisyon, BOY) bazlidir: ayni oranin farkli boyu farkli plate'tir.
        """
        if not boy:
            raise SystemExit(f'{ed}/{oran}: plate icin boy gerekli')
        hed = self.eu.YOL / ed / 'zemin'
        hed.mkdir(parents=True, exist_ok=True)
        hedef = hed / f'{oran}.png'
        if self.plate_indi.get((ed, oran)) == boy and hedef.exists():
            return hedef
        ad = f'{ed.upper()}{PLATE_EK}_{boy}.png'
        kaynak = W / 'plates' / ad
        kaynak.parent.mkdir(parents=True, exist_ok=True)
        if not kaynak.exists():
            try:
                rc('copy', f'{PLATES}/{ad}', str(kaynak.parent), timeout=1800)
            except RuntimeError:
                pass
        if not kaynak.exists():
            raise PlateHatasi(f'PLATE YOK: {ad} (PLATES klasorunde yok)', {'plate': ad, 'durum': 'YOK'})
        hedef.write_bytes(kaynak.read_bytes())
        self.plate_indi[(ed, oran)] = boy
        return hedef

    def plate_maske(self, plate_yol):
        """`sayfa_olc` icin murekkep maskesi ureticisi: |dosya - plate|.

        Serdar 3. madde: sembol, glif ve isim yerleri DOSYANIN KENDISINDEN,
        `dosya - plate` farkindan olculur (MB'den kopyalama yok). `sayfa_olc`
        zaten maske parametresi aldigi icin bu bir GIRDI degisikligidir; sayfa_olc
        kodu degismez. Esik 12: olculen murekkep disi p99 0-3, cekirdek > 30.
        Kucuk bilesen eleme ve kenar payi onayli `edisyon_maske` ile ayni.
        """
        return plate_fark_maskesi(plate_yol)

    def olc(self, yol, plate_yol):
        """Sayfa olcumu HER ZAMAN 2400'de (sayfa_olc bu olcekte dogrulandi)."""
        from a1_poster import olcum_duzelt
        olcek_kur(2400)
        ref_norm = self.p11.norm(Image.open(yol).convert('RGB'))[0]
        m = self.eu.murekkep(np.asarray(ref_norm).astype(np.float32))
        o = self.p11.sayfa_olc(yol, maske=self.plate_maske(plate_yol))
        return (*olcum_duzelt(o, m), m)

    def render(self, ed, oran, sayfa_no, o, kilit, isimler, mesaj):
        """Tek olcekte render (NORM_W o an ne ise). Render kodu degismez."""
        import giris_dogrula as gd
        self.eu.REF_SAYFA = sayfa_no
        s, S = self.eu.oran_kur(ed, oran, kilit, o)
        g0, g1 = o['isim_govde']
        s['isim_y'] = (g0 + g1) / 2               # dikey merkez: govde (inen kuyruk haric)
        r = gd.siparis_dogrula(isimler[0], isimler[1], mesaj, None)
        if r['durum'] != 'TAMAM':
            return None, None, None, None, {'durum': 'ELLE KONTROL', 'dogrulama': r}
        import mesaj_kapisi
        mesaj_kapisi.ETKIN['edisyon'] = True       # tagline ton eslemesi yalniz edisyon render'inda
        try:
            with _HamKayit(self.p16) as hk:
                p, bilgi, merkez, x, yeni = self.p16.poster_kur(
                    s, S, {'sol': r['sol']['deger'], 'sag': r['sag']['deger']}, mesaj)
        finally:
            mesaj_kapisi.ETKIN['edisyon'] = False
        return s, S, p, (merkez, yeni), {'olcek': bilgi['olcek'], 'punto': bilgi['punto'],
                                         'yeni_ham': hk.maske()}

    def __call__(self, kaynak_bayt, sayfa_no, ed, oran, isimler, mesaj,
                 hedef_en=None, boy=None):
        from a1_poster import sembol_kapisi, SEMBOL_ESIK
        t0 = time.time()
        kilit = self.kilitler.get(ed, {}).get(oran)
        if not kilit:
            raise SystemExit(f'{ed} {oran} icin ORAN_SABITLERI kilidi yok')
        plate_yol = self.plate(ed, oran, boy)
        ham = self.eu.YOL / ed / 'ham'; ham.mkdir(parents=True, exist_ok=True)
        yol = ham / f'{oran}_p{sayfa_no}.jpg'
        yol.write_bytes(kaynak_bayt) if kaynak_bayt[:3] == b'\xff\xd8\xff' else \
            Image.open(io.BytesIO(kaynak_bayt)).convert('RGB').save(yol, 'PNG')
        # Olcum kaynagi (Serdar onayi 25 Eyl, 3. madde): HER DOSYA KENDISINDEN.
        # MB'den kutu kopyalama KALDIRILDI - AQUARIUS^2 A3'te CI 29 px, WP 58 px
        # kayik oldugu olculdu (kosu 36153249586); yerlesim her renkte ayni degil.
        o, duz, m = self.olc(yol, plate_yol)

        # 1) ONAYLI 2400 render (referans, butun mevcut kapilar burada kosar)
        olcek_kur(2400)
        try:
            boy0, yer0 = {}, {}
            with IsimPlakasi(kayit=boy0), _SatirYerlesim(self.p16, yer0):
                s0, S0, p0, ek0, bi0 = self.render(ed, oran, sayfa_no, o, kilit, isimler, mesaj)
        except KeyError as e:
            # Eski oge ayristirilamadi (WP 1. iterasyon: KeyError 'sembol_sol').
            # Yigin izi yerine OLCUM raporlanir; siparis durur ama kosu devam eder.
            self.eu.REF_SAYFA = sayfa_no
            return None, {'durum': 'SISTEM HATASI', 'edisyon': ed, 'oran': oran,
                          'hata': f'oge baglanamadi: KeyError {e}',
                          'oge_tanisi': oge_tanisi(self.eu, self.p16, ed, oran, o),
                          'olcum_kaynagi': 'kendi dosyasi (dosya - plate)'}, None
        if p0 is None:
            return None, bi0, None
        merkez0, yeni0 = ek0
        kapi0 = self.p16.blok_kapisi(p0, S0, s0, yeni0)
        sk, kirp = sembol_kapisi(p0, S0, s0, merkez0, m, SEMBOL_ESIK,
                                 maske=self.eu.murekkep, doku=(ed == 'vintage'))
        maske0 = (S0['genis'] | yeni0)
        silinen0 = S0['genis'] & ~yeni0

        # 2) HEDEF COZUNURLUK render (Serdar 1. madde)
        hedef_en = int(hedef_en or 2400)
        if hedef_en != 2400:
            k = hedef_en / 2400.0
            olcek = olcek_kur(hedef_en)
            kilit1 = kilit_olcekle(kilit, k)
            capmap = {kilit['cap'][y]: kilit1['cap'][y] for y in kilit['cap']}
            sabit = {(mt, capmap.get(c, c)): b * k for (mt, c), b in boy0.items()}
            with IsimPlakasi(sabit=sabit), (_SatirYerlesim(self.p16, yer0, k) if SATIR_OLCEKLI['etkin'] else _SatirYerlesim(self.p16, {})):
                s1, S1, p1, ek1, bi1 = self.render(ed, oran, sayfa_no, olcekle(o, k),
                                                   kilit1, isimler, mesaj)
            merkez1, yeni1 = ek1
            maske1 = (S1['genis'] | yeni1)
            silinen1 = S1['genis'] & ~yeni1
            leke = {'gecti': None, 'uygulandi': False,
                    'sebep': 'baski dosyasi uretildikten sonra olculur'}
            # Hi-res geometriyi kendi piksel uzayinda olc. Render'i 2400'e BOX ile
            # kucultup tekrar esiklemek harf kenarlarini degistiriyor ve dogru ciktiyi
            # reddediyordu. Farklar asagida 2400 birimine normalize edilir.
            g1 = self.eu.satir_olc(
                np.asarray(p1.convert('RGB')).astype(np.float32), s1['isim_bant'])
            olcek_kur(2400)
            g0 = self.eu.satir_olc(
                np.asarray(p0.convert('RGB')).astype(np.float32), s0['isim_bant'])
            olcek_kapi = olcek_kapisi(g1, g0, k, p1.size, p0.size)
        else:
            k, s1, S1, p1 = 1.0, s0, S0, p0
            maske1, silinen1, yeni1 = maske0, silinen0, yeni0
            olcek = {'hedef_en': 2400, 'k': 1.0}
            leke = {'gecti': None, 'uygulandi': False,
                    'sebep': 'baski dosyasi uretildikten sonra olculur'}
            olcek_kapi = {'gecti': True, 'not': 'hedef zaten 2400'}
            bi1 = bi0

        bilgi = {
            'durum': 'URETILDI', 'edisyon': ed, 'oran': oran, 'sayfa': sayfa_no,
            'olcum_kaynagi': 'kendi dosyasi (dosya - plate)', 'plate': str(plate_yol),
            'kaynak_px': list(Image.open(yol).size), 'poster_px': list(p1.size),
            'olcek': olcek, 'olcek_kapisi': olcek_kapi, 'leke_kapisi': leke,
            'olcum': {a: o.get(a) for a in ('isim_bant', 'isim_govde', 'sembol_bant',
                                            'sembol', 'tag_bant', 'sol_isim', 'sag_isim')},
            'olcum_duzeltme': duz,
            'kilit': {'bosluk': kilit['bosluk'], 'cap': kilit['cap']},
            'temiz_ara_kapisi': s0['temiz_ara_kapisi'], 'kalinti_kapisi': kapi0,
            'sembol_kapisi': sk, 'punto_2400': bi0['punto'], 'punto_hedef': bi1['punto'],
            'sure_sn': round(time.time() - t0, 1),
        }
        bilgi['olcek_kapisi_eski'] = bilgi.pop('olcek_kapisi')    # asil kapi BASKI uzerinde
        return p1, bilgi, {'maske': maske1, 'silinen': silinen1, 'kirp': kirp,
                           'maske_2400': maske0, 'silinen_2400': silinen0, 'p0': p0,
                           'yeni': yeni1, 'yeni_2400': yeni0, 'yeni_ham': bi1.get('yeni_ham')}


def oge_tanisi(eu, p16, ed, oran, o28):
    """SALT OKUR tani: (ref, zemin) ciftinde eski ogeler ayrilabiliyor mu?

    1. iterasyonda Warm Parchment `KeyError: 'sembol_sol'` ile durdu: oge_ve_yildiz
    hedeflerin bir kismina hicbir bilesen baglayamadi ve olcum yerine yigin izi
    raporlandi. Bu fonksiyon hatanin yerine SAYI koyar: fark yuzdelikleri, bilesen
    sayisi, en buyuk bilesenin alani/kutusu ve her hedefe baglanan bilesenler.
    Iki ayirt edici durum: (a) fark her yerde yuksek -> dilate sonrasi TEK dev bilesen,
    ilk hedef ('sonsuz') onu kapar, geri kalan hedefler bos kalir; (b) fark cok dusuk
    -> hicbir bilesen yok. Kod degistirmez, yalnizca olcer.
    """
    import cv2
    import pilot16
    d = {'edisyon': ed, 'oran': oran}
    try:
        ham = Image.open(eu.YOL / ed / 'ham' / f'{oran}_p{eu.REF_SAYFA}.jpg').convert('RGB')
        ref, _ = eu.norm(ham)
        zem = Image.open(eu.YOL / ed / 'zemin' / f'{oran}.png').convert('RGB')
        zemin, _ = eu.norm(zem)
        if zemin.size != ref.size:
            zemin = zemin.resize(ref.size, Image.LANCZOS)
        ref_a = np.asarray(ref).astype(np.float32)
        zemin_a = np.asarray(zemin).astype(np.float32)
        fark = np.abs(ref_a - zemin_a).max(axis=2)
        ib, sb, tb = o28['isim_bant'], o28['sembol_bant'], o28['tag_bant']
        pay = pilot16.GENISLET + 8
        y0, y1 = max(sb[0] - pay, 0), min(tb[1] + pay, ref.height)
        kes = fark[y0:y1]
        d['tuval_px'] = list(ref.size)
        d['bant'] = {'isim': list(ib), 'sembol': list(sb), 'tag': list(tb)}
        d['fark_yuzdelik'] = {f'p{q}': round(float(np.percentile(kes, q)), 2)
                              for q in (50, 90, 99, 99.9)}
        d['cekirdek_esigi'] = pilot16.CEKIRDEK
        d['cekirdek_ustu_oran'] = round(float((kes > pilot16.CEKIRDEK).mean()), 4)
        ham_m = (kes > pilot16.CEKIRDEK).astype(np.uint8)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pilot16.GENISLET + 1,) * 2)
        n, etiket, stat, _ = cv2.connectedComponentsWithStats(cv2.dilate(ham_m, k), 8)
        alanlar = sorted((int(stat[i][4]) for i in range(1, n)), reverse=True)
        d['bilesen_sayisi'] = int(n - 1)
        d['en_buyuk_bilesen_alan'] = alanlar[0] if alanlar else 0
        d['ilk_bes_alan'] = alanlar[:5]
        d['bant_alani'] = int(kes.shape[0] * kes.shape[1])
        d['en_buyuk_bilesen_pay'] = (round(alanlar[0] / d['bant_alani'], 3)
                                     if alanlar else 0.0)
        hedef = {'sonsuz': pilot16.kume_kutusu(fark, ib, *o28['sonsuz']),
                 'sembol_sol': pilot16.kume_kutusu(fark, sb, *o28['sembol'][0]),
                 'sembol_sag': pilot16.kume_kutusu(fark, sb, *o28['sembol'][1]),
                 'isim_sol': pilot16.kume_kutusu(fark, ib, *o28['sol_isim']),
                 'isim_sag': pilot16.kume_kutusu(fark, ib, *o28['sag_isim'])}
        d['hedef_kutulari'] = {a: [int(v) for v in b] for a, b in hedef.items()}
        bil, _alfa, _g, _y, _yn = pilot16.oge_ve_yildiz(
            fark, [(0, y0, eu.NORM_W, y1)], hedef, eu.murekkep(ref_a))
        d['baglanan_hedefler'] = sorted(bil.keys())
        d['bos_hedefler'] = sorted(set(hedef) - set(bil))
        d['teshis'] = ('fark her yerde yuksek: tek dev bilesen ilk hedefi kapiyor'
                       if d['en_buyuk_bilesen_pay'] > 0.5 else
                       'fark cok dusuk: oge bileseni olusmuyor'
                       if d['bilesen_sayisi'] < len(hedef) else
                       'bilesenler var ama hedef kutulariyla eslesmiyor'
                       if d['bos_hedefler'] else 'tum hedefler baglandi')
    except BaseException as e:                                    # noqa: BLE001
        d['tani_hatasi'] = f'{type(e).__name__}: {e}'
    return d


OLCEK_KONUM = 1         # Serdar 25 Eyl: konum <= 1 px
OLCEK_KENAR = 2         # Serdar 25 Eyl: harf kenari <= 2 px


def olcek_kapisi(g1, g0, k=1.0, hi_res_boyut=None, referans_boyut=None):
    """Hi-res olcumu 2400 biriminde onayli render olcumuyle karsilastirir.

    Iki olcut (Serdar onayi 25 Eyl, 4. madde): KONUM (satir merkezi, bosluklar,
    taban, cap) <= 1 px; HARF KENARI (uc kutunun x kenarlari) <= 2 px.
    Raster kucultulmez: iki render kendi dogal olceginde olculur, hi-res
    koordinatlari k ile bolunur. Boylece yeniden ornekleme kenari kapiya girmez."""
    if 'hata' in g1 or 'hata' in g0:
        return {'gecti': False, 'sebep': f"olculemedi {g1.get('hata')} / {g0.get('hata')}"}
    def norm(v):
        if isinstance(v, (list, tuple)):
            return [x / k for x in v]
        return v / k
    d = {}
    for alan in ('cap_sol', 'cap_sag', 'taban_sol', 'taban_sag'):
        d[alan] = round(norm(g1[alan]) - g0[alan], 2)
    d['satir_merkez'] = round(norm(g1['satir_merkez']) - g0['satir_merkez'], 2)
    d['bosluk_sol'] = round(norm(g1['bosluk'])[0] - g0['bosluk'][0], 2)
    d['bosluk_sag'] = round(norm(g1['bosluk'])[1] - g0['bosluk'][1], 2)
    for ad in ('sol_isim', 'sonsuz', 'sag_isim'):
        d[f'{ad}_x0'] = round(norm(g1[ad])[0] - g0[ad][0], 2)
        d[f'{ad}_x1'] = round(norm(g1[ad])[1] - g0[ad][1], 2)
    konum = ('satir_merkez', 'bosluk_sol', 'bosluk_sag', 'taban_sol', 'taban_sag',
             'cap_sol', 'cap_sag')
    en_k = max(abs(d[a]) for a in konum)
    en_h = max(abs(v) for a, v in d.items() if a not in konum)
    return {'gecti': bool(en_k <= OLCEK_KONUM and en_h <= OLCEK_KENAR),
            'konum_fark_px': en_k, 'kenar_fark_px': en_h,
            'esik': {'konum': OLCEK_KONUM, 'harf_kenari': OLCEK_KENAR},
            'olcum': 'dogal olcek; farklar 2400 px birimine normalize', 'fark': d,
            'boyut': {'hi_res': list(hi_res_boyut or []),
                      'onayli_2400': list(referans_boyut or [])}}


OLCEK_PAY = 10          # satir_olc ile ayni pencere payi (2400 px birimi)
OLCEK_UC = 0.002        # kenar = murekkep kutlesinin %0.2 / %99.8 noktasi


def _uc(profil, q=OLCEK_UC):
    """Kutle profilinin q ve 1-q noktalari (piksel i = [i, i+1), dogrusal ara deger)."""
    cum = np.cumsum(profil)
    T = float(cum[-1])

    def nokta(h):
        i = min(int(np.searchsorted(cum, h)), len(cum) - 1)
        once = float(cum[i - 1]) if i else 0.0
        return i + (h - once) / max(float(profil[i]), 1e-9)
    return nokta(q * T), nokta((1 - q) * T)


def satir_olc_alt(im, bant, k=1.0, pay=OLCEK_PAY):
    """Isim satiri geometrisi 2400 px biriminde, ALT PIKSEL (olcek kapisi icin).

    28 Eyl hata kontrolu (DB/CI/PW 'olcek' FAIL): eski olcum hi-res'te `satir_olc(.., pay=10)`
    kullaniyordu; pay olceklenmedigi icin pencere 2400 biriminde her kenarda 2.7 px dar
    kaliyor, sinirdaki murekkep (yildiz, J kuyrugu) iki olcekte farkli kirpiliyordu. Ayrica
    iki farkli izgaranin TAM SAYI satir/sutun indeksleri karsilastiriliyordu (niceleme
    +-0.86 px, taban icin +0.27 px sistematik). Burada: pencere fiziksel olarak AYNI (sinir
    satirlari kesirli agirlikla), murekkep kapsami 0..1 (murekkep ile zemin medyani
    arasinda), kenarlar kutle dagiliminin uc noktalarindan. Kumeler onayli edisyon maskesiyle
    bulunur; bosluk ve genislik esikleri k ile olceklenir. Kapi esikleri DEGISMEZ.
    `im` PIL goruntu; yalniz pencere satirlari diziye cevrilir (30x40 = 9000 px).
    """
    import cv2
    from pilot6 import LUMA
    eu = _mod('edisyon_uret')
    Y0, Y1 = (bant[0] - pay) * k, (bant[1] + pay) * k
    y0, y1 = max(int(np.floor(Y0)), 0), min(int(np.ceil(Y1)), im.height)
    kes = np.asarray(im.convert('RGB').crop((0, y0, im.width, y1))).astype(np.float32)
    m = eu.murekkep(kes)
    km = [c for c in eu._kumeler(m, max(int(round(20 * k)), 1)) if c[1] - c[0] > 40 * k]
    if len(km) != 3:
        return {'hata': f'{len(km)} kume'}
    L = kes @ LUMA
    mu = m.astype(np.uint8)
    r = max(int(round(3 * k)), 1)
    yakin = cv2.dilate(mu, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2)) > 0
    uzak = ~(cv2.dilate(mu, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4 * r + 1,) * 2)) > 0)
    cekirdek = cv2.erode(mu, np.ones((3, 3), np.uint8)) > 0
    if cekirdek.sum() < 50:
        cekirdek = m
    Li, Lz = float(np.median(L[cekirdek])), float(np.median(L[uzak] if uzak.any() else L))
    if abs(Li - Lz) < 5:
        return {'hata': f'kontrast yok (murekkep {Li:.0f}, zemin {Lz:.0f})'}
    c = np.clip((L - Lz) / (Li - Lz), 0, 1) * yakin
    satir = np.arange(y0, y1)
    c *= np.clip(np.minimum(satir + 1, Y1) - np.maximum(satir, Y0), 0, 1)[:, None]
    Wd = c.shape[1]
    M = max(int(round(eu.UZAT_AZAMI * k)), 1)
    sinir = [0, (km[0][1] + km[1][0]) // 2, (km[1][1] + km[2][0]) // 2, Wd]
    out = {}
    for i, ad in enumerate(('sol_isim', 'sonsuz', 'sag_isim')):
        xa = max(km[i][0] - M, sinir[i]); xb = min(km[i][1] + M, sinir[i + 1])
        C = c[:, xa:xb]
        if C.sum() <= 0:
            return {'hata': f'{ad}: murekkep kutlesi yok'}
        x0, x1 = _uc(C.sum(axis=0))
        out[ad] = [round((xa + x0) / k, 2), round((xa + x1) / k, 2)]
        if ad != 'sonsuz':
            u, t = _uc(C.sum(axis=1))
            y = ad.split('_')[0]
            out[f'ust_{y}'] = round((y0 + u) / k, 2)
            out[f'taban_{y}'] = round((y0 + t) / k, 2)
            out[f'cap_{y}'] = round((t - u) / k, 2)
    out['bosluk'] = [round(out['sonsuz'][0] - out['sol_isim'][1], 2),
                     round(out['sag_isim'][0] - out['sonsuz'][1], 2)]
    out['satir_merkez'] = round((out['sol_isim'][0] + out['sag_isim'][1]) / 2, 2)
    out['kontrast'] = {'murekkep_L': round(Li, 1), 'zemin_L': round(Lz, 1)}
    return out


def olcek_kapisi_baski(baski, p2400, bant):
    """OLCEK KAPISI, uretilen BASKI dosyasi uzerinde: isim satiri onayli 2400 render ile ayni mi.

    Eski kapi hi-res render'i (p1) olcuyordu ve Blue'da hic kosmuyordu (Blue 2400 render
    edip baski_dosyasi'nda buyutuluyor; kapi None). Burada her edisyonda teslim edilen
    dosyanin kendisi olculur: Blue'da buyutme + yerlestirme, digerlerinde hi-res render +
    hibrit birlestirme kapinin icindedir. Esikler ayni (konum <= 1, harf kenari <= 2).
    """
    k = baski.width / float(p2400.width)
    try:
        olcek_kur(baski.width)
        g1 = satir_olc_alt(baski, bant, k)
        olcek_kur(2400)
        g0 = satir_olc_alt(p2400, bant, 1.0)
    except Exception as e:                                        # noqa: BLE001
        return {'gecti': False, 'sebep': f'olculemedi: {type(e).__name__}: {e}'}
    finally:
        olcek_kur(2400)
    r = olcek_kapisi(g1, g0, 1.0, baski.size, p2400.size)
    r['olcum'] = ('BASKI dosyasi vs onayli 2400 render; pencere fiziksel ayni, alt piksel '
                  '(murekkep kutlesi %0.2/%99.8), farklar 2400 px biriminde')
    r['k'] = round(k, 4)
    return r


# ------------------------------------------------------------------ isim bandi kalintisi (GIFT_9518, 29 Eyl)
# Bulgu (Serdar reddi, %100 kirpim): isim satirinda eski burc yazisinin (ARIES / SCORPIO) ince
# uclari. KAYNAK (3. iterasyonda olculdu): MEDYAN PLATE'IN ISIM BANDI TEMIZ DEGIL -
# PLATES/BLUE_11x14.png'de ayni noktada altin var (plate 164,126,32 / baski 166,128,31); plate
# temizligi yalniz slogan bandini kapsiyordu. Plate'i "temiz zemin" sayan her duzeltme ve kapi
# bu yuzden kordu (1. ve 2. iterasyon).
# Duzeltme (Serdar onayi 29 Eyl): isim bandinda render'in YENI OGE kaydi (poster_kur yeni_genis:
# yeni isimler + tasinan sonsuzluk/semboller + tagline, 3 px) DISINDAKI her yer, bandin hemen
# ustundeki ve altindaki temiz seritlerin capraz karisimiyla (onayli slogan temizleme yontemi,
# plate_uret.slogan_temizle) kurulan zeminle degistirilir. PLATE KULLANILMAZ.
# Kapi (plate'ten bagimsiz): ayni bolgede, yeni oge kaydi (+1 px) disinda YEREL ZEMINE (medyan)
# gore altin murekkep varsa FAIL.
ISIM_KALINTI_ESIK = 24.0   # |L - yerel medyan zemin| (kapi)
ISIM_KALINTI_ALAN = 1      # bilesen alani (2400 uzayinda px^2) x k^2, en az 2 px (olculen leke 3-30 px)
ISIM_BANT_PAY = 0.25       # isim bandi dikey payi (bant yuksekligi orani)
ISIM_YAN_PAY = 60          # sutun araligi: eski/yeni isimlerin disina pay (2400 px)
ZEMIN_YARICAP = 31         # yerel zemin medyani (2400 px)
DOLGU_MUREKKEP = 16.0      # kaynak seritte bu kontrasttan fazlasi murekkep sayilir (dolguya girmez)
# 4. iterasyon (Serdar onayi 29 Eyl): koruma = HAM yeni oge maskesi (harfin kendi siniri, alfa > 8;
# 3 px KAPI_PAY yok). MB 11x14'te pay icinde kalan soluk izler altin degil zemine gore renk kaymasi
# (orn. 37,22,27 / zemin 0,6,32: dL 22, R-B 10) -> eski olcut (dL > 24 ve R-B > 20) goremiyordu.
# Soluk iz: (R-B) yerel medyana gore > ISIM_IZ_RB ve |dL| > ISIM_IZ_L. Olculen gurultu (MB,
# temiz dolgu, q92): R-B kaymasi en cok 10, |dL| en cok 5.3; izler 20-44 / 7-25.
ISIM_IZ_RB = 14.0
ISIM_IZ_L = 5.0
KENAR_HALKA = 3            # kenar kapisi: korumanin disinda bakilan halka (baski px)
ISIM_KALINTI_PAY = 4       # temizlik: kalinti bileseninin cevresine pay (2400 px)


def _isim_satirlari(olcum, k, H):
    y0, y1 = olcum['isim_bant']
    h = y1 - y0
    a0, a1 = (y0 - ISIM_BANT_PAY * h) * k, (y1 + ISIM_BANT_PAY * h) * k
    sb = olcum.get('sembol_bant')
    if sb:
        a0 = max(a0, (sb[1] + 2) * k)                  # sembollere tasma
    tb = olcum.get('tag_bant')
    if tb:
        a1 = min(a1, (tb[0] - 2) * k)
    return max(int(a0), 0), min(int(np.ceil(a1)), H)


def _yeni_tam(yeni, boyut, pay_2400=0, ham=False):
    """poster_kur yeni_genis maskesi baski boyunda (tam sayfa), istenirse ek pay.
    ham=True: HAM maske (alfa > 8); dogrusal olceklenir, kismen degen her baski pikseli korunur."""
    import cv2
    Wd, H = boyut
    k = Wd / 2400.0
    if ham:
        f = np.asarray(yeni, np.float32)
        if f.shape != (H, Wd):
            f = cv2.resize(f, (Wd, H), interpolation=cv2.INTER_LINEAR)
        return f > 0.01
    m = cv2.resize(np.asarray(yeni, np.uint8), (Wd, H), interpolation=cv2.INTER_NEAREST)
    p = int(round(pay_2400 * k))
    if p > 0:
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * p + 1,) * 2))
    return m > 0


def _isim_sutunlari(olcum, Yb, k, Wd):
    """Eski isimlerin (kaynak olcumu) ve yeni ogelerin yatay uzanimi + pay; cerceveye dokunulmaz."""
    xs = []
    for a in ('sol_isim', 'sag_isim'):
        if olcum.get(a):
            xs += [olcum[a][0] * k, olcum[a][1] * k]
    c = np.nonzero(Yb.any(axis=0))[0]
    if len(c):
        xs += [float(c.min()), float(c.max())]
    if not xs:
        return int(Wd * 0.05), int(Wd * 0.95)
    p = ISIM_YAN_PAY * k
    return max(int(min(xs) - p), int(Wd * 0.03)), min(int(max(xs) + p), int(Wd * 0.97))


def _yerel_zemin(L, k, haric=None, kaydir=0.0):
    """Yerel medyan zemin. `haric` (korunan harf pikselleri) verilirse medyana GIRMEZ: once bant
    medyaniyla, sonra ilk tahminle doldurulup iki gecisle olculur. 29 Eyl CI bulgusu: sik harflerin
    arasinda (M, N ici) 31 px medyan koyu murekkebe cekiliyor, acik zemin 'murekkep' okunuyordu."""
    import cv2
    r = max(int(round(ZEMIN_YARICAP * k)) | 1, 3)
    r = min(r, 255)

    def mb(x):
        return cv2.medianBlur(np.clip(x + kaydir, 0, 255).astype(np.uint8), r).astype(np.float32) - kaydir
    if haric is None or not haric.any() or haric.all():
        return mb(L)
    h = cv2.dilate(haric.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if h.all():
        return mb(L)
    X = L.copy(); X[h] = float(np.median(L[~h]))
    Z = mb(X)
    X[h] = Z[h]
    return mb(X)


def _serit_murekkebi(S, k):
    """Kaynak seritte murekkep (sembol, yazi, eski ic): yerel kontrast > DOLGU_MUREKKEP, genisletilmis."""
    import cv2
    L = S @ np.array([0.299, 0.587, 0.114], np.float32)
    m = (np.abs(L - _yerel_zemin(L, k)) > DOLGU_MUREKKEP).astype(np.uint8)
    d = max(int(round(3 * k)), 1)
    return cv2.dilate(m, np.ones((2 * d + 1,) * 2, np.uint8)) > 0


def _iz_haritasi(Bb, k, haric=None, esik=None):
    """Isim bandi parcasinda iz olcutleri: (altin murekkep, soluk iz, dL, R-B kaymasi).
    haric: korunan (yeni oge) pikseller; yerel zemin tahminine girmez.
    esik: _iz_esikleri (zemin dokusuna gore); verilmezse sabit esikler."""
    e = esik or {'altin_L': ISIM_KALINTI_ESIK, 'soluk_L': ISIM_IZ_L, 'soluk_rb': ISIM_IZ_RB}
    L = Bb @ np.array([0.299, 0.587, 0.114], np.float32)
    dL = L - _yerel_zemin(L, k, haric)
    rb = Bb[..., 0] - Bb[..., 2]
    ws = rb - _yerel_zemin(rb, k, haric, kaydir=128.0)
    altin = (np.abs(dL) > e['altin_L']) & (rb > 20)
    # 30 Eyl (ARIES_SCORPIO MB 11x14): soluk iz YONLU. Altin iz koyu zeminde zeminden ACIK, acik zeminde KOYU;
    # |dL| zeminden koyu mavi bir satiri (0,0,17 / zemin 1,5,29, dL -5.7) JPEG gurultusuyle iz sayiyordu.
    yon = 1.0 if float(np.median(L)) < 128.0 else -1.0
    soluk = (ws > e['soluk_rb']) & (yon * dL > e['soluk_L'])
    return altin, soluk, dL, ws


# 30 Eyl (WP AQUARIUS_CANCER): parsomen dokusunda sabit esikler dokunun kendisini iz sayiyordu (920 bilesen)
# ve tum banda uygulanan dolgu dokuyu bozuyordu. Esikler bandin hemen ustu / alti SERITLERINDEKI zemin
# gurultusunden olculur (plate'ten bagimsiz, her dosya kendisinden): p99.99 x IZ_GURULTU_KAT, sabit esikler
# alt sinir. Seritte guclu murekkep (|dL| > 60, sembol / tagline) olcume girmez.
IZ_GURULTU_KAT = 1.25
IZ_YUZDELIK = 99.99
IZ_SERIT_MUREKKEP = 60.0


def _iz_esikleri(B, r0, r1, c0, c1, k, koruma=None):
    import cv2
    H = B.shape[0]; h = r1 - r0
    dls, wss = [], []
    for y0, y1 in ((max(r0 - h, 0), r0), (r1, min(r1 + h, H))):
        if y1 - y0 < 4:
            continue
        S = B[y0:y1, c0:c1]
        hr = None if koruma is None else koruma[y0:y1, c0:c1]
        _a, _s, dL, ws = _iz_haritasi(S, k, hr)
        m = np.abs(dL) > IZ_SERIT_MUREKKEP
        m = cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        if hr is not None:
            m |= hr
        dls.append(np.abs(dL)[~m]); wss.append(ws[~m])
    if not dls or not sum(x.size for x in dls):
        return {'altin_L': ISIM_KALINTI_ESIK, 'soluk_L': ISIM_IZ_L, 'soluk_rb': ISIM_IZ_RB, 'kaynak': 'sabit'}
    dl = np.concatenate(dls); ws = np.concatenate(wss)
    qL = float(np.percentile(dl, IZ_YUZDELIK)) * IZ_GURULTU_KAT
    qW = float(np.percentile(ws, IZ_YUZDELIK)) * IZ_GURULTU_KAT
    return {'altin_L': round(max(ISIM_KALINTI_ESIK, qL), 1), 'soluk_L': round(max(ISIM_IZ_L, qL), 1),
            'soluk_rb': round(max(ISIM_IZ_RB, qW), 1), 'kaynak': 'serit',
            'serit_p999': [round(qL / IZ_GURULTU_KAT, 1), round(qW / IZ_GURULTU_KAT, 1)]}


def isim_kenar_kapisi(once, sonra, koruma, satir, sutun, k):
    """Kenar kirpilmasi = FAIL. (a) korunan (ham maske) piksellerden hic biri degismedi;
    (b) korumanin hemen disindaki halkada (KENAR_HALKA px) GUCLU harf murekkebi (|dL| > harf
    kontrastinin yarisi, korunan harfe 8-bagli) tasiyan hic bir piksel degismedi (govde kesilmedi);
    (c) bilgi: harf murekkebinin koruma icinde kalma payi (hiza kontrolu)."""
    import cv2
    r0, r1 = satir; c0, c1 = sutun
    A = once[r0:r1, c0:c1]; B = sonra[r0:r1, c0:c1]; P = koruma[r0:r1, c0:c1]
    deg = np.abs(B - A).max(axis=2) > 0.5
    L = A @ np.array([0.299, 0.587, 0.114], np.float32)
    dLs = L - _yerel_zemin(L, k, P)
    # harfin yonu: acik zeminde koyu harf (CI, PW) negatif, koyu zeminde acik harf pozitif
    yon = -1.0 if (P.any() and float(np.median(dLs[P])) < 0) else 1.0
    dL = yon * dLs
    kon = float(np.median(dL[P])) if P.any() else 0.0
    esik = max(0.5 * kon, 40.0)
    rb = A[..., 0] - A[..., 2]
    rb_harf = float(np.median(rb[P & (dL > esik)])) if (P & (dL > esik)).any() else 0.0
    guclu = (dL > esik) & (np.abs(rb - rb_harf) < 70)       # harf rengi (yildiz / zemin degil)
    # harf govdesi = korunan harf murekkebine 8-bagli guclu pikseller (bagimsiz yildiz / leke sayilmaz)
    n, lab = cv2.connectedComponents(guclu.astype(np.uint8), connectivity=8)
    bagli = np.zeros(n, bool); bagli[np.unique(lab[guclu & P])] = True; bagli[0] = False
    guclu = bagli[lab]
    d = KENAR_HALKA
    halka = (cv2.dilate(P.astype(np.uint8), np.ones((2 * d + 1,) * 2, np.uint8)) > 0) & ~P
    ic = int((deg & P).sum())
    kesik = int((deg & halka & guclu).sum())
    harf = guclu & (P | halka)
    pay = round(float((guclu & P).sum()) / max(int(harf.sum()), 1), 4)
    return {'gecti': ic == 0 and kesik == 0, 'korunan_degisen_px': ic, 'kesilen_harf_px': kesik,
            'harf_murekkebi_koruma_icinde': pay, 'guclu_esik': round(esik, 1),
            'halka_px': d, 'olcut': 'korunan (ham maske) 0 degisim; halkada guclu harf murekkebi 0 degisim'}


ALAN_PAY = 6               # render bolgesi (degisim maskesi) genisletmesi, 2400 px


def _alan_tam(alan, boyut):
    """Render bolgesi (ek['maske'], degisim maskesi) baski boyunda + ALAN_PAY. 30 Eyl WP AQUARIUS_CANCER:
    bu bolgenin DISI kaynak dosyanin kendisidir (eski isim kalintisi orada olamaz); dokulu zeminde temizlik
    ve kapi orada kaynak dokusunu iz sayip leke / isim_kenar kapilarini dusuruyordu."""
    if alan is None:
        return None
    import cv2
    Wd, H = boyut
    m = _yeni_tam(np.asarray(alan, np.float32), (Wd, H), ham=True)
    p = max(int(round(ALAN_PAY * Wd / 2400.0)), 1)
    return cv2.dilate(m.astype(np.uint8), np.ones((2 * p + 1,) * 2, np.uint8)) > 0


def isim_bandi_temizle(out, yeni, olcum, ham=False, alan=None):
    """out: baski boyunda (float32, birlestirilmis). Isim bandinda yeni oge kaydi DISI, bandin ustu ve
    alti seritlerinin capraz karisimi + bandin kendi (murekkepsiz) dusuk frekans tonuyla doldurulur."""
    import cv2
    H, Wd = out.shape[:2]
    k = Wd / 2400.0
    r0, r1 = _isim_satirlari(olcum, k, H)
    h = r1 - r0
    if h < 4:
        return out, {'uygulandi': False, 'sebep': 'isim bandi yok'}
    Yt = _yeni_tam(yeni, (Wd, H), ham=ham)
    c0, c1 = _isim_sutunlari(olcum, Yt[r0:r1], k, Wd)
    D = h + max(int(0.3 * h), 4)                        # kaynak otelemesi (plate_uret ile ayni mantik)
    kes = out[r0:r1, c0:c1]
    Yb = Yt[r0:r1, c0:c1]
    w = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    toplam = np.zeros(kes.shape, np.float32); agir = np.zeros(kes.shape[:2], np.float32)
    kaynak = {}
    for ad, y, ag in (('ust', r0 - D, 1.0 - w), ('alt', r0 + D, w)):
        if y < 0 or y + h > H:
            continue
        S = out[y:y + h, c0:c1]
        temiz = ~(_serit_murekkebi(S, k) | Yt[y:y + h, c0:c1])
        a_ = np.broadcast_to(ag, temiz.shape) * temiz
        toplam += S * a_[..., None]; agir += a_
        kaynak[ad] = round(float(temiz.mean()), 3)
    sg = max(18.0 * k, 3.0)
    gecerli = agir > 0.05
    dolgu = np.where(gecerli[..., None], toplam / np.maximum(agir, 1e-3)[..., None], 0)
    # yuksek frekans: NORMALIZE bulaniklik (30 Eyl: gecersiz 0 pikseller bulaniga karisip hf'i 255 ustune
    # tasiyordu -> WP'de parlak lekeler). Seritteki dokunun kendi genligiyle sinirlanir.
    vw = gecerli.astype(np.float32)
    vden = np.maximum(cv2.GaussianBlur(vw, (0, 0), sg), 1e-3)
    bd = np.dstack([cv2.GaussianBlur(dolgu[..., c] * vw, (0, 0), sg) / vden for c in range(3)])
    hf = np.where(gecerli[..., None] & (vden[..., None] > 0.2), dolgu - bd, 0)
    if gecerli.any():
        sin = float(np.percentile(np.abs(hf[gecerli]), 99.5)) + 1.0
        hf = np.clip(hf, -sin, sin)
    # 30 Eyl: dolgu yalniz KALINTININ cevresine uygulanir (tum bant degil). Kalinti = iz olcutu, esikler
    # zemin dokusundan; bilesen >= 2 px; ISIM_KALINTI_PAY px genisletilir. Doku ve harf kenari korunur.
    esik = _iz_esikleri(out, r0, r1, c0, c1, k, Yt)
    altin, soluk, _dL, _ws = _iz_haritasi(kes, k, Yb, esik)
    iz = (altin | soluk) & ~Yb
    Ab = _alan_tam(alan, (Wd, H))
    if Ab is not None:                                  # 30 Eyl: yalniz render bolgesi (disi kaynagin kendisi)
        iz &= Ab[r0:r1, c0:c1]
    iz = iz.astype(np.uint8)
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(iz, 8)
    iz = np.isin(lab_, [i for i in range(1, n_) if st_[i][4] >= 2])
    pay = max(int(round(ISIM_KALINTI_PAY * k)), 2)
    R = (cv2.dilate(iz.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pay + 1,) * 2)) > 0) & ~Yb
    # dusuk frekans ton: bandin KENDI murekkepsiz, yeni-disi pikselleri (normalize bulaniklik).
    # 30 Eyl: dokulu zeminde (WP) agirlik ~0'a dusuyor, 1e-6'ya bolme parlak leke uretiyordu -> korunur.
    tw = (~(_serit_murekkebi(kes, k) | Yb | R)).astype(np.float32)
    if tw.mean() < 0.05:                                # dokulu zemin: kalinti ve harf disi her piksel
        tw = (~(Yb | R)).astype(np.float32)
    den = cv2.GaussianBlur(tw, (0, 0), sg)
    zem = np.median(kes[tw > 0], 0) if (tw > 0).any() else np.median(kes.reshape(-1, 3), 0)
    lf = np.dstack([np.where(den > 0.02, cv2.GaussianBlur(kes[..., c] * tw, (0, 0), sg) / np.maximum(den, 0.02),
                             zem[c]) for c in range(3)])
    dolgu = lf + hf
    Ef = np.clip(cv2.GaussianBlur(R.astype(np.float32), (0, 0), max(k, 0.8)) * 2.0, 0, 1)
    Ef[R] = 1.0
    Ef[Yb] = 0.0
    once = out
    out = out.copy()
    out[r0:r1, c0:c1] = kes * (1 - Ef[..., None]) + dolgu * Ef[..., None]
    kenar = isim_kenar_kapisi(once, out, Yt, (r0, r1), (c0, c1), k)
    return out, {'uygulandi': True, 'koruma': 'ham' if ham else 'genis', 'satir': [r0, r1],
                 'sutun': [c0, c1], 'kaynak_temiz_payi': kaynak, 'esik': esik,
                 'kalinti_bileseni': int(n_ - 1), 'degisen_px': int((Ef > 0.5).sum()), 'kenar': kenar}


def isim_kalinti_kapisi(baski, yeni, olcum, ham=False, alan=None):
    """Plate'ten BAGIMSIZ: isim bandinda yeni oge kaydi (+1 px) disinda, yerel zemine gore altin
    murekkep (|L - medyan| > esik ve R-B > 20) varsa FAIL. (BASKI uzerinde)"""
    import cv2
    d = {'esik': ISIM_KALINTI_ESIK, 'alan_2400': ISIM_KALINTI_ALAN,
         'olcut': 'isim bandi, |L - yerel medyan zemin| > esik ve altin (R-B > 20), yeni oge kaydi '
                  '(poster_kur yeni_genis 3 px + 1) disi'}
    try:
        if yeni is None:
            return {**d, 'gecti': False, 'hata': 'yeni oge maskesi yok'}
        B = np.asarray(baski.convert('RGB')).astype(np.float32)
        H, Wd = B.shape[:2]
        k = Wd / 2400.0
        r0, r1 = _isim_satirlari(olcum, k, H)
        Yt = _yeni_tam(yeni, (Wd, H), 0 if ham else 1, ham=ham)
        c0, c1 = _isim_sutunlari(olcum, Yt[r0:r1], k, Wd)
        esik = _iz_esikleri(B, r0, r1, c0, c1, k, Yt)
        d['esikler'] = esik
        altin, soluk, _dL, _ws = _iz_haritasi(B[r0:r1, c0:c1], k, Yt[r0:r1, c0:c1] if ham else None, esik)
        if ham:
            d['olcut'] = ('isim bandi, altin murekkep (|dL| > esik ve R-B > 20) VEYA soluk iz (R-B kaymasi > '
                          f'{ISIM_IZ_RB} ve |dL| > {ISIM_IZ_L}), HAM yeni oge maskesi (harfin kendi siniri) disi')
            altin = altin | soluk
        kal = altin & ~Yt[r0:r1, c0:c1]
        Ab = _alan_tam(alan, (Wd, H))
        if Ab is not None:
            kal &= Ab[r0:r1, c0:c1]
            d['alan'] = 'render bolgesi (degisim maskesi) + %d px' % ALAN_PAY
        kal = kal.astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(kal, 8)
        en_az = max(int(round(ISIM_KALINTI_ALAN * k * k)), 2)
        parca = [{'x': int(st[i][0] + c0), 'y': int(st[i][1] + r0), 'w': int(st[i][2]), 'h': int(st[i][3]),
                  'alan': int(st[i][4]), 'x_2400': round(float((st[i][0] + c0) / k), 1)}
                 for i in range(1, n) if st[i][4] >= en_az]
        parca.sort(key=lambda z: -z['alan'])
        return {**d, 'gecti': not parca, 'kalinti_sayisi': len(parca), 'kalintilar': parca[:12],
                'satir': [r0, r1], 'sutun': [c0, c1]}
    except Exception as e:                                        # noqa: BLE001
        return {**d, 'gecti': False, 'hata': f'{type(e).__name__}: {e}'}


def iz_olc(baski, kutu, yeni, ham=True):
    """Kutu (x0, y0, x1, y1, baski px) icinde, koruma disinda soluk iz / altin murekkep piksel sayisi
    ve en buyuk R-B kaymasi / |dL| (Serdar'in bildirdigi noktalar icin: sayi 0 olmali)."""
    B = np.asarray(baski.convert('RGB')).astype(np.float32)
    H, Wd = B.shape[:2]
    k = Wd / 2400.0
    x0, y0, x1, y1 = kutu
    r = int(ZEMIN_YARICAP * k) + 8
    a0, a1, b0, b1 = max(y0 - r, 0), min(y1 + r, H), max(x0 - r, 0), min(x1 + r, Wd)
    Pk = None if yeni is None else _yeni_tam(yeni, (Wd, H), 0 if ham else 1, ham=ham)[a0:a1, b0:b1]
    altin, soluk, dL, ws = _iz_haritasi(B[a0:a1, b0:b1], k, Pk if ham else None)
    ic = np.zeros(altin.shape, bool); ic[y0 - a0:y1 - a0, x0 - b0:x1 - b0] = True
    if Pk is not None:
        ic &= ~Pk
    iz = (altin | soluk) & ic
    return {'iz_px': int(iz.sum()), 'rb_kayma_max': round(float(ws[ic].max()) if ic.any() else 0.0, 1),
            'dL_max': round(float(np.abs(dL[ic]).max()) if ic.any() else 0.0, 1)}


def nokta_olc(baski, x, y, yaricap=(6, 4), yeni=None):
    """Bir noktada yerel zemine gore en guclu altin murekkep (kontrol noktasi dogrulamasi).
    `yeni` verilirse yeni oge kaydi (+1 px, kapiyla ayni) olcumden cikarilir: pencere yeni harfin
    kendisine tasarsa harf leke sayilmasin (29 Eyl: 8x10 'L' ayak serifi 165-172 olculdu)."""
    B = np.asarray(baski.convert('RGB')).astype(np.float32)
    k = B.shape[1] / 2400.0
    r = int(ZEMIN_YARICAP * k) + 8
    y0, y1 = max(y - r, 0), min(y + r, B.shape[0]); x0, x1 = max(x - r, 0), min(x + r, B.shape[1])
    Bb = B[y0:y1, x0:x1]
    L = Bb @ np.array([0.299, 0.587, 0.114], np.float32)
    f = np.abs(L - _yerel_zemin(L, k)) * (((Bb[..., 0] - Bb[..., 2]) > 20))
    if yeni is not None:
        f[_yeni_tam(yeni, (B.shape[1], B.shape[0]), 1)[y0:y1, x0:x1]] = 0.0
    yy, xx = y - y0, x - x0
    w = f[max(yy - yaricap[1], 0):yy + yaricap[1] + 1, max(xx - yaricap[0], 0):xx + yaricap[0] + 1]
    return round(float(w.max()) if w.size else 0.0, 1)


def koruma(ek):
    """Isim bandi korumasi: ham yeni oge maskesi varsa o (harfin kendi siniri), yoksa yeni_genis."""
    if ek.get('yeni_ham') is not None:
        return ek['yeni_ham'], True
    return ek.get('yeni'), False


class _HamKayit:
    """poster_kur'un HAM yeni oge maskesini (isaretle ile alfa > 8 isaretlenen; KAPI_PAY genisletmesi
    YOK) yakalar: pilot16.isaretle cagri suresince sarilir, hedef dizinin referansi tutulur. Render
    kodu degismez (29 Eyl, GIFT_9518 iter. 4: koruma payi harfin kendi sinirina daralir)."""

    def __init__(self, p16):
        self.p16, self.ham = p16, None

    def __enter__(self):
        self.asil = self.p16.isaretle

        def sar(hedef, maske, x, y):
            self.ham = hedef
            return self.asil(hedef, maske, x, y)
        self.p16.isaretle = sar
        return self

    def __exit__(self, *a):
        self.p16.isaretle = self.asil
        return False

    def maske(self):
        return None if self.ham is None else (np.asarray(self.ham) > 0)


MB_HEDEF = {'etkin': False}        # dijital MB: isim / mesaj bandi hedef cozunurlukte (BluePoster.hedef_render)
GENISLIK_AZAMI = 0.02     # 3. dijital deneme: isim plakasi yatay yeniden ornekleme siniri (1 Eki)
SATIR_OLCEKLI = {'etkin': False}   # pod_uret: yalniz olcek kapisi FAIL olunca ikinci render (regresyon 36756875368)


class _SatirYerlesim:
    """Isim satiri yerlesimi: hi-res render 2400 yerlesimini OLCEKLER (30 Eyl, GEMINI_LEO DB olcek konum 1.18).

    Kok neden (olcek_tani 36749680993): pilot16.poster_kur satiri her olcekte TAM SAYI kutu genisliklerinden
    yeniden kurar (isim plakasi genisligi, sonsuz kesit kutusu w / pay). Hi-res'te bu genislikler 2400*k'dan
    0.3-1.1 birim sapar ve satir boyunca birikir: GEMINI_LEO 11x14'te sonsuz kutusu 1.13 birim dar, sag isim
    1.37 birim kayik (kontrol ciftlerinde 0.37-0.65). Duzeltme: 2400 cagrisinda murekkep konumlari kaydedilir;
    hi-res cagrisinda isimler murekkep merkezinden, sonsuz kaynak konumuna gore ayni kaydirma * k ile konur.
    poster_kur'un geri kalani (plaka, tagline, semboller, maskeler) birebir aynidir; yalniz `x` hesabi degisir."""

    def __init__(self, p16, kayit, k=None):
        self.p16, self.kayit, self.k = p16, kayit, k

    def __enter__(self):
        self.asil = self.p16.poster_kur
        self.p16.poster_kur = self._kaydet if self.k is None else self._olcekli
        return self

    def __exit__(self, *a):
        self.p16.poster_kur = self.asil
        return False

    @staticmethod
    def _kutle(a):
        """Alfa / maske kutlesinin yatay merkezi ve ust kenari (_uc %0.2 / %99.8, olcek kapisiyla ayni tanim)."""
        a = np.asarray(a, np.float32)
        x0, x1 = _uc(a.sum(axis=0))
        t, _b = _uc(a.sum(axis=1))
        return (x0 + x1) / 2.0, t

    @staticmethod
    def _genislik(a):
        x0, x1 = _uc(np.asarray(a, np.float32).sum(axis=0))
        return x1 - x0

    def _genislik_esle(self, pl, hedef):
        """Isim plakasini (RGBA) yatayda murekkep genisligi `hedef` olacak sekilde yeniden orneklendirir (<= %2)."""
        im = pl[0]
        w = self._genislik(np.asarray(im)[..., 3])
        f = hedef / max(w, 1e-6)
        if abs(f - 1) > GENISLIK_AZAMI:
            return pl, {'oran': round(f, 4), 'uygulandi': False}
        yeni = im.resize((max(int(round(im.width * f)), 1), im.height), Image.LANCZOS)
        return (yeni, *pl[1:]), {'oran': round(f, 4), 'uygulandi': True}

    def _kaydet(self, s, S, isimler, tagline):
        out = self.asil(s, S, isimler, tagline)
        _, bilgi, merkez, x, _ = out
        self.kayit.update({'x': dict(x), 'mm': {y: merkez[y] - x[y] for y in ('sol', 'sag')},
                           'inf_g0': float(S['oge']['sonsuz']['gorsel'][0])})
        if SATIR_OLCEKLI.get('kutle'):                # yalniz dijital 2. yerlesim denemesi (kutle merkezi; 1 Eki)
            p16 = self.p16
            olcek = p16.d_olcek(isimler, s, S)
            for y in ('sol', 'sag'):
                pl = p16.plaka(isimler[y], S["prof"][y], s["cap"][y], olcek)[0]
                cx, top = self._kutle(np.asarray(pl)[..., 3])
                px, py = bilgi['isim_kutu'][y][:2]
                self.kayit[f'murekkep_{y}'] = (px + cx, py + top)
                if SATIR_OLCEKLI.get('genislik'):        # 3. deneme: murekkep genisligi (kapi ile ayni tanim)
                    self.kayit[f'genislik_{y}'] = self._genislik(np.asarray(pl)[..., 3])
            o = S['oge']['sonsuz']
            mcx, _t = self._kutle(o['maske'])
            self.kayit['sonsuz_murekkep'] = int(round(x['inf'] - o['pay'][0])) + mcx
        return out

    def _olcekli(self, s, S, isimler, tagline):
        if not self.kayit.get('x'):
            return self.asil(s, S, isimler, tagline)
        import cv2
        p16, k, r = self.p16, self.k, self.kayit
        olcek = p16.d_olcek(isimler, s, S)
        pl = {y: p16.plaka(isimler[y], S["prof"][y], s["cap"][y], olcek) for y in ("sol", "sag")}
        w = {y: pl[y][0].width for y in pl}
        inf = S["oge"]["sonsuz"]
        mm = {y: p16.murekkep_merkezi(pl[y][0]) for y in ("sol", "sag")}
        pyy = {y: s["isim_y"] - pl[y][0].height / 2 for y in ("sol", "sag")}
        genislik_esle = {}
        if SATIR_OLCEKLI.get('genislik') and r.get('genislik_sol'):
            for y in ("sol", "sag"):
                pl[y], genislik_esle[y] = self._genislik_esle(pl[y], r[f'genislik_{y}'] * k)
            w = {y: pl[y][0].width for y in pl}
            mm = {y: p16.murekkep_merkezi(pl[y][0]) for y in ("sol", "sag")}
            pyy = {y: s["isim_y"] - pl[y][0].height / 2 for y in ("sol", "sag")}
        if SATIR_OLCEKLI.get('kutle') and r.get('murekkep_sol'):
            # dijital 2. yerlesim denemesi: yatay KUTLE merkezi, dikey ust kenar 2400 x k (kapi ile ayni tanim)
            x = {}
            for y in ("sol", "sag"):
                cx, top = self._kutle(np.asarray(pl[y][0])[..., 3])
                mx, my = r[f'murekkep_{y}']
                x[y] = mx * k - cx
                pyy[y] = my * k - top
            mcx, _t = self._kutle(inf['maske'])
            x["inf"] = r['sonsuz_murekkep'] * k - mcx + inf['pay'][0]
        else:
            x = {y: (r['x'][y] + r['mm'][y]) * k - mm[y] for y in ("sol", "sag")}
            x["inf"] = float(inf["gorsel"][0]) + (r['x']['inf'] - r['inf_g0']) * k
        toplam = x["sag"] + w["sag"] - x["sol"]
        x0 = x["sol"]
        a = S["temiz_a"].copy()
        merkez = {y: x[y] + mm[y] for y in ("sol", "sag")}
        yer = {"sonsuz": (x["inf"], S["oge"]["sonsuz"]["gorsel"][1])}
        for y in ("sol", "sag"):
            o = S["oge"][f"sembol_{y}"]
            yer[f"sembol_{y}"] = (merkez[y] - o["w"] / 2, o["gorsel"][1])
        for ad, (px, py) in yer.items():
            o = S["oge"][ad]
            p16.delta_koy(a, o["delta"], o["maske"], px - o["pay"][0], py - o["pay"][1])
        t = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        yeni_maske = np.zeros(a.shape[:2], np.uint8)
        isim_geometri, isim_kutu = {}, {}
        for y in ("sol", "sag"):
            p = pl[y][0]
            px, py = int(round(x[y])), int(round(pyy[y]))
            t.alpha_composite(p, (px, py))
            isim_kutu[y] = [px, py, px + p.width, py + p.height]
            alfa = np.asarray(p)[..., 3]
            pm = alfa > 40
            p16.isaretle(yeni_maske, alfa > 8, px, py)
            ys = np.nonzero(pm.any(axis=1))[0]
            isim_geometri[y] = {"cap": int(ys[-1] - ys[0] + 1),
                                "dikey_merkez": round(py + (int(ys[0]) + int(ys[-1])) / 2, 1)}
        tg, tbilgi = p16.tagline_plaka(s, {"prof": S["prof"]}, tagline)
        tx, ty = (int(round(p16.NORM_W / 2 - tg.width / 2)), int(round(s["tag_y"] - tg.height / 2)))
        t.alpha_composite(tg, (tx, ty))
        p16.isaretle(yeni_maske, np.asarray(tg)[..., 3] > 8, tx, ty)
        for ad, (px, py) in yer.items():
            o = S["oge"][ad]
            p16.isaretle(yeni_maske, o["maske"] > 0.02, int(round(px - o["pay"][0])), int(round(py - o["pay"][1])))
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * p16.KAPI_PAY + 1,) * 2)
        yeni_genis = cv2.dilate(yeni_maske, ker).astype(bool)
        bilgi = {"olcek": round(olcek, 3), "punto": [pl["sol"][1], pl["sag"][1]],
                 "genislik": [w["sol"], w["sag"]], "satir": round(toplam, 1),
                 "kenar": [x0, p16.NORM_W - x0 - toplam], "satir_merkez": round(x0 + toplam / 2, 1),
                 "isim_geometri": isim_geometri, "isim_kutu": isim_kutu, "tagline": tbilgi,
                 "yerlesim": 'olcekli (2400 x k)'}
        if genislik_esle:
            bilgi['genislik_esle'] = genislik_esle
        return t.convert("RGB"), bilgi, merkez, x, yeni_genis


# ------------------------------------------------------------------ hibrit baski dosyasi
def baski_dosyasi(poster, ek, tam_sayfa_png, hedef_px):
    """Tuval = hedef piksel boyundaki TAM COZUNURLUKLU Canva sayfasi.
    Yalnizca degisen bant (eski oge maskesi + yeni yazi maskesi) 2400'luk render'dan gelir."""
    import cv2
    tam = Image.open(io.BytesIO(tam_sayfa_png)).convert('RGB')
    kaynak_px = list(tam.size)
    if list(tam.size) != list(hedef_px):
        tam = tam.resize(tuple(hedef_px), Image.LANCZOS)
    A = np.asarray(tam).astype(np.float32)
    P = np.asarray(poster.convert('RGB').resize(tuple(hedef_px), Image.LANCZOS)).astype(np.float32)
    mf = cv2.GaussianBlur(ek['maske'].astype(np.float32), (0, 0), KENAR_YUMUSAT)
    M = cv2.resize(mf, tuple(hedef_px), interpolation=cv2.INTER_LINEAR)
    M = np.clip(M, 0.0, 1.0)[..., None]
    out = A * (1 - M) + P * M
    temiz = {'uygulandi': False, 'sebep': 'plate / olcum yok'}
    if (ek.get('olcum') or {}).get('isim_bant') and ek.get('yeni') is not None:
        Y, ham = koruma(ek)
        out, temiz = isim_bandi_temizle(out, Y, ek['olcum'], ham=ham, alan=ek.get('maske'))
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGB'), {
        'kaynak_px': kaynak_px, 'baski_px': list(hedef_px),
        'maske_px_2400': int(ek['maske'].sum()),
        'maske_orani': round(float(ek['maske'].mean()), 5),
        'isim_bandi_temizligi': temiz,
    }


def onizleme(baski, poster, ek, ad, cik):
    """Sol: baski dosyasi kucultulmus. Sag: isim satiri + tagline bandi 1:1 kirpim (baski cozunurlugunde)."""
    H = 1400
    sol = baski.resize((round(baski.width * H / baski.height), H), Image.LANCZOS)
    ys, xs = np.nonzero(ek['maske'])
    k = baski.width / ek['maske'].shape[1]
    x0, x1 = int(xs.min() * k), int(xs.max() * k)
    y0, y1 = int(ys.min() * k), int(ys.max() * k)
    kirp = baski.crop((max(x0 - 40, 0), max(y0 - 40, 0),
                       min(x1 + 40, baski.width), min(y1 + 40, baski.height)))
    if kirp.width > 1200:
        kirp = kirp.resize((1200, round(kirp.height * 1200 / kirp.width)), Image.LANCZOS)
    t = Image.new('RGB', (sol.width + kirp.width + 40, max(H, kirp.height)), 'white')
    t.paste(sol, (0, 0)); t.paste(kirp, (sol.width + 40, 0))
    t.save(cik / ad, quality=92)


# ------------------------------------------------------------------ akis
def pod_kaynak(cift, renk, boy):
    """Onayli baski dosyasini indir: POD_PRINT/<cift>/<renk>/<boy>.jpg (hedef boy ve dpi burada)."""
    hed = W / 'pod' / cift / renk
    hed.mkdir(parents=True, exist_ok=True)
    yol = hed / f'{boy}.jpg'
    if not yol.exists():
        rc('copy', f'{POD}/{cift}/{renk}/{boy}.jpg', str(hed), timeout=900)
    if not yol.exists():
        raise SystemExit(f'POD_PRINT\'te yok: {cift}/{renk}/{boy}.jpg')
    return yol


def sayfa_no_tablosu():
    ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
    return {c: i + 1 for i, c in enumerate(ciftler)}, ciftler



# ------------------------------------------------------------------ COZUNURLUK OLCEGI (Serdar karari 25 Eyl, 1. madde)
# Onayli render hatti NORM_W=2400 ile calisir; isim/mesaj bandi bu yuzden 2400 px
# dogar. Karar: bant baski boyutunun hedef cozunurlugunde (300 dpi) uretilsin.
# Yontem: OLCUM 2400'de kalir (sayfa_olc bu olcekte dogrulandi), olculen bantlar ve
# kilitler k = hedef_en/2400 ile olceklenir, NORM_W ve piksel tabanli sabitler modul
# DEGISKENI olarak k'ya cekilir (kod degismez, girdi degisir - REF_SAYFA ile ayni usul).
# Kapi: hi-res sonuc 2400'e indirilip onayli 2400 render'i ile karsilastirilir (<=1 px).
_TABAN = {}                    # modul -> {sabit: 2400'deki deger}
# (modul adi, sabit, olcek turu) - 'px' k ile, 'alan' k^2 ile, 'tek' k ile ve TEK sayi
OLCEKLI = [('pilot16', 'YUMUSAK', 'px'), ('pilot16', 'KAPI_PAY', 'px'),
           ('pilot16', 'GENISLET', 'px'), ('pilot16', 'BLOK', 'px'),
           ('pilot16', 'MIN_ALAN', 'alan'),
           ('edisyon_uret', 'GENISLET', 'px'), ('edisyon_uret', 'MASKE_YARICAP', 'tek'),
           ('edisyon_uret', 'MASKE_MIN_ALAN', 'alan'), ('edisyon_uret', 'DOKU_EROZYON', 'px'),
           ('edisyon_uret', 'UZAT_AZAMI', 'px'), ('edisyon_uret', 'KIRPIM_PAY', 'px'),
           ('a1_poster', 'SEMBOL_BIRLES', 'px'), ('a1_poster', 'SEMBOL_KAYMA', 'px'),
           ('a1_poster', 'SEMBOL_UST', 'px')]
# Yogunluk/oran esikleri OLCEKLENMEZ: CEKIRDEK, MASKE_ESIK, BLOK_ORT/TEPE, PARCA_PAY,
# KENAR_ORAN, TAG_TABAN_*, DOKU_FARK, SEMBOL_ESIK.
PX_ALAN = ('isim_bant', 'sol_isim', 'sonsuz', 'sag_isim', 'sembol_bant', 'sembol',
           'tag_bant', 'tag_x', 'isim_govde', 'satir', 'bosluk', 'satir_genislik',
           'isim_yuksekligi', 'kenar_payi', 'tag_genislik', 'tag_yuksekligi',
           'ust_en_genis', 'satir_merkez', 'poster_merkez', 'isim_merkez',
           'sembol_merkez', 'tag_merkez', 'norm_boyut', 'tag_kumeleri')


def _mod(ad):
    import importlib
    return importlib.import_module(ad)


def olcek_kur(hedef_en):
    """NORM_W ve piksel sabitlerini hedef genislige tasir. k=1 ise 2400'e geri doner."""
    k = hedef_en / 2400.0
    for ad in ('pilot11', 'pilot12', 'pilot16', 'edisyon_uret'):
        setattr(_mod(ad), 'NORM_W', int(round(hedef_en)))
    for ad, sabit, tur in OLCEKLI:
        m = _mod(ad)
        _TABAN.setdefault((ad, sabit), getattr(m, sabit))
        t = _TABAN[(ad, sabit)]
        if tur == 'alan':
            v = max(int(round(t * k * k)), 1)
        elif tur == 'tek':
            v = max(int(round(t * k)), 3)
            v = v if v % 2 else v + 1
        else:
            v = max(int(round(t * k)), 1)
        setattr(m, sabit, v)
    return {'hedef_en': int(round(hedef_en)), 'k': round(k, 4),
            'sabitler': {f'{a}.{s}': getattr(_mod(a), s) for a, s, _ in OLCEKLI}}


# Yalniz KONUM hesabina giren (dilimlemede kullanilmayan) alanlar olceklenirken yuvarlanmaz.
# 28 Eyl olcumu (baski-duzelt tani kosusu): hi-res'te isim_govde tam sayiya yuvarlanip cizimde
# konum bir kez daha yuvarlaniyordu; iki yuvarlamanin en kotusu 2400 biriminde 1.23 px ediyor
# (olculen en buyuk olcek farki 1.23). Karar (Serdar adina, 28 Eyl): (a) yuvarlama kaldirilir,
# cizim yalniz bir kez (pilot16 icinde) yuvarlar; degisim <= 1 px.
HASSAS_ALAN = ('isim_govde',)


def olcekle(d, k):
    """Olculen sayfa kaydini (sayfa_olc + olcum_duzelt) k ile olcekler."""
    def sc(v, hassas=False):
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (int, float)):
            if hassas:
                return v * k
            return int(round(v * k)) if isinstance(v, int) else round(v * k, 1)
        if isinstance(v, (list, tuple)):
            return [sc(x, hassas) for x in v]
        return v
    return {a: (sc(b, a in HASSAS_ALAN) if a in PX_ALAN else b) for a, b in d.items()}


def kilit_olcekle(kilit, k):
    out = dict(kilit)
    out['bosluk'] = kilit['bosluk'] * k                 # HASSAS_ALAN ile ayni gerekce
    out['cap'] = {y: int(round(kilit['cap'][y] * k)) for y in kilit['cap']}
    for a in ('isim_bant', 'sembol_bant', 'tag_bant'):
        if isinstance(kilit.get(a), list):
            out[a] = [int(round(v * k)) for v in kilit[a]]
    return out


# ------------------------------------------------------------------ LEKE / YAMA KAPISI (Serdar 2. madde)
# Wallpaper'da parsomende silme yama birakti. "Temiz ara zemin" kapisi ara goruntuyu
# ZEMINE karsi olcuyor; zemin zaten oraya yapistirildigi icin yamayi goremez.
# Bu kapi DOKUYA bakar: silinen bolgenin yuksek frekans enerjisi, cevresindeki
# DOKUNULMAMIS orijinal dokunun enerjisine oranlanir. Yama duz olur -> oran duser.
LEKE_P99 = 10.0         # Serdar 25 Eyl: bant DISINDA |baski - kaynak| p99 <= 10
LEKE_PAY = 9            # bant maskesi bu kadar genisletilir (yumusak kenar payi)


def leke_kapisi(baski, kaynak, maske, esik_p99=LEKE_P99):
    """BANT DISINDA baski, birlestirmenin kaynak tuvaliyle ayni olmali.

    Eski kapi silinen bolgenin doku ENERJISINI olcuyordu; dokusuz edisyonlarda
    yanlis hata veriyordu (Deep Black 30x40: silinen_enerji 0.00 / halka 2.58,
    cunku o bant gercekten duz zemin). Yeni olcut dogrudan ve her edisyonda
    ayni: degisen bandin disinda uretilen dosya ile kaynak arasindaki fark JPEG
    gurultusu kadar olmali. Plate yalniz oge ayirmak icindir; kaynak burc resmini
    plate ile karsilastirmak gercek tasarimi leke sayar.
    Olculen taban (kosu 36153249586, murekkep disi p99): MB 0, CI 0, WP 3.
    Esik 10 bunun cok ustunde; gercek bir leke/yamayi ise yakalar.

    Bant DISI = ogelerin degistirildigi yerler haric HER YER: burc resmi,
    yildizlar ve cerceve kaynak tuvaldeki gibi durmali.
    """
    import cv2
    if isinstance(kaynak, Image.Image):
        kaynak_im = kaynak.convert('RGB')
    else:
        with Image.open(io.BytesIO(kaynak) if isinstance(kaynak, bytes) else kaynak) as im:
            kaynak_im = im.convert('RGB')
    if kaynak_im.size != baski.size:
        kaynak_im = kaynak_im.resize(baski.size, Image.LANCZOS)
    pl = np.asarray(kaynak_im)
    a = np.asarray(baski.convert('RGB'))
    if pl.shape != a.shape:
        return {'gecti': None, 'uygulandi': False,
                'sebep': f'kaynak {pl.shape[1]}x{pl.shape[0]} != baski {a.shape[1]}x{a.shape[0]}'}
    m = cv2.resize(maske.astype(np.uint8), (a.shape[1], a.shape[0]),
                   interpolation=cv2.INTER_NEAREST)
    m = cv2.dilate(m, np.ones((LEKE_PAY, LEKE_PAY), np.uint8)) > 0
    f = np.abs(a.astype(np.int16) - pl.astype(np.int16)).max(axis=2)
    dis = f[~m]
    if dis.size < 10000:
        return {'gecti': None, 'uygulandi': False, 'sebep': 'bant disi alan kucuk',
                'bant_disi_px': int(dis.size)}
    p50 = float(np.percentile(dis, 50)); p99 = float(np.percentile(dis, 99))
    # Yerel yama ortalamada kaybolmasin: en kotu 256 px'lik blok ayrica olculur.
    B = 256
    H, Wd = f.shape
    kotu, yer = 0.0, None
    for by in range(0, H - B + 1, B):
        for bx in range(0, Wd - B + 1, B):
            bm = ~m[by:by + B, bx:bx + B]
            if bm.sum() < B * B * 0.5:
                continue
            v = float(np.percentile(f[by:by + B, bx:bx + B][bm], 99))
            if v > kotu:
                kotu, yer = v, [bx, by]
    return {'gecti': bool(p99 <= esik_p99 and kotu <= esik_p99 * 1.5),
            'uygulandi': True, 'p50': p50, 'p99': p99, 'esik_p99': esik_p99,
            'en_kotu_blok_p99': round(kotu, 1), 'en_kotu_blok_yeri': yer,
            'bant_disi_px': int(dis.size), 'bant_orani': round(float(m.mean()), 4)}


def silinen_kirpim(baski, maske2400, ad, cik, buyut=BUYUT, azami_en=3000):
    """Silinen bolgenin x3 buyutmesi (Serdar: kontrol paketine eklenecek)."""
    ys, xs = np.nonzero(maske2400)
    if not len(ys):
        return None
    k = baski.width / maske2400.shape[1]
    x0 = max(int(xs.min() * k) - 30, 0); x1 = min(int(xs.max() * k) + 30, baski.width)
    y0 = max(int(ys.min() * k) - 30, 0); y1 = min(int(ys.max() * k) + 30, baski.height)
    kirp = baski.crop((x0, y0, x1, y1))
    en = min(kirp.width * buyut, azami_en)
    kirp = kirp.resize((en, max(round(kirp.height * en / kirp.width), 1)), Image.LANCZOS)
    kirp.save(cik / ad, quality=95, subsampling=0)
    return {'kutu': [x0, y0, x1, y1], 'gorsel_px': list(kirp.size), 'buyutme': buyut}

# ------------------------------------------------------------------ Blue sarmalayicisi (a1, onayli)
class BluePoster:
    """Blue hatti: a1_poster.Poster (pilot16). Boy tavani her oran icin Cancer-Libra'dan alinir."""

    def __init__(self):
        from a1_poster import Poster
        self.P = Poster()
        # Onayli altin isim profili (Cancer / Libra name gold; Poster.__init__ -> pilot12.profil_yukle).
        # 30 Eyl: edisyon_uret.oran_kur her edisyon render'inda pilot12.PROFIL global'ini o dosyanin
        # profiliyle eziyor; Blue (pilot16.oran_kur) sonra onu okuyordu -> MB isim rengi onceki renderdan
        # geliyordu (ARIES_SCORPIO MB: tek basina 253,193,61 / CI sonrasi 115,73,35, mesaj dE 9.8).
        self.profil = {y: np.array(v, copy=True) for y, v in self.P.p12.PROFIL.items()}
        self.hazir_oran = set()
        self.plate_boy = None

    def plate_kur(self, P_ed, boy, oran):
        """Blue'nun zemini de medyan plate olur (Serdar onayi 25 Eyl).

        `a1_poster.Poster.sayfa_kur` `self.bg`'yi oran_kur'a gecirir; burada o
        GIRDI degistirilir, a1_poster kodu degismez. Boy degisince tavan
        referansi da yeniden kurulur (plate farkli dosyadir).
        """
        if not boy or self.plate_boy == boy:
            return
        yol = P_ed.plate('blue', oran, boy)
        self.P.bg = Image.open(yol).convert('RGB')
        self.plate_boy = boy
        self.hazir_oran.clear(); self.P.tavan = None

    def __call__(self, kaynak_bayt, sayfa_no, oran, isimler, tagline, ref_bayt=None, ref_sayfa=28):
        self.P.p12.PROFIL = {y: v.copy() for y, v in self.profil.items()}   # onayli profil (sira bagimsiz)
        if oran not in self.hazir_oran:
            if ref_bayt is None:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referansi verilmedi (boy tavani)')
            self.P.tavan = None
            self.P(ref_bayt, ref_sayfa, 'blue', oran, isimler, tagline, referans=True)
            self.hazir_oran.add(oran)
        # poster_kur'un yeni_genis maskesi (isim bandi temizligi / kalinti kapisi icin) a1_poster
        # kodu degismeden kaydedilir: modul fonksiyonu cagri suresince sarilir.
        p16 = self.P.p16
        asil, kayit = p16.poster_kur, {}

        def kaydeden(*a, **kw):
            with _HamKayit(p16) as hk:
                r = asil(*a, **kw)
            kayit['yeni'], kayit['yeni_ham'] = r[4], hk.maske()
            return r
        p16.poster_kur = kaydeden
        try:
            p, bi, kirp = self.P(kaynak_bayt, sayfa_no, 'blue', oran, isimler, tagline)
        finally:
            p16.poster_kur = asil
        return p, {**bi, 'edisyon': 'blue', 'oran': oran, 'durum': 'URETILDI'}, \
            {'kirp': kirp, 'yeni': kayit.get('yeni'), 'yeni_ham': kayit.get('yeni_ham')}

    def hedef_render(self, kaynak_bayt, sayfa_no, oran, isimler, tagline, hedef_en, ref_bayt=None, ref_sayfa=28):
        """YALNIZ DIJITAL MB (Serdar 1 Eki, siparis 4188621967): isim / mesaj bandi HEDEF cozunurlukte cizilir.

        Once onayli 2400 render (cikti ayni; isim plaka boyu ve yerlesim kaydedilir), sonra edisyon hattindaki
        gibi olcek_kur(hedef_en): sayfa olcumu, bg hizasi, isim / tagline caplari ve bosluk k ile olceklenir,
        isim punto = 2400 boyu x k (IsimPlakasi sabit). POD yolu bu fonksiyonu cagirmaz."""
        import giris_dogrula as gd
        self.P.p12.PROFIL = {y: v.copy() for y, v in self.profil.items()}
        if oran not in self.hazir_oran:
            if ref_bayt is None:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referansi verilmedi (boy tavani)')
            self.P.tavan = None
            self.P(ref_bayt, ref_sayfa, 'blue', oran, isimler, tagline, referans=True)
            self.hazir_oran.add(oran)
        p16, p12 = self.P.p16, self.P.p12
        olcek_kur(2400)
        B = self.P.sayfa_kur(kaynak_bayt, sayfa_no, 'blue', oran)
        boy0, yer0, tag0 = {}, {}, {}
        asil_tag = p16.tagline_plaka

        def tag_kaydet(s_, S_, metin):                           # 2400 tagline punto (shrink dahil son deger)
            r_ = asil_tag(s_, S_, metin)
            tag0['punto'] = r_[1].get('punto')
            return r_
        p16.tagline_plaka = tag_kaydet
        try:
            with _PlakaKayit(boy0), _SatirYerlesim(p16, yer0), _HamKayit(p16) as hk0:
                p0, bi0, kirp = self.P.uret(B, isimler, tagline)
        finally:
            p16.tagline_plaka = asil_tag
        s0, S0 = B['s'], B['S']
        yeni0 = hk0.maske()
        k = hedef_en / 2400.0
        h0 = dict(s0['bg_hiza'])
        h1 = {**h0, 'dx': int(round(h0.get('dx', 0) * k)), 'dy': int(round(h0.get('dy', 0) * k))}
        o1 = olcekle(B['o'], k)
        kayit = dict(self.P.olcum[oran]); kayit['sayfalar'] = {str(sayfa_no): o1}
        asil_hiza = p16.hizalama
        asil_cp = p12.cap_punto
        olcek = olcek_kur(hedef_en)
        try:
            if tag0.get('punto'):                                 # 1 Eki: mesaj puntosu 2400 x k (cap_punto yeniden
                tp1 = max(int(round(tag0['punto'] * k)), 4)       # hesabi mesaji ~%4 genisletiyordu, MB 24x36)
                p12.cap_punto = lambda *a_, **kw_: tp1
            p16.REF_SAYFA = sayfa_no
            p16.hizalama = lambda *a, **kw: (dict(h1), False)       # 2400 kilidi, k ile (arama yok)
            s1, S1 = p16.oran_kur(oran, kayit, self.P.bg, kalibre=False)
            g0, g1 = o1['isim_govde']; s1['isim_y'] = (g0 + g1) / 2
            s1['cap'] = {y: int(round(s0['cap'][y] * k)) for y in ('sol', 'sag')}
            s1['tag_cap'] = int(round(s0['tag_cap'] * k))
            s1['tag_sinir'] = 10 ** 6 if tag0.get('punto') else int(round(s0['tag_sinir'] * k))   # punto zaten son deger
            s1['bosluk'] = s0['bosluk'] * k
            capmap = {s0['cap'][y]: s1['cap'][y] for y in ('sol', 'sag')}
            sabit = {(mt, capmap.get(c, c)): b * k for (mt, c), b in boy0.items()}
            r = gd.siparis_dogrula(isimler[0], isimler[1], tagline, None)
            yer = _SatirYerlesim(p16, yer0, k) if SATIR_OLCEKLI['etkin'] else _SatirYerlesim(p16, {})
            with IsimPlakasi(sabit=sabit), yer, _HamKayit(p16) as hk1:
                p1, bilgi1, merkez1, x1, yeni1 = p16.poster_kur(
                    s1, S1, {'sol': r['sol']['deger'], 'sag': r['sag']['deger']}, tagline)
        finally:
            p16.hizalama = asil_hiza
            p12.cap_punto = asil_cp
            olcek_kur(2400)
        bi = {**bi0, 'edisyon': 'blue', 'oran': oran, 'durum': 'URETILDI', 'poster_px': list(p1.size),
              'mb_hedef_render': {'k': round(k, 4), 'olcek': olcek, 'punto_2400': bi0.get('punto'),
                                  'punto_hedef': bilgi1.get('punto'), 'bg_hiza': h1,
                                  'tag_punto_2400': tag0.get('punto'), 'tag_punto_hedef': (bilgi1.get('tagline') or {}).get('punto')}}
        return p1, bi, {'kirp': kirp, 'p0': p0, 'yeni': yeni1, 'yeni_ham': hk1.maske(),
                        'maske': S1['genis'] | yeni1, 'maske_2400': S0['genis'] | (yeni0 if yeni0 is not None else False),
                        'yeni_2400': yeni0}


class _PlakaKayit:
    """2400 Blue render'inda (metin, cap) -> kullanilan isim boyu (cikti degismez; IsimPlakasi kayit gibi)."""

    def __init__(self, kayit):
        self.kayit = kayit

    def __enter__(self):
        self._eski = (_mod('pilot12').plaka, _mod('pilot16').plaka)
        asil = self._eski[1]

        def kaydet(metin, prof, hedef_cap, olcek=1.0, tam=None):
            r = asil(metin, prof, hedef_cap, olcek, tam)
            self.kayit[(metin, hedef_cap)] = r[2] * olcek
            return r
        _mod('pilot12').plaka = kaydet
        _mod('pilot16').plaka = kaydet
        return self

    def __exit__(self, *a):
        _mod('pilot12').plaka, _mod('pilot16').plaka = self._eski
        return False


def degisim_maskesi(poster, kaynak_bayt):
    """Precise maske yoksa: uretilen poster ile normalize kaynak arasindaki gercek degisim."""
    import cv2, pilot11
    ref = pilot11.norm(Image.open(io.BytesIO(kaynak_bayt)).convert('RGB'))[0]
    a = np.asarray(ref).astype(np.int16)
    b = np.asarray(poster.convert('RGB')).astype(np.int16)
    n = min(a.shape[0], b.shape[0])
    d = np.zeros(b.shape[:2], bool)
    d[:n] = np.abs(a[:n] - b[:n]).max(2) > 2
    return cv2.dilate(d.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0


# ------------------------------------------------------------------ kontrol paketi
def bant_kirpim(baski, bant, x_araligi, ad, cik, buyut=BUYUT, azami_en=3000):
    """Tam cozunurluklu dosyadan bir bandi kirpip buyutur (Serdar gozle kontrol eder)."""
    k = baski.width / 2400.0
    x0 = max(int(x_araligi[0] * k) - 30, 0); x1 = min(int(x_araligi[1] * k) + 30, baski.width)
    y0 = max(int(bant[0] * k) - 20, 0); y1 = min(int(bant[1] * k) + 20, baski.height)
    kirp = baski.crop((x0, y0, x1, y1))
    en = min(kirp.width * buyut, azami_en)
    kirp = kirp.resize((en, max(round(kirp.height * en / kirp.width), 1)), Image.LANCZOS)
    kirp.save(cik / ad, quality=95, subsampling=0)
    return {'kutu_2400': [x_araligi[0], bant[0], x_araligi[1], bant[1]],
            'kirpim_px': [x1 - x0, y1 - y0], 'gorsel_px': list(kirp.size), 'buyutme': buyut}


def font_kapsami(isimler, mesaj):
    import giris_dogrula as gd
    r = gd.siparis_dogrula(isimler[0], isimler[1], mesaj, None)
    eksik = {'isim1': gd.eksik_karakterler(r['sol']['deger'], 'isim'),
             'isim2': gd.eksik_karakterler(r['sag']['deger'], 'isim'),
             'mesaj': gd.eksik_karakterler(r['tagline']['deger'], 'tagline')}
    return {'gecti': not any(eksik.values()) and r['durum'] == 'TAMAM',
            'dogrulama': r['durum'], 'eksik_karakter': eksik,
            'notlar': {k: r[k]['notlar'] for k in ('sol', 'sag', 'tagline') if r[k]['notlar']}}


def boy_kapisi(baski_px, beklenen_px, dosya_mb=None, azami_mb=None):
    tam = list(baski_px) == list(beklenen_px)
    d = {'gecti': tam, 'baski_px': list(baski_px), 'beklenen_px_300dpi': list(beklenen_px)}
    if azami_mb is not None:
        d['dosya_MB'] = dosya_mb; d['azami_MB'] = azami_mb
        d['gecti'] = tam and dosya_mb is not None and dosya_mb <= azami_mb
    return d


def renk_onizleme(yollar, ad, cik, yukseklik=900):
    """Bes rengin tek gorselde yan yana onizlemesi."""
    ims = []
    for renk, yol in yollar:
        im = Image.open(yol).convert('RGB')
        im = im.resize((max(round(im.width * yukseklik / im.height), 1), yukseklik), Image.LANCZOS)
        ims.append((renk, im))
    en = sum(i.width for _, i in ims) + 20 * (len(ims) + 1)
    t = Image.new('RGB', (en, yukseklik + 40), 'white')
    x = 20
    for _, im in ims:
        t.paste(im, (x, 30)); x += im.width + 20
    t.save(cik / ad, quality=92)
    return {'renkler': [r for r, _ in ims], 'px': list(t.size)}


ZEMIN_UYUM_ESIK = 4.0      # |kaynak - plate| medyani (sayfa geneli); 30 Eyl olcum: TAURUS_TAURUS DB 10.3, diger DB 0


def zemin_uyumu(kaynak_bayt, plate_yol):
    """Kaynak dosyanin zemini medyan plate ile ayni mi? (30 Eyl, TAURUS_TAURUS DB 'isim satiri bulunamadi':
    kaynak zemini dokulu / acik, fark maskesi 39-2922 satirini tek bant yapiyordu.) Olcum 1/4 olcekte."""
    try:
        A = Image.open(io.BytesIO(kaynak_bayt)).convert('RGB')
        P = Image.open(plate_yol).convert('RGB')
        boy = (max(A.width // 4, 1), max(A.height // 4, 1))
        a = np.asarray(A.resize(boy, Image.BILINEAR)).astype(np.float32)
        p = np.asarray(P.resize(boy, Image.BILINEAR)).astype(np.float32)
        p50 = float(np.median(np.abs(a - p).mean(2)))
        return {'gecti': p50 <= ZEMIN_UYUM_ESIK, 'p50': round(p50, 1), 'esik': ZEMIN_UYUM_ESIK}
    except Exception as e:                                        # noqa: BLE001
        return {'gecti': True, 'hata': f'{type(e).__name__}: {e}', 'esik': ZEMIN_UYUM_ESIK}


def render_et(ed, oran, sayfa, kaynak_bayt, isimler, mesaj, P_blue, P_ed,
              cift=None, ref_boy=None, hedef_en=None, boy=None):
    """blue -> a1 (pilot16, 2400), diger dort edisyon -> edisyon_uret (hedef cozunurluk)."""
    # PLATE KAPISI (fail-closed): plate yoksa ya da eski slogani iceriyorsa uretim yok.
    try:
        plate_yol = P_ed.plate(ed, oran, boy or ref_boy)
        pk = plate_slogan_kapisi(kaynak_bayt, plate_yol, ed)
    except PlateHatasi as e:
        return None, plate_bildir({'durum': 'SISTEM HATASI', 'edisyon': ed, 'oran': oran,
                                   'hata': str(e), 'plate_slogan_kapisi': e.ayrinti}, cift), None
    if not pk['gecti']:
        return None, plate_bildir({'durum': 'SISTEM HATASI', 'edisyon': ed, 'oran': oran,
                                   'hata': f"PLATE KIRLI: {pk['plate']} eski slogani iceriyor "
                                           f"({pk.get('sebep') or 'glif farkli payi ' + str(pk.get('glif_farkli_payi'))})",
                                   'plate_slogan_kapisi': pk}, cift), None
    zu = zemin_uyumu(kaynak_bayt, plate_yol)
    if not zu['gecti']:
        return None, plate_bildir({'durum': 'SISTEM HATASI', 'edisyon': ed, 'oran': oran,
                                   'hata': f"ZEMIN PLATE ILE UYUMSUZ: kaynak zemini medyan plate'ten farkli "
                                           f"(fark p50 {zu['p50']} > {zu['esik']}); dosya-plate farki tum sayfayi "
                                           f"murekkep sayar, isim satiri ayrilamaz. Kaynak yeniden disa "
                                           f"aktarilmali ya da cifte ozel plate gerekir.",
                                   'plate_slogan_kapisi': pk, 'zemin_uyumu': zu}, cift), None
    if ed == 'blue':
        ref_bayt = None
        # plate_kur boy degisince hazir_oran'i temizler: referans karari ONDAN SONRA
        # verilmeli (GOREV_0020 tablo kosusu: ayni surecte 2. boyda RuntimeError).
        P_blue.plate_kur(P_ed, boy or ref_boy, oran)
        if oran not in P_blue.hazir_oran:
            boy = ref_boy or DIJITAL_BOY.get(oran)
            if not boy:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referans boyu bulunamadi')
            ref_bayt = pod_kaynak('CANCER_LIBRA', 'MIDNIGHT_BLUE', boy).read_bytes()
        olcek_kur(2400)
        # Blue de plate zeminine gecer (Serdar onayi 25 Eyl): a1 sarmalayicisinin
        # `bg` girdisi HAZIR/bg.png yerine bu boyun plate'i olur. GIRDI degisikligi;
        # a1_poster kodu degismez. Hiza `bg_hiza` alaninda raporlanir.
        if MB_HEDEF['etkin'] and hedef_en and int(hedef_en) != 2400:
            poster, bi, ek = P_blue.hedef_render(kaynak_bayt, sayfa, oran, isimler, mesaj, int(hedef_en),
                                                 ref_bayt=ref_bayt)
        else:
            poster, bi, ek = P_blue(kaynak_bayt, sayfa, oran, isimler, mesaj, ref_bayt=ref_bayt)
        bi['plate'] = str(P_ed.plate('blue', oran, boy or ref_boy))
        bi['olcum_kaynagi'] = 'kendi dosyasi (a1 sarmalayicisi, zemin = plate)'
        # Olcek kapisi baski dosyasi uretildikten sonra (olcek_kapisi_baski) kosar:
        # Blue 2400 render edilir, kapi buyutulmus bandi onayli 2400 render ile olcer.
        bi['olcek_kapisi'] = {'gecti': None, 'sebep': 'baski dosyasi uretildikten sonra olculur'}
        bi['leke_kapisi'] = {'gecti': None, 'sebep': 'Blue 2400 render'}
    else:
        poster, bi, ek = P_ed(kaynak_bayt, sayfa, ed, oran, isimler, mesaj,
                              hedef_en=hedef_en, boy=boy or ref_boy)
    if poster is None:
        return None, bi, None
    bi['plate_slogan_kapisi'] = pk
    if ek is None or 'maske' not in ek:
        ek = dict(ek or {}); ek['maske'] = degisim_maskesi(poster, kaynak_bayt)
        ek.setdefault('maske_2400', ek['maske'])
    ek['plate_yol'] = bi.get('plate')                  # isim bandi temizligi + kalinti kapisi
    ek['olcum'] = bi.get('olcum')
    try:                                          # GOREV_0020 mesaj murekkebi kapisi
        import mesaj_kapisi
        o = bi['olcum']
        bi['mesaj_kapisi'] = mesaj_kapisi.kapi(poster, o['isim_bant'], o['tag_bant'],
                                               poster.width / 2400.0)
    except Exception as e:                                        # noqa: BLE001
        bi['mesaj_kapisi'] = {'gecti': False, 'hata': f'{type(e).__name__}: {e}'}
    return poster, bi, ek


def tek_dosya(poster, bi, ek, kaynak_bayt, hedef_px, yol, kalite=95, azami_bayt=None):
    """azami_bayt verilirse kalite kademeli dusurulerek dosya butcesine sigdirilir."""
    baski, bpx = baski_dosyasi(poster, ek, kaynak_bayt, hedef_px)
    kullanilan = kalite
    for q in ([kalite] if azami_bayt is None else [kalite, 88, 84, 80, 76, 72, 68]):
        baski.save(yol, 'JPEG', quality=q, subsampling=(0 if q >= 90 else 1), optimize=True)
        kullanilan = q
        if azami_bayt is None or yol.stat().st_size <= azami_bayt:
            break
    return baski, {**bpx, 'dosya_MB': round(yol.stat().st_size / 1e6, 2),
                   'jpeg_kalite': kullanilan}


def bant_dogrulama(cift, boy, P_ed):
    """Bant konumlari bes renkte ayni mi? MB referans, fark <= 2 px.

    Bu artik BILGI amaclidir: siparis ureticisi her dosyayi KENDISINDEN olcuyor
    (Serdar 25 Eyl, 3. madde), MB'den kutu kopyalamiyor. Olculen fark yalniz
    raporlanir, uretimi yonlendirmez.
    NOT (pod canli testinde gorulen hata): `olc()` plate yolunu da ister; plate
    yoluna geciste burasi guncellenmemisti ve bes renkte TypeError, ardindan
    KeyError 'tag_bant' veriyordu. Artik her renk kendi plate'iyle olculur.
    """
    olcek_kur(2400)
    out, temel = {}, None
    for renk in RENKLER:
        try:
            yol = pod_kaynak(cift, renk, boy)
            ed = RENK_ED[renk]
            oran = BOY[boy][0]
            o, _duz, _m = P_ed.olc(yol, P_ed.plate(ed, oran, boy))
            eksik = [a for a in ('isim_bant', 'isim_govde', 'sembol_bant', 'tag_bant',
                                 'sol_isim', 'sag_isim') if a not in o]
            if eksik:
                raise RuntimeError(f'olcumde eksik alan: {eksik}')
            v = {a: o[a] for a in ('isim_bant', 'isim_govde', 'sembol_bant', 'tag_bant')}
            v['sol_isim'] = o['sol_isim']; v['sag_isim'] = o['sag_isim']
            out[renk] = {'olculdu': True, 'bant': v}
            if renk == 'MIDNIGHT_BLUE':
                temel = v
        except BaseException as e:                                # noqa: BLE001
            out[renk] = {'olculdu': False, 'hata': f'{type(e).__name__}: {e}'}
    if temel:
        for renk, v in out.items():
            if not v.get('olculdu') or renk == 'MIDNIGHT_BLUE':
                continue
            f = {a: [int(v['bant'][a][i] - temel[a][i]) for i in range(2)] for a in temel}
            v['fark_px'] = f
            v['en_buyuk_fark'] = max(abs(x) for d in f.values() for x in d)
            v['gecti'] = v['en_buyuk_fark'] <= 2
    olculen = [r for r, v in out.items() if v.get('olculdu')]
    kiyas = [v for r, v in out.items() if 'en_buyuk_fark' in v]
    return {'cift': cift, 'boy': boy, 'referans': 'MIDNIGHT_BLUE', 'esik_px': 2,
            'olculebilen': olculen, 'olculemeyen': [r for r in RENKLER if r not in olculen],
            'en_buyuk_fark': max([v['en_buyuk_fark'] for v in kiyas], default=None),
            'gecti': bool(kiyas) and all(v['gecti'] for v in kiyas), 'renkler': out}


# ------------------------------------------------------------------ ESKI METIN IZI KAPISI (Serdar 1 Eki, siparis 4188621967)
# Bulgu: "A King and his Crab" arkasinda eski motto "Two Souls One Bond" silik izi (CI normal bakista, DB / PW
# kontrastla okunuyor; 11x14 kesitlerde iz p99 3-7 gri seviye). Mevcut kapilar kacirdi: plate_slogan glif
# PAYINA bakar (zayif iz farki esigin ustunde kalir), leke kaynaga karsi olcer (kaynakta da slogan var).
# Olcum (2400 biriminde, mesaj bandi): eski glif maskesi G = KAYNAK sayfanin bantta yerel kontrast maskesi;
# yeni oge maskesi N (+3 px) disarida birakilir; cikti lumasinin yerel zeminden (21 px medyan) sapmasi
# G\N'de medyan alinir, ayni bandin glifsiz pikselindeki taban cikarilir. fazla > ESIK -> FAIL.
IZ_ESIK = 0.6            # gri seviye (eski glif pikselinde isaretli ortalama fazla); sentetik kalibrasyon testte
IZ_PAY = 3               # yeni oge maskesi genisletmesi (2400 px)
IZ_MIN_PX = 200


def eski_metin_izi_kapisi(cikti, kaynak, tag_bant, tag_x, yeni_maske=None, esik=IZ_ESIK):
    """cikti: PIL (baski / sayfa); kaynak: bayt / yol / PIL (eski slogan iceren onayli sayfa); bant 2400 biriminde."""
    import cv2
    from pilot6 import LUMA
    eu = _mod('edisyon_uret')
    olcek_kur(2400)

    def n24(im):
        im = im if isinstance(im, Image.Image) else Image.open(io.BytesIO(im) if isinstance(im, (bytes, bytearray)) else im)
        im = im.convert('RGB')
        return np.asarray(im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)).astype(np.float32) @ LUMA
    Ls, Lo = n24(kaynak), n24(cikti)
    h = min(Ls.shape[0], Lo.shape[0])
    y0, y1 = max(int(tag_bant[0]) - 12, 0), min(int(tag_bant[1]) + 12, h)
    x0, x1 = max(int(tag_x[0]) - 40, 0), min(int(tag_x[1]) + 40, 2400)
    acik = float(np.median(Ls)) > 128
    G = eu.edisyon_maske(Ls, acik)[y0:y1, x0:x1]
    if yeni_maske is not None:
        ym = np.asarray(yeni_maske).astype(np.uint8)
        ym = cv2.resize(ym, (2400, round(ym.shape[0] * 2400 / ym.shape[1])), interpolation=cv2.INTER_NEAREST) > 0
        N = np.zeros_like(G); hh = min(ym.shape[0], y1) - y0
        if hh > 0:
            N[:hh] = ym[y0:y0 + hh, x0:x1]
    else:
        N = eu.edisyon_maske(Lo, float(np.median(Lo)) > 128)[y0:y1, x0:x1]
    N = cv2.dilate(N.astype(np.uint8), np.ones((2 * IZ_PAY + 1,) * 2, np.uint8)) > 0
    def sapma(L):
        u = np.clip(L, 0, 255).astype(np.uint8)
        return L - cv2.medianBlur(u, 21).astype(np.float32)
    ds = sapma(Ls[y0:y1, x0:x1]); do = sapma(Lo[y0:y1, x0:x1])
    R = G & ~N
    B = ~cv2.dilate(G.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~N
    r = {'esik': esik, 'eski_glif_px': int(R.sum()), 'bant': [y0, y1], 'x': [x0, x1]}
    if R.sum() < IZ_MIN_PX or B.sum() < IZ_MIN_PX:
        return {**r, 'gecti': None, 'sebep': 'olculecek eski glif pikseli yok'}
    yon = 1.0 if float(np.median(ds[G])) >= 0 else -1.0       # eski glif zeminden acik mi koyu mu (kaynakta)
    iz, taban = float(np.mean(yon * do[R])), float(np.mean(yon * do[B]))
    r.update({'yon': yon, 'iz_ort': round(iz, 2), 'taban_ort': round(taban, 2), 'fazla': round(iz - taban, 2),
              'kaynak_glif_kontrast': round(float(np.mean(yon * ds[G])), 1)})
    r['gecti'] = bool(iz - taban <= esik)
    return r


def kapilari_topla(bi, isimler, mesaj, baski_px, uretim_px, dosya_mb=None, azami_mb=None):
    fk = font_kapsami(isimler, mesaj)
    bk = boy_kapisi(baski_px, uretim_px, dosya_mb, azami_mb)
    k = {'kalinti': bi['kalinti_kapisi']['gecti'],
         'temiz_ara_zemin': bi.get('temiz_ara_kapisi', {}).get('gecti'),
         'sembol': bi['sembol_kapisi']['gecti'],
         'plate_slogan': bi.get('plate_slogan_kapisi', {}).get('gecti'),
         'olcek': bi.get('olcek_kapisi', {}).get('gecti'),
         'leke': bi.get('leke_kapisi', {}).get('gecti'),
         'boy_siniri': bk['gecti'], 'font_kapsami': fk['gecti'],
         'mesaj_murekkep': bi.get('mesaj_kapisi', {}).get('gecti'),
         'isim_kalinti': bi.get('isim_kalinti_kapisi', {}).get('gecti'),
         'isim_kenar': (bi.get('isim_kenar_kapisi') or {}).get('gecti'),
         'eski_metin_izi': (bi.get('eski_metin_izi_kapisi') or {}).get('gecti')}
    return k, {'boy_siniri': bk, 'font_kapsami': fk, 'mesaj_murekkep': bi.get('mesaj_kapisi')}


def kapi_sonucu(kapilar):
    """None = uygulanmadi (bloklamaz). False = KALDI."""
    return all(v is not False for v in kapilar.values())


def kontrol_paketi(cik, baski, bi, ek, ana_ad, sonek=''):
    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    o = bi['olcum']
    # Kirpim penceresi ISIMLERIN kutusundan alinir. 25 Eyl olcumu: pencere
    # sembollerden turetildiginde isimler sembollerden genis oldugu icin
    # "EMILY"nin E'si ve "JAMES"in S'si disarida kaliyordu.
    if o.get('sol_isim') and o.get('sag_isim'):
        isim_x = [o['sol_isim'][0] - 80, o['sag_isim'][1] + 80]
    elif o.get('sembol'):
        isim_x = [o['sembol'][0][0] - 200, o['sembol'][1][1] + 200]
    else:
        isim_x = [0, 2400]
    isim_x = [max(isim_x[0], 0), isim_x[1]]
    d = {}
    try:
        d['isim'] = bant_kirpim(baski, o['isim_bant'], isim_x, f'ISIM_BANDI_x3{sonek}.jpg', kon)
        d['mesaj'] = bant_kirpim(baski, o['tag_bant'], [300, 2100], f'MESAJ_BANDI_x3{sonek}.jpg', kon)
    except Exception as e:                                        # noqa: BLE001
        d['bant_hata'] = f'{type(e).__name__}: {e}'
    try:                                                          # Serdar 2. madde
        d['silinen'] = silinen_kirpim(baski, ek.get('silinen_2400', ek['maske_2400']),
                                      f'SILINEN_BOLGE_x3{sonek}.jpg', kon)
    except Exception as e:                                        # noqa: BLE001
        d['silinen_hata'] = f'{type(e).__name__}: {e}'
    try:
        from a1_poster import sembol_gorseli, CIK as A1_CIK
        A1_CIK.mkdir(parents=True, exist_ok=True)
        sembol_gorseli(ek['kirp'], f'SEMBOL{sonek}.jpg')
        (A1_CIK / f'SEMBOL{sonek}.jpg').replace(kon / f'SEMBOL_kaynak_vs_yeni{sonek}.jpg')
    except Exception as e:                                        # noqa: BLE001
        d['sembol_gorseli'] = f'uretilemedi: {e}'
    if ana_ad:
        (kon / ana_ad).write_bytes((cik / ana_ad).read_bytes())
    return d


def pod_uret(sip, kaynak_bayt, P_blue, P_ed, cik):
    ed, oran = sip['edisyon'], sip['oran']
    isimler = (sip['isim1'], sip['isim2']); mesaj = sip.get('mesaj') or ''
    # MB olcumu kaldirildi (Serdar onayi 25 Eyl, 3. madde): her dosya kendisinden.
    poster, bi, ek = render_et(ed, oran, sip['sayfa'], kaynak_bayt, isimler, mesaj,
                               P_blue, P_ed, sip['cift'], ref_boy=sip['boy'],
                               hedef_en=sip['hedef_px'][0], boy=sip['boy'])
    if poster is None:
        return {**sip, **bi}
    ad = f'BASKI_{sip["boy"]}.jpg'
    baski, bpx = tek_dosya(poster, bi, ek, kaynak_bayt, sip['hedef_px'], cik / ad)
    bi['leke_kapisi'] = leke_kapisi(baski, kaynak_bayt, ek['maske'])
    bi['olcek_kapisi'] = olcek_kapisi_baski(baski, ek.get('p0', poster), bi['olcum']['isim_bant'])
    # 30 Eyl (GEMINI_LEO DB konum 1.18): olcek FAIL ise isim satiri 2400 yerlesiminden OLCEKLENEREK yeniden
    # render edilir (_SatirYerlesim); yalniz olcek kapisi o zaman PASS olursa kullanilir. Varsayilan yol
    # degismez: regresyon 36756875368'de olcekli yerlesim her hucrede kullanilinca 4 DB hucresi PASS->FAIL oldu.
    if ed != 'blue' and not bi['olcek_kapisi'].get('gecti') and sip['hedef_px'][0] != 2400:
        SATIR_OLCEKLI['etkin'] = True
        try:
            p2, bi2, ek2 = render_et(ed, oran, sip['sayfa'], kaynak_bayt, isimler, mesaj, P_blue, P_ed,
                                     sip['cift'], ref_boy=sip['boy'], hedef_en=sip['hedef_px'][0], boy=sip['boy'])
        finally:
            SATIR_OLCEKLI['etkin'] = False
        if p2 is not None:
            gecici = cik / f'_olcekli_{ad}'
            b2, bpx2 = tek_dosya(p2, bi2, ek2, kaynak_bayt, sip['hedef_px'], gecici)
            ok2 = olcek_kapisi_baski(b2, ek2.get('p0', p2), bi2['olcum']['isim_bant'])
            ilk = {q: bi['olcek_kapisi'].get(q) for q in ('konum_fark_px', 'kenar_fark_px')}
            if ok2.get('gecti'):
                gecici.replace(cik / ad)
                poster, bi, ek, baski, bpx = p2, bi2, ek2, b2, bpx2
                bi['leke_kapisi'] = leke_kapisi(baski, kaynak_bayt, ek['maske'])
                bi['olcek_kapisi'] = {**ok2, 'yerlesim': 'olcekli (2400 x k)', 'ilk_yerlesim': ilk}
            else:
                gecici.unlink(missing_ok=True)
                bi['olcek_kapisi']['olcekli_deneme'] = {q: ok2.get(q) for q in ('konum_fark_px', 'kenar_fark_px')}
    bi['isim_kalinti_kapisi'] = isim_kalinti_kapisi(baski, *koruma(ek)[:1], bi['olcum'], ham=koruma(ek)[1],
                                                    alan=ek.get('maske'))
    bi['isim_kenar_kapisi'] = (bpx.get('isim_bandi_temizligi') or {}).get('kenar')
    bi['eski_metin_izi_kapisi'] = _iz_kapisi(baski, kaynak_bayt, bi, ek)   # 1 Eki: yeni kapi (cikti degismez)
    if _TANI is not None:                         # baski_tani.py: goruntuler (kapiya etkisi yok)
        _TANI.update({'baski': baski, 'p0': ek.get('p0', poster), 'poster': poster, 'yeni': ek.get('yeni'),
                      'koruma': koruma(ek)})
    onizleme(baski, poster, ek, f'ONIZLEME_{sip["boy"]}.jpg', cik)
    bant = kontrol_paketi(cik, baski, bi, ek, ad)
    inc = sip['inc']
    # Serdar 3. madde: beklenen boy URETIM dosyasinin kendi pikselinden
    kapilar, ayrinti = kapilari_topla(bi, isimler, mesaj, bpx['baski_px'], sip['hedef_px'])
    metin_en = bi.get('poster_px', [2400])[0]
    bi.update({**bpx, 'bant_kirpimlari': bant, 'kapi_ayrinti': ayrinti,
               'gorsel_dpi': [round(bpx['baski_px'][0] / inc[0], 1),
                              round(bpx['baski_px'][1] / inc[1], 1)],
               'metin_dpi': round(metin_en / inc[0], 1),
               'metin_render_px': metin_en,
               'kapilar': kapilar, 'kapilar_gecti': kapi_sonucu(kapilar)})
    return {**sip, **bi}


def _iz_kapisi(baski, kaynak_bayt, bi, ek):
    try:
        o = bi.get('olcum') or {}
        if not o.get('tag_bant') or not (o.get('tag_x') or o.get('tag_bant')):
            return {'gecti': None, 'sebep': 'mesaj bandi olcumu yok'}
        # 1 Eki (siparis 4188621967, iz-tani 36886773315): yatay pencere ESKI SLOGANIN OLCULEN genisligi
        # (plate_slogan_kapisi tag_x, kaynak - plate). bi['olcum'] tag_x tasimiyordu -> [300, 2100] sabiti bandin
        # iki yanindaki tasarim yildizlarini (DB 11x14: x 281 / 2094, 13x16 px) 'eski glif' sayiyordu; DB 11x14
        # fazla 3.62'nin tamami bu 208 px, silik iz 0.00. Iz olcumu, esik, bant ve yeni maske AYNI.
        pk = bi.get('plate_slogan_kapisi') or {}
        tx = o.get('tag_x') or pk.get('tag_x') or [300, 2100]
        r = eski_metin_izi_kapisi(baski, kaynak_bayt, o['tag_bant'], tx, ek.get('yeni'))
        r['x_kaynagi'] = 'olcum' if o.get('tag_x') else ('plate_slogan_kapisi' if pk.get('tag_x') else 'sabit')
        return r
    except Exception as e:                                        # noqa: BLE001
        return {'gecti': False, 'hata': f'{type(e).__name__}: {e}'}


def dijital_leke(baski, kaynak_bayt, ek):
    """DIJITAL leke kapisi KAYNAGA karsi (POD ile ayni, leke_kapisi docstring'i). 1 Eki (siparis 4188621967):
    dijital yol plate'e karsi olcuyordu; plate yalniz oge ayirmak icindir, burc resmini / yildizlari plate ile
    karsilastirmak gercek tasarimi leke sayiyordu (CANCER_LEO DB + CI: 3x4 / 4x5 / 11x14 / A sayfalarinin hepsi
    'leke' FAIL). Esik ve olcum ayni; yalniz referans tuval duzeldi."""
    return leke_kapisi(baski, kaynak_bayt, ek['maske'])


def olcek_ikinci_deneme(ed, hedef_en, ilk, yeniden, olcek_olc, leke_olc, hedef_yol, kutle_dene=True):
    """POD'daki (siparis-baski-v1 pod_uret) olcek ikinci denemesinin AYNISI, dijital yol icin.

    olcek FAIL (Blue disi, hedef != 2400) -> isim satiri 2400 yerlesiminden olceklenerek yeniden render
    (SATIR_OLCEKLI / _SatirYerlesim, POD ile ayni kod); yalniz olcek kapisi o zaman PASS olursa kullanilir,
    leke yeniden olculur. ilk = (poster, bi, ek, baski, bpx); yeniden() -> (p, bi, ek, baski, bpx, gecici_yol)
    ya da None. Doner: secilen (poster, bi, ek, baski, bpx)."""
    poster, bi, ek, baski, bpx = ilk
    if (ed == 'blue' and not MB_HEDEF['etkin']) or bi['olcek_kapisi'].get('gecti') or hedef_en == 2400:
        return ilk
    ilk_o = {q: bi['olcek_kapisi'].get(q) for q in ('konum_fark_px', 'kenar_fark_px')}
    denemeler = {}
    # 1 Eki (siparis 4188621967 DB 18x24 konum 1.52; olcekli 1.97, kutle 1.97): ucuncu deneme GENISLIK. Fark yer
    # degil isim GENISLIGI (sol isim x0 +0.42 / x1 -1.65 -> 2.07 birim dar): sabit punto hi-res'te farkli
    # yuvarlanir, hicbir kaydirma ikisini birden 1'in altina indiremez. Hi-res isim plakasi yatayda 2400 x k
    # murekkep genisligine (en fazla %2) esitlenir; render hi-res kalir (2400'den buyutme yok).
    for ad, kutle, gen in (('olcekli (2400 x k)', False, False), ('olcekli kutle (2400 x k)', True, False),
                           ('olcekli kutle genislik (2400 x k)', True, True)):
        if kutle and not kutle_dene:
            break
        SATIR_OLCEKLI['etkin'] = True; SATIR_OLCEKLI['kutle'] = kutle; SATIR_OLCEKLI['genislik'] = gen
        try:
            r2 = yeniden()
        finally:
            SATIR_OLCEKLI['etkin'] = False; SATIR_OLCEKLI['kutle'] = False; SATIR_OLCEKLI['genislik'] = False
        if r2 is None:
            continue
        p2, bi2, ek2, b2, bpx2, gecici = r2
        ok2 = olcek_olc(b2, ek2, p2, bi2)
        denemeler[ad] = {q: ok2.get(q) for q in ('konum_fark_px', 'kenar_fark_px')}
        if ok2.get('gecti'):
            Path(gecici).replace(hedef_yol)
            bi2['leke_kapisi'] = leke_olc(b2, ek2)
            bi2['olcek_kapisi'] = {**ok2, 'yerlesim': ad, 'ilk_yerlesim': ilk_o, 'denemeler': denemeler}
            return p2, bi2, ek2, b2, bpx2
        Path(gecici).unlink(missing_ok=True)
    if denemeler:
        bi['olcek_kapisi']['olcekli_deneme'] = denemeler.get('olcekli (2400 x k)')
        bi['olcek_kapisi']['denemeler'] = denemeler
    return ilk


def _dijital_is(arg):
    """Tek (renk, oran) isi - paralel havuzda kosar (Serdar 4. madde)."""
    renk, oran, sip, klas, kon = arg
    oran = dijital_oran(oran)
    ed = RENK_ED[renk]; boy = DIJITAL_BOY[oran]
    isimler = (sip['isim1'], sip['isim2']); mesaj = sip.get('mesaj') or ''
    try:
        yol = pod_kaynak(sip['cift'], renk, boy)
        kb = yol.read_bytes()
        with Image.open(yol) as im:
            hedef = list(im.size)
        P_ed = EdisyonPoster(); P_blue = BluePoster() if ed == 'blue' else None
        render_oran = 'A' if oran == 'a_series' else oran
        MB_HEDEF['etkin'] = ed == 'blue'                 # yalniz dijital MB (Serdar 1 Eki); POD hic acmaz
        poster, bi, ek = render_et(ed, render_oran, sip['sayfa'], kb, isimler, mesaj,
                                   P_blue, P_ed, sip['cift'], ref_boy=boy,
                                   hedef_en=hedef[0], boy=boy)
        if poster is None:
            return renk, oran, {'durum': 'ELLE KONTROL', **bi}, None
        jpg = klas / f'{sip["cift"]}_{renk}_{oran}_{boy}.jpg'
        butce = int(PDF_AZAMI_MB * 1e6 * 0.92 / len(DIJITAL_ORANLAR))
        baski, bpx = tek_dosya(poster, bi, ek, kb, hedef, jpg, kalite=DIJITAL_KALITE, azami_bayt=butce)
        bi['leke_kapisi'] = dijital_leke(baski, kb, ek)
        bi['olcek_kapisi'] = olcek_kapisi_baski(baski, ek.get('p0', poster),
                                                bi['olcum']['isim_bant'])

        def yeniden():                            # ikinci deneme: ayni render + ayni baski butcesi
            p2, bi2, ek2 = render_et(ed, render_oran, sip['sayfa'], kb, isimler, mesaj, P_blue, P_ed,
                                     sip['cift'], ref_boy=boy, hedef_en=hedef[0], boy=boy)
            if p2 is None:
                return None
            gecici = klas / f'_olcekli_{jpg.name}'
            b2, bpx2 = tek_dosya(p2, bi2, ek2, kb, hedef, gecici, kalite=DIJITAL_KALITE, azami_bayt=butce)
            return p2, bi2, ek2, b2, bpx2, gecici
        poster, bi, ek, baski, bpx = olcek_ikinci_deneme(
            ed, hedef[0], (poster, bi, ek, baski, bpx), yeniden,
            lambda b, e, p, i: olcek_kapisi_baski(b, e.get('p0', p), i['olcum']['isim_bant']),
            lambda b, e: dijital_leke(b, kb, e), jpg)
        bi['isim_kalinti_kapisi'] = isim_kalinti_kapisi(baski, *koruma(ek)[:1], bi['olcum'],
                                                        ham=koruma(ek)[1], alan=ek.get('maske'))
        bi['isim_kenar_kapisi'] = (bpx.get('isim_bandi_temizligi') or {}).get('kenar')
        bi['eski_metin_izi_kapisi'] = _iz_kapisi(baski, kb, bi, ek)
        kapilar, ayrinti = kapilari_topla(bi, isimler, mesaj, bpx['baski_px'], hedef)
        kayit = {'durum': 'URETILDI', 'boy': boy, **bpx, 'kapilar': kapilar,
                 'eski_metin_izi_kapisi': bi.get('eski_metin_izi_kapisi'),
                 'kapi_ayrinti': ayrinti, 'kapilar_gecti': kapi_sonucu(kapilar),
                 'olcek_kapisi': bi.get('olcek_kapisi'), 'leke_kapisi': bi.get('leke_kapisi'),
                 'metin_render_px': bi.get('poster_px', [2400])[0], 'sure_sn': bi.get('sure_sn')}
        if oran == '3x4':
            ornek = kon / f'ORNEK_3x4_{renk}.jpg'
            ornek.write_bytes(jpg.read_bytes())
            kontrol_paketi(cik=klas.parent, baski=baski, bi=bi, ek=ek, ana_ad=None,
                           sonek=f'_{renk}')
            return renk, oran, kayit, str(ornek)
        return renk, oran, kayit, None
    except BaseException as e:                                    # noqa: BLE001
        return renk, oran, {'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}'}, None
    finally:
        MB_HEDEF['etkin'] = False


def pdf_adi(cift, renk):
    a, b = (x.title() for x in cift.split('_', 1))
    return f'AstroLove_{a}_{b}_{renk.title()}.pdf'


def pdf_yap(sayfalar, yol):
    """sayfalar: [(jpg_yolu, boy)]. Sayfa = fiziksel boy (BOY inc), JPEG yeniden sikistirilmadan gomulur."""
    import img2pdf
    olcu = [(BOY[b][1] * 72.0, BOY[b][2] * 72.0) for _, b in sayfalar]
    sira = iter(olcu)

    def yerlesim(_w, _h, _dpi):                     # img2pdf sayfa basina sirayla cagirir
        pw, ph = next(sira)
        return pw, ph, pw, ph
    with open(yol, 'wb') as f:
        f.write(img2pdf.convert([str(j) for j, _ in sayfalar], layout_fun=yerlesim))
    return yol


def _ncc_kucuk(a_bayt, b_yol, en=600):
    def ac(v):
        with Image.open(io.BytesIO(v) if isinstance(v, bytes) else v) as im:
            im.draft('L', (en, en * im.size[1] // im.size[0]))
            return np.asarray(im.convert('L').resize((en, round(en * im.size[1] / im.size[0])),
                                                      Image.BOX)).astype(np.float64)
    a, b = ac(a_bayt), ac(b_yol)
    h = min(a.shape[0], b.shape[0]); a, b = a[:h].ravel(), b[:h].ravel()
    if np.array_equal(a, b):
        return 1.0
    a -= a.mean(); b -= b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def pdf_kapisi(yol, sayfalar, dpi=None):
    """PASS/FAIL: sayfa sayisi, sayfa olcusu, gomulu gorsel dpi, JPEG ayni bayt, NCC>=0.99, boyut."""
    import pikepdf
    dpi = dpi or DPI
    r = {'dosya': yol.name, 'MB': round(yol.stat().st_size / 1e6, 2), 'sayfalar': []}
    r['boyut_gecti'] = r['MB'] <= PDF_AZAMI_MB
    r['hedef_40MB'] = r['MB'] <= PDF_HEDEF_MB
    with pikepdf.open(yol) as pdf:
        r['sayfa_sayisi'] = len(pdf.pages)
        for sayfa, (jpg, boy) in zip(pdf.pages, sayfalar):
            mb = [float(x) for x in sayfa.mediabox]
            w_mm, h_mm = (mb[2] - mb[0]) / 72 * 25.4, (mb[3] - mb[1]) / 72 * 25.4
            bek = (BOY[boy][1] * 25.4, BOY[boy][2] * 25.4)
            gorsel = next(iter(sayfa.images.values()))
            ham = gorsel.read_raw_bytes()
            px = (int(gorsel.Width), int(gorsel.Height))
            gdpi = (px[0] / (w_mm / 25.4), px[1] / (h_mm / 25.4))
            s = {'boy': boy, 'sayfa_mm': [round(w_mm, 2), round(h_mm, 2)],
                 'beklenen_mm': [round(bek[0], 2), round(bek[1], 2)], 'px': list(px),
                 'dpi': [round(gdpi[0], 1), round(gdpi[1], 1)],
                 'filtre': str(gorsel.get('/Filter')), 'ayni_bayt': ham == Path(jpg).read_bytes(),
                 'ncc': round(_ncc_kucuk(ham, jpg), 5)}
            s['olcu_gecti'] = abs(w_mm - bek[0]) <= SAYFA_TOL_MM and abs(h_mm - bek[1]) <= SAYFA_TOL_MM
            s['dpi_gecti'] = all(abs(d - dpi) <= dpi * DPI_TOL for d in gdpi)
            s['gecti'] = bool(s['olcu_gecti'] and s['dpi_gecti'] and s['ncc'] >= 0.99
                              and s['filtre'] == '/DCTDecode')
            r['sayfalar'].append(s)
    r['gecti'] = bool(r['sayfa_sayisi'] == len(DIJITAL_ORANLAR) == len(r['sayfalar'])
                      and r['boyut_gecti'] and all(s['gecti'] for s in r['sayfalar']))
    return r


def dijital_uret(sip, P_blue, P_ed, cik, paralel=3):
    """Bes renk x bes oran; oranlar PARALEL (Serdar 4. madde, hedef < 10 dk). Teslim: renk basina 1 PDF."""
    from multiprocessing import get_context
    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    R = {'urun': 'DIJITAL', 'renkler': {}, 'pdf_azami_MB': PDF_AZAMI_MB, 'paralel': paralel}
    R['bant_dogrulama'] = bant_dogrulama(sip['cift'], DIJITAL_BOY['3x4'], P_ed)
    onizleme_yollari = []
    isler = []
    renkler = (sip['renk'],) if sip.get('yalniz_renk') else RENKLER
    for renk in renkler:
        klas = cik / renk; klas.mkdir(parents=True, exist_ok=True)
        # buyukten kucuge: uzun isler once baslasin
        for oran in sorted(DIJITAL_ORANLAR, key=lambda o: -BOY[DIJITAL_BOY[o]][1]):
            isler.append((renk, oran, sip, klas, kon))
    ctx = get_context('fork')
    with ctx.Pool(processes=paralel) as havuz:
        sonuc = havuz.map(_dijital_is, isler, chunksize=1)
    for renk, oran, kayit, ornek in sonuc:
        rk = R['renkler'].setdefault(renk, {'edisyon': RENK_ED[renk], 'oranlar': {},
                                            'durum': 'URETILDI'})
        rk['oranlar'][oran] = kayit
        if kayit.get('durum') != 'URETILDI':
            rk['durum'] = 'EKSIK'
        if ornek:
            onizleme_yollari.append((renk, Path(ornek)))
    for renk in renkler:
        klas = cik / renk
        rk = R['renkler'][renk]
        rk['dosya_sayisi'] = len(list(klas.glob('*.jpg')))
        sayfalar = []
        for oran in DIJITAL_ORANLAR:                                  # PDF sayfa sirasi
            bul = sorted(klas.glob(f'*{renk}_{oran}*.jpg'))
            if len(bul) == 1:
                sayfalar.append((bul[0], DIJITAL_BOY[oran]))
        rk['pdf_icerik'] = [f'{j.name} -> {b}' for j, b in sayfalar]
        if rk['dosya_sayisi'] != len(DIJITAL_ORANLAR) or len(sayfalar) != len(DIJITAL_ORANLAR):
            rk['durum'] = 'EKSIK'
        if rk['durum'] == 'URETILDI':
            pdf = pdf_yap(sayfalar, klas / pdf_adi(sip['cift'], renk))
            rk['pdf'] = pdf.name
            rk['pdf_kapisi'] = pdf_kapisi(pdf, sayfalar)
            rk['pdf_MB'] = rk['pdf_kapisi']['MB']
            if not rk['pdf_kapisi']['gecti']:
                rk['durum'] = 'EKSIK'
        if rk['durum'] != 'URETILDI':
            import shutil
            shutil.rmtree(klas)
        log('dijital', renk, {a: rk.get(a) for a in ('durum', 'pdf', 'pdf_MB', 'dosya_sayisi')})
    if onizleme_yollari:
        sirali = [(r, y) for r in renkler for rr, y in onizleme_yollari if rr == r]
        R['renk_onizleme'] = renk_onizleme(sirali, 'BES_RENK_ONIZLEME.jpg', kon)
    R['toplam_pdf'] = sum(1 for v in R['renkler'].values() if v.get('pdf'))
    R['durum'] = ('URETILDI' if all(v.get('durum') == 'URETILDI' and v.get('pdf_kapisi', {}).get('gecti')
                                    for v in R['renkler'].values()) else 'EKSIK')
    R['kapilar_gecti'] = R['durum'] == 'URETILDI' and all(
        o.get('kapilar_gecti') for v in R['renkler'].values() for o in v['oranlar'].values()
        if isinstance(o, dict) and o.get('durum') == 'URETILDI')
    return {**sip, **R}


def duvar_kagidi_uret(sip, cik):
    return {**sip, 'urun': 'DUVAR_KAGIDI', 'durum': 'BEKLIYOR',
            'sebep': ('dijital-78 oturumunun wallpaper kodu bu depoda yok ve henuz onaylanmadi; '
                      '4 renk ZIP + 1 PDF (her biri <= 20 MB) o kod onaylaninca uretilecek.'),
            'kapilar_gecti': None}


# Testlerde SAHTE isim kullanilir; musteri verisi asla depoya girmez (yalniz Drive).
SAHTE = {'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'}
TESTLER = [
    {'receipt': 'TEST_A_ARIES_LEO', 'cift': 'ARIES_LEO', 'renk': 'DEEP_BLACK', 'boy': '30x40',
     'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_B_AQUARIUS_AQUARIUS', 'cift': 'AQUARIUS_AQUARIUS', 'renk': 'PURE_WHITE',
     'boy': 'A3', 'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_C_CANCER_LIBRA', 'cift': 'CANCER_LIBRA', 'renk': 'WARM_PARCHMENT',
     'boy': '30x40', 'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_D_AQUARIUS_CHAMPAGNE', 'cift': 'AQUARIUS_AQUARIUS',
     'renk': 'CHAMPAGNE_IVORY', 'boy': 'A3', 'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_E_DIJITAL_ARIES_LEO', 'cift': 'ARIES_LEO', 'boy': '-',
     'urun': 'dijital', **SAHTE},
    # (f) uzun isim / uzun mesaj siniri: en kucuk boyda en uzun girdi
    {'receipt': 'TEST_F_UZUN_ISIM', 'cift': 'CANCER_LIBRA', 'renk': 'WARM_PARCHMENT',
     'boy': '8x10', 'urun': 'pod', 'isim1': 'MAXIMILIANA', 'isim2': 'CHRISTOPHER',
     'mesaj': 'Two Hearts One Sky Forever Entwined'},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kart')
    ap.add_argument('--cift'); ap.add_argument('--renk'); ap.add_argument('--boy')
    ap.add_argument('--urun', default='pod', choices=('pod', 'dijital'))
    ap.add_argument('--isim1'); ap.add_argument('--isim2'); ap.add_argument('--mesaj', default='')
    ap.add_argument('--mesaj-b64', default='',
                    help='mesaj base64 (bosluklu mesaj workflow ARGS ile bolunmesin diye)')
    ap.add_argument('--test', action='store_true', help='ornek siparisler (canli siparis yok)')
    ap.add_argument('--yalniz', default='',
                    help='--test ile: virgulle ayrilmis receipt parcasi. Dijital paket POD'
                         ' testlerinden ayri kosulabilsin diye (45 dk is siniri).')
    ap.add_argument('--kaynak', default='pod', choices=('pod', 'canva'),
                    help="pod: POD_PRINT'teki onayli baski dosyasi (varsayilan). "
                         "canva: imzali URL listesinden tek sayfa")
    ap.add_argument('--liste', default='SIPARIS_URL.json',
                    help='--kaynak canva icin Drive KISISEL_PILOT altindaki imzali URL listesi')
    ap.add_argument('--plate', default='medyan', choices=('medyan', 'canva'),
                    help='zemin plate kumesi: medyan (<ED>_<boy>.png) ya da canva (<ED>_CANVA_<boy>.png)')
    ap.add_argument('--sip-kok', default='',
                    help='cikti koku (varsayilan TEMP/SIPARIS_ISIM); test icin orn. .../SIPARIS_ISIM/TEST_PDF')
    a = ap.parse_args()
    global SIP
    if a.sip_kok:
        SIP = a.sip_kok
    if a.mesaj_b64:
        import base64
        a.mesaj = base64.b64decode(a.mesaj_b64).decode('utf-8')
    global PLATE_EK
    PLATE_EK = '_CANVA' if a.plate == 'canva' else ''
    log('plate kumesi', a.plate)

    if a.test:
        siparisler = [dict(t) for t in TESTLER]
        if a.yalniz:
            se = [x.strip() for x in a.yalniz.split(',') if x.strip()]
            siparisler = [t for t in siparisler if any(x in t['receipt'] for x in se)]
            if not siparisler:
                raise SystemExit(f'--yalniz hicbir teste uymadi: {a.yalniz}')
    elif a.kart:
        rc('copy', f'{SIP}/{a.kart}', str(W))
        d = kart_oku((W / a.kart).read_text(encoding='utf-8'))
        siparisler = [{**d, 'receipt': Path(a.kart).stem}]
    elif a.cift:
        rec = '_'.join(x for x in (a.cift, a.renk, a.boy) if x) + ('_DIJITAL' if a.urun == 'dijital' else '')
        siparisler = [{'receipt': rec, 'cift': a.cift, 'renk': a.renk, 'boy': a.boy,
                       'urun': a.urun, 'yalniz_renk': a.renk is not None,
                       'isim1': a.isim1, 'isim2': a.isim2, 'mesaj': a.mesaj}]
    else:
        raise SystemExit('--kart, --test ya da elle parametre gerekir')

    no, _ = sayfa_no_tablosu()
    siparisler = [normalize(x) for x in siparisler]
    kaynak_b = {}
    for x in siparisler:
        if x['cift'] not in no:
            raise SystemExit(f'cift POD_PRINT\'te yok: {x["cift"]}')
        x['sayfa'] = no[x['cift']]
        if x['urun'] != 'POD':
            continue
        x['canva_design'] = CANVA[x['edisyon']][x['oran']]
        if a.kaynak == 'pod':
            yol = pod_kaynak(x['cift'], x['renk'], x['boy'])
            with Image.open(yol) as im:
                x['hedef_px'] = list(im.size)          # hedef boy onayli baski dosyasindan
            x['kaynak'] = f'POD_PRINT/{x["cift"]}/{x["renk"]}/{x["boy"]}.jpg'
            kaynak_b[x['receipt']] = yol.read_bytes()
        else:
            x['kaynak'] = f'canva:{x["canva_design"]} p{x["sayfa"]}'
        x['beklenen_px_300dpi'] = [round(x['inc'][0] * DPI), round(x['inc'][1] * DPI)]
    log('siparisler', [{k: x.get(k) for k in ('receipt', 'urun', 'cift', 'renk', 'boy',
                                              'edisyon', 'oran', 'sayfa', 'kaynak', 'hedef_px')}
                       for x in siparisler])

    if a.kaynak != 'pod':
        rc('copy', f'{KP}/{a.liste}', str(W))
        L = json.loads((W / a.liste).read_text())
        for x in siparisler:
            if x['urun'] != 'POD':
                continue
            k = f'{x["edisyon"]}_{x["oran"]}_p{x["sayfa"]}'
            v = L.get(k)
            if v is None:
                raise SystemExit(f'URL listesinde anahtar yok: {k} (liste: {sorted(L)})')
            u = v['url'] if isinstance(v, dict) else v
            maskele(u)
            kaynak_b[x['receipt']] = indir(u)
            with Image.open(io.BytesIO(kaynak_b[x['receipt']])) as im:
                x['hedef_px'] = x.get('hedef_px') or list(im.size)

    kisisel_hazirla(); log('kisisel-v1 hazir')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    P_ed = EdisyonPoster()
    P_blue = BluePoster()
    R = {'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'dpi_hedefi': DPI,
         'siparisler': []}
    bant_kontrol = {}
    for x in siparisler:
        cik = W / x['receipt']; cik.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            if x['urun'] == 'POD':
                anahtar = (x['cift'], x['boy'])
                if anahtar not in bant_kontrol:
                    bant_kontrol[anahtar] = bant_dogrulama(x['cift'], x['boy'], P_ed)
                    log('bant dogrulama', anahtar,
                        {a: bant_kontrol[anahtar].get(a)
                         for a in ('gecti', 'en_buyuk_fark', 'olculemeyen')})
                r = pod_uret(x, kaynak_b[x['receipt']], P_blue, P_ed, cik)
                r['bant_dogrulama'] = bant_kontrol[anahtar]
            elif x['urun'] == 'DIJITAL':
                r = dijital_uret(x, P_blue, P_ed, cik)
            else:
                r = duvar_kagidi_uret(x, cik)
        except BaseException as e:                                # noqa: BLE001
            import traceback
            r = {**x, 'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}',
                 'iz': traceback.format_exc()[-1500:]}
            log(x['receipt'], 'HATA', r['hata'])
        r['toplam_sn'] = round(time.time() - t0, 1)
        R['siparisler'].append(r)
        (cik / 'KAPI_RAPORU.json').write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        rc('copy', str(cik), f'{SIP}/{x["receipt"]}', timeout=1800)
        log(x['receipt'], {k: r.get(k) for k in ('urun', 'durum', 'baski_px', 'gorsel_dpi',
                                                 'metin_dpi', 'kapilar', 'kapilar_gecti',
                                                 'toplam_sn', 'dosya_MB', 'toplam_pdf')})
    R['toplam_sn'] = round(time.time() - T0, 1)
    R['ozet'] = [{k: x.get(k) for k in ('receipt', 'urun', 'durum', 'baski_px', 'gorsel_dpi',
                                        'metin_dpi', 'metin_buyutme', 'kapilar', 'kapilar_gecti',
                                        'toplam_sn', 'dosya_MB', 'toplam_pdf', 'sebep',
                                        'metin_render_px')} for x in R['siparisler']]
    R['bant_dogrulama'] = {f'{a}/{b}': v for (a, b), v in bant_kontrol.items()}
    (W / 'SIPARIS_RAPOR.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(W / 'SIPARIS_RAPOR.json'), f'{SIP}')
    print(json.dumps(R['ozet'], ensure_ascii=False, indent=1, default=str), flush=True)
    kotu = [x['receipt'] for x in R['siparisler']
            if x.get('durum') not in ('URETILDI', 'BEKLIYOR') or x.get('kapilar_gecti') is False]
    if kotu:
        raise SystemExit(f'kapilari gecemeyen ya da uretilemeyen siparis: {kotu}')


if __name__ == '__main__':
    main()
