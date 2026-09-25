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
SIGNS = ('AQUARIUS', 'AQUARIUS')   # (sol, sag) burc; 77 cift sablonu bunu degistirir

def caption03(signs=SIGNS, n1='EMILY', n2='JAMES'):
    """Kart 3 alt yazisi (Serdar, 25 Eyl): ayni burc -> Left/Right name; farkli burc -> NAME UNDER {A}/{B}."""
    if signs[0] == signs[1]: return f'LEFT NAME = {n1}   RIGHT NAME = {n2}'
    return f'NAME UNDER {signs[0]} = {n1}   NAME UNDER {signs[1]} = {n2}'
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
    """Ek karar (24 Eyl): sol/sag secim yok; Serdar onayi (iterasyon 3): TEK ornek, ortalanmis."""
    card = header(card, 3)
    card = glyph_panel(card, 3, (145, 830, 1425, 1414), (0.03, 0.36))
    card = txt(card, 3, (130, 180, 1800, 330), 'Choose which sign goes on the left.', 'Your names, in one fixed layout.', 'ebg')
    card = txt(card, 3, (130, 325, 1800, 395), 'Each name stays with its zodiac sign when you switch the order.',
               'Both names sit under the Aquarius sign. The layout stays as shown.', 'mont')
    card = txt(card, 3, (1000, 1975, 2000, 2060), 'Choose by zodiac sign, not by gender.', 'Names in the photos are examples.', 'ebg', align='center')
    card = txt(card, 3, (560, 490, 1010, 590), 'Cancer left', 'Example', 'mont', align='center')
    # alt yazi: referans alt yazi fontu kelime bazinda (JAMES) alt piksel uyumla olculur
    pc = T.fit(card, (822, 1738, 972, 1792), 'JAMES', 'mont', BG, (500,), sub=True, sizes_fixed=list(np.arange(38.0, 40.51, 0.25)))
    log.setdefault(3, {}).setdefault('text', []).append({'old': 'JAMES (alt yazi olcum)', 'new': 'LEFT NAME ...', **{k: pc[k] for k in ('size', 'w', 'track', 'mse', 'box')}})
    base_c = pc['oy'] + pc['base0']
    card = card.copy()
    card[1740:1800, 400:1180] = BG           # sol alt yazi
    card[470:1830, 1440:2900] = BG           # sag sutun (2. ornek: etiket, panel, alt yazi) kaldirildi
    # sol sutunu (etiket + panel) karta ortala: dx = 1500 - 785; alt yazi kaydirmadan sonra kart ortasina (uzun burc adlari sigsin)
    dx = 1500 - 785
    blk = card[470:1830, 100:1470].copy()
    card[470:1830, 100:1470] = BG
    card[470:1830, 100 + dx:1470 + dx] = blk
    cap = caption03()
    card = T.draw_with(card, pc, cap, cx=1500, base=base_c)
    log[3]['alt_yazi'] = cap
    log[3]['tek_ornek'] = {'kaldirilan': [1440, 470, 2900, 1830], 'kaydirma_dx': dx}
    gp = log[3]['glyph_panel'][0]; x0, y0, x1, y1 = gp['rect']; gp['rect_out'] = [x0 + dx, y0, x1 + dx, y1]
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
    prot4 = ndimage.binary_dilation(M.components(ink & ~(top | low), 20), iterations=3)
    r4, _ = M.halo_radius(P, gly | fus, np.broadcast_to(flat, P.shape).astype(float), ~prot4)
    rem4 = ndimage.binary_dilation(gly | fus, iterations=r4 + 1) & ~prot4
    fill4 = P.copy(); fill4[rem4] = flat
    out = M.soft_blend(P, fill4, rem4)
    for side, (a0, a1, b0, b1) in enumerate(sides):
        m = S.glyph_src_mask('MB', side); yy, xx = np.where(m)
        s = M.S * f
        a, Fa = S.layer_mask('MB', m, s, W, H, (a0 + a1) / 2 - (xx.min() + xx.max()) / 2 * s, (b0 + b1) / 2 - (yy.min() + yy.max()) / 2 * s)
        out = S.composite(out, a, Fa)
    m = S.layer_part_mask('MB', 'fusion'); yy, xx = np.where(m); s = M.S * ff
    a, Fa = S.layer_mask('MB', m, s, W, H, (fb[0] + fb[1]) / 2 - (xx.min() + xx.max()) / 2 * s, (fb[2] + fb[3]) / 2 - (yy.min() + yy.max()) / 2 * s)
    out = S.composite(out, a, Fa)
    card = card.copy(); card[y0:y1, x0:x1] = np.clip(out, 0, 255)
    log.setdefault(4, {})['panel'] = {'halo_r': int(r4), 'glyph_f': float(f), 'fusion_f': float(ff), 'glyph_boxes': [list(map(int, b)) for b in sides], 'fusion_box': list(map(int, fb))}
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
    # yakin plan (Serdar, 25 Eyl): dalgalarin ic ice gectigi kesisim. Kaynak: Kova ozgun poster 05_WA_01 (KP kirpimi),
    # kutu kaynak koordinatinda secilir -> panel ve inset kutusu ayni geometriden (sablon eslestirme gerekmez)
    tw, th = 2821 - 1169, 1854 - 569
    DET = (662, 672, 962, 905)   # kaynak px, en/boy = panel en/boy (300/233 ~ 1652/1285)
    K = S.kova_src('MB')['K']
    crop = Image.fromarray(K.astype(np.uint8)).crop(DET).resize((tw, th), Image.LANCZOS)
    card = card.copy(); card[569:1854, 1169:2821] = np.asarray(crop).astype(np.float64)
    s = meta['s']; cxr, cyr, rr = meta['ring']; ox = cxr - 767.4 * s; oy = cyr - 819.7 * s
    bx0, by0 = ins[0] + ox + DET[0] * s, ins[1] + oy + DET[1] * s
    bx1, by1 = ins[0] + ox + DET[2] * s, ins[1] + oy + DET[3] * s
    # dogrulama: kutunun altindaki inset icerigi ile panelin kucultulmusu (NCC, cizimden once)
    import cv2
    sub = card[int(round(by0)) + 6:int(round(by1)) - 6, int(round(bx0)) + 6:int(round(bx1)) - 6]
    pan = np.asarray(crop.resize((int(round(bx1 - bx0)), int(round(by1 - by0))), Image.LANCZOS)).astype(np.float64)[6:-6, 6:-6]
    hh, ww = min(sub.shape[0], pan.shape[0]), min(sub.shape[1], pan.shape[1])
    a = sub[:hh, :ww].mean(2).ravel(); b = pan[:hh, :ww].mean(2).ravel()
    ncc = float(np.corrcoef(a, b)[0, 1])
    im = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    lw = 4
    d.rectangle([bx0, by0, bx1, by1], outline=tuple(int(v) for v in line_col), width=lw)
    yc = (by0 + by1) / 2
    d.line([(bx1, yc), (1169, yc)], fill=tuple(int(v) for v in line_col), width=lw)
    card = np.asarray(im).astype(np.float64)
    log.setdefault(7, {})['detail'] = {'kaynak': '05_WA_01 KP', 'src_box': list(DET), 'buyutme': round(tw / (DET[2] - DET[0]), 2),
                                        'card_box': [float(bx0), float(by0), float(bx1), float(by1)], 'kutu_panel_ncc': round(ncc, 4)}
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
