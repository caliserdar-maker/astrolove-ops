#!/usr/bin/env python3
"""WP PLATE B (Serdar onayi 2 Eki, SECENEK A): Canva sayfa 45-78 ciftleri icin ikinci VINTAGE plate.

TANI 2/3 (kosu 37038496246, 37039856907): 78 ciftin onayli WARM_PARCHMENT kaynak kagidi iki grup. Sayfa 1-44 kagidi
VINTAGE_<boy> plate'i ile piksel piksel ayni (e_kagit ort 0.07-0.14); sayfa 45-78 kagidi ayni ortalama renk, farkli doku
(e_kagit ort 1.95-2.32, 5 boyda da sinir GEMINI_LEO | GEMINI_LIBRA). Mevcut plate 78 kaynagin piksel ortancasi oldugu
icin cogunluk (44) kagidina oturmus.

uret : plate B = VINTAGE_<boy> + ortanca(kaynak - VINTAGE) yalniz sayfa >= 45 ciftlerin MUREKKEP DISI piksellerinde
       (murekkep = wk.murekkep_maskesi(S - P, kenar=0), 9x9 genisletilmis). Murekkep yeri cifte gore degistigi icin
       bosluk dolar; 34 ciftin hepsinde murekkep olan piksel (ortak yazi) = VINTAGE degeri (fark 0; temizlenmis plate,
       iz yok). Bellek: kaynaklar /mnt'de uint8 memmap, ortanca satir karolarinda.
tara : 78 cift, uretimin kendi qc() fonksiyonu (wp_bakir.qc, ders 33) e_kagit + cift_boy'daki plate zemin_uyumu.
       Secilen plate (sayfa < 45 -> VINTAGE, >= 45 -> VINTAGE_B) + sayfa >= 45 icin eski plate (kapi hassas mi).
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

Image.MAX_IMAGE_PIXELS = None
SAYFA_B = 45                    # Canva sayfa 45-78 (GEMINI_LIBRA..VIRGO_VIRGO) -> plate B
GENIS = 9                       # murekkep maskesi genisletme (anti-alias kenari ortancaya girmesin)
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
    S0 = wk.dizi(kaynak(a.kok, grup[0][1], a.boy)); H, W = S0.shape[:2]; del S0
    P = plate_oku(a.plate, (W, H))
    tmp = Path(a.tmp); tmp.mkdir(parents=True, exist_ok=True)
    n = len(grup)
    D = np.lib.format.open_memmap(tmp / 'D.npy', 'w+', np.int8, (n, H, W, 3))    # S - P (int8), murekkep = -128
    bilgi = []
    for i, (no, c) in enumerate(grup):
        S = wk.dizi(kaynak(a.kok, c, a.boy))
        if S.shape[:2] != (H, W):
            raise SystemExit(f'HATA: {c} {S.shape[:2]} != {(H, W)}')
        d = S - P
        ink = cv2.dilate(wk.murekkep_maskesi(d, kenar=0).astype(np.uint8), np.ones((GENIS, GENIS), np.uint8)).astype(bool)
        di = np.rint(d)
        kirp = int((np.abs(di[~ink]) > 127).sum())                       # murekkep disi |fark| > 127 (beklenen 0)
        di = np.clip(di, -127, 127).astype(np.int8)
        di[ink] = -128
        D[i] = di
        bilgi.append({'cift': c, 'sayfa': no, 'murekkep_payi': round(float(ink.mean()), 4), 'kirpilan_px': kirp})
        del S, d, di, ink
        eta(i + 1, n, c)
    D.flush()
    B = np.empty((H, W, 3), np.uint8)
    bos = np.zeros((H, W), bool)
    gecerli_min = n
    T = max(16, int(2.5e8 // (n * W * 3 * 4)))
    for y in range(0, H, T):
        k = D[:, y:y + T].astype(np.float32)
        m = D[:, y:y + T, :, 0] == -128
        k[m] = np.nan
        with np.errstate(all='ignore'):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                med = np.nanmedian(k, axis=0)
        b = np.isnan(med[..., 0])
        bos[y:y + T] = b
        med[b] = 0.0                                                     # ortak yazi: VINTAGE degeri
        gecerli_min = min(gecerli_min, int((~m).sum(0)[~b].min()) if (~b).any() else gecerli_min)
        B[y:y + T] = np.clip(np.rint(P[y:y + T] + med), 0, 255).astype(np.uint8)
    del D
    (tmp / 'D.npy').unlink()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    ad = f'VINTAGE_B_{a.boy}.png'
    Image.fromarray(B).save(cik / ad, optimize=False, compress_level=6)
    ys, xs = np.nonzero(bos)
    fark = wk.dE(B.astype(np.float32), P)
    R = {'boy': a.boy, 'plate': ad, 'px': [W, H], 'cift_sayisi': n, 'ilk': grup[0][1], 'son': grup[-1][1],
         'yontem': 'VINTAGE + nanmedian(S - VINTAGE) murekkep disi (murekkep_maskesi kenar=0, genisletme 9)',
         'bos_px': int(bos.sum()), 'bos_kutu': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if bos.any() else None,
         'ortanca_min_ornek': gecerli_min,
         'B_vs_VINTAGE_dE': wk.ozet(fark), 'murekkep': bilgi, 'sure_sn': round(time.time() - T0, 1)}
    (cik / f'PLATE_B_{a.boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
    log('PLATE_B', json.dumps({x: R[x] for x in R if x != 'murekkep'}, ensure_ascii=False))


def e_kagit(P, S):
    """Uretimin qc() fonksiyonu (wp_bakir.qc), kagit = plate, murekkep cizgisi yok: e_kagit aynen uretimdeki tanim."""
    z = np.zeros(P.shape[:2], bool)
    return wb.qc(P, P, S, {'ce': z, 'core': z}, {}, z, {'rgb': list(wb.BAKIR_KOYU)})['e_kagit']


def zemin(P, S):
    """cift_boy plate kapisinin sayisal parcasi: wk.ozet(dE(P, S), murekkep disi) ort <= 0.5."""
    mk = wk.murekkep_maskesi(S - P, kenar=0)
    z = wk.ozet(wk.dE(P, S), ~mk)
    return {'ort': z.get('ort'), 'p99': z.get('p99'), 'gecti': bool(z.get('ort', 99) <= 0.5)}


def tara(a):
    tam = ciftler(a.kok, a.boy)
    S0 = wk.dizi(kaynak(a.kok, tam[0][1], a.boy)); H, W = S0.shape[:2]; del S0
    PA = plate_oku(a.plate, (W, H))
    PB = plate_oku(a.plate_b, (W, H))
    sat = []
    for i, (no, c) in enumerate(tam, 1):
        S = wk.dizi(kaynak(a.kok, c, a.boy))
        sec = 'B' if no >= SAYFA_B else 'VINTAGE'
        P = PB if sec == 'B' else PA
        r = {'cift': c, 'sayfa': no, 'boy': a.boy, 'plate': sec, 'e_kagit': e_kagit(P, S), 'zemin': zemin(P, S)}
        if sec == 'B':
            r['eski_plate'] = {'e_kagit': e_kagit(PA, S), 'zemin': zemin(PA, S)}
        r['gecti'] = bool(r['e_kagit']['gecti'] and r['zemin']['gecti'])
        sat.append(r)
        log('HUCRE', json.dumps(r, ensure_ascii=False))
        eta(i, len(tam), c)
        del S
    A = [r for r in sat if r['plate'] == 'VINTAGE']
    B = [r for r in sat if r['plate'] == 'B']
    o = {'boy': a.boy, 'hucre': len(sat), 'pass': sum(r['gecti'] for r in sat),
         'A44_eski_pass': sum(r['gecti'] for r in A), 'A_n': len(A),
         'B34_B_pass': sum(r['gecti'] for r in B), 'B_n': len(B),
         'B34_eski_fail': sum(not r['eski_plate']['e_kagit']['gecti'] for r in B),
         'B_ort_aralik': [min(r['e_kagit']['ort'] for r in B), max(r['e_kagit']['ort'] for r in B)],
         'B_eski_ort_aralik': [min(r['eski_plate']['e_kagit']['ort'] for r in B),
                               max(r['eski_plate']['e_kagit']['ort'] for r in B)],
         'sure_sn': round(time.time() - T0, 1)}
    o['iki_yon'] = bool(o['A44_eski_pass'] == o['A_n'] and o['B34_B_pass'] == o['B_n'] and o['B34_eski_fail'] == o['B_n'])
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    (cik / f'TARA_{a.boy}.json').write_text(json.dumps({'ozet': o, 'hucreler': sat}, ensure_ascii=False, indent=1))
    log('OZET', json.dumps(o, ensure_ascii=False))
    return 0 if o['pass'] == o['hucre'] and o['iki_yon'] else 1


def toplam(a):
    sat, oz = [], []
    for p in sorted(Path(a.kok).glob('**/TARA_*.json')):
        d = json.loads(p.read_text()); oz.append(d['ozet']); sat += d['hucreler']
    md = ['| cift | sayfa | ' + ' | '.join(o['boy'] for o in oz) + ' |', '|---|---|' + '---|' * len(oz)]
    for c in sorted({r['cift'] for r in sat}):
        rr = {r['boy']: r for r in sat if r['cift'] == c}
        h = [f"{rr[o['boy']]['plate'][0]} {rr[o['boy']]['e_kagit']['ort']}/{rr[o['boy']]['e_kagit']['p99']} "
             f"{'PASS' if rr[o['boy']]['gecti'] else 'FAIL'}" for o in oz if o['boy'] in rr]
        md.append(f"| {c} | {next(iter(rr.values()))['sayfa']} | " + ' | '.join(h) + ' |')
    T = {'hucre': sum(o['hucre'] for o in oz), 'pass': sum(o['pass'] for o in oz),
         'iki_yon': all(o['iki_yon'] for o in oz), 'boylar': oz}
    Path(a.cik).mkdir(parents=True, exist_ok=True)
    (Path(a.cik) / 'TARA_390.md').write_text('\n'.join(md) + '\n')
    (Path(a.cik) / 'TARA_390.json').write_text(json.dumps(T, ensure_ascii=False, indent=1))
    log('TOPLAM', json.dumps({x: T[x] for x in ('hucre', 'pass', 'iki_yon')}),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('is_', choices=('uret', 'tara', 'toplam', 'kesit'))
    ap.add_argument('--boy', default='11x14')
    ap.add_argument('--kok', default='')
    ap.add_argument('--plate', default='')
    ap.add_argument('--plate-b', default='')
    ap.add_argument('--tmp', default='/mnt/plate_b')
    ap.add_argument('--cik', required=True)
    ap.add_argument('--cift', default='PISCES_SCORPIO')
    ap.add_argument('--onayli', default='')
    ap.add_argument('--once', default='')
    ap.add_argument('--sonra', default='')
    a = ap.parse_args()
    r = {'uret': uret, 'tara': tara, 'toplam': toplam, 'kesit': kesit}[a.is_](a)
    sys.exit(r or 0)


if __name__ == '__main__':
    main()
