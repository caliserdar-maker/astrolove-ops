#!/usr/bin/env python3
"""AstroLoveArt kupa, onayli 7 stil (16 Eki 2026): Botanical, Gold, Nazar Bond, Rose Ribbon,
Promise Line, Aegean Tile, Mediterranean.

- Yerlesim, ChatGPT'nin onayli duzeltilmis mockup'larindan olculdu (ref7/grid_*.png).
  Birim: "on gorunus" pikseli (yuz ortasinda 300 dpi), yuz merkezi (0, 0).
- Her yuz once duz bir on-gorunus tuvaline cizilir, sonra silindire gore yatayda on-duzeltilir
  (kupaya onden bakinca tasarim mockup'taki gibi gorunur).
- Sembol ve halka orijinal maskelerden; yeniden cizim yok, yalniz olcek + tek renk.
- Susler ChatGPT'nin ayri uretim gorsellerinden (kupa_suslemeler/); zemin saf beyaza cekilir,
  carpma (multiply) ile basilir. Isimler / burc / mesaj kodla yazilir.
Kullanim: python kupa_7stil.py <sembol> <font> <susleme> <cikti>
"""
import math, sys, time, pathlib
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SEM, FNT, SUS, OUT = (pathlib.Path(a) for a in sys.argv[1:5])
OUT.mkdir(parents=True, exist_ok=True)

DPI, FW, FH = 300, 2700, 1050
D_IN = 3.35
RK = D_IN / 2 * DPI                         # silindir yaricapi (baski px)
QUARTER = D_IN * math.pi / 4 * DPI
FACE = {"on": FW / 2 - QUARTER, "arka": FW / 2 + QUARTER}
TV = 452                                    # on-gorunus tuvali yari genisligi (kulp tarafi siniri)
Y_MAX, X_MAX = 500, 446                     # ust/alt >= 25 px bos; yanlar kulp boslugundan once

ISIM1, ISIM2 = "Emily", "James"
ISIM_MM, BURC_MM, MESAJ_MM = 2.2, 2.0, 2.6      # uzun isim / uzun burc satiri bu harf boyuna kadar buyutulur (zor ornek testi 17.10)
REF_ANA = (2082, 1961)           # Cancer-Libra birlesik sembol olcusu: diger ciftlerin sembolu bu zarfi %5'ten fazla asmaz
BURC = "CANCER · LIBRA"
import os as _os0, json as _json0
if _os0.environ.get("CIFT"):          # zor ornek testi: {"isim1": "...", "isim2": "...", "burc": "..."}
    _c = _json0.loads(_os0.environ["CIFT"])
    ISIM1, ISIM2, BURC = _c["isim1"], _c["isim2"], _c["burc"]
AYNI_BURC = len(set(BURC.split(" · "))) == 1   # ayni burclu cift (12 cift)

GREEN, TERRA = (44, 73, 56), (205, 98, 60)
GOLD, NAVY = (182, 133, 44), (10, 30, 62)
NB_GOLD, NB_NAVY = (166, 118, 38), (12, 31, 74)
BURG = (130, 18, 46)
BLACK = (12, 12, 12)
ROSE = (200, 70, 98)          # Rose Ribbon cicek pembesi (vurgu)
P_NAVY = (10, 40, 130)        # Promise Line bileklik nazari (vurgu)
TURQ = (0, 132, 186)          # Aegean cini turkuazi (vurgu)
SEA = (0, 140, 200)           # Mediterranean deniz turkuazi (vurgu)
AEG = (8, 36, 122)
MED = (6, 60, 180)
# ozgun sembol rengi (varsayilan = stilin ana rengi)
GREEN_SEM, GOLD_SEM, NB_SEM, BURG_SEM, BLACK_SEM, AEG_SEM, MED_SEM = GREEN, GOLD, NB_GOLD, BURG, BLACK, AEG, MED
# Gold oge renkleri (ayri ayri denenebilir)
# KARAR 17 Eki 2026 (Serdar): okra altin + lacivert; on: isimler altin, burc adlari lacivert; arka: mesaj altin, isimler lacivert
G_GLIF, G_LOGO, G_ISIM, G_BURC, G_MESAJ, G_AISIM, G_AYRAC = GOLD, GOLD, GOLD, NAVY, GOLD, NAVY, GOLD
# Nazar Bond KARAR 17 Eki 2026 (Serdar, ON-13 + ARKA-4): sembol altin; glif, logo, isimler lacivert; burc adlari altin; arka mesaj lacivert, isimler altin
NB_GLIF, NB_ISIM, NB_BURC, NB_MESAJ, NB_AISIM = NB_NAVY, NB_NAVY, NB_GOLD, NB_NAVY, NB_GOLD
# Rose Ribbon KARAR 17 Eki 2026 (Serdar, ON-2 + ARKA-2): sembol, glif, logo, isimler bordo; burc adlari gul; arka mesaj bordo, isimler gul
RR_GLIF, RR_ISIM, RR_BURC, RR_MESAJ, RR_AISIM = BURG, BURG, ROSE, BURG, ROSE
# Promise Line KARAR 17 Eki 2026 (Serdar): sembol, glif, logo, isimler siyah; burc adlari antrasit; arka mesaj siyah, isimler antrasit
ANTRASIT = (62, 64, 70)
# Aegean Tile KARAR 17 Eki 2026 (Serdar, ON-2 + ARKA-2): sembol, glif, logo, isimler lacivert; burc adlari kobalt; arka mesaj lacivert, isimler kobalt
AE_LAC, AE_KOB = (10, 36, 120), (0, 68, 184)
AE_GLIF, AE_ISIM, AE_BURC, AE_MESAJ, AE_AISIM = AE_LAC, AE_LAC, AE_KOB, AE_LAC, AE_KOB
# Mediterranean oge renkleri
MD_GLIF, MD_ISIM, MD_BURC, MD_MESAJ, MD_AISIM = MED, MED, SEA, MED, SEA   # kilit 17.10: ON-3 + ARKA-3
PL_GLIF, PL_ISIM, PL_BURC, PL_MESAJ, PL_AISIM = BLACK, BLACK, ANTRASIT, BLACK, ANTRASIT
import os as _os, json as _json
if _os.environ.get("RENK"):          # renk denemesi: {"SABIT": [r,g,b], ...}
    for _k, _v in _json.loads(_os.environ["RENK"]).items():
        globals()[_k] = tuple(_v)

F_SERIF, F_ITAL = "EBGaramond[wght].ttf", "EBGaramond-Italic[wght].ttf"


def font(ad, px, w=500):
    f = ImageFont.truetype(str(FNT / ad), max(4, int(round(px))))
    try:
        f.set_variation_by_axes([w])
    except Exception:
        pass
    return f


# ---------------- oge tanimlari ----------------
def T(metin, kutu, renk, ad=F_SERIF, w=500, aralik=0.0, olcu="yuk", genis=None, hedef_mm=None):
    """olcu: yuk = kutu yuksekligi buyuk harf (cap) boyu; gen = kutu genisligine sigdir.
    genis=(x0, x1): uzun metin icin dis sinirlar. Metin kutuya sigiyorsa onaylı gorunum aynen kalir;
    sigmazsa harf boyu hedef_mm'e kadar buyutulup genis sinirlar icinde (kutu merkezine en yakin) yazilir."""
    return dict(tip="yazi", metin=metin, kutu=kutu, renk=renk, font=ad, w=w, aralik=aralik, olcu=olcu,
                genis=genis, hedef_mm=hedef_mm)


def MESAJ(satirlar, ust, cap, aralik_satir, renk, ad=F_SERIF, maxw=720, harf=0.0, cx=0):
    """Cok satirli mesaj: tum satirlar ayni punto (ayni cap yuksekligi), sabit satir araligi."""
    out = []
    for i, m in enumerate(satirlar):
        y0 = ust + i * aralik_satir
        o = T(m, (cx - maxw / 2, y0, cx + maxw / 2, y0 + cap), renk, ad=ad, aralik=harf)
        o["grup"] = f"mesaj{ust}"
        out.append(o)
    return out


def MESAJ1(metin, cy, cap, maxw, renk, ad=F_SERIF, harf=0.0, cx=0, genis=None):
    """Tek satir mesaj (musteri metni): cap yuksekligi en fazla 'cap'; uzun metin maxw'e sigacak kadar kuculur,
    satirin dikey ortasi sabit kalir."""
    if _os0.environ.get("MESAJ"):        # musteri mesaji denemesi; buyuk harfli stilde buyuk harf kalir
        metin = _os0.environ["MESAJ"].upper() if metin.isupper() else _os0.environ["MESAJ"]
    return T(metin, (cx - maxw / 2, cy - cap / 2, cx + maxw / 2, cy + cap / 2), renk, ad=ad, aralik=harf,
             genis=genis, hedef_mm=MESAJ_MM if genis else None)


def ALT(y, cx, renk, isim_renk, gh=80, ic=40, bc=28, maxw=230, g1=30, g2=45, burc_w=440, burc_renk=None,
        dis_sol=400, dis_sag=400, burc_dis=380):
    """Botanical duzeni: iki burc glifi, altlarinda isimler, ortada logo (sonsuz), en altta burc adlari."""
    y2 = y + gh + g1
    y3 = y2 + ic + g2
    # isimler glifin altinda ortali; ic kenar logodan en az 60 birim uzakta kalacak sekilde kutu daraltilir
    maxw = min(maxw, 2 * (cx - 60))
    return [*ISIM_SATIRI(y, gh, y2, ic, renk, isim_renk, renk, g=75, maxw=maxw, dis_sol=dis_sol, dis_sag=dis_sag),
            T(BURC, (-burc_w / 2, y3, burc_w / 2, y3 + bc), burc_renk or renk, aralik=8,
              genis=(-burc_dis, burc_dis), hedef_mm=BURC_MM)]


GLIF_MIN = 100     # iki kisa isimde glifler birbirine yaklasmasin: glif merkezi ortadan en az bu kadar uzakta


def ISIM_SATIRI(y_glif, gh, y_isim, ic, glif_renk, isim_renk, logo_renk, g=60, maxw=230, dis_sol=400, dis_sag=400,
                glif_w=120, logo=(34, 12)):
    """Poster duzeni: logo (sonsuz) tam ortada; isimler logoya ESIT uzaklikta (sol isim saga, sag isim sola dayali);
    her burc glifi kendi isminin tam ustunde ortali. Boylece satir, uzun/kisa isimde de logoya gore simetrik kalir."""
    a, b = ISIM1.upper(), ISIM2.upper()
    o1 = T(a, (-g - maxw, y_isim, -g, y_isim + ic), isim_renk, aralik=2, genis=(-dis_sol, -g), hedef_mm=ISIM_MM)
    o2 = T(b, (g, y_isim, g + maxw, y_isim + ic), isim_renk, aralik=2, genis=(g, dis_sag), hedef_mm=ISIM_MM)
    o1["hiza"], o2["hiza"] = "sag", "sol"
    o1["grup"] = o2["grup"] = "isim"
    s1 = S((-glif_w / 2, y_glif, glif_w / 2, y_glif + gh), glif_renk, "sol")
    s2 = S((-glif_w / 2, y_glif, glif_w / 2, y_glif + gh), glif_renk, "sag")
    s1["bagli"], s1["yon"], s2["bagli"], s2["yon"] = o1, -1, o2, 1
    lg = dict(tip="sonsuz", kutu=(-logo[0], y_isim + ic / 2 - logo[1], logo[0], y_isim + ic / 2 + logo[1]), renk=logo_renk)
    # satir ortalama: "ISIM1 ∞ ISIM2" blogunun tamami yuz ortasina ortalanir (burc satiri gibi)
    sat = dict(sol=o1, sag=o2, logo=lg, g=g, D=min(dis_sol, dis_sag))
    o1["satir"] = sat
    o1["_satir_ref"] = o2["_satir_ref"] = sat
    return [o1, o2, s1, s2, lg]


def S(kutu, renk, ad="ana", alan=False, maxg=None):
    """alan=True: referanstaki sembolle ayni gorsel alan (geometrik ortalama), merkez ayni.
    maxg: yatay sembol icin izin verilen en buyuk genislik (yanlari bos stillerde); yoksa Cancer-Libra zarfi +%5."""
    return dict(tip="sembol", kutu=kutu, renk=renk, ad=ad, alan=alan, maxg=maxg)


def A(dosya, kutu, kirp=None, cevir=False, esnet=False, yatay_tekrar=False, kalinlas=0):
    return dict(tip="susleme", dosya=dosya, kutu=kutu, kirp=kirp, cevir=cevir, esnet=esnet, tekrar=yatay_tekrar,
                kalinlas=kalinlas)


def ISIM_IKI(k1, k2, renk, aralik=2, buyuk=True, genis=(None, None)):
    """Iki isim, referanstaki kendi kutularinda; ikisi ayni punto."""
    a, b = (ISIM1.upper(), ISIM2.upper()) if buyuk else (ISIM1, ISIM2)
    o1 = T(a, k1, renk, aralik=aralik, genis=genis[0], hedef_mm=ISIM_MM)
    o2 = T(b, k2, renk, aralik=aralik, genis=genis[1], hedef_mm=ISIM_MM)
    o1["grup"] = o2["grup"] = "isim"
    return [o1, o2]


def ISIMLER(cx, y0, y1, renk, buyuk=True, maxw=300, aralik=2):
    a, b = (ISIM1.upper(), ISIM2.upper()) if buyuk else (ISIM1, ISIM2)
    o1 = T(a, (-cx - maxw / 2, y0, -cx + maxw / 2, y1), renk, aralik=aralik)
    o2 = T(b, (cx - maxw / 2, y0, cx + maxw / 2, y1), renk, aralik=aralik)
    o1["grup"] = o2["grup"] = "isim"
    return [o1, o2]


def GLIFLER(cx, y0, y1, renk):
    return [S((-cx - 60, y0, -cx + 60, y1), renk, "sol"), S((cx - 60, y0, cx + 60, y1), renk, "sag")]


def IP(noktalar, ilmek, kalin, renk):
    """Promise Line ipi: noktalar uzerinden yumusak egri + kucuk ilmek (merkez, yaricap)."""
    return dict(tip="ip", noktalar=noktalar, ilmek=ilmek, kalin=kalin, renk=renk,
                kutu=(min(p[0] for p in noktalar), min(p[1] for p in noktalar),
                      max(p[0] for p in noktalar), max(p[1] for p in noktalar)))


def AYRAC(y, x0, x1, renk, yildiz=(30, 70)):
    return dict(tip="ayrac", kutu=(x0, y - yildiz[1] / 2, x1, y + yildiz[1] / 2), y=y, renk=renk, yildiz=yildiz)


STILLER = [
    dict(no="01", ad="Botanical", on=[
        A("B1_Botanical_on_sol_dal", (-478, -485, -195, 565), esnet=True),
        A("B2_Botanical_on_sag_dal", (190, -450, 468, 565), esnet=True),
        S((-252, -372, 252, 152), GREEN_SEM, alan=True),
        *ISIM_SATIRI(160, 90, 292, 40, GREEN, TERRA, GREEN, g=80, maxw=230, dis_sol=300, dis_sag=300,
                     glif_w=110, logo=(47, 16)),
        T(BURC, (-200, 392, 200, 422), GREEN, aralik=8, genis=(-230, 230), hedef_mm=BURC_MM),
    ], arka=[
        A("B3_Botanical_arka_celenk", (-455, -445, 445, 505)),
        MESAJ1("Rooted in love", -60, 70, 500, TERRA, cx=5, genis=(-265, 275)),
        T(f"{ISIM1} & {ISIM2}", (-200, 75, 210, 115), GREEN),
    ]),
    dict(no="02", ad="Gold", on=[
        dict(tip="halkali", kutu=(-395, -445, 395, 205), renk=GOLD_SEM),
        *ISIM_SATIRI(242, 100, 392, 55, G_GLIF, G_ISIM, G_LOGO, g=75, maxw=270, dis_sol=400, dis_sag=400,
                     glif_w=108, logo=(34, 12)),
        T(BURC, (-255, 505, 255, 545), G_BURC, aralik=12, genis=(-380, 380), hedef_mm=BURC_MM),
    ], arka=[
        MESAJ1("Same Stars Same Heart" if AYNI_BURC else "Different Stars Same Heart", -75, 70, 800, G_MESAJ, ad=F_ITAL),  # ONERI 17 Eki: ayni burcta "Different" anlamsiz
        T(f"{ISIM1} & {ISIM2}", (-222, 30, 202, 72), G_AISIM, aralik=2),
        AYRAC(155, -205, 195, G_AYRAC, (38, 95)),
    ]),
    dict(no="03", ad="Nazar Bond", on=[
        A("N1_NazarBond_on_sol_dal", (-317, -445, -36, 124)),
        A("N2_NazarBond_on_firca_hilal", (50, -379, 322, 151)),
        A("N3_NazarBond_on_nazar", (-31, -500, 63, -319), kirp=(0.0, 0.70)),
        S((-135, -274, 195, 62), NB_SEM, alan=True, maxg=420),
        *ALT(185, 190, NB_GLIF, NB_ISIM, burc_renk=NB_BURC),
    ], arka=[
        A("N5_NazarBond_arka_zincir", (-60, -480, 60, -250), kirp=(0.0, 0.33)),
        MESAJ1("A LOVE WORTH PROTECTING", -95, 58, 800, NB_MESAJ, harf=2),
        T(f"{ISIM1} & {ISIM2}", (-220, -20, 220, 16), NB_AISIM, aralik=2),
        A("N5_NazarBond_arka_zincir", (-70, 120, 70, 545), kirp=(0.36, 1.0)),
        A("N4_NazarBond_arka_dallar", (-470, 5, 470, 545)),
    ]),
    dict(no="04", ad="Rose Ribbon", on=[
        A("R1_RoseRibbon_on_sag_ust", (50, -465, 465, 35)),
        A("R2_RoseRibbon_on_sol_alt", (-505, 229, -268, 545)),   # 17.10: gul asagi (uzun isimlere yer)
        S((-205, -330, 205, 90), BURG_SEM, alan=True),
        *ALT(125, 175, RR_GLIF, RR_ISIM, maxw=230, burc_w=400, burc_renk=RR_BURC, dis_sol=360, burc_dis=345),
    ], arka=[
        dict(tip="kurdele", kutu=(-325, -405, 405, 245), nazar=((25, -50), 185)),
        A("R4_RoseRibbon_arka_sol", (-445, -320, -95, 145)),
        A("R5_RoseRibbon_arka_sag_tomurcuk", (255, -275, 470, 60)),
        MESAJ1("A love worth protecting", 262, 60, 640, RR_MESAJ, cx=20),
        T(f"{ISIM1} & {ISIM2}", (-180, 322, 220, 358), RR_AISIM),
    ]),
    dict(no="05", ad="Promise Line", on=[
        S((-215, -400, 215, 40), BLACK_SEM, alan=True, maxg=720),
        *ALT(80, 195, PL_GLIF, PL_ISIM, burc_renk=PL_BURC),
    ], sarma=dict(
        on=[(-452, 372), (-300, 445), (-150, 485), (0, 500), (150, 490), (300, 450), (452, 368)],
        arka=[(-452, 370), (-250, 450), (-50, 505), (100, 512), (300, 485), (452, 400)],
        ilmek=[("on", -228, 38), ("arka", 300, 40)], kalin=7, renk=BLACK),
    arka=[
        A("P1_PromiseLine_eller", (-405, -465, 400, 120), kalinlas=3),
        MESAJ1("A love worth protecting", 215, 64, 740, PL_MESAJ),
        T(f"{ISIM1} & {ISIM2}", (-200, 282, 200, 318), PL_AISIM),
    ]),
    dict(no="06", ad="Aegean Tile", on=[
        A("A1_Aegean_yan_bordur", (-458, -470, -398, 490)),
        A("A1_Aegean_yan_bordur", (400, -470, 460, 490)),
        A("A3_Aegean_kemer", (-368, -468, 378, 478), esnet=True),
        A("A2_Aegean_alt_bordur", (-400, 480, 410, 560), yatay_tekrar=True),
        A("A4_Aegean_on_ust_nazar", (-58, -440, 95, -160)),
        S((-160, -150, 170, 150), AEG_SEM, alan=True, maxg=560),
        *ALT(180, 170, AE_GLIF, AE_ISIM, burc_renk=AE_BURC, gh=70, ic=35, bc=24, maxw=220, g2=40, burc_w=380,
             dis_sol=330, dis_sag=330, burc_dis=330),
    ], arka=[
        A("A1_Aegean_yan_bordur", (-458, -470, -398, 490)),
        A("A1_Aegean_yan_bordur", (400, -470, 460, 490)),
        A("A3_Aegean_kemer", (-368, -468, 378, 478), esnet=True),
        A("A2_Aegean_alt_bordur", (-400, 480, 410, 560), yatay_tekrar=True),
        A("A5_Aegean_arka_nazar", (-110, -410, 120, 5)),
        MESAJ1("A love worth protecting", 110, 64, 620, AE_MESAJ, cx=5),
        T(f"{ISIM1} & {ISIM2}", (-190, 172, 200, 206), AE_AISIM),
        A("A6_Aegean_lotus", (-110, 262, 120, 342)),
    ]),
    dict(no="07", ad="Mediterranean", on=[
        A("M2_Mediterranean_nazar_gunes", (-72, -470, 72, -326)),
        S((-180, -305, 180, 80), MED_SEM, alan=True, maxg=680),
        *ALT(105, 185, MD_GLIF, MD_ISIM, burc_renk=MD_BURC, gh=70, ic=38, bc=24, maxw=230, g2=40, burc_w=380),
        A("M1_Mediterranean_deniz", (-468, 360, 468, 545), esnet=True),
    ], arka=[
        A("M2_Mediterranean_nazar_gunes", (-220, -420, 220, 20)),
        MESAJ1("A love worth protecting", 120, 64, 740, MD_MESAJ),
        T(f"{ISIM1} & {ISIM2}", (-200, 178, 200, 214), MD_AISIM),
        A("M1_Mediterranean_deniz", (-468, 360, 468, 545), esnet=True),
    ]),
]


# ---------------- cizim yardimcilari ----------------
def maske(ad):
    return Image.open(SEM / f"{ad}.png").getchannel("A")


BOSLUK_TOL = 2.0   # px (on-gorunus), olcum gurultusu payi


def bosluk_px(edt, m, k, cx, cy):
    """Sembol (m maskesi, k olcegi, merkez cx,cy) ile sus murekkebi arasindaki en kucuk uzaklik (px)."""
    mm = np.asarray(m.resize((max(1, round(m.width * k)), max(1, round(m.height * k))), Image.LANCZOS)) > 76
    x0, y0 = int(round(cx - mm.shape[1] / 2)), int(round(cy - mm.shape[0] / 2))
    ys, xs = np.where(mm)
    ys, xs = ys + y0, xs + x0
    ic = (ys >= 0) & (ys < edt.shape[0]) & (xs >= 0) & (xs < edt.shape[1])
    if not ic.all():
        return 0.0
    return float(edt[ys, xs].min())


SUS_TIPLERI = ("susleme", "kurdele", "ip", "ayrac", "halkali")


def boya(im, m, x, y, renk):
    im.paste(Image.new("RGB", m.size, renk), (int(round(x)), int(round(y))), m)


_SUS = {}


def susleme_yukle(ad):
    if ad not in _SUS:
        a = np.asarray(Image.open(SUS / f"{ad}.png").convert("RGB")).astype(np.float32)
        # zemin saf beyaza: 250+ -> 255, gerisi orantili acilir
        a = np.clip(a * 255.0 / 250.0, 0, 255)
        a[a.min(-1) >= 252] = 255
        m = a.min(-1) < 240
        ys, xs = np.where(m)
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        _SUS[ad] = a
    return _SUS[ad]


def carp(im, parca, x, y):
    x, y = int(round(x)), int(round(y))
    h, w = parca.shape[:2]
    X0, Y0 = max(0, x), max(0, y)
    X1, Y1 = min(im.width, x + w), min(im.height, y + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    alan = np.asarray(im.crop((X0, Y0, X1, Y1))).astype(np.float32)
    p = parca[Y0 - y:Y1 - y, X0 - x:X1 - x]
    im.paste(Image.fromarray(np.clip(alan * p / 255.0, 0, 255).astype(np.uint8)), (X0, Y0))


def kap_yuk(f, metin):
    """Buyuk harf (cap) yuksekligi ve x-yuksekligi (px, 100 punto icin)."""
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    H = d.textbbox((0, 0), "H", font=f)
    x = d.textbbox((0, 0), "x", font=f)
    return H[3] - H[1], x[3] - x[1]


def yazi_px(o, kutu):
    px = yazi_px_kutu(o, kutu)
    if o.get("genis") and o.get("hedef_mm"):
        don = o["_don"]
        gx0, gx1 = don(o["genis"][0], 0)[0], don(o["genis"][1], 0)[0]
        f100 = font(o["font"], 100, o["w"])
        cap100 = kap_yuk(f100, o["metin"])[0]
        px_hedef = 100 * (o["hedef_mm"] / 25.4 * DPI) / cap100
        px = max(px, min(yazi_px_kutu(o, (gx0, kutu[1], gx1, kutu[3])), px_hedef))
    return px


def yazi_px_kutu(o, kutu):
    x0, y0, x1, y1 = kutu
    f100 = font(o["font"], 100, o["w"])
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    ar100 = o["aralik"] * 100 / 60.0
    gen100 = sum(d.textlength(c, font=f100) for c in o["metin"]) + ar100 * (len(o["metin"]) - 1)
    cap, xh = kap_yuk(f100, o["metin"])
    if o["olcu"] == "gen":
        return 100 * (x1 - x0) / gen100
    ref = xh if o["olcu"] == "xh" else cap
    px = 100 * (y1 - y0) / ref
    return min(px, 100 * (x1 - x0) / gen100)


def yazi_ciz(im, o, kutu, px):
    x0, y0, x1, y1 = kutu
    d = ImageDraw.Draw(im)
    f = font(o["font"], px, o["w"])
    ar = o["aralik"] * px / 60.0
    genis = sum(d.textlength(c, font=f) for c in o["metin"]) + ar * (len(o["metin"]) - 1)
    cap, xh = kap_yuk(f, o["metin"])
    ref = xh if o["olcu"] == "xh" else cap
    # taban cizgisi: kutunun alti (cap/xh hizasi); 'gen' modunda kutu ortasi
    asc = f.getmetrics()[0]
    taban = y1 - max(0, (y1 - y0) - ref) / 2 if o["olcu"] != "gen" else (y0 + y1) / 2 + cap / 2
    y = taban - asc
    if _os0.environ.get("OLCU"):
        print(f"OLCU|{o['metin']}|{cap / 300 * 25.4:.2f}")
    x = (x0 + x1) / 2 - genis / 2
    if o.get("_x_zorla") is not None:
        x = o["_x_zorla"]
    elif o.get("hiza") == "sag":
        x = x1 - genis
    elif o.get("hiza") == "sol":
        x = x0
    elif o.get("genis"):
        gx0, gx1 = o["_don"](o["genis"][0], 0)[0], o["_don"](o["genis"][1], 0)[0]
        if px > yazi_px_kutu(o, kutu) * 1.001:   # yalniz buyutulmus (kutuya sigmayan) metin kaydirilir
            x = max(min(gx0, x0), min(x, max(gx1, x1) - genis))
    o["_orta_px"] = x + genis / 2
    if _os0.environ.get("MERKEZ"):
        print(f"MERKEZ|{o['metin']}|{x - TV:.1f}|{x + genis - TV:.1f}")
    for c in o["metin"]:
        d.text((x, y), c, font=f, fill=o["renk"])
        x += d.textlength(c, font=f) + ar


def yildiz4(d, cx, cy, w, h, renk):
    t = np.linspace(0, 2 * np.pi, 240)
    xs = cx + (w / 2) * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** 3
    ys = cy + (h / 2) * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** 3
    d.polygon(list(zip(xs, ys)), fill=renk)


def catmull(pts, n=40):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(pts[-1]))
    return [tuple(p) for p in out]


def oge_ciz(im, o, kutu, s):
    x0, y0, x1, y1 = kutu
    d = ImageDraw.Draw(im)
    t = o["tip"]
    if t == "yazi":
        yazi_ciz(im, o, kutu, o.get("px_zorla") or yazi_px(o, kutu))
    elif t == "sembol":
        if o.get("bagli"):
            mx = o["bagli"]["_orta_px"]
            lc = o["bagli"]["_satir_ref"]["logo"]["_cx_zorla"]
            mx = lc + o["yon"] * max(abs(mx - lc), GLIF_MIN * s)
            yw = (x1 - x0) / 2
            x0, x1 = mx - yw, mx + yw
        m = maske(o["ad"])
        k = min((y1 - y0) / m.height, (x1 - x0) / m.width)
        if o.get("alan"):
            k = math.sqrt((y1 - y0) * (x1 - x0) / (m.height * m.width))
            k_ref = math.sqrt((y1 - y0) * (x1 - x0) / (REF_ANA[0] * REF_ANA[1]))
            if _os0.environ.get("SEMBOL_KURAL", "standart") != "alan":
                k = k_ref   # STANDART 17 Eki: posterdeki olcek, tum ciftlerde ayni (= Cancer-Libra olcegi)
            gmax = o["maxg"] * s if o.get("maxg") else 1.05 * REF_ANA[0] * k_ref
            k = min(k, gmax / m.width, 1.05 * REF_ANA[1] * k_ref / m.height)
            if o.get("_edt") is not None:   # STANDART: suslere en az Cancer-Libra kadar bosluk; dar ise %1 adimlarla kucult
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                hedef = o["_hedef"]
                while k > 0.3 * k_ref and bosluk_px(o["_edt"], m, k, cx, cy) < hedef - BOSLUK_TOL:
                    k *= 0.99
                o["_olcek_orani"] = k / k_ref
        m = m.resize((max(1, round(m.width * k)), max(1, round(m.height * k))), Image.LANCZOS)
        renk = (0, 255, 0) if (_os0.environ.get("SEMBOL_TEST_RENK") and o["ad"] == "ana" and not o.get("bagli")) else o["renk"]   # olcum icin
        boya(im, m, (x0 + x1) / 2 - m.width / 2, (y0 + y1) / 2 - m.height / 2, renk)
    elif t == "sonsuz":
        m = maske("sonsuz")
        k = (x1 - x0) / m.width
        m = m.resize((max(1, round(m.width * k)), max(1, round(m.height * k))), Image.LANCZOS)
        mx = o["_cx_zorla"] if o.get("_cx_zorla") is not None else (x0 + x1) / 2
        boya(im, m, mx - m.width / 2, (y0 + y1) / 2 - m.height / 2, o["renk"])
    elif t == "halkali":
        W = x1 - x0
        for ad, kalin in (("halka_ring", True), ("halka_sembol", False)):
            m = maske(ad)
            k = W / m.width
            m = m.resize((max(1, round(m.width * k)), max(1, round(m.height * k))), Image.LANCZOS)
            if kalin:
                m = m.filter(ImageFilter.MaxFilter(3))
            boya(im, m, x0, y0, o["renk"])
    elif t == "susleme":
        a = susleme_yukle(o["dosya"])
        if o["kirp"]:
            h = a.shape[0]
            a = a[int(h * o["kirp"][0]):int(h * o["kirp"][1])]
            m = a.min(-1) < 240
            ys, xs = np.where(m)
            a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if o["cevir"]:
            a = a[:, ::-1]
        bw, bh = x1 - x0, y1 - y0
        img = Image.fromarray(a.astype(np.uint8))
        if o["tekrar"]:
            k = bh / img.height
            img = img.resize((max(1, round(img.width * k)), round(bh)), Image.LANCZOS)
            if img.width < bw:
                tam = Image.new("RGB", (int(bw) + 2, img.height), "white")
                for xx in range(0, int(bw) + 2, img.width):
                    tam.paste(img, (xx, 0))
                img = tam
            ox = (img.width - bw) / 2
            img = img.crop((int(ox), 0, int(ox + bw), img.height))
        elif o["esnet"]:
            img = img.resize((max(1, round(bw)), max(1, round(bh))), Image.LANCZOS)
        else:
            k = min(bw / img.width, bh / img.height)
            img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
        if o.get("kalinlas"):
            img = img.filter(ImageFilter.MinFilter(o["kalinlas"]))
        carp(im, np.asarray(img).astype(np.float32), (x0 + x1) / 2 - img.width / 2, (y0 + y1) / 2 - img.height / 2)
    elif t == "kurdele":
        # R3: fiyonk ve nazar ayri; nazar referanstaki yerine, zincir uzatilir
        a = np.asarray(Image.open(SUS / "R3_RoseRibbon_arka_kurdele.png").convert("RGB")).astype(np.float32)
        a = np.clip(a * 255.0 / 250.0, 0, 255); a[a.min(-1) >= 252] = 255
        NX, NY, NR = 542, 714, 162
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        daire = (xx - NX) ** 2 + (yy - NY) ** 2 <= NR ** 2
        naz = a[NY - NR:NY + NR, NX - NR:NX + NR].copy()
        nm = daire[NY - NR:NY + NR, NX - NR:NX + NR]
        naz[~nm] = 255
        a[daire] = 255
        CX0, CX1, CY0 = 106, 1021, 155
        CY1 = 1300
        kx = (x1 - x0) / (CX1 - CX0)
        ky = (y1 - y0) / (CY1 - CY0)
        fy = a[CY0:CY1, CX0:CX1 + 1]
        img = Image.fromarray(fy.astype(np.uint8)).resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS)
        carp(im, np.asarray(img).astype(np.float32), x0, y0)
        zx = x0 + (NX - CX0) * kx
        zy = y0 + (NY - NR - CY0) * ky
        (ncx, ncy), nd = o["nazar"]
        nd = nd * s
        ImageDraw.Draw(im).line((zx, zy - 2, zx, o["_don"](0, ncy)[1] - nd / 2 + 2), fill=(196, 92, 104), width=max(2, round(4 * s)))
        nimg = Image.fromarray(naz.astype(np.uint8)).resize((round(nd * 2 * NR / 310), round(nd * 2 * NR / 310)), Image.LANCZOS)
        carp(im, np.asarray(nimg).astype(np.float32), zx - nimg.width / 2, o["_don"](0, ncy)[1] - nimg.height / 2)
    elif t == "ip":
        don = o["_don"]
        pts = catmull([don(*p) for p in o["noktalar"]])
        hx, r = don(*o["ilmek"][0])[0], o["ilmek"][1] * s
        j = int(np.argmin([abs(p[0] - hx) for p in pts]))
        px_, py_ = pts[j]
        # ilmek: egrinin ustunde, alt noktasi egriye degen hafif egik oval
        aci = np.linspace(math.pi / 2, math.pi / 2 - 2 * math.pi, 70)
        ilmek = [(px_ + r * 0.85 * math.cos(a) + 0.35 * r * (1 - math.sin(a)), py_ - r + r * math.sin(a)) for a in aci]
        tum = pts[:j] + ilmek + pts[j:]
        d.line(tum, fill=o["renk"], width=max(2, round(o["kalin"] * s)), joint="curve")
    elif t == "ayrac":
        cy = (y0 + y1) / 2
        yw, yh = o["yildiz"][0] * s, o["yildiz"][1] * s
        mx = (x0 + x1) / 2
        kal = max(2, round(3 * s))
        d.line((x0, cy, mx - yw * 1.6, cy), fill=o["renk"], width=kal)
        d.line((mx + yw * 1.6, cy, x1, cy), fill=o["renk"], width=kal)
        yildiz4(d, mx, cy, yw, yh, o["renk"])


def bbox(ogeler):
    xs0, ys0, xs1, ys1 = zip(*[o["kutu"] for o in ogeler])
    return min(xs0), min(ys0), max(xs1), max(ys1)


def metin_gen(o, px):
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    f = font(o["font"], px, o["w"])
    return sum(d.textlength(c, font=f) for c in o["metin"]) + o["aralik"] * px / 60.0 * (len(o["metin"]) - 1)


def satir_yerlestir(sat, s):
    """ISIM1 [g] ∞ [g] ISIM2: blok genisligi wL + 2g + wR, blok yuz ortasina ortali.
    Blok dis sinirlari (+-D) asarsa iki ismin puntosu birlikte kucultulur."""
    o1, o2, lg = sat["sol"], sat["sag"], sat["logo"]
    px = o1["px_zorla"]
    g, D = sat["g"] * s, sat["D"] * s
    wL, wR = metin_gen(o1, px), metin_gen(o2, px)
    if wL + wR + 2 * g > 2 * D:
        px *= (2 * D - 2 * g) / (wL + wR)
        wL, wR = metin_gen(o1, px), metin_gen(o2, px)
    o1["px_zorla"] = o2["px_zorla"] = px
    sol = TV - (wL + wR + 2 * g) / 2
    o1["_x_zorla"], o2["_x_zorla"] = sol, sol + wL + 2 * g
    lg["_cx_zorla"] = sol + wL + g


def yuz_tuvali(ogeler, s):
    """On-gorunus tuvali: genislik 2*TV, yukseklik FH; merkez = yuz ortasi."""
    im = Image.new("RGB", (2 * TV, FH), "white")
    don = lambda x, y: (TV + x * s, FH / 2 + y * s)
    for o in ogeler:
        o["_don"] = don
    for g in {o["grup"] for o in ogeler if o.get("grup")}:
        uye = [o for o in ogeler if o.get("grup") == g]
        pxs = []
        for o in uye:
            (a, b), (c, e) = don(*o["kutu"][:2]), don(*o["kutu"][2:])
            pxs.append(yazi_px(o, (a, b, c, e)))
        for o in uye:
            o["px_zorla"] = min(pxs)
    for o in ogeler:
        if o.get("satir"):
            satir_yerlestir(o["satir"], s)
    for o in ogeler:
        o["_don"] = don
    ana = [o for o in ogeler if o["tip"] == "sembol" and o.get("alan") and o["ad"] == "ana" and not o.get("bagli")]
    if ana and _os0.environ.get("SEMBOL_KURAL", "standart") != "alan":
        sus = Image.new("RGB", (2 * TV, FH), "white")
        for o in ogeler:
            if o["tip"] in SUS_TIPLERI:
                (a, b), (c, e) = don(*o["kutu"][:2]), don(*o["kutu"][2:])
                oge_ciz(sus, o, (a, b, c, e), s)
        murekkep = np.asarray(sus).min(-1) < 215
        edt = ndimage.distance_transform_edt(~murekkep) if murekkep.any() else np.full(murekkep.shape, 1e9)
        o = ana[0]
        (a, b), (c, e) = don(*o["kutu"][:2]), don(*o["kutu"][2:])
        ref = Image.open(SEM.parent / "CANCER_LIBRA" / "ana.png").getchannel("A")
        k_ref = math.sqrt((e - b) * (c - a) / (REF_ANA[0] * REF_ANA[1]))
        o["_edt"], o["_hedef"] = edt, bosluk_px(edt, ref, k_ref, (a + c) / 2, (b + e) / 2)
    for o in sorted(ogeler, key=lambda o: 1 if o.get("bagli") else 0):
        (a, b), (c, e) = don(*o["kutu"][:2]), don(*o["kutu"][2:])
        oge_ciz(im, o, (a, b, c, e), s)
    return im


def egrile(tuval, yuz, baski):
    """On-gorunus tuvalini silindir yayina acar: yay a -> gorunus x = R sin(a/R)."""
    t = np.asarray(tuval).astype(np.float32)
    fx = np.arange(FW, dtype=np.float32)
    a = fx - FACE[yuz]
    gecerli = np.abs(a) < RK * math.pi / 2
    v = RK * np.sin(np.clip(a / RK, -math.pi / 2, math.pi / 2))
    kx = v + TV - 0.5
    gecerli &= (kx >= 0) & (kx <= 2 * TV - 1)
    kol = np.where(gecerli)[0]
    yy = np.arange(FH)[:, None] * np.ones((1, len(kol)))
    xx = np.ones((FH, 1)) * kx[kol][None, :]
    for ch in range(3):
        parca = ndimage.map_coordinates(t[..., ch], [yy, xx], order=1, mode="nearest")
        baski[:, kol, ch] = np.minimum(baski[:, kol, ch], parca)


def baski_uret(st):
    tum = st["on"] + st["arka"]
    mx = max(max(abs(o["kutu"][0]), abs(o["kutu"][2])) for o in tum)
    sus = [o for o in tum if o["tip"] in ("susleme", "kurdele")]
    ana = [o for o in tum if o["tip"] not in ("susleme", "kurdele")]
    my_ana = max(max(abs(o["kutu"][1]), abs(o["kutu"][3])) for o in ana)
    my_sus = max([max(abs(o["kutu"][1]), abs(o["kutu"][3])) for o in sus] or [1])
    # yazi / sembol / ip: kenardan >= 28 px (0.09 inc); susleme baski kenarina kadar gidebilir
    s = min(1.0, 497 / my_ana, 524 / my_sus, X_MAX / mx)
    baski = np.full((FH, FW, 3), 255, np.float32)
    for yuz in ("on", "arka"):
        egrile(yuz_tuvali(st[yuz], s), yuz, baski)
    if st.get("sarma"):
        sarma_ip(baski, st["sarma"], s)
    return Image.fromarray(np.clip(baski, 0, 255).astype(np.uint8)), s


def sarma_ip(baski, sp, s):
    """Promise Line ipi: tum baski boyunca TEK cizgi (kulp tarafindaki iki kenarda biter).
    Noktalar on-gorunus biriminde verilir; yay koordinatina cevrilir."""
    def yay(yuz, v, y):
        return (FACE[yuz] + RK * math.asin(max(-0.999, min(0.999, v * s / RK))), FH / 2 + y * s)
    on = [yay("on", *p) for p in sp["on"]]
    ar = [yay("arka", *p) for p in sp["arka"]]
    yol = [(0, on[0][1] - 6)] + on + [(FW / 2, FH / 2 + 330 * s)] + ar + [(FW, ar[-1][1] - 6)]
    pts = catmull(yol, 60)
    for yuz, v, r in sp["ilmek"]:
        hx = yay(yuz, v, 0)[0]
        r = r * s
        j = int(np.argmin([abs(p[0] - hx) for p in pts]))
        px_, py_ = pts[j]
        aci = np.linspace(math.pi / 2, math.pi / 2 - 2 * math.pi, 80)
        ilm = [(px_ + r * 0.85 * math.cos(a) + 0.35 * r * (1 - math.sin(a)), py_ - r + r * math.sin(a)) for a in aci]
        pts = pts[:j] + ilm + pts[j:]
    K = 3
    m = Image.new("L", (FW * K, FH * K), 0)
    ImageDraw.Draw(m).line([(x * K, y * K) for x, y in pts], fill=255, width=max(2, round(sp["kalin"] * s * K)), joint="curve")
    m = np.asarray(m.resize((FW, FH), Image.LANCZOS)).astype(np.float32)[..., None] / 255.0
    renk = np.array(sp["renk"], np.float32)
    baski[:] = baski * (1 - m) + renk * m


import os
if os.environ.get("TASARIM"):
    # s=1 on-gorunus tuvalleri (referansla ust uste kiyas icin)
    TD = OUT / "tasarim"; TD.mkdir(exist_ok=True)
    for st in STILLER:
        for yuz in ("on", "arka"):
            yuz_tuvali(st[yuz], 1.0).save(TD / f"{st['no']}_{yuz}.png")
    sys.exit(0)

if _os.environ.get("YALNIZ"):
    STILLER = [x for x in STILLER if x["no"] == _os.environ["YALNIZ"]]
t0 = time.time()
for i, st in enumerate(STILLER, 1):
    b, s = baski_uret(st)
    ad = st["ad"].replace(" ", "")
    b.save(OUT / f"KUPA_{st['no']}_{ad}_baski_2700x1050.png", dpi=(DPI, DPI))
    g = time.time() - t0
    print(f"{i}/{len(STILLER)}  {st['ad']}  olcek {s:.3f}  {g:.0f} sn  kalan ~{g / i * (len(STILLER) - i):.0f} sn  %{100 * i // len(STILLER)}")
print("bitti", OUT)
