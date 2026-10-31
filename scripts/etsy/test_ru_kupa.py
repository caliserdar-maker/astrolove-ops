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


from kupa_en_ornek import en  # noqa: E402




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
k("cogul: 10 букв, 21 буквы, 22 букв, 31 символа, 11 букв", (R.cogul(10, 'a', 'b', 'c'), R.cogul(21, 'a', 'b', 'c'),
  R.cogul(22, 'a', 'b', 'c'), R.cogul(31, 'a', 'b', 'c'), R.cogul(11, 'a', 'b', 'c')) == ('c', 'a', 'b', 'a', 'c'))
ru, kon = R.kur(en("Cancer", "Libra").replace("up to 10 letters", "up to 21 letters").replace("up to 30 characters", "up to 31 characters"))
k("21 / 31 dogru cogulla", kon["pass_"] and "(до 21 буквы)" in ru and "до 31 символа," in ru, kon["hata"])
k("10 / 30: букв / символов", "(до 10 букв)" in R.kur(en("Cancer", "Libra"))[0] and "до 30 символов," in R.kur(en("Cancer", "Libra"))[0])
_, kon = R.kur(en("Cancer", "Libra").replace("See photo 4.", "See photo 99."))
k("foto numarasi aralik disi FAIL", not kon["pass_"])
e = en("Cancer", "Libra"); p = e.split("\n\n")
_, kon = R.kur("\n\n".join(p[:3] + [p[2]] + p[3:]))
k("tekrarlanan paragraf FAIL", not kon["pass_"] and "tekrar" in " ".join(kon["hata"]))
_, kon = R.kur(e.replace("My favorite place is with you", "Buy now at example dot com and more words"))
k("bos mesaj metni siniri asarsa FAIL", not kon["pass_"])
_, kon = R.kur("\n\n".join(p[1:]).replace("1. Name for Cancer", "1. Left name").replace("2. Name for Libra", "2. Right name"))
k("giris paragrafi yoksa isim satiri FAIL", not kon["pass_"])
# Serdar 31 Eki 5a / 6a: yeni galeri foto numaralari + Latin harf notu
e0 = en("Cancer", "Libra", "Cancer gifts or Libra gifts")
e1, deg = R.galeri_en(e0)
k("galeri_en: stil 6-14, boy 4, kisisellestirme 3, Latin notu; eski numara yok", deg == ["foto_stil", "foto_boy", "foto_kisisel", "latin"]
  and "back. See photos 6 to 14." in e1 and "both. See photo 4." in e1 and "spelling. See photo 3." in e1
  and "punctuation)\n" + R.LATIN_EN + "\nLeave the message blank" in e1 and not R.hedef_kapisi(e1) and R.hedef_kapisi(e0), deg)
k("galeri_en idempotan (ikinci kosu degisiklik yok)", R.galeri_en(e1) == (e1, []))
ru, kon = R.kur(e1)
k("RU: фото с 6 по 14, фото 4, фото 3, Latin RU satiri, PASS", kon["pass_"] and "Смотрите фото с 6 по 14." in ru and "Смотрите фото 4." in ru
  and "Смотрите фото 3." in ru and "знаки препинания)\n" + R.LATIN_RU + "\nЕсли вы оставите" in ru, kon["hata"])
k("RU tire / yasak yok", not any(c in ru for c in "—–") and not R.E.RU_YASAK.search(ru))
e2, d2 = R.kupa_en(en("Leo", "Leo", "Leo gifts"), "Leo", "Leo")
k("ayni burc: kupa_en hem isim hem galeri", d2 == "DEGISTI" and not R.hedef_kapisi(e2) and R.kur(e2)[1]["pass_"])
try:
    R.galeri_en(e0.replace("See photo 4.", "See photo 9."))
    k("bilinmeyen foto numarasi -> ValueError", False)
except ValueError:
    k("bilinmeyen foto numarasi -> ValueError", True)
k("hedef kapisi: galeri disi foto (15) FAIL", R.hedef_kapisi(e1.replace("See photo 4.", "See photo 15.")))
_, kon = R.kur(e1.replace("6 to 14", "14 to 6"))
k("ters foto araligi FAIL", not kon["pass_"])
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
