#!/usr/bin/env python3
"""Wall art + kupa bilgi kartlari, YD'de onaylanan SADE stil (Serdar 'Ok', Merkez 27 Eki gorev C). ORNEK: tek cift. Etsy yok.
Stil yd_kart_ornek.py ile ayni (zemin #F5F0E7, tek yazi rengi #2B2220, Cormorant baslik, Manrope etiket ve metin, en kucuk 58 px,
panel / golge / imza yok, 3000x2250). Fotograf ve isim bandi gorselleri renk kapisi disinda (kutulari raporda).
Wall art (kaynak: Canva POSTER_GALERI_V1 s1 sembol, s2 kisisellestirme; DAHZGSI_nLw s12 format ORTAK, s13 surec ORTAK; metinler aynen,
SADE kurallari: '|' cizilmez, etiketler Title Case):
  WA_<CIFT>_S1_SEMBOL   burclar + ortak sembol (kupa_uretim/sembol/<CIFT> sol / sag / ana maskeleri, Midnight Blue posterinden; murekkep rengi)
  WA_<CIFT>_S2_KISISEL  isim bandi (canli galeri karti POSTER_GALERI_V10 <CIFT>_G3 icindeki koyu bant, kirpim)
  WA_ORTAK_S3_FORMAT, WA_ORTAK_S4_SUREC
Kupa (Orchard galerisi kupa_orchard/kod/cift.py kart 3, 5, 6, 7 = bilgi kartlari; kart 2 yakin plan ve kart 4 stil secimi fotograf
kartidir). Fotograflar ayni ciftin Orchard galeri kartlarindan cift.py'deki yapistirma kutulariyla kirpilir (yeniden uretim yok):
  KUPA_<CIFT>_K03_KISISEL, KUPA_<CIFT>_K05_BOYUT, KUPA_<CIFT>_K06_ORNEK, KUPA_<CIFT>_K07_BAKIM
Kapilar (PASS/FAIL, biri FAIL ise dosya yazilmaz): metin (cizilen satirlar = beklenen, sirayla), baslik / etiket Title Case (birim
sozcukleri oz, in, cm, ml haric), yasak karakter (ondalik nokta disinda nokta, arti, esittir, tire), yasak sozcuk (yd_kart_ornek.YASAK_SOZ),
punto >= 58, renk kapisi (cizim + JPEG), KONTAK_WA_KUPA.jpg < 300 KB.
Kullanim: wa_kupa_kart_ornek.py --cift CANCER_LIBRA --a Cancer --b Libra --sembol <dir> --g3 <G3.jpg> --orchard <galeri dir> --out <dir>"""
import argparse, hashlib, io, json, re, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

W, H = K.W, K.H
YASAK = re.compile(r"(?<!\d)\.|\.(?!\d)|[+=‐-―−]")     # ondalik nokta (9.6) serbest
BIRIM = {"oz", "in", "cm", "ml"}
ORCH = 2048                                                            # Orchard kart boyu (cift.py S)


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


def bant_kirp(g3):
    """canli G3 kartindaki isim bandi: en buyuk koyu (lum < 60) dikdortgen"""
    a = np.asarray(g3.convert("RGB")).astype(np.float32); lum = a @ np.float32([0.299, 0.587, 0.114])
    koyu = lum < 60
    sat = np.nonzero(koyu.mean(axis=1) > 0.4)[0]; sut = np.nonzero(koyu.mean(axis=0) > 0.25)[0]
    if not len(sat) or not len(sut):
        raise SystemExit("DUR: G3'te isim bandi bulunamadi")
    k = (int(sut[0]), int(sat[0]), int(sut[-1]) + 1, int(sat[-1]) + 1)
    return g3.convert("RGB").crop(k), k


def wa_s2(a, b, g3):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Your Names, Your Message")
    bant, k = bant_kirp(g3)
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
    return im, dict(g3_bant_kutu=list(k), bant=[bw, bh]), [pk]


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
def k03(a, b, src):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "How to Personalize")
    fw, ara = 820, 140; x0 = W / 2 - fw - ara / 2
    kut = []
    for j in range(2):                                   # cift.py kart 3: kupa_kirp 860x975, x = 120 + j * 948, y = 330
        kut.append(foto(im, src, (120 + j * 948, 330, 980 + j * 948, 1305), (x0 + j * (fw + ara), K.ALAN[0] - 20, fw)))
    y = kut[0][3] + 50
    sol, sag = x0 + fw / 2, x0 + fw + ara + fw / 2
    ortala(d, K.ETIKET, ["Front"], sol, y, fw); ortala(d, K.ETIKET, ["Back"], sag, y, fw)
    y += K.ETIKET["boy"] + 30
    ortala(d, K.METIN, [f"1  Name for {a}", f"2  Name for {b}", "Up to 10 letters per name"], sol, y, fw + ara)
    ortala(d, K.METIN, ["3  Your message", "Up to 30 characters"], sag, y, fw + ara)
    ortala(d, K.METIN, ["You receive one mug, printed on both sides"], W / 2, K.NOT_Y)
    return im, dict(foto=kut), kut


def k05(src):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Two Sizes")
    SC = 0.66; taban_k = 1430; kut = []
    oz = (((540, (215, 380, 1575, 1705)), "11 oz", ["9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml"]),
          ((1500, (230, 400, 1635, 2005)), "15 oz", ["11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml"]))
    f = 1.0                                              # iki kupa ayni olcekte (boy karsilastirmasi bozulmaz)
    taban = K.ALAN[0] + 1080
    for i, ((cx_k, kk), et, sat) in enumerate(oz):
        w_, h_ = round((kk[2] - kk[0]) * SC), round((kk[3] - kk[1]) * SC)   # cift.py kart 5 yapistirma kutusu
        x_, y_ = round(cx_k - w_ / 2), round(taban_k - h_)
        cx = W / 2 + (i - 0.5) * 1150
        kut.append(foto(im, src, (x_, y_, x_ + w_, y_ + h_), (cx - w_ * f / 2, taban - h_ * f, round(w_ * f))))
        y = taban + 50
        y += ortala(d, K.ETIKET, [et], cx, y, 900) + 30
        ortala(d, K.METIN, sat, cx, y, 900)
    ortala(d, K.NOT, ["Height x diameter", "Approximate size comparison"], W / 2, K.NOT_Y - 40)
    return im, dict(foto=kut), kut


def k06(src):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Your Names, Your Message")
    SUT = 864; xs_k = (128, 128 + SUT + 64)
    KUTU = {"on": (585, 1090, 1465, 1610), "arka": (555, 1060, 1495, 1520)}   # cift.py kart 6
    hk = {k: round((v[3] - v[1]) * SUT / (v[2] - v[0])) for k, v in KUTU.items()}
    fw = 880; xs = (W / 2 - 40 - fw, W / 2 + 40)
    y = K.ALAN[0] - 40
    ortala(d, K.ETIKET, ["Front"], xs[0] + fw / 2, y, fw); ortala(d, K.ETIKET, ["Back"], xs[1] + fw / 2, y, fw)
    y += K.ETIKET["boy"] + 40; yk = 400; kut = []
    for et in ("Short Example", "Long Example"):
        ortala(d, K.ETIKET, [et], W / 2, y)
        y += K.ETIKET["boy"] + 25; hmax = 0
        for x, xk, kk in ((xs[0], xs_k[0], "on"), (xs[1], xs_k[1], "arka")):
            r = foto(im, src, (xk, yk + 90, xk + SUT, yk + 90 + hk[kk]), (x, y, fw)); kut.append(r); hmax = max(hmax, r[3] - r[1])
        y += hmax + 50; yk += 90 + max(hk.values()) + 70
    if y > K.NOT_Y - 20:
        raise SystemExit(f"DUR: K06 fotograflari alt metne tasiyor ({y:.0f})")
    ortala(d, K.METIN, ["Up to 10 letters per name", "Message up to 30 characters"], W / 2, K.NOT_Y - 30)
    return im, dict(foto=kut), kut


def k07(src):
    im = K.tuval(); d = ImageDraw.Draw(im)
    K.baslik(d, "Care & Making")
    kut = [foto(im, src, (1130, 420, 1930, 1327), (K.POSTER[0] - 40, K.ALAN[0] - 20, 980))]    # cift.py kart 7
    x0 = K.SUTUN_X; y = (K.ALAN[0] + K.ALAN[1]) / 2 - 330
    for s in ["Dishwasher safe", "Microwave safe", "Glossy white ceramic, white inside", "Made to order, just for you"]:
        r = 11; cy = y + K.METIN["boy"] / 2 + 4
        d.ellipse((x0, cy - r, x0 + 2 * r, cy + r), fill=K.MUREKKEP)
        y += K.yaz(d, K.METIN, [s], x0 + 60, y, gen=W - K.KENAR - x0 - 60) + 70
    ortala(d, K.METIN, ["Original zodiac fusion symbols designed by AstroLoveArt"], W / 2, K.NOT_Y)
    return im, dict(foto=kut), kut


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
    for k in ("--cift", "--a", "--b", "--sembol", "--g3", "--orchard", "--out"):
        ap.add_argument(k, required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); sem = Path(a.sembol); og = Path(a.orchard)
    orch = {}
    for n in ("03", "05", "06", "07"):
        f = sorted(og.glob(f"{n}_*.jpg"))
        if len(f) != 1:
            raise SystemExit(f"DUR: Orchard galeri kart {n}: {len(f)} dosya ({og})")
        orch[n] = Image.open(f[0]).convert("RGB")
    for n, im in orch.items():
        if im.size != (ORCH, ORCH):
            raise SystemExit(f"DUR: Orchard kart {n} boyutu {im.size} ({ORCH}x{ORCH} beklenir)")
    c = a.cift
    islem = [(f"WA_{c}_S1_SEMBOL.jpg", lambda: wa_s1(a.a, a.b, sem)), (f"WA_{c}_S2_KISISEL.jpg", lambda: wa_s2(a.a, a.b, Image.open(a.g3))),
             ("WA_ORTAK_S3_FORMAT.jpg", wa_s3), ("WA_ORTAK_S4_SUREC.jpg", wa_s4),
             (f"KUPA_{c}_K03_KISISEL.jpg", lambda: k03(a.a, a.b, orch["03"])), (f"KUPA_{c}_K05_BOYUT.jpg", lambda: k05(orch["05"])),
             (f"KUPA_{c}_K06_ORNEK.jpg", lambda: k06(orch["06"])), (f"KUPA_{c}_K07_BAKIM.jpg", lambda: k07(orch["07"]))]
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
        sonuc[ad] = im; rapor[ad] = dict(o, renk_kapisi="PASS (cizim + JPEG)", foto_kutu=pk, yazi=yazi, kb=round(len(jb[ad]) / 1024))
    kb, q = kontak(list(sonuc.values()))
    for ad, b in jb.items():
        (out / ad).write_bytes(b)
    (out / "KONTAK_WA_KUPA.jpg").write_bytes(kb)
    girdi = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [Path(a.g3), *(sem / f"{x}.png" for x in ("sol", "sag", "ana")), *sorted(og.glob("0[3567]_*.jpg"))]}
    (out / "KART_OZET.json").write_text(json.dumps(dict(cift=c, kartlar=rapor, girdi_sha256=girdi, surum=K.SURUM, tuval=[W, H],
                                                        kontak=dict(kb=round(len(kb) / 1024, 1), kalite=q)), indent=1, ensure_ascii=False),
                                        encoding="utf-8")
    print(f"KART: {len(sonuc)} kart PASS (metin, Title Case, yasak, renk) + KONTAK_WA_KUPA.jpg {len(kb) / 1024:.0f} KB q{q} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
