#!/usr/bin/env python3
"""CL galeri kart metinleri denetimi (Serdar 28 Eyl): Ingilizce yazim (pyspellchecker + alan sozlugu), uzun/orta tire
yok, urun metni yasaklari (CLAUDE.md 25 Eyl: OBA-free, bright white, omur yili, 12-colour). FAIL: yazim hatasi, tire,
yasak ifade. UYARI (FAIL degil, rapora): isimden once birlesik sifat tiresi onerisi (orn. 'print ready PDF').
Kullanim: metin_qc.py data/pod/cl_galeri_final19_metin.json
"""
import json
import re
import sys
from spellchecker import SpellChecker

ALAN = {'astrolove', 'hahnemühle', 'giclée', 'gsm', 'dpi', 'pdf', 'pdfs', 'etsy', 'emily', 'james', 'a2', 'a3', 'a4',
        'mm', 'cm', 'in', 'rag', 'libra', 'cancer', 'zodiac', 'personalized', 'finalize', 'color', 'colors',
        'aries', 'taurus', 'gemini', 'leo', 'virgo', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'}
YASAK = [r'\bOBA[- ]free\b', r'\bbright white\b', r'\b\d+\s*(?:-|to)?\s*\d*\s*years?\b', r'\b12[- ]colou?r\b']
TIRE_ONERI = [(r'\bprint ready (?=PDF)', 'print-ready'), (r'\bHigh resolution (?=\d)', 'High-resolution')]
sp = SpellChecker(); sp.word_frequency.load_words(ALAN)
J = json.load(open(sys.argv[1]))
hepsi = True
for kart, satirlar in J.items():
    if kart.startswith('_'):
        continue
    metin = ' '.join(satirlar)
    kelime = [w for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", metin) if not w.isupper() or len(w) > 3]
    hata = sorted(sp.unknown([w.lower() for w in kelime]))
    tire = re.findall(r'[‒-―−]', metin)
    yasak = [y for y in YASAK if re.search(y, metin, re.I)]
    oneri = [f"'{m.group(0).strip()}' -> '{o}'" for r, o in TIRE_ONERI for m in re.finditer(r, metin)]
    ok = not hata and not tire and not yasak
    hepsi &= ok
    print(f"{kart}: yazim hatasi {hata or 0} | tire {len(tire)} | yasak {yasak or 0} | "
          f"uyari {'; '.join(oneri) or '-'} | {'PASS' if ok else 'FAIL'}")
print('GENEL', 'PASS' if hepsi else 'FAIL')
sys.exit(0 if hepsi else 1)
