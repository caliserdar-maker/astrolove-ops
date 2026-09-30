#!/usr/bin/env python3
"""SALT OKUR tani (30 Eyl 2026): GEMINI_LEO Deep Black olcek kapisi konum 1.18 px (11x14) / 1.13 (16x20);
e62e35d'de de ayni (kapi-olc 36744803676). Isim satiri 2400 render ile hi-res render'da farkli yerlesiyor.
Her poster_kur cagrisinda (2400 ve hi-res) yerlesim girdileri loga basilir: NORM_W, isim plakasi genislikleri,
sonsuz ogesinin kutusu (w, gorsel, pay), bosluk, x konumlari. Farklar 2400 birimine bolunur.
Hicbir yere YAZMAZ."""
import argparse, json, sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--isler', default='GEMINI_LEO:DEEP_BLACK:11x14;GEMINI_LEO:DEEP_BLACK:16x20;'
                                       'CANCER_LEO:DEEP_BLACK:11x14;ARIES_SCORPIO:DEEP_BLACK:11x14')
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    p16 = P_ed.p16
    asil = p16.poster_kur
    kay = []

    def sar(s, S, isimler, tagline):
        out = asil(s, S, isimler, tagline)
        t, bilgi, merkez, x, _ = out
        inf = S['oge']['sonsuz']
        kay.append({'W': t.width, 'bosluk': s.get('bosluk'), 'genislik': bilgi.get('genislik'),
                    'punto': bilgi.get('punto'), 'olcek': bilgi.get('olcek'), 'satir': bilgi.get('satir'),
                    'x': {q: round(float(v), 2) for q, v in x.items()},
                    'inf': {'w': inf.get('w'), 'gorsel': [round(float(v), 2) for v in inf.get('gorsel', [])],
                            'pay': [round(float(v), 2) for v in inf.get('pay', [])],
                            'maske': list(inf['maske'].shape) if 'maske' in inf else None},
                    'sembol': {y: {'w': S['oge'][f'sembol_{y}'].get('w'),
                                   'gorsel': [round(float(v), 2) for v in S['oge'][f'sembol_{y}'].get('gorsel', [])]}
                               for y in ('sol', 'sag')}})
        return out
    p16.poster_kur = sar
    for is_ in [x for x in a.isler.split(';') if x]:
        cift, renk, boy = is_.split(':')
        kay.clear()
        x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod',
                          'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'})
        x['receipt'] = f'OLCEKTANI_{cift}_{renk}_{boy}'; x['sayfa'] = no[cift]
        yol = sd.pod_kaynak(cift, renk, boy)
        with Image.open(yol) as im:
            x['hedef_px'] = list(im.size)
        is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
        s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
        r = {'cift': cift, 'renk': renk, 'boy': boy, 'kalan': sorted(g for g, v in (s.get('kapilar') or {}).items() if v is False),
             'olcek_kapisi': {q: (s.get('olcek_kapisi') or {}).get(q) for q in ('konum_fark_px', 'kenar_fark_px', 'fark', 'k')},
             'cagri': kay[:]}
        if len(kay) >= 2:
            k = kay[-1]['W'] / kay[0]['W']
            a0, a1 = kay[0], kay[-1]
            r['fark_2400'] = {
                'k': round(k, 4),
                'genislik': [round(a1['genislik'][i] / k - a0['genislik'][i], 2) for i in (0, 1)],
                'inf_w': round(a1['inf']['w'] / k - a0['inf']['w'], 2),
                'inf_gorsel': [round(a1['inf']['gorsel'][i] / k - a0['inf']['gorsel'][i], 2) for i in range(len(a0['inf']['gorsel']))],
                'inf_pay': [round(a1['inf']['pay'][i] / k - a0['inf']['pay'][i], 2) for i in range(len(a0['inf']['pay']))],
                'bosluk': round(a1['bosluk'] / k - a0['bosluk'], 2),
                'x': {q: round(a1['x'][q] / k - a0['x'][q], 2) for q in a0['x']},
                'satir': round(a1['satir'] / k - a0['satir'], 2)}
        yol.unlink(missing_ok=True)
        print('OLCEKTANI', json.dumps(r, ensure_ascii=False, default=str), flush=True)


if __name__ == '__main__':
    main()
