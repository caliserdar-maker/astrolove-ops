#!/usr/bin/env python3
"""ORNAMENT SON URETIM, 5 STIL (Serdar 3 Kas, karar 25): Actions'ta yeniden uretilen PNG'lerin onayli PNG'lerle HAM PIKSEL karsilastirmasi.
Onayli kaynak: dal ornament-printful-katalog 6daab364, docs/ornament/ornek/ORNAMENT_5STIL_20261103_1539/ (is akisi git show ile cikarir):
  RUBY, SAPPHIRE, EMERALD : eliptik zemin (ON_OLCUM_ELIPS, 6322d66b) + ALTIN_MOTOR deneme 4 ogeler (kontur yok)
  SADE ALTIN              : SADE_1_ALTIN_TONU_954.png (029a670d), seffaf RGBA
  FILDISI                 : scripts/printful/ornament_fildisi.py birebir (girdi SADE_1); ham piksel sha256 ea47a57f... (Merkez)
Kapi (Merkez 3 Kas, A): her PNG'de ayni mod ve boyut 954 x 954, ham pikselde en buyuk fark <= 1 seviye ve farkli piksel <= 10 (alfa dahil);
  PNG sha farki sayilmaz. PASS'ta cikti klasorune ONAYLI PNG'lerin kendisi + ONIZLEME_76mm_5STIL.png (onayli) + OLCUM.json yazilir.
Kullanim: ornament_son_uretim.py --uretim DIR --onayli DIR --onizleme PNG --cikti DIR --bilgi JSON"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RENKLER = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
KAYNAK_COMMIT = {r: '6daab364' for r in RENKLER}
FILDISI_HAM = 'ea47a57f49ec73af4b9606dd3c5636f97f0121f1ac10305630c76431409f952b'
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
TOL_SEVIYE, TOL_PIKSEL = 1, 10


def main():
    ap = argparse.ArgumentParser()
    for k in ('uretim', 'onayli', 'onizleme', 'cikti', 'bilgi'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    U, ON, O = Path(a.uretim), Path(a.onayli), Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    R = dict(karar='Serdar 3 Kas, karar 25: 5 stil kesin (RUBY, SAPPHIRE, EMERALD eliptik; SADE ALTIN; FILDISI KREM); BEIGE ve AGED_PAPYRUS cikti',
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
        ham = lambda x: hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
        R['karsilastirma'][renk] = dict(onayli_commit=KAYNAK_COMMIT[renk], mod=u.mode, boyut=list(au.shape), en_buyuk_fark=fark, farkli_piksel=n,
                                        uretim_sha256=sha(U / f), onayli_sha256=sha(ON / f), uretim_ham_piksel_sha256=ham(au), onayli_ham_piksel_sha256=ham(ao),
                                        tolerans_icinde=ok)
        if renk == 'FILDISI':
            R['karsilastirma'][renk]['merkez_ham_piksel_sha256'] = FILDISI_HAM
            R['karsilastirma'][renk]['onayli_merkez_ham_ayni'] = ham(ao) == FILDISI_HAM
        print(f'{renk:13s} mod {u.mode} {au.shape} en buyuk fark {fark} farkli piksel {n} -> {"PASS" if ok else "FAIL"}', flush=True)
    R['kapi'] = dict(tanim=f'en buyuk fark <= {TOL_SEVIYE} seviye ve farkli piksel <= {TOL_PIKSEL} (Merkez 3 Kas, A)', pass_=bool(hepsi))
    R['drive_dosyasi'] = 'onayli PNG (git), Actions ciktisi degil'
    if hepsi:
        for renk in RENKLER:
            f = f'CANCER_LIBRA_{renk}_954.png'
            shutil.copyfile(ON / f, O / f)                                  # onayli dosyanin kendisi
        shutil.copyfile(a.onizleme, O / 'ONIZLEME_76mm_5STIL.png')
        R['cikti_sha256'] = {p.name: sha(p) for p in sorted(O.iterdir()) if p.suffix in ('.png', '.jpg')}
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(f'KAPI (fark <= {TOL_SEVIYE}, piksel <= {TOL_PIKSEL})', 'PASS' if hepsi else 'FAIL', flush=True)
    return 0 if hepsi else 1


if __name__ == '__main__':
    sys.exit(main())
