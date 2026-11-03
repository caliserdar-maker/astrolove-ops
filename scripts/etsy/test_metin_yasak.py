#!/usr/bin/env python3
"""metin_yasak_kapisi testleri (Serdar 3 Kas "A"; Etsy YOK). Bilinen PASS (mesru cumleler) + bilinen FAIL (her yasak ifade, EN + RU
cekim ekleriyle) + BAGLAM kurallari + UYARI/ENGEL modu + gercek Etsy._call / post_file yolunda kapinin calismasi.
Kullanim: python3 scripts/etsy/test_metin_yasak.py  -> SONUC n/n PASS (cikis 1 = FAIL)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402

sonuc = []


def k(ad, kosul, ayrinti=""):
    sonuc.append(bool(kosul))
    print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayrinti}]"))


def bul(metin, mod="UYARI", method="PATCH", alan="description"):
    return E.metin_yasak_kapisi(method, "/shops/1/listings/2", data={alan: metin}, mod=mod)


def main():
    pass_ornek = [
        "This print is not metallic foil; the gold is printed color.",
        "Printed on matte art paper.",
        "Ships from 308 Main Street.",
        "We use AI tools to help create the artwork.",
        "Печать на матовой художественной бумаге.",
        "Free shipping worldwide.",
        "Choose your style, your format and your size.",
    ]
    for m in pass_ornek:
        k(f"PASS ornek temiz: {m[:40]}", bul(m) == [], bul(m))
    kesin = {
        "Printed by Prodigi": "tedarikci adi", "Printful partner": "tedarikci adi", "Gelato print": "tedarikci adi",
        "Hahnemuhle paper": "Hahnemuhle", "Hahnemühle Photo Rag": "Hahnemuhle", "бумага Ханемюле": "Hahnemuhle",
        "on Photo Rag": "Photo Rag", "giclée print": "giclee", "giclee print": "giclee", "жикле печать": "giclee",
        "100% cotton": "cotton", "хлопок": "cotton", "хлопковая": "cotton",
        "museum quality": "museum / ISO 9706", "ISO 9706": "museum / ISO 9706", "музейное качество": "museum / ISO 9706",
        "OBA-free paper": "OBA-free", "bright white": "bright white", "12-colour inks": "12-colour", "12 color": "12-colour",
        "premium matte art paper": "premium", "Premium paper": "premium", "премиальной бумаге": "premium",
        "премиум качество": "premium", "премиальная": "premium",
        "long-lasting inks": "long-lasting", "long lasting colors": "long-lasting", "Long-Lasting": "long-lasting",
        "стойкими чернилами": "long-lasting", "стойкие": "long-lasting", "долговечные чернила": "long-lasting",
        "долговечность": "long-lasting",
        "art — print": "uzun/orta tire", "5–7 days": "uzun/orta tire",
        "Made by Lena": "kisi adi", "Serdar says": "kisi adi",
    }
    for m, ad in kesin.items():
        b = bul(m)
        k(f"FAIL ornek yakalanir: {m!r} -> {ad}", any(x[0] == "KESIN" and x[1] == ad for x in b), b)
    baglam = {"gold metallic foil accents": "metallic foil", "308 gsm paper": "308", "308 g/m2": "308",
              "one print ready 300 dpi JPG": "300 dpi", "Free preview before printing": "free preview",
              "tracking number by email": "tracking"}
    for m, ad in baglam.items():
        b = bul(m)
        k(f"BAGLAM uyarisi: {m!r}", any(x[0] == "BAGLAM" and x[1].startswith(ad) for x in b) and not any(x[0] == "KESIN" for x in b), b)
    # mod
    try:
        bul("premium paper", mod="UYARI"); uy = True
    except SystemExit:
        uy = False
    k("UYARI modu KESIN eslesmede istegi durdurmaz", uy)
    try:
        bul("premium paper", mod="ENGEL"); en = False
    except SystemExit:
        en = True
    k("ENGEL modu KESIN eslesmede SystemExit", en)
    try:
        bul("Free preview before printing", mod="ENGEL"); eb = True
    except SystemExit:
        eb = False
    k("ENGEL modu BAGLAM eslesmede durdurmaz (yalniz uyari)", eb)
    k("GET taranmaz", E.metin_yasak_kapisi("GET", "/listings/1", params={"q": "premium"}, mod="ENGEL") == [])
    k("varsayilan mod UYARI", E.METIN_KAPI_MOD == "UYARI")
    # tum istek degerleri: ic ice json (varyasyon adi, kisisellestirme), urlencoded govde, params, etiket listesi
    js = {"products": [{"property_values": [{"property_name": "Style", "values": ["Premium Gold"]}]}],
          "personalization_questions": [{"question_text": "Heading", "instructions": "long-lasting keepsake"}]}
    b = E.metin_yasak_kapisi("PUT", "/listings/2/inventory", json_body=js, mod="UYARI")
    k("ic ice json (varyasyon degeri + kisisellestirme talimati) taranir", {x[1] for x in b} >= {"premium", "long-lasting"}, b)
    b = E.metin_yasak_kapisi("PATCH", "/shops/1/listings/2", data="title=Premium%20print&tags=a%2Cb", mod="UYARI")
    k("urlencoded govde taranir", any(x[1] == "premium" for x in b), b)
    b = E.metin_yasak_kapisi("PATCH", "/shops/1/listings/2", data={"tags": ["gift", "long lasting"], "materials": ["cotton"]})
    k("etiket ve malzeme listeleri taranir", {x[1] for x in b} >= {"long-lasting", "cotton"}, b)
    b = E.metin_yasak_kapisi("POST", "/shops/1/listings/2/images", data={"alt_text": "Premium paper card"})
    k("alt metin taranir", any(x[1] == "premium" for x in b), b)
    # gercek Etsy._call ve post_file yolu (sahte requests; istek UYARI modunda gonderilir)
    import requests
    gonderilen = []

    class R:
        status_code, headers, text = 200, {"x-remaining-today": "5000"}, "{}"

        def json(self):
            return {}
    gercek_req, gercek_post = requests.request, requests.post
    requests.request = lambda *a, **kw: (gonderilen.append((a, kw)), R())[1]
    requests.post = lambda *a, **kw: (gonderilen.append((a, kw)), R())[1]
    try:
        api = E.Etsy.__new__(E.Etsy)
        api.__dict__.update(calls=0, remaining=5000, store=type("S", (), {"access_token": "x", "api_key_header": "k"})(), api_key="k", shared_secret="s")
        api._istek_oncesi = lambda: None
        api._bekle = lambda: 0
        api._kalan_yaz = lambda *a, **kw: None
        api.yayin_beyan_kontrol = lambda *a, **kw: None   # yayin denetimi ayri testte (test_ai_beyan); burada yalniz metin kapisi
        E.METIN_UYARI.clear()
        try:
            api._call("PATCH", "/shops/1/listings/9", data={"title": "Premium Leo print"})
        except Exception as e:  # noqa: BLE001  (sahte yanitta sonraki adimlar)
            print("   not:", type(e).__name__, str(e)[:80])
        k("Etsy._call: KESIN eslesme METIN_UYARI'ya yazilir ve istek gonderilir (UYARI)",
          any(u[3] == "premium" for u in E.METIN_UYARI) and gonderilen, (E.METIN_UYARI, len(gonderilen)))
        n0 = len(E.METIN_UYARI)
        try:
            api.post_file("/shops/1/listings/9/images", {}, data={"alt_text": "long-lasting card"})
        except Exception as e:  # noqa: BLE001
            print("   not:", type(e).__name__, str(e)[:80])
        k("post_file: alt metin kapidan gecer ve uyarilir", len(E.METIN_UYARI) > n0)
        E.METIN_KAPI_MOD = "ENGEL"
        n1 = len(gonderilen)
        try:
            api._call("PATCH", "/shops/1/listings/9", data={"title": "Premium Leo print"}); dur = False
        except SystemExit:
            dur = True
        k("Etsy._call ENGEL modunda KESIN eslesmede istek gonderilmez", dur and len(gonderilen) == n1)
    finally:
        E.METIN_KAPI_MOD = "UYARI"
        requests.request, requests.post = gercek_req, gercek_post
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
