#!/usr/bin/env python3
"""KENAR ZEMIN PAYI (ALTIN_MOTOR deneme 5 on olcumu, Merkez / Serdar 3 Kas). Yalniz olcum; uretim yok.
Kenar halkasi: oge cekirdeginin (maske alfa >= 0.9) 2 px disi (5 x 5 elips genisletme - cekirdek); baska ogenin maskesi (> 0.02) disarida.
Karisim modeli (sRGB, butunlesme sRGB'de alfa karisimi oldugu icin): p = w_a * G + w_z * Z + w_k * 0
  G = ogenin YEREL cekirdek rengi (cekirdek pikselleri sigma 3 normalize bulanik), Z = o noktadaki GERCEK zemin (zemin_canva, golgesiz),
  0 = notr koyu (dis golge / kontur golgesi zemini notr karartir; notr karartma = Z ile siyahin karisimi).
  Cozum: piksel basina en kucuk kareler (w_a, w_z >= 0); w_k = max(0, 1 - w_a - w_z). Zemin payi = w_z / (w_a + w_z + w_k).
Ek (capraz kontrol, Merkez olcusu): renk cekirdegi R > 150, G > 110, B < 100 (oge maskesi > 0.5 icinde); kenar = 2 px disi;
  altin yonlu = R > G > B ve G - B > 15; oran = altin yonlu / kenar.
Kullanim: ornament_kenar_olc.py --pkl KATMAN.pkl --kaynak DIR --surum AD=DIR [--surum ...] --cikti JSON"""
import argparse
import importlib.util
import json
import pickle
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o1 = al.o1
KUCUK = ('kucuk_sol', 'kucuk_sag', 'isim1', 'isim2', 'tarih', 'sonsuz', 'halka')
EL5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


def halka_ve_cekirdek(M, ad):
    core = M[ad] >= 0.9
    ring = (cv2.dilate(core.astype(np.uint8), EL5) > 0) & ~core
    diger = np.maximum.reduce([M[k] for k in M if k != ad])
    return core, ring & (diger <= 0.02)


def zemin_payi(rgb, z, core, ring):
    c = core.astype(np.float32)
    G = cv2.GaussianBlur(rgb * c[..., None], (0, 0), 3) / np.maximum(cv2.GaussianBlur(c, (0, 0), 3), 1e-4)[..., None]
    p, g, zz = rgb[ring], G[ring], z[ring]
    gg, gz, zz2 = (g * g).sum(1), (g * zz).sum(1), (zz * zz).sum(1)
    pg, pz = (p * g).sum(1), (p * zz).sum(1)
    det = gg * zz2 - gz * gz
    wa = np.where(np.abs(det) > 1e-6, (pg * zz2 - pz * gz) / np.where(np.abs(det) > 1e-6, det, 1), 0)
    wz = np.where(np.abs(det) > 1e-6, (pz * gg - pg * gz) / np.where(np.abs(det) > 1e-6, det, 1), 0)
    a_only = np.maximum(pg / np.maximum(gg, 1e-6), 0); z_only = np.maximum(pz / np.maximum(zz2, 1e-6), 0)
    wa, wz = np.where(wz < 0, a_only, wa), np.where(wz < 0, 0, wz)
    wa, wz = np.where(wa < 0, 0, wa), np.where(wa < 0, z_only, wz)
    wk = np.maximum(0, 1 - wa - wz)
    pay = wz / np.maximum(wa + wz + wk, 1e-6)
    art = p - (wa[:, None] * g + wz[:, None] * zz)
    return pay, float(np.sqrt((art ** 2).mean()))


def merkez_orani(rgb, M, ad):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    cc = (r > 150) & (g > 110) & (b < 100) & (M[ad] > 0.5)
    ring = (cv2.dilate(cc.astype(np.uint8), EL5) > 0) & ~cc
    diger = np.maximum.reduce([M[k] for k in M if k != ad])
    ring &= diger <= 0.02
    yon = (r > g) & (g > b) & (g - b > 15)
    return float(yon[ring].mean()) if ring.any() else None, int(ring.sum())


def olc(rgb, z, M):
    out, havuz, havuz_b, havuz_e = {}, [], [], []
    for ad in ('sembol',) + KUCUK:
        core, ring = halka_ve_cekirdek(M, ad)
        pay, rms = zemin_payi(rgb, z, core, ring)
        mo, mn = merkez_orani(rgb, M, ad)
        bant = ring & (M[ad] > 0.05)                                   # yalniz kenar yumusatma bandi (oge alfasi 0.05 - 0.9)
        pay_b, _ = zemin_payi(rgb, z, core, bant)
        out[ad] = dict(zemin_payi_ortanca=round(float(np.median(pay)), 4), zemin_payi_p75=round(float(np.percentile(pay, 75)), 4),
                       kenar_piksel=int(ring.sum()), model_rms=round(rms, 2),
                       aa_bant_zemin_payi_ortanca=round(float(np.median(pay_b)), 4) if pay_b.size else None, aa_bant_piksel=int(bant.sum()),
                       aa_bant_beklenen_ortanca=round(float(np.median(1 - M[ad][bant])), 4) if bant.any() else None, merkez_altin_yonlu=round(mo, 3) if mo is not None else None,
                       merkez_kenar_piksel=mn)
        if ad != 'sembol':
            havuz.append(pay); havuz_b.append(pay_b); havuz_e.append(1 - M[ad][bant])
    hv = np.concatenate(havuz)
    out['KUCUK_HAVUZ'] = dict(zemin_payi_ortanca=round(float(np.median(hv)), 4), zemin_payi_p75=round(float(np.percentile(hv, 75)), 4),
                              kenar_piksel=int(hv.size), aa_bant_zemin_payi_ortanca=round(float(np.median(np.concatenate(havuz_b))), 4),
                              aa_bant_beklenen_ortanca=round(float(np.median(np.concatenate(havuz_e))), 4))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkl', required=True); ap.add_argument('--kaynak', required=True); ap.add_argument('--cikti', required=True)
    ap.add_argument('--surum', action='append', required=True)
    a = ap.parse_args()
    D = pickle.load(open(a.pkl, 'rb')); M = D['M']
    K = Path(a.kaynak)
    R = dict(yontem=__doc__.split('Kullanim')[0].strip(), sonuc={})
    for s in a.surum:
        ad, d = s.split('=', 1)
        R['sonuc'][ad] = {}
        for renk, zf in al.RENKLER:
            z = o1.zemin_canva(K / zf).astype(np.float32)
            rgb = np.asarray(Image.open(Path(d) / f'CANCER_LIBRA_{renk}_954.png').convert('RGB')).astype(np.float32)
            r = olc(rgb, z, M)
            R['sonuc'][ad][renk] = r
            print(f'{ad:10s} {renk:9s} AA bant zemin payi: sembol {r["sembol"]["aa_bant_zemin_payi_ortanca"]} (geometrik beklenen {r["sembol"]["aa_bant_beklenen_ortanca"]}) | '
                  f'kucuk {r["KUCUK_HAVUZ"]["aa_bant_zemin_payi_ortanca"]} (beklenen {r["KUCUK_HAVUZ"]["aa_bant_beklenen_ortanca"]})', flush=True)
            print(f'{ad:10s} {renk:9s} zemin payi: sembol {r["sembol"]["zemin_payi_ortanca"]:.3f} | kucuk havuz {r["KUCUK_HAVUZ"]["zemin_payi_ortanca"]:.3f} | '
                  + ' '.join(f'{k} {r[k]["zemin_payi_ortanca"]:.2f}' for k in KUCUK)
                  + f' || merkez altin yonlu: sembol {r["sembol"]["merkez_altin_yonlu"]} kucuk_sol {r["kucuk_sol"]["merkez_altin_yonlu"]} '
                  f'kucuk_sag {r["kucuk_sag"]["merkez_altin_yonlu"]} | rms sembol {r["sembol"]["model_rms"]} kucuk_sol {r["kucuk_sol"]["model_rms"]}', flush=True)
    Path(a.cikti).write_text(json.dumps(R, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
