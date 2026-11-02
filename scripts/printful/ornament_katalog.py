#!/usr/bin/env python3
"""Printful ornament katalog SALT OKUMA (Serdar 2 Kas 2026).
Yalniz GET + kargo ucreti sorgusu (POST /shipping/rates, POST /v2/shipping-rates). Siparis, urun, sablon, mockup gorevi
OLUSTURULMAZ: izinli POST yollari POST_IZIN'de, disindaki her POST betigi durdurur. Etsy'ye dokunmaz.

Kullanim:
  ornament_katalog.py oku <ham_klasor>      env PRINTFUL_TOKEN. Ham API yanitlari (token yazilmaz; istek basliklari kaydedilmez).
  ornament_katalog.py rapor <cikti_klasor>  API yok; <cikti>/ham'dan okur. PRINTFUL_ORNAMENT.csv, PRINTFUL_ORNAMENT_KARGO.csv,
                                            PRINTFUL_ORNAMENT.md yazar. API'nin vermedigi alan: "API vermedi".
Aday urun: v1 /products ve v2 /v2/catalog-products listesinde title/type_name/model/name/description alaninda "ornament"
gecen, adi "ornament" gecen kategorideki ve gorevde adi gecen (881, 900, 634) urunler. Kargo: aciklama disi eslesen her
urunun her varyanti x ULKELER, 1 adet, USD (v1: secenek + ucret + gun; v2: cikis ulkesi / gumruk)."""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.printful.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops"
POST_IZIN = {"/shipping/rates", "/v2/shipping-rates"}
ULKELER = os.environ.get("ULKELER", "US CA GB DE FR IT ES NL AU").split()
ZORUNLU = [881, 900, 634]
ANAHTAR = re.compile(r"ornament", re.I)
ADRES = {"US": {"state_code": "NY", "city": "New York", "zip": "10001"},
         "CA": {"state_code": "ON", "city": "Toronto", "zip": "M5V 2T6"},
         "GB": {"city": "London", "zip": "SW1A 1AA"}, "DE": {"city": "Berlin", "zip": "10115"},
         "FR": {"city": "Paris", "zip": "75001"}, "IT": {"city": "Rome", "zip": "00184"},
         "ES": {"city": "Madrid", "zip": "28001"}, "NL": {"city": "Amsterdam", "zip": "1012 JS"},
         "AU": {"state_code": "NSW", "city": "Sydney", "zip": "2000"}}
YOK = "API vermedi"
ISTEKLER = []


# ----------------------------------------------------------------------------------------------------------- oku
def istek(yol, token, veri=None):
    yontem = "POST" if veri is not None else "GET"
    if yontem == "POST" and yol.split("?")[0] not in POST_IZIN:
        raise SystemExit(f"DUR: izinsiz POST {yol}")
    kod, j = 0, {}
    for deneme in range(6):
        req = urllib.request.Request(API + yol, data=json.dumps(veri).encode() if veri is not None else None,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                              "User-Agent": UA, "Accept": "application/json"}, method=yontem)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                kod, j = r.status, json.load(r)
        except urllib.error.HTTPError as e:
            govde = e.read().decode(errors="replace")[:5000]
            if e.code in (429, 500, 502, 503, 504) and deneme < 5:
                try:
                    bekle = int(e.headers.get("Retry-After") or 0)
                except ValueError:
                    bekle = 0
                bekle = min(max(bekle, 15 * (deneme + 1)), 90)
                print(f"  {yontem} {yol} HTTP {e.code}, {bekle}s bekleniyor", flush=True)
                time.sleep(bekle)
                continue
            kod = e.code
            try:
                j = json.loads(govde)
            except ValueError:
                j = {"ham": govde}
        except (urllib.error.URLError, TimeoutError) as e:
            if deneme < 5:
                time.sleep(10)
                continue
            kod, j = 0, {"hata": type(e).__name__}
        break
    ISTEKLER.append({"yontem": yontem, "yol": yol, "http": kod, "zaman": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    time.sleep(0.35)
    return kod, j


def sar(yontem, yol, govde, kod, j):
    return {"istek": {"yontem": yontem, "yol": yol, "govde": govde}, "http": kod, "yanit": j}


def yaz(p, veri):
    p.write_text(json.dumps(veri, indent=1, ensure_ascii=False), encoding="utf-8")


def oku(ham):
    token = os.environ["PRINTFUL_TOKEN"].strip()
    ham.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    k, v1list = istek("/products", token)
    yaz(ham / "v1_products.json", sar("GET", "/products", None, k, v1list))
    print(f"GET /products -> {k}", flush=True)
    k, kat = istek("/categories", token)
    yaz(ham / "v1_categories.json", sar("GET", "/categories", None, k, kat))
    print(f"GET /categories -> {k}", flush=True)
    sayfalar, off = [], 0
    while off < 5000:
        yol = f"/v2/catalog-products?limit=100&offset={off}"
        k, j = istek(yol, token)
        sayfalar.append(sar("GET", yol, None, k, j))
        data = (j.get("data") if isinstance(j, dict) else None) or []
        if k != 200 or not data:
            break
        off += len(data)
        top = ((j.get("paging") or {}).get("total")) if isinstance(j, dict) else None
        if top is None or off >= int(top):
            break
    yaz(ham / "v2_catalog_products.json", {"sayfalar": sayfalar})
    print(f"GET /v2/catalog-products: {len(sayfalar)} sayfa, {off} urun", flush=True)

    aday = adaylar(ham)
    yaz(ham / "_adaylar.json", aday)
    print("ADAY " + json.dumps({k_: v["neden"] for k_, v in aday.items()}, ensure_ascii=False), flush=True)

    for i, pid in enumerate(sorted(aday, key=int), 1):
        for ad, yol in (("v1", f"/products/{pid}"), ("v1_sizes", f"/products/{pid}/sizes?unit=inches,cm"),
                        ("printfiles", f"/mockup-generator/printfiles/{pid}"), ("v2", f"/v2/catalog-products/{pid}"),
                        ("v2_variants", f"/v2/catalog-products/{pid}/catalog-variants?limit=100"),
                        ("v2_prices_USD", f"/v2/catalog-products/{pid}/prices?currency=USD"),
                        ("v2_prices_EUR", f"/v2/catalog-products/{pid}/prices?currency=EUR"),
                        ("v2_availability", f"/v2/catalog-products/{pid}/availability?limit=100"),
                        ("v2_sizes", f"/v2/catalog-products/{pid}/sizes"),
                        ("v2_mockup_templates", f"/v2/catalog-products/{pid}/mockup-templates?limit=100")):
            k, j = istek(yol, token)
            yaz(ham / f"urun_{pid}_{ad}.json", sar("GET", yol, None, k, j))
        print(f"[urun {i}/{len(aday)}] {pid} detay okundu | gecen {int(time.time() - t0)}s", flush=True)

    # kargo plani: aciklama-disi eslesen urunlerin tum varyantlari
    plan = []
    for pid in sorted(aday, key=int):
        if not aday[pid]["kargo"]:
            continue
        v1 = json.loads((ham / f"urun_{pid}_v1.json").read_text(encoding="utf-8"))
        for v in ((v1.get("yanit") or {}).get("result") or {}).get("variants") or []:
            for ulke in ULKELER:
                plan.append((pid, v.get("id"), ulke))
    print(f"KARGO plani: {len(plan)} varyant x ulke (x2: v1 + v2)", flush=True)
    k1, k2, t1 = [], [], time.time()
    for n, (pid, vid, ulke) in enumerate(plan, 1):
        g1 = {"recipient": {"country_code": ulke, **ADRES.get(ulke, {})},
              "items": [{"variant_id": vid, "quantity": 1}], "currency": "USD"}
        k, j = istek("/shipping/rates", token, g1)
        k1.append({"urun": pid, "varyant": vid, "ulke": ulke, **sar("POST", "/shipping/rates", g1, k, j)})
        g2 = {"recipient": {"country_code": ulke, **ADRES.get(ulke, {})},
              "order_items": [{"source": "catalog", "catalog_variant_id": vid, "quantity": 1}], "currency": "USD"}
        k_, j_ = istek("/v2/shipping-rates", token, g2)
        k2.append({"urun": pid, "varyant": vid, "ulke": ulke, **sar("POST", "/v2/shipping-rates", g2, k_, j_)})
        if n % 9 == 0 or n == len(plan):
            g = time.time() - t1
            print(f"[kargo {n}/{len(plan)} %{100 * n // len(plan)}] gecen {int(g)}s kalan ~{int(g * (len(plan) - n) / n)}s "
                  f"| son: {pid}/{vid}/{ulke} v1 {k} v2 {k_}", flush=True)
    yaz(ham / "kargo_v1.json", k1)
    yaz(ham / "kargo_v2.json", k2)
    yaz(ham / "_istekler.json", ISTEKLER)
    post = [x for x in ISTEKLER if x["yontem"] == "POST"]
    print(f"ISTEK toplam {len(ISTEKLER)} | GET {len(ISTEKLER) - len(post)} | POST {len(post)} "
          f"(yollar: {sorted({x['yol'] for x in post})}) | sure {int(time.time() - t0)}s", flush=True)
    return 0 if (ham / "v1_products.json").exists() else 1


def adaylar(ham):
    def oku_j(ad):
        p = ham / ad
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    v1 = ((oku_j("v1_products.json").get("yanit") or {}).get("result")) or []
    kat = (((oku_j("v1_categories.json").get("yanit") or {}).get("result")) or {}).get("categories") or []
    katid = {c.get("id") for c in kat if ANAHTAR.search(str(c.get("title") or ""))}
    v2 = [p for s in oku_j("v2_catalog_products.json").get("sayfalar") or [] for p in ((s.get("yanit") or {}).get("data") or [])]
    a = {}

    def ekle(pid, neden):
        a.setdefault(str(pid), {"neden": [], "kargo": False})
        if neden not in a[str(pid)]["neden"]:
            a[str(pid)]["neden"].append(neden)
        if not neden.endswith("description"):
            a[str(pid)]["kargo"] = True
    for kaynak, liste, alanlar in (("v1", v1, ("title", "type_name", "model", "type", "description")),
                                   ("v2", v2, ("name", "type", "model", "description"))):
        for p in liste:
            for al in alanlar:
                if ANAHTAR.search(str(p.get(al) or "")):
                    ekle(p.get("id"), f"{kaynak}.{al}")
            if p.get("main_category_id") in katid:
                ekle(p.get("id"), f"{kaynak}.kategori")
    for z in ZORUNLU:
        ekle(z, "gorev_listesi")
    return a


# --------------------------------------------------------------------------------------------------------- rapor
def jy(ham, ad):
    p = ham / ad
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def yanit(w):
    return (w or {}).get("yanit") or {}


def http(w):
    return (w or {}).get("http")


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def inch_olcu(s):
    """Varyant size metnindeki inch degerleri (ornek 3"x3", 2.75″). cm = inch x 2.54 (hesap)."""
    s = str(s or "")
    sayi = re.findall(r"(\d+(?:\.\d+)?)\s*(?:\"|″|”|''|in\b|inch)", s)
    if not sayi:
        sayi = re.findall(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", s)
        sayi = [x for t in sayi for x in t]
    return [float(x) for x in sayi]


def anahtar_bul(d, kelime, yol=""):
    b = {}
    if isinstance(d, dict):
        for k, v in d.items():
            y = f"{yol}.{k}" if yol else k
            if kelime in k.lower():
                b[y] = v
            b.update(anahtar_bul(v, kelime, y))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            b.update(anahtar_bul(v, kelime, f"{yol}[{i}]"))
    return b


def en_ucuz(secenekler):
    s = [x for x in secenekler or [] if isinstance(x, dict) and fl(x.get("rate")) is not None]
    return min(s, key=lambda x: fl(x["rate"])) if s else None


def urun_veri(ham, pid):
    U = {ad: jy(ham, f"urun_{pid}_{ad}.json") for ad in ("v1", "v1_sizes", "printfiles", "v2", "v2_variants", "v2_prices_USD",
                                                         "v2_prices_EUR", "v2_availability", "v2_sizes", "v2_mockup_templates")}
    r1 = yanit(U["v1"]).get("result") or {}
    U["p"] = r1.get("product") or {}
    U["vs"] = r1.get("variants") or []
    U["p2"] = yanit(U["v2"]).get("data") or {}
    pf = yanit(U["printfiles"]).get("result") or {}
    U["pf_id"] = {x.get("printfile_id"): x for x in pf.get("printfiles") or []}
    U["pf_var"] = {x.get("variant_id"): x.get("placements") or {} for x in pf.get("variant_printfiles") or []}
    U["pf_yer"] = pf.get("available_placements") or {}
    # v2 fiyat: variants[].techniques[].price ; urun placements[].price
    U["fiyat2"] = {}
    U["yer_fiyat2"] = {}
    for cur in ("USD", "EUR"):
        d = yanit(U[f"v2_prices_{cur}"]).get("data") or {}
        for v in d.get("variants") or []:
            for t in v.get("techniques") or []:
                U["fiyat2"].setdefault((v.get("id"), cur), []).append((t.get("technique_key") or t.get("technique_display_name"),
                                                                     t.get("price"), t.get("discounted_price")))
        for pl in (d.get("product") or {}).get("placements") or []:
            U["yer_fiyat2"].setdefault(cur, []).append(pl)
        U[f"para2_{cur}"] = d.get("currency")
    U["uyg2"] = {}
    for v in yanit(U["v2_availability"]).get("data") or []:
        for t in v.get("techniques") or []:
            for sr in t.get("selling_regions") or []:
                U["uyg2"].setdefault(v.get("catalog_variant_id"), {})[f"{sr.get('name')}"] = sr.get("availability")
    return U


def bolgeler_v1(v):
    durum = v.get("availability_status") or []
    tum = [f"{x.get('region')}:{x.get('status')}" for x in durum]
    sat = sorted({x.get("region") for x in durum if x.get("status") in ("in_stock", "stocked_on_demand")})
    return tum, sat


def yuz_bilgi(U):
    yer = list(U["pf_yer"].keys()) or [p.get("placement") for p in U["p2"].get("placements") or []]
    yer = [y for y in yer if y]
    ek = [f"{f.get('id') or f.get('type')}:{f.get('additional_price')}" for f in U["p"].get("files") or []
          if f.get("type") not in ("preview", "mockup")]
    if not yer:
        return YOK, ek
    arka = [y for y in yer if re.search(r"back|second|side_?2|reverse", y, re.I)]
    return (f"cift yuz secenegi ({', '.join(yer)})" if arka else f"tek yuz ({', '.join(yer)})"), ek


def aciklama_satir(metin, desen):
    parca = [s.strip(" •-*\t") for s in re.split(r"[\n\r]+|•", metin or "") if s.strip()]
    return [s for s in parca if re.search(desen, s, re.I)]


MALZEME = r"ceramic|porcelain|wood|birch|maple|mdf|plywood|glass|acrylic|alumin|metal|steel|brass|plastic|gloss|matte|finish|thick|mm\b"
PAKET = r"ribbon|string|cord|twine|loop|hook|hang|box|packag|gift|bag|wrap"
BASKI = r"sublimat|uv\b|print|dtg|engrav|laser|dye|side|sided|bleed"


def rapor(cikti):
    ham = cikti / "ham"
    aday = jy(ham, "_adaylar.json") or {}
    k1 = jy(ham, "kargo_v1.json") or []
    k2 = jy(ham, "kargo_v2.json") or []
    K1 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in k1}
    K2 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in k2}
    satirlar, kargo_satir, urunler = [], [], []
    for pid in sorted(aday, key=int):
        U = urun_veri(ham, pid)
        p, vs = U["p"], U["vs"]
        yuz, ek = yuz_bilgi(U)
        ac = p.get("description") or U["p2"].get("description") or ""
        tasma = aciklama_satir(ac, r"bleed")
        tek = [t.get("display_name") or t.get("key") for t in p.get("techniques") or []]
        tek2 = [t.get("display_name") or t.get("key") for t in U["p2"].get("techniques") or []]
        uru = {"id": pid, "ad": p.get("title") or U["p2"].get("name") or YOK, "neden": aday[pid]["neden"],
               "http_v1": http(U["v1"]), "http_v2": http(U["v2"]), "tur": p.get("type_name") or YOK,
               "model": p.get("model") or YOK, "marka": p.get("brand") or YOK, "durdu": p.get("is_discontinued"),
               "yuz": yuz, "ek_yer": ek, "teknik": tek or tek2 or [YOK], "aciklama": ac, "tasma": tasma,
               "ort_sure": p.get("avg_fulfillment_time"), "origin": p.get("origin_country"), "olcu_tablo": [],
               "varyant": [], "kargo": {}, "cikis": {}, "U": U, "kargo_var": aday[pid]["kargo"]}
        for ad in ("v1_sizes", "v2_sizes"):
            r = yanit(U[ad]).get("result") or yanit(U[ad]).get("data") or {}
            tabs = r.get("size_tables") if isinstance(r, dict) else [t for x in r for t in (x.get("size_tables") or [])]
            for t in tabs or []:
                for m in t.get("measurements") or []:
                    deg = "; ".join(f"{x.get('size')}: {x.get('value') if x.get('value') is not None else str(x.get('min_value')) + '-' + str(x.get('max_value'))}"
                                    for x in m.get("values") or [])
                    uru["olcu_tablo"].append(f"{ad} {t.get('type')} | {m.get('type_label')} ({m.get('unit') or t.get('unit')}): {deg}")
        for v in vs:
            vid = v.get("id")
            tum, sat = bolgeler_v1(v)
            yer = U["pf_var"].get(vid) or {}
            pf = [(y, U["pf_id"].get(i) or {}) for y, i in yer.items()]
            inch = inch_olcu(v.get("size"))
            f2u = U["fiyat2"].get((vid, "USD"))
            f2e = U["fiyat2"].get((vid, "EUR"))
            sat_ = {
                "urun_id": pid, "urun_adi": uru["ad"], "urun_turu": uru["tur"], "model": uru["model"],
                "eslesme": "|".join(uru["neden"]), "urun_durdu": p.get("is_discontinued", YOK),
                "varyant_id": vid, "varyant_adi": v.get("name") or YOK, "boyut_api": v.get("size") or YOK,
                "renk_api": v.get("color") or YOK,
                "olcu_inch": " x ".join(f"{x:g}" for x in inch) if inch else YOK,
                "olcu_cm_hesap": " x ".join(f"{x * 2.54:.2f}" for x in inch) if inch else YOK,
                "yuz": yuz, "ek_baski_ucreti_v1": "; ".join(ek) or YOK, "teknik": "; ".join(uru["teknik"]),
                "malzeme_api": json.dumps(v.get("material"), ensure_ascii=False) if v.get("material") else YOK,
                "aciklama_malzeme": " / ".join(aciklama_satir(ac, MALZEME)) or YOK,
                "aciklama_paket": " / ".join(aciklama_satir(ac, PAKET)) or YOK,
                "fiyat_usd_v1": v.get("price") if v.get("price") is not None else YOK,
                "fiyat_usd_v2": "; ".join(f"{t}:{pr}" for t, pr, _ in f2u) if f2u else YOK,
                "fiyat_eur_v2": "; ".join(f"{t}:{pr}" for t, pr, _ in f2e) if f2e else YOK,
                "stok_v1": v.get("in_stock", YOK), "bolge_durum_v1": "; ".join(tum) or YOK,
                "satilabilir_bolgeler_v1": ", ".join(sat) or YOK,
                "yalniz_abd": "EVET" if sat == ["US"] else ("hayir" if sat else YOK),
                "bolge_durum_v2": "; ".join(f"{a}:{b}" for a, b in sorted((U["uyg2"].get(vid) or {}).items())) or YOK,
                "printfile_id": "; ".join(f"{y}={x.get('printfile_id')}" for y, x in pf) or YOK,
                "printfile_px": "; ".join(f"{y}={x.get('width')}x{x.get('height')}" for y, x in pf) or YOK,
                "printfile_dpi": "; ".join(f"{y}={x.get('dpi')}" for y, x in pf) or YOK,
                "fill_mode": "; ".join(f"{y}={x.get('fill_mode')}" for y, x in pf) or YOK,
                "can_rotate": "; ".join(f"{y}={x.get('can_rotate')}" for y, x in pf) or YOK,
                "tasma_payi": " / ".join(tasma) or YOK,
                "ort_uretim_suresi_v1": p.get("avg_fulfillment_time") if p.get("avg_fulfillment_time") is not None else YOK,
                "origin_country_v1": p.get("origin_country") or YOK,
            }
            cikis = []
            for ulke in ULKELER:
                x1, x2 = K1.get((pid, vid, ulke)), K2.get((pid, vid, ulke))
                if x1 is None:
                    sat_[f"kargo_{ulke}_usd"] = "sorgulanmadi" if not uru["kargo_var"] else YOK
                    continue
                s1 = yanit(x1).get("result") if isinstance(yanit(x1).get("result"), list) else []
                s2 = yanit(x2).get("data") if isinstance(yanit(x2).get("data"), list) else []
                e = en_ucuz(s1)
                m2 = None
                if e:
                    m2 = next((y for y in s2 if y.get("shipping") == e.get("id")), None)
                m2 = m2 or en_ucuz(s2)
                dep = sorted({sh.get("departure_country") for sh in (m2 or {}).get("shipments") or [] if sh.get("departure_country")})
                gum = sorted({str(sh.get("customs_fees_possible")) for sh in (m2 or {}).get("shipments") or []
                              if "customs_fees_possible" in sh})
                takip = anahtar_bul(e, "track") if e else {}
                takip.update(anahtar_bul(m2, "track") if m2 else {})
                sat_[f"kargo_{ulke}_usd"] = e.get("rate") if e else f"HATA HTTP {http(x1)}"
                cikis += dep
                uru["cikis"].setdefault(ulke, set()).update(dep)
                kargo_satir.append({
                    "urun_id": pid, "urun_adi": uru["ad"], "varyant_id": vid, "varyant_adi": v.get("name"), "ulke": ulke,
                    "adres": ", ".join(f"{a}={b}" for a, b in ADRES.get(ulke, {}).items()), "http_v1": http(x1),
                    "yontem_id": e.get("id") if e else YOK, "yontem_adi": e.get("name") if e else YOK,
                    "ucret": e.get("rate") if e else YOK, "para": e.get("currency") if e else YOK,
                    "min_gun": e.get("minDeliveryDays") if e and e.get("minDeliveryDays") is not None else YOK,
                    "max_gun": e.get("maxDeliveryDays") if e and e.get("maxDeliveryDays") is not None else YOK,
                    "tum_secenekler_v1": "; ".join(f"{y.get('id')}={y.get('rate')} {y.get('currency')}" for y in s1) or YOK,
                    "http_v2": http(x2), "yontem_v2": (m2 or {}).get("shipping_method_name") or (m2 or {}).get("shipping") or YOK,
                    "ucret_v2": (m2 or {}).get("rate") if m2 else YOK,
                    "cikis_ulkesi_v2": ", ".join(dep) or YOK, "gumruk_olasi_v2": ", ".join(gum) or YOK,
                    "takip_api": json.dumps(takip, ensure_ascii=False) if takip else YOK,
                    "hata_v1": "" if http(x1) == 200 else json.dumps(yanit(x1), ensure_ascii=False)[:300],
                    "hata_v2": "" if http(x2) == 200 else json.dumps(yanit(x2), ensure_ascii=False)[:300]})
            sat_["cikis_ulkesi_v2"] = ", ".join(sorted(set(cikis))) or (YOK if uru["kargo_var"] else "sorgulanmadi")
            satirlar.append(sat_)
            uru["varyant"].append(sat_)
        urunler.append(uru)

    alanlar = list(satirlar[0].keys()) if satirlar else ["urun_id"]
    with open(cikti / "PRINTFUL_ORNAMENT.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)
    ka = list(kargo_satir[0].keys()) if kargo_satir else ["urun_id"]
    with open(cikti / "PRINTFUL_ORNAMENT_KARGO.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ka)
        w.writeheader()
        w.writerows(kargo_satir)
    (cikti / "PRINTFUL_ORNAMENT.md").write_text(md(urunler, kargo_satir, ham), encoding="utf-8")
    print(f"RAPOR urun {len(urunler)} | varyant satiri {len(satirlar)} | kargo satiri {len(kargo_satir)}", flush=True)
    return 0 if satirlar else 1


def aralik(deg):
    s = sorted({x for x in deg if fl(x) is not None}, key=fl)
    if not s:
        return YOK
    return s[0] if len(s) == 1 else f"{s[0]}-{s[-1]}"


def kargo_hucre(ks):
    """urun x ulke: varyantlar arasi en ucuz yontem ucreti (aralik), yontem adi ve gun."""
    ok = [k for k in ks if fl(k["ucret"]) is not None]
    if not ok:
        return "HATA " + ",".join(sorted({str(k["http_v1"]) for k in ks})) if ks else "sorgulanmadi"
    a = aralik([k["ucret"] for k in ok])
    yon = sorted({str(k["yontem_id"]) for k in ok})
    gun = sorted({f"{k['min_gun']}-{k['max_gun']}" for k in ok})
    return f"{a} ({'/'.join(yon)}, {'/'.join(gun)} g)"


def md(urunler, kargo, ham):
    ist = jy(ham, "_istekler.json") or []
    post = sorted({x["yol"] for x in ist if x["yontem"] == "POST"})
    zaman = max((x["zaman"] for x in ist), default=YOK)
    L = ["# Printful ornament urunleri (salt okuma)", "",
         f"Kaynak: Printful API (v1 + v2), ham yanitlar `ham/`. Son istek: {zaman}. Istek: {len(ist)} "
         f"(GET {sum(1 for x in ist if x['yontem'] == 'GET')}, POST {sum(1 for x in ist if x['yontem'] == 'POST')}: {', '.join(post) or 'yok'}).",
         "Olcu cm = inch x 2.54 (hesap). Fiyat: v1 `variants[].price` (USD, kargo haric); v2 `prices?currency=` (USD/EUR).",
         "Kargo: 1 adet, ornek adres (baskent/merkez posta kodu), en ucuz secenek (v1 /shipping/rates). Cikis ulkesi: v2 "
         "/v2/shipping-rates `shipments[].departure_country`. Takip: API'de takip alani yoksa \"API vermedi\".", "",
         "## 1. Urunler", "",
         "| urun | sekil/olcu | yuz | fiyat USD (v1) | uretim yeri (cikis, v2) | satilabildigi bolgeler (v1) | baski dosyasi piksel |",
         "|---|---|---|---|---|---|---|"]
    for u in urunler:
        sekil = sorted({f"{v['varyant_adi']} [{v['boyut_api']}]" for v in u["varyant"]})
        sek = "; ".join(sekil) if len(sekil) <= 6 else "; ".join(sekil[:6]) + f" (+{len(sekil) - 6})"
        fiyat = aralik([v["fiyat_usd_v1"] for v in u["varyant"]])
        grup = {}
        for hedef, dep in u["cikis"].items():
            grup.setdefault(", ".join(sorted(dep)) or YOK, []).append(hedef)
        cik = "; ".join(f"{d} (hedef {', '.join(h)})" for d, h in grup.items()) or (
            "sorgulanmadi" if not u["kargo_var"] else YOK)
        bol = sorted({b for v in u["varyant"] for b in v["satilabilir_bolgeler_v1"].split(", ") if b and b != YOK})
        bolt = ", ".join(bol) or YOK
        if bol == ["US"]:
            bolt = "**YALNIZ ABD** (US)"
        px = sorted({v["printfile_px"] for v in u["varyant"]})
        durdu = " (DURDURULMUS)" if u["durdu"] is True else ""
        L.append(f"| {u['id']} {u['ad']}{durdu} | {sek or YOK} | {u['yuz']} | {fiyat} | {cik} | {bolt} | {'; '.join(px) or YOK} |")
    L += ["", "## 2. Kargo ucreti (USD, 1 adet, en ucuz yontem; hucre: ucret (yontem id, min-max gun))", "",
          "| urun | " + " | ".join(ULKELER) + " |", "|---|" + "---|" * len(ULKELER)]
    for u in urunler:
        if not u["kargo_var"]:
            continue
        hucre = [kargo_hucre([k for k in kargo if k["urun_id"] == u["id"] and k["ulke"] == ul]) for ul in ULKELER]
        L.append(f"| {u['id']} {u['ad']} | " + " | ".join(hucre) + " |")
    L += ["", "Yontem adlari (v1 `name`, ilk varyant):", ""]
    for u in urunler:
        ad = sorted({f"{k['ulke']}: {k['yontem_adi']}" for k in kargo if k["urun_id"] == u["id"]
                     and k["varyant_id"] == (u["varyant"][0]["varyant_id"] if u["varyant"] else None)})
        if ad:
            L.append(f"- {u['id']}: " + " | ".join(ad))
    L += ["", "## 3. Urun ayrintilari", ""]
    for u in urunler:
        U = u["U"]
        L += [f"### {u['id']} {u['ad']}", "",
              f"- eslesme: {', '.join(u['neden'])} | HTTP v1 {u['http_v1']} v2 {u['http_v2']}",
              f"- tur: {u['tur']} | model: {u['model']} | marka: {u['marka']} | durdurulmus: {u['durdu'] if u['durdu'] is not None else YOK}",
              f"- baski teknigi: {', '.join(u['teknik'])}",
              f"- yuz / baski alanlari: {u['yuz']} | v1 files ek ucret: {'; '.join(u['ek_yer']) or YOK}",
              f"- v2 placement fiyatlari USD: " + ("; ".join(f"{pl.get('id') or pl.get('placement')}:{pl.get('price')}"
                                                       for pl in U["yer_fiyat2"].get("USD", [])) or YOK),
              f"- v2 placement fiyatlari EUR: " + ("; ".join(f"{pl.get('id') or pl.get('placement')}:{pl.get('price')}"
                                                       for pl in U["yer_fiyat2"].get("EUR", [])) or YOK),
              f"- ort. uretim suresi (v1 avg_fulfillment_time): {u['ort_sure'] if u['ort_sure'] is not None else YOK}"
              f" | origin_country (v1): {u['origin'] or YOK}",
              f"- tasma payi: {' / '.join(u['tasma']) or YOK}", ""]
        if u["olcu_tablo"]:
            L += ["Olcu tablosu (API):", ""] + [f"- {t}" for t in u["olcu_tablo"]] + [""]
        else:
            L += [f"Olcu tablosu: {YOK}", ""]
        L += ["| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for v in u["varyant"]:
            L.append(f"| {v['varyant_id']} | {v['varyant_adi']} | {v['boyut_api']} | {v['olcu_inch']} | {v['olcu_cm_hesap']} | "
                     f"{v['fiyat_usd_v1']} | {v['fiyat_usd_v2']} | {v['fiyat_eur_v2']} | {v['stok_v1']} | {v['bolge_durum_v1']} | "
                     f"{v['printfile_id']} | {v['printfile_px']} | {v['printfile_dpi']} | {v['fill_mode']} |")
        L += ["", "Aciklama metni (API, aynen):", "", "```", (u["aciklama"] or YOK).strip(), "```", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("oku", "rapor"):
        sys.exit(__doc__)
    sys.exit(oku(Path(sys.argv[2])) if sys.argv[1] == "oku" else rapor(Path(sys.argv[2])))
