#!/usr/bin/env python3
"""Bizim Yilimiz musteri dosyasi (14 Eki 2026, Serdar onayi). Akis ELLE baslatilir; Etsy'ye yazma ve musteriye gonderim YOK.
Girdi (env): TUR (ONIZLEME | NIHAI), SIPARIS_NO (NIHAI: yalniz rakam; ONIZLEME: bos), PAIR, NAME1, NAME2, DATE, HEADING,
LINE (bos = YEAR ONE), STYLE (1..5), FORMAT (poster | kart | ikisi), KOD (bizim-yilimiz-v3 kopyasi), CIKTI (klasor),
BOY (yeni yapi, Serdar 31 Eki 2a: 14 boydan biri; verilirse FORMAT poster, dosya by_boy.py aile sayfasindan, 300 dpi).
Ön kontrol: PAIR alfabetik + kaynak alfa var; isim/tarih/satir BUYUK harf; isim <= 11, tarih/satir <= 20 karakter;
uzun/orta tire yok; her harf stilin fontlarinda var (yoksa FAIL, dosya uretilmez).
NIHAI  : tam dosya 8x10 2400x3000 / 5x7 1500x2100, 300 dpi -> AstroLoveArt_<Burc1>_<Burc2>_<Stil>_<8x10|5x7>.jpg
ONIZLEME: uzun kenar 1000 px, ortada "AstroLoveArt PREVIEW" filigrani -> ..._PREVIEW.jpg (tam dosya Drive'a GITMEZ).
Cikti: CIKTI/<klasor>/ + KONTROL.json; klasor adi CIKTI/KLASOR.txt (siparis_no ya da ONIZLEME_<YYYYMMDD>_<ISIM1>_<ISIM2>).
Son satir: KONTROL PASS | KONTROL FAIL (cikis kodu 1)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_boy as BB  # noqa: E402  14 boy (Serdar 31 Eki 2a)

BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN",
           "AQUARIUS", "PISCES"]
STIL = {"1": "1_Starlit", "2": "2_Timeless", "3": "3_FirstPage", "4": "4_Layers", "5": "5_Botanical"}
# musteri metninin (isim/tarih/satir) basildigi fontlar, poster + kart (kod/by_poster.py, kod/by_kart.py)
FONT = {"1": ["Cinzel.ttf"], "2": ["Cinzel.ttf"],
        "3": ["cormorant-garamond-latinext-700-normal.ttf", "Cinzel.ttf"],
        "4": ["montserrat-latinext-600-normal.ttf"],
        "5": ["cormorant-garamond-latinext-700-normal.ttf", "Cinzel.ttf"]}
OLCU = {"8x10": (2400, 3000), "5x7": (1500, 2100)}   # eski yol (by_poster 8x10 / by_kart 5x7)
ONIZLEME_UZUN = 1000


def ascii_ad(s):
    s = s.replace("ı", "i").replace("İ", "I")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")


def girdiler(hata):
    e = lambda k, d="": " ".join(os.environ.get(k, d).split())
    g = {"tur": e("TUR").upper(), "siparis_no": e("SIPARIS_NO"), "pair": e("PAIR").upper().replace(" ", "_"),
         "name1": e("NAME1").upper(), "name2": e("NAME2").upper(), "date": e("DATE").upper(),
         "heading": e("HEADING", "Paper Anniversary"), "line": e("LINE").upper() or "YEAR ONE",
         "style": e("STYLE"), "format": e("FORMAT").lower(), "boy": e("BOY")}
    if g["tur"] not in ("ONIZLEME", "NIHAI"):
        hata.append(f"tur ONIZLEME ya da NIHAI olmali: {g['tur']!r}")
    if g["tur"] == "NIHAI" and not g["siparis_no"].isdigit():
        hata.append("NIHAI icin siparis_no yalniz rakam olmali")
    if g["tur"] == "ONIZLEME" and g["siparis_no"]:
        hata.append("ONIZLEME'de siparis_no bos olmali")
    b = g["pair"].split("_")
    if len(b) != 2 or not all(x in BURCLAR for x in b):
        hata.append(f"pair iki burc olmali (orn. CANCER_LIBRA): {g['pair']!r}")
    elif b != sorted(b):
        hata.append(f"pair alfabetik olmali: {'_'.join(sorted(b))} (name1 = {sorted(b)[0]} burcunun ismi, solda)")
    for k, sinir in (("name1", 11), ("name2", 11), ("date", 20), ("line", 20)):
        if not g[k]:
            hata.append(f"{k} bos")
        elif len(g[k]) > sinir:
            hata.append(f"{k} en fazla {sinir} karakter ({len(g[k])})")
        if "—" in g[k] or "–" in g[k]:
            hata.append(f"{k}: uzun/orta tire yok")
    if g["heading"] not in ("Paper Anniversary", "Our First Year"):
        hata.append(f"heading 'Paper Anniversary' ya da 'Our First Year': {g['heading']!r}")
    if g["style"] not in STIL:
        hata.append(f"style 1..5: {g['style']!r}")
    if g["format"] not in ("poster", "kart", "ikisi"):
        hata.append(f"format poster | kart | ikisi: {g['format']!r}")
    if g["boy"] and g["boy"] not in BB.BOY:   # Serdar 31 Eki 2a: yeni yapi 14 boy (Digital File ve Print ayni dosya)
        hata.append(f"boy 14 boydan biri olmali ({', '.join(BB.BOY)}): {g['boy']!r}")
    if g["boy"] and g["format"] != "poster":
        hata.append("boy verildiginde format poster olmali (yeni yapida kart yok)")
    return g


def glif_kontrol(g, kod, hata):
    from fontTools.ttLib import TTFont
    metin = set((g["name1"] + g["name2"] + g["date"] + g["line"]).replace(" ", ""))
    for f in FONT.get(g["style"], []):
        cmap = TTFont(kod / "fonts" / f).getBestCmap()
        eksik = sorted(c for c in metin if ord(c) not in cmap)
        if eksik:
            hata.append(f"font {f} su harfleri basamaz: {' '.join(eksik)}")


def filigran(src, dst, font_yol):
    im = Image.open(src).convert("RGB")
    k = ONIZLEME_UZUN / max(im.size)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    kat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    yazi = "AstroLoveArt PREVIEW"
    boy = 60
    for _ in range(4):                                  # yazi genisligi gorselin %62'si
        f = ImageFont.truetype(str(font_yol), boy)
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
        w = d.textlength(yazi, font=f)
        boy = max(10, round(boy * 0.62 * im.width / w))
    f = ImageFont.truetype(str(font_yol), boy)
    try:
        f.set_variation_by_axes([700])
    except Exception:
        pass
    x0, y0, x1, y1 = d.textbbox((0, 0), yazi, font=f, stroke_width=2)
    x, y = (im.width - (x1 - x0)) / 2 - x0, (im.height - (y1 - y0)) / 2 - y0
    d.text((x, y), yazi, font=f, fill=(255, 255, 255, 120), stroke_width=2, stroke_fill=(40, 30, 25, 90))
    out = Image.alpha_composite(im.convert("RGBA"), kat).convert("RGB")
    out.save(dst, quality=88, dpi=(72, 72))


def main():
    t0 = time.time()
    hata = []
    g = girdiler(hata)
    kod, cikti = Path(os.environ["KOD"]).resolve(), Path(os.environ["CIKTI"]).resolve()
    if not hata:
        if not (kod / "kaynak" / "ana" / f"{g['pair'].lower()}_alfa.png").exists():
            hata.append(f"kaynak alfa yok: kaynak/ana/{g['pair'].lower()}_alfa.png")
        glif_kontrol(g, kod, hata)
    print("GIRDI tur={tur} siparis_no={siparis_no} pair={pair} heading={heading!r} style={style} format={format}".format(**g))
    if hata:
        for h in hata:
            print("ONKONTROL FAIL:", h)
        print("KONTROL FAIL")
        sys.exit(1)
    print("ONKONTROL PASS (pair alfabetik, alfa var, BUYUK harf, uzunluk, glif)")

    stil = STIL[g["style"]]
    b1, b2 = (x.capitalize() for x in g["pair"].split("_"))
    stil_ad = stil.split("_", 1)[1]
    klasor = g["siparis_no"] if g["tur"] == "NIHAI" else \
        f"ONIZLEME_{datetime.now(timezone.utc):%Y%m%d}_{ascii_ad(g['name1'])}_{ascii_ad(g['name2'])}"
    hedef = cikti / klasor
    hedef.mkdir(parents=True, exist_ok=True)
    (cikti / "KLASOR.txt").write_text(klasor + "\n", encoding="utf-8")
    env = dict(os.environ, BY_ROOT=str(kod), PAIR=g["pair"], NAME1=g["name1"], NAME2=g["name2"], DATE=g["date"],
               HEADING=g["heading"], LINE=g["line"], STYLE=g["style"])
    isler = [("poster", "by_poster.py", "8x10"), ("kart", "by_kart.py", "5x7")]
    isler = [i for i in isler if g["format"] in (i[0], "ikisi")]
    if g["boy"]:   # yeni yapi: tek boy, aile sayfasi (by_boy.py; 24 inc genislige kadar SCALE 2)
        isler = [("poster", "by_boy", g["boy"])]
    tmp = Path(tempfile.mkdtemp(prefix="by_"))
    dosyalar = []
    for tur, betik, boy in isler:
        if betik == "by_boy":
            aile = BB.BOY_AILE[boy]
            sayfa = BB.aile_sayfasi(kod, aile, dict(env, SCALE="2"), tmp)
            br = BB.boy_dosyasi(sayfa, aile, boy, tmp / f"{stil}_{boy}.jpg")
            print(f"BOY {boy}: aile {aile} {br}")
            hedef_olcu = tuple(BB.hedef_px(boy))
        else:
            r = subprocess.run([sys.executable, str(kod / "kod" / betik)], env=dict(env, OUT=str(tmp)), cwd=kod,
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(f"URETIM FAIL {betik}:", (r.stderr or r.stdout).strip().splitlines()[-1:] or "?")
                print("KONTROL FAIL")
                sys.exit(1)
            hedef_olcu = OLCU[boy]
        tam = tmp / f"{stil}_{boy}.jpg"
        ad = f"AstroLoveArt_{b1}_{b2}_{stil_ad}_{boy}"
        im = Image.open(tam)
        dpi = tuple(round(v) for v in im.info.get("dpi", (0, 0)))
        ok = im.size == hedef_olcu and dpi == (300, 300)
        print(f"OLCU {'PASS' if ok else 'FAIL'} tam {boy}: {im.size[0]}x{im.size[1]} {dpi[0]} dpi (beklenen {hedef_olcu[0]}x{hedef_olcu[1]} 300)")
        if g["tur"] == "NIHAI":
            yol = hedef / f"{ad}.jpg"
            shutil.copyfile(tam, yol)
        else:
            yol = hedef / f"{ad}_PREVIEW.jpg"
            filigran(tam, yol, kod / "galeri" / "fonts" / "Manrope.ttf")
            p = Image.open(yol)
            okp = max(p.size) == ONIZLEME_UZUN
            print(f"OLCU {'PASS' if okp else 'FAIL'} onizleme {boy}: {p.size[0]}x{p.size[1]} (uzun kenar {ONIZLEME_UZUN})")
            ok = ok and okp
        dosyalar.append({"dosya": yol.name, "olcu": list(Image.open(yol).size), "pass": ok})
    shutil.rmtree(tmp, ignore_errors=True)
    gecti = bool(dosyalar) and all(d["pass"] for d in dosyalar)
    json.dump({"girdi": g, "kod": os.environ.get("KOD_SHA", ""), "klasor": klasor, "dosyalar": dosyalar,
               "sonuc": "PASS" if gecti else "FAIL", "sure_sn": round(time.time() - t0, 1)},
              open(hedef / "KONTROL.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for d in dosyalar:
        print("DOSYA", d["dosya"], f"{d['olcu'][0]}x{d['olcu'][1]}")
    print(f"SURE {time.time() - t0:.0f} sn")
    print("KONTROL " + ("PASS" if gecti else "FAIL"))
    sys.exit(0 if gecti else 1)


if __name__ == "__main__":
    main()
