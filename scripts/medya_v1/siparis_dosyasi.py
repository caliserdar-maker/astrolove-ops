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
          'mesaj': 'mesaj', 'message': 'mesaj', 'tagline': 'mesaj'}
    d = {}
    for satir in metin.splitlines():
        s = satir.strip().lstrip('-*# ').strip()
        if ':' not in s:
            continue
        a, b = s.split(':', 1)
        a = a.strip().strip('*_`').lower()
        if a in ES:
            d[ES[a]] = b.strip().strip('*_`')
    eksik = [k for k in ('cift', 'renk', 'boy', 'isim1', 'isim2') if not d.get(k)]
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
    boy = d['boy'].strip().upper().replace(' ', '').replace('×', 'x').replace('X', 'x')
    boy = boy.replace('A3', 'A3').replace('A4', 'A4').replace('A2', 'A2')
    if boy not in BOY:
        raise SystemExit(f'bilinmeyen boy: {d["boy"]} (beklenen {sorted(BOY)})')
    return {**d, 'cift': cift, 'renk': renk, 'boy': boy, 'edisyon': RENK_ED[renk],
            'oran': BOY[boy][0], 'hedef_px': [round(BOY[boy][1] * DPI), round(BOY[boy][2] * DPI)],
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


def uret(sip, kaynak_bayt, P_blue, P_ed, cik):
    ed, oran = sip['edisyon'], sip['oran']
    isimler = (sip['isim1'], sip['isim2'])
    mesaj = sip.get('mesaj') or ''
    if ed == 'blue':
        raise SystemExit('Blue yolu a1_poster.Poster ile kosar; bu testler dort edisyon uzerinde')
    poster, bi, ek = P_ed(kaynak_bayt, sip['sayfa'], ed, oran, isimler, mesaj)
    if poster is None:
        return {**sip, **bi}
    baski, bpx = baski_dosyasi(poster, ek, kaynak_bayt, sip['hedef_px'])
    ad = f'BASKI_{sip["boy"]}.jpg'
    baski.save(cik / ad, 'JPEG', quality=95, subsampling=0, optimize=True)
    onizleme(baski, poster, ek, f'ONIZLEME_{sip["boy"]}.jpg', cik)
    from a1_poster import sembol_gorseli, CIK as A1_CIK
    try:
        A1_CIK.mkdir(parents=True, exist_ok=True)
        sembol_gorseli(ek['kirp'], f'SEMBOL_{sip["cift"]}_{sip["boy"]}.jpg')
        (A1_CIK / f'SEMBOL_{sip["cift"]}_{sip["boy"]}.jpg').replace(
            cik / f'SEMBOL_{sip["cift"]}_{sip["boy"]}.jpg')
    except Exception as e:                                        # noqa: BLE001
        bi['sembol_gorseli'] = f'uretilemedi: {e}'
    inc = sip['inc']
    bi.update({
        **bpx,
        'dosya_MB': round((cik / ad).stat().st_size / 1e6, 2),
        'gorsel_dpi': [round(bpx['baski_px'][0] / inc[0], 1), round(bpx['baski_px'][1] / inc[1], 1)],
        'metin_dpi': round(2400 / inc[0], 1),
        'metin_buyutme': round(bpx['baski_px'][0] / 2400, 2),
        'not_dpi': ('gorsel_dpi: Canva sayfasinin hedef boydaki gercek cozunurlugu. '
                    'metin_dpi: kisisellestirilen isim/tagline bandinin gercek cozunurlugu '
                    '(onayli render hatti NORM_W=2400 ile calisir).'),
    })
    kapilar = {'kalinti': bi['kalinti_kapisi']['gecti'],
               'temiz_ara_zemin': bi['temiz_ara_kapisi']['gecti'],
               'sembol': bi['sembol_kapisi']['gecti']}
    bi['kapilar'] = kapilar
    bi['kapilar_gecti'] = all(kapilar.values())
    return {**sip, **bi}


TESTLER = [
    {'receipt': 'TEST_A_ARIES_LEO', 'cift': 'ARIES_LEO', 'renk': 'DEEP_BLACK', 'boy': '12x16',
     'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'},
    {'receipt': 'TEST_B_AQUARIUS_AQUARIUS', 'cift': 'AQUARIUS_AQUARIUS', 'renk': 'PURE_WHITE', 'boy': 'A3',
     'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'},
    {'receipt': 'TEST_C_CANCER_LIBRA', 'cift': 'CANCER_LIBRA', 'renk': 'WARM_PARCHMENT', 'boy': '30x40',
     'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'},
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
    siparisler = [normalize(s) for s in siparisler]
    kaynak_b = {}
    for s in siparisler:
        if s['cift'] not in no:
            raise SystemExit(f'cift POD_PRINT\'te yok: {s["cift"]}')
        s['sayfa'] = no[s['cift']]
        s['canva_design'] = CANVA[s['edisyon']][s['oran']]
        if a.kaynak == 'pod':
            yol = pod_kaynak(s['cift'], s['renk'], s['boy'])
            with Image.open(yol) as im:
                s['hedef_px'] = list(im.size)          # hedef boy onayli baski dosyasindan
            s['kaynak'] = f'POD_PRINT/{s["cift"]}/{s["renk"]}/{s["boy"]}.jpg'
            kaynak_b[s['receipt']] = yol.read_bytes()
        else:
            s['kaynak'] = f'canva:{s["canva_design"]} p{s["sayfa"]}'
        s['beklenen_px_300dpi'] = [round(s['inc'][0] * DPI), round(s['inc'][1] * DPI)]
    log('siparisler', [{k: s.get(k) for k in ('receipt', 'cift', 'renk', 'boy', 'edisyon', 'oran',
                                              'sayfa', 'kaynak', 'hedef_px', 'beklenen_px_300dpi')}
                       for s in siparisler])

    if a.kaynak != 'pod':
        rc('copy', f'{KP}/{a.liste}', str(W))
        L = json.loads((W / a.liste).read_text())
        for s in siparisler:
            k = f'{s["edisyon"]}_{s["oran"]}_p{s["sayfa"]}'
            v = L.get(k)
            if v is None:
                raise SystemExit(f'URL listesinde anahtar yok: {k} (liste: {sorted(L)})')
            u = v['url'] if isinstance(v, dict) else v
            maskele(u)
            kaynak_b[s['receipt']] = indir(u)
            with Image.open(io.BytesIO(kaynak_b[s['receipt']])) as im:
                s['hedef_px'] = s.get('hedef_px') or list(im.size)
            log('sayfa indi', k, len(kaynak_b[s['receipt']]), 'bayt')

    kisisel_hazirla(); log('kisisel-v1 hazir')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    P_ed = EdisyonPoster()
    P_blue = None
    R = {'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'dpi_hedefi': DPI, 'siparisler': []}
    for s in siparisler:
        cik = W / s['receipt']; cik.mkdir(parents=True, exist_ok=True)
        try:
            r = uret(s, kaynak_b[s['receipt']], P_blue, P_ed, cik)
        except BaseException as e:                                # noqa: BLE001
            import traceback
            r = {**s, 'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}',
                 'iz': traceback.format_exc()[-1500:]}
            log(s['receipt'], 'HATA', r['hata'])
        R['siparisler'].append(r)
        (cik / 'KAPI_RAPORU.json').write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        rc('copy', str(cik), f'{SIP}/{s["receipt"]}')
        log(s['receipt'], {k: r.get(k) for k in ('durum', 'baski_px', 'gorsel_dpi', 'metin_dpi',
                                                 'kapilar', 'kapilar_gecti', 'sure_sn', 'dosya_MB')})
    R['toplam_sn'] = round(time.time() - T0, 1)
    R['ozet'] = [{k: x.get(k) for k in ('receipt', 'durum', 'baski_px', 'gorsel_dpi', 'metin_dpi',
                                        'metin_buyutme', 'kapilar', 'kapilar_gecti', 'sure_sn',
                                        'dosya_MB', 'olcum_girdisi')} for x in R['siparisler']]
    (W / 'SIPARIS_RAPOR.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(W / 'SIPARIS_RAPOR.json'), f'{SIP}')
    print(json.dumps(R['ozet'], ensure_ascii=False, indent=1, default=str), flush=True)
    if not all(x.get('kapilar_gecti') for x in R['siparisler']):
        raise SystemExit('en az bir siparis kapilari gecemedi ya da uretilemedi')


if __name__ == '__main__':
    main()
