#!/usr/bin/env python3
"""SALT OKUR tani (29 Eyl 2026, Serdar onayi): Leo / Libra Deep Black mesaj_murekkep FAIL
(dE 10.4-11.5 > 9.2) ve ARIES_LEO Pure White. Hicbir yere YAZMAZ: sonuc yalniz loga basilir.

Her (cift, renk) icin sahte isimli (EMILY / JAMES) render uretilir ve olculur:
  - kaynak Canva dosyasinda kapi (orijinal)
  - render'da kapi (hattaki olcum) + isim bandi sol yari / sag yari / sonsuz ayri murekkep rengi
  - S['prof'] sol / sag profil medyani, tagline'a giden kuyruk_duzlestir(sol) medyani ve kesim satiri
Kontrol: ARIES_SCORPIO DB (PASS).
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import mesaj_kapisi as mk                                        # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ISLER = [('LEO_LEO', 'DEEP_BLACK'), ('ARIES_LEO', 'DEEP_BLACK'), ('ARIES_LEO', 'PURE_WHITE'),
         ('LEO_LIBRA', 'DEEP_BLACK'), ('LIBRA_LIBRA', 'DEEP_BLACK'), ('LIBRA_VIRGO', 'DEEP_BLACK'),
         ('ARIES_SCORPIO', 'DEEP_BLACK'), ('AQUARIUS_LEO', 'DEEP_BLACK')]
BOY = '11x14'
MESAJ = 'It Began With a Kiss in the Rain'


def rgb(x):
    return [int(round(float(v))) for v in x]


def parca(a, bant, x0, x1, k):
    """Isim bandinda [x0, x1) sutunlarinda murekkep cekirdegi (mk.murekkep ile ayni kural)."""
    y0, y1 = int(bant[0] * k), int(bant[1] * k)
    p = int(0.5 * (y1 - y0))
    kes = a[max(y0 - p, 0):y1 + p, int(x0):int(x1)].astype(np.float32)
    z = np.median(kes.reshape(-1, 3), 0)
    d = np.abs(kes - z).max(2)
    m = d > max(40.0, 0.5 * float(np.percentile(d, 99.5)))
    return rgb(np.median(kes[m], 0)) if m.any() else None, int(m.sum())


def main():
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    p16 = P_ed.p16
    for cift, renk in ISLER:
        r = {'cift': cift, 'renk': renk}
        try:
            ed = sd.RENK_ED[renk]
            yol = sd.pod_kaynak(cift, renk, BOY)
            kb = yol.read_bytes()
            with Image.open(yol) as im:
                hedef = list(im.size)
            kay = {}
            asil = p16.poster_kur

            def sar(s, S, isimler, tagline):
                kay['S'] = S
                return asil(s, S, isimler, tagline)
            p16.poster_kur = sar
            try:
                x = sd.normalize({'cift': cift, 'renk': renk, 'boy': BOY, 'urun': 'pod',
                                  'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': MESAJ})
                poster, bi, ek = sd.render_et(ed, x['oran'], no[cift], kb, ('EMILY', 'JAMES'), MESAJ,
                                              P_blue, P_ed, cift, ref_boy=BOY, hedef_en=hedef[0], boy=BOY)
            finally:
                p16.poster_kur = asil
            if poster is None:
                r['hata'] = bi.get('durum') or bi.get('hata'); print('TANI', json.dumps(r)); continue
            o = bi['olcum']; k = poster.width / 2400.0
            a = np.asarray(poster.convert('RGB'))
            r['kapi_render'] = bi.get('mesaj_kapisi')
            ref = P_ed.p11.norm(Image.open(yol).convert('RGB'))[0]
            r['kapi_kaynak'] = mk.kapi(ref, o['isim_bant'], o['tag_bant'])
            W = a.shape[1]; orta = W / 2
            r['render_sol_yari'] = parca(a, o['isim_bant'], W * 0.05, orta - 0.06 * W, k)
            r['render_sonsuz'] = parca(a, o['isim_bant'], orta - 0.05 * W, orta + 0.05 * W, k)
            r['render_sag_yari'] = parca(a, o['isim_bant'], orta + 0.06 * W, W * 0.95, k)
            S = kay.get('S')
            if S is not None and 'prof' in S:
                ps = np.asarray(S['prof']['sol'], np.float32); pg = np.asarray(S['prof']['sag'], np.float32)
                pf, son = P_ed.p12.kuyruk_duzlestir(ps)
                L = ps @ mk.LUMA
                r['prof'] = {'sol_med': rgb(np.median(ps, 0)), 'sag_med': rgb(np.median(pg, 0)),
                             'tag_med': rgb(np.median(pf, 0)), 'n': len(ps), 'kesim': int(son),
                             'Lmax': round(float(L.max()), 1), 'L_ust20': round(float(L[:len(L) // 5].mean()), 1),
                             'L_alt20': round(float(L[-len(L) // 5:].mean()), 1),
                             'sol_satir_L': [round(float(v)) for v in L[::max(len(L) // 12, 1)]]}
            yol.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
        print('TANI', json.dumps(r, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
