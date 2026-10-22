#!/usr/bin/env python3
"""78 video kapagi toplu kosu (tasarim kapak_uret.py, DEGISTIRILMEZ).
1) GEMINI_LEO uretilir, onayli/kapak_gemini_leo.jpg ile ortalama mutlak fark (RGB, 0-255) <= --esik; degilse DUR (cikis 2).
2) 78 cift icin kapak_uret.py --a <ilk burc> --b <ikinci burc>; cikis kodu 0 = PASS. ETA sayaci.
3) QC.csv (cift, sonuc, hata, fark) + KONTAK.jpg (78 kucuk kapak, ortadaki 3:4 izgara kirpimi y 240..1680).
Kullanim: kapak_toplu.py --posters <PAIR.jpg 2000x3000 dizini> --out <dizin> [--esik 2.5]"""
import argparse, csv, os, subprocess, sys, time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ONAYLI = os.path.join(HERE, 'onayli', 'kapak_gemini_leo.jpg')


def dosya(c):
    a, b = c.lower().split('_')
    return f'{a}-and-{b}-astroloveart-kapak.jpg'


def uret(poster, c, out):
    a, b = (x.capitalize() for x in c.split('_'))
    r = subprocess.run([sys.executable, os.path.join(HERE, 'kapak_uret.py'), '--poster', poster, '--a', a, '--b', b, '--out', out],
                       capture_output=True, text=True)
    son = (r.stderr.strip() or r.stdout.strip()).splitlines()[-1:] if r.returncode else []
    return r.returncode, (son[0][:300] if son else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posters', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--esik', type=float, default=2.5)
    g = ap.parse_args()
    os.makedirs(g.out, exist_ok=True)
    ciftler = sorted(os.path.splitext(f)[0] for f in os.listdir(g.posters) if f.endswith('.jpg'))
    qc = {}
    # 1) onayli ornekle karsilastirma
    rc, h = uret(os.path.join(g.posters, 'GEMINI_LEO.jpg'), 'GEMINI_LEO', g.out)
    yol = os.path.join(g.out, dosya('GEMINI_LEO'))
    fark = float(np.abs(np.asarray(Image.open(yol).convert('RGB'), np.float32) -
                        np.asarray(Image.open(ONAYLI).convert('RGB'), np.float32)).mean()) if rc == 0 else -1
    print(f'ONAYLI KARSILASTIRMA GEMINI_LEO: cikis {rc}, ortalama fark {fark:.3f} (esik {g.esik})', flush=True)
    qc['GEMINI_LEO'] = ('PASS' if rc == 0 and 0 <= fark <= g.esik else 'FAIL', h or ('' if fark <= g.esik else f'fark {fark:.3f}'), f'{fark:.3f}')

    def yaz_qc():
        with open(os.path.join(g.out, 'QC.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(['cift', 'sonuc', 'hata', 'onayli_fark'])
            for c in ciftler:
                if c in qc:
                    w.writerow([c, *qc[c]])
    if qc['GEMINI_LEO'][0] != 'PASS':
        yaz_qc(); print('DUR: GEMINI_LEO onayli ornekle uyusmuyor; 77 kapak uretilmedi'); sys.exit(2)
    # 2) kalan 77
    t0, kalan = time.time(), [c for c in ciftler if c != 'GEMINI_LEO']
    for i, c in enumerate(kalan, 1):
        rc, h = uret(os.path.join(g.posters, c + '.jpg'), c, g.out)
        qc[c] = ('PASS' if rc == 0 and os.path.exists(os.path.join(g.out, dosya(c))) else 'FAIL', h, '')
        e = time.time() - t0
        if i % 5 == 0 or i == len(kalan):
            print(f'[{i + 1}/{len(ciftler)}] {c} {qc[c][0]} | gecen {e:.0f} sn, kalan ~{e / i * (len(kalan) - i):.0f} sn, '
                  f'%{100 * (i + 1) / len(ciftler):.0f}', flush=True)
    yaz_qc()
    # 3) kontak: 13 x 6, ortadaki 3:4 bant, 180x240
    tw, th, ara, sut = 180, 240, 6, 13
    sat = -(-len(ciftler) // sut)
    k = Image.new('RGB', (sut * (tw + ara) + ara, sat * (th + ara) + ara), (20, 20, 20))
    for i, c in enumerate(ciftler):
        p = os.path.join(g.out, dosya(c))
        if os.path.exists(p):
            im = Image.open(p).convert('RGB').crop((0, 240, 1080, 1680)).resize((tw, th), Image.LANCZOS)
            k.paste(im, (ara + (i % sut) * (tw + ara), ara + (i // sut) * (th + ara)))
    k.save(os.path.join(g.out, 'KONTAK.jpg'), quality=88)
    n = sum(v[0] == 'PASS' for v in qc.values())
    print(f'KAPAK {n}/{len(ciftler)} PASS' + ''.join(f'\n  {c}: {v[1]}' for c, v in qc.items() if v[0] != 'PASS'))
    sys.exit(0 if n == len(ciftler) == 78 else 1)


if __name__ == '__main__':
    main()
