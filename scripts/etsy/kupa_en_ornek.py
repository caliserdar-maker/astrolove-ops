#!/usr/bin/env python3
"""Test fikstoru: canli kupa EN aciklamasinin kalibi (31 Eki canli okuma, kupa-yd-oku KUPA_CANLI.json ile ayni yapi; eski foto
numaralari 4 / 5 / 3 ve 6, beyan paragrafi). test_ru_kupa ve test_kupa_galeri78 kullanir."""
from beyan_marka_yaz import BEYAN


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
