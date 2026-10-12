"""78 cift icin IG karusel, IG Reel, TikTok ve Facebook gonderi metinleri (TASLAK).

Kaynak sablonlar (AYNEN): data/sosyal/arastirma/raporlar/
  INSTAGRAM_CLAUDE.md C.1, C.2, C.4, B.3 | TIKTOK_CLAUDE.md C.1 (B sablonu), C.4, B.3
  FACEBOOK_CLAUDE.md C.1, C.2, C.3, C.4
Calistir: python3 data/sosyal/metin/metin_78_uret.py  (uretir + denetler, FAIL'de cikis 1)
"""
import csv
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
RAPOR = KOK.parent / "arastirma" / "raporlar"

BURCLAR = ["Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo", "Libra",
           "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo"]
CIFTLER = [(a, b) for i, a in enumerate(BURCLAR) for b in BURCLAR[i:]]

IG_KARUSEL_HT = "#zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift"
IG_REEL_HT = "#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift"
TT_HT = "#zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts"
FB_HT = "#zodiaccouple #zodiacart #personalizedgift"


def ig_karusel(a, b):
    return (f"{a} and {b}, as one? Swipe to see your shared symbol.\n\n"
            f"Our {a} and {b} zodiac couple art merges both signs into one gold symbol on navy. "
            f"We add your two names and your personal message, so it becomes your own "
            f"{a} and {b} compatibility art for your wall.\n\n"
            "A personal zodiac gift for an anniversary, engagement or wedding. "
            "Save this for your next anniversary.\n\n"
            "Make it yours on Etsy, link in bio.\n\n" + IG_KARUSEL_HT)


def ig_alt(a, b):
    return [
        f"Slide 1. A navy background with gold zodiac art. Text on the image reads: "
        f"{a} & {b}, as one? Zodiac art with your names & message. Swipe to reveal.",
        f"Slide 2. The {a} sign and the {b} sign in gold on navy, and one gold symbol that "
        "merges both signs. Below it, the sample names Emily and James joined by an infinity "
        "sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.",
        f"Slide 3. The personalized poster hanging on a wall. It shows the merged {a} and {b} "
        "gold symbol on navy with two names and a short message.",
        f"Slide 4. Close-up of the poster with the names Emily and James under the gold {a} and "
        f"{b} symbol. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.",
    ]


def ig_reel(a, b):
    return (f"{a} and {b}, as one? Watch two signs become one gold symbol.\n\n"
            f"{a} and {b} compatibility art with your names and your personal message, "
            "designed by AstroLoveArt.\n\n"
            "Make it yours on Etsy, link in bio.\n\n" + IG_REEL_HT)


def tiktok(a, b):
    # B sablonu (profilde link yokken); tek paragraf
    return (f"{a} and {b}, as one? Watch two zodiac signs become one gold symbol. "
            f"{a} and {b} compatibility art with your names and your personal message, "
            "made by AstroLoveArt. A personalized anniversary gift idea for her or for him, "
            "and a couple gift for an engagement or wedding. "
            "Make it yours: search AstroLoveArt on Etsy. " + TT_HT)


def tiktok_kapak(a, b):
    return f"{a.upper()} & {b.upper()}, AS ONE?"


def fb_gonderi(a, b):
    return (f"{a} and {b}, as one? Two signs become one gold symbol.\n\n"
            f"Our {a} and {b} zodiac couple art merges both signs into one gold symbol on navy. "
            f"We add your two names and your personal message, so it becomes your own "
            f"{a} and {b} compatibility art for your wall.\n\n"
            "A personal gift for an anniversary, engagement or wedding.\n\n"
            "Make it yours: search AstroLoveArt on Etsy.\n\n" + FB_HT)


def fb_reel(a, b):
    return (f"{a} and {b}, as one? Watch two signs become one gold symbol.\n\n"
            f"{a} and {b} compatibility art with your names and your personal message, "
            "designed by AstroLoveArt.\n\n"
            "Find it on Etsy: search AstroLoveArt.\n\n" + FB_HT)


def fb_alt(a, b):
    return [
        f"Slide 2. The {a} sign and the {b} sign in gold on navy, and one gold symbol that "
        "merges both signs, with two sample names below. Text on the image reads: "
        "Two signs, Your shared symbol.",
        f"Slide 3. A room scene with the personalized {a} and {b} poster on a wall: "
        "one gold merged symbol on navy with two names and a short message.",
        f"Slide 4. Close-up of the poster showing the gold {a} and {b} symbol and two sample "
        "names. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.",
    ]


def anahtar(a, b):
    return f"{a.upper()}_{b.upper()}"


def yaz(ad, basliklar, satirlar):
    with open(KOK / ad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(basliklar)
        w.writerows(satirlar)


def uret():
    ig_k, ig_r, tt, fb = [], [], [], []
    for a, b in CIFTLER:
        k = anahtar(a, b)
        ig_k.append([k, a, b, ig_karusel(a, b), IG_KARUSEL_HT, *ig_alt(a, b)])
        ig_r.append([k, ig_reel(a, b), IG_REEL_HT])
        tt.append([k, tiktok(a, b), TT_HT, tiktok_kapak(a, b)])
        fb.append([k, fb_gonderi(a, b), fb_reel(a, b), FB_HT, *fb_alt(a, b)])
    yaz("IG_KARUSEL_78.csv", ["cift_anahtari", "burc_sol", "burc_sag", "caption", "hashtagler",
                              "alt_metin_1", "alt_metin_2", "alt_metin_3", "alt_metin_4"], ig_k)
    yaz("IG_REEL_78.csv", ["cift_anahtari", "caption", "hashtagler"], ig_r)
    yaz("TIKTOK_78.csv", ["cift_anahtari", "caption", "hashtagler", "kapak_yazisi"], tt)
    yaz("FACEBOOK_78.csv", ["cift_anahtari", "gonderi_metni", "reel_caption", "hashtagler",
                            "alt_metin_2", "alt_metin_3", "alt_metin_4"], fb)


# ---------------------------------------------------------------- denetim
# uzun/orta tire ve "+"; kisa kisa cizgi (raporlardaki "Close-up") kural disi
YASAK_KAR = ["—", "–", "‒", "―", "−", "+"]
YASAK_SOZ = ["constellation", "tarot", "tattoo", "wallpaper", "friendship", "tag your",
             "comment your", "best seller", "bestseller", "frame", "paper", "size", "price",
             "$", "astrolove ", "astrolove,", "astrolove."]
HATALAR = []


def kontrol(kosul, mesaj):
    if not kosul:
        HATALAR.append(mesaj)


def utf16(s):
    return len(s.encode("utf-16-le")) // 2


def oku(ad):
    with open(KOK / ad, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metin_denetle(dosya, satir, alan, deger, a, b, cift_adi_gerekli=True):
    yer = f"{dosya} {satir['cift_anahtari']} {alan}"
    for c in YASAK_KAR:
        kontrol(c not in deger, f"{yer}: yasak karakter {c!r}")
    kucuk = deger.lower()
    for s in YASAK_SOZ:
        kontrol(s not in kucuk, f"{yer}: yasak ifade {s!r}")
    kontrol("AstroLove" not in deger.replace("AstroLoveArt", "")
            and "ASTROLOVE" not in deger.replace("ASTROLOVEART", ""), f"{yer}: marka AstroLoveArt degil")
    if cift_adi_gerekli:
        kontrol(re.search(rf"\b{a}\b", deger, re.I) and re.search(rf"\b{b}\b", deger, re.I),
                f"{yer}: iki burc da yok")
        diger = [x for x in BURCLAR if x not in (a, b)]
        kontrol(not any(re.search(rf"\b{x}\b", deger, re.I) for x in diger), f"{yer}: yanlis burc")
        cift = f"{a} and {b}" if "AS ONE" not in deger else f"{a.upper()} & {b.upper()}"
        kontrol(cift in deger or f"{a} & {b}" in deger or f"{a} sign and the {b}" in deger,
                f"{yer}: cift adi alfabetik sirada degil")


def ht_say(s):
    return len(re.findall(r"#\w+", s))


def denetle():
    beklenen = [anahtar(a, b) for a, b in CIFTLER]
    kontrol(len(set(beklenen)) == 78, "78 benzersiz cift degil")
    burc = dict(zip(beklenen, CIFTLER))
    for ad, ht_sinir, alanlar in [
        ("IG_KARUSEL_78.csv", 5, ["caption", "alt_metin_1", "alt_metin_2", "alt_metin_3", "alt_metin_4"]),
        ("IG_REEL_78.csv", 5, ["caption"]),
        ("TIKTOK_78.csv", 5, ["caption", "kapak_yazisi"]),
        ("FACEBOOK_78.csv", 5, ["gonderi_metni", "reel_caption", "alt_metin_2", "alt_metin_3", "alt_metin_4"]),
    ]:
        rows = oku(ad)
        kontrol(len(rows) == 78, f"{ad}: {len(rows)} satir (78 olmali)")
        kontrol([r["cift_anahtari"] for r in rows] == beklenen, f"{ad}: cift anahtarlari/sira hatali")
        for r in rows:
            a, b = burc[r["cift_anahtari"]]
            kontrol(sorted([a, b]) == [a, b], f"{ad} {r['cift_anahtari']}: alfabetik degil")
            if "burc_sol" in r:
                kontrol((r["burc_sol"], r["burc_sag"]) == (a, b), f"{ad} {r['cift_anahtari']}: burc_sol/sag")
            kontrol(ht_say(r["hashtagler"]) <= ht_sinir, f"{ad} {r['cift_anahtari']}: hashtag > {ht_sinir}")
            metin_denetle(ad, r, "hashtagler", r["hashtagler"], a, b, cift_adi_gerekli=False)
            for alan in alanlar:
                v = r[alan]
                metin_denetle(ad, r, alan, v, a, b)
                if alan in ("caption", "gonderi_metni", "reel_caption"):
                    kontrol(utf16(v) <= 2200, f"{ad} {r['cift_anahtari']} {alan}: {utf16(v)} > 2200")
                    kontrol(ht_say(v) <= 5, f"{ad} {r['cift_anahtari']} {alan}: hashtag > 5")
                    kontrol(v.endswith(r["hashtagler"]), f"{ad} {r['cift_anahtari']} {alan}: hashtagler sutunuyla uyusmuyor")
                if alan.startswith("alt_metin"):
                    kontrol(utf16(v) <= 1000, f"{ad} {r['cift_anahtari']} {alan}: alt metin > 1000")
            if ad == "TIKTOK_78.csv":
                kontrol("\n" not in r["caption"], f"{ad} {r['cift_anahtari']}: caption tek paragraf degil")


# ------------------------------------------------- rapor ornekleriyle karsilastirma
def bloklar(md, baslik):
    """'### <baslik>' bolumundeki ```text bloklari (sirayla)."""
    m = re.search(rf"^### {re.escape(baslik)}\n(.*?)(?=^### |^## |\Z)", md, re.S | re.M)
    if not m:
        return None
    return re.findall(r"```text\n(.*?)\n```", m.group(1), re.S)


def karsilastir():
    ig = (RAPOR / "INSTAGRAM_CLAUDE.md").read_text(encoding="utf-8")
    tt = (RAPOR / "TIKTOK_CLAUDE.md").read_text(encoding="utf-8")
    fb = (RAPOR / "FACEBOOK_CLAUDE.md").read_text(encoding="utf-8")
    satirlar = []
    ornekler = [
        # (cift, IG baslik, IG'de kullanilan sira, TT baslik, FB baslik)
        (("Gemini", "Leo"), "D.1 Gemini & Leo", ("Gemini", "Leo"), "D.1 Gemini & Leo", "D.1 Gemini & Leo"),
        (("Cancer", "Libra"), "D.2 Cancer & Libra", ("Cancer", "Libra"), "D.2 Cancer & Libra", "D.2 Cancer & Libra"),
        (("Pisces", "Scorpio"), "D.3 Scorpio & Pisces", ("Scorpio", "Pisces"),
         "D.3 Scorpio & Pisces (alfabetik kuralla: Pisces & Scorpio)", "D.3 Pisces & Scorpio"),
    ]
    for (a, b), igb, (ia, ib), ttb, fbb in ornekler:
        k = anahtar(a, b)
        bi, bt, bf = bloklar(ig, igb), bloklar(tt, ttb), bloklar(fb, fbb)
        for ad, ok in [("IG karusel", bi and bi[0] == ig_karusel(ia, ib)),
                       ("IG Reel", bi and bi[1] == ig_reel(ia, ib)),
                       ("IG alt metin 1-4", bi and bi[2].split("\n") == ig_alt(ia, ib)),
                       ("TikTok caption (B)", bt and bt[1] == tiktok(a, b)),
                       ("TikTok kapak", f"`{tiktok_kapak(a, b)}`" in tt),
                       ("FB gonderi", bf and bf[0] == fb_gonderi(a, b)),
                       ("FB Reel", bf and bf[1] == fb_reel(a, b)),
                       ("FB alt metin 2-4", bf and bf[3].split("\n") == fb_alt(a, b))]:
            kontrol(bool(ok), f"ornek farkli: {k} {ad}")
            not_ = ""
            if ad.startswith("IG") and (ia, ib) != (a, b):
                not_ = f"rapor sirasi {ia} & {ib}; CSV alfabetik {a} & {b} (yalniz sira farkli)"
            satirlar.append(f"{k:16} {ad:20} {'AYNI' if ok else 'FARKLI'} {not_}")
    return satirlar


if __name__ == "__main__":
    uret()
    denetle()
    rapor = karsilastir()
    print("\n".join(rapor))
    for r in [("IG_KARUSEL_78.csv", "caption"), ("IG_REEL_78.csv", "caption"), ("TIKTOK_78.csv", "caption"),
              ("FACEBOOK_78.csv", "gonderi_metni"), ("FACEBOOK_78.csv", "reel_caption")]:
        n = [utf16(x[r[1]]) for x in oku(r[0])]
        print(f"{r[0]:18} {r[1]:14} {min(n)}-{max(n)} karakter")
    if HATALAR:
        print("FAIL", len(HATALAR))
        print("\n".join(HATALAR[:40]))
        sys.exit(1)
    print("PASS: 4 dosya x 78 satir, tire/+ yok, yasak ifade yok, hashtag <= 5, caption <= 2200, cift adlari dogru")
