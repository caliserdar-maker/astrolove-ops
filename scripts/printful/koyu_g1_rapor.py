#!/usr/bin/env python3
"""KOYU ZEMIN G1 rapor: ONIZLEME (eski e5412718 | yeni G1, 3 renk, 7.6 cm, 300 dpi) + OLCUM.json (zemin + oge kapilari).
Kullanim: koyu_g1_rapor.py --eski DIR --yeni DIR(motor ciktisi) --cikti DIR --font TTF"""
import argparse, importlib.util, json, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont
_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('son', _d / 'ornament_son.py'); son = importlib.util.module_from_spec(_s); _s.loader.exec_module(son)
ap = argparse.ArgumentParser()
for k in ('eski', 'yeni', 'cikti', 'font'): ap.add_argument('--' + k, required=True)
a = ap.parse_args(); O = Path(a.cikti)
M = json.loads((Path(a.yeni) / 'OLCUM.json').read_text()); Z = json.loads((O / 'OLCUM_ZEMIN.json').read_text())
shutil.copyfile(Path(a.yeni) / 'OLCUM.json', O / 'OLCUM_MOTOR.json')                 # inceleme: motor olcumu depoda
D4 = {'RUBY': 0.693, 'SAPPHIRE': 0.692, 'EMERALD': 0.692}                            # deneme 4 (e5412718) halka govde surekliligi
liste, et = [], []
for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
    f = f'CANCER_LIBRA_{renk}_954.png'
    shutil.copyfile(Path(a.yeni) / f, O / f)
    liste += [np.asarray(Image.open(Path(a.eski) / f).convert('RGB')), np.asarray(Image.open(O / f).convert('RGB'))]
    z = Z['renk'][renk]; s = M['sonuc'][renk]
    et += [f'{renk} ESKI (deneme 4, Canva AI zemin)\nleke {z["leke_eski"]["pencere_ortalama_std"]}',
           f'{renk} YENI (G1 duz radyal + tane)\nleke {z["leke_yeni"]["pencere_ortalama_std"]}, halka dE00 maks {z["renk_dE00_halka_maks"]}\n'
           f'kontrast ortanca {s["kontrast_ortanca_en_kotu"]}']
son.onizleme_etiketli(liste, et, ImageFont.truetype(a.font, 24), h_et=120).save(O / 'ONIZLEME_76mm_ESKI_YENI.png', dpi=(300, 300))
g = M['kapi']
R = dict(karar='Serdar 3 Kas: koyu zemin duz (G1, BEIGE / AGED_PAPYRUS yontemi); ogeler deneme 4 (e5412718) aynen, yalniz zemin',
         zemin=Z, oge=dict(kapi=g, kontrast_ortanca={r: M['sonuc'][r]['kontrast_ortanca_en_kotu'] for r in ('RUBY', 'SAPPHIRE', 'EMERALD')},
                           dE00_son_ham_maks={r: max(M['sonuc'][r]['dE00_son_ham'].values()) for r in ('RUBY', 'SAPPHIRE', 'EMERALD')},
                           halka_sureklilik_bilgi={r: M['sonuc'][r]['halka_sureklilik']['oran'] for r in ('RUBY', 'SAPPHIRE', 'EMERALD')},
                           dusus_kucuk_oge_sabit=M['deneme4']['dusus_kucuk_oge_sabit'], zemin_sha256=M['zemin']['sha256']),
         kapi=dict(zemin_leke_le_beige_g1=all(Z['renk'][r]['kapi']['leke_le_beige'] for r in Z['renk']),
                   zemin_renk_dE00_le_2=all(Z['renk'][r]['kapi']['renk_dE00_le_2'] for r in Z['renk']),
                   kontrast_ortanca=g['kontrast_ortanca'], oge_alfa_leke_0=g['leke_a_0'] and g['leke_a_kaynak_0'], tasma_0=g['goruntu_yasak_0'],
                   yerlesim_ayni=g['yerlesim_ayni'],
                   halka_sureklilik_deneme4_ile_ayni=all(abs(M['sonuc'][r]['halka_sureklilik']['oran'] - D4[r]) <= 0.002 for r in D4)),
         motor_genel=dict(sonuc='FAIL' if not all(g.values()) else 'PASS', cikis_kodu=0 if all(g.values()) else 1,
                          neden=[k for k, v in g.items() if not v],
                          not_='halka govde surekliligi 0.692-0.693 < 0.70; deneme 4 ile ayni; Serdar 3 Kas deneme 4 sonucunu kabul etti (soru yaniti)'),
         motor_olcum_tam='OLCUM_MOTOR.json (bu klasorde)')
(O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
print(json.dumps(R['kapi']))
