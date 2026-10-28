import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
TG = 1500                      # tablo metin sutunu genisligi
ETG = 140                      # etiket ile metin arasi
SATIR_ARA = 120                # satirlar arasi
PAR = 0.6 * K.METIN["boy"]    # ayni satirda iki bilgi arasi

def tablo_kart(baslik, satirlar, alt, out):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, baslik)
    ew = max(K.genislik(K.ETIKET, e) for e, _ in satirlar)
    hz = [(e, [K.sar_d(K.METIN, p, TG) for p in ps]) for e, ps in satirlar]
    tw = max(max(K.genislik(K.METIN, x) for p in ps for x in p) for _, ps in hz)
    yk = [max(K.ETIKET["boy"], sum(K.blok_yuk(K.METIN, len(p)) for p in ps) + PAR * (len(ps) - 1)) for _, ps in hz]
    top = sum(yk) + SATIR_ARA * (len(yk) - 1)
    x0 = round((W - (ew + ETG + tw)) / 2); y = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
    for (e, ps), h in zip(hz, yk):
        K.yaz(d, K.ETIKET, [e], x0, y + (K.METIN["boy"] - K.ETIKET["boy"]) / 2, gen=ew)
        yy = y
        for p in ps:
            yy += K.yaz(d, K.METIN, p, x0 + ew + ETG, yy, gen=TG) + PAR
        y += h + SATIR_ARA
    K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    im.save(out, quality=95)

SIZES = "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2"
tablo_kart("Digital File or Print", [
    ("Digital File", ["One print ready digital file in the color and size you choose", "Nothing is shipped"]),
    ("Print", ["Unframed print on matte art paper", "Free shipping worldwide"]),
    ("14 Sizes", [SIZES])], "Every size as a print or a digital file", "S3_sablon2.jpg")
tablo_kart("Digital File or Print", [
    ("Digital File", ["One print ready digital file in the style and size you choose", "Nothing is shipped"]),
    ("Print", ["Unframed print on matte art paper", "Free shipping worldwide"]),
    ("14 Sizes", [SIZES])], "Every style and size as a print or a digital file", "Y04_sablon2.jpg")

# Kupa: iki kupa ayni olcekte, tabanlar hizali; altinda ayni tablo mantigi (etiket + olcu satirlari) her kupanin altinda ortali
g = [Image.open("k05_11.png").convert("RGB"), Image.open("k05_15.png").convert("RGB")]
s = 1.0; g = [x.resize((round(x.width * s), round(x.height * s)), Image.LANCZOS) for x in g]
bilgi = [("11 oz", ["9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml"]), ("15 oz", ["11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml"])]
D = max(x.width for x in g) + 220
im = K.tuval(); gh = max(x.height for x in g); ara = 90
yb = K.ETIKET["boy"] + 0.3 * K.ETIKET["boy"] + K.blok_yuk(K.METIN, 3)
top = gh + ara + yb; y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
cx = [W / 2 - D / 2, W / 2 + D / 2]
for x, c in zip(g, cx):
    im.paste(x, (round(c - x.width / 2), round(y0 + gh - x.height)))
d = ImageDraw.Draw(im); K.baslik(d, "Two Sizes")
for (e, ls), c in zip(bilgi, cx):
    y = y0 + gh + ara
    y += K.yaz(d, K.ETIKET, [e], c, y, "center", 700) + 0.3 * K.ETIKET["boy"]
    K.yaz(d, K.METIN, ls, c, y, "center", 700)
K.yaz(d, K.NOT, ["Height x diameter, approximate size comparison"], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
im.save("K05_sablon2.jpg", quality=95)
print("ok")
