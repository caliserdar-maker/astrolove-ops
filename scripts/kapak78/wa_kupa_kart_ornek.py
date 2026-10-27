#!/usr/bin/env python3
"""Wall art + kupa bilgi kartlari, YD'de onaylanan SADE stil (Serdar 'Ok', Merkez 27 Eki gorev C). ORNEK: tek cift. Etsy yok.
Stil yd_kart_ornek.py ile ayni (zemin #F5F0E7, tek yazi rengi #2B2220, Cormorant baslik, Manrope etiket ve metin, en kucuk 58 px,
panel / golge / imza yok, 3000x2250). Fotograf ve isim bandi gorselleri renk kapisi disinda (kutulari raporda).
Wall art (kaynak: Canva POSTER_GALERI_V1 s1 sembol, s2 kisisellestirme; DAHZGSI_nLw s12 format ORTAK, s13 surec ORTAK; metinler aynen,
SADE kurallari: '|' cizilmez, etiketler Title Case):
  WA_<CIFT>_S1_SEMBOL   burclar + ortak sembol (kupa_uretim/sembol/<CIFT> sol / sag / ana maskeleri, Midnight Blue posterinden; murekkep rengi)
  WA_<CIFT>_S2_KISISEL  isim bandi (Merkez 27 Eki madde 3): Midnight Blue ornek poster 2000x3000 (EMILY / JAMES / It Began With a Kiss in
                        the Rain; test siparisi 9000000532) bant kirpimi, karta ~0,95 olcekle (G3 kartindaki bant buyutulmus ve bulanikti)
  WA_ORTAK_S3_FORMAT, WA_ORTAK_S4_SUREC
Kupa (Orchard galerisi kupa_orchard/kod/cift.py kart 3, 5, 6, 7 = bilgi kartlari; kart 2 yakin plan, kart 4 stil secimi). Fotograflar
cift.py bolum 3 gorunumlerinden (tek_on, tek_arka, m15, ML_on/arka, MJ_on/arka; orchard_gorunum.py ile ayni kod ve surumlerle) ve
kupa_zemin.py ile zemini #F5F0E7'ye esitlenmis halde (Merkez 27 Eki madde 4); kupa ve golgesi korunur, kulp kesilmez:
  KUPA_<CIFT>_K03_KISISEL, KUPA_<CIFT>_K05_BOYUT, KUPA_<CIFT>_K06_ORNEK, KUPA_<CIFT>_K07_BAKIM
Kapilar (PASS/FAIL, biri FAIL ise dosya yazilmaz): metin (cizilen satirlar = beklenen, sirayla), baslik / etiket Title Case (birim
sozcukleri oz, in, cm, ml haric), yasak karakter (ondalik nokta disinda nokta, arti, esittir, tire), yasak sozcuk (yd_kart_ornek.YASAK_SOZ),
punto >= 58, renk kapisi (cizim + JPEG), zemin kapisi (kupa fotograf kutusu ic kenar seridi #F5F0E7'den en fazla ZEMIN_ESIK; kutu
icinde kupa + golge parcasina (fark > 1 ile bagli) bagli olmayan, fark > 3 piksel yok),
KONTAK_WA_KUPA.jpg < 300 KB.
Kullanim: wa_kupa_kart_ornek.py --cift CANCER_LIBRA --a Cancer --b Libra --sembol <dir> --poster <MB 2000x3000> --sahne <z_/k_ dir> --out <dir>"""
import argparse, hashlib, io, json, re, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

W, H = K.W, K.H
YASAK = re.compile(r"(?<!\d)\.|\.(?!\d)|[+=‐-―−]")     # ondalik nokta (9.6) serbest
BIRIM = {"oz", "in", "cm", "ml"}
SAHNELER = ("tek_on", "tek_arka", "m15", "ML_on", "ML_arka", "MJ_on", "MJ_arka")   # kupa_orchard cift.py bolum 3 gorunumleri
ZEMIN_ESIK = 3                 # fotograf kutusu kenar seridi ile #F5F0E7 arasinda izinli en buyuk RGB farki (cizim; kupa_zemin olcumu 0-3)


def title_ok(t):
    return K.title_case(" ".join(x for x in t.split() if x not in BIRIM)) or all(x in BIRIM or x[0].isdigit() for x in t.split())


def ortala(d, s, satirlar, cx, y, gen=None):
    return K.yaz(d, s, satirlar, cx, y, "center", gen or W - 2 * K.KENAR)


def foto(im, src, kutu, hedef):
    """src kirpim (kutu) -> hedef (x, y, w) genislik; -> gercek kutu"""
    p = src.crop(kutu)
    x, y, w = hedef; h = round(p.height * w / p.width)
    im.paste(p.resize((w, h), Image.LANCZOS), (round(x), round(y)))
    return [round(x), round(y), round(x) + w, round(y) + h]


def maske(yol, h):
    """kupa_uretim sembol maskesi (RGBA, alfa = altin) -> murekkep renginde RGBA, yukseklik h"""
    a = Image.open(yol).convert("RGBA").getchannel("A")
    a = a.crop(a.getbbox()); a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    al = np.asarray(a).astype(np.float32) / 255
    al = np.clip((al - 0.2) / 0.6, 0, 1)                               # yd_kart_ornek.sembol_al ile ayni keskin kenar
    rgba = np.zeros(al.shape + (4,), np.uint8); rgba[..., :3] = K.rgb(K.MUREKKEP); rgba[..., 3] = (al * 255).astype(np.uint8)
    return Image.fromarray(rgba)


# ---------------------------------------------------------------- wall art
def wa_s1(a, b, sem):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Two Signs, One Shared Symbol")
    ortala(d, K.METIN, [f"{a} and {b} joined in an original AstroLoveArt design"], W / 2, K.BASLIK_Y + K.BASLIK["boy"] + 50)
    gh, cxs, gy = 300, (W / 2 - 560, W / 2 + 560), 680
    for f, cx, ad in ((sem / "sol.png", cxs[0], a), (sem / "sag.png", cxs[1], b)):
        g = maske(f, gh); im.paste(g, (round(cx - g.width / 2), gy), g)
        ortala(d, K.ETIKET, [ad], cx, gy + gh + 50, 0.3 * W)
    ty = gy + gh + 50 + K.ETIKET["boy"] + 60; uy = ty + 170
    for cx in cxs:
        K.cizgi(d, (cx, ty), (W / 2, uy))
    uc = 24
    d.line([(W / 2 - uc * 0.6, uy - uc), (W / 2, uy), (W / 2 + uc * 0.6, uy - uc)], fill=K.MUREKKEP, width=K.CIZGI)
    s = maske(sem / "ana.png", round(K.NOT_Y - 80 - (uy + 50)))
    im.paste(s, (round(W / 2 - s.width / 2), round(uy + 50)), s)
    ortala(d, K.METIN, ["Personalized with your two names and your message"], W / 2, K.NOT_Y)
    return im, dict(glif_h=gh, sembol=[s.width, s.height]), []


BANT_ORAN = 1798 / 812          # canli G3 kartindaki bandin en / boy orani (20261026_181944 olcumu)


def bant_kirp(poster):
    """Midnight Blue ornek poster (EMILY / JAMES / It Began With a Kiss in the Rain) -> isim bandi: altin satirlar (R - B > 60)
    halkadan sonra 3 bant (burclar, isimler, mesaj); tam genislik, yukseklik = genislik / BANT_ORAN, icerik dikeyde ortali"""
    a = np.asarray(poster.convert("RGB")).astype(np.int16)
    sat = ((a[..., 0] - a[..., 2] > 60) & (a[..., 0] > 120)).mean(axis=1) > 0.002
    idx = np.nonzero(sat)[0]; bant = []; s0 = p0 = int(idx[0])
    for i in idx[1:]:
        if i - p0 > 15:
            bant.append((s0, p0)); s0 = int(i)
        p0 = int(i)
    bant.append((s0, p0))
    hal = max(range(len(bant)), key=lambda j: bant[j][1] - bant[j][0])
    alt = [b_ for b_ in bant[hal + 1:] if b_[1] - b_[0] > 40][:3]
    if len(alt) != 3:
        raise SystemExit(f"DUR: posterde burc / isim / mesaj bantlari bulunamadi ({bant})")
    w = a.shape[1]; h = round(w / BANT_ORAN); ust = round((alt[0][0] + alt[2][1]) / 2 - h / 2)
    if ust < bant[hal][1] or ust + h > a.shape[0]:
        raise SystemExit(f"DUR: bant kirpimi halkaya / kenara tasiyor ({ust}, {h})")
    k = (0, ust, w, ust + h)
    return poster.convert("RGB").crop(k), k


def wa_s2(a, b, poster):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Your Names, Your Message")
    bant, k = bant_kirp(poster)
    bw = 1900; bh = round(bant.height * bw / bant.width); by = round(K.ALAN[0] - 20)
    im.paste(bant.resize((bw, bh), Image.LANCZOS), (round(W / 2 - bw / 2), by))
    pk = [round(W / 2 - bw / 2), by, round(W / 2 - bw / 2) + bw, by + bh]
    y = by + bh + 90
    y += ortala(d, K.ETIKET, [f"Name Under {a}", f"Name Under {b}"], W / 2, y) + 25
    y += ortala(d, K.METIN, ["Up to 11 letters each, English letters, printed in capitals"], W / 2, y) + 75
    y += ortala(d, K.ETIKET, ["Your Message"], W / 2, y) + 25
    y += ortala(d, K.METIN, ["Up to 35 characters, printed as you type it, no emoji"], W / 2, y)
    if y > K.NOT_Y - 40:
        raise SystemExit(f"DUR: S2 metni alt nota tasiyor ({y:.0f} > {K.NOT_Y - 40:.0f})")
    ortala(d, K.NOT, ["Please check your spelling before you order"], W / 2, K.NOT_Y)
    return im, dict(poster_bant_kutu=list(k), bant=[bw, bh], olcek=round(bw / bant.width, 4)), [pk]


def wa_s3():
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Digital File or Print")
    kolon = [("Digital File", ["One print ready digital file in the color and size you choose", "Nothing is shipped"]),
             ("Print", ["Unframed print on matte art paper", "Free shipping worldwide"]),
             ("13 Sizes", ["8x10, 11x14, 12x16, 12x18, 16x20 in", "16x24, 18x24, 20x30, 24x30, 24x36 in", "A4, A3, A2"])]   # Canva'daki 3 satir
    kg = (W - 2 * K.KENAR) / 3; gen = kg - 0.06 * W
    sat = [[K.sar_d(K.METIN, m, gen) for m in ms] for _, ms in kolon]
    ara_p = 0.6 * K.METIN["boy"]
    hh = max(sum(K.blok_yuk(K.METIN, len(x)) for x in s) + ara_p * (len(s) - 1) for s in sat)
    ara = 0.45 * K.ETIKET["boy"] + K.ETIKET["boy"]
    ust = (K.ALAN[0] + K.ALAN[1]) / 2 - (ara + hh) / 2; alt = ust + ara + hh
    for i, ((bas, _), s) in enumerate(zip(kolon, sat)):
        cx = K.KENAR + kg * (i + 0.5)
        K.yaz(d, K.ETIKET, [bas], cx, ust, "center", gen)
        y = ust + ara
        for p in s:
            y += K.yaz(d, K.METIN, p, cx, y, "center", gen) + ara_p
        if i:
            K.cizgi(d, (K.KENAR + kg * i, ust - 0.02 * H), (K.KENAR + kg * i, alt + 0.02 * H))
    ortala(d, K.NOT, ["Every size as a print or a digital file"], W / 2, K.NOT_Y)
    return im, dict(kolon_px=round(kg)), []


def wa_s4():
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Made for You, Step by Step")
    x0, gen = 0.2 * W, 0.6 * W
    K.adimlar(d, x0, gen, [
        ("01", ["Your Preview"], "For every print, we send a preview via Etsy Messages within 24 hours of your order"),
        ("02", ["Your Approval"], "We print once you approve, or as shown if there is no reply within 24 hours of the preview"),
        ("03", ["Made to Order"], "Printed on matte art paper, gold tones are printed color, not metallic foil"),
        ("04", ["Free Shipping"], "Free shipping worldwide, see the listing for your delivery estimate")], no_g=round(1.75 * K.ETIKET["boy"]))
    ortala(d, K.NOT, ["Digital files are checked by hand before sending"], W / 2, K.NOT_Y)
    return im, {}, []


# ---------------------------------------------------------------- kupa (Orchard)
def sahne(d, ad):
    """kupa_zemin ile zemini esitlenmis Orchard gorunumu (z_<ad>.png) + kupa maskesi (k_<ad>.npy)"""
    return Image.open(Path(d) / f"z_{ad}.png").convert("RGB"), np.load(Path(d) / f"k_{ad}.npy")


def kupa_kutu(z, k, pay=30):
    """kupa + golgesi: zeminden (#F5F0E7) 2'den fazla farkli piksellerin kutusu + pay (kirpim kenari golgeyi kesmesin);
    k z'nin alt dilimi olabilir (k.shape[0] satir, z'nin son satirlari)"""
    a = np.asarray(z)[-k.shape[0]:]
    fark = np.abs(a.astype(np.int16) - np.int16(K.rgb(K.ZEMIN))).max(axis=2) > 2
    ys, xs = np.nonzero(fark | (k > 0))
    return [max(0, int(xs.min()) - pay), max(0, int(ys.min()) - pay), min(k.shape[1], int(xs.max()) + pay + 1),
            min(k.shape[0], int(ys.max()) + pay + 1)]


def yapistir(im, src, kutu, x, y, s, fade=0, dort=False):
    """src[kutu] -> s olcekli, (x, y) sol ust; fade > 0: ust kenar (dort=True: dort kenar) fade px (kart olceginde) icinde zemine
    yumusak gecis (smoothstep); ilk 8 px tam zemin (kenar seridi)"""
    p = src.crop(kutu); w, h = round(p.width * s), round(p.height * s)
    p = p.resize((w, h), Image.LANCZOS)
    if fade:
        a = np.asarray(p).astype(np.float32); z = np.float32(K.rgb(K.ZEMIN))
        r = lambda n: np.clip((np.arange(n, dtype=np.float32) - 8) / fade, 0, 1)
        ty = r(h)
        if dort:
            ty = np.minimum(ty, r(h)[::-1]); tx = np.minimum(r(w), r(w)[::-1])
        else:
            tx = np.ones(w, np.float32)
        t = np.minimum(ty[:, None], tx[None, :]); t = (t * t * (3 - 2 * t))[..., None]
        p = Image.fromarray(np.round(z + (a - z) * t).astype(np.uint8))
    im.paste(p, (round(x), round(y)))
    return [round(x), round(y), round(x) + w, round(y) + h]


def k03(a, b, sd):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "How to Personalize")
    (zo, ko), (za, ka) = sahne(sd, "tek_on"), sahne(sd, "tek_arka")
    bo, ba = kupa_kutu(zo, ko), kupa_kutu(za, ka)
    s = 900 / max(bo[3] - bo[1], ba[3] - ba[1]); ara = 60
    wo, wa = (bo[2] - bo[0]) * s, (ba[2] - ba[0]) * s
    x0 = W / 2 - (wo + ara + wa) / 2; y0 = K.ALAN[0] - 40
    kut = [yapistir(im, zo, bo, x0, y0, s), yapistir(im, za, ba, x0 + wo + ara, y0, s)]
    y = max(k[3] for k in kut) + 30
    sol, sag = x0 + wo / 2, x0 + wo + ara + wa / 2
    ortala(d, K.ETIKET, ["Front"], sol, y, wo); ortala(d, K.ETIKET, ["Back"], sag, y, wa)
    y += K.ETIKET["boy"] + 30
    ortala(d, K.METIN, [f"1  Name for {a}", f"2  Name for {b}", "Up to 10 letters per name"], sol, y, wo + ara)
    ortala(d, K.METIN, ["3  Your message", "Up to 30 characters"], sag, y, wa + ara)
    ortala(d, K.METIN, ["You receive one mug, printed on both sides"], W / 2, K.NOT_Y)
    return im, dict(foto=kut, olcek=round(s, 4)), kut


def k05(sd):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Two Sizes")
    oz = (("tek_on", "11 oz", ["9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml"]), ("m15", "15 oz", ["11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml"]))
    sh = [sahne(sd, ad) for ad, _, _ in oz]
    ku = [kupa_kutu(z, k) for z, k in sh]
    s = 1020 / max(k[3] - k[1] for k in ku)                 # iki sahne ayni olcekte (cift.py kart 5 gibi; boy karsilastirmasi bozulmaz)
    taban = K.ALAN[0] + 1060; kut = []
    for i, ((ad, et, sat), (z, k), kk) in enumerate(zip(oz, sh, ku)):
        alt = int(np.nonzero(k)[0].max())                   # kupa tabani ayni cizgide
        cx = W / 2 + (i - 0.5) * 1180
        kut.append(yapistir(im, z, kk, cx - (kk[2] - kk[0]) * s / 2, taban - (alt - kk[1]) * s, s))
        y = taban + (kk[3] - alt) * s + 20
        y += ortala(d, K.ETIKET, [et], cx, y, 900) + 30
        ortala(d, K.METIN, sat, cx, y, 900)
    ortala(d, K.NOT, ["Height x diameter", "Approximate size comparison"], W / 2, K.NOT_Y - 40)
    return im, dict(foto=kut, olcek=round(s, 4)), kut


def k06(sd):
    """kisa / uzun ornek: tam kupa gorunumleri (ML_on / ML_arka, MJ_on / MJ_arka; zemin esitlenmis, kesit yok; inceleme 27 Eki:
    yakin kesit + yumusak gecis panel / hale gibi duruyordu). Dort kupa ayni olcekte."""
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Your Names, Your Message")
    sh = {ad: sahne(sd, ad) for ad in ("ML_on", "ML_arka", "MJ_on", "MJ_arka")}
    ku = {ad: kupa_kutu(z, k) for ad, (z, k) in sh.items()}
    y = K.ALAN[0] - 40
    hmax_k = max(v[3] - v[1] for v in ku.values()); wmax_k = max(v[2] - v[0] for v in ku.values())
    satir_h = (K.NOT_Y - 60 - (y + K.ETIKET["boy"] + 30) - 2 * (K.ETIKET["boy"] + 10) - 30) / 2
    s = 0.97 * min(satir_h / hmax_k, 1250 / wmax_k)              # 0,97: satir aralari ve alt metin payi
    xs = (W / 2 - 40 - 1250, W / 2 + 40)
    ortala(d, K.ETIKET, ["Front"], xs[0] + 625, y, 1250); ortala(d, K.ETIKET, ["Back"], xs[1] + 625, y, 1250)
    y += K.ETIKET["boy"] + 30; kut = []
    for et, on, ar in (("Short Example", "ML_on", "ML_arka"), ("Long Example", "MJ_on", "MJ_arka")):
        ortala(d, K.ETIKET, [et], W / 2, y)
        y += K.ETIKET["boy"] + 10
        for x, ad in ((xs[0], on), (xs[1], ar)):
            z, _ = sh[ad]; kk = ku[ad]
            kut.append(yapistir(im, z, kk, x + (1250 - (kk[2] - kk[0]) * s) / 2, y, s))
        y += hmax_k * s + 30
    if y > K.NOT_Y - 40:
        raise SystemExit(f"DUR: K06 fotograflari alt metne tasiyor ({y:.0f})")
    ortala(d, K.METIN, ["Up to 10 letters per name", "Message up to 30 characters"], W / 2, K.NOT_Y - 30)
    return im, dict(foto=kut, olcek=round(s, 4)), kut


def k07(sd):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Care & Making")
    z, k = sahne(sd, "tek_on"); kk = kupa_kutu(z, k)
    s = 1000 / (kk[2] - kk[0])
    kut = [yapistir(im, z, kk, K.POSTER[0] - 120, (K.ALAN[0] + K.ALAN[1]) / 2 - (kk[3] - kk[1]) * s / 2, s)]
    x0 = K.SUTUN_X + 40; y = (K.ALAN[0] + K.ALAN[1]) / 2 - 330
    for t in ["Dishwasher safe", "Microwave safe", "Glossy white ceramic, white inside", "Made to order, just for you"]:
        r = 11; cy = y + K.METIN["boy"] / 2 + 4
        d.ellipse((x0, cy - r, x0 + 2 * r, cy + r), fill=K.MUREKKEP)
        y += K.yaz(d, K.METIN, [t], x0 + 60, y, gen=W - K.KENAR - x0 - 60) + 70
    ortala(d, K.METIN, ["Original zodiac fusion symbols designed by AstroLoveArt"], W / 2, K.NOT_Y)
    return im, dict(foto=kut, olcek=round(s, 4)), kut


def kopuk_ton(im, kutular, esik=3, bag=1):
    """fotograf kutusu icinde zeminden (#F5F0E7) esik'ten fazla farkli piksellerden, kutunun en buyuk (kupa + golge) parcasina bagli
    OLMAYANLAR (kopuk leke / ton farki / panel kalintisi; inceleme 27 Eki: kenar seridi tek basina yetmiyordu). Baglanti fark > bag
    ile kurulur (golge kuyrugu ana golgeye soluk piksellerle baglidir). -> (kopuk piksel sayisi, parcalar [x, y, w, h, alan])"""
    import cv2
    a = np.asarray(im.convert("RGB")).astype(np.int16); z = np.int16(K.rgb(K.ZEMIN)); n_k = 0; liste = []
    for x0, y0, x1, y1 in kutular:
        f = np.abs(a[y0:y1, x0:x1] - z).max(axis=2)
        n, lab, st, _ = cv2.connectedComponentsWithStats((f > bag).astype(np.uint8), 8)
        if n > 2:
            en = 1 + int(np.argmax(st[1:, 4]))
            for i in range(1, n):
                c = (lab == i) & (f > esik)
                if i != en and c.any():
                    n_k += int(c.sum()); liste.append([x0 + int(st[i, 0]), y0 + int(st[i, 1]), int(st[i, 2]), int(st[i, 3]), int(c.sum())])
    return n_k, liste


def zemin_kenar(im, kutular, serit=6):
    """yapistirilan fotograf kutularinin ic kenar seridinde #F5F0E7'den en buyuk RGB farki (panel / kenar kapisi)"""
    a = np.asarray(im.convert("RGB")).astype(np.float32); z = np.float32(K.rgb(K.ZEMIN)); m = 0.0
    for x0, y0, x1, y1 in kutular:
        p = a[y0:y1, x0:x1]
        for sr in (p[:serit], p[-serit:], p[:, :serit], p[:, -serit:]):
            m = max(m, float(np.abs(sr - z).max()))
    return m


def beklenen(a, b):
    return {
        "S1_SEMBOL": ["Two Signs, One Shared Symbol", f"{a} and {b} joined in an original AstroLoveArt design", a, b,
                      "Personalized with your two names and your message"],
        "S2_KISISEL": ["Your Names, Your Message", f"Name Under {a}", f"Name Under {b}",
                       "Up to 11 letters each, English letters, printed in capitals", "Your Message",
                       "Up to 35 characters, printed as you type it, no emoji", "Please check your spelling before you order"],
        "S3_FORMAT": ["Digital File or Print", "Digital File", "One print ready digital file in the color and size you choose",
                      "Nothing is shipped", "Print", "Unframed print on matte art paper", "Free shipping worldwide", "13 Sizes",
                      "8x10, 11x14, 12x16, 12x18, 16x20 in", "16x24, 18x24, 20x30, 24x30, 24x36 in", "A4, A3, A2",
                      "Every size as a print or a digital file"],
        "S4_SUREC": ["Made for You, Step by Step",
                     "01", "Your Preview", "For every print, we send a preview via Etsy Messages within 24 hours of your order",
                     "02", "Your Approval", "We print once you approve, or as shown if there is no reply within 24 hours of the preview",
                     "03", "Made to Order", "Printed on matte art paper, gold tones are printed color, not metallic foil",
                     "04", "Free Shipping", "Free shipping worldwide, see the listing for your delivery estimate",
                     "Digital files are checked by hand before sending"],
        "K03_KISISEL": ["How to Personalize", "Front", "Back", f"1 Name for {a}", f"2 Name for {b}", "Up to 10 letters per name",
                        "3 Your message", "Up to 30 characters", "You receive one mug, printed on both sides"],
        "K05_BOYUT": ["Two Sizes", "11 oz", "9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml", "15 oz", "11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml",
                      "Height x diameter", "Approximate size comparison"],
        "K06_ORNEK": ["Your Names, Your Message", "Front", "Back", "Short Example", "Long Example",
                      "Up to 10 letters per name", "Message up to 30 characters"],
        "K07_BAKIM": ["Care & Making", "Dishwasher safe", "Microwave safe", "Glossy white ceramic, white inside",
                      "Made to order, just for you", "Original zodiac fusion symbols designed by AstroLoveArt"]}


def kontak(kartlar):
    t = Image.new("RGB", (4 * 600, 2 * 450), "white")
    for i, im in enumerate(kartlar):
        r, c = divmod(i, 4); t.paste(im.resize((600, 450), Image.LANCZOS), (c * 600, r * 450))
    for q in (85, 80, 75, 70, 65):
        b = io.BytesIO(); t.save(b, "JPEG", quality=q)
        if b.tell() < 300 * 1024:
            return b.getvalue(), q
    raise SystemExit(f"DUR: KONTAK_WA_KUPA.jpg {b.tell() / 1024:.0f} KB (300 KB alti beklenir)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--cift", "--a", "--b", "--sembol", "--poster", "--sahne", "--out"):
        ap.add_argument(k, required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); sem = Path(a.sembol); sd = Path(a.sahne)
    gerek = [sd / f"{p}_{ad}.{u}" for ad in SAHNELER for p, u in (("z", "png"), ("k", "npy"))]
    eksik = [p.name for p in gerek if not p.exists()]
    if eksik:
        raise SystemExit(f"DUR: sahne dosyalari eksik: {eksik}")
    c = a.cift
    islem = [(f"WA_{c}_S1_SEMBOL.jpg", lambda: wa_s1(a.a, a.b, sem)), (f"WA_{c}_S2_KISISEL.jpg", lambda: wa_s2(a.a, a.b, Image.open(a.poster))),
             ("WA_ORTAK_S3_FORMAT.jpg", wa_s3), ("WA_ORTAK_S4_SUREC.jpg", wa_s4),
             (f"KUPA_{c}_K03_KISISEL.jpg", lambda: k03(a.a, a.b, sd)), (f"KUPA_{c}_K05_BOYUT.jpg", lambda: k05(sd)),
             (f"KUPA_{c}_K06_ORNEK.jpg", lambda: k06(sd)), (f"KUPA_{c}_K07_BAKIM.jpg", lambda: k07(sd))]
    bek = beklenen(a.a, a.b); sonuc, rapor, jb = {}, {}, {}
    for ad, fn in islem:
        anah = "_".join(ad[:-4].split("_")[-2:])
        n0 = len(K.YAZILAR)
        im, o, pk = fn()
        yazi, sat = K.YAZILAR[n0:], K.SATIRLAR[n0:]
        kotu = [t for t in yazi if YASAK.search(t) or K.YASAK_SOZ.search(t)]
        if kotu:
            raise SystemExit(f"DUR: {ad} yasak karakter / sozcuk: {kotu}")
        for tur, t in sat:
            if tur in ("baslik", "etiket") and not title_ok(t) and not t.isdigit():
                raise SystemExit(f"DUR: {ad} {tur} satiri Title Case degil: {t!r}")
        g, e = " ".join(yazi).split(), " ".join(bek[anah]).split()
        if [x.casefold() for x in g] != [x.casefold() for x in e]:
            raise SystemExit(f"DUR: {ad} metni beklenenden farkli\n cizilen: {' '.join(g)}\n beklenen: {' '.join(e)}")
        sap = K.renk_kapisi(im, pk)
        if sap:
            raise SystemExit(f"DUR: {ad} renk kapisi (cizim) {sap}")
        jb[ad] = K.jpeg_bayt(im)
        sapj = K.renk_kapisi(Image.open(io.BytesIO(jb[ad])), pk, jpeg=True)
        if sapj:
            raise SystemExit(f"DUR: {ad} renk kapisi (JPEG) {sapj}")
        zk = kp = kl = None
        if ad.startswith("KUPA_"):                           # ZEMIN KAPISI: fotograf kutusu ic kenar seridi kart zeminine esit (panel yok)
            zk = zemin_kenar(im, pk); kp, kl = kopuk_ton(im, pk)
            if zk > ZEMIN_ESIK:
                raise SystemExit(f"DUR: {ad} fotograf kenari zeminden farkli (en buyuk {zk:.0f} > {ZEMIN_ESIK})")
            if kp:
                raise SystemExit(f"DUR: {ad} fotograf kutusunda kupadan kopuk zemin disi ton {kp} px")
        sonuc[ad] = im; rapor[ad] = dict(o, renk_kapisi="PASS (cizim + JPEG)", foto_kutu=pk, zemin_kenar_max=zk, kopuk_ton_px=kp, kopuk_parcalar=kl if zk is not None else None, yazi=yazi,
                                         kb=round(len(jb[ad]) / 1024))
    kb, q = kontak(list(sonuc.values()))
    for ad, b in jb.items():
        (out / ad).write_bytes(b)
    (out / "KONTAK_WA_KUPA.jpg").write_bytes(kb)
    girdi = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [Path(a.poster), *(sem / f"{x}.png" for x in ("sol", "sag", "ana")), *gerek]}
    (out / "KART_OZET.json").write_text(json.dumps(dict(cift=c, kartlar=rapor, girdi_sha256=girdi, surum=K.SURUM, tuval=[W, H],
                                                        kontak=dict(kb=round(len(kb) / 1024, 1), kalite=q)), indent=1, ensure_ascii=False),
                                        encoding="utf-8")
    print(f"KART: {len(sonuc)} kart PASS (metin, Title Case, yasak, renk) + KONTAK_WA_KUPA.jpg {len(kb) / 1024:.0f} KB q{q} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
