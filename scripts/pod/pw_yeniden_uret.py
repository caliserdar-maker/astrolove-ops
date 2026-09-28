#!/usr/bin/env python3
"""DURUM 28 Eyl: KULLANMA. 2 deneme QC FAIL (1: ana sembolde Voronoi kesikleri; 2: KUCUK binde 7.46 ama IoU 0.958).
POD_PRINT'e yazilmadi. Yalniz KUCUK icin 1. deneme yontemi binde <=1.04 verdi (IoU gercek 0.983-0.991).
PURE_WHITE POD_PRINT yeniden uretimi: ana + kucuk sembol kenari premultiplied alfa ile BEYAZA yeniden birlestirilir.
Kok neden (28 Eyl olcumu): PW masterda sembol kenari siyah matla birlesmis (kenar = t x altin + (1-t) x SIYAH).
Kaynak: ayni cift/boyun DEEP_BLACK dosyasi. DB zemini tam 0 (olculdu: ort 0, std 0.1) ve yerlesim PW ile ayni
(faz korelasyonu kayma 0,0) -> DB pikseli = a x altin (onceden carpilmis sembol). Alfa oradan TEK KAYNAKTAN alinir.
Renk PW'nin kendi ic pikselinden (kucuk sembolde PW altini DB'den ~16 seviye koyu; tonu korunur).
Yeniden kurulum (yalniz ANA ve KUCUK kutusunda, PW murekkebinin zemine < 2.5 px dis kenari):
  PW' = k (.) C_db + (1 - a) x 255; k = bolge PW/DB ic ton orani, a = C_db'nin en yakin DB ic pikseline izdusumu.
  (1. deneme: renk en yakin PW ic pikselinden -> ana sembol kenarinda Voronoi kesikleri; bu yuzden degisti.)
  Ic ve kutu disi DEGISMEZ.
Yazma: pw_kenar_duzelt.jpeg_drop (orijinal nicemleme tablolari, jpegtran -drop; kutu disi bayt bayt ayni).
QC (PASS/FAIL, her kutu): kenar orani (kaynak_kenar_tara.olc) < 10 binde; sekil IoU >= 0.99: yeni dosyanin sekli
  (esik = zemin ile ic altin arasi yari yol) ile GERCEK sembol (DB alfa >= 0.5). Eski dosyayla IoU bilgi olarak
  (iou_eski): eski sekle koyu halka 1 px ekler, ince kucuk sembolde bu tek basina ~0.92'ye dusurur; kutu disi fark 0 (isim/slogan/zemin); kutu icinde murekkebe > 12 px uzak piksel farki <= 2.
Kullanim: pw_yeniden_uret.py KOK CIKIS [--ciftler A,B] [--boylar 11x14] [--parca k/n]
  KOK/<CIFT>/{PURE_WHITE,DEEP_BLACK}/<BOY>.jpg -> CIKIS/yeni/<CIFT>/PURE_WHITE/<BOY>.jpg (yalniz PASS), URET_k.csv
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
ESIK_ORAN, ESIK_IOU, ESIK_UZAK = 10.0, 0.99, 2


def en_yakin(a, maske):
    _, (iy, ix) = ndi.distance_transform_edt(~maske, return_indices=True)
    return a[iy, ix]


def yeniden(pw, db):
    """pw, db: HxWx3 float (ayni kutu). Donus: yeni pw, degisen maske, gercek sekil (DB alfa >= 0.5).
    PW' = k (.) C_db + (1 - a) x 255: C_db onceden carpilmis sembol (piksel basina gercek renk + kabartma golgesi),
    k = bolge basina PW/DB ic ton orani (kucuk sembolde PW daha koyu), a = C_db'nin en yakin DB ic pikseline izdusumu.
    Bolme yok (gurultu buyumez). Serit: PW murekkebinin zemine < 2.5 px dis kenari (olculdu: ana sembolde >= 2.5 px
    PW == DB, fark ~1)."""
    Lp = pw @ LUMA
    ink_p = Lp < 245
    ink_d = (db @ LUMA) > 6
    dp = ndi.distance_transform_edt(ink_p)
    ic_p = ink_p & (dp >= 4)
    ic_d = ink_d & (ndi.distance_transform_edt(ink_d) >= 4)
    ortak = ic_p & ic_d
    if ortak.sum() < 50:
        raise ValueError('ic murekkep yok')
    k = np.median(pw[ortak], 0) / np.maximum(np.median(db[ortak], 0), 1)
    Gd = en_yakin(db, ic_d)
    a = np.clip((db * Gd).sum(-1) / np.maximum((Gd * Gd).sum(-1), 1), 0, 1)
    serit = ndi.binary_dilation(ink_p, iterations=2) & (dp < 2.5)
    yeni = pw.copy()
    yeni[serit] = (k * db + (1 - a[..., None]) * 255.0)[serit]
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


def isle(pw_yol, db_yol, cik_yol):
    im0 = Image.open(pw_yol)
    qt, dpi = im0.quantization, im0.info.get('dpi', (300, 300))
    if JpegImagePlugin.get_sampling(im0) != 0:
        raise ValueError('4:4:4 degil')
    im = im0.convert('RGB')
    dbi = Image.open(db_yol).convert('RGB')
    if dbi.size != im.size:
        raise ValueError(f'DB boyut {dbi.size} != PW {im.size}')
    kut = bolgeler(im)
    s, parcalar = {}, []
    for ad, k in kut.items():
        a = np.asarray(im.crop(k)).astype(np.float32)
        b = np.asarray(dbi.crop(k)).astype(np.float32)
        y, m, gercek = yeniden(a, b)
        parcalar.append((k[0], k[1], Image.fromarray(np.clip(np.rint(y), 0, 255).astype(np.uint8))))
        s[ad] = {'kutu': k, 'once': olc(a)[0], 'serit_px': int(m.sum()), 'gercek': gercek}
    jpeg_drop(pw_yol, cik_yol, parcalar, qt, dpi)
    im2 = Image.open(cik_yol).convert('RGB')
    A0, A2 = np.asarray(im).astype(np.int16), np.asarray(im2).astype(np.int16)
    dis = np.ones(A0.shape[:2], bool)
    os_ = {}
    for ad, r in s.items():
        x0, y0, x1, y1 = r['kutu']
        dis[y0:y1, x0:x1] = False
        a0 = A0[y0:y1, x0:x1].astype(np.float32); a2 = A2[y0:y1, x0:x1].astype(np.float32)
        r['sonra'] = olc(a2)[0]
        s0, s2 = sekil(a0), sekil(a2)
        g = r.pop('gercek')
        r['iou'] = round(float((s2 & g).sum() / max((s2 | g).sum(), 1)), 4)          # yeni vs gercek sembol (DB alfa>=0.5)
        r['iou_eski'] = round(float((s0 & s2).sum() / max((s0 | s2).sum(), 1)), 4)   # yeni vs eski (koyu halka dahil)
        r['iou_eski_gercek'] = round(float((s0 & g).sum() / max((s0 | g).sum(), 1)), 4)
        uzak = ndi.distance_transform_edt(~((a0 @ LUMA) < 245)) > 12
        r['uzak_fark'] = int(np.abs(a2 - a0).max(-1)[uzak].max()) if uzak.any() else 0
        os_[ad] = (im.crop(r['kutu']), im2.crop(r['kutu']))
    dis_fark = int(np.abs(A2 - A0).max(-1)[dis].max()) if dis.any() else 0
    gecti = dis_fark == 0 and all(r['sonra'] < ESIK_ORAN and r['iou'] >= ESIK_IOU and r['uzak_fark'] <= ESIK_UZAK
                                  for r in s.values())
    return gecti, s, dis_fark, os_


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kok'); ap.add_argument('cikis')
    ap.add_argument('--ciftler', default=''); ap.add_argument('--boylar', default='')
    ap.add_argument('--parca', default='1/1')
    a = ap.parse_args()
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
            gecti, s, dis, os_ = isle(p, p.parents[1] / 'DEEP_BLACK' / p.name, hedef)
            r = {'cift': cift, 'boy': boy, 'sonuc': 'PASS' if gecti else 'FAIL', 'dis_fark': dis}
            for ad in ('ANA', 'KUCUK'):
                r.update({f'{ad}_{x}': s[ad][x] for x in ('once', 'sonra', 'iou', 'iou_eski', 'iou_eski_gercek',
                                                            'uzak_fark', 'serit_px')})
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
