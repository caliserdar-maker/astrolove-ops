#!/usr/bin/env python3
"""SALT OKUR TARAMA (1 Eki 2026, Serdar; siparis 4188621967 hayalet yazi): eski metin izi kapisi
(siparis_dosyasi.eski_metin_izi_kapisi) her (cift, renk, boy) icin. Siparis ciktisinda mesaj bandinin
eski slogan silinmis zemini = medyan PLATE'in o bandi; plate'te iz varsa o plate'i kullanan HER siparis
etkilenir. Olcum: cift POD_PRINT sayfasindan eski glif maskesi + bant (plate_slogan_kapisi olcumu), plate
o maskede yeni metin YOK kabuluyle (bos maske). PLATES / POD_PRINT'e YAZMA YOK.
Cikti: <cikti>/IZ_TARA_<parca>.jsonl"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
BOYLAR = ('8x10', '11x14', '12x16', '12x18', '16x20', '16x24', '18x24', '20x30', '24x36',
          '30x40', 'A4', 'A3', 'A2')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ciftler', default='')
    ap.add_argument('--renkler', default=','.join(sd.RENKLER))
    ap.add_argument('--boylar', default=','.join(BOYLAR))
    ap.add_argument('--parca', default='0/1')
    ap.add_argument('--cikti', default='iz_tara')
    a = ap.parse_args()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    sd.kisisel_hazirla()
    P_ed = sd.EdisyonPoster()
    _, ciftler = sd.sayfa_no_tablosu()
    if a.ciftler:
        ciftler = [c for c in a.ciftler.split(',') if c]
    i, n = (int(v) for v in a.parca.split('/'))
    isler = [(c, r, b) for r in a.renkler.split(',') for b in a.boylar.split(',') for c in ciftler][i::n]
    fo = open(cik / f'IZ_TARA_{i}.jsonl', 'w')
    T0 = time.time()
    for k, (cift, renk, boy) in enumerate(isler, 1):
        r = {'cift': cift, 'renk': renk, 'boy': boy}
        try:
            ed = sd.RENK_ED[renk]; oran = sd.BOY[boy][0]
            src = sd.pod_kaynak(cift, renk, boy)
            plate = Path(P_ed.plate(ed, oran, boy))
            kb = src.read_bytes()
            pk = sd.plate_slogan_kapisi(kb, plate, ed)
            r['plate'] = plate.name
            r['plate_slogan'] = {q: pk.get(q) for q in ('gecti', 'glif_farkli_payi', 'sebep')}
            if pk.get('tag_bant'):
                with Image.open(plate) as im:
                    pl = im.convert('RGB')
                bos = np.zeros((pl.height, pl.width), bool)
                iz = sd.eski_metin_izi_kapisi(pl, kb, pk['tag_bant'], pk['tag_x'], bos)
                r['iz'] = {q: iz.get(q) for q in ('gecti', 'fazla', 'iz_ort', 'taban_ort', 'eski_glif_px',
                                                  'kaynak_glif_kontrast', 'sebep')}
            else:
                r['iz'] = {'gecti': None, 'sebep': 'mesaj bandi olculemedi'}
            src.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
        fo.write(json.dumps(r) + '\n'); fo.flush()
        g = time.time() - T0
        iz = r.get('iz') or {}
        print(f"[{k}/{len(isler)}] {cift} {renk} {boy}: iz {'PASS' if iz.get('gecti') else 'FAIL' if iz.get('gecti') is False else '-'}"
              f" fazla={iz.get('fazla')} {r.get('hata') or ''} | gecen {g:.0f}s kalan ~{g / k * (len(isler) - k):.0f}s "
              f"%{100 * k // len(isler)}", flush=True)


if __name__ == '__main__':
    main()
