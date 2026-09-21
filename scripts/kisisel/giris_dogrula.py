#!/usr/bin/env python3
"""
Etsy girisi dogrulama (uretimden ONCE calisir).

Serdar karari 21 Eylul 2026:
  - Isim: en fazla 11 harf; yalniz harf (Latin + Turkce), bosluk, kesme isareti.
  - Tagline: en fazla 35 karakter.
  - Desteklenmeyen alfabe / karakter / emoji -> ELLE KONTROL.
  - Sinir icinde sigmazsa orantili kuculur; alt sinir %65. Altina inecek giris
    URETILMEZ, siparis ELLE KONTROL ile durur.
  - Isimler her zaman BUYUK harfe cevrilir (orijinal tasarimdaki gibi).
    Tagline musterinin yazdigi gibi kalir.
"""
import unicodedata
from pathlib import Path

ISIM_AZAMI = 11
TAG_AZAMI = 35
ALT_SINIR = 0.65
KESME = "'’ʼ"                       # ' ’ ʼ
AYIRICI = " -" + KESME                        # isimde harf disi izin verilenler
ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts"
FONTLAR = {"isim": "Cinzel.ttf", "tagline": "EBGaramond-Italic.ttf"}

# Turkce ozel: i/I donusumu
TR_BUYUK = str.maketrans({"i": "İ", "ı": "I"})
# Turkce kural yalniz metinde Turkce'ye ozgu harf varsa uygulanir.
TR_ULKE = {"TR", "TUR", "TURKEY", "T\u00dcRK\u0130YE", "TURKIYE"}
TR_ISARET = set("çğıöşüÇĞİÖŞÜ")


def buyut(s, ulke=None):
    """Isimleri buyuk harfe cevir.

    Serdar karari 21 Eylul 2026:
      - Teslimat ulkesi TR ise Turkce kural: i -> I, i -> I (DENIZ, ELIF).
      - Diger ulkelerde standart kural: i -> I.
      - Ulke bilgisi yoksa: isimde Turkce'ye ozgu harf varsa Turkce kural,
        yoksa standart.
    """
    s = unicodedata.normalize("NFC", s).replace("i\u0307", "\u0130")
    u = (ulke or "").strip().upper()
    if u:
        turkce = u in TR_ULKE
    else:
        turkce = bool(TR_ISARET & set(s))
    if turkce:
        s = s.translate(TR_BUYUK)
    return unicodedata.normalize("NFC", s.upper())


def harf_sayisi(s):
    """Yalniz harfler sayilir; bosluk, tire ve kesme isareti sayilmaz."""
    return sum(1 for c in s if c.isalpha())


def font_karakterleri(font_yolu):
    from fontTools.ttLib import TTFont
    f = TTFont(str(font_yolu), fontNumber=0, lazy=True)
    kod = set()
    for t in f["cmap"].tables:
        kod.update(t.cmap.keys())
    f.close()
    return kod


_CACHE = {}


def desteklenen(tur):
    if tur not in _CACHE:
        _CACHE[tur] = font_karakterleri(FONT_DIR / FONTLAR[tur])
    return _CACHE[tur]


def eksik_karakterler(metin, tur):
    d = desteklenen(tur)
    return sorted({c for c in metin if ord(c) not in d and not c.isspace()})


def alfabe_adi(c):
    try:
        ad = unicodedata.name(c)
    except ValueError:
        return "BILINMEYEN"
    for a in ("LATIN", "CYRILLIC", "GREEK", "ARABIC", "HEBREW", "HAN", "HIRAGANA",
              "KATAKANA", "HANGUL", "DEVANAGARI", "THAI", "ARMENIAN", "GEORGIAN"):
        if ad.startswith(a):
            return a
    return ad.split(" ")[0]


def emoji_mi(c):
    o = ord(c)
    return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0xFE00 <= o <= 0xFE0F
            or o == 0x200D or 0x1F1E6 <= o <= 0x1F1FF)


def isim_dogrula(ham, ulke=None):
    """(durum, deger, notlar) -> durum: 'TAMAM' | 'ELLE KONTROL'"""
    notlar = []
    s = unicodedata.normalize("NFC", (ham or "").strip())
    if not s:
        return "ELLE KONTROL", "", ["isim bos"]
    s = buyut(s, ulke)
    yabanci = {c for c in s if not c.isalpha() and c not in AYIRICI}
    if yabanci:
        notlar.append("izin verilmeyen karakter: " + " ".join(sorted(yabanci)))
    alfabeler = {alfabe_adi(c) for c in s if c.isalpha()}
    if alfabeler - {"LATIN"}:
        notlar.append("desteklenmeyen alfabe: " + ", ".join(sorted(alfabeler - {"LATIN"})))
    if any(emoji_mi(c) for c in s):
        notlar.append("emoji")
    eksik = eksik_karakterler(s, "isim")
    if eksik:
        notlar.append("fontta olmayan karakter: " + " ".join(eksik))
    n = harf_sayisi(s)
    if n > ISIM_AZAMI:
        notlar.append(f"{n} harf (azami {ISIM_AZAMI})")
    if n == 0:
        notlar.append("harf yok")
    return ("ELLE KONTROL" if notlar else "TAMAM"), s, notlar


def tagline_dogrula(ham):
    notlar = []
    s = unicodedata.normalize("NFC", (ham or "").strip())
    if not s:
        return "ELLE KONTROL", "", ["tagline bos"]
    if len(s) > TAG_AZAMI:
        notlar.append(f"{len(s)} karakter (azami {TAG_AZAMI})")
    if any(emoji_mi(c) for c in s):
        notlar.append("emoji")
    eksik = eksik_karakterler(s, "tagline")
    if eksik:
        notlar.append("fontta olmayan karakter: " + " ".join(eksik))
    alfabeler = {alfabe_adi(c) for c in s if c.isalpha()}
    if alfabeler - {"LATIN"}:
        notlar.append("desteklenmeyen alfabe: " + ", ".join(sorted(alfabeler - {"LATIN"})))
    return ("ELLE KONTROL" if notlar else "TAMAM"), s, notlar


def olcek_kontrol(olcek, oge="isim"):
    """Uretim sirasinda olculen orantili kuculme alt siniri (%65)."""
    if olcek < ALT_SINIR:
        return "ELLE KONTROL", [f"{oge} olcegi %{olcek * 100:.0f} < %{ALT_SINIR * 100:.0f}"]
    return "TAMAM", []


def siparis_dogrula(sol, sag, tagline, ulke=None):
    """ulke: teslimat ulkesi kodu (TR, US, DE...). Yoksa isimden karar verilir."""
    d = {"ulke": (ulke or "").strip().upper() or None}
    d["sol"] = dict(zip(("durum", "deger", "notlar"), isim_dogrula(sol, ulke)))
    d["sag"] = dict(zip(("durum", "deger", "notlar"), isim_dogrula(sag, ulke)))
    d["tagline"] = dict(zip(("durum", "deger", "notlar"), tagline_dogrula(tagline)))
    d["durum"] = ("ELLE KONTROL"
                  if any(d[k]["durum"] != "TAMAM" for k in ("sol", "sag", "tagline"))
                  else "TAMAM")
    return d


if __name__ == "__main__":
    ornek = [("SERDAR", "LENA", "Two Souls · One Bond"),
             ("Christopher", "elizabeth", "Written in the Stars Long Before Us"),
             ("Güli̇zar", "İpek", "Yağmurun Altındaki İlk Öpücük"),
             ("Александр", "LENA", "Forever Us"),
             ("ABDURRAHMANOGLU", "LENA", "Two Souls"),
             ("ANNA", "MARK", "We ❤️ Each Other Always And Forever!")]
    for a, b, t in ornek:
        r = siparis_dogrula(a, b, t)
        print(f"{r['durum']:13s} {a!r:20s} {b!r:10s} {t[:34]!r}")
        for k in ("sol", "sag", "tagline"):
            if r[k]["notlar"]:
                print(f"    {k}: {r[k]['notlar']}")
