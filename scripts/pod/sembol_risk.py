#!/usr/bin/env python3
"""SALT OKUR tani: hat (a1_poster.olcum_duzelt) sembol bandini yalniz YUKARI genisletir. Sembolun bandin
ALTINDA kalan parcasi (orn. Terazi'nin alt cubugu) sembolle birlikte tasinmaz; sembol yeni ismin murekkep
merkezine ortalandiginda (pilot16.poster_kur) parca yerinde kalir -> sembol kapisi FAIL (ARIES_LIBRA IN:
olcum 1941-2109, gercek 1941-2127, sag iou 0.719). Risk olcutu (EJ KAPI_RAPORU.json):
  eksik = bant_dogrulama MIDNIGHT_BLUE sembol_bant[1] - olcum.sembol_bant[1]  (> 2 px -> RISK)
Kullanim: sembol_risk.py SIPARIS_DIZINI (icinde <CIFT>_MIDNIGHT_BLUE_11x14/KAPI_RAPORU.json)"""
import json
import sys
from pathlib import Path

ESIK = 2
sat, risk = [], []
for p in sorted(Path(sys.argv[1]).glob('*_MIDNIGHT_BLUE_11x14/KAPI_RAPORU.json')):
    k = json.loads(p.read_text())
    c = k.get('cift') or p.parent.name.removesuffix('_MIDNIGHT_BLUE_11x14')
    olc = (k.get('olcum') or {}).get('sembol_bant') or [0, 0]
    gercek = (((k.get('bant_dogrulama') or {}).get('renkler') or {}).get('MIDNIGHT_BLUE') or {}).get('bant', {}).get('sembol_bant')
    if not gercek:
        sat.append(f'| {c} | {olc} | - | ? | olculemedi |'); risk.append(c); continue
    eksik = gercek[1] - olc[1]
    r = eksik > ESIK
    sat.append(f'| {c} | {olc} | {gercek} | {eksik} | {"RISK" if r else "-"} |')
    if r:
        risk.append(c)
out = ['# SEMBOL BANDI RISK (EJ KAPI_RAPORU)', '', f'Toplam {len(sat)} | RISK {len(risk)} (eksik > {ESIK} px)',
       f'RISK: {" ".join(risk) or "-"}', '', '| cift | olcum sembol_bant | gercek (bant_dogrulama) | eksik px | durum |',
       '|---|---|---|---|---|'] + sat
Path('SEMBOL_RISK.md').write_text('\n'.join(out) + '\n')
print('\n'.join(out[:4]))
