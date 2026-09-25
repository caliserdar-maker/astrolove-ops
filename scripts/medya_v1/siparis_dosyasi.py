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
        if (hed / f'{oran}.png').exists():        # paralel isler tekrar indirmesin
            self.zemin_indi.add((ed, oran)); return
        rc('copy', f'{KP}/HAZIR/zemin_{ed}_{oran}.png', str(hed))
        (hed / f'zemin_{ed}_{oran}.png').replace(hed / f'{oran}.png')
        self.zemin_indi.add((ed, oran))

    def olc(self, yol):
        """Sayfa olcumu HER ZAMAN 2400'de (sayfa_olc bu olcekte dogrulandi)."""
        from a1_poster import olcum_duzelt
        olcek_kur(2400)
        ref_norm = self.p11.norm(Image.open(yol).convert('RGB'))[0]
        m = self.eu.murekkep(np.asarray(ref_norm).astype(np.float32))
        o = self.p11.sayfa_olc(yol, maske=self.eu.edisyon_maske)
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
        p, bilgi, merkez, x, yeni = self.p16.poster_kur(
            s, S, {'sol': r['sol']['deger'], 'sag': r['sag']['deger']}, mesaj)
        return s, S, p, (merkez, yeni), {'olcek': bilgi['olcek'], 'punto': bilgi['punto']}

    def __call__(self, kaynak_bayt, sayfa_no, ed, oran, isimler, mesaj,
                 olcum_bayt=None, hedef_en=None):
        from a1_poster import sembol_kapisi, SEMBOL_ESIK
        t0 = time.time()
        kilit = self.kilitler.get(ed, {}).get(oran)
        if not kilit:
            raise SystemExit(f'{ed} {oran} icin ORAN_SABITLERI kilidi yok')
        self.zemin(ed, oran)
        ham = self.eu.YOL / ed / 'ham'; ham.mkdir(parents=True, exist_ok=True)
        yol = ham / f'{oran}_p{sayfa_no}.jpg'
        yol.write_bytes(kaynak_bayt) if kaynak_bayt[:3] == b'\xff\xd8\xff' else \
            Image.open(io.BytesIO(kaynak_bayt)).convert('RGB').save(yol, 'PNG')
        # Olcum kaynagi (Serdar 2. madde): dokulu renklerde bantlar ayni cift+boydaki
        # Midnight Blue dosyasindan olculur, tuval kendi rengidir.
        olcum_yolu = yol
        if olcum_bayt is not None and olcum_bayt is not kaynak_bayt:
            olcum_yolu = ham / f'{oran}_olcum_p{sayfa_no}.jpg'
            olcum_yolu.write_bytes(olcum_bayt)
        o, duz, m = self.olc(olcum_yolu)

        # 1) ONAYLI 2400 render (referans, butun mevcut kapilar burada kosar)
        olcek_kur(2400)
        s0, S0, p0, ek0, bi0 = self.render(ed, oran, sayfa_no, o, kilit, isimler, mesaj)
        if p0 is None:
            return None, bi0, None
        merkez0, yeni0 = ek0
        kapi0 = self.p16.blok_kapisi(p0, S0, s0, yeni0)
        sk, kirp = sembol_kapisi(p0, S0, s0, merkez0, m, SEMBOL_ESIK, maske=self.eu.murekkep)
        maske0 = (S0['genis'] | yeni0)
        silinen0 = S0['genis'] & ~yeni0

        # 2) HEDEF COZUNURLUK render (Serdar 1. madde)
        hedef_en = int(hedef_en or 2400)
        if hedef_en != 2400:
            k = hedef_en / 2400.0
            olcek = olcek_kur(hedef_en)
            s1, S1, p1, ek1, bi1 = self.render(ed, oran, sayfa_no, olcekle(o, k),
                                               kilit_olcekle(kilit, k), isimler, mesaj)
            merkez1, yeni1 = ek1
            maske1 = (S1['genis'] | yeni1)
            silinen1 = S1['genis'] & ~yeni1
            leke = leke_kapisi(S1['temiz_a'], np.asarray(S1['ref']).astype(np.float32),
                               silinen1, k=k)
            kucuk = self.p11.norm(p1)[0] if p1.width != 2400 else p1
            olcek_kapi = olcek_kapisi(kucuk, p0, s0)
            olcek_kur(2400)
        else:
            k, s1, S1, p1 = 1.0, s0, S0, p0
            maske1, silinen1 = maske0, silinen0
            olcek = {'hedef_en': 2400, 'k': 1.0}
            leke = leke_kapisi(S0['temiz_a'], np.asarray(S0['ref']).astype(np.float32),
                               silinen0, k=1.0)
            olcek_kapi = {'gecti': True, 'not': 'hedef zaten 2400'}
            bi1 = bi0

        bilgi = {
            'durum': 'URETILDI', 'edisyon': ed, 'oran': oran, 'sayfa': sayfa_no,
            'olcum_kaynagi': ('MIDNIGHT_BLUE' if olcum_yolu is not yol else 'kendi rengi'),
            'kaynak_px': list(Image.open(yol).size), 'poster_px': list(p1.size),
            'olcek': olcek, 'olcek_kapisi': olcek_kapi, 'leke_kapisi': leke,
            'olcum': {a: o.get(a) for a in ('isim_bant', 'isim_govde', 'sembol_bant',
                                            'sembol', 'tag_bant')},
            'olcum_duzeltme': duz, 'kilit': {'bosluk': kilit['bosluk'], 'cap': kilit['cap']},
            'temiz_ara_kapisi': s0['temiz_ara_kapisi'], 'kalinti_kapisi': kapi0,
            'sembol_kapisi': sk, 'punto_2400': bi0['punto'], 'punto_hedef': bi1['punto'],
            'sure_sn': round(time.time() - t0, 1),
        }
        return p1, bilgi, {'maske': maske1, 'silinen': silinen1, 'kirp': kirp,
                           'maske_2400': maske0, 'silinen_2400': silinen0}


def olcek_kapisi(kucuk, p0, s0):
    """Serdar 1. madde kapisi: hi-res sonuc 2400'e indirilince onayli render ile
    boy ve konum farki <= 1 px olmali."""
    import edisyon_uret as eu
    a = np.asarray(kucuk.convert('RGB')).astype(np.float32)
    b = np.asarray(p0.convert('RGB')).astype(np.float32)
    n = min(a.shape[0], b.shape[0])
    g1 = eu.satir_olc(a[:n], s0['isim_bant'])
    g0 = eu.satir_olc(b[:n], s0['isim_bant'])
    if 'hata' in g1 or 'hata' in g0:
        return {'gecti': False, 'sebep': f"olculemedi {g1.get('hata')} / {g0.get('hata')}"}
    d = {}
    for alan in ('cap_sol', 'cap_sag', 'taban_sol', 'taban_sag'):
        d[alan] = int(g1[alan] - g0[alan])
    d['satir_merkez'] = round(g1['satir_merkez'] - g0['satir_merkez'], 1)
    d['bosluk_sol'] = int(g1['bosluk'][0] - g0['bosluk'][0])
    d['bosluk_sag'] = int(g1['bosluk'][1] - g0['bosluk'][1])
    for ad in ('sol_isim', 'sonsuz', 'sag_isim'):
        d[f'{ad}_x0'] = int(g1[ad][0] - g0[ad][0])
        d[f'{ad}_x1'] = int(g1[ad][1] - g0[ad][1])
    en = max(abs(v) for v in d.values())
    return {'gecti': bool(en <= 1), 'en_buyuk_fark_px': en, 'esik_px': 1, 'fark': d,
            'boyut': {'hi_res_2400': list(kucuk.size), 'onayli_2400': list(p0.size)}}


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


def olcekle(d, k):
    """Olculen sayfa kaydini (sayfa_olc + olcum_duzelt) k ile olcekler."""
    def sc(v):
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (int, float)):
            return int(round(v * k)) if isinstance(v, int) else round(v * k, 1)
        if isinstance(v, (list, tuple)):
            return [sc(x) for x in v]
        return v
    return {a: (sc(b) if a in PX_ALAN else b) for a, b in d.items()}


def kilit_olcekle(kilit, k):
    out = dict(kilit)
    out['bosluk'] = int(round(kilit['bosluk'] * k))
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
LEKE_YARICAP = 9        # yuksek frekans olcumu icin medyan yaricapi (2400 uzayinda px)
LEKE_HALKA = 24         # karsilastirma halkasinin kalinligi (2400 uzayinda px)
LEKE_ORAN = 0.55        # silinen bolge enerjisi / halka enerjisi bu orandan kucukse YAMA
LEKE_TON = 3.0          # silinen bolge ile halka arasinda azami ortalama ton farki


def leke_kapisi(temiz_a, ref_a, maske, k=1.0, bloklar=True):
    """Silinen bolgede doku kayboldu mu (yama/leke)? Oran ve ton farki ile."""
    import cv2
    from pilot6 import LUMA
    r = max(int(round(LEKE_YARICAP * k)), 3); r = r if r % 2 else r + 1
    h = max(int(round(LEKE_HALKA * k)), 3)
    L = (temiz_a @ LUMA).astype(np.float32)
    Lr = (ref_a @ LUMA).astype(np.float32)
    hf = np.abs(L - cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), r).astype(np.float32))
    hfr = np.abs(Lr - cv2.medianBlur(np.clip(Lr, 0, 255).astype(np.uint8), r).astype(np.float32))
    ic = maske.astype(bool)
    genis = cv2.dilate(ic.astype(np.uint8), np.ones((2 * h + 1, 2 * h + 1), np.uint8)) > 0
    halka = genis & ~cv2.dilate(ic.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if ic.sum() < 100 or halka.sum() < 100:
        return {'gecti': None, 'sebep': 'olcum alani kucuk',
                'ic_px': int(ic.sum()), 'halka_px': int(halka.sum())}
    ic_e = float(hf[ic].mean()); hal_e = float(hfr[halka].mean())
    oran = ic_e / hal_e if hal_e > 0 else 0.0
    ton = abs(float(L[ic].mean()) - float(Lr[halka].mean()))
    d = {'gecti': bool(oran >= LEKE_ORAN and ton <= LEKE_TON),
         'doku_orani': round(oran, 3), 'esik_oran': LEKE_ORAN,
         'silinen_enerji': round(ic_e, 2), 'halka_enerji': round(hal_e, 2),
         'ton_farki': round(ton, 2), 'esik_ton': LEKE_TON,
         'ic_px': int(ic.sum()), 'halka_px': int(halka.sum()),
         'yaricap': r, 'halka_kalinlik': h}
    if bloklar:                                   # en kotu 64x64 blok (yerel yama)
        B = max(int(round(64 * k)), 16)
        en, yer = None, None
        H, W = ic.shape
        for by in range(0, H - B + 1, B):
            if not ic[by:by + B].any():
                continue
            for bx in range(0, W - B + 1, B):
                m = ic[by:by + B, bx:bx + B]
                if m.sum() < B * B * 0.15:
                    continue
                hb = halka[max(by - h, 0):by + B + h, max(bx - h, 0):bx + B + h]
                hr = hfr[max(by - h, 0):by + B + h, max(bx - h, 0):bx + B + h]
                if hb.sum() < 50:
                    continue
                o = float(hf[by:by + B, bx:bx + B][m].mean()) / max(float(hr[hb].mean()), 1e-6)
                if en is None or o < en:
                    en, yer = o, [bx, by]
        d['en_kotu_blok_orani'] = None if en is None else round(en, 3)
        d['en_kotu_blok_yeri'] = yer
        if en is not None and en < LEKE_ORAN * 0.8:
            d['gecti'] = False
    return d


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


def render_et(ed, oran, sayfa, kaynak_bayt, isimler, mesaj, P_blue, P_ed,
              cift=None, ref_boy=None, olcum_bayt=None, hedef_en=None):
    """blue -> a1 (pilot16, 2400), diger dort edisyon -> edisyon_uret (hedef cozunurluk)."""
    if ed == 'blue':
        ref_bayt = None
        if oran not in P_blue.hazir_oran:
            boy = ref_boy or DIJITAL_BOY.get(oran)
            if not boy:
                raise RuntimeError(f'Blue {oran}: Cancer-Libra referans boyu bulunamadi')
            ref_bayt = pod_kaynak('CANCER_LIBRA', 'MIDNIGHT_BLUE', boy).read_bytes()
        olcek_kur(2400)
        poster, bi, ek = P_blue(kaynak_bayt, sayfa, oran, isimler, mesaj, ref_bayt=ref_bayt)
        bi['olcek_kapisi'] = {'gecti': None, 'sebep': (
            'Blue hatti (a1_poster.Poster) bu iterasyonda 2400 render ediyor; hedef '
            'cozunurluk icin sarmalayiciya hazir olcum parametresi gerekiyor. '
            'Metin dpi = 2400/inc.')}
        bi['leke_kapisi'] = {'gecti': None, 'sebep': 'Blue 2400 render'}
    else:
        poster, bi, ek = P_ed(kaynak_bayt, sayfa, ed, oran, isimler, mesaj,
                              olcum_bayt=olcum_bayt, hedef_en=hedef_en)
    if poster is None:
        return None, bi, None
    if ek is None or 'maske' not in ek:
        ek = dict(ek or {}); ek['maske'] = degisim_maskesi(poster, kaynak_bayt)
        ek.setdefault('maske_2400', ek['maske'])
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
    """Serdar 2. madde: bant konumlari bes renkte ayni mi? MB referans, fark <= 2 px."""
    olcek_kur(2400)
    out, temel = {}, None
    for renk in RENKLER:
        try:
            yol = pod_kaynak(cift, renk, boy)
            o, _duz, _m = P_ed.olc(yol)
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


def kapilari_topla(bi, isimler, mesaj, baski_px, uretim_px, dosya_mb=None, azami_mb=None):
    fk = font_kapsami(isimler, mesaj)
    bk = boy_kapisi(baski_px, uretim_px, dosya_mb, azami_mb)
    k = {'kalinti': bi['kalinti_kapisi']['gecti'],
         'temiz_ara_zemin': bi.get('temiz_ara_kapisi', {}).get('gecti'),
         'sembol': bi['sembol_kapisi']['gecti'],
         'olcek': bi.get('olcek_kapisi', {}).get('gecti'),
         'leke': bi.get('leke_kapisi', {}).get('gecti'),
         'boy_siniri': bk['gecti'], 'font_kapsami': fk['gecti']}
    return k, {'boy_siniri': bk, 'font_kapsami': fk}


def kapi_sonucu(kapilar):
    """None = uygulanmadi (bloklamaz). False = KALDI."""
    return all(v is not False for v in kapilar.values())


def kontrol_paketi(cik, baski, bi, ek, ana_ad, sonek=''):
    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    o = bi['olcum']
    isim_x = [o['sembol'][0][0] - 60, o['sembol'][1][1] + 60] if o.get('sembol') else [0, 2400]
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
    olcum_bayt = None
    if ed != 'blue':                      # Serdar 2. madde: bantlar MB dosyasindan
        olcum_bayt = pod_kaynak(sip['cift'], 'MIDNIGHT_BLUE', sip['boy']).read_bytes()
    poster, bi, ek = render_et(ed, oran, sip['sayfa'], kaynak_bayt, isimler, mesaj,
                               P_blue, P_ed, sip['cift'], ref_boy=sip['boy'],
                               olcum_bayt=olcum_bayt, hedef_en=sip['hedef_px'][0])
    if poster is None:
        return {**sip, **bi}
    ad = f'BASKI_{sip["boy"]}.jpg'
    baski, bpx = tek_dosya(poster, bi, ek, kaynak_bayt, sip['hedef_px'], cik / ad)
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


def _dijital_is(arg):
    """Tek (renk, oran) isi - paralel havuzda kosar (Serdar 4. madde)."""
    renk, oran, sip, klas, kon = arg
    ed = RENK_ED[renk]; boy = DIJITAL_BOY[oran]
    isimler = (sip['isim1'], sip['isim2']); mesaj = sip.get('mesaj') or ''
    try:
        yol = pod_kaynak(sip['cift'], renk, boy)
        kb = yol.read_bytes()
        with Image.open(yol) as im:
            hedef = list(im.size)
        olcum_bayt = None if ed == 'blue' else \
            pod_kaynak(sip['cift'], 'MIDNIGHT_BLUE', boy).read_bytes()
        P_ed = EdisyonPoster(); P_blue = BluePoster() if ed == 'blue' else None
        poster, bi, ek = render_et(ed, oran, sip['sayfa'], kb, isimler, mesaj,
                                   P_blue, P_ed, sip['cift'], ref_boy=boy,
                                   olcum_bayt=olcum_bayt, hedef_en=hedef[0])
        if poster is None:
            return renk, oran, {'durum': 'ELLE KONTROL', **bi}, None
        jpg = klas / f'{sip["cift"]}_{renk}_{oran}_{boy}.jpg'
        butce = int(ZIP_AZAMI_MB * 1e6 * 0.92 / len(DIJITAL_ORANLAR))
        baski, bpx = tek_dosya(poster, bi, ek, kb, hedef, jpg, kalite=92, azami_bayt=butce)
        kapilar, ayrinti = kapilari_topla(bi, isimler, mesaj, bpx['baski_px'], hedef)
        kayit = {'durum': 'URETILDI', 'boy': boy, **bpx, 'kapilar': kapilar,
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


def dijital_uret(sip, P_blue, P_ed, cik, paralel=3):
    """Bes renk x bes oran; oranlar PARALEL (Serdar 4. madde, hedef < 10 dk)."""
    import zipfile
    from multiprocessing import get_context
    kon = cik / 'KONTROL'; kon.mkdir(parents=True, exist_ok=True)
    R = {'urun': 'DIJITAL', 'renkler': {}, 'zip_azami_MB': ZIP_AZAMI_MB, 'paralel': paralel}
    R['bant_dogrulama'] = bant_dogrulama(sip['cift'], DIJITAL_BOY['3x4'], P_ed)
    onizleme_yollari = []
    isler = []
    for renk in RENKLER:
        klas = cik / renk; klas.mkdir(parents=True, exist_ok=True)
        # buyukten kucuge: uzun isler once baslasin
        for oran in sorted(DIJITAL_ORANLAR, key=lambda o: -BOY[DIJITAL_BOY[o]][0]):
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
    for renk in RENKLER:
        klas = cik / renk
        rk = R['renkler'][renk]
        zp = cik / f'{sip["cift"]}_{renk}.zip'
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:
            for f in sorted(klas.glob('*.jpg')):
                z.write(f, f.name)
        rk['zip_MB'] = round(zp.stat().st_size / 1e6, 2)
        rk['zip_kapisi'] = rk['zip_MB'] <= ZIP_AZAMI_MB
        rk['dosya_sayisi'] = len(list(klas.glob('*.jpg')))
        rk['zip_icerik'] = sorted(f.name for f in klas.glob('*.jpg'))
        if rk['dosya_sayisi'] != len(DIJITAL_ORANLAR):
            rk['durum'] = 'EKSIK'
        for f in klas.glob('*.jpg'):
            f.unlink()
        klas.rmdir()
        log('dijital', renk, {a: rk.get(a) for a in ('durum', 'zip_MB', 'dosya_sayisi')})
    if onizleme_yollari:
        sirali = [(r, y) for r in RENKLER for rr, y in onizleme_yollari if rr == r]
        R['renk_onizleme'] = renk_onizleme(sirali, 'BES_RENK_ONIZLEME.jpg', kon)
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
    {'receipt': 'TEST_A_ARIES_LEO', 'cift': 'ARIES_LEO', 'renk': 'DEEP_BLACK', 'boy': '30x40',
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
                                                 'toplam_sn', 'dosya_MB', 'toplam_zip')})
    R['toplam_sn'] = round(time.time() - T0, 1)
    R['ozet'] = [{k: x.get(k) for k in ('receipt', 'urun', 'durum', 'baski_px', 'gorsel_dpi',
                                        'metin_dpi', 'metin_buyutme', 'kapilar', 'kapilar_gecti',
                                        'toplam_sn', 'dosya_MB', 'toplam_zip', 'sebep',
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
