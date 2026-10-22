"""Kaynak: npm @fontsource/<aile> 5.3.0 (OFL-1.1; fonts/*_OFL.txt). Repodaki latin woff ile bayt bayt ayni surum.
Kullanim: font_latinext.py LATIN.woff LATIN-EXT.woff CIKTI.ttf (fonts/*-latinext-*.ttf boyle uretildi).
latin woff (taban, GPOS/kerning AYNEN) + latin-ext woff'tan yalniz eksik karakterlerin glifleri -> tek TTF."""
import sys
from fontTools.ttLib import TTFont
def birlestir(latin, ext, out):
    A = TTFont(latin); B = TTFont(ext); A.flavor = None
    assert 'glyf' in A and 'glyf' in B
    ca, cb = A.getBestCmap(), B.getBestCmap()
    eksik = {u: g for u, g in cb.items() if u not in ca}
    ad = lambda n: n + '.lx'
    kapanis, yigin = set(), list(eksik.values())
    while yigin:
        n = yigin.pop()
        if n in kapanis: continue
        kapanis.add(n)
        gl = B['glyf'][n]
        if gl.isComposite(): yigin += [c.glyphName for c in gl.components]
    order = A.getGlyphOrder() + [ad(n) for n in sorted(kapanis)]
    gA, gB = A['glyf'], B['glyf']
    for n in sorted(kapanis):
        g = gB[n]
        if g.isComposite():
            for c in g.components: c.glyphName = ad(c.glyphName)
        gA.glyphs[ad(n)] = g
        A['hmtx'].metrics[ad(n)] = B['hmtx'].metrics[n]
    A.setGlyphOrder(order); gA.glyphOrder = order
    for t in A['cmap'].tables:
        if t.isUnicode():
            for u, g in eksik.items(): t.cmap[u] = ad(g)
    A['maxp'].numGlyphs = len(order)
    if 'post' in A: A['post'].formatType = 3.0      # glif adlari tablosu yok (yeni adlar icin)
    A.save(out)
    print(out, 'eklenen karakter', len(eksik), 'glif', len(kapanis))
birlestir(*sys.argv[1:4])
