#!/usr/bin/env python3
"""SALT OKUR tani (1 Eki): olcek kapisi FAIL hucrelerinde isim satiri penceresi. Her hucre icin tek PNG:
ust = onayli 2400 render (p0) baski olcegine buyutulmus, orta = BASKI, alt = |fark| (x4). Ayrica satir_olc_alt
ciktilari (g0 / g1). Drive'a yalniz --kok (TEMP/OLCEK_TANI)."""
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--isler', required=True)
    ap.add_argument('--kok', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    d = sd.W / '_olcek_gorsel'; d.mkdir(parents=True, exist_ok=True)
    for is_ in [x for x in a.isler.split(';') if x]:
        cift, renk, boy = is_.split(':')
        sd._TANI = {}
        x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod', 'isim1': 'EMILY', 'isim2': 'JAMES',
                          'mesaj': 'It Began With a Kiss in the Rain'})
        x['receipt'] = f'OGT_{cift}_{renk}_{boy}'; x['sayfa'] = no[cift]
        yol = sd.pod_kaynak(cift, renk, boy)
        with Image.open(yol) as im:
            x['hedef_px'] = list(im.size)
        is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
        s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
        T = sd._TANI
        baski, p0 = T['baski'], T['p0']
        bant = s['olcum']['isim_bant']
        k = baski.width / p0.width
        y0, y1 = int((bant[0] - 25) * k), int((bant[1] + 25) * k)
        B = np.asarray(baski.convert('RGB').crop((0, y0, baski.width, y1))).astype(np.float32)
        P = np.asarray(p0.convert('RGB').resize(baski.size, Image.BICUBIC).crop((0, y0, baski.width, y1))).astype(np.float32)
        D = np.clip(np.abs(B - P) * 4, 0, 255)
        s3 = np.concatenate([P, B, D], 0).astype(np.uint8)
        im = Image.fromarray(s3)
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        im.save(d / f'{cift}_{renk}_{boy}.png')
        sd.olcek_kur(baski.width); g1 = sd.satir_olc_alt(baski, bant, k)
        sd.olcek_kur(2400); g0 = sd.satir_olc_alt(p0, bant, 1.0)
        print('OGT', json.dumps({'cift': cift, 'renk': renk, 'boy': boy, 'k': round(k, 4),
                                 'olcek': (s.get('olcek_kapisi') or {}).get('fark'), 'g0': g0, 'g1': g1},
                                default=str), flush=True)
        yol.unlink(missing_ok=True)
    sd.rc('copy', str(d), a.kok, timeout=1800)


if __name__ == '__main__':
    main()
