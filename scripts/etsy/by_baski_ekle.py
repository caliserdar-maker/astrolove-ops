#!/usr/bin/env python3
"""BIZIM YILIMIZ (yil donumu, bolum 60895624): "Shipped print 8x10" ($29) secenegini ve baski ayarlarini KURAR (v2).

Serdar onayi 24 Eki 2026 (Genel Merkez): tedarikci Printful ana + Shortrun ABD yedek; baski geri gelir.
v2 kararlari (Serdar 24 Eki "ok"): kargo profili DEGISMEZ (318577242658 BY Digital Free Worldwide, baski her yere ucretsiz);
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
  degismez : state active, baslik, etiket, kargo profili 318577242658, listing_type physical, stil-gorsel baglari (ada gore)
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
PROFIL = 318577242658          # BY Digital Free Worldwide: DEGISTIRILMEZ (Serdar 24 Eki)
PARTNER = 5817638              # "Printing and Fulfillment Partner", United States (kupa_taslak.py, Serdar 18 Eki)
HAZIRLIK_BASKI = 1517641240112  # magaza ortak 4-7 gun tanimi (burc_gift_yaz.ORTAK_HAZIRLIK); okunarak dogrulanir
MATERIALS = ["matte art paper", "ink", "digital file"]
ONAY, ONAY_HEPSI = "BASKI_EKLE", "BASKI_EKLE_HEPSI"
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
         (re.compile(r"instant\s*download", re.I), "instant download (dijital Etsy Messages ile gider)")]


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


def imza(inv):
    """{(stil, format): (sku, fiyat, stok, acik, hazirlik, stil_vid, format_vid)}"""
    s = {}
    for p in inv.get("products") or []:
        d = pvd(p)
        o = (p.get("offerings") or [{}])[0]
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
    for p in inv.get("products") or []:
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
        for p in inv.get("products") or []:
            if anahtar(p)[0] != st:
                continue
            o = (p.get("offerings") or [{}])[0]
            pv = [dict(property_id=v["property_id"], property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                       values=v.get("values")) for v in p.get("property_values") or []]
            if anahtar(p)[1] == BASKI:
                continue
            urunler.append(dict(sku=p.get("sku") or "", property_values=pv,
                                offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled") is True,
                                                readiness_state_id=o.get("readiness_state_id"))]))
        mevcut = next((p for p in inv.get("products") or [] if anahtar(p) == (st, BASKI)), None)
        stil_pv = pvd(next(p for p in inv.get("products") or [] if anahtar(p) == (st, DOSYA)))[P_STYLE]
        if mevcut:
            pv = [dict(property_id=v["property_id"], property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                       values=v.get("values")) for v in mevcut.get("property_values") or []]
            stok = (mevcut.get("offerings") or [{}])[0].get("quantity") or 0
        else:
            pv = [dict(property_id=P_STYLE, property_name=stil_pv.get("property_name") or "Style", value_ids=stil_pv.get("value_ids"),
                       values=stil_pv.get("values")),
                  dict(property_id=P_FORMAT, property_name="Format", values=[BASKI])]
            stok = 0
        urunler.append(dict(sku=hedef_baski[st], property_values=pv,
                            offerings=[dict(price=FIYAT, quantity=stok if stok >= 1 else 999, is_enabled=True,
                                            readiness_state_id=HAZIRLIK_BASKI)]))
    sku_on = sorted(set((inv.get("sku_on_property") or [])) | {P_STYLE, P_FORMAT})
    rd_on = sorted(set((inv.get("readiness_state_on_property") or [])) | {P_FORMAT})
    govde = dict(products=urunler, price_on_property=inv.get("price_on_property") or [],
                 quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=sku_on,
                 readiness_state_on_property=rd_on)
    tamam = nb == 5 and envanter_hedefte(inv, i0, hedef_baski) == []
    return ("TAMAM" if tamam else "YAZ"), govde, stiller, hedef_baski


def envanter_hedefte(inv, dijital_once, hedef_baski):
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
    if P_FORMAT not in (inv.get("readiness_state_on_property") or []):
        f.append(f"readiness_state_on_property {inv.get('readiness_state_on_property')}")
    if not {P_STYLE, P_FORMAT} <= set(inv.get("sku_on_property") or []):
        f.append(f"sku_on_property {inv.get('sku_on_property')}")
    sat = [(p.get("sku"), o.get("quantity"), o.get("is_enabled")) for p in inv.get("products") or []
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
            if not m or m.group(1) not in izin or not set(data) <= {"description", "materials", "production_partner_ids"}:
                raise SystemExit(f"YASAK: PATCH {path} {sorted(data)}")
            return super().patch(path, data)

        def post_json(self, path, body):
            m = re.fullmatch(rf"/shops/{shop}/listings/(\d+)/variation-images", path)
            if not m or m.group(1) not in izin:
                raise SystemExit(f"YASAK: POST {path}")
            return super().post_json(path, body)

        def post(self, *a, **k):
            raise SystemExit("YASAK: POST form")

        def put(self, *a, **k):
            raise SystemExit("YASAK: PUT form")

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

def ilan(api, shop, lid, yaz, out):
    R = {"ilan": lid, "yazildi": []}
    d = out / lid
    d.mkdir(parents=True, exist_ok=True)
    x = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    sg0 = stil_gorsel(api, shop, lid)
    (d / "ONCE.json").write_text(json.dumps({"listing": x, "inventory": inv, "vimg": sg0}, ensure_ascii=False, indent=1), encoding="utf-8")
    R["once"] = dict(state=x.get("state"), profil=x.get("shipping_profile_id"), tip=x.get("listing_type"),
                     materials=x.get("materials"), partner=partner_ids(x), urun=len(inv.get("products") or []),
                     hazirlik=sorted({str(v[4]) for v in imza(inv).values()}), sku_on=inv.get("sku_on_property"),
                     rd_on=inv.get("readiness_state_on_property"), price_on=inv.get("price_on_property"))
    if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
        raise Dur(f"state {x.get('state')} / shop {x.get('shop_id')}: dokunulmaz")
    if int(x.get("shipping_profile_id") or 0) != PROFIL:
        raise Dur(f"kargo profili {x.get('shipping_profile_id')} (beklenen {PROFIL})")
    if x.get("listing_type") != "physical":
        raise Dur(f"listing_type {x.get('listing_type')} (physical bekleniyordu)")
    if partner_ids(x) is None:
        raise Dur("uretim ortagi alani API yanitinda yok")
    a_durum, d1 = aciklama_plani(x.get("description"))
    e_durum, govde, stiller, hedef_baski = envanter_plani(inv)
    sg0_ad = sg_ad(inv, sg0)
    if len(sg0) != 5 or any(n.startswith("?") for _, n, _ in sg0_ad):
        raise Dur(f"stil-gorsel baglari 5 degil ya da adsiz: {sg0_ad}")
    yama = {}
    if a_durum == "YAZ":
        yama["description"] = d1
        (d / "ACIKLAMA_PLAN.txt").write_text(d1, encoding="utf-8")
    if not materials_ok(x):
        yama["materials"] = ",".join(MATERIALS)
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
    i0 = imza(inv)
    if e_durum == "YAZ":
        api.put_json(f"/listings/{lid}/inventory", govde)
        R["yazildi"].append("envanter")
    if yama:
        api.patch(f"/shops/{shop}/listings/{lid}", yama)
        R["yazildi"].append("ilan:" + "+".join(sorted(yama)))
    if partner_yaz:
        api.patch(f"/shops/{shop}/listings/{lid}", {"production_partner_ids": str(PARTNER)})
        R["yazildi"].append("uretim_ortagi")
    # geri okuma: bayat okumaya karsi 3 deneme
    f = ["okunmadi"]
    for _ in range(3):
        x2 = api.get(f"/listings/{lid}") or {}
        inv2 = api.get(f"/listings/{lid}/inventory") or {}
        f = envanter_hedefte(inv2, i0, hedef_baski)
        if not esdeger(norm(x2.get("description")), d1):
            f.append("aciklama plan ile ayni degil")
        if not materials_ok(x2):
            f.append(f"materials {x2.get('materials')}")
        if partner_ids(x2) != [PARTNER]:
            f.append(f"uretim ortagi {partner_ids(x2)}")
        for k in ("state", "title", "tags", "shipping_profile_id", "listing_type", "price", "shop_section_id"):
            if x2.get(k) != x.get(k):
                f.append(f"{k} degisti: {x.get(k)} -> {x2.get(k)}")
        if not f:
            break
        time.sleep(BEKLE_SN)
    onarim = "gerekmedi"
    sg2 = stil_gorsel(api, shop, lid)
    if sg_ad(inv2, sg2) != sg0_ad:
        vid = deger_adlari(inv2)[1]
        istek = [{"property_id": p, "value_id": vid[(p, n)], "image_id": im} for p, n, im in sg0_ad if (p, n) in vid]
        if len(istek) != len(sg0_ad):
            f.append(f"stil-gorsel eslemesi kurulamadi {len(istek)}/{len(sg0_ad)}")
        else:
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
            R["yazildi"].append("stil_gorsel")
            onarim = "ada gore geri yazildi"
            for _ in range(3):
                sg2 = stil_gorsel(api, shop, lid)
                if sg_ad(inv2, sg2) == sg0_ad:
                    break
                time.sleep(BEKLE_SN)
            if sg_ad(inv2, sg2) != sg0_ad:
                f.append("stil-gorsel baglari geri yazilamadi")
    if {k: v[5:] for k, v in imza(inv2).items() if k[1] != BASKI} != {k: v[5:] for k, v in i0.items() if k[1] != BASKI}:
        R["not"] = "dijital urunlerde value_id degisti (fiyat/SKU/stok/hazirlik ayni; baglar ada gore kontrol edildi)"
    (d / "SONRA.json").write_text(json.dumps({"listing": x2, "inventory": inv2, "vimg": sg2}, ensure_ascii=False, indent=1), encoding="utf-8")
    R.update(hatalar=f, onarim=onarim, durum="PASS" if not f else "FAIL", kota=api.remaining)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    if yaz and a.confirm != (ONAY_HEPSI if a.hepsi else ONAY):
        raise SystemExit(f"DUR: yaz icin --confirm {ONAY_HEPSI if a.hepsi else ONAY}")
    if a.hepsi == bool(a.ilanlar.strip()):
        raise SystemExit("DUR: ya --ilanlar ya --hepsi")
    from etsy_common import TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)
    sonuc, t0, oz_hata, api = [], time.time(), None, None
    ids = []
    try:
        izin = set()
        api = kilitli(store, shop, izin)
        tum = bolum_ids(api, shop)
        ids = tum if a.hepsi else [x.strip() for x in a.ilanlar.split(",") if x.strip()]
        if [x for x in ids if x not in tum]:
            raise SystemExit("DUR: ilan listesi yil donumu bolumu disinda")
        if yaz:
            izin.update(ids)
        hz = hazirlik_dogrula(api, shop)
        log(f"hazirlik {HAZIRLIK_BASKI}: {hz.get('readiness_state')} {hz.get('min_processing_days')}-{hz.get('max_processing_days')}")
        for i, lid in enumerate(ids, 1):
            R = {"ilan": lid, "yazildi": []}
            try:
                api.kota_kapisi(f"ilan {lid}")
                R = ilan(api, shop, lid, yaz, OUT)
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
            if R["durum"].startswith("DUR"):
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
        iyi = ("PASS", "ZATEN") if yaz else ("PLAN_OK", "ZATEN")
        tamam = oz_hata is None and len(sonuc) == len(ids) and all(r["durum"].split(" ")[0] in iyi for r in sonuc)
        oz = {"mod": a.mod, "istenen": len(ids), "islenen": len(sonuc), "sayim": say,
              "kota_son": api.remaining if api else None, "genel_hata": oz_hata, "durum": "PASS" if tamam else "FAIL",
              "ilanlar": sonuc}
        (OUT / f"BY_BASKI_EKLE_{a.mod.upper()}.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        log("OZET " + json.dumps({k: v for k, v in oz.items() if k != "ilanlar"}, ensure_ascii=False))
    sys.exit(0 if tamam else 1)


if __name__ == "__main__":
    main()
