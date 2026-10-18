#!/usr/bin/env python3
"""KUPA: CANCER_LIBRA kupa ilani TASLAK (Serdar 18 Eki 2026). YAYIN YOK, Etsy Ads YOK.

--mod oku  : SALT OKUMA (Etsy'ye yazma yok; kilitli istemci her yazmayi durdurur).
             kupa kategorisi (taxonomy) adaylari + secilen dugumun nitelikleri (zorunlu/istege bagli, olasi degerler),
             Bizim Yilimiz CANCER_LIBRA ilaninin hazirlik ayari (readiness_state_id, processing, kargo profili),
             iade politikalari, uretim ortaklari, bolumler, kargo profilleri, ayni baslikli taslak var mi,
             Etsy OAS (statik): ilgili uclarin istek alanlari (production partner olusturma ucu var mi dahil).
             Cikti: OUT/KUPA_OKU.json + OUT/KUPA_OKU.md
--mod yaz  : ETSY'YE YAZAR (Serdar onayi 18 Eki). Yalniz yeni kayitlar + 1 taslak; mevcut ilan/profil/politika/ortaga yazma YOK.
             a) bolum "Zodiac Couple Mugs" (yoksa POST), kargo profili "Kupa Free US UK EU" (yoksa POST; US/EU/GB 0 USD,
                baska hedef yok; islem 4-7 is gunu ve teslim gunleri BY profiliyle ayni), iade politikasi iade yok/degisim yok
                (mevcut 1513990287785 ayniysa o; yoksa POST), uretim ortagi 5817638 (Serdar 18 Eki: mevcut ortak; API olusturamaz).
             b) createDraftListing (tek POST): CSV basligi/aciklamasi/13 etiket birebir, i_did, made_to_order, fiziksel,
                Ceramic, kategori 1062 Mugs, readiness BY ile ayni (1517641240112), fiyat 24.00, stok 999.
             c) envanter: Style (513) x Size (514) = 14 urun, fiyat yalniz boya gore (11 oz 24.00, 15 oz 29.00), stok 999,
                SKU KUPA-CANCER_LIBRA-<stil no>-<11|15>.  d) 13 gorsel (galeri 01-13 sirasi) + video.
             e) Style -> kapak baglari (Rose Ribbon=01, Botanical=03 ... Mediterranean=08).  f) kisisellestirme: tek kutu,
                zorunlu, 256 karakter, talimat CSV.  g) nitelikler (kategori 1062).  h) geri okuma kontrolleri.
             Her yazmadan sonra state okunur; "active" gorulurse aninda state=inactive + DUR. updateListing (PATCH) YOK
             (CLAUDE.md: taslagi yayina alir); PATCH yalniz acil {"state": "inactive"}. Ikinci kosu ikinci ilan acmaz
             (DURUM.json + ayni baslikli taslak). Cikti: OUT/KUPA_TASLAK.json + OUT/DURUM.json
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, BY_CSV (BY78_TASLAKLAR.csv), KUPA_CSV, IMG_DIR, OUT
Kota tabani 10 (Serdar 15 Eki): x-remaining-today < 10 ise DUR.
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402

PAIR = "CANCER_LIBRA"
KOTA_MIN = 10
OAS = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
OAS_OP = ["createDraftListing", "createShopReturnPolicy", "createShopShippingProfile", "createShopShippingProfileDestination",
          "createShopSection", "getShopProductionPartners", "uploadListingVideo", "updateVariationImages",
          "updateListingPersonalization", "updateListingProperty", "updateListingInventory", "uploadListingImage",
          "getListingPersonalization", "getShopReadinessStateDefinitions", "createShopReadinessStateDefinition"]
KUPA_ADLARI = ("mug", "mugs")


class SaltOkur(Etsy):
    """Her yazma cagrisi programi durdurur; her cevaptan sonra kota tabani kontrol edilir."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        try:
            if self.remaining is not None and int(self.remaining) < KOTA_MIN:
                raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        except ValueError:
            pass
        return r

    def post(self, *a, **k):
        raise SystemExit("YASAK: POST")

    def put(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def patch(self, *a, **k):
        raise SystemExit("YASAK: PATCH")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")

    def post_json(self, *a, **k):
        raise SystemExit("YASAK: POST json")

    def put_json(self, *a, **k):
        raise SystemExit("YASAK: PUT json")

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


def oas_ozet():
    d = requests.get(OAS, timeout=120).json()
    S = d.get("components", {}).get("schemas", {})

    def coz(x, n=0):
        if n > 4 or not isinstance(x, dict):
            return x
        if "$ref" in x:
            return coz(S.get(x["$ref"].split("/")[-1], {}), n + 1)
        if "allOf" in x:
            return coz(x["allOf"][0], n + 1)
        return x

    R = {"surum": d.get("info", {}).get("version"), "uclar": {}, "production_partner_yollari": {}}
    for path, ops in d.get("paths", {}).items():
        for m, op in ops.items():
            if not isinstance(op, dict):
                continue
            if "production-partner" in path:
                R["production_partner_yollari"][f"{m.upper()} {path}"] = op.get("operationId")
            if op.get("operationId") not in OAS_OP:
                continue
            alan = {}
            for ct, c in ((op.get("requestBody") or {}).get("content") or {}).items():
                sc = coz(c.get("schema") or {})
                for k, v in (sc.get("properties") or {}).items():
                    v = coz(v)
                    it = coz(v.get("items") or {}) if v.get("type") == "array" else {}
                    alan[k] = dict(tip=v.get("type"), enum=v.get("enum") or it.get("enum"), zorunlu=k in (sc.get("required") or []),
                                   min=v.get("minimum", v.get("minLength")), max=v.get("maximum", v.get("maxLength")),
                                   oge=sorted((it.get("properties") or {}).keys()) if it else None,
                                   aciklama=(v.get("description") or "")[:400])
            R["uclar"][op["operationId"]] = dict(yol=f"{m.upper()} {path}", ozet=(op.get("summary") or "")[:200],
                                                 aciklama=(op.get("description") or "")[:900], alanlar=alan,
                                                 parametreler=[(p.get("in"), p.get("name"), p.get("required")) for p in op.get("parameters") or []])
    pq = S.get("ListingPersonalizationQuestion") or next((S[k] for k in S if k.endswith("PersonalizationQuestion")), None)
    if pq:
        R["kisisellestirme_soru_semasi"] = {k: (coz(v).get("type"), coz(v).get("enum"), (coz(v).get("description") or "")[:300])
                                            for k, v in (pq.get("properties") or {}).items()}
    return R


def oku(api, shop, out):
    R = {"kota_bas": None}
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining

    # 1) kupa kategorisi
    duz = agac_duz((api.get("/seller-taxonomy/nodes") or {}).get("results"))
    aday = [(i, " > ".join(p), c) for i, p, c in duz if (p[-1] or "").strip().lower() in KUPA_ADLARI]
    R["kategori_adaylari"] = aday
    yaprak = [a for a in aday if not a[2]]
    tercih = [a for a in yaprak if "drinkware" in a[1].lower()] or yaprak
    R["kategori"] = dict(id=tercih[0][0], yol=tercih[0][1]) if tercih else None
    if R["kategori"]:
        props = (api.get(f"/seller-taxonomy/nodes/{R['kategori']['id']}/properties") or {}).get("results") or []
        R["nitelikler"] = [dict(property_id=p.get("property_id"), ad=p.get("name"), gorunen=p.get("display_name"),
                                zorunlu=p.get("is_required"), varyasyon=p.get("supports_variations"),
                                coklu=p.get("is_multivalued"), max_deger=p.get("max_values_allowed"),
                                attribute=p.get("supports_attributes"),
                                olcekler=[(s.get("scale_id"), s.get("display_name")) for s in p.get("scales") or []],
                                degerler=[(v.get("value_id"), v.get("name"), v.get("scale_id")) for v in p.get("possible_values") or []])
                           for p in props]

    # 2) Bizim Yilimiz CANCER_LIBRA ilani (hazirlik ayari)
    by = next((r for r in csv.DictReader(open(os.environ["BY_CSV"], encoding="utf-8")) if r.get("cift") == PAIR), None)
    R["by_csv_satir"] = by
    lid = int(by["listing_id"]) if by and by.get("listing_id") else None
    if lid:
        L = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        rs = sorted({o.get("readiness_state_id") for p in inv.get("products") or [] for o in p.get("offerings") or []
                     if o.get("readiness_state_id")})
        sp = api.get(f"/shops/{shop}/shipping-profiles/{L.get('shipping_profile_id')}", ok404=True) or {}
        R["by_ilan"] = dict(listing_id=lid, state=L.get("state"), processing=(L.get("processing_min"), L.get("processing_max")),
                            readiness_state_ids=rs, shipping_profile_id=L.get("shipping_profile_id"),
                            return_policy_id=L.get("return_policy_id"), who_made=L.get("who_made"), when_made=L.get("when_made"),
                            production_partners=L.get("production_partners"), shop_section_id=L.get("shop_section_id"),
                            personalization=(L.get("is_personalizable"), L.get("personalization_is_required"),
                                             L.get("personalization_char_count_max")))
        R["by_kargo_profili"] = dict(
            id=sp.get("shipping_profile_id"), ad=sp.get("title"), cikis=(sp.get("origin_country_iso"), sp.get("origin_postal_code")),
            islem=(sp.get("min_processing_days"), sp.get("max_processing_days"), sp.get("processing_days_display_label")),
            hedefler=[(d.get("destination_country_iso") or d.get("destination_region"), para(d.get("primary_cost")),
                       para(d.get("secondary_cost")), d.get("min_delivery_days"), d.get("max_delivery_days"))
                      for d in sp.get("shipping_profile_destinations") or []],
            ham_anahtarlar=sorted(sp.keys()))
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    R["hazirlik_tanimlari"] = [dict(id=x.get("readiness_state_id"), durum=x.get("readiness_state"), min=x.get("min_processing_days"),
                                    max=x.get("max_processing_days"), etiket=x.get("processing_days_display_label")) for x in rsd]

    # 3) iade, ortak, bolum, kargo profilleri, ayni baslikli taslak
    rp = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    R["iade_politikalari"] = [dict(id=x.get("return_policy_id"), iade=x.get("accepts_returns"), degisim=x.get("accepts_exchanges"),
                                   sure=x.get("return_deadline")) for x in rp]
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    R["uretim_ortaklari"] = [dict(id=x.get("production_partner_id"), ad=x.get("partner_name"), konum=x.get("location")) for x in pp]
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    R["bolumler"] = [dict(id=x.get("shop_section_id"), ad=x.get("title"), aktif_ilan=x.get("active_listing_count")) for x in secs]
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    R["kargo_profilleri"] = [dict(id=x.get("shipping_profile_id"), ad=x.get("title")) for x in sps]
    if os.environ.get("KUPA_CSV"):
        row = next(r for r in csv.DictReader(open(os.environ["KUPA_CSV"], encoding="utf-8")) if r["kod"] == PAIR)
        drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
        R["ayni_baslikli_taslak"] = [x.get("listing_id") for x in drafts if x.get("title") == row["baslik"]]
    R["kota_son"] = api.remaining
    R["cagri"] = api.calls

    # 4) OAS (statik dosya, kota harcamaz)
    try:
        R["oas"] = oas_ozet()
    except Exception as e:  # noqa: BLE001
        R["oas"] = dict(hata=str(e)[:300])

    json.dump(R, open(out / "KUPA_OKU.json", "w"), indent=1, ensure_ascii=False, default=str)
    md = [f"# KUPA OKU ({PAIR})", f"kota bas {R['kota_bas']} son {R['kota_son']} cagri {R['cagri']}",
          f"kategori: {R.get('kategori')}", f"kategori adaylari: {R['kategori_adaylari']}", "", "## Nitelikler"]
    for p in R.get("nitelikler") or []:
        md.append(f"- {p['property_id']} {p['ad']} zorunlu={p['zorunlu']} varyasyon={p['varyasyon']} coklu={p['coklu']} "
                  f"olcek={p['olcekler']} degerler({len(p['degerler'])})={[d[1] for d in p['degerler']][:40]}")
    md += ["", f"BY ilan: {R.get('by_ilan')}", f"BY kargo: {R.get('by_kargo_profili')}", f"hazirlik: {R['hazirlik_tanimlari']}",
           f"iade: {R['iade_politikalari']}", f"ortak: {R['uretim_ortaklari']}", f"bolum: {R['bolumler']}",
           f"kargo profilleri: {R['kargo_profilleri']}", f"ayni baslikli taslak: {R.get('ayni_baslikli_taslak')}",
           f"OAS production partner yollari: {(R['oas'] or {}).get('production_partner_yollari')}"]
    (out / "KUPA_OKU.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"::warning::OKU kategori {R.get('kategori')} | nitelik {len(R.get('nitelikler') or [])} | BY readiness "
          f"{(R.get('by_ilan') or {}).get('readiness_state_ids')} | iade {len(rp)} ortak {len(pp)} bolum {len(secs)} | "
          f"kota {R['kota_bas']} -> {R['kota_son']} | OAS partner {(R['oas'] or {}).get('production_partner_yollari')}")
    return R


# ------------------------------------------------------------------ yaz
TAXONOMY = 1062                     # Home & Living > Kitchen & Dining > Drink & Barware > Drinkware > Mugs (oku 18 Eki)
READINESS = 1517641240112           # made_to_order 4-7 gun = BY CANCER_LIBRA 4595350971 (oku 18 Eki)
PARTNER = 5817638                   # "Printing and Fulfillment Partner", United States (Serdar 18 Eki)
IADE_ID = 1513990287785             # iade yok, degisim yok (oku 18 Eki; ayni kayit kullanilir)
BOLUM_AD = "Zodiac Couple Mugs"
PROFIL_AD = "Kupa Free US UK EU"
ORIGIN = ("US", "28216")            # BY profiliyle ayni cikis
ISLEM = (4, 7)                      # BY ile ayni hazirlik (4-7 is gunu)
# (anahtar, tur, kod, ucret, min, max teslim gunu) = BY profilindeki US/EU/GB degerleri; baska hedef YOK
HEDEF = [("US", "country", "US", 0, 3, 8), ("EU", "region", "eu", 0, 5, 12), ("GB", "country", "GB", 0, 5, 10)]
P_STYLE, P_SIZE = 513, 514
STILLER = [("Rose Ribbon", "04", "RoseRibbon", 1), ("Botanical", "01", "Botanical", 3), ("Gold", "02", "Gold", 4),
           ("Nazar Bond", "03", "NazarBond", 5), ("Promise Line", "05", "PromiseLine", 6), ("Aegean Tile", "06", "AegeanTile", 7),
           ("Mediterranean", "07", "Mediterranean", 8)]          # (menu adi, stil no, dosya adi parcasi, kapak rank)
BOYLAR = [("11 oz", "11", 24.00), ("15 oz", "15", 29.00)]
MALZEME = ["Ceramic"]
SORU_METNI = "Personalization"
SORU_MAX = 256
# kategori 1062 nitelikleri: (property_id, ad, value_ids, values)
NITELIK = [(148789511893, "Materials", [83], ["Ceramic"]), (200, "Primary color", [10], ["White"]),
           (47626760110, "Dishwasher safe", [1094], ["Yes"]), (47626760308, "Microwave safe", [1144], ["Yes"]),
           (406291158703, "Handle", [3554], ["Yes"]), (325502674580, "Insulated", [2612], ["No"]),
           (406291158731, "Enamel", [3557], ["No"]), (46803063641, "Occasion", [32], ["Wedding"]),
           (396998957792, "Graphic", [2534], ["Zodiac"])]
NITELIK_BOS = ["Secondary color (stile gore degisir)", "Width/Height/Depth (iki boy)", "Capacity (iki boy; Size menusu)",
               "Holiday (BY ile ayni: bos)", "Material features (Upcycled degil)"]
TIRE = re.compile("[\u2013\u2014]")


def sku(no, boy):
    return f"KUPA-{PAIR}-{no}-{boy}"


def metin_kontrol(row):
    title, desc = row["baslik"], row["aciklama"]
    tags = [t.strip() for t in row["etiketler"].split(",")]
    inst = row["kisisellestirme_talimati"]
    hata = []
    if TIRE.search(title + desc + " ".join(tags) + inst):
        hata.append("uzun/orta tire var")
    if len(title) > 140:
        hata.append(f"baslik {len(title)} > 140")
    if len(tags) != 13 or len(set(tags)) != 13:
        hata.append(f"etiket sayisi {len(tags)} (tekil {len(set(tags))})")
    uzun = [t for t in tags if len(t) > 20]
    if uzun:
        hata.append(f"20 karakteri asan etiket {uzun}")
    if not re.fullmatch(r"[A-Za-z0-9 ]+", "".join(tags).replace(" ", "") or "x"):
        hata.append("etikette harf/rakam/bosluk disi karakter")
    if len(inst) > SORU_MAX:
        hata.append(f"talimat {len(inst)} > {SORU_MAX}")
    if "AstroLove " in desc.replace("AstroLoveArt", ""):
        hata.append("aciklamada yalniz 'AstroLove' (marka AstroLoveArt)")
    return title, desc, tags, inst, hata


class Kilitli(Etsy):
    """Izinli yazmalar: yeni bolum/profil/hedef/iade, taslak olusturma ve YALNIZ bu taslagin alt uclari.
    PATCH yalniz acil {"state": "inactive"}. DELETE yok. Kota < 10 -> DUR."""
    lid = None
    profil = None
    iade_izin = False

    def _izin(self, method, path):
        ok = [("POST", r"^/shops/\d+/sections$"), ("POST", r"^/shops/\d+/shipping-profiles$"),
              ("POST", r"^/shops/\d+/listings$")]
        if self.profil:
            ok.append(("POST", rf"^/shops/\d+/shipping-profiles/{self.profil}/destinations$"))
        if self.iade_izin:
            ok.append(("POST", r"^/shops/\d+/policies/return$"))
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
            if method == "PATCH" and kw.get("data") != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        r = super()._call(method, path, **kw)
        self.kota()
        return r

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        r = super().post_file(path, files, data)
        self.kota()
        return r

    def kota(self):
        try:
            if self.remaining is not None and int(self.remaining) < KOTA_MIN:
                raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        except ValueError:
            pass

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")


def yaz(api, shop, out):
    R = {"olaylar": [], "adimlar": [], "nitelik_bos": NITELIK_BOS}
    durum_f = out / "DURUM.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(out / "KUPA_TASLAK.json", "w"), indent=1, ensure_ascii=False, default=str)

    row = next(r for r in csv.DictReader(open(os.environ["KUPA_CSV"], encoding="utf-8")) if r["kod"] == PAIR)
    title, desc, tags, inst, hata = metin_kontrol(row)
    R["metin"] = dict(baslik_kr=len(title), etiket=len(tags), etiket_max=max(len(t) for t in tags), talimat_kr=len(inst),
                      tire_yok=not TIRE.search(title + desc + " ".join(tags) + inst))
    if hata:
        kaydet(); raise SystemExit(f"DUR: metin kontrolu {hata}")
    img_dir = Path(os.environ["IMG_DIR"])
    galeri = sorted(img_dir.glob("[0-1][0-9]_*.jpg"))
    video = sorted(img_dir.glob("VIDEO_*.mp4"))
    if [int(p.name[:2]) for p in galeri] != list(range(1, 14)) or len(video) != 1:
        kaydet(); raise SystemExit(f"DUR: galeri {[p.name for p in galeri]} video {[p.name for p in video]}")
    for ad, no, parca, rk in STILLER:
        if parca not in galeri[rk - 1].name:
            kaydet(); raise SystemExit(f"DUR: kapak {rk} ({galeri[rk - 1].name}) {ad} degil")
    R["galeri"] = [p.name for p in galeri] + [video[0].name]

    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    print(f"kota basta {api.remaining}")

    # a) kayitlar
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    if PARTNER not in [x.get("production_partner_id") for x in pp]:
        kaydet(); raise SystemExit(f"DUR: uretim ortagi {PARTNER} yok")
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    b = [x for x in secs if (x.get("title") or "").strip().lower() == BOLUM_AD.lower()]
    if b:
        bolum = b[0]["shop_section_id"]; R["olaylar"].append(f"bolum zaten var {bolum}")
    else:
        if len(secs) >= 20:
            kaydet(); raise SystemExit("DUR: bolum sayisi 20")
        api.post(f"/shops/{shop}/sections", {"title": BOLUM_AD})
        secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
        b = [x for x in secs if (x.get("title") or "").strip().lower() == BOLUM_AD.lower()]
        if len(b) != 1:
            kaydet(); raise SystemExit("DUR: bolum olusmadi")
        bolum = b[0]["shop_section_id"]; R["olaylar"].append(f"bolum OLUSTURULDU {bolum}")
    R["bolum"] = bolum

    rps = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    uygun = [x for x in rps if x.get("accepts_returns") is False and x.get("accepts_exchanges") is False]
    if uygun:
        iade = IADE_ID if IADE_ID in [x["return_policy_id"] for x in uygun] else uygun[0]["return_policy_id"]
        R["olaylar"].append(f"iade politikasi mevcut kullanildi {iade}")
    else:
        api.iade_izin = True
        r_ = api.post(f"/shops/{shop}/policies/return", {"accepts_returns": "false", "accepts_exchanges": "false"}) or {}
        api.iade_izin = False
        iade = r_.get("return_policy_id")
        R["olaylar"].append(f"iade politikasi OLUSTURULDU {iade}")
    R["iade"] = iade

    def hedef_anahtar(x):
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        return cc if cc else ("EVERYWHERE" if rg == "none" else rg.upper())

    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    v = [x for x in sps if (x.get("title") or "").strip() == PROFIL_AD]
    if len(v) > 1:
        kaydet(); raise SystemExit(f"DUR: ayni adla {len(v)} profil")
    if v:
        pid = v[0]["shipping_profile_id"]; R["olaylar"].append(f"kargo profili zaten var {pid}")
        prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
    else:
        _, _, kod, ucret, dmin, dmax = HEDEF[0]
        body = {"title": PROFIL_AD, "origin_country_iso": ORIGIN[0], "origin_postal_code": ORIGIN[1], "primary_cost": ucret,
                "secondary_cost": ucret, "min_processing_time": ISLEM[0], "max_processing_time": ISLEM[1],
                "processing_time_unit": "business_days", "destination_country_iso": kod, "min_delivery_days": dmin,
                "max_delivery_days": dmax}
        prof = api.post(f"/shops/{shop}/shipping-profiles", body) or {}
        pid = prof.get("shipping_profile_id")
        if not pid:
            kaydet(); raise SystemExit(f"DUR: kargo profili olusmadi {str(prof)[:200]}")
        R["olaylar"].append(f"kargo profili OLUSTURULDU {pid}")
    api.profil = pid
    var = {hedef_anahtar(x) for x in prof.get("shipping_profile_destinations") or []}
    for key, tur, kod, ucret, dmin, dmax in HEDEF:
        if key in var:
            continue
        body = {"primary_cost": ucret, "secondary_cost": ucret, "min_delivery_days": dmin, "max_delivery_days": dmax}
        body["destination_country_iso" if tur == "country" else "destination_region"] = kod
        api.post(f"/shops/{shop}/shipping-profiles/{pid}/destinations", body)
        R["olaylar"].append(f"kargo hedefi eklendi {key} {ucret} USD {dmin}-{dmax} gun")
    son = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
    hed = {hedef_anahtar(x): (para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"),
                              x.get("max_delivery_days")) for x in son.get("shipping_profile_destinations") or []}
    bek = {k_: (float(u), float(u), a, b_) for k_, _, _, u, a, b_ in HEDEF}
    R["kargo_profili"] = dict(id=pid, ad=son.get("title"), cikis=(son.get("origin_country_iso"), son.get("origin_postal_code")),
                              hedefler=hed)
    if hed != bek:
        kaydet(); raise SystemExit(f"DUR: kargo hedefleri {hed} != {bek}")
    kaydet()

    # b) taslak
    def state_oku(adim):
        L = None
        for i in range(6):                 # yeni ilan birkac saniye 404 donebilir
            L = api.get(f"/listings/{api.lid}", ok404=True)
            if L:
                break
            print(f"{adim}: GET /listings/{api.lid} 404, {5 * (i + 1)} sn bekleniyor", flush=True)
            time.sleep(5 * (i + 1))
        if not L:
            kaydet(); raise SystemExit(f"DUR: /listings/{api.lid} okunamadi (404) ({adim})")
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
            print(f"::error::ACIL: {adim} sonrasi active -> inactive yapildi (simdi {st2}). DUR.")
            raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: beklenmeyen state {st} ({adim})")
        return L

    lid = D.get("listing_id")
    if not lid:
        drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
        lid = next((x["listing_id"] for x in drafts if x.get("title") == title), None)
    if lid:
        R["olusturma"] = "VAR OLAN TASLAK kullanildi (ikinci ilan acilmadi)"
    else:
        body = {"quantity": 999, "title": title, "description": desc, "price": BOYLAR[0][2], "who_made": "i_did",
                "when_made": "made_to_order", "is_supply": "false", "taxonomy_id": TAXONOMY, "type": "physical",
                "shipping_profile_id": pid, "return_policy_id": iade, "readiness_state_id": READINESS, "shop_section_id": bolum,
                "tags": ",".join(tags), "materials": ",".join(MALZEME), "should_auto_renew": "true",
                "production_partner_ids": str(PARTNER)}
        api._izin("POST", f"/shops/{shop}/listings")
        r_ = requests.post(API + f"/shops/{shop}/listings", data=body, headers=api._headers(), timeout=120)   # TEK deneme
        api.remaining = r_.headers.get("x-remaining-today", api.remaining)
        if r_.status_code not in (200, 201):
            drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
            lid = next((x["listing_id"] for x in drafts if x.get("title") == title), None)
            if lid:
                D["listing_id"] = lid
            kaydet()
            raise SystemExit(f"DUR: createDraftListing {r_.status_code}: {r_.text[:300]} | ayni baslikli taslak: {lid}")
        lid = r_.json().get("listing_id")
        R["olusturma"] = "yeni taslak (tek POST)"
    api.lid = lid
    D["listing_id"] = lid; kaydet()
    print(f"::warning::listing_id {lid}")
    state_oku("1 olusturma")

    # c) envanter
    def urunler():
        return [dict(sku=sku(no, bk), property_values=[dict(property_id=P_STYLE, property_name="Style", values=[ad]),
                                                        dict(property_id=P_SIZE, property_name="Size", values=[bad])],
                     offerings=[dict(price=fiyat, quantity=999, is_enabled=True, readiness_state_id=READINESS)])
                for ad, no, _, _ in STILLER for bad, bk, fiyat in BOYLAR]
    inv = api.get(f"/listings/{lid}/inventory") or {}
    if len(inv.get("products") or []) != 14:
        api.put_json(f"/listings/{lid}/inventory", dict(products=urunler(), price_on_property=[P_SIZE], quantity_on_property=[],
                                                        sku_on_property=[P_STYLE, P_SIZE], readiness_state_on_property=[]))
    state_oku("2 envanter")

    # d) gorseller + video
    have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
    t0 = time.time()
    for rk, p in enumerate(galeri, 1):
        if rk in have:
            continue
        with open(p, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")}, data={"rank": str(rk)})
        g = time.time() - t0
        print(f"gorsel [{rk}/13] {p.name} | gecen {g:.0f} sn | kalan ~{g / rk * (13 - rk):.0f} sn | %{100 * rk // 13}", flush=True)
    state_oku("3 gorseller")
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    if not vids:
        with open(video[0], "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("video.mp4", fh, "video/mp4")},
                          data={"name": f"AstroLoveArt_{PAIR}_mug_video.mp4"})
    state_oku("4 video")

    # e) stil -> kapak
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == P_STYLE and v.get("value_ids")}
    if sorted(vid) != sorted(a for a, *_ in STILLER) or any(rank_id.get(rk) is None for *_, rk in STILLER):
        kaydet(); raise SystemExit(f"DUR: Style value_id {sorted(vid)} / rank {sorted(rank_id)}")
    vi = [dict(property_id=P_STYLE, value_id=vid[ad], image_id=rank_id[rk]) for ad, _, _, rk in STILLER]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
    state_oku("5 stil kapaklari")

    # f) kisisellestirme
    Q = [dict(question_text=SORU_METNI, question_type="text_input", required=True, max_allowed_characters=SORU_MAX,
              instructions=inst)]
    api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": Q})
    state_oku("6 kisisellestirme")

    # g) nitelikler
    for pid_, ad, ids, vals in NITELIK:
        api.put(f"/shops/{shop}/listings/{lid}/properties/{pid_}", {"value_ids": ",".join(str(i) for i in ids),
                                                                     "values": ",".join(vals)})
    state_oku("7 nitelikler")

    # h) geri okuma
    for _ in range(4):                     # gorsel boyutlari islenirken bos gelebilir
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
    tablo = []
    for p in inv.get("products") or []:
        pv = {v.get("property_id"): (v.get("values") or [None])[0] for v in p.get("property_values") or []}
        o = (p.get("offerings") or [{}])[0]
        tablo.append((pv.get(P_STYLE), pv.get(P_SIZE), para(o.get("price")), o.get("quantity"), p.get("sku"),
                      o.get("is_enabled"), o.get("readiness_state_id")))
    bek_tablo = [(ad, bad, fiyat, 999, sku(no, bk), True, READINESS) for ad, no, _, _ in STILLER for bad, bk, fiyat in BOYLAR]
    id_rank = {x.get("listing_image_id"): x.get("rank") for x in ims}
    vid2 = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
            if v.get("property_id") == P_STYLE and v.get("value_ids")}
    bag = {vid2.get(v.get("value_id")): id_rank.get(v.get("image_id")) for v in vis if v.get("property_id") == P_STYLE}
    bek_bag = {ad: rk for ad, _, _, rk in STILLER}
    adlar = [x.get("name") or "" for x in ims]
    K = {
        "baslik CSV ile birebir": L.get("title") == title,
        "aciklama CSV ile birebir": html.unescape(L.get("description") or "").strip() == desc.strip(),
        "13 etiket CSV ile birebir": sorted(L.get("tags") or []) == sorted(tags) and len(L.get("tags") or []) == 13,
        "14 secenek, fiyat, SKU, stok 999": sorted(tablo) == sorted(bek_tablo) and len(tablo) == 14,
        "fiyat yalniz boya gore": inv.get("price_on_property") == [P_SIZE],
        "13 gorsel 1-13 sirada": [x.get("rank") for x in ims] == list(range(1, 14)),
        "video var": len(vids) == 1,
        "7 stil dogru kapak": bag == bek_bag,
        "kisisellestirme zorunlu, 256, talimat": len(per) == 1 and per[0].get("required") is True
        and per[0].get("max_allowed_characters") == SORU_MAX and (per[0].get("instructions") or "") == inst
        and per[0].get("question_type") == "text_input",
        "state draft": L.get("state") == "draft",
        "kargo/iade/bolum/ortak": (L.get("shipping_profile_id"), L.get("return_policy_id"), L.get("shop_section_id"),
                                   sorted(p_.get("production_partner_id") for p_ in L.get("production_partners") or []))
        == (pid, iade, bolum, [PARTNER]),
        "i_did, made_to_order, fiziksel, Ceramic, kategori": (L.get("who_made"), L.get("when_made"), L.get("listing_type") or L.get("type"),
                                                               [m.lower() for m in L.get("materials") or []], L.get("taxonomy_id"))
        == ("i_did", "made_to_order", "physical", [m.lower() for m in MALZEME], TAXONOMY),
        "nitelikler": sorted((p_.get("property_id"), tuple(p_.get("value_ids") or [])) for p_ in props)
        == sorted((a, tuple(b_)) for a, _, b_, _ in NITELIK),
    }
    R["kontrol"] = K
    R["son"] = dict(listing_id=lid, state=L.get("state"), link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    tablo=tablo, bag=bag, gorsel_rank=[x.get("rank") for x in ims], gorsel_boyut=[(x.get("full_width"), x.get("full_height")) for x in ims],
                    video=[(v.get("video_id"), v.get("video_state")) for v in vids],
                    kisisellestirme=per, nitelik=[(p_.get("property_name"), p_.get("values")) for p_ in props],
                    readiness=L.get("readiness_state_id"), islem=(L.get("processing_min"), L.get("processing_max")),
                    is_personalizable=L.get("is_personalizable"), personalization_is_required=L.get("personalization_is_required"),
                    personalization_char_count_max=L.get("personalization_char_count_max"), adlar=adlar,
                    etiketler=L.get("tags"), url=L.get("url"))
    R["kota_son"] = api.remaining
    R["cagri"] = api.calls
    kaydet()
    kotu = [k_ for k_, v_ in K.items() if not v_]
    print(f"::warning::TASLAK {lid} state={L.get('state')} | kontrol {len(K) - len(kotu)}/{len(K)} PASS | FAIL: {kotu} | "
          f"kota {R['kota_bas']} -> {R['kota_son']} | {R['olaylar']}")
    if L.get("state") != "draft":
        raise SystemExit(f"HATA: son state {L.get('state')}")
    if kotu:
        raise SystemExit(f"FAIL kontrol: {kotu}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "yaz"])
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out)
    else:
        try:
            yaz(Kilitli(store), shop, out)
        except BaseException as e:  # noqa: BLE001  hata nedeni rapora ve annotation'a (job loglari okunamiyor)
            f = out / "KUPA_TASLAK.json"
            R = json.load(open(f)) if f.exists() else {}
            R["hata"] = f"{type(e).__name__}: {e}"[:1500]
            json.dump(R, open(f, "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::error::KUPA YAZ HATA {R['hata'][:600]}")
            raise


if __name__ == "__main__":
    main()
