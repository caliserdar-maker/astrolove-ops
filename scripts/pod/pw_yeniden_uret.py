#!/usr/bin/env python3
"""PURE_WHITE POD_PRINT: KUCUK sembol kenari DB alfasi ile BEYAZA yeniden birlestirilir (Serdar karari 28 Eyl, secenek b).
Kok neden (28 Eyl olcumu): PW masterda sembol kenari siyah matla birlesmis (kenar = t x altin + (1-t) x SIYAH).
Alfa kaynagi: ayni cift/boyun DEEP_BLACK dosyasi (zemin tam 0, yerlesim PW ile ayni -> DB pikseli = a x altin).
Yontem (1. deneme yontemi, YALNIZ KUCUK kutusu; ANA sembol ve kutu disi DOKUNULMAZ):
  a = C_db'nin en yakin DB ic pikseline izdusumu; renk G = en yakin PW ic pikseli (PW tonu korunur);
  serit (PW murekkebi 2 px genisletilmis & birlesik murekkebe < 4 px): PW' = a x G + (1 - a) x 255.
  ANA sembolde bu yontem Voronoi kesikleri verdi (28 Eyl 1. deneme); ana sembol Canva seffaf disa aktarimini bekler (acik is).
Yazma: pw_kenar_duzelt.jpeg_drop (orijinal nicemleme tablolari, jpegtran -drop; kutu disi bayt bayt ayni).
QC (PASS/FAIL, KUCUK kutusu): kenar orani (kaynak_kenar_tara.olc) < 10 binde; sekil IoU >= 0.98 (yeni dosyanin sekli,
  esik = zemin ile ic altin arasi yari yol, ile GERCEK sembol = DB alfa >= 0.5); kutu disi fark 0 (ANA, isim, slogan,
  zemin); kutu icinde murekkebe > 12 px uzak piksel farki <= 2 (yeniden nicemleme).
Kullanim: pw_yeniden_uret.py KOK CIKIS [--ciftler A,B] [--boylar 11x14] [--parca k/n]
  KOK/<CIFT>/{PURE_WHITE,DEEP_BLACK}/<BOY>.jpg -> CIKIS/yeni/<CIFT>/PURE_WHITE/<BOY>.jpg (yalniz PASS), URET_k.csv
          pw_yeniden_uret.py --ozet CIKIS --boy-sayisi 15
  URET_*.csv -> YAZ.txt (15 boyu da PASS olan ciftler), OZET.md (FAIL ciftler + neden)
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kaynak_kenar_tara import olc  # noqa: E402
from pw_kenar_duzelt import bolgeler, jpeg_drop, LUMA  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ESIK_ORAN, ESIK_IOU, ESIK_UZAK = 10.0, 0.98, 2


def en_yakin(a, maske):
    _, (iy, ix) = ndi.distance_transform_edt(~maske, return_indices=True)
    return a[iy, ix]


def yeniden(pw, db):
    """pw, db: HxWx3 float (ayni KUCUK kutusu). Donus: yeni pw, degisen maske, gercek sekil (DB alfa >= 0.5)."""
    Lp = pw @ LUMA
    ink_p = Lp < 245
    ink_d = (db @ LUMA) > 6
    d = ndi.distance_transform_edt(ink_p | ink_d)
    ic_p = ink_p & (ndi.distance_transform_edt(ink_p) >= 4)
    ic_d = ink_d & (ndi.distance_transform_edt(ink_d) >= 4)
    if ic_p.sum() < 50 or ic_d.sum() < 50:
        raise ValueError('ic murekkep yok')
    Gd = en_yakin(db, ic_d)
    Gp = en_yakin(pw, ic_p)
    a = np.clip((db * Gd).sum(-1) / np.maximum((Gd * Gd).sum(-1), 1), 0, 1)
    serit = ndi.binary_dilation(ink_p, iterations=2) & (d < 4)
    yeni = pw.copy()
    yeni[serit] = (a[..., None] * Gp + (1 - a[..., None]) * 255.0)[serit]
    return yeni, serit, a >= 0.5


def sekil(a):
    """Zemin (255) ile yerel ic altin arasi yari yol esigiyle sekil maskesi."""
    L = a @ LUMA
    ink = L < 245
    ic = ink & (ndi.distance_transform_edt(ink) >= 4)
    if not ic.any():
        return ink
    Lg = en_yakin(L[..., None], ic)[..., 0]
    return L < (255 + Lg) / 2


def dis_fark(A, B, kutu, adim=512):
    """Kutu disinda en buyuk piksel farki (bellek icin satir parcalari)."""
    x0, y0, x1, y1 = kutu
    m = 0
    for r in range(0, A.shape[0], adim):
        d = np.abs(A[r:r + adim].astype(np.int16) - B[r:r + adim].astype(np.int16)).max(-1)
        rr0, rr1 = max(y0 - r, 0), min(y1 - r, d.shape[0])
        if rr0 < rr1:
            d[rr0:rr1, x0:x1] = 0
        m = max(m, int(d.max()))
    return m


def isle(pw_yol, db_yol, cik_yol):
    im0 = Image.open(pw_yol)
    qt, dpi = im0.quantization, im0.info.get('dpi', (300, 300))
    if JpegImagePlugin.get_sampling(im0) != 0:
        raise ValueError('4:4:4 degil')
    im = im0.convert('RGB')
    dbi = Image.open(db_yol).convert('RGB')
    if dbi.size != im.size:
        raise ValueError(f'DB boyut {dbi.size} != PW {im.size}')
    k = bolgeler(im)['KUCUK']
    a0 = np.asarray(im.crop(k)).astype(np.float32)
    y, m, g = yeniden(a0, np.asarray(dbi.crop(k)).astype(np.float32))
    del dbi
    jpeg_drop(pw_yol, cik_yol, [(k[0], k[1], Image.fromarray(np.clip(np.rint(y), 0, 255).astype(np.uint8)))], qt, dpi)
    im2 = Image.open(cik_yol).convert('RGB')
    if im2.size != im.size:
        raise ValueError('cikis boyutu farkli')
    a2 = np.asarray(im2.crop(k)).astype(np.float32)
    s0, s2 = sekil(a0), sekil(a2)
    uzak = ndi.distance_transform_edt(~((a0 @ LUMA) < 245)) > 12
    r = {'kutu': 'x'.join(map(str, k)), 'once': olc(a0)[0], 'sonra': olc(a2)[0],
         'iou': round(float((s2 & g).sum() / max((s2 | g).sum(), 1)), 4),              # yeni vs gercek (DB alfa>=0.5)
         'iou_eski_gercek': round(float((s0 & g).sum() / max((s0 | g).sum(), 1)), 4),  # eski vs gercek (bilgi)
         'uzak_fark': int(np.abs(a2 - a0).max(-1)[uzak].max()) if uzak.any() else 0,
         'serit_px': int(m.sum()),
         'dis_fark': dis_fark(np.asarray(im), np.asarray(im2), k)}
    gecti = (r['dis_fark'] == 0 and r['sonra'] < ESIK_ORAN and r['iou'] >= ESIK_IOU and r['uzak_fark'] <= ESIK_UZAK)
    return gecti, r, {'KUCUK': (im.crop(k), im2.crop(k))}


def temas(cift, os_, yol):
    try:
        F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    except OSError:
        F = ImageFont.load_default()
    satir = []
    for ad, (o, y) in os_.items():
        a = np.asarray(o).astype(np.float32)
        L = a @ LUMA
        ink = L < 245
        kenar = ink & (ndi.distance_transform_edt(ink) <= 2.5) & (L < 150)
        yog = ndi.uniform_filter(kenar.astype(np.float32), size=(200, 300))
        cy, cx = np.unravel_index(np.argmax(yog), yog.shape)
        y0 = int(np.clip(cy - 100, 0, max(a.shape[0] - 200, 0))); x0 = int(np.clip(cx - 150, 0, max(a.shape[1] - 300, 0)))
        k = (x0, y0, x0 + 300, y0 + 200)
        satir.append((ad, o.crop(k).resize((900, 600), Image.LANCZOS), y.crop(k).resize((900, 600), Image.LANCZOS)))
    T = Image.new('RGB', (1840, len(satir) * 660 + 10), (128, 128, 128))
    d = ImageDraw.Draw(T)
    for j, (ad, o, y) in enumerate(satir):
        yy = j * 660 + 5
        d.text((10, yy), f'{cift} {ad}  ONCE (sol) / SONRA (sag), 3x', fill=(255, 255, 255), font=F)
        T.paste(o, (10, yy + 45)); T.paste(y, (930, yy + 45))
    T.save(yol, quality=90)


def ozet(cik, boy_sayisi):
    """URET_*.csv -> YAZ.txt (tum boylari PASS ciftler) + OZET.md. Cift duzeyinde: tek boy FAIL ise cift atlanir."""
    sat = [r for f in sorted(cik.glob('URET_*.csv')) for r in csv.DictReader(open(f))]
    ciftler = sorted({r['cift'] for r in sat})
    yaz, fail = [], []
    for c in ciftler:
        rs = [r for r in sat if r['cift'] == c]
        kotu = [r for r in rs if r['sonuc'] != 'PASS']
        if not kotu and len(rs) == boy_sayisi:
            yaz.append(c)
        else:
            neden = '; '.join(f"{r['boy']}: {r.get('hata') or 'sonra %s iou %s dis %s uzak %s' % (r.get('sonra'), r.get('iou'), r.get('dis_fark'), r.get('uzak_fark'))}"
                              for r in kotu) or f'boy sayisi {len(rs)} != {boy_sayisi}'
            fail.append((c, neden))
    (cik / 'YAZ.txt').write_text(''.join(c + '\n' for c in yaz))
    ps = [r for r in sat if r['sonuc'] == 'PASS']
    f = lambda k: np.array([float(r[k]) for r in ps]) if ps else np.zeros(1)          # noqa: E731
    md = [f'PW kucuk sembol yeniden birlestirme: {len(yaz)}/{len(ciftler)} cift PASS (15 boyun hepsi), {len(fail)} cift FAIL (atlandi).', '',
          f'- dosya: {len(sat)}, PASS {len(ps)}',
          f"- KUCUK kenar binde once medyan {np.median(f('once')):.2f} / sonra medyan {np.median(f('sonra')):.2f}, en cok {f('sonra').max():.2f} (esik < 10)",
          f"- IoU (gercek sekil) en az {f('iou').min():.4f} (esik >= 0.98); kutu disi fark en cok {f('dis_fark').max():.0f}; uzak fark en cok {f('uzak_fark').max():.0f}",
          '', '## FAIL ciftler', ''] + [f'- {c}: {n}' for c, n in fail] + ([] if fail else ['- yok'])
    (cik / 'OZET.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kok', nargs='?'); ap.add_argument('cikis', nargs='?')
    ap.add_argument('--ciftler', default=''); ap.add_argument('--boylar', default='')
    ap.add_argument('--parca', default='1/1')
    ap.add_argument('--ozet', default=''); ap.add_argument('--boy-sayisi', type=int, default=15)
    a = ap.parse_args()
    if a.ozet:
        return ozet(Path(a.ozet), a.boy_sayisi)
    kok, cik = Path(a.kok), Path(a.cikis)
    cik.mkdir(parents=True, exist_ok=True)
    sc = {c for c in a.ciftler.split(',') if c}
    sb = {b for b in a.boylar.split(',') if b}
    dos = sorted(p for p in kok.glob('*/PURE_WHITE/*.jpg')
                 if (not sc or p.parts[-3] in sc) and (not sb or p.stem in sb))
    k, n = (int(v) for v in a.parca.split('/'))
    dos = dos[k - 1::n]
    N = len(dos)
    print(f'dosya: {N}', flush=True)
    t0 = time.time()
    sat = []
    for i, p in enumerate(dos, 1):
        cift, boy = p.parts[-3], p.stem
        hedef = cik / 'yeni' / cift / 'PURE_WHITE' / p.name
        hedef.parent.mkdir(parents=True, exist_ok=True)
        try:
            gecti, s, os_ = isle(p, p.parents[1] / 'DEEP_BLACK' / p.name, hedef)
            r = {'cift': cift, 'boy': boy, 'sonuc': 'PASS' if gecti else 'FAIL', **s}
            if boy == '11x14':
                temas(cift, os_, cik / f'ONCE_SONRA_{cift}.jpg')
            if not gecti:
                hedef.unlink()
        except Exception as e:                                           # noqa: BLE001
            r = {'cift': cift, 'boy': boy, 'sonuc': 'FAIL', 'hata': f'{type(e).__name__}: {e}'}
            hedef.unlink(missing_ok=True)
        sat.append(r)
        g = time.time() - t0
        print(f"[{i}/{N}] {cift} {boy} {r['sonuc']} {r.get('hata', '')} | gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s "
              f"| %{i / N * 100:.0f}", flush=True)
    alan = list(dict.fromkeys(x for r in sat for x in r))
    with open(cik / f'URET_{k}of{n}.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(sat)
    print(f"PASS {sum(r['sonuc'] == 'PASS' for r in sat)}/{N}")


if __name__ == '__main__':
    main()
