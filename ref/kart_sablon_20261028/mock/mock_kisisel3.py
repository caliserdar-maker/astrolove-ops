import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent / "k78/scripts/kapak78"))
import yd_kart_ornek as K
W, H = K.W, K.H
GEN = 1290            # yazi sutunu sarma genisligi (uc kartta ayni)
ARA = 150             # gorsel ile yazi arasi (uc kartta ayni)
GH = K.ALAN[1] - K.ALAN[0]   # gorsel yuksekligi siniri: icerik alaninin tamami
GW = 1140             # gorsel genisligi siniri

def yazi_gen(bloklar):
    m = 0
    for _, e, t in bloklar:
        m = max(m, *[K.genislik(K.ETIKET, x) for x in e], *[K.genislik(K.METIN, x) for x in K.sar_d(K.METIN, t, GEN)])
    return m

def kart(baslik, gorsel, bloklar, out):
    """gorsel: PIL (tek parca) ya da [(PIL), (PIL)] ust uste"""
    parca = gorsel if isinstance(gorsel, list) else [gorsel]
    ara_p = 30
    hh = (GH - ara_p * (len(parca) - 1)) / len(parca)
    olc = [min(GW / p.width, hh / p.height) for p in parca]
    gw = max(round(p.width * s) for p, s in zip(parca, olc))
    tw = yazi_gen(bloklar)
    x0 = round((W - (gw + ARA + tw)) / 2)                 # gorsel + bosluk + yazi grubu sayfada ortali
    im = K.tuval()
    top = sum(round(p.height * s) for p, s in zip(parca, olc)) + ara_p * (len(parca) - 1)
    y = round((K.ALAN[0] + K.ALAN[1]) / 2 - top / 2)
    for p, s in zip(parca, olc):
        nw, nh = round(p.width * s), round(p.height * s)
        im.paste(p.resize((nw, nh), Image.LANCZOS), (x0 + round((gw - nw) / 2), y)); y += nh + ara_p
    d = ImageDraw.Draw(im)
    K.baslik(d, baslik)
    K.adimlar(d, x0 + gw + ARA, GEN, bloklar)
    K.yaz(d, K.NOT, ["Please check your spelling before you order"], W/2, K.NOT_Y, "center", W - 2*K.KENAR)
    im.save(out, quality=95)
    return dict(x0=x0, gw=gw, tw=round(tw), sag_bosluk=W - (x0 + gw + ARA + tw))

poster = Image.open("AstroLoveArt_Cancer_Libra_Midnight_Blue_2000.jpg").convert("RGB")
print(kart("Your Names, Your Message", poster, [
    (None, ["Name Under Cancer", "Name Under Libra"], "Up to 11 letters each, English letters, printed in capitals"),
    (None, ["Your Message"], "Up to 35 characters, printed as you type it, no emoji")], "S2_sablon3.jpg"))
on, arka = Image.open("kupa_on.png").convert("RGB"), Image.open("kupa_arka.png").convert("RGB")
print(kart("Your Names, Your Message", [on, arka], [
    (None, ["Name Under Cancer", "Name Under Libra"], "Up to 10 letters each, printed in capitals on the front"),
    (None, ["Your Message"], "Up to 30 characters, printed on the back with your names"),
    (None, ["One Mug, Two Sides"], "Front with your symbol and names, back with your message")], "K03_sablon3.jpg"))
ydp = Image.open("yd_poster.png").convert("RGB")
print(kart("Your Names, Your Date", ydp, [
    (None, ["Name Under Cancer", "Name Under Libra"], "Up to 11 letters each, English letters, printed in capitals"),
    (None, ["Your Special Date"], "Month in letters, for example 14 June 2025"),
    (None, ["Your Heading"], "Paper Anniversary or Our First Year"),
    (None, ["Optional Short Line"], "Up to 20 characters, Year One if left empty")], "Y03_sablon3.jpg"))
