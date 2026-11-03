#!/usr/bin/env python3
"""ALTIN_MOTOR deneme 5 ON OLCUM (Merkez 3 Kas; deneme sayilmaz, uretim degil): notr koyu kontur golgesi etkisi.
Deneme 4 butunlesmesi (ornament_motor.boya_motor + dus_sabit, ic golge guc 0.35) ORN_DUMP katmanindan yeniden kurulur; once kontursuz
cikti e5412718 PNG'leriyle bayt bayt karsilastirilir (oz test). Kontur: tum ogelerin birlesik maskesi (alfa >= 0.5) disinda mesafe d ile
kapsama clip(1.5 + 0.5 - d, 0, 1) (1.5 px genisletme, kenar yumusak), sonra GaussianBlur sigma 0.6; kayma 0; notr siyah:
zemin x (1 - opak x kontur), dis golgeden SONRA, ogelerden ONCE (ogeler ustune biner; yalniz kenar bandi ve disari 1.5 px etkilenir).
Olcum: ornament_kenar_olc (onayli tanim): kenar yumusatma bandi (alfa 0.05 - 0.9) NNLS zemin payi ortancasi, ana / kucuk havuz.
Kullanim: ornament_kontur_on.py --pkl PKL --kaynak DIR --d4 DIR(e5412718 PNG) --cikti DIR"""
import argparse
import importlib.util
import json
import pickle
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
_s = importlib.util.spec_from_file_location('ko', _d / 'ornament_kenar_olc.py'); ko = importlib.util.module_from_spec(_s); _s.loader.exec_module(ko)
o5, o4, o1 = al.o5, al.o4, al.o1
N, CX, CY = o5.N, o5.CX, o5.CY
lum = o4.lum
RENK = {'RUBY': 'RUBY_1264.png', 'SAPPHIRE': 'SAPPHIRE_1264.png'}
OPAK = (0.5, 0.85)


def f_dus_hesap(z):
    zf = z.astype(np.float32)
    Lz = cv2.GaussianBlur(lum(zf), (0, 0), al.DUSUS['sigma'])
    yy, xx = np.mgrid[0:N, 0:N]
    Lref = float(np.median(Lz[np.hypot(xx + 0.5 - CX, yy + 0.5 - CY) < 150]))
    return np.clip((Lz / max(Lref, 1)) ** al.DUSUS['us'], al.DUSUS['alt'], 1.0)


def kontur_maske(M):
    tum = np.maximum.reduce([M[k] for k in M])
    ic = (tum >= 0.5).astype(np.uint8)
    d = cv2.distanceTransform(1 - ic, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    k = np.clip(1.5 + 0.5 - d, 0, 1).astype(np.float32)
    return cv2.GaussianBlur(k, (0, 0), 0.6)


def boya(D, z, opak=0.0, K=None):
    """ornament_motor.boya_motor (deneme 4) ile ayni; opak > 0 ise kontur."""
    E, M, CC, ICP = D['E'], D['M'], D['CC'], D['ICP']
    zf = z.astype(np.float32); out = zf.copy()
    tum = np.maximum.reduce([M[k] for k in M])
    gm_ = cv2.GaussianBlur(tum, (0, 0), al.DIS_GOLGE['sigma'])
    gm_ = cv2.warpAffine(gm_, np.float32([[1, 0, al.DIS_GOLGE['kayma']], [0, 1, al.DIS_GOLGE['kayma']]]), (N, N))
    out = out * (1 - al.DIS_GOLGE['opak'] * gm_)[..., None]
    if opak > 0:
        out = out * (1 - opak * K)[..., None]
    f_dus = f_dus_hesap(z)
    dus_sabit = float(np.median(f_dus[M['sembol'] >= 0.9]))
    sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
    for ad in E:
        if ad == 'sembol':
            cc = np.zeros((N, N, 3), np.float32); rgb_, a_, x, y = E[ad]; h, w = a_.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = rgb_[ya - y:yb - y, xa - x:xb - x]
        else:
            cc = CC[ad].copy()
        cc = np.clip(cc, 0, 255)
        m = M[ad]; q = ICP[ad]
        ic = cv2.GaussianBlur(np.clip(m - sh(m, q['kayma']), 0, 1), (0, 0), q['sigma']) * m
        fd = f_dus if ad == 'sembol' else dus_sabit
        cc = cc * (fd * (1 - q['guc'] * ic))[..., None]
        sat = cc.max(2, keepdims=True); cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
        out = out * (1 - m[..., None]) + cc * m[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkl', required=True); ap.add_argument('--kaynak', required=True); ap.add_argument('--d4', required=True)
    ap.add_argument('--cikti', required=True); ap.add_argument('--font', required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    D = pickle.load(open(a.pkl, 'rb')); M, E = D['M'], D['E']
    K = kontur_maske(M)
    kb = o5.kutu(E, 'kucuk_sol')
    bx = (kb[0] - 12, kb[1] - 20 - 70, kb[2] + 60, kb[3] + 6)
    font = ImageFont.truetype(a.font, 22)
    R = dict(yontem=__doc__.split('Kullanim')[0].strip(), kirpim=list(bx), sonuc={})
    satir = []
    for renk, zf in RENK.items():
        z = o1.zemin_canva(Path(a.kaynak) / zf)
        d4 = np.asarray(Image.open(Path(a.d4) / f'CANCER_LIBRA_{renk}_954.png').convert('RGB'))
        r0 = boya(D, z)
        oz = dict(bayt_ayni=bool(np.array_equal(r0, d4)), en_buyuk_fark=int(np.abs(r0.astype(int) - d4).max()))
        print(renk, 'oz test (kontursuz = e5412718)', oz, flush=True)
        R['sonuc'][renk] = {'oz_test': oz}
        paneller = [('deneme 4 (e5412718)', d4)]
        for op in OPAK:
            paneller.append((f'kontur 1.5 px, opak {op}', boya(D, z, op, K)))
        for ad_p, img in paneller:
            r = ko.olc(img.astype(np.float32), z.astype(np.float32), M)
            R['sonuc'][renk][ad_p] = dict(bant_ana=r['sembol']['aa_bant_zemin_payi_ortanca'], bant_kucuk=r['KUCUK_HAVUZ']['aa_bant_zemin_payi_ortanca'],
                                          halka2px_ana=r['sembol']['zemin_payi_ortanca'], halka2px_kucuk=r['KUCUK_HAVUZ']['zemin_payi_ortanca'],
                                          oge_bant={k: r[k]['aa_bant_zemin_payi_ortanca'] for k in ko.KUCUK},
                                          merkez_altin_yonlu=dict(ana=r['sembol']['merkez_altin_yonlu'], kucuk_sol=r['kucuk_sol']['merkez_altin_yonlu'],
                                                                  kucuk_sag=r['kucuk_sag']['merkez_altin_yonlu']))
            v = R['sonuc'][renk][ad_p]
            print(f'{renk:9s} {ad_p:24s} bant zemin payi ana {v["bant_ana"]:.3f} kucuk {v["bant_kucuk"]:.3f} | 2px ana {v["halka2px_ana"]:.3f} '
                  f'kucuk {v["halka2px_kucuk"]:.3f} | altin yonlu {v["merkez_altin_yonlu"]}', flush=True)
        # 8x gorsel: once | 0.5 | 0.85
        kir = [Image.fromarray(img).crop(bx).resize(((bx[2] - bx[0]) * 8, (bx[3] - bx[1]) * 8), Image.NEAREST) for _, img in paneller]
        w, h = kir[0].size
        c = Image.new('RGB', (3 * w + 2 * 16, h + 34), 'white')
        dr = ImageDraw.Draw(c)
        for i, (im, (ad_p, _)) in enumerate(zip(kir, paneller)):
            c.paste(im, (i * (w + 16), 0)); dr.text((i * (w + 16) + 4, h + 6), f'{renk}: {ad_p}', fill=(20, 20, 20), font=font)
        satir.append(c)
    u = Image.new('RGB', (max(s.width for s in satir), sum(s.height + 20 for s in satir)), 'white'); y = 0
    for s in satir:
        u.paste(s, (0, y)); y += s.height + 20
    u.save(O / 'KONTUR_ON_8x.png')
    (O / 'KONTUR_ON_OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
