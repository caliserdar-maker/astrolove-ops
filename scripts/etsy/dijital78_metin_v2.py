#!/usr/bin/env python3
"""
DIJITAL 78 v2 - ADIM 5: METIN TASLAKLARI v2 + QC (Etsy'ye yazma YOK).

Serdar duzeltmeleri (20 Eyl 2026):
  - "A thank you PDF from our studio" -> "A thank you note from us";
    "studio" hicbir metinde gecmez (EN ve RU).
  - Yazim tutarliligi: Amerikan "color"; "colour" yok.
  - Basilabilir boyutlar OLCULEN piksellerden dogru turetilir
    (3:4 7200x9600 -> 24x32 in; A serisi 9934x14044 -> A0, ara boylar dahil).
  - Etiketler: cift etiketi "X and Y"; "zodiac gift" ve "celestial wall art"
    her sette; tam 13, her biri <= 20; tek burc kapsami korunur.
  - Baslik: anahtar kelime tekrari yok, tek kalip.
  - Aciklamaya "* PREFER A PRINTED POSTER?" (ayni ciftin POD ilani, tek cumle,
    fiyat yok). RU'da da ayni bolum.
  - Ingilizce metinde uzun tire YOK.
"""
import argparse
import csv
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
ORAN_SIRA = ["2:3", "3:4", "4:5", "11:14", "A"]

# Oran -> standart basim boyutlari (inc). Hangileri kullanilabilir, olculen
# pikselden 300 DPI kuraliyla secilir. Ust uclar olculen degerlere gore genisletildi:
# 2:3 7200x10800 -> 24x36 | 3:4 7200x9600 -> 24x32 | 4:5 7200x9000 -> 24x30
# 11:14 6600x8400 -> 22x28 | A 9934x14044 -> A0
BOYUT_MERDIVENI = OrderedDict([
    ("2:3", [(4, 6), (6, 9), (8, 12), (10, 15), (12, 18), (16, 24), (20, 30), (24, 36)]),
    ("3:4", [(6, 8), (9, 12), (12, 16), (15, 20), (18, 24), (21, 28), (24, 32)]),
    ("4:5", [(4, 5), (8, 10), (12, 15), (16, 20), (20, 25), (24, 30)]),
    ("11:14", [(11, 14), (16.5, 21), (22, 28)]),
    ("A", [("A5", 5.83, 8.27), ("A4", 8.27, 11.69), ("A3", 11.69, 16.54),
           ("A2", 16.54, 23.39), ("A1", 23.39, 33.11), ("A0", 33.11, 46.81)]),
])
DPI = 300.0
TOL_PX = 4          # olcum yuvarlamasi icin piksel toleransi

ORTAK_ETIKET = ["zodiac gift", "celestial wall art", "zodiac wall art", "couple wall art",
                "printable wall art", "digital download"]
V1_ETIKET = {
    "ARIES_LEO": ["aries leo", "aries zodiac", "aries sign", "aries star sign", "leo zodiac",
                  "leo sign", "leo star sign", "zodiac wall art", "couple wall art",
                  "astrology print", "printable wall art", "digital download", "celestial decor"],
    "CANCER_SCORPIO": ["cancer scorpio", "cancer zodiac", "cancer sign", "cancer star sign",
                       "scorpio zodiac", "scorpio sign", "scorpio star sign", "zodiac wall art",
                       "couple wall art", "astrology print", "printable wall art",
                       "digital download", "celestial decor"],
    "GEMINI_GEMINI": ["gemini zodiac", "gemini sign", "gemini star sign", "gemini couple",
                      "gemini wall art", "gemini gift", "zodiac wall art", "couple wall art",
                      "astrology print", "printable wall art", "digital download",
                      "celestial decor", "air sign decor"],
}

CIFTLER = [
    {"anahtar": "ARIES_LEO", "a": "Aries", "b": "Leo",
     "etiketler": ["aries and leo", "aries zodiac", "aries sign", "aries star sign",
                   "leo zodiac", "leo sign", "leo star sign"] + ORTAK_ETIKET,
     "acilis": ("Two star signs, one symbol. The Aries and Leo glyphs are drawn into a "
                "single line emblem for couples who share a love of astrology.")},
    {"anahtar": "CANCER_SCORPIO", "a": "Cancer", "b": "Scorpio",
     "etiketler": ["cancer and scorpio", "cancer zodiac", "cancer sign", "cancer star sign",
                   "scorpio zodiac", "scorpio sign", "scorpio star sign"] + ORTAK_ETIKET,
     "acilis": ("Two star signs, one symbol. The Cancer and Scorpio glyphs are drawn into a "
                "single line emblem for couples who share a love of astrology.")},
    {"anahtar": "GEMINI_GEMINI", "a": "Gemini", "b": "Gemini",
     "etiketler": ["gemini and gemini", "gemini zodiac", "gemini sign", "gemini star sign",
                   "gemini couple", "gemini wall art", "air sign decor"] + ORTAK_ETIKET,
     "acilis": ("Two Gemini signs, one symbol. Both Gemini glyphs are drawn into a single "
                "line emblem for couples who share a love of astrology.")},
]
BASLIK_KALIP = ("{a} and {b} Zodiac Couple Print, 5 Colors in One Download, "
                "Printable Wall Art, Astrology Gift for Couples")

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
OLUMSUZ = re.compile(r"\b(not|never|no)\b[^.]{0,24}$", re.I)
ETIKET_GECERLI = re.compile(r"^[a-z0-9 ]+$")
STUDIO = re.compile(r"studio|студи", re.I)
COLOUR = re.compile(r"\bcolour", re.I)
POD_BASLIK = "* PREFER A PRINTED POSTER?"
POD_BASLIK_RU = "* ХОТИТЕ НАПЕЧАТАННЫЙ ПОСТЕР?"


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def olculen_pikseller(zip_csv, cift):
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
    if not wh:
        return None
    w, h = sorted(wh)
    sigan = []
    for giris in BOYUT_MERDIVENI[oran]:
        if oran == "A":
            ad, iw, ih = giris
        else:
            iw, ih = giris
            ad = f"{iw:g}x{ih:g} in"
        # 300 DPI'da gereken piksel, olculen pikseli asmamali (TOL_PX tolerans)
        if iw * DPI <= w + TOL_PX and ih * DPI <= h + TOL_PX:
            sigan.append(ad)
    return {"oran": oran, "piksel": f"{w}x{h}", "boyutlar": sigan,
            "inc": f"{w/DPI:.2f}x{h/DPI:.2f}"}


def boyut_bloku(olcum):
    satir, eksik = [], []
    for oran in ORAN_SIRA:
        b = boyut_satiri(oran, olcum.get(oran))
        (satir.append(b) if b else eksik.append(oran))
    return satir, eksik


def boyut_metni(boyutlar):
    if not boyutlar:
        return "OLCUM BEKLENIYOR"
    sat = []
    for b in boyutlar:
        if not b["boyutlar"]:
            sat.append(f"{b['oran']} ratio, {b['piksel']} px, up to {b['inc']} in at 300 DPI")
            continue
        en_buyuk = b["boyutlar"][-1]
        digerleri = ", ".join(b["boyutlar"][:-1])
        sat.append(f"{b['oran']} ratio, {b['piksel']} px, prints up to {en_buyuk} at 300 DPI"
                   + (f" (also {digerleri})" if digerleri else ""))
    return "\n".join(sat)


def en_aciklama(c, boyutlar, pod_id):
    ed = "\n".join(f"{i+1}. {e}" for i, e in enumerate(EDISYONLAR))
    pod = (f"{POD_BASLIK}\nThe same design is also available as a museum quality giclee print, "
           f"made to order and shipped unframed:\nhttps://www.etsy.com/listing/{pod_id}\n\n"
           if pod_id else "")
    return f"""{c['acilis']}

Instant digital download. Print it at home, at a local print shop, or with an online printing service.

* WHAT MAKES THIS LISTING DIFFERENT
5 Colors in one purchase. You receive every color edition of this design, not just one:
{ed}

* WHAT YOU RECEIVE
5 ZIP files, one per color edition. Every ZIP holds the same set:
5 high resolution JPG files, one for each print ratio
Ratios 2:3, 3:4, 4:5, 11:14 and A series
Full artwork in every ratio, nothing cropped
300 DPI, sRGB
A Print and Care Guide PDF
A thank you note from us

* PRINT SIZES IN EVERY ZIP
{boyut_metni(boyutlar)}

* HOW TO DOWNLOAD
After Etsy confirms your payment, open Etsy on a computer or a mobile browser and go to Your account, then Purchases and reviews. Open this order and download all 5 ZIP files. Extract the edition you want to print, then pick the JPG that matches your print size. Ask your printer to print without cropping, and read the Print and Care Guide first.

{pod}* GOOD TO KNOW
This is a digital file, so nothing is shipped to you. Props in the mockup photos are for display only.
This is decorative wall art, not a compatibility reading and not a birth chart.
Names, dates, quotes and color changes are not offered.
Colors may vary between your screen and the final print, depending on your printer, ink and paper.

* LICENSE
Your purchase is for personal use. Print it as often as you like for your own home or as a gift. Copyright stays with AstroLove: resale, redistribution and commercial use are not permitted.

Central composite symbol and original composition, copyright 2026 AstroLove.

ASTROLOVE
The Shape of Your Connection"""


def ru_aciklama(c, boyutlar, pod_id):
    a, b = RU_BURC.get(c["a"], c["a"]), RU_BURC.get(c["b"], c["b"])
    ed = "\n".join(f"{i+1}. {RU_EDISYON[e]}" for i, e in enumerate(EDISYONLAR))
    ikili = f"{a} и {b}"
    pod = (f"{POD_BASLIK_RU}\nТот же дизайн доступен как жикле принт музейного качества, "
           f"печать на заказ, доставка без рамы:\nhttps://www.etsy.com/listing/{pod_id}\n\n"
           if pod_id else "")
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
Записка с благодарностью от нас

РАЗМЕРЫ ПЕЧАТИ В КАЖДОМ АРХИВЕ:
{boyut_metni(boyutlar)}

КАК ЭТО РАБОТАЕТ:
После подтверждения оплаты откройте Etsy на компьютере или в мобильном браузере, раздел «Ваш аккаунт», затем «Покупки и отзывы». Скачайте все 5 архивов, распакуйте нужную версию и выберите файл JPG под ваш размер печати. Просите печать без обрезки.

{pod}ОБРАТИТЕ ВНИМАНИЕ:
Это цифровой файл, физическая посылка не отправляется. Реквизит на фотографиях служит только для показа.
Это декоративный постер, а не разбор совместимости и не натальная карта.
Имена, даты, цитаты и смена цвета не предлагаются.
Цвета на экране и в печати могут отличаться в зависимости от принтера, чернил и бумаги.

ЛИЦЕНЗИЯ:
Покупка для личного использования. Печатайте сколько угодно для своего дома или в подарок. Авторские права остаются за AstroLove: перепродажа и коммерческое использование не разрешены."""


def qc(c, baslik, etiketler, en, ru, boyutlar, pod_id):
    h = []
    burclar = {c["a"], c["b"]}
    for burc in burclar:
        n = len(re.findall(rf"\b{burc}\b", baslik))
        if n == 0:
            h.append(f"baslikta '{burc}' yok")
        if n > 2:
            h.append(f"baslikta '{burc}' {n} kez geciyor (anahtar kelime tekrari)")
    if c["a"] == c["b"] and len(re.findall(rf"\b{c['a']}\b", baslik)) < 2:
        h.append(f"ayni burc ciftinde '{c['a']}' baslikta 2 kez gecmeli")
    if re.search(r"Sign and .* Sign", baslik):
        h.append("baslikta 'Sign and ... Sign' tekrari var")
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
    cift_etiket = f"{c['a'].lower()} and {c['b'].lower()}"
    if cift_etiket not in etiketler:
        h.append(f"cift etiketi '{cift_etiket}' yok")
    for zorunlu in ("zodiac gift", "celestial wall art"):
        if zorunlu not in etiketler:
            h.append(f"zorunlu etiket yok: '{zorunlu}'")
    for burc in burclar:
        bl = burc.lower()
        for kalip in (f"{bl} zodiac", f"{bl} sign", f"{bl} star sign"):
            if kalip not in etiketler:
                h.append(f"tek burc etiketi eksik: '{kalip}'")
    if UZUN_TIRE.search(baslik) or UZUN_TIRE.search(en):
        h.append("Ingilizce metinde uzun tire (em/en dash) var")
    for metin, ad in ((baslik, "baslik"), (en, "EN aciklama"), (ru, "RU aciklama")):
        if STUDIO.search(metin):
            h.append(f"{ad}: 'studio' gecmemeli -> '{STUDIO.search(metin).group(0)}'")
        if COLOUR.search(metin):
            h.append(f"{ad}: Ingiliz yazimi 'colour' var")
        for rx, etiket in YASAK:
            for m in re.finditer(rx, metin, re.I):
                if OLUMSUZ.search(metin[max(0, m.start() - 40):m.start()]):
                    continue
                h.append(f"{ad}: yasak ifade ({etiket}) -> '{m.group(0)}'")
    for e in EDISYONLAR:
        if e not in en:
            h.append(f"aciklamada edisyon adi yok: {e}")
    if "A thank you note from us" not in en:
        h.append("EN'de 'A thank you note from us' satiri yok")
    if pod_id:
        for metin, ad, bas in ((en, "EN", POD_BASLIK), (ru, "RU", POD_BASLIK_RU)):
            if bas not in metin:
                h.append(f"{ad} aciklamada '{bas}' bolumu yok")
            elif f"listing/{pod_id}" not in metin:
                h.append(f"{ad} POD bolumunde {pod_id} linki yok")
            else:
                blok = metin.split(bas, 1)[1].split("\n\n", 1)[0]
                if re.search(r"\$|USD|\d+\.\d{2}", blok):
                    h.append(f"{ad} POD bolumunde fiyat var")
    else:
        h.append("POD ilan no bulunamadi, 'PREFER A PRINTED POSTER' bolumu yazilamadi")
    beklenen = {"2:3": "24x36 in", "3:4": "24x32 in", "4:5": "24x30 in",
                "11:14": "22x28 in", "A": "A0"}
    for b in boyutlar:
        if b["boyutlar"] and b["boyutlar"][-1] != beklenen.get(b["oran"]):
            h.append(f"{b['oran']} en buyuk boyut '{b['boyutlar'][-1]}', "
                     f"beklenen '{beklenen.get(b['oran'])}' ({b['piksel']} px)")
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip-csv", default="")
    ap.add_argument("--pod-json", default="", help="KALACAK_V2_OZET.json (pod_cift eslemesi)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    pod_cift = {}
    if a.pod_json and Path(a.pod_json).exists():
        pod_cift = (json.loads(Path(a.pod_json).read_text(encoding="utf-8")) or {}).get("pod_cift", {})

    md = [f"# METIN TASLAKLARI v2 - 3 CIFT ({simdi()} UTC)", "",
          "Taslaktir. Etsy'ye YAZILMADI. Onay sonrasi uygulanir.", "",
          "v2 duzeltmeleri: \"studio\" kelimesi hicbir metinde yok; Amerikan yazimi \"color\";",
          "basilabilir boyutlar olculen piksellerden turetildi (3:4 -> 24x32 in, A -> A0);",
          "cift etiketi \"X and Y\"; \"zodiac gift\" ve \"celestial wall art\" her sette;",
          "baslikta anahtar kelime tekrari yok; \"PREFER A PRINTED POSTER?\" bolumu eklendi.", ""]
    tum_hata, eksik_olcum = [], []

    for c in CIFTLER:
        olcum = olculen_pikseller(a.zip_csv, c["anahtar"]) if a.zip_csv else {}
        boyutlar, eksik = boyut_bloku(olcum)
        if eksik:
            eksik_olcum.append(f"{c['anahtar']}: {', '.join(eksik)}")
        baslik = BASLIK_KALIP.format(a=c["a"], b=c["b"])
        etiketler = c["etiketler"]
        pod_id = pod_cift.get(c["anahtar"], "")
        en = en_aciklama(c, boyutlar, pod_id)
        ru = ru_aciklama(c, boyutlar, pod_id)
        hatalar = qc(c, baslik, etiketler, en, ru, boyutlar, pod_id)
        tum_hata += [f"{c['anahtar']}: {x}" for x in hatalar]

        eski = V1_ETIKET.get(c["anahtar"], [])
        cikan = [t for t in eski if t not in etiketler]
        giren = [t for t in etiketler if t not in eski]

        md += [f"## {c['a']} + {c['b']}", "",
               f"### Baslik ({len(baslik)} karakter)", "", "```", baslik, "```", "",
               "### 13 etiket", "", "| # | etiket | karakter |", "|---:|---|---:|"]
        for i, t in enumerate(etiketler, 1):
            md.append(f"| {i} | {t} | {len(t)} |")
        md += ["", f"**v1'den cikarilan:** {', '.join(cikan) if cikan else '(yok)'}",
               f"**v2'de eklenen:** {', '.join(giren) if giren else '(yok)'}", "",
               f"### Aciklama (EN)  [POD ilani: {pod_id or 'BULUNAMADI'}]", "", "```", en, "```", "",
               "### Aciklama (RU taslak)", "", "```", ru, "```", "",
               f"### QC: {'PASS' if not hatalar else 'FAIL'}", ""]
        md += ([f"- {x}" for x in hatalar] if hatalar else ["- Tum kurallar saglandi."])
        md.append("")

    md += ["## Olcum notu", "",
           "- Basilabilir boyutlar ZIP_KONTROL.csv'deki OLCULEN piksellerden 300 DPI ile "
           "turetildi, tahmin edilmedi.",
           "- Beklenen ust uclar: 2:3 -> 24x36 in, 3:4 -> 24x32 in, 4:5 -> 24x30 in, "
           "11:14 -> 22x28 in, A -> A0. QC bunu dogrular."]
    if eksik_olcum:
        md += ["- OLCUM EKSIK:"] + [f"  - {x}" for x in eksik_olcum]
    md += ["", f"## GENEL QC: {'PASS' if not tum_hata else 'FAIL'}", ""]
    md += ([f"- {x}" for x in tum_hata] if tum_hata else ["- 3/3 cift kurallara uygun."])
    (out / "METIN_TASLAK_v2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(("PASS" if not tum_hata else "FAIL") + f" | {len(CIFTLER)} cift | hata {len(tum_hata)}",
          flush=True)
    for x in tum_hata:
        print("  - " + x, flush=True)
    sys.exit(1 if tum_hata else 0)


if __name__ == "__main__":
    main()
