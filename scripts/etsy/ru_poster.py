#!/usr/bin/env python3
"""Poster RU aciklamasini canli EN aciklamadan + envanterden kurar (Serdar 23 Eki: sablon yontemi onayli; eski RU kullanilmaz).
Kural: EN'deki HER paragraf bilinen bir kalibin birebir karsiligi olmali; kalip disi paragraf ya da beklenmeyen deger = FAIL
(eksik / fazla bilgi uretilmez). Degiskenler EN'den (burc, tarih, isim/mesaj siniri, renk sayisi, mesaj ornekleri, boy araligi)
ve envanterden (boy sayisi) alinir. Kagit / tedarikci yalniz EN'deki gibi (Hahnemuhle, Prodigi vb. yok; CLAUDE.md 23 Eki).
kur(en, envanter) -> (ru, kontrol: dict(pass_, hata, paragraf_en, paragraf_ru))."""
import html
import pathlib
import re
import sys

BURC = {"Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы", "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
        "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец", "Capricorn": "Козерог", "Aquarius": "Водолей",
        "Pisces": "Рыбы"}
AY = {"January": "января", "February": "февраля", "March": "марта", "April": "апреля", "May": "мая", "June": "июня",
      "July": "июля", "August": "августа", "September": "сентября", "October": "октября", "November": "ноября",
      "December": "декабря"}
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beyan_marka_yaz import BEYAN, RU_BEYAN  # noqa: E402  tek kaynak
import etsy_common as E  # noqa: E402
# Serdar 23 Eki (madde 1, ikinci karar): not yalniz isim icin. Isim fontu Cinzel Kiril basamaz (0/64); mesaj fontu EB Garamond
# Italic Kiril basar ve siparis karti Kiril mesaji kabul eder, bu yuzden mesaja kisit yok. Aksan cumlesi yok: siparis-dijital
# isim kontrolu (siparis-dijital.yml:147/:213) aksanli ismi reddediyor (inceleme 23 Eki; destek ayri onayla, PLAN.md).
LATIN_EN = "Names must use English letters."
LATIN_RU = "Имена должны быть написаны английскими буквами."
LATIN_CAPA = "No emoji. Please check your spelling."


def poster_en(desc):
    """Poster yeni EN: canli EN + beyan (beyan_marka_yaz.en_plan) + Latin harf notu (kisisellestirme satirinda, 'No emoji.' sonrasi).
    Not zaten varsa degismez; capa tam 1 kez degilse ValueError."""
    import beyan_marka_yaz as B
    d = B.norm(desc)
    en = B.en_plan(d, "poster")[0] or d
    if LATIN_EN in en:
        return en
    if en.count(LATIN_CAPA) != 1:
        raise ValueError(f"Latin notu capasi {en.count(LATIN_CAPA)} kez (1 olmali)")
    return en.replace(LATIN_CAPA, f"No emoji. {LATIN_EN} Please check your spelling.")


DATIF = {"Aries": "Овну", "Taurus": "Тельцу", "Gemini": "Близнецам", "Cancer": "Раку", "Leo": "Льву", "Virgo": "Деве",
         "Libra": "Весам", "Scorpio": "Скорпиону", "Sagittarius": "Стрельцу", "Capricorn": "Козерогу", "Aquarius": "Водолею",
         "Pisces": "Рыбам"}
YASAK_RU = E.RU_YASAK   # tek kaynak etsy_common (inceleme 23 Eki: genisletildi; madde 4 merkezi RU kapisi)
B_RX = "(" + "|".join(BURC) + ")"


def cift(a, b):
    return f"{BURC[a]} и {BURC[b]}"


def boy_ru(s):
    return s.replace(" x ", " × ")


KUYRUK = re.compile(r"(?:an? )?" + B_RX + r" gifts?(?: or (?:an? )?" + B_RX + r" gifts?)?")   # EN: "an Aries gift", "Cancer gifts or a Leo gift"


def p_giris(m, ctx):
    a, b, kuyruk = m.group(1), m.group(2), m.group(3)
    k = KUYRUK.fullmatch(kuyruk)   # inceleme 23 Eki O1: kuyrukta burc disi bilgi varsa FAIL (sessizce atilmaz)
    if not k:
        raise ValueError(f"giris kuyrugu kalip disi: {kuyruk!r}")
    ad = [x for x in k.groups() if x]
    if set(ad) - {a, b}:
        raise ValueError(f"giris kuyrugu burclari {ad}")
    ctx["burc"] = (a, b)
    secim = " или ".join(dict.fromkeys(DATIF[x] for x in ad))
    return (f"Именной постер для пары со знаками зодиака {cift(a, b)}, с вашими двумя именами и вашей собственной короткой надписью. Особенный "
            f"подарок молодожёнам или на первую годовщину. Наш оригинальный дизайн объединяет ваши два знака зодиака в один "
            f"общий символ, а ваши имена располагаются под двумя небольшими знаками. Выберите цифровой файл или напечатанный "
            f"постер. Особенный подарок на годовщину, помолвку, свадьбу, День святого Валентина и день рождения. Удачный "
            f"выбор, если вы ищете подарок {secim}.")


def p_tarih(m, ctx):
    parca = re.findall(B_RX + r": (\w+) (\d+) to (\w+) (\d+)\.", m.group(0))
    if not parca or any(x[1] not in AY or x[3] not in AY for x in parca):
        raise ValueError("tarih satiri")
    return " ".join(f"{BURC[b]}: с {g1} {AY[a1]} по {g2} {AY[a2]}." for b, a1, g1, a2, g2 in parca)


def p_siparis(m, ctx):
    renk, isim, mesaj, fikir = m.group(1), m.group(2), m.group(3), m.group(4)
    ctx.update(renk=int(renk), isim=int(isim), mesaj=int(mesaj))
    return ("КАК ЗАКАЗАТЬ\n"
            "1. Формат (Format): выберите Digital File (цифровой файл) или Print (постер).\n"
            f"2. Цвет (Primary color): выберите один из {renk} цветов.\n"
            "3. Размер (Size): выберите размер. Цифровой файл создаётся в выбранном вами цвете и размере.\n"
            "4. Персонализация: впишите два имени и вашу надпись.\n"
            f"Имена: до {isim} букв каждое, печатаются заглавными буквами. Надпись: до {mesaj} символов, печатается так, "
            f"как вы её напишете. Без эмодзи. {LATIN_RU} Пожалуйста, проверьте написание.\n"
            f"Идеи для надписи: {fikir}")


def uc_kontrol(ctx, k1, b1, a1, a2):
    """inceleme 23 Eki O6: EN'deki aralik uclari envanterde olmali."""
    env = set(ctx.get("boylar") or [])
    if env and {k1.replace(" ", ""), b1.replace(" ", ""), a1, a2} - env:
        raise ValueError(f"boy uclari envanterde yok: {k1}, {b1}, {a1}, {a2}")


# Teslim satiri (Serdar 26 Eki: dijitalde de ucretsiz onizleme, onaydan sonra e-posta). Eski satir geriye uyum icin kalir.
TESLIM_RU = {
    "Delivered to your Etsy order within 24 hours": "Файл приходит в ваш заказ на Etsy в течение 24 часов",
    "We send a free preview via Etsy Messages within 24 hours. After you approve, your file is emailed to you within 24 hours":
        "Мы бесплатно отправляем макет через сообщения Etsy в течение 24 часов. После вашего одобрения файл придёт вам на "
        "электронную почту в течение 24 часов",
}


# Indirme satiri (Serdar 28 Eki: dosya e-postayla; e-posta uygun degilse Etsy Messages'ta indirme baglantisi). Eski satir geriye uyum.
INDIR_RU = {
    "Download it from Purchases in a web browser. The Etsy app can't download files":
        "Скачайте его в разделе «Покупки» (Purchases) в браузере. В приложении Etsy файлы скачать нельзя",
    "If email doesn't suit you, we can send you a download link through Etsy Messages.":
        "Если вам неудобно получать файл по электронной почте, мы можем отправить ссылку для скачивания через сообщения Etsy.",
}


def p_dijital(m, ctx):
    k1, b1, a1, a2 = m.group(1), m.group(2), m.group(3), m.group(4)
    uc_kontrol(ctx, k1, b1, a1, a2)
    return ("ЦИФРОВОЙ ФАЙЛ\n"
            "- Один готовый к печати файл JPG в выбранном вами цвете и размере\n"
            f"- Высокое разрешение: 300 dpi в полном выбранном размере, от {boy_ru(k1)} до {boy_ru(b1)} дюймов или от {a1} до {a2}\n"
            f"- {TESLIM_RU[m.group(5)]}. Перед отправкой мы вручную проверяем каждую персонализацию\n"
            f"- {INDIR_RU[m.group(6)]}\n"
            "- Распечатайте его дома, в местной типографии или в онлайн-сервисе печати\n"
            "- Мы ничего не отправляем по почте. Только для личного использования.")


def p_boy(m, ctx):
    n, k1, b1, a1, a2 = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
    if ctx.get("sku_boy") is not None and n != ctx["sku_boy"]:
        raise ValueError(f"EN {n} boy, envanter {ctx['sku_boy']}")
    uc_kontrol(ctx, k1, b1, a1, a2)
    return (f"РАЗМЕРЫ\n{n} размеров: от {boy_ru(k1)} до {boy_ru(b1)} дюймов, а также от {a1} до {a2}. Каждый размер доступен "
            "в виде постера и цифрового файла. Смотрите фото с таблицей размеров.")


HEDIYE_RU = {   # Serdar 28 Eki: dijital onizleme + onaydan sonra; eski cumle geriye uyum
    "It arrives within 24 hours, ready to print or share.": "Он придёт в течение 24 часов, и его можно распечатать или переслать.",
    "Nothing to ship, so it is ready to print or share soon after you approve your preview.":
        "Его не нужно отправлять по почте, поэтому его можно распечатать или переслать вскоре после того, как вы одобрите макет.",
}


def p_hediye(m, ctx):
    a, b = m.group(1), m.group(2)
    if ctx.get("burc") and (a, b) != ctx["burc"]:
        raise ValueError("hediye burclari girisle ayni degil")
    return (f"ИДЕАЛЬНЫЙ ПОДАРОК\nПамятный подарок для пары со знаками {cift(a, b)}. Мало времени? Выберите цифровой файл. "
            + HEDIYE_RU[m.group(3)])


SABIT = {
    BEYAN: RU_BEYAN,
    "YOUR PREVIEW\nFor every print, we send you a preview via Etsy Messages within 24 hours of your order. We print as soon as you "
    "approve it. If we don't hear from you within 24 hours of receiving the preview, we print the design as shown.":
        "ВАШ МАКЕТ\nДля каждого заказа постера мы отправляем вам макет через сообщения Etsy в течение 24 часов после заказа. "
        "Мы печатаем сразу после того, как вы его одобрите. Если в течение 24 часов после получения макета мы не получим от вас "
        "ответа, мы напечатаем дизайн в том виде, в каком он показан на макете.",
    # Serdar 28 Eki: onizleme ve onay gelmezse cumleleri dijitali de kapsar (eski paragraf geriye uyum icin kalir)
    "YOUR PREVIEW\nWe send you a preview via Etsy Messages within 24 hours of your order. We print your poster or prepare your file "
    "as soon as you approve it. If we don't hear from you within 24 hours of receiving the preview, we go ahead with the design as "
    "shown: we print your poster, or send your digital file as a download link in Etsy Messages.":
        "ВАШ МАКЕТ\nМы отправляем вам макет через сообщения Etsy в течение 24 часов после заказа. Мы печатаем постер или готовим "
        "файл сразу после того, как вы одобрите макет. Если в течение 24 часов после получения макета мы не получим от вас ответа, "
        "мы продолжим работу с дизайном в том виде, в каком он показан на макете: напечатаем постер или отправим цифровой файл "
        "в виде ссылки для скачивания в сообщениях Etsy.",
    "PRINT\n- Printed on premium matte art paper with long-lasting inks\nFrames shown in photos are for display only and are not "
    "included. Prints ship unframed.":
        "ПЕЧАТЬ\n- Печать на премиальной матовой художественной бумаге стойкими чернилами\nРамы на фото показаны только для "
        "примера и в комплект не входят. Постеры отправляются без рамы.",
    "COLORS\nSee the color photo. The gold look is a printed color, not metallic foil or raised ink. Colors may vary slightly "
    "between screens and paper.":
        "ЦВЕТА\nСмотрите фото с цветами. Золотистый эффект создаётся при печати: это не металлическая фольга и не рельефная "
        "печать. Оттенки на экране и на бумаге могут немного отличаться.",
    "PRODUCTION AND DELIVERY\n- Made to order. Printed and shipped within 7 business days after you approve your preview.\n- US "
    "orders are printed in the US. US delivery usually takes 5 to 8 business days after shipping.\n- For other countries, please "
    "see the delivery estimate for your address.\n- US orders ship with tracking.":
        "ПРОИЗВОДСТВО И ДОСТАВКА\n- Изготавливаем на заказ. Печатаем и отправляем в течение 7 рабочих дней после того, как вы "
        "одобрите макет.\n- Заказы в США печатаются в США. Доставка по США обычно занимает от 5 до 8 рабочих дней после отправки.\n"
        "- Для других стран смотрите срок доставки, указанный для вашего адреса.\n- Заказы в США отправляются с трек-номером.",
    # Serdar 26 Eki: takip dogrulanmadi, "US orders ship with tracking." satiri kaldirildi (eski paragraf geriye uyum icin kalir)
    "PRODUCTION AND DELIVERY\n- Made to order. Printed and shipped within 7 business days after you approve your preview.\n- US "
    "orders are printed in the US. US delivery usually takes 5 to 8 business days after shipping.\n- For other countries, please "
    "see the delivery estimate for your address.":
        "ПРОИЗВОДСТВО И ДОСТАВКА\n- Изготавливаем на заказ. Печатаем и отправляем в течение 7 рабочих дней после того, как вы "
        "одобрите макет.\n- Заказы в США печатаются в США. Доставка по США обычно занимает от 5 до 8 рабочих дней после отправки.\n"
        "- Для других стран смотрите срок доставки, указанный для вашего адреса.",
    "PACKAGING\nPrints are rolled in tissue paper and sent in a thick cardboard tube. Small prints to Europe may come in a stiff "
    "flat envelope.":
        "УПАКОВКА\nПостеры сворачиваем в рулон, оборачиваем папиросной бумагой и отправляем в плотном картонном тубусе. "
        "Небольшие постеры в Европу могут прийти в жёстком плоском конверте.",
    "CHANGES\nNeed to change a name or the message? Just tell us before you approve your preview.":
        "ИЗМЕНЕНИЯ\nНужно изменить имя или надпись? Просто напишите нам до того, как одобрите макет.",
    "CARE\nKeep away from direct sunlight and damp rooms.":
        "УХОД\nНе размещайте под прямыми солнечными лучами и во влажных помещениях.",
    "RETURNS\nEvery item is personalized, so we can't accept returns or exchanges. Digital files can't be refunded once sent. If "
    "your print arrives damaged, send us a photo within 7 days and we'll replace it at no cost.":
        "ВОЗВРАТ\nКаждый товар персонализирован, поэтому мы не принимаем возвраты и обмены. Деньги за цифровые файлы после "
        "отправки не возвращаются. Если постер пришёл повреждённым, пришлите нам фото в течение 7 дней, и мы бесплатно заменим его.",
    "FAQ\nCan I order the digital file and a print together? Yes. Add each one to your cart as a separate item.\nHow large can I "
    "print the digital file? At the size you choose, at 300 dpi. The largest size is 24 x 36 inches.":
        "ВОПРОСЫ И ОТВЕТЫ\nМожно ли заказать цифровой файл и постер вместе? Да. Добавьте каждый из них в корзину отдельным "
        "товаром.\nНасколько крупно можно напечатать цифровой файл? В выбранном вами размере, с разрешением 300 dpi. Самый "
        "большой размер: 24 × 36 дюймов.",
}

KALIP = [
    (re.compile(r"Personalized " + B_RX + " and " + B_RX + r" couple wall art with your two names and your own short message, a "
                r"meaningful newlywed gift or 1st anniversary gift\. Our original design joins your two zodiac symbols into one "
                r"shared symbol, with your names under the two small signs\. Choose a digital file or a print\. A meaningful gift "
                r"for anniversaries, engagements, weddings, Valentine's Day and birthdays\. A thoughtful choice when you are "
                r"looking for (.+)\."), p_giris),
    (re.compile(r"(?:" + B_RX + r": \w+ \d+ to \w+ \d+\.\s?)+"), p_tarih),
    (re.compile(r"HOW TO ORDER\n1\. Format: choose Digital File or Print\.\n2\. Primary color: choose one of (\d+) colors\.\n"
                r"3\. Size: choose your size\. Your digital file is made in the color and size you choose\.\n4\. Personalization: "
                r"type the two names and your message\.\nNames: up to (\d+) letters each, printed in capitals\. Message: up to "
                r"(\d+) characters, printed as you type it\. No emoji\. " + re.escape(LATIN_EN) + r" Please check your spelling\.\n"
                r"Message ideas: (.+)"), p_siparis),
    (re.compile(r"DIGITAL FILE\n- One print ready JPG file in the color and size you choose\n- High resolution: 300 dpi at the "
                r"full size you choose, from (\d+ x \d+) to (\d+ x \d+) inches, or (A\d) to (A\d)\n- ("
                + "|".join(re.escape(k) for k in TESLIM_RU) + r")\. We check every personalization by hand before sending\n- ("
                + "|".join(re.escape(k) for k in INDIR_RU) + r")\n- Print it at home, at a local print shop or with an online print "
                r"service\n- Nothing is shipped\. For personal use only\."), p_dijital),
    (re.compile(r"SIZES\n(\d+) sizes, from (\d+ x \d+) to (\d+ x \d+) inches, plus (A\d) to (A\d)\. Every size is available as a "
                r"print and as a digital file\. See the size guide photo\."), p_boy),
    (re.compile(r"THE PERFECT GIFT\nA keepsake made for " + B_RX + " and " + B_RX + r" couples\. Short on time\? Choose the digital "
                r"file\. (" + "|".join(re.escape(k) for k in HEDIYE_RU) + ")"), p_hediye),
]


def kur(en, envanter=None):
    d = html.unescape(en or "").replace("\r\n", "\n").strip()
    par = [p.strip() for p in d.split("\n\n") if p.strip()]
    ctx = dict(sku_boy=len((envanter or {}).get("boy") or []) or None, boylar=(envanter or {}).get("boy"))
    if not (envanter or {}).get("boy"):   # inceleme 23 Eki: envanter okunamazsa boy/uc kontrolleri atlanmaz, FAIL
        return "", dict(pass_=False, hata=["envanter boy listesi yok (okunamadi)"], paragraf_en=0, paragraf_ru=0)
    ru, hata = [], []
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
    if BEYAN not in par:
        hata.append("EN'de beyan yok (once en_plan)")
    if envanter and ctx.get("renk") is not None and len(envanter.get("renk") or []) not in (0, ctx["renk"]):
        hata.append(f"EN {ctx['renk']} renk, envanter {len(envanter['renk'])}")
    out = "\n\n".join(ru)
    if re.search("[—–―‒−]", out):
        hata.append("RU'da uzun/orta tire")
    yasak = sorted({m.group(0) for m in YASAK_RU.finditer(out)})
    if yasak:   # inceleme 23 Eki O2: kagit/tedarikci/marka yasak ifadesi kosulsuz FAIL
        hata.append(f"RU'da yasak ifade: {yasak}")
    return out, dict(pass_=not hata and len(ru) == len(par), hata=hata, paragraf_en=len(par), paragraf_ru=len(ru))


def izin_ver(lid, ru, kontrol):
    """Serdar 23 Eki madde 4: kontrolu PASS olan yeni RU'yu bu kosu icin yazima acar (etsy_common RU kapisi yalniz bunu gecirir)."""
    if not (kontrol or {}).get("pass_") or not ru or (kontrol or {}).get("sorunlar"):
        raise SystemExit(f"DUR: ilan {lid} yeni RU kontrolu PASS degil; izin yok")
    E.RU_POSTER_IZIN[str(lid)] = E.ozet(ru)


def onay_ozet(en, ru):
    """Serdar 23 Eki 2a: kuru planda onaylanan EN + RU metninin ozeti; yazim aninda kurulan metin bununla birebir olmali."""
    return E.ozet((en or "") + "\n\x00\n" + (ru or ""))
