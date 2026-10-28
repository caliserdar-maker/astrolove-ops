import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
ET_ARA = 40

# K04: 4x2 izgara, etiket kalin (K05 ile ayni), alt not
adlar = ["Orange Blossom", "Purple Fig", "Olive Breeze", "Pomegranate Bloom", "Almond Blossom", "Lemon Grove", "Blue Grape", "Golden Loquat"]
g = [Image.open(f"k04_{i}.png").convert("RGB") for i in range(8)]
g = [x.resize((round(x.width * 0.92), round(x.height * 0.92)), Image.LANCZOS) for x in g]
IZ = 150   # izgara yan boslugu (8 stil adi sigsin)
gw = max(x.width for x in g); gh = max(x.height for x in g)
hucre_w = (W - 2 * IZ) / 4
sat_h = gh + ET_ARA + K.ETIKET["boy"]; sat_ara = 110
top = 2 * sat_h + sat_ara; y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
im = K.tuval()
for i, x in enumerate(g):
    r, c = divmod(i, 4); cx = IZ + hucre_w * (c + 0.5); y = y0 + r * (sat_h + sat_ara)
    im.paste(x, (round(cx - x.width / 2), round(y + gh - x.height)))
d = ImageDraw.Draw(im); K.baslik(d, "Choose Your Style")
for i, ad in enumerate(adlar):
    r, c = divmod(i, 4); cx = IZ + hucre_w * (c + 0.5); y = y0 + r * (sat_h + sat_ara) + gh + ET_ARA
    K.yaz(d, K.ETIKET, [ad], cx, y, "center", hucre_w - 10)
K.yaz(d, K.NOT, ["Every style in 11 oz and 15 oz"], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
im.save("K04_sablon.jpg", quality=95)

# K06: 2x2, sutun basliklari Front / Back, satir etiketleri solda, alt not tek satir
k = {n: Image.open(f"k06_{n}.png").convert("RGB") for n in ("kisa_on", "kisa_arka", "uzun_on", "uzun_arka")}
s = 1.05
k = {n: x.resize((round(x.width * s), round(x.height * s)), Image.LANCZOS) for n, x in k.items()}
mw = max(x.width for x in k.values()); mh = max(x.height for x in k.values())
et_w = max(K.genislik(K.ETIKET, t) for t in ("Short Example", "Long Example"))
kol_ara = 160; et_ara = 120
grup_w = et_w + et_ara + mw * 2 + kol_ara
x0 = (W - grup_w) / 2; xm = [x0 + et_w + et_ara + mw / 2, x0 + et_w + et_ara + mw * 1.5 + kol_ara]
bas_h = K.ETIKET["boy"] + 50; sat_ara = 60
top = bas_h + 2 * mh + sat_ara; y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
im = K.tuval()
for r, (on, arka) in enumerate((("kisa_on", "kisa_arka"), ("uzun_on", "uzun_arka"))):
    y = y0 + bas_h + r * (mh + sat_ara)
    for n, cx in ((on, xm[0]), (arka, xm[1])):
        x = k[n]; im.paste(x, (round(cx - x.width / 2), round(y + (mh - x.height) / 2)))
d = ImageDraw.Draw(im); K.baslik(d, "Short and Long Examples")
for t, cx in (("Front", xm[0]), ("Back", xm[1])):
    K.yaz(d, K.ETIKET, [t], cx, y0, "center", mw)
for r, t in enumerate(("Short Example", "Long Example")):
    y = y0 + bas_h + r * (mh + sat_ara) + mh / 2 - K.ETIKET["boy"] / 2
    K.yaz(d, K.ETIKET, [t], x0, y, gen=et_w + 2)
K.yaz(d, K.NOT, ["Up to 10 letters per name, message up to 30 characters"], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
im.save("K06_sablon.jpg", quality=95)
print("ok")
