#!/usr/bin/env python3
"""Goz kontrolu kesiti (Serdar 2 Eki): renk basina tek JPEG, 5 boy alt alta, 1:1. Bant satirlari KAPI_RAPORU'ndan
(siparis-kesit-son ile ayni). Tagline dikis: scripts/ornek/dikis_kapisi.dikis (esik 13). Isim / mesaj loga yazilmaz.
Kullanim: kesit_birlesik.py RECEIPT RENKLER(virgullu) DRIVE_DIZIN CIKTI"""
import glob
import io
import json
import os
import sys
import time
from pathlib import Path

import pikepdf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ornek'))
import dikis_kapisi as dk  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ESIK = 13.0
BOY = {(4800, 6000): '16x20', (5400, 7200): '18x24', (7200, 10800): '24x36', (3307, 4200): '11x14', (4960, 7015): 'A2'}
ORAN = {'4x5': '16x20', '3x4': '18x24', '2x3': '24x36', '11x14': '11x14', 'a_series': 'A2'}
SIRA = ['11x14', '16x20', '18x24', 'A2', '24x36']
RENK = {'Midnight_Blue': 'MIDNIGHT_BLUE', 'Deep_Black': 'DEEP_BLACK', 'Pure_White': 'PURE_WHITE',
        'Champagne_Ivory': 'CHAMPAGNE_IVORY', 'Warm_Parchment': 'WARM_PARCHMENT'}


def en_yeni(desen):
    f = sorted(glob.glob(desen, recursive=True), key=os.path.getmtime)
    return f[-1] if f else None


def etiket(im, yazi, boy=56):
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', boy)
    except OSError:
        f = ImageFont.load_default()
    b = Image.new('RGB', (im.width, im.height + boy + 24), (255, 255, 255))
    b.paste(im, (0, boy + 24))
    ImageDraw.Draw(b).text((12, 8), yazi, fill=(0, 0, 0), font=f)
    return b


def main(rec, renkler, d, cik):
    t_tum = time.time()
    cik = Path(cik); cik.mkdir(parents=True, exist_ok=True)
    renkler = [r for r in renkler.split(',') if r]
    bant = {}
    for r in renkler:
        f = en_yeni(f'{d}/**/KAPI_RAPORU_{r}.json')
        for o, v in json.load(open(f))['renkler'][r]['oranlar'].items():
            bant[(r, ORAN[o])] = {'isim': (v.get('isim_bandi_temizligi') or {}).get('satir'),
                                  'tag': (v.get('eski_metin_izi_kapisi') or {}).get('bant')}
    olcu, n = {}, 0
    toplam = len(renkler) * 5
    for pdf in sorted(glob.glob(f'{d}/**/AstroLove*_*.pdf', recursive=True)):
        r = next(v for k, v in RENK.items() if k in os.path.basename(pdf))
        if r not in renkler:
            continue
        bloklar = {}
        with pikepdf.open(pdf) as p:
            for pg in p.pages:
                for _, x in pg.images.items():
                    im = Image.open(io.BytesIO(x.read_raw_bytes())); im.load(); im = im.convert('RGB')
                    W, H = im.size; b = BOY[im.size]; k = W / 2400.0
                    bb = bant[(r, b)]
                    i0, i1 = bb['isim']; t0, t1 = int(bb['tag'][0] * k), int(bb['tag'][1] * k)
                    span = t1 - i0
                    y0, y1 = max(int(i0 - 1.3 * span), 0), min(int(t1 + 0.3 * span), H)
                    th = t1 - t0; p_ = int(0.12 * th)
                    tag = im.crop((int(0.08 * W), max(t0 - p_, 0), int(0.92 * W), min(t1 + p_, H)))
                    try:
                        dd = dk.dikis(tag)
                    except Exception as e:                        # noqa: BLE001  (olculemeyen bant kesiti durdurmaz)
                        dd = {'hata': f'{type(e).__name__}: {e}'}
                    dd['gecti'] = bool(dd.get('dikis', 1e9) <= ESIK)
                    olcu[f'{r}_{b}'] = {'kesit_satir': [y0, y1], 'tag_satir': [t0, t1], **dd}
                    yazi = (f'{r} {b} {W}x{H} 1:1 | satir {y0}-{y1} | tagline dikis {dd.get("dikis")} '
                            f'(ust {dd.get("dikis_ust")} / alt {dd.get("dikis_alt")} / govde {dd.get("dikis_govde")}) '
                            f'esik {ESIK} {"PASS" if dd["gecti"] else "FAIL"}')
                    bloklar[b] = etiket(im.crop((0, y0, W, y1)), yazi, boy=max(28, min(56, W // 90)))
                    n += 1
                    g = time.time() - t_tum
                    print(f'KESIT {n}/{toplam} {r} {b} dikis {dd.get("dikis")} {"PASS" if dd["gecti"] else "FAIL"} '
                          f'| gecen {g:.0f} sn kalan ~{g / n * (toplam - n):.0f} sn %{100 * n // toplam}', flush=True)
        sira = [bloklar[b] for b in SIRA if b in bloklar]
        Wm = max(x.width for x in sira); Hs = sum(x.height for x in sira) + 40 * (len(sira) - 1)
        c = Image.new('RGB', (Wm, Hs), (255, 255, 255)); y = 0
        for x in sira:
            c.paste(x, (0, y)); y += x.height + 40
        c.save(cik / f'KESIT_{r}_5boy_1e1.jpg', 'JPEG', quality=90, subsampling=0)
        print('DOSYA', f'KESIT_{r}_5boy_1e1.jpg', c.size, round(os.path.getsize(cik / f'KESIT_{r}_5boy_1e1.jpg') / 1e6, 1), 'MB', flush=True)
    (cik / 'DIKIS_TAGLINE.json').write_text(json.dumps(olcu, indent=1))
    print('SURE toplam', round(time.time() - t_tum, 1), 'sn')


if __name__ == '__main__':
    main(*sys.argv[1:5])
