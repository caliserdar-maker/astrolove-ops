import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
GEN = 1290; ARA = 150; GH = K.ALAN[1] - K.ALAN[0]; GW = 1140
NO_G = 150                     # "01" numara sutunu

def yazi_gen(bloklar, no_g, GEN):
    m = 0
    for n, e, t in bloklar:
        m = max(m, *[K.genislik(K.ETIKET, x) for x in e], *[K.genislik(K.METIN, x) for x in K.sar_d(K.METIN, t, GEN - no_g)])
    return m + no_g

def kart(baslik, gorsel, bloklar, alt, out):
    for k in (1.0, 0.92, 0.85, 0.78, 0.72):
        try:
            return _kart(baslik, gorsel, bloklar, alt, out, k)
        except SystemExit as e:
            print("kucult", k, e)
    raise SystemExit("sigmadi")

def _kart(baslik, gorsel, bloklar, alt, out, k):
    no_g = NO_G if any(n for n, _, _ in bloklar) else 0
    s = min(GW / gorsel.width, GH / gorsel.height) * k; gw, gh = round(gorsel.width * s), round(gorsel.height * s)
    GEN = min(1500, W - 2 * K.KENAR - gw - ARA)
    tw = yazi_gen(bloklar, no_g, GEN)
    x0 = round((W - (gw + ARA + tw)) / 2)
    im = K.tuval(); im.paste(gorsel.resize((gw, gh), Image.LANCZOS), (x0, round((K.ALAN[0] + K.ALAN[1]) / 2 - gh / 2)))
    d = ImageDraw.Draw(im); K.baslik(d, baslik)
    K.adimlar(d, x0 + gw + ARA, GEN, bloklar, no_g)
    K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    im.save(out, quality=95); print(out, 'olcek', k, 'gorsel', gw, gh, 'yazi', GEN)

