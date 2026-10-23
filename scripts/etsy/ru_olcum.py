#!/usr/bin/env python3
"""RU aciklama olcumu (Serdar 23 Eki; SALT OKUMA, Etsy'ye yazma YOK). Beyan partilerinden once: 234 aktif ilanin EN ve RU
aciklamasi + gercek boy/renk/format listesi (envanter) okunur, RU'da sayilir:
  boy sayisi ve boy adlari (envanterle kiyas), kagit adi, tedarikci adi, Art'siz "AstroLove", uzun/orta tire,
  EN'de olmayan ya da EN ile celisen bilgi (isim/mesaj siniri, sure, renk sayisi, dijital format, fiyat, EN'de olmayan sayilar).

Modlar:
  oku    : Etsy (ilan basina api.kota_kapisi) -> <out>/HAM.json.gz, ardindan analiz.
  analiz : yalniz --ham dosyasindan (Etsy yok) -> RU_OLCUM.csv + RU_OZET.json + RU_OZET.md.
Istek: liste ~3 + bolum 1 + batch 3 + ilan basina 2 (RU tekil + envanter) ~ 475. Musteri verisi yok (yalniz ilan metni)."""
import argparse
import csv
import gzip
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beyan_marka_yaz as B  # noqa: E402

TEDARIKCI = re.compile(r"\b(Prodigi|Printful|Gelato|Printify|Gooten|Lulu|Printique|WhiteWall|Gelato|CustomCat|SPOD)\b", re.I)
KAGIT = re.compile(r"Hahnem[uü]hle|Photo\s*Rag|\b\d{3}\s*(?:г/м²|г/м2|gsm|g/m²)|хлопк\w*|cotton|matte art paper|art paper|"
                   r"бескислотн\w*|acid[- ]free|museum|музейн\w*|ISO\s*9706|жикле|gicl[eé]e", re.I)
CIFT = re.compile(r"(\d{1,2})\s*[×xX]\s*(\d{1,2})(?!\s*(?:см|cm|мм|mm))")
A_BOY = re.compile(r"\bA([0-6])\b")
OZ = re.compile(r"(\d{2})\s*(?:oz|унц)", re.I)
BOY_SAYI_RU = re.compile(r"(\d+)\s+РАЗМЕР", re.I)
BOY_SAYI_EN = re.compile(r"(\d+)\s+sizes", re.I)
RENK_SAYI_RU = re.compile(r"(\d+)\s+ЦВЕТ", re.I)
ISIM_EN = re.compile(r"up to (\d+) letters", re.I)
ISIM_RU = re.compile(r"до (\d+) букв", re.I)
MESAJ_EN = re.compile(r"up to (\d+) characters", re.I)
MESAJ_RU = re.compile(r"до (\d+) символ", re.I)
SURE_EN = re.compile(r"(\d+)\s*(?:to\s*\d+\s*)?(business days|days|hours)", re.I)
SURE_RU = re.compile(r"(\d+)\s*(?:(?:[-–]|до)\s*\d+\s*)?(рабоч\w*\s*дн\w*|дн\w*|день|дня|час\w*|недел\w*)", re.I)
FIYAT = re.compile(r"\$\s*\d|USD|руб|₽|€|£")
DIJITAL_RU = re.compile(r"цифров|файл|JPG|скача", re.I)
ONIZ_EN = re.compile(r"\bpreview\b", re.I)
ONIZ_RU = re.compile(r"превью|макет|предпросмотр|эскиз|согласован|утвержд", re.I)
STIL_EN = re.compile(r"(\d+)\s+STYLES", re.I)
STIL_RU = re.compile(r"(\d+)\s+СТИЛ", re.I)
ISIM_ISTISNA_RU = re.compile(r"больше\s+\d+\s+букв", re.I)
KIRIL_RU = re.compile(r"на русском|кириллиц", re.I)


def basliklar(t):
    """Bolum basligi satirlari: tamami BUYUK harf (>= 4 harf) ya da [ ... ] icinde."""
    out = []
    for s in (t or "").splitlines():
        s = s.strip()
        harf = [c for c in s if c.isalpha()]
        if (s.startswith("[") and s.endswith("]")) or (len(harf) >= 4 and all(c.isupper() for c in harf) and len(s) <= 60):
            out.append(s)
    return out


def boy_ad(v):
    """Envanter/metin boy adi -> anahtar: '8x10', 'A4', '11oz'."""
    v = str(v)
    m = re.match(r"\s*A([0-6])\b", v)
    if m:
        return f"A{m.group(1)}"
    m = re.search(r"(\d{2})\s*oz", v, re.I)
    if m:
        return f"{m.group(1)}oz"
    m = re.search(r"(\d{1,2})\s*[×xX]\s*(\d{1,2})", v)
    return f"{m.group(1)}x{m.group(2)}" if m else v.strip()


def envanter_ozet(inv):
    boy, renk, fmt, sku = set(), set(), set(), []
    for p in (inv or {}).get("products") or []:
        if p.get("is_deleted"):
            continue
        sku.append(p.get("sku"))
        for pv in p.get("property_values") or []:
            ad, vals = (pv.get("property_name") or "").lower(), pv.get("values") or []
            if ad == "size":
                boy.update(boy_ad(v) for v in vals)
            elif "color" in ad:
                renk.update(vals)
            elif ad == "format":
                fmt.update(vals)
    return dict(boy=sorted(boy), renk=sorted(renk), format=sorted(fmt), sku_sayi=len(sku))


def metin_boylar(t):
    t = t or ""
    s = {f"{a}x{b}" for a, b in CIFT.findall(t) if int(a) >= 5}
    s |= {f"A{a}" for a in A_BOY.findall(t)}
    s |= {f"{a}oz" for a in OZ.findall(t)}
    return s


def sayilar(t):
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", t or ""))


def ilk(rx, t):
    m = rx.search(t or "")
    return int(m.group(1)) if m else None


def analiz_bir(r):
    en, ru = B.norm(r.get("en")), B.norm(r.get("ru"))
    inv = r["envanter"]
    o = dict(listing_id=r["listing_id"], aile=r["aile"], ru_var=bool(ru.strip()), url=f"https://www.etsy.com/listing/{r['listing_id']}")
    o["sku_boy_sayi"], o["sku_boylar"] = len(inv["boy"]), " ".join(inv["boy"])
    o["sku_renk_sayi"], o["sku_format"] = len(inv["renk"]), " ".join(inv["format"])
    o["uretim_ortagi"] = "; ".join(f"{a} {b} ({c})" for a, b, c in (r.get("ortak") or []))
    o["en_boy_beyan"], o["ru_boy_beyan"] = ilk(BOY_SAYI_EN, en), ilk(BOY_SAYI_RU, ru)
    rb = metin_boylar(ru)
    sku_b = set(inv["boy"])
    o["ru_boylar"] = " ".join(sorted(rb))
    o["ru_boy_fazla"] = " ".join(sorted(rb - sku_b)) if rb else ""
    o["ru_boy_eksik"] = " ".join(sorted(metin_boylar(en) - rb))   # EN'de gecen boy RU'da yok (EN de aralik yazabilir)
    o["ru_kagit"] = "; ".join(sorted({m.group(0) for m in KAGIT.finditer(ru)}))
    o["en_kagit"] = "; ".join(sorted({m.group(0) for m in KAGIT.finditer(en)}))
    o["ru_tedarikci"] = "; ".join(sorted({m.group(1) for m in TEDARIKCI.finditer(ru)}))
    o["en_tedarikci"] = "; ".join(sorted({m.group(1) for m in TEDARIKCI.finditer(en)}))
    o["ru_astrolove_artsiz"] = len(B.MARKA.findall(ru))
    o["ru_tire"], o["en_tire"] = len(B.TIRE.findall(ru)), len(B.TIRE.findall(en))
    o["en_isim"], o["ru_isim"] = ilk(ISIM_EN, en), ilk(ISIM_RU, ru)
    o["en_mesaj"], o["ru_mesaj"] = ilk(MESAJ_EN, en), ilk(MESAJ_RU, ru)
    o["ru_renk_beyan"] = ilk(RENK_SAYI_RU, ru)
    o["en_sure"] = " ".join(sorted({f"{a} {b.lower()}" for a, b in SURE_EN.findall(en)}))
    o["ru_sure"] = " ".join(sorted({f"{a} {b.lower()}" for a, b in SURE_RU.findall(ru)}))
    o["ru_fiyat"] = len(FIYAT.findall(ru))
    dijital = any("digital" in f.lower() for f in inv["format"])
    o["ru_dijital_anilir"] = bool(DIJITAL_RU.search(ru))
    boy_sayilari = {x for b in sku_b | rb for x in re.findall(r"\d+", b)}
    boy_sayilari |= {str(x) for x in (o["ru_boy_beyan"], o["ru_renk_beyan"]) if x is not None}   # ayri kiyaslaniyor
    o["ru_sayi_en_yok"] = " ".join(sorted(sayilar(ru) - sayilar(en) - boy_sayilari, key=lambda x: float(x.replace(",", "."))))
    # iki yon (inceleme 23 Eki): EN'deki bilgi RU'da var mi
    en_boy_say = {str(x) for x in (o["en_boy_beyan"],) if x is not None}
    o["en_sayi_ru_yok"] = " ".join(sorted(sayilar(en) - sayilar(ru) - boy_sayilari - en_boy_say, key=lambda x: float(x.replace(",", "."))))
    o["en_baslik"], o["ru_baslik"] = len(basliklar(en)), len(basliklar(ru))
    en_sn = {a for a, _ in SURE_EN.findall(en)}
    ru_sn = {a for a, _ in SURE_RU.findall(ru)}
    o["sure_ru_yok"] = " ".join(sorted(en_sn - ru_sn, key=int))
    o["oniz_en"], o["oniz_ru"] = bool(ONIZ_EN.search(en)), bool(ONIZ_RU.search(ru))
    o["en_stil"], o["ru_stil"] = ilk(STIL_EN, en), ilk(STIL_RU, ru)
    o["ru_isim_istisna"] = bool(ISIM_ISTISNA_RU.search(ru))
    o["ru_kiril_mesaj"] = bool(KIRIL_RU.search(ru))
    s = []
    if o["ru_var"]:
        if o["ru_boy_beyan"] is not None and o["ru_boy_beyan"] != o["sku_boy_sayi"]:
            s.append("boy_sayisi")
        if o["ru_boy_fazla"]:
            s.append("boy_fazla")
        if o["ru_boy_eksik"]:
            s.append("boy_eksik")
        if o["ru_kagit"] and set(o["ru_kagit"].lower().split("; ")) - set(o["en_kagit"].lower().split("; ")) and \
                re.search(r"Hahnem|Photo\s*Rag|\d{3}\s*г", o["ru_kagit"]) and not re.search(r"Hahnem|Photo\s*Rag", o["en_kagit"]):
            s.append("kagit_celiski")
        if o["ru_tedarikci"] and o["ru_tedarikci"] != o["en_tedarikci"]:
            s.append("tedarikci")
        if o["ru_astrolove_artsiz"]:
            s.append("marka_artsiz")
        if o["ru_tire"]:
            s.append("tire")
        if (o["en_isim"], o["ru_isim"]) != (None, None) and o["en_isim"] != o["ru_isim"]:
            s.append("isim_siniri")
        if (o["en_mesaj"], o["ru_mesaj"]) != (None, None) and o["en_mesaj"] != o["ru_mesaj"]:
            s.append("mesaj_siniri")
        if o["ru_renk_beyan"] is not None and o["sku_renk_sayi"] and o["ru_renk_beyan"] != o["sku_renk_sayi"]:
            s.append("renk_sayisi")
        if dijital and not o["ru_dijital_anilir"]:
            s.append("dijital_yok")
        if o["ru_fiyat"]:
            s.append("fiyat")
        if o["ru_sayi_en_yok"]:
            s.append("ru_sayi_en_yok")
        if o["en_sayi_ru_yok"]:
            s.append("en_sayi_ru_yok")
        if o["ru_baslik"] < o["en_baslik"]:
            s.append("bolum_eksik")
        if o["sure_ru_yok"]:
            s.append("sure_eksik")
        if o["oniz_en"] and not o["oniz_ru"]:
            s.append("onizleme_yok")
        if o["en_stil"] != o["ru_stil"]:
            s.append("stil_sayisi")
        if o["ru_isim_istisna"]:
            s.append("isim_istisna")
        if o["ru_kiril_mesaj"] and not re.search(r"Cyrillic|Russian", en, re.I):
            s.append("ru_ek_bilgi")
    import etsy_common as E   # Serdar 23 Eki not: 2b deseni (RU_YASAK) her ailenin RU baslik + aciklamasinda olculur
    ru_hepsi = " ".join([ru, B.norm(r.get("ru_title"))])
    o["ru_yasak"] = "; ".join(sorted({m.group(0) for m in E.RU_YASAK.finditer(ru_hepsi)}))
    if o["ru_yasak"]:
        s.append("ru_yasak")
    o["sorunlar"] = " ".join(s)
    return o


def insa(r):
    """Poster: canli EN (+ beyan) ve envanterden yeni RU kur (ru_poster), yeni RU'yu ayni kurallarla olc."""
    import ru_poster
    en = B.norm(r.get("en"))
    try:
        en1 = ru_poster.poster_en(en)   # beyan + Latin harf notu (Serdar 23 Eki madde 1-2)
    except (B.Dur, ValueError) as e:
        return dict(insa_pass=False, insa_hata=f"poster_en DUR: {e}", insa_sorun="")
    ru, k = ru_poster.kur(en1, r["envanter"])
    s = analiz_bir(dict(r, en=en1, ru=ru))["sorunlar"] if k["pass_"] else ""
    return dict(insa_pass=k["pass_"] and not s, insa_hata="; ".join(k["hata"]), insa_sorun=s, _en=en1, _ru=ru)


def analiz(ham, out):
    satir = [analiz_bir(r) for r in ham]
    for o, r in zip(satir, ham):
        if r["aile"] == "poster":
            x = insa(r)
            o.update({k: v for k, v in x.items() if not k.startswith("_")})
        else:
            o.update(insa_pass="", insa_hata="", insa_sorun="")
    with open(out / "RU_OLCUM.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0].keys()))
        w.writeheader(); w.writerows(satir)
    oz = {}
    for o in satir:
        a = oz.setdefault(o["aile"], dict(ilan=0, ru_var=0, sorunlu=0, tur={}, ornek=[]))
        a["ilan"] += 1; a["ru_var"] += o["ru_var"]
        if o["insa_pass"] != "":
            a["insa_pass"] = a.get("insa_pass", 0) + bool(o["insa_pass"])
        if o["sorunlar"]:
            a["sorunlu"] += 1
            for t in o["sorunlar"].split():
                a["tur"][t] = a["tur"].get(t, 0) + 1
            if len(a["ornek"]) < 3:
                a["ornek"].append({k: o[k] for k in ("listing_id", "url", "sorunlar", "sku_boy_sayi", "ru_boy_beyan", "ru_boy_fazla",
                                                       "ru_kagit", "ru_tedarikci", "ru_sayi_en_yok")})
    (out / "RU_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    for aile in sorted({r["aile"] for r in ham}):   # elle kontrol icin aile basina 2 ornek metin (ilan metni, musteri verisi yok)
        ornek = [r for r in ham if r["aile"] == aile][:2]
        (out / f"ORNEK_{aile}.txt").write_text("\n\n".join(
            f"===== {r['listing_id']} | {r.get('title')}\nENVANTER {json.dumps(r['envanter'], ensure_ascii=False)}\nORTAK {r.get('ortak')}\n"
            f"----- RU BASLIK: {r.get('ru_title')}\n----- RU\n{B.norm(r.get('ru'))}\n----- EN\n{B.norm(r.get('en'))}" for r in ornek) + "\n",
            encoding="utf-8")
    md = ["# RU olcum ozeti (salt okuma)", ""]
    for a, v in oz.items():
        md.append(f"- {a}: {v['ilan']} ilan, RU var {v['ru_var']}, sorunlu {v['sorunlu']}, yeni RU kurulum PASS {v.get('insa_pass', '-')}; " +
                  ", ".join(f"{k} {n}" for k, n in sorted(v["tur"].items(), key=lambda x: -x[1])))
    (out / "RU_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return oz


def oku(api, shop, out):
    bolum = {str(s["shop_section_id"]): s.get("title") for s in (api.get(f"/shops/{shop}/sections") or {}).get("results") or []}
    ids = B.aktif_idler(api, shop)
    ilan = []
    for k in range(0, len(ids), 100):
        ilan += (api.get("/listings/batch", {"listing_ids": ",".join(ids[k:k + 100])}) or {}).get("results") or []
        B.kota(api)
    ham = []
    for n, L in enumerate(sorted(ilan, key=lambda x: int(x["listing_id"])), 1):
        lid = str(L["listing_id"])
        api.kota_kapisi(f"ilan {lid}")   # Serdar 23 Eki: ilan basina kota kapisi (esik aktifse)
        ru = B.ru_tekil(api, shop, lid)
        inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
        B.kota(api)
        ham.append(dict(listing_id=lid, aile=B.BOLUM_AILE.get(bolum.get(str(L.get("shop_section_id"))), "?"), state=L.get("state"),
                        title=L.get("title"), en=L.get("description"), ru=(ru or {}).get("description"), ru_title=(ru or {}).get("title"),
                        envanter=envanter_ozet(inv), ortak=B.ortak(L)))
        if n % 25 == 0:
            print(f"[{n}/{len(ilan)} %{100 * n // len(ilan)}] kota {api.remaining}", flush=True)
    with gzip.open(out / "HAM.json.gz", "wt", encoding="utf-8") as f:
        json.dump(ham, f, ensure_ascii=False)
    print(f"OKU: {len(ham)} ilan | istek {api.calls} | kota {api.remaining}", flush=True)
    return ham


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["oku", "analiz"], required=True)
    ap.add_argument("--ham", help="analiz: HAM.json.gz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.mod == "analiz":
        with gzip.open(a.ham, "rt", encoding="utf-8") as f:
            ham = json.load(f)
    else:
        k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        B.mask(k); B.mask(s)
        store = B.TokenStore(os.environ["TOKEN_FILE"], k, s)
        if store.needs_refresh():
            store.refresh()
        api = B.Etsy(store)
        try:
            ham = oku(api, os.environ["ETSY_SHOP_ID"], out)
        except B.Dur as e:
            print(f"DUR: {e} | istek {api.calls} | kota {api.remaining}", flush=True); sys.exit(3)
    analiz(ham, out)


if __name__ == "__main__":
    main()
