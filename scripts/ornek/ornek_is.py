#!/usr/bin/env python3
"""ORNEK URETIMI (Serdar onayi 2 Eki: dikis + sembol ornekleri). Tek sayfa, uretimle AYNI fonksiyon:
renk -> surucu.sayfa_asamasi (sd._dijital_is), wp -> surucu.wp_asamasi. DIKIS_DUZELT ortam degiskeni v1 kodunda
(ornek-dikis-v1) tagline duzeltmesini acar (SONRA). MB islerinde sembol kapisi girdileri yakalanir: kapinin
hizaladigi kaynak / uretim pencereleri (1:1) + olcu. Etsy / musteri / PLATES yazimi YOK.
Cikti: <cikti>/<etiket>/ sayfa jpg, SAYFA json, sembol_<i>_<sol|sag>_{kaynak,uretim}.png, SEMBOL.json"""
import argparse, json, os, shutil, sys, time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'siparis_dijital'))
import surucu                                                      # noqa: E402
import prova                                                       # noqa: E402  (SETLER, ON_TEST_CIFT)


def sembol_kancasi(cik):
    import numpy as np
    from PIL import Image
    import a1_poster
    asil = a1_poster.sembol_kapisi
    say = [0]

    def sk(poster, S, s, merkez, m_src, esik, maske=None, doku=False):
        r = asil(poster, S, s, merkez, m_src, esik, maske=maske, doku=doku)
        i = say[0]; say[0] += 1
        ref = np.asarray(S['ref']).astype(np.uint8); P = np.asarray(poster.convert('RGB')).astype(np.uint8)
        kay = {'sira': i, 'not': 'MB hedef_render: 0 = Cancer-Libra referans render, 1 = siparis sayfasi, 2+ = ikinci deneme',
               'sembol_bant': s['sembol_bant'], 'isim_bant': s['isim_bant'], 'poster_px': list(poster.size), 'yan': {}}
        for y in ('sol', 'sag'):
            v = r[0][y]; x0, y0, x1, y1 = v['kaynak_kutu']
            o = S['oge'][f'sembol_{y}']; g = o['gorsel']
            ex = int(round(merkez[y] - o['w'] / 2)) - (g[0] - x0) + (g[0] - o['gorsel'][0])
            dx, dy = v['dx'], v['dy']
            a = ref[y0:y1, x0:x1]; b = P[y0 + dy:y1 + dy, ex + dx:ex + dx + (x1 - x0)]
            m = np.asarray(m_src)[y0:y1, x0:x1]
            Image.fromarray(a).save(cik / f'sembol_{i}_{y}_kaynak.png'); Image.fromarray(b).save(cik / f'sembol_{i}_{y}_uretim.png')
            np.save(cik / f'sembol_{i}_{y}_maske.npy', m)
            kay['yan'][y] = {**{q: v[q] for q in ('fark', 'iou', 'dx', 'dy', 'gecti', 'kaynak_kutu')},
                             'kaydirma_px': int(ex + dx - x0)}
        (cik / f'SEMBOL_{i}.json').write_text(json.dumps(kay, default=str))
        print('SEMBOL_YAKALA', i, json.dumps(kay['yan'], default=str), flush=True)
        return r
    a1_poster.sembol_kapisi = sk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tur', required=True, choices=('renk', 'wp'))
    ap.add_argument('--renk'); ap.add_argument('--oran'); ap.add_argument('--boy')
    ap.add_argument('--set', required=True); ap.add_argument('--etiket', required=True)
    ap.add_argument('--kod', required=True); ap.add_argument('--kod-ref', default='')
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    cik = Path(a.cikti).resolve() / a.etiket; cik.mkdir(parents=True, exist_ok=True)
    kod = Path(a.kod).resolve(); os.chdir(kod)
    g = {'receipt': 'ORNEK', 'cift': prova.ON_TEST_CIFT[a.set], **prova.SETLER[a.set]}
    t0 = time.time()
    print(f"ORNEK {a.etiket} DIKIS_DUZELT={os.environ.get('DIKIS_DUZELT', '0')} cift {g['cift']} set {a.set}", flush=True)
    sd = surucu.kod_yukle(str(kod))
    if a.tur == 'renk':
        sd.kisisel_hazirla()
        if a.renk == 'MIDNIGHT_BLUE':
            sembol_kancasi(cik)
        arg = SimpleNamespace(kod=str(kod), kod_ref=a.kod_ref, renk=a.renk, oran=a.oran, cikti=str(cik / 'is'))
        rc = surucu.sayfa_asamasi(arg, g)
        for f in (cik / 'is' / a.renk).glob('*.jpg'):
            shutil.copy(f, cik / f'SAYFA_{a.renk}_{a.oran}.jpg')
        for f in (cik / 'is').glob('SAYFA_*.json'):
            shutil.copy(f, cik / f.name)
    else:
        arg = SimpleNamespace(kod=str(kod), kod_ref=a.kod_ref, boy=a.boy, cikti=str(cik / 'is'))
        rc = surucu.wp_asamasi(arg, g)
        for f in (cik / 'is').glob('WP_*.jpg'):
            shutil.copy(f, cik / f.name)
        for f in (cik / 'is').glob('OZET_WP_*.json'):
            shutil.copy(f, cik / f.name)
    shutil.rmtree(cik / 'is', ignore_errors=True)
    print(f'ORNEK_BITTI {a.etiket} rc {rc} {time.time() - t0:.0f} sn', sorted(p.name for p in cik.iterdir()), flush=True)


if __name__ == '__main__':
    main()
