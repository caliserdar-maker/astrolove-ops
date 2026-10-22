#!/usr/bin/env python3
"""siparis-dijital PLAN adimi (Serdar 1 Eki, Test 2 dersleri): is matrisi + cift normalizasyonu + HIZLI KAYNAK DENETIMI.

1) Cift alfabetik normalize (surucu.cift_normalize; isimler yer degistirir) - loga yalniz cift kodu ve evet/hayir.
2) Kaynak denetimi: gerekli POD_PRINT ve PLATES dosyalari iki `rclone lsf` listesiyle (cift klasoru + PLATES)
   karsilastirilir; eksik varsa EKSIK satirlari + cikis 1 (13 is acilmaz). --ls-json ile yerel deneme (rclone yok).
Cikti: GITHUB_OUTPUT satirlari (renk, sayfa, sayfa_var, wp, cift, normalize) stdout'a.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surucu                                                     # noqa: E402

R = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY']; B = ['16x20', '18x24', '24x36', '11x14', 'A2']
SAYFA_RENK = ['MIDNIGHT_BLUE']        # HIZ (1 Eki): MB renk x oran matrisi (5 paralel sayfa isi, PDF pakette birlesir)


def matris(isler_str):
    i = [x.strip() for x in (isler_str or '').split(',') if x.strip()]
    r = [x for x in R if not i or f'renk:{x}' in i]; w = [x for x in B if not i or f'wp:{x}' in i]
    bil = [x for x in i if x not in [f'renk:{y}' for y in R] + [f'wp:{y}' for y in B] + ['paket']]   # 'paket': yalniz paketleme
    if bil:
        raise SystemExit(f'HATA: bilinmeyen is: {bil}')
    return r, w


def lsf(yol):
    """PLATES yalniz ust seviye (alt klasorler yedek; sayilmaz), cift klasoru ozyinelemeli (<renk>/<boy>.jpg)."""
    rek = [] if yol.rstrip('/').endswith('PLATES') else ['-R']
    p = subprocess.run(['rclone', 'lsf', *rek, '--files-only', yol], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:                 # klasor yok -> bos liste (eksik olarak raporlanir)
        return []
    return [x.strip() for x in p.stdout.splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ls-json', default='', help='yerel deneme: {"pod": [...], "plates": [...]} (rclone yerine)')
    a = ap.parse_args()
    t0 = time.time()
    g = surucu.girdi()
    e = json.loads(Path(os.environ.get('SIPARIS_GIRDI_JSON') or os.environ['GITHUB_EVENT_PATH']).read_text())
    e = e.get('inputs', e)
    r, w = matris(e.get('isler'))
    if g['normalize']:
        print(f"CIFT normalize: evet ({g['cift_girdi']} -> {g['cift']}, isimler yer degistirdi)", file=sys.stderr)
    else:
        print(f"CIFT normalize: hayir ({g['cift']})", file=sys.stderr)
    gerek = surucu.kaynak_listesi(g['cift'], r, w)
    if a.ls_json:
        v = json.loads(Path(a.ls_json).read_text()); pod_var, pl_var = v['pod'], v['plates']
    else:
        yollar = [f"{surucu.POD_YOL}/{g['cift']}", surucu.PLATES_YOL]
        if any(x.startswith('CANCER_LIBRA/') for x in gerek['pod']) and g['cift'] != 'CANCER_LIBRA':
            yollar.append(f'{surucu.POD_YOL}/CANCER_LIBRA/MIDNIGHT_BLUE')
        with ThreadPoolExecutor(len(yollar)) as ex:
            ls = list(ex.map(lsf, yollar))
        pod_var = [f"{g['cift']}/{x}" for x in ls[0]] + ([f'CANCER_LIBRA/MIDNIGHT_BLUE/{x}' for x in ls[2]] if len(ls) > 2 else [])
        pl_var = ls[1]
    eksik = surucu.kaynak_eksik(gerek, pod_var, pl_var)
    sn = round(time.time() - t0, 1)
    if eksik:
        for x in eksik:
            print(f'::error title=EKSIK KAYNAK::{x}', file=sys.stderr)
        print(f'HATA: {len(eksik)} kaynak eksik ({sn} sn): ' + ', '.join(eksik[:12]) + (' ...' if len(eksik) > 12 else ''),
              file=sys.stderr)
        return 1
    print(f"KAYNAK TAMAM: {len(gerek['pod'])} POD + {len(gerek['plates'])} plate ({sn} sn)", file=sys.stderr)
    sy = [{'renk': x, 'oran': o} for x in r if x in SAYFA_RENK for o in ('2x3', '3x4', 'a_series', '4x5', '11x14')]
    r = [x for x in r if x not in SAYFA_RENK]
    print('renk=' + json.dumps(r))
    print('sayfa=' + json.dumps({'include': sy} if sy else {'include': [{'renk': '', 'oran': ''}]}))
    print('sayfa_var=' + ('1' if sy else '0'))
    print('wp=' + json.dumps(w))
    print('cift=' + g['cift'])
    print('normalize=' + ('evet' if g['normalize'] else 'hayir'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
