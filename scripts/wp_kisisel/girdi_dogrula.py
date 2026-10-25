#!/usr/bin/env python3
"""Musteri girdisi dogrulamasi: isim / mesaj / font kapsami (GOREV_0014).

Neden: siparis metni SESSIZCE kirpilabiliyordu ve fontta olmayan harf (U-umlaut,
E-accent, dotless i) yerine .notdef kutusu basilabiliyordu; ikisi de kapiya
takilmiyordu. Burada esik YOK, kural var: uymayan girdi REDDEDILIR.

Font kapsami olcumu: TAHMIN YOK - fontun `cmap` tablosu dogrudan okunur
(fontTools bagimliligi olmadan, format 12/4/6/0). Render karsilastirmasi
guvenilmezdi: HarfBuzz eksik glifi kimi zaman notdef'ten FARKLI cizer
(olculdu: DejaVuSans, U+1F600 maskesi 100x86, notdef 58x85).
"""
import pathlib, struct, unicodedata

ISIM_SINIR = 30          # Etsy kisisellestirme onerisi (MTO_DIJITAL_KURALLARI)
MESAJ_SINIR = 35         # GOREV_0014 testi; MTO onerisi 80 - celiski raporlandi (E08)
NOTDEF_KOD = ""    # ozel kullanim alani: hicbir uretim fontunda glif yok


def _temiz(s):
    return unicodedata.normalize("NFC", (s or "").strip())


def isim_dogrula(isim, alan="isim", sinir=ISIM_SINIR):
    s = _temiz(isim)
    if not s:
        raise SystemExit(f"HATA: {alan} bos. REDDEDILDI.")
    if len(s) > sinir:
        raise SystemExit(f"HATA: {alan} {len(s)} karakter > sinir {sinir}: {s!r}. "
                         f"REDDEDILDI - kirpma yapilmaz.")
    kotu = sorted({c for c in s if unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co", "Cn")})
    if kotu:
        raise SystemExit(f"HATA: {alan} basilamayan karakter iceriyor: {kotu}. REDDEDILDI.")
    return s


def mesaj_dogrula(mesaj, sinir=MESAJ_SINIR):
    s = _temiz(mesaj)
    if len(s) > sinir:
        raise SystemExit(f"HATA: mesaj {len(s)} karakter > sinir {sinir}: {s!r}. "
                         f"REDDEDILDI - kirpma yapilmaz.")
    kotu = sorted({c for c in s if unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co", "Cn")})
    if kotu:
        raise SystemExit(f"HATA: mesaj basilamayan karakter iceriyor: {kotu}. REDDEDILDI.")
    return s


def _tablolar(veri):
    if veri[:4] == b"ttcf":                       # font koleksiyonu: ilk font
        (ofs,) = struct.unpack(">I", veri[12:16])
    else:
        ofs = 0
    (sayi,) = struct.unpack(">H", veri[ofs + 4:ofs + 6])
    t = {}
    for i in range(sayi):
        k = ofs + 12 + 16 * i
        etiket, _, o, u = struct.unpack(">4sIII", veri[k:k + 16])
        t[etiket] = (o, u)
    return t


def _glif_4(veri, o, kod):
    if kod > 0xFFFF:
        return 0
    (segx2,) = struct.unpack(">H", veri[o + 6:o + 8])
    n = segx2 // 2
    son = o + 14
    bas = son + segx2 + 2
    delta = bas + segx2
    ofs = delta + segx2
    for i in range(n):
        (e,) = struct.unpack(">H", veri[son + 2 * i:son + 2 * i + 2])
        if kod > e:
            continue
        (s,) = struct.unpack(">H", veri[bas + 2 * i:bas + 2 * i + 2])
        if kod < s:
            return 0
        (ro,) = struct.unpack(">H", veri[ofs + 2 * i:ofs + 2 * i + 2])
        (d,) = struct.unpack(">h", veri[delta + 2 * i:delta + 2 * i + 2])
        if ro == 0:
            return (kod + d) & 0xFFFF
        yer = ofs + 2 * i + ro + 2 * (kod - s)
        (g,) = struct.unpack(">H", veri[yer:yer + 2])
        return 0 if g == 0 else (g + d) & 0xFFFF
    return 0


def _glif_12(veri, o, kod):
    (n,) = struct.unpack(">I", veri[o + 12:o + 16])
    for i in range(n):
        k = o + 16 + 12 * i
        s, e, g0 = struct.unpack(">III", veri[k:k + 12])
        if s <= kod <= e:
            return g0 + (kod - s)
        if kod < s:
            return 0
    return 0


def _glif_6(veri, o, kod):
    ilk, adet = struct.unpack(">HH", veri[o + 6:o + 10])
    if not (ilk <= kod < ilk + adet):
        return 0
    (g,) = struct.unpack(">H", veri[o + 10 + 2 * (kod - ilk):o + 12 + 2 * (kod - ilk)])
    return g


def _glif_0(veri, o, kod):
    return veri[o + 6 + kod] if kod < 256 else 0


def cmap_altlari(font_yolu):
    """(format, ofset) listesi - tercih sirasi: 12 (tam), 4 (BMP), 6, 0."""
    veri = pathlib.Path(font_yolu).read_bytes()
    tb = _tablolar(veri)
    if b"cmap" not in tb:
        raise SystemExit(f"HATA: {font_yolu} icinde cmap tablosu yok - font kapsami olculemez.")
    c0 = tb[b"cmap"][0]
    (n,) = struct.unpack(">H", veri[c0 + 2:c0 + 4])
    alt = []
    for i in range(n):
        k = c0 + 4 + 8 * i
        _p, _e, o = struct.unpack(">HHI", veri[k:k + 8])
        (bicim,) = struct.unpack(">H", veri[c0 + o:c0 + o + 2])
        alt.append((bicim, c0 + o))
    sira = {12: 0, 4: 1, 6: 2, 0: 3}
    alt = [x for x in alt if x[0] in sira]
    alt.sort(key=lambda x: sira[x[0]])
    if not alt:
        raise SystemExit(f"HATA: {font_yolu} cmap alt tablolari desteklenmiyor (format 0/4/6/12 yok).")
    return veri, alt


def glif_id(veri, alt, kod):
    for bicim, o in alt:
        g = {12: _glif_12, 4: _glif_4, 6: _glif_6, 0: _glif_0}[bicim](veri, o, kod)
        if g:
            return g
    return 0


def eksik_glifler(font_yolu, metin, punto=96):
    """metinde fontun cmap'inde OLMAYAN karakterleri dondurur (bosluk haric).

    punto: geriye uyum icin kabul edilir, olcume girmez (cmap punto'dan bagimsiz).
    """
    veri, alt = cmap_altlari(font_yolu)
    return [ch for ch in sorted(set(metin))
            if not ch.isspace() and glif_id(veri, alt, ord(ch)) == 0]


def font_kapsami_dogrula(font_yolu, metin, alan="metin", punto=96):
    eksik = eksik_glifler(font_yolu, metin, punto)
    if eksik:
        ad = ", ".join(f"{c!r} U+{ord(c):04X}" for c in eksik)
        raise SystemExit(f"HATA: {alan} fontta glifi olmayan karakter iceriyor ({font_yolu}): "
                         f"{ad}. REDDEDILDI - .notdef kutusu basilmaz.")
    return True


def kayit_dogrula(isim1, isim2, mesaj, isim_font=None, mesaj_font=None,
                  mesaj_sinir=MESAJ_SINIR):
    """Isimler ISIM_FONT ile, mesaj TAG_FONT ile basilir: kapsam AYRI dogrulanir."""
    i1 = isim_dogrula(isim1, "isim1")
    i2 = isim_dogrula(isim2, "isim2")
    me = mesaj_dogrula(mesaj, mesaj_sinir)
    if isim_font:
        font_kapsami_dogrula(isim_font, i1 + i2, "isimler")
    if mesaj_font and me:
        font_kapsami_dogrula(mesaj_font, me, "mesaj")
    return i1, i2, me
