import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
ET_ARA = 45; SAT_ARA = 90; ARALIK = 760     # hucre merkezleri arasi (yatay)

def secim_kart(baslik, ogeler, alt, out, sira=(3, 2)):
    """ogeler: [(ad, PIL)], satirlar sira'ya gore (3 + 2), her satir ortali; gorseller ayni yukseklikte"""
    ph = round((K.ALAN[1] - K.ALAN[0] - len(sira) * (ET_ARA + K.ETIKET["boy"]) - (len(sira) - 1) * SAT_ARA))
    ph = ph // len(sira)
    gr = [(ad, g.resize((round(g.width * ph / g.height), ph), Image.LANCZOS)) for ad, g in ogeler]
    sat_h = ph + ET_ARA + K.ETIKET["boy"]; top = len(sira) * sat_h + (len(sira) - 1) * SAT_ARA
    y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
    im = K.tuval(); yer = []; k = 0
    for r, n in enumerate(sira):
        for j in range(n):
            cx = W / 2 + (j - (n - 1) / 2) * ARALIK; y = y0 + r * (sat_h + SAT_ARA)
            yer.append((cx, y)); k += 1
    for (ad, g), (cx, y) in zip(gr, yer):
        im.paste(g, (round(cx - g.width / 2), round(y)))
    d = ImageDraw.Draw(im); K.baslik(d, baslik)
    for (ad, g), (cx, y) in zip(gr, yer):
        K.yaz(d, K.ETIKET, [ad], cx, y + ph + ET_ARA, "center", ARALIK - 80)
    K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    im.save(out, quality=95); print(out, "poster yuksekligi", ph)

secim_kart("Choose Your Color", [("Midnight Blue", Image.open("renk_mb.png")), ("Deep Black", Image.open("renk_6.png")),
    ("Pure White", Image.open("renk_7.png")), ("Champagne Ivory", Image.open("renk_8.png")), ("Warm Parchment", Image.open("renk_9.png"))],
    "Every color as a print or a digital file", "WA_SECIM_sablon.jpg")
secim_kart("Choose Your Style", [(ad, Image.open(f"stil_{i}.png")) for ad, i in
    (("Starlit", 6), ("Timeless", 7), ("First Page", 8), ("Layers", 9), ("Botanical", 10))],
    "Every style as a print or a digital file", "YD_SECIM_sablon.jpg")
