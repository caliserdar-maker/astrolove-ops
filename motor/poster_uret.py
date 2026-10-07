#!/usr/bin/env python3
"""POSTER URETIM HATTI (Serdar 4 Eki): doku_poster (oge renk esitleme acik, ortak hedef Lab 71.5 / 8.5 / 49.5) ->
golge 1 -> renk_kapi (poster uzerinde, ogeler arasi en buyuk dE00 <= 1.0, ana sembol lekesi esik alti).
Kapi gecmezse kapali dongu: olculen fark kazanca yazilir, poster BIR KEZ daha basilir ve yeniden olculur.
Ikinci tur da gecmezse cikis kodu 1 (FAIL). Son poster: <cikti>/GOLGE_1.png, kapi raporu <cikti>/RENK_KAPI.json.

Kullanim: poster_uret.py --cikti DIR -- <doku_poster.py argumanlari (--cikti haric)>
"""
import json, subprocess, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
PY = sys.executable


def kos(*a):
    r = subprocess.run([PY, *map(str, a)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    i = sys.argv.index('--')
    C = Path(sys.argv[sys.argv.index('--cikti') + 1]); C.mkdir(parents=True, exist_ok=True)
    pargs = sys.argv[i + 1:]
    kaz = None
    # HEDEF GORUNUM (7 Eki): hedef JSON verildiyse renk kapisi kapali dongu hedefi = REF donusumu sonrasi (kapi_hedef)
    kh = []
    if '--hedef-json' in pargs:
        kh = ['--hedef', ','.join(map(str, json.loads(Path(pargs[pargs.index('--hedef-json') + 1]).read_text())['kapi_hedef']))]
    for tur in (1, 2):
        ek = ['--renk-kazanc', kaz] if kaz else []
        rc, out = kos(KOK / 'doku_poster.py', *pargs, '--cikti', C, *ek)
        if rc:
            print(out); sys.exit(f'FAIL: doku_poster (tur {tur})')
        rc, out = kos(KOK / 'golge.py', '--poster', C / 'POSTER.png', '--alfa', C / 'ALFA.png', '--rapor',
                      C / 'POSTER.json', '--cikti', C, '--kademe', '1')
        if rc:
            print(out); sys.exit(f'FAIL: golge (tur {tur})')
        yeni = C / f'RENK_KAZANC_{tur}.json'
        rc, out = kos(KOK / 'renk_kapi.py', '--poster', C / 'GOLGE_1.png', '--dizin', C, '--rapor', C / 'RENK_KAPI.json',
                      '--kazanc-cikti', yeni, *(['--onceki-kazanc', kaz] if kaz else []), *kh)
        print(f'[tur {tur}]', out.strip().splitlines()[-1], flush=True)
        r = json.loads((C / 'RENK_KAPI.json').read_text()); r['tur'] = tur
        (C / 'RENK_KAPI.json').write_text(json.dumps(r, indent=1, ensure_ascii=False))
        if rc == 0:
            return
        kaz = str(yeni)
    sys.exit('FAIL: renk kapisi 2 turda gecmedi')


if __name__ == '__main__':
    main()
