#!/usr/bin/env python3
"""YD (1st Anniversary) yeni galerinin 2-5. kartlari, ESKI 1st Anniversary galerisinin tarzinda (Serdar 27 Eki; Merkez gorevi).
ETSY API YOK, Canva yok. Ornek: CANCER_LIBRA; toplu uretim Serdar ornegi onaylayinca.
Tarz kaynagi (birebir): origin/bizim-yilimiz-v3 galeri/gallery_layout.json (yd_kart/gallery_layout_eski.json kopyasi) ve
galeri/fonts (yd_kart/fonts: Cormorant Garamond, Manrope; OFL). Eski canli kartlar (CANCER_LIBRA r2 / r3 / r6 / r8) bu duzenden
uretilmis: r2 = slayt 2 (Shared Symbol), r3 = slayt 8 (Formats), r6 = slayt 4 (Personalization), r8 = slayt 10 (Free Preview).
Renk / font / punto / konum yuzde degerleri o JSON'dan okunur; cizim 3200x2400 tuvalde (eski tuval), cikti Lanczos ile 3000x2250.
  Y02 sembol (cifte ozel)      : slayt 2 duzeni; baslik "Your two signs, one shared symbol" (nokta yok), '+' yok, alt satir noktasiz.
                                 Burc ve ortak semboller eski r2 kartindan (yedek r2) kutu kirpimi + alfa (kagit / murekkep orani).
  Y03 kisisellestirme (cifte)  : slayt 4 duzeni; solda Botanical poster (yedek r12 stil gorselinden poster dikdortgeni kirpilir),
                                 sagda panel: 4 satir (etiket + aciklama) + alt not.
  Y04 format (ORTAK)           : slayt 8 duzeni; 3 panel (Digital File, Print, 14 Sizes), yalniz yazi (78 ilanda ayni dosya,
                                 cifte ozel poster yok) + alt not.
  Y05 surec (cifte ozel)       : slayt 10 (eski r8) duzeni; solda Timeless poster (yedek r10 stil gorselinden kirpim), sagda 4 adim
                                 (01-04, etiket + metin) + alt not (Merkez 27 Eki karar d).
  KONTAK_KUCUK.jpg (--ortak)   : 4 kart 2x2, 1600x1200, JPEG 80, < 200 KB (Merkez inceleme onizlemesi).
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
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

HERE = Path(__file__).resolve().parent / "yd_kart"
W, H = 3200, 2400                     # eski tuval (gallery_layout.json canvas)
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


def stil(e, **deg):
    """eski ogeden yazi stili: dosya, boy, agirlik, renk, aralik, satir"""
    f = e["font"]
    s = dict(dosya=f["file"], boy=f["size_px"], agirlik=f["weight"], renk=e["color_hex"], aralik=e.get("letter_spacing_px") or 0,
             satir=e.get("line_height_em", 1.15))
    s.update(deg)
    return s


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


def yaz(d, s, satirlar, x, y, hiza="left", gen=None):
    """satirlar ust kenari y; hiza left (x sol), center (x orta). -> blok yuksekligi"""
    f = font(s["dosya"], s["boy"], s["agirlik"])
    adim = s["boy"] * s["satir"]
    for j, t in enumerate(satirlar):
        YAZILAR.append(t)
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


def golge(im, k, sh):
    """eski gallery_layout poster golgesi (slayt 4 sample_poster.shadow): ana golge + temas golgesi"""
    box = [round(v) for v in k]
    for off, blur, op in (((sh["offset_x_px"], sh["offset_y_px"]), sh["softness_blur_px"], sh["opacity"]),
                          ((0, 0), sh["contact_shadow_blur_px"], sh["contact_shadow_opacity"])):
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rectangle((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]), fill=round(255 * op))
        im = Image.composite(Image.new("RGB", im.size, rgb(sh["color_hex"])), im, m.filter(ImageFilter.GaussianBlur(blur)))
    return im


def tuval(slayt):
    return Image.new("RGB", (W, H), bg(slayt)["color_hex"])


def panel(d, b):
    k = kutu(b); d.rectangle([round(v) for v in k], fill=b["fill_hex"]); return k


def baslik(d, slayt, metin):
    e = el(slayt, "headline"); k = kutu(e); s = stil(e)
    yaz(d, s, [metin], (k[0] + k[2]) / 2, (k[1] + k[3]) / 2 - s["boy"] / 2, "center", k[2] - k[0])


def marka(d, slayt):
    e = el(slayt, "brand"); k = kutu(e); s = stil(e)
    yaz(d, s, [e["content"]], (k[0] + k[2]) / 2, (k[1] + k[3]) / 2 - s["boy"] / 2, "center", k[2] - k[0])


def cizgi(d, x0, x1, y, e):
    d.line([(x0, y), (x1, y)], fill=e["stroke_hex"], width=e["stroke_width_px"])


# ---------------------------------------------------------------- Y02 sembol
def sembol_al(r2, e, pay=0.06):
    """eski r2 (3000x2250 ya da 3200x2400) icinde ogenin kutusu -> RGBA sembol (murekkep rengi, alfa = kagittan uzaklik)"""
    im = r2.convert("RGB").resize((W, H), Image.LANCZOS) if r2.size != (W, H) else r2.convert("RGB")
    k = kutu(e); bw, bh = k[2] - k[0], k[3] - k[1]
    k = [k[0] - pay * bw, k[1] - pay * bh, k[2] + pay * bw, k[3] + pay * bh]
    a = np.asarray(im.crop([round(v) for v in k])).astype(np.float32)
    kag = np.float32(rgb(bg(2)["color_hex"]))
    lum = a @ np.float32([0.299, 0.587, 0.114]); lk = float(kag @ np.float32([0.299, 0.587, 0.114]))
    murekkep = np.percentile(lum, 0.5)
    al = np.clip((lk - lum) / max(lk - murekkep, 1), 0, 1)
    al[al < 0.04] = 0
    ys, xs = np.nonzero(al > 0.5)
    if len(xs) < 200:
        raise SystemExit(f"DUR: eski r2'de {e['id']} sembolu bulunamadi")
    renk = np.median(a[al > 0.9], axis=0) if (al > 0.9).any() else np.float32((40, 30, 30))
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8); rgba[..., :3] = renk.astype(np.uint8); rgba[..., 3] = (al * 255).astype(np.uint8)
    return Image.fromarray(rgba), [round(v) for v in k], dict(murekkep=[int(x) for x in renk], piksel=int((al > 0.5).sum()))


def y02(a, b, r2):
    im = tuval(2); d = ImageDraw.Draw(im)
    olcu = {}
    for eid in ("cancer_symbol", "libra_symbol", "shared_symbol"):     # eski ogeler (ad Cancer/Libra; cift icin a / b)
        rgba, k, o = sembol_al(r2, el(2, eid)); im.paste(rgba, (k[0], k[1]), rgba); olcu[eid] = o
    d = ImageDraw.Draw(im)
    baslik(d, 2, "Your two signs, one shared symbol")
    e = el(2, "merge_arrow"); (x0, y0), (x1, y1) = [(p[0] * W / 100, p[1] * H / 100) for p in e["points_pct"]]
    d.line([(x0, y0), (x1, y1)], fill=e["stroke_hex"], width=e["stroke_width_px"])
    uc = 26
    d.line([(x1 - uc, y1 - uc * 0.55), (x1, y1), (x1 - uc, y1 + uc * 0.55)], fill=e["stroke_hex"], width=e["stroke_width_px"])
    for eid, t in (("cancer_label", a), ("libra_label", b), ("pair_label", f"{a} & {b}"),
                   ("meaning", "An original symbol for your zodiac pairing")):
        e = el(2, eid); k = kutu(e); s = stil(e)
        yaz(d, s, [t], (k[0] + k[2]) / 2, (k[1] + k[3]) / 2 - s["boy"] / 2, "center", k[2] - k[0])
    marka(d, 2)
    return im, olcu


# ---------------------------------------------------------------- Y03 kisisellestirme
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
    im = tuval(4)
    sp = el(4, "sample_poster"); k = kutu(sp)
    im = golge(im, k, sp["shadow"])
    d = ImageDraw.Draw(im)
    pk = panel(d, bg(4, "details_panel"))
    p, olcu = poster_kirp(r12)
    bw, bh = k[2] - k[0], k[3] - k[1]
    s_ = min(bw / p.width, bh / p.height); nw, nh = round(p.width * s_), round(p.height * s_)
    im.paste(p.resize((nw, nh), Image.LANCZOS), (round((k[0] + k[2] - nw) / 2), round((k[1] + k[3] - nh) / 2)))
    d = ImageDraw.Draw(im)
    baslik(d, 4, "Your Names, Your Date")
    et = stil(el(4, "names_label")); ac = stil(el(4, "names_example"), satir=1.28)
    ac["boy"] = 60; ac["agirlik"] = 400
    bas = stil(el(4, "heading_options"), boy=84)
    notu = stil(el(4, "shortline_limit"), boy=56)
    x0 = kutu(el(4, "names_label"))[0]; gen = kutu(el(4, "names_label"))[2] - x0
    # gorev metni "Name under A | Name under B": '|' iki alanin ayiricisi sayildi (gorevdeki '—' gibi); Manrope buyuk harf etiket
    # stilinde '|' buyuk I gibi okunuyor ("NAME UNDER CANCER I", 27 Eki olcum), bu yuzden iki alan iki satir. Merkez karari bekler.
    ad_et = [f"NAME UNDER {a.upper()}", f"NAME UNDER {b.upper()}"]
    satir = [(ad_et, ac, "Up to 11 letters each, English letters, printed in capitals"),
             (["YOUR SPECIAL DATE"], ac, "Month in letters, for example 14 June 2025"),
             (["YOUR HEADING"], bas, "Paper Anniversary or Our First Year"),
             (["OPTIONAL SHORT LINE"], ac, "Up to 20 characters, Year One if left empty")]
    bloklar = [(e, sar(s, t, gen), s) for e, s, t in satir]
    ara_et = 0.75 * et["boy"]
    yuk = [blok_yuk(et, len(e)) + ara_et + blok_yuk(s, len(t)) for e, t, s in bloklar]
    not_sat = sar(notu, "Please check your spelling before you order", gen)
    ust, alt = pk[1] + 0.06 * (pk[3] - pk[1]), pk[3] - 0.05 * (pk[3] - pk[1]) - blok_yuk(notu, len(not_sat)) - 60
    bos = (alt - ust - sum(yuk)) / (len(yuk) - 1)
    if bos < 50:
        raise SystemExit(f"DUR: Y03 panel satirlari sigmiyor (aralik {bos:.0f} px)")
    y = ust
    rule = el(4, "detail_rule")
    for i, ((e, t, s), h) in enumerate(zip(bloklar, yuk)):
        yy = y + yaz(d, et, e, x0, y, gen=gen) + ara_et
        yaz(d, s, t, x0, yy, gen=gen)
        y += h + bos
        if i < len(bloklar) - 1:
            cizgi(d, x0, x0 + gen, y - bos / 2, rule)
    yaz(d, notu, not_sat, x0, pk[3] - 0.05 * (pk[3] - pk[1]) - blok_yuk(notu, len(not_sat)), gen=gen)
    marka(d, 4)
    return im, olcu


# ---------------------------------------------------------------- Y04 format (ORTAK)
def y04():
    im = tuval(8); d = ImageDraw.Draw(im)
    pan = [b for b in SL[8]["background_layers"] if b.get("type") == "panel"]
    kl = []                                        # paneller eski genislikte; yalniz yazi oldugu icin boy 61 -> 50 (alt not icin yer)
    for b in pan:
        b = dict(b, center_y_pct=55.5, height_pct=50.0)
        kl.append(panel(d, b))
    baslik(d, 8, "Digital File or Print")
    bs = stil(el(8, "digital_heading")); ds = stil(el(8, "digital_details"))
    kolon = [("Digital File", "One print ready digital file in the style and size you choose\n\nNothing is shipped"),
             ("Print", "Unframed print on matte art paper"),
             ("14 Sizes", "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2")]
    rule = el(4, "detail_rule")
    gen = (kl[0][2] - kl[0][0]) * 0.84
    satlar = [sar(ds, met, gen) for _, met in kolon]
    hh = max(blok_yuk(ds, len(x)) for x in satlar)   # uc sutun ayni ustten baslar (inceleme 27 Eki: ayri ayri ortalama kaymasi)
    for k, (bas, _), sat in zip(kl, kolon, satlar):
        cx = (k[0] + k[2]) / 2
        yb = k[1] + 0.08 * (k[3] - k[1])
        h = yaz(d, bs, [bas], cx, yb, "center", gen)
        cizgi(d, cx - 0.18 * (k[2] - k[0]), cx + 0.18 * (k[2] - k[0]), yb + h + 60, rule)
        ust = yb + h + 60; y = ust + ((k[3] - 0.08 * (k[3] - k[1])) - ust - hh) / 2
        yaz(d, ds, sat, cx, y, "center", gen)
    ns = stil(el(8, "subtitle"))
    yaz(d, ns, ["Every style and size as a print or a digital file"], W / 2, max(k[3] for k in kl) + 0.045 * H, "center", 0.9 * W)
    marka(d, 8)
    return im, dict(panel_px=[[round(v) for v in k] for k in kl])


# ---------------------------------------------------------------- Y05 surec (cifte ozel; Merkez 27 Eki karar d)
def y05(a, b, r10):
    """eski r8 (slayt 10 Free Preview) duzeni: solda Timeless poster (preview_poster kutusu + golge), sagda 4 adim (etiket + metin)"""
    im = tuval(10)
    pp = el(10, "preview_poster"); k = kutu(pp)
    im = golge(im, k, pp["shadow"])
    p, olcu = poster_kirp(r10)
    bw, bh = k[2] - k[0], k[3] - k[1]
    s_ = min(bw / p.width, bh / p.height); nw, nh = round(p.width * s_), round(p.height * s_)
    im.paste(p.resize((nw, nh), Image.LANCZOS), (round((k[0] + k[2] - nw) / 2), round((k[1] + k[3] - nh) / 2)))
    d = ImageDraw.Draw(im)
    baslik(d, 10, "Made for You, Step by Step")
    et = stil(el(10, "after_order_label")); ac = stil(el(10, "after_order_copy"), boy=60, satir=1.3)
    no = stil(el(2, "plus"), boy=84, agirlik=500)                  # eski altin vurgu rengi (slayt 2 '+' / ok: #977342)
    ns = stil(el(10, "quality_check"), boy=52)                     # 60 px sutuna sigmiyor (1553 > 1408 px)
    adim = [("01", "FREE PREVIEW BEFORE YOU ORDER", "Message us your names, your date and your style, and we send you a free preview"),
            ("02", "YOUR FINAL PREVIEW", "After your order, we send your final preview in Etsy Messages within 24 hours"),
            ("03", "YOUR APPROVAL", "Once you approve, we send your digital file in Etsy Messages, or prepare your print"),
            ("04", "A FLAT PRINT", "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper")]
    lk = kutu(el(10, "after_order_label"))
    x0 = lk[0]; gen_t = lk[2] - lk[0]; no_g = 150; gen = gen_t - no_g
    bloklar = [(n, e, sar(ac, t, gen)) for n, e, t in adim]
    ara_et = 0.6 * et["boy"]
    yuk = [blok_yuk(et, 1) + ara_et + blok_yuk(ac, len(t)) for _, _, t in bloklar]
    ust, alt = k[1], k[3]                                          # adimlar poster yuksekligi boyunca (eski r8: sag sutun poster boyunca)
    bos = (alt - ust - sum(yuk)) / (len(yuk) - 1)
    if bos < 50:
        raise SystemExit(f"DUR: Y05 adimlari sigmiyor (aralik {bos:.0f} px)")
    rule = el(10, "preview_rule")
    y = ust
    for i, ((n, e, t), h) in enumerate(zip(bloklar, yuk)):
        yaz(d, no, [n], x0, y - 0.5 * (no["boy"] - et["boy"]), gen=no_g)
        yy = y + yaz(d, et, [e], x0 + no_g, y, gen=gen) + ara_et
        yaz(d, ac, t, x0 + no_g, yy, gen=gen)
        y += h + bos
        if i < len(bloklar) - 1:
            cizgi(d, x0, x0 + gen_t, y - bos / 2, rule)
    yaz(d, ns, ["Colors may look slightly different on screen and on paper"], x0, k[3] + 0.06 * H, gen=gen_t)   # poster altindan 144 px
    marka(d, 10)
    return im, olcu


def kontak(yollar, hedef):
    """KONTAK_KUCUK.jpg (Merkez 27 Eki): 4 kart 2x2, 1600x1200, JPEG 80, < 200 KB"""
    t = Image.new("RGB", (1600, 1200), "white")
    for i, y in enumerate(yollar):
        r, c = divmod(i, 2)
        t.paste(Image.open(y).convert("RGB").resize((800, 600), Image.LANCZOS), (c * 800, r * 600))
    t.save(hedef, "JPEG", quality=80)
    kb = hedef.stat().st_size / 1024
    if kb >= 200:
        raise SystemExit(f"DUR: {hedef.name} {kb:.0f} KB (200 KB alti beklenir)")
    return round(kb, 1)


def kaydet(im, yol):
    im.resize(CIKTI, Image.LANCZOS).save(yol, "JPEG", quality=95, subsampling=0)


def EK_METIN(a, b):
    """gorev metninde olmayan, eski karttan gelen yazilar (rapora yazilir; Merkez karari bekler)"""
    return {"Y02": [f"{a} & {b}", "An original symbol for your zodiac pairing"], "hepsi": ["ASTROLOVEART"],
            "Y03_ayirici": "gorevdeki '|' cizilmedi; iki ad alani iki satir"}


def beklenen(a, b):
    """gorev metni (Merkez 27 Eki, aynen), cizim sirasiyla; buyuk/kucuk harf etiket stilidir, kapida yok sayilir"""
    return {
        "Y02": ["Your two signs, one shared symbol", a, b, f"{a} & {b}", "An original symbol for your zodiac pairing", "ASTROLOVEART"],
        "Y03": ["Your Names, Your Date",
                f"Name under {a}", f"Name under {b}", "Up to 11 letters each, English letters, printed in capitals",
                "Your Special Date", "Month in letters, for example 14 June 2025",
                "Your Heading", "Paper Anniversary or Our First Year",
                "Optional Short Line", "Up to 20 characters, Year One if left empty",
                "Please check your spelling before you order", "ASTROLOVEART"],
        "Y04": ["Digital File or Print",
                "Digital File", "One print ready digital file in the style and size you choose", "Nothing is shipped",
                "Print", "Unframed print on matte art paper",
                "14 Sizes", "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2",
                "Every style and size as a print or a digital file", "ASTROLOVEART"],
        "Y05": ["Made for You, Step by Step",
                "01", "Free Preview Before You Order", "Message us your names, your date and your style, and we send you a free preview",
                "02", "Your Final Preview", "After your order, we send your final preview in Etsy Messages within 24 hours",
                "03", "Your Approval", "Once you approve, we send your digital file in Etsy Messages, or prepare your print",
                "04", "A Flat Print", "Gold, relief and paper layer looks are printed effects, with no foil, raised layers or cut paper",
                "Colors may look slightly different on screen and on paper", "ASTROLOVEART"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cift", required=True); ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--eski-r2", required=True, help="o ciftin eski galerisinin r2 karti (yedek; burc + ortak sembol)")
    ap.add_argument("--botanical", required=True, help="o ciftin Botanical stil gorseli (yedek r12, 2400x3000)")
    ap.add_argument("--timeless", required=True, help="o ciftin Timeless stil gorseli (yedek r10, 2400x3000)")
    ap.add_argument("--out", required=True); ap.add_argument("--ortak", action="store_true", help="ORTAK_Y04 de uret (+ KONTAK_KUCUK.jpg)")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    YAZILAR.clear()
    islem = [(f"{a.cift}_Y02.jpg", lambda: y02(a.a, a.b, Image.open(a.eski_r2))),
             (f"{a.cift}_Y03.jpg", lambda: y03(a.a, a.b, Image.open(a.botanical)))]
    if a.ortak:
        islem += [("ORTAK_Y04.jpg", y04)]
    islem += [(f"{a.cift}_Y05.jpg", lambda: y05(a.a, a.b, Image.open(a.timeless)))]
    sonuc, rapor, metin = {}, {}, {}
    for ad, fn in islem:
        n0 = len(YAZILAR)
        im, o = fn(); sonuc[ad] = im; rapor[ad] = o; metin[ad] = YAZILAR[n0:]
    kotu = sorted({t for t in YAZILAR if YASAK.search(t) or YASAK_SOZ.search(t)})
    if kotu:
        raise SystemExit(f"DUR: yasak karakter / sozcuk iceren yazi: {kotu}")
    bek = beklenen(a.a, a.b)
    for ad, sat in metin.items():                   # METIN KAPISI: cizilen satirlar, sirasiyla, gorev metni + izinli ek (buyuk/kucuk harf haric) ile ayni
        g, e = " ".join(sat).split(), " ".join(bek[ad[-7:-4]]).split()
        if [x.casefold() for x in g] != [x.casefold() for x in e]:
            raise SystemExit(f"DUR: {ad} metni gorev metninden farkli\n cizilen: {' '.join(g)}\n beklenen: {' '.join(e)}")
    for ad, im in sonuc.items():
        kaydet(im, out / ad)
    if a.ortak:
        kontak_kb = kontak([out / f"{a.cift}_Y02.jpg", out / f"{a.cift}_Y03.jpg", out / "ORTAK_Y04.jpg", out / f"{a.cift}_Y05.jpg"],
                           out / "KONTAK_KUCUK.jpg")
        rapor["KONTAK_KUCUK.jpg"] = dict(boyut=[1600, 1200], kb=kontak_kb)
    girdi = {k: dict(dosya=Path(v).name, sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest()) for k, v in
             (("eski_r2", a.eski_r2), ("botanical", a.botanical), ("timeless", a.timeless))}
    (out / "KART_OZET.json").write_text(json.dumps(dict(cift=a.cift, dosyalar=list(sonuc), girdi=girdi, surum=SURUM, olcu=rapor,
                                                        yazilar=metin, gorevde_olmayan=EK_METIN(a.a, a.b), tuval=[W, H],
                                                        cikti=list(CIKTI)), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"KART: {', '.join(sonuc)} -> {out} | yazi {len(YAZILAR)} satir, yasak 0, metin kapisi PASS {len(metin)}/{len(metin)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
