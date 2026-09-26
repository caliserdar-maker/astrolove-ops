#!/usr/bin/env python3
"""
DIJITAL 78 - ADIM 5: METIN TASLAKLARI + QC (Etsy'ye yazma YOK).

3 cift icin baslik / 13 etiket / EN aciklama / RU aciklama taslagi uretir ve
tek scriptle PASS/FAIL dogrular. Basilabilir boyutlar TAHMIN EDILMEZ:
ZIP_KONTROL.csv'deki OLCULEN piksellerden 300 DPI'da turetilir.

Kurallar (Serdar, 20 Eyl 2026):
  - Iki burc her baslikta gecer (Gemini+Gemini'de en az iki kez).
  - Kisisellestirme, isim, uyum okumasi, dogum haritasi, cerceve, metalik
    folyo, asilmaya hazir vaadi YOK.
  - Tam 13 etiket, her biri <= 20 karakter.
  - Tek burc aramalari iki burc icin de kapsanir (zodiac / sign / star sign).
  - Ingilizce metinde uzun tire (em dash, en dash) YOK.
  - "5 Colors" gercegi hem baslikta hem aciklamada.
"""
import argparse
import csv
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]

# Oran -> standart basim boyutlari (inc). Hangileri kullanilabilir, olculen
# pikselden 300 DPI kuraliyla secilir.
BOYUT_MERDIVENI = OrderedDict([
    ("2:3", [(4, 6), (6, 9), (8, 12), (12, 18), (16, 24), (20, 30), (24, 36)]),
    ("3:4", [(6, 8), (9, 12), (12, 16), (15, 20), (18, 24)]),
    ("4:5", [(4, 5), (8, 10), (12, 15), (16, 20), (24, 30)]),
    ("11:14", [(11, 14), (16.5, 21), (22, 28)]),
    ("A", [("A5", 5.8, 8.3), ("A4", 8.3, 11.7), ("A3", 11.7, 16.5), ("A2", 16.5, 23.4),
           ("A1", 23.4, 33.1)]),
])
ORAN_SIRA = ["2:3", "3:4", "4:5", "11:14", "A"]

CIFTLER = [
    {"anahtar": "ARIES_LEO", "a": "Aries", "b": "Leo",
     "baslik": ("Aries and Leo Zodiac Wall Art, 5 Colors in One Download, "
                "Printable Couple Poster, Aries Sign and Leo Sign Art"),
     "etiketler": ["aries leo", "aries zodiac", "aries sign", "aries star sign",
                   "leo zodiac", "leo sign", "leo star sign", "zodiac wall art",
                   "couple wall art", "astrology print", "printable wall art",
                   "digital download", "celestial decor"],
     "acilis": ("Two star signs, one symbol. The Aries and Leo glyphs are drawn into a "
                "single line emblem for couples who share a love of astrology.")},
    {"anahtar": "CANCER_SCORPIO", "a": "Cancer", "b": "Scorpio",
     "baslik": ("Cancer and Scorpio Zodiac Wall Art, 5 Colors in One Download, "
                "Printable Couple Poster, Cancer Sign and Scorpio Sign Art"),
     "etiketler": ["cancer scorpio", "cancer zodiac", "cancer sign", "cancer star sign",
                   "scorpio zodiac", "scorpio sign", "scorpio star sign", "zodiac wall art",
                   "couple wall art", "astrology print", "printable wall art",
                   "digital download", "celestial decor"],
     "acilis": ("Two star signs, one symbol. The Cancer and Scorpio glyphs are drawn into a "
                "single line emblem for couples who share a love of astrology.")},
    {"anahtar": "GEMINI_GEMINI", "a": "Gemini", "b": "Gemini",
     "baslik": ("Gemini and Gemini Zodiac Wall Art, 5 Colors in One Download, "
                "Printable Couple Poster, Gemini Sign Astrology Art"),
     "etiketler": ["gemini zodiac", "gemini sign", "gemini star sign", "gemini couple",
                   "gemini wall art", "gemini gift", "zodiac wall art", "couple wall art",
                   "astrology print", "printable wall art", "digital download",
                   "celestial decor", "air sign decor"],
     "acilis": ("Two Gemini signs, one symbol. Both Gemini glyphs are drawn into a single "
                "line emblem for couples who share a love of astrology.")},
]

RU_BURC = {"Aries": "Овен", "Leo": "Лев", "Cancer": "Рак", "Scorpio": "Скорпион",
           "Gemini": "Близнецы"}
RU_EDISYON = {"Champagne Ivory": "Champagne Ivory (тёплый слоновая кость)",
              "Pure White": "Pure White (чистый белый)",
              "Warm Parchment": "Warm Parchment (тёплый пергамент)",
              "Midnight Blue": "Midnight Blue (глубокий синий)",
              "Deep Black": "Deep Black (глубокий чёрный)"}

YASAK = [
    (r"personali[sz]", "kisisellestirme"),
    (r"\byour name\b|\bcustom name\b|\bnames? and dates?\b", "isim"),
    (r"compatibility reading|love reading", "uyum okumasi"),
    (r"birth chart|natal chart|\bhoroscope reading\b", "dogum haritasi"),
    (r"\bframed\b|\bframe is included\b|\bwith frame\b", "cerceve vaadi"),
    (r"ready to hang|ready-to-hang", "asilmaya hazir vaadi"),
    (r"metallic|\bfoil\b|gold foil", "metalik folyo"),
]
UZUN_TIRE = re.compile(r"[—–]")
# "not a compatibility reading" gibi OLUMSUZ cumleler iddia degildir, elenir.
OLUMSUZ = re.compile(r"\b(not|never|no)\b[^.]{0,24}$", re.I)
ETIKET_GECERLI = re.compile(r"^[a-z0-9 ]+$")


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------- olculen boyutlar
def olculen_pikseller(zip_csv, cift):
    """ZIP_KONTROL.csv 'olculen_pikseller' -> {oran: (w, h)} (en buyuk edisyon)."""
    out = {}
    p = Path(zip_csv)
    if not p.exists():
        return out
    with open(p, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("cift") != cift or not r.get("olculen_pikseller"):
                continue
            for parca in r["olculen_pikseller"].split(";"):
                m = re.search(r"=(\d+)x(\d+)@([^/]+)/", parca.strip())
                if not m:
                    continue
                w, h, oran = int(m.group(1)), int(m.group(2)), m.group(3).strip()
                if oran in BOYUT_MERDIVENI:
                    onceki = out.get(oran)
                    if not onceki or w * h > onceki[0] * onceki[1]:
                        out[oran] = (w, h)
    return out


def boyut_satiri(oran, wh):
    """300 DPI'da sigan standart boyutlar + en buyuk boyut."""
    if not wh:
        return None
    w, h = sorted(wh)
    inc_w, inc_h = w / 300.0, h / 300.0
    sigan = []
    for giris in BOYUT_MERDIVENI[oran]:
        if oran == "A":
            ad, iw, ih = giris
        else:
            iw, ih = giris
            ad = f"{iw:g}x{ih:g} in"
        if iw <= inc_w + 0.02 and ih <= inc_h + 0.02:
            sigan.append(ad)
    return {"oran": oran, "piksel": f"{w}x{h}", "inc": f"{inc_w:.1f}x{inc_h:.1f}",
            "boyutlar": sigan}


def boyut_bloku(olcum):
    satir, eksik = [], []
    for oran in ORAN_SIRA:
        b = boyut_satiri(oran, olcum.get(oran))
        if not b:
            eksik.append(oran)
            continue
        satir.append(b)
    return satir, eksik


# -------------------------------------------------------- metin uretimi
def en_aciklama(c, boyutlar):
    ed = "\n".join(f"{i+1}. {e}" for i, e in enumerate(EDISYONLAR))
    if boyutlar:
        bl = "\n".join(
            f"{b['oran']} ratio, {b['piksel']} px, prints up to "
            f"{b['boyutlar'][-1] if b['boyutlar'] else b['inc'] + ' in'} at 300 DPI"
            + (f" (also {', '.join(b['boyutlar'][:-1])})" if len(b['boyutlar']) > 1 else "")
            for b in boyutlar)
    else:
        bl = "OLCUM BEKLENIYOR"
    return f"""{c['acilis']}

Instant digital download. Print it at home, at a local print shop, or with an online printing service.

* WHAT MAKES THIS LISTING DIFFERENT
5 Colors in one purchase. You receive every colour edition of this design, not just one:
{ed}

* WHAT YOU RECEIVE
5 ZIP files, one per colour edition. Every ZIP holds the same set:
5 high resolution JPG files, one for each print ratio
Ratios 2:3, 3:4, 4:5, 11:14 and A series
Full artwork in every ratio, nothing cropped
300 DPI, sRGB
A Print and Care Guide PDF
A thank you PDF from our studio

* PRINT SIZES IN EVERY ZIP
{bl}

* HOW TO DOWNLOAD
After Etsy confirms your payment, open Etsy on a computer or a mobile browser and go to Your account, then Purchases and reviews. Open this order and download all 5 ZIP files. Extract the edition you want to print, then pick the JPG that matches your print size. Ask your printer to print without cropping, and read the Print and Care Guide first.

* GOOD TO KNOW
This is a digital file, so nothing is shipped to you. Props in the mockup photos are for display only.
This is decorative wall art, not a compatibility reading and not a birth chart.
Names, dates, quotes and colour changes are not offered.
Colours may vary between your screen and the final print, depending on your printer, ink and paper.

* LICENSE
Your purchase is for personal use. Print it as often as you like for your own home or as a gift. Copyright stays with AstroLove: resale, redistribution and commercial use are not permitted.

Central composite symbol and original composition, copyright 2026 AstroLove.

ASTROLOVE
The Shape of Your Connection"""


def ru_aciklama(c):
    a, b = RU_BURC.get(c["a"], c["a"]), RU_BURC.get(c["b"], c["b"])
    ed = "\n".join(f"{i+1}. {RU_EDISYON[e]}" for i, e in enumerate(EDISYONLAR))
    ikili = f"{a} и {b}" if c["a"] != c["b"] else f"{a} и {b} (одна и та же стихия)"
    return f"""Два знака зодиака, один символ. Глифы {ikili} соединены в единую линейную эмблему для пар, которые любят астрологию.

Мгновенное скачивание. Печатайте дома, в типографии или через онлайн сервис печати.

ЧТО ВЫ ПОЛУЧАЕТЕ (мгновенное скачивание после оплаты):
5 цветовых версий в одной покупке, 5 ZIP архивов:
{ed}

В каждом архиве одно и то же наполнение:
5 файлов JPG высокого разрешения, по одному на каждое соотношение сторон
Соотношения 2:3, 3:4, 4:5, 11:14 и серия A
Полное изображение в каждом соотношении, без обрезки
300 DPI, sRGB
PDF с рекомендациями по печати
PDF с благодарностью от студии

КАК ЭТО РАБОТАЕТ:
После подтверждения оплаты откройте Etsy на компьютере или в мобильном браузере, раздел «Ваш аккаунт», затем «Покупки и отзывы». Скачайте все 5 архивов, распакуйте нужную версию и выберите файл JPG под ваш размер печати. Просите печать без обрезки.

ОБРАТИТЕ ВНИМАНИЕ:
Это цифровой файл, физическая посылка не отправляется. Реквизит на фотографиях служит только для показа.
Это декоративный постер, а не разбор совместимости и не натальная карта.
Имена, даты, цитаты и смена цвета не предлагаются.
Цвета на экране и в печати могут отличаться в зависимости от принтера, чернил и бумаги.

ЛИЦЕНЗИЯ:
Покупка для личного использования. Печатайте сколько угодно для своего дома или в подарок. Авторские права остаются за AstroLove: перепродажа и коммерческое использование не разрешены."""


# -------------------------------------------------------- QC
def qc(c, baslik, etiketler, en, ru):
    h = []
    for burc in {c["a"], c["b"]}:
        if not re.search(rf"\b{burc}\b", baslik):
            h.append(f"baslikta '{burc}' yok")
    if c["a"] == c["b"] and len(re.findall(rf"\b{c['a']}\b", baslik)) < 2:
        h.append(f"ayni burc ciftinde '{c['a']}' baslikta 2 kez gecmeli")
    if "5 Colors" not in baslik:
        h.append("baslikta '5 Colors' yok")
    if "5 Colors" not in en:
        h.append("aciklamada '5 Colors' yok")
    if len(baslik) > 140:
        h.append(f"baslik {len(baslik)} karakter (Etsy siniri 140)")
    if len(etiketler) != 13:
        h.append(f"etiket sayisi {len(etiketler)} (13 olmali)")
    if len(set(etiketler)) != len(etiketler):
        h.append("tekrar eden etiket var")
    for t in etiketler:
        if len(t) > 20:
            h.append(f"etiket 20 karakteri asiyor: '{t}' ({len(t)})")
        if not ETIKET_GECERLI.match(t):
            h.append(f"etikette gecersiz karakter: '{t}'")
    for burc in {c["a"], c["b"]}:
        bl = burc.lower()
        for kalip in (f"{bl} zodiac", f"{bl} sign", f"{bl} star sign"):
            if kalip not in etiketler:
                h.append(f"tek burc etiketi eksik: '{kalip}'")
    if UZUN_TIRE.search(baslik) or UZUN_TIRE.search(en):
        h.append("Ingilizce metinde uzun tire (em/en dash) var")
    for metin, ad in ((baslik, "baslik"), (en, "EN aciklama"), (ru, "RU aciklama")):
        for rx, etiket in YASAK:
            for m in re.finditer(rx, metin, re.I):
                onc = metin[max(0, m.start() - 40):m.start()]
                if OLUMSUZ.search(onc):
                    continue        # olumsuzlama: iddia degil, uyari
                h.append(f"{ad}: yasak ifade ({etiket}) -> '{m.group(0)}'")
    for e in EDISYONLAR:
        if e not in en:
            h.append(f"aciklamada edisyon adi yok: {e}")
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip-csv", default="", help="ZIP_KONTROL.csv (olculen pikseller)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    md = [f"# METIN TASLAKLARI - 3 CIFT ({simdi()} UTC)", "",
          "Taslaktir. Etsy'ye YAZILMADI. Onay sonrasi uygulanir.", "",
          "Kurallar: iki burc her baslikta; kisisellestirme / isim / uyum okumasi / dogum",
          "haritasi / cerceve / metalik folyo / asilmaya hazir vaadi YOK; tam 13 etiket,",
          "her biri <= 20 karakter; tek burc aramalari iki burc icin de kapsanir;",
          "Ingilizce metinde uzun tire YOK; \"5 Colors\" hem baslikta hem aciklamada.", ""]
    tum_hata, eksik_olcum = [], []

    for c in CIFTLER:
        olcum = olculen_pikseller(a.zip_csv, c["anahtar"]) if a.zip_csv else {}
        boyutlar, eksik = boyut_bloku(olcum)
        if eksik:
            eksik_olcum.append(f"{c['anahtar']}: {', '.join(eksik)}")
        baslik, etiketler = c["baslik"], c["etiketler"]
        en, ru = en_aciklama(c, boyutlar), ru_aciklama(c)
        hatalar = qc(c, baslik, etiketler, en, ru)
        tum_hata += [f"{c['anahtar']}: {x}" for x in hatalar]

        md += [f"## {c['a']} + {c['b']}", "",
               f"### Baslik ({len(baslik)} karakter)", "", "```", baslik, "```", "",
               "### 13 etiket", "", "| # | etiket | karakter |", "|---:|---|---:|"]
        for i, t in enumerate(etiketler, 1):
            md.append(f"| {i} | {t} | {len(t)} |")
        md += ["", "### Aciklama (EN)", "", "```", en, "```", "",
               "### Aciklama (RU taslak)", "", "```", ru, "```", "",
               f"### QC: {'PASS' if not hatalar else 'FAIL'}", ""]
        md += ([f"- {x}" for x in hatalar] if hatalar else ["- Tum kurallar saglandi."])
        md.append("")

    md += ["## Olcum notu", ""]
    md.append("- Basilabilir boyutlar ZIP_KONTROL.csv'deki OLCULEN piksellerden 300 DPI ile "
              "turetildi, tahmin edilmedi.")
    if eksik_olcum:
        md += ["- OLCUM EKSIK (boyut satiri bos kalan oranlar):"] + [f"  - {x}" for x in eksik_olcum]
    md += ["", f"## GENEL QC: {'PASS' if not tum_hata else 'FAIL'}", ""]
    md += ([f"- {x}" for x in tum_hata] if tum_hata else ["- 3/3 cift kurallara uygun."])
    (out / "METIN_TASLAK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(("PASS" if not tum_hata else "FAIL") + f" | {len(CIFTLER)} cift | hata {len(tum_hata)}",
          flush=True)
    for x in tum_hata:
        print("  - " + x, flush=True)
    sys.exit(1 if tum_hata else 0)


if __name__ == "__main__":
    main()
