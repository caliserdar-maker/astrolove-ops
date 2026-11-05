#!/usr/bin/env python3
"""Gizlilik kapisi (plan 2.8; ANA_2 7.3; depo public): verilen dosyalarda siparis girdisinin isimleri ve tarihi aranir.
Kelime siniri ile, buyuk/kucuk harf duyarsiz (AL, ED gibi kisa adlarda alt dizgi yanlis FAIL'i olmaz). Bulunursa cikis 1.
Cikti yalniz dosya adi + alan adi (deger yazilmaz). Kullanim: gizlilik_tara.py GIRDI.json DOSYA [DOSYA ...]  (0 temiz, 1 sizinti, 2 kullanim)."""
import json
import re
import sys
from pathlib import Path


def desenler(g):
    d = {}
    for alan in ('isim1', 'isim2'):
        v = (g.get(alan) or '').strip()
        if len(v) >= 2:
            d[alan] = re.compile(r'(?<![A-Za-z])' + re.escape(v) + r'(?![A-Za-z])', re.IGNORECASE)
    t = (g.get('tarih') or '').strip()
    if t:
        d['tarih'] = re.compile(re.escape(t), re.IGNORECASE)
    return d


def tara(g, dosyalar):
    d = desenler(g)
    bulgu = []
    for f in dosyalar:
        p = Path(f)
        if not p.is_file():
            continue
        metin = p.read_text(errors='replace')
        for alan, rx in d.items():
            if rx.search(metin):
                bulgu.append((p.name, alan))
    return bulgu, len(d)


def main(argv):
    if len(argv) < 3:
        print('kullanim: gizlilik_tara.py GIRDI.json DOSYA ...'); return 2
    g = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    bulgu, n = tara(g, argv[2:])
    if n == 0:
        print('GIZLILIK desen yok (girdi bos): FAIL'); return 1                # sessiz gecis yok
    for dosya, alan in bulgu:
        print('GIZLILIK SIZINTI', dosya, alan)
    print('GIZLILIK', 'FAIL' if bulgu else 'PASS', len(argv) - 2, 'dosya')
    return 1 if bulgu else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
