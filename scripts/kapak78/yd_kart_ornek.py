#!/usr/bin/env python3
"""YD (1st Anniversary) bilgi kartlari, KART SABLONU (Merkez 28 Eki, Serdar onayi; 27 Eki SADE stili). ETSY API YOK, Canva yok.
Ornek: CANCER_LIBRA; toplu uretim Serdar ornegi onaylayinca (yd_kart_toplu.py bu yeni CLI'ye henuz uyarlanmadi).
Fontlar yd_kart/fonts (Cormorant Garamond, Manrope; OFL); stil sabitleri ve yardimcilar bu dosyada, yerlesim kart_sablon.py'de
(wall art ve kupa ile ayni kart turu ayni fonksiyon). SADE: zemin #F5F0E7, tek murekkep #2B2220, baslik Cormorant 500 170 px, etiket
Manrope 600 68, metin 64, alt not 58 (en kucuk 58), panel / golge / imza yok, 3000x2250.
  <CIFT>_Y02       sembol (galeri 2): iki burc + ad, Bezier baglac, ortak sembol (kupa_uretim/sembol/<CIFT>); eski "<A> & <B>" ve ok yok
  <CIFT>_Y03       kisisellestirme (3): Botanical poster (yedek stil gorseli, 4:5 kirpim) + 4 blok (27 Eki metinleri aynen)
  ORTAK_Y04        format (4): tablo Digital File / Print / 14 Sizes (--ortak)
  <CIFT>_Y05       surec (5): Timeless poster + 4 adim (27 Eki metinleri aynen)
  YD_<CIFT>_GENEL  genel bakis (6): 5 stil 3 + 2 (Starlit, Timeless, First Page / Layers, Botanical); <CIFT>_Y<NN> bicimine girmez
Stil gorselleri adim 5 yedeginden (GALERI.json Style 513 baglari). Kapilar: renk (cizim + JPEG; baglac uclarinin 4 px yakininda ara ton
serbest), punto >= 58, BASLIK / ETIKET satirlari gorev metniyle birebir ve Title Case, yasak karakter ('.', '+', '=', tire bicimleri) ve
CLAUDE.md urun metni yasaklari, METIN KAPISI (cizilen satirlar sirasiyla beklenen()), yerlesim kapilari (kart_sablon.py). Biri tutmazsa DUR.
Kullanim: yd_kart_ornek.py --cift CANCER_LIBRA --a Cancer --b Libra --yedek <yedek ilan klasoru> --sembol <dir> --out DIR [--ortak]"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont, features

HERE = Path(__file__).resolve().parent / "yd_kart"
W, H = 3000, 2250                     # cizim dogrudan cikti boyutunda (punto kurali cikti pikseli; eski layout yuzdeleri olcekten bagimsiz)
CIKTI = (3000, 2250)                  # Serdar 27 Eki: tum gorseller 4:3, 3000x2250
YASAK = re.compile(r"[.+=\u2010-\u2015\u2212]")      # nokta, arti, esittir, tum tire / eksi bicimleri (ASCII '-' haric)
YASAK_SOZ = re.compile(r"hahnem|photo rag|308|giclee|giclée|prodigi|cotton|museum|iso 9706|\boba\b|bright white|12.colou?r|years?\b.*\d|astrolove(?!art)",
                       re.I)                       # CLAUDE.md urun metni yasaklari + marka adi
SURUM = dict(pillow=PIL.__version__, raqm=features.check("raqm"), numpy=np.__version__)
LAY = json.loads((HERE / "gallery_layout_eski.json").read_text(encoding="utf-8"))
SL = {s["number"]: s for s in LAY["slides"]}


def el(slayt, eid):
    return next(e for e in SL[slayt]["elements"] if e["id"] == eid)


def bg(slayt, ad=None):
    b = SL[slayt]["background_layers"]
    return b[0] if ad is None else next(x for x in b if x.get("name") == ad)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def kutu(e):
    cx, cy, w, h = (e[k] for k in ("center_x_pct", "center_y_pct", "width_pct", "height_pct"))
    return [(cx - w / 2) * W / 100, (cy - h / 2) * H / 100, (cx + w / 2) * W / 100, (cy + h / 2) * H / 100]


_F = {}


def font(dosya, boy, agirlik):
    k = (dosya, round(boy), agirlik)
    if k not in _F:
        f = ImageFont.truetype(str(HERE / dosya), round(boy))
        f.set_variation_by_axes([agirlik])
        _F[k] = f
    return _F[k]


def ozellik(s, t):
    """Cormorant rakamlari eski stil (oldstyle: '14' 'I4' gibi okunur): rakamli Cormorant yazida lining figures (lnum; raqm)"""
    if "Cormorant" in s["dosya"] and re.search(r"\d", t):
        if not features.check("raqm"):
            raise SystemExit("DUR: Pillow raqm yok (Cormorant rakamlari icin lnum gerekli)")
        return ["lnum"]
    return None


def genislik(s, t):
    f = font(s["dosya"], s["boy"], s["agirlik"]); o = ozellik(s, t)
    return (f.getlength(t, features=o) if o else f.getlength(t)) if not s["aralik"] else \
        sum(f.getlength(c) for c in t) + s["aralik"] * max(0, len(t) - 1)


def sar(s, metin, gen):
    """kelime kelime satira bol (genislik gen px)"""
    out = []
    for par in metin.split("\n"):
        sat = ""
        for k in par.split(" "):
            aday = (sat + " " + k).strip()
            if sat and genislik(s, aday) > gen:
                out.append(sat); sat = k
            else:
                sat = aday
        out.append(sat)
    return out


YAZILAR = []
SATIRLAR = []                                    # (tur, satir): baslik / etiket satirlari tam metin + Title Case kapisi icin
KUTULAR = []                                     # (blok, tur, [x0, y0, x1, y1]) satir kutusu (yerlesim kapilari, kart_sablon.py)
BLOK = ["?"]                                     # o an cizilen blogun adi (kart_sablon.Kayit.blok)


def yaz(d, s, satirlar, x, y, hiza="left", gen=None):
    """satirlar ust kenari y; hiza left (x sol), center (x orta). -> blok yuksekligi"""
    f = font(s["dosya"], s["boy"], s["agirlik"])
    adim = s["boy"] * s["satir"]
    if s["boy"] < EN_KUCUK:
        raise SystemExit(f"DUR: punto {s['boy']} < {EN_KUCUK} px ({satirlar[:1]})")
    for j, t in enumerate(satirlar):
        YAZILAR.append(t); SATIRLAR.append((s.get("tur"), t))
        tw = genislik(s, t)
        if gen and tw > gen + 1:
            raise SystemExit(f"DUR: yazi sigmiyor ({t!r}, {tw:.0f} > {gen:.0f} px)")
        x0 = x if hiza == "left" else x - tw / 2
        KUTULAR.append((BLOK[0], s.get("tur"), [round(x0), round(y + j * adim), round(x0 + tw), round(y + j * adim + s["boy"])]))
        o = ozellik(s, t)
        ink = f.getbbox("Hg")                      # satir bazli sabit taban (iceriğe gore kayma yok)
        yy = y + j * adim + (s["boy"] - (ink[3] - ink[1])) / 2 - ink[1]
        if s["aralik"]:
            for c in t:
                d.text((x0, yy), c, font=f, fill=s["renk"]); x0 += f.getlength(c) + s["aralik"]
        elif o:
            d.text((x0, yy), t, font=f, fill=s["renk"], features=o)
        else:
            d.text((x0, yy), t, font=f, fill=s["renk"])
    return s["boy"] + (len(satirlar) - 1) * adim


def blok_yuk(s, n):
    return s["boy"] + (n - 1) * s["boy"] * s["satir"]


# ---------------------------------------------------------------- SADE stil (Serdar / Merkez 27 Eki: "sade, easy to read")
# 4 kartta aynen: zemin tek duz #F5F0E7 (panel / kutu / degrade yok); TUM yazi, ok ve cizgi tek renk #2B2220 (ince); baslik Cormorant 500
# 170 px Title Case; etiket Manrope 600 68 px Title Case; metin Manrope 400 >= 64 px; alt not >= 58 px; hicbir yazi < 58 px (3000x2250
# cikti pikseli). Imza yok. Posterler (Y03 Botanical, Y05 Timeless) golgesiz duz kirpim. Yerlesim yuzdeleri eski layout'tan.
ZEMIN, MUREKKEP = "#F5F0E7", "#2B2220"
CIZGI = 4                                                       # ince cizgi / ok (px; 570 px onizlemede ~0,8 px)
BASLIK = dict(dosya="fonts/CormorantGaramond.ttf", boy=170, agirlik=500, renk=MUREKKEP, aralik=0, satir=1.15, tur="baslik")
ETIKET = dict(dosya="fonts/Manrope.ttf", boy=68, agirlik=600, renk=MUREKKEP, aralik=0, satir=1.2, tur="etiket")
METIN = dict(dosya="fonts/Manrope.ttf", boy=64, agirlik=400, renk=MUREKKEP, aralik=0, satir=1.32, tur="metin")
NOT = dict(dosya="fonts/Manrope.ttf", boy=58, agirlik=400, renk=MUREKKEP, aralik=0, satir=1.2, tur="not")
EN_KUCUK = 58
KENAR = 0.07 * W                                                # yan bosluk
BASLIK_Y = 0.085 * H                                            # baslik ust kenari
NOT_Y = 0.905 * H                                               # alt not (Y03, Y04, Y05 ayni konum, ortali)
ALAN = (BASLIK_Y + BASLIK["boy"] + 0.06 * H, NOT_Y - 0.05 * H)  # icerik alani (baslik alti .. alt not ustu)
POSTER = (0.25 * W - 450, (ALAN[0] + ALAN[1]) / 2 - 562.5, 0.25 * W + 450, (ALAN[0] + ALAN[1]) / 2 + 562.5)   # Y03 / Y05 ayni, 900x1125
SUTUN_X = POSTER[2] + 0.07 * W                                  # poster sagindaki sutun


def tuval():
    return Image.new("RGB", (W, H), ZEMIN)


def baslik(d, metin):
    yaz(d, BASLIK, [metin], W / 2, BASLIK_Y, "center", W - 2 * KENAR)


def cizgi(d, p0, p1):
    d.line([p0, p1], fill=MUREKKEP, width=CIZGI)


def sar_d(s, metin, gen):
    """dengeli satir bolme: ayni satir sayisinda en kisa satiri en uzun yapan genislik (tek kalan kelime yok)"""
    taban = sar(s, metin, gen); en, puan = taban, -1
    for w in range(int(gen), int(gen * 0.55), -12):
        L = sar(s, metin, w)
        if len(L) > len(taban):
            break
        dolu = [genislik(s, x) for x in L if x]
        if dolu and min(dolu) > puan:
            en, puan = L, min(dolu)
    return en


def adimlar(d, x0, gen, bloklar, no_g=0):
    """[(numara|None, etiket satirlari, metin)] -> icerik alaninin (ALAN) ortasina, poster ortasiyla hizali bloklar"""
    hazir = [(n, e, sar_d(METIN, t, gen - no_g)) for n, e, t in bloklar]
    ara_et = 0.28 * ETIKET["boy"]
    yuk = [blok_yuk(ETIKET, len(e)) + ara_et + blok_yuk(METIN, len(t)) for _, e, t in hazir]
    bos = min(140, (ALAN[1] - ALAN[0] - sum(yuk)) / max(1, len(yuk) - 1))
    if bos < 60:
        raise SystemExit(f"DUR: adimlar sigmiyor (aralik {bos:.0f} px)")
    y = (ALAN[0] + ALAN[1]) / 2 - (sum(yuk) + bos * (len(yuk) - 1)) / 2
    for (n, e, t), h in zip(hazir, yuk):
        if n:
            yaz(d, ETIKET, [n], x0, y, gen=no_g)
        yy = y + yaz(d, ETIKET, e, x0 + no_g, y, gen=gen - no_g) + ara_et
        yaz(d, METIN, t, x0 + no_g, yy, gen=gen - no_g)
        y += h + bos
    return y - bos


def poster_kirp(r12):
    """stil gorseli (2400x3000, poster acik gri zeminde) -> poster dikdortgeni (zeminden farkli en genis bilesen)"""
    a = np.asarray(r12.convert("RGB")).astype(np.float32)
    kenar = np.concatenate([a[:20].reshape(-1, 3), a[-20:].reshape(-1, 3), a[:, :20].reshape(-1, 3), a[:, -20:].reshape(-1, 3)])
    z = np.median(kenar, axis=0)
    fark = np.abs(a - z).max(axis=2) > 18
    sat = fark.mean(axis=1) > 0.5; sut = fark.mean(axis=0) > 0.5
    ys, xs = np.nonzero(sat)[0], np.nonzero(sut)[0]
    if not len(ys) or not len(xs):
        raise SystemExit("DUR: Botanical stil gorselinde poster bulunamadi")
    k = [int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1]
    # kaba kutu poster golgesini (yumusak gri, zeminden 18+ fark) de icine aliyor (inceleme 27 Eki: sag 30, alt 47 px).
    # Keskin poster kenari: kaba kenarin +-80 px icinde ortalama parlaklik profilinin en buyuk sicramasi.
    lum = a.mean(axis=2)
    ort_y = lum[k[1] + (k[3] - k[1]) // 4:k[3] - (k[3] - k[1]) // 4].mean(axis=0)
    ort_x = lum[:, k[0] + (k[2] - k[0]) // 4:k[2] - (k[2] - k[0]) // 4].mean(axis=1)

    def sicrama(pr, c):                             # pr[i] - pr[i-1] en buyuk |fark| -> kenar i (sol/ust ilk poster pikseli, sag/alt ilk disari)
        lo, hi = max(1, c - 80), min(len(pr) - 1, c + 80)
        return lo + int(np.argmax(np.abs(pr[lo:hi + 1] - pr[lo - 1:hi])))
    k = (sicrama(ort_y, k[0]), sicrama(ort_x, k[1]), sicrama(ort_y, k[2]), sicrama(ort_x, k[3]))
    oran = (k[2] - k[0]) / (k[3] - k[1])
    if abs(oran - 0.8) > 0.02:
        raise SystemExit(f"DUR: poster orani {oran:.3f} (4:5 = 0.8 beklenir), kutu {k}")
    return r12.convert("RGB").crop(k), dict(kutu=k, oran=round(oran, 4), zemin=[int(x) for x in z])



def _kutu_toplam(m, r):
    """m (bool) icin (2r+1)^2 pencere toplami (integral goruntu)"""
    c = np.pad(np.pad(m.astype(np.int32), r).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    n = 2 * r + 1
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def renk_kapisi(im, poster_kutulari, jpeg=False, muaf=(), muaf_r=4):
    """RENK KAPISI (inceleme 27 Eki: yalniz dogruya uzaklik gri / panel geciriyordu). Poster disinda:
    (1) her piksel zemin -> murekkep dogrusu uzerinde (tolerans 6; JPEG 20),
    (2) zeminden belirgin ayrisan ara ton (t > 0.03; JPEG 0.06) yalniz murekkep cekirdeginin (t > 0.6) 3 px (JPEG 8 px) yakininda
        (kenar yumusatma; gri yazi / panel / koyu alan FAIL),
    (3) 61x61 tamamen murekkep (t > 0.6) blok yok (dolu koyu alan / panel FAIL; ortak sembol kesisimleri 41 px'i asabiliyor).
    muaf: (x, y) noktalari; muaf_r px yaricapta ara ton serbest (Merkez 28 Eki: baglacin uc keskin ucu). -> {neden: piksel}"""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    z, m = np.float32(rgb(ZEMIN)), np.float32(rgb(MUREKKEP))
    v = m - z; t = np.clip(((a - z) @ v) / float(v @ v), 0, 1)
    dis = np.ones(t.shape, bool)
    for k in poster_kutulari:
        dis[k[1]:k[3], k[0]:k[2]] = False
    tol, esik, r = (20, 0.06, 8) if jpeg else (6, 0.03, 3)
    cekirdek = t > 0.6                                      # gri yazi (#A09992 t~0.5) cekirdek sayilmaz
    yakin = _kutu_toplam(cekirdek, r) > 0
    if muaf:
        yy, xx = np.mgrid[0:t.shape[0], 0:t.shape[1]]
        for mx, my in muaf:
            yakin |= (xx - mx) ** 2 + (yy - my) ** 2 <= muaf_r * muaf_r
    out = dict(dogru_disi=int(((np.linalg.norm(a - (z + t[..., None] * v), axis=2) > tol) & dis).sum()),
               ara_ton=int(((t > esik) & ~yakin & dis).sum()),
               dolu_blok=int(((_kutu_toplam(cekirdek, 30) == 61 * 61) & dis).sum()))
    return {k: n for k, n in out.items() if n}


def kontak(kartlar):
    """KONTAK_KUCUK.jpg (Merkez 27 Eki): 4 kart 2x2, 1600x1200, JPEG 80, < 200 KB. Kartlar diske yazilmadan once kurulur ve
    denetlenir (inceleme 27 Eki: kontak DUR verirse yarim cikti Drive'a gitmesin). -> JPEG baytlari"""
    import io
    t = Image.new("RGB", (1600, 1200), "white")
    for i, im in enumerate(kartlar):
        r, c = divmod(i, 2)
        t.paste(im.resize((800, 600), Image.LANCZOS), (c * 800, r * 600))
    b = io.BytesIO(); t.save(b, "JPEG", quality=80)
    if b.tell() >= 200 * 1024:
        raise SystemExit(f"DUR: KONTAK_KUCUK.jpg {b.tell() / 1024:.0f} KB (200 KB alti beklenir)")
    return b.getvalue()


def jpeg_bayt(im):
    import io
    b = io.BytesIO(); (im if im.size == CIKTI else im.resize(CIKTI, Image.LANCZOS)).save(b, "JPEG", quality=95, subsampling=0)
    return b.getvalue()


def title_case(t):
    """her sozcuk buyuk harfle (rakam ve kisa baglaclar haric)"""
    kucuk = {"a", "an", "and", "or", "for", "by", "of", "the", "to", "in", "on", "&"}
    w = t.split()
    return bool(w) and all(x[0].isupper() or x[0].isdigit() or (i and x in kucuk) for i, x in enumerate(w))


def EK_METIN(a, b):
    """gorev metninde olmayan yazilar: yok (Merkez 28 Eki: Y02'deki "<A> & <B>" cift etiketi ve yatay ok kaldirildi)"""
    return {}


def beklenen(a, b):
    """gorev metni (Merkez 28 Eki kart sablonu; Y03 / Y05 metinleri 27 Eki ile aynen), cizim sirasiyla; buyuk/kucuk harf kapida yok
    sayilir (ayrica Title Case denetlenir)"""
    return {
        "Y02": ["Two Signs, One Shared Symbol", f"{a} and {b} joined in an original AstroLoveArt design", a, b,
                "Personalized with your two names and your date"],
        "Y03": ["Your Names, Your Date",
                f"Name Under {a}", f"Name Under {b}", "Up to 11 letters each, English letters, printed in capitals",
                "Your Special Date", "Month in letters, for example 14 June 2025",
                "Your Heading", "Paper Anniversary or Our First Year",
                "Optional Short Line", "Up to 20 characters, Year One if left empty",
                "Please check your spelling before you order"],
        "Y04": ["Digital File or Print",
                "Digital File", "One print ready digital file in the style and size you choose", "Nothing is shipped",
                "Print", "Unframed print on matte art paper", "Free shipping worldwide",
                "14 Sizes", "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2",
                "Every style and size as a print or a digital file"],
        "Y05": ["Made for You, Step by Step",
                "01", "Free Preview Before You Order", "Message us your names, your date and your style, and we send you a free preview",
                "02", "Your Final Preview", "After your order, we send your final preview in Etsy Messages within 24 hours",
                "03", "Your Approval", "Once you approve, we send your digital file in Etsy Messages, or prepare your print",
                "04", "A Flat Print", "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper",
                "Colors may look slightly different on screen and on paper"],
        "GENEL": ["Choose Your Style"] + list(STILLER) + ["Every style as a print or a digital file"]}


STILLER = ("Starlit", "Timeless", "First Page", "Layers", "Botanical")   # yeni galeri Y06-Y10 sirasi (yd_liste_uret.STIL_SIRA)
BOYLAR = "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2"


def stil_gorselleri(yedek):
    """adim 5 yedegi (GALERI.json baglar: Style (513) -> image_id; r<rank>_<id>.jpg) -> {stil: dosya yolu}"""
    g = json.loads((Path(yedek) / "GALERI.json").read_text(encoding="utf-8"))
    rk = {x["listing_image_id"]: x["rank"] for x in g["gorseller"]}
    bag = {b["value"]: b["image_id"] for b in g["baglar"] if b.get("property_id", 513) == 513}
    eksik = [s for s in STILLER if s not in bag]
    if eksik:
        raise SystemExit(f"DUR: yedekte stil bagi yok: {eksik}")
    return {s: Path(yedek) / f"r{rk[bag[s]]}_{bag[s]}.jpg" for s in STILLER}


def yd_kartlari(a, b, sem, stil):
    """Merkez 28 Eki sablonlari (kart_sablon.py); -> [(dosya anahtari, fn)]; fn -> (im, olcu, poster kutulari, renk muafiyeti)"""
    import kart_sablon as S
    p = {k: poster_kirp(Image.open(v)) for k, v in stil.items()}           # 4:5 poster (oran kapisi 0,8 +- 0,02)

    def y02():
        return S.sembol_kart(a, b, sem, "Personalized with your two names and your date")

    def y03():
        im, o, k = S.yan_kart("Your Names, Your Date", [p["Botanical"][0]], [
            (None, [f"Name Under {a}", f"Name Under {b}"], "Up to 11 letters each, English letters, printed in capitals"),
            (None, ["Your Special Date"], "Month in letters, for example 14 June 2025"),
            (None, ["Your Heading"], "Paper Anniversary or Our First Year"),
            (None, ["Optional Short Line"], "Up to 20 characters, Year One if left empty")], "Please check your spelling before you order")
        return im, dict(o, poster=p["Botanical"][1]), k, ()

    def y04():
        im, o, k = S.tablo_kart("Digital File or Print", [
            ("Digital File", ["One print ready digital file in the style and size you choose", "Nothing is shipped"]),
            ("Print", ["Unframed print on matte art paper", "Free shipping worldwide"]),
            ("14 Sizes", [BOYLAR])], "Every style and size as a print or a digital file")
        return im, o, k, ()

    def y05():
        im, o, k = S.yan_kart("Made for You, Step by Step", [p["Timeless"][0]], [
            ("01", ["Free Preview Before You Order"], "Message us your names, your date and your style, and we send you a free preview"),
            ("02", ["Your Final Preview"], "After your order, we send your final preview in Etsy Messages within 24 hours"),
            ("03", ["Your Approval"], "Once you approve, we send your digital file in Etsy Messages, or prepare your print"),
            ("04", ["A Flat Print"], "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper")],
            "Colors may look slightly different on screen and on paper", surec=True)
        return im, dict(o, poster=p["Timeless"][1]), k, ()

    def genel():
        im, o, k = S.secim_kart("Choose Your Style", [(s, p[s][0]) for s in STILLER], "Every style as a print or a digital file")
        return im, dict(o, poster={s: p[s][1] for s in STILLER}), k, ()
    return [("Y02", y02), ("Y03", y03), ("Y04", y04), ("Y05", y05), ("GENEL", genel)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cift", required=True); ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--yedek", required=True, help="adim 5 yedek klasoru (GALERI.json + r<rank>_<id>.jpg): 5 stil gorseli")
    ap.add_argument("--sembol", required=True, help="kupa_uretim/sembol/<CIFT> (sol.png, sag.png, ana.png)")
    ap.add_argument("--out", required=True); ap.add_argument("--ortak", action="store_true", help="ORTAK_Y04 de uret")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    YAZILAR.clear(); SATIRLAR.clear(); KUTULAR.clear()
    stil = stil_gorselleri(a.yedek)
    adlar = {"Y02": f"{a.cift}_Y02.jpg", "Y03": f"{a.cift}_Y03.jpg", "Y04": "ORTAK_Y04.jpg", "Y05": f"{a.cift}_Y05.jpg",
             "GENEL": f"YD_{a.cift}_GENEL.jpg"}   # GENEL <CIFT>_Y<NN> bicimine girmez (Y06 Starlit; galeri_tasi / test_yd_kapak_qc)
    islem = [(k, adlar[k], fn) for k, fn in yd_kartlari(a.a, a.b, Path(a.sembol), stil) if a.ortak or k != "Y04"]
    sonuc, rapor, metin, satir, jb = {}, {}, {}, {}, {}
    import io
    for anah, ad, fn in islem:
        n0, n1 = len(YAZILAR), len(SATIRLAR)
        im, o, pk, muaf = fn(); sonuc[ad] = im; metin[ad] = (anah, YAZILAR[n0:]); satir[ad] = (anah, SATIRLAR[n1:])
        sap = renk_kapisi(im, pk, muaf=muaf)         # RENK KAPISI (cizim): poster disinda yalniz zemin + murekkep (+ kenar yumusatma)
        if sap:
            raise SystemExit(f"DUR: {ad} renk kapisi (cizim) {sap}")
        jb[ad] = jpeg_bayt(im)
        sapj = renk_kapisi(Image.open(io.BytesIO(jb[ad])), pk, jpeg=True, muaf=muaf)    # teslim edilen JPEG
        if sapj:
            raise SystemExit(f"DUR: {ad} renk kapisi (JPEG) {sapj}")
        rapor[ad] = dict(o or {}, renk_kapisi="PASS (cizim + JPEG)", poster_kutu=pk, kb=round(len(jb[ad]) / 1024))
    kotu = sorted({t for t in YAZILAR if YASAK.search(t) or YASAK_SOZ.search(t)})
    if kotu:
        raise SystemExit(f"DUR: yasak karakter / sozcuk iceren yazi: {kotu}")
    bek = beklenen(a.a, a.b)
    for ad, (anah, ss) in satir.items():            # BASLIK / ETIKET: her satir gorev metninin bir ogesiyle BIREBIR ve Title Case
        for tur, t in ss:
            if tur in ("baslik", "etiket") and (t not in bek[anah] or not title_case(t)):
                raise SystemExit(f"DUR: {ad} {tur} satiri {t!r} gorev metninde birebir yok / Title Case degil")
    for ad, (anah, sat) in metin.items():           # METIN KAPISI: cizilen satirlar, sirasiyla, gorev metni ile ayni (buyuk/kucuk harf haric)
        g, e = " ".join(sat).split(), " ".join(bek[anah]).split()
        if [x.casefold() for x in g] != [x.casefold() for x in e]:
            raise SystemExit(f"DUR: {ad} metni gorev metninden farkli\n cizilen: {' '.join(g)}\n beklenen: {' '.join(e)}")
    for ad, b_ in jb.items():
        (out / ad).write_bytes(b_)
    girdi = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [*stil.values(), *(Path(a.sembol) / f"{x}.png" for x in ("sol", "sag", "ana"))]}
    (out / "KART_OZET_YD.json").write_text(json.dumps(dict(cift=a.cift, dosyalar=list(sonuc), girdi_sha256=girdi,
                                                           stil_kaynak={k: v.name for k, v in stil.items()}, surum=SURUM, olcu=rapor,
                                                           yazilar={k: v[1] for k, v in metin.items()}, gorevde_olmayan=EK_METIN(a.a, a.b),
                                                           tuval=[W, H], cikti=list(CIKTI)), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"KART YD: {', '.join(sonuc)} -> {out} | yazi {len(YAZILAR)} satir, yasak 0, metin / yerlesim / renk kapisi PASS {len(metin)}/{len(metin)}")
    return 0


if __name__ == "__main__":
    import yd_kart_ornek as _M                       # kart_sablon ayni modul nesnesini (YAZILAR / KUTULAR) kullansin
    sys.exit(_M.main())
