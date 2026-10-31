#!/usr/bin/env python3
"""SADE kupa bilgi kartlari (tek burc; Serdar 31 Eki is 9; ornek CANCER, EMILY / "My favorite place is with you"). ETSY YOK, toplu uretim yok.
Cift kartlariyla AYNI sira ve stil (galeri 2 K02, 3 K03, 4 K05, 5 K07, 6 K04; 3000x2250): cizim, kapilar (metin, Title Case, yasak karakter,
renk, yerlesim, zemin, kopuk ton) wa_kupa_kart_ornek.kart_isle + kart_sablon AYNEN (zemin / kopuk ton kapisi SADE_ adlarinda da kosar,
inceleme 31 Eki); K05 ve K04 cift kartlarinin fonksiyonlari (metin ayni).
Degisen yalniz: K02 tek burc sembol karti (iki burc + baglac yerine tek buyuk sembol + burc adi), K03 / K07 metinleri (SADE12_METIN.csv
CANCER aciklamasi ve kisisellestirme talimati ile ayni bilgi), sahneler sade baskiyla.
Sahne (mod sahne, _v12 ortami = orchard_gorunum ile ayni surumler + simd_sabit kapisi, Serdar 31 Eki 8a):
  baski  : v2 (Serdar 31 Eki) kupa-orchard dc4a432 kod/baski_kes_sade.py (sade12.sh ile ayni arguman: kes/<STIL>R, glif, on yazi, mesaj, renk)
  gorunum: temiz/kupa-orchard 0196e37a kod/kapak_canva3.py, orchard_gorunum ile ayni sahneler / geo / ortam (GOLGE_US 0.4, PARLA 0.7):
           tek_on, tek_arka (Orange Blossom baskisi), m15 (sahne15, D_IN 3.35, gercek BOY=15 baski satir 45:1095), stil_<st> (tek on)
  zemin  : kupa_zemin.py (kart ortami) -> z_<ad>.png
Kullanim: sade_kart.py sahne --ko <0196e37a kupa_orchard> --kos <dc4a432 kupa_orchard (v2)> --glif <sol.png> --on EMILY --mesaj ... --out <dir>
          sade_kart.py kart --burc Cancer --glif <sol.png> --gorunum <sahne/gorunum> --sahne <z_*.png dir> --out <dir>"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# v2 (Serdar 31 Eki, kupa-orchard dc4a432 sade12.sh STIL tablosu): kisa ad -> (kes klasoru, baski rengi). v1 (baski_sade3) GECERSIZ.
SADE_V2 = {"orange": ("ORANGER", "67,87,42"), "fig": ("FIGR", "126,43,113"), "olive": ("OLIVER", "78,84,30"),
           "pomegranate": ("POMEGRANATER", "139,46,60"), "almond": ("ALMONDR", "112,58,72"), "lemon": ("LEMONR", "93,76,31"),
           "grape": ("GRAPER", "72,59,172"), "loquat": ("LOQUATR", "105,69,35")}
SADE_RENK = {k: v[1] for k, v in SADE_V2.items()}
# K02 sembol kutusu (inceleme 31 Eki): en / boy = v2 baski kutusu (dc4a432 varlik/kes/<STIL>R_kes.json yerlesim sembol_w / sembol_h
# = 136 / 127, 8 stilde ayni; v1 baski_sade3 44 / 33,5 GECERSIZ). Cizgi baskidaki gibi KALIN 1,24 ile kalinlastirilir (baski_kes_sade.py
# sembol_yap: dis kenar r = (KALIN - 1) x cizgi / 2). Kutu yuksekligi 430: 12 glifin hepsinde en kalin cizgi <= 56 px (renk kapisi 61x61)
# olan en buyuk deger (olcum 31 Eki: 430 -> ARIES 55 px, 440 -> 59 px). Cizgi / en (DIST_C): K02 CANCER 0,100, baski 0,103-0,109.
K02_KUTU_H, K02_KUTU_ORAN, K02_KALIN = 430, 136 / 127, 1.24
SAHNE_AD = ("tek_on", "tek_arka", "m15") + tuple(f"stil_{s}" for s in SADE_RENK)


def sahne(a):
    import simd_sabit
    py = sys.executable
    env = {"GOLGE_US": "0.4", "PARLA": "0.7", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    simd_sabit.ayarla(env, py); simd_sabit.kapi(py, env, "sade_kart sahne")
    out = Path(a.out).resolve(); (out / "baski").mkdir(parents=True, exist_ok=True); (out / "gorunum").mkdir(exist_ok=True)
    kos, ko = Path(a.kos).resolve(), Path(a.ko).resolve()
    V = ko / "varlik" / "gorunum"

    def calis(arg, e, cwd):
        r = subprocess.run(arg, capture_output=True, text=True, env=e, cwd=cwd)
        if r.returncode:
            print(r.stdout[-800:], r.stderr[-1500:])
            raise SystemExit("DUR: " + " ".join(str(x) for x in arg[:3]))

    for st, (kes, rgb) in SADE_V2.items():          # v2: baski_kes_sade.py (canli Orchard dallari, tek sembol + isim; arka nazar + mesaj)
        calis([py, "-I", str(kos / "kod" / "baski_kes_sade.py"), str(kos / "varlik" / "kes" / kes), str(Path(a.glif).resolve()),
               a.on, a.mesaj, rgb, str(out / "baski" / f"S_{st}")], dict(env), kos / "kod")
    bo = out / "baski" / "S_orange_baski_11oz.png"

    def giydir(s, b, g, c, d_in=None):
        e = dict(env)
        if d_in:
            e["D_IN"] = d_in
        calis([py, "-I", str(ko / "kod" / "kapak_canva3.py"), str(s), str(b), str(g), str(c)], e, ko / "kod")

    G = out / "gorunum"
    for y in ("tek_on", "tek_arka"):
        giydir(V / f"ORCHARD_OrangeBlossom_sahne_{y}.png", bo, V / f"geo_{y}.json", G / f"{y}.jpg")
    # 15 oz (inceleme 31 Eki): gercek BOY=15 baski (2700x1140, cizim dikeyde ortali) satir 45:1095 kesilir -> 2700x1050 (kapak_canva3
    # FH 1050 sabit), D_IN 3.35 ile giydirilir; 11 oz baskiyi 15 oz capina giydirmek on yuzu ~23 px kaydiriyordu.
    e15 = dict(env); e15["BOY"] = "15"
    calis([py, "-I", str(kos / "kod" / "baski_kes_sade.py"), str(kos / "varlik" / "kes" / SADE_V2["orange"][0]), str(Path(a.glif).resolve()),
           a.on, a.mesaj, SADE_V2["orange"][1], str(out / "baski" / "S15_orange")], e15, kos / "kod")
    from PIL import Image
    b15 = Image.open(out / "baski" / "S15_orange_baski_15oz.png")
    if b15.size != (2700, 1140):
        raise SystemExit(f"DUR: 15 oz baski boyutu {b15.size}")
    b15.crop((0, 45, 2700, 1095)).save(out / "baski" / "S15_orange_kesim_1050.png")
    giydir(V / "sahne15.png", out / "baski" / "S15_orange_kesim_1050.png", V / "geo15.json", G / "m15.jpg", d_in="3.35")
    for st in SADE_RENK:
        giydir(V / "ORCHARD_OrangeBlossom_sahne_tek_on.png", out / "baski" / f"S_{st}_baski_11oz.png", V / "geo_tek_on.json", G / f"stil_{st}.jpg")
    print("sahne tamam", sorted(p.name for p in G.iterdir()), flush=True)
    return 0


def k02_glif(yol, rgb):
    """K02 sembolu: glif K02_KUTU_H x K02_KUTU_ORAN kutusuna sigar (baski_kes_sade olcek), cizgi K02_KALIN ile kalinlasir (baski_kes_sade
    sembol_yap ile ayni formul; EDT opencv DIST_L2 PRECISE), sonra kart_sablon.maske ile ayni keskinlestirme (alfa 0,2-0,8) -> RGBA."""
    import cv2
    import numpy as np
    from PIL import Image
    edt = lambda m: cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    a = Image.open(yol).convert("RGBA").getchannel("A"); a = a.crop(a.getbbox())
    k = min(K02_KUTU_H * K02_KUTU_ORAN / a.width, K02_KUTU_H / a.height)
    a = np.asarray(a.resize((max(1, round(a.width * k)), max(1, round(a.height * k))), Image.LANCZOS)).astype(np.float32) / 255
    r = max(0.0, (K02_KALIN - 1) * 2 * float(edt(a > 0.5).max()) / 2)
    p = int(np.ceil(r)) + 2
    a = np.pad(a, p)
    a = np.clip(np.maximum(a, 1 - (edt(a < 0.5) - r)), 0, 1)
    ys, xs = np.where(a > 0.02)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    al = np.clip((a - 0.2) / 0.6, 0, 1)
    rgba = np.zeros(al.shape + (4,), np.uint8); rgba[..., :3] = rgb; rgba[..., 3] = (al * 255).astype(np.uint8)   # kart_sablon.maske ile ayni (kesme)
    return Image.fromarray(rgba)


# ---------------------------------------------------------------- kartlar (kart ortami: pillow 11.0.0, numpy 2.1.3)
def kart(a):
    import simd_sabit                                                 # Serdar 31 Eki 8a: numpy yuklenmeden once
    if "numpy" in sys.modules:
        raise SystemExit("DUR: numpy SIMD ayarindan once yuklenmis")
    simd_sabit.ayarla(os.environ); simd_sabit.kapi(sys.executable, dict(os.environ), "sade_kart kart")
    from PIL import Image, ImageDraw
    import cv2  # noqa: F401
    import kupa_kart78 as K78
    import wa_kupa_kart_ornek as Wk
    simd_sabit.surec_ici("sade_kart kart")
    K, S = Wk.K, Wk.S
    W = K.W
    b = a.burc
    glif = Path(a.glif)
    sd = Path(a.sahne)
    if a.gorunum:                                                     # zemin esitleme (kupa_kart78.zemin = kupa_zemin._isle, ayni 11 sahne adi)
        K78.zemin(a.gorunum, sd)
    eksik = [f"z_{x}.png" for x in SAHNE_AD if not (sd / f"z_{x}.png").exists()]
    if eksik:
        raise SystemExit(f"DUR: sahne eksik {eksik}")

    def k02():
        kay = S.Kayit(); im = K.tuval(); d = ImageDraw.Draw(im)
        kay.blok("baslik"); K.baslik(d, "Your Zodiac Sign")
        ay = K.BASLIK_Y + K.BASLIK["boy"] + 50
        kay.blok("alt_baslik"); K.yaz(d, K.METIN, [f"The {b} symbol, designed by AstroLoveArt"], W / 2, ay, "center", W - 2 * K.KENAR)
        ust = ay + K.METIN["boy"] + 160                                   # alt baslik ile sembol arasi (cift kartinda glif ust bosluguna yakin)
        et_y = K.NOT_Y - 160 - K.ETIKET["boy"]                            # burc adi alt nottan 160 px yukarida
        # 12 burcta AYNI kutu, baskidaki oran ve kalinlik (K02_* aciklamasi). Asilirsa DUR (sessiz kucultme yok).
        import cv2
        import numpy as np
        g = k02_glif(glif, K.rgb(K.MUREKKEP))
        gh = g.height
        c = (np.asarray(g.getchannel("A")) > 153).astype(np.uint8)
        kal = float(cv2.distanceTransform(c, cv2.DIST_C, 3).max()) * 2 - 1
        if kal > 56:
            raise SystemExit(f"DUR: K02 {b} sembol cizgisi {kal} px > 56 (renk kapisi 61x61); K02_KUTU_H yeniden olculmeli")
        ust = ust + (round(et_y - 60 - ust) - gh) / 2                      # sembol alanda dikeyde ortali
        x = round(W / 2 - g.width / 2); im.paste(g, (x, round(ust)), g)
        kay.ekle("sembol", [x, round(ust), x + g.width, round(ust) + g.height])
        d = ImageDraw.Draw(im)
        kay.blok("burc"); K.yaz(d, K.ETIKET, [b], W / 2, et_y, "center", 0.3 * W)
        kay.blok("not"); K.yaz(d, K.METIN, ["Personalized with a name or a date and your message"], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
        kay.gruplar = [["sembol"]]
        o = dict(sembol=[g.width, g.height], en_kalin_cizgi_px=kal)
        o["yerlesim"] = S.yerlesim_kapisi(kay, "sade sembol")
        return im, o, [], ()

    def k03():
        (on, ko_), (ar, ka) = Wk.sahne(sd, "tek_on"), Wk.sahne(sd, "tek_arka")
        im, o, kut = S.yan_kart("Your Name, Your Message", [on, ar], [
            (None, ["Name or Date"], "Up to 12 characters, printed in capitals on the front"),
            (None, ["Your Message"], "Up to 30 characters, required, printed on the back as you type it"),
            (None, ["One Mug, Two Sides"], f"Front with the {b} symbol and your name or date, back with an evil eye bead and your message")],
            "Please check your spelling before you order")
        return im, dict(o, kirpim=dict(tek_on=ko_, tek_arka=ka)), kut

    def k07():
        on, ko_ = Wk.sahne(sd, "tek_on")
        im, o, kut = S.yan_kart("Made for You, Step by Step", [on], [
            ("01", ["Your Preview"], "For every order, we send a preview of your mug via Etsy Messages"),
            ("02", ["Your Approval"], "We print your mug once you approve the preview"),
            ("03", ["Made to Order"], "Printed on both sides, glossy white ceramic, white inside"),
            ("04", ["Easy Care"], "Dishwasher safe and microwave safe")],
            "Zodiac symbol designed by AstroLoveArt", surec=True)
        return im, dict(o, kirpim=dict(tek_on=ko_)), kut

    bek = dict(Wk.beklenen(b, b))
    bek["K02_SEMBOL"] = ["Your Zodiac Sign", f"The {b} symbol, designed by AstroLoveArt", b,
                         "Personalized with a name or a date and your message"]
    bek["K03_KISISEL"] = ["Your Name, Your Message", "Name or Date", "Up to 12 characters, printed in capitals on the front",
                          "Your Message", "Up to 30 characters, required, printed on the back as you type it",
                          "One Mug, Two Sides", f"Front with the {b} symbol and your name or date, back with an evil eye bead and your message",
                          "Please check your spelling before you order"]
    bek["K07_SUREC"] = bek["K07_SUREC"][:-1] + ["Zodiac symbol designed by AstroLoveArt"]
    yok = lambda f: (lambda: (*f(), ()))
    c = b.upper()
    islem = [(f"SADE_{c}_K02_SEMBOL.jpg", "K02_SEMBOL", k02),
             (f"SADE_{c}_K03_KISISEL.jpg", "K03_KISISEL", yok(k03)),
             (f"SADE_{c}_K05_BOYUT.jpg", "K05_BOYUT", yok(lambda: Wk.k05(sd))),
             (f"SADE_{c}_K07_SUREC.jpg", "K07_SUREC", yok(k07)),
             (f"SADE_{c}_K04_STIL.jpg", "K04_STIL", yok(lambda: Wk.k04(sd)))]      # galeri sirasi 2, 3, 4, 5, 6 (cift kartlariyla ayni)
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()
    sonuc, rapor, jb = Wk.kart_isle(islem, bek)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for ad, by in jb.items():
        (out / ad).write_bytes(by)
    girdi = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [glif, *(sd / f"z_{x}.png" for x in SAHNE_AD)]}
    (out / f"KART_OZET_SADE_{c}.json").write_text(json.dumps(dict(burc=b, galeri_sira={ad: i + 2 for i, (ad, _, _) in enumerate(islem)},
                                                                  kartlar=rapor, girdi_sha256=girdi, surum=K.SURUM, tuval=[W, K.H]),
                                                             indent=1, ensure_ascii=False), encoding="utf-8")
    ims = [Image.open(out / ad) for ad, _, _ in islem]
    kt = Image.new("RGB", (3 * 1000 + 40, 2 * 750 + 30), (230, 230, 230))
    for i, im in enumerate(ims):
        kt.paste(im.resize((1000, 750), Image.LANCZOS), (10 + (i % 3) * 1010, 10 + (i // 3) * 760))
    kt.save(out / f"KONTAK_SADE_{c}.jpg", quality=88)
    print(f"SADE KART {c}: {len(sonuc)} kart PASS -> {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="mod", required=True)
    s = sp.add_parser("sahne")
    for k in ("--ko", "--kos", "--glif", "--on", "--mesaj", "--out"):
        s.add_argument(k, required=True)
    k = sp.add_parser("kart")
    for x in ("--burc", "--glif", "--sahne", "--out"):
        k.add_argument(x, required=True)
    k.add_argument("--gorunum", default="", help="sahne modunun gorunum/ klasoru: once kupa_zemin ile z_*.png uretilir (--sahne'ye)")
    a = ap.parse_args(argv)
    return sahne(a) if a.mod == "sahne" else kart(a)


if __name__ == "__main__":
    import sade_kart as _M
    sys.exit(_M.main())
