#!/usr/bin/env python3
"""Urun metni kurali (tek kaynak). Serdar karari 25 Eyl 2026; 24 Eyl B-5 kuralini gunceller.
Birincil kaynak: Hahnemuhle Photo Rag datasheet + urun sayfasi; Prodigi HPR urun foyu.
IZINLI: acid-free, 100% cotton, pigment-based archival inks, natural white, matte,
        "Hahnemuhle rates Photo Rag as museum quality (ISO 9706)".
YASAK:  OBA-free, bright white, omur yili (orn. 100-200 years), "12-colour"/"12-color", uzun/orta tire.
Kullanim: python3 metin_kurali.py <dosya|klasor> ...   -> PASS/FAIL (FAIL'de cikis kodu 1)"""
import re, sys
from pathlib import Path

IZINLI = ['acid-free', '100% cotton', 'pigment-based archival inks', 'natural white', 'matte',
          'Hahnemühle rates Photo Rag as museum quality (ISO 9706)']
YASAK = {
    'OBA-free': r'\bOBA[\s-]*free\b',
    'bright white': r'\bbright[\s-]+white\b',
    'omur yili': r'\b\d{2,4}\s*(?:[-–—]|to)?\s*(?:\d{2,4}\s*)?\+?\s*years?\b',
    '12-colour': r'\b12[\s-]*colou?rs?\b',
    'uzun/orta tire': r'[—–]',
}

def denetle(metin):
    return [(ad, m.group(0)) for ad, rx in YASAK.items() for m in re.finditer(rx, metin, re.I)]

if __name__ == '__main__':
    hata = 0
    for a in sys.argv[1:]:
        p = Path(a)
        for f in ([p] if p.is_file() else sorted(x for x in p.rglob('*') if x.suffix in ('.txt', '.json', '.csv', '.md'))):
            for ad, s in denetle(f.read_text(encoding='utf-8', errors='replace')):
                print(f'FAIL {f}: {ad}: {s!r}'); hata += 1
    print('GENEL', 'PASS' if hata == 0 else f'FAIL ({hata})'); sys.exit(1 if hata else 0)
