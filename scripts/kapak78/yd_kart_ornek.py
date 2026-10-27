#!/usr/bin/env python3
"""YD (1st Anniversary) yeni galerinin 2-5. kartlari, ESKI 1st Anniversary galerisinin tarzinda (Serdar 27 Eki; Merkez gorevi).
ETSY API YOK, Canva yok. Ornek: CANCER_LIBRA; toplu uretim Serdar ornegi onaylayinca.
Tarz kaynagi (birebir): origin/bizim-yilimiz-v3 galeri/gallery_layout.json (yd_kart/gallery_layout_eski.json kopyasi) ve
galeri/fonts (yd_kart/fonts: Cormorant Garamond, Manrope; OFL). Eski canli kartlar (CANCER_LIBRA r2 / r3 / r6 / r8) bu duzenden
uretilmis: r2 = slayt 2 (Shared Symbol), r3 = slayt 8 (Formats), r6 = slayt 4 (Personalization), r8 = slayt 10 (Free Preview).
SADE STIL (Serdar / Merkez 27 Eki "sade, easy to read"; 4 kartta aynen): zemin tek duz #F5F0E7, yazi / ok / cizgi tek renk #2B2220,
baslik Cormorant 500 170 px Title Case, etiket Manrope 600 68 px Title Case, metin Manrope 400 64 px, alt not 58 px (en kucuk 58),
panel / golge / imza yok. Cizim dogrudan 3000x2250; eski layout yalniz yuzde konumlar (sembol kutulari, poster kutulari).
  Y02 sembol (cifte ozel)      : "Your Two Signs, One Shared Symbol"; burc ve ortak semboller eski r2'den (alfa, tek renge boyanir),
                                 ok, burc adlari + "<A> & <B>".
  Y03 kisisellestirme (cifte)  : solda Botanical poster (yedek r12 kirpimi, golgesiz), sagda 4 satir (etiket + metin) + alt not.
  Y04 format (ORTAK)           : 3 sutun panelsiz, ince dikey ayirici + alt not.
  Y05 surec (cifte ozel)       : eski r8 duzeni; solda Timeless poster (yedek r10), sagda 4 adim (01-04) + alt not.
  KONTAK_KUCUK.jpg (--ortak)   : 4 kart 2x2, 1600x1200, JPEG 80, < 200 KB (kartlar yazilmadan once denetlenir).
RENK KAPISI (cizim + teslim JPEG): poster disinda zemin / murekkep dogrusu, ara ton yalniz murekkep kenarinda, dolu koyu blok yok.
PUNTO KAPISI: her yazi >= 58 px. BASLIK / ETIKET satirlari gorev metniyle birebir ve Title Case.
Yazi kapisi: gorsele giren her metinde '.', '+', '=', tire / eksi bicimleri ve CLAUDE.md urun metni yasaklari yok; METIN KAPISI: her
kartta cizilen satirlar sirasiyla gorev metni (beklenen()) ile ayni (buyuk/kucuk harf haric). Biri tutmazsa DUR (cikti yazilmaz).
Kullanim: yd_kart_ornek.py --cift CANCER_LIBRA --a Cancer --b Libra --eski-r2 r2.jpg --botanical r12.jpg --timeless r10.jpg --out DIR [--ortak]"""
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


def poster_koy(im, k, src):
    """poster (golgesiz) kutuya sigdir, ortala -> gercek kutu (renk kapisi disi)"""
    p, olcu = poster_kirp(src)
    bw, bh = k[2] - k[0], k[3] - k[1]
    s_ = min(bw / p.width, bh / p.height); nw, nh = round(p.width * s_), round(p.height * s_)
    x, y = round((k[0] + k[2] - nw) / 2), round((k[1] + k[3] - nh) / 2)
    im.paste(p.resize((nw, nh), Image.LANCZOS), (x, y))
    return [x, y, x + nw, y + nh], olcu


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


def sembol_al(r2, e, pay=0.06):
    """eski r2 (3000x2250 ya da 3200x2400) icinde ogenin kutusu -> RGBA sembol (murekkep rengi, alfa = kagittan uzaklik)"""
    im = r2.convert("RGB").resize((W, H), Image.LANCZOS) if r2.size != (W, H) else r2.convert("RGB")
    k = kutu(e); bw, bh = k[2] - k[0], k[3] - k[1]
    k = [k[0] - pay * bw, k[1] - pay * bh, k[2] + pay * bw, k[3] + pay * bh]
    a = np.asarray(im.crop([round(v) for v in k])).astype(np.float32)
    kag = np.float32(rgb(bg(2)["color_hex"]))                 # eski r2 kagidi (alfa olcumu)
    lum = a @ np.float32([0.299, 0.587, 0.114]); lk = float(kag @ np.float32([0.299, 0.587, 0.114]))
    murekkep = np.percentile(lum, 3)             # cekirdek tam opak (inceleme 27 Eki: %0,5 ile cekirdek (50,40,38) kaliyordu)
    al = np.clip((lk - lum) / max(lk - murekkep, 1), 0, 1)
    al = np.clip((al - 0.2) / 0.6, 0, 1)        # keskin kenar: eski JPEG'in yumusak hale / gurultusu atilir (renk kapisi ara ton)
    al[(al < 0.6) & ~(_kutu_toplam(al >= 0.6, 3) > 0)] = 0   # cekirdekten kopuk JPEG lekesi
    ys, xs = np.nonzero(al > 0.5)
    if len(xs) < 200:
        raise SystemExit(f"DUR: eski r2'de {e['id']} sembolu bulunamadi")
    renk = np.median(a[al > 0.9], axis=0) if (al > 0.9).any() else np.float32((40, 30, 30))
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8); rgba[..., :3] = rgb(MUREKKEP); rgba[..., 3] = (al * 255).astype(np.uint8)  # tek renk
    return Image.fromarray(rgba), [round(v) for v in k], dict(eski_murekkep=[int(x) for x in renk], piksel=int((al > 0.5).sum()))



def y02(a, b, r2):
    im = tuval()
    olcu = {}
    for eid in ("cancer_symbol", "libra_symbol", "shared_symbol"):     # eski ogeler (ad Cancer/Libra; cift icin a / b)
        rgba, k, o = sembol_al(r2, el(2, eid)); im.paste(rgba, (k[0], k[1]), rgba); olcu[eid] = o
    d = ImageDraw.Draw(im)
    baslik(d, "Your Two Signs, One Shared Symbol")
    e = el(2, "merge_arrow"); (x0, y0), (x1, y1) = [(p[0] * W / 100, p[1] * H / 100) for p in e["points_pct"]]
    cizgi(d, (x0, y0), (x1, y1))
    uc = 24
    d.line([(x1 - uc, y1 - uc * 0.6), (x1, y1), (x1 - uc, y1 + uc * 0.6)], fill=MUREKKEP, width=CIZGI)
    for eid, t in (("cancer_label", a), ("libra_label", b), ("pair_label", f"{a} & {b}")):
        k = kutu(el(2, eid))
        yaz(d, ETIKET, [t], (k[0] + k[2]) / 2, (k[1] + k[3]) / 2 - ETIKET["boy"] / 2, "center", max(k[2] - k[0], 0.4 * W))
    return im, olcu, []


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



def y03(a, b, r12):
    im = tuval()
    pkutu, olcu = poster_koy(im, POSTER, r12)
    d = ImageDraw.Draw(im)
    baslik(d, "Your Names, Your Date")
    adimlar(d, SUTUN_X, W - KENAR - SUTUN_X, [
        (None, [f"Name Under {a}", f"Name Under {b}"], "Up to 11 letters each, English letters, printed in capitals"),
        (None, ["Your Special Date"], "Month in letters, for example 14 June 2025"),
        (None, ["Your Heading"], "Paper Anniversary or Our First Year"),
        (None, ["Optional Short Line"], "Up to 20 characters, Year One if left empty")])
    yaz(d, NOT, ["Please check your spelling before you order"], W / 2, NOT_Y, "center", W - 2 * KENAR)
    return im, olcu, [pkutu]


def y04():
    im = tuval(); d = ImageDraw.Draw(im)
    baslik(d, "Digital File or Print")
    kolon = [("Digital File", "One print ready digital file in the style and size you choose\n\nNothing is shipped"),
             ("Print", "Unframed print on matte art paper"),
             ("14 Sizes", "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2")]
    kg = (W - 2 * KENAR) / 3; gen = kg - 0.06 * W
    sat = [sar_d(METIN, m, gen) for _, m in kolon]
    hh = max(blok_yuk(METIN, len(x)) for x in sat)
    ara = 0.45 * ETIKET["boy"] + ETIKET["boy"]
    ust = (ALAN[0] + ALAN[1]) / 2 - (ara + hh) / 2                # Y03 / Y05 ile ayni icerik alaninda ortali
    alt = ust + ara + hh
    for i, ((bas, _), t) in enumerate(zip(kolon, sat)):
        cx = KENAR + kg * (i + 0.5)
        yaz(d, ETIKET, [bas], cx, ust, "center", gen)
        yaz(d, METIN, t, cx, ust + ara, "center", gen)
        if i:
            cizgi(d, (KENAR + kg * i, ust - 0.02 * H), (KENAR + kg * i, alt + 0.02 * H))   # ince dikey ayirici
    yaz(d, NOT, ["Every style and size as a print or a digital file"], W / 2, NOT_Y, "center", W - 2 * KENAR)
    return im, dict(kolon_px=round(kg)), []


def y05(a, b, r10):
    """eski r8 (slayt 10) duzeni: solda Timeless poster, sagda 4 adim (Merkez 27 Eki karar d); Y03 ile ayni geometri"""
    im = tuval()
    pkutu, olcu = poster_koy(im, POSTER, r10)
    d = ImageDraw.Draw(im)
    baslik(d, "Made for You, Step by Step")
    adimlar(d, SUTUN_X, W - KENAR - SUTUN_X, [
        ("01", ["Free Preview Before You Order"], "Message us your names, your date and your style, and we send you a free preview"),
        ("02", ["Your Final Preview"], "After your order, we send your final preview in Etsy Messages within 24 hours"),
        ("03", ["Your Approval"], "Once you approve, we send your digital file in Etsy Messages, or prepare your print"),
        ("04", ["A Flat Print"], "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper")],
        no_g=round(1.75 * ETIKET["boy"]))
    yaz(d, NOT, ["Colors may look slightly different on screen and on paper"], W / 2, NOT_Y, "center", W - 2 * KENAR)
    return im, olcu, [pkutu]


def _kutu_toplam(m, r):
    """m (bool) icin (2r+1)^2 pencere toplami (integral goruntu)"""
    c = np.pad(np.pad(m.astype(np.int32), r).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    n = 2 * r + 1
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def renk_kapisi(im, poster_kutulari, jpeg=False):
    """RENK KAPISI (inceleme 27 Eki: yalniz dogruya uzaklik gri / panel geciriyordu). Poster disinda:
    (1) her piksel zemin -> murekkep dogrusu uzerinde (tolerans 6; JPEG 20),
    (2) zeminden belirgin ayrisan ara ton (t > 0.03; JPEG 0.06) yalniz murekkep cekirdeginin (t > 0.6) 3 px (JPEG 8 px) yakininda
        (kenar yumusatma; gri yazi / panel / koyu alan FAIL),
    (3) 61x61 tamamen murekkep (t > 0.6) blok yok (dolu koyu alan / panel FAIL; ortak sembol kesisimleri 41 px'i asabiliyor). -> {neden: piksel}"""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    z, m = np.float32(rgb(ZEMIN)), np.float32(rgb(MUREKKEP))
    v = m - z; t = np.clip(((a - z) @ v) / float(v @ v), 0, 1)
    dis = np.ones(t.shape, bool)
    for k in poster_kutulari:
        dis[k[1]:k[3], k[0]:k[2]] = False
    tol, esik, r = (20, 0.06, 8) if jpeg else (6, 0.03, 3)
    cekirdek = t > 0.6                                      # gri yazi (#A09992 t~0.5) cekirdek sayilmaz
    yakin = _kutu_toplam(cekirdek, r) > 0
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
    """gorev metninde olmayan, eski karttan gelen yazilar (Merkez 27 Eki karar c: kalir)"""
    return {"Y02": [f"{a} & {b}"], "Y03_ayirici": "gorevdeki '|' cizilmedi; iki ad alani iki satir (karar a)"}


def beklenen(a, b):
    """gorev metni (Merkez 27 Eki, aynen), cizim sirasiyla; buyuk/kucuk harf kapida yok sayilir (ayrica Title Case denetlenir)"""
    return {
        "Y02": ["Your Two Signs, One Shared Symbol", a, b, f"{a} & {b}"],
        "Y03": ["Your Names, Your Date",
                f"Name Under {a}", f"Name Under {b}", "Up to 11 letters each, English letters, printed in capitals",
                "Your Special Date", "Month in letters, for example 14 June 2025",
                "Your Heading", "Paper Anniversary or Our First Year",
                "Optional Short Line", "Up to 20 characters, Year One if left empty",
                "Please check your spelling before you order"],
        "Y04": ["Digital File or Print",
                "Digital File", "One print ready digital file in the style and size you choose", "Nothing is shipped",
                "Print", "Unframed print on matte art paper",
                "14 Sizes", "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2",
                "Every style and size as a print or a digital file"],
        "Y05": ["Made for You, Step by Step",
                "01", "Free Preview Before You Order", "Message us your names, your date and your style, and we send you a free preview",
                "02", "Your Final Preview", "After your order, we send your final preview in Etsy Messages within 24 hours",
                "03", "Your Approval", "Once you approve, we send your digital file in Etsy Messages, or prepare your print",
                "04", "A Flat Print", "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper",
                "Colors may look slightly different on screen and on paper"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cift", required=True); ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--eski-r2", required=True, help="o ciftin eski galerisinin r2 karti (yedek; burc + ortak sembol)")
    ap.add_argument("--botanical", required=True, help="o ciftin Botanical stil gorseli (yedek r12, 2400x3000)")
    ap.add_argument("--timeless", required=True, help="o ciftin Timeless stil gorseli (yedek r10, 2400x3000)")
    ap.add_argument("--out", required=True); ap.add_argument("--ortak", action="store_true", help="ORTAK_Y04 de uret (+ KONTAK_KUCUK.jpg)")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    YAZILAR.clear(); SATIRLAR.clear()
    islem = [(f"{a.cift}_Y02.jpg", lambda: y02(a.a, a.b, Image.open(a.eski_r2))),
             (f"{a.cift}_Y03.jpg", lambda: y03(a.a, a.b, Image.open(a.botanical)))]
    if a.ortak:
        islem += [("ORTAK_Y04.jpg", y04)]
    islem += [(f"{a.cift}_Y05.jpg", lambda: y05(a.a, a.b, Image.open(a.timeless)))]
    sonuc, rapor, metin, satir, jb = {}, {}, {}, {}, {}
    for ad, fn in islem:
        n0 = len(YAZILAR)
        im, o, pk = fn(); sonuc[ad] = im; metin[ad] = YAZILAR[n0:]; satir[ad] = SATIRLAR[n0:]
        sap = renk_kapisi(im, pk)                    # RENK KAPISI (cizim): poster disinda yalniz zemin + murekkep (+ kenar yumusatma)
        if sap:
            raise SystemExit(f"DUR: {ad} renk kapisi (cizim) {sap}")
        jb[ad] = jpeg_bayt(im)
        import io
        sapj = renk_kapisi(Image.open(io.BytesIO(jb[ad])), pk, jpeg=True)    # teslim edilen JPEG (inceleme 27 Eki)
        if sapj:
            raise SystemExit(f"DUR: {ad} renk kapisi (JPEG) {sapj}")
        rapor[ad] = dict(o or {}, renk_kapisi="PASS (cizim + JPEG)", poster_kutu=pk)
    kotu = sorted({t for t in YAZILAR if YASAK.search(t) or YASAK_SOZ.search(t)})
    if kotu:
        raise SystemExit(f"DUR: yasak karakter / sozcuk iceren yazi: {kotu}")
    bek = beklenen(a.a, a.b)
    for ad, ss in satir.items():                    # BASLIK / ETIKET: her satir gorev metninin bir ogesiyle BIREBIR (buyuk/kucuk harf dahil)
        for tur, t in ss:                           # ve Title Case ("Name Under A" / "Name Under B" ayri satir)
            if tur in ("baslik", "etiket") and (t not in bek[ad[-7:-4]] or not title_case(t)):
                raise SystemExit(f"DUR: {ad} {tur} satiri {t!r} gorev metninde birebir yok / Title Case degil")
    for ad, sat in metin.items():                   # METIN KAPISI: cizilen satirlar, sirasiyla, gorev metni + izinli ek (buyuk/kucuk harf haric) ile ayni
        g, e = " ".join(sat).split(), " ".join(bek[ad[-7:-4]]).split()
        if [x.casefold() for x in g] != [x.casefold() for x in e]:
            raise SystemExit(f"DUR: {ad} metni gorev metninden farkli\n cizilen: {' '.join(g)}\n beklenen: {' '.join(e)}")
    kb = kontak([sonuc[f"{a.cift}_Y02.jpg"], sonuc[f"{a.cift}_Y03.jpg"], sonuc["ORTAK_Y04.jpg"], sonuc[f"{a.cift}_Y05.jpg"]]) if a.ortak else None
    for ad, b in jb.items():
        (out / ad).write_bytes(b)
    if kb:
        (out / "KONTAK_KUCUK.jpg").write_bytes(kb)
        rapor["KONTAK_KUCUK.jpg"] = dict(boyut=[1600, 1200], kb=round(len(kb) / 1024, 1))
    girdi = {k: dict(dosya=Path(v).name, sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest()) for k, v in
             (("eski_r2", a.eski_r2), ("botanical", a.botanical), ("timeless", a.timeless))}
    (out / "KART_OZET.json").write_text(json.dumps(dict(cift=a.cift, dosyalar=list(sonuc), girdi=girdi, surum=SURUM, olcu=rapor,
                                                        yazilar=metin, gorevde_olmayan=EK_METIN(a.a, a.b), tuval=[W, H],
                                                        cikti=list(CIKTI)), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"KART: {', '.join(sonuc)} -> {out} | yazi {len(YAZILAR)} satir, yasak 0, metin kapisi PASS {len(metin)}/{len(metin)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
