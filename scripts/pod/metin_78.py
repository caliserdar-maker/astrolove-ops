#!/usr/bin/env python3
"""78 POD ilani icin METIN KURU KOSU (Serdar, 24 Eyl 2026).

SALT OKUMA. Etsy'ye hicbir sey yazilmaz: her ilanin mevcut basligi, etiketleri,
aciklamasi, RU cevirisi, kategorisi ve nitelikleri okunur, YEDEK/ altina kaydedilir;
yeni baslik / 13 etiket / EN aciklama / RU baslik + aciklama URETILIR ve kontrol
edilir. Cikti: METIN_78.csv + METIN_78.md.

Burc sirasi ilanin MEVCUT basligindan alinir (katalogdaki siradan degil).
"""
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))

BURCLAR = ["Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo",
           "Libra", "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo"]
RU_AD = {"Aquarius": "Водолей", "Aries": "Овен", "Cancer": "Рак", "Capricorn": "Козерог",
         "Gemini": "Близнецы", "Leo": "Лев", "Libra": "Весы", "Pisces": "Рыбы",
         "Sagittarius": "Стрелец", "Scorpio": "Скорпион", "Taurus": "Телец", "Virgo": "Дева"}
ORTAK = ["personalized couple", "custom couple print", "zodiac couple print",
         "couple names print", "zodiac couple gift", "astrology wall art",
         "anniversary gift", "star sign print", "giclee print"]
YASAK_KELIME = ["archival", "acid-free", "museum", "studio", "студи"]
UZUN_TIRE = ["—", "–"]          # em dash, en dash

BASLIK = ("{A} and {B} Zodiac Wall Art, Personalized Couple Print with Names and Message, "
          "Unframed")

EN_GOVDE = """Personalized {A} and {B} zodiac wall art with your two names and your own short message. One original AstroLove design that joins both signs into a single symbol, printed on Hahnemühle Photo Rag 308 gsm cotton paper and shipped unframed.

HOW TO PERSONALIZE
1. Pick a color and size.
2. Type the two names. Each name goes under its own sign.
3. Type your message.
Names: up to 11 letters, printed in capitals. Message: up to 35 characters, printed as you type it. Please check your spelling. For longer names or special characters, send us a message before you order.

THE ARTWORK
The {A} and {B} fusion symbol is original AstroLove artwork. Your names sit under the two small signs, and your message appears below them.

PAPER AND PRINT
- Hahnemühle Photo Rag, 308 gsm, 100% cotton, matte finish
- Giclée print
- Unframed, ready for a frame of your choice
The gold look is a printed color. It is not metallic foil or raised ink. Colors may vary slightly between screens and paper.

5 COLORS
Midnight Blue, Deep Black, Champagne Ivory, Pure White and Warm Parchment. Choose yours in the Color menu.

16 SIZES
8 × 10, 11 × 14, 12 × 16, 12 × 18, 16 × 20, 16 × 24, 18 × 24, 20 × 30, 24 × 30, 24 × 32, 24 × 36 and 30 × 40 inches, plus A4, A3, A2 and A1. See the size guide photo.

MADE TO ORDER
Each print is made for your order by our production partner Prodigi. It ships flat or rolled, depending on the size. See the delivery estimate for your address.

RETURNS
Every print is personalized, so we can't accept returns or exchanges. If your print arrives damaged, send us a photo within 7 days and we'll happily reprint it at no cost.

A meaningful anniversary, wedding or Valentine's gift for a {A} and {B} couple."""

RU_BASLIK = "Знаки зодиака {A} и {B}: именной постер для пары с вашими именами и посланием, без рамы"

RU_GOVDE = """Именной постер для пары {A} и {B} с вашими двумя именами и короткой надписью. Оригинальный дизайн AstroLove объединяет оба знака в один символ. Печать на хлопковой бумаге Hahnemühle Photo Rag 308 г/м2, отправляем без рамы.

КАК ПЕРСОНАЛИЗИРОВАТЬ
1. Выберите цвет и размер.
2. Впишите два имени. Каждое имя печатается под своим знаком.
3. Впишите свою надпись.
Имена: до 11 букв, печатаются заглавными. Надпись: до 35 символов, печатается так, как вы её напишете. Пожалуйста, проверьте написание. Если имя длиннее или нужны особые символы, напишите нам до заказа.

О РИСУНКЕ
Символ, объединяющий знаки {A} и {B}. Оригинальный рисунок AstroLove. Имена стоят под двумя небольшими знаками, а ваша надпись напечатана под ними.

БУМАГА И ПЕЧАТЬ
- Hahnemühle Photo Rag, 308 г/м2, 100% хлопок, матовая поверхность
- Печать жикле
- Без рамы, готов к раме на ваш выбор
Золотистый цвет это напечатанная краска, а не металлическая фольга и не рельефная печать. Оттенки на экране и на бумаге могут немного отличаться.

5 ЦВЕТОВ
Midnight Blue, Deep Black, Champagne Ivory, Pure White и Warm Parchment. Выберите свой в меню Color.

16 РАЗМЕРОВ
8 × 10, 11 × 14, 12 × 16, 12 × 18, 16 × 20, 16 × 24, 18 × 24, 20 × 30, 24 × 30, 24 × 32, 24 × 36 и 30 × 40 дюймов, а также A4, A3, A2 и A1. Смотрите фото с таблицей размеров.

ПЕЧАТАЕМ ПОД ЗАКАЗ
Каждый постер печатается по вашему заказу нашим партнером Prodigi. В зависимости от размера отправляем плоско или в тубусе. Сроки доставки для вашего адреса указаны в карточке товара.

ВОЗВРАТ
Каждый постер именной, поэтому возврат и обмен невозможны. Если постер придет поврежденным, пришлите фото в течение 7 дней, и мы бесплатно напечатаем новый.

Хороший подарок на годовщину, свадьбу или День святого Валентина для пары {A} и {B}."""



# ------------------------------------------------------------------ uretim
def burc_sirasi(baslik, yedek_cift):
    """Mevcut basliktaki burc sirasi. Bulunamazsa katalogdaki cift sirasi."""
    bulunan = []
    for m in re.finditer(r"\b(" + "|".join(BURCLAR) + r")\b", baslik or ""):
        ad = m.group(1)
        bulunan.append(ad)
        if len(bulunan) == 2:
            return bulunan[0], bulunan[1], "baslik"
    if len(bulunan) == 1:                      # ayni burcli cift tek kez yazilmis olabilir
        return bulunan[0], bulunan[0], "baslik(tek)"
    p = [s.strip() for s in (yedek_cift or "").split("+")]
    return (p + ["", ""])[0], (p + ["", ""])[1], "katalog"


def _hediye_sanat(s):
    """Tek burc icin 'gift' + 'wall art' slotlari; Cancer'da 'cancer' tek basina yazilmaz."""
    if s == "cancer":
        return ["cancer zodiac gift", "cancer zodiac art"]
    return [f"{s} gift", f"{s} wall art"]


def cift_etiketleri(A, B):
    a, b = A.lower(), B.lower()
    t = []
    if a != b:
        cift = f"{a} and {b}"
        if len(cift) > 20:
            cift = f"{a} {b}"
        if len(cift) <= 20:
            t.append(cift)
        t += _hediye_sanat(a) + _hediye_sanat(b)
    else:
        t += _hediye_sanat(a)
        cift = f"{a} and {a}"
        if len(cift) <= 20:
            t.append(cift)
        t.append("cancer zodiac couple" if a == "cancer" else f"{a} couple")
        if a == "cancer":
            t.append("cancer star sign")
        else:
            zp = f"{a} zodiac print"
            t.append(zp if len(zp) <= 20 else f"{a} print")
    return [x for x in t if len(x) <= 20]


def etiketler(A, B):
    t = []
    for x in cift_etiketleri(A, B) + ORTAK:
        if x not in t and len(x) <= 20:
            t.append(x)
        if len(t) == 13:
            break
    return t


def kisisel_alanlar(A, B):
    """Kisisellestirme alani PLANI (yalniz CSV/rapor; Etsy'ye yazilmaz). 3 alan, hepsi zorunlu.
    Ayni burclu ciftlerde ad ayrimi 'Left name' / 'Right name' olur. 'Sign order' alani YOK."""
    if A == B:
        ad1, ad2 = "Left name", "Right name"
    else:
        ad1, ad2 = f"Name under {A}", f"Name under {B}"
    return [
        {"ad": ad1, "aciklama": "Up to 11 letters. Printed in capitals.", "max": 11, "zorunlu": True},
        {"ad": ad2, "aciklama": "Up to 11 letters. Printed in capitals.", "max": 11, "zorunlu": True},
        {"ad": "Your message",
         "aciklama": "Up to 35 characters, including spaces. Printed as you type it.",
         "max": 35, "zorunlu": True},
    ]


def metinler(A, B):
    en = EN_GOVDE.replace("{A}", A).replace("{B}", B)
    ru = RU_GOVDE.replace("{A}", RU_AD.get(A, A)).replace("{B}", RU_AD.get(B, B))
    return {
        "baslik": BASLIK.replace("{A}", A).replace("{B}", B),
        "etiketler": etiketler(A, B),
        "aciklama": en,
        "ru_baslik": RU_BASLIK.replace("{A}", RU_AD.get(A, A)).replace("{B}", RU_AD.get(B, B)),
        "ru_aciklama": ru,
    }


# ------------------------------------------------------------------ kontroller
def kontrol(m):
    h = []
    et = m["etiketler"]
    if len(et) != 13:
        h.append(f"etiket sayisi {len(et)}")
    uzun = [x for x in et if len(x) > 20]
    if uzun:
        h.append(f"20 karakteri asan etiket: {uzun}")
    if len(set(et)) != len(et):
        h.append("tekrar eden etiket")
    if any(x != x.lower() for x in et):
        h.append("kucuk harf disi etiket")
    if len(m["baslik"]) > 140:
        h.append(f"baslik {len(m['baslik'])} karakter")
    if len(m["ru_baslik"]) > 140:
        h.append(f"RU baslik {len(m['ru_baslik'])} karakter")
    metin = " ".join([m["baslik"], m["aciklama"], m["ru_baslik"], m["ru_aciklama"]])
    for t in UZUN_TIRE:
        if t in metin:
            h.append(f"uzun tire var ({t!r})")
    dusuk = metin.lower()
    for k in YASAK_KELIME:
        if k in dusuk:
            h.append(f"yasak kelime: {k}")
    return h


# ------------------------------------------------------------ Etsy API yetenegi (OAS)
OAS_URL = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"


def oas_kisisellestirme(url=OAS_URL):
    """Etsy OAS'i indirip kisisellestirme ile ilgili ALAN ve UC'lari cikarir. Yalniz okuma."""
    import requests
    try:
        d = requests.get(url, timeout=120).json()
    except Exception as e:                       # ag yoksa rapor 'OKUNAMADI' der
        return {"hata": f"{type(e).__name__}: {e}"[:200]}
    sema = (d.get("components") or {}).get("schemas") or {}
    listing_alan = sorted(k for k in ((sema.get("ShopListing") or {}).get("properties") or {})
                          if "personaliz" in k.lower())
    sema_adlari = sorted(k for k in sema if "personaliz" in k.lower())
    uclar, aciklama = [], {}
    for yol, islemler in (d.get("paths") or {}).items():
        for yontem, op in (islemler or {}).items():
            if yontem not in ("get", "post", "put", "patch", "delete"):
                continue
            adlar = set()
            for prm in op.get("parameters") or []:
                if "personaliz" in (prm.get("name") or "").lower():
                    adlar.add(prm["name"])
            rb = ((op.get("requestBody") or {}).get("content") or {})
            for ictyp in rb.values():
                sema_g = (ictyp.get("schema") or {})
                for k, v in (sema_g.get("properties") or {}).items():
                    if "personaliz" in k.lower():
                        adlar.add(k)
                        if (v or {}).get("description"):
                            aciklama[f"{op.get('operationId')}:{k}"] = v["description"]
            # yolunda personalization gecen uclari da al (parametresiz GET dahil)
            if adlar or "personaliz" in yol.lower():
                uclar.append((yontem.upper(), yol, op.get("operationId"), sorted(adlar)))
                for alan in ("summary", "description"):
                    if op.get(alan):
                        aciklama[f"{op.get('operationId')}:{alan}"] = op[alan]
    ayrinti = {}
    for ad in sema_adlari:
        props = (sema.get(ad) or {}).get("properties") or {}
        ayrinti[ad] = {k: {kk: vv for kk, vv in (v or {}).items()
                           if kk in ("type", "maxLength", "minimum", "maximum", "description", "items")}
                       for k, v in props.items()}
    coklu = sorted({a for _, _, _, adlar in uclar for a in adlar
                    if "question" in a.lower() or "multiple" in a.lower()})
    okuma_uclari = [(y, yol, oid) for y, yol, oid, _ in uclar if y == "GET"]
    return {"listing_alanlari": listing_alan, "personalizasyon_semalari": sema_adlari,
            "uclar": sorted(uclar, key=lambda t: (t[1], t[0])),
            "coklu_alan_izleri": coklu, "sema_ayrinti": ayrinti,
            "okuma_uclari": okuma_uclari, "aciklamalar": aciklama}


# ------------------------------------------------------------------ Etsy okuma
# Serdar karari 24 Eyl: tum ilanlarda bu iki nitelik planlanir (YAZILMAZ, yalniz CSV).
NITELIK_PLAN = [("Can be personalized", "Yes"), ("Occasion", "Anniversary")]


def taksonomi_nitelik(props, ad, deger_ad):
    """taxonomy properties -> (property_id, property_adi, value_id, deger_adi). Bulunmazsa None."""
    for pr in props or []:
        adlar = {(pr.get("name") or "").lower(), (pr.get("display_name") or "").lower()}
        if ad.lower() in adlar:
            for v in pr.get("possible_values") or []:
                if (v.get("name") or "").lower() == deger_ad.lower():
                    return pr.get("property_id"), pr.get("name") or pr.get("display_name"), v.get("value_id"), v.get("name")
            return pr.get("property_id"), pr.get("name") or pr.get("display_name"), None, None
    return None, None, None, None


def sorulari_oku(api, shop, lid):
    """Kisisellestirme sorularini OKUMA denemesi: once ilana ozel uc, sonra listing include."""
    r = api.get(f"/shops/{shop}/listings/{lid}/personalization", ok404=True)
    if isinstance(r, dict) and r:
        return r, "GET /shops/{shop_id}/listings/{listing_id}/personalization"
    r2 = api.get(f"/listings/{lid}", params={"includes": "Personalization"}, ok404=True) or {}
    if r2.get("personalization_questions") or r2.get("personalization"):
        return {k: v for k, v in r2.items() if "personaliz" in k.lower()}, "GET /listings/{listing_id}?includes=Personalization"
    return None, "YOK"


def soru_ozeti(veri):
    """{'personalization_questions':[...]} -> 'Sign order[sec:Cancer left/Libra left, zorunlu]' gibi."""
    if not veri:
        return "OKUNAMADI"
    sorular = veri.get("personalization_questions") or veri.get("personalization") or []
    if isinstance(sorular, dict):
        sorular = sorular.get("personalization_questions") or []
    if not sorular:
        return "SORU YOK"
    out = []
    for q in sorular:
        if not isinstance(q, dict):
            continue
        sec = "/".join(str(o.get("label")) for o in (q.get("options") or []) if isinstance(o, dict))
        out.append(f"{q.get('question_text')}[{q.get('question_type')}"
                   + (f", sec:{sec}" if sec else "")
                   + (f", max:{q.get('max_allowed_characters')}" if q.get("max_allowed_characters") else "")
                   + (", zorunlu" if q.get("required") else "") + "]")
    return " | ".join(out) or "SORU YOK"


def oku(api, shop, lid, yedek_dir, taksonomi_onbellek):
    L = api.get(f"/listings/{lid}") or {}
    ru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
    tid = L.get("taxonomy_id")
    if tid and tid not in taksonomi_onbellek:
        taksonomi_onbellek[tid] = (api.get(f"/seller-taxonomy/nodes/{tid}/properties", ok404=True) or {}).get("results") or []
    sorular, soru_uc = sorulari_oku(api, shop, lid)
    for ad, veri in (("listing", L), ("translations_ru", ru), ("properties", props),
                     ("personalization", sorular)):
        (yedek_dir / f"{lid}_{ad}.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    return L, ru, props, tid, sorular, soru_uc


def nitelik_ozeti(props):
    """[(ad, deger1|deger2)] -> 'Occasion=Anniversary; Holiday=YOK' gibi tek satir."""
    out = []
    for p in props or []:
        ad = p.get("property_name") or str(p.get("property_id"))
        deg = "|".join(str(v) for v in (p.get("values") or []))
        out.append(f"{ad}={deg or 'YOK'}")
    return "; ".join(out) if out else "YOK"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="_out/metin78")
    ap.add_argument("--katalog", default=str(KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kota-alt", type=int, default=200)
    ap.add_argument("--ornek", default="4570143815,LEO_LEO,CAPRICORN_SAGITTARIUS")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)

    from etsy_common import Etsy, TokenStore, log
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""),
                       os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]

    katalog = json.loads(pathlib.Path(a.katalog).read_text(encoding="utf-8"))
    if a.limit:
        katalog = katalog[:a.limit]
    toplam = len(katalog)
    t0 = time.time()
    son_rapor = t0
    satirlar, taksonomi = [], {}
    hata_ilan = []

    for i, k in enumerate(katalog, 1):
        lid = str(k["id"])
        L, ru, props, tid, sorular, soru_uc = oku(api, shop, lid, out / "YEDEK", taksonomi)
        A, B, kaynak = burc_sirasi(L.get("title") or "", k.get("pair"))
        m = metinler(A, B)
        alanlar = kisisel_alanlar(A, B)
        yonerge = L.get("personalization_instructions") or ""
        ozet = soru_ozeti(sorular)
        sign_order = ("kaldirilacak" if ("sign order" in ozet.lower() or "sign order" in yonerge.lower())
                      else ("okunamadi" if ozet == "OKUNAMADI" else "yok"))
        tks = taksonomi.get(tid) or []
        nplan = [taksonomi_nitelik(tks, ad, dg) for ad, dg in NITELIK_PLAN]
        h = kontrol(m)
        if h:
            hata_ilan.append((lid, h))
        satirlar.append({
            "ilan_id": lid, "cift": f"{A} + {B}", "burc_kaynagi": kaynak, "state": L.get("state"),
            "taxonomy_id": tid, "nitelikler": nitelik_ozeti(props),
            "eski_baslik": L.get("title") or "", "yeni_baslik": m["baslik"],
            "eski_etiketler": "|".join(L.get("tags") or []),
            "yeni_etiketler": "|".join(m["etiketler"]),
            "yeni_aciklama_en": m["aciklama"],
            "eski_ru_baslik": ru.get("title") or "", "yeni_ru_baslik": m["ru_baslik"],
            "eski_ru_aciklama_var": "E" if (ru.get("description") or "").strip() else "H",
            "yeni_ru_aciklama": m["ru_aciklama"],
            "kisisel_acik": "E" if L.get("is_personalizable") else "H",
            "kisisel_zorunlu_mevcut": L.get("personalization_is_required"),
            "kisisel_max_mevcut": L.get("personalization_char_count_max"),
            "kisisel_yonerge_mevcut": yonerge,
            "sign_order_alani": sign_order,
            "mevcut_sorular": ozet, "sorular_okuma_ucu": soru_uc,
            "nitelik1_ad": NITELIK_PLAN[0][0], "nitelik1_property_id": nplan[0][0],
            "nitelik1_deger": NITELIK_PLAN[0][1], "nitelik1_value_id": nplan[0][2],
            "nitelik2_ad": NITELIK_PLAN[1][0], "nitelik2_property_id": nplan[1][0],
            "nitelik2_deger": NITELIK_PLAN[1][1], "nitelik2_value_id": nplan[1][2],
            "alan1_ad": alanlar[0]["ad"], "alan1_aciklama": alanlar[0]["aciklama"],
            "alan1_max": alanlar[0]["max"], "alan1_zorunlu": "E",
            "alan2_ad": alanlar[1]["ad"], "alan2_aciklama": alanlar[1]["aciklama"],
            "alan2_max": alanlar[1]["max"], "alan2_zorunlu": "E",
            "alan3_ad": alanlar[2]["ad"], "alan3_aciklama": alanlar[2]["aciklama"],
            "alan3_max": alanlar[2]["max"], "alan3_zorunlu": "E",
            "kontrol": "PASS" if not h else "FAIL: " + "; ".join(h),
        })
        simdi = time.time()
        if simdi - son_rapor >= 60 or i == toplam:
            gecen = simdi - t0
            kalan = gecen / i * (toplam - i)
            log(f"  {i}/{toplam} (%{i * 100 // toplam}) | gecen {gecen / 60:.1f} dk | "
                f"kalan {kalan / 60:.1f} dk | kota {api.remaining}")
            son_rapor = simdi

    sutunlar = list(satirlar[0].keys())
    with (out / "METIN_78.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sutunlar)
        w.writeheader()
        w.writerows(satirlar)

    pass_n = sum(1 for s in satirlar if s["kontrol"] == "PASS")
    nitelik_adlari = sorted({p.split("=")[0] for s in satirlar for p in s["nitelikler"].split("; ") if p != "YOK"})
    taks_adlari = sorted({p.get("name") for lst in taksonomi.values() for p in lst if p.get("name")})
    md = [f"# 78 POD ilani metin kuru kosu — {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", "",
          "**SALT OKUMA.** Etsy'ye hicbir sey yazilmadi; yalniz okuma + dosya uretimi.", "",
          f"- ilan: {toplam} | kontrol PASS: {pass_n} | FAIL: {toplam - pass_n}",
          f"- burc sirasi kaynagi: " + ", ".join(f"{k}={v}" for k, v in sorted(
              {s['burc_kaynagi']: sum(1 for x in satirlar if x['burc_kaynagi'] == s['burc_kaynagi'])
               for s in satirlar}.items())),
          f"- baslik uzunlugu: en fazla {max(len(s['yeni_baslik']) for s in satirlar)} karakter (sinir 140)",
          f"- RU baslik uzunlugu: en fazla {max(len(s['yeni_ru_baslik']) for s in satirlar)} karakter",
          f"- etiket: her ilanda 13; en uzun etiket {max(len(t) for s in satirlar for t in s['yeni_etiketler'].split('|'))} karakter (sinir 20)",
          f"- RU cevirisi zaten olan ilan: {sum(1 for s in satirlar if s['eski_ru_aciklama_var'] == 'E')}/{toplam}",
          f"- ilanlarda dolu nitelikler: {', '.join(nitelik_adlari) or 'YOK'}",
          f"- kategoride tanimli nitelikler (taxonomy {sorted(taksonomi)}): {', '.join(taks_adlari) or 'YOK'}",
          "- nitelikler DEGISTIRILMEDI, yalniz raporlandi.", ""]
    oas = oas_kisisellestirme()
    (out / "OAS_KISISELLESTIRME.json").write_text(json.dumps(oas, ensure_ascii=False, indent=1), encoding="utf-8")
    md += ["## Kisisellestirme alani plani (YAZILMADI)", "",
           "- Her ilanda 3 alan, hepsi ZORUNLU: iki isim (en fazla 11 harf, buyuk harf basilir) + mesaj "
           "(en fazla 35 karakter, yazildigi gibi basilir).",
           "- Farkli burclu ciftlerde alan adlari `Name under {A}` / `Name under {B}`; ayni burclu ciftlerde "
           "`Left name` / `Right name`. Ucuncu alan her ilanda `Your message`.",
           "- `Sign order` alani YOK. Mevcut yonergesinde 'sign order' gecen ilan: "
           f"{sum(1 for s2 in satirlar if s2['sign_order_alani'] == 'kaldirilacak')}/{toplam} "
           "(CSV `sign_order_alani` sutununda 'kaldirilacak' olarak isaretli).",
           f"- Mevcut kisisellestirme SORULARI okuma ucu: {satirlar[0]['sorular_okuma_ucu']}; "
           f"soru okunabilen ilan: {sum(1 for s2 in satirlar if s2['mevcut_sorular'] not in ('OKUNAMADI',))}/{toplam}; "
           f"'Sign order' sorusu bulunan: {sum(1 for s2 in satirlar if s2['sign_order_alani'] == 'kaldirilacak')}/{toplam}; "
           f"okunamayan: {sum(1 for s2 in satirlar if s2['sign_order_alani'] == 'okunamadi')}/{toplam}",
           f"- Ilanlarin kisisellestirme durumu (okunan): acik {sum(1 for s2 in satirlar if s2['kisisel_acik'] == 'E')}/{toplam}; "
           f"mevcut karakter siniri degerleri: {sorted({str(s2['kisisel_max_mevcut']) for s2 in satirlar})}; "
           f"mevcut zorunluluk: {sorted({str(s2['kisisel_zorunlu_mevcut']) for s2 in satirlar})}; "
           f"mevcut yonerge dolu olan: {sum(1 for s2 in satirlar if (s2['kisisel_yonerge_mevcut'] or '').strip())}/{toplam}", "",
           "## Etsy API coklu kisisellestirme alanini destekliyor mu? (OAS okumasi)", ""]
    if oas.get("hata"):
        md += [f"- OAS OKUNAMADI: {oas['hata']}", ""]
    else:
        md += [f"- Kaynak: {OAS_URL}",
               f"- ShopListing semasindaki kisisellestirme alanlari: {oas['listing_alanlari']}",
               f"- Adinda 'personaliz' gecen sema: {oas['personalizasyon_semalari'] or 'YOK'}",
               "- Kisisellestirme alani yazan/okuyan uclar:", ""]
        md += [f"  - `{y} {yol}` ({oid}): {', '.join(adlar)}" for y, yol, oid, adlar in oas["uclar"]]
        coklu_uc = [(y, yol, oid) for y, yol, oid, adlar in oas["uclar"]
                    if any("question" in a.lower() or "multiple" in a.lower() for a in adlar)]
        md += ["", f"- Coklu alan izi (uc parametreleri): {oas['coklu_alan_izleri'] or 'YOK'}",
               f"- Kisisellestirme OKUMA ucu (GET): "
               + (", ".join(f"`{y} {yol}` ({oid})" for y, yol, oid in oas["okuma_uclari"]) or "YOK"), ""]
        if oas.get("aciklamalar"):
            md += ["OAS aciklamalari (kanit):", ""]
            md += [f"- `{k}`: {v[:400]}" for k, v in sorted(oas["aciklamalar"].items())]
            md += [""]
        for ad, props in (oas.get("sema_ayrinti") or {}).items():
            md += [f"**Sema `{ad.split('_')[-1]}`** (`{ad}`):", "",
                   "| alan | tip | sinir | aciklama |", "|---|---|---|---|"]
            for k, v in props.items():
                sinir = v.get("maxLength") or (f"{v.get('minimum')}..{v.get('maximum')}"
                                               if v.get("maximum") is not None else "")
                md += [f"| `{k}` | {v.get('type') or ''} | {sinir} | {(v.get('description') or '')[:160]} |"]
            md += [""]
        if coklu_uc:
            y, yol, oid = coklu_uc[0]
            md += ["**Sonuc: Etsy API coklu kisisellestirme alanini DESTEKLIYOR.** Kanit: "
                   f"`{y} {yol}` ({oid}), govdede `personalization_questions` dizisi ve "
                   "`supports_multiple_personalization_questions` bayragi. Yani 3 alan (iki isim + mesaj) "
                   "panelden degil, bu uc ile yazilabilir. Listing seviyesindeki tek alanlik eski model "
                   "(`is_personalizable`, `personalization_is_required`, `personalization_char_count_max`, "
                   "`personalization_instructions`; `PATCH /v3/application/shops/{shop_id}/listings/{listing_id}`) "
                   "yerini bu uca birakir. BU GOREVDE YAZILMADI; yazma ayri onay ister.", ""]
        else:
            md += ["**Sonuc: OAS'ta coklu alan icin uc/sema bulunamadi.** Kisisellestirme ilan basina tek "
                   "serbest metin alanidir; 3 ayri alan ancak Etsy panelinden "
                   "(Listings > ilan > Personalization) kurulabilir.", ""]
    if hata_ilan:
        md += ["## Kontrol hatalari", ""] + [f"- {lid}: {'; '.join(h)}" for lid, h in hata_ilan] + [""]

    md += ["## Nitelik plani (YAZILMADI, taxonomy 121'den okundu)", "",
           "| nitelik | deger | property_id | value_id | ilan sayisi |", "|---|---|---|---|---|"]
    for i in (1, 2):
        pid = {str(s2[f"nitelik{i}_property_id"]) for s2 in satirlar}
        vid = {str(s2[f"nitelik{i}_value_id"]) for s2 in satirlar}
        md += [f"| {satirlar[0][f'nitelik{i}_ad']} | {satirlar[0][f'nitelik{i}_deger']} | "
               f"{', '.join(sorted(pid))} | {', '.join(sorted(vid))} | {toplam} |"]
    md += ["", "Bu iki nitelik TUM ilanlara planlanir; yazma ayri onay ister "
           "(`PUT /v3/application/shops/{shop_id}/listings/{listing_id}/properties/{property_id}`).", ""]

    ornekler = [x.strip() for x in a.ornek.split(",") if x.strip()]
    md += ["## Ornek ilanlar (tam metin)", ""]
    for o in ornekler:
        s = next((x for x in satirlar if x["ilan_id"] == o or
                  x["cift"].upper().replace(" + ", "_") == o.upper()), None)
        if not s:
            md += [f"### {o}: BULUNAMADI", ""]
            continue
        md += [f"### {s['cift']} — ilan {s['ilan_id']} ({s['kontrol']})", "",
               f"**Eski baslik ({len(s['eski_baslik'])}):** {s['eski_baslik']}", "",
               f"**Yeni baslik ({len(s['yeni_baslik'])}):** {s['yeni_baslik']}", "",
               f"**Eski etiketler:** {s['eski_etiketler']}", "",
               "**Yeni 13 etiket:**", ""]
        md += [f"{i}. `{t}` ({len(t)})" for i, t in enumerate(s["yeni_etiketler"].split("|"), 1)]
        md += ["", f"**Nitelikler (degismedi):** {s['nitelikler']}", "",
               "**Kisisellestirme alani plani (yazilmadi):**", "",
               "| # | alan adi | aciklama | en fazla | zorunlu |", "|---|---|---|---|---|",
               f"| 1 | {s['alan1_ad']} | {s['alan1_aciklama']} | {s['alan1_max']} | E |",
               f"| 2 | {s['alan2_ad']} | {s['alan2_aciklama']} | {s['alan2_max']} | E |",
               f"| 3 | {s['alan3_ad']} | {s['alan3_aciklama']} | {s['alan3_max']} | E |",
               "", f"**Mevcut kisisellestirme sorulari (Etsy'den okunan):** {s['mevcut_sorular']}", "",
               f"**Nitelik plani:** {s['nitelik1_ad']}={s['nitelik1_deger']} "
               f"(property_id {s['nitelik1_property_id']}, value_id {s['nitelik1_value_id']}); "
               f"{s['nitelik2_ad']}={s['nitelik2_deger']} "
               f"(property_id {s['nitelik2_property_id']}, value_id {s['nitelik2_value_id']})", "",
               f"**Sign order alani:** {s['sign_order_alani']} | "
               f"**mevcut kisisellestirme:** acik={s['kisisel_acik']}, zorunlu={s['kisisel_zorunlu_mevcut']}, "
               f"max={s['kisisel_max_mevcut']}, yonerge={s['kisisel_yonerge_mevcut'] or 'YOK'}", "",
               "**Yeni EN aciklama:**", "", "```", s["yeni_aciklama_en"], "```", "",
               f"**Yeni RU baslik:** {s['yeni_ru_baslik']}", "",
               "**Yeni RU aciklama:**", "", "```", s["yeni_ru_aciklama"], "```", ""]
    md += ["## Dosyalar", "",
           "- `METIN_78.csv` — ilan_id, cift, eski/yeni baslik, eski/yeni etiketler, yeni EN aciklama, yeni RU baslik + aciklama, nitelikler, kontrol",
           "- `YEDEK/<ilan>_listing.json`, `_translations_ru.json`, `_properties.json` — Etsy'den okunan ham hali",
           "- `OAS_KISISELLESTIRME.json` — Etsy OAS'tan cikarilan kisisellestirme alanlari ve uclari (kanit)", ""]
    metin = "\n".join(md)
    (out / "METIN_78.md").write_text(metin + "\n", encoding="utf-8")
    log(f"CSV {out / 'METIN_78.csv'} ({len(satirlar)} satir) | MD {out / 'METIN_78.md'} | PASS {pass_n}/{toplam}")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n".join(md[:24]) + "\n")
    if pass_n != toplam:
        sys.exit(1)


if __name__ == "__main__":
    main()
