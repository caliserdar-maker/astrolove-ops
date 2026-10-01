#!/usr/bin/env python3
"""Regresyon karsilastirmasi (30 Eyl 2026): eski (merge oncesi siparis-baski-v1) ve yeni (merge sonrasi) kapi_olc
JSONL sonuclari hucre hucre (cift, renk, boy). Kural: eskide PASS olan hicbir hucre yenide FAIL / HATA olmamali.
Cikti: ozet satirlari + REGRESYON.md; PASS->FAIL varsa cikis 1."""
import argparse, json, sys
from pathlib import Path


def oku(d):
    r = {}
    for f in sorted(Path(d).rglob('*.jsonl')):
        for s in f.read_text().splitlines():
            if s.strip():
                x = json.loads(s)
                r[(x['cift'], x['renk'], x['boy'])] = x
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eski', required=True)
    ap.add_argument('--yeni', required=True)
    ap.add_argument('--md', default='REGRESYON.md')
    a = ap.parse_args()
    E, Y = oku(a.eski), oku(a.yeni)
    anahtar = sorted(set(E) | set(Y))
    ok = lambda x: bool(x and x.get('gecti'))
    # eksik hucre (bir tarafta olculmemis: zaman asimi) PASS->FAIL sayilmaz; ayrica listelenir ve cikis 1 olur
    geri = [k for k in anahtar if k in E and k in Y and ok(E[k]) and not ok(Y[k])]
    duzelen = [k for k in anahtar if k in E and k in Y and not ok(E[k]) and ok(Y[k])]
    eksik = [k for k in anahtar if k not in E or k not in Y]
    renkler = sorted({k[1] for k in anahtar})
    boylar = ', '.join(sorted({k[2] for k in anahtar}))
    satir = [f'# REGRESYON 78 cift x 4 renk (WP haric) x {boylar}', '',
             f'Hucre: eski {len(E)}, yeni {len(Y)}. PASS: eski {sum(ok(v) for v in E.values())}, '
             f'yeni {sum(ok(v) for v in Y.values())}. PASS->FAIL: {len(geri)}. FAIL->PASS: {len(duzelen)}. '
             f'Eksik: {len(eksik)}.', '', '| renk | eski PASS | yeni PASS | PASS->FAIL |', '|---|---|---|---|']
    for rk in renkler:
        satir.append(f"| {rk} | {sum(ok(v) for k, v in E.items() if k[1] == rk)} | "
                     f"{sum(ok(v) for k, v in Y.items() if k[1] == rk)} | {sum(k[1] == rk for k in geri)} |")
    satir += ['', '## PASS -> FAIL', '']
    satir += [f"- {k[0]} {k[1]} {k[2]}: yeni kalan={Y.get(k, {}).get('kalan')} hata={Y.get(k, {}).get('hata')}"
              for k in geri] or ['- yok']
    satir += ['', '## FAIL -> PASS', '']
    satir += [f"- {k[0]} {k[1]} {k[2]}: eski kalan={E.get(k, {}).get('kalan')} hata={E.get(k, {}).get('hata')}"
              for k in duzelen] or ['- yok']
    satir += ['', '## Yeni FAIL (tum)', '']
    satir += [f"- {k[0]} {k[1]} {k[2]}: kalan={v.get('kalan')} hata={v.get('hata')} (eski: "
              f"{'PASS' if ok(E.get(k)) else 'FAIL'})" for k, v in sorted(Y.items()) if not ok(v)] or ['- yok']
    if eksik:
        satir += ['', '## Eksik', ''] + [f'- {k}' for k in eksik]
    Path(a.md).write_text('\n'.join(satir) + '\n')
    print('\n'.join(satir[:12 + len(renkler)]))
    print('PASS->FAIL', json.dumps(geri))
    sys.exit(1 if geri or eksik else 0)


if __name__ == '__main__':
    main()
