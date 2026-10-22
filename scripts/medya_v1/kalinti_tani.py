#!/usr/bin/env python3
"""SALT OKUR tani (30 Eyl 2026): ARIES_SCORPIO MB 11x14 (onayli profil) isim_kalinti 2 ince kalinti
(15x1, 3x1 px, y=3093). Temizlik (isim_bandi_temizle) bu pikselleri neden birakti: her kalinti pikselinde
temizlik oncesi / sonrasi RGB, temizlik iz haritasi (altin / soluk), koruma (Yb), alan (Ab), dolgu bolgesi (R),
Ef ve kapinin dL degeri loga basilir. Hicbir yere YAZMAZ."""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main():
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    kay = {}
    asil = sd.isim_bandi_temizle

    def sar(out, yeni, olcum, ham=False, alan=None):
        o2, t = asil(out, yeni, olcum, ham=ham, alan=alan)
        kay.update({'once': out, 'sonra': o2, 'yeni': yeni, 'olcum': olcum, 'ham': ham, 'alan': alan, 't': t})
        return o2, t
    sd.isim_bandi_temizle = sar
    for cift, renk, boy in (('ARIES_SCORPIO', 'MIDNIGHT_BLUE', '11x14'), ('CANCER_LIBRA', 'MIDNIGHT_BLUE', '11x14')):
        kay.clear()
        x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod', 'isim1': 'EMILY', 'isim2': 'JAMES',
                          'mesaj': 'It Began With a Kiss in the Rain'})
        x['receipt'] = f'KALTANI_{cift}'; x['sayfa'] = no[cift]
        yol = sd.pod_kaynak(cift, renk, boy)
        with Image.open(yol) as im:
            x['hedef_px'] = list(im.size)
        is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
        s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
        g = s.get('isim_kalinti_kapisi') or {}
        r = {'cift': cift, 'kapilar': s.get('kapilar'), 'kalintilar': g.get('kalintilar'), 'esikler': g.get('esikler'),
             'ham': kay.get('ham'), 'alan_var': kay.get('alan') is not None,
             'temizlik': {q: v for q, v in (kay.get('t') or {}).items() if q != 'kenar'}}
        if kay and g.get('kalintilar'):
            once, sonra, t = kay['once'], kay['sonra'], kay['t']
            H, Wd = once.shape[:2]; k = Wd / 2400.0
            r0, r1 = t['satir']; c0, c1 = t['sutun']
            Yt = sd._yeni_tam(kay['yeni'], (Wd, H), ham=kay['ham'])
            Yg = sd._yeni_tam(kay['yeni'], (Wd, H), 0 if kay['ham'] else 1, ham=kay['ham'])
            Ab = sd._alan_tam(kay['alan'], (Wd, H))
            kes = once[r0:r1, c0:c1]; Yb = Yt[r0:r1, c0:c1]
            altin, soluk, dL, ws = sd._iz_haritasi(kes, k, Yb, t['esik'])
            B = np.asarray(Image.open(io_yol(is_dir)).convert('RGB')).astype(np.float32) if io_yol(is_dir) else None
            gal, gso, gdL, _ = sd._iz_haritasi(sonra[r0:r1, c0:c1], k, None if not kay['ham'] else Yb, g.get('esikler'))
            noktalar = []
            for z in g['kalintilar'][:2]:
                for dx in range(0, z['w'], max(z['w'] // 4, 1)):
                    X, Y = z['x'] + dx, z['y']
                    yy, xx = Y - r0, X - c0
                    noktalar.append({'x': X, 'y': Y, 'once': [round(float(v)) for v in once[Y, X]],
                                     'sonra': [round(float(v)) for v in sonra[Y, X]],
                                     'baski': None if B is None else [round(float(v)) for v in B[Y, X]],
                                     'iz_altin': bool(altin[yy, xx]), 'iz_soluk': bool(soluk[yy, xx]),
                                     'temizlik_dL': round(float(dL[yy, xx]), 1), 'Yb': bool(Yb[yy, xx]),
                                     'Yg_kapi': bool(Yg[Y, X]), 'Ab': None if Ab is None else bool(Ab[Y, X]),
                                     'kapi_dL': round(float(gdL[yy, xx]), 1), 'kapi_altin': bool(gal[yy, xx])})
            r['noktalar'] = noktalar
        yol.unlink(missing_ok=True)
        print('KALTANI', json.dumps(r, ensure_ascii=False, default=str), flush=True)


def io_yol(d):
    c = sorted(Path(d).rglob('BASKI_*.jpg')) + sorted(Path(d).rglob('*.jpg'))
    return c[0] if c else None


if __name__ == '__main__':
    main()
