#!/usr/bin/env python3
"""Hat yamasi testi (sembol alt bandi; scripts/pod/hat_yama/sembol_alt_bant.patch). SIPARIS HATTINA UYGULANMAZ:
yama yalniz bu surecte a1_poster.olcum_duzelt uzerine konur; siparis-baski-v1 / kisisel-v1 degismez (merge Serdar onayiyla).

Kok neden (28 Eyl, ARIES_LIBRA / AQUARIUS_LIBRA IN): olcum_duzelt sembol bandini yalniz YUKARI genisletir. Terazi'nin alt
cubugu bandin altinda kalir; pilot16.poster_kur sembolu yeni ismin murekkep merkezine ortalarken cubuk yerinde kalir.
Yama: bandin altinda, isim bandindan once, her kumesi bir sembolun x araligiyla ortusen bantlar sembole katilir.

Cift basina (Midnight Blue 11x14, POD_PRINT kaynagi, onayli sarmalayici a1_poster.Poster):
  - sayfa olcumu iki kez: ONCE (hat) ve SONRA (yama). Olcum ayniysa render girdisi aynidir.
  - 3 isim seti (KISA / ORTA / UZUN) SONRA ile render; kapilar: sembol (sol/sag fark + iou), kalinti, temiz ara zemin.
  - ONCE ile render: olcum degistiyse 3 set; degismediyse KISA set (birebir ayni olmali: piksel farki 0).
Cikti (--out): SONUC_<CIFT>.json + kirpim PNG'leri (sembol + isim bandi) -> birlestir: TEMAS_<SET>.jpg, ONCE_SONRA.jpg, RAPOR.md.
Kullanim (cwd = siparis-baski-v1 checkout'u):
  sembol_yama_test.py uret PARCA TOPLAM YAMALI_A1_POSTER.py OUT
  sembol_yama_test.py birlestir GIRDI_DIZINI OUT
"""
import ast
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SETLER = {'KISA': ('MIA', 'NOAH', 'Since 2019'),
          'ORTA': ('SOPHIE', 'OLIVER', 'Where Our Story Began'),
          'UZUN': ('ALEXANDERRR', 'MAXIMILIANO', "I'd Choose You in Every Lifetime")}
REF_CIFT = 'CANCER_LIBRA'
HATA = {'sembol': False, 'kalinti': False, 'temiz_ara': False, 'sol': {'iou': None}, 'sag': {'iou': None}}


def kirpim(p, o, cik):
    """sembol bandi ustu - 90 .. isim bandi alti + 15, tam genislik -> 900 px genislik."""
    y0, y1 = max(o['sembol_bant'][0] - 90, 0), min(o['isim_bant'][1] + 15, p.height)
    k = p.convert('RGB').crop((0, y0, p.width, y1))
    k.resize((900, round(900 * k.height / k.width)), Image.LANCZOS).save(cik)


def kapi_ozet(bi):
    sk = bi['sembol_kapisi']
    return {'sembol': bool(sk['gecti']), 'kalinti': bool(bi['kalinti_kapisi']['gecti']),
            'temiz_ara': bool(bi['temiz_ara_kapisi']['gecti']),
            'sol': {k: sk['sol'][k] for k in ('fark', 'iou', 'dx')}, 'sag': {k: sk['sag'][k] for k in ('fark', 'iou', 'dx')}}


def uret(parca, toplam, yamali, out):
    sys.path.insert(0, str(Path('scripts/medya_v1').resolve()))
    import siparis_dosyasi as sd
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sd.kisisel_hazirla()
    import a1_poster
    ns = dict(vars(a1_poster))
    for n in ast.parse(Path(yamali).read_text()).body:
        if isinstance(n, ast.FunctionDef) and n.name == 'olcum_duzelt':
            exec(compile(ast.Module([n], []), 'yama', 'exec'), ns)
    HAT, YAMA = a1_poster.olcum_duzelt, ns['olcum_duzelt']
    no, ciftler = sd.sayfa_no_tablosu()
    benim = ciftler[parca::toplam]
    P_ed = sd.EdisyonPoster(); PB = sd.BluePoster()
    PB.plate_kur(P_ed, '11x14', '11x14')
    sd.olcek_kur(2400)
    a1_poster.olcum_duzelt = HAT                                  # referans (boy tavani) hat olcumuyle
    ref = sd.pod_kaynak(REF_CIFT, 'MIDNIGHT_BLUE', '11x14').read_bytes()
    PB.P(ref, no[REF_CIFT], 'blue', '11x14', SETLER['ORTA'][:2], SETLER['ORTA'][2], referans=True)
    t0 = time.time()
    print(f'parca {parca}/{toplam}: {len(benim)} cift: {" ".join(benim)}', flush=True)
    for i, c in enumerate(benim, 1):
        kb = sd.pod_kaynak(c, 'MIDNIGHT_BLUE', '11x14').read_bytes()
        a1_poster.olcum_duzelt = HAT; B0 = PB.P.sayfa_kur(kb, no[c], 'blue', '11x14')
        a1_poster.olcum_duzelt = YAMA; B1 = PB.P.sayfa_kur(kb, no[c], 'blue', '11x14')
        degisti = json.dumps(B0['o'], sort_keys=True, default=str) != json.dumps(B1['o'], sort_keys=True, default=str)
        r = {'cift': c, 'sayfa': no[c], 'olcum_degisti': degisti,
             'sembol_bant': {'once': B0['o']['sembol_bant'], 'sonra': B1['o']['sembol_bant']},
             'sembol_x': {'once': B0['o']['sembol'], 'sonra': B1['o']['sembol']},
             'ek_bant_sonra': B1['duz']['sembol_ek_bant'], 'setler': {}}
        for s, (a, b, m) in SETLER.items():
            try:
                p1, bi1, _ = PB.P.uret(B1, (a, b), m)
                kirpim(p1, B1['o'], out / f'K_{c}_{s}_SONRA.png')
                d = {'sonra': kapi_ozet(bi1)}
                if degisti or s == 'KISA':
                    p0, bi0, _ = PB.P.uret(B0, (a, b), m)
                    d['once'] = kapi_ozet(bi0)
                    fark = np.abs(np.asarray(p0.convert('RGB')).astype(np.int16) - np.asarray(p1.convert('RGB')).astype(np.int16))
                    d['piksel_fark'] = {'max': int(fark.max()), 'degisen_px': int((fark.max(2) > 0).sum())}
                    if degisti:
                        kirpim(p0, B0['o'], out / f'K_{c}_{s}_ONCE.png')
            except Exception as e:                                    # noqa: BLE001 - set HATA, parca devam
                d = {'sonra': {**HATA, 'hata': f'{type(e).__name__}: {e}'[:300]}}
            r['setler'][s] = d
        (out / f'SONUC_{c}.json').write_text(json.dumps(r, indent=1, default=str))
        g = time.time() - t0
        ozet = ' '.join(f'{s}:{"PASS" if all(r["setler"][s]["sonra"][k] for k in ("sembol", "kalinti", "temiz_ara")) else "FAIL"}'
                        for s in SETLER)
        print(f'[{i}/{len(benim)}] {c} olcum {"DEGISTI" if degisti else "ayni"} {r["sembol_bant"]} | {ozet} | '
              f'gecen {g:.0f}s | kalan ~{g / i * (len(benim) - i):.0f}s | %{i * 100 // len(benim)}', flush=True)


def gecti(d):
    return all(d[k] for k in ('sembol', 'kalinti', 'temiz_ara'))


def birlestir(girdi, out):
    girdi, out = Path(girdi), Path(out); out.mkdir(parents=True, exist_ok=True)
    R = [json.loads(p.read_text()) for p in sorted(girdi.glob('SONUC_*.json'))]
    sat = ['# SEMBOL ALT BANDI YAMASI: TEST (siparis hattina UYGULANMADI)', '',
           f'- Cift {len(R)} x 3 isim seti ({", ".join(f"{k}: {a}/{b}" for k, (a, b, _) in SETLER.items())}), Midnight Blue 11x14',
           f'- Olcumu degisen (riskli) cift: {sum(r["olcum_degisti"] for r in R)}: '
           f'{" ".join(r["cift"] for r in R if r["olcum_degisti"]) or "-"}']
    for s in SETLER:
        once_f = [r['cift'] for r in R if 'once' in r['setler'][s] and not gecti(r['setler'][s]['once'])]
        sonra_f = [r['cift'] for r in R if not gecti(r['setler'][s]['sonra'])]
        sat.append(f'- {s}: yama SONRASI PASS {len(R) - len(sonra_f)}/{len(R)} FAIL {" ".join(sonra_f) or "-"} | '
                   f'yama ONCESI FAIL (olculenler) {" ".join(once_f) or "-"}')
    ayni = [r for r in R if not r['olcum_degisti']]
    birebir = [r['cift'] for r in ayni if r['setler']['KISA'].get('piksel_fark', {}).get('max') == 0]
    sat.append(f'- Olcumu degismeyen {len(ayni)} cift: KISA set ONCE/SONRA birebir ayni {len(birebir)}/{len(ayni)}'
               f'{"" if len(birebir) == len(ayni) else " | FARKLI: " + " ".join(r["cift"] for r in ayni if r["cift"] not in birebir)}')
    sat += ['', '| cift | olcum | sembol_bant once -> sonra | ' + ' | '.join(SETLER) + ' |', '|---|---|---|' + '---|' * len(SETLER)]
    for r in R:
        h = []
        for s in SETLER:
            d = r['setler'][s]; x = 'PASS' if gecti(d['sonra']) else (f'HATA {d["sonra"]["hata"][:60]}' if 'hata' in d['sonra'] else f'FAIL (sag iou {d["sonra"]["sag"]["iou"]}, sol iou {d["sonra"]["sol"]["iou"]})')
            if 'once' in d and not gecti(d['once']):
                x += f' [once FAIL, sag iou {d["once"]["sag"]["iou"]}, sol iou {d["once"]["sol"]["iou"]}]'
            h.append(x)
        sat.append(f'| {r["cift"]} | {"DEGISTI" if r["olcum_degisti"] else "ayni"} | {r["sembol_bant"]["once"]} -> '
                   f'{r["sembol_bant"]["sonra"]} | ' + ' | '.join(h) + ' |')
    (out / 'RAPOR.md').write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat[:8]), flush=True)

    def sayfa(dosyalar, ad, sut=3):
        tiles = []
        for yol, etiket, ok in dosyalar:
            im = Image.open(yol).convert('RGB') if yol.exists() else Image.new('RGB', (900, 200), (80, 0, 0))
            t = Image.new('RGB', (900, im.height + 30), (255, 255, 255)); t.paste(im, (0, 30))
            ImageDraw.Draw(t).text((8, 8), etiket, fill=(0, 110, 0) if ok else (200, 0, 0))
            tiles.append(t)
        if not tiles:
            return
        h = max(t.height for t in tiles); n = (len(tiles) + sut - 1) // sut
        S = Image.new('RGB', (sut * 900 + (sut - 1) * 10, n * (h + 10)), (255, 255, 255))
        for j, t in enumerate(tiles):
            S.paste(t, ((j % sut) * 910, (j // sut) * (h + 10)))
        S.save(out / ad, quality=85)

    for s in SETLER:
        sayfa([(girdi / f'K_{r["cift"]}_{s}_SONRA.png', f'{r["cift"]} {s} {"PASS" if gecti(r["setler"][s]["sonra"]) else "FAIL"}'
                + (' (olcum degisti)' if r['olcum_degisti'] else ''), gecti(r['setler'][s]['sonra'])) for r in R], f'TEMAS_{s}.jpg')
    oncesonra = []
    for r in R:
        if r['olcum_degisti']:
            for s in SETLER:
                d = r['setler'][s]
                if 'once' in d:
                    oncesonra.append((girdi / f'K_{r["cift"]}_{s}_ONCE.png', f'{r["cift"]} {s} ONCE {"PASS" if gecti(d["once"]) else "FAIL"}', gecti(d['once'])))
                oncesonra.append((girdi / f'K_{r["cift"]}_{s}_SONRA.png', f'{r["cift"]} {s} SONRA {"PASS" if gecti(d["sonra"]) else "FAIL"}', gecti(d['sonra'])))
    sayfa(oncesonra, 'ONCE_SONRA.jpg', sut=2)
    tum = all(gecti(r['setler'][s]['sonra']) for r in R for s in SETLER) and len(birebir) == len(ayni)
    return 0 if tum else 1


if __name__ == '__main__':
    if sys.argv[1] == 'uret':
        uret(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif sys.argv[1] == 'birlestir':
        sys.exit(birlestir(sys.argv[2], sys.argv[3]))
    else:
        raise SystemExit(__doc__)
