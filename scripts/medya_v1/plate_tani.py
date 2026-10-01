#!/usr/bin/env python3
"""SALT OKUR plate tanisi (1 Eki 2026, siparis 4188621967 kosusu 36867636749): CANCER_LEO DEEP_BLACK 2x3
'PLATE KIRLI: 2x3.png eski slogani iceriyor (slogan glifi yok (0 px))'. Ayni plate_slogan_kapisi (degismeden)
cift x renk x dijital boy icin kosar; ham olcum (sayfa_olc bantlari, glif px, glif farkli payi, zemin p50) ve
FAIL hucrelerde 1:1 kesit (kaynak / plate / |kaynak - plate| x4, slogan + isim bolgesi) uretir.
Hicbir plate'i ya da kaynagi DEGISTIRMEZ; cikti yerel klasor (workflow Drive TEMP/PLATE_TANI'ya kopyalar)."""
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
BOYLAR = ('16x20', '18x24', '24x36', '11x14', 'A2')


def olc(src, plate, ed):
    import pilot11
    eu = sd._mod('edisyon_uret')
    sd.olcek_kur(2400)
    r = {}
    for ad, m in (('yerel', None if ed == 'blue' else (lambda L, acik: eu.edisyon_maske(L, acik))),
                  ('plate_fark', sd.plate_fark_maskesi(plate))):
        try:
            o = pilot11.sayfa_olc(src, maske=m)
            r[ad] = {q: o.get(q) for q in ('isim_bant', 'tag_bant', 'tag_x', 'sembol_bant') if q in o}
        except SystemExit as e:
            r[ad] = {'hata': str(e)[:200]}
    return r


def kesit(src, plate, cik, ad, bant):
    """bant: 2400 biriminde [y0, y1]; tam cozunurlukte 1:1 kesit (kaynak, plate, |fark| x4) alt alta."""
    A = Image.open(src).convert('RGB')
    P = Image.open(plate).convert('RGB')
    if P.size != A.size:
        P = P.resize(A.size, Image.LANCZOS)
    k = A.width / 2400.0
    y0, y1 = max(0, int((bant[0] - 40) * k)), min(A.height, int((bant[1] + 40) * k))
    a = np.asarray(A.crop((0, y0, A.width, y1))).astype(np.int16)
    p = np.asarray(P.crop((0, y0, A.width, y1))).astype(np.int16)
    f = np.clip(np.abs(a - p) * 4, 0, 255)
    Image.fromarray(np.concatenate([a, p, f], 0).astype(np.uint8)).save(cik / ad, 'JPEG', quality=95, subsampling=0)
    return [y0, y1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ciftler', default='CANCER_LEO')
    ap.add_argument('--renkler', default=','.join(sd.RENKLER))
    ap.add_argument('--boylar', default=','.join(BOYLAR))
    ap.add_argument('--kesit', default='fail', choices=('fail', 'hep', 'yok'))
    ap.add_argument('--cikti', default='plate_tani')
    a = ap.parse_args()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    sd.kisisel_hazirla()
    P_ed = sd.EdisyonPoster()
    isler = [(c, r, b) for c in a.ciftler.split(',') for r in a.renkler.split(',') for b in a.boylar.split(',')]
    fo = open(cik / 'PLATE_TANI.jsonl', 'w')
    for n, (cift, renk, boy) in enumerate(isler, 1):
        ed = sd.RENK_ED[renk]; oran = sd.BOY[boy][0]
        r = {'cift': cift, 'renk': renk, 'boy': boy, 'edisyon': ed, 'oran': oran}
        try:
            src = sd.pod_kaynak(cift, renk, boy)
            plate = Path(P_ed.plate(ed, oran, boy))
            r['plate'] = plate.name
            with Image.open(src) as im:
                r['kaynak_px'] = list(im.size)
            pk = sd.plate_slogan_kapisi(src.read_bytes(), plate, ed)
            r['kapi'] = {q: pk.get(q) for q in ('gecti', 'sebep', 'glif_px', 'glif_farkli_payi', 'fark_p50',
                                                'tag_bant', 'tag_x', 'olcum')}
            r['zemin_uyumu'] = sd.zemin_uyumu(src.read_bytes(), plate)
            r['olcum'] = olc(src, plate, ed)
            if a.kesit == 'hep' or (a.kesit == 'fail' and not pk.get('gecti')):
                bb = [v for o in r['olcum'].values() for q in ('isim_bant', 'tag_bant') for v in [o.get(q)] if v]
                bant = [min(v[0] for v in bb), max(v[1] for v in bb)] if bb else [2300, 3500]
                r['kesit'] = kesit(src, plate, cik, f'KESIT_{cift}_{renk}_{boy}.jpg', bant)
            src.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
        fo.write(json.dumps(r, default=str) + '\n'); fo.flush()
        print(f"[{n}/{len(isler)}] {cift} {renk} {boy}: "
              f"{'PASS' if (r.get('kapi') or {}).get('gecti') else 'FAIL'} {json.dumps(r, default=str)}", flush=True)


if __name__ == '__main__':
    main()
