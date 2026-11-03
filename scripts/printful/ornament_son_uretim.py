#!/usr/bin/env python3
"""ORNAMENT SON URETIM (Serdar 3 Kas, karar 22): 6 renk, Actions'ta yeniden uretilen PNG'lerin onayli PNG'lerle PIKSEL PIKSEL karsilastirmasi.
Onayli kaynaklar (is akisi git show ile cikarir):
  RUBY, SAPPHIRE, EMERALD : ALTIN_MOTOR deneme 4, e5412718 (kontur yok)
  BEIGE, AGED_PAPYRUS     : STIL3_SON, a5e3ea2
  SADE ALTIN              : SADE_1_ALTIN_TONU_954.png, 029a670d (seffaf zemin, RGBA)
Kapi (Merkez 3 Kas, secenek A): her PNG'de ayni mod ve boyut 954 x 954, en buyuk fark <= 1 seviye ve farkli piksel <= 10 (SADE'de alfa dahil).
  Gerekce: kosu 41641826870 ayni girdi / paket surumleriyle AMD EPYC'de 1-2 piksel 1 seviye fark verdi (yerel Intel Xeon'da 6/6 bayt ayni).
PASS'ta cikti klasorune ONAYLI PNG'lerin kendisi yazilir (Actions ciktisi yeniden uretilebilirlik kaniti): 6 PNG (CANCER_LIBRA_<RENK>_954.png),
ONIZLEME_76mm_6RENK.png, MOCKUP_1.jpg (Printful, SADE_1), OLCUM.json.
Kullanim: ornament_son_uretim.py --uretim DIR --onayli DIR --mockup JPG --kaynak DIR --cikti DIR --bilgi JSON"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('son', _d / 'ornament_son.py'); son = importlib.util.module_from_spec(_s); _s.loader.exec_module(son)
RENKLER = ('RUBY', 'SAPPHIRE', 'EMERALD', 'BEIGE', 'AGED_PAPYRUS', 'SADE_ALTIN')
KAYNAK_COMMIT = {'RUBY': 'e5412718', 'SAPPHIRE': 'e5412718', 'EMERALD': 'e5412718', 'BEIGE': 'a5e3ea2', 'AGED_PAPYRUS': 'a5e3ea2',
                 'SADE_ALTIN': '029a670d'}
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
TOL_SEVIYE, TOL_PIKSEL = 1, 10


def main():
    ap = argparse.ArgumentParser()
    for k in ('uretim', 'onayli', 'mockup', 'kaynak', 'cikti', 'bilgi'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    U, ON, O = Path(a.uretim), Path(a.onayli), Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    R = dict(karar='Serdar 3 Kas, karar 22: 6 renk kesin; RUBY / SAPPHIRE / EMERALD deneme 4 kontursuz, BEIGE / AGED_PAPYRUS STIL3_SON, SADE ALTIN seffaf',
             bilgi=json.loads(Path(a.bilgi).read_text()), karsilastirma={})
    hepsi = True
    for renk in RENKLER:
        f = f'CANCER_LIBRA_{renk}_954.png'
        u, o = Image.open(U / f), Image.open(ON / f)
        au, ao = np.asarray(u), np.asarray(o)
        ayni_mod = u.mode == o.mode and au.shape == ao.shape
        fark = int(np.abs(au.astype(int) - ao.astype(int)).max()) if ayni_mod else None
        n = int((au != ao).any(-1).sum()) if ayni_mod else None
        ok = bool(ayni_mod and fark <= TOL_SEVIYE and n <= TOL_PIKSEL and au.shape[:2] == (954, 954))
        hepsi &= ok
        R['karsilastirma'][renk] = dict(onayli_commit=KAYNAK_COMMIT[renk], mod=u.mode, boyut=list(au.shape), en_buyuk_fark=fark, farkli_piksel=n,
                                        uretim_sha256=sha(U / f), onayli_sha256=sha(ON / f), piksel_ayni=ok)
        print(f'{renk:13s} mod {u.mode} {au.shape} en buyuk fark {fark} farkli piksel {n} -> {"PASS" if ok else "FAIL"}', flush=True)
    R['kapi'] = dict(tanim=f'en buyuk fark <= {TOL_SEVIYE} seviye ve farkli piksel <= {TOL_PIKSEL} (Merkez 3 Kas, A)', pass_=bool(hepsi))
    R['drive_dosyasi'] = 'onayli PNG (git), Actions ciktisi degil'
    if hepsi:
        liste, et = [], []
        for renk in RENKLER:
            f = f'CANCER_LIBRA_{renk}_954.png'
            shutil.copyfile(ON / f, O / f)                                  # onayli dosyanin kendisi
            im = Image.open(O / f)
            if im.mode == 'RGBA':                                         # seffaf: onizlemede beyaz seramik uzerinde
                b = Image.new('RGB', im.size, (255, 255, 255)); b.paste(im, (0, 0), im); arr = np.asarray(b)
                et.append(f'SADE ALTIN (seffaf zemin)\nonizleme beyaz seramik uzerinde\nonayli {KAYNAK_COMMIT[renk]}')
            else:
                arr = np.asarray(im.convert('RGB')); et.append(f'{renk}\nonayli {KAYNAK_COMMIT[renk]}')
            liste.append(arr)
        font = ImageFont.truetype(str(Path(a.kaynak) / 'EBGaramond-Italic.ttf'), 24)
        son.onizleme_etiketli(liste, et, font, h_et=110).save(O / 'ONIZLEME_76mm_6RENK.png', dpi=(300, 300))
        shutil.copyfile(a.mockup, O / 'MOCKUP_1.jpg')
        R['mockup'] = dict(dosya='MOCKUP_1.jpg', kaynak='Printful v2 mockup, kosu 41629499594, stil 26418 Flat Front, SADE_1 (71a17026 = 029a670d bayt ayni)',
                           sha256=sha(O / 'MOCKUP_1.jpg'))
        R['cikti_sha256'] = {p.name: sha(p) for p in sorted(O.iterdir()) if p.suffix in ('.png', '.jpg')}
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(f'KAPI (fark <= {TOL_SEVIYE}, piksel <= {TOL_PIKSEL})', 'PASS' if hepsi else 'FAIL', flush=True)
    return 0 if hepsi else 1


if __name__ == '__main__':
    sys.exit(main())
