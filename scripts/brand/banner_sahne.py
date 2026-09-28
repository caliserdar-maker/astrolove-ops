#!/usr/bin/env python3
"""Etsy magaza banner'i (3360x840): ChatGPT sahnesi A + GERCEK hattan posterler.

Adimlar (28 Eyl 2026, Serdar karari "A ile devam"):
  buyut      A (2000x667, 3:1) ortadan 4:1 kirpilir (ust 83, alt 84 px; B 4:1 gelir, kirpilmaz), Real-ESRGAN
             x2plus ile 4000x1000'e buyutulur, Lanczos ile 3360x840'a indirilir.
  yerlestir  3360x840 taban uzerinde beyaz cerceve acikliklari OLCULUR, posterler
             (siparis-baski-v1 BASKI_12x16.jpg, 3:4) esnetmeden acikliga oturtulur,
             sahnenin isik yonune gore (--isik) hafif ic golge verilir. Golge yalniz kenar
             bandindadir; merkez bolgede poster pikselleri birebir korunur.
QC (PASS/FAIL): taban 3360x840; poster oran farki < %1.5 (AI cizimi aciklik, pervaz dahil
0.752-0.758; 3:4'ten sapma); kirpilan poster kenari toplam <= 8 px (kenar basina ~4 px); merkez bolge dE76 maks < 1; aciklik cevresinde beyaz dikis pikseli = 0.
Etsy'ye yukleme YOK.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 3360, 840
UST, ALT = 83, 84                     # 2000x667 kaynakta 4:1 orta kirpim


def buyut(kaynak, model_yol, cik):
    import torch
    from spandrel import ModelLoader
    im = Image.open(kaynak).convert('RGB')
    w, h = im.size
    # A (3:1) ortadan 4:1 kirpilir; B zaten 4:1 gelir, kirpilmaz
    kir = im if w == 4 * h else im.crop((0, UST, w, h - ALT))
    assert kir.size[0] == 4 * kir.size[1], kir.size
    m = ModelLoader().load_from_file(model_yol).eval()
    x = torch.from_numpy(np.asarray(kir, np.float32) / 255).permute(2, 0, 1)[None]
    parca, bindir, satirlar = 256, 16, []
    _, _, th, tw = x.shape
    s = m.scale
    out = torch.zeros(1, 3, th * s, tw * s)
    toplam = ((th + parca - 1) // parca) * ((tw + parca - 1) // parca); n = 0
    with torch.no_grad():
        for y0 in range(0, th, parca):
            for x0 in range(0, tw, parca):
                ya, xa = max(y0 - bindir, 0), max(x0 - bindir, 0)
                yb, xb = min(y0 + parca + bindir, th), min(x0 + parca + bindir, tw)
                o = m(x[:, :, ya:yb, xa:xb]).clamp(0, 1)
                y1, x1 = min(y0 + parca, th), min(x0 + parca, tw)
                out[:, :, y0 * s:y1 * s, x0 * s:x1 * s] = \
                    o[:, :, (y0 - ya) * s:(y1 - ya) * s, (x0 - xa) * s:(x1 - xa) * s]
                n += 1
                print(f'\r  ESRGAN parca {n}/{toplam} %{n * 100 // toplam}', end='', flush=True)
    print()
    b = Image.fromarray((out[0].permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8))
    b = b.resize((W, H), Image.LANCZOS)
    b.save(cik)
    print('taban', b.size, '->', cik)


def notr_acik(a, alt=150, doygunluk=24):
    ai = a.astype(np.int16)
    return (ai.min(axis=2) > alt) & ((ai.max(axis=2) - ai.min(axis=2)) < doygunluk)


def acikliklar(a, esik=238, doygunluk=12, pay=20):
    """Beyaz acikliklar (notr ve cok acik): en buyuk iki bilesen (soldan saga).
    Duvar krem tonludur (doygunluk > 12), acikliklar notr beyazdir. Cekirdek, cerceve
    ic pervazindaki gri golge seridini de alacak sekilde notr-acik piksellere buyutulur
    (altin cerceve doygun oldugu icin buyume orada durur)."""
    from scipy import ndimage
    ai = a.astype(np.int16)
    beyaz = (ai.min(axis=2) > esik) & ((ai.max(axis=2) - ai.min(axis=2)) < doygunluk)
    lab, _ = ndimage.label(ndimage.binary_opening(beyaz, iterations=2))
    aday = notr_acik(a)
    kutu = []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if h * w <= 50000:
            continue
        y0, y1 = max(s[0].start - pay, 0), s[0].stop + pay
        x0, x1 = max(s[1].start - pay, 0), s[1].stop + pay
        tohum = lab[y0:y1, x0:x1] == i
        b = ndimage.binary_propagation(tohum, mask=aday[y0:y1, x0:x1] | tohum)
        ys, xs = np.nonzero(b)
        kutu.append((int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1)))
    return sorted(kutu)[:2]


def ic_golge(w, h, ust=0.16, sol=0.11, sag=0.035, alt=0.045, sigma=7.0):
    """Carpim maskesi (1 = degismez). Isik sol-ustten: cerceve dudagi ust/sol kenara golge dusurur."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = (ust * np.exp(-yy / sigma) + sol * np.exp(-xx / sigma)
         + sag * np.exp(-(w - 1 - xx) / sigma) + alt * np.exp(-(h - 1 - yy) / sigma))
    return 1.0 - np.clip(g, 0, 0.35)


def lab(rgb):
    c = rgb.astype(np.float64) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


ISIK = {  # ic golge kenar siddetleri (ust, sol, sag, alt)
    'sol_ust': (0.16, 0.11, 0.035, 0.045),   # A: pencere isigi soldan, golgeler saga dusuyor
    'ust': (0.16, 0.06, 0.06, 0.04),         # B: iki yanda simetrik aplik, isik yukaridan
}


def yerlestir(taban, posterler, cik_dir, damga, isik='sol_ust'):
    cik_dir = Path(cik_dir); cik_dir.mkdir(parents=True, exist_ok=True)
    B = Image.open(taban).convert('RGB')
    a = np.asarray(B)
    rap = {'taban': list(B.size), 'acikliklar': [], 'kapilar': {}}
    kapi = rap['kapilar']
    kapi['taban_3360x840'] = B.size == (W, H)
    kutular = acikliklar(a)
    kapi['aciklik_sayisi_dogru'] = len(kutular) == len(posterler)
    out = a.astype(np.float32).copy()
    dE_maks, kirp_maks, oran_maks = 0.0, 0, 0.0
    for (x0, y0, x1, y1), pyol in zip(kutular, posterler):
        # 1 px tasma: cerceve ic kenarina tam oturur, beyaz dikis kalmaz
        x0, y0, x1, y1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1
        aw, ah = x1 - x0, y1 - y0
        P = Image.open(pyol).convert('RGB')
        pw, ph = P.size
        oran_fark = abs((pw / ph) / (aw / ah) - 1)
        s = max(aw / pw, ah / ph)                       # kaplama; esnetme yok (tek olcek)
        rw, rh = round(pw * s), round(ph * s)
        R = P.resize((rw, rh), Image.LANCZOS)
        kx, ky = (rw - aw) // 2, (rh - ah) // 2
        R = R.crop((kx, ky, kx + aw, ky + ah))
        r = np.asarray(R, np.float32)
        u, l, r_, al = ISIK[isik]
        g = ic_golge(aw, ah, ust=u, sol=l, sag=r_, alt=al)[..., None]
        out[y0:y1, x0:x1] = r * g
        # merkez (golge bandi disi) birebir mi?
        m = 40
        yer = np.clip(out[y0 + m:y1 - m, x0 + m:x1 - m] + 0.5, 0, 255).astype(np.uint8)
        dE = float(np.sqrt(((lab(yer) - lab(r[m:-m, m:-m].astype(np.uint8))) ** 2).sum(-1)).max())
        dE_maks = max(dE_maks, dE); kirp_maks = max(kirp_maks, rw - aw, rh - ah)
        oran_maks = max(oran_maks, oran_fark)
        rap['acikliklar'].append({'poster': Path(pyol).parent.name, 'kutu': [x0, y0, x1, y1],
                                  'aciklik_px': [aw, ah], 'aciklik_oran': round(aw / ah, 4),
                                  'poster_px': [pw, ph], 'poster_oran': round(pw / ph, 4),
                                  'olcek': round(s, 5), 'kirpilan_px': [rw - aw, rh - ah],
                                  'merkez_dE76_maks': round(dE, 3)})
    son = Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))
    # dikis: kutunun 1-3 px disinda (daha disi cerceve parlamasi) notr-acik (beyaz/gri pervaz) piksel
    sa = np.asarray(son); dikis = 0
    for x0, y0, x1, y1 in [tuple(d['kutu']) for d in rap['acikliklar']]:
        halka = np.zeros(sa.shape[:2], bool)
        halka[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = True
        halka[y0 - 1:y1 + 1, x0 - 1:x1 + 1] = False
        dikis += int(notr_acik(sa)[halka].sum())
    kapi['oran_fark_lt_1.5pct'] = oran_maks < 0.015
    kapi['kirpilan_le_8px'] = kirp_maks <= 8
    kapi['merkez_dE_lt_1'] = dE_maks < 1
    kapi['beyaz_dikis_0'] = dikis == 0
    rap['beyaz_dikis_px'] = dikis
    rap['SONUC'] = 'PASS' if all(kapi.values()) else 'FAIL'

    ad = f'ASTROLOVE_BANNER_ETSY_3360x840_{damga}'
    son.save(cik_dir / f'{ad}.png', optimize=True)
    son.save(cik_dir / f'{ad}.jpg', quality=95, subsampling=0)
    onizlemeler(son, cik_dir, rap)
    (cik_dir / 'BANNER_RAPOR.json').write_text(json.dumps(rap, ensure_ascii=False, indent=1))
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    return rap


def onizlemeler(son, cik_dir, rap):
    try:
        fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except OSError:
        fnt = ImageFont.load_default()
    # 1) gercek oran (4:1), 1680x420
    son.resize((1680, 420), Image.LANCZOS).save(cik_dir / 'ONIZLEME_gercek_oran_1680x420.jpg', quality=92)
    # 2) telefon: orta kirpim. Etsy mobil kirpim olcusu yayimlanmiyor; varsayim 2:1 orta (1680x840)
    tw = 1680; x0 = (W - tw) // 2
    tel = son.crop((x0, 0, x0 + tw, H))
    tel.resize((840, 420), Image.LANCZOS).save(cik_dir / 'ONIZLEME_telefon_orta_2x1.jpg', quality=92)
    # 3) kirpim nerede: tam banner uzerinde cerceve
    k = son.resize((1680, 420), Image.LANCZOS); d = ImageDraw.Draw(k)
    d.rectangle([x0 // 2, 0, (x0 + tw) // 2 - 1, 419], outline=(0, 150, 255), width=3)
    d.text((x0 // 2 + 8, 6), 'telefon orta kirpim (varsayim 2:1)', fill=(0, 110, 220), font=fnt)
    k.save(cik_dir / 'ONIZLEME_telefon_kirpim_yeri.jpg', quality=92)
    # 4) poster yakin plan (sembol/isim kontrolu), 1:1 piksel
    parcalar = [son.crop(tuple(a['kutu'])) for a in rap['acikliklar']]
    if parcalar:
        gw = sum(p.size[0] for p in parcalar) + 20 * (len(parcalar) - 1)
        gh = max(p.size[1] for p in parcalar)
        yk = Image.new('RGB', (gw, gh), 'white'); x = 0
        for p in parcalar:
            yk.paste(p, (x, 0)); x += p.size[0] + 20
        yk.save(cik_dir / 'ONIZLEME_poster_1e1.jpg', quality=95)


def sayfa(bannerlar, etiketler, cik):
    """A ve B alt alta, gercek oranda (1680x420) + her birinin telefon orta kirpimi (2:1)."""
    try:
        fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except OSError:
        fnt = ImageFont.load_default()
    tw = 1680; x0 = (W - tw) // 2
    satirlar = []
    for yol, et in zip(bannerlar, etiketler):
        b = Image.open(yol).convert('RGB')
        k = b.resize((1680, 420), Image.LANCZOS)
        d = ImageDraw.Draw(k)
        d.rectangle([x0 // 2, 0, (x0 + tw) // 2 - 1, 419], outline=(0, 150, 255), width=2)
        tel = b.crop((x0, 0, x0 + tw, H)).resize((840, 420), Image.LANCZOS)
        bas = Image.new('RGB', (1680 + 20 + 840, 40), 'white')
        ImageDraw.Draw(bas).text((6, 8), f'{et}: 3360x840 gercek oran (mavi = telefon orta kirpimi, varsayim 2:1)',
                                 fill='black', font=fnt)
        ImageDraw.Draw(bas).text((1700 + 6, 8), f'{et}: telefon orta kirpim', fill='black', font=fnt)
        sat = Image.new('RGB', (1680 + 20 + 840, 420), 'white')
        sat.paste(k, (0, 0)); sat.paste(tel, (1700, 0))
        satirlar += [bas, sat, Image.new('RGB', (sat.size[0], 30), 'white')]
    gh = sum(s.size[1] for s in satirlar)
    out = Image.new('RGB', (satirlar[0].size[0], gh), 'white'); y = 0
    for s in satirlar:
        out.paste(s, (0, y)); y += s.size[1]
    out.save(cik, quality=90)
    print('sayfa', out.size, '->', cik)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='k', required=True)
    b = sp.add_parser('buyut'); b.add_argument('--kaynak', required=True)
    b.add_argument('--model', required=True); b.add_argument('--cik', required=True)
    y = sp.add_parser('yerlestir'); y.add_argument('--taban', required=True)
    y.add_argument('--poster', action='append', required=True,
                   help='aciklik basina bir poster, soldan saga sirayla')
    y.add_argument('--cik', required=True); y.add_argument('--damga', required=True)
    y.add_argument('--isik', default='sol_ust', choices=sorted(ISIK))
    p = sp.add_parser('sayfa'); p.add_argument('--banner', action='append', required=True)
    p.add_argument('--etiket', action='append', required=True); p.add_argument('--cik', required=True)
    a = ap.parse_args()
    if a.k == 'sayfa':
        sayfa(a.banner, a.etiket, a.cik)
    elif a.k == 'buyut':
        buyut(a.kaynak, a.model, a.cik)
    else:
        r = yerlestir(a.taban, a.poster, a.cik, a.damga, a.isik)
        sys.exit(0 if r['SONUC'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
