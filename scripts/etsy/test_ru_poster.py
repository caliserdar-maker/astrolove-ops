#!/usr/bin/env python3
"""ru_poster testi (ag yok): sablon EN -> RU, kalip disi paragraf FAIL, envanter boy sayisi farki FAIL, RU olcumu sorun 0."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ru_olcum as R  # noqa: E402
import ru_poster as P  # noqa: E402

GIRIS = ("Personalized Aries and Leo couple wall art with your two names and your own short message, a meaningful newlywed gift or "
         "1st anniversary gift. Our original design joins your two zodiac symbols into one shared symbol, with your names under the "
         "two small signs. Choose a digital file or a print. A meaningful gift for anniversaries, engagements, weddings, Valentine's "
         "Day and birthdays. A thoughtful choice when you are looking for an Aries gift or Leo gifts.")
SIPARIS = ("HOW TO ORDER\n1. Format: choose Digital File or Print.\n2. Primary color: choose one of 5 colors.\n3. Size: choose your "
           "size. Your digital file is made in the color and size you choose.\n4. Personalization: type the two names and your "
           "message.\nNames: up to 11 letters each, printed in capitals. Message: up to 35 characters, printed as you type it. No "
           "emoji. Please check your spelling.\nMessage ideas: Where Our Story Began / Since 2019")
DIJITAL = ("DIGITAL FILE\n- One print ready JPG file in the color and size you choose\n- High resolution: 300 dpi at the full size you "
           "choose, from 8 x 10 to 24 x 36 inches, or A4 to A2\n- Delivered to your Etsy order within 24 hours. We check every "
           "personalization by hand before sending\n- Download it from Purchases in a web browser. The Etsy app can't download "
           "files\n- Print it at home, at a local print shop or with an online print service\n- Nothing is shipped. For personal use only.")
BOY = ("SIZES\n13 sizes, from 8 x 10 to 24 x 36 inches, plus A4 to A2. Every size is available as a print and as a digital file. "
       "See the size guide photo.")
HEDIYE = ("THE PERFECT GIFT\nA keepsake made for Aries and Leo couples. Short on time? Choose the digital file. It arrives within 24 "
          "hours, ready to print or share.")
sabit = [k for k in P.SABIT if k != P.BEYAN]
EN = "\n\n".join([GIRIS, P.BEYAN, "Aries: March 21 to April 19. Leo: July 23 to August 22.", SIPARIS, sabit[0], DIJITAL] + sabit[1:3]
                 + [BOY] + sabit[3:] + [HEDIYE])
ENV = dict(boy=["8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x30", "24x36", "A4", "A3", "A2"],
           renk=["a", "b", "c", "d", "e"], format=["Digital File", "Print"], sku_sayi=130)


def main():
    s = []
    ru, k = P.kur(EN, ENV)
    s.append(("tum paragraflar kalipli, PASS", k["pass_"] and k["paragraf_en"] == k["paragraf_ru"] == 16))
    o = R.analiz_bir(dict(listing_id="1", aile="poster", en=EN, ru=ru, envanter=ENV, ortak=[]))
    s.append(("yeni RU olcumde sorun 0", o["sorunlar"] == ""))
    s.append(("burc ve tarih RU", "знаками зодиака Овен и Лев" in ru and "подарок Овну или Льву" in ru and "с 21 марта по 19 апреля" in ru and "с 23 июля по 22 августа" in ru))
    s.append(("yasak ifade yok", not any(x in ru for x in ("Hahnem", "Prodigi", "308", "жикле", "хлоп", "AstroLove "))))
    s.append(("kalip disi paragraf FAIL", not P.kur(EN + "\n\nNEW\nSomething.", ENV)[1]["pass_"]))
    s.append(("envanter boy sayisi farki FAIL", not P.kur(EN, dict(ENV, boy=ENV["boy"][:12]))[1]["pass_"]))
    s.append(("beyansiz EN FAIL", not P.kur(EN.replace(P.BEYAN + "\n\n", ""), ENV)[1]["pass_"]))
    s.append(("EN'de tek harf degisirse FAIL (sabit bolum)", not P.kur(EN.replace("damp rooms", "damp room"), ENV)[1]["pass_"]))
    s.append(("kuyrukta burc disi bilgi FAIL", not P.kur(EN.replace("an Aries gift or Leo gifts", "an Aries gift for him"), ENV)[1]["pass_"]))
    s.append(("aralik ucu envanterde yok FAIL", not P.kur(EN, dict(ENV, boy=[b for b in ENV["boy"] if b != "24x36"] + ["20x24"]))[1]["pass_"]))
    import re as _re
    s.append(("yasak ifade denetimi", bool(P.YASAK_RU.search("бумага хлопковая")) and bool(P.YASAK_RU.search("AstroLove дизайн"))
              and not P.YASAK_RU.search(ru)))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"ru_poster testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
