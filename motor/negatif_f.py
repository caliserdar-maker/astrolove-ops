#!/usr/bin/env python3
"""QC f (sembol rengi) iki yonlu kapi testi (3 Eki 2026, Serdar onayli koordinator notu).
Negatif: kosu 37134636169'un ana sembolu bozuk 10 sayfasi (Drive TEMP/MOTOR/SOSYAL/78_ONCEKI_37134636169) - f FAIL
vermeli. Pozitif: satistaki orijinaller (78) ve dogru uretilen ciftler f PASS vermeli (kosularin QC.json'larindan).
Negatif sayfalar ayni cifti dogru olcen sabitlerle (yeni kosu SABITLER/) qc.py'den gecirilir.

Kullanim: negatif_f.py --kaynak DIR --sabit-dizin DIR --negatif-dizin DIR --qc-dizin DIR [--qc-dizin DIR] --cikti F.md
"""
import argparse, json, subprocess, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
NEGATIF = ['AQUARIUS_ARIES', 'AQUARIUS_CANCER', 'AQUARIUS_CAPRICORN', 'AQUARIUS_GEMINI', 'AQUARIUS_LEO',
           'AQUARIUS_SAGITTARIUS', 'AQUARIUS_TAURUS', 'GEMINI_GEMINI', 'LIBRA_LIBRA', 'PISCES_SCORPIO']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit-dizin', required=True)
    ap.add_argument('--negatif-dizin', required=True)
    ap.add_argument('--qc-dizin', action='append', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    K = Path(a.kaynak)
    E = json.loads((KOK / 'sabitler' / 'E_ESIK.json').read_text())['MIDNIGHT_BLUE']['esik']
    sat = ['# QC f iki yonlu test', '', '## Negatif: kosu 37134636169 bozuk ana sembol sayfalari (f FAIL beklenir)', '',
           '| cift | f | buyuk sembol dE | kucuk sembol dE |', '|---|---|---|---|']
    neg_fail = 0
    for c in NEGATIF:
        S = Path(a.sabit_dizin) / f'SABITLER_{c}_MB_16x20.json'
        cik = Path(f'_neg_{c}.json')
        subprocess.run([sys.executable, str(KOK / 'qc.py'), '--kaynak', str(K), '--sabit', str(S), '--motor',
                        str(Path(a.negatif_dizin) / f'{c}.png'), '--isim1', 'X', '--isim2', 'Y', '--mesaj', 'Z',
                        '--cikti', str(cik), '--orijinal', str(K / 'orijinal' / f'{c}.jpg'),
                        '--orijinal-metin', f"{c.split('_')[0]}|{c.split('_')[1]}|Two Souls · One Bond",
                        '--plate-dosya', str(K / 'plates' / 'BLUE_16x20.png'), '--test5', 'yok', '--e-esik', str(E)],
                       capture_output=True, text=True)
        f = json.loads(cik.read_text())['motor']['f_sembol']
        neg_fail += not f['gecti']
        sat.append(f"| {c} | {'PASS' if f['gecti'] else 'FAIL'} | {f['dE']['buyuk_sembol']} | {f['dE']['kucuk_sembol']} |")
    o_pass = o_n = m_pass = m_n = 0
    gor = {}
    for d in a.qc_dizin:                                               # sonraki dizin ayni cifti gunceller
        for q in sorted(Path(d).glob('*_QC.json')):
            gor[q.name] = json.loads(q.read_text())
    for q in gor.values():
        o_n += 1; o_pass += bool(q['orijinal']['f_sembol']['gecti'])
        m_n += 1; m_pass += bool(q['motor']['f_sembol']['gecti'])
    sat += ['', f'Negatif: FAIL {neg_fail} / {len(NEGATIF)} (beklenen {len(NEGATIF)} / {len(NEGATIF)})',
            f'Pozitif orijinal: PASS {o_pass} / {o_n}', f'Pozitif motor (uretilen): PASS {m_pass} / {m_n}',
            f"SONUC: {'PASS' if neg_fail == len(NEGATIF) and o_pass == o_n and m_pass == m_n else 'FAIL'}"]
    Path(a.cikti).write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat))
    sys.exit(0 if neg_fail == len(NEGATIF) and o_pass == o_n and m_pass == m_n else 1)


if __name__ == '__main__':
    main()
