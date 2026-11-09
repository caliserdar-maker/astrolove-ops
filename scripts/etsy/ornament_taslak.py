#!/usr/bin/env python3
"""ORNAMENT 78: Etsy TASLAK ilanlari (Serdar 6 Kas gece: "taslak olustur", yayin sabah ayri onay; "denetim code ile islerin olursa tam
yetki, onaylar sende"). YAYIN YOK, Etsy Ads YOK, DELETE YOK. Kalip: scripts/etsy/kupa_taslak.py (cift kupa, 19 Eki, Serdar onayli).

--mod oku : SALT OKUMA. Ornament kategorisi + nitelikleri, hazirlik tanimlari, iade / ortak / bolum / kargo profilleri (+ cikis, hedef),
            ayni baslikli taslaklar, kota. Cikti OUT/ORN_OKU.json + .md
--mod kur : MAGAZA KAYITLARI (yalniz yoksa, ada gore idempotent): hazirlik made_to_order 3-5 is gunu, kargo profili
            "Ornament Free Worldwide" (cikis LV, ucretsiz; hedefler US, CA, GB, AU, EU, diger), bolum "Zodiac Couple Ornaments".
            Kararlar: KARARLAR_20261106_2 (6 Kas gece). Ilan YAZMAZ. Cikti OUT/ORN_KUR.json
--mod kuru: AG YOK, TOKEN YOK. yaz() ile ayni kod yolu; Etsy bellekte taklit; her istek OUT/kuru/KURU_<CIFT>.json
--mod yaz : cift basina 1 YENI taslak: createDraftListing (tek POST) -> envanter (Style x ayar fiyati) -> taslak galerisi (alt metinli) -> video
            -> stil gorselleri (Ruby 7 ... Ivory 11) -> 3 kisisellestirme kutusu -> nitelikler -> tam geri okuma. Her yazmadan sonra state
            okunur; "active" -> aninda inactive + DUR. updateListing (PATCH) YOK (taslagi yayina alir); PATCH yalniz acil state=inactive.
Metin: data/pod/ORNAMENT78_METIN.csv (scripts/etsy/ornament_metin.py). Medya: IMG_ROOT/<CIFT>/<CIFT>_01_KAPAK.jpg ... _11_IVORY.jpg,
<CIFT>_VIDEO.mp4 (ornament-galeri78 ciktisi). Kota tabani 10 (KOTA_SINIRI).
Ayarlar (Serdar 8 Kas gece "Hepsi oneriyle", Onay 3b): docs/urun/ornament78/URUN_AYAR.json (scripts/etsy/urun_ayar.py). Ilan alanlari,
fiyat, varyasyon, envanter, taslak galerisi ve nitelikleri AYARDAN gelir; her yazimdan ONCE (html_coz sonrasi son govde) ayar kapisi
(urun_ayar.yazim_kapisi: kilit, onay kaydi ONAY_YOLU, panel on isleri, metin sha, SPEC farki, state yasagi, govde = ayar) + metin yasak
ENGEL (S9) mevcut kapilarin ONUNDE calisir. Kod state active YAPMAZ (S14; PATCH yalniz acil inactive). URUN_AYAR ortam yolu yalniz kuru.
docs/ornament/ORN_ETSY_AYAR.json artik okunmaz (emekliye ayirma ayri onay, S5); kur modu degismedi.
"""
import argparse
import csv
import html
import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, Etsy, TokenStore, ai_beyan_kapisi, html_coz, mask, metin_yasak_kapisi, ru_yazim_kapisi  # noqa: E402
import urun_ayar as UA  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10
BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
CIFTLER = sorted("_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2))
URUN = "ornament78"
KOTA_ILAN = 70                 # ilan basina tahmini istek (kuru olcum 40) + 10 + pay: ilan yarim birakilmaz (CLAUDE.md Etsy 3)
PARTI_MAX = 20                 # tek kosuda en fazla yeni cift (kilit suresi, CLAUDE.md KILIT SURESI 23 Eki)
SURE_DK = 60                   # kilit anindan (KILIT_T0) sonra yeni cifte baslanmaz
ISIM_MAX, TARIH_MAX = 30, 30   # yalniz Etsy alani (genis): ilanda harf siniri yok (SEO_DUZELTME 3), sigmayi siparis kapisi olcer; "10th of September 2026" 22
HAZIRLIK = (3, 5)              # is gunu (Serdar 6 Kas gece)
PROFIL_AD = "Ornament Free Worldwide"
BOLUM_AD = "Zodiac Couple Ornaments"
# Printful resmi (support.printful.com "What are Printful's shipping options", 6 Kas): uluslararasi 5-20 is gunu uretim sonrasi
HEDEF = [("US", "country", "US", 5, 20), ("CA", "country", "CA", 5, 20), ("GB", "country", "GB", 5, 20), ("AU", "country", "AU", 5, 20),
         ("EU", "region", "eu", 5, 20), ("EVERYWHERE", "region", "none", 5, 20)]
METIN_SUTUN = ["kod", "baslik", "etiketler", "aciklama"] + [f"alt_{i:02d}" for i in range(1, 12)] + ["soru1", "soru2", "soru3", "talimat_isim", "talimat_tarih"]
TIRE = re.compile("[–—]")
TETIK_ADLAR = ("ornaments", "ornament", "christmas ornaments", "ornaments & accents")


def ayar():
    """URUN_AYAR (urun_ayar.yukle: sema, bos zorunlu alan, bilinmeyen anahtar -> DUR). URUN_AYAR ortam yolu yalniz kuru / test."""
    return UA.yukle(URUN, os.environ.get("URUN_AYAR") or None)


def stiller(A):
    """(menu adi, SKU kodu, galeri sirasi, dosya eki) ayardan."""
    return [(m["ad"], m["sku_kodu"], m["gorsel_sira"], A["taslak"]["galeri"][m["gorsel_sira"] - 1]) for m in A["varyasyon"]["menu"]]


def galeri(A):
    return list(A["taslak"]["galeri"])


def metin_yolu(A=None):
    """EN metin CSV: METIN_CSV (yalniz kuru / test; yaz modunda yasak) ya da ayardaki metin.en.csv (kapi sha'sini bu dosyada olcer)."""
    if os.environ.get("METIN_CSV"):
        return Path(os.environ["METIN_CSV"])
    return KOK / (A or ayar())["metin"]["en"]["csv"]


def taslak_govde(A, title, desc, tags):
    """createDraftListing govdesi: metin disindaki her alan ayardan."""
    I = A["ilan"]
    return {"quantity": I["quantity"], "title": title, "description": desc, "price": I["fiyat"], "who_made": I["who_made"],
            "when_made": I["when_made"], "is_supply": I["is_supply"], "taxonomy_id": I["taxonomy_id"], "type": I["type"],
            "shipping_profile_id": I["shipping_profile_id"], "return_policy_id": I["return_policy_id"],
            "readiness_state_id": I["readiness_state_id"], "shop_section_id": I["shop_section_id"], "tags": ",".join(tags),
            "materials": ",".join(I["materials"]), "should_auto_renew": I["should_auto_renew"],
            "production_partner_ids": str(I["production_partner_id"])}


def envanter_govde(A, pair):
    """updateListingInventory govdesi: fiyat, stok, readiness, varyasyon ve *_on_property ayardan."""
    V, I, E = A["varyasyon"], A["ilan"], A["envanter"]
    prods = [dict(sku=sku(pair, kd), property_values=[dict(property_id=V["property_id"], property_name=V["property_name"], values=[ad])],
                  offerings=[dict(price=I["fiyat"], quantity=I["quantity"], is_enabled=True, readiness_state_id=I["readiness_state_id"])])
             for ad, kd, _, _ in stiller(A)]
    return dict(products=prods, **{k: list(E[k]) for k in ("price_on_property", "quantity_on_property", "sku_on_property",
                                                            "readiness_state_on_property")})


# ornament_kargo.py uyumu (OT.P_STYLE / OT.STILLER / OT.STOK; o betik bu gorevde degismez): degerler URUN_AYAR'dan, sabit yazilmaz.
# TEMBEL (PEP 562): ayar yalniz bu adlar okununca yuklenir; oku / kur modlari ve ice aktarma ayar bozuk / eksikken de calisir.
_UYUM = {"P_STYLE": lambda A: A["varyasyon"]["property_id"], "STILLER": stiller, "GALERI": galeri, "STOK": lambda A: A["ilan"]["quantity"]}


def __getattr__(ad):
    if ad in _UYUM:
        return _UYUM[ad](ayar())                    # ayar() ile ayni kaynak (URUN_AYAR ortam yolu dahil)
    raise AttributeError(f"module {__name__!r} has no attribute {ad!r}")


class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


def para(p):
    if isinstance(p, dict) and p.get("divisor"):
        return round(p["amount"] / p["divisor"], 2)
    return p


def agac_duz(dugumler, yol=(), out=None):
    out = [] if out is None else out
    for n in dugumler or []:
        p = yol + (n.get("name"),)
        out.append((n.get("id"), p, bool(n.get("children"))))
        agac_duz(n.get("children"), p, out)
    return out


def profil_ozet(sp):
    return dict(id=sp.get("shipping_profile_id"), ad=sp.get("title"), cikis=(sp.get("origin_country_iso"), sp.get("origin_postal_code")),
                hedefler=[(d.get("destination_country_iso") or d.get("destination_region"), para(d.get("primary_cost")),
                           para(d.get("secondary_cost")), d.get("min_delivery_days"), d.get("max_delivery_days"))
                          for d in sp.get("shipping_profile_destinations") or []])


def oku(api, shop, out):
    R = {}
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    duz = agac_duz((api.get("/seller-taxonomy/nodes") or {}).get("results"))
    R["kategori_adaylari"] = [(i, " > ".join(p), c) for i, p, c in duz if (p[-1] or "").strip().lower() in TETIK_ADLAR]
    R["nitelikler"] = {}
    for i, yol, cocuk in R["kategori_adaylari"]:
        if cocuk:
            continue
        props = (api.get(f"/seller-taxonomy/nodes/{i}/properties") or {}).get("results") or []
        R["nitelikler"][str(i)] = [dict(property_id=p.get("property_id"), ad=p.get("name"), zorunlu=p.get("is_required"),
                                        varyasyon=p.get("supports_variations"), coklu=p.get("is_multivalued"),
                                        olcekler=[(s.get("scale_id"), s.get("display_name")) for s in p.get("scales") or []],
                                        degerler=[(v.get("value_id"), v.get("name")) for v in p.get("possible_values") or []][:80])
                                   for p in props]
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    R["hazirlik_tanimlari"] = [dict(id=x.get("readiness_state_id"), durum=x.get("readiness_state"), min=x.get("min_processing_days"),
                                    max=x.get("max_processing_days"), etiket=x.get("processing_days_display_label")) for x in rsd]
    rp = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    R["iade_politikalari"] = [dict(id=x.get("return_policy_id"), iade=x.get("accepts_returns"), degisim=x.get("accepts_exchanges"),
                                   sure=x.get("return_deadline")) for x in rp]
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    R["uretim_ortaklari"] = [dict(id=x.get("production_partner_id"), ad=x.get("partner_name"), konum=x.get("location")) for x in pp]
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    R["bolumler"] = [dict(id=x.get("shop_section_id"), ad=x.get("title"), aktif_ilan=x.get("active_listing_count")) for x in secs]
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    R["kargo_profilleri"] = [profil_ozet(x) for x in sps]
    drafts, off = [], 0
    while True:
        r_ = api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100, "offset": off}) or {}
        drafts += [dict(listing_id=x.get("listing_id"), title=x.get("title")) for x in r_.get("results") or []]
        off += 100
        if off >= (r_.get("count") or 0) or off > 1000:
            break
    R["taslaklar_ornament"] = [d for d in drafts if "Ornament" in (d["title"] or "")]
    R["taslak_sayisi"] = len(drafts)
    R["kota_son"] = api.remaining
    R["cagri"] = api.calls
    json.dump(R, open(out / "ORN_OKU.json", "w"), indent=1, ensure_ascii=False, default=str)
    md = [f"# ORNAMENT OKU | kota {R['kota_bas']} -> {R['kota_son']} | cagri {R['cagri']}",
          f"kategori adaylari: {R['kategori_adaylari']}", f"hazirlik: {R['hazirlik_tanimlari']}", f"iade: {R['iade_politikalari']}",
          f"ortak: {R['uretim_ortaklari']}", f"bolum: {R['bolumler']}", f"kargo: {R['kargo_profilleri']}",
          f"ornament taslaklari: {R['taslaklar_ornament']} (toplam taslak {R['taslak_sayisi']})"]
    for k, v in R["nitelikler"].items():
        md.append(f"## nitelik {k}")
        md += [f"- {p['property_id']} {p['ad']} zorunlu={p['zorunlu']} varyasyon={p['varyasyon']} coklu={p['coklu']} "
               f"olcek={p['olcekler']} degerler={[d[1] for d in p['degerler']][:40]}" for p in v]
    (out / "ORN_OKU.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:9]))
    return R


class KurIzin(Etsy):
    """Yalniz hazirlik tanimi, kargo profili + hedefleri, bolum olusturma. Baska her yazma DUR."""
    def _call(self, method, path, **kw):
        if method != "GET":
            ok = [("POST", r"^/shops/\d+/readiness-state-definitions$"), ("POST", r"^/shops/\d+/shipping-profiles$"),
                  ("POST", r"^/shops/\d+/shipping-profiles/\d+/destinations$"), ("POST", r"^/shops/\d+/sections$")]
            if not any(m == method and re.match(p, path) for m, p in ok):
                raise SystemExit(f"YASAK (kur): {method} {path}")
        r = super()._call(method, path, **kw)
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        return r


def kur(api, shop, out, oku_R):
    R = {"olaylar": []}
    # 1) hazirlik 3-5
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    var = [x for x in rsd if x.get("readiness_state") == "made_to_order" and (x.get("min_processing_days"), x.get("max_processing_days")) == HAZIRLIK]
    if var:
        R["readiness_state_id"] = var[0]["readiness_state_id"]; R["olaylar"].append(f"hazirlik var {R['readiness_state_id']}")
    else:
        x = api.post(f"/shops/{shop}/readiness-state-definitions", {"readiness_state": "made_to_order", "min_processing_time": HAZIRLIK[0],
                                                                    "max_processing_time": HAZIRLIK[1], "processing_time_unit": "days"}) or {}   # Etsy enum (days, weeks); 6 Kas 400
        R["readiness_state_id"] = x.get("readiness_state_id"); R["olaylar"].append(f"hazirlik olusturuldu {R['readiness_state_id']} {x}")
    # 2) bolum
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    var = [x for x in secs if (x.get("title") or "").strip().lower() == BOLUM_AD.lower()]
    if len(var) > 1:
        raise SystemExit(f"DUR: ayni adla {len(var)} bolum")
    if var:
        R["shop_section_id"] = var[0]["shop_section_id"]; R["olaylar"].append(f"bolum var {R['shop_section_id']}")
    else:
        if len(secs) >= 20:
            raise SystemExit("DUR: bolum sayisi 20")
        x = api.post(f"/shops/{shop}/sections", {"title": BOLUM_AD}) or {}
        R["shop_section_id"] = x.get("shop_section_id"); R["olaylar"].append(f"bolum olusturuldu {R['shop_section_id']}")
    # 3) kargo profili
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    var = [x for x in sps if x.get("title") == PROFIL_AD]
    if len(var) > 1:
        raise SystemExit(f"DUR: ayni adla {len(var)} kargo profili")
    if var:
        pid = var[0]["shipping_profile_id"]; R["olaylar"].append(f"profil var {pid}")
    else:
        k0, t0, c0, a0, b0 = HEDEF[0]
        body = {"title": PROFIL_AD, "origin_country_iso": "LV", "origin_postal_code": os.environ.get("LV_POSTA", "LV-1004"),
                "primary_cost": 0, "secondary_cost": 0, "min_processing_time": HAZIRLIK[0], "max_processing_time": HAZIRLIK[1],
                "processing_time_unit": "business_days", "destination_country_iso": c0, "min_delivery_days": a0, "max_delivery_days": b0}
        x = api.post(f"/shops/{shop}/shipping-profiles", body) or {}
        pid = x.get("shipping_profile_id")
        if not pid:
            raise SystemExit(f"DUR: profil olusmadi {str(x)[:300]}")
        R["olaylar"].append(f"profil olusturuldu {pid}")
    R["shipping_profile_id"] = pid

    def anahtar(x):
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        return cc if cc else ("EVERYWHERE" if rg == "none" else rg.upper())
    prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
    have = {anahtar(x) for x in prof.get("shipping_profile_destinations") or []}
    for key, tur, kod, a, b in HEDEF:
        if key in have:
            continue
        body = {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": a, "max_delivery_days": b}
        body["destination_country_iso" if tur == "country" else "destination_region"] = kod
        try:
            api.post(f"/shops/{shop}/shipping-profiles/{pid}/destinations", body)
            R["olaylar"].append(f"hedef eklendi {key}")
        except SystemExit as e:
            R["olaylar"].append(f"HEDEF HATA {key}: {str(e)[:200]}")
            if key != "EVERYWHERE":
                raise
    R["profil"] = profil_ozet(api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {})
    json.dump(R, open(out / "ORN_KUR.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(R, ensure_ascii=False, default=str)[:2500])
    return R


# ------------------------------------------------------------------ metin + medya
def metin_satiri(pair):
    rows = list(csv.DictReader(open(metin_yolu(), encoding="utf-8")))
    eksik = [c for c in METIN_SUTUN if rows and c not in rows[0]]
    if len(rows) != 78 or eksik:
        raise SystemExit(f"DUR: METIN_CSV satir {len(rows)} / sutun eksik {eksik}")
    r = [x for x in rows if x["kod"] == pair]
    if len(r) != 1:
        raise SystemExit(f"DUR: METIN_CSV {pair} satiri {len(r)}")
    return r[0]


def metin_kontrol(row, A):
    title, desc = row["baslik"], row["aciklama"]
    tags = [t.strip() for t in row["etiketler"].split(",")]
    n_g = len(galeri(A))
    if any(f"alt_{i:02d}" not in row for i in range(1, n_g + 1)):
        raise SystemExit(f"DUR-ON: metin CSV'de {n_g} alt metin sutunu yok (taslak galerisi {n_g})")
    alt = [row[f"alt_{i:02d}"] for i in range(1, n_g + 1)]
    Q = [dict(question_text=row["soru1"], instructions=row["talimat_isim"], question_type="text_input", required=True,
              max_allowed_characters=ISIM_MAX),
         dict(question_text=row["soru2"], instructions=row["talimat_isim"], question_type="text_input", required=True,
              max_allowed_characters=ISIM_MAX),
         dict(question_text=row["soru3"], instructions=row["talimat_tarih"], question_type="text_input", required=True,
              max_allowed_characters=TARIH_MAX)]
    hata = []
    hepsi = "\n".join([title, desc, " ".join(tags)] + alt + [json.dumps(Q)])
    if TIRE.search(hepsi):
        hata.append("uzun/orta tire")
    if len(title) > 140:
        hata.append(f"baslik {len(title)}")
    if len(tags) != 13 or len(set(tags)) != 13 or any(len(t) > 20 for t in tags):
        hata.append(f"etiket {tags}")
    if any(len(a) > 250 for a in alt):
        hata.append("alt metin > 250")
    if re.search(r"\b(?:Lena|Serdar)\b", hepsi, re.I):
        hata.append("kisi adi")
    metinler = "\n".join([title, desc, " ".join(tags)] + alt + [q["question_text"] + q["instructions"] for q in Q])
    if "{" in metinler or "}" in metinler:
        hata.append("yer tutucu")
    for ad, *_ in stiller(A):
        if ad not in desc:
            hata.append(f"stil {ad} yok")
    try:                                      # tum alanlar (baslik, aciklama, etiket, alt metin, kutular) KESIN yasakta ENGEL, ag oncesi
        metin_yasak_kapisi("POST", "/shops/0/listings", data=dict(title=title, description=desc, tags=",".join(tags),
                                                                 **{f"alt_{i}": a for i, a in enumerate(alt, 1)}),
                           json_body={"personalization_questions": Q}, mod="ENGEL")
    except SystemExit as e:
        hata.append(str(e.code)[:200])
    return title, desc, tags, alt, Q, hata


def medya(pair, A):
    kok = Path(os.environ["IMG_ROOT"]) / pair
    g_ = [kok / f"{pair}_{g}.jpg" for g in galeri(A)]
    video = kok / f"{pair}_VIDEO.mp4"
    hata = [p.name for p in g_ + [video] if not p.exists()]
    return g_, video, ([f"eksik {hata}"] if hata else [])


class Kilitli(Etsy):
    """Izinli yazmalar: taslak olusturma ve YALNIZ o taslagin alt uclari. PATCH yalniz acil state=inactive. DELETE yok."""
    lid = None
    _olustur = False
    A = None                          # yaz() kurar (URUN_AYAR)
    cift = None                       # yaz() kurar: kapi CSV satirini ve SKU'yu bu cifte baglar
    stil_baglam = None                # yaz() kurar: (vid, rank_id) -> variation-images eslemesi kapida

    def _ayar_kapi(self, method, path, data=None, json_body=None):
        """Her yazimdan ONCE, mevcut kapilarin ONUNDE: html_coz SONRASI son govde -> ayar kapisi (urun_ayar.yazim_kapisi) + metin yasak
        ENGEL (S9). Ozgun govde gonderilir; Etsy._call / post_file ayni html_coz'u BIR kez uygular (ikinci cozme yok: "&amp;amp;" ->
        "&amp;" kalir). Istisna: acil {"state": "inactive"} PATCH'i (guvenlik adimi). -> (data, json_body) cozulmus kopya ya da None."""
        if str(method).upper() == "PATCH" and data == {"state": "inactive"} and json_body is None:
            return None
        if self.A is None:
            raise SystemExit("DUR: ayar kapisi: URUN_AYAR yuklenmedi")
        d2, j2 = html_coz(data), html_coz(json_body)
        UA.yazim_kapisi(self.A, method, path, d2, j2, onay_yolu=os.environ.get("ONAY_YOLU") or None, metin_yolu=metin_yolu(self.A),
                        cift=self.cift, stil_baglam=self.stil_baglam)
        metin_yasak_kapisi(method, path, d2, j2, mod="ENGEL")
        return d2, j2

    def _tek_kapilar(self, shop, body):
        """createDraftListing tek gonderim yolu: Etsy._call ile ayni kapi dizisi (html_coz, ayar, metin ENGEL, RU yazim, AI beyan, yayin
        beyan) + kota. -> gonderilecek (cozulmus) govde."""
        path = f"/shops/{shop}/listings"
        self._olustur = True
        try:
            self._izin("POST", path)
        finally:
            self._olustur = False
        b2, _ = self._ayar_kapi("POST", path, data=body)
        ru_yazim_kapisi("POST", path, b2)
        ai_beyan_kapisi("POST", path, data=b2)
        self.yayin_beyan_kontrol("POST", path, b2)
        self.kota()
        return b2

    def _izin(self, method, path):
        ok = [("POST", r"^/shops/\d+/listings$")] if self._olustur else []    # createDraftListing yalniz taslak_olustur (tek gonderim)
        if self.lid:
            L = self.lid
            ok += [("PUT", rf"^/listings/{L}/inventory$"), ("POST", rf"^/shops/\d+/listings/{L}/images$"),
                   ("POST", rf"^/shops/\d+/listings/{L}/videos$"), ("POST", rf"^/shops/\d+/listings/{L}/variation-images$"),
                   ("POST", rf"^/shops/\d+/listings/{L}/personalization$"), ("PUT", rf"^/shops/\d+/listings/{L}/properties/\d+$"),
                   ("PATCH", rf"^/shops/\d+/listings/{L}$")]
        if not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def _call(self, method, path, **kw):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and (kw.get("data") != {"state": "inactive"} or kw.get("json_body") is not None or kw.get("params")):
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
            self._ayar_kapi(method, path, kw.get("data"), kw.get("json_body"))
        r = super()._call(method, path, **kw)
        self.kota()
        return r

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        self._ayar_kapi("POST", path, data=data)
        r = super().post_file(path, files, data, tekrar=1)       # tekrar yok: hata yanitinda cift yukleme riski; cagiran galeriyi okur
        self.kota()
        return r

    def taslak_kapi(self, shop, body):
        """createDraftListing kapilari (_tek_kapilar): istek YOK. yaz() BELIRSIZ isaretinden ONCE cagirir."""
        self._tek_kapilar(shop, body)
        if not getattr(self, "kuru", False):
            self._istek_oncesi()

    def taslak_olustur(self, shop, body):
        """createDraftListing: TEK gonderim (5xx / zaman asiminda yeniden GONDERILMEZ). Kapilar (_tek_kapilar: ayar, metin ENGEL, RU, AI, kota) istekten
        ONCE. -> (kod, json, metin); kod "BELIRSIZ": istek gitti mi bilinmiyor (baglanti / zaman asimi). Kota kontrolu cagiranda, listing_id
        DURUM'a yazildiktan SONRA (201 sonrasi id kaybolmaz)."""
        b2 = self._tek_kapilar(shop, body)
        ai_beyan_kapisi("POST", f"/shops/{shop}/listings", data=b2)   # gonderilen govdeyle ayni fonksiyonda (test_ai_beyan C, AST kurali)
        self._istek_oncesi()
        sira = self._bekle()            # tempo + token erken yenileme (10 dk)
        try:
            r_ = requests.post(API + f"/shops/{shop}/listings", data=b2, headers=self._headers(), timeout=120)
        except requests.RequestException as e:
            return "BELIRSIZ", None, f"{type(e).__name__}: {str(e)[:250]}"
        self._kalan_yaz(r_.headers.get("x-remaining-today"), sira)
        try:
            js = r_.json() if r_.status_code in (200, 201) else None
        except ValueError:
            return "BELIRSIZ", None, f"{r_.status_code} json okunamadi: {r_.text[:250]}"
        return r_.status_code, js, r_.text[:300]

    def kota(self, esik=KOTA_MIN):
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < esik:
            raise SystemExit(f"DUR: kota {self.remaining} < {esik}")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")


def sku(pair, kod):
    s = f"ORN-{pair}-{kod}"
    if len(s) > 32:
        b1, b2 = pair.split("_"); s = f"ORN-{b1[:3]}_{b2[:3]}-{kod}"
    return s


def yaz(api, shop, out, pair):
    A = ayar()
    api.A, api.cift, api.stil_baglam = A, pair, None
    V = A["varyasyon"]
    ST, GAL = stiller(A), galeri(A)
    R = {"cift": pair, "adimlar": []}
    durum_f = out / "DURUM.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    D.setdefault("ciftler", {})
    rapor_f = out / f"ORN_TASLAK_{pair}.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    title, desc, tags, alt, Q, hata = metin_kontrol(metin_satiri(pair), A)
    R["metin"] = dict(baslik_kr=len(title), etiket=len(tags), hata=hata)
    if hata:
        kaydet(); raise SystemExit(f"DUR-ON: metin kontrolu {hata}")
    g_dosya, video, mhata = medya(pair, A)
    if mhata:
        kaydet(); raise SystemExit(f"DUR-ON: medya {mhata}")
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    api.kota(KOTA_ILAN + (0 if getattr(api, "_harita", None) is not None else 30))   # tahmini istek + 10 (+ ilk tam tarama): yarim ilan acilmaz
    NIT = [(n["property_id"], n["ad"], n["value_ids"], n["values"], n.get("scale_id")) for n in A["taslak"]["nitelikler"]]

    def state_oku(adim, acil=True):
        L = None
        for i in range(6):
            L = api.get(f"/listings/{api.lid}", ok404=True)
            if L:
                break
            time.sleep(5 * (i + 1))
        if not L:
            kaydet(); raise SystemExit(f"DUR: /listings/{api.lid} okunamadi ({adim})")
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active" and not acil:            # var olan ilan (Serdar yayina almis olabilir): dokunulmaz
            kaydet(); raise SystemExit(f"DUR: var olan {api.lid} active ({adim}); dokunulmadi")
        if st == "active":
            st2, gitti = "?", False
            try:
                api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
                gitti = True
                st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            except BaseException as e:  # noqa: BLE001 PATCH/okuma hatasi da DUR (kod 2); dongu asla sonraki cifte gecmez
                st2 = f"{'PATCH gitti, okuma' if gitti else 'PATCH gonderilemedi'} hatasi {type(e).__name__}: {str(e)[:200]}"
            finally:
                R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
                print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive (simdi {st2}). DUR.", flush=True)
                if st2 != "inactive":
                    print(f"::error::ACIL BASARISIZ: {pair} listing {api.lid} hala {st2}; Etsy panelinden elle inactive yapilmali.", flush=True)
                raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: beklenmeyen state {st} ({adim})")
        return L

    def ayni_baslik(taze=False):
        """draft + inactive + active ilanlarda ayni baslik (html varliklari cozulur). Tam tarama kosuda bir kez (api._harita); sonraki
        ciftlerde yalniz ilk draft sayfasi tazelenir (kota). taze=True (BELIRSIZ): tam tarama. Birden fazla -> DUR."""
        H = getattr(api, "_harita", None)
        if H is None or taze:
            H = {}
            for st in ("draft", "inactive", "active"):
                off = 0
                while True:
                    r_ = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100, "offset": off}) or {}
                    for x in r_.get("results") or []:
                        H.setdefault(html.unescape(x.get("title") or ""), set()).add(x["listing_id"])
                    off += 100
                    if off >= (r_.get("count") or 0) or off > 2000:
                        break
            api._harita = H
        else:
            r_ = api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100, "offset": 0}) or {}
            for x in r_.get("results") or []:
                H.setdefault(html.unescape(x.get("title") or ""), set()).add(x["listing_id"])
        bul = set(H.get(title, set()))
        if len(bul) > 1:
            kaydet(); raise SystemExit(f"DUR: ayni baslikli {len(bul)} ilan {sorted(bul)}")
        return next(iter(bul), None)

    lid = D["ciftler"].get(pair)
    if lid == "BELIRSIZ":                      # onceki kosuda createDraftListing yaniti belirsiz kaldi: 3 kez ara, bulunamazsa DUR
        for i in range(3):
            lid = ayni_baslik(taze=True)
            if lid:
                break
            time.sleep(30)
        if not lid:
            kaydet(); raise SystemExit(f"DUR: {pair} BELIRSIZ olusturma; ayni baslikli ilan bulunamadi (elle kontrol, DURUM'dan BELIRSIZ silinir)")
        D["ciftler"][pair] = lid; kaydet()
    lid = lid or ayni_baslik()
    if lid:
        R["olusturma"] = f"VAR OLAN TASLAK {lid} (ikinci ilan acilmadi)"
        api.lid = lid
        L0 = api.get(f"/listings/{lid}", ok404=True)
        if not L0:
            kaydet(); raise SystemExit(f"DUR: var olan {lid} okunamadi")
        if L0.get("state") != "draft":        # yayindaki / pasif ilana dokunulmaz (acil PATCH dahil)
            kaydet(); raise SystemExit(f"DUR: var olan {lid} state {L0.get('state')} (draft degil); dokunulmadi")
        if html.unescape(L0.get("title") or "") != title or L0.get("taxonomy_id") != A["ilan"]["taxonomy_id"]:
            kaydet(); raise SystemExit(f"DUR: var olan {lid} baslik/kategori uyusmuyor ({L0.get('taxonomy_id')}); dokunulmadi")
    else:
        body = taslak_govde(A, title, desc, tags)
        api.taslak_kapi(shop, body)            # kapilar once (istek yok); gecemezse BELIRSIZ yazilmaz
        D["ciftler"][pair] = "BELIRSIZ"; kaydet()   # POST'tan ONCE: iptal / zaman asimi / kopma -> yeniden kosu once arar, yeni ilan acmaz
        kod, js, metin = api.taslak_olustur(shop, body)
        if kod in (200, 201) and (js or {}).get("listing_id"):
            lid = js["listing_id"]
            R["olusturma"] = "yeni taslak (tek POST)"
        else:
            if isinstance(kod, int) and 400 <= kod < 500:
                D["ciftler"].pop(pair, None)    # Etsy reddetti: ilan acilmadi (kesin)
            kaydet()
            raise SystemExit(f"DUR: createDraftListing {kod}: {metin}")
    api.lid = lid
    D["ciftler"][pair] = lid; kaydet()
    if getattr(api, "_harita", None) is not None:
        api._harita.setdefault(title, set()).add(lid)
    api.kota()
    print(f"::warning::{pair} listing_id {lid}")
    state_oku("1 olusturma", acil=R["olusturma"].startswith("yeni"))

    # envanter: ayardaki varyasyon menusu, fiyat / stok / readiness ayardan
    inv = api.get(f"/listings/{lid}/inventory") or {}
    if len(inv.get("products") or []) != len(ST):
        api.put_json(f"/listings/{lid}/inventory", envanter_govde(A, pair))
    state_oku("2 envanter")

    # gorseller (alt metinli) + video
    have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
    t0 = time.time()
    for rk, p in enumerate(g_dosya, 1):
        if rk in have:
            continue
        with open(p, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")},
                          data={"rank": str(rk), "alt_text": alt[rk - 1]})
        g = time.time() - t0
        print(f"{pair} gorsel [{rk}/{len(GAL)}] | gecen {g:.0f} sn | kalan ~{g / rk * (len(GAL) - rk):.0f} sn | %{100 * rk // len(GAL)}", flush=True)
    state_oku("3 gorseller")
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    if not vids and D.setdefault("video", {}).get(pair) == lid:   # onceki kosuda yuklendi, Etsy henuz gostermiyor: ikinci video yok
        for i in range(6):
            time.sleep(30)
            vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
            if vids:
                break
        if not vids:
            kaydet(); raise SystemExit(f"DUR: {pair} video onceki kosuda yuklendi ama gorunmuyor (ikinci video yuklenmedi)")
    if not vids:
        D.setdefault("video", {})[pair] = lid; kaydet()   # yuklemeden ONCE: 5xx / kopma sonrasi yeniden kosuda ikinci video yok
        with open(video, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("video.mp4", fh, "video/mp4")},
                          data={"name": f"AstroLoveArt_{pair}_ornament_video.mp4"})
    state_oku("4 video")

    # stil -> gorsel
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == V["property_id"] and v.get("value_ids")}
    if sorted(vid) != sorted(a for a, *_ in ST) or any(rank_id.get(rk) is None for _, _, rk, _ in ST):
        kaydet(); raise SystemExit(f"DUR: Style value_id {sorted(vid)} / rank {sorted(rank_id)}")
    api.stil_baglam = (dict(vid), dict(rank_id))
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": [dict(property_id=V["property_id"], value_id=vid[ad], image_id=rank_id[rk]) for ad, _, rk, _ in ST]})
    state_oku("5 stil gorselleri")

    api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": Q})
    state_oku("6 kisisellestirme")

    for pid_, ad, ids, vals, scale in NIT:
        b = {"value_ids": ",".join(str(i) for i in ids), "values": ",".join(vals)}
        if scale is not None:
            b["scale_id"] = scale
        api.put(f"/shops/{shop}/listings/{lid}/properties/{pid_}", b)
    state_oku("7 nitelikler")

    # geri okuma
    for _ in range(6):
        ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
        vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
        if all(x.get("full_width") for x in ims) and vids:
            break
        time.sleep(10)
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
    tablo = sorted(((({v.get("property_id"): (v.get("values") or [None])[0] for v in p.get("property_values") or []}).get(V["property_id"]),
                     para((p.get("offerings") or [{}])[0].get("price")), (p.get("offerings") or [{}])[0].get("quantity"), p.get("sku"),
                     (p.get("offerings") or [{}])[0].get("is_enabled"), (p.get("offerings") or [{}])[0].get("readiness_state_id"))
                    for p in inv.get("products") or []), key=str)
    I = A["ilan"]
    bek_tablo = sorted(((ad, I["fiyat"], I["quantity"], sku(pair, kd), True, I["readiness_state_id"]) for ad, kd, _, _ in ST), key=str)
    id_rank = {x.get("listing_image_id"): x.get("rank") for x in ims}
    vid2 = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
            if v.get("property_id") == V["property_id"] and v.get("value_ids")}
    bag = {vid2.get(v.get("value_id")): id_rank.get(v.get("image_id")) for v in vis if v.get("property_id") == V["property_id"]}
    soru = [(q.get("question_text"), q.get("instructions"), q.get("required"), q.get("max_allowed_characters"), q.get("question_type")) for q in per]
    bek_soru = [(q["question_text"], q["instructions"], True, q["max_allowed_characters"], "text_input") for q in Q]
    norm = lambda t: " ".join(str(t).split())  # noqa: E731
    alt_oku = [norm(html.unescape(x.get("alt_text") or "")) for x in ims]
    K = {
        "baslik": L.get("title") == title,
        "aciklama": html.unescape(L.get("description") or "").strip() == desc.strip(),
        "13 etiket": sorted(L.get("tags") or []) == sorted(tags),
        f"{len(ST)} secenek fiyat SKU stok": tablo == bek_tablo,
        f"{len(GAL)} gorsel 1-{len(GAL)}": [x.get("rank") for x in ims] == list(range(1, len(GAL) + 1)),
        "alt metinler": alt_oku == [norm(a) for a in alt],
        "video": len(vids) == 1,
        "stil gorselleri": bag == {ad: rk for ad, _, rk, _ in ST},
        "3 kutu zorunlu": soru == bek_soru,
        "state draft": L.get("state") == "draft",
        "kargo iade bolum ortak": (L.get("shipping_profile_id"), L.get("return_policy_id"), L.get("shop_section_id"),
                                   sorted(p_.get("production_partner_id") for p_ in L.get("production_partners") or []))
        == (I["shipping_profile_id"], I["return_policy_id"], I["shop_section_id"], [I["production_partner_id"]]),
        "who_made when_made tur malzeme kategori": (L.get("who_made"), L.get("when_made"), L.get("listing_type") or L.get("type"),
                                                    [m.lower() for m in L.get("materials") or []], L.get("taxonomy_id"))
        == (I["who_made"], I["when_made"], I["type"], [m.lower() for m in I["materials"]], I["taxonomy_id"]),
        "nitelikler": sorted((p_.get("property_id"), tuple(p_.get("value_ids") or [])) for p_ in props)
        == sorted((a, tuple(b_)) for a, _, b_, _, _ in NIT),
    }
    R["kontrol"] = K
    R["son"] = dict(listing_id=lid, state=L.get("state"), link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    tablo=tablo, bag=bag, gorsel=[(x.get("rank"), x.get("full_width"), x.get("full_height")) for x in ims],
                    video=[(v.get("video_id"), v.get("video_state")) for v in vids], kutular=soru, alt_fark=[i + 1 for i, (a_, b_) in enumerate(zip(alt_oku, alt)) if a_ != norm(b_)],
                    nitelik=[(p_.get("property_name"), p_.get("values")) for p_ in props], url=L.get("url"))
    R["kota_son"] = api.remaining
    kaydet()
    kotu = [k_ for k_, v_ in K.items() if not v_]
    print(f"::warning::{pair} TASLAK {lid} state={L.get('state')} | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if L.get("state") != "draft":
        raise SystemExit(f"HATA: {pair} son state {L.get('state')}")
    if kotu:
        raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    if pair not in D.setdefault("tamam", []):
        D["tamam"].append(pair); kaydet()
    return R


# ------------------------------------------------------------------ kuru (ag yok)
class Kuru(Kilitli):
    kuru = True

    def __init__(self, shop):
        self.shop, self.calls, self.remaining, self.lid = str(shop), 0, "KURU", None
        self.kayit = []
        self.L, self.inv, self.ims, self.vids, self.vis, self.per, self.props = None, None, [], [], [], [], {}
        self.A = ayar()

    def _kaydet(self, method, path, params=None, data=None, json_body=None, files=None):
        k = dict(no=len(self.kayit) + 1, method=method, url=API + path, yazma=method != "GET")
        for ad, v in (("params", params), ("form", data), ("json", json_body)):
            if v is not None:
                k[ad] = v
        if files:
            k["dosya"] = {a: dict(ad=f[0], mime=f[2], bayt=os.fstat(f[1].fileno()).st_size) for a, f in files.items()}
        self.kayit.append(k); self.calls += 1

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and (data != {"state": "inactive"} or json_body is not None or params):
                raise SystemExit("YASAK: PATCH yalniz acil durum")
            c = self._ayar_kapi(method, path, data, json_body)
            if c:                                  # Etsy._call'un html_coz'u: gercekte gidecek govde kaydedilir
                data, json_body = c
            ru_yazim_kapisi(method, path, data, json_body)       # Etsy._call ile ayni kapi dizisi (kuru = gercek yol)
            ai_beyan_kapisi(method, path, data, json_body, params); metin_yasak_kapisi(method, path, data, json_body, params)
        self._kaydet(method, path, params, data, json_body)
        return self._sim(method, path, params, data, ok404, json_body)

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        c = self._ayar_kapi("POST", path, data=data)
        data = c[0] if c else data
        ai_beyan_kapisi("POST", path, data)                     # Etsy.post_file ile ayni kapi dizisi
        metin_yasak_kapisi("POST", path, data)
        self._kaydet("POST", path, data=data, files=files)
        if path.endswith("/images"):
            rk = int(data["rank"])
            self.ims.append(dict(rank=rk, listing_image_id=800000 + rk, full_width=3000, full_height=2250, alt_text=data.get("alt_text")))
            return self.ims[-1]
        self.vids.append(dict(video_id=900001, video_state="active")); return self.vids[-1]

    def taslak_olustur(self, shop, body):
        body = self._tek_kapilar(shop, body)     # Kilitli ile ayni kapi dizisi; kaydedilen = gonderilecek (cozulmus) govde
        self._kaydet("POST", f"/shops/{shop}/listings", data=body)
        self.n = getattr(self, "n", 0) + 1
        lid = 9000000000 + self.n
        self.inv, self.ims, self.vids, self.vis, self.per, self.props = None, [], [], [], [], {}
        self.L = dict(listing_id=lid, state="draft", title=body["title"], description=body["description"], tags=body["tags"].split(","),
                      who_made=body["who_made"], when_made=body["when_made"], listing_type=body["type"], materials=body["materials"].split(","),
                      taxonomy_id=body["taxonomy_id"], shipping_profile_id=body["shipping_profile_id"], return_policy_id=body["return_policy_id"],
                      shop_section_id=body["shop_section_id"], production_partners=[dict(production_partner_id=int(body["production_partner_ids"]))])
        return 201, dict(listing_id=lid), ""

    def _sim(self, method, path, params, data, ok404, js):
        s, lid = self.shop, self.lid
        if method == "GET":
            if path == f"/shops/{s}":
                return {}
            if path == f"/shops/{s}/listings":
                return dict(results=[], count=0)
            if path == f"/listings/{lid}":
                return self.L
            if path == f"/listings/{lid}/inventory":
                return self.inv or dict(products=[])
            if path == f"/listings/{lid}/images":
                return dict(results=self.ims)
            if path == f"/listings/{lid}/videos":
                return dict(results=self.vids)
            if path == f"/listings/{lid}/personalization":
                return dict(personalization_questions=self.per)
            if path == f"/shops/{s}/listings/{lid}/properties":
                return dict(results=list(self.props.values()))
            if path == f"/shops/{s}/listings/{lid}/variation-images":
                return dict(results=self.vis)
            raise SystemExit(f"KURU: taklit edilmeyen GET {path}")
        if path == f"/listings/{lid}/inventory":
            urun = []
            for i, p in enumerate(js["products"]):
                pv = [dict(v, value_ids=[5000 + i]) for v in p["property_values"]]
                o = p["offerings"][0]
                urun.append(dict(sku=p["sku"], property_values=pv, offerings=[dict(o, price=dict(amount=round(o["price"] * 100), divisor=100))]))
            self.inv = dict(products=urun); return self.inv
        if path.endswith("/variation-images"):
            self.vis = js["variation_images"]; return dict(results=self.vis)
        if path.endswith("/personalization"):
            self.per = js["personalization_questions"]; return js
        if "/properties/" in path:
            pid_ = int(path.rsplit("/", 1)[1])
            self.props[pid_] = dict(property_id=pid_, value_ids=[int(x) for x in data["value_ids"].split(",")], values=data["values"].split(","))
            return self.props[pid_]
        if method == "PATCH":
            self.L["state"] = data["state"]; return self.L
        raise SystemExit(f"KURU: taklit edilmeyen {method} {path}")


def kuru(shop, out, pair):
    api = Kuru(shop)
    o2 = out / "kuru"; o2.mkdir(parents=True, exist_ok=True)
    (o2 / "DURUM.json").unlink(missing_ok=True)
    R = yaz(api, shop, o2, pair)
    yazma = [k for k in api.kayit if k["yazma"]]
    ozet = dict(cift=pair, istek=len(api.kayit), yazma=len(yazma), kontrol=R["kontrol"], metin=R["metin"])
    json.dump(dict(ozet=ozet, istekler=api.kayit), open(o2 / f"KURU_{pair}.json", "w"), indent=1, ensure_ascii=False)
    print(f"KURU {pair}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol {sum(R['kontrol'].values())}/{len(R['kontrol'])}")
    (o2 / "DURUM.json").unlink(missing_ok=True)
    return ozet


def cift_listesi(girdi):
    secim = CIFTLER if girdi.strip().upper() == "TUMU" else [c.strip().upper() for c in re.split(r"[,\s]+", girdi) if c.strip()]
    bil = [c for c in secim if c not in CIFTLER]
    if bil or not secim:
        raise SystemExit(f"DUR: bilinmeyen cift {bil}")
    return secim


def yaz_dongu(api, shop, out, ciftler, parti_max=PARTI_MAX, sure_dk=SURE_DK, on_ardisik_max=3):
    """Her hata DUR (CLAUDE.md Etsy 3: FAIL / son okuma farki -> DUR). Tek istisna: ag ONCESI metin/medya DUR'u ("DUR-ON:"), hic istek
    yok; o cift atlanir, ard arda 3 olursa DUR. Parti: en fazla parti_max yeni cift ve kilit anindan sure_dk; kalan yeniden kosuda."""
    t0 = time.time()
    t_kilit = float(os.environ.get("KILIT_T0") or t0)
    D = json.load(open(out / "DURUM.json")) if (out / "DURUM.json").exists() else {}
    on_ardisik, yeni = 0, 0
    for i, c in enumerate(ciftler, 1):
        api.lid = None
        if c in D.get("tamam", []):
            print(f"::warning::{c} ATLANDI: tamam ({D.get('ciftler', {}).get(c)})")
            continue
        if yeni >= parti_max or (time.time() - t_kilit) / 60 >= sure_dk:
            kalan = [x for x in ciftler[i - 1:] if x not in D.get("tamam", [])]
            msg = f"PARTI SINIRI: {yeni} cift / {(time.time() - t_kilit) / 60:.0f} dk; KALAN {len(kalan)} cift yeniden kosuda (DURUM tamamlari atlar)"
            print(f"::warning::{msg}")
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(msg + "\n")
            break
        yeni += 1
        try:
            yaz(api, shop, out, c)
            on_ardisik = 0
        except BaseException as e:  # noqa: BLE001
            f = out / f"ORN_TASLAK_{c}.json"
            R = json.load(open(f)) if f.exists() else {}
            R["hata"] = f"{type(e).__name__}: {e}"[:1500]
            json.dump(R, open(f, "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::error::ORN YAZ HATA {c} {R['hata'][:600]}")
            on_hata = isinstance(e, SystemExit) and isinstance(e.code, str) and e.code.startswith("DUR-ON:")
            if not on_hata:
                raise
            on_ardisik += 1
            if on_ardisik >= on_ardisik_max:
                raise
        D = json.load(open(out / "DURUM.json")) if (out / "DURUM.json").exists() else D
        g = time.time() - t0
        hedef = min(parti_max, len([x for x in ciftler if x not in D.get("tamam", [])]) + yeni)
        print(f"ETA parti [{yeni}/{hedef}] {c} | gecen {g / 60:.1f} dk | kalan ~{g / max(yeni, 1) * max(hedef - yeni, 0) / 60:.1f} dk | %{100 * yeni // max(hedef, 1)} | kota {api.remaining}", flush=True)


def liste_yaz(out):
    D = json.load(open(out / "DURUM.json")) if (out / "DURUM.json").exists() else {}
    say = {}
    with open(out / "ORN_TASLAK_LISTE.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["cift", "listing_id", "durum", "neden", "link"])
        for c in CIFTLER:
            lid = D.get("ciftler", {}).get(c, "")
            f = out / f"ORN_TASLAK_{c}.json"
            hata = (json.load(open(f)).get("hata") or "") if f.exists() else ""
            durum = ("TAMAM" if c in D.get("tamam", []) else "BELIRSIZ" if lid == "BELIRSIZ" else "YARIM" if lid
                     else "FAIL" if hata else "ACILMADI")
            say[durum] = say.get(durum, 0) + 1
            w.writerow([c, lid, durum, hata[:300], f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}" if str(lid).isdigit() else ""])
    print(f"::warning::LISTE {say}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "kur", "kuru", "yaz"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    ciftler = cift_listesi(a.ciftler)
    if a.mod == "kuru":
        for c in ciftler:
            kuru(os.environ.get("ETSY_SHOP_ID", "39729443"), out, c)
        return
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out); return
    if a.mod == "kur":
        kur(KurIzin(store), shop, out, None); return
    if os.environ.get("METIN_CSV"):
        raise SystemExit("DUR: yaz modunda METIN_CSV yasak (metin yalniz depodaki data/pod/ORNAMENT78_METIN.csv)")
    if os.environ.get("URUN_AYAR"):
        raise SystemExit("DUR: yaz modunda URUN_AYAR yasak (ayar yalniz depodaki docs/urun/ornament78/URUN_AYAR.json)")
    try:
        yaz_dongu(Kilitli(store), shop, out, ciftler)
    finally:
        liste_yaz(out)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
