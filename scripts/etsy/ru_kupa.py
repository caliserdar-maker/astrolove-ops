#!/usr/bin/env python3
"""Kupa (Orchard, 78 ilan) RU aciklamasini canli EN aciklamadan kurar (Serdar 31 Eki karar 3b). ETSY YOK; yazim bu dosyada YOK.
Yapi poster kurucusuyla ayni (ru_poster.py, Serdar 23 Eki sablon yontemi): EN'deki HER paragraf bilinen bir kalibin birebir
karsiligi olmali; kalip disi paragraf ya da beklenmeyen deger = FAIL (eksik / fazla bilgi uretilmez). Degiskenler EN'den alinir
(burclar, giris kuyrugu, foto numaralari, isim / mesaj siniri, bos mesajda basilan metin).
Kaynak: kupa-orchard dali kupa_orchard/kod/ilan_metin.py (EN sablonu) + ilan_metin_ru.py (19 Eki RU sablonu); RU cumleler EN ile
birebir ayni bilgiyi verecek sekilde duzeltildi (19 Eki RU'da EN'de olmayan "перед оформлением заказа" yok; EN'deki "A thoughtful
choice..." cumlesinin karsiligi var).
GALERI (Serdar 31 Eki 5a / 6a, 2a): kupa_en canli EN'deki foto numaralarini GORSEL ADIYLA degistirir (stil / boyut / kisisellestirme
fotografi; numara yok, Etsy videoyu 2. siraya koyuyor)
ve kisisellestirme bolumune sade kupa Latin harf notunu ekler; ru_kupa_78 hedef_kapisi ile denetler.
AYNI BURC (12 cift, Serdar 30 Eki): isim satirlari "First Name" / "Second Name". kupa_en() canli EN'deki "Left name" / "Right name"
ya da "Name Under <Burc>" ciftini bu ada cevirir (hedef EN); farkli burcta EN degismez. EN degisikligi de Serdar onayina tabidir.
kur(en) -> (ru, kontrol: dict(pass_, hata, paragraf_en, paragraf_ru)). Yasak ifade etsy_common.RU_YASAK (RU yazim kapisiyla ayni)."""
import html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
from beyan_marka_yaz import BEYAN, RU_BEYAN  # noqa: E402  tek kaynak (beyan kupada da 1. paragraftan sonra)
from ru_poster import BURC, DATIF  # noqa: E402  burc adlari ve datif tek kaynak

B_RX = "(" + "|".join(BURC) + ")"
KUYRUK = re.compile(r"(?:an? )?" + B_RX + r" gifts?(?: or (?:an? )?" + B_RX + r" gifts?)?")
AYNI_EN = ("First Name", "Second Name")
ISIM_RU = {"Left name": "Имя слева", "Right name": "Имя справа", "First Name": "Первое имя", "Second Name": "Второе имя"}


FOTO_AD_RU = {"the style photos": "фото стилей", "the sizes photo": "фото с размерами",
              "the names and message photo": "фото с именами и надписью"}   # Serdar 31 Eki 2a: numara yok, gorsel adi
FOTO_BOLUM = {"stil": "the style photos", "boy": "the sizes photo", "kisisel": "the names and message photo"}


def foto_ru(s, bolum):
    """EN 'See <s>.' nesnesi -> RU nesnesi. Yalniz o bolumun gorsel adi kabul edilir (Serdar 31 Eki 2a; inceleme 31 Eki: numarali atif ya da
    baska bolumun adi FAIL, kur kurali kendisi uygular)."""
    if s != FOTO_BOLUM[bolum]:
        raise ValueError(f"foto atfi {bolum}: {s!r} (beklenen {FOTO_BOLUM[bolum]!r}; foto numarasi yok, Serdar 31 Eki 2a)")
    return FOTO_AD_RU[s]


def cogul(n, bir, iki, bes):
    """Rusca sayi ile isim uyumu: 1 буква, 2-4 буквы, 5+ букв (11-14 букв)."""
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return bir
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return iki
    return bes


def ikili(a, b):
    return f"«{BURC[a]}» и «{BURC[b]}»"


def p_giris(m, ctx):
    a, b, kuyruk = m.group(1), m.group(2), m.group(3)
    ctx["burc"] = (a, b)
    s = (f"Именная кружка для пары со знаками зодиака {ikili(a, b)}: ваши два знака зодиака объединяются в один оригинальный "
         f"символ, с вашими именами и вашей надписью. Кофейная кружка на заказ и персональный подарок для пары, созданный "
         f"специально для вас двоих.")
    if kuyruk is None:
        return s
    k = KUYRUK.fullmatch(kuyruk)
    if not k:
        raise ValueError(f"giris kuyrugu kalip disi: {kuyruk!r}")
    ad = [x for x in k.groups() if x]
    if set(ad) - {a, b}:
        raise ValueError(f"giris kuyrugu burclari {ad}")
    return s + f" Удачный выбор, если вы ищете подарок {' или '.join(dict.fromkeys(DATIF[x] for x in ad))}."


def p_stil(m, ctx):
    a, b = m.group(1), m.group(2)
    if ctx.get("burc") and (a, b) != ctx["burc"]:
        raise ValueError("stil paragrafi burclari girisle ayni degil")
    return ("[ 8 СТИЛЕЙ: THE ORCHARD WE KEEP ]\nOrange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, "
            "Lemon Grove, Blue Grape или Golden Loquat. Во всех стилях этой зодиакальной кружки для пары один и тот же символ знаков "
            f"{ikili(a, b)} и турецкий глаз на обратной стороне. Смотрите {foto_ru(m.group(3), 'stil')}.")


def p_boy(m, ctx):
    return ("[ ДВА РАЗМЕРА ]\n- 11 oz (325 мл)\n- 15 oz (444 мл)\nОдинаковый дизайн в обоих размерах. "
            f"Смотрите {foto_ru(m.group(1), 'boy')}.")


def isim_ru(s, ctx, sira):
    if not ctx.get("burc"):
        raise ValueError("isim satiri: giris paragrafi (burclar) once gelmeli")
    a, b = ctx["burc"]
    hedef = a if sira == 1 else b
    m = re.fullmatch(r"Name (for|Under) " + B_RX, s)
    if m:
        if m.group(2) != hedef:
            raise ValueError(f"{sira}. isim satiri burcu {m.group(2)} != {hedef}")
        return f"Имя для знака «{BURC[hedef]}»" if m.group(1) == "for" else f"Имя под знаком «{BURC[hedef]}»"
    beklenen = {1: ("Left name", "First Name"), 2: ("Right name", "Second Name")}[sira]
    if s not in beklenen:
        raise ValueError(f"{sira}. isim satiri kalip disi: {s!r}")
    if a != b:
        raise ValueError(f"farkli burcta {s!r} (ayni burc adi)")
    return ISIM_RU[s]


LATIN_EN = "Please use Latin letters, numbers and simple punctuation, no emoji."   # sade kupa metni (kupa-orchard 1ed1122)
LATIN_RU = "Пожалуйста, используйте латинские буквы, цифры и простые знаки препинания, без эмодзи."
# Yeni galeri sirasi (Serdar 31 Eki karar 5a; kupa_kart78 / kupa_galeri78): 1 kapak, 2 K02 sembol, 3 K03 kisisellestirme, 4 K05 boyut,
# 5 K07 surec, 6 K04 stil genel bakis, 7-14 stil gorselleri, video. Eski canli numaralar -> yeni.
# Serdar 31 Eki 2a: aciklamada foto NUMARASI yok (Etsy videoyu 2. siraya koyuyor, numara kayar); gorsel adiyla atif.
FOTO_YENI = {"stil": ("an evil eye on the back. See photo 4.", "an evil eye on the back. See the style photos."),
             "boy": ("Same design on both. See photo 5.", "Same design on both. See the sizes photo."),
             "kisisel": ("Please check your spelling. See photos 3 and 6.", "Please check your spelling. See the names and message photo.")}


def p_kisisel(m, ctx):
    i1, n1, i2, n2, msj, latin, bos, foto = m.groups()
    if n1 != n2:
        raise ValueError(f"isim sinirlari farkli {n1} / {n2}")
    if not re.fullmatch(r"[A-Za-z][A-Za-z ,.'!&]*", bos) or len(bos) > int(msj):
        raise ValueError(f"bos mesaj metni kalip disi ya da {msj} karakterden uzun: {bos!r}")
    ctx.update(isim=int(n1), mesaj=int(msj))
    return ("[ КАК ПЕРСОНАЛИЗИРОВАТЬ ]\nНапишите три строки в поле персонализации:\n"
            f"1. {isim_ru(i1, ctx, 1)} (до {n1} {cogul(n1, 'буквы', 'букв', 'букв')})\n"
            f"2. {isim_ru(i2, ctx, 2)} (до {n2} {cogul(n2, 'буквы', 'букв', 'букв')})\n"
            f"3. Надпись (одна строка, до {msj} {cogul(msj, 'символа', 'символов', 'символов')}, включая пробелы и знаки препинания)\n"
            + (f"{LATIN_RU}\n" if latin else "") +
            "Если вы оставите надпись пустой, мы напечатаем:\n"
            f"{bos}\n"
            f"Пожалуйста, проверьте написание. Смотрите {foto_ru(foto, 'kisisel')}.")


SABIT = {
    BEYAN: RU_BEYAN,
    "[ A GIFT FOR COUPLES ]\nA wedding gift for couples who love astrology, an engagement gift for couples, an anniversary surprise "
    "or a newlywed gift. A zodiac gift for every morning.":
        "[ ПОДАРОК ДЛЯ ПАРЫ ]\nПодарок на свадьбу для пары, которая любит астрологию, подарок на помолвку для пары, сюрприз на "
        "годовщину или подарок молодожёнам. Зодиакальный подарок на каждое утро.",
    "[ WHAT YOU GET ]\nOne mug, printed on both sides. The cover shows its front and back.\nFront: the fusion symbol, two small zodiac "
    "signs, your names in capitals joined by ∞, and your zodiac sign names.\nBack: your message in italics, your names and a small "
    "nazar (evil eye).":
        "[ ЧТО ВЫ ПОЛУЧИТЕ ]\nОдна кружка с печатью с двух сторон. На главном фото показаны её лицевая и обратная стороны.\n"
        "Лицевая сторона: объединённый символ, два небольших знака зодиака, ваши имена заглавными буквами, соединённые знаком ∞, "
        "и названия ваших знаков зодиака.\nОбратная сторона: ваша надпись курсивом, ваши имена и небольшой назар (турецкий глаз).",
        # Serdar 31 Eki 2: yeni kapak yalniz on yuz -> "The cover shows its front and back." hedef EN'den CIKAR (RU karsiligi da)
    "[ WHAT YOU GET ]\nOne mug, printed on both sides.\nFront: the fusion symbol, two small zodiac "
    "signs, your names in capitals joined by ∞, and your zodiac sign names.\nBack: your message in italics, your names and a small "
    "nazar (evil eye).":
        "[ ЧТО ВЫ ПОЛУЧИТЕ ]\nОдна кружка с печатью с двух сторон.\n"
        "Лицевая сторона: объединённый символ, два небольших знака зодиака, ваши имена заглавными буквами, соединённые знаком ∞, "
        "и названия ваших знаков зодиака.\nОбратная сторона: ваша надпись курсивом, ваши имена и небольшой назар (турецкий глаз).",
"[ DETAILS ]\n- Glossy white ceramic, white inside\n- Dishwasher and microwave safe\n- Made to order, just for you\n- Original "
    "zodiac fusion symbols designed by AstroLoveArt":
        "[ ХАРАКТЕРИСТИКИ ]\n- Глянцевая белая керамика, белая внутри\n- Можно мыть в посудомоечной машине и использовать в "
        "микроволновой печи\n- Изготавливаем на заказ, специально для вас\n- Оригинальные объединённые символы зодиака, созданные "
        "AstroLoveArt",
    "[ RETURNS ]\nEvery mug is personalized, so we can't accept returns or exchanges for a change of mind. If your mug arrives "
    "damaged, send us a photo within 7 days of delivery and we'll replace it at no cost.":
        "[ ВОЗВРАТ И ОБМЕН ]\nКаждая кружка персонализирована, поэтому мы не принимаем возврат или обмен, если вы передумали. "
        "Если кружка пришла повреждённой, пришлите нам фото в течение 7 дней с момента доставки, и мы бесплатно заменим её.",
    "Questions? Send us a message, we're happy to help.": "Есть вопросы? Напишите нам, мы будем рады помочь.",
}

BN = "(?:" + "|".join(BURC) + ")"
ISIM_RX = r"(Name for " + BN + r"|Name Under " + BN + r"|Left name|Right name|First Name|Second Name)"
KALIP = [
    (re.compile(r"A personalized mug for " + B_RX + " and " + B_RX + r" couples: your two zodiac symbols join into one original "
                r"fusion symbol, with your names and your message\. A custom coffee mug and personalized couple gift made just for "
                r"the two of you\.(?: A thoughtful choice when you are looking for (.+)\.)?"), p_giris),
    (re.compile(r"\[ 8 STYLES: THE ORCHARD WE KEEP \]\nOrange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, "
                r"Lemon Grove, Blue Grape or Golden Loquat\. Every style of this zodiac couple mug has the same " + B_RX + " and "
                + B_RX + r" symbol and an evil eye on the back\. See (photos? [\d a-z]+|the [a-z]+(?: [a-z]+)* photos?)\."), p_stil),
    (re.compile(r"\[ TWO SIZES \]\n- 11 oz \(325 ml\)\n- 15 oz \(444 ml\)\nSame design on both\. See (photos? [\d a-z]+|the [a-z]+(?: [a-z]+)* photos?)\."), p_boy),
    (re.compile(r"\[ HOW TO PERSONALIZE \]\nWrite three lines in the personalization box:\n1\. " + ISIM_RX + r" \(up to (\d+) "
                r"letters\)\n2\. " + ISIM_RX + r" \(up to (\d+) letters\)\n3\. Message \(one line, up to (\d+) characters including "
                r"spaces and punctuation\)\n(" + re.escape(LATIN_EN) + r"\n)?Leave the message blank and we print:\n([^\n]+)\nPlease check your spelling\. See "
                r"(photos? [\d a-z]+|the [a-z]+(?: [a-z]+)* photos?)\."), p_kisisel),
]


def norm(s):
    return html.unescape(s or "").replace("\r\n", "\n").strip()


KAPAK_EN = " The cover shows its front and back."         # Serdar 31 Eki 2: hedef EN'de YOK (yeni kapak yalniz on yuz)


def galeri_en(d):
    """Serdar 31 Eki 5a + 6a + 2a: foto atiflari gorsel adiyla (numara yok), kisisellestirme bolumune Latin harf notu. Idempotan.
    -> (en, degisen[]) ; eski / yeni kalip tam 1 kez bulunmazsa ValueError."""
    deg = []
    for ad, (eski, yeni) in FOTO_YENI.items():
        if d.count(yeni) == 1 and d.count(eski) == 0:
            continue
        if d.count(eski) != 1:
            raise ValueError(f"foto {ad}: eski kalip {d.count(eski)} kez, yeni {d.count(yeni)} kez")
        d = d.replace(eski, yeni); deg.append(f"foto_{ad}")
    if d.count(KAPAK_EN) > 1:
        raise ValueError("kapak cumlesi birden cok")
    if KAPAK_EN in d:                                       # Serdar 31 Eki 2: yeni kapak yalniz on yuz
        d = d.replace(KAPAK_EN, ""); deg.append("kapak")
    capa = " characters including spaces and punctuation)\nLeave the message blank and we print:"
    if LATIN_EN not in d:   # inceleme 31 Eki: not mesaj satirindan hemen sonra (bos mesaj metniyle karismasin)
        if d.count(capa) != 1:
            raise ValueError("Latin notu capasi bulunamadi")
        d = d.replace(capa, capa.replace("\nLeave", "\n" + LATIN_EN + "\nLeave")); deg.append("latin")
    return d, deg


def hedef_kapisi(en):
    """Hedef EN'de 3 gorsel adi atfi (numara yok, Serdar 31 Eki 2a) + tek Latin notu var, eski numarali atif yok."""
    h = [f"foto {ad}: yeni '{y}' yok" for ad, (e, y) in FOTO_YENI.items() if en.count(y) != 1]
    h += [f"foto {ad}: eski '{e}' kaldi" for ad, (e, y) in FOTO_YENI.items() if e in en]
    if en.count(LATIN_EN) != 1:
        h.append("Latin harf notu yok / birden cok")
    if KAPAK_EN.strip() in en:
        h.append("kapak cumlesi kaldi (Serdar 31 Eki 2: yeni kapak yalniz on yuz)")
    ref = re.findall(r"See (photos? [\d a-z]+|the [a-z]+(?: [a-z]+)* photos?)\.", en)
    if len(ref) != 3:
        h.append(f"'See ...' foto atfi {len(ref)} (3 beklenir)")
    if any(re.search(r"\d", r) or r not in FOTO_AD_RU for r in ref):
        h.append(f"foto numarasi / bilinmeyen atif kaldi (Serdar 31 Eki 2a: numara yok): {ref}")
    return h


def kupa_en(desc, a, b):
    """Hedef EN: galeri_en (foto numaralari + Latin notu, 31 Eki) + ayni burcta isim satirlari First Name / Second Name (30 Eki).
    -> (en, durum DEGISTI | AYNI | YOK); DEGISTI/AYNI yalniz isim satiri icin."""
    d, _ = galeri_en(norm(desc))
    if a != b:
        return d, "AYNI"
    if AYNI_EN[0] in d and AYNI_EN[1] in d:
        return d, "AYNI"
    for x, y in (("Left name", "Right name"), (f"Name Under {a}", f"Name Under {a}"), (f"Name for {a}", f"Name for {a}")):
        rx = re.compile(r"(\n1\. )" + re.escape(x) + r"( \(up to \d+ letters\)\n2\. )" + re.escape(y) + r"( \(up to)")
        if len(rx.findall(d)) == 1:
            return rx.sub(lambda m: m.group(1) + AYNI_EN[0] + m.group(2) + AYNI_EN[1] + m.group(3), d), "DEGISTI"
    return d, "YOK"


def kur(en):
    d = norm(en)
    par = [p.strip() for p in d.split("\n\n") if p.strip()]
    ctx, ru, hata = {}, [], []
    tekrar = sorted({p[:40] for p in par if par.count(p) > 1})
    if tekrar:
        hata.append(f"tekrarlanan paragraf: {tekrar}")
    for i, p in enumerate(par, 1):
        if p in SABIT:
            ru.append(SABIT[p]); continue
        for rx, f in KALIP:
            m = rx.fullmatch(p)
            if m:
                try:
                    ru.append(f(m, ctx))
                except ValueError as e:
                    hata.append(f"paragraf {i}: {e}")
                break
        else:
            hata.append(f"paragraf {i} kalip disi: {p[:80]!r}")
    a, b = ctx.get("burc") or (None, None)
    if a and a == b and not all(x in d for x in AYNI_EN):
        hata.append("ayni burc: EN isim satirlari First Name / Second Name degil (once kupa_en)")
    gerekli = {"[ A GIFT FOR COUPLES ]", "[ WHAT YOU GET ]", "[ 8 STYLES", "[ TWO SIZES ]", "[ HOW TO PERSONALIZE ]", "[ DETAILS ]",
               "[ RETURNS ]"}
    eksik = sorted(g for g in gerekli if not any(p.startswith(g) for p in par))
    if eksik:
        hata.append(f"EN'de bolum yok: {eksik}")
    out = "\n\n".join(ru)
    if re.search("[—–―‒−]", out):
        hata.append("RU'da uzun/orta tire")
    yasak = sorted({m.group(0) for m in E.RU_YASAK.finditer(out)})
    if yasak:
        hata.append(f"RU'da yasak ifade: {yasak}")
    if re.search(r"[{}]|lena|serdar", out, re.I):
        hata.append("RU'da yer tutucu / kisi adi")
    return out, dict(pass_=not hata and len(ru) == len(par), hata=hata, paragraf_en=len(par), paragraf_ru=len(ru), burc=[a, b])
