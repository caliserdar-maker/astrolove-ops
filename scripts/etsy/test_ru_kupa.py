#!/usr/bin/env python3
"""ru_kupa testi (Etsy yok): Serdar 31 Eki 3b. Calistir: python3 scripts/etsy/test_ru_kupa.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ru_kupa as R  # noqa: E402
from beyan_marka_yaz import BEYAN, RU_BEYAN  # noqa: E402

sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def en(a, b, kuyruk=None, isim=None, beyan=True):
    isim = isim or ("1. Left name (up to 10 letters)\n2. Right name (up to 10 letters)" if a == b
                    else f"1. Name for {a} (up to 10 letters)\n2. Name for {b} (up to 10 letters)")
    g = (f"A personalized mug for {a} and {b} couples: your two zodiac symbols join into one original fusion symbol, with your names "
         "and your message. A custom coffee mug and personalized couple gift made just for the two of you."
         + (f" A thoughtful choice when you are looking for {kuyruk}." if kuyruk else ""))
    p = [g] + ([BEYAN] if beyan else []) + [
        "[ A GIFT FOR COUPLES ]\nA wedding gift for couples who love astrology, an engagement gift for couples, an anniversary surprise "
        "or a newlywed gift. A zodiac gift for every morning.",
        "[ WHAT YOU GET ]\nOne mug, printed on both sides. The cover shows its front and back.\nFront: the fusion symbol, two small zodiac "
        "signs, your names in capitals joined by ∞, and your zodiac sign names.\nBack: your message in italics, your names and a small "
        "nazar (evil eye).",
        "[ 8 STYLES: THE ORCHARD WE KEEP ]\nOrange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, Lemon Grove, Blue "
        f"Grape or Golden Loquat. Every style of this zodiac couple mug has the same {a} and {b} symbol and an evil eye on the back. See photo 4.",
        "[ TWO SIZES ]\n- 11 oz (325 ml)\n- 15 oz (444 ml)\nSame design on both. See photo 5.",
        f"[ HOW TO PERSONALIZE ]\nWrite three lines in the personalization box:\n{isim}\n3. Message (one line, up to 30 characters "
        "including spaces and punctuation)\nLeave the message blank and we print:\nMy favorite place is with you\nPlease check your "
        "spelling. See photos 3 and 6.",
        "[ DETAILS ]\n- Glossy white ceramic, white inside\n- Dishwasher and microwave safe\n- Made to order, just for you\n- Original "
        "zodiac fusion symbols designed by AstroLoveArt",
        "[ RETURNS ]\nEvery mug is personalized, so we can&#39;t accept returns or exchanges for a change of mind. If your mug arrives "
        "damaged, send us a photo within 7 days of delivery and we&#39;ll replace it at no cost.",
        "Questions? Send us a message, we&#39;re happy to help."]
    return "\n\n".join(p)


ru, kon = R.kur(en("Cancer", "Libra", "a Cancer gift or Libra gifts"))
k("farkli burc PASS, 10 paragraf", kon["pass_"] and kon["paragraf_ru"] == 10, kon)
k("giris kuyrugu datif (Раку или Весам)", "подарок Раку или Весам." in ru)
k("beyan RU 2. paragraf", ru.split("\n\n")[1] == RU_BEYAN)
k("isim satirlari burca gore", "1. Имя для знака «Рак» (до 10 букв)\n2. Имя для знака «Весы» (до 10 букв)" in ru)
k("foto numaralari EN'den", "Смотрите фото 4." in ru and "Смотрите фото 5." in ru and "Смотрите фото 3 и 6." in ru)
k("bos mesaj metni Ingilizce aynen", "\nMy favorite place is with you\n" in ru)
k("tire yok, yasak yok", not any(c in ru for c in "—–") and not R.E.RU_YASAK.search(ru))
e = en("Leo", "Leo", "Leo gifts")
_, kon = R.kur(e)
k("ayni burc Left / Right -> kupa_en olmadan FAIL", not kon["pass_"] and "kupa_en" in " ".join(kon["hata"]), kon["hata"])
e2, d = R.kupa_en(e, "Leo", "Leo")
ru, kon = R.kur(e2)
k("kupa_en ayni burc DEGISTI, First Name / Second Name, PASS", d == "DEGISTI" and "1. First Name (up to 10 letters)\n2. Second Name (up to"
  in e2 and kon["pass_"] and "1. Первое имя (до 10 букв)\n2. Второе имя (до 10 букв)" in ru, (d, kon["hata"]))
k("kupa_en ikinci kez AYNI (idempotan)", R.kupa_en(e2, "Leo", "Leo") == (e2, "AYNI"))
k("kupa_en farkli burcta EN degismez", R.kupa_en(en("Cancer", "Libra"), "Cancer", "Libra")[1] == "AYNI")
_, kon = R.kur(en("Cancer", "Libra", "an Aries gift"))
k("kuyrukta baska burc FAIL", not kon["pass_"], kon["hata"])
_, kon = R.kur(en("Cancer", "Libra", "a Cancer gift for him"))
k("kuyruk kalip disi FAIL", not kon["pass_"], kon["hata"])
_, kon = R.kur(en("Cancer", "Libra", isim="1. Name for Libra (up to 10 letters)\n2. Name for Cancer (up to 10 letters)"))
k("isim satiri burc sirasi ters FAIL", not kon["pass_"], kon["hata"])
_, kon = R.kur(en("Cancer", "Libra", isim="1. Left name (up to 10 letters)\n2. Right name (up to 10 letters)"))
k("farkli burcta Left / Right FAIL", not kon["pass_"], kon["hata"])
_, kon = R.kur(en("Cancer", "Libra").replace("Dishwasher and microwave safe", "Dishwasher and microwave safe, lasts 100 years"))
k("bilinmeyen / fazla bilgi paragrafi FAIL", not kon["pass_"] and "kalip disi" in " ".join(kon["hata"]))
_, kon = R.kur(en("Cancer", "Libra") + "\n\nPrinted by Prodigi.")
k("fazladan paragraf FAIL", not kon["pass_"])
_, kon = R.kur(en("Cancer", "Libra", beyan=False))
k("beyansiz EN de kurulur (beyan zorunlu degil, EN ne ise RU o)", kon["pass_"] and kon["paragraf_ru"] == 9)
_, kon = R.kur(en("Cancer", "Libra").replace("[ RETURNS ]", "[ RETURN ]"))
k("bolum eksik FAIL", not kon["pass_"])
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
