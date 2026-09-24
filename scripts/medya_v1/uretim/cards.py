#!/usr/bin/env python3
"""Kova-Kova galeri kartlari 02-10: referans kartin piksel duzeni korunur; yalniz cift-ozgu
sanat/sembol/metin, dogrulanmis Kova kaynak sanati (05_WA_01) ve native font metin katmaniyla degisir."""
import json, sys, time
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
sys.path.insert(0, '.')
import master as M, subst as S, textlayer as T

REF = M.ROOT / 'etsy/REF_4570143815'
CARDS = {2: '02_8567954544', 3: '03_8615800647', 4: '04_8567954548', 5: '05_8567954574', 6: '06_8567954580',
         7: '07_8615800641', 8: '08_8616354969', 9: '09_8615800661', 10: '10_8615800655'}
BG = np.array([237., 232., 226.])
HDR = (418, 80, 760, 135)
log = {}

def header(card, n):
    out, p = T.replace(card, HDR, 'CANCER + LIBRA', 'AQUARIUS + AQUARIUS', 'mont', bg=BG)
    log.setdefault(n, {})['header'] = {k: p[k] for k in ('size', 'w', 'track', 'mse', 'box')}
    return out

def txt(card, n, box, old, new, key, align='left', bg=BG):
    out, p = T.replace(card, box, old, new, key, align=align, bg=bg)
    log.setdefault(n, {}).setdefault('text', []).append({'old': old, 'new': new, **{k: p[k] for k in ('size', 'w', 'track', 'mse', 'box')}})
    return out

def poster(card, n, rect, c, rel=S.REL45):
    x0, y0, x1, y1 = rect
    R = card[y0:y1, x0:x1]
    out, meta, masks = S.subst_poster(R, c, rel=rel)
    card = card.copy(); card[y0:y1, x0:x1] = out
    log.setdefault(n, {}).setdefault('poster', []).append({'rect': rect, 'color': c, **meta})
    return card, meta

def glyph_panel(card, n, rect, band_frac, flat=None):
    x0, y0, x1, y1 = rect
    R = card[y0:y1, x0:x1]; H = y1 - y0
    out, meta, rem = S.subst_glyphs(R, 'MB', (int(band_frac[0] * H), int(band_frac[1] * H)), flat_bg=flat)
    card = card.copy(); card[y0:y1, x0:x1] = out
    log.setdefault(n, {}).setdefault('glyph_panel', []).append({'rect': rect, **meta})
    return card

def card02(card):
    card = header(card, 2)
    return glyph_panel(card, 2, (145, 536, 2855, 1768), (0.03, 0.40))

def card03(card):
    card = header(card, 3)
    card = glyph_panel(card, 3, (145, 830, 1425, 1414), (0.03, 0.36))
    card = glyph_panel(card, 3, (1575, 830, 2855, 1414), (0.03, 0.36))
    # Ek karar (24 Eyl): sol/sag burc secimi sunulmaz; kart secimden bahsetmez.
    card = txt(card, 3, (130, 180, 1800, 330), 'Choose which sign goes on the left.', 'Your names, in one fixed layout.', 'ebg')
    card = txt(card, 3, (130, 325, 1800, 395), 'Each name stays with its zodiac sign when you switch the order.',
               'Both names sit under the Aquarius sign. The layout stays as shown.', 'mont')
    card = txt(card, 3, (560, 490, 1010, 590), 'Cancer left', 'Example 1', 'mont', align='center')
    card = txt(card, 3, (2020, 490, 2420, 590), 'Libra left', 'Example 2', 'mont', align='center')
    for full, part, new in (((400, 1730, 1170, 1800), (400, 1730, 790, 1800), 'EMILY  +  JAMES'),
                            ((1830, 1730, 2600, 1800), (1830, 1730, 2220, 1800), 'JAMES  +  EMILY')):
        p = T.fit(card, part, 'EMILY = CANCER', 'mont', BG)
        (fx0, fy0, fx1, fy1), _, _ = T.ink_of(card, full, BG)
        card = card.copy(); card[fy0 - 5:fy1 + 5, fx0 - 5:fx1 + 5] = BG
        card = T.draw_with(card, p, new, cx=(fx0 + fx1) / 2, base=p['oy'] + p['base0'])
        log.setdefault(3, {}).setdefault('text', []).append({'old': 'EMILY = CANCER (parca)', 'new': new, **{k: p[k] for k in ('size', 'w', 'track', 'mse', 'box')}})
    card = txt(card, 3, (1000, 1975, 2000, 2060), 'Choose by zodiac sign, not by gender.', 'Names in the photos are examples.', 'ebg', align='center')
    return card

def card04(card):
    card = header(card, 4)
    card = txt(card, 4, (130, 325, 1700, 395), 'Cancer and Libra, united in an original AstroLove design.',
               'Aquarius and Aquarius, united in an original AstroLove design.', 'mont')
    x0, y0, x1, y1 = (1320, 480, 2831, 2011); P = card[y0:y1, x0:x1].copy(); H, W = P.shape[:2]
    flat = np.median(P[5:40, 5:40].reshape(-1, 3), 0)
    ink = M.ink(P, flat, 40)
    top = np.zeros((H, W), bool); top[int(0.03 * H):int(0.25 * H)] = True
    low = np.zeros((H, W), bool); low[int(0.55 * H):int(0.98 * H)] = True
    gly = M.components(ink & top, 200); fus = M.components(ink & low, 200)
    # kucuk semboller
    lab, n = ndimage.label(gly); sides = []
    for side in (0, 1):
        pts = [np.where(lab == i) for i in range(1, n + 1)]
        pts = [p for p in pts if (p[1].mean() < W / 2) == (side == 0)]
        ys = np.concatenate([p[0] for p in pts]); xs = np.concatenate([p[1] for p in pts])
        sides.append((xs.min(), xs.max(), ys.min(), ys.max()))
    f = ((sides[0][1] - sides[0][0] + 1) / S.REF_GLYPH_W[0] + (sides[1][1] - sides[1][0] + 1) / S.REF_GLYPH_W[1]) / 2
    ys, xs = np.where(fus); fb = (xs.min(), xs.max(), ys.min(), ys.max())
    ff = ((fb[1] - fb[0] + 1) / S.REF_FUSION_WH[0] + (fb[3] - fb[2] + 1) / S.REF_FUSION_WH[1]) / 2
    P[ndimage.binary_dilation(gly | fus, iterations=6)] = flat
    out = P
    for side, (a0, a1, b0, b1) in enumerate(sides):
        m = S.glyph_src_mask('MB', side); yy, xx = np.where(m)
        s = M.S * f
        a, Fa = S.layer_mask('MB', m, s, W, H, (a0 + a1) / 2 - (xx.min() + xx.max()) / 2 * s, (b0 + b1) / 2 - (yy.min() + yy.max()) / 2 * s)
        out = S.composite(out, a, Fa)
    m = S.layer_part_mask('MB', 'fusion'); yy, xx = np.where(m); s = M.S * ff
    a, Fa = S.layer_mask('MB', m, s, W, H, (fb[0] + fb[1]) / 2 - (xx.min() + xx.max()) / 2 * s, (fb[2] + fb[3]) / 2 - (yy.min() + yy.max()) / 2 * s)
    out = S.composite(out, a, Fa)
    card = card.copy(); card[y0:y1, x0:x1] = np.clip(out, 0, 255)
    log.setdefault(4, {})['panel'] = {'glyph_f': float(f), 'fusion_f': float(ff), 'glyph_boxes': [list(map(int, b)) for b in sides], 'fusion_box': list(map(int, fb))}
    # etiketler (lacivert panel uzerinde altin)
    card = txt(card, 4, (1540, 860, 1790, 945), 'CANCER', 'AQUARIUS', 'mont', align='center', bg=flat)
    card = txt(card, 4, (2380, 860, 2580, 945), 'LIBRA', 'AQUARIUS', 'mont', align='center', bg=flat)
    return card

def card05(card):
    card = header(card, 5)
    for rect, c in (((269, 499, 791, 1151), 'MB'), ((1240, 500, 1760, 1150), 'DB'), ((2208, 497, 2734, 1152), 'CI'),
                    ((755, 1310, 1275, 1960), 'PW'), ((1722, 1306, 2248, 1963), 'WP')):
        card, _ = poster(card, 5, rect, c)
    return card

def card06(card):
    card = header(card, 6); card, _ = poster(card, 6, (190, 595, 1170, 1820), 'MB')
    # Serdar kurali 5: 'archival' iddiasi yok
    card = txt(card, 6, (1355, 1738, 2200, 1797), 'Printed with archival pigment inks.', 'Printed with pigment inks.', 'mont')
    return card

def card09(card):
    card = header(card, 9); card, _ = poster(card, 9, (180, 606, 1190, 1869), 'MB'); return card

def card07(card):
    card = header(card, 7)
    ins = (170, 717, 952, 1692)
    # eski gosterge kutusu + baglanti cizgisi (renk 147,118,73): baglanti cizgisini sil
    line_col = np.array([147., 118., 73.])
    seg = card[1040:1060, 952:1169]; m = np.abs(seg - BG).max(2) > 20; seg[m] = BG; card[1040:1060, 952:1169] = seg
    x0, y0, x1, y1 = ins
    R = card[y0:y1, x0:x1]
    boxm = (np.abs(R - line_col).max(2) < 30)
    boxm = M.components(boxm, 20); boxm = ndimage.binary_dilation(boxm, iterations=2)
    Rb = M.harmonic(R, boxm); card = card.copy(); card[y0:y1, x0:x1] = Rb
    log.setdefault(7, {})['gosterge_temizlenen_px'] = int(boxm.sum())
    card, meta = poster(card, 7, ins, 'MB')
    # yakin plan: Kova ozgun detay paneli (10_WA_05, MB) -> referans panel
    src = Image.open(M.ROOT / 'src/MB/10_WA_05_TECH_CRAFTED_DETAIL_AQUARIUS_AQUARIUS_MIDNIGHT_BLUE.jpg').convert('RGB')
    px0, py0, px1, py1 = 1100 + 10, 602 + 10, 2739 - 10, 1494 - 10
    ph = py1 - py0; tw, th = 2821 - 1169, 1854 - 569
    cw = int(round(ph * tw / th)); cx = (px0 + px1) // 2
    crop = src.crop((cx - cw // 2, py0, cx - cw // 2 + cw, py1)).resize((tw, th), Image.LANCZOS)
    card = card.copy(); card[569:1854, 1169:2821] = np.asarray(crop).astype(np.float64)
    # kaynak kirpimin poster uzerindeki yeri: sablon eslestirme (Kova MB poster, kaynak olcek)
    import cv2
    k = S.kova_src('MB')['K'].astype(np.uint8)
    best = None
    for sc in np.arange(3.0, 12.0, 0.1):
        t = np.asarray(crop.resize((max(8, int(tw / sc)), max(8, int(th / sc))), Image.LANCZOS))
        r = cv2.matchTemplate(cv2.cvtColor(k, cv2.COLOR_RGB2GRAY), cv2.cvtColor(t, cv2.COLOR_RGB2GRAY), cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(r)
        if best is None or mv > best[0]: best = (mv, sc, ml, t.shape[1], t.shape[0])
    mv, sc, (lx, ly), bw, bh = best
    s, ox, oy = meta['s'], None, None
    cxr, cyr, rr = meta['ring']; ox = cxr - 767.4 * s; oy = cyr - 819.7 * s
    bx0, by0 = ins[0] + lx * s + ox, ins[1] + ly * s + oy
    bx1, by1 = bx0 + bw * s, by0 + bh * s
    im = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    lw = 4
    d.rectangle([bx0, by0, bx1, by1], outline=tuple(int(v) for v in line_col), width=lw)
    yc = (by0 + by1) / 2
    d.line([(bx1, yc), (1169, yc)], fill=tuple(int(v) for v in line_col), width=lw)
    card = np.asarray(im).astype(np.float64)
    log.setdefault(7, {})['detail'] = {'match_score': float(mv), 'scale': float(sc), 'src_box': [int(lx), int(ly), int(bw), int(bh)],
                                        'card_box': [float(bx0), float(by0), float(bx1), float(by1)], 'crop_src': [cx - cw // 2, py0, cx - cw // 2 + cw, py1]}
    return card

def card08(card): return header(card, 8)
def card10(card): return header(card, 10)

FN = {2: card02, 3: card03, 4: card04, 5: card05, 6: card06, 7: card07, 8: card08, 9: card09, 10: card10}
if __name__ == '__main__':
    ns = [int(a) for a in sys.argv[1:]] or list(FN)
    t0 = time.time()
    for i, n in enumerate(ns, 1):
        card = M.arr(REF / f'{CARDS[n]}.jpg')
        out = FN[n](card)
        Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8)).save(M.ROOT / f'out/card{n:02d}.png')
        el = time.time() - t0
        print(f'[{i}/{len(ns)}] %{100*i/len(ns):.0f} gecen {el:.0f}s kalan ~{el/i*(len(ns)-i):.0f}s kart{n:02d}', flush=True)
        json.dump(log, open(M.ROOT / f'out/cards_log_{"_".join(map(str,ns))}.json', 'w'), indent=1, default=float)
