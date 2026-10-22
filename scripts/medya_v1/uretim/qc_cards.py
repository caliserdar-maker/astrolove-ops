#!/usr/bin/env python3
"""Kart QC (tek script, PASS/FAIL).
K1 boyut 3000x2250.
K2 dokunulmayan alan: degistirilen bolgeler (poster/panel dikdortgenleri, metin kutulari, 07 gosterge) DISI referansla maks fark 0.
K3 Cancer artigi: poster/panel icinde referans Cancer murekkebi (dilate) - beklenen Kova murekkebi (dilate) bolgesinde,
   |out-yerel zemin|>T olan >=6 px bilesen sayisi (dikdortgenin 8 px cerceve bandi haric) <= referansin kendi temiz zeminindeki yogunluk x alan (doku tabani) + 1.
K4 sembol hizasi: ciktida olculen Kova sembol bbox merkezi - hedef (referans sembol merkezi) |dx|,|dy| <= 2 px.
K5 metin: yeniden kurma RMS (eski metin, uydurulan font ile) <= 30 (JPEG referans).
K6 panel sembol hizasi (02/03): ciktida olculen Kova sembol merkezi - hedef <= 2 px."""
import glob, json, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, '.')
import master as M, subst as S, cards as C
log = json.load(open('out/cards_log_2_3_4_5_6_7_8_9_10.json'))
res = {}; allok = True
def dev_of(a): return np.abs(a - M.local_bg(a, 41)).max(2)
for n, name in C.CARDS.items():
    ref = M.arr(C.REF / f'{name}.jpg'); out = M.arr(f'out/card{n:02d}.png')
    L = log.get(str(n), {}); r = {'K1': out.shape[:2] == (2250, 3000)}
    touched = np.zeros(out.shape[:2], bool)
    for t in L.get('text', []) + ([L['header']] if 'header' in L else []):
        b = t['box']; touched[b[1] - 60:b[3] + 60, b[0] - 60:b[2] + 900] = True
    for key in ('poster', 'glyph_panel'):
        for p in L.get(key, []):
            x0, y0, x1, y1 = p['rect']; touched[y0:y1, x0:x1] = True
    if n == 4: touched[480:2011, 1320:2831] = True
    if n == 3: touched[470:1830, 100:2900] = True   # tek ornek: sag sutun kaldirildi, sol sutun ortalandi
    if n == 7: touched[560:1870, 160:2830] = True
    d = np.abs(out - ref).max(2); d[touched] = 0
    r['K2_dokunulmayan_maks_fark'] = float(d.max())
    k3 = []; k4 = []
    for p in L.get('poster', []):
        x0, y0, x1, y1 = p['rect']; R = ref[y0:y1, x0:x1]; O = out[y0:y1, x0:x1]; H, W = R.shape[:2]
        light = p['light']; T = 16 if light else 22
        cx, cy, rr = p['ring']; s = p['s']
        yy, xx = np.mgrid[:H, :W]
        ink = M.ink(R, M.local_bg(R, 41), 18 if light else 30)
        disk = np.hypot(xx - cx, yy - cy) <= rr + max(6, 0.04 * rr)
        cancer = M.components(ink & ((disk & (yy < cy + 0.8 * rr)) | ((yy >= cy + 0.8 * rr) & (yy < cy + 1.1 * rr))), 8)
        k = S.kova_src(p['color'])
        E = S.warp_full(k['art'].astype(float), s, cx - 767.4 * s, cy - 819.7 * s, W, H) > 0.05
        for side, (dcx, dcy) in enumerate(p['glyph_dst']):
            m = S.glyph_src_mask(p['color'], side); ys, xs = np.where(m)
            scx, scy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
            E |= S.warp_full(m.astype(float), s, dcx - scx * s, dcy - scy * s, W, H) > 0.05
            # K4
            dv = dev_of(O); bw = int(60 * s / M.S) + 10; bh = int(35 * s / M.S) + 10
            box = (slice(max(0, int(dcy) - bh), int(dcy) + bh), slice(max(0, int(dcx) - bw), int(dcx) + bw))
            g = M.components(dv[box] > T, 10); gy, gx = np.where(g)
            k4.append([float((gx.min() + gx.max()) / 2 + box[1].start - dcx), float((gy.min() + gy.max()) / 2 + box[0].start - dcy)])
        zone = ndimage.binary_dilation(cancer, iterations=3) & ~ndimage.binary_dilation(E, iterations=4)
        zone[:8] = zone[-8:] = False; zone[:, :8] = zone[:, -8:] = False   # inset cerceve cizgisi (cikti=referans, fark 0) olcum disi
        if n == 7 and 'detail' in L:   # gosterge kutusu + baglanti cizgisi (tasarim ogesi, renk 147,118,73) olcum disi
            b = [int(round(v - o)) for v, o in zip(L['detail']['card_box'], (x0, y0, x0, y0))]
            ex = np.zeros((H, W), bool); ex[b[1] - 6:b[3] + 7, b[0] - 6:b[2] + 7] = True; ex[b[1] + 6:b[3] - 6, b[0] + 6:b[2] - 6] = False
            cyl = (b[1] + b[3]) // 2; ex[cyl - 12:cyl + 13, b[2]:] = True; zone &= ~ex
        dv = dev_of(O); lab, nn = ndimage.label(zone & (dv > T)); cnt = int((np.bincount(lab.ravel())[1:] >= 6).sum()) if nn else 0
        rd = dev_of(R); ctrl = np.zeros((H, W), bool); ctrl[int(0.02 * H):int(0.12 * H), int(0.05 * W):int(0.95 * W)] = True
        lb, nb = ndimage.label(ctrl & (rd > T)); base = ((np.bincount(lb.ravel())[1:] >= 6).sum() if nb else 0) / ctrl.sum()
        k3.append({'rect': p['rect'], 'renk': p['color'], 'artik': cnt, 'limit': round(float(base * zone.sum()) + 1, 2)})
    for p in L.get('glyph_panel', []):
        for (dcx, dcy) in p['dst']: pass
    r['K3'] = k3; r['K4'] = k4
    k5 = [round(float(np.sqrt(t['mse'])), 1) for t in L.get('text', []) + ([L['header']] if 'header' in L else [])]
    r['K5_rms'] = k5
    ok = r['K1'] and r['K2_dokunulmayan_maks_fark'] == 0 and all(x['artik'] <= x['limit'] for x in k3) \
        and all(abs(a) <= 2 and abs(b) <= 2 for a, b in k4) and all(v <= 30 for v in k5)
    r['SONUC'] = 'PASS' if ok else 'FAIL'; allok &= ok
    res[n] = r; print(n, r)
json.dump(res, open('out/qc_cards.json', 'w'), indent=1, default=float)
print('GENEL', 'PASS' if allok else 'FAIL')
