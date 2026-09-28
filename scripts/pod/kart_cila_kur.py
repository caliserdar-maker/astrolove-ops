#!/usr/bin/env python3
"""CL sahne kartlari 06/09/10/11: ChatGPT cilali cerceveli bos sahneler (data/pod/gpt_sahne_cila, 1729x910).
Serdar 28 Eyl: atmosfer + cerceve + isik ChatGPT'den AYNEN; cerceve eklenmez, set_grade/sahne_isik uygulanmaz.
Yalniz cercevenin acikligi olculur (aciklik(): koyu ic dudagin ici) ve gercek poster oraya oturur.
Oran 11:14'ten farkli ise poster germe yok: kaplayacak sekilde olceklenir, merkezden kirpilir (<= %3, fazlasi DUR).
Poster kenarinda cok ince ic golge (cerceve dudaginin golgesi; isik sol-ustten).
Kart iskeleti ve metinler kart12/14/15/16_kur.py ile ayni (Garamond + Montserrat, ayni olcu/konum);
ust etiket (0,70)-(1500,140) ve alt serit (0,2130)-(3000,2250) main'deki mevcut kartin piksellerinden alinir.
Kullanim: kart_cila_kur.py KART SAHNE.png POSTER_KAYNAK.jpg ESKI_KART.jpg GARAMOND.ttf MONTSERRAT.ttf CIKIS.jpg [KONTROL.png]
  KART: 06 (hediye, BASKI_11x14 MB) | 09 (yatak, canli 04 CI) | 10 (calisma, canli 04 DB) | 11 (yemek, canli 04 PW)
"""
import math
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

BG = (237, 232, 226); NAVY_T = (25, 34, 49); SANS_T = (23, 25, 30)
PANEL_W, SX = 2710, 145
GAR_BOY = 51

# baslik, alt baslik, SY, alt satirlar [(metin, font, hedef genislik, y ofseti[, sabit punto])]; poster kirpimi
# 'Shown in ...' satiri: metin kisalinca hedef genislik puntoyu 89'a sisiriyordu (Serdar 28 Eyl) -> sabit 51
# (onayli kart14 v2 'Shown in Champagne Ivory with an Antique Gold frame.' puntosu; hediye satiri 50)
# 'baski' = BASKI_11x14 (rebate 5 mm / 279.4 x 355.6 mm); kutu = canli kart 04 kirpimi (rebate 5 / 406.4 x 508)
KARTLAR = {
    '06': dict(ad='06_hediye_sahne', baslik='A gift for your story.',
               alt="For anniversaries, engagements, weddings, Valentine's Day and birthdays.", SY=440,
               satirlar=[('Your two names and your own message, in one shared symbol.', 'GAR', 1208, 90)],
               poster='baski'),
    '09': dict(ad='09_yatak_sahne', baslik='Made for the room you share.',
               alt='A calm, personal piece for your bedroom or living room.', SY=420,
               satirlar=[('Shown in Champagne Ivory.', 'GAR', None, 45, GAR_BOY),
                         ('Five colors, thirteen sizes, four frame finishes.', 'MON', 760, 132)],
               poster=(2208, 499, 2733, 1152)),
    '10': dict(ad='10_calisma_sahne', baslik='Deep Black, bold and modern.',
               alt='A modern look for a living room, hallway or office.', SY=420,
               satirlar=[('Shown in Deep Black.', 'GAR', None, 45, GAR_BOY),
                         ('Every color comes in all four frame finishes.', 'MON', 740, 132)],
               poster=(1240, 500, 1760, 1150)),
    '11': dict(ad='11_yemek_sahne', baslik='Pure White, calm and airy.',
               alt='Light and calm, for a dining room or entryway.', SY=420,
               satirlar=[('Shown in Pure White.', 'GAR', None, 45, GAR_BOY),
                         ('Framed prints arrive ready to hang.', 'MON', 640, 132)],
               poster=(755, 1310, 1275, 1960)),
}
SAHNE_DOSYA = {'06': 'SAHNE_HEDIYE.png', '09': 'SAHNE_YATAK.png', '10': 'SAHNE_CALISMA.png', '11': 'SAHNE_YEMEK.png'}


def aciklik(G):
    """Girdi sahnede cercevenin acikligi (x0,y0,x1,y1) dahil, doluluk, kenar sapmasi (px).
    v2 sahneler (28 Eyl): ChatGPT beyazin kenarina ince gri gecis (237-249) + koyu ic dudak cizdi; min>238
    esigi gecis seridini disarida birakiyordu. Aciklik = koyu dudagin ici: acik-notr (min>200 & chroma<14)
    en buyuk bilesen, delik doldurulur; kenar = orta %80 satir/sutun uclarinin medyani (kose pahi sizintisina dayanikli).
    Sapma = orta %90'da kenar ucunun medyandan en buyuk uzakligi (<=1 ise eksene paralel, homografi gerekmez)."""
    A = np.asarray(G.convert('RGB')).astype(np.int16)
    m = (A.min(2) > 200) & ((A.max(2) - A.min(2)) < 14)
    lab, n = ndi.label(m)
    M = ndi.binary_fill_holes(lab == (np.argmax(ndi.sum(m, lab, range(1, n + 1))) + 1))
    ys, xs = np.nonzero(M)
    by0, by1, bx0, bx1 = ys.min(), ys.max(), xs.min(), xs.max()
    def uclar(eks, a0, a1, pay):
        ic = range(a0 + (a1 - a0) * pay // 100, a1 - (a1 - a0) * pay // 100 + 1)
        dizi = [np.flatnonzero(M[i] if eks == 0 else M[:, i]) for i in ic]
        return np.array([d.min() for d in dizi]), np.array([d.max() for d in dizi])
    L, R = uclar(0, by0, by1, 10); T, B = uclar(1, bx0, bx1, 10)
    x0, x1, y0, y1 = (int(np.median(v)) for v in (L, R, T, B))
    L5, R5 = uclar(0, by0, by1, 5); T5, B5 = uclar(1, bx0, bx1, 5)
    sapma = int(max(np.abs(L5 - x0).max(), np.abs(R5 - x1).max(), np.abs(T5 - y0).max(), np.abs(B5 - y1).max()))
    dolu = float(M[y0:y1 + 1, x0:x1 + 1].mean())
    return (x0, y0, x1, y1), dolu, sapma


def sahne_isle(G):
    """Kart scriptleriyle ayni: tam sahne 2710 genislige LANCZOS + UnsharpMask(2,60,2). Renk/isik degismez."""
    s = PANEL_W / G.width
    return G.resize((PANEL_W, round(G.height * s)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2)), s


def panel_aciklik(kutu, s):
    """Acikligin panel koordinatlari (disa yuvarlanir: kenarda beyaz gecis pikseli kalmaz). [X0,X1) x [Y0,Y1)"""
    x0, y0, x1, y1 = kutu
    return math.floor(x0 * s), math.floor(y0 * s), math.ceil((x1 + 1) * s), math.ceil((y1 + 1) * s)


def poster_hazirla(kart, kaynak, W, H):
    """Gercek poster: rebate kirpilir, (W,H)'yi kaplayacak sekilde olceklenir, merkezden kirpilir. Germe yok."""
    K = KARTLAR[kart]
    B = Image.open(kaynak).convert('RGB')
    if K['poster'] == 'baski':
        kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
    else:
        B = B.crop(K['poster'])
        kx, ky = round(B.width * 5 / 406.4), round(B.height * 5 / 508)
    B = B.crop((kx, ky, B.width - kx, B.height - ky))
    k = max(W / B.width, H / B.height)
    bw, bh = round(B.width * k), round(B.height * k)
    kirp = 1 - (W * H) / (bw * bh)                        # kirpilan alan orani
    kirp_eks = max(1 - W / bw, 1 - H / bh)                # en cok kirpilan eksen
    P = B.resize((bw, bh), Image.LANCZOS)
    L, T = (bw - W) // 2, (bh - H) // 2
    return P.crop((L, T, L + W, T + H)), kirp, kirp_eks


def ic_golge(P):
    """Cok ince ic golge: ust/sol (isik sol-ust) ~%18 -> 0 (tau 2.2 px), alt/sag ~%7 (tau 1.2 px)."""
    W, H = P.size
    x = np.arange(W, dtype=np.float32); y = np.arange(H, dtype=np.float32)
    g = np.ones((H, W), np.float32)
    g *= (1 - 0.18 * np.exp(-y / 2.2))[:, None]
    g *= (1 - 0.18 * np.exp(-x / 2.2))[None, :]
    g *= (1 - 0.07 * np.exp(-(H - 1 - y) / 1.2))[:, None]
    g *= (1 - 0.07 * np.exp(-(W - 1 - x) / 1.2))[None, :]
    a = np.asarray(P).astype(np.float32) * g[..., None]
    return Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8))


def font(yol, boy, w):
    f = ImageFont.truetype(yol, boy); f.set_variation_by_axes([w]); return f


def panel_maske(boyut):
    m = Image.new('L', boyut, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, boyut[0] - 1, boyut[1] - 1), radius=30, fill=255)
    return m


def kur(kart, sahne_yol, poster_yol, eski_yol, GAR, MON):
    K = KARTLAR[kart]
    out = Image.new('RGB', (3000, 2250), BG); d = ImageDraw.Draw(out)
    E = Image.open(eski_yol).convert('RGB')
    out.paste(E.crop((0, 70, 1500, 140)), (0, 70)); out.paste(E.crop((0, 2130, 3000, 2250)), (0, 2130))
    FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
    b = FT.getbbox('Two signs. One shared symbol.', anchor='ls'); d.text((143 - b[0], 201 - b[1]), K['baslik'], font=FT, fill=NAVY_T, anchor='ls')
    b = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')
    d.text((147 - b[0], 336 - b[1]), K['alt'], font=FS, fill=SANS_T, anchor='ls')

    G = Image.open(sahne_yol).convert('RGB')
    kutu, dolu, sapma = aciklik(G)
    sahne, s = sahne_isle(G)
    X0, Y0, X1, Y1 = panel_aciklik(kutu, s)
    poster, kirp, kirp_eks = poster_hazirla(kart, poster_yol, X1 - X0, Y1 - Y0)
    if kirp_eks > 0.03:
        raise SystemExit(f'DUR: {kart} poster kirpimi %{kirp_eks * 100:.2f} > %3 (acıklik oran {(X1 - X0) / (Y1 - Y0):.4f})')
    sahne.paste(ic_golge(poster), (X0, Y0))
    SY = K['SY']
    out.paste(sahne, (SX, SY), panel_maske(sahne.size))

    yollar = {'GAR': (GAR, 450), 'MON': (MON, 400)}
    def orta(y, t, f, renk):
        b = f.getbbox(t, anchor='ls'); d.text((1500 - (b[0] + b[2]) / 2, y - b[1]), t, font=f, fill=renk, anchor='ls')
    def fit(yol, w, t, hedef):
        return font(yol, min(range(24, 90), key=lambda z: abs((lambda bb: bb[2] - bb[0])(font(yol, z, w).getbbox(t, anchor='ls')) - hedef)), w)
    for t, fnt, hedef, dy, *boy in K['satirlar']:
        yol, w = yollar[fnt]
        f = font(yol, boy[0], w) if boy else fit(yol, w, t, hedef)
        orta(SY + sahne.height + dy, t, f, NAVY_T if fnt == 'GAR' else SANS_T)
    bilgi = dict(kutu=kutu, dolu=dolu, sapma=sapma, s=s, acik=(X0, Y0, X1, Y1), SY=SY, panel=sahne.size,
                 poster=poster.size, kirp=kirp, kirp_eks=kirp_eks)
    return out, bilgi


if __name__ == '__main__':
    kart, SAHNE, POSTER, ESKI, GAR, MON, CIK = sys.argv[1:8]
    out, bilgi = kur(kart, SAHNE, POSTER, ESKI, GAR, MON)
    out.save(CIK, quality=95, subsampling=0)
    if len(sys.argv) > 8:
        out.save(sys.argv[8])                              # kayipsiz kontrol kopyasi (QC 'birebir' olcumu)
    print(kart, bilgi)
