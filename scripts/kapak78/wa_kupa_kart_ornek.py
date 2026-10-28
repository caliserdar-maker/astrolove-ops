#!/usr/bin/env python3
"""Wall art + kupa bilgi kartlari, KART SABLONU (Merkez 28 Eki, Serdar onayi). ORNEK: tek cift (CANCER_LIBRA). Etsy yok, toplu uretim yok.
Stil yd_kart_ornek.py SADE; yerlesim ve yerlesim kapilari kart_sablon.py (ayni kart turu uc kategoride ayni fonksiyon).
Wall art (galeri sirasi: 1 kapak, 2 sembol, 3 kisisellestirme, 4 format, 5 surec, 6 genel bakis, 7-10 renkler):
  WA_<CIFT>_S1_SEMBOL   sembol karti (kupa_uretim/sembol/<CIFT> sol / sag / ana), Bezier baglac
  WA_<CIFT>_S2_KISISEL  Midnight Blue ornek poster TAM (2000x3000; EMILY / JAMES / It Began With a Kiss in the Rain) + 2 blok
  WA_ORTAK_S3_FORMAT    tablo (Digital File / Print / 14 Sizes)
  WA_<CIFT>_S4_SUREC    Champagne Ivory 4:5 poster (canli G8 ic baski kirpimi, ref poster_kaynak) + 4 adim (metinler mevcut S4 ile aynen)
  WA_<CIFT>_S5_GENEL    renk secimi 3 + 2: Midnight Blue (kisisellestirilmis 4x5 kaynak), Deep Black / Pure White / Champagne Ivory /
                        Warm Parchment (canli G6-G9 ic baski kirpimlari); ayni yukseklik, yalniz kucultme
Kupa (Orchard gorunumleri cift.py bolum 3, orchard_gorunum.py; zemin kupa_zemin.py ile #F5F0E7). KUPA KIRPIM KURALI: zeminden RGB farki > 3
pikselerin en kucuk kutusu + 4 px (kupa + golge). Galeri sirasi: 1 kapak, 2 sembol, 3 kisisellestirme, 4 boyut (K05), 5 surec (K07),
6 genel bakis (K04), 7+ stil kapaklari; K06 cikti (canlidan silinecek), eski K07 "Care & Making" uretilmez (bakim bilgisi K07 surecte):
  KUPA_<CIFT>_K02_SEMBOL  sembol karti (eski K02 yakin plan fotografi IPTAL)
  KUPA_<CIFT>_K03_KISISEL tek on ustte, tek arka altta (30 px), her biri (icerik alani - 30) / 2 yukseklige
  KUPA_<CIFT>_K04_STIL    8 stil 4 + 4 (cift.py ST8 sirasi), ayni olcek (kupa ~452 px = onizleme 491 x 0,92), yan bosluk 150, etiket 40 px alt,
                          satirlar 110 px; alt not "Every style in 11 oz and 15 oz" (dogrulama: 23 Eki salt okuma envanter dokumu, 25/25 kupa
                          ilaninda 8 stil x 11 oz / 15 oz; kupa_fiyat.py envanter kapisi 11 oz 8 + 15 oz 8)
  KUPA_<CIFT>_K05_BOYUT   iki kupa ayni olcekte (15 oz yuksekligi onaylanan onizlemedeki 989 px), kirpim kutusu tabanlari hizali, merkezler arasi
                          en genis kupa + 220; 90 px altta etiket, 0,3 x 68 px sonra 3 satir; yazi - alt not >= 100 px
  KUPA_<CIFT>_K07_SUREC   tek on + 4 adim (sure ve ucretsiz kargo yok)
K05 olculeri Printful White Glossy Mug katalog degerleri (Printful API /products/19, kosu 40642887254); ml = US fl oz x 29,5735.
Kapilar (PASS/FAIL, biri FAIL ise hicbir dosya yazilmaz): metin (cizilen satirlar = beklenen, sirayla), baslik / etiket Title Case (birim
sozcukleri oz, in, cm, ml haric), yasak karakter (ondalik nokta disinda nokta, arti, esittir, uzun / orta tire), yasak sozcuk, punto >= 58,
renk kapisi (cizim + JPEG; baglacin uc noktalarinin 4 px yakininda ara ton serbest), yerlesim kapilari (kart_sablon.py: ortalama <= 2 px,
ayri bloklar >= 40 px, baglac), kupa: zemin kapisi (fotograf kutusu kenar seritlerinin medyan farki <= ZEMIN_ESIK; panel / kutu kenari yok)
ve kopuk ton (kupa + golge parcasina bagli olmayan fark > 3 piksel yok).
Kullanim: wa_kupa_kart_ornek.py --cift C --a A --b B --sembol <dir> --poster <MB 2000x3000> --mb45 <MB 4x5> --poster-kaynak <dir> --sahne <dir> --out <dir>"""
import argparse, hashlib, io, json, re, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402
import kart_sablon as S  # noqa: E402

W, H = K.W, K.H
YASAK = re.compile(r"(?<!\d)\.|\.(?!\d)|[+=‐-―−]")     # ondalik nokta (9.6) serbest
BIRIM = {"oz", "in", "cm", "ml"}
ST8 = (("orange", "Orange Blossom"), ("fig", "Purple Fig"), ("olive", "Olive Breeze"), ("pomegranate", "Pomegranate Bloom"),
       ("almond", "Almond Blossom"), ("lemon", "Lemon Grove"), ("grape", "Blue Grape"), ("loquat", "Golden Loquat"))   # cift.py ST8 sirasi
SAHNELER = ("tek_on", "tek_arka", "m15") + tuple(f"stil_{s}" for s, _ in ST8)
ZEMIN_ESIK = 3                 # fotograf kutusu kenar seridi medyani ile #F5F0E7 arasinda izinli en buyuk RGB farki
RENKLER = (("Midnight Blue", None), ("Deep Black", "DEEP_BLACK_4x5_G6ic.png"), ("Pure White", "PURE_WHITE_4x5_G7ic.png"),
           ("Champagne Ivory", "CHAMPAGNE_IVORY_4x5_G8ic.png"), ("Warm Parchment", "WARM_PARCHMENT_4x5_G9ic.png"))
K04_KUPA_H = 452               # Merkez 28 Eki: onizleme 491 x 0,92
K05_15_H = 989                 # Merkez 28 Eki: onaylanan onizlemede 15 oz kupa yuksekligi (11 oz ayni olcekte)
K05_ARA, K05_ET, K05_NOT_ARA = 90, 0.3 * K.ETIKET["boy"], 100
BOYLAR = "5x7, 8x10, 11x14, 12x16, 12x18, 16x20, 16x24, 18x24, 20x30, 24x30, 24x36 in, A4, A3, A2"


def title_ok(t):
    return K.title_case(" ".join(x for x in t.split() if x not in BIRIM)) or all(x in BIRIM or x[0].isdigit() for x in t.split())


def sahne(d, ad):
    """kupa_zemin ile zemini esitlenmis Orchard gorunumu -> kupa kirpimi (fark > 3 + 4 px)"""
    return S.kupa_kirp(Image.open(Path(d) / f"z_{ad}.png"))


# ---------------------------------------------------------------- wall art
def wa_s2(a, b, poster):
    return S.yan_kart("Your Names, Your Message", [poster.convert("RGB")], [
        (None, [f"Name Under {a}", f"Name Under {b}"], "Up to 11 letters each, English letters, printed in capitals"),
        (None, ["Your Message"], "Up to 35 characters, printed as you type it, no emoji")], "Please check your spelling before you order")


def wa_s3():
    return S.tablo_kart("Digital File or Print", [
        ("Digital File", ["One print ready digital file in the color and size you choose", "Nothing is shipped"]),
        ("Print", ["Unframed print on matte art paper", "Free shipping worldwide"]),
        ("14 Sizes", [BOYLAR])], "Every size as a print or a digital file")


def wa_s4(ci):
    return S.yan_kart("Made for You, Step by Step", [ci], [
        ("01", ["Your Preview"], "For every order, we send a preview via Etsy Messages within 24 hours of your order"),
        ("02", ["Your Approval"], "We make your print or file once you approve, or as shown if there is no reply within 24 hours of the preview"),
        ("03", ["Made to Order"], "Printed on matte art paper, gold tones are printed color, not metallic foil"),
        ("04", ["Free Shipping"], "Free shipping worldwide, see the listing for your delivery estimate")],
        "Digital files are checked by hand before sending", surec=True)


def wa_s5(renkler):
    return S.secim_kart("Choose Your Color", renkler, "Every color as a print or a digital file")


# ---------------------------------------------------------------- kupa
def k03(a, b, sd):
    (on, ko), (ar, ka) = sahne(sd, "tek_on"), sahne(sd, "tek_arka")
    im, o, kut = S.yan_kart("Your Names, Your Message", [on, ar], [
        (None, [f"Name Under {a}", f"Name Under {b}"], "Up to 10 letters each, printed in capitals on the front"),
        (None, ["Your Message"], "Up to 30 characters, printed on the back with your names"),
        (None, ["One Mug, Two Sides"], "Front with your symbol and names, back with your message")],
        "Please check your spelling before you order")
    return im, dict(o, kirpim=dict(tek_on=ko, tek_arka=ka)), kut


def k07(sd):
    on, ko = sahne(sd, "tek_on")
    im, o, kut = S.yan_kart("Made for You, Step by Step", [on], [
        ("01", ["Your Preview"], "For every order, we send a preview of your mug via Etsy Messages"),
        ("02", ["Your Approval"], "We print your mug once you approve the preview"),
        ("03", ["Made to Order"], "Printed on both sides, glossy white ceramic, white inside"),
        ("04", ["Easy Care"], "Dishwasher safe and microwave safe")],
        "Original zodiac fusion symbols designed by AstroLoveArt", surec=True)
    return im, dict(o, kirpim=dict(tek_on=ko)), kut


def k04(sd):
    sh = [(ad, *sahne(sd, f"stil_{st}")) for st, ad in ST8]
    s = K04_KUPA_H / max(p.height for _, p, _ in sh)               # 8 kupa ayni olcek
    IZ = 150; hw = (W - 2 * IZ) / 4
    im, o, kut = S.izgara_kart("Choose Your Style", [(ad, p) for ad, p, _ in sh], "Every style in 11 oz and 15 oz", (4, 4),
                               lambda r, j, n: IZ + hw * (j + 0.5), 40, 110,
                               lambda og: [(round(g.width * s), round(g.height * s)) for _, g in og])
    return im, dict(o, olcek=round(s, 4), kirpim={ad: k for ad, _, k in sh}), kut


def k05(sd):
    oz = (("tek_on", "11 oz", ["9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml"]), ("m15", "15 oz", ["11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml"]))
    sh = [sahne(sd, ad) for ad, _, _ in oz]
    s = K05_15_H / sh[1][0].height                                   # iki kupa ayni olcekte (gercek oran)
    g = [(p.resize((round(p.width * s), round(p.height * s)), Image.LANCZOS) if s < 1 else None) for p, _ in sh]
    if any(x is None for x in g):
        raise SystemExit("DUR: K05 buyutme gerekiyor")
    kay = S.Kayit(); im = K.tuval()
    D = max(x.width for x in g) + 220; gh = max(x.height for x in g)
    yb = K.ETIKET["boy"] + K05_ET + K.blok_yuk(K.METIN, 3)
    top = gh + K05_ARA + yb; y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
    cx = [W / 2 - D / 2, W / 2 + D / 2]; kut = []
    yar = [max(x.width, K.genislik(K.METIN, oz[i][2][0])) / 2 for i, x in enumerate(g)]   # grup (kupa + yazi) ortali, merkez araligi D
    dx = (W - (cx[0] - yar[0]) - (cx[1] + yar[1])) / 2; cx = [x + dx for x in cx]
    for i, (x, c) in enumerate(zip(g, cx)):
        xx, yy = round(c - x.width / 2), round(y0 + gh - x.height)       # kirpim kutusu tabanlari ayni cizgide
        im.paste(x, (xx, yy)); kut.append([xx, yy, xx + x.width, yy + x.height]); kay.ekle(f"kupa{i}", kut[-1])
    d = ImageDraw.Draw(im)
    kay.blok("baslik"); K.baslik(d, "Two Sizes")
    alt_y = 0
    for i, ((_, e, ls), c) in enumerate(zip(oz, cx)):
        kay.blok(f"kupa{i}")
        y = y0 + gh + K05_ARA
        y += K.yaz(d, K.ETIKET, [e], c, y, "center", 700) + K05_ET
        alt_y = max(alt_y, y + K.yaz(d, K.METIN, ls, c, y, "center", 700))
    if K.NOT_Y - alt_y < K05_NOT_ARA:
        raise SystemExit(f"DUR: K05 yazi - alt not {K.NOT_Y - alt_y:.0f} < {K05_NOT_ARA} px")
    kay.blok("not"); K.yaz(d, K.NOT, ["Height x diameter, approximate size comparison"], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    kay.gruplar = [["kupa0", "kupa1"]]
    o = dict(olcek=round(s, 4), gorsel=[[x.width, x.height] for x in g], merkez_arasi=D, yazi_not_arasi=round(K.NOT_Y - alt_y),
             kirpim=dict(tek_on=sh[0][1], m15=sh[1][1]))
    o["yerlesim"] = S.yerlesim_kapisi(kay, "Two Sizes")
    return im, o, kut


def kopuk_ton(im, kutular, esik=3, bag=1):
    """fotograf kutusu icinde zeminden (#F5F0E7) esik'ten fazla farkli piksellerden, kutunun en buyuk (kupa + golge) parcasina bagli
    OLMAYANLAR (kopuk leke / ton farki / panel kalintisi). Baglanti fark > bag ile kurulur. -> (kopuk piksel sayisi, parcalar)"""
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


def zemin_kenar(im, kutular, serit=2):
    """fotograf kutularinin ic kenar seritlerinde (serit px) #F5F0E7'den farkin MEDYANI, en buyuk deger (panel / kutu kenari kapisi).
    Kirpim payi 4 px (Merkez 28 Eki) oldugundan kupa / golge kenara yerel olarak degebilir; panel kenari tum serit boyunca fark verir."""
    a = np.asarray(im.convert("RGB")).astype(np.float32); z = np.float32(K.rgb(K.ZEMIN)); m = 0.0
    for x0, y0, x1, y1 in kutular:
        p = a[y0:y1, x0:x1]
        for sr in (p[:serit], p[-serit:], p[:, :serit], p[:, -serit:]):
            m = max(m, float(np.median(np.abs(sr - z).max(axis=-1))))
    return m


def beklenen(a, b):
    sem = lambda alt: ["Two Signs, One Shared Symbol", f"{a} and {b} joined in an original AstroLoveArt design", a, b, alt]
    return {
        "S1_SEMBOL": sem("Personalized with your two names and your message"),
        "S2_KISISEL": ["Your Names, Your Message", f"Name Under {a}", f"Name Under {b}",
                       "Up to 11 letters each, English letters, printed in capitals", "Your Message",
                       "Up to 35 characters, printed as you type it, no emoji", "Please check your spelling before you order"],
        "S3_FORMAT": ["Digital File or Print", "Digital File", "One print ready digital file in the color and size you choose",
                      "Nothing is shipped", "Print", "Unframed print on matte art paper", "Free shipping worldwide", "14 Sizes", BOYLAR,
                      "Every size as a print or a digital file"],
        "S4_SUREC": ["Made for You, Step by Step",
                     "01", "Your Preview", "For every order, we send a preview via Etsy Messages within 24 hours of your order",
                     "02", "Your Approval", "We make your print or file once you approve, or as shown if there is no reply within 24 hours of the preview",
                     "03", "Made to Order", "Printed on matte art paper, gold tones are printed color, not metallic foil",
                     "04", "Free Shipping", "Free shipping worldwide, see the listing for your delivery estimate",
                     "Digital files are checked by hand before sending"],
        "S5_GENEL": ["Choose Your Color"] + [ad for ad, _ in RENKLER] + ["Every color as a print or a digital file"],
        "K02_SEMBOL": sem("Personalized with your two names and your message"),
        "K03_KISISEL": ["Your Names, Your Message", f"Name Under {a}", f"Name Under {b}", "Up to 10 letters each, printed in capitals on the front",
                        "Your Message", "Up to 30 characters, printed on the back with your names",
                        "One Mug, Two Sides", "Front with your symbol and names, back with your message",
                        "Please check your spelling before you order"],
        "K04_STIL": ["Choose Your Style"] + [ad for _, ad in ST8] + ["Every style in 11 oz and 15 oz"],
        "K05_BOYUT": ["Two Sizes", "11 oz", "9.6 x 8.2 cm", "3.8 x 3.2 in", "325 ml", "15 oz", "11.9 x 8.5 cm", "4.7 x 3.3 in", "444 ml",
                      "Height x diameter, approximate size comparison"],
        "K07_SUREC": ["Made for You, Step by Step",
                      "01", "Your Preview", "For every order, we send a preview of your mug via Etsy Messages",
                      "02", "Your Approval", "We print your mug once you approve the preview",
                      "03", "Made to Order", "Printed on both sides, glossy white ceramic, white inside",
                      "04", "Easy Care", "Dishwasher safe and microwave safe",
                      "Original zodiac fusion symbols designed by AstroLoveArt"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--cift", "--a", "--b", "--sembol", "--poster", "--mb45", "--poster-kaynak", "--sahne", "--out"):
        ap.add_argument(k, required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); sem = Path(a.sembol); sd = Path(a.sahne); pk_d = Path(a.poster_kaynak)
    gerek = [sd / f"z_{ad}.png" for ad in SAHNELER]
    eksik = [p.name for p in gerek if not p.exists()]
    if eksik:
        raise SystemExit(f"DUR: sahne dosyalari eksik: {eksik}")
    renk_yol = [(ad, Path(a.mb45) if f is None else pk_d / f) for ad, f in RENKLER]
    renkler = [(ad, Image.open(p).convert("RGB")) for ad, p in renk_yol]
    ci = dict(renkler)["Champagne Ivory"]
    c = a.cift
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()
    yok = lambda f: (lambda: (*f(), ()))                               # renk muafiyeti olmayan kartlar
    islem = [(f"WA_{c}_S1_SEMBOL.jpg", "S1_SEMBOL", lambda: S.sembol_kart(a.a, a.b, sem, "Personalized with your two names and your message")),
             (f"WA_{c}_S2_KISISEL.jpg", "S2_KISISEL", yok(lambda: wa_s2(a.a, a.b, Image.open(a.poster)))),
             ("WA_ORTAK_S3_FORMAT.jpg", "S3_FORMAT", yok(wa_s3)),
             (f"WA_{c}_S4_SUREC.jpg", "S4_SUREC", yok(lambda: wa_s4(ci))),
             (f"WA_{c}_S5_GENEL.jpg", "S5_GENEL", yok(lambda: wa_s5(renkler))),
             (f"KUPA_{c}_K02_SEMBOL.jpg", "K02_SEMBOL", lambda: S.sembol_kart(a.a, a.b, sem, "Personalized with your two names and your message")),
             (f"KUPA_{c}_K03_KISISEL.jpg", "K03_KISISEL", yok(lambda: k03(a.a, a.b, sd))),
             (f"KUPA_{c}_K05_BOYUT.jpg", "K05_BOYUT", yok(lambda: k05(sd))),
             (f"KUPA_{c}_K07_SUREC.jpg", "K07_SUREC", yok(lambda: k07(sd))),
             (f"KUPA_{c}_K04_STIL.jpg", "K04_STIL", yok(lambda: k04(sd)))]           # galeri sirasi (kupa: 2, 3, 4, 5, 6)
    bek = beklenen(a.a, a.b); sonuc, rapor, jb = {}, {}, {}
    for ad, anah, fn in islem:
        n0, n1 = len(K.YAZILAR), len(K.SATIRLAR)
        im, o, pk, muaf = fn()
        yazi, sat = K.YAZILAR[n0:], K.SATIRLAR[n1:]
        kotu = [t for t in yazi if YASAK.search(t) or K.YASAK_SOZ.search(t)]
        if kotu:
            raise SystemExit(f"DUR: {ad} yasak karakter / sozcuk: {kotu}")
        for tur, t in sat:
            if tur in ("baslik", "etiket") and not title_ok(t) and not t.isdigit():
                raise SystemExit(f"DUR: {ad} {tur} satiri Title Case degil: {t!r}")
        g, e = " ".join(yazi).split(), " ".join(bek[anah]).split()
        if [x.casefold() for x in g] != [x.casefold() for x in e]:
            raise SystemExit(f"DUR: {ad} metni beklenenden farkli\n cizilen: {' '.join(g)}\n beklenen: {' '.join(e)}")
        sap = K.renk_kapisi(im, pk, muaf=muaf)
        if sap:
            raise SystemExit(f"DUR: {ad} renk kapisi (cizim) {sap}")
        jb[ad] = K.jpeg_bayt(im)
        sapj = K.renk_kapisi(Image.open(io.BytesIO(jb[ad])), pk, jpeg=True, muaf=muaf)
        if sapj:
            raise SystemExit(f"DUR: {ad} renk kapisi (JPEG) {sapj}")
        zk = kp = kl = None
        if ad.startswith("KUPA_") and pk:                    # ZEMIN KAPISI: fotograf kutusu kenar seritleri kart zeminine esit (panel yok)
            zk = S_zk = zemin_kenar(im, pk); kp, kl = kopuk_ton(im, pk)
            if S_zk > ZEMIN_ESIK:
                raise SystemExit(f"DUR: {ad} fotograf kenari zeminden farkli (medyan {zk:.1f} > {ZEMIN_ESIK})")
            if kp:
                raise SystemExit(f"DUR: {ad} fotograf kutusunda kupadan kopuk zemin disi ton {kp} px {kl[:5]}")
        sonuc[ad] = im; rapor[ad] = dict(o, renk_kapisi="PASS (cizim + JPEG)", foto_kutu=pk, zemin_kenar_medyan_max=zk, kopuk_ton_px=kp,
                                         yazi=yazi, kb=round(len(jb[ad]) / 1024))
    for ad, b in jb.items():
        (out / ad).write_bytes(b)
    girdi = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [Path(a.poster), *(p for _, p in renk_yol), *(sem / f"{x}.png" for x in ("sol", "sag", "ana")), *gerek]}
    (out / "KART_OZET_WA_KUPA.json").write_text(json.dumps(dict(cift=c, kartlar=rapor, girdi_sha256=girdi, surum=K.SURUM, tuval=[W, H]),
                                                           indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"KART WA + KUPA: {len(sonuc)} kart PASS (metin, Title Case, yasak, renk, yerlesim, zemin) -> {out}")
    return 0


if __name__ == "__main__":
    import wa_kupa_kart_ornek as _M                  # tek modul nesnesi (yd_kart_ornek / kart_sablon ile ayni K)
    sys.exit(_M.main())
