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
       '24x36': ('2x3', 24, 36),
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

# Urun turu (router kartindan). POD: tek renk+boy baski dosyasi. DIJITAL: 5 renk x 5 oran ZIP.
# DUVAR_KAGIDI: dijital-78 oturumunun wallpaper kodu (henuz onaylanmadi) -> BEKLIYOR.
URUN_ES = {'pod': 'POD', 'print': 'POD', 'baski': 'POD', 'poster': 'POD',
           'dijital': 'DIJITAL', 'digital': 'DIJITAL', 'dijital_duvar_sanati': 'DIJITAL',
           'duvar_kagidi': 'DUVAR_KAGIDI', 'wallpaper': 'DUVAR_KAGIDI'}
# Dijital pakette her oran icin kullanilan onayli baski dosyasi (hepsi 300 dpi)
DIJITAL_BOY = {'4x5': '16x20', '3x4': '18x24', '2x3': '24x36', '11x14': '11x14', 'A': 'A2'}
DIJITAL_ORANLAR = ('4x5', '3x4', '2x3', '11x14', 'A')
ZIP_AZAMI_MB = 20.0
RENKLER = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT')
BUYUT = 3                               # kontrol paketinde bant buyutme


def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


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
    renk = d['renk'].upper().replace(' ', '_').replace('-', '_')
    renk = RENK_TAKMA.get(renk, renk)
    if renk not in RENK_ED:
        raise SystemExit(f'bilinmeyen renk: {d["renk"]} (beklenen {sorted(RENK_ED)})')
    urun = URUN_ES.get(str(d.get('urun', 'pod')).strip().lower().replace(' ', '_'), 'POD')
    out = {**d, 'cift': cift, 'renk': renk, 'urun': urun, 'edisyon': RENK_ED[renk]}
    if urun != 'POD':
        return {**out, 'boy': d.get('boy') or '-', 'oran': None, 'hedef_px': None, 'inc': None}
    boy = d['boy'].strip().upper().replace(' ', '').replace('×', 'x').replace('X', 'x')
    if boy not in BOY:
        raise SystemExit(f'bilinmeyen boy: {d["boy"]} (beklenen {sorted(BOY)})')
    return {**out, 'boy': boy, 'oran': BOY[boy][0],
            'hedef_px': [round(BOY[boy][1] * DPI), round(BOY[boy][2] * DPI)],
            'inc': [BOY[boy][1], BOY[boy][2]]}


# ------------------------------------------------------------------ edisyon sarmalayicisi
class EdisyonPoster:
    """Blue disi dort edisyon: edisyon_uret yolu. Girdi degisir, render kodu degismez."""

    def __init__(self):
        import pilot11, pilot12, pilot16
        import edisyon_uret as eu
        self.p11, self.p12, self.p16, self.eu = pilot11, pilot12, pilot16, eu
        self.sab = json.loads((K / 'scripts' / 'kisisel' / 'ORAN_SABITLERI.json').read_text())
        self.kilitler = self.sab.get('edisyonlar', {})
        self.zemin_indi = set()

    def zemin(self, ed, oran):
        if (ed, oran) in self.zemin_indi:
            return
        hed = self.eu.YOL / ed / 'zemin'
        hed.mkdir(parents=True, exist_ok=True)
        rc('copy', f'{KP}/HAZIR/zemin_{ed}_{oran}.png', str(hed))
        (hed / f'zemin_{ed}_{oran}.png').replace(hed / f'{oran}.png')
        self.zemin_indi.add((ed, oran))

    def __call__(self, sayfa_png, sayfa_no, ed, oran, isimler, tagline):
        from a1_poster import olcum_duzelt, sembol_kapisi, SEMBOL_ESIK
        import giris_dogrula as gd
        t0 = time.time()
        kilit = self.kilitler.get(ed, {}).get(oran)
        if not kilit:
            raise SystemExit(f'{ed} {oran} icin ORAN_SABITLERI kilidi yok')
        self.zemin(ed, oran)
        ham = self.eu.YOL / ed / 'ham'
        ham.mkdir(parents=True, exist_ok=True)
        yol = ham / f'{oran}_p{sayfa_no}.jpg'          # render kodu bu adi okur
        kaynak = Image.open(io.BytesIO(sayfa_png)).convert('RGB')
        hedef_en = OLCUM_EN.get(oran, kaynak.width)
        o = m = duz = None; kullanilan = None; hatalar = []
        for carpan in OLCUM_MERDIVEN:
            en = max(int(round(hedef_en * carpan)), 1200)
            im = (kaynak if en == kaynak.width else
                  kaynak.resize((en, round(kaynak.height * en / kaynak.width)), Image.LANCZOS))
            im.save(yol, 'PNG')                        # kayipsiz: JPEG artefakti eklenmez
            try:
                ref_norm = self.p11.norm(Image.open(yol).convert('RGB'))[0]
                mm = self.eu.murekkep(np.asarray(ref_norm).astype(np.float32))
                oo = self.p11.sayfa_olc(yol, maske=self.eu.edisyon_maske)
                o, duz = olcum_duzelt(oo, mm)
                m = mm; kullanilan = {'olcum_en': en, 'carpan': carpan}
                break
            except BaseException as e:                            # noqa: BLE001
                hatalar.append(f'{en}px: {type(e).__name__}: {e}')
        if o is None:
            raise RuntimeError('olcum yapilamadi: ' + ' | '.join(hatalar))
        self.eu.REF_SAYFA = sayfa_no
        s, S = self.eu.oran_kur(ed, oran, kilit, o)
        g0, g1 = o['isim_govde']
        s['isim_y'] = (g0 + g1) / 2                    # dikey merkez: govde (inen kuyruk haric)
        r = gd.siparis_dogrula(isimler[0], isimler[1], tagline, None)
        if r['durum'] != 'TAMAM':
            return None, {'durum': 'ELLE KONTROL', 'dogrulama': r}, None
        sol, sag = r['sol']['deger'], r['sag']['deger']
        p, bilgi, merkez, x, yeni = self.p16.poster_kur(s, S, {'sol': sol, 'sag': sag}, tagline)
        kapi = self.p16.blok_kapisi(p, S, s, yeni)
        sk, kirp = sembol_kapisi(p, S, s, merkez, m, SEMBOL_ESIK, maske=self.eu.murekkep)
        bilgi_ek = {
            'durum': 'URETILDI', 'edisyon': ed, 'oran': oran, 'sayfa': sayfa_no,
            'kaynak_px': list(kaynak.size), 'olcum_girdisi': kullanilan,
            'olcum_denemeleri': hatalar, 'poster_px': list(p.size),
            'olcum': {k: o.get(k) for k in ('isim_bant', 'isim_govde', 'sembol_bant', 'sembol', 'tag_bant')},
            'olcum_duzeltme': duz, 'kilit': {'bosluk': kilit['bosluk'], 'cap': kilit['cap']},
            'bg_hiza': s.get('bg_hiza'), 'temiz_ara_kapisi': s['temiz_ara_kapisi'],
            'kalinti_kapisi': kapi, 'sembol_kapisi': sk,
            'olcek': bilgi['olcek'], 'punto': bilgi['punto'], 'sure_sn': round(time.time() - t0, 1),
        }
        return p, bilgi_ek, {'ref': S['ref'], 'maske': (S['genis'] | yeni), 'kirp': kirp}


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
    out = np.clip(A * (1 - M) + P * M, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGB'), {
        'kaynak_px': kaynak_px, 'baski_px': list(hedef_px),
        'maske_px_2400': int(ek['maske'].sum()),
        'maske_orani': round(float(ek['maske'].mean()), 5),
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



# ------------------------------------------------------------------ Blue sarmalayicisi (a1, onayli)
class BluePoster:
    """Blue hatti: a1_poster.Poster (pilot16). Boy tavani her oran icin Cancer-Libra'dan alinir."""

    def __init__(self):
        from a1_poster import Poster
        self.P = Poster()
        self.hazir_oran = set()

    def __call__(self, kaynak_bayt, sayfa_no, oran, isimler, tagline, ref_bayt=None, ref_sayfa=28):
        if oran not in self.hazir_oran:
            if ref_bayt is None:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referansi verilmedi (boy tavani)')
            self.P.tavan = None
            self.P(ref_bayt, ref_sayfa, 'blue', oran, isimler, tagline, referans=True)
            self.hazir_oran.add(oran)
        p, bi, kirp = self.P(kaynak_bayt, sayfa_no, 'blue', oran, isimler, tagline)
        return p, {**bi, 'edisyon': 'blue', 'oran': oran, 'durum': 'URETILDI'}, {'kirp': kirp}


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


def render_et(ed, oran, sayfa, kaynak_bayt, isimler, mesaj, P_blue, P_ed, cift=None, ref_boy=None):
    """Tek poster: blue -> a1 (pilot16), diger dort edisyon -> edisyon_uret. Render kodu degismez."""
    if ed == 'blue':
        ref_bayt = None
        if oran not in P_blue.hazir_oran:
            # boy tavani Cancer-Libra'dan (a1 kurali); ayni orandan herhangi bir onayli boy yeter
            boy = ref_boy or DIJITAL_BOY.get(oran)
            if not boy:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referans boyu bulunamadi')
            ref_bayt = pod_kaynak('CANCER_LIBRA', 'MIDNIGHT_BLUE', boy).read_bytes()
        poster, bi, ek = P_blue(kaynak_bayt, sayfa, oran, isimler, mesaj, ref_bayt=ref_bayt)
    else:
        poster, bi, ek = P_ed(kaynak_bayt, sayfa, ed, oran, isimler, mesaj)
    if poster is None:
        return None, bi, None
    if ek is None or 'maske' not in ek:
        ek = dict(ek or {}); ek['maske'] = degisim_maskesi(poster, kaynak_bayt)
    return poster, bi, ek


def tek_dosya(poster, bi, ek, kaynak_bayt, hedef_px, yol, kalite=95):
    baski, bpx = baski_dosyasi(poster, ek, kaynak_bayt, hedef_px)
    baski.save(yol, 'JPEG', quality=kalite, subsampling=0, optimize=True)
    return baski, {**bpx, 'dosya_MB': round(yol.stat().st_size / 1e6, 2)}


def kapilari_topla(bi, isimler, mesaj, baski_px, beklenen_px, dosya_mb=None, azami_mb=None):
    k = {'kalinti': bi['kalinti_kapisi']['gecti'],
         'temiz_ara_zemin': bi.get('temiz_ara_kapisi', {}).get('gecti'),
         'sembol': bi['sembol_kapisi']['gecti'],
         'boy_siniri': boy_kapisi(baski_px, beklenen_px, dosya_mb, azami_mb)['gecti'],
         'font_kapsami': font_kapsami(isimler, mesaj)['gecti']}
    return k, {'boy_siniri': boy_kapisi(baski_px, beklenen_px, dosya_mb, azami_mb),
               'font_kapsami': font_kapsami(isimler, mesaj)}


def pod_uret(sip, kaynak_bayt, P_blue, P_ed, cik):
    ed, oran = sip['edisyon'], sip['oran']
    isimler = (sip['isim1'], sip['isim2']); mesaj = sip.get('mesaj') or ''
    poster, bi, ek = render_et(ed, oran, sip['sayfa'], kaynak_bayt, isimler, mesaj,
                               P_blue, P_ed, sip['cift'], ref_boy=sip['boy'])
    if poster is None:
        return {**sip, **bi}
    ad = f'BASKI_{sip["boy"]}.jpg'
    baski, bpx = tek_dosya(poster, bi, ek, kaynak_bayt, sip['hedef_px'], cik / ad)
    onizleme(baski, poster, ek, f'ONIZLEME_{sip["boy"]}.jpg', cik)

    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    (kon / ad).write_bytes((cik / ad).read_bytes())            # tam cozunurluklu ana dosya
    o = bi['olcum']
    isim_x = [o['sembol'][0][0] - 60, o['sembol'][1][1] + 60] if o.get('sembol') else [0, 2400]
    bant = {}
    try:
        bant['isim'] = bant_kirpim(baski, o['isim_bant'], isim_x, 'ISIM_BANDI_x3.jpg', kon)
        bant['mesaj'] = bant_kirpim(baski, o['tag_bant'], [300, 2100], 'MESAJ_BANDI_x3.jpg', kon)
    except Exception as e:                                      # noqa: BLE001
        bant['hata'] = f'{type(e).__name__}: {e}'
    try:
        from a1_poster import sembol_gorseli, CIK as A1_CIK
        A1_CIK.mkdir(parents=True, exist_ok=True)
        sembol_gorseli(ek['kirp'], 'SEMBOL.jpg')
        (A1_CIK / 'SEMBOL.jpg').replace(kon / 'SEMBOL_kaynak_vs_yeni.jpg')
    except Exception as e:                                      # noqa: BLE001
        bant['sembol_gorseli'] = f'uretilemedi: {e}'

    inc = sip['inc']
    kapilar, ayrinti = kapilari_topla(bi, isimler, mesaj, bpx['baski_px'], sip['beklenen_px_300dpi'])
    bi.update({**bpx, 'bant_kirpimlari': bant, 'kapi_ayrinti': ayrinti,
               'gorsel_dpi': [round(bpx['baski_px'][0] / inc[0], 1), round(bpx['baski_px'][1] / inc[1], 1)],
               'metin_dpi': round(2400 / inc[0], 1),
               'metin_buyutme': round(bpx['baski_px'][0] / 2400, 2),
               'not_dpi': ('gorsel_dpi: onayli baski dosyasinin gercek cozunurlugu. metin_dpi: '
                           'kisisellestirilen isim/mesaj bandinin gercek cozunurlugu '
                           '(onayli render hatti NORM_W=2400 ile calisir).'),
               'kapilar': kapilar, 'kapilar_gecti': all(bool(v) for v in kapilar.values())})
    return {**sip, **bi}


def dijital_uret(sip, P_blue, P_ed, cik):
    """Bes renk, her renk icin bes oran JPG -> renk basina tek ZIP (<= 20 MB)."""
    import zipfile
    isimler = (sip['isim1'], sip['isim2']); mesaj = sip.get('mesaj') or ''
    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    R = {'urun': 'DIJITAL', 'renkler': {}, 'zip_azami_MB': ZIP_AZAMI_MB}
    onizleme_yollari = []
    for renk in RENKLER:
        ed = RENK_ED[renk]
        rk = {'edisyon': ed, 'oranlar': {}, 'durum': 'URETILDI'}
        klas = cik / renk; klas.mkdir(parents=True, exist_ok=True)
        for oran in DIJITAL_ORANLAR:
            boy = DIJITAL_BOY[oran]
            try:
                yol = pod_kaynak(sip['cift'], renk, boy)
                kb = yol.read_bytes()
                with Image.open(yol) as im:
                    hedef = list(im.size)
                poster, bi, ek = render_et(ed, oran, sip['sayfa'], kb, isimler, mesaj,
                                           P_blue, P_ed, sip['cift'], ref_boy=boy)
                if poster is None:
                    rk['oranlar'][oran] = {'durum': 'ELLE KONTROL', **bi}; continue
                jpg = klas / f'{sip["cift"]}_{renk}_{oran}_{boy}.jpg'
                baski, bpx = tek_dosya(poster, bi, ek, kb, hedef, jpg, kalite=90)
                bek = [round(BOY[boy][1] * DPI), round(BOY[boy][2] * DPI)]
                kapilar, ayrinti = kapilari_topla(bi, isimler, mesaj, bpx['baski_px'], bek)
                rk['oranlar'][oran] = {'durum': 'URETILDI', 'boy': boy, **bpx,
                                       'kapilar': kapilar, 'kapi_ayrinti': ayrinti,
                                       'kapilar_gecti': all(bool(v) for v in kapilar.values()),
                                       'sure_sn': bi.get('sure_sn')}
                if oran == '3x4':
                    # KONTROL'e tam cozunurluklu ornek: klasor ZIP sonrasi silinecegi icin once kopyala
                    ornek = kon / f'ORNEK_3x4_{renk}.jpg'
                    ornek.write_bytes(jpg.read_bytes())
                    onizleme_yollari.append((renk, ornek))
                    try:
                        o = bi['olcum']
                        ix = [o['sembol'][0][0] - 60, o['sembol'][1][1] + 60] if o.get('sembol') else [0, 2400]
                        bant_kirpim(baski, o['isim_bant'], ix, f'ISIM_BANDI_x3_{renk}.jpg', kon)
                        bant_kirpim(baski, o['tag_bant'], [300, 2100], f'MESAJ_BANDI_x3_{renk}.jpg', kon)
                    except Exception as e:                       # noqa: BLE001
                        rk['bant_hata'] = f'{type(e).__name__}: {e}'
            except BaseException as e:                           # noqa: BLE001
                rk['oranlar'][oran] = {'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}'}
                rk['durum'] = 'EKSIK'
        # ZIP: 20 MB'i asarsa kalite dusurulur
        zp = cik / f'{sip["cift"]}_{renk}.zip'
        kalite = 90
        while True:
            with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
                for f in sorted(klas.glob('*.jpg')):
                    z.write(f, f.name)
            mb = round(zp.stat().st_size / 1e6, 2)
            if mb <= ZIP_AZAMI_MB or kalite <= 70:
                break
            kalite -= 6
            for f in sorted(klas.glob('*.jpg')):
                Image.open(f).convert('RGB').save(f, 'JPEG', quality=kalite,
                                                  subsampling=1, optimize=True)
        rk['zip_MB'] = mb; rk['zip_kalite'] = kalite
        rk['zip_kapisi'] = mb <= ZIP_AZAMI_MB
        rk['dosya_sayisi'] = len(list(klas.glob('*.jpg')))
        rk['zip_icerik'] = sorted(f.name for f in klas.glob('*.jpg'))
        if rk['dosya_sayisi'] != len(DIJITAL_ORANLAR):
            rk['durum'] = 'EKSIK'
        for f in klas.glob('*.jpg'):                          # Drive'a yalniz ZIP + KONTROL
            f.unlink()
        klas.rmdir()
        R['renkler'][renk] = rk
        log('dijital', renk, {k: rk.get(k) for k in ('durum', 'zip_MB', 'zip_kapisi', 'dosya_sayisi')})
    if onizleme_yollari:
        R['renk_onizleme'] = renk_onizleme(onizleme_yollari, 'BES_RENK_ONIZLEME.jpg', kon)
    R['toplam_zip'] = len(R['renkler'])
    R['durum'] = ('URETILDI' if all(v.get('durum') == 'URETILDI' and v.get('zip_kapisi')
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
    {'receipt': 'TEST_A_ARIES_LEO', 'cift': 'ARIES_LEO', 'renk': 'DEEP_BLACK', 'boy': '12x16',
     'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_B_AQUARIUS_AQUARIUS', 'cift': 'AQUARIUS_AQUARIUS', 'renk': 'PURE_WHITE',
     'boy': 'A3', 'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_C_CANCER_LIBRA', 'cift': 'CANCER_LIBRA', 'renk': 'WARM_PARCHMENT',
     'boy': '30x40', 'urun': 'pod', **SAHTE},
    {'receipt': 'TEST_D_DIJITAL_ARIES_LEO', 'cift': 'ARIES_LEO', 'boy': '-',
     'urun': 'dijital', **SAHTE},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kart')
    ap.add_argument('--cift'); ap.add_argument('--renk'); ap.add_argument('--boy')
    ap.add_argument('--isim1'); ap.add_argument('--isim2'); ap.add_argument('--mesaj', default='')
    ap.add_argument('--test', action='store_true', help='uc ornek siparis (canli siparis yok)')
    ap.add_argument('--kaynak', default='pod', choices=('pod', 'canva'),
                    help="pod: POD_PRINT'teki onayli baski dosyasi (varsayilan). "
                         "canva: imzali URL listesinden tek sayfa")
    ap.add_argument('--liste', default='SIPARIS_URL.json',
                    help='--kaynak canva icin Drive KISISEL_PILOT altindaki imzali URL listesi')
    a = ap.parse_args()

    if a.test:
        siparisler = [dict(t) for t in TESTLER]
    elif a.kart:
        rc('copy', f'{SIP}/{a.kart}', str(W))
        d = kart_oku((W / a.kart).read_text(encoding='utf-8'))
        siparisler = [{**d, 'receipt': Path(a.kart).stem}]
    elif a.cift:
        siparisler = [{'receipt': f'{a.cift}_{a.boy}', 'cift': a.cift, 'renk': a.renk, 'boy': a.boy,
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
    for x in siparisler:
        cik = W / x['receipt']; cik.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            if x['urun'] == 'POD':
                r = pod_uret(x, kaynak_b[x['receipt']], P_blue, P_ed, cik)
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
                                                 'toplam_sn', 'dosya_MB', 'toplam_zip')})
    R['toplam_sn'] = round(time.time() - T0, 1)
    R['ozet'] = [{k: x.get(k) for k in ('receipt', 'urun', 'durum', 'baski_px', 'gorsel_dpi',
                                        'metin_dpi', 'metin_buyutme', 'kapilar', 'kapilar_gecti',
                                        'toplam_sn', 'dosya_MB', 'olcum_girdisi', 'toplam_zip',
                                        'sebep')} for x in R['siparisler']]
    (W / 'SIPARIS_RAPOR.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(W / 'SIPARIS_RAPOR.json'), f'{SIP}')
    print(json.dumps(R['ozet'], ensure_ascii=False, indent=1, default=str), flush=True)
    kotu = [x['receipt'] for x in R['siparisler']
            if x.get('durum') not in ('URETILDI', 'BEKLIYOR') or x.get('kapilar_gecti') is False]
    if kotu:
        raise SystemExit(f'kapilari gecemeyen ya da uretilemeyen siparis: {kotu}')


if __name__ == '__main__':
    main()
