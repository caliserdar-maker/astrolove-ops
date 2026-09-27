#!/usr/bin/env python3
"""POD kapak v3 (Serdar onayi 27 Eyl 2026, ADIM 2). Etsy'ye erisim YOK; yalniz Drive (rclone).

Sablon = onayli CL kapagi (data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg). Duvar ve cerceve
sabittir; yalniz cerceve acikligi (ACIKLIK, onayli dosyadan olculdu) degisir.
Poster = siparis_dosyasi.py'nin (siparis-baski-v1 dali) urettigi gercek BASKI dosyasi, Midnight Blue,
EMILY / JAMES / "It Began With a Kiss in the Rain". Sembol ve yazi yeniden cizilmez; dosya yalniz
olceklenir ve aciklik icine yapistirilir (renk/filtre degisikligi yok).

Adimlar (--mod ornek):
  1) yer: POD_PRINT/CANCER_LIBRA/MIDNIGHT_BLUE/ altindaki her oranin en kucuk boyu onayli kapagin
     ust bolgesine (isim ve yazi disi) cok olcekli matchTemplate ile oturtulur; en yuksek NCC'li
     boy, olcek ve konum secilir (tahmin yok, olculur).
  2) CL: hat EMILY/JAMES uretir -> sablona yapistirilir -> NCC(aciklik, gri) >= 0.97, degilse DUR.
  3) ornek: ARIES_LEO, CAPRICORN_SAGITTARIUS, LEO_LEO -> 3000x2250 JPEG -> TEMP/POD_KAPAK_V3/ORNEK/.
--mod 77: kalan 77 cift, olculmus YER sabitiyle -> TEMP/POD_KAPAK_V3/77/ + tek sayfa onizleme.
"""
import argparse, base64, csv, json, subprocess, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KOK = Path(__file__).resolve().parents[2]
SABLON = KOK / 'data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg'
LISTE = KOK / 'data/pod/pod78_ids.csv'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
HEDEF = 'gdrive:ASTROLOVE/TEMP/POD_KAPAK_V3'
SIP_HEDEF = f'{HEDEF}/SIPARIS'            # siparis_dosyasi ciktisi buraya (TEMP/SIPARIS_ISIM'e dokunulmaz)
RENK = 'MIDNIGHT_BLUE'
ISIM = ('EMILY', 'JAMES'); MESAJ = 'It Began With a Kiss in the Rain'
REF = 'CANCER_LIBRA'
ORNEK = ('ARIES_LEO', 'CAPRICORN_SAGITTARIUS', 'LEO_LEO')
NCC_ESIK = 0.97
# Onayli kapakta poster acikligi (olculdu 27 Eyl: lacivert doluluk > %90 satir/sutun, egim yok).
# Koseler: SolUst (734,130)  SagUst (2267,130)  SagAlt (2267,2117)  SolAlt (734,2117). Yari acik kutu:
ACIKLIK = (734, 130, 2268, 2118)
# Yer olcumu icin ust bolge: aciklik ici, kenarlardan 60-120 px iceride (poster aciklik kenarina
# degmeyebilir), kucuk burc sembolleri (y 1396) ve isim/yazinin USTU. Buyuk sembol + daire burada.
UST = (800, 250, 2200, 1350)
# Oran -> en kucuk boy adaylari (siparis_dosyasi.BOY ile ayni anahtarlar)
ORAN_BOY = {'4x5': ('8x10', '16x20'), '3x4': ('12x16', '18x24', '30x40'), '11x14': ('11x14',),
            '2x3': ('24x36',), 'A': ('A4', 'A3', 'A2')}
YER = None   # --mod 77 icin: ornek kosusunun OLCUM.json degeri buraya sabitlenir

W = Path('_kapak').resolve(); W.mkdir(exist_ok=True)


def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def gri(a): return a.astype(np.float32).mean(2)


def ncc(a, b):
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def eta(i, n, ad):
    g = time.time() - T0; k = g / i * (n - i) if i else 0
    log(f'ETA {i}/{n} ({100 * i / n:.0f}%) gecen {g / 60:.1f} dk kalan {k / 60:.1f} dk | {ad}')


# ------------------------------------------------------------------ 1) yer olcumu
def yer_olc(C, P):
    """C: sablon gri (tam), P: poster gri (herhangi cozunurluk). Donus: poster kutusu sablon pikselinde."""
    x0, y0, x1, y1 = UST
    T = C[y0:y1, x0:x1]; Hp, Wp = P.shape; k = 4
    T4 = cv2.resize(T, (T.shape[1] // k, T.shape[0] // k), interpolation=cv2.INTER_AREA)
    kaba = None
    for pw in range(1400, 1801, 8):
        ph = round(pw * Hp / Wp)
        P4 = cv2.resize(P, (pw // k, ph // k), interpolation=cv2.INTER_AREA)
        if P4.shape[0] < T4.shape[0] or P4.shape[1] < T4.shape[1]:
            continue
        m = cv2.minMaxLoc(cv2.matchTemplate(P4, T4, cv2.TM_CCOEFF_NORMED))[1]
        if kaba is None or m > kaba[0]:
            kaba = (m, pw)
    if kaba is None:
        return None
    en = None
    for pw in range(kaba[1] - 8, kaba[1] + 9):
        ph = round(pw * Hp / Wp)
        Pr = cv2.resize(P, (pw, ph), interpolation=cv2.INTER_AREA)
        if Pr.shape[0] < T.shape[0] or Pr.shape[1] < T.shape[1]:
            continue
        _, m, _, loc = cv2.minMaxLoc(cv2.matchTemplate(Pr, T, cv2.TM_CCOEFF_NORMED))
        if en is None or m > en['ncc_ust']:
            en = {'ncc_ust': round(float(m), 5), 'w': pw, 'h': ph, 'x': x0 - loc[0], 'y': y0 - loc[1]}
    return en


def yer_bul(C):
    ls = rc('lsf', f'{POD}/{REF}/{RENK}').split()
    var = {f[:-4] for f in ls if f.endswith('.jpg')}
    adaylar = []
    for oran, boylar in ORAN_BOY.items():
        b = next((b for b in boylar if b in var), None)
        if b: adaylar.append((oran, b))
    log('POD_PRINT boylari', sorted(var), '| aday', adaylar)
    sonuc = []
    for oran, b in adaylar:
        yol = W / 'pod' / f'{b}.jpg'; yol.parent.mkdir(exist_ok=True)
        rc('copyto', f'{POD}/{REF}/{RENK}/{b}.jpg', str(yol))
        with Image.open(yol) as im:
            px = im.size; im.draft('RGB', (2400, 2400 * im.size[1] // im.size[0]))
            im = im.convert('RGB')
            if im.size[0] != 2400:
                im = im.resize((2400, round(2400 * px[1] / px[0])), Image.BOX)
            P = gri(np.asarray(im))
        r = yer_olc(C, P)
        log('yer', oran, b, px, r)
        if r: sonuc.append({'oran': oran, 'boy': b, 'kaynak_px': list(px), **r})
    if not sonuc:
        raise SystemExit('HATA: hicbir POD_PRINT boyu sablona oturmadi. DUR.')
    return max(sonuc, key=lambda r: r['ncc_ust']), sonuc


# ------------------------------------------------------------------ 2) hat + yapistirma
def hat(sb, cift, boy):
    """siparis_dosyasi.py (degistirilmeden) -> BASKI_<boy>.jpg yolu."""
    args = ['--cift', cift, '--renk', RENK, '--boy', boy, '--isim1', ISIM[0], '--isim2', ISIM[1],
            '--mesaj-b64', base64.b64encode(MESAJ.encode()).decode()]
    kod = ("import sys; sys.path.insert(0, 'scripts/medya_v1'); import siparis_dosyasi as s; "
           f"s.SIP = {SIP_HEDEF!r}; sys.argv = ['siparis_dosyasi.py'] + {args!r}; s.main()")
    subprocess.run([sys.executable, '-c', kod], cwd=sb, check=True)
    yol = Path(sb) / '_siparis' / f'{cift}_{RENK}_{boy}' / f'BASKI_{boy}.jpg'
    if not yol.exists():
        raise SystemExit(f'HATA: hat ciktisi yok: {yol}. DUR.')
    return yol


def yapistir(S, baski_yol, yer):
    with Image.open(baski_yol) as im:
        p = np.asarray(im.convert('RGB').resize((yer['w'], yer['h']), Image.LANCZOS))
    a = S.copy(); X0, Y0, X1, Y1 = ACIKLIK; x, y = yer['x'], yer['y']
    x0, y0 = max(X0, x), max(Y0, y); x1, y1 = min(X1, x + yer['w']), min(Y1, y + yer['h'])
    a[y0:y1, x0:x1] = p[y0 - y:y1 - y, x0 - x:x1 - x]          # cerceve ve duvar sablondan aynen
    kap = (x1 - x0) * (y1 - y0) / ((X1 - X0) * (Y1 - Y0))
    return a, round(kap, 4)


def kaydet(a, yol):
    Image.fromarray(a).save(yol, 'JPEG', quality=95, subsampling=0, optimize=True)


def kontrol_gorseli(S, K, yol):
    X0, Y0, X1, Y1 = ACIKLIK
    fark = np.clip(np.abs(S.astype(np.int16) - K.astype(np.int16)) * 4, 0, 255).astype(np.uint8)
    parca = [Image.fromarray(x[Y0:Y1, X0:X1]).resize((500, 647), Image.BOX) for x in (S, K, fark)]
    t = Image.new('RGB', (1500, 647)); [t.paste(p, (i * 500, 0)) for i, p in enumerate(parca)]
    t.save(yol, quality=90)


def onizleme(yollar, yol, sut=4, w=600):
    h = w * 3 // 4; n = len(yollar); sat = -(-n // sut)
    t = Image.new('RGB', (sut * w, sat * h), 'white')
    for i, p in enumerate(yollar):
        with Image.open(p) as im:
            t.paste(im.resize((w, h), Image.BOX), ((i % sut) * w, (i // sut) * h))
    t.save(yol, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mod', default='ornek', choices=('ornek', '77'))
    ap.add_argument('--sb', required=True, help='siparis-baski-v1 checkout dizini')
    a = ap.parse_args()
    S = np.asarray(Image.open(SABLON).convert('RGB'))
    assert S.shape[:2] == (2250, 3000), S.shape
    C = gri(S); X0, Y0, X1, Y1 = ACIKLIK
    cik = W / ('ORNEK' if a.mod == 'ornek' else '77'); cik.mkdir(exist_ok=True)
    R = {'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'mod': a.mod, 'aciklik': ACIKLIK,
         'koseler': {'sol_ust': [X0, Y0], 'sag_ust': [X1 - 1, Y0], 'sag_alt': [X1 - 1, Y1 - 1],
                     'sol_alt': [X0, Y1 - 1]}, 'isim': ISIM, 'mesaj': MESAJ, 'esik': NCC_ESIK}

    if a.mod == 'ornek':
        yer, adaylar = yer_bul(C)
        R['yer'] = yer; R['yer_adaylari'] = adaylar
        log('SECILEN yer', yer)
        cl = hat(a.sb, REF, yer['boy'])
        K, kap = yapistir(S, cl, yer)
        n_ac = ncc(C[Y0:Y1, X0:X1], gri(K)[Y0:Y1, X0:X1])
        n_yazi = ncc(C[1380:1900, X0:X1], gri(K)[1380:1900, X0:X1])
        mad = float(np.abs(S[Y0:Y1, X0:X1].astype(np.int16) - K[Y0:Y1, X0:X1].astype(np.int16)).mean())
        R['cl'] = {'ncc_aciklik': round(n_ac, 5), 'ncc_isim_yazi': round(n_yazi, 5),
                   'ort_mutlak_fark': round(mad, 2), 'kaplama': kap,
                   'gecti': n_ac >= NCC_ESIK}
        kaydet(K, cik / f'{REF}.jpg'); kontrol_gorseli(S, K, cik / 'CL_KONTROL_onayli_uretilen_fark.jpg')
        log('CL', R['cl'])
        (cik / 'OLCUM.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
        if not R['cl']['gecti']:
            rc('copy', str(cik), f'{HEDEF}/ORNEK')
            raise SystemExit(f'FAIL: CL NCC {n_ac:.4f} < {NCC_ESIK}. Ornek uretilmedi. DUR.')
        ciftler = list(ORNEK)
    else:
        if not YER:
            raise SystemExit('HATA: YER sabiti bos (ornek onayi sonrasi OLCUM.json degeri sabitlenir). DUR.')
        yer = YER; R['yer'] = yer
        with open(LISTE, newline='') as f:
            ciftler = [r['cift'] for r in csv.DictReader(f) if r['cift'] != REF]
        assert len(ciftler) == 77, len(ciftler)

    R['ciftler'] = []; yollar = []
    for i, c in enumerate(ciftler):
        eta(i, len(ciftler), c)
        K, kap = yapistir(S, hat(a.sb, c, yer['boy']), yer)
        yol = cik / f'{c}.jpg'; kaydet(K, yol); yollar.append(yol)
        # sabit alan kapisi: aciklik disi sablonla birebir (JPEG oncesi dizi)
        dis = S.copy(); dis[Y0:Y1, X0:X1] = K[Y0:Y1, X0:X1]
        R['ciftler'].append({'cift': c, 'kaplama': kap, 'boyut': list(Image.open(yol).size),
                             'aciklik_disi_ayni': bool((dis == K).all())})
        (cik / 'OLCUM.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
    eta(len(ciftler), len(ciftler), 'bitti')
    onizleme(([cik / f'{REF}.jpg'] if a.mod == 'ornek' else []) + yollar, cik / 'ONIZLEME.jpg')
    rc('copy', str(cik), f'{HEDEF}/{cik.name}')
    kotu = [x['cift'] for x in R['ciftler'] if x['boyut'] != [3000, 2250] or not x['aciklik_disi_ayni']]
    print(json.dumps({k: R.get(k) for k in ('yer', 'cl')}, ensure_ascii=False), flush=True)
    log('Cikti', f'TEMP/POD_KAPAK_V3/{cik.name}/', len(yollar), 'dosya | FAIL', kotu)
    if kotu:
        raise SystemExit(f'FAIL: {kotu}')


if __name__ == '__main__':
    main()
