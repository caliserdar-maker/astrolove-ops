#!/usr/bin/env python3
"""78 POSTER: 5x7 + aciklama + Avustralya kargo suresi KURU KOSU (Merkez 26 Eki C; ETSY'YE YAZMA YOK).

Yalniz GET. Yazma yontemleri (put/patch/post) bu betikte kapatilir; cagrilirsa SystemExit.
Ilan basina 4 GET: listing, inventory, variation-images, translations/ru. Ayrica kargo profili 1 GET ve profil kullanan ilan
taramasi (aktif ilanlar, 100'luk sayfa).

Plan (yazim ayri betik + Serdar onayi):
 1) Envanter: her (format, renk) blogunun basina 5x7 urunu (Size "5×7″ (13×18cm)", value_ids YOK -> Etsy uretir; pod_boy_15.py:111-124
    yontemi; menu sirasi dizi sirasiyla, pod_boy_15.py:8-11). Print 19.90, Digital File 3.90, adet = ilandaki adet (999/998),
    readiness = blogun readiness_state_id'si, SKU POD-<CIFT>-5x7 / POD-<CIFT>-5x7-DIGITAL. Mevcut 130 urun (SKU, deger, value_id,
    fiyat, adet, acik, readiness) AYNEN. price/quantity/sku/readiness_on_property aynen.
 2) Kargo profili 314711751541: yalniz AU hedefi min/max teslim 7-21 (Serdar 26 Eki); diger her alan ayni.
 3) Aciklama EN (8 degisiklik: 26 Eki 4 + 28 Eki celiski 4, her biri tam 1 kez) + RU ru_poster.kur (5x7 dahil boy listesi) + kapilar.
Kapilar (ilan basina): state active (CLAUDE.md: updateListing taslagi yayina alir -> taslak ATLANIR), 130 urun / 13 bilinen boy /
5 renk / 2 format, 5x7 yok; once/sonra karsilastirma; aciklama yasak ifade + tire; RU kur PASS + RU_YASAK + ru_yazim_kapisi.
Cikti: <out>/KURU_<lid>.json, PLAN.csv, OZET.md (ilan basina degisiklik listesi), PROFIL_PLAN.json, ISTEK_TAHMINI.json."""
import argparse
import csv
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
from beyan_marka_yaz import norm  # noqa: E402

PROFIL = 314711751541
AU_YENI = (7, 21)
ETIKET_5X7 = "5×7″ (13×18cm)"
BOYLAR = {"8×10″ (20×25cm)": "8x10", "11×14″ (28×36cm)": "11x14", "12×16″ (30×41cm)": "12x16", "12×18″ (30×46cm)": "12x18",
          "16×20″ (41×51cm)": "16x20", "16×24″ (41×61cm)": "16x24", "18×24″ (46×61cm)": "18x24", "20×30″ (51×76cm)": "20x30",
          "24×30″ (61×76cm)": "24x30", "24×36″ (61×91cm)": "24x36", "A4 (21×29.7cm)": "A4", "A3 (29.7×42cm)": "A3",
          "A2 (42×59.4cm)": "A2"}
FIYAT_5X7 = {"Print": 19.90, "Digital File": 3.90}
RENKLER = ["Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment"]
# EN degisiklikleri (Serdar 26 Eki). Her eski metin aciklamada TAM 1 kez olmali.
EN_DEGISIKLIK = [
    ("13 sizes, from 8 x 10 to 24 x 36 inches, plus A4 to A2.", "14 sizes, from 5 x 7 to 24 x 36 inches, plus A4 to A2."),
    ("- High resolution: 300 dpi at the full size you choose, from 8 x 10 to 24 x 36 inches, or A4 to A2",
     "- High resolution: 300 dpi at the full size you choose, from 5 x 7 to 24 x 36 inches, or A4 to A2"),
    ("\n- US orders ship with tracking.", ""),
    ("- Delivered to your Etsy order within 24 hours. We check every personalization by hand before sending",
     "- We send a free preview via Etsy Messages within 24 hours. After you approve, your file is emailed to you within 24 hours. "
     "We check every personalization by hand before sending"),
    # Serdar 28 Eki: celiskili 4 cumlenin yeni hali (canli metinden dogrulandi: KURU_4570143815.json aciklama_ham satir 16, 22, 59)
    ("Download it from Purchases in a web browser. The Etsy app can't download files",
     "If email doesn't suit you, we can send you a download link through Etsy Messages."),
    ("For every print, we send you a preview via Etsy Messages within 24 hours of your order. We print as soon as you approve it.",
     "We send you a preview via Etsy Messages within 24 hours of your order. We print your poster or prepare your file as soon as "
     "you approve it."),
    ("Short on time? Choose the digital file. It arrives within 24 hours, ready to print or share.",
     "Short on time? Choose the digital file. Nothing to ship, so it is ready to print or share soon after you approve your preview."),
    ("If we don't hear from you within 24 hours of receiving the preview, we print the design as shown.",
     "If we don't hear from you within 24 hours of receiving the preview, we go ahead with the design as shown: we print your "
     "poster, or send your digital file as a download link in Etsy Messages."),
]
# Karar sonrasi celisen satirlar: DEGISTIRILMEZ, liste olarak raporlanir (Serdar karar verecek). Serdar 28 Eki: indirme, onizleme,
# 'Short on time' ve onay gelmezse cumleleri EN_DEGISIKLIK'e alindi; ambalaj (5x7 karariyla) ve 'Nothing is shipped' (dogru) kalir.
CELISKI = [
    ("Prints are rolled in tissue paper and sent in a thick cardboard tube. Small prints to Europe may come in a stiff flat envelope.",
     "PACKAGING Printful 5x7 icin dogrulanmadi"),
    ("- Nothing is shipped. For personal use only.",
     "dijital varyant fiziksel ilanda: AU alicisi kargo profili tahminini (7-21 + hazirlik) gorur, metin 'Nothing is shipped' der"),
]
# Galeri kartlari (canli, scripts/pod/eski78_gorsel_uret.py:45-50; 17 Eki hatti): metinle celisen kart yazilari (gorsel, aciklamada degil)
KART_CELISKI = [("kart 8", "Five colors and thirteen sizes.", "5x7 ile 14 boy"),
                ("kart 9", "Every color comes in all thirteen sizes.", "5x7 ile 14 boy"),
                ("kart 13", "US orders are tracked.", "takip satiri aciklamadan kaldiriliyor (Serdar 26 Eki)"),
                ("boy kilavuzu karesi", "See the size guide photo.", "kilavuz gorselinde 5x7 yok (olculmedi)")]
YASAK_EN = re.compile(r"Hahnem|Photo Rag|\b308\b|g/m2|gicl[eé]e|Prodigi|100% cotton|museum|ISO 9706|\bOBA\b|bright white|12-colou?r|[—–]", re.I)


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else p


def salt_okur(api):
    def yok(*a, **k):
        raise SystemExit("DUR: kuru kosuda Etsy yazma cagrisi")
    for ad in ("put", "patch", "post", "put_json", "post_json", "post_file", "delete"):
        setattr(api, ad, yok)
    asil = api._call

    def yalniz_get(method, path, *a, **k):
        if str(method).upper() != "GET":
            raise SystemExit(f"DUR: kuru kosuda {method} {path}")
        return asil(method, path, *a, **k)
    api._call = yalniz_get


def pv(p, pid):
    return next((v for v in p.get("property_values") or [] if v.get("property_id") == pid), {})


def urun_ozet(p):
    o = (p.get("offerings") or [{}])[0]
    return (p.get("sku"), tuple((v.get("property_id"), v.get("property_name"), v.get("scale_id"), tuple(v.get("values") or []),
                                 tuple(v.get("value_ids") or [])) for v in p.get("property_values") or []),
            tuple((para(x.get("price")), x.get("quantity"), bool(x.get("is_enabled")), x.get("readiness_state_id"))
                  for x in p.get("offerings") or []), len(p.get("offerings") or []), o is not None)


def kopya(p):
    return {"sku": p.get("sku") or "",
            "property_values": [{k: v[k] for k in ("property_id", "property_name", "scale_id", "value_ids", "values") if v.get(k) is not None}
                                for v in p.get("property_values") or []],
            "offerings": [{"price": para(o.get("price")), "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled")),
                           **({"readiness_state_id": o["readiness_state_id"]} if o.get("readiness_state_id") else {})}
                          for o in p.get("offerings") or []]}


def envanter_plani(inv):
    """(yuk, hata[]). Yuk = updateListingInventory govdesi (gonderilmez)."""
    hata, pr = [], inv.get("products") or []
    if len(pr) != 130:
        hata.append(f"urun {len(pr)} != 130")
    boylar = {pv(p, 513).get("values", [None])[0] for p in pr}
    if ETIKET_5X7 in boylar or any("5×7" in (b or "") or "5x7" in (b or "") for b in boylar):
        hata.append("5x7 zaten var")
    if boylar - set(BOYLAR):
        hata.append(f"bilinmeyen boy {sorted(boylar - set(BOYLAR))}")
    adet = {o.get("quantity") for p in pr for o in p.get("offerings") or []}
    if len(adet) != 1:
        hata.append(f"adet tek deger degil {sorted(adet)}")
    yeni, eklenen, onceki_blok = [], [], None
    for p in pr:
        f, r = pv(p, 514).get("values", [None])[0], pv(p, 200).get("values", [None])[0]
        if (f, r) != onceki_blok:                      # (format, renk) blogu basliyor: 5x7 basa
            onceki_blok = (f, r)
            m = re.match(r"^(POD-[A-Z]{3}_[A-Z]{3})-[0-9A-Za-z]+(-DIGITAL)?$", p.get("sku") or "")
            if not m or f not in FIYAT_5X7:
                hata.append(f"SKU/format kalibi {p.get('sku')} {f}"); continue
            o = (p.get("offerings") or [{}])[0]
            n = {"sku": f"{m.group(1)}-5x7" + ("-DIGITAL" if f == "Digital File" else ""),
                 "property_values": [{k: v[k] for k in ("property_id", "property_name", "scale_id", "value_ids", "values") if v.get(k) is not None}
                                     for v in (pv(p, 514), pv(p, 200))]
                 + [{"property_id": 513, "property_name": "Size", "values": [ETIKET_5X7]}],     # value_ids YOK: Etsy uretir
                 "offerings": [{"price": FIYAT_5X7[f], "quantity": o.get("quantity"), "is_enabled": True,
                                **({"readiness_state_id": o["readiness_state_id"]} if o.get("readiness_state_id") else {})}]}
            yeni.append(n); eklenen.append(n)
        yeni.append(kopya(p))
    yuk = {"products": yeni, **{k: inv.get(k) for k in ("price_on_property", "quantity_on_property", "sku_on_property",
                                                       "readiness_state_on_property")}}
    # once/sonra kapisi: 5x7 disi urunler birebir ayni ve ayni sirada
    once = [urun_ozet(p) for p in pr]
    sonra = [urun_ozet({**p, "offerings": [{**o, "price": {"amount": round(o["price"] * 100), "divisor": 100}} for o in p["offerings"]]})
             for p in yuk["products"] if pv(p, 513).get("values", [None])[0] != ETIKET_5X7]
    if once != sonra:
        hata.append("once/sonra: mevcut 130 urun ayni degil")
    if len(eklenen) != 10 or len(yuk["products"]) != 140:
        hata.append(f"eklenen {len(eklenen)} (10 olmali), toplam {len(yuk['products'])} (140 olmali)")
    kombi = [(pv(p, 514).get("values", [None])[0], pv(p, 200).get("values", [None])[0], pv(p, 513).get("values", [None])[0])
             for p in yuk["products"]]
    if len(set(kombi)) != len(kombi) or len(set(kombi)) != 2 * 5 * 14:
        hata.append(f"kombinasyon: {len(set(kombi))} benzersiz / {len(kombi)} (2 x 5 x 14 = 140 olmali)")
    ilk = pv(yuk["products"][0], 513).get("values", [None])[0] if yuk["products"] else None
    if ilk != ETIKET_5X7:
        hata.append(f"menu ilk boy {ilk}")
    renk_sira = [pv(p, 200).get("values", [None])[0] for p in eklenen]
    if renk_sira[:5] != RENKLER or renk_sira[5:] != RENKLER:
        hata.append(f"5x7 renk sirasi {renk_sira}")
    return yuk, eklenen, hata


def aciklama_plani(desc, boylar):
    en0 = norm(desc)
    en, hata, satir = en0, [], []
    for a, b in EN_DEGISIKLIK:
        n = en.count(a)
        if n != 1:
            hata.append(f"EN '{a[:40]}...' {n} kez (1 olmali)"); continue
        en = en.replace(a, b); satir.append({"eski": a.strip("\n"), "yeni": b})
    yas = sorted({m.group(0) for m in YASAK_EN.finditer(en)})
    if yas:
        hata.append(f"EN yasak/tire {yas}")
    ru, k = R.kur(en, {"boy": ["5x7"] + boylar})
    if not k.get("pass_"):
        hata.append(f"RU kur FAIL {k.get('hata')}")
    if ru and sorted({m.group(0) for m in E.RU_YASAK.finditer(ru)}):
        hata.append("RU_YASAK")
    celiski = [{"satir": c, "neden": n} for c, n in CELISKI if c in en] + [{"kart": k, "satir": c, "neden": n} for k, c, n in KART_CELISKI]
    yas_ru_en = sorted({m.group(0) for m in E.RU_YASAK.finditer(en)})
    if yas_ru_en:
        hata.append(f"EN'de RU_YASAK kalibi {yas_ru_en}")
    return en0, en, ru, k, satir, celiski, hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--liste", default=str(KOK.parent.parent / "data/pod/pod78_ids.csv"))
    ap.add_argument("--pilot", default="4570110121")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = E.Etsy(store), os.environ["ETSY_SHOP_ID"]
    salt_okur(api)
    ids = [x.strip() for x in a.ids.split(",") if x.strip()] or [r["listing_id"] for r in csv.DictReader(open(a.liste))]
    ids = sorted(ids, key=lambda x: x != a.pilot)               # pilot once
    plan, md = [], ["# 5x7 + ACIKLAMA + AU KURU KOSU (Etsy'ye yazma yok)", ""]
    for i, lid in enumerate(ids, 1):
        api.kota_kapisi(f"ilan {lid}")                          # CLAUDE.md: toplu islerde ilan basina kota kapisi
        x = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        rut = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        ru_simdi, ru_baslik, ru_etiket = rut.get("description") or "", rut.get("title") or "", rut.get("tags") or []
        hata = []
        if x.get("state") != "active":
            hata.append(f"state {x.get('state')} (taslak/aktif degil: updateListing yayina alir, ATLANIR)")
        yuk, eklenen, h1 = envanter_plani(inv); hata += h1
        boylar = [BOYLAR[b] for b in dict.fromkeys(pv(p, 513).get("values", [None])[0] for p in inv.get("products") or []) if b in BOYLAR]
        en0, en, ru, k, satir, celiski, h2 = aciklama_plani(x.get("description"), boylar); hata += h2
        if not h2:
            try:
                R.izin_ver(lid, ru, k)
                if not ru_baslik:
                    raise SystemExit("RU baslik okunamadi (yazimda title zorunlu, canli korunur)")
                # gercek yazim govdesi: canli RU baslik + etiketler AYNEN, yalniz aciklama yeni (etiketler gonderilmezse silinebilir)
                E.ru_yazim_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru",
                                  data={"title": ru_baslik, "description": ru, "tags": ",".join(ru_etiket)})
            except SystemExit as e:
                hata.append(f"ru_yazim_kapisi {e}")
        kayit = {"listing_id": lid, "pilot": lid == a.pilot, "state": x.get("state"), "title": x.get("title"),
                 "adet": sorted({o.get("quantity") for p in inv.get("products") or [] for o in p.get("offerings") or []}),
                 "renk_bagi": len(vi), "eklenen_5x7": eklenen, "envanter_yuk": yuk, "en_eski": en0, "en_yeni": en, "ru_simdi": ru_simdi,
                 "ru_yeni": ru, "ru_kur": k, "ru_baslik": ru_baslik, "ru_etiket": ru_etiket,
                 "ru_yazim_govdesi": {"title": ru_baslik, "description": ru, "tags": ru_etiket},
                 "envanter_ham_yedek": inv, "renk_bagi_ham": vi, "aciklama_ham": x.get("description"), "en_satir": satir, "celiski": celiski, "hata": hata, "PASS": not hata}
        (out / f"KURU_{lid}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        plan.append([lid, kayit["pilot"], x.get("state"), len(inv.get("products") or []), len(yuk["products"]), len(eklenen),
                     "/".join(map(str, kayit["adet"])), len(vi), len(satir), len(celiski), "PASS" if not hata else "FAIL", " | ".join(hata)])
        md += [f"## {lid}{' (PILOT)' if kayit['pilot'] else ''}: {'PASS' if not hata else 'FAIL ' + '; '.join(hata)}",
               f"- envanter: {len(inv.get('products') or [])} -> {len(yuk['products'])} urun; 5x7 SKU "
               + ", ".join(sorted({n['sku'] for n in eklenen})) + f"; adet {kayit['adet']}; renk bagi {len(vi)}/5",
               *[f"- EN eski: {s['eski']}\n  EN yeni: {s['yeni'] or '(satir kaldirilir)'}" for s in satir],
               f"- RU: kur {'PASS' if k.get('pass_') else 'FAIL'}; simdiki RU uzunluk {len(ru_simdi)}, yeni {len(ru)}", ""]
        print(f"[{i}/{len(ids)}] {lid} {'PASS' if not hata else 'FAIL'} istek {api.calls} kota {api.remaining}", flush=True)
    # kargo profili
    sp = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
    hed = sp.get("shipping_profile_destinations") or []
    au = [d for d in hed if d.get("destination_country_iso") == "AU"]
    yaz_govde = [{"yol": f"/shops/{{shop}}/shipping-profiles/{PROFIL}/destinations/{d.get('shipping_profile_destination_id')}",
                  "govde": {"primary_cost": para(d.get("primary_cost")), "secondary_cost": para(d.get("secondary_cost")),
                            "min_delivery_days": AU_YENI[0], "max_delivery_days": AU_YENI[1]}} for d in au]   # profil_ucretsiz.py:126 kalibi
    pplan = {"profil": PROFIL, "baslik": sp.get("title"), "hedef_sayisi": len(hed), "once_tum_hedefler": hed, "yazim_istegi": yaz_govde,
             "uyari": "Printful 5x7 AU teslim 20-22 gun (API, kosu 40179982544); 7-21 ust siniri asabilir; Etsy tahminine hazirlik 4-7 eklenir",
             "au_once": [{k: d.get(k) for k in ("shipping_profile_destination_id", "min_delivery_days", "max_delivery_days",
                                               "primary_cost", "secondary_cost", "mail_class", "shipping_carrier_id")} for d in au],
             "au_sonra": {"min_delivery_days": AU_YENI[0], "max_delivery_days": AU_YENI[1]},
             "diger_hedefler_ayni": "yazim yalniz AU hedef id'sine gider (yazim_istegi); once_tum_hedefler yedek", "hata": [] if len(au) == 1 else [f"AU hedefi {len(au)} (1 olmali)"]}
    # profili kullanan aktif ilanlar (salt okuma)
    say, ofs, kul = 0, 0, []
    while True:
        r = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": ofs}) or {}
        res = r.get("results") or []
        say += len(res); kul += [str(y.get("listing_id")) for y in res if y.get("shipping_profile_id") == PROFIL]
        ofs += 100
        if not res or ofs >= (r.get("count") or 0):
            break
    for durum in ("draft", "inactive"):                     # taslak / pasif ilanlar da profili kullaniyor mu
        r = api.get(f"/shops/{shop}/listings", params={"state": durum, "limit": 100}) or {}
        kul += [str(y.get("listing_id")) for y in r.get("results") or [] if y.get("shipping_profile_id") == PROFIL]
        say += len(r.get("results") or [])
    pod = set(ids)
    pplan.update(aktif_ilan=say, profili_kullanan=len(kul), pod78_disi_kullanan=sorted(set(kul) - pod))
    (out / "PROFIL_PLAN.json").write_text(json.dumps(pplan, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "pilot", "state", "urun_once", "urun_sonra", "eklenen_5x7", "adet", "renk_bagi", "en_degisiklik",
                    "celiski_satir", "sonuc", "hata"])
        w.writerows(plan)
    tahmin = {"kuru_istek": api.calls, "kota_kalan_kosu_sonu": api.remaining,
              "yazim_tahmini": {"ilan_basina": "GET listing+inventory+variation-images (3) + PUT inventory (1) + GET inventory (1) + "
                                               "GET variation-images (1, bag bozulursa +1 POST) + GET translations/ru (1, baslik/etiket) + "
                                               "PATCH listing (1) + GET listing (1) + PUT translations/ru (1) + GET translations/ru (1) = 11 "
                                               "(en cok 12); token yenileme ve 5xx tekrarlari dahil degil (tahmin)",
                                "ilan": len(ids), "toplam_ilan": 11 * len(ids), "en_cok": 12 * len(ids), "profil": 3,
                                "toplam": 11 * len(ids) + 3, "toplam_en_cok": 12 * len(ids) + 3,
                                "not": "kalan kota (bu kosu sonu) ile ayni gun yazim sigmazsa iki gune bolunur; kota siniri 10"}}
    (out / "ISTEK_TAHMINI.json").write_text(json.dumps(tahmin, ensure_ascii=False, indent=1), encoding="utf-8")
    gecen = sum(1 for p in plan if p[10] == "PASS")
    md[1:1] = [f"- ilan {len(plan)}: PASS {gecen}, FAIL {len(plan) - gecen}; pilot {a.pilot}",
               f"- profil {PROFIL}: AU {pplan['au_once']} -> {AU_YENI}; profili kullanan aktif ilan {len(kul)}/{say}, 78 disi "
               f"{pplan['pod78_disi_kullanan']}",
               f"- istek {api.calls}, kota {api.remaining}; yazim tahmini {tahmin['yazim_tahmini']['toplam']}-{tahmin['yazim_tahmini']['toplam_en_cok']}",
               "- Celisen satirlar (DEGISTIRILMEDI, Serdar karari): " + "; ".join(f"'{c}' ({n})" for c, n in CELISKI),
               "- Celisen galeri kartlari (gorsel; ayri is, CLAUDE.md GALERI kurali): " + "; ".join(f"{k} '{c}' ({n})" for k, c, n in KART_CELISKI),
               f"- AU uyarisi: {pplan['uyari']}", ""]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:6]))
    return 0 if gecen == len(plan) and not pplan["hata"] else 1


if __name__ == "__main__":
    sys.exit(main())
