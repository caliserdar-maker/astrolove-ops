#!/usr/bin/env python3
"""YAKIN_DOKU ek (inceleme ad3aa746 bulgu 5): ana sembol GOVDESI ile kucuk burc YAN YANA, ayni olcek (954, 3x), son PNG'lerden.
Uretim koşusu degil: yalniz teslim PNG'lerinden kirpim. Altin piksel: R > G > B, R - B > 60, luma > 60.
Ana govde penceresi: sembol kutusunda (OLCUM sembol_kutu) altin mesafe donusumu en buyuk nokta merkezli 70 x 70.
Kucuk burc: sembol kutusunun altindaki sol altin bilesen (cancer). Kullanim: ornament_yan_yana.py --dir CIKTI --font TTF"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def altin(rgb):
    r, g, b = [rgb[..., i].astype(np.int32) for i in range(3)]
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (r > g) & (g > b) & (r - b > 60) & (L > 60)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dir', required=True); ap.add_argument('--font', required=True)
    a = ap.parse_args(); O = Path(a.dir)
    R = json.loads((O / 'OLCUM.json').read_text())
    font = ImageFont.truetype(a.font, 24)
    satir = []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        rgb = np.asarray(Image.open(O / f'CANCER_LIBRA_{renk}_954.png').convert('RGB'))
        x0, y0, x1, y1 = R['sonuc'][renk]['sembol_kutu']
        m = altin(rgb).astype(np.uint8)
        ms = np.zeros_like(m); ms[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        dt = cv2.distanceTransform(ms, cv2.DIST_L2, 5)
        cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
        W = 70
        ana = (cx - W // 2, cy - W // 2, cx + W // 2, cy + W // 2)
        alt = np.zeros_like(m); alt[y1:y1 + 120, x0 - 60:(x0 + x1) // 2] = m[y1:y1 + 120, x0 - 60:(x0 + x1) // 2]
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(alt, np.ones((9, 9), np.uint8)), 8)   # sembol parcalari birlesir (isim satiri 20 px uzakta)
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        kx, ky, kw, kh = st[i, :4]
        kuc = (kx - 2, ky - 2, kx + kw + 2, ky + kh + 2)
        im = Image.fromarray(rgb)
        p1 = im.crop(ana); p2 = im.crop(kuc)
        h = max(p1.height, p2.height)
        c = Image.new('RGB', (p1.width + p2.width + 8, h), 'white'); c.paste(p1, (0, 0)); c.paste(p2, (p1.width + 8, 0))
        c = c.resize((c.width * 3, c.height * 3), Image.NEAREST)
        yazi = f'{renk}: sol ana sembol govdesi (en kalin yer), sag kucuk burc; ayni karede yan yana, 954 (3x)'
        tw = int(ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(yazi, font=font)) + 12
        k = Image.new('RGB', (max(c.width, tw), c.height + 36), 'white'); k.paste(c, (0, 0))
        ImageDraw.Draw(k).text((4, c.height + 4), yazi, fill=(20, 20, 20), font=font)
        satir.append((k, dict(ana_pencere=[int(v) for v in ana], kucuk_kutu=[int(v) for v in kuc])))
    # mevcut YAKIN_DOKU: alt alta 3 satiri (son 3 satir) cikar, yan yana satirlari ekle
    yd = np.asarray(Image.open(O / 'YAKIN_DOKU.png').convert('RGB'))
    bos = (yd > 250).all(2).all(1)
    bant, i = [], 0
    while i < len(bos):
        if not bos[i]:
            j = i
            while j < len(bos) and not bos[j]:
                j += 1
            bant.append((i, j)); i = j
        else:
            i += 1
    # her satir = gorsel blogu + etiket blogu; son 3 satir (6 bant) alt alta karelerdir
    kes = bant[-6][0] - 12
    ust = Image.fromarray(yd[:kes])
    W_ = max(ust.width, max(s.width for s, _ in satir))
    u = Image.new('RGB', (W_, ust.height + sum(s.height + 24 for s, _ in satir)), 'white'); u.paste(ust, (0, 0)); yy = ust.height + 12
    for s, _ in satir:
        u.paste(s, (0, yy)); yy += s.height + 24
    u.save(O / 'YAKIN_DOKU.png')
    R['yakin_doku_yan_yana'] = {renk: v for renk, (_, v) in zip(('RUBY', 'SAPPHIRE', 'EMERALD'), satir)}
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R['yakin_doku_yan_yana']))


if __name__ == '__main__':
    main()
