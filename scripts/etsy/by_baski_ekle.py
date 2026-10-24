#!/usr/bin/env python3
"""BIZIM YILIMIZ (yil donumu, bolum 60895624): "Shipped print 8x10" ($29) secenegini ve baski ayarlarini KURAR (v2).

Serdar onayi 24 Eki 2026 (Genel Merkez): tedarikci Printful ana + Shortrun ABD yedek; baski geri gelir.
v2 kararlari (Serdar 24 Eki "ok"): kargo profili BASKI profili 318080539024 (secenek B: AU ve diger ulkeler de ucretsiz,
teslim gunleri ayni; profil_yaz modu);
baski urunlerinin hazirligi ortak 4-7 gun (1517641240112), dijitaller oldugu gibi; uretim ortagi 5817638 ("Printing and
Fulfillment Partner", US) baglanir; materials "matte art paper", "ink", "digital file"; baski SKU = ayni stilin FILE8X10
SKU'su -> PRINT8X10. Bagimsiz inceleme (24 Eki) bulgulari: baski 77 ilanda burc_gift_yaz.py ile kaldirildi (profil,
materials, ortak, hazirlik da degisti), bu betik 'ters islem' degil HEDEF DURUMA YAKINSAR: her parca ayri okunur, yalniz
farkli olan yazilir; tekrar kosu guvenlidir (yarim kalan ilan tamamlanir).

Ilan basina hedef:
  envanter : 5 stil x (Digital card 5x7, Digital file 8x10) AYNEN (sku, value_ids, fiyat, stok, hazirlik) +
             5 stil x Shipped print 8x10: 29.00, stok >= 1, acik, hazirlik 1517641240112, SKU ...-PRINT8X10;
             readiness_state_on_property [514]
  ilan     : aciklamada baski satirlari (4 parca, her biri TAM 1 kez), materials hedef, uretim ortagi [5817638]
  ilan     : kargo profili 318080539024 (once profil_yaz: tum hedefler ucretsiz)
  degismez : state active, baslik, etiket, listing_type physical, stil-gorsel baglari (ada gore)
Modlar: oku (plan + ham veri, yazma yok, DURMAZ: her ilan raporlanir) | yaz (--confirm BASKI_EKLE; --hepsi: BASKI_EKLE_HEPSI;
ilk FAIL'de DUR). Ozet her durumda (istisna dahil) out/BY_BASKI_EKLE_<MOD>.json'a yazilir.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

P_STYLE, P_FORMAT = 513, 514
KART, DOSYA, BASKI = "Digital card 5x7", "Digital file 8x10", "Shipped print 8x10"
FIYAT = 29.00
DIJ_FIYAT = {KART: 3.90, DOSYA: 4.90}
BOLUM = 60895624
PROFIL_DIJITAL, PROFIL_BASKI = 318577242658, 318080539024   # BY Digital Free Worldwide / BY Print 8x10 Worldwide
PROFIL = PROFIL_BASKI          # HEDEF (Serdar 24 Eki secenek B): baski profili, tum hedefler ucretsiz, gercekci teslim gunleri
KABUL_PROFIL = {PROFIL_DIJITAL, PROFIL_BASKI}
# Baski profili hedefleri (by78_kargo_sku_aciklama.HEDEF, 15 Eki): anahtar -> (ucret simdi, ucret hedef, min gun, max gun)
PROFIL_HEDEF = {"US": (0, 0, 3, 8), "EU": (0, 0, 5, 12), "GB": (0, 0, 5, 10), "AU": (5, 0, 5, 10), "EVERYWHERE": (12, 0, 7, 21)}
ONAY_PROFIL = "PROFIL_UCRETSIZ"
PARTNER = 5817638              # "Printing and Fulfillment Partner", United States (kupa_taslak.py, Serdar 18 Eki)
HAZIRLIK_BASKI = 1517641240112  # magaza ortak 4-7 gun tanimi (burc_gift_yaz.ORTAK_HAZIRLIK); okunarak dogrulanir
MATERIALS = ["matte art paper", "ink", "digital file"]
ONAY, ONAY_HEPSI = "BASKI_EKLE", "BASKI_EKLE_HEPSI"
ISTEK_TAHMIN = 16   # ilan basina en fazla istek (3 oku + PUT + 2 bag + 2 PATCH + 3x2 geri okuma + bag okuma); kural: tahmini + KOTA_SINIRI
BEKLE_SN = 10
OUT = Path("out")

SATIR_TESLIM = ("- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping to the US, UK "
                "and EU. Estimated delivery: US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days. For other "
                "countries, see the delivery estimate at checkout.")
SATIR_FORMAT = ("- Shipped print 8x10: printed on premium matte art paper with long-lasting inks and shipped to you by our "
                "production partner.")
DEGIS = [  # (simdiki, yeni)
    ("As soon as you approve it, we prepare your file.", "As soon as you approve it, we prepare your file or your print."),
    ("Digital files can't be refunded once sent.",
     "Digital files can't be refunded once sent. If your print arrives damaged, send us a photo within 7 days and we'll "
     "replace it at no cost."),
]
SONRASINA = [  # (bu satirdan sonra, eklenecek satir)
    ("- Digital card and digital file: sent in Etsy Messages as soon as you approve your preview.", SATIR_TESLIM),
    ("- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.", SATIR_FORMAT),
]
# CLAUDE.md "Urun metni" tam listesi (KAGIT 23 Eki + Yasak) + tedarikci adlari
YASAK = [(re.compile("[–—]"), "uzun/orta tire"),
         (re.compile(r"hahnem|photo\s*rag|gicl[eé]e|prodigi|printful|shortrun|printify|gelato", re.I), "yasak marka/kagit/tedarikci"),
         (re.compile(r"308\s*(g|gsm)|g/m2|g/m²|100\s*%\s*cotton|%\s*100\s*cotton|cotton\s*rag|museum|iso\s*9706", re.I), "yasak kagit iddiasi"),
         (re.compile(r"oba[\s-]*free|bright\s*white|12[\s-]*colou?r", re.I), "yasak ifade"),
         (re.compile(r"\b\d{2,3}\s*(-|to)\s*\d{2,3}\s*years?\b|\b\d{2,3}\+?\s*years?\s*(of\s*)?(life|lasting|archival)", re.I), "omur yili"),
         (re.compile(r"instant\s*download", re.I), "instant download (dijital Etsy Messages ile gider)"),
         (re.compile(r"frame", re.I), "frame (BY cercevesiz; by78 kurali)"),
         (re.compile(r"AstroLove(?!Art)"), "marka adi AstroLoveArt olmali")]


class Dur(Exception):
    pass


def log(m):
    print(m, flush=True)


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else round(float(p), 2)


def norm(t):
    return html.unescape(t or "").replace("\r\n", "\n")


def esdeger(a, b):
    return [ln.rstrip() for ln in (a or "").strip().split("\n")] == [ln.rstrip() for ln in (b or "").strip().split("\n")]


# ---------------- aciklama ----------------

def aciklama_plani(d0):
    """(durum, yeni_metin). durum: TAMAM (4 parca var, eskiler yok) | YAZ (4 parca yok, 4 capa TAM 1 kez) | Dur (kismi/kayma)."""
    t = norm(d0)
    satirlar = [s.strip() for s in t.split("\n")]
    yeni_var = [t.count(DEGIS[0][1]) == 1, t.count(DEGIS[1][1]) == 1,
                satirlar.count(SATIR_TESLIM) == 1, satirlar.count(SATIR_FORMAT) == 1]
    if all(yeni_var):
        sonuc = t
        durum = "TAMAM"
    elif not any(yeni_var) and "Shipped print" not in t:
        sonuc = t
        for eski, yeni in DEGIS:
            if sonuc.count(eski) != 1:
                raise Dur(f"aciklama capasi {sonuc.count(eski)} kez: {eski[:60]}")
            sonuc = sonuc.replace(eski, yeni)
        sl = sonuc.split("\n")
        for once, ekle in SONRASINA:
            idx = [i for i, s in enumerate(sl) if s.strip() == once]
            if len(idx) != 1:
                raise Dur(f"aciklama satiri {len(idx)} kez: {once[:60]}")
            sl.insert(idx[0] + 1, ekle)
        sonuc = "\n".join(sl)
        durum = "YAZ"
    else:
        raise Dur(f"aciklamada baski metni KISMI (parcalar {yeni_var}); elle bakilmali")
    for rx, ad in YASAK:
        m = rx.search(sonuc)
        if m:
            raise Dur(f"aciklamada {ad}: '{m.group(0)}'")
    return durum, sonuc


# ---------------- envanter ----------------

def pvd(p):
    return {v["property_id"]: v for v in p.get("property_values") or []}


def anahtar(p):
    d = pvd(p)
    return d[P_STYLE]["values"][0], d[P_FORMAT]["values"][0]


def teklif(p):
    canli = [o for o in p.get("offerings") or [] if not o.get("is_deleted")]
    if len(canli) != 1:
        raise Dur(f"urun {p.get('sku')}: silinmemis teklif sayisi {len(canli)}")
    return canli[0]


def urunler_canli(inv):
    return [p for p in inv.get("products") or [] if not p.get("is_deleted")]


def imza(inv):
    """{(stil, format): (sku, fiyat, stok, acik, hazirlik, stil_vid, format_vid)}; silinmis urun/teklif sayilmaz."""
    s = {}
    for p in urunler_canli(inv):
        d = pvd(p)
        o = teklif(p)
        s[anahtar(p)] = (p.get("sku") or "", para(o["price"]), o.get("quantity"), o.get("is_enabled") is True,
                         o.get("readiness_state_id"), tuple(d[P_STYLE].get("value_ids") or []),
                         tuple(d[P_FORMAT].get("value_ids") or []))
    return s


def baski_sku(dosya_sku):
    if not re.fullmatch(r"BY-[A-Z]{3}_[A-Z]{3}-[A-Z]+-FILE8X10", dosya_sku or ""):
        raise Dur(f"FILE8X10 SKU beklenen sablonda degil: '{dosya_sku}'")
    return dosya_sku[: -len("FILE8X10")] + "PRINT8X10"


def envanter_plani(inv):
    """(durum, govde, stiller). durum TAMAM | YAZ. Dijital urunler aynen; baski urunleri hedefe getirilir."""
    i0 = imza(inv)
    stiller = []
    for p in urunler_canli(inv):
        st = anahtar(p)[0]
        if st not in stiller:
            stiller.append(st)
    fmts = {k[1] for k in i0}
    if len(stiller) != 5 or not fmts <= {KART, DOSYA, BASKI} or not {KART, DOSYA} <= fmts:
        raise Dur(f"envanter yapisi beklenmedik: {len(i0)} urun, stil {stiller}, format {sorted(fmts)}")
    if any((st, f) not in i0 for st in stiller for f in (KART, DOSYA)):
        raise Dur("her stilde kart + dosya yok")
    nb = sum(1 for k in i0 if k[1] == BASKI)
    if nb not in (0, 5) or len(i0) != 10 + nb:
        raise Dur(f"baski urunu sayisi {nb}, toplam {len(i0)}")
    for k, v in i0.items():
        if k[1] in DIJ_FIYAT and v[1] != DIJ_FIYAT[k[1]]:
            raise Dur(f"dijital fiyat {k}: {v[1]} (beklenen {DIJ_FIYAT[k[1]]})")
        if k[1] in DIJ_FIYAT and not ((v[2] or 0) >= 1 and v[3]):
            raise Dur(f"dijital urun satilamaz durumda {k}: stok {v[2]} acik {v[3]}")
    for f in (KART, DOSYA):
        hz = {v[4] for k, v in i0.items() if k[1] == f}
        if len(hz) != 1:
            raise Dur(f"{f} urunlerinde hazirlik tek degil: {hz} (readiness_state_on_property [514] kurulamaz)")
    skular = [i0[(st, f)][0] for st in stiller for f in (KART, DOSYA)]
    if len(set(skular)) != 10:
        raise Dur(f"dijital SKU'lar dolu ve farkli degil: {skular}")
    hedef_baski = {st: baski_sku(i0[(st, DOSYA)][0]) for st in stiller}
    urunler = []
    for st in stiller:
        for p in urunler_canli(inv):
            if anahtar(p)[0] != st:
                continue
            o = teklif(p)
            pv = [dict(property_id=v["property_id"], property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                       values=v.get("values")) for v in p.get("property_values") or []]
            if anahtar(p)[1] == BASKI:
                continue
            urunler.append(dict(sku=p.get("sku") or "", property_values=pv,
                                offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled") is True,
                                                readiness_state_id=o.get("readiness_state_id"))]))
        mevcut = next((p for p in urunler_canli(inv) if anahtar(p) == (st, BASKI)), None)
        dosya_pv = pvd(next(p for p in urunler_canli(inv) if anahtar(p) == (st, DOSYA)))
        stil_pv = dosya_pv[P_STYLE]
        if mevcut:
            pv = [dict(property_id=v["property_id"], property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                       values=v.get("values")) for v in mevcut.get("property_values") or []]
            stok = teklif(mevcut).get("quantity") or 0
        else:
            pv = [dict(property_id=P_STYLE, property_name=stil_pv.get("property_name") or "Style", value_ids=stil_pv.get("value_ids"),
                       values=stil_pv.get("values")),
                  dict(property_id=P_FORMAT, property_name=dosya_pv[P_FORMAT].get("property_name") or "Format", values=[BASKI])]
            stok = 0
        urunler.append(dict(sku=hedef_baski[st], property_values=pv,
                            offerings=[dict(price=FIYAT, quantity=stok if stok >= 1 else 999, is_enabled=True,
                                            readiness_state_id=HAZIRLIK_BASKI)]))
    sku_on = [P_STYLE, P_FORMAT]
    rd_on = [P_STYLE, P_FORMAT]   # iki menulu ilanda *_on_property ya bos ya iki ozellik (kupa_taslak.py:505 18 Eki 400, by78:338)
    govde = dict(products=urunler, price_on_property=inv.get("price_on_property") or [],
                 quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=sku_on,
                 readiness_state_on_property=rd_on)
    tamam = nb == 5 and envanter_hedefte(inv, i0, hedef_baski, govde) == []
    return ("TAMAM" if tamam else "YAZ"), govde, stiller, hedef_baski


def envanter_hedefte(inv, dijital_once, hedef_baski, beklenen_on=None):
    """Hedef durumdan sapmalari listeler (bos = hedefte). dijital_once: dijital urunlerin beklenen imzasi."""
    f = []
    i = imza(inv)
    # value_id'ler haric (Etsy PUT'ta degistirirse stil-gorsel baglari ada gore onarilir; ilan() ayrica not dusur)
    dij = {k: v[:5] for k, v in i.items() if k[1] != BASKI}
    bek = {k: v[:5] for k, v in dijital_once.items() if k[1] != BASKI}
    if dij != bek:
        f.append("dijital urunler degisti: " + str(sorted(set(dij.items()) ^ set(bek.items())))[:300])
    b = {k: v for k, v in i.items() if k[1] == BASKI}
    if len(b) != 5:
        f.append(f"baski urunu {len(b)} != 5")
    for (st, _), v in b.items():
        if (v[0], v[1], v[3], v[4]) != (hedef_baski.get(st), FIYAT, True, HAZIRLIK_BASKI) or not (v[2] or 0) >= 1:
            f.append(f"baski {st}: sku {v[0]} fiyat {v[1]} stok {v[2]} acik {v[3]} hazirlik {v[4]}")
    if sorted(inv.get("readiness_state_on_property") or []) != [P_STYLE, P_FORMAT]:
        f.append(f"readiness_state_on_property {inv.get('readiness_state_on_property')}")
    if sorted(inv.get("sku_on_property") or []) != [P_STYLE, P_FORMAT]:
        f.append(f"sku_on_property {inv.get('sku_on_property')}")
    if beklenen_on is not None:
        for k in ("price_on_property", "quantity_on_property"):
            if sorted(inv.get(k) or []) != sorted(beklenen_on.get(k) or []):
                f.append(f"{k} {inv.get(k)} (beklenen {beklenen_on.get(k)})")
    sat = [(p.get("sku"), o.get("quantity"), o.get("is_enabled")) for p in urunler_canli(inv)
           for o in p.get("offerings") or [] if not o.get("is_deleted") and not ((o.get("quantity") or 0) >= 1 and o.get("is_enabled") is True)]
    if sat:
        f.append(f"satilamaz teklif {sat}")
    return f


# ---------------- ilan alanlari ----------------

def partner_ids(x):
    if x.get("production_partners") is not None:
        return sorted(p.get("production_partner_id") for p in x["production_partners"])
    if "production_partner_ids" in x:
        return sorted(x.get("production_partner_ids") or [])
    return None


def materials_ok(x):
    return sorted(m.strip().lower() for m in x.get("materials") or []) == sorted(MATERIALS)


def stil_gorsel(api, shop, lid):
    d = api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True)
    if d is None:
        raise Dur("variation-images okunamadi (404)")
    return sorted((v.get("property_id"), v.get("value_id"), v.get("image_id")) for v in d.get("results") or [])


def deger_adlari(inv):
    ad, vid = {}, {}
    for p in (inv or {}).get("products") or []:
        for v in p.get("property_values") or []:
            for i, a in zip(v.get("value_ids") or [], v.get("values") or []):
                ad[(v.get("property_id"), i)] = a
                vid[(v.get("property_id"), a)] = i
    return ad, vid


def sg_ad(inv, sg):
    ad = deger_adlari(inv)[0]
    return sorted((pid, ad.get((pid, vi), f"?{vi}"), img) for pid, vi, img in sg or [])


def kilitli(store, shop, izin):
    """Yalniz izinli uclar (izin kumesindeki ilanlar): envanter PUT, ilan PATCH (description/materials/production_partner_ids),
    variation-images POST. izin kumesi disaridan doldurulur (oku modunda bos: her yazma YASAK)."""
    from etsy_common import Etsy

    class Kilitli(Etsy):
        def put_json(self, path, body):
            m = re.fullmatch(r"/listings/(\d+)/inventory", path)
            if not m or m.group(1) not in izin:
                raise SystemExit(f"YASAK: PUT {path}")
            return super().put_json(path, body)

        def patch(self, path, data):
            m = re.fullmatch(rf"/shops/{shop}/listings/(\d+)", path)
            if not m or m.group(1) not in izin or not set(data) <= {"description", "materials", "production_partner_ids", "shipping_profile_id"}:
                raise SystemExit(f"YASAK: PATCH {path} {sorted(data)}")
            return super().patch(path, data)

        def post_json(self, path, body):
            m = re.fullmatch(rf"/shops/{shop}/listings/(\d+)/variation-images", path)
            if not m or m.group(1) not in izin:
                raise SystemExit(f"YASAK: POST {path}")
            return super().post_json(path, body)

        def post(self, *a, **k):
            raise SystemExit("YASAK: POST form")

        def put(self, path, data):
            if "PROFIL" not in izin or not re.fullmatch(rf"/shops/{shop}/shipping-profiles/{PROFIL_BASKI}/destinations/\d+", path) \
                    or not {"primary_cost", "secondary_cost", "min_delivery_days", "max_delivery_days"} <= set(data) \
                    or not set(data) <= {"primary_cost", "secondary_cost", "min_delivery_days", "max_delivery_days",
                                         "destination_country_iso", "destination_region"} \
                    or ("destination_country_iso" in data) == ("destination_region" in data):
                raise SystemExit(f"YASAK: PUT form {path} {sorted(data)}")
            return super().put(path, data)

        def post_file(self, *a, **k):
            raise SystemExit("YASAK: POST file")

        def delete(self, *a, **k):
            raise SystemExit("YASAK: DELETE")
    return Kilitli(store)


def hazirlik_dogrula(api, shop):
    t = api.get(f"/shops/{shop}/readiness-state-definitions/{HAZIRLIK_BASKI}", ok404=True) or {}
    if (t.get("min_processing_days"), t.get("max_processing_days")) != (4, 7):
        raise SystemExit(f"DUR: hazirlik tanimi {HAZIRLIK_BASKI} 4-7 gun degil: {t}")
    return t


# ---------------- ilan ----------------

def stil_bag_onar(api, shop, lid, inv_simdi, hedef_ad, R):
    """Stil-gorsel baglarini deger ADINA gore kurar (burc_gift_yaz.sg_bagla yolu); geri okuma 3 deneme. Hata listesi doner."""
    if sg_ad(inv_simdi, stil_gorsel(api, shop, lid)) == hedef_ad:
        return []
    vid = deger_adlari(inv_simdi)[1]
    istek = [{"property_id": p, "value_id": vid[(p, n)], "image_id": im} for p, n, im in hedef_ad if (p, n) in vid]
    if len(istek) != len(hedef_ad):
        return [f"stil-gorsel eslemesi kurulamadi {len(istek)}/{len(hedef_ad)}"]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
    R["yazildi"].append("stil_gorsel")
    R["onarim"] = "ada gore geri yazildi"
    for _ in range(3):
        if sg_ad(inv_simdi, stil_gorsel(api, shop, lid)) == hedef_ad:
            return []
        time.sleep(BEKLE_SN)
    return ["stil-gorsel baglari geri yazilamadi"]


def ilan(api, shop, lid, yaz, out, R=None):
    """R disaridan verilir: istisnada da yazilan adimlar (R['yazildi']) ozete gecer."""
    R = R if R is not None else {"ilan": lid, "yazildi": []}
    R.setdefault("yazildi", [])
    d = out / lid
    d.mkdir(parents=True, exist_ok=True)
    x = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    sg0 = stil_gorsel(api, shop, lid)
    (d / "ONCE.json").write_text(json.dumps({"listing": x, "inventory": inv, "vimg": sg0}, ensure_ascii=False, indent=1), encoding="utf-8")
    R["once"] = dict(state=x.get("state"), profil=x.get("shipping_profile_id"), tip=x.get("listing_type"),
                     materials=x.get("materials"), partner=partner_ids(x), urun=len(urunler_canli(inv)),
                     sku_on=inv.get("sku_on_property"), rd_on=inv.get("readiness_state_on_property"),
                     price_on=inv.get("price_on_property"), fiyat=x.get("price"))
    if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
        raise Dur(f"state {x.get('state')} / shop {x.get('shop_id')}: dokunulmaz")
    profil0 = int(x.get("shipping_profile_id") or 0)
    if profil0 not in KABUL_PROFIL:
        raise Dur(f"kargo profili {profil0} (kabul {sorted(KABUL_PROFIL)})")
    if x.get("listing_type") != "physical":
        raise Dur(f"listing_type {x.get('listing_type')} (physical bekleniyordu)")
    if partner_ids(x) is None:
        raise Dur("uretim ortagi alani API yanitinda yok")
    R["once"]["hazirlik"] = sorted({str(v[4]) for v in imza(inv).values()})
    a_durum, d1 = aciklama_plani(x.get("description"))
    e_durum, govde, stiller, hedef_baski = envanter_plani(inv)
    sg0_ad = sg_ad(inv, sg0)
    if len(sg0) != 5 or any(n.startswith("?") for _, n, _ in sg0_ad):
        raise Dur(f"stil-gorsel baglari 5 degil ya da adsiz: {sg0_ad} (onceki ONCE.json'dan elle onar)")
    yama = {}
    if a_durum == "YAZ":
        yama["description"] = d1
        (d / "ACIKLAMA_PLAN.txt").write_text(d1, encoding="utf-8")
    if not materials_ok(x):
        yama["materials"] = ",".join(MATERIALS)
    if profil0 != PROFIL:
        yama["shipping_profile_id"] = PROFIL
    partner_yaz = partner_ids(x) != [PARTNER]
    (d / "PUT.json").write_text(json.dumps(govde, ensure_ascii=False, indent=1), encoding="utf-8")
    R["plan"] = dict(envanter=e_durum, aciklama=a_durum, alanlar=sorted(yama), partner="YAZ" if partner_yaz else "TAMAM",
                     baski_sku=hedef_baski)
    if e_durum == "TAMAM" and not yama and not partner_yaz:
        R["durum"] = "ZATEN"
        return R
    if not yaz:
        R["durum"] = "PLAN_OK"
        return R
    from etsy_common import KOTA_SINIRI
    if api.remaining is not None and int(api.remaining) < ISTEK_TAHMIN + KOTA_SINIRI:   # kural: tahmini istek + 10
        R["durum"] = f"KOTA_BEKLE kalan {api.remaining} < {ISTEK_TAHMIN} + {KOTA_SINIRI} (yazma yok)"
        return R
    i0 = imza(inv)
    R["onarim"] = "gerekmedi"
    f = []
    if e_durum == "YAZ":
        api.put_json(f"/listings/{lid}/inventory", govde)
        R["yazildi"].append("envanter")
        # baglar PUT'un HEMEN ardindan (burc_gift_yaz.py:320-326 sirasi): sonraki adim durursa ilan bagsiz kalmaz
        f += stil_bag_onar(api, shop, lid, api.get(f"/listings/{lid}/inventory") or {}, sg0_ad, R)
    if yama:
        api.patch(f"/shops/{shop}/listings/{lid}", yama)
        R["yazildi"].append("ilan:" + "+".join(sorted(yama)))
    if partner_yaz:
        api.patch(f"/shops/{shop}/listings/{lid}", {"production_partner_ids": str(PARTNER)})
        R["yazildi"].append("uretim_ortagi")
    # geri okuma: bayat okumaya karsi 3 deneme
    for _ in range(3):
        x2 = api.get(f"/listings/{lid}") or {}
        inv2 = api.get(f"/listings/{lid}/inventory") or {}
        g = envanter_hedefte(inv2, i0, hedef_baski, govde)
        if not esdeger(norm(x2.get("description")), d1):
            g.append("aciklama plan ile ayni degil")
        if not materials_ok(x2):
            g.append(f"materials {x2.get('materials')}")
        if partner_ids(x2) != [PARTNER]:
            g.append(f"uretim ortagi {partner_ids(x2)}")
        if int(x2.get("shipping_profile_id") or 0) != PROFIL:
            g.append(f"kargo profili {x2.get('shipping_profile_id')} (hedef {PROFIL})")
        for k in ("state", "title", "tags", "listing_type", "shop_section_id"):
            if x2.get(k) != x.get(k):
                g.append(f"{k} degisti: {x.get(k)} -> {x2.get(k)}")
        if not g:
            break
        time.sleep(BEKLE_SN)
    f += g
    sg2 = stil_gorsel(api, shop, lid)
    if sg_ad(inv2, sg2) != sg0_ad:
        f += stil_bag_onar(api, shop, lid, inv2, sg0_ad, R)
        sg2 = stil_gorsel(api, shop, lid)
    if x2.get("price") != x.get("price"):
        R["not_fiyat"] = f"ilan price alani {x.get('price')} -> {x2.get('price')} (bilgi; urun fiyatlari ayrica kontrol edildi)"
    if {k: v[5:] for k, v in imza(inv2).items() if k[1] != BASKI} != {k: v[5:] for k, v in i0.items() if k[1] != BASKI}:
        R["not"] = "dijital urunlerde value_id degisti (fiyat/SKU/stok/hazirlik ayni; baglar ada gore kontrol edildi)"
    (d / "SONRA.json").write_text(json.dumps({"listing": x2, "inventory": inv2, "vimg": sg2}, ensure_ascii=False, indent=1), encoding="utf-8")
    R.update(hatalar=f, durum="PASS" if not f else "FAIL", kota=api.remaining)
    return R


def bolum_ids(api, shop):
    ids, off = [], 0
    while True:
        d = api.get(f"/shops/{shop}/shop-sections/listings", params={"shop_section_ids": BOLUM, "limit": 100, "offset": off}) or {}
        r = d.get("results") or []
        ids += [str(x.get("listing_id")) for x in r if x.get("listing_id")]
        if len(r) < 100:
            break
        off += 100
    ids = list(dict.fromkeys(ids))
    if len(ids) != 78:
        raise SystemExit(f"DUR: bolum {BOLUM} ilan sayisi {len(ids)} (78 bekleniyordu)")
    return ids


def hedef_anahtar(x):
    cc = (x.get("destination_country_iso") or "").upper()
    rg = (x.get("destination_region") or "none").lower()
    return cc if cc else ("EVERYWHERE" if rg == "none" else rg.upper())


def profil_imza(P):
    return {hedef_anahtar(x): (para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"),
                               x.get("max_delivery_days"), x.get("shipping_profile_destination_id"))
            for x in P.get("shipping_profile_destinations") or []}


def profil_kullananlar(api, shop):
    """Aktif + taslak + pasif ilanlarda baski profilini kullananlar (bolum ile). Profil ucreti degisince etkilenecekler."""
    kim = []
    for st in ("active", "draft", "inactive", "expired", "sold_out"):
        off = 0
        while True:
            d = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100, "offset": off}) or {}
            r = d.get("results") or []
            kim += [(str(x.get("listing_id")), st, x.get("shop_section_id")) for x in r
                    if int(x.get("shipping_profile_id") or 0) == PROFIL_BASKI]
            off += len(r)
            if len(r) < 100:
                break
    return kim


def profil_adimi(api, shop, yaz, out):
    """Secenek B: baski profilinde AU ($5) ve diger tum ulkeler ($12) ucretsiz; teslim gunleri DEGISMEZ.
    KAPI: profili yil donumu bolumu disinda kullanan ilan varsa DUR (o ilanlarin kargosu degisirdi)."""
    P0 = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL_BASKI}") or {}
    (out / "PROFIL_YEDEK.json").write_text(json.dumps(P0, ensure_ascii=False, indent=1), encoding="utf-8")
    i0 = profil_imza(P0)
    R = {"profil": PROFIL_BASKI, "baslik": P0.get("title"), "once": {k: v[:4] for k, v in i0.items()}}
    if set(i0) != set(PROFIL_HEDEF):
        raise SystemExit(f"DUR: profil hedefleri beklenmedik: {sorted(i0)}")
    for k, (simdi, hedef, a, b) in PROFIL_HEDEF.items():
        if i0[k][2:4] != (a, b) or i0[k][0] not in (float(simdi), float(hedef)) or i0[k][0] != i0[k][1]:
            raise SystemExit(f"DUR: {k} beklenmedik: {i0[k][:4]}")
    kim = profil_kullananlar(api, shop)
    R["kullanan"] = kim
    disari = [x for x in kim if x[2] != BOLUM]
    if disari:
        raise SystemExit(f"DUR: profili yil donumu disinda kullanan ilan var: {disari[:10]}")
    degis = [k for k, v in PROFIL_HEDEF.items() if i0[k][0] != float(v[1])]
    R["degisecek"] = degis
    if yaz:
        for k in degis:
            _, hedef, a, b = PROFIL_HEDEF[k]
            hedef_alan = {"destination_country_iso": k} if k not in ("EU", "EVERYWHERE") else \
                {"destination_region": "eu" if k == "EU" else "none"}
            api.put(f"/shops/{shop}/shipping-profiles/{PROFIL_BASKI}/destinations/{i0[k][4]}",
                    {"primary_cost": hedef, "secondary_cost": hedef, "min_delivery_days": a, "max_delivery_days": b, **hedef_alan})
        i1 = profil_imza(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL_BASKI}") or {})
        R["sonra"] = {k: v[:4] for k, v in i1.items()}
        bek = {k: (float(v[1]), float(v[1]), v[2], v[3]) for k, v in PROFIL_HEDEF.items()}
        if R["sonra"] != bek:
            raise SystemExit(f"DUR: profil geri okuma beklenen degil: {R['sonra']} != {bek}")
    (out / f"PROFIL_{'YAZ' if yaz else 'OKU'}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    log("PROFIL " + json.dumps(R, ensure_ascii=False, default=str))
    return R


def profil_ucretsiz_mi(api, shop):
    i = profil_imza(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL_BASKI}") or {})
    bad = {k: v[:4] for k, v in i.items() if v[0] != 0 or v[1] != 0 or k not in PROFIL_HEDEF or v[2:4] != PROFIL_HEDEF[k][2:4]}
    if set(i) != set(PROFIL_HEDEF) or bad:
        raise SystemExit(f"DUR: baski profili {PROFIL_BASKI} henuz her yere ucretsiz degil (once profil_yaz): {bad}")


KOTA_ONEK = ("DUR: kota esigi", "DUR: kota sert tabani", "KOTA_BEKLE")   # etsy_common mesajlari + bu betik


def kota_mi(metin):
    return any(o in (metin or "") for o in KOTA_ONEK)


def sonuc_etiketi(sonuc, oz_hata, tamam):
    """TAMAM | KOTA (yalniz kota yuzunden yarim; tekrar kosu tamamlar) | HATA (gece zinciri durur)."""
    if oz_hata and not kota_mi(oz_hata):
        return "HATA"
    if any(r["durum"].startswith(("FAIL", "DUR")) and not kota_mi(r["durum"]) for r in sonuc):
        return "HATA"
    return "TAMAM" if tamam else "KOTA"


def token_kur():
    from etsy_common import TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    return store


def profil_main(a):
    OUT.mkdir(exist_ok=True)
    oz_hata, R, api = None, None, None
    try:
        if a.mod == "profil_yaz" and a.confirm != ONAY_PROFIL:
            raise SystemExit(f"DUR: profil_yaz icin --confirm {ONAY_PROFIL}")
        store = token_kur()
        shop = os.environ["ETSY_SHOP_ID"]
        api = kilitli(store, shop, {"PROFIL"} if a.mod == "profil_yaz" else set())
        R = profil_adimi(api, shop, a.mod == "profil_yaz", OUT)
    except BaseException as e:  # noqa: BLE001
        oz_hata = f"{type(e).__name__}: {str(e)[:400]}"
        log("PROFIL HATA " + oz_hata)
        (OUT / "PROFIL_HATA.json").write_text(json.dumps({"hata": oz_hata, "iz": traceback.format_exc()[-1500:]}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    finally:
        et = sonuc_etiketi([], oz_hata, oz_hata is None)
        print(f"::notice::SONUC {et} {a.mod} degisecek {R.get('degisecek') if R else '-'} kota {api.remaining if api else '-'}", flush=True)
    sys.exit(0 if oz_hata is None else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz", "profil_oku", "profil_yaz"])
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--tamam", default="", help="onceki kosularda PASS/ZATEN olan ilanlar (satir basina id); yalniz yaz modunda atlanir")
    a = ap.parse_args()
    if a.mod.startswith("profil"):
        profil_main(a)
    yaz = a.mod == "yaz"
    OUT.mkdir(exist_ok=True)
    sonuc, t0, oz_hata, api, tamam = [], time.time(), None, None, False
    ids = []
    try:
        if yaz and a.confirm != (ONAY_HEPSI if a.hepsi else ONAY):
            raise SystemExit(f"DUR: yaz icin --confirm {ONAY_HEPSI if a.hepsi else ONAY}")
        if a.hepsi == bool(a.ilanlar.strip()):
            raise SystemExit("DUR: ya --ilanlar ya --hepsi")
        store = token_kur()
        shop = os.environ["ETSY_SHOP_ID"]
        izin = set()
        api = kilitli(store, shop, izin)
        tum = bolum_ids(api, shop)
        ids = tum if a.hepsi else [x.strip() for x in a.ilanlar.split(",") if x.strip()]
        if [x for x in ids if x not in tum]:
            raise SystemExit("DUR: ilan listesi yil donumu bolumu disinda")
        onceden = set()
        if yaz and a.tamam and Path(a.tamam).exists():
            onceden = {x.strip() for x in Path(a.tamam).read_text().split() if x.strip().isdigit()}
        atlanan = [x for x in ids if x in onceden]
        ids = [x for x in ids if x not in onceden]
        log(f"onceki kosularda tamam: {len(atlanan)} ilan atlandi; bu kosuda {len(ids)} ilan")
        if yaz:
            izin.update(ids)
        pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
        if PARTNER not in [p.get("production_partner_id") for p in pp]:
            raise SystemExit(f"DUR: uretim ortagi {PARTNER} magazada yok: {pp}")
        if yaz and PROFIL == PROFIL_BASKI:
            profil_ucretsiz_mi(api, shop)
        hz = hazirlik_dogrula(api, shop)
        log(f"hazirlik {HAZIRLIK_BASKI}: {hz.get('readiness_state')} {hz.get('min_processing_days')}-{hz.get('max_processing_days')}")
        for i, lid in enumerate(ids, 1):
            R = {"ilan": lid, "yazildi": []}
            try:
                api.kota_kapisi(f"ilan {lid}")
                ilan(api, shop, lid, yaz, OUT, R)
            except Dur as e:
                R["durum"] = f"FAIL_DUR: {str(e)[:400]}"
            except SystemExit as e:
                R["durum"] = f"DUR: {str(e)[:400]}"
            except Exception as e:  # noqa: BLE001
                R["durum"] = f"FAIL_ISTISNA: {type(e).__name__}: {str(e)[:300]}"
                R["iz"] = traceback.format_exc()[-1500:]
            sonuc.append(R)
            g = time.time() - t0
            log(f"[{i}/{len(ids)}] {100 * i // len(ids)}% gecen {g:.0f}s kalan ~{g / i * (len(ids) - i):.0f}s | {lid} {R['durum'][:160]} "
                f"yazildi={R.get('yazildi')} kota={api.remaining}")
            if kota_mi(R["durum"]):
                break
            if R["durum"].startswith("DUR") and (yaz or R["yazildi"]):
                break
            if yaz and R["durum"].startswith("FAIL"):
                break
    except BaseException as e:  # noqa: BLE001
        oz_hata = f"{type(e).__name__}: {str(e)[:400]}"
        log("GENEL HATA " + oz_hata)
    finally:
        say = {}
        for r in sonuc:
            k = r["durum"].split(" ")[0].rstrip(":")
            say[k] = say.get(k, 0) + 1
        iyi = ("PASS", "ZATEN") if yaz else ("PLAN_OK", "ZATEN")   # KOTA_BEKLE = tamam degil (tekrar kosu tamamlar)
        tamam = oz_hata is None and len(sonuc) == len(ids) and all(r["durum"].split(" ")[0] in iyi for r in sonuc)
        et = sonuc_etiketi(sonuc, oz_hata, tamam)
        oz = {"mod": a.mod, "istenen": len(ids), "islenen": len(sonuc), "sayim": say,
              "kota_son": api.remaining if api else None, "genel_hata": oz_hata, "durum": "PASS" if tamam else "FAIL",
              "sonuc": et, "ilanlar": sonuc}
        (OUT / f"BY_BASKI_EKLE_{a.mod.upper()}.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        if yaz:
            (OUT / "TAMAM_EK.txt").write_text("".join(r["ilan"] + "\n" for r in sonuc if r["durum"].split(" ")[0] in ("PASS", "ZATEN")))
        log("OZET " + json.dumps({k: v for k, v in oz.items() if k != "ilanlar"}, ensure_ascii=False))
        print(f"::notice::SONUC {et} {a.mod} islenen {len(sonuc)}/{len(ids)} zaten {say.get('ZATEN', 0)} sayim {say} kota {oz['kota_son']}",
              flush=True)
    sys.exit(0 if tamam else 1)


if __name__ == "__main__":
    main()
