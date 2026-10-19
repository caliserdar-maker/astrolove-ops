#!/usr/bin/env python3
"""KUPA ORCHARD: 78 cift kupa ilani TASLAK (Serdar 19 Eki 2026). YAYIN YOK, Etsy Ads YOK.

--mod oku  : SALT OKUMA (Etsy'ye yazma yok; SaltOkur her yazmayi durdurur). Kategori/nitelik, BY hazirlik ayari,
             iade/ortak/bolum/kargo profilleri, sabit kayitlarin varligi, ayni baslikli taslak, Etsy OAS.
             Cikti: OUT/KUPA_OKU.json + OUT/KUPA_OKU.md
--mod kuru : AG YOK, TOKEN YOK. yaz() ile ayni kod yolu, Etsy bellekte taklit edilir (Kuru istemci); gonderilecek her
             istek (GET dahil) sirasiyla OUT/KURU_<CIFT>.json'a yazilir. Izin listesi (Kilitli._izin) kuruda da uygulanir.
--mod yaz  : ETSY'YE YAZAR (yalniz Serdar'in o adima ozel onayiyla kosulur). Cift basina 1 YENI taslak; yeni kayit
             (bolum/kargo profili/iade) OLUSTURULMAZ, sabit kayitlar yalniz okunup dogrulanir.
             b) createDraftListing (tek POST): CSV basligi/aciklamasi/13 etiket birebir, i_did, made_to_order, fiziksel,
                Ceramic, kategori 1062 Mugs, readiness 1517641240112, bolum 60980873, kargo 318301958420,
                iade 1513990287785, ortak 5817638, fiyat 24.00, stok 999.
             c) envanter: Style (513) x Size (514) = 16 urun (8 Orchard stili x 11/15 oz), fiyat yalniz boya gore
                (11 oz 24.00, 15 oz 29.00), stok 999, price_on_property ve sku_on_property [513, 514],
                SKU KUPA-<CIFT>-<01-08>-<11|15>.  d) 14 gorsel (galeri 01-14 sirasi) + video.
             e) Style -> gorsel (Orange Blossom=01, Purple Fig=08 ... Golden Loquat=14).  f) kisisellestirme: tek kutu,
                zorunlu, 256 karakter, talimat CSV.  g) nitelikler (kategori 1062).  h) geri okuma kontrolleri.
             Her yazmadan sonra state okunur; "active" gorulurse aninda state=inactive + DUR. updateListing (PATCH) YOK
             (CLAUDE.md: taslagi yayina alir); PATCH yalniz acil {"state": "inactive"}. DELETE yok.
             Eski 7 stil taslagi 4597843405 (ESKI_TASLAK) hicbir yazmada hedef olamaz ve "ayni baslikli taslak"
             aramasinda yok sayilir. Ikinci kosu ikinci ilan acmaz (DURUM.json cift -> listing_id + ayni baslikli taslak).
             Cikti: OUT/KUPA_TASLAK_<CIFT>.json + OUT/DURUM.json
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE (oku/yaz), BY_CSV (oku), METIN_CSV
       (KUPA78_ORCHARD_METIN.csv: kod, baslik, etiketler, kisisellestirme_talimati, aciklama), IMG_ROOT
       (<IMG_ROOT>/<CIFT>/galeri/01-14_*.jpg ve <IMG_ROOT>/<CIFT>/video/*.mp4), OUT
Kota tabani 10 (Serdar 15 Eki): x-remaining-today < 10 ise DUR.
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
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402

KOTA_MIN = 10
OAS = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
OAS_OP = ["createDraftListing", "createShopReturnPolicy", "createShopShippingProfile", "createShopShippingProfileDestination",
          "createShopSection", "getShopProductionPartners", "uploadListingVideo", "updateVariationImages",
          "updateListingPersonalization", "updateListingProperty", "updateListingInventory", "uploadListingImage",
          "getListingPersonalization", "getShopReadinessStateDefinitions", "createShopReadinessStateDefinition"]
KUPA_ADLARI = ("mug", "mugs")
BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN",
           "AQUARIUS", "PISCES"]
CIFTLER = sorted("_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2))   # 78, alfabetik anahtar


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


def oku(api, shop, out, PAIR):
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
    R["sabit_kayit"] = dict(ortak=PARTNER in [x["id"] for x in R["uretim_ortaklari"]],
                            bolum=BOLUM_ID in [x["id"] for x in R["bolumler"]],
                            kargo=PROFIL_ID in [x["id"] for x in R["kargo_profilleri"]],
                            iade=[x for x in R["iade_politikalari"] if x["id"] == IADE_ID])
    if os.environ.get("METIN_CSV"):
        row = metin_satiri(PAIR)
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
           f"kargo profilleri: {R['kargo_profilleri']}", f"sabit kayit: {R['sabit_kayit']}", f"ayni baslikli taslak: {R.get('ayni_baslikli_taslak')}",
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
IADE_ID = 1513990287785             # iade yok, degisim yok
BOLUM_ID = 60980873                 # "Zodiac Couple Mugs" (18 Eki kosusunda olustu)
PROFIL_ID = 318301958420            # "Kupa Free US UK EU" (18 Eki kosusunda olustu)
ESKI_TASLAK = {4597843405}          # eski 7 stil CANCER_LIBRA taslagi: bu kod ona YAZMAZ, onu "ayni baslikli taslak" saymaz
P_STYLE, P_SIZE = 513, 514
# (menu adi, stil no, galeri sirasi); galeri dosya adi <sira>_<Ad_Soyad>... (kupa_orchard/kod/cift.py)
STILLER = [("Orange Blossom", "01", 1), ("Purple Fig", "02", 8), ("Olive Breeze", "03", 9), ("Pomegranate Bloom", "04", 10),
           ("Almond Blossom", "05", 11), ("Lemon Grove", "06", 12), ("Blue Grape", "07", 13), ("Golden Loquat", "08", 14)]
ESKI_STILLER = ["Rose Ribbon", "Botanical", "Gold", "Nazar Bond", "Promise Line", "Aegean Tile", "Mediterranean"]
BOYLAR = [("11 oz", "11", 24.00), ("15 oz", "15", 29.00)]
N_URUN = len(STILLER) * len(BOYLAR)
N_GORSEL = 14
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
METIN_SUTUN = ["kod", "baslik", "etiketler", "kisisellestirme_talimati", "aciklama"]
TIRE = re.compile("[–—]")


def sku(pair, no, boy):
    return f"KUPA-{pair}-{no}-{boy}"


def metin_satiri(pair):
    rows = list(csv.DictReader(open(os.environ["METIN_CSV"], encoding="utf-8")))
    eksik = [c for c in METIN_SUTUN if rows and c not in rows[0]]
    if not rows or eksik:
        raise SystemExit(f"DUR: METIN_CSV sutun eksik {eksik} (beklenen {METIN_SUTUN})")
    r = [x for x in rows if x["kod"] == pair]
    if len(r) != 1:
        raise SystemExit(f"DUR: METIN_CSV'de {pair} satiri {len(r)} (1 olmali)")
    return r[0]


def metin_kontrol(row):
    """(title, desc, tags, inst, hata, uyari). hata -> yaz DURUR; uyari yalniz rapora."""
    title, desc = row["baslik"], row["aciklama"]
    tags = [t.strip() for t in row["etiketler"].split(",")]
    inst = row["kisisellestirme_talimati"]
    hata, uyari = [], []
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
    eski = [s for s in ESKI_STILLER if re.search(rf"\b{s}\b", title + "\n" + desc)]
    if eski:
        hata.append(f"eski 7 stil adi metinde {eski}")
    yok = [ad for ad, *_ in STILLER if ad not in desc]
    if yok:
        uyari.append(f"aciklamada gecmeyen Orchard stili {yok}")
    return title, desc, tags, inst, hata, uyari


def medya(pair):
    """<IMG_ROOT>/<CIFT>/galeri/01-14 + <IMG_ROOT>/<CIFT>/video/*.mp4; stil -> gorsel adi kontrolu."""
    kok = Path(os.environ["IMG_ROOT"]) / pair
    galeri = sorted((kok / "galeri").glob("[0-1][0-9]_*.jpg"))
    video = sorted((kok / "video").glob("*.mp4"))
    hata = []
    if [int(p.name[:2]) for p in galeri] != list(range(1, N_GORSEL + 1)):
        hata.append(f"galeri 01-{N_GORSEL} degil: {[p.name for p in galeri]}")
    if len(video) != 1:
        hata.append(f"video 1 degil: {[p.name for p in video]}")
    if not hata:
        for ad, _, rk in STILLER:
            if ad.replace(" ", "_") not in galeri[rk - 1].name:
                hata.append(f"gorsel {rk:02d} ({galeri[rk - 1].name}) {ad} degil")
    return galeri, video, hata


class Kilitli(Etsy):
    """Izinli yazmalar: taslak olusturma ve YALNIZ o taslagin alt uclari. Yeni bolum/profil/iade YOK.
    PATCH yalniz acil {"state": "inactive"}. DELETE yok. ESKI_TASLAK'a yazma yok. Kota < 10 -> DUR."""
    lid = None

    def _izin(self, method, path):
        if any(re.search(rf"/listings/{e}(/|$)", path) for e in ESKI_TASLAK):
            raise SystemExit(f"YASAK yazma (eski taslak): {method} {path}")
        ok = [("POST", r"^/shops/\d+/listings$")]
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

    def taslak_olustur(self, shop, body):
        """createDraftListing: TEK deneme (tekrar ikinci ilan acabilir). (status, json|None, metin)."""
        self._izin("POST", f"/shops/{shop}/listings")
        self.calls += 1
        r_ = requests.post(API + f"/shops/{shop}/listings", data=body, headers=self._headers(), timeout=120)
        self.remaining = r_.headers.get("x-remaining-today", self.remaining)
        self.kota()
        return r_.status_code, (r_.json() if r_.status_code in (200, 201) else None), r_.text[:300]

    def kota(self):
        try:
            if self.remaining is not None and int(self.remaining) < KOTA_MIN:
                raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        except ValueError:
            pass

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")


def yaz(api, shop, out, pair):
    R = {"cift": pair, "olaylar": [], "adimlar": [], "nitelik_bos": NITELIK_BOS}
    durum_f = out / "DURUM.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    D.setdefault("ciftler", {})
    rapor_f = out / f"KUPA_TASLAK_{pair}.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    title, desc, tags, inst, hata, uyari = metin_kontrol(metin_satiri(pair))
    R["metin"] = dict(baslik_kr=len(title), etiket=len(tags), etiket_max=max(len(t) for t in tags), talimat_kr=len(inst),
                      hata=hata, uyari=uyari)
    if hata and not getattr(api, "kuru", False):
        kaydet(); raise SystemExit(f"DUR: metin kontrolu {hata}")
    galeri, video, mhata = medya(pair)
    if mhata:
        kaydet(); raise SystemExit(f"DUR: medya {mhata}")
    R["galeri"] = [p.name for p in galeri] + [video[0].name]

    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    print(f"{pair}: kota basta {api.remaining}")

    # a) sabit kayitlar (yalniz okunur; olusturma yok)
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    prof = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL_ID}", ok404=True) or {}
    rps = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    iade = [x for x in rps if x.get("return_policy_id") == IADE_ID]
    eksik = [ad for ad, ok in (("ortak", PARTNER in [x.get("production_partner_id") for x in pp]),
                               ("bolum", BOLUM_ID in [x.get("shop_section_id") for x in secs]),
                               ("kargo profili", prof.get("shipping_profile_id") == PROFIL_ID),
                               ("iade (iade yok/degisim yok)", bool(iade) and iade[0].get("accepts_returns") is False
                                and iade[0].get("accepts_exchanges") is False)) if not ok]
    if eksik:
        kaydet(); raise SystemExit(f"DUR: sabit kayit yok/uyumsuz {eksik}")
    R["sabit"] = dict(ortak=PARTNER, bolum=BOLUM_ID, kargo=(PROFIL_ID, prof.get("title")), iade=IADE_ID)

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
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            R["adimlar"].append((adim + " ACIL inactive", st2, api.remaining)); kaydet()
            print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive yapildi (simdi {st2}). DUR.")
            raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: beklenmeyen state {st} ({adim})")
        return L

    def ayni_baslik():
        drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
        R["eski_taslak_yok_sayildi"] = [x["listing_id"] for x in drafts if x.get("title") == title and x["listing_id"] in ESKI_TASLAK]
        return next((x["listing_id"] for x in drafts if x.get("title") == title and x["listing_id"] not in ESKI_TASLAK), None)

    lid = D["ciftler"].get(pair)
    if lid in ESKI_TASLAK:
        kaydet(); raise SystemExit(f"DUR: DURUM.json {pair} = eski taslak {lid}")
    lid = lid or ayni_baslik()
    if lid:
        R["olusturma"] = f"VAR OLAN TASLAK {lid} kullanildi (ikinci ilan acilmadi)"
    else:
        body = {"quantity": 999, "title": title, "description": desc, "price": BOYLAR[0][2], "who_made": "i_did",
                "when_made": "made_to_order", "is_supply": "false", "taxonomy_id": TAXONOMY, "type": "physical",
                "shipping_profile_id": PROFIL_ID, "return_policy_id": IADE_ID, "readiness_state_id": READINESS,
                "shop_section_id": BOLUM_ID, "tags": ",".join(tags), "materials": ",".join(MALZEME),
                "should_auto_renew": "true", "production_partner_ids": str(PARTNER)}
        kod, js, metin = api.taslak_olustur(shop, body)
        if kod not in (200, 201):
            lid = ayni_baslik()
            if lid:
                D["ciftler"][pair] = lid
            kaydet()
            raise SystemExit(f"DUR: createDraftListing {kod}: {metin} | ayni baslikli taslak: {lid}")
        lid = js.get("listing_id")
        R["olusturma"] = "yeni taslak (tek POST)"
    api.lid = lid
    D["ciftler"][pair] = lid; kaydet()
    print(f"::warning::{pair} listing_id {lid}")
    state_oku("1 olusturma")

    # c) envanter
    def urunler():
        return [dict(sku=sku(pair, no, bk), property_values=[dict(property_id=P_STYLE, property_name="Style", values=[ad]),
                                                              dict(property_id=P_SIZE, property_name="Size", values=[bad])],
                     offerings=[dict(price=fiyat, quantity=999, is_enabled=True, readiness_state_id=READINESS)])
                for ad, no, _ in STILLER for bad, bk, fiyat in BOYLAR]
    inv = api.get(f"/listings/{lid}/inventory") or {}
    if len(inv.get("products") or []) != N_URUN:
        # Etsy (18 Eki 400): *_on_property ya bos ya iki ozellik; sku iki ozellikte -> fiyat da [513, 514]
        # (fiyatlar yine yalniz boya gore: her stilde 11 oz 24.00, 15 oz 29.00)
        api.put_json(f"/listings/{lid}/inventory", dict(products=urunler(), price_on_property=[P_STYLE, P_SIZE], quantity_on_property=[],
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
        print(f"{pair} gorsel [{rk}/{N_GORSEL}] {p.name} | gecen {g:.0f} sn | kalan ~{g / rk * (N_GORSEL - rk):.0f} sn | "
              f"%{100 * rk // N_GORSEL}", flush=True)
    state_oku("3 gorseller")
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    if not vids:
        with open(video[0], "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("video.mp4", fh, "video/mp4")},
                          data={"name": f"AstroLoveArt_{pair}_mug_video.mp4"})
    state_oku("4 video")

    # e) stil -> gorsel
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == P_STYLE and v.get("value_ids")}
    if sorted(vid) != sorted(a for a, *_ in STILLER) or any(rank_id.get(rk) is None for *_, rk in STILLER):
        kaydet(); raise SystemExit(f"DUR: Style value_id {sorted(vid)} / rank {sorted(rank_id)}")
    vi = [dict(property_id=P_STYLE, value_id=vid[ad], image_id=rank_id[rk]) for ad, _, rk in STILLER]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
    state_oku("5 stil gorselleri")

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
    bek_tablo = [(ad, bad, fiyat, 999, sku(pair, no, bk), True, READINESS) for ad, no, _ in STILLER for bad, bk, fiyat in BOYLAR]
    id_rank = {x.get("listing_image_id"): x.get("rank") for x in ims}
    vid2 = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
            if v.get("property_id") == P_STYLE and v.get("value_ids")}
    bag = {vid2.get(v.get("value_id")): id_rank.get(v.get("image_id")) for v in vis if v.get("property_id") == P_STYLE}
    bek_bag = {ad: rk for ad, _, rk in STILLER}
    K = {
        "baslik CSV ile birebir": L.get("title") == title,
        "aciklama CSV ile birebir": html.unescape(L.get("description") or "").strip() == desc.strip(),
        "13 etiket CSV ile birebir": sorted(L.get("tags") or []) == sorted(tags) and len(L.get("tags") or []) == 13,
        f"{N_URUN} secenek, fiyat, SKU, stok 999": sorted(tablo) == sorted(bek_tablo) and len(tablo) == N_URUN,
        "fiyat yalniz boya gore": all(f == dict((b_, f_) for b_, _, f_ in BOYLAR)[bo] for _, bo, f, *_ in tablo),
        f"{N_GORSEL} gorsel 1-{N_GORSEL} sirada": [x.get("rank") for x in ims] == list(range(1, N_GORSEL + 1)),
        "video var": len(vids) == 1,
        f"{len(STILLER)} stil dogru gorsel": bag == bek_bag,
        "kisisellestirme zorunlu, 256, talimat": len(per) == 1 and per[0].get("required") is True
        and per[0].get("max_allowed_characters") == SORU_MAX and (per[0].get("instructions") or "") == inst
        and per[0].get("question_type") == "text_input",
        "state draft": L.get("state") == "draft",
        "kargo/iade/bolum/ortak": (L.get("shipping_profile_id"), L.get("return_policy_id"), L.get("shop_section_id"),
                                   sorted(p_.get("production_partner_id") for p_ in L.get("production_partners") or []))
        == (PROFIL_ID, IADE_ID, BOLUM_ID, [PARTNER]),
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
                    readiness=L.get("readiness_state_id"), etiketler=L.get("tags"), url=L.get("url"))
    R["kota_son"] = api.remaining
    R["cagri"] = api.calls
    kaydet()
    kotu = [k_ for k_, v_ in K.items() if not v_]
    print(f"::warning::{pair} TASLAK {lid} state={L.get('state')} | kontrol {len(K) - len(kotu)}/{len(K)} PASS | FAIL: {kotu} | "
          f"kota {R['kota_bas']} -> {R['kota_son']} | metin hata {hata} uyari {uyari}")
    if L.get("state") != "draft":
        raise SystemExit(f"HATA: {pair} son state {L.get('state')}")
    if kotu:
        raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    return R


# ------------------------------------------------------------------ kuru
class Kuru(Kilitli):
    """AG YOK. Etsy bellekte taklit edilir; yaz() kodu degismeden kosar. Her istek (GET dahil) self.kayit'a duser.
    Kilitli._izin ve PATCH kurali aynen uygulanir (izin disi yazma kuruda da DURDURUR)."""
    kuru = True

    def __init__(self, shop, eski_baslik=None):          # Etsy.__init__ cagrilmaz: token/ag yok
        self.shop, self.calls, self.remaining, self.lid = str(shop), 0, "KURU", None
        self.kayit, self.eski_baslik = [], eski_baslik
        self.L, self.inv, self.ims, self.vids, self.vis, self.per, self.props = None, None, [], [], [], [], {}

    def _kaydet(self, method, path, params=None, data=None, json_body=None, files=None):
        k = dict(no=len(self.kayit) + 1, method=method, url=API + path, yazma=method != "GET")
        if params:
            k["params"] = params
        if data is not None:
            k["form"] = data
        if json_body is not None:
            k["json"] = json_body
        if files:
            k["dosya"] = {a: dict(ad=f[0], mime=f[2], bayt=os.fstat(f[1].fileno()).st_size) for a, f in files.items()}
        self.kayit.append(k)
        self.calls += 1

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and data != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        self._kaydet(method, path, params, data, json_body)
        return self._sim(method, path, params, data, ok404, json_body)

    def post_file(self, path, files, data=None):
        self._izin("POST", path)
        self._kaydet("POST", path, data=data, files=files)
        if path.endswith("/images"):
            rk = int(data["rank"])
            self.ims.append(dict(rank=rk, listing_image_id=800000 + rk, full_width=2048, full_height=2048, name=files["image"][0]))
            return self.ims[-1]
        self.vids.append(dict(video_id=900001, video_state="active"))
        return self.vids[-1]

    def taslak_olustur(self, shop, body):
        self._izin("POST", f"/shops/{shop}/listings")
        self._kaydet("POST", f"/shops/{shop}/listings", data=body)
        lid = 9000000001                   # KURU sahte listing_id
        self.L = dict(listing_id=lid, state="draft", title=body["title"], description=body["description"],
                      tags=body["tags"].split(","), who_made=body["who_made"], when_made=body["when_made"],
                      listing_type=body["type"], materials=body["materials"].split(","), taxonomy_id=body["taxonomy_id"],
                      shipping_profile_id=body["shipping_profile_id"], return_policy_id=body["return_policy_id"],
                      shop_section_id=body["shop_section_id"], readiness_state_id=body["readiness_state_id"],
                      production_partners=[dict(production_partner_id=int(body["production_partner_ids"]))])
        return 201, dict(listing_id=lid), ""

    def _sim(self, method, path, params, data, ok404, js):
        s, lid = self.shop, self.lid
        if method == "GET":
            sabit = {f"/shops/{s}": {}, f"/shops/{s}/production-partners": dict(results=[dict(production_partner_id=PARTNER)]),
                     f"/shops/{s}/sections": dict(results=[dict(shop_section_id=BOLUM_ID, title="Zodiac Couple Mugs")]),
                     f"/shops/{s}/shipping-profiles/{PROFIL_ID}": dict(shipping_profile_id=PROFIL_ID, title="Kupa Free US UK EU"),
                     f"/shops/{s}/policies/return": dict(results=[dict(return_policy_id=IADE_ID, accepts_returns=False,
                                                                       accepts_exchanges=False)]),
                     # eski taslak ayni baslikla duruyormus gibi: yok sayilmali (ESKI_TASLAK)
                     f"/shops/{s}/listings": dict(results=[dict(listing_id=e, title=self.eski_baslik) for e in ESKI_TASLAK])}
            if path in sabit:
                return sabit[path]
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
            stil = {}
            urun = []
            for p in js["products"]:
                pv = []
                for v in p["property_values"]:
                    vid = stil.setdefault(v["values"][0], 5000 + len(stil)) if v["property_id"] == P_STYLE else 6000
                    pv.append(dict(v, value_ids=[vid]))
                o = p["offerings"][0]
                urun.append(dict(sku=p["sku"], property_values=pv,
                                 offerings=[dict(o, price=dict(amount=round(o["price"] * 100), divisor=100))]))
            self.inv = dict(products=urun)
            return self.inv
        if path.endswith("/variation-images"):
            self.vis = js["variation_images"]
            return dict(results=self.vis)
        if path.endswith("/personalization"):
            self.per = js["personalization_questions"]
            return js
        if "/properties/" in path:
            pid_ = int(path.rsplit("/", 1)[1])
            self.props[pid_] = dict(property_id=pid_, value_ids=[int(x) for x in data["value_ids"].split(",")],
                                    values=data["values"].split(","))
            return self.props[pid_]
        if method == "PATCH":
            self.L["state"] = data["state"]
            return self.L
        raise SystemExit(f"KURU: taklit edilmeyen {method} {path}")


def kuru(shop, out, pair):
    row = metin_satiri(pair)
    api = Kuru(shop, eski_baslik=row["baslik"])
    out = out / "kuru"                     # gercek DURUM.json'a dokunmaz; kuru her zaman yeni taslak yolunu gosterir
    out.mkdir(parents=True, exist_ok=True)
    durum_f = out / "DURUM.json"
    if durum_f.exists():
        durum_f.unlink()
    R = yaz(api, shop, out, pair)
    durum_f.unlink()
    yazma = [k for k in api.kayit if k["yazma"]]
    ozet = dict(cift=pair, istek=len(api.kayit), yazma=len(yazma),
                yazma_dagilim={u: sum(1 for k in yazma if re.sub(r"\d{6,}", "{id}", k["url"].replace(API, "")) == u)
                               for u in sorted({re.sub(r"\d{6,}", "{id}", k["url"].replace(API, "")) for k in yazma})},
                kontrol=R["kontrol"], metin=R["metin"], eski_taslak_yok_sayildi=R.get("eski_taslak_yok_sayildi"),
                not_="KURU: ag/token yok; listing_id 9000000001, gorsel id 8000NN, value_id 50NN sahtedir.")
    json.dump(dict(ozet=ozet, istekler=api.kayit), open(out / f"KURU_{pair}.json", "w"), indent=1, ensure_ascii=False)
    (out / f"KUPA_TASLAK_{pair}.json").unlink()
    print(f"KURU {pair}: {len(api.kayit)} istek ({len(yazma)} yazma) | kontrol {sum(R['kontrol'].values())}/{len(R['kontrol'])} | "
          f"metin hata {R['metin']['hata']} | uyari {R['metin']['uyari']} -> {out / f'KURU_{pair}.json'}")
    return ozet


def cift_listesi(girdi):
    secim = CIFTLER if girdi.strip().upper() == "TUMU" else [c.strip().upper() for c in re.split(r"[,\s]+", girdi) if c.strip()]
    bilinmeyen = [c for c in secim if c not in CIFTLER]
    if bilinmeyen or not secim:
        raise SystemExit(f"DUR: bilinmeyen cift {bilinmeyen} (anahtar alfabetik: CANCER_LIBRA)")
    return secim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "kuru", "yaz"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA", help="TUMU ya da virgul/bosluk ayrimli CIFT listesi")
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
        oku(SaltOkur(store), shop, out, ciftler[0])
        return
    api = Kilitli(store)
    t0 = time.time()
    for i, c in enumerate(ciftler, 1):
        api.lid = None
        try:
            yaz(api, shop, out, c)
        except BaseException as e:  # noqa: BLE001  hata nedeni rapora ve annotation'a (job loglari okunamiyor)
            f = out / f"KUPA_TASLAK_{c}.json"
            R = json.load(open(f)) if f.exists() else {}
            R["hata"] = f"{type(e).__name__}: {e}"[:1500]
            json.dump(R, open(f, "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::error::KUPA YAZ HATA {c} {R['hata'][:600]}")
            raise
        g = time.time() - t0
        print(f"ETA cift [{i}/{len(ciftler)}] {c} | gecen {g / 60:.1f} dk | kalan ~{g / i * (len(ciftler) - i) / 60:.1f} dk | "
              f"%{100 * i // len(ciftler)} | kota {api.remaining}", flush=True)


if __name__ == "__main__":
    main()
