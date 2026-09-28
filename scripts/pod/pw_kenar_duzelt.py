#!/usr/bin/env python3
# DURUM 28 Eyl: 2 iterasyonda QC FAIL (kucuk sembol kenar orani 15-47 > 10, gorsel daha kotu); POD_PRINT e yazilmadi. KULLANMA.
"""PURE_WHITE kaynak (POD_PRINT/<CIFT>/PURE_WHITE/<BOY>.jpg): ana + kucuk sembol dis kenarindaki SIYAH karisimini temizler.
Neden (28 Eyl olcumu): kenar pikseli = t x yerel altin + (1-t) x SIYAH (artik ~2 seviye); dogrusu t x altin + (1-t) x BEYAZ.
Yontem:
  1 Bolge: 1/8 kucultmede murekkep bilesenleri; halka (genis ince bilesen) ve yildizlar (kucuk) atilir, kalanlar dikey
    bantlara toplanir: en buyuk alanli bant = ANA sembol, hemen altindaki bant = KUCUK semboller (isim/slogan dokunulmaz).
    Beklenen yapi yoksa dosya YAZILMAZ (FAIL).
  2 Duzeltme (yalniz iki bolge kutusunda, tam cozunurluk): zemine uzakligi <= 2.5 px murekkep pikseli c icin yerel altin G
    (3-8 px icerideki murekkebin ortalamasi), t = c.G / G.G; |c - tG| <= 18 ve c, beyaz karisimdan en az 8 L koyuysa
    c' = tG + (1-t) x 255. t (alfa) degismez -> sekil degismez.
  3 Yazma: kutular orijinal nicemleme tablolari + 4:4:4 ile JPEG'e, `jpegtran -drop` ile orijinale (kutu disi DCT
    bloklari bayt bayt ayni). EXIF/ICC/dpi korunur (-copy all).
QC (PASS/FAIL): her kutuda kenar orani (kaynak_kenar_tara.olc, goreli binde) sonra < 10; kutu disi piksel farki = 0;
  kutu icinde degistirilmeyen piksellerde yeniden nicemleme farki p99.9 <= 4.
Kullanim: pw_kenar_duzelt.py KOK CIKIS [--yaz]   (KOK/<CIFT>/PURE_WHITE/*.jpg; --yaz yoksa yalniz olc + onizleme)
Cikti: CIKIS/DUZELT.csv, CIKIS/duzeltilmis/<CIFT>/PURE_WHITE/<BOY>.jpg (yalniz PASS), CIKIS/ONCE_SONRA_<CIFT>.jpg (11x14)
"""
import argparse
import csv
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kaynak_kenar_tara import olc  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
ESIK_ORAN = 10.0
ESIK_REQ = 4


def bolgeler(im):
    """ANA ve KUCUK kutulari (tam cozunurluk, 8'e hizali). Yapi beklenmedikse ValueError."""
    k = 8
    s = np.asarray(im.reduce(k)).astype(np.float32)
    L = s @ LUMA
    ink = L < 235
    lab, n = ndi.label(ink)
    if not n:
        raise ValueError('murekkep yok')
    obj = ndi.find_objects(lab)
    alan = ndi.sum(ink, lab, range(1, n + 1))
    H, W = L.shape
    parca = []
    for i, o in enumerate(obj):
        h, w = o[0].stop - o[0].start, o[1].stop - o[1].start
        if alan[i] < 25:                                   # yildiz / toz
            continue
        if w > 0.55 * W and alan[i] < 0.08 * h * w:        # halka
            continue
        parca.append([o[0].start, o[0].stop, o[1].start, o[1].stop, alan[i]])
    parca.sort()
    bant = []
    for p in parca:                                        # dikey ortusme (+ %1.2 H pay) ile bant
        if bant and p[0] <= bant[-1][1] + 0.012 * H:
            b = bant[-1]
            b[1] = max(b[1], p[1]); b[2] = min(b[2], p[2]); b[3] = max(b[3], p[3]); b[4] += p[4]; b[5] += 1
        else:
            bant.append([p[0], p[1], p[2], p[3], p[4], 1])
    if len(bant) < 3:
        raise ValueError(f'bant sayisi {len(bant)}')
    ia = int(np.argmax([b[4] for b in bant]))
    if ia + 1 >= len(bant):
        raise ValueError('ana sembol altinda bant yok')
    out = {}
    for ad, b in (('ANA', bant[ia]), ('KUCUK', bant[ia + 1])):
        y0, y1, x0, x1 = b[0] * k - 16, b[1] * k + 16, b[2] * k - 16, b[3] * k + 16
        y0, x0 = max(0, y0 // 8 * 8), max(0, x0 // 8 * 8)
        y1, x1 = min(im.height, -(-y1 // 8) * 8), min(im.width, -(-x1 // 8) * 8)
        out[ad] = (x0, y0, x1, y1)
    kb = bant[ia + 1]
    if (kb[1] - kb[0]) * k > 0.12 * im.height:
        raise ValueError('kucuk sembol bandi beklenenden yuksek')
    return out


def duzelt(a):
    """a: HxWx3 float. Donus: yeni dizi, degisen maske.
    Yerel altin G = en yakin ic murekkep pikselinin (zemine 3-6 px) rengi; altin tonu hizla degistigi icin
    pencere ortalamasi yerine en yakin piksel (1. iterasyonda ortalama, artigi 27'ye cikariyordu)."""
    L = a @ LUMA
    bg = L >= 245
    ink = ~bg
    d = ndi.distance_transform_edt(ink)
    kenar = ink & (d <= 2.5)
    ic = ink & (d >= 3) & (d <= 6)
    if not ic.any():
        return a.copy(), np.zeros(L.shape, bool)
    uz, (iy, ix) = ndi.distance_transform_edt(~ic, return_indices=True)
    G = a[iy, ix]
    gecerli = uz <= 6
    gg = (G * G).sum(-1)
    t = np.clip((a * G).sum(-1) / np.maximum(gg, 1), 0, 1)
    tG = t[..., None] * G
    res = np.abs(a - tG).max(-1)
    beyaz = tG + (1 - t[..., None]) * 255.0
    koyu = L < (beyaz @ LUMA) - 8
    m = kenar & gecerli & (res <= 12 + 0.12 * tG.max(-1)) & (t < 0.97) & koyu
    b = a.copy()
    b[m] = beyaz[m]
    return b, m


def jpeg_drop(kaynak, cikis, parcalar, qt, dpi):
    """parcalar: [(x0,y0,PIL.Image)]. Orijinal tablolarla kodlayip jpegtran -drop ile yerlestirir."""
    gecici = [kaynak]
    with tempfile.TemporaryDirectory() as td:
        for j, (x0, y0, p) in enumerate(parcalar):
            dp = Path(td) / f'd{j}.jpg'
            p.save(dp, 'JPEG', qtables=qt, subsampling=0, dpi=dpi)
            yeni = Path(td) / f'o{j}.jpg'
            subprocess.run(['jpegtran', '-copy', 'all', '-drop', f'+{x0}+{y0}', str(dp), '-outfile', str(yeni),
                            str(gecici[-1])], check=True)
            gecici.append(yeni)
        Path(cikis).write_bytes(Path(gecici[-1]).read_bytes())


def isle(yol, cik_yol):
    im0 = Image.open(yol)
    qt, dpi = im0.quantization, im0.info.get('dpi', (300, 300))
    if JpegImagePlugin.get_sampling(im0) != 0:
        raise ValueError('4:4:4 degil')
    im = im0.convert('RGB')
    kut = bolgeler(im)
    sonuc, parcalar, once_sonra = {}, [], {}
    for ad, (x0, y0, x1, y1) in kut.items():
        a = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float32)
        b, m = duzelt(a)
        o1 = olc(a)[0]
        parcalar.append((x0, y0, Image.fromarray(np.clip(np.rint(b), 0, 255).astype(np.uint8))))
        sonuc[ad] = {'kutu': (x0, y0, x1, y1), 'once': o1, 'degisen_px': int(m.sum()), 'm': m}
    jpeg_drop(yol, cik_yol, parcalar, qt, dpi)
    im2 = Image.open(cik_yol).convert('RGB')
    A0, A2 = np.asarray(im).astype(np.int16), np.asarray(im2).astype(np.int16)
    dis = np.ones(A0.shape[:2], bool)
    for ad, r in sonuc.items():
        x0, y0, x1, y1 = r['kutu']
        dis[y0:y1, x0:x1] = False
        b2 = A2[y0:y1, x0:x1].astype(np.float32)
        r['sonra'] = olc(b2)[0]
        fark = np.abs(A2[y0:y1, x0:x1] - A0[y0:y1, x0:x1]).max(-1)
        Lk = (A0[y0:y1, x0:x1].astype(np.float32) @ LUMA) < 245
        uzak = ndi.distance_transform_edt(~Lk) > 8                  # murekkebe 8 px'ten uzak (beyaz bloklar)
        r['uzak_fark'] = int(fark[uzak].max()) if uzak.any() else 0
        dokunulmayan = ~ndi.binary_dilation(r['m'], iterations=1) & ~uzak
        r['req_p999'] = float(np.percentile(fark[dokunulmayan], 99.9)) if dokunulmayan.any() else 0.0
        once_sonra[ad] = (im.crop(r['kutu']), im2.crop(r['kutu']))
    dis_fark = int(np.abs(A2 - A0).max(-1)[dis].max()) if dis.any() else 0
    gecti = (dis_fark == 0 and all(r['sonra'] < ESIK_ORAN and r['uzak_fark'] == 0 and r['req_p999'] <= ESIK_REQ
                                   for r in sonuc.values()))
    return gecti, sonuc, dis_fark, once_sonra


def temas(cift, once_sonra, yol):
    try:
        F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    except OSError:
        F = ImageFont.load_default()
    satir = []
    for ad, (o, s) in once_sonra.items():
        # 3x: kutunun koyu kenarca en yogun 300x200 penceresi (once goruntusunden)
        a = np.asarray(o).astype(np.float32)
        L = a @ LUMA
        ink = L < 245
        kenar = ink & (ndi.distance_transform_edt(ink) <= 2.5) & (L < 150)
        yog = ndi.uniform_filter(kenar.astype(np.float32), size=(200, 300))
        y, x = np.unravel_index(np.argmax(yog), yog.shape)
        y0 = int(np.clip(y - 100, 0, max(a.shape[0] - 200, 0))); x0 = int(np.clip(x - 150, 0, max(a.shape[1] - 300, 0)))
        kt = (x0, y0, x0 + 300, y0 + 200)
        satir.append((ad, o.crop(kt).resize((900, 600), Image.LANCZOS), s.crop(kt).resize((900, 600), Image.LANCZOS)))
    T = Image.new('RGB', (1840, len(satir) * 660 + 10), (128, 128, 128))
    d = ImageDraw.Draw(T)
    for j, (ad, o, s) in enumerate(satir):
        y = j * 660 + 5
        d.text((10, y), f'{cift} {ad}  ONCE (sol) / SONRA (sag), 3x', fill=(255, 255, 255), font=F)
        T.paste(o, (10, y + 45)); T.paste(s, (930, y + 45))
    T.save(yol, quality=90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kok'); ap.add_argument('cikis')
    ap.add_argument('--ciftler', default='', help='virgulle; bos = hepsi')
    ap.add_argument('--parca', default='1/1', help='k/n: dosyalarin k. parcasi (paralel is icin)')
    a = ap.parse_args()
    kok, cik = Path(a.kok), Path(a.cikis)
    cik.mkdir(parents=True, exist_ok=True)
    sec = {c for c in a.ciftler.split(',') if c}
    dosyalar = sorted(p for p in kok.glob('*/PURE_WHITE/*.jpg') if not sec or p.parts[-3] in sec)
    k, n = (int(v) for v in a.parca.split('/'))
    dosyalar = dosyalar[k - 1::n]
    N = len(dosyalar)
    print(f'dosya: {N}', flush=True)
    t0 = time.time()
    sat = []
    for i, p in enumerate(dosyalar, 1):
        cift, boy = p.parts[-3], p.stem
        hedef = cik / 'duzeltilmis' / cift / 'PURE_WHITE' / p.name
        hedef.parent.mkdir(parents=True, exist_ok=True)
        try:
            gecti, s, dis, os_ = isle(p, hedef)
            r = {'cift': cift, 'boy': boy, 'sonuc': 'PASS' if gecti else 'FAIL', 'dis_fark': dis}
            for ad in ('ANA', 'KUCUK'):
                r.update({f'{ad}_once': s[ad]['once'], f'{ad}_sonra': s[ad]['sonra'], f'{ad}_degisen': s[ad]['degisen_px'],
                          f'{ad}_req_p999': s[ad]['req_p999'], f'{ad}_uzak_fark': s[ad]['uzak_fark']})
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
    alan = list(dict.fromkeys(k2 for r in sat for k2 in r))
    with open(cik / f'DUZELT_{k}of{n}.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(sat)
    ok = sum(r['sonuc'] == 'PASS' for r in sat)
    print(f'PASS {ok}/{N}')


if __name__ == '__main__':
    main()
