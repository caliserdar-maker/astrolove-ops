#!/usr/bin/env python3
"""EB Garamond Italic 'c' ust ucu: damlanin ic kenar seviyesinin (y = 387) altinda kalan kismi k carpaniyla yukari cekilir.
Kullanim: harf_a_glif.py GIRDI.ttf CIKTI.ttf K"""
import sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
gir, cik, k = sys.argv[1], sys.argv[2], float(sys.argv[3])
f = TTFont(gir)
g = f['glyf']['c']
BEKLENEN = [(276, 414), (303, 414), (331, 395), (331, 382), (331, 366), (312, 333), (301, 333), (293, 333), (282, 347), (277, 357), (271, 368), (253, 387), (236, 387)]
co = list(g.coordinates)
assert co[10:23] == BEKLENEN and g.numberOfContours == 1 and len(co) == 43, 'c glifi beklenen kontur degil'
IC = 387
for i in range(11, 22):                      # ust uc noktalari (10 ve 22 sabit)
    x, y = co[i]
    if y < IC: co[i] = (x, round(IC - (IC - y) * k))
g.coordinates = GlyphCoordinates(co)
g.recalcBounds(f['glyf'])
f.save(cik)
print('damla alti y: 333 ->', min(y for x, y in co[11:22]), '| k', k)
