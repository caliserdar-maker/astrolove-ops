#!/usr/bin/env python3
"""IZ TARAMASI (tek script, PASS/FAIL): Kova-Kova gorsellerinde baska burcun (Cancer/Libra) izi.
Her islenen bolgede, referanstaki Cancer/Libra murekkebinin (tam bilesen) d=1..30 px uzakliktaki halkalarinda
|cikti - temiz zemin tahmini| ortalamasi tabana oranlanir; beklenen Kova murekkebi ve Kova'nin ciktida olculen
kendi halesi (kova_hale_r) ile korunan metin olcum disidir. Ayrica murekkebin KENDISI (d=0) de olculur.
Taban: ayni izin bolgesinde d=31..45 halkasi (yerel; genis parilti/doku esit etkiler). v1 uzak zemin tabani kullaniyordu,
MB'de Kova'nin genis isigini iz sayiyordu.
T1 hale: tum halkalarda (d=0..30) oran <= 1.15.
T2 gorunur iz: Cancer/Libra ayak izi (+30 px) icinde beklenen Kova murekkebi (+3; ortak cember dahil) ve metin disinda kalan
murekkep bileseni (>=3 px, esik referans murekkep esiginin yarisi) sayisi <= doku siniri (ayni goruntunun iz bolgesi disi
yogunlugu x alan; temiz zeminde 0).
PASS: T1 ve T2. Kontrol: ayni olcum referansin kendisinde FAIL vermeli (ref_* alanlari).
Zemin tahmini: posterlerde Kova'nin hizalanmis ton-esli sablon zemini; panellerde murekkep maskeli normalize
Gauss (sigma 25) zemin."""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, '.')
import master as M, subst as S

def profile(img, m, bgest, allowed, dmax=30):
    dev = np.abs(img - bgest).max(2)
    d30 = ndimage.binary_dilation(m, iterations=dmax); d45 = ndimage.binary_dilation(m, iterations=dmax + 15)
    loc = allowed & d45 & ~d30
    far = allowed & ~ndimage.binary_dilation(m, iterations=dmax + 5)
    base = max(dev[loc].mean() if loc.sum() > 200 else dev[far].mean(), 0.5)
    prof = [float(dev[m & allowed].mean() / base) if (m & allowed).sum() > 20 else 1.0]
    prev = m
    for d in range(1, dmax + 1):
        cur = ndimage.binary_dilation(m, iterations=d); ring = cur & ~prev & allowed; prev = cur
        prof.append(float(dev[ring].mean() / base) if ring.sum() > 20 else 1.0)
    return [round(x, 2) for x in prof]

def foreign(img, m, expected, protect, thr, dmax=30):
    """T2: ayak izi (+30) icinde beklenmeyen murekkep bilesen (>=3 px) sayisi ve doku siniri.
    Sinir = ayni goruntude ayak izi (+45) DISINDAKI izinli alanda ayni esikle bulunan bilesen yogunlugu x bolge alani
    (WP kagit dokusu gibi). Temiz zeminde sinir 0."""
    zone = ndimage.binary_dilation(m, iterations=dmax)
    exp = ndimage.binary_dilation(expected, iterations=3)
    ink = M.ink(img, M.local_bg(img, 41), thr) & ~exp & ~protect
    def count(mask):
        lab, n = ndimage.label(ink & mask)
        if n == 0: return 0
        return int((ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) >= 3).sum())
    z = zone & ~exp & ~protect
    ctrl = ~ndimage.binary_dilation(m, iterations=dmax + 15) & ~exp & ~protect
    ctrl[:4] = ctrl[-4:] = False; ctrl[:, :4] = ctrl[:, -4:] = False
    lim = count(ctrl) / max(ctrl.sum(), 1) * z.sum() if ctrl.sum() > 5000 else 0.0
    return count(zone), round(float(lim), 2)

def smooth_bg(img, allink, sigma=25):
    w = (~ndimage.binary_dilation(allink, iterations=6)).astype(float)
    num = np.stack([ndimage.gaussian_filter(img[..., i] * w, sigma) for i in range(3)], 2)
    den = ndimage.gaussian_filter(w, sigma)[..., None]
    return num / np.maximum(den, 1e-3)

def poster_region(Rref, Rout, c, ring, s, glyph_dst, extra=None):
    H, W = Rref.shape[:2]; cx, cy, r = ring
    light = Rref[int(H * .02):int(H * .08), int(W * .1):int(W * .9)].mean() > 128
    ink = M.ink(Rref, M.local_bg(Rref, 41), 18 if light else 30)
    yy, xx = np.mgrid[:H, :W]
    disk = np.hypot(xx - cx, yy - cy) <= r + max(6, 0.04 * r)
    art = M.components(ink & disk & (yy < cy + 0.8 * r), 8)
    gb = np.zeros((H, W), bool)
    for gx, gy in glyph_dst:
        gb[int(gy - 0.05 * H):int(gy + 0.05 * H), int(gx - 0.10 * W):int(gx + 0.10 * W)] = True
    gly = M.components(ink & gb & (yy >= cy + 0.8 * r) & (yy < cy + 1.1 * r), 8)
    k = S.kova_src(c)
    kb = S.warp_full(k['kbg'], s, cx - 767.4 * s, cy - 819.7 * s, W, H); valid = kb[..., 0] >= 0
    E = S.warp_full(k['art'].astype(float), s, cx - 767.4 * s, cy - 819.7 * s, W, H) > 0.02
    for side, (dcx, dcy) in enumerate(glyph_dst):
        mm = S.glyph_src_mask(c, side); ys, xs = np.where(mm); scx, scy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        E |= S.warp_full(mm.astype(float), s, dcx - scx * s, dcy - scy * s, W, H) > 0.02
    both = valid & ~ndimage.binary_dilation(ink | E, iterations=4)
    kt = kb.copy()
    for ch in range(3):
        x = kb[..., ch][both]; y = Rref[..., ch][both]
        p = np.linalg.lstsq(np.c_[x, np.ones_like(x)], y, rcond=None)[0]
        if not (0.7 <= p[0] <= 1.4) or x.std() < 4: p = np.array([1.0, float(np.median(y - x))])
        kt[..., ch] = kb[..., ch] * p[0] + p[1]
    gzone = np.zeros((H, W), bool); pz = int(round(0.04 * r))
    for gx, gy in glyph_dst:
        g1 = gly & gb & (np.abs(xx - gx) < 0.10 * W)
        if g1.any():
            ys, xs = np.where(g1); gzone[max(ys.min() - pz, 0):ys.max() + pz + 1, max(xs.min() - pz, 0):xs.max() + pz + 1] = True
    low = M.components(ink & (yy >= cy + 0.8 * r) & ~gly, 8)
    lab_t, nt = ndimage.label(low)
    inside = ndimage.minimum(gzone.astype(int), lab_t, index=np.arange(1, nt + 1)) if nt else []
    text = low & ~np.isin(lab_t, [i + 1 for i, v in enumerate(inside) if v == 1])
    tprot = ndimage.binary_dilation(text, iterations=3)
    if extra is not None: tprot |= extra
    # beklenen Kova murekkebi + KENDI halesi: yaricap ciktida Kova murekkebinden olculur (v2a'da sabit 3 px idi; MB'de
    # Kova parlamasi Cancer halkalarina dusup iz gibi sayiliyordu)
    free = valid & ~tprot & ~ndimage.binary_dilation(art | gly, iterations=35)
    r_k, _ = M.halo_radius(Rout, E, kt, free)
    allowed = valid & ~ndimage.binary_dilation(E, iterations=max(3, r_k)) & ~tprot
    allowed[:3] = allowed[-3:] = False; allowed[:, :3] = allowed[:, -3:] = False
    thr = (18 if light else 30) / 2; cancer = art | gly | (low & ~text)
    band = np.abs(np.hypot(xx - cx, yy - cy) - r) <= 0.03 * r + 4   # ortak AstroLove cemberi (iki tasarimda ayni)
    E = E | band
    edge = np.zeros((H, W), bool); edge[:4] = edge[-4:] = True; edge[:, :4] = edge[:, -4:] = True
    return {'art_cikti': profile(Rout, art, kt, allowed), 'gly_cikti': profile(Rout, gly, kt, allowed),
            'art_ref': profile(Rref, art, kt, allowed)[:3],
            'kova_hale_r': int(r_k), 'T2_iz_bilesen': foreign(Rout, cancer, E, tprot | edge, thr),
            'ref_T2_iz_bilesen': foreign(Rref, cancer, E, tprot | edge, thr)}

def panel_region(Rref, Rout, c, gly_ref, protect):
    allink = M.ink(Rout, M.local_bg(Rout, 61), 30) | gly_ref
    bg = smooth_bg(Rout, allink | protect)
    oi = M.ink(Rout, M.local_bg(Rout, 61), 30) & ~protect
    lab, n = ndimage.label(oi); sz = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) if n else np.zeros(0)
    Eo = np.isin(lab, [i + 1 for i, v in enumerate(sz) if v >= 0.1 * sz.max()]) if n else np.zeros(oi.shape, bool)
    free = ~protect & ~ndimage.binary_dilation(gly_ref, iterations=35)
    r_k, _ = M.halo_radius(Rout, Eo, bg, free)
    allowed = ~ndimage.binary_dilation(Eo, iterations=max(3, r_k)) & ~protect
    return {'kova_hale_r': int(r_k), 'gly_cikti': profile(Rout, gly_ref, bg, allowed), 'gly_ref': profile(Rref, gly_ref, smooth_bg(Rref, allink | protect), allowed)[:3],
            'T2_iz_bilesen': foreign(Rout, gly_ref, Eo, protect, 15), 'ref_T2_iz_bilesen': foreign(Rref, gly_ref, Eo, protect, 15)}

def verdict(d):
    worst = max(max(v) for k, v in d.items() if k.endswith('cikti'))
    d['maks_oran'] = round(worst, 2)
    n, lim = d['T2_iz_bilesen']; rn, rlim = d['ref_T2_iz_bilesen']
    d['SONUC'] = 'PASS' if worst <= 1.15 and n <= lim else 'FAIL'
    d['kontrol_ref_yakalandi'] = rn > rlim or max(d.get('art_ref', d.get('gly_ref'))) > 1.5
    return d

if __name__ == '__main__':
    res = {}
    meta = json.load(open('out/master_meta.json'))
    for c in M.COLORS:
        ref = M.arr('refs_centered/' + M.COLORS[c][0])[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]]
        out = M.arr(f'out/cover_{c}.png')[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]]
        res[f'kapak_{c}'] = verdict(poster_region(ref, out, c, (*M.RING_C, M.RING_R), M.S, M.DST_C)); print(f'kapak_{c}', {k: v for k, v in res[f'kapak_{c}'].items() if not k.endswith('cikti')}, flush=True)
    vm = json.load(open('out/video_states_meta.json')); A = np.load('vid/ref_frames.npy')
    for st, fr in {0: 0, 1: 20, 2: 60, 3: 110}.items():
        ref = A[fr].astype(float)[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]]
        out = M.arr(f'out/cover_state{st}.png')[M.OPEN[1]:M.OPEN[3], M.OPEN[0]:M.OPEN[2]]
        res[f'video_durum{st}'] = verdict(poster_region(ref, out, 'MB', (*M.RING_C, M.RING_R), M.S, vm[str(st)]['glyph_dst_center'])); print(f'video_durum{st}', {k: v for k, v in res[f'video_durum{st}'].items() if not k.endswith('cikti')}, flush=True)
    L = json.load(open('out/cards_log_2_3_4_5_6_7_8_9_10.json'))
    import cards as C
    for n in ('5', '6', '7', '9'):
        ref = M.arr(C.REF / f'{C.CARDS[int(n)]}.jpg'); out = M.arr(f'out/card{int(n):02d}.png')
        for p in L[n]['poster']:
            x0, y0, x1, y1 = p['rect']
            key = f'kart{int(n):02d}_{p["color"]}'
            ex = None
            if n == '7':   # kart 7 gosterge kutusu + baglanti cizgisi (tasarim ogesi, iz degil) olcum disi
                bx0, by0, bx1, by1 = [v - o for v, o in zip(L['7']['detail']['card_box'], (x0, y0, x0, y0))]
                ex = np.zeros((y1 - y0, x1 - x0), bool); b = [int(round(v)) for v in (bx0, by0, bx1, by1)]
                ex[b[1] - 6:b[3] + 7, b[0] - 6:b[2] + 7] = True; ex[b[1] + 6:b[3] - 6, b[0] + 6:b[2] - 6] = False
                cyl = (b[1] + b[3]) // 2; ex[cyl - 12:cyl + 13, b[2]:] = True
            res[key] = verdict(poster_region(ref[y0:y1, x0:x1], out[y0:y1, x0:x1], p['color'], p['ring'], p['s'], p['glyph_dst'], ex)); print(key, {k: v for k, v in res[key].items() if not k.endswith('cikti')}, flush=True)
    for n in ('2', '3'):
        ref = M.arr(C.REF / f'{C.CARDS[int(n)]}.jpg'); out = M.arr(f'out/card{int(n):02d}.png')
        for i, p in enumerate(L[n].get('glyph_panel', [])):
            x0, y0, x1, y1 = p['rect']; R = ref[y0:y1, x0:x1]; H = y1 - y0
            ox0, oy0, ox1, oy1 = p.get('rect_out', p['rect']); O = out[oy0:oy1, ox0:ox1]
            ink = M.ink(R, M.local_bg(R, 61), 30); band = np.zeros(ink.shape, bool); band[int(0.03 * H):int(0.36 * H)] = True
            g = M.components(ink & band, 30); prot = ndimage.binary_dilation(M.components(ink & ~band, 30), iterations=3)
            key = f'kart{int(n):02d}_panel{i}'; res[key] = verdict(panel_region(R, O, 'MB', g, prot)); print(key, {k: v for k, v in res[key].items() if not k.endswith('cikti')}, flush=True)
    ref = M.arr(C.REF / f'{C.CARDS[4]}.jpg'); out = M.arr('out/card04.png')
    x0, y0, x1, y1 = (1320, 480, 2831, 2011); R = ref[y0:y1, x0:x1]; O = out[y0:y1, x0:x1]; H = y1 - y0
    flat = np.median(R[5:40, 5:40].reshape(-1, 3), 0); ink = M.ink(R, flat, 40)
    zone = np.zeros(ink.shape, bool); zone[int(0.03 * H):int(0.25 * H)] = True; zone[int(0.55 * H):int(0.98 * H)] = True
    g = M.components(ink & zone, 200); prot = ndimage.binary_dilation(M.components(ink & ~zone, 20), iterations=3)
    res['kart04_panel'] = verdict(panel_region(R, O, 'MB', g, prot)); print('kart04_panel', {k: v for k, v in res['kart04_panel'].items() if not k.endswith('cikti')}, flush=True)
    ok = all(v['SONUC'] == 'PASS' and v['kontrol_ref_yakalandi'] for v in res.values())
    json.dump(res, open('out/iz_tarama.json', 'w'), indent=1)
    print('GENEL', 'PASS' if ok else 'FAIL', 'bolge', len(res))
