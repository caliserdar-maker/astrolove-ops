#!/usr/bin/env python3
"""WP PLATE B (Serdar onayi 2 Eki, SECENEK A): Canva sayfa 45-78 ciftleri icin ikinci VINTAGE plate.

TANI 2/3 (kosu 37038496246, 37039856907): 78 ciftin onayli WARM_PARCHMENT kaynak kagidi iki grup. Sayfa 1-44 kagidi
VINTAGE_<boy> plate'i ile piksel piksel ayni (e_kagit ort 0.07-0.14); sayfa 45-78 kagidi ayni ortalama renk, farkli doku
(e_kagit ort 1.95-2.32, 5 boyda da sinir GEMINI_LEO | GEMINI_LIBRA). Mevcut plate 78 kaynagin piksel ortancasi oldugu
icin cogunluk (44) kagidina oturmus.

uret : plate B = sayfa >= 45 ciftlerin MUREKKEP DISI piksel ortancasi. Murekkep grubun kendi kagidina gore aranir:
       B0 = ham ortanca (plate_uret yontemi), murekkep = wk.murekkep_maskesi(S - B0, kenar=0) | VINTAGE'e gore belirgin
       koyu, 9x9 genisletilmis. Murekkep yeri cifte gore degistigi icin bosluk dolar; 34 ciftin hepsinde murekkep olan
       piksel (ortak yazi) = VINTAGE degeri (temizlenmis plate, iz yok). Bellek: kaynaklar /mnt'de uint8 memmap,
       ortanca satir karolarinda.
tara : 78 cift x aday plate'ler, uretimin kendi qc() fonksiyonu (wp_bakir.qc, ders 33) e_kagit + cift_boy'daki plate
       zemin_uyumu. Secim = uretimin wo.plate_adi (sayfa < 45 VINTAGE; >= 45 plate B, 11x14'te alt kume B1/B2/B3).
       Iki yonlu: kendi plate'i PASS, diger her aday FAIL.
kume : (uret icinde, 11x14) 34 kaynagin kagidi cift cift dE matrisi + kumeleme -> wo.PLATE_B_11x14 kaniti.
kesit: PISCES_SCORPIO WP once (WP_REF adfb2b9) / sonra (plate B) 1:1, isim bandi; onayli kaynakla yan yana.
Kilitli kod / esik degismez. Drive'a yazmaz (workflow yazar)."""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_katman as wk                                           # noqa: E402
import wp_bakir as wb                                            # noqa: E402
import wp_ornek as wo                                            # noqa: E402 (plate_adi, PLATE_B_11x14)

Image.MAX_IMAGE_PIXELS = None
SAYFA_B = 45                    # Canva sayfa 45-78 (GEMINI_LIBRA..VIRGO_VIRGO) -> plate B
GENIS = 9                       # murekkep maskesi genisletme (anti-alias kenari ortancaya girmesin)
KOYU = 4 * wk.ESIK              # VINTAGE'e gore bu kadar koyu = murekkep (kagit doku farki ~ESIK, murekkep >> ESIK)
T0 = time.time()


def log(*a):
    print(*a, flush=True)


def eta(i, n, ad):
    g = time.time() - T0
    log(f'[{i}/{n}] {ad} | gecen {g:.0f}s | kalan ~{g / i * (n - i):.0f}s | %{100 * i // n}')


def ciftler(kok, boy):
    """Alfabetik = sayfa_no_tablosu (POD_PRINT klasor sirasi). 78 cift yoksa sayfa numarasi guvenilmez -> dur."""
    c = sorted(p.name for p in Path(kok).iterdir() if (p / 'WARM_PARCHMENT' / f'{boy}.jpg').exists())
    if len(c) != 78:
        raise SystemExit(f'HATA: {boy} icin {len(c)} cift (78 beklenir); sayfa numarasi kurulamaz')
    return [(i + 1, x) for i, x in enumerate(c)]


def kaynak(kok, c, boy):
    return Path(kok) / c / 'WARM_PARCHMENT' / f'{boy}.jpg'


def plate_oku(yol, wh):
    return wk.boyutla(wk.dizi(yol), wh)


def uret(a):
    tam = ciftler(a.kok, a.boy)
    grup = [(n, c) for n, c in tam if n >= SAYFA_B]
    if a.alt:                                                            # 11x14 alt kume plate'i (Serdar 2 Eki ek deneme)
        uye = wo.PLATE_B_11x14[a.alt]
        grup = [(n, c) for n, c in grup if c in uye]
        if len(grup) != len(uye):
            raise SystemExit(f'HATA: alt kume {a.alt}: {len(grup)} kaynak, tablo {len(uye)}')
    S0 = wk.dizi(kaynak(a.kok, grup[0][1], a.boy)); H, W = S0.shape[:2]; del S0
    P = plate_oku(a.plate, (W, H))
    Y = plate_oku(a.yedek, (W, H)) if a.yedek else P                     # tum ciftlerde murekkep olan piksel
    LP = P @ wk.LUMA
    tmp = Path(a.tmp); tmp.mkdir(parents=True, exist_ok=True)
    n = len(grup)
    S = np.lib.format.open_memmap(tmp / 'S.npy', 'w+', np.uint8, (n, H, W, 3))     # grup kaynaklari (uint8)
    for i, (no, c) in enumerate(grup):
        x = np.asarray(Image.open(kaynak(a.kok, c, a.boy)).convert('RGB'))
        if x.shape[:2] != (H, W):
            raise SystemExit(f'HATA: {c} {x.shape[:2]} != {(H, W)}')
        S[i] = x
        del x
        eta(i + 1, 3 * n, f'oku {c}')
    S.flush()
    T = max(16, int(2.5e8 // (n * W * 3 * 4)))
    # 1. gecis: grubun HAM ortancasi B0 (plate_uret yontemi). 1. deneme (37044638005) murekkebi VINTAGE'e gore
    # ariyordu: B kagidinin dokusu VINTAGE'den farkli oldugu icin doku farki her ciftte "murekkep" (pay 0.26) ->
    # sayfanin %23'u bos -> VINTAGE degeri -> zemin_uyumu 0.83-0.92. Murekkep artik grubun kendi kagidina gore.
    B0 = np.empty((H, W, 3), np.float32)
    for y in range(0, H, T):
        B0[y:y + T] = np.median(S[:, y:y + T], axis=0)
    # 2. gecis: murekkep = |S - B0| (murekkep_maskesi kenar=0) | VINTAGE'e gore belirgin koyu (cogunlukta murekkep
    # olan piksel B0'a girse bile dislanir), 9x9 genisletilmis
    K = np.lib.format.open_memmap(tmp / 'K.npy', 'w+', np.bool_, (n, H, W))
    bilgi = []
    for i, (no, c) in enumerate(grup):
        x = S[i].astype(np.float32)
        m = wk.murekkep_maskesi(x - B0, kenar=0) | (LP - x @ wk.LUMA > KOYU)
        K[i] = cv2.dilate(m.astype(np.uint8), np.ones((GENIS, GENIS), np.uint8)).astype(bool)
        bilgi.append({'cift': c, 'sayfa': no, 'murekkep_payi': round(float(K[i].mean()), 4),
                      'B0_dE_ort': round(float(wk.dE(x, B0)[~K[i]].mean()), 3)})
        del x, m
        eta(n + i + 1, 3 * n, f'maske {c}')
    K.flush()
    if not a.alt and a.boy in KUME_BOY:
        kume_kanit(a, S, K, grup, H, W)
    # 3. gecis: murekkep disi ortanca; tum ciftlerde murekkep (ortak yazi) = VINTAGE degeri (temizlenmis plate)
    B = np.empty((H, W, 3), np.uint8)
    bos = np.zeros((H, W), bool)
    gecerli_min = n
    for j, y in enumerate(range(0, H, T)):
        k = S[:, y:y + T].astype(np.float32)
        m = K[:, y:y + T]
        k[m] = np.nan
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            med = np.nanmedian(k, axis=0)
        b = np.isnan(med[..., 0])
        bos[y:y + T] = b
        med[b] = Y[y:y + T][b]
        if (~b).any():
            gecerli_min = min(gecerli_min, int((~m).sum(0)[~b].min()))
        B[y:y + T] = np.clip(np.rint(med), 0, 255).astype(np.uint8)
        del k, m
        eta(2 * n + min(n, (j + 1) * n * T // H), 3 * n, 'ortanca')
    del S, K
    (tmp / 'S.npy').unlink(); (tmp / 'K.npy').unlink()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    ek = f'B{a.alt}' if a.alt else 'B'
    ad = f'VINTAGE_{ek}_{a.boy}.png'
    Image.fromarray(B).save(cik / ad, optimize=False, compress_level=6)
    ys, xs = np.nonzero(bos)
    Bf = B.astype(np.float32)
    fark = wk.dE(Bf, P)
    iz = int((LP - Bf @ wk.LUMA > KOYU).sum())                                # plate B'de VINTAGE'e gore koyu iz (beklenen 0)
    R = {'boy': a.boy, 'plate': ad, 'px': [W, H], 'cift_sayisi': n, 'ilk': grup[0][1], 'son': grup[-1][1],
         'yontem': ('B0 = grup ham ortancasi; murekkep = murekkep_maskesi(S - B0, kenar=0) | (L_VINTAGE - L_S > '
                    f'{KOYU:g}), genisletme {GENIS}; plate = murekkep disi ortanca, tum ciftlerde murekkep = '
                    + (Path(a.yedek).name if a.yedek else 'VINTAGE')), 'alt_kume': a.alt, 'uyeler': [c for _, c in grup],
         'bos_px': int(bos.sum()), 'bos_pay': round(float(bos.mean()), 5),
         'bos_kutu': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if bos.any() else None,
         'ortanca_min_ornek': gecerli_min, 'koyu_iz_px': iz,
         'B_vs_VINTAGE_dE': wk.ozet(fark), 'murekkep': bilgi, 'sure_sn': round(time.time() - T0, 1)}
    (cik / f'PLATE_{ek}_{a.boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
    log('PLATE_' + ek, json.dumps({x: R[x] for x in R if x not in ('murekkep', 'uyeler')}, ensure_ascii=False))
    log('MUREKKEP_PAYI', min(x['murekkep_payi'] for x in bilgi), max(x['murekkep_payi'] for x in bilgi))


KUME_BOY = ('11x14',)
ORNEK_PX = 400000


def _ortalama_bag(D, k):
    """Ortalama baglantili hiyerarsik kumeleme (n kucuk): k kume kalana kadar en yakin iki kumeyi birlestir."""
    kum = [[i] for i in range(len(D))]
    while len(kum) > k:
        en = None
        for i in range(len(kum)):
            for j in range(i + 1, len(kum)):
                d = float(D[np.ix_(kum[i], kum[j])].mean())
                if en is None or d < en[0]:
                    en = (d, i, j)
        _, i, j = en
        kum[i] += kum.pop(j)
    return [sorted(x) for x in kum]


def kume_kanit(a, S, K, grup, H, W):
    """11x14 alt kume kaniti: 34 kaynagin kagidi cift cift, ORNEK_PX rastgele piksel (iki ciftte de murekkep disi),
    dE (uretimin lab'i) ort / p99 matrisi. Ortalama baglantili kumeleme (k=3) ve birini-disarida-birak en yakin kume
    wo.PLATE_B_11x14 tablosuyla karsilastirilir. Karar kapisi DEGIL (kapi tara'daki capraz plate testi); kanit."""
    n = len(grup)
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(H * W, min(ORNEK_PX, H * W), replace=False))
    L = np.empty((n, len(idx), 3), np.float32)
    ok = np.empty((n, len(idx)), bool)
    for i in range(n):
        L[i] = wk.lab(S[i].reshape(-1, 3)[idx][:, None, :].astype(np.float32))[:, 0]
        ok[i] = ~K[i].reshape(-1)[idx]
    ort = np.zeros((n, n), np.float32); p99 = np.zeros((n, n), np.float32)
    for i in range(n):
        for j in range(i + 1, n):
            m = ok[i] & ok[j]
            d = np.sqrt(((L[i, m] - L[j, m]) ** 2).sum(-1))
            ort[i, j] = ort[j, i] = d.mean(); p99[i, j] = p99[j, i] = np.percentile(d, 99)
    ad = [c for _, c in grup]
    tablo = {c: k for k, v in wo.PLATE_B_11x14.items() for c in v}
    kum = _ortalama_bag(p99, 3)
    bulunan = sorted(sorted(ad[i] for i in x) for x in kum)
    beklenen = sorted(sorted(c for c in ad if tablo[c] == k) for k in wo.PLATE_B_11x14)
    loo = {}
    for i, c in enumerate(ad):
        uz = {k: float(np.mean([p99[i, j] for j, d in enumerate(ad) if tablo[d] == k and j != i]))
              for k in wo.PLATE_B_11x14}
        loo[c] = {'tablo': tablo[c], 'en_yakin': min(uz, key=uz.get), 'p99_ort': {k: round(v, 2) for k, v in uz.items()}}
    blok = {}
    for k1 in wo.PLATE_B_11x14:
        for k2 in wo.PLATE_B_11x14:
            if k2 < k1:
                continue
            ii = [i for i, c in enumerate(ad) if tablo[c] == k1]; jj = [j for j, c in enumerate(ad) if tablo[c] == k2]
            v = [(ort[i, j], p99[i, j]) for i in ii for j in jj if i != j]
            blok[f'K{k1}-K{k2}'] = {'ort': [round(float(min(x[0] for x in v)), 2), round(float(max(x[0] for x in v)), 2)],
                                   'p99': [round(float(min(x[1] for x in v)), 2), round(float(max(x[1] for x in v)), 2)]}
    R = {'boy': a.boy, 'ornek_px': int(len(idx)), 'olcu': 'dE (wk.lab), iki kaynakta da murekkep disi pikseller',
         'kumeleme': 'ortalama baglanti, p99 uzakligi, k=3', 'bulunan': bulunan, 'tablo': beklenen,
         'eslesme': bulunan == beklenen,
         'loo_eslesme': sum(v['tablo'] == v['en_yakin'] for v in loo.values()), 'n': n,
         'blok': blok, 'loo': loo, 'ciftler': ad,
         'matris_ort': np.round(ort, 2).tolist(), 'matris_p99': np.round(p99, 2).tolist()}
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    (cik / f'KUME_{a.boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
    log('KUME', json.dumps({x: R[x] for x in ('boy', 'eslesme', 'loo_eslesme', 'n', 'blok')}, ensure_ascii=False))


def e_kagit(P, S):
    """Uretimin qc() fonksiyonu (wp_bakir.qc), kagit = plate, murekkep cizgisi yok: e_kagit aynen uretimdeki tanim."""
    z = np.zeros(P.shape[:2], bool)
    return wb.qc(P, P, S, {'ce': z, 'core': z}, {}, z, {'rgb': list(wb.BAKIR_KOYU)})['e_kagit']


def zemin(P, S):
    """cift_boy plate kapisinin sayisal parcasi: wk.ozet(dE(P, S), murekkep disi) ort <= 0.5."""
    mk = wk.murekkep_maskesi(S - P, kenar=0)
    z = wk.ozet(wk.dE(P, S), ~mk)
    return {'ort': z.get('ort'), 'p99': z.get('p99'), 'gecti': bool(z.get('ort', 99) <= 0.5)}


def adaylar(boy):
    if boy == '11x14':
        return ['VINTAGE_11x14.png'] + [f'VINTAGE_B{k}_11x14.png' for k in sorted(wo.PLATE_B_11x14)]
    return [f'VINTAGE_{boy}.png', f'VINTAGE_B_{boy}.png']


def kisa(ad, boy):
    x = ad[:-len(f'_{boy}.png')]
    return 'VINTAGE' if x == 'VINTAGE' else x[len('VINTAGE_'):]


def hucre(P, S):
    r = {'e_kagit': e_kagit(P, S), 'zemin': zemin(P, S)}
    r['gecti'] = bool(r['e_kagit']['gecti'] and r['zemin']['gecti'])
    return r


def _aralik(v):
    return [min(v), max(v)] if v else None


def tara(a):
    """78 cift x aday plate'ler. Secim = uretimin wo.plate_adi (siparis yolu). Kendi plate'i PASS, diger her aday
    plate FAIL olmali (iki yonlu test)."""
    tam = ciftler(a.kok, a.boy)
    S0 = wk.dizi(kaynak(a.kok, tam[0][1], a.boy)); H, W = S0.shape[:2]; del S0
    PL = {kisa(ad, a.boy): plate_oku(Path(a.plates) / ad, (W, H)) for ad in adaylar(a.boy)}
    sat = []
    for i, (no, c) in enumerate(tam, 1):
        S = wk.dizi(kaynak(a.kok, c, a.boy))
        sec = kisa(wo.plate_adi(c, no, a.boy), a.boy)
        r = {'cift': c, 'sayfa': no, 'boy': a.boy, 'plate': sec, **hucre(PL[sec], S)}
        r['yanlis'] = {k: hucre(P, S) for k, P in PL.items() if k != sec}
        if sec != 'VINTAGE':
            r['eski_plate'] = r['yanlis']['VINTAGE']
        sat.append(r)
        log('HUCRE', json.dumps(r, ensure_ascii=False))
        eta(i, len(tam), c)
        del S
    A = [r for r in sat if r['plate'] == 'VINTAGE']
    B = [r for r in sat if r['plate'] != 'VINTAGE']
    yl = [(r['cift'], r['plate'], k, v['gecti']) for r in sat for k, v in r['yanlis'].items()]
    o = {'boy': a.boy, 'hucre': len(sat), 'pass': sum(r['gecti'] for r in sat),
         'A44_eski_pass': sum(r['gecti'] for r in A), 'A_n': len(A),
         'B34_B_pass': sum(r['gecti'] for r in B), 'B_n': len(B),
         'B34_eski_fail': sum(not r['eski_plate']['gecti'] for r in B),
         'B_ort_aralik': _aralik([r['e_kagit']['ort'] for r in B]),
         'B_eski_ort_aralik': _aralik([r['eski_plate']['e_kagit']['ort'] for r in B]),
         'yanlis_n': len(yl), 'yanlis_fail': sum(not g for *_, g in yl),
         'yanlis_pass': [f'{c} {p}->{k}' for c, p, k, g in yl if g],
         'plate': {k: {'n': sum(r['plate'] == k for r in sat), 'pass': sum(r['gecti'] for r in sat if r['plate'] == k),
                       'e_ort': _aralik([r['e_kagit']['ort'] for r in sat if r['plate'] == k]),
                       'e_p99': _aralik([r['e_kagit']['p99'] for r in sat if r['plate'] == k]),
                       'zemin': _aralik([r['zemin']['ort'] for r in sat if r['plate'] == k])} for k in PL},
         'sure_sn': round(time.time() - T0, 1)}
    o['iki_yon'] = bool(o['pass'] == o['hucre'] and o['yanlis_fail'] == o['yanlis_n'])
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    (cik / f'TARA_{a.boy}.json').write_text(json.dumps({'ozet': o, 'hucreler': sat}, ensure_ascii=False, indent=1))
    log('OZET', json.dumps(o, ensure_ascii=False))
    return 0 if o['iki_yon'] else 1


def toplam(a):
    sat, oz = [], []
    for p in sorted(Path(a.kok).glob('**/TARA_*.json')):
        d = json.loads(p.read_text()); oz.append(d['ozet']); sat += d['hucreler']
    md = ['| cift | sayfa | ' + ' | '.join(o['boy'] for o in oz) + ' |', '|---|---|' + '---|' * len(oz)]
    for c in sorted({r['cift'] for r in sat}):
        rr = {r['boy']: r for r in sat if r['cift'] == c}
        h = [f"{rr[o['boy']]['plate']} {rr[o['boy']]['e_kagit']['ort']}/{rr[o['boy']]['e_kagit']['p99']} "
             f"{'PASS' if rr[o['boy']]['gecti'] else 'FAIL'}" for o in oz if o['boy'] in rr]
        md.append(f"| {c} | {next(iter(rr.values()))['sayfa']} | " + ' | '.join(h) + ' |')
    T = {'hucre': sum(o['hucre'] for o in oz), 'pass': sum(o['pass'] for o in oz),
         'iki_yon': all(o['iki_yon'] for o in oz), 'boylar': oz}
    T['yanlis_n'] = sum(o.get('yanlis_n', 0) for o in oz); T['yanlis_fail'] = sum(o.get('yanlis_fail', 0) for o in oz)
    Path(a.cik).mkdir(parents=True, exist_ok=True)
    (Path(a.cik) / 'TARA_390.md').write_text('\n'.join(md) + '\n')
    (Path(a.cik) / 'TARA_390.json').write_text(json.dumps(T, ensure_ascii=False, indent=1))
    log('TOPLAM', json.dumps({x: T[x] for x in ('hucre', 'pass', 'iki_yon', 'yanlis_n', 'yanlis_fail')}),
        json.dumps([{x: o[x] for x in ('boy', 'pass', 'hucre', 'A44_eski_pass', 'B34_B_pass', 'B34_eski_fail',
                                       'B_ort_aralik', 'B_eski_ort_aralik')} for o in oz]))
    return 0 if T['pass'] == T['hucre'] == 390 and T['iki_yon'] else 1


def kesit(a):
    """once/sonra BASKI + onayli kaynak, isim bandi 1:1 (RAPOR_<boy>.json bantlar)."""
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    c, boy = a.cift, a.boy
    S = np.asarray(Image.open(a.onayli).convert('RGB'))
    H, W = S.shape[:2]
    rap = {k: json.loads((Path(d) / f'RAPOR_{boy}.json').read_text()) for k, d in (('once', a.once), ('sonra', a.sonra))}
    et = rap['sonra'].get('bantlar') or rap['once'].get('bantlar') or {}
    y0, y1 = et.get('isim', [int(H * 0.70), int(H * 0.76)])
    y0, y1 = max(0, y0 - 120), min(H, y1 + 120)
    x0 = max(0, W // 2 - 600); x1 = min(W, x0 + 1200)
    parca = [('ONAYLI', S)]
    for k, d in (('ONCE_VINTAGE', a.once), ('SONRA_VINTAGE_B', a.sonra)):
        img = np.asarray(Image.open(Path(d) / f'WP_{c}_{boy}_BASKI.jpg').convert('RGB'))
        if img.shape[:2] != (H, W):
            raise SystemExit(f'HATA: {k} {img.shape[:2]} != {(H, W)}')
        parca.append((k, img))
    seri, sonuc = [], {'cift': c, 'boy': boy, 'pencere': {'x': [x0, x1], 'y': [y0, y1]}}
    for k, img in parca:
        p = img[y0:y1, x0:x1]
        Image.fromarray(p).save(cik / f'KESIT_{c}_{boy}_{k}_1e1.png')
        seri += [p, np.full((p.shape[0], 8, 3), 255, np.uint8)]
    Image.fromarray(np.concatenate(seri[:-1], 1)).save(cik / f'KESIT_{c}_{boy}_ONAYLI_ONCE_SONRA_1e1.png')
    for k in ('once', 'sonra'):
        r = rap[k]; q = r.get('qc') or {}
        sonuc[k] = {'durum': r.get('durum'), 'gecti': r.get('gecti'), 'plate': (r.get('plate') or {}).get('ad'),
                    'plate_gecti': r.get('plate_gecti'), 'zemin_uyumu': (r.get('plate') or {}).get('zemin_uyumu'),
                    'e_kagit': q.get('e_kagit'), 'qc_gecti': q.get('gecti'),
                    'kalan': sorted(g for g, v in q.items() if isinstance(v, dict) and v.get('gecti') is False)}
    (cik / f'KESIT_{c}_{boy}.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
    log('KESIT', json.dumps(sonuc, ensure_ascii=False, default=str))


def kesit_a(a):
    """KARAR A gorsel onay: onayli kaynak | yeni WP (uretim, en iyi / secili plate), 1:1.
    KAGIT: iki goruntude de murekkep yok (plate'e gore, 31 px genisletilmis), aralarindaki dE ortancasi en yuksek
    400 px pencere (fark en gorunur yer). Bantlar: RAPOR bantlar (isim, mesaj = tagline) +-120 satir, orta 1600 px."""
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    c, boy = a.cift, a.boy
    S = wk.dizi(a.onayli); H, W = S.shape[:2]
    O = wk.dizi(Path(a.sonra) / f'WP_{c}_{boy}_BASKI.jpg')
    P = plate_oku(a.plates, (W, H))
    rap = json.loads((Path(a.sonra) / f'RAPOR_{boy}.json').read_text())
    if O.shape[:2] != (H, W):
        raise SystemExit(f'HATA: WP {O.shape[:2]} != {(H, W)}')
    ink = wk.murekkep_maskesi(S - P, kenar=0) | wk.murekkep_maskesi(O - P, kenar=0)
    ink = cv2.dilate(ink.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    d = wk.dE(S, O)
    ii = cv2.integral(ink.astype(np.uint8))
    en, n = None, 400
    for y in range(0, H - n + 1, n // 4):
        for x in range(0, W - n + 1, n // 4):
            if ii[y + n, x + n] - ii[y, x + n] - ii[y + n, x] + ii[y, x]:
                continue
            v = float(np.median(d[y:y + n, x:x + n]))
            if en is None or v > en[0]:
                en = (v, x, y)
    plate_ad = (rap.get('plate') or {}).get('ad')
    q = rap.get('qc') or {}
    R = {'cift': c, 'boy': boy, 'plate': plate_ad, 'isim': a.isim, 'mesaj': a.mesaj, 'durum': rap.get('durum'),
         'gecti': rap.get('gecti'), 'plate_gecti': rap.get('plate_gecti'),
         'zemin_uyumu': (rap.get('plate') or {}).get('zemin_uyumu'), 'e_kagit': q.get('e_kagit'),
         'qc_kalan': sorted(g for g, v in q.items() if isinstance(v, dict) and v.get('gecti') is False), 'kesitler': {}}
    def yaz(ad, sl, yon):
        A_, B_ = np.clip(S[sl], 0, 255).astype(np.uint8), np.clip(O[sl], 0, 255).astype(np.uint8)
        Image.fromarray(A_).save(cik / f'KESIT_{c}_{boy}_{ad}_ONAYLI_1e1.png')
        Image.fromarray(B_).save(cik / f'KESIT_{c}_{boy}_{ad}_WP_1e1.png')
        ara = np.full((8, A_.shape[1], 3) if yon == 0 else (A_.shape[0], 8, 3), 255, np.uint8)
        Image.fromarray(np.concatenate([A_, ara, B_], yon)).save(cik / f'KESIT_{c}_{boy}_{ad}_ONAYLI_WP_1e1.png')
        dd = wk.dE(S[sl], O[sl])
        R['kesitler'][ad] = {'y': [sl[0].start, sl[0].stop], 'x': [sl[1].start, sl[1].stop],
                             'dE_ort': round(float(dd.mean()), 2), 'dE_p99': round(float(np.percentile(dd, 99)), 2)}
    if en is not None:
        _, x0, y0 = en
        yaz('KAGIT', (slice(y0, y0 + n), slice(x0, x0 + n)), 1)
    else:
        R['kesitler']['KAGIT'] = 'murekkepsiz pencere yok'
    et = rap.get('bantlar') or {}
    x0 = max(0, W // 2 - 800); x1 = min(W, x0 + 1600)
    for b in ('isim', 'mesaj'):
        if b in et:
            y0, y1 = et[b]
            yaz(b.upper(), (slice(max(0, y0 - 120), min(H, y1 + 120)), slice(x0, x1)), 0)
    (cik / f'KESIT_{c}_{boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    log('KESIT_A', json.dumps(R, ensure_ascii=False, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('is_', choices=('uret', 'tara', 'toplam', 'kesit', 'kesit_a'))
    ap.add_argument('--boy', default='11x14')
    ap.add_argument('--kok', default='')
    ap.add_argument('--plate', default='')
    ap.add_argument('--plates', default='', help='tara: aday plate klasoru (VINTAGE_<boy>.png, VINTAGE_B*_<boy>.png)')
    ap.add_argument('--alt', type=int, default=0, help='uret: 11x14 alt kume (1/2/3, wo.PLATE_B_11x14)')
    ap.add_argument('--yedek', default='', help='uret: tum ciftlerde murekkep olan piksel icin plate (vars. VINTAGE)')
    ap.add_argument('--tmp', default='/mnt/plate_b')
    ap.add_argument('--cik', required=True)
    ap.add_argument('--cift', default='PISCES_SCORPIO')
    ap.add_argument('--onayli', default='')
    ap.add_argument('--once', default='')
    ap.add_argument('--sonra', default='')
    ap.add_argument('--isim', default='')
    ap.add_argument('--mesaj', default='')
    a = ap.parse_args()
    r = {'uret': uret, 'tara': tara, 'toplam': toplam, 'kesit': kesit, 'kesit_a': kesit_a}[a.is_](a)
    sys.exit(r or 0)


if __name__ == '__main__':
    main()
